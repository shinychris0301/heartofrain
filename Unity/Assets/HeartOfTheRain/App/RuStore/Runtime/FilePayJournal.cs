using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

namespace HeartOfTheRain.App.RuStore
{
    // Stores only correlation and delivery metadata, never credentials. The
    // checksum detects corruption; it is NOT a server signature or authority.
    // A reopened order must still be reconciled with the authenticated server.
    public sealed class FilePayJournal:IPayJournal
    {
        readonly string path,player;
        const int Limit=32768;
        static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
        [Serializable] sealed class RequestData {public string orderId,productId,appUserId,developerPayload;public int quantity;public bool sandbox;}
        [Serializable] sealed class LocatorData {public string purchaseId,invoiceId,orderId,productId;public int quantity;public bool sandbox;}
        [Serializable] sealed class ReceiptData {public string orderId,productId,appUserId,purchaseId,invoiceId,receiptId;public bool sandbox,durable,availableToSpend;}
        // JsonUtility serializes inline class fields as objects even when the
        // source reference is null. Explicit presence flags preserve optional
        // metadata across a real file roundtrip.
        [Serializable] sealed class Data {public RequestData request;public LocatorData locator;public ReceiptData receipt;public string phase;public bool hasLocator,hasReceipt;}
        [Serializable] sealed class TerminalData {public string orderId,productId,appUserId,purchaseId,invoiceId,state;public bool sandbox,durable,noCredit;}
        [Serializable] sealed class Data2 {public RequestData request;public LocatorData locator;public ReceiptData receipt;public string phase;public bool hasLocator,hasReceipt;public string recoveryPurchaseId;public bool hasRecoveryPurchaseId,hasTerminal;public TerminalData terminal;}
        [Serializable] sealed class Envelope {public int schemaVersion=2;public string playerId,payload,sha256;}
        public FilePayJournal(string path,string expectedPlayer)
        {
            if(string.IsNullOrWhiteSpace(path)||!PayRequest.Hex(expectedPlayer))throw new ArgumentException("Invalid payment journal configuration");
            this.path=Path.GetFullPath(path);player=expectedPlayer;
            Directory.CreateDirectory(Path.GetDirectoryName(this.path));
        }
        static string Hash(string value){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(Utf8.GetBytes(value))).Replace("-","").ToLowerInvariant();}
        FileStream Lock()=>new FileStream(path+".lock",FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None);
        static PayRequest Request(RequestData d)=>d==null?null:new PayRequest(d.orderId,d.productId,d.appUserId,d.developerPayload,d.quantity,d.sandbox);
        static PayLocator Locator(LocatorData d)=>d==null?null:new PayLocator(d.purchaseId,d.invoiceId,d.orderId,d.productId,d.quantity,d.sandbox);
        static PayDeliveryReceipt Receipt(ReceiptData d)=>d==null?null:new PayDeliveryReceipt(d.orderId,d.productId,d.appUserId,d.purchaseId,d.invoiceId,d.receiptId,d.sandbox,d.durable,d.availableToSpend);
        static PayTerminalReceipt Terminal(TerminalData d)=>d==null?null:new PayTerminalReceipt(d.orderId,d.productId,d.appUserId,d.purchaseId,d.invoiceId,d.state,d.sandbox,d.durable,d.noCredit);
        static Data Record(PayPending p)=>new Data {
            phase=p.phase,request=new RequestData{orderId=p.request.orderId,productId=p.request.productId,appUserId=p.request.appUserId,developerPayload=p.request.developerPayload,quantity=p.request.quantity,sandbox=p.request.sandbox},
            hasLocator=p.locator!=null,hasReceipt=p.receipt!=null,
            locator=p.locator==null?new LocatorData():new LocatorData{purchaseId=p.locator.purchaseId,invoiceId=p.locator.invoiceId,orderId=p.locator.orderId,productId=p.locator.productId,quantity=p.locator.quantity,sandbox=p.locator.sandbox},
            receipt=p.receipt==null?new ReceiptData():new ReceiptData{orderId=p.receipt.orderId,productId=p.receipt.productId,appUserId=p.receipt.appUserId,purchaseId=p.receipt.purchaseId,invoiceId=p.receipt.invoiceId,receiptId=p.receipt.receiptId,sandbox=p.receipt.sandbox,durable=p.receipt.durable,availableToSpend=p.receipt.availableToSpend}
        };
        static Data2 Record2(PayPending p){var old=Record(p);return new Data2{
            request=old.request,locator=old.locator,receipt=old.receipt,phase=old.phase,hasLocator=old.hasLocator,hasReceipt=old.hasReceipt,
            recoveryPurchaseId=p.recoveryPurchaseId??"",hasRecoveryPurchaseId=p.recoveryPurchaseId!=null,hasTerminal=p.terminal!=null,
            terminal=p.terminal==null?new TerminalData():new TerminalData{orderId=p.terminal.orderId,productId=p.terminal.productId,appUserId=p.terminal.appUserId,purchaseId=p.terminal.purchaseId,invoiceId=p.terminal.invoiceId,state=p.terminal.state,sandbox=p.terminal.sandbox,durable=p.terminal.durable,noCredit=p.terminal.noCredit}
        };}
        void Validate(PayPending p)
        {
            if(p==null||!p.Valid||p.request.appUserId!=player)throw new InvalidOperationException("Invalid payment journal identity");
            if(!new[]{"AwaitingPayment","OutcomeUnknown","AwaitingRecovery","AwaitingAuthority","AcknowledgementPending","Acknowledged","ResolvedWithoutDelivery"}.Contains(p.phase))throw new InvalidOperationException("Invalid payment journal phase");
            bool early=p.phase=="AwaitingPayment"||p.phase=="OutcomeUnknown";
            bool delivery=p.phase=="AcknowledgementPending"||p.phase=="Acknowledged";
            if(early&&(p.locator!=null||p.receipt!=null)||!early&&(p.locator==null||!p.locator.Matches(p.request)))throw new InvalidOperationException("Invalid payment journal correlation");
            Guid purchase;
            if(p.locator!=null&&!Guid.TryParse(p.locator.purchaseId,out purchase))throw new InvalidOperationException("Invalid purchase identity");
            if(delivery) {
                // Structural consistency only. No SDK observation or grant is
                // manufactured by reading this file; recovery re-verifies it.
                var shape=new PayPurchase(p.locator,p.request.developerPayload,"CONFIRMED","UNDEFINED","UNKNOWN");
                if(p.receipt==null||!p.receipt.Matches(p.request,shape))throw new InvalidOperationException("Invalid delivery metadata");
            } else if(p.receipt!=null)throw new InvalidOperationException("Unexpected delivery metadata");
        }
        PayPending Read()
        {
            if(!File.Exists(path))return null;
            byte[] bytes;
            using(var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)) {
                if(stream.Length<1||stream.Length>Limit)throw new InvalidOperationException("Invalid payment journal length");
                bytes=new byte[(int)stream.Length];int offset=0,n;
                while(offset<bytes.Length&&(n=stream.Read(bytes,offset,bytes.Length-offset))>0)offset+=n;
                if(offset!=bytes.Length)throw new InvalidOperationException("Incomplete payment journal");
            }
            string text=Utf8.GetString(bytes);var e=JsonUtility.FromJson<Envelope>(text);
            if(e==null||(e.schemaVersion!=1&&e.schemaVersion!=2)||e.playerId!=player||string.IsNullOrEmpty(e.payload)||Hash(e.payload)!=e.sha256||JsonUtility.ToJson(e)!=text)
                throw new InvalidOperationException("Payment journal checksum or identity mismatch");
            PayPending result;
            if(e.schemaVersion==1){
                // Keep the exact original inline-class/presence-flag parser.
                // Loading an old pending record never rewrites it or dispatches.
                var data=JsonUtility.FromJson<Data>(e.payload);
                if(data==null||JsonUtility.ToJson(data)!=e.payload)throw new InvalidOperationException("Invalid payment journal shape");
                result=new PayPending(Request(data.request),data.phase,data.hasLocator?Locator(data.locator):null,data.hasReceipt?Receipt(data.receipt):null);
                Validate(result);
                if(JsonUtility.ToJson(Record(result))!=e.payload)throw new InvalidOperationException("Noncanonical payment journal metadata");
            }else{
                var data=JsonUtility.FromJson<Data2>(e.payload);
                if(data==null||JsonUtility.ToJson(data)!=e.payload)throw new InvalidOperationException("Invalid payment journal shape");
                result=new PayPending(Request(data.request),data.phase,data.hasLocator?Locator(data.locator):null,data.hasReceipt?Receipt(data.receipt):null,data.hasRecoveryPurchaseId?data.recoveryPurchaseId:null,data.hasTerminal?Terminal(data.terminal):null);
                Validate(result);
                if(JsonUtility.ToJson(Record2(result))!=e.payload)throw new InvalidOperationException("Noncanonical payment journal metadata");
            }
            return result;
        }
        public PayPending Load()
        {
            try{using(Lock())return Read();}
            catch(Exception){throw new InvalidOperationException("Payment journal unavailable or corrupt");}
        }
        public bool TrySave(PayPending pending,out string error)
        {
            error=null;string temp=null;
            try {
                Validate(pending);
                using(Lock()) {
                    var old=Read();
                    if(old!=null) {
                        if(old.request.orderId==pending.request.orderId&&!old.request.SameOrder(pending.request))throw new InvalidOperationException("Order identity changed");
                        if(old.request.orderId==pending.request.orderId&&pending.phase=="AwaitingPayment")throw new InvalidOperationException("Payment was already dispatched or requires recovery");
                        if(old.request.orderId!=pending.request.orderId&&old.phase!="Acknowledged"&&old.phase!="ResolvedWithoutDelivery")throw new InvalidOperationException("Another order remains pending");
                        if(old.request.orderId==pending.request.orderId&&old.recoveryPurchaseId!=null&&
                           (pending.locator==null?pending.recoveryPurchaseId!=old.recoveryPurchaseId:pending.locator.purchaseId!=old.recoveryPurchaseId))throw new InvalidOperationException("Known recovery hint cannot be erased or rebound");
                        if(old.request.orderId==pending.request.orderId&&old.locator!=null&&pending.locator==null)throw new InvalidOperationException("Known purchase identity cannot be erased");
                        if(old.request.orderId==pending.request.orderId&&old.locator!=null&&pending.locator!=null&&
                           (old.locator.purchaseId!=pending.locator.purchaseId||old.locator.invoiceId!=pending.locator.invoiceId))throw new InvalidOperationException("Purchase identity changed");
                    }
                    string payload=JsonUtility.ToJson(Record2(pending));
                    byte[] bytes=Utf8.GetBytes(JsonUtility.ToJson(new Envelope{playerId=player,payload=payload,sha256=Hash(payload)}));
                    if(bytes.Length>Limit)throw new InvalidOperationException("Payment journal too large");
                    temp=path+"."+Guid.NewGuid().ToString("N")+".tmp";
                    using(var stream=new FileStream(temp,FileMode.CreateNew,FileAccess.Write,FileShare.None)) {
                        stream.Write(bytes,0,bytes.Length);stream.Flush(true);
                    }
                    if(File.Exists(path))File.Replace(temp,path,path+".bak");else File.Move(temp,path);
                    temp=null;
                    return true;
                }
            } catch(Exception) {error="PaymentJournalSaveUnavailable";return false;}
            finally {if(temp!=null)try{File.Delete(temp);}catch(Exception){}}
        }
    }
}

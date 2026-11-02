using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.Profile;

namespace HeartOfTheRain.App.ServerRewards {
    [Serializable] public sealed class RewardPresentation {
        public string channel,id;
        public RewardGrant grant;
        public bool presented;
    }
    // A public receipt outbox, not a wallet. Changing or replaying this file can
    // change a cosmetic notification only; it can never credit the player.
    public sealed class RewardPresentationJournal {
        [Serializable] sealed class Document {
            public int version=1;public long revision;
            public string origin,player;
            public List<RewardPresentation> receipts=new List<RewardPresentation>();
        }
        [Serializable] sealed class Envelope {public string payload,sha256;}
        const int ByteLimit=4194304,ReceiptLimit=8192,PresentedHistoryLimit=512;
        readonly string path,origin,player;
        readonly UTF8Encoding utf8=new UTF8Encoding(false,true);
        public Action<string> VerificationCheckpoint;
        public static RewardPresentationJournal ForPlayer(string origin,string player) {
            var canonical=new Uri(origin).GetLeftPart(UriPartial.Authority);
            return new RewardPresentationJournal(Path.Combine(Application.persistentDataPath,"ServerReview","RewardPresentation",IdentityProtocol82.Sha(canonical),player,"receipts.json"),canonical,player);
        }
        public RewardPresentationJournal(string path,string origin,string player) {
            Uri uri;
            if(!IdentityProtocol82.Id(player)||!Uri.TryCreate(origin,UriKind.Absolute,out uri)||uri.UserInfo!=""||uri.Query!=""||uri.Fragment!=""||(uri.Scheme!="https"&&!(uri.Scheme=="http"&&uri.IsLoopback)))throw new ArgumentException("PresentationBindingInvalid");
            this.path=Path.GetFullPath(path);this.origin=uri.GetLeftPart(UriPartial.Authority);this.player=player;
            Directory.CreateDirectory(Path.GetDirectoryName(this.path));
        }
        static T Copy<T>(T value) where T:class=>value==null?null:JsonUtility.FromJson<T>(JsonUtility.ToJson(value));
        static void ValidateReceipt(RewardPresentation receipt) {
            if(receipt==null||string.IsNullOrEmpty(receipt.channel)||receipt.channel.Length>32||string.IsNullOrEmpty(receipt.id)||receipt.id.Length>256||receipt.grant==null)throw new InvalidOperationException("PresentationReceiptInvalid");
            receipt.grant.Validate();
        }
        void Validate(Document document) {
            if(document==null||document.version!=1||document.revision<0||document.origin!=origin||document.player!=player||document.receipts==null||document.receipts.Count>ReceiptLimit)throw new InvalidOperationException("PresentationJournalInvalid");
            var ids=new HashSet<string>();foreach(var receipt in document.receipts){ValidateReceipt(receipt);if(!ids.Add(receipt.channel+"/"+receipt.id))throw new InvalidOperationException("PresentationReceiptDuplicate");}
        }
        Document ReadCore() {
            if(!File.Exists(path))return new Document{origin=origin,player=player};
            using(var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)){
                if(file.Length<2||file.Length>ByteLimit)throw new InvalidOperationException("PresentationJournalSize");
                var bytes=new byte[(int)file.Length];int at=0;while(at<bytes.Length){int read=file.Read(bytes,at,bytes.Length-at);if(read<=0)throw new IOException();at+=read;}
                var envelope=JsonUtility.FromJson<Envelope>(utf8.GetString(bytes));
                if(envelope==null||!IdentityProtocol82.Digest(envelope.sha256)||IdentityProtocol82.Sha(utf8.GetBytes(envelope.payload??""))!=envelope.sha256)throw new InvalidOperationException("PresentationJournalCorrupt");
                var document=JsonUtility.FromJson<Document>(envelope.payload);Validate(document);return document;
            }
        }
        void SaveCore(Document document) {
            // Financial idempotence lives in the server ledger. Keep a bounded
            // cosmetic replay history so years of viewed notices cannot block
            // a new claim. Pending receipts are never retired by this policy.
            int retired=document.receipts.Count(r=>r.presented)-PresentedHistoryLimit;
            if(retired>0)document.receipts.RemoveAll(r=>r.presented&&retired-- > 0);
            Validate(document);document.revision=checked(document.revision+1);
            string payload=JsonUtility.ToJson(document);var bytes=utf8.GetBytes(JsonUtility.ToJson(new Envelope{payload=payload,sha256=IdentityProtocol82.Sha(utf8.GetBytes(payload))}));
            if(bytes.Length>ByteLimit)throw new InvalidOperationException("PresentationJournalSize");
            string temporary=Path.Combine(Path.GetDirectoryName(path),"p-"+Guid.NewGuid().ToString("N")+".tmp");
            try{using(var file=new FileStream(temporary,FileMode.CreateNew,FileAccess.Write,FileShare.None)){file.Write(bytes,0,bytes.Length);file.Flush(true);}
                VerificationCheckpoint?.Invoke("BeforeCommit");if(File.Exists(path))File.Replace(temporary,path,path+".bak");else File.Move(temporary,path);
                VerificationCheckpoint?.Invoke("AfterCommit");
            }finally{if(File.Exists(temporary))File.Delete(temporary);}
        }
        public void Enqueue(string channel,string receiptId,RewardGrant grant) {
            var receipt=new RewardPresentation{channel=channel,id=receiptId,grant=grant?.Copy()};ValidateReceipt(receipt);
            using(var held=new FileStream(path+".lock",FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)){
                var document=ReadCore();var previous=document.receipts.Find(r=>r.channel==channel&&r.id==receiptId);
                if(previous!=null){if(JsonUtility.ToJson(previous.grant)!=JsonUtility.ToJson(receipt.grant))throw new InvalidOperationException("PresentationReceiptConflict");return;}
                document.receipts.Add(receipt);SaveCore(document);
            }
        }
        public RewardPresentation Peek() {
            using(var held=new FileStream(path+".lock",FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None))return Copy(ReadCore().receipts.FirstOrDefault(r=>!r.presented));
        }
        public void MarkPresented(string channel,string receiptId) {
            using(var held=new FileStream(path+".lock",FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)){
                var document=ReadCore();var receipt=document.receipts.Find(r=>r.channel==channel&&r.id==receiptId);
                if(receipt==null)throw new InvalidOperationException("PresentationReceiptMissing");if(receipt.presented)return;
                receipt.presented=true;SaveCore(document);
            }
        }
    }
}

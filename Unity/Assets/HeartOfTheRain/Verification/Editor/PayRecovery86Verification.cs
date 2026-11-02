#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using HeartOfTheRain.App.RuStore;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.Verification {
    // Executes real disk journal/parser/coordinator code. Store and payment
    // authority are scripted; no payment, SDK, HTTP or coin grant is exercised.
    public static class PayRecovery86Verification {
        const string Player="11111111111111111111111111111111",Purchase="11111111-1111-4111-8111-111111111111";
        static string folder;static Report report;
        [Serializable] sealed class Row {public string name;public int checks;public bool passed;}
        [Serializable] sealed class Report {
            public string status,utc,unity;public int checks,cases,legacyRecords,terminalParserAccepted,terminalParserRejected,catalogParserAccepted,catalogParserRejected;
            public bool actualDiskJournal=true,scriptedStore=true,scriptedAuthority=true,sdkInvoked=false,httpInvoked=false;
            public string scope="Pinned Unity Editor execution of actual payment coordinator, version1/2 disk journal and actual server terminal/catalog parsers with scripted store/authority. No SDK invocation, HTTP, real payment, provider verification, wallet mutation, app lifecycle or Android power-loss proof.";
            public List<Row> rows=new List<Row>();public List<string> errors=new List<string>();
        }
        static void Need(bool ok,string code){report.checks++;if(!ok)throw new InvalidOperationException(code);}
        static void Case(string name,Action action){int before=report.checks;var row=new Row{name=name};report.rows.Add(row);report.cases++;try{action();row.passed=true;}catch(Exception e){report.errors.Add(name+":"+e.GetType().Name+":"+e.Message);}finally{row.checks=report.checks-before;}}
        static string Hash(byte[] bytes){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
        static PayRequest Request(string order)=>new PayRequest(order,"synthetic_1000",Player,"hotr-order-v1:"+order+":22222222222222222222222222222222",1,true);
        static PayRequest NewRequest(){string id=Guid.NewGuid().ToString("N");return Request(id);}
        static PayLocator Locator(PayRequest r,string purchase=Purchase)=>new PayLocator(purchase,"1001",r.orderId,r.productId,1,true);
        static PayPurchase Observed(PayRequest r,string status="CANCELLED",string purchase=Purchase)=>new PayPurchase(Locator(r,purchase),r.developerPayload,status,"ONE_STEP","PENDING");
        static PayTerminalReceipt Terminal(PayRequest r,PayPurchase p,string state=null,bool durable=true,bool noCredit=true)=>new PayTerminalReceipt(r.orderId,r.productId,r.appUserId,p.locator.purchaseId,p.locator.invoiceId,state??PayTerminalReceipt.StateFor(p.status),true,durable,noCredit);

        sealed class Store:IPayStore {
            public bool SdkCompiled=>true;public bool Configured=>true;
            public int purchases,lookups,lists,acks;public string hint=PayRecovery86Verification.Purchase;public PayPurchase observed;public bool hold;public Action<PayReply<PayLocator>> held;
            public void GetPurchaseAvailability(Action<PayReply<PayAvailability>> done)=>done(PayReply<PayAvailability>.Ok(new PayAvailability(true)));
            public void GetProducts(string[] ids,Action<PayReply<PayProduct[]>> done)=>done(PayReply<PayProduct[]>.Ok(new PayProduct[0]));
            public void Purchase(PayRequest request,Action<PayReply<PayLocator>> done){purchases++;if(hold){held=done;return;}done(PayReply<PayLocator>.Fail("SyntheticCancelled",true,hint));}
            public void GetPurchase(string id,Action<PayReply<PayPurchase>> done){lookups++;done(observed==null?PayReply<PayPurchase>.Fail("SyntheticUnknown",true):PayReply<PayPurchase>.Ok(observed));}
            public void GetPurchases(Action<PayReply<PayPurchase[]>> done){lists++;done(PayReply<PayPurchase[]>.Ok(new PayPurchase[0]));}
            public void ConfirmTwoStep(PayRequest r,PayPurchase p,PayCaptureAuthorization a,Action<PayReply<PayAvailability>> done)=>done(PayReply<PayAvailability>.Fail("SyntheticUnavailable"));
            public void Acknowledge(PayRequest r,PayPurchase p,PayDeliveryReceipt a,Action<PayReply<PayAvailability>> done){acks++;done(PayReply<PayAvailability>.Ok(new PayAvailability(true)));}
        }
        sealed class Authority:IPayAuthority,IPayTerminalAuthority {
            public bool WalletReady=>true;public int reconciles,resolutions;public PayTerminalReceipt receipt;public bool duplicate;
            public void Reconcile(PayRequest r,PayPurchase p,Action<PayReply<PayDeliveryReceipt>> done){reconciles++;done(PayReply<PayDeliveryReceipt>.Fail("SyntheticNotPaid",true));}
            public void ResolveTerminal(PayRequest r,PayPurchase p,Action<PayReply<PayTerminalReceipt>> done){resolutions++;var result=PayReply<PayTerminalReceipt>.Ok(receipt??Terminal(r,p));done(result);if(duplicate)done(result);}
        }
        sealed class LegacyAuthority:IPayAuthority {public bool WalletReady=>true;public void Reconcile(PayRequest r,PayPurchase p,Action<PayReply<PayDeliveryReceipt>> done)=>done(PayReply<PayDeliveryReceipt>.Fail("SyntheticNoTerminalAuthority"));}
        sealed class FaultJournal:IPayJournal {
            public FilePayJournal disk;public bool failHint;
            public PayPending Load()=>disk.Load();
            public bool TrySave(PayPending p,out string error){if(failHint&&p.recoveryPurchaseId!=null){error="SyntheticBeforeCommit";return false;}return disk.TrySave(p,out error);}
        }
        static FilePayJournal Journal(string label)=>new FilePayJournal(Path.Combine(folder,label+".json"),Player);
        static PayReply<PayPending> Begin(PayDeliveryCoordinator flow,PayRequest request){PayReply<PayPending> result=null;flow.Begin(request,value=>result=value);return result;}
        static PayReply<PayPending> Recover(PayDeliveryCoordinator flow){PayReply<PayPending> result=null;flow.Recover(value=>result=value);return result;}

        static void DurableHintAndTerminal(){
            foreach(string state in new[]{"CANCELLED","REJECTED","EXPIRED"}){
                var r=NewRequest();var journal=Journal(state);var store=new Store{observed=Observed(r,state)};var authority=new Authority();var first=Begin(new PayDeliveryCoordinator(store,authority,journal),r);
                Need(first!=null&&!first.Succeeded&&journal.Load().recoveryPurchaseId==Purchase&&store.lookups==0,"HintDurableBeforeLookup");
                var recovered=Recover(new PayDeliveryCoordinator(store,authority,journal));
                Need(recovered.Succeeded&&recovered.value.phase=="ResolvedWithoutDelivery"&&journal.Load().terminal.state==PayTerminalReceipt.StateFor(state),"FreshServerTerminalReceiptClosesOnlyKnownNoDelivery");
                Need(store.purchases==1&&store.lookups==1&&store.lists==0&&store.acks==0&&authority.reconciles==0&&authority.resolutions==1,"NoRepurchaseNoCreditNoDeliveryAck");
                Begin(new PayDeliveryCoordinator(store,authority,journal),NewRequest());Need(store.purchases==2,"OnlyNewExplicitBuyAfterTerminalResolutionCanDispatch");
            }
        }
        static void EmptyListRetained(){
            var r=NewRequest();var j=Journal("empty");var store=new Store{hint=null};var a=new Authority();Begin(new PayDeliveryCoordinator(store,a,j),r);var prior=j.Load();
            var answer=Recover(new PayDeliveryCoordinator(store,a,j));Need(!answer.Succeeded&&answer.error.outcomeUnknown&&answer.error.code=="PurchaseStillUnknown"&&j.Load().phase==prior.phase,"EmptyListNeverProvesCancellation");
            Begin(new PayDeliveryCoordinator(store,a,j),NewRequest());Need(store.purchases==1&&store.lists==1&&a.resolutions==0,"UnknownIntentBlocksReplacementPurchase");
        }
        static void ForeignHintRetained(){
            foreach(bool wrongPurchase in new[]{false,true}){
                var r=NewRequest();var j=Journal("foreign"+wrongPurchase);var store=new Store{observed=wrongPurchase?Observed(r,"CANCELLED","22222222-2222-4222-8222-222222222222"):Observed(NewRequest())};var a=new Authority();Begin(new PayDeliveryCoordinator(store,a,j),r);var saved=j.Load();
                var answer=Recover(new PayDeliveryCoordinator(store,a,j));Need(!answer.Succeeded&&j.Load().recoveryPurchaseId==saved.recoveryPurchaseId&&a.resolutions==0&&store.acks==0,"ForeignPurchaseOrOrderCannotResolveHint");
            }
        }
        static void TerminalMismatchRetained(){
            foreach(string mismatch in new[]{"state","durable","credit","owner"}){
                var r=NewRequest();var p=Observed(r);var j=Journal("mismatch"+mismatch);var store=new Store{observed=p};var a=new Authority{receipt=mismatch=="owner"?new PayTerminalReceipt(r.orderId,r.productId,"22222222222222222222222222222222",Purchase,"1001","Cancelled",true,true,true):Terminal(r,p,mismatch=="state"?"Expired":null,mismatch!="durable",mismatch!="credit")};Begin(new PayDeliveryCoordinator(store,a,j),r);
                var result=Recover(new PayDeliveryCoordinator(store,a,j));Need(!result.Succeeded&&j.Load().phase=="AwaitingAuthority"&&store.acks==0,"UnboundTerminalReceiptDoesNotClose");
            }
        }
        static void OptionalAuthorityRequired(){var r=NewRequest();var j=Journal("legacyAuthority");var store=new Store{observed=Observed(r)};Begin(new PayDeliveryCoordinator(store,new LegacyAuthority(),j),r);var result=Recover(new PayDeliveryCoordinator(store,new LegacyAuthority(),j));Need(!result.Succeeded&&result.error.code=="TerminalAuthorityUnavailable"&&j.Load().phase=="AwaitingAuthority","OldAuthorityCannotInventTerminalProof");}
        static void HintSaveFault(){var r=NewRequest();var disk=Journal("fault");var j=new FaultJournal{disk=disk,failHint=true};var store=new Store{observed=Observed(r)};var a=new Authority();var answer=Begin(new PayDeliveryCoordinator(store,a,j),r);Need(!answer.Succeeded&&answer.error.code=="JournalSaveUnavailable"&&disk.Load().phase=="AwaitingPayment"&&store.lookups==0&&a.resolutions==0,"HintSaveFailureCannotStartRecoveryOrEraseUnknown");}
        static void OwnerCancellation(){var r=NewRequest();var j=Journal("owner");var store=new Store{hold=true};var a=new Authority();var flow=new PayDeliveryCoordinator(store,a,j);int callbacks=0;flow.Begin(r,_=>callbacks++);flow.Cancel();store.held(PayReply<PayLocator>.Fail("SyntheticLate",true,Purchase));Need(callbacks==0&&!flow.Busy&&j.Load().phase=="AwaitingPayment"&&j.Load().recoveryPurchaseId==null,"CancelledOwnerLateHintCannotMutateJournal");}
        static void HintMonotonic(){var r=NewRequest();var j=Journal("monotonic");string error;Need(j.TrySave(new PayPending(r,"OutcomeUnknown",recoveryPurchaseId:Purchase),out error),"SaveInitialHint");Need(!j.TrySave(new PayPending(r,"OutcomeUnknown"),out error)&&j.Load().recoveryPurchaseId==Purchase,"HintCannotBeErased");Need(!j.TrySave(new PayPending(r,"OutcomeUnknown",recoveryPurchaseId:"22222222-2222-4222-8222-222222222222"),out error),"HintCannotBeRebound");Need(!j.TrySave(new PayPending(r,"AwaitingAuthority",Locator(r,"22222222-2222-4222-8222-222222222222")),out error),"HintCannotPromoteForeignLocator");Need(j.TrySave(new PayPending(r,"AwaitingAuthority",Locator(r)),out error)&&j.Load().locator.purchaseId==Purchase,"ExactHintPromotesToFullBoundLocator");Need(PayReply<PayLocator>.Fail("Synthetic",true,"invalid").error.recoveryPurchaseId==null,"MalformedSdkHintRetainsUnresolvedOutcome");}
        static void DuplicateTerminalCallback(){var r=NewRequest();var j=Journal("duplicate");var store=new Store{observed=Observed(r)};var a=new Authority{duplicate=true};Begin(new PayDeliveryCoordinator(store,a,j),r);int calls=0;bool success=false;new PayDeliveryCoordinator(store,a,j).Recover(value=>{calls++;success=value.Succeeded;});Need(calls==1&&success&&j.Load().phase=="ResolvedWithoutDelivery"&&store.acks==0,"RepeatedAuthorityCallbackCannotReplayClose");}

        [Serializable] sealed class LegacyRequest {public string orderId,productId,appUserId,developerPayload;public int quantity;public bool sandbox;}
        [Serializable] sealed class LegacyLocator {public string purchaseId,invoiceId,orderId,productId;public int quantity;public bool sandbox;}
        [Serializable] sealed class LegacyReceipt {public string orderId,productId,appUserId,purchaseId,invoiceId,receiptId;public bool sandbox,durable,availableToSpend;}
        [Serializable] sealed class LegacyData {public LegacyRequest request;public LegacyLocator locator;public LegacyReceipt receipt;public string phase;public bool hasLocator,hasReceipt;}
        [Serializable] sealed class LegacyEnvelope {public int schemaVersion=1;public string playerId,payload,sha256;}
        static void LegacyMigration(){
            foreach(string phase in new[]{"AwaitingPayment","OutcomeUnknown","AwaitingRecovery","AwaitingAuthority","AcknowledgementPending","Acknowledged"}){
                var r=NewRequest();bool known=phase!="AwaitingPayment"&&phase!="OutcomeUnknown",credited=phase=="AcknowledgementPending"||phase=="Acknowledged";
                var data=new LegacyData{request=new LegacyRequest{orderId=r.orderId,productId=r.productId,appUserId=r.appUserId,developerPayload=r.developerPayload,quantity=1,sandbox=true},locator=known?new LegacyLocator{purchaseId=Purchase,invoiceId="1001",orderId=r.orderId,productId=r.productId,quantity=1,sandbox=true}:new LegacyLocator(),receipt=credited?new LegacyReceipt{orderId=r.orderId,productId=r.productId,appUserId=Player,purchaseId=Purchase,invoiceId="1001",receiptId="synthetic-receipt",sandbox=true,durable=true,availableToSpend=true}:new LegacyReceipt(),phase=phase,hasLocator=known,hasReceipt=credited};
                string payload=JsonUtility.ToJson(data),path=Path.Combine(folder,"legacy"+phase+".json");File.WriteAllText(path,JsonUtility.ToJson(new LegacyEnvelope{playerId=Player,payload=payload,sha256=Hash(Encoding.UTF8.GetBytes(payload))}),new UTF8Encoding(false));var bytes=File.ReadAllBytes(path);
                var j=new FilePayJournal(path,Player);var loaded=j.Load();Need(loaded.Valid&&loaded.phase==phase&&loaded.recoveryPurchaseId==null&&bytes.SequenceEqual(File.ReadAllBytes(path)),"ExactSchema1LoadPreservesBytesAndPendingState");report.legacyRecords++;
                string error;var next=phase=="AwaitingPayment"?new PayPending(r,"OutcomeUnknown",recoveryPurchaseId:Purchase):loaded;
                Need(j.TrySave(next,out error)&&j.Load().Valid&&File.ReadAllText(path).Contains("\"schemaVersion\":2"),"ExplicitNextCommitUpgradesSchema2WithoutRedispatch");
            }
        }

        static RuStoreBackendClient Client()=>new RuStoreBackendClient("http://127.0.0.1:18686",new string('A',43),Player,true,true,_=>{});
        static string OrderJson(PayRequest r,string state="Cancelled")=>"{\"orderId\":\""+r.orderId+"\",\"playerId\":\""+Player+"\",\"state\":\""+state+"\",\"catalogVersion\":\"synthetic86\",\"productId\":\"coins-1000\",\"coins\":1000,\"amountMinor\":19900,\"currency\":\"RUB\",\"invoiceId\":\"1001\",\"purchaseId\":\""+Purchase+"\",\"sdk\":{\"orderId\":\""+r.orderId+"\",\"productId\":\""+r.productId+"\",\"quantity\":1,\"appUserId\":\""+Player+"\",\"developerPayload\":\""+r.developerPayload+"\",\"sandbox\":true},\"credit\":null,\"deliveryAcknowledgement\":null,\"productionEnabled\":false,\"availableToSpend\":false,\"availableInServerWallet\":false,\"balanceScope\":\"server_wallet\",\"normalUnityProfileIntegrated\":false,\"localProfileMutated\":false}";
        static void TerminalParser(){
            var r=NewRequest();using(var c=Client()){
                foreach(string status in new[]{"CANCELLED","REJECTED","EXPIRED"}){var p=Observed(r,status);var receipt=c.VerificationParseTerminalOrder(OrderJson(r,PayTerminalReceipt.StateFor(status)),r,p);Need(receipt.Matches(r,p.locator),"ActualTerminalParserPositive");report.terminalParserAccepted++;}
                string json=OrderJson(r);var invalid=new[]{json.Replace("\"Cancelled\"","\"Confirmed\""),json.Replace("\"Cancelled\"","\"RefundReview\""),json.Replace("\"availableToSpend\":false","\"availableToSpend\":true"),json.Replace("\"availableInServerWallet\":false","\"availableInServerWallet\":true"),json.Replace("\"credit\":null","\"credit\":{\"receiptId\":\"synthetic\",\"coins\":1000}"),json.Replace("\"deliveryAcknowledgement\":null","\"deliveryAcknowledgement\":\"Pending\""),json.Replace("\"invoiceId\":\"1001\"","\"invoiceId\":\"1002\""),json.Replace("\"quantity\":1","\"quantity\":2"),json.Replace("\"sandbox\":true","\"sandbox\":false"),json.Replace(r.developerPayload,"foreign-payload"),json.Replace("\"playerId\":\""+Player+"\"","\"playerId\":\"22222222222222222222222222222222\""),json.Replace("\"productionEnabled\":false","\"productionEnabled\":false,\"productionEnabled\":false")};
                foreach(string bad in invalid){bool rejected=false;try{c.VerificationParseTerminalOrder(bad,r,Observed(r));}catch{rejected=true;}Need(rejected,"ActualTerminalParserRejectsUnboundOrCreditedResponse");report.terminalParserRejected++;}
                foreach(string token in new[]{"\"\"","\"null\"","false","0","{}","[]"}){bool rejected=false;try{c.VerificationParseTerminalOrder(json.Replace("\"deliveryAcknowledgement\":null","\"deliveryAcknowledgement\":"+token),r,Observed(r));}catch{rejected=true;}Need(rejected,"OnlyExplicitNullAcknowledgementCanAuthorizeNoDelivery");report.terminalParserRejected++;}
                bool missingRejected=false;try{c.VerificationParseTerminalOrder(json.Replace("\"deliveryAcknowledgement\":null,",""),r,Observed(r));}catch{missingRejected=true;}Need(missingRejected,"MissingAcknowledgementIsNotVerifiedAbsence");report.terminalParserRejected++;
                foreach(string state in new[]{"PAID","CONFIRMED","REFUNDING","REFUNDED","REVERSED"}){bool rejected=false;try{c.VerificationParseTerminalOrder(json,r,Observed(r,state));}catch{rejected=true;}Need(rejected,"NonterminalOrQuarantinedObservationCannotClose");report.terminalParserRejected++;}
            }
        }
        static string CatalogJson()=>"{\"version\":\"synthetic86\",\"appId\":123,\"sandbox\":true,\"enabled\":true,\"productionEnabled\":false,\"fullGameplayWallet\":false,\"balanceScope\":\"server_wallet\",\"serverWalletProjection\":true,\"normalUnityProfileIntegrated\":false,\"reason\":\"staging_server_wallet\",\"products\":[{\"id\":\"coins-1000\",\"storeProductId\":\"synthetic_1000\",\"coins\":1000,\"amountMinor\":19900,\"currency\":\"RUB\",\"quantity\":1}]}";
        static void CatalogParser(){using(var c=Client()){
            string good=CatalogJson();var value=c.VerificationParseCatalog(good);Need(value.enabled&&value.appId==123&&value.sandbox&&value.products.Length==1&&value.products[0].amountMinor==19900,"ActualCatalogParserPositive");report.catalogParserAccepted++;
            string disabled=good.Replace("\"appId\":123","\"appId\":null").Replace("\"enabled\":true","\"enabled\":false");disabled=disabled.Substring(0,disabled.IndexOf("\"products\":",StringComparison.Ordinal))+"\"products\":[]}";Need(!c.VerificationParseCatalog(disabled).enabled&&c.VerificationParseCatalog(disabled).appId==0,"DisabledCatalogHasExplicitNoAppIdentity");report.catalogParserAccepted++;
            foreach(string bad in new[]{good.Replace("\"appId\":123","\"appId\":null"),good.Replace("\"appId\":123","\"appId\":true"),good.Replace("\"appId\":123","\"appId\":0"),good.Replace("\"sandbox\":true","\"sandbox\":false"),good.Replace("\"enabled\":true","\"enabled\":1"),good.Replace("\"productionEnabled\":false","\"productionEnabled\":true"),good.Replace("\"quantity\":1","\"quantity\":2"),good.Replace("\"amountMinor\":19900","\"amountMinor\":0"),good.Replace("\"coins\":1000","\"coins\":true"),good.Replace("\"RUB\"","\"USD\""),good.Replace("\"server_wallet\"","\"local_wallet\""),good.Replace("\"appId\":123","\"appId\":123,\"appId\":123"),disabled.Replace("\"enabled\":false","\"enabled\":true")}){bool rejected=false;try{c.VerificationParseCatalog(bad);}catch{rejected=true;}Need(rejected,"ActualCatalogParserRejectsInvalidIdentityPriceOrPolicy");report.catalogParserRejected++;}
        }}
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,status="FAIL_NATIVE_PAY_RECOVERY86"};
            string output=Environment.GetEnvironmentVariable("HOTR_REVIEW86_OUTPUT");if(string.IsNullOrEmpty(output))output=Path.GetFullPath("../Verification/Evidence/Review86");
            folder=Path.Combine(Path.GetTempPath(),"hotr-pay-recovery86-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(folder);
            try{Need(Application.unityVersion=="2022.3.62f3","PinnedEditorRequired");Case("DurableHintAndThreeVerifiedTerminalStates",DurableHintAndTerminal);Case("UnknownEmptyListRetainsIntent",EmptyListRetained);Case("ForeignPurchaseHintRetained",ForeignHintRetained);Case("UnboundTerminalReceiptRetained",TerminalMismatchRetained);Case("OptionalTerminalAuthorityRequired",OptionalAuthorityRequired);Case("HintBeforeCommitFault",HintSaveFault);Case("CancelledOwnerLateCallback",OwnerCancellation);Case("HintCannotEraseOrRebind",HintMonotonic);Case("DuplicateTerminalCallback",DuplicateTerminalCallback);Case("SixExactSchema1RecordsMigrateOnlyOnCommit",LegacyMigration);Case("ActualBoundServerTerminalParser",TerminalParser);Case("ActualStrictCatalogParser",CatalogParser);}catch(Exception e){report.errors.Add(e.GetType().Name+":"+e.Message);}finally{try{Directory.Delete(folder,true);}catch{report.errors.Add("SyntheticTempCleanupFailed");}}
            if(report.errors.Count==0)report.status="PASS_NATIVE_PAY_RECOVERY86";string native=Path.Combine(output,"Native");Directory.CreateDirectory(native);File.WriteAllText(Path.Combine(native,"PayRecovery86.json"),JsonUtility.ToJson(report,true));if(Application.isBatchMode)EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif

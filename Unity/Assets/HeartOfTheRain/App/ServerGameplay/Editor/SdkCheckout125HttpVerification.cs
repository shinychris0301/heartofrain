#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.ShopCheckout86;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.App.ServerGameplay.Editor {
    public static class SdkCheckout125HttpVerification {
        [Serializable] sealed class Connection {public string origin=null,playerId=null,token=null,verificationMode=null,fixtureId=null;public long appId=0;public bool productionEnabled=false,sandbox=false,syntheticSdkObservationsOnly=false;}
        [Serializable] sealed class Checkpoint {public string fixtureId,orderId,pendingOrderId,receiptId;public int coins;public long revision;}
        [Serializable] sealed class Report {
            public string status="FAIL_NATIVE_SDK_HTTP125",utc,unity,phase,ordinaryProfilesBefore,ordinaryProfilesAfter;
            public int checks,controlledSdkPurchases,controlledSdkLookups,controlledSdkAcknowledgements;
            public bool actualUnityHttp=true,actualBackendSQLite=true,actualEncryptedCas=true,syntheticSdk=true,actualProvider=false,actualAndroid=false,productionActivated=false;
            public string scope="Actual native UnityWebRequest/client/coordinator/encrypted journal against an isolated SDK125 FastAPI/SQLite fixture. Purchase observations and SDK acknowledgements are synthetic. No provider payment, APK, real account, production activation or local-profile grant.";
            public List<string> passed=new List<string>(),errors=new List<string>();
        }
        sealed class Job:IDisposable {
            readonly Stack<IEnumerator> stack=new Stack<IEnumerator>();AsyncOperation waiting;
            public Job(IEnumerator routine){stack.Push(routine);}
            public bool Tick(){if(waiting!=null&&!waiting.isDone)return true;waiting=null;for(int i=0;i<1024;i++){
                if(stack.Count==0)return false;var value=stack.Peek();if(!value.MoveNext()){(stack.Pop()as IDisposable)?.Dispose();continue;}
                if(value.Current is IEnumerator nested){stack.Push(nested);continue;}if(value.Current is AsyncOperation operation)waiting=operation;return true;
            }throw new InvalidOperationException("NestedHttpWorkBound");}
            public void Dispose(){while(stack.Count>0)try{(stack.Pop()as IDisposable)?.Dispose();}catch{}}
        }
        sealed class SyntheticStore:IPayStore {
            readonly PayRequest request;readonly int amount;public int purchases,lookups,acknowledgements;public Action beforeAcknowledge;
            public SyntheticStore(RuStoreServerOrder order){request=order.Request();amount=order.amountMinor;}
            public bool SdkCompiled=>true;public bool Configured=>true;
            public PayPurchase Observe(string status="CONFIRMED",string method="ONE_STEP",int? observedAmount=null)=>new PayPurchase(new PayLocator(new Guid(request.orderId).ToString("D"),Invoice(request.orderId),request.orderId,request.productId,1,true),request.developerPayload,status,method,acknowledgements>0?"ACKNOWLEDGED":"PENDING","CONSUMABLE_PRODUCT",observedAmount??amount,"RUB");
            public void GetPurchaseAvailability(Action<PayReply<PayAvailability>> done)=>done(PayReply<PayAvailability>.Ok(new PayAvailability(true)));
            public void GetProducts(string[] ids,Action<PayReply<PayProduct[]>> done)=>done(PayReply<PayProduct[]>.Ok(new[]{new PayProduct(request.productId,"synthetic RUB","RUB",amount)}));
            public void Purchase(PayRequest value,Action<PayReply<PayLocator>> done){Check(value.SameOrder(request),"SyntheticSdkReceivesFrozenServerCorrelation");purchases++;done(PayReply<PayLocator>.Ok(Observe().locator));}
            public void GetPurchase(string id,Action<PayReply<PayPurchase>> done){lookups++;done(PayReply<PayPurchase>.Ok(Observe()));}
            public void GetPurchases(Action<PayReply<PayPurchase[]>> done){lookups++;done(PayReply<PayPurchase[]>.Ok(new[]{Observe()}));}
            public void ConfirmTwoStep(PayRequest r,PayPurchase p,PayCaptureAuthorization a,Action<PayReply<PayAvailability>> done)=>done(PayReply<PayAvailability>.Fail("CaptureNotExercised"));
            public void Acknowledge(PayRequest r,PayPurchase p,PayDeliveryReceipt receipt,Action<PayReply<PayAvailability>> done){Check(receipt.Matches(r,p),"SdkAckRequiresDurableMatchedServerCredit");beforeAcknowledge?.Invoke();acknowledgements++;done(PayReply<PayAvailability>.Ok(new PayAvailability(true)));}
        }
        static Connection connection;static Report report;static Job main;static readonly List<Job> jobs=new List<Job>();static readonly Queue<IEnumerator> scheduled=new Queue<IEnumerator>();
        static string output,checkpoint,temporary;static double deadline;
        static void Check(bool condition,string label){report.checks++;if(!condition)throw new InvalidOperationException(label);report.passed.Add(label);}
        static string Invoice(string order)=>(125000000000000L+Convert.ToInt64(order.Substring(0,12),16)).ToString(System.Globalization.CultureInfo.InvariantCulture);
        static void Schedule(IEnumerator value)=>scheduled.Enqueue(value);
        static RuStoreBackendClient Client(string mode=CommerceVerification125.SdkClientReported)=>new RuStoreBackendClient(connection.origin,connection.token,connection.playerId,true,true,Schedule,false,connection.appId,mode);
        static IEnumerator Await<T>(Action<Action<PayReply<T>>> start,Action<T> receive,string label)where T:class{PayReply<T> reply=null;start(value=>reply=value);while(reply==null)yield return null;Check(reply.Succeeded,label+":"+(reply.error?.code??"OK"));receive(reply.value);}
        static IEnumerator Denied<T>(Action<Action<PayReply<T>>> start,string label)where T:class{PayReply<T> reply=null;start(value=>reply=value);while(reply==null)yield return null;Check(!reply.Succeeded,label);}
        static string ProfileDigest(){string path=Path.Combine(Application.persistentDataPath,"Profiles");if(!Directory.Exists(path))return IdentityProtocol82.Sha("absent");return IdentityProtocol82.Sha(string.Join("\n",Directory.GetFiles(path,"*",SearchOption.AllDirectories).OrderBy(p=>p,StringComparer.Ordinal).Select(p=>p.Substring(path.Length)+":"+IdentityProtocol82.Sha(File.ReadAllBytes(p)))));}
        static IEnumerator Initial(){
            using(var client=Client())using(var vault=new EditorEphemeralIdentity82()){
                RuStoreServerWallet before=null,after=null;RuStoreServerCatalog86 catalog=null;RuStoreServerOrder order=null;
                yield return Await<RuStoreServerWallet>(client.GetWallet,v=>before=v,"FreshActualManagedWallet");Check(client.WalletReady,"InitializedFixtureWalletReady");
                yield return Await<RuStoreServerCatalog86>(client.GetCatalog,v=>catalog=v,"ActualSdkCatalogHttp");Check(catalog.Verification==CommerceVerificationMode125.SdkClientReported&&catalog.appId==connection.appId,"ActualCatalogModeAndAppBound");
                string command=Guid.NewGuid().ToString("N");yield return Await<RuStoreServerOrder>(done=>client.CreateOrder(command,"coins-1000",done),v=>order=v,"CreateActualFrozenSdkOrder");
                Check(order.creationCommandId==command&&order.Verification==CommerceVerificationMode125.SdkClientReported,"ActualCreatorAndVerificationModeFrozen");
                var sdk=new SyntheticStore(order);string journalPath=Path.Combine(temporary,"checkout.sealed");
                using(var journal=new ProtectedCheckoutJournal86(vault.CreateStore(journalPath),connection.origin,connection.playerId,false,CommerceVerification125.SdkClientReported)){
                    journal.Read();journal.Save(new CheckoutDocument86{verificationMode=CommerceVerification125.SdkClientReported,origin=connection.origin,player=connection.playerId,phase="Ordered",commandId=command,productId=order.productId,amountLabel="synthetic RUB",product=CheckoutCatalogRules86.FrozenProduct(order),hasOrder=true,order=order});
                    sdk.beforeAcknowledge=()=>{var saved=journal.Read();Check(saved.hasPayment&&saved.payment.phase=="AcknowledgementPending"&&saved.payment.hasReceipt,"EncryptedDeliveryReceiptDurableBeforeSdkAcknowledgement");};
                    var coordinator=new PayDeliveryCoordinator(sdk,client,journal);PayReply<PayPending> delivered=null;coordinator.Begin(order.Request(),v=>delivered=v);while(delivered==null)yield return null;
                    Check(delivered.Succeeded&&delivered.value.phase=="Acknowledged","ActualHttpCreditThenControlledSdkAcknowledgement");Check(sdk.purchases==1&&sdk.lookups==1&&sdk.acknowledgements==1,"OneSdkDispatchFreshGetPurchaseThenAck");
                    PayDeliveryReceipt replay=null;yield return Await<PayDeliveryReceipt>(done=>client.Reconcile(order.Request(),sdk.Observe(),done),v=>replay=v,"ActualPostAcknowledgementSdkReport");
                    RuStoreServerOrder canonical=null;yield return Await<RuStoreServerOrder>(done=>client.GetOrder(order.orderId,done),v=>canonical=v,"ActualServerAcknowledgementReadback");
                    Check(canonical.deliveryAcknowledgement=="Acknowledged"&&canonical.credit.receiptId==delivered.value.receipt.receiptId&&canonical.credit.Verification==CommerceVerificationMode125.SdkClientReported,"DurableSdkAuditAndServerAckAgree");
                    yield return Await<RuStoreServerWallet>(client.GetWallet,v=>after=v,"AuthoritativeWalletRefreshAfterDelivery");
                    Check(after.coins==before.coins+order.grant.coins&&after.stars==before.stars&&after.tools.SequenceEqual(before.tools)&&after.starting.SequenceEqual(before.starting),"ExactlyOneActualWalletCoinGrantNoLocalProjection");
                    long revision=after.revision;yield return Await<PayDeliveryReceipt>(done=>client.Reconcile(order.Request(),sdk.Observe(),done),v=>replay=v,"DuplicateSdkReportReturnsCurrentReceipt");
                    yield return Await<RuStoreServerWallet>(client.GetWallet,v=>after=v,"WalletAfterDuplicateSdkReport");Check(after.revision==revision&&after.coins==before.coins+order.coins,"DuplicateReportCannotCreditAgain");
                    var settled=journal.Read();settled.phase="Settled";settled.order=canonical;journal.Save(settled);Check(!journal.Read().Pending,"ManagedJournalSettlesOnlyAfterAuthoritativeRefresh");
                    report.controlledSdkPurchases=sdk.purchases;report.controlledSdkLookups=sdk.lookups;report.controlledSdkAcknowledgements=sdk.acknowledgements;
                }
                RuStoreServerOrder terminal=null;yield return Await<RuStoreServerOrder>(done=>client.CreateOrder(Guid.NewGuid().ToString("N"),"coins-1000",done),v=>terminal=v,"CreateSecondOrderForMismatchAndTerminal");var terminalSdk=new SyntheticStore(terminal);
                yield return Denied<PayDeliveryReceipt>(done=>client.Reconcile(terminal.Request(),terminalSdk.Observe(observedAmount:terminal.amountMinor+1),done),"BackendRejectsMismatchedActualReportedPrice");
                yield return Await<RuStoreServerWallet>(client.GetWallet,v=>after=v,"RefreshAfterRejectedReport");Check(after.coins==before.coins+order.coins,"RejectedReportHasNoGrant");
                PayTerminalReceipt closed=null;yield return Await<PayTerminalReceipt>(done=>client.ResolveTerminal(terminal.Request(),terminalSdk.Observe("CANCELLED","UNDEFINED"),done),v=>closed=v,"ActualUndefinedMethodCancellationReport");Check(closed.noCredit&&closed.state=="Cancelled","TerminalSdkReportDurablyClosesWithoutCredit");
                RuStoreServerOrder pending=null;yield return Await<RuStoreServerOrder>(done=>client.CreateOrder(Guid.NewGuid().ToString("N"),"coins-1000",done),v=>pending=v,"CreatePendingSdkOrder");var pendingSdk=new SyntheticStore(pending);
                yield return Denied<PayDeliveryReceipt>(done=>client.Reconcile(pending.Request(),pendingSdk.Observe("INVOICE_CREATED","UNDEFINED"),done),"PendingObservationCannotProduceDeliveryReceipt");
                yield return Await<RuStoreServerOrder>(done=>client.GetOrder(pending.orderId,done),v=>pending=v,"ReadNormalizedPendingSdkOrder");Check(pending.state=="Created"&&pending.credit==null,"ActualPendingStateRemainsRecoverableWithoutGrant");
                RuStorePendingOrders100 pendingPage=null;yield return Await<RuStorePendingOrders100>(done=>client.GetPendingOrders100(0,done),v=>pendingPage=v,"ActualSdkPendingDiscovery");Check(pendingPage.orders.Any(v=>v.orderId==pending.orderId),"PendingSdkOrderIncludedAfterActualHttpReport");
                yield return Await<RuStoreServerWallet>(client.GetWallet,v=>after=v,"FreshWalletBeforeRefundObservation");
                yield return Denied<PayDeliveryReceipt>(done=>client.Reconcile(order.Request(),sdk.Observe("REFUNDING"),done),"RefundObservationCannotReissueDelivery");
                yield return Await<RuStoreServerOrder>(done=>client.GetOrder(order.orderId,done),v=>order=v,"ActualRefundReviewReadback");
                yield return Await<RuStoreServerWallet>(client.GetWallet,v=>after=v,"ActualWalletRefundReviewReadback");Check(order.state=="RefundReview"&&after.refundReviewRequired&&!client.WalletReady&&after.coins==before.coins+order.coins,"RefundReviewBlocksNewAuthorityWithoutDuplicateOrSilentReversal");
                File.WriteAllText(checkpoint,JsonUtility.ToJson(new Checkpoint{fixtureId=connection.fixtureId,orderId=order.orderId,pendingOrderId=pending.orderId,receiptId=order.credit.receiptId,coins=after.coins,revision=after.revision}),new UTF8Encoding(false));
                using(var legacy=Client(CommerceVerification125.ProviderApi))yield return Denied<RuStoreServerCatalog86>(legacy.GetCatalog,"ActualApiClientRejectsSdkModeCatalog");
            }
        }
        static IEnumerator Resume(){
            var prior=JsonUtility.FromJson<Checkpoint>(File.ReadAllText(checkpoint));Check(prior.fixtureId==connection.fixtureId,"SameOwnedFixtureAfterActualBackendRestart");
            using(var client=Client()){
                RuStoreServerWallet wallet=null;RuStoreServerOrder order=null,pending=null;
                yield return Await<RuStoreServerWallet>(client.GetWallet,v=>wallet=v,"WalletSurvivesActualServerRestart");
                yield return Await<RuStoreServerOrder>(done=>client.GetOrder(prior.orderId,done),v=>order=v,"CreditedOrderSurvivesActualServerRestart");
                yield return Await<RuStoreServerOrder>(done=>client.GetOrder(prior.pendingOrderId,done),v=>pending=v,"PendingOrderSurvivesActualServerRestart");
                Check(wallet.coins==prior.coins&&wallet.revision==prior.revision&&wallet.refundReviewRequired&&!client.WalletReady,"RestartPreservesExactWalletAndReviewBlock");
                Check(order.state=="RefundReview"&&order.credit.receiptId==prior.receiptId&&order.Verification==CommerceVerificationMode125.SdkClientReported&&pending.state=="Created"&&pending.credit==null,"RestartPreservesModeBoundCreditAndUnresolvedPurchase");
                yield return Denied<RuStoreServerOrder>(done=>client.CreateOrder(Guid.NewGuid().ToString("N"),"coins-1000",done),"ReviewBlockedWalletCannotDispatchNewCheckout");
            }
        }
        public static void Run(){
            string descriptor=Environment.GetEnvironmentVariable("HOTR_REVIEW125_HTTP_DESCRIPTOR"),project=Environment.GetEnvironmentVariable("HOTR_REVIEW125_ISOLATED_PROJECT");output=Environment.GetEnvironmentVariable("HOTR_REVIEW125_OUT");checkpoint=Environment.GetEnvironmentVariable("HOTR_REVIEW125_HTTP_CHECKPOINT");string phase=Environment.GetEnvironmentVariable("HOTR_REVIEW125_HTTP_PHASE");
            if(string.IsNullOrEmpty(project)||Path.GetFullPath(".")!=Path.GetFullPath(project)||string.IsNullOrEmpty(descriptor)||string.IsNullOrEmpty(checkpoint)||string.IsNullOrEmpty(output)||phase!="initial"&&phase!="resume")throw new InvalidOperationException("ExplicitPrivateHttpFixtureRequired");
            connection=JsonUtility.FromJson<Connection>(File.ReadAllText(descriptor));Uri uri;
            if(connection==null||!Uri.TryCreate(connection.origin,UriKind.Absolute,out uri)||!uri.IsLoopback||connection.appId!=123||connection.verificationMode!=CommerceVerification125.SdkClientReported||connection.productionEnabled||!connection.sandbox||!connection.syntheticSdkObservationsOnly)throw new InvalidOperationException("SyntheticLoopbackFixtureRequired");
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,phase=phase,ordinaryProfilesBefore=ProfileDigest()};temporary=Path.GetFullPath(Path.Combine("../.verification-cache/Launch82/SdkHttp125",Guid.NewGuid().ToString("N")));Directory.CreateDirectory(temporary);
            deadline=EditorApplication.timeSinceStartup+180;main=new Job(phase=="resume"?Resume():Initial());EditorApplication.update+=Tick;
        }
        static void Tick(){try{if(EditorApplication.timeSinceStartup>deadline)throw new TimeoutException();while(scheduled.Count>0)jobs.Add(new Job(scheduled.Dequeue()));for(int i=jobs.Count-1;i>=0;i--)if(!jobs[i].Tick()){jobs[i].Dispose();jobs.RemoveAt(i);}if(!main.Tick())Finish();}catch(Exception error){report.errors.Add(error is InvalidOperationException?error.Message:error.GetType().Name);Finish();}}
        static void Finish(){
            EditorApplication.update-=Tick;main?.Dispose();foreach(var job in jobs)job.Dispose();jobs.Clear();scheduled.Clear();report.ordinaryProfilesAfter=ProfileDigest();if(report.ordinaryProfilesAfter!=report.ordinaryProfilesBefore)report.errors.Add("OrdinaryProfilesChanged");
            if(Directory.Exists(temporary))Directory.Delete(temporary,true);report.status=report.errors.Count==0?"PASS_NATIVE_SDK_HTTP125":"FAIL_NATIVE_SDK_HTTP125";Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"SdkHttp125.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));connection=null;EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif

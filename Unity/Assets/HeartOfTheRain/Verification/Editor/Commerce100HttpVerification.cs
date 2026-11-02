#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.ServerRewards;
using HeartOfTheRain.App.ShopCheckout86;

// TEMPLATE: the native owner copies this into an Editor folder only after the
// runtime/input freeze. This file itself is outside Assets and is not imported.
namespace HeartOfTheRain.Verification {
    public static class Commerce100HttpVerification {
        [Serializable] sealed class Credential {public string name=null,playerId=null,token=null;}
        [Serializable] sealed class Configuration {
            public string runId=null,origin=null,providerControlPath=null,catalogPath=null;
            public Credential[] players=null;public int trustedPendingSeedCount=0;
        }
        [Serializable] sealed class OrderControl {
            public string orderId=null,status="CONFIRMED",acknowledgement="PENDING";
            public bool unavailable=false,mismatchAmount=false;
        }
        [Serializable] sealed class Control {
            public OrderControl[] orders=new OrderControl[0];public int dropNextReconcile;
            public bool legacyWire;public string catalogMode="";
        }
        [Serializable] sealed class Product {
            public string id=null,storeProductId=null,currency=null;public int coins=0,amountMinor=0;
        }
        [Serializable] sealed class Catalog {public Product[] products=null;}
        [Serializable] sealed class Report {
            public string status="FAIL_NATIVE_COMMERCE_HTTP100",utc,unity,runId;
            public string scope="Actual Editor UnityWebRequest, CheckoutFlow/shared production adapter, encrypted CAS and isolated FastAPI/SQLite. SDK callbacks, publisher invoices and operator-provisioned guests/backlog are controlled. No live SDK/provider, real money, Android, ordinary account startup or production acceptance.";
            public bool actualHttp=true,actualBackendSQLite=true,actualEncryptedCas=true;
            public bool controlledSdk=true,controlledPublisher=true,android=false,productionEnabled=false;
            public string profilesBefore,profilesAfter;
            public int checks,cases,pagedOrders,pages,sdkPurchases,sdkAcknowledgements,duplicateCallbacks;
            public List<string> passed=new List<string>(),errors=new List<string>(),diagnostics=new List<string>();
        }
        sealed class Job:IDisposable {
            readonly Stack<IEnumerator> stack=new Stack<IEnumerator>();AsyncOperation waiting;
            public Job(IEnumerator value){stack.Push(value);}
            public bool Tick(){
                if(waiting!=null&&!waiting.isDone)return true;waiting=null;
                for(int n=0;n<1024;n++){
                    if(stack.Count==0)return false;
                    var current=stack.Peek();if(!current.MoveNext()){(stack.Pop()as IDisposable)?.Dispose();continue;}
                    if(current.Current is IEnumerator nested){stack.Push(nested);continue;}
                    if(current.Current is AsyncOperation operation)waiting=operation;
                    return true;
                }
                throw new InvalidOperationException("NestedRoutineBound100");
            }
            public void Dispose(){while(stack.Count>0)try{(stack.Pop()as IDisposable)?.Dispose();}catch{}}
        }
        static Configuration config;static Report report;static Job main;
        static readonly List<Job> jobs=new List<Job>();static readonly Queue<IEnumerator> scheduled=new Queue<IEnumerator>();
        static string directory,output,stage,completedOrder;static double deadline;
        static void Schedule(IEnumerator routine){scheduled.Enqueue(routine);}
        static string NewId()=>Guid.NewGuid().ToString("N");
        static string SafeCode(string value)=>value==null?"NoError":Regex.IsMatch(value,"\\A[A-Za-z0-9_.-]{1,128}\\z")?value:"Unclassified";
        static void Check(bool value,string message){report.checks++;if(!value)throw new InvalidOperationException(message);report.passed.Add(message);}
        static Credential Player(string name)=>config.players.Single(p=>p.name==name);
        static Control ReadControl()=>JsonUtility.FromJson<Control>(File.ReadAllText(config.providerControlPath,Encoding.UTF8));
        static void WriteControl(Control value){
            string temporary=config.providerControlPath+".native-"+NewId()+".tmp";
            try{File.WriteAllText(temporary,JsonUtility.ToJson(value),new UTF8Encoding(false));File.Replace(temporary,config.providerControlPath,null);}
            finally{if(File.Exists(temporary))File.Delete(temporary);}
        }
        static void ChangeControl(Action<Control> change){var value=ReadControl();change(value);WriteControl(value);}
        static OrderControl Behavior(string id){return ReadControl().orders.FirstOrDefault(p=>p.orderId==id)??new OrderControl{orderId=id};}
        static void SetOrder(string id,Action<OrderControl> change){ChangeControl(value=>{var rows=value.orders.ToList();var row=rows.FirstOrDefault(p=>p.orderId==id);if(row==null){row=new OrderControl{orderId=id};rows.Add(row);}change(row);value.orders=rows.ToArray();});}
        static string Invoice(string id)=>(810000000000000L+Convert.ToInt64(id.Substring(0,12),16)).ToString(CultureInfo.InvariantCulture);
        static string PurchaseId(string id)=>Guid.ParseExact(id,"N").ToString("D");
        static string ProfileDigest(){
            string root=Path.Combine(Application.persistentDataPath,"Profiles");if(!Directory.Exists(root))return IdentityProtocol82.Sha("absent");
            return IdentityProtocol82.Sha(string.Join("\n",Directory.GetFiles(root,"*",SearchOption.AllDirectories).OrderBy(p=>p,StringComparer.Ordinal).Select(p=>p.Substring(root.Length)+":"+IdentityProtocol82.Sha(File.ReadAllBytes(p)))));
        }
        static IEnumerator Await<T>(Action<Action<PayReply<T>>> send,Action<T> receive,string label) where T:class {
            PayReply<T> reply=null;send(value=>reply=value);while(reply==null)yield return null;
            Check(reply.Succeeded,label);receive(reply.value);
        }
        static RuStoreBackendClient Client(Credential player)=>new RuStoreBackendClient(config.origin,player.token,player.playerId,true,true,Schedule);
        sealed class Store:IPayStore {
            readonly Dictionary<string,PayRequest> known=new Dictionary<string,PayRequest>(StringComparer.Ordinal);
            public bool unknown,recoverable=true,duplicate;public int purchases,acknowledgements,lookups,productRequests,productReturned;
            public Action<PayRequest> beforeCallback;readonly Product[] products;
            public Store(){products=JsonUtility.FromJson<Catalog>(File.ReadAllText(config.catalogPath,Encoding.UTF8)).products;}
            public bool SdkCompiled=>true;public bool Configured=>true;
            public void Seed(RuStoreServerOrder order){known[PurchaseId(order.orderId)]=order.Request();}
            PayLocator Locator(PayRequest request)=>new PayLocator(PurchaseId(request.orderId),Invoice(request.orderId),request.orderId,request.productId,1,true);
            PayPurchase Purchase(PayRequest request){var row=Behavior(request.orderId);return new PayPurchase(Locator(request),request.developerPayload,row.status,"ONE_STEP",row.acknowledgement=="ACKNOWLEDGED"?"ACKNOWLEDGED":"NOT_ACKNOWLEDGED");}
            public void GetPurchaseAvailability(Action<PayReply<PayAvailability>> done)=>done(PayReply<PayAvailability>.Ok(new PayAvailability(true)));
            public void GetProducts(string[] ids,Action<PayReply<PayProduct[]>> done){productRequests=ids.Length;var quoted=products.Where(p=>ids.Contains(p.storeProductId)).Select(p=>new PayProduct(p.storeProductId,(p.amountMinor/100).ToString(CultureInfo.InvariantCulture)+" RUB (controlled SDK)",p.currency,p.amountMinor)).ToArray();productReturned=quoted.Length;done(PayReply<PayProduct[]>.Ok(quoted));}
            public void Purchase(PayRequest request,Action<PayReply<PayLocator>> done){
                purchases++;known[PurchaseId(request.orderId)]=request;beforeCallback?.Invoke(request);
                if(unknown){done(PayReply<PayLocator>.Fail("ControlledSdkOutcomeUnknown",true));return;}
                var reply=PayReply<PayLocator>.Ok(Locator(request));done(reply);if(duplicate){report.duplicateCallbacks++;done(reply);}
            }
            public void GetPurchase(string id,Action<PayReply<PayPurchase>> done){lookups++;done(known.TryGetValue(id,out var request)?PayReply<PayPurchase>.Ok(Purchase(request)):PayReply<PayPurchase>.Fail("ControlledSdkPurchaseNotFound",true));}
            public void GetPurchases(Action<PayReply<PayPurchase[]>> done){lookups++;done(PayReply<PayPurchase[]>.Ok(recoverable?known.Values.Select(Purchase).ToArray():new PayPurchase[0]));}
            public void ConfirmTwoStep(PayRequest request,PayPurchase purchase,PayCaptureAuthorization authorization,Action<PayReply<PayAvailability>> done)=>done(PayReply<PayAvailability>.Fail("ControlledOneStepOnly"));
            public void Acknowledge(PayRequest request,PayPurchase purchase,PayDeliveryReceipt receipt,Action<PayReply<PayAvailability>> done){acknowledgements++;SetOrder(request.orderId,row=>row.acknowledgement="ACKNOWLEDGED");done(PayReply<PayAvailability>.Ok(new PayAvailability(true)));}
        }
        sealed class Harness:IDisposable {
            public readonly Credential credential;public readonly Store store=new Store();readonly EditorEphemeralIdentity82 vault=new EditorEphemeralIdentity82();
            readonly string path;public readonly RewardPresentationJournal presentation;public ShopCheckoutFlow86 flow;
            public RuStoreServerWallet wallet;public int refreshes,presentationCalls,authorizations,journalFactories;public bool valid=true,presentationFault,lastWalletReady;
            public Harness(string name){credential=Player(name);path=Path.GetFullPath(Path.Combine("../.verification-cache/Launch82/Commerce100Http",config.runId,name,"checkout.sealed"));presentation=new RewardPresentationJournal(Path.Combine(directory,name,"presentation.json"),config.origin,credential.playerId);Open();}
            public ProtectedCheckoutJournal86 Journal(){journalFactories++;return new ProtectedCheckoutJournal86(vault.CreateStore(path),config.origin,credential.playerId);}
            public IEnumerator RefreshWallet(Action<bool,string> done){
                refreshes++;PayReply<RuStoreServerWallet> reply=null;
                using(var client=Client(credential)){client.GetWallet(value=>reply=value);while(reply==null)yield return null;}
                if(reply.Succeeded)wallet=reply.value;done(reply.Succeeded,reply.error?.code);
            }
            IEnumerator Authorize(Action<CheckoutAccess86,string> done){
                var client=Client(credential);PayReply<RuStoreServerWallet> reply=null;client.GetWallet(value=>reply=value);while(reply==null)yield return null;
                if(!valid||!reply.Succeeded){client.Dispose();done(null,"ControlledAccessUnavailable");yield break;}
                wallet=reply.value;authorizations++;lastWalletReady=client.WalletReady;done(new CheckoutAccess86(config.origin,credential.playerId,1,new CheckoutBackend100(client),()=>valid),null);
            }
            public void Open(){flow?.Dispose();flow=new ShopCheckoutFlow86(new CheckoutConfiguration86{version=1,enabled=true,sandbox=true,consoleAppId="123456"},Authorize,RefreshWallet,access=>Journal(),authority=>store,(access,order)=>{
                if(presentationFault){presentationFault=false;throw new IOException("ControlledPresentationWriteFailure");}
                presentation.Enqueue("commerce",order.credit.receiptId,order.credit.grant);presentationCalls++;
            });flow.SetAuthorityDispatcher(Schedule);}
            public IEnumerator Run(IEnumerator routine){yield return flow.Guard(routine);}
            public void SeedCreating(string command,RuStoreServerOrder frozen){using(var saved=Journal()){
                var document=saved.Read();document.phase="Creating";document.commandId=command;document.productId=frozen.productId;document.product=CheckoutCatalogRules86.FrozenProduct(frozen);document.amountLabel="Controlled frozen recovery";saved.Save(document);
            }}
            public void ForgetLocalJournal(){flow.Dispose();File.Delete(path);Open();}
            public void Dispose(){flow.Dispose();vault.Dispose();report.sdkPurchases+=store.purchases;report.sdkAcknowledgements+=store.acknowledgements;}
        }
        static void WalletGrant(RuStoreServerWallet before,RuStoreServerWallet after,RewardGrant grant,string name){
            Check(after.coins==before.coins+grant.coins&&after.stars==before.stars+grant.stars&&after.lives==before.lives&&after.completed==before.completed,name+" exact coins/stars/lives/progression");
            for(int i=0;i<4;i++)Check(after.starting[i]==before.starting[i]+grant.starting[i]&&after.tools[i]==before.tools[i]+grant.tools[i],name+" exact starting/tool slot "+i);
        }
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};
            try{
                string path=Environment.GetEnvironmentVariable("HOTR_COMMERCE100_HTTP_CONFIG");string allowed=Path.GetFullPath("../.verification-cache/Review100/CommerceHTTP/");
                if(string.IsNullOrEmpty(path)||!Path.GetFullPath(path).StartsWith(allowed,StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("PrivateFixtureRequired100");
                config=JsonUtility.FromJson<Configuration>(File.ReadAllText(path,Encoding.UTF8));
                if(config==null||!Regex.IsMatch(config.runId??"","\\A[0-9a-f]{32}\\z")||!RuStoreBackendClient.IsAllowedOrigin(config.origin,true)||!new Uri(config.origin).IsLoopback||config.players==null||config.players.Length!=10||config.players.Any(p=>!Regex.IsMatch(p.playerId??"","\\A[0-9a-f]{32}\\z")||!Regex.IsMatch(p.token??"","\\A[A-Za-z0-9_-]{43}\\z")))throw new InvalidOperationException("PrivateFixtureBindingInvalid100");
                if(new[]{config.providerControlPath,config.catalogPath}.Any(p=>!Path.GetFullPath(p).StartsWith(allowed,StringComparison.OrdinalIgnoreCase)))throw new InvalidOperationException("PrivateOperatorControlRequired100");
                output=Environment.GetEnvironmentVariable("HOTR_REVIEW100_OUT");if(string.IsNullOrEmpty(output)||!Path.IsPathRooted(output))throw new InvalidOperationException("ExplicitOutputRequired100");
                report.runId=config.runId;report.profilesBefore=ProfileDigest();directory=Path.Combine(allowed,config.runId,"NativeClient");Directory.CreateDirectory(directory);
                deadline=EditorApplication.timeSinceStartup+360;main=new Job(Checks());EditorApplication.update+=Tick;
            }catch(Exception error){report.errors.Add("Configuration:"+error.GetType().Name);Finish();}
        }
        static void Tick(){
            try{
                if(EditorApplication.timeSinceStartup>deadline)throw new TimeoutException("NativeHttpDeadline100");
                while(scheduled.Count>0)jobs.Add(new Job(scheduled.Dequeue()));
                for(int i=jobs.Count-1;i>=0;i--)if(!jobs[i].Tick()){jobs[i].Dispose();jobs.RemoveAt(i);}
                if(!main.Tick())Finish();
            }catch(Exception error){report.errors.Add((stage??"Unknown")+":"+error.GetType().Name+(error is InvalidOperationException?":"+error.Message:""));Finish();}
        }
        static IEnumerator Checks(){
            yield return Full();yield return Unknown();yield return Discovery();yield return Frozen();yield return Cancelled();yield return Legacy();yield return Ownership();yield return Paging();yield return Creator();yield return Daily();
        }
        static IEnumerator Full(){
            stage="FullGrant";report.cases++;
            using(var h=new Harness("full")){
                bool fresh=false;yield return h.RefreshWallet((ok,error)=>fresh=ok);Check(fresh,"Full grant has actual initial wallet");var before=h.wallet;h.store.duplicate=true;
                yield return h.Run(h.flow.Buy("wellkeeper"));
                report.diagnostics.Add("Full authorizations="+h.authorizations+" walletReady="+h.lastWalletReady+" journalFactories="+h.journalFactories+" sdkRequested="+h.store.productRequests+" sdkReturned="+h.store.productReturned+" pending="+h.flow.Pending+" error="+SafeCode(h.flow.Error));
                Check(h.flow.Error==null,"Full explicit purchase error_"+SafeCode(h.flow.Error));Check(h.flow.Credited&&!h.flow.Pending&&h.store.purchases==1&&h.store.acknowledgements==1,"Duplicate SDK callback commits and acknowledges one purchase");
                WalletGrant(before,h.wallet,CheckoutCatalogRules86.ApprovedGrant("wellkeeper"),"Wellkeeper");RewardGrant frozen;string receiptId;
                using(var saved=h.Journal()){var doc=saved.Read();completedOrder=doc.order.orderId;frozen=doc.product.grant.Copy();receiptId=doc.payment.receiptId;}
                using(var client=Client(h.credential)){RuStoreServerOrder canonical=null;yield return Await<RuStoreServerOrder>(done=>client.GetOrder(completedOrder,done),v=>canonical=v,"Actual completed order re-read independently");Check(canonical.credit!=null&&CommerceTerms100.Same(canonical.credit.grant,frozen)&&canonical.credit.receiptId==receiptId&&canonical.deliveryAcknowledgement=="Acknowledged","Actual server order/credit agrees with frozen journal terms and payment receipt");}
                var notification=h.presentation.Peek();Check(notification!=null&&notification.channel=="commerce"&&notification.grant.tools.All(n=>n==1),"Verified full receipt queued before settlement");long revision=h.wallet.revision;yield return h.Run(h.flow.Recover());Check(h.wallet.revision==revision&&h.store.purchases==1,"Settled recovery cannot credit or dispatch again");
            }
        }
        static IEnumerator Unknown(){
            stage="Committed503";report.cases++;
            using(var h=new Harness("unknown")){
                bool fresh=false;yield return h.RefreshWallet((ok,error)=>fresh=ok);Check(fresh,"Unknown outcome has initial actual wallet");var before=h.wallet;ChangeControl(c=>c.dropNextReconcile=1);
                yield return h.Run(h.flow.Buy("wellkeeper"));Check(h.flow.Pending&&!h.flow.Credited&&h.store.purchases==1,"Postcommit503 retains exact protected purchase outbox");
                yield return h.RefreshWallet((ok,error)=>fresh=ok);WalletGrant(before,h.wallet,CheckoutCatalogRules86.ApprovedGrant("wellkeeper"),"Committed despite lost response");
                long revision=h.wallet.revision;h.Open();yield return h.Run(h.flow.Recover());Check(h.flow.Credited&&!h.flow.Pending&&h.store.purchases==1&&h.wallet.revision==revision,"Recreated flow reconciles one committed full grant without rebuy");
            }
        }
        static IEnumerator Discovery(){
            stage="ServerPendingDiscovery";report.cases++;
            using(var h=new Harness("discovery")){
                bool fresh=false;yield return h.RefreshWallet((ok,error)=>fresh=ok);Check(fresh,"Pending discovery has actual initial wallet");var before=h.wallet;RuStoreServerOrder order=null;
                using(var client=Client(h.credential)){yield return Await<RuStoreServerWallet>(client.GetWallet,v=>{},"Pending creator wallet ready");yield return Await<RuStoreServerOrder>(done=>client.CreateOrder(NewId(),"wellkeeper",done),v=>order=v,"Trusted second-device order created through real HTTP");}
                h.store.Seed(order);h.store.recoverable=false;yield return h.Run(h.flow.Refresh());Check(h.flow.Pending&&h.store.purchases==0,"Server pending order adopted without SDK purchase");
                h.ForgetLocalJournal();yield return h.Run(h.flow.Recover());Check(h.flow.Pending&&h.store.purchases==0,"Missing local journal and empty SDK list remain lookup-only");
                h.store.recoverable=true;yield return h.Run(h.flow.Recover());Check(h.flow.Credited&&!h.flow.Pending&&h.store.purchases==0,"Later controlled SDK listing recovers existing order without new charge");WalletGrant(before,h.wallet,order.grant,"Discovered frozen grant");
            }
        }
        static IEnumerator Frozen(){
            stage="FrozenCatalog";report.cases++;
            try{using(var h=new Harness("frozen")){
                bool fresh=false;yield return h.RefreshWallet((ok,error)=>fresh=ok);Check(fresh,"Frozen order has actual initial wallet");var before=h.wallet;h.store.unknown=true;h.store.recoverable=false;
                yield return h.Run(h.flow.Buy("rainlight"));Check(h.flow.Pending&&!h.flow.Credited&&h.store.purchases==1,"Unknown retired bundle keeps frozen outbox");
                RewardGrant frozen;int amount;using(var saved=h.Journal()){var doc=saved.Read();frozen=doc.product.grant.Copy();amount=doc.product.amountMinor;}
                ChangeControl(c=>c.catalogMode="retire-rainlight");h.store.recoverable=true;h.Open();yield return h.Run(h.flow.Recover());
                Check(h.flow.Credited&&!h.flow.Pending&&h.store.purchases==1,"Retired bundle recovery needs no current catalog quote");WalletGrant(before,h.wallet,frozen,"Retired immutable grant");using(var saved=h.Journal())Check(saved.Read().order.amountMinor==amount,"Changed catalog preserves original paid amount");
            }}finally{ChangeControl(c=>c.catalogMode="");}
        }
        static IEnumerator Cancelled(){
            stage="Cancellation";report.cases++;
            using(var h=new Harness("cancel")){
                bool fresh=false;yield return h.RefreshWallet((ok,error)=>fresh=ok);Check(fresh,"Cancellation has initial wallet");var before=h.wallet;
                h.store.beforeCallback=request=>SetOrder(request.orderId,row=>row.status="CANCELLED");yield return h.Run(h.flow.Buy("wellkeeper"));
                Check(!h.flow.Pending&&!h.flow.Credited&&h.store.acknowledgements==0&&h.flow.Error=="CheckoutResolvedWithoutDelivery","Verified cancellation settles without credit or SDK acknowledgement");WalletGrant(before,h.wallet,new RewardGrant(),"Cancelled order");
            }
        }
        static IEnumerator Legacy(){
            stage="LegacyWire";report.cases++;
            try{ChangeControl(c=>c.legacyWire=true);using(var h=new Harness("legacy")){
                bool fresh=false;yield return h.RefreshWallet((ok,error)=>fresh=ok);Check(fresh,"Legacy wire has actual initial wallet");var before=h.wallet;
                yield return h.Run(h.flow.Buy("coins-1000"));Check(h.flow.Credited&&!h.flow.Pending&&h.store.purchases==1,"Six-coin additive wire fallback remains compatible");WalletGrant(before,h.wallet,new RewardGrant{coins=1000},"Legacy coin receipt");
            }}finally{ChangeControl(c=>c.legacyWire=false);}
        }
        static IEnumerator Ownership(){
            stage="ForeignOrder";report.cases++;string order=completedOrder;Check(!string.IsNullOrEmpty(order),"Foreign read uses recorded original order identity");
            using(var client=Client(Player("foreign"))){PayReply<RuStoreServerOrder> denied=null;client.GetOrder(order,r=>denied=r);while(denied==null)yield return null;Check(!denied.Succeeded,"Another player's credential cannot read or adopt full grant order");}
        }
        static IEnumerator Paging(){
            stage="PagedPending";report.cases++;
            using(var client=Client(Player("paging"))){long cursor=0;var ids=new HashSet<string>(StringComparer.Ordinal);bool more;
                do{RuStorePendingOrders100 page=null;yield return Await<RuStorePendingOrders100>(done=>client.GetPendingOrders100(cursor,done),v=>page=v,"Bounded pending page parsed by actual production client");
                    report.pages++;foreach(var order in page.orders){Check(order.playerId==Player("paging").playerId&&ids.Add(order.orderId)&&order.grant!=null,"Paged full order remains unique and player bound");}more=page.hasMore;Check(!more||page.nextCursor>cursor,"Paged cursor advances truthfully");cursor=page.nextCursor;Check(report.pages<=101,"Pending pagination terminates within seed count");
                }while(more);report.pagedOrders=ids.Count;Check(ids.Count==config.trustedPendingSeedCount&&ids.Count==101&&report.pages>1,"All101 operator-seeded orders survive bounded multi-page actual HTTP");}
        }
        static IEnumerator Creator(){
            stage="CreatorOwnership";report.cases++;
            using(var h=new Harness("creator")){
                RuStoreServerOrder creator=null,follower=null;string first=NewId(),second=NewId();
                using(var client=Client(h.credential)){yield return Await<RuStoreServerWallet>(client.GetWallet,v=>{},"Creator wallet initialized");yield return Await<RuStoreServerOrder>(done=>client.CreateOrder(first,"wellkeeper",done),v=>creator=v,"First creator reservation made");}
                using(var client=Client(h.credential)){yield return Await<RuStoreServerWallet>(client.GetWallet,v=>{},"Follower wallet verified independently");yield return Await<RuStoreServerOrder>(done=>client.CreateOrder(second,"wellkeeper",done),v=>follower=v,"Follower obtains same reserved order");}
                Check(creator.orderId==follower.orderId&&creator.creationCommandId==first&&follower.creationCommandId==first&&second!=first,"Actual backend freezes creator command instead of transferring dispatch ownership");
                h.store.Seed(creator);h.store.recoverable=false;h.SeedCreating(second,follower);yield return h.Run(h.flow.Buy("wellkeeper"));
                using(var saved=h.Journal()){var document=saved.Read();Check(h.flow.Pending&&document.commandId==second&&document.order.creationCommandId==first&&document.hasPayment&&h.store.purchases==0,"Actual follower Create callback with foreign creator proof becomes lookup-only without SDK dispatch");}
            }
        }
        static IEnumerator Daily(){
            stage="DailyPresentationFault";report.cases++;
            using(var h=new Harness("daily")){
                bool fresh=false;yield return h.RefreshWallet((ok,error)=>fresh=ok);Check(fresh,"Daily recovery uses initial actual wallet");int initial=h.wallet.coins;string claimRoot=Path.Combine(Path.GetTempPath(),"hotr-commerce116-"+config.runId,"claims");
                Func<Action<RewardAccess,string>,IEnumerator> authorize=done=>DailyAuthorize(h,done);
                Func<RewardAccess,RewardPresentationJournal> factory=access=>h.presentation;
                var coordinator=new ServerRewardsCoordinator(claimRoot,authorize,h.RefreshWallet,factory);RewardCompletion result=null;
                yield return coordinator.Refresh("Daily",r=>result=r);report.diagnostics.Add("Daily metadata error="+SafeCode(result?.error)+" targetLength="+Path.Combine(claimRoot,new string('a',64),h.credential.playerId,"rewards.json").Length+" temporaryLength="+Path.Combine(claimRoot,new string('a',64),h.credential.playerId,"r-"+new string('a',32)+".tmp").Length);Check(result!=null&&result.ok&&coordinator.Offer.step==0&&!coordinator.Offer.claimed,"Real unclaimed Daily offer loaded");
                h.presentation.VerificationCheckpoint=point=>{if(point=="BeforeCommit")throw new IOException("ControlledPresentationDiskFault");};yield return coordinator.ClaimDaily(r=>result=r);
                int historicalTemporaryLength=Path.Combine(claimRoot,IdentityProtocol82.Sha(new Uri(config.origin).GetLeftPart(UriPartial.Authority)),h.credential.playerId,"r-"+new string('a',32)+".tmp").Length;
                report.diagnostics.Add("Daily initial error="+SafeCode(result?.error)+" pending="+coordinator.HasPending+" coins="+h.wallet.coins+" presentationPending="+(h.presentation.Peek()!=null)+" historicalTemporaryPathLength="+historicalTemporaryLength);
                if(result!=null&&result.error=="RewardIntentSaveUnavailable"&&historicalTemporaryLength>=260){
                    Check(h.wallet.coins==initial&&h.presentation.Peek()==null,"Historical synthetic Windows path failure precedes any financial credit or presentation");
                    claimRoot=Path.GetFullPath(Path.Combine("../.verification-cache/Launch82/R100D",config.runId));
                    coordinator=new ServerRewardsCoordinator(claimRoot,authorize,h.RefreshWallet,factory);
                    yield return coordinator.Refresh("Daily",r=>result=r);Check(result!=null&&result.ok&&!coordinator.Offer.claimed,"Short synthetic journal path reloads still-unclaimed authoritative offer");
                    yield return coordinator.ClaimDaily(r=>result=r);
                    report.diagnostics.Add("Daily short-path error="+SafeCode(result?.error)+" pending="+coordinator.HasPending+" coins="+h.wallet.coins+" presentationPending="+(h.presentation.Peek()!=null));
                }
                Check(result!=null&&!result.ok&&result.error=="RewardPresentationSaveUnavailable"&&coordinator.HasPending&&h.wallet.coins==initial+50,"Committed real50coin claim retains intent when presentation save fails");
                string claimPath=Path.Combine(claimRoot,IdentityProtocol82.Sha(new Uri(config.origin).GetLeftPart(UriPartial.Authority)),h.credential.playerId,"rewards.json");
                var intentJournal=new ServerRewardJournal(claimPath,config.origin,h.credential.playerId);var pending=intentJournal.Read().pending;var original=JsonUtility.FromJson<PendingGift>(pending.payload);long revision=h.wallet.revision;
                Check(!File.ReadAllText(claimPath).Contains(h.credential.token),"Actual claim intent contains no credential");h.presentation.VerificationCheckpoint=null;coordinator=new ServerRewardsCoordinator(claimRoot,authorize,h.RefreshWallet,factory);
                yield return coordinator.RecoverPending(r=>result=r);Check(result!=null&&result.ok&&!coordinator.HasPending&&!intentJournal.Read().hasPending&&result.receiptId==original.offerId,"Recreated coordinator resolves same claim and queues receipt before intent acknowledgement");
                var queued=h.presentation.Peek();Check(queued!=null&&queued.channel=="reward"&&queued.id==original.offerId&&queued.grant.coins==50&&h.wallet.coins==initial+50&&h.wallet.revision==revision,"Recovered presentation does not create another real wallet grant");
                h.presentation.MarkPresented(queued.channel,queued.id);yield return coordinator.RecoverPending(r=>result=r);Check(result.ok&&result.grant==null&&h.presentation.Peek()==null&&h.wallet.coins==initial+50,"Cleared claim cannot replay collection or financial credit on later Home recovery");
            }
        }
        static IEnumerator DailyAuthorize(Harness h,Action<RewardAccess,string> done){bool fresh=false;yield return h.RefreshWallet((ok,error)=>fresh=ok);done(fresh?new RewardAccess(config.origin,h.credential.playerId,1,()=>h.valid?h.credential.token:null,true):null,fresh?null:"ControlledDailyWalletUnavailable");}
        static void Finish(){
            EditorApplication.update-=Tick;main?.Dispose();main=null;foreach(var job in jobs)job.Dispose();jobs.Clear();scheduled.Clear();
            if(report==null)report=new Report();report.profilesAfter=ProfileDigest();if(report.profilesBefore!=null&&report.profilesBefore!=report.profilesAfter)report.errors.Add("OrdinaryProfileHashChanged");
            report.status=report.errors.Count==0?"PASS_NATIVE_COMMERCE_HTTP100":"FAIL_NATIVE_COMMERCE_HTTP100";
            if(output==null)output=Path.GetFullPath("../Verification/Evidence/Review100/Native/UnconfiguredCommerce100");string native=Path.Combine(output,"Native");Directory.CreateDirectory(native);File.WriteAllText(Path.Combine(native,"Commerce100Http.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));
            config=null;EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif

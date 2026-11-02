#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.NoMoves;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.Shop;
using HeartOfTheRain.App.ShopCheckout86;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification {
    public static class ShopCheckout86Verification {
        const string Origin="http://127.0.0.1:18686",Player="11111111111111111111111111111111";
        static readonly BindingFlags Hidden=BindingFlags.Instance|BindingFlags.NonPublic;
        [Serializable] sealed class Report {
            public string status,utc,unity,scope;public int checks,cases,uiCases;
            public bool scriptedSdk=true,scriptedAuthority=true,actualEncryptedCas=true,actualUGui=true,actualHttp=false;
            public List<string> passed=new List<string>(),errors=new List<string>(),captures=new List<string>();
            public List<QuantityDiagnostic100> quantities=new List<QuantityDiagnostic100>();
        }
        [Serializable] sealed class QuantityDiagnostic100 {
            public string stage,name,text,font,maskInfo;public int locale,fontSize,vertices,opaqueVertices,triangles,inkPixels=-1;
            public float preferredWidth,preferredHeight,width,height,scale,triangleArea,groupAlpha;
            public bool culled;public Vector3 meshMin,meshMax;public Rect screen;
        }
        static bool Quantity(Text text)=>text.name.StartsWith("detail-rewards-",StringComparison.Ordinal)&&(text.name.Contains("-tool-count-")||text.name.Contains("-power-count-"));
        static List<QuantityDiagnostic100> InspectQuantities(Canvas canvas,Transform root,string stage,Texture2D capture=null,Camera camera=null){
            var result=new List<QuantityDiagnostic100>();Color32[] pixels=capture?capture.GetPixels32():null;
            foreach(var text in root.GetComponentsInChildren<Text>().Where(Quantity)){
                var mesh=text.canvasRenderer.GetMesh();var vertices=mesh?mesh.vertices:new Vector3[0];var colors=mesh?mesh.colors32:new Color32[0];var triangles=mesh?mesh.triangles:new int[0];float area=0;
                for(int i=0;i+2<triangles.Length;i+=3)area+=Vector3.Cross(vertices[triangles[i+1]]-vertices[triangles[i]],vertices[triangles[i+2]]-vertices[triangles[i]]).magnitude*.5f;
                var corners=new Vector3[4];text.rectTransform.GetWorldCorners(corners);var points=corners.Select(point=>RectTransformUtility.WorldToScreenPoint(camera,point)).ToArray();
                var diagnostic=new QuantityDiagnostic100{stage=stage,name=text.name,text=text.text,font=text.font?text.font.name:"missing",locale=GameLocale.Current,fontSize=text.fontSize,vertices=vertices.Length,opaqueVertices=colors.Count(color=>color.a>0),triangles=triangles.Length/3,triangleArea=area,
                    preferredWidth=text.preferredWidth,preferredHeight=text.preferredHeight,width=text.rectTransform.rect.width,height=text.rectTransform.rect.height,scale=canvas.scaleFactor,culled=text.canvasRenderer.cull,
                    groupAlpha=text.GetComponentsInParent<CanvasGroup>().Aggregate(1f,(value,group)=>value*group.alpha),maskInfo="RectMasks="+text.GetComponentsInParent<RectMask2D>().Length+";Masks="+text.GetComponentsInParent<Mask>().Length,
                    screen=Rect.MinMaxRect(points.Min(point=>point.x),points.Min(point=>point.y),points.Max(point=>point.x),points.Max(point=>point.y)),meshMin=mesh?mesh.bounds.min:Vector3.zero,meshMax=mesh?mesh.bounds.max:Vector3.zero};
                if(capture){int count=0;for(int y=Mathf.Max(0,Mathf.FloorToInt(diagnostic.screen.yMin));y<Mathf.Min(capture.height,Mathf.CeilToInt(diagnostic.screen.yMax));y++)for(int x=Mathf.Max(0,Mathf.FloorToInt(diagnostic.screen.xMin));x<Mathf.Min(capture.width,Mathf.CeilToInt(diagnostic.screen.xMax));x++){var color=pixels[y*capture.width+x];if(color.r<120&&color.g<155&&color.b<180&&color.a>0)count++;}diagnostic.inkPixels=count;}
                report.quantities.Add(diagnostic);result.Add(diagnostic);
            }
            return result;
        }
        static Report report;static string directory,output;
        static void Need(bool value,string code){report.checks++;if(!value)throw new InvalidOperationException(code);}
        static void Reject(Action action,string code){bool rejected=false;try{action();}catch{rejected=true;}Need(rejected,code);}
        static void Case(string name,Action action){report.cases++;try{action();report.passed.Add(name);}catch(Exception error){report.errors.Add(name+":"+(error is InvalidOperationException?error.Message:error.GetType().Name));}}
        static IEnumerator Immediate(Action action){action();yield break;}
        static CheckoutConfiguration86 Config()=>new CheckoutConfiguration86{version=1,enabled=true,sandbox=true,consoleAppId="123456"};
        static CheckoutCatalog86 Catalog()=>new CheckoutCatalog86{version="fixture86",appId="123456",enabled=true,sandbox=true,balanceScope="server_wallet",serverWalletProjection=true,products=CheckoutCatalogRules86.Ids.Select((id,i)=>new CheckoutProduct86{id=id,storeProductId="hotr_"+id.Replace('-','_'),coins=CheckoutCatalogRules86.Coins[i],amountMinor=new[]{9900,29900,49900,89900,159900,299900}[i],currency="RUB",quantity=1}).ToArray()};
        sealed class Server {
            public CheckoutCatalog86 catalog=Catalog();public int coins=1250,grants,createCalls,reads,reconciles;public int[] starting=new int[4],tools=new int[4];public bool loseCreate,failRefresh,delayAck,hidePending,reuseExisting;
            public readonly List<string> createIds=new List<string>();public readonly Dictionary<string,RuStoreServerOrder> orders=new Dictionary<string,RuStoreServerOrder>();
            public RuStoreServerOrder active;
            public RuStoreServerOrder Create(string command,string product){createCalls++;createIds.Add(command);if(reuseExisting&&orders.Count>0)return active=orders.Values.First();if(!orders.TryGetValue(command,out var order)){var quote=catalog.products.Single(p=>p.id==product);string id=Guid.NewGuid().ToString("N");order=new RuStoreServerOrder{orderId=id,playerId=Player,state="Created",creationCommandId=command,productId=product,coins=quote.coins,grant=CheckoutCatalogRules86.FrozenGrant(quote.id,quote.coins,quote.grant).Copy(),policy=quote.policy,amountMinor=quote.amountMinor,currency="RUB",catalogVersion=catalog.version,sdk=new RuStoreServerSdkOrder{orderId=id,productId=quote.storeProductId,appUserId=Player,developerPayload="hotr-order-v1:"+id+":"+new string('a',32),quantity=1,sandbox=true}};orders.Add(command,order);}return active=order;}
        }
        sealed class Backend:ICheckoutBackend86,ICheckoutRecovery100 {
            readonly Server state;public bool disposed;public Backend(Server state){this.state=state;}
            public bool WalletReady=>!disposed;
            public void Catalog(Action<PayReply<CheckoutCatalog86>> done)=>done(PayReply<CheckoutCatalog86>.Ok(state.catalog));
            public void Pending(long after,Action<PayReply<RuStorePendingOrders100>> done)=>done(PayReply<RuStorePendingOrders100>.Ok(new RuStorePendingOrders100{playerId=Player,orders=state.hidePending?new RuStoreServerOrder[0]:state.orders.Values.Where(o=>o.deliveryAcknowledgement!="Acknowledged"&&!new[]{"Cancelled","Rejected","Expired"}.Contains(o.state)).ToArray(),nextCursor=state.orders.Count}));
            public void Create(string command,string product,Action<PayReply<RuStoreServerOrder>> done){var order=state.Create(command,product);if(state.loseCreate){state.loseCreate=false;done(PayReply<RuStoreServerOrder>.Fail("StagingNetworkUnavailable",true));}else done(PayReply<RuStoreServerOrder>.Ok(order));}
            public void Read(string id,Action<PayReply<RuStoreServerOrder>> done){state.reads++;done(PayReply<RuStoreServerOrder>.Ok(state.orders.Values.Single(o=>o.orderId==id)));}
            public void Reconcile(PayRequest request,PayPurchase observed,Action<PayReply<PayDeliveryReceipt>> done){state.reconciles++;var order=state.orders.Values.Single(o=>o.orderId==request.orderId);if(order.state!="Confirmed"){state.coins+=order.coins;for(int i=0;i<4;i++){state.starting[i]+=order.grant.starting[i];state.tools[i]+=order.grant.tools[i];}state.grants++;order.state="Confirmed";order.credit=new RuStoreServerCredit{receiptId="receipt/"+order.orderId,coins=order.coins,grant=order.grant.Copy(),createdAt=1,balanceScope="commerce_receipt_audit"};}done(PayReply<PayDeliveryReceipt>.Ok(new PayDeliveryReceipt(request.orderId,request.productId,request.appUserId,observed.locator.purchaseId,observed.locator.invoiceId,"receipt/"+order.orderId,true,true,true)));}
            public void ResolveTerminal(PayRequest request,PayPurchase observed,Action<PayReply<PayTerminalReceipt>> done){state.reconciles++;state.active.state=PayTerminalReceipt.StateFor(observed.status);done(PayReply<PayTerminalReceipt>.Ok(new PayTerminalReceipt(request.orderId,request.productId,request.appUserId,observed.locator.purchaseId,observed.locator.invoiceId,state.active.state,true,true,true)));}
            public void Dispose(){disposed=true;}
        }
        sealed class Store:IPayStore {
            public bool SdkCompiled=>true;public bool Configured=>true;public bool unknown,recoverable;public int purchases,lookups,acks;public string status="CONFIRMED";public Action beforePurchase,acknowledged;
            public PayProduct[] products=Catalog().products.Select(p=>new PayProduct(p.storeProductId,(p.amountMinor/100)+" ₽",p.currency,p.amountMinor)).ToArray();
            PayRequest request;Action<PayReply<PayLocator>> pending;
            public void GetPurchaseAvailability(Action<PayReply<PayAvailability>> done)=>done(PayReply<PayAvailability>.Ok(new PayAvailability(true)));
            public void GetProducts(string[] ids,Action<PayReply<PayProduct[]>> done)=>done(PayReply<PayProduct[]>.Ok(products.Where(p=>ids.Contains(p.productId)).ToArray()));
            PayLocator Locator()=>new PayLocator("11111111-1111-4111-8111-111111111111","8100001",request.orderId,request.productId,1,true);
            PayPurchase Purchase()=>new PayPurchase(Locator(),request.developerPayload,status,"ONE_STEP",acks>0?"ACKNOWLEDGED":"NOT_ACKNOWLEDGED");
            public void Purchase(PayRequest value,Action<PayReply<PayLocator>> done){purchases++;request=value;beforePurchase?.Invoke();if(unknown)done(PayReply<PayLocator>.Fail("PaymentUnknown",true));else pending=done;}
            public void Complete(){recoverable=true;var callback=pending;pending=null;callback(PayReply<PayLocator>.Ok(Locator()));}
            public void GetPurchase(string id,Action<PayReply<PayPurchase>> done){lookups++;done(PayReply<PayPurchase>.Ok(Purchase()));}
            public void GetPurchases(Action<PayReply<PayPurchase[]>> done){lookups++;done(PayReply<PayPurchase[]>.Ok(recoverable?new[]{Purchase()}:new PayPurchase[0]));}
            public void ConfirmTwoStep(PayRequest r,PayPurchase p,PayCaptureAuthorization a,Action<PayReply<PayAvailability>> done)=>done(PayReply<PayAvailability>.Fail("NotUsed"));
            public void Acknowledge(PayRequest r,PayPurchase p,PayDeliveryReceipt receipt,Action<PayReply<PayAvailability>> done){acks++;acknowledged?.Invoke();done(PayReply<PayAvailability>.Ok(new PayAvailability(true)));}
        }
        sealed class Driver:IDisposable {
            readonly Stack<IEnumerator> stack=new Stack<IEnumerator>();public Driver(IEnumerator routine){stack.Push(routine);}
            bool Tick(){for(int n=0;n<1024;n++){if(stack.Count==0)return false;var value=stack.Peek();if(!value.MoveNext()){(stack.Pop()as IDisposable)?.Dispose();continue;}if(value.Current is IEnumerator nested)stack.Push(nested);else return true;}throw new InvalidOperationException("CheckoutNestedWorkBound");}
            public void Start(){Tick();}
            public void Until(Func<bool> condition){for(int n=0;n<256;n++){if(condition())return;if(!Tick())break;}Need(condition(),"CheckoutScriptedWaitBound");}
            public void End(){for(int n=0;n<256;n++)if(!Tick())return;throw new InvalidOperationException("CheckoutScriptedFrameBound");}
            public void Dispose(){while(stack.Count>0)(stack.Pop()as IDisposable)?.Dispose();}
        }
        sealed class Fixture:IDisposable {
            public readonly Server server=new Server();public readonly Store store=new Store();public readonly EditorEphemeralIdentity82 vault=new EditorEphemeralIdentity82();
            readonly string path;public ShopCheckoutFlow86 flow;public ProtectedCheckoutJournal86 journal;public bool access=true,renew,failPresentation;public int presentations;public int authorizations,projected=1250;public int[] projectedStarting=new int[4],projectedTools=new int[4];
            public Fixture(string name){path=Path.Combine(directory,name,"checkout.sealed");store.acknowledged=()=>{if(!server.delayAck)server.active.deliveryAcknowledgement="Acknowledged";};Open();}
            public ProtectedCheckoutJournal86 Journal()=>new ProtectedCheckoutJournal86(vault.CreateStore(path),Origin,Player);
            public void RemoveProtectedBytes()=>File.Delete(path);
            public void SeedLegacy(){
                var type=typeof(ProtectedCheckoutJournal86).GetNestedType("LegacyDocument100",BindingFlags.NonPublic);
                string legacy=JsonUtility.ToJson(JsonUtility.FromJson(JsonUtility.ToJson(journal.Read()),type));
                using(var storage=vault.CreateStore(path)){byte[] before=storage.Read();storage.CompareExchange(IdentityProtocol82.Sha(before),Encoding.UTF8.GetBytes(legacy));}
            }
            public void Open(){flow?.Dispose();flow=new ShopCheckoutFlow86(Config(),done=>Immediate(()=>{authorizations++;if(renew){renew=false;access=true;}done(access?new CheckoutAccess86(Origin,Player,authorizations,new Backend(server),()=>access):null,access?null:"IdentityExpired");}),done=>Immediate(()=>{if(server.failRefresh){server.failRefresh=false;done(false,"ProjectionUnavailable");}else{projected=server.coins;projectedStarting=(int[])server.starting.Clone();projectedTools=(int[])server.tools.Clone();done(true,null);}}),a=>journal=Journal(),a=>store,(a,order)=>{if(failPresentation){failPresentation=false;throw new IOException();}presentations++;});flow.SetAuthorityDispatcher(routine=>new Driver(routine).End());}
            public Driver Drive(IEnumerator routine)=>new Driver(flow.Guard(routine));
            public Driver Buy(string product="coins-1000"){int before=store.purchases;var driver=Drive(flow.Buy(product));driver.Start();driver.Until(()=>store.purchases>before||!flow.Busy);Need(store.purchases>before,"ExplicitPurchaseExpectedSdkDispatch_"+(flow.Error??"NoError"));return driver;}
            public void Dispose(){flow.Dispose();vault.Dispose();}
        }
        static void Success(){using(var f=new Fixture("success")){
            f.store.beforePurchase=()=>{var saved=f.journal.Read();Need(saved.hasOrder&&saved.hasPayment&&saved.payment.phase=="AwaitingPayment"&&saved.commandId==f.server.createIds[0],"CreateAndFullOrderAndDispatchClaimDurableBeforeSdk");};
            using(var driver=f.Buy()){Need(f.server.coins==1250&&f.projected==1250&&f.server.grants==0,"SdkPresentationAloneCannotGrant");f.access=false;f.renew=true;f.store.Complete();driver.End();}
            Need(f.authorizations>=2&&f.server.reconciles==2&&f.server.grants==1&&f.projected==2250&&f.store.acks==1&&f.flow.Credited&&!f.flow.Pending,"FreshSameOwnerAuthorityThenProjectionBeforeCreditFeedback");
        }}
        static void CreateLost(){using(var f=new Fixture("lostCreate")){
            f.server.loseCreate=true;f.Drive(f.flow.Buy("coins-1000")).End();string id=f.journal.Read().commandId;
            Need(f.flow.Pending&&f.journal.Read().phase=="Creating"&&f.store.purchases==0,"UnknownCreateRetainsOriginalBeforeSdk");f.Open();f.Drive(f.flow.Recover()).End();
            Need(f.server.createIds.Count==2&&f.server.createIds.All(v=>v==id)&&f.journal.Read().hasOrder&&f.store.purchases==0&&f.flow.Pending,"PassiveRestartRecoversSameOrderWithoutStartingPurchase");
            using(var driver=f.Buy()){f.store.Complete();driver.End();}Need(f.store.purchases==1&&f.server.grants==1&&!f.flow.Pending,"SeparateExplicitTapStartsOnlyRecoveredOrder");
        }}
        static void UnknownPurchase(){using(var f=new Fixture("unknownPurchase")){
            f.store.unknown=true;f.Drive(f.flow.Buy("coins-1000")).End();string id=f.journal.Read().order.orderId;
            Need(f.flow.Pending&&f.journal.Read().payment.phase=="OutcomeUnknown","UnknownSdkOutcomePersisted");f.Open();f.Drive(f.flow.Recover()).End();
            Need(f.flow.Pending&&f.store.purchases==1&&f.server.createCalls==1&&f.journal.Read().order.orderId==id&&f.server.grants==0,"EmptyPurchaseListNeverClosesOrCreatesAnotherOrder");
            f.store.recoverable=true;f.Drive(f.flow.Recover()).End();Need(f.store.purchases==1&&f.server.grants==1&&!f.flow.Pending&&f.projected==2250,"LaterExactPurchaseRecoversOneAuthoritativeCredit");
        }}
        static void DiskFault(){using(var f=new Fixture("disk")){
            f.vault.VerificationCheckpoint=stage=>{if(stage=="BeforeCommit")throw new IOException();};f.Drive(f.flow.Buy("coins-1000")).End();Need(f.server.createCalls==0&&f.store.purchases==0,"PreCreateDiskFaultStopsAllFinancialDispatch");
            f.vault.VerificationCheckpoint=null;using(var driver=f.Buy()){using(var another=f.Journal()){string error;Need(!another.TrySave(f.journal.Load(),out error),"SecondOwnerCannotReclaimAwaitingPaymentDispatch");}f.store.Complete();driver.End();}Need(f.store.purchases==1&&f.server.grants==1,"DiskRetryStillDispatchesAndCreditsOnce");
        }}
        static void ProjectionFault(){using(var f=new Fixture("projection")){
            f.server.failRefresh=true;using(var driver=f.Buy()){f.store.Complete();driver.End();}Need(f.server.grants==1&&f.projected==1250&&!f.flow.Credited&&f.flow.Pending,"CommittedCreditWithoutProjectionKeepsFeedbackHidden");
            f.Open();f.Drive(f.flow.Recover()).End();Need(f.server.grants==1&&f.projected==2250&&f.flow.Credited&&!f.flow.Pending&&f.store.purchases==1,"RestartRevalidatesAndRefreshesWithoutRebuy");
        }}
        static void Stale(){using(var f=new Fixture("stale")){
            using(var driver=f.Buy()){f.flow.Invalidate();f.access=false;f.store.Complete();driver.End();}Need(f.server.grants==0&&f.projected==1250&&f.journal.Read().Pending,"InvalidatedOwnerCannotReconcileLateSdkCallback");
        }}
        static void Terminal(){using(var f=new Fixture("terminal")){
            f.store.status="CANCELLED";using(var driver=f.Buy()){f.store.Complete();driver.End();}Need(f.server.grants==0&&f.store.acks==0&&!f.flow.Credited&&!f.flow.Pending&&f.journal.Read().payment.hasTerminal,"ServerTerminalProofClosesWithoutCreditOrAcknowledgement");
            var view=new CheckoutUiState86{configured=true,error=f.flow.Error,pending=f.flow.Pending,credited=f.flow.Credited};Need(view.Status==CheckoutText86.T("closed")&&!view.credited&&!view.pending,"TerminalNoDeliveryShowsNotCompletedWithoutSuccess");
        }}
        static void MissingStore(){using(var f=new Fixture("missingStore")){
            using(var driver=f.Buy()){f.RemoveProtectedBytes();f.store.Complete();driver.End();}
            Need(f.flow.Pending&&f.server.grants==0&&f.projected==1250,"MissingObservedOutboxRetainsPendingAndCannotGrant");Reject(()=>f.journal.Read(),"MissingObservedProtectedBytesFailClosed");f.Drive(f.flow.Buy("coins-1000")).End();Need(f.server.createCalls==1&&f.store.purchases==1&&f.flow.Pending,"MissingObservedOutboxCannotCreateAnotherOrder");
        }}
        static void CatalogChecks(){
            var catalog=Catalog();var sdk=catalog.products.Select(p=>new PayProduct(p.storeProductId,"SDK label "+p.amountMinor,"RUB",p.amountMinor)).ToArray();Need(CheckoutCatalogRules86.Match(Config(),catalog,sdk).Count==6,"ExactApprovedSixCoinProducts");
            var config=Config();config.sandbox=false;Reject(()=>CheckoutCatalogRules86.Match(config,catalog,sdk),"LiveConfigNeverEnablesCheckout");catalog.appId="654321";Reject(()=>CheckoutCatalogRules86.Match(Config(),catalog,sdk),"ConsoleIdentityBound");catalog=Catalog();catalog.products[0].coins=5000;Reject(()=>CheckoutCatalogRules86.Match(Config(),catalog,sdk),"CoinCountBound");catalog=Catalog();var wrong=(PayProduct[])sdk.Clone();wrong[0]=new PayProduct(sdk[0].productId,"sample","USD",19900);Reject(()=>CheckoutCatalogRules86.Match(Config(),catalog,wrong),"CurrencyBound");wrong[0]=new PayProduct(sdk[0].productId,"sample","RUB",1);Reject(()=>CheckoutCatalogRules86.Match(Config(),catalog,wrong),"SdkPriceBound");wrong[0]=sdk[1];Reject(()=>CheckoutCatalogRules86.Match(Config(),catalog,wrong),"DuplicateOrMissingSkuRejected");
        }
        static CheckoutProduct86 Bundle(string id){
            bool special=Array.IndexOf(CheckoutCatalogRules86.BundleIds,id)<3;var grant=CheckoutCatalogRules86.ApprovedGrant(id);
            return new CheckoutProduct86{id=id,storeProductId="hotr_bundle_"+id.Replace('-','_'),coins=grant.coins,grant=grant,amountMinor=new[]{9900,19900,29900,39900,59900,99900}[Array.IndexOf(CheckoutCatalogRules86.BundleIds,id)],currency="RUB",quantity=1,policy=new CommercePolicy100{specified=true,repeatable=!special,purchaseLimitPerPlayer=special?1:0,eligible=true,eligibility="Available"}};
        }
        static void TypedGrantParser100(){
            const string body="{\"coins\":2000,\"grant\":{\"coins\":2000,\"stars\":0,\"starting\":[1,1,1,1],\"tools\":[1,1,1,1]},\"purchaseLimitPerPlayer\":1,\"repeatable\":false,\"eligible\":true,\"pendingOrderId\":null,\"eligibility\":\"Available\"}";
            Need(CommerceTerms100.Same(CommerceTerms100.ParseGrant(body,2000,"wellkeeper"),CheckoutCatalogRules86.ApprovedGrant("wellkeeper"))&&CommerceTerms100.ParsePolicy(body,"wellkeeper").purchaseLimitPerPlayer==1,"TypedFullGrantAndStablePolicyArePreserved");
            foreach(string malformed in new[]{body.Replace("[1,1,1,1]","[1,1,1]"),body.Replace("[1,1,1,1]","[1,1,1,-1]"),body.Replace("[1,1,1,1]","[1,1,1,true]"),body.Replace("\"stars\":0","\"stars\":1"),body.Replace("\"coins\":2000","\"coins\":3000")})Reject(()=>CommerceTerms100.ParseGrant(malformed,2000,"wellkeeper"),"MalformedOrConflictingFullInventoryGrantRejected");
            Reject(()=>CommerceTerms100.ParseGrant("{}",2000,"wellkeeper"),"MissingBundleGrantCannotManufactureInventory");Need(CommerceTerms100.ParseGrant("{}",1000,"coins-1000").tools.All(n=>n==0),"OnlyLegacyCoinMappingMayInferZeroInventory");Reject(()=>CommerceTerms100.ParseGrant("{}",5000,"coins-1000"),"LegacyCoinIdentityAndQuantityMustAgree");
            foreach(string malformed in new[]{body.Replace("\"repeatable\":false","\"repeatable\":true"),body.Replace("\"eligibility\":\"Available\"","\"eligibility\":\"Purchased\""),body.Replace("\"pendingOrderId\":null","\"pendingOrderId\":\"invalid\"")})Reject(()=>CommerceTerms100.ParsePolicy(malformed,"wellkeeper"),"TypedEligibilityConflictsRejected");
        }
        static void LegacyCachedCreatorParser100(){
            var server=new Server();string command=Guid.NewGuid().ToString("N");var order=server.Create(command,"coins-1000");
            string common="\"orderId\":\""+order.orderId+"\",\"playerId\":\""+Player+"\",\"catalogVersion\":\"legacy-cache100\",\"productId\":\"coins-1000\",\"coins\":1000,\"amountMinor\":"+order.amountMinor+",\"currency\":\"RUB\",\"balanceScope\":\"server_wallet\",\"productionEnabled\":false,\"normalUnityProfileIntegrated\":false,\"localProfileMutated\":false,\"sdk\":"+JsonUtility.ToJson(order.sdk);
            string legacy="{"+common+",\"state\":\"Created\",\"availableToSpend\":false,\"availableInServerWallet\":false,\"invoiceId\":null,\"purchaseId\":null,\"deliveryAcknowledgement\":null,\"credit\":null}";
            string grant="{\"coins\":1000,\"stars\":0,\"starting\":[0,0,0,0],\"tools\":[0,0,0,0]}";
            string paid="{"+common+",\"creationCommandId\":null,\"state\":\"Confirmed\",\"availableToSpend\":true,\"availableInServerWallet\":true,\"invoiceId\":\"8100001\",\"purchaseId\":\"11111111-1111-4111-8111-111111111111\",\"deliveryAcknowledgement\":\"Acknowledged\",\"grant\":"+grant+",\"purchaseLimitPerPlayer\":null,\"repeatable\":true,\"eligible\":true,\"eligibility\":\"Available\",\"pendingOrderId\":null,\"credit\":{\"receiptId\":\"legacy-paid100\",\"coins\":1000,\"createdAt\":1,\"balanceScope\":\"commerce_receipt_audit\",\"grant\":"+grant+"}}";
            var parser=typeof(RuStoreBackendClient).GetMethod("Order",Hidden);
            using(var client=new RuStoreBackendClient(Origin,new string('a',43),Player,true,true,_=>{})){
                var cached=(RuStoreServerOrder)parser.Invoke(client,new object[]{legacy,order.orderId,"coins-1000",order.Request()});
                Need(cached.creationCommandId==null&&cached.credit==null,"LegacyCachedCreateOmissionIsUnknownCreator");
                var canonical=(RuStoreServerOrder)parser.Invoke(client,new object[]{paid,order.orderId,"coins-1000",order.Request()});
                Need(canonical.creationCommandId==null&&canonical.credit!=null&&canonical.credit.coins==1000&&CommerceTerms100.Same(canonical.grant,canonical.credit.grant)&&canonical.Request().SameOrder(cached.Request()),"Schema9ExplicitNullPaidRecoveryKeepsLegacyFrozenOrderBinding");
                Need(canonical.creationCommandId!=command,"UnknownCreatorNeverBecomesPermissionForInitialSdkDispatch");
                foreach(string malformed in new[]{paid.Replace("\"creationCommandId\":null","\"creationCommandId\":\"\""),paid.Replace("\"creationCommandId\":null","\"creationCommandId\":true"),paid.Replace("\"creationCommandId\":null","\"creationCommandId\":\"invalid\"")})Reject(()=>parser.Invoke(client,new object[]{malformed,order.orderId,"coins-1000",order.Request()}),"RawMalformedCreatorRemainsRejected");
            }
        }
        static void BundleContracts(){
            var catalog=Catalog();catalog.products=catalog.products.Concat(CheckoutCatalogRules86.BundleIds.Select(Bundle)).ToArray();var sdk=catalog.products.Select(p=>new PayProduct(p.storeProductId,"quoted "+p.amountMinor,"RUB",p.amountMinor)).ToArray();
            Need(CheckoutCatalogRules86.Match(Config(),catalog,sdk).Count==12,"AllApprovedCoinAndFullInventoryQuotesMatchActualSdkLabels");
            var persisted=JsonUtility.FromJson<CheckoutProduct86>(JsonUtility.ToJson(catalog.products[6]));Need(CheckoutCatalogRules86.ValidProduct(persisted),"UnitySerializedAbsentPendingOrderDoesNotInvalidateAvailableBundle");persisted.policy.pendingOrderId="invalid";Need(!CheckoutCatalogRules86.ValidProduct(persisted),"TypedNonemptyInvalidPendingOrderRemainsRejected");
            var product=catalog.products[6];product.grant.tools[0]++;Reject(()=>CheckoutCatalogRules86.Match(Config(),catalog,sdk),"MismatchedAdvertisedToolGrantCannotQuote");product.grant=CheckoutCatalogRules86.ApprovedGrant(product.id);product.grant=null;Reject(()=>CheckoutCatalogRules86.Match(Config(),catalog,sdk),"BundleCannotInferFullGrantFromCoins");product.grant=CheckoutCatalogRules86.ApprovedGrant(product.id);product.policy.purchaseLimitPerPlayer=0;product.policy.repeatable=true;Reject(()=>CheckoutCatalogRules86.Match(Config(),catalog,sdk),"SpecialCannotSilentlyBecomeRepeatable");
        }
        static void BundleSuccess(){using(var f=new Fixture("bundle")){
            f.server.catalog.products=new[]{Bundle("rainlight")};f.store.products=f.server.catalog.products.Select(p=>new PayProduct(p.storeProductId,"SDK299 RUB","RUB",p.amountMinor)).ToArray();
            using(var driver=f.Buy("rainlight")){Need(f.server.grants==0&&f.projectedStarting.All(n=>n==0),"BundleSdkPresentationDoesNotGrantAnyInventory");f.store.Complete();driver.End();}
            Need(f.server.grants==1&&f.projected==7250&&f.projectedStarting.All(n=>n==3)&&f.projectedTools.All(n=>n==3)&&!f.flow.Pending&&f.flow.Credited,"FullBundleProjectionAndProviderAcknowledgementPrecedeSuccess");
        }}
        static void AckLag(){using(var f=new Fixture("ackLag")){
            f.server.delayAck=true;using(var driver=f.Buy()){f.store.Complete();driver.End();}
            Need(f.server.grants==1&&f.flow.Pending&&!f.flow.Credited&&f.flow.Error=="CheckoutAcknowledgementPending","SdkAcknowledgementAloneCannotClearServerPendingOrder");
            f.server.delayAck=false;f.Open();f.Drive(f.flow.Recover()).End();Need(f.server.grants==1&&f.store.purchases==1&&!f.flow.Pending&&f.flow.Credited,"ProviderAcknowledgementLagRecoversWithoutRebuyOrDoubleGrant");
        }}
        static void PresentationFault(){using(var f=new Fixture("presentationFault100")){
            f.failPresentation=true;using(var driver=f.Buy()){f.store.Complete();driver.End();}
            Need(f.server.grants==1&&f.projected==2250&&f.flow.Pending&&!f.flow.Credited&&f.presentations==0&&f.flow.Error=="CheckoutRewardPresentationPending","PresentationQueueFailureKeepsCommittedOrderPendingWithoutOptimisticSuccess");
            f.Open();f.Drive(f.flow.Recover()).End();Need(f.server.grants==1&&f.store.purchases==1&&f.presentations==1&&!f.flow.Pending&&f.flow.Credited,"CommittedReceiptQueueRetriesBeforeSettlementWithoutNewPayment");
        }}
        static void FrozenAndLegacy(){using(var f=new Fixture("legacy100")){
            f.store.unknown=true;f.Drive(f.flow.Buy("coins-1000")).End();f.SeedLegacy();f.Open();f.store.recoverable=true;f.Drive(f.flow.Recover()).End();Need(!f.flow.Pending&&f.flow.Credited&&f.server.grants==1&&f.store.purchases==1,"ExactLegacyEncryptedCoinOutboxMigratesAndRecoversWithoutRebuy");
        }using(var f=new Fixture("frozen100")){
            f.server.catalog.products=new[]{Bundle("wellkeeper")};f.store.products=f.server.catalog.products.Select(p=>new PayProduct(p.storeProductId,"old quoted RUB","RUB",p.amountMinor)).ToArray();f.store.unknown=true;f.Drive(f.flow.Buy("wellkeeper")).End();
            int coins=f.server.active.coins;f.server.catalog.products[0]=Bundle("wellkeeper");f.server.catalog.products[0].amountMinor+=10000;f.server.catalog.products[0].grant.tools[0]++;
            f.Open();f.store.recoverable=true;f.Drive(f.flow.Recover()).End();Need(f.flow.Credited&&f.projected==1250+coins&&f.projectedTools.All(n=>n==1)&&f.store.purchases==1,"RecoveryUsesFrozenFullGrantAndPriceRatherThanChangedCurrentCatalog");
        }}
        static void LegacyCreatorUnknown(){using(var f=new Fixture("legacyCreator100")){
            f.server.loseCreate=true;f.Drive(f.flow.Buy("coins-1000")).End();f.server.active.creationCommandId=null;f.SeedLegacy();f.Open();f.Drive(f.flow.Recover()).End();
            Need(f.flow.Pending&&f.journal.Read().hasPayment&&f.journal.Read().payment.phase=="OutcomeUnknown"&&f.store.purchases==0&&f.server.grants==0,"LegacyOrderWithoutServerCreatorProofRemainsLookupOnlyAfterOriginalCreateRetry");
            f.Drive(f.flow.Buy("coins-1000")).End();Need(f.store.purchases==0&&f.flow.Pending,"ExplicitTapCannotTurnUnknownLegacyCreatorIntoSdkDispatchPermission");
        }}
        static void ReservationRace(){using(var f=new Fixture("reservationRace100")){
            string creator=Guid.NewGuid().ToString("N");f.server.Create(creator,"coins-1000");f.server.hidePending=f.server.reuseExisting=true;
            f.Drive(f.flow.Buy("coins-1000")).End();Need(f.flow.Pending&&f.journal.Read().order.creationCommandId==creator&&f.journal.Read().commandId!=creator&&f.journal.Read().hasPayment&&f.store.purchases==0&&f.server.grants==0,"ForeignCreatorReturnedAfterEmptyDiscoveryNeverAuthorizesSdkDispatch");
        }}
        static void CrossDevice(){using(var f=new Fixture("crossDevice100")){
            f.server.Create(Guid.NewGuid().ToString("N"),"coins-1000");f.Drive(f.flow.Refresh()).End();Need(f.flow.Pending&&f.journal.Read().hasPayment&&f.journal.Read().payment.phase=="OutcomeUnknown"&&f.store.purchases==0,"ServerCreatedOrderWithoutLocalDispatchProofIsAdoptedAsUnknown");
            f.Drive(f.flow.Recover()).End();f.Drive(f.flow.Buy("coins-1000")).End();Need(f.flow.Pending&&f.store.purchases==0&&f.server.createCalls==1&&f.server.grants==0,"EmptySdkRecoveryAndExplicitRetryCannotCreateAnotherCharge");
        }}
        static void Ui(){
            int locale=GameLocale.Current;var assets=AssetDatabase.LoadAssetAtPath<ShopAssets>("Assets/HeartOfTheRain/App/Shop/ShopAssets.asset");var session=new ShopSession(JsonUtility.FromJson<ShopCatalog>(assets.catalog.text));session.Open("coins-1000");
            var node=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab"));var home=node.GetComponent<HomePage>();home.Build();var page=node.AddComponent<ShopPage>();page.home=home;page.assets=assets;typeof(ShopPage).GetMethod("Build",Hidden).Invoke(page,null);var canvas=(Canvas)typeof(ShopPage).GetField("canvas",Hidden).GetValue(page);var root=new GameObject("Checkout86 render",typeof(RectTransform)).GetComponent<RectTransform>();root.SetParent(canvas.transform,false);
            try{foreach(string productId in new[]{"coins-1000","wellkeeper","rainlight","village"})foreach(int language in Enumerable.Range(0,5))foreach(int width in new[]{320,480})foreach(float renderScale in new[]{1f,1.832f,3f}){
                session.Close();Need(session.Open(productId),"ConfiguredProductDetailOpens");
                // Match ordinary Shop.Reflow: final pixel scale is established
                // before the renderer creates text and applies LabelFit.
                canvas.GetComponent<CanvasScaler>().scaleFactor=renderScale;canvas.scaleFactor=renderScale;
                GameLocale.Select(language);var frame=ShopLayout.Build(width,800,session,1250);var state=new CheckoutUiState86{configured=true,price=Price,canBuy=id=>true};ShopCheckoutUi86.Apply(frame,session,state);
                Need(frame.overlay.elements.Single(e=>e.id=="detail-back").action=="checkout:buy:"+productId&&frame.overlay.elements.Single(e=>e.id=="detail-price").text==Price(productId),"RenderedBuyUsesOnlyMatchedSdkLabel");
                foreach(Transform child in root.Cast<Transform>().ToArray())UnityEngine.Object.DestroyImmediate(child.gameObject);typeof(ShopPage).GetField("nodes",Hidden).GetValue(page).GetType().GetMethod("Clear").Invoke(typeof(ShopPage).GetField("nodes",Hidden).GetValue(page),null);
                root.anchorMin=root.anchorMax=root.pivot=new Vector2(0,1);root.anchoredPosition=Vector2.zero;root.sizeDelta=new Vector2(width,800);typeof(ShopPage).GetMethod("Render",Hidden).Invoke(page,new object[]{frame.overlay,root});Canvas.ForceUpdateCanvases();
                foreach(string id in new[]{"detail-price","detail-price-note","detail-status-1","detail-status-2","detail-back-label"}){var label=root.GetComponentsInChildren<Text>().Single(t=>t.name==id);Need(!label.supportRichText&&label.preferredWidth<=label.rectTransform.rect.width+2&&label.preferredHeight<=label.rectTransform.rect.height+2,"ActualCheckoutTextFits_"+id);}
                var beforeQuantities=InspectQuantities(canvas,root,"before-capture");
                if(session.OpenOffer.section!="coins"){
                    Need(beforeQuantities.Count==8,"AllEightAdvertisedInventoryQuantitiesAreRendered");
                    for(int i=0;i<4;i++)Need(beforeQuantities.Single(q=>q.name=="detail-rewards-tool-count-"+i).text=="\u00d7"+session.OpenOffer.boostersEach&&beforeQuantities.Single(q=>q.name=="detail-rewards-power-count-"+i).text=="\u00d7"+session.OpenOffer.StartingCount(i),"RenderedQuantityMatchesAdvertisedGrantSlot_"+i);
                }
                if(session.OpenOffer.section!="coins")foreach(var quantity in root.GetComponentsInChildren<Text>().Where(t=>t.name.StartsWith("detail-rewards-",StringComparison.Ordinal)&&(t.name.Contains("-tool-count-")||t.name.Contains("-power-count-")))){
                    var mesh=quantity.canvasRenderer.GetMesh();int vertices=mesh?mesh.vertexCount:0;Need(!string.IsNullOrWhiteSpace(quantity.text)&&quantity.color.a>.9f&&vertices>=4,"ActualBundleQuantityHasVisibleVertices_"+quantity.name+"_font"+quantity.fontSize+"_preferredHeight"+quantity.preferredHeight+"_height"+quantity.rectTransform.rect.height+"_verts"+vertices);
                }
                var buy=root.GetComponentsInChildren<HomeControlLabel>().Single(v=>v.name=="detail-back");Need(buy.action=="checkout:buy:"+productId&&buy.GetComponent<Button>().interactable,"ActualUguiBuyActionEnabledOnlyFromQuote");report.uiCases++;
                string scaleName=renderScale.ToString("0.###",System.Globalization.CultureInfo.InvariantCulture).Replace('.', 'p');
                bool keepImage=width==320&&(language==0||language==4)&&(renderScale==3||productId=="wellkeeper");
                if(session.OpenOffer.section!="coins"||keepImage)Capture(canvas,width,800,"Shop_"+productId+"_"+GameLocale.Codes[language]+"_s"+scaleName,renderScale,keepImage);
                state.canBuy=id=>false;state.error="QuoteMismatch";frame=ShopLayout.Build(width,800,session,1250);ShopCheckoutUi86.Apply(frame,session,state);Need(frame.overlay.elements.Single(e=>e.id=="detail-back").action=="disabled","UnmatchedQuoteNeverOffersBuy");
                if(session.OpenOffer.section=="special"){
                    state.eligibility=id=>"Purchased";frame=ShopLayout.Build(width,800,session,1250);ShopCheckoutUi86.Apply(frame,session,state);
                    Need(frame.overlay.elements.Single(e=>e.id=="detail-status-1").text==CheckoutText86.T("purchased")&&frame.overlay.elements.Single(e=>e.id=="detail-status-2").text==CheckoutText86.T("once")&&frame.overlay.elements.Single(e=>e.id=="detail-back").action=="disabled","OneTimeOwnedOfferShowsStatusAndCannotBuyAgain");
                }
                state.price=id=>null;state.canBuy=id=>true;frame=ShopLayout.Build(width,800,session,1250);ShopCheckoutUi86.Apply(frame,session,state);Need(frame.overlay.elements.Single(e=>e.id=="detail-back").action=="checkout:retry"&&frame.overlay.elements.Single(e=>e.id=="detail-price").text==CheckoutText86.T("unavailable"),"PreviewPriceNeverSubstitutesForMissingSdkQuote");
                state.busy=true;frame=ShopLayout.Build(width,800,session,1250);ShopCheckoutUi86.Apply(frame,session,state);Need(frame.overlay.elements.Single(e=>e.id=="detail-back").action=="disabled","MissingQuoteRetryWaitsForTheCurrentRead");state.busy=false;
            }}finally{GameLocale.Select(locale);UnityEngine.Object.DestroyImmediate(node);}
        }
        static string Price(string id)=>((CheckoutCatalogRules86.Ids.Contains(id)?Catalog().products.Single(p=>p.id==id).amountMinor:Bundle(id).amountMinor)/100)+" \u20bd";
        static void NoMovesUi(){
            int language=GameLocale.Current;
            try{foreach(int locale in Enumerable.Range(0,5)){
                GameLocale.Select(locale);var owner=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab"));
                try{
                    var home=owner.GetComponent<HomePage>();home.Build();var shop=owner.AddComponent<ShopPage>();shop.home=home;shop.assets=AssetDatabase.LoadAssetAtPath<ShopAssets>("Assets/HeartOfTheRain/App/Shop/ShopAssets.asset");
                    var page=owner.AddComponent<NoMovesPage>();page.home=home;page.art=Resources.Load<NoMovesAssets>("HOTR_NoMoves/Design");Need(page.art!=null,"ApprovedNoMovesArtPresent");
                    page.VerificationCheckout86=()=>new CheckoutUiState86{configured=true,price=Price,canBuy=id=>true};typeof(NoMovesPage).GetMethod("Build",Hidden).Invoke(page,null);var checkoutCanvas=(Canvas)typeof(NoMovesPage).GetField("canvas",Hidden).GetValue(page);checkoutCanvas.GetComponent<CanvasScaler>().scaleFactor=3;checkoutCanvas.scaleFactor=3;typeof(NoMovesPage).GetProperty("Screen").GetSetMethod(true).Invoke(page,new object[]{"shop"});
                    var safe=(RectTransform)typeof(NoMovesPage).GetField("safe",Hidden).GetValue(page);safe.sizeDelta=new Vector2(320,800);var body=new GameObject("Actual checkout Shop body",typeof(RectTransform)).GetComponent<RectTransform>();body.SetParent(safe,false);body.anchorMin=body.anchorMax=body.pivot=new Vector2(0,1);typeof(NoMovesPage).GetField("body",Hidden).SetValue(page,body);
                    typeof(NoMovesPage).GetMethod("BuildShop",Hidden).Invoke(page,new object[]{320f,800f,300f});page.SetBusy(false);Canvas.ForceUpdateCanvases();string clicked=null;page.Requested=value=>clicked=value;
                    foreach(string id in CheckoutCatalogRules86.Ids){
                        var button=page.Nodes["Checkout purchase "+id].GetComponent<Button>();Need(button.interactable,"NoMovesMatchedQuoteEnablesOnlyApprovedCoinPack");button.onClick.Invoke();Need(clicked=="checkout:buy:"+id,"ActualNoMovesPurchaseControlDispatchesTypedAction");
                        var label=button.GetComponentInChildren<Text>();var rect=label.rectTransform;var bounds=((RectTransform)button.transform).rect;string price=Price(id);
                        Need(!label.supportRichText&&label.text==price&&label.horizontalOverflow==HorizontalWrapMode.Overflow&&!label.resizeTextForBestFit,"CompactBuyDisplaysExactSingleLineSdkAmount");
                        Need(label.preferredWidth<=rect.rect.width+.01f&&label.preferredHeight<=rect.rect.height+.01f,"ActualNoMovesPriceFitsInteriorWidthAndHeight");
                        Need(rect.anchoredPosition.x>=13&&-rect.anchoredPosition.y>=8&&rect.anchoredPosition.x+rect.rect.width<=bounds.width-13+.01f&&-rect.anchoredPosition.y+rect.rect.height<=bounds.height-8+.01f,"NoMovesPriceRespectsGoldGreenButtonInterior");
                        var semantic=button.GetComponent<HomeControlLabel>();Need(semantic&&semantic.label==CheckoutText86.Buy(price)&&semantic.action=="checkout:buy:"+id,"CompactPriceRetainsLocalizedBuySemantics");
                    }
                    var canvas=(Canvas)typeof(NoMovesPage).GetField("canvas",Hidden).GetValue(page);if(locale==0||locale==4)Capture(canvas,320,800,"NoMoves_"+GameLocale.Codes[locale]);report.uiCases++;
                }finally{UnityEngine.Object.DestroyImmediate(owner);}
            }}finally{GameLocale.Select(language);}
        }
        static void Capture(Canvas canvas,int width,int height,string name,float captureScale=3,bool saveImage=true){
            var cameraNode=new GameObject("Checkout86 capture camera");var camera=cameraNode.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.03f,.08f,.13f);var target=RenderTexture.GetTemporary(Mathf.RoundToInt(width*captureScale),Mathf.RoundToInt(height*captureScale),24,RenderTextureFormat.ARGB32);var prior=RenderTexture.active;var mode=canvas.renderMode;var previousCamera=canvas.worldCamera;float distance=canvas.planeDistance,scale=canvas.scaleFactor;Texture2D image=null;
            try{camera.targetTexture=target;canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=1;canvas.scaleFactor=captureScale;var scaler=canvas.GetComponent<CanvasScaler>();float old=scaler.scaleFactor;scaler.scaleFactor=captureScale;try{Canvas.ForceUpdateCanvases();camera.Render();Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;image=new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);image.ReadPixels(new Rect(0,0,target.width,target.height),0,0);image.Apply();string relative="Native/CheckoutUI/"+name+".png";if(saveImage){Directory.CreateDirectory(Path.GetDirectoryName(Path.Combine(output,relative)));File.WriteAllBytes(Path.Combine(output,relative),image.EncodeToPNG());report.captures.Add(relative);}var diagnostics=InspectQuantities(canvas,canvas.transform,"capture-scale"+captureScale.ToString(System.Globalization.CultureInfo.InvariantCulture),image,camera);foreach(var diagnostic in diagnostics)Need(!diagnostic.culled&&diagnostic.groupAlpha>.9f&&diagnostic.triangleArea>.5f&&diagnostic.opaqueVertices>=4&&diagnostic.inkPixels>4,"CapturedBundleQuantityActuallyVisible_"+diagnostic.name+"_area"+diagnostic.triangleArea+"_ink"+diagnostic.inkPixels+"_font"+diagnostic.fontSize+"_preferredH"+diagnostic.preferredHeight+"_height"+diagnostic.height);}finally{scaler.scaleFactor=old;}}
            finally{canvas.renderMode=mode;canvas.worldCamera=previousCamera;canvas.planeDistance=distance;canvas.scaleFactor=scale;RenderTexture.active=prior;RenderTexture.ReleaseTemporary(target);if(image)UnityEngine.Object.DestroyImmediate(image);UnityEngine.Object.DestroyImmediate(cameraNode);}
        }
        public static void Run(){
            report=new Report{status="FAIL_NATIVE_SHOP_CHECKOUT86",utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,scope="Actual pinned Editor controller/PayDeliveryCoordinator and encrypted CAS disk journal using scripted SDK/catalog/authority/wallet callbacks. Unknown create/payment, explicit-only purchase, terminal proof, fresh authority, ownership fencing and projection ordering. Actual approved coin/Special/Mega Shop UGUI controls/text are rendered and measured against scripted verified quotes in five locales/two widths/three final pixel scales (1,1.832,3), with real captured quantity ink/triangle checks. Visual quote fixtures use approved current RUB amounts; arbitrary opaque SDK-label matching is a separate contract test. Full grants, eligibility, server acknowledgement lag, legacy encrypted journal migration, frozen recovery and presentation-outbox ordering are checked. Not real SDK/payment/HTTP, ordinary configured startup, Android restart, screenshot visual approval or production activation."};
            directory=Path.GetFullPath("../.verification-cache/Launch82/Checkout86Native/"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(directory);output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_CHECKOUT86_OUTPUT")??"../Verification/Evidence/ClientLifecycle86");
            Need(Application.unityVersion=="2022.3.62f3","PinnedEditor");Case("ExactSdkCatalogAndSandboxGuards",CatalogChecks);Case("FullInventoryBundleContracts100",BundleContracts);Case("TypedGrantAndEligibilityParser100",TypedGrantParser100);Case("LegacyCachedCreatorParser100",LegacyCachedCreatorParser100);Case("AtomicFullBundleProjection100",BundleSuccess);Case("ServerAcknowledgementLag100",AckLag);Case("FrozenTermsAndLegacyJournal100",FrozenAndLegacy);Case("ReceiptPresentationSaveFailure100",PresentationFault);Case("CrossDeviceUnknownOrder100",CrossDevice);Case("CrossDeviceConcurrentReservation100",ReservationRace);Case("LegacyUnknownCreatorLookupOnly100",LegacyCreatorUnknown);Case("DurableOrderBeforeSdkAndFreshAuthority",Success);Case("LostCreateReplyRestartRequiresExplicitPurchase",CreateLost);Case("UnknownPurchaseEmptyListRetainsExactOrder",UnknownPurchase);Case("DiskFailureAndExclusiveSdkDispatch",DiskFault);Case("ProjectionFailureRestartNoDoubleCredit",ProjectionFault);Case("InvalidatedOwnerFencesSdkCallback",Stale);Case("ServerTerminalProofNoCredit",Terminal);Case("ObservedProtectedOutboxDisappearanceFailsClosed",MissingStore);Case("ActualLocalizedShopBuyControls",Ui);Case("ActualNoMovesShopBuyControls",NoMovesUi);
            if(report.errors.Count==0)report.status="PASS_NATIVE_SHOP_CHECKOUT86";Directory.CreateDirectory(Path.Combine(output,"Native"));File.WriteAllText(Path.Combine(output,"Native","ShopCheckout86.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));if(Application.isBatchMode)EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif

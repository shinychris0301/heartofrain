using System;
using System.Collections;
using System.Collections.Concurrent;
using System.IO;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.ServerRewards;
using UnityEngine;

namespace HeartOfTheRain.App.ShopCheckout86 {
    [DisallowMultipleComponent] public sealed class ShopCheckoutHost86:MonoBehaviour {
        HomePage home;ServerGameSession session;CheckoutConfiguration86 configuration;ShopCheckoutFlow86 flow;
        readonly ConcurrentQueue<Action> callbacks=new ConcurrentQueue<Action>();string player,origin;bool inLevel;
        public event Action Changed;public bool Busy=>flow!=null&&flow.Busy;public bool Pending=>flow!=null&&flow.Pending;public bool Credited=>flow!=null&&flow.Credited;
        public string Error=>flow?.Error;public bool Configured=>configuration!=null;
        public string PendingProduct=>flow?.PendingProduct;
        public bool Sandbox=>configuration==null||configuration.sandbox;
        public bool Reading=>flow!=null&&flow.Reading;
        public string Price(string product)=>flow?.Price(product);
        public string Eligibility(string product)=>flow?.Eligibility(product);
        public bool CanBuy(string product)=>Eligible&&flow!=null&&flow.CanBuy(product);
        public static bool FirstModerationPurchasesDisabled {
            get {
#if HOTR_FIRST_MODERATION130
                return true;
#else
                return false;
#endif
            }
        }
        bool Eligible=>session&&session.Ready&&!session.AccountBlocked&&!session.HasPending&&(inLevel?session.Attempt?.state=="AwaitingContinuation":!session.HasActiveServerAttempt);
        public static ShopCheckoutHost86 Select(HomePage home){
            if(FirstModerationPurchasesDisabled)return null;
            if(!home)return null;var existing=home.GetComponent<ShopCheckoutHost86>();if(existing)return existing;
            CheckoutConfiguration86 config;var profile=home.GetComponent<PlayerProfileHost>();if(!CheckoutConfiguration86.TryRead(out config)||!profile||profile.LocalEconomyMode||!profile.ServerSession)return null;
            var result=home.gameObject.AddComponent<ShopCheckoutHost86>();result.home=home;result.configuration=config;return result;
        }
        void Post(Action callback){if(callback!=null)callbacks.Enqueue(callback);}
        void Update(){Action callback;for(int n=0;n<64&&callbacks.TryDequeue(out callback);n++)callback();}
        void Publish(){Changed?.Invoke();}
        void IdentityChanged(){if(!session||session.AccountBlocked||session.PlayerId!=player||session.Origin!=origin)flow?.Invalidate();}
        void Bind(){
            if(FirstModerationPurchasesDisabled){flow?.Dispose();flow=null;return;}
            var current=home?home.GetComponent<PlayerProfileHost>()?.ServerSession:null;
            if(current==session&&current&&current.PlayerId==player&&current.Origin==origin&&flow!=null)return;
            if(Busy)return;if(session)session.IdentityChanged-=IdentityChanged;flow?.Dispose();flow=null;session=current;player=origin=null;
            if(!session||!session.Ready||session.ProductionEnabled!=configuration.productionEnabled||(configuration.productionEnabled||configuration.Verification==CommerceVerificationMode125.SdkClientReported)&&(session.Origin!=configuration.backendOrigin||Application.identifier!=configuration.packageName))return;player=session.PlayerId;origin=session.Origin;session.IdentityChanged+=IdentityChanged;
            flow=new ShopCheckoutFlow86(configuration,Authorize,Refresh,access=>new ProtectedCheckoutJournal86(session.CreateProtectedCheckoutStore86(),access.Origin,access.Player,configuration.productionEnabled,configuration.verificationMode),authority=>new MainThreadStore(new RuStorePayAdapter(true,authority),Post),(owner,order)=>RewardPresentationJournal.ForPlayer(owner.Origin,owner.Player).Enqueue("commerce",order.credit.receiptId,order.credit.grant));flow.SetAuthorityDispatcher(value=>StartCoroutine(value));flow.Changed+=Publish;
        }
        IEnumerator Authorize(Action<CheckoutAccess86,string> done){
            if(!Eligible){done(null,"CheckoutEligibleShopRequired");yield break;}
            bool finished=false;ServerAuthorizedContext context=null;string why=null;session.WithAuthenticatedSession((value,error)=>{context=value;why=error;finished=true;});while(!finished&&session)yield return null;
            if(context==null||!session||context.PlayerId!=player||context.Origin!=origin||string.IsNullOrEmpty(context.CurrentAccess)){done(null,why??"CheckoutOwnerChanged");yield break;}
            var client=new RuStoreBackendClient(context.Origin,context.CurrentAccess,context.PlayerId,true,context.AllowDevelopmentLoopback,value=>StartCoroutine(value),context.ExpectedProduction,(context.ExpectedProduction||configuration.Verification==CommerceVerificationMode125.SdkClientReported)?long.Parse(configuration.consoleAppId,System.Globalization.CultureInfo.InvariantCulture):0,CommerceVerification125.Legacy(configuration.verificationMode));PayReply<RuStoreServerWallet> wallet=null;client.GetWallet(value=>wallet=value);while(wallet==null&&session)yield return null;
            if(!session||!Eligible||string.IsNullOrEmpty(context.CurrentAccess)||wallet==null||!wallet.Succeeded||!client.WalletReady){client.Dispose();done(null,wallet?.error?.code??"CheckoutFreshWalletRequired");yield break;}
            done(new CheckoutAccess86(context.Origin,context.PlayerId,context.Generation,new CheckoutBackend100(client),()=>this&&session&&session.PlayerId==player&&session.Origin==origin&&!session.AccountBlocked&&!string.IsNullOrEmpty(context.CurrentAccess)),null);
        }
        IEnumerator Refresh(Action<bool,string> done){bool finished=false,ok=false;string why=null;if(!session||session.PlayerId!=player||session.Origin!=origin){done(false,"CheckoutOwnerChanged");yield break;}session.Refresh((value,error)=>{ok=value;why=error;finished=true;});while(!finished&&session)yield return null;done(session&&ok,why);}
        IEnumerator Open(){yield return flow.Guard(flow.Refresh());if(flow.Pending&&!flow.Busy)yield return flow.Guard(flow.Recover());}
        public void Show(bool duringLevel=false){inLevel=duringLevel;Bind();if(flow!=null&&!Busy)StartCoroutine(Open());Publish();}
        public void Request(string action){
            if(FirstModerationPurchasesDisabled)return;
            if(Busy||string.IsNullOrEmpty(action))return;Bind();if(flow==null||!Eligible)return;
            if(action=="checkout:retry"){if(flow.Pending&&flow.PendingProduct!=null)StartCoroutine(flow.Guard(flow.Buy(flow.PendingProduct)));else StartCoroutine(Open());return;}
            const string prefix="checkout:buy:";if(action.StartsWith(prefix,StringComparison.Ordinal))StartCoroutine(flow.Guard(flow.Buy(action.Substring(prefix.Length))));
        }
        public static bool PendingOnDisk(ServerGameSession session){
            CheckoutConfiguration86 selected;string mode=CheckoutConfiguration86.TryRead(out selected)?CommerceVerification125.Legacy(selected.verificationMode):CommerceVerification125.ProviderApi;
            using(var journal=new ProtectedCheckoutJournal86(session.CreateProtectedCheckoutStore86(),session.Origin,session.PlayerId,session.ProductionEnabled,mode))return journal.Read().Pending;
        }
        void OnDestroy(){if(session)session.IdentityChanged-=IdentityChanged;flow?.Dispose();}
        sealed class MainThreadStore:IPayStore {
            readonly IPayStore inner;readonly Action<Action> post;public MainThreadStore(IPayStore inner,Action<Action> post){this.inner=inner;this.post=post;}
            Action<PayReply<T>> Marshal<T>(Action<PayReply<T>> done)where T:class=>reply=>post(()=>done(reply));
            public bool SdkCompiled=>inner.SdkCompiled;public bool Configured=>inner.Configured;
            public void GetPurchaseAvailability(Action<PayReply<PayAvailability>> done)=>inner.GetPurchaseAvailability(Marshal(done));
            public void GetProducts(string[] ids,Action<PayReply<PayProduct[]>> done)=>inner.GetProducts(ids,Marshal(done));
            public void Purchase(PayRequest request,Action<PayReply<PayLocator>> done)=>inner.Purchase(request,Marshal(done));
            public void GetPurchase(string id,Action<PayReply<PayPurchase>> done)=>inner.GetPurchase(id,Marshal(done));
            public void GetPurchases(Action<PayReply<PayPurchase[]>> done)=>inner.GetPurchases(Marshal(done));
            public void ConfirmTwoStep(PayRequest request,PayPurchase purchase,PayCaptureAuthorization authorization,Action<PayReply<PayAvailability>> done)=>inner.ConfirmTwoStep(request,purchase,authorization,Marshal(done));
            public void Acknowledge(PayRequest request,PayPurchase purchase,PayDeliveryReceipt receipt,Action<PayReply<PayAvailability>> done)=>inner.Acknowledge(request,purchase,receipt,Marshal(done));
        }
    }
}

namespace HeartOfTheRain.App.ServerGameplay {
    public sealed partial class ServerGameSession {
        // Distinct purpose/alias: never reuses or clears the social/identity outbox.
        public IProtectedSessionStore82 CreateProtectedCheckoutStore86(){
            if(!Ready)throw new InvalidOperationException("CheckoutSessionUnavailable");string scope="review-checkout-"+IdentityProtocol82.Sha(config.origin+"|"+PlayerId).Substring(0,32);IProtectedSessionStore82 storage;
#if UNITY_ANDROID && !UNITY_EDITOR
            storage=new AndroidDeviceIdentity82(scope);
#elif UNITY_EDITOR
            storage=editorVault.CreateStore(Path.GetFullPath("../.verification-cache/Launch82/Checkout86/"+scope+".sealed"));
#else
            throw new NotSupportedException();
#endif
            return new OriginBoundIdentityStore82(storage,config.origin+"|checkout|"+PlayerId);
        }
    }
}

using System;
using System.Collections.Concurrent;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.RuStore;
using UnityEngine;

namespace HeartOfTheRain.App.ShopCheckout86 {
    // Only the explicitly built local-economy channel can select this host.
    // It never creates an HTTP order or asks the game backend to credit a sale.
    [DisallowMultipleComponent] public sealed class DirectShopCheckoutHost132:MonoBehaviour {
        readonly ConcurrentQueue<Action> callbacks=new ConcurrentQueue<Action>();
        HomePage home;PlayerProfileHost profile;DirectPurchaseCoordinator flow;bool reading;
        public event Action Changed;
        public bool Configured=>flow!=null;public bool Busy=>flow!=null&&flow.Busy;public bool Reading=>reading;
        public bool Pending=>flow!=null&&flow.PendingProduct!=null;public string PendingProduct=>flow?.PendingProduct;
        public bool Credited=>flow!=null&&flow.Credited;public string Error=>flow?.Error;
        public string Price(string id)=>flow?.Price(id);
        public string Eligibility(string id)=>DirectPurchaseCatalog.Find(id)?.purchasable==true?"Available":"Unavailable";
        public bool CanBuy(string id)=>flow!=null&&flow.CanBuy(id);
        public static DirectShopCheckoutHost132 Select(HomePage home){
#if HOTR_DIRECT_PAY132 && !HOTR_FIRST_MODERATION130
            if(!home)return null;var profile=home.GetComponent<PlayerProfileHost>();
            if(!profile||!profile.Ready||!profile.LocalEconomyMode)return null;
            var existing=home.GetComponent<DirectShopCheckoutHost132>();if(existing)return existing;
            var host=home.gameObject.AddComponent<DirectShopCheckoutHost132>();host.home=home;host.profile=profile;return host;
#else
            return null;
#endif
        }
        void Post(Action value){if(value!=null)callbacks.Enqueue(value);}
        void Update(){for(int i=0;i<64&&callbacks.TryDequeue(out var callback);i++)callback();}
        void Bind(){if(flow!=null)return;
            var ledger=new DirectPurchaseLedger(profile.Service);
            bool sandbox=false;
#if HOTR_DIRECT_SANDBOX132
            sandbox=true;
#endif
            flow=new DirectPurchaseCoordinator(ledger,new MainThreadStore(new RuStorePayAdapter(true),Post),sandbox);
        }
        public void Show(){Bind();reading=true;Changed?.Invoke();flow.Refresh((ok,error)=>{
            reading=false;Changed?.Invoke();if(!ok||!Pending)return;
            flow.Recover((recovered,why)=>{if(flow.Credited)profile.Refresh();Changed?.Invoke();});
        });}
        public void Request(string action){if(string.IsNullOrEmpty(action))return;Bind();
            if(action=="checkout:retry"){if(Pending)flow.Recover((ok,error)=>{if(flow.Credited)profile.Refresh();Changed?.Invoke();});else Show();Changed?.Invoke();return;}
            const string prefix="checkout:buy:";if(!action.StartsWith(prefix,StringComparison.Ordinal))return;
            flow.Buy(action.Substring(prefix.Length),(ok,error)=>{if(flow.Credited)profile.Refresh();Changed?.Invoke();});Changed?.Invoke();
        }
        sealed class MainThreadStore:IDirectPurchaseStore {
            readonly IDirectPurchaseStore inner;readonly Action<Action> post;
            public MainThreadStore(IDirectPurchaseStore inner,Action<Action> post){this.inner=inner;this.post=post;}
            Action<PayReply<T>> Marshal<T>(Action<PayReply<T>> done)where T:class=>value=>post(()=>done(value));
            public bool SdkCompiled=>inner.SdkCompiled;public bool Configured=>inner.Configured;
            public void GetPurchaseAvailability(Action<PayReply<PayAvailability>> done)=>inner.GetPurchaseAvailability(Marshal(done));
            public void GetProducts(string[] ids,Action<PayReply<PayProduct[]>> done)=>inner.GetProducts(ids,Marshal(done));
            public void PurchaseDirect(PayRequest request,Action<PayReply<PayLocator>> done)=>inner.PurchaseDirect(request,Marshal(done));
            public void GetPurchase(string id,Action<PayReply<PayPurchase>> done)=>inner.GetPurchase(id,Marshal(done));
            public void GetPurchases(Action<PayReply<PayPurchase[]>> done)=>inner.GetPurchases(Marshal(done));
            public void AcknowledgeDirect(PayRequest request,PayPurchase purchase,DirectPurchaseReceipt receipt,Action<PayReply<PayAvailability>> done)=>inner.AcknowledgeDirect(request,purchase,receipt,Marshal(done));
        }
    }
}

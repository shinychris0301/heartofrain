using System;
using System.Text.RegularExpressions;
using System.Threading;
#if HOTR_YANDEX_ADS
using YandexMobileAds;
using YandexMobileAds.Base;
using UnityEngine;
#endif

namespace HeartOfTheRain.App.Advertising {
    // Optional provider only: construction never initializes, loads or shows
    // the SDK. Completion is client-reported information, not a wallet grant
    // or provider-authenticated server-side reward.
    public sealed class YandexRewardedAdsProvider85:IRewardedAdsProvider85 {
        readonly string unitId;readonly AdPrivacy85 privacy;readonly Action<Action> dispatch;
        readonly int ownerThread;readonly bool fixtureDemo;
        int disposed,generation;
#if HOTR_YANDEX_ADS
        RewardedAdLoader loader;RewardedAd ad;Timer loadDeadline;
        Action<bool,string> loadedCallback;Action<RewardedSignal85> showCallback;
        bool loading,showing,shown,rewarded,terminal;
#endif
        public YandexRewardedAdsProvider85(string unitId,AdPrivacy85 privacy,Action<Action> dispatch,bool allowFixtureDemo=false) {
            this.unitId=unitId;this.privacy=privacy;this.dispatch=dispatch??throw new ArgumentNullException(nameof(dispatch));
            ownerThread=Thread.CurrentThread.ManagedThreadId;
#if HOTR_YANDEX_ADS_ISOLATED_FIXTURE && DEVELOPMENT_BUILD
            fixtureDemo=allowFixtureDemo;
#else
            fixtureDemo=false;
#endif
        }
        public bool Installed {
            get {
#if HOTR_YANDEX_ADS && UNITY_ANDROID && !UNITY_EDITOR
                return Volatile.Read(ref disposed)==0;
#else
                return false;
#endif
            }
        }
        bool Current(int token) { return Volatile.Read(ref disposed)==0&&Volatile.Read(ref generation)==token; }
        bool Owner { get { return Thread.CurrentThread.ManagedThreadId==ownerThread; } }
        bool UnitValid { get { return unitId!=null&&(Regex.IsMatch(unitId,@"\AR-M-[1-9][0-9]{0,18}-[1-9][0-9]{0,18}\z")||(fixtureDemo&&unitId=="demo-rewarded-yandex")); } }
        void Post(Action action) {
            try { dispatch(()=>{if(Owner)action();}); }
            catch { /* No SDK data/exception content is logged. Owner disposal remains available. */ }
        }
        static void Complete(Action<bool,string> callback,bool success,string code) { try{callback(success,code);}catch{} }
        static void Signal(Action<RewardedSignal85> callback,RewardedSignal85 value) { try{if(callback!=null)callback(value);}catch{} }
        public void Load(Action<bool,string> complete) {
            if(complete==null)throw new ArgumentNullException(nameof(complete));
            if(!Owner){Post(()=>Complete(complete,false,"AdsOwnerThreadRequired"));return;}
            if(!Installed){Complete(complete,false,"AdsSdkUnavailable");return;}
            if(privacy==null||!privacy.Accepted){Complete(complete,false,"AdsPrivacyRequired");return;}
            if(!UnitValid){Complete(complete,false,"AdsBlockNotConfigured");return;}
#if HOTR_YANDEX_ADS
            if(loading||showing||ad!=null){Complete(complete,false,"AdsProviderBusy");return;}
            int token=Interlocked.Increment(ref generation);loading=true;terminal=false;shown=false;rewarded=false;loadedCallback=complete;
            try {
                // The manifest must disable automatic initialization. Set all
                // policy before even constructing the native loader. The
                // Unity facade omits the analytics switch, so use its native
                // documented SDK8 class for that one setting.
                using(var native=new AndroidJavaClass("com.yandex.mobile.ads.common.YandexAds"))native.CallStatic("setAppAdAnalyticsReporting",false);
                YandexAds.SetLocationTracking(false);
                YandexAds.SetAgeRestricted(privacy.AgeRestricted);
                YandexAds.SetUserConsent(privacy.Personalized&&!privacy.AgeRestricted);
                loader=new RewardedAdLoader();
                loadDeadline=new Timer(_=>Post(()=>{if(Current(token)&&loading)FinishLoad(token,null,"AdsLoadTimeout");}),null,45000,Timeout.Infinite);
                loader.LoadAd(new AdRequest(unitId),value=>Post(()=>FinishLoad(token,value,null)),failure=>Post(()=>FinishLoad(token,null,"AdsLoadFailed")));
            } catch { FinishLoad(token,null,"AdsLoadFailed"); }
#endif
        }
        public void Show(Action<RewardedSignal85> signal) {
            if(signal==null)throw new ArgumentNullException(nameof(signal));
            if(!Owner){Post(()=>Signal(signal,RewardedSignal85.Failed));return;}
            if(!Installed){Signal(signal,RewardedSignal85.Failed);return;}
#if HOTR_YANDEX_ADS
            if(loading||showing||ad==null){Signal(signal,RewardedSignal85.Failed);return;}
            int token=Volatile.Read(ref generation);showing=true;showCallback=signal;
            ad.OnAdShown+=(sender,args)=>Post(()=>{if(Current(token)&&showing&&!terminal&&!shown){shown=true;Signal(showCallback,RewardedSignal85.Shown);}});
            ad.OnRewarded+=(sender,args)=>Post(()=>{
                if(Current(token)&&showing&&shown&&!terminal&&!rewarded){rewarded=true;Signal(showCallback,RewardedSignal85.CompletedInfoOnly);}
            });
            ad.OnAdDismissed+=(sender,args)=>Post(()=>FinishShow(token,RewardedSignal85.Closed));
            ad.OnAdFailedToShow+=(sender,args)=>Post(()=>FinishShow(token,RewardedSignal85.Failed));
            try{ad.Show();}catch{FinishShow(token,RewardedSignal85.Failed);}
#endif
        }
#if HOTR_YANDEX_ADS
        void FinishLoad(int token,RewardedAd value,string code) {
            if(!Current(token)||!loading){Destroy(value);return;}
            loading=false;StopDeadline();CancelLoader();
            var callback=loadedCallback;loadedCallback=null;
            ad=value;
            if(ad==null){Complete(callback,false,code??"AdsLoadFailed");return;}
            Complete(callback,true,null);
        }
        void FinishShow(int token,RewardedSignal85 value) {
            if(!Current(token)||!showing||terminal)return;
            terminal=true;showing=false;var callback=showCallback;showCallback=null;
            var old=ad;ad=null;Destroy(old);Signal(callback,value);
        }
        void StopDeadline(){var old=loadDeadline;loadDeadline=null;if(old!=null)old.Dispose();}
        void CancelLoader(){var old=loader;loader=null;if(old!=null)try{old.CancelLoading();}catch{}}
        static void Destroy(RewardedAd value){if(value!=null)try{value.Destroy();}catch{}}
        void Cleanup(){StopDeadline();CancelLoader();var old=ad;ad=null;Destroy(old);loading=false;showing=false;terminal=true;loadedCallback=null;showCallback=null;}
#endif
        public void Dispose() {
            if(Interlocked.Exchange(ref disposed,1)!=0)return;
            Interlocked.Increment(ref generation);
#if HOTR_YANDEX_ADS
            if(Owner)Cleanup();else Post(Cleanup);
#endif
        }
    }
}

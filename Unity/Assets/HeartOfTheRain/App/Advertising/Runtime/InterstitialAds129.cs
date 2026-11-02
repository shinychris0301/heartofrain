using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Threading;
using UnityEngine;
#if HOTR_YANDEX_ADS
using YandexMobileAds;
using YandexMobileAds.Base;
#endif

namespace HeartOfTheRain.App.Advertising {
    public interface IInterstitialProvider129:IDisposable {
        bool Installed{get;}
        void Load(Action<bool> done);
        void Show(Action shown,Action done);
    }
    // Owner decision, 1 November 2026: at the start of levels 1, 6, 11, 16 and so on, never at
    // launch or after a win. Only the level the player is progressing through counts, once.
    public sealed class InterstitialPolicy129 {
        public const int LevelsBetween=5;
        public const string LastLevelKey="HeartOfTheRain.Interstitial129.lastShownLevel";
        readonly Func<string,int,int> read;readonly Action<string,int> write;public bool AnyLevel;
        public InterstitialPolicy129(Func<string,int,int> read,Action<string,int> write){this.read=read;this.write=write;}
        public bool Due(int level,int completed)=>AnyLevel||level%LevelsBetween==1&&level==completed+1&&level>read(LastLevelKey,0);
        public void Mark(int level){write(LastLevelKey,level);AnyLevel=false;}
    }
    // Grants nothing and contacts no game server. Level start waits only briefly: with
    // no ad ready the level starts, and the ad stays due if that level is started again.
    [DisallowMultipleComponent] public sealed class InterstitialAds129:MonoBehaviour {
        const float LoadSeconds=20,ShowSeconds=8,ResumeSeconds=3;
        public static InterstitialAds129 Instance{get;private set;}
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        public static Func<Action<Action>,IInterstitialProvider129> VerificationFactory;
        public static bool VerificationAnyLevel;
#endif
        readonly ConcurrentQueue<Action> callbacks=new ConcurrentQueue<Action>();
        InterstitialPolicy129 policy;Func<IInterstitialProvider129> factory;IInterstitialProvider129 provider;
        bool loading,loaded,showing;float loadDeadline,showDeadline;Action shownDone;
        public bool Showing=>showing;public bool Loaded=>loaded;public bool Loading=>loading;
        public static InterstitialAds129 Ensure(){
            if(Instance)return Instance;
            if(!Application.isPlaying)return null;
            Func<Action<Action>,IInterstitialProvider129> make=null;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(VerificationFactory!=null)make=VerificationFactory;
#endif
            if(make==null){
                RewardedAdsConfiguration85 config;
                if(!RewardedAdsConfiguration85.TryRead(out config)||config==null||!config.enabled||string.IsNullOrEmpty(config.interstitialUnitId))return null;
                string unit=config.interstitialUnitId;
                using(var probe=new YandexInterstitialProvider129(unit,_=>{}))if(!probe.Installed)return null;
                make=post=>new YandexInterstitialProvider129(unit,post);
            }
            var owner=new GameObject("Interstitial ads");DontDestroyOnLoad(owner);
            Instance=owner.AddComponent<InterstitialAds129>();
            var policy=new InterstitialPolicy129(Read,Write);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            policy.AnyLevel=VerificationAnyLevel;
#endif
            Instance.Configure(policy,make);
            return Instance;
        }
        static int Read(string key,int fallback)=>PlayerPrefs.GetInt(key,fallback);
        // Persist as soon as the SDK reports a show: an ad's landing page can get the game killed.
        static void Write(string key,int value){PlayerPrefs.SetInt(key,value);PlayerPrefs.Save();}
        public void Configure(InterstitialPolicy129 value,Func<Action<Action>,IInterstitialProvider129> make){policy=value;factory=()=>make(Post);}
        void Post(Action action){if(action!=null)callbacks.Enqueue(action);}
        void Update()=>Pump();
        public void Pump(){
            int count=0;Action callback;while(count++<16&&callbacks.TryDequeue(out callback))callback();
            if(loading&&Time.unscaledTime>loadDeadline)Release();
            // The ad pauses the game, so this only runs if it never opened or its close report was lost.
            if(showing&&Application.isFocused&&Time.unscaledTime>showDeadline)Finish();
        }
        void OnApplicationFocus(bool focused){if(focused&&showing)showDeadline=Time.unscaledTime+ResumeSeconds;}
        void Load(){
            if(loading||loaded||showing||factory==null)return;
            provider=factory();
            if(provider==null||!provider.Installed){Release();return;}
            loading=true;loadDeadline=Time.unscaledTime+LoadSeconds;
            var owner=provider;
            try{owner.Load(ok=>{if(owner!=provider||!loading)return;loading=false;loaded=ok;if(!ok)Release();});}catch(Exception){Release();}
        }
        void Release(){var old=provider;provider=null;loading=loaded=false;if(old!=null)try{old.Dispose();}catch(Exception){}}
        void Show(int level,Action done){
            loaded=false;showing=true;shownDone=done;showDeadline=Time.unscaledTime+ShowSeconds;
            var owner=provider;
            bool marked=false;
            Action mark=()=>{if(showing&&owner==provider&&!marked){marked=true;policy.Mark(level);}};
            try{owner.Show(mark,()=>{if(owner==provider)Finish();});}catch(Exception){Finish();}
        }
        void Finish(){if(!showing)return;showing=false;Release();var done=shownDone;shownDone=null;done?.Invoke();}
        // An ad loaded for a level the player left is released rather than held in memory.
        public void Prepare(int level,int completed){if(Due(level,completed))Load();else if(!showing)Release();}
        public bool Due(int level,int completed)=>policy!=null&&policy.Due(level,completed);
        // Runs before the attempt exists, so no life is at stake while the ad is open.
        public IEnumerator ShowForLevel(int level,int completed,float waitSeconds){
            if(!Due(level,completed))yield break;
            Load();float end=Time.unscaledTime+waitSeconds;
            while(loading&&Time.unscaledTime<end)yield return null;
            if(!loaded){Release();yield break;}
            bool finished=false;Show(level,()=>finished=true);
            while(!finished)yield return null;
        }
        void OnDestroy(){if(Instance==this)Instance=null;Release();}
    }
    public sealed class YandexInterstitialProvider129:IInterstitialProvider129 {
        readonly string unitId;readonly Action<Action> post;int disposed;
#if HOTR_YANDEX_ADS
        InterstitialAdLoader loader;Interstitial ad;
#endif
        public YandexInterstitialProvider129(string unitId,Action<Action> post){
#if HOTR_INTERSTITIAL_DEMO129 && DEVELOPMENT_BUILD
            unitId="demo-interstitial-yandex";
#endif
            this.unitId=unitId;this.post=post??throw new ArgumentNullException(nameof(post));
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
        public void Load(Action<bool> done){
#if HOTR_YANDEX_ADS
            // Same fixed policy as the rewarded provider, set before the native loader exists.
            using(var native=new AndroidJavaClass("com.yandex.mobile.ads.common.YandexAds"))native.CallStatic("setAppAdAnalyticsReporting",false);
            YandexAds.SetLocationTracking(false);YandexAds.SetAgeRestricted(true);YandexAds.SetUserConsent(false);
            loader=new InterstitialAdLoader();
            loader.LoadAd(new AdRequest(unitId),value=>post(()=>{if(Volatile.Read(ref disposed)!=0){if(value!=null)value.Destroy();return;}ad=value;done(value!=null);}),failure=>post(()=>done(false)));
#else
            done(false);
#endif
        }
        public void Show(Action shown,Action done){
#if HOTR_YANDEX_ADS
            if(ad==null){done();return;}
            ad.OnAdShown+=(sender,args)=>post(shown);
            ad.OnAdDismissed+=(sender,args)=>post(()=>{shown();done();});
            ad.OnAdFailedToShow+=(sender,args)=>post(done);
            ad.Show();
#else
            done();
#endif
        }
        public void Dispose(){
            if(Interlocked.Exchange(ref disposed,1)!=0)return;
#if HOTR_YANDEX_ADS
            var old=ad;ad=null;if(old!=null)try{old.Destroy();}catch(Exception){}
            loader=null;
#endif
        }
    }
}

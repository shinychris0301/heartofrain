using System;
using System.Collections;
using System.Collections.Concurrent;
using System.IO;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.OnlineIdentity;
using UnityEngine;

namespace HeartOfTheRain.App.Advertising {
    [DisallowMultipleComponent] public sealed class RewardedShop85:MonoBehaviour {
        HomePage home;ServerGameSession session;RewardedAdsFlow85 flow;RewardedAdsConfiguration85 config;
        readonly ConcurrentQueue<Action> callbacks=new ConcurrentQueue<Action>();string player,origin;bool visible;
        public event Action Changed;public bool ConsentOpen{get;private set;}
        public bool Busy=>flow!=null&&flow.Busy;public bool Reading=>flow!=null&&flow.Reading;public bool HasPending=>flow!=null&&flow.Pending;
        public bool Ready=>config!=null&&config.enabled&&session&&session.Ready&&flow!=null&&!Busy;
        public AdStatus85 Status=>flow?.Status;public string Error=>flow?.Error;
        public bool Rewarded=>flow?.Receipt!=null;
        public bool Configured=>config!=null&&config.enabled;
        bool? installed;public bool ProviderInstalled{get{if(config==null||!config.enabled)return false;if(installed==null)using(var p=new YandexRewardedAdsProvider85(config.rewardedUnitId,new AdPrivacy85(false),Post))installed=p.Installed;return installed.Value;}}
        public bool LoadingAd=>flow!=null&&flow.LoadingAd;public bool ReadFailed=>flow!=null&&flow.ReadFailed;
        public long ServerNow=>session?session.ServerTimeNow:0;public void CancelLoad(){flow?.CancelLoad();}
        public AdCardState85 Card()=>new AdCardState85{present=true,consent=ConsentOpen,pending=HasPending,installed=ProviderInstalled,busy=Busy,reading=Reading,loading=LoadingAd,ready=Ready,idle=Free(),readFailed=ReadFailed,rewarded=Rewarded,error=Error,status=Status,now=ServerNow};
        public static string JournalPath(string origin,string player)=>Path.Combine(Application.persistentDataPath,"ServerReview","Advertising",IdentityProtocol82.Sha(origin),player,"intent.json");
        public static bool PendingOnDisk(string origin,string player){var journal=new RewardedAdsJournal85(JournalPath(origin,player));AdIntent85 intent;string error;return journal.TryLoad(origin,player,out intent,out error)?intent!=null:error!=null;}
        public void Configure(HomePage value){home=value;installed=null;RewardedAdsConfiguration85.TryRead(out config);}
        void Post(Action action){if(action!=null)callbacks.Enqueue(action);}
        float nextTick,firstRead,nextRead;bool readForHome,firstReadDone;
        void Update(){int count=0;Action callback;while(count++<32&&callbacks.TryDequeue(out callback))callback();if(Time.unscaledTime>=nextTick){nextTick=Time.unscaledTime+1;Tick();}}
        // Keeps the card and the Home plate true over time: a session that became ready
        // behind an open Shop, a countdown, and a cooldown or daily limit that has passed.
        void Tick(){
            if(!Configured||!home)return;var economy=home.GetComponent<HeartOfTheRain.App.Profile.PlayerProfileHost>();if(economy&&economy.LocalEconomyMode)return;
            var current=home.GetComponent<ServerGameSession>();
            if(visible&&!Busy&&flow==null&&current&&current.Ready){Bind();if(flow!=null)StartCoroutine(flow.Guard(flow.Refresh()));}
            if(visible)Publish();
            if(Busy||!current||!current.Ready||current.Busy||current.HasPending||current.HasActiveServerAttempt||!visible&&!home.PresentationInteractable)return;
            // Home's badges read first after a cold start. This is one read for the plate, not a poll.
            if(firstRead==0){firstRead=Time.unscaledTime+5;return;}if(Time.unscaledTime<firstRead||Time.unscaledTime<nextRead)return;
            Bind();if(flow==null)return;bool first=!firstReadDone&&!visible&&flow.Status==null;
            if(!first&&!AdShopView85.Expired(flow.Status,current.ServerTimeNow))return;
            firstReadDone=true;nextRead=Time.unscaledTime+60;readForHome=!visible;StartCoroutine(flow.Guard(flow.Refresh()));
        }
        void Publish(){if(!Busy)readForHome=false;Changed?.Invoke();}
        void Bind(){
            var current=home?home.GetComponent<ServerGameSession>():null;
            if(current==session&&current&&current.Ready&&current.PlayerId==player&&current.Origin==origin&&flow!=null)return;
            if(flow!=null&&flow.Busy)return;
            if(session)session.IdentityChanged-=IdentityChanged;
            flow?.Dispose();flow=null;session=current;player=origin=null;
            if(!session||!session.Ready)return;
            player=session.PlayerId;origin=session.Origin;session.IdentityChanged+=IdentityChanged;
            flow=new RewardedAdsFlow85(new RewardedAdsClient85(),new RewardedAdsJournal85(JournalPath(origin,player)),Authorize,RefreshWallet,p=>new YandexRewardedAdsProvider85(config?.rewardedUnitId,p,Post),()=>Application.isFocused);flow.Changed+=Publish;
        }
        void IdentityChanged(){if(!session||session.AccountBlocked||session.PlayerId!=player||session.Origin!=origin){ConsentOpen=false;flow?.Invalidate();Publish();}}
        bool Idle(){return (visible||readForHome)&&Free();}
        bool Free(){var level=home?home.GetComponent<HomeLevelFlow>():null;var pre=home?home.GetComponent<PreLevelModal>():null;return home&&!(level&&level.Playing)&&!(pre&&pre.IsVisible)&&session&&session.Ready&&!session.HasPending&&!session.HasActiveServerAttempt;}
        IEnumerator Authorize(Action<ServerAuthorizedContext,string> done){
            if(!Idle()){done(null,"AdsIdleShopRequired");yield break;}
            bool finished=false;ServerAuthorizedContext context=null;string error=null;session.WithAuthenticatedSession((value,why)=>{context=value;error=why;finished=true;});
            while(!finished&&session)yield return null;done(context,error??(context==null?"AdsSessionUnavailable":null));
        }
        IEnumerator RefreshWallet(Action<bool,string> done){bool finished=false,success=false;string error=null;
            if(!session||session.PlayerId!=player||session.Origin!=origin){done(false,"AdsOwnerChanged");yield break;}
            session.Refresh((ok,why)=>{success=ok;error=why;finished=true;});while(!finished&&session)yield return null;done(success,error);
        }
        public void Show(){visible=true;Bind();if(flow!=null&&!Busy)StartCoroutine(flow.Guard(flow.Refresh()));Publish();}
        public void Hide(){if(Busy&&!Reading)return;visible=false;ConsentOpen=false;}
        public void Request(string action){if(!visible||Busy)return;Bind();
            if(action=="ad:close"){ConsentOpen=false;Publish();return;}
            if(action=="ad:privacy"){if(config!=null)Application.OpenURL(config.privacyUrl);return;}
            if(action=="ad:retry"){ConsentOpen=false;if(flow!=null&&Idle())StartCoroutine(flow.Guard(flow.Pending?flow.Recover():flow.Refresh()));return;}
            if(action=="ad:watch"){if(Ready&&ProviderInstalled&&Idle()){ConsentOpen=true;Publish();}return;}
            // A fresh explicit decision for each video. No silent SDK request
            // from opening Shop and no reuse of another feature's consent.
            if(action=="ad:accept"&&ConsentOpen&&Ready&&ProviderInstalled&&Idle()){ConsentOpen=false;StartCoroutine(flow.Guard(flow.Watch(new AdPrivacy85(true,false,true))));}
        }
        void OnDestroy(){if(session)session.IdentityChanged-=IdentityChanged;flow?.Dispose();}
    }
}

using System;
using System.IO;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.ServerRewards;
namespace HeartOfTheRain.App.Profile {
    [DisallowMultipleComponent] public sealed class PlayerProfileHost:MonoBehaviour {
        public ProfileService Service {get;private set;}
        public ServerGameSession ServerSession {get;private set;}
        public bool LocalEconomyMode {get;private set;}
        public ProfileEventFeed Events {get;private set;}
        public DailyGiftService Gifts {get;private set;}
        public BackendGiftSession BackendGifts {get;private set;}
        public GiftSchedule Schedule {get;private set;}
        public WellworksService Wellworks {get;private set;}
        public IRainCupService Cup {get;private set;}
        public bool IsTransient {get;private set;}
        public bool Ready {get;private set;}
        public bool ApplyingView {get;private set;}
        public string LastError {get;private set;}
        HomePage home;PreLevelAssets assets;long displayedDay;int displayedLocale;bool refreshOnHome,startupRecovered;
        RainCupSnapshot cupSnapshot;float nextCupTick;long nextLifeDue;int displayedLives,displayedMaxLives;float nextLifeRead,lifeReadDelay=5;string walletShown;
        ServerRewardsSession serverRewards;float nextServerBadgeTick,nextServerStart,serverStartDelay=10;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        [NonSerialized] public IProfileRepository VerificationRepository;
        [NonSerialized] public Func<string,IDailyGiftAuthority> VerificationAuthorityFactory;
        [NonSerialized] public Func<long> VerificationCupClock;
        [NonSerialized] public Func<long> VerificationLivesClock;
        [NonSerialized] public BackendClient VerificationBackendClient;
#endif
        // Device UTC seconds for life regeneration; untrusted until a time
        // service exists (the model stalls on a clock that moved backwards).
        public long Now(){
            if(ServerSession&&ServerSession.Ready)return ServerSession.ServerTimeNow;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(VerificationLivesClock!=null)return VerificationLivesClock();
#endif
            return DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        }
        // Seconds until the next life from the last applied profile, or -1.
        public long NextLifeIn=>!Ready||displayedLives>=displayedMaxLives||nextLifeDue<=0?-1:Math.Max(0,nextLifeDue-Now());
        public bool LifeDue=>Ready&&nextLifeDue>0&&displayedLives<displayedMaxLives&&Now()>=nextLifeDue;
        public void Initialize(HomePage home,PreLevelAssets assets){
            if(Service!=null)return;this.home=home;this.assets=assets;
            IProfileRepository repository=null;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(VerificationBackendClient!=null&&VerificationRepository==null)throw new InvalidOperationException("Backend review requires an isolated repository");
            var first=home.GetComponent<FirstStartPage>();IsTransient=first&&first.reviewAlways&&VerificationRepository==null;
            repository=VerificationRepository;
#endif
            if(repository==null&&!IsTransient)ServerSession=ServerGameSession.Select(home);
#if HOTR_DIRECT_PAY132 && !HOTR_FIRST_MODERATION130
            LocalEconomyMode=repository==null&&!IsTransient;
            if(LocalEconomyMode){
                repository=new FileProfileRepository(Path.Combine(Application.persistentDataPath,"Profiles","Direct132-v1"),CreateDirectProfile);
                if(ServerSession)ServerSession.Changed+=ApplyServerView;
            }
#endif
            if(ServerSession&&!LocalEconomyMode){repository=ServerSession.Projection;ServerSession.Changed+=ApplyServerView;serverRewards=ServerRewardsSession.Select(ServerSession);}
            if(repository==null)repository=IsTransient?(IProfileRepository)new MemoryProfileRepository(PlayerProfile.New(assets.initialStock)):new FileProfileRepository(ProfileDirectory(),()=>PlayerProfile.New(assets.initialStock));
            Service=new ProfileService(repository);if(!ServerSession||LocalEconomyMode)Events=new ProfileEventFeed(Service);
            else{ConfigureServices(Service.Read());Apply(Service.Read());}
            Refresh();
            var page=home.GetComponent<DailyGiftPage>();if(!page)page=home.gameObject.AddComponent<DailyGiftPage>();page.Configure(home,assets,this);
            var works=home.GetComponent<WellworksPage>();if(!works)works=home.gameObject.AddComponent<WellworksPage>();works.Configure(home,assets,this);
            var cup=home.GetComponent<RainCupPage>();if(!cup)cup=home.gameObject.AddComponent<RainCupPage>();cup.Configure(home,assets,this);
            var receipts=home.GetComponent<RewardReceiptPresenter>();if(!receipts)receipts=home.gameObject.AddComponent<RewardReceiptPresenter>();receipts.Configure(home,this,assets);
        }
        PlayerProfile CreateDirectProfile(){
            var wallet=ServerSession?.Wallet;
            return DirectEconomyMigration132.Create(wallet,ServerSession&&ServerSession.Ready,ServerSession&&ServerSession.HasPending);
        }
        void ConfigureServices(PlayerProfile player){
            if(Cup==null){Cup=new UnavailableRainCupService();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                if(!ServerSession)try{var resource=Resources.Load<TextAsset>("HOTR_RainCup/Rules");if(resource)Cup=new DevelopmentRainCupService(Service,JsonUtility.FromJson<RainCupRules>(resource.text),VerificationCupClock??(()=>DateTimeOffset.UtcNow.ToUnixTimeSeconds()));}catch(Exception){Cup=new UnavailableRainCupService();}
#endif
            }
            if(Wellworks==null){var config=Resources.Load<TextAsset>("HOTR_Wellworks/Schedule");if(!config)throw new InvalidOperationException("Missing Wellworks schedule");bool enabled=false;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                enabled=!ServerSession;
#endif
                Wellworks=new WellworksService(Service,JsonUtility.FromJson<WellworksSchedule>(config.text),enabled);
            }
            if(Schedule==null){var resource=Resources.Load<TextAsset>("HOTR_DailyGift/Schedule");if(!resource)throw new InvalidOperationException("Missing Daily Gift schedule");Schedule=JsonUtility.FromJson<GiftSchedule>(resource.text);}Schedule.Validate();
            if(Gifts!=null)return;IDailyGiftAuthority authority=new UnavailableGiftAuthority();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                if(ServerSession){ /* Server claims use the async gateway; never local ApplyGrant. */ }
                else if(VerificationBackendClient!=null){
                    if(VerificationRepository==null)throw new InvalidOperationException("Backend review requires an isolated repository");
                    BackendGifts=new BackendGiftSession(Service,VerificationBackendClient,Schedule);
                }
                else if(VerificationAuthorityFactory!=null)authority=VerificationAuthorityFactory(player.playerId);
                else{
                    var initial=new PlayerProfile{playerId=player.playerId,coins=0,starting=new int[4],tools=new int[4]};
                    IProfileRepository ledger=IsTransient?(IProfileRepository)new MemoryProfileRepository(initial):new FileProfileRepository(Path.Combine(ProfileDirectory(),"DailyGiftDevelopmentAuthority"),()=>initial);
                    authority=new DevelopmentGiftAuthority(ledger,()=>DateTimeOffset.UtcNow.ToUnixTimeSeconds()/86400,Schedule);
                }
#endif
            Gifts=new DailyGiftService(Service,authority,Schedule);
        }
        static string ProfileDirectory(){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            return Path.Combine(Application.persistentDataPath,"Profiles","Development-v1");
#else
            return Path.Combine(Application.persistentDataPath,"Profiles","Player-v1");
#endif
        }
        public bool Refresh(){
            if(ServerSession&&!LocalEconomyMode){
                if(!ServerSession.Ready){ServerSession.RetryInitialize();Apply(Service.Read());Ready=false;if(home.LifeFeedback)home.LifeFeedback.Unavailable();LastError="Server progress is unavailable. Please try again.";return false;}
                try{var current=Service.Read();if(home.LifeFeedback)home.LifeFeedback.View.Seed(current);ConfigureServices(current);Apply(current);Ready=true;LastError="";return true;}
                catch(Exception){Ready=false;LastError="Server progress is unavailable. Please try again.";return false;}
            }
            try{var player=Service.Read();if(home.LifeFeedback)home.LifeFeedback.View.Seed(player);ConfigureServices(player);if(!startupRecovered){Service.RecoverInterrupted();startupRecovered=true;}Service.RegenerateLives(Now());player=Service.Read();Apply(player);Ready=true;LastError="";return true;}catch(Exception){Ready=false;if(home.LifeFeedback)home.LifeFeedback.Unavailable();LastError="Your saved game could not be loaded. Please try again.";return false;}
        }
        void Apply(PlayerProfile p){
            var state=home.State;state.walletUnavailable=ServerSession&&!ServerSession.Ready&&!LocalEconomyMode;state.currentLevel=p.currentLevel;state.coins=p.coins;state.stars=p.stars;state.lives=p.lives;state.maxLives=p.maxLives;state.chapterNumber=1;state.completedLevelsInChapter=p.completed;
            if(nextLifeDue!=p.livesRefillDueUnix){nextLifeRead=0;lifeReadDelay=5;}nextLifeDue=p.livesRefillDueUnix;displayedLives=p.lives;displayedMaxLives=p.maxLives;
            if(ServerSession&&!LocalEconomyMode){serverRewards.ObserveHomeScope(p.completed,Now()/86400);cupSnapshot=null;state.dailyStatus=serverRewards.HomeDailyBadge;state.wellworksStatus=serverRewards.HomeWellworksBadge;state.cupStatus=serverRewards.HomeCupBadge;}
            else{state.dailyStatus=Gifts==null?"Unavailable":Badge();state.wellworksStatus=Wellworks==null?"Unavailable":Wellworks.Badge(p);try{cupSnapshot=Cup.View();state.cupStatus=RainCupModel.Badge(cupSnapshot,Cup.Remaining(cupSnapshot));}catch(Exception){cupSnapshot=null;state.cupStatus="Unavailable";}}ApplyingView=true;try{home.ApplyState(state);}finally{ApplyingView=false;}
            if(home.LifeFeedback)home.LifeFeedback.Observe(p,Now());
            displayedDay=DateTimeOffset.UtcNow.ToUnixTimeSeconds()/86400;displayedLocale=HeartOfTheRain.App.Localization.GameLocale.Revision;refreshOnHome=false;
        }
        string Badge(){try{var p=Service.Read();if(p.pendingGift!=null)return DailyGiftText.T("Please try again");var offer=BackendGifts!=null?BackendGifts.Offer:Gifts.Offer();return offer==null?"Unavailable":offer.claimed?DailyGiftText.T("Tomorrow"):"Ready";}catch(Exception){return "Unavailable";}}
        // A periodic wallet read usually changes nothing: keep Home's nodes under the
        // player's finger unless something the header shows actually moved.
        void ApplyServerView(){
            if(LocalEconomyMode){if(Service!=null&&!Ready)Refresh();return;}
            if(Service==null)return;string shown=ServerSession?ServerSession.WalletDisplaySignature:null;
            if(shown!=null&&shown==walletShown&&Ready)return;walletShown=shown;Refresh();
        }
        void OnApplicationFocus(bool focused){if(focused){refreshOnHome=true;if(nextServerStart>0)nextServerStart=Time.unscaledTime;}}
        void ApplyServerRewardBadges(){var state=home.State;PatchServerBadge("daily",serverRewards.HomeDailyBadge,ref state.dailyStatus);PatchServerBadge("wellworks",serverRewards.HomeWellworksBadge,ref state.wellworksStatus);PatchServerBadge("cup",serverRewards.HomeCupBadge,ref state.cupStatus);}
        void PatchServerBadge(string id,string value,ref string current){if(current==value)return;current=value;home.UpdateLabel(id+"-status",value);home.UpdateLabel("drawer-"+id+"-status",value);}
        // A failed start has nothing else to wake it: the failure report arrives while its own
        // start is still running, and the rest of Update needs a ready session.
        void RetryServerStart(){
            if(!ServerSession||ServerSession.Ready||ServerSession.Busy||!home.PresentationVisible)return;
            if(nextServerStart==0){nextServerStart=Time.unscaledTime+5;return;}
            if(Time.unscaledTime<nextServerStart)return;
            nextServerStart=Time.unscaledTime+serverStartDelay;serverStartDelay=Mathf.Min(serverStartDelay*2,60);ServerSession.RetryInitialize();
        }
        void Update(){RetryServerStart();if(!Ready||!home.PresentationVisible||home.RewardRevealPlaying)return;var flow=home.GetComponent<HomeLevelFlow>();if(!flow||!flow.CanOpenAppSettings)return;
            bool serverLifeDue=ServerSession&&!LocalEconomyMode&&LifeDue;
            if(refreshOnHome||displayedLocale!=HeartOfTheRain.App.Localization.GameLocale.Revision||displayedDay!=DateTimeOffset.UtcNow.ToUnixTimeSeconds()/86400||LifeDue&&!serverLifeDue){if(ServerSession&&!LocalEconomyMode&&!ServerSession.Busy)ServerSession.Refresh();Refresh();}
            // The server owns regeneration: ask it once, backing off if it fails or has
            // not moved the timer. Its reply rebuilds Home through ApplyServerView.
            else if(serverLifeDue&&Time.unscaledTime>=nextLifeRead&&!ServerSession.Busy){nextLifeRead=Time.unscaledTime+lifeReadDelay;lifeReadDelay=Mathf.Min(lifeReadDelay*2,60);ServerSession.Refresh();}
            if(ServerSession&&!LocalEconomyMode&&home.PresentationInteractable&&Time.unscaledTime>=nextServerBadgeTick){nextServerBadgeTick=Time.unscaledTime+1;serverRewards.PollHomeMetadata(home.State.completedLevelsInChapter,Now()/86400);ApplyServerRewardBadges();}
            if(cupSnapshot?.state=="Active"&&Time.unscaledTime>=nextCupTick){nextCupTick=Time.unscaledTime+1;try{long left=Cup.Remaining(cupSnapshot);if(left==0){Refresh();return;}string badge=RainCupModel.Badge(cupSnapshot,left);if(home.State.cupStatus!=badge){home.State.cupStatus=badge;bool main=home.UpdateLabel("cup-status",badge),drawer=home.UpdateLabel("drawer-cup-status",badge);if(!main&&!drawer){ApplyingView=true;try{home.ApplyState(home.State);}finally{ApplyingView=false;}}}}catch(Exception){cupSnapshot=null;}}
        }
        // Existing opt-in fixtures intentionally edit Home state. Mirror those
        // edits only into their disposable in-memory repository, never a save.
        public void ImportTransientView(HomeState state){
            if(!IsTransient||ApplyingView||!Ready)return;
            Service.Change(p=>{p.coins=state.coins;p.stars=state.stars;p.lives=state.lives;p.maxLives=state.maxLives;p.completed=Math.Min(50,Math.Max(state.currentLevel-1,(state.chapterNumber-1)*50+state.completedLevelsInChapter));p.currentLevel=Math.Min(state.currentLevel,Math.Min(50,p.completed+1));return true;});
            if(home.LifeFeedback)home.LifeFeedback.Observe(Service.Read(),Now());
        }
        public void ShowSaveError(Action retry,Action dismiss=null){var page=home.GetComponent<DailyGiftPage>();if(page)page.ShowError(retry,dismiss,null,ServerSession&&!LocalEconomyMode);}
        // Over Home the player can always close it, and it clears itself once the account loads.
        public void ShowHomeError(Action retry,Func<bool> settled=null){var page=home.GetComponent<DailyGiftPage>();if(page)page.ShowError(retry,()=>home.SetPresentation(true,true),settled,ServerSession&&!LocalEconomyMode);}
        void OnDestroy(){if(ServerSession)ServerSession.Changed-=ApplyServerView;}
    }
}

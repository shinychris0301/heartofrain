using System;
using HeartOfTheRain.App.Celebrations;
using HeartOfTheRain.App.GameplayLoading;
using System.Collections;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Settings;
using HeartOfTheRain.App.EndLevel;
using HeartOfTheRain.App.LevelComplete;
using HeartOfTheRain.App.Journey;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.App.Profile;
namespace HeartOfTheRain.App.PreLevel
{
    [DisallowMultipleComponent]
    public sealed partial class HomeLevelFlow:MonoBehaviour
    {
        public HomePage home;public PreLevelAssets assets;public GameplaySettingsAssets settingsAssets;public EndLevelAssets endLevelAssets;
        PreLevelSession session;PreLevelModal modal;GameplayScreen gameplay;readonly LevelCompleteSession completion=new LevelCompleteSession();
        readonly BoosterInventory tools=new BoosterInventory();bool failureSettled;int completionSerial;
        PlayerProfileHost profile;string attemptId;readonly ToolSpendReconciliation toolSpend=new ToolSpendReconciliation();bool finishingLaunch;
        string refillKey;float nextLifeTick;
        GameplayLoadingPage loading;PreLevelTicket launchTicket;int launchGeneration;ResourceRequest artRequest;float launchDeadline,pausedAt=-1;bool levelAdOpen;
        public GameplayLoadingPage Loading=>loading;
        long? cupWinTime;bool cupWinTimeCaptured;
        // Snapshots are read from a button handler: a transient read failure
        // falls back to the in-memory stock instead of throwing out of the click.
        public int[] ToolStockSnapshot(){int[] stock=null;try{if(profile&&profile.Ready)stock=(int[])profile.Service.Read().tools.Clone();}catch(Exception){}return stock??new[]{tools.hammer,tools.axe,tools.ram,tools.atlas};}
        public PreLevelViewData Preview {get{return session==null?null:session.View;}}
        public bool Playing {get{return gameplay&&gameplay.Ready;}}
        public bool CanOpenAppSettings {get{return session!=null&&!session.IsOpen&&!gameplay&&!session.View.busy&&(!loading||!loading.IsVisible);}}
        public int[] StartingStockSnapshot(){int[] stock=null;try{if(profile&&profile.Ready)stock=(int[])profile.Service.Read().starting.Clone();}catch(Exception){}return stock??(session==null?new int[4]:Enumerable.Range(0,4).Select(i=>session.Count(i)).ToArray());}
        public bool RetryVisible {get{return session!=null&&session.IsOpen&&session.View.retry&&modal&&modal.IsVisible;}}
        void Start()
        {
            if(!home||!assets||!assets.home||!assets.gameplay){Debug.LogError("Assign Home and PreLevelAssets.",this);enabled=false;return;}
            home.Build();profile=home.GetComponent<PlayerProfileHost>();if(!profile)profile=home.gameObject.AddComponent<PlayerProfileHost>();profile.Initialize(home,assets);
            session=new PreLevelSession(profile.Ready?profile.Service.Read().starting:assets.initialStock);SyncTools();modal=gameObject.AddComponent<PreLevelModal>();modal.home=home;modal.assets=assets;modal.Requested=Handle;
            loading=gameObject.AddComponent<GameplayLoadingPage>();loading.home=home;loading.font=assets.home.boldFont;loading.RetryRequested=RetryLoading;loading.BackRequested=BackFromLoading;loading.Prepare();
            home.PreLevelRequested.AddListener(Open);home.NavigationRequested.AddListener(OpenLives);
            StartCoroutine(M68CelebrationAssets.Warmup());
            if(Server)StartCoroutine(AwaitServerRestore());
            else if(profile.Ready&&profile.Service.Read().attempts.Any(a=>a.state=="Started"&&ContinueJournal.Restorable(a)))StartCoroutine(RestoreContinueAttempt());
        }
        void OpenLives(string action)
        {
            if(action!="lives"||!CanOpenAppSettings||(Server&&Server.Busy))return;
            if(WaitingForAccount){AfterAccount(()=>OpenLives(action));return;}
            if(!profile.Refresh()){profile.ShowHomeError(()=>OpenLives(action),AccountSettled);return;}
            home.ShowEvents(false);session.OpenLives(home.State.lives,home.State.maxLives);SyncLifeTimer();home.SetPresentation(true,false);modal.Show(session.View);
        }
        public void Open(int level){
            // Until the wallet answers, Home's level is only a placeholder.
            if(WaitingForAccount){AfterAccount(()=>Open(home.State.currentLevel));return;}
            OpenPreview(level,false);
        }
        bool WaitingForAccount=>Server&&(!Server.Ready||home.State.walletUnavailable);
        bool AccountSettled()=>Server&&Server.Ready&&!Server.Busy;
        const float AccountWaitSeconds=2;
        // A brief wait is normal on every cold start. Past that, say so instead of ignoring the tap.
        void AfterAccount(Action proceed){if(!openQueued){openQueued=true;StartCoroutine(AwaitAccount(proceed));}}
        IEnumerator AwaitAccount(Action proceed){
            Server.RetryInitialize();float deadline=Time.unscaledTime+AccountWaitSeconds;
            while(Server&&!Server.Ready&&Time.unscaledTime<deadline)yield return null;
            openQueued=false;if(!Server||!home.PresentationInteractable)yield break;
            if(!Server.Ready||!profile.Refresh()){profile.ShowHomeError(proceed,AccountSettled);yield break;}
            proceed();
        }
        // A wallet read or authorization is brief: honour the player's tap once it ends.
        bool openQueued;
        System.Collections.IEnumerator OpenWhenServerIdle(int level,bool retry){
            float deadline=Time.unscaledTime+20;while(Server&&Server.Busy&&Time.unscaledTime<deadline)yield return null;
            openQueued=false;if(Server&&!Server.Busy&&home.PresentationInteractable)OpenPreview(level,retry);
        }
        void OpenPreview(int level,bool retry)
        {
            if(session==null||gameplay||session.View.busy||completion.IsOpen||(loading&&loading.IsVisible))return;
            if(Server&&Server.Busy){if(!openQueued){openQueued=true;StartCoroutine(OpenWhenServerIdle(level,retry));}return;}
            if(!profile.Refresh()){if(home.PresentationInteractable)profile.ShowHomeError(()=>OpenPreview(level,retry),AccountSettled);else profile.ShowSaveError(()=>OpenPreview(level,retry));return;}
            session.RefreshStock(profile.Service.Read().starting);SyncTools();
            int index=Mathf.Clamp(level-1,0,assets.gameplay.boards.levels.Length-1);
            var data=JsonUtility.FromJson<LevelData>(assets.gameplay.boards.levels[index].text);
            int completed=CompletedLevels();bool rewardEligible=index+1==completed+1;
            session.Open(index+1,home.State.lives,data.goals.Select(g=>new PreLevelGoal{family=g.family,count=g.count}).ToArray(),rewardEligible?assets.rewardCoins:0,rewardEligible?assets.rewardStars:0,retry:retry);
            SyncLifeTimer();home.SetPresentation(true,false);modal.Show(session.View);EnsureLoadingArt();
            var ads=HeartOfTheRain.App.Advertising.InterstitialAds129.Ensure();if(ads)ads.Prepare(index+1,completed);
        }
        int CompletedLevels()=>Math.Max(home.State.currentLevel-1,(home.State.chapterNumber-1)*50+home.State.completedLevelsInChapter);
        // The loading screen's uncompressed art (≈38 MB) is resident only while a pre-level is open or a
        // launch is in flight; it loads asynchronously behind the modal and is released at the board handoff.
        void EnsureLoadingArt(){if(!loading||loading.art||artRequest!=null)return;artRequest=GameplayLoadingAssets.LoadAsync();StartCoroutine(AwaitLoadingArt(artRequest));}
        IEnumerator AwaitLoadingArt(ResourceRequest request){
            yield return request;var art=request.asset as GameplayLoadingAssets;
            if(artRequest!=request||!loading){if(artRequest!=request&&art)art.Release();yield break;}
            artRequest=null;if(!art)yield break;loading.art=art;loading.Rebuild();
        }
        void ReleaseLoadingArt(){artRequest=null;if(!loading||!loading.art)return;var art=loading.art;loading.art=null;loading.Rebuild();art.Release();}
        void OnApplicationPause(bool paused){if(paused)pausedAt=Time.realtimeSinceStartup;else if(pausedAt>=0){launchDeadline+=Time.realtimeSinceStartup-pausedAt;pausedAt=-1;}}
        void SyncLifeTimer(){if(session==null||!session.IsOpen)return;long seconds=profile.NextLifeIn;session.RefreshLifeTimer(seconds<0?-1:(int)Math.Min(int.MaxValue,seconds),session.View.lives<=0&&home.State.coins>=LifeRules.RefillCoins,LifeRules.RefillCoins);}
        void Update()
        {
            if(session==null||!session.IsOpen||session.View.busy)return;
            if(session.View.lives!=home.State.lives){RefreshLifeState();modal.Show(session.View);return;}
            // At zero lives the modal counts down once a second and picks up
            // the credited life when it is due.
            if((session.View.lives>0&&!session.View.livesOnly)||session.View.lives>=home.State.maxLives||Time.unscaledTime<nextLifeTick)return;nextLifeTick=Time.unscaledTime+1;
            int beforeLives=session.View.lives,before=session.View.nextLifeSeconds;bool refill=session.View.canRefill;
            if(profile.LifeDue){if(Server)RefreshServerLifeDue();else if(profile.Refresh())RefreshLifeState();}
            SyncLifeTimer();
            if(session.View.lives!=beforeLives||session.View.nextLifeSeconds!=before||session.View.canRefill!=refill)modal.Show(session.View);
        }
        void RefreshLifeState()
        {
            session.RefreshLives(home.State.lives);
            if(session.View.livesOnly){session.View.maxLives=home.State.maxLives;if(session.View.lives>0)session.View.message="";}
            SyncLifeTimer();
        }
        // Paid refill at zero lives (LifeRules). The key makes a retry after a
        // lost save confirmation return the same receipt instead of debiting twice.
        void RefillLives()
        {
            if(session==null||!session.IsOpen||session.View.busy||session.View.lives>0)return;
            if(Server){ServerRefill();return;}
            string key=refillKey??(refillKey=Guid.NewGuid().ToString("N"));
            try{profile.Service.RefillLives(key,profile.Now());refillKey=null;}
            catch(InvalidOperationException ex){refillKey=null;session.View.message=ex.Message=="Not enough coins"?"Not enough coins":"No lives remaining";}
            catch(Exception){profile.ShowSaveError(RefillLives);return;}
            if(!profile.Refresh()){profile.ShowSaveError(RefillLives);return;}
            RefreshLifeState();if(session.View.lives>0)session.View.message="";modal.Show(session.View);
        }
        void Handle(string action)
        {
            if(string.IsNullOrEmpty(action))return;
            if(gameplay||levelAdOpen||(loading&&loading.IsVisible))return;
            if(session!=null&&session.View.livesOnly&&action!="close"&&action!="refill")return;
            if(action=="close")
            {if(session.Close()){modal.Hide();home.SetPresentation(true,true);ReleaseLoadingArt();}return;}
            if(action.StartsWith("toggle:",StringComparison.Ordinal))
            {int index;if(int.TryParse(action.Substring(7),out index))session.Toggle(index);modal.Show(session.View);return;}
            if(action=="refill"){RefillLives();return;}
            if(action=="play")
            {
                session.RefreshLives(home.State.lives);
                PreLevelTicket ticket;
                if(session.TryBegin(out ticket)){
                    var ads=HeartOfTheRain.App.Advertising.InterstitialAds129.Instance;int completed=CompletedLevels();
                    if(ads&&ads.Due(ticket.level,completed)){levelAdOpen=true;modal.Show(session.View);StartCoroutine(BeginAfterLevelAd(ads,ticket,completed));}
                    else BeginLoading(ticket,false);
                }
                else modal.Show(session.View);
            }
        }
        IEnumerator BeginAfterLevelAd(HeartOfTheRain.App.Advertising.InterstitialAds129 ads,PreLevelTicket ticket,int completed){
            yield return ads.ShowForLevel(ticket.level,completed,3);
            levelAdOpen=false;BeginLoading(ticket,false);
        }
        void BeginLoading(PreLevelTicket ticket,bool keepTip){
            attemptId=Guid.NewGuid().ToString("N");toolSpend.BeginAttempt(attemptId);cupWinTimeCaptured=false;cupWinTime=null;
            launchTicket=ticket;int generation=++launchGeneration;
            // Both power kinds are available in current M46 matching rules, without a level unlock gate.
            bool hints=PlayerPrefs.GetInt("HeartOfTheRain.Settings.v1.hints",1)!=0;
            loading.Begin(hints,true,true,keepTip);modal.Hide();
            StartCoroutine(ReserveAfterFrame(ticket,generation));
        }
        IEnumerator ReserveAfterFrame(PreLevelTicket ticket,int generation){
            // Let the opaque overlay reach a rendered frame before any profile IO or board work.
            yield return null;if(!CurrentLaunch(ticket,generation))yield break;ReserveAndLaunch(ticket,generation);
        }
        bool CurrentLaunch(PreLevelTicket ticket,int generation)=>generation==launchGeneration&&ReferenceEquals(launchTicket,ticket);
        void ReserveAndLaunch(PreLevelTicket ticket,int generation){
            if(!CurrentLaunch(ticket,generation))return;
            if(gameplay){FailLaunch(ticket,generation);return;}
            if(Server){ServerReserve(ticket,generation);return;}
            try{profile.Service.Reserve(attemptId,ticket.level,ProfileJson.Hash(assets.gameplay.boards.levels[ticket.level-1].text),ticket.chosen.Select(v=>v?1:0).ToArray(),assets.rewardCoins,assets.rewardStars);}
            catch(InvalidOperationException ex) when(ProfileService.IsReservationRule(ex.Message)){
                profile.Refresh();session.RefreshLives(home.State.lives);session.Fail(ticket,ex.Message);launchTicket=null;loading.Hide();modal.Show(session.View);return;
            }
            catch(Exception){
                bool saved=false;
                try{saved=profile.Service.Read().attempts.Any(a=>a.id==attemptId&&a.state=="Reserved");}
                catch(Exception){profile.ShowSaveError(()=>ReserveAndLaunch(ticket,generation));return;}
                if(!saved){FailLaunch(ticket,generation);return;}
            }
            StartCoroutine(Launch(ticket,generation));
        }
        IEnumerator Launch(PreLevelTicket ticket,int generation)
        {
            if(!CurrentLaunch(ticket,generation))yield break;
            var go=new GameObject("Level "+ticket.level);gameplay=go.AddComponent<GameplayScreen>();
            gameplay.uiAssets=assets.gameplay;gameplay.initialLevel=ticket.level;gameplay.initialSeed=Server?(uint)Server.Attempt.seed:ProfileService.AttemptSeed(attemptId);gameplay.showLevelIntro=false;gameplay.SharedToolInventory=tools;failureSettled=false;
            gameplay.pendingStartingPowers=(int[])ticket.powerKinds.Clone();gameplay.ReviewInputBlocked=true;gameplay.SettingsBlocked=()=>launchTicket!=null||serverToolPending;gameplay.RecoverFirstPresentationFault=Server;
            if(Server)gameplay.RestoredLevelConfiguration=RetainedLevel(ticket.level,Server.Attempt.configHash);
            var source=gameplay;gameplay.ModelTurnAccepted+=turn=>CommitWonModel(source);
            gameplay.CommitToolSpend=CommitTool;ObserveServerActions(source);
            // Time spent in the background does not count against the preparation budget.
            launchDeadline=Time.realtimeSinceStartup+15;
            while(CurrentLaunch(ticket,generation)&&gameplay&&!gameplay.InitializationComplete&&Time.realtimeSinceStartup<launchDeadline)yield return null;
            if(!CurrentLaunch(ticket,generation))yield break;
            // Readiness includes all resources and the one-shot model grant, not hidden creation playback.
            if(!gameplay||!gameplay.InitializationComplete||!gameplay.HasStartedWithPowers||!string.IsNullOrEmpty(gameplay.StartingPowerError))
            {FailLaunch(ticket,generation);yield break;}
            // Introductions use the ready board and existing HUD, while the attempt
            // is still only Reserved. Closing the app here cannot charge a started loss.
            var introductions=ObstacleIntroductionRules.Plan(gameplay.Model.Level,home.State.completedLevelsInChapter,session.View.retry,false);
            // Read optional history only for a newcomer card, never on ordinary launches.
            // A history read fault may repeat a card; CommitStart still guards the financial start.
            if(introductions.Length>0&&!Server){try{
                if(profile.Service.Read().attempts.Any(a=>a.id!=attemptId&&a.level==ticket.level&&a.state!="Reserved"&&a.state!="Cancelled"))introductions=new ObstacleIntroductionCard[0];
            }catch(Exception){}}
            if(introductions.Length>0){
                modal.Hide();home.SetPresentation(false,false);loading.Hide();ReleaseLoadingArt();
                var hud=gameplay.GetComponent<GameplayHUD>();
                foreach(var card in introductions){
                    bool dismissed=false;hud.ShowObstacleIntroduction(card,()=>dismissed=true,gameplay.ObstacleIntroductionSprite(card.ArtKey));
                    while(CurrentLaunch(ticket,generation)&&gameplay&&!dismissed)yield return null;
                    if(!CurrentLaunch(ticket,generation)||!gameplay)yield break;
                }
                gameplay.SetPause(false);
            }
            CompleteLaunch(ticket,generation);
        }
        void FailLaunch(PreLevelTicket ticket,int generation){
            if(!CurrentLaunch(ticket,generation))return;
            if(gameplay){gameplay.gameObject.SetActive(false);Destroy(gameplay.gameObject);gameplay=null;}
            if(Server){ServerFailLaunch(ticket,generation);return;}
            // Recovery controls remain unavailable until durable cleanup is confirmed.
            try{if(profile.Service.Read().attempts.Any(a=>a.id==attemptId))profile.Service.CancelReservation(attemptId);if(!profile.Refresh())throw new InvalidOperationException("Save unavailable");}
            catch(Exception){
                bool cancelled=false;try{cancelled=!profile.Service.Read().attempts.Any(a=>a.id==attemptId&&a.state!="Cancelled")&&profile.Refresh();}catch(Exception){}
                if(!cancelled){profile.ShowSaveError(()=>FailLaunch(ticket,generation));return;}
            }
            session.Fail(ticket,"Could not start. Please try again.");EnsureLoadingArt();loading.ShowFailure();
        }
        void RetryLoading(){
            if(!loading.IsFailure||launchTicket==null)return;PreLevelTicket ticket;
            if(!profile.Refresh()){profile.ShowSaveError(RetryLoading);return;}
            session.RefreshLives(home.State.lives);session.RefreshStock(profile.Service.Read().starting);
            if(session.TryBegin(out ticket))BeginLoading(ticket,true);else BackFromLoading();
        }
        void BackFromLoading(){
            if(!loading.IsFailure)return;launchGeneration++;launchTicket=null;loading.Hide();home.SetPresentation(true,false);modal.Show(session.View);
        }
        void CompleteLaunch(PreLevelTicket ticket,int generation){
            if(!CurrentLaunch(ticket,generation)||finishingLaunch||!gameplay)return;
            if(Server&&!serverStartConfirmed){ServerStart(ticket,generation);return;}
            finishingLaunch=true;
            try{if(!Server)profile.Service.CommitStart(attemptId);}
            // A rule rejection at commit (lives or stock gone meanwhile) is a failed start, not a lost write to retry forever.
            catch(InvalidOperationException ex) when(ex.Message=="Cannot start this attempt"){finishingLaunch=false;FailLaunch(ticket,generation);return;}
            catch(Exception){
                bool saved=false;try{saved=profile.Service.Read().attempts.Any(a=>a.id==attemptId&&a.state=="Started");}catch(Exception){}
                if(!saved){finishingLaunch=false;profile.ShowSaveError(()=>CompleteLaunch(ticket,generation));return;}
            }
            if(!session.Complete(ticket)){finishingLaunch=false;Debug.LogError("Pre-level session rejected a committed start; releasing attempt "+attemptId,this);ReleaseStartedLaunch(ticket,generation);return;}
            var launched=gameplay;
            if(settingsAssets)gameplay.gameObject.AddComponent<GameplaySettingsController>().Configure(gameplay,settingsAssets,home,decision=>ConfirmExit(launched,decision),endLevelAssets);
            if(completion.Arm(++completionSerial,ticket.level)){
                var hud=gameplay.GetComponent<GameplayHUD>();hud.ResultRequested=(won,number)=>won?TryShowCompletion(launched,true,number):TrySettleFailure(launched,number);hud.ExternalResultVisible=()=>completion.IsOpen;
                // The connected flow settles every end state; the HUD's standalone
                // in-place reload must stay unreachable here.
                hud.RetryPressed=null;
            }
            ConfigureContinuation(launched);
            // Immediate handoff: no dwell, progress simulation or exit fade. Creation begins on the visible board.
            modal.Hide();home.SetPresentation(false,false);loading.Hide();ReleaseLoadingArt();launchTicket=null;gameplay.ReviewInputBlocked=false;
            finishingLaunch=false;profile.Refresh();
        }
        // Unreachable through the ticket guards today; if the session ever rejects a committed start,
        // release the attempt (items refunded, no life) instead of leaving a live board under the overlay.
        void ReleaseStartedLaunch(PreLevelTicket ticket,int generation){
            if(!CurrentLaunch(ticket,generation))return;
            if(Server){finishingLaunch=false;profile.ShowSaveError(()=>Server.Quit((ok,why)=>{if(ok)FailLaunch(ticket,generation);}));return;}
            if(gameplay){gameplay.gameObject.SetActive(false);Destroy(gameplay.gameObject);gameplay=null;}
            try{profile.Service.ReleaseFault(attemptId);if(!profile.Refresh())throw new InvalidOperationException("Save unavailable");}
            catch(Exception){profile.ShowSaveError(()=>ReleaseStartedLaunch(ticket,generation));return;}
            session.Fail(ticket,"Could not start. Please try again.");loading.ShowFailure();
        }
        void SyncTools(){if(!profile||!profile.Ready)return;var stock=profile.Service.Read().tools;tools.hammer=stock[0];tools.axe=stock[1];tools.ram=stock[2];tools.atlas=stock[3];}
        bool CommitTool(BoosterKind kind,int x,int y){
            if(Server)return ServerCommitTool(kind,x,y);
            bool unconfirmed;
            if(toolSpend.TryCommit(profile.Service,kind,x,y,out unconfirmed))return true;
            if(!unconfirmed)return false;
            // Reconcile the exact command/target before accepting other
            // input. The rejected plan restored the board and RNG.
            var source=gameplay;source.ReviewInputBlocked=true;source.SetPause(true);
            profile.ShowSaveError(()=>{if(!source||source!=gameplay)return;source.SetPause(false);source.ReviewInputBlocked=false;source.UseBooster(kind,x,y);});return false;
        }
        void CommitWonModel(GameplayScreen source){
            if(!source||source!=gameplay||source.Model.Status!="Won")return;
            if(Server){VerifyServerBoard(source);return;}
            try{profile.Service.Win(attemptId,CupWinTimestamp());}
            catch(Exception){source.ReviewInputBlocked=true;source.SetPause(true);profile.ShowSaveError(()=>{
                try{profile.Service.Win(attemptId,CupWinTimestamp());source.SetPause(false);source.ReviewInputBlocked=false;}catch(Exception){CommitWonModel(source);}
            });}
        }
        long? CupWinTimestamp(){if(!cupWinTimeCaptured){cupWinTime=profile.Cup?.CaptureWinTime();cupWinTimeCaptured=true;}return cupWinTime;}
        bool TrySettleFailure(GameplayScreen source,int number)
        {
            if(!source||source!=gameplay||number!=source.CurrentLevel||source.Busy)return false;
            // Every end state the model can reach settles here: out of moves and
            // a failed reshuffle are losses; the resolution guard is a fault.
            string status=source.Model.Status;if(status=="Playing"||status=="Won")return false;
            if(status=="Out of moves"&&source.Model.Moves==0){var continuation=source.GetComponent<HeartOfTheRain.App.NoMoves.NoMovesController>();if(continuation){continuation.Open();return true;}}
            if(failureSettled)return true;
            if(Server&&(status=="Resolution limit"||status=="Engine fault")){VerifyServerBoard(source,()=>{if(source&&source==gameplay)profile.ShowSaveError(()=>SettleLoss(source,number));});return true;}
            if(Server&&(Server.LastOperation==null||Server.LastOperation.model?.checkpointSHA256!=ProfileJson.Hash(JsonUtility.ToJson(source.Model.Checkpoint())))){VerifyServerBoard(source,()=>TrySettleFailure(source,number));return true;}
            if(status=="Resolution limit"||status=="Engine fault"){ReleaseFaultedAttempt(source,number);return true;}
            // Loss beat (owner decision, 22 October 2026): the approved HUD dialog
            // shows while the cue plays; the life is charged on acknowledgement.
            failureSettled=true;source.ReviewInputBlocked=true;
            source.GetComponent<GameplayHUD>().ShowLoss(GameplayHUD.LossTitleFor(status),()=>SettleLoss(source,number));
            return true;
        }
        void SettleLoss(GameplayScreen source,int number)
        {
            if(!source||source!=gameplay)return;
            var loss=new EndLevelSession();EndLevelDecision decision;
            if(!loss.Open(number,home.State.lives)||!loss.Confirm(home.State.lives,out decision))return;
            ConfirmExit(source,decision);
        }
        // The 128-wave / 512-step guard is an engine fault, not a player outcome:
        // record the board for diagnosis, release the attempt without a life
        // charge and reopen the pre-level so the player can try again.
        void ReleaseFaultedAttempt(GameplayScreen source,int number)
        {
            if(!source||source!=gameplay)return;
            if(!failureSettled){failureSettled=true;source.ReviewInputBlocked=true;string cause=source.Model.Status=="Engine fault"?"Engine fault ("+source.Model.FaultDetail+")":"Resolution guard reached";Debug.LogError(cause+" on level "+number+" seed "+source.CurrentSeed+" turn "+source.Model.Turn+"; attempt "+attemptId+" released without charge.",this);}
            try{profile.Service.ReleaseFault(attemptId);if(!profile.Refresh())throw new InvalidOperationException("Save unavailable");}
            catch(Exception){profile.ShowSaveError(()=>ReleaseFaultedAttempt(source,number));return;}
            gameplay.gameObject.SetActive(false);Destroy(gameplay.gameObject);gameplay=null;
            modal.Hide();OpenPreview(number,true);
        }
        bool TryShowCompletion(GameplayScreen source,bool won,int number)
        {
            if(!won||!source||source!=gameplay||!source.Ready||number!=source.CurrentLevel)return false;
            if(completion.IsOpen)return true;
            if(source.Model.Status!="Won"||source.Busy)return false;
            AttemptRecord receipt;
            if(Server){receipt=Server.CompletionReceipt();if(receipt==null||receipt.state!="Won"){ServerVerifyWin(source,number);return true;}}
            else try{receipt=profile.Service.Read().attempts.First(a=>a.id==attemptId);if(receipt.state!="Won")receipt=profile.Service.Win(attemptId,CupWinTimestamp());}
            catch(Exception){source.SetPause(true);profile.ShowSaveError(()=>{source.SetPause(false);TryShowCompletion(source,true,number);});return true;}
            if(!completion.PresentReceipt(number,receipt,Math.Min(50,assets.gameplay.boards.levels.Length)))return false;
            profile.Refresh();
            source.ReviewInputBlocked=true;source.SetPause(true);source.GetComponent<GameplayHUD>().Close(false);
            var journey=home.GetComponent<JourneyPage>();if(journey)journey.UseHomeProgress();
            if(CelebrationMotion.ShouldPlayFinale(number,completion.View.firstClear,completion.View.completedAfter)&&ChapterCelebrationPlayer.TryPlay(home,completion.View.chapter,()=>FinishCompletion("home")))return true;
            if(!VictoryCelebrationPlayer.TryPlay(home,number,()=>FinishCompletion("home")))FinishCompletion("home");
            return true;
        }
        void FinishCompletion(string action)
        {
            if(action!="continue"&&action!="home")return;if(!completion.IsOpen)return;var result=completion.View;if(!completion.Close())return;
            if(gameplay){gameplay.gameObject.SetActive(false);Destroy(gameplay.gameObject);gameplay=null;}modal.Hide();home.ApplyState(home.State);home.SetPresentation(true,true);
            home.PlayRewardReveal(result.coins,result.stars,result.completedBefore);
        }
        void ConfirmExit(GameplayScreen source,EndLevelDecision decision)
        {
            if(!source||source!=gameplay||decision==null||decision.Level!=gameplay.CurrentLevel)return;
            if(Server){ServerConfirmExit(source,decision);return;}
            try{
                var current=profile.Service.Read().attempts.First(a=>a.id==attemptId);
                // Already won while the exit was confirmed: withdraw the exit so the
                // level runs on to its completion with input and music restored.
                if(current.state=="Won"){var controller=source.GetComponent<GameplaySettingsController>();if(controller)controller.CancelExit();source.SetPause(false);return;}
                profile.Service.Lose(attemptId);if(!profile.Refresh())throw new InvalidOperationException("Save unavailable");
            }catch(Exception){profile.ShowSaveError(()=>ConfirmExit(source,decision));return;}
            gameplay.gameObject.SetActive(false);Destroy(gameplay.gameObject);gameplay=null;
            modal.Hide();OpenPreview(decision.Level,true);
        }
        // Review-only shortcut: bypasses life loss. Player exit uses the M58 confirmation.
        public void ReturnHomeForReview()
        {
            if(session==null||session.View.busy)return;
            if(profile&&!profile.IsTransient)return;
            if(gameplay&&profile&&profile.Ready){profile.Service.Change(p=>{var active=p.attempts.FirstOrDefault(a=>a.id==attemptId&&a.state=="Started");if(active!=null)active.state="Cancelled";return true;});profile.Refresh();}
            var victory=home.GetComponent<VictoryCelebrationPlayer>();if(victory&&victory.IsVisible)victory.Cancel();
            var cinematic=home.GetComponent<ChapterCelebrationPlayer>();if(cinematic&&cinematic.IsVisible)cinematic.Cancel();
            if(gameplay){gameplay.gameObject.SetActive(false);Destroy(gameplay.gameObject);gameplay=null;}
            if(completion.IsOpen)completion.Close();if(loading)loading.Hide();launchGeneration++;launchTicket=null;modal.Hide();home.SetPresentation(true,true);
        }
        void OnDestroy(){launchGeneration++;launchTicket=null;if(loading)Destroy(loading);if(home){var v=home.GetComponent<VictoryCelebrationPlayer>();if(v&&v.IsVisible)v.Cancel();var c=home.GetComponent<ChapterCelebrationPlayer>();if(c&&c.IsVisible)c.Cancel();home.PreLevelRequested.RemoveListener(Open);home.NavigationRequested.RemoveListener(OpenLives);}if(gameplay)Destroy(gameplay.gameObject);}
    }
}

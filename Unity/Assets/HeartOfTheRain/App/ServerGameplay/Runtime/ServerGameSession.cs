using System;
using System.Collections;
using System.Diagnostics;
using System.IO;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.RuStore;

namespace HeartOfTheRain.App.ServerGameplay {
    public sealed class ServerAuthorizedContext {
        public readonly string Origin,PlayerId;public readonly long Generation;public readonly bool AllowDevelopmentLoopback,ExpectedProduction;
        readonly Func<string> access;public string CurrentAccess=>access();
        internal ServerAuthorizedContext(string origin,string player,long generation,bool loopback,Func<string> access):this(origin,player,generation,loopback,access,false){}
        internal ServerAuthorizedContext(string origin,string player,long generation,bool loopback,Func<string> access,bool expectedProduction){ExpectedProduction=expectedProduction;Origin=origin;PlayerId=player;Generation=generation;AllowDevelopmentLoopback=loopback;this.access=access;}
    }
    // Selected only by an explicit external review configuration. The normal
    // local factory and its files are never imported, replaced or modified.
    public sealed partial class ServerGameSession:MonoBehaviour {
        ServerGameplayConfiguration config;ManagedIdentitySession82 identity;IdentityHttpTransport82 identityTransport;
        RuStoreBackendClient walletClient,readClient;ServerGameplayBrokerClient broker;ServerAttemptJournal journal;ServerAttemptDocument document;
        RuStoreServerWallet wallet;readonly ServerProfileProjection projection=new ServerProfileProjection();
        long clockAnchor,observedUtc,generation,playerOwnershipEpoch;bool busy,closed,journalDirty,bootstrapping;string error;
        const float GateWaitSeconds=20,StallSeconds=45;
#if UNITY_EDITOR
        EditorEphemeralIdentity82 editorVault;
#endif
        public bool Ready=>!closed&&!accountBlocked&&wallet!=null&&wallet.initialized&&journal!=null&&document!=null&&broker!=null;
        public bool Busy=>busy;
        public string LastError=>error;
        public string PlayerId=>identity?.ActivePlayerId??identity?.KnownPlayerId;
        public string Origin=>config?.origin;
        public bool ProductionEnabled=>config!=null&&config.productionEnabled;
        public bool SocialEnabled=>Ready&&config.socialEnabled;
        public long SessionGeneration=>generation;
        // Presentation ownership survives credential renewal. Account changes
        // and disposal invalidate it, even when recovery returns to one player.
        public long PlayerOwnershipEpoch=>playerOwnershipEpoch;
        public bool OwnsPlayer(long epoch,string origin,string player)=>Ready&&IdentityProtocol82.Id(player)&&playerOwnershipEpoch==epoch&&Origin==origin&&PlayerId==player;
        public long ServerTimeNow=>observedUtc<=0?0:observedUtc+(long)Math.Max(0,(Stopwatch.GetTimestamp()-clockAnchor)/(double)Stopwatch.Frequency);
        public RuStoreServerWallet Wallet=>wallet==null?null:Copy(wallet);
        public string WalletDisplaySignature=>wallet==null?null:wallet.revision+"|"+wallet.coins+"|"+wallet.stars+"|"+wallet.lives+"|"+wallet.maxLives+"|"+wallet.nextLifeAt+"|"+wallet.completed+"|"+wallet.currentLevel;
        public RuStoreServerAttempt Attempt=>document!=null&&document.hasAttempt?Copy(document.attempt):null;
        public ServerBrokerOperation LastOperation=>document!=null&&document.hasLastOperation?Copy(document.lastOperation):null;
        public bool HasPending=>document!=null&&document.hasPending;
        public bool HasRestorableContinue=>document!=null&&wallet?.activeAttempt?.attemptId==document.attemptId&&(document.phase=="Awaiting"||document.phase=="Purchased")&&!string.IsNullOrEmpty(document.checkpoint);
        public string ContinueCheckpoint=>HasRestorableContinue?document.checkpoint:null;
        public string ContinueView=>document?.view??"offer";
        public ServerProfileProjection Projection=>projection;
        public event Action Changed,IdentityChanged;
        static T Copy<T>(T value){
            if(value==null)return default(T);var result=JsonUtility.FromJson<T>(JsonUtility.ToJson(value));
            if(value is RuStoreServerWallet sourceWallet&&result is RuStoreServerWallet targetWallet&&sourceWallet.activeAttempt==null)targetWallet.activeAttempt=null;
            if(value is ServerBrokerOperation sourceOperation&&result is ServerBrokerOperation targetOperation){
                if(sourceOperation.model==null)targetOperation.model=null;if(sourceOperation.wallet==null)targetOperation.wallet=null;
                else if(sourceOperation.wallet.activeAttempt==null)targetOperation.wallet.activeAttempt=null;
                if(sourceOperation.attempt==null)targetOperation.attempt=null;if(sourceOperation.displayReceipt==null)targetOperation.displayReceipt=null;
            }
            return result;
        }
        static string NewId()=>Guid.NewGuid().ToString("N");
        static void Deliver(Action<bool,string> done,bool ok,string why){try{done?.Invoke(ok,why);}catch(Exception){}}
        public static ServerGameSession Select(HomePage home){
            ServerGameplayConfiguration configuration;string why;if(!ServerGameplayConfiguration.TryRead(out configuration,out why))return null;
            var session=home.gameObject.AddComponent<ServerGameSession>();session.config=configuration;session.error=why;
            if(configuration!=null)session.StartCoroutine(session.Bootstrap());return session;
        }
        IEnumerator Bootstrap(){
            if(bootstrapping)yield break;
            bootstrapping=true;
            try{yield return BootstrapCore();}
            finally{bootstrapping=false;}
        }
        IEnumerator BootstrapCore(){
            busy=true;
            try{InitializeAccountIdentity();}catch(Exception){error="ServerIdentityUnavailable";busy=false;Changed?.Invoke();yield break;}
            if(accountBlocked){busy=false;error="AccountSessionClosed";Changed?.Invoke();yield break;}
            bool identified=false;string why=null;yield return EnsureIdentity((ok,message)=>{identified=ok;why=message;});
            if(!identified){error=why;busy=false;Changed?.Invoke();yield break;}
            bool fresh=false;yield return FetchWallet((ok,message)=>{fresh=ok;why=message;});
            if(!fresh){error=why;busy=false;Changed?.Invoke();yield break;}
            try{
                BindRecoveredAttemptDecision();
                string directory=Path.Combine(Application.persistentDataPath,"ServerReview",IdentityProtocol82.Sha(config.origin).Substring(0,16),PlayerId);
                journal=new ServerAttemptJournal(Path.Combine(directory,"attempt.json"),config.origin,PlayerId);document=journal.Read();
                broker=new ServerGameplayBrokerClient(config.origin,PlayerId,()=>identity?.AccessToken,r=>StartCoroutine(r),config.allowDevelopmentLoopback,config.productionEnabled);
                if(wallet.activeAttempt!=null&&(!document.hasAttempt||document.attemptId!=wallet.activeAttempt.attemptId)){
                    // A Reserve whose reply was lost binds its attempt from the server's cached answer below.
                    if(document.hasPending&&document.pending.operation!="Reserve")throw new InvalidOperationException("UnresolvedOtherAttempt");
                    if(!document.hasPending)BindActiveAttempt();
                }
                // A Start that never reached the server must not charge a life for a board never shown.
                if(document.hasPending&&document.pending.operation=="Start"&&wallet.activeAttempt?.state=="Reserved"&&wallet.activeAttempt.attemptId==document.pending.attemptId){document.hasPending=false;Save();}
                Publish(wallet);
            }catch(Exception){error="ServerJournalUnavailable";busy=false;Changed?.Invoke();yield break;}
            if(document.hasPending)yield return ResumePending((ok,message)=>{fresh=ok;why=message;});
            busy=false;error=fresh?null:why;Changed?.Invoke();
            // Existing Continue/Shop checkpoints remain resumable. Other
            // interrupted attempts follow the approved one-loss rule.
            if(fresh&&!accountRecoveryBootstrap&&!HoldRecoveredAttemptDecision&&!HasRestorableContinue&&wallet.activeAttempt!=null){
                if(wallet.activeAttempt.state=="Reserved")CancelReservation((ok,message)=>{});
                else Quit((ok,message)=>{});
            }
        }
        void BindActiveAttempt(){
            document.phase="";document.checkpoint="";document.delta.Clear();document.hasLastOperation=false;document.acceptedActions=document.prefixRevision=0;
            BindAttempt(wallet.activeAttempt);Save();
        }
        long pausedUtcTicks,pausedStamp;
        // Stopwatch can stop in deep sleep. Move token age and server time on by the gap
        // the device clock saw, so a long lock renews instead of sending an expired token.
        void OnApplicationPause(bool paused){
            if(paused){pausedUtcTicks=DateTime.UtcNow.Ticks;pausedStamp=Stopwatch.GetTimestamp();return;}
            if(pausedUtcTicks==0)return;
            double slept=(DateTime.UtcNow.Ticks-pausedUtcTicks)/(double)TimeSpan.TicksPerSecond-(Stopwatch.GetTimestamp()-pausedStamp)/(double)Stopwatch.Frequency;pausedUtcTicks=0;
            if(slept>1){identity?.AdjustForSleep(slept);clockAnchor-=(long)(slept*Stopwatch.Frequency);}
        }
        IEnumerator EnsureIdentity(Action<bool,string> done){
            if(accountBlocked){done(false,"AccountSessionClosed");yield break;}
            if(identity==null){done(false,"ManagedIdentityUnavailable");yield break;}
            if(identity.HasAccess&&!identity.RenewalDue){done(true,null);yield break;}
            // Renewing keeps the same player and owner, so pages keep their views.
            // Only a first sign-in or another pending identity action starts a new one.
            var view=identity.View;bool renewal=view.hasSession&&(!view.hasPending||view.pendingPurpose=="session");
            IdentityReply82<IdentityView82> reply=null;long before=renewal?generation:++generation;if(!renewal)IdentityChanged?.Invoke();
            if(view.hasPending)identity.Resume(r=>reply=r);else if(view.hasSession)identity.Refresh(NewId(),r=>reply=r);else identity.CreateGuest(NewId(),r=>reply=r);
            // A coroutine can miss its transport timeout across an app suspend. The intent
            // stays in the journal, so give up the wait and let the next action resume it.
            float limit=Time.unscaledTime+StallSeconds;while(reply==null&&!closed&&before==generation&&Time.unscaledTime<limit)yield return null;
            if(reply==null&&!closed&&before==generation)identity.Cancel();
            if(closed||before!=generation){done(false,"ServerSessionChanged");yield break;}
            if(CloseRefusedIdentity(reply?.error)){done(false,"AccountSessionClosed");yield break;}done(reply!=null&&reply.Succeeded,reply?.error??"ManagedIdentityUnavailable");
        }
        IEnumerator FetchWallet(Action<bool,string> done){
            bool identified=false;string why=null;yield return EnsureIdentity((ok,message)=>{identified=ok;why=message;});if(!identified){done(false,why);yield break;}
            walletClient?.Dispose();walletClient=NewWalletClient();
            PayReply<RuStoreServerWallet> reply=null;walletClient.GetWallet(r=>reply=r);float limit=Time.unscaledTime+GateWaitSeconds;while(reply==null&&!closed&&Time.unscaledTime<limit)yield return null;
            if(closed){done(false,"ServerSessionClosed");yield break;}
            // The token's local age can be wrong after a sleep: renew once and read again.
            if(reply?.error?.code=="StagingHttp401"){
                identity.ExpireAccess();yield return EnsureIdentity((ok,message)=>{identified=ok;why=message;});if(!identified){done(false,why);yield break;}
                walletClient?.Dispose();walletClient=NewWalletClient();reply=null;walletClient.GetWallet(r=>reply=r);limit=Time.unscaledTime+GateWaitSeconds;while(reply==null&&!closed&&Time.unscaledTime<limit)yield return null;
                if(closed){done(false,"ServerSessionClosed");yield break;}
            }
            if(reply==null||!reply.Succeeded||!reply.value.initialized){done(false,reply?.error?.code??"ServerWalletUnavailable");yield break;}
            Publish(reply.value);done(true,null);
        }
        RuStoreBackendClient NewWalletClient()=>new RuStoreBackendClient(config.origin,identity.AccessToken,PlayerId,true,config.allowDevelopmentLoopback,r=>StartCoroutine(r),config.productionEnabled,config.productionEnabled?long.Parse(config.consoleAppId,System.Globalization.CultureInfo.InvariantCulture):0);
        void Publish(RuStoreServerWallet value){
            if(value==null||value.playerId!=PlayerId)return;
            bool historical=wallet!=null&&(value.revision<wallet.revision||value.revision==wallet.revision&&(value.serverUtc<observedUtc||wallet.refundReviewRequired&&!value.refundReviewRequired));
            if(!historical){wallet=Copy(value);observedUtc=value.serverUtc;clockAnchor=Stopwatch.GetTimestamp();}
            projection.Apply(wallet,DisplayAttempt());Changed?.Invoke();
        }
        void BindAttempt(RuStoreServerAttempt value){
            document.attemptId=value.attemptId;document.level=value.level;document.configHash=value.configHash;document.seed=value.seed;document.initialMoves=value.moves;
            document.selected=(int[])value.starting.Clone();document.hasAttempt=true;document.attempt=Copy(value);
        }
        AttemptRecord DisplayAttempt(){
            if(document==null||!document.hasAttempt)return null;var a=document.attempt;
            var result=new AttemptRecord{id=a.attemptId,level=a.level,config=a.configHash,seed=a.seed,selected=(int[])a.starting.Clone(),state=a.state=="AwaitingContinuation"?"Started":a.state,coins=50,stars=1,livesAfter=wallet?.lives??0};
            if(HasRestorableContinue){result.continuation.phase=document.phase;result.continuation.checkpoint=document.checkpoint;result.continuation.view=document.view;}
            var receipt=document.hasLastOperation?document.lastOperation.displayReceipt:null;
            if(receipt!=null&&receipt.outcome=="Won"){result.state="Won";result.firstClear=receipt.firstClear;result.awardedCoins=receipt.awardedCoins;result.awardedStars=receipt.awardedStars;result.completedBefore=receipt.completedBefore;result.completedAfter=receipt.completedAfter;result.livesAfter=receipt.livesAfter;}
            return result;
        }
        public AttemptRecord CompletionReceipt()=>DisplayAttempt();
        void Save(){
            var candidate=document;
            try{document=journal.Save(candidate);journalDirty=false;}
            catch{
                // Keep unsaved accepted move deltas on a pre-commit failure.
                // A post-commit lost acknowledgement must instead adopt the
                // new durable revision, so retry cannot conflict forever.
                journalDirty=true;
                try{var durable=journal.Read();if(durable.revision>candidate.revision){document=durable;journalDirty=false;}}catch(Exception){}
                throw;
            }
        }
        public void RetryInitialize(){if(!closed&&!accountBlocked&&!busy&&!bootstrapping&&config!=null&&!Ready)StartCoroutine(Bootstrap());}
        public void WithAuthenticatedSession(Action<ServerAuthorizedContext,string> done){
            if(done==null)throw new ArgumentNullException(nameof(done));if(!Ready){done(null,"ServerSessionUnavailable");return;}
            StartCoroutine(AuthorizeExternal(done));
        }
        IEnumerator AuthorizeExternal(Action<ServerAuthorizedContext,string> done){
            if(busy){float deadline=Time.unscaledTime+GateWaitSeconds;while(busy&&!closed&&Time.unscaledTime<deadline)yield return null;if(closed||busy||!Ready){done(null,"ServerSessionUnavailable");yield break;}}
            busy=true;bool fresh=false;string why=null;yield return FetchWallet((ok,message)=>{fresh=ok;why=message;});busy=false;
            if(!fresh||closed){done(null,why??"ServerSessionClosed");yield break;}
            long ownerGeneration=generation;string player=PlayerId;
            done(new ServerAuthorizedContext(config.origin,player,ownerGeneration,config.allowDevelopmentLoopback,()=>!closed&&generation==ownerGeneration&&PlayerId==player&&identity.HasAccess?identity.AccessToken:null,config.productionEnabled),null);
        }
        public void Refresh(Action<bool,string> done=null){if(closed||busy){Deliver(done,false,"ServerBusy");return;}if(!Ready){RetryInitialize();Deliver(done,false,"ServerInitializationPending");return;}if(identity.HasAccess&&!identity.RenewalDue){StartCoroutine(ReadWalletRoutine(done));return;}busy=true;StartCoroutine(RefreshRoutine(done));}
        // A wallet read commits nothing, so it neither holds nor waits for the
        // transaction gate. Publish already discards a reply older than the wallet.
        IEnumerator ReadWalletRoutine(Action<bool,string> done){
            long owner=playerOwnershipEpoch;float deadline=Time.unscaledTime+GateWaitSeconds;readClient?.Dispose();readClient=NewWalletClient();
            PayReply<RuStoreServerWallet> reply=null;readClient.GetWallet(r=>reply=r);while(reply==null&&!closed&&owner==playerOwnershipEpoch&&Time.unscaledTime<deadline)yield return null;
            if(closed||owner!=playerOwnershipEpoch){Deliver(done,false,"ServerSessionChanged");yield break;}
            if(reply==null||!reply.Succeeded||!reply.value.initialized){if(reply?.error?.code=="StagingHttp401")identity.ExpireAccess();error=reply?.error?.code??"ServerWalletUnavailable";Deliver(done,false,error);yield break;}
            error=null;Publish(reply.value);Deliver(done,true,null);
        }
        // A short wallet read or authorization holds the gate only briefly: wait
        // for it instead of failing the player's action.
        IEnumerator AfterGate(Action proceed,Action<bool,string> done){
            float deadline=Time.unscaledTime+GateWaitSeconds;while(busy&&!closed&&Time.unscaledTime<deadline)yield return null;
            if(closed||busy){Deliver(done,false,"ServerSessionUnavailable");yield break;}proceed();
        }
        IEnumerator RefreshRoutine(Action<bool,string> done){bool ok=false;string why=null;yield return FetchWallet((value,message)=>{ok=value;why=message;});busy=false;error=why;Deliver(done,ok,why);}
        public SocialBackendClient82 CreateSocialClient(Action<IEnumerator> dispatch,IProtectedSessionStore82 protectedOutbox=null){if(!SocialEnabled||!identity.HasAccess)throw new InvalidOperationException("SocialSessionUnavailable");return new SocialBackendClient82(config.origin,()=>identity.HasAccess?new SocialAccess82(PlayerId,identity.AccessToken):null,dispatch,protectedOutbox,true,config.allowDevelopmentLoopback,()=>identity.HasAccess&&identity.View.playerId==identity.ActivePlayerId);}
        public IProtectedSessionStore82 CreateProtectedSocialStore(){
            if(!Ready)throw new InvalidOperationException("ServerSessionUnavailable");string scope="review-social-"+IdentityProtocol82.Sha(config.origin+"|"+PlayerId).Substring(0,32);IProtectedSessionStore82 store;
#if UNITY_ANDROID && !UNITY_EDITOR
            store=new AndroidDeviceIdentity82(scope);
#elif UNITY_EDITOR
            store=editorVault.CreateStore(Path.GetFullPath("../.verification-cache/Launch82/ServerReview/"+scope+".sealed"));
#else
            throw new NotSupportedException();
#endif
            return new OriginBoundIdentityStore82(store,config.origin+"|social|"+PlayerId);
        }
        void OnDestroy(){DisposeAccountState();closed=true;playerOwnershipEpoch++;generation++;IdentityChanged?.Invoke();broker?.Dispose();walletClient?.Dispose();readClient?.Dispose();identity?.Dispose();identityTransport?.Dispose();
#if UNITY_EDITOR
            editorVault?.Dispose();
#endif
        }
    }
}

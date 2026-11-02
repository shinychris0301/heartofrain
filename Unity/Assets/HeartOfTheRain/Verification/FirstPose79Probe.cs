#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using UnityEngine;
using UnityEngine.SceneManagement;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.M48;
namespace HeartOfTheRain.Verification {
    // Opt-in memory-profile boards. Runtime PlayerSwap is dispatched from a real
    // Update or a resumed coroutine; neither is a claim of OS touch latency.
    public sealed class FirstPose79Probe:MonoBehaviour {
        public const string Request="HOTR_RunFirstPose79";
        const int FrameCapacity=16384;
        static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        [Serializable] public struct Phase {
            public string kind;public int frame;public long ticks;public float duration,clock;public double wall;
        }
        [Serializable] public struct Frame {
            public int row,frame,gc0,gc1,gc2;public long ticks;public double wall;public float intervalMs,clock,age;
            public string kind;public bool pending,busy,canAct,canBuffer;
            public GameplayScreen.FrameCost cost;
        }
        [Serializable] public sealed class Row {
            public string name,fixture,dispatch,startupTraceJson,metadataTraceJson,turnHash,finalHash,checkpointHash,dictionaryOrderHash,queueHash,resourceHash,holdPoseHash,holdPoseAfterHash;
            public int level,commandFrame,commandReturnedFrame,metadataReadyFrame,queueInspectionFrame,frameStart,frameCount,queuedSteps,actionCallbacks,modelCallbacks,settlementCallbacks,pendingSamples,holdSamples,releaseFrame;
            public bool checkpoint78,holdWorker,initialPending,headReferenceRetained,holdGateValid,settledBeforeRelease;
            public long commandStartedTicks,modelAcceptedTicks,commandFinishedTicks,metadataReadyTicks,settledTicks,queueInspectionStartedTicks,queueInspectionFinishedTicks,holdReleasedTicks,gateEnteredTicks,gateExitedTicks;
            public double commandStartedWall,modelAcceptedWall,commandFinishedWall,metadataReadyWall,settledWall,commandMs,preAcceptMs,presentationAcceptMs,metadataWaitMs,queueInspectionMs,settleSeconds;
            public float scheduledSeconds,headDuration;
            public GameplayScreen.CommandCost initialEnqueueCost,completedEnqueueCost;
            public List<Phase> phases=new List<Phase>(32);
        }
        [Serializable] public sealed class Report {
            public string status="RUNNING",utc,platform,graphics;
            public int schema=1,sourceCheckpoint=79,targetFps=60,bufferCapacity=FrameCapacity,droppedFrames;
            public long stopwatchFrequency;public bool isolatedProfile,launchCleared;
            public string scope="Same-APK synchronous78/current79 startup on isolated memory-profile boards. Runtime PlayerSwap is called in Update or an after-Update coroutine. Input command spans end immediately on return; metadata waits, signatures and serialization are outside those spans. A real own-camera witness is distinct from CPU submission and physical display. Two deliberately blocked worker rows test head-end hold, not production performance. Native lifecycle tests separately cover reload/cancellation/fault/service recovery. Elapsed work includes scheduling and this observer; no physical-device, OS-touch, universal speedup or hitch-free claim.";
            public List<Row> rows=new List<Row>();public Frame[] frames;public List<string> errors=new List<string>();
        }
        Report report;GameplayUIAssets assets;GameplayScreen game;M46AtlasBank bank;BoardPresentation presentation;
        Action<int,int,int,int> swap;Func<bool> canBuffer;Action dispatchAction;
        Canvas[] hidden;bool[] shown;Frame[] frames;int used;Row row;TurnResult accepted;
        BoardStep initialHead;ManualResetEventSlim workerGate;double deadline;string memoryPlayerId;bool finished;
        static bool bootPending;
        static double Now=>Time.realtimeSinceStartupAsDouble;
        static long Ticks=>Stopwatch.GetTimestamp();
        static double Ms(long ticks)=>ticks*1000.0/Stopwatch.Frequency;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)] static void Boot(){
            SceneManager.sceneLoaded-=Attach;bootPending=false;string path=Path.Combine(Application.persistentDataPath,Request);
            if(!File.Exists(path))return;File.Delete(path);bootPending=true;SceneManager.sceneLoaded+=Attach;
        }
        static void Attach(Scene scene,LoadSceneMode mode){
            if(!bootPending)return;var first=FindFirstObjectByType<FirstStartPage>();if(!first)return;bootPending=false;SceneManager.sceneLoaded-=Attach;first.reviewAlways=true;
            var host=first.home.GetComponent<PlayerProfileHost>();if(!host)host=first.home.gameObject.AddComponent<PlayerProfileHost>();var profile=PlayerProfile.New(new[]{5,5,3,2});
            host.VerificationRepository=new MemoryProfileRepository(profile);host.VerificationAuthorityFactory=_=>new UnavailableGiftAuthority();host.VerificationLivesClock=()=>1000;
            var node=new GameObject("Opt-in first playback pose79 controls");DontDestroyOnLoad(node);node.AddComponent<FirstPose79Probe>().memoryPlayerId=profile.playerId;
        }
        void Start(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),platform=Application.platform.ToString(),graphics=SystemInfo.graphicsDeviceName,stopwatchFrequency=Stopwatch.Frequency};
            frames=new Frame[FrameCapacity];deadline=Now+600;Application.targetFrameRate=report.targetFps;Application.logMessageReceived+=Log;StartCoroutine(Run());
        }
        void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)Fail(message+"\n"+stack);}
        void Update(){
            if(finished)return;if(Now>deadline){Fail("FirstPose79 timeout");return;}
            var action=dispatchAction;if(action==null)return;dispatchAction=null;try{action();}catch(Exception ex){Fail(ex.ToString());}
        }
        void LateUpdate(){
            if(row==null||!game||game.LastFrameCost.frame!=Time.frameCount)return;
            if(used==frames.Length){report.droppedFrames++;Fail("FirstPose79 frame capacity exceeded");return;}
            bool pending=game.VerificationStartupPending;if(pending)row.pendingSamples++;
            frames[used++]=new Frame{row=report.rows.Count-1,frame=Time.frameCount,ticks=Ticks,wall=Now,intervalMs=Time.unscaledDeltaTime*1000,
                clock=game.VerificationPlaybackClock,age=game.VerificationPlaybackAge,kind=game.VerificationPlaybackKind,pending=pending,busy=game.Busy,canAct=game.CanAct,canBuffer=canBuffer(),
                gc0=GC.CollectionCount(0),gc1=GC.MaxGeneration>=1?GC.CollectionCount(1):-1,gc2=GC.MaxGeneration>=2?GC.CollectionCount(2):-1,cost=game.LastFrameCost};
        }
        T Get<T>(string field)=>(T)typeof(GameplayScreen).GetField(field,Private).GetValue(game);
        void Check(bool ok,string text){if(!ok)throw new InvalidOperationException(text);}
        IEnumerator Ready(){while(!game.CanAct)yield return null;yield return null;bank=Get<M46AtlasBank>("bank");presentation=Get<BoardPresentation>("presentation");}
        void Step(BoardStep step){if(row==null)return;row.phases.Add(new Phase{kind=step.kind,frame=Time.frameCount,ticks=Ticks,wall=Now,duration=step.duration,clock=game.VerificationPlaybackClock});}
        void ModelAccepted(TurnResult turn){if(row==null)return;accepted=turn;row.modelCallbacks++;row.modelAcceptedTicks=Ticks;row.modelAcceptedWall=Now;}
        void ActionCompleted(PlayerActionRecord action){if(row!=null)row.actionCallbacks++;}
        void Settled(string status){if(row==null)return;row.settlementCallbacks++;if(row.holdWorker&&row.holdReleasedTicks==0)row.settledBeforeRelease=true;row.settledTicks=Ticks;row.settledWall=Now;}
        static string JsonHash(object value)=>Snapshot79Proof.JsonHash(value);
        static string ResourceHash(CommandResourcePreparation.Plan plan,int count){
            var text=new System.Text.StringBuilder("all:").Append(string.Join("\n",plan.All));
            for(int i=0;i<count;i++)text.Append("\nphase:").Append(string.Join("\n",plan.Phase(i)));
            return Snapshot79Proof.Hash(text.ToString());
        }
        BoardStep[] CompleteQueue(){
            // Retained metadata remains available even if a short queue settles
            // before this coroutine resumes. Sharing immutable step references
            // also lets this check the exact already-published head object.
            return game.VerificationStartupQueue;
        }
        void CallSwap(Cell[] move){
            row.commandFrame=Time.frameCount;row.commandStartedWall=Now;row.commandStartedTicks=Ticks;
            swap(move[0].x,move[0].y,move[1].x,move[1].y);
            row.commandFinishedTicks=Ticks;row.commandFinishedWall=Now;row.commandReturnedFrame=Time.frameCount;
            row.commandMs=Ms(row.commandFinishedTicks-row.commandStartedTicks);row.preAcceptMs=Ms(row.modelAcceptedTicks-row.commandStartedTicks);row.presentationAcceptMs=Ms(row.commandFinishedTicks-row.modelAcceptedTicks);
            row.initialPending=game.VerificationStartupPending;row.initialEnqueueCost=game.LastCommandCost;initialHead=Get<BoardStep>("current");
            Check(accepted!=null&&accepted.accepted&&row.actionCallbacks==1&&row.modelCallbacks==1,"Runtime PlayerSwap did not accept exactly once");
        }
        IEnumerator Run(){
            FirstStartPage first;while(!(first=FindFirstObjectByType<FirstStartPage>())||!first.Initialized)yield return null;
            while(FindFirstObjectByType<HeartOfTheRain.App.Launch.LaunchPage>())yield return null;report.launchCleared=true;
            var host=first.home.GetComponent<PlayerProfileHost>();report.isolatedProfile=host&&host.Ready&&host.VerificationRepository is MemoryProfileRepository&&host.Service.Read().playerId==memoryPlayerId;
            if(!report.isolatedProfile){Fail("FirstPose79 memory-profile isolation failed");yield break;}
            assets=first.assets.Gameplay;hidden=FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID);shown=hidden.Select(c=>c.enabled).ToArray();foreach(var canvas in hidden)canvas.enabled=false;
            game=new GameObject("Isolated first pose79 board").AddComponent<GameplayScreen>();game.uiAssets=assets;game.initialLevel=4;game.showLevelIntro=false;game.HintsEnabled=false;game.DeferTerminalPresentation=true;game.MeasureFrameCosts=true;game.MeasureDetailedDrawCosts=false;
            swap=(Action<int,int,int,int>)Delegate.CreateDelegate(typeof(Action<int,int,int,int>),game,typeof(GameplayScreen).GetMethod("PlayerSwap",Private));
            canBuffer=(Func<bool>)Delegate.CreateDelegate(typeof(Func<bool>),game,typeof(GameplayScreen).GetProperty("CanBuffer",Private).GetGetMethod(true));
            game.ModelTurnAccepted+=ModelAccepted;game.PlayerActionCompleted+=ActionCompleted;game.StepStarted+=Step;game.TurnSettled+=Settled;yield return Ready();game.GetComponent<GameplayHUD>().ResultRequested=(won,level)=>true;
            int pair=0;foreach(int level in new[]{4,14,31,33})foreach(string mode in new[]{"update","coroutine"}){
                bool controlFirst=pair++%2==0;yield return Case(level,mode,controlFirst,false);if(finished)yield break;yield return Case(level,mode,!controlFirst,false);if(finished)yield break;
            }
            foreach(string mode in new[]{"update","coroutine"}){yield return Case(4,mode,false,true);if(finished)yield break;}
            foreach(var value in report.rows)Check(value.settlementCallbacks==1&&value.queuedSteps==value.phases.Count,"One complete queue and settlement per command: "+value.name);
            foreach(var group in report.rows.Where(r=>!r.holdWorker).GroupBy(r=>r.fixture+"/"+r.dispatch)){
                Check(group.Count()==2&&group.Select(r=>r.checkpoint78).Distinct().Count()==2,"Complete paired startup branches");
                Check(group.Select(r=>r.turnHash+"/"+r.finalHash+"/"+r.checkpointHash+"/"+r.dictionaryOrderHash+"/"+r.queueHash+"/"+r.resourceHash).Distinct().Count()==1,"Same-platform model/fullqueue/resource parity: "+group.Key);
            }
            Finish(true);
        }
        IEnumerator Case(int level,string mode,bool control,bool hold){
            game.VerificationUseCheckpoint78Startup=control;game.Load(level-1);yield return Ready();var move=game.Model.LegalSwaps().First();
            accepted=null;initialHead=null;row=new Row{name="L"+level+"_"+mode+(hold?"_hold":control?"_control78":"_current79"),fixture="L"+level,level=level,dispatch=mode,checkpoint78=control,holdWorker=hold,frameStart=used};report.rows.Add(row);
            if(hold){workerGate=new ManualResetEventSlim(false);var gate=workerGate;var heldRow=row;game.VerificationStartupWorkHook=stage=>{
                if(stage!=PlaybackPreparationJob79.WorkStage.BeforeBuild)return;
                Interlocked.Exchange(ref heldRow.gateEnteredTicks,Ticks);
                try{if(!gate.Wait(TimeSpan.FromSeconds(10)))throw new TimeoutException("FirstPose79 controlled worker gate timed out");}
                finally{Interlocked.Exchange(ref heldRow.gateExitedTicks,Ticks);}
            };}
            else game.VerificationStartupWorkHook=null;
            if(mode=="update"){dispatchAction=()=>CallSwap(move);while(dispatchAction!=null&&!finished)yield return null;}
            else CallSwap(move);
            if(finished)yield break;
            if(hold){
                while((game.VerificationStartup.headEndedFrame<=0||Interlocked.Read(ref row.gateEnteredTicks)==0)&&!finished)yield return null;
                if(finished)yield break;
                for(int i=0;i<3;i++){
                    Check(game.VerificationStartupPending&&game.Busy&&!game.CanAct&&!canBuffer()&&row.settlementCallbacks==0,"Pending head-end gates stay closed");
                    string pose=JsonHash(new Draws{values=presentation.SampleLive(Get<BoardStep>("current"),Get<BoardSnapshot>("idle"),game.VerificationPlaybackClock,Get<float>("started"))});
                    if(i==0)row.holdPoseHash=pose;else Check(row.holdPoseHash==pose,"Head-end hold pose remains unchanged");row.holdPoseAfterHash=pose;row.holdSamples++;yield return null;
                }
                row.holdGateValid=true;row.releaseFrame=Time.frameCount;row.holdReleasedTicks=Ticks;workerGate.Set();
            }
            while(game.VerificationStartupPending&&!finished)yield return null;if(finished)yield break;
            row.metadataReadyTicks=Ticks;row.metadataReadyWall=Now;row.metadataWaitMs=Ms(row.metadataReadyTicks-row.commandFinishedTicks);row.metadataReadyFrame=Time.frameCount;row.completedEnqueueCost=game.LastCommandCost;
            // Capture immutable references now; hashing and independent path
            // resolution must wait until genuine idle, so they cannot create a
            // playback-frame stall under the label "outside Accept".
            var queue=CompleteQueue();var plan=game.VerificationStartupResources;var metadataTrace=game.VerificationStartup;
            Check(queue!=null&&queue.Length>1,"Retained complete queue metadata is available");row.queuedSteps=queue.Length;row.headReferenceRetained=ReferenceEquals(initialHead,queue[0]);row.headDuration=queue[0].duration;
            Check(row.headReferenceRetained&&queue[0].kind=="swap"&&Math.Abs(row.headDuration-.12f)<.000001f,"Published swap head identity and120ms duration are retained");
            while((game.Busy||game.VerificationTurnPreparationPending)&&!finished)yield return null;if(finished)yield break;yield return null;yield return null;
            row.frameCount=used-row.frameStart;row.queueInspectionFrame=Time.frameCount;row.queueInspectionStartedTicks=Ticks;row.metadataTraceJson=JsonUtility.ToJson(metadataTrace);
            row.scheduledSeconds=queue.Sum(s=>s.duration);row.queueHash=SmoothnessCommandProof.Signature(queue.ToList(),false);Check(plan!=null&&plan.Matches(queue),"Actual retained resource-plan ownership matches complete queue");row.resourceHash=ResourceHash(plan,queue.Length);var expectedPlan=new CommandResourcePreparation(assets.boards).Build(queue);Check(row.resourceHash==ResourceHash(expectedPlan,queue.Length),"Transferred actual resource paths match independent main-thread resolution");
            row.queueInspectionFinishedTicks=Ticks;row.queueInspectionMs=Ms(row.queueInspectionFinishedTicks-row.queueInspectionStartedTicks);
            row.startupTraceJson=JsonUtility.ToJson(game.VerificationStartup);row.turnHash=JsonHash(accepted);row.finalHash=JsonHash(game.Model.Snapshot());row.checkpointHash=JsonHash(game.Model.Checkpoint());row.dictionaryOrderHash=Snapshot79Proof.Hash(string.Join(";",game.Model.Pieces.Select(p=>p.Key+":"+p.Value.id)));
            row.settleSeconds=row.settledWall-row.commandStartedWall;game.Model.Validate();row=null;game.VerificationStartupWorkHook=null;
            if(workerGate!=null){workerGate.Set();workerGate.Dispose();workerGate=null;}
        }
        [Serializable] sealed class Draws {public List<DrawSprite> values;}
        void Fail(string text){if(finished)return;report.errors.Add(text);Finish(false);}
        void Finish(bool ok){
            if(finished)return;finished=true;dispatchAction=null;if(workerGate!=null)workerGate.Set();row=null;StopAllCoroutines();report.frames=new Frame[used];Array.Copy(frames,report.frames,used);
            report.status=ok&&report.errors.Count==0?"PASS_NATIVE_FIRST_POSE79":"FAIL_NATIVE_FIRST_POSE79";Application.logMessageReceived-=Log;
            if(game){game.VerificationStartupWorkHook=null;game.gameObject.SetActive(false);Destroy(game.gameObject);}if(hidden!=null)for(int i=0;i<hidden.Length;i++)if(hidden[i])hidden[i].enabled=shown[i];
            string folder=Path.Combine(Application.persistentDataPath,"FirstPose79");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"Report.json"),JsonUtility.ToJson(report,true));
        }
        void OnDestroy(){Application.logMessageReceived-=Log;if(workerGate!=null)workerGate.Set();}
    }
}
#endif

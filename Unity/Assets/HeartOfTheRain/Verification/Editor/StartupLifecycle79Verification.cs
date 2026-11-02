#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.M48;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class StartupLifecycle79Verification {
        const string Key="HOTR.StartupLifecycle79.Native";
        const string ControlledFault="Controlled startup79 lifecycle failure";
        static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static readonly string[] Cases={"pure_swap_hold_rapid_input","reload_discards_stale","disable_resume","pause_worker_install","fault_out_of_moves","fault_won"};
        [Serializable] public sealed class Row {
            public string name,rawHash,expectedQueueHash,installedQueueHash,expectedFinalHash,finalHash,expectedCheckpointHash,checkpointHash,settledStatus;
            public int playerRecords,modelAccepted,settled,authorizations,toolSpends,cameraEvents,expectedFaultLogs;public bool exactQueue,modelPreserved,staleDiscarded,resumed,paused;
            public GameplayScreen.StartupTrace79 trace;public List<string> captures=new List<string>();
        }
        [Serializable] public sealed class Report {
            public string status,utc,unity,scope="Native Editor Play Mode with actual GameplayScreen, model, worker and camera.Render/onPostRender. Worker-only controlled gates verify a rendered pure swap before build, tail holding/input exclusion, exact queue/final state, reload discard, disable/resume, pause and terminal faults. Won uses an explicit goal-free level fixture; no HomeLevelFlow, real profile, receipt, Android, performance or physical-device claim.";
            public int checks;public List<Row> rows=new List<Row>();public List<string> checksPassed=new List<string>();public List<string> errors=new List<string>();
        }
        sealed class WorkGate {
            public readonly ManualResetEventSlim release=new ManualResetEventSlim(false);
            public readonly bool fail;public int entered,thread;public long enteredTicks;
            public WorkGate(bool fail=false){this.fail=fail;}
            public void Hook(PlaybackPreparationJob79.WorkStage stage){
                if(stage!=PlaybackPreparationJob79.WorkStage.BeforeBuild)return;
                thread=Thread.CurrentThread.ManagedThreadId;enteredTicks=Stopwatch.GetTimestamp();Interlocked.Increment(ref entered);
                long began=Stopwatch.GetTimestamp();while(!release.Wait(10))if((Stopwatch.GetTimestamp()-began)/(double)Stopwatch.Frequency>15)throw new TimeoutException("Startup79 lifecycle gate was not released");
                if(fail)throw new InvalidOperationException(ControlledFault);
            }
        }
        static GameplayScreen game;static GameplayUIAssets assets;static Report report;static Row row;static WorkGate gate;
        static readonly List<WorkGate> allGates=new List<WorkGate>();
        static bool launched,finished,installedChecked;static int index,phase,mainThread,playerRecords,modelAccepted,settled,authorizations,toolSpends,cameraEvents,expectedFaultLogs;
        static double deadline,caseDeadline,at;static string output,settledStatus,modelAfterCommand,inventoryAfterCommand,reloadedHash;static float pauseClock,disabledClock,headStartedClock,originalTimeScale;
        static Cell[] move;static TurnResult acceptedTurn;static BoardStep[] expectedQueue;static BoardModel reloadedModel;static PlaybackPreparationJob79 oldJob;static long oldGeneration;
        static bool expectsFault;static LevelData fixture;static int cameraBefore;
        static StartupLifecycle79Verification(){if(SessionState.GetBool(Key,false))EditorApplication.update+=Tick;}
        public static void Run(){SessionState.SetBool(Key,true);EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorApplication.update-=Tick;EditorApplication.update+=Tick;EditorApplication.isPlaying=true;}
        static T Field<T>(string name)=>(T)typeof(GameplayScreen).GetField(name,Private).GetValue(game);
        static object Invoke(string name,params object[] values)=>typeof(GameplayScreen).GetMethod(name,Private).Invoke(game,values);
        static string JsonHash(object value)=>Snapshot79Proof.JsonHash(value);
        static string QueueHash(IEnumerable<BoardStep> queue)=>SmoothnessCommandProof.Signature(queue.ToList(),false);
        static void Check(bool value,string text){report.checks++;if(!value)throw new InvalidOperationException(Cases[index]+": "+text);report.checksPassed.Add(Cases[index]+": "+text);}
        static void Next(int value){phase=value;at=EditorApplication.timeSinceStartup;}
        static void Log(string text,string stack,LogType type){
            if(type!=LogType.Error&&type!=LogType.Exception&&type!=LogType.Assert)return;
            if(expectsFault&&type==LogType.Exception&&text.Contains(ControlledFault)){expectedFaultLogs++;return;}
            Finish(text+"\n"+stack);
        }
        static void CameraWitness(Camera camera){if(game&&camera==Field<Camera>("view"))cameraEvents++;}
        static LevelData Data(string name){
            var value=JsonUtility.FromJson<LevelData>(assets.boards.levels[3].text);
            if(name=="fault_out_of_moves")value.movesProposal=1;
            if(name=="fault_won"){value.obstacles=Array.Empty<ObstacleCell>();value.goals=Array.Empty<Goal>();}
            return value;
        }
        static void ResetCounters(){playerRecords=modelAccepted=settled=authorizations=toolSpends=cameraEvents=expectedFaultLogs=0;acceptedTurn=null;settledStatus=null;installedChecked=false;oldJob=null;}
        static void LoadCase(){
            ResetCounters();expectsFault=Cases[index].StartsWith("fault_",StringComparison.Ordinal);fixture=Data(Cases[index]);game.VerificationStartupWorkHook=null;game.VerificationLevelOverride=fixture;game.SharedToolInventory=new BoosterInventory();game.playbackSpeed=1;game.Load(3);Next(0);caseDeadline=EditorApplication.timeSinceStartup+90;
        }
        static void Launch(){
            launched=true;report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};output=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY79_OUTPUT");if(string.IsNullOrEmpty(output))output="../Verification/Evidence/Gameplay79";output=Path.GetFullPath(output);Directory.CreateDirectory(Path.Combine(output,"Native/StartupLifecycle79"));
            originalTimeScale=Time.timeScale;Time.timeScale=1;mainThread=Thread.CurrentThread.ManagedThreadId;deadline=EditorApplication.timeSinceStartup+420;caseDeadline=EditorApplication.timeSinceStartup+90;
            Application.logMessageReceived+=Log;Camera.onPostRender+=CameraWitness;assets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
            fixture=Data(Cases[0]);game=new GameObject("Native startup79 isolated lifecycle").AddComponent<GameplayScreen>();game.uiAssets=assets;game.initialLevel=4;game.VerificationLevelOverride=fixture;game.showLevelIntro=false;game.HintsEnabled=false;game.DeferTerminalPresentation=true;game.boardRecoil=false;
            game.BeforePlayerCommand=()=>{authorizations++;return true;};game.CommitToolSpend=(kind,x,y)=>{toolSpends++;return true;};game.PlayerActionCompleted+=record=>playerRecords++;game.ModelTurnAccepted+=turn=>{acceptedTurn=turn;modelAccepted++;};game.TurnSettled+=status=>{settled++;settledStatus=status;};
        }
        static void Begin(){
            row=new Row{name=Cases[index]};game.GetComponent<GameplayHUD>().ResultRequested=(won,level)=>true;var camera=Field<Camera>("view");camera.enabled=false;
            move=game.Model.LegalSwaps().First(m=>game.Model.At(m[0].x,m[0].y).family=="gem"&&game.Model.At(m[1].x,m[1].y).family=="gem");
            var control=BoardModel.FromCheckpoint(game.Model.Level,game.Model.Checkpoint());var expected=control.Swap(move[0].x,move[0].y,move[1].x,move[1].y);Check(expected.accepted,"Control match is accepted");
            expectedQueue=BoardPlayback.Build(expected.steps,control.Level).ToArray();row.rawHash=JsonHash(expected);row.expectedQueueHash=QueueHash(expectedQueue);row.expectedFinalHash=JsonHash(control.Snapshot());row.expectedCheckpointHash=JsonHash(control.Checkpoint());
            if(Cases[index]=="fault_out_of_moves")Check(control.Status=="Out of moves","Accepted last move reaches Out of moves before presentation fault");
            if(Cases[index]=="fault_won")Check(control.Status=="Won","Accepted goal-free fixture reaches Won before presentation fault");
            gate=new WorkGate(expectsFault);allGates.Add(gate);game.VerificationStartupWorkHook=gate.Hook;
            Invoke("PlayerSwap",move[0].x,move[0].y,move[1].x,move[1].y);game.SetPause(true);pauseClock=Field<float>("clock");
            Check(playerRecords==1&&modelAccepted==1&&authorizations==1&&acceptedTurn!=null&&JsonHash(acceptedTurn)==row.rawHash,"Actual player command accepted exactly once with expected raw turn");
            modelAfterCommand=JsonHash(game.Model.Checkpoint());inventoryAfterCommand=JsonUtility.ToJson(Field<BoosterInventory>("inventory"));
            var prefix=Field<BoardStep>("current");Check(game.VerificationStartupPending&&game.Busy&&!game.CanAct&&prefix!=null&&prefix.kind=="swap"&&Math.Abs(prefix.duration-.12f)<.00001f,"Only the pure120ms leading swap is published");
            headStartedClock=Field<float>("started");
            Check(Field<List<BoardStep>>("queue").Count==1&&!Field<PlaybackPreparationJob79>("startupJob79").Started&&Volatile.Read(ref gate.entered)==0,"Worker is not started by command acceptance");
            Invoke("Render");Check(game.VerificationStartup.headSubmittedFrame==Time.frameCount&&!Field<PlaybackPreparationJob79>("startupJob79").Started,"Submitting the pose alone cannot start managed work");
            WrongCamera();Check(!Field<PlaybackPreparationJob79>("startupJob79").Started&&Volatile.Read(ref gate.entered)==0,"An unrelated actual camera cannot witness the board");
            cameraBefore=cameraEvents;Capture("FirstPose");Check(cameraEvents==cameraBefore+1&&Field<PlaybackPreparationJob79>("startupJob79").Started,"Actual board camera onPostRender starts the worker");
            var trace=game.VerificationStartup;Check(trace.cameraWitnessFrame==Time.frameCount&&trace.headSubmittedTicks<=trace.cameraWitnessTicks&&trace.cameraWitnessTicks<=trace.jobStartedTicks,"Camera witness follows submitted head and precedes worker start");
            PoseAtSource(prefix);camera.enabled=true;Next(1);
        }
        static void WrongCamera(){var node=new GameObject("Unrelated startup79 camera");var camera=node.AddComponent<Camera>();camera.enabled=false;var target=new RenderTexture(32,32,16);try{camera.targetTexture=target;camera.Render();}finally{camera.targetTexture=null;UnityEngine.Object.Destroy(target);UnityEngine.Object.Destroy(node);}}
        static void Capture(string suffix){
            string name="Native/StartupLifecycle79/"+Cases[index]+"_"+suffix+".png";var camera=Field<Camera>("view");var previous=camera.targetTexture;var active=RenderTexture.active;var target=new RenderTexture(720,1280,24);Texture2D pixels=null;
            try{camera.targetTexture=target;camera.Render();RenderTexture.active=target;pixels=new Texture2D(720,1280,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,720,1280),0,0);pixels.Apply();File.WriteAllBytes(Path.Combine(output,name),pixels.EncodeToPNG());row.captures.Add(name);}
            finally{camera.targetTexture=previous;RenderTexture.active=active;if(pixels)UnityEngine.Object.Destroy(pixels);UnityEngine.Object.Destroy(target);}
        }
        static void PoseAtSource(BoardStep prefix){
            var draws=Field<BoardPresentation>("presentation").SampleLive(prefix,Field<BoardSnapshot>("idle"),Field<float>("clock"),Field<float>("started"));var motion=prefix.motion[0];var body=draws.First(d=>d.pieceId==motion.id);var point=(Vector3)Invoke("Position",body.x,body.y);var sprite=Field<M46AtlasBank>("bank").Get(body);
            Check(Math.Abs(body.x-motion.fromX)<.00001f&&Math.Abs(body.y-motion.fromY)<.00001f,"First sampled swap pose starts at the source cell");
            Check(Field<List<SpriteRenderer>>("pool").Any(sr=>sr.enabled&&sr.sprite==sprite&&(sr.transform.localPosition-point).sqrMagnitude<.000001f),"Actual visible SpriteRenderer matches the first sampled pose");
        }
        static void RapidInput(){
            for(int i=0;i<8;i++){Invoke("PlayerSwap",move[0].x,move[0].y,move[1].x,move[1].y);Invoke("PlayerTap",move[0].x,move[0].y);game.UseBooster(BoosterKind.Hammer,move[0].x,move[0].y);}
            Check(game.Busy&&!game.CanAct&&!game.VerificationCanBuffer&&!Field<BoardGestureBuffer>("pendingGesture").HasPending,"Pending startup rejects rapid swap/tap/booster input without buffering");
            Check(playerRecords==1&&modelAccepted==1&&authorizations==1&&toolSpends==0&&settled==0,"Rapid input triggers no additional authorization, action, tool spend or settlement");
            Check(JsonHash(game.Model.Checkpoint())==modelAfterCommand&&JsonUtility.ToJson(Field<BoosterInventory>("inventory"))==inventoryAfterCommand,"Blocked inputs preserve settled model and tool inventory");
        }
        static void Installed(){
            if(installedChecked)return;Check(!game.VerificationStartupPending&&game.VerificationStartupQueue.Length==expectedQueue.Length,"Worker result installs one complete tail");
            row.installedQueueHash=QueueHash(game.VerificationStartupQueue);row.exactQueue=row.installedQueueHash==row.expectedQueueHash;Check(row.exactQueue,"Installed full queue equals synchronous construction");
            var trace=game.VerificationStartup;Check(trace.workerThreadId!=0&&trace.workerThreadId!=trace.callerThreadId&&trace.callerThreadId==mainThread,"Compilation and dependency planning execute on another managed thread");
            Check(trace.workerStartedTicks>=trace.cameraWitnessTicks&&trace.tailInstalledTicks>=trace.workerFinishedTicks,"Worker/tail installation chronology preserves the camera witness");installedChecked=true;
        }
        static void Tick(){try{
            if(finished||!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;if(!launched){Launch();return;}
            if(EditorApplication.timeSinceStartup>deadline||EditorApplication.timeSinceStartup>caseDeadline)throw new TimeoutException("Startup79 phase "+phase+" case "+Cases[index]);double elapsed=EditorApplication.timeSinceStartup-at;
            switch(phase){
                case 0:if(!game.CanAct)return;Begin();break;
                case 1:
                    if(Volatile.Read(ref gate.entered)==0)return;Check(gate.thread!=mainThread&&gate.enteredTicks>=game.VerificationStartup.jobStartedTicks,"BeforeBuild gate runs on the worker after actual camera start");
                    if(Cases[index]=="pause_worker_install"){gate.release.Set();Next(6);}else{game.SetPause(false);Next(2);}break;
                case 2:
                    if(elapsed<.30)return;Check(game.VerificationStartupPending&&game.VerificationStartup.held&&Field<BoardStep>("current")==null&&settled==0,"Head ends while tail waits without an early TurnSettled");
                    Check(Field<float>("clock")>headStartedClock+(float)game.VerificationStartup.headDuration,"Effects keep moving while the held head waits for its tail");RapidInput();
                    if(Cases[index]=="reload_discards_stale"){
                        oldJob=Field<PlaybackPreparationJob79>("startupJob79");oldGeneration=oldJob.Generation;game.VerificationStartupWorkHook=null;game.Load(3);reloadedModel=game.Model;reloadedHash=JsonHash(game.Model.Checkpoint());gate.release.Set();Next(4);
                    }else if(Cases[index]=="disable_resume"){
                        oldJob=Field<PlaybackPreparationJob79>("startupJob79");oldGeneration=oldJob.Generation;disabledClock=Field<float>("clock");game.enabled=false;gate.release.Set();gate=new WorkGate();allGates.Add(gate);game.VerificationStartupWorkHook=gate.Hook;Next(5);
                    }else{gate.release.Set();Next(3);}break;
                case 3:
                    if(expectsFault){
                        if(game.VerificationStartupPending||settled==0)return;Check(game.VerificationStartup.workerFailed&&expectedFaultLogs==1&&settled==1,"Controlled worker exception settles once through the fault path");
                        if(Cases[index]=="fault_won"){Check(game.Model.Status=="Won"&&game.Model.FaultDetail==null&&JsonHash(game.Model.Checkpoint())==row.expectedCheckpointHash,"Post-model presentation failure preserves Won and its checkpoint");}
                        else{var restored=game.Model.Checkpoint();restored.board.status="Out of moves";Check(game.Model.Status=="Engine fault"&&game.Model.FaultDetail.Contains(ControlledFault)&&JsonHash(restored)==row.expectedCheckpointHash,"Post-model Out of moves becomes Engine fault without changing game state");}
                        Check(!game.Busy&&!game.CanAct&&!Field<BoardGestureBuffer>("pendingGesture").HasPending,"Fault clears pending presentation/input ownership");Next(8);break;
                    }
                    if(game.VerificationStartupPending)return;Installed();if(game.Busy)return;Check(settled==1&&JsonHash(game.Model.Snapshot())==row.expectedFinalHash&&JsonHash(game.Model.Checkpoint())==row.expectedCheckpointHash,"Released tail finishes the exact solved model once");Next(8);break;
                case 4:
                    if(!game.CanAct||!oldJob.IsCompleted||elapsed<.25)return;
                    Check(oldJob.Cancelled&&ReferenceEquals(game.Model,reloadedModel)&&JsonHash(game.Model.Checkpoint())==reloadedHash&&game.Model.Turn==0,"Reload discards stale worker success and keeps the replacement model");
                    Check(!game.VerificationStartupPending&&game.VerificationStartupQueue.Length==0&&Field<List<BoardStep>>("queue").Count==0&&settled==0,"Stale generation installs no queue and settles no replacement turn");row.staleDiscarded=true;Next(8);break;
                case 5:
                    if(elapsed<.20)return;Check(oldJob.Cancelled&&game.VerificationStartupPending&&game.Busy&&Math.Abs(Field<float>("clock")-disabledClock)<.00001f,"Disable cancels work but retains immutable pending request and clock");
                    game.enabled=true;Check(game.VerificationStartup.generation>oldGeneration&&!Field<PlaybackPreparationJob79>("startupJob79").Started,"Re-enable owns a new generation awaiting a fresh camera witness");
                    Invoke("Render");Capture("ResumedPose");row.resumed=true;Next(7);break;
                case 6:
                    if(game.VerificationStartupPending)return;Installed();Check(game.Paused&&game.Busy&&settled==0&&Math.Abs(Field<float>("clock")-pauseClock)<.00001f,"Worker may install while paused without consuming swap time or settlement");row.paused=true;Next(9);break;
                case 7:
                    if(Volatile.Read(ref gate.entered)==0)return;Check(game.VerificationStartup.resumed&&gate.thread!=mainThread&&settled==0,"Resumed request starts once after a new native camera event");RapidInput();gate.release.Set();Next(3);break;
                case 8:
                    if(elapsed<.15)return;Invoke("PollStartup79");Invoke("PollStartup79");Check(playerRecords==1&&modelAccepted==1&&authorizations==1&&toolSpends==0&&settled==(row.staleDiscarded?0:1),"Repeated polls cannot replay accepted actions, inventory charges or settlement");CompleteCase();break;
                case 9:
                    if(elapsed<.20)return;Check(game.Paused&&Math.Abs(Field<float>("clock")-pauseClock)<.00001f&&settled==0,"Pause remains stable after tail installation");game.SetPause(false);Next(3);break;
            }
        }catch(Exception error){Finish(error.ToString());}}
        static void CompleteCase(){
            row.playerRecords=playerRecords;row.modelAccepted=modelAccepted;row.settled=settled;row.settledStatus=settledStatus;row.authorizations=authorizations;row.toolSpends=toolSpends;row.cameraEvents=cameraEvents;row.expectedFaultLogs=expectedFaultLogs;row.finalHash=JsonHash(game.Model.Snapshot());row.checkpointHash=JsonHash(game.Model.Checkpoint());row.trace=game.VerificationStartup;row.modelPreserved=row.staleDiscarded||expectsFault||row.finalHash==row.expectedFinalHash;report.rows.Add(row);
            foreach(var item in allGates)item.release.Set();game.VerificationStartupWorkHook=null;expectsFault=false;index++;if(index==Cases.Length){Finish(null);return;}LoadCase();
        }
        static void Finish(string error){
            if(finished)return;finished=true;foreach(var item in allGates)item.release.Set();Application.logMessageReceived-=Log;Camera.onPostRender-=CameraWitness;EditorApplication.update-=Tick;SessionState.EraseBool(Key);
            if(report==null)report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};if(error!=null)report.errors.Add(error);report.status=report.errors.Count==0&&report.rows.Count==Cases.Length?"PASS_NATIVE_STARTUP_LIFECYCLE79":"FAIL_NATIVE_STARTUP_LIFECYCLE79";
            if(game){game.VerificationStartupWorkHook=null;game.gameObject.SetActive(false);UnityEngine.Object.Destroy(game.gameObject);}Time.timeScale=originalTimeScale;
            if(string.IsNullOrEmpty(output)){output=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY79_OUTPUT");if(string.IsNullOrEmpty(output))output="../Verification/Evidence/Gameplay79";output=Path.GetFullPath(output);}Directory.CreateDirectory(Path.Combine(output,"Native"));File.WriteAllText(Path.Combine(output,"Native/StartupLifecycle79.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.status.StartsWith("PASS",StringComparison.Ordinal)?0:1);
        }
    }
}
#endif

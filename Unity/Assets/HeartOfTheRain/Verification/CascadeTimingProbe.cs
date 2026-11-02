#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 // Opt-in isolated live renderer; no attempt, inventory or progression hooks.
 public sealed class CascadeTimingProbe:MonoBehaviour {
  public const string Request="HOTR_RunCascadeTiming";
  const int FrameLimit=16384,RowFrameLimit=2048;
  [Serializable] public class RequestData {public string variant="measure";public int repeats=1,visualLevel=4;public bool profileModelWork,checkpoint74Continuation;}
  [Serializable] public class Phase {public string kind,label;public int frame;public float clock,duration,lastContact;public double wall,absoluteWall;}
  [Serializable] public struct CommandSpan {public string kind;public int frame,gc0Before,gc0After,spritesBefore,spritesAfter,texturesBefore,texturesAfter,synchronousLoadsBefore,synchronousLoadsAfter;public double startedWall,finishedWall,milliseconds;}
  [Serializable] public struct FrameSample {
   public int row,frame,gc0,gc1,gc2,spriteCreates,spriteEvictions,cachedSprites,cachedTextures,synchronousLoads;
   public long textureBytes;public string stage,kind;public bool timingWindow,preparing,commandFrame,costPredatesCommand;
   public float intervalMs,clock,age;public double absoluteWall,lateIntervalMs,afterUpdateElapsedMs;
   // The cost tag belongs to Update/Render, before a coroutine can change the
   // live phase later that frame. Keep these two state samples separate.
   public GameplayScreen.FrameCost cost;
  }
  [Serializable] public class Row {
   public string name,baseCase,turnHash,finalHash,warmthScope,startupTraceJson;public int targetFps,matches,frames,lateFrames,repeatIndex,commandFrame,queuedSteps,recordedFrames,queueInspectionFrame;
   public bool deferredStartup;public double initialCommandFinishedWall,metadataReadyWall,queueInspectionStartedWall,queueInspectionFinishedWall;public GameplayScreen.CommandCost initialEnqueueCost;
   public double captureStartedWall,commandStartedWall,acceptStartedWall,acceptFinishedWall,commandFinishedWall,firstCommandRenderFinishedWall;
   public double legalSearchMs,fixtureSetupMs,modelMs,acceptMs,commandMs,queueInspectionMs,totalSynchronousProbeMs,firstDispatchFromAcceptMs,firstCommandRenderMs;
   public double wallSeconds,totalCommandToSettledSeconds;public float scheduledSeconds,maxIntervalMs;
   public GameplayScreen.CommandCost enqueueCost;
   public BoardModel.ModelWork modelWork;
   public List<Phase> phases=new List<Phase>(32);public List<CommandSpan> commandSpans=new List<CommandSpan>(4);
  }
  [Serializable] public class Report {
   public string status="RUNNING",utc,variant,platform,scope="Unaccelerated isolated native GameplayScreen. Legacy wallSeconds starts immediately before real Accept and excludes fixture search/model. Absolute spans and bounded pre-roll/playback/post frames identify omitted work. Intervals include emulator/OS waits; native Render completion is not displayed-pixel or touch latency. Not physical-device certification.";
   public string diagnosticOverhead="Detailed frame/stage/per-draw timers and counters add diagnostic overhead. Compare equally instrumented controls; these samples provide attribution rather than uninstrumented performance.";
   public int profilingSchemaVersion=2,sourceCheckpoint=79,repeats=1,frameLimit=FrameLimit,droppedFrameSamples,maxGcGeneration;
   public bool modelWorkEnabled,checkpoint74Continuation;public int visualLevel=4;
   public List<Row> rows=new List<Row>();public List<FrameSample> frameSamples=new List<FrameSample>(FrameLimit);public List<string> errors=new List<string>();
  }
  public GameplayUIAssets suppliedAssets;public string variant="measure";public int repeats=1,visualLevel=4;public bool profileModelWork,checkpoint74Continuation;public Action<Report> Completed;
  Report report;GameplayScreen game;M46AtlasBank bank;Row row;double began,deadline,lastLateWall;bool timed;string stage;
  int oldFps,oldSync;Canvas[] hidden;bool[] shown;
  static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
  static readonly FieldInfo QueueField=typeof(GameplayScreen).GetField("queue",Private),BankField=typeof(GameplayScreen).GetField("bank",Private);
  static readonly MethodInfo AcceptMethod=typeof(GameplayScreen).GetMethod("Accept",Private);
  static double Now=>Time.realtimeSinceStartupAsDouble;
  static string Hash(string s){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(Encoding.UTF8.GetBytes(s))).Replace("-","").ToLowerInvariant();}
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]static void Boot(){
   var p=Path.Combine(Application.persistentDataPath,Request);if(!File.Exists(p))return;string text=File.ReadAllText(p).Trim();File.Delete(p);
   var config=text.StartsWith("{",StringComparison.Ordinal)?JsonUtility.FromJson<RequestData>(text):new RequestData{variant=text};
   var node=new GameObject("Opt-in cascade timing review");DontDestroyOnLoad(node);var probe=node.AddComponent<CascadeTimingProbe>();probe.variant=config.variant;probe.repeats=config.repeats;probe.profileModelWork=config.profileModelWork;probe.visualLevel=config.visualLevel;probe.checkpoint74Continuation=config.checkpoint74Continuation;
  }
  void Start(){
   report=new Report{utc=DateTime.UtcNow.ToString("o"),platform=Application.platform.ToString(),variant=variant,repeats=repeats,maxGcGeneration=GC.MaxGeneration,modelWorkEnabled=profileModelWork,visualLevel=visualLevel,checkpoint74Continuation=checkpoint74Continuation};oldFps=Application.targetFrameRate;oldSync=QualitySettings.vSyncCount;
   deadline=Now+240+120*Math.Max(0,repeats-1);Application.logMessageReceived+=Log;
   if((variant!="measure"&&variant!="visual")||repeats<1||repeats>5||visualLevel<1||visualLevel>50||variant=="visual"&&repeats!=1){report.errors.Add("Unsupported variant/repeat request");Finish();return;}StartCoroutine(Run());
  }
  void Log(string text,string trace,LogType type){if(type==LogType.Exception||type==LogType.Error||type==LogType.Assert){report.errors.Add(text+"\n"+trace);Finish();}}
  void Update(){if((report.status=="RUNNING"||report.status=="READY_FOR_CAPTURE")&&Now>deadline){report.errors.Add("Playback timeout");Finish();}}
  void LateUpdate(){
   if(row==null||!game)return;double now=Now;var cost=game.LastFrameCost;
   if(timed){row.frames++;row.maxIntervalMs=Math.Max(row.maxIntervalMs,Time.unscaledDeltaTime*1000);if(Time.unscaledDeltaTime>.10f)row.lateFrames++;}
   if(row.firstCommandRenderFinishedWall==0&&row.phases.Count>0&&cost.frame==Time.frameCount&&cost.renderStartedWall>=row.phases[0].absoluteWall&&cost.kind!="idle"){
    row.firstCommandRenderFinishedWall=cost.renderFinishedWall;row.firstCommandRenderMs=(cost.renderFinishedWall-row.commandStartedWall)*1000;
   }
   if(report.frameSamples.Count<FrameLimit&&row.recordedFrames<RowFrameLimit){
    report.frameSamples.Add(new FrameSample{row=report.rows.Count,frame=Time.frameCount,stage=stage,timingWindow=timed,absoluteWall=now,lateIntervalMs=lastLateWall==0?0:(now-lastLateWall)*1000,
     intervalMs=Time.unscaledDeltaTime*1000,clock=game.VerificationPlaybackClock,age=game.VerificationPlaybackAge,kind=game.VerificationPlaybackKind,preparing=game.VerificationPreparing,
     commandFrame=row.commandStartedWall>0&&Time.frameCount==row.commandFrame,costPredatesCommand=row.commandStartedWall>0&&cost.updateFinishedWall<=row.commandStartedWall,
     afterUpdateElapsedMs=cost.frame==Time.frameCount?Math.Max(0,now-cost.updateFinishedWall)*1000:0,cost=cost,
     gc0=GC.CollectionCount(0),gc1=report.maxGcGeneration>=1?GC.CollectionCount(1):-1,gc2=report.maxGcGeneration>=2?GC.CollectionCount(2):-1,
     spriteCreates=bank.SpriteCreates,spriteEvictions=bank.SpriteEvictions,cachedSprites=bank.SpriteCount,cachedTextures=bank.TextureCount,textureBytes=bank.TextureBytes,synchronousLoads=bank.SynchronousLoads});row.recordedFrames++;
   }else report.droppedFrameSamples++;
   lastLateWall=now;
  }
  void Step(BoardStep s){if(row==null)return;double now=Now;if(row.phases.Count==0)row.firstDispatchFromAcceptMs=(now-row.acceptStartedWall)*1000;
   row.phases.Add(new Phase{kind=s.kind,label=s.label,frame=Time.frameCount,clock=game.VerificationPlaybackClock,wall=now-began,absoluteWall=now,duration=s.duration,lastContact=s.motion.Count==0?0:s.motion.Max(m=>m.delay+m.seconds)});
  }
  CommandSpan StartSpan(string kind)=>new CommandSpan{kind=kind,frame=Time.frameCount,startedWall=Now,gc0Before=GC.CollectionCount(0),spritesBefore=bank.SpriteCreates,texturesBefore=bank.TextureCount,synchronousLoadsBefore=bank.SynchronousLoads};
  double EndSpan(CommandSpan span){span.finishedWall=Now;span.milliseconds=(span.finishedWall-span.startedWall)*1000;span.gc0After=GC.CollectionCount(0);span.spritesAfter=bank.SpriteCreates;span.texturesAfter=bank.TextureCount;span.synchronousLoadsAfter=bank.SynchronousLoads;row.commandSpans.Add(span);return span.milliseconds;}
  IEnumerator Ready(){while(!game.CanAct)yield return null;yield return null;}
  IEnumerator Run(){
   var assets=suppliedAssets;
   if(!assets){FirstStartPage first;while(!(first=FindFirstObjectByType<FirstStartPage>())||!first.Initialized||FindFirstObjectByType<HeartOfTheRain.App.Launch.LaunchPage>())yield return null;assets=first.assets.Gameplay;hidden=FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID);shown=hidden.Select(c=>c.enabled).ToArray();foreach(var c in hidden)c.enabled=false;}
   game=new GameObject("Isolated cascade board").AddComponent<GameplayScreen>();game.uiAssets=assets;game.initialLevel=4;game.showLevelIntro=false;game.MeasureFrameCosts=true;game.StepStarted+=Step;yield return Ready();game.GetComponent<GameplayHUD>().ResultRequested=(win,level)=>true;
   var fixtures=variant=="visual"?new[]{new[]{visualLevel-1,0,30}}:new[]{new[]{3,0,60},new[]{3,0,30},new[]{3,0,15},new[]{0,21,30},new[]{25,8,30},new[]{47,16,30}};
   var priorHashes=new Dictionary<string,string>();
   for(int repeat=0;repeat<repeats;repeat++)foreach(var fixture in fixtures){
    QualitySettings.vSyncCount=0;Application.targetFrameRate=fixture[2];game.Load(fixture[0]);yield return Ready();bank=(M46AtlasBank)BankField.GetValue(game);
    string caseName="L"+(fixture[0]+1)+"_"+fixture[1]+"_"+fixture[2];row=new Row{name=caseName+(repeat==0?"":"_r"+repeat),baseCase=caseName,repeatIndex=repeat,targetFps=fixture[2],captureStartedWall=Now,warmthScope=repeat==0?"First fixture pass in this process; board preparation already completed":"Repeated process/code/driver paths; board reloaded with fresh bank, not a retained sprite-cache control"};stage="pre_roll";timed=false;lastLateWall=0;
    yield return new WaitForSecondsRealtime(.3f);
    if(variant=="visual"){
     stage="capture_wait";report.status="READY_FOR_CAPTURE";Save();string gate=Path.Combine(Application.persistentDataPath,"HOTR_CascadeTiming_Continue");while(!File.Exists(gate))yield return null;File.Delete(gate);report.status="RUNNING";
    }
    var model=game.Model;Cell[] move=null;Piece source=null,partner=null;
    double fixtureStarted=Now;stage=fixture[1]==0?"legal_search":"fixture_setup";var setup=StartSpan(stage);
    if(fixture[1]==0)move=model.LegalSwaps().First();
    else{source=model.Pieces.Values.First(v=>v.family=="gem");model.InjectReviewPower(source.x,source.y,fixture[1]==8?7:fixture[1]);if(fixture[1]==8){partner=model.Pieces.Values.First(v=>v.family=="gem"&&Math.Abs(v.x-source.x)+Math.Abs(v.y-source.y)==1);model.InjectReviewPower(partner.x,partner.y,4);}}
    double setupMs=EndSpan(setup);if(fixture[1]==0)row.legalSearchMs=setupMs;else row.fixtureSetupMs=setupMs;
    model.VerificationResetWork();model.VerificationMeasureWork=profileModelWork;
    stage="model";row.commandFrame=Time.frameCount;row.commandStartedWall=Now;var solve=StartSpan("model");
    var turn=move!=null?model.Swap(move[0].x,move[0].y,move[1].x,move[1].y):partner!=null?model.Swap(source.x,source.y,partner.x,partner.y):model.Tap(source.x,source.y);row.modelMs=EndSpan(solve);
    model.VerificationMeasureWork=false;if(profileModelWork)row.modelWork=model.VerificationGetWork();
    if(!turn.accepted){report.errors.Add("Fixture rejected");Finish();yield break;}
    stage="accept";row.acceptStartedWall=began=Now;timed=true;var accept=StartSpan("real_accept");
    bool previousControl=LocalCascadeContinuation.VerificationUseCheckpoint74;
    try{LocalCascadeContinuation.VerificationUseCheckpoint74=checkpoint74Continuation;AcceptMethod.Invoke(game,new object[]{turn});}finally{LocalCascadeContinuation.VerificationUseCheckpoint74=previousControl;}
    row.acceptMs=EndSpan(accept);row.acceptFinishedWall=Now;row.initialCommandFinishedWall=row.commandFinishedWall=row.acceptFinishedWall;row.commandMs=(row.acceptFinishedWall-row.commandStartedWall)*1000;row.initialEnqueueCost=game.LastCommandCost;row.deferredStartup=game.VerificationStartupPending;
    // The first published swap may precede its compiled tail. This wait is
    // part of observed playback, never part of synchronous Accept latency.
    stage="playback";while(game.VerificationStartupPending)yield return null;
    row.metadataReadyWall=Now;row.queueInspectionFrame=Time.frameCount;row.enqueueCost=game.LastCommandCost;
    stage="queue_inspection";row.queueInspectionStartedWall=Now;var inspect=StartSpan("accepted_queue_inspection");
    // Inspect the actual completed queue once. A second diagnostic Build
    // would contaminate the command and duplicate background work.
    var queue=game.VerificationStartupQueue;row.queuedSteps=queue.Length;foreach(var step in queue)row.scheduledSeconds+=step.duration;row.queueInspectionMs=EndSpan(inspect);
    if(row.queuedSteps==0){report.errors.Add("Accepted queue was empty");Finish();yield break;}
    row.queueInspectionFinishedWall=Now;row.totalSynchronousProbeMs=setupMs+row.modelMs+row.acceptMs+row.queueInspectionMs;stage="playback";
    while(game.Busy)yield return null;
    row.startupTraceJson=JsonUtility.ToJson(game.VerificationStartup);
    row.wallSeconds=Now-began;row.totalCommandToSettledSeconds=Now-row.commandStartedWall;timed=false;stage="post_roll";
    yield return new WaitForSecondsRealtime(variant=="visual"?1f:.1f);
    var done=row;row=null;done.matches=turn.steps.Count(s=>s.kind=="match");done.turnHash=Hash(JsonUtility.ToJson(turn));done.finalHash=Hash(JsonUtility.ToJson(model.Snapshot()));model.Validate();
    string signature=done.turnHash+"/"+done.finalHash;if(priorHashes.TryGetValue(caseName,out var previous)&&previous!=signature){report.errors.Add("Repeated fixture changed model result: "+caseName);Finish();yield break;}priorHashes[caseName]=signature;report.rows.Add(done);
   }
   Finish();
  }
  void Save(){var folder=Path.Combine(Application.persistentDataPath,"CascadeTiming");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"Report.json"),JsonUtility.ToJson(report,true));}
  void Finish(){if(report.status.StartsWith("PASS")||report.status.StartsWith("FAIL"))return;row=null;timed=false;if(report.droppedFrameSamples>0)report.errors.Add("Frame sample limit exceeded: "+report.droppedFrameSamples);report.status=report.errors.Count==0?"PASS_CASCADE_PLAYBACK":"FAIL_CASCADE_PLAYBACK";Application.logMessageReceived-=Log;Application.targetFrameRate=oldFps;QualitySettings.vSyncCount=oldSync;if(game){game.gameObject.SetActive(false);Destroy(game.gameObject);}if(hidden!=null)for(int i=0;i<hidden.Length;i++)if(hidden[i])hidden[i].enabled=shown[i];Save();Completed?.Invoke(report);}
  void OnDestroy(){Application.logMessageReceived-=Log;}
 }
}
#endif

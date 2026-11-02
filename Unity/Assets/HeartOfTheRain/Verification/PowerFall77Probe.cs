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
using UnityEngine.SceneManagement;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Profile;
namespace HeartOfTheRain.Verification {
 // Explicit opt-in, memory-profile fixture. This observer never settles an
 // attempt, changes inventory, or writes the normal player repository.
 public sealed class PowerFall77Probe:MonoBehaviour {
  public const string Request="HOTR_RunPowerFall77";
  const float FrozenAge=2.5761447f;
  static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
  [Serializable] public struct Frame {
   public int row,frame,spriteCreates,spriteEvictions,synchronousLoads,cachedSprites,cachedTextures,preparationBatches,preparationFrames,preparationCreates;
   public float intervalMs;public double absoluteWall;public bool preparationPending;
   public GameplayScreen.FrameCost cost;public M46AtlasBank.PowerPreparationBatch preparation;
  }
  [Serializable] public sealed class NaturalRow {
   public string name,family,turnHash,finalHash;public int count,repeat,commandFrame,frameStart,frameCount;
   public bool skipTurnPreparation;public double preparationSeconds,commandStartedWall,commandFinishedWall,modelMs,acceptMs,commandMs,settleSeconds;
   public int spriteCreates,spriteEvictions,synchronousLoads,preparationBatches,preparationFrames,preparationCreates,preparationSkippedAtlases;
   public double maximumPreparationBatchMs;public GameplayScreen.CommandCost enqueueCost;
  }
  [Serializable] public struct FrozenPair {public int index;public bool controlFirst;public double controlStartedWall,controlFinishedWall,refinedStartedWall,refinedFinishedWall;public GameplayScreen.FrameCost controlCost,refinedCost;}
  [Serializable] public sealed class FrozenRow {
   public string name,family,turnHash,finalHash,queueHash,beforeControlDrawHash,beforeRefinedDrawHash,beforeControlMeshHash,beforeRefinedMeshHash,afterControlDrawHash,afterRefinedDrawHash,afterControlMeshHash,afterRefinedMeshHash;
   public int count,phaseIndex;public float age,clock,phaseDuration;public bool resourcesReady,preparationPending;public FrozenPair[] pairs=new FrozenPair[4];
  }
  [Serializable] public sealed class Report {
   public int profilingSchemaVersion=2,sourceCheckpoint=79;public bool usesCurrentDefaultStartup=true;public string status="RUNNING",utc,platform,graphics;
   public string scope="Isolated memory-profile Double Orb crate/stone fixtures. Natural pairs vary only turn preparation on fresh banks after two untimed code/driver warmups; AB/BA ordering, no cache flush. Frozen pairs vary only checkpoint76/current sampling at one identical same-bank pose; actual Update/Render, all resources ready. Outer spans are disjoint; legacy spans are nested. GC counters detect completed collections, not incremental-slice CPU. Coarse draw instrumentation; elapsed spans include observer/host scheduling. No I/O/hash/mesh readback during timed frames. No physical-device or hitch-free claim.";
   public bool detailedDrawCosts=false,isolatedProfile,launchCleared;public int bufferCapacity=16384;
   public List<NaturalRow> naturalRows=new List<NaturalRow>();public List<FrozenRow> frozenRows=new List<FrozenRow>();public Frame[] frames;public List<string> errors=new List<string>();
  }
  [Serializable] sealed class DrawState {public List<DrawSprite> draws;}
  [Serializable] sealed class MeshState {public string name;public int order;public Vector3[] vertices;public Vector2[] uv;public Color32[] colors;public int[] triangles;}
  [Serializable] sealed class MeshStates {public List<MeshState> meshes=new List<MeshState>();}
  public GameplayUIAssets suppliedAssets;public Action<Report> Completed;public Report Result {get;private set;}
  GameplayScreen game;M46AtlasBank bank;BoardPresentation presentation;Action<TurnResult> accept;Action updateGame;
  Frame[] buffered;int used,recordingRow=-1;double deadline;string reviewPlayerId;Canvas[] hidden;bool[] wasEnabled;
  static bool pending;
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)] static void Boot(){SceneManager.sceneLoaded-=Attach;pending=false;var path=Path.Combine(Application.persistentDataPath,Request);if(!File.Exists(path))return;File.Delete(path);pending=true;SceneManager.sceneLoaded+=Attach;}
  static void Attach(Scene scene,LoadSceneMode mode){if(!pending)return;var first=FindFirstObjectByType<FirstStartPage>();if(!first)return;pending=false;SceneManager.sceneLoaded-=Attach;first.reviewAlways=true;var host=first.home.GetComponent<PlayerProfileHost>();if(!host)host=first.home.gameObject.AddComponent<PlayerProfileHost>();var profile=PlayerProfile.New(new[]{5,5,3,2});host.VerificationRepository=new MemoryProfileRepository(profile);host.VerificationAuthorityFactory=_=>new UnavailableGiftAuthority();host.VerificationLivesClock=()=>1000;var node=new GameObject("Opt-in power fall77 review");DontDestroyOnLoad(node);node.AddComponent<PowerFall77Probe>().reviewPlayerId=profile.playerId;}
  void Start(){Result=new Report{utc=DateTime.UtcNow.ToString("o"),platform=Application.platform.ToString(),graphics=SystemInfo.graphicsDeviceName};buffered=new Frame[Result.bufferCapacity];deadline=Time.realtimeSinceStartupAsDouble+600;Application.logMessageReceived+=Log;StartCoroutine(Run());}
  void Log(string value,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)Fail(value+"\n"+stack);}
  void Update(){if(Result!=null&&Result.status=="RUNNING"&&Time.realtimeSinceStartupAsDouble>deadline)Fail("PowerFall77 timeout");}
  void LateUpdate(){if(recordingRow<0||!game||game.LastFrameCost.frame!=Time.frameCount)return;if(used==buffered.Length){Fail("PowerFall77 frame buffer overflow");return;}var cost=game.LastFrameCost;buffered[used++]=new Frame{row=recordingRow,frame=Time.frameCount,intervalMs=Time.unscaledDeltaTime*1000,absoluteWall=Time.realtimeSinceStartupAsDouble,cost=cost,spriteCreates=bank.SpriteCreates,spriteEvictions=bank.SpriteEvictions,synchronousLoads=bank.SynchronousLoads,cachedSprites=bank.SpriteCount,cachedTextures=bank.TextureCount,preparationPending=bank.PowerPreparationPending,preparation=bank.LastPowerPreparationBatch,preparationBatches=bank.PowerPreparationBatches,preparationFrames=bank.PowerPreparationFrames,preparationCreates=bank.PowerPreparationCreates};}
  void Fail(string error){if(Result==null||Result.status!="RUNNING")return;Result.errors.Add(error);Finish(false);}
  IEnumerator Ready(){while(!game.CanAct)yield return null;yield return null;bank=Get<M46AtlasBank>("bank");presentation=Get<BoardPresentation>("presentation");}
  T Get<T>(string field)=>(T)typeof(GameplayScreen).GetField(field,Private).GetValue(game);
  void Set(string field,object value)=>typeof(GameplayScreen).GetField(field,Private).SetValue(game,value);
  static string Hash(string value){using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(value))).Replace("-","").ToLowerInvariant();}
  IEnumerator Run(){
   var assets=suppliedAssets;
   if(!assets){FirstStartPage first;while(!(first=FindFirstObjectByType<FirstStartPage>())||!first.Initialized)yield return null;while(FindFirstObjectByType<HeartOfTheRain.App.Launch.LaunchPage>())yield return null;Result.launchCleared=true;var host=first.home.GetComponent<PlayerProfileHost>();Result.isolatedProfile=host&&host.Ready&&host.VerificationRepository is MemoryProfileRepository&&host.Service.Read().playerId==reviewPlayerId;if(!Result.isolatedProfile){Fail("PowerFall77 memory-profile isolation failed");yield break;}assets=first.assets.Gameplay;hidden=FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID);wasEnabled=hidden.Select(c=>c.enabled).ToArray();foreach(var c in hidden)c.enabled=false;}
   game=new GameObject("Isolated power fall77 board").AddComponent<GameplayScreen>();game.uiAssets=assets;game.initialLevel=26;game.VerificationRendererCapacity=1182;game.showLevelIntro=false;game.MeasureFrameCosts=true;game.MeasureDetailedDrawCosts=false;game.DeferTerminalPresentation=true;game.HintsEnabled=false;var source=JsonUtility.FromJson<LevelData>(assets.boards.levels[25].text);game.VerificationLevelOverride=ObstacleDensityFixture.Level(source,45,"crate");
   accept=(Action<TurnResult>)Delegate.CreateDelegate(typeof(Action<TurnResult>),game,typeof(GameplayScreen).GetMethod("Accept",Private));updateGame=(Action)Delegate.CreateDelegate(typeof(Action),game,typeof(GameplayScreen).GetMethod("Update",Private));yield return Ready();game.GetComponent<GameplayHUD>().ResultRequested=(won,level)=>true;
   // Code/driver warmups do not pretend to warm the later newly loaded banks.
   for(int warm=0;warm<2;warm++){game.VerificationSkipTurnPreparation=warm==0;game.Load(25);yield return Ready();accept(ObstacleDensityFixture.Solve(game.Model));while(game.Busy||game.VerificationTurnPreparationPending)yield return null;}
   foreach(string family in new[]{"crate","stone"})foreach(int count in new[]{1,45})for(int repeat=0;repeat<2;repeat++)for(int branch=0;branch<2;branch++){
    bool skipped=(branch==0)==(repeat%2==0);game.VerificationSkipTurnPreparation=skipped;game.VerificationLevelOverride=ObstacleDensityFixture.Level(source,count,family);double loaded=Time.realtimeSinceStartupAsDouble;game.Load(25);yield return Ready();
    var row=new NaturalRow{name=family+"_"+count+"_"+repeat+(skipped?"_skipped":"_prepared"),family=family,count=count,repeat=repeat,skipTurnPreparation=skipped,preparationSeconds=Time.realtimeSinceStartupAsDouble-loaded,frameStart=used};Result.naturalRows.Add(row);recordingRow=Result.naturalRows.Count-1;
    row.commandFrame=Time.frameCount;row.commandStartedWall=Time.realtimeSinceStartupAsDouble;var turn=ObstacleDensityFixture.Solve(game.Model);row.modelMs=(Time.realtimeSinceStartupAsDouble-row.commandStartedWall)*1000;double at=Time.realtimeSinceStartupAsDouble;accept(turn);row.acceptMs=(Time.realtimeSinceStartupAsDouble-at)*1000;row.commandFinishedWall=Time.realtimeSinceStartupAsDouble;row.commandMs=(row.commandFinishedWall-row.commandStartedWall)*1000;row.enqueueCost=game.LastCommandCost;if(!turn.accepted){Fail("Rejected natural fixture "+row.name);yield break;}
    while(game.Busy||game.VerificationTurnPreparationPending)yield return null;yield return null;yield return null;recordingRow=-1;row.frameCount=used-row.frameStart;row.settleSeconds=Time.realtimeSinceStartupAsDouble-row.commandStartedWall;row.turnHash=Hash(JsonUtility.ToJson(turn));row.finalHash=Hash(JsonUtility.ToJson(game.Model.Snapshot()));row.spriteCreates=bank.SpriteCreates;row.spriteEvictions=bank.SpriteEvictions;row.synchronousLoads=bank.SynchronousLoads;row.preparationBatches=bank.PowerPreparationBatches;row.preparationFrames=bank.PowerPreparationFrames;row.preparationCreates=bank.PowerPreparationCreates;row.preparationSkippedAtlases=bank.PowerPreparationSkippedAtlases;row.maximumPreparationBatchMs=bank.PowerPreparationMaxBatchMilliseconds;
   }
   foreach(string family in new[]{"crate","stone"})foreach(int count in new[]{1,45}){
    game.VerificationSkipTurnPreparation=false;game.VerificationLevelOverride=ObstacleDensityFixture.Level(source,count,family);game.Load(25);yield return Ready();var turn=ObstacleDensityFixture.Solve(game.Model);accept(turn);if(!turn.accepted){Fail("Rejected frozen fixture");yield break;}
    // Wait only for actual resource work, then stop automatic Update. No sleeps,
    // fabricated frames or target-frame-rate changes are used for frozen calls.
    // Checkpoint79 may publish only the leading swap at Accept. Await its
    // complete immutable metadata before selecting a frozen pose; this wait
    // is outside every natural Accept span and every timed frozen Render.
    while(game.VerificationStartupPending)yield return null;
    Set("pause",true);var queue=Get<List<BoardStep>>("queue");var required=bank.RequiredResources(queue);yield return null;
    while(game.VerificationPreparing||game.VerificationTurnPreparationPending||!bank.Ready(required))yield return null;yield return null;
    while(game.VerificationTurnPreparationPending)yield return null;game.enabled=false;
    int index=queue.FindIndex(s=>s.kind=="powerFall");if(index<0||queue[index].duration<FrozenAge){Fail("Frozen fixture does not contain requested powerFall age "+family+"/"+count);yield break;}float start=0;presentation.history.Clear();for(int i=0;i<=index;i++){presentation.Add(queue[i],start);if(i<index)start+=queue[i].duration;}
    var step=queue[index];Set("current",step);Set("idle",step.before);Set("clock",start+FrozenAge);Set("started",start);Set("queueIndex",index+1);Set("pause",true);Set("awaitingPlaybackPose",false);Set("playbackPoseAnchor",false);
    var row=new FrozenRow{name=family+"_"+count,family=family,count=count,phaseIndex=index,age=FrozenAge,clock=start+FrozenAge,phaseDuration=step.duration,resourcesReady=bank.Ready(bank.RequiredResources(queue)),preparationPending=bank.PowerPreparationPending,turnHash=Hash(JsonUtility.ToJson(turn)),finalHash=Hash(JsonUtility.ToJson(game.Model.Snapshot())),queueHash=Hash(JsonUtility.ToJson(new StepList{steps=queue}))};Result.frozenRows.Add(row);if(!row.resourcesReady||row.preparationPending){Fail("Frozen resources not ready");yield break;}
    for(int warm=0;warm<2;warm++){game.VerificationUseCheckpoint76Sampling=true;updateGame();game.VerificationUseCheckpoint76Sampling=false;updateGame();}Capture(row,true);
    for(int pair=0;pair<4;pair++){var sample=new FrozenPair{index=pair,controlFirst=pair%2==0};if(sample.controlFirst){Timed(true,ref sample);Timed(false,ref sample);}else{Timed(false,ref sample);Timed(true,ref sample);}row.pairs[pair]=sample;yield return null;}
    Capture(row,false);if(row.beforeControlDrawHash!=row.beforeRefinedDrawHash||row.beforeControlMeshHash!=row.beforeRefinedMeshHash||row.afterControlDrawHash!=row.afterRefinedDrawHash||row.afterControlMeshHash!=row.afterRefinedMeshHash||row.beforeControlDrawHash!=row.afterControlDrawHash||row.beforeControlMeshHash!=row.afterControlMeshHash){Fail("Frozen draw/mesh parity failed "+row.name);yield break;}
    game.VerificationUseCheckpoint76Sampling=false;game.enabled=true;Set("pause",false);
   }
   // Validate after all measurements, avoiding validator allocations/branching
   // in observed frames. Hashing and serialization are also outside playback.
   for(int i=0;i<used;i++){string error;if(!ValidateFrameCost(buffered[i].cost,out error)){Fail("Frame "+buffered[i].frame+": "+error);yield break;}}
   foreach(var row in Result.frozenRows)foreach(var pair in row.pairs){string error;if(!ValidateFrameCost(pair.controlCost,out error)||!ValidateFrameCost(pair.refinedCost,out error)){Fail("Frozen instrumentation: "+error);yield break;}}
   Finish(true);
  }
  [Serializable] sealed class StepList {public List<BoardStep> steps;}
  void Timed(bool control,ref FrozenPair pair){game.VerificationUseCheckpoint76Sampling=control;double began=Time.realtimeSinceStartupAsDouble;updateGame();double ended=Time.realtimeSinceStartupAsDouble;if(control){pair.controlStartedWall=began;pair.controlFinishedWall=ended;pair.controlCost=game.LastFrameCost;}else{pair.refinedStartedWall=began;pair.refinedFinishedWall=ended;pair.refinedCost=game.LastFrameCost;}}
  void Capture(FrozenRow row,bool before){game.VerificationUseCheckpoint76Sampling=true;updateGame();string cd=DrawHash(),cm=MeshHash();game.VerificationUseCheckpoint76Sampling=false;updateGame();string rd=DrawHash(),rm=MeshHash();if(before){row.beforeControlDrawHash=cd;row.beforeControlMeshHash=cm;row.beforeRefinedDrawHash=rd;row.beforeRefinedMeshHash=rm;}else{row.afterControlDrawHash=cd;row.afterControlMeshHash=cm;row.afterRefinedDrawHash=rd;row.afterRefinedMeshHash=rm;}}
  string DrawHash()=>Hash(JsonUtility.ToJson(new DrawState{draws=presentation.SampleLive(Get<BoardStep>("current"),Get<BoardSnapshot>("idle"),Get<float>("clock"),Get<float>("started"))}));
  string MeshHash(){var state=new MeshStates();foreach(var filter in Get<Transform>("root").GetComponentsInChildren<MeshFilter>(true)){var renderer=filter.GetComponent<MeshRenderer>();if(!renderer||!renderer.enabled)continue;var mesh=filter.sharedMesh;if(!mesh)continue;state.meshes.Add(new MeshState{name=filter.name,order=renderer.sortingOrder,vertices=mesh.vertices,uv=mesh.uv,colors=mesh.colors32,triangles=mesh.triangles});}return Hash(JsonUtility.ToJson(state));}
  void Finish(bool ok){if(Result==null||Result.status!="RUNNING")return;recordingRow=-1;StopAllCoroutines();Result.frames=new Frame[used];Array.Copy(buffered,Result.frames,used);Result.status=ok&&Result.errors.Count==0?"PASS_NATIVE_POWER_FALL77":"FAIL_NATIVE_POWER_FALL77";Application.logMessageReceived-=Log;if(game){game.VerificationUseCheckpoint76Sampling=false;game.gameObject.SetActive(false);Destroy(game.gameObject);}if(hidden!=null)for(int i=0;i<hidden.Length;i++)if(hidden[i])hidden[i].enabled=wasEnabled[i];string folder=Path.Combine(Application.persistentDataPath,"PowerFall77");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"Report.json"),JsonUtility.ToJson(Result,true));Completed?.Invoke(Result);}
  void OnDestroy(){Application.logMessageReceived-=Log;}
  public static bool ValidateFrameCost(GameplayScreen.FrameCost f,out string error){
   const double tolerance=.15;error=null;double[] spans={f.outerSetupMs,f.outerSampleMs,f.outerBeginMs,f.outerDrawMs,f.outerDisableMs,f.outerUploadMs,f.outerEndCollectionsMs,f.outerBankEndMs,f.outerSelectionMs};double sum=0;foreach(double span in spans){if(double.IsNaN(span)||double.IsInfinity(span)||span<0){error="invalid outer span";return false;}sum+=span;}
   double[] durations={f.updateMs,f.renderMs,f.outerSpanMs,f.outerWrapperResidualMs,f.sampleMs,f.bodySampleMs,f.effectsSampleMs,f.sortMs,f.lookupMs,f.batchAddMs,f.batchUploadMs,f.spriteUpdateMs,f.bankEndMs};foreach(double value in durations)if(double.IsNaN(value)||double.IsInfinity(value)||value<0){error="invalid duration";return false;}
   if(Math.Abs(sum-f.outerSpanMs)>.001||f.outerSpanMs>f.renderMs+tolerance||Math.Abs(f.renderMs-f.outerSpanMs-f.outerWrapperResidualMs)>.001){error="outer hierarchy";return false;}
   if(f.bodySampleMs+f.effectsSampleMs+f.sortMs>f.outerSampleMs+tolerance||f.lookupMs+f.batchAddMs+f.spriteUpdateMs>f.outerDrawMs+tolerance||f.batchUploadMs>f.outerUploadMs+tolerance||f.bankEndMs>f.outerBankEndMs+tolerance||f.sampleMs>f.outerSampleMs+f.outerBeginMs+tolerance||f.renderMs>f.updateMs+tolerance){error="nested hierarchy";return false;}
   if(!(f.updateStartedWall<=f.renderStartedWall&&f.renderStartedWall<=f.renderFinishedWall&&f.renderFinishedWall<=f.updateFinishedWall)){error="wall timestamp order";return false;}
   if(f.gcMaxGeneration<0){error="GC generation range";return false;}
   int[,] counts={{f.gc0BeforeUpdate,f.gc0BeforeRender,f.gc0AfterRender,f.gc0AfterUpdate},{f.gc1BeforeUpdate,f.gc1BeforeRender,f.gc1AfterRender,f.gc1AfterUpdate},{f.gc2BeforeUpdate,f.gc2BeforeRender,f.gc2AfterRender,f.gc2AfterUpdate}};
   for(int gen=0;gen<3;gen++)for(int point=0;point<4;point++){int count=counts[gen,point];if(gen>f.gcMaxGeneration?count!=-1:count<0||(point>0&&count<counts[gen,point-1])){error="GC snapshot chronology/support";return false;}}return true;
  }
#if UNITY_EDITOR
  [Serializable] sealed class InstrumentationReport {public string status="RUNNING",utc,scope="Native Unity Editor instrumentation arithmetic and deliberately invalid counter/timing records; not gameplay/device measurements.";public int checks,negativeControls;public List<string> errors=new List<string>();}
  public static void RunInstrumentationChecks(){var report=new InstrumentationReport{utc=DateTime.UtcNow.ToString("o")};try{
   var good=new GameplayScreen.FrameCost{outerSetupMs=1,outerSampleMs=2,outerBeginMs=1,outerDrawMs=4,outerDisableMs=1,outerUploadMs=1,outerEndCollectionsMs=1,outerBankEndMs=1,outerSelectionMs=1,outerSpanMs=13,outerWrapperResidualMs=1,renderMs=14,updateMs=16,sampleMs=3,bodySampleMs=1,effectsSampleMs=.5,sortMs=.2,lookupMs=1,batchAddMs=1,spriteUpdateMs=1,batchUploadMs=.5,bankEndMs=.5,updateStartedWall=1,renderStartedWall=1.001,renderFinishedWall=1.015,updateFinishedWall=1.016,gcMaxGeneration=2,gc0BeforeUpdate=10,gc0BeforeRender=10,gc0AfterRender=11,gc0AfterUpdate=11,gc1BeforeUpdate=3,gc1BeforeRender=3,gc1AfterRender=3,gc1AfterUpdate=3,gc2BeforeUpdate=1,gc2BeforeRender=1,gc2AfterRender=1,gc2AfterUpdate=1};string error;report.checks++;if(!ValidateFrameCost(good,out error))report.errors.Add("Positive hierarchy rejected: "+error);
   var cases=new List<GameplayScreen.FrameCost>();var bad=good;bad.outerDrawMs+=1;cases.Add(bad);bad=good;bad.outerSampleMs=-1;cases.Add(bad);bad=good;bad.renderMs=double.NaN;cases.Add(bad);bad=good;bad.outerWrapperResidualMs+=1;cases.Add(bad);bad=good;bad.outerSpanMs=15;cases.Add(bad);bad=good;bad.lookupMs=10;cases.Add(bad);bad=good;bad.bodySampleMs=10;cases.Add(bad);bad=good;bad.batchUploadMs=10;cases.Add(bad);bad=good;bad.bankEndMs=10;cases.Add(bad);bad=good;bad.renderFinishedWall=.9;cases.Add(bad);bad=good;bad.updateMs=1;cases.Add(bad);bad=good;bad.gc0AfterRender=9;cases.Add(bad);bad=good;bad.gc1BeforeRender=2;cases.Add(bad);bad=good;bad.gc2AfterUpdate=0;cases.Add(bad);bad=good;bad.gcMaxGeneration=0;cases.Add(bad);bad=good;bad.gc0BeforeUpdate=-1;cases.Add(bad);bad=good;bad.sampleMs=10;cases.Add(bad);
   foreach(var item in cases){report.checks++;report.negativeControls++;if(ValidateFrameCost(item,out error))report.errors.Add("Invalid counter/timing record was accepted at negative control "+report.negativeControls);}
   var unsupported=good;unsupported.gcMaxGeneration=0;unsupported.gc1BeforeUpdate=unsupported.gc1BeforeRender=unsupported.gc1AfterRender=unsupported.gc1AfterUpdate=-1;unsupported.gc2BeforeUpdate=unsupported.gc2BeforeRender=unsupported.gc2AfterRender=unsupported.gc2AfterUpdate=-1;report.checks++;if(!ValidateFrameCost(unsupported,out error))report.errors.Add("Unsupported GC generations rejected: "+error);
  }catch(Exception ex){report.errors.Add(ex.ToString());}report.status=report.errors.Count==0?"PASS_NATIVE_POWER_FALL_INSTRUMENTATION77":"FAIL_NATIVE_POWER_FALL_INSTRUMENTATION77";string output=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY77_OUTPUT");if(string.IsNullOrEmpty(output))output=Path.GetFullPath(Path.Combine(Application.dataPath,"../../Verification/Evidence/Gameplay77"));Directory.CreateDirectory(Path.Combine(output,"Native"));File.WriteAllText(Path.Combine(output,"Native/PowerFallInstrumentation.json"),JsonUtility.ToJson(report,true));UnityEditor.EditorApplication.Exit(report.errors.Count==0?0:1);}
#endif
 }
}
#endif

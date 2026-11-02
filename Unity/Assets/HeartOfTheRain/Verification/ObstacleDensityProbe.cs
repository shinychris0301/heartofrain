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
 // Explicit, isolated fixture board: no HomeLevelFlow, attempt, inventory or
 // progression callbacks are attached. No screenshot or report I/O while timed.
 // Variant syntax: baseline_1 | candidate_2 ... optionally followed by
 // "-stone", "-gate" or "-tiles" to break that family instead of crates.
 // Checkpoint 60: baseline draws effects through one SpriteRenderer each,
 // candidate through the effect mesh batcher; both keep every other
 // optimization (checkpoints 44 and 45) enabled.
 public sealed class ObstacleDensityProbe:MonoBehaviour {
  public const string Request="HOTR_RunObstacleDensity";
  [Serializable] public class Frame {public int phase,frame,draws,crateDraws,meshQuads,meshes,renderersCreated,spritesCreated;public float intervalMs,playbackAge;public string step;public double renderMs,sampleMs,updateMs,bodySampleMs,effectsSampleMs,sortMs,absoluteWall;public GameplayScreen.FrameCost cost;}
  [Serializable] public class Row {public string name,family,turnHash,finalHash;public bool checkpoint75Transform;public int crates,hits,cleared,powers,originX,originY,poolReady,poolEnd,peakDraws,peakMeshes,renderersCreated,crateSpritesCreated,gen0Collections,commandFrame;public double preparationSeconds,commandMs,modelMs,acceptMs,settleSeconds,commandStartedWall,commandFinishedWall;public GameplayScreen.CommandCost enqueueCost;}
  [Serializable] public class Report {public int profilingSchemaVersion=1;public bool detailedDrawCosts=true;public string status="RUNNING",utc,variant,family,platform,graphics,scope="Unaccelerated isolated gameplay fixture; elapsed CPU sections and frame intervals include OS/emulator scheduling. No capture/I/O in timed sections. Same-APK controls keep checkpoint-44/45 preparation, lookup, debris math and sorting; baseline renders effects through SpriteRenderers, candidate through the effect mesh batcher. Fixed geometry, seed, one-layer obstacles and power type; one untimed warm-up per process. Not physical-device certification.";public List<Row> rows=new List<Row>();public List<Frame> frames=new List<Frame>(8192);public List<string> errors=new List<string>();}
  public string variant="candidate";public GameplayUIAssets suppliedAssets;public Action<Report> Completed;public Action<GameplayScreen> InspectPeak;bool peakInspected;
  public Report Result {get;private set;}GameplayScreen game;Row row;double deadline,began;int gc;Canvas[] hidden;bool[] canvasEnabled;string family="crate",mode="candidate",reviewPlayerId;bool previousTransform;
  static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
  static string Hash(string s){using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(s))).Replace("-","").ToLowerInvariant();}
  static string pendingVariant;
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]static void Boot(){
   SceneManager.sceneLoaded-=Attach;pendingVariant=null;var path=Path.Combine(Application.persistentDataPath,Request);if(!File.Exists(path))return;
   pendingVariant=File.ReadAllText(path).Trim();File.Delete(path);SceneManager.sceneLoaded+=Attach;
  }
  static void Attach(Scene scene,LoadSceneMode mode){
   var first=FindFirstObjectByType<FirstStartPage>();if(!first)return;SceneManager.sceneLoaded-=Attach;first.reviewAlways=true;
   var host=first.home.GetComponent<PlayerProfileHost>();if(!host)host=first.home.gameObject.AddComponent<PlayerProfileHost>();
   var profile=PlayerProfile.New(new[]{5,5,3,2});host.VerificationRepository=new MemoryProfileRepository(profile);host.VerificationAuthorityFactory=_=>new UnavailableGiftAuthority();host.VerificationLivesClock=()=>1000;
   var go=new GameObject("Opt-in obstacle density review");DontDestroyOnLoad(go);var probe=go.AddComponent<ObstacleDensityProbe>();probe.variant=pendingVariant;probe.reviewPlayerId=profile.playerId;pendingVariant=null;
  }
  void Start(){previousTransform=EffectMeshBatcher.VerificationUseCheckpoint75Transform;int dash=variant.IndexOf('-');mode=dash<0?variant:variant.Substring(0,dash);family=dash<0?"crate":variant.Substring(dash+1);Result=new Report{utc=DateTime.UtcNow.ToString("o"),variant=variant,family=family,platform=Application.platform.ToString(),graphics=SystemInfo.graphicsDeviceName};if(mode.StartsWith("paired",StringComparison.Ordinal))Result.scope="Same-process alternating checkpoint75/current effect-transform controls. Both paths use the mesh batcher, identical fixtures, current playback and equally instrumented renderer; one untimed warm-up of each. Each pair reloads the board/bank; caches and OS are not flushed. Rendering spans include observer/emulator/host overhead; not physical-device certification.";deadline=Time.realtimeSinceStartupAsDouble+360;Application.logMessageReceived+=Log;StartCoroutine(Run());}
  void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert){Result.errors.Add(text+"\n"+stack);Finish(false);}}
  void Update(){if(Result.status=="RUNNING"&&Time.realtimeSinceStartupAsDouble>deadline){Result.errors.Add("Obstacle density timeout");Finish(false);}}
  void LateUpdate(){if(row==null||!game||game.LastFrameCost.frame!=Time.frameCount)return;var f=game.LastFrameCost;row.peakDraws=Math.Max(row.peakDraws,f.draws);row.peakMeshes=Math.Max(row.peakMeshes,f.meshes);row.renderersCreated+=f.poolCreated;Result.frames.Add(new Frame{phase=Result.rows.Count,frame=f.frame,draws=f.draws,crateDraws=f.crateDraws,meshQuads=f.meshQuads,meshes=f.meshes,playbackAge=game.VerificationPlaybackAge,step=game.VerificationPlaybackKind,bodySampleMs=f.bodySampleMs,effectsSampleMs=f.effectsSampleMs,sortMs=f.sortMs,renderersCreated=f.poolCreated,spritesCreated=f.spriteCreated,intervalMs=Time.unscaledDeltaTime*1000,renderMs=f.renderMs,sampleMs=f.sampleMs,updateMs=f.updateMs,absoluteWall=Time.realtimeSinceStartupAsDouble,cost=f});}
  IEnumerator Ready(){while(!game.CanAct)yield return null;yield return null;}
  int FamilyCreates(M46AtlasBank bank){var entries=(IDictionary)typeof(M46AtlasBank).GetField("sprites",Private).GetValue(bank);int n=0;string prefix="o/"+family+"/";foreach(string key in entries.Keys)if(key.StartsWith(prefix,StringComparison.Ordinal))n++;return n;}
  IEnumerator Run(){
   GameplayUIAssets assets=suppliedAssets;
   if(!assets){FirstStartPage first;while(!(first=FindFirstObjectByType<FirstStartPage>())||!first.Initialized)yield return null;
    // Let Launch observe the visible destination before disabling its canvases.
    while(FindFirstObjectByType<HeartOfTheRain.App.Launch.LaunchPage>())yield return null;
    var host=first.home.GetComponent<PlayerProfileHost>();if(!host||!host.Ready||!(host.VerificationRepository is MemoryProfileRepository)||host.Service.Read().playerId!=reviewPlayerId){Result.errors.Add("Obstacle density review did not initialize its isolated memory profile");Finish(false);yield break;}
    assets=first.assets.Gameplay;hidden=FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID);canvasEnabled=hidden.Select(c=>c.enabled).ToArray();foreach(var c in hidden)c.enabled=false;}
   game=new GameObject("Isolated obstacle stress board").AddComponent<GameplayScreen>();game.uiAssets=assets;game.initialLevel=26;game.VerificationRendererCapacity=1182;game.VerificationUseLegacyDensityWork=false;game.VerificationUseSpriteRenderersForEffects=mode.StartsWith("baseline",StringComparison.Ordinal);Result.detailedDrawCosts=mode.IndexOf("coarse",StringComparison.Ordinal)<0;game.MeasureDetailedDrawCosts=Result.detailedDrawCosts;var source=JsonUtility.FromJson<LevelData>(assets.boards.levels[25].text);game.VerificationLevelOverride=ObstacleDensityFixture.Level(source,45,family);game.showLevelIntro=false;game.MeasureFrameCosts=true;double loaded=Time.realtimeSinceStartupAsDouble;yield return Ready();game.GetComponent<GameplayHUD>().ResultRequested=(won,level)=>true;
   // Prime code/shader/driver paths without including the cold process command.
   typeof(GameplayScreen).GetMethod("Accept",Private).Invoke(game,new object[]{ObstacleDensityFixture.Solve(game.Model)});while(game.Busy)yield return null;
   bool paired=mode.StartsWith("paired",StringComparison.Ordinal);
   if(paired){EffectMeshBatcher.VerificationUseCheckpoint75Transform=true;game.Load(25);yield return Ready();typeof(GameplayScreen).GetMethod("Accept",Private).Invoke(game,new object[]{ObstacleDensityFixture.Solve(game.Model)});while(game.Busy)yield return null;EffectMeshBatcher.VerificationUseCheckpoint75Transform=false;}
   int[] counts=paired?new[]{1,45}:mode.EndsWith("2",StringComparison.Ordinal)?new[]{45,32,16,8,1}:new[]{1,8,16,32,45};
   foreach(int repeat in paired?new[]{0,1,2,3}:new[]{0,1})foreach(int count in counts)foreach(int branch in paired?new[]{0,1}:new[]{0}){
    bool control=paired&&(branch==0)==(repeat%2==0);EffectMeshBatcher.VerificationUseCheckpoint75Transform=control;
    loaded=Time.realtimeSinceStartupAsDouble;game.VerificationLevelOverride=ObstacleDensityFixture.Level(source,count,family);game.Load(25);yield return Ready();
    double preparation=Time.realtimeSinceStartupAsDouble-loaded;var model=game.Model;var pieces=model.Pieces.Values.Count(p=>p.family==family);string name=family+"_"+count+"_"+repeat;
    if(paired)name+=control?"_control75":"_current76";
    yield return new WaitForSecondsRealtime(.3f);var bank=(M46AtlasBank)typeof(GameplayScreen).GetField("bank",Private).GetValue(game);int before=FamilyCreates(bank);gc=GC.CollectionCount(0);row=new Row{name=name,family=family,checkpoint75Transform=control,crates=pieces,poolReady=game.RendererPoolCount,preparationSeconds=preparation};began=Time.realtimeSinceStartupAsDouble;
    double at=Time.realtimeSinceStartupAsDouble;row.commandStartedWall=at;row.commandFrame=Time.frameCount;var turn=ObstacleDensityFixture.Solve(model);row.modelMs=(Time.realtimeSinceStartupAsDouble-at)*1000;double accept=Time.realtimeSinceStartupAsDouble;typeof(GameplayScreen).GetMethod("Accept",Private).Invoke(game,new object[]{turn});row.acceptMs=(Time.realtimeSinceStartupAsDouble-accept)*1000;row.commandMs=(Time.realtimeSinceStartupAsDouble-at)*1000;row.commandFinishedWall=Time.realtimeSinceStartupAsDouble;row.enqueueCost=game.LastCommandCost;
    if(!turn.accepted){Result.errors.Add("Rejected fixture "+name);Finish(false);yield break;}
    // Hashing/counters are deferred until after playback to avoid disturbing pacing.
    while(game.Busy){if(count==45&&!peakInspected&&game.ActiveSpriteCount>600&&InspectPeak!=null){peakInspected=true;InspectPeak(game);}yield return null;}yield return new WaitForSecondsRealtime(.15f);var complete=row;row=null;complete.settleSeconds=Time.realtimeSinceStartupAsDouble-began;complete.poolEnd=game.RendererPoolCount;complete.crateSpritesCreated=FamilyCreates(bank)-before;complete.gen0Collections=GC.CollectionCount(0)-gc;complete.turnHash=Hash(JsonUtility.ToJson(turn));complete.finalHash=Hash(JsonUtility.ToJson(model.Snapshot()));complete.hits=turn.steps.Sum(s=>s.damage.Count(d=>d.family==family));complete.cleared=turn.steps.Sum(s=>s.removed.Count(r=>r.piece.family==family));complete.powers=turn.steps.Count(s=>s.kind=="power");var power=turn.steps.First(s=>s.powerPlan!=null).powerPlan;complete.originX=power.originX;complete.originY=power.originY;Result.rows.Add(complete);
   }
   Finish(true);
  }
  void Finish(bool ok){if(Result.status!="RUNNING")return;row=null;EffectMeshBatcher.VerificationUseCheckpoint75Transform=previousTransform;Result.status=ok&&Result.errors.Count==0?"PASS_OBSTACLE_DENSITY_PLAYBACK":"FAIL_OBSTACLE_DENSITY_PLAYBACK";Application.logMessageReceived-=Log;if(game){game.gameObject.SetActive(false);Destroy(game.gameObject);}if(hidden!=null)for(int i=0;i<hidden.Length;i++)if(hidden[i])hidden[i].enabled=canvasEnabled[i];string output=Path.Combine(Application.persistentDataPath,"ObstacleDensity");Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"Report.json"),JsonUtility.ToJson(Result,true));Completed?.Invoke(Result);}
  void OnDestroy(){EffectMeshBatcher.VerificationUseCheckpoint75Transform=previousTransform;Application.logMessageReceived-=Log;}
 }
}
#endif

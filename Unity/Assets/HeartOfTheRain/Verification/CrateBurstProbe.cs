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
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.App.FirstStart;
namespace HeartOfTheRain.Verification {
 // Explicit, isolated fixture board: no HomeLevelFlow, attempt, inventory or
 // progression callbacks are attached. No screenshot or report I/O while timed.
 public sealed class CrateBurstProbe:MonoBehaviour {
  public const string Request="HOTR_RunCrateBurst";
  [Serializable] public class Frame {public int phase,frame,draws,renderersCreated,spritesCreated;public float intervalMs;public double renderMs,sampleMs,updateMs;}
  [Serializable] public class Row {public string name,turnHash,finalHash;public int crates,hits,cleared,powers,poolReady,poolEnd,peakDraws,renderersCreated,crateSpritesCreated,gen0Collections;public double preparationSeconds,commandMs,settleSeconds;}
  [Serializable] public class Report {public string status="RUNNING",utc,variant,platform,graphics,scope="Unaccelerated isolated gameplay fixture; elapsed CPU sections and frame intervals include OS/emulator scheduling. No capture/I/O in timed sections. Same-APK control disables only crate preparation. Not physical-device certification.";public List<Row> rows=new List<Row>();public List<Frame> frames=new List<Frame>(8192);public List<string> errors=new List<string>();}
  public string variant="candidate";public GameplayUIAssets suppliedAssets;public Action<Report> Completed;
  public Report Result {get;private set;}GameplayScreen game;Row row;double deadline,began;int gc;Canvas[] hidden;bool[] canvasEnabled;
  static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
  static string Hash(string s){using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(s))).Replace("-","").ToLowerInvariant();}
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]static void Boot(){var path=Path.Combine(Application.persistentDataPath,Request);if(!File.Exists(path))return;var variant=File.ReadAllText(path).Trim();File.Delete(path);var go=new GameObject("Opt-in crate burst review");DontDestroyOnLoad(go);go.AddComponent<CrateBurstProbe>().variant=variant;}
  void Start(){Result=new Report{utc=DateTime.UtcNow.ToString("o"),variant=variant,platform=Application.platform.ToString(),graphics=SystemInfo.graphicsDeviceName};deadline=Time.realtimeSinceStartupAsDouble+240;Application.logMessageReceived+=Log;StartCoroutine(Run());}
  void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert){Result.errors.Add(text+"\n"+stack);Finish(false);}}
  void Update(){if(Result.status=="RUNNING"&&Time.realtimeSinceStartupAsDouble>deadline){Result.errors.Add("Crate burst timeout");Finish(false);}}
  void LateUpdate(){if(row==null||!game||game.LastFrameCost.frame!=Time.frameCount)return;var f=game.LastFrameCost;row.peakDraws=Math.Max(row.peakDraws,f.draws);row.renderersCreated+=f.poolCreated;Result.frames.Add(new Frame{phase=Result.rows.Count,frame=f.frame,draws=f.draws,renderersCreated=f.poolCreated,spritesCreated=f.spriteCreated,intervalMs=Time.unscaledDeltaTime*1000,renderMs=f.renderMs,sampleMs=f.sampleMs,updateMs=f.updateMs});}
  IEnumerator Ready(){while(!game.CanAct)yield return null;yield return null;}
  static TurnResult Solve(BoardModel b,string kind){
   var a=b.Pieces.Values.First(p=>p.family=="gem"&&b.At(p.x+1,p.y)?.family=="gem");var partner=b.At(a.x+1,a.y);b.InjectReviewPower(a.x,a.y,7);b.InjectReviewPower(partner.x,partner.y,kind=="double_orb"?7:4);return b.Swap(a.x,a.y,partner.x,partner.y);
  }
  int CrateCreates(M46AtlasBank bank){var entries=(IDictionary)typeof(M46AtlasBank).GetField("sprites",Private).GetValue(bank);int n=0;foreach(string key in entries.Keys)if(key.StartsWith("o/crate/",StringComparison.Ordinal))n++;return n;}
  IEnumerator Run(){
   GameplayUIAssets assets=suppliedAssets;
   if(!assets){FirstStartPage first;while(!(first=FindFirstObjectByType<FirstStartPage>())||!first.Initialized||FindFirstObjectByType<HeartOfTheRain.App.Launch.LaunchPage>())yield return null;assets=first.assets.Gameplay;hidden=FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID);canvasEnabled=hidden.Select(c=>c.enabled).ToArray();foreach(var c in hidden)c.enabled=false;}
   game=new GameObject("Isolated crate stress board").AddComponent<GameplayScreen>();game.uiAssets=assets;game.initialLevel=12;game.showLevelIntro=false;game.MeasureFrameCosts=true;game.VerificationSkipCratePreparation=variant.StartsWith("baseline",StringComparison.Ordinal);double loaded=Time.realtimeSinceStartupAsDouble;yield return Ready();game.GetComponent<GameplayHUD>().ResultRequested=(won,level)=>true;
   foreach(int repeat in new[]{0,1})foreach(var fixture in new[]{new[]{11,0},new[]{25,0},new[]{41,1}}){
    if(Result.rows.Count>0){loaded=Time.realtimeSinceStartupAsDouble;game.Load(fixture[0]);yield return Ready();}
    double preparation=Time.realtimeSinceStartupAsDouble-loaded;var model=game.Model;var crates=model.Pieces.Values.Count(p=>p.family=="crate");string name="L"+(fixture[0]+1)+"_"+(fixture[1]==0?"double_orb":"orb_rocket")+"_"+repeat;
    yield return new WaitForSecondsRealtime(.3f);var bank=(M46AtlasBank)typeof(GameplayScreen).GetField("bank",Private).GetValue(game);int before=CrateCreates(bank);gc=GC.CollectionCount(0);row=new Row{name=name,crates=crates,poolReady=game.RendererPoolCount,preparationSeconds=preparation};began=Time.realtimeSinceStartupAsDouble;
    double at=Time.realtimeSinceStartupAsDouble;var turn=Solve(model,fixture[1]==0?"double_orb":"orb_rocket");typeof(GameplayScreen).GetMethod("Accept",Private).Invoke(game,new object[]{turn});row.commandMs=(Time.realtimeSinceStartupAsDouble-at)*1000;
    if(!turn.accepted){Result.errors.Add("Rejected fixture "+name);Finish(false);yield break;}
    // Hashing/counters are deferred until after playback to avoid disturbing pacing.
    while(game.Busy)yield return null;yield return new WaitForSecondsRealtime(.15f);var complete=row;row=null;complete.settleSeconds=Time.realtimeSinceStartupAsDouble-began;complete.poolEnd=game.RendererPoolCount;complete.crateSpritesCreated=CrateCreates(bank)-before;complete.gen0Collections=GC.CollectionCount(0)-gc;complete.turnHash=Hash(JsonUtility.ToJson(turn));complete.finalHash=Hash(JsonUtility.ToJson(model.Snapshot()));complete.hits=turn.steps.Sum(s=>s.damage.Count(d=>d.family=="crate"));complete.cleared=turn.steps.Sum(s=>s.removed.Count(r=>r.piece.family=="crate"));complete.powers=turn.steps.Count(s=>s.kind=="power");Result.rows.Add(complete);
   }
   Finish(true);
  }
  void Finish(bool ok){if(Result.status!="RUNNING")return;row=null;Result.status=ok&&Result.errors.Count==0?"PASS_CRATE_BURST_PLAYBACK":"FAIL_CRATE_BURST_PLAYBACK";Application.logMessageReceived-=Log;if(game){game.gameObject.SetActive(false);Destroy(game.gameObject);}if(hidden!=null)for(int i=0;i<hidden.Length;i++)if(hidden[i])hidden[i].enabled=canvasEnabled[i];string output=Path.Combine(Application.persistentDataPath,"CrateBurst");Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"Report.json"),JsonUtility.ToJson(Result,true));Completed?.Invoke(Result);}
  void OnDestroy(){Application.logMessageReceived-=Log;}
 }
}
#endif

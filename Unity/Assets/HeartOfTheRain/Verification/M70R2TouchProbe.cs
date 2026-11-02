#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.IO;
using System.Linq;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 // Consumed opt-in markers, transient boards only. No profile/inventory grants.
 public sealed class M70R2TouchProbe:MonoBehaviour {
  const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic|BindingFlags.Public;
  [Serializable] public class Pose {public string key,phase,sprite;public int id,atlas,frame;public float clock,age,x,y,sx,sy;}
  [Serializable] public class Report {public string status="STARTING",utc,mode,action,scope="Actual Android swipes or intro tap; starting reveal, pause/retry and injected load-failure cases use explicit development lifecycle controls. Transient fixtures, no save writes; not a performance test.";public int fromX,fromY,toX,toY,width,height,columns,rows,expectedPower,createdPower=-1,movesBefore,syncBefore,syncAfter;public bool accepted,gateHeld,pauseChecked,retryChecked,failureChecked;public List<Pose> poses=new List<Pose>();public List<string> failures=new List<string>();}
  Report report;GameplayScreen game;GameplayUIAssets original;M46Assets clone;string expected;int index;bool ready,begun,grant,convert,failedResource,pausedOnce,retrying;float deadline,born=-1,pauseAt,pausedClock;int[] kinds;string originalPath;
  string Folder=>Path.Combine(Application.persistentDataPath,"M70R2Review");
  static T Field<T>(object obj,string name)=>(T)obj.GetType().GetField(name,Flags).GetValue(obj);
  IDictionary Births()=>Field<IDictionary>(Field<BoardPresentation>(game,"presentation"),"powerBirths");
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)] static void Boot(){var p=Path.Combine(Application.persistentDataPath,"HOTR_RunM70R2");if(!File.Exists(p))return;string mode=File.ReadAllText(p).Trim();File.Delete(p);foreach(var f in FindObjectsByType<FirstStartPage>(UnityEngine.FindObjectsSortMode.InstanceID))f.reviewAlways=true;new GameObject("Opt-in M70R2 creation proof").AddComponent<M70R2TouchProbe>().report=new Report{utc=DateTime.UtcNow.ToString("o"),mode=mode};}
  IEnumerator Start(){
   Directory.CreateDirectory(Folder);Application.logMessageReceived+=Log;deadline=Time.realtimeSinceStartup+150;
   while(!FindFirstObjectByType<FirstStartPage>()||!FindFirstObjectByType<FirstStartPage>().IsVisible)yield return null;
   var f=FindFirstObjectByType<FirstStartPage>();original=f.assets.Gameplay;f.Request("skip");f.Request("skip");f.home.SetPresentation(false,false);
   grant=report.mode.StartsWith("Grant")||report.mode=="FailureRetry";convert=report.mode.StartsWith("Conversion");kinds=report.mode=="FailureRetry"?new[]{4}:new[]{4,21,7,16};
   index=report.mode=="GrantIntro"?Array.FindIndex(original.boards.levels,t=>{var l=JsonUtility.FromJson<LevelData>(t.text);return l.columns==9&&l.rows==11;}):report.mode=="GrantNoIntro"?Array.FindIndex(original.boards.levels,t=>JsonUtility.FromJson<LevelData>(t.text).columns==11):0;
   var ui=original;
   if(report.mode=="FailureRetry"){ui=Instantiate(original);clone=Instantiate(original.boards);clone.powerResources=(string[])clone.powerResources.Clone();originalPath=clone.powerResources[9];clone.powerResources[9]="HOTR_Verification_Missing_Power";ui.boards=clone;}
   game=new GameObject("Creation review gameplay").AddComponent<GameplayScreen>();game.uiAssets=ui;game.initialLevel=index+1;game.showLevelIntro=report.mode=="GrantIntro";game.ReviewInputBlocked=true;game.SharedToolInventory=new BoosterInventory();if(grant)game.pendingStartingPowers=(int[])kinds.Clone();
   while(!game.InitializationComplete)yield return null;game.GetComponent<GameplayHUD>().ResultRequested=(won,level)=>true;
   Cell from=new Cell(4,4),to=new Cell(5,4);
   if(grant){var shadow=new BoardModel(JsonUtility.FromJson<LevelData>(original.boards.levels[index].text));string error;if(!shadow.TryPlaceStartingPowers(kinds,out error))throw new Exception(error);expected=JsonUtility.ToJson(shadow.Snapshot());report.gateHeld=Births().Count==0&&Field<bool>(game,"startingCreationPending");if(!report.gateHeld)report.failures.Add("Birth elapsed before visible ownership");
    if(report.mode=="FailureRetry"){report.failureChecked=failedResource&&game.Paused&&game.Busy&&!game.CanAct&&Births().Count==0&&!string.IsNullOrEmpty(game.StartingPowerError);if(!report.failureChecked)report.failures.Add("Load failure was not gated");}
   }else{
    int kind=report.mode=="MatchV"?5:report.mode=="MatchBomb"?21:report.mode=="MatchOrb"?7:report.mode=="MatchSeeker"?11:4;report.expectedPower=kind;var level=M70R2Fixtures.Match(kind);var board=new BoardModel(level);var shadow=new BoardModel(level);
    if(convert){int partner=report.mode=="ConversionBomb"?21:4;board.InjectReviewPower(4,4,7);board.InjectReviewPower(5,4,partner);shadow.InjectReviewPower(4,4,7);shadow.InjectReviewPower(5,4,partner);}else{from=M70R2Fixtures.From(kind);to=new Cell(4,4);}
    var turn=shadow.Swap(from.x,from.y,to.x,to.y);expected=JsonUtility.ToJson(shadow.Snapshot());yield return Field<M46AtlasBank>(game,"bank").Prewarm(Field<M46AtlasBank>(game,"bank").RequiredResources(BoardPlayback.Build(turn.steps,level)));
    typeof(GameplayScreen).GetField("board",Flags).SetValue(game,board);typeof(GameplayScreen).GetField("idle",Flags).SetValue(game,board.Snapshot());
   }
   report.movesBefore=game.Model.Moves;report.columns=game.Model.Level.columns;report.rows=game.Model.Level.rows;report.syncBefore=game.SynchronousTextureLoads;
   game.PlayerActionCompleted+=record=>report.accepted=record.accepted;game.StepStarted+=s=>{if(s.kind=="match"&&s.created.Count>0&&born<0){born=Field<float>(game,"clock");report.createdPower=s.created[0].power;}};
   yield return null;yield return new WaitForEndOfFrame();var camera=Field<Camera>(game,"view");var root=Field<Transform>(game,"root");Vector3 Pixel(Cell c)=>camera.WorldToScreenPoint(root.TransformPoint(new Vector3(c.x-(report.columns-1)*.5f,c.y-(report.rows-1)*.5f,0)));var a=Pixel(from);var b=Pixel(to);report.fromX=Mathf.RoundToInt(a.x);report.fromY=Screen.height-Mathf.RoundToInt(a.y);report.toX=Mathf.RoundToInt(b.x);report.toY=Screen.height-Mathf.RoundToInt(b.y);
   report.action=grant?"release": "swipe";
   if(report.mode=="GrantIntro"){var modal=Field<RectTransform>(game.GetComponent<GameplayHUD>(),"modal");var button=modal.GetComponentInChildren<Button>();var rect=(RectTransform)button.transform;var p=RectTransformUtility.WorldToScreenPoint(null,rect.TransformPoint(rect.rect.center));report.toX=Mathf.RoundToInt(p.x);report.toY=Screen.height-Mathf.RoundToInt(p.y);report.action="introTap";}
   report.width=Screen.width;report.height=Screen.height;report.status="READY_FOR_NATIVE_GESTURE";ready=true;Save();
  }
  void LateUpdate(){
   if(!ready||report.status!="READY_FOR_NATIVE_GESTURE")return;
   if(Time.realtimeSinceStartup>deadline){report.failures.Add("Creation lifecycle timeout");Finish();return;}
   if(!begun){var p=Path.Combine(Folder,"Begin");if(!File.Exists(p))return;File.Delete(p);begun=true;game.ReviewInputBlocked=false;if(report.mode=="FailureRetry"){clone.powerResources[9]=originalPath;game.pendingStartingPowers=(int[])kinds.Clone();game.Load(index,0,"verification-load-retry");}return;}
   if(!game.InitializationComplete)return;
   float clock=Field<float>(game,"clock");var view=Field<BoardPresentation>(game,"presentation");var current=Field<BoardStep>(game,"current");
   if(grant&&born<0&&Births().Count>0)born=Field<float>(Births().Values.Cast<object>().First(),"start");
   var draws=view.SampleLive(current,Field<BoardSnapshot>(game,"idle"),clock,Field<float>(game,"started"));
   foreach(var d in draws)if(!Field<bool>(game,"startingCreationPending")&&d.bank=="power"&&(d.order==10||convert&&d.order==20)){
    var sprite=Field<M46AtlasBank>(game,"bank").Get(d);if(!sprite)continue;
    report.poses.Add(new Pose{key=d.key,phase=current==null?"idle":current.kind,sprite=sprite.name,id=d.pieceId,atlas=d.atlas,frame=Time.frameCount,clock=clock,age=d.age,x=d.x,y=d.y,sx=d.sx,sy=d.sy});
   }
   if(report.mode=="GrantIntro"&&born>=0&&!pausedOnce&&clock-born>.1f){pausedOnce=true;game.SetPause(true);pausedClock=clock;pauseAt=Time.realtimeSinceStartup;}
   if(pausedOnce&&!report.pauseChecked&&Time.realtimeSinceStartup-pauseAt>.25f){report.pauseChecked=Math.Abs(clock-pausedClock)<.0001f;if(!report.pauseChecked)report.failures.Add("Pause advanced creation clock");game.SetPause(false);}
   if(report.mode=="GrantIntro"&&!retrying&&born>=0&&clock-born>1){
    if(JsonUtility.ToJson(game.Model.Snapshot())!=expected)report.failures.Add("Starting reveal mutated model");retrying=true;game.showLevelIntro=false;game.Load(index,0,"verification-retry");var shadow=new BoardModel(JsonUtility.FromJson<LevelData>(original.boards.levels[index].text));expected=JsonUtility.ToJson(shadow.Snapshot());return;
   }
   bool complete=grant?born>=0&&(retrying?game.InitializationComplete&&!game.Busy:clock-born>.85f):report.accepted&&!game.Busy&&(born<0||clock-born>.75f);
   if(!complete)return;
   if(retrying){report.retryChecked=Births().Count==0&&!game.HasStartedWithPowers&&!Field<bool>(game,"startingCreationPending");if(!report.retryChecked)report.failures.Add("Retry replayed an old grant or birth clock");}
   if(JsonUtility.ToJson(game.Model.Snapshot())!=expected)report.failures.Add("Visual playback changed the expected solve");
   if(!grant&&!convert&&(report.createdPower!=report.expectedPower||game.Model.Moves!=report.movesBefore-1))report.failures.Add("Creation recipe, anchor or move charge changed");
   var formation=report.poses.Where(p=>p.key=="Create"||p.key.EndsWith("_Create")).ToArray();if(formation.Select(p=>p.sprite).Distinct().Count()<2)report.failures.Add("No multiple native formation frames");
   if(grant&&formation.Select(p=>p.atlas).Distinct().Count()!=kinds.Length)report.failures.Add("Starting items skipped a formation");
   if(convert&&!report.poses.Any(p=>p.key=="Charge"))report.failures.Add("Conversion lost charge phase");
   report.syncAfter=game.SynchronousTextureLoads;if(grant&&!retrying&&report.syncAfter!=report.syncBefore)report.failures.Add("Starting reveal synchronously loaded a texture");game.Model.Validate();Finish();
  }
  void Log(string text,string stack,LogType type){if(type!=LogType.Error&&type!=LogType.Exception&&type!=LogType.Assert)return;if(report.mode=="FailureRetry"&&text=="Missing texture resource: HOTR_Verification_Missing_Power"){failedResource=true;return;}report.failures.Add(text+"\n"+stack);Finish();}
  void Save()=>File.WriteAllText(Path.Combine(Folder,"Report.json"),JsonUtility.ToJson(report,true));
  void Finish(){report.status=report.failures.Count==0?"PASS_NATIVE_DEVICE_M70R2_CREATION":"FAIL_NATIVE_DEVICE_M70R2_CREATION";Application.logMessageReceived-=Log;Save();}
  void OnDestroy(){Application.logMessageReceived-=Log;}
 }
}
#endif

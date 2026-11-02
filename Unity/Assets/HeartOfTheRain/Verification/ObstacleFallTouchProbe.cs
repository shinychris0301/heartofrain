#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.IO;
using System.Linq;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 public sealed class ObstacleFallTouchProbe:MonoBehaviour {
  const string Marker="HOTR_RunObstacleFall";const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
  [Serializable] public class Pose {public int frame;public float age,x,y,sx,sy;}
  [Serializable] public class Report {public string status="STARTING",utc,mode,scope="Actual Android tool/power input on a transient obstacle fixture; no save writes. Slow mode deliberately stalls one frame180ms; no performance certification.";public int targetX,targetY,sourceId,fromX,fromY,toX,toY,width,height,inputFromX,inputFromY,inputToX,inputToY;public float seconds,landing,forcedSlowAge=-1;public bool accepted,forcedSlowFrame;public List<Pose> poses=new List<Pose>();public List<string> failures=new List<string>();}
  GameplayScreen game;Report report;bool ready,rocket,natural,large;float deadline;string expected;int column;
  string Output=>Path.Combine(Application.persistentDataPath,"ObstacleFallReview");
  static T Field<T>(object o,string n)=>(T)o.GetType().GetField(n,Private).GetValue(o);
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)] static void Boot(){var path=Path.Combine(Application.persistentDataPath,Marker);if(!File.Exists(path))return;string mode=File.ReadAllText(path).Trim();File.Delete(path);foreach(var f in FindObjectsByType<FirstStartPage>(UnityEngine.FindObjectsSortMode.InstanceID))f.reviewAlways=true;new GameObject("Opt-in obstacle fall touch").AddComponent<ObstacleFallTouchProbe>().report=new Report{utc=DateTime.UtcNow.ToString("o"),mode=mode};}
  public static LevelData MatchFixture(){var level=PlaybackFixtures.StackedStones();foreach(var gem in level.initialTiles)if(gem.y==1){if(gem.x==3)gem.color=2;else if(gem.x==4||gem.x==5)gem.color=3;}return level;}
  IEnumerator Start(){
   Directory.CreateDirectory(Output);Application.logMessageReceived+=Log;deadline=Time.realtimeSinceStartup+120;
   while(!FindFirstObjectByType<FirstStartPage>()||!FindFirstObjectByType<FirstStartPage>().IsVisible)yield return null;
   var first=FindFirstObjectByType<FirstStartPage>();var ui=first.assets.Gameplay;first.Request("skip");first.Request("skip");first.home.SetPresentation(false,false);
   game=new GameObject("Obstacle fall review board").AddComponent<GameplayScreen>();game.uiAssets=ui;game.showLevelIntro=false;while(!game.InitializationComplete)yield return null;
   game.GetComponent<GameplayHUD>().ResultRequested=(won,level)=>true;
   column=report.mode=="EdgeLeft"?0:report.mode=="EdgeRight"?8:4;rocket=report.mode=="Rocket";natural=report.mode=="Match";large=report.mode=="LargeGap";var levelData=large?PlaybackFixtures.LargeObstacleGap():natural?MatchFixture():PlaybackFixtures.StackedStones(column);
   var shadow=new BoardModel(levelData);if(rocket)shadow.InjectReviewPower(column,0,5);var turn=natural?shadow.Swap(3,0,3,1):rocket?shadow.Tap(column,0):shadow.UseBooster(BoosterKind.Hammer,large?3:column,large?1:2,new BoosterInventory());expected=JsonUtility.ToJson(shadow.Snapshot());
   var bank=Field<M46AtlasBank>(game,"bank");yield return bank.Prewarm(bank.RequiredResources(BoardPlayback.Build(turn.steps,levelData)));
   var board=new BoardModel(levelData);if(rocket)board.InjectReviewPower(column,0,5);typeof(GameplayScreen).GetField("board",Private).SetValue(game,board);typeof(GameplayScreen).GetField("idle",Private).SetValue(game,board.Snapshot());report.sourceId=board.At(large?2:column==0?1:column-1,natural?4:3).id;
   game.PlayerActionCompleted+=action=>report.accepted=action.accepted;
   yield return null;yield return new WaitForEndOfFrame();var camera=Field<Camera>(game,"view");var root=Field<Transform>(game,"root");Vector3 PixelAt(int x,int y)=>camera.WorldToScreenPoint(root.TransformPoint(new Vector3(x-4,y-4,0)));
   var inputFrom=PixelAt(3,0);var inputTo=PixelAt(3,1);report.inputFromX=Mathf.RoundToInt(inputFrom.x);report.inputFromY=Screen.height-Mathf.RoundToInt(inputFrom.y);report.inputToX=Mathf.RoundToInt(inputTo.x);report.inputToY=Screen.height-Mathf.RoundToInt(inputTo.y);
   var point=PixelAt(large?3:column,large?1:rocket?0:2);report.width=Screen.width;report.height=Screen.height;report.targetX=Mathf.RoundToInt(point.x);report.targetY=Screen.height-Mathf.RoundToInt(point.y);report.status="READY_FOR_NATIVE_GESTURE";ready=true;Save();
  }
  void LateUpdate(){
   if(!ready||report.status!="READY_FOR_NATIVE_GESTURE")return;
   if(Time.realtimeSinceStartup>deadline){report.failures.Add("Input/settle timeout");Finish();return;}
   var step=Field<BoardStep>(game,"current");var motion=step?.motion.FirstOrDefault(m=>m.id==report.sourceId&&(large||m.fromX!=m.toX));
   if(motion!=null){float clock=Field<float>(game,"clock"),started=Field<float>(game,"started");var pose=Field<BoardPresentation>(game,"presentation").SampleLive(step,step.before,clock,started).FirstOrDefault(d=>d.pieceId==report.sourceId);
    report.fromX=(int)motion.fromX;report.fromY=(int)motion.fromY;report.toX=(int)motion.toX;report.toY=(int)motion.toY;report.seconds=motion.seconds;report.landing=motion.landing;
    if(pose!=null)report.poses.Add(new Pose{frame=Time.frameCount,age=clock-started-motion.delay,x=pose.x,y=pose.y,sx=pose.sx,sy=pose.sy});
    if(report.mode=="Slow"&&!report.forcedSlowFrame&&clock-started>=motion.delay&&clock-started<motion.delay+motion.seconds){report.forcedSlowAge=clock-started-motion.delay;report.forcedSlowFrame=true;System.Threading.Thread.Sleep(180);}
   }
   if(report.accepted&&!game.Busy){
    if(report.poses.Count(p=>p.age>0&&p.age<report.seconds)<4)report.failures.Add("Fewer than four visible flight poses");
    if(!report.poses.Any(p=>p.sy/p.sx>1.04f))report.failures.Add("No rendered flight stretch");
    if(!large&&(report.toX!=column||report.toY!=2||game.Model.At(column,2)?.id!=report.sourceId))report.failures.Add("Wrong refill source/destination");
    if(!large&&(game.Model.At(column,3)?.family!="stone"||game.Model.At(column,4)?.family!="stone"))report.failures.Add("Upper fixed obstacles changed position");
    if(game.Model.Moves!=(large?10:rocket||natural?19:20)||game.Model.Goals["stone"]!=2)report.failures.Add("Move cost or goals changed");
    if(JsonUtility.ToJson(game.Model.Snapshot())!=expected)report.failures.Add("Actual action differs from unchanged model solve");
    if(report.mode=="Slow"&&(!report.forcedSlowFrame||report.forcedSlowAge<0||report.forcedSlowAge>=report.seconds))report.failures.Add("Slow frame was not exercised");game.Model.Validate();Finish();
   }
  }
  void Log(string message,string trace,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert){report.failures.Add(message+"\n"+trace);Finish();}}
  void Save()=>File.WriteAllText(Path.Combine(Output,"Report.json"),JsonUtility.ToJson(report,true));
  void Finish(){report.status=report.failures.Count==0?"PASS_ACTUAL_OBSTACLE_FALL_INPUT":"FAIL_ACTUAL_OBSTACLE_FALL_INPUT";Application.logMessageReceived-=Log;Save();}
  void OnDestroy(){Application.logMessageReceived-=Log;}
 }
}
#endif

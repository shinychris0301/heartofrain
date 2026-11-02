#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.IO;
using System.Linq;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Profile;
using UnityEngine.SceneManagement;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 // Explicit transient fixtures. Real Android input, no save writes or grants.
 public sealed class GameplayAuditTouchProbe:MonoBehaviour {
  const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
  [Serializable] public class Pose {public string phase,key,sprite;public int frame,id;public float age,x,y,clock;}
  [Serializable] public class Report {public string utc,status="STARTING",mode,scope="Transient mixed-swap fixtures with actual Android swipe and native sprites; no persistent state writes. Recording is visual evidence, not a performance measurement.";public int fromX,fromY,toX,toY,recipe,sourcePower,movesBefore,createdId,createdKind,createdX,createdY,powerSteps;public bool accepted,chained,sourceActivated,protectedBirth,launchCleared;public List<Pose> poses=new List<Pose>();public List<string> failures=new List<string>();}
  GameplayScreen game;Report report;string expected;bool ready,begun,obstacle;float deadline,contactClock=-1;int recipe,source,movedGemId,originalPowerId;
  string Folder=>Path.Combine(Application.persistentDataPath,"GameplayAuditReview");
  static T Field<T>(object obj,string key)=>(T)obj.GetType().GetField(key,Flags).GetValue(obj);
  static string requestedMode;
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)] static void Boot(){string path=Path.Combine(Application.persistentDataPath,"HOTR_RunGameplayAudit");if(!File.Exists(path))return;requestedMode=File.ReadAllText(path).Trim();File.Delete(path);SceneManager.sceneLoaded+=Attach;}
  static void Attach(Scene scene,LoadSceneMode mode){var first=FindFirstObjectByType<FirstStartPage>();if(!first)return;SceneManager.sceneLoaded-=Attach;first.reviewAlways=true;var host=first.home.GetComponent<PlayerProfileHost>();if(!host)host=first.home.gameObject.AddComponent<PlayerProfileHost>();host.VerificationRepository=new MemoryProfileRepository(PlayerProfile.New(new[]{5,5,3,2}));host.VerificationAuthorityFactory=_=>new UnavailableGiftAuthority();host.VerificationLivesClock=()=>1000;var node=new GameObject("Opt-in gameplay audit");DontDestroyOnLoad(node);node.AddComponent<GameplayAuditTouchProbe>().report=new Report{utc=DateTime.UtcNow.ToString("o"),mode=requestedMode};requestedMode=null;}

  IEnumerator Start(){
   Application.logMessageReceived+=Log;Directory.CreateDirectory(Folder);deadline=Time.realtimeSinceStartup+90;
   while(!FindFirstObjectByType<FirstStartPage>()||!FindFirstObjectByType<FirstStartPage>().IsVisible)yield return null;
   while(FindFirstObjectByType<HeartOfTheRain.App.Launch.LaunchPage>())yield return null;report.launchCleared=true;
   var first=FindFirstObjectByType<FirstStartPage>();var ui=first.assets.Gameplay;first.Request("skip");first.Request("skip");first.home.SetPresentation(false,false);
   obstacle=report.mode.StartsWith("Obstacle");recipe=report.mode=="MixedV"?5:report.mode=="MixedBomb"?21:report.mode=="MixedOrb"?7:report.mode=="MixedSeeker"?11:4;
   source=recipe==5||recipe==21||report.mode=="MixedChain"?4:5;report.recipe=recipe;report.sourcePower=source;
   game=new GameObject("Audited mixed swap").AddComponent<GameplayScreen>();game.uiAssets=ui;game.initialLevel=1;game.showLevelIntro=false;game.ReviewInputBlocked=true;game.SharedToolInventory=new BoosterInventory();
   while(!game.InitializationComplete)yield return null;game.GetComponent<GameplayHUD>().ResultRequested=(won,number)=>true;
   var level=obstacle?GameplayAuditFixtures.Obstacle("stone",report.mode=="ObstaclePartial"?2:1):MixedPowerSwapFixtures.Match(recipe);var from=obstacle?new Cell(4,2):MixedPowerSwapFixtures.From(recipe);var to=obstacle?new Cell(4,3):MixedPowerSwapFixtures.To();var board=new BoardModel(level);var shadow=new BoardModel(level);if(!obstacle){board.InjectReviewPower(to.x,to.y,source);shadow.InjectReviewPower(to.x,to.y,source);}
   if(!obstacle)originalPowerId=board.At(to.x,to.y).id;var turn=shadow.Swap(from.x,from.y,to.x,to.y);expected=JsonUtility.ToJson(shadow.Snapshot());
   yield return Field<M46AtlasBank>(game,"bank").Prewarm(Field<M46AtlasBank>(game,"bank").RequiredResources(BoardPlayback.Build(turn.steps,level)));
   typeof(GameplayScreen).GetField("board",Flags).SetValue(game,board);typeof(GameplayScreen).GetField("idle",Flags).SetValue(game,board.Snapshot());report.movesBefore=board.Moves;movedGemId=obstacle?board.At(4,4).id:board.At(from.x,from.y).id;if(obstacle)report.createdId=movedGemId;
   game.PlayerActionCompleted+=action=>report.accepted=action.accepted;
   game.StepStarted+=step=>{if(obstacle&&step.damage.Any(d=>d.id==movedGemId)&&contactClock<0)contactClock=Field<float>(game,"clock");foreach(var piece in step.created)if(piece.id==movedGemId){report.createdId=piece.id;report.createdKind=piece.power;report.createdX=piece.x;report.createdY=piece.y;}if(step.kind=="power"||step.kind=="powerFall"){report.powerSteps++;var tracks=step.playbackTracks==null?new[]{step}:step.playbackTracks.Select(t=>t.step).Concat(new[]{step});if(tracks.Any(s=>s.removed.Any(p=>p.piece.id==movedGemId&&p.cause=="source")))report.chained=true;if(tracks.Any(s=>s.removed.Any(p=>p.piece.id==originalPowerId&&p.cause=="source")))report.sourceActivated=true;}};
   yield return null;yield return new WaitForEndOfFrame();var camera=Field<Camera>(game,"view");var root=Field<Transform>(game,"root");Vector3 Pixel(Cell cell)=>camera.WorldToScreenPoint(root.TransformPoint(new Vector3(cell.x-4,cell.y-4,0)));var a=Pixel(from);var b=Pixel(to);report.fromX=Mathf.RoundToInt(a.x);report.fromY=Screen.height-Mathf.RoundToInt(a.y);report.toX=Mathf.RoundToInt(b.x);report.toY=Screen.height-Mathf.RoundToInt(b.y);ready=true;report.status="READY_FOR_NATIVE_GESTURE";Save();
  }
  void LateUpdate(){if(!ready||report.status!="READY_FOR_NATIVE_GESTURE")return;if(Time.realtimeSinceStartup>deadline){report.failures.Add("Native swipe timeout");Finish();return;}if(!begun){string path=Path.Combine(Folder,"Begin");if(!File.Exists(path))return;File.Delete(path);game.ReviewInputBlocked=false;begun=true;return;}
   var view=Field<BoardPresentation>(game,"presentation");var current=Field<BoardStep>(game,"current");float clock=Field<float>(game,"clock");foreach(var d in view.SampleLive(current,Field<BoardSnapshot>(game,"idle"),clock,Field<float>(game,"started")))if((d.bank=="power"||obstacle)&&d.pieceId==report.createdId){var sprite=Field<M46AtlasBank>(game,"bank").Get(d);if(sprite)report.poses.Add(new Pose{phase=current==null?"idle":current.kind,key=d.key,sprite=sprite.name,frame=Time.frameCount,id=d.pieceId,age=d.age,x=d.x,y=d.y,clock=clock});}
   if(!report.accepted||game.Busy||obstacle&&clock-contactClock<1)return;
   if(!obstacle){int kind=recipe;if(report.createdKind!=kind||report.createdX!=4||report.createdY!=4)report.failures.Add("Missing or displaced initial match creation");if(!report.poses.Any(p=>p.key=="Create"||p.key.EndsWith("_Create")))report.failures.Add("Creation frames were not rendered");}else if(report.mode=="ObstaclePartial"&&!report.poses.Any(p=>p.key.StartsWith("stone/Stone_Hit")&&p.age>.3f))report.failures.Add("Hit clip ended at phase handoff");if(game.Model.Moves!=report.movesBefore-1)report.failures.Add("Incorrect move charge");if(JsonUtility.ToJson(game.Model.Snapshot())!=expected)report.failures.Add("Visual playback changed solved state");if(!obstacle){var birth=game.Model.Pieces.Values.FirstOrDefault(p=>p.id==movedGemId);report.protectedBirth=birth!=null&&birth.family=="power"&&birth.power==recipe&&!report.chained;if(!report.sourceActivated)report.failures.Add("Swapped source power did not activate");if(!report.protectedBirth)report.failures.Add("New reward was consumed by its originating power wave");}game.Model.Validate();Finish();
  }
  void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert){report.failures.Add(message+"\n"+stack);Finish();}}
  void Save()=>File.WriteAllText(Path.Combine(Folder,"Report.json"),JsonUtility.ToJson(report,true));
  void Finish(){report.status=report.failures.Count==0?"PASS_NATIVE_DEVICE_GAMEPLAY_AUDIT":"FAIL_NATIVE_DEVICE_GAMEPLAY_AUDIT";Application.logMessageReceived-=Log;Save();}
  void OnDestroy(){Application.logMessageReceived-=Log;}
 }
}
#endif

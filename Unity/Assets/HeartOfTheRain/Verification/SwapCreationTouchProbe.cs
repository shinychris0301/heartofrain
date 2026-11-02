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
namespace HeartOfTheRain.Verification
{
    // Explicit opt-in fixture for actual Android gestures. No save-store writes.
    public sealed class SwapCreationTouchProbe:MonoBehaviour
    {
        const string Marker="HOTR_RunSwapReview";
        const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        [Serializable] public class Sample {public string phase;public float age,x,y;public int frame,atlas;}
        [Serializable] public class Report {public string status="STARTING",utc,mode,scope="Actual app input on a transient authored-color fixture. Native rendered poses sampled without screenshot readbacks; not a physical-device/performance test.";public int expectedPower,sourceId,createdX=-1,createdY=-1,createdPower=-1,width,height,fromX,fromY,toX,toY;public bool accepted,oneMove;public List<Sample> samples=new List<Sample>();public List<string> failures=new List<string>();}
        GameplayScreen game;Report report;bool ready;float deadline;
        string Output=>Path.Combine(Application.persistentDataPath,"SwapReview");
        static T Field<T>(object o,string name)=>(T)o.GetType().GetField(name,Private).GetValue(o);
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)] static void Boot(){
            var path=Path.Combine(Application.persistentDataPath,Marker);if(!File.Exists(path))return;string mode=File.ReadAllText(path).Trim();File.Delete(path);
            foreach(var f in FindObjectsByType<FirstStartPage>(UnityEngine.FindObjectsSortMode.InstanceID))f.reviewAlways=true;
            new GameObject("Opt-in swap touch proof").AddComponent<SwapCreationTouchProbe>().report=new Report{utc=DateTime.UtcNow.ToString("o"),mode=mode};
        }
        IEnumerator Start(){
            Directory.CreateDirectory(Output);deadline=Time.realtimeSinceStartup+90;Application.logMessageReceived+=Log;
            while(!FindFirstObjectByType<FirstStartPage>()||!FindFirstObjectByType<FirstStartPage>().IsVisible)yield return null;
            var f=FindFirstObjectByType<FirstStartPage>();var ui=f.assets.Gameplay;f.Request("skip");f.Request("skip");f.home.SetPresentation(false,false);
            game=new GameObject("Native swap touch board").AddComponent<GameplayScreen>();game.uiAssets=ui;game.showLevelIntro=false;while(!game.InitializationComplete)yield return null;
            game.GetComponent<GameplayHUD>().ResultRequested=(won,level)=>true;
            bool vertical=report.mode.StartsWith("V"),reverse=report.mode.EndsWith("Reverse");var levelData=SwapCreationFixtures.Rocket(vertical,reverse);var from=SwapCreationFixtures.From(vertical,reverse);var to=SwapCreationFixtures.To();
            var shadow=new BoardModel(levelData);var turn=shadow.Swap(from.x,from.y,to.x,to.y);var bank=Field<M46AtlasBank>(game,"bank");yield return bank.Prewarm(bank.RequiredResources(BoardPlayback.Build(turn.steps,levelData)));
            var board=new BoardModel(levelData);typeof(GameplayScreen).GetField("board",Private).SetValue(game,board);typeof(GameplayScreen).GetField("idle",Private).SetValue(game,board.Snapshot());report.sourceId=board.At(from.x,from.y).id;report.expectedPower=vertical?5:4;
            game.PlayerActionCompleted+=a=>{if(a.kind=="swap")report.accepted=a.accepted;};
            game.StepStarted+=s=>{if(s.kind!="match"||report.createdPower>=0)return;var p=s.created.FirstOrDefault(c=>c.id==report.sourceId);if(p!=null){report.createdX=p.x;report.createdY=p.y;report.createdPower=p.power;}};
            yield return null;yield return new WaitForEndOfFrame();
            var camera=Field<Camera>(game,"view");var root=Field<Transform>(game,"root");Vector3 PixelAt(Cell cell)=>camera.WorldToScreenPoint(root.TransformPoint(new Vector3(cell.x-4,cell.y-4,0)));
            var pixelFrom=PixelAt(from);var pixelTo=PixelAt(to);report.width=Screen.width;report.height=Screen.height;report.fromX=Mathf.RoundToInt(pixelFrom.x);report.fromY=Screen.height-Mathf.RoundToInt(pixelFrom.y);report.toX=Mathf.RoundToInt(pixelTo.x);report.toY=Screen.height-Mathf.RoundToInt(pixelTo.y);report.status="READY_FOR_NATIVE_GESTURE";ready=true;Save();
        }
        void LateUpdate(){
            if(report==null||!ready||report.status!="READY_FOR_NATIVE_GESTURE")return;
            if(Time.realtimeSinceStartup>deadline){report.failures.Add("Gesture/settle timeout");Finish();return;}
            var step=Field<BoardStep>(game,"current");
            if(step!=null&&(step.kind=="swap"||step.kind=="match"&&step.created.Any(p=>p.id==report.sourceId))){
                float clock=Field<float>(game,"clock"),started=Field<float>(game,"started");var pose=Field<BoardPresentation>(game,"presentation").SampleLive(step,step.before,clock,started).FirstOrDefault(d=>d.pieceId==report.sourceId);
                if(pose!=null)report.samples.Add(new Sample{phase=step.kind,age=clock-started,x=pose.x,y=pose.y,atlas=pose.atlas,frame=Time.frameCount});
            }
            if(report.accepted&&!game.Busy){
                report.oneMove=game.Model.Moves==19&&game.Model.Turn==1;
                if(!report.oneMove)report.failures.Add("Move/turn charge differs");
                if(report.createdX!=4||report.createdY!=4||report.createdPower!=report.expectedPower)report.failures.Add("Creation endpoint/orientation differs");
                if(!report.samples.Any(s=>s.phase=="swap"&&(Math.Abs(s.x-Mathf.Round(s.x))>.02f||Math.Abs(s.y-Mathf.Round(s.y))>.02f)))report.failures.Add("No rendered fractional swap pose");
                if(!report.samples.Any(s=>s.phase=="match"&&s.x==4&&s.y==4&&s.atlas==(report.expectedPower==4?9:10)))report.failures.Add("No rendered newborn rocket at destination");
                game.Model.Validate();Finish();
            }
        }
        void Log(string text,string trace,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert){report.failures.Add(text);Finish();}}
        void Save()=>File.WriteAllText(Path.Combine(Output,"Report.json"),JsonUtility.ToJson(report,true));
        void Finish(){report.status=report.failures.Count==0?"PASS_ACTUAL_SWAP_CREATION_INPUT":"FAIL_ACTUAL_SWAP_CREATION_INPUT";Application.logMessageReceived-=Log;Save();}
        void OnDestroy(){Application.logMessageReceived-=Log;}
    }
}
#endif

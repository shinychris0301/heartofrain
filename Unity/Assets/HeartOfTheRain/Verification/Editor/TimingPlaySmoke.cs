#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.M48;
namespace HeartOfTheRain.Verification
{
    [InitializeOnLoad] public static class TimingPlaySmoke
    {
        const string Key="HOTR.TimingSmoke";static GameplayScreen game;static int phase,moves,accepted,settled;static double at;static float pausedClock;static Cell[] move;
        static readonly List<string> checks=new List<string>();static readonly BindingFlags Private=BindingFlags.NonPublic|BindingFlags.Instance;
        [Serializable] class Report {public string status,utc,scope="Native Editor Play Mode rejection animation, pause and validated single-gesture buffering. Decorative-tail fixtures are synthetic; real Android input/rendering evidence is separate.";public string[] checks;public string error;}
        static TimingPlaySmoke(){if(SessionState.GetBool(Key,false)){EditorApplication.update+=Tick;Application.logMessageReceived+=Log;}}
        static void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)Finish(text+"\n"+stack);}
        public static void Run(){SessionState.SetBool(Key,true);SessionState.SetFloat(Key+".start",(float)EditorApplication.timeSinceStartup);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");UnityEngine.Object.FindFirstObjectByType<FirstStartPage>().reviewAlways=true;EditorApplication.isPlaying=true;}
        static T Field<T>(string name)=>(T)typeof(GameplayScreen).GetField(name,Private).GetValue(game);
        static void Invoke(string name,params object[] args)=>typeof(GameplayScreen).GetMethod(name,Private).Invoke(game,args);
        static void Check(bool ok,string label){if(!ok)throw new Exception(label);checks.Add(label);}
        static void Next(){phase++;at=EditorApplication.timeSinceStartup;}
        static void Tail(){var s=game.Model.Snapshot();Invoke("Enqueue",new List<BoardStep>{new BoardStep{kind="powerFall",duration=1,before=s,after=s,playbackTracks=new List<PlaybackTrack>()}});}
        static void BufferMove(){move=game.Model.LegalSwaps().First();Invoke("PlayerSwap",move[0].x,move[0].y,move[1].x,move[1].y);}
        static void Tick(){try{
            if(EditorApplication.timeSinceStartup-SessionState.GetFloat(Key+".start",0)>120)throw new TimeoutException("Timing smoke phase "+phase);
            if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
            double elapsed=EditorApplication.timeSinceStartup-at;
            switch(phase){
                case 0:var first=UnityEngine.Object.FindFirstObjectByType<FirstStartPage>();if(!first||!first.IsVisible)return;var ui=first.assets.Gameplay;first.Request("skip");first.Request("skip");first.home.SetPresentation(false,false);game=new GameObject("Native timing input smoke").AddComponent<GameplayScreen>();game.uiAssets=ui;game.showLevelIntro=false;Next();break;
                case 1:if(!game.CanAct)return;game.GetComponent<GameplayHUD>().ResultRequested=(won,level)=>true;game.PlayerActionCompleted+=a=>{if(a.accepted)accepted++;};game.TurnSettled+=s=>settled++;moves=game.Model.Moves;
                    var legal=game.Model.LegalSwaps();Cell[] invalid=null;foreach(var a in game.Model.Pieces.Values.Where(p=>p.family=="gem")){var b=game.Model.At(a.x+1,a.y);if(b==null||b.family!="gem")continue;if(!legal.Any(p=>p[0].x==a.x&&p[0].y==a.y&&p[1].x==b.x&&p[1].y==b.y)){invalid=new[]{new Cell(a.x,a.y),new Cell(b.x,b.y)};break;}}
                    Check(invalid!=null,"Found an authored invalid adjacent swap");game.playbackSpeed=.1f;Invoke("PlayerSwap",invalid[0].x,invalid[0].y,invalid[1].x,invalid[1].y);Check(Field<BoardStep>("current")?.kind=="reject","Invalid swap starts native return animation");Check(game.Model.Moves==moves&&game.Model.Turn==0,"Rejection spends no move or turn");Next();break;
                case 2:if(elapsed<.4)return;game.SetPause(true);pausedClock=Field<float>("clock");Check(game.Busy&&Field<BoardStep>("current").kind=="reject","Rejection remains a presentation step");Next();break;
                case 3:if(elapsed<.25)return;Check(Math.Abs(Field<float>("clock")-pausedClock)<.001f,"Pause freezes rejection playback");game.playbackSpeed=1;game.SetPause(false);Next();break;
                case 4:if(game.Busy)return;Check(settled==0&&accepted==0&&game.Model.Moves==moves,"Rejected animation emits no accepted action or turn settlement");Tail();Check((bool)typeof(GameplayScreen).GetProperty("CanBuffer",Private).GetValue(game),"Stable decorative tail accepts a buffer");BufferMove();Check(Field<BoardGestureBuffer>("pendingGesture").HasPending&&game.Model.Moves==moves,"Queued gesture leaves the model untouched until ready");Next();break;
                case 5:if(game.Busy)return;Check(accepted==1&&game.Model.Moves==moves-1,"Queued gesture executes and charges exactly once");Invoke("ConsumeBufferedGesture");Check(accepted==1&&!Field<BoardGestureBuffer>("pendingGesture").HasPending,"Repeated consume cannot duplicate the gesture");Tail();BufferMove();game.SetPause(true);Check(!Field<BoardGestureBuffer>("pendingGesture").HasPending,"Pause clears queued input");game.SetPause(false);game.Load(0);Next();break;
                case 6:if(!game.CanAct)return;Tail();BufferMove();game.Load(0);Check(!Field<BoardGestureBuffer>("pendingGesture").HasPending,"Level reload clears queued input");Next();break;
                case 7:if(!game.CanAct)return;Check(game.Model.Moves==moves&&accepted==1,"Reload cannot replay an old intent");Tail();BufferMove();game.ReviewInputBlocked=true;Invoke("ConsumeBufferedGesture");Check(!Field<BoardGestureBuffer>("pendingGesture").HasPending,"Modal/review ownership cancels queued input");game.ReviewInputBlocked=false;Finish(null);break;
            }
        }catch(Exception e){Finish(e.ToString());}}
        static void Finish(string error){SessionState.EraseBool(Key);EditorApplication.update-=Tick;Application.logMessageReceived-=Log;string dir=Path.GetFullPath("../Verification/Evidence/Timing");Directory.CreateDirectory(dir);File.WriteAllText(Path.Combine(dir,"Play_Smoke.json"),JsonUtility.ToJson(new Report{status=error==null?"PASS_NATIVE_TIMING_PLAY_SMOKE":"FAIL_NATIVE_TIMING_PLAY_SMOKE",utc=DateTime.UtcNow.ToString("o"),checks=checks.ToArray(),error=error},true));EditorApplication.Exit(error==null?0:1);}
    }
}
#endif

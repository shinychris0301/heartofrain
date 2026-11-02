#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
    // Native Play Mode, real model/renderer, deterministic onset budgets.
    // Deliberate stalls are controls, never performance measurements.
    [InitializeOnLoad] public static class PlaybackOnsetVerification {
        const string Key="HOTR.PlaybackOnset.Native";
        static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static readonly string[] Cases={"swap_stall_before_accept","swap_stall_after_accept","rejected_swap","power_tap","hammer","resource_wait","scaled_pause_continuity","reload"};
        [Serializable] public sealed class Row {public string name;public float duration,firstAge,contactBudget;public int movingPoses;public bool modelPreserved;}
        [Serializable] public sealed class Report {public string status,utc,unity,scope="Native Unity Play Mode with actual BoardModel, GameplayScreen and SpriteRenderers. Two deliberate200ms controls and injected frame-clock budgets verify first-pose ownership, full scheduled swap duration, resource waits, pause/scaling and ongoing clocks. GPU board captures are untimed; no Android, touch-latency or FPS claim.";public int checks;public List<Row> cases=new List<Row>();public List<string> failures=new List<string>();}
        static Report report;static GameplayScreen game;static bool launched,caseStarted;static int index;static double deadline;static string output;static float originalTimeScale;
        static PlaybackOnsetVerification(){if(SessionState.GetBool(Key,false))EditorApplication.update+=Tick;}
        public static void Run(){SessionState.SetBool(Key,true);EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorApplication.update-=Tick;EditorApplication.update+=Tick;EditorApplication.isPlaying=true;}
        static T Field<T>(string name)=>(T)typeof(GameplayScreen).GetField(name,Private).GetValue(game);
        static void Set(string name,object value)=>typeof(GameplayScreen).GetField(name,Private).SetValue(game,value);
        static object Invoke(string name,params object[] args)=>typeof(GameplayScreen).GetMethod(name,Private).Invoke(game,args);
        static void Check(bool ok,string name){report.checks++;if(!ok)throw new InvalidOperationException(name);}
        static float Age=>Field<float>("clock")-Field<float>("started");
        static void Log(string message,string trace,LogType type){if(type==LogType.Error||type==LogType.Assert||type==LogType.Exception)Finish(message+"\n"+trace);}
        static void Tick(){try{
            if(!EditorApplication.isPlaying||EditorApplication.isCompiling)return;
            if(!launched){launched=true;report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};output=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY72_OUTPUT");if(string.IsNullOrEmpty(output))output="../Verification/Evidence/Gameplay72";output=Path.GetFullPath(output);Directory.CreateDirectory(output);originalTimeScale=Time.timeScale;Time.timeScale=1;Application.logMessageReceived+=Log;deadline=EditorApplication.timeSinceStartup+180;
                game=new GameObject("Native playback onset review").AddComponent<GameplayScreen>();game.uiAssets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");game.showLevelIntro=false;return;}
            if(EditorApplication.timeSinceStartup>deadline)throw new TimeoutException("Onset case "+Cases[index]);
            if(!caseStarted){if(!game.CanAct)return;game.enabled=false;BeginCase(Cases[index]);caseStarted=true;}
            // Actual texture preparation may yield. No game Update/Render runs
            // while disabled, so readiness alone must never consume onset time.
            if(Field<BoardStep>("current")==null)return;
            Exercise(Cases[index]);index++;caseStarted=false;
            if(index==Cases.Length){Finish(null);return;}game.Load(0);deadline=EditorApplication.timeSinceStartup+90;
        }catch(Exception e){Finish(e.ToString());}}
        static void BeginCase(string name){
            var board=game.Model;
            if(name=="rejected_swap"){
                var legal=board.LegalSwaps();Piece a=null,b=null;
                foreach(var p in board.Pieces.Values.Where(p=>p.family=="gem"))foreach(var d in new[]{new Cell(1,0),new Cell(0,1)}){
                    var q=board.At(p.x+d.x,p.y+d.y);if(q==null||q.family!="gem"||legal.Any(m=>m[0].x==p.x&&m[0].y==p.y&&m[1].x==q.x&&m[1].y==q.y))continue;a=p;b=q;break;
                }
                Check(a!=null&&b!=null,"Rejected gesture control exists");int moves=board.Moves;Invoke("PlayerSwap",a.x,a.y,b.x,b.y);Check(board.Moves==moves,"Rejected swap spends no move");
            }else if(name=="power_tap"){
                var p=board.Pieces.Values.First(p=>p.family=="gem");Check(board.InjectReviewPower(p.x,p.y,4),"Install explicit tap fixture");Invoke("PlayerTap",p.x,p.y);
            }else if(name=="hammer"){
                var p=board.Pieces.Values.First(p=>p.family=="gem");game.UseBooster(BoosterKind.Hammer,p.x,p.y);
            }else{
                if(name=="swap_stall_before_accept")Thread.Sleep(200);
                var m=board.LegalSwaps().First();var turn=board.Swap(m[0].x,m[0].y,m[1].x,m[1].y);Check(turn.accepted,"Accepted swap fixture "+name);Invoke("Accept",turn);
                if(name=="swap_stall_after_accept")Thread.Sleep(200);
            }
            Check(Field<bool>("awaitingPlaybackPose")&&!Field<bool>("playbackPoseAnchor"),name+": enqueued command waits for a rendered pose");
            if(Field<BoardStep>("current")==null){Invoke("Render");Check(Field<bool>("awaitingPlaybackPose")&&!Field<bool>("playbackPoseAnchor"),name+": resource preparation is not a first pose");}
        }
        static void Pose(BoardStep step,string name){
            var view=Field<BoardPresentation>("presentation");var draws=view.SampleLive(step,Field<BoardSnapshot>("idle"),Field<float>("clock"),Field<float>("started"));
            var motion=step.motion.FirstOrDefault();if(motion==null)return;
            var body=draws.FirstOrDefault(d=>d.pieceId==motion.id);Check(body!=null,name+": moving body was sampled");
            if(Age==0)Check(Math.Abs(body.x-motion.fromX)<.00001f&&Math.Abs(body.y-motion.fromY)<.00001f,name+": first moving body stays at its source cell");
            var bank=Field<M46AtlasBank>("bank");var sprite=bank.Get(body);var point=(Vector3)Invoke("Position",body.x,body.y);var pool=Field<List<SpriteRenderer>>("pool");
            Check(pool.Any(sr=>sr.enabled&&sr.sprite==sprite&&(sr.transform.localPosition-point).sqrMagnitude<.000001f),name+": actual SpriteRenderer matches the sampled moving body");
        }
        static void Capture(string name){
            var camera=Field<Camera>("view");var old=camera.targetTexture;var active=RenderTexture.active;var target=new RenderTexture(720,1280,24);Texture2D image=null;
            try{camera.targetTexture=target;camera.Render();RenderTexture.active=target;image=new Texture2D(720,1280,TextureFormat.RGBA32,false);image.ReadPixels(new Rect(0,0,720,1280),0,0);image.Apply();File.WriteAllBytes(Path.Combine(output,name+".png"),image.EncodeToPNG());}
            finally{camera.targetTexture=old;RenderTexture.active=active;if(image)UnityEngine.Object.Destroy(image);UnityEngine.Object.Destroy(target);}
        }
        static void Exercise(string name){
            var step=Field<BoardStep>("current");string solved=JsonUtility.ToJson(game.Model.Snapshot());var row=new Row{name=name,duration=step.duration};
            if(name=="resource_wait"){
                Set("current",null);Invoke("Render");Check(Field<bool>("awaitingPlaybackPose")&&!Field<bool>("playbackPoseAnchor"),"An idle render while resources wait cannot anchor playback");Set("current",step);
            }
            float before=Field<float>("clock");Invoke("AdvancePlayback",.2f);Check(Field<float>("clock")==before&&Age==0,name+": pre-render200ms frame debt advances no animation");
            Invoke("Render");row.firstAge=Age;Check(Age==0&&!Field<bool>("awaitingPlaybackPose")&&Field<bool>("playbackPoseAnchor"),name+": first actual render anchors age zero");Pose(step,name);
            // A controlled16ms after the first pose must consume16ms, not the
            // legacy40ms swap fence from a200ms pre-presentation frame.
            Set("playbackPoseAt",100.0);float allowed=(float)Invoke("PlaybackOnsetAdvance",.2f,100.016,1f);Check(Math.Abs(allowed-.016f)<.00001f,name+": only post-pose16ms is charged");
            Check(!Field<bool>("playbackPoseAnchor"),name+": onset allowance is consumed once");
            if(step.kind=="swap"){
                Check(Math.Abs(step.duration-.12f)<.000001f,name+": scheduled swap remains120ms");int poses=1;
                if(name.StartsWith("swap_stall_",StringComparison.Ordinal))Capture(name+"_FirstPose");
                for(int n=0;n<7;n++){Invoke("AdvancePlayback",.016f);Invoke("Render");Check(ReferenceEquals(Field<BoardStep>("current"),step),name+": swap remains active before contact "+n);Check(Math.Abs(Age-.016f*(n+1))<.00002f,name+": visible playback clock "+n);Pose(step,name);poses++;if(n==3&&name.StartsWith("swap_stall_",StringComparison.Ordinal))Capture(name+"_MovingPose");}
                Invoke("AdvancePlayback",.007f);Invoke("Render");Check(ReferenceEquals(Field<BoardStep>("current"),step)&&Math.Abs(Age-.119f)<.00002f,name+": full119ms is visible before swap contact");
                if(name.StartsWith("swap_stall_",StringComparison.Ordinal))Capture(name+"_BeforeContact");
                Invoke("AdvancePlayback",.002f);Check(!ReferenceEquals(Field<BoardStep>("current"),step),name+": contact occurs at scheduled120ms");Check(!Field<bool>("awaitingPlaybackPose")&&!Field<bool>("playbackPoseAnchor"),name+": phase transition does not re-anchor cascade time");row.contactBudget=.121f;row.movingPoses=poses;
            }else{Invoke("AdvancePlayback",allowed);Check(Math.Abs(Age-.016f)<.00002f,name+": non-swap command retains its first visible interval");}
            if(name=="scaled_pause_continuity"){
                foreach(float timeScale in new[]{0f,.25f,1f})foreach(float speed in new[]{0f,.5f,2f}){Set("playbackPoseAnchor",true);Set("playbackPoseAt",100.0);float scale=timeScale*speed;float budget=(float)Invoke("PlaybackOnsetAdvance",.2f*scale,100.016,scale);Check(Math.Abs(budget-.016f*scale)<.00001f,"Onset preserves timeScale/playbackSpeed "+timeScale+"/"+speed);}
                Set("playbackPoseAnchor",true);Set("playbackPoseAt",100.0);float clock=Field<float>("clock");game.SetPause(true);Invoke("Update");Check(Field<float>("clock")==clock&&Field<bool>("playbackPoseAnchor"),"Pause neither advances nor consumes the anchor");game.SetPause(false);
                float resumed=(float)Invoke("PlaybackOnsetAdvance",.016f,110.0,1f);Check(Math.Abs(resumed-.016f)<.00001f,"Long pause cannot create resumed frame debt");
                Check(Math.Abs((float)Invoke("PlaybackOnsetAdvance",.08f,111.0,1f)-.08f)<.00001f,"Following gravity/cascade intervals are not capped by onset");
            }
            Check(JsonUtility.ToJson(game.Model.Snapshot())==solved,name+": native playback preserves solved model");row.modelPreserved=true;report.cases.Add(row);
            if(name=="reload"){Set("awaitingPlaybackPose",true);Set("playbackPoseAnchor",true);game.Load(0);Check(!Field<bool>("awaitingPlaybackPose")&&!Field<bool>("playbackPoseAnchor")&&game.Model.Turn==0,"Reload resets pending pose and clock ownership");}
        }
        static void Finish(string error){if(report==null||report.status!=null)return;report.status=error==null?"PASS_NATIVE_PLAYBACK_ONSET":"FAIL_NATIVE_PLAYBACK_ONSET";if(error!=null)report.failures.Add(error);Time.timeScale=originalTimeScale;Application.logMessageReceived-=Log;EditorApplication.update-=Tick;SessionState.EraseBool(Key);File.WriteAllText(Path.Combine(output,"PlaybackOnset.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(error==null?0:1);}
    }
}
#endif

#if UNITY_EDITOR
using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.Celebrations;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Home;
namespace HeartOfTheRain.Verification
{
    [InitializeOnLoad] public static class M68PlaybackSmoke
    {
        const string Key="HOTR.M68Smoke";static int phase,callbacks;static double at;static HomePage home;static VictoryCelebrationPlayer player;static float pausedAt;static readonly System.Collections.Generic.List<string> checks=new System.Collections.Generic.List<string>();
        static HeartOfTheRain.M46.M46AtlasBank sharedBank;static string sharedPath;static int warmers;
        [Serializable] class Report {public string status,utc,scope="Native Editor Play Mode M68 pause/skip/reduced-motion and callback lifecycle. Device/UI regression is separate.";public string[] checks;public string error;}
        static M68PlaybackSmoke(){if(SessionState.GetBool(Key,false)){EditorApplication.update+=Tick;Application.logMessageReceived+=Log;}}
        static void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)Finish(text+"\n"+stack);}
        static System.Collections.IEnumerator Warm(){yield return sharedBank.Prewarm(new[]{sharedPath});warmers++;}
        public static void Run(){SessionState.SetBool(Key,true);SessionState.SetFloat(Key+".start",(float)EditorApplication.timeSinceStartup);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");UnityEngine.Object.FindFirstObjectByType<FirstStartPage>().reviewAlways=true;EditorApplication.isPlaying=true;}
        static void Check(bool ok,string text){if(!ok)throw new Exception(text);checks.Add(text);}
        static VictoryPlaybackSession Clock=>(VictoryPlaybackSession)typeof(VictoryCelebrationPlayer).GetField("clock",BindingFlags.NonPublic|BindingFlags.Instance).GetValue(player);
        static void Pause(bool value)=>typeof(VictoryCelebrationPlayer).GetMethod("OnApplicationPause",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(player,new object[]{value});
        static void Next(){phase++;at=EditorApplication.timeSinceStartup;}
        static void Tick(){try{
            if(EditorApplication.timeSinceStartup-SessionState.GetFloat(Key+".start",0)>90)throw new TimeoutException("M68 smoke phase "+phase);
            if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
            double elapsed=EditorApplication.timeSinceStartup-at;
            switch(phase){
                case 0:var first=UnityEngine.Object.FindFirstObjectByType<FirstStartPage>();if(!first||!first.IsVisible)return;home=first.home;sharedBank=new HeartOfTheRain.M46.M46AtlasBank(first.assets.Gameplay.boards);sharedPath=first.assets.Gameplay.boards.powerResources[2];first.Request("skip");first.Request("skip");home.StartCoroutine(Warm());home.StartCoroutine(Warm());Next();break;
                case 1:if(elapsed<.4||warmers<2)return;Check(sharedBank.LoadError==null,"Foreground and prefetch coroutines share one async texture request");sharedBank.Dispose();sharedBank=null;Check(VictoryCelebrationPlayer.TryPlay(home,1,()=>callbacks++),"M68 starts");player=home.GetComponent<VictoryCelebrationPlayer>();Next();break;
                case 2:if(elapsed<.8)return;Check(UnityEngine.Object.FindFirstObjectByType<M68MeshGraphic>().GetComponent<CanvasRenderer>(),"M68 mesh has native CanvasRenderer");Pause(true);pausedAt=Clock.Elapsed;Next();break;
                case 3:if(elapsed<.35)return;Check(Mathf.Abs(Clock.Elapsed-pausedAt)<.001f,"Suspension does not consume animation time");Pause(false);player.Skip();Check(player.IsVisible,"Skip starts a fade rather than cutting immediately");Next();break;
                case 4:if(elapsed<.30)return;Check(!player.IsVisible&&callbacks==1,"Skip finishes exactly once");player.Finish();Check(callbacks==1,"Repeated finish cannot invoke completion twice");home.State.reduceMotion=true;Check(VictoryCelebrationPlayer.TryPlay(home,1,()=>callbacks++),"Reduced motion starts");Next();break;
                case 5:if(elapsed<.45)return;var still=Array.Find(home.GetComponentsInChildren<RawImage>(),v=>v.name=="M68 reduced motion");Check(still&&still.enabled,"Reduced motion uses supplied still");Check(!home.GetComponentInChildren<M68MeshGraphic>().enabled,"Reduced motion disables mesh movement");foreach(var raw in home.GetComponentsInChildren<RawImage>())if(raw.name.StartsWith("M68 particle"))Check(!raw.enabled,"Reduced motion omits "+raw.name);Next();break;
                case 6:if(player.IsVisible)return;Check(callbacks==2,"Reduced motion completes once");home.State.reduceMotion=false;Finish(null);break;
            }
        }catch(Exception e){Finish(e.ToString());}}
        static void Finish(string error){SessionState.EraseBool(Key);EditorApplication.update-=Tick;Application.logMessageReceived-=Log;if(sharedBank!=null){sharedBank.Dispose();sharedBank=null;}string dir=Path.GetFullPath("../Verification/Evidence/Fluidity");Directory.CreateDirectory(dir);File.WriteAllText(Path.Combine(dir,"M68_Play_Smoke.json"),JsonUtility.ToJson(new Report{status=error==null?"PASS_NATIVE_M68_PLAY_SMOKE":"FAIL_NATIVE_M68_PLAY_SMOKE",utc=DateTime.UtcNow.ToString("o"),checks=checks.ToArray(),error=error},true));EditorApplication.Exit(error==null?0:1);}
    }
}
#endif

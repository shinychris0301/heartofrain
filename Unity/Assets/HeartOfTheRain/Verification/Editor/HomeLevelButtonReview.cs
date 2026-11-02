#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.Localization;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification
{
    [InitializeOnLoad] public static class HomeLevelButtonReview
    {
        const string Key="HOTR.HomeLevelButton";
        static readonly Vector2Int[] Sizes={new Vector2Int(720,1280),new Vector2Int(900,2000),new Vector2Int(1200,1600)};
        static int index,originalLocale;static double started,readyAt;static Report report;
        [Serializable] sealed class Frame {public string file,label,language;public int level,width,height,fontSize;public bool preLevelOpened;}
        [Serializable] sealed class Report {public string utc,unity,status,error,scope="Native Unity Play Mode Home renders and programmatic button dispatch with review-memory campaign/appearance. Not device screenshots, touch or FPS verification.";public List<Frame> frames=new List<Frame>();}
        static string Output=>Path.GetFullPath("../Verification/Evidence/HomeLevelButton");
        static HomeLevelButtonReview(){if(SessionState.GetBool(Key,false)){started=readyAt=EditorApplication.timeSinceStartup;report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};originalLocale=GameLocale.Current;EditorApplication.update+=Tick;Application.logMessageReceived+=Log;}}
        public static void Run()
        {
            SessionState.SetBool(Key,true);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");UnityEngine.Object.FindFirstObjectByType<FirstStartPage>().reviewAlways=true;
            // Reuse the established native viewport helper; restore its sizes on completion.
            typeof(ChapterBackgroundReview).GetMethod("SetupSizes",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);
            EditorApplication.isPlaying=true;
        }
        static void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.error=message+"\n"+stack;}
        static void Tick()
        {
            try
            {
                if(EditorApplication.timeSinceStartup-started>180)throw new TimeoutException("Home label review timed out");
                if(!string.IsNullOrEmpty(report.error))throw new InvalidOperationException(report.error);
                if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating||EditorApplication.timeSinceStartup-readyAt<1)return;
                var home=UnityEngine.Object.FindFirstObjectByType<HomePage>();if(!home||!home.GetComponent<PlayerProfileHost>()||!home.GetComponent<PlayerProfileHost>().Ready)return;
                var first=home.GetComponent<FirstStartPage>();if(first.IsVisible){first.Request("skip");first.Request("skip");}
                if(!home.PresentationInteractable)throw new InvalidOperationException("Home is not interactive");
                int size=index<6?0:index-5;int level=index==0?12:50;int language=index<2?0:Math.Min(4,index-1);
                // The existing helper uses these three requested dimensions.
                var expected=Sizes[size];
                if(Screen.width!=expected.x||Screen.height!=expected.y){readyAt=EditorApplication.timeSinceStartup;return;}
                if(!home.GetComponent<PlayerProfileHost>().IsTransient)throw new InvalidOperationException("An isolated campaign is required");
                GameLocale.Select(language);home.State.currentLevel=level;home.State.completedLevelsInChapter=level-1;home.ApplyState(home.State);
                Directory.CreateDirectory(Output);string file=$"Home_L{level}_{GameLocale.Codes[language]}_{Screen.width}x{Screen.height}.png";
                Capture(home,Path.Combine(Output,file));
                var label=home.GetComponentsInChildren<Text>().Single(t=>t.name=="start-label");string expectedLabel=GameLocale.Format("Level {0}",level);
                if(label.text!=expectedLabel||home.GetComponentsInChildren<Text>().Any(t=>t.name=="start-number"))throw new InvalidOperationException("Home label differs from the supplied update");
                if(label.preferredWidth>label.rectTransform.rect.width+.5f||label.preferredHeight>label.rectTransform.rect.height+.5f)throw new InvalidOperationException("Home label does not fit");
                var button=home.GetComponentsInChildren<HomeControlLabel>().Single(c=>c.action=="prelevel");if(button.label!=expectedLabel)throw new InvalidOperationException("Accessible label is stale");
                bool opened=false;if(index<2){button.GetComponent<Button>().onClick.Invoke();var modal=home.GetComponent<PreLevelModal>();opened=modal&&modal.IsVisible;if(!opened||home.LastRequestedAction!="prelevel:"+level)throw new InvalidOperationException("Actual pre-level routing failed");modal.Requested("close");}
                report.frames.Add(new Frame{file=file,label=label.text,language=GameLocale.Codes[language],level=level,width=Screen.width,height=Screen.height,fontSize=label.fontSize,preLevelOpened=opened});
                index++;if(index==8){Finish(0);return;}
                int next=index<6?0:index-5;if(next!=size){var view=EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(view,SessionState.GetInt("HOTR.ChapterBackgroundReview.first",0)+next);view.Repaint();}
                readyAt=EditorApplication.timeSinceStartup;
            }
            catch(Exception e){report.error=e.ToString();Finish(1);}
        }
        static void Capture(HomePage home,string path)
        {
            var canvases=UnityEngine.Object.FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID).Where(c=>c.isActiveAndEnabled&&c.renderMode==RenderMode.ScreenSpaceOverlay).ToArray();var cameras=canvases.Select(c=>c.worldCamera).ToArray();var distances=canvases.Select(c=>c.planeDistance).ToArray();
            var go=new GameObject("Home label capture camera");go.transform.position=new Vector3(-10000,0,-10);var camera=go.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;
            var previous=RenderTexture.active;var target=RenderTexture.GetTemporary(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);Texture2D pixels=null;
            try{camera.targetTexture=target;foreach(var c in canvases){c.renderMode=RenderMode.ScreenSpaceCamera;c.worldCamera=camera;c.planeDistance=1;}Canvas.ForceUpdateCanvases();camera.Render();home.SetChapterBackground(null);Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;pixels=new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0);pixels.Apply();File.WriteAllBytes(path,pixels.EncodeToPNG());}
            finally{for(int n=0;n<canvases.Length;n++){canvases[n].renderMode=RenderMode.ScreenSpaceOverlay;canvases[n].worldCamera=cameras[n];canvases[n].planeDistance=distances[n];}RenderTexture.active=previous;RenderTexture.ReleaseTemporary(target);if(pixels)UnityEngine.Object.Destroy(pixels);UnityEngine.Object.Destroy(go);Canvas.ForceUpdateCanvases();}
        }
        static void Finish(int code)
        {
            report.status=code==0?"PASS_NATIVE_HOME_LEVEL_BUTTON":"FAIL_NATIVE_HOME_LEVEL_BUTTON";Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"Native_Review.json"),JsonUtility.ToJson(report,true));GameLocale.Select(originalLocale);
            EditorApplication.update-=Tick;Application.logMessageReceived-=Log;SessionState.EraseBool(Key);
            var view=EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(view,SessionState.GetInt("HOTR.ChapterBackgroundReview.previous",0));var group=typeof(ChapterBackgroundReview).GetMethod("Group",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);
            for(int n=2;n>=0;n--)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{SessionState.GetInt("HOTR.ChapterBackgroundReview.first",0)+n});EditorApplication.Exit(code);
        }
    }
}
#endif

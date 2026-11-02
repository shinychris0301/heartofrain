#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification
{
    [InitializeOnLoad]
    public static class RewardedHome135Capture
    {
        const string Key="HOTR.RewardedHome135Capture";
        static readonly Vector2Int[] Sizes={new Vector2Int(360,640),new Vector2Int(390,844)};
        static double started,readyAt;static int index;static string error;
        static RewardedHome135Capture(){if(SessionState.GetBool(Key,false))Attach();}
        static object Group(){var a=typeof(Editor).Assembly;var t=a.GetType("UnityEditor.GameViewSizes");var i=typeof(ScriptableSingleton<>).MakeGenericType(t).GetProperty("instance",BindingFlags.Public|BindingFlags.Static).GetValue(null);return t.GetMethod("GetGroup").Invoke(i,new[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeGroupType"),SessionState.GetString(Key+".group","Standalone"))});}
        static EditorWindow View()=>EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));
        static PropertyInfo Selection(EditorWindow view)=>view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance);
        public static void Run()
        {
            if(!Application.isBatchMode)throw new InvalidOperationException("Use an isolated batch Editor.");
            SessionState.SetBool(Key,true);SessionState.SetString(Key+".group",EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android?"Android":"Standalone");
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var home=new GameObject("Rewarded Home native capture").AddComponent<HomePage>();var fields=new SerializedObject(home);
            fields.FindProperty("assets").objectReferenceValue=AssetDatabase.LoadAssetAtPath<HomePageAssets>("Assets/HeartOfTheRain/App/Home/HomePageAssets.asset");fields.ApplyModifiedPropertiesWithoutUndo();
            var group=Group();var view=View();SessionState.SetInt(Key+".previous",(int)Selection(view).GetValue(view));int first=(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null);SessionState.SetInt(Key+".first",first);
            var a=typeof(Editor).Assembly;foreach(var size in Sizes){var entry=Activator.CreateInstance(a.GetType("UnityEditor.GameViewSize"),BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance,null,new object[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),size.x,size.y,"HOTR Rewarded Home 135"},null);group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{entry});}
            Selection(view).SetValue(view,first);EditorApplication.isPlaying=true;
        }
        static void Attach(){started=readyAt=EditorApplication.timeSinceStartup;index=0;error="";Application.logMessageReceived+=OnLog;EditorApplication.update+=Tick;}
        static void OnLog(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)error=message+"\n"+stack;}
        static string Output=>Path.GetFullPath("../Verification/Evidence/RewardedHome135");
        static void Tick()
        {
            try
            {
                if(EditorApplication.timeSinceStartup-started>120)throw new TimeoutException("Rewarded Home capture timed out.");
                if(error.Length>0)throw new InvalidOperationException(error);
                if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
                View().Repaint();if(Screen.width!=Sizes[index].x||Screen.height!=Sizes[index].y){readyAt=EditorApplication.timeSinceStartup;return;}
                if(EditorApplication.timeSinceStartup-readyAt<1)return;
                var home=UnityEngine.Object.FindFirstObjectByType<HomePage>();if(!home||!home.PresentationVisible)return;
                GameLocale.Select(4);home.SetRewardedShortcut(true,false,"...");
                string forwarded=null;UnityEngine.Events.UnityAction<string> onRoute=action=>forwarded=action;home.NavigationRequested.AddListener(onRoute);home.Request("video");home.NavigationRequested.RemoveListener(onRoute);if(forwarded!="video")throw new InvalidOperationException("Home video action was not forwarded to page routing.");
                var icon=home.GetComponentsInChildren<Image>().SingleOrDefault(i=>i.name=="video-icon");if(!icon||!icon.sprite)throw new InvalidOperationException("Native Home video icon is not bound.");
                var team=home.GetComponentsInChildren<RectTransform>().SingleOrDefault(r=>r.name=="team");var video=home.GetComponentsInChildren<RectTransform>().SingleOrDefault(r=>r.name=="video");
                if(!team||!video||video.position.y>=team.position.y)throw new InvalidOperationException("Native Video shortcut is not below Team Quest.");
                Directory.CreateDirectory(Output);Capture(home,Path.Combine(Output,"Home_"+Screen.width+"x"+Screen.height+".png"));
                index++;if(index==Sizes.Length){Finish(0);return;}Selection(View()).SetValue(View(),SessionState.GetInt(Key+".first",0)+index);readyAt=EditorApplication.timeSinceStartup;
            }
            catch(Exception ex){error=ex.ToString();Finish(1);}
        }
        static void Capture(HomePage home,string path)
        {
            var canvas=home.GetComponentInChildren<Canvas>();var go=new GameObject("Rewarded Home capture camera");go.transform.position=new Vector3(-10000,0,-10);var camera=go.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;
            var target=RenderTexture.GetTemporary(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);var previous=RenderTexture.active;var oldCamera=canvas.worldCamera;float oldDistance=canvas.planeDistance;Texture2D pixels=null;
            try{camera.targetTexture=target;canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=1;Canvas.ForceUpdateCanvases();camera.Render();home.SetChapterBackground(null);Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;pixels=new Texture2D(Screen.width,Screen.height,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,Screen.width,Screen.height),0,0);pixels.Apply();File.WriteAllBytes(path,pixels.EncodeToPNG());}
            finally{canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.worldCamera=oldCamera;canvas.planeDistance=oldDistance;RenderTexture.active=previous;RenderTexture.ReleaseTemporary(target);if(pixels)UnityEngine.Object.Destroy(pixels);UnityEngine.Object.Destroy(go);Canvas.ForceUpdateCanvases();}
        }
        static void Finish(int code)
        {
            EditorApplication.update-=Tick;Application.logMessageReceived-=OnLog;Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"Capture.txt"),"status="+(code==0?"PASS":"FAIL")+"\nunity="+Application.unityVersion+"\nscope=Native Unity Play Mode Home UGUI, isolated scene; no Android or live-ad assertion.\n"+error+"\n");
            Selection(View()).SetValue(View(),SessionState.GetInt(Key+".previous",0));var group=Group();for(int i=Sizes.Length-1;i>=0;i--)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{SessionState.GetInt(Key+".first",0)+i});
            SessionState.EraseBool(Key);SessionState.EraseString(Key+".group");SessionState.EraseInt(Key+".first");SessionState.EraseInt(Key+".previous");EditorApplication.Exit(code);
        }
    }
}
#endif

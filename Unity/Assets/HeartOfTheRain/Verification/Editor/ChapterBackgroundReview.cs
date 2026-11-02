#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using HeartOfTheRain.App.Home;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification
{
    // Captures the real Home component in a disposable scene, without a profile host.
    [InitializeOnLoad]
    public static class ChapterBackgroundReview
    {
        const string Key = "HOTR.ChapterBackgroundReview";
        static readonly Vector2Int[] Sizes = { new Vector2Int(720,1280), new Vector2Int(900,2000), new Vector2Int(1200,1600) };
        static int index;
        static double readyAt, started;
        static Report report;
        [Serializable] sealed class Frame { public string file, texture; public int width,height; public Rect uv,safeArea; }
        [Serializable] sealed class Report
        {
            public string utc, unity, status, error;
            public string scope = "Native Unity Play Mode Home UGUI rendered through a camera. Disposable scene, preview state, no profile host or saved-data mutation. Not Android/device evidence.";
            public List<Frame> frames = new List<Frame>();
        }
        static ChapterBackgroundReview() { if(SessionState.GetBool(Key,false)) Attach(); }
        public static void Before() => Begin("Before");
        public static void After() => Begin("After");
        static void Begin(string mode)
        {
            if(!Application.isBatchMode) throw new InvalidOperationException("Run in an isolated batch Editor.");
            SessionState.SetString(Key+".mode",mode);
            SessionState.SetBool(Key,true);
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var home = new GameObject("Chapter 1 Home review").AddComponent<HomePage>();
            var fields = new SerializedObject(home);
            fields.FindProperty("assets").objectReferenceValue = AssetDatabase.LoadAssetAtPath<HomePageAssets>("Assets/HeartOfTheRain/App/Home/HomePageAssets.asset");
            fields.ApplyModifiedPropertiesWithoutUndo();
            SetupSizes();
            EditorApplication.isPlaying = true;
        }
        static object Group()
        {
            var a=typeof(Editor).Assembly;var type=a.GetType("UnityEditor.GameViewSizes");
            var instance=typeof(ScriptableSingleton<>).MakeGenericType(type).GetProperty("instance",BindingFlags.Public|BindingFlags.Static).GetValue(null);
            return type.GetMethod("GetGroup").Invoke(instance,new[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeGroupType"),SessionState.GetString(Key+".group","Standalone"))});
        }
        static EditorWindow View() => EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));
        static PropertyInfo Selection(EditorWindow view) => view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance);
        static void SetupSizes()
        {
            SessionState.SetString(Key+".group",EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android?"Android":EditorUserBuildSettings.activeBuildTarget==BuildTarget.iOS?"iOS":"Standalone");
            var group=Group();var view=View();var a=typeof(Editor).Assembly;
            SessionState.SetInt(Key+".previous",(int)Selection(view).GetValue(view));
            int first=(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null);SessionState.SetInt(Key+".first",first);
            foreach(var size in Sizes)
            {
                var entry=Activator.CreateInstance(a.GetType("UnityEditor.GameViewSize"),BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance,null,new object[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),size.x,size.y,"HOTR Chapter background review"},null);
                group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{entry});
            }
            Selection(view).SetValue(view,first);
        }
        static void Attach()
        {
            started=EditorApplication.timeSinceStartup;readyAt=started;index=0;
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};
            Application.logMessageReceived+=OnLog;EditorApplication.update+=Tick;
        }
        static void OnLog(string message,string stack,LogType type)
        { if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.error=message+"\n"+stack; }
        static string Output => Path.GetFullPath("../Verification/Evidence/ChapterBackground/"+SessionState.GetString(Key+".mode","Unknown"));
        static void Tick()
        {
            try
            {
                if(EditorApplication.timeSinceStartup-started>120)throw new TimeoutException("Home render timed out.");
                if(!string.IsNullOrEmpty(report.error))throw new InvalidOperationException(report.error);
                if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
                View().Repaint();
                if(Screen.width!=Sizes[index].x||Screen.height!=Sizes[index].y){readyAt=EditorApplication.timeSinceStartup;return;}
                if(EditorApplication.timeSinceStartup-readyAt<1)return;
                var home=UnityEngine.Object.FindFirstObjectByType<HomePage>();
                if(!home||!home.PresentationVisible)return;
                // Editor safe-area propagation can lag the requested GameView size.
                if(Mathf.Abs(Screen.safeArea.width-Screen.width)>1||Mathf.Abs(Screen.safeArea.height-Screen.height)>1){readyAt=EditorApplication.timeSinceStartup;return;}
                var background=home.GetComponentsInChildren<RawImage>().Single(x=>x.name=="Chapter artwork");
                if(SessionState.GetString(Key+".mode","")=="After"&&background.texture.name!="Chapter01_VillageWell")throw new InvalidOperationException("A portrait layout is using the superseded artwork.");
                Directory.CreateDirectory(Output);string file=$"Home_{Screen.width}x{Screen.height}.png";
                Capture(home,Path.Combine(Output,file));
                report.frames.Add(new Frame{file=file,width=Screen.width,height=Screen.height,texture=background.texture.name,uv=background.uvRect,safeArea=Screen.safeArea});
                index++;if(index==Sizes.Length){Finish(0);return;}
                var view=View();Selection(view).SetValue(view,SessionState.GetInt(Key+".first",0)+index);readyAt=EditorApplication.timeSinceStartup;
            }
            catch(Exception e){report.error=e.ToString();Finish(1);}
        }
        static void Capture(HomePage home,string path)
        {
            var canvas=home.GetComponentInChildren<Canvas>();
            var go=new GameObject("Isolated UI capture camera");go.transform.position=new Vector3(-10000,0,-10);
            var camera=go.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;
            var target=RenderTexture.GetTemporary(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);var previous=RenderTexture.active;
            var previousCamera=canvas.worldCamera;float previousDistance=canvas.planeDistance;Texture2D pixels=null;
            try
            {
                camera.targetTexture=target;canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=1;
                // Prime the native camera viewport before applying responsive layout.
                // Batch GameView can retain the previous window's pixel size until its first render.
                Canvas.ForceUpdateCanvases();camera.Render();home.SetChapterBackground(null);
                Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;
                var background=home.GetComponentsInChildren<RawImage>().Single(x=>x.name=="Chapter artwork");
                var physicalSize=background.rectTransform.rect.size*canvas.scaleFactor;
                if(Mathf.Abs(physicalSize.x-Screen.safeArea.width)>1||Mathf.Abs(physicalSize.y-Screen.safeArea.height)>1)throw new InvalidOperationException("Home artwork does not cover the native viewport.");
                pixels=new Texture2D(Screen.width,Screen.height,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,Screen.width,Screen.height),0,0);pixels.Apply();
                File.WriteAllBytes(path,pixels.EncodeToPNG());
            }
            finally
            {
                canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.worldCamera=previousCamera;canvas.planeDistance=previousDistance;
                RenderTexture.active=previous;RenderTexture.ReleaseTemporary(target);if(pixels)UnityEngine.Object.Destroy(pixels);UnityEngine.Object.Destroy(go);Canvas.ForceUpdateCanvases();
            }
        }
        static void Finish(int code)
        {
            EditorApplication.update-=Tick;Application.logMessageReceived-=OnLog;report.status=code==0?"PASS_NATIVE_HOME_RENDER":"FAIL_NATIVE_HOME_RENDER";
            Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"Report.json"),JsonUtility.ToJson(report,true));
            var view=View();Selection(view).SetValue(view,SessionState.GetInt(Key+".previous",0));var group=Group();
            for(int i=Sizes.Length-1;i>=0;i--)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{SessionState.GetInt(Key+".first",0)+i});
            SessionState.EraseBool(Key);SessionState.EraseString(Key+".mode");SessionState.EraseString(Key+".group");SessionState.EraseInt(Key+".first");SessionState.EraseInt(Key+".previous");
            EditorApplication.Exit(code);
        }
    }
}
#endif

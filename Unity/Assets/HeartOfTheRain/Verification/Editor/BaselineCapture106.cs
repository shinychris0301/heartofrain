#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification {
    // The identical fixture runs against held105 runtime and final106 runtime.
    // No PlayMode, profile factory, board, service or attempt is started.
    public static class BaselineCapture106 {
        const BindingFlags Fields=BindingFlags.Instance|BindingFlags.NonPublic|BindingFlags.Public;
        [Serializable] sealed class AlphaRow {public string id,sprite;public Rect opaquePixels;public int pixels;}
        [Serializable] sealed class Report {
            public string status="RUNNING",phase,utc,unity;
            public string scope="Actual Home.Build after confirmed720x1600 Editor Screen and actual GameplayHUD.Build/UpdateState; imported artwork, fixed native WorldSpace camera/framebuffer, isolated GPU alpha readback. Synthetic Home/goal counts; no PlayMode, gameplay board, ordinary profile, Android/device or backend claim.";
            public int checks,screenWidth,screenHeight;public bool profilesPreserved,serverReviewPreserved,languagePreferencePreserved,projectSettingsPreserved,gameViewRestored;
            public List<string> captures=new List<string>(),errors=new List<string>();public List<AlphaRow> alpha=new List<AlphaRow>();
        }
        static Report report;static string output,profiles,server;static byte[] settings;static string settingsPath;
        static int locale,storedLanguage,first,previous;static bool hadLanguage,finished;static object group;static EditorWindow view;static double deadline;
        static T Field<T>(object o,string name)=>(T)o.GetType().GetField(name,Fields).GetValue(o);
        static void Set(object o,string name,object value)=>o.GetType().GetField(name,Fields).SetValue(o,value);
        static void Check(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);}
        static string Tree(string root){if(!Directory.Exists(root))return "Absent";using(var h=SHA256.Create()){string rows=string.Join("\n",Directory.GetFiles(root,"*",SearchOption.AllDirectories).OrderBy(v=>v,StringComparer.Ordinal).Select(p=>p.Substring(root.Length)+":"+Convert.ToBase64String(h.ComputeHash(File.ReadAllBytes(p)))));return Convert.ToBase64String(h.ComputeHash(Encoding.UTF8.GetBytes(rows)));}}
        public static void Run(){
            output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW106_OUT")??"../Verification/Evidence/Review106");Directory.CreateDirectory(Path.Combine(output,"Native","BaselineCapture106"));
            report=new Report{phase=Environment.GetEnvironmentVariable("HOTR_REVIEW106_PHASE")??"Unspecified",utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};
            locale=GameLocale.Current;hadLanguage=PlayerPrefs.HasKey(GameLocale.PreferenceKey);storedLanguage=PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue);
            profiles=Tree(Path.Combine(Application.persistentDataPath,"Profiles"));server=Tree(Path.Combine(Application.persistentDataPath,"ServerReview"));settingsPath=Path.GetFullPath("ProjectSettings/ProjectSettings.asset");settings=File.ReadAllBytes(settingsPath);Application.logMessageReceived+=Log;
            try{
                Check(Application.unityVersion=="2022.3.62f3"&&!Application.isPlaying,"Pinned non-PlayMode Editor");
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);GameLocale.Select(4);
                var a=typeof(Editor).Assembly;var sizes=a.GetType("UnityEditor.GameViewSizes");var singleton=typeof(ScriptableSingleton<>).MakeGenericType(sizes).GetProperty("instance",BindingFlags.Static|BindingFlags.Public).GetValue(null);
                group=sizes.GetMethod("GetGroup").Invoke(singleton,new[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeGroupType"),EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android?"Android":"Standalone")});
                view=EditorWindow.GetWindow(a.GetType("UnityEditor.GameView"));previous=(int)view.GetType().GetProperty("selectedSizeIndex",Fields).GetValue(view);first=(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null);
                var size=Activator.CreateInstance(a.GetType("UnityEditor.GameViewSize"),Fields,null,new object[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),720,1600,"HOTR106 controlled capture"},null);
                group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{size});view.GetType().GetProperty("selectedSizeIndex",Fields).SetValue(view,first);view.Repaint();deadline=EditorApplication.timeSinceStartup+8;EditorApplication.update+=Tick;
            }catch(Exception error){report.errors.Add(error.ToString());Finish();}
        }
        static void Tick(){
            if(finished)return;if(Screen.width!=720||Screen.height!=1600){view.Repaint();if(EditorApplication.timeSinceStartup<deadline)return;report.errors.Add("Editor Screen did not confirm720x1600; no reconstructed Home frame is substituted.");Finish();return;}
            EditorApplication.update-=Tick;
            try{report.screenWidth=Screen.width;report.screenHeight=Screen.height;Home();Hud();}catch(Exception error){report.errors.Add(error.ToString());}Finish();
        }
        static void Configure(Canvas canvas,float scale){canvas.renderMode=RenderMode.WorldSpace;canvas.GetComponent<CanvasScaler>().enabled=false;canvas.scaleFactor=scale;var r=(RectTransform)canvas.transform;r.anchorMin=r.anchorMax=r.pivot=Vector2.one*.5f;r.localPosition=Vector3.zero;r.localScale=Vector3.one;r.sizeDelta=new Vector2(720/scale,1600/scale);Canvas.ForceUpdateCanvases();}
        static void Home(){
            var owner=new GameObject("106 isolated actual Home Build");HomePage page=null;
            try{
                page=owner.AddComponent<HomePage>();page.enabled=false;Set(page,"assets",AssetDatabase.LoadAssetAtPath<HomePageAssets>("Assets/HeartOfTheRain/App/Home/HomePageAssets.asset"));Set(page,"usePreviewState",false);page.State.reduceMotion=true;page.State.coins=1250;
                var appearance=owner.AddComponent<ProfilePage>();appearance.enabled=false;Set(appearance,"home",page);page.Build();
                var canvas=Field<Canvas>(page,"canvas");float scale=canvas.scaleFactor;var frame=Field<HomeFrame>(page,"frame");Check(Math.Abs(frame.width-720/scale)<1,"Actual Home frame matches confirmed phone width");Configure(canvas,scale);
                Capture(canvas,scale,report.phase+"_Home720.png");var nodes=Field<Dictionary<string,RectTransform>>(page,"nodes");foreach(string key in new[]{"journey","leaderboard","home","teams","shop"})Measure(canvas,scale,nodes["nav-"+key+"-icon"].GetComponent<Image>(),"nav-"+key);
            }finally{
                if(page){var slices=Field<HomeHeaderSprites>(page,"headerSprites");if(slices!=null){foreach(var s in new[]{slices.Panel,slices.DefaultAvatar,slices.Connector})if(s)UnityEngine.Object.DestroyImmediate(s);Set(page,"headerSprites",null);}var events=Field<EventSystem>(page,"ownedEvents");Set(page,"ownedEvents",null);if(events)UnityEngine.Object.DestroyImmediate(events.gameObject);}
                UnityEngine.Object.DestroyImmediate(owner);
            }
        }
        static void Hud(){
            var owner=new GameObject("106 isolated actual GameplayHUD Build");
            try{
                var hud=owner.AddComponent<GameplayHUD>();hud.enabled=false;hud.assets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");hud.feedback=owner.AddComponent<GameplayFeedback>();hud.feedback.soundEnabled=false;hud.Build();
                var canvas=Field<Canvas>(hud,"canvas");Configure(canvas,1);var safe=Field<RectTransform>(hud,"safe");safe.anchoredPosition=Vector2.zero;safe.sizeDelta=new Vector2(720,1600);Set(hud,"<Height>k__BackingField",1600f);Field<RectTransform>(hud,"bar").anchoredPosition=new Vector2(0,-1434);
                var goals=new[]{new Goal{family="crate",count=21},new Goal{family="moss",count=10},new Goal{family="stone",count=14},new Goal{family="pail",count=2}};hud.UpdateState(12,25,goals,new BoosterInventory(),-1,false,"");Canvas.ForceUpdateCanvases();
                Capture(canvas,1,report.phase+"_Goals720.png");foreach(var goal in goals){var image=canvas.GetComponentsInChildren<Image>().Single(v=>v.name==GameplayHUD.GoalSprite(goal.family));Measure(canvas,1,image,"goal-"+goal.family);}
            }finally{UnityEngine.Object.DestroyImmediate(owner);}
        }
        static Color32[] Render(Canvas canvas,float scale,out Texture2D pixels){
            var go=new GameObject("106 native framebuffer camera");var camera=go.AddComponent<Camera>();camera.enabled=false;camera.orthographic=true;camera.orthographicSize=800/scale;camera.aspect=720f/1600;camera.transform.position=canvas.transform.position-new Vector3(0,0,10);camera.nearClipPlane=.1f;camera.farClipPlane=100;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.clear;
            var target=new RenderTexture(720,1600,24,RenderTextureFormat.ARGB32);target.Create();var active=RenderTexture.active;var old=canvas.worldCamera;
            try{camera.targetTexture=target;canvas.worldCamera=camera;Canvas.ForceUpdateCanvases();camera.Render();camera.Render();RenderTexture.active=target;pixels=new Texture2D(720,1600,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,720,1600),0,0);pixels.Apply();return pixels.GetPixels32();}
            finally{canvas.worldCamera=old;camera.targetTexture=null;RenderTexture.active=active;target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(go);}
        }
        static void Capture(Canvas canvas,float scale,string file){Texture2D pixels;var data=Render(canvas,scale,out pixels);try{Check(data.Count(v=>v.a>24)>10000,"Actual native frame contains artwork");File.WriteAllBytes(Path.Combine(output,"Native","BaselineCapture106",file),pixels.EncodeToPNG());report.captures.Add("Native/BaselineCapture106/"+file);}finally{UnityEngine.Object.DestroyImmediate(pixels);}}
        static void Measure(Canvas canvas,float scale,Image image,string id){
            var graphics=canvas.GetComponentsInChildren<Graphic>(true);var states=graphics.Select(v=>v.enabled).ToArray();Texture2D pixels=null;
            try{foreach(var g in graphics)g.enabled=false;image.enabled=true;var data=Render(canvas,scale,out pixels);int left=720,right=-1,bottom=1600,top=-1,n=0;for(int y=0;y<1600;y++)for(int x=0;x<720;x++)if(data[y*720+x].a>24){n++;left=Math.Min(left,x);right=Math.Max(right,x);bottom=Math.Min(bottom,y);top=Math.Max(top,y);}Check(n>20,"Actual imported alpha pixels exist: "+id);report.alpha.Add(new AlphaRow{id=id,sprite=image.sprite.name,pixels=n,opaquePixels=new Rect(left,bottom,right-left+1,top-bottom+1)});}
            finally{if(pixels)UnityEngine.Object.DestroyImmediate(pixels);for(int i=0;i<graphics.Length;i++)graphics[i].enabled=states[i];Canvas.ForceUpdateCanvases();}
        }
        static void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(text+"\n"+stack);}
        static void Finish(){
            if(finished)return;finished=true;EditorApplication.update-=Tick;
            try{if(view&&group!=null){view.GetType().GetProperty("selectedSizeIndex",Fields).SetValue(view,previous);group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{first});report.gameViewRestored=(int)view.GetType().GetProperty("selectedSizeIndex",Fields).GetValue(view)==previous&&(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null)==first;Check(report.gameViewRestored,"GameView selection/custom-size restored");}GameLocale.Select(locale);report.profilesPreserved=profiles==Tree(Path.Combine(Application.persistentDataPath,"Profiles"));report.serverReviewPreserved=server==Tree(Path.Combine(Application.persistentDataPath,"ServerReview"));report.languagePreferencePreserved=PlayerPrefs.HasKey(GameLocale.PreferenceKey)==hadLanguage&&PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue)==storedLanguage;report.projectSettingsPreserved=settings.SequenceEqual(File.ReadAllBytes(settingsPath));Check(report.profilesPreserved&&report.serverReviewPreserved&&report.languagePreferencePreserved&&report.projectSettingsPreserved,"Ordinary profile/preferences/settings remain unchanged");}catch(Exception error){report.errors.Add(error.ToString());}
            Application.logMessageReceived-=Log;report.status=report.errors.Count==0?"PASS_NATIVE_BASELINE_CAPTURE106":"FAIL_NATIVE_BASELINE_CAPTURE106";File.WriteAllText(Path.Combine(output,"Native","BaselineCapture106.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif

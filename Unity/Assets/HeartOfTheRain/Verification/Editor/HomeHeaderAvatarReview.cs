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
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification
{
    [InitializeOnLoad] public static class HomeHeaderAvatarReview
    {
        const string Key="HOTR.HomeHeaderAvatar";
        static readonly Vector2Int[] Sizes={new Vector2Int(720,1280),new Vector2Int(900,2000),new Vector2Int(1200,1600)};
        static int index;static double started,readyAt;static Report report;
        [Serializable] sealed class Frame {public string file,avatar,frame;public int width,height;public float edge;}
        [Serializable] sealed class Report
        {
            public string utc,unity,status,error,scope="Native Unity Play Mode UGUI renders and programmatic Profile selections using review-memory campaign/appearance. Not device screenshots, physical touch, persistence or FPS tests.";
            public int combinations,fallbacks;public bool stableWallet,headerRoutes,prelevel;
            public List<Frame> frames=new List<Frame>();
        }
        static bool BeforeMode=>SessionState.GetString(Key,"")=="Before";
        static string Output=>Path.GetFullPath("../Verification/Evidence/HomeHeaderAvatar/"+(BeforeMode?"Before":"After"));
        static HomeHeaderAvatarReview(){if(SessionState.GetString(Key,"")!=""){started=readyAt=EditorApplication.timeSinceStartup;report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};EditorApplication.update+=Tick;Application.logMessageReceived+=Log;}}
        public static void Before()=>Run("Before");
        public static void After()=>Run("After");
        static void Run(string phase)
        {
            SessionState.SetString(Key,phase);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");UnityEngine.Object.FindFirstObjectByType<FirstStartPage>().reviewAlways=true;
            typeof(ChapterBackgroundReview).GetMethod("SetupSizes",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);EditorApplication.isPlaying=true;
        }
        static void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.error=message+"\n"+stack;}
        static void Need(bool condition,string message){if(!condition)throw new InvalidOperationException(message);}
        static Transform Node(HomePage h,string name)=>h.GetComponentsInChildren<Transform>(true).Single(t=>t.name==name&&t.gameObject.activeInHierarchy);
        static void Click(ProfilePage p,string name)=>p.GetComponentsInChildren<Button>().Single(b=>b.name==name).onClick.Invoke();
        static void Select(HomePage home,string avatar,string border)
        {
            var profile=home.GetComponent<ProfilePage>();home.GetComponentsInChildren<HomeControlLabel>().Single(c=>c.action=="profile").GetComponent<Button>().onClick.Invoke();Need(profile.IsVisible,"Avatar did not open Profile");
            Click(profile,"Tab 0");Click(profile,"Choice "+avatar);Click(profile,"Tab 2");Click(profile,"Choice "+border);profile.Hide();
            Need(profile.Snapshot.avatarId==avatar&&profile.Snapshot.frameId==border&&home.PresentationInteractable,"Profile selection failed");
        }
        static void Tick()
        {
            try
            {
                if(EditorApplication.timeSinceStartup-started>210)throw new TimeoutException("Home header review timed out");
                if(!string.IsNullOrEmpty(report.error))throw new InvalidOperationException(report.error);
                if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating||EditorApplication.timeSinceStartup-readyAt<.65)return;
                var home=UnityEngine.Object.FindFirstObjectByType<HomePage>();if(!home||!home.GetComponent<PlayerProfileHost>()||!home.GetComponent<PlayerProfileHost>().Ready)return;
                Need(home.GetComponent<PlayerProfileHost>().IsTransient,"Isolated campaign required");var first=home.GetComponent<FirstStartPage>();if(first.IsVisible){first.Request("skip");first.Request("skip");}
                Need(home.PresentationInteractable,"Home not interactive");int size=BeforeMode?index:index/19,choice=BeforeMode?0:index%19;
                if(Screen.width!=Sizes[size].x||Screen.height!=Sizes[size].y){readyAt=EditorApplication.timeSinceStartup;return;}
                Directory.CreateDirectory(Output);
                if(choice==0){home.State.coins=1234;home.State.lives=4;home.State.currentLevel=18;home.State.completedLevelsInChapter=17;home.ApplyState(home.State);Capture(home,null,true);}
                string avatar=BeforeMode?"Dariya":choice==18?"fallback":ProfileRules.Avatars[choice%6];string border=BeforeMode?"Sapphire":choice==18?"fallback":ProfileRules.Frames[choice/6];
                var wallet=BeforeMode?null:Node(home,"header-panel");var coin=Node(home,"coin-count");var life=Node(home,"life-count");var level=Node(home,"start-label");var dock=Node(home,"dock-bg");var art=Node(home,"Chapter artwork");
                Vector3 walletPos=wallet?wallet.position:Vector3.zero;string coinText=coin.GetComponent<Text>().text,lifeText=life.GetComponent<Text>().text;
                if(choice==18&&!BeforeMode)home.SetProfileAvatar(null,null,null);else Select(home,avatar,border);
                Canvas.ForceUpdateCanvases();float edge=((RectTransform)Node(home,"header")).rect.width*.17f;
                if(!BeforeMode)
                {
                    Need(wallet==Node(home,"header-panel")&&coin==Node(home,"coin-count")&&life==Node(home,"life-count")&&level==Node(home,"start-label")&&dock==Node(home,"dock-bg")&&art==Node(home,"Chapter artwork"),"Avatar rebuilt unrelated Home objects");
                    Need(wallet.position==walletPos&&coin.GetComponent<Text>().text==coinText&&life.GetComponent<Text>().text==lifeText,"Wallet moved or counters changed");report.stableWallet=true;
                    Need(!home.GetComponentsInChildren<Image>(true).Any(i=>i.gameObject.activeInHierarchy&&i.sprite&&i.sprite.name=="R4_Header"),"Flattened header still renders");
                    var panel=wallet.GetComponent<Image>().sprite;Need(panel.rect.x>=400&&panel.rect.width==1721,"Panel includes avatar pixels");
                    if(choice==18){Need(Node(home,"avatar-default").gameObject.activeSelf,"Fallback absent");Need(!home.GetComponentsInChildren<Transform>().Any(t=>t.name=="Selected profile avatar"),"Stale custom portrait");report.fallbacks++;}
                    else
                    {
                        var selected=(RectTransform)Node(home,"Selected profile avatar");Need(Mathf.Abs(selected.rect.width-edge)<.01f&&Mathf.Abs(selected.rect.height-edge)<.01f&&selected.anchoredPosition==Vector2.zero,"Frame size or placement changed");
                        Need(!Node(home,"avatar-slot").Find("avatar-default").gameObject.activeSelf,"Fallback portrait under selected avatar");
                        var portrait=Node(home,"Portrait").GetComponent<Image>();Need(portrait.sprite==Resources.Load<ProfileAssets>("HeartOfTheRainProfile/Config").Find("Avatar_"+avatar),"Wrong Home portrait");
                        Need(Mathf.Abs(portrait.rectTransform.rect.width/portrait.rectTransform.rect.height-portrait.sprite.rect.width/portrait.sprite.rect.height)<.001f,"Portrait stretched");report.combinations++;
                    }
                }
                if(BeforeMode||choice==0||choice==7||choice==14||choice==18)
                {
                    string file=$"Home_{avatar}_{border}_{Screen.width}x{Screen.height}.png";Capture(home,Path.Combine(Output,file),false);report.frames.Add(new Frame{file=file,avatar=avatar,frame=border,width=Screen.width,height=Screen.height,edge=edge});
                }
                if(!BeforeMode&&index==56)
                {
                    var routes=new List<string>();UnityEngine.Events.UnityAction<string> listener=s=>routes.Add(s);home.NavigationRequested.AddListener(listener);
                    foreach(var route in new[]{"coins","lives","settings"}){home.GetComponentsInChildren<HomeControlLabel>().Single(c=>c.action==route).GetComponent<Button>().onClick.Invoke();Need(routes.LastOrDefault()==route,"Header route failed: "+route);home.NavigationRequested.Invoke("home");home.SetPresentation(true,true);}
                    home.NavigationRequested.RemoveListener(listener);report.headerRoutes=true;
                    // Routing listeners may show overlays; close them through their existing request handler before pre-level.
                    var modal=home.GetComponent<PreLevelModal>();modal.Requested("close");home.SetPresentation(true,true);
                    home.GetComponentsInChildren<HomeControlLabel>().Single(c=>c.action=="prelevel").GetComponent<Button>().onClick.Invoke();Need(modal.IsVisible&&home.LastRequestedAction=="prelevel:18","Level button routing changed");modal.Requested("close");report.prelevel=true;
                }
                index++;if(index==(BeforeMode?3:57)){Finish(0);return;}
                int next=BeforeMode?index:index/19;if(next!=size){var view=EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(view,SessionState.GetInt("HOTR.ChapterBackgroundReview.first",0)+next);view.Repaint();}readyAt=EditorApplication.timeSinceStartup;
            }
            catch(Exception e){report.error=e.ToString();Finish(1);}
        }
        static void Capture(HomePage home,string path,bool prime)
        {
            var canvases=UnityEngine.Object.FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID).Where(c=>c.isActiveAndEnabled&&c.renderMode==RenderMode.ScreenSpaceOverlay).ToArray();var cameras=canvases.Select(c=>c.worldCamera).ToArray();var distances=canvases.Select(c=>c.planeDistance).ToArray();
            var go=new GameObject("Header capture camera");go.transform.position=new Vector3(-10000,0,-10);var camera=go.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;
            var previous=RenderTexture.active;var target=RenderTexture.GetTemporary(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);Texture2D pixels=null;
            try{camera.targetTexture=target;foreach(var c in canvases){c.renderMode=RenderMode.ScreenSpaceCamera;c.worldCamera=camera;c.planeDistance=1;}Canvas.ForceUpdateCanvases();camera.Render();if(prime){home.SetChapterBackground(null);Canvas.ForceUpdateCanvases();camera.Render();}if(path!=null){RenderTexture.active=target;pixels=new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0);pixels.Apply();File.WriteAllBytes(path,pixels.EncodeToPNG());}}
            finally{for(int n=0;n<canvases.Length;n++){canvases[n].renderMode=RenderMode.ScreenSpaceOverlay;canvases[n].worldCamera=cameras[n];canvases[n].planeDistance=distances[n];}RenderTexture.active=previous;RenderTexture.ReleaseTemporary(target);if(pixels)UnityEngine.Object.Destroy(pixels);UnityEngine.Object.Destroy(go);Canvas.ForceUpdateCanvases();}
        }
        static void Finish(int code)
        {
            report.status=code==0?"PASS_NATIVE_HOME_HEADER":"FAIL_NATIVE_HOME_HEADER";Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"Native_Review.json"),JsonUtility.ToJson(report,true));EditorApplication.update-=Tick;Application.logMessageReceived-=Log;SessionState.EraseString(Key);
            var view=EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(view,SessionState.GetInt("HOTR.ChapterBackgroundReview.previous",0));var group=typeof(ChapterBackgroundReview).GetMethod("Group",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);
            for(int n=2;n>=0;n--)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{SessionState.GetInt("HOTR.ChapterBackgroundReview.first",0)+n});EditorApplication.Exit(code);
        }
    }
}
#endif

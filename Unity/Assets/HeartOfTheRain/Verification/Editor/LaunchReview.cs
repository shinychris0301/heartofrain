#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using HeartOfTheRain.App.Launch;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.Settings;
using HeartOfTheRain.App.Localization;
using UnityEditor;
using UnityEditor.Android;
using UnityEditor.Build;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification
{
    [InitializeOnLoad] public static class LaunchReview
    {
        const string Key="HOTR.LaunchReview";
        const string BarKey=Key+".LoadingBar";
        static readonly Vector2Int[] Sizes={new Vector2Int(393,852),new Vector2Int(320,480),new Vector2Int(768,1024),new Vector2Int(900,2000),new Vector2Int(320,568)};
        static int index,scenario=-1,originalLocale;static double started,readyAt,releasedAt;static bool loadingFixture;
        static Report report;static MemorySettings settings;static MemoryProfileRepository repository;static PlayerProfile initial;
        static string ordinaryAppearance;static int ordinaryStage,ordinaryComplete;
        [Serializable] sealed class Report {public string utc,unity,status,error,scope="Native Editor Play Mode; exact imported art, camera-rendered UGUI and actual async scene transitions with isolated memory profiles/tutorial/appearance. Layout progress values are review fixtures. Cutout checks are geometry simulation; not Android/device or measured startup performance.";public int checks;public List<string> frames=new List<string>();public List<Route> routes=new List<Route>();public List<BarState> bars=new List<BarState>();}
        [Serializable] sealed class Route {public string name,stage;public bool homeVisible,tutorialVisible,launchReleased,artUnloaded,logoUnloaded,loadingSkinsUnloaded,settingsUnchanged,walletUnchanged;}
        [Serializable] sealed class BarState {public int width,height;public float progress,fillWidth,expectedWidth,barHeight;public bool visible;}
        sealed class MemorySettings:ISettingsStore {public int stage,complete,writes;public int Read(string key,int fallback)=>key==FirstStartSession.StageKey?stage:key==FirstStartSession.CompleteKey?complete:fallback;public void Write(string key,int value){writes++;if(key==FirstStartSession.StageKey)stage=value;else if(key==FirstStartSession.CompleteKey)complete=value;}public void Flush(){}}
        static string Output=>Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_LAUNCH80_OUTPUT")??(SessionState.GetBool(BarKey,false)?"../Verification/Evidence/LoadingBar/Native":"../Verification/Evidence/LaunchIntegration"));
        static LaunchReview(){if(SessionState.GetBool(Key,false)){started=readyAt=EditorApplication.timeSinceStartup;report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};originalLocale=GameLocale.Current;ordinaryAppearance=PlayerPrefs.GetString(ProfileStore.Key,"<absent>");ordinaryStage=PlayerPrefs.GetInt(FirstStartSession.StageKey,-1);ordinaryComplete=PlayerPrefs.GetInt(FirstStartSession.CompleteKey,-1);SceneManager.sceneLoaded+=Loaded;EditorApplication.update+=Tick;Application.logMessageReceived+=Log;}}
        public static void Run(){SessionState.SetBool(Key,true);EditorSceneManager.OpenScene(LaunchPage.ScenePath);UnityEngine.Object.FindFirstObjectByType<LaunchPage>().HoldForReview=true;typeof(ProfileM71Verification).GetMethod("SetupSizes",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);EditorApplication.isPlaying=true;}
        public static void LoadingBar(){SessionState.SetBool(BarKey,true);Run();}
        static void Check(bool condition,string message){report.checks++;if(!condition)throw new InvalidOperationException(message);}
        static void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.error=message+"\n"+stack;}
        static void Invoke(LaunchPage page,string name,object arg)=>typeof(LaunchPage).GetMethod(name,BindingFlags.Instance|BindingFlags.NonPublic).Invoke(page,new[]{arg});
        static void Size(int index){var view=EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(view,SessionState.GetInt("HOTR.M71.Verification.first",0)+index);view.Repaint();readyAt=EditorApplication.timeSinceStartup;}
        static void Rules(LaunchPage page)
        {
            Check(EditorBuildSettings.scenes[0].path==LaunchPage.ScenePath,"Launch is not the first build scene");
            Check(Application.CanStreamedLevelBeLoaded(LaunchPage.GameScenePath),"Target scene unavailable");
            Check(page.keyArt.width==941&&page.keyArt.height==1672&&page.title.width==1774&&page.title.height==887,"Source texture resolution changed");
            Check(AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(page.title))=="dbf14ca73e245a739834a16d7faa3b82","Russian opening wordmark is not bound");
            Check(PlayerSettings.productName=="Сердце дождя","Visible app name changed");
            Check(page.font!=null,"Launch font missing");
            var icon=AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/HeartOfTheRain/App/Launch/Art/App_Icon_R1.png");
            var slots=PlayerSettings.GetPlatformIcons(NamedBuildTarget.Android,HeartOfTheRain.App.Launch.Editor.LaunchSetup.LegacyIconKind);Check(slots.Length>0&&slots.All(s=>s.GetTexture()==icon),"Android legacy icon slots differ");
            Check(HeartOfTheRain.App.Editor.PortraitBuildPolicy.IsPortraitOnly,"Portrait policy regressed");
            Invoke(page,"SetProgress",.25f);Invoke(page,"SetProgress",.1f);Check(page.Progress==.25f,"Progress regressed");Invoke(page,"SetProgress",2f);Check(page.Progress==1,"Progress exceeds one");
            typeof(LaunchPage).GetProperty("Progress").SetValue(page,0f);Invoke(page,"SetProgress",.4f);
            foreach(var size in Sizes)foreach(var inset in new[]{0,24})
            {
                var safe=new Rect(0,inset,size.x,size.y-inset-32);var f=LaunchLayout.Build(size.x,size.y,safe);
                foreach(var rect in new[]{f.logo,f.footer,f.track,f.status})Check(rect.xMin>=safe.xMin-.01f&&rect.xMax<=safe.xMax+.01f&&rect.yMin>=safe.yMin-.01f&&rect.yMax<=safe.yMax+.01f,"Simulated safe-area overflow");
                Check(Mathf.Abs(f.logo.width/f.logo.height-2)<.001f,"Logo aspect changed");
                Check(f.uv.xMin>=0&&f.uv.xMax<=1.001f&&f.uv.yMin>=0&&f.uv.yMax<=1.001f,"Invalid art UV crop");
            }
        }
        static void Tick()
        {
            try
            {
                if(EditorApplication.timeSinceStartup-started>210)throw new TimeoutException("Launch verification timeout");
                if(!string.IsNullOrEmpty(report.error))throw new InvalidOperationException(report.error);
                if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating||EditorApplication.timeSinceStartup-readyAt<.4)return;
                if(index<5)
                {
                    if(Screen.width!=Sizes[index].x||Screen.height!=Sizes[index].y)return;
                    var page=UnityEngine.Object.FindFirstObjectByType<LaunchPage>();if(!page)return;
                    if(index==0)Rules(page);
                    if(SessionState.GetBool(BarKey,false))BarStates(page);
                    foreach(int language in new[]{0,1,2,3,4})
                    {
                        GameLocale.Select(language);page.Reflow();
                        // Prime the changed native canvas viewport before checking text.
                        Capture(page,Path.GetFullPath("../.verification-cache/Launch_Prime.png"));page.Reflow();Canvas.ForceUpdateCanvases();
                        var text=page.GetComponentsInChildren<Text>().Single(t=>t.name=="Loading status");var generator=new TextGenerator();generator.Populate(text.text,text.GetGenerationSettings(text.rectTransform.rect.size));
                        Check(generator.characterCountVisible>=text.text.Length,"Localized loading text clipped");
                        var frame=LaunchLayout.Build(Screen.width,Screen.height,Screen.safeArea);
                        Check(Mathf.Abs(page.GetComponentsInChildren<RawImage>().Single(t=>t.name=="Opening artwork").uvRect.width-frame.uv.width)<.001f,"Native crop differs");
                        if(language==0||language==4){string file=$"Launch_{GameLocale.Codes[language]}_{Screen.width}x{Screen.height}.png";Capture(page,Path.Combine(Output,file));report.frames.Add(file);}
                    }
                    index++;if(index<5){Size(index);return;}
                    scenario=0;GameLocale.Select(0);Size(0);StartRoute(page);return;
                }
                if(loadingFixture)return;
                var launch=UnityEngine.Object.FindFirstObjectByType<LaunchPage>();
                if(launch){Check(!launch.Failed,"Real async launch failed");return;}
                if(releasedAt==0){releasedAt=EditorApplication.timeSinceStartup;return;}
                if(EditorApplication.timeSinceStartup-releasedAt<.6)return;
                var first=UnityEngine.Object.FindFirstObjectByType<FirstStartPage>();if(!first||!first.Initialized)return;
                var home=first.home;var profile=home.GetComponent<PlayerProfileHost>();Check(profile.Ready,"Profile did not initialize");
                var snapshot=repository.Read();
                var route=new Route{name=new[]{"Fresh","ResumeRocket","ReturningProgress","CompletedTutorial"}[scenario],stage=first.Stage.ToString(),homeVisible=home.PresentationVisible,tutorialVisible=first.IsVisible,launchReleased=!launch,
                    artUnloaded=!Resources.FindObjectsOfTypeAll<Texture2D>().Any(t=>t.name=="Opening_Key_Art_R1"),logoUnloaded=!Resources.FindObjectsOfTypeAll<Texture2D>().Any(t=>t.name=="Title_Logo_R1"||t.name=="Title_Logo_RU_R1"),settingsUnchanged=settings.writes==0,
                    walletUnchanged=snapshot.coins==initial.coins&&snapshot.lives==initial.lives&&snapshot.stars==initial.stars&&snapshot.completed==initial.completed&&snapshot.starting.SequenceEqual(initial.starting)&&snapshot.tools.SequenceEqual(initial.tools)&&snapshot.attempts.Count==0&&snapshot.rewards.Count==0};
                Check(route.launchReleased&&route.artUnloaded&&route.logoUnloaded,"Launch textures/root retained after handoff");
                route.loadingSkinsUnloaded=!Resources.FindObjectsOfTypeAll<Texture2D>().Any(t=>t.name.StartsWith("Loading_"));Check(route.loadingSkinsUnloaded,"Loading skin textures retained");
                Check(route.walletUnchanged&&route.settingsUnchanged,"Launch altered progression/inventory/tutorial");
                Check(scenario<2?first.IsVisible&&!home.PresentationVisible:!first.IsVisible&&home.PresentationInteractable,"Wrong tutorial/Home route");
                Check(first.Stage==(scenario==0?FirstStartStage.Prologue:scenario==1?FirstStartStage.Rocket:FirstStartStage.Complete),"Saved tutorial stage changed");
                string capture="Route_"+route.name+".png";typeof(HomeLevelButtonReview).GetMethod("Capture",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{home,Path.Combine(Output,capture)});report.frames.Add(capture);report.routes.Add(route);
                Check(PlayerPrefs.GetString(ProfileStore.Key,"<absent>")==ordinaryAppearance&&PlayerPrefs.GetInt(FirstStartSession.StageKey,-1)==ordinaryStage&&PlayerPrefs.GetInt(FirstStartSession.CompleteKey,-1)==ordinaryComplete,"Ordinary preferences changed");
                scenario++;if(scenario==4){Finish(0);return;}
                loadingFixture=true;SceneManager.LoadSceneAsync(LaunchPage.ScenePath);readyAt=EditorApplication.timeSinceStartup;
            }
            catch(Exception e){report.error=e.ToString();Finish(1);}
        }
        static void StartRoute(LaunchPage page)
        {
            settings=new MemorySettings{stage=scenario==1?3:0,complete=scenario==3?1:0};
            releasedAt=0;typeof(LaunchPage).GetProperty("Progress").SetValue(page,0f);Invoke(page,"SetProgress",0f);
            page.HoldForReview=false;page.StartCoroutine("Start");readyAt=EditorApplication.timeSinceStartup;
        }
        static void BarStates(LaunchPage page)
        {
            var sprites=new[]{page.loadingTrack,page.loadingFill,page.loadingFrame};
            foreach(var sprite in sprites){Check(sprite&&sprite.pixelsPerUnit==400&&!sprite.packed,"Missing/packed loading skin or incorrect PPU");Check(sprite.texture.mipmapCount==1&&sprite.texture.filterMode==FilterMode.Bilinear,"Small UI skin sampling changed");}
            var track=page.GetComponentsInChildren<Image>(true).Single(i=>i.name=="Loading track");var fill=page.GetComponentsInChildren<Image>(true).Single(i=>i.name=="Actual loading progress");var outline=page.GetComponentsInChildren<Image>(true).Single(i=>i.name=="Loading frame");
            foreach(var image in new[]{track,fill,outline})Check(image.type==Image.Type.Sliced&&image.color==Color.white&&!image.raycastTarget,"Loading layer is distorted/tinted/interactive");
            Check(page.GetComponentsInChildren<Image>().Single(i=>i.name=="Loading footer").color.a==0,"Dark footer plate remains visible");
            Check(outline.transform.GetSiblingIndex()==outline.transform.parent.childCount-1,"Outline is not drawn last");
            page.Reflow();Capture(page,Path.GetFullPath("../.verification-cache/LoadingBar/Prime.png"));
            foreach(float p in new[]{0,.01f,.25f,.72f,1})
            {
                typeof(LaunchPage).GetProperty("Progress").SetValue(page,0f);Invoke(page,"SetProgress",p);Canvas.ForceUpdateCanvases();
                float expected=((RectTransform)fill.transform.parent).rect.width*p;
                Check(Mathf.Abs(fill.rectTransform.rect.width-expected)<.01f,"Loading fill width differs from actual progress");Check(fill.gameObject.activeSelf==(p>0),"Zero fill is visible or positive fill hidden");
                Check(Mathf.Abs(track.rectTransform.rect.width/track.rectTransform.rect.height-20)<.001f,"Bar aspect ratio changed");
                var state=new BarState{width=Screen.width,height=Screen.height,progress=p,fillWidth=fill.rectTransform.rect.width,expectedWidth=expected,barHeight=track.rectTransform.rect.height,visible=fill.gameObject.activeSelf};report.bars.Add(state);
                if(index==0){string file="Bar_"+Mathf.RoundToInt(p*100).ToString("000")+".png";Capture(page,Path.Combine(Output,file));report.frames.Add(file);}
            }
            typeof(LaunchPage).GetProperty("Progress").SetValue(page,0f);Invoke(page,"SetProgress",.4f);
        }
        static void Loaded(Scene scene,LoadSceneMode mode)
        {
            if(scene.path==LaunchPage.ScenePath)
            {
                if(scenario<0)return;
                var page=UnityEngine.Object.FindFirstObjectByType<LaunchPage>();page.HoldForReview=true;
                // Start will observe Hold before loading; explicitly restart next tick.
                EditorApplication.delayCall+=()=>{if(!SessionState.GetBool(Key,false)||!page)return;StartRoute(page);loadingFixture=false;};return;
            }
            if(scene.path!=LaunchPage.GameScenePath)return;
            var first=UnityEngine.Object.FindFirstObjectByType<FirstStartPage>();first.reviewAlways=false;first.VerificationStore=settings;
            var home=first.home;var flow=home.GetComponent<HomeLevelFlow>();initial=PlayerProfile.New(flow.assets.initialStock);
            if(scenario==2){initial.completed=10;initial.currentLevel=11;initial.stars=20;}
            repository=new MemoryProfileRepository(initial);
            var host=home.gameObject.AddComponent<PlayerProfileHost>();host.VerificationRepository=repository;host.VerificationAuthorityFactory=_=>new UnavailableGiftAuthority();
            home.gameObject.AddComponent<ProfilePage>().VerificationStore=new ProfileStore(new MemoryAppearancePreferences());
        }
        static void Capture(LaunchPage page,string file)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(file));var canvas=page.GetComponentInChildren<Canvas>();var go=new GameObject("Launch review capture");go.transform.position=new Vector3(-10000,0,-10);var camera=go.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;
            var old=RenderTexture.active;var target=RenderTexture.GetTemporary(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);Texture2D pixels=null;
            try{camera.targetTexture=target;canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=1;Canvas.ForceUpdateCanvases();camera.Render();page.Reflow();Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;pixels=new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0);pixels.Apply();File.WriteAllBytes(file,pixels.EncodeToPNG());}
            finally{canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.worldCamera=null;RenderTexture.active=old;RenderTexture.ReleaseTemporary(target);if(pixels)UnityEngine.Object.Destroy(pixels);UnityEngine.Object.Destroy(go);}
        }
        static void Finish(int code)
        {
            report.status=code==0?"PASS_NATIVE_LAUNCH_INTEGRATION":"FAIL_NATIVE_LAUNCH_INTEGRATION";Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"Native_Review.json"),JsonUtility.ToJson(report,true));SceneManager.sceneLoaded-=Loaded;EditorApplication.update-=Tick;Application.logMessageReceived-=Log;SessionState.EraseBool(Key);SessionState.EraseBool(BarKey);GameLocale.Select(originalLocale);
            var view=EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(view,SessionState.GetInt("HOTR.M71.Verification.previous",0));var group=typeof(ProfileM71Verification).GetMethod("Group",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);for(int i=4;i>=0;i--)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{SessionState.GetInt("HOTR.M71.Verification.first",0)+i});EditorApplication.Exit(code);
        }
    }
}
#endif

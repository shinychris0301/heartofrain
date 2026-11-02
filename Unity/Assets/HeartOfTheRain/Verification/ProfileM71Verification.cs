#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.Teams;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using Debug = UnityEngine.Debug;

namespace HeartOfTheRain.Verification
{
    [InitializeOnLoad] public sealed class ProfileM71Verification : MonoBehaviour
    {
        const string Key="HOTR.M71.Verification";
        const string Marker="HOTR_RunProfileM71";
        const string PlatformKey="HeartOfTheRain.Verification.ProfileM71.v1";
        static string Output=>Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW98_OUT")??"../Verification/Evidence/ProfileM71");
        static string Fixture=>Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW98_PROFILE_FIXTURE")??"../.verification-cache/ProfileM71/appearance.json");
        static readonly Vector2Int[] Sizes={new Vector2Int(393,852),new Vector2Int(320,480),new Vector2Int(768,1024),new Vector2Int(900,2000),new Vector2Int(320,568)};
        [Serializable] public sealed class Report
        {
            public string utc,unity,status="RUNNING",mode;
            public string scope="Native Unity Play Mode, programmatic button/input dispatch, isolated appearance file and in-memory campaign. Camera-rendered UGUI at requested viewports; not physical touch, Android, software-keyboard or FPS certification.";
            public int checks;public double coldOpenMs,warmOpenMaxMs;
            public List<string> passed=new List<string>(),errors=new List<string>(),frames=new List<string>();
        }
        public sealed class FilePreferences:IAppearancePreferences
        {
            public bool fail;readonly string path;
            public FilePreferences(string path){this.path=path;}
            public string Read()=>File.Exists(path)?File.ReadAllText(path):"{}";
            public void Write(string value){if(fail)throw new IOException("Explicit appearance write fault");File.WriteAllText(path,value);}
            public void Flush(){}
        }
        static ProfileM71Verification(){if(SessionState.GetBool(Key,false))EditorApplication.update+=Monitor;}
        public static void Play()=>Begin(false);
        public static void Restart()=>Begin(true);
        static void Begin(bool restart)
        {
            if(!Application.isBatchMode)throw new InvalidOperationException("Use isolated batch verification.");
            Directory.CreateDirectory(Path.GetDirectoryName(Fixture));Directory.CreateDirectory(Output);
            if(!restart){File.WriteAllText(Fixture,"{}");PlayerPrefs.SetString(PlatformKey,"{}");PlayerPrefs.Save();}else if(!File.Exists(Fixture))throw new InvalidOperationException("Run Play before Restart.");
            SessionState.SetBool(Key,true);SessionState.SetString(Key+".mode",restart?"Restart":"Play");SessionState.SetFloat(Key+".start",(float)EditorApplication.timeSinceStartup);
            EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");SetupSizes();
            Directory.CreateDirectory(Application.persistentDataPath);File.WriteAllText(Path.Combine(Application.persistentDataPath,Marker),restart?"Restart":"Play");EditorApplication.isPlaying=true;
        }
        static object Group()
        {
            var a=typeof(Editor).Assembly;var type=a.GetType("UnityEditor.GameViewSizes");var instance=typeof(ScriptableSingleton<>).MakeGenericType(type).GetProperty("instance",BindingFlags.Public|BindingFlags.Static).GetValue(null);
            return type.GetMethod("GetGroup").Invoke(instance,new[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeGroupType"),SessionState.GetString(Key+".group","Standalone"))});
        }
        static EditorWindow View()=>EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));
        static PropertyInfo Selected(EditorWindow view)=>view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance);
        static void SetupSizes()
        {
            SessionState.SetString(Key+".group",EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android?"Android":EditorUserBuildSettings.activeBuildTarget==BuildTarget.iOS?"iOS":"Standalone");var group=Group();var view=View();var a=typeof(Editor).Assembly;
            SessionState.SetInt(Key+".previous",(int)Selected(view).GetValue(view));int first=(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null);SessionState.SetInt(Key+".first",first);
            foreach(var size in Sizes){var entry=Activator.CreateInstance(a.GetType("UnityEditor.GameViewSize"),BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance,null,new object[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),size.x,size.y,"HOTR M71 profile"},null);group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{entry});}Selected(view).SetValue(view,first);
        }
        static void Monitor()
        {
            if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
            var probe=FindFirstObjectByType<ProfileM71Verification>();if(probe&&probe.report!=null&&probe.report.status!="RUNNING")Finish(probe.report.errors.Count==0?0:1);
            else if(EditorApplication.timeSinceStartup-SessionState.GetFloat(Key+".start",0)>240){Debug.LogError("M71 verification timed out");Finish(1);}
        }
        static void Finish(int code)
        {
            EditorApplication.update-=Monitor;var view=View();Selected(view).SetValue(view,SessionState.GetInt(Key+".previous",0));var group=Group();
            for(int i=Sizes.Length-1;i>=0;i--)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{SessionState.GetInt(Key+".first",0)+i});SessionState.EraseBool(Key);EditorApplication.Exit(code);
        }
        Report report;HomePage home;ProfilePage page;FilePreferences preferences;string ordinaryBefore,campaignBefore;int originalLocale;float deadline;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)] static void Boot()
        {
            string marker=Path.Combine(Application.persistentDataPath,Marker);if(!File.Exists(marker))return;string mode=File.ReadAllText(marker);File.Delete(marker);if(mode!="Play"&&mode!="Restart")throw new InvalidOperationException("Invalid M71 fixture mode");
            var first=FindFirstObjectByType<FirstStartPage>();first.reviewAlways=true;var probe=new GameObject("Opt-in M71 native verification").AddComponent<ProfileM71Verification>();probe.home=first.home;
            probe.preferences=new FilePreferences(Fixture);probe.page=first.home.gameObject.AddComponent<ProfilePage>();probe.page.VerificationStore=new ProfileStore(probe.preferences);
            probe.ordinaryBefore=PlayerPrefs.GetString(ProfileStore.Key,"<absent>");probe.originalLocale=GameLocale.Current;probe.report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,mode=mode};probe.deadline=Time.realtimeSinceStartup+200;Application.logMessageReceived+=probe.Log;
        }
        IEnumerator Start()
        {
            IEnumerator work=Run();while(true){object step;try{if(!work.MoveNext())break;step=work.Current;}catch(Exception e){Complete(e.ToString());yield break;}yield return step;}Complete(null);
        }
        IEnumerator Run()
        {
            yield return new WaitForSecondsRealtime(1);
            while(!page.IsPrepared){if(Time.realtimeSinceStartup>deadline)throw new TimeoutException("Profile preparation timed out");yield return null;}
            var first=home.GetComponent<FirstStartPage>();if(first.IsVisible){first.Request("skip");first.Request("skip");}
            Check(home.PresentationInteractable,"Review tutorial returned interactive Home");var host=home.GetComponent<PlayerProfileHost>();Check(host.IsTransient,"Campaign repository is isolated review memory");campaignBefore=JsonUtility.ToJson(host.Service.Read());
            Check(page.IsPrepared,"Profile preparation completed while its canvas stayed hidden");
            var reviewType=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("HeartOfTheRain.App.Profile.Editor.ProfileReview")).First(t=>t!=null);reviewType.GetMethod("Validate").Invoke(null,null);RulesAndStore();
            var platform=new ProfileStore(new PlayerAppearancePreferences(PlatformKey));string platformError;
            if(report.mode=="Restart")
            {
                Check(platform.Snapshot.displayName=="Platform Élodie"&&platform.Snapshot.avatarId=="Dariya"&&platform.Snapshot.bannerId=="Lantern"&&platform.Snapshot.frameId=="Sapphire","Native PlayerPrefs adapter reloads the isolated key in a second Unity process");PlayerPrefs.DeleteKey(PlatformKey);PlayerPrefs.Save();
                Check(page.Snapshot.displayName=="Дарья Élodie"&&page.Snapshot.avatarId=="Dariya"&&page.Snapshot.bannerId=="Lantern"&&page.Snapshot.frameId=="Sapphire","Second Unity process reloads saved name, avatar, banner and frame");
                ClickHome();yield return null;Capture("Restart_Profile");page.Hide();Capture("Restart_Home");Check(home.PresentationInteractable,"Restart close restores Home input");yield break;
            }
            Check(platform.Rename("Platform Élodie",out platformError)&&platform.Select(0,"Dariya",out platformError)&&platform.Select(1,"Lantern",out platformError)&&platform.Select(2,"Sapphire",out platformError),"Native PlayerPrefs adapter saves name and appearance under an isolated verification key");
            var clock=Stopwatch.StartNew();ClickHome();clock.Stop();report.coldOpenMs=clock.Elapsed.TotalMilliseconds;
            Check(page.IsVisible&&!home.PresentationInteractable,"Home avatar opens modal and blocks underlying input");Capture("Profile_en");
            Click("Edit name");Check(page.IsRenaming,"Edit opens Change Name");Capture("Rename_en");Input().text="   ";Click("Save");Check(page.IsRenaming&&page.Snapshot.displayName=="Rainkeeper","Blank rename cannot commit");Capture("Rename_Error");Input().text="Cancelled draft";Click("Cancel");Check(!page.IsRenaming&&page.Snapshot.displayName=="Rainkeeper","Cancel discards the name draft");
            for(int language=1;language<5;language++)
            {
                GameLocale.Select(language);yield return null;Capture("Profile_"+new[]{"en","es","fr","de","ru"}[language]);Click("Edit name");Capture("Rename_"+new[]{"en","es","fr","de","ru"}[language]);Click("Cancel");
            }
            GameLocale.Select(0);yield return null;
            for(int tab=0;tab<3;tab++)
            {
                Click("Tab "+tab);foreach(string id in tab==0?ProfileRules.Avatars:tab==1?ProfileRules.Banners:ProfileRules.Frames){Click("Choice "+id);Check((tab==0?page.Snapshot.avatarId:tab==1?page.Snapshot.bannerId:page.Snapshot.frameId)==id,"Selection persists "+tab+":"+id);yield return null;}
                Capture(new[]{"All_Avatars","All_Banners","All_Frames"}[tab]);
            }
            Click("Tab 0");Click("Choice Dariya");Click("Tab 1");Click("Choice Lantern");Click("Tab 2");Click("Choice Sapphire");Click("Tab 3");Capture("Live_Stats");
            Check(page.GetComponentsInChildren<Text>().Any(t=>t.name=="Stat value 3"&&t.text==home.State.stars.ToString()),"Stats use current Home model values");
            Click("Edit name");Input().text=new string('W',20);Click("Save");page.SetTeam("Very long local team display name","");Capture("Long_Names");foreach(var text in page.GetComponentsInChildren<Text>().Where(t=>t.name=="Player name"||t.name=="Team name"))Check(text.preferredWidth<=text.rectTransform.rect.width+.1f,"Long display names fit without changing saved values");Check(page.Snapshot.displayName==new string('W',20),"Ellipsis never truncates saved names");page.SetTeam("","");
            Click("Edit name");Input().text="  Дарья E\u0301lodie  ";Click("Save");Check(!page.IsRenaming&&page.Snapshot.displayName=="Дарья Élodie","Rename commits normalized accents and Cyrillic");
            Click("Edit name");preferences.fail=true;Input().text="Cannot save";Click("Save");Check(page.IsRenaming&&page.Snapshot.displayName=="Дарья Élodie","Failed storage keeps the saved name and open draft");Capture("Save_Error");preferences.fail=false;Click("Cancel");
            Click("Tab 0");preferences.fail=true;Click("Choice Compass");Check(page.Snapshot.avatarId=="Dariya","Failed appearance save preserves selected avatar");Capture("Selection_Save_Error");preferences.fail=false;Click("Choice Dariya");page.Hide();Capture("Home_Selected");Check(home.GetComponentsInChildren<Image>().Any(i=>i.name=="Portrait"&&i.sprite&&i.sprite.name=="Avatar_Dariya"),"Selected portrait is bound on Home");
            int blurId=0;for(int i=0;i<12;i++){clock.Restart();ClickHome();clock.Stop();report.warmOpenMaxMs=Math.Max(report.warmOpenMaxMs,clock.Elapsed.TotalMilliseconds);var texture=page.GetComponentsInChildren<RawImage>().Single(x=>x.name=="Profile backdrop").texture;if(i==0)blurId=texture.GetInstanceID();Check(texture.GetInstanceID()==blurId,"Repeated opening reuses cached chapter backdrop");page.Hide();yield return null;}
            var lost=page.GetComponentsInChildren<RawImage>(true).Single(x=>x.name=="Profile backdrop").texture as RenderTexture;Check(lost&&lost.IsCreated(),"Cached backdrop is a live native render target");lost.Release();ClickHome();var restored=page.GetComponentsInChildren<RawImage>().Single(x=>x.name=="Profile backdrop").texture as RenderTexture;Check(restored&&restored.IsCreated()&&restored!=lost,"Opening recovers a lost native backdrop target");
            Click("Join");Check(!page.IsVisible&&home.GetComponent<TeamsPage>().IsVisible,"Join routes the existing Teams page");home.GetComponent<TeamsPage>().Hide();Check(home.PresentationInteractable,"Teams close restores Home input");
            // A save-recovery dialog must not be displaced by a programmatic Profile open.
            bool retried=false;home.GetComponent<DailyGiftPage>().ShowError(()=>{retried=true;home.SetPresentation(true,true);});page.Show();Check(!page.IsVisible,"Profile cannot cover a protected save-recovery dialog");home.GetComponent<DailyGiftPage>().Request("claim");Check(retried,"Protected save-recovery callback is preserved");
            for(int n=1;n<Sizes.Length;n++)
            {
                var view=View();Selected(view).SetValue(view,SessionState.GetInt(Key+".first",0)+n);View().Repaint();yield return new WaitForSecondsRealtime(.8f);
                Check(Screen.width==Sizes[n].x&&Screen.height==Sizes[n].y,"Requested native viewport is active");home.SetChapterBackground(null);ClickHome();yield return null;Capture("Profile_"+Sizes[n].x+"x"+Sizes[n].y);
                if(n==1||n==2){var outer=page.transform.Find("Profile Canvas/Profile Safe Area").GetComponent<ScrollRect>();Check(outer.vertical&&outer.content.rect.height>outer.viewport.rect.height,"Short/tablet viewport retains full authored layout with scrolling");var inner=page.transform.Find("Profile Canvas/Profile Safe Area/Scrollable authored layout/Profile Panel/Collection/Collection viewport").GetComponent<ScrollRect>();Check(!inner.enabled,"A fitting avatar collection does not consume the page drag");var point=RectTransformUtility.WorldToScreenPoint(null,inner.viewport.TransformPoint(inner.viewport.rect.center));var data=new PointerEventData(EventSystem.current){button=PointerEventData.InputButton.Left,position=point,pressPosition=point};var hits=new List<RaycastResult>();EventSystem.current.RaycastAll(data,hits);Check(hits.Count>0,"Native profile raycast finds a scrollable surface");var handler=ExecuteEvents.GetEventHandler<IDragHandler>(hits[0].gameObject);Check(handler==outer.gameObject,"Native drag routing reaches the outer profile scroll");data.pointerPressRaycast=hits[0];ExecuteEvents.Execute(handler,data,ExecuteEvents.initializePotentialDrag);ExecuteEvents.Execute(handler,data,ExecuteEvents.beginDragHandler);data.position+=new Vector2(0,180);ExecuteEvents.Execute(handler,data,ExecuteEvents.dragHandler);ExecuteEvents.Execute(handler,data,ExecuteEvents.endDragHandler);Check(outer.verticalNormalizedPosition<.98f,"Native UGUI pointer drag scrolls the complete profile");Canvas.ForceUpdateCanvases();Capture(n==1?"Compact_Scrolled":"Tablet_Scrolled");if(n==1){Click("Edit name");Capture("Compact_Rename");Click("Cancel");}}
                page.Hide();
            }
            Check(JsonUtility.ToJson(host.Service.Read())==campaignBefore,"Appearance actions preserve all campaign/economy/inventory/receipt state");
            var retained=page.GetComponentsInChildren<RawImage>(true).Single(x=>x.name=="Profile backdrop").texture as RenderTexture;Destroy(home.gameObject);yield return null;Check(!retained||!retained.IsCreated(),"Destroying the owning Home releases the cached backdrop");
        }
        void RulesAndStore()
        {
            string clean,error;foreach(string valid in new[]{"Élodie","Дарья","Jose\u0301",new string('a',20),"<b>Ivan</b>"})Check(ProfileRules.TryName(valid,out clean,out error),"Valid name accepted as plain text");
            foreach(string invalid in new[]{"",new string('a',21),"a\nB","a\u202eB","x\ud800"})Check(!ProfileRules.TryName(invalid,out clean,out error),"Invalid name rejected");
            var isolated=new MemoryAppearancePreferences();var model=new ProfileStore(isolated);int changes=0;model.Changed+=_=>changes++;var snapshot=model.Snapshot;snapshot.displayName="Alias";Check(model.Snapshot.displayName=="Rainkeeper","Snapshots cannot mutate stored preferences");
            Check(!model.Select(0,"Unknown",out error)&&changes==0,"Unknown choice cannot mutate preferences");Check(model.Rename(" Élodie ",out error)&&changes==1,"Successful name change publishes one model event");Check(new ProfileStore(isolated).Snapshot.displayName=="Élodie","A new store reloads normalized preference state");
        }
        void ClickHome(){var label=home.GetComponentsInChildren<HomeControlLabel>().First(x=>x.action=="profile");label.GetComponent<Button>().onClick.Invoke();}
        Button Button(string name)=>page.GetComponentsInChildren<Button>().Single(x=>x.name==name);
        void Click(string name){var button=Button(name);Check(button.interactable,"Button enabled: "+name);button.onClick.Invoke();}
        InputField Input()=>page.GetComponentInChildren<InputField>();
        void Check(bool value,string name){report.checks++;if(!value)throw new InvalidOperationException(name);report.passed.Add(name);}
        void Capture(string name)
        {
            var canvases=FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID).Where(c=>c.isActiveAndEnabled&&c.renderMode==RenderMode.ScreenSpaceOverlay).ToArray();var cameras=canvases.Select(c=>c.worldCamera).ToArray();var distances=canvases.Select(c=>c.planeDistance).ToArray();
            var go=new GameObject("Native M71 capture camera");var camera=go.AddComponent<Camera>();go.transform.position=new Vector3(-10000,0,-10);camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;
            var previous=RenderTexture.active;var target=RenderTexture.GetTemporary(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);Texture2D pixels=null;
            try
            {
                camera.targetTexture=target;for(int i=0;i<canvases.Length;i++){canvases[i].renderMode=RenderMode.ScreenSpaceCamera;canvases[i].worldCamera=camera;canvases[i].planeDistance=1;}Canvas.ForceUpdateCanvases();camera.Render();home.SetChapterBackground(null);
                if(page.IsVisible)typeof(ProfilePage).GetMethod("Layout",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(page,null);
                Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;pixels=new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0);pixels.Apply();File.WriteAllBytes(Path.Combine(Output,name+".png"),pixels.EncodeToPNG());report.frames.Add(name+".png");
                if(page.IsVisible)foreach(var image in page.GetComponentsInChildren<RawImage>().Where(x=>x.name.StartsWith("Banner choice",StringComparison.Ordinal)))Check(Mathf.Abs(image.texture.width/(float)image.texture.height*image.uvRect.width/image.uvRect.height-image.rectTransform.rect.width/image.rectTransform.rect.height)<.001f,"Banner choice preserves source proportions");
                if(page.IsVisible)foreach(var text in page.GetComponentsInChildren<Text>().Where(t=>t.isActiveAndEnabled&&!string.IsNullOrEmpty(t.text))){Check(!text.supportRichText,"Profile displays plain text");foreach(char c in text.text)Check(char.IsWhiteSpace(c)||text.font.HasCharacter(c),"Profile font contains visible glyph");}
            }
            finally{for(int i=0;i<canvases.Length;i++){canvases[i].renderMode=RenderMode.ScreenSpaceOverlay;canvases[i].worldCamera=cameras[i];canvases[i].planeDistance=distances[i];}RenderTexture.active=previous;RenderTexture.ReleaseTemporary(target);if(pixels)Destroy(pixels);Destroy(go);Canvas.ForceUpdateCanvases();}
        }
        void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(message+"\n"+stack);}
        void Complete(string error){Application.logMessageReceived-=Log;if(error!=null)report.errors.Add(error);Check(PlayerPrefs.GetString(ProfileStore.Key,"<absent>")==ordinaryBefore,"Ordinary appearance preference is unchanged");GameLocale.Select(originalLocale);report.status=report.errors.Count==0?"PASS_NATIVE_M71_PROFILE":"FAIL_NATIVE_M71_PROFILE";File.WriteAllText(Path.Combine(Output,report.mode=="Restart"?"Native_Restart_Checks.json":"Native_Play_Checks.json"),JsonUtility.ToJson(report,true));}
        void OnDestroy(){Application.logMessageReceived-=Log;}
    }
}
#endif

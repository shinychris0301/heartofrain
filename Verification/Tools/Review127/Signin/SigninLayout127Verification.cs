#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.Rendering;
using UnityEngine.UI;
using HeartOfTheRain.App.AccountDesign;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.ServerAccount;

namespace HeartOfTheRain.Verification127 {
    // Private native rendering fixture. It never creates a profile/session or calls a provider.
    [InitializeOnLoad] public static class SigninLayout127Verification {
        const string Key="HOTR.SigninLayout127";
        const string OwnPath="Assets/Review127Diagnostics/Editor/SigninLayout127Verification.cs";
        const BindingFlags Private=BindingFlags.NonPublic|BindingFlags.Instance;
        static readonly string[] BoundPaths={
            "Assets/HeartOfTheRain/App/AccountDesign/AccountModal.cs",
            "Assets/HeartOfTheRain/App/ServerAccount/Runtime/ServerAccountModal83.cs",
            "Assets/HeartOfTheRain/App/ServerAccount/Runtime/ProviderAccountUI89.cs",
            "Assets/HeartOfTheRain/App/ServerAccount/Runtime/VkSigninUI102.cs",
            "Assets/HeartOfTheRain/App/ServerAccount/Runtime/ServerAccountText83.cs",OwnPath};
        static readonly Vector2Int[] Sizes={new Vector2Int(720,1600),new Vector2Int(320,480),new Vector2Int(1600,720),new Vector2Int(393,852),new Vector2Int(720,1600),new Vector2Int(320,568)};
        static readonly float[] Scales={0,0,0,.5f,3,5};
        static readonly string[] States={"Guest","PendingVk","ReadySame","ReadyOther","CommittingVk","PendingRecovery"};
        static readonly string[] MetricButtonNames={"VK registration or sign in","Check VK sign in","Cancel VK sign in","Refresh server status","Back up account","Copy recovery code","Resume server account","Recover server account","Start new guest","Sign out server account","Delete server account","Resume confirmed VK sign in","Confirm VK saved game","Account return"};
        [Serializable] sealed class Pin {public string path,sha256;}
        [Serializable] sealed class CaptionMetric {
            public string button,state;public int profile,locale,scroll,rawUsed,configuredMin,configuredMax,fontSize;
            public float pixelsPerUnit,normalizedUsed,settingsScale;public bool fontDynamic;
        }
        [Serializable] sealed class Report {
            public string status="RUNNING",utc,unity,project,scope;
            public int checks,cases,layouts,profiles=6,locales=5,states=6,bodyRaycastRejects,visibleBodyRaycasts;
            public bool actualNativeLayout=true,actualProvider=false,deviceTouched=false,playerPreferencesOrClipboardWritten=false,editorStartupCompletedBeforePlay;
            public List<Pin> sourceBindings=new List<Pin>();
            public List<string> errors=new List<string>(),frames=new List<string>();
            public CaptionMetric lastCaptionMetric;
        }
        // Explicit rendering data only. Calling any account/provider action fails the fixture.
        sealed class View:IManagedServerAccount83,IProviderAccount89,IProviderSignin102 {
            public event Action Changed {add{} remove{}}
            public readonly ServerAccountControls83 controls=new ServerAccountControls83{ready=true,canCopyRecovery=true,playerId=new string('a',32)};
            public VkSigninStatus102 signin;
            public int providerRefreshes;
            public ServerAccountControls83 Controls=>controls;
            public VkSigninStatus102 VkSignin=>signin?.Copy();
            public ProviderStatus89 VkStatus=>new ProviderStatus89{available=true,provider="vk",phase="Idle",playerId=controls.playerId};
            public bool ProviderBusy=>false;
            public AccountStatus Read()=>new AccountStatus{managed=true,serverSaved=controls.ready,online=true,playerId=controls.playerId,sync=AccountSync.Synced,confirmedServerSaveUtc=controls.ready?1793446914:0};
            public void RefreshProviders(){providerRefreshes++;}
            static void Denied(){throw new InvalidOperationException("LayoutFixtureAccountOperationDisallowed127");}
            public void Link(string provider,Action<AccountLinkResult> done)=>Denied();
            public void Refresh(Action<bool,string> done)=>Denied();public bool CopyRecovery(){Denied();return false;}
            public void Recover(string id,string code,bool yes,Action<bool,string> done)=>Denied();
            public void StartAnotherRecovery(string id,string code,bool yes,Action<bool,string> done)=>Denied();
            public void Logout(bool yes,Action<bool,string> done)=>Denied();public void Delete(bool yes,Action<bool,string> done)=>Denied();
            public void StartFresh(bool yes,Action<bool,string> done)=>Denied();public void Resume(Action<bool,string> done)=>Denied();public void EndAttempt(bool yes,Action<bool,string> done)=>Denied();
            public void BeginVk(Action<bool,string> done)=>Denied();public void CancelVk(Action<bool,string> done)=>Denied();
            public void BeginVkSignin(Action<bool,string> done)=>Denied();public void RefreshVkSignin(Action<bool,string> done)=>Denied();public void CancelVkSignin(Action<bool,string> done)=>Denied();
            public void CompleteVkSignin(string target,bool yes,Action<bool,string> done)=>Denied();
        }
        static Report report;static GameObject owner,events;static HomePage home;static AccountModal modal;static View view;
        static int profile,language,state,phase,scrollStep,waitFrames;static double began;static string loggedFailure;
        static string Project=>Path.GetFullPath(Path.Combine(Application.dataPath,".."));
        static string Output=>Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_SIGNIN_LAYOUT127_OUTPUT")??throw new InvalidOperationException("LayoutOutputRequired127"));
        static string Hash(string path){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
        static T Field<T>(object value,string name)=>(T)value.GetType().GetField(name,Private).GetValue(value);
        static void Check(bool ok,string code){report.checks++;if(!ok)throw new InvalidOperationException(code+"/"+profile+"/"+language+"/"+States[state]+"/"+scrollStep);}
        static object Group(){var a=typeof(Editor).Assembly;var t=a.GetType("UnityEditor.GameViewSizes");var instance=typeof(ScriptableSingleton<>).MakeGenericType(t).GetProperty("instance",BindingFlags.Public|BindingFlags.Static).GetValue(null);return t.GetMethod("GetGroup").Invoke(instance,new[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeGroupType"),SessionState.GetString(Key+".group","Standalone"))});}
        static EditorWindow GameView()=>EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));
        static PropertyInfo Selected(EditorWindow w)=>w.GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance);
        static void SetupSizes(){
            SessionState.SetString(Key+".group",EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android?"Android":EditorUserBuildSettings.activeBuildTarget==BuildTarget.iOS?"iOS":"Standalone");
            var g=Group();var w=GameView();var a=typeof(Editor).Assembly;SessionState.SetInt(Key+".previous",(int)Selected(w).GetValue(w));
            int first=(int)g.GetType().GetMethod("GetTotalCount").Invoke(g,null);SessionState.SetInt(Key+".first",first);SessionState.SetBool(Key+".sizesOwned",true);
            foreach(var s in Sizes){var e=Activator.CreateInstance(a.GetType("UnityEditor.GameViewSize"),BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance,null,new object[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),s.x,s.y,"HOTR Signin127 isolated"},null);g.GetType().GetMethod("AddCustomSize").Invoke(g,new[]{e});}
        }
        static void RestoreSizes(){
            if(!SessionState.GetBool(Key+".sizesOwned",false))return;
            var g=Group();int first=SessionState.GetInt(Key+".first",-1),total=(int)g.GetType().GetMethod("GetTotalCount").Invoke(g,null);
            if(first<0||total<first||total>first+Sizes.Length)throw new InvalidOperationException("GameViewOwnershipChanged127");
            var labels=(string[])g.GetType().GetMethod("GetDisplayTexts").Invoke(g,null);for(int i=first;i<total;i++)if(!labels[i].Contains("HOTR Signin127 isolated"))throw new InvalidOperationException("ForeignGameViewEntryPreserved127");
            Selected(GameView()).SetValue(GameView(),SessionState.GetInt(Key+".previous",0));for(int i=total-1;i>=first;i--)g.GetType().GetMethod("RemoveCustomSize").Invoke(g,new object[]{i});
            if((int)g.GetType().GetMethod("GetTotalCount").Invoke(g,null)!=first)throw new InvalidOperationException("GameViewCountNotRestored127");SessionState.EraseBool(Key+".sizesOwned");
        }
        static void SelectSize(){var w=GameView();Selected(w).SetValue(w,SessionState.GetInt(Key+".first",0)+profile);w.Repaint();waitFrames=4;}
        static SigninLayout127Verification(){
            if(!SessionState.GetBool(Key,false))return;
            loggedFailure=SessionState.GetString(Key+".nativeError","");if(loggedFailure.Length==0)loggedFailure=null;
            string saved=SessionState.GetString(Key+".report","");if(saved.Length>0)report=JsonUtility.FromJson<Report>(saved);
            Application.logMessageReceived+=Log;EditorApplication.update+=Tick;
            if(SessionState.GetBool(Key+".starting",false))EditorApplication.delayCall+=StartupDelayComplete;
        }
        public static void Run(){
            string p=Project.Replace('\\','/');if(!p.StartsWith("E:/.verification-cache/HOTR127/",StringComparison.OrdinalIgnoreCase)||!p.EndsWith("/Game",StringComparison.Ordinal))throw new InvalidOperationException("PrivateLayoutProjectRequired127");
            if(EditorApplication.isPlayingOrWillChangePlaymode)throw new InvalidOperationException("LayoutStartsFromEditMode127");
            if(SystemInfo.graphicsDeviceType==GraphicsDeviceType.Null)throw new InvalidOperationException("NativeGraphicsRequired127");
            Directory.CreateDirectory(Output);if(File.Exists(Path.Combine(Output,"Native.json")))throw new InvalidOperationException("FreshLayoutOutputRequired127");
            report=NewReport();loggedFailure=null;SessionState.EraseString(Key+".nativeError");SessionState.SetBool(Key+".errorPersistenceFailed",false);
            SessionState.SetBool(Key,true);SessionState.SetBool(Key+".starting",true);SessionState.SetBool(Key+".startupDelayComplete",false);SessionState.SetFloat(Key+".startupBegan",(float)EditorApplication.timeSinceStartup);
            SessionState.SetString(Key+".report",JsonUtility.ToJson(report));Application.logMessageReceived-=Log;Application.logMessageReceived+=Log;
            SessionState.SetInt(Key+".locale",GameLocale.Current);try{SetupSizes();}catch(Exception failure){report.errors.Add(failure.GetType().Name+":"+failure.Message);Finish(1);return;}
            // Let the normal delayed Editor search initialization run in Edit mode. Unity skips
            // first-use index creation while a Play transition is pending, then indexes an empty list.
            EditorApplication.delayCall+=StartupDelayComplete;EditorApplication.update-=Tick;EditorApplication.update+=Tick;
        }
        static Report NewReport(){
            var r=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,project=Project,scope="Actual Unity UGUI/font generation, camera-rendered account modal and native mask/raycast checks. Passive managed/VK view fixtures only. Six screen/scale profiles, five locales, six states; no profile/session/provider, touch, OAuth, purchase or cloud acceptance. Safe area is the Editor full-screen safe area; no notched-device claim."};
            foreach(string p in BoundPaths)r.sourceBindings.Add(new Pin{path=p,sha256=Hash(Path.Combine(Project,p))});return r;
        }
        static void StartupDelayComplete(){SessionState.SetBool(Key+".startupDelayComplete",true);}
        static void BeginReport(){
            began=EditorApplication.timeSinceStartup;if(report==null)report=NewReport();
            Check(report.editorStartupCompletedBeforePlay,"EditorStartupBeforePlay127");
            Check(UnityEngine.Object.FindObjectsOfType<HeartOfTheRain.App.Profile.PlayerProfileHost>(true).Length==0&&UnityEngine.Object.FindObjectsOfType<HeartOfTheRain.App.ServerGameplay.ServerGameSession>(true).Length==0,"EmptySceneHasNoProfileOrSession127");
            events=new GameObject("Isolated layout EventSystem127",typeof(EventSystem));SelectSize();
        }
        static void Log(string message,string stack,LogType type){
            if(type!=LogType.Error&&type!=LogType.Exception&&type!=LogType.Assert)return;
            loggedFailure="NativeUnityError127";SessionState.SetString(Key+".nativeError",loggedFailure);
            try{string path=Path.Combine(Output,"NativeError127.json");if(!File.Exists(path)){byte[] bytes=Encoding.UTF8.GetBytes("{\"error\":\"NativeUnityError127\"}\n");using(var stream=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.Read,1024,FileOptions.WriteThrough)){stream.Write(bytes,0,bytes.Length);stream.Flush(true);}}}
            catch{SessionState.SetBool(Key+".errorPersistenceFailed",true);}
        }
        static void CreateCase(){
            GameLocale.Select(language);owner=new GameObject("Passive account layout127");home=owner.AddComponent<HomePage>();home.enabled=false;
            var prefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab");Check(prefab!=null,"ActualHomePrefabAsset127");
            typeof(HomePage).GetField("assets",Private).SetValue(home,Field<HomePageAssets>(prefab.GetComponent<HomePage>(),"assets"));typeof(HomePage).GetField("uiScaleOverride",Private).SetValue(home,Scales[profile]);
            view=new View();if(state>0&&state<5)view.signin=new VkSigninStatus102{provider="vk",playerId=view.controls.playerId,phase=state==1?"Pending":state==4?"Committing":"Ready",targetPlayerId=state==2?view.controls.playerId:new string('b',32),requiresConfirmation=state==3,available=true};
            if(state==4||state==5){view.controls.ready=false;view.controls.blocked=view.controls.pending=true;view.controls.purpose=state==4?"vk":"recover";view.controls.needsRecoveryEntry=state==5;}
            modal=owner.AddComponent<AccountModal>();modal.Configure(home,AccountDesignAssets.Load());Check(modal.Show(view),"ActualModalShown127");
            Check(!home.enabled&&owner.GetComponent<HeartOfTheRain.App.Profile.PlayerProfileHost>()==null&&owner.GetComponent<HeartOfTheRain.App.ServerGameplay.ServerGameSession>()==null,"NoProfileSessionBootstrap127");
            Check(view.providerRefreshes==1,"OnlyPassiveProviderViewRefresh127");report.cases++;scrollStep=0;SetScroll();
        }
        static void SetScroll(){var s=Field<ScrollRect>(modal,"scroll");s.StopMovement();s.verticalNormalizedPosition=scrollStep==0?1:scrollStep==1?.5f:0;Canvas.ForceUpdateCanvases();waitFrames=2;}
        static Rect Bounds(RectTransform t){var c=new Vector3[4];t.GetWorldCorners(c);return Rect.MinMaxRect(c.Min(v=>v.x),c.Min(v=>v.y),c.Max(v=>v.x),c.Max(v=>v.y));}
        static bool Contains(Rect outer,Rect inner,float epsilon=1)=>inner.xMin>=outer.xMin-epsilon&&inner.xMax<=outer.xMax+epsilon&&inner.yMin>=outer.yMin-epsilon&&inner.yMax<=outer.yMax+epsilon;
        static Rect Intersect(Rect a,Rect b)=>Rect.MinMaxRect(Mathf.Max(a.xMin,b.xMin),Mathf.Max(a.yMin,b.yMin),Mathf.Min(a.xMax,b.xMax),Mathf.Min(a.yMax,b.yMax));
        static void RaycastRejected(Image graphic,Vector2 point){
            Check(!graphic.Raycast(point,null),"OutsideViewportNativeMaskReject127");var hits=new List<RaycastResult>();Field<Canvas>(modal,"canvas").GetComponent<GraphicRaycaster>().Raycast(new PointerEventData(EventSystem.current){position=point},hits);Check(!hits.Any(h=>h.gameObject==graphic.gameObject),"OutsideViewportNotInGraphicRaycasts127");report.bodyRaycastRejects++;
        }
        static void RecordCaptionMetric(Button button,Text text,TextGenerator generator){
            var settings=text.GetGenerationSettings(text.rectTransform.rect.size);
            report.lastCaptionMetric=new CaptionMetric{button=MetricButtonNames.Contains(button.name)?button.name:"OTHER_STATIC_LAYOUT_BUTTON",state=States[state],profile=profile,locale=language,scroll=scrollStep,rawUsed=generator.fontSizeUsedForBestFit,configuredMin=text.resizeTextMinSize,configuredMax=text.resizeTextMaxSize,fontSize=text.fontSize,pixelsPerUnit=text.pixelsPerUnit,normalizedUsed=generator.fontSizeUsedForBestFit/text.pixelsPerUnit,settingsScale=settings.scaleFactor,fontDynamic=text.font!=null&&text.font.dynamic};
            // Preserve numeric evidence before the existing failing assertion; no caption/user text.
            if(!File.Exists(Path.Combine(Output,"CaptionMetric127.json"))&&(generator.fontSizeUsedForBestFit<text.resizeTextMinSize||generator.fontSizeUsedForBestFit>text.resizeTextMaxSize)){
                byte[] bytes=Encoding.UTF8.GetBytes(JsonUtility.ToJson(report.lastCaptionMetric,true)+"\n");using(var stream=new FileStream(Path.Combine(Output,"CaptionMetric127.json"),FileMode.CreateNew,FileAccess.Write,FileShare.Read,1024,FileOptions.WriteThrough)){stream.Write(bytes,0,bytes.Length);stream.Flush(true);}
            }
        }
        static void CheckCaptionMetric(){
            var m=report.lastCaptionMetric;float unit=m.pixelsPerUnit;
            Check(m.fontDynamic&&m.rawUsed>0&&unit>0&&!float.IsNaN(unit)&&!float.IsInfinity(unit)&&!float.IsNaN(m.normalizedUsed)&&!float.IsInfinity(m.normalizedUsed)&&m.settingsScale>0&&!float.IsNaN(m.settingsScale)&&!float.IsInfinity(m.settingsScale)&&Mathf.Approximately(m.settingsScale,unit)&&m.configuredMin>0&&m.configuredMax>=m.configuredMin,"ActualDynamicFontScale127");
            // Native generator sizes are integer pixels. Compare in logical UI units, allowing
            // only the floor/ceil quantization of the configured limits (less than one pixel).
            float lower=Mathf.Floor(m.configuredMin*unit)/unit,upper=Mathf.Ceil(m.configuredMax*unit)/unit;
            Check(m.normalizedUsed>=lower&&m.normalizedUsed<=upper,"BoundedReadableButtonCaption127");
        }
        static void LayoutChecks(){
            Canvas.ForceUpdateCanvases();var panel=Field<RectTransform>(modal,"panel");var viewport=Field<RectTransform>(modal,"viewport");var footer=Field<RectTransform>(modal,"footer");var body=Field<RectTransform>(modal,"body");var header=Field<RectTransform>(modal,"header");var canvas=Field<Canvas>(modal,"canvas");
            Rect p=Bounds(panel),v=Bounds(viewport),f=Bounds(footer);float scale=canvas.scaleFactor;
            Check(panel.rect.width>0&&panel.rect.height>0&&viewport.rect.width>0&&viewport.rect.height>0&&body.rect.height>=viewport.rect.height,"PositiveNativeLayout127");
            Check(Contains(Screen.safeArea,p)&&Contains(p,v)&&Contains(p,f),"PanelViewportFooterInsideSafeArea127");
            Check(v.xMin-p.xMin>=27.9f*scale&&p.xMax-v.xMax>=27.9f*scale,"PaintedChromeHorizontalClearance127");
            Check(f.yMin-p.yMin>=21.9f*scale&&v.yMin-f.yMax>=11.9f*scale,"FixedFooterChromeAndBodyGap127");
            Check(viewport.GetComponent<RectMask2D>()&&!panel.GetComponent<RectMask2D>()&&!header.GetComponent<RectMask2D>(),"OnlyBodyMaskedHeaderArtPreserved127");
            Check(!canvas.GetComponentsInChildren<Button>().Any(b=>b.name.IndexOf("Google",StringComparison.OrdinalIgnoreCase)>=0)&&!body.GetComponentsInChildren<Text>().Any(t=>t.text.IndexOf("Google",StringComparison.OrdinalIgnoreCase)>=0),"UnsupportedGoogleControlsAndCopyAbsent127");
            if(profile==0&&state==0)Check(Mathf.Abs(panel.rect.width-369)<.1f&&Mathf.Abs(panel.rect.height-620)<.1f,"OriginalPortraitPanelSizeRetained127");
            var close=canvas.GetComponentsInChildren<Button>().Single(b=>b.name=="Account close");Check(Contains(Screen.safeArea,Bounds(close.GetComponent<RectTransform>()))&&close.transform.IsChildOf(header),"FloatingCloseInsideSafeArea127");
            foreach(var button in canvas.GetComponentsInChildren<Button>()){
                var rt=button.GetComponent<RectTransform>();var br=Bounds(rt);if(button.transform.IsChildOf(footer))Check(Contains(f,br)&&Contains(p,br),"FooterButtonContained127");
                foreach(var text in button.GetComponentsInChildren<Text>()){
                    Check(text.rectTransform.rect.width>0&&text.rectTransform.rect.height>0&&Contains(br,Bounds(text.rectTransform)),"ButtonLabelRectContained127");
                    using(var generator=new TextGenerator()){Check(generator.Populate(text.text,text.GetGenerationSettings(text.rectTransform.rect.size)),"ActualNativeFontGeneration127");Check(generator.characterCountVisible>=text.text.Length,"FullButtonCaptionVisible127");if(text.resizeTextForBestFit){RecordCaptionMetric(button,text,generator);CheckCaptionMetric();}}
                }
                if(!button.transform.IsChildOf(body))continue;var image=button.targetGraphic as Image;Check(image&&image.maskable,"BodyButtonMaskable127");Check(br.xMin>=v.xMin-.5f&&br.xMax<=v.xMax+.5f,"BodyButtonHorizontalClipBounds127");
                var visible=Intersect(br,v);if(visible.width>2&&visible.height>2){Check(image.Raycast(visible.center,null),"VisibleBodyButtonAcceptsNativeMask127");var hits=new List<RaycastResult>();canvas.GetComponent<GraphicRaycaster>().Raycast(new PointerEventData(EventSystem.current){position=visible.center},hits);Check(hits.Any(h=>h.gameObject==button.gameObject),"VisibleBodyButtonNativeGraphicRaycast127");report.visibleBodyRaycasts++;}
                if(br.yMax>v.yMax+1)RaycastRejected(image,new Vector2(br.center.x,(Mathf.Max(br.yMin,v.yMax)+br.yMax)/2));
                if(br.yMin<v.yMin-1)RaycastRejected(image,new Vector2(br.center.x,(br.yMin+Mathf.Min(br.yMax,v.yMin))/2));
            }
            var scroll=Field<ScrollRect>(modal,"scroll");Check(scroll.content==body&&scroll.viewport==viewport&&scroll.vertical&&!scroll.horizontal,"ActualVerticalScroll127");
            if(scrollStep==2){if(body.rect.height>viewport.rect.height+.1f)Check(scroll.verticalNormalizedPosition<.01f&&Bounds(body).yMin>=v.yMin-1,"LastRowsReachableByScrolling127");else Check(Contains(v,Bounds(body)),"NonOverflowingBodyFullyVisible127");}
            Check(view.providerRefreshes==1,"LayoutNeverDispatchesAccountAction127");report.layouts++;
            if(language==4&&(profile==0||profile==1&&state==3||profile==2&&state==3)&&(scrollStep==0||scrollStep==2))Capture("P"+profile+"_"+States[state]+"_"+(scrollStep==0?"Top":"Bottom")+".png");
        }
        static void Capture(string name){
            var canvas=Field<Canvas>(modal,"canvas");var original=canvas.renderMode;var originalCamera=canvas.worldCamera;float originalPlane=canvas.planeDistance;var go=new GameObject("Private modal capture127",typeof(Camera));var camera=go.GetComponent<Camera>();var target=new RenderTexture(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);var old=RenderTexture.active;Texture2D image=null;
            try{camera.enabled=false;camera.orthographic=true;camera.orthographicSize=Screen.height/2f;camera.transform.position=new Vector3(0,0,-1000);camera.nearClipPlane=.1f;camera.farClipPlane=2000;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.02f,.06f,.12f);camera.targetTexture=target;canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=100;Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;image=new Texture2D(Screen.width,Screen.height,TextureFormat.RGBA32,false);image.ReadPixels(new Rect(0,0,Screen.width,Screen.height),0,0);image.Apply();File.WriteAllBytes(Path.Combine(Output,name),image.EncodeToPNG());report.frames.Add(name);}
            finally{canvas.renderMode=original;canvas.worldCamera=originalCamera;canvas.planeDistance=originalPlane;camera.targetTexture=null;RenderTexture.active=old;target.Release();UnityEngine.Object.DestroyImmediate(target);if(image)UnityEngine.Object.DestroyImmediate(image);UnityEngine.Object.DestroyImmediate(go);Canvas.ForceUpdateCanvases();}
        }
        static void Tick(){
            try{
                if(loggedFailure!=null||SessionState.GetString(Key+".nativeError","").Length>0)throw new InvalidOperationException("NativeUnityError127");
                if(SessionState.GetBool(Key+".starting",false)){
                    if(EditorApplication.timeSinceStartup-SessionState.GetFloat(Key+".startupBegan",0)>60)throw new TimeoutException("EditorStartupReadyTimeout127");
                    if(EditorApplication.isPlayingOrWillChangePlaymode)throw new InvalidOperationException("UnexpectedPlayBeforeEditorStartup127");
                    if(EditorApplication.isCompiling||EditorApplication.isUpdating||!SessionState.GetBool(Key+".startupDelayComplete",false)||!SessionState.GetBool("IndexingOnEditorStartup_Started",false)||!File.Exists(Path.Combine(Project,"UserSettings/Search.index")))return;
                    report.editorStartupCompletedBeforePlay=true;SessionState.SetString(Key+".report",JsonUtility.ToJson(report));SessionState.SetBool(Key+".starting",false);
                    EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);if(SessionState.GetString(Key+".nativeError","").Length>0)throw new InvalidOperationException("NativeUnityError127");EditorApplication.isPlaying=true;return;
                }
                if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
                if(events==null){BeginReport();return;}if(EditorApplication.timeSinceStartup-began>420)throw new TimeoutException("NativeLayoutTimeout127");
                if(waitFrames-->0)return;if(Screen.width!=Sizes[profile].x||Screen.height!=Sizes[profile].y)return;
                if(phase==0){CreateCase();phase=1;return;}
                LayoutChecks();if(++scrollStep<3){SetScroll();return;}
                UnityEngine.Object.DestroyImmediate(owner);owner=null;modal=null;phase=0;
                if(++state<States.Length)return;state=0;if(++language<5)return;language=0;if(++profile<Sizes.Length){SelectSize();return;}Finish(0);
            }catch(Exception failure){if(report==null)report=NewReport();report.errors.Add(failure.GetType().Name+":"+failure.Message);try{if(modal)Capture("Failure.png");}catch{}Finish(1);}
        }
        static void Finish(int code){
            if(loggedFailure!=null){report.errors.Add(loggedFailure);code=1;}
            if(SessionState.GetBool(Key+".errorPersistenceFailed",false)){report.errors.Add("NativeErrorEvidenceWriteFailed127");code=1;}
            EditorApplication.update-=Tick;EditorApplication.delayCall-=StartupDelayComplete;Application.logMessageReceived-=Log;if(owner)UnityEngine.Object.DestroyImmediate(owner);if(events)UnityEngine.Object.DestroyImmediate(events);
            try{GameLocale.Select(SessionState.GetInt(Key+".locale",4));RestoreSizes();}
            catch(Exception){report.errors.Add("GameViewRestoreFailed127");code=1;}
            SessionState.EraseBool(Key);foreach(var pin in report.sourceBindings)if(Hash(Path.Combine(Project,pin.path))!=pin.sha256){report.errors.Add("SourceChangedDuringNativeLayout127");code=1;}
            if(code==0&&(!report.editorStartupCompletedBeforePlay||report.cases!=180||report.layouts!=540||report.visibleBodyRaycasts==0||report.bodyRaycastRejects==0)){report.errors.Add("NativeLayoutCoverageIncomplete127");code=1;}
            report.status=code==0?"PASS_NATIVE_SIGNIN_LAYOUT127":"FAIL_NATIVE_SIGNIN_LAYOUT127";Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"Native.json"),JsonUtility.ToJson(report,true)+"\n",new UTF8Encoding(false));if(Application.isBatchMode)EditorApplication.Exit(code);else EditorApplication.isPlaying=false;
        }
        public static void RequireAcceptedReport(string reportPath){
            if(string.IsNullOrWhiteSpace(reportPath))throw new InvalidOperationException("NativeLayoutReportRequired127");var r=JsonUtility.FromJson<Report>(File.ReadAllText(reportPath));
            if(r==null||r.status!="PASS_NATIVE_SIGNIN_LAYOUT127"||!r.actualNativeLayout||!r.editorStartupCompletedBeforePlay||r.actualProvider||r.deviceTouched||r.errors==null||r.errors.Count!=0||r.cases!=180||r.layouts!=540||r.visibleBodyRaycasts<=0||r.bodyRaycastRejects<=0||r.sourceBindings==null||r.sourceBindings.Count!=BoundPaths.Length||r.project!=Project)throw new InvalidOperationException("AcceptedNativeLayoutReportRequired127");
            foreach(string path in BoundPaths){var pin=r.sourceBindings.SingleOrDefault(x=>x.path==path);if(pin==null||pin.sha256!=Hash(Path.Combine(Project,path)))throw new InvalidOperationException("NativeLayoutReportSourceStale127");}
        }
    }
}
#endif

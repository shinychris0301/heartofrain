#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using HeartOfTheRain.App.AccountDesign;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.ServerAccount;
using HeartOfTheRain.App.ServerGameplay;

namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class ProviderIdentity89Verification {
        const string Key="HOTR.Provider89.Native";const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        [Serializable] sealed class Report {
            public string status,utc,unity,scope="Pinned Unity Editor/Play Mode parser and actual AccountModal UGUI with in-memory synthetic local/managed provider fixtures. No ordinary profile, PlayerPrefs, HTTP, VK account, SDK, Android, real browser or provider acceptance.";
            public int checks,cases;public List<string> failures=new List<string>(),errors=new List<string>(),captures=new List<string>();
        }
        sealed class Local:IAccountService {
            public AccountStatus Read()=>new AccountStatus{playerId=new string('a',32),localSaved=true,online=true};
            public void Link(string provider,Action<AccountLinkResult> done){throw new InvalidOperationException("Unconfigured provider must not run");}
        }
        sealed class Managed:IManagedServerAccount83,IProviderAccount89 {
            // Passive fixture: state is set explicitly by each test; it emits no changes.
            public event Action Changed { add { } remove { } }
            public ProviderStatus89 value;public int begun,cancelled,refreshed;
            public ProviderStatus89 VkStatus=>value?.Copy();public bool ProviderBusy=>false;
            public ServerAccountControls83 Controls=>new ServerAccountControls83{ready=true,playerId=new string('a',32)};
            public AccountStatus Read()=>new AccountStatus{managed=true,serverSaved=true,confirmedServerSaveUtc=100,playerId=new string('a',32),online=true,sync=AccountSync.Synced};
            public void Link(string provider,Action<AccountLinkResult> done){throw new InvalidOperationException("Google remains unavailable");}
            public void RefreshProviders(){refreshed++;}
            public void BeginVk(Action<bool,string> done){begun++;done(true,null);}
            public void CancelVk(Action<bool,string> done){cancelled++;done(true,null);}
            public void Refresh(Action<bool,string> done)=>done(true,null);public bool CopyRecovery()=>false;
            public void Recover(string id,string code,bool confirmed,Action<bool,string> done)=>done(false,"Unused");
            public void StartAnotherRecovery(string id,string code,bool confirmed,Action<bool,string> done)=>done(false,"Unused");
            public void Logout(bool confirmed,Action<bool,string> done)=>done(false,"Unused");public void Delete(bool confirmed,Action<bool,string> done)=>done(false,"Unused");
            public void StartFresh(bool confirmed,Action<bool,string> done)=>done(false,"Unused");public void Resume(Action<bool,string> done)=>done(false,"Unused");public void EndAttempt(bool confirmed,Action<bool,string> done)=>done(false,"Unused");
        }
        static Report report;static string output;static double began;static int previousLocale;static bool ran;
        static object Group(){var asm=typeof(Editor).Assembly;var type=asm.GetType("UnityEditor.GameViewSizes");var singleton=typeof(ScriptableSingleton<>).MakeGenericType(type).GetProperty("instance",BindingFlags.Static|BindingFlags.Public).GetValue(null);string group=EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android?"Android":EditorUserBuildSettings.activeBuildTarget==BuildTarget.iOS?"iOS":"Standalone";return type.GetMethod("GetGroup").Invoke(singleton,new[]{Enum.Parse(asm.GetType("UnityEditor.GameViewSizeGroupType"),group)});}
        static EditorWindow View()=>EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));
        static void Size(){var group=Group();var view=View();var property=view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic);SessionState.SetInt(Key+".previous",(int)property.GetValue(view));int count=(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null);SessionState.SetInt(Key+".custom",count);var asm=typeof(Editor).Assembly;var size=Activator.CreateInstance(asm.GetType("UnityEditor.GameViewSize"),BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance,null,new object[]{Enum.Parse(asm.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),720,1600,"HOTR Provider89"},null);group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{size});property.SetValue(view,count);view.Repaint();}
        static void RestoreSize(){try{var view=View();view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(view,SessionState.GetInt(Key+".previous",0));Group().GetType().GetMethod("RemoveCustomSize").Invoke(Group(),new object[]{SessionState.GetInt(Key+".custom",0)});}catch(Exception e){report.errors.Add("Size cleanup: "+e.GetType().Name);}}
        static ProviderIdentity89Verification(){if(SessionState.GetBool(Key,false)){report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};output=Environment.GetEnvironmentVariable("HOTR_PROVIDER89_OUT");if(string.IsNullOrEmpty(output))output=Path.GetFullPath("../Verification/Evidence/RegionAccounts89/Native/Provider89");Directory.CreateDirectory(output);began=EditorApplication.timeSinceStartup;previousLocale=GameLocale.Current;EditorApplication.update+=Tick;Application.logMessageReceived+=Log;}}
        public static void Run(){SessionState.SetBool(Key,true);Size();EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorApplication.isPlaying=true;}
        static void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(message+"\n"+stack);}
        static void Check(bool ok,string label){report.checks++;if(!ok)throw new InvalidOperationException(label);}
        static void Reject(Action action,string label){bool rejected=false;try{action();}catch(Exception){rejected=true;}Check(rejected,label);}
        static void Case(string name,Action action){report.cases++;try{action();}catch(Exception e){report.failures.Add(name+": "+e);}}
        static void Tick(){
            if(!EditorApplication.isPlaying||EditorApplication.isCompiling){if(EditorApplication.timeSinceStartup-began>180)Finish();return;}
            if(ran)return;ran=true;
            Case("Exact external browser destination",()=>{
                Check(ProviderIdentityClient89.SafeAuthorizeUrl("https://id.vk.ru/authorize?state=example"),"Canonical VK HTTPS URL accepted");
                Check(ProviderIdentityClient89.SafeAuthorizeUrl("https://id.vk.com/authorize?state=example"),"Existing pending VK URL accepted");
                Check(!ProviderIdentityClient89.SafeAuthorizeUrl("https://id.vk.ru.evil.example/authorize"),"Canonical-host lookalike rejected");
                foreach(string bad in new[]{"http://id.vk.com/authorize","https://id.vk.com.evil.example/authorize","https://id.vk.com@evil.example/authorize","https://user@id.vk.com/authorize","https://id.vk.com/authorize#secret","https://id.vk.com:444/authorize","https://id.vk.com/oauth2/auth"," https://id.vk.com/authorize","javascript:alert(1)","https://id.vk.com/authorize\n"})Check(!ProviderIdentityClient89.SafeAuthorizeUrl(bad),"Reject unsafe URL "+bad.Replace("\n","<newline>"));
            });
            Case("Bound status parser",()=>{
                var value=new ProviderStatus89{playerId=new string('a',32),provider="vk",phase="Pending",flowId=new string('b',32),requestId=new string('c',32),authorizeUrl="https://id.vk.com/authorize?state=fixture",available=true,samePlayer=true,serverUtc=100,expiresAt=700};
                string json=JsonUtility.ToJson(value);Check(ProviderIdentityClient89.ParseStatus(json,value.playerId).Pending,"Existing pending protocol parsed");
                Check(ProviderIdentityClient89.ParseStatus(json.Replace("id.vk.com","id.vk.ru"),value.playerId).Pending,"Canonical pending protocol parsed");
                Reject(()=>ProviderIdentityClient89.ParseStatus(json,new string('d',32)),"Different player rejected");
                foreach(string bad in new[]{json.Replace("\"samePlayer\":true","\"samePlayer\":false"),json.Replace("\"available\":true","\"available\":\"true\""),json.Replace("\"linked\":false,",""),json.Replace("\"available\":true","\"available\":true,\"available\":false"),json.Replace("\"serverUtc\":100","\"serverUtc\":0"),json.Replace("\"expiresAt\":700","\"expiresAt\":100"),json.Replace("id.vk.com","evil.example"),json.Replace("\"provider\":\"vk\"","\"provider\":\"google\"")})Reject(()=>ProviderIdentityClient89.ParseStatus(bad,value.playerId),"Malformed or unbound status rejected");
            });
            Case("Provider status never fabricates cloud save",()=>{var account=new AccountStatus{managed=true,serverSaved=true,confirmedServerSaveUtc=100,sync=AccountSync.Synced};Check(account.ServerSaved&&!account.linked&&!account.CloudSaved,"Managed guest remains distinct from OAuth and cloud sync");});
            Case("Provider ownership fence",()=>{
                var owner=new GameObject("Provider89 owner fence");try{var gateway=owner.AddComponent<ServerGameSession>();using(var service=new ServerAccountService83(gateway)){
                    typeof(ServerAccountService83).GetField("providerOwner",Private).SetValue(service,new string('a',32));
                    typeof(ServerAccountService83).GetField("vkStatus",Private).SetValue(service,new ProviderStatus89{linked=true,available=true,phase="Pending",flowId=new string('b',32),authorizeUrl="https://id.vk.com/authorize?state=fixture"});
                    Check(service.VkStatus==null,"Previous owner's provider status cannot leak into a closed/different session");bool called=false,accepted=true;service.BeginVk((ok,error)=>{called=true;accepted=ok;});Check(called&&!accepted,"Previous owner's authorization URL cannot open for another session");
                    called=false;service.CancelVk((ok,error)=>{called=true;accepted=ok;});Check(called&&!accepted,"Previous owner's provider flow cannot be cancelled by a different session");
                }}finally{UnityEngine.Object.DestroyImmediate(owner);}
            });
            foreach(int language in new[]{0,1,2,3,4}){
                int locale=language;
                Case("Local unavailable provider row "+locale,()=>UiCase(locale,null,"Local_"+locale));
                foreach(string phase in new[]{"Idle","Pending","Exchanging","Linked","Conflict"}){string selected=phase;Case("Managed provider "+selected+" "+locale,()=>UiCase(locale,selected,selected+"_"+locale));}
            }
            Finish();
        }
        static void UiCase(int locale,string phase,string name){
            GameLocale.Select(locale);GameObject owner=null,eventOwner=null;AccountModal modal=null;
            try{
                owner=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab"));var home=owner.GetComponent<HomePage>();home.enabled=false;
                if(!EventSystem.current)eventOwner=new GameObject("Provider89 isolated EventSystem",typeof(EventSystem));
                modal=owner.AddComponent<AccountModal>();modal.Configure(home,AccountDesignAssets.Load());Managed fixture=null;
                IAccountService service=phase==null?(IAccountService)new Local():(fixture=new Managed{value=new ProviderStatus89{playerId=new string('a',32),provider="vk",available=true,phase=phase,linked=phase=="Linked",linkedAt=phase=="Linked"?100:0,samePlayer=true,flowId=new string('b',32),requestId=new string('c',32),expiresAt=700,serverUtc=100}});
                Check(modal.Show(service),"Modal opens with isolated account source");Canvas.ForceUpdateCanvases();
                var canvas=(Canvas)typeof(AccountModal).GetField("canvas",Private).GetValue(modal);var buttons=canvas.GetComponentsInChildren<Button>();
                Check(!buttons.Any(b=>b.name=="Provider Google"||b.name=="Server provider Google"),"Unsupported Google sign-in is hidden");var vk=buttons.Single(b=>b.name==(phase==null?"Provider VK":"Server provider VK"));
                Check(vk.interactable==(phase!=null&&phase!="Linked"&&phase!="Exchanging"),"VK availability follows provider phase");
                Check(canvas.GetComponentsInChildren<Text>().Any(t=>t.text.Contains("VK")),"VK label renders in every supported language");
                var body=(RectTransform)typeof(AccountModal).GetField("body",Private).GetValue(modal);var viewport=(RectTransform)typeof(AccountModal).GetField("viewport",Private).GetValue(modal);Check(viewport.GetComponent<RectMask2D>()&&viewport.GetComponent<ScrollRect>().vertical,"Larger account content remains masked and scrollable");
                foreach(var button in new[]{vk}){var rect=(RectTransform)button.transform;Check(rect.sizeDelta.x<=body.rect.width+.01f,"Provider control stays inside body width");}
                if(phase=="Pending")Check(buttons.Any(b=>b.name=="Cancel VK signup"),"Pending browser operation exposes cancellation");
                if(locale==4&&(phase==null||phase=="Idle"||phase=="Pending"||phase=="Linked"||phase=="Conflict"))Capture(canvas,name+".png");
                if(phase=="Idle"){modal.Request("vk-signup");Check(fixture.begun==1&&!modal.IsBusy,"VK button delegates to model/service only");}
                if(phase=="Pending"){modal.Request("vk-cancel");Check(fixture.cancelled==1&&!modal.IsBusy,"Cancellation delegates to provider service");}
                modal.Request("Google");if(fixture!=null)Check(fixture.begun==(phase=="Idle"?1:0),"Google cannot invoke VK");
                if(phase==null){modal.Request("VK");Check(!modal.IsBusy&&!modal.Snapshot.linked,"Local VK cannot claim signup or mutate progress");}
            }finally{if(owner)UnityEngine.Object.DestroyImmediate(owner);if(eventOwner)UnityEngine.Object.DestroyImmediate(eventOwner);}
        }
        static void Capture(Canvas canvas,string filename){
            var go=new GameObject("Provider89 native UI capture");var camera=go.AddComponent<Camera>();camera.enabled=false;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.02f,.07f,.15f,1);camera.transform.position=new Vector3(-10000,0,-10);camera.orthographic=true;camera.nearClipPlane=.1f;camera.farClipPlane=100;
            var target=new RenderTexture(Screen.width,Screen.height,24);target.Create();var mode=canvas.renderMode;var previous=canvas.worldCamera;float distance=canvas.planeDistance;var active=RenderTexture.active;Texture2D pixels=null;
            try{camera.targetTexture=target;canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=1;Canvas.ForceUpdateCanvases();camera.Render();Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;pixels=new Texture2D(target.width,target.height,TextureFormat.RGB24,false);pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0);pixels.Apply();File.WriteAllBytes(Path.Combine(output,filename),pixels.EncodeToPNG());report.captures.Add(filename);}
            finally{canvas.renderMode=mode;canvas.worldCamera=previous;canvas.planeDistance=distance;camera.targetTexture=null;RenderTexture.active=active;if(pixels)UnityEngine.Object.DestroyImmediate(pixels);target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(go);}
        }
        static void Finish(){EditorApplication.update-=Tick;GameLocale.Select(previousLocale);if(report==null)return;RestoreSize();Application.logMessageReceived-=Log;SessionState.SetBool(Key,false);int code=report.failures.Count==0&&report.errors.Count==0&&report.checks>0?0:1;report.status=code==0?"PASS_NATIVE_PROVIDER_IDENTITY89":"FAIL_NATIVE_PROVIDER_IDENTITY89";File.WriteAllText(Path.Combine(output,"Report.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(code);}
    }
}
#endif

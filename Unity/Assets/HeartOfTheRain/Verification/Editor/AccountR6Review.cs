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
using UnityEngine.SceneManagement;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.AppSettings;
using HeartOfTheRain.App.AccountDesign;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.Settings;
namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class AccountR6Review {
        const string Key="HOTR.AccountR6";const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static string Output=>Path.GetFullPath("../Verification/Evidence/AccountR6");
        [Serializable] class Report {public string utc,status,error,scope="Native Unity Editor/Play Mode, isolated campaign/appearance/settings and explicit fake account service for linked/sync/callback cases. Camera-rendered UGUI; not Android, physical touch or real provider/cloud integration.";public int checks,layouts;public List<string> frames=new List<string>();}
        sealed class SettingsStore:ISettingsStore {public readonly Dictionary<string,int> values=new Dictionary<string,int>();public int Read(string k,int f)=>values.TryGetValue(k,out int v)?v:f;public void Write(string k,int v){values[k]=v;}public void Flush(){}}
        sealed class AccountFixture:IAccountService {public AccountStatus status=new AccountStatus{localSaved=true,online=true,playerId="native-fixture-id"};public Action<AccountLinkResult> done;public int links,reads;public AccountStatus Read(){reads++;return status.Copy();}public void Link(string provider,Action<AccountLinkResult> callback){links++;done=callback;}}
        static Report report;static double began,next;static int index,phase,originalLocale;static HomePage home;static AppSettingsPage settings;static AccountFixture source;static SettingsStore preferences;
        static readonly Vector2Int[] Sizes={new Vector2Int(393,852),new Vector2Int(320,480),new Vector2Int(768,1024),new Vector2Int(900,2000),new Vector2Int(320,568),new Vector2Int(844,390)};
        static object Group()=>typeof(ProfileM71Verification).GetMethod("Group",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);
        static EditorWindow View()=>EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));
        static void Size(int n){var view=View();view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).SetValue(view,SessionState.GetInt("HOTR.M71.Verification.first",0)+n);view.Repaint();next=EditorApplication.timeSinceStartup+.4;}
        static AccountR6Review(){if(SessionState.GetBool(Key,false)){report=new Report{utc=DateTime.UtcNow.ToString("o")};began=EditorApplication.timeSinceStartup;originalLocale=GameLocale.Current;EditorApplication.update+=Tick;Application.logMessageReceived+=Log;SceneManager.sceneLoaded+=IsolateSettings;}}
        static void IsolateSettings(Scene scene,LoadSceneMode mode){foreach(var p in UnityEngine.Object.FindObjectsByType<AppSettingsPage>(UnityEngine.FindObjectsSortMode.InstanceID))p.VerificationStore=new SettingsStore();}
        public static void Prepare(){
            AssetDatabase.Refresh();string path="Assets/HeartOfTheRain/Resources/HOTR_Account/Config.asset";Directory.CreateDirectory(Path.GetDirectoryName(path));AssetDatabase.Refresh();var a=AssetDatabase.LoadAssetAtPath<AccountDesignAssets>(path);if(!a){a=ScriptableObject.CreateInstance<AccountDesignAssets>();AssetDatabase.CreateAsset(a,path);}
            Sprite Sprite(string file)=>AssetDatabase.LoadAssetAtPath<Sprite>("Assets/HeartOfTheRain/"+file);
            a.chrome=Sprite("App/AccountDesign/Art/AccountChrome.png");a.close=Sprite("App/AccountDesign/Art/Close.png");a.google=Sprite("App/AccountDesign/Art/Provider_Google.png");a.apple=Sprite("App/AccountDesign/Art/Provider_Apple.png");
            a.primary=Sprite("App/Profile/Art/Primary.png");a.banner=Sprite("App/Profile/Art/DesignKitR1/Banner_Village_R3.png");a.check=Sprite("App/Profile/Art/CheckSource.png");a.shield=Sprite("App/Profile/Art/Team.png");
            a.titleFont=AssetDatabase.LoadAssetAtPath<Font>("Assets/HeartOfTheRain/App/Home/Fonts/HomeRounded-Black.ttf");a.bodyFont=AssetDatabase.LoadAssetAtPath<Font>("Assets/HeartOfTheRain/App/Home/Fonts/HomeRounded-ExtraBold.ttf");
            if(!a.chrome||!a.close||!a.google||!a.apple||!a.primary||!a.banner||!a.check||!a.shield||!a.titleFont||!a.bodyFont)throw new Exception("Account asset binding missing");EditorUtility.SetDirty(a);AssetDatabase.SaveAssets();Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"Import.json"),"{\"status\":\"PASS_NATIVE_ACCOUNT_ASSET_BINDINGS\"}");
        }
        public static void Run(){
            SessionState.SetBool(Key,true);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");UnityEngine.Object.FindFirstObjectByType<FirstStartPage>().reviewAlways=true;
            // Inject before Start so preferences never write into ordinary PlayerPrefs.
            var page=UnityEngine.Object.FindFirstObjectByType<AppSettingsPage>();page.VerificationStore=new SettingsStore();
            typeof(ProfileM71Verification).GetMethod("SetupSizes",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);var group=Group();var asm=typeof(Editor).Assembly;var extra=Activator.CreateInstance(asm.GetType("UnityEditor.GameViewSize"),BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance,null,new object[]{Enum.Parse(asm.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),844,390,"HOTR Account landscape layout"},null);group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{extra});EditorApplication.isPlaying=true;
        }
        static void Check(bool ok,string message){report.checks++;if(!ok)throw new Exception(message);}
        static void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.error=message+"\n"+stack;}
        static void Click(string name){Field<Canvas>(settings.AccountView,"canvas").GetComponentsInChildren<Button>().Single(b=>b.name==name).onClick.Invoke();}
        static T Field<T>(object o,string key)=>(T)o.GetType().GetField(key,Private).GetValue(o);
        static void Rules(){
            for(int lang=0;lang<5;lang++){GameLocale.Select(lang);foreach(var key in new[]{"linkUnavailable","syncPending","syncFailed","localUnverified","saveUnavailable","syncFailedBadge"})Check(!AccountText.T(key).Contains("?"),"Localized availability copy retains Unicode "+lang+"/"+key);}GameLocale.Select(0);
            Check(settings.VerificationStore is SettingsStore,"Native preference store isolated before Start");preferences=(SettingsStore)settings.VerificationStore;var art=AccountDesignAssets.Load();Check(art.chrome.border==new Vector4(186,170,186,288)&&art.primary.border==new Vector4(300,240,300,240),"Authored slice borders retained");Check(art.close.border==Vector4.zero&&art.close.texture.width==1254&&art.chrome.texture.width==1392,"Original close/chrome dimensions retained");source=new AccountFixture();settings.AccountService=source;home.NavigationRequested.Invoke("settings");Check(settings.IsVisible,"Gear opens Settings");
            string appearanceError;Check(Field<ProfileStore>(home.GetComponent<ProfilePage>(),"store").Select(0,"Dariya",out appearanceError),"Select isolated appearance before account review");var before=home.GetComponent<PlayerProfileHost>().Service.Read();string campaign=JsonUtility.ToJson(before);var look=JsonUtility.ToJson(home.GetComponent<ProfilePage>().Snapshot);
            settings.Request("toggle:music");settings.Request("toggle:sound");settings.Request("toggle:hints");Check(!settings.ReviewSession.Preferences.Music&&!settings.ReviewSession.Preferences.Sound&&!settings.ReviewSession.Preferences.Hints,"Existing toggles respond");
            var scroll=Field<ScrollRect>(settings,"scroll");scroll.verticalNormalizedPosition=.86f;float pos=scroll.verticalNormalizedPosition;settings.Request("save-progress");Check(settings.AccountView.IsVisible&&settings.AccountView.ScreenKey=="save","Guest opens save modal");Check(!Field<CanvasGroup>(settings,"fade").blocksRaycasts,"Settings input suspended");
            Check(!Field<Canvas>(settings.AccountView,"canvas").GetComponentsInChildren<Button>().Any(b=>b.name=="Provider Google"),"Unsupported Google sign-in is hidden");settings.Request("close");Check(settings.IsVisible&&settings.AccountView.IsVisible,"Underlying close cannot bypass account modal");Click("Account return");
            Check(settings.IsVisible&&!settings.AccountView.IsVisible,"Not now returns to Settings");Check(Mathf.Abs(scroll.verticalNormalizedPosition-pos)<.005f,"Settings scroll position retained");Check(EventSystem.current.currentSelectedGameObject.name=="save-progress","Focus restored to save entry");Check(!settings.ReviewSession.Preferences.Music&&!settings.ReviewSession.Preferences.Sound&&!settings.ReviewSession.Preferences.Hints,"Toggles retained across modal");
            source.status.linked=true;source.status.provider="Google";source.status.sync=AccountSync.Synced;source.status.confirmedCloudSaveUtc=1780000000;settings.Request("save-progress");Check(settings.AccountView.ScreenKey=="connected"&&settings.AccountView.Snapshot.CloudSaved,"Verified linked account opens status");Check(Field<Canvas>(settings.AccountView,"canvas").GetComponentsInChildren<Text>().Any(t=>t.name=="Cloud timestamp"&&t.text.Contains("UTC")),"Real confirmed timestamp displayed");Click("Account close");
            source.status.sync=AccountSync.Pending;settings.Request("save-progress");Check(!settings.AccountView.Snapshot.CloudSaved&&settings.AccountView.Snapshot.StatusKey=="syncPending","Pending sync never says cloud saved");settings.AccountView.Hide();
            source.status.sync=AccountSync.Failed;settings.Request("save-progress");Check(settings.AccountView.Snapshot.StatusKey=="syncFailed","Failed sync retained");settings.AccountView.Hide();
            source.status.sync=AccountSync.Synced;source.status.confirmedCloudSaveUtc=0;Check(!source.status.CloudSaved,"Missing confirmation cannot prove cloud save");source.status.confirmedCloudSaveUtc=long.MaxValue;Check(!source.status.CloudSaved,"Invalid timestamp cannot prove cloud save");
            source.status=new AccountStatus{localSaved=true,online=false,playerId=before.playerId};settings.Request("save-progress");Check(settings.AccountView.ScreenKey=="offline","Offline guest opens local-save view");settings.AccountView.Request("back");Check(settings.IsVisible,"Account Back preserves Settings");
            source.status.online=true;source.status.canLink=true;settings.Request("save-progress");settings.AccountView.Request("Google");settings.AccountView.Request("Google");Check(source.links==1&&settings.AccountView.IsBusy,"Provider double tap blocked");var stale=source.done;settings.AccountView.Hide();settings.Request("save-progress");stale(AccountLinkResult.Failed);Check(settings.AccountView.ScreenKey=="save"&&!settings.AccountView.IsBusy,"Late callback cannot replace reopened modal");settings.AccountView.Request("Google");source.done(AccountLinkResult.Cancelled);Check(settings.AccountView.ScreenKey=="save"&&!settings.AccountView.IsBusy,"Cancellation returns quietly");settings.AccountView.Request("Google");source.done(AccountLinkResult.Failed);Check(settings.AccountView.ScreenKey=="error","Provider failure shows safe error");settings.AccountView.Hide();
            Check(campaign==JsonUtility.ToJson(home.GetComponent<PlayerProfileHost>().Service.Read())&&look==JsonUtility.ToJson(home.GetComponent<ProfilePage>().Snapshot),"Account navigation never mutates campaign/economy/appearance");
            settings.Hide();home.NavigationRequested.Invoke("profile");Check(home.GetComponent<ProfilePage>().IsVisible,"Home avatar still opens Profile");home.GetComponent<ProfilePage>().Hide();
            foreach(string key in new[]{"inventory","language","help","follow"}){settings.Show();settings.Request(key);Check(settings.ReviewSession.Page==key,"Existing Settings route retained: "+key);settings.Request("back");settings.Hide();}
            settings.AccountService=new LocalAccountService(home);var real=settings.AccountService.Read();Check(real.playerId==before.playerId&&!real.linked&&real.localSaved&&!real.canLink,"Default service reports verified local identity only");
        }
        static void LayoutChecks(){
            var accountCanvas=Field<Canvas>(settings.AccountView,"canvas");var pointer=new PointerEventData(EventSystem.current){position=new Vector2(Screen.width*.5f,Screen.height*.5f)};var hits=new List<RaycastResult>();EventSystem.current.RaycastAll(pointer,hits);Check(hits.Count>0&&hits[0].gameObject.transform.IsChildOf(accountCanvas.transform),"Foremost native raycast belongs to account modal: "+string.Join(",",hits.Select(h=>h.gameObject.name+"/"+h.depth)));
            Check(Field<ScrollRect>(settings.AccountView,"scroll").verticalScrollbar.handleRect.rect.width<=4,"Scrollbar thumb remains narrow");
            var frame=AppSettingsLayout.Build(Screen.width/home.CurrentUIScale,Screen.height/home.CurrentUIScale,settings.ReviewSession);var entry=frame.content.elements.Single(e=>e.id=="save-progress");var inventory=frame.content.elements.Single(e=>e.id=="inventory");Check(entry.height==60&&entry.y+60<inventory.y,"Save entry precedes Inventory without overlap");
            foreach(var t in Field<Canvas>(settings.AccountView,"canvas").GetComponentsInChildren<Text>()){if(t.name=="Account title")Check(t.cachedTextGenerator.characterCountVisible>=t.text.Count(c=>!char.IsWhiteSpace(c)),"Rendered characters retained "+t.name+": "+t.cachedTextGenerator.characterCountVisible+" / "+t.text.Length);Check(t.fontSize>=12,"Readable account copy "+t.name);Check(t.preferredHeight<=t.rectTransform.rect.height+2,"Account text fits "+t.name+" font="+t.fontSize+" preferred="+t.preferredHeight+" rect="+t.rectTransform.rect.height);}
            var corners=new Vector3[4];var close=Field<Canvas>(settings.AccountView,"canvas").GetComponentsInChildren<Button>().Single(b=>b.name=="Account close");close.GetComponent<RectTransform>().GetWorldCorners(corners);Check(corners.All(v=>Screen.safeArea.Contains(new Vector2(v.x,v.y))),"Close stays inside safe area");
            Check(!Field<RectTransform>(settings.AccountView,"panel").GetComponent<RectMask2D>()&&!Field<RectTransform>(settings.AccountView,"header").GetComponent<RectMask2D>(),"Header/artwork are outside body clip");report.layouts++;
        }
        static void Capture(string file){typeof(HomeLevelButtonReview).GetMethod("Capture",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{home,Path.Combine(Output,file)});report.frames.Add(file);}
        static void Tick(){try{
            if(EditorApplication.timeSinceStartup-began>240)throw new TimeoutException("Account native review timeout");if(!string.IsNullOrEmpty(report.error))throw new Exception(report.error);
            if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating||EditorApplication.timeSinceStartup<next)return;
            if(!home){home=UnityEngine.Object.FindFirstObjectByType<HomePage>();if(!home||!home.GetComponent<PlayerProfileHost>()||!home.GetComponent<PlayerProfileHost>().Ready){home=null;return;}var first=home.GetComponent<FirstStartPage>();if(!first.Initialized){home=null;return;}if(first.IsVisible){first.Request("skip");first.Request("skip");}Check(!first.IsVisible,"Onboarding is dismissed before UI review");home.State.reduceMotion=true;settings=home.GetComponent<AppSettingsPage>();if(settings.ReviewSession==null){home=null;return;}Check(home.GetComponent<PlayerProfileHost>().IsTransient,"Native test campaign isolated");Rules();Size(0);return;}
            if(index>=30){
                if(Screen.width!=Sizes[0].x||Screen.height!=Sizes[0].y)return;
                if(phase==0){preferences.Write(GameLocale.PreferenceKey,0);GameLocale.Select(0);settings.AccountService=source;source.status=index==33?new AccountStatus{localSaved=true,online=false}:new AccountStatus{linked=true,localSaved=true,provider="Google",playerId="native-fixture-id",sync=(AccountSync)(index==30?2:index==31?1:3),confirmedCloudSaveUtc=1780000000};settings.Show();settings.Request("save-progress");phase=1;next=EditorApplication.timeSinceStartup+.15;return;}
                LayoutChecks();Capture(index==33?"Offline.png":"Linked_"+source.status.sync+".png");settings.AccountView.Hide();settings.Hide();phase=0;index++;if(index==34){Finish(0);return;}next=EditorApplication.timeSinceStartup+.1;return;
            }
            int dim=index/5,lang=index%5;if(Screen.width!=Sizes[dim].x||Screen.height!=Sizes[dim].y)return;preferences.Write(GameLocale.PreferenceKey,lang);GameLocale.Select(lang);
            if(phase==0){settings.Show();var scroll=Field<ScrollRect>(settings,"scroll");scroll.verticalNormalizedPosition=1;Capture($"Settings_{GameLocale.Codes[lang]}_{Screen.width}x{Screen.height}.png");settings.Request("save-progress");phase=1;next=EditorApplication.timeSinceStartup+.15;return;}
            LayoutChecks();Capture($"Guest_{GameLocale.Codes[lang]}_{Screen.width}x{Screen.height}.png");
            if(dim==1&&lang==0){var sc=Field<ScrollRect>(settings.AccountView,"scroll");var foot=Field<RectTransform>(settings.AccountView,"footer");var position=foot.position;sc.verticalNormalizedPosition=0;Canvas.ForceUpdateCanvases();Check(sc.content.rect.height>sc.viewport.rect.height&&sc.verticalNormalizedPosition<.01f,"Compact account content scrolls to bottom");Check(foot.position==position,"Footer remains fixed while body scrolls");Capture("Compact_Scrolled.png");}
            settings.AccountView.Hide();settings.Hide();phase=0;index++;
            if(index==30){Size(0);return;}if(index%5==0)Size(index/5);else next=EditorApplication.timeSinceStartup+.1;
        }catch(Exception e){report.error=e.ToString();try{if(home&&settings&&settings.AccountView.IsVisible)Capture("Failure.png");}catch(Exception){}Finish(1);}}
        static void Finish(int code){report.status=code==0?"PASS_NATIVE_ACCOUNT_R6":"FAIL_NATIVE_ACCOUNT_R6";Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"Native_Review.json"),JsonUtility.ToJson(report,true));EditorApplication.update-=Tick;Application.logMessageReceived-=Log;SceneManager.sceneLoaded-=IsolateSettings;GameLocale.Select(originalLocale);SessionState.EraseBool(Key);
            var view=View();view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).SetValue(view,SessionState.GetInt("HOTR.M71.Verification.previous",0));var group=Group();for(int i=5;i>=0;i--)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{SessionState.GetInt("HOTR.M71.Verification.first",0)+i});EditorApplication.Exit(code);
        }
    }
}
#endif

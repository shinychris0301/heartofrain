#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using HeartOfTheRain.App.AppSettings;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.Settings;
using HeartOfTheRain.M46;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class RussianLocale80Verification {
        const string Key="HOTR.RussianLocale80";
        const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static readonly int[] ExpectedOrder={4,0,1,2,3};
        static string Output=>Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_LAUNCH80_OUTPUT")??"../Verification/Evidence/LaunchRuStoreR3");
        [Serializable] sealed class Report {
            public string status="RUNNING",utc,unity;
            public string scope="Native Unity Editor policy/layout checks and real FirstStartPage/AppSettingsPage Play Mode button listeners, with transient campaign/tutorial and memory Settings. The existing Editor language preference is temporarily exercised and restored exactly. Six camera-rendered UGUI captures; no Android, physical touch, performance, full translation or production-service claim.";
            public int checks,preferenceCases,layoutCases,liveCases;
            public bool validStoredSelectionsPreserved,preferenceRestored,ordinaryTutorialPreserved;
            public int[] persistedIndices={0,1,2,3,4},visualOrder={4,0,1,2,3};
            public List<string> checksPassed=new List<string>(),errors=new List<string>(),captures=new List<string>();
        }
        sealed class MemorySettings:ISettingsStore {
            public readonly Dictionary<string,int> values=new Dictionary<string,int>();public int writes,flushes;
            public int Read(string key,int fallback)=>values.TryGetValue(key,out int value)?value:fallback;
            public void Write(string key,int value){values[key]=value;writes++;}public void Flush(){flushes++;}
        }
        static Report report;static double began,next;static int phase,index;
        static HomePage home;static FirstStartPage first;static AppSettingsPage settings;static MemorySettings preferences;
        static RussianLocale80Verification(){if(SessionState.GetBool(Key,false))Attach();}
        public static void Run(){
            SessionState.SetBool(Key,true);SessionState.SetInt(Key+".locale",GameLocale.Current);
            SessionState.SetBool(Key+".hasLanguage",PlayerPrefs.HasKey(GameLocale.PreferenceKey));SessionState.SetInt(Key+".language",PlayerPrefs.GetInt(GameLocale.PreferenceKey,0));
            SessionState.SetInt(Key+".stage",PlayerPrefs.GetInt(FirstStartSession.StageKey,-1));SessionState.SetInt(Key+".complete",PlayerPrefs.GetInt(FirstStartSession.CompleteKey,-1));
            EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");
            UnityEngine.Object.FindFirstObjectByType<FirstStartPage>().reviewAlways=true;
            typeof(ProfileM71Verification).GetMethod("SetupSizes",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);
            var view=View();view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).SetValue(view,SessionState.GetInt("HOTR.M71.Verification.first",0));
            EditorApplication.isPlaying=true;
        }
        static EditorWindow View()=>EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));
        static void Attach(){report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};began=EditorApplication.timeSinceStartup;preferences=new MemorySettings();SceneManager.sceneLoaded+=Loaded;EditorApplication.update+=Tick;Application.logMessageReceived+=Log;}
        static void Loaded(Scene scene,LoadSceneMode mode){foreach(var page in UnityEngine.Object.FindObjectsByType<AppSettingsPage>(UnityEngine.FindObjectsSortMode.InstanceID))page.VerificationStore=preferences;}
        static void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(message+"\n"+stack);}
        static void Check(bool value,string message){report.checks++;if(!value)throw new InvalidOperationException(message);report.checksPassed.Add(message);}
        static T Field<T>(object owner,string key)=>(T)owner.GetType().GetField(key,Private).GetValue(owner);
        static Dictionary<string,RectTransform> Nodes(object page)=>Field<Dictionary<string,RectTransform>>(page,"nodes");
        static void Bootstrap()=>typeof(LocaleBootstrap).GetMethod("Initialize",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);
        static void RestorePreference(){if(SessionState.GetBool(Key+".hasLanguage",false))PlayerPrefs.SetInt(GameLocale.PreferenceKey,SessionState.GetInt(Key+".language",0));else PlayerPrefs.DeleteKey(GameLocale.PreferenceKey);PlayerPrefs.Save();}
        static bool PreferenceRestored()=>PlayerPrefs.HasKey(GameLocale.PreferenceKey)==SessionState.GetBool(Key+".hasLanguage",false)&&(!PlayerPrefs.HasKey(GameLocale.PreferenceKey)||PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue)==SessionState.GetInt(Key+".language",0));
        static void PolicyChecks(){
            Check(GameLocale.Codes.SequenceEqual(new[]{"en","es","fr","de","ru"}),"Saved locale indices remain en0/es1/fr2/de3/ru4 without Japanese");
            Check(GameLocale.Names.SequenceEqual(new[]{"English","Español","Français","Deutsch","Русский"}),"All five native labels retain their stable indices");
            Check(ExpectedOrder.SequenceEqual(Enumerable.Range(0,5).Select(GameLocale.DisplayIndexAt)),"Visual order is Russian, English, Spanish, French, German");
            foreach(int row in new[]{-1,5}){bool rejected=false;try{GameLocale.DisplayIndexAt(row);}catch(ArgumentOutOfRangeException){rejected=true;}Check(rejected,"Invalid display row rejected "+row);}
            try {
                PlayerPrefs.DeleteKey(GameLocale.PreferenceKey);GameLocale.Select(0);Bootstrap();
                Check(GameLocale.Current==4&&!PlayerPrefs.HasKey(GameLocale.PreferenceKey),"Actual bootstrap defaults missing preference to Russian without writing a choice");report.preferenceCases++;
                foreach(int stored in new[]{0,1,2,3,4,-1,5,int.MinValue,int.MaxValue}){
                    PlayerPrefs.SetInt(GameLocale.PreferenceKey,stored);GameLocale.Select(stored==4?0:4);Bootstrap();int expected=stored>=0&&stored<=4?stored:4;
                    Check(GameLocale.Current==expected&&PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue)==stored,"Actual bootstrap preserves stored value/falls back only for invalid value "+stored);report.preferenceCases++;
                    var memory=new MemorySettings();memory.values[GameLocale.PreferenceKey]=stored;var session=new AppSettingsSession(memory,null);
                    Check(session.Language==expected&&GameLocale.Current==expected&&memory.writes==0&&memory.flushes==0,"Settings reads stored locale without migration/write "+stored);report.preferenceCases++;
                }
                var absent=new MemorySettings();var fresh=new AppSettingsSession(absent,null);Check(fresh.Language==4&&absent.writes==0,"Settings missing preference defaults Russian without persistence");report.preferenceCases++;
                fresh.Open(new[]{1,2,3,4},new[]{4,3,2,1});Check(!fresh.ChooseLanguage(0)&&absent.writes==0,"Closed language page rejects selection without a write");fresh.Navigate("language");
                foreach(int invalid in new[]{-1,5})Check(!fresh.ChooseLanguage(invalid)&&absent.writes==0,"Invalid stable index cannot be selected "+invalid);
                foreach(int stable in ExpectedOrder){int writes=absent.writes;Check(fresh.ChooseLanguage(stable)&&absent.values[GameLocale.PreferenceKey]==stable&&absent.writes==writes+1,"Settings persists actual stable index "+stable);var reopened=new AppSettingsSession(absent,null);Check(reopened.Language==stable,"Reopening retains selected stable index "+stable);}
                report.validStoredSelectionsPreserved=true;
            }finally{RestorePreference();Check(PreferenceRestored(),"Ordinary Editor preference restored after bootstrap controls");}
        }
        static void LayoutChecks(){
            var assets=AssetDatabase.LoadAssetAtPath<FirstStartAssets>("Assets/HeartOfTheRain/App/FirstStart/FirstStartAssets.asset");Check(assets&&assets.lessons.Length==3,"Real onboarding assets available");
            var lessons=assets.lessons.Select(a=>JsonUtility.FromJson<LevelData>(a.text)).ToArray();
            foreach(int selected in Enumerable.Range(0,5))foreach(var size in new[]{new Vector2(320,480),new Vector2(393,852),new Vector2(768,1024)}){
                GameLocale.Select(selected);var fs=FirstStartLayout.Build(size.x,size.y,new FirstStartSession(new MemorySettings(),lessons),"",true,true);
                var store=new MemorySettings();store.values[GameLocale.PreferenceKey]=selected;var session=new AppSettingsSession(store,null);session.Navigate("language");var app=AppSettingsLayout.Build(size.x,size.y,session);
                var fsRows=fs.overlay.elements.Where(e=>e.kind=="group"&&e.action!=null&&e.action.StartsWith("locale:",StringComparison.Ordinal)).OrderBy(e=>e.y).ToArray();
                var appRows=app.content.elements.Where(e=>e.kind=="group"&&e.action!=null&&e.action.StartsWith("language:",StringComparison.Ordinal)).OrderBy(e=>e.y).ToArray();
                Check(fsRows.Length==5&&appRows.Length==5,"Both layouts contain five actual language actions "+selected+"/"+size);
                for(int row=0;row<5;row++){int stable=ExpectedOrder[row];Check(fsRows[row].action=="locale:"+stable&&appRows[row].action=="language:"+stable,"Row action maps to persisted index "+selected+"/"+size+"/"+row);
                    Check(fs.overlay.elements.Single(e=>e.id=="locale-name-"+stable).text==GameLocale.Names[stable]&&app.content.elements.Single(e=>e.id=="language-"+stable+"-label").text==GameLocale.Names[stable],"Native name maps to stable index "+selected+"/"+size+"/"+row);}
                Check(fs.overlay.elements.Count(e=>e.id.StartsWith("locale-tick-",StringComparison.Ordinal))==1&&fs.overlay.elements.Any(e=>e.id=="locale-tick-"+selected),"FirstStart tick follows selected stable index "+selected+"/"+size);
                Check(app.content.elements.Count(e=>e.id.StartsWith("language-",StringComparison.Ordinal)&&e.id.EndsWith("-check",StringComparison.Ordinal))==1&&app.content.elements.Any(e=>e.id=="language-"+selected+"-check"),"Settings tick follows selected stable index "+selected+"/"+size);report.layoutCases++;
            }
        }
        static void CheckMenu(object page,bool onboarding,int selected){
            var nodes=Nodes(page);float previous=float.PositiveInfinity;var canvas=Field<Canvas>(page,"canvas");Canvas.ForceUpdateCanvases();
            for(int row=0;row<5;row++){int stable=ExpectedOrder[row];string id=onboarding?"locale-"+stable:"language-"+stable;var node=nodes[id];
                Check(node.gameObject.activeInHierarchy&&node.GetComponent<Button>().interactable,"Actual row is active/interactable "+id);
                Check(node.GetComponent<HomeControlLabel>().action==(onboarding?"locale:":"language:")+stable,"Actual listener action uses stable index "+id);
                Check(node.position.y<previous,"Actual Russian-first vertical order "+id);previous=node.position.y;
                var text=nodes[onboarding?"locale-name-"+stable:id+"-label"].GetComponent<Text>();Check(text.text==GameLocale.Names[stable],"Actual native name "+id);
                text.font.RequestCharactersInTexture(text.text,text.fontSize,text.fontStyle);Check(text.text.All(c=>char.IsWhiteSpace(c)||text.font.HasCharacter(c)),"Actual label font contains native glyphs "+id);
                Check(text.preferredWidth<=text.rectTransform.rect.width+1&&text.preferredHeight<=text.rectTransform.rect.height+1,"Actual label fits its rendered row "+id);
            }
            string tick=onboarding?"locale-tick-"+selected:"language-"+selected+"-check";
            Check(nodes.ContainsKey(tick)&&nodes[tick].gameObject.activeInHierarchy,"Actual selection mark uses stable index "+selected);
            Check(canvas&&canvas.isActiveAndEnabled,"Actual language canvas is visible");report.liveCases++;
        }
        static void Capture(string name){
            string relative="Native/Locale80/"+name+".png",path=Path.Combine(Output,relative);Directory.CreateDirectory(Path.GetDirectoryName(path));
            var canvases=UnityEngine.Object.FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID).Where(c=>c.isActiveAndEnabled&&c.renderMode==RenderMode.ScreenSpaceOverlay).ToArray();var cameras=canvases.Select(c=>c.worldCamera).ToArray();var distances=canvases.Select(c=>c.planeDistance).ToArray();
            var go=new GameObject("Locale80 capture camera");go.transform.position=new Vector3(-10000,0,-10);var camera=go.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;
            var previous=RenderTexture.active;var target=RenderTexture.GetTemporary(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);Texture2D pixels=null;
            try{camera.targetTexture=target;foreach(var c in canvases){c.renderMode=RenderMode.ScreenSpaceCamera;c.worldCamera=camera;c.planeDistance=1;}Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;pixels=new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0);pixels.Apply();File.WriteAllBytes(path,pixels.EncodeToPNG());report.captures.Add(relative);}
            finally{for(int n=0;n<canvases.Length;n++){canvases[n].renderMode=RenderMode.ScreenSpaceOverlay;canvases[n].worldCamera=cameras[n];canvases[n].planeDistance=distances[n];}camera.targetTexture=null;RenderTexture.active=previous;RenderTexture.ReleaseTemporary(target);if(pixels)UnityEngine.Object.Destroy(pixels);UnityEngine.Object.Destroy(go);Canvas.ForceUpdateCanvases();}
        }
        static void Tick(){try{
            if(EditorApplication.timeSinceStartup-began>180)throw new TimeoutException("Russian locale80 verification timeout");if(report.errors.Count>0)throw new InvalidOperationException(report.errors[0]);
            if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating||EditorApplication.timeSinceStartup<next)return;
            if(phase==0){home=UnityEngine.Object.FindFirstObjectByType<HomePage>();first=UnityEngine.Object.FindFirstObjectByType<FirstStartPage>();settings=UnityEngine.Object.FindFirstObjectByType<AppSettingsPage>();
                if(!home||!first||!first.Initialized||!first.IsVisible||!settings||settings.ReviewSession==null||Screen.width!=393||Screen.height!=852)return;
                Check(home.GetComponent<PlayerProfileHost>().IsTransient&&ReferenceEquals(settings.VerificationStore,preferences),"Campaign/tutorial/settings isolated before live selection");PolicyChecks();LayoutChecks();home.State.reduceMotion=true;GameLocale.Select(4);first.Request("language");first.Request("language");phase=1;next=EditorApplication.timeSinceStartup+.2;return;}
            if(phase==1){Capture("FirstStart_Russian");phase=2;return;}
            if(phase==2){int stable=ExpectedOrder[index];first.Request("language");Nodes(first)["locale-"+stable].GetComponent<Button>().onClick.Invoke();
                Check(GameLocale.Current==stable&&PlayerPrefs.GetInt(GameLocale.PreferenceKey,-1)==stable,"Actual onboarding button selects/persists stable index "+stable);
                Check(Nodes(first)["language-label"].GetComponent<Text>().text==GameLocale.Names[stable],"Onboarding pill uses selected native language "+stable);first.Request("language");CheckMenu(first,true,stable);
                if(stable==4||stable==0)Capture("FirstStart_Languages_"+GameLocale.Codes[stable]);first.Request("language");index++;
                if(index==5){first.Request("skip");first.Request("skip");Check(!first.IsVisible,"Return Home after isolated onboarding");settings.Show();Check(settings.IsVisible&&settings.ReviewSession.Language==4,"Actual Settings missing preference uses Russian");index=0;phase=3;}next=EditorApplication.timeSinceStartup+.15;return;}
            if(phase==3){int stable=ExpectedOrder[index];settings.Request("language");Nodes(settings)["language-"+stable].GetComponent<Button>().onClick.Invoke();
                Check(settings.ReviewSession.Language==stable&&GameLocale.Current==stable&&preferences.Read(GameLocale.PreferenceKey,-1)==stable,"Actual Settings button persists stable index "+stable);
                settings.Hide();settings.Show();Check(settings.ReviewSession.Language==stable,"Actual Settings reopen preserves stable index "+stable);settings.Request("language");CheckMenu(settings,false,stable);
                if(stable==4||stable==0)Capture("Settings_Languages_"+GameLocale.Codes[stable]);settings.Request("back");index++;if(index==5){settings.Request("language");settings.Request("language:4");settings.Request("back");Capture("Settings_Russian");phase=4;}next=EditorApplication.timeSinceStartup+.15;return;}
            if(phase==4){Check(report.captures.Count==6,"Six actual native UI captures recorded");Finish(0);}
        }catch(Exception error){report.errors.Add(error.ToString());Finish(1);}}
        static void Finish(int code){
            try{RestorePreference();report.preferenceRestored=PreferenceRestored();report.ordinaryTutorialPreserved=PlayerPrefs.GetInt(FirstStartSession.StageKey,-1)==SessionState.GetInt(Key+".stage",-1)&&PlayerPrefs.GetInt(FirstStartSession.CompleteKey,-1)==SessionState.GetInt(Key+".complete",-1);
                Check(report.preferenceRestored&&report.ordinaryTutorialPreserved,"Ordinary language/tutorial preferences restored/preserved at suite exit");GameLocale.Select(SessionState.GetInt(Key+".locale",4));
            }catch(Exception error){report.errors.Add(error.ToString());code=1;}
            report.status=code==0?"PASS_NATIVE_RUSSIAN_LOCALE80":"FAIL_NATIVE_RUSSIAN_LOCALE80";Directory.CreateDirectory(Path.Combine(Output,"Native"));File.WriteAllText(Path.Combine(Output,"Native/Locale80.json"),JsonUtility.ToJson(report,true));
            EditorApplication.update-=Tick;Application.logMessageReceived-=Log;SceneManager.sceneLoaded-=Loaded;SessionState.EraseBool(Key);
            try{View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).SetValue(View(),SessionState.GetInt("HOTR.M71.Verification.previous",0));var group=typeof(ProfileM71Verification).GetMethod("Group",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);for(int i=4;i>=0;i--)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{SessionState.GetInt("HOTR.M71.Verification.first",0)+i});}catch(Exception error){Debug.LogWarning(error.Message);}
            EditorApplication.Exit(code);
        }
    }
}
#endif

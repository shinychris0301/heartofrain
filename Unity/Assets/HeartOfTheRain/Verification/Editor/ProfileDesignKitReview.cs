#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.Localization;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification
{
    [InitializeOnLoad] public static class ProfileDesignKitReview
    {
        const string Key="HOTR.ProfileDesignKit";
        static readonly int[] Size={0,0,0,0,0,0,0,0,0,1,1,2,3,3,4,4,4,4};
        static readonly Vector2Int[] Dimensions={new Vector2Int(393,852),new Vector2Int(320,480),new Vector2Int(768,1024),new Vector2Int(900,2000),new Vector2Int(320,568)};
        static int index,originalLocale;static double started,readyAt;static string ordinary;static Report report;
        [Serializable] sealed class Report {public string utc,unity,status,error,scope="Native Unity Editor/Play Mode with review-memory campaign and appearance. Camera-rendered UGUI and programmatic selections/scrolling; not device/touch/FPS or production-service certification.";public int checks;public List<string> frames=new List<string>();}
        sealed class Preferences:IAppearancePreferences {public string json="{}";public bool fail;public string Read()=>json;public void Write(string text){if(fail)throw new IOException("Explicit write fault");json=text;}public void Flush(){}}
        static string Output=>Path.GetFullPath(System.Environment.GetEnvironmentVariable("HOTR_REVIEW93_OUT")??"../Verification/Evidence/ProfileDesignKit");
        static ProfileDesignKitReview(){if(SessionState.GetBool(Key,false)){started=readyAt=EditorApplication.timeSinceStartup;report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};ordinary=PlayerPrefs.GetString(ProfileStore.Key,"<absent>");originalLocale=GameLocale.Current;EditorApplication.update+=Tick;Application.logMessageReceived+=Log;}}
        public static void Run(){SessionState.SetBool(Key,true);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");UnityEngine.Object.FindFirstObjectByType<FirstStartPage>().reviewAlways=true;typeof(ProfileM71Verification).GetMethod("SetupSizes",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);EditorApplication.isPlaying=true;}
        static void Check(bool ok,string message){report.checks++;if(!ok)throw new InvalidOperationException(message);}
        static void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.error=message+"\n"+stack;}
        static void Call(ProfilePage page,string method)=>typeof(ProfilePage).GetMethod(method,BindingFlags.Instance|BindingFlags.NonPublic).Invoke(page,null);
        static void Click(ProfilePage page,string name)=>page.GetComponentsInChildren<Button>().Single(b=>b.name==name).onClick.Invoke();
        static bool ProgressMatches(ProfilePage page,float value)
        {
            // Inspect the current active card, then include its inactive zero
            // clip directly. Destroy-deferred cards from prior renders stay out.
            var card=page.GetComponentsInChildren<RectTransform>().Single(t=>t.name=="Stat 2");
            var track=card.Find("Stats progress track") as RectTransform;
            var clip=card.Find("Stats progress clip") as RectTransform;
            var fill=clip?clip.Find("Stats progress fill") as RectTransform:null;
            if(!track||!clip||!fill)return false;
            float amount=Mathf.Clamp01(value),width=track.rect.width*amount;
            var image=fill.GetComponent<Image>();
            return track.rect.width>0&&clip.GetComponent<RectMask2D>()&&image&&image.type==Image.Type.Sliced&&!image.preserveAspect&&image.maskable&&!image.raycastTarget&&
                Mathf.Abs(image.pixelsPerUnitMultiplier-4)<.001f&&clip.gameObject.activeSelf==(amount>0)&&
                Mathf.Abs(clip.rect.width-width)<.001f&&Mathf.Abs(fill.rect.width-Mathf.Max(12,width))<.001f&&
                Mathf.Abs(clip.rect.height-18)<.001f&&Mathf.Abs(fill.rect.height-track.rect.height)<.001f&&
                Vector2.Distance(clip.anchoredPosition,track.anchoredPosition)<.001f&&fill.anchoredPosition==Vector2.zero;
        }
        static void Rules()
        {
            HeartOfTheRain.App.Profile.Editor.ProfileReview.Validate();var preferences=new Preferences();var store=new ProfileStore(preferences);string error;
            foreach(var frame in ProfileRules.Frames){Check(store.Select(2,frame,out error),"Frame rejected "+frame);Check(new ProfileStore(preferences).Snapshot.frameId==frame,"Frame did not reload "+frame);}
            Check(!store.Select(2,"unknown",out error),"Unknown frame accepted");string before=preferences.json;preferences.fail=true;Check(!store.Select(2,"Sapphire",out error)&&store.Snapshot.frameId=="GardenIvory"&&preferences.json==before,"Failed write changed appearance");preferences.fail=false;
            var assets=Resources.Load<ProfileAssets>("HeartOfTheRainProfile/Config");foreach(var id in ProfileRules.Frames)Check(assets.Find("Frame"+id)==assets.Find("Frame"+id),"Frame slice is not cached");
            foreach(var id in ProfileRules.Banners)Check(assets.Find("Banner_"+id).rect.size==new Vector2(2172,724),"Banner was resized");
        }
        static void Tick()
        {
            try
            {
                if(EditorApplication.timeSinceStartup-started>210)throw new TimeoutException("Profile design review timed out");
                if(!string.IsNullOrEmpty(report.error))throw new InvalidOperationException(report.error);
                if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating||EditorApplication.timeSinceStartup-readyAt<.8)return;
                var home=UnityEngine.Object.FindFirstObjectByType<HomePage>();if(!home||!home.GetComponent<PlayerProfileHost>()||!home.GetComponent<PlayerProfileHost>().Ready)return;
                var page=home.GetComponent<ProfilePage>();if(!page||!page.IsPrepared)return;
                int size=Size[index];if(Screen.width!=Dimensions[size].x||Screen.height!=Dimensions[size].y){readyAt=EditorApplication.timeSinceStartup;return;}
                var first=home.GetComponent<FirstStartPage>();if(first.IsVisible){first.Request("skip");first.Request("skip");}Check(home.GetComponent<PlayerProfileHost>().IsTransient,"Campaign is not isolated");
                if(index==0)Rules();if(page.IsVisible)page.Hide();GameLocale.Select(index>=5&&index<=8?index-4:index==9||index==10?4:0);
                home.State.currentLevel=12;home.State.chapterNumber=1;home.State.completedLevelsInChapter=11;home.State.levelsPerChapter=50;home.State.stars=24;home.ApplyState(home.State);
                // Prime native viewport/canvas geometry before opening Profile.
                Capture(home,null);home.GetComponentsInChildren<HomeControlLabel>().Single(c=>c.action=="profile").GetComponent<Button>().onClick.Invoke();Check(page.IsVisible,"Avatar did not open Profile");
                Click(page,"Tab 0");Click(page,"Choice Dariya");Click(page,"Tab 1");string banner=index==1?"Lantern":index==2?"Twilight":"Village";Click(page,"Choice "+banner);
                Click(page,"Tab 2");string frame=index==1?"LanternSapphire":index==2?"GardenIvory":"RainkeeperGold";Click(page,"Choice "+frame);
                // Exercise each classic/new choice and ensure Home retains the R2 square footprint.
                if(index==0)foreach(var id in ProfileRules.Frames){Click(page,"Choice "+id);var selected=home.GetComponentsInChildren<RectTransform>().Single(t=>t.name=="Selected profile avatar");var header=home.GetComponentsInChildren<RectTransform>().Single(t=>t.name=="header");Check(Mathf.Abs(selected.rect.width-header.rect.width*.17f)<.01f&&Mathf.Abs(selected.rect.width-selected.rect.height)<.01f,"Home frame footprint changed: "+id);Check(new ProfileStore((IAppearancePreferences)typeof(ProfileStore).GetField("preferences",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(typeof(ProfilePage).GetField("store",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(page))).Snapshot.frameId==id,"UI selection was not persisted");}if(index==0)Click(page,"Choice RainkeeperGold");
                int tab=index==3||index==12?2:index==4?1:3;Click(page,"Tab "+tab);Canvas.ForceUpdateCanvases();
                if(index==3){for(int language=0;language<5;language++){GameLocale.Select(language);Call(page,"RefreshText");Call(page,"RenderCollection");foreach(var text in page.GetComponentsInChildren<Text>().Where(t=>t.name.StartsWith("Choice label "))){var generator=new TextGenerator();generator.Populate(text.text,text.GetGenerationSettings(text.rectTransform.rect.size));Check(generator.characterCountVisible>=text.text.Length,"Localized frame caption clipped: "+text.text);}}GameLocale.Select(0);Call(page,"RefreshText");Call(page,"RenderCollection");}
                var inner=page.GetComponentsInChildren<ScrollRect>().Single(s=>s.name=="Collection viewport");var outer=page.GetComponentsInChildren<ScrollRect>().Single(s=>s.name=="Profile Safe Area");
                if(size==1||size==2||size==4)outer.verticalNormalizedPosition=0;inner.verticalNormalizedPosition=index==3||index==4||index==10||index==12||index==16||index==17?0:1;
                if(tab==3)
                {
                    var join=page.GetComponentsInChildren<Button>().Single(b=>b.name=="Join");var joinLabel=join.GetComponentInChildren<Text>();var joinGenerator=new TextGenerator();joinGenerator.Populate(joinLabel.text,joinLabel.GetGenerationSettings(joinLabel.rectTransform.rect.size));Check(joinGenerator.characterCountVisible>=joinLabel.text.Length&&joinGenerator.lines.Count==1,"Join caption clipped or wrapped");
                    foreach(var button in page.GetComponentsInChildren<Button>().Where(b=>b.name.StartsWith("Tab "))){var text=button.GetComponentInChildren<Text>();var generator=new TextGenerator();generator.Populate(text.text,text.GetGenerationSettings(text.rectTransform.rect.size));Check(generator.characterCountVisible>=text.text.Length,"Localized tab caption clipped: "+text.text);}
                    Check(page.GetComponentsInChildren<Text>().Single(t=>t.name=="Stat value 0").text=="12"&&page.GetComponentsInChildren<Text>().Single(t=>t.name=="Stat value 3").text=="24","Stats do not use Home state");
                    Check(ProgressMatches(page,.22f),"Progress clip ratio, zero state or sliced fill geometry wrong");
                    var cards=page.GetComponentsInChildren<RectTransform>().Where(t=>t.name=="Stat 0"||t.name=="Stat 1").ToArray();Check(size==1||size==4?cards[0].anchoredPosition.x==cards[1].anchoredPosition.x:cards[0].anchoredPosition.y==cards[1].anchoredPosition.y,"Stats column policy wrong");
                    foreach(var label in page.GetComponentsInChildren<Text>().Where(t=>t.name.StartsWith("Stat label "))){var generator=new TextGenerator();generator.Populate(label.text,label.GetGenerationSettings(label.rectTransform.rect.size));Check(generator.characterCountVisible>=label.text.Length&&generator.lines.Count<=2,"Localized stats label clipped: "+label.text);}
                    foreach(var icon in page.GetComponentsInChildren<Image>().Where(i=>i.name.StartsWith("Stat icon ")))Check(icon.preserveAspect&&icon.sprite.rect.width>0&&icon.sprite.rect.height>0,"Stats icon distorted or absent");
                }
                if(index==15){home.State.currentLevel=50;home.State.completedLevelsInChapter=99;home.State.stars=88;Call(page,"Update");Check(ProgressMatches(page,1),"Progress exceeds 100 percent or clipped fill geometry changed");home.State.completedLevelsInChapter=-1;Call(page,"Update");Check(ProgressMatches(page,0),"Negative progress not clamped and hidden");home.State.completedLevelsInChapter=49;Call(page,"Update");Check(page.GetComponentsInChildren<Text>().Single(t=>t.name=="Stat value 3").text=="88","Live stat refresh failed");}
                if(index==16){home.State.levelsPerChapter=0;Call(page,"RefreshText");Call(page,"RenderCollection");Check(page.GetComponentsInChildren<Text>().Single(t=>t.name=="Stat value 2").text=="—"&&ProgressMatches(page,0),"Zero denominator not handled and hidden");}
                var host=home.GetComponent<PlayerProfileHost>();if(index==17){typeof(PlayerProfileHost).GetProperty("Ready").SetValue(host,false);Call(page,"RefreshText");Call(page,"RenderCollection");Check(page.GetComponentsInChildren<Text>().Where(t=>t.name.StartsWith("Stat value ")).All(t=>t.text=="—"),"Unloaded stats fabricate zeroes");}
                if(index>=15)inner.verticalNormalizedPosition=0; // Put the changed fraction/stars in the captured viewport.
                string file=$"{index:00}_{banner}_{frame}_Tab{tab}_{GameLocale.Codes[GameLocale.Current]}_{Screen.width}x{Screen.height}.png";Directory.CreateDirectory(Output);Capture(home,Path.Combine(Output,file));report.frames.Add(file);
                if(index==17)typeof(PlayerProfileHost).GetProperty("Ready").SetValue(host,true);
                Check(PlayerPrefs.GetString(ProfileStore.Key,"<absent>")==ordinary,"Ordinary appearance modified");page.Hide();Check(home.PresentationInteractable,"Profile close did not restore Home");
                index++;if(index==Size.Length){Finish(0);return;}if(Size[index]!=size){var view=EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(view,SessionState.GetInt("HOTR.M71.Verification.first",0)+Size[index]);view.Repaint();}readyAt=EditorApplication.timeSinceStartup;
            }
            catch(Exception e){report.error=e.ToString();Finish(1);}
        }
        static void Capture(HomePage home,string path)=>typeof(HomeLevelButtonReview).GetMethod("Capture",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{home,path??Path.GetFullPath("../.verification-cache/ProfileDesignKit_Prime.png")});
        static void Finish(int code)
        {
            report.status=code==0?"PASS_NATIVE_PROFILE_DESIGN_KIT":"FAIL_NATIVE_PROFILE_DESIGN_KIT";Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"Native_Review.json"),JsonUtility.ToJson(report,true));GameLocale.Select(originalLocale);EditorApplication.update-=Tick;Application.logMessageReceived-=Log;SessionState.EraseBool(Key);
            var view=EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(view,SessionState.GetInt("HOTR.M71.Verification.previous",0));var group=typeof(ProfileM71Verification).GetMethod("Group",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);for(int n=4;n>=0;n--)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{SessionState.GetInt("HOTR.M71.Verification.first",0)+n});EditorApplication.Exit(code);
        }
    }
}
#endif

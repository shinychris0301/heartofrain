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
using UnityEngine.SceneManagement;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.AppSettings;
using HeartOfTheRain.App.Settings;
using HeartOfTheRain.App.Localization;
namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class DailyGiftR1Review {
        const string Key="HOTR.DailyGiftR1";const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static string Output=>Path.GetFullPath(System.Environment.GetEnvironmentVariable("HOTR_REVIEW93_OUT")??"../Verification/Evidence/DailyGiftR1");
        [Serializable] class Report {public string utc,status,error,scope="Native Unity Editor Play Mode UGUI captures, isolated in-memory profile and development authority. Visual day/network fixtures are labelled; no Android, physical input, remote-service or performance certification.";public int checks,layouts;public List<string> frames=new List<string>();}
        sealed class SettingsStore:ISettingsStore {public int Read(string k,int f)=>f;public void Write(string k,int v){}public void Flush(){}}
        static Report report;static double began,next;static int index,phase,originalLocale,first,previous;static long day=100;
        static HomePage home;static DailyGiftPage page;static PlayerProfileHost host;static DevelopmentGiftAuthority authority;
        static readonly Vector2Int[] Sizes={new Vector2Int(393,852),new Vector2Int(320,568),new Vector2Int(430,932),new Vector2Int(768,1024),new Vector2Int(844,390),new Vector2Int(320,480)};
        static EditorWindow View()=>EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));
        static object Group(){var a=typeof(Editor).Assembly;var type=a.GetType("UnityEditor.GameViewSizes");var instance=typeof(ScriptableSingleton<>).MakeGenericType(type).GetProperty("instance",BindingFlags.Public|BindingFlags.Static).GetValue(null);string group=EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android?"Android":EditorUserBuildSettings.activeBuildTarget==BuildTarget.iOS?"iOS":"Standalone";return type.GetMethod("GetGroup").Invoke(instance,new[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeGroupType"),group)});}
        static void Size(int n){View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).SetValue(View(),first+n);View().Repaint();next=EditorApplication.timeSinceStartup+.4;}
        static DailyGiftR1Review(){if(SessionState.GetBool(Key,false)){report=new Report{utc=DateTime.UtcNow.ToString("o")};began=EditorApplication.timeSinceStartup;originalLocale=GameLocale.Current;first=SessionState.GetInt(Key+".first",0);previous=SessionState.GetInt(Key+".previous",0);EditorApplication.update+=Tick;Application.logMessageReceived+=Log;SceneManager.sceneLoaded+=Isolate;}}
        static void Isolate(Scene scene,LoadSceneMode mode){var h=UnityEngine.Object.FindFirstObjectByType<HomePage>();if(!h)return;h.GetComponent<AppSettingsPage>().VerificationStore=new SettingsStore();var p=h.GetComponent<PlayerProfileHost>()??h.gameObject.AddComponent<PlayerProfileHost>();p.VerificationAuthorityFactory=id=>authority=new DevelopmentGiftAuthority(new MemoryProfileRepository(new PlayerProfile{playerId=id,coins=0,starting=new int[4],tools=new int[4]}),()=>day,GiftSchedule.Preview());}
        public static void Prepare(){
            CleanupStaleSizes();
            AssetDatabase.Refresh();string path="Assets/HeartOfTheRain/Resources/HOTR_DailyGift/Design.asset";Directory.CreateDirectory(Path.GetDirectoryName(path));AssetDatabase.Refresh();var a=AssetDatabase.LoadAssetAtPath<DailyGiftDesignAssets>(path);if(!a){a=ScriptableObject.CreateInstance<DailyGiftDesignAssets>();AssetDatabase.CreateAsset(a,path);}
            Sprite S(string p)=>AssetDatabase.LoadAssetAtPath<Sprite>("Assets/HeartOfTheRain/"+p);
            Sprite D(string p)=>S("App/DailyGiftDesign/Art/"+p+".png");
            var shared=HeartOfTheRain.App.AccountDesign.AccountDesignAssets.Load();a.chrome=shared.chrome;a.close=shared.close;a.primary=shared.primary;a.check=shared.check;a.titleFont=shared.titleFont;a.bodyFont=shared.bodyFont;
            a.coin=S("App/Home/Art/R3_Coin.png");a.chest=D("DG_Gift_Chest");a.hero=D("DG_Hero_Well");a.star=D("DG_Star");a.upcoming=D("DG_Card_Upcoming");a.today=D("DG_Card_Today");a.collected=D("DG_Card_Collected");a.bonus=D("DG_Card_Bonus");a.rocket=D("Reward_Rocket");a.bomb=D("Reward_Bomb");a.hammer=D("Reward_Hammer");a.orb=D("Reward_Orb");
            foreach(var field in typeof(DailyGiftDesignAssets).GetFields(BindingFlags.Public|BindingFlags.Instance))if(typeof(UnityEngine.Object).IsAssignableFrom(field.FieldType)&&!(UnityEngine.Object)field.GetValue(a))throw new Exception("Missing binding "+field.Name);
            EditorUtility.SetDirty(a);AssetDatabase.SaveAssets();Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"Import.json"),"{\"status\":\"PASS_NATIVE_DAILY_GIFT_R1_BINDINGS\"}");
        }
        // A terminated verification may leave its temporary sizes in another target group.
        static void CleanupStaleSizes(){var a=typeof(Editor).Assembly;var type=a.GetType("UnityEditor.GameViewSizes");var instance=typeof(ScriptableSingleton<>).MakeGenericType(type).GetProperty("instance",BindingFlags.Public|BindingFlags.Static).GetValue(null);foreach(string key in new[]{"Standalone","Android","iOS"}){var group=type.GetMethod("GetGroup").Invoke(instance,new[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeGroupType"),key)});var names=(string[])group.GetType().GetMethod("GetDisplayTexts").Invoke(group,null);for(int i=names.Length-1;i>=0;i--)if(names[i].StartsWith("HOTR Daily Gift R1",StringComparison.Ordinal))group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{i});}}
        public static void Run(){
            SessionState.SetBool(Key,true);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");UnityEngine.Object.FindFirstObjectByType<FirstStartPage>().reviewAlways=true;
            var group=Group();first=(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null);previous=(int)View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).GetValue(View());SessionState.SetInt(Key+".first",first);SessionState.SetInt(Key+".previous",previous);
            var asm=typeof(Editor).Assembly;foreach(var size in Sizes){var v=Activator.CreateInstance(asm.GetType("UnityEditor.GameViewSize"),BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance,null,new object[]{Enum.Parse(asm.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),size.x,size.y,"HOTR Daily Gift R1"},null);group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{v});}
            EditorApplication.isPlaying=true;
        }
        static void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.error=message+"\n"+stack;}
        static void Check(bool ok,string message){report.checks++;if(!ok)throw new Exception(message);}
        static T Field<T>(object o,string key)=>(T)o.GetType().GetField(key,Private).GetValue(o);
        static Dictionary<string,RectTransform> Nodes=>Field<Dictionary<string,RectTransform>>(page,"nodes");
        static void Render(DailyGiftView v){typeof(DailyGiftPage).GetField("view",Private).SetValue(page,v);typeof(DailyGiftPage).GetMethod("Render",Private).Invoke(page,null);}
        static DailyGiftView Fixture(int step=0,bool claimed=false)=>new DailyGiftView{schedule=host.Schedule,development=true,claims=step+(claimed?1:0),offer=new GiftOffer{step=step,claimed=claimed,grant=host.Schedule.days[step].Copy()}};
        static void Capture(string file){typeof(HomeLevelButtonReview).GetMethod("Capture",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{home,Path.Combine(Output,file)});report.frames.Add(file);}
        static void Rules(){
            Check(host.IsTransient,"Review uses isolated in-memory campaign");Check(authority!=null,"Explicit local test authority injected");
            var before=host.Service.Read();page.Show();page.Request("claim");page.Request("claim");var after=host.Service.Read();Check(after.coins==before.coins+50&&after.giftClaims==1,"Double claim credits exactly 50 coins once");Check(Nodes["claim"].GetComponent<Button>().interactable&&Nodes["claim-label"].GetComponent<Text>().text==DailyGiftDesignText.T("done"),"Confirmed gift offers Done");Check(!Nodes["hero"].Find("Collection effects"),"Reduced motion has no transient effects");Nodes["claim"].GetComponent<Button>().onClick.Invoke();Check(!page.IsVisible,"Done returns to Home");
            day++;authority.Offline=true;page.Show();Check(!Nodes["claim"].GetComponent<Button>().interactable,"Unavailable offer cannot claim");page.Request("claim");Check(host.Service.Read().giftClaims==1&&host.Service.Read().pendingGift==null,"Failed confirmation cannot advance or grant");authority.Offline=false;page.Request("claim");Check(host.Service.Read().giftClaims==2&&host.Service.Read().starting[0]==before.starting[0]+1,"Retry grants actual next reward");
            page.Hide();for(int i=2;i<7;i++){day++;page.Show();page.Request("claim");page.Hide();}
            after=host.Service.Read();Check(after.giftClaims==7&&after.coins==before.coins+375&&after.starting[2]==before.starting[2]+1,"Seven-day sequence includes both Day 7 rewards");
            day++;page.Show();Check(Nodes["hero-day"].GetComponent<Text>().text==DailyGiftDesignText.Day(1),"Existing cycle restarts only on next authoritative day");page.Hide();
            bool retried=false;page.ShowError(()=>{retried=true;home.SetPresentation(true,true);});page.Request("close");Check(page.IsVisible&&!Nodes.ContainsKey("close"),"Protected save error cannot be dismissed");page.Request("claim");Check(retried&&!page.IsVisible,"Protected retry callback preserved");
        }
        static void LayoutChecks(){
            Check(!Nodes["panel"].GetComponent<RectMask2D>()&&!Nodes["header"].GetComponent<RectMask2D>()&&Nodes["viewport"].GetComponent<RectMask2D>(),"Only body viewport clips");
            Check(Nodes["claim"].IsChildOf(Nodes["footer"])&&!Nodes["claim"].IsChildOf(Nodes["body"]),"Claim remains outside scroll body");
            var corners=new Vector3[4];Nodes["close"].GetWorldCorners(corners);Check(corners.All(v=>Screen.safeArea.Contains(new Vector2(v.x,v.y))),"Close touch target stays in device safe area");
            foreach(var t in Field<Canvas>(page,"canvas").GetComponentsInChildren<Text>()){
                Check(t.preferredHeight<=t.rectTransform.rect.height+1,"Localized text height "+t.name);Check(t.fontSize>=10,"Readable localized text "+t.name);Check(t.text.All(c=>char.IsWhiteSpace(c)||t.font.HasCharacter(c)),"Native glyph coverage "+t.name);
                if(t.name=="title"||t.name=="claim-label")Check(t.cachedTextGenerator.characterCountVisible>=t.text.Count(c=>!char.IsWhiteSpace(c)),"Rendered text completeness "+t.name);
            }
            for(int i=0;i<6;i++)Check(Nodes["day-"+i].rect.height>=91,"Larger card "+i);
            Check(Nodes["shell"].GetComponent<Image>().pixelsPerUnitMultiplier==3.891f,"Chrome nine-slice multiplier retained");
            var sc=Field<ScrollRect>(page,"scroll");var footer=Nodes["footer"].position;sc.verticalNormalizedPosition=0;Canvas.ForceUpdateCanvases();Check(Nodes["footer"].position==footer,"Scrolling cannot move fixed footer");sc.verticalNormalizedPosition=1;report.layouts++;
        }
        static void Tick(){try{
            if(EditorApplication.timeSinceStartup-began>240)throw new TimeoutException("Daily Gift native review timeout");if(!string.IsNullOrEmpty(report.error))throw new Exception(report.error);
            if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating||EditorApplication.timeSinceStartup<next)return;
            if(!home){home=UnityEngine.Object.FindFirstObjectByType<HomePage>();if(!home||!home.GetComponent<PlayerProfileHost>()||!home.GetComponent<PlayerProfileHost>().Ready){home=null;return;}var firstPage=home.GetComponent<FirstStartPage>();if(!firstPage.Initialized){home=null;return;}if(firstPage.IsVisible){firstPage.Request("skip");firstPage.Request("skip");}host=home.GetComponent<PlayerProfileHost>();page=home.GetComponent<DailyGiftPage>();home.State.reduceMotion=true;Rules();Size(0);return;}
            if(index<30){int dim=index/5,lang=index%5;if(Screen.width!=Sizes[dim].x||Screen.height!=Sizes[dim].y)return;GameLocale.Select(lang);
                if(phase==0){page.Show();Render(Fixture(lang==1?3:lang==2||lang==4?6:0,lang==3));phase=1;next=EditorApplication.timeSinceStartup+.2;return;}
                LayoutChecks();Capture($"Gift_{GameLocale.Codes[lang]}_{Screen.width}x{Screen.height}.png");
                if(dim==1||dim==5){var sc=Field<ScrollRect>(page,"scroll");Check(sc.vertical,"Compact body scrolls");sc.verticalNormalizedPosition=0;Canvas.ForceUpdateCanvases();Capture($"Scrolled_{GameLocale.Codes[lang]}_{Screen.width}x{Screen.height}.png");}
                page.Hide();phase=0;index++;if(index==30){Size(0);return;}if(index%5==0)Size(index/5);return;
            }
            if(Screen.width!=Sizes[0].x||Screen.height!=Sizes[0].y)return;GameLocale.Select(0);
            if(index==30){page.Show();var v=Fixture();v.loading=true;v.claiming=true;Render(v);index++;next=EditorApplication.timeSinceStartup+.2;return;}
            if(index==31){Check(!Nodes["claim"].GetComponent<Button>().interactable,"Loading primary disables immediately");Check(Nodes["claim"].GetComponent<Image>().color.a<.001f,"Disabled claim keeps its hit area invisible");Capture("Loading_Fixture.png");var v=Fixture();v.networkError=true;Render(v);index++;next=EditorApplication.timeSinceStartup+.2;return;}
            if(index==32){Check(Nodes["claim"].GetComponent<Button>().interactable,"Network error allows explicit retry");Capture("Retry_Fixture.png");Render(new DailyGiftView{schedule=host.Schedule,error=true});index++;next=EditorApplication.timeSinceStartup+.2;return;}
            if(index==33){Check(!((RawImage)typeof(DailyGiftPage).GetField("backdrop",Private).GetValue(page)).gameObject.activeSelf,"Save-error dialog keeps the scene behind it visible (no chapter backdrop)");Capture("Save_Error_Fixture.png");page.Hide();home.State.reduceMotion=false;page.Show();page.Request("claim");Check(host.Service.Read().giftClaims==8,"Actual reward committed before collection animation");index++;next=EditorApplication.timeSinceStartup+.18;return;}
            if(index==34){Check(Nodes["hero"].Find("Collection effects").GetComponentsInChildren<Image>().Length==14,"Confirmed success uses fourteen bounded glints");Capture("Collection_Confirmed_Day1.png");page.Hide();Check(!Nodes["hero"].Find("Collection effects")||!Nodes["hero"].Find("Collection effects").gameObject.activeSelf,"Dismissal clears effects synchronously");page.Show();index++;next=EditorApplication.timeSinceStartup+1;return;}
            Check(!Nodes["hero"].Find("Collection effects"),"Reopened page has no stale effects");Capture("Reopened.png");page.Hide();Finish(0);
        }catch(Exception e){report.error=e.ToString();try{if(home&&page&&page.IsVisible)Capture("Failure.png");}catch(Exception){}Finish(1);}}
        static void Finish(int code){report.status=code==0?"PASS_NATIVE_DAILY_GIFT_R1":"FAIL_NATIVE_DAILY_GIFT_R1";Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"Native_Review.json"),JsonUtility.ToJson(report,true));EditorApplication.update-=Tick;Application.logMessageReceived-=Log;SceneManager.sceneLoaded-=Isolate;GameLocale.Select(originalLocale);SessionState.EraseBool(Key);View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).SetValue(View(),previous);var group=Group();for(int i=Sizes.Length-1;i>=0;i--)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{first+i});EditorApplication.Exit(code);}
    }
}
#endif

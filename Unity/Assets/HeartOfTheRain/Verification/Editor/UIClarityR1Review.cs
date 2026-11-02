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
using UnityEngine.Profiling;
using UnityEngine.SceneManagement;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.AppSettings;
using HeartOfTheRain.App.Settings;
using HeartOfTheRain.App.UIClarity;
namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class UIClarityR1Review {
        const string Key="HOTR.UIClarityR1";const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static string phase=>SessionState.GetString(Key,"");static string Output=>Path.GetFullPath("../Verification/Evidence/UIClarityR1/"+phase);
        [Serializable] class Report {public string utc,status,error,scope="Native Unity Editor UGUI, isolated campaign/settings/appearance. Peak is an explicit maximum-scale presentation fixture. No Android, physical-device memory/performance or native-language editorial approval.";public int checks;public List<string> frames=new List<string>();public List<Sample> graphics=new List<Sample>();}
        [Serializable] class Sample {public string frame,name,path,filter;public int mips;public float width,height,texelsX,texelsY,multiplier;public long bytes;public bool sliced,white;}
        sealed class Store:ISettingsStore {public int Read(string k,int f)=>f;public void Write(string k,int v){}public void Flush(){}}
        static Report report;static double began,next;static int index,step,first,previous;static HomePage home;static DailyGiftPage gift;static WellworksPage works;static ProfilePage profile;
        static readonly Vector2Int[] Sizes={new Vector2Int(393,852),new Vector2Int(320,568),new Vector2Int(900,2000),new Vector2Int(1440,3120),new Vector2Int(1572,3408)};
        static EditorWindow View()=>EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));
        static object Group(){var a=typeof(Editor).Assembly;var t=a.GetType("UnityEditor.GameViewSizes");var instance=typeof(ScriptableSingleton<>).MakeGenericType(t).GetProperty("instance",BindingFlags.Public|BindingFlags.Static).GetValue(null);return t.GetMethod("GetGroup").Invoke(instance,new[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeGroupType"),EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android?"Android":"Standalone")});}
        static UIClarityR1Review(){if(phase!=""){report=new Report{utc=DateTime.UtcNow.ToString("o")};began=EditorApplication.timeSinceStartup;first=SessionState.GetInt(Key+".first",0);previous=SessionState.GetInt(Key+".previous",0);EditorApplication.update+=Tick;Application.logMessageReceived+=Log;SceneManager.sceneLoaded+=Isolate;}}
        static void Isolate(Scene s,LoadSceneMode m){foreach(var p in UnityEngine.Object.FindObjectsByType<AppSettingsPage>(UnityEngine.FindObjectsSortMode.InstanceID))p.VerificationStore=new Store();}
        public static void Before()=>Run("Before");public static void After()=>Run("After");
        static void Run(string name){SessionState.SetString(Key,name);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");UnityEngine.Object.FindFirstObjectByType<FirstStartPage>().reviewAlways=true;var group=Group();first=(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null);previous=(int)View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).GetValue(View());SessionState.SetInt(Key+".first",first);SessionState.SetInt(Key+".previous",previous);var a=typeof(Editor).Assembly;foreach(var s in Sizes){var v=Activator.CreateInstance(a.GetType("UnityEditor.GameViewSize"),BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance,null,new object[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),s.x,s.y,"HOTR UI Clarity R1"},null);group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{v});}EditorApplication.isPlaying=true;}
        static void Check(bool ok,string message){report.checks++;if(!ok)throw new Exception(message);}
        static void Log(string m,string s,LogType t){if(t==LogType.Error||t==LogType.Exception||t==LogType.Assert)report.error=m+"\n"+s;}
        static T Field<T>(object o,string key)=>(T)o.GetType().GetField(key,Private).GetValue(o);
        static void Size(int n){View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).SetValue(View(),first+n);View().Repaint();next=EditorApplication.timeSinceStartup+.4;}
        static void Capture(string file){
            Directory.CreateDirectory(Output);typeof(HomeLevelButtonReview).GetMethod("Capture",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{home,Path.Combine(Output,file)});report.frames.Add(file);
            var canvas=index%3==0?Field<Canvas>(gift,"canvas"):index%3==1?Field<Canvas>(works,"canvas"):profile.GetComponentsInChildren<Canvas>().First(c=>c.name.Contains("Profile"));
            foreach(var im in canvas.GetComponentsInChildren<Image>()){if(!im.sprite)continue;var sp=im.sprite;var tex=sp.texture;var corners=new Vector3[4];im.rectTransform.GetWorldCorners(corners);float w=Vector3.Distance(corners[0],corners[3]),h=Vector3.Distance(corners[0],corners[1]);
                report.graphics.Add(new Sample{frame=file,name=im.name,path=AssetDatabase.GetAssetPath(sp),filter=tex.filterMode.ToString(),mips=tex.mipmapCount,width=w,height=h,texelsX=sp.rect.width,texelsY=sp.rect.height,multiplier=im.pixelsPerUnitMultiplier,bytes=Profiler.GetRuntimeMemorySizeLong(tex),sliced=im.type==Image.Type.Sliced,white=im.color==Color.white});
                if(phase=="After"&&im.name=="hero-well")Check(im.pixelsPerUnitMultiplier==6&&sp.border.x==108,"Paired doubled slice migration");
                if(phase=="After"&&(im.name=="chest"||im.name.StartsWith("day-reward-")&&im.name.EndsWith("icon")))Check(tex.mipmapCount>1&&tex.filterMode==FilterMode.Trilinear,"Detailed artwork filtered: "+im.name);
            }
            if(phase=="After"){string dir=Path.Combine(Application.dataPath,"../UIClarityReports");var before=Directory.Exists(dir)?Directory.GetDirectories(dir):new string[0];UIClarityGuard.AuditLive();var added=Directory.GetDirectories(dir).Except(before).Single();File.Copy(Path.Combine(added,"Live_UI_Audit.txt"),Path.Combine(Output,Path.GetFileNameWithoutExtension(file)+"_Live.txt"),true);}
        }
        static void Tick(){try{if(EditorApplication.timeSinceStartup-began>240)throw new TimeoutException("Clarity review timeout");if(!string.IsNullOrEmpty(report.error))throw new Exception(report.error);if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating||EditorApplication.timeSinceStartup<next)return;
            if(!home){home=UnityEngine.Object.FindFirstObjectByType<HomePage>();if(!home||!home.GetComponent<PlayerProfileHost>()||!home.GetComponent<PlayerProfileHost>().Ready){home=null;return;}var start=home.GetComponent<FirstStartPage>();if(!start.Initialized){home=null;return;}if(start.IsVisible){start.Request("skip");start.Request("skip");}Check(home.GetComponent<PlayerProfileHost>().IsTransient,"Campaign is isolated");home.State.reduceMotion=true;gift=home.GetComponent<DailyGiftPage>();works=home.GetComponent<WellworksPage>();profile=home.GetComponent<ProfilePage>();Size(0);return;}
            int dim=index/3,page=index%3;if(Screen.width!=Sizes[dim].x||Screen.height!=Sizes[dim].y)return;
            if(step==0){if(page==0)gift.Show();else if(page==1)works.Show();else profile.Show();step=1;next=EditorApplication.timeSinceStartup+.3;return;}
            string prefix=(page==0?"DailyGift":page==1?"Wellworks":"Profile")+"_"+Screen.width+"x"+Screen.height;
            if(step==1){Capture(prefix+"_Idle.png");if(page==0){var nodes=Field<Dictionary<string,RectTransform>>(gift,"nodes");nodes["chest"].localScale=Vector3.one*1.12f;nodes["reward"].localScale=Vector3.one*1.15f;}else if(page==1){Field<ScrollRect>(works,"scroll").verticalNormalizedPosition=0;}step=2;next=EditorApplication.timeSinceStartup+.2;return;}
            if(page<2)Capture(prefix+(page==0?"_PeakFixture.png":"_Scrolled.png"));
            if(phase=="After"&&page==0&&dim>=3){var host=home.GetComponent<PlayerProfileHost>();for(int day=1;day<7;day++){typeof(DailyGiftPage).GetField("view",Private).SetValue(gift,new DailyGiftView{schedule=host.Schedule,development=true,claims=day,offer=new GiftOffer{step=day,grant=host.Schedule.days[day]}});typeof(DailyGiftPage).GetMethod("Render",Private).Invoke(gift,null);var nodes=Field<Dictionary<string,RectTransform>>(gift,"nodes");nodes["chest"].localScale=Vector3.one*1.12f;nodes["reward"].localScale=Vector3.one*1.15f;Capture(prefix+"_Day"+(day+1)+"_PeakFixture.png");}}
            if(page==0)gift.Hide();else if(page==1)works.Hide();else profile.Hide();index++;step=0;if(index==Sizes.Length*3){Finish(0);return;}if(index%3==0)Size(index/3);else next=EditorApplication.timeSinceStartup+.15;
        }catch(Exception e){report.error=e.ToString();Finish(1);}}
        static void Finish(int code){report.status=code==0?"PASS_NATIVE_UI_CLARITY_"+phase.ToUpperInvariant():"FAIL_NATIVE_UI_CLARITY";Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"Report.json"),JsonUtility.ToJson(report,true));EditorApplication.update-=Tick;Application.logMessageReceived-=Log;SceneManager.sceneLoaded-=Isolate;SessionState.EraseString(Key);View().GetType().GetProperty("selectedSizeIndex",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance).SetValue(View(),previous);var group=Group();for(int i=Sizes.Length-1;i>=0;i--)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{first+i});EditorApplication.Exit(code);}
    }
}
#endif

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
using HeartOfTheRain.App.Profile.Editor;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Profiling;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification
{
    [InitializeOnLoad] public static class ProfileClarityReview
    {
        const string Key="HOTR.ProfileClarity";
        static readonly int[] Sizes={0,0,0,0,1,1,2,3,4,0,0,0,0,0};
        static readonly Vector2Int[] Dimensions={new Vector2Int(393,852),new Vector2Int(320,480),new Vector2Int(768,1024),new Vector2Int(900,2000),new Vector2Int(320,568)};
        static readonly string[] Ids={"Stat_Level","Stat_Chapter","Stat_Progress","Stat_Stars","FrameGold","FrameSapphire","FrameIvory","FrameRainkeeperGold","FrameLanternSapphire","FrameGardenIvory","Banner_Village","Banner_Lantern","Banner_Twilight"};
        static int index,originalLocale;static double started,readyAt;static string phase,ordinary;static Report report;
        [Serializable] sealed class Report {public string utc,unity,status,error,phase,scope="Native Unity Editor/Play Mode, isolated review-memory profile. Original textures at native display resolution; not Android/device or physical GPU memory certification.";public int checks;public long textureBytes;public List<string> frames=new List<string>();public List<TextureInfo> textures=new List<TextureInfo>();public List<GraphicInfo> graphics=new List<GraphicInfo>();}
        [Serializable] sealed class TextureInfo {public string id,path,format,filter,guid;public int width,height,mips;public bool readable,packed;public long bytes;}
        [Serializable] sealed class GraphicInfo {public string name,texture,filter;public int frame,mips;public float sourceWidth,sourceHeight,physicalWidth,physicalHeight;public bool white,preserveAspect,packed;}
        static string Output=>Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW98_OUT")??"../Verification/Evidence/ProfileClarity/"+phase);
        static ProfileClarityReview(){phase=SessionState.GetString(Key,"");if(phase!=""){started=readyAt=EditorApplication.timeSinceStartup;report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,phase=phase};originalLocale=GameLocale.Current;ordinary=PlayerPrefs.GetString(ProfileStore.Key,"<absent>");EditorApplication.update+=Tick;Application.logMessageReceived+=Log;}}
        public static void Before()=>Run("Before");public static void After()=>Run("After");
        static void Run(string p){SessionState.SetString(Key,p);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");UnityEngine.Object.FindFirstObjectByType<FirstStartPage>().reviewAlways=true;typeof(ProfileM71Verification).GetMethod("SetupSizes",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);EditorApplication.isPlaying=true;}
        static string[] Paths(){var assets=Resources.Load<ProfileAssets>("HeartOfTheRainProfile/Config");return Ids.Select(id=>AssetDatabase.GetAssetPath(assets.sprites.Single(s=>s.id==id).sprite.texture)).ToArray();}
        public static void Apply()
        {
            Selection.objects=Paths().Select(p=>AssetDatabase.LoadAssetAtPath<Texture2D>(p)).ToArray();
            ProfileClarityTools.AuditSelected();ProfileClarityTools.FixSelected();
            foreach(var path in Paths()){var importer=(TextureImporter)AssetImporter.GetAtPath(path);if(!importer.mipmapEnabled||importer.filterMode!=FilterMode.Trilinear)throw new Exception("Clarity import not applied: "+path);}
            AssetDatabase.SaveAssets();
        }
        static void Check(bool ok,string message){report.checks++;if(!ok)throw new InvalidOperationException(message);}
        static void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.error=message+"\n"+stack;}
        static void Call(ProfilePage page,string method)=>typeof(ProfilePage).GetMethod(method,BindingFlags.Instance|BindingFlags.NonPublic).Invoke(page,null);
        static void Click(ProfilePage page,string name)=>page.GetComponentsInChildren<Button>().Single(b=>b.name==name).onClick.Invoke();
        static void Tick()
        {
            try
            {
                if(EditorApplication.timeSinceStartup-started>180)throw new TimeoutException("Profile clarity review timed out");
                if(!string.IsNullOrEmpty(report.error))throw new InvalidOperationException(report.error);
                if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating||EditorApplication.timeSinceStartup-readyAt<.6)return;
                var home=UnityEngine.Object.FindFirstObjectByType<HomePage>();if(!home||!home.GetComponent<PlayerProfileHost>()||!home.GetComponent<PlayerProfileHost>().Ready)return;
                var page=home.GetComponent<ProfilePage>();if(!page||!page.IsPrepared)return;
                int size=Sizes[index];if(Screen.width!=Dimensions[size].x||Screen.height!=Dimensions[size].y){readyAt=EditorApplication.timeSinceStartup;return;}
                Check(home.GetComponent<PlayerProfileHost>().IsTransient,"Campaign is not isolated");
                var first=home.GetComponent<FirstStartPage>();if(first.IsVisible){first.Request("skip");first.Request("skip");}
                if(page.IsVisible)page.Hide();GameLocale.Select(index>=9&&index<=12?index-8:0);
                home.State.currentLevel=12;home.State.chapterNumber=1;home.State.completedLevelsInChapter=11;home.State.levelsPerChapter=50;home.State.stars=24;home.ApplyState(home.State);Capture(home,null);
                home.GetComponentsInChildren<HomeControlLabel>().Single(c=>c.action=="profile").GetComponent<Button>().onClick.Invoke();Check(page.IsVisible,"Profile did not open");
                Click(page,"Tab 0");Click(page,"Choice Dariya");Click(page,"Tab 1");string banner=index==1?"Lantern":index==2?"Twilight":"Village";Click(page,"Choice "+banner);
                Click(page,"Tab 2");string frame=index==1?"LanternSapphire":index==2?"GardenIvory":index==3?"Gold":"RainkeeperGold";Click(page,"Choice "+frame);
                if(index==0)
                {
                    var assets=Resources.Load<ProfileAssets>("HeartOfTheRainProfile/Config");
                    foreach(var id in Ids)
                    {
                        var sprite=assets.Find(id);var t=sprite.texture;Check(!sprite.packed,"Packed source needs independent atlas review");
                        var info=new TextureInfo{id=id,path=AssetDatabase.GetAssetPath(t),width=t.width,height=t.height,format=t.format.ToString(),filter=t.filterMode.ToString(),mips=t.mipmapCount,readable=t.isReadable,packed=sprite.packed,bytes=Profiler.GetRuntimeMemorySizeLong(t),guid=AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(t))};
                        report.textures.Add(info);report.textureBytes+=info.bytes;
                        Check(phase=="Before"?t.mipmapCount==1&&t.filterMode==FilterMode.Bilinear:t.mipmapCount>1&&t.filterMode==FilterMode.Trilinear,"Unexpected sampling: "+id);
                    }
                    foreach(var id in ProfileRules.Frames){Click(page,"Choice "+id);var r=home.GetComponentsInChildren<RectTransform>().Single(t=>t.name=="Selected profile avatar");var header=home.GetComponentsInChildren<RectTransform>().Single(t=>t.name=="header");Check(Mathf.Abs(r.rect.width-r.rect.height)<.01f&&Mathf.Abs(r.rect.width-header.rect.width*.17f)<.01f,"Home avatar footprint changed");}
                    Click(page,"Choice "+frame);
                }
                int tab=index==3||index==13?2:3;Click(page,"Tab "+tab);Canvas.ForceUpdateCanvases();
                var inner=page.GetComponentsInChildren<ScrollRect>().Single(s=>s.name=="Collection viewport");var outer=page.GetComponentsInChildren<ScrollRect>().Single(s=>s.name=="Profile Safe Area");
                if(size==1||size==2||size==4)outer.verticalNormalizedPosition=0;inner.verticalNormalizedPosition=index==5||index==8||index==13?0:1;
                string file=$"{index:00}_{banner}_{frame}_Tab{tab}_{GameLocale.Codes[GameLocale.Current]}_{Screen.width}x{Screen.height}.png";Capture(home,Path.Combine(Output,file));report.frames.Add(file);
                foreach(var image in page.GetComponentsInChildren<Image>().Where(i=>i.name.StartsWith("Stat icon ")||i.name=="Frame"))
                {
                    var corners=new Vector3[4];image.rectTransform.GetWorldCorners(corners);var points=corners.Select(c=>RectTransformUtility.WorldToScreenPoint(null,c)).ToArray();var sprite=image.sprite;var t=sprite.texture;
                    report.graphics.Add(new GraphicInfo{frame=index,name=image.name,texture=t.name,filter=t.filterMode.ToString(),mips=t.mipmapCount,sourceWidth=sprite.rect.width,sourceHeight=sprite.rect.height,physicalWidth=points.Max(p=>p.x)-points.Min(p=>p.x),physicalHeight=points.Max(p=>p.y)-points.Min(p=>p.y),white=image.color==Color.white,preserveAspect=image.preserveAspect,packed=sprite.packed});
                    Check(image.color==Color.white&&!sprite.packed,"Tint or packing changed");
                    if(image.name.StartsWith("Stat icon "))Check(image.preserveAspect,"Stat aspect was lost");
                }
                if(tab==3)
                {
                    foreach(var text in page.GetComponentsInChildren<Text>().Where(t=>t.name.StartsWith("Stat label "))){var gen=new TextGenerator();gen.Populate(text.text,text.GetGenerationSettings(text.rectTransform.rect.size));Check(gen.characterCountVisible>=text.text.Length,"Stats label clipped");}
                    Check(page.GetComponentsInChildren<Text>().Single(t=>t.name=="Stat value 0").text=="12"&&page.GetComponentsInChildren<Text>().Single(t=>t.name=="Stat value 3").text=="24","Live stat binding changed");
                }
                ProfileClarityTools.AuditGraphics();Check(PlayerPrefs.GetString(ProfileStore.Key,"<absent>")==ordinary,"Ordinary appearance changed");page.Hide();Check(home.PresentationInteractable,"Home did not regain input");
                index++;if(index==Sizes.Length){Finish(0);return;}
                if(Sizes[index]!=size){var view=EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(view,SessionState.GetInt("HOTR.M71.Verification.first",0)+Sizes[index]);view.Repaint();}readyAt=EditorApplication.timeSinceStartup;
            }
            catch(Exception e){report.error=e.ToString();Finish(1);}
        }
        static void Capture(HomePage home,string path){path=path??Path.GetFullPath("../.verification-cache/ProfileClarityR2/Prime.png");Directory.CreateDirectory(Path.GetDirectoryName(path));typeof(HomeLevelButtonReview).GetMethod("Capture",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{home,path});}
        static void Finish(int code)
        {
            report.status=code==0?"PASS_NATIVE_PROFILE_CLARITY":"FAIL_NATIVE_PROFILE_CLARITY";Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"Native_Review.json"),JsonUtility.ToJson(report,true));GameLocale.Select(originalLocale);EditorApplication.update-=Tick;Application.logMessageReceived-=Log;SessionState.EraseString(Key);
            var view=EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(view,SessionState.GetInt("HOTR.M71.Verification.previous",0));var group=typeof(ProfileM71Verification).GetMethod("Group",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,null);for(int n=4;n>=0;n--)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{SessionState.GetInt("HOTR.M71.Verification.first",0)+n});EditorApplication.Exit(code);
        }
    }
}
#endif

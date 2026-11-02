#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.Verification
{
    public static class RewardedHome135Verification
    {
        static void Need(bool value,string message){if(!value)throw new InvalidOperationException(message);}
        static HomeElement Find(HomeFrame frame,string id)=>frame.elements.Single(e=>e.id==id);
        static void Within(HomeFrame frame,string child,string parent)
        {
            var a=Find(frame,child);var b=Find(frame,parent);
            Need(a.x>=-.01f&&a.y>=-.01f&&a.x+a.width<=b.width+.01f&&a.y+a.height<=b.height+.01f,child+" escapes "+parent);
        }
        public static void Run()
        {
            string output=Path.GetFullPath("../Verification/Evidence/RewardedHome135");Directory.CreateDirectory(output);
            string result="FAIL";string detail="";
            try
            {
                var assets=AssetDatabase.LoadAssetAtPath<HomePageAssets>("Assets/HeartOfTheRain/App/Home/HomePageAssets.asset");
                Need(assets!=null&&assets.Find("Rewarded_Video_Icon")!=null&&assets.Find("R3_Ribbon")!=null,"Home video assets are unbound");
                var icon=assets.Find("Rewarded_Video_Icon");Need(icon.texture.width==512&&icon.texture.height==512,"Rewarded icon resolution changed");
                var importer=AssetImporter.GetAtPath("Assets/HeartOfTheRain/App/Home/Art/Rewarded_Video_Icon.png") as TextureImporter;
                Need(importer!=null&&importer.textureType==TextureImporterType.Sprite&&importer.spriteImportMode==SpriteImportMode.Single,"Rewarded icon is not a single Sprite");
                int old=GameLocale.Current;try
                {
                    GameLocale.Select(4);
                    foreach(var size in new[]{new Vector2Int(360,640),new Vector2Int(390,844),new Vector2Int(347,780),new Vector2Int(320,480)})
                    {
                        var state=new HomeState{rewardedVisible=true,rewardedEligible=true,rewardedStatus="●"};
                        var frame=HomeLayoutEngine.Build(size.x,size.y,state);
                        if(frame.compact)
                        {
                            Need(frame.elements.Any(e=>e.id=="events"),"Compact layout has no event drawer entry: "+size);
                        }
                        else
                        {
                            var video=Find(frame,"video");var team=Find(frame,"team");var progress=Find(frame,"progress");
                            Need(video.action=="video"&&video.y>=team.y+team.height-.01f,"Video is not below Team Quest: "+size);
                            Need(video.x>=0&&video.x+video.width<=frame.width&&video.y+video.height<=progress.y,"Video overlaps level controls: "+size);
                            foreach(var part in new[]{"icon","ribbon","title","plate","status"})Within(frame,"video-"+part,"video");
                            Need(Find(frame,"video-title").text=="Видео","Russian Video label is missing");
                        }
                        var drawer=HomeLayoutEngine.Build(size.x,size.y,state,true);
                        var drawerVideo=Find(drawer,"drawer-video");var drawerTeam=Find(drawer,"drawer-team");
                        Need(drawerVideo.action=="video"&&drawerVideo.y>=drawerTeam.y+drawerTeam.height-.01f,"Drawer video is not below Team Quest: "+size);
                        Need(drawerVideo.y+drawerVideo.height<=Find(drawer,"drawer-panel").y+Find(drawer,"drawer-panel").height+.01f,"Drawer video is clipped: "+size);
                        foreach(var part in new[]{"icon","ribbon","title","plate","status"})Within(drawer,"drawer-video-"+part,"drawer-video");
                        var hidden=HomeLayoutEngine.Build(size.x,size.y,new HomeState());
                        Need(!hidden.elements.Any(e=>e.id=="video"||e.id=="drawer-video"),"Disabled shortcut remains visible");
                    }
                }
                finally{GameLocale.Select(old);}
                result="PASS";detail="Unity 2022 import, Russian label, rail/drawer geometry at 360x640, 390x844, 347x780 and 320x480; no ad grant or device assertion.";
            }
            catch(Exception ex){detail=ex.ToString();Debug.LogException(ex);}
            File.WriteAllText(Path.Combine(output,"Check.txt"),"status="+result+"\nunity="+Application.unityVersion+"\n"+detail+"\n");
            if(result!="PASS")EditorApplication.Exit(1);
        }
    }
}
#endif

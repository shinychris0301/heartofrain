#if UNITY_EDITOR
using System;
using System.IO;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using HeartOfTheRain.App.Home;
namespace HeartOfTheRain.App.Profile.Editor
{
    public static class ProfileReview
    {
        [MenuItem("Heart of the Rain/App/M71 R2/Open Home and Profile Review")]
        public static void Open(){if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/PreLevel/Scenes/M56_Home_PreLevel.unity");}
        [MenuItem("Heart of the Rain/App/M71 R2/Show Profile in Play Mode")]
        public static void Show(){var h=UnityEngine.Object.FindFirstObjectByType<HomePage>();if(!Application.isPlaying||!h){Debug.LogWarning("Open the Home review scene and enter Play Mode first.");return;}ProfilePage.Attach(h).Show();}
        [MenuItem("Heart of the Rain/App/M71 R2/Validate Profile Assets and Name Rules")]
        public static void Validate()
        {
            var a=Resources.Load<ProfileAssets>("HeartOfTheRainProfile/Config");Require(a&&a.home,"Missing Profile config/Home reference");
            Require(a.profileFont,"Missing rounded Black font");
            foreach(var id in ProfileRules.Avatars)Require(a.Find("Avatar_"+id),"Missing avatar "+id);
            foreach(var id in ProfileRules.Banners)Require(a.Find("Banner_"+id),"Missing banner "+id);
            foreach(var id in ProfileRules.Frames)Require(a.Find("Frame"+id),"Missing frame "+id);
            foreach(var id in new[]{"Stat_Level","Stat_Chapter","Stat_Progress","Stat_Stars","Progress_Track","Progress_Fill"})Require(a.Find(id),"Missing design kit art "+id);
            foreach(var s in new[]{"ProfileChrome","RenameChrome","FrameGold","FrameSapphire","FrameIvory","TabActive","TabInactive","Primary","Input","RoundMask","CloseSource","CheckSource","PencilSource","Team"})Require(a.Find(s),"Missing art "+s);
            string clean,error;Require(!ProfileRules.TryName("  ",out clean,out error),"Blank name accepted");
            Require(ProfileRules.TryName("  Élodie  ",out clean,out error)&&clean=="Élodie","Accent or trim failed");
            Require(ProfileRules.TryName("Дарья",out clean,out error)&&clean=="Дарья","Russian name failed");
            Require(ProfileRules.TryName("Jose\u0301",out clean,out error)&&clean=="José","Normalization failed");
            Require(!ProfileRules.TryName(new string('a',21),out clean,out error),"Length limit failed");
            Require(!ProfileRules.TryName("Ivan\nX",out clean,out error),"Control character accepted");
            Require(!ProfileRules.TryName("x\ud800",out clean,out error),"Invalid surrogate accepted");
            var d=ProfileRules.Sanitize(new ProfileData {avatarId="old-id",bannerId="missing",frameId="missing"});
            Require(d.avatarId=="Ivan"&&d.bannerId=="Village"&&d.frameId=="Gold","Unknown saved IDs not repaired");
            foreach(var entry in ProfileText.Entries)Require(entry.Value.Length==5,"Incomplete locale: "+entry.Key);
            Debug.Log("M71 asset bindings and pure name rules passed in Unity Editor. Run native interaction and device checks separately.");
        }
        static void Require(bool condition,string message){if(!condition)throw new Exception(message);}
        [MenuItem("Heart of the Rain/App/M71 R2/Capture Actual Profile Game View")]
        public static void Capture()
        {
            var p=UnityEngine.Object.FindFirstObjectByType<ProfilePage>();if(!Application.isPlaying||!p||!p.IsVisible){Debug.LogWarning("Open Profile in Play Mode first.");return;}
            var path=Path.GetFullPath("../ReviewCaptures");Directory.CreateDirectory(path);ScreenCapture.CaptureScreenshot(Path.Combine(path,"M71_Profile_"+DateTime.Now.ToString("yyyyMMdd_HHmmss")+".png"));
        }
    }
}
#endif

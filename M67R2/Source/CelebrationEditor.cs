#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace HeartOfTheRain.App.Celebrations.Editor
{
    public static class CelebrationEditor
    {
        const string Root="Assets/HeartOfTheRain/App/Celebrations/";
        [MenuItem("Heart of the Rain/App/M67 R2/Open Daria Celebration Review")]
        public static void Daria(){Open("M67_Daria_Celebration");}
        [MenuItem("Heart of the Rain/App/M67 R2/Open Chapter 1 Finale Review")]
        public static void Finale(){Open("M67_Chapter01_Finale");}
        static void Open(string name){if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene(Root+"Scenes/"+name+".unity");}
        [MenuItem("Heart of the Rain/App/M67 R2/Validate Celebration Assets")]
        public static void Validate()
        {
            var a=CelebrationAssets.Load();if(!a||!a.ui||!a.dariaAtlas||!a.dariaBlend)throw new Exception("Missing M67 UI, atlas or shader binding");
            if(a.dariaAtlas.width!=a.dariaAtlas.height)throw new Exception("Daria atlas must have four columns and four square rows");
            foreach(var c in a.chapters)if(!c.restoration||!c.hook||c.captions==null||c.captions.Length!=3)throw new Exception("Incomplete chapter celebration art");
            Debug.Log("M67 bindings verified. Review actual rendering and shader compilation in Play Mode.");
        }
        [MenuItem("Heart of the Rain/App/M67 R2/Capture Actual Game View")]
        public static void Capture()
        {
            if(!Application.isPlaying){Debug.LogWarning("Enter Play Mode first.");return;}
            string dir=Path.GetFullPath("../ReviewCaptures");Directory.CreateDirectory(dir);
            ScreenCapture.CaptureScreenshot(Path.Combine(dir,"M67_"+DateTime.Now.ToString("yyyyMMdd_HHmmss")+".png"));
        }
    }
}
#endif

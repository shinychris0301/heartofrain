#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace HeartOfTheRain.App.PreLevel.Editor
{
    public static class PreLevelReview
    {
        const string Root="Assets/HeartOfTheRain/App/PreLevel";
        [MenuItem("Heart of the Rain/App/M56/Open Home to Pre-level Review")]
        public static void Open()
        {
            if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene(Root+"/Scenes/M56_Home_PreLevel.unity");
        }
        [MenuItem("Heart of the Rain/App/M56/Validate Pre-level Artwork")]
        public static void ValidateArt()
        {
            int count=0;foreach(string guid in AssetDatabase.FindAssets("t:Texture2D",new[]{Root+"/Art"}))
            {
                string path=AssetDatabase.GUIDToAssetPath(guid);var t=(TextureImporter)AssetImporter.GetAtPath(path);
                if(!t.sRGBTexture||t.mipmapEnabled||t.textureCompression!=TextureImporterCompression.Uncompressed)throw new System.Exception("Home-style import mismatch: "+path);
                count++;
            }
            var a=AssetDatabase.LoadAssetAtPath<PreLevelAssets>(Root+"/PreLevelAssets.asset");
            if(!a||!a.home||!a.gameplay||a.gameplay.boards.levels.Length!=50)throw new System.Exception("Missing Home/gameplay/level bindings.");
            Debug.Log("M56 bindings and "+count+" sprite imports pass. Inspect Play mode for actual color, font and interaction parity.");
        }
        [MenuItem("Heart of the Rain/App/M56/Capture Actual Game View")]
        public static void Capture()
        {
            if(!Application.isPlaying){Debug.LogWarning("Enter Play mode and open the pre-level modal first.");return;}
            string dir=Path.GetFullPath("../ReviewCaptures");Directory.CreateDirectory(dir);
            string path=Path.Combine(dir,"M56_GameView_"+System.DateTime.Now.ToString("yyyyMMdd_HHmmss")+".png");
            ScreenCapture.CaptureScreenshot(path);Debug.Log("Queued actual Game view capture: "+path);
        }
    }
    public sealed class PreLevelArtImportPolicy:AssetPostprocessor
    {
        void OnPreprocessTexture()
        {
            if(!assetPath.StartsWith("Assets/HeartOfTheRain/App/PreLevel/Art/",System.StringComparison.Ordinal))return;
            var t=(TextureImporter)assetImporter;t.textureType=TextureImporterType.Sprite;t.spriteImportMode=SpriteImportMode.Single;
            t.sRGBTexture=true;t.mipmapEnabled=false;t.alphaIsTransparency=true;t.textureCompression=TextureImporterCompression.Uncompressed;t.crunchedCompression=false;
            t.npotScale=TextureImporterNPOTScale.None;t.maxTextureSize=2048;t.filterMode=FilterMode.Bilinear;t.wrapMode=TextureWrapMode.Clamp;
            foreach(string name in new[]{"Android","iPhone","Standalone"}){var p=t.GetPlatformTextureSettings(name);p.overridden=false;t.SetPlatformTextureSettings(p);}
        }
    }
    [CustomEditor(typeof(HomeLevelFlow))]
    public sealed class FlowInspector:UnityEditor.Editor
    {
        public override void OnInspectorGUI()
        {
            DrawDefaultInspector();if(!Application.isPlaying)return;var flow=(HomeLevelFlow)target;
            if(GUILayout.Button("Open current level preview"))flow.Open(flow.home.State.currentLevel);
            if(GUILayout.Button("Return Home (review only)"))flow.ReturnHomeForReview();
            EditorGUILayout.HelpBox("Home → pre-level → gameplay includes M57 settings when settingsAssets is assigned. M58 provides the designed life-loss confirmation when endLevelAssets is assigned. M59 opens Try Again automatically after confirmed exit. Reward settlement and persistent inventory remain future milestones. Initial stock and rewards are review values.",MessageType.Info);
        }
    }
}
#endif

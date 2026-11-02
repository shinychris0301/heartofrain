#if UNITY_EDITOR
using System.IO;
using System.Linq;
using HeartOfTheRain.App.Launch;
using UnityEditor;
using UnityEditor.Android;
using UnityEditor.Build;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace HeartOfTheRain.App.Launch.Editor
{
    public static class LaunchSetup
    {
        public const string Art="Assets/HeartOfTheRain/App/Launch/Art/";
        public const string TitlePath=Art+"Title_Logo_RU_R1.png";
        // Query the supported fallback kind without invoking its deprecated constant.
        public static PlatformIconKind LegacyIconKind=>PlayerSettings.GetSupportedIconKinds(NamedBuildTarget.Android).Single(kind=>kind.ToString()=="Legacy");
        public static void Configure()
        {
            foreach(var name in new[]{"App_Icon_R1","Opening_Key_Art_R1","Title_Logo_R1"})
            {
                var importer=(TextureImporter)AssetImporter.GetAtPath(Art+name+".png");
                importer.textureType=TextureImporterType.Default;importer.sRGBTexture=true;importer.mipmapEnabled=false;importer.isReadable=false;
                importer.npotScale=TextureImporterNPOTScale.None;importer.maxTextureSize=2048;importer.wrapMode=TextureWrapMode.Clamp;importer.filterMode=FilterMode.Bilinear;
                importer.textureCompression=TextureImporterCompression.Uncompressed;importer.alphaIsTransparency=name=="Title_Logo_R1";importer.SaveAndReimport();
            }
            var icon=AssetDatabase.LoadAssetAtPath<Texture2D>(Art+"App_Icon_R1.png");
            var slots=PlayerSettings.GetPlatformIcons(NamedBuildTarget.Android,LegacyIconKind);
            foreach(var slot in slots)slot.SetTexture(icon);
            PlayerSettings.SetPlatformIcons(NamedBuildTarget.Android,LegacyIconKind,slots);
            // No invented adaptive cutouts: retain the flat source as legacy art.
            Directory.CreateDirectory(Path.GetDirectoryName(LaunchPage.ScenePath));
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var camera=new GameObject("Launch camera").AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.035f,.085f,.16f);camera.orthographic=true;
            var launch=new GameObject("Heart of the Rain Launch").AddComponent<LaunchPage>();
            launch.keyArt=AssetDatabase.LoadAssetAtPath<Texture2D>(Art+"Opening_Key_Art_R1.png");
            launch.title=AssetDatabase.LoadAssetAtPath<Texture2D>(TitlePath);
            launch.font=AssetDatabase.LoadAssetAtPath<Font>("Assets/HeartOfTheRain/App/Profile/Art/ProfileBlack.ttf");
            BindLoadingBar(launch);
            EditorSceneManager.SaveScene(scene,LaunchPage.ScenePath);
            EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(LaunchPage.ScenePath,true)}.Concat(EditorBuildSettings.scenes.Where(s=>s.path!=LaunchPage.ScenePath)).ToArray();
            AssetDatabase.SaveAssets();
        }
        public static void ConfigureLoadingBar()
        {
            var scene=EditorSceneManager.OpenScene(LaunchPage.ScenePath);
            BindLoadingBar(Object.FindFirstObjectByType<LaunchPage>());
            EditorSceneManager.SaveScene(scene);AssetDatabase.SaveAssets();
        }
        static void BindLoadingBar(LaunchPage launch)
        {
            launch.loadingTrack=AssetDatabase.LoadAssetAtPath<Sprite>(Art+"Loading_Track.png");
            launch.loadingFill=AssetDatabase.LoadAssetAtPath<Sprite>(Art+"Loading_Fill.png");
            launch.loadingFrame=AssetDatabase.LoadAssetAtPath<Sprite>(Art+"Loading_Frame.png");
            if(!launch.loadingTrack||!launch.loadingFill||!launch.loadingFrame)throw new System.InvalidOperationException("Missing loading-bar sprites.");
        }
    }
}
#endif

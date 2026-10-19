using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.M48 {
    [InitializeOnLoad]
    public static class M48ReviewMenu {
        public const string Scene="Assets/HeartOfTheRain/M48/Scenes/M48_Chapter01_Review.unity";
        const string Root="Assets/HeartOfTheRain/M48/";
        static M48ReviewMenu(){EditorApplication.delayCall+=()=>{if(File.Exists(".m48-review-project")&&!File.Exists("ProjectSettings/M48Configured.txt")){Configure();File.WriteAllText("ProjectSettings/M48Configured.txt","M48 review defaults applied");}};}
        [MenuItem("Heart of the Rain/M48/1 Open Review Scene")]
        public static void Open(){if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene(Scene);}
        [MenuItem("Heart of the Rain/M48/2 Configure Review Project")]
        public static void Configure(){
            PlayerSettings.companyName="Heart of the Rain";PlayerSettings.productName="Heart of the Rain - M48 Review";
            PlayerSettings.colorSpace=ColorSpace.Gamma;PlayerSettings.defaultInterfaceOrientation=UIOrientation.Portrait;
            PlayerSettings.defaultScreenWidth=720;PlayerSettings.defaultScreenHeight=1280;PlayerSettings.runInBackground=false;
            PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android,"com.heartoftherain.m48review");
            PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android,ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures=AndroidArchitecture.ARM64;
            PlayerSettings.Android.minSdkVersion=AndroidSdkVersions.AndroidApiLevel26;
            PlayerSettings.Android.targetSdkVersion=AndroidSdkVersions.AndroidApiLevelAuto;
            EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(Scene,true)};
            var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>(Root+"M48GameplayUIAssets.asset");
            if(ui==null)throw new Exception("Missing M48 gameplay UI binding");
            ui.bodyShader=Shader.Find("Sprites/Default");if(ui.bodyShader==null)throw new Exception("Built-in sprite shader missing");EditorUtility.SetDirty(ui);
            AssetDatabase.SaveAssets();Debug.Log("M48 review defaults configured. These are internal review settings, not store-release settings.");
        }
        [Serializable] sealed class ImportReport {public string status="FAIL_UNITY_IMPORT_VALIDATION",milestone="M54 R1",unity,utc;public int levels,resources,uiSprites,audio;public CampaignValidationReport campaign;public List<string> errors=new List<string>();public string rendering="NOT_TESTED_BY_THIS_COMMAND",devicePerformance="NOT_TESTED_BY_THIS_COMMAND";}
        [Serializable] sealed class Catalog {public ResourceRecord[] textures;}
        [Serializable] sealed class ResourceRecord {public string path;public int width,height;}
        [MenuItem("Heart of the Rain/M48/3 Validate Imported Assets")]
        public static void Validate(){
            var report=new ImportReport{unity=Application.unityVersion,utc=DateTime.UtcNow.ToString("o")};
            try {
            if(PlayerSettings.colorSpace!=ColorSpace.Gamma)throw new Exception("Approved review baseline requires Gamma color space; run Configure Review Project.");
            var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>(Root+"M48GameplayUIAssets.asset");
            if(ui==null||ui.boards==null)throw new Exception("Missing M48 UI or board binding");
            if(ui.bodyShader==null)throw new Exception("Run M48 > 2 Configure Review Project to bind the built-in sprite shader before building");
            var a=ui.boards;if(a.levels.Length!=50||a.surfaceResources.Length!=50||a.maskResources.Length!=50)throw new Exception("Expected 50 level, surface and mask bindings");
            var replayAsset=Resources.Load<TextAsset>("HOTR_Playtests/Campaign_Replays");
            report.campaign=CampaignValidation.Run(a.levels.Select(l=>l==null?null:JsonUtility.FromJson<LevelData>(l.text)).ToArray(),replayAsset==null?null:JsonUtility.FromJson<CampaignReplaySet>(replayAsset.text));
            if(report.campaign.errors.Count>0)throw new Exception("Campaign validation failed; see campaign.errors in the JSON report.");
            foreach(var s in ui.sprites)if(s.sprite==null)throw new Exception("Missing UI sprite: "+s.id);
            foreach(var c in ui.sounds)if(c.clip==null)throw new Exception("Missing audio: "+c.id);
            if(ui.regular==null||ui.bold==null)throw new Exception("Missing font");
            var catalog=JsonUtility.FromJson<Catalog>(File.ReadAllText(Root+"Data/Resource_Catalog.json"));
            foreach(var r in catalog.textures){var texture=AssetDatabase.LoadAssetAtPath<Texture2D>(r.path);if(texture==null||texture.width!=r.width||texture.height!=r.height)throw new Exception("Missing or resized texture: "+r.path);var importer=AssetImporter.GetAtPath(r.path) as TextureImporter;if(importer==null||importer.mipmapEnabled||importer.isReadable||!importer.sRGBTexture)throw new Exception("Unexpected texture import settings: "+r.path);}
            if(a.powerAtlases.Any(t=>t!=null)||a.surfaces.Any(t=>t!=null)||a.masks.Any(t=>t!=null)||a.bodies.Any(b=>b.texture!=null)||a.obstacleClips.Any(c=>c.pages.Any(t=>t!=null)))throw new Exception("Main binding unexpectedly holds texture references");
            if(a.effectsMaterial==null||a.tileGlowMaterial==null||!a.effectsMaterial.shader.isSupported||!a.tileGlowMaterial.shader.isSupported)throw new Exception("Required sprite shader is unsupported");
            report.levels=50;report.resources=catalog.textures.Length;report.uiSprites=ui.sprites.Length;report.audio=ui.sounds.Length;report.status="PASS_UNITY_IMPORT_VALIDATION";
            } catch(Exception ex){report.errors.Add(ex.ToString());}
            finally {Directory.CreateDirectory("Builds/Validation");File.WriteAllText("Builds/Validation/Unity_Import_Report.json",JsonUtility.ToJson(report,true));}
            if(report.errors.Count>0)throw new Exception("M54 validation failed. See Builds/Validation/Unity_Import_Report.json. "+report.errors[0]);
            Debug.Log("M54 import and campaign validation passed: 50 openings and 5 recorded clears. Rendering, playback and phone profiling remain separate checks.");
        }
        [MenuItem("Heart of the Rain/M48/5 Open Local Playtest Reports")]
        public static void OpenPlaytestReports(){var folder=Path.Combine(Application.persistentDataPath,"M48Review");Directory.CreateDirectory(folder);EditorUtility.RevealInFinder(folder);}
        [MenuItem("Heart of the Rain/M48/Build/Windows Review")]
        public static void BuildWindows(){Build(BuildTarget.StandaloneWindows64,"Builds/Windows/HeartOfTheRain_M48.exe");}
        [MenuItem("Heart of the Rain/M48/Build/Android Review APK")]
        public static void BuildAndroid(){EditorUserBuildSettings.buildAppBundle=false;Build(BuildTarget.Android,"Builds/Android/HeartOfTheRain_M48.apk");}
        static void Build(BuildTarget target,string output){
            if(!BuildPipeline.IsBuildTargetSupported(BuildPipeline.GetBuildTargetGroup(target),target))throw new Exception("Install Unity build support for "+target);
            Configure();Validate();Directory.CreateDirectory(Path.GetDirectoryName(output));
            var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{Scene},locationPathName=output,target=target,options=BuildOptions.Development});
            if(report.summary.result!=BuildResult.Succeeded)throw new Exception("M48 build failed: "+report.summary.result);
            Debug.Log("M48 review build: "+Path.GetFullPath(output));
        }
    }
}

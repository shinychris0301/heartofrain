#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using HeartOfTheRain.App.PreLevel;

public static class Connected84FixtureBuild {
    const string Package="com.heartoftherain.connected84fixture";
    [Serializable] sealed class InputRow {public string path,sha256;}
    [Serializable] sealed class Inputs {public InputRow[] files;}
    [Serializable] sealed class Result {
        public string status="FAIL_ISOLATED_CONNECTED84_ANDROID_ASSEMBLY",utc,unity,package=Package,result,apkSHA256,baselineManifestSHA256;
        public int errors,warnings,baselineAssetInputs;public bool development=true,arm64=true,il2cpp=true,min26=true,noPaySdkDefine,exactBaselineAssetsBefore,exactBaselineAssetsAfter;
        public List<string> permittedFixtureSettings=new List<string>(),errorsStatic=new List<string>();
    }
    static string Sha(string file){using(var stream=File.OpenRead(file))using(var hash=SHA256.Create())return string.Concat(hash.ComputeHash(stream).Select(b=>b.ToString("x2")));}
    static void CheckAssets(Inputs source){foreach(var row in source.files)if(!File.Exists(row.path)||Sha(row.path)!=row.sha256)throw new InvalidOperationException("FrozenAssetInputChanged");}
    public static void Build(){
        Directory.CreateDirectory("Build");var output=new Result{utc=DateTime.UtcNow.ToString("O"),unity=Application.unityVersion};
        try{
            if(Application.unityVersion!="2022.3.62f3")throw new InvalidOperationException("PinnedUnityRequired");
            string project=Path.GetFullPath(".");if(!project.Replace('\\','/').Contains("/.verification-cache/Connected84/"))throw new InvalidOperationException("IsolatedCacheProjectRequired");
            var inputs=JsonUtility.FromJson<Inputs>(File.ReadAllText("Connected84_BaselineAssets.json"));if(inputs?.files==null||inputs.files.Length<5000)throw new InvalidOperationException("FrozenAssetManifestRequired");output.baselineAssetInputs=inputs.files.Length;output.baselineManifestSHA256=File.ReadAllText("Connected84_BaselineManifest.sha256").Trim();CheckAssets(inputs);output.exactBaselineAssetsBefore=true;
            EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.Android,BuildTarget.Android);
            string symbols=PlayerSettings.GetScriptingDefineSymbolsForGroup(BuildTargetGroup.Android);if(symbols.Split(';').Any(s=>s=="HOTR_RUSTORE_PAY"||s=="HOTR_SERVER_REPLAY_WORKER"||s=="HOTR_REPLAY83_ANDROID_PROOF"))throw new InvalidOperationException("UnrelatedSdkOrWorkerDefineForbidden");output.noPaySdkDefine=true;
            if(Environment.GetEnvironmentVariable(HeartOfTheRain.App.RuStore.Editor.RuStoreReleasePreflight.ChannelVariable)=="rustore")throw new InvalidOperationException("FixtureCannotUseProductionReleaseChannel");
            PlayerSettings.companyName="HeartOfTheRainVerification";PlayerSettings.productName="Connected84QA";PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android,Package);PlayerSettings.bundleVersion="84.0";PlayerSettings.Android.bundleVersionCode=84;PlayerSettings.Android.minSdkVersion=AndroidSdkVersions.AndroidApiLevel26;PlayerSettings.Android.targetSdkVersion=(AndroidSdkVersions)35;PlayerSettings.Android.targetArchitectures=AndroidArchitecture.ARM64;PlayerSettings.Android.useCustomKeystore=false;PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android,ScriptingImplementation.IL2CPP);PlayerSettings.SetManagedStrippingLevel(BuildTargetGroup.Android,ManagedStrippingLevel.Low);PlayerSettings.insecureHttpOption=InsecureHttpOption.DevelopmentOnly;
            HeartOfTheRain.App.Editor.PortraitBuildPolicy.Configure();output.permittedFixtureSettings.AddRange(new[]{"Separate debug-signed package/product/version","Android API26+ ARM64 IL2CPP Development","HTTP permitted only in development fixture","Portrait policy and fixture-only entry scene"});
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);var bootstrap=new GameObject("ExplicitConnected84Fixture").AddComponent<Connected84FixtureBootstrap>();bootstrap.homePrefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab");bootstrap.levelAssets=AssetDatabase.LoadAssetAtPath<PreLevelAssets>("Assets/HeartOfTheRain/App/PreLevel/PreLevelAssets.asset");if(!bootstrap.homePrefab||!bootstrap.levelAssets)throw new InvalidOperationException("FrozenHomeReferencesMissing");EditorSceneManager.SaveScene(scene,"Assets/Connected84Fixture/Fixture.unity");
            var built=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{"Assets/Connected84Fixture/Fixture.unity"},target=BuildTarget.Android,locationPathName="Build/Connected84.apk",options=BuildOptions.Development});output.result=built.summary.result.ToString();output.errors=(int)built.summary.totalErrors;output.warnings=(int)built.summary.totalWarnings;CheckAssets(inputs);output.exactBaselineAssetsAfter=true;if(built.summary.result==BuildResult.Succeeded){output.apkSHA256=Sha("Build/Connected84.apk");output.status="PASS_ISOLATED_CONNECTED84_ANDROID_ASSEMBLY";}
        }catch(Exception error){output.errorsStatic.Add(error is InvalidOperationException?error.Message:error.GetType().Name);}
        File.WriteAllText("Build/Build.json",JsonUtility.ToJson(output,true),new UTF8Encoding(false));if(Application.isBatchMode)EditorApplication.Exit(output.status.StartsWith("PASS_",StringComparison.Ordinal)?0:1);
    }
}
#endif

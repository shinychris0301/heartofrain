#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.Android;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class Yandex85SdkExport {
    [Serializable] public sealed class Binding { public string path,sha256; }
    [Serializable] public sealed class Report {
        public string status="FAIL_ISOLATED_YANDEX85_GRADLE_EXPORT",utc,unity,package,output,error,apiContract;
        public int errors,warnings,minApi=26,targetApi=35;
        public bool noSdkInitializationOrAdRequests=true,apkLaunched=false,jdkSettingsUnchanged,actualSdkReferenceCompiled,adapterIncluded,actualAdapterSdkBranchCompiled;
        public Binding[] sourceBindings,exportBindings;
        public string scope="Pinned Unity2022.3.62f3 Android ARM64 IL2CPP build-only export with actual official Yandex8.6.0 runtime. No SDK initialization/ad requests, no app launch, no reward/provider/payment or production certification. External modern Gradle assembly is a separately recorded tool profile.";
    }
    static string Hash(string path) { using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant(); }
    static Binding[] Bind(string root,string[] paths) { return paths.OrderBy(p=>p,StringComparer.Ordinal).Select(p=>new Binding{path=p.Substring(root.Length+1).Replace('\\','/'),sha256=Hash(p)}).ToArray(); }
    public static void Run() {
        string root=Path.GetFullPath(Path.GetDirectoryName(Application.dataPath)),jdk=AndroidExternalToolsSettings.jdkRootPath;
        bool embedded=EditorPrefs.GetBool("JdkUseEmbedded",true),previousExport=EditorUserBuildSettings.exportAsGoogleAndroidProject;
        var result=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,package="com.heartoftherain.yandex85sdkfixture"};
        try {
            if(Application.unityVersion!="2022.3.62f3"||EditorUserBuildSettings.activeBuildTarget!=BuildTarget.Android)throw new InvalidOperationException("Pinned Android Editor required");
            string expected=Path.GetFullPath(Path.Combine(Path.GetDirectoryName(EditorApplication.applicationPath),"Data/PlaybackEngines/AndroidPlayer/OpenJDK"));
            if(!embedded||!string.Equals(Path.GetFullPath(jdk).TrimEnd('\\','/'),expected.TrimEnd('\\','/'),StringComparison.OrdinalIgnoreCase)||!File.ReadAllText(Path.Combine(jdk,"release")).Contains("JAVA_VERSION=\"11."))throw new InvalidOperationException("Keep supported embedded Editor Java11; external Java17 assembly is separate");
            result.apiContract=Yandex85ApiReference.VersionContract;result.actualSdkReferenceCompiled=!string.IsNullOrEmpty(result.apiContract);
            result.adapterIncluded=File.Exists(Path.Combine(Application.dataPath,"Integration/YandexRewardedAdsProvider85.cs"));
            var adapter=Type.GetType("HeartOfTheRain.App.Advertising.YandexRewardedAdsProvider85, Assembly-CSharp");
            result.actualAdapterSdkBranchCompiled=adapter!=null&&adapter.GetMethod("FinishLoad",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic)!=null;
            if(result.adapterIncluded&&!result.actualAdapterSdkBranchCompiled)throw new InvalidOperationException("Actual adapter SDK branch not compiled");
            PlayerSettings.companyName="HeartOfTheRainVerification";PlayerSettings.productName="Yandex85 build-only SDK fixture";
            PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android,result.package);
            PlayerSettings.bundleVersion="85.0";PlayerSettings.Android.bundleVersionCode=85;
            PlayerSettings.Android.minSdkVersion=(AndroidSdkVersions)26;PlayerSettings.Android.targetSdkVersion=(AndroidSdkVersions)35;
            PlayerSettings.Android.targetArchitectures=AndroidArchitecture.ARM64;PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android,ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.useCustomKeystore=false;PlayerSettings.defaultInterfaceOrientation=UIOrientation.Portrait;
            PlayerSettings.SetManagedStrippingLevel(BuildTargetGroup.Android,ManagedStrippingLevel.Low);
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);new GameObject("BuildOnlyCamera",typeof(Camera));
            string scenePath="Assets/BuildOnly.unity";EditorSceneManager.SaveScene(scene,scenePath);
            result.sourceBindings=Bind(root,Directory.GetFiles(Application.dataPath,"*",SearchOption.AllDirectories).Where(p=>!p.EndsWith(".meta",StringComparison.OrdinalIgnoreCase)).Concat(new[]{Path.Combine(root,"Packages/manifest.json"),Path.Combine(root,"ProjectSettings/ProjectVersion.txt")}).ToArray());
            result.output=Path.Combine(root,"Build/GradleExport");if(Directory.Exists(result.output))throw new InvalidOperationException("Preserve prior export before retry");
            EditorUserBuildSettings.exportAsGoogleAndroidProject=true;
            var build=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{scenePath},target=BuildTarget.Android,locationPathName=result.output,options=BuildOptions.AcceptExternalModificationsToPlayer|BuildOptions.Development});
            result.errors=(int)build.summary.totalErrors;result.warnings=(int)build.summary.totalWarnings;
            if(build.summary.result!=BuildResult.Succeeded)throw new InvalidOperationException("Export failed: "+build.summary.result);
            result.exportBindings=Bind(result.output,Directory.GetFiles(result.output,"*",SearchOption.AllDirectories));
            result.status="PASS_ISOLATED_YANDEX85_GRADLE_EXPORT";
        } catch(Exception error) { result.error=error.GetType().Name+": "+error.Message; }
        finally {
            EditorUserBuildSettings.exportAsGoogleAndroidProject=previousExport;
            result.jdkSettingsUnchanged=jdk==AndroidExternalToolsSettings.jdkRootPath&&embedded==EditorPrefs.GetBool("JdkUseEmbedded",true);
            if(!result.jdkSettingsUnchanged)result.status="FAIL_ISOLATED_YANDEX85_GRADLE_EXPORT";
            File.WriteAllText(Path.Combine(root,"AndroidExport.json"),JsonUtility.ToJson(result,true));
        }
        if(Application.isBatchMode)EditorApplication.Exit(result.status.StartsWith("PASS_",StringComparison.Ordinal)?0:1);
    }
}
#endif

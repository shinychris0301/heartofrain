#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.Android;
using UnityEditor.Build.Reporting;
using UnityEngine;

// Copied only into an explicitly prepared cache clone. Never imported into the
// ordinary project's Assets, and never runs automatically at Editor startup.
public static class Yandex85GameExport {
    const string Package="com.heartoftherain.ads85review";
    [Serializable] sealed class Profile {public int version;public string package;public bool configurationProvisioned;public string[] enabledScenes;}
    [Serializable] public sealed class Binding {public string path,sha256;}
    [Serializable] public sealed class Report {
        public string status="FAIL_ISOLATED_YANDEX85_GAME_GRADLE_EXPORT",utc,unity,package=Package,output,error,productNameBefore,productNameAfter,preparationSHA256;
        public int errors,warnings,minApi=26,targetApi=35;
        public bool fullGame=true,development=true,configurationProvisioned=false,noSdkInitializationOrAdRequests=true,apkLaunched=false,jdkSettingsUnchanged,actualAdapterSdkBranchCompiled,portraitOnly,enabledScenesUnchanged;
        public string[] enabledScenes;public Binding[] sourceBindings,exportBindings;
        public string scope="Full current game scenes/art/model with unmodified official Yandex8.6.0 Android runtime in a cache-only clone, internal debug application identity and actual adapter SDK compile branch. Build-only Unity2022.3.62f3 ARM64 IL2CPP Gradle export with embedded Java11; external AGP8.7/Gradle8.9/Java17 assembly is separate. No publisher/config provisioning, SDK initialization/load/show, APK launch/install, impression/revenue/grant, main project modification or production certification.";
    }
    static string Io(string path){string prefix=new string('\\',2)+"?"+'\\';return Application.platform==RuntimePlatform.WindowsEditor&&!path.StartsWith(prefix,StringComparison.Ordinal)?prefix+Path.GetFullPath(path):path;}
    static string Logical(string path){string prefix=new string('\\',2)+"?"+'\\';return path.StartsWith(prefix,StringComparison.Ordinal)?path.Substring(prefix.Length):path;}
    static string Hash(string path){using(var hash=SHA256.Create())using(var stream=File.OpenRead(Io(path)))return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-","").ToLowerInvariant();}
    static Binding[] Bind(string root,string[] paths)=>paths.Select(Logical).OrderBy(p=>p,StringComparer.Ordinal).Select(p=>new Binding{path=p.Substring(root.Length+1).Replace('\\','/'),sha256=Hash(p)}).ToArray();
    public static void Run(){
        string root=Path.GetFullPath(Path.GetDirectoryName(Application.dataPath)),jdk=AndroidExternalToolsSettings.jdkRootPath;
        bool embedded=EditorPrefs.GetBool("JdkUseEmbedded",true),previousExport=EditorUserBuildSettings.exportAsGoogleAndroidProject;
        var result=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,productNameBefore=PlayerSettings.productName};
        string[] enabled=EditorBuildSettings.scenes.Where(s=>s.enabled).Select(s=>s.path).ToArray();
        try{
            if(Application.unityVersion!="2022.3.62f3"||EditorUserBuildSettings.activeBuildTarget!=BuildTarget.Android)throw new InvalidOperationException("Pinned Android Editor required");
            if(!Regex.IsMatch(Path.GetFileName(root),@"\A(?:GameProject_[0-9a-f]{32}|G85_[0-9a-f]{8})\z")||!Path.GetDirectoryName(root).Replace('\\','/').EndsWith("/.verification-cache/Ads85",StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("Prepared isolated game clone required");
            if(Environment.GetEnvironmentVariable("HOTR_BUILD_CHANNEL")=="rustore")throw new InvalidOperationException("Production channel forbidden for SDK compile review");
            string profilePath=Path.Combine(root,"GameAds85Profile.json");var profile=JsonUtility.FromJson<Profile>(File.ReadAllText(profilePath));
            if(profile==null||profile.version!=1||profile.package!=Package||profile.configurationProvisioned||profile.enabledScenes==null||!enabled.SequenceEqual(profile.enabledScenes)||enabled.Length==0||enabled.Any(p=>!File.Exists(Path.Combine(root,p))))throw new InvalidOperationException("Game profile/actual enabled scenes mismatch");
            result.preparationSHA256=Hash(Path.Combine(Path.GetDirectoryName(root),Path.GetFileName(root)+"_Preparation.json"));
            string expected=Path.GetFullPath(Path.Combine(Path.GetDirectoryName(EditorApplication.applicationPath),"Data/PlaybackEngines/AndroidPlayer/OpenJDK"));
            if(!embedded||!string.Equals(Path.GetFullPath(jdk).TrimEnd('\\','/'),expected.TrimEnd('\\','/'),StringComparison.OrdinalIgnoreCase)||!File.ReadAllText(Path.Combine(jdk,"release")).Contains("JAVA_VERSION=\"11."))throw new InvalidOperationException("Keep supported embedded Editor Java11; external Java17 assembly is separate");
            string response=File.ReadAllText(Path.Combine(Application.dataPath,"csc.rsp"));
            if(!response.Contains("HOTR_YANDEX_ADS")||response.Contains("HOTR_YANDEX_ADS_ISOLATED_FIXTURE"))throw new InvalidOperationException("Real adapter define required without demo fixture define");
            var adapter=Type.GetType("HeartOfTheRain.App.Advertising.YandexRewardedAdsProvider85, Assembly-CSharp");
            result.actualAdapterSdkBranchCompiled=adapter!=null&&adapter.GetMethod("FinishLoad",BindingFlags.Instance|BindingFlags.NonPublic)!=null;
            if(!result.actualAdapterSdkBranchCompiled)throw new InvalidOperationException("Actual game adapter SDK branch not compiled");
            if(PlayerSettings.productName!="Сердце дождя")throw new InvalidOperationException("Preserve the approved Russian application name");
            PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android,Package);PlayerSettings.bundleVersion="85.0";PlayerSettings.Android.bundleVersionCode=85;
            PlayerSettings.Android.minSdkVersion=(AndroidSdkVersions)26;PlayerSettings.Android.targetSdkVersion=(AndroidSdkVersions)35;
            PlayerSettings.Android.targetArchitectures=AndroidArchitecture.ARM64;PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android,ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.useCustomKeystore=false;PlayerSettings.defaultInterfaceOrientation=UIOrientation.Portrait;
            PlayerSettings.allowedAutorotateToPortrait=true;PlayerSettings.allowedAutorotateToPortraitUpsideDown=false;PlayerSettings.allowedAutorotateToLandscapeLeft=false;PlayerSettings.allowedAutorotateToLandscapeRight=false;
            PlayerSettings.SetManagedStrippingLevel(BuildTargetGroup.Android,ManagedStrippingLevel.Low);
            result.portraitOnly=PlayerSettings.defaultInterfaceOrientation==UIOrientation.Portrait&&!PlayerSettings.allowedAutorotateToLandscapeLeft&&!PlayerSettings.allowedAutorotateToLandscapeRight;
            result.enabledScenes=enabled;
            result.sourceBindings=Bind(root,Directory.GetFiles(Io(Application.dataPath),"*",SearchOption.AllDirectories).Concat(Directory.GetFiles(Io(Path.Combine(root,"Packages")),"*",SearchOption.AllDirectories)).Concat(Directory.GetFiles(Io(Path.Combine(root,"ProjectSettings")),"*",SearchOption.AllDirectories)).ToArray());
            result.output=Path.Combine(root,"Build/GameGradleExport");if(Directory.Exists(result.output))throw new InvalidOperationException("Preserve prior full-game export before retry");
            EditorUserBuildSettings.exportAsGoogleAndroidProject=true;
            var build=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=enabled,target=BuildTarget.Android,locationPathName=result.output,options=BuildOptions.AcceptExternalModificationsToPlayer|BuildOptions.Development});
            result.errors=(int)build.summary.totalErrors;result.warnings=(int)build.summary.totalWarnings;
            if(build.summary.result!=BuildResult.Succeeded)throw new InvalidOperationException("Full-game export failed: "+build.summary.result);
            result.exportBindings=Bind(result.output,Directory.GetFiles(Io(result.output),"*",SearchOption.AllDirectories));result.status="PASS_ISOLATED_YANDEX85_GAME_GRADLE_EXPORT";
        }catch(Exception error){result.error=error.GetType().Name+": "+error.Message;}
        finally{
            EditorUserBuildSettings.exportAsGoogleAndroidProject=previousExport;result.productNameAfter=PlayerSettings.productName;
            result.jdkSettingsUnchanged=jdk==AndroidExternalToolsSettings.jdkRootPath&&embedded==EditorPrefs.GetBool("JdkUseEmbedded",true);
            result.enabledScenesUnchanged=enabled.SequenceEqual(EditorBuildSettings.scenes.Where(s=>s.enabled).Select(s=>s.path));
            if(!result.jdkSettingsUnchanged||!result.enabledScenesUnchanged||result.productNameBefore!=result.productNameAfter)result.status="FAIL_ISOLATED_YANDEX85_GAME_GRADLE_EXPORT";
            File.WriteAllText(Path.Combine(root,"GameAndroidExport.json"),JsonUtility.ToJson(result,true));
        }
        if(Application.isBatchMode)EditorApplication.Exit(result.status.StartsWith("PASS_",StringComparison.Ordinal)?0:1);
    }
}
#endif

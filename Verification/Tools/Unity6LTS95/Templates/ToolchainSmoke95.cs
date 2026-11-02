#if UNITY_EDITOR
using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEditor.Android;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace HeartOfTheRain.Verification {
    // Fresh minimal toolchain project only. No game assets or runtime verification code.
    public static class ToolchainSmoke95 {
        [Serializable] sealed class Report {
            public string status="FAIL_ACTUAL_LTS95_EMPTY_ANDROID_BUILD",utc,unity,project,error,package,apk,apkSHA256,buildResult;
            public string sdk,jdk,ndk,gradle,jdkRelease,ndkProperties,architecture="ARM64",backend="IL2CPP";
            public string scope="Actual empty-scene Development ARM64 IL2CPP toolchain smoke only. No game imported, APK installation, device/backend/provider or production/game acceptance. External-tool preferences are read only; no API preference setters used.";
            public int checks,minSdk,targetSdk,buildErrors,buildWarnings;public long apkBytes;public bool splash,unityLogo,preferencesReadOnly,development;
        }
        static void Check(Report r,bool condition,string reason){r.checks++;if(!condition)throw new InvalidOperationException(reason);}
        static string Full(string path)=>Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar,Path.AltDirectorySeparatorChar);
        static bool Under(string path,string parent)=>Full(path).StartsWith(Full(parent)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase);
        static string Hash(string path){using(var stream=File.OpenRead(path))using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-","").ToLowerInvariant();}
        static void Write(string path,string text){using(var file=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.Read))using(var writer=new StreamWriter(file,new UTF8Encoding(false)))writer.Write(text);}
        public static void Run(){
            var report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,preferencesReadOnly=true};string output=null;
            try{
                report.project=Full(Path.Combine(Application.dataPath,".."));var folder=new DirectoryInfo(report.project);var migration=folder.Parent;var cache=migration==null?null:migration.Parent;var workspace=cache==null?null:cache.Parent;
                Check(report,folder.Name=="Smoke"&&migration!=null&&migration.Name=="Unity6LTS95"&&cache!=null&&cache.Name==".verification-cache"&&workspace!=null&&File.Exists(Path.Combine(workspace.FullName,"AGENTS.md")),"Exact private smoke project required");
                Check(report,report.unity=="6000.3.27f1","Exact approved LTS engine required");
                string expectedEditor=Environment.GetEnvironmentVariable("HOTR_SMOKE95_EDITOR");Check(report,!string.IsNullOrEmpty(expectedEditor)&&Full(EditorApplication.applicationPath)==Full(expectedEditor),"Exact LTS executable required");
                string requested=Environment.GetEnvironmentVariable("HOTR_SMOKE95_OUT");Check(report,!string.IsNullOrEmpty(requested)&&Path.IsPathRooted(requested),"Explicit output required");output=Full(requested);
                Check(report,Under(output,Path.Combine(workspace.FullName,"Verification","Evidence","Unity6LTS95","SmokeRuns")),"Fresh contained95 evidence required");Directory.CreateDirectory(output);
                string android=Path.Combine(EditorApplication.applicationContentsPath,"PlaybackEngines","AndroidPlayer");
                report.sdk=Full(AndroidExternalToolsSettings.sdkRootPath);report.ndk=Full(AndroidExternalToolsSettings.ndkRootPath);report.jdk=Full(AndroidExternalToolsSettings.jdkRootPath);report.gradle=Full(AndroidExternalToolsSettings.gradlePath);
                Check(report,Under(report.sdk,android)&&Under(report.ndk,android)&&Under(report.jdk,android)&&Under(report.gradle,android),"All resolved tools must be embedded in this LTS Editor; custom/global preferences are never altered");
                Check(report,Directory.Exists(report.sdk)&&Directory.Exists(report.ndk)&&Directory.Exists(report.jdk)&&Directory.Exists(report.gradle),"Embedded official tool directories required");
                report.jdkRelease=File.ReadAllText(Path.Combine(report.jdk,"release"));report.ndkProperties=File.ReadAllText(Path.Combine(report.ndk,"source.properties"));
                Check(report,report.jdkRelease.Contains("JAVA_VERSION=\"17."),"Embedded JDK17 required");Check(report,report.ndkProperties.Contains("27.2.12479018"),"Embedded NDKr27c required");
                Check(report,File.Exists(Path.Combine(report.sdk,"platforms","android-36","android.jar"))&&File.Exists(Path.Combine(report.sdk,"build-tools","36.0.0","aapt2.exe")),"Embedded SDK36/build-tools36 required");
                string requestedApk=Environment.GetEnvironmentVariable("HOTR_SMOKE95_APK");Check(report,!string.IsNullOrEmpty(requestedApk)&&Path.IsPathRooted(requestedApk),"Explicit private APK required");report.apk=Full(requestedApk);
                Check(report,Under(report.apk,Path.Combine(workspace.FullName,".verification-cache","Unity6LTS95","SmokeOutputs"))&&Path.GetFileName(report.apk)=="ToolchainSmoke95.apk"&&!File.Exists(report.apk),"Fresh private smoke APK only; never install");Directory.CreateDirectory(Path.GetDirectoryName(report.apk));
                PlayerSettings.companyName="HeartOfTheRainVerification";PlayerSettings.productName="Toolchain Smoke95";PlayerSettings.bundleVersion="0.0.95";
                report.package="com.heartoftherain.toolchain95";PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android,report.package);
                PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android,ScriptingImplementation.IL2CPP);PlayerSettings.Android.targetArchitectures=AndroidArchitecture.ARM64;
                PlayerSettings.Android.minSdkVersion=(AndroidSdkVersions)26;PlayerSettings.Android.targetSdkVersion=(AndroidSdkVersions)36;PlayerSettings.Android.bundleVersionCode=95;PlayerSettings.Android.useCustomKeystore=false;
                PlayerSettings.defaultInterfaceOrientation=UIOrientation.Portrait;PlayerSettings.SplashScreen.show=false;PlayerSettings.SplashScreen.showUnityLogo=false;
                EditorUserBuildSettings.buildAppBundle=false;EditorUserBuildSettings.exportAsGoogleAndroidProject=false;EditorUserBuildSettings.androidBuildType=AndroidBuildType.Debug;
                report.minSdk=(int)PlayerSettings.Android.minSdkVersion;report.targetSdk=(int)PlayerSettings.Android.targetSdkVersion;report.splash=PlayerSettings.SplashScreen.show;report.unityLogo=PlayerSettings.SplashScreen.showUnityLogo;
                Check(report,report.minSdk==26&&report.targetSdk==36&&!report.splash&&!report.unityLogo&&PlayerSettings.Android.targetArchitectures==AndroidArchitecture.ARM64&&PlayerSettings.GetScriptingBackend(NamedBuildTarget.Android)==ScriptingImplementation.IL2CPP,"Exact smoke build settings required");
                var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);Check(report,scene.rootCount==0,"Actual empty scene required");
                string scenePath="Assets/ToolchainSmoke95.unity";Check(report,EditorSceneManager.SaveScene(scene,scenePath),"Save empty smoke scene");AssetDatabase.SaveAssets();
                var build=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{scenePath},locationPathName=report.apk,target=BuildTarget.Android,options=BuildOptions.Development|BuildOptions.CompressWithLz4});
                report.buildResult=build.summary.result.ToString();report.buildErrors=(int)build.summary.totalErrors;report.buildWarnings=(int)build.summary.totalWarnings;report.development=(build.summary.options&BuildOptions.Development)!=0;
                Check(report,build.summary.result==BuildResult.Succeeded&&build.summary.totalErrors==0&&report.development&&File.Exists(report.apk),"Actual stock LTS Android build must succeed");
                report.apkBytes=new FileInfo(report.apk).Length;report.apkSHA256=Hash(report.apk);Check(report,report.apkBytes>0,"Nonempty actual APK required");
                Check(report,Full(AndroidExternalToolsSettings.sdkRootPath)==report.sdk&&Full(AndroidExternalToolsSettings.ndkRootPath)==report.ndk&&Full(AndroidExternalToolsSettings.jdkRootPath)==report.jdk&&Full(AndroidExternalToolsSettings.gradlePath)==report.gradle,"External tool resolved paths unchanged");
                report.status="PASS_ACTUAL_LTS95_EMPTY_ANDROID_BUILD";
            }catch(Exception error){report.error=error.ToString();}
            if(output!=null)Write(Path.Combine(output,"Native.json"),JsonUtility.ToJson(report,true));else Debug.LogError("Smoke95 refused before safe evidence output available");
            EditorApplication.Exit(report.status=="PASS_ACTUAL_LTS95_EMPTY_ANDROID_BUILD"?0:1);
        }
    }
}
#endif

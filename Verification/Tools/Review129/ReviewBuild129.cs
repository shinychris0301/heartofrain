#if UNITY_EDITOR && HOTR_RUSTORE_REVIEW129
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using HeartOfTheRain.App.RuStore.Editor;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace HeartOfTheRain.Verification129 {
    // Non-Development build for the RuStore review, in an isolated project only. It talks to the
    // staging server with production off. The release gates stay unmet and are listed in the report:
    // this profile does not pass them, it is a labelled exception that the main project does not have.
    public static class ReviewBuild129 {
        [Serializable] sealed class Report {
            public string status="FAIL_REVIEW129_BUILD",unity,package,version,apk,apkSHA256,errorType,error;
            public int versionCode,errors=-1,warnings=-1;public long bytes;public bool development,customSigning,productionEnabled=false;
            public string scope="RuStore review test version on the staging server. Not a production release: purchases and the release gates below are not accepted.";
            public List<string> configurationErrors=new List<string>(),unmetReleaseGates=new List<string>();
        }
        static string Hash(string path){using(var sha=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
        public static void Run(){
            var r=new Report{unity=Application.unityVersion};
            string output=Environment.GetEnvironmentVariable("HOTR_REVIEW129_OUT");int code=1;
            string originalStore=PlayerSettings.Android.keystoreName,originalAlias=PlayerSettings.Android.keyaliasName;bool originalCustom=PlayerSettings.Android.useCustomKeystore;
            try{
                var release=JsonUtility.FromJson<RuStoreReleaseConfiguration>(File.ReadAllText(Environment.GetEnvironmentVariable(RuStoreReleasePreflight.ConfigVariable)));
                r.configurationErrors=RuStoreReleasePreflight.Validate(release);
                if(r.configurationErrors.Count>0)throw new BuildFailedException("Release configuration invalid");
                r.package=release.packageName;r.versionCode=release.versionCode;r.version=Environment.GetEnvironmentVariable("HOTR_REVIEW129_VERSION");
                PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android,release.packageName);
                PlayerSettings.Android.bundleVersionCode=release.versionCode;PlayerSettings.bundleVersion=r.version;
                PlayerSettings.Android.minSdkVersion=(AndroidSdkVersions)release.minimumApiLevel;PlayerSettings.Android.targetSdkVersion=(AndroidSdkVersions)release.targetApiLevel;
                string password=Environment.GetEnvironmentVariable("HOTR_RELEASE_SIGNING_PASSWORD"),store=Environment.GetEnvironmentVariable("HOTR_RELEASE_KEYSTORE");
                PlayerSettings.Android.keystoreName=store;PlayerSettings.Android.keyaliasName="heartoftherain-release";PlayerSettings.Android.useCustomKeystore=true;
                PlayerSettings.Android.keystorePass=password;PlayerSettings.Android.keyaliasPass=password;r.customSigning=true;
                EditorUserBuildSettings.buildAppBundle=false;
                bool hasConfig;r.unmetReleaseGates=RuStoreReleasePreflight.Evaluate(out hasConfig);
                string apk=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW129_APK"));r.apk=apk;Directory.CreateDirectory(Path.GetDirectoryName(apk));
                var scenes=EditorBuildSettings.scenes.Where(s=>s.enabled).Select(s=>s.path).ToArray();
                var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=scenes,locationPathName=apk,target=BuildTarget.Android,options=BuildOptions.None});
                r.errors=(int)result.summary.totalErrors;r.warnings=(int)result.summary.totalWarnings;r.development=(result.summary.options&BuildOptions.Development)!=0;
                if(result.summary.result==BuildResult.Succeeded&&r.errors==0&&!r.development&&File.Exists(apk)){r.bytes=new FileInfo(apk).Length;r.apkSHA256=Hash(apk);r.status="PASS_REVIEW129_BUILD";code=0;}
            }catch(Exception failure){r.errorType=failure.GetType().Name;if(failure is BuildFailedException)r.error=failure.Message;}
            finally{
                PlayerSettings.Android.keystorePass=PlayerSettings.Android.keyaliasPass="";PlayerSettings.Android.keystoreName=originalStore;PlayerSettings.Android.keyaliasName=originalAlias;PlayerSettings.Android.useCustomKeystore=originalCustom;
                Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"Native.json"),JsonUtility.ToJson(r,true)+"\n");
            }
            if(Application.isBatchMode)EditorApplication.Exit(code);
        }
    }
}
#endif

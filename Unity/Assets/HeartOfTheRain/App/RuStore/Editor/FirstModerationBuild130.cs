#if UNITY_EDITOR && HOTR_FIRST_MODERATION130
using System;
using System.IO;
using System.Linq;
using HeartOfTheRain.App.ShopCheckout86;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace HeartOfTheRain.App.RuStore.Editor {
    // Explicit first-version review artifact. The normal production build channel is unchanged.
    public static class FirstModerationBuild130 {
        [Serializable] sealed class Receipt {
            public string status="FAIL_FIRST_MODERATION130",unity,package,version,apkSha256,error;
            public int versionCode,errors=-1,warnings=-1;
            public long bytes;
            public bool development,purchasesDisabled,customSigning,productionEnabled=false;
            public string scope="Signed non-debug first-version RuStore moderation candidate, held unpublished. Sandbox staging; real-money checkout is compiled out.";
        }
        static string Hash(string path){using(var sha=System.Security.Cryptography.SHA256.Create())return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
        public static void Run(){
            var receipt=new Receipt{unity=Application.unityVersion,purchasesDisabled=ShopCheckoutHost86.FirstModerationPurchasesDisabled};int code=1;
            string output=Environment.GetEnvironmentVariable("HOTR_REVIEW130_OUT");
            string originalStore=PlayerSettings.Android.keystoreName,originalAlias=PlayerSettings.Android.keyaliasName;
            bool originalCustom=PlayerSettings.Android.useCustomKeystore;
            try{
                if(Environment.GetEnvironmentVariable("HOTR_BUILD_CHANNEL")!=FirstModeration130.Channel||!receipt.purchasesDisabled)
                    throw new BuildFailedException("FirstModerationExplicitProfileRequired");
                string configPath=Environment.GetEnvironmentVariable(RuStoreReleasePreflight.ConfigVariable);
                if(string.IsNullOrEmpty(configPath)||!File.Exists(configPath))throw new BuildFailedException("FirstModerationReleaseConfigMissing");
                var release=JsonUtility.FromJson<RuStoreReleaseConfiguration>(File.ReadAllText(configPath));
                if(RuStoreReleasePreflight.Validate(release).Count!=0)throw new BuildFailedException("FirstModerationReleaseConfigInvalid");
                receipt.package=release.packageName;receipt.versionCode=release.versionCode;
                receipt.version=Environment.GetEnvironmentVariable("HOTR_REVIEW130_VERSION");
                if(string.IsNullOrEmpty(receipt.version))throw new BuildFailedException("FirstModerationVersionMissing");
                string password=Environment.GetEnvironmentVariable("HOTR_RELEASE_SIGNING_PASSWORD");
                string store=Environment.GetEnvironmentVariable("HOTR_RELEASE_KEYSTORE");
                if(string.IsNullOrEmpty(password)||string.IsNullOrEmpty(store)||!File.Exists(store))throw new BuildFailedException("FirstModerationSigningCustodyMissing");
                string apk=Environment.GetEnvironmentVariable("HOTR_REVIEW130_APK");
                if(string.IsNullOrEmpty(apk)||File.Exists(apk))throw new BuildFailedException("FirstModerationFreshApkRequired");
                PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android,release.packageName);
                PlayerSettings.Android.bundleVersionCode=release.versionCode;
                PlayerSettings.bundleVersion=receipt.version;
                PlayerSettings.Android.minSdkVersion=(AndroidSdkVersions)release.minimumApiLevel;
                PlayerSettings.Android.targetSdkVersion=(AndroidSdkVersions)release.targetApiLevel;
                PlayerSettings.Android.keystoreName=store;
                PlayerSettings.Android.keyaliasName="heartoftherain-release";
                PlayerSettings.Android.useCustomKeystore=true;
                PlayerSettings.Android.keystorePass=password;
                PlayerSettings.Android.keyaliasPass=password;
                receipt.customSigning=true;
                EditorUserBuildSettings.buildAppBundle=false;
                apk=Path.GetFullPath(apk);Directory.CreateDirectory(Path.GetDirectoryName(apk));
                var scenes=EditorBuildSettings.scenes.Where(s=>s.enabled).Select(s=>s.path).ToArray();
                if(scenes.Length==0)throw new BuildFailedException("FirstModerationScenesMissing");
                var build=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=scenes,locationPathName=apk,target=BuildTarget.Android,options=BuildOptions.None});
                receipt.errors=(int)build.summary.totalErrors;receipt.warnings=(int)build.summary.totalWarnings;
                receipt.development=(build.summary.options&BuildOptions.Development)!=0;
                if(build.summary.result!=BuildResult.Succeeded||receipt.errors!=0||receipt.development||!File.Exists(apk))
                    throw new BuildFailedException("FirstModerationBuildFailed");
                receipt.bytes=new FileInfo(apk).Length;receipt.apkSha256=Hash(apk);
                receipt.status="PASS_FIRST_MODERATION130";code=0;
            }catch(BuildFailedException e){receipt.error=e.Message;}
            catch(Exception){receipt.error="FirstModerationUnexpectedBuildFailure";}
            finally{
                PlayerSettings.Android.keystorePass=PlayerSettings.Android.keyaliasPass="";
                PlayerSettings.Android.keystoreName=originalStore;
                PlayerSettings.Android.keyaliasName=originalAlias;
                PlayerSettings.Android.useCustomKeystore=originalCustom;
                if(!string.IsNullOrEmpty(output)){Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"Native.json"),JsonUtility.ToJson(receipt,true)+"\n");}
            }
            if(Application.isBatchMode)EditorApplication.Exit(code);
        }
    }
}
#endif

#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using HeartOfTheRain.App.Advertising;
using HeartOfTheRain.App.ShopCheckout86;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.RuStore.Editor;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.Android;
using UnityEngine;

namespace HeartOfTheRain.App.ServerGameplay.Editor {
    // Separate SDK-only build policy. It does not certify provider/device,
    // signing, legal or bank-return acceptance and never builds an APK itself.
    public static class SdkCheckoutBuild125 {
        public const string Define="HOTR_RUSTORE_SDK_ONLY125";
        public static string[] ToolchainErrors(string unity,string contents,string sdk,string ndk,string jdk,string gradle){
            var errors=new List<string>();
            try{
                string android=Path.GetFullPath(Path.Combine(contents,"PlaybackEngines","AndroidPlayer"));
                Func<string,string,bool> same=(actual,name)=>!string.IsNullOrEmpty(actual)&&string.Equals(Path.GetFullPath(actual).TrimEnd('\\','/'),Path.GetFullPath(Path.Combine(android,name)).TrimEnd('\\','/'),StringComparison.OrdinalIgnoreCase);
                if(unity!="6000.3.27f1")errors.Add("sdk_checkout_supported_isolated_lts_profile_required");
                if(!same(sdk,"SDK")||!same(ndk,"NDK")||!same(jdk,"OpenJDK")||!same(gradle,"Tools/gradle"))errors.Add("sdk_checkout_matching_stock_android_tool_paths_required");
                if(string.IsNullOrEmpty(sdk)||!File.Exists(Path.Combine(sdk,"platforms/android-36/android.jar")))errors.Add("sdk_checkout_stock_android_36_required");
                if(string.IsNullOrEmpty(jdk)||!File.Exists(Path.Combine(jdk,"bin/java.exe"))||!File.ReadAllLines(Path.Combine(jdk,"release")).Contains("JAVA_VERSION=\"17.0.18\""))errors.Add("sdk_checkout_stock_java_17_0_18_required");
                if(string.IsNullOrEmpty(ndk)||!File.ReadAllLines(Path.Combine(ndk,"source.properties")).Contains("Pkg.Revision = 27.2.12479018"))errors.Add("sdk_checkout_stock_ndk_27_2_required");
                // Unity's stock Gradle distribution is JAR-only; no bin launcher is required.
                if(string.IsNullOrEmpty(gradle)||!File.Exists(Path.Combine(gradle,"lib/gradle-core-9.3.1.jar"))||!File.Exists(Path.Combine(gradle,"lib/gradle-launcher-9.3.1.jar")))errors.Add("sdk_checkout_stock_gradle_9_3_1_required");
            }catch(Exception){errors.Add("sdk_checkout_stock_toolchain_metadata_unavailable");}
            return errors.Distinct().ToArray();
        }
        public static string[] ActualToolchainErrors(){
            string gradle=null;
#if UNITY_6000_0_OR_NEWER
            gradle=AndroidExternalToolsSettings.Gradle.path;
#endif
            return ToolchainErrors(Application.unityVersion,EditorApplication.applicationContentsPath,AndroidExternalToolsSettings.sdkRootPath,AndroidExternalToolsSettings.ndkRootPath,AndroidExternalToolsSettings.jdkRootPath,gradle);
        }
        public static string[] Validate(bool android,bool development,bool debugging,bool customSigning,int minimumApi,string package,string[] defines,string unity,
            ServerConfigurationInput104 sdk,ServerConfigurationInput104 production,ServerConfigurationInput104 staging,ServerConfigurationInput104 legacyCheckout){
            var errors=new List<string>();defines=defines??new string[0];
            if(!android)errors.Add("SdkCheckoutAndroidRequired");
            if(debugging)errors.Add("SdkCheckoutScriptDebuggingRejected");
            if(minimumApi<26)errors.Add("SdkCheckoutProtectedIdentityApi26Required");
            if(!defines.Contains(Define))errors.Add("SdkCheckoutExplicitBuildDefineRequired");
            if(!defines.Contains("HOTR_RUSTORE_PAY"))errors.Add("SdkCheckoutRuStoreSdkRequired");
            if(unity!="6000.3.27f1")errors.Add("SdkCheckoutSupportedIsolatedLtsProfileRequired");
            ServerGameplayConfiguration selected;string why;
            CheckoutSdkConfiguration125.Resolve(true,package,sdk,production,staging,legacyCheckout,out selected,out why);
            if(selected==null)errors.Add("SdkCheckoutPackagedManagedBindingInvalid");
            else if(selected.productionEnabled){
                if(development)errors.Add("SdkCheckoutProductionDevelopmentRejected");
                if(!customSigning)errors.Add("SdkCheckoutDeveloperReleaseSignerRequired");
                if(!defines.Contains("HOTR_PRODUCTION122"))errors.Add("SdkCheckoutExplicitProductionDefineRequired");
            }else{
                if(!development)errors.Add("SdkCheckoutSandboxDevelopmentRequired");
                if(defines.Contains("HOTR_PRODUCTION122"))errors.Add("SdkCheckoutMixedEnvironmentDefinesRejected");
            }
            return errors.ToArray();
        }
        static bool Reserved(string path,string key){
            if(path==null||path.EndsWith(".meta",StringComparison.OrdinalIgnoreCase))return false;
            string normalized=path.Replace('\\','/');int at=normalized.LastIndexOf("/Resources/",StringComparison.OrdinalIgnoreCase);
            if(at<0)return false;string relative=normalized.Substring(at+11);
            return relative.StartsWith(key+"/",StringComparison.OrdinalIgnoreCase)||string.Equals(Path.ChangeExtension(relative,null),key,StringComparison.OrdinalIgnoreCase);
        }
        static ServerConfigurationInput104 Imported(string key,string exact){
            var paths=AssetDatabase.GetAllAssetPaths().Where(path=>Reserved(path,key)).ToArray();
            if(paths.Length==0)return ServerConfigurationInput104.Absent;
            if(paths.Length!=1||paths[0]!=exact)return ServerConfigurationInput104.Invalid;
            var asset=AssetDatabase.LoadMainAssetAtPath(exact) as TextAsset;
            if(!asset||!File.Exists(exact)||asset.text!=File.ReadAllText(exact,new System.Text.UTF8Encoding(false,true)))return ServerConfigurationInput104.Invalid;
            return new ServerConfigurationInput104(true,asset.text);
        }
        public static bool GuardIfSelected(BuildReport report){
            if(FirstModeration130.GuardIfSelected(report))return true;
            var sdk=Imported(CheckoutSdkConfiguration125.ResourceKey,CheckoutSdkConfiguration125.ResourceAssetPath);
            var defines=PlayerSettings.GetScriptingDefineSymbolsForGroup(BuildTargetGroup.Android).Split(';');
            if(!sdk.present&&!defines.Contains(Define))return false;
            if(report==null)throw new BuildFailedException("SdkCheckoutBuildReportRequired");
            var options=report.summary.options;
            var errors=Validate(report.summary.platform==BuildTarget.Android,(options&BuildOptions.Development)!=0,
                (options&(BuildOptions.AllowDebugging|BuildOptions.ConnectWithProfiler|BuildOptions.EnableDeepProfilingSupport))!=0,
                PlayerSettings.Android.useCustomKeystore,(int)PlayerSettings.Android.minSdkVersion,PlayerSettings.GetApplicationIdentifier(BuildTargetGroup.Android),defines,Application.unityVersion,sdk,
                Imported(ServerProductionConfiguration122.ResourceKey,ServerProductionConfiguration122.ResourceAssetPath),
                Imported(ServerStagingConfiguration104.ResourceKey,ServerStagingConfiguration104.ResourceAssetPath),
                Imported(ServerProductionConfiguration122.CheckoutResourceKey,ServerProductionConfiguration122.CheckoutResourceAssetPath)).ToList();
            var advertising=Imported(AdvertisingConfiguration107.ResourceKey,AdvertisingConfiguration107.ResourceAssetPath);RewardedAdsConfiguration85 ads;string why;
            errors.AddRange(ActualToolchainErrors());
            errors.AddRange(SdkVendorBindings125.ActualPackageErrors());
            try{
                CheckoutConfiguration86 selected;string releasePath=Environment.GetEnvironmentVariable(RuStoreReleasePreflight.ConfigVariable);
                var release=JsonUtility.FromJson<RuStoreReleaseConfiguration>(File.ReadAllText(releasePath));
                if(!CheckoutConfiguration86.TryRead(out selected)||selected==null||selected.Verification!=CommerceVerificationMode125.SdkClientReported||release.verificationMode!=CommerceVerification125.SdkClientReported
                    ||release.consoleApplicationId!=selected.consoleAppId||release.packageName!=selected.packageName||release.backendOrigin!=selected.backendOrigin||release.environment!=(selected.productionEnabled?"production":"sandbox"))throw new FormatException();
                errors.AddRange(SdkVendorBindings125.ActualBindingErrors(selected.consoleAppId,release.paymentReturnScheme));
            }catch(Exception){errors.Add("sdk_checkout_matching_public_release_and_vendor_bindings_required");}
            if(!advertising.present||advertising.failed||!RewardedAdsConfiguration85.TryParsePackaged(advertising.json,out ads,out why))errors.Add("SdkCheckoutAdvertisingPayloadInvalid");
            else if(ads.enabled&&!defines.Contains("HOTR_YANDEX_ADS"))errors.Add("SdkCheckoutEnabledAdvertisingSdkRequired");
            if(errors.Count>0)throw new BuildFailedException(string.Join(",",errors));
            return true;
        }
        // Run only inside the explicitly selected private approved LTS Android
        // project after installing the pinned SDK and packaging public profiles.
        // This updates vendor settings/resources/manifest, never builds an APK.
        public static void PrepareVendorBindings(){
            if(EditorUserBuildSettings.activeBuildTarget!=BuildTarget.Android||ActualToolchainErrors().Length!=0||SdkVendorBindings125.ActualPackageErrors().Length!=0)throw new InvalidOperationException("Sdk125QualifiedIsolatedAndroidProfileRequired");
            CheckoutConfiguration86 selected;string path=Environment.GetEnvironmentVariable(RuStoreReleasePreflight.ConfigVariable);
            if(string.IsNullOrEmpty(path)||!CheckoutConfiguration86.TryRead(out selected)||selected==null||selected.Verification!=CommerceVerificationMode125.SdkClientReported)throw new InvalidOperationException("Sdk125CompletePackagedManagedProfileRequired");
            var release=JsonUtility.FromJson<RuStoreReleaseConfiguration>(File.ReadAllText(path));
            if(release==null||release.schemaVersion!=1||release.verificationMode!=CommerceVerification125.SdkClientReported||release.consoleApplicationId!=selected.consoleAppId||release.packageName!=selected.packageName||release.backendOrigin!=selected.backendOrigin||release.environment!=(selected.productionEnabled?"production":"sandbox"))throw new InvalidOperationException("Sdk125MatchingPublicReleaseMetadataRequired");
            SdkVendorBindings125.ConfigureIsolated(selected.consoleAppId,release.paymentReturnScheme);
            Debug.Log("SDK125 vendor settings and generated Android ID/scheme bindings prepared. APK/signing/provider/device acceptance remains required.");
            if(Application.isBatchMode)EditorApplication.Exit(0);
        }
    }
}
#endif

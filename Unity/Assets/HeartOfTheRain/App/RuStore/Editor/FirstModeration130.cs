#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using HeartOfTheRain.App.Advertising;
using HeartOfTheRain.App.Advertising.Editor;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.ServerGameplay.Editor;
using HeartOfTheRain.App.ShopCheckout86;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.Android;
using UnityEngine;

namespace HeartOfTheRain.App.RuStore.Editor {
    // First-version moderation is held unpublished while RuStore unlocks sandbox payments.
    // It is a separate, signed, non-debug build with checkout disabled in compiled runtime.
    public static class FirstModeration130 {
        public const string Define="HOTR_FIRST_MODERATION130",Channel="first_moderation";
        public const string Package="com.heartoftherain.game",Origin="https://api.novamind-it.ru";
        public const string PrivacyVersion="2026-11-01";
        const string SigningAlias="heartoftherain-release";

        public static string[] Validate(bool android,BuildOptions options,bool signed,string alias,string unity,
            string package,int minimumApi,int targetApi,int versionCode,bool il2cpp,bool arm64,
            string[] defines,string channel,CheckoutConfiguration86 checkout,ServerGameplayConfiguration server,
            RewardedAdsConfiguration85 ads,RuStoreReleaseConfiguration release,string[] vendorErrors,
            string[] adErrors,string[] toolchainErrors){
            var errors=new List<string>();defines=defines??Array.Empty<string>();
            if(!defines.Contains(Define)||channel!=Channel)errors.Add("FirstModerationExplicitProfileRequired");
            if(!android||options!=BuildOptions.None||!signed||alias!=SigningAlias)errors.Add("FirstModerationSignedNonDebugAndroidRequired");
            if(unity!="6000.3.27f1"||package!=Package||minimumApi!=26||targetApi!=36||versionCode<130||!il2cpp||!arm64)
                errors.Add("FirstModerationPinnedAndroidIdentityRequired");
            if(!defines.Contains("HOTR_RUSTORE_PAY")||!defines.Contains("HOTR_RUSTORE_SDK_ONLY125")||!defines.Contains("HOTR_YANDEX_ADS")
                ||defines.Contains("HOTR_PRODUCTION122")||defines.Contains("HOTR_DIAGNOSTICS127")||defines.Contains("HOTR_INTERSTITIAL_DEMO129"))
                errors.Add("FirstModerationCompiledFeatureSetInvalid");
            if(!ShopCheckoutHost86.FirstModerationPurchasesDisabled)errors.Add("FirstModerationCheckoutMustBeCompiledOut");
            if(checkout==null||!checkout.enabled||!checkout.sandbox||checkout.productionEnabled||checkout.packageName!=Package
                ||checkout.backendOrigin!=Origin||checkout.Verification!=CommerceVerificationMode125.SdkClientReported)
                errors.Add("FirstModerationStagingCheckoutBindingInvalid");
            if(server==null||server.mode!="ManagedGuestServer"||server.productionEnabled||server.origin!=Origin)
                errors.Add("FirstModerationStagingServerBindingInvalid");
            if(ads==null||!ads.enabled||ads.rewardedUnitId!="R-M-20291714-1"||ads.interstitialUnitId!="R-M-20291714-2"
                ||ads.privacyUrl!=Origin+"/privacy"||ads.privacyVersion!=PrivacyVersion)
                errors.Add("FirstModerationApprovedAdvertisingRequired");
            if(release==null||release.environment!="sandbox"||release.packageName!=Package||release.backendOrigin!=Origin
                ||release.versionCode!=versionCode||release.verificationMode!=CommerceVerification125.SdkClientReported
                ||checkout!=null&&release.consoleApplicationId!=checkout.consoleAppId)
                errors.Add("FirstModerationReleaseMetadataInvalid");
            if(release!=null)errors.AddRange(RuStoreReleasePreflight.Validate(release));
            errors.AddRange(vendorErrors??new[]{"FirstModerationVendorInventoryMissing"});
            errors.AddRange(adErrors??new[]{"FirstModerationAdvertisingInventoryMissing"});
            errors.AddRange(toolchainErrors??new[]{"FirstModerationAndroidToolchainMissing"});
            return errors.Distinct().ToArray();
        }

        public static bool GuardIfSelected(BuildReport report){
            var defines=PlayerSettings.GetScriptingDefineSymbols(NamedBuildTarget.Android).Split(';').ToList();
            if(File.Exists("Assets/csc.rsp"))defines.AddRange(File.ReadAllText("Assets/csc.rsp").Replace("-define:","").Trim().Split(';'));
            string channel=Environment.GetEnvironmentVariable("HOTR_BUILD_CHANNEL");
            if(!defines.Contains(Define)&&channel!=Channel)return false;
            if(report==null)throw new BuildFailedException("FirstModerationBuildReportRequired");
            CheckoutConfiguration86 checkout=null;ServerGameplayConfiguration server=null;RewardedAdsConfiguration85 ads=null;
            string ignored;
            CheckoutConfiguration86.TryRead(out checkout);
            ServerGameplayConfiguration.TryRead(out server,out ignored);
            RewardedAdsConfiguration85.TryRead(out ads,out ignored);
            RuStoreReleaseConfiguration release=null;
            try{release=JsonUtility.FromJson<RuStoreReleaseConfiguration>(File.ReadAllText(Environment.GetEnvironmentVariable(RuStoreReleasePreflight.ConfigVariable)));}catch(Exception){}
            var vendor=SdkVendorBindings125.ActualPackageErrors().ToList();
            if(release!=null)vendor.AddRange(SdkVendorBindings125.ActualBindingErrors(release.consoleApplicationId,release.paymentReturnScheme));
            var errors=Validate(report.summary.platform==BuildTarget.Android,report.summary.options,
                PlayerSettings.Android.useCustomKeystore,PlayerSettings.Android.keyaliasName,Application.unityVersion,
                PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android),(int)PlayerSettings.Android.minSdkVersion,
                (int)PlayerSettings.Android.targetSdkVersion,PlayerSettings.Android.bundleVersionCode,
                PlayerSettings.GetScriptingBackend(NamedBuildTarget.Android)==ScriptingImplementation.IL2CPP,
                PlayerSettings.Android.targetArchitectures==AndroidArchitecture.ARM64,defines.ToArray(),channel,
                checkout,server,ads,release,vendor.ToArray(),AdvertisingCombinedBoundary126.ActualErrors(),
                SdkCheckoutBuild125.ActualToolchainErrors());
            if(errors.Length>0)throw new BuildFailedException("First moderation blocked: "+string.Join(",",errors));
            return true;
        }
    }
}
#endif

#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using HeartOfTheRain.App.Advertising;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.ShopCheckout86;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace HeartOfTheRain.App.RuStore.Editor {
    public static class FirstModeration130Verification {
        [Serializable] sealed class Report {public string status="FAIL_NATIVE_FIRST_MODERATION130",unity,error;public int checks;}
        static Report result;
        static void Check(bool yes,string name){if(!yes)throw new InvalidOperationException(name);result.checks++;}
        static string[] Evaluate(string[] defines=null,string channel=FirstModeration130.Channel,BuildOptions options=BuildOptions.None,
            bool signing=true,bool production=false,string privacy=FirstModeration130.PrivacyVersion,string[] vendor=null){
            var checkout=new CheckoutConfiguration86{version=3,enabled=true,sandbox=!production,productionEnabled=production,
                packageName=FirstModeration130.Package,backendOrigin=FirstModeration130.Origin,consoleAppId="2063777840",verificationMode=CommerceVerification125.SdkClientReported};
            var server=new ServerGameplayConfiguration{version=3,mode="ManagedGuestServer",origin=FirstModeration130.Origin,productionEnabled=production};
            var ads=new RewardedAdsConfiguration85{version=2,enabled=true,rewardedUnitId="R-M-20291714-1",interstitialUnitId="R-M-20291714-2",
                privacyUrl=FirstModeration130.Origin+"/privacy",privacyVersion=privacy};
            var release=new RuStoreReleaseConfiguration{schemaVersion=1,minimumApiLevel=26,targetApiLevel=36,versionCode=130,
                packageName=FirstModeration130.Package,consoleApplicationId="2063777840",paymentReturnScheme="heartoftherain-pay",
                backendOrigin=FirstModeration130.Origin,privacyPolicyUrl=FirstModeration130.Origin+"/privacy",
                supportUrl=FirstModeration130.Origin+"/support",termsUrl=FirstModeration130.Origin+"/terms",
                signingCertificateSha256="7257537a5b329cc5b018d93299d748404432c1b49f1b2388444ab843a4ba170d",
                environment="sandbox",verificationMode=CommerceVerification125.SdkClientReported};
            return FirstModeration130.Validate(true,options,signing,"heartoftherain-release","6000.3.27f1",
                FirstModeration130.Package,26,36,130,true,true,defines??new[]{FirstModeration130.Define,"HOTR_RUSTORE_PAY","HOTR_RUSTORE_SDK_ONLY125","HOTR_YANDEX_ADS"},
                channel,checkout,server,ads,release,vendor??Array.Empty<string>(),Array.Empty<string>(),Array.Empty<string>());
        }
        public static void Run(){
            result=new Report{unity=Application.unityVersion};
            try{
#if HOTR_FIRST_MODERATION130
                Check(ShopCheckoutHost86.FirstModerationPurchasesDisabled,"CheckoutCompiledDisabled");
                Check(Evaluate().Length==0,"QualifiedFirstModerationProfileAccepted");
#else
                Check(!ShopCheckoutHost86.FirstModerationPurchasesDisabled,"OrdinaryCheckoutProfilePreserved");
                Check(Evaluate().Contains("FirstModerationCheckoutMustBeCompiledOut"),"MissingCompiledDisableRejected");
#endif
                Check(Evaluate(channel:"rustore").Contains("FirstModerationExplicitProfileRequired"),"WrongChannelRejected");
                Check(Evaluate(options:BuildOptions.Development).Contains("FirstModerationSignedNonDebugAndroidRequired"),"DevelopmentRejected");
                Check(Evaluate(signing:false).Contains("FirstModerationSignedNonDebugAndroidRequired"),"UnsignedRejected");
                Check(Evaluate(production:true).Contains("FirstModerationStagingCheckoutBindingInvalid"),"ProductionCheckoutRejected");
                Check(Evaluate(production:true).Contains("FirstModerationStagingServerBindingInvalid"),"ProductionServerRejected");
                Check(Evaluate(privacy:"draft-2026-10-30").Contains("FirstModerationApprovedAdvertisingRequired"),"OldPolicyVersionRejected");
                Check(Evaluate(vendor:new[]{"VendorChanged"}).Contains("VendorChanged"),"VendorDriftRejected");
                Check(Evaluate(defines:new[]{FirstModeration130.Define,"HOTR_RUSTORE_PAY","HOTR_RUSTORE_SDK_ONLY125","HOTR_YANDEX_ADS","HOTR_INTERSTITIAL_DEMO129"}).Contains("FirstModerationCompiledFeatureSetInvalid"),"DemoAdRejected");
                result.status="PASS_NATIVE_FIRST_MODERATION130";
            }catch(Exception e){result.error=e.Message;}
            string output=Environment.GetEnvironmentVariable("HOTR_REVIEW130_GUARD_OUT");
            if(!string.IsNullOrEmpty(output)){Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"FirstModeration130.json"),JsonUtility.ToJson(result,true));}
            if(Application.isBatchMode)EditorApplication.Exit(result.status.StartsWith("PASS_",StringComparison.Ordinal)?0:1);
        }
    }
}
#endif

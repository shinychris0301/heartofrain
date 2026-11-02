#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.PackageManager;
using UnityEditor.Android;
using UnityEngine;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.ShopCheckout86;
using PackageInfo = UnityEditor.PackageManager.PackageInfo;

namespace HeartOfTheRain.App.RuStore.Editor
{
    [Serializable] public sealed class RuStoreReleaseConfiguration
    {
        public int schemaVersion, minimumApiLevel, targetApiLevel, versionCode;
        public string packageName, consoleApplicationId, paymentReturnScheme, backendOrigin;
        public string privacyPolicyUrl, supportUrl, termsUrl, signingCertificateSha256, environment,verificationMode;
    }

    // This is a release gate, not an alternative to the SDK's manifest verifier
    // or proof of a working payment service. No secret is read into this DTO.
    public static class RuStoreReleasePreflight
    {
        public const string ConfigVariable = "HOTR_RUSTORE_RELEASE_CONFIG";
        public const string ChannelVariable = "HOTR_BUILD_CHANNEL";
        public const string ExternalJavaVariable = "HOTR_RUSTORE_JDK17_ROOT";
        public const int MinimumApi = 26;
        public const string PayVersion = "11.1.0", CoreVersion = "10.5.0";

        public static List<string> Validate(RuStoreReleaseConfiguration c)
        {
            var errors = new List<string>();
            if(c == null) { errors.Add("release_configuration_missing"); return errors; }
            if(c.schemaVersion != 1) errors.Add("release_schema_unsupported");
            try{CommerceVerification125.Legacy(c.verificationMode);}catch{errors.Add("payment_verification_mode_invalid");}
            if(!Match(c.packageName,@"\A[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2,}\z") ||
               c.packageName.Contains("verification") || c.packageName.Contains("defaultcompany") ||
               c.packageName.Contains("example")) errors.Add("registered_package_name_required");
            long appId;
            if(!Match(c.consoleApplicationId,@"\A[1-9][0-9]{0,18}\z") ||
               !long.TryParse(c.consoleApplicationId,System.Globalization.NumberStyles.None,System.Globalization.CultureInfo.InvariantCulture,out appId) || appId<1)
                errors.Add("console_application_id_required");
            if(!Match(c.paymentReturnScheme,@"\A[a-z][a-z0-9+.-]{2,62}\z") ||
               new[]{"http","https","file","intent","content","javascript"}.Contains(c.paymentReturnScheme))
                errors.Add("unique_payment_return_scheme_required");
            if(!Https(c.backendOrigin,true)) errors.Add("deployed_https_backend_required");
            if(!Https(c.privacyPolicyUrl,false)) errors.Add("russian_privacy_policy_url_required");
            if(!Https(c.supportUrl,false)) errors.Add("support_url_required");
            if(!Https(c.termsUrl,false)) errors.Add("terms_url_required");
            if(c.minimumApiLevel < MinimumApi) errors.Add("minimum_api_26_required");
            if(c.targetApiLevel < c.minimumApiLevel || c.targetApiLevel > 1000) errors.Add("explicit_target_api_required");
            if(c.versionCode < 1) errors.Add("version_code_required");
            if(!Match(c.signingCertificateSha256,@"\A[0-9a-fA-F]{64}\z") || c.signingCertificateSha256.ToLowerInvariant().Distinct().Count()<2)
                errors.Add("release_signing_identity_required");
            if(c.environment != "sandbox" && c.environment != "production") errors.Add("explicit_payment_environment_required");
            if(c.environment == "production" && c.verificationMode == CommerceVerification125.SdkClientReported)
                errors.Add("client_reported_backend_credit_disallowed");
            return errors;
        }
        static bool Match(string value,string pattern) => value != null && Regex.IsMatch(value,pattern);
        static bool Https(string value,bool origin)
        {
            Uri uri;
            if(string.IsNullOrWhiteSpace(value) || value.Any(char.IsControl) || !Uri.TryCreate(value,UriKind.Absolute,out uri) ||
               uri.Scheme != "https" || uri.UserInfo.Length != 0 || uri.Query.Length != 0 || uri.Fragment.Length != 0 ||
               uri.IsLoopback || uri.HostNameType != UriHostNameType.Dns || !uri.Host.Contains(".")) return false;
            string host=uri.DnsSafeHost.ToLowerInvariant();
            if(new[]{"example.com","example.org","example.net","example","invalid","test","localhost","local"}
                .Any(h=>host==h||host.EndsWith("."+h,StringComparison.Ordinal))) return false;
            return !origin || uri.AbsolutePath == "/";
        }
        [Serializable] sealed class Report
        {
            public string utc,unity,status,configStatus,payVersion,coreVersion,javaVersion,externalJavaVersion;
            public int currentMinimumApi,currentTargetApi;
            public bool activationReady,known2025SecurityFix,projectSettingsUnchanged;
            public string[] blockers;
            public string scope="Native Editor readback and release configuration checks only. No Console registration, SDK payment, real hosting, legal approval, store signing or publication. Provider/device acceptance blocks release independently of public configuration syntax.";
        }
        // Public configuration can select the implemented production code path;
        // it cannot certify its hosted Android/provider acceptance. Keep those
        // diagnostics distinct from the legacy unconfigured/offline selection.
        public static List<string> IntegrationBlockers122(RuStoreReleaseConfiguration config,string actualPackage,
            ServerConfigurationInput104 server,ServerConfigurationInput104 checkout,bool stagingPresent){
            bool configured=false;
            try{
                ServerGameplayConfiguration selected;string why;
                ServerProductionConfiguration122.Resolve(true,actualPackage,server,stagingPresent,out selected,out why);
                if(config!=null&&config.environment=="production"&&selected!=null&&config.packageName==actualPackage
                    &&config.backendOrigin==selected.origin&&config.consoleApplicationId==selected.consoleAppId
                    &&checkout!=null&&checkout.present&&!checkout.failed){
                    CheckoutConfiguration86.ParseProduction122(checkout.json,selected,actualPackage);configured=true;
                }
            }catch(Exception){/* Rejected metadata never establishes integration or acceptance. */}
            var errors=new List<string>();
            if(configured)errors.Add("configured_production_identity_and_wallet_android_acceptance_required");
            else{
                errors.Add("production_identity_and_secure_credential_recovery_not_connected");
                errors.Add("unified_server_gameplay_wallet_not_connected");
            }
            errors.Add("provider_notification_authentication_not_configured");
            errors.Add("native_sandbox_and_external_bank_return_not_verified");
            errors.Add("production_signing_and_legal_hosting_review_not_complete");
            return errors;
        }
        // Only a matching strict packaged SDK profile changes the provider
        // requirements. Merely writing a mode string cannot waive a gate.
        public static List<string> IntegrationBlockers125(RuStoreReleaseConfiguration config,string actualPackage,ServerConfigurationInput104 sdk,
            ServerConfigurationInput104 production,ServerConfigurationInput104 staging,ServerConfigurationInput104 legacyCheckout){
            bool sdkSelected=config!=null&&config.verificationMode==CommerceVerification125.SdkClientReported;
            if(!sdkSelected){
                var result=IntegrationBlockers122(config,actualPackage,production,legacyCheckout,staging!=null&&staging.present);
                if(sdk!=null&&sdk.present)result.Add("packaged_sdk_checkout_mode_does_not_match_release_config");
                return result;
            }
            bool configured=false;
            try{
                ServerGameplayConfiguration selected;string why;
                CheckoutSdkConfiguration125.Resolve(true,actualPackage,sdk,production,staging,legacyCheckout,out selected,out why);
                configured=selected!=null&&config.packageName==actualPackage&&config.backendOrigin==selected.origin&&config.consoleApplicationId==selected.consoleAppId
                    &&config.environment==(selected.productionEnabled?"production":"sandbox");
            }catch(Exception){/* Invalid/mixed metadata never establishes integration. */}
            if(!configured){var result=IntegrationBlockers122(config,actualPackage,production,legacyCheckout,staging!=null&&staging.present);result.Add("strict_sdk_checkout_managed_profile_required");return result;}
            return new List<string>{"configured_sdk_managed_wallet_android_acceptance_required","native_sdk_payment_recovery_and_external_bank_return_not_verified","production_signing_and_legal_hosting_review_not_complete"};
        }
        public static List<string> Evaluate(out bool hasConfig)
        {
            string path=Environment.GetEnvironmentVariable(ConfigVariable);hasConfig=!string.IsNullOrWhiteSpace(path);
            RuStoreReleaseConfiguration config=null;var errors=new List<string>();
            if(hasConfig) {
                try { config=JsonUtility.FromJson<RuStoreReleaseConfiguration>(File.ReadAllText(path)); }
                catch { errors.Add("release_configuration_unreadable"); }
            }
            errors.AddRange(Validate(config));
            var integration=IntegrationBlockers125(config,PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android),
                ServerProductionConfiguration122.ReadResource(CheckoutSdkConfiguration125.ResourceKey),
                ServerProductionConfiguration122.ReadResource(ServerProductionConfiguration122.ResourceKey),
                ServerProductionConfiguration122.ReadResource(ServerStagingConfiguration104.ResourceKey),
                ServerProductionConfiguration122.ReadResource(ServerProductionConfiguration122.CheckoutResourceKey));
            bool sdkConfigured=integration.Contains("configured_sdk_managed_wallet_android_acceptance_required");
            // Unity2022 rejects Java17 in its Editor JDK setter. The separately
            // exported Gradle build uses an explicitly configured Java17 root;
            // do not bypass the Editor's supported embedded-JDK selection.
            if(sdkConfigured)errors.AddRange(HeartOfTheRain.App.ServerGameplay.Editor.SdkCheckoutBuild125.ActualToolchainErrors());
            else if(!JavaVersion(Environment.GetEnvironmentVariable(ExternalJavaVariable)).StartsWith("17.",StringComparison.Ordinal))
                errors.Add("external_java_17_required_for_rustore_profile");
            var packages=PackageInfo.GetAllRegisteredPackages();
            if(!packages.Any(p=>p.name=="ru.rustore.pay"&&p.version==PayVersion)) errors.Add("verified_pay_sdk_11_1_0_installation_required");
            if(!packages.Any(p=>p.name=="ru.rustore.core"&&p.version==CoreVersion)) errors.Add("compatible_core_10_5_0_installation_required");
            if(config!=null) {
                if(PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android)!=config.packageName) errors.Add("player_package_does_not_match_release_config");
                if((int)PlayerSettings.Android.minSdkVersion<MinimumApi) errors.Add("release_minimum_api_not_applied");
                if((int)PlayerSettings.Android.minSdkVersion!=config.minimumApiLevel) errors.Add("player_minimum_api_does_not_match_release_config");
                if((int)PlayerSettings.Android.targetSdkVersion!=config.targetApiLevel) errors.Add("release_target_api_not_applied");
            }
            errors.AddRange(integration);
            return errors.Distinct().ToList();
        }
        static string JavaVersion(string root=null)
        {
            try {
                if(string.IsNullOrWhiteSpace(root))return "not_configured";
                string release=File.ReadAllText(Path.Combine(root,"release"));
                var match=Regex.Match(release,"JAVA_VERSION=\"([^\"]+)\"");
                return match.Success?match.Groups[1].Value:"unknown";
            } catch { return "unknown"; }
        }
        [MenuItem("Heart of the Rain/RuStore/Check release readiness")]
        public static void Run()
        {
            string settingsPath=Path.GetFullPath("ProjectSettings/ProjectSettings.asset");byte[] before=File.ReadAllBytes(settingsPath);
            bool hasConfig;var errors=Evaluate(out hasConfig);var packages=PackageInfo.GetAllRegisteredPackages();
            var report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,
                status=errors.Count==0?"READY_FOR_SEPARATE_NATIVE_RELEASE_VERIFICATION":"BLOCKED_RUSTORE_EXTERNAL_CONFIGURATION_AND_INTEGRATION",
                configStatus=hasConfig?"external_configuration_supplied":"not_configured",activationReady=errors.Count==0,
                known2025SecurityFix=Application.unityVersion=="2022.3.62f3",projectSettingsUnchanged=before.SequenceEqual(File.ReadAllBytes(settingsPath)),
                payVersion=packages.FirstOrDefault(p=>p.name=="ru.rustore.pay")?.version??"not_installed",
                coreVersion=packages.FirstOrDefault(p=>p.name=="ru.rustore.core")?.version??"not_installed",blockers=errors.ToArray()};
            report.javaVersion=JavaVersion(AndroidExternalToolsSettings.jdkRootPath);
            report.externalJavaVersion=JavaVersion(Environment.GetEnvironmentVariable(ExternalJavaVariable));
            report.currentMinimumApi=(int)PlayerSettings.Android.minSdkVersion;
            report.currentTargetApi=(int)PlayerSettings.Android.targetSdkVersion;
            string output=Path.GetFullPath("../Verification/Evidence/RuStore81/Native");Directory.CreateDirectory(output);
            File.WriteAllText(Path.Combine(output,"Release_Preflight.json"),JsonUtility.ToJson(report,true));
            if(Application.isBatchMode)EditorApplication.Exit(report.projectSettingsUnchanged?0:1);
        }
        public static void RequireReady()
        {
            bool hasConfig;var errors=Evaluate(out hasConfig);
            if(errors.Count>0)throw new BuildFailedException("RuStore release blocked: "+string.Join(", ",errors));
        }
    }
    public sealed class RuStoreReleaseGuard:IPreprocessBuildWithReport
    {
        public int callbackOrder=>-10000;
        public void OnPreprocessBuild(BuildReport report)
        {
            if(FirstModeration130.GuardIfSelected(report))return;
            bool productionAndroid=report!=null&&report.summary.platform==BuildTarget.Android&&
                (report.summary.options&BuildOptions.Development)==0&&
                PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android)!="com.heartoftherain.verification";
            if(productionAndroid||Environment.GetEnvironmentVariable(RuStoreReleasePreflight.ChannelVariable)=="rustore")
                RuStoreReleasePreflight.RequireReady();
        }
    }
}
#endif

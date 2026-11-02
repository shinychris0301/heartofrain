#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using HeartOfTheRain.App.Advertising;
using HeartOfTheRain.App.ShopCheckout86;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace HeartOfTheRain.App.ServerGameplay.Editor {
    public static class ProductionBuildConfiguration122 {
        public static string[] Validate(bool android,bool development,bool customSigning,int minimumApi,string package,string[] defines,
            ServerConfigurationInput104 server,ServerConfigurationInput104 checkout,bool stagingPresent){
            var errors=new List<string>();
            if(!android)errors.Add("ProductionAndroidRequired");
            if(development)errors.Add("ProductionDevelopmentOptionsRejected");
            if(!customSigning)errors.Add("ProductionDeveloperReleaseSignerRequired");
            if(minimumApi<26)errors.Add("ProductionProtectedIdentityApi26Required");
            if(defines==null||!defines.Contains("HOTR_PRODUCTION122"))errors.Add("ProductionExplicitBuildDefineRequired");
            if(defines==null||!defines.Contains("HOTR_RUSTORE_PAY"))errors.Add("ProductionRuStoreSdkRequired");
            ServerGameplayConfiguration parsed;string why;
            ServerProductionConfiguration122.Resolve(true,package,server,stagingPresent,out parsed,out why);
            if(parsed==null)errors.Add("ProductionPackagedServerBindingInvalid");
            try{
                if(checkout==null||!checkout.present||checkout.failed)throw new FormatException();
                CheckoutConfiguration86.ParseProduction122(checkout.json,parsed,package);
            }catch(Exception){errors.Add("ProductionPackagedCheckoutBindingInvalid");}
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
            if(SdkCheckoutBuild125.GuardIfSelected(report))return true;
            var server=Imported(ServerProductionConfiguration122.ResourceKey,ServerProductionConfiguration122.ResourceAssetPath);
            var checkout=Imported(ServerProductionConfiguration122.CheckoutResourceKey,ServerProductionConfiguration122.CheckoutResourceAssetPath);
            var defines=PlayerSettings.GetScriptingDefineSymbolsForGroup(BuildTargetGroup.Android).Split(';');
            if(!server.present&&!checkout.present&&!defines.Contains("HOTR_PRODUCTION122"))return false;
            bool staging=AssetDatabase.GetAllAssetPaths().Any(StagingServerBuild104.ReservedResourcePath);
            var options=report.summary.options;
            var errors=Validate(report.summary.platform==BuildTarget.Android,(options&(BuildOptions.Development|BuildOptions.AllowDebugging|BuildOptions.ConnectWithProfiler|BuildOptions.EnableDeepProfilingSupport))!=0,
                PlayerSettings.Android.useCustomKeystore,(int)PlayerSettings.Android.minSdkVersion,PlayerSettings.GetApplicationIdentifier(BuildTargetGroup.Android),defines,server,checkout,staging).ToList();
            var advertising=Imported(AdvertisingConfiguration107.ResourceKey,AdvertisingConfiguration107.ResourceAssetPath);
            RewardedAdsConfiguration85 ads;string why;
            if(!advertising.present||advertising.failed||!RewardedAdsConfiguration85.TryParsePackaged(advertising.json,out ads,out why))errors.Add("ProductionAdvertisingPayloadInvalid");
            else if(ads.enabled&&!defines.Contains("HOTR_YANDEX_ADS"))errors.Add("ProductionEnabledAdvertisingSdkRequired");
            if(errors.Count>0)throw new BuildFailedException(string.Join(",",errors));
            return true;
        }
    }
    public sealed class ProductionBuildGuard122:IPreprocessBuildWithReport {
        public int callbackOrder=>-21000;
        public void OnPreprocessBuild(BuildReport report)=>ProductionBuildConfiguration122.GuardIfSelected(report);
    }
}
#endif

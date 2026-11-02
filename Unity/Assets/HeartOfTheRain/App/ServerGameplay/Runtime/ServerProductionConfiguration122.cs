using System;
using System.Linq;
using System.Text.RegularExpressions;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.RuStore;
using UnityEngine;

namespace HeartOfTheRain.App.ServerGameplay {
    // Public immutable build metadata. No provider key or device override is read.
    public static class ServerProductionConfiguration122 {
        public const string ResourceKey="HOTR_Server/ManagedProduction";
        public const string ResourceAssetPath="Assets/HeartOfTheRain/Resources/HOTR_Server/ManagedProduction.json";
        public const string CheckoutResourceKey="HOTR_RuStore/CheckoutProduction";
        public const string CheckoutResourceAssetPath="Assets/HeartOfTheRain/Resources/HOTR_RuStore/CheckoutProduction.json";
        public const string InvalidError="ExplicitProductionConfigurationInvalid";
        public static bool ProfileRequired {
            get {
#if HOTR_PRODUCTION122
                return true;
#else
                return false;
#endif
            }
        }
        public static bool AppId(string value){long parsed;return value!=null&&Regex.IsMatch(value,@"\A[1-9][0-9]{0,18}\z")&&long.TryParse(value,out parsed)&&parsed>0;}
        public static ServerConfigurationInput104 ReadResource(string key){
            try{
                var exact=Resources.Load<UnityEngine.Object>(key);var all=Resources.LoadAll(key);
                if(!exact&&all.Length==0)return ServerConfigurationInput104.Absent;
                if(!(exact is TextAsset text)||all.Length!=1||all[0]!=exact)return ServerConfigurationInput104.Invalid;
                return new ServerConfigurationInput104(true,text.text);
            }catch(Exception){return ServerConfigurationInput104.Invalid;}
        }
        public static ServerGameplayConfiguration Parse(string json){
            try{
                if(json==null||new System.Text.UTF8Encoding(false,true).GetByteCount(json)>8192)throw new FormatException();
                var row=SocialJson82.Read(json);
                var allowed=new[]{"version","mode","runtimeMode","origin","identityScope","packageName","consoleAppId","socialEnabled","allowDevelopmentLoopback"};
                if(row.Count!=allowed.Length||row.Keys.Any(key=>!allowed.Contains(key)))throw new FormatException();
                SocialJson82.Number(row,"version",2,2);
                if(SocialJson82.Text(row,"mode",64)!="ManagedGuestServer"||SocialJson82.Text(row,"runtimeMode",16)!="production"||SocialJson82.Flag(row,"allowDevelopmentLoopback"))throw new FormatException();
                string origin=SocialJson82.Text(row,"origin",512),package=SocialJson82.Text(row,"packageName",255),appId=SocialJson82.Text(row,"consoleAppId",19),scope=SocialJson82.Text(row,"identityScope",55);
                if(!RuStoreBackendClient.IsAllowedOrigin(origin)||new Uri(origin).Port!=443||new Uri(origin).GetLeftPart(UriPartial.Authority)!=origin||!AppId(appId)
                    ||!Regex.IsMatch(package,@"\A[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+\z")||package==ServerStagingConfiguration104.PackageName||package=="com.heartoftherain.verification"
                    ||!Regex.IsMatch(scope,@"\Aprod-[a-z0-9.-]{1,50}\z"))throw new FormatException();
                return new ServerGameplayConfiguration{version=2,mode="ManagedGuestServer",origin=origin,identityScope=scope,socialEnabled=SocialJson82.Flag(row,"socialEnabled"),
                    productionEnabled=true,consoleAppId=appId,packageName=package};
            }catch(Exception){throw new FormatException(InvalidError);}
        }
        // Returning true includes a blocked required profile: no caller may fall
        // through to a persistent, environment or staging configuration after it.
        public static bool Resolve(bool required,string actualPackage,ServerConfigurationInput104 packaged,bool stagingPresent,out ServerGameplayConfiguration value,out string error){
            value=null;error=null;
            if(!required&&(packaged==null||!packaged.present))return false;
            try{
                if(packaged==null||!packaged.present||packaged.failed||stagingPresent)throw new FormatException();
                var parsed=Parse(packaged.json);if(parsed.packageName!=actualPackage)throw new FormatException();value=parsed;
            }catch(Exception){error=InvalidError;}
            return true;
        }
    }
}

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.ServerGameplay;
using UnityEngine;

namespace HeartOfTheRain.App.RuStore {
    public enum CommerceVerificationMode125 { ProviderApi, SdkClientReported }
    // This describes the source of a payment observation, not its authenticity.
    public static class CommerceVerification125 {
        public const string ProviderApi="provider_api",SdkClientReported="sdk_client_reported";
        public static string Legacy(string value){if(value==null)return ProviderApi;if(value!=ProviderApi&&value!=SdkClientReported)throw new FormatException("CommerceVerificationModeInvalid");return value;}
        public static CommerceVerificationMode125 Value(string value)=>Legacy(value)==SdkClientReported?CommerceVerificationMode125.SdkClientReported:CommerceVerificationMode125.ProviderApi;
        public static string Read(Dictionary<string,object> row){object value;if(!row.TryGetValue("verificationMode",out value))return ProviderApi;if(!(value is string text))throw new FormatException("CommerceVerificationModeInvalid");return Legacy(text);}
    }
}

namespace HeartOfTheRain.App.ShopCheckout86 {
    // The distinct packaged profile is the only opt-in to app-reported grants.
    // No environment variable, persistent device file or local-wallet fallback.
    public static class CheckoutSdkConfiguration125 {
        public const string ResourceKey="HOTR_RuStore/CheckoutSdk125";
        public const string ResourceAssetPath="Assets/HeartOfTheRain/Resources/HOTR_RuStore/CheckoutSdk125.json";
        public const string InvalidError="ExplicitSdkCheckoutConfigurationInvalid";
        public static bool Required {
            get {
#if HOTR_RUSTORE_SDK_ONLY125
                return true;
#else
                return false;
#endif
            }
        }
        sealed class Header {public string mode,origin,package,appId;public bool production;}
        static Header Read(string json,string actualPackage){
            var row=SocialJson82.Read(json);var fields=new[]{"version","enabled","verificationMode","sandbox","consoleAppId","runtimeMode","packageName","backendOrigin"};
            if(json==null||System.Text.Encoding.UTF8.GetByteCount(json)>4096||row.Count!=fields.Length||row.Keys.Any(key=>!fields.Contains(key)))throw new FormatException();
            SocialJson82.Number(row,"version",1,1);
            string mode=SocialJson82.Text(row,"runtimeMode",16),origin=SocialJson82.Text(row,"backendOrigin",512),package=SocialJson82.Text(row,"packageName",255),appId=SocialJson82.Text(row,"consoleAppId",19);
            if(!SocialJson82.Flag(row,"enabled")||CommerceVerification125.Read(row)!=CommerceVerification125.SdkClientReported||mode!="staging"&&mode!="production"||SocialJson82.Flag(row,"sandbox")!=(mode=="staging")
                ||!ServerProductionConfiguration122.AppId(appId)||package!=actualPackage||!Regex.IsMatch(package,@"\A[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){2,}\z")
                ||package.Contains("verification")||package.Contains("defaultcompany")||package.Contains("example")||package==ServerStagingConfiguration104.PackageName
                ||!RuStoreBackendClient.IsAllowedOrigin(origin)||new Uri(origin).Port!=443||new Uri(origin).GetLeftPart(UriPartial.Authority)!=origin)throw new FormatException();
            return new Header{mode=mode,origin=origin,package=package,appId=appId,production=mode=="production"};
        }
        public static CheckoutConfiguration86 Parse(string json,ServerGameplayConfiguration server,string actualPackage){
            try{
                var header=Read(json,actualPackage);
                if(server==null||server.mode!="ManagedGuestServer"||server.productionEnabled!=header.production||server.allowDevelopmentLoopback||server.origin!=header.origin
                    ||server.packageName!=header.package||server.consoleAppId!=header.appId)throw new FormatException();
                return new CheckoutConfiguration86{version=3,enabled=true,sandbox=!header.production,productionEnabled=header.production,consoleAppId=header.appId,
                    packageName=header.package,backendOrigin=header.origin,verificationMode=CommerceVerification125.SdkClientReported};
            }catch(Exception){throw new FormatException(InvalidError);}
        }
        // As in122, true includes a required-but-blocked selection. That stops
        // every older configuration source from silently changing authority.
        public static bool Resolve(bool required,string actualPackage,ServerConfigurationInput104 sdk,ServerConfigurationInput104 production,
            ServerConfigurationInput104 staging,ServerConfigurationInput104 legacyCheckout,out ServerGameplayConfiguration selected,out string error){
            selected=null;error=null;
            if(!required&&(sdk==null||!sdk.present))return false;
            try{
                if(sdk==null||!sdk.present||sdk.failed||legacyCheckout!=null&&legacyCheckout.present)throw new FormatException();
                var header=Read(sdk.json,actualPackage);
                if(header.production){
                    string why;ServerProductionConfiguration122.Resolve(true,actualPackage,production,staging!=null&&staging.present,out selected,out why);
                    if(selected==null)throw new FormatException();
                }else{
                    if(production!=null&&production.present||staging==null||!staging.present||staging.failed)throw new FormatException();
                    string why;if(!ServerStagingConfiguration104.TryParsePackaged(staging.json,out selected,out why)||selected.allowDevelopmentLoopback)throw new FormatException();
                    selected.packageName=header.package;selected.consoleAppId=header.appId;
                }
                Parse(sdk.json,selected,actualPackage);
            }catch(Exception){selected=null;error=InvalidError;}
            return true;
        }
        public static bool TryReadManaged(out ServerGameplayConfiguration selected,out string error)=>Resolve(Required,Application.identifier,
            ServerProductionConfiguration122.ReadResource(ResourceKey),ServerProductionConfiguration122.ReadResource(ServerProductionConfiguration122.ResourceKey),
            ServerProductionConfiguration122.ReadResource(ServerStagingConfiguration104.ResourceKey),ServerProductionConfiguration122.ReadResource(ServerProductionConfiguration122.CheckoutResourceKey),out selected,out error);
    }
}

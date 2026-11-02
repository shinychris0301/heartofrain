using System;
using System.IO;
using UnityEngine;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.OnlineSocial;

namespace HeartOfTheRain.App.ServerGameplay {
    [Serializable] public sealed class ServerGameplayConfiguration {
        public int version; public string mode,origin,identityScope; public bool allowDevelopmentLoopback,socialEnabled;
        [NonSerialized] public bool productionEnabled;
        [NonSerialized] public string consoleAppId,packageName;
        // Public for the Editor staging builder too: parsing never reads a file,
        // loads Resources, creates an identity or changes an ordinary profile.
        public static ServerGameplayConfiguration Parse(string json){
            try{
                if(json==null||System.Text.Encoding.UTF8.GetByteCount(json)<2||System.Text.Encoding.UTF8.GetByteCount(json)>8192)throw new FormatException();
                var fields=SocialJson82.Read(json);
                foreach(string key in fields.Keys)if(key!="version"&&key!="mode"&&key!="origin"&&key!="identityScope"&&key!="allowDevelopmentLoopback"&&key!="socialEnabled")throw new FormatException();
                var value=new ServerGameplayConfiguration{
                    version=(int)SocialJson82.Number(fields,"version",1,1),mode=SocialJson82.Text(fields,"mode",64),origin=SocialJson82.Text(fields,"origin",2048),identityScope=SocialJson82.Text(fields,"identityScope",57),
                    allowDevelopmentLoopback=fields.ContainsKey("allowDevelopmentLoopback")&&SocialJson82.Flag(fields,"allowDevelopmentLoopback"),socialEnabled=fields.ContainsKey("socialEnabled")&&SocialJson82.Flag(fields,"socialEnabled")};
                if(value.mode!="ManagedGuestServer"||!RuStoreBackendClient.IsAllowedOrigin(value.origin,value.allowDevelopmentLoopback)||!System.Text.RegularExpressions.Regex.IsMatch(value.identityScope,@"\Areview-[a-z0-9.-]{1,50}\z"))throw new FormatException();
                value.origin=new Uri(value.origin).GetLeftPart(UriPartial.Authority);return value;
            }catch(Exception){throw new FormatException(ServerStagingConfiguration104.InvalidError);}
        }
        public static bool TryRead(out ServerGameplayConfiguration config,out string error){
            if(HeartOfTheRain.App.ShopCheckout86.CheckoutSdkConfiguration125.TryReadManaged(out config,out error)){
                if(ServerProductionConfiguration122.ProfileRequired&&config!=null&&!config.productionEnabled){config=null;error=HeartOfTheRain.App.ShopCheckout86.CheckoutSdkConfiguration125.InvalidError;}
                return true;
            }
            var production=ServerProductionConfiguration122.ReadResource(ServerProductionConfiguration122.ResourceKey);
            if(production.present||ServerProductionConfiguration122.ProfileRequired){
                var staging=ReadPackaged();
                return ServerProductionConfiguration122.Resolve(ServerProductionConfiguration122.ProfileRequired,Application.identifier,production,staging.present,out config,out error);
            }
            string path=Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG");bool explicitPath=!string.IsNullOrEmpty(path);
            var external=ServerConfigurationInput104.Absent;var packaged=ServerConfigurationInput104.Absent;var persistent=ServerConfigurationInput104.Absent;
            if(Application.isEditor&&explicitPath)external=ReadFile(path);
            else {
                packaged=ReadPackaged();
                if(!packaged.present&&(Application.isEditor||Application.identifier!=ServerStagingConfiguration104.PackageName)){
                    if(explicitPath)external=ReadFile(path);else persistent=ReadFile(Path.Combine(Application.persistentDataPath,"ServerReview","configuration.json"));
                }
            }
            string source;return ServerGameplaySelection104.Resolve(Application.isEditor,Debug.isDebugBuild,Application.identifier,explicitPath,external,packaged,persistent,out config,out error,out source);
        }
        static ServerConfigurationInput104 ReadFile(string path){
            try{
                using(var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)){
                    if(file.Length<2||file.Length>8192)return ServerConfigurationInput104.Invalid;
                    var bytes=new byte[(int)file.Length];int at=0;while(at<bytes.Length){int count=file.Read(bytes,at,bytes.Length-at);if(count==0)return ServerConfigurationInput104.Invalid;at+=count;}
                    if(file.ReadByte()!=-1)return ServerConfigurationInput104.Invalid;
                    int start=bytes.Length>=3&&bytes[0]==239&&bytes[1]==187&&bytes[2]==191?3:0;
                    return new ServerConfigurationInput104(true,new System.Text.UTF8Encoding(false,true).GetString(bytes,start,bytes.Length-start));
                }
            }catch(FileNotFoundException){return ServerConfigurationInput104.Absent;}
            catch(DirectoryNotFoundException){return ServerConfigurationInput104.Absent;}
            catch(Exception){return ServerConfigurationInput104.Invalid;}
        }
        static ServerConfigurationInput104 ReadPackaged(){
            try{
                var exact=Resources.Load<UnityEngine.Object>(ServerStagingConfiguration104.ResourceKey);var assets=Resources.LoadAll(ServerStagingConfiguration104.ResourceKey);
                if(!exact&&assets.Length==0)return ServerConfigurationInput104.Absent;
                if(!(exact is TextAsset text)||assets.Length!=1||assets[0]!=exact)return ServerConfigurationInput104.Invalid;
                return new ServerConfigurationInput104(true,text.text);
            }catch(Exception){return ServerConfigurationInput104.Invalid;}
        }
    }
}

using System;
using System.IO;
using System.Text;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.ServerGameplay;
using UnityEngine;

namespace HeartOfTheRain.App.Advertising {
    public sealed class AdvertisingConfigurationInput107 {
        public readonly bool present,failed;public readonly string json;
        public AdvertisingConfigurationInput107(bool present,string json=null,bool failed=false){this.present=present;this.json=json;this.failed=failed;}
        public static AdvertisingConfigurationInput107 Absent=>new AdvertisingConfigurationInput107(false);
        public static AdvertisingConfigurationInput107 Invalid=>new AdvertisingConfigurationInput107(true,null,true);
    }
    // Public placement IDs are configuration, not an SDK activation or wallet grant.
    // An existing packaged value, including a disabled/invalid one, owns selection.
    public static class AdvertisingConfiguration107 {
        public const string ResourceKey="HOTR_Advertising/Configuration";
        public const string ResourceAssetPath="Assets/HeartOfTheRain/Resources/HOTR_Advertising/Configuration.json";
        public const string RewardedUnitId="R-M-20291714-1",InterstitialUnitId="R-M-20291714-2";
        public const string InvalidError="AdsConfigurationInvalid";
        // Editor build helpers consume this public boundary rather than an
        // internal JSON reader from the player assembly. No IO or activation.
        public static bool TryCanonicalManagedBuild107(string json,out string canonical){
            canonical=null;
            try{
                if(SocialJson82.Read(json).Count!=6)return false;
                ServerGameplayConfiguration config;string error;
                if(!ServerStagingConfiguration104.TryParsePackaged(json,out config,out error))return false;
                canonical=ServerStagingConfiguration104.CanonicalJson(config);return true;
            }catch(Exception){return false;}
        }
        public static bool Select(AdvertisingConfigurationInput107 packaged,AdvertisingConfigurationInput107 persistent,out RewardedAdsConfiguration85 value,out string error,out string source){
            value=null;error=null;source="None";bool package=packaged!=null&&packaged.present;
            var selected=package?packaged:persistent;
            if(selected==null||!selected.present)return false;source=package?"Packaged":"Persistent";
            if(selected.failed){error=InvalidError;return false;}
            if(package)return RewardedAdsConfiguration85.TryParsePackaged(selected.json,out value,out error);
            try{value=RewardedAdsConfiguration85.ParseLegacyOrV2(selected.json);return true;}catch(Exception){error=InvalidError;return false;}
        }
        public static AdvertisingConfigurationInput107 ReadFile(string path){
            try{
                using(var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)){
                    if(file.Length<2||file.Length>4096)return AdvertisingConfigurationInput107.Invalid;
                    var bytes=new byte[(int)file.Length];int at=0;while(at<bytes.Length){int count=file.Read(bytes,at,bytes.Length-at);if(count==0)return AdvertisingConfigurationInput107.Invalid;at+=count;}
                    if(file.ReadByte()!=-1)return AdvertisingConfigurationInput107.Invalid;
                    int start=bytes.Length>=3&&bytes[0]==239&&bytes[1]==187&&bytes[2]==191?3:0;
                    return new AdvertisingConfigurationInput107(true,new UTF8Encoding(false,true).GetString(bytes,start,bytes.Length-start));
                }
            }catch(FileNotFoundException){return AdvertisingConfigurationInput107.Absent;}
            catch(DirectoryNotFoundException){return AdvertisingConfigurationInput107.Absent;}
            catch(Exception){return AdvertisingConfigurationInput107.Invalid;}
        }
        public static AdvertisingConfigurationInput107 ReadPackaged(){
            try{
                var exact=Resources.Load<UnityEngine.Object>(ResourceKey);var all=Resources.LoadAll(ResourceKey);
                if(!exact&&all.Length==0)return AdvertisingConfigurationInput107.Absent;
                if(!(exact is TextAsset text)||all.Length!=1||all[0]!=exact)return AdvertisingConfigurationInput107.Invalid;
                return new AdvertisingConfigurationInput107(true,text.text);
            }catch(Exception){return AdvertisingConfigurationInput107.Invalid;}
        }
    }
}

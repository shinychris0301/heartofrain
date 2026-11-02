using System;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;
using HeartOfTheRain.App.OnlineSocial;

namespace HeartOfTheRain.App.Advertising {
    [Serializable] public sealed class RewardedAdsConfiguration85 {
        public int version;public bool enabled;public string rewardedUnitId,interstitialUnitId,privacyUrl,privacyVersion;
        public static string FilePath=>Path.Combine(Application.persistentDataPath,"HOTR_Advertising.json");
        static bool Unit(string value)=>value!=null&&Regex.IsMatch(value,@"\AR-M-[1-9][0-9]{0,18}-[1-9][0-9]{0,18}\z");
        static bool Privacy(string value){
            if(string.IsNullOrWhiteSpace(value)||value.Length>500)return false;
            foreach(char c in value)if(char.IsControl(c)||char.IsWhiteSpace(c))return false;
            Uri uri;if(!Uri.TryCreate(value,UriKind.Absolute,out uri)||uri.Scheme!="https"||uri.UserInfo!=""||uri.Query!=""||uri.Fragment!=""||uri.IsLoopback||uri.HostNameType!=UriHostNameType.Dns||!uri.Host.Contains("."))return false;
            string host=uri.DnsSafeHost.ToLowerInvariant();
            foreach(string reserved in new[]{"example.com","example.org","example.net","example","invalid","test","localhost","local"})if(host==reserved||host.EndsWith("."+reserved,StringComparison.Ordinal))return false;
            return true;
        }
        static RewardedAdsConfiguration85 Parse(string json,bool legacy){
            try{
                if(json==null||new UTF8Encoding(false,true).GetByteCount(json)<2||new UTF8Encoding(false,true).GetByteCount(json)>4096)throw new FormatException();
                var fields=SocialJson82.Read(json);int version=(int)SocialJson82.Number(fields,"version",1,2);
                if(version==1&&!legacy)throw new FormatException();
                foreach(string key in fields.Keys)if(key!="version"&&key!="enabled"&&key!="rewardedUnitId"&&key!="privacyUrl"&&key!="privacyVersion"&&(version!=2||key!="interstitialUnitId"))throw new FormatException();
                var value=new RewardedAdsConfiguration85{version=version,enabled=SocialJson82.Flag(fields,"enabled"),rewardedUnitId=SocialJson82.Text(fields,"rewardedUnitId",64,true),
                    interstitialUnitId=version==2?SocialJson82.Text(fields,"interstitialUnitId",64):"",privacyUrl=SocialJson82.Text(fields,"privacyUrl",500,true),privacyVersion=SocialJson82.Text(fields,"privacyVersion",64)};
                if(!Regex.IsMatch(value.privacyVersion,@"\A[A-Za-z0-9_.-]{1,64}\z")||!Unit(value.rewardedUnitId)&&!(version==1&&!value.enabled&&value.rewardedUnitId==""))throw new FormatException();
                if(version==2&&!Unit(value.interstitialUnitId)||value.privacyUrl!=""&&!Privacy(value.privacyUrl)||value.enabled&&!Privacy(value.privacyUrl))throw new FormatException();
                return value;
            }catch(Exception){throw new FormatException(AdvertisingConfiguration107.InvalidError);}
        }
        public static RewardedAdsConfiguration85 ParseLegacyOrV2(string json)=>Parse(json,true);
        public static bool TryParsePackaged(string json,out RewardedAdsConfiguration85 value,out string error){
            value=null;error=null;try{value=Parse(json,false);return true;}catch(Exception){error=AdvertisingConfiguration107.InvalidError;return false;}
        }
        public static string CanonicalPackagedJson(RewardedAdsConfiguration85 value){
            if(value==null)throw new FormatException(AdvertisingConfiguration107.InvalidError);
            return JsonUtility.ToJson(Parse(JsonUtility.ToJson(value),false));
        }
        public static bool TryRead(out RewardedAdsConfiguration85 value){
            string error;return TryRead(out value,out error);
        }
        public static bool TryRead(out RewardedAdsConfiguration85 value,out string error){
            var packaged=AdvertisingConfiguration107.ReadPackaged();var persistent=packaged.present?AdvertisingConfigurationInput107.Absent:AdvertisingConfiguration107.ReadFile(FilePath);
            string source;if(!AdvertisingConfiguration107.Select(packaged,persistent,out value,out error,out source))return false;
            if(!value.enabled){value=null;error="AdsDisabled";return false;}return true;
        }
    }
}

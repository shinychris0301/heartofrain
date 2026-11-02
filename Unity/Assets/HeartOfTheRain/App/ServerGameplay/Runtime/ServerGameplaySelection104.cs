using System;
using UnityEngine;

namespace HeartOfTheRain.App.ServerGameplay {
    // Only public, non-secret connection metadata belongs in this resource.
    // The build guard owns temporary delivery; this file ships no active host.
    public static class ServerStagingConfiguration104 {
        public const string ResourceKey="HOTR_Server/ManagedStaging";
        public const string ResourceAssetPath="Assets/HeartOfTheRain/Resources/HOTR_Server/ManagedStaging.json";
        public const string PackageName="com.heartoftherain.stagingreview";
        public const string InvalidError="ExplicitServerConfigurationInvalid";
        static ServerGameplayConfiguration ParsePackaged(string json){
            var value=ServerGameplayConfiguration.Parse(json);var origin=new Uri(value.origin);
            if(value.allowDevelopmentLoopback||origin.Scheme!="https"||origin.IsLoopback||origin.HostNameType!=UriHostNameType.Dns)throw new FormatException(InvalidError);
            return value;
        }
        public static bool TryParsePackaged(string json,out ServerGameplayConfiguration config,out string error){
            config=null;error=null;try{config=ParsePackaged(json);return true;}catch(Exception){error=InvalidError;return false;}
        }
        public static string CanonicalJson(ServerGameplayConfiguration config){
            if(config==null)throw new FormatException(InvalidError);
            return JsonUtility.ToJson(ParsePackaged(JsonUtility.ToJson(config)));
        }
    }
    public sealed class ServerConfigurationInput104 {
        public readonly bool present,failed;public readonly string json;
        public ServerConfigurationInput104(bool present,string json=null,bool failed=false){this.present=present;this.json=json;this.failed=failed;}
        public static ServerConfigurationInput104 Absent=>new ServerConfigurationInput104(false);
        public static ServerConfigurationInput104 Invalid=>new ServerConfigurationInput104(true,null,true);
    }
    // Pure selection: callers supply observations; no Resources, filesystem,
    // network, credential store or profile factory is accessed here.
    public static class ServerGameplaySelection104 {
        public static bool Resolve(bool editor,bool development,string packageName,bool explicitOverride,ServerConfigurationInput104 external,ServerConfigurationInput104 packaged,ServerConfigurationInput104 persistent,out ServerGameplayConfiguration config,out string error,out string source){
            config=null;error=null;source="None";ServerConfigurationInput104 selected;bool requirePackaged=false;
            if(editor&&explicitOverride){selected=external;source="External";}
            else if(packaged!=null&&packaged.present||!editor&&packageName==ServerStagingConfiguration104.PackageName){selected=packaged;source="Packaged";requirePackaged=true;}
            else if(explicitOverride){selected=external;source="External";}
            else{selected=persistent;if(selected==null||!selected.present)return false;source="Persistent";}
            if(selected==null||!selected.present||selected.failed){error=ServerStagingConfiguration104.InvalidError;return true;}
            if(requirePackaged){
                if(packageName!=ServerStagingConfiguration104.PackageName||!editor&&!development){error=ServerStagingConfiguration104.InvalidError;return true;}
                ServerStagingConfiguration104.TryParsePackaged(selected.json,out config,out error);return true;
            }
            try{config=ServerGameplayConfiguration.Parse(selected.json);}catch(Exception){error=ServerStagingConfiguration104.InvalidError;}return true;
        }
    }
}

using System;
using System.Collections;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;
using UnityEngine.Networking;
using HeartOfTheRain.App.RuStore;

namespace HeartOfTheRain.App.OnlineIdentity {
    [Serializable] public sealed class ProviderStatus89 {
        public string playerId,provider,phase,flowId,requestId,authorizeUrl;
        public bool available,linked,samePlayer;
        public long linkedAt,expiresAt,serverUtc;
        public bool Pending=>phase=="Pending"||phase=="Exchanging";
        public ProviderStatus89 Copy()=>(ProviderStatus89)MemberwiseClone();
    }
    // Only the app's authenticated backend receives game credentials. VK's
    // browser code exchange and user_info verification stay on the backend.
    public sealed class ProviderIdentityClient89:IDisposable {
        const int Limit=32768;static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
        readonly string origin,player;readonly Func<string> access;readonly Action<IEnumerator> dispatch;
        bool disposed,busy;UnityWebRequest active;
        [Serializable] sealed class Command {public string requestId;}
        sealed class Download:DownloadHandlerScript {
            readonly byte[] bytes=new byte[Limit];int count;public bool exceeded;
            public Download():base(new byte[4096]){}
            protected override void ReceiveContentLengthHeader(ulong length){if(length>Limit)exceeded=true;}
            protected override bool ReceiveData(byte[] data,int length){if(exceeded||data==null||length<0||length>Limit-count){exceeded=true;return false;}Buffer.BlockCopy(data,0,bytes,count,length);count+=length;return true;}
            public string Text(){if(exceeded||count<1)throw new InvalidOperationException();return Utf8.GetString(bytes,0,count);}
        }
        public ProviderIdentityClient89(string backendOrigin,string playerId,Func<string> token,Action<IEnumerator> dispatcher,bool developmentLoopback=false){
            if(!RuStoreBackendClient.IsAllowedOrigin(backendOrigin,developmentLoopback)||!IdentityProtocol82.Id(playerId)||token==null||dispatcher==null)throw new ArgumentException("ProviderSessionInvalid");
            origin=new Uri(backendOrigin).GetLeftPart(UriPartial.Authority);player=playerId;access=token;dispatch=dispatcher;
        }
        public static bool SafeAuthorizeUrl(string value){
            Uri uri;return !string.IsNullOrEmpty(value)&&value==value.Trim()&&!Regex.IsMatch(value,@"[\x00-\x20\x7f]")&&value.Length<=4096&&Uri.TryCreate(value,UriKind.Absolute,out uri)&&uri.Scheme=="https"&&(uri.Host=="id.vk.ru"||uri.Host=="id.vk.com")&&uri.Port==443&&uri.AbsolutePath=="/authorize"&&uri.UserInfo==""&&uri.Fragment=="";
        }
        static void Flag(string json,string name){if(Regex.Matches(json,"(?<!\\\\)\""+Regex.Escape(name)+"\"\\s*:").Count!=1||!Regex.IsMatch(json,"\""+Regex.Escape(name)+"\"\\s*:\\s*(true|false)(?=\\s*[,}])"))throw new InvalidOperationException();}
        public static ProviderStatus89 ParseStatus(string text,string expectedPlayer){
            if(string.IsNullOrEmpty(text)||Utf8.GetByteCount(text)>Limit||!IdentityProtocol82.Id(expectedPlayer))throw new InvalidOperationException("ProviderResponseInvalid");
            foreach(string flag in new[]{"available","linked","samePlayer"})Flag(text,flag);
            var value=JsonUtility.FromJson<ProviderStatus89>(text);
            if(value==null||value.playerId!=expectedPlayer||value.provider!="vk"||!value.samePlayer||value.serverUtc<=0||Array.IndexOf(new[]{"Idle","Pending","Exchanging","Linked","Cancelled","Expired","Failed","Conflict"},value.phase)<0
                ||(!string.IsNullOrEmpty(value.flowId)&&(!IdentityProtocol82.Id(value.flowId)||!IdentityProtocol82.Id(value.requestId)))
                ||(value.Pending&&(!IdentityProtocol82.Id(value.flowId)||value.expiresAt<=value.serverUtc))
                ||(value.linked&&(value.linkedAt<=0||value.linkedAt>value.serverUtc))
                ||(!string.IsNullOrEmpty(value.authorizeUrl)&&!SafeAuthorizeUrl(value.authorizeUrl)))throw new InvalidOperationException("ProviderResponseInvalid");
            return value;
        }
        public void Status(Action<ProviderStatus89,string> done)=>Send("GET","/v1/identity/vk/status",null,done);
        public void Begin(string requestId,Action<ProviderStatus89,string> done){if(!IdentityProtocol82.Id(requestId)){done(null,"ProviderIntentInvalid");return;}Send("POST","/v1/identity/vk/link",JsonUtility.ToJson(new Command{requestId=requestId}),done);}
        public void Cancel(string flowId,Action<ProviderStatus89,string> done){if(!IdentityProtocol82.Id(flowId)){done(null,"ProviderIntentInvalid");return;}Send("POST","/v1/identity/vk/flows/"+flowId+"/cancel",null,done);}
        void Send(string method,string path,string json,Action<ProviderStatus89,string> done){
            if(done==null)throw new ArgumentNullException(nameof(done));if(disposed||busy){done(null,"ProviderUnavailable");return;}busy=true;
            try{dispatch(Exchange(method,path,json,done));}catch(Exception){busy=false;done(null,"ProviderUnavailable");}
        }
        IEnumerator Exchange(string method,string path,string json,Action<ProviderStatus89,string> done){
            ProviderStatus89 result=null;string error=null;UnityWebRequestAsyncOperation operation=null;Download download=null;
            try{
                try{
                    string token=access();if(disposed||!IdentityProtocol82.Secret(token))throw new InvalidOperationException();
                    active=new UnityWebRequest(origin+path,method);active.redirectLimit=0;active.timeout=15;download=new Download();active.downloadHandler=download;
                    if(json!=null){active.uploadHandler=new UploadHandlerRaw(Utf8.GetBytes(json));active.SetRequestHeader("Content-Type","application/json");}
                    active.SetRequestHeader("Accept","application/json");active.SetRequestHeader("Authorization","Bearer "+token);operation=active.SendWebRequest();
                }catch(Exception){error="ProviderUnavailable";}
                if(operation!=null){yield return operation;
                    try{
                        string type=active.GetResponseHeader("Content-Type");
                        if(disposed||string.IsNullOrEmpty(access()))error="ProviderSessionChanged";
                        else if(download.exceeded)error="ProviderResponseTooLarge";
                        else if(active.result!=UnityWebRequest.Result.Success||active.responseCode!=200)error="ProviderRequestFailed";
                        else if(type==null||!type.Split(';')[0].Trim().Equals("application/json",StringComparison.OrdinalIgnoreCase))error="ProviderResponseInvalid";
                        else{
                            result=ParseStatus(download.Text(),player);
                        }
                    }catch(Exception){error="ProviderResponseInvalid";}
                }
            }finally{active?.Dispose();active=null;busy=false;try{done(disposed?null:result,disposed?"ProviderSessionChanged":error);}catch(Exception){}}
        }
        public void Dispose(){if(disposed)return;disposed=true;try{active?.Abort();}catch(Exception){}}
    }
}

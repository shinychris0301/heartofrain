using System;
using System.Collections;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;
using UnityEngine.Networking;
using HeartOfTheRain.App.RuStore;

namespace HeartOfTheRain.App.OnlineIdentity {
    public sealed class VkSigninClient102:IDisposable {
        const int Limit=32768;static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
        readonly string origin,player;readonly Func<string> access;readonly Action<IEnumerator> dispatch;
        bool disposed,busy;UnityWebRequest active;
        [Serializable] sealed class BeginBody {public string requestId,publicKey,completionDigest;}
        sealed class Download:DownloadHandlerScript {
            readonly byte[] bytes=new byte[Limit];int count;public bool exceeded;
            public Download():base(new byte[4096]){}
            protected override void ReceiveContentLengthHeader(ulong length){if(length>Limit)exceeded=true;}
            protected override bool ReceiveData(byte[] data,int length){if(exceeded||data==null||length<0||length>Limit-count){exceeded=true;return false;}Buffer.BlockCopy(data,0,bytes,count,length);count+=length;return true;}
            public string Text(){if(exceeded||count<1)throw new InvalidOperationException();return Utf8.GetString(bytes,0,count);}
        }
        public VkSigninClient102(string backendOrigin,string playerId,Func<string> token,Action<IEnumerator> dispatcher,bool developmentLoopback=false){
            if(!RuStoreBackendClient.IsAllowedOrigin(backendOrigin,developmentLoopback)||!IdentityProtocol82.Id(playerId)||token==null||dispatcher==null)throw new ArgumentException("VkSigninSessionInvalid");
            origin=new Uri(backendOrigin).GetLeftPart(UriPartial.Authority);player=playerId;access=token;dispatch=dispatcher;
        }
        static void Flag(string text,string name){
            if(Regex.Matches(text,"(?<!\\\\)\""+Regex.Escape(name)+"\"\\s*:").Count!=1||!Regex.IsMatch(text,"\""+Regex.Escape(name)+"\"\\s*:\\s*(true|false)(?=\\s*[,}])"))throw new InvalidOperationException("VkSigninFlagInvalid");
        }
        public static VkSigninStatus102 Parse(string text,string expectedPlayer,string expectedFlow){
            if(string.IsNullOrEmpty(text)||Utf8.GetByteCount(text)>Limit||!IdentityProtocol82.Id(expectedPlayer)||!IdentityProtocol82.Id(expectedFlow))throw new InvalidOperationException("VkSigninResponseInvalid");
            Flag(text,"available");Flag(text,"requiresConfirmation");var value=JsonUtility.FromJson<VkSigninStatus102>(text);
            if(value==null||value.playerId!=expectedPlayer||value.provider!="vk"||value.flowId!=expectedFlow||value.requestId!=expectedFlow||value.serverUtc<=0
                ||Array.IndexOf(new[]{"Pending","Exchanging","Ready","Completed","Cancelled","Expired","Failed","Conflict"},value.phase)<0
                ||(value.Pending||value.phase=="Ready")&&value.expiresAt<=value.serverUtc
                ||(value.phase=="Ready"||value.phase=="Completed")&&!IdentityProtocol82.Id(value.targetPlayerId)
                ||value.phase!="Ready"&&value.phase!="Completed"&&!string.IsNullOrEmpty(value.targetPlayerId)
                ||value.phase!="Ready"&&value.phase!="Completed"&&value.requiresConfirmation
                ||(value.phase=="Ready"||value.phase=="Completed")&&value.requiresConfirmation!=(value.targetPlayerId!=expectedPlayer)
                ||!string.IsNullOrEmpty(value.authorizeUrl)&&(!ProviderIdentityClient89.SafeAuthorizeUrl(value.authorizeUrl)||value.phase!="Pending"))
                throw new InvalidOperationException("VkSigninResponseInvalid");
            return value;
        }
        public void Begin(string flow,string publicKey,string proofDigest,Action<VkSigninStatus102,string> done){
            if(!IdentityProtocol82.Id(flow)||!IdentityProtocol82.PublicKey(publicKey)||!IdentityProtocol82.Digest(proofDigest)){done(null,"VkSigninIntentInvalid");return;}
            Send("POST","/v1/identity/vk/signin",flow,JsonUtility.ToJson(new BeginBody{requestId=flow,publicKey=publicKey,completionDigest=proofDigest}),done);
        }
        public void Status(string flow,Action<VkSigninStatus102,string> done){if(!IdentityProtocol82.Id(flow)){done(null,"VkSigninIntentInvalid");return;}Send("GET","/v1/identity/vk/signin/"+flow,flow,null,done);}
        public void Cancel(string flow,Action<VkSigninStatus102,string> done){if(!IdentityProtocol82.Id(flow)){done(null,"VkSigninIntentInvalid");return;}Send("POST","/v1/identity/vk/signin/"+flow+"/cancel",flow,null,done);}
        void Send(string method,string path,string flow,string json,Action<VkSigninStatus102,string> done){
            if(done==null)throw new ArgumentNullException(nameof(done));if(disposed||busy){done(null,"VkSigninUnavailable");return;}busy=true;
            try{dispatch(Exchange(method,path,flow,json,done));}catch(Exception){busy=false;done(null,"VkSigninUnavailable");}
        }
        IEnumerator Exchange(string method,string path,string flow,string json,Action<VkSigninStatus102,string> done){
            VkSigninStatus102 result=null;string error=null;UnityWebRequestAsyncOperation operation=null;Download download=null;
            try{
                try{string token=access();if(disposed||!IdentityProtocol82.Secret(token))throw new InvalidOperationException();
                    active=new UnityWebRequest(origin+path,method);active.redirectLimit=0;active.timeout=15;download=new Download();active.downloadHandler=download;
                    if(json!=null){active.uploadHandler=new UploadHandlerRaw(Utf8.GetBytes(json));active.SetRequestHeader("Content-Type","application/json");}
                    active.SetRequestHeader("Accept","application/json");active.SetRequestHeader("Authorization","Bearer "+token);operation=active.SendWebRequest();
                }catch(Exception){error="VkSigninUnavailable";}
                if(operation!=null){yield return operation;
                    try{string type=active.GetResponseHeader("Content-Type");
                        if(disposed||string.IsNullOrEmpty(access()))error="VkSigninSessionChanged";
                        else if(download.exceeded)error="VkSigninResponseTooLarge";
                        else if(active.result!=UnityWebRequest.Result.Success||active.responseCode!=200){NetworkFailureLog.Report("vk",active);error=active.responseCode>0?"VkSigninHttp"+active.responseCode:"VkSigninRequestFailed";}
                        else if(type==null||!type.Split(';')[0].Trim().Equals("application/json",StringComparison.OrdinalIgnoreCase))error="VkSigninResponseInvalid";
                        else result=Parse(download.Text(),player,flow);
                    }catch(Exception){error="VkSigninResponseInvalid";}
                }
            }finally{active?.Dispose();active=null;busy=false;try{done(disposed?null:result,disposed?"VkSigninSessionChanged":error);}catch(Exception){}}
        }
        public void Dispose(){if(disposed)return;disposed=true;try{active?.Abort();}catch(Exception){}}
    }
}

using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.RuStore;

namespace HeartOfTheRain.App.ServerGameplay {
    // One explicitly owned, bounded asynchronous transport. It has no factory,
    // financial model mutation, verifier credential or local success fallback.
    public sealed class ServerGameplayBrokerClient:IServerGameplayBroker,IDisposable {
        readonly string origin,player;readonly bool expectedProduction;readonly Func<string> access;readonly Action<IEnumerator> dispatch;readonly int owner=System.Threading.Thread.CurrentThread.ManagedThreadId;
        long generation;bool closed,busy;UnityWebRequest active;const int Limit=65536;
        sealed class Download:DownloadHandlerScript {
            readonly byte[] bytes=new byte[Limit];int count;public bool exceeded;
            public Download():base(new byte[8192]){}
            protected override void ReceiveContentLengthHeader(ulong size){if(size>Limit)exceeded=true;}
            protected override bool ReceiveData(byte[] data,int size){if(exceeded||data==null||size<0||size>Limit-count){exceeded=true;return false;}Buffer.BlockCopy(data,0,bytes,count,size);count+=size;return true;}
            public string Text(){if(exceeded||count<1)throw new FormatException();return new UTF8Encoding(false,true).GetString(bytes,0,count);}
        }
        public ServerGameplayBrokerClient(string origin,string player,Func<string> currentAccess,Action<IEnumerator> dispatcher,bool allowLoopback=false,bool expectedProduction=false){
            if(expectedProduction&&allowLoopback)throw new ArgumentException("ProductionLoopbackRejected");this.expectedProduction=expectedProduction;
            if(!RuStoreBackendClient.IsAllowedOrigin(origin,allowLoopback)||!IdentityProtocol82.Id(player)||currentAccess==null||dispatcher==null)throw new ArgumentException("ExplicitBrokerConfigurationRequired");
            this.origin=new Uri(origin).GetLeftPart(UriPartial.Authority);this.player=player;access=currentAccess;dispatch=dispatcher;
        }
        static void Need(bool valid){if(!valid)throw new FormatException();}
        static void Four(Dictionary<string,object> row,string key){var values=SocialJson82.Array(row,key,4);Need(values.Count==4&&values.All(v=>v is long&&(long)v>=0&&(long)v<=int.MaxValue));}
        static void Attempt(Dictionary<string,object> value){
            Need(IdentityProtocol82.Id(SocialJson82.Text(value,"attemptId",32))&&IdentityProtocol82.Digest(SocialJson82.Text(value,"configHash",64)));
            SocialJson82.Number(value,"level",1,50);SocialJson82.Number(value,"seed",1,uint.MaxValue);SocialJson82.Number(value,"moves",1,int.MaxValue);SocialJson82.Number(value,"continues",0,int.MaxValue);Four(value,"starting");
            Need(SocialJson82.Array(value,"starting",4).All(v=>(long)v<=1));
            Need(new[]{"Reserved","Started","AwaitingContinuation","Won","Lost","Released","Cancelled"}.Contains(SocialJson82.Text(value,"state",32)));
        }
        static void Wallet(Dictionary<string,object> value,string player,bool expectedProduction){
            Need(SocialJson82.Text(value,"playerId",32)==player&&SocialJson82.Text(value,"balanceScope",32)=="server_wallet");
            Need(SocialJson82.Flag(value,"productionEnabled")==expectedProduction&&!SocialJson82.Flag(value,"normalUnityProfileIntegrated")&&!SocialJson82.Flag(value,"localProfileMutated"));
            SocialJson82.Flag(value,"initialized");SocialJson82.Flag(value,"refundReviewRequired");SocialJson82.Number(value,"revision");SocialJson82.Number(value,"coins",0,int.MaxValue);SocialJson82.Number(value,"stars",0,int.MaxValue);
            SocialJson82.Number(value,"lives",0,5);SocialJson82.Number(value,"maxLives",5,5);long completed=SocialJson82.Number(value,"completed",0,50);Need(SocialJson82.Number(value,"currentLevel",1,50)==Math.Min(50,completed+1));
            SocialJson82.Number(value,"serverUtc",1);SocialJson82.Number(value,"nextLifeAt");Four(value,"starting");Four(value,"tools");
            object active=SocialJson82.Field(value,"activeAttempt");if(active!=null)Attempt(SocialJson82.Object(active));
        }
        ServerBrokerOperation Parse(string json,string attempt,string command){
            var raw=SocialJson82.Read(json);Need(SocialJson82.Text(raw,"operationId",32)==command&&SocialJson82.Text(raw,"attemptId",32)==attempt&&SocialJson82.Flag(raw,"productionEnabled")==expectedProduction);
            string state=SocialJson82.Text(raw,"state",16);Need(new[]{"Committed","Pending","Rejected"}.Contains(state));
            SocialJson82.Text(raw,"code",128,true);SocialJson82.Flag(raw,"acknowledgementRequired");
            SocialJson82.Number(raw,"prefixRevision",0,int.MaxValue);SocialJson82.Number(raw,"acceptedActions",0,1000);long added=SocialJson82.Number(raw,"addedMoves",0,5);Need(added==0||added==5);
            var value=JsonUtility.FromJson<ServerBrokerOperation>(json);object model=SocialJson82.Field(raw,"model"),wallet=SocialJson82.Field(raw,"wallet"),record=SocialJson82.Field(raw,"attempt"),receipt=SocialJson82.Field(raw,"displayReceipt");
            string paid=SocialJson82.Text(raw,"paidReceiptId",128,true);Need(paid==""||System.Text.RegularExpressions.Regex.IsMatch(paid,@"\Awallet/[0-9a-f]{64}\z"));
            if(model==null)value.model=null;else{var row=SocialJson82.Object(model);Need(new[]{"Playing","Won","Out of moves","No legal moves"}.Contains(SocialJson82.Text(row,"outcome",32))&&IdentityProtocol82.Digest(SocialJson82.Text(row,"checkpointSHA256",64)));SocialJson82.Number(row,"moves",0,int.MaxValue);SocialJson82.Number(row,"turn",0,int.MaxValue);}
            if(wallet==null)value.wallet=null;else{var row=SocialJson82.Object(wallet);Wallet(row,player,expectedProduction);if(SocialJson82.Field(row,"activeAttempt")==null)value.wallet.activeAttempt=null;}
            if(record==null)value.attempt=null;else{Attempt(SocialJson82.Object(record));Need(value.attempt.attemptId==attempt);}
            if(receipt==null)value.displayReceipt=null;else{var row=SocialJson82.Object(receipt);Need(new[]{"Won","OutOfMoves","Lost","Fault"}.Contains(SocialJson82.Text(row,"outcome",16)));SocialJson82.Text(row,"receiptId",128);SocialJson82.Number(row,"awardedCoins",0,int.MaxValue);SocialJson82.Number(row,"awardedStars",0,int.MaxValue);SocialJson82.Number(row,"completedBefore",0,50);SocialJson82.Number(row,"completedAfter",0,50);SocialJson82.Number(row,"livesAfter",0,5);SocialJson82.Flag(row,"firstClear");}
            if(state=="Committed"){
                Need(value.wallet!=null&&value.attempt!=null);
                if(value.displayReceipt?.outcome=="Fault")Need(value.model==null&&value.attempt.state=="Released"&&paid==""&&added==0&&value.displayReceipt.awardedCoins==0&&value.displayReceipt.awardedStars==0);
                else Need(value.model!=null);
            }return value;
        }
        static void Deliver(Action<ServerGameReply<ServerBrokerOperation>> done,ServerGameReply<ServerBrokerOperation> value){try{done(value);}catch(Exception){}}
        void Send(string method,string attempt,string command,string suffix,object body,Action<ServerGameReply<ServerBrokerOperation>> done){
            if(done==null)throw new ArgumentNullException(nameof(done));
            if(closed||busy||owner!=System.Threading.Thread.CurrentThread.ManagedThreadId||!IdentityProtocol82.Id(attempt)||!IdentityProtocol82.Id(command)){Deliver(done,ServerGameReply<ServerBrokerOperation>.Fail("BrokerUnavailable"));return;}
            string bearer=access();if(!IdentityProtocol82.Secret(bearer)){Deliver(done,ServerGameReply<ServerBrokerOperation>.Fail("ManagedAccessRequired"));return;}
            string json=body==null?null:JsonUtility.ToJson(body);if(json!=null&&Encoding.UTF8.GetByteCount(json)>Limit){Deliver(done,ServerGameReply<ServerBrokerOperation>.Fail("BrokerRequestTooLarge"));return;}
            busy=true;long token=++generation;try{dispatch(Exchange(method,attempt,command,suffix,json,bearer,token,done));}catch(Exception){busy=false;Deliver(done,ServerGameReply<ServerBrokerOperation>.Fail("BrokerDispatchUnavailable",true));}
        }
        IEnumerator Exchange(string method,string attempt,string command,string suffix,string json,string bearer,long token,Action<ServerGameReply<ServerBrokerOperation>> done){
            UnityWebRequest request=null;Download download=null;UnityWebRequestAsyncOperation sent=null;ServerGameReply<ServerBrokerOperation> reply=null;
            try{
                try{request=new UnityWebRequest(origin+"/v1/gameplay/attempts/"+attempt+suffix,method);active=request;download=new Download();request.downloadHandler=download;request.redirectLimit=0;request.timeout=40;
                    request.SetRequestHeader("Authorization","Bearer "+bearer);request.SetRequestHeader("Accept","application/json");if(json!=null){request.SetRequestHeader("Content-Type","application/json");request.uploadHandler=new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));}sent=request.SendWebRequest();}
                catch(Exception){reply=ServerGameReply<ServerBrokerOperation>.Fail("BrokerRequestUnavailable",true);}
                if(sent!=null){yield return sent;try{
                    if(closed||token!=generation||access()!=bearer)reply=ServerGameReply<ServerBrokerOperation>.Fail("BrokerIdentityChanged",true);
                    else if(download.exceeded)reply=ServerGameReply<ServerBrokerOperation>.Fail("BrokerResponseTooLarge",true);
                    else if(request.result!=UnityWebRequest.Result.Success||(request.responseCode!=200&&request.responseCode!=202)){NetworkFailureLog.Report("broker",request);reply=ServerGameReply<ServerBrokerOperation>.Fail("BrokerHttp"+request.responseCode,true);}
                    else if((request.GetResponseHeader("Content-Type")??"").Split(';')[0].Trim()!="application/json")reply=ServerGameReply<ServerBrokerOperation>.Fail("BrokerContentTypeInvalid",true);
                    else reply=ServerGameReply<ServerBrokerOperation>.Ok(Parse(download.Text(),attempt,command));
                }catch(Exception){reply=ServerGameReply<ServerBrokerOperation>.Fail("BrokerBoundResponseInvalid",true);}}
            }finally{request?.Dispose();if(active==request)active=null;if(token==generation)busy=false;if(reply==null)reply=ServerGameReply<ServerBrokerOperation>.Fail("BrokerRequestStopped",true);Deliver(done,reply);}
        }
        public void Verify(string attempt,ServerVerifyRequest request,Action<ServerGameReply<ServerBrokerOperation>> done)=>Send("POST",attempt,request.commandId,"/verify",request,done);
        public void Tool(string attempt,ServerToolRequest request,Action<ServerGameReply<ServerBrokerOperation>> done)=>Send("POST",attempt,request.commandId,"/tool",request,done);
        public void Continue(string attempt,ServerContinueRequest request,Action<ServerGameReply<ServerBrokerOperation>> done)=>Send("POST",attempt,request.commandId,"/continue",request,done);
        public void Operation(string attempt,string command,bool resume,Action<ServerGameReply<ServerBrokerOperation>> done)=>Send(resume?"POST":"GET",attempt,command,"/operations/"+command+(resume?"/resume":""),resume?(object)new Empty():null,done);
        [Serializable] sealed class Empty{}
        public void Cancel(){generation++;busy=false;try{active?.Abort();}catch(Exception){}}
        public void Dispose(){if(closed)return;Cancel();closed=true;}
    }
}

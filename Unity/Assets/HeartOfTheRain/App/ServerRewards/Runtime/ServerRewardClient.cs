using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.RuStore;

namespace HeartOfTheRain.App.ServerRewards {
    // Explicit managed-session transport: bounded bytes, no redirects, and live
    // account/generation access is checked both before and after every request.
    public sealed class ServerRewardClient {
        readonly RewardAccess owner;const int Limit=65536;
        sealed class Download:DownloadHandlerScript {
            readonly byte[] bytes=new byte[Limit];int count;public bool exceeded;
            public Download():base(new byte[8192]){}
            protected override void ReceiveContentLengthHeader(ulong size){if(size>Limit)exceeded=true;}
            protected override bool ReceiveData(byte[] data,int size){if(exceeded||data==null||size<0||size>Limit-count){exceeded=true;return false;}Buffer.BlockCopy(data,0,bytes,count,size);count+=size;return true;}
            public string Text(){if(exceeded||count<1)throw new FormatException();return new UTF8Encoding(false,true).GetString(bytes,0,count);}
        }
        public ServerRewardClient(RewardAccess owner){this.owner=owner??throw new ArgumentNullException(nameof(owner));if(!RuStoreBackendClient.IsAllowedOrigin(owner.Origin,owner.AllowLoopback)||!IdentityProtocol82.Id(owner.PlayerId))throw new ArgumentException("ExplicitRewardSessionRequired");}
        static void Need(bool test){if(!test)throw new FormatException();}
        static void Grant(Dictionary<string,object> row){SocialJson82.Number(row,"coins",0,int.MaxValue);SocialJson82.Number(row,"stars",0,int.MaxValue);foreach(string key in new[]{"starting","tools"}){var values=SocialJson82.Array(row,key,4);Need(values.Count==4&&values.All(n=>n is long&&(long)n>=0&&(long)n<=int.MaxValue));}}
        static void Rules(Dictionary<string,object> row){SocialJson82.Text(row,"version",128);SocialJson82.Number(row,"unlockClears",0,49);SocialJson82.Number(row,"durationSeconds",1,2592000);var rivals=SocialJson82.Array(row,"rivalFinalScores",4);Need(rivals.Count==4&&rivals.All(n=>n is long&&(long)n>=0&&(long)n<=50));var grants=SocialJson82.Array(row,"rankRewards",5);Need(grants.Count==5);foreach(var g in grants){var r=SocialJson82.Object(g);Grant(r);Need(SocialJson82.Number(r,"stars")==0);}}
        public static BackendOffer ParseOffer(string json){var row=SocialJson82.Read(json);Need(SocialJson82.Text(row,"id",256).StartsWith("server-daily/",StringComparison.Ordinal));SocialJson82.Text(row,"schedule",128);SocialJson82.Number(row,"day",0,2932896);SocialJson82.Number(row,"step",0,6);SocialJson82.Flag(row,"claimed");Grant(SocialJson82.Object(SocialJson82.Field(row,"grant")));return JsonUtility.FromJson<BackendOffer>(json);}
        public static ServerWellworks ParseWellworks(string json){var row=SocialJson82.Read(json);long completed=SocialJson82.Number(row,"completed",0,50);var milestones=SocialJson82.Array(row,"milestones",50);Need(milestones.Count>0);long previous=0;foreach(var value in milestones){var m=SocialJson82.Object(value);long level=SocialJson82.Number(m,"level",1,50);Need(level>previous&&SocialJson82.Flag(m,"eligible")== (completed>=level));previous=level;SocialJson82.Flag(m,"claimed");var grant=SocialJson82.Object(SocialJson82.Field(m,"grant"));Grant(grant);Need(SocialJson82.Number(grant,"stars")==0);}return JsonUtility.FromJson<ServerWellworks>(json);}
        public static ServerCup ParseCup(string json){var row=SocialJson82.Read(json);string state=SocialJson82.Text(row,"state",16);Need(new[]{"Locked","Ready","Exhausted","Active","Finished","Claimed"}.Contains(state));SocialJson82.Number(row,"completed",0,50);Need(SocialJson82.Flag(row,"practice")&&SocialJson82.Flag(row,"simulatedRivals")&&!SocialJson82.Flag(row,"realCompetition"));SocialJson82.Flag(row,"canJoin");long now=SocialJson82.Number(row,"serverUtc",1,253402300799);var rules=SocialJson82.Object(SocialJson82.Field(row,"rules"));Rules(rules);bool hasRun=row.TryGetValue("run",out var run)&&run!=null;Need(hasRun==(state=="Active"||state=="Finished"||state=="Claimed"));if(hasRun){var r=SocialJson82.Object(run);Need(IdentityProtocol82.Id(SocialJson82.Text(r,"id",32)));long joined=SocialJson82.Number(r,"joinedAt",1,now),end=SocialJson82.Number(r,"endsAt",joined+1,253402300799);Need(end-joined==SocialJson82.Number(rules,"durationSeconds"));SocialJson82.Number(r,"points",0,50);long rank=SocialJson82.Number(r,"finalRank",0,5);Need(state=="Active"?rank==0:rank>=1);var scores=SocialJson82.Array(r,"rivalScores",4);Need(scores.Count==4&&scores.All(n=>n is long&&(long)n>=0&&(long)n<=50));}var dto=JsonUtility.FromJson<ServerCup>(json);if(!hasRun)dto.run=null;dto.rules.Validate();return dto;}
        static ServerRewardReceipt Receipt(string json,string source){var row=SocialJson82.Read(json);Need(SocialJson82.Text(row,"source",32)==source);SocialJson82.Text(row,"id",256);Grant(SocialJson82.Object(SocialJson82.Field(row,"grant")));Need(SocialJson82.Number(SocialJson82.Object(SocialJson82.Field(row,"grant")),"stars")==0);SocialJson82.Number(row,"serverUtc",1,253402300799);SocialJson82.Number(row,"cursor",1);return JsonUtility.FromJson<ServerRewardReceipt>(json);}
        public static BackendDecision ParseDaily(string json,string player,PendingGift request){var r=SocialJson82.Read(json);Need(SocialJson82.Text(r,"playerId",32)==player&&SocialJson82.Text(r,"receiptId",256)==request.offerId&&SocialJson82.Text(r,"requestId",32)==request.requestId&&SocialJson82.Text(r,"schedule",128)==request.schedule&&SocialJson82.Number(r,"day")==request.day&&SocialJson82.Number(r,"step",0,6)==request.step);Grant(SocialJson82.Object(SocialJson82.Field(r,"grant")));var d=JsonUtility.FromJson<BackendDecision>(json);Need(JsonUtility.ToJson(d.grant)==JsonUtility.ToJson(request.expectedGrant));return d;}
        public IEnumerator Offer(Action<RewardReply<BackendOffer>> done)=>Send("GET","/v1/daily-gift/offer",null,ParseOffer,done);
        public IEnumerator Wellworks(Action<RewardReply<ServerWellworks>> done)=>Send("GET","/v1/wellworks",null,ParseWellworks,done);
        public IEnumerator Cup(Action<RewardReply<ServerCup>> done)=>Send("GET","/v1/rain-cup",null,ParseCup,done);
        public IEnumerator DailyClaim(PendingGift request,Action<RewardReply<BackendDecision>> done)=>Send("POST","/v1/daily-gift/claim",JsonUtility.ToJson(request),json=>ParseDaily(json,owner.PlayerId,request),done);
        public IEnumerator WellworksClaim(RewardMilestoneClaim request,Action<RewardReply<ServerRewardReceipt>> done)=>Send("POST","/v1/wellworks/claim",JsonUtility.ToJson(request),json=>{var r=Receipt(json,"wellworks");Need(r.id=="server-wellworks/"+owner.PlayerId+"/"+request.level);return r;},done);
        public IEnumerator CupJoin(RewardJoin request,Action<RewardReply<ServerCupJoined>> done)=>Send("POST","/v1/rain-cup/join",JsonUtility.ToJson(request),json=>{var r=SocialJson82.Read(json);Need(SocialJson82.Text(r,"runId",32)==request.commandId&&SocialJson82.Flag(r,"practice"));SocialJson82.Number(r,"endsAt",1,253402300799);return JsonUtility.FromJson<ServerCupJoined>(json);},done);
        public IEnumerator CupClaim(RewardCupClaim request,Action<RewardReply<ServerRewardReceipt>> done)=>Send("POST","/v1/rain-cup/claim",JsonUtility.ToJson(request),json=>{var r=Receipt(json,"rain_cup");Need(r.id=="server-rain-cup/"+request.runId);return r;},done);
        IEnumerator Send<T>(string method,string path,string json,Func<string,T> parse,Action<RewardReply<T>> done) where T:class {
            RewardReply<T> reply=null;string bearer=owner.CurrentAccess;
            if(!IdentityProtocol82.Secret(bearer)){done(RewardReply<T>.Fail("RewardSessionChanged"));yield break;}
            UnityWebRequest request=null;Download download=null;UnityWebRequestAsyncOperation operation=null;
            try{
                try{request=new UnityWebRequest(new Uri(owner.Origin).GetLeftPart(UriPartial.Authority)+path,method);download=new Download();request.downloadHandler=download;request.timeout=15;request.redirectLimit=0;request.SetRequestHeader("Authorization","Bearer "+bearer);request.SetRequestHeader("Accept","application/json");if(json!=null){byte[] bytes=Encoding.UTF8.GetBytes(json);if(bytes.Length>8192)throw new FormatException();request.uploadHandler=new UploadHandlerRaw(bytes);request.SetRequestHeader("Content-Type","application/json");}operation=request.SendWebRequest();}catch(Exception){reply=RewardReply<T>.Fail("RewardRequestUnavailable",method!="GET");}
                // The transport timeout can be missed across an app suspend. A claim stays
                // unknown here, so its saved intent resolves against the server later.
                var stall=System.Diagnostics.Stopwatch.StartNew();
                if(operation!=null){while(!operation.isDone&&stall.Elapsed.TotalSeconds<=25)yield return null;if(!operation.isDone){request.Abort();reply=RewardReply<T>.Fail("RewardRequestStalled",method!="GET");}else try{
                    if(owner.CurrentAccess!=bearer)reply=RewardReply<T>.Fail("RewardSessionChanged",method!="GET");
                    else if(download.exceeded)reply=RewardReply<T>.Fail("RewardResponseTooLarge",method!="GET");
                    else if(request.result!=UnityWebRequest.Result.Success||request.responseCode!=200){string code="RewardHttp"+request.responseCode;if(request.responseCode>=400&&request.responseCode<500){try{var error=SocialJson82.Read(download.Text());code=SocialJson82.Text(error,"error",128);}catch(Exception){}}reply=RewardReply<T>.Fail(code,method!="GET",request.responseCode);}
                    else if((request.GetResponseHeader("Content-Type")??"").Split(';')[0].Trim()!="application/json")reply=RewardReply<T>.Fail("RewardContentTypeInvalid",method!="GET");
                    else reply=RewardReply<T>.Success(parse(download.Text()));
                }catch(Exception){reply=RewardReply<T>.Fail("RewardResponseInvalid",method!="GET");}}
            }finally{request?.Dispose();done(reply??RewardReply<T>.Fail("RewardRequestStopped",method!="GET"));}
        }
    }
}

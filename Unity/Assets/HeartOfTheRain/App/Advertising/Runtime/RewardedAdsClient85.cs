using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using UnityEngine;
using UnityEngine.Networking;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.ServerGameplay;

namespace HeartOfTheRain.App.Advertising {
    public interface IRewardedAdsApi85 {
        IEnumerator Status(ServerAuthorizedContext a,Action<AdReply85<AdStatus85>> done);
        IEnumerator Reserve(ServerAuthorizedContext a,string commandId,Action<AdReply85<AdOpportunity85>> done);
        IEnumerator Read(ServerAuthorizedContext a,string opportunityId,Action<AdReply85<AdOpportunity85>> done);
        IEnumerator Report(ServerAuthorizedContext a,string opportunityId,string commandId,Action<AdReply85<AdOpportunity85>> done);
        IEnumerator Claim(ServerAuthorizedContext a,string opportunityId,string commandId,Action<AdReply85<AdOpportunity85>> done);
        IEnumerator Cancel(ServerAuthorizedContext a,string opportunityId,string commandId,Action<AdReply85<AdOpportunity85>> done);
    }

    // Transport only. The caller owns encrypted intent recovery and any wallet
    // refresh. Neither an SDK callback nor parsing a receipt changes a balance.
    public sealed class RewardedAdsClient85:IRewardedAdsApi85,IDisposable {
        const int Limit=65536,StallSeconds=25;
        const long MaxTime=253402300799;
        const string Root="/v1/ads/rewarded",Placement="shop_rewarded",Reported="sdk_client_reported_capped",Trusted="trusted_completion";
        static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
        readonly int ownerThread=Thread.CurrentThread.ManagedThreadId;
        UnityWebRequest active;
        volatile bool disposed;
        bool busy;
        int generation;
        public bool Busy=>busy;

        sealed class Download:DownloadHandlerScript {
            readonly byte[] bytes=new byte[Limit];int count;public bool exceeded;
            public Download():base(new byte[8192]){}
            protected override void ReceiveContentLengthHeader(ulong size){if(size>Limit)exceeded=true;}
            protected override bool ReceiveData(byte[] data,int size){
                if(exceeded||data==null||size<0||size>Limit-count){exceeded=true;return false;}
                Buffer.BlockCopy(data,0,bytes,count,size);count+=size;return true;
            }
            public string Text(){if(exceeded||count<1)throw new FormatException();return Utf8.GetString(bytes,0,count);}
        }
        [Serializable] sealed class Command {public string commandId;}
        [Serializable] sealed class Reservation {public string commandId;public string placement=Placement;}
        static void Need(bool value){if(!value)throw new FormatException();}
        static bool Code(string value,int cap=64)=>value!=null&&value.Length>=1&&value.Length<=cap&&Regex.IsMatch(value,@"\A[A-Za-z0-9_.-]+\z");
        static bool Id(string value)=>IdentityProtocol82.Id(value);
        static long Number(Dictionary<string,object> row,string key,long min=0,long max=long.MaxValue)=>SocialJson82.Number(row,key,min,max);
        static string Text(Dictionary<string,object> row,string key,int cap=64)=>SocialJson82.Text(row,key,cap);
        static bool Flag(Dictionary<string,object> row,string key)=>SocialJson82.Flag(row,key);
        static long Day(long now,int offset)=>(long)Math.Floor((now+offset)/86400d);
        // Only the local zone offset is sent. Device wall-clock values never
        // participate in a quota, cooldown or claim calculation.
        public static int LocalUtcOffsetSeconds(){
            try{int value=(int)DateTimeOffset.Now.Offset.TotalSeconds;return value>=-43200&&value<=50400&&value%900==0?value:0;}
            catch{return 0;}
        }
        public static string LocalTimeZoneId(){
            try{
                string zone;
#if UNITY_ANDROID && !UNITY_EDITOR
                using(var api=new AndroidJavaClass("java.util.TimeZone"))using(var local=api.CallStatic<AndroidJavaObject>("getDefault"))zone=local.Call<string>("getID");
#else
                zone=TimeZoneInfo.Local.Id;
#endif
                return zone!=null&&zone.Length<=64&&Regex.IsMatch(zone,@"\A[A-Za-z][A-Za-z0-9_+-]*(?:/[A-Za-z0-9_+-]+){0,3}\z")?zone:"";
            }catch{return "";}
        }
        static int Offset(Dictionary<string,object> row,string key){int value=(int)Number(row,key,-43200,50400);Need(value%900==0);return value;}
        static bool IsPending(string state)=>state=="Reserved"||state=="AwaitingVerification"||state=="CompletedReported"||state=="Verified";
        static int Policy(Dictionary<string,object> row){
            Need(Text(row,"placement")==Placement&&Code(Text(row,"configVersion")));
            Number(row,"rewardCoins",400,400);Number(row,"dailyLimit",3,3);
            int offset=Offset(row,"utcOffsetSeconds");Number(row,"cooldownSeconds",600,600);return offset;
        }
        static string Mode(Dictionary<string,object> row){
            string mode=Text(row,"completionMode");Need(mode==Trusted||mode==Reported);
            string verification=Text(row,"verificationMode");Need(Code(verification));
            if(mode==Reported)Need(verification==Reported);
            return mode;
        }
        static void Opportunity(Dictionary<string,object> row,string player,string expectedId=null){
            int offset=Policy(row);string mode=Mode(row),id=Text(row,"opportunityId",32);
            Need(Id(id)&&Text(row,"playerId",32)==player&&(expectedId==null||id==expectedId));
            string state=Text(row,"state",32),source=Text(row,"completionSource");
            Need(IsPending(state)||state=="Claimed"||state=="Cancelled"||state=="Expired");
            Need(source=="none"||source==Reported||source=="provider_verified");
            Need(mode==Reported?source!="provider_verified":source!=Reported);
            long created=Number(row,"createdAt",0,MaxTime),expiry=Number(row,"expiresAt",created+1,MaxTime+3600);
            Need(expiry-created>=60&&expiry-created<=3600);
            long now=Number(row,"serverUtc",created,MaxTime),reported=Number(row,"clientReportedAt",0,now);
            long verified=Number(row,"verifiedAt",0,now),claimed=Number(row,"claimedAt",0,now);
            Need(Number(row,"reservedDay",-1)==Day(created,offset));
            object claimedDay=SocialJson82.Field(row,"claimedDay"),receipt=SocialJson82.Field(row,"receipt");
            Need(Flag(row,"completionAuthoritative")== (source=="provider_verified"&&(state=="Verified"||state=="Claimed")));
            if(state=="Reserved")Need(source=="none"&&reported==0&&verified==0);
            if(state=="AwaitingVerification")Need(mode==Trusted&&source=="none"&&reported>=created&&reported<expiry&&verified==0);
            if(state=="CompletedReported")Need(mode==Reported&&source==Reported&&reported>=created&&reported<expiry&&verified==0);
            if(state=="Verified")Need(mode==Trusted&&source=="provider_verified"&&verified>=created&&verified<expiry);
            if(mode==Reported)Need(verified==0);
            if(source==Reported)Need(reported>=created&&reported<expiry);
            if(state=="Cancelled"||state=="Expired")Need(verified==0&&source!="provider_verified");
            if(state=="Expired")Need(now>=expiry);
            if(state=="Claimed"){
                int claimedOffset=row.ContainsKey("claimedUtcOffsetSeconds")?Offset(row,"claimedUtcOffsetSeconds"):offset;
                Need(claimed>=created&&claimedDay is long&&(long)claimedDay==Day(claimed,claimedOffset));
                Need(mode==Reported?source==Reported&&reported>=created:source=="provider_verified"&&verified>=created);
                var value=SocialJson82.Object(receipt);
                Need(Text(value,"id",128)=="rewarded-ad/"+id);
                string wallet=Text(value,"walletReceiptId",128);
                Need(Regex.IsMatch(wallet,@"\Awallet/[0-9a-f]{64}\z")&&Text(value,"completionSource")==source);
                Number(value,"coins",400,400);Need(Number(value,"serverUtc",0,MaxTime)==claimed);
                Number(value,"walletRevision",1);
            } else Need(claimed==0&&claimedDay==null&&receipt==null);
        }

        // Public pure parsers permit actual native malformed-response controls
        // without a provider SDK, client profile mutation or a network request.
        public static AdOpportunity85 ParseOpportunity(string json,string expectedPlayerId,string expectedOpportunityId=null){
            Need(Id(expectedPlayerId)&&(expectedOpportunityId==null||Id(expectedOpportunityId)));
            var row=SocialJson82.Read(json);Opportunity(row,expectedPlayerId,expectedOpportunityId);
            bool noDay=SocialJson82.Field(row,"claimedDay")==null;
            if(noDay)row["claimedDay"]=-1L;
            var value=JsonUtility.FromJson<AdOpportunity85>(SocialJson82.Write(row));Need(value!=null);
            if(SocialJson82.Field(row,"receipt")==null)value.receipt=null;
            return value;
        }
        public static AdStatus85 ParseStatus(string json,string expectedPlayerId,bool expectedProduction=false){
            Need(Id(expectedPlayerId));var row=SocialJson82.Read(json);int offset=Policy(row);string mode=Mode(row);
            bool enabled=Flag(row,"enabled"),available=Flag(row,"available");Need(Flag(row,"productionEnabled")==expectedProduction);
            string reason=Text(row,"reason",128);Need(Code(reason,128));
            long now=Number(row,"serverUtc",0,MaxTime),day=Number(row,"day",-1);Need(day==Day(now,offset));
            long claimed=Number(row,"claimedToday",0,3),remaining=Number(row,"remainingToday",0,3);
            Need(remaining==3-claimed);
            long cooldown=Number(row,"cooldownRemainingSeconds",0,600);
            Need(Number(row,"nextEligibleAt",now,MaxTime+600)==now+cooldown);
            long end=Number(row,"nextDayAt",now+1,MaxTime+86400);
            int nextOffset=row.ContainsKey("nextDayUtcOffsetSeconds")?Offset(row,"nextDayUtcOffsetSeconds"):offset;
            if(row.ContainsKey("timeZoneId")){
                string zone=SocialJson82.Text(row,"timeZoneId",64,true);
                Need(zone.Length==0||Regex.IsMatch(zone,@"\A[A-Za-z][A-Za-z0-9_+-]*(?:/[A-Za-z0-9_+-]+){0,3}\z"));
            }
            if(row.ContainsKey("dayStartedAt")){
                long start=Number(row,"dayStartedAt",-86400,now);
                Need(end>start&&end-start<=172800&&end==(day+1)*86400-nextOffset);
            }else Need(end==(day+1)*86400-nextOffset); // Legacy status/cached fixture.
            object active=SocialJson82.Field(row,"activeOpportunity");
            if(active!=null){var pending=SocialJson82.Object(active);Opportunity(pending,expectedPlayerId);Need(IsPending(Text(pending,"state",32)));}
            if(available)Need(enabled&&active==null&&remaining>0&&cooldown==0&&reason==(mode==Reported?"ready_client_reported_capped":"ready")&&Text(row,"verificationMode")!="unavailable");
            if(active!=null)SocialJson82.Object(active)["claimedDay"]=-1L;
            var value=JsonUtility.FromJson<AdStatus85>(SocialJson82.Write(row));Need(value!=null);
            if(active==null)value.activeOpportunity=null;
            if(value.activeOpportunity!=null&&SocialJson82.Field(SocialJson82.Object(active),"receipt")==null)value.activeOpportunity.receipt=null;
            return value;
        }

        // Pure classification of a complete response. Runtime Send additionally
        // requires the actual current-owner /reserve ProtocolError response.
        // Each allowed code is thrown inside reserve's execute callback, AFTER
        // the server has checked for this command's previously committed reply.
        // Wallet/auth guards run before that lookup and are deliberately absent.
        public static AdReply85<AdOpportunity85> ParseReserveDenial(long status,string contentType,string json){
            if(!string.Equals((contentType??"").Split(';')[0].Trim(),"application/json",StringComparison.OrdinalIgnoreCase))return null;
            try{
                var row=SocialJson82.Read(json);if(row.Count!=1)return null;
                string code=SocialJson82.Text(row,"error",128);
                bool denied=status==409&&(code=="ad_cooldown"||code=="ad_daily_limit"||code=="ad_placement_unavailable"||code=="ad_opportunity_pending")||
                    status==503&&(code=="ads_disabled"||code=="trusted_completion_unavailable");
                return denied?AdReply85<AdOpportunity85>.ReserveDenied(code):null;
            }catch{return null;}
        }

        public IEnumerator Status(ServerAuthorizedContext a,Action<AdReply85<AdStatus85>> done)=>
            Send(a,"GET",Root+"/status?utcOffsetSeconds="+LocalUtcOffsetSeconds().ToString(CultureInfo.InvariantCulture)+"&timeZoneId="+Uri.EscapeDataString(LocalTimeZoneId()),null,true,json=>ParseStatus(json,a.PlayerId,a.ExpectedProduction),done);
        public IEnumerator Reserve(ServerAuthorizedContext a,string commandId,Action<AdReply85<AdOpportunity85>> done)=>
            Send(a,"POST",Root+"/reserve",JsonUtility.ToJson(new Reservation{commandId=commandId}),Id(commandId),json=>ParseOpportunity(json,a.PlayerId),done);
        public IEnumerator Read(ServerAuthorizedContext a,string opportunityId,Action<AdReply85<AdOpportunity85>> done)=>
            Send(a,"GET",Root+"/opportunities/"+opportunityId,null,Id(opportunityId),json=>ParseOpportunity(json,a.PlayerId,opportunityId),done);
        public IEnumerator Report(ServerAuthorizedContext a,string opportunityId,string commandId,Action<AdReply85<AdOpportunity85>> done)=>
            Mutation(a,opportunityId,commandId,"client-completion",done);
        public IEnumerator Claim(ServerAuthorizedContext a,string opportunityId,string commandId,Action<AdReply85<AdOpportunity85>> done)=>
            Mutation(a,opportunityId,commandId,"claim",done);
        public IEnumerator Cancel(ServerAuthorizedContext a,string opportunityId,string commandId,Action<AdReply85<AdOpportunity85>> done)=>
            Mutation(a,opportunityId,commandId,"cancel",done);
        IEnumerator Mutation(ServerAuthorizedContext a,string id,string command,string action,Action<AdReply85<AdOpportunity85>> done)=>
            Send(a,"POST",Root+"/opportunities/"+id+"/"+action,JsonUtility.ToJson(new Command{commandId=command}),Id(id)&&Id(command),json=>ParseOpportunity(json,a.PlayerId,id),done);

        static string Access(ServerAuthorizedContext a){try{return a?.CurrentAccess;}catch{return null;}}
        static bool Context(ServerAuthorizedContext a){
            try{return a!=null&&a.Generation>=0&&Id(a.PlayerId)&&RuStoreBackendClient.IsAllowedOrigin(a.Origin,a.AllowDevelopmentLoopback);}
            catch{return false;}
        }
        bool Same(ServerAuthorizedContext a,string bearer,int token)=>!disposed&&token==Volatile.Read(ref generation)&&Context(a)&&Access(a)==bearer;
        static void Deliver<T>(Action<AdReply85<T>> done,AdReply85<T> reply) where T:class{try{done(reply);}catch{/* Caller owns its UI error handling. */}}
        IEnumerator Send<T>(ServerAuthorizedContext a,string method,string path,string body,bool valid,Func<string,T> parse,Action<AdReply85<T>> done) where T:class {
            if(done==null)throw new ArgumentNullException(nameof(done));
            if(disposed||Thread.CurrentThread.ManagedThreadId!=ownerThread||!Context(a)||!valid){Deliver(done,AdReply85<T>.Fail("AdsRequestInvalid"));yield break;}
            if(busy){Deliver(done,AdReply85<T>.Fail("AdsRequestBusy"));yield break;}
            string bearer=Access(a);if(!IdentityProtocol82.Secret(bearer)){Deliver(done,AdReply85<T>.Fail("AdsSessionChanged"));yield break;}
            int token=Volatile.Read(ref generation);busy=true;bool mutating=method!="GET",sent=false;
            AdReply85<T> reply=null;UnityWebRequest request=null;Download download=null;UnityWebRequestAsyncOperation operation=null;
            try{
                try{
                    if(!Same(a,bearer,token))throw new InvalidOperationException();
                    request=new UnityWebRequest(new Uri(a.Origin).GetLeftPart(UriPartial.Authority)+path,method);active=request;
                    download=new Download();request.downloadHandler=download;request.timeout=15;request.redirectLimit=0;
                    request.SetRequestHeader("Authorization","Bearer "+bearer);request.SetRequestHeader("Accept","application/json");
                    if(body!=null){byte[] bytes=Utf8.GetBytes(body);if(bytes.Length>8192)throw new FormatException();request.uploadHandler=new UploadHandlerRaw(bytes);request.SetRequestHeader("Content-Type","application/json");}
                    sent=true;operation=request.SendWebRequest();
                }catch{reply=AdReply85<T>.Fail("AdsRequestUnavailable",mutating&&sent);}
                if(operation!=null){
                    // The transport timeout can be missed across an app suspend. A mutation
                    // stays unknown, so the saved intent recovers it from the server.
                    var stall=System.Diagnostics.Stopwatch.StartNew();
                    while(!operation.isDone){
                        if(!Same(a,bearer,token)){request.Abort();reply=AdReply85<T>.Fail("AdsSessionChanged",mutating);break;}
                        if(stall.Elapsed.TotalSeconds>StallSeconds){request.Abort();reply=AdReply85<T>.Fail("AdsRequestStalled",mutating);break;}
                        yield return null;
                    }
                    if(reply==null)try{
                        if(!Same(a,bearer,token))reply=AdReply85<T>.Fail("AdsSessionChanged",mutating);
                        else if(download.exceeded)reply=AdReply85<T>.Fail("AdsResponseTooLarge",mutating);
                        else if(request.result!=UnityWebRequest.Result.Success||request.responseCode!=200){
                            AdReply85<AdOpportunity85> denial=null;
                            if(method=="POST"&&path==Root+"/reserve"&&request.result==UnityWebRequest.Result.ProtocolError)
                                try{denial=ParseReserveDenial(request.responseCode,request.GetResponseHeader("Content-Type"),download.Text());}catch{}
                            if(denial!=null&&Same(a,bearer,token))reply=AdReply85<T>.ReserveDenied(denial.Error);
                            else{
                                string code="AdsRequestFailed";
                                if(request.responseCode>=400&&request.responseCode<500)try{string error=SocialJson82.Text(SocialJson82.Read(download.Text()),"error",128);if(Regex.IsMatch(error,@"\A[a-z0-9_]{1,128}\z"))code=error;}catch{}
                                reply=AdReply85<T>.Fail(code,mutating);
                            }
                        }else if(!string.Equals((request.GetResponseHeader("Content-Type")??"").Split(';')[0].Trim(),"application/json",StringComparison.OrdinalIgnoreCase))reply=AdReply85<T>.Fail("AdsContentTypeInvalid",mutating);
                        else reply=AdReply85<T>.Success(parse(download.Text()));
                    }catch{reply=AdReply85<T>.Fail("AdsResponseInvalid",mutating);}
                }
            }finally{
                if(ReferenceEquals(active,request))active=null;request?.Dispose();busy=false;
                Deliver(done,reply??AdReply85<T>.Fail("AdsRequestStopped",mutating&&sent));
            }
        }
        public void Dispose(){
            if(disposed)return;disposed=true;Interlocked.Increment(ref generation);
            if(Thread.CurrentThread.ManagedThreadId==ownerThread)try{active?.Abort();}catch{}
        }
    }
}

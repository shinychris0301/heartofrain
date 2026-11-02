using System;
using System.Collections;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;
using UnityEngine.Networking;
namespace HeartOfTheRain.App.Profile {
    public sealed class BackendResult<T> where T:class {public bool ok;public long status;public T value;public string error;}
    [Serializable] public sealed class BackendTime {public long serverUtc,day;}
    [Serializable] public sealed class BackendOffer {
        public string id,schedule;public long day;public int step;public bool claimed;public RewardGrant grant;
        public GiftOffer Offer()=>new GiftOffer{id=id,schedule=schedule,day=day,step=step,claimed=claimed,grant=grant?.Copy()};
    }
    [Serializable] public sealed class BackendDecision {
        public string playerId,receiptId,requestId,schedule;public long day;public int step;public RewardGrant grant;
        public GiftDecision Decision()=>new GiftDecision{playerId=playerId,receiptId=receiptId,requestId=requestId,schedule=schedule,day=day,step=step,grant=grant?.Copy()};
    }
    [Serializable] public sealed class BackendEventBatch {public ProfileAuditEvent[] events;}
    [Serializable] public sealed class BackendEventAck {public int accepted,duplicates;public string trust;public bool rewarded;}
    [Serializable] public sealed class BackendAccount {public string playerId,balanceScope;public int completed;public long serverUtc;public int[] rewardTotals;public bool realCompetition,purchaseFulfillment;}
    [Serializable] public sealed class BackendReceipt {public string id,source;public RewardGrant grant;public long serverUtc,cursor;}
    [Serializable] public sealed class BackendReceipts {public BackendReceipt[] receipts;public long nextCursor;public bool hasMore;}
    // Explicitly configured transport. Never logs or serializes credentials. No
    // default endpoint, automatic profile migration, sender or synchronous wait.
    public sealed class BackendClient {
        readonly string endpoint,token;
        public BackendClient(string endpoint,string token,bool allowLocalHttp=false){
            Uri uri;if(!Uri.TryCreate(endpoint,UriKind.Absolute,out uri)||uri.UserInfo!=""||uri.Query!=""||uri.Fragment!=""||uri.AbsolutePath!="/")throw new ArgumentException("Invalid backend origin");
            bool local=false;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            local=allowLocalHttp&&uri.Scheme=="http"&&(uri.Host=="127.0.0.1"||uri.Host=="localhost"||uri.Host=="[::1]");
#endif
            if(uri.Scheme!="https"&&!local)throw new ArgumentException("Backend requires HTTPS");
            if(token==null||!Regex.IsMatch(token,"\\A[A-Za-z0-9_-]{43}\\z"))throw new ArgumentException("Invalid backend credential");
            this.endpoint=uri.GetLeftPart(UriPartial.Authority);this.token=token;
        }
        public IEnumerator Time(Action<BackendResult<BackendTime>> done)=>Send<BackendTime>("GET","/v1/time",null,done);
        public IEnumerator Offer(Action<BackendResult<BackendOffer>> done)=>Send<BackendOffer>("GET","/v1/daily-gift/offer",null,done);
        public IEnumerator Claim(PendingGift request,Action<BackendResult<BackendDecision>> done)=>Send<BackendDecision>("POST","/v1/daily-gift/claim",JsonUtility.ToJson(request),done);
        public IEnumerator Account(Action<BackendResult<BackendAccount>> done)=>Send<BackendAccount>("GET","/v1/me",null,done);
        public IEnumerator Receipts(long after,Action<BackendResult<BackendReceipts>> done){if(after<0)throw new ArgumentOutOfRangeException(nameof(after));return Send<BackendReceipts>("GET","/v1/rewards?after="+after+"&limit=100",null,done);}
        public IEnumerator Events(ProfileAuditEvent[] events,Action<BackendResult<BackendEventAck>> done){
            if(events==null||events.Length<1||events.Length>100)throw new ArgumentException("Invalid backend event batch");foreach(var e in events){if(e==null)throw new ArgumentException("Invalid backend event");e.Validate();}
            return Send<BackendEventAck>("POST","/v1/audit-events",JsonUtility.ToJson(new BackendEventBatch{events=events}),done);
        }
        IEnumerator Send<T>(string method,string path,string payload,Action<BackendResult<T>> done) where T:class {
            if(done==null)throw new ArgumentNullException(nameof(done));
            var result=new BackendResult<T>();byte[] bytes=payload==null?null:Encoding.UTF8.GetBytes(payload);
            if(bytes!=null&&bytes.Length>65536){result.error="request_too_large";done(result);yield break;}
            using(var request=new UnityWebRequest(endpoint+path,method)){
                request.downloadHandler=new DownloadHandlerBuffer();request.timeout=10;request.redirectLimit=0;
                request.SetRequestHeader("Authorization","Bearer "+token);request.SetRequestHeader("Accept","application/json");
                if(bytes!=null){request.uploadHandler=new UploadHandlerRaw(bytes);request.SetRequestHeader("Content-Type","application/json");}
                yield return request.SendWebRequest();result.status=request.responseCode;
                if(request.result!=UnityWebRequest.Result.Success){result.error=result.status==0?"network_unavailable":"http_"+result.status;done(result);yield break;}
                if(request.downloadHandler.data.Length>262144){result.error="response_too_large";done(result);yield break;}
                try{result.value=JsonUtility.FromJson<T>(request.downloadHandler.text);result.ok=result.value!=null;result.error=result.ok?null:"invalid_response";}catch(Exception){result.error="invalid_response";}
                done(result);
            }
        }
    }
}

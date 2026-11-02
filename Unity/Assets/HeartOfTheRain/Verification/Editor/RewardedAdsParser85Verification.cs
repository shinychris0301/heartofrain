#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.App.Advertising;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.ServerGameplay;

namespace HeartOfTheRain.Verification {
    // Actual pinned-native parsers and optional real loopback HTTP. Neither
    // entry starts Play Mode, an advertising SDK, or an ordinary app profile.
    public static class RewardedAdsParser85Verification {
        const string Player="11111111111111111111111111111111",Other="22222222222222222222222222222222",Opportunity="33333333333333333333333333333333";
        const string SDK="sdk_client_reported_capped",Trusted="trusted_completion";
        [Serializable] sealed class Report {
            public string status,utc,unity,scope,ordinaryProfilesBefore,ordinaryProfilesAfter,playerHash;
            public int checks,positiveCases,negativeCases,adsCalls,signedIdentityCalls,walletReads,creditedCoins,creditedGrants;
            public bool actualHttp,ordinaryProfilesUnchanged,languagePreferenceUnchanged,localProfileMutated,realAdImpressionVerified;
            public List<string> passed=new List<string>(),errors=new List<string>();
            public List<int> identityStatuses=new List<int>();
        }
        static Report report;
        static string Output=>Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REWARDED_ADS85_OUTPUT")??"../Verification/Evidence/ShopAds85");
        static void Check(bool condition,string label){report.checks++;if(!condition)throw new InvalidOperationException(label);report.passed.Add(label);}
        static string Q(string value)=>"\""+value+"\"";
        static string Sample(string state="Reserved",string mode=SDK,string source="none",long reported=0,long verified=0,long claimed=0,bool authoritative=false,long now=100010){
            string receipt=state!="Claimed"?"null":"{\"id\":\"rewarded-ad/"+Opportunity+"\",\"walletReceiptId\":\"wallet/"+new string('a',64)+"\",\"coins\":400,\"serverUtc\":"+claimed+",\"walletRevision\":2,\"completionSource\":"+Q(source)+"}";
            return "{\"opportunityId\":"+Q(Opportunity)+",\"playerId\":"+Q(Player)+",\"placement\":\"shop_rewarded\",\"configVersion\":\"rewarded-shop-v1\",\"rewardCoins\":400,\"dailyLimit\":3,\"utcOffsetSeconds\":36000,\"cooldownSeconds\":600,\"completionMode\":"+Q(mode)+",\"verificationMode\":"+Q(mode==SDK?SDK:"synthetic_local_staging_only")+",\"completionSource\":"+Q(source)+",\"reservedDay\":1,\"createdAt\":100000,\"expiresAt\":100900,\"state\":"+Q(state)+",\"clientReportedAt\":"+reported+",\"verifiedAt\":"+verified+",\"claimedAt\":"+claimed+",\"claimedDay\":"+(state=="Claimed"?"1":"null")+",\"receipt\":"+receipt+",\"serverUtc\":"+now+",\"completionAuthoritative\":"+(authoritative?"true":"false")+"}";
        }
        static string Status(string active="null",bool available=true){
            return "{\"enabled\":true,\"available\":"+(available?"true":"false")+",\"reason\":"+Q(active=="null"?"ready_client_reported_capped":"pending_opportunity")+",\"verificationMode\":"+Q(SDK)+",\"completionMode\":"+Q(SDK)+",\"productionEnabled\":false,\"placement\":\"shop_rewarded\",\"configVersion\":\"rewarded-shop-v1\",\"rewardCoins\":400,\"dailyLimit\":3,\"utcOffsetSeconds\":36000,\"cooldownSeconds\":600,\"day\":1,\"claimedToday\":0,\"remainingToday\":3,\"cooldownRemainingSeconds\":0,\"nextEligibleAt\":100010,\"nextDayAt\":136800,\"activeOpportunity\":"+active+",\"serverUtc\":100010}";
        }
        static void Reject(string label,Action parse){bool rejected=false;try{parse();}catch(FormatException){rejected=true;}Check(rejected,label);report.negativeCases++;}
        static void Mutate(string original,string from,string to,string label,bool status=false){
            string changed=original.Replace(from,to);Check(changed!=original,"Negative control actually changes "+label);
            Reject(label,()=>{if(status)RewardedAdsClient85.ParseStatus(changed,Player);else RewardedAdsClient85.ParseOpportunity(changed,Player,Opportunity);});
        }
        static void ParserChecks(){
            var values=new[]{Sample(),Sample("CompletedReported",SDK,SDK,100005),Sample("Claimed",SDK,SDK,100005,0,100008),
                Sample("Cancelled"),Sample("Cancelled",SDK,SDK,100005),Sample("Expired",SDK,SDK,100005,0,0,false,100900),
                Sample("Reserved",Trusted),Sample("AwaitingVerification",Trusted,"none",100005),
                Sample("Verified",Trusted,"provider_verified",0,100006,0,true),Sample("Claimed",Trusted,"provider_verified",100005,100006,100008,true)};
            foreach(string json in values){var value=RewardedAdsClient85.ParseOpportunity(json,Player,Opportunity);Check(value.playerId==Player&&value.opportunityId==Opportunity,"Positive fixed-policy state parses "+value.state+"/"+value.completionMode);if(value.state!="Claimed")Check(value.receipt==null&&value.claimedDay==-1,"Actual null receipt/day normalized without fabricated claim "+value.state);report.positiveCases++;}
            var ready=RewardedAdsClient85.ParseStatus(Status(),Player);Check(ready.available&&ready.activeOpportunity==null&&ready.day==1,"Ready status preserves actual null active opportunity");report.positiveCases++;
            var pending=RewardedAdsClient85.ParseStatus(Status(Sample("CompletedReported",SDK,SDK,100005),false),Player);Check(!pending.available&&pending.activeOpportunity.claimedDay==-1&&pending.activeOpportunity.receipt==null,"Nested pending status normalizes actual null fields");report.positiveCases++;
            foreach(int offset in new[]{-43200,-18000,0,19800,20700,36000,50400}){
                long day=(long)Math.Floor((100010L+offset)/86400d),createdDay=(long)Math.Floor((100000L+offset)/86400d),end=(day+1)*86400-offset;
                string local=values[2].Replace("\"utcOffsetSeconds\":36000","\"utcOffsetSeconds\":"+offset).Replace("\"reservedDay\":1","\"reservedDay\":"+createdDay).Replace("\"claimedDay\":1","\"claimedDay\":"+day);
                Check(RewardedAdsClient85.ParseOpportunity(local,Player,Opportunity).utcOffsetSeconds==offset,"Local claim offset accepted "+offset);report.positiveCases++;
                local=Status().Replace("\"utcOffsetSeconds\":36000","\"utcOffsetSeconds\":"+offset).Replace("\"day\":1","\"day\":"+day).Replace("\"nextDayAt\":136800","\"nextDayAt\":"+end+",\"dayStartedAt\":"+(end-86400));
                Check(RewardedAdsClient85.ParseStatus(local,Player).nextDayAt==end,"Local status midnight accepted "+offset);report.positiveCases++;
                Mutate(local,"\"dayStartedAt\":"+(end-86400),"\"dayStartedAt\":100011","Future local window start rejected",true);
            }
            string transition=Status().Replace("\"utcOffsetSeconds\":36000","\"utcOffsetSeconds\":19800").Replace("\"nextDayAt\":136800","\"nextDayAt\":153000,\"dayStartedAt\":45000");
            Check(RewardedAdsClient85.ParseStatus(transition,Player).dayStartedAt==45000,"Offset-change transition preserves existing window start");report.positiveCases++;
            Check(RewardedAdsClient85.LocalUtcOffsetSeconds()>=-43200&&RewardedAdsClient85.LocalUtcOffsetSeconds()<=50400,"Actual host local offset is bounded without a wall-clock grant");
            foreach(var localDay in new[]{new long[]{1772946600,1772946000,1773028800,-18000,-14400},new long[]{1774739400,1774738800,1774821600,3600,7200},new long[]{1792879800,1792879200,1792969200,7200,3600},new long[]{1793506200,1793505600,1793595600,-14400,-18000}}){
                long day=(long)Math.Floor((localDay[0]+localDay[3])/86400d);
                string json=Status().Replace("\"utcOffsetSeconds\":36000","\"utcOffsetSeconds\":"+localDay[3]).Replace("\"day\":1","\"day\":"+day).Replace("100010",localDay[0].ToString()).Replace("\"nextDayAt\":136800","\"nextDayAt\":"+localDay[2]+",\"dayStartedAt\":"+localDay[1]+",\"nextDayUtcOffsetSeconds\":"+localDay[4]+",\"timeZoneId\":\"America/New_York\"");
                var parsed=RewardedAdsClient85.ParseStatus(json,Player);
                Check(parsed.nextDayAt-parsed.dayStartedAt==localDay[2]-localDay[1],"Server IANA 23/25-hour local day parses with separate next-midnight offset");report.positiveCases++;
                Mutate(json,"\"nextDayUtcOffsetSeconds\":"+localDay[4],"\"nextDayUtcOffsetSeconds\":901","Invalid next-midnight offset rejected",true);
                Mutate(json,"America/New_York","../UTC","Timezone path rejected",true);
            }
            long claimedNow=1773028810,claimDay=(claimedNow-14400)/86400;
            string dstClaim=Sample("Claimed",Trusted,"provider_verified",100005,100006,claimedNow,true,claimedNow).Replace("\"utcOffsetSeconds\":36000","\"utcOffsetSeconds\":-18000,\"claimedUtcOffsetSeconds\":-14400").Replace("\"reservedDay\":1","\"reservedDay\":0").Replace("\"claimedDay\":1","\"claimedDay\":"+claimDay);
            Check(RewardedAdsClient85.ParseOpportunity(dstClaim,Player,Opportunity).claimedUtcOffsetSeconds==-14400,"Claim recovery preserves different reserved and actual claim DST offsets");report.positiveCases++;
            Mutate(dstClaim,"\"claimedUtcOffsetSeconds\":-14400","\"claimedUtcOffsetSeconds\":901","Invalid claim-time offset rejected");
            string basis=Sample(),claimed=values[2],status=Status();
            foreach(string json in new[]{"null","[]","{}","{}x","{\"rewardCoins\":NaN}","{\"rewardCoins\":400.0}","{\"text\":\"\\ud800\"}"})Reject("Malformed/type/Unicode response rejected",()=>RewardedAdsClient85.ParseOpportunity(json,Player));
            Mutate(basis,"\"rewardCoins\":400","\"rewardCoins\":400,\"rewardCoins\":400","Duplicate policy key");
            foreach(var change in new[]{new[]{"\"rewardCoins\":400","\"rewardCoins\":401"},new[]{"\"dailyLimit\":3","\"dailyLimit\":4"},new[]{"\"utcOffsetSeconds\":36000","\"utcOffsetSeconds\":901"},new[]{"\"cooldownSeconds\":600","\"cooldownSeconds\":599"},new[]{"\"rewardCoins\":400","\"rewardCoins\":\"400\""},new[]{"\"dailyLimit\":3","\"dailyLimit\":true"},new[]{Player,Other},new[]{"\"reservedDay\":1","\"reservedDay\":2"},new[]{"\"claimedDay\":null","\"claimedDay\":1"},new[]{"\"expiresAt\":100900","\"expiresAt\":100000"},new[]{"\"state\":\"Reserved\"","\"state\":\"Approved\""}})Mutate(basis,change[0],change[1],"Policy/owner/state/day counterexample");
            Reject("Expected opportunity binding",()=>RewardedAdsClient85.ParseOpportunity(basis,Player,Other));
            Reject("Invalid expected player",()=>RewardedAdsClient85.ParseOpportunity(basis,"invalid"));
            Mutate(claimed,"\"completionAuthoritative\":false","\"completionAuthoritative\":true","SDK claim is never provider-authoritative");
            Mutate(claimed,"\"completionSource\":\""+SDK+"\"","\"completionSource\":\"provider_verified\"","SDK mode cannot contain verified source");
            Mutate(claimed,"wallet/","foreign/","Wallet receipt format");
            Mutate(claimed,"rewarded-ad/"+Opportunity,"rewarded-ad/"+Other,"Reward receipt owner-opportunity binding");
            Mutate(claimed,"\"coins\":400","\"coins\":999","Receipt quantity");
            Mutate(claimed,"\"walletRevision\":2","\"walletRevision\":0","Receipt revision");
            Mutate(claimed,"\"claimedDay\":1","\"claimedDay\":2","Claim uses fixed-offset actual claim day");
            Mutate(claimed,"\"claimedAt\":100008","\"claimedAt\":100009","Receipt clock matches claim");
            Mutate(claimed,"\"state\":\"Claimed\"","\"state\":\"Verified\"","SDK mode cannot impersonate verified state");
            Mutate(values[8],"\"completionAuthoritative\":true","\"completionAuthoritative\":false","Trusted verified flag consistency");
            foreach(var change in new[]{new[]{"\"day\":1","\"day\":2"},new[]{"\"remainingToday\":3","\"remainingToday\":2"},new[]{"\"nextEligibleAt\":100010","\"nextEligibleAt\":100011"},new[]{"\"nextDayAt\":136800","\"nextDayAt\":136801"},new[]{"\"productionEnabled\":false","\"productionEnabled\":true"},new[]{"\"enabled\":true","\"enabled\":false"}})Mutate(status,change[0],change[1],"Status arithmetic/availability counterexample",true);
            Reject("Terminal opportunity cannot appear as pending active",()=>RewardedAdsClient85.ParseStatus(Status(claimed,false),Player));
            Reject("Available status cannot hide active pending",()=>RewardedAdsClient85.ParseStatus(Status(Sample("CompletedReported",SDK,SDK,100005)),Player));
        }
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,scope="Actual pinned-native pure parser/JsonUtility positives and malformed-response controls. No Play Mode, HTTP, SDK, actual impression, currency grant or ordinary profile mutation."};
            try{ParserChecks();}catch(Exception error){report.errors.Add(error.GetType().Name+": parser assertion failed");}
            Write("RewardedAdsParser85.json","PASS_NATIVE_REWARDED_ADS85_PARSER","FAIL_NATIVE_REWARDED_ADS85_PARSER");
        }
        static void Write(string file,string pass,string fail){report.utc=DateTime.UtcNow.ToString("o");report.status=report.errors.Count==0?pass:fail;Directory.CreateDirectory(Path.Combine(Output,"Native"));File.WriteAllText(Path.Combine(Output,"Native",file),JsonUtility.ToJson(report,true),new UTF8Encoding(false));if(Application.isBatchMode)EditorApplication.Exit(report.errors.Count==0?0:1);}

        static readonly Stack<IEnumerator> stack=new Stack<IEnumerator>();
        static readonly Queue<IEnumerator> dispatched=new Queue<IEnumerator>();
        static readonly List<IDisposable> cleanup=new List<IDisposable>();
        static readonly List<IdentityHttpTransport82> transports=new List<IdentityHttpTransport82>();
        static AsyncOperation waiting;static double deadline;static bool finished,hadLanguage;static int language;
        static string temporary;
        static void Dispatch(IEnumerator value){dispatched.Enqueue(value);}
        static string Id()=>Guid.NewGuid().ToString("N");
        static string ProfilesHash(){string root=Path.Combine(Application.persistentDataPath,"Profiles");if(!Directory.Exists(root))return IdentityProtocol82.Sha("absent");return IdentityProtocol82.Sha(string.Join("\n",Directory.GetFiles(root,"*",SearchOption.AllDirectories).OrderBy(x=>x,StringComparer.Ordinal).Select(p=>p.Substring(root.Length).Replace('\\','/')+":"+IdentityProtocol82.Sha(File.ReadAllBytes(p)))));}
        static ManagedIdentitySession82 Session(string origin,string name){var vault=new EditorEphemeralIdentity82();cleanup.Add(vault);var transport=new IdentityHttpTransport82(origin,Dispatch,true);transports.Add(transport);cleanup.Add(transport);var session=new ManagedIdentitySession82(vault.CreateKey(),vault.CreateStore(Path.Combine(temporary,name+".sealed")),transport);cleanup.Add(session);return session;}
        static IEnumerator Guest(ManagedIdentitySession82 session){IdentityReply82<IdentityView82> result=null;session.CreateGuest(Id(),r=>result=r);while(result==null)yield return null;Check(result.Succeeded&&session.HasAccess,"Actual signed managed guest created using ephemeral protected device key");}
        static ServerAuthorizedContext Context(string origin,ManagedIdentitySession82 session,Func<bool> live){
            return (ServerAuthorizedContext)Activator.CreateInstance(typeof(ServerAuthorizedContext),BindingFlags.Instance|BindingFlags.NonPublic,null,new object[]{origin,session.View.playerId,1L,true,(Func<string>)(()=>live()&&session.HasAccess?session.AccessToken:null)},null);
        }
        static IEnumerator Wallet(string origin,ManagedIdentitySession82 session,Action<RuStoreServerWallet> check){var client=new RuStoreBackendClient(origin,session.AccessToken,session.View.playerId,true,true,Dispatch);cleanup.Add(client);PayReply<RuStoreServerWallet> result=null;client.GetWallet(r=>result=r);while(result==null)yield return null;report.walletReads++;Check(result.Succeeded,"Actual authoritative wallet HTTP read succeeds");check(result.value);}
        static IEnumerator Call<T>(Func<Action<AdReply85<T>>,IEnumerator> call,Action<T> check) where T:class{AdReply85<T> result=null;yield return call(r=>result=r);report.adsCalls++;Check(result!=null&&result.Ok,"Actual typed rewarded-ad HTTP reply succeeds");check?.Invoke(result.Value);}
        static IEnumerator HttpChecks(string origin){
            var first=Session(origin,"first");var second=Session(origin,"second");yield return Guest(first);yield return Guest(second);
            bool live=true;var context=Context(origin,first,()=>live);var peer=Context(origin,second,()=>true);var client=new RewardedAdsClient85();cleanup.Add(client);
            report.playerHash=IdentityProtocol82.Sha(first.View.playerId);yield return Wallet(origin,first,w=>Check(w.coins==1250&&w.revision==1&&w.lives==5,"Managed account starts with approved server genesis only"));
            yield return Call<AdStatus85>(done=>client.Status(context,done),value=>Check(value.available&&value.completionMode==SDK&&value.rewardCoins==400&&value.remainingToday==3,"Actual fixture exposes explicit lower-trust capped400 offer"));
            AdOpportunity85 opportunity=null;string reserve=Id();yield return Call<AdOpportunity85>(done=>client.Reserve(context,reserve,done),value=>{opportunity=value;Check(value.state=="Reserved"&&value.receipt==null&&value.claimedDay==-1,"Actual reservation is owner bound and grants nothing");});
            yield return Call<AdOpportunity85>(done=>client.Reserve(context,reserve,done),value=>Check(value.opportunityId==opportunity.opportunityId,"Actual lost-reservation retry returns same opportunity"));
            AdReply85<AdOpportunity85> denied=null;yield return client.Read(peer,opportunity.opportunityId,value=>denied=value);report.adsCalls++;Check(denied!=null&&!denied.Ok&&denied.Error=="ad_opportunity_not_found","Actual foreign managed actor cannot read opportunity");
            yield return Call<AdOpportunity85>(done=>client.Claim(context,opportunity.opportunityId,Id(),done),value=>Check(value.state=="Reserved"&&value.receipt==null,"Claim before completion grants no coins"));
            yield return Call<AdOpportunity85>(done=>client.Report(context,opportunity.opportunityId,Id(),done),value=>Check(value.state=="CompletedReported"&&!value.completionAuthoritative&&value.verifiedAt==0,"Actual client report is explicitly non-authoritative"));
            yield return Wallet(origin,first,w=>Check(w.coins==1250&&w.revision==1,"Client callback alone does not change authoritative wallet"));
            string claim=Id();AdOpportunity85 receipt=null;yield return Call<AdOpportunity85>(done=>client.Claim(context,opportunity.opportunityId,claim,done),value=>{receipt=value;Check(value.state=="Claimed"&&value.receipt.coins==400&&value.receipt.completionSource==SDK&&!value.completionAuthoritative,"Actual fixed server claim credits lower-trust reported-ad receipt");});
            yield return Call<AdOpportunity85>(done=>client.Claim(context,opportunity.opportunityId,claim,done),value=>Check(value.receipt.id==receipt.receipt.id&&value.receipt.walletRevision==receipt.receipt.walletRevision,"Actual duplicate/lost-ack claim returns same durable receipt"));
            yield return Call<AdOpportunity85>(done=>client.Read(context,opportunity.opportunityId,done),value=>Check(value.state=="Claimed"&&value.receipt.id==receipt.receipt.id,"Actual GET recovers committed claim receipt"));
            yield return Wallet(origin,first,w=>Check(w.coins==1650&&w.revision==2&&w.lives==5&&!w.localProfileMutated,"Exactly one400 server-wallet credit and revision; no local profile grant"));
            yield return Wallet(origin,second,w=>Check(w.coins==1250&&w.revision==1,"Foreign managed actor wallet remains unchanged"));
            yield return Call<AdStatus85>(done=>client.Status(context,done),value=>Check(!value.available&&value.reason=="cooldown"&&value.claimedToday==1&&value.remainingToday==2&&value.cooldownRemainingSeconds>0,"Actual server cooldown and fixed-day quota visible"));
            live=false;AdReply85<AdStatus85> stale=null;yield return client.Status(context,value=>stale=value);Check(stale!=null&&!stale.Ok&&stale.Error=="AdsSessionChanged"&&!stale.Unknown,"Expired/generation-fenced access fails before another request");
            report.creditedCoins=400;report.creditedGrants=1;
        }
        public static void RunHttp(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,actualHttp=true,scope="Actual native non-PlayMode UnityWebRequest against isolated SQLite API with two real signed managed guests and encrypted ephemeral Windows identity journals. The authorized-context internal constructor is used only by this transport fixture. SDK completion is deliberately client-reported/capped and proves no ad impression, Yandex verification or advertising revenue. No normal-selected app routing, Android, SDK load/display, local economy/profile mutation or production activation."};
            try{string origin=Environment.GetEnvironmentVariable("HOTR_REWARDED_ADS85_HTTP_ORIGIN");if(Environment.GetEnvironmentVariable("HOTR_REWARDED_ADS85_HTTP_ALLOWED")!="1"||!RuStoreBackendClient.IsAllowedOrigin(origin,true)||!new Uri(origin).IsLoopback)throw new InvalidOperationException();
                temporary=Path.GetFullPath("../.verification-cache/Launch82/Ads85/HttpClient/"+Id());Directory.CreateDirectory(temporary);report.ordinaryProfilesBefore=ProfilesHash();hadLanguage=PlayerPrefs.HasKey(GameLocale.PreferenceKey);language=PlayerPrefs.GetInt(GameLocale.PreferenceKey,-1);
                finished=false;deadline=EditorApplication.timeSinceStartup+180;stack.Clear();dispatched.Clear();stack.Push(HttpChecks(origin));EditorApplication.update+=Tick;
            }catch{report.errors.Add("Explicit isolated rewarded-ad HTTP fixture unavailable");FinishHttp();}
        }
        static void Tick(){try{if(EditorApplication.timeSinceStartup>deadline)throw new TimeoutException();if(waiting!=null){if(!waiting.isDone)return;waiting=null;}if(stack.Count==0){FinishHttp();return;}var value=stack.Peek();if(!value.MoveNext()){stack.Pop();(value as IDisposable)?.Dispose();}else if(value.Current is IEnumerator child)stack.Push(child);else if(value.Current is AsyncOperation operation)waiting=operation;while(dispatched.Count>0)stack.Push(dispatched.Dequeue());}catch(Exception error){report.errors.Add("HTTP verification "+error.GetType().Name+": bounded assertion failed");FinishHttp();}}
        static void FinishHttp(){if(finished)return;finished=true;EditorApplication.update-=Tick;while(stack.Count>0)(stack.Pop() as IDisposable)?.Dispose();while(dispatched.Count>0)(dispatched.Dequeue() as IDisposable)?.Dispose();foreach(var value in transports){report.signedIdentityCalls+=value.VerificationRequestCount;report.identityStatuses.AddRange(value.VerificationStatuses);}for(int n=cleanup.Count-1;n>=0;n--)try{cleanup[n].Dispose();}catch{}cleanup.Clear();transports.Clear();waiting=null;
            try{report.ordinaryProfilesAfter=ProfilesHash();report.ordinaryProfilesUnchanged=report.ordinaryProfilesBefore==report.ordinaryProfilesAfter;report.languagePreferenceUnchanged=PlayerPrefs.HasKey(GameLocale.PreferenceKey)==hadLanguage&&PlayerPrefs.GetInt(GameLocale.PreferenceKey,-1)==language;Check(report.ordinaryProfilesUnchanged&&report.languagePreferenceUnchanged,"Ordinary local profiles and language preference unchanged");}catch{report.errors.Add("Ordinary profile audit failed");}
            Write("RewardedAds85_HTTP.json","PASS_NATIVE_REWARDED_ADS85_HTTP","FAIL_NATIVE_REWARDED_ADS85_HTTP");
        }
    }
}
#endif

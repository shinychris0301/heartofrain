#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using HeartOfTheRain.App.Advertising;
using HeartOfTheRain.App.ServerGameplay;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.Verification {
    // Native Editor state/transaction tests using scripted API/provider seams
    // and the actual disk journal. No SDK, HTTP, ad, revenue or device proof.
    public static class RewardedAdsFlow85Verification {
        [Serializable] sealed class CaseRow { public string name;public int checks;public bool passed; }
        [Serializable] sealed class Report {
            public string status,utc,unity;public int checks,cases;
            public int reserveDenialClassifierAccepted,reserveDenialClassifierRejected,freshReserveDenialsResolved,unprovenReserveDenialsRetained,recoveredReserveDenialsRetained;
            public bool actualDiskJournal=true,scriptedProvider=true,scriptedApi=true;
            public string scope="Pinned Unity Editor execution of the actual rewarded-flow/journal with scripted provider/API and isolated temporary-file I/O. A callback alone cannot change the scripted wallet; only its fake authenticated Claim changes that fixture. Not provider verification, server HTTP/idempotency proof, real ads, real reward/currency, production or Android/power-loss certification.";
            public List<CaseRow> rows=new List<CaseRow>();public List<string> errors=new List<string>();
        }
        const string Origin="http://127.0.0.1:18585",Player="11111111111111111111111111111111";
        static Report report;static string directory;
        static void Need(bool value,string code){report.checks++;if(!value)throw new InvalidOperationException(code);}
        static IEnumerator Immediate(Action action){action();yield break;}
        static T Copy<T>(T value) where T:class {if(value==null)return null;return JsonUtility.FromJson<T>(JsonUtility.ToJson(value));}
        static AdOpportunity85 CopyOpportunity(AdOpportunity85 value){var next=Copy(value);if(next!=null&&value.receipt==null)next.receipt=null;return next;}

        sealed class Provider:IRewardedAdsProvider85 {
            public bool loadSuccess=true;public int loads,shows,disposes;public Action<RewardedSignal85> callback;
            public bool Installed=>true;
            public void Load(Action<bool,string> complete){loads++;complete(loadSuccess,loadSuccess?null:"ScriptedNoFill");}
            public void Show(Action<RewardedSignal85> signal){shows++;callback=signal;}
            // Intentionally retain callback after Dispose for stale-owner controls.
            public void Emit(RewardedSignal85 value){callback?.Invoke(value);}
            public void Dispose(){disposes++;}
        }
        sealed class Api:IRewardedAdsApi85 {
            public int coins=1250,grants,statusCalls,readCalls,reserveCalls,reportCalls,claimCalls,cancelCalls;
            public bool available=true,loseReserveOnce,loseReportBeforeOnce,loseReportAfterOnce,loseClaimOnce,loseCancelOnce;
            public AdOpportunity85 opportunity;int nextOpportunity;
            public AdReply85<AdOpportunity85> reserveReply;
            public Action beforeRead,beforeClaim;
            public readonly List<string> reserveIds=new List<string>(),reportIds=new List<string>(),claimIds=new List<string>(),cancelIds=new List<string>();
            string reservation;
            public IEnumerator Status(ServerAuthorizedContext a,Action<AdReply85<AdStatus85>> done){
                bool active=opportunity!=null&&(opportunity.state=="Reserved"||opportunity.state=="CompletedReported"||opportunity.state=="Verified");
                statusCalls++;done(AdReply85<AdStatus85>.Success(new AdStatus85{enabled=true,available=available&&!active,reason=active?"opportunity_pending":available?"ready_client_reported_capped":"daily_limit",rewardCoins=400,dailyLimit=3,utcOffsetSeconds=36000,cooldownSeconds=600,remainingToday=available?3:0,claimedToday=available?0:3,completionMode="sdk_client_reported_capped",activeOpportunity=active?CopyOpportunity(opportunity):null}));yield break;
            }
            public IEnumerator Reserve(ServerAuthorizedContext a,string commandId,Action<AdReply85<AdOpportunity85>> done){
                reserveCalls++;reserveIds.Add(commandId);
                if(reserveReply!=null){done(reserveReply);yield break;}
                if(reservation!=commandId){
                    if(opportunity!=null&&(opportunity.state=="Reserved"||opportunity.state=="CompletedReported")){done(AdReply85<AdOpportunity85>.Fail("ScriptedOutstanding"));yield break;}
                    reservation=commandId;opportunity=new AdOpportunity85{opportunityId=(++nextOpportunity).ToString("x32"),playerId=Player,state="Reserved",placement="shop_rewarded",configVersion="fixture85",rewardCoins=400,dailyLimit=3,utcOffsetSeconds=36000,cooldownSeconds=600,completionMode="sdk_client_reported_capped",completionAuthoritative=false};
                }
                if(loseReserveOnce){loseReserveOnce=false;done(AdReply85<AdOpportunity85>.Fail("ScriptedLostReserve",true));yield break;}
                done(AdReply85<AdOpportunity85>.Success(CopyOpportunity(opportunity)));yield break;
            }
            public IEnumerator Read(ServerAuthorizedContext a,string id,Action<AdReply85<AdOpportunity85>> done){beforeRead?.Invoke();readCalls++;done(id==opportunity?.opportunityId?AdReply85<AdOpportunity85>.Success(CopyOpportunity(opportunity)):AdReply85<AdOpportunity85>.Fail("ScriptedMissing"));yield break;}
            public IEnumerator Report(ServerAuthorizedContext a,string id,string commandId,Action<AdReply85<AdOpportunity85>> done){
                reportCalls++;reportIds.Add(commandId);
                if(loseReportBeforeOnce){loseReportBeforeOnce=false;done(AdReply85<AdOpportunity85>.Fail("ScriptedLostReportBefore",true));yield break;}
                opportunity.state="CompletedReported";
                if(loseReportAfterOnce){loseReportAfterOnce=false;done(AdReply85<AdOpportunity85>.Fail("ScriptedLostReportAfter",true));yield break;}
                done(AdReply85<AdOpportunity85>.Success(CopyOpportunity(opportunity)));yield break;
            }
            public IEnumerator Claim(ServerAuthorizedContext a,string id,string commandId,Action<AdReply85<AdOpportunity85>> done){
                claimCalls++;claimIds.Add(commandId);
                beforeClaim?.Invoke();
                if(opportunity.state!="Claimed"){
                    if(opportunity.state!="CompletedReported"&&opportunity.state!="Verified"){done(AdReply85<AdOpportunity85>.Fail("ScriptedNotCompleted"));yield break;}
                    coins+=400;grants++;opportunity.state="Claimed";
                    opportunity.receipt=new AdReceipt85{id="rewarded-ad/"+id,walletReceiptId="wallet/"+grants.ToString("x64"),coins=400,walletRevision=grants+1,completionSource=opportunity.completionMode=="trusted_completion"?"provider_verified":"sdk_client_reported_capped"};
                }
                if(loseClaimOnce){loseClaimOnce=false;done(AdReply85<AdOpportunity85>.Fail("ScriptedLostClaim",true));yield break;}
                done(AdReply85<AdOpportunity85>.Success(CopyOpportunity(opportunity)));yield break;
            }
            public IEnumerator Cancel(ServerAuthorizedContext a,string id,string commandId,Action<AdReply85<AdOpportunity85>> done){
                cancelCalls++;cancelIds.Add(commandId);
                if(loseCancelOnce){loseCancelOnce=false;done(AdReply85<AdOpportunity85>.Fail("ScriptedLostCancel",true));yield break;}
                if(opportunity.state!="Claimed")opportunity.state="Cancelled";
                done(AdReply85<AdOpportunity85>.Success(CopyOpportunity(opportunity)));yield break;
            }
        }
        sealed class Driver:IDisposable {
            readonly Stack<IEnumerator> stack=new Stack<IEnumerator>();
            public Driver(IEnumerator value){stack.Push(value);}
            bool Tick(){
                int work=0;while(stack.Count>0){if(++work>4096)throw new InvalidOperationException("NestedDriverWorkBound");
                    var current=stack.Peek();if(!current.MoveNext()){(stack.Pop() as IDisposable)?.Dispose();continue;}
                    if(current.Current is IEnumerator next)stack.Push(next);else return true;
                }return false;
            }
            public void Until(Func<bool> stop){for(int i=0;i<512;i++){if(stop())return;if(!Tick())break;}if(!stop())throw new InvalidOperationException("NestedDriverConditionBound");}
            public void End(){for(int i=0;i<512;i++)if(!Tick())return;throw new InvalidOperationException("NestedDriverFrameBound");}
            public void Dispose(){while(stack.Count>0)try{(stack.Pop() as IDisposable)?.Dispose();}catch{}}
        }
        sealed class Fixture:IDisposable {
            public readonly Api api=new Api();public readonly List<Provider> providers=new List<Provider>();
            readonly List<RewardedAdsFlow85> flows=new List<RewardedAdsFlow85>();readonly List<Driver> drivers=new List<Driver>();
            public readonly string path;public RewardedAdsJournal85 journal;public RewardedAdsFlow85 flow;
            public bool access=true,loadSuccess=true,failRefreshOnce,renewOnAuthorize;public int projectedCoins=1250,refreshes,authorizations;
            public Fixture(string name){path=Path.Combine(directory,name,"intent.json");Open();}
            ServerAuthorizedContext Context(){
                return (ServerAuthorizedContext)Activator.CreateInstance(typeof(ServerAuthorizedContext),BindingFlags.Instance|BindingFlags.NonPublic,null,new object[]{Origin,Player,1L,true,new Func<string>(()=>access?"scripted-in-memory-access":null)},null);
            }
            public void Open(){
                flow?.Dispose();journal=new RewardedAdsJournal85(path);
                flow=new RewardedAdsFlow85(api,journal,done=>Immediate(()=>{authorizations++;if(renewOnAuthorize){renewOnAuthorize=false;access=true;}done(Context(),null);}),done=>Immediate(()=>{
                    refreshes++;if(failRefreshOnce){failRefreshOnce=false;done(false,"ScriptedWalletUnavailable");return;}projectedCoins=api.coins;done(true,null);
                }),privacy=>{var value=new Provider{loadSuccess=loadSuccess};providers.Add(value);return value;});flows.Add(flow);
            }
            public Driver Drive(IEnumerator routine){var value=new Driver(flow.Guard(routine));drivers.Add(value);return value;}
            public Driver Watch(){int before=providers.Count;var value=Drive(flow.Watch(new AdPrivacy85(true)));value.Until(()=>providers.Count==before+1&&providers[providers.Count-1].shows==1);return value;}
            public AdIntent85 Saved(){AdIntent85 value;string error;Need(journal.TryLoad(Origin,Player,out value,out error)&&error==null&&value!=null,"ActualDiskIntentAvailable");return value;}
            public void Finish(Driver driver,bool completion=true){var provider=providers[providers.Count-1];provider.Emit(RewardedSignal85.Shown);if(completion)provider.Emit(RewardedSignal85.CompletedInfoOnly);provider.Emit(RewardedSignal85.Closed);driver.End();}
            public void Dispose(){foreach(var value in flows)value.Dispose();foreach(var value in drivers)value.Dispose();}
        }
        static void Case(string name,Action action){
            int before=report.checks;var row=new CaseRow{name=name};report.rows.Add(row);report.cases++;
            try{action();row.passed=true;}catch(Exception error){report.errors.Add(name+":"+(error is InvalidOperationException?error.Message:error.GetType().Name));}
            row.checks=report.checks-before;
        }
        static void Success(){using(var f=new Fixture("success")){
            var driver=f.Watch();var ids=f.Saved();var provider=f.providers[0];provider.Emit(RewardedSignal85.Shown);provider.Emit(RewardedSignal85.CompletedInfoOnly);provider.Emit(RewardedSignal85.CompletedInfoOnly);
            Need(f.api.coins==1250&&f.projectedCoins==1250&&f.api.claimCalls==0&&f.api.reportCalls==0&&f.flow.Receipt==null,"CallbackAloneCannotGrantOrPublishReceipt");
            Need(f.Saved().CompletionReported,"CompletionDurableBeforeAnyReport");provider.Emit(RewardedSignal85.Closed);provider.Emit(RewardedSignal85.Closed);driver.End();
            Need(f.api.coins==1650&&f.projectedCoins==1650&&f.api.grants==1,"OneScripted400ClaimThenProjection");
            Need(f.api.reportCalls==1&&f.api.claimCalls==1&&f.api.reportIds[0]==ids.reportCommandId&&f.api.claimIds[0]==ids.claimCommandId,"ExactDurableReportAndClaimIds");
            Need(!f.flow.Pending&&f.flow.Receipt?.coins==400&&f.refreshes==1&&!File.Exists(f.path),"ReceiptAfterFreshWalletThenJournalResolution");
            provider.Emit(RewardedSignal85.CompletedInfoOnly);Need(f.api.grants==1,"LateDuplicateCompletionNoAdditionalClaim");
        }}
        static void LostClaim(){using(var f=new Fixture("claimLost")){
            f.api.loseClaimOnce=true;var driver=f.Watch();var ids=f.Saved();f.Finish(driver);
            Need(f.api.grants==1&&f.flow.Receipt==null&&f.flow.Pending&&f.Saved().claimCommandId==ids.claimCommandId,"LostClaimReplyKeepsExactPendingIntent");
            f.Open();f.Drive(f.flow.Recover()).End();Need(f.api.grants==1&&f.api.claimCalls==1&&f.providers.Count==1&&f.flow.Receipt?.coins==400&&!f.flow.Pending,"FreshFlowRecoversCommittedClaimWithoutAnotherVideoOrGrant");
        }}
        static void LostReport(bool before){using(var f=new Fixture(before?"reportBefore":"reportAfter")){
            f.api.loseReportBeforeOnce=before;f.api.loseReportAfterOnce=!before;var driver=f.Watch();var ids=f.Saved();f.Finish(driver);
            Need(f.api.grants==0&&f.flow.Pending&&f.flow.Receipt==null,"UnknownReportDoesNotPublishGrant");
            f.Open();f.Drive(f.flow.Recover()).End();
            Need(f.api.reportIds.All(id=>id==ids.reportCommandId)&&f.api.claimIds.SequenceEqual(new[]{ids.claimCommandId}),"ReportRetryAndClaimRetainOriginalIds");
            Need(f.api.reportCalls==(before?2:1)&&f.api.grants==1&&!f.flow.Pending&&f.providers.Count==1,"ReportBeforeAfterCommitRecoveryOnceWithoutReplayAd");
        }}
        static void LostReserve(){using(var f=new Fixture("reserveLost")){
            f.api.loseReserveOnce=true;f.Drive(f.flow.Watch(new AdPrivacy85(true))).End();var ids=f.Saved();
            Need(ids.state=="Reserving"&&f.providers[0].shows==0&&f.api.grants==0,"ReserveUnknownNeverShowsAd");
            f.Open();f.Drive(f.flow.Recover()).End();
            Need(f.api.reserveIds.Count==2&&f.api.reserveIds.All(id=>id==ids.reserveCommandId)&&f.api.cancelIds.Single()==ids.cancelCommandId,"ReserveReplayAndCancellationUseExactDurableIds");
            Need(f.api.grants==0&&!f.flow.Pending&&f.api.opportunity.state=="Cancelled","UnshownRecoveredReservationCancelledWithoutQuotaClaim");
        }}
        static AdReply85<AdOpportunity85> Denial(long status,string code)=>RewardedAdsClient85.ParseReserveDenial(status,"application/json; charset=utf-8","{\"error\":\""+code+"\"}");
        static void ReserveDenialClassifier(){
            string[] conflicts={"ad_cooldown","ad_daily_limit","ad_placement_unavailable","ad_opportunity_pending"};
            string[] unavailable={"ads_disabled","trusted_completion_unavailable"};
            foreach(string code in conflicts.Concat(unavailable)){
                var reply=RewardedAdsClient85.ParseReserveDenial(conflicts.Contains(code)?409:503,"Application/Json; charset=UTF-8","{\"error\":\""+code+"\"}");
                Need(reply!=null&&!reply.Ok&&reply.DefinitiveReserveDenial&&!reply.Unknown&&reply.Value==null&&reply.Error==code,"OnlyExactReserveExecuteDenialClassified_"+code);report.reserveDenialClassifierAccepted++;
            }
            Action<long,string,string> reject=(status,mime,json)=>{Need(RewardedAdsClient85.ParseReserveDenial(status,mime,json)==null,"UnprovenReserveDenialNotClassified");report.reserveDenialClassifierRejected++;};
            foreach(long status in new long[]{0,200,301,400,401,403,408,429,500,502,504})reject(status,"application/json","{\"error\":\"ad_cooldown\"}");
            reject(503,"application/json","{\"error\":\"ad_cooldown\"}");reject(409,"application/json","{\"error\":\"ads_disabled\"}");
            foreach(string code in new[]{"wallet_migration_required","wallet_refund_review_required","invalid_token","account_closed","unknown_error","AD_COOLDOWN","ad_cooldown "})reject(409,"application/json","{\"error\":\""+code+"\"}");
            foreach(string mime in new[]{null,"","text/html","text/plain","application/problem+json"})reject(409,mime,"{\"error\":\"ad_cooldown\"}");
            foreach(string json in new[]{null,"","not json","[]","{\"error\":null}","{\"error\":409}","{\"error\":true}","{\"error\":{}}","{\"error\":\"ad_cooldown\",\"extra\":true}","{\"error\":\"ad_cooldown\",\"error\":\"ad_cooldown\"}","{\"error\":\"ad_cooldown\"}{}"})reject(409,"application/json",json);
            Need(!AdReply85<AdOpportunity85>.Fail("ad_cooldown").DefinitiveReserveDenial&&!AdReply85<AdOpportunity85>.Fail("ad_cooldown",true).DefinitiveReserveDenial,"ErrorTextAndUnknownFlagsCannotFabricateTransportProof");
        }
        static void FreshReserveDenial(long status,string code){using(var f=new Fixture("fresh_"+code)){
            f.api.reserveReply=Denial(status,code);Need(f.api.reserveReply!=null,"TypedDenialFixtureRequired");
            f.Drive(f.flow.Watch(new AdPrivacy85(true))).End();string rejectedId=f.api.reserveIds.Single();
            Need(f.api.statusCalls==1&&f.api.reserveCalls==1&&f.api.opportunity==null,"ReadyStatusCanRaceWithAuthoritativeNoCommitDenial");
            Need(!f.flow.Pending&&!File.Exists(f.path)&&f.flow.Status==null&&f.flow.Error==code&&!f.flow.Busy,"FreshDefinitiveDenialDurablyResolvesEmptyOpportunityIntent");
            Need(f.providers.Count==1&&f.providers[0].loads==0&&f.providers[0].shows==0&&f.providers[0].disposes>0&&f.api.reportCalls==0&&f.api.claimCalls==0&&f.api.cancelCalls==0&&f.api.coins==1250&&f.projectedCoins==1250&&f.flow.Receipt==null,"DenialDoesNotLoadShowCancelOrGrant");
            report.freshReserveDenialsResolved++;
            f.api.reserveReply=null;var next=f.Watch();var ids=f.Saved();
            Need(ids.reserveCommandId!=rejectedId&&f.api.reserveCalls==2,"AProvenRejectedFirstRequestDoesNotLockNextExplicitWatch");
            f.Finish(next);Need(f.api.grants==1&&f.projectedCoins==1650&&!f.flow.Pending,"LaterNewExplicitWatchClaimsExactlyOnce");
        }}
        static void UnprovenReserveDenials(){
            var replies=new[]{AdReply85<AdOpportunity85>.Fail("ad_cooldown"),AdReply85<AdOpportunity85>.Fail("ad_daily_limit",true),AdReply85<AdOpportunity85>.Fail("ads_disabled",true),AdReply85<AdOpportunity85>.Fail("AdsRequestUnavailable",true),AdReply85<AdOpportunity85>.Fail("AdsResponseInvalid",true),AdReply85<AdOpportunity85>.Fail("wallet_refund_review_required",true)};
            for(int i=0;i<replies.Length;i++)using(var f=new Fixture("unproven_"+i)){
                f.api.reserveReply=replies[i];f.Drive(f.flow.Watch(new AdPrivacy85(true))).End();var ids=f.Saved();var bytes=File.ReadAllBytes(f.path);
                Need(f.flow.Pending&&ids.state=="Reserving"&&ids.opportunityId==""&&f.flow.Error==replies[i].Error&&f.api.opportunity==null,"TextOrAmbiguousErrorKeepsEmptyOpportunityIntent");
                Need(f.providers[0].loads==0&&f.providers[0].shows==0&&f.api.grants==0&&f.api.claimCalls==0,"UnprovenDenialCannotShowOrGrant");
                f.Open();f.Drive(f.flow.Recover()).End();
                Need(f.flow.Pending&&f.api.reserveIds.Count==2&&f.api.reserveIds.All(id=>id==ids.reserveCommandId)&&bytes.SequenceEqual(File.ReadAllBytes(f.path))&&f.providers.Count==1,"RestartRetriesExactUnprovenIntentWithoutErasingEvidence");
                report.unprovenReserveDenialsRetained++;
            }
        }
        static void UnknownThenDefinitiveDenial(){
            string[] codes={"ad_cooldown","ad_daily_limit","ads_disabled"};
            foreach(string code in codes)using(var f=new Fixture("unknown_then_"+code)){
                f.api.reserveReply=AdReply85<AdOpportunity85>.Fail("AdsRequestUnavailable",true);f.Drive(f.flow.Watch(new AdPrivacy85(true))).End();var ids=f.Saved();var bytes=File.ReadAllBytes(f.path);
                f.api.reserveReply=Denial(code=="ads_disabled"?503:409,code);Need(f.api.reserveReply?.DefinitiveReserveDenial==true,"RecoveryTypedDenialFixtureRequired");
                f.Open();f.Drive(f.flow.Recover()).End();
                Need(f.flow.Pending&&f.Saved().reserveCommandId==ids.reserveCommandId&&bytes.SequenceEqual(File.ReadAllBytes(f.path))&&f.flow.Error==code,"LaterDefinitiveDenialDoesNotFenceEarlierUnknownRequest");
                f.Drive(f.flow.Watch(new AdPrivacy85(true))).End();
                Need(f.flow.Pending&&f.api.reserveIds.Count==3&&f.api.reserveIds.All(id=>id==ids.reserveCommandId)&&f.providers.Count==1&&f.providers[0].shows==0&&f.api.grants==0,"ExplicitWatchAlsoRecoversUnknownHistoryWithSameIds");
                report.recoveredReserveDenialsRetained++;
                f.api.reserveReply=null;f.Drive(f.flow.Recover()).End();
                Need(f.api.reserveIds.Count==4&&f.api.reserveIds.All(id=>id==ids.reserveCommandId)&&f.api.cancelIds.SequenceEqual(new[]{ids.cancelCommandId})&&!f.flow.Pending&&f.api.opportunity.state=="Cancelled"&&f.api.grants==0,"EventualSameRequestReplyReconcilesWithoutShowingOrGranting");
            }
        }
        static void NoFillAndCancel(){using(var f=new Fixture("noFill")){
            f.loadSuccess=false;f.api.loseCancelOnce=true;f.Drive(f.flow.Watch(new AdPrivacy85(true))).End();var ids=f.Saved();
            Need(f.api.cancelCalls==1&&f.providers[0].shows==0&&f.api.reportCalls==0&&f.api.grants==0,"NoFillOnlyCancelsReservation");
            f.Open();f.Drive(f.flow.Recover()).End();Need(f.api.cancelIds.All(id=>id==ids.cancelCommandId)&&f.api.cancelCalls==2&&!f.flow.Pending&&f.api.grants==0,"UnknownCancelRecoveredWithSameCommandNoClaim");
        }}
        static void IncompleteAndQuota(){using(var f=new Fixture("incomplete")){
            var driver=f.Watch();f.providers[0].Emit(RewardedSignal85.CompletedInfoOnly);f.providers[0].Emit(RewardedSignal85.Closed);driver.End();
            Need(f.api.reportCalls==0&&f.api.claimCalls==0&&f.api.cancelCalls==1&&f.api.coins==1250&&!f.flow.Pending,"CompletionWithoutShownIsNotAccepted");
        }using(var f=new Fixture("quota")){
            f.api.available=false;f.Drive(f.flow.Watch(new AdPrivacy85(true))).End();
            Need(f.api.reserveCalls==0&&f.providers.Count==0&&f.api.grants==0&&f.flow.Error=="daily_limit"&&!File.Exists(f.path),"QuotaDenialCreatesNoProviderReservationOrGrant");
        }using(var f=new Fixture("privacy")){
            f.Drive(f.flow.Watch(new AdPrivacy85(false))).End();Need(f.api.statusCalls==0&&f.providers.Count==0&&!f.flow.Busy,"MissingExplicitConsentMakesNoRequest");
        }}
        static void WalletRefresh(){using(var f=new Fixture("wallet")){
            f.failRefreshOnce=true;var driver=f.Watch();f.Finish(driver);
            Need(f.api.grants==1&&f.projectedCoins==1250&&f.flow.Receipt==null&&f.flow.Pending,"ClaimedButWalletUnavailableKeepsReceiptHidden");
            f.Open();f.Drive(f.flow.Recover()).End();Need(f.projectedCoins==1650&&f.flow.Receipt?.coins==400&&f.api.grants==1&&f.refreshes==2,"ReceiptAppearsOnlyAfterSuccessfulFreshProjection");
        }}
        static void DiskBeforeCommit(){using(var f=new Fixture("diskBefore")){
            bool armed=true;f.journal.VerificationCheckpoint=step=>{if(armed&&step=="BeforeCommit"){armed=false;throw new IOException();}};
            f.Drive(f.flow.Watch(new AdPrivacy85(true))).End();
            Need(f.api.reserveCalls==0&&f.api.reportCalls==0&&f.api.grants==0&&f.providers.All(p=>p.shows==0)&&!f.flow.Busy,"DiskFailureBeforeIntentPreventsAnyMutationOrVideo");
            Need(f.flow.Error=="AdsRecoveryRequired"&&!File.Exists(f.path),"GuardSurfacesStorageFaultWithoutFabricatingDurability");
        }}
        static void DiskLostAck(){using(var f=new Fixture("diskAfter")){
            var driver=f.Watch();f.providers[0].Emit(RewardedSignal85.Shown);bool armed=true;
            f.journal.VerificationCheckpoint=step=>{if(armed&&step=="AfterCommit"){armed=false;throw new IOException();}};
            f.providers[0].Emit(RewardedSignal85.CompletedInfoOnly);f.providers[0].Emit(RewardedSignal85.Closed);driver.End();
            Need(f.Saved().CompletionReported&&f.api.reportCalls==0&&f.api.claimCalls==0&&f.api.grants==0,"LostDiskAcknowledgementDoesNotSendUnconfirmedMutation");
            f.Open();f.Drive(f.flow.Recover()).End();Need(f.api.grants==1&&f.flow.Receipt?.coins==400&&!f.flow.Pending,"ReopenedActualJournalRecoversDurableCompletion");
        }}
        static void DiskCompletionRetry(){using(var f=new Fixture("completionBefore")){
            var driver=f.Watch();var ids=f.Saved();f.providers[0].Emit(RewardedSignal85.Shown);bool armed=true;
            f.journal.VerificationCheckpoint=step=>{if(armed&&step=="BeforeCommit"){armed=false;throw new IOException();}};
            f.providers[0].Emit(RewardedSignal85.CompletedInfoOnly);f.providers[0].Emit(RewardedSignal85.Closed);driver.End();
            Need(!f.Saved().CompletionReported&&f.api.reportCalls==0&&f.api.claimCalls==0&&f.api.grants==0&&f.flow.Pending,"CompletionBeforeCommitFaultDoesNotSendOrClaim");
            f.journal.VerificationCheckpoint=null;
            f.api.beforeRead=()=>{var saved=f.Saved();Need(saved.CompletionReported&&saved.state=="CompletionReported"&&saved.reserveCommandId==ids.reserveCommandId&&saved.reportCommandId==ids.reportCommandId&&saved.claimCommandId==ids.claimCommandId&&saved.cancelCommandId==ids.cancelCommandId,"SameProcessCompletionRepairedDurablyBeforeServerRead");};
            f.Drive(f.flow.Recover()).End();Need(f.api.grants==1&&f.api.cancelCalls==0&&f.api.reportIds.SequenceEqual(new[]{ids.reportCommandId})&&f.api.claimIds.SequenceEqual(new[]{ids.claimCommandId})&&f.providers.Count==1&&f.flow.Receipt?.coins==400&&!f.flow.Pending,"TransientCompletionWriteRetryKeepsExactIntentAndClaimsOnce");
        }}
        static void FinalResolutionFailure(bool clear){using(var f=new Fixture(clear?"finalClear126":"finalCommit126")){
            var driver=f.Watch();var ids=f.Saved();bool armed=true;
            f.journal.VerificationCheckpoint=step=>{if(armed&&f.api.grants==1&&step==(clear?"BeforeClear":"BeforeCommit")){armed=false;throw new IOException("ControlledFinalResolutionFailure126");}};
            f.Finish(driver);
            Need(f.api.grants==1&&f.projectedCoins==1650&&f.flow.Receipt==null&&f.flow.Pending,"FinalJournalFailureCannotPublishCollectionFeedback");
            Need(f.Saved().state==(clear?"Resolved":"Claiming")&&f.Saved().claimCommandId==ids.claimCommandId,"FinalFailureRetainsExactRecoverableClaimIntent");
            f.Open();f.Drive(f.flow.Recover()).End();
            Need(f.api.grants==1&&f.api.claimCalls==1&&f.providers.Count==1&&!f.flow.Pending&&f.flow.Receipt?.id==f.api.opportunity.receipt.id,"FinalResolutionRecoveryUsesSameClaimAndReceiptWithoutAnotherAd");
        }}
        static void LostClearAcknowledgement(){using(var f=new Fixture("clearAck126")){
            var driver=f.Watch();bool armed=true;f.journal.VerificationCheckpoint=step=>{if(armed&&step=="AfterClear"){armed=false;throw new IOException("ControlledLostClearAcknowledgement126");}};
            f.Finish(driver);
            Need(!File.Exists(f.path)&&!f.flow.Pending&&f.flow.Receipt?.coins==400&&f.api.grants==1,"ActualMissingJournalConfirmsClearBeforePublishingReceipt");
        }}
        static void Corruption(){using(var f=new Fixture("corrupt")){
            File.WriteAllText(f.path,"{\"corrupted\":true}");var before=File.ReadAllBytes(f.path);
            f.Drive(f.flow.Refresh()).End();Need(f.flow.Error=="AdJournalCorrupt"&&f.api.statusCalls==0&&f.api.reserveCalls==0&&before.SequenceEqual(File.ReadAllBytes(f.path)),"CorruptJournalFailsClosedBeforeHttpAndRemainsIntact");
        }}
        static void MissingJournalServerCompletion(bool verified){using(var f=new Fixture(verified?"serverVerified":"serverReported")){
            f.api.opportunity=new AdOpportunity85{opportunityId="88888888888888888888888888888888",playerId=Player,state=verified?"Verified":"CompletedReported",placement="shop_rewarded",configVersion="fixture85",rewardCoins=400,dailyLimit=3,utcOffsetSeconds=36000,cooldownSeconds=600,completionMode=verified?"trusted_completion":"sdk_client_reported_capped",completionAuthoritative=verified};
            f.Drive(f.flow.Refresh()).End();Need(f.flow.Pending&&f.providers.Count==0,"ServerOwnedCompletionDiscoveredWithoutShowingAnotherAd");
            f.api.beforeClaim=()=>{var saved=f.Saved();Need(saved.CompletionReported&&saved.state=="Claiming","CanonicalServerCompletionAdoptedDurablyBeforeClaim");};
            f.Drive(f.flow.Recover()).End();Need(f.api.grants==1&&f.api.claimCalls==1&&f.api.reportCalls==0&&f.api.cancelCalls==0&&!f.flow.Pending&&f.flow.Receipt?.coins==400,"MissingJournalCanonicalCompletionClaimsWithoutCancelOrSdkReplay");
        }}
        static void ExpiredAccessDuringPresentation(){using(var f=new Fixture("expiredAccess")){
            var driver=f.Watch();var ids=f.Saved();f.access=false;
            f.providers[0].Emit(RewardedSignal85.Shown);f.providers[0].Emit(RewardedSignal85.CompletedInfoOnly);
            Need(f.Saved().CompletionReported&&f.api.reportCalls==0&&f.api.claimCalls==0&&f.api.grants==0&&f.flow.Presenting,"ExpiredAccessDoesNotEraseOwnedSdkCompletionOrGrant");
            f.renewOnAuthorize=true;f.providers[0].Emit(RewardedSignal85.Closed);driver.End();
            Need(f.access&&f.authorizations>=2&&f.api.reportIds.SequenceEqual(new[]{ids.reportCommandId})&&f.api.claimIds.SequenceEqual(new[]{ids.claimCommandId})&&f.api.grants==1&&f.projectedCoins==1650&&f.flow.Receipt?.coins==400&&!f.flow.Pending,"ExplicitPostAdAuthorizationRenewsBeforeSingleClaim");
        }}
        static void StaleOwnerAndUnwind(){using(var f=new Fixture("stale")){
            var oldDriver=f.Watch();var old=f.providers[0];f.access=false;f.flow.Invalidate();old.Emit(RewardedSignal85.Shown);old.Emit(RewardedSignal85.CompletedInfoOnly);
            Need(!f.Saved().CompletionReported&&f.api.reportCalls==0&&f.api.grants==0,"OldOwnerCallbacksCannotMarkCompletion");
            f.access=true;f.Drive(f.flow.Recover()).End();Need(!f.flow.Pending&&f.api.cancelCalls==1,"OldReservationExplicitlyReconciledBeforeNewWatch");
            var current=f.Watch();var active=f.providers[1];oldDriver.End();
            Need(active.disposes==0&&f.flow.Busy&&f.flow.Presenting,"OldGuardUnwindCannotDisposeOrUnlockNewOperation");
            old.Emit(RewardedSignal85.CompletedInfoOnly);Need(!f.Saved().CompletionReported,"OldCallbackCannotChangeNewIntent");
            f.Finish(current);Need(f.api.grants==1&&f.flow.Receipt?.coins==400&&!f.flow.Busy,"NewOwnerOperationCompletesAfterOldCoroutineUnwind");
        }}
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,status="FAIL_NATIVE_REWARDED_ADS_FLOW85"};
            string workspace=Directory.GetParent(Directory.GetParent(Application.dataPath).FullName).FullName;
            directory=Path.Combine(workspace,".verification-cache","Ads85","FlowNative",Guid.NewGuid().ToString("N"));Directory.CreateDirectory(directory);
            try{
                Need(Application.unityVersion=="2022.3.62f3","PinnedEditorRequired");
                Case("CompletionAndDuplicates",Success);Case("ClaimReplyLostAcrossFreshFlow",LostClaim);
                Case("ReportReplyLostBeforeCommit",()=>LostReport(true));Case("ReportReplyLostAfterCommit",()=>LostReport(false));
                Case("ReserveReplyLostAcrossFreshFlow",LostReserve);Case("NoFillAndUnknownCancellation",NoFillAndCancel);
                Case("ReserveDenialStrictClassifier",ReserveDenialClassifier);
                Case("FreshReserveCooldownDenialResolves",()=>FreshReserveDenial(409,"ad_cooldown"));
                Case("FreshReserveDailyLimitDenialResolves",()=>FreshReserveDenial(409,"ad_daily_limit"));
                Case("FreshReservePlacementDenialResolves",()=>FreshReserveDenial(409,"ad_placement_unavailable"));
                Case("FreshReserveOpportunityPendingDenialResolves",()=>FreshReserveDenial(409,"ad_opportunity_pending"));
                Case("FreshReserveDisabledDenialResolves",()=>FreshReserveDenial(503,"ads_disabled"));
                Case("FreshReserveUnconfiguredTrustedDenialResolves",()=>FreshReserveDenial(503,"trusted_completion_unavailable"));
                Case("UnprovenReserveDenialsRetainExactIntent",UnprovenReserveDenials);
                Case("UnknownReserveThenDefinitiveDenialRetainsExactIntent",UnknownThenDefinitiveDenial);
                Case("IncompleteQuotaAndConsent",IncompleteAndQuota);Case("WalletBeforeReceipt",WalletRefresh);
                Case("DiskBeforeCommit",DiskBeforeCommit);Case("DiskAfterCommitAcknowledgement",DiskLostAck);
                Case("SameProcessCompletionBeforeCommitRetry",DiskCompletionRetry);
                Case("FinalResolvedCommitFailureHidesFeedback",()=>FinalResolutionFailure(false));Case("FinalClearFailureRecoversSameReceipt",()=>FinalResolutionFailure(true));Case("LostClearAcknowledgementConfirmedByRead",LostClearAcknowledgement);
                Case("DiskCorruptionFailsClosed",Corruption);Case("StaleOwnerAndInterleavedUnwind",StaleOwnerAndUnwind);
                Case("MissingJournalServerReportedCompletion",()=>MissingJournalServerCompletion(false));Case("MissingJournalServerVerifiedCompletion",()=>MissingJournalServerCompletion(true));
                Case("AccessExpiryDuringExternalAdPresentation",ExpiredAccessDuringPresentation);
                if(report.errors.Count==0)report.status="PASS_NATIVE_REWARDED_ADS_FLOW85";
            }catch(Exception error){report.errors.Add(error.GetType().Name);}
            string output=Environment.GetEnvironmentVariable("HOTR_ADS85_OUTPUT");if(string.IsNullOrEmpty(output))output=Path.Combine(workspace,"Verification","Evidence","ShopAds85");
            output=Path.Combine(output,"Native");Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"RewardedAdsFlow85.json"),JsonUtility.ToJson(report,true));
            if(Application.isBatchMode)EditorApplication.Exit(report.status.StartsWith("PASS_",StringComparison.Ordinal)?0:1);
        }
    }
}
#endif

#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using HeartOfTheRain.App.Advertising;

using HeartOfTheRain.App.Leaderboard;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.ServerRewards;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.Verification {
    // Review 136 client fixes, with scripted transports and real disk journals.
    // No HTTP, SDK, device or ad proof: those stay with the connected suites.
    public static class ClientFixes136Verification {
        [Serializable] sealed class Report {public string status="FAIL_NATIVE_CLIENT_FIXES136",utc,unity,error;public int checks;public List<string> passed=new List<string>();}
        const string Origin="http://127.0.0.1:18585",Player="11111111111111111111111111111111",Team="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic|BindingFlags.Public;
        static Report report;static string root;
        static void Need(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);}
        static void Passed(string label){report.passed.Add(label);}

        // ---- final refusals on durable social writes
        sealed class MemoryStore:IProtectedSessionStore82 {
            byte[] data;public bool failNext;
            public byte[] Read()=>data==null?null:(byte[])data.Clone();
            public void CompareExchange(string expected,byte[] replacement){if(failNext){failNext=false;throw new InvalidOperationException("SyntheticFailure136");}if((data==null||data.Length==0?"":IdentityProtocol82.Sha(data))!=expected)throw new InvalidOperationException("SyntheticConflict136");data=(byte[])replacement.Clone();}
            public void Dispose(){}
        }
        sealed class Social {
            public readonly MemoryStore store=new MemoryStore();public SocialBackendClient82 client;public SocialPageSession82 session;
            public string mode="ok",refusal,error;public int exchanges;public bool failClear;
            public Social(){var access=new SocialAccess82(Player,IdentityProtocol82.NewSecret());client=new SocialBackendClient82(Origin,()=>access,Dispatch,store,true,true);session=new SocialPageSession82(client,null,()=>1,()=>0);}
            void Dispatch(IEnumerator exchange){
                exchanges++;var pending=typeof(SocialBackendClient82).GetField("active",Private).GetValue(client);string json=null,reply=null;bool unknown=false;
                if(mode=="refuse"){reply=error;pending.GetType().GetField("refusal",Private).SetValue(pending,refusal);if(failClear)store.failNext=true;}
                else if(mode=="lost"){reply="SocialNetworkUnavailable";unknown=true;}
                else json="{\"teamId\":\""+Team+"\",\"state\":\"Joined\"}";
                typeof(SocialBackendClient82).GetMethod("Complete",Private).Invoke(client,new[]{pending,json,reply,(object)unknown});
                pending.GetType().GetMethod("Release",Private).Invoke(pending,null);(exchange as IDisposable)?.Dispose();
            }
            public bool Join()=>session.JoinTeam(Guid.NewGuid().ToString("N"),Team);
        }
        static void SocialRefusals(){
            foreach(long status in new long[]{400,403,404,409,422,429})Need(SocialBackendClient82.FinalRefusal(status),"A rule answer is final: "+status);
            foreach(long status in new long[]{0,200,401,410,500,503})Need(!SocialBackendClient82.FinalRefusal(status),"Not a final refusal: "+status);
            Need(SocialBackendClient82.RefusalCode(409,"{\"error\":\"team_full\"}")=="team_full","The server code is carried");
            Need(SocialBackendClient82.RefusalCode(429,"not json")=="rate_limited"&&SocialBackendClient82.RefusalCode(404,null)=="refused","A body without a code still refuses");
            Need(SocialBackendClient82.RefusalCode(409,"{\"error\":\"<b>x</b>\"}")=="refused","A code outside the safe form is not trusted");
            var f=new Social();f.mode="refuse";f.error="SocialHttp409";f.refusal="team_full";Need(f.Join(),"The write is sent");
            Need(f.session.PendingCommand==null,"A refused write leaves nothing in the outbox");
            var status2=f.session.Status(SocialPane82.Teams);Need(status2.state==SocialViewState82.Rejected&&status2.reason=="team_full","The pane keeps the server's reason");
            Need(OnlineTeamsText82.Status(status2)==OnlineTeamsText82.T("RefusedTeamFull"),"The player sees the mapped reason");
            Need(f.session.TakeWriteRefusal()=="team_full"&&f.session.TakeWriteRefusal()==null,"The refusal is reported once");
            int before=f.exchanges;f.mode="ok";Need(f.Join()&&f.exchanges==before+1&&f.session.PendingCommand==null,"The next write is not blocked");
            f.mode="refuse";f.error="SocialHttp429";f.refusal="message_rate_limited";Need(f.Join()&&f.session.PendingCommand==null,"A rate limit also clears");
            Need(f.session.Status(SocialPane82.Teams).state==SocialViewState82.Rejected&&OnlineTeamsText82.Status(f.session.Status(SocialPane82.Teams))==OnlineTeamsText82.T("RefusedShortly"),"A rate limit says try again shortly, not offline");
            f.mode="lost";Need(f.Join()&&f.session.PendingCommand!=null&&f.session.Status(SocialPane82.Teams).state==SocialViewState82.CommitUnknown,"A lost reply stays unknown and pending");
            f.session.TakeWriteRefusal();
            f.mode="refuse";f.error="SocialHttp409";f.refusal="team_full";Need(f.session.ResumePending()&&f.session.PendingCommand==null,"Retry of an old stuck intent clears on refusal");
            var g=new Social();g.mode="refuse";g.error="SocialHttp409";g.refusal="team_full";g.failClear=true;Need(g.Join()&&g.session.PendingCommand!=null,"A clear that fails to save keeps the intent");
            Need(g.session.Status(SocialPane82.Teams).state==SocialViewState82.CommitUnknown,"An unsaved clear is reported as unknown");
            int locale=GameLocale.Current;
            try{
                foreach(int n in Enumerable.Range(0,5)){GameLocale.Select(n);foreach(string code in new[]{"rate_limited","message_rate_limited","team_full","already_in_team","life_help_unavailable","life_request_cooldown","life_claim_unavailable","friend_request_unavailable","friend_limit","incoming_friend_request_exists","invalid_text","anything_else"}){string text=OnlineTeamsText82.Refusal(code);Need(!string.IsNullOrEmpty(text)&&!text.StartsWith("Refused",StringComparison.Ordinal)&&!text.Contains("?"),"Refusal text exists in locale "+n+": "+code);if(n==4)Need(text.Any(c=>c>=0x400&&c<=0x4FF),"Russian text is Russian: "+code);}}
            }finally{GameLocale.Select(locale);}
            Passed("Final social refusals clear the outbox, carry their reason and unblock the next write; unknown stays pending");
        }
        static void TeamsBack(){
            Func<bool,bool,bool,bool,bool,bool,int,string> back=OnlineTeamsPage82.BackAction136;
            Need(back(true,true,true,true,true,true,1)=="cancel","A dialog closes first");
            Need(back(false,true,false,false,false,false,0)=="mail-owned-close","Saved mail returns to Teams");
            Need(back(false,false,true,false,false,false,0)=="close-saved-lives","Saved lives returns to Teams");
            Need(back(false,false,false,true,false,false,0)=="tab-chat","Mail returns to Chat");
            Need(back(false,false,false,false,true,false,1)=="close-details","Team details return to the list");
            Need(back(false,false,false,false,false,true,1)=="access-find","Create returns to Find");
            Need(back(false,false,false,false,false,false,1)=="tab-chat"&&back(false,false,false,false,false,false,2)=="tab-chat","Info and Ranks return to Chat");
            Need(back(false,false,false,false,false,false,0)==null,"Only the base view leaves the page");
            Passed("Android Back steps out of Teams sub-views");
        }

        // ---- rewarded flow
        sealed class Api:IRewardedAdsApi85 {
            public AdOpportunity85 opportunity;public int grants,cancels,reports;public bool failStatus;
            static IEnumerator Now(Action a){a();yield break;}
            AdOpportunity85 Copy()=>JsonUtility.FromJson<AdOpportunity85>(JsonUtility.ToJson(opportunity));
            public IEnumerator Status(ServerAuthorizedContext a,Action<AdReply85<AdStatus85>> done)=>Now(()=>done(failStatus?AdReply85<AdStatus85>.Fail("ScriptedNoStatus"):AdReply85<AdStatus85>.Success(new AdStatus85{enabled=true,available=true,reason="ready",dailyLimit=3,remainingToday=3})));
            public IEnumerator Reserve(ServerAuthorizedContext a,string id,Action<AdReply85<AdOpportunity85>> done)=>Now(()=>{opportunity=new AdOpportunity85{opportunityId=new string('c',32),state="Reserved",playerId=Player};done(AdReply85<AdOpportunity85>.Success(Copy()));});
            public IEnumerator Read(ServerAuthorizedContext a,string id,Action<AdReply85<AdOpportunity85>> done)=>Now(()=>done(AdReply85<AdOpportunity85>.Success(Copy())));
            public IEnumerator Report(ServerAuthorizedContext a,string id,string command,Action<AdReply85<AdOpportunity85>> done)=>Now(()=>{reports++;opportunity.state="CompletedReported";done(AdReply85<AdOpportunity85>.Success(Copy()));});
            public IEnumerator Claim(ServerAuthorizedContext a,string id,string command,Action<AdReply85<AdOpportunity85>> done)=>Now(()=>{grants++;opportunity.state="Claimed";opportunity.receipt=new AdReceipt85{id="rewarded-ad/"+id,coins=400};done(AdReply85<AdOpportunity85>.Success(Copy()));});
            public IEnumerator Cancel(ServerAuthorizedContext a,string id,string command,Action<AdReply85<AdOpportunity85>> done)=>Now(()=>{cancels++;opportunity.state="Cancelled";done(AdReply85<AdOpportunity85>.Success(Copy()));});
        }
        sealed class Provider:IRewardedAdsProvider85 {
            public bool loadNow=true;public int shows;public Action<RewardedSignal85> signal;
            public bool Installed=>true;public void Load(Action<bool,string> complete){if(loadNow)complete(true,null);}
            public void Show(Action<RewardedSignal85> value){shows++;signal=value;}public void Dispose(){}
        }
        sealed class Flow {
            public readonly Api api=new Api();public readonly Provider provider=new Provider();public RewardedAdsFlow85 flow;public bool focused=true;IEnumerator routine;
            static IEnumerator Now(Action a){a();yield break;}
            public Flow(string name){
                var context=(ServerAuthorizedContext)Activator.CreateInstance(typeof(ServerAuthorizedContext),BindingFlags.Instance|BindingFlags.NonPublic,null,new object[]{Origin,Player,1L,true,new Func<string>(()=>"scripted-in-memory-access")},null);
                flow=new RewardedAdsFlow85(api,new RewardedAdsJournal85(Path.Combine(root,name,"intent.json")),done=>Now(()=>done(context,null)),done=>Now(()=>done(true,null)),privacy=>provider,()=>focused);
            }
            public void Watch(){routine=flow.Guard(flow.Watch(new AdPrivacy85(true)));}
            public void Refresh(){routine=flow.Guard(flow.Refresh());}
            public void Tick(int count=1){for(int i=0;i<count;i++)routine.MoveNext();}
            public void Until(Func<bool> stop){for(int i=0;i<256&&!stop();i++)routine.MoveNext();Need(stop(),"Scripted flow reaches its state");}
        }
        static void RewardedFocus(){
            var a=new Flow("closed");a.flow.ResumeCloseSeconds=0;a.Watch();a.Until(()=>a.provider.shows==1);a.Tick(2);Need(a.flow.Presenting,"The ad stays up while the game keeps focus briefly");
            a.focused=false;a.Tick(64);Need(a.flow.Presenting,"No timer closes an ad while the game is out of focus");
            a.provider.signal(RewardedSignal85.Shown);a.focused=true;a.Until(()=>!a.flow.Busy);
            Need(!a.flow.Presenting&&a.api.cancels==1&&a.api.grants==0&&a.flow.Error=="AdsNotCompleted","Back in focus with no close report ends the wait and grants nothing");
            var b=new Flow("completed");b.flow.ResumeCloseSeconds=0;b.Watch();b.Until(()=>b.provider.shows==1);b.focused=false;b.Tick();b.provider.signal(RewardedSignal85.Shown);b.provider.signal(RewardedSignal85.CompletedInfoOnly);b.focused=true;b.Until(()=>!b.flow.Busy);
            Need(b.api.reports==1&&b.api.grants==1&&b.flow.Receipt?.coins==400&&b.api.cancels==0,"A reported completion still claims once when the close report is lost");
            var c=new Flow("neverleft");c.flow.ShowCloseSeconds=0;c.Watch();c.Tick();c.Until(()=>!c.flow.Busy);Need(c.provider.shows==1&&c.api.cancels==1&&c.api.grants==0,"An ad that never took focus does not hold the page");
            var d=new Flow("suspend");d.flow.ShowCloseSeconds=1000;d.flow.ResumeCloseSeconds=1000;d.Watch();d.Until(()=>d.provider.shows==1);d.Tick();System.Threading.Thread.Sleep(1100);d.flow.ShowCloseSeconds=0;d.Tick(3);Need(d.flow.Presenting,"Returning from a suspend counts as leaving, so the resume delay applies");d.flow.Dispose();
            var e=new Flow("back");e.provider.loadNow=false;e.Watch();e.Until(()=>e.flow.LoadingAd);e.flow.CancelLoad();e.Until(()=>!e.flow.Busy);
            Need(e.provider.shows==0&&e.api.cancels==1&&e.flow.Error==null&&!e.flow.LoadingAd&&!e.flow.Pending,"Back during load cancels the reservation with no error");
            var g=new Flow("read");g.api.failStatus=true;g.Refresh();g.Tick();g.Until(()=>!g.flow.Busy);Need(g.flow.ReadFailed&&!g.flow.Reading,"A failed read is known and does not stay Reading");
            g.api.failStatus=false;g.Refresh();g.Tick();g.Until(()=>!g.flow.Busy);Need(!g.flow.ReadFailed&&g.flow.Status!=null,"The next read clears it");
            Passed("Rewarded wait ends on a lost close report, never grants without completion, and Back cancels a load");
        }
        static void RewardedWording(){
            Func<AdCardState85,AdShopView85> card=AdShopView85.Build;
            Need(card(new AdCardState85()).action=="disabled","No host stays unavailable");
            var ready=new AdStatus85{enabled=true,available=true,reason="ready",dailyLimit=3,remainingToday=3};
            Need(card(new AdCardState85{present=true,installed=true,busy=true,reading=true}).message==AdText85.T("checking"),"Opening Shop says checking, not a pending reward");
            Need(card(new AdCardState85{present=true,installed=true,busy=true,loading=true,pending=true}).message==AdText85.T("loading"),"A loading video says so");
            Need(card(new AdCardState85{present=true,installed=true,busy=true,pending=true}).message==AdText85.T("pending"),"A real pending reward keeps its wording");
            var failed=card(new AdCardState85{present=true,installed=true,ready=true,readFailed=true,status=ready,error="AdsStatusUnavailable"});
            Need(failed.message==AdText85.T("checkFailed")&&failed.action=="ad:retry"&&failed.message!=AdText85.T("failed"),"A failed read says it could not check and offers a retry");
            Need(card(new AdCardState85{present=true,installed=true,ready=true,idle=true,status=ready}).action=="ad:watch","An idle ready status can watch");
            var blocked=card(new AdCardState85{present=true,installed=true,ready=true,idle=false,status=ready});Need(blocked.action=="disabled"&&blocked.message==AdText85.T("blocked"),"A blocked Watch says why instead of doing nothing");
            var cooling=new AdStatus85{enabled=true,reason="cooldown",nextEligibleAt=1000,nextDayAt=5000,dailyLimit=3,remainingToday=2};
            string clock=card(new AdCardState85{present=true,installed=true,ready=true,idle=true,status=cooling,now=488}).message;Need(clock.Contains("8:32"),"The cooldown counts down: "+clock);
            Need(card(new AdCardState85{present=true,installed=true,ready=true,idle=true,status=cooling,now=1000}).message==AdText85.T("checking"),"A passed cooldown is rechecked");
            Need(card(new AdCardState85{present=true,installed=true,ready=true,idle=true,status=cooling}).message==AdText85.T("cooldown"),"With no server time the plain cooldown text remains");
            Need(AdShopView85.Expired(cooling,1000)&&!AdShopView85.Expired(cooling,999)&&!AdShopView85.Expired(cooling,0)&&!AdShopView85.Expired(null,1000),"Cooldown expiry follows server time");
            var limit=new AdStatus85{enabled=true,reason="daily_limit",nextEligibleAt=1000,nextDayAt=5000,dailyLimit=3,remainingToday=0};
            Need(AdShopView85.Expired(limit,5000)&&!AdShopView85.Expired(limit,4999),"The daily limit expires at the next day");
            bool eligible;
            Need(AdShopView85.HomePlate(false,true,false,false,false,ready,10,out eligible)==""&&!eligible,"Hidden shortcut has no plate");
            Need(AdShopView85.HomePlate(true,true,false,false,false,ready,10,out eligible)=="Ready"&&eligible,"Ready plate");
            Need(AdShopView85.HomePlate(true,true,false,false,true,ready,10,out eligible)=="-"&&!eligible,"A failed read is never Ready");
            Need(AdShopView85.HomePlate(true,true,false,false,false,null,10,out eligible)=="-","No status is a dash");
            Need(AdShopView85.HomePlate(true,true,false,false,false,cooling,999,out eligible)=="Later"&&AdShopView85.HomePlate(true,true,false,false,false,cooling,1000,out eligible)=="...","Later ends when the cooldown does");
            Need(AdShopView85.HomePlate(true,true,false,false,false,limit,4999,out eligible)=="0/3"&&AdShopView85.HomePlate(true,true,false,false,false,limit,5000,out eligible)=="...","The daily count ends at the next day");
            int locale=GameLocale.Current;
            try{foreach(int n in Enumerable.Range(0,5)){GameLocale.Select(n);foreach(string key in new[]{"checking","checkFailed","loading","blocked","cooldownIn"}){string text=AdText85.T(key);Need(text!=key&&text.Length>3,"Card text exists: "+key);if(key=="cooldownIn")Need(string.Format(text,"1:00").Contains("1:00"),"Countdown slot exists");}}}
            finally{GameLocale.Select(locale);}
            Passed("Video card and Home plate wording follow the real state and server time");
        }

        // ---- journals and refused rewards
        static void Journals(){
            foreach(long status in new long[]{400,403,404,409,422})Need(ServerRewardsCoordinator.FinalRefusal(status,"cup_locked"),"Reward refusal is final: "+status);
            foreach(long status in new long[]{0,401,429,500,503})Need(!ServerRewardsCoordinator.FinalRefusal(status,"x"),"Not final for a reward: "+status);
            Need(!ServerRewardsCoordinator.FinalRefusal(409,"attempt_active"),"An active attempt only delays a reward");
            string rewards=Path.Combine(root,"rewards","rewards.json");var journal=new ServerRewardJournal(rewards,Origin,Player);var doc=journal.Read();doc=journal.Save(doc);doc=journal.Save(doc);Need(doc.revision==2&&File.Exists(rewards+".bak"),"Two saves leave a backup");
            File.WriteAllText(rewards,"{}");var restored=journal.Read();Need(restored.revision==1&&File.Exists(rewards+".corrupt"),"A damaged reward journal falls back to its backup");
            restored=journal.Save(restored);Need(restored.revision==2,"Saving works after the fallback");
            File.WriteAllText(rewards,"{}");File.WriteAllText(rewards+".bak","not json");var empty=journal.Read();Need(empty.revision==0&&!empty.hasPending&&!File.Exists(rewards),"With both damaged it starts empty");
            empty=journal.Save(empty);Need(empty.revision==1,"Saving works after the rebuild");
            bool refused=false;try{new ServerRewardJournal(rewards,Origin,new string('2',32)).Read();}catch(Exception){refused=true;}Need(refused,"Another account's file stays refused");
            string attempt=Path.Combine(root,"attempt","attempt.json");var journal2=new ServerAttemptJournal(attempt,Origin,Player);var value=journal2.Read();value=journal2.Save(value);value=journal2.Save(value);Need(File.Exists(attempt+".bak"),"Attempt backup exists");
            File.WriteAllText(attempt,"{}");var rebuilt=journal2.Read();Need(rebuilt.revision==0&&!rebuilt.hasPending&&!rebuilt.hasAttempt&&File.Exists(attempt+".corrupt")&&!File.Exists(attempt+".bak"),"A damaged attempt journal starts empty and never uses its backup");
            Need(journal2.Save(rebuilt).revision==1,"Saving works after the attempt rebuild");
            refused=false;try{new ServerAttemptJournal(attempt,Origin,new string('2',32)).Read();}catch(Exception){refused=true;}Need(refused,"Another account's attempt stays refused");
            string pending=Path.Combine(root,"pending");var coordinator=new ServerRewardsCoordinator(pending,done=>null,done=>null);Need(!coordinator.LocalPending(Origin,Player),"No file means nothing to recover, with no network");
            Passed("Refused rewards clear, journals recover from damage, and idle Home reads only the local journal");
        }
        static void Identity(){
            Need(IdentityHttpTransport82.FailureCode(401,"{\"error\":\"invalid_identity_session\"}")==IdentityHttpTransport82.SessionRefused,"A dead session is terminal");
            Need(IdentityHttpTransport82.FailureCode(401,"{\"error\":\"refresh_reuse_detected\"}")==IdentityHttpTransport82.SessionRefused,"A reused token is terminal");
            Need(IdentityHttpTransport82.FailureCode(401,"{\"error\":\"invalid_identity_proof\"}")=="IdentityHttp401","A failed proof stays retryable");
            Need(IdentityHttpTransport82.FailureCode(401,"{\"error\":\"invalid_identity_recovery\"}")=="IdentityHttp401","Recovery keeps its own code");
            Need(IdentityHttpTransport82.FailureCode(401,null)=="IdentityHttp401"&&IdentityHttpTransport82.FailureCode(0,null)=="IdentityNetworkUnavailable"&&IdentityHttpTransport82.FailureCode(503,"{}")=="IdentityHttp503","Other failures are unchanged");
            Passed("Only a terminal session refusal stops retries");
        }
        static void Art(){
            var daily=DailyGiftDesignAssets.Load();Need(daily,"Daily art loads");var owned=daily.OwnedArt;
            foreach(var shared in new[]{daily.chrome,daily.close,daily.primary,daily.check,daily.star,daily.coin})Need(!owned.Contains(shared),"Art other pages use is not released: "+(shared?shared.name:"none"));
            Need(owned.All(s=>s)&&owned.Length==10,"Owned art is bound");
            var leaderboard=AssetDatabase.LoadAssetAtPath<LeaderboardAssets>("Assets/HeartOfTheRain/App/Leaderboard/LeaderboardAssets.asset");
            Need(leaderboard&&!leaderboard.sprites.Any(s=>s.id.StartsWith("Portrait_",StringComparison.Ordinal)),"Review portraits have no serialized player-build edge");
            Need(leaderboard.Find("Portrait_Ivan_R2"),"Editor review still resolves its portraits");
            Passed("Reward art release leaves shared sprites alone; review portraits are Editor only");
        }
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};root=Path.GetFullPath("../.verification-cache/Review136/Client/"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(root);
            try{SocialRefusals();TeamsBack();RewardedFocus();RewardedWording();Journals();Identity();Art();report.status="PASS_NATIVE_CLIENT_FIXES136";}
            catch(Exception failure){report.error=failure.Message;}
            string output=Environment.GetEnvironmentVariable("HOTR_REVIEW128_OUT");
            if(!string.IsNullOrEmpty(output)){Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"ClientFixes136.json"),JsonUtility.ToJson(report,true));}
            if(Application.isBatchMode)EditorApplication.Exit(report.status.StartsWith("PASS_",StringComparison.Ordinal)?0:1);
        }
    }
}
#endif

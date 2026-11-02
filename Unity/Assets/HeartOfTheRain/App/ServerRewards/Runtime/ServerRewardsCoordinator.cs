using System;
using System.Collections;
using System.IO;
using UnityEngine;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.OnlineIdentity;

namespace HeartOfTheRain.App.ServerRewards {
    public sealed class RewardCompletion {public bool ok;public string error,kind,target,receiptId;public RewardGrant grant;}
    public sealed class ServerRewardsCoordinator {
        readonly Func<Action<RewardAccess,string>,IEnumerator> authorize;readonly Func<Action<bool,string>,IEnumerator> refreshWallet;readonly string directory;
        RewardAccess owner;ServerRewardJournal journal;RewardIntentDocument document;
        readonly Func<RewardAccess,RewardPresentationJournal> presentationFactory;
        public bool Busy{get;private set;}public BackendOffer Offer{get;private set;}public ServerWellworks Wellworks{get;private set;}public ServerCup Cup{get;private set;}
        public string PlayerId=>owner?.PlayerId;public bool HasPending=>document!=null&&document.hasPending;
        public void Invalidate(){owner=null;Offer=null;Wellworks=null;Cup=null;document=null;journal=null;}
        // Test-only local save fault seam. It never changes the HTTP request or
        // authority result, and has no remote/public configuration.
        public Action<string> VerificationCheckpoint;
        public ServerRewardsCoordinator(string directory,Func<Action<RewardAccess,string>,IEnumerator> authorize,Func<Action<bool,string>,IEnumerator> refreshWallet,Func<RewardAccess,RewardPresentationJournal> presentationFactory=null){this.directory=Path.GetFullPath(directory);this.authorize=authorize??throw new ArgumentNullException(nameof(authorize));this.refreshWallet=refreshWallet??throw new ArgumentNullException(nameof(refreshWallet));this.presentationFactory=presentationFactory??(value=>new RewardPresentationJournal(Path.Combine(this.directory,IdentityProtocol82.Sha(new Uri(value.Origin).GetLeftPart(UriPartial.Authority)),value.PlayerId,"presentation.json"),value.Origin,value.PlayerId));}
        IEnumerator Authorize(Action<string> done){RewardAccess value=null;string why=null;yield return authorize((context,error)=>{value=context;why=error;});if(value==null||!IdentityProtocol82.Secret(value.CurrentAccess)){done(why??"RewardSessionUnavailable");yield break;}
            try{string origin=new Uri(value.Origin).GetLeftPart(UriPartial.Authority);if(owner==null||owner.Origin!=value.Origin||owner.PlayerId!=value.PlayerId){Offer=null;Wellworks=null;Cup=null;}owner=value;journal=new ServerRewardJournal(Path.Combine(directory,IdentityProtocol82.Sha(origin),value.PlayerId,"rewards.json"),origin,value.PlayerId);journal.VerificationCheckpoint=stage=>VerificationCheckpoint?.Invoke(stage);document=journal.Read();}catch(Exception){done("RewardJournalUnavailable");yield break;}done(null);
        }
        bool Current(RewardAccess captured)=>ReferenceEquals(owner,captured)&&IdentityProtocol82.Secret(captured.CurrentAccess);
        static string Id()=>Guid.NewGuid().ToString("N");
        public IEnumerator Refresh(string page,Action<RewardCompletion> done)=>Run(page,null,done);
        public IEnumerator RecoverPending(Action<RewardCompletion> done)=>Run("Home",null,done);
        public bool LocalPending(string origin,string player){
            try{string authority=new Uri(origin).GetLeftPart(UriPartial.Authority);return new ServerRewardJournal(Path.Combine(directory,IdentityProtocol82.Sha(authority),player,"rewards.json"),authority,player).Read().hasPending;}
            catch(Exception){return true;}
        }
        // The server returns a command's committed reply before any rule check, so this
        // answer proves it did not commit. Session and network failures keep the intent.
        public static bool FinalRefusal(long status,string code)=>(status==400||status==403||status==404||status==409||status==422)&&code!="attempt_active";
        public IEnumerator ClaimDaily(Action<RewardCompletion> done){var offer=Offer;if(offer==null||offer.claimed){yield return Run("Daily",null,done);yield break;}var request=new PendingGift{requestId=Id(),offerId=offer.id,day=offer.day,step=offer.step,schedule=offer.schedule,expectedGrant=offer.grant.Copy()};yield return Run("Daily",new RewardIntent{kind="Daily",target=offer.id,commandId=request.requestId,payload=JsonUtility.ToJson(request)},done);}
        public IEnumerator ClaimWellworks(int level,Action<RewardCompletion> done){var milestone=Wellworks?.milestones==null?null:Array.Find(Wellworks.milestones,m=>m.level==level);if(milestone==null){yield return Run("Wellworks",null,done);yield break;}if(!HasPending&&(!milestone.eligible||milestone.claimed)){done(new RewardCompletion{ok=milestone.claimed,error=milestone.claimed?null:"MilestoneUnavailable"});yield break;}var request=new RewardMilestoneClaim{commandId=Id(),level=level};yield return Run("Wellworks",new RewardIntent{kind="Wellworks",target=level.ToString(System.Globalization.CultureInfo.InvariantCulture),commandId=request.commandId,payload=JsonUtility.ToJson(request)},done);}
        public IEnumerator JoinCup(Action<RewardCompletion> done){if(Cup==null){yield return Run("Cup",null,done);yield break;}if(!HasPending&&!Cup.canJoin){done(new RewardCompletion{error="PracticeJoinUnavailable"});yield break;}var request=new RewardJoin{commandId=Id()};yield return Run("Cup",new RewardIntent{kind="CupJoin",target="join",commandId=request.commandId,payload=JsonUtility.ToJson(request)},done);}
        public IEnumerator ClaimCup(string runId,Action<RewardCompletion> done){if(Cup==null){yield return Run("Cup",null,done);yield break;}if(!HasPending&&(Cup.run==null||Cup.run.id!=runId||Cup.state!="Finished")){bool claimed=Cup.run?.id==runId&&Cup.state=="Claimed";done(new RewardCompletion{ok=claimed,error=claimed?null:"PracticePrizeUnavailable"});yield break;}var request=new RewardCupClaim{commandId=Id(),runId=runId};yield return Run("Cup",new RewardIntent{kind="CupClaim",target=runId,commandId=request.commandId,payload=JsonUtility.ToJson(request)},done);}
        IEnumerator Run(string page,RewardIntent requested,Action<RewardCompletion> done){
            if(Busy){done(new RewardCompletion{error="RewardsBusy"});yield break;}Busy=true;var completion=new RewardCompletion();
            try{
                var metadataOwner=owner;string why=null,refused=null;yield return Authorize(error=>why=error);if(why!=null){completion.error=why;yield break;}var captured=owner;var client=new ServerRewardClient(captured);
                if(requested!=null&&metadataOwner!=null&&(metadataOwner.Origin!=captured.Origin||metadataOwner.PlayerId!=captured.PlayerId||metadataOwner.Generation!=captured.Generation)){completion.error="RewardSessionChanged";yield break;}
                if(requested!=null){
                    if(document.hasPending){/* Resolve the stored command first; a different click never replaces it. */}
                    else{bool saved=false;try{ServerRewardJournal.ValidateIntent(requested);document.hasPending=true;document.pending=requested;document=journal.Save(document);saved=true;}catch(Exception){completion.error="RewardIntentSaveUnavailable";}if(!saved)yield break;}
                }
                if(document.hasPending){
                    var pending=document.pending;completion.kind=pending.kind;completion.target=pending.target;bool success=false;RewardGrant grant=null;string receiptId=null;long status=0;
                    if(pending.kind=="Daily"){RewardReply<BackendDecision> reply=null;yield return client.DailyClaim(JsonUtility.FromJson<PendingGift>(pending.payload),r=>reply=r);success=reply!=null&&(reply.Ok||reply.status==410&&reply.error=="gift_expired");why=reply?.error;status=reply?.status??0;grant=reply?.value?.grant;receiptId=reply?.value?.receiptId;}
                    else if(pending.kind=="Wellworks"){RewardReply<ServerRewardReceipt> reply=null;yield return client.WellworksClaim(JsonUtility.FromJson<RewardMilestoneClaim>(pending.payload),r=>reply=r);success=reply!=null&&reply.Ok;why=reply?.error;status=reply?.status??0;grant=reply?.value?.grant;receiptId=reply?.value?.id;}
                    else if(pending.kind=="CupJoin"){RewardReply<ServerCupJoined> reply=null;yield return client.CupJoin(JsonUtility.FromJson<RewardJoin>(pending.payload),r=>reply=r);success=reply!=null&&reply.Ok;why=reply?.error;status=reply?.status??0;}
                    else{RewardReply<ServerRewardReceipt> reply=null;yield return client.CupClaim(JsonUtility.FromJson<RewardCupClaim>(pending.payload),r=>reply=r);success=reply!=null&&reply.Ok;why=reply?.error;status=reply?.status??0;grant=reply?.value?.grant;receiptId=reply?.value?.id;}
                    if(!success&&Current(captured)&&FinalRefusal(status,why)){
                        bool dropped=false;try{document.hasPending=false;document=journal.Save(document);dropped=true;}catch(Exception){completion.error="RewardConfirmationSaveUnavailable";}if(!dropped)yield break;
                        // Still read the page, so it shows the state that caused the refusal.
                        refused=why;
                    }else{
                    if(!success||!Current(captured)){completion.error=why??"RewardSessionChanged";yield break;}
                    // A lost reply or failed refresh keeps this exact intent.
                    // No local reward credit or optimistic wallet is permitted.
                    bool fresh=false;yield return refreshWallet((ok,error)=>{fresh=ok;why=error;});if(!fresh||!Current(captured)){completion.error=why??"RewardProjectionUnavailable";yield break;}
                    // Save the cosmetic receipt before acknowledging the durable
                    // claim intent. A crash between files retries the same server
                    // command and deduplicates this receipt, never another grant.
                    bool queued=grant==null;try{if(grant!=null){presentationFactory(captured).Enqueue("reward",receiptId,grant);queued=true;}}catch(Exception){completion.error="RewardPresentationSaveUnavailable";}if(!queued)yield break;
                    bool cleared=false;try{VerificationCheckpoint?.Invoke("BeforeAcknowledge");document.hasPending=false;document=journal.Save(document);cleared=true;}catch(Exception){completion.error="RewardConfirmationSaveUnavailable";}if(!cleared)yield break;completion.grant=grant?.Copy();completion.receiptId=receiptId;
                    }
                }
                if(!Current(captured)){completion.error="RewardSessionChanged";yield break;}
                if(page=="Daily"){RewardReply<BackendOffer> reply=null;yield return client.Offer(r=>reply=r);if(reply==null||!reply.Ok){completion.error=reply?.error??"RewardOfferUnavailable";yield break;}Offer=reply.value;}
                else if(page=="Wellworks"){RewardReply<ServerWellworks> reply=null;yield return client.Wellworks(r=>reply=r);if(reply==null||!reply.Ok){completion.error=reply?.error??"MilestonesUnavailable";yield break;}Wellworks=reply.value;}
                else if(page=="Cup"){RewardReply<ServerCup> reply=null;yield return client.Cup(r=>reply=r);if(reply==null||!reply.Ok){completion.error=reply?.error??"PracticeCupUnavailable";yield break;}Cup=reply.value;}
                else if(page!="Home"){completion.error="RewardPageInvalid";yield break;}
                if(!Current(captured)){Offer=null;Wellworks=null;Cup=null;completion.grant=null;completion.error="RewardSessionChanged";yield break;}if(refused!=null){completion.error=refused;yield break;}completion.ok=true;
            }finally{Busy=false;done(completion);}
        }
    }
}

using System;
using System.Collections;
using System.Diagnostics;
using HeartOfTheRain.App.ServerGameplay;

namespace HeartOfTheRain.App.Advertising {
    // The SDK can report completion, never money. The service owns the fixed
    // policy and credit; a durable receipt and wallet read precede presentation.
    public sealed class RewardedAdsFlow85:IDisposable {
        readonly IRewardedAdsApi85 api;readonly RewardedAdsJournal85 journal;
        readonly Func<Action<ServerAuthorizedContext,string>,IEnumerator> authorize;
        readonly Func<Action<bool,string>,IEnumerator> refreshWallet;
        readonly Func<AdPrivacy85,IRewardedAdsProvider85> providerFactory;
        readonly Func<bool> appFocused;
        IRewardedAdsProvider85 provider;AdIntent85 intent;ServerAuthorizedContext owner;
        int epoch;bool disposed;
        public bool Busy{get;private set;}public bool Presenting{get;private set;}
        public bool Pending=>intent!=null;public string Error{get;private set;}
        public AdStatus85 Status{get;private set;}public AdReceipt85 Receipt{get;private set;}
        public bool ReadFailed{get;private set;}public bool LoadingAd{get;private set;}
        // With the game in front and no close report: seconds after it returned, and seconds after a Show that never left.
        public double ResumeCloseSeconds=5,ShowCloseSeconds=8;
        bool cancelLoad;public void CancelLoad(){if(LoadingAd)cancelLoad=true;}
        public event Action Changed;
        public RewardedAdsFlow85(IRewardedAdsApi85 api,RewardedAdsJournal85 journal,
            Func<Action<ServerAuthorizedContext,string>,IEnumerator> authorize,
            Func<Action<bool,string>,IEnumerator> refreshWallet,Func<AdPrivacy85,IRewardedAdsProvider85> factory,Func<bool> appFocused=null){
            this.appFocused=appFocused;
            this.api=api??throw new ArgumentNullException(nameof(api));this.journal=journal??throw new ArgumentNullException(nameof(journal));
            this.authorize=authorize??throw new ArgumentNullException(nameof(authorize));this.refreshWallet=refreshWallet??throw new ArgumentNullException(nameof(refreshWallet));providerFactory=factory??throw new ArgumentNullException(nameof(factory));
        }
        bool Owned(int token)=>!disposed&&epoch==token&&owner!=null;
        bool Current(int token)=>Owned(token)&&!string.IsNullOrEmpty(owner.CurrentAccess);
        void Notify(){Changed?.Invoke();}
        static string Id()=>Guid.NewGuid().ToString("N");
        void Persist(){journal.Save(intent);}
        void Resolve(){
            intent.state="Resolved";Persist();
            try{journal.Clear(intent.origin,intent.playerId);}
            catch{
                // A lost clear acknowledgement can be confirmed by a fresh
                // locked read. Unknown/unreadable/present data still fails closed.
                AdIntent85 remaining;string why;
                if(journal.TryLoad(intent.origin,intent.playerId,out remaining,out why)||why!=null)throw;
            }
            intent=null;
        }
        bool Load(){string error;AdIntent85 saved;if(!journal.TryLoad(owner.Origin,owner.PlayerId,out saved,out error)&&error!=null){Error=error;return false;}
            // A transient pre-commit disk failure must not erase a callback
            // still observed by this same process/owner/immutable operation.
            if(intent!=null&&intent.CompletionReported&&saved!=null&&!saved.CompletionReported&&saved.state=="Reserved"&&
                intent.origin==saved.origin&&intent.playerId==saved.playerId&&intent.opportunityId==saved.opportunityId&&
                intent.reserveCommandId==saved.reserveCommandId&&intent.reportCommandId==saved.reportCommandId&&intent.claimCommandId==saved.claimCommandId&&intent.cancelCommandId==saved.cancelCommandId){
                saved.CompletionReported=true;saved.state="CompletionReported";journal.Save(saved);
            }
            // A resolved known opportunity may be a committed claim whose
            // local clear failed. Requery it before discarding its receipt.
            intent=saved;if(intent!=null&&intent.state=="Resolved"&&string.IsNullOrEmpty(intent.opportunityId))Resolve();return true;}
        void Create(){intent=new AdIntent85{origin=owner.Origin,playerId=owner.PlayerId,reserveCommandId=Id(),reportCommandId=Id(),claimCommandId=Id(),cancelCommandId=Id(),state="Reserving",opportunityId=""};Persist();}
        void ResolveFreshReserveDenial(AdReply85<AdOpportunity85> reply){
            if(reply==null||!reply.DefinitiveReserveDenial||reply.Unknown||intent==null||intent.state!="Reserving"||
                !string.IsNullOrEmpty(intent.opportunityId)||intent.CompletionReported)return;
            // Only called after Watch's single first send of a newly created
            // request. Recovery may have an older delayed/unknown request; a
            // later denial is not a server tombstone and must not clear it.
            Resolve();Status=null;
        }
        IEnumerator Authorize(int token){ServerAuthorizedContext context=null;string error=null;yield return authorize((value,why)=>{context=value;error=why;});
            if(disposed||token!=epoch)yield break;
            if(context==null){Error=error??"AdsSessionUnavailable";yield break;}
            if(owner!=null&&(owner.Origin!=context.Origin||owner.PlayerId!=context.PlayerId)){Error="AdsOwnerChanged";yield break;}owner=context;
        }
        public bool Reading{get;private set;}
        public IEnumerator Refresh(){if(disposed||Busy)yield break;Busy=Reading=true;int token=++epoch;Error=null;Notify();
            try{yield return Authorize(token);if(!Current(token)||!Load())yield break;
                AdReply85<AdStatus85> reply=null;yield return api.Status(owner,r=>reply=r);if(!Current(token))yield break;
                if(reply==null||!reply.Ok){Error=reply?.Error??"AdsStatusUnavailable";yield break;}Status=reply.Value;
                // Recover a server-owned reservation when a local pre-reserve
                // write survived but its HTTP reply did not. Never show it again.
                if(intent==null&&Status.activeOpportunity!=null){Create();intent.opportunityId=Status.activeOpportunity.opportunityId;intent.state="Reserved";Persist();}
            }finally{if(token==epoch){ReadFailed=Error!=null;Busy=Reading=false;Notify();}}
        }
        public IEnumerator Watch(AdPrivacy85 privacy){if(disposed||Busy||privacy==null||!privacy.Accepted)yield break;Busy=true;Receipt=null;Error=null;int token=++epoch;Notify();
            try{yield return Authorize(token);if(!Current(token)||!Load())yield break;
                if(intent!=null){yield return Reconcile(token);yield break;}
                AdReply85<AdStatus85> status=null;yield return api.Status(owner,r=>status=r);if(!Current(token))yield break;
                if(status==null||!status.Ok){Error=status?.Error??"AdsStatusUnavailable";yield break;}Status=status.Value;
                if(!Status.enabled||!Status.available){Error=Status.reason??"AdsUnavailable";yield break;}
                provider=providerFactory(privacy);if(provider==null||!provider.Installed){Error="AdsSdkUnavailable";yield break;}
                Create();AdReply85<AdOpportunity85> reserved=null;yield return api.Reserve(owner,intent.reserveCommandId,r=>reserved=r);if(!Current(token))yield break;
                if(reserved==null||!reserved.Ok){Error=reserved?.Error??"AdsReserveUnavailable";ResolveFreshReserveDenial(reserved);yield break;}
                intent.opportunityId=reserved.Value.opportunityId;intent.state="Reserved";Persist();
                bool loaded=false,loadDone=false;string loadError=null;LoadingAd=true;cancelLoad=false;Notify();provider.Load((ok,why)=>{if(Owned(token)){loaded=ok;loadError=why;loadDone=true;}});
                var deadline=Stopwatch.StartNew();while(Owned(token)&&!loadDone&&!cancelLoad&&deadline.Elapsed.TotalSeconds<50)yield return null;LoadingAd=false;if(!Owned(token))yield break;
                if(cancelLoad){cancelLoad=false;yield return Cancel(token);yield break;}
                if(!loaded){Error=loadError??"AdsLoadTimeout";yield return Cancel(token);yield break;}
                // This second durable checkpoint is deliberately before Show.
                Persist();bool terminal=false,shown=false,completionSaveFailed=false;Presenting=true;Notify();
                provider.Show(signal=>{
                    if(!Owned(token))return;
                    if(signal==RewardedSignal85.Shown)shown=true;
                    else if(signal==RewardedSignal85.CompletedInfoOnly&&shown&&!terminal&&!intent.CompletionReported){
                        intent.CompletionReported=true;intent.state="CompletionReported";
                        try{Persist();}catch{completionSaveFailed=true;Error="AdsJournalUnavailable";}
                    }else if(signal==RewardedSignal85.Closed||signal==RewardedSignal85.Failed)terminal=true;
                });
                // Ads may include an external landing page, which keeps the game out of
                // focus, so nothing here closes a visible advertisement. With the game back
                // in front and no close report the wait ends. Nothing is granted without a
                // reported completion, and a report seen before that still counts.
                var focus=Stopwatch.StartNew();var frame=Stopwatch.StartNew();bool left=false;
                while(Owned(token)&&!terminal){
                    if(appFocused!=null){
                        if(!appFocused()||frame.Elapsed.TotalSeconds>1){left=true;focus.Restart();}
                        else if(focus.Elapsed.TotalSeconds>=(left?ResumeCloseSeconds:ShowCloseSeconds))terminal=true;
                        frame.Restart();
                    }
                    yield return null;
                }
                if(!Owned(token))yield break;Presenting=false;
                if(completionSaveFailed)yield break;
                // An external landing page may outlive the access token.
                // Keep the observed callback durably, then renew credentials
                // before any report or claim. Identity changes still fence it.
                if(!Current(token))yield return Authorize(token);if(!Current(token))yield break;
                if(intent.CompletionReported)yield return Reconcile(token);else{Error="AdsNotCompleted";yield return Cancel(token);}
            }finally{if(token==epoch){provider?.Dispose();provider=null;Presenting=LoadingAd=false;Busy=false;Notify();}}
        }
        public IEnumerator Recover(){if(disposed||Busy)yield break;Busy=true;Receipt=null;Error=null;int token=++epoch;Notify();
            try{yield return Authorize(token);if(Current(token)&&Load())yield return Reconcile(token);}
            finally{if(token==epoch){Busy=false;Notify();}}
        }
        IEnumerator Reconcile(int token){if(intent==null)yield break;
            AdReply85<AdOpportunity85> reply=null;
            if(string.IsNullOrEmpty(intent.opportunityId)){
                yield return api.Reserve(owner,intent.reserveCommandId,r=>reply=r);if(!Current(token))yield break;
                if(reply==null||!reply.Ok){Error=reply?.Error??"AdsReserveUnavailable";yield break;}
                intent.opportunityId=reply.Value.opportunityId;intent.state="Reserved";Persist();
            }
            yield return api.Read(owner,intent.opportunityId,r=>reply=r);if(!Current(token))yield break;
            if(reply==null||!reply.Ok){Error=reply?.Error??"AdsRecoveryUnavailable";yield break;}
            var opportunity=reply.Value;
            if(opportunity.state=="Cancelled"||opportunity.state=="Expired"){Resolve();Error="AdsNotCompleted";yield break;}
            if(opportunity.state=="Claimed"){yield return Project(token,opportunity);yield break;}
            // The authenticated canonical state can recover a report made by
            // another process/device even when this local callback was lost.
            if(!intent.CompletionReported&&(opportunity.state=="CompletedReported"||opportunity.state=="Verified")){
                intent.CompletionReported=true;intent.state="Claiming";Persist();
            }
            if(!intent.CompletionReported){yield return Cancel(token);yield break;}
            if(opportunity.state=="Reserved"||opportunity.state=="AwaitingVerification"){
                yield return api.Report(owner,intent.opportunityId,intent.reportCommandId,r=>reply=r);if(!Current(token))yield break;
                if(reply==null||!reply.Ok){Error=reply?.Error??"AdsCompletionPending";yield break;}opportunity=reply.Value;
            }
            intent.state="Claiming";Persist();
            yield return api.Claim(owner,intent.opportunityId,intent.claimCommandId,r=>reply=r);if(!Current(token))yield break;
            if(reply==null||!reply.Ok){Error=reply?.Error??"AdsCompletionPending";yield break;}
            if(reply.Value.state!="Claimed"){Error="AdsCompletionPending";yield break;}yield return Project(token,reply.Value);
        }
        IEnumerator Cancel(int token){if(intent==null||intent.CompletionReported||string.IsNullOrEmpty(intent.opportunityId))yield break;
            intent.state="Cancelling";Persist();AdReply85<AdOpportunity85> reply=null;yield return api.Cancel(owner,intent.opportunityId,intent.cancelCommandId,r=>reply=r);if(!Current(token))yield break;
            if(reply!=null&&reply.Ok&&(reply.Value.state=="Cancelled"||reply.Value.state=="Expired"))Resolve();
            else if(reply!=null&&reply.Ok&&reply.Value.state=="Claimed")yield return Project(token,reply.Value);
            else Error=reply?.Error??"AdsCancellationPending";
        }
        IEnumerator Project(int token,AdOpportunity85 opportunity){
            if(opportunity.receipt==null||opportunity.receipt.coins!=400){Error="AdsReceiptInvalid";yield break;}
            bool fresh=false;string error=null;yield return refreshWallet((ok,why)=>{fresh=ok;error=why;});if(!Current(token))yield break;
            if(!fresh){Error=error??"AdsWalletPending";yield break;}
            // A failed final journal commit/clear must keep collection feedback
            // hidden. Recovery reads the same server receipt without a new ad
            // or claim; only durable local resolution publishes the receipt.
            Resolve();Receipt=opportunity.receipt;Status=null;Error=null;
        }
        public void Invalidate(){epoch++;provider?.Dispose();provider=null;Busy=Presenting=Reading=LoadingAd=false;Status=null;owner=null;intent=null;Receipt=null;Error="AdsSessionChanged";Notify();}
        // Unity does not propagate exceptions thrown by nested coroutines to
        // the caller. Walk them here so storage/transport faults fail closed.
        public IEnumerator Guard(IEnumerator routine){
            int owned=epoch+1;var stack=new System.Collections.Generic.Stack<IEnumerator>();stack.Push(routine);
            try{while(stack.Count>0){object next=null;bool moved=false;Exception fault=null;try{moved=stack.Peek().MoveNext();if(moved)next=stack.Peek().Current;}catch(Exception error){fault=error;}
                if(fault!=null){if(epoch==owned)Error="AdsRecoveryRequired";break;}
                if(!moved){(stack.Pop() as IDisposable)?.Dispose();continue;}
                if(next is IEnumerator nested)stack.Push(nested);else yield return next;
            }}finally{while(stack.Count>0)try{(stack.Pop() as IDisposable)?.Dispose();}catch{}if(!disposed&&epoch==owned){provider?.Dispose();provider=null;Busy=Presenting=Reading=LoadingAd=false;Notify();}}
        }
        public void Dispose(){if(disposed)return;Invalidate();disposed=true;}
    }
}

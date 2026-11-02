using System;
using System.Collections;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.ServerAccount;

namespace HeartOfTheRain.App.ServerGameplay {
    public sealed partial class ServerGameSession {
        VkSigninJournal102 vkJournal;VkSigninDocument102 vkDocument;VkSigninStatus102 vkSigninStatus;VkSigninClient102 vkSigninClient;bool vkDisposed;
        void EnsureVkJournal(){
            if(vkDisposed||config==null||accountSelection==null)throw new InvalidOperationException("VkAccountUnavailable");
            if(vkJournal==null){string scope="review-vk-"+IdentityProtocol82.Sha(config.identityScope).Substring(0,32);vkJournal=new VkSigninJournal102(new OriginBoundIdentityStore82(NewProtectedStore(scope),config.origin+"|vk-signin"),config.origin);}
            vkDocument=vkJournal.Read();
        }
        bool VkHasPending {get{EnsureVkJournal();if(vkSigninStatus==null&&vkDocument.Pending)SetVkLocalStatus();return vkDocument.Pending;}}
        public VkSigninStatus102 AccountVkStatus {
            get{
                if(vkDisposed||closed||vkSigninStatus==null||vkDocument==null||accountSelection==null||identity==null||accountSelection.purpose!=""&&accountSelection.purpose!="vk")return null;
                bool source=accountSelection.currentScope==vkDocument.sourceScope&&PlayerId==vkDocument.sourcePlayerId;
                bool target=vkDocument.Confirmed&&accountSelection.currentScope==vkDocument.pendingScope&&PlayerId==vkDocument.targetPlayerId;
                return source||target?vkSigninStatus.Copy():null;
            }
        }
        public bool AccountCanCopyRecovery=>Ready&&!busy&&identity!=null&&identity.HasRecoveryBackup;
        void SetVkLocalStatus(){
            if(vkDocument==null||vkDocument.phase=="Empty"){vkSigninStatus=null;return;}
            vkSigninStatus=new VkSigninStatus102{playerId=PlayerId??vkDocument.sourcePlayerId,provider="vk",phase=vkDocument.phase,flowId=vkDocument.requestId,requestId=vkDocument.requestId,targetPlayerId=vkDocument.targetPlayerId,requiresConfirmation=IdentityProtocol82.Id(vkDocument.targetPlayerId)&&vkDocument.targetPlayerId!=vkDocument.sourcePlayerId,available=true};
        }
        bool VkSourceCurrent()=>!vkDisposed&&!closed&&identity!=null&&accountSelection!=null&&vkDocument!=null&&accountSelection.currentScope==vkDocument.sourceScope&&PlayerId==vkDocument.sourcePlayerId;
        void EnsureVkIdentity(){
            if(pendingIdentity!=null&&pendingIdentityScope!=vkDocument.pendingScope)throw new InvalidOperationException("VkIdentityScopeConflict");
            if(pendingIdentity==null){pendingIdentityScope=vkDocument.pendingScope;pendingIdentity=NewScopedIdentity(pendingIdentityScope,out pendingIdentityTransport);}
        }
        void StoreVkStatus(VkSigninStatus102 value){
            if(!VkSourceCurrent()||value==null||value.playerId!=vkDocument.sourcePlayerId||value.flowId!=vkDocument.requestId)throw new InvalidOperationException("VkOwnerChanged");
            if(vkDocument.Confirmed)throw new InvalidOperationException("VkConfirmedFlowCannotRegress");
            if(vkDocument.phase=="Ready"&&value.Pending)throw new InvalidOperationException("VkReadyFlowCannotRegress");
            if(!string.IsNullOrEmpty(vkDocument.targetPlayerId)&&!string.IsNullOrEmpty(value.targetPlayerId)&&value.targetPlayerId!=vkDocument.targetPlayerId)throw new InvalidOperationException("VkTargetChanged");
            vkDocument.phase=value.phase=="Completed"?"Ready":value.phase;vkDocument.targetPlayerId=value.targetPlayerId??"";
            if(value.Terminal&&value.phase!="Completed"){vkDocument.flowSecret="";vkDocument.refreshToken="";}
            vkDocument=vkJournal.Save(vkDocument);vkSigninStatus=value.Copy();vkSigninStatus.phase=vkDocument.phase;
            if(value.Terminal&&value.phase!="Completed"&&pendingIdentityScope==vkDocument.pendingScope){pendingIdentity?.Dispose();pendingIdentityTransport?.Dispose();pendingIdentity=null;pendingIdentityTransport=null;pendingIdentityScope=null;}
        }
        public void AccountVkBegin(Action<bool,string> done){
            string blocker=AccountTransitionBlocker();if(blocker!=null){Deliver(done,false,blocker);return;}
            busy=true;StartCoroutine(VkSourceOperation("begin",done));
        }
        public void AccountVkRefresh(Action<bool,string> done){
            if(closed||busy||vkDisposed){Deliver(done,false,"AccountBusy");return;}
            try{EnsureVkJournal();
                if(vkDocument.phase=="Empty"){vkSigninStatus=null;Deliver(done,true,null);return;}
                if(VkAlreadyPromoted()){FinishVkJournal();Changed?.Invoke();Deliver(done,true,null);return;}
                if(accountBlocked&&accountSelection.purpose=="vk"){AccountResume(done);return;}
                if(!VkSourceCurrent()){if(!vkDocument.Pending){vkSigninStatus=null;Deliver(done,true,null);}else Deliver(done,false,"VkOwnerChanged");return;}
                if(!vkDocument.Pending){SetVkLocalStatus();Deliver(done,true,null);return;}
                if(vkSigninStatus==null)SetVkLocalStatus();
            }catch(Exception){Deliver(done,false,"VkJournalUnavailable");return;}
            busy=true;StartCoroutine(VkSourceOperation("status",done));
        }
        public void AccountVkCancel(Action<bool,string> done){
            if(closed||busy||accountBlocked||vkDisposed){Deliver(done,false,"AccountBusy");return;}
            try{EnsureVkJournal();if(!vkDocument.Pending||vkDocument.Confirmed||!VkSourceCurrent()){Deliver(done,false,"VkCancellationUnavailable");return;}}
            catch(Exception){Deliver(done,false,"VkJournalUnavailable");return;}
            busy=true;StartCoroutine(VkSourceOperation("cancel",done));
        }
        IEnumerator VkSourceOperation(string operation,Action<bool,string> done){
            bool fresh=false;string why=null;yield return FetchWallet((ok,error)=>{fresh=ok;why=error;});
            busy=false;string blocker=fresh?TransitionBlockerIgnoringVk():why;
            if(blocker!=null){Deliver(done,false,blocker);yield break;}busy=true;
            try{
                EnsureVkJournal();
                if(operation=="begin"){
                    if(vkDocument.Pending)throw new InvalidOperationException();
                    pendingIdentity?.Dispose();pendingIdentityTransport?.Dispose();pendingIdentity=null;pendingIdentityTransport=null;
                    vkDocument=new VkSigninDocument102{origin=config.origin,revision=vkDocument.revision,sourceScope=accountSelection.currentScope,sourcePlayerId=PlayerId,pendingScope=NewAccountScope(),requestId=NewId(),flowSecret=IdentityProtocol82.NewSecret(),refreshToken=IdentityProtocol82.NewSecret(),phase="Prepared"};
                    vkDocument=vkJournal.Save(vkDocument);
                }
                if(!VkSourceCurrent())throw new InvalidOperationException();EnsureVkIdentity();
            }catch(Exception){busy=false;Deliver(done,false,"VkIntentSaveUnconfirmed");yield break;}
            string source=PlayerId;long owner=playerOwnershipEpoch;
            vkSigninClient?.Dispose();vkSigninClient=new VkSigninClient102(config.origin,source,()=>!closed&&!vkDisposed&&playerOwnershipEpoch==owner&&PlayerId==source?identity.AccessToken:null,r=>StartCoroutine(r),config.allowDevelopmentLoopback);
            VkSigninStatus102 result=null;string failure=null;bool finished=false;
            Action<VkSigninStatus102,string> received=(value,error)=>{result=value;failure=error;finished=true;};
            if(operation=="cancel")vkSigninClient.Cancel(vkDocument.requestId,received);
            else if(vkDocument.phase=="Prepared")vkSigninClient.Begin(vkDocument.requestId,pendingIdentity.DevicePublicKey,IdentityProtocol82.Sha(vkDocument.flowSecret),received);
            else vkSigninClient.Status(vkDocument.requestId,received);
            while(!finished&&!closed&&!vkDisposed)yield return null;
            if(closed||vkDisposed)yield break;
            // Not found proves a saved intent never reached the server, so no
            // authorization exists to cancel and the local intent can end here.
            if(operation=="cancel"&&result==null&&failure=="VkSigninHttp404"&&vkDocument.phase=="Prepared"){failure=null;result=new VkSigninStatus102{playerId=source,provider="vk",phase="Cancelled",flowId=vkDocument.requestId,requestId=vkDocument.requestId,available=true};}
            if(result!=null&&playerOwnershipEpoch==owner&&PlayerId==source){try{StoreVkStatus(result);}catch(Exception){failure="VkStatusSaveUnconfirmed";result=null;}}
            else if(result!=null){failure="VkOwnerChanged";result=null;}
            busy=false;Changed?.Invoke();Deliver(done,result!=null,failure??(result==null?"VkSigninUnavailable":null));
        }
        public void AccountVkComplete(string expectedTarget,bool confirmed,Action<bool,string> done){
            if(!confirmed||!IdentityProtocol82.Id(expectedTarget)||closed||busy||accountBlocked){Deliver(done,false,"AccountConfirmationRequired");return;}
            try{EnsureVkJournal();if(vkDocument.phase!="Ready"||vkDocument.targetPlayerId!=expectedTarget||!VkSourceCurrent())throw new InvalidOperationException();}
            catch(Exception){Deliver(done,false,"VkConfirmationChanged");return;}
            string blocker=TransitionBlockerIgnoringVk();if(blocker!=null){Deliver(done,false,blocker);return;}
            busy=true;StartCoroutine(VkPrepareCompletion(expectedTarget,done));
        }
        IEnumerator VkPrepareCompletion(string target,Action<bool,string> done){
            bool fresh=false;string why=null;yield return FetchWallet((ok,error)=>{fresh=ok;why=error;});
            busy=false;string blocker=fresh?TransitionBlockerIgnoringVk():why;if(blocker!=null){Deliver(done,false,blocker);yield break;}busy=true;
            try{
                EnsureVkJournal();if(!VkSourceCurrent()||vkDocument.phase!="Ready"||vkDocument.targetPlayerId!=target)throw new InvalidOperationException();
                accountSelection.lastPlayer=PlayerId;accountSelection.blocked=true;accountSelection.purpose="vk";accountSelection.requestId=vkDocument.requestId;accountSelection.targetPlayer=target;accountSelection.pendingScope=vkDocument.pendingScope;
                accountBlocked=true;SaveAccountSelection();AccountInvalidatePrivateView();
                vkDocument.phase="Committing";vkDocument=vkJournal.Save(vkDocument);
                SetVkLocalStatus();Changed?.Invoke();
            }catch(Exception){if(accountBlocked)AccountInvalidatePrivateView();busy=false;Deliver(done,false,"VkConfirmationSaveUnconfirmed");yield break;}
            yield return VkCompleteRoutine(done);
        }
        bool VkAlreadyPromoted()=>vkDocument!=null&&(vkDocument.phase=="Committing"||vkDocument.phase=="Completed")&&accountSelection!=null&&accountSelection.currentScope==vkDocument.pendingScope&&identity!=null&&identity.View.hasSession&&identity.View.playerId==vkDocument.targetPlayerId;
        void FinishVkJournal(){if(vkDocument.phase!="Completed"){vkDocument.phase="Completed";vkDocument.flowSecret="";vkDocument.refreshToken="";vkDocument=vkJournal.Save(vkDocument);}SetVkLocalStatus();}
        IEnumerator VkResumeRoutine(Action<bool,string> done){
            bool terminal=false;
            try{EnsureVkJournal();if(accountSelectionDirty)SaveAccountSelection();terminal=!vkDocument.Pending&&vkDocument.phase!="Completed";}
            catch(Exception){busy=false;Deliver(done,false,"VkJournalUnavailable");yield break;}
            if(terminal){yield return VkReconcileCompletionFailure("VkAuthorizationEnded",done);yield break;}
            yield return VkCompleteRoutine(done);
        }
        // An unknown network result never rolls an account back. Only an
        // authenticated terminal server flow with no locally committed target
        // credentials proves no usable target adoption remains. The target may
        // also have been deleted after a commit whose response was lost.
        bool TryReadVkPendingSession(out bool hasSession,Action<bool,string> done){
            try{hasSession=pendingIdentity!=null&&pendingIdentity.View.hasSession;return true;}
            catch(Exception){hasSession=false;busy=false;Deliver(done,false,"VkProtectedReadUnconfirmed");return false;}
        }
        IEnumerator VkReconcileCompletionFailure(string original,Action<bool,string> done){
            if(closed||vkDisposed)yield break;
            bool protectedSession;if(!TryReadVkPendingSession(out protectedSession,done))yield break;
            if(protectedSession){busy=false;Deliver(done,false,original);yield break;}
            bool owner;
            try{EnsureVkJournal();owner=VkSigninProtocol102.OwnsSelection(vkDocument,accountSelection)&&identity!=null&&identity.View.hasSession&&identity.View.playerId==vkDocument.sourcePlayerId;}
            catch(Exception){owner=false;}
            if(!owner){busy=false;Deliver(done,false,original);yield break;}
            if(!identity.HasAccess){
                IdentityReply82<IdentityView82> refreshed=null;
                try{if(identity.View.hasPending)identity.Resume(r=>refreshed=r);else identity.Refresh(NewId(),r=>refreshed=r);}
                catch(Exception){busy=false;Deliver(done,false,original);yield break;}
                while(refreshed==null&&!closed&&!vkDisposed)yield return null;
                if(refreshed==null||!refreshed.Succeeded){busy=false;Deliver(done,false,original);yield break;}
            }
            long epoch=playerOwnershipEpoch;string source=vkDocument.sourcePlayerId;
            vkSigninClient?.Dispose();vkSigninClient=new VkSigninClient102(config.origin,source,()=>!closed&&!vkDisposed&&playerOwnershipEpoch==epoch&&PlayerId==source?identity.AccessToken:null,r=>StartCoroutine(r),config.allowDevelopmentLoopback);
            VkSigninStatus102 state=null;bool returned=false;
            vkSigninClient.Status(vkDocument.requestId,(value,error)=>{state=value;returned=true;});while(!returned&&!closed&&!vkDisposed)yield return null;
            if(closed||vkDisposed)yield break;
            if(state==null||playerOwnershipEpoch!=epoch||PlayerId!=source||!state.Terminal||state.phase=="Completed"){
                busy=false;Deliver(done,false,original);yield break;
            }
            AccountSelectionState83 prior=null;
            try{
                EnsureVkJournal();
                if(pendingIdentity!=null&&pendingIdentity.View.hasSession||!VkSigninProtocol102.OwnsSelection(vkDocument,accountSelection))throw new InvalidOperationException();
                vkDocument.phase=state.phase;vkDocument.targetPlayerId="";vkDocument.flowSecret="";vkDocument.refreshToken="";vkDocument=vkJournal.Save(vkDocument);vkSigninStatus=state.Copy();
                if(pendingIdentityScope==vkDocument.pendingScope){pendingIdentity?.Dispose();pendingIdentityTransport?.Dispose();pendingIdentity=null;pendingIdentityTransport=null;pendingIdentityScope=null;}
                prior=UnityEngine.JsonUtility.FromJson<AccountSelectionState83>(UnityEngine.JsonUtility.ToJson(accountSelection));
                accountSelection.pendingScope="";accountSelection.purpose="";accountSelection.requestId="";accountSelection.targetPlayer="";accountSelection.blocked=false;
                accountSelection.recoveredAttemptDecision=true;accountSelection.recoveredAttemptId="";SaveAccountSelection();accountBlocked=false;AccountInvalidatePrivateView();
            }catch(Exception){if(prior!=null)accountSelection=prior;accountBlocked=true;busy=false;Deliver(done,false,"VkRollbackSaveUnconfirmed");yield break;}
            accountRecoveryBootstrap=true;yield return Bootstrap();accountRecoveryBootstrap=false;Changed?.Invoke();Deliver(done,false,Ready?"VkAuthorizationEnded":error??original);
        }
        IEnumerator VkCompleteRoutine(Action<bool,string> done){
            IdentityReply82<IdentityView82> reply=null;
            try{
                EnsureVkJournal();if(accountSelectionDirty)SaveAccountSelection();
                if(VkAlreadyPromoted()){FinishVkJournal();busy=false;Deliver(done,true,null);yield break;}
                if(accountSelection.purpose!="vk"||accountSelection.requestId!=vkDocument.requestId||accountSelection.pendingScope!=vkDocument.pendingScope||accountSelection.targetPlayer!=vkDocument.targetPlayerId||!accountSelection.blocked)throw new InvalidOperationException();
                if(vkDocument.phase=="Ready"){vkDocument.phase="Committing";vkDocument=vkJournal.Save(vkDocument);}
                if(vkDocument.phase!="Committing")throw new InvalidOperationException();EnsureVkIdentity();
                if(!pendingIdentity.View.hasSession){
                    string recovery="";if(vkDocument.sourcePlayerId==vkDocument.targetPlayerId&&identity.HasRecoveryBackup)recovery=identity.RecoverySecretForExplicitBackup();
                    pendingIdentity.CompleteVk(vkDocument.Completion(pendingIdentity.DevicePublicKey),recovery,r=>reply=r);
                }
            }catch(Exception){busy=false;Deliver(done,false,"VkCompletionUnavailable");yield break;}
            bool protectedSession;if(!TryReadVkPendingSession(out protectedSession,done))yield break;
            if(!protectedSession){while(reply==null&&!closed)yield return null;if(reply==null||!reply.Succeeded){yield return VkReconcileCompletionFailure(reply?.error??"VkCompletionUnknown",done);yield break;}}
            bool promoted=false;string failure=null;yield return PromoteRecoveredIdentity((ok,error)=>{promoted=ok;failure=error;});
            if(promoted){try{FinishVkJournal();}catch(Exception){promoted=false;failure="VkJournalCompletionUnconfirmed";}}
            Changed?.Invoke();Deliver(done,promoted,failure);
        }
        void DisposeVkSignin(){vkDisposed=true;vkSigninClient?.Dispose();vkJournal?.Dispose();vkSigninClient=null;vkJournal=null;}
    }
}

using System;
using System.Collections;
using System.IO;
using UnityEngine;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.ServerAccount;

namespace HeartOfTheRain.App.ServerGameplay {
    public sealed partial class ServerGameSession {
        AccountSelection83 accountSelector;AccountSelectionState83 accountSelection;bool accountBlocked,accountRecoveryBootstrap,accountSelectionDirty,accountSelectionConflict;string pendingIdentityScope;
        ManagedIdentitySession82 pendingIdentity;IdentityHttpTransport82 pendingIdentityTransport;
#if UNITY_EDITOR
        readonly System.Collections.Generic.Dictionary<string,EditorEphemeralIdentity82> editorAccountVaults=new System.Collections.Generic.Dictionary<string,EditorEphemeralIdentity82>();
#endif
        public bool AccountBlocked=>accountBlocked;
        public string AccountState=>accountSelection?.purpose??"";
        public string AccountStablePlayerId=>PlayerId??accountSelection?.lastPlayer??"";
        public string AccountRecoveryTarget=>accountSelection?.purpose=="recover"?accountSelection.targetPlayer:"";
        public bool AccountIdentityPending=>accountSelection!=null&&accountSelection.purpose!=""&&accountSelection.purpose!="closed"||accountBlocked&&pendingIdentity!=null&&pendingIdentity.View.hasSession;
        public bool AccountCanStartAnotherRecovery=>accountBlocked&&accountSelection?.purpose=="recover"&&accountSelection.recoveryRejected;
        public bool AccountRecoveryRequiresEntry=>accountSelection?.purpose=="recover"&&pendingIdentity!=null&&!pendingIdentity.View.hasPending&&!pendingIdentity.View.hasSession;
        public bool HasActiveServerAttempt=>wallet?.activeAttempt!=null;
        bool HoldRecoveredAttemptDecision=>accountSelection!=null&&accountSelection.recoveredAttemptDecision&&wallet?.activeAttempt!=null&&(string.IsNullOrEmpty(accountSelection.recoveredAttemptId)||accountSelection.recoveredAttemptId==wallet.activeAttempt.attemptId);
        void BindRecoveredAttemptDecision(){
            if(accountSelection==null||!accountSelection.recoveredAttemptDecision||wallet==null)return;
            if(wallet.activeAttempt==null){accountSelection.recoveredAttemptDecision=false;accountSelection.recoveredAttemptId="";SaveAccountSelection();}
            else if(string.IsNullOrEmpty(accountSelection.recoveredAttemptId)){accountSelection.recoveredAttemptId=wallet.activeAttempt.attemptId;SaveAccountSelection();}
        }
        void PrepareRecoveredAttemptDecision(){
            if(accountSelection.purpose=="recover"||accountSelection.purpose=="vk"){accountSelection.recoveredAttemptDecision=true;accountSelection.recoveredAttemptId="";}
            else if(accountSelection.purpose=="fresh"){accountSelection.recoveredAttemptDecision=false;accountSelection.recoveredAttemptId="";}
            // An already-prepared promotion may have cleared purpose before a
            // failed selector write. Exact retry must preserve its decision.
        }
        string NewAccountScope()=>"review-account-"+NewId();
        IProtectedSessionStore82 NewProtectedStore(string scope){
#if UNITY_ANDROID && !UNITY_EDITOR
            return new AndroidDeviceIdentity82(scope);
#elif UNITY_EDITOR
            if(editorVault==null)editorVault=new EditorEphemeralIdentity82();
            return editorVault.CreateStore(Path.GetFullPath("../.verification-cache/Launch82/ServerAccount83/Editor/"+NewId()+".sealed"));
#else
            throw new NotSupportedException("ManagedServerIdentityRequiresAndroidApi26");
#endif
        }
        ManagedIdentitySession82 NewScopedIdentity(string scope,out IdentityHttpTransport82 transport){
            IDeviceIdentityKey82 key;IProtectedSessionStore82 storage;
#if UNITY_ANDROID && !UNITY_EDITOR
            var android=new AndroidDeviceIdentity82(scope);key=android;storage=android;
#elif UNITY_EDITOR
            // Recovery requires a NEW device key. Each explicitly isolated
            // Editor scope therefore owns a different ephemeral CNG key too.
            if(!editorAccountVaults.TryGetValue(scope,out var scopedVault)){scopedVault=new EditorEphemeralIdentity82();editorAccountVaults.Add(scope,scopedVault);}
            key=scopedVault.CreateKey();storage=scopedVault.CreateStore(Path.GetFullPath("../.verification-cache/Launch82/ServerAccount83/Editor/"+NewId()+".sealed"));
#else
            throw new NotSupportedException("ManagedServerIdentityRequiresAndroidApi26");
#endif
            transport=new IdentityHttpTransport82(config.origin,r=>StartCoroutine(r),config.allowDevelopmentLoopback,config.productionEnabled);
            return new ManagedIdentitySession82(key,new OriginBoundIdentityStore82(storage,config.origin),transport,config.productionEnabled);
        }
        void InitializeAccountIdentity(){
            if(accountSelector==null){
                string selectorScope="review-selector-"+IdentityProtocol82.Sha(config.identityScope).Substring(0,32);
                accountSelector=new AccountSelection83(new OriginBoundIdentityStore82(NewProtectedStore(selectorScope),config.origin+"|account-selector"),config.origin,config.identityScope);
                accountSelection=accountSelector.Read();accountBlocked=accountSelection.blocked;
            }
            if(identity==null)identity=NewScopedIdentity(accountSelection.currentScope,out identityTransport);
        }
        void SaveAccountSelection(){
            if(accountSelectionConflict)throw new InvalidOperationException("AccountSelectionConflict");
            string previousDigest=accountSelector.CurrentDigest;var candidate=accountSelection;var expected=JsonUtility.FromJson<AccountSelectionState83>(JsonUtility.ToJson(candidate));expected.revision=checked(candidate.revision+1);
            try{accountSelection=accountSelector.Save(candidate);accountSelectionDirty=false;}
            catch{
                accountSelectionDirty=true;
                try{var durable=accountSelector.Read();if(durable.revision==expected.revision&&JsonUtility.ToJson(durable)==JsonUtility.ToJson(expected)){accountSelection=durable;accountSelectionDirty=false;return;}if(accountSelector.CurrentDigest!=previousDigest)accountSelectionConflict=true;}catch(Exception){}
                throw;
            }
        }
        void AccountInvalidatePrivateView(){
            playerOwnershipEpoch++;generation++;IdentityChanged?.Invoke();broker?.Dispose();broker=null;walletClient?.Dispose();walletClient=null;wallet=null;journal=null;document=null;journalDirty=false;
            var empty=new RuStoreServerWallet{playerId=IdentityProtocol82.Id(accountSelection?.lastPlayer)?accountSelection.lastPlayer:new string('0',32),coins=0,stars=0,lives=0,maxLives=5,currentLevel=1,starting=new int[4],tools=new int[4]};
            projection.Apply(empty,null);Changed?.Invoke();
        }
        string TransitionBlocker(){
            string current=TransitionBlockerIgnoringVk();if(current!=null)return current;
            try{if(VkHasPending)return "AccountPendingActions";}catch(Exception){return "AccountPendingStateUnavailable";}
            return null;
        }
        string TransitionBlockerIgnoringVk(){
            if(closed||busy)return "AccountBusy";
            if(!Ready)return "AccountSessionUnavailable";
            if(HasPending||journalDirty||identity.View.hasPending)return "AccountPendingActions";
            if(HasActiveServerAttempt)return "AccountActiveAttempt";
            var checkout=GetComponent<HeartOfTheRain.App.ShopCheckout86.ShopCheckoutHost86>();
            if(checkout&&(checkout.Busy||checkout.Pending))return "AccountPendingActions";
            try{if(HeartOfTheRain.App.ShopCheckout86.ShopCheckoutHost86.PendingOnDisk(this))return "AccountPendingActions";}catch(Exception){return "AccountPendingStateUnavailable";}
            var ads=GetComponent<HeartOfTheRain.App.Advertising.RewardedShop85>();
            if(ads&&(ads.Busy||ads.HasPending))return "AccountPendingActions";
            try{if(HeartOfTheRain.App.Advertising.RewardedShop85.PendingOnDisk(config.origin,PlayerId))return "AccountPendingActions";}catch(Exception){return "AccountPendingStateUnavailable";}
            var rewards=GetComponent<HeartOfTheRain.App.ServerRewards.ServerRewardsSession>();
            if(rewards&&(rewards.Coordinator.Busy||rewards.Coordinator.HasPending))return "AccountPendingActions";
            try{var rewardJournal=new HeartOfTheRain.App.ServerRewards.ServerRewardJournal(Path.Combine(Application.persistentDataPath,"ServerReview","Rewards",IdentityProtocol82.Sha(config.origin),PlayerId,"rewards.json"),config.origin,PlayerId);if(rewardJournal.Read().hasPending)return "AccountPendingActions";}catch(Exception){return "AccountPendingStateUnavailable";}
            try{
                using(var storage=CreateProtectedSocialStore())
                using(var client=new SocialBackendClient82(config.origin,()=>identity.HasAccess?new SocialAccess82(PlayerId,identity.AccessToken):null,r=>StartCoroutine(r),storage,true,config.allowDevelopmentLoopback))
                    if(client.PendingCommand!=null)return "AccountPendingActions";
            }catch(Exception){return "AccountPendingStateUnavailable";}
            return null;
        }
        public string AccountTransitionBlocker()=>accountBlocked?"AccountSessionClosed":TransitionBlocker();
        public bool AccountCopyRecoveryToClipboard(){
            if(!Ready||busy||identity==null||identity.View.hasPending)return false;
            try{string code=identity.RecoverySecretForExplicitBackup();if(!IdentityProtocol82.Secret(code))return false;GUIUtility.systemCopyBuffer=code;return true;}catch(Exception){return false;}
        }
        public void AccountRefresh(Action<bool,string> done){
            if(accountBlocked){if(AccountIdentityPending)AccountResume(done);else Deliver(done,false,"AccountSessionClosed");return;}
            if(HasPending){Reconcile((ok,why)=>{if(ok)Refresh(done);else Deliver(done,false,why);});return;}Refresh(done);
        }
        public void AccountEndAttempt(bool confirmed,Action<bool,string> done){if(!confirmed){Deliver(done,false,"AccountConfirmationRequired");return;}Quit((ok,why)=>{if(ok)try{BindRecoveredAttemptDecision();}catch(Exception){Deliver(done,false,"AccountDecisionSaveUnconfirmed");return;}Deliver(done,ok,why);});}
        public void AccountRecover(string target,string code,bool confirmed,Action<bool,string> done){
            if(closed||busy){Deliver(done,false,"AccountBusy");return;}
            if(!confirmed||!IdentityProtocol82.Id(target)||!IdentityProtocol82.Secret(code)){Deliver(done,false,"AccountRecoveryInputInvalid");return;}
            if(accountBlocked){
                if(accountSelection?.purpose=="closed"){busy=true;StartCoroutine(AccountPrepareClosedRecovery(target,code,done));return;}
                if(accountSelection?.purpose!="recover"||accountSelection.targetPlayer!=target){Deliver(done,false,"AccountPendingActions");return;}
                busy=true;StartCoroutine(AccountRecoverRoutine(target,code,done));return;
            }
            string blocker=TransitionBlocker();if(blocker!=null){Deliver(done,false,blocker);return;}
            busy=true;StartCoroutine(AccountPrepareTransition("recover",target,code,done));
        }
        IEnumerator AccountPrepareClosedRecovery(string target,string code,Action<bool,string> done){
            try{accountSelection.purpose="recover";accountSelection.requestId=NewId();accountSelection.targetPlayer=target;accountSelection.pendingScope=NewAccountScope();accountSelection.recoveryRejected=false;SaveAccountSelection();}
            catch(Exception){busy=false;Deliver(done,false,"AccountIntentSaveUnconfirmed");yield break;}
            yield return AccountRecoverRoutine(target,code,done);
        }
        public void AccountStartAnotherRecovery(string target,string code,bool confirmed,Action<bool,string> done){
            if(!confirmed||closed||busy||accountSelectionConflict||!AccountCanStartAnotherRecovery||!IdentityProtocol82.Id(target)||!IdentityProtocol82.Secret(code)||accountSelection.retainedRecoveryScopes.Length>=8){Deliver(done,false,"AccountConfirmationRequired");return;}
            try{
                var scopes=new System.Collections.Generic.List<string>(accountSelection.retainedRecoveryScopes);scopes.Add(accountSelection.pendingScope);accountSelection.retainedRecoveryScopes=scopes.ToArray();
                pendingIdentity?.Dispose();pendingIdentityTransport?.Dispose();pendingIdentity=null;pendingIdentityTransport=null;
                accountSelection.pendingScope=NewAccountScope();accountSelection.requestId=NewId();accountSelection.targetPlayer=target;accountSelection.recoveryRejected=false;SaveAccountSelection();
            }catch(Exception){Deliver(done,false,"AccountIntentSaveUnconfirmed");return;}
            busy=true;StartCoroutine(AccountRecoverRoutine(target,code,done));
        }
        public void AccountLogout(bool confirmed,Action<bool,string> done)=>AccountClose("logout",confirmed,done);
        public void AccountRequestDeletion(bool confirmedTwice,Action<bool,string> done)=>AccountClose("delete",confirmedTwice,done);
        void AccountClose(string purpose,bool confirmed,Action<bool,string> done){
            if(!confirmed){Deliver(done,false,"AccountConfirmationRequired");return;}
            string blocker=TransitionBlocker();if(blocker!=null){Deliver(done,false,blocker);return;}
            busy=true;StartCoroutine(AccountPrepareTransition(purpose,null,null,done));
        }
        IEnumerator AccountPrepareTransition(string purpose,string target,string code,Action<bool,string> done){
            bool fresh=false;string why=null;yield return FetchWallet((ok,message)=>{fresh=ok;why=message;});
            busy=false;string blocker=fresh?TransitionBlocker():why;
            if(blocker!=null){Deliver(done,false,blocker);yield break;}busy=true;
            try{
                accountSelection.lastPlayer=PlayerId;accountSelection.blocked=true;accountSelection.purpose=purpose;accountSelection.requestId=NewId();accountSelection.targetPlayer=target??"";
                accountSelection.pendingScope=purpose=="recover"?NewAccountScope():"";accountBlocked=true;SaveAccountSelection();AccountInvalidatePrivateView();
            }catch(Exception){if(accountBlocked)AccountInvalidatePrivateView();busy=false;Deliver(done,false,"AccountIntentSaveUnconfirmed");yield break;}
            if(purpose=="recover")yield return AccountRecoverRoutine(target,code,done);else yield return AccountCloseRoutine(done);
        }
        IEnumerator AccountRecoverRoutine(string target,string code,Action<bool,string> done){
            IdentityReply82<IdentityView82> reply=null;
            try{
                if(accountSelectionDirty)SaveAccountSelection();
                if(pendingIdentity==null){pendingIdentityScope=accountSelection.pendingScope;pendingIdentity=NewScopedIdentity(pendingIdentityScope,out pendingIdentityTransport);}
                if(!pendingIdentity.View.hasSession){
                if(!pendingIdentity.View.hasPending&&code==null){busy=false;Deliver(done,false,"AccountRecoveryCodeRequired");yield break;}
                if(pendingIdentity.View.hasPending)pendingIdentity.Resume(r=>reply=r);else pendingIdentity.Recover(accountSelection.requestId,target,code,r=>reply=r);}
            }catch(Exception){busy=false;Deliver(done,false,"AccountRecoveryUnavailable");yield break;}
            if(pendingIdentity.View.hasSession){yield return PromoteRecoveredIdentity(done);yield break;}
            yield return AwaitIdentity(()=>reply!=null,pendingIdentity);
            if(reply==null||!reply.Succeeded){
                if(reply?.error=="IdentityHttp401"||reply?.error=="IdentityHttp422"){try{accountSelection.recoveryRejected=true;SaveAccountSelection();}catch(Exception){}}
                busy=false;Deliver(done,false,reply?.error??"AccountRecoveryUnknown");yield break;}
            yield return PromoteRecoveredIdentity(done);
        }
        IEnumerator PromoteRecoveredIdentity(Action<bool,string> done){
            try{
                if(!pendingIdentity.View.hasSession||(accountSelection.purpose=="recover"||accountSelection.purpose=="vk")&&pendingIdentity.View.playerId!=accountSelection.targetPlayer)throw new InvalidOperationException();
                PrepareRecoveredAttemptDecision();accountSelection.currentScope=string.IsNullOrEmpty(accountSelection.pendingScope)?pendingIdentityScope:accountSelection.pendingScope;accountSelection.lastPlayer=pendingIdentity.View.playerId;accountSelection.pendingScope="";accountSelection.purpose="";accountSelection.requestId="";accountSelection.targetPlayer="";accountSelection.blocked=false;SaveAccountSelection();
                var previous=identity;var previousTransport=identityTransport;identity=pendingIdentity;identityTransport=pendingIdentityTransport;try{previous?.Dispose();}catch(Exception){}try{previousTransport?.Dispose();}catch(Exception){}pendingIdentity=null;pendingIdentityTransport=null;accountBlocked=false;playerOwnershipEpoch++;generation++;IdentityChanged?.Invoke();
            }catch(Exception){busy=false;Deliver(done,false,"AccountSelectionConfirmationUnconfirmed");yield break;}
            // A recovered account's existing remote attempt needs an explicit
            // decision; recovery is not consent to forfeit another device's board.
            accountRecoveryBootstrap=true;yield return Bootstrap();accountRecoveryBootstrap=false;Deliver(done,Ready,error);
        }
        IEnumerator AccountCloseRoutine(Action<bool,string> done){
            IdentityReply82<IdentityView82> reply=null;
            try{
                if(accountSelectionDirty)SaveAccountSelection();
                if(identity.View.hasPending)identity.Resume(r=>reply=r);
                else if(!identity.View.hasSession){FinalizeClosedAccount();busy=false;Deliver(done,true,null);yield break;}
                else if(accountSelection.purpose=="delete")identity.RequestDeletion(accountSelection.requestId,r=>reply=r);else identity.Logout(accountSelection.requestId,r=>reply=r);
            }catch(Exception){busy=false;Deliver(done,false,"AccountCloseUnavailable");yield break;}
            yield return AwaitIdentity(()=>reply!=null,identity);
            if(reply==null||!reply.Succeeded){busy=false;Deliver(done,false,reply?.error??"AccountCloseUnknown");yield break;}
            try{FinalizeClosedAccount();busy=false;Deliver(done,true,null);}catch(Exception){busy=false;Deliver(done,false,"AccountCloseConfirmationUnconfirmed");}
        }
        // A coroutine can miss its transport timeout across an app suspend. The intent stays
        // in the journal and the player's next try resumes it.
        IEnumerator AwaitIdentity(Func<bool> replied,ManagedIdentitySession82 waiting){
            float limit=Time.unscaledTime+StallSeconds;while(!replied()&&!closed&&Time.unscaledTime<limit)yield return null;
            if(!replied()&&!closed)waiting?.Cancel();
        }
        // The server ended this device's session for good, usually after a recovery on another
        // device. Stop retrying and open the closed-account choices: Recover and Start fresh.
        bool CloseRefusedIdentity(string why){
            if(why!=IdentityHttpTransport82.SessionRefused||accountBlocked||accountSelection==null)return false;
            try{var lastPlayer=identity?.View.playerId;if(IdentityProtocol82.Id(lastPlayer))accountSelection.lastPlayer=lastPlayer;FinalizeClosedAccount();return true;}catch(Exception){return false;}
        }
        void FinalizeClosedAccount(){accountSelection.purpose="closed";accountSelection.requestId="";accountSelection.blocked=true;SaveAccountSelection();accountBlocked=true;AccountInvalidatePrivateView();error="AccountSessionClosed";}
        public void AccountResume(Action<bool,string> done){
            if(closed||busy||accountSelectionConflict||!accountBlocked||!AccountIdentityPending){Deliver(done,false,"AccountSessionUnavailable");return;}busy=true;
            if(accountSelection.purpose=="vk")StartCoroutine(VkResumeRoutine(done));
            else if(pendingIdentity!=null&&pendingIdentity.View.hasSession)StartCoroutine(PromoteRecoveredIdentity(done));
            else if(accountSelection.purpose=="recover")StartCoroutine(AccountRecoverRoutine(accountSelection.targetPlayer,null,done));
            else if(accountSelection.purpose=="fresh")StartCoroutine(AccountFreshRoutine(done));else StartCoroutine(AccountCloseRoutine(done));
        }
        public void AccountStartFresh(bool confirmed,Action<bool,string> done){
            if(!confirmed||closed||busy||!accountBlocked||accountSelection?.purpose!="closed"){Deliver(done,false,"AccountConfirmationRequired");return;}
            try{accountSelection.pendingScope=NewAccountScope();accountSelection.purpose="fresh";accountSelection.requestId=NewId();SaveAccountSelection();}catch(Exception){Deliver(done,false,"AccountIntentSaveUnconfirmed");return;}
            busy=true;StartCoroutine(AccountFreshRoutine(done));
        }
        IEnumerator AccountFreshRoutine(Action<bool,string> done){
            IdentityReply82<IdentityView82> reply=null;
            try{
                if(accountSelectionDirty)SaveAccountSelection();
                if(pendingIdentity==null){pendingIdentityScope=accountSelection.pendingScope;pendingIdentity=NewScopedIdentity(pendingIdentityScope,out pendingIdentityTransport);}
                if(!pendingIdentity.View.hasSession){if(pendingIdentity.View.hasPending)pendingIdentity.Resume(r=>reply=r);else pendingIdentity.CreateGuest(accountSelection.requestId,r=>reply=r);}
            }catch(Exception){busy=false;Deliver(done,false,"AccountFreshStartUnavailable");yield break;}
            if(pendingIdentity.View.hasSession){yield return PromoteRecoveredIdentity(done);yield break;}
            yield return AwaitIdentity(()=>reply!=null,pendingIdentity);if(reply==null||!reply.Succeeded){busy=false;Deliver(done,false,reply?.error??"AccountFreshStartUnknown");yield break;}
            yield return PromoteRecoveredIdentity(done);
        }
        void DisposeAccountState(){DisposeVkSignin();pendingIdentity?.Dispose();pendingIdentityTransport?.Dispose();accountSelector?.Dispose();
#if UNITY_EDITOR
            foreach(var item in editorAccountVaults.Values)item.Dispose();editorAccountVaults.Clear();
#endif
        }
    }
}

using System;
using UnityEngine;
using HeartOfTheRain.App.AccountDesign;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.ServerGameplay;

namespace HeartOfTheRain.App.ServerAccount {
    public sealed class ServerAccountControls83 {
        public bool ready,busy,blocked,pending,needsRecoveryEntry,activeAttempt,canRestartRecovery,canCopyRecovery;public string playerId,purpose,recoveryTarget,blocker;
    }
    public interface IManagedServerAccount83:IAccountService {
        event Action Changed;ServerAccountControls83 Controls{get;}
        void Refresh(Action<bool,string> done);bool CopyRecovery();
        void Recover(string playerId,string maskedCode,bool confirmed,Action<bool,string> done);
        void StartAnotherRecovery(string playerId,string maskedCode,bool confirmed,Action<bool,string> done);
        void Logout(bool confirmed,Action<bool,string> done);void Delete(bool confirmedTwice,Action<bool,string> done);
        void StartFresh(bool confirmed,Action<bool,string> done);void Resume(Action<bool,string> done);void EndAttempt(bool confirmed,Action<bool,string> done);
    }
    public sealed partial class ServerAccountService83:IManagedServerAccount83,IDisposable {
        readonly ServerGameSession gateway;bool disposed;public event Action Changed;
        public ServerAccountService83(ServerGameSession gateway){this.gateway=gateway??throw new ArgumentNullException(nameof(gateway));gateway.Changed+=Notify;gateway.IdentityChanged+=Notify;}
        public static IAccountService Select(HomePage home){var gateway=home?home.GetComponent<PlayerProfileHost>()?.ServerSession:null;return gateway?new ServerAccountService83(gateway):null;}
        void Notify(){blockerFrame=-1;var listeners=Changed;if(listeners!=null)foreach(Action listener in listeners.GetInvocationList())try{listener();}catch(Exception){}}
        public ServerAccountControls83 Controls=>disposed||!gateway?new ServerAccountControls83{blocked=true,blocker="AccountServiceClosed",playerId="",purpose="closed"}:new ServerAccountControls83{ready=!disposed&&gateway&&gateway.Ready,busy=gateway&&gateway.Busy,blocked=gateway&&gateway.AccountBlocked,pending=gateway&&gateway.AccountIdentityPending,needsRecoveryEntry=gateway&&gateway.AccountRecoveryRequiresEntry,activeAttempt=gateway&&gateway.HasActiveServerAttempt,canRestartRecovery=gateway&&gateway.AccountCanStartAnotherRecovery,canCopyRecovery=gateway&&gateway.AccountCanCopyRecovery,playerId=gateway?gateway.AccountStablePlayerId:"",purpose=gateway?gateway.AccountState:"",recoveryTarget=gateway?gateway.AccountRecoveryTarget:"",blocker=gateway?FrameBlocker():"AccountSessionUnavailable"};
        // The blocker reads protected journals through the Keystore, and one layout reads
        // it per button. Once a frame is enough; a state change invalidates it.
        int blockerFrame=-1;string frameBlocker;
        string FrameBlocker(){if(!Application.isPlaying)return gateway.AccountTransitionBlocker();if(blockerFrame!=Time.frameCount){frameBlocker=gateway.AccountTransitionBlocker();blockerFrame=Time.frameCount;}return frameBlocker;}
        public AccountStatus Read(){var state=Controls;return new AccountStatus{managed=true,serverSaved=state.ready&&!gateway.HasPending,online=Application.internetReachability!=NetworkReachability.NotReachable,localSaved=false,linked=false,canLink=false,playerId=state.playerId,provider="",sync=state.ready?AccountSync.Synced:AccountSync.Failed,confirmedServerSaveUtc=state.ready?gateway.Wallet.serverUtc:0};}
        public void Link(string provider,Action<AccountLinkResult> completed)=>completed?.Invoke(AccountLinkResult.Failed);
        void Call(Action<Action<bool,string>> operation,Action<bool,string> done){if(disposed||!gateway){done?.Invoke(false,"AccountServiceClosed");return;}operation((ok,why)=>done?.Invoke(!disposed&&ok,disposed?"AccountServiceClosed":why));}
        public void Refresh(Action<bool,string> done)=>Call(gateway.AccountRefresh,done);
        public bool CopyRecovery()=>!disposed&&gateway&&gateway.AccountCopyRecoveryToClipboard();
        public void Recover(string playerId,string maskedCode,bool confirmed,Action<bool,string> done)=>Call(callback=>gateway.AccountRecover(playerId,maskedCode,confirmed,callback),done);
        public void StartAnotherRecovery(string playerId,string maskedCode,bool confirmed,Action<bool,string> done)=>Call(callback=>gateway.AccountStartAnotherRecovery(playerId,maskedCode,confirmed,callback),done);
        public void Logout(bool confirmed,Action<bool,string> done)=>Call(callback=>gateway.AccountLogout(confirmed,callback),done);
        public void Delete(bool confirmedTwice,Action<bool,string> done)=>Call(callback=>gateway.AccountRequestDeletion(confirmedTwice,callback),done);
        public void StartFresh(bool confirmed,Action<bool,string> done)=>Call(callback=>gateway.AccountStartFresh(confirmed,callback),done);
        public void Resume(Action<bool,string> done)=>Call(gateway.AccountResume,done);
        public void EndAttempt(bool confirmed,Action<bool,string> done)=>Call(callback=>gateway.AccountEndAttempt(confirmed,callback),done);
        public void Dispose(){if(disposed)return;disposed=true;DisposeProvider();if(gateway){gateway.Changed-=Notify;gateway.IdentityChanged-=Notify;}Changed=null;}
    }
}

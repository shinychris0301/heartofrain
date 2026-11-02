using System;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Profile;
namespace HeartOfTheRain.App.AccountDesign {
    public enum AccountSync { LocalOnly, Pending, Synced, Failed }
    public enum AccountLinkResult { Completed, Cancelled, Failed }
    public sealed class AccountStatus {
        public bool linked,online=true,localSaved,canLink,managed,serverSaved;
        public string playerId="",provider="";
        public AccountSync sync;
        // Only a service-confirmed server timestamp can substantiate cloud saved.
        public long confirmedCloudSaveUtc,confirmedServerSaveUtc;
        public bool ServerSaved=>managed&&serverSaved&&sync==AccountSync.Synced&&confirmedServerSaveUtc>0&&confirmedServerSaveUtc<=253402300799L;
        public bool CloudSaved=>linked&&sync==AccountSync.Synced&&confirmedCloudSaveUtc>0&&confirmedCloudSaveUtc<=253402300799L;
        public string StatusKey=>managed?(ServerSaved?"serverSaved":"serverUnavailable"):CloudSaved?"saveCloudStatus":linked?(sync==AccountSync.Failed?"syncFailed":"syncPending"):localSaved?"saveLocalStatus":"localUnverified";
        public string EntryStatusKey=>managed?StatusKey:!linked&&!localSaved?"saveUnavailable":linked&&sync==AccountSync.Failed?"syncFailedBadge":StatusKey;
        public AccountStatus Copy()=>(AccountStatus)MemberwiseClone();
    }
    // Implementations own provider credentials and durable linking/sync. Callbacks
    // run on the Unity thread; presenting/dismissing a view never replaces a save.
    public interface IAccountService {
        AccountStatus Read();
        void Link(string provider,Action<AccountLinkResult> completed);
    }
    public sealed class LocalAccountService:IAccountService {
        readonly HomePage home;
        public LocalAccountService(HomePage owner){home=owner;}
        public AccountStatus Read(){
            var state=new AccountStatus{online=Application.internetReachability!=NetworkReachability.NotReachable};
            var host=home?home.GetComponent<PlayerProfileHost>():null;
            if(host&&host.Ready){try{state.playerId=host.Service.Read().playerId;state.localSaved=true;}catch(Exception){}}
            // Anonymous reward-service authentication is not a linked cloud save.
            return state;
        }
        public void Link(string provider,Action<AccountLinkResult> completed){completed?.Invoke(AccountLinkResult.Failed);}
    }
}

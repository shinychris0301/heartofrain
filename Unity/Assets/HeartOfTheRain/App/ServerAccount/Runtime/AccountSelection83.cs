using System;
using System.Text;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.App.OnlineIdentity;

namespace HeartOfTheRain.App.ServerAccount {
    [Serializable] public sealed class AccountSelectionState83 {
        public int version=1;public long revision;public string origin,currentScope,pendingScope,purpose="",requestId="",targetPlayer="",lastPlayer="";
        public bool blocked,recoveryRejected,recoveredAttemptDecision;public string recoveredAttemptId="";public string[] retainedRecoveryScopes=new string[0];
    }
    // Scope selection and close state share an encrypted CAS record. It holds
    // no bearer, refresh token, recovery code or arbitrary endpoint override.
    public sealed class AccountSelection83:IDisposable {
        readonly IProtectedSessionStore82 store;readonly string origin,initialScope;readonly UTF8Encoding utf8=new UTF8Encoding(false,true);string digest="";
        internal string CurrentDigest=>digest;
        public AccountSelection83(IProtectedSessionStore82 store,string origin,string initialScope){this.store=store??throw new ArgumentNullException(nameof(store));this.origin=origin;this.initialScope=initialScope;}
        public static bool Scope(string value)=>value!=null&&System.Text.RegularExpressions.Regex.IsMatch(value,@"\A[a-z][a-z0-9.-]{0,63}\z");
        void Validate(AccountSelectionState83 value){
            if(value==null||value.version!=1||value.revision<0||value.origin!=origin||!Scope(value.currentScope)||!string.IsNullOrEmpty(value.pendingScope)&&!Scope(value.pendingScope)||!new[]{"","recover","logout","delete","closed","fresh","vk"}.Contains(value.purpose))throw new InvalidOperationException("AccountSelectionInvalid");
            if(value.purpose!=""&&value.purpose!="closed"&&!IdentityProtocol82.Id(value.requestId))throw new InvalidOperationException("AccountSelectionIntentInvalid");
            if(value.retainedRecoveryScopes==null||value.retainedRecoveryScopes.Length>8||value.retainedRecoveryScopes.Any(s=>!Scope(s)))throw new InvalidOperationException("AccountRetainedScopeInvalid");
            if(!string.IsNullOrEmpty(value.recoveredAttemptId)&&!IdentityProtocol82.Id(value.recoveredAttemptId))throw new InvalidOperationException("AccountRecoveredAttemptBindingInvalid");
            if((value.purpose=="recover"||value.purpose=="vk")&&(!IdentityProtocol82.Id(value.targetPlayer)||!Scope(value.pendingScope)))throw new InvalidOperationException("AccountRecoveryBindingInvalid");
        }
        public AccountSelectionState83 Read(){
            byte[] bytes=store.Read();if(bytes==null){digest="";return new AccountSelectionState83{origin=origin,currentScope=initialScope};}
            string json=utf8.GetString(bytes);var value=JsonUtility.FromJson<AccountSelectionState83>(json);Validate(value);if(JsonUtility.ToJson(value)!=json)throw new InvalidOperationException("AccountSelectionCanonicalRequired");digest=IdentityProtocol82.Sha(bytes);return value;
        }
        public AccountSelectionState83 Save(AccountSelectionState83 value){
            Validate(value);var copy=JsonUtility.FromJson<AccountSelectionState83>(JsonUtility.ToJson(value));copy.revision=checked(value.revision+1);byte[] bytes=utf8.GetBytes(JsonUtility.ToJson(copy));
            store.CompareExchange(digest,bytes);var observed=Read();if(observed.revision!=copy.revision||JsonUtility.ToJson(observed)!=JsonUtility.ToJson(copy))throw new InvalidOperationException("AccountSelectionWriteUnconfirmed");return observed;
        }
        public void Dispose()=>store.Dispose();
    }
}

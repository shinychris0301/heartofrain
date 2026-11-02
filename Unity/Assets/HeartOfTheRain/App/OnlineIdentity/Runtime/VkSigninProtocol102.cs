using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using UnityEngine;

namespace HeartOfTheRain.App.OnlineIdentity {
    [Serializable] public sealed class VkSigninStatus102 {
        public string playerId,provider,phase,flowId,requestId,authorizeUrl,targetPlayerId;
        public bool available,requiresConfirmation;
        public long expiresAt,serverUtc;
        public bool Pending=>phase=="Pending"||phase=="Exchanging";
        public bool Terminal=>phase=="Completed"||phase=="Cancelled"||phase=="Expired"||phase=="Failed"||phase=="Conflict";
        public VkSigninStatus102 Copy()=>(VkSigninStatus102)MemberwiseClone();
    }
    // Contains credentials: serialize only to the encrypted origin-bound journal
    // or the bounded signed HTTPS completion request. Never to an ordinary save.
    [Serializable] public sealed class VkCompletionIntent102 {
        public string requestId,publicKey,flowId,targetPlayerId,flowSecret,refreshToken;
        public bool confirmed;
        public VkCompletionIntent102 Copy()=>(VkCompletionIntent102)MemberwiseClone();
        public bool Valid=>IdentityProtocol82.Id(requestId)&&flowId==requestId&&IdentityProtocol82.PublicKey(publicKey)
            &&IdentityProtocol82.Id(targetPlayerId)&&IdentityProtocol82.Secret(flowSecret)&&IdentityProtocol82.Secret(refreshToken)&&flowSecret!=refreshToken&&confirmed;
    }
    public static class VkSigninProtocol102 {
        public static bool OwnsSelection(VkSigninDocument102 value,HeartOfTheRain.App.ServerAccount.AccountSelectionState83 selection){
            return value!=null&&selection!=null&&Array.IndexOf(new[]{"Ready","Committing","Cancelled","Expired","Failed","Conflict"},value.phase)>=0&&selection.purpose=="vk"&&selection.blocked&&IdentityProtocol82.Id(value.requestId)
                &&selection.requestId==value.requestId&&selection.pendingScope==value.pendingScope&&selection.currentScope==value.sourceScope
                &&IdentityProtocol82.Id(selection.targetPlayer)&&(!value.Pending||selection.targetPlayer==value.targetPlayerId);
        }
        static string Canonical(SortedDictionary<string,string> fields)=>"{"+string.Join(",",fields.Select(p=>"\""+p.Key+"\":\""+p.Value+"\""))+"}";
        public static string PayloadDigest(VkCompletionIntent102 intent){
            if(intent==null||!intent.Valid)throw new InvalidOperationException("VkCompletionIntentInvalid");
            return IdentityProtocol82.Sha(Canonical(new SortedDictionary<string,string>(StringComparer.Ordinal){
                {"protocol",IdentityProtocol82.Protocol},{"purpose","vk"},{"requestId",intent.requestId},{"publicKey",intent.publicKey},
                {"flowId",intent.flowId},{"targetPlayerId",intent.targetPlayerId},{"flowDigest",IdentityProtocol82.Sha(intent.flowSecret)},
                {"refreshDigest",IdentityProtocol82.Sha(intent.refreshToken)},{"confirmed","true"}}));
        }
        public static byte[] ChallengeBytes(IdentityChallenge82 value,VkCompletionIntent102 intent){
            if(value==null||intent==null||!intent.Valid||value.algorithm!="ES256-DER"||!IdentityProtocol82.Id(value.challengeId)
                ||value.purpose!="vk"||value.requestId!=intent.requestId||value.keyFingerprint!=IdentityProtocol82.Fingerprint(intent.publicKey)
                ||value.payloadDigest!=PayloadDigest(intent)||!IdentityProtocol82.Secret(value.nonce)||value.serverUtc<=0||value.expiresAt-value.serverUtc!=60)
                throw new InvalidOperationException("VkChallengeBindingInvalid");
            var fields=new SortedDictionary<string,string>(StringComparer.Ordinal){
                {"challengeId","\""+value.challengeId+"\""},{"expiresAt",value.expiresAt.ToString(System.Globalization.CultureInfo.InvariantCulture)},
                {"keyFingerprint","\""+value.keyFingerprint+"\""},{"nonce","\""+value.nonce+"\""},
                {"payloadDigest","\""+value.payloadDigest+"\""},{"purpose","\"vk\""},{"requestId","\""+value.requestId+"\""}};
            byte[] expected=Encoding.ASCII.GetBytes(IdentityProtocol82.Protocol+"\n{"+string.Join(",",fields.Select(p=>"\""+p.Key+"\":"+p.Value))+"}");
            byte[] supplied;try{supplied=Convert.FromBase64String(value.signingBytes??"");}catch(FormatException){throw new InvalidOperationException("VkChallengeEncodingInvalid");}
            if(Convert.ToBase64String(supplied)!=value.signingBytes||!expected.SequenceEqual(supplied))throw new InvalidOperationException("VkChallengeBytesChanged");
            return expected;
        }
    }
    [Serializable] public sealed class VkSigninDocument102 {
        public int version=1;public long revision;
        public string origin,sourceScope,sourcePlayerId,pendingScope,requestId,flowSecret,refreshToken,targetPlayerId,phase="Empty";
        public bool Confirmed=>phase=="Committing"||phase=="Completed";
        public bool Pending=>phase!="Empty"&&phase!="Completed"&&phase!="Cancelled"&&phase!="Expired"&&phase!="Failed"&&phase!="Conflict";
        public VkCompletionIntent102 Completion(string publicKey)=>new VkCompletionIntent102{requestId=requestId,flowId=requestId,publicKey=publicKey,targetPlayerId=targetPlayerId,flowSecret=flowSecret,refreshToken=refreshToken,confirmed=Confirmed};
    }
    public sealed class VkSigninJournal102:IDisposable {
        readonly IProtectedSessionStore82 store;readonly string origin;string digest="";long observedRevision;
        static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
        public VkSigninJournal102(IProtectedSessionStore82 store,string origin){this.store=store??throw new ArgumentNullException(nameof(store));this.origin=origin;}
        void Validate(VkSigninDocument102 value){
            if(value==null||value.version!=1||value.revision<0||value.origin!=origin||Array.IndexOf(new[]{"Empty","Prepared","Pending","Exchanging","Ready","Committing","Completed","Cancelled","Expired","Failed","Conflict"},value.phase)<0)
                throw new InvalidOperationException("VkJournalInvalid");
            if(value.phase=="Empty")return;
            if(!HeartOfTheRain.App.ServerAccount.AccountSelection83.Scope(value.sourceScope)||!HeartOfTheRain.App.ServerAccount.AccountSelection83.Scope(value.pendingScope)
                ||value.sourceScope==value.pendingScope||!IdentityProtocol82.Id(value.sourcePlayerId)||!IdentityProtocol82.Id(value.requestId))throw new InvalidOperationException("VkJournalOwnerInvalid");
            if((value.Pending&&!IdentityProtocol82.Secret(value.flowSecret))||value.Pending&&!IdentityProtocol82.Secret(value.refreshToken)||value.Pending&&value.flowSecret==value.refreshToken)
                throw new InvalidOperationException("VkJournalProofInvalid");
            if((value.phase=="Ready"||value.Confirmed)&&!IdentityProtocol82.Id(value.targetPlayerId))throw new InvalidOperationException("VkJournalTargetInvalid");
        }
        public VkSigninDocument102 Read(){
            byte[] bytes=store.Read();if(bytes==null){digest="";observedRevision=0;return new VkSigninDocument102{origin=origin};}
            if(bytes.Length==0||bytes.Length>16384)throw new InvalidOperationException("VkJournalSizeInvalid");
            string json=Utf8.GetString(bytes);var value=JsonUtility.FromJson<VkSigninDocument102>(json);Validate(value);
            if(JsonUtility.ToJson(value)!=json)throw new InvalidOperationException("VkJournalCanonicalRequired");digest=IdentityProtocol82.Sha(bytes);observedRevision=value.revision;return value;
        }
        public VkSigninDocument102 Save(VkSigninDocument102 value){
            Validate(value);if(value.revision!=observedRevision)throw new InvalidOperationException("VkJournalRevisionChanged");var next=JsonUtility.FromJson<VkSigninDocument102>(JsonUtility.ToJson(value));next.revision=checked(value.revision+1);
            byte[] bytes=Utf8.GetBytes(JsonUtility.ToJson(next));string prior=digest;
            try{store.CompareExchange(prior,bytes);}catch{
                long priorRevision=value.revision;VkSigninDocument102 observed;
                try{observed=Read();}catch{digest=prior;observedRevision=priorRevision;throw;}
                if(JsonUtility.ToJson(observed)==JsonUtility.ToJson(next))return observed;
                digest=prior;observedRevision=priorRevision;throw;
            }
            var actual=Read();if(JsonUtility.ToJson(actual)!=JsonUtility.ToJson(next))throw new InvalidOperationException("VkJournalWriteUnconfirmed");return actual;
        }
        public void Dispose()=>store.Dispose();
    }
}

using System;
using System.Diagnostics;

namespace HeartOfTheRain.App.OnlineIdentity {
    public interface IVkIdentityTransport102 {
        void SubmitVk(VkCompletionIntent102 intent,string challengeId,string signature,Action<IdentityReply82<IdentitySessionResponse82>> done);
    }
    public sealed partial class IdentityHttpTransport82:IVkIdentityTransport102 {
        [Serializable] sealed class VkCompleteBody102 {public string requestId,challengeId,publicKey,signature,flowId,targetPlayerId,flowSecret,refreshToken;public bool confirmed;}
        public void SubmitVk(VkCompletionIntent102 intent,string challengeId,string signature,Action<IdentityReply82<IdentitySessionResponse82>> done){
            if(done==null)throw new ArgumentNullException(nameof(done));
            if(intent==null||!intent.Valid||!IdentityProtocol82.Id(challengeId)||string.IsNullOrEmpty(signature)||signature.Length<80||signature.Length>112){Deliver(done,IdentityReply82<IdentitySessionResponse82>.Fail("VkSignedIntentInvalid"));return;}
            Send("/v1/identity/vk/complete",new VkCompleteBody102{requestId=intent.requestId,challengeId=challengeId,publicKey=intent.publicKey,signature=signature,flowId=intent.flowId,targetPlayerId=intent.targetPlayerId,flowSecret=intent.flowSecret,refreshToken=intent.refreshToken,confirmed=intent.confirmed},ParseSessionResponse122,done);
        }
    }
    sealed partial class ProtectedSessionJournal82 {
        public IdentityDocument82 PromoteVk(VkCompletionIntent102 intent,IdentitySessionResponse82 response,string knownRecovery){
            string digest;var value=Read(out digest);
            if(value.hasPending||intent==null||!intent.Valid||response==null||response.playerId!=intent.targetPlayerId||response.keyFingerprint!=IdentityProtocol82.Fingerprint(publicKey)||intent.publicKey!=publicKey
                ||!string.IsNullOrEmpty(knownRecovery)&&!IdentityProtocol82.Secret(knownRecovery))throw new InvalidOperationException("VkSessionPromotionInvalid");
            if(value.hasCurrent){
                if(value.lastCompletedPurpose=="vk"&&value.lastCompletedRequest==intent.requestId&&value.current.playerId==response.playerId&&value.current.familyId==response.familyId&&value.current.refreshToken==intent.refreshToken)return value;
                throw new InvalidOperationException("VkSessionReplacementRequiresNewScope");
            }
            value.hasCurrent=true;value.current=new IdentityCredentials82{playerId=response.playerId,familyId=response.familyId,keyFingerprint=response.keyFingerprint,refreshToken=intent.refreshToken,recoverySecret=knownRecovery??"",refreshExpiresAt=response.refreshExpiresAt};
            value.lastCompletedRequest=intent.requestId;value.lastCompletedPurpose="vk";value.revision=checked(value.revision+1);return Write(digest,value);
        }
        public bool IsVkPromoted(VkCompletionIntent102 intent,IdentitySessionResponse82 response){
            string digest;var value=Read(out digest);return !value.hasPending&&value.hasCurrent&&value.lastCompletedPurpose=="vk"&&value.lastCompletedRequest==intent.requestId
                &&value.current.playerId==response.playerId&&value.current.familyId==response.familyId&&value.current.refreshToken==intent.refreshToken&&value.current.keyFingerprint==IdentityProtocol82.Fingerprint(publicKey);
        }
    }
    public sealed partial class ManagedIdentitySession82 {
        public string DevicePublicKey=>publicKey;
        public bool HasRecoveryBackup {
            get{if(disposed||busy)return false;try{string digest;var value=journal.Read(out digest);return value.hasCurrent&&!value.hasPending&&IdentityProtocol82.Secret(value.current.recoverySecret);}catch(Exception){return false;}}
        }
        // The caller MUST first persist this exact intent in VkSigninJournal102.
        // It uses a fresh scoped key; the previous account remains intact until
        // the separate durable selector explicitly promotes this session.
        public void CompleteVk(VkCompletionIntent102 intent,string knownRecovery,Action<IdentityReply82<IdentityView82>> done){
            if(!Ready(done))return;
            if(intent==null||!intent.Valid||intent.publicKey!=publicKey||!(transport is IVkIdentityTransport102)){Deliver(done,IdentityReply82<IdentityView82>.Fail("VkCompletionInvalid"));return;}
            try{string digest;var before=journal.Read(out digest);if(before.hasPending||before.hasCurrent&&(before.lastCompletedPurpose!="vk"||before.lastCompletedRequest!=intent.requestId))throw new InvalidOperationException();}
            catch(Exception){Deliver(done,IdentityReply82<IdentityView82>.Fail("VkCompletionScopeInvalid"));return;}
            busy=true;long token=++generation,began=Stopwatch.GetTimestamp();int challenged=0,submitted=0;
            try{transport.Challenge(new IdentityChallengeRequest82{purpose="vk",requestId=intent.requestId,publicKey=publicKey,payloadDigest=VkSigninProtocol102.PayloadDigest(intent)},challengeReply=>{
                if(disposed||generation!=token||System.Threading.Interlocked.Exchange(ref challenged,1)!=0)return;
                try{
                    if(challengeReply==null||!challengeReply.Succeeded){Finish(token,done,challengeReply?.error??"VkChallengeUnavailable",true);return;}
                    var challenge=challengeReply.value;byte[] bytes=VkSigninProtocol102.ChallengeBytes(challenge,intent);
                    if((Stopwatch.GetTimestamp()-began)/(double)Stopwatch.Frequency>=55){Finish(token,done,"VkChallengeExpired",true);return;}
                    string signature=Convert.ToBase64String(key.SignSha256Der(bytes));
                    ((IVkIdentityTransport102)transport).SubmitVk(intent.Copy(),challenge.challengeId,signature,reply=>{
                        if(disposed||generation!=token||System.Threading.Interlocked.Exchange(ref submitted,1)!=0)return;
                        try{
                            if(reply==null||!reply.Succeeded){Finish(token,done,reply?.error??"VkCompletionUnconfirmed",true);return;}
                            var response=reply.value;
                            if(response==null||response.requestId!=intent.requestId||response.playerId!=intent.targetPlayerId||!IdentityProtocol82.Id(response.familyId)
                                ||response.keyFingerprint!=IdentityProtocol82.Fingerprint(publicKey)||!IdentityProtocol82.Secret(response.accessToken)||response.accountState!="Active"
                                ||response.productionEnabled!=expectedProduction||response.normalUnityProfileIntegrated||response.expiresAt<=challenge.serverUtc||response.expiresAt>challenge.serverUtc+960
                                ||response.refreshExpiresAt<response.expiresAt||response.refreshExpiresAt>challenge.serverUtc+90L*86400+60)throw new InvalidOperationException();
                            try{journal.PromoteVk(intent,response,knownRecovery);}catch(Exception){if(!journal.IsVkPromoted(intent,response)){Finish(token,done,"VkSuccessorSaveUnconfirmed",true);return;}}
                            access=response.accessToken;accessPlayerId=response.playerId;accessAt=began;accessSeconds=Math.Min(900,response.expiresAt-challenge.serverUtc);Finish(token,done,null);
                        }catch(Exception){Finish(token,done,"VkBoundConfirmationInvalid",true);}
                    });
                }catch(Exception){Finish(token,done,"VkChallengeOrSigningInvalid",true);}
            });}catch(Exception){Finish(token,done,"VkDispatchUnavailable",true);}
        }
    }
}

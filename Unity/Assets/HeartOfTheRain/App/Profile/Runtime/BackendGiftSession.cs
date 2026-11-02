using System;
using System.Collections;
namespace HeartOfTheRain.App.Profile {
    // A cache bridge lets the established durable intent/decision transaction
    // remain authoritative while HTTP runs asynchronously between model calls.
    // It does not replace the existing Home factory or its development service.
    public sealed class BackendGiftSession {
        sealed class NeedsDecision:Exception {}
        sealed class Bridge:IDailyGiftAuthority {
            public bool IsDevelopment=>false;
            public GiftOffer offer;public GiftDecision decision;public bool expired;
            public GiftOffer Offer(string player)=>offer;
            public GiftDecision Claim(string player,PendingGift request){if(expired)throw new GiftExpiredException();if(decision==null||decision.requestId!=request.requestId)throw new NeedsDecision();return decision;}
        }
        readonly ProfileService profile;readonly BackendClient client;readonly Bridge bridge=new Bridge();readonly DailyGiftService gifts;
        bool busy,verified;
        public GiftOffer Offer=>bridge.offer;
        public BackendGiftSession(ProfileService profile,BackendClient client,GiftSchedule schedule){this.profile=profile??throw new ArgumentNullException(nameof(profile));this.client=client??throw new ArgumentNullException(nameof(client));gifts=new DailyGiftService(profile,bridge,schedule);}
        IEnumerator Verify(Action<bool,string> done){
            if(verified){done(true,null);yield break;}BackendResult<BackendAccount> response=null;yield return client.Account(value=>response=value);
            if(response==null||!response.ok){done(false,response?.error??"network_unavailable");yield break;}
            string player=null;try{player=profile.Read().playerId;}catch(Exception){}if(player==null){done(false,"local_claim_unavailable");yield break;}
            if(response.value.playerId!=player){done(false,"account_mismatch");yield break;}verified=true;done(true,null);
        }
        public IEnumerator Refresh(Action<bool,string> done){
            if(busy){done(false,"busy");yield break;}busy=true;
            try{bool identified=false;string why=null;yield return Verify((ok,error)=>{identified=ok;why=error;});if(!identified){done(false,why);yield break;}BackendResult<BackendOffer> response=null;yield return client.Offer(value=>response=value);
                if(response==null||!response.ok){done(false,response?.error??"network_unavailable");yield break;}
                var value=response.value;if(string.IsNullOrEmpty(value.id)||string.IsNullOrEmpty(value.schedule)||value.day<0||value.step<0||value.step>6||value.grant==null){done(false,"invalid_response");yield break;}
                bool valid;try{value.grant.Validate();valid=true;}catch(Exception){valid=false;}if(!valid){done(false,"invalid_response");yield break;}
                bridge.offer=value.Offer();done(true,null);
            }finally{busy=false;}
        }
        public IEnumerator Claim(Action<RewardGrant,string> done){
            if(busy){done(null,"busy");yield break;}
            PlayerProfile saved=null;try{saved=profile.Read();}catch(Exception){}if(saved==null){done(null,"local_claim_unavailable");yield break;}
            if(saved.pendingGift==null){bool refreshed=false;string error=null;yield return Refresh((ok,why)=>{refreshed=ok;error=why;});if(!refreshed){done(null,error);yield break;}}
            busy=true;
            try{
                bool identified=false;string why=null;yield return Verify((ok,error)=>{identified=ok;why=error;});if(!identified){done(null,why);yield break;}
                bridge.decision=null;bridge.expired=false;RewardGrant grant=null;string localError=null;
                try{grant=gifts.Claim();}catch(NeedsDecision){}catch(Exception){localError="local_claim_unavailable";}
                if(localError!=null){done(null,localError);yield break;}
                saved=null;try{saved=profile.Read();}catch(Exception){}if(saved==null){done(null,"local_claim_unavailable");yield break;}var pending=saved.pendingGift;if(pending==null){done(grant,null);yield break;}
                BackendResult<BackendDecision> response=null;yield return client.Claim(pending,value=>response=value);
                if(response==null||!response.ok){
                    if(response?.status==410){bridge.expired=true;try{gifts.Claim();}catch(GiftExpiredException){}catch(Exception){localError="local_claim_unavailable";}}
                    done(null,localError??response?.error??"network_unavailable");yield break;
                }
                bridge.decision=response.value.Decision();
                // Existing DailyGiftService checks player, command, offer, day,
                // configured quantities and receipt before committing any credit.
                try{grant=gifts.Claim();}catch(Exception){localError="claim_confirmation_unavailable";}
                if(localError==null){var decision=bridge.decision;bridge.offer=new GiftOffer{id=decision.receiptId,schedule=decision.schedule,day=decision.day,step=decision.step,grant=decision.grant.Copy(),claimed=true};}
                done(grant,localError);
            }finally{busy=false;}
        }
    }
}

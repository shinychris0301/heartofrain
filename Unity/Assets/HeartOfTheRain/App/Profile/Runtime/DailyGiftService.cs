using System;
using System.Linq;
namespace HeartOfTheRain.App.Profile {
    [Serializable] public sealed class GiftSchedule {
        public string version="daily-preview-v1";public RewardGrant[] days;
        public void Validate(){if(string.IsNullOrEmpty(version)||version.Length>128||days==null||days.Length!=7)throw new InvalidOperationException("Invalid daily schedule");foreach(var d in days){if(d==null)throw new InvalidOperationException("Missing daily reward");d.Validate();}}
        public GiftSchedule Copy()=>new GiftSchedule{version=version,days=days.Select(d=>d.Copy()).ToArray()};
        public static GiftSchedule Preview()=>new GiftSchedule{days=new[]{
            new RewardGrant{coins=50},new RewardGrant{starting=new[]{1,0,0,0}},new RewardGrant{coins=75},new RewardGrant{starting=new[]{0,1,0,0}},new RewardGrant{coins=100},new RewardGrant{tools=new[]{1,0,0,0}},new RewardGrant{coins=150,starting=new[]{0,0,1,0}}
        }};
    }
    public sealed class GiftOffer {public string id,schedule;public long day;public int step;public bool claimed;public RewardGrant grant;}
    public sealed class GiftDecision {public string playerId,receiptId,requestId,schedule;public long day;public int step;public RewardGrant grant;}
    public interface IDailyGiftAuthority {
        bool IsDevelopment {get;}
        GiftOffer Offer(string playerId);
        GiftDecision Claim(string playerId,PendingGift request);
    }
    public sealed class GiftExpiredException:Exception {}
    public sealed class UnavailableGiftAuthority:IDailyGiftAuthority {
        public bool IsDevelopment=>false;
        public GiftOffer Offer(string playerId)=>null;
        public GiftDecision Claim(string playerId,PendingGift request){throw new InvalidOperationException("Daily Gift is unavailable");}
    }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
    // Explicitly untrusted LOCAL development service. Separate repository and
    // receipt namespace; never selected by the release factory. It simulates
    // remote confirmation/retry so no server-security claim is implied.
    public sealed class DevelopmentGiftAuthority:IDailyGiftAuthority {
        readonly ProfileService ledger;readonly Func<long> day;readonly GiftSchedule schedule;
        public bool Offline;public Action<string> Checkpoint;
        public bool IsDevelopment=>true;
        public DevelopmentGiftAuthority(IProfileRepository repository,Func<long> day,GiftSchedule schedule){this.ledger=new ProfileService(repository);this.day=day;schedule.Validate();this.schedule=schedule.Copy();}
        static string Id(string player,long day,string version)=>"dev-daily/"+player+"/"+version+"/"+day;
        public GiftOffer Offer(string playerId){
            if(Offline)return null;var p=ledger.Read();if(p.playerId!=playerId)throw new InvalidOperationException("Gift authority identity mismatch");long now=day();if(now<0||now<p.lastGiftDay)return null;
            int step=p.lastGiftDay==now?Math.Max(0,p.giftClaims-1)%7:p.giftClaims%7;
            return new GiftOffer{id=Id(playerId,now,schedule.version),day=now,step=step,schedule=schedule.version,claimed=p.lastGiftDay==now,grant=schedule.days[step].Copy()};
        }
        public GiftDecision Claim(string playerId,PendingGift request){
            if(Offline)throw new InvalidOperationException("Daily Gift is unavailable");
            var decision=ledger.Change(p=>{
                if(p.playerId!=playerId)throw new InvalidOperationException("Gift authority identity mismatch");
                var previous=p.rewards.FirstOrDefault(r=>r.key==request.offerId);
                if(previous!=null){if(previous.source!=request.schedule+":"+request.step)throw new InvalidOperationException("Gift request contents changed");return Decision(playerId,request,previous.grant);}
                if(request.day!=day()||request.day<=p.lastGiftDay||request.schedule!=schedule.version||request.step!=p.giftClaims%7||request.offerId!=Id(playerId,request.day,schedule.version))throw new GiftExpiredException();
                var grant=schedule.days[request.step];ProfileService.ApplyGrant(p,request.offerId,request.schedule+":"+request.step,grant);p.lastGiftDay=request.day;p.giftClaims=checked(p.giftClaims+1);return Decision(playerId,request,grant);
            });
            Checkpoint?.Invoke("AuthorityCommitted");return decision;
        }
        static GiftDecision Decision(string player,PendingGift request,RewardGrant grant)=>new GiftDecision{playerId=player,receiptId=request.offerId,requestId=request.requestId,day=request.day,step=request.step,schedule=request.schedule,grant=grant.Copy()};
    }
#endif
    public sealed class DailyGiftService {
        readonly ProfileService profile;readonly IDailyGiftAuthority authority;readonly GiftSchedule schedule;
        public bool IsDevelopment=>authority.IsDevelopment;
        public DailyGiftService(ProfileService profile,IDailyGiftAuthority authority,GiftSchedule schedule){this.profile=profile;this.authority=authority;schedule.Validate();this.schedule=schedule.Copy();}
        public GiftOffer Offer(){var p=profile.Read();return authority.Offer(p.playerId);}
        public RewardGrant Claim(){
            var snapshot=profile.Read();var request=snapshot.pendingGift;
            if(request==null){
                var offer=authority.Offer(snapshot.playerId);if(offer==null)throw new InvalidOperationException("Daily Gift is unavailable");if(offer.claimed)return null;
                if(offer.day<=snapshot.lastGiftDay||offer.step!=snapshot.giftClaims%7||offer.schedule!=schedule.version||string.IsNullOrEmpty(offer.id)||offer.id.Length>256||offer.grant==null)throw new InvalidOperationException("Invalid daily offer");
                offer.grant.Validate();var configured=schedule.days[offer.step];if(offer.grant.coins!=configured.coins||offer.grant.stars!=configured.stars||!offer.grant.starting.SequenceEqual(configured.starting)||!offer.grant.tools.SequenceEqual(configured.tools))throw new InvalidOperationException("Daily offer differs from configured reward");
                string id=Guid.NewGuid().ToString("N");request=profile.Change(p=>{
                    if(p.pendingGift!=null)return p.pendingGift;
                    if(offer.day<=p.lastGiftDay||offer.step!=p.giftClaims%7)throw new InvalidOperationException("Daily offer changed");
                    return p.pendingGift=new PendingGift{requestId=id,offerId=offer.id,day=offer.day,step=offer.step,schedule=offer.schedule,expectedGrant=offer.grant.Copy()};
                });
            }
            GiftDecision receipt;
            try{receipt=authority.Claim(snapshot.playerId,request);}
            catch(GiftExpiredException){profile.Change(p=>{if(p.pendingGift!=null&&p.pendingGift.requestId==request.requestId)p.pendingGift=null;return true;});throw;}
            if(receipt==null||receipt.playerId!=snapshot.playerId||receipt.requestId!=request.requestId||receipt.receiptId!=request.offerId||receipt.day!=request.day||receipt.step!=request.step||receipt.schedule!=request.schedule||receipt.grant==null)throw new InvalidOperationException("Gift confirmation does not match its request");
            var expected=request.expectedGrant;var got=receipt.grant;got.Validate();
            if(got.coins!=expected.coins||got.stars!=expected.stars||!got.starting.SequenceEqual(expected.starting)||!got.tools.SequenceEqual(expected.tools))throw new InvalidOperationException("Gift confirmation differs from schedule");
            bool applied=profile.Change(p=>{
                if(p.rewards.Any(r=>r.key==receipt.receiptId)){ProfileService.ApplyGrant(p,receipt.receiptId,"daily/"+request.schedule,got);if(p.pendingGift!=null&&p.pendingGift.requestId==request.requestId)p.pendingGift=null;return false;}
                if(p.pendingGift==null||p.pendingGift.requestId!=request.requestId||p.lastGiftDay>=receipt.day||p.giftClaims%7!=request.step)throw new InvalidOperationException("Gift claim state changed");
                ProfileService.ApplyGrant(p,receipt.receiptId,"daily/"+request.schedule,got);p.lastGiftDay=receipt.day;p.giftClaims=checked(p.giftClaims+1);p.pendingGift=null;return true;
            });
            return applied?got:null;
        }
    }
}

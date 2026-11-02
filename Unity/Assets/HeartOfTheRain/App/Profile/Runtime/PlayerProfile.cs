using System;
using System.Collections.Generic;
using System.Linq;
namespace HeartOfTheRain.App.Profile {
    [Serializable] public sealed class RewardGrant {
        public int coins,stars;public int[] starting=new int[4],tools=new int[4];
        public void Validate(){if(coins<0||stars<0||starting==null||tools==null||starting.Length!=4||tools.Length!=4||starting.Any(n=>n<0)||tools.Any(n=>n<0))throw new InvalidOperationException("Invalid reward grant");}
        public RewardGrant Copy()=>new RewardGrant{coins=coins,stars=stars,starting=(int[])starting.Clone(),tools=(int[])tools.Clone()};
    }
    [Serializable] public sealed class AttemptRecord {
        public string id,config,state;public int level,coins,stars;public int[] selected=new int[4];
        public int completedBefore,completedAfter,awardedCoins,awardedStars,livesAfter;public bool firstClear;
        public List<string> toolCommands=new List<string>();
        public string rainCupId;public int rainCupPoint;public long rainCupWinAt;
        // Refill RNG seed for this attempt (owner decision, 22 October 2026):
        // derived from the attempt id, so retries differ and a receipt replays.
        public long seed;
        public ContinueJournal continuation=new ContinueJournal();
    }
    [Serializable] public sealed class RewardReceipt {
        public string key,source;public RewardGrant grant;
    }
    [Serializable] public sealed class DirectPurchaseIntent {
        public string orderId,commandId,productId,storeProductId,developerPayload,purchaseId,invoiceId,phase;
        public int amountMinor;public bool sandbox;
    }
    [Serializable] public sealed class DirectPurchaseReceipt {
        public string purchaseId,invoiceId,orderId,productId,storeProductId,phase;
        public int amountMinor;public bool sandbox;
    }
    [Serializable] public sealed class LifeCreditReceipt {public string key;public long at;public int lives;}
    [Serializable] public sealed class LifeRefillReceipt {public string key;public long at;public int coins,livesBefore,livesAfter;}
    // Owner decisions: one life every 30 minutes up to maxLives (22 October 2026),
    // and a full refill at zero lives for 900 coins (24 October 2026). Times are
    // device UTC seconds until a trusted time service exists.
    public static class LifeRules {public const int RegenerationSeconds=1800,RefillCoins=900;}
    [Serializable] public sealed class PendingGift {
        public string requestId,offerId;public long day;public int step;public string schedule;public RewardGrant expectedGrant;
    }
    [Serializable] public sealed class PlayerProfile {
        public int schemaVersion=1;public long revision;public string playerId;
        public int coins=1250,stars,lives=5,maxLives=5,completed,currentLevel=1;
        public int[] starting={5,5,3,2},tools={3,3,3,3};
        public List<AttemptRecord> attempts=new List<AttemptRecord>();
        public List<RewardReceipt> rewards=new List<RewardReceipt>();
        // The receipt and its wallet grant are committed in the same profile revision.
        public List<DirectPurchaseIntent> directPurchaseIntents=new List<DirectPurchaseIntent>();
        public List<DirectPurchaseReceipt> directPurchaseReceipts=new List<DirectPurchaseReceipt>();
        public List<RainCupRun> rainCups=new List<RainCupRun>();
        public int giftClaims;public long lastGiftDay=-1;
        // Unix seconds at which the next life is due; 0 while lives are full.
        public long livesRefillDueUnix;public List<LifeCreditReceipt> lifeCredits=new List<LifeCreditReceipt>();public List<LifeRefillReceipt> lifeRefills=new List<LifeRefillReceipt>();
        // Unity serializes inline class fields as objects even when null. Keep
        // presence explicit so a completed/absent claim survives a JSON roundtrip.
        [UnityEngine.SerializeField] bool hasPendingGift;
        [UnityEngine.SerializeField] PendingGift pendingGiftValue;
        public PendingGift pendingGift {get=>hasPendingGift?pendingGiftValue:null;set{pendingGiftValue=value;hasPendingGift=value!=null;}}
        public static PlayerProfile New(int[] initial){
            if(initial==null||(initial.Length!=3&&initial.Length!=4)||initial.Any(n=>n<0))throw new ArgumentException("Invalid initial inventory");
            return new PlayerProfile{playerId=Guid.NewGuid().ToString("N"),starting=initial.Length==3?new[]{initial[0],initial[0],initial[1],initial[2]}:(int[])initial.Clone()};
        }
        public void Validate(){
            // Older version-1 profiles predate direct-pay journals. Missing lists
            // are empty, while an invalid populated journal still fails closed.
            if(directPurchaseIntents==null)directPurchaseIntents=new List<DirectPurchaseIntent>();
            if(directPurchaseReceipts==null)directPurchaseReceipts=new List<DirectPurchaseReceipt>();
            Guid id;if(schemaVersion!=1||!Guid.TryParseExact(playerId,"N",out id)||revision<0)throw new InvalidOperationException("Unsupported or invalid profile");
            if(coins<0||stars<0||maxLives<1||lives<0||lives>maxLives||completed<0||completed>50||currentLevel<1||currentLevel>Math.Min(50,completed+1))throw new InvalidOperationException("Invalid profile progression or balances");
            new RewardGrant{starting=starting,tools=tools}.Validate();
            if(attempts==null||rewards==null||attempts.Count>100000||rewards.Count>100000||giftClaims<0||lastGiftDay< -1)throw new InvalidOperationException("Invalid profile journal");
            var ids=new HashSet<string>();int active=0;
            foreach(var a in attempts){
                if(a==null||!Guid.TryParseExact(a.id,"N",out id)||!ids.Add(a.id)||string.IsNullOrEmpty(a.config)||a.config.Length>128||a.level<1||a.level>50||a.coins<0||a.stars<0||a.selected==null||a.selected.Length!=4||a.selected.Any(n=>n<0||n>1)||a.toolCommands==null||a.toolCommands.Count>100000||a.toolCommands.Any(string.IsNullOrEmpty)||a.toolCommands.Distinct().Count()!=a.toolCommands.Count)throw new InvalidOperationException("Invalid attempt journal");
                if(a.state=="Reserved"||a.state=="Started")active++;else if(a.state!="Cancelled"&&a.state!="Won"&&a.state!="Lost"&&a.state!="Interrupted"&&a.state!="Released")throw new InvalidOperationException("Invalid attempt state");
                if(a.awardedCoins<0||a.awardedStars<0||a.completedBefore<0||a.completedAfter<a.completedBefore||a.completedAfter>50||a.livesAfter<0||a.seed<0||a.seed>uint.MaxValue)throw new InvalidOperationException("Invalid settlement receipt");
                ContinueJournal.Validate(a);
            }
            if(active>1)throw new InvalidOperationException("Conflicting attempts");
            ids.Clear();foreach(var r in rewards){if(r==null||string.IsNullOrEmpty(r.key)||r.key.Length>256||!ids.Add(r.key)||string.IsNullOrEmpty(r.source)||r.grant==null)throw new InvalidOperationException("Invalid reward receipt");r.grant.Validate();}
            if(directPurchaseIntents==null||directPurchaseReceipts==null||directPurchaseIntents.Count>100000||directPurchaseReceipts.Count>100000)throw new InvalidOperationException("Invalid direct purchase journal");
            ids.Clear();foreach(var i in directPurchaseIntents){
                if(i==null||!Guid.TryParseExact(i.orderId,"N",out id)||!ids.Add(i.orderId)||!Guid.TryParseExact(i.commandId,"N",out id)||string.IsNullOrWhiteSpace(i.productId)||string.IsNullOrWhiteSpace(i.storeProductId)||i.developerPayload!="hotr-order-v1:"+i.orderId+":"+i.commandId||i.amountMinor<=0||!new[]{"Intent","Dispatched","OutcomeUnknown","Confirmed","Acknowledged","Terminal","RefundReview"}.Contains(i.phase))throw new InvalidOperationException("Invalid direct purchase intent");
            }
            ids.Clear();foreach(var r in directPurchaseReceipts){
                if(r==null||!Guid.TryParse(r.purchaseId,out id)||!ids.Add(r.purchaseId)||!Guid.TryParseExact(r.orderId,"N",out id)||string.IsNullOrWhiteSpace(r.productId)||string.IsNullOrWhiteSpace(r.storeProductId)||r.amountMinor<=0||!new[]{"Credited","Acknowledged","RefundReview"}.Contains(r.phase)||
                    !directPurchaseIntents.Any(i=>i.orderId==r.orderId&&i.productId==r.productId&&i.storeProductId==r.storeProductId&&i.purchaseId==r.purchaseId)||
                    !rewards.Any(v=>v.key=="rustore:"+r.purchaseId&&v.source=="rustore-direct"))throw new InvalidOperationException("Invalid direct purchase receipt");
            }
            if(livesRefillDueUnix<0||lifeCredits==null||lifeRefills==null||lifeCredits.Count>100000||lifeRefills.Count>100000)throw new InvalidOperationException("Invalid life journal");
            ids.Clear();foreach(var c in lifeCredits){if(c==null||!Guid.TryParseExact(c.key,"N",out id)||!ids.Add(c.key)||c.at<0||c.lives<1||c.lives>maxLives)throw new InvalidOperationException("Invalid life credit receipt");}
            ids.Clear();foreach(var r in lifeRefills){if(r==null||!Guid.TryParseExact(r.key,"N",out id)||!ids.Add(r.key)||r.at<0||r.coins<1||r.livesBefore<0||r.livesAfter<=r.livesBefore||r.livesAfter>maxLives)throw new InvalidOperationException("Invalid life refill receipt");}
            if(hasPendingGift){if(pendingGift==null||!Guid.TryParseExact(pendingGift.requestId,"N",out id)||pendingGift.day<0||pendingGift.step<0||pendingGift.step>6||string.IsNullOrEmpty(pendingGift.offerId)||string.IsNullOrEmpty(pendingGift.schedule)||pendingGift.expectedGrant==null)throw new InvalidOperationException("Invalid pending gift");pendingGift.expectedGrant.Validate();}
            RainCupModel.Validate(this);
        }
    }
    public sealed class ProfileConflictException:Exception {public ProfileConflictException():base("The saved profile changed"){} }
    public interface IProfileRepository {PlayerProfile Read();PlayerProfile Commit(long expectedRevision,PlayerProfile next);}
    public sealed partial class ProfileService {
        readonly IProfileRepository repository;
        // Reservation rule messages are player outcomes the pre-level shows
        // (localized there); any other failure is a lost write.
        public const string AttemptInProgress="An attempt is already in progress",NoLives="No lives remaining",LevelLocked="This level is locked",BoosterUnavailable="A selected booster is unavailable";
        public static bool IsReservationRule(string message)=>message==AttemptInProgress||message==NoLives||message==LevelLocked||message==BoosterUnavailable;
        public ProfileService(IProfileRepository repository){this.repository=repository??throw new ArgumentNullException(nameof(repository));}
        public PlayerProfile Read()=>repository.Read();
        public T Change<T>(Func<PlayerProfile,T> update){
            for(int i=0;i<4;i++){var p=repository.Read();long revision=p.revision;T result=update(p);try{repository.Commit(revision,p);return result;}catch(ProfileConflictException){}}
            throw new ProfileConflictException();
        }
        public AttemptRecord Reserve(string id,int level,string config,int[] selected,int coins,int stars){
            return Change(p=>{
                var old=p.attempts.FirstOrDefault(a=>a.id==id);
                if(old!=null){if(old.level!=level||old.config!=config||!old.selected.SequenceEqual(selected)||old.coins!=coins||old.stars!=stars)throw new InvalidOperationException("Attempt key reused with different contents");return old;}
                if(p.attempts.Any(a=>a.state=="Reserved"||a.state=="Started"))throw new InvalidOperationException(AttemptInProgress);
                if(p.lives<=0)throw new InvalidOperationException(NoLives);
                if(level<1||level>Math.Min(50,p.completed+1))throw new InvalidOperationException(LevelLocked);
                if(selected==null||selected.Length!=4||selected.Any(n=>n<0||n>1)||coins<0||stars<0)throw new InvalidOperationException("Cannot reserve this attempt");
                if(selected.Where((n,i)=>n>p.starting[i]).Any())throw new InvalidOperationException(BoosterUnavailable);
                var cup=p.rainCups.LastOrDefault(r=>r.state=="Active");var record=new AttemptRecord{id=id,level=level,config=config,state="Reserved",selected=(int[])selected.Clone(),coins=coins,stars=stars,rainCupId=cup?.id,seed=AttemptSeed(id)};p.attempts.Add(record);return record;
            });
        }
        // Non-zero 32-bit refill seed for an attempt. Verification replays and
        // review scenes keep passing the authored tileSeed to BoardModel directly.
        public static uint AttemptSeed(string attemptId){
            if(string.IsNullOrEmpty(attemptId))throw new ArgumentException("Attempt id required");
            uint seed=Convert.ToUInt32(ProfileJson.Hash("hotr-attempt-seed-v1|"+attemptId).Substring(0,8),16);return seed==0?1u:seed;
        }
        static AttemptRecord Find(PlayerProfile p,string id){var a=p.attempts.FirstOrDefault(v=>v.id==id);if(a==null)throw new InvalidOperationException("Unknown attempt");return a;}
        public AttemptRecord CommitStart(string id)=>Change(p=>{var a=Find(p,id);if(a.state=="Started")return a;if(a.state!="Reserved"||p.lives<=0||a.selected.Where((n,i)=>n>p.starting[i]).Any())throw new InvalidOperationException("Cannot start this attempt");for(int i=0;i<4;i++)p.starting[i]-=a.selected[i];a.state="Started";return a;});
        public void CancelReservation(string id){Change(p=>{var a=Find(p,id);if(a.state=="Cancelled")return false;if(a.state!="Reserved")throw new InvalidOperationException("Cannot cancel a committed start");a.state="Cancelled";return true;});}
        // An engine fault (the resolution guard) ends a started attempt without
        // a player outcome: no life charge, and the starting items debited at
        // CommitStart return to stock (owner decision, 22 October 2026). Tools
        // already used stay spent. "Released" keeps the debit, tool and refund
        // receipts distinct from an attempt cancelled before it started.
        public bool ReleaseFault(string id)=>Change(p=>{var a=Find(p,id);if(a.state=="Released")return false;if(a.state!="Started")throw new InvalidOperationException("Only a started attempt can be released");for(int i=0;i<4;i++)p.starting[i]=checked(p.starting[i]+a.selected[i]);a.livesAfter=p.lives;a.state="Released";return true;});
        public AttemptRecord Win(string id,long? rainCupTime=null)=>Change(p=>{
            var a=Find(p,id);if(a.state=="Won")return a;if(a.state!="Started"||a.level>p.completed+1)throw new InvalidOperationException("Cannot settle this attempt as won");
            a.completedBefore=p.completed;a.firstClear=a.level==p.completed+1;
            if(a.firstClear){p.coins=checked(p.coins+a.coins);p.stars=checked(p.stars+a.stars);p.completed++;p.currentLevel=Math.Min(50,p.completed+1);a.awardedCoins=a.coins;a.awardedStars=a.stars;}
            a.completedAfter=p.completed;a.livesAfter=p.lives;a.state="Won";
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(rainCupTime.HasValue)DevelopmentRainCupService.RecordWin(p,a,rainCupTime.Value);
#endif
            return a;
        });
        public AttemptRecord Lose(string id,bool interrupted=false)=>Change(p=>{
            var a=Find(p,id);if(a.state=="Lost"||a.state=="Interrupted")return a;if(a.state!="Started")throw new InvalidOperationException("Cannot settle this attempt as lost");
            if(!string.IsNullOrEmpty(a.continuation.pending))throw new InvalidOperationException("Continue requires reconciliation");
            // A loss never moves the current level: replaying an earlier level
            // must not send Home's Play button back to it.
            p.lives=Math.Max(0,p.lives-1);a.livesAfter=p.lives;a.completedBefore=a.completedAfter=p.completed;a.state=interrupted?"Interrupted":"Lost";return a;
        });
        public void RecoverInterrupted(){
            var active=Read().attempts.FirstOrDefault(a=>a.state=="Reserved"||a.state=="Started");if(active==null)return;
            if(active.state=="Started"&&ContinueJournal.Restorable(active))return;
            if(active.state=="Reserved")CancelReservation(active.id);else Lose(active.id,true);
        }
        // Timed regeneration (LifeRules). The timer starts the first time a
        // profile below maxLives is observed, so a loss costs nothing extra and
        // older saves simply begin counting. A device clock that moved backwards
        // stalls the timer; a forward jump credits lives. Nothing is written
        // unless a life or the timer state changes.
        public int RegenerateLives(long now){
            if(now<=0)return 0;var p=Read();
            if(p.lives>=p.maxLives)return p.livesRefillDueUnix==0?0:Change(q=>{if(q.lives>=q.maxLives)q.livesRefillDueUnix=0;return 0;});
            if(p.livesRefillDueUnix<=0)return Change(q=>{if(q.lives<q.maxLives&&q.livesRefillDueUnix<=0)q.livesRefillDueUnix=now+LifeRules.RegenerationSeconds;return 0;});
            if(now<p.livesRefillDueUnix)return 0;
            return Change(q=>CreditLives(q,now));
        }
        static int CreditLives(PlayerProfile q,long now){
            if(q.lives>=q.maxLives){q.livesRefillDueUnix=0;return 0;}
            if(q.livesRefillDueUnix<=0){q.livesRefillDueUnix=now+LifeRules.RegenerationSeconds;return 0;}
            int credited=0;long due=q.livesRefillDueUnix;
            while(q.lives<q.maxLives&&now>=due){q.lives++;credited++;due+=LifeRules.RegenerationSeconds;}
            q.livesRefillDueUnix=q.lives>=q.maxLives?0:due;
            if(credited>0)q.lifeCredits.Add(new LifeCreditReceipt{key=Guid.NewGuid().ToString("N"),at=now,lives=credited});
            return credited;
        }
        // Seconds until the next life, or -1 when lives are full or no timer runs.
        public static long NextLifeIn(PlayerProfile p,long now)=>p.lives>=p.maxLives||p.livesRefillDueUnix<=0?-1:Math.Max(0,p.livesRefillDueUnix-now);
        // Full refill at zero lives for LifeRules.RefillCoins; idempotent by key so
        // a lost save confirmation can be retried without a second debit.
        public LifeRefillReceipt RefillLives(string key,long now){
            if(string.IsNullOrEmpty(key)||now<=0)throw new ArgumentException("Invalid refill request");
            return Change(p=>{
                var existing=p.lifeRefills.FirstOrDefault(r=>r.key==key);if(existing!=null)return existing;
                CreditLives(p,now);
                if(p.lives>0)throw new InvalidOperationException("Lives are not empty");
                if(p.coins<LifeRules.RefillCoins)throw new InvalidOperationException("Not enough coins");
                var receipt=new LifeRefillReceipt{key=key,at=now,coins=LifeRules.RefillCoins,livesBefore=p.lives,livesAfter=p.maxLives};
                p.coins-=receipt.coins;p.lives=p.maxLives;p.livesRefillDueUnix=0;p.lifeRefills.Add(receipt);return receipt;
            });
        }
        // Tool callers validate a disposable board first. A durable debit must
        // succeed before the player's board or presentation is changed.
        public void SpendTool(string attempt,string command,int tool){Change(p=>{
            var a=Find(p,attempt);if(tool<0||tool>3||string.IsNullOrEmpty(command)||command.Length>128||command.Contains(":"))throw new InvalidOperationException("Invalid tool command");
            string key=tool+":"+command;var prior=a.toolCommands.FirstOrDefault(v=>v.EndsWith(":"+command,StringComparison.Ordinal));if(prior!=null){if(prior!=key)throw new InvalidOperationException("Tool command contents changed");return false;}
            if(a.state!="Started"||p.tools[tool]<=0)throw new InvalidOperationException("No active attempt or tool available");p.tools[tool]--;a.toolCommands.Add(key);return true;
        });}
        public bool Grant(string key,string source,RewardGrant grant)=>Change(p=>ApplyGrant(p,key,source,grant));
        public static bool ApplyGrant(PlayerProfile p,string key,string source,RewardGrant grant){
            if(grant==null)throw new ArgumentNullException(nameof(grant));grant.Validate();var old=p.rewards.FirstOrDefault(r=>r.key==key);
            if(old!=null){if(old.source!=source||old.grant.coins!=grant.coins||old.grant.stars!=grant.stars||!old.grant.starting.SequenceEqual(grant.starting)||!old.grant.tools.SequenceEqual(grant.tools))throw new InvalidOperationException("Reward key reused with different contents");return false;}
            p.coins=checked(p.coins+grant.coins);p.stars=checked(p.stars+grant.stars);for(int i=0;i<4;i++){p.starting[i]=checked(p.starting[i]+grant.starting[i]);p.tools[i]=checked(p.tools[i]+grant.tools[i]);}
            p.rewards.Add(new RewardReceipt{key=key,source=source,grant=new RewardGrant{coins=grant.coins,stars=grant.stars,starting=(int[])grant.starting.Clone(),tools=(int[])grant.tools.Clone()}});return true;
        }
    }
}

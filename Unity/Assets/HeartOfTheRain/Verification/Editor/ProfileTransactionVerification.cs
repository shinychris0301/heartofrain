#if UNITY_EDITOR
using System;using System.IO;using System.Linq;using System.Collections.Generic;using UnityEngine;using UnityEditor;
using HeartOfTheRain.App.Profile;using HeartOfTheRain.App.Localization;using HeartOfTheRain.App.Home;using HeartOfTheRain.App.PreLevel;using HeartOfTheRain.M46;
namespace HeartOfTheRain.Verification {
    public static class ProfileTransactionVerification {
        // Same fault model as the connected probes: a commit can be saved and
        // then lose its confirmation, after which reads fail until recovery.
        sealed class FaultRepository:IProfileRepository {
            public IProfileRepository inner;public bool Unavailable,FailAfterCommit;
            public PlayerProfile Read(){if(Unavailable)throw new IOException("Injected unavailable save read");return inner.Read();}
            public PlayerProfile Commit(long revision,PlayerProfile next){var saved=inner.Commit(revision,next);if(FailAfterCommit){FailAfterCommit=false;Unavailable=true;throw new IOException("Injected lost save confirmation");}return saved;}
        }
        [Serializable] sealed class Report {public string status,utc,scope="Native Unity Editor execution of file repository, transaction/fault, gift-authority adapter, board tool rollback and layout checks. Development authority is local simulation; Android persistence/UI and release-server behavior are separate.";public int checks;public List<string> cases=new List<string>(),failures=new List<string>();}
        [Serializable] sealed class Envelope {public int format=1;public string payload,sha256;}
        static Report report;static string root;static int serial;
        static void Check(bool ok,string message){report.checks++;if(!ok)throw new Exception(message);}
        static void Throws<T>(Action action,string message) where T:Exception {try{action();}catch(T){Check(true,message);return;}throw new Exception("Expected "+typeof(T).Name+": "+message);}
        static void Case(string name,Action action){try{action();report.cases.Add(name);}catch(Exception e){report.failures.Add(name+": "+e);}}
        static string Id()=>Guid.NewGuid().ToString("N");
        static FileProfileRepository Files(string name,PlayerProfile initial=null){var p=initial??PlayerProfile.New(new[]{5,5,3,2});return new FileProfileRepository(Path.Combine(root,name),()=>p);}
        static ProfileService Memory()=>new ProfileService(new MemoryProfileRepository(PlayerProfile.New(new[]{5,5,3,2})));
        static string Reserve(ProfileService service,int level=1,int[] selected=null){string id=Id();service.Reserve(id,level,"level-config-v1",selected??new int[4],50,1);return id;}
        static ProfileService Started(out string id,int[] selected=null){var s=Memory();id=Reserve(s,1,selected);s.CommitStart(id);return s;}
        sealed class Fixture {
            public string name;public long day=100;public GiftSchedule schedule=GiftSchedule.Preview();public FileProfileRepository client,server;public ProfileService profile;public DevelopmentGiftAuthority authority;public DailyGiftService gifts;
            public Fixture(){name="gift-"+(++serial);Restart();}
            public void Restart(){client=Files(name+"-client");profile=new ProfileService(client);var initial=new PlayerProfile{playerId=profile.Read().playerId,coins=0,starting=new int[4],tools=new int[4]};server=Files(name+"-authority",initial);authority=new DevelopmentGiftAuthority(server,()=>day,schedule);gifts=new DailyGiftService(profile,authority,schedule);}
        }
        sealed class CorruptDecision:IDailyGiftAuthority {
            public IDailyGiftAuthority inner;public bool IsDevelopment=>true;public GiftOffer Offer(string p)=>inner.Offer(p);
            public GiftDecision Claim(string p,PendingGift request){var d=inner.Claim(p,request);d.grant.coins+=999;return d;}
        }
        sealed class CorruptOffer:IDailyGiftAuthority {
            public IDailyGiftAuthority inner;public bool IsDevelopment=>true;public GiftOffer Offer(string p){var offer=inner.Offer(p);offer.grant.coins+=999;return offer;}public GiftDecision Claim(string p,PendingGift r)=>inner.Claim(p,r);
        }
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o")};root=Path.GetFullPath("../.verification-cache/DailyGift/Native-"+Id());Directory.CreateDirectory(root);
            Case("Safe defaults, legacy split inventory, defensive snapshots",()=>{
                var p=PlayerProfile.New(new[]{5,3,2});Check(p.starting.SequenceEqual(new[]{5,5,3,2}),"Legacy Rocket/Bomb split");Check(p.completed==0&&p.currentLevel==1,"Never bootstrap from Home preview level18");var r=Files("defaults",p);var s=r.Read();Check(s.playerId==p.playerId,"Stable identity");s.coins=0;Check(r.Read().coins==1250,"Read has no mutable alias");var changed=r.Read();changed.coins=1300;r.Commit(changed.revision,changed);changed.coins=1;Check(r.Read().coins==1300,"Commit has no mutable alias");Check(Files("defaults").Read().playerId==p.playerId,"Reopen preserves identity");
            });
            Case("Compare-and-swap, identity and balance validation",()=>{
                var r=Files("cas");var a=r.Read();var b=Files("cas").Read();a.coins++;r.Commit(a.revision,a);Throws<ProfileConflictException>(()=>Files("cas").Commit(b.revision,b),"Stale repository rejected");b=r.Read();b.playerId=Id();Throws<InvalidOperationException>(()=>r.Commit(b.revision,b),"Identity cannot change");b=r.Read();b.tools[0]=-1;Throws<InvalidOperationException>(()=>r.Commit(b.revision,b),"Negative inventory rejected");Check(r.Read().tools[0]==3,"Invalid commit leaves file unchanged");
            });
            Case("Explicit nullable pending claim survives Unity serialization",()=>{
                var p=PlayerProfile.New(new[]{5,5,3,2});Check(ProfileJson.Copy(p).pendingGift==null,"Absent claim remains absent");p.pendingGift=new PendingGift{requestId=Id(),offerId="one",day=100,step=0,schedule="v1",expectedGrant=new RewardGrant{coins=50}};Check(ProfileJson.Copy(p).pendingGift.expectedGrant.coins==50,"Present claim survives roundtrip");p.pendingGift=null;Check(ProfileJson.Copy(p).pendingGift==null,"Cleared claim remains absent");var invalid=JsonUtility.FromJson<PlayerProfile>(JsonUtility.ToJson(p).Replace("\"hasPendingGift\":false","\"hasPendingGift\":true"));Throws<InvalidOperationException>(()=>invalid.Validate(),"Present but invalid claim is not silently discarded");
            });
            Case("Crash before replace leaves old commit and ignores temp",()=>{
                var r=Files("before");var service=new ProfileService(r);r.Read();r.Checkpoint=phase=>{if(phase=="TempFlushed")throw new IOException("Injected before replace");};Throws<IOException>(()=>service.Grant("one","test",new RewardGrant{coins=50}),"Precommit interruption");var saved=Files("before").Read();Check(saved.coins==1250&&saved.rewards.Count==0,"No partial credit or receipt");Check(Directory.GetFiles(Path.Combine(root,"before"),"*.tmp").Length==1,"Uncommitted temp is not promoted");
            });
            Case("Crash after commit and duplicate credit replay",()=>{
                var r=Files("after");var s=new ProfileService(r);r.Read();r.Checkpoint=phase=>{if(phase=="Committed")throw new IOException("Injected response loss");};Throws<IOException>(()=>s.Grant("one","test",new RewardGrant{coins=50}),"Postcommit response loss");s=new ProfileService(Files("after"));Check(!s.Grant("one","test",new RewardGrant{coins=50}),"Duplicate returns no new grant");Check(s.Read().coins==1300&&s.Read().rewards.Count==1,"Exactly one durable credit");Throws<InvalidOperationException>(()=>s.Grant("one","test",new RewardGrant{coins=99}),"Conflicting receipt payload rejected");
            });
            Case("Corrupt primary recovery preserves backup; corrupt/future saves fail closed",()=>{
                var r=Files("backup");var s=new ProfileService(r);s.Grant("a","test",new RewardGrant{coins=50});s.Grant("b","test",new RewardGrant{coins=25});File.WriteAllText(Path.Combine(root,"backup/profile.json"),"broken");r=Files("backup");Check(r.Read().coins==1300&&r.RecoveredBackup,"Recover last known good snapshot");Check(r.Read().coins==1300,"Recovery is stable on second read");Check(Directory.GetFiles(Path.Combine(root,"backup"),"profile.corrupt.*.json").Length==1,"Corrupt primary quarantined");
                File.WriteAllText(Path.Combine(root,"backup/profile.json"),"broken");File.WriteAllText(Path.Combine(root,"backup/profile.backup.json"),"also broken");Throws<Exception>(()=>Files("backup").Read(),"Both bad files fail closed");Check(File.ReadAllText(Path.Combine(root,"backup/profile.json"))=="broken","No silent reset");
                r=Files("future");var p=r.Read();s=new ProfileService(r);s.Grant("a","test",new RewardGrant{coins=5});p.schemaVersion=2;string payload=JsonUtility.ToJson(p);File.WriteAllText(Path.Combine(root,"future/profile.json"),JsonUtility.ToJson(new Envelope{payload=payload,sha256=ProfileJson.Hash(payload)}));Throws<NotSupportedException>(()=>Files("future").Read(),"Future version never downgraded to backup");
            });
            Case("Reservation and successful-start debit exactly once",()=>{
                var s=Memory();string id=Reserve(s,1,new[]{1,1,1,1});Check(s.Read().starting.SequenceEqual(new[]{5,5,3,2}),"Reservation is not debit");s.Reserve(id,1,"level-config-v1",new[]{1,1,1,1},50,1);s.CommitStart(id);s.CommitStart(id);Check(s.Read().starting.SequenceEqual(new[]{4,4,2,1}),"Repeated commit debits once");Throws<InvalidOperationException>(()=>s.CancelReservation(id),"Cannot cancel committed start");Throws<InvalidOperationException>(()=>Reserve(s),"Only one active attempt");
            });
            Case("Startup recovery, no-charge failed initialization and one-loss interruption",()=>{
                var s=Memory();string reserved=Reserve(s);s.RecoverInterrupted();s.RecoverInterrupted();Check(s.Read().lives==5&&s.Read().attempts[0].state=="Cancelled","Uninitialized reservation has no cost");string started=Reserve(s,1,new[]{1,0,0,0});s.CommitStart(started);s.RecoverInterrupted();s.RecoverInterrupted();Check(s.Read().lives==4&&s.Read().starting[0]==4,"One life lost and used item stays spent");Check(s.Read().attempts.Last().state=="Interrupted","Interrupted receipt persisted");
            });
            Case("Win before presentation, replay reward protection and normal loss",()=>{
                string id;var s=Started(out id);var won=s.Win(id);s.Win(id);s.RecoverInterrupted();Check(s.Read().coins==1300&&s.Read().stars==1&&s.Read().completed==1&&s.Read().currentLevel==2&&s.Read().lives==5,"Durable win independent of animation");string replay=Reserve(s);s.CommitStart(replay);Check(!s.Win(replay).firstClear&&s.Read().coins==1300,"Replay does not earn another first clear");string lost=Reserve(s,2);s.CommitStart(lost);s.Lose(lost);s.Lose(lost);s.RecoverInterrupted();Check(s.Read().lives==4,"Loss charged once");Throws<InvalidOperationException>(()=>s.Win(lost),"Settled loss cannot become a win");
            });
            Case("Persistent tool command and overflow are atomic",()=>{
                string id;var s=Started(out id);s.SpendTool(id,"tap",0);s.SpendTool(id,"tap",0);Check(s.Read().tools[0]==2,"Duplicate tool command debits once");Throws<InvalidOperationException>(()=>s.SpendTool(id,"tap",1),"Tool command cannot change its payload");s.Lose(id);s.SpendTool(id,"tap",0);Check(s.Read().tools[0]==2,"Old command after settlement remains idempotent");s.Change(p=>{p.coins=int.MaxValue;return true;});Throws<OverflowException>(()=>s.Grant("overflow","test",new RewardGrant{coins=1,tools=new[]{1,0,0,0}}),"Overflow does not partly grant");Check(s.Read().tools[0]==2&&s.Read().rewards.Count==0,"Failed credit preserves all stock");
            });
            Case("Unconfirmed tool debit reconciles its exact target and never leaks into the next attempt",()=>{
                var faults=new FaultRepository{inner=new MemoryProfileRepository(PlayerProfile.New(new[]{5,5,3,2}))};var s=new ProfileService(faults);
                string first=Reserve(s);s.CommitStart(first);var tools=new ToolSpendReconciliation();tools.BeginAttempt(first);bool unconfirmed;
                Check(tools.TryCommit(s,BoosterKind.Hammer,2,2,out unconfirmed)&&!unconfirmed&&s.Read().tools[0]==2,"Healthy debit spends once");
                faults.FailAfterCommit=true;Check(!tools.TryCommit(s,BoosterKind.Axe,3,3,out unconfirmed)&&unconfirmed&&tools.HasPending,"Save and confirming read both fail: exact command stays pending");
                faults.Unavailable=false;Check(s.Read().tools[1]==2,"The unconfirmed debit was in fact saved");
                Check(!tools.TryCommit(s,BoosterKind.Hammer,2,2,out unconfirmed)&&!unconfirmed&&s.Read().tools[0]==2,"Other targets are refused while a command is pending, with no second debit");
                Check(tools.TryCommit(s,BoosterKind.Axe,3,3,out unconfirmed)&&!tools.HasPending&&s.Read().tools[1]==2,"Retrying the exact target finds the saved command and debits nothing more");
                faults.FailAfterCommit=true;Check(!tools.TryCommit(s,BoosterKind.Ram,1,1,out unconfirmed)&&unconfirmed&&tools.HasPending,"A second double fault is left pending at the end of the attempt");faults.Unavailable=false;
                s.Lose(first);string second=Reserve(s);s.CommitStart(second);tools.BeginAttempt(second);
                Check(!tools.HasPending&&tools.AttemptId==second,"The next attempt starts without the stale command");
                Check(tools.TryCommit(s,BoosterKind.Hammer,4,4,out unconfirmed)&&s.Read().tools[0]==1,"Tool use at another cell works in the next attempt");
                Check(tools.TryCommit(s,BoosterKind.Ram,1,1,out unconfirmed)&&s.Read().tools[2]==1,"The old pending target spends normally in the new attempt under a fresh command");
                var saved=s.Read();Check(saved.attempts.First(a=>a.id==first).toolCommands.Count==3&&saved.attempts.First(a=>a.id==second).toolCommands.Count==2,"Every command is attributed to its own attempt");
                var fresh=new ToolSpendReconciliation();Check(!fresh.TryCommit(s,BoosterKind.Hammer,0,0,out unconfirmed)&&!unconfirmed&&s.Read().tools[0]==1,"No attempt, no debit");
            });
            Case("Engine-fault release refunds starting items, spares the life and audits as Released",()=>{
                var s=Memory();var feed=new ProfileEventFeed(s);string id=Reserve(s,1,new[]{1,0,1,0});s.CommitStart(id);s.SpendTool(id,"hit",0);
                Check(s.Read().starting.SequenceEqual(new[]{4,5,2,2})&&s.Read().tools[0]==2,"Start debited two items and one tool");
                Check(s.ReleaseFault(id),"Release accepted");var p=s.Read();var a=p.attempts.Single(r=>r.id==id);
                Check(a.state=="Released"&&p.lives==5&&p.starting.SequenceEqual(new[]{5,5,3,2})&&p.tools[0]==2,"Items refunded, life kept, used tool stays spent");
                Check(!s.ReleaseFault(id)&&s.Read().starting.SequenceEqual(new[]{5,5,3,2}),"Repeated release refunds nothing more");
                Throws<InvalidOperationException>(()=>s.Win(id),"A released attempt cannot be won");Throws<InvalidOperationException>(()=>s.Lose(id),"A released attempt cannot be lost");
                p.Validate();var snapshot=feed.Capture();
                Check(snapshot.events.Count(e=>e.kind=="attempt_started")==1&&snapshot.events.Count(e=>e.kind=="tool_spent")==1&&snapshot.events.Count(e=>e.kind=="attempt_released")==1,"Debit, tool and release each audited once");
                var release=snapshot.events.Single(e=>e.kind=="attempt_released");Check(release.delta[4]==1&&release.delta[6]==1&&release.delta[5]==0&&release.delta[2]==0,"Release refunds exactly the selected items and no life");
                Check(snapshot.opening.Skip(4).Take(4).SequenceEqual(new long[]{5,5,3,2})&&snapshot.opening[2]==5&&snapshot.opening[8]==3,"Opening balances reconcile through the release");
                string next=Reserve(s,1,new[]{0,1,0,0});s.CommitStart(next);Check(s.Read().starting.SequenceEqual(new[]{5,4,3,2}),"A new attempt starts normally after a release");
                Throws<InvalidOperationException>(()=>s.ReleaseFault(next+"x"),"Unknown attempt cannot be released");
                string reserved=null;s.Lose(next);reserved=Reserve(s);Throws<InvalidOperationException>(()=>s.ReleaseFault(reserved),"A reservation that never started is cancelled, not released");
            });
            Case("Attempt seeds are per attempt, stable, non-zero and recorded in the receipt",()=>{
                string a=Id(),b=Id();uint seedA=ProfileService.AttemptSeed(a);
                Check(seedA!=0&&seedA==ProfileService.AttemptSeed(a),"Seed is non-zero and deterministic for an id");
                Check(ProfileService.AttemptSeed(b)!=seedA,"Different attempts get different seeds");
                Throws<ArgumentException>(()=>ProfileService.AttemptSeed(""),"Empty attempt id rejected");
                var s=Memory();s.Reserve(a,1,"level-config-v1",new int[4],50,1);var record=s.Read().attempts.Single(r=>r.id==a);
                Check(record.seed==seedA,"Reservation records the attempt seed");s.Reserve(a,1,"level-config-v1",new int[4],50,1);Check(s.Read().attempts.Count==1&&s.Read().attempts[0].seed==seedA,"Repeated reservation keeps the same seed");
                s.CommitStart(a);s.Lose(a);s.Reserve(b,1,"level-config-v1",new int[4],50,1);Check(s.Read().attempts.Single(r=>r.id==b).seed==ProfileService.AttemptSeed(b),"The retry attempt carries its own seed");s.Read().Validate();
                var board=new BoardModel(JsonUtility.FromJson<LevelData>(AssetDatabase.LoadAssetAtPath<HeartOfTheRain.M47.GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset").boards.levels[0].text),seedA);
                Check(JsonUtility.ToJson(board.Snapshot())==JsonUtility.ToJson(new BoardModel(board.Level).Snapshot()),"The authored opening board does not depend on the attempt seed");
            });
            Case("Timed life regeneration and paid refill are durable, bounded and audited",()=>{
                var s=Memory();var feed=new ProfileEventFeed(s);long t=1_700_000_000;int interval=LifeRules.RegenerationSeconds;
                Action lose=()=>{string a=Reserve(s);s.CommitStart(a);s.Lose(a);};
                Check(s.RegenerateLives(t)==0&&s.Read().livesRefillDueUnix==0,"Full lives run no timer");
                lose();lose();Check(s.Read().lives==3&&s.Read().livesRefillDueUnix==0,"Losses do not start the timer by themselves");
                Check(s.RegenerateLives(t)==0&&s.Read().livesRefillDueUnix==t+interval,"First observation below max starts the timer");
                Check(s.RegenerateLives(t+interval-1)==0&&s.Read().lives==3,"No credit before the interval");
                Check(s.RegenerateLives(t+interval)==1&&s.Read().lives==4&&s.Read().livesRefillDueUnix==t+2*interval,"One life after one interval, timer rolls forward");
                Check(s.RegenerateLives(t+interval)==0,"Repeated observation credits nothing");
                Check(s.RegenerateLives(t+10*interval)==1&&s.Read().lives==5&&s.Read().livesRefillDueUnix==0,"A long gap credits only up to max and clears the timer");
                Check(s.Read().lifeCredits.Count==2&&s.Read().lifeCredits.Sum(c=>c.lives)==2,"Each credit occurrence is one receipt");
                lose();s.RegenerateLives(t+10*interval);long due=s.Read().livesRefillDueUnix;
                Check(s.RegenerateLives(t+9*interval)==0&&s.Read().livesRefillDueUnix==due,"A clock that moved backwards stalls the timer without rewriting it");
                Check(s.RegenerateLives(due)==1&&s.Read().lives==5,"The stalled timer resumes when the clock catches up");
                s.Read().Validate();var snapshot=feed.Capture();Check(snapshot.events.Count(e=>e.kind=="lives_regenerated")==3&&snapshot.opening[2]<=5,"Regeneration receipts reconcile the audit opening balance");
                Throws<InvalidOperationException>(()=>s.RefillLives(Id(),t+20*interval),"Refill refused while lives remain");
                for(int i=0;i<5;i++)lose();Check(s.Read().lives==0,"Five losses empty the lives");
                Throws<InvalidOperationException>(()=>Reserve(s),"No attempt without lives");
                string key=Id();var receipt=s.RefillLives(key,t+20*interval);var p=s.Read();
                Check(p.lives==5&&p.coins==1250-LifeRules.RefillCoins&&p.livesRefillDueUnix==0&&receipt.livesBefore==0&&receipt.livesAfter==5,"Refill fills to max, debits the price and stops the timer");
                Check(s.RefillLives(key,t+21*interval).key==key&&s.Read().coins==1250-LifeRules.RefillCoins&&s.Read().lifeRefills.Count==1,"Repeating the key returns the same receipt without a second debit");
                s.Change(q=>{q.lives=0;q.coins=LifeRules.RefillCoins-1;return true;});Throws<InvalidOperationException>(()=>s.RefillLives(Id(),t+22*interval),"Refill refused without enough coins");
                Check(s.Read().lives==0&&s.Read().coins==LifeRules.RefillCoins-1,"Refused refill changes nothing");
                s.Read().Validate();snapshot=feed.Capture();Check(snapshot.events.Count(e=>e.kind=="lives_refilled")==1&&snapshot.events.Single(e=>e.kind=="lives_refilled").delta[0]==-LifeRules.RefillCoins,"Refill receipt audits the coin debit and life credit");Check(snapshot.opening[2]<=5&&snapshot.opening[0]>=0,"Lives and coins reconcile after refill");
                Check(ProfileService.NextLifeIn(s.Read(),t)==-1,"No timer reported at zero lives before observation");s.RegenerateLives(t+30*interval);Check(ProfileService.NextLifeIn(s.Read(),t+30*interval+100)==interval-100,"Seconds to next life reported from the running timer");
            });
            Case("Full-life refill costs 900 at the wallet boundary and preserves old receipts",()=>{
                Check(LifeRules.RefillCoins==900,"Owner-approved full-life refill price is 900 coins");
                foreach(int balance in new[]{0,500,899,900,1250}){
                    var initial=PlayerProfile.New(new[]{5,5,3,2});initial.coins=balance;initial.lives=0;initial.livesRefillDueUnix=2800;
                    var service=new ProfileService(new MemoryProfileRepository(initial));string key=Id();
                    if(balance<900){string before=JsonUtility.ToJson(service.Read());Throws<InvalidOperationException>(()=>service.RefillLives(key,1000),"Below 900 cannot buy a full refill: "+balance);Check(JsonUtility.ToJson(service.Read())==before,"Insufficient refill leaves balances, timer, revision and receipts unchanged: "+balance);}
                    else{var receipt=service.RefillLives(key,1000);Check(service.Read().coins==balance-900&&service.Read().lives==5&&service.Read().livesRefillDueUnix==0&&receipt.coins==900,"900-coin refill grants all five lives: "+balance);service.RefillLives(key,1001);Check(service.Read().coins==balance-900&&service.Read().lifeRefills.Count==1,"900-coin receipt retry never charges twice: "+balance);}
                }
                string legacyKey=Id();var legacy=PlayerProfile.New(new[]{5,5,3,2});legacy.coins=750;legacy.lifeRefills.Add(new LifeRefillReceipt{key=legacyKey,at=1000,coins=500,livesBefore=0,livesAfter=5});
                var repository=Files("refill-price-upgrade",legacy);repository.Read();var reopened=new ProfileService(Files("refill-price-upgrade"));
                Check(reopened.RefillLives(legacyKey,1001).coins==500&&reopened.Read().coins==750&&reopened.Read().lifeRefills.Count==1,"Reopening/retrying an old 500-coin receipt retains its original amount without repricing");
                reopened.Change(q=>{q.coins=900;q.lives=0;q.livesRefillDueUnix=2800;return true;});reopened.RefillLives(Id(),1100);
                var saved=Files("refill-price-upgrade").Read();Check(saved.coins==0&&saved.lives==5&&saved.lifeRefills.Select(r=>r.coins).SequenceEqual(new[]{500,900}),"Next refill uses 900 while the old durable receipt remains unchanged");saved.Validate();
            });
            Case("All four board tools reject failed debit without board/RNG changes",()=>{
                var asset=AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/HeartOfTheRain/M46/Data/Levels/CH01_L001.json");
                if(!asset){var ui=AssetDatabase.LoadAssetAtPath<HeartOfTheRain.M47.GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");asset=ui.boards.levels[0];}
                var level=JsonUtility.FromJson<LevelData>(asset.text);
                for(int n=0;n<4;n++){var board=new BoardModel(level);var stock=new BoosterInventory();var piece=board.Pieces.Values.First(p=>p.family=="gem");int x=piece.x,y=piece.y;string before=JsonUtility.ToJson(board.Snapshot());int calls=0;var result=board.UseBooster((BoosterKind)n,x,y,stock,()=>{calls++;return false;});Check(!result.accepted&&calls==1&&stock.Count((BoosterKind)n)==3,"Tool rejected before inventory spend "+n);Check(JsonUtility.ToJson(board.Snapshot())==before,"No board mutation after rejected debit "+n);result=board.UseBooster((BoosterKind)n,x,y,stock,()=>throw new IOException("Injected callback failure"));Check(!result.accepted&&JsonUtility.ToJson(board.Snapshot())==before,"Thrown debit preserves board "+n);var control=new BoardModel(level);var a=board.UseBooster((BoosterKind)n,x,y,stock);var b=control.UseBooster((BoosterKind)n,x,y,new BoosterInventory());Check(JsonUtility.ToJson(a)==JsonUtility.ToJson(b),"Next accepted turn preserves RNG/steps "+n);}
            });
            Case("Seven-day schedule, missed days, same-day retry and next cycle",()=>{
                var f=new Fixture();for(int i=0;i<7;i++){f.day+=i==2?4:1;Check(f.gifts.Offer().step==i,"Correct next reward despite missed days "+i);f.gifts.Claim();Check(f.gifts.Claim()==null,"No second claim same day "+i);f.Restart();Check(f.profile.Read().giftClaims==i+1,"Claim survives process reconstruction "+i);}
                var p=f.profile.Read();Check(p.coins==1625&&p.starting.SequenceEqual(new[]{6,6,4,2})&&p.tools.SequenceEqual(new[]{4,3,3,3}),"Approved provisional quantities");f.day++;Check(f.gifts.Offer().step==0,"Seven-day cycle wraps");f.gifts.Claim();Check(f.profile.Read().coins==1675,"Next cycle starts once");
            });
            Case("Remote-confirmation loss and persisted pending recovery",()=>{
                var f=new Fixture();f.authority.Checkpoint=_=>throw new IOException("Injected after authority confirmation");Throws<IOException>(()=>f.gifts.Claim(),"Lost authority response");Check(f.profile.Read().coins==1250&&f.profile.Read().pendingGift!=null,"No early local credit");Check(f.server.Read().giftClaims==1,"Authority confirmed only once");f.Restart();f.gifts.Claim();Check(f.profile.Read().coins==1300&&f.profile.Read().pendingGift==null,"Recovered original confirmation");Check(f.server.Read().giftClaims==1,"Recovery did not ask for another entitlement");
            });
            Case("Local claim crash before/after credit commit",()=>{
                for(int stage=1;stage<=2;stage++){var f=new Fixture();int committed=0;f.client.Checkpoint=phase=>{if(phase=="Committed"&&++committed==stage)throw new IOException("Injected client response loss");};Throws<IOException>(()=>f.gifts.Claim(),"Client interrupted stage "+stage);f.Restart();f.gifts.Claim();Check(f.profile.Read().coins==1300&&f.profile.Read().giftClaims==1&&f.profile.Read().rewards.Count==1,"Exactly one recovered local reward stage "+stage);}
            });
            Case("Offline, rollback, tampered reply and unavailable production adapter",()=>{
                var f=new Fixture();f.authority.Offline=true;Throws<InvalidOperationException>(()=>f.gifts.Claim(),"Offline before intent");Check(f.profile.Read().pendingGift==null&&f.profile.Read().coins==1250,"Offline makes no claim");f.authority.Offline=false;
                var bad=new DailyGiftService(f.profile,new CorruptDecision{inner=f.authority},f.schedule);Throws<InvalidOperationException>(()=>bad.Claim(),"Changed quantities rejected");Check(f.profile.Read().coins==1250&&f.profile.Read().pendingGift!=null,"Bad reply retains recoverable request");f.gifts.Claim();f.day--;Check(f.gifts.Offer()==null,"Clock rollback cannot create a claim");var unavailable=new DailyGiftService(f.profile,new UnavailableGiftAuthority(),f.schedule);Check(unavailable.Offer()==null&&!unavailable.IsDevelopment,"Unavailable adapter never uses local clock");Throws<InvalidOperationException>(()=>unavailable.Claim(),"Production adapter cannot grant preview currency");
            });
            Case("A confirmed pending grant survives schedule revision",()=>{
                var f=new Fixture();f.authority.Checkpoint=_=>throw new IOException("Interrupted");Throws<IOException>(()=>f.gifts.Claim(),"Pending v1");f.schedule=GiftSchedule.Preview();f.schedule.version="daily-preview-v2";f.schedule.days[0].coins=77;f.Restart();f.gifts.Claim();Check(f.profile.Read().coins==1300,"Confirmed v1 grant not replaced with v2 quantities");f.day++;Check(f.gifts.Offer().schedule=="daily-preview-v2"&&f.gifts.Offer().step==1,"New offers use new config without resetting cycle");
            });
            Case("Changed offers and unconfirmed expired requests cannot grant",()=>{
                var f=new Fixture();var bad=new DailyGiftService(f.profile,new CorruptOffer{inner=f.authority},f.schedule);Throws<InvalidOperationException>(()=>bad.Claim(),"Changed offer quantities rejected before intent");Check(f.profile.Read().pendingGift==null&&f.server.Read().giftClaims==0,"Changed offer creates no claim");var offer=f.gifts.Offer();f.profile.Change(p=>p.pendingGift=new PendingGift{requestId=Id(),offerId=offer.id,schedule=offer.schedule,day=offer.day,step=offer.step,expectedGrant=offer.grant.Copy()});f.day++;Throws<GiftExpiredException>(()=>f.gifts.Claim(),"Unconfirmed old day expired");Check(f.profile.Read().pendingGift==null&&f.profile.Read().coins==1250,"Expired intent clears without credit");f.gifts.Claim();Check(f.profile.Read().coins==1300&&f.profile.Read().giftClaims==1,"Next valid day retains first reward");
            });
            Case("Native schedule resource and all five responsive layouts",()=>{
                var resource=Resources.Load<TextAsset>("HOTR_DailyGift/Schedule");Check(resource!=null,"Runtime schedule packaged as resource");var schedule=JsonUtility.FromJson<GiftSchedule>(resource.text);schedule.Validate();Check(JsonUtility.ToJson(schedule)==JsonUtility.ToJson(GiftSchedule.Preview()),"Resource matches approved provisional schedule");
                int locale=GameLocale.Current;try{for(int l=0;l<5;l++){GameLocale.Select(l);foreach(int width in new[]{320,393,768})foreach(int step in Enumerable.Range(0,7)){var frame=DailyGiftLayout.Build(width,640,new DailyGiftView{schedule=schedule,offer=new GiftOffer{step=step,day=100},development=true});var panel=frame.elements.First(e=>e.id=="panel");Check(frame.elements.Where(e=>e.parent=="panel").All(e=>e.x>=0&&e.y>=0&&e.x+e.width<=panel.width+.01f&&e.y+e.height<=panel.height+.01f),"Layout bounds "+l+"/"+width+"/"+step);Check(frame.elements.Count(e=>e.id.StartsWith("day-label-"))==7,"Seven visible steps "+l+"/"+width+"/"+step);}}}finally{GameLocale.Select(locale);}
            });
            Case("Native font fitting and glyphs in every gift state",()=>{
                var assets=AssetDatabase.LoadAssetAtPath<HeartOfTheRain.App.PreLevel.PreLevelAssets>("Assets/HeartOfTheRain/App/PreLevel/PreLevelAssets.asset");var go=new GameObject("Gift font verification",typeof(RectTransform),typeof(UnityEngine.UI.Text));var text=go.GetComponent<UnityEngine.UI.Text>();text.font=assets.home.boldFont;text.horizontalOverflow=HorizontalWrapMode.Overflow;text.verticalOverflow=VerticalWrapMode.Truncate;text.supportRichText=false;int locale=GameLocale.Current;
                try{for(int l=0;l<5;l++){GameLocale.Select(l);foreach(int width in new[]{320,393,768})for(int state=0;state<17;state++){
                    var view=new DailyGiftView{schedule=GiftSchedule.Preview(),development=true};if(state<14)view.offer=new GiftOffer{step=state%7,claimed=state>=7};else if(state==15)view.pending=true;else if(state==16)view.error=true;
                    var f=DailyGiftLayout.Build(width,640,view);foreach(var e in f.elements.Where(e=>e.kind=="text")){text.text=e.text;text.fontSize=e.fontSize;((RectTransform)text.transform).sizeDelta=new Vector2(e.width,e.height);var design=DailyGiftDesignAssets.Load();bool heading=e.id=="title"||e.id.Contains("label")||e.id.Contains("quantity")||e.id.Contains("heading");text.font=heading?design.titleFont:design.bodyFont;text.horizontalOverflow=HorizontalWrapMode.Wrap;text.lineSpacing=1;if(e.id=="title"){if(GameLocale.Current==4)text.fontSize=e.width<=250?22:24;text.lineSpacing=.9f;}while(text.preferredHeight>e.height+.1f&&text.fontSize>10)text.fontSize--;bool paragraph=true;text.font.RequestCharactersInTexture(text.text,text.fontSize);Check((paragraph||text.preferredWidth<=e.width+.5f)&&text.preferredHeight<=e.height+.5f,"Native text bounds "+l+"/"+width+"/"+state+"/"+e.id);Check(e.text.All(c=>char.IsWhiteSpace(c)||text.font.HasCharacter(c)),"Native glyphs "+l+"/"+width+"/"+state+"/"+e.id);}
                }}}finally{GameLocale.Select(locale);UnityEngine.Object.DestroyImmediate(go);}
            });
            report.status=report.failures.Count==0?"PASS_NATIVE_PROFILE_TRANSACTIONS":"FAIL_NATIVE_PROFILE_TRANSACTIONS";string output=Path.GetFullPath(System.Environment.GetEnvironmentVariable("HOTR_REVIEW93_OUT")??"../Verification/Evidence/DailyGift");Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"Native_Profile_Checks.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.failures.Count==0?0:1);
        }
    }
}
#endif

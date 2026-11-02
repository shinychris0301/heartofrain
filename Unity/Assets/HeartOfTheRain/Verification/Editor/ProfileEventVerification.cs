#if UNITY_EDITOR
using System;using System.IO;using System.Linq;using System.Collections.Generic;using UnityEngine;using UnityEditor;
using HeartOfTheRain.App.Profile;
namespace HeartOfTheRain.Verification {
    public static class ProfileEventVerification {
        [Serializable] sealed class Report {public string utc,status,unity,scope="Native Unity receipt-projected audit feed and explicit local archive. No network, analytics provider, Android or rendering certification.";public int checks;public List<string> cases=new List<string>(),failures=new List<string>();}
        static Report report;static string root;
        static string Id()=>Guid.NewGuid().ToString("N");
        static void Check(bool ok,string name){report.checks++;if(!ok)throw new Exception(name);}
        static void Throws<T>(Action action,string name) where T:Exception {try{action();}catch(T){Check(true,name);return;}throw new Exception("Expected "+typeof(T).Name+": "+name);}
        static void Case(string name,Action action){try{action();report.cases.Add(name);}catch(Exception e){report.failures.Add(name+": "+e);}}
        static ProfileService Memory(PlayerProfile p=null)=>new ProfileService(new MemoryProfileRepository(p??PlayerProfile.New(new[]{5,5,3,2})));
        static string Reserve(ProfileService s,int level=1,int[] selected=null){string id=Id();s.Reserve(id,level,"fixture-config",selected??new int[4],50,1);return id;}
        static string Start(ProfileService s,int level=1,int[] selected=null){string id=Reserve(s,level,selected);s.CommitStart(id);return id;}
        static Dictionary<string,string> Payloads(ProfileEventFeed feed)=>feed.Capture().events.ToDictionary(e=>e.id,e=>JsonUtility.ToJson(e));
        static void Reconciles(ProfileEventSnapshot snapshot){
            var balance=(long[])snapshot.opening.Clone();foreach(var e in snapshot.events){e.Validate();for(int i=0;i<12;i++)balance[i]=checked(balance[i]+e.delta[i]);}
            Check(balance.SequenceEqual(snapshot.current),"Opening plus recorded deltas equals all twelve saved balances");
            Check(snapshot.events.Select(e=>e.id).Distinct().Count()==snapshot.events.Count,"Unique stable event IDs");
        }
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};root=Path.GetFullPath("../.verification-cache/ProfileEvents/N-"+Id().Substring(0,8));Directory.CreateDirectory(root);
            Case("Existing saves: read-only projection, no schema rewrite or fabricated history",()=>{
                var p=PlayerProfile.New(new[]{5,5,3,2});p.completed=10;p.currentLevel=11;p.stars=10;
                var r=new FileProfileRepository(Path.Combine(root,"legacy"),()=>p);var s=new ProfileService(r);s.Read();string path=Path.Combine(root,"legacy/profile.json"),before=File.ReadAllText(path);var snapshot=new ProfileEventFeed(s).Capture();
                Check(snapshot.events.Count==0&&snapshot.opening[3]==10,"Existing progress is an explicit opening balance");Reconciles(snapshot);Check(File.ReadAllText(path)==before,"Capture never rewrites old save");
                Check(snapshot.sourceRevision==0&&!JsonUtility.ToJson(snapshot).Contains(p.playerId),"Snapshot has no raw player identity");
            });
            Case("Lifecycle events remain immutable through start, tools and outcome",()=>{
                var s=Memory();var feed=new ProfileEventFeed(s);string id=Reserve(s,1,new[]{1,1,1,1});var first=Payloads(feed);Check(first.Count==1,"Reservation is not a debit");
                s.CommitStart(id);s.CommitStart(id);s.SpendTool(id,"tool-a",0);s.SpendTool(id,"tool-a",0);s.Win(id);s.Win(id);s.RecoverInterrupted();var snapshot=feed.Capture();
                Check(snapshot.events.Count==6,"Reserve/start/tool/win/progression/reward once");foreach(var kv in first)Check(Payloads(feed)[kv.Key]==kv.Value,"Reserved payload is stable after settlement");
                Check(snapshot.events.Single(e=>e.kind=="attempt_started").delta.Skip(4).Take(4).All(n=>n==-1),"All four starting items debited in the model event");
                Check(snapshot.events.Single(e=>e.kind=="tool_spent").delta[8]==-1,"Tool command debited once");Reconciles(snapshot);
                string json=string.Join("\n",snapshot.events.Select(e=>JsonUtility.ToJson(e)));Check(!json.Contains(id)&&!json.Contains("fixture-config")&&!json.Contains("tool-a")&&!json.Contains(s.Read().playerId),"Raw command, config and profile IDs are absent");
                var before=Payloads(feed);string replay=Start(s);s.Win(replay);Check(feed.Capture().events.Count==before.Count+3,"Replay emits lifecycle without progression or reward");foreach(var kv in before)Check(Payloads(feed)[kv.Key]==kv.Value,"Old payload survives new attempt");
            });
            Case("Initialization cancellation, ordinary loss and interrupted loss",()=>{
                var s=Memory();var feed=new ProfileEventFeed(s);Reserve(s);s.RecoverInterrupted();s.RecoverInterrupted();Check(feed.Capture().events.Count==2&&feed.Capture().current[2]==5,"Uninitialized reservation cancels without debit");
                string lost=Start(s);s.Lose(lost);s.Lose(lost);Start(s);s.RecoverInterrupted();s.RecoverInterrupted();var snapshot=feed.Capture();
                Check(snapshot.events.Count(e=>e.kind=="attempt_lost")==1&&snapshot.events.Count(e=>e.kind=="attempt_interrupted")==1,"Exactly one event per settled loss");Check(snapshot.current[2]==3,"Exactly two lives charged");Reconciles(snapshot);
            });
            Case("All fifty first clears, daily gifts, Wellworks and Cup share one reconciled ledger",()=>{
                var s=Memory();var feed=new ProfileEventFeed(s);long day=100,now=1000;var authority=new DevelopmentGiftAuthority(new MemoryProfileRepository(new PlayerProfile{playerId=s.Read().playerId,coins=0,starting=new int[4],tools=new int[4]}),()=>day,GiftSchedule.Preview());var gifts=new DailyGiftService(s,authority,GiftSchedule.Preview());
                for(int i=0;i<8;i++){gifts.Claim();gifts.Claim();day++;}var schedule=JsonUtility.FromJson<WellworksSchedule>(Resources.Load<TextAsset>("HOTR_Wellworks/Schedule").text);var works=new WellworksService(s,schedule,true);var rules=JsonUtility.FromJson<RainCupRules>(Resources.Load<TextAsset>("HOTR_RainCup/Rules").text);var cup=new DevelopmentRainCupService(s,rules,()=>now);string cupId=null;
                for(int level=1;level<=50;level++){
                    if(level==11)cupId=cup.Join(Id());string id=Start(s,level);s.Win(id,cup.CaptureWinTime());s.Win(id,cup.CaptureWinTime());
                    if(level%10==0){works.Claim(level);works.Claim(level);}Reconciles(feed.Capture());
                }
                now+=rules.durationSeconds;cup.Claim(cupId);cup.Claim(cupId);var snapshot=feed.Capture();Reconciles(snapshot);
                Check(snapshot.events.Count(e=>e.kind=="level_completed")==50,"Fifty progression events");Check(snapshot.events.Count(e=>e.kind=="cup_point")==40,"Forty eligible first-clear cup points");
                Check(snapshot.events.Count(e=>e.kind=="reward_granted"&&e.category=="daily_gift")==8,"Eight daily receipts, not sixteen callbacks");Check(snapshot.events.Count(e=>e.kind=="reward_granted"&&e.category=="wellworks")==5,"Five milestones");Check(snapshot.events.Count(e=>e.kind=="reward_granted"&&e.category=="rain_cup")==1,"One prize credit");
                Check(snapshot.events.Count(e=>e.kind=="cup_joined")==1&&snapshot.events.Count(e=>e.kind=="cup_finished")==1&&snapshot.events.Count(e=>e.kind=="cup_claimed")==1,"One lifecycle per cup");Check(snapshot.events.Single(e=>e.kind=="cup_finished").rank==1,"Persisted final rank");
                var archive=new LocalProfileEventArchive(Path.Combine(root,"campaign-archive"));var chunks=new List<LocalProfileEventArchive.Result>();do{chunks.Add(archive.Flush(feed,37));}while(chunks.Last().remaining>0);
                Check(chunks.Sum(c=>c.written)==snapshot.events.Count,"Bounded chunks deliver every receipt exactly once");Check(new LocalProfileEventArchive(Path.Combine(root,"campaign-archive")).Flush(feed).written==0,"Recreated archive deduplicates the entire campaign");
                foreach(var e in snapshot.events)Check(e.id==ProfileJson.Hash("hotr-event-v1|"+e.stream+"|"+e.kind+"|"+e.receipt),"Schema-valid deterministic identity");
            });
            Case("Profile commit failures never invent or lose a projected reward",()=>{
                foreach(string phase in new[]{"TempFlushed","Committed"}){
                    string folder=Path.Combine(root,"source-fault-"+phase);var r=new FileProfileRepository(folder,()=>PlayerProfile.New(new[]{5,5,3,2}));var s=new ProfileService(r);s.Read();r.Checkpoint=p=>{if(p==phase)throw new IOException("Injected profile interruption");};Throws<IOException>(()=>s.Grant("one","test",new RewardGrant{coins=50}),"Source interruption "+phase);
                    s=new ProfileService(new FileProfileRepository(folder,()=>throw new Exception("Must not recreate")));var feed=new ProfileEventFeed(s);Check(feed.Capture().events.Count==(phase=="Committed"?1:0),"Only durable receipt is projected "+phase);s.Grant("one","test",new RewardGrant{coins=50});s.Grant("one","test",new RewardGrant{coins=50});Check(feed.Capture().events.Count==1,"Retry produces exactly one event "+phase);Reconciles(feed.Capture());
                }
            });
            Case("Archive interruption, process recreation and immutable payload conflict",()=>{
                var s=Memory();s.Grant("one","test",new RewardGrant{coins=50});var feed=new ProfileEventFeed(s);
                foreach(string phase in new[]{"EventFlushed","EventCommitted"}){
                    string folder=Path.Combine(root,"delivery-fault-"+phase);var archive=new LocalProfileEventArchive(folder);archive.Checkpoint=p=>{if(p==phase)throw new IOException("Injected delivery interruption");};Throws<IOException>(()=>archive.Flush(feed),"Delivery interruption "+phase);
                    var retry=new LocalProfileEventArchive(folder).Flush(feed);Check(retry.written==(phase=="EventCommitted"?0:1),"Replay honors committed event "+phase);Check(new LocalProfileEventArchive(folder).Flush(feed).written==0,"Repeated delivery deduplicates "+phase);Check(!Directory.GetFiles(folder,"*.tmp",SearchOption.AllDirectories).Any(),"Temp does not become receipt");
                }
                var stable=new LocalProfileEventArchive(Path.Combine(root,"stable"));stable.Flush(feed);s.Change(p=>{p.rewards[0].grant.coins++;p.coins++;return true;});Throws<InvalidDataException>(()=>stable.Flush(feed),"Same ID cannot silently change payload");
            });
            Case("Corruption, rollback, stream isolation and invalid archive requests",()=>{
                var s=Memory();s.Grant("one","test",new RewardGrant{coins=50});var feed=new ProfileEventFeed(s);string folder=Path.Combine(root,"corruption");var archive=new LocalProfileEventArchive(folder);archive.Flush(feed);string file=Directory.GetFiles(folder,"*.json",SearchOption.AllDirectories).Single();File.WriteAllText(file,"broken");Throws<Exception>(()=>archive.Flush(feed),"Corrupt delivery never silently overwritten");Check(s.Read().coins==1300,"Archive failure cannot mutate player wallet");
                folder=Path.Combine(root,"rollback");archive=new LocalProfileEventArchive(folder);archive.Flush(feed);s.Change(p=>{p.coins-=50;p.rewards.Clear();return true;});Throws<InvalidDataException>(()=>archive.Flush(feed),"Profile rollback is detected against archived receipt");
                var second=Memory();second.Grant("one","test",new RewardGrant{coins=50});Check(archive.Flush(new ProfileEventFeed(second)).written==1,"Different profile owns a different local stream");
                Throws<ArgumentOutOfRangeException>(()=>archive.Flush(feed,0),"Zero batch rejected");Throws<ArgumentOutOfRangeException>(()=>archive.Flush(feed,1001),"Unbounded batch rejected");
            });
            Case("Archive lock contention and subsequent new receipts",()=>{
                var s=Memory();s.Grant("one","test",new RewardGrant{coins=50});var feed=new ProfileEventFeed(s);string folder=Path.Combine(root,"locking");var archive=new LocalProfileEventArchive(folder);archive.Flush(feed);
                string directory=Path.Combine(folder,feed.Capture().stream);using(var locked=new FileStream(Path.Combine(directory,"archive.lock"),FileMode.Open,FileAccess.ReadWrite,FileShare.None))Throws<IOException>(()=>archive.Flush(feed),"Concurrent archive writer rejected");
                s.Grant("two","test",new RewardGrant{tools=new[]{0,1,0,0}});var result=archive.Flush(feed);Check(result.existing==1&&result.written==1&&result.remaining==0,"New receipt is discovered without an unsafe ordering cursor");Check(archive.Flush(feed).existing==2,"Both persisted receipts survive retry");
            });
            Case("Invalid receipts, event schema and alias protection",()=>{
                var s=Memory();string id=Start(s);s.Win(id);var feed=new ProfileEventFeed(s);var snapshot=feed.Capture();snapshot.events[0].delta[0]=99;snapshot.current[0]=0;Check(feed.Capture().current[0]==1300&&feed.Capture().events[0].delta[0]==0,"Returned audit objects cannot alter saved state or future snapshots");
                var invalid=s.Read();invalid.attempts[0].awardedCoins=99;Throws<InvalidOperationException>(()=>ProfileEventFeed.Project(invalid),"Reward differs from first-clear settlement");invalid=s.Read();invalid.attempts[0].toolCommands.Add("8:bad");Throws<InvalidOperationException>(()=>ProfileEventFeed.Project(invalid),"Unknown tool index");invalid=s.Read();invalid.coins=0;Throws<InvalidOperationException>(()=>ProfileEventFeed.Project(invalid),"Negative inferred opening balance cannot reconcile");
                var e=feed.Capture().events[0];e.schema=2;Throws<InvalidOperationException>(()=>e.Validate(),"Future event schema rejected");e.schema=1;e.id="../outside";Throws<InvalidOperationException>(()=>e.Validate(),"Invalid digest cannot become filename");
                invalid=s.Read();invalid.attempts[0].completedAfter=2;Throws<InvalidOperationException>(()=>ProfileEventFeed.Project(invalid),"Inconsistent first-clear progression");
            });
            report.status=report.failures.Count==0?"PASS_NATIVE_PROFILE_EVENTS":"FAIL_NATIVE_PROFILE_EVENTS";string output=Path.GetFullPath("../Verification/Evidence/ProfileEvents");Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"Native_Checks.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.failures.Count==0?0:1);
        }
    }
}
#endif

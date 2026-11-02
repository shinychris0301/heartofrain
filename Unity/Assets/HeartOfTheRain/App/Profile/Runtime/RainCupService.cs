using System;using System.Collections.Generic;using System.Linq;using UnityEngine;
namespace HeartOfTheRain.App.Profile {
    [Serializable] public sealed class RainCupRules {
        public string version;public int unlockClears,durationSeconds;public int[] rivalFinalScores;public RewardGrant[] rankRewards;
        public void Validate(){if(string.IsNullOrEmpty(version)||version.Length>128||unlockClears<0||unlockClears>=50||durationSeconds<1||durationSeconds>2592000||rivalFinalScores==null||rivalFinalScores.Length!=4||rivalFinalScores.Any(n=>n<0||n>50)||rankRewards==null||rankRewards.Length!=5)throw new InvalidOperationException("Invalid Rain Cup rules");foreach(var g in rankRewards){if(g==null)throw new InvalidOperationException("Missing Cup reward");g.Validate();if(g.stars!=0||(g.coins>0?1:0)+g.starting.Count(n=>n>0)+g.tools.Count(n=>n>0)>3)throw new InvalidOperationException("Invalid Cup reward types");}}
        public RainCupRules Copy()=>JsonUtility.FromJson<RainCupRules>(JsonUtility.ToJson(this));
    }
    [Serializable] public sealed class RainCupRun {
        public string id,state;public long joinedAt,endsAt,lastObserved;public int joinedCompleted,points,finalRank;public RainCupRules rules;
        public List<string> scoredAttempts=new List<string>();
        public void Validate(){Guid parsed;if(!Guid.TryParseExact(id,"N",out parsed)||rules==null)throw new InvalidOperationException("Invalid Cup identity");rules.Validate();if(joinedAt<0||endsAt!=checked(joinedAt+rules.durationSeconds)||lastObserved<joinedAt||joinedCompleted<rules.unlockClears||joinedCompleted>=50||points<0||points>50-joinedCompleted||scoredAttempts==null||scoredAttempts.Count!=points||scoredAttempts.Distinct().Count()!=points)throw new InvalidOperationException("Invalid Cup progress");if(state=="Active"){if(finalRank!=0)throw new InvalidOperationException("Active Cup has final rank");}else if(state=="Finished"||state=="Claimed"){if(lastObserved<endsAt||finalRank!=RainCupModel.Rank(points,rules.rivalFinalScores))throw new InvalidOperationException("Invalid final Cup result");}else throw new InvalidOperationException("Invalid Cup state");}
    }
    public sealed class RainCupSnapshot {
        public string state="Unavailable";public int completed;public bool development,canJoin;public long observedNow;public RainCupRules rules;public RainCupRun run;
    }
    public interface IRainCupService {
        RainCupSnapshot View();string Join(string commandId);RewardGrant Claim(string runId);long? CaptureWinTime();long Remaining(RainCupSnapshot snapshot);
    }
    public sealed class UnavailableRainCupService:IRainCupService {
        public RainCupSnapshot View()=>new RainCupSnapshot();public string Join(string id)=>throw new InvalidOperationException("Rain Cup unavailable");public RewardGrant Claim(string id)=>throw new InvalidOperationException("Rain Cup unavailable");public long? CaptureWinTime()=>null;public long Remaining(RainCupSnapshot s)=>0;
    }
    public static class RainCupModel {
        public static string ReceiptKey(string runId)=>"rain-cup/"+runId;
        public static int Rank(int points,int[] rivals)=>1+rivals.Count(n=>n>points);
        public static int[] RivalScores(RainCupRun run,long now){long elapsed=Math.Max(0,Math.Min(run.rules.durationSeconds,now-run.joinedAt));return run.rules.rivalFinalScores.Select(n=>(int)(n*elapsed/run.rules.durationSeconds)).ToArray();}
        public static void Validate(PlayerProfile p){
            if(p.rainCups==null||p.rainCups.Count>100000)throw new InvalidOperationException("Invalid Cup journal");if(p.rainCups.Count==0){if(p.attempts.Any(a=>!string.IsNullOrEmpty(a.rainCupId)||a.rainCupPoint!=0||a.rainCupWinAt!=0))throw new InvalidOperationException("Missing Cup journal");return;}
            var ids=new HashSet<string>();var attempts=p.attempts.ToDictionary(a=>a.id);int pending=0;
            foreach(var run in p.rainCups){if(run==null||!ids.Add(run.id))throw new InvalidOperationException("Duplicate Cup");run.Validate();if(run.joinedCompleted>p.completed)throw new InvalidOperationException("Cup progression moved backwards");if(run.state!="Claimed")pending++;
                foreach(string id in run.scoredAttempts){AttemptRecord a;if(!attempts.TryGetValue(id,out a)||a.state!="Won"||!a.firstClear||a.level<=run.joinedCompleted||a.rainCupId!=run.id||a.rainCupPoint!=1||a.rainCupWinAt<run.joinedAt||a.rainCupWinAt>=run.endsAt)throw new InvalidOperationException("Invalid Cup contribution");}
                var receipt=p.rewards.FirstOrDefault(r=>r.key==ReceiptKey(run.id));if((run.state=="Claimed")!=(receipt!=null))throw new InvalidOperationException("Cup receipt/state mismatch");if(receipt!=null){var g=run.rules.rankRewards[run.finalRank-1];if(receipt.source!="rain-cup"||JsonUtility.ToJson(receipt.grant)!=JsonUtility.ToJson(g))throw new InvalidOperationException("Cup receipt changed");}
            }
            if(pending>1)throw new InvalidOperationException("More than one unfinished Cup");foreach(var a in p.attempts){if(!string.IsNullOrEmpty(a.rainCupId)&&!ids.Contains(a.rainCupId))throw new InvalidOperationException("Unknown attempt Cup");if(a.rainCupPoint<0||a.rainCupPoint>1||a.rainCupPoint==1&&!p.rainCups.Any(r=>r.id==a.rainCupId&&r.scoredAttempts.Contains(a.id)))throw new InvalidOperationException("Missing contribution receipt");}
        }
        public static string Badge(RainCupSnapshot s,long remaining){if(s.state=="Active")return (remaining/3600).ToString("00")+":"+(remaining%3600/60).ToString("00");if(s.state=="Finished")return "Ready";if(s.state=="Locked")return s.completed+"/"+s.rules.unlockClears;if(s.state=="Unavailable")return "Unavailable";return s.canJoin?"Ready":"✓";}
    }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
    // LOCAL, untrusted practice authority. Rival scores follow a fixed linear
    // script; these are never presented as live people or a production ranking.
    public sealed class DevelopmentRainCupService:IRainCupService {
        readonly ProfileService profile;readonly RainCupRules rules;readonly Func<long> clock;long highWater;
        public DevelopmentRainCupService(ProfileService profile,RainCupRules rules,Func<long> clock){this.profile=profile??throw new ArgumentNullException(nameof(profile));if(rules==null)throw new ArgumentNullException(nameof(rules));rules.Validate();this.rules=rules.Copy();this.clock=clock??throw new ArgumentNullException(nameof(clock));highWater=profile.Read().rainCups.LastOrDefault()?.lastObserved??0;}
        long Now(){long now=clock();if(now<0||now>long.MaxValue-2592000)throw new InvalidOperationException("Invalid practice clock");highWater=Math.Max(now,highWater);return highWater;}
        public long? CaptureWinTime(){try{return Now();}catch(Exception){return null;}} // Optional practice availability must not block campaign settlement.
        public long Remaining(RainCupSnapshot s)=>s.run==null?0:Math.Max(0,s.run.endsAt-Math.Max(s.observedNow,Now()));
        public RainCupSnapshot View(){
            var p=profile.Read();long now=Now();var run=p.rainCups.LastOrDefault();if(run!=null&&run.state=="Active"&&Math.Max(now,run.lastObserved)>=run.endsAt){Finish(run.id,now);p=profile.Read();run=p.rainCups.Last();}
            return new RainCupSnapshot{development=true,completed=p.completed,rules=run?.rules??rules,run=run,observedNow=run==null?now:Math.Max(now,run.lastObserved),state=run?.state??(p.completed<rules.unlockClears?"Locked":p.completed>=50?"Exhausted":"Ready"),canJoin=(run==null||run.state=="Claimed")&&p.completed>=rules.unlockClears&&p.completed<50};
        }
        public string Join(string commandId){Guid id;if(!Guid.TryParseExact(commandId,"N",out id))throw new ArgumentException("Invalid Cup command");long now=Now();return profile.Change(p=>{
            var old=p.rainCups.FirstOrDefault(r=>r.id==commandId);if(old!=null)return old.id;
            var latest=p.rainCups.LastOrDefault();if(p.completed<rules.unlockClears||p.completed>=50||latest!=null&&latest.state!="Claimed"||p.attempts.Any(a=>a.state=="Started"||a.state=="Reserved"))throw new InvalidOperationException("Cannot join Cup");
            if(latest!=null&&now<latest.lastObserved)throw new InvalidOperationException("Practice clock moved backwards");p.rainCups.Add(new RainCupRun{id=commandId,state="Active",joinedAt=now,endsAt=checked(now+rules.durationSeconds),lastObserved=now,joinedCompleted=p.completed,rules=rules.Copy()});return commandId;
        });}
        void Finish(string id,long now){profile.Change(p=>{var r=p.rainCups.First(v=>v.id==id);if(r.state!="Active")return false;if(Math.Max(now,r.lastObserved)<r.endsAt)throw new InvalidOperationException("Cup still active");r.lastObserved=Math.Max(now,r.lastObserved);r.finalRank=RainCupModel.Rank(r.points,r.rules.rivalFinalScores);r.state="Finished";return true;});}
        public RewardGrant Claim(string id){long now=Now();return profile.Change(p=>{
            var r=p.rainCups.FirstOrDefault(v=>v.id==id);if(r==null)throw new InvalidOperationException("Unknown Cup");if(r.state=="Claimed")return null;
            if(r.state=="Active"){if(Math.Max(now,r.lastObserved)<r.endsAt)throw new InvalidOperationException("Cup still active");r.lastObserved=Math.Max(now,r.lastObserved);r.finalRank=RainCupModel.Rank(r.points,r.rules.rivalFinalScores);r.state="Finished";}
            var grant=r.rules.rankRewards[r.finalRank-1];ProfileService.ApplyGrant(p,RainCupModel.ReceiptKey(id),"rain-cup",grant);r.state="Claimed";return grant.Copy();
        });}
        public static void RecordWin(PlayerProfile p,AttemptRecord a,long now){
            if(!a.firstClear||string.IsNullOrEmpty(a.rainCupId))return;var r=p.rainCups.First(v=>v.id==a.rainCupId);now=Math.Max(now,r.lastObserved);if(r.state!="Active"||now<r.joinedAt||now>=r.endsAt)return;
            // A rollback cannot move the durable observation backwards. This
            // is a practice guard, not trusted time or anti-cheat protection.
            r.lastObserved=now;r.points++;r.scoredAttempts.Add(a.id);a.rainCupPoint=1;a.rainCupWinAt=now;
        }
    }
#endif
}

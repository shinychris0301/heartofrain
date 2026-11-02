using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace HeartOfTheRain.App.Profile {
    // Receipt projection: no second write alongside a gameplay transaction, no
    // invented timestamps, no network, and no animation or Update callbacks.
    [Serializable] public sealed class ProfileAuditEvent {
        public int schema=1;public string id,stream,kind,receipt,aggregate,category;
        public int level,rank,points;
        // coins, stars, lives, first clears, starting[4], tools[4]. Signed deltas.
        public long[] delta=new long[12];
        public void Validate(){
            if(schema!=1||!ProfileEventFeed.Digest(stream)||!ProfileEventFeed.Digest(receipt)||!ProfileEventFeed.Digest(aggregate)||id!=ProfileEventFeed.EventId(stream,kind,receipt)||delta==null||delta.Length!=12||level<0||level>50||rank<0||rank>5||points<0||points>1)throw new InvalidOperationException("Invalid audit event");
            var allowed=new HashSet<string>{"attempt_reserved","attempt_started","attempt_cancelled","attempt_won","attempt_lost","attempt_interrupted","tool_spent","level_completed","reward_granted","cup_joined","cup_point","cup_finished","cup_claimed","lives_regenerated","lives_refilled","attempt_released"};
            if(!allowed.Contains(kind)||!new[]{"campaign","daily_gift","wellworks","rain_cup","other"}.Contains(category))throw new InvalidOperationException("Unknown audit schema value");
            for(int i=0;i<12;i++){
                long n=delta[i];bool valid=n==0;
                if(kind=="attempt_started"&&i>=4&&i<8)valid=n==0||n==-1;
                if(kind=="attempt_released"&&i>=4&&i<8)valid=n==0||n==1;
                if(kind=="tool_spent"&&i>=8)valid=n==0||n==-1;
                if((kind=="attempt_lost"||kind=="attempt_interrupted")&&i==2)valid=n==-1;
                if(kind=="level_completed"&&i==3)valid=n==1;
                if(kind=="reward_granted"&&(i<2||i>=4))valid=n>=0&&n<=int.MaxValue;
                if(kind=="lives_regenerated"&&i==2)valid=n>=1&&n<=int.MaxValue;
                if(kind=="lives_refilled"&&i==0)valid=n<0&&n>=-int.MaxValue;
                if(kind=="lives_refilled"&&i==2)valid=n>=1&&n<=int.MaxValue;
                if(!valid)throw new InvalidOperationException("Invalid audit delta");
            }
            if(kind=="tool_spent"&&delta.Sum()!=-1||kind=="cup_point"&&points!=1||kind!="cup_point"&&points!=0)throw new InvalidOperationException("Invalid audit quantity");
            bool attempt=kind.StartsWith("attempt_",StringComparison.Ordinal)||kind=="tool_spent"||kind=="level_completed"||kind=="cup_point";
            if(attempt&&level==0||!attempt&&kind!="reward_granted"&&level!=0)throw new InvalidOperationException("Invalid audit level");
            if(kind.StartsWith("cup_",StringComparison.Ordinal)?category!="rain_cup":kind!="reward_granted"&&category!="campaign")throw new InvalidOperationException("Invalid audit category");
            if(kind=="reward_granted"&&((category=="campaign")!=(level>0)))throw new InvalidOperationException("Invalid reward origin");
            if((kind=="cup_finished"||kind=="cup_claimed")!=(rank>0))throw new InvalidOperationException("Invalid audit rank");
        }
    }
    [Serializable] public sealed class ProfileEventSnapshot {
        public string stream;public long sourceRevision;
        public long[] current,opening;
        public List<ProfileAuditEvent> events;
    }
    public sealed class ProfileEventFeed {
        readonly ProfileService profile;
        public ProfileEventFeed(ProfileService profile){this.profile=profile??throw new ArgumentNullException(nameof(profile));}
        internal static bool Digest(string value)=>value!=null&&value.Length==64&&value.All(c=>c>='0'&&c<='9'||c>='a'&&c<='f');
        internal static string EventId(string stream,string kind,string receipt)=>ProfileJson.Hash("hotr-event-v1|"+stream+"|"+kind+"|"+receipt);
        public ProfileEventSnapshot Capture()=>Project(profile.Read());
        public static ProfileEventSnapshot Project(PlayerProfile profile){
            if(profile==null)throw new ArgumentNullException(nameof(profile));
            // Copy before inspecting: callers cannot mutate events through a profile alias.
            var p=ProfileJson.Copy(profile);p.Validate();string stream=ProfileJson.Hash("hotr-local-stream-v1|"+p.playerId);
            var events=new List<ProfileAuditEvent>();
            Action<string,string,string,string,int,int,int,long[]> add=(kind,key,aggregate,category,level,rank,points,delta)=>{
                string receipt=ProfileJson.Hash(key);var e=new ProfileAuditEvent{stream=stream,kind=kind,receipt=receipt,aggregate=ProfileJson.Hash(aggregate),category=category,level=level,rank=rank,points=points,delta=delta??new long[12]};e.id=EventId(stream,kind,receipt);e.Validate();events.Add(e);
            };
            int previousClear=-1;
            foreach(var a in p.attempts){
                bool started=a.state!="Reserved"&&a.state!="Cancelled";
                bool won=a.state=="Won",lost=a.state=="Lost"||a.state=="Interrupted";
                if(!started&&a.toolCommands.Count!=0||a.livesAfter>p.maxLives||!won&&(a.firstClear||a.awardedCoins!=0||a.awardedStars!=0))throw new InvalidOperationException("Audit attempt receipt mismatch");
                if(won&&(a.firstClear?(a.level!=a.completedBefore+1||a.completedAfter!=a.completedBefore+1||a.awardedCoins!=a.coins||a.awardedStars!=a.stars):(a.completedAfter!=a.completedBefore||a.awardedCoins!=0||a.awardedStars!=0)))throw new InvalidOperationException("Audit win receipt mismatch");
                if(won&&a.firstClear){if(a.completedAfter>p.completed||previousClear>=0&&a.completedBefore!=previousClear)throw new InvalidOperationException("Audit progression receipt mismatch");previousClear=a.completedAfter;}
                add("attempt_reserved",a.id,a.id,"campaign",a.level,0,0,null);
                if(a.state=="Cancelled")add("attempt_cancelled",a.id,a.id,"campaign",a.level,0,0,null);
                if(started){var debit=new long[12];for(int i=0;i<4;i++)debit[4+i]=-a.selected[i];add("attempt_started",a.id,a.id,"campaign",a.level,0,0,debit);}
                foreach(string command in a.toolCommands){
                    if(command.Length<3||command[0]<'0'||command[0]>'3'||command[1]!=':'||command.Substring(2).Contains(":"))throw new InvalidOperationException("Audit tool receipt mismatch");
                    var debit=new long[12];debit[8+command[0]-'0']=-1;add("tool_spent",a.id+"/"+command,a.id,"campaign",a.level,0,0,debit);
                }
                if(won){
                    add("attempt_won",a.id,a.id,"campaign",a.level,0,0,null);
                    if(a.firstClear){var progress=new long[12];progress[3]=1;add("level_completed",a.id,a.id,"campaign",a.level,0,0,progress);var credit=new long[12];credit[0]=a.awardedCoins;credit[1]=a.awardedStars;add("reward_granted","attempt/"+a.id,a.id,"campaign",a.level,0,0,credit);}
                    if(a.rainCupPoint==1)add("cup_point",a.id,a.rainCupId,"rain_cup",a.level,0,1,null);
                }
                if(lost){var debit=new long[12];debit[2]=-1;add(a.state=="Lost"?"attempt_lost":"attempt_interrupted",a.id,a.id,"campaign",a.level,0,0,debit);}
                // Engine-fault release: the starting debit is refunded, no life moves.
                if(a.state=="Released"){var refund=new long[12];for(int i=0;i<4;i++)refund[4+i]=a.selected[i];add("attempt_released",a.id,a.id,"campaign",a.level,0,0,refund);}
            }
            foreach(var r in p.rewards){
                string category=r.source.StartsWith("daily/",StringComparison.Ordinal)?"daily_gift":r.source=="wellworks"?"wellworks":r.source=="rain-cup"?"rain_cup":"other";
                var credit=new long[12];credit[0]=r.grant.coins;credit[1]=r.grant.stars;for(int i=0;i<4;i++){credit[4+i]=r.grant.starting[i];credit[8+i]=r.grant.tools[i];}
                add("reward_granted","reward/"+r.key,"reward/"+r.key,category,0,0,0,credit);
            }
            // Timer credits and paid refills are campaign life receipts; without
            // them the inferred opening balance would exceed maxLives.
            foreach(var c in p.lifeCredits){var credit=new long[12];credit[2]=c.lives;add("lives_regenerated","life-credit/"+c.key,"life-credit/"+c.key,"campaign",0,0,0,credit);}
            foreach(var r in p.lifeRefills){var delta=new long[12];delta[0]=-r.coins;delta[2]=r.livesAfter-r.livesBefore;add("lives_refilled","life-refill/"+r.key,"life-refill/"+r.key,"campaign",0,0,0,delta);}
            foreach(var c in p.rainCups){
                add("cup_joined",c.id,c.id,"rain_cup",0,0,0,null);
                if(c.state!="Active")add("cup_finished",c.id,c.id,"rain_cup",0,c.finalRank,0,null);
                if(c.state=="Claimed")add("cup_claimed",c.id,c.id,"rain_cup",0,c.finalRank,0,null);
            }
            if(events.Select(e=>e.id).Distinct().Count()!=events.Count)throw new InvalidOperationException("Duplicate audit identity");
            // Historical snapshots may start after progress or grants already existed.
            // This residual is explicitly an opening balance, never invented income.
            var current=new long[]{p.coins,p.stars,p.lives,p.completed,p.starting[0],p.starting[1],p.starting[2],p.starting[3],p.tools[0],p.tools[1],p.tools[2],p.tools[3]};
            var opening=(long[])current.Clone();foreach(var e in events)for(int i=0;i<12;i++)opening[i]=checked(opening[i]-e.delta[i]);
            if(opening.Any(n=>n<0||n>int.MaxValue)||opening[2]>p.maxLives||opening[3]>50)throw new InvalidOperationException("Audit balances do not reconcile with receipts");
            return new ProfileEventSnapshot{stream=stream,sourceRevision=p.revision,current=current,opening=opening,events=events};
        }
    }
}

using System;
using System.Linq;
using HeartOfTheRain.App.Profile;

namespace HeartOfTheRain.App.ServerRewards {
    public sealed class RewardAccess {
        public readonly string Origin,PlayerId;public readonly long Generation;public readonly bool AllowLoopback;readonly Func<string> access;
        public string CurrentAccess=>access();
        public RewardAccess(string origin,string player,long generation,Func<string> currentAccess,bool allowLoopback=false){Origin=origin;PlayerId=player;Generation=generation;access=currentAccess??throw new ArgumentNullException(nameof(currentAccess));AllowLoopback=allowLoopback;}
    }
    [Serializable] public sealed class ServerMilestone {public int level;public RewardGrant grant;public bool eligible,claimed;}
    [Serializable] public sealed class ServerWellworks {public int completed;public ServerMilestone[] milestones;}
    [Serializable] public sealed class ServerCupRun {public string id;public long joinedAt,endsAt;public int points,finalRank;public int[] rivalScores;}
    [Serializable] public sealed class ServerCup {public string state;public int completed;public bool practice,simulatedRivals,realCompetition,canJoin;public long serverUtc;public RainCupRules rules;public ServerCupRun run;}
    [Serializable] public sealed class ServerCupJoined {public string runId;public long endsAt;public bool practice;}
    [Serializable] public sealed class ServerRewardReceipt {public string id,source;public RewardGrant grant;public long serverUtc,cursor;}
    [Serializable] public sealed class RewardMilestoneClaim {public string commandId;public int level;}
    [Serializable] public sealed class RewardCupClaim {public string commandId,runId;}
    [Serializable] public sealed class RewardJoin {public string commandId;}
    public sealed class RewardReply<T> where T:class {
        public T value;public string error;public bool unknown;public long status;public bool Ok=>value!=null&&error==null;
        public static RewardReply<T> Success(T value)=>new RewardReply<T>{value=value};
        public static RewardReply<T> Fail(string error,bool unknown=false,long status=0)=>new RewardReply<T>{error=error,unknown=unknown,status=status};
    }
    // These detached objects exist solely for the approved layout engines. They
    // are never saved, validated as a player profile, or passed to ProfileService.
    public static class ServerRewardProjection {
        public static WellworksView Wellworks(ServerWellworks data,string player){
            var profile=new PlayerProfile{playerId=player,completed=data.completed,coins=0,stars=0,starting=new int[4],tools=new int[4]};
            foreach(var m in data.milestones)if(m.claimed)profile.rewards.Add(new RewardReceipt{key=WellworksService.Key(m.level),source="server-wellworks",grant=m.grant.Copy()});
            return new WellworksView{enabled=true,player=profile,schedule=new WellworksSchedule{milestones=data.milestones.Select(m=>new WellworksMilestone{level=m.level,grant=m.grant.Copy()}).ToArray()}};
        }
        public static RainCupSnapshot Cup(ServerCup data){
            var result=new RainCupSnapshot{state=data.state,completed=data.completed,development=true,canJoin=data.canJoin,observedNow=data.serverUtc,rules=data.rules.Copy()};
            if(data.run!=null)result.run=new RainCupRun{id=data.run.id,state=data.state,joinedAt=data.run.joinedAt,endsAt=data.run.endsAt,lastObserved=data.serverUtc,points=data.run.points,finalRank=data.run.finalRank,rules=data.rules.Copy()};
            return result;
        }
    }
}

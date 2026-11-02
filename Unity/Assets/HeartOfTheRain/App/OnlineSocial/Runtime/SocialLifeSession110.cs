using System;
using System.Linq;

namespace HeartOfTheRain.App.OnlineSocial
{
    public sealed partial class SocialPageSession82
    {
        double lifeObservedAt110;
        long lifeServerUtc110;
        SocialMutation82 lastLifeReceipt110;
        public SocialMutation82 LastLifeReceipt110 => !ActiveOwner()||lastLifeReceipt110 == null ? null : UnityEngine.JsonUtility.FromJson<SocialMutation82>(UnityEngine.JsonUtility.ToJson(lastLifeReceipt110));
        public long LifeServerNow110 => !ActiveOwner()||lifeServerUtc110 <= 0 ? 0 : lifeServerUtc110 + (long)Math.Max(0, clock() - lifeObservedAt110);
        public long TeamMessageAcknowledged110 {get;private set;}
        void AcknowledgeMessage110(){TeamMessageAcknowledged110++;}
        void ObserveLifeClock110(long utc) { lifeServerUtc110 = Math.Max(LifeServerNow110,utc); lifeObservedAt110 = clock(); }
        bool newTeamMessages110;
        public bool HasNewTeamMessages110=>ActiveOwner()&&newTeamMessages110;
        public bool ProbeTeamMessages110()=>!string.IsNullOrEmpty(teamId)&&Read<SocialMessages82>(SocialPane82.TeamTail110,done=>client.GetMessagesTail("Team",teamId,PageSize,done),value=>{var current=Snapshot<SocialMessages82>(SocialPane82.TeamChat);if(current!=null&&value.nextCursor>current.nextCursor)newTeamMessages110=true;});
        void AcceptedLife110(SocialMutation82 value)
        {
            if(value == null || value.operation == null || !value.operation.StartsWith("life.", StringComparison.Ordinal)) return;
            lastLifeReceipt110 = UnityEngine.JsonUtility.FromJson<SocialMutation82>(UnityEngine.JsonUtility.ToJson(value));
            ObserveLifeClock110(value.serverUtc);
            // This is presentation/cache invalidation only. A wallet fetch by
            // the managed gameplay gateway remains the only balance projection.
            states.Remove(SocialPane82.TeamLives110);states.Remove(SocialPane82.OwnedLives110);
        }
        public bool RefreshTeamLives110(long before = 0)
        {
            if(string.IsNullOrEmpty(teamId)) return false;
            var messages = Snapshot<SocialMessages82>(SocialPane82.TeamChat);
            string[] ids = before > 0 ? new string[0] : messages?.messages?.Select(value => value.messageId).Take(8).ToArray() ?? new string[0];
            return Read<SocialLifeRequests110>(SocialPane82.TeamLives110, done => client.GetTeamLives110(teamId, before, ids, done), value => ObserveLifeClock110(value.serverUtc));
        }
        public bool RefreshOwnedLives110(long after = 0) => Read<SocialOwnedLives110>(SocialPane82.OwnedLives110, done => client.GetOwnedLives110(after, done), value => ObserveLifeClock110(value.serverUtc));
        public bool RequestTeamLives110(string commandId) => !string.IsNullOrEmpty(teamId) && Mutate(SocialPane82.TeamLives110, done => client.RequestTeamLives110(commandId, teamId, done), AcceptedLife110);
        public bool HelpTeamLife110(string commandId, string requestId) => !string.IsNullOrEmpty(teamId) && Mutate(SocialPane82.TeamLives110, done => client.HelpTeamLife110(commandId, teamId, requestId, done), AcceptedLife110);
        public bool ClaimTeamLives110(string commandId, string requestId) => Mutate(SocialPane82.OwnedLives110, done => client.ClaimTeamLives110(commandId, requestId, done), AcceptedLife110);
    }
}

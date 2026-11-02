using System;

namespace HeartOfTheRain.App.OnlineSocial
{
    [Serializable] public sealed class SocialLifePolicy110
    {
        public string version;public int capacity, cooldownSeconds, lifetimeSeconds;
        public bool helpSpendsDonorLives;
    }
    [Serializable] public sealed class SocialLifeRequest110
    {
        public string requestId, messageId, eventId, teamId, playerId, displayName, state, closeReason,collectBlockedReason;
        public long sequence, createdAt, closesAt, nextRequestAt;
        public int received, required, claimed, remaining;
        public bool canHelp, helped, canCollect;
    }
    [Serializable] public sealed class SocialLifeRequests110
    {
        public string teamId;
        public long serverUtc, nextRequestAt, olderCursor;
        public bool hasOlder;
        public SocialLifePolicy110 policy;
        public SocialLifeRequest110 ownRequest;
        public SocialLifeRequest110[] requests;
    }
    [Serializable] public sealed class SocialOwnedLives110
    {
        public long serverUtc, nextCursor;
        public bool hasMore;
        public SocialLifePolicy110 policy;
        public SocialLifeRequest110[] requests;
    }
}

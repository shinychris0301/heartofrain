using System;

namespace HeartOfTheRain.App.OnlineSocial
{
    // Access lives in memory and is fetched from the current managed owner.
    // Never serialize this value into a profile, outbox, log or report.
    public sealed class SocialAccess82 {
        public readonly string playerId, bearer;
        public SocialAccess82(string playerId, string bearer) { this.playerId = playerId; this.bearer = bearer; }
    }
    public sealed class SocialReply82<T> where T : class {
        public readonly T value; public readonly string error, refusal; public readonly bool unknown;
        public bool Succeeded => value != null && error == null;
        SocialReply82(T value, string error, bool unknown, string refusal = null) { this.value = value; this.error = error; this.unknown = unknown; this.refusal = refusal; }
        public static SocialReply82<T> Ok(T value) => new SocialReply82<T>(value ?? throw new ArgumentNullException(nameof(value)), null, false);
        public static SocialReply82<T> Fail(string error, bool unknown = false, string refusal = null) => new SocialReply82<T>(null, error ?? "SocialUnavailable", unknown, refusal);
    }
    [Serializable] public sealed class SocialProfile82 { public string playerId, displayName; public int completedLevels; public bool leaderboardOptIn; }
    [Serializable] public sealed class SocialRelationship82 { public string playerId, state, requestId; }
    [Serializable] public sealed class SocialFriends82 { public SocialProfile82[] friends; public bool hasMore; public string nextCursor; }
    [Serializable] public sealed class SocialFriendRequest82 { public string requestId, direction, state; public SocialProfile82 profile; public long createdAt; }
    [Serializable] public sealed class SocialRequests82 { public SocialFriendRequest82[] requests; public bool hasMore; public string nextCursor; }
    [Serializable] public sealed class SocialBlock82 { public string playerId; public long createdAt; }
    [Serializable] public sealed class SocialBlocks82 { public SocialBlock82[] blocks; public bool hasMore; public string nextCursor; }
    [Serializable] public sealed class SocialTeamMember82 { public string playerId, displayName; public bool isOwner; }
    [Serializable] public sealed class SocialTeam82 {
        public string teamId, name, description, ownerId,badgeId; public int memberCount, capacity;
        public bool isMember; public SocialTeamMember82[] members;
        public string membershipVersion,leaveRestrictionReason; public bool leaveClosesTeam;
    }
    [Serializable] public sealed class SocialTeams82 { public SocialTeam82[] teams; public string myTeamId, nextCursor; public bool hasMore; }
    [Serializable] public sealed class SocialMessage82 { public string messageId, authorId, displayName, text; public long sequence, createdAt; }
    [Serializable] public sealed class SocialMessages82 { public SocialMessage82[] messages; public long nextCursor, olderCursor, unreadCount; public bool hasMore, hasOlder, hasNewer; }
    [Serializable] public sealed class SocialFirstClear82 { public int level; public long verifiedAt; }
    [Serializable] public sealed class SocialAttemptCounts82 { public int Reserved, Started, AwaitingContinuation, Won, Lost, Cancelled, Released; }
    [Serializable] public sealed class SocialRecords82 {
        public int completedLevels; public SocialAttemptCounts82 attempts; public SocialFirstClear82[] firstClears;
        public long nextCursor; public bool hasMore, clientScoresAccepted; public string scoreSource;
    }
    [Serializable] public sealed class SocialRank82 { public string playerId, displayName; public int score; public long rank; }
    [Serializable] public sealed class SocialRegion89 { public string playerId,regionCode,regionSource;public bool locationVerified; }
    [Serializable] public sealed class SocialTeamRank89 { public string teamId,name;public int score,memberCount;public long rank; }
    [Serializable] public sealed class SocialTeamLeaderboard89 { public string scope,regionCode,scoreSource,teamRegionSource;public bool tiesShareRank,hasMore,rewardGranted;public SocialTeamRank89[] entries;public int nextOffset; }
    [Serializable] public sealed class SocialLeaderboard82 {
        public string scope, scoreSource,regionCode; public bool tiesShareRank, hasMore, rewardGranted;
        public SocialRank82[] entries; public int nextOffset;
    }
    // A typed union for the small public mutation receipts. The transport
    // validates required fields separately for every captured operation.
    [Serializable] public sealed class SocialMutation82 {
        public string playerId, displayName, requestId, state, teamId, messageId, reportId, action, receiptScope,regionCode,regionSource;
        public bool locationVerified;
        public bool leaderboardOptIn, blocked, automatedDecision, reviewPendingAtAcceptance;
        public int completedLevels; public long sequence, createdAt, through;
        public string operation,eventId,receiptId,friendId,inviteId,reason;public long createdAtUtc,expiresAtUtc;
        public int creditedLives,lives,maxLives,received,claimed,remaining,rewardCoins,rewardLives,coins;public long walletRevision,nextLifeAt,serverUtc,readAtUtc;
    }
    [Serializable] public sealed class SocialOperationReceipt82 {
        public string commandId, operation, status, receiptScope, payloadDigest, digestScope;
        public SocialMutation82 response;
    }
}

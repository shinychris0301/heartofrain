using System;
namespace HeartOfTheRain.App.OnlineSocial {
 [Serializable] public sealed class SocialInvitableFriend112 { public string friendId,displayName,inviteState,inviteId;public int completedLevels;public long expiresAtUtc; }
 [Serializable] public sealed class SocialInviteFriends112 { public string teamId,teamName,badgeId,publicTeamCode,nextCursor;public long serverUtc;public int memberCount,capacity;public bool canInvite,hasMore;public SocialInvitableFriend112[] friends; }
 [Serializable] public sealed class SocialInvitation112 {public string inviteId,teamId,teamName,badgeId,senderName,state;public int memberCount,capacity;public long sequence,expiresAtUtc;}
 [Serializable] public sealed class SocialInvitations112 {public long serverUtc,nextCursor;public bool hasMore;public SocialInvitation112[] invitations;}
 [Serializable] public sealed class SocialInvitationDetail112 {public long serverUtc;public SocialInvitation112 invitation;}
}

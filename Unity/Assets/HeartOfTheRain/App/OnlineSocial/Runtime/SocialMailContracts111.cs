using System;
namespace HeartOfTheRain.App.OnlineSocial {
 [Serializable] public sealed class SocialMailMessage111 { public string messageId,teamId,senderLabel,title,body,claimState,claimBlockedReason; public long sequence,sentAtUtc,readAtUtc,expiresAtUtc; public int rewardCoins,rewardLives; public bool canClaim; }
 [Serializable] public sealed class SocialMailList111 { public string teamId;public long serverUtc,olderCursor;public int unreadCount;public bool hasOlder;public SocialMailMessage111[] messages; }
 [Serializable] public sealed class SocialMailReward111 { public string messageId,claimState,claimBlockedReason;public long sequence,sentAtUtc,expiresAtUtc;public int rewardCoins,rewardLives;public bool canClaim; }
 [Serializable] public sealed class SocialOwnedMail111 { public long serverUtc,nextCursor;public bool hasMore;public SocialMailReward111[] rewards; }
 [Serializable] public sealed class SocialMailDetail111 { public long serverUtc;public SocialMailMessage111 message; }
}

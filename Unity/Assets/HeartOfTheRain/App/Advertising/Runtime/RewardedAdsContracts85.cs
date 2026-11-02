using System;

namespace HeartOfTheRain.App.Advertising {
    public enum RewardedSignal85 { Shown, CompletedInfoOnly, Closed, Failed }
    // A recorded, explicit decision. Neither loading a page nor another
    // feature's consent can create this advertising permission.
    public sealed class AdPrivacy85 {
        public readonly bool Accepted, Personalized, AgeRestricted;
        public AdPrivacy85(bool accepted,bool personalized=false,bool ageRestricted=true){Accepted=accepted;Personalized=personalized;AgeRestricted=ageRestricted;}
    }
    public interface IRewardedAdsProvider85:IDisposable {
        bool Installed{get;}
        void Load(Action<bool,string> complete);
        void Show(Action<RewardedSignal85> signal);
    }
    public sealed class UnavailableRewardedAdsProvider85:IRewardedAdsProvider85 {
        public bool Installed=>false;
        public void Load(Action<bool,string> complete)=>complete(false,"AdsSdkUnavailable");
        public void Show(Action<RewardedSignal85> signal)=>signal(RewardedSignal85.Failed);
        public void Dispose(){}
    }
    [Serializable] public sealed class AdReceipt85 {
        public string id,walletReceiptId,completionSource;public int coins;public long serverUtc,walletRevision;
    }
    [Serializable] public sealed class AdOpportunity85 {
        public string opportunityId,playerId,placement,configVersion,state,completionMode,verificationMode,completionSource;
        public int rewardCoins,dailyLimit,utcOffsetSeconds,claimedUtcOffsetSeconds,cooldownSeconds;
        public long reservedDay,claimedDay,createdAt,expiresAt,clientReportedAt,verifiedAt,claimedAt,serverUtc;
        public bool completionAuthoritative;public AdReceipt85 receipt;
    }
    [Serializable] public sealed class AdStatus85 {
        public bool enabled,available,productionEnabled;public string reason,verificationMode,completionMode,placement,configVersion,timeZoneId;
        public int rewardCoins,dailyLimit,utcOffsetSeconds,nextDayUtcOffsetSeconds,cooldownSeconds,claimedToday,remainingToday,cooldownRemainingSeconds;
        public long day,dayStartedAt,nextEligibleAt,nextDayAt,serverUtc;public AdOpportunity85 activeOpportunity;
    }
    public sealed class AdReply85<T> where T:class {
        public readonly T Value;public readonly string Error;public readonly bool Unknown,DefinitiveReserveDenial;
        public bool Ok=>Value!=null&&Error==null;
        AdReply85(T value,string error,bool unknown,bool definitiveReserveDenial=false){Value=value;Error=error;Unknown=unknown;DefinitiveReserveDenial=definitiveReserveDenial;}
        public static AdReply85<T> Success(T value)=>new AdReply85<T>(value,null,false);
        public static AdReply85<T> Fail(string error,bool unknown=false)=>new AdReply85<T>(null,error,unknown);
        // Produced only by the narrow /reserve HTTP error classifier. A later
        // denial cannot fence an earlier unknown request with the same ID.
        internal static AdReply85<T> ReserveDenied(string error)=>new AdReply85<T>(null,error,false,true);
    }
}

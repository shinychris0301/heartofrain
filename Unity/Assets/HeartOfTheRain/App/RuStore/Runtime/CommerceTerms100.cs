using System;
using System.Collections.Generic;
using System.Linq;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.Profile;

namespace HeartOfTheRain.App.RuStore {
    [Serializable] public sealed class CommercePolicy100 {
        public bool specified,repeatable=true,eligible=true;
        // Zero represents the server's JSON null (unlimited), never a zero limit.
        public int purchaseLimitPerPlayer;public string eligibility="Available",pendingOrderId;
    }
    [Serializable] public sealed class RuStorePendingOrders100 {
        public string playerId;public RuStoreServerOrder[] orders;public long nextCursor;public bool hasMore,productionEnabled;
    }
    // Shared typed transport validation. Only six historic coin products may
    // omit the additive fields; bundles never infer an inventory grant.
    public static class CommerceTerms100 {
        public static RewardGrant ParseGrant(string json,int coins,string id)=>Grant(SocialJson82.Read(json),coins,id);
        public static CommercePolicy100 ParsePolicy(string json,string id)=>Policy(SocialJson82.Read(json),id);
        public static bool LegacyCoin(string id)=>new[]{"coins-1000","coins-5000","coins-10000","coins-25000","coins-50000","coins-100000"}.Contains(id);
        public static bool Same(RewardGrant a,RewardGrant b)=>a!=null&&b!=null&&a.coins==b.coins&&a.stars==b.stars&&a.starting!=null&&b.starting!=null&&a.tools!=null&&b.tools!=null&&a.starting.SequenceEqual(b.starting)&&a.tools.SequenceEqual(b.tools);
        public static RewardGrant Grant(Dictionary<string,object> row,int coins,string id){
            if(!row.TryGetValue("grant",out var raw)){
                if(!LegacyCoin(id)||coins!=int.Parse(id.Substring(6),System.Globalization.CultureInfo.InvariantCulture))throw new FormatException("FullCommerceGrantRequired");
                return new RewardGrant{coins=coins};
            }
            var fields=SocialJson82.Object(raw);
            var result=new RewardGrant{coins=(int)SocialJson82.Number(fields,"coins",1,int.MaxValue),stars=(int)SocialJson82.Number(fields,"stars",0,0)};
            if(result.coins!=coins)throw new FormatException("CommerceCoinGrantConflict");
            foreach(string key in new[]{"starting","tools"}){
                var values=SocialJson82.Array(fields,key,4);
                if(values.Count!=4||values.Any(v=>!(v is long)||(long)v<0||(long)v>int.MaxValue))throw new FormatException("CommerceInventoryGrantInvalid");
                if(key=="starting")result.starting=values.Select(v=>(int)(long)v).ToArray();else result.tools=values.Select(v=>(int)(long)v).ToArray();
            }
            return result;
        }
        public static CommercePolicy100 Policy(Dictionary<string,object> row,string id){
            bool any=new[]{"purchaseLimitPerPlayer","repeatable","eligible","pendingOrderId","eligibility"}.Any(row.ContainsKey);
            if(!any){if(!LegacyCoin(id))throw new FormatException("CommerceEligibilityRequired");return new CommercePolicy100();}
            object cap=SocialJson82.Field(row,"purchaseLimitPerPlayer");
            if(cap!=null&&(!(cap is long)||(long)cap!=1))throw new FormatException("CommercePurchaseLimitInvalid");
            var value=new CommercePolicy100{specified=true,purchaseLimitPerPlayer=cap==null?0:1,repeatable=SocialJson82.Flag(row,"repeatable"),eligible=SocialJson82.Flag(row,"eligible"),eligibility=SocialJson82.Text(row,"eligibility",32)};
            object pending=SocialJson82.Field(row,"pendingOrderId");
            if(pending!=null&&(!(pending is string)||!PayRequest.Hex((string)pending)))throw new FormatException("CommercePendingOrderInvalid");
            value.pendingOrderId=pending as string;
            if(value.repeatable!=(value.purchaseLimitPerPlayer==0)||!new[]{"Available","Pending","Purchased","RefundReview"}.Contains(value.eligibility)||value.eligible!=(value.eligibility=="Available"))throw new FormatException("CommerceEligibilityConflict");
            return value;
        }
    }
}

using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.OnlineSocial;
using UnityEngine;

namespace HeartOfTheRain.App.ShopCheckout86 {
    [Serializable] public sealed class CheckoutConfiguration86 {
        public int version;public bool enabled,sandbox;public string consoleAppId;
        [NonSerialized] public bool productionEnabled;
        [NonSerialized] public string backendOrigin,packageName,verificationMode;
        public CommerceVerificationMode125 Verification=>CommerceVerification125.Value(verificationMode);
        public static bool Valid(CheckoutConfiguration86 value){try{long id;if(value==null)return false;string mode=CommerceVerification125.Legacy(value.verificationMode);
            bool legacy=mode==CommerceVerification125.ProviderApi&&(value.version==1&&value.sandbox&&!value.productionEnabled||value.version==2&&!value.sandbox&&value.productionEnabled);
            bool sdk=value.version==3&&mode==CommerceVerification125.SdkClientReported&&value.sandbox!=value.productionEnabled&&!string.IsNullOrEmpty(value.packageName)&&RuStoreBackendClient.IsAllowedOrigin(value.backendOrigin);
            return (legacy||sdk)&&value.enabled&&value.consoleAppId!=null&&Regex.IsMatch(value.consoleAppId,@"\A[1-9][0-9]{0,18}\z")&&long.TryParse(value.consoleAppId,out id)&&id>0;}catch{return false;}}
        public static CheckoutConfiguration86 ParseProduction122(string json,ServerGameplayConfiguration server,string actualPackage){
            try{
                var row=SocialJson82.Read(json);var fields=new[]{"version","enabled","sandbox","consoleAppId","runtimeMode","packageName","backendOrigin"};
                if(row.Count!=fields.Length||row.Keys.Any(key=>!fields.Contains(key))||server==null||!server.productionEnabled)throw new FormatException();
                SocialJson82.Number(row,"version",2,2);
                string package=SocialJson82.Text(row,"packageName",255),origin=SocialJson82.Text(row,"backendOrigin",512),appId=SocialJson82.Text(row,"consoleAppId",19);
                if(!SocialJson82.Flag(row,"enabled")||SocialJson82.Flag(row,"sandbox")||SocialJson82.Text(row,"runtimeMode",16)!="production"
                    ||package!=actualPackage||package!=server.packageName||origin!=server.origin||appId!=server.consoleAppId)throw new FormatException();
                var result=new CheckoutConfiguration86{version=2,enabled=true,sandbox=false,consoleAppId=appId,productionEnabled=true,backendOrigin=origin,packageName=package};
                if(!Valid(result))throw new FormatException();return result;
            }catch(Exception){throw new FormatException("ProductionCheckoutConfigurationInvalid");}
        }
        public static bool TryRead(out CheckoutConfiguration86 value){
            value=null;
            var sdk=ServerProductionConfiguration122.ReadResource(CheckoutSdkConfiguration125.ResourceKey);
            if(sdk.present||CheckoutSdkConfiguration125.Required){
                try{ServerGameplayConfiguration selected;string why;
                    if(sdk.failed||!ServerGameplayConfiguration.TryRead(out selected,out why)||selected==null)return false;
                    value=CheckoutSdkConfiguration125.Parse(sdk.json,selected,Application.identifier);return true;
                }catch{return false;}
            }
            var production=ServerProductionConfiguration122.ReadResource(ServerProductionConfiguration122.ResourceKey);
            var checkout=ServerProductionConfiguration122.ReadResource(ServerProductionConfiguration122.CheckoutResourceKey);
            if(production.present||checkout.present||ServerProductionConfiguration122.ProfileRequired){
                try{
                    ServerGameplayConfiguration server;string why;
                    if(!ServerGameplayConfiguration.TryRead(out server,out why)||server==null||!server.productionEnabled||!checkout.present||checkout.failed)return false;
                    value=ParseProduction122(checkout.json,server,Application.identifier);return true;
                }catch(Exception){return false;}
            }
            string path=Environment.GetEnvironmentVariable("HOTR_SHOP_CHECKOUT86_CONFIG");if(string.IsNullOrEmpty(path))path=Path.Combine(Application.persistentDataPath,"ServerReview","checkout.json");
            try{if(!File.Exists(path)||new FileInfo(path).Length>4096)return false;var parsed=JsonUtility.FromJson<CheckoutConfiguration86>(File.ReadAllText(path,new UTF8Encoding(false,true)));if(!Valid(parsed))return false;value=parsed;return true;}catch{return false;}
        }
    }
    [Serializable] public sealed class CheckoutProduct86 {public string id,storeProductId,currency;public int coins,amountMinor,quantity;public RewardGrant grant;public CommercePolicy100 policy;}
    [Serializable] public sealed class CheckoutCatalog86 {[NonSerialized] public string verificationMode;public CommerceVerificationMode125 Verification=>CommerceVerification125.Value(verificationMode);public string version,appId,balanceScope;public bool enabled,sandbox,productionEnabled,serverWalletProjection;public CheckoutProduct86[] products;}
    public interface ICheckoutBackend86:IPayAuthority,IPayTerminalAuthority,IDisposable {
        void Catalog(Action<PayReply<CheckoutCatalog86>> done);
        void Create(string commandId,string productId,Action<PayReply<RuStoreServerOrder>> done);
        void Read(string orderId,Action<PayReply<RuStoreServerOrder>> done);
    }
    public interface ICheckoutRecovery100 {void Pending(long after,Action<PayReply<RuStorePendingOrders100>> done);}
    public sealed class CheckoutAccess86 {
        public readonly string Origin,Player;public readonly long Generation;public readonly ICheckoutBackend86 Backend;
        readonly Func<bool> current;public bool Current=>current();
        public CheckoutAccess86(string origin,string player,long generation,ICheckoutBackend86 backend,Func<bool> current){Origin=origin;Player=player;Generation=generation;Backend=backend;this.current=current;}
    }
    public sealed class CheckoutQuote86 {
        public readonly CheckoutProduct86 Product;public readonly string AmountLabel;
        public CheckoutQuote86(CheckoutProduct86 product,string label){Product=JsonUtility.FromJson<CheckoutProduct86>(JsonUtility.ToJson(product));Product.grant=CheckoutCatalogRules86.FrozenGrant(product.id,product.coins,product.grant).Copy();Product.policy=product.policy??new CommercePolicy100();AmountLabel=label;}
    }
    public static class CheckoutCatalogRules86 {
        // Keep the original coin-only list for the compact in-level coin shop.
        public static readonly string[] Ids={"coins-1000","coins-5000","coins-10000","coins-25000","coins-50000","coins-100000"};
        public static readonly int[] Coins={1000,5000,10000,25000,50000,100000};
        public static readonly string[] BundleIds={"wellkeeper","rainy-day","rainlight","village","festival","keepers"};
        static readonly int[] BundleCoins={2000,3500,6000,5000,10000,25000},BundleTools={1,2,3,2,4,8},BundleStarting={1,2,3,3,6,12};
        public static bool Known(string id)=>Ids.Contains(id)||BundleIds.Contains(id);
        public static RewardGrant ApprovedGrant(string id){
            int index=Array.IndexOf(Ids,id);if(index>=0)return new RewardGrant{coins=Coins[index]};
            index=Array.IndexOf(BundleIds,id);if(index<0)throw new InvalidOperationException("CheckoutUnknownProduct");
            return new RewardGrant{coins=BundleCoins[index],tools=Enumerable.Repeat(BundleTools[index],4).ToArray(),starting=Enumerable.Repeat(BundleStarting[index],4).ToArray()};
        }
        public static RewardGrant FrozenGrant(string id,int coins,RewardGrant grant){
            if(grant==null){if(!CommerceTerms100.LegacyCoin(id)||coins!=Coins[Array.IndexOf(Ids,id)])throw new InvalidOperationException("CheckoutFullGrantRequired");grant=new RewardGrant{coins=coins};}
            grant.Validate();if(grant.coins!=coins||grant.coins<=0||grant.stars!=0)throw new InvalidOperationException("CheckoutGrantInvalid");return grant;
        }
        public static bool ValidProduct(CheckoutProduct86 product,bool currentTerms=true){
            try{
                if(product==null||!Known(product.id)||product.quantity!=1||product.currency!="RUB"||product.amountMinor<=0||string.IsNullOrWhiteSpace(product.storeProductId)||product.storeProductId.Any(c=>char.IsWhiteSpace(c)||char.IsControl(c)))return false;
                var grant=FrozenGrant(product.id,product.coins,product.grant);if(currentTerms&&!CommerceTerms100.Same(grant,ApprovedGrant(product.id)))return false;
                int bundle=Array.IndexOf(BundleIds,product.id);var policy=product.policy;
                if(bundle>=0&&(policy==null||!policy.specified))return false;
                if(policy!=null&&policy.specified&&(policy.purchaseLimitPerPlayer!=0&&policy.purchaseLimitPerPlayer!=1||policy.repeatable!=(policy.purchaseLimitPerPlayer==0)||!new[]{"Available","Pending","Purchased","RefundReview"}.Contains(policy.eligibility)||policy.eligible!=(policy.eligibility=="Available")||!string.IsNullOrEmpty(policy.pendingOrderId)&&!PayRequest.Hex(policy.pendingOrderId)))return false;
                if(currentTerms&&policy!=null&&policy.specified&&(policy.purchaseLimitPerPlayer!=(bundle>=0&&bundle<3?1:0)||policy.repeatable!=(bundle<0||bundle>=3)))return false;
                return true;
            }catch{return false;}
        }
        public static CheckoutProduct86 FrozenProduct(RuStoreServerOrder order)=>new CheckoutProduct86{id=order.productId,storeProductId=order.sdk?.productId,coins=order.coins,grant=order.grant?.Copy(),policy=order.policy,currency=order.currency,amountMinor=order.amountMinor,quantity=order.sdk?.quantity??0};
        public static Dictionary<string,CheckoutQuote86> Match(CheckoutConfiguration86 config,CheckoutCatalog86 catalog,PayProduct[] sdk){
            if(!CheckoutConfiguration86.Valid(config)||catalog==null||!catalog.enabled||catalog.sandbox!=config.sandbox||catalog.productionEnabled!=config.productionEnabled||CommerceVerification125.Legacy(catalog.verificationMode)!=CommerceVerification125.Legacy(config.verificationMode)||catalog.appId!=config.consoleAppId||catalog.balanceScope!="server_wallet"||!catalog.serverWalletProjection||string.IsNullOrEmpty(catalog.version)||catalog.products==null||catalog.products.Length<1||catalog.products.Length>12||sdk==null||sdk.Length!=catalog.products.Length)throw new InvalidOperationException("CheckoutCatalogUnavailable");
            var result=new Dictionary<string,CheckoutQuote86>(StringComparer.Ordinal);var skus=new HashSet<string>(StringComparer.Ordinal);
            foreach(var product in catalog.products){if(!ValidProduct(product)||!skus.Add(product.storeProductId)||result.ContainsKey(product.id))throw new InvalidOperationException("CheckoutCatalogMismatch");
                var items=sdk.Where(p=>p!=null&&p.productId==product.storeProductId).ToArray();if(items.Length!=1)throw new InvalidOperationException("CheckoutSdkCatalogMismatch");var item=items[0];
                if(item.currency!="RUB"||item.amountMinor!=product.amountMinor||string.IsNullOrWhiteSpace(item.amountLabel)||item.amountLabel.Length>80||item.amountLabel.Any(char.IsControl))throw new InvalidOperationException("CheckoutSdkPriceMismatch");result.Add(product.id,new CheckoutQuote86(product,item.amountLabel));
            }return result;
        }
        // Recovery compares frozen order terms, never a newly priced/rebalanced catalog.
        public static bool Order(RuStoreServerOrder order,CheckoutQuote86 quote,string player,bool expectedProduction=false,string expectedVerificationMode=CommerceVerification125.ProviderApi){
            try{return order!=null&&CommerceVerification125.Legacy(order.verificationMode)==CommerceVerification125.Legacy(expectedVerificationMode)&&quote!=null&&ValidProduct(quote.Product,false)&&order.playerId==player&&order.productId==quote.Product.id&&order.coins==quote.Product.coins&&CommerceTerms100.Same(FrozenGrant(order.productId,order.coins,order.grant),FrozenGrant(quote.Product.id,quote.Product.coins,quote.Product.grant))&&order.amountMinor==quote.Product.amountMinor&&order.currency=="RUB"&&order.productionEnabled==expectedProduction&&order.sdk!=null&&order.sdk.productId==quote.Product.storeProductId&&order.sdk.appUserId==player&&order.sdk.quantity==1&&order.sdk.sandbox!=expectedProduction&&order.Request().Valid;}catch{return false;}
        }
    }
}

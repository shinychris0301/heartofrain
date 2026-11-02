using System;
using System.Collections.Generic;
using System.Linq;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.ShopCheckout86;

namespace HeartOfTheRain.App.RuStore {
    // Versioned, baked grant terms. Prices shown to the player still come from GetProducts.
    // Specials are visible in the provider catalogue but cannot be purchased
    // until their one-time entitlement and restoration policy is resolved.
    public sealed class DirectOffer {
        public readonly string id,sku,productType;public readonly int amountMinor;public readonly bool purchasable;public readonly RewardGrant grant;
        internal DirectOffer(string id,string sku,int amountMinor,string productType="CONSUMABLE_PRODUCT",bool purchasable=true){this.id=id;this.sku=sku;this.amountMinor=amountMinor;this.productType=productType;this.purchasable=purchasable;grant=CheckoutCatalogRules86.ApprovedGrant(id);}
        public bool Matches(PayProduct product)=>product!=null&&product.productId==sku&&
            (productType==null?product.productType=="CONSUMABLE_PRODUCT"||product.productType=="NON_CONSUMABLE_PRODUCT":product.productType==productType)&&
            product.currency=="RUB"&&product.amountMinor==amountMinor&&
            !string.IsNullOrWhiteSpace(product.amountLabel)&&product.amountLabel.Length<=80&&!product.amountLabel.Any(char.IsControl);
    }
    public static class DirectPurchaseCatalog {
        public static readonly DirectOffer[] Offers={
            new DirectOffer("coins-1000","hotr_coins_1000",9900),new DirectOffer("coins-5000","hotr_coins_5000",29900),
            new DirectOffer("coins-10000","hotr_coins_10000",49900),new DirectOffer("coins-25000","hotr_coins_25000",89900),
            new DirectOffer("coins-50000","hotr_coins_50000",159900),new DirectOffer("coins-100000","hotr_coins_100000",299900),
            new DirectOffer("wellkeeper","hotr_bundle_wellkeeper_c",9900,null,false),
            new DirectOffer("rainy-day","hotr_bundle_rainy_day",19900,null,false),
            new DirectOffer("rainlight","hotr_bundle_rainlight",29900,null,false),
            new DirectOffer("village","hotr_bundle_village",39900),new DirectOffer("festival","hotr_bundle_festival",59900),
            new DirectOffer("keepers","hotr_bundle_keepers",99900)
        };
        public static DirectOffer Find(string id)=>Offers.FirstOrDefault(o=>o.id==id);
    }
    public sealed class DirectPurchaseLedger {
        readonly ProfileService profile;public DirectPurchaseLedger(ProfileService profile){this.profile=profile??throw new ArgumentNullException(nameof(profile));}
        public PlayerProfile Read()=>profile.Read();
        static bool Active(DirectPurchaseIntent i)=>i.phase=="Intent"||i.phase=="Dispatched"||i.phase=="OutcomeUnknown"||i.phase=="Confirmed";
        public DirectPurchaseIntent Pending()=>Read().directPurchaseIntents.FirstOrDefault(Active);
        public DirectPurchaseIntent Begin(DirectOffer offer,bool sandbox){
            if(offer==null)throw new ArgumentNullException(nameof(offer));
            if(!offer.purchasable||offer.productType!="CONSUMABLE_PRODUCT")throw new InvalidOperationException("OneTimePurchaseNotEnabled");
            return profile.Change(p=>{
                if(p.directPurchaseIntents.Any(Active))throw new InvalidOperationException("DirectPurchasePending");
                var order=Guid.NewGuid().ToString("N");var command=Guid.NewGuid().ToString("N");
                var intent=new DirectPurchaseIntent{orderId=order,commandId=command,productId=offer.id,storeProductId=offer.sku,
                    developerPayload="hotr-order-v1:"+order+":"+command,amountMinor=offer.amountMinor,sandbox=sandbox,phase="Intent"};
                p.directPurchaseIntents.Add(intent);return intent;
            });
        }
        public DirectPurchaseIntent MarkDispatched(string order){return profile.Change(p=>{
            var i=p.directPurchaseIntents.Single(v=>v.orderId==order);
            if(i.phase!="Intent")throw new InvalidOperationException("PurchaseCannotDispatchAgain");i.phase="Dispatched";return i;
        });}
        public void AbortUnsent(string order){profile.Change(p=>{
            var i=p.directPurchaseIntents.Single(v=>v.orderId==order);
            if(i.phase!="Intent"||!string.IsNullOrEmpty(i.purchaseId))throw new InvalidOperationException("PurchaseMayHaveBeenSent");
            i.phase="Terminal";return true;
        });}
        public void MarkUnknown(string order,string purchaseId=null){profile.Change(p=>{
            var i=p.directPurchaseIntents.Single(v=>v.orderId==order);
            if(i.phase!="Dispatched"&&i.phase!="OutcomeUnknown")throw new InvalidOperationException("PurchaseStateChanged");
            if(purchaseId!=null){if(!Guid.TryParse(purchaseId,out var id))throw new InvalidOperationException("InvalidPurchaseId");i.purchaseId=id.ToString("D");}
            i.phase="OutcomeUnknown";return true;
        });}
        public bool Credit(string order,PayPurchase observed){return profile.Change(p=>{
            var i=p.directPurchaseIntents.Single(v=>v.orderId==order);var offer=DirectPurchaseCatalog.Find(i.productId);
            if(offer==null||!offer.purchasable||offer.productType!="CONSUMABLE_PRODUCT"||offer.sku!=i.storeProductId||offer.amountMinor!=i.amountMinor)throw new InvalidOperationException("FrozenPurchaseTermsMismatch");
            var request=Request(p.playerId,i);if(!Confirmed(request,observed,offer))throw new InvalidOperationException("PurchaseNotConfirmed");
            var id=observed.locator.purchaseId;
            var prior=p.directPurchaseReceipts.FirstOrDefault(r=>r.purchaseId==id);
            if(prior!=null){if(prior.orderId!=order||prior.productId!=i.productId)throw new InvalidOperationException("ReceiptReused");return false;}
            if(i.phase!="Dispatched"&&i.phase!="OutcomeUnknown"&&i.phase!="Confirmed")throw new InvalidOperationException("PurchaseNotPending");
            if(!string.IsNullOrEmpty(i.purchaseId)&&i.purchaseId!=id)throw new InvalidOperationException("PurchaseLocatorChanged");
            if(!ProfileService.ApplyGrant(p,"rustore:"+id,"rustore-direct",offer.grant))throw new InvalidOperationException("ReceiptGrantConflict");
            i.purchaseId=id;i.invoiceId=observed.locator.invoiceId;i.phase="Confirmed";
            p.directPurchaseReceipts.Add(new DirectPurchaseReceipt{purchaseId=id,invoiceId=i.invoiceId,orderId=order,productId=i.productId,storeProductId=i.storeProductId,
                amountMinor=i.amountMinor,sandbox=i.sandbox,phase="Credited"});return true;
        });}
        public void MarkAcknowledged(string order){profile.Change(p=>{
            var i=p.directPurchaseIntents.Single(v=>v.orderId==order);
            var r=p.directPurchaseReceipts.Single(v=>v.orderId==order&&v.purchaseId==i.purchaseId);
            if(i.phase!="Confirmed"&&i.phase!="Acknowledged")throw new InvalidOperationException("NoDurableGrant");
            i.phase="Acknowledged";r.phase="Acknowledged";return true;
        });}
        public void MarkTerminal(string order,PayPurchase observed){profile.Change(p=>{
            var i=p.directPurchaseIntents.Single(v=>v.orderId==order);
            if(i.phase=="Confirmed"||i.phase=="Acknowledged")throw new InvalidOperationException("CreditedPurchaseCannotClose");
            if(!new[]{"CANCELLED","REJECTED","EXPIRED"}.Contains(observed?.status)||!observed.Matches(Request(p.playerId,i))||
                !string.IsNullOrEmpty(i.purchaseId)&&i.purchaseId!=observed.locator.purchaseId)throw new InvalidOperationException("TerminalNotBound");
            i.purchaseId=observed.locator.purchaseId;i.invoiceId=observed.locator.invoiceId;i.phase="Terminal";return true;
        });}
        public void MarkRefundReview(string purchaseId){profile.Change(p=>{
            var r=p.directPurchaseReceipts.Single(v=>v.purchaseId==purchaseId);
            var i=p.directPurchaseIntents.Single(v=>v.orderId==r.orderId);
            r.phase="RefundReview";i.phase="RefundReview";return true;
        });}
        public static PayRequest Request(string player,DirectPurchaseIntent i)=>new PayRequest(i.orderId,i.storeProductId,player,i.developerPayload,1,i.sandbox);
        public static bool Confirmed(PayRequest request,PayPurchase purchase,DirectOffer offer)=>request!=null&&request.Valid&&offer!=null&&offer.purchasable&&offer.productType=="CONSUMABLE_PRODUCT"&&
            purchase!=null&&purchase.Matches(request)&&purchase.status=="CONFIRMED"&&purchase.purchaseType=="ONE_STEP"&&
            purchase.currency=="RUB"&&purchase.amountMinor==offer.amountMinor&&purchase.locator?.productId==offer.sku;
    }
}

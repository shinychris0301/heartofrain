using System;
using System.Collections.Generic;
using System.Linq;
using HeartOfTheRain.App.Profile;

namespace HeartOfTheRain.App.RuStore {
    // SDK callbacks are observations. Only the local profile transaction can
    // turn a confirmed observation into spendable currency and inventory.
    public sealed class DirectPurchaseCoordinator {
        readonly DirectPurchaseLedger ledger;readonly IDirectPurchaseStore store;readonly string player;readonly bool sandbox;
        readonly Dictionary<string,string> prices=new Dictionary<string,string>(StringComparer.Ordinal);
        public bool Busy{get;private set;}public string Error{get;private set;}public bool Credited{get;private set;}
        public string Price(string offer)=>prices.TryGetValue(offer,out var price)?price:null;
        public string PendingProduct=>ledger.Pending()?.productId;
        public bool CanBuy(string offer)=>!Busy&&PendingProduct==null&&DirectPurchaseCatalog.Find(offer)?.purchasable==true&&prices.ContainsKey(offer);
        public DirectPurchaseCoordinator(DirectPurchaseLedger ledger,IDirectPurchaseStore store,bool sandbox){
            this.ledger=ledger??throw new ArgumentNullException(nameof(ledger));this.store=store??throw new ArgumentNullException(nameof(store));this.sandbox=sandbox;
            player=ledger.Read().playerId;
        }
        static Action<PayReply<T>> Once<T>(Action<PayReply<T>> callback) where T:class {bool called=false;return value=>{if(called)return;called=true;callback(value);};}
        void End(Action<bool,string> done,bool ok,string error=null){Busy=false;Error=error;done(ok,error);}
        public void Refresh(Action<bool,string> done){
            if(Busy){done(false,"PurchaseBusy");return;}Busy=true;Error=null;Credited=false;prices.Clear();
            if(!store.Configured||!store.SdkCompiled){End(done,false,"RuStoreUnavailable");return;}
            store.GetPurchaseAvailability(Once<PayAvailability>(available=>{
                if(!available.Succeeded||!available.value.available){End(done,false,available.error?.code??"RuStoreUnavailable");return;}
                store.GetProducts(DirectPurchaseCatalog.Offers.Select(o=>o.sku).ToArray(),Once<PayProduct[]>(result=>{
                    if(!result.Succeeded){End(done,false,result.error?.code??"ProductReadFailed");return;}
                    var found=result.value??new PayProduct[0];var unique=new HashSet<string>(StringComparer.Ordinal);
                    foreach(var item in found){
                        var offer=DirectPurchaseCatalog.Offers.FirstOrDefault(o=>o.sku==item?.productId);
                        if(offer==null||!unique.Add(item.productId)){prices.Clear();End(done,false,"ProductCatalogMismatch");return;}
                        if(offer.Matches(item))prices.Add(offer.id,item.amountLabel);
                    }
                    End(done,true);
                }));
            }));
        }
        public void Buy(string offerId,Action<bool,string> done){
            if(Busy||!CanBuy(offerId)){done(false,"PurchaseUnavailable");return;}
            var offer=DirectPurchaseCatalog.Find(offerId);if(offer==null){done(false,"UnknownOffer");return;}
            Busy=true;Credited=false;Error=null;
            // The Shop may have been open for minutes. A fresh SDK quote must
            // still match the baked terms at the exact Buy decision.
            store.GetProducts(new[]{offer.sku},Once<PayProduct[]>(quote=>{
                if(!quote.Succeeded||quote.value.Length!=1||!offer.Matches(quote.value[0])){End(done,false,"ProductPriceChanged");return;}
                DispatchPurchase(offer,done);
            }));
        }
        void DispatchPurchase(DirectOffer offer,Action<bool,string> done){
            DirectPurchaseIntent intent;
            try{intent=ledger.Begin(offer,sandbox);ledger.MarkDispatched(intent.orderId);}
            catch(Exception){End(done,false,"PurchaseJournalUnavailable");return;}
            PayRequest request=DirectPurchaseLedger.Request(player,intent);
            store.PurchaseDirect(request,Once<PayLocator>(result=>{
                try{ledger.MarkUnknown(intent.orderId,result.Succeeded?result.value.purchaseId:result.error?.recoveryPurchaseId);}
                catch(Exception){End(done,false,"PurchaseJournalUnavailable");return;}
                if(!result.Succeeded||!result.value.Matches(request)){End(done,false,result.error?.code??"PurchaseOutcomeUnknown");return;}
                Lookup(intent,done);
            }));
        }
        public void Recover(Action<bool,string> done){
            if(Busy){done(false,"PurchaseBusy");return;}Busy=true;Credited=false;Error=null;
            var intent=ledger.Pending();if(intent==null){End(done,true);return;}
            if(intent.phase=="Intent"){
                try{ledger.AbortUnsent(intent.orderId);End(done,true);}catch(Exception){End(done,false,"PurchaseJournalUnavailable");}
                return;
            }
            if(!string.IsNullOrEmpty(intent.purchaseId)){Lookup(intent,done);return;}
            store.GetPurchases(Once<PayPurchase[]>(result=>{
                if(!result.Succeeded){End(done,false,result.error?.code??"PurchaseRecoveryUnavailable");return;}
                var request=DirectPurchaseLedger.Request(player,intent);
                var matches=(result.value??new PayPurchase[0]).Where(p=>p!=null&&p.Matches(request)).ToArray();
                if(matches.Length!=1){End(done,false,matches.Length==0?"PurchaseOutcomeUnknown":"AmbiguousPurchaseRecovery");return;}
                try{ledger.MarkUnknown(intent.orderId,matches[0].locator.purchaseId);}catch(Exception){End(done,false,"PurchaseJournalUnavailable");return;}
                Lookup(intent,done);
            }));
        }
        void Lookup(DirectPurchaseIntent intent,Action<bool,string> done){
            var current=ledger.Read().directPurchaseIntents.Single(i=>i.orderId==intent.orderId);
            if(string.IsNullOrEmpty(current.purchaseId)){End(done,false,"PurchaseOutcomeUnknown");return;}
            store.GetPurchase(current.purchaseId,Once<PayPurchase>(result=>{
                if(!result.Succeeded){End(done,false,result.error?.code??"PurchaseLookupUnavailable");return;}
                var observed=result.value;var request=DirectPurchaseLedger.Request(player,current);
                if(!observed.Matches(request)||observed.locator.purchaseId!=current.purchaseId){End(done,false,"PurchaseCorrelationMismatch");return;}
                if(observed.status=="REFUNDED"||observed.status=="REVERSED"){
                    try{if(ledger.Read().directPurchaseReceipts.Any(r=>r.purchaseId==current.purchaseId))ledger.MarkRefundReview(current.purchaseId);}
                    catch(Exception){End(done,false,"RefundJournalUnavailable");return;}
                    End(done,false,"RefundReview");return;
                }
                if(new[]{"CANCELLED","REJECTED","EXPIRED"}.Contains(observed.status)){
                    try{ledger.MarkTerminal(current.orderId,observed);}catch(Exception){End(done,false,"TerminalJournalUnavailable");return;}
                    End(done,false,"PurchaseNotCompleted");return;
                }
                var offer=DirectPurchaseCatalog.Find(current.productId);
                if(!DirectPurchaseLedger.Confirmed(request,observed,offer)){End(done,false,observed.status=="PAID"?"PaymentHeld":"PurchaseNotConfirmed");return;}
                try{Credited=ledger.Credit(current.orderId,observed)||ledger.Read().directPurchaseReceipts.Any(r=>r.orderId==current.orderId);}
                catch(Exception){End(done,false,"PurchaseGrantUnavailable");return;}
                var receipt=ledger.Read().directPurchaseReceipts.Single(r=>r.orderId==current.orderId&&r.purchaseId==current.purchaseId);
                store.AcknowledgeDirect(request,observed,receipt,Once<PayAvailability>(ack=>{
                    if(!ack.Succeeded||!ack.value.available){End(done,false,ack.error?.code??"AcknowledgementPending");return;}
                    try{ledger.MarkAcknowledged(current.orderId);}catch(Exception){End(done,false,"AcknowledgementJournalUnavailable");return;}
                    End(done,true);
                }));
            }));
        }
    }
}

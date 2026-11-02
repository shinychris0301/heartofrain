using System;
using System.Linq;
using System.Text.RegularExpressions;
using HeartOfTheRain.App.Profile;

namespace HeartOfTheRain.App.RuStore {
    // Transport observations never authorize a local wallet mutation.
    public sealed class PayFailure {
        public readonly string code,recoveryPurchaseId;public readonly bool outcomeUnknown;
        public PayFailure(string code,bool outcomeUnknown=false,string recoveryPurchaseId=null){this.code=code??"Unknown";this.outcomeUnknown=outcomeUnknown;this.recoveryPurchaseId=PayPending.CanonicalPurchaseId(recoveryPurchaseId);}
    }
    public sealed class PayReply<T> where T:class {
        public readonly T value;public readonly PayFailure error;public bool Succeeded=>error==null&&value!=null;
        PayReply(T value,PayFailure error){this.value=value;this.error=error;}
        public static PayReply<T> Ok(T value)=>new PayReply<T>(value??throw new ArgumentNullException(nameof(value)),null);
        public static PayReply<T> Fail(string code,bool unknown=false,string recoveryPurchaseId=null)=>new PayReply<T>(null,new PayFailure(code,unknown,recoveryPurchaseId));
    }
    public sealed class PayAvailability {public readonly bool available;public PayAvailability(bool available){this.available=available;}}
    public sealed class PayProduct {
        public readonly string productId,amountLabel,currency,productType;public readonly long? amountMinor;
        public PayProduct(string productId,string amountLabel,string currency,long? amountMinor,string productType="CONSUMABLE_PRODUCT"){this.productId=productId;this.amountLabel=amountLabel;this.currency=currency;this.amountMinor=amountMinor;this.productType=productType;}
    }
    public sealed class PayRequest {
        public readonly string orderId,productId,appUserId,developerPayload;public readonly int quantity;public readonly bool sandbox;
        public PayRequest(string orderId,string productId,string appUserId,string developerPayload,int quantity,bool sandbox){this.orderId=orderId;this.productId=productId;this.appUserId=appUserId;this.developerPayload=developerPayload;this.quantity=quantity;this.sandbox=sandbox;}
        public bool Valid=>Hex(orderId)&&Hex(appUserId)&&!string.IsNullOrWhiteSpace(productId)&&productId.Length<=255&&!productId.Any(c=>char.IsControl(c)||char.IsWhiteSpace(c))&&quantity==1
            &&developerPayload!=null&&Regex.IsMatch(developerPayload,@"\Ahotr-order-v1:"+Regex.Escape(orderId??"")+@":([0-9a-f]{32})\z");
        public bool SameOrder(PayRequest other)=>other!=null&&orderId==other.orderId&&productId==other.productId&&appUserId==other.appUserId&&developerPayload==other.developerPayload&&quantity==other.quantity&&sandbox==other.sandbox;
        internal static bool Hex(string value)=>value!=null&&Regex.IsMatch(value,@"\A[0-9a-f]{32}\z");
    }
    public sealed class PayLocator {
        public readonly string purchaseId,invoiceId,orderId,productId;public readonly int quantity;public readonly bool sandbox;
        public PayLocator(string purchaseId,string invoiceId,string orderId,string productId,int quantity,bool sandbox){this.purchaseId=purchaseId;this.invoiceId=invoiceId;this.orderId=orderId;this.productId=productId;this.quantity=quantity;this.sandbox=sandbox;}
        public bool Matches(PayRequest request)=>request!=null&&request.Valid&&orderId==request.orderId&&productId==request.productId&&quantity==request.quantity&&sandbox==request.sandbox&&!string.IsNullOrWhiteSpace(purchaseId)&&invoiceId!=null&&Regex.IsMatch(invoiceId,@"\A[1-9][0-9]{0,29}\z");
    }
    public sealed class PayPurchase {
        public readonly PayLocator locator;public readonly string developerPayload,status,purchaseType,acknowledgementState,productType,currency;public readonly long? amountMinor;
        public PayPurchase(PayLocator locator,string developerPayload,string status,string purchaseType,string acknowledgementState,string productType="CONSUMABLE_PRODUCT",long? amountMinor=null,string currency=null){this.locator=locator;this.developerPayload=developerPayload;this.status=status;this.purchaseType=purchaseType;this.acknowledgementState=acknowledgementState;this.productType=productType;this.amountMinor=amountMinor;this.currency=currency;}
        public bool Matches(PayRequest request)=>locator!=null&&locator.Matches(request)&&developerPayload==request.developerPayload&&productType=="CONSUMABLE_PRODUCT";
    }
    // Only the authenticated authoritative service may supply this decision.
    // The SDK result itself is not a receipt. Server-only/nonspendable credit
    // is insufficient to acknowledge delivery of player currency.
    public sealed class PayDeliveryReceipt {
        public readonly string orderId,productId,appUserId,purchaseId,invoiceId,receiptId;public readonly bool sandbox,durable,availableToSpend;
        public PayDeliveryReceipt(string orderId,string productId,string appUserId,string purchaseId,string invoiceId,string receiptId,bool sandbox,bool durable,bool availableToSpend){this.orderId=orderId;this.productId=productId;this.appUserId=appUserId;this.purchaseId=purchaseId;this.invoiceId=invoiceId;this.receiptId=receiptId;this.sandbox=sandbox;this.durable=durable;this.availableToSpend=availableToSpend;}
        public bool MatchesLocator(PayRequest request,PayLocator locator)=>durable&&availableToSpend&&!string.IsNullOrWhiteSpace(receiptId)&&request!=null&&locator!=null&&locator.Matches(request)
            &&orderId==request.orderId&&productId==request.productId&&appUserId==request.appUserId&&sandbox==request.sandbox&&purchaseId==locator.purchaseId&&invoiceId==locator.invoiceId;
        public bool Matches(PayRequest request,PayPurchase purchase)=>purchase!=null&&purchase.Matches(request)&&purchase.status=="CONFIRMED"&&MatchesLocator(request,purchase.locator);
    }
    public sealed class PayCaptureAuthorization {
        public readonly string orderId,purchaseId,invoiceId;public readonly bool authorized;
        public PayCaptureAuthorization(string orderId,string purchaseId,string invoiceId,bool authorized){this.orderId=orderId;this.purchaseId=purchaseId;this.invoiceId=invoiceId;this.authorized=authorized;}
        public bool Matches(PayRequest request,PayPurchase purchase)=>authorized&&purchase!=null&&purchase.Matches(request)&&purchase.status=="PAID"&&purchase.purchaseType=="TWO_STEP"&&orderId==request.orderId&&purchaseId==purchase.locator.purchaseId&&invoiceId==purchase.locator.invoiceId;
    }
    // A no-delivery decision comes only from the authenticated server's fresh
    // bound payment reconciliation. SDK cancellation text and an empty list are not
    // terminal evidence. Refund review is intentionally not a closed state.
    public sealed class PayTerminalReceipt {
        public readonly string orderId,productId,appUserId,purchaseId,invoiceId,state;
        public readonly bool sandbox,durable,noCredit;
        public PayTerminalReceipt(string orderId,string productId,string appUserId,string purchaseId,string invoiceId,string state,bool sandbox,bool durable,bool noCredit){this.orderId=orderId;this.productId=productId;this.appUserId=appUserId;this.purchaseId=purchaseId;this.invoiceId=invoiceId;this.state=state;this.sandbox=sandbox;this.durable=durable;this.noCredit=noCredit;}
        public static string StateFor(string sdkStatus){switch(sdkStatus){case "CANCELLED":return "Cancelled";case "REJECTED":return "Rejected";case "EXPIRED":return "Expired";default:return null;}}
        public bool Matches(PayRequest request,PayLocator locator)=>durable&&noCredit&&new[]{"Cancelled","Rejected","Expired"}.Contains(state)&&request!=null&&locator!=null&&locator.Matches(request)&&orderId==request.orderId&&productId==request.productId&&appUserId==request.appUserId&&sandbox==request.sandbox&&purchaseId==locator.purchaseId&&invoiceId==locator.invoiceId;
    }
    public interface IPayTerminalAuthority {
        void ResolveTerminal(PayRequest request,PayPurchase observed,Action<PayReply<PayTerminalReceipt>> done);
    }
    public interface IPayStore {
        bool SdkCompiled{get;}bool Configured{get;}
        void GetPurchaseAvailability(Action<PayReply<PayAvailability>> done);
        void GetProducts(string[] productIds,Action<PayReply<PayProduct[]>> done);
        void Purchase(PayRequest request,Action<PayReply<PayLocator>> done);
        void GetPurchase(string purchaseId,Action<PayReply<PayPurchase>> done);
        void GetPurchases(Action<PayReply<PayPurchase[]>> done);
        void ConfirmTwoStep(PayRequest request,PayPurchase purchase,PayCaptureAuthorization authorization,Action<PayReply<PayAvailability>> done);
        void Acknowledge(PayRequest request,PayPurchase purchase,PayDeliveryReceipt receipt,Action<PayReply<PayAvailability>> done);
    }
    public interface IDirectPurchaseStore {
        bool SdkCompiled{get;}bool Configured{get;}
        void GetPurchaseAvailability(Action<PayReply<PayAvailability>> done);
        void GetProducts(string[] productIds,Action<PayReply<PayProduct[]>> done);
        void PurchaseDirect(PayRequest request,Action<PayReply<PayLocator>> done);
        void GetPurchase(string purchaseId,Action<PayReply<PayPurchase>> done);
        void GetPurchases(Action<PayReply<PayPurchase[]>> done);
        void AcknowledgeDirect(PayRequest request,PayPurchase purchase,DirectPurchaseReceipt receipt,Action<PayReply<PayAvailability>> done);
    }
    public interface IPayAuthority {
        bool WalletReady{get;}
        void Reconcile(PayRequest request,PayPurchase observed,Action<PayReply<PayDeliveryReceipt>> done);
    }
    public sealed class UnavailablePayAuthority:IPayAuthority {
        public bool WalletReady=>false;
        public void Reconcile(PayRequest request,PayPurchase observed,Action<PayReply<PayDeliveryReceipt>> done)=>done(PayReply<PayDeliveryReceipt>.Fail("AuthoritativeWalletUnavailable"));
    }
    public sealed class PayPending {
        public readonly PayRequest request;public readonly PayLocator locator;public readonly string phase,recoveryPurchaseId;public readonly PayDeliveryReceipt receipt;public readonly PayTerminalReceipt terminal;
        public PayPending(PayRequest request,string phase,PayLocator locator=null,PayDeliveryReceipt receipt=null,string recoveryPurchaseId=null,PayTerminalReceipt terminal=null){this.request=request;this.phase=phase;this.locator=locator;this.receipt=receipt;this.recoveryPurchaseId=recoveryPurchaseId;this.terminal=terminal;}
        internal static string CanonicalPurchaseId(string value){Guid id;return value!=null&&Guid.TryParse(value,out id)?id.ToString("D"):null;}
        public bool Valid {
            get {
                if(request==null||!request.Valid||recoveryPurchaseId!=null&&(CanonicalPurchaseId(recoveryPurchaseId)!=recoveryPurchaseId||phase!="OutcomeUnknown"))return false;
                switch(phase){
                    case "AwaitingPayment":case "OutcomeUnknown":return locator==null&&receipt==null&&terminal==null;
                    case "AwaitingRecovery":case "AwaitingAuthority":return locator!=null&&locator.Matches(request)&&receipt==null&&terminal==null;
                    case "AcknowledgementPending":case "Acknowledged":return locator!=null&&receipt!=null&&receipt.MatchesLocator(request,locator)&&terminal==null;
                    case "ResolvedWithoutDelivery":return locator!=null&&receipt==null&&terminal!=null&&terminal.Matches(request,locator);
                    default:return false;
                }
            }
        }
    }
    public interface IPayJournal {
        PayPending Load();
        // Must return true only after durable atomic persistence. No SDK call
        // may begin if saving the server-provided correlation fails.
        bool TrySave(PayPending pending,out string error);
    }
}

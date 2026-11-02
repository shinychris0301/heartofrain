using System;
using System.Text;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.RuStore;
using UnityEngine;

namespace HeartOfTheRain.App.ShopCheckout86 {
    [Serializable] public sealed class CheckoutPayment86 {
        public string phase="",purchaseId="",invoiceId="",recoveryPurchaseId="",receiptId="",terminalState="";
        public bool hasLocator,hasReceipt,hasTerminal;
        public PayPending Pending(PayRequest request){
            var locator=hasLocator?new PayLocator(purchaseId,invoiceId,request.orderId,request.productId,request.quantity,request.sandbox):null;
            var receipt=hasReceipt?new PayDeliveryReceipt(request.orderId,request.productId,request.appUserId,purchaseId,invoiceId,receiptId,request.sandbox,true,true):null;
            var terminal=hasTerminal?new PayTerminalReceipt(request.orderId,request.productId,request.appUserId,purchaseId,invoiceId,terminalState,request.sandbox,true,true):null;
            return new PayPending(request,phase,locator,receipt,string.IsNullOrEmpty(recoveryPurchaseId)?null:recoveryPurchaseId,terminal);
        }
        public static CheckoutPayment86 From(PayPending value)=>new CheckoutPayment86{phase=value.phase,hasLocator=value.locator!=null,purchaseId=value.locator?.purchaseId??"",invoiceId=value.locator?.invoiceId??"",recoveryPurchaseId=value.recoveryPurchaseId??"",hasReceipt=value.receipt!=null,receiptId=value.receipt?.receiptId??"",hasTerminal=value.terminal!=null,terminalState=value.terminal?.state??""};
    }
    [Serializable] public sealed class CheckoutDocument86 {
        public string verificationMode=CommerceVerification125.ProviderApi;
        public int version=1;public long revision;public string origin,player,phase="",commandId="",productId="",amountLabel="";
        public bool hasOrder,hasPayment;public CheckoutProduct86 product=new CheckoutProduct86();public RuStoreServerOrder order=new RuStoreServerOrder();public CheckoutPayment86 payment=new CheckoutPayment86();
        public bool Pending=>phase!=""&&phase!="Settled";
    }
    // All bytes go to the existing encrypted CAS store. This outbox contains
    // immutable correlation, never access/refresh/recovery tokens or wallet truth.
    public sealed class ProtectedCheckoutJournal86:IPayJournal,IDisposable {
        readonly IProtectedSessionStore82 store;readonly bool expectedProduction;readonly string origin,player,expectedVerificationMode;string digest="";bool observed;
        static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
        public ProtectedCheckoutJournal86(IProtectedSessionStore82 store,string origin,string player,bool expectedProduction=false,string expectedVerificationMode=CommerceVerification125.ProviderApi){this.expectedVerificationMode=CommerceVerification125.Legacy(expectedVerificationMode);this.expectedProduction=expectedProduction;this.store=store??throw new ArgumentNullException(nameof(store));this.origin=origin;this.player=player;Uri uri;if(!IdentityProtocol82.Id(player)||!Uri.TryCreate(origin,UriKind.Absolute,out uri)||uri.GetLeftPart(UriPartial.Authority)!=origin||uri.UserInfo!=""||uri.Scheme!="https"&&!(uri.Scheme=="http"&&uri.IsLoopback))throw new ArgumentException("CheckoutOwnerInvalid");}
        void Validate(CheckoutDocument86 value){
            if(value==null||CommerceVerification125.Legacy(value.verificationMode)!=expectedVerificationMode||value.version!=1||value.revision<0||value.origin!=origin||value.player!=player||value.phase!=""&&value.phase!="Creating"&&value.phase!="Ordered"&&value.phase!="Settled")throw new InvalidOperationException("CheckoutJournalInvalid");
            if(value.phase==""){if(value.hasOrder||value.hasPayment||value.commandId!="")throw new InvalidOperationException("CheckoutJournalInitialInvalid");return;}

            if(!IdentityProtocol82.Id(value.commandId)||!CheckoutCatalogRules86.ValidProduct(value.product,false)||value.product.id!=value.productId||string.IsNullOrEmpty(value.amountLabel)||value.amountLabel.Length>80)throw new InvalidOperationException("CheckoutJournalIntentInvalid");
            if(value.phase=="Creating"){if(value.hasOrder||value.hasPayment)throw new InvalidOperationException("CheckoutJournalCreatingInvalid");return;}
            if(!value.hasOrder||!CheckoutCatalogRules86.Order(value.order,new CheckoutQuote86(value.product,value.amountLabel),player,expectedProduction,expectedVerificationMode))throw new InvalidOperationException("CheckoutJournalOrderInvalid");
            if(value.hasPayment&&(value.payment==null||!value.payment.Pending(value.order.Request()).Valid))throw new InvalidOperationException("CheckoutJournalPaymentInvalid");
            if(value.phase=="Settled"&&(!value.hasPayment||value.payment.phase!="Acknowledged"&&value.payment.phase!="ResolvedWithoutDelivery"))throw new InvalidOperationException("CheckoutJournalSettlementInvalid");
        }
        // Exact old serialized shapes retain the version1 encrypted journal.
        // Additive fields do not make a previously canonical paid order corrupt.
        [Serializable] sealed class LegacyDocument122 {
            public int version=1;public long revision=0;public string origin=null,player=null,phase="",commandId="",productId="",amountLabel="";
            public bool hasOrder=false,hasPayment=false;public CheckoutProduct86 product=new CheckoutProduct86();public RuStoreServerOrder order=new RuStoreServerOrder();public CheckoutPayment86 payment=new CheckoutPayment86();
        }
        static bool LegacyCanonical122(string json){try{return JsonUtility.ToJson(JsonUtility.FromJson<LegacyDocument122>(json))==json;}catch{return false;}}
        static void RestoreModes(CheckoutDocument86 value){if(value.order==null)return;value.order.verificationMode=value.verificationMode;if(value.order.credit!=null)value.order.credit.verificationMode=value.verificationMode;}
        [Serializable] sealed class LegacyProduct100 {public string id=null,storeProductId=null,currency=null;public int coins=0,amountMinor=0,quantity=0;}
        [Serializable] sealed class LegacyCredit100 {public string receiptId=null,balanceScope=null;public int coins=0;public long createdAt=0;}
        [Serializable] sealed class LegacyOrder100 {
            public string orderId=null,playerId=null,state=null,catalogVersion=null,productId=null,currency=null,invoiceId=null,purchaseId=null,deliveryAcknowledgement=null,balanceScope=null;
            public int coins=0,amountMinor=0;public bool productionEnabled=false,availableToSpend=false,availableInServerWallet=false,normalUnityProfileIntegrated=false,localProfileMutated=false;
            public RuStoreServerSdkOrder sdk=null;public LegacyCredit100 credit=null;
        }
        [Serializable] sealed class LegacyDocument100 {
            public int version=1;public long revision=0;public string origin=null,player=null,phase="",commandId="",productId="",amountLabel="";
            public bool hasOrder=false,hasPayment=false;public LegacyProduct100 product=new LegacyProduct100();public LegacyOrder100 order=new LegacyOrder100();public CheckoutPayment86 payment=new CheckoutPayment86();
        }
        static bool LegacyCanonical(string json){try{return JsonUtility.ToJson(JsonUtility.FromJson<LegacyDocument100>(json))==json;}catch{return false;}}
        static void CompleteLegacy(CheckoutDocument86 value){
            if(value.phase=="")return;
            if(value.product!=null&&CommerceTerms100.LegacyCoin(value.product.id)){
                value.product.grant=CheckoutCatalogRules86.FrozenGrant(value.product.id,value.product.coins,null).Copy();value.product.policy=new CommercePolicy100();
            }
            if(value.hasOrder&&value.order!=null&&CommerceTerms100.LegacyCoin(value.order.productId)){
                value.order.grant=CheckoutCatalogRules86.FrozenGrant(value.order.productId,value.order.coins,null).Copy();value.order.policy=new CommercePolicy100();
                if(value.order.credit!=null&&value.order.credit.coins>0)value.order.credit.grant=new HeartOfTheRain.App.Profile.RewardGrant{coins=value.order.credit.coins};
            }
        }
        static void CompleteNullLegacy(CheckoutDocument86 value){
            if(value.phase=="")return;
            if(value.product!=null&&value.product.policy==null&&CommerceTerms100.LegacyCoin(value.product.id))value.product.policy=new CommercePolicy100();
            if(value.hasOrder&&value.order!=null&&value.order.policy==null&&CommerceTerms100.LegacyCoin(value.order.productId))value.order.policy=new CommercePolicy100();
            if(value.product?.grant==null&&CommerceTerms100.LegacyCoin(value.product?.id))value.product.grant=CheckoutCatalogRules86.FrozenGrant(value.product.id,value.product.coins,null).Copy();
            if(value.hasOrder&&value.order?.grant==null&&CommerceTerms100.LegacyCoin(value.order?.productId))value.order.grant=CheckoutCatalogRules86.FrozenGrant(value.order.productId,value.order.coins,null).Copy();
        }
        public CheckoutDocument86 Read(){
            byte[] bytes=store.Read();if(bytes==null){if(observed)throw new InvalidOperationException("CheckoutObservedJournalMissing");digest="";return new CheckoutDocument86{verificationMode=expectedVerificationMode,origin=origin,player=player};}
            if(bytes.Length<2||bytes.Length>32768)throw new InvalidOperationException("CheckoutJournalSizeInvalid");string json=Utf8.GetString(bytes);var value=JsonUtility.FromJson<CheckoutDocument86>(json);
            if(JsonUtility.ToJson(value)!=json){
                if(LegacyCanonical122(json))value.verificationMode=CommerceVerification125.ProviderApi;
                else if(LegacyCanonical(json)){value.verificationMode=CommerceVerification125.ProviderApi;CompleteLegacy(value);}
                else throw new InvalidOperationException("CheckoutJournalCanonicalRequired");
            }
            RestoreModes(value);Validate(value);
            observed=true;digest=IdentityProtocol82.Sha(bytes);return value;
        }
        public CheckoutDocument86 Save(CheckoutDocument86 value){
            CompleteNullLegacy(value);Validate(value);var next=JsonUtility.FromJson<CheckoutDocument86>(JsonUtility.ToJson(value));next.revision=checked(value.revision+1);byte[] bytes=Utf8.GetBytes(JsonUtility.ToJson(next));if(bytes.Length>32768)throw new InvalidOperationException("CheckoutJournalSizeInvalid");
            store.CompareExchange(digest,bytes);var actual=Read();if(actual.revision!=next.revision||JsonUtility.ToJson(actual)!=JsonUtility.ToJson(next))throw new InvalidOperationException("CheckoutJournalWriteUnconfirmed");return actual;
        }
        public PayPending Load(){var value=Read();return value.hasPayment?value.payment.Pending(value.order.Request()):null;}
        public bool TrySave(PayPending pending,out string error){
            error=null;try{
                if(pending==null||!pending.Valid)throw new InvalidOperationException("CheckoutPaymentInvalid");var value=Read();
                if(value.phase!="Ordered"||!value.hasOrder||!pending.request.SameOrder(value.order.Request()))throw new InvalidOperationException("CheckoutPaymentOwnerMismatch");
                // Two owners must not both claim the one pre-SDK dispatch.
                // An acknowledgement lost after this CAS is recovered via
                // GetPurchase(s); it never authorizes another Purchase call.
                if(value.hasPayment&&pending.phase=="AwaitingPayment")throw new InvalidOperationException("CheckoutPaymentAlreadyClaimed");
                if(value.hasPayment){var prior=value.payment.Pending(value.order.Request());
                    if(prior.locator!=null&&(pending.locator==null||prior.locator.purchaseId!=pending.locator.purchaseId||prior.locator.invoiceId!=pending.locator.invoiceId))throw new InvalidOperationException("CheckoutKnownPurchaseChanged");
                    if(prior.recoveryPurchaseId!=null&&(pending.locator==null?pending.recoveryPurchaseId!=prior.recoveryPurchaseId:pending.locator.purchaseId!=prior.recoveryPurchaseId))throw new InvalidOperationException("CheckoutRecoveryHintChanged");
                }
                value.hasPayment=true;value.payment=CheckoutPayment86.From(pending);Save(value);return true;
            }catch{error="CheckoutPaymentSaveUnconfirmed";return false;}
        }
        public void Dispose()=>store.Dispose();
    }
}

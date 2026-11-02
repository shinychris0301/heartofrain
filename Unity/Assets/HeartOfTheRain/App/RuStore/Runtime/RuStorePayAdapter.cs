using System;
using System.Linq;
using System.Threading;
using HeartOfTheRain.App.Profile;
#if HOTR_RUSTORE_PAY
using RuStore.PayClient;
#endif

namespace HeartOfTheRain.App.RuStore {
    // Deliberately has no runtime initializer or scene binding. Without an
    // explicit registered configuration it never accesses the SDK singleton.
    // HOTR_RUSTORE_PAY is set only in the separately prepared SDK build path.
    public sealed class RuStorePayAdapter:IPayStore,IDirectPurchaseStore {
        readonly bool configured;readonly IPayAuthority authority;
        public RuStorePayAdapter(bool registeredConfiguration=false,IPayAuthority authority=null){configured=registeredConfiguration;this.authority=authority??new UnavailablePayAuthority();}
        public bool Configured=>configured;
        public bool SdkCompiled{get{
#if HOTR_RUSTORE_PAY
            return true;
#else
            return false;
#endif
        }}
        static Action<PayReply<T>> Once<T>(Action<PayReply<T>> done)where T:class{if(done==null)throw new ArgumentNullException(nameof(done));int called=0;return reply=>{if(Interlocked.Exchange(ref called,1)==0)done(reply);};}
        void Dispatch<T>(Action<PayReply<T>> done,Action<Action<PayReply<T>>> send,bool unknown=false)where T:class{
            var complete=Once(done);if(!configured){complete(PayReply<T>.Fail("RuStoreNotConfigured"));return;}if(!SdkCompiled){complete(PayReply<T>.Fail("RuStoreSdkNotInstalled"));return;}
            try{send(complete);}catch(Exception){complete(PayReply<T>.Fail("RuStoreDispatchFailed",unknown));}
        }
        public void GetPurchaseAvailability(Action<PayReply<PayAvailability>> done){
            Dispatch(done,complete=>{
#if HOTR_RUSTORE_PAY
                RuStorePayClient.Instance.GetPurchaseAvailability(error=>{LogUnavailable(error);complete(PayReply<PayAvailability>.Fail(Error(error)));},value=>{if(value!=null&&!value.isAvailable)LogUnavailable(value.cause);complete(value==null?PayReply<PayAvailability>.Fail("MissingAvailability"):PayReply<PayAvailability>.Ok(new PayAvailability(value.isAvailable)));});
#endif
            });
        }
        public void GetProducts(string[] productIds,Action<PayReply<PayProduct[]>> done){
            if(productIds==null||productIds.Length==0||productIds.Length>1000||productIds.Any(string.IsNullOrWhiteSpace)||productIds.Distinct(StringComparer.Ordinal).Count()!=productIds.Length){done(PayReply<PayProduct[]>.Fail("InvalidProductIds"));return;}
            var requested=(string[])productIds.Clone();Dispatch(done,complete=>{
#if HOTR_RUSTORE_PAY
                RuStorePayClient.Instance.GetProducts(requested.Select(id=>new ProductId(id)).ToArray(),error=>complete(PayReply<PayProduct[]>.Fail(Error(error))),values=>{
                    if(values==null||values.Any(p=>p==null||p.productId==null||!requested.Contains(p.productId.value,StringComparer.Ordinal))||values.Select(p=>p.productId.value).Distinct(StringComparer.Ordinal).Count()!=values.Count){complete(PayReply<PayProduct[]>.Fail("ProductCorrelationMismatch"));return;}
                    complete(PayReply<PayProduct[]>.Ok(values.Select(p=>new PayProduct(p.productId.value,p.amountLabel?.value,p.currency?.value,p.price==null?(long?)null:p.price.value,p.type.ToString())).ToArray()));
                });
#endif
            });
        }
        public void Purchase(PayRequest request,Action<PayReply<PayLocator>> done){
            if(request==null||!request.Valid){done(PayReply<PayLocator>.Fail("InvalidServerOrder"));return;}if(!authority.WalletReady){done(PayReply<PayLocator>.Fail("AuthoritativeWalletUnavailable"));return;}
            PurchaseCore(request,done);
        }
        public void PurchaseDirect(PayRequest request,Action<PayReply<PayLocator>> done){
            if(request==null||!request.Valid){done(PayReply<PayLocator>.Fail("InvalidLocalOrder"));return;}
            PurchaseCore(request,done);
        }
        void PurchaseCore(PayRequest request,Action<PayReply<PayLocator>> done){
            Dispatch(done,complete=>{
#if HOTR_RUSTORE_PAY
                // Supply the actual SDK AppUserId field. Never replace a
                // missing server identity/payload with local profile data.
                var parameters=new ProductPurchaseParams(new ProductId(request.productId),appUserId:new AppUserId(request.appUserId),developerPayload:new DeveloperPayload(request.developerPayload),orderId:new OrderId(request.orderId),quantity:new Quantity(request.quantity));
                RuStorePayClient.Instance.Purchase(parameters,PreferredPurchaseType.ONE_STEP,error=>complete(PayReply<PayLocator>.Fail(Error(error),true,RecoveryPurchaseId(error))),value=>{
                    if(value==null){complete(PayReply<PayLocator>.Fail("MissingPurchaseResult",true));return;}
                    var locator=new PayLocator(value.purchaseId?.value,value.invoiceId?.value,value.orderId?.value,value.productId?.value,value.quantity?.value??0,value.sandbox);
                    complete(locator.Matches(request)?PayReply<PayLocator>.Ok(locator):PayReply<PayLocator>.Fail("PurchaseCorrelationMismatch",true));
                });
#endif
            },true);
        }
        public void GetPurchase(string purchaseId,Action<PayReply<PayPurchase>> done){
            if(string.IsNullOrWhiteSpace(purchaseId)){done(PayReply<PayPurchase>.Fail("InvalidPurchaseId"));return;}Dispatch(done,complete=>{
#if HOTR_RUSTORE_PAY
                RuStorePayClient.Instance.GetPurchase(new PurchaseId(purchaseId),error=>complete(PayReply<PayPurchase>.Fail(Error(error),true)),value=>{
                    var product=value as ProductPurchase;if(product==null||product.purchaseId?.value!=purchaseId){complete(PayReply<PayPurchase>.Fail("PurchaseLookupMismatch",true));return;}complete(PayReply<PayPurchase>.Ok(Map(product)));
                });
#endif
            },true);
        }
        public void GetPurchases(Action<PayReply<PayPurchase[]>> done){Dispatch(done,complete=>{
#if HOTR_RUSTORE_PAY
            RuStorePayClient.Instance.GetPurchases(error=>complete(PayReply<PayPurchase[]>.Fail(Error(error),true)),values=>{
                if(values==null||values.Any(p=>!(p is ProductPurchase))){complete(PayReply<PayPurchase[]>.Fail("UnsupportedRecoveryPurchase",true));return;}complete(PayReply<PayPurchase[]>.Ok(values.Cast<ProductPurchase>().Select(Map).ToArray()));
            });
#endif
        },true);}
        public void ConfirmTwoStep(PayRequest request,PayPurchase purchase,PayCaptureAuthorization authorization,Action<PayReply<PayAvailability>> done){
            if(!authority.WalletReady||authorization==null||!authorization.Matches(request,purchase)){done(PayReply<PayAvailability>.Fail("CaptureNotAuthorized"));return;}Dispatch(done,complete=>{
#if HOTR_RUSTORE_PAY
                RuStorePayClient.Instance.ConfirmTwoStepPurchase(new PurchaseId(purchase.locator.purchaseId),null,error=>complete(PayReply<PayAvailability>.Fail(Error(error),true)),()=>complete(PayReply<PayAvailability>.Ok(new PayAvailability(true))));
#endif
            },true);
        }
        public void Acknowledge(PayRequest request,PayPurchase purchase,PayDeliveryReceipt receipt,Action<PayReply<PayAvailability>> done){
            if(!authority.WalletReady||receipt==null||!receipt.Matches(request,purchase)){done(PayReply<PayAvailability>.Fail("DeliveryNotAuthorized"));return;}Dispatch(done,complete=>{
#if HOTR_RUSTORE_PAY
                if(purchase.acknowledgementState=="ACKNOWLEDGED"){complete(PayReply<PayAvailability>.Ok(new PayAvailability(true)));return;}
                RuStorePayClient.Instance.UpdateAcknowledgementState(new PurchaseId(purchase.locator.purchaseId),AcknowledgementState.ACKNOWLEDGED,null,error=>complete(PayReply<PayAvailability>.Fail(Error(error),true)),state=>{
                    if(state!=AcknowledgementState.ACKNOWLEDGED){complete(PayReply<PayAvailability>.Fail("AcknowledgementPending",true));return;}
                    GetPurchase(purchase.locator.purchaseId,observed=>complete(observed.Succeeded&&observed.value.Matches(request)&&observed.value.acknowledgementState=="ACKNOWLEDGED"?PayReply<PayAvailability>.Ok(new PayAvailability(true)):PayReply<PayAvailability>.Fail("AcknowledgementNotVerified",true)));
                });
#endif
            },true);
        }
        public void AcknowledgeDirect(PayRequest request,PayPurchase purchase,DirectPurchaseReceipt receipt,Action<PayReply<PayAvailability>> done){
            if(receipt==null||!receipt.sandbox.Equals(request?.sandbox)||receipt.orderId!=request.orderId||
                receipt.productId==null||receipt.storeProductId!=request.productId||receipt.purchaseId!=purchase?.locator?.purchaseId||
                receipt.invoiceId!=purchase.locator.invoiceId||!DirectPurchaseLedger.Confirmed(request,purchase,DirectPurchaseCatalog.Find(receipt.productId))||
                receipt.phase!="Credited"&&receipt.phase!="Acknowledged"){
                done(PayReply<PayAvailability>.Fail("LocalDeliveryNotCommitted"));return;
            }
            Dispatch(done,complete=>{
#if HOTR_RUSTORE_PAY
                if(purchase.acknowledgementState=="ACKNOWLEDGED"){complete(PayReply<PayAvailability>.Ok(new PayAvailability(true)));return;}
                RuStorePayClient.Instance.UpdateAcknowledgementState(new PurchaseId(purchase.locator.purchaseId),AcknowledgementState.ACKNOWLEDGED,null,
                    error=>complete(PayReply<PayAvailability>.Fail(Error(error),true)),state=>{
                        if(state!=AcknowledgementState.ACKNOWLEDGED){complete(PayReply<PayAvailability>.Fail("AcknowledgementPending",true));return;}
                        GetPurchase(purchase.locator.purchaseId,observed=>complete(observed.Succeeded&&observed.value.Matches(request)&&
                            observed.value.acknowledgementState=="ACKNOWLEDGED"?PayReply<PayAvailability>.Ok(new PayAvailability(true)):PayReply<PayAvailability>.Fail("AcknowledgementNotVerified",true)));
                    });
#endif
            },true);
        }
#if HOTR_RUSTORE_PAY
        // The exception name alone cannot separate a provider refusal from a network fault.
        // The id and message appear in development builds only, with any query string removed.
        static void LogUnavailable(global::RuStore.RuStoreError error){
            var line="HOTR rustore unavailable";
            for(int depth=0;error!=null&&depth<4;depth++){
                var network=error as RuStorePaymentException.RuStorePaymentNetworkException;
                line+=" cause"+depth+"="+Safe(error.name)+(network==null?"":" code="+Safe(network.code));
                if(UnityEngine.Debug.isDebugBuild)line+=(network==null?"":" id="+Safe(network.id))+" message="+Safe(error.description);
                error=(error as RuStorePaymentException)?.cause;
            }
            UnityEngine.Debug.Log(line);
        }
        static string Safe(string value){
            if(string.IsNullOrEmpty(value))return "none";
            int query=value.IndexOf('?');if(query>=0)value=value.Substring(0,query);
            return value.Length>160?value.Substring(0,160):value;
        }
        static string RecoveryPurchaseId(global::RuStore.RuStoreError error){
            var cancelled=error as RuStorePaymentException.ProductPurchaseCancelled;
            if(cancelled!=null)return PayPending.CanonicalPurchaseId(cancelled.purchaseId?.value);
            var failed=error as RuStorePaymentException.ProductPurchaseException;
            return failed==null?null:PayPending.CanonicalPurchaseId(failed.purchaseId?.value);
        }
        static string Error(global::RuStore.RuStoreError error)=>string.IsNullOrWhiteSpace(error?.name)?"RuStoreUnknownError":error.name;
        static PayPurchase Map(ProductPurchase value)=>new PayPurchase(new PayLocator(value.purchaseId?.value,value.invoiceId?.value,value.orderId?.value,value.productId?.value,value.quantity?.value??0,value.sandbox),value.developerPayload?.value,value.status.ToString(),value.purchaseType.ToString(),value.acknowledgementState.ToString(),value.productType.ToString(),value.price==null?(long?)null:value.price.value,value.currency==null?null:value.currency.value);
#endif
    }
}

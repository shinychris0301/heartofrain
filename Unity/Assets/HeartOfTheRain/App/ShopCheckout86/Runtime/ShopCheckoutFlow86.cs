using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using HeartOfTheRain.App.RuStore;

namespace HeartOfTheRain.App.ShopCheckout86 {
    // An explicitly configured managed-wallet controller. SDK callbacks never mutate a profile.
    public sealed class ShopCheckoutFlow86:IDisposable {
        readonly CheckoutConfiguration86 configuration;
        readonly Func<Action<CheckoutAccess86,string>,IEnumerator> authorize;
        readonly Func<Action<bool,string>,IEnumerator> refresh;
        readonly Func<CheckoutAccess86,ProtectedCheckoutJournal86> journalFactory;
        readonly Func<IPayAuthority,IPayStore> storeFactory;readonly Action<CheckoutAccess86,RuStoreServerOrder> committedPresentation;
        CheckoutAccess86 owner;ProtectedCheckoutJournal86 journal;CheckoutDocument86 document;IPayStore store;PayDeliveryCoordinator delivery;
        readonly Authority authority;int epoch;bool disposed;string boundOrigin,boundPlayer;
        readonly Dictionary<string,CheckoutQuote86> quotes=new Dictionary<string,CheckoutQuote86>(StringComparer.Ordinal);
        public bool Busy{get;private set;}public bool Pending=>document!=null&&document.Pending;public bool Credited{get;private set;}
        public string Error{get;private set;}public event Action Changed;
        public string PendingProduct=>Pending?document.productId:null;
        public string Price(string id)=>quotes.TryGetValue(id,out var quote)?quote.AmountLabel:null;
        public string Eligibility(string id)=>quotes.TryGetValue(id,out var quote)?quote.Product.policy?.eligibility:document!=null&&document.hasOrder&&document.productId==id?document.order.policy?.eligibility:null;
        public bool CanBuy(string id)=>!disposed&&!Busy&&quotes.TryGetValue(id,out var quote)&&(Pending?document.productId==id:quote.Product.policy==null||!quote.Product.policy.specified||quote.Product.policy.eligible);
        public ShopCheckoutFlow86(CheckoutConfiguration86 configuration,Func<Action<CheckoutAccess86,string>,IEnumerator> authorize,Func<Action<bool,string>,IEnumerator> refresh,Func<CheckoutAccess86,ProtectedCheckoutJournal86> journalFactory,Func<IPayAuthority,IPayStore> storeFactory,Action<CheckoutAccess86,RuStoreServerOrder> committedPresentation=null){
            if(!CheckoutConfiguration86.Valid(configuration))throw new ArgumentException("CheckoutExplicitEnvironmentRequired");this.configuration=configuration;this.authorize=authorize??throw new ArgumentNullException(nameof(authorize));this.refresh=refresh??throw new ArgumentNullException(nameof(refresh));this.journalFactory=journalFactory??throw new ArgumentNullException(nameof(journalFactory));this.storeFactory=storeFactory??throw new ArgumentNullException(nameof(storeFactory));this.committedPresentation=committedPresentation;authority=new Authority(this);
        }
        bool Owned(int token)=>!disposed&&epoch==token&&owner!=null;
        bool Current(int token)=>Owned(token)&&owner.Current;
        void Notify(){Changed?.Invoke();}
        IEnumerator Authorize(int token){
            CheckoutAccess86 next=null;string why=null;yield return authorize((value,error)=>{next=value;why=error;});
            if(disposed||token!=epoch){next?.Backend.Dispose();yield break;}
            if(next==null||!next.Current||!next.Backend.WalletReady){next?.Backend.Dispose();Error=why??"CheckoutFreshWalletRequired";yield break;}
            if(boundPlayer!=null&&(boundOrigin!=next.Origin||boundPlayer!=next.Player)){next.Backend.Dispose();Error="CheckoutOwnerChanged";yield break;}
            boundOrigin=next.Origin;boundPlayer=next.Player;
            var before=owner;owner=next;if(before!=null&&!ReferenceEquals(before.Backend,next.Backend))before.Backend.Dispose();
            if(journal==null)journal=journalFactory(owner);document=journal.Read();
            if(store==null)store=storeFactory(authority);
            if(store==null||!store.Configured||!store.SdkCompiled){Error="CheckoutSdkUnavailable";yield break;}
        }
        IEnumerator Discover(int token){
            if(document.Pending||!(owner.Backend is ICheckoutRecovery100 recovery))yield break;
            PayReply<RuStorePendingOrders100> reply=null;recovery.Pending(0,r=>reply=r);while(Owned(token)&&reply==null)yield return null;if(!Current(token))yield break;
            if(reply==null||!reply.Succeeded){Error=reply?.error?.code??"CheckoutPendingDiscoveryUnavailable";yield break;}
            var pending=reply.value;if(pending.playerId!=owner.Player||pending.productionEnabled!=configuration.productionEnabled||pending.orders==null){Error="CheckoutPendingOwnerMismatch";yield break;}
            if(pending.orders.Length==0){if(pending.hasMore)Error="CheckoutPendingPageInvalid";yield break;}
            var order=pending.orders[0];var product=CheckoutCatalogRules86.FrozenProduct(order);var quote=new CheckoutQuote86(product,CheckoutText86.T("retry"));
            if(!CheckoutCatalogRules86.Order(order,quote,owner.Player,configuration.productionEnabled,configuration.verificationMode)){Error="CheckoutPendingOrderMismatch";yield break;}
            // Without this device's durable pre-dispatch journal, Created is
            // also an unknown payment outcome. Never infer permission to rebuy.
            var payment=new CheckoutPayment86{phase="OutcomeUnknown"};
            if(!string.IsNullOrEmpty(order.purchaseId)&&!string.IsNullOrEmpty(order.invoiceId)){
                var locator=new PayLocator(order.purchaseId,order.invoiceId,order.orderId,order.sdk.productId,1,configuration.sandbox);
                if(!locator.Matches(order.Request())){Error="CheckoutPendingLocatorInvalid";yield break;}
                payment=new CheckoutPayment86{phase="AwaitingAuthority",hasLocator=true,purchaseId=order.purchaseId,invoiceId=order.invoiceId};
            }
            document=journal.Save(new CheckoutDocument86{verificationMode=CommerceVerification125.Legacy(configuration.verificationMode),revision=document.revision,origin=owner.Origin,player=owner.Player,phase="Ordered",commandId=Guid.NewGuid().ToString("N"),productId=order.productId,product=product,amountLabel=quote.AmountLabel,hasOrder=true,order=order,hasPayment=true,payment=payment});
        }
        IEnumerator Quotes(int token){
            // SDK reads have no deadline of their own; a silent callback must not hold the Shop.
            float limit=UnityEngine.Time.unscaledTime+SdkReadSeconds;
            quotes.Clear();PayReply<PayAvailability> available=null;store.GetPurchaseAvailability(r=>available=r);while(Owned(token)&&available==null&&UnityEngine.Time.unscaledTime<limit)yield return null;if(!Current(token))yield break;
            if(available==null||!available.Succeeded||!available.value.available){Error=available?.error?.code??"CheckoutPaymentUnavailable";yield break;}
            PayReply<CheckoutCatalog86> catalog=null;owner.Backend.Catalog(r=>catalog=r);while(Owned(token)&&catalog==null)yield return null;if(!Current(token))yield break;
            if(catalog==null||!catalog.Succeeded){Error=catalog?.error?.code??"CheckoutCatalogUnavailable";yield break;}
            if(catalog.value.products==null){Error="CheckoutCatalogUnavailable";yield break;}
            PayReply<PayProduct[]> products=null;limit=UnityEngine.Time.unscaledTime+SdkReadSeconds;store.GetProducts(catalog.value.products.Select(p=>p.storeProductId).ToArray(),r=>products=r);while(Owned(token)&&products==null&&UnityEngine.Time.unscaledTime<limit)yield return null;if(!Current(token))yield break;
            if(products==null||!products.Succeeded){Error=products?.error?.code??"CheckoutSdkCatalogUnavailable";yield break;}
            var matched=CheckoutCatalogRules86.Match(configuration,catalog.value,products.value);quotes.Clear();foreach(var pair in matched)quotes.Add(pair.Key,pair.Value);
        }
        const float SdkReadSeconds=20;
        public bool Reading{get;private set;}
        public IEnumerator Refresh(){
            if(disposed||Busy)yield break;Busy=Reading=true;Credited=false;Error=null;int token=++epoch;Notify();
            try{yield return Authorize(token);if(!Current(token)||Error!=null)yield break;yield return Discover(token);if(!Current(token)||Error!=null)yield break;yield return Quotes(token);}
            finally{if(token==epoch){Busy=Reading=false;Notify();}}
        }
        public IEnumerator Buy(string product){
            if(disposed||Busy||!CheckoutCatalogRules86.Known(product))yield break;Busy=true;Credited=false;Error=null;int token=++epoch;Notify();
            try{
                yield return Authorize(token);if(!Current(token)||Error!=null)yield break;
                yield return Discover(token);if(!Current(token)||Error!=null)yield break;
                if(!document.Pending){
                    yield return Quotes(token);if(!Current(token)||Error!=null||!quotes.TryGetValue(product,out var quote))yield break;
                    if(quote.Product.policy!=null&&quote.Product.policy.specified&&!quote.Product.policy.eligible){Error="CheckoutOfferNotEligible";yield break;}
                    document=new CheckoutDocument86{verificationMode=CommerceVerification125.Legacy(configuration.verificationMode),revision=document.revision,origin=owner.Origin,player=owner.Player,phase="Creating",commandId=Guid.NewGuid().ToString("N"),productId=product,product=quote.Product,amountLabel=quote.AmountLabel};document=journal.Save(document);
                }else if(document.productId!=product){Error="CheckoutAnotherOrderPending";yield break;}
                yield return RecoverCore(token,true);
            }finally{if(token==epoch){Busy=false;Notify();}}
        }
        public IEnumerator Recover(){
            if(disposed||Busy)yield break;Busy=true;Credited=false;Error=null;int token=++epoch;Notify();
            try{yield return Authorize(token);if(!Current(token)||Error!=null)yield break;yield return Discover(token);if(Current(token)&&Error==null&&document.Pending)yield return RecoverCore(token,false);}
            finally{if(token==epoch){Busy=false;Notify();}}
        }
        IEnumerator RecoverCore(int token,bool explicitPurchase){
            if(document.phase=="Creating"){
                PayReply<RuStoreServerOrder> created=null;owner.Backend.Create(document.commandId,document.productId,r=>created=r);while(Owned(token)&&created==null)yield return null;if(!Current(token))yield break;
                if(created==null||!created.Succeeded){Error=created?.error?.code??"CheckoutCreateUnknown";yield break;}
                if(!CheckoutCatalogRules86.Order(created.value,new CheckoutQuote86(document.product,document.amountLabel),owner.Player,configuration.productionEnabled,configuration.verificationMode)){Error="CheckoutOrderMismatch";yield break;}
                document.order=created.value;document.hasOrder=true;document.phase="Ordered";
                // Another device may have won reservation after our discovery.
                // Only the server-frozen creator command can authorize this
                // device's first SDK dispatch; null/foreign remains lookup-only.
                if(created.value.creationCommandId!=document.commandId){document.hasPayment=true;document.payment=new CheckoutPayment86{phase="OutcomeUnknown"};}
                document=journal.Save(document);
            }
            PayReply<RuStoreServerOrder> canonical=null;owner.Backend.Read(document.order.orderId,r=>canonical=r);while(Owned(token)&&canonical==null)yield return null;if(!Current(token))yield break;
            if(canonical==null||!canonical.Succeeded||!CheckoutCatalogRules86.Order(canonical.value,new CheckoutQuote86(document.product,document.amountLabel),owner.Player,configuration.productionEnabled,configuration.verificationMode)||!canonical.value.Request().SameOrder(document.order.Request())){Error="CheckoutOrderRecoveryUnavailable";yield break;}
            if(!document.hasPayment&&(canonical.value.creationCommandId!=document.commandId||canonical.value.state!="Created")){
                document.hasPayment=true;document.payment=new CheckoutPayment86{phase="OutcomeUnknown"};
                if(!string.IsNullOrEmpty(canonical.value.purchaseId)&&!string.IsNullOrEmpty(canonical.value.invoiceId))document.payment=new CheckoutPayment86{phase="AwaitingAuthority",hasLocator=true,purchaseId=canonical.value.purchaseId,invoiceId=canonical.value.invoiceId};
                document=journal.Save(document);
            }
            // Passive reopen/reconciliation never starts a new SDK purchase.
            if(!document.hasPayment&&!explicitPurchase){Error="CheckoutExplicitPurchaseRequired";yield break;}
            delivery=new PayDeliveryCoordinator(store,authority,journal);PayReply<PayPending> result=null;
            if(document.hasPayment)delivery.Recover(r=>result=r);else delivery.Begin(document.order.Request(),r=>result=r);
            while(Owned(token)&&result==null)yield return null;if(!Owned(token))yield break;document=journal.Read();
            if(result==null||!result.Succeeded){Error=result?.error?.code??"CheckoutDeliveryUnknown";yield break;}
            if(result.value.phase!="Acknowledged"&&result.value.phase!="ResolvedWithoutDelivery"){Error="CheckoutDeliveryUnknown";yield break;}
            RuStoreServerOrder settledOrder=null;
            if(result.value.phase=="Acknowledged"){
                // SDK delivery acknowledgement is not server acknowledgement.
                // Reconcile the selected payment mode; a lag/failed reply leaves
                // the same paid outbox recoverable without another Purchase.
                yield return Authorize(token);if(!Current(token)||Error!=null)yield break;
                PayReply<PayPurchase> observed=null;store.GetPurchase(result.value.locator.purchaseId,r=>observed=r);while(Owned(token)&&observed==null)yield return null;if(!Current(token))yield break;
                if(observed==null||!observed.Succeeded||!observed.value.Matches(document.order.Request())){Error=observed?.error?.code??"CheckoutAcknowledgementLookupUnavailable";yield break;}
                PayReply<PayDeliveryReceipt> confirmed=null;owner.Backend.Reconcile(document.order.Request(),observed.value,r=>confirmed=r);while(Owned(token)&&confirmed==null)yield return null;if(!Current(token))yield break;
                if(confirmed==null||!confirmed.Succeeded||!confirmed.value.Matches(document.order.Request(),observed.value)){Error=confirmed?.error?.code??"CheckoutAcknowledgementPending";yield break;}
                PayReply<RuStoreServerOrder> acknowledged=null;owner.Backend.Read(document.order.orderId,r=>acknowledged=r);while(Owned(token)&&acknowledged==null)yield return null;if(!Current(token))yield break;
                if(acknowledged==null||!acknowledged.Succeeded||!CheckoutCatalogRules86.Order(acknowledged.value,new CheckoutQuote86(document.product,document.amountLabel),owner.Player,configuration.productionEnabled,configuration.verificationMode)||acknowledged.value.state!="Confirmed"||acknowledged.value.deliveryAcknowledgement!="Acknowledged"){Error="CheckoutAcknowledgementPending";yield break;}
                settledOrder=acknowledged.value;
            }
            bool fresh=false;string why=null;yield return refresh((ok,error)=>{fresh=ok;why=error;});if(!Current(token)||!fresh){Error=why??"CheckoutProjectionPending";yield break;}
            if(result.value.phase=="Acknowledged"){
                if(settledOrder?.credit==null||!CommerceTerms100.Same(settledOrder.credit.grant,document.product.grant)||settledOrder.credit.receiptId!=result.value.receipt.receiptId){Error="CheckoutCommittedReceiptMismatch";yield break;}
                try{committedPresentation?.Invoke(owner,settledOrder);}catch{Error="CheckoutRewardPresentationPending";yield break;}
            }
            document=journal.Read();document.phase="Settled";if(settledOrder!=null)document.order=settledOrder;document=journal.Save(document);if(settledOrder!=null&&quotes.TryGetValue(document.productId,out var deliveredQuote))deliveredQuote.Product.policy=settledOrder.policy;Credited=result.value.phase=="Acknowledged";Error=Credited?null:"CheckoutResolvedWithoutDelivery";
        }
        sealed class Authority:IPayAuthority,IPayTerminalAuthority {
            readonly ShopCheckoutFlow86 flow;public Authority(ShopCheckoutFlow86 flow){this.flow=flow;}
            public bool WalletReady=>!flow.disposed&&flow.owner!=null&&flow.owner.Current&&flow.owner.Backend.WalletReady;
            public void Reconcile(PayRequest request,PayPurchase observed,Action<PayReply<PayDeliveryReceipt>> done)=>flow.AuthorityRequest(request,observed,done);
            public void ResolveTerminal(PayRequest request,PayPurchase observed,Action<PayReply<PayTerminalReceipt>> done)=>flow.TerminalRequest(request,observed,done);
        }
        // SDK presentation can outlive a short bearer. Renew the same bound
        // account before contacting authority; the outbox survives any failure.
        void AuthorityRequest(PayRequest request,PayPurchase purchase,Action<PayReply<PayDeliveryReceipt>> done){if(authorityDispatch==null){done(PayReply<PayDeliveryReceipt>.Fail("CheckoutDispatcherRequired",true));return;}try{authorityDispatch(Guard(RenewAndReconcile(request,purchase,done)));}catch{done(PayReply<PayDeliveryReceipt>.Fail("CheckoutDispatchUnknown",true));}}
        void TerminalRequest(PayRequest request,PayPurchase purchase,Action<PayReply<PayTerminalReceipt>> done){if(authorityDispatch==null){done(PayReply<PayTerminalReceipt>.Fail("CheckoutDispatcherRequired",true));return;}try{authorityDispatch(Guard(RenewAndTerminal(request,purchase,done)));}catch{done(PayReply<PayTerminalReceipt>.Fail("CheckoutDispatchUnknown",true));}}
        Action<IEnumerator> authorityDispatch;
        public void SetAuthorityDispatcher(Action<IEnumerator> dispatch){authorityDispatch=dispatch??throw new ArgumentNullException(nameof(dispatch));}
        IEnumerator RenewAndReconcile(PayRequest request,PayPurchase purchase,Action<PayReply<PayDeliveryReceipt>> done){int token=epoch;bool dispatched=false;try{yield return Authorize(token);if(!Current(token)||Error!=null){dispatched=true;done(PayReply<PayDeliveryReceipt>.Fail(Error??"CheckoutOwnerChanged",true));yield break;}dispatched=true;owner.Backend.Reconcile(request,purchase,done);}finally{if(!dispatched)done(PayReply<PayDeliveryReceipt>.Fail("CheckoutAuthorityUnknown",true));}}
        IEnumerator RenewAndTerminal(PayRequest request,PayPurchase purchase,Action<PayReply<PayTerminalReceipt>> done){int token=epoch;bool dispatched=false;try{yield return Authorize(token);if(!Current(token)||Error!=null){dispatched=true;done(PayReply<PayTerminalReceipt>.Fail(Error??"CheckoutOwnerChanged",true));yield break;}dispatched=true;owner.Backend.ResolveTerminal(request,purchase,done);}finally{if(!dispatched)done(PayReply<PayTerminalReceipt>.Fail("CheckoutAuthorityUnknown",true));}}
        public IEnumerator Guard(IEnumerator routine){
            var stack=new Stack<IEnumerator>();stack.Push(routine);int owned=epoch;bool entered=false;
            try{while(stack.Count>0){bool moved=false;object next=null;Exception fault=null;try{moved=stack.Peek().MoveNext();if(moved)next=stack.Peek().Current;}catch(Exception error){fault=error;}
                if(!entered){entered=true;owned=epoch;}if(fault!=null){if(!disposed&&epoch==owned){Error="CheckoutRecoveryRequired";Busy=false;Notify();}yield break;}if(!moved){(stack.Pop()as IDisposable)?.Dispose();continue;}if(next is IEnumerator nested)stack.Push(nested);else yield return next;
            }}finally{while(stack.Count>0)try{(stack.Pop()as IDisposable)?.Dispose();}catch{}}
        }
        public void Invalidate(){epoch++;delivery?.Cancel();owner?.Backend.Dispose();owner=null;quotes.Clear();Credited=false;Busy=false;Error="CheckoutOwnerChanged";Notify();}
        public void Dispose(){if(disposed)return;Invalidate();disposed=true;journal?.Dispose();}
    }
}

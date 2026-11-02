using System;
using System.Linq;
using System.Threading;

namespace HeartOfTheRain.App.RuStore {
    // No default instance, automatic checkout or local grant. The app must
    // supply its authenticated authority and durable journal explicitly.
    // Callbacks belong to one serialized owner; cancellation fences callbacks
    // while retaining the journal so another owner can recover the order.
    public sealed class PayDeliveryCoordinator {
        readonly IPayStore store;readonly IPayAuthority authority;readonly IPayJournal journal;long generation;Action<PayReply<PayPending>> activeDone;
        public bool Busy{get;private set;}
        public PayDeliveryCoordinator(IPayStore store,IPayAuthority authority,IPayJournal journal){this.store=store??throw new ArgumentNullException(nameof(store));this.authority=authority??throw new ArgumentNullException(nameof(authority));this.journal=journal??throw new ArgumentNullException(nameof(journal));}
        public void Cancel(){Interlocked.Increment(ref generation);Busy=false;}
        static Action<PayReply<PayPending>> CompleteOnce(Action<PayReply<PayPending>> done){int called=0;return result=>{if(Interlocked.Exchange(ref called,1)!=0)return;try{done(result);}catch(Exception){/* A UI callback cannot replay financial work. */}};}
        Action<PayReply<T>> Once<T>(long token,Action<PayReply<T>> action)where T:class{int called=0;return result=>{if(token!=generation||Interlocked.Exchange(ref called,1)!=0)return;try{action(result??PayReply<T>.Fail("MissingProviderReply",true));}catch(Exception){if(token==generation)End(activeDone,"PaymentStageFailed",true);}};}
        bool Save(PayPending pending,Action<PayReply<PayPending>> done){if(pending==null||!pending.Valid){End(done,"InvalidPendingJournal",true);return false;}try{string error;if(journal.TrySave(pending,out error))return true;End(done,"JournalSaveUnavailable",true);}catch(Exception){End(done,"JournalSaveFailed",true);}return false;}
        void End(Action<PayReply<PayPending>> done,string error,bool unknown=false){Busy=false;done(PayReply<PayPending>.Fail(error,unknown));}
        bool Ready(Action<PayReply<PayPending>> done){if(Busy){done(PayReply<PayPending>.Fail("PaymentBusy"));return false;}if(!store.Configured||!store.SdkCompiled||!authority.WalletReady){done(PayReply<PayPending>.Fail("PaymentNotConfigured"));return false;}Busy=true;return true;}
        public void Begin(PayRequest request,Action<PayReply<PayPending>> done){
            if(done==null)throw new ArgumentNullException(nameof(done));done=CompleteOnce(done);if(request==null||!request.Valid){done(PayReply<PayPending>.Fail("InvalidServerOrder"));return;}if(!Ready(done))return;long token=Interlocked.Increment(ref generation);activeDone=done;
            try{var prior=journal.Load();if(prior!=null&&!prior.Valid){End(done,"InvalidPendingJournal",true);return;}if(prior!=null&&prior.request.orderId==request.orderId){if(!prior.request.SameOrder(request)){End(done,"ExistingOrderCorrelationMismatch",true);return;}if(prior.phase=="Acknowledged"||prior.phase=="ResolvedWithoutDelivery")Lookup(prior,token,done);else End(done,"PendingOrderRequiresRecovery",true);return;}if(prior!=null&&prior.phase!="Acknowledged"&&prior.phase!="ResolvedWithoutDelivery"){End(done,"AnotherOrderRequiresRecovery",true);return;}
                var pending=new PayPending(request,"AwaitingPayment");if(!Save(pending,done))return;
                store.Purchase(request,Once<PayLocator>(token,result=>{if(!result.Succeeded){if(!Save(new PayPending(request,"OutcomeUnknown",recoveryPurchaseId:result.error.recoveryPurchaseId),done))return;End(done,result.error.code,true);return;}if(!result.value.Matches(request)){End(done,"PurchaseCorrelationMismatch",true);return;}var observed=new PayPending(request,"AwaitingRecovery",result.value);if(!Save(observed,done))return;Lookup(observed,token,done);}));
            }catch(Exception){End(done,"PaymentDispatchFailed",true);}
        }
        public void Recover(Action<PayReply<PayPending>> done){
            if(done==null)throw new ArgumentNullException(nameof(done));done=CompleteOnce(done);if(!Ready(done))return;long token=Interlocked.Increment(ref generation);activeDone=done;
            try{var pending=journal.Load();if(pending==null){End(done,"NoValidPendingOrder");return;}if(!pending.Valid){End(done,"InvalidPendingJournal",true);return;}if(pending.locator!=null){Lookup(pending,token,done);return;}if(pending.recoveryPurchaseId!=null){store.GetPurchase(pending.recoveryPurchaseId,Once<PayPurchase>(token,result=>{if(!result.Succeeded){End(done,result.error.code,true);return;}if(result.value?.locator?.purchaseId!=pending.recoveryPurchaseId){End(done,"RecoveredPurchaseHintMismatch",true);return;}Reconcile(pending,result.value,token,done);}));return;}
                store.GetPurchases(Once<PayPurchase[]>(token,result=>{if(!result.Succeeded){End(done,result.error.code,true);return;}var matches=result.value.Where(p=>p!=null&&p.Matches(pending.request)).ToArray();if(matches.Length!=1){End(done,matches.Length==0?"PurchaseStillUnknown":"AmbiguousPurchaseRecovery",true);return;}var known=new PayPending(pending.request,"AwaitingAuthority",matches[0].locator);if(Save(known,done))Reconcile(known,matches[0],token,done);}));
            }catch(Exception){End(done,"PaymentRecoveryFailed",true);}
        }
        void Lookup(PayPending pending,long token,Action<PayReply<PayPending>> done){store.GetPurchase(pending.locator.purchaseId,Once<PayPurchase>(token,result=>{if(!result.Succeeded){End(done,result.error.code,true);return;}Reconcile(pending,result.value,token,done);}));}
        void Reconcile(PayPending pending,PayPurchase observed,long token,Action<PayReply<PayPending>> done){
            if(observed==null||!observed.Matches(pending.request)||pending.locator!=null&&(observed.locator.purchaseId!=pending.locator.purchaseId||observed.locator.invoiceId!=pending.locator.invoiceId)){End(done,"RecoveredPurchaseCorrelationMismatch",true);return;}
            if(!Save(new PayPending(pending.request,"AwaitingAuthority",observed.locator),done))return;
            string terminalState=PayTerminalReceipt.StateFor(observed.status);
            if(terminalState!=null){
                var resolver=authority as IPayTerminalAuthority;if(resolver==null){End(done,"TerminalAuthorityUnavailable",true);return;}
                resolver.ResolveTerminal(pending.request,observed,Once<PayTerminalReceipt>(token,result=>{
                    if(!result.Succeeded){End(done,result.error.code,true);return;}
                    if(result.value.state!=terminalState||!result.value.Matches(pending.request,observed.locator)){End(done,"TerminalAuthorityBindingMismatch",true);return;}
                    var closed=new PayPending(pending.request,"ResolvedWithoutDelivery",observed.locator,terminal:result.value);
                    if(!Save(closed,done))return;Busy=false;done(PayReply<PayPending>.Ok(closed));
                }));return;
            }
            authority.Reconcile(pending.request,observed,Once<PayDeliveryReceipt>(token,result=>{if(!result.Succeeded){End(done,result.error.code,true);return;}if(!authority.WalletReady||!result.value.Matches(pending.request,observed)){End(done,"AuthoritativeDeliveryNotCommitted",true);return;}
                var granted=new PayPending(pending.request,"AcknowledgementPending",observed.locator,result.value);if(!Save(granted,done))return;
                store.Acknowledge(pending.request,observed,result.value,Once<PayAvailability>(token,ack=>{if(!ack.Succeeded||!ack.value.available){End(done,ack.error==null?"AcknowledgementPending":ack.error.code,true);return;}var complete=new PayPending(pending.request,"Acknowledged",observed.locator,result.value);if(!Save(complete,done))return;Busy=false;done(PayReply<PayPending>.Ok(complete));}));
            }));
        }
    }
}

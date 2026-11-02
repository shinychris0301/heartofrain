using System;
using System.Globalization;
using System.Linq;
using HeartOfTheRain.App.RuStore;

namespace HeartOfTheRain.App.ShopCheckout86 {
    // The ordinary Host and actual HTTP fixtures share this one typed adapter.
    // No SDK callback, DTO mapping or UI operation grants currency/inventory.
    public sealed class CheckoutBackend100:ICheckoutBackend86,ICheckoutRecovery100 {
        readonly RuStoreBackendClient client;
        public CheckoutBackend100(RuStoreBackendClient client){this.client=client??throw new ArgumentNullException(nameof(client));}
        public bool WalletReady=>client.WalletReady;
        public void Catalog(Action<PayReply<CheckoutCatalog86>> done)=>client.GetCatalog(reply=>{
            if(!reply.Succeeded){done(PayReply<CheckoutCatalog86>.Fail(reply.error.code,reply.error.outcomeUnknown));return;}
            var value=reply.value;done(PayReply<CheckoutCatalog86>.Ok(new CheckoutCatalog86{verificationMode=value.verificationMode,version=value.version,appId=value.appId.ToString(CultureInfo.InvariantCulture),enabled=value.enabled,sandbox=value.sandbox,productionEnabled=value.productionEnabled,balanceScope=value.balanceScope,serverWalletProjection=value.serverWalletProjection,
                products=value.products.Select(p=>new CheckoutProduct86{id=p.id,storeProductId=p.storeProductId,coins=p.coins,grant=p.grant?.Copy(),policy=p.policy,amountMinor=p.amountMinor,currency=p.currency,quantity=p.quantity}).ToArray()}));
        });
        public void Pending(long after,Action<PayReply<RuStorePendingOrders100>> done)=>client.GetPendingOrders100(after,done);
        public void Create(string id,string product,Action<PayReply<RuStoreServerOrder>> done)=>client.CreateOrder(id,product,done);
        public void Read(string id,Action<PayReply<RuStoreServerOrder>> done)=>client.GetOrder(id,done);
        public void Reconcile(PayRequest request,PayPurchase purchase,Action<PayReply<PayDeliveryReceipt>> done)=>client.Reconcile(request,purchase,done);
        public void ResolveTerminal(PayRequest request,PayPurchase purchase,Action<PayReply<PayTerminalReceipt>> done)=>client.ResolveTerminal(request,purchase,done);
        public void Dispose()=>client.Dispose();
    }
}

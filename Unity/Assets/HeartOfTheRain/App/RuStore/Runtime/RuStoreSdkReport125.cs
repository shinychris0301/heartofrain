using System;
using System.Linq;

namespace HeartOfTheRain.App.RuStore {
    // Actual fresh GetPurchase observations only. This is explicitly untrusted
    // app-reported data; it is never converted into a provider VerifiedInvoice.
    [Serializable] public sealed class RuStoreSdkReport125 {
        public string invoiceId,purchaseId,orderId,productId,developerPayload;
        public int quantity;public bool sandbox;
        public string status,purchaseType,acknowledgementState,productType;
        public int amountMinor;public string currency;
        public static RuStoreSdkReport125 From(PayRequest request,PayPurchase observed){
            Guid purchase;
            if(request==null||!request.Valid||observed==null||!observed.Matches(request)||!observed.amountMinor.HasValue||observed.amountMinor.Value<1||observed.amountMinor.Value>int.MaxValue||observed.currency!="RUB"
                ||!Guid.TryParse(observed.locator.purchaseId,out purchase)||purchase.ToString("D")!=observed.locator.purchaseId
                ||!new[]{"INVOICE_CREATED","CANCELLED","PROCESSING","REJECTED","CONFIRMED","REFUNDED","REFUNDING","EXECUTING","EXPIRED","PAID","REVERSED"}.Contains(observed.status)
                ||!new[]{"ONE_STEP","TWO_STEP","UNDEFINED"}.Contains(observed.purchaseType)||!new[]{"PENDING","ACKNOWLEDGED","UNKNOWN"}.Contains(observed.acknowledgementState)
                ||observed.status=="PAID"&&observed.purchaseType!="TWO_STEP"||observed.purchaseType=="UNDEFINED"&&!new[]{"INVOICE_CREATED","PROCESSING","EXECUTING","CANCELLED","REJECTED","EXPIRED"}.Contains(observed.status))throw new ArgumentException("SdkPurchaseObservationInvalid");
            return new RuStoreSdkReport125{invoiceId=observed.locator.invoiceId,purchaseId=observed.locator.purchaseId,orderId=observed.locator.orderId,productId=observed.locator.productId,
                developerPayload=observed.developerPayload,quantity=observed.locator.quantity,sandbox=observed.locator.sandbox,status=observed.status,purchaseType=observed.purchaseType,
                acknowledgementState=observed.acknowledgementState,productType=observed.productType,amountMinor=(int)observed.amountMinor.Value,currency=observed.currency};
        }
    }
}

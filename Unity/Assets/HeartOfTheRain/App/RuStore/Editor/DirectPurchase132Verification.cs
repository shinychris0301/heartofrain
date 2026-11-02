#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.ShopCheckout86;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace HeartOfTheRain.App.RuStore.Editor {
    public static class DirectPurchase132Verification {
        public static void EnableIsolatedSandboxDefines(){
            string expected=Environment.GetEnvironmentVariable("HOTR_DIRECT132_CLONE");
            if(string.IsNullOrEmpty(expected)||Path.GetFullPath(expected).TrimEnd(Path.DirectorySeparatorChar)!=Path.GetFullPath(Directory.GetCurrentDirectory()).TrimEnd(Path.DirectorySeparatorChar))
                throw new InvalidOperationException("IsolatedCloneRequired");
            string defines="HOTR_DIRECT_PAY132;HOTR_DIRECT_SANDBOX132";
            if(Directory.Exists(Path.Combine(expected,"Assets","RustoreSDK")))defines+=";HOTR_RUSTORE_PAY";
            PlayerSettings.SetScriptingDefineSymbols(NamedBuildTarget.Android,defines);
        }
        sealed class FakeStore:IDirectPurchaseStore {
            public bool SdkCompiled=>true;public bool Configured=>true;
            public bool ackFails,callbackLost,wrongPrice,doubleCallback;public int observedPriceDelta,lastProductCount;public string status="CONFIRMED",productType;public int purchaseCalls,ackCalls,lookups;
            public PayRequest request;public string purchaseId=Guid.NewGuid().ToString("D");
            public void GetPurchaseAvailability(Action<PayReply<PayAvailability>> done)=>done(PayReply<PayAvailability>.Ok(new PayAvailability(true)));
            public void GetProducts(string[] ids,Action<PayReply<PayProduct[]>> done){lastProductCount=ids.Length;done(PayReply<PayProduct[]>.Ok(DirectPurchaseCatalog.Offers.Where(o=>ids.Contains(o.sku)).Select(o=>new PayProduct(o.sku,"99 RUB","RUB",o.amountMinor+(wrongPrice?100:0),productType??o.productType??"CONSUMABLE_PRODUCT")).ToArray()));}
            public void PurchaseDirect(PayRequest value,Action<PayReply<PayLocator>> done){purchaseCalls++;request=value;
                if(callbackLost){done(PayReply<PayLocator>.Fail("SyntheticCallbackLost",true));return;}
                done(PayReply<PayLocator>.Ok(Locator()));if(doubleCallback)done(PayReply<PayLocator>.Ok(Locator()));
            }
            PayLocator Locator()=>new PayLocator(purchaseId,"123456",request.orderId,request.productId,1,request.sandbox);
            PayPurchase Purchase()=>new PayPurchase(Locator(),request.developerPayload,status,"ONE_STEP","NOT_ACKNOWLEDGED","CONSUMABLE_PRODUCT",DirectPurchaseCatalog.Offers.Single(o=>o.sku==request.productId).amountMinor+observedPriceDelta,"RUB");
            public void GetPurchase(string id,Action<PayReply<PayPurchase>> done){lookups++;done(id==purchaseId?PayReply<PayPurchase>.Ok(Purchase()):PayReply<PayPurchase>.Fail("Unknown"));}
            public void GetPurchases(Action<PayReply<PayPurchase[]>> done)=>done(PayReply<PayPurchase[]>.Ok(request==null?new PayPurchase[0]:new[]{Purchase()}));
            public void AcknowledgeDirect(PayRequest r,PayPurchase p,DirectPurchaseReceipt receipt,Action<PayReply<PayAvailability>> done){ackCalls++;done(ackFails?PayReply<PayAvailability>.Fail("SyntheticAckFailure",true):PayReply<PayAvailability>.Ok(new PayAvailability(true)));}
            public void ConfirmTwoStep(PayRequest r,PayPurchase p,PayCaptureAuthorization a,Action<PayReply<PayAvailability>> d)=>throw new InvalidOperationException();
        }
        static int checks;static void Check(bool yes,string name){checks++;if(!yes)throw new InvalidOperationException(name);}
        // Native compile and installation smoke only. This verification package
        // is not registered in RuStore Console and cannot test a real charge.
        public static void BuildAndroidSmoke(){
            string project=Path.GetFullPath(Directory.GetCurrentDirectory()).TrimEnd(Path.DirectorySeparatorChar);
            string pinned=Environment.GetEnvironmentVariable("HOTR_DIRECT132_CLONE");
            string output=Environment.GetEnvironmentVariable("HOTR_DIRECT132_APK");
            if(string.IsNullOrEmpty(pinned)||!string.Equals(project,Path.GetFullPath(pinned).TrimEnd(Path.DirectorySeparatorChar),StringComparison.OrdinalIgnoreCase)||
                string.IsNullOrEmpty(output)||!Path.GetFullPath(output).StartsWith(project+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))
                throw new BuildFailedException("PinnedDirect132VerificationCloneRequired");
            string[] defines=PlayerSettings.GetScriptingDefineSymbols(NamedBuildTarget.Android).Split(';');
            if(EditorUserBuildSettings.activeBuildTarget!=BuildTarget.Android||
                PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android)!="com.heartoftherain.directsmoke"||
                !new[]{"HOTR_DIRECT_PAY132","HOTR_DIRECT_SANDBOX132","HOTR_RUSTORE_PAY"}.All(defines.Contains)||
                defines.Contains("HOTR_FIRST_MODERATION130")||defines.Contains("HOTR_PRODUCTION122"))
                throw new BuildFailedException("Direct132SmokeProfileInvalid");
            if(File.Exists(output))throw new BuildFailedException("FreshSmokeApkRequired");
            Directory.CreateDirectory(Path.GetDirectoryName(output));
            var scenes=EditorBuildSettings.scenes.Where(s=>s.enabled).Select(s=>s.path).ToArray();
            var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=scenes,locationPathName=output,target=BuildTarget.Android,options=BuildOptions.Development});
            bool ok=report.summary.result==BuildResult.Succeeded&&report.summary.totalErrors==0&&File.Exists(output);
            Debug.Log("HOTR Direct132 Android smoke "+(ok?"PASS":"FAIL")+" warnings="+report.summary.totalWarnings);
            if(!ok)throw new BuildFailedException("Direct132AndroidSmokeFailed");
            if(Application.isBatchMode)EditorApplication.Exit(0);
        }
        static DirectPurchaseCoordinator Ready(DirectPurchaseLedger ledger,FakeStore store){var flow=new DirectPurchaseCoordinator(ledger,store,true);bool ok=false;flow.Refresh((value,error)=>ok=value);Check(ok,"SDKProductsReady");return flow;}
        [MenuItem("Heart of the Rain/Verification/Direct Purchase 132")]
        public static void Run(){checks=0;string root=Path.Combine(Path.GetTempPath(),"hotr-direct132-"+Guid.NewGuid().ToString("N"));
            try{
                int originalLocale=GameLocale.Current;
                try{GameLocale.Select(4);Check(CheckoutText86.T("buy")=="Купить"&&CheckoutText86.DeviceOnlyNote().Contains("Покупки"),"RussianDirectShopCopy");}
                finally{GameLocale.Select(originalLocale);}
                Check(DirectPurchaseCatalog.Offers.Select(o=>o.id+":"+o.amountMinor).SequenceEqual(new[]{
                    "coins-1000:9900","coins-5000:29900","coins-10000:49900","coins-25000:89900",
                    "coins-50000:159900","coins-100000:299900","wellkeeper:9900","rainy-day:19900",
                    "rainlight:29900","village:39900","festival:59900","keepers:99900"}),"OwnerApprovedRubPriceTable");
                var repository=new FileProfileRepository(root,()=>PlayerProfile.New(new[]{5,5,3,2}));var ledger=new DirectPurchaseLedger(new ProfileService(repository));var store=new FakeStore();
                var flow=Ready(ledger,store);Check(store.lastProductCount==12,"AllTwelveProductsRequested");int before=ledger.Read().coins;bool delivered=false;
                flow.Buy("coins-1000",(ok,error)=>delivered=ok);Check(delivered,"ConfirmedPurchaseDelivered");
                Check(ledger.Read().coins==before+1000&&ledger.Read().directPurchaseReceipts.Count==1&&store.purchaseCalls==1&&store.lookups==1&&store.ackCalls==1,"OneAtomicGrantAndAck");
                var receipt=ledger.Read().directPurchaseReceipts.Single();Check(receipt.phase=="Acknowledged","DurableAcknowledgement");
                Check(!ledger.Credit(receipt.orderId,new PayPurchase(new PayLocator(receipt.purchaseId,receipt.invoiceId,receipt.orderId,receipt.storeProductId,1,true),store.request.developerPayload,"CONFIRMED","ONE_STEP","ACKNOWLEDGED","CONSUMABLE_PRODUCT",receipt.amountMinor,"RUB")),"DuplicateReceiptNoGrant");
                Check(new FileProfileRepository(root,()=>throw new Exception()).Read().coins==before+1000,"DiskRestartRetainsGrant");
                var lost=new FakeStore{callbackLost=true,ackFails=true};var resumed=Ready(ledger,lost);resumed.Buy("village",(ok,error)=>Check(!ok,"CallbackLostRemainsPending"));
                Check(ledger.Read().directPurchaseReceipts.Count==1&&lost.purchaseCalls==1,"CallbackLossDoesNotGrantOrRepurchase");
                resumed.Recover((ok,error)=>Check(!ok&&error=="SyntheticAckFailure","AckFailureRecoverable"));
                Check(ledger.Read().coins==before+6000&&ledger.Read().directPurchaseReceipts.Count==2&&lost.purchaseCalls==1,"RecoveryCreditsOnceWithoutPurchase");
                lost.ackFails=false;new DirectPurchaseCoordinator(new DirectPurchaseLedger(new ProfileService(new FileProfileRepository(root,()=>throw new Exception()))),lost,true)
                    .Recover((ok,error)=>Check(ok,"RestartAcknowledgesExistingGrant"));
                Check(ledger.Read().coins==before+6000&&lost.purchaseCalls==1,"AckRetryNoSecondGrant");
                var held=new FakeStore{status="PAID"};var heldFlow=Ready(ledger,held);heldFlow.Buy("coins-5000",(ok,error)=>Check(!ok&&error=="PaymentHeld","PaidHoldNoGrant"));
                Check(ledger.Read().coins==before+6000,"PaidHoldBalanceUnchanged");held.status="CONFIRMED";heldFlow.Recover((ok,error)=>Check(ok,"PaidHoldLaterConfirmed"));
                Check(ledger.Read().coins==before+11000,"HeldPurchaseCreditedOnce");
                var mismatch=new FakeStore{wrongPrice=true};var mismatchFlow=Ready(ledger,mismatch);Check(mismatchFlow.Price("coins-1000")==null,"PriceMismatchNotQuoted");
                mismatchFlow.Buy("coins-1000",(ok,error)=>Check(!ok,"PriceMismatchCannotBuy"));Check(mismatch.purchaseCalls==0,"NoSDKDispatchOnPriceMismatch");
                var wrongType=new FakeStore{productType="NON_CONSUMABLE_PRODUCT"};var wrongTypeFlow=Ready(ledger,wrongType);
                Check(wrongTypeFlow.Price("coins-1000")==null,"NonConsumableCatalogRejected");
                wrongTypeFlow.Buy("coins-1000",(ok,error)=>Check(!ok,"NonConsumableCannotBuy"));Check(wrongType.purchaseCalls==0,"NoSDKDispatchForWrongType");
                var last=ledger.Read().directPurchaseReceipts.Last();ledger.MarkRefundReview(last.purchaseId);Check(ledger.Read().directPurchaseReceipts.Last().phase=="RefundReview","RefundFlagDurable");
                Check(DirectPurchaseCatalog.Offers.Length==12&&DirectPurchaseCatalog.Offers.Count(o=>!o.purchasable)==3&&
                    DirectPurchaseCatalog.Offers.Where(o=>!o.purchasable).All(o=>o.productType==null),"SpecialTypeUnknownAndCheckoutGated");
                var specials=Ready(ledger,new FakeStore());Check(specials.Price("wellkeeper")!=null&&specials.Price("rainy-day")!=null&&specials.Price("rainlight")!=null,"SpecialPricesFromProvider");
                Check(!specials.CanBuy("wellkeeper")&&!specials.CanBuy("rainy-day")&&!specials.CanBuy("rainlight"),"SpecialCheckoutDisabled");
                specials.Buy("wellkeeper",(ok,error)=>Check(!ok&&error=="PurchaseUnavailable","SpecialBuyRejected"));
                bool specialLedgerBlocked=false;try{ledger.Begin(DirectPurchaseCatalog.Find("wellkeeper"),true);}catch(InvalidOperationException){specialLedgerBlocked=true;}
                Check(specialLedgerBlocked,"SpecialCannotBypassUiThroughLedger");
                foreach(var offer in DirectPurchaseCatalog.Offers.Where(o=>o.purchasable)){
                    var stock=new[]{5,5,3,2};var p=PlayerProfile.New(stock);var matrixLedger=new DirectPurchaseLedger(new ProfileService(new MemoryProfileRepository(p)));
                    var matrixStore=new FakeStore{doubleCallback=true};var matrixFlow=Ready(matrixLedger,matrixStore);bool matrixOk=false;
                    matrixFlow.Buy(offer.id,(ok,error)=>matrixOk=ok);var after=matrixLedger.Read();
                    Check(matrixOk&&after.coins==1250+offer.grant.coins&&after.directPurchaseReceipts.Count==1&&matrixStore.ackCalls==1,"ProductCreditsOnce_"+offer.id);
                    Check(after.starting.SequenceEqual(stock.Select((n,index)=>n+offer.grant.starting[index]))&&
                        after.tools.SequenceEqual(new[]{3,3,3,3}.Select((n,index)=>n+offer.grant.tools[index])),"FullGrant_"+offer.id);
                }
                var failedRepository=new FileProfileRepository(Path.Combine(root,"atomic"),()=>PlayerProfile.New(new[]{5,5,3,2}));
                var atomicLedger=new DirectPurchaseLedger(new ProfileService(failedRepository));var atomicStore=new FakeStore();var atomicFlow=Ready(atomicLedger,atomicStore);
                failedRepository.Checkpoint=phase=>{if(phase=="TempFlushed")throw new IOException("SyntheticPowerLossBeforeCommit");};
                atomicFlow.Buy("coins-1000",(ok,error)=>Check(!ok&&error=="PurchaseJournalUnavailable","IntentWriteFailureStopsSdk"));
                Check(atomicStore.purchaseCalls==0&&atomicLedger.Read().directPurchaseReceipts.Count==0,"NoPaymentBeforeDurableDispatch");
                failedRepository.Checkpoint=null;
                atomicFlow.Recover((ok,error)=>Check(ok,"UnsentIntentClearedOnRecovery"));
                Check(atomicLedger.Pending()==null&&atomicStore.purchaseCalls==0,"UnsentRecoveryCannotStartPayment");
                var secondRepository=new FileProfileRepository(Path.Combine(root,"second-commit"),()=>PlayerProfile.New(new[]{5,5,3,2}));
                var secondLedger=new DirectPurchaseLedger(new ProfileService(secondRepository));var secondStore=new FakeStore();var secondFlow=Ready(secondLedger,secondStore);
                int flushed=0;secondRepository.Checkpoint=phase=>{if(phase=="TempFlushed"&&++flushed==2)throw new IOException("SyntheticDispatchCommitFailure");};
                secondFlow.Buy("coins-1000",(ok,error)=>Check(!ok&&error=="PurchaseJournalUnavailable","DispatchWriteFailureStopsSdk"));
                Check(secondStore.purchaseCalls==0&&secondLedger.Pending()?.phase=="Intent","DurableUnsentIntentRetained");
                secondRepository.Checkpoint=null;secondFlow.Recover((ok,error)=>Check(ok,"DurableUnsentIntentRecovered"));
                Check(secondLedger.Pending()==null,"RecoveredIntentClosedWithoutCharge");
                var mismatchReceipt=new FakeStore{observedPriceDelta=100};var mismatchLedger=new DirectPurchaseLedger(new ProfileService(new MemoryProfileRepository(PlayerProfile.New(new[]{5,5,3,2}))));
                var mismatchReceiptFlow=Ready(mismatchLedger,mismatchReceipt);mismatchReceiptFlow.Buy("coins-1000",(ok,error)=>Check(!ok&&error=="PurchaseNotConfirmed","ObservedPriceMismatchBlocked"));
                Check(mismatchLedger.Read().directPurchaseReceipts.Count==0,"PriceMismatchNoReceipt");
                mismatchReceipt.observedPriceDelta=0;mismatchReceiptFlow.Recover((ok,error)=>Check(ok,"CorrectedFreshObservationCredits"));
                var cancelled=new FakeStore{status="CANCELLED"};var cancelledLedger=new DirectPurchaseLedger(new ProfileService(new MemoryProfileRepository(PlayerProfile.New(new[]{5,5,3,2}))));
                var cancelledFlow=Ready(cancelledLedger,cancelled);cancelledFlow.Buy("coins-5000",(ok,error)=>Check(!ok&&error=="PurchaseNotCompleted","BoundCancellation"));
                Check(cancelledLedger.Read().coins==1250&&cancelledLedger.Pending()==null&&cancelledLedger.Read().directPurchaseReceipts.Count==0,"CancellationNoGrantAndClosesIntent");
                var conflictingLedger=new DirectPurchaseLedger(new ProfileService(new MemoryProfileRepository(PlayerProfile.New(new[]{5,5,3,2}))));
                var conflicting=conflictingLedger.Begin(DirectPurchaseCatalog.Find("coins-1000"),true);conflictingLedger.MarkDispatched(conflicting.orderId);
                string originalId=Guid.NewGuid().ToString("D");conflictingLedger.MarkUnknown(conflicting.orderId,originalId);
                var otherCancellation=new PayPurchase(new PayLocator(Guid.NewGuid().ToString("D"),"123456",conflicting.orderId,conflicting.storeProductId,1,true),
                    conflicting.developerPayload,"CANCELLED","ONE_STEP","NOT_ACKNOWLEDGED");
                bool wrongCancellationBlocked=false;try{conflictingLedger.MarkTerminal(conflicting.orderId,otherCancellation);}catch(InvalidOperationException){wrongCancellationBlocked=true;}
                Check(wrongCancellationBlocked&&conflictingLedger.Pending().purchaseId==originalId,"OtherPurchaseCannotClosePendingIntent");
                var wallet=new RuStoreServerWallet{playerId=Guid.NewGuid().ToString("N"),coins=850,stars=7,lives=3,maxLives=5,
                    completed=2,currentLevel=3,starting=new[]{4,5,6,7},tools=new[]{1,2,3,4},nextLifeAt=123456};
                var migrated=DirectEconomyMigration132.Create(wallet,true,false);
                Check(migrated.playerId==wallet.playerId&&migrated.coins==850&&migrated.completed==2&&migrated.currentLevel==3&&
                    migrated.starting.SequenceEqual(wallet.starting)&&migrated.tools.SequenceEqual(wallet.tools)&&migrated.livesRefillDueUnix==wallet.nextLifeAt,"ExactWalletCutover");
                bool blocked=false;try{DirectEconomyMigration132.Create(wallet,false,false);}catch(InvalidOperationException){blocked=true;}Check(blocked,"NoOfflineFirstCutover");
                blocked=false;try{DirectEconomyMigration132.Create(wallet,true,true);}catch(InvalidOperationException){blocked=true;}Check(blocked,"NoCutoverDuringAttempt");
                string output=Environment.GetEnvironmentVariable("HOTR_DIRECT132_OUT");if(!string.IsNullOrEmpty(output))File.WriteAllText(output,JsonUtility.ToJson(new Result{status="PASS",checks=checks}));
                Debug.Log("HOTR DirectPurchase132 PASS "+checks);
            }finally{if(Directory.Exists(root))Directory.Delete(root,true);}
        }
        [Serializable] sealed class Result {public string status;public int checks;}
    }
}
#endif

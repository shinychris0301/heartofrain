#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using HeartOfTheRain.App.Advertising;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.RuStore.Editor;
using HeartOfTheRain.App.ShopCheckout86;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.App.ServerGameplay.Editor {
    public static class ProductionClient122Verification {
        [Serializable] sealed class Report {
            public string status,unity,utc;
            public int checks,cases;
            public bool actualUnityEditor=true,actualAndroid=false,providerAcceptanceVerified=false,productionActivated=false;
            public List<string> passed=new List<string>(),errors=new List<string>();
        }
        const string Origin="https://api.novamind-it.ru",Package="com.heartoftherain.productionfixture";
        const string Player="11111111111111111111111111111111",OrderId="22222222222222222222222222222222",Command="33333333333333333333333333333333";
        static Report report;
        static string Profile=>"{\"version\":2,\"mode\":\"ManagedGuestServer\",\"runtimeMode\":\"production\",\"origin\":\""+Origin+"\",\"identityScope\":\"prod-fixture122\",\"packageName\":\""+Package+"\",\"consoleAppId\":\"12345\",\"socialEnabled\":true,\"allowDevelopmentLoopback\":false}";
        static string Checkout=>"{\"version\":2,\"enabled\":true,\"sandbox\":false,\"consoleAppId\":\"12345\",\"runtimeMode\":\"production\",\"packageName\":\""+Package+"\",\"backendOrigin\":\""+Origin+"\"}";
        static string Wallet=>"{\"playerId\":\""+Player+"\",\"balanceScope\":\"server_wallet\",\"initialized\":true,\"refundReviewRequired\":false,\"productionEnabled\":true,\"normalUnityProfileIntegrated\":false,\"localProfileMutated\":false,\"revision\":1,\"coins\":1250,\"stars\":0,\"lives\":5,\"maxLives\":5,\"completed\":0,\"currentLevel\":1,\"serverUtc\":1000,\"nextLifeAt\":0,\"starting\":[0,0,0,0],\"tools\":[0,0,0,0],\"activeAttempt\":null}";
        static string Catalog=>"{\"version\":\"fixture122\",\"balanceScope\":\"server_wallet\",\"reason\":\"ready\",\"enabled\":true,\"sandbox\":false,\"productionEnabled\":true,\"serverWalletProjection\":true,\"normalUnityProfileIntegrated\":false,\"fullGameplayWallet\":true,\"appId\":12345,\"products\":[{\"id\":\"coins-1000\",\"storeProductId\":\"hotr_coins_1000\",\"currency\":\"RUB\",\"coins\":1000,\"amountMinor\":9900,\"quantity\":1}]}";
        static string Order=>"{\"orderId\":\""+OrderId+"\",\"playerId\":\""+Player+"\",\"state\":\"Created\",\"catalogVersion\":\"fixture122\",\"productId\":\"coins-1000\",\"currency\":\"RUB\",\"invoiceId\":null,\"purchaseId\":null,\"deliveryAcknowledgement\":null,\"balanceScope\":\"server_wallet\",\"coins\":1000,\"amountMinor\":9900,\"productionEnabled\":true,\"availableToSpend\":false,\"availableInServerWallet\":false,\"normalUnityProfileIntegrated\":false,\"localProfileMutated\":false,\"sdk\":{\"orderId\":\""+OrderId+"\",\"productId\":\"hotr_coins_1000\",\"appUserId\":\""+Player+"\",\"developerPayload\":\"hotr-order-v1:"+OrderId+":"+Command+"\",\"quantity\":1,\"sandbox\":false},\"credit\":null}";
        static void Check(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);}
        static void Reject(Action call,string label){bool failed=false;try{call();}catch(Exception){failed=true;}Check(failed,label);}
        static void Case(string name,Action call){report.cases++;try{call();report.passed.Add(name);}catch(Exception error){report.errors.Add(name+":"+error.GetType().Name+":"+error.Message);}}
        static object Invoke(object owner,string name,params object[] values){var method=owner.GetType().GetMethod(name,BindingFlags.Instance|BindingFlags.NonPublic);if(method==null)throw new MissingMethodException(name);return method.Invoke(owner,values);}
        static RuStoreBackendClient Client(bool production)=>new RuStoreBackendClient(Origin,new string('t',43),Player,true,false,r=>{},production,production?12345:0);
        static string Stage(string json)=>json.Replace("\"productionEnabled\":true","\"productionEnabled\":false");
        static void Profiles(){
            var config=ServerProductionConfiguration122.Parse(Profile);Check(config.productionEnabled&&config.consoleAppId=="12345"&&config.origin==Origin,"ProductionPublicProfileBound");
            Reject(()=>ServerProductionConfiguration122.Parse(Profile.Replace(Package,"com.heartoftherain.verification")),"VerificationPackageCannotBypassReleaseAcceptanceGuard");
            foreach(string bad in new[]{Profile.Replace("\"version\":2","\"version\":true"),Profile.Replace("\"production\"","\"staging\""),Profile.Replace("prod-fixture122","review-fixture122"),Profile.Replace("\"12345\"","\"0\""),Profile.Replace("\"12345\"","12345"),Profile.Replace("\"allowDevelopmentLoopback\":false","\"allowDevelopmentLoopback\":true"),Profile.Replace(Origin,"http://127.0.0.1"),Profile.Replace(Origin,Origin+"/api"),Profile.Replace("\"socialEnabled\":true","\"socialEnabled\":\"true\""),Profile.Replace("\"version\":2","\"secret\":\"fixture\",\"version\":2"),Profile.Replace("\"version\":2","\"version\":2,\"version\":2")})Reject(()=>ServerProductionConfiguration122.Parse(bad),"RejectInvalidProductionProfile");
            var legacy=ServerGameplayConfiguration.Parse("{\"version\":1,\"mode\":\"ManagedGuestServer\",\"origin\":\""+Origin+"\",\"identityScope\":\"review-fixture122\",\"allowDevelopmentLoopback\":false,\"socialEnabled\":true}");
            Check(!legacy.productionEnabled&&legacy.consoleAppId==null,"LegacyStagingDefaultPreserved");Check(!JsonUtility.ToJson(legacy).Contains("productionEnabled"),"LegacyCanonicalFieldSetPreserved");
        }
        static void Selection(){
            ServerGameplayConfiguration value;string why;var absent=ServerConfigurationInput104.Absent;var valid=new ServerConfigurationInput104(true,Profile);
            Check(!ServerProductionConfiguration122.Resolve(false,Package,absent,false,out value,out why)&&value==null&&why==null,"AbsentOptionalProfileLeavesLegacySelection");
            Check(ServerProductionConfiguration122.Resolve(true,Package,absent,false,out value,out why)&&value==null&&why!=null,"RequiredMissingProfileBlocksFallback");
            Check(ServerProductionConfiguration122.Resolve(false,Package,valid,false,out value,out why)&&value!=null&&why==null,"PackagedProductionSelectedWithoutDevelopmentRequirement");
            foreach(var package in new[]{"com.other.app",ServerStagingConfiguration104.PackageName})Check(ServerProductionConfiguration122.Resolve(false,package,valid,false,out value,out why)&&value==null&&why!=null,"ForeignPackageBlocks");
            Check(ServerProductionConfiguration122.Resolve(false,Package,valid,true,out value,out why)&&value==null,"MixedStagingAndProductionBlocked");
            Check(ServerProductionConfiguration122.Resolve(false,Package,ServerConfigurationInput104.Invalid,false,out value,out why)&&value==null,"InvalidPresentProfileBlocksFallback");
        }
        static void WithPackagedResource(string path,string json,Action action){
            string expected=Environment.GetEnvironmentVariable("HOTR_REVIEW122_ISOLATED_PROJECT");
            if(string.IsNullOrEmpty(expected)||Path.GetFullPath(".")!=Path.GetFullPath(expected))throw new InvalidOperationException("IsolatedSourceProjectRequired");
            string folder=Path.GetDirectoryName(path),folderMeta=folder+".meta",meta=path+".meta";
            if(File.Exists(path)||File.Exists(meta))throw new InvalidOperationException("FreshPackagedFixtureRequired");
            bool folderExisted=Directory.Exists(folder),folderMetaExisted=File.Exists(folderMeta);byte[] oldFolderMeta=folderMetaExisted?File.ReadAllBytes(folderMeta):null;
            string guid=Guid.NewGuid().ToString("N");byte[] bytes=new UTF8Encoding(false).GetBytes(json);
            Directory.CreateDirectory(folder);File.WriteAllBytes(path,bytes);
            File.WriteAllText(meta,"fileFormatVersion: 2\nguid: "+guid+"\nTextScriptImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n",new UTF8Encoding(false));
            try{AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport|ImportAssetOptions.ForceUpdate);action();}
            finally{
                if(!File.ReadAllBytes(path).SequenceEqual(bytes)||!File.ReadAllText(meta).Contains("guid: "+guid))throw new InvalidOperationException("PackagedFixtureChangedConcurrently");
                AssetDatabase.DeleteAsset(path);
                if(!folderExisted){if(Directory.Exists(folder)&&Directory.GetFileSystemEntries(folder).Length==0)Directory.Delete(folder);else throw new InvalidOperationException("FixtureFolderNotEmpty");}
                if(folderMetaExisted){if(!File.ReadAllBytes(folderMeta).SequenceEqual(oldFolderMeta))throw new InvalidOperationException("ExistingFolderMetaChanged");}
                else if(!folderExisted&&File.Exists(folderMeta))File.Delete(folderMeta);
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            }
        }
        static void ActualPackagedReaders(){
            string serverOverride=Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG"),checkoutOverride=Environment.GetEnvironmentVariable("HOTR_SHOP_CHECKOUT86_CONFIG");
            try{
                Check(Application.identifier==Package,"IsolatedEditorPackageSelection");
                Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",Path.Combine(Path.GetTempPath(),Guid.NewGuid().ToString("N"),"absent.json"));
                Environment.SetEnvironmentVariable("HOTR_SHOP_CHECKOUT86_CONFIG",Path.Combine(Path.GetTempPath(),Guid.NewGuid().ToString("N"),"absent.json"));
                WithPackagedResource(ServerProductionConfiguration122.ResourceAssetPath,Profile,()=>{
                    var imported=ServerProductionConfiguration122.ReadResource(ServerProductionConfiguration122.ResourceKey);Check(imported.present&&!imported.failed,"ActualImportedProductionTextResource");
                    ServerGameplayConfiguration value;string why;
                    Check(ServerGameplayConfiguration.TryRead(out value,out why)&&value!=null&&value.productionEnabled&&why==null,"ActualResourcesReaderIgnoresExternalReviewOverride:"+(why??"none"));
                    WithPackagedResource(ServerProductionConfiguration122.CheckoutResourceAssetPath,Checkout,()=>{
                        CheckoutConfiguration86 checkout;Check(CheckoutConfiguration86.TryRead(out checkout)&&checkout!=null&&checkout.productionEnabled&&!checkout.sandbox,"ActualCheckoutResourceIgnoresDeviceOverride");
                    });
                    CheckoutConfiguration86 missing;Check(!CheckoutConfiguration86.TryRead(out missing)&&missing==null,"MissingProductionCheckoutNeverFallsBackToDeviceFile");
                });
            }finally{Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",serverOverride);Environment.SetEnvironmentVariable("HOTR_SHOP_CHECKOUT86_CONFIG",checkoutOverride);}
        }
        static void CheckoutBinding(){
            var server=ServerProductionConfiguration122.Parse(Profile);var config=CheckoutConfiguration86.ParseProduction122(Checkout,server,Package);Check(CheckoutConfiguration86.Valid(config)&&!config.sandbox&&config.productionEnabled,"ProductionCheckoutBound");
            foreach(string bad in new[]{Checkout.Replace("12345","12346"),Checkout.Replace(Origin,"https://different.novamind-it.ru"),Checkout.Replace(Package,"com.other.app"),Checkout.Replace("\"sandbox\":false","\"sandbox\":true"),Checkout.Replace("\"production\"","\"sandbox\""),Checkout.Replace("\"version\":2","\"version\":1"),Checkout.Replace("\"enabled\":true","\"enabled\":\"true\""),Checkout.Replace("\"version\":2","\"privateKey\":\"fixture\",\"version\":2")})Reject(()=>CheckoutConfiguration86.ParseProduction122(bad,server,Package),"MixedCheckoutBindingRejected");
            Reject(()=>CheckoutConfiguration86.ParseProduction122(Checkout,new ServerGameplayConfiguration(),Package),"CheckoutNeedsProductionServer");
            var legacy=new CheckoutConfiguration86{version=1,enabled=true,sandbox=true,consoleAppId="12345"};Check(CheckoutConfiguration86.Valid(legacy),"LegacyCheckoutRemainsValid");legacy.sandbox=false;Check(!CheckoutConfiguration86.Valid(legacy),"DeviceLegacyFileCannotSelectProduction");
        }
        static void WalletsAndCatalogs(){
            using(var live=Client(true))using(var staging=Client(false)){
                Check(((RuStoreServerWallet)Invoke(live,"ReadWallet",Wallet)).productionEnabled,"ProductionWalletAccepted");
                Reject(()=>Invoke(staging,"ReadWallet",Wallet),"StagingRejectsProductionWallet");Reject(()=>Invoke(live,"ReadWallet",Stage(Wallet)),"ProductionRejectsStagingWallet");
                Check(!((RuStoreServerWallet)Invoke(staging,"ReadWallet",Stage(Wallet))).productionEnabled,"StagingWalletStillAccepted");
                Check(live.VerificationParseCatalog(Catalog).appId==12345,"ProductionCatalogAccepted");
                foreach(string bad in new[]{Catalog.Replace("12345","12346"),Stage(Catalog),Catalog.Replace("\"sandbox\":false","\"sandbox\":true"),Catalog.Replace("\"fullGameplayWallet\":true","\"fullGameplayWallet\":false")})Reject(()=>live.VerificationParseCatalog(bad),"ProductionCatalogMixedPolicyRejected");
                Reject(()=>staging.VerificationParseCatalog(Catalog),"StagingRejectsProductionCatalog");
            }
            Reject(()=>new RuStoreBackendClient(Origin,new string('t',43),Player,true,false,r=>{},true),"ProductionClientNeedsConsoleAppBinding");
            Reject(()=>new RuStoreBackendClient("http://127.0.0.1:8751",new string('t',43),Player,true,true,r=>{},true,12345),"ProductionClientRejectsLoopback");
        }
        static void OrdersAndPending(){
            using(var live=Client(true))using(var staging=Client(false)){
                var order=(RuStoreServerOrder)Invoke(live,"Order",Order,null,null,null);Check(!order.Request().sandbox&&order.productionEnabled,"ProductionOrderAccepted");
                Reject(()=>Invoke(staging,"Order",Order,null,null,null),"StagingRejectsProductionOrder");
                Reject(()=>Invoke(live,"Order",Stage(Order),null,null,null),"ProductionRejectsStagingOrderFlag");
                Reject(()=>Invoke(live,"Order",Order.Replace("\"sandbox\":false","\"sandbox\":true"),null,null,null),"ProductionRejectsSandboxSdkOrder");
                var quote=new CheckoutQuote86(CheckoutCatalogRules86.FrozenProduct(order),"99 RUB");Check(CheckoutCatalogRules86.Order(order,quote,Player,true),"ProductionFrozenOrderTermsAccepted");Check(!CheckoutCatalogRules86.Order(order,quote,Player),"DefaultFrozenTermsRejectLiveEnvironment");
                string pending="{\"playerId\":\""+Player+"\",\"nextCursor\":1,\"hasMore\":false,\"productionEnabled\":true,\"orders\":["+Order+"]}";
                Check(((RuStorePendingOrders100)Invoke(live,"ParsePendingOrders122",pending,0L)).orders.Length==1,"ProductionPendingRecoveryAccepted");
                Reject(()=>Invoke(staging,"ParsePendingOrders122",pending,0L),"StagingRejectsLivePending");
                Reject(()=>Invoke(live,"ParsePendingOrders122",Stage(pending),0L),"ProductionRejectsMixedPending");
                string terminal=Order.Replace("\"Created\"","\"Cancelled\"").Replace("\"invoiceId\":null","\"invoiceId\":\"123\"").Replace("\"purchaseId\":null","\"purchaseId\":\"purchase122\"");
                var observed=new PayPurchase(new PayLocator("purchase122","123",OrderId,"hotr_coins_1000",1,false),order.Request().developerPayload,"CANCELLED","ONE_STEP","NOT_ACKNOWLEDGED");
                Check(((PayTerminalReceipt)Invoke(live,"ParseTerminalOrder",terminal,order.Request(),observed)).noCredit,"ProductionTerminalRecoveryUsesServerProof");
            }
        }
        static void IdentityAndBroker(){
            string identity="{\"productionEnabled\":true,\"normalUnityProfileIntegrated\":false}";
            using(var live=new IdentityHttpTransport82(Origin,r=>{},false,true))using(var staging=new IdentityHttpTransport82(Origin,r=>{})){
                Check(((IdentitySessionResponse82)Invoke(live,"ParseSessionResponse122",identity)).productionEnabled,"IdentityAndVkSharedProductionReaderAccepted");
                Reject(()=>Invoke(staging,"ParseSessionResponse122",identity),"StagingIdentityRejectsLive");Reject(()=>Invoke(live,"ParseSessionResponse122",Stage(identity)),"ProductionIdentityRejectsStaging");
                Reject(()=>Invoke(live,"ParseSessionResponse122",identity.Replace("\"productionEnabled\":true","\"productionEnabled\":\"true\"")),"IdentityFlagMustBeBoolean");
            }
            string operation="{\"operationId\":\""+Command+"\",\"attemptId\":\""+OrderId+"\",\"state\":\"Pending\",\"code\":\"worker_pending\",\"paidReceiptId\":\"\",\"prefixRevision\":0,\"acceptedActions\":0,\"addedMoves\":0,\"model\":null,\"wallet\":"+Wallet+",\"attempt\":null,\"displayReceipt\":null,\"productionEnabled\":true,\"acknowledgementRequired\":false}";
            using(var live=new ServerGameplayBrokerClient(Origin,Player,()=>new string('t',43),r=>{},false,true))using(var staging=new ServerGameplayBrokerClient(Origin,Player,()=>new string('t',43),r=>{})){
                Check(((ServerBrokerOperation)Invoke(live,"Parse",operation,OrderId,Command)).wallet.productionEnabled,"BrokerOuterAndNestedWalletProductionAccepted");
                Reject(()=>Invoke(staging,"Parse",operation,OrderId,Command),"StagingBrokerRejectsLive");Reject(()=>Invoke(live,"Parse",operation.Replace(Wallet,Stage(Wallet)),OrderId,Command),"BrokerRejectsMixedNestedWallet");
            }
        }
        static void AdsAndBuildPolicy(){
            string status="{\"enabled\":false,\"available\":false,\"productionEnabled\":true,\"reason\":\"ads_disabled\",\"completionMode\":\"sdk_client_reported_capped\",\"verificationMode\":\"sdk_client_reported_capped\",\"placement\":\"shop_rewarded\",\"configVersion\":\"rewarded-shop-v1\",\"rewardCoins\":400,\"dailyLimit\":3,\"utcOffsetSeconds\":36000,\"cooldownSeconds\":600,\"serverUtc\":1000,\"day\":0,\"claimedToday\":0,\"remainingToday\":3,\"cooldownRemainingSeconds\":0,\"nextEligibleAt\":1000,\"nextDayAt\":50400,\"activeOpportunity\":null}";
            Check(RewardedAdsClient85.ParseStatus(status,Player,true).productionEnabled,"AdStatusProductionPolicyAcceptedWithoutEnablingAds");Reject(()=>RewardedAdsClient85.ParseStatus(status,Player),"DefaultAdParserRejectsLive");Reject(()=>RewardedAdsClient85.ParseStatus(Stage(status),Player,true),"LiveAdParserRejectsStaging");
            var server=new ServerConfigurationInput104(true,Profile);var checkout=new ServerConfigurationInput104(true,Checkout);var defines=new[]{"HOTR_PRODUCTION122","HOTR_RUSTORE_PAY"};
            Check(ProductionBuildConfiguration122.Validate(true,false,true,26,Package,defines,server,checkout,false).Length==0,"NonDevelopmentAndroidProductionPolicyAccepted");
            Check(ProductionBuildConfiguration122.Validate(false,false,true,26,Package,defines,server,checkout,false).Length>0,"ProductionPlatformGuard");
            Check(ProductionBuildConfiguration122.Validate(true,true,true,26,Package,defines,server,checkout,false).Length>0,"DevelopmentOptionsGuard");
            Check(ProductionBuildConfiguration122.Validate(true,false,false,26,Package,defines,server,checkout,false).Length>0,"ReleaseSignerGuard");
            Check(ProductionBuildConfiguration122.Validate(true,false,true,22,Package,defines,server,checkout,false).Length>0,"ProtectedIdentityApiGuard");
            Check(ProductionBuildConfiguration122.Validate(true,false,true,26,Package,new[]{"HOTR_RUSTORE_PAY"},server,checkout,false).Length>0,"ProductionDefineGuard");
            Check(ProductionBuildConfiguration122.Validate(true,false,true,26,Package,new[]{"HOTR_PRODUCTION122"},server,checkout,false).Length>0,"RuStoreSdkGuard");
        }
        static void ReleaseDiagnostics(){
            var server=new ServerConfigurationInput104(true,Profile);var checkout=new ServerConfigurationInput104(true,Checkout);
            var release=new RuStoreReleaseConfiguration{schemaVersion=1,packageName=Package,consoleApplicationId="12345",paymentReturnScheme="heartoftherain-pay",backendOrigin=Origin,
                privacyPolicyUrl="https://legal.hotr-fixture-provider.net/privacy",supportUrl="https://legal.hotr-fixture-provider.net/support",termsUrl="https://legal.hotr-fixture-provider.net/terms",
                minimumApiLevel=26,targetApiLevel=35,versionCode=1,signingCertificateSha256=string.Concat(Enumerable.Repeat("ab",32)),environment="production"};
            Check(RuStoreReleasePreflight.Validate(release).Count==0,"NativeCanonicalReleaseSyntaxControl");
            var configured=RuStoreReleasePreflight.IntegrationBlockers122(release,Package,server,checkout,false);
            Check(configured.Contains("configured_production_identity_and_wallet_android_acceptance_required"),"ConfiguredCodeRequiresActualProductionAndroidAcceptance");
            Check(!configured.Contains("production_identity_and_secure_credential_recovery_not_connected")&&!configured.Contains("unified_server_gameplay_wallet_not_connected"),"ConfiguredProductionRemovesObsoleteOfflineDiagnostics");
            foreach(string code in new[]{"provider_notification_authentication_not_configured","native_sandbox_and_external_bank_return_not_verified","production_signing_and_legal_hosting_review_not_complete"})Check(configured.Contains(code),"ProviderSigningLegalAndBankReturnGatesRemain");
            var absent=RuStoreReleasePreflight.IntegrationBlockers122(release,Package,ServerConfigurationInput104.Absent,ServerConfigurationInput104.Absent,false);
            Check(absent.Contains("production_identity_and_secure_credential_recovery_not_connected")&&absent.Contains("unified_server_gameplay_wallet_not_connected"),"DefaultUnconfiguredDiagnosticsUnchanged");
            foreach(string mode in new[]{"sandbox","invalid"}){release.environment=mode;Check(!RuStoreReleasePreflight.IntegrationBlockers122(release,Package,server,checkout,false).Contains("configured_production_identity_and_wallet_android_acceptance_required"),"ReleaseEnvironmentMustMatchProduction");}release.environment="production";
            release.consoleApplicationId="12346";Check(!RuStoreReleasePreflight.IntegrationBlockers122(release,Package,server,checkout,false).Contains("configured_production_identity_and_wallet_android_acceptance_required"),"ReleaseAppBindingMismatchDoesNotHideLegacyDiagnostic");release.consoleApplicationId="12345";
            Check(!RuStoreReleasePreflight.IntegrationBlockers122(release,Package,server,checkout,true).Contains("configured_production_identity_and_wallet_android_acceptance_required"),"MixedResourceProfileCannotClaimConfigured");
            Check(!RuStoreReleasePreflight.IntegrationBlockers122(release,"com.other.app",server,checkout,false).Contains("configured_production_identity_and_wallet_android_acceptance_required"),"ForeignPackageCannotClaimConfigured");
        }
        public static void Run(){
            report=new Report{status="FAIL_NATIVE_PRODUCTION_CLIENT122",unity=Application.unityVersion,utc=DateTime.UtcNow.ToString("o")};
            Case("PinnedUnity",()=>Check(Application.unityVersion=="2022.3.62f3","PinnedMainEngine"));
            Case("StrictProductionProfile",Profiles);Case("PackagedSelectionAndFallbackGuards",Selection);Case("CheckoutPublicBinding",CheckoutBinding);Case("ActualPackagedResourceReaders",ActualPackagedReaders);
            Case("WalletAndCatalogEnvironment",WalletsAndCatalogs);Case("FrozenOrdersPendingAndTerminalRecovery",OrdersAndPending);Case("IdentityVkAndNestedBrokerPolicy",IdentityAndBroker);Case("AdvertisingAndNonDevelopmentBuildPolicy",AdsAndBuildPolicy);Case("AccurateReleaseIntegrationDiagnostics",ReleaseDiagnostics);
            if(report.errors.Count==0)report.status="PASS_NATIVE_PRODUCTION_CLIENT122";
            string output=Environment.GetEnvironmentVariable("HOTR_REVIEW122_OUT");if(string.IsNullOrEmpty(output))throw new InvalidOperationException("Review122OutputRequired");Directory.CreateDirectory(output);
            using(var stream=new FileStream(Path.Combine(output,"ProductionClient122.json"),FileMode.CreateNew,FileAccess.Write))using(var writer=new StreamWriter(stream,new UTF8Encoding(false)))writer.Write(JsonUtility.ToJson(report,true));
            if(Application.isBatchMode)EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif

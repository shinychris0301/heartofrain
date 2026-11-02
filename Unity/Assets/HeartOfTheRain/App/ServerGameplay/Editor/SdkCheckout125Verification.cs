#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using HeartOfTheRain.App.OnlineIdentity;
using System.Text.RegularExpressions;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.RuStore.Editor;
using HeartOfTheRain.App.ShopCheckout86;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.App.ServerGameplay.Editor {
    public static class SdkCheckout125Verification {
        [Serializable] sealed class Report {
            public string status,unity,utc;
            public int checks,cases;
            public bool actualUnityEditor=true,actualEncryptedCas=true,actualHttp=false,actualSdk=false,actualAndroid=false,providerAcceptanceVerified=false,productionActivated=false;
            public string scope="Native Editor strict configuration/DTO/report/journal/build policy checks with explicit synthetic fixtures. No SDK payment, network, APK, provider acceptance or service activation.";
            public List<string> passed=new List<string>(),errors=new List<string>();
        }
        const string Origin="https://api.novamind-it.ru",Package="com.heartoftherain.productionfixture",Player="11111111111111111111111111111111",OrderId="22222222222222222222222222222222",Command="33333333333333333333333333333333",Purchase="aabbccdd-1111-4111-8111-111111111111";
        static Report report;static string privateRoot;
        static string Profile=>"{\"version\":2,\"mode\":\"ManagedGuestServer\",\"runtimeMode\":\"production\",\"origin\":\""+Origin+"\",\"identityScope\":\"prod-sdk125\",\"packageName\":\""+Package+"\",\"consoleAppId\":\"12345\",\"socialEnabled\":true,\"allowDevelopmentLoopback\":false}";
        static string Stage=>"{\"version\":1,\"mode\":\"ManagedGuestServer\",\"origin\":\""+Origin+"\",\"identityScope\":\"review-sdk125\",\"allowDevelopmentLoopback\":false,\"socialEnabled\":true}";
        static string Sdk(bool production=true)=>"{\"version\":1,\"enabled\":true,\"verificationMode\":\"sdk_client_reported\",\"sandbox\":"+(production?"false":"true")+",\"consoleAppId\":\"12345\",\"runtimeMode\":\""+(production?"production":"staging")+"\",\"packageName\":\""+Package+"\",\"backendOrigin\":\""+Origin+"\"}";
        static string Catalog=>"{\"verificationMode\":\"sdk_client_reported\",\"version\":\"sdk125\",\"balanceScope\":\"server_wallet\",\"reason\":\"ready\",\"enabled\":true,\"sandbox\":false,\"productionEnabled\":true,\"serverWalletProjection\":true,\"normalUnityProfileIntegrated\":false,\"fullGameplayWallet\":true,\"appId\":12345,\"products\":[{\"id\":\"coins-1000\",\"storeProductId\":\"hotr_coins_1000\",\"currency\":\"RUB\",\"coins\":1000,\"amountMinor\":9900,\"quantity\":1}]}";
        static string Order=>"{\"verificationMode\":\"sdk_client_reported\",\"orderId\":\""+OrderId+"\",\"playerId\":\""+Player+"\",\"state\":\"Created\",\"catalogVersion\":\"sdk125\",\"productId\":\"coins-1000\",\"currency\":\"RUB\",\"invoiceId\":null,\"purchaseId\":null,\"deliveryAcknowledgement\":null,\"balanceScope\":\"server_wallet\",\"coins\":1000,\"amountMinor\":9900,\"productionEnabled\":true,\"availableToSpend\":false,\"availableInServerWallet\":false,\"normalUnityProfileIntegrated\":false,\"localProfileMutated\":false,\"sdk\":{\"orderId\":\""+OrderId+"\",\"productId\":\"hotr_coins_1000\",\"appUserId\":\""+Player+"\",\"developerPayload\":\"hotr-order-v1:"+OrderId+":"+Command+"\",\"quantity\":1,\"sandbox\":false},\"credit\":null}";
        static string Confirmed=>Order.Replace("\"state\":\"Created\"","\"state\":\"Confirmed\"").Replace("\"invoiceId\":null","\"invoiceId\":\"125001\"").Replace("\"purchaseId\":null","\"purchaseId\":\""+Purchase+"\"").Replace("\"availableToSpend\":false","\"availableToSpend\":true").Replace("\"availableInServerWallet\":false","\"availableInServerWallet\":true").Replace("\"credit\":null","\"credit\":{\"verificationMode\":\"sdk_client_reported\",\"receiptId\":\"credit125\",\"balanceScope\":\"commerce_receipt_audit\",\"coins\":1000,\"createdAt\":1000}");
        static ServerConfigurationInput104 Input(string json)=>new ServerConfigurationInput104(true,json);
        static void Check(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);}
        static void Reject(Action call,string label){bool rejected=false;try{call();}catch{rejected=true;}Check(rejected,label);}
        static void Case(string label,Action call){report.cases++;try{call();report.passed.Add(label);}catch(Exception error){report.errors.Add(label+":"+error.GetType().Name+":"+error.Message);}}
        static RuStoreBackendClient Client(string mode=CommerceVerification125.SdkClientReported)=>new RuStoreBackendClient(Origin,new string('t',43),Player,true,false,r=>{},true,12345,mode);
        static CheckoutConfiguration86 Config()=>CheckoutSdkConfiguration125.Parse(Sdk(),ServerProductionConfiguration122.Parse(Profile),Package);
        static PayRequest Request()=>new PayRequest(OrderId,"hotr_coins_1000",Player,"hotr-order-v1:"+OrderId+":"+Command,1,false);
        static PayPurchase Observed(string status="CONFIRMED",string type="ONE_STEP",string ack="PENDING",long? amount=9900,string currency="RUB",string purchase=Purchase)=>new PayPurchase(new PayLocator(purchase,"125001",OrderId,"hotr_coins_1000",1,false),Request().developerPayload,status,type,ack,"CONSUMABLE_PRODUCT",amount,currency);
        static void Profiles(){
            var absent=ServerConfigurationInput104.Absent;ServerGameplayConfiguration selected;string why;
            Check(CheckoutSdkConfiguration125.Resolve(false,Package,absent,absent,absent,absent,out selected,out why)==false,"AbsentSdkLeavesLegacySelection");
            Check(CheckoutSdkConfiguration125.Resolve(true,Package,absent,absent,absent,absent,out selected,out why)&&selected==null&&why!=null,"RequiredMissingSdkBlocksFallback");
            Check(CheckoutSdkConfiguration125.Resolve(false,Package,Input(Sdk()),Input(Profile),absent,absent,out selected,out why)&&selected!=null&&selected.productionEnabled,"StrictProductionManagedSelection");
            var config=CheckoutSdkConfiguration125.Parse(Sdk(),selected,Package);Check(CheckoutConfiguration86.Valid(config)&&config.Verification==CommerceVerificationMode125.SdkClientReported,"ExplicitSdkTrustMetadata");
            Check(CheckoutSdkConfiguration125.Resolve(false,Package,Input(Sdk(false)),absent,Input(Stage),absent,out selected,out why)&&selected!=null&&!selected.productionEnabled&&!selected.allowDevelopmentLoopback,"StrictStagingManagedSelection");
            Check(CheckoutSdkConfiguration125.Parse(Sdk(false),selected,Package).sandbox,"StagingBoundSdkConfig");
            foreach(string bad in new[]{Sdk().Replace("\"version\":1","\"version\":true"),Sdk().Replace("\"12345\"","12345"),Sdk().Replace("\"enabled\":true","\"enabled\":false"),Sdk().Replace("\"sandbox\":false","\"sandbox\":true"),Sdk().Replace("sdk_client_reported","provider_api"),Sdk().Replace(Origin,Origin+"/api"),Sdk().Replace("\"version\":1","\"privateKey\":\"fixture\",\"version\":1"),Sdk().Replace("\"version\":1","\"version\":1,\"version\":1"),Sdk().Replace(Package,"com.heartoftherain.verification"),Sdk().Replace(Package,"com.other.app")})Reject(()=>CheckoutSdkConfiguration125.Parse(bad,ServerProductionConfiguration122.Parse(Profile),Package),"RejectMixedOrMalformedSdkProfile");
            foreach(var item in new[]{ServerConfigurationInput104.Invalid,Input(Sdk(false))})Check(CheckoutSdkConfiguration125.Resolve(false,Package,item,Input(Profile),absent,absent,out selected,out why)&&selected==null,"InvalidOrMixedSdkBlocksFallback");
            Check(CheckoutSdkConfiguration125.Resolve(false,Package,Input(Sdk()),Input(Profile),Input(Stage),absent,out selected,out why)&&selected==null,"MixedServerProfilesBlocked");
            Check(CheckoutSdkConfiguration125.Resolve(false,Package,Input(Sdk()),Input(Profile),absent,Input("{}"),out selected,out why)&&selected==null,"LegacyCheckoutResourceCollisionBlocked");
            Check(!CheckoutConfiguration86.Valid(new CheckoutConfiguration86{version=1,enabled=true,sandbox=true,consoleAppId="12345",verificationMode=CommerceVerification125.SdkClientReported}),"LegacyDeviceShapeCannotOptIntoSdkMode");
        }
        static void TypedModes(){
            using(var sdk=Client())using(var api=Client(CommerceVerification125.ProviderApi)){
                Check(sdk.VerificationParseCatalog(Catalog).Verification==CommerceVerificationMode125.SdkClientReported,"SdkCatalogModeExplicit");
                string oldCatalog=Catalog.Replace("\"verificationMode\":\"sdk_client_reported\",","");
                Check(api.VerificationParseCatalog(oldCatalog).Verification==CommerceVerificationMode125.ProviderApi,"OmittedModeDefaultsOnlyToProviderApi");
                Reject(()=>sdk.VerificationParseCatalog(oldCatalog),"SdkRejectsOmittedCatalogMode");Reject(()=>api.VerificationParseCatalog(Catalog),"ApiRejectsSdkCatalog");
                foreach(string mode in new[]{"null","true","\"\"","\"verified\"","\"provider_api\""})Reject(()=>sdk.VerificationParseCatalog(Catalog.Replace("\"verificationMode\":\"sdk_client_reported\"","\"verificationMode\":"+mode)),"SdkRejectsInvalidOrMixedMode");
                var order=sdk.VerificationParseOrder125(Order);Check(order.Verification==CommerceVerificationMode125.SdkClientReported,"OrderModeExplicit");
                Reject(()=>sdk.VerificationParseOrder125(Order.Replace("\"verificationMode\":\"sdk_client_reported\",","")),"LegacyOrderNeverReinterpretedAsSdk");
                Reject(()=>api.VerificationParseOrder125(Order),"ProviderClientRejectsSdkOrder");
                var credited=sdk.VerificationParseOrder125(Confirmed);Check(credited.credit.Verification==CommerceVerificationMode125.SdkClientReported,"CreditAuditModeExplicit");
                Reject(()=>sdk.VerificationParseOrder125(Confirmed.Replace("\"credit\":{\"verificationMode\":\"sdk_client_reported\"","\"credit\":{\"verificationMode\":\"provider_api\"")),"CreditCannotClaimDifferentVerificationSource");
                var p=CheckoutCatalogRules86.FrozenProduct(order);var quote=new CheckoutQuote86(p,"99 RUB");
                Check(CheckoutCatalogRules86.Order(order,quote,Player,true,CommerceVerification125.SdkClientReported),"FrozenSdkOrderAccepted");Check(!CheckoutCatalogRules86.Order(order,quote,Player,true),"DefaultProviderOrderRuleRejectsSdk");
            }
            Reject(()=>new RuStoreBackendClient(Origin,new string('t',43),Player,true,false,r=>{},false,0,CommerceVerification125.SdkClientReported),"SdkClientRequiresAppBinding");
        }
        static void ReportContract(){
            using(var sdk=Client())using(var api=Client(CommerceVerification125.ProviderApi)){
                string json=sdk.VerificationReportJson125(Request(),Observed());var fieldsFound=Regex.Matches(json,"\"([A-Za-z][A-Za-z0-9_]*)\":").Cast<Match>().Select(match=>match.Groups[1].Value).ToArray();var observation=JsonUtility.FromJson<RuStoreSdkReport125>(json);
                string[] fields={"invoiceId","purchaseId","orderId","productId","developerPayload","quantity","sandbox","status","purchaseType","acknowledgementState","productType","amountMinor","currency"};
                Check(fieldsFound.Length==13&&fieldsFound.OrderBy(v=>v).SequenceEqual(fields.OrderBy(v=>v)),"Exact13SdkFieldsNoActorOrGrantProof");
                Check(observation.amountMinor==9900&&observation.currency=="RUB","FreshObservedPriceCurrencyPreserved");
                Check(sdk.VerificationReportSuffix125=="/sdk-report"&&api.VerificationReportSuffix125=="/reconcile","ExplicitHttpRouteSelection");
                var callbackOnly=new PayPurchase(Observed().locator,Request().developerPayload,"CONFIRMED","ONE_STEP","PENDING");
                Reject(()=>sdk.VerificationReportJson125(Request(),callbackOnly),"PurchaseCallbackWithoutGetPurchasePriceCannotReport");
                Check(api.VerificationReportJson125(Request(),callbackOnly)=="{\"invoiceId\":\"125001\"}","LegacyProviderInvoiceOnlyRouteUnchanged");
                foreach(var purchase in new[]{Observed(amount:null),Observed(amount:0),Observed(amount:-1),Observed(amount:(long)int.MaxValue+1),Observed(currency:null),Observed(currency:"USD"),Observed(status:"CREATED"),Observed(status:"EXECUTED"),Observed(type:"UNDEFINED"),Observed(status:"PAID"),Observed(ack:"NOT_ACKNOWLEDGED"),Observed(purchase:Purchase.ToUpperInvariant())})Reject(()=>sdk.VerificationReportJson125(Request(),purchase),"InvalidSdkObservationBlockedBeforeHttp");
                foreach(string status in new[]{"INVOICE_CREATED","PROCESSING","EXECUTING","CANCELLED","REJECTED","EXPIRED"})Check(RuStoreSdkReport125.From(Request(),Observed(status:status,type:"UNDEFINED")).status==status,"ActualPendingOrTerminalUndefinedTypeRetained");
                foreach(string status in new[]{"REFUNDED","REFUNDING","REVERSED"})Check(RuStoreSdkReport125.From(Request(),Observed(status:status)).status==status,"RefundObservationReportsWithoutDeliveryClaim");
                Check(RuStoreSdkReport125.From(Request(),Observed(status:"PAID",type:"TWO_STEP")).status=="PAID","HeldTwoStepCanBeRecordedWithoutCaptureOrGrant");
                foreach(string ack in new[]{"PENDING","ACKNOWLEDGED","UNKNOWN"})Check(RuStoreSdkReport125.From(Request(),Observed(ack:ack)).acknowledgementState==ack,"ActualVendorAcknowledgementEnum");
            }
        }
        static CheckoutDocument86 Document(RuStoreServerOrder order)=>new CheckoutDocument86{verificationMode=order.verificationMode,origin=Origin,player=Player,phase="Ordered",commandId=Command,productId=order.productId,amountLabel="99 RUB",product=CheckoutCatalogRules86.FrozenProduct(order),hasOrder=true,order=order};
        static void Journal(){
            using(var vault=new EditorEphemeralIdentity82())using(var sdk=Client()){
                string path=Path.Combine(privateRoot,"sdk.sealed");
                using(var journal=new ProtectedCheckoutJournal86(vault.CreateStore(path),Origin,Player,true,CommerceVerification125.SdkClientReported)){
                    Check(journal.Read().verificationMode==CommerceVerification125.SdkClientReported,"EmptyManagedSdkJournalMode");
                    var saved=journal.Save(Document(sdk.VerificationParseOrder125(Order)));Check(saved.order.Verification==CommerceVerificationMode125.SdkClientReported,"SdkOrderModeSurvivesEncryptedReload");
                    Reject(()=>journal.Save(Document(new RuStoreServerOrder())),"InvalidOrderCannotPersist");
                    Check(!File.ReadAllText(path).Contains(OrderId),"JournalUsesActualEncryptedCas");
                }
                using(var provider=new ProtectedCheckoutJournal86(vault.CreateStore(path),Origin,Player,true))Reject(()=>provider.Read(),"SdkPendingJournalCannotBecomeProviderOrder");
                string legacyPath=Path.Combine(privateRoot,"legacy122.sealed");
                var legacyType=typeof(ProtectedCheckoutJournal86).GetNestedType("LegacyDocument122",BindingFlags.NonPublic);
                using(var api=Client(CommerceVerification125.ProviderApi)){
                    var document=Document(api.VerificationParseOrder125(Order.Replace("\"verificationMode\":\"sdk_client_reported\",","")));
                    string legacy=JsonUtility.ToJson(JsonUtility.FromJson(JsonUtility.ToJson(document),legacyType));
                    using(var storage=vault.CreateStore(legacyPath))storage.CompareExchange("",Encoding.UTF8.GetBytes(legacy));
                    using(var journal=new ProtectedCheckoutJournal86(vault.CreateStore(legacyPath),Origin,Player,true)){
                        var restored=journal.Read();Check(restored.order.Verification==CommerceVerificationMode125.ProviderApi,"ExactLegacy122JournalRestoresProviderMode");
                        Check(journal.Save(restored).verificationMode==CommerceVerification125.ProviderApi,"LegacyJournalUpgradeRetainsMode");
                    }
                    using(var changed=new ProtectedCheckoutJournal86(vault.CreateStore(legacyPath),Origin,Player,true,CommerceVerification125.SdkClientReported))Reject(()=>changed.Read(),"LegacyPaidOrderCannotBecomeSdkOrder");
                }
            }
        }
        static RuStoreReleaseConfiguration Release()=>new RuStoreReleaseConfiguration{schemaVersion=1,packageName=Package,consoleApplicationId="12345",paymentReturnScheme="heartoftherain-pay",backendOrigin=Origin,
            privacyPolicyUrl="https://legal.hotr-native-fixture.net/privacy",supportUrl="https://legal.hotr-native-fixture.net/support",termsUrl="https://legal.hotr-native-fixture.net/terms",minimumApiLevel=26,targetApiLevel=36,versionCode=1,
            signingCertificateSha256=string.Concat(Enumerable.Repeat("ab",32)),environment="production",verificationMode=CommerceVerification125.SdkClientReported};
        static void GuardPolicies(){
            var absent=ServerConfigurationInput104.Absent;var sdk=Input(Sdk());var production=Input(Profile);string[] defines={SdkCheckoutBuild125.Define,"HOTR_RUSTORE_PAY","HOTR_PRODUCTION122"};
            Check(SdkCheckoutBuild125.Validate(true,false,false,true,26,Package,defines,"6000.3.27f1",sdk,production,absent,absent).Length==0,"SyntheticQualifiedProductionSdkBuildPolicy");
            Check(SdkCheckoutBuild125.Validate(true,true,false,false,26,Package,new[]{SdkCheckoutBuild125.Define,"HOTR_RUSTORE_PAY"},"6000.3.27f1",Input(Sdk(false)),absent,Input(Stage),absent).Length==0,"SyntheticIsolatedStagingSdkBuildPolicy");
            Check(SdkCheckoutBuild125.Validate(true,true,false,true,26,Package,new[]{SdkCheckoutBuild125.Define,"HOTR_RUSTORE_PAY"},"6000.3.27f1",Input(Sdk(false)),absent,Input(Stage),absent).Length==0,"SdkSandboxAllowsExplicitConsoleMatchingDeveloperSigner");
            foreach(string fault in new[]{"android","development","debugging","signing","api","package","define","sdk","engine","collision"}){
                var current=defines.Where(v=>fault!="define"||v!=SdkCheckoutBuild125.Define).Where(v=>fault!="sdk"||v!="HOTR_RUSTORE_PAY").ToArray();
                Check(SdkCheckoutBuild125.Validate(fault!="android",fault=="development",fault=="debugging",fault!="signing",fault=="api"?25:26,fault=="package"?"com.other.app":Package,current,fault=="engine"?"2022.3.62f3":"6000.3.27f1",sdk,production,absent,fault=="collision"?Input("{}"):absent).Length>0,"SdkBuildGuardRejects_"+fault);
            }
            var release=Release();Check(RuStoreReleasePreflight.Validate(release).Contains("client_reported_backend_credit_disallowed"),"LiveSdkClientReportCannotPassReleaseGate");
            release.environment="sandbox";Check(RuStoreReleasePreflight.Validate(release).Count==0,"ExplicitSdkSandboxCanRunForModerationTests");release.environment="production";
            release.verificationMode=CommerceVerification125.ProviderApi;Check(RuStoreReleasePreflight.Validate(release).Count==0,"ProviderVerifiedLiveModeRemainsSelectable");release.verificationMode=CommerceVerification125.SdkClientReported;
            var blockers=RuStoreReleasePreflight.IntegrationBlockers125(release,Package,sdk,production,absent,absent);
            Check(!blockers.Contains("provider_notification_authentication_not_configured"),"OnlyStrictSdkModeOmitsIrrelevantNotificationGate");
            foreach(string code in new[]{"configured_sdk_managed_wallet_android_acceptance_required","native_sdk_payment_recovery_and_external_bank_return_not_verified","production_signing_and_legal_hosting_review_not_complete"})Check(blockers.Contains(code),"RealAcceptanceGateRetained");
            Check(RuStoreReleasePreflight.IntegrationBlockers125(release,Package,absent,production,absent,absent).Contains("strict_sdk_checkout_managed_profile_required"),"ModeStringAloneCannotWaiveProviderGate");
            release.verificationMode=null;Check(RuStoreReleasePreflight.IntegrationBlockers125(release,Package,sdk,production,absent,absent).Contains("provider_notification_authentication_not_configured"),"LegacyModeStillRequiresProviderAcceptance");
            release.verificationMode="unverified";Check(RuStoreReleasePreflight.Validate(release).Contains("payment_verification_mode_invalid"),"UnknownReleaseModeRejected");
        }
        static void ToolchainPolicy(){
            string data=Path.Combine(privateRoot,"SyntheticEditor","Data"),android=Path.Combine(data,"PlaybackEngines","AndroidPlayer"),sdk=Path.Combine(android,"SDK"),ndk=Path.Combine(android,"NDK"),jdk=Path.Combine(android,"OpenJDK"),gradle=Path.Combine(android,"Tools","gradle");
            foreach(string relative in new[]{"SDK/platforms/android-36/android.jar","OpenJDK/bin/java.exe","Tools/gradle/lib/gradle-core-9.3.1.jar","Tools/gradle/lib/gradle-launcher-9.3.1.jar"}){string path=Path.Combine(android,relative);Directory.CreateDirectory(Path.GetDirectoryName(path));File.WriteAllText(path,"synthetic policy fixture");}
            Directory.CreateDirectory(ndk);File.WriteAllText(Path.Combine(ndk,"source.properties"),"Pkg.Revision = 27.2.12479018\n");File.WriteAllText(Path.Combine(jdk,"release"),"JAVA_VERSION=\"17.0.18\"\n");
            Check(SdkCheckoutBuild125.ToolchainErrors("6000.3.27f1",data,sdk,ndk,jdk,gradle).Length==0,"SyntheticStockMetadataPolicyControlNotActualBuildAcceptance");
            Check(!Directory.Exists(Path.Combine(gradle,"bin"))&&SdkCheckoutBuild125.ToolchainErrors("6000.3.27f1",data,sdk,ndk,jdk,gradle).Length==0,"StockJarOnlyGradleNeedsNoBatchLauncher126");
            string launcher=Path.Combine(gradle,"lib/gradle-launcher-9.3.1.jar");File.Delete(launcher);
            Check(SdkCheckoutBuild125.ToolchainErrors("6000.3.27f1",data,sdk,ndk,jdk,gradle).Contains("sdk_checkout_stock_gradle_9_3_1_required"),"MissingExactGradleLauncherRejected126");File.WriteAllText(launcher,"synthetic policy fixture");
            string core=Path.Combine(gradle,"lib/gradle-core-9.3.1.jar");File.Delete(core);
            Check(SdkCheckoutBuild125.ToolchainErrors("6000.3.27f1",data,sdk,ndk,jdk,gradle).Contains("sdk_checkout_stock_gradle_9_3_1_required"),"MissingExactGradleCoreRejected126");File.WriteAllText(core,"synthetic policy fixture");
            Check(SdkCheckoutBuild125.ToolchainErrors("2022.3.62f3",data,sdk,ndk,jdk,gradle).Length>0,"MainEngineCannotQualifySdkShippingProfile");
            Check(SdkCheckoutBuild125.ToolchainErrors("6000.3.27f1",data,sdk,ndk,jdk,Path.Combine(privateRoot,"foreignGradle")).Length>0,"MatchingVersionCannotWaiveForeignToolPath");
            File.WriteAllText(Path.Combine(jdk,"release"),"JAVA_VERSION=\"17.0.1\"\n");Check(SdkCheckoutBuild125.ToolchainErrors("6000.3.27f1",data,sdk,ndk,jdk,gradle).Length>0,"WrongEmbeddedJavaMetadataRejected");
            Check(SdkCheckoutBuild125.ActualToolchainErrors().Length>0,"ActualRunningMain2022DoesNotClaimLtsShippingReadiness");
        }
        static void VendorBindings(){
            var pay=new SdkVendorBindings125.PackageObservation{name="ru.rustore.pay",version="11.1.0",source="Registry",files=234,aggregate="00ad7edc4f0d67eda4afd750eccc54b5cdce36fac23b1bf7b7cb288aa94a39e3"};
            var core=new SdkVendorBindings125.PackageObservation{name="ru.rustore.core",version="10.5.0",source="Registry",files=81,aggregate="6b9543abfea570e6e97096a8f77a2a9e292c29e91536eadf6c53be6336c2446d"};
            Check(SdkVendorBindings125.PackageErrors(new[]{pay,core}).Length==0,"SyntheticOfficialPackagePinControl");
            Check(SdkVendorBindings125.PackageErrors(new[]{pay}).Length>0&&SdkVendorBindings125.PackageErrors(new[]{core}).Length>0,"MissingVendorPackageCannotPassDevelopmentGuard");
            pay.version="11.0.0";Check(SdkVendorBindings125.PackageErrors(new[]{pay,core}).Length>0,"WrongPayVersionRejectedBeforeSandboxBuild");pay.version="11.1.0";
            pay.aggregate=new string('a',64);Check(SdkVendorBindings125.PackageErrors(new[]{pay,core}).Length>0,"MatchingVersionWithChangedVendorBytesRejected");
            Check(SdkVendorBindings125.ActualPackageErrors().Length>0,"OrdinarySdkFreeProjectNotCertifiedByPureFixture");
            const string values="<resources><string name='rustore_PayClientSettings_consoleApplicationId'>12345</string><string name='rustore_PayClientSettings_deeplinkScheme'>heartoftherain-pay</string><string name='rustore_PayClientSettings_internalConfigKey'>unity</string></resources>";
            const string manifest="<manifest xmlns:android='http://schemas.android.com/apk/res/android'><application><meta-data android:name='console_app_id_value' android:value='@string/rustore_PayClientSettings_consoleApplicationId'/><meta-data android:name='sdk_pay_scheme_value' android:value='@string/rustore_PayClientSettings_deeplinkScheme'/><meta-data android:name='internal_config_key' android:value='@string/rustore_PayClientSettings_internalConfigKey'/><activity android:name='ru.rustore.unitysdk.RuStoreDeeplinkActivityDefault' android:exported='true' android:theme='@android:style/Theme.NoDisplay'><intent-filter><action android:name='android.intent.action.VIEW'/><category android:name='android.intent.category.DEFAULT'/><category android:name='android.intent.category.BROWSABLE'/><data android:scheme='@string/rustore_PayClientSettings_deeplinkScheme'/></intent-filter></activity></application></manifest>";
            Check(SdkVendorBindings125.Validate("12345","heartoftherain-pay","12345","heartoftherain-pay",values,manifest).Length==0,"SyntheticAssetGeneratedValuesAndManifestBinding");
            foreach(string fault in new[]{"assetId","assetScheme","generatedId","generatedScheme","manifestRef","intent","duplicate","dtd"}){
                string xml=fault=="generatedId"?values.Replace("12345","12346"):fault=="generatedScheme"?values.Replace("heartoftherain-pay","other-pay"):values;
                string main=fault=="manifestRef"?manifest.Replace("@string/rustore_PayClientSettings_consoleApplicationId","@string/other"):fault=="intent"?manifest.Replace("android.intent.category.BROWSABLE","other"):fault=="duplicate"?manifest.Replace("</application>","<meta-data android:name='console_app_id_value' android:value='@string/rustore_PayClientSettings_consoleApplicationId'/></application>"):fault=="dtd"?"<!DOCTYPE manifest [<!ENTITY test 'bad'>]>"+manifest:manifest;
                Check(SdkVendorBindings125.Validate("12345","heartoftherain-pay",fault=="assetId"?"12346":"12345",fault=="assetScheme"?"other-pay":"heartoftherain-pay",xml,main).Length>0,"RejectVendorBinding_"+fault);
            }
            Reject(()=>SdkVendorBindings125.ConfigureIsolated("12345","heartoftherain-pay"),"NativeMainProfileCannotMutateVendorSettings");
        }
        [Serializable] sealed class UpmVectors126 {public UpmVector126[] packages=null;}
        [Serializable] sealed class UpmVector126 {public string name=null,version=null,registryFingerprint=null,stockRawSHA256=null,stockJson=null,upmJson=null;}
        const string UpmFixture126=@"{""packages"":[{""name"":""ru.rustore.pay"",""version"":""11.1.0"",""registryFingerprint"":""268ab2fb33b68595db5bc2d8a1af792e191fe7b8"",""stockRawSHA256"":""afbaabf48f1c57f77432775121ac21923c16e51839c29288ee205a5b4aec3ff3"",""stockJson"":""{\n  \""name\"": \""ru.rustore.pay\"",\n  \""version\"": \""11.1.0\"",\n  \""displayName\"": \""RuStore Pay\"",\n  \""description\"": \""RuStore SDK for in-app payments\"",\n  \""unity\"": \""6000.0\"",\n  \""documentationUrl\"": \""https://www.rustore.ru/help/sdk/payments/unity\"",\n  \""changelogUrl\"": \""https://gitflic.ru/project/rustore/unity-rustore-pay-sdk/blob/?file=ru.rustore.pay%2FCHANGELOG.md\"",\n  \""licensesUrl\"": \""https://gitflic.ru/project/rustore/unity-rustore-pay-sdk/blob?file=MIT-LICENSE.txt\"",\n  \""keywords\"": [\n    \""rustore\"",\n    \""pay\"",\n    \""payments\""\n  ],\n  \""dependencies\"": {\n    \""ru.rustore.core\"": \""10.5.0\""\n  },\n  \""author\"": {\n    \""name\"": \""RuStore\"",\n    \""email\"": \""support@rustore.ru\"",\n    \""url\"": \""https://www.rustore.ru/developer\""\n  },\n  \""samples\"": [\n    {\n      \""displayName\"": \""RuStore Pay Example\"",\n      \""description\"": \""Contains sample RuStore shop\"",\n      \""path\"": \""Samples~/RuStorePayExample\""\n    }\n  ],\n  \""repository\"": {\n    \""url\"": \""https://gitflic.ru/project/rustore/unity-rustore-pay-sdk.git\"",\n    \""type\"": \""git\"",\n    \""revision\"": \""42544fc42862ed7f8144ce952646eb85033f2fa5\""\n  }\n}\n"",""upmJson"":""{\n  \""name\"": \""ru.rustore.pay\"",\n  \""version\"": \""11.1.0\"",\n  \""displayName\"": \""RuStore Pay\"",\n  \""description\"": \""RuStore SDK for in-app payments\"",\n  \""unity\"": \""6000.0\"",\n  \""documentationUrl\"": \""https://www.rustore.ru/help/sdk/payments/unity\"",\n  \""changelogUrl\"": \""https://gitflic.ru/project/rustore/unity-rustore-pay-sdk/blob/?file=ru.rustore.pay%2FCHANGELOG.md\"",\n  \""licensesUrl\"": \""https://gitflic.ru/project/rustore/unity-rustore-pay-sdk/blob?file=MIT-LICENSE.txt\"",\n  \""keywords\"": [\n    \""rustore\"",\n    \""pay\"",\n    \""payments\""\n  ],\n  \""dependencies\"": {\n    \""ru.rustore.core\"": \""10.5.0\""\n  },\n  \""author\"": {\n    \""name\"": \""RuStore\"",\n    \""email\"": \""support@rustore.ru\"",\n    \""url\"": \""https://www.rustore.ru/developer\""\n  },\n  \""samples\"": [\n    {\n      \""displayName\"": \""RuStore Pay Example\"",\n      \""description\"": \""Contains sample RuStore shop\"",\n      \""path\"": \""Samples~/RuStorePayExample\""\n    }\n  ],\n  \""repository\"": {\n    \""url\"": \""https://gitflic.ru/project/rustore/unity-rustore-pay-sdk.git\"",\n    \""type\"": \""git\"",\n    \""revision\"": \""42544fc42862ed7f8144ce952646eb85033f2fa5\""\n  },\n  \""_fingerprint\"": \""268ab2fb33b68595db5bc2d8a1af792e191fe7b8\""\n}\n""},{""name"":""ru.rustore.core"",""version"":""10.5.0"",""registryFingerprint"":""985c393e8d98b181445205858b678e25cc4dd178"",""stockRawSHA256"":""b820d53463b52b64d530c47ce6c0d3c570eabc6166fed81b63e28b71800dd54b"",""stockJson"":""{\n  \""name\"": \""ru.rustore.core\"",\n  \""version\"": \""10.5.0\"",\n  \""displayName\"": \""RuStore Core\"",\n  \""description\"": \""The common part of RuStore SDK plugins\"",\n  \""unity\"": \""6000.0\"",\n  \""documentationUrl\"": \""https://www.rustore.ru/help/sdk\"",\n  \""changelogUrl\"": \""https://gitflic.ru/project/rustore/unity-rustore-core-sdk/blob/?file=CHANGELOG.md\"",\n  \""licensesUrl\"": \""https://gitflic.ru/project/rustore/unity-rustore-core-sdk/blob?file=MIT-LICENSE.txt\"",\n  \""keywords\"": [\n    \""rustore\"",\n    \""core\""\n  ],\n  \""author\"": {\n    \""name\"": \""RuStore\"",\n    \""email\"": \""support@rustore.ru\"",\n    \""url\"": \""https://www.rustore.ru/developer\""\n  },\n  \""samples\"": [\n    {\n      \""displayName\"": \""External Dependency Manager\"",\n      \""description\"": \""External Dependency Manager for Unity (EDM4U) can be used by any Unity plugin that requires Android specific libraries (e.g. AARs).\"",\n      \""path\"": \""Samples~/External Dependency Manager\""\n    },\n    {\n      \""displayName\"": \""RuStore Core Example\"",\n      \""description\"": \""Contains sample public methods of RuStoreUtils\"",\n      \""path\"": \""Samples~/RuStoreCoreExample\""\n    }\n  ],\n  \""repository\"": {}\n}\n"",""upmJson"":""{\n  \""name\"": \""ru.rustore.core\"",\n  \""version\"": \""10.5.0\"",\n  \""displayName\"": \""RuStore Core\"",\n  \""description\"": \""The common part of RuStore SDK plugins\"",\n  \""unity\"": \""6000.0\"",\n  \""documentationUrl\"": \""https://www.rustore.ru/help/sdk\"",\n  \""changelogUrl\"": \""https://gitflic.ru/project/rustore/unity-rustore-core-sdk/blob/?file=CHANGELOG.md\"",\n  \""licensesUrl\"": \""https://gitflic.ru/project/rustore/unity-rustore-core-sdk/blob?file=MIT-LICENSE.txt\"",\n  \""keywords\"": [\n    \""rustore\"",\n    \""core\""\n  ],\n  \""author\"": {\n    \""name\"": \""RuStore\"",\n    \""email\"": \""support@rustore.ru\"",\n    \""url\"": \""https://www.rustore.ru/developer\""\n  },\n  \""samples\"": [\n    {\n      \""displayName\"": \""External Dependency Manager\"",\n      \""description\"": \""External Dependency Manager for Unity (EDM4U) can be used by any Unity plugin that requires Android specific libraries (e.g. AARs).\"",\n      \""path\"": \""Samples~/External Dependency Manager\""\n    },\n    {\n      \""displayName\"": \""RuStore Core Example\"",\n      \""description\"": \""Contains sample public methods of RuStoreUtils\"",\n      \""path\"": \""Samples~/RuStoreCoreExample\""\n    }\n  ],\n  \""repository\"": {},\n  \""_fingerprint\"": \""985c393e8d98b181445205858b678e25cc4dd178\""\n}\n""}]}";
        static void UpmManifestPolicy126(){
            var vectors=JsonUtility.FromJson<UpmVectors126>(UpmFixture126);Check(vectors.packages.Length==2,"BothOfficialPinnedManifestVectors126");
            foreach(var p in vectors.packages){
                Func<string,string,string> hash=(json,source)=>SdkVendorBindings125.ManifestHash126(p.name,p.version,source,Encoding.UTF8.GetBytes(json));
                Check(hash(p.stockJson,"Registry")==p.stockRawSHA256,"OriginalRawOfficialManifestAccepted126");
                Check(hash(p.upmJson,"Registry")==p.stockRawSHA256,"KnownTrailingUpmFingerprintPreservesOriginalManifestHash126");
                Check(hash(" \r\n\t"+p.upmJson.Replace("\n","\r\n\t")+" \r\n","Registry")==p.stockRawSHA256,"OnlyAsciiWhitespaceOutsideTokensMayVary126");
                Check(hash(p.upmJson,"Embedded")!=p.stockRawSHA256,"UpmWrapperAcceptedOnlyForRegistry126");
                Check(hash(" "+p.stockJson,"Registry")!=p.stockRawSHA256,"WhitespaceOnlyWithoutKnownProvenanceWrapperNotNormalized126");
                string field="\"_fingerprint\": \""+p.registryFingerprint+"\"";
                var bad=new[]{
                    p.upmJson.Replace(p.registryFingerprint,new string('0',40)),
                    p.upmJson.Replace("\"_fingerprint\":","\"extra\":true,\"_fingerprint\":"),
                    p.upmJson.Replace("\"_fingerprint\":","\"unity\":\"6000.0\",\"_fingerprint\":"),
                    p.upmJson.Replace(field,field+","+field),
                    p.upmJson.Replace("\"6000.0\"","\"2022.3\""),
                    p.upmJson.Replace("\""+p.version+"\"","\"0.0.0\""),
                    p.upmJson.Replace("\"name\": \""+p.name+"\",\n  \"version\": \""+p.version+"\"","\"version\": \""+p.version+"\",\n  \"name\": \""+p.name+"\""),
                    p.upmJson.Replace("\"name\"","\"\\u006eame\""),
                    p.upmJson.Replace("https://","https:\\/\\/"),
                    p.upmJson.Replace(p.name=="ru.rustore.pay"?"RuStore Pay":"The common part",p.name=="ru.rustore.pay"?"RuStore  Pay":"The  common part"),
                    p.upmJson.Replace("\"_fingerprint\":","\"dependencies\":{},\"_fingerprint\":"),
                    "\u00a0"+p.upmJson,
                    p.upmJson.Replace(field,"\"_fingerprint\":null")
                };
                foreach(string json in bad){Check(json!=p.upmJson,"ManifestNegativeActuallyChangesInput126");Check(hash(json,"Registry")!=p.stockRawSHA256,"ChangedExtraDuplicateEscapedOrVendorTokensCannotNormalize126");}
                if(p.name=="ru.rustore.pay")Check(hash(p.upmJson.Replace("\"ru.rustore.core\": \"10.5.0\"","\"ru.rustore.core\": \"10.4.0\""),"Registry")!=p.stockRawSHA256,"ChangedDependencyCannotHideBehindUpmWrapper126");
                Check(SdkVendorBindings125.ManifestHash126(p.name,p.version+"x","Registry",Encoding.UTF8.GetBytes(p.upmJson))!=p.stockRawSHA256,"WrongObservedVersionCannotNormalize126");
                string directory=Path.Combine(privateRoot,"PackageObservation126",p.name);Directory.CreateDirectory(directory);string manifest=Path.Combine(directory,"package.json"),other=Path.Combine(directory,"other.txt");File.WriteAllText(manifest,p.stockJson,new UTF8Encoding(false));File.WriteAllText(other,"untouched vendor file",new UTF8Encoding(false));
                var stock=SdkVendorBindings125.ObservePackage(p.name,p.version,"Registry",directory);File.WriteAllText(manifest,p.upmJson,new UTF8Encoding(false));var upm=SdkVendorBindings125.ObservePackage(p.name,p.version,"Registry",directory);
                Check(stock.aggregate==upm.aggregate&&stock.files==upm.files,"FullFileAggregateRestoresOnlyOriginalManifestContribution126");File.WriteAllText(other,"changed vendor file",new UTF8Encoding(false));Check(SdkVendorBindings125.ObservePackage(p.name,p.version,"Registry",directory).aggregate!=stock.aggregate,"OtherVendorFileBytesRemainRawAndPinned126");
            }
        }
        static void WithResource(string path,string json,Action action){
            string project=Environment.GetEnvironmentVariable("HOTR_REVIEW125_ISOLATED_PROJECT");
            if(string.IsNullOrEmpty(project)||Path.GetFullPath(".")!=Path.GetFullPath(project))throw new InvalidOperationException("SealedIsolatedProjectRequired");
            string folder=Path.GetDirectoryName(path),meta=path+".meta",folderMeta=folder+".meta";
            if(File.Exists(path)||File.Exists(meta))throw new InvalidOperationException("FreshResourceRequired");
            bool hadFolder=Directory.Exists(folder),hadMeta=File.Exists(folderMeta);byte[] priorMeta=hadMeta?File.ReadAllBytes(folderMeta):null;
            string guid=Guid.NewGuid().ToString("N");byte[] bytes=Encoding.UTF8.GetBytes(json);Directory.CreateDirectory(folder);File.WriteAllBytes(path,bytes);
            File.WriteAllText(meta,"fileFormatVersion: 2\nguid: "+guid+"\nTextScriptImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n",new UTF8Encoding(false));
            try{AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport|ImportAssetOptions.ForceUpdate);action();}
            finally{
                if(!File.ReadAllBytes(path).SequenceEqual(bytes)||!File.ReadAllText(meta).Contains("guid: "+guid))throw new InvalidOperationException("ForeignResourceMutationPreserved");
                AssetDatabase.DeleteAsset(path);
                if(!hadFolder){if(Directory.GetFileSystemEntries(folder).Length!=0)throw new InvalidOperationException("ForeignFolderContentsPreserved");Directory.Delete(folder);}
                if(hadMeta){if(!File.ReadAllBytes(folderMeta).SequenceEqual(priorMeta))throw new InvalidOperationException("FolderMetaChanged");}
                else if(!hadFolder&&File.Exists(folderMeta))File.Delete(folderMeta);
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            }
        }
        static void ActualResources(){
            Check(Application.identifier==Package,"SealedPrivateEditorPackage");string oldServer=Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG"),oldCheckout=Environment.GetEnvironmentVariable("HOTR_SHOP_CHECKOUT86_CONFIG");
            try{
                Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",Path.Combine(privateRoot,"absent-server.json"));Environment.SetEnvironmentVariable("HOTR_SHOP_CHECKOUT86_CONFIG",Path.Combine(privateRoot,"absent-checkout.json"));
                WithResource(ServerProductionConfiguration122.ResourceAssetPath,Profile,()=>WithResource(CheckoutSdkConfiguration125.ResourceAssetPath,Sdk(),()=>{
                    ServerGameplayConfiguration selected;string why;CheckoutConfiguration86 config;
                    Check(ServerGameplayConfiguration.TryRead(out selected,out why)&&selected!=null&&selected.productionEnabled,"ActualSdkProductionReaderIgnoresOverride");
                    Check(CheckoutConfiguration86.TryRead(out config)&&config.Verification==CommerceVerificationMode125.SdkClientReported&&!config.sandbox,"ActualSdkCheckoutReaderIgnoresDeviceFile");
                    WithResource(ServerProductionConfiguration122.CheckoutResourceAssetPath,"{}",()=>Check(!CheckoutConfiguration86.TryRead(out config),"ActualMixedCheckoutResourcesFailClosed"));
                }));
                WithResource(ServerStagingConfiguration104.ResourceAssetPath,Stage,()=>WithResource(CheckoutSdkConfiguration125.ResourceAssetPath,Sdk(false),()=>{
                    ServerGameplayConfiguration selected;string why;CheckoutConfiguration86 config;
                    Check(ServerGameplayConfiguration.TryRead(out selected,out why)&&selected!=null&&!selected.productionEnabled&&selected.packageName==Package,"ActualSdkStageRegisteredPackageBound");
                    Check(CheckoutConfiguration86.TryRead(out config)&&config.sandbox&&config.Verification==CommerceVerificationMode125.SdkClientReported,"ActualSdkStageReaderNoExternalOverride");
                }));
                WithResource(CheckoutSdkConfiguration125.ResourceAssetPath,"{}",()=>{ServerGameplayConfiguration selected;string why;Check(ServerGameplayConfiguration.TryRead(out selected,out why)&&selected==null&&why!=null,"MalformedSdkResourceNeverFallsBack");});
            }finally{Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",oldServer);Environment.SetEnvironmentVariable("HOTR_SHOP_CHECKOUT86_CONFIG",oldCheckout);}
        }
        public static void Run(){
            report=new Report{status="FAIL_NATIVE_SDK_CHECKOUT125",unity=Application.unityVersion,utc=DateTime.UtcNow.ToString("o")};
            string project=Environment.GetEnvironmentVariable("HOTR_REVIEW125_ISOLATED_PROJECT"),output=Environment.GetEnvironmentVariable("HOTR_REVIEW125_OUT");
            if(string.IsNullOrEmpty(project)||Path.GetFullPath(".")!=Path.GetFullPath(project)||string.IsNullOrEmpty(output))throw new InvalidOperationException("IsolatedOutputRequired");
            privateRoot=Path.GetFullPath(Path.Combine("../.verification-cache/Launch82/Sdk125",Guid.NewGuid().ToString("N")));Directory.CreateDirectory(privateRoot);
            try{Case("PinnedNativeEngine",()=>Check(Application.unityVersion=="2022.3.62f3","PinnedBaselineEngine"));Case("StrictPackagedSdkSelection",Profiles);Case("BoundModeAndCreditDtos",TypedModes);Case("ExactSdkReportContract",ReportContract);Case("EncryptedJournalModeAndLegacyRecovery",Journal);Case("SdkBuildAndAcceptanceGuards",GuardPolicies);Case("ModeSpecificStockToolchainPolicy",ToolchainPolicy);Case("PinnedVendorAndAndroidBindings",VendorBindings);Case("RegistryOnlyUpmManifestProvenance126",UpmManifestPolicy126);Case("ActualPackagedResourceReaders",ActualResources);}
            finally{if(Directory.Exists(privateRoot))Directory.Delete(privateRoot,true);}
            if(report.errors.Count==0)report.status="PASS_NATIVE_SDK_CHECKOUT125";Directory.CreateDirectory(output);
            using(var file=new FileStream(Path.Combine(output,"SdkCheckout125.json"),FileMode.CreateNew,FileAccess.Write))using(var writer=new StreamWriter(file,new UTF8Encoding(false)))writer.Write(JsonUtility.ToJson(report,true));
            if(Application.isBatchMode)EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif

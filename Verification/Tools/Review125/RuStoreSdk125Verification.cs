#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.RuStore.Editor;
using RuStore.PayClient;
using UnityEditor;
using UnityEngine;

// Imported only by the isolated SDK API fixture. Never calls Instance or JNI.
public static class RuStoreSdk125Verification {
    [Serializable] sealed class Source {public string source,copied,sha256;}
    [Serializable] sealed class Pin {public string name,version,packageManifestSHA256,vendorUnityMinimum;}
    [Serializable] sealed class Inputs {public string runId;public Source[] sources;public Pin[] packages;}
    [Serializable] sealed class PackageJson {public string unity;}
    [Serializable] sealed class PackageProof {public string name,version,unity,source,resolvedPath,manifestSHA256;}
    [Serializable] sealed class Result {
        public string status="FAIL_NATIVE_RUSTORE_SDK125_CURRENT_API",utc,unity,runId,error,inputManifestSHA256;
        public int checks;public bool apiCompileOnly=true,sdkDefineEnabled,sdkInitialized=false,paymentCalls=false,androidBuild=false,gameSdkEnabled=false;
        public string scope="Fresh exact adapter/contracts/coordinator/journal and vendor binding helper with stock Pay11.1.0/Core10.5.0 in pinned Unity2022.3.62f3. Real SDK models/static map and official Editor binding generation with synthetic public ID/scheme in a disposable fixture; all fixture Assets restored. No singleton/JNI, provider/purchase/Android build, device acceptance, ordinary-game packaging, upgrade or vendor support certification.";
        public Source[] sources;public List<PackageProof> packages=new List<PackageProof>();
    }
    static string Hash(string path){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
    static void Need(Result report,bool value,string code){report.checks++;if(!value)throw new InvalidOperationException(code);}
    static bool Api(string name,params Type[] parameters){return typeof(RuStorePayClient).GetMethods().Any(method=>method.Name==name&&!method.IsStatic&&method.ReturnType==typeof(void)&&method.GetParameters().Select(parameter=>parameter.ParameterType).SequenceEqual(parameters));}
    static ProductPurchase Purchase(string payload,Price price,Currency currency,ProductPurchaseStatus status=ProductPurchaseStatus.CONFIRMED,PurchaseType purchaseType=PurchaseType.ONE_STEP){
        return new ProductPurchase(new AmountLabel("123.45 RUB"),currency,new Description("API fixture only"),
            new DeveloperPayload(payload),new InvoiceId("123456"),new OrderId("11111111111111111111111111111111"),
            price,new ProductId("unregistered.review125.only"),ProductType.CONSUMABLE_PRODUCT,
            new PurchaseId("33333333-3333-3333-3333-333333333333"),DateTime.UtcNow,purchaseType,
            new Quantity(1),status,false,AcknowledgementState.PENDING);
    }
    static Dictionary<string,byte[]> Assets(string project)=>Directory.GetFiles(Path.Combine(project,"Assets"),"*",SearchOption.AllDirectories).ToDictionary(path=>path,path=>File.ReadAllBytes(path),StringComparer.OrdinalIgnoreCase);
    static void BindingChecks(Result report,string project){
        var before=Assets(project);var directories=new HashSet<string>(Directory.GetDirectories(Path.Combine(project,"Assets"),"*",SearchOption.AllDirectories),StringComparer.OrdinalIgnoreCase);
        string key="HOTR_SDK125_PACKAGING_PROJECT",prior=Environment.GetEnvironmentVariable(key),prefix=Path.GetFullPath(Path.Combine(project,"Assets"))+Path.DirectorySeparatorChar;
        Func<string,bool> inside=path=>Path.GetFullPath(path).StartsWith(prefix,StringComparison.OrdinalIgnoreCase);
        try{
            Need(report,SdkVendorBindings125.ActualPackageErrors().Length==0,"ExactActualSdkPackageInventory");
            Environment.SetEnvironmentVariable(key,null);bool blocked=false;
            try{SdkVendorBindings125.ConfigureIsolated("123456","heartoftherain-pay");}catch(InvalidOperationException){blocked=true;}
            Need(report,blocked,"UnselectedPackagingProjectCannotChangeBindings");
            Environment.SetEnvironmentVariable(key,project);
            SdkVendorBindings125.ConfigureIsolated("123456","heartoftherain-pay");
            Need(report,SdkVendorBindings125.ActualBindingErrors("123456","heartoftherain-pay").Length==0,"RealVendorSettingsValuesAndManifestGenerated");
            Need(report,SdkVendorBindings125.ActualBindingErrors("654321","heartoftherain-pay").Length>0,"MismatchedConsoleIdBlocked");
            Need(report,SdkVendorBindings125.ActualBindingErrors("123456","other-test-scheme").Length>0,"MismatchedBankReturnSchemeBlocked");
            string values=File.ReadAllText(SdkVendorBindings125.ValuesPath),manifest=File.ReadAllText(SdkVendorBindings125.ManifestPath);
            Need(report,SdkVendorBindings125.Validate("123456","heartoftherain-pay","123456","heartoftherain-pay",values,manifest.Replace("@string/rustore_PayClientSettings_deeplinkScheme","incorrect-scheme")).Length>0,"BrokenManifestReturnBindingBlocked");
            var invalid=new[]{new SdkVendorBindings125.PackageObservation{name="ru.rustore.pay",version="11.2.0",source="Registry",files=234,aggregate="00ad7edc4f0d67eda4afd750eccc54b5cdce36fac23b1bf7b7cb288aa94a39e3"}};
            Need(report,SdkVendorBindings125.PackageErrors(invalid).Length>0,"UpgradedOrMissingVendorPackageBlocked");
        }finally{
            Environment.SetEnvironmentVariable(key,prior);
            foreach(string path in Directory.GetFiles(Path.Combine(project,"Assets"),"*",SearchOption.AllDirectories))if(!before.ContainsKey(path)){if(!inside(path))throw new InvalidOperationException("FixtureCleanupEscapedAssets");File.Delete(path);}
            foreach(var pair in before){if(!inside(pair.Key))throw new InvalidOperationException("FixtureRestoreEscapedAssets");if(!File.Exists(pair.Key)||!File.ReadAllBytes(pair.Key).SequenceEqual(pair.Value)){Directory.CreateDirectory(Path.GetDirectoryName(pair.Key));File.WriteAllBytes(pair.Key,pair.Value);}}
            foreach(string path in Directory.GetDirectories(Path.Combine(project,"Assets"),"*",SearchOption.AllDirectories).OrderByDescending(path=>path.Length))if(!directories.Contains(path)){if(!inside(path)||Directory.EnumerateFileSystemEntries(path).Any())throw new InvalidOperationException("UnexpectedFixtureDirectoryPreserved");Directory.Delete(path,false);}
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
        }
        var after=Assets(project);
        Need(report,before.Count==after.Count&&before.All(pair=>after.ContainsKey(pair.Key)&&after[pair.Key].SequenceEqual(pair.Value)),"ExactPrivateFixtureAssetsRestored");
        Need(report,Environment.GetEnvironmentVariable(key)==prior,"ProcessPackagingEnvironmentRestored");
    }
    public static void Run(){
        var report=new Result{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};int exit=1;
        string project=Path.GetDirectoryName(Application.dataPath),output=Environment.GetEnvironmentVariable("HOTR_REVIEW125_SDK_OUTPUT");
        try{
            Need(report,Application.isBatchMode&&Application.unityVersion=="2022.3.62f3","PinnedBatchEditorRequired");
            string path=Path.Combine(project,"ProofInputs125.json");report.inputManifestSHA256=Hash(path);var inputs=JsonUtility.FromJson<Inputs>(File.ReadAllText(path,Encoding.UTF8));report.runId=inputs.runId;report.sources=inputs.sources;
            Need(report,inputs.sources!=null&&inputs.sources.Length==10&&inputs.packages!=null&&inputs.packages.Length==2,"ExactInputsRequired");
            foreach(var source in inputs.sources){string copy=Path.GetFullPath(Path.Combine(project,source.copied));Need(report,copy.StartsWith(project+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)&&Hash(copy)==source.sha256,"CurrentSourceBinding");}
#if HOTR_RUSTORE_PAY
            report.sdkDefineEnabled=true;
#endif
            var adapter=new RuStorePayAdapter();Need(report,report.sdkDefineEnabled&&adapter.SdkCompiled&&!adapter.Configured,"SdkBranchCompiledButNotInitialized");
            const string player="00000000000000000000000000000000",order="11111111111111111111111111111111",payload="hotr-order-v1:11111111111111111111111111111111:22222222222222222222222222222222";
            var parameters=new ProductPurchaseParams(new ProductId("unregistered.review125.only"),appUserId:new AppUserId(player),developerPayload:new DeveloperPayload(payload),orderId:new OrderId(order),quantity:new Quantity(1));
            Need(report,parameters.appUserId.value==player&&parameters.orderId.value==order&&parameters.developerPayload.value==payload&&parameters.quantity.value==1,"RealSdkRequestCorrelation");
            Need(report,typeof(ProductPurchase).GetProperty("appUserId")==null&&typeof(ProductPurchaseResult).GetProperty("appUserId")==null,"AppUserIdIsRequestOnly");
            Need(report,typeof(ProductPurchaseResult).GetProperty("price")==null&&typeof(ProductPurchaseResult).GetProperty("currency")==null&&typeof(ProductPurchaseResult).GetProperty("status")==null&&typeof(ProductPurchaseResult).GetProperty("developerPayload")==null,"PurchaseSuccessNeedsFreshLookup");
            Need(report,typeof(ProductPurchase).GetProperty("price").PropertyType==typeof(Price)&&typeof(Price).BaseType.GetGenericArguments()[0]==typeof(int),"SdkPriceIsIntegerMinorUnits");
            Need(report,typeof(ProductPurchase).GetProperty("currency").PropertyType==typeof(Currency),"SdkCurrencyType");
            Need(report,Api("GetProducts",typeof(ProductId[]),typeof(Action<global::RuStore.RuStoreError>),typeof(Action<List<Product>>)),"RealSdkProductsApi");
            Need(report,Api("GetPurchase",typeof(PurchaseId),typeof(Action<global::RuStore.RuStoreError>),typeof(Action<IPurchase>))&&Api("GetPurchases",typeof(Action<global::RuStore.RuStoreError>),typeof(Action<List<IPurchase>>)),"RealSdkRecoveryApi");
            Need(report,Api("GetPurchases",typeof(ProductType?),typeof(Enum),typeof(AcknowledgementState?),typeof(Action<global::RuStore.RuStoreError>),typeof(Action<List<IPurchase>>)),"RealSdkRecoveryFilters");
            Need(report,Api("ConfirmTwoStepPurchase",typeof(PurchaseId),typeof(DeveloperPayload),typeof(Action<global::RuStore.RuStoreError>),typeof(Action))&&Api("CancelTwoStepPurchase",typeof(PurchaseId),typeof(Action<global::RuStore.RuStoreError>),typeof(Action)),"CaptureAndCancelAreSeparate");
            Need(report,Api("UpdateAcknowledgementState",typeof(PurchaseId),typeof(AcknowledgementState),typeof(DeveloperPayload),typeof(Action<global::RuStore.RuStoreError>),typeof(Action<AcknowledgementState>)),"AcknowledgementApiIsSeparate");
            Need(report,Enum.GetNames(typeof(AcknowledgementState)).SequenceEqual(new[]{"PENDING","ACKNOWLEDGED","UNKNOWN"}),"ActualAcknowledgementEnum");
            Need(report,Enum.GetNames(typeof(ProductPurchaseStatus)).SequenceEqual(new[]{"INVOICE_CREATED","CANCELLED","PROCESSING","REJECTED","CONFIRMED","REFUNDED","REFUNDING","EXECUTING","EXPIRED","PAID","REVERSED"}),"ExactPinnedPurchaseStatusEnum");
            Need(report,!Enum.GetNames(typeof(ProductPurchaseStatus)).Contains("CONSUMED")&&!typeof(RuStorePayClient).GetMethods().Any(method=>method.Name=="DeletePurchase"),"NoLegacyDeleteOrConsumedContract");
            Need(report,Enum.GetNames(typeof(ProductPurchaseStatus)).Contains("PAID")&&Enum.GetNames(typeof(ProductPurchaseStatus)).Contains("CONFIRMED")&&Enum.GetNames(typeof(PurchaseType)).Contains("TWO_STEP"),"HeldAndCapturedStatesRemainDistinct");
            var native=Purchase(payload,new Price(12345),new Currency("RUB"));
            Need(report,native.price.value==12345&&native.currency.value=="RUB"&&native.status==ProductPurchaseStatus.CONFIRMED&&native.developerPayload.value==payload,"ConstructActualSdkPurchase");
            var map=typeof(RuStorePayAdapter).GetMethod("Map",BindingFlags.Static|BindingFlags.NonPublic);
            Need(report,map!=null,"ActualAdapterMapPresent");
            var observed=(PayPurchase)map.Invoke(null,new object[]{native});
            Need(report,observed.amountMinor==12345&&observed.currency=="RUB","ActualAdapterMapsSdkAmountAndCurrency");
            Need(report,observed.status=="CONFIRMED"&&observed.purchaseType=="ONE_STEP"&&observed.acknowledgementState=="PENDING"&&observed.productType=="CONSUMABLE_PRODUCT","ActualAdapterMapsSdkStates");
            Need(report,observed.developerPayload==payload&&observed.locator.invoiceId=="123456"&&observed.locator.orderId==order&&observed.locator.quantity==1&&!observed.locator.sandbox,"ActualAdapterMapsSdkCorrelation");
            var missing=(PayPurchase)map.Invoke(null,new object[]{Purchase(payload,null,null)});
            Need(report,missing.amountMinor==null&&missing.currency==null,"MissingSdkMoneyIsNotInvented");
            var held=(PayPurchase)map.Invoke(null,new object[]{Purchase(payload,new Price(12345),new Currency("RUB"),ProductPurchaseStatus.PAID,PurchaseType.TWO_STEP)});
            var request=new PayRequest(order,"unregistered.review125.only",player,payload,1,false);
            var receipt=new PayDeliveryReceipt(order,request.productId,player,observed.locator.purchaseId,observed.locator.invoiceId,"synthetic-not-a-server-receipt",false,true,true);
            Need(report,held.status=="PAID"&&held.purchaseType=="TWO_STEP"&&!receipt.Matches(request,held),"HeldFundsCannotSatisfyDeliveryReceipt");
            Need(report,typeof(PayDeliveryCoordinator).GetConstructor(new[]{typeof(IPayStore),typeof(IPayAuthority),typeof(IPayJournal)})!=null&&typeof(FilePayJournal).GetConstructor(new[]{typeof(string),typeof(string)})!=null,"CurrentCoordinatorAndJournalCompiled");
            var registered=UnityEditor.PackageManager.PackageInfo.GetAllRegisteredPackages();
            foreach(var pin in inputs.packages){var package=Array.Find(registered,p=>p.name==pin.name);Need(report,package!=null&&package.version==pin.version,"ExactOfficialPackageVersion");string manifest=Path.Combine(package.resolvedPath,"package.json");string minimum=JsonUtility.FromJson<PackageJson>(File.ReadAllText(manifest)).unity;string hash=Hash(manifest);
                Need(report,hash==pin.packageManifestSHA256&&minimum==pin.vendorUnityMinimum,"StockVendorMetadataUnmodified");report.packages.Add(new PackageProof{name=package.name,version=package.version,source=package.source.ToString(),resolvedPath=package.resolvedPath,unity=minimum,manifestSHA256=hash});}
            Need(report,RuStorePayClient.PluginVersion=="11.1.0"&&RuStore.CoreClient.RuStoreCoreClient.PluginVersion=="10.5.0","ActualPluginVersionConstants");
            BindingChecks(report,project);
            report.status="PASS_NATIVE_RUSTORE_SDK125_CURRENT_API";exit=0;
        }catch(Exception error){report.error=error.GetType().Name+":"+error.Message;}
        if(string.IsNullOrEmpty(output))throw new InvalidOperationException("RootOwnedFreshOutputRequired");Directory.CreateDirectory(Path.Combine(output,"Native"));
        using(var file=new FileStream(Path.Combine(output,"Native","RuStoreSdk125.json"),FileMode.CreateNew,FileAccess.Write,FileShare.None))using(var writer=new StreamWriter(file,new UTF8Encoding(false)))writer.Write(JsonUtility.ToJson(report,true));
        EditorApplication.Exit(exit);
    }
}
#endif

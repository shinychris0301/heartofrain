#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using HeartOfTheRain.App.RuStore;
using RuStore.PayClient;
using UnityEditor;
using UnityEngine;

// Copied only into the isolated review project. Never imported by the game.
public static class RuStoreSdk86Verification {
    [Serializable] sealed class Source {public string source,copied,sha256;}
    [Serializable] sealed class Pin {public string name,version,packageManifestSHA256,vendorUnityMinimum;}
    [Serializable] sealed class Inputs {public string runId;public Source[] sources;public Pin[] packages;}
    [Serializable] sealed class PackageJson {public string unity;}
    [Serializable] sealed class PackageProof {public string name,version,unity,source,resolvedPath,manifestSHA256;}
    [Serializable] sealed class Result {
        public string status="FAIL_NATIVE_RUSTORE_SDK86_CURRENT_API",utc,unity,runId,error,inputManifestSHA256;
        public int checks;public bool apiCompileOnly=true,sdkDefineEnabled,sdkInitialized=false,paymentCalls=false,androidBuild=false,gameSdkEnabled=false;
        public string scope="Current exact game adapter/contracts/coordinator/file-journal compiled with HOTR_RUSTORE_PAY against stock official Pay11.1.0/Core10.5.0 in pinned Unity2022.3.62f3 Editor. No singleton initialization, provider/payment call, Android/native build, ordinary-game SDK inclusion, vendor-support certification or production enablement.";
        public Source[] sources;public List<PackageProof> packages=new List<PackageProof>();
    }
    static string Hash(string path){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
    static void Need(Result report,bool value,string code){report.checks++;if(!value)throw new InvalidOperationException(code);}
    static bool Api(string name,params Type[] parameters){return typeof(RuStorePayClient).GetMethods().Any(method=>method.Name==name&&!method.IsStatic&&method.ReturnType==typeof(void)&&method.GetParameters().Select(parameter=>parameter.ParameterType).SequenceEqual(parameters));}
    public static void Run(){
        var report=new Result{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};int exit=1;
        string project=Path.GetDirectoryName(Application.dataPath),output=Environment.GetEnvironmentVariable("HOTR_REVIEW86_SDK_OUTPUT");
        try{
            Need(report,Application.isBatchMode&&Application.unityVersion=="2022.3.62f3","PinnedBatchEditorRequired");
            string path=Path.Combine(project,"ProofInputs86.json");report.inputManifestSHA256=Hash(path);var inputs=JsonUtility.FromJson<Inputs>(File.ReadAllText(path,Encoding.UTF8));report.runId=inputs.runId;report.sources=inputs.sources;
            Need(report,inputs.sources!=null&&inputs.sources.Length==8&&inputs.packages!=null&&inputs.packages.Length==2,"ExactInputsRequired");
            foreach(var source in inputs.sources){string copy=Path.GetFullPath(Path.Combine(project,source.copied));Need(report,copy.StartsWith(project+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)&&Hash(copy)==source.sha256,"CurrentSourceBinding");}
#if HOTR_RUSTORE_PAY
            report.sdkDefineEnabled=true;
#endif
            var adapter=new RuStorePayAdapter();Need(report,report.sdkDefineEnabled&&adapter.SdkCompiled&&!adapter.Configured,"SdkBranchCompiledButNotInitialized");
            const string player="00000000000000000000000000000000",order="11111111111111111111111111111111",payload="hotr-order-v1:11111111111111111111111111111111:22222222222222222222222222222222";
            var parameters=new ProductPurchaseParams(new ProductId("unregistered.review86.only"),appUserId:new AppUserId(player),developerPayload:new DeveloperPayload(payload),orderId:new OrderId(order),quantity:new Quantity(1));
            Need(report,parameters.appUserId.value==player&&parameters.orderId.value==order&&parameters.developerPayload.value==payload&&parameters.quantity.value==1,"RealSdkRequestCorrelation");
            Need(report,Api("GetProducts",typeof(ProductId[]),typeof(Action<global::RuStore.RuStoreError>),typeof(Action<List<Product>>))&&typeof(Product).GetProperties().Any(property=>property.Name=="amountLabel"&&property.PropertyType==typeof(AmountLabel)&&property.CanRead),"RealSdkProductsAndDisplayPrice");
            Need(report,Api("GetPurchase",typeof(PurchaseId),typeof(Action<global::RuStore.RuStoreError>),typeof(Action<IPurchase>))&&Api("GetPurchases",typeof(Action<global::RuStore.RuStoreError>),typeof(Action<List<IPurchase>>)),"RealSdkRecoveryApi");
            Need(report,Api("ConfirmTwoStepPurchase",typeof(PurchaseId),typeof(DeveloperPayload),typeof(Action<global::RuStore.RuStoreError>),typeof(Action))&&Api("UpdateAcknowledgementState",typeof(PurchaseId),typeof(AcknowledgementState),typeof(DeveloperPayload),typeof(Action<global::RuStore.RuStoreError>),typeof(Action<AcknowledgementState>)),"CaptureAcknowledgementSeparate");
            Need(report,typeof(RuStorePaymentException.ProductPurchaseCancelled)!=null&&typeof(RuStorePaymentException.ProductPurchaseException)!=null,"RealSdkFailureTypesCompiled");
            Need(report,typeof(PayDeliveryCoordinator).GetConstructor(new[]{typeof(IPayStore),typeof(IPayAuthority),typeof(IPayJournal)})!=null&&typeof(FilePayJournal).GetConstructor(new[]{typeof(string),typeof(string)})!=null,"CurrentCoordinatorAndJournalCompiled");
            var registered=UnityEditor.PackageManager.PackageInfo.GetAllRegisteredPackages();
            foreach(var pin in inputs.packages){var package=Array.Find(registered,p=>p.name==pin.name);Need(report,package!=null&&package.version==pin.version,"ExactOfficialPackageVersion");string manifest=Path.Combine(package.resolvedPath,"package.json");string minimum=JsonUtility.FromJson<PackageJson>(File.ReadAllText(manifest)).unity;string hash=Hash(manifest);
                Need(report,hash==pin.packageManifestSHA256&&minimum==pin.vendorUnityMinimum,"StockVendorMetadataUnmodified");report.packages.Add(new PackageProof{name=package.name,version=package.version,source=package.source.ToString(),resolvedPath=package.resolvedPath,unity=minimum,manifestSHA256=hash});}
            Need(report,RuStorePayClient.PluginVersion=="11.1.0"&&RuStore.CoreClient.RuStoreCoreClient.PluginVersion=="10.5.0","ActualPluginVersionConstants");
            report.status="PASS_NATIVE_RUSTORE_SDK86_CURRENT_API";exit=0;
        }catch(Exception error){report.error=error.GetType().Name+":"+error.Message;}
        if(string.IsNullOrEmpty(output))throw new InvalidOperationException("RootOwnedFreshOutputRequired");Directory.CreateDirectory(Path.Combine(output,"Native"));
        using(var file=new FileStream(Path.Combine(output,"Native","RuStoreSdk86.json"),FileMode.CreateNew,FileAccess.Write,FileShare.None))using(var writer=new StreamWriter(file,new UTF8Encoding(false)))writer.Write(JsonUtility.ToJson(report,true));
        EditorApplication.Exit(exit);
    }
}
#endif

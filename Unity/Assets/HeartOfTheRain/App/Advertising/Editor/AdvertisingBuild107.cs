#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using HeartOfTheRain.App.ServerGameplay;
using UnityEditor;
using UnityEditor.Android;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace HeartOfTheRain.App.Advertising.Editor {
    // Only the explicit build entry can create this private in-memory authority.
    // A leftover file or a caller-supplied policy-test boolean never owns a build.
    public static class AdvertisingBuild107 {
        public const string Package="com.heartoftherain.ads107review",Company="HeartRainAds107";
        const string Marker=".hotr-ads107-active.json",Vendor="0d0a2546dd752d6b02864df5833767703ae88d5b292da0e0b8eec815d7f066c3";
        const string ManagedPath="Assets/HeartOfTheRain/Resources/HOTR_Server/ManagedStaging.json";
        const string ManagedPackage="com.heartoftherain.stagingreview";
        static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
        static Context active;
        [Serializable] sealed class Receipt {public int version;public string status,sourceRoot,project,nonce,unity,packageName,vendorSHA256;public string[] paths,sha256;}
        [Serializable] sealed class Proof {public int version=1,pid;public string nonce,adsSHA,managedSHA;}
        [Serializable] sealed class Report {
            public string status="FAIL_ADS107",operation,unity,code,apk,apkSHA256,receiptSHA256;
            public int checks,errors=-1,warnings=-1;public long bytes;
            public bool actualBuild,development,scriptDebugging,managedPackaging,cleanupVerified,sourcePreserved,
                actualSdkBranchCompiled,adsEnabled,automaticSdkRequests=false,productionApproved=false;
            public string scope="Owned isolatedLTS SDK/configuration packaging and optional actual development Android compilation. No app launch/install, SDK initialization/load/show, impression, reward, public hosting or provider/privacy certification. AppMetrica remains a required dependency; privacy controls do not imply zero provider collection.";
            public List<string> passed=new List<string>(),failures=new List<string>();
        }
        static string Full(string p)=>Path.GetFullPath(p).TrimEnd(Path.DirectorySeparatorChar,Path.AltDirectorySeparatorChar);
        static bool Under(string p,string root)=>Full(p).StartsWith(Full(root)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase);
        static string Hash(byte[] data){using(var h=SHA256.Create())return string.Concat(h.ComputeHash(data).Select(v=>v.ToString("x2")));}
        static string HashFile(string p)=>Hash(File.ReadAllBytes(p));
        static void Need(bool ok,string code){if(!ok)throw new InvalidOperationException(code);}
        static void Plain(string p){Need(!Full(p).StartsWith("\\\\",StringComparison.Ordinal),"Ads107LocalPathRequired");for(var d=new DirectoryInfo(Path.GetDirectoryName(Full(p)));d!=null;d=d.Parent)if(d.Exists)Need((d.Attributes&FileAttributes.ReparsePoint)==0,"Ads107LinkedPath");if(File.Exists(p))Need((File.GetAttributes(p)&FileAttributes.ReparsePoint)==0,"Ads107LinkedPath");}
        static string Small(string p){Plain(p);var f=new FileInfo(p);Need(f.Exists&&f.Length>=2&&f.Length<=8192,"Ads107ConfigurationMissingOrOversized");return File.ReadAllText(p,Utf8);}
        static string CanonicalAds(string json){RewardedAdsConfiguration85 c;string why;Need(RewardedAdsConfiguration85.TryParsePackaged(json,out c,out why),"Ads107ConfigurationInvalid");Need(c.rewardedUnitId==AdvertisingConfiguration107.RewardedUnitId&&c.interstitialUnitId==AdvertisingConfiguration107.InterstitialUnitId,"Ads107PlacementMismatch");return RewardedAdsConfiguration85.CanonicalPackagedJson(c);}
        static string CanonicalManaged(string json){string canonical;Need(AdvertisingConfiguration107.TryCanonicalManagedBuild107(json,out canonical),"Ads107ManagedConfigurationInvalid");return canonical;}
        static Receipt ValidateReceipt(){
            string path=Environment.GetEnvironmentVariable("HOTR_ADS107_RECEIPT");Need(!string.IsNullOrEmpty(path),"Ads107ReceiptRequired");Need(Full(path)==Full(Path.Combine(Directory.GetParent(Full(".")).FullName,"Preparation.json")),"Ads107ReceiptInvalid");Plain(path);var file=new FileInfo(path);Need(file.Exists&&file.Length<8*1024*1024,"Ads107ReceiptInvalid");
            var r=JsonUtility.FromJson<Receipt>(File.ReadAllText(path,Utf8));string project=Full(".");
            Need(r!=null&&r.version==1&&r.status=="PREPARED_ADS107"&&r.unity=="6000.3.27f1"&&Application.unityVersion==r.unity&&r.packageName==Package&&r.vendorSHA256==Vendor,"Ads107ReceiptInvalid");
            Need(!string.IsNullOrEmpty(r.sourceRoot)&&Full(r.sourceRoot)==Full(Path.Combine(project,"../../../../.."))&&File.Exists(Path.Combine(r.sourceRoot,"AGENTS.md"))&&Under(project,Path.Combine(r.sourceRoot,".verification-cache","Review107","Candidates"))&&Full(r.project)==project&&Regex.IsMatch(r.nonce??"",@"\A[0-9a-f]{32}\z"),"Ads107ReceiptInvalid");
            Need(r.paths!=null&&r.sha256!=null&&r.paths.Length>100&&r.paths.Length==r.sha256.Length,"Ads107ReceiptInvalid");
            var seen=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            for(int i=0;i<r.paths.Length;i++){string relative=r.paths[i],p=Full(Path.Combine(project,relative??""));Need(relative!=null&&relative.StartsWith("Assets/",StringComparison.Ordinal)&&!relative.Contains("\\")&&!relative.Split('/').Any(v=>v==".."||v==""||v.Contains(":"))&&Under(p,project)&&seen.Add(relative)&&Regex.IsMatch(r.sha256[i]??"",@"\A[0-9a-f]{64}\z"),"Ads107ReceiptInvalid");Plain(p);Need(File.Exists(p)&&HashFile(p)==r.sha256[i],"Ads107SourceChanged");}
            Need(new[]{AdvertisingConfiguration107.ResourceAssetPath,"Assets/HeartOfTheRain/App/Advertising/Runtime/YandexRewardedAdsProvider85.cs","Assets/YandexMobileAds/RewardedAdLoader.cs","Assets/Plugins/Android/yandex-ads-unity-plugin.aar","Assets/Plugins/Android/AndroidManifest.xml","Assets/Plugins/Android/mainTemplate.gradle","Assets/Plugins/Android/launcherTemplate.gradle","Assets/Plugins/Android/settingsTemplate.gradle","Assets/Plugins/Android/gradleTemplate.properties","Assets/csc.rsp"}.All(seen.Contains),"Ads107ReceiptCriticalInputsMissing");
            Need(HashFile("Assets/Plugins/Android/yandex-ads-unity-plugin.aar")=="9420d5d297f6bad315f691b9083063b5f22f5c0883a02549f8c96f98b9e476ef","Ads107PinnedNativePluginRequired");
            Need(PlayerSettings.companyName==Company&&PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android)==Package&&!File.Exists(Marker)&&!File.Exists(ManagedPath)&&!Directory.Exists(Path.GetDirectoryName(ManagedPath))&&!File.Exists(Path.GetDirectoryName(ManagedPath)+".meta"),"Ads107CandidateOrStalePayload");return r;
        }
        public static bool ReservedAdsPath(string p){if(string.IsNullOrEmpty(p)||p.EndsWith(".meta",StringComparison.OrdinalIgnoreCase))return false;string n=p.Replace('\\','/');int i=n.LastIndexOf("/Resources/",StringComparison.OrdinalIgnoreCase);if(i<0)return false;string key=n.Substring(i+11);if(key.StartsWith(AdvertisingConfiguration107.ResourceKey+"/",StringComparison.OrdinalIgnoreCase))return true;int dot=key.LastIndexOf('.');return string.Equals(dot<0?key:key.Substring(0,dot),AdvertisingConfiguration107.ResourceKey,StringComparison.OrdinalIgnoreCase);}
        static string[] ResourcePaths()=>AssetDatabase.GetAllAssetPaths().Where(ReservedAdsPath).ToArray();
        public static string[] VerifyBoundary(BuildTarget target,BuildOptions options,string package,bool customSigning,bool sdk,bool enabled,bool ownedProfile,bool managed,string[] resources,string channel){
            var errors=new List<string>();var paths=(resources??Array.Empty<string>()).Where(ReservedAdsPath).ToArray();
            if(paths.Length>0&&(paths.Length!=1||paths[0]!=AdvertisingConfiguration107.ResourceAssetPath))errors.Add("Ads107ResourceCollision");
            if(!sdk&&!enabled&&!ownedProfile)return errors.ToArray();
            if(!sdk)errors.Add("Ads107SdkRequired");if(!ownedProfile)errors.Add("Ads107OwnedProfileRequired");
            if(paths.Length!=1)errors.Add("Ads107PayloadRequired");if(target!=BuildTarget.Android)errors.Add("Ads107AndroidOnly");
            if((options&BuildOptions.Development)==0)errors.Add("Ads107DevelopmentOnly");if((options&(BuildOptions.AllowDebugging|BuildOptions.ConnectWithProfiler|BuildOptions.EnableDeepProfilingSupport))!=0)errors.Add("Ads107NoScriptDebugging");
            if(package!=(managed?ManagedPackage:Package))errors.Add("Ads107PackageMismatch");if(customSigning)errors.Add("Ads107DebugSigningOnly");if(channel=="rustore")errors.Add("Ads107ProductionChannelBlocked");return errors.ToArray();
        }
        static bool SdkCompiled {
            get{
#if HOTR_YANDEX_ADS
                return typeof(YandexRewardedAdsProvider85).GetField("loader",BindingFlags.Instance|BindingFlags.NonPublic)!=null&&Type.GetType("YandexMobileAds.RewardedAdLoader, Assembly-CSharp")!=null;
#else
                return false;
#endif
            }
        }
        static string SelectedGradlePath {
            get {
#if UNITY_6000_0_OR_NEWER
                return AndroidExternalToolsSettings.Gradle.path;
#else
                // Main2022 compiles policy checks only. ValidateReceipt rejects
                // this engine before the isolated-LTS build entry reaches here.
                return null;
#endif
            }
        }
        public static string[] VerifyActiveBoundary(BuildTarget target,BuildOptions options){
            RewardedAdsConfiguration85 c;string why;var paths=ResourcePaths();bool valid=paths.Length==1&&RewardedAdsConfiguration85.TryParsePackaged((AssetDatabase.LoadMainAssetAtPath(AdvertisingConfiguration107.ResourceAssetPath) as TextAsset)?.text,out c,out why);
            bool enabled=false;if(valid){RewardedAdsConfiguration85.TryParsePackaged((AssetDatabase.LoadMainAssetAtPath(AdvertisingConfiguration107.ResourceAssetPath) as TextAsset).text,out c,out why);enabled=c.enabled;}
            var errors=VerifyBoundary(target,options,PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android),PlayerSettings.Android.useCustomKeystore,SdkCompiled,enabled,active!=null&&active.Matches(),active!=null&&active.Managed,paths,Environment.GetEnvironmentVariable("HOTR_BUILD_CHANNEL")).ToList();
            if(paths.Length>0&&!valid)errors.Add("Ads107ImportedPayloadInvalid");if(!SdkCompiled&&(Directory.Exists("Assets/YandexMobileAds")||File.Exists("Assets/Plugins/Android/yandex-ads-unity-plugin.aar")))errors.Add("Ads107SdkDefineRequired");if(active!=null&&active.Managed){var managed=AssetDatabase.GetAllAssetPaths().Where(HeartOfTheRain.App.ServerGameplay.Editor.StagingServerBuild104.ReservedResourcePath).ToArray();if(managed.Length!=1||managed[0]!=ManagedPath)errors.Add("Ads107ManagedResourceCollision");}return errors.ToArray();
        }
        //104 retains its original authority. Only this live validated107 lease
        //may handle a configured107 SDK build, never a caller-provided boolean.
        public static bool GuardManagedBuild(BuildReport report){
            if(active==null||!active.Managed)return false;
            Need(report!=null&&VerifyActiveBoundary(report.summary.platform,report.summary.options).Length==0,"Ads107ManagedBoundaryInvalid");active.ValidateImported();return true;
        }
        public static string[] CombinedErrors126()=>AdvertisingCombinedBoundary126.ActualErrors();
        internal static void Guard(BuildReport report){
            if(HeartOfTheRain.App.ServerGameplay.Editor.ProductionBuildConfiguration122.GuardIfSelected(report)){
                var sdk=HeartOfTheRain.App.ServerGameplay.ServerProductionConfiguration122.ReadResource(HeartOfTheRain.App.ShopCheckout86.CheckoutSdkConfiguration125.ResourceKey);
                if(sdk.present||HeartOfTheRain.App.ShopCheckout86.CheckoutSdkConfiguration125.Required){var combined=CombinedErrors126();if(combined.Length>0)throw new BuildFailedException(string.Join(",",combined));}
                return;
            }
            var errors=VerifyActiveBoundary(report.summary.platform,report.summary.options);if(errors.Length>0)throw new BuildFailedException(string.Join(",",errors));if(active!=null)active.ValidateImported();
        }
        sealed class Context:IDisposable {
            readonly Receipt receipt;readonly byte[] originalAds,selectedAds,managed,proof;readonly string adsPath,managedPath,marker,folder,am,fm;readonly Action import;readonly byte[] assetMeta,folderMeta;bool markerOwned,resourceOwned,adsChanged;
            public bool Managed=>managed!=null;
            static bool Equal(string p,byte[] b)=>File.Exists(p)&&File.ReadAllBytes(p).SequenceEqual(b);
            static bool Same(string a,string b)=>string.Equals(Full(a),Full(b),StringComparison.OrdinalIgnoreCase);
            static void Exclusive(string p,byte[] b){using(var f=new FileStream(p,FileMode.CreateNew,FileAccess.Write,FileShare.None)){f.Write(b,0,b.Length);f.Flush(true);}}
            public Context(Receipt r,string ads,string server,string project,Action importer){receipt=r;import=importer;adsPath=Full(Path.Combine(project,AdvertisingConfiguration107.ResourceAssetPath));managedPath=Full(Path.Combine(project,ManagedPath));marker=Full(Path.Combine(project,Marker));Plain(adsPath);Plain(managedPath);Plain(marker);originalAds=File.ReadAllBytes(adsPath);selectedAds=Utf8.GetBytes(CanonicalAds(ads));managed=server==null?null:Utf8.GetBytes(CanonicalManaged(server));folder=Full(Path.GetDirectoryName(managedPath));am=managedPath+".meta";fm=folder+".meta";assetMeta=Utf8.GetBytes("fileFormatVersion: 2\nguid: "+Guid.NewGuid().ToString("N")+"\nTextScriptImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n");folderMeta=Utf8.GetBytes("fileFormatVersion: 2\nguid: "+Guid.NewGuid().ToString("N")+"\nfolderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n");proof=Utf8.GetBytes(JsonUtility.ToJson(new Proof{pid=System.Diagnostics.Process.GetCurrentProcess().Id,nonce=r.nonce,adsSHA=Hash(selectedAds),managedSHA=managed==null?null:Hash(managed)}));}
            public void Create(){Need(!File.Exists(marker),"Ads107StaleLease");if(Managed)Need(!Directory.Exists(folder)&&!File.Exists(folder)&&!File.Exists(fm),"Ads107ForeignManagedPayload");Exclusive(marker,proof);markerOwned=true;try{adsChanged=true;File.WriteAllBytes(adsPath,selectedAds);if(Managed){Directory.CreateDirectory(folder);resourceOwned=true;Exclusive(fm,folderMeta);Exclusive(managedPath,managed);Exclusive(am,assetMeta);}import?.Invoke();Need(Matches(),"Ads107ImportOwnershipChanged");}catch{Dispose();throw;}}
            bool PinnedCode(){if(receipt.paths==null)return true;for(int i=0;i<receipt.paths.Length;i++){string p=receipt.paths[i];if(p.EndsWith(".cs",StringComparison.Ordinal)||p.EndsWith(".aar",StringComparison.Ordinal)||p.EndsWith(".xml",StringComparison.Ordinal)||p.EndsWith(".gradle",StringComparison.Ordinal)||p.EndsWith(".properties",StringComparison.Ordinal)||p=="Assets/csc.rsp")if(!File.Exists(p)||HashFile(p)!=receipt.sha256[i])return false;}return true;}
            public bool Matches()=>markerOwned&&Equal(marker,proof)&&Equal(adsPath,selectedAds)&&PinnedCode()&&(!Managed||resourceOwned&&Equal(managedPath,managed)&&Equal(am,assetMeta)&&Equal(fm,folderMeta));
            public void ValidateImported(){Need(Matches(),"Ads107LeaseInvalid");var cfg=AssetDatabase.LoadMainAssetAtPath(AdvertisingConfiguration107.ResourceAssetPath) as TextAsset;Need(cfg&&CanonicalAds(cfg.text)==Utf8.GetString(selectedAds),"Ads107ImportedAdsMismatch");if(Managed){var value=AssetDatabase.LoadMainAssetAtPath(ManagedPath) as TextAsset;Need(value&&CanonicalManaged(value.text)==Utf8.GetString(managed),"Ads107ImportedManagedMismatch");}}
            public void Dispose(){if(!markerOwned)return;Need(Equal(marker,proof),"Ads107ForeignMarkerPreserved");if(adsChanged)Need(Equal(adsPath,selectedAds),"Ads107ForeignAdsBytesPreserved");if(resourceOwned){Need(Equal(managedPath,managed)&&Equal(am,assetMeta)&&Equal(fm,folderMeta),"Ads107ForeignManagedBytesPreserved");Need(Directory.GetFileSystemEntries(folder).All(p=>Same(p,managedPath)||Same(p,am)),"Ads107ForeignManagedFilesPreserved");File.Delete(managedPath);File.Delete(am);Directory.Delete(folder,false);File.Delete(fm);}if(adsChanged)File.WriteAllBytes(adsPath,originalAds);File.Delete(marker);markerOwned=false;import?.Invoke();}
        }
        static void WithLease(Receipt receipt,string ads,string managed,Action body){Need(active==null,"Ads107AlreadyActive");string package=PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android);bool signing=PlayerSettings.Android.useCustomKeystore;var context=new Context(receipt,ads,managed,Full("."),()=>AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport));try{PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android,managed==null?Package:ManagedPackage);PlayerSettings.Android.useCustomKeystore=false;context.Create();active=context;body();}finally{active=null;try{context.Dispose();}finally{PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android,package);PlayerSettings.Android.useCustomKeystore=signing;AssetDatabase.SaveAssets();}}}
        static void Check(Report r,bool ok,string name){if(r.operation=="Policy")r.scope="Actual mainEditor pure boundary checks plus real disposable file-lease faults. SDK/platform/ownership booleans are explicit policy fixtures; no actual SDK import, LTS packaging, BuildPipeline, HTTP, ad, profile or device operation.";r.checks++;Need(ok,name);r.passed.Add(name);}
        const string FixtureManaged="{\"version\":1,\"mode\":\"ManagedGuestServer\",\"origin\":\"https://staging.hotr-native-fixture.net\",\"identityScope\":\"review-ads107\",\"allowDevelopmentLoopback\":false,\"socialEnabled\":true}";
        static void FileLeaseChecks(Report r){
            string repo=Full("..");Need(File.Exists(Path.Combine(repo,"AGENTS.md")),"Ads107MainPolicyFixtureOnly");
            string ads=File.ReadAllText(AdvertisingConfiguration107.ResourceAssetPath,Utf8);
            foreach(string name in new[]{"success","importThrow","buildThrow","stale","foreignFolder","foreignAds","foreignChild"}){
                string root=Path.Combine(repo,".verification-cache","Review107","LeaseCases",Guid.NewGuid().ToString("N"),name);Directory.CreateDirectory(Path.Combine(root,Path.GetDirectoryName(AdvertisingConfiguration107.ResourceAssetPath)));string file=Path.Combine(root,AdvertisingConfiguration107.ResourceAssetPath),marker=Path.Combine(root,Marker),managed=Path.Combine(root,ManagedPath);File.WriteAllText(file,ads,Utf8);int imports=0;
                var context=new Context(new Receipt{nonce=Guid.NewGuid().ToString("N")},ads,FixtureManaged,root,()=>{imports++;if(name=="importThrow"&&imports==1)throw new InvalidOperationException("Expected107ImportFailure");});
                if(name=="stale")File.WriteAllText(marker,"foreign",Utf8);if(name=="foreignFolder"){Directory.CreateDirectory(Path.GetDirectoryName(managed));File.WriteAllText(Path.Combine(Path.GetDirectoryName(managed),"foreign.txt"),"foreign",Utf8);}
                bool failed=false;try{context.Create();if(name=="foreignAds")File.WriteAllText(file,"foreign",Utf8);if(name=="foreignChild")File.WriteAllText(Path.Combine(Path.GetDirectoryName(managed),"foreign.txt"),"foreign",Utf8);if(name=="buildThrow")throw new InvalidOperationException("Expected107BuildFailure");context.Dispose();}catch(InvalidOperationException){failed=true;if(name=="buildThrow")context.Dispose();}
                if(name=="success"||name=="importThrow"||name=="buildThrow")Check(r,failed==(name!="success")&&!File.Exists(marker)&&!Directory.Exists(Path.GetDirectoryName(managed))&&File.ReadAllText(file,Utf8)==ads,"FileLeaseCleanup_"+name);
                else if(name=="stale")Check(r,failed&&File.ReadAllText(marker,Utf8)=="foreign"&&File.ReadAllText(file,Utf8)==ads,"FileLeaseStalePreserved");
                else if(name=="foreignFolder")Check(r,failed&&File.ReadAllText(Path.Combine(Path.GetDirectoryName(managed),"foreign.txt"),Utf8)=="foreign"&&!File.Exists(marker),"FileLeaseForeignFolderPreserved");
                else Check(r,failed&&File.Exists(marker)&&(name=="foreignAds"?File.ReadAllText(file,Utf8)=="foreign":File.ReadAllText(Path.Combine(Path.GetDirectoryName(managed),"foreign.txt"),Utf8)=="foreign"),"FileLeaseForeignMutationPreserved_"+name);
            }
        }
        public static void RunPolicy(){var r=new Report{operation="Policy",unity=Application.unityVersion};try{string path=AdvertisingConfiguration107.ResourceAssetPath;Check(r,VerifyBoundary(BuildTarget.Android,BuildOptions.Development,Package,false,true,false,true,false,new[]{path},null).Length==0,"OwnedSdkBoundaryAllowed");Check(r,VerifyBoundary(BuildTarget.Android,BuildOptions.Development,ManagedPackage,false,true,true,true,true,new[]{path},null).Length==0,"OwnedManagedSdkBoundaryAllowed");Check(r,VerifyBoundary(BuildTarget.Android,BuildOptions.Development,Package,false,false,false,false,false,new[]{path},null).Length==0,"OrdinaryDisabledSdkFreeAllowed");foreach(var item in new[]{"ownership","release","platform","package","signing","debugger","channel","collision","missingSdk"}){var e=VerifyBoundary(item=="platform"?BuildTarget.StandaloneWindows64:BuildTarget.Android,item=="release"?BuildOptions.None:BuildOptions.Development|(item=="debugger"?BuildOptions.AllowDebugging:BuildOptions.None),item=="package"?"com.other.app":Package,item=="signing",item!="missingSdk",true,item!="ownership",false,item=="collision"?new[]{path,"Assets/Other/Resources/HOTR_Advertising/Configuration.txt"}:new[]{path},item=="channel"?"rustore":null);Check(r,e.Length>0,"Reject_"+item);}Check(r,ReservedAdsPath("Assets/Other/Resources/hotr_advertising/CONFIGURATION.asset")&&ReservedAdsPath("Assets/Other/Resources/"+AdvertisingConfiguration107.ResourceKey+"/child.txt")&&!ReservedAdsPath(path+".meta"),"ResourceShadowsDetected");FileLeaseChecks(r);r.status="PASS_NATIVE_ADS107_BUILD_POLICY";}catch(Exception e){r.code=e.Message;r.failures.Add(e.GetType().Name);}Write(r,"BuildPolicy107.json");}
        public static void RunPackaging()=>Run(false,true);
        public static void BuildDevelopment()=>Run(true,false);
        static void CheckRuntimeAds(Report r,RewardedAdsConfiguration85 expected){
            RewardedAdsConfiguration85 actual;string error;bool available=RewardedAdsConfiguration85.TryRead(out actual,out error);
            Check(r,available==expected.enabled,"ActualAdsRuntimeReaderAvailability");
            if(expected.enabled)Check(r,actual!=null&&error==null&&actual.version==expected.version&&actual.enabled&&actual.rewardedUnitId==expected.rewardedUnitId&&actual.interstitialUnitId==expected.interstitialUnitId&&actual.privacyUrl==expected.privacyUrl&&actual.privacyVersion==expected.privacyVersion,"ActualAdsRuntimeResourceFieldsMatchCanonicalOwnerPayload");
            else Check(r,actual==null&&error=="AdsDisabled","ActualAdsRuntimeReaderDisabled");
        }
        static void Run(bool build,bool packaging){var r=new Report{operation=build?"Build":"Packaging",unity=Application.unityVersion};string oldServerOverride=Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG");
            try{var receipt=ValidateReceipt();r.receiptSHA256=HashFile(Environment.GetEnvironmentVariable("HOTR_ADS107_RECEIPT"));Check(r,SdkCompiled,"ActualSdkManagedBranchCompiled");r.actualSdkBranchCompiled=true;Check(r,Application.unityVersion=="6000.3.27f1"&&EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android,"PinnedLtsAndroidTarget");Check(r,PlayerSettings.Android.minSdkVersion==(AndroidSdkVersions)26&&(int)PlayerSettings.Android.targetSdkVersion==36&&!PlayerSettings.Android.useCustomKeystore,"Api26To36DebugSigning");Check(r,PlayerSettings.GetScriptingBackend(NamedBuildTarget.Android)==ScriptingImplementation.IL2CPP&&PlayerSettings.Android.targetArchitectures==AndroidArchitecture.ARM64,"Arm64Il2cpp");
                string tools=Full(Path.Combine(EditorApplication.applicationContentsPath,"PlaybackEngines","AndroidPlayer"));Check(r,new[]{AndroidExternalToolsSettings.sdkRootPath,AndroidExternalToolsSettings.jdkRootPath,AndroidExternalToolsSettings.ndkRootPath,SelectedGradlePath}.All(p=>Under(p,tools)),"StockMatchingEditorAndroidToolchain");
                string ads=File.ReadAllText(AdvertisingConfiguration107.ResourceAssetPath,Utf8),managed=null;
                string adsFile=Environment.GetEnvironmentVariable("HOTR_ADS107_ADVERTISING_CONFIG"),managedFile=Environment.GetEnvironmentVariable("HOTR_ADS107_MANAGED_CONFIG");if(!string.IsNullOrEmpty(adsFile))ads=CanonicalAds(Small(adsFile));if(!string.IsNullOrEmpty(managedFile))managed=CanonicalManaged(Small(managedFile));
                RewardedAdsConfiguration85 selectedAds;string adsError;Need(RewardedAdsConfiguration85.TryParsePackaged(ads,out selectedAds,out adsError),"Ads107ConfigurationInvalid");r.adsEnabled=selectedAds.enabled;r.managedPackaging=managed!=null;
                if(packaging){Need(managed!=null,"Ads107ManagedFixtureRequired");Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",null);int calls=0;WithLease(receipt,ads,managed,()=>{Check(r,VerifyActiveBoundary(BuildTarget.Android,BuildOptions.Development).Length==0,"ActualManagedBoundaryAndImportedPayload");CheckRuntimeAds(r,selectedAds);ServerGameplayConfiguration c;string why;Check(r,ServerGameplayConfiguration.TryRead(out c,out why)&&c!=null&&ServerStagingConfiguration104.CanonicalJson(c)==managed,"ActualManagedResourcesReaderWithoutBootstrap");calls++;});Check(r,calls==1&&!File.Exists(ManagedPath)&&!File.Exists(Marker),"ActualManagedSuccessCleanup");bool threw=false;try{WithLease(receipt,ads,managed,()=>{throw new InvalidOperationException("Expected107DelegateFailure");});}catch(InvalidOperationException e){threw=e.Message=="Expected107DelegateFailure";}Check(r,threw&&!File.Exists(ManagedPath)&&!File.Exists(Marker),"ActualManagedFailureCleanup");r.managedPackaging=true;r.status="PASS_NATIVE_ADS107_PACKAGING";}
                else{string output=Environment.GetEnvironmentVariable("HOTR_ADS107_APK");Need(!string.IsNullOrEmpty(output)&&Under(output,Path.Combine(Full("."),"Builds"))&&!File.Exists(output),"Ads107FreshContainedApkRequired");r.apk=Full(output);Directory.CreateDirectory(Path.GetDirectoryName(r.apk));WithLease(receipt,ads,managed,()=>{Check(r,VerifyActiveBoundary(BuildTarget.Android,BuildOptions.Development).Length==0,"ActualOwnedBuildBoundary");r.actualBuild=true;var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{HeartOfTheRain.App.Launch.LaunchPage.ScenePath,HeartOfTheRain.App.Launch.LaunchPage.GameScenePath},locationPathName=r.apk,target=BuildTarget.Android,options=BuildOptions.Development});r.errors=(int)result.summary.totalErrors;r.warnings=(int)result.summary.totalWarnings;r.development=(result.summary.options&BuildOptions.Development)!=0;r.scriptDebugging=(result.summary.options&(BuildOptions.AllowDebugging|BuildOptions.ConnectWithProfiler|BuildOptions.EnableDeepProfilingSupport))!=0;Check(r,result.summary.result==BuildResult.Succeeded&&r.errors==0&&r.development&&!r.scriptDebugging&&File.Exists(r.apk),"ActualDevelopmentApkCompiled");});r.bytes=new FileInfo(r.apk).Length;r.apkSHA256=HashFile(r.apk);r.status="PASS_NATIVE_ADS107_ANDROID_BUILD";}
                Check(r,!File.Exists(Marker)&&!File.Exists(ManagedPath)&&PlayerSettings.GetApplicationIdentifier(NamedBuildTarget.Android)==Package,"TemporaryResourcesAndPackageRestored");ValidateReceipt();r.cleanupVerified=r.sourcePreserved=true;
            }catch(Exception e){r.status="FAIL_NATIVE_ADS107_"+(build?"ANDROID_BUILD":"PACKAGING");r.code=Regex.IsMatch(e.Message??"",@"\A[A-Za-z0-9_]{1,100}\z")?e.Message:e.GetType().Name;r.failures.Add(e.GetType().Name);}
            finally{Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",oldServerOverride);}
            Write(r,build?"AndroidBuild107.json":"Packaging107.json");
        }
        static void Write(Report r,string name){string output=Environment.GetEnvironmentVariable("HOTR_REVIEW107_OUT");if(string.IsNullOrEmpty(output))throw new InvalidOperationException("Ads107OutputRequired");Directory.CreateDirectory(output);using(var stream=new FileStream(Path.Combine(output,name),FileMode.CreateNew,FileAccess.Write))using(var writer=new StreamWriter(stream,Utf8))writer.Write(JsonUtility.ToJson(r,true));if(Application.isBatchMode)EditorApplication.Exit(r.status.StartsWith("PASS",StringComparison.Ordinal)?0:1);}
    }
    public sealed class AdvertisingBuildGuard107:IPreprocessBuildWithReport {public int callbackOrder=>-19000;public void OnPreprocessBuild(BuildReport report)=>AdvertisingBuild107.Guard(report);}
}
#endif

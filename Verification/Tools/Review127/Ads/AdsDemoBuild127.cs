#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using System.Xml;
using System.Xml.Linq;
using UnityEditor;
using UnityEditor.Android;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using HeartOfTheRain.App.Advertising;
using HeartOfTheRain.Verification127;

namespace HeartOfTheRain.Verification127.Editor {
    // Sole guard for an explicitly isolated diagnostic project. Shipping107/125
    // code/config/build barriers are not changed or included in this fixture.
    public static class AdsDemoBuild127 {
        [Serializable] sealed class Receipt {public int version;public string status,project,packageName,unity,demoUnit,origin,symbols,harnessSHA256,builderSHA256,officialVendorPackageSHA256;public string[] assetPaths,assetSHA256;}
        [Serializable] sealed class Report {
            public string status="FAIL_PRIVATE_AD_DEMO127_BUILD",unity,package,receiptSHA256,apk,apkSHA256,errorType,code;
            public int checks,errors=-1,warnings=-1;public long bytes;public bool actualBuild,development,debugSigning=true,sourcePinsPreserved;
            public bool providerContacted=false,deviceTouched=false,actualSdkPlayback=false,actualAuthorityGrant=false;
            public string scope="Actual isolated pinned-LTS build of realYandex demo-SDK fixture. No launch/device/provider/authority actions performed by builder; no fake completion/credit path.";
            public List<string> passed=new List<string>();
        }
        static Report report;static Receipt receipt;static bool active;static Dictionary<string,string> pins;
        static string Hash(string path){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
        static string Full(string path)=>Path.GetFullPath(path).TrimEnd('\\','/');
        static void Need(bool value,string code){if(!value)throw new BuildFailedException(code);if(report!=null){report.checks++;report.passed.Add(code);}}
        static void Plain(string path){for(var p=new DirectoryInfo(Path.GetDirectoryName(Full(path)));p!=null;p=p.Parent)Need((p.Attributes&FileAttributes.ReparsePoint)==0,"PlainPrivateAncestors127");}
        static string GuidFrom(string path){var m=Regex.Matches(File.ReadAllText(path),@"(?m)^guid:\s*([a-f0-9]{32})\s*$");Need(m.Count==1,"SingleAssetGuid127");return m[0].Groups[1].Value;}
        static void ValidatePins(){
            foreach(var pin in pins.Where(p=>p.Key.StartsWith("Assets/",StringComparison.Ordinal))){
                Need(!pin.Key.Contains("..")&&!Path.IsPathRooted(pin.Key)&&File.Exists(pin.Key),"ContainedCopiedAsset127");
                Need(Hash(pin.Key)==pin.Value,"ExactActualSourceAndVendorPin127");
            }
            var actual=Directory.GetFiles("Assets","*",SearchOption.AllDirectories).Select(p=>p.Replace('\\','/'))
                .Where(p=>!p.EndsWith(".meta",StringComparison.Ordinal)&&p!="Assets/Fixture127/AdDemo127.unity").OrderBy(p=>p,StringComparer.Ordinal);
            var expected=pins.Keys.Where(p=>p.StartsWith("Assets/",StringComparison.Ordinal)&&!p.EndsWith(".meta",StringComparison.Ordinal)).OrderBy(p=>p,StringComparer.Ordinal);
            Need(actual.SequenceEqual(expected),"NoExtraCompiledPluginOrResourceAsset127");
            Need(!Directory.Exists("Assets/Resources")&&!Directory.GetDirectories("Assets","Resources",SearchOption.AllDirectories).Any(),"NoShippingOrExternalConfigurationResources127");
            Need(!Directory.GetFiles("Assets","*RuStore*.aar",SearchOption.AllDirectories).Any()&&!Directory.Exists("Assets/Plugins/RuStore"),"NoRuStoreSdkPlugin127");
            Need(!UnityEditor.PackageManager.PackageInfo.GetAllRegisteredPackages().Any(p=>p.name.StartsWith("ru.rustore.",StringComparison.Ordinal)),"NoRuStoreUpmSdk127");
            var guids=Directory.GetFiles("Assets","*.meta",SearchOption.AllDirectories).Select(GuidFrom).ToArray();
            Need(guids.Length==guids.Distinct(StringComparer.Ordinal).Count(),"UniquePreservedAndPrivateFixtureGuids127");
        }
        static string[] PrivacyErrors(string manifest,string gradle){
            var errors=new List<string>();
            try{
                XDocument xml;using(var read=XmlReader.Create(new StringReader(manifest),new XmlReaderSettings{DtdProcessing=DtdProcessing.Prohibit,XmlResolver=null}))xml=XDocument.Load(read);
                XNamespace a="http://schemas.android.com/apk/res/android",t="http://schemas.android.com/tools";
                var app=xml.Root.Elements("application").ToArray();
                if(app.Length!=1||(string)app[0].Attribute(a+"usesCleartextTraffic")!="false")errors.Add("CleartextOrApplication");
                var init=xml.Descendants("meta-data").Where(x=>(string)x.Attribute(a+"name")=="com.yandex.mobile.ads.AUTOMATIC_SDK_INITIALIZATION").ToArray();
                if(init.Length!=1||(string)init[0].Attribute(a+"value")!="false"||(string)init[0].Attribute(t+"replace")!="android:value")errors.Add("AutomaticInitialization");
                foreach(var name in new[]{"android.permission.ACCESS_FINE_LOCATION","android.permission.ACCESS_COARSE_LOCATION","android.permission.ACCESS_BACKGROUND_LOCATION","com.google.android.gms.permission.AD_ID"}){
                    var found=xml.Root.Elements("uses-permission").Where(x=>(string)x.Attribute(a+"name")==name).ToArray();
                    if(found.Length!=1||(string)found[0].Attribute(t+"node")!="remove")errors.Add("PrivacyPermission");
                }
                if(xml.Descendants("activity").Any(x=>((string)x.Attribute(a+"name")??"").Contains("GameActivity")))errors.Add("UnsupportedGameActivity");
            }catch{errors.Add("InvalidPrivacyManifest");}
            if(!gradle.Contains("implementation('com.yandex.android:mobileads:8.6.0') { version { strictly '8.6.0' } }")
                ||!gradle.Contains("implementation('io.appmetrica.analytics:analytics:8.6.0') { version { strictly '8.6.0' } }")
                ||!gradle.Contains("dependencyLocking { lockAllConfigurations() }")
                ||gradle.IndexOf("rustore",StringComparison.OrdinalIgnoreCase)>=0)errors.Add("PinnedAdsOnlyDependencies");
            return errors.ToArray();
        }
        static void ValidatePrivacy(){
            string xml=File.ReadAllText("Assets/Plugins/Android/AndroidManifest.xml"),gradle=File.ReadAllText("Assets/Plugins/Android/mainTemplate.gradle");
            Need(PrivacyErrors(xml,gradle).Length==0,"PinnedDemoPrivacyManifestAndDependencies127");
            Need(PrivacyErrors(xml.Replace("AUTOMATIC_SDK_INITIALIZATION\" android:value=\"false","AUTOMATIC_SDK_INITIALIZATION\" android:value=\"true"),gradle).Contains("AutomaticInitialization"),"RejectAutomaticSdkInitialization127");
            Need(PrivacyErrors(xml.Replace("tools:node=\"remove\"","tools:node=\"merge\""),gradle).Contains("PrivacyPermission"),"RejectLocationOrAdIdPermission127");
            Need(PrivacyErrors(xml,gradle.Replace("strictly '8.6.0'","strictly '8.7.0'")).Contains("PinnedAdsOnlyDependencies"),"RejectChangedSdkVersion127");
        }
        static void ValidateTools(){
            string editor=Full("E:/HeartRainUnity6LTS95/6000.3.27f1/Editor");string tools=Path.Combine(editor,"Data/PlaybackEngines/AndroidPlayer");
            Need(Application.unityVersion=="6000.3.27f1"&&Full(Path.GetDirectoryName(EditorApplication.applicationPath))==editor,"ExactApprovedIsolatedLts127");
            Need(Full(AndroidExternalToolsSettings.sdkRootPath)==Full(Path.Combine(tools,"SDK"))&&Full(AndroidExternalToolsSettings.ndkRootPath)==Full(Path.Combine(tools,"NDK"))&&Full(AndroidExternalToolsSettings.jdkRootPath)==Full(Path.Combine(tools,"OpenJDK"))&&Full(AndroidExternalToolsSettings.Gradle.path)==Full(Path.Combine(tools,"Tools/gradle")),"ActualStockAndroidToolPaths127");
            Need(File.ReadAllText(Path.Combine(tools,"OpenJDK/release")).Contains("JAVA_VERSION=\"17.0.18\"")
                &&File.ReadAllText(Path.Combine(tools,"NDK/source.properties")).Contains("27.2.12479018")
                &&File.Exists(Path.Combine(tools,"SDK/platforms/android-36/android.jar"))
                &&File.Exists(Path.Combine(tools,"Tools/gradle/lib/gradle-core-9.3.1.jar"))
                &&File.Exists(Path.Combine(tools,"Tools/gradle/lib/gradle-launcher-9.3.1.jar")),"MatchingStockJdk17Ndk27Sdk36Gradle931127");
        }
        static void ValidateProfile(BuildTarget target,BuildOptions options){
            Need(active&&receipt!=null&&target==BuildTarget.Android,"OwnedClinicalAndroidBuildLease127");
            Need(PlayerSettings.GetApplicationIdentifier(BuildTargetGroup.Android)==AdsDemo127.Package&&!PlayerSettings.Android.useCustomKeystore,"ExactDistinctPackageDebugSigning127");
            Need((options&BuildOptions.Development)!=0&&(options&(BuildOptions.AllowDebugging|BuildOptions.ConnectWithProfiler|BuildOptions.EnableDeepProfilingSupport))==0,"DevelopmentWithoutScriptDebugger127");
            var symbols=PlayerSettings.GetScriptingDefineSymbolsForGroup(BuildTargetGroup.Android).Split(';');
            Need(symbols.OrderBy(x=>x).SequenceEqual(receipt.symbols.Split(';').OrderBy(x=>x))
                 &&symbols.Contains("HOTR_YANDEX_ADS_ISOLATED_FIXTURE")&&!symbols.Any(x=>x.Contains("RUSTORE")||x.Contains("PRODUCTION")),"ExactDemoAndPrivacySymbolsNoPayments127");
            Need(AdsDemo127.Unit=="demo-rewarded-yandex"&&AdsDemo127.Origin=="https://api.novamind-it.ru"&&receipt.demoUnit==AdsDemo127.Unit&&receipt.origin==AdsDemo127.Origin,"ExactDemoOnlyUnitAndOwnedOrigin127");
            Need(PlayerSettings.Android.targetArchitectures==AndroidArchitecture.ARM64&&PlayerSettings.GetScriptingBackend(BuildTargetGroup.Android)==ScriptingImplementation.IL2CPP
                &&(int)PlayerSettings.Android.minSdkVersion==26&&(int)PlayerSettings.Android.targetSdkVersion==36,"Arm64Il2cppApi26To36127");
            ValidateTools();ValidatePins();ValidatePrivacy();
        }
        public sealed class Guard:IPreprocessBuildWithReport {
            public int callbackOrder=>-2000;
            public void OnPreprocessBuild(BuildReport build){ValidateProfile(build.summary.platform,build.summary.options);}
        }
        public static void Run(){
            string output=Environment.GetEnvironmentVariable("HOTR_ADS127_OUT");report=new Report{unity=Application.unityVersion,package=AdsDemo127.Package};
            try{
                string rp=Environment.GetEnvironmentVariable("HOTR_ADS127_RECEIPT");Plain(rp);report.receiptSHA256=Hash(rp);
                Need(report.receiptSHA256==Environment.GetEnvironmentVariable("HOTR_ADS127_RECEIPT_SHA256"),"ExactReviewedPreparationReceipt127");
                string json=File.ReadAllText(rp);receipt=JsonUtility.FromJson<Receipt>(json);
                Need(receipt.assetPaths!=null&&receipt.assetSHA256!=null&&receipt.assetPaths.Length==receipt.assetSHA256.Length&&receipt.assetPaths.Length>500,"CompleteFixtureSourcePinArrays127");
                pins=Enumerable.Range(0,receipt.assetPaths.Length).ToDictionary(i=>receipt.assetPaths[i],i=>receipt.assetSHA256[i],StringComparer.Ordinal);
                string project=Full(Path.GetDirectoryName(Application.dataPath));
                Need(receipt.version==1&&receipt.status=="PREPARED_REAL_SDK_AD_DEMO127_NOT_BUILT"&&Full(receipt.project)==project
                    &&project.StartsWith(Full("E:/.verification-cache/HOTR127")+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)
                    &&receipt.packageName==AdsDemo127.Package,"FreshOwnedProjectReceipt127");
                Need(Hash("Assets/Fixture127/AdsDemo127.cs")==receipt.harnessSHA256&&Hash("Assets/Fixture127/Editor/AdsDemoBuild127.cs")==receipt.builderSHA256,"ReviewedActualHarnessAndBuilder127");
                PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android,AdsDemo127.Package);PlayerSettings.Android.useCustomKeystore=false;
                PlayerSettings.Android.bundleVersionCode=127;PlayerSettings.bundleVersion="127.0";
                PlayerSettings.Android.minSdkVersion=(AndroidSdkVersions)26;PlayerSettings.Android.targetSdkVersion=(AndroidSdkVersions)36;
                PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android,ScriptingImplementation.IL2CPP);PlayerSettings.Android.targetArchitectures=AndroidArchitecture.ARM64;
                PlayerSettings.defaultInterfaceOrientation=UIOrientation.Portrait;PlayerSettings.SplashScreen.show=false;PlayerSettings.SplashScreen.showUnityLogo=false;
                active=true;ValidateProfile(BuildTarget.Android,BuildOptions.Development);
                var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
                new GameObject("DiagnosticCamera",typeof(Camera));new GameObject("RealSdkDemoOnly127",typeof(AdsDemo127));
                const string scenePath="Assets/Fixture127/AdDemo127.unity";EditorSceneManager.SaveScene(scene,scenePath);
                Need(scene.GetRootGameObjects().Length==2,"OnlyClinicalHarnessAndCameraScene127");
                string apk=Path.Combine(project,"Builds/HeartRain_RealSdk_DemoAds127.apk");Need(!File.Exists(apk),"FreshContainedFixtureApk127");Directory.CreateDirectory(Path.GetDirectoryName(apk));report.apk=apk;report.actualBuild=true;
                var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{scenePath},locationPathName=apk,target=BuildTarget.Android,options=BuildOptions.Development});
                report.errors=(int)result.summary.totalErrors;report.warnings=(int)result.summary.totalWarnings;report.development=(result.summary.options&BuildOptions.Development)!=0;
                Need(result.summary.result==BuildResult.Succeeded&&report.errors==0&&report.development&&File.Exists(apk),"ActualDemoSdkApkBuilt127");
                ValidatePins();report.sourcePinsPreserved=true;report.bytes=new FileInfo(apk).Length;report.apkSHA256=Hash(apk);report.status="PASS_REAL_SDK_AD_DEMO127_ANDROID_BUILD";
            }catch(Exception error){report.errorType=error.GetType().Name;if(error is BuildFailedException)report.code=error.Message;}
            finally{active=false;Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"Native.json"),JsonUtility.ToJson(report,true)+"\n");}
            if(Application.isBatchMode)EditorApplication.Exit(report.status.StartsWith("PASS_",StringComparison.Ordinal)?0:1);
        }
    }
}
#endif

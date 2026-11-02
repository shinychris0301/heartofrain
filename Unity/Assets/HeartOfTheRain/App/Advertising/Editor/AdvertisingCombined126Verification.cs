#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using HeartOfTheRain.App.Advertising;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.App.Advertising.Editor {
    public static class AdvertisingCombined126Verification {
        [Serializable] sealed class Report {
            public string status="FAIL_NATIVE_COMBINED_ADVERTISING126",utc,unity;
            public int checks;
            public bool actualUnityEditor=true,syntheticBoundaryObservations=true,actualSdk=false,actualBuild=false,actualProviderRequest=false;
            public string scope="Native Editor pure combined SDK125/ads build-boundary controls with explicit synthetic file/SDK observations. Actual pinned vendor/plugin compilation and APK checks are separate. No SDK initialization, live ads, device or production acceptance.";
            public List<string> passed=new List<string>(),errors=new List<string>();
        }
        static Report report;
        static void Check(bool ok,string label){report.checks++;if(!ok)throw new InvalidOperationException(label);report.passed.Add(label);}
        static string Json(bool enabled)=>JsonUtility.ToJson(new RewardedAdsConfiguration85{version=2,enabled=enabled,rewardedUnitId=AdvertisingConfiguration107.RewardedUnitId,interstitialUnitId=AdvertisingConfiguration107.InterstitialUnitId,privacyUrl="https://api.novamind-it.ru/privacy",privacyVersion="draft126"});
        const string Gradle="implementation('com.yandex.android:mobileads:8.6.0') { version { strictly '8.6.0' } }\nimplementation('io.appmetrica.analytics:analytics:8.6.0') { version { strictly '8.6.0' } }";
        const string Manifest="<manifest xmlns:android='http://schemas.android.com/apk/res/android' xmlns:tools='http://schemas.android.com/tools'><uses-permission android:name='android.permission.ACCESS_FINE_LOCATION' tools:node='remove'/><uses-permission android:name='android.permission.ACCESS_COARSE_LOCATION' tools:node='remove'/><uses-permission android:name='android.permission.ACCESS_BACKGROUND_LOCATION' tools:node='remove'/><uses-permission android:name='com.google.android.gms.permission.AD_ID' tools:node='remove'/><application android:usesCleartextTraffic='false'><meta-data android:name='com.yandex.mobile.ads.AUTOMATIC_SDK_INITIALIZATION' android:value='false' tools:replace='android:value'/></application></manifest>";
        static readonly string[] Defines={"HOTR_RUSTORE_SDK_ONLY125","HOTR_RUSTORE_PAY","HOTR_YANDEX_ADS","APPMETRICA_ADAPTER_ADREVENUE_AUTOCOLLECTION_DISABLED","APPMETRICA_ADAPTER_ADREVENUE_AUTO_COLLECTION_DISABLED"};
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};
            try{
                Check(Application.unityVersion=="2022.3.62f3","PinnedNativeBaseline");
                var files=AdvertisingCombinedBoundary126.ExpectedFiles();Check(files.Count==88,"ExplicitOfficialAndroidRuntimePinInventory");
                Check(AdvertisingCombinedBoundary126.Validate(Json(true),Defines,true,files,Gradle,Manifest).Length==0,"SyntheticCombinedOwnerPackageCheckoutAndAdsPolicy");
                Check(AdvertisingCombinedBoundary126.Validate(Json(false),new string[0],false,new Dictionary<string,string>(),null,null).Length==0,"DisabledSdkFreeDefaultPreserved");
                var extra=new Dictionary<string,string>(files){{"Assets/YandexMobileAds/UnexpectedStartup126.cs",new string('a',64)}};
                Check(AdvertisingCombinedBoundary126.Validate(Json(true),Defines,true,extra,Gradle,Manifest).Length>0,"UnexpectedCompiledVendorFileCannotHideBehindExpectedPins");
                string temporary=Path.Combine(Path.GetTempPath(),"hotr-ads-inventory126-"+Guid.NewGuid().ToString("N"));
                try{string folder=Path.Combine(temporary,"Assets/YandexMobileAds");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"UnexpectedStartup126.cs"),"// synthetic file-enumeration fixture");var observed=AdvertisingCombinedBoundary126.ObserveVendorFiles(temporary);Check(observed.ContainsKey("Assets/YandexMobileAds/UnexpectedStartup126.cs"),"ActualDirectoryEnumerationIncludesUnexpectedCompiledFiles");}
                finally{if(Directory.Exists(temporary))Directory.Delete(temporary,true);}
                foreach(string fault in new[]{"missingDefine","uncompiled","autoCollection1","autoCollection2","missingFile","changedFile","missingGradle","wrongYandex","wrongMetrica","duplicateVersion","commentedPins","autoInit","location","adId","cleartext","doctype","placement"}){
                    var observed=new Dictionary<string,string>(files);string[] symbols=Defines;bool compiled=true;string gradle=Gradle,manifest=Manifest,config=Json(true);
                    if(fault=="missingDefine")symbols=Defines.Where(v=>v!="HOTR_YANDEX_ADS").ToArray();
                    if(fault=="uncompiled")compiled=false;
                    if(fault=="autoCollection1")symbols=Defines.Where(v=>v!="APPMETRICA_ADAPTER_ADREVENUE_AUTOCOLLECTION_DISABLED").ToArray();
                    if(fault=="autoCollection2")symbols=Defines.Where(v=>v!="APPMETRICA_ADAPTER_ADREVENUE_AUTO_COLLECTION_DISABLED").ToArray();
                    if(fault=="missingFile")observed.Remove(observed.Keys.First());
                    if(fault=="changedFile")observed[observed.Keys.First()]=new string('0',64);
                    if(fault=="missingGradle")gradle=null;
                    if(fault=="wrongYandex")gradle=gradle.Replace("mobileads:8.6.0","mobileads:8.7.0");
                    if(fault=="wrongMetrica")gradle=gradle.Replace("analytics:8.6.0","analytics:8.7.0");
                    if(fault=="duplicateVersion")gradle+="\nimplementation 'com.yandex.android:mobileads:9.0.0'";
                    if(fault=="commentedPins")gradle="/*"+gradle+"*/";
                    if(fault=="autoInit")manifest=manifest.Replace("android:value='false'","android:value='true'");
                    if(fault=="location")manifest=manifest.Replace("android.permission.ACCESS_FINE_LOCATION","another.permission");
                    if(fault=="adId")manifest=manifest.Replace("com.google.android.gms.permission.AD_ID","another.permission");
                    if(fault=="cleartext")manifest=manifest.Replace("usesCleartextTraffic='false'","usesCleartextTraffic='true'");
                    if(fault=="doctype")manifest="<!DOCTYPE manifest [<!ENTITY test 'bad'>]>"+manifest;
                    if(fault=="placement")config=config.Replace(AdvertisingConfiguration107.RewardedUnitId,"R-M-20291714-9");
                    Check(AdvertisingCombinedBoundary126.Validate(config,symbols,compiled,observed,gradle,manifest).Length>0,"RejectCombinedBoundary_"+fault);
                }
                Check(AdvertisingBuild107.CombinedErrors126().Length==0,"ActualOrdinaryDisabledProfileRemainsUnchanged");
                report.status="PASS_NATIVE_COMBINED_ADVERTISING126";
            }catch(Exception error){report.errors.Add(error is InvalidOperationException?error.Message:error.GetType().Name);}
            string output=Environment.GetEnvironmentVariable("HOTR_REVIEW126_ADVERTISING_OUT");if(string.IsNullOrEmpty(output))throw new InvalidOperationException("ExplicitAds126OutputRequired");Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"AdvertisingCombined126.json"),JsonUtility.ToJson(report,true));
            if(Application.isBatchMode)EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif

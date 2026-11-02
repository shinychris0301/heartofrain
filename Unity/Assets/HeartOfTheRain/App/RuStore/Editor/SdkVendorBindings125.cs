#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Xml;
using System.Xml.Linq;
using UnityEditor;
using PackageInfo=UnityEditor.PackageManager.PackageInfo;
using UnityEngine;

namespace HeartOfTheRain.App.RuStore.Editor {
    // Preparation and validation only: no SDK singleton, JNI, payment or build.
    // File aggregates cover the exact unmodified official npm package contents.
    public static class SdkVendorBindings125 {
        public const string SettingsPath="Assets/RustoreSDK/Editor/PayClientSettings.asset";
        public const string ValuesPath="Assets/Plugins/Android/RuStoreSDKSettings.androidlib/res/values/values.xml";
        public const string ManifestPath="Assets/Plugins/Android/AndroidManifest.xml";
        const string PayAggregate="00ad7edc4f0d67eda4afd750eccc54b5cdce36fac23b1bf7b7cb288aa94a39e3",CoreAggregate="6b9543abfea570e6e97096a8f77a2a9e292c29e91536eadf6c53be6336c2446d";
        static readonly XNamespace Android="http://schemas.android.com/apk/res/android";
        public sealed class PackageObservation {public string name,version,source,aggregate;public int files;}
        public static string[] PackageErrors(PackageObservation[] packages){
            var errors=new List<string>();
            foreach(string name in new[]{"ru.rustore.pay","ru.rustore.core"}){
                bool pay=name=="ru.rustore.pay";var rows=(packages??new PackageObservation[0]).Where(p=>p!=null&&p.name==name).ToArray();
                if(rows.Length!=1||rows[0].version!=(pay?"11.1.0":"10.5.0")||rows[0].source!="Registry"||rows[0].files!=(pay?234:81)||rows[0].aggregate!=(pay?PayAggregate:CoreAggregate))errors.Add(pay?"sdk_checkout_exact_official_pay_11_1_required":"sdk_checkout_exact_official_core_10_5_required");
            }
            return errors.ToArray();
        }
        static string Hash(byte[] bytes){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
        static string ManifestTokens126(byte[] bytes){
            if(bytes==null||bytes.Length>262144)throw new FormatException();
            string text=new UTF8Encoding(false,true).GetString(bytes);var result=new StringBuilder(text.Length);bool quoted=false,escaped=false;
            foreach(char value in text){
                if(quoted){result.Append(value);if(escaped)escaped=false;else if(value=='\\')escaped=true;else if(value=='"')quoted=false;}
                else{if(value==' '||value=='\t'||value=='\r'||value=='\n')continue;result.Append(value);if(value=='"')quoted=true;}
            }
            if(quoted||escaped)throw new FormatException();return result.ToString();
        }
        // Unity6000 UPM appends registry provenance to package.json. Observe
        // that wrapper without editing the cache or changing any vendor token.
        // Only the exact known trailing field may restore the original raw hash.
        public static string ManifestHash126(string name,string version,string source,byte[] bytes){
            string raw=Hash(bytes);bool pay=name=="ru.rustore.pay"&&version=="11.1.0",core=name=="ru.rustore.core"&&version=="10.5.0";
            if(!pay&&!core)return raw;
            string original=pay?"afbaabf48f1c57f77432775121ac21923c16e51839c29288ee205a5b4aec3ff3":"b820d53463b52b64d530c47ce6c0d3c570eabc6166fed81b63e28b71800dd54b";
            if(raw==original||source!="Registry")return raw;
            try{
                string fingerprint=pay?"268ab2fb33b68595db5bc2d8a1af792e191fe7b8":"985c393e8d98b181445205858b678e25cc4dd178";
                string suffix=",\"_fingerprint\":\""+fingerprint+"\"}";string tokens=ManifestTokens126(bytes);
                if(!tokens.EndsWith(suffix,StringComparison.Ordinal))return raw;
                string vendor=tokens.Substring(0,tokens.Length-suffix.Length)+"}";
                string expected=pay?"505e8f6119691079c511dc22bbb932ee034f2ff90112b45e571b79b7651f743c":"476e22532c376a43ae7e11459ff29b3f7f218bc6446a3834063bc25c01ecbebd";
                return Hash(new UTF8Encoding(false).GetBytes(vendor))==expected?original:raw;
            }catch(Exception){return raw;}
        }
        public static PackageObservation ObservePackage(string name,string version,string source,string path){
            string root=Path.GetFullPath(path).TrimEnd('\\','/')+Path.DirectorySeparatorChar;
            var files=Directory.GetFiles(root,"*",SearchOption.AllDirectories).Select(p=>new{path=p,relative=p.Substring(root.Length).Replace('\\','/')}).OrderBy(p=>p.relative,StringComparer.Ordinal).ToArray();
            string canonical=string.Concat(files.Select(p=>{byte[] bytes=File.ReadAllBytes(p.path);return p.relative+"="+(p.relative=="package.json"?ManifestHash126(name,version,source,bytes):Hash(bytes))+"\n";}));
            return new PackageObservation{name=name,version=version,source=source,files=files.Length,aggregate=Hash(new UTF8Encoding(false).GetBytes(canonical))};
        }
        public static string[] ActualPackageErrors(){
            try{return PackageErrors(PackageInfo.GetAllRegisteredPackages().Where(p=>p.name=="ru.rustore.pay"||p.name=="ru.rustore.core").Select(p=>ObservePackage(p.name,p.version,p.source.ToString(),p.resolvedPath)).ToArray());}
            catch(Exception){return new[]{"sdk_checkout_official_package_contents_unavailable"};}
        }
        static XDocument Xml(string text){
            if(text==null||text.Length>262144)throw new FormatException();
            using(var reader=XmlReader.Create(new StringReader(text),new XmlReaderSettings{DtdProcessing=DtdProcessing.Prohibit,XmlResolver=null}))return XDocument.Load(reader,LoadOptions.PreserveWhitespace);
        }
        static void Need(bool condition){if(!condition)throw new FormatException();}
        public static string[] Validate(string appId,string scheme,string assetAppId,string assetScheme,string valuesXml,string manifestXml){
            var errors=new List<string>();long numeric;
            if(appId==null||!Regex.IsMatch(appId,@"\A[1-9][0-9]{0,18}\z")||!long.TryParse(appId,out numeric)||numeric<=0||scheme==null||!Regex.IsMatch(scheme,@"\A[a-z][a-z0-9+.-]{2,62}\z")||new[]{"http","https","file","intent","content","javascript"}.Contains(scheme))errors.Add("sdk_checkout_public_vendor_parameters_invalid");
            if(assetAppId!=appId||assetScheme!=scheme)errors.Add("sdk_checkout_vendor_settings_id_or_scheme_mismatch");
            try{
                var values=Xml(valuesXml);Need(values.Root?.Name=="resources");
                foreach(var expected in new[]{new[]{"rustore_PayClientSettings_consoleApplicationId",appId},new[]{"rustore_PayClientSettings_deeplinkScheme",scheme},new[]{"rustore_PayClientSettings_internalConfigKey","unity"}}){var found=values.Root.Elements("string").Where(e=>(string)e.Attribute("name")==expected[0]).ToArray();Need(found.Length==1&&found[0].Value==expected[1]);}
            }catch(Exception){errors.Add("sdk_checkout_generated_android_values_mismatch");}
            try{
                var manifest=Xml(manifestXml);Need(manifest.Root?.Name=="manifest");var apps=manifest.Root.Elements("application").ToArray();Need(apps.Length==1);var app=apps[0];
                foreach(var expected in new[]{new[]{"console_app_id_value","@string/rustore_PayClientSettings_consoleApplicationId"},new[]{"sdk_pay_scheme_value","@string/rustore_PayClientSettings_deeplinkScheme"},new[]{"internal_config_key","@string/rustore_PayClientSettings_internalConfigKey"}}){var found=app.Elements("meta-data").Where(e=>(string)e.Attribute(Android+"name")==expected[0]).ToArray();Need(found.Length==1&&(string)found[0].Attribute(Android+"value")==expected[1]);}
                var activities=app.Elements("activity").Where(e=>(string)e.Attribute(Android+"name")=="ru.rustore.unitysdk.RuStoreDeeplinkActivityDefault").ToArray();Need(activities.Length==1&&(string)activities[0].Attribute(Android+"exported")=="true"&&(string)activities[0].Attribute(Android+"theme")=="@android:style/Theme.NoDisplay");
                Need(activities[0].Elements("intent-filter").Any(filter=>filter.Elements("action").Any(e=>(string)e.Attribute(Android+"name")=="android.intent.action.VIEW")&&filter.Elements("category").Any(e=>(string)e.Attribute(Android+"name")=="android.intent.category.DEFAULT")&&filter.Elements("category").Any(e=>(string)e.Attribute(Android+"name")=="android.intent.category.BROWSABLE")&&filter.Elements("data").Any(e=>(string)e.Attribute(Android+"scheme")=="@string/rustore_PayClientSettings_deeplinkScheme")));
            }catch(Exception){errors.Add("sdk_checkout_android_manifest_id_scheme_or_return_activity_mismatch");}
            return errors.ToArray();
        }
        static UnityEngine.Object Settings(){
            var paths=AssetDatabase.FindAssets("t:PayClientSettings").Select(AssetDatabase.GUIDToAssetPath).ToArray();
            if(paths.Length!=1||paths[0]!=SettingsPath)throw new InvalidOperationException("Sdk125ExactVendorSettingsAssetRequired");
            var value=AssetDatabase.LoadMainAssetAtPath(SettingsPath);if(value==null||value.GetType().FullName!="RuStore.Editor.PayClientSettings")throw new InvalidOperationException("Sdk125VendorSettingsTypeInvalid");return value;
        }
        static string Text(UnityEngine.Object value,string name)=>(string)value.GetType().GetField(name).GetValue(value);
        public static string[] ActualBindingErrors(string appId,string scheme){
            try{var value=Settings();var errors=Validate(appId,scheme,Text(value,"consoleApplicationId"),Text(value,"deeplinkScheme"),File.ReadAllText(ValuesPath),File.ReadAllText(ManifestPath)).ToList();
                if((int)value.GetType().GetField("schemeVersion").GetValue(value)!=1||Text(value,"internalConfigKey")!="unity")errors.Add("sdk_checkout_vendor_settings_schema_invalid");return errors.ToArray();}
            catch(Exception){return new[]{"sdk_checkout_vendor_settings_values_and_manifest_required"};}
        }
        public static void ConfigureIsolated(string appId,string scheme){
            string project=Path.GetFullPath("."),selected=Environment.GetEnvironmentVariable("HOTR_SDK125_PACKAGING_PROJECT");
            if(string.IsNullOrEmpty(selected)||!string.Equals(project,Path.GetFullPath(selected),StringComparison.OrdinalIgnoreCase)||project.IndexOf(Path.DirectorySeparatorChar+".verification-cache"+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)<0)throw new InvalidOperationException("Sdk125ExplicitPrivatePackagingProjectRequired");
            if(ActualPackageErrors().Length!=0)throw new InvalidOperationException("Sdk125PinnedOfficialPackagesRequired");
            // Existing approved startup/launcher manifest is mandatory. Never
            // replace the game's activity with a generic vendor demo manifest.
            if(!File.Exists(ManifestPath))throw new InvalidOperationException("Sdk125ExistingApprovedLauncherManifestRequired");
            long id;if(appId==null||!Regex.IsMatch(appId,@"\A[1-9][0-9]{0,18}\z")||!long.TryParse(appId,out id)||id<=0||scheme==null||!Regex.IsMatch(scheme,@"\A[a-z][a-z0-9+.-]{2,62}\z")||new[]{"http","https","file","intent","content","javascript"}.Contains(scheme))throw new InvalidOperationException("Sdk125PublicAppIdAndSchemeRequired");
            UnityEngine.Object value;
            if(AssetDatabase.FindAssets("t:PayClientSettings").Length==0){
                var settingsType=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("RuStore.Editor.PayClientSettings")).First(t=>t!=null);
                value=ScriptableObject.CreateInstance(settingsType);Directory.CreateDirectory(Path.GetDirectoryName(SettingsPath));AssetDatabase.CreateAsset(value,SettingsPath);
            }else value=Settings();
            value.GetType().GetField("schemeVersion").SetValue(value,1);value.GetType().GetField("consoleApplicationId").SetValue(value,appId);value.GetType().GetField("deeplinkScheme").SetValue(value,scheme);EditorUtility.SetDirty(value);AssetDatabase.SaveAssets();
            var core=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("RuStore.Editor.RuStoreSDKSettings")).First(t=>t!=null);core.GetMethod("UpdateSettingsLibrary",BindingFlags.Public|BindingFlags.Static).Invoke(null,null);
            var patcher=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("RuStore.Editor.Manifest.PayClientManifestPatcher")).First(t=>t!=null);var instance=patcher.GetProperty("Instance",BindingFlags.Public|BindingFlags.Static).GetValue(null);
            patcher.GetMethod("PatchProjectManifest",BindingFlags.Public|BindingFlags.Instance).Invoke(instance,new object[]{value});
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            if(ActualBindingErrors(appId,scheme).Length!=0)throw new InvalidOperationException("Sdk125GeneratedVendorBindingInvalid");
        }
    }
}
#endif

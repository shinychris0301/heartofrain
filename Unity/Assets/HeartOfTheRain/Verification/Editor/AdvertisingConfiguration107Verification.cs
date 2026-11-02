#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using HeartOfTheRain.App.Advertising;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.ServerGameplay;
using UnityEditor;
using UnityEngine;

namespace HeartOfTheRain.Verification {
    public static class AdvertisingConfiguration107Verification {
        const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        [Serializable] sealed class Report {
            public string status="RUNNING",utc,unity;
            public string scope="Actual Editor strict configuration parser, packaged Resources adapter, bounded temporary-file IO and SDK-free Shop action guards. Ready managed gateway is an injected layout/eligibility snapshot, not a real authenticated backend. No SDK initialization/load/display, interstitial placement, impression, reward grant, HTTP, Android or production acceptance.";
            public int checks,cases;public bool ordinaryProfilesPreserved,serverReviewPreserved,advertisingFilePreserved,languagePreferencePreserved;
            public List<string> passed=new List<string>(),errors=new List<string>();
        }
        static Report report;static string temporary;
        static void Check(bool value,string code){report.checks++;if(!value)throw new InvalidOperationException(code);report.passed.Add(code);}
        static void Set(object owner,string field,object value)=>owner.GetType().GetField(field,Private).SetValue(owner,value);
        static T Get<T>(object owner,string field)=>(T)owner.GetType().GetField(field,Private).GetValue(owner);
        static string Digest(string path){
            if(!File.Exists(path)&&!Directory.Exists(path))return "Absent";
            using(var sha=SHA256.Create()){
                if(File.Exists(path))return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path)));
                string rows=string.Join("\n",Directory.GetFiles(path,"*",SearchOption.AllDirectories).OrderBy(p=>p,StringComparer.Ordinal).Select(p=>p.Substring(path.Length).Replace('\\','/')+":"+BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(p)))));
                return "Directory:"+BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(rows)));
            }
        }
        static string Json(bool enabled=false,string privacy="")=>"{\"version\":2,\"enabled\":"+(enabled?"true":"false")+",\"rewardedUnitId\":\""+AdvertisingConfiguration107.RewardedUnitId+"\",\"interstitialUnitId\":\""+AdvertisingConfiguration107.InterstitialUnitId+"\",\"privacyUrl\":\""+privacy+"\",\"privacyVersion\":\"launch-r1\"}";
        static string Legacy(bool enabled=false,string privacy="")=>Json(enabled,privacy).Replace("\"version\":2","\"version\":1").Replace(",\"interstitialUnitId\":\""+AdvertisingConfiguration107.InterstitialUnitId+"\"","");
        static void Reject(string json,string label){RewardedAdsConfiguration85 value;string error;Check(!RewardedAdsConfiguration85.TryParsePackaged(json,out value,out error)&&value==null&&error==AdvertisingConfiguration107.InvalidError,label);}
        static void Case(string name,Action action){report.cases++;try{action();}catch(Exception e){report.errors.Add(name+": "+(e is InvalidOperationException?e.Message:e.GetType().Name));}}
        static void Parser(){
            RewardedAdsConfiguration85 value;string error;Check(RewardedAdsConfiguration85.TryParsePackaged(Json(),out value,out error)&&error==null&&!value.enabled,"Disabled v2 payload remains valid without a fabricated privacy URL");
            Check(value.rewardedUnitId=="R-M-20291714-1"&&value.interstitialUnitId=="R-M-20291714-2"&&value.privacyUrl==""&&value.privacyVersion=="launch-r1","Both owner-provided public placements retained separately");
            Check(RewardedAdsConfiguration85.CanonicalPackagedJson(value)==Json(),"Canonical output contains exactly the validated six public fields");
            // This syntactically valid hostname is never resolved or contacted.
            Check(RewardedAdsConfiguration85.TryParsePackaged(Json(true,"https://privacy.heartoftherain.ru/policy"),out value,out error)&&value.enabled,"Enabled syntax requires explicit non-placeholder HTTPS privacy information");
            Reject(Json(true),"Enabled with absent privacy is unavailable");Reject(Legacy(),"Legacy v1 cannot become a packaged activation");
            Check(RewardedAdsConfiguration85.ParseLegacyOrV2(Legacy(true,"https://privacy.heartoftherain.ru/policy")).version==1,"Strict legacy enabled configuration remains available to persistent-only selection");
            Check(RewardedAdsConfiguration85.ParseLegacyOrV2(Legacy().Replace(AdvertisingConfiguration107.RewardedUnitId,"")).rewardedUnitId=="","Disabled legacy example with empty placement remains readable");
            foreach(string json in new[]{"null","[]","{}",Json()+"x",Json().Replace("\"version\":2","\"version\":2.0"),Json().Replace("\"enabled\":false","\"enabled\":0"),Json().Replace("\"enabled\":false","\"enabled\":\"false\""),Json().Replace("\"version\":2","\"version\":2,\"version\":2"),Json().Replace("\"enabled\":false","\"enabled\":false,\"enabled\":true"),Json().Replace("\"version\":2","\"version\":3"),Json().Replace("\"version\":2,",""),Json().Replace("\"privacyUrl\":\"\",",""),Json().Replace(",\"interstitialUnitId\":\""+AdvertisingConfiguration107.InterstitialUnitId+"\"",""),Json().Replace("\"privacyVersion\":\"launch-r1\"","\"privacyVersion\":null"),Json().Replace("launch-r1","bad version"),Json().Replace(AdvertisingConfiguration107.RewardedUnitId,"demo-rewarded-yandex"),Json().Replace(AdvertisingConfiguration107.InterstitialUnitId,"R-M-0-2"),Json().Replace("\"version\":2","\"version\":2,\"apiSecret\":\"do-not-ship\""),Json().Replace("\"version\":2","\"version\":2,\"nested\":{\"enabled\":true}"),"\ufeff"+Json(),Json()+new string(' ',4097),Json().Replace("launch-r1","\\ud800")})Reject(json,"Malformed, duplicate, unknown, secret, missing or mistyped field rejected");
            foreach(string url in new[]{"http://privacy.heartoftherain.ru/policy","https://127.0.0.1/policy","https://[::1]/policy","https://localhost/policy","https://private.local/policy","https://privacy.example.com/policy","https://privacy.invalid/policy","https://privacy.test/policy","https://user:password@privacy.heartoftherain.ru/policy","https://privacy.heartoftherain.ru/policy#fragment","https://privacy.heartoftherain.ru/policy?token=value","https://privacy.heartoftherain.ru/a b","https://privacy.heartoftherain.ru/\\n"})Reject(Json(true,url),"Unsafe or placeholder privacy URL rejected");
            Check(!RewardedAdsConfiguration85.ParseLegacyOrV2(Json()).enabled,"Reading a public ID never implicitly enables advertising");
        }
        static void Selection(){
            var absent=AdvertisingConfigurationInput107.Absent;var disabled=new AdvertisingConfigurationInput107(true,Json());var enabled=new AdvertisingConfigurationInput107(true,Legacy(true,"https://privacy.heartoftherain.ru/policy"));
            RewardedAdsConfiguration85 value;string error,source;
            Check(!AdvertisingConfiguration107.Select(absent,absent,out value,out error,out source)&&value==null&&error==null&&source=="None","Absent optional advertising stays unavailable without selecting a local reward source");
            Check(AdvertisingConfiguration107.Select(absent,enabled,out value,out error,out source)&&value.enabled&&value.version==1&&source=="Persistent","Legacy device configuration is selected only without a packaged key");
            Check(AdvertisingConfiguration107.Select(disabled,enabled,out value,out error,out source)&&!value.enabled&&value.version==2&&source=="Packaged","Packaged disabled value cannot be enabled by a legacy device file");
            foreach(var invalid in new[]{AdvertisingConfigurationInput107.Invalid,new AdvertisingConfigurationInput107(true,"{}"),new AdvertisingConfigurationInput107(true,Legacy()),new AdvertisingConfigurationInput107(true,Json(true))})
                Check(!AdvertisingConfiguration107.Select(invalid,enabled,out value,out error,out source)&&value==null&&error==AdvertisingConfiguration107.InvalidError&&source=="Packaged","Present invalid packaged payload never falls back to a valid device activation");
            Check(!AdvertisingConfiguration107.Select(absent,AdvertisingConfigurationInput107.Invalid,out value,out error,out source)&&value==null&&error==AdvertisingConfiguration107.InvalidError&&source=="Persistent","Unreadable legacy input stays unavailable");
            Check(!AdvertisingConfiguration107.Select(new AdvertisingConfigurationInput107(true,Json().Replace("\"version\":2","\"version\":2,\"origin\":\"https://wrong.heartoftherain.ru\"")),enabled,out value,out error,out source),"Advertising does not reinterpret a managed-backend configuration field");
        }
        static void FileIO(){
            string file=Path.Combine(temporary,"advertising.json");var absent=AdvertisingConfiguration107.ReadFile(file);Check(!absent.present,"Missing legacy file stays absent");
            File.WriteAllText(file,Legacy(),new UTF8Encoding(false));var input=AdvertisingConfiguration107.ReadFile(file);Check(input.present&&!input.failed&&input.json==Legacy(),"Actual bounded UTF8 legacy file is observed without mutating it");
            File.WriteAllBytes(file,new byte[]{239,187,191}.Concat(Encoding.UTF8.GetBytes(Legacy())).ToArray());input=AdvertisingConfiguration107.ReadFile(file);Check(input.json==Legacy(),"Existing UTF8 BOM legacy compatibility retained");
            File.WriteAllBytes(file,new byte[]{255,254,128,128});Check(AdvertisingConfiguration107.ReadFile(file).failed,"Invalid UTF8 is not replaced permissively");
            File.WriteAllText(file,new string(' ',4097),new UTF8Encoding(false));Check(AdvertisingConfiguration107.ReadFile(file).failed,"Oversized legacy file rejected before decoding");
            using(var locked=new FileStream(file,FileMode.Open,FileAccess.ReadWrite,FileShare.None))Check(AdvertisingConfiguration107.ReadFile(file).failed,"Unreadable selected legacy file is invalid rather than absent");
        }
        static void Packaged(){
            var input=AdvertisingConfiguration107.ReadPackaged();Check(input.present&&!input.failed,"Actual imported exact Resources TextAsset is selected");
            var asset=AssetDatabase.LoadAssetAtPath<TextAsset>(AdvertisingConfiguration107.ResourceAssetPath);Check(asset&&Resources.Load<TextAsset>(AdvertisingConfiguration107.ResourceKey)==asset,"Resource key resolves the committed placement asset rather than another folder");
            RewardedAdsConfiguration85 value;string error;Check(RewardedAdsConfiguration85.TryParsePackaged(input.json,out value,out error)&&!value.enabled&&value.rewardedUnitId==AdvertisingConfiguration107.RewardedUnitId&&value.interstitialUnitId==AdvertisingConfiguration107.InterstitialUnitId,"Actual resource is disabled and retains both owner placement IDs");
            Check(!RewardedAdsConfiguration85.TryRead(out value,out error)&&value==null&&error=="AdsDisabled","Actual runtime adapter cannot activate disabled packaged advertising");
        }
        static void ManagedBuild(){
            const string json="{\"version\":1,\"mode\":\"ManagedGuestServer\",\"origin\":\"https://managed.hotr-synthetic.ru\",\"identityScope\":\"review-ad107\",\"allowDevelopmentLoopback\":false,\"socialEnabled\":true}";
            string canonical;Check(AdvertisingConfiguration107.TryCanonicalManagedBuild107(json,out canonical)&&ServerGameplayConfiguration.Parse(canonical).socialEnabled,"Public runtime build boundary reuses the existing104 strict managed parser and canonicalizer");
            foreach(string invalid in new[]{json.Replace(",\"socialEnabled\":true",""),json.Replace(",\"allowDevelopmentLoopback\":false",""),json.Replace("\"version\":1","\"version\":1,\"apiSecret\":\"do-not-ship\""),json.Replace("\"version\":1","\"version\":1,\"version\":1"),json.Replace("\"socialEnabled\":true","\"socialEnabled\":\"true\""),json.Replace("https://managed.hotr-synthetic.ru","http://127.0.0.1:8000"),json.Replace("\"allowDevelopmentLoopback\":false","\"allowDevelopmentLoopback\":true")})
                Check(!AdvertisingConfiguration107.TryCanonicalManagedBuild107(invalid,out canonical)&&canonical==null,"Managed ad-build boundary rejects missing, extra, duplicate, mistyped or loopback fields without side effects");
        }
        sealed class NoRequests:IRewardedAdsApi85 {
            public int calls;IEnumerator Denied(){calls++;throw new InvalidOperationException("UnexpectedAdvertisingRequest");}
            public IEnumerator Status(ServerAuthorizedContext c,Action<AdReply85<AdStatus85>> d)=>Denied();
            public IEnumerator Reserve(ServerAuthorizedContext c,string id,Action<AdReply85<AdOpportunity85>> d)=>Denied();
            public IEnumerator Read(ServerAuthorizedContext c,string id,Action<AdReply85<AdOpportunity85>> d)=>Denied();
            public IEnumerator Report(ServerAuthorizedContext c,string id,string cmd,Action<AdReply85<AdOpportunity85>> d)=>Denied();
            public IEnumerator Claim(ServerAuthorizedContext c,string id,string cmd,Action<AdReply85<AdOpportunity85>> d)=>Denied();
            public IEnumerator Cancel(ServerAuthorizedContext c,string id,string cmd,Action<AdReply85<AdOpportunity85>> d)=>Denied();
        }
        static void ShopGuards(){
            var owner=new GameObject("Advertising107 isolated action fixture");RewardedAdsFlow85 flow=null;
            try{
                var home=owner.AddComponent<HomePage>();home.enabled=false;string before=JsonUtility.ToJson(home.State);
                var shop=owner.AddComponent<RewardedShop85>();shop.enabled=false;shop.Configure(home);Set(shop,"visible",true);
                foreach(string action in new[]{"ad:watch","ad:accept","ad:privacy","interstitial","interstitial:show"})shop.Request(action);
                Check(!shop.Ready&&!shop.ProviderInstalled&&!shop.ConsentOpen&&!shop.Busy,"Actual local Shop action route cannot activate advertising or an interstitial");
                Check(AdShopView85.From(shop).action=="disabled","Unconfigured local wallet has no fake rewarded-video button");
                // Snapshot only: no identity Bootstrap, account creation, HTTP or ordinary profile factory.
                var gateway=owner.AddComponent<ServerGameSession>();gateway.enabled=false;string origin="https://staging.heartoftherain.ru",player=new string('a',32);
                var broker=new ServerGameplayBrokerClient(origin,player,()=>null,_=>{throw new InvalidOperationException("UnexpectedBrokerDispatch");});
                Set(gateway,"config",new ServerGameplayConfiguration{version=1,mode="ManagedGuestServer",origin=origin,identityScope="review-ad107"});
                Set(gateway,"wallet",new RuStoreServerWallet{initialized=true,playerId=player,coins=1250,lives=5,maxLives=5});Set(gateway,"journal",new ServerAttemptJournal(Path.Combine(temporary,"attempt.json"),origin,player));Set(gateway,"document",new ServerAttemptDocument());Set(gateway,"broker",broker);
                Check(gateway.Ready&&gateway.AccountVkStatus==null,"Ready managed gateway eligibility does not require a linked VK provider (injected snapshot)");
                var api=new NoRequests();int providers=0;string intent=Path.Combine(temporary,"ad-intent.json");
                flow=new RewardedAdsFlow85(api,new RewardedAdsJournal85(intent),_=>{throw new InvalidOperationException("UnexpectedAuthorization");},_=>{throw new InvalidOperationException("UnexpectedWalletRefresh");},p=>{providers++;return new UnavailableRewardedAdsProvider85();});
                var enabled=RewardedAdsConfiguration85.ParseLegacyOrV2(Json(true,"https://privacy.heartoftherain.ru/policy"));
                Set(shop,"config",enabled);Set(shop,"session",gateway);Set(shop,"origin",origin);Set(shop,"player",null);Set(shop,"flow",flow);
                Check(shop.Ready&&!shop.ProviderInstalled,"Managed unlinked snapshot is eligible while the missing SDK independently blocks presentation");
                shop.Request("ad:watch");shop.Request("ad:accept");Check(!shop.ConsentOpen&&!shop.Busy&&api.calls==0&&providers==0&&!File.Exists(intent),"Missing SDK blocks consent/start before provider factory, reservation, journal or wallet requests");
                Set(shop,"config",null);Check(!shop.Ready&&!shop.ProviderInstalled,"Missing privacy/config prevents new video activation even on a Ready managed gateway");
                Set(shop,"config",RewardedAdsConfiguration85.ParseLegacyOrV2(Json()));Check(!shop.Ready&&!shop.ProviderInstalled,"Explicit disabled configuration cannot bypass host activation gate");
                Check(api.calls==0&&providers==0&&gateway.Wallet.coins==1250&&JsonUtility.ToJson(home.State)==before,"All local/managed SDK-free actions leave authoritative snapshot and local economy unchanged");
                using(var provider=new YandexRewardedAdsProvider85(enabled.rewardedUnitId,new AdPrivacy85(false),action=>action())){
                    Check(!provider.Installed,"Ordinary Editor profile has no installed native provider");bool called=false;provider.Load((ok,why)=>{called=true;Check(!ok&&why=="AdsSdkUnavailable","Direct load cannot initialize an absent SDK");});Check(called,"Missing SDK failure is explicit");
                }
                Check(Get<RewardedAdsConfiguration85>(shop,"config").interstitialUnitId==AdvertisingConfiguration107.InterstitialUnitId&&api.calls==0,"Interstitial remains inert configuration, with no placement or server command");
            }finally{if(owner)UnityEngine.Object.DestroyImmediate(owner);flow?.Dispose();}
        }
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};string output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW107_OUT")??"../Verification/Evidence/Review107");
            string profiles=Path.Combine(Application.persistentDataPath,"Profiles"),server=Path.Combine(Application.persistentDataPath,"ServerReview");
            string p=null,s=null,a=null;bool languagePresent=PlayerPrefs.HasKey(GameLocale.PreferenceKey);int language=PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue);
            try{
                p=Digest(profiles);s=Digest(server);a=Digest(RewardedAdsConfiguration85.FilePath);temporary=Path.GetFullPath("../.verification-cache/Review107/Configuration/"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(temporary);
                Check(Application.unityVersion=="2022.3.62f3","Pinned main Editor engine retained");Case("Strict parser",Parser);Case("Selection",Selection);Case("Bounded legacy IO",FileIO);Case("Actual packaged adapter",Packaged);Case("Managed build payload",ManagedBuild);Case("Actual Shop guards",ShopGuards);
            }catch(Exception e){report.errors.Add("Fixture: "+e.GetType().Name);}
            finally{
                report.ordinaryProfilesPreserved=p!=null&&p==Digest(profiles);report.serverReviewPreserved=s!=null&&s==Digest(server);report.advertisingFilePreserved=a!=null&&a==Digest(RewardedAdsConfiguration85.FilePath);report.languagePreferencePreserved=PlayerPrefs.HasKey(GameLocale.PreferenceKey)==languagePresent&&PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue)==language;
                try{Check(report.ordinaryProfilesPreserved&&report.serverReviewPreserved&&report.advertisingFilePreserved&&report.languagePreferencePreserved,"Ordinary profile, managed journals, device ad file and exact locale preference preserved");}catch(Exception e){report.errors.Add(e.Message);}
                // This newly generated fixture directory contains no ordinary save data.
                string fixtureRoot=Path.GetFullPath("../.verification-cache/Review107/Configuration")+Path.DirectorySeparatorChar;
                if(temporary!=null&&temporary.StartsWith(fixtureRoot,StringComparison.OrdinalIgnoreCase)&&Directory.Exists(temporary))Directory.Delete(temporary,true);
                report.status=report.errors.Count==0?"PASS_NATIVE_ADVERTISING_CONFIGURATION107":"FAIL_NATIVE_ADVERTISING_CONFIGURATION107";Directory.CreateDirectory(Path.Combine(output,"Native"));File.WriteAllText(Path.Combine(output,"Native","AdvertisingConfiguration107.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));
            }
            if(Application.isBatchMode)EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif

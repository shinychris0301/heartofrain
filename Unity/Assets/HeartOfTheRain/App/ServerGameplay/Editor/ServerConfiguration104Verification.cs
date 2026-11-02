#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.ServerGameplay.Editor;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace HeartOfTheRain.Verification {
    public static class ServerConfiguration104Verification {
        const string Origin="https://staging.hotr-native-fixture.net",OtherOrigin="https://other.hotr-native-fixture.net";
        const string Payload="{\"version\":1,\"mode\":\"ManagedGuestServer\",\"origin\":\"https://staging.hotr-native-fixture.net\",\"identityScope\":\"review-staging-native104\",\"allowDevelopmentLoopback\":false,\"socialEnabled\":true}";
        const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        [Serializable] sealed class Report {
            public string status="RUNNING",utc,unity;
            public string scope="Actual Unity Editor strict parser, pure source resolver, real temporary-file IO and selected-invalid PlayerProfileHost isolation. Synthetic DNS strings are parsed only; no host contact, identity creation, Android APK, deployment or device/backend acceptance.";
            public int checks,cases;public bool profilesPreserved,serverReviewPreserved,languagePreferencePreserved,externalOverridePreserved;
            public bool componentCaseRequested,componentCaseVerified;
            public List<string> errors=new List<string>();
        }
        static Report report;
        static void Check(bool condition,string label){report.checks++;if(!condition)throw new InvalidOperationException(label);}
        static void Reject(Action action,string label){bool rejected=false;try{action();}catch(FormatException error){rejected=error.Message==ServerStagingConfiguration104.InvalidError;}Check(rejected,label);}
        static void Case(string name,Action action){report.cases++;try{action();}catch(Exception error){report.errors.Add(name+": "+error);}}
        static ServerConfigurationInput104 Present(string json)=>new ServerConfigurationInput104(true,json);
        static string Tree(string root){
            if(!Directory.Exists(root))return "Absent";using(var sha=SHA256.Create()){
                string rows=string.Join("\n",Directory.GetFiles(root,"*",SearchOption.AllDirectories).OrderBy(v=>v,StringComparer.Ordinal).Select(path=>path.Substring(root.Length)+":"+BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path)))));
                return "Present:"+Convert.ToBase64String(sha.ComputeHash(Encoding.UTF8.GetBytes(rows)));
            }
        }
        static ServerGameplayConfiguration Select(bool editor,bool development,string package,bool explicitOverride,ServerConfigurationInput104 external,ServerConfigurationInput104 packaged,ServerConfigurationInput104 persistent,bool selected,string expectedSource,bool valid,string expectedOrigin=null){
            ServerGameplayConfiguration value;string error,source;bool actual=ServerGameplaySelection104.Resolve(editor,development,package,explicitOverride,external,packaged,persistent,out value,out error,out source);
            Check(actual==selected&&source==expectedSource,"Resolver selects the exact authorized source");
            Check((value!=null)==valid&&error==(selected&&!valid?ServerStagingConfiguration104.InvalidError:null),"Resolver absence/invalid/valid distinction never permits fallback");
            if(valid)Check(value.origin==(expectedOrigin??Origin)&&value.identityScope.StartsWith("review-",StringComparison.Ordinal),"Chosen origin and isolated scope are retained without creating credentials");return value;
        }
        public static void Run()=>Run(false);
        public static void RunIsolated()=>Run(true);
        static void Run(bool componentCase){
            string output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW104_OUT")??"../Verification/Evidence/Review104");Directory.CreateDirectory(Path.Combine(output,"Native"));
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,componentCaseRequested=componentCase};string previous=Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG");
            if(!componentCase)report.scope="Actual Unity Editor strict parser, pure source resolver and real temporary-file IO only. No profile host initialization, host contact, identity creation, APK, deployment or physical-device/backend acceptance.";
            bool hadLanguage=PlayerPrefs.HasKey(GameLocale.PreferenceKey);int language=PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue);
            string profilesRoot=Path.Combine(Application.persistentDataPath,"Profiles"),serverRoot=Path.Combine(Application.persistentDataPath,"ServerReview"),profiles=null,server=null;
            string temporary=Path.GetFullPath("../.verification-cache/Review104/Configuration/"+Guid.NewGuid().ToString("N"));Application.logMessageReceived+=Log;
            try {
                profiles=Tree(profilesRoot);server=Tree(serverRoot);Check(Application.unityVersion=="2022.3.62f3","Approved main editor engine");
                if(componentCase){
                    Check(Application.companyName=="HeartRainStaging104"&&Application.productName=="HeartRainStaging104","Actual host fixture requires the prepared private persistent-data identity");
                    string fixture=Environment.GetEnvironmentVariable(StagingServerBuild104.ConfigVariable),receipt=Environment.GetEnvironmentVariable(StagingServerBuild104.IsolationVariable);
                    Check(!string.IsNullOrEmpty(fixture)&&File.Exists(fixture)&&new FileInfo(fixture).Length<=8192,"Explicit isolated preparation configuration is required");
                    Check(StagingServerBuild104.Preflight(File.ReadAllText(fixture,new UTF8Encoding(false,true)),receipt).Length==0,"Actual component fixture requires the fresh contained clone and intact source receipt");
                }
                Case("strict public parser and canonical nonsecret payload",()=>{
                    var parsed=ServerGameplayConfiguration.Parse(Payload);Check(parsed.version==1&&parsed.mode=="ManagedGuestServer"&&parsed.socialEnabled&&!parsed.allowDevelopmentLoopback,"Strict legacy DTO fields parsed");
                    ServerGameplayConfiguration packaged;string error;Check(ServerStagingConfiguration104.TryParsePackaged(Payload,out packaged,out error)&&error==null,"Packaged public parser accepts bounded HTTPS staging metadata");
                    string canonical=ServerStagingConfiguration104.CanonicalJson(packaged);Check(canonical==ServerStagingConfiguration104.CanonicalJson(ServerGameplayConfiguration.Parse(canonical)),"Canonical packaged bytes round-trip deterministically");
                    Check(canonical==Payload&&canonical.Contains("\"allowDevelopmentLoopback\":false")&&canonical.Contains("\"socialEnabled\":true"),"Canonical output contains exactly the six known fields");
                    var legacy=ServerGameplayConfiguration.Parse("{\"version\":1,\"mode\":\"ManagedGuestServer\",\"origin\":\"http://127.0.0.1:18483\",\"identityScope\":\"review-native-104\",\"allowDevelopmentLoopback\":true}");Check(legacy.allowDevelopmentLoopback&&!legacy.socialEnabled,"Legacy explicit Editor loopback fixtures remain supported");
                    Check(!ServerStagingConfiguration104.TryParsePackaged(JsonUtility.ToJson(legacy),out packaged,out error)&&packaged==null&&error==ServerStagingConfiguration104.InvalidError,"Loopback review metadata cannot become packaged staging");
                    var optional=ServerGameplayConfiguration.Parse(Payload.Replace(",\"allowDevelopmentLoopback\":false,\"socialEnabled\":true",""));Check(!optional.allowDevelopmentLoopback&&!optional.socialEnabled,"Legacy optional flags default false without inventing activation");
                });
                Case("ambiguous secret extra type and origin rejection",()=>{
                    foreach(string bad in new[]{"{}","null","[]",Payload+"{}",Payload.Insert(1,"\"version\":1,"),Payload.Insert(1,"\"apiSecret\":\"not-a-real-secret\","),Payload.Insert(1,"\"unknown\":false,"),Payload.Insert(1,"\"identity\\u0053cope\":\"review-other\","),Payload.Replace("\"version\":1","\"version\":1.0"),Payload.Replace("\"socialEnabled\":true","\"socialEnabled\":\"true\""),Payload.Replace("\"allowDevelopmentLoopback\":false","\"allowDevelopmentLoopback\":0"),Payload.Replace("\"identityScope\":\"review-staging-native104\"","\"identityScope\":null"),Payload.Replace("review-staging-native104","ordinary-player"),new string(' ',8193),Payload.Replace(Origin,"https://user:password@host.native-fixture.net"),Payload.Replace(Origin,"https://staging.hotr-native-fixture.net/path"),Payload.Replace(Origin,"https://staging.hotr-native-fixture.net?secret=value"),Payload.Replace(Origin,"http://staging.hotr-native-fixture.net"),Payload.Replace(Origin,"https://127.0.0.1")}){
                        Reject(()=>ServerGameplayConfiguration.Parse(bad),"Malformed/ambiguous external input rejected with safe fixed error");ServerGameplayConfiguration value;string error;Check(!ServerStagingConfiguration104.TryParsePackaged(bad,out value,out error)&&value==null&&error==ServerStagingConfiguration104.InvalidError,"Packaged rejection also uses a safe fixed error");
                    }
                    Reject(()=>ServerStagingConfiguration104.CanonicalJson(null),"Null canonical input is rejected");
                    string multibyte=Payload.Insert(1,"\"extra\":\""+new string('\u044f',4100)+"\",");Reject(()=>ServerGameplayConfiguration.Parse(multibyte),"UTF8 byte limit cannot be bypassed with multibyte text");
                });
                Case("pure precedence and closed staging package",()=>{
                    var absent=ServerConfigurationInput104.Absent;var valid=Present(Payload);var other=Present(Payload.Replace(Origin,OtherOrigin));var invalid=Present("{}");
                    foreach(bool editor in new[]{false,true})foreach(bool development in new[]{false,true}){
                        Select(editor,development,"com.heartoftherain.verification",false,absent,absent,absent,false,"None",false);
                        Select(editor,development,"com.heartoftherain.verification",true,absent,absent,valid,true,"External",false);
                        Select(editor,development,"com.heartoftherain.verification",true,other,absent,valid,true,"External",true,OtherOrigin);
                        Select(editor,development,"com.heartoftherain.verification",false,absent,absent,valid,true,"Persistent",true);
                        Select(editor,development,ServerStagingConfiguration104.PackageName,true,other,valid,invalid,true,editor?"External":"Packaged",editor||development,editor?OtherOrigin:Origin);
                        Select(editor,development,"com.heartoftherain.verification",true,other,valid,valid,true,editor?"External":"Packaged",editor,OtherOrigin);
                        Select(editor,development,ServerStagingConfiguration104.PackageName,false,absent,invalid,valid,true,"Packaged",false);
                        Select(editor,development,ServerStagingConfiguration104.PackageName,false,absent,ServerConfigurationInput104.Invalid,valid,true,"Packaged",false);
                    }
                    Select(false,true,ServerStagingConfiguration104.PackageName,true,valid,absent,valid,true,"Packaged",false);
                    Select(false,false,ServerStagingConfiguration104.PackageName,false,absent,valid,absent,true,"Packaged",false);
                    Select(false,true,ServerStagingConfiguration104.PackageName,false,absent,valid,other,true,"Packaged",true);
                    var changed=Select(false,true,ServerStagingConfiguration104.PackageName,false,absent,Present(Payload.Replace("review-staging-native104","review-other104")),other,true,"Packaged",true);Check(changed.identityScope=="review-other104","Configured identity scope is selected verbatim without silently sharing or migrating a prior scope");
                    Select(true,true,ServerStagingConfiguration104.PackageName,true,ServerConfigurationInput104.Invalid,valid,valid,true,"External",false);
                });
                Directory.CreateDirectory(temporary);string path=Path.Combine(temporary,"configuration.json");Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",path);
                Case("real IO explicit override cannot fall through",()=>{
                    ServerGameplayConfiguration value;string error;Check(ServerGameplayConfiguration.TryRead(out value,out error)&&value==null&&error==ServerStagingConfiguration104.InvalidError,"Explicit missing file is selected-invalid");
                    File.WriteAllText(path,Payload,new UTF8Encoding(false));Check(ServerGameplayConfiguration.TryRead(out value,out error)&&value.origin==Origin&&value.socialEnabled,"Actual file IO uses strict external parser without contacting host");
                    File.WriteAllText(path,Payload,new UTF8Encoding(true));Check(ServerGameplayConfiguration.TryRead(out value,out error)&&value.origin==Origin,"Legacy UTF8-BOM file compatibility is preserved without relaxing packaged bytes");
                    using(var held=new FileStream(path,FileMode.Open,FileAccess.ReadWrite,FileShare.None))Check(ServerGameplayConfiguration.TryRead(out value,out error)&&value==null&&error==ServerStagingConfiguration104.InvalidError,"Unreadable explicitly selected file stays blocked");
                    File.WriteAllBytes(path,new byte[]{255,254});Check(ServerGameplayConfiguration.TryRead(out value,out error)&&value==null,"Malformed UTF8 cannot select a server or local fallback");
                    File.WriteAllBytes(path,new byte[8193]);Check(ServerGameplayConfiguration.TryRead(out value,out error)&&value==null,"Actual file length bound is enforced before decoding");
                    Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",temporary);Check(ServerGameplayConfiguration.TryRead(out value,out error)&&value==null,"Directory supplied as explicit config stays blocked");Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",path);
                });
                File.WriteAllText(path,"{}",new UTF8Encoding(false));
                if(componentCase)Case("actual invalid managed selection cannot open isolated ordinary local repository",()=>{
                    EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);GameObject owner=null;
                    try {
                        owner=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab"));var home=owner.GetComponent<HomePage>();home.enabled=false;home.State.coins=9876;
                        var assets=AssetDatabase.LoadAssetAtPath<PreLevelAssets>("Assets/HeartOfTheRain/App/PreLevel/PreLevelAssets.asset");var host=owner.AddComponent<PlayerProfileHost>();host.enabled=false;host.Initialize(home,assets);
                        Check(host.ServerSession&&!host.Ready&&!host.IsTransient,"Selected-invalid config creates unavailable managed host rather than local profile host");
                        Check(host.ServerSession.LastError==ServerStagingConfiguration104.InvalidError&&!host.ServerSession.Ready&&!host.ServerSession.Busy,"Invalid metadata never starts identity bootstrap or network work");
                        Check(host.ServerSession.PlayerId==null&&host.ServerSession.Wallet==null&&!host.ServerSession.HasPending,"No identity, wallet or attempt is minted from invalid config");
                        var repository=typeof(ProfileService).GetField("repository",Private).GetValue(host.Service);Check(ReferenceEquals(repository,host.ServerSession.Projection)&&host.Service.Read().coins==0,"Existing authoritative projection prevents local-wallet import/fallback");
                        bool rejected=false;try{host.Service.Change(p=>{p.coins++;return true;});}catch(InvalidOperationException error){rejected=error.Message=="ServerWalletIsAuthoritative";}Check(rejected,"Unavailable managed projection cannot accept a local grant");
                        Check(Tree(profilesRoot)==profiles&&Tree(serverRoot)==server,"Actual selected-invalid host does not touch ordinary profiles or protected ServerReview journals");
                        report.componentCaseVerified=true;
                    }finally{if(owner)UnityEngine.Object.DestroyImmediate(owner);}
                });
            }catch(Exception error){report.errors.Add(error.ToString());}
            finally {
                Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",previous);
                try{report.profilesPreserved=profiles!=null&&Tree(profilesRoot)==profiles;Check(report.profilesPreserved,"Ordinary profile bytes preserved");report.serverReviewPreserved=server!=null&&Tree(serverRoot)==server;Check(report.serverReviewPreserved,"Ordinary managed identity/journal/config bytes preserved");report.languagePreferencePreserved=PlayerPrefs.HasKey(GameLocale.PreferenceKey)==hadLanguage&&PlayerPrefs.GetInt(GameLocale.PreferenceKey,int.MinValue)==language;Check(report.languagePreferencePreserved,"Saved language key presence and value preserved");report.externalOverridePreserved=Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG")==previous;Check(report.externalOverridePreserved,"Explicit fixture environment override restored exactly");}catch(Exception error){report.errors.Add(error.ToString());}
                Application.logMessageReceived-=Log;string suffix=componentCase?"_ISOLATED":"";report.status=(report.errors.Count==0&&report.checks>0&&(!componentCase||report.componentCaseVerified)?"PASS_NATIVE_SERVER_CONFIGURATION104":"FAIL_NATIVE_SERVER_CONFIGURATION104")+suffix;File.WriteAllText(Path.Combine(output,"Native",componentCase?"ServerConfiguration104_Isolated.json":"ServerConfiguration104.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));
            }
            EditorApplication.Exit(report.status.StartsWith("PASS_NATIVE_SERVER_CONFIGURATION104",StringComparison.Ordinal)?0:1);
        }
        static void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(text+"\n"+stack);}
    }
}
#endif

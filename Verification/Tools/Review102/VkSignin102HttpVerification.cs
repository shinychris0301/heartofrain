#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Networking;
using HeartOfTheRain.App.AppSettings;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.ServerRewards;
using HeartOfTheRain.App.Settings;

namespace HeartOfTheRain.Verification {
    // Actual local HTTP/SQLite and device signatures. VK itself is an explicit
    // synthetic transport in the separately owned private server fixture.
    [InitializeOnLoad] public static class VkSignin102HttpVerification {
        const string Key="HOTR.VkSignin102.Http";
        const BindingFlags Hidden=BindingFlags.Instance|BindingFlags.NonPublic;
        [Serializable] sealed class Connection {public string runId=null,origin=null,serverConfigurationPath=null,operatorControlPath=null;}
        [Serializable] sealed class Operator {public bool seed,dropCompleteOnce;public string seedPlayerId,expireReadyFlow="";}
        [Serializable] sealed class ExpectedBindings {public string playerA,playerB,recoveryDigest;}
        [Serializable] sealed class Report {
            public string status="RUNNING",utc,unity,error,failedCheck,ordinaryProfilesBefore,ordinaryProfilesAfter,playerAHash,playerBHash;
            public string scope="Actual Unity Editor Home/gateway, managed guest signatures, protected journals, local OAuth callback routes and authoritative SQLite accounts. VK token/user_info HTTP is an explicit in-process MockTransport; no browser is opened. Private operator adds137 coins once to distinguish preserved target wallet and expires one Ready flow before signed completion. One after-commit HTTP503 is intentional. No real VK account/provider, Android Keystore, device, process restart, natural10minute expiry, local-save import or production acceptance.";
            public bool actualHttp=true,syntheticVkProvider=true,syntheticLocalAccessExpiry=true,browserOpened=false,android=false,productionEnabled=false;
            public bool registeredSamePlayer,registrationKeptRecovery,replyLossRecovered,sourceRenewalKeptFlow,cancelPreservedPlayer,confirmedExpiryRestoredSource,crossPlayerConfirmed,existingRecoveryNotImported,duplicateCompletionRejected;
            public int checks,finalCoins,finalLives;public List<string> passed=new List<string>();
        }
        sealed class Preferences:ISettingsStore {public int Read(string key,int fallback)=>fallback;public void Write(string key,int value){}public void Flush(){}}
        static Report report;static Connection connection;static HomePage home;static PlayerProfileHost host;static ServerGameSession server;static GameObject owner;
        static RewardReceiptPresenter receipts;static ServerRewardsSession rewards;static UnityWebRequest callback;
        static string playerA,playerB,recoveryA,authorize,output;static long sourceGeneration,sourceEpoch;static int phase;
        static bool launched,finished,done,ok;static string why;static double deadline;
        static VkSignin102HttpVerification(){if(SessionState.GetBool(Key,false))EditorApplication.update+=Tick;}
        static T Field<T>(object value,string name)=>(T)value.GetType().GetField(name,Hidden).GetValue(value);
        static void Check(bool value,string label){report.checks++;if(!value){report.failedCheck=label;throw new InvalidOperationException("Vk102ControlledAssertion");}report.passed.Add(label);}
        static void Complete(bool value,string error){done=true;ok=value;why=error;}
        static void Reset()=>done=false;
        static string ProfileDigest(){string root=Path.Combine(Application.persistentDataPath,"Profiles");return IdentityProtocol82.Sha(!Directory.Exists(root)?"absent":string.Join("\n",Directory.GetFiles(root,"*",SearchOption.AllDirectories).OrderBy(p=>p,StringComparer.Ordinal).Select(p=>p.Substring(root.Length)+":"+IdentityProtocol82.Sha(File.ReadAllBytes(p)))));}
        static Connection ReadConnection()=>JsonUtility.FromJson<Connection>(File.ReadAllText(Environment.GetEnvironmentVariable("HOTR_VK102_HTTP_CONFIG")));
        static void Control(bool seed=false,bool drop=false,string expire=""){
            string path=connection.operatorControlPath,temp=path+".native";
            File.WriteAllText(temp,JsonUtility.ToJson(new Operator{seed=seed,seedPlayerId=playerA,dropCompleteOnce=drop,expireReadyFlow=expire}));File.Replace(temp,path,null);
        }
        static void SavePrivateBindings()=>File.WriteAllText(Path.Combine(Path.GetDirectoryName(connection.operatorControlPath),"ExpectedBindings.json"),JsonUtility.ToJson(new ExpectedBindings{playerA=playerA,playerB=playerB,recoveryDigest=IdentityProtocol82.Sha(recoveryA)}));
        static string State(string url){
            var uri=new Uri(url);Check(uri.Scheme=="https"&&uri.Host=="id.vk.com"&&uri.AbsolutePath=="/authorize","Authorize URL is bounded to the official VK origin but is never opened");
            string[] states=uri.Query.TrimStart('?').Split('&').Where(x=>x.StartsWith("state=",StringComparison.Ordinal)).Select(x=>Uri.UnescapeDataString(x.Substring(6))).ToArray();
            Check(states.Length==1&&IdentityProtocol82.Secret(states[0]),"Exactly one state is copied only in memory to the private synthetic callback");return states[0];
        }
        static void Callback(string code){
            string state=State(authorize);
            callback=UnityWebRequest.Get(connection.origin+"/v1/identity/vk/callback?state="+Uri.EscapeDataString(state)+"&code="+Uri.EscapeDataString(code)+"&device_id=fixture-browser");
            callback.redirectLimit=0;callback.timeout=15;callback.SendWebRequest();
        }
        static bool CallbackReady(){
            if(!callback.isDone)return false;
            Check(callback.result==UnityWebRequest.Result.Success&&callback.responseCode==200,"Real local OAuth callback route completes using synthetic provider exchange");
            Check(callback.GetResponseHeader("Referrer-Policy")=="no-referrer"&&callback.GetResponseHeader("Cache-Control").Contains("no-store"),"OAuth callback page suppresses caching and referrer leakage");
            callback.Dispose();callback=null;return true;
        }
        public static void Run(){
            connection=ReadConnection();
            if(!Application.isBatchMode||!IdentityProtocol82.Id(connection.runId)||!RuStoreBackendClient.IsAllowedOrigin(connection.origin,true)||!new Uri(connection.origin).IsLoopback||!File.Exists(connection.serverConfigurationPath))throw new InvalidOperationException("ExplicitPrivateVk102FixtureRequired");
            SessionState.SetString(Key+".previousConfig",Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG")??"");Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",connection.serverConfigurationPath);
            SessionState.SetBool(Key,true);EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorApplication.update-=Tick;EditorApplication.update+=Tick;EditorApplication.isPlaying=true;
        }
        static void Launch(){
            launched=true;connection=ReadConnection();deadline=EditorApplication.timeSinceStartup+300;output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW102_OUT")??"../Verification/Evidence/Review102/VkHttp");
            report=new Report{utc=DateTime.UtcNow.ToString("O"),unity=Application.unityVersion,ordinaryProfilesBefore=ProfileDigest()};
            owner=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab"));home=owner.GetComponent<HomePage>();
            var flow=owner.GetComponent<HomeLevelFlow>();if(!flow)flow=owner.AddComponent<HomeLevelFlow>();flow.home=home;flow.assets=AssetDatabase.LoadAssetAtPath<PreLevelAssets>("Assets/HeartOfTheRain/App/PreLevel/PreLevelAssets.asset");
            var settings=owner.GetComponent<AppSettingsPage>();if(!settings)settings=owner.AddComponent<AppSettingsPage>();settings.home=home;settings.assets=AssetDatabase.LoadAssetAtPath<AppSettingsAssets>("Assets/HeartOfTheRain/App/AppSettings/AppSettingsAssets.asset");settings.VerificationStore=new Preferences();
        }
        static void Tick(){
            if(finished||!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
            try{
                if(!launched){Launch();return;}if(EditorApplication.timeSinceStartup>deadline)throw new TimeoutException();
                switch(phase){
                    case 0:
                        host=home.GetComponent<PlayerProfileHost>();if(!host||!host.Ready||!host.ServerSession||host.ServerSession.Busy)return;server=host.ServerSession;
                        Check(server.Ready&&!host.IsTransient&&server.Origin==connection.origin,"Ordinary host selects only the private managed service");
                        Check(server.Wallet.coins==1250&&server.Wallet.lives==5&&server.Wallet.activeAttempt==null,"First real managed guest begins with one unmodified genesis and no attempt");
                        playerA=server.PlayerId;report.playerAHash=IdentityProtocol82.Sha(playerA);recoveryA=Field<ManagedIdentitySession82>(server,"identity").RecoverySecretForExplicitBackup();
                        Check(IdentityProtocol82.Secret(recoveryA),"Registration source has its existing private recovery backup");SavePrivateBindings();host.enabled=false;
                        receipts=home.GetComponent<RewardReceiptPresenter>();if(receipts)receipts.enabled=false;rewards=home.GetComponent<ServerRewardsSession>();phase=1;return;
                    case 1:
                        if(server.Busy||(receipts&&Field<bool>(receipts,"recovering"))||(rewards&&(rewards.Coordinator==null||rewards.Coordinator.Busy||rewards.HomeMetadataBusy)))return;
                        if(rewards)rewards.enabled=false;Check(!server.HasPending,"No background financial action is pending before VK intent");Reset();server.AccountVkBegin(Complete);phase=2;return;
                    case 2:
                        if(!done)return;Check(ok&&server.AccountVkStatus!=null&&server.AccountVkStatus.phase=="Pending","VK begin durably prepares a real source-bound pending flow");
                        Check(server.PlayerId==playerA&&server.Wallet.coins==1250&&!server.AccountBlocked,"Beginning authorization does not replace the current player or wallet");authorize=server.AccountVkStatus.authorizeUrl;
                        Callback("fixture-first");phase=3;return;
                    case 3:
                        if(!CallbackReady())return;Reset();server.AccountVkRefresh(Complete);phase=4;return;
                    case 4:
                        if(!done)return;Check(ok&&server.AccountVkStatus.phase=="Ready"&&server.AccountVkStatus.targetPlayerId==playerA&&!server.AccountVkStatus.requiresConfirmation,"Unlinked VK prepares registration to the same existing guest");
                        Reset();server.AccountVkComplete(playerA,false,Complete);Check(done&&!ok&&server.PlayerId==playerA&&!server.AccountBlocked,"Unconfirmed completion is rejected without changing the source");
                        Control(drop:true);Reset();server.AccountVkComplete(playerA,true,Complete);phase=5;return;
                    case 5:
                        if(!done)return;Check(!ok&&server.AccountBlocked&&server.AccountIdentityPending,"Intentional after-commit503 retains a blocked durable pending identity instead of creating a guest");
                        Reset();server.AccountResume(Complete);phase=6;return;
                    case 6:
                        if(!done)return;Check(ok&&server.Ready&&!server.AccountBlocked&&server.PlayerId==playerA,"Exact signed retry recovers the committed same-player registration");report.replyLossRecovered=true;
                        Check(server.Wallet.coins==1250&&server.Wallet.lives==5&&server.Wallet.activeAttempt==null,"Registration does not grant a second wallet, currency, life or attempt");report.registeredSamePlayer=true;
                        Check(Field<ManagedIdentitySession82>(server,"identity").RecoverySecretForExplicitBackup()==recoveryA,"Same-player registration preserves the known original recovery backup");report.registrationKeptRecovery=true;
                        Reset();server.AccountVkComplete(playerA,true,Complete);Check(done&&!ok&&server.PlayerId==playerA,"Completed flow cannot be completed again through a stale UI callback");report.duplicateCompletionRejected=true;
                        Control(seed:true);Reset();server.Refresh(Complete);phase=7;return;
                    case 7:
                        if(!done)return;Check(ok&&server.Wallet.coins==1250+137,"One private operator ledger seed distinguishes the preserved target wallet");
                        Reset();server.AccountVkBegin(Complete);phase=8;return;
                    case 8:
                        if(!done)return;Check(ok&&server.AccountVkStatus.phase=="Pending","A later separate authorization gets its own durable flow");Reset();server.AccountVkCancel(Complete);phase=9;return;
                    case 9:
                        if(!done)return;Check(ok&&server.AccountVkStatus.phase=="Cancelled"&&server.PlayerId==playerA&&server.Wallet.coins==1387&&!server.AccountBlocked,"Cancellation preserves the authenticated player and seeded wallet");report.cancelPreservedPlayer=true;
                        Reset();server.AccountVkBegin(Complete);phase=90;return;
                    case 90:
                        if(!done)return;Check(ok&&server.AccountVkStatus.phase=="Pending","A separate flow is prepared for controlled post-confirmation expiry");authorize=server.AccountVkStatus.authorizeUrl;Callback("fixture-first");phase=91;return;
                    case 91:
                        if(!CallbackReady())return;Reset();server.AccountVkRefresh(Complete);phase=92;return;
                    case 92:
                        if(!done)return;Check(ok&&server.AccountVkStatus.phase=="Ready"&&server.AccountVkStatus.targetPlayerId==playerA,"Expiry control begins from the authoritative Ready target");
                        Control(expire:server.AccountVkStatus.flowId);Reset();server.AccountVkComplete(playerA,true,Complete);phase=93;return;
                    case 93:
                        if(!done)return;Check(!ok&&server.Ready&&!server.AccountBlocked&&!server.AccountIdentityPending&&server.PlayerId==playerA&&server.Wallet.coins==1387,"Confirmed but uncommitted expired authorization restores the original account without stranding its selector");
                        Check(server.AccountVkStatus!=null&&server.AccountVkStatus.phase=="Expired"&&string.IsNullOrEmpty(server.AccountVkStatus.targetPlayerId),"Authoritative terminal expiry clears the stale target after real failed completion/status reconciliation");report.confirmedExpiryRestoredSource=true;
                        Reset();server.AccountLogout(true,Complete);phase=10;return;
                    case 10:
                        if(!done)return;Check(ok&&server.AccountBlocked&&!server.Ready,"Explicit logout closes the first game session before another guest is created");Reset();server.AccountStartFresh(true,Complete);phase=11;return;
                    case 11:
                        if(!done)return;Check(ok&&server.Ready&&server.PlayerId!=playerA&&server.Wallet.coins==1250,"Explicit fresh guest has a separate server-owned wallet");
                        playerB=server.PlayerId;report.playerBHash=IdentityProtocol82.Sha(playerB);SavePrivateBindings();Reset();server.AccountVkBegin(Complete);phase=12;return;
                    case 12:
                        if(!done)return;Check(ok&&server.AccountVkStatus.phase=="Pending"&&server.PlayerId==playerB,"New guest prepares a new fresh-key sign-in without selecting another account");authorize=server.AccountVkStatus.authorizeUrl;
                        Callback("fixture-first");phase=13;return;
                    case 13:
                        if(!CallbackReady())return;Reset();server.AccountVkRefresh(Complete);phase=14;return;
                    case 14:
                        if(!done)return;Check(ok&&server.AccountVkStatus.phase=="Ready"&&server.AccountVkStatus.targetPlayerId==playerA&&server.AccountVkStatus.requiresConfirmation,"Existing VK resolves the exact earlier player and requests explicit account-switch confirmation");
                        Check(server.PlayerId==playerB&&server.Wallet.coins==1250,"Browser callback alone cannot mint or promote a different game account");
                        Reset();server.AccountVkComplete(playerB,true,Complete);Check(done&&!ok&&server.PlayerId==playerB,"Confirmation for a different displayed target is rejected");
                        Reset();server.AccountVkComplete(playerA,false,Complete);Check(done&&!ok&&server.PlayerId==playerB,"Missing explicit account-switch confirmation retains the original player");
                        sourceGeneration=server.SessionGeneration;sourceEpoch=server.PlayerOwnershipEpoch;typeof(ManagedIdentitySession82).GetField("accessSeconds",Hidden).SetValue(Field<ManagedIdentitySession82>(server,"identity"),0d);
                        Reset();server.AccountVkRefresh(Complete);phase=15;return;
                    case 15:
                        if(!done)return;Check(ok&&server.SessionGeneration>sourceGeneration&&server.PlayerOwnershipEpoch==sourceEpoch&&server.PlayerId==playerB&&server.AccountVkStatus.targetPlayerId==playerA,"Actual same-player access renewal retains the exact authorized source family and pending VK target");report.sourceRenewalKeptFlow=true;
                        Reset();server.AccountVkComplete(playerA,true,Complete);phase=16;return;
                    case 16:
                        if(!done)return;Check(ok&&server.Ready&&!server.AccountBlocked&&server.PlayerId==playerA&&server.PlayerOwnershipEpoch>sourceEpoch,"Explicit signed completion adopts the exact existing VK owner with a new protected device scope");
                        Check(server.Wallet.coins==1387&&server.Wallet.lives==5&&server.Wallet.activeAttempt==null,"Restored account retains its own ledger instead of merging source guest currency or attempts");
                        Check(!server.AccountCanCopyRecovery&&!Field<ManagedIdentitySession82>(server,"identity").HasRecoveryBackup,"Cross-device VK authentication does not fabricate or expose another device recovery code");
                        report.existingRecoveryNotImported=true;report.crossPlayerConfirmed=true;report.finalCoins=server.Wallet.coins;report.finalLives=server.Wallet.lives;
                        Reset();server.AccountVkComplete(playerA,true,Complete);Check(done&&!ok&&server.PlayerId==playerA&&server.Wallet.coins==1387,"Repeated confirmation cannot switch again or duplicate a grant");
                        UnityEngine.Object.DestroyImmediate(owner);Finish(true);return;
                }
            }catch(Exception error){if(report!=null)report.error=error.GetType().Name+" at controlled phase "+phase;Finish(false);}
        }
        static void Finish(bool success){
            if(finished)return;finished=true;EditorApplication.update-=Tick;recoveryA=null;authorize=null;callback?.Dispose();callback=null;
            Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",SessionState.GetString(Key+".previousConfig",""));SessionState.EraseString(Key+".previousConfig");SessionState.EraseBool(Key);
            if(report==null)report=new Report{error="FixtureSetupFailed"};report.ordinaryProfilesAfter=ProfileDigest();
            if(report.ordinaryProfilesBefore!=report.ordinaryProfilesAfter){success=false;report.error="OrdinaryProfileFilesChanged";}
            report.status=success?"PASS_NATIVE_VK_SIGNIN102_HTTP":"FAIL_NATIVE_VK_SIGNIN102_HTTP";
            if(string.IsNullOrEmpty(output))output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW102_OUT")??"../Verification/Evidence/Review102/VkHttp");
            Directory.CreateDirectory(Path.Combine(output,"Native"));File.WriteAllText(Path.Combine(output,"Native/VkSignin102Http.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(success?0:1);
        }
    }
}
#endif

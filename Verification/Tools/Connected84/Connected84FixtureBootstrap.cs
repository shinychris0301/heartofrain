using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;

public sealed class Connected84FixtureBootstrap:MonoBehaviour {
    public GameObject homePrefab;public PreLevelAssets levelAssets;
    [Serializable] sealed class ProtectedProof {
        public int version=1;public string scopeHash,originHash,playerId,backupSecret,lastStage,identityKeyFingerprint;
        public int coins,stars,lives,completed,currentLevel;public long revision;public int[] starting,tools;
    }
    [Serializable] sealed class Report {
        public string status="FAIL_ANDROID_CONNECTED84_STAGE",utc,unity,stage,scopeHash,originHash,package,proofKeyFingerprint,serverKeyFingerprint,playerIdHash,ordinaryProfilesBefore,ordinaryProfilesAfter,errorCode,stageBefore;
        public int pid,sdk,checks,coins,stars,lives,completed,currentLevel;public long revision;
        public int[] starting,tools;public bool actualAndroid,actualIl2cpp,androidSigningKeyNonexportable,androidEncryptionKeyNonexportable,hardwareBackedReported;
        public bool actualServerFactory,readOnlyProfile,selectedStartingSpent,paidToolVerified,explicitQuit,backupOnlyProtectedStore,closed,ready,exactWalletRestored,noAutomaticGuest,deletionConfirmed,recoveryChangedDeviceKey;
        public List<string> passed=new List<string>();
        public string scope="Actual isolated-package Android Home/ProfileHost + explicit managed-server session. Programmatic ordinary Play/paid Hammer/explicit quit and account lifecycle across externally distinct processes. No normal startup routing, physical input, live payment/provider SDK, OS power-loss, production deployment, hardware-attestation or whole-game claim. Ordinary applications are outside this process; their nonmutation requires an external before/after audit.";
    }
    string scope,stage,origin,reportPath,proofDigest="";Report report;ProtectedProof proof;
    AndroidDeviceIdentity82 protectedStore;HomePage home;HomeLevelFlow flow;PlayerProfileHost host;ServerGameSession server;double deadline;
    bool done,success;string resultCode;
    static readonly string[] Stages={"setup","reopen","logout","closed","recover","recovered","delete","deleted"};
    void Check(bool condition,string code){report.checks++;if(!condition){report.errorCode=code;throw new InvalidOperationException(code);}report.passed.Add(code);}
    void Complete(bool ok,string code){done=true;success=ok;resultCode=code;}
    static string ProfilesDigest(){string folder=Path.Combine(Application.persistentDataPath,"Profiles");return IdentityProtocol82.Sha(!Directory.Exists(folder)?"absent":string.Join("\n",Directory.GetFiles(folder,"*",SearchOption.AllDirectories).OrderBy(x=>x,StringComparer.Ordinal).Select(x=>x.Substring(folder.Length)+":"+IdentityProtocol82.Sha(File.ReadAllBytes(x)))));}
    void ReadProof(){
        byte[] bytes=protectedStore.Read();if(bytes==null){proofDigest="";proof=null;return;}
        try{proof=JsonUtility.FromJson<ProtectedProof>(new UTF8Encoding(false,true).GetString(bytes));proofDigest=IdentityProtocol82.Sha(bytes);Check(proof!=null&&proof.version==1&&proof.scopeHash==report.scopeHash&&proof.originHash==report.originHash&&IdentityProtocol82.Id(proof.playerId),"ProtectedProofOwnerBound");}
        finally{Array.Clear(bytes,0,bytes.Length);}
    }
    void SaveProof(){
        byte[] bytes=new UTF8Encoding(false,true).GetBytes(JsonUtility.ToJson(proof));
        try{protectedStore.CompareExchange(proofDigest,bytes);proofDigest=IdentityProtocol82.Sha(bytes);byte[] observed=protectedStore.Read();try{Check(observed!=null&&IdentityProtocol82.Sha(observed)==proofDigest,"ProtectedProofDurableCAS");}finally{if(observed!=null)Array.Clear(observed,0,observed.Length);}}
        finally{Array.Clear(bytes,0,bytes.Length);}
    }
    void RememberWallet(){var value=server.Wallet;proof.coins=value.coins;proof.stars=value.stars;proof.lives=value.lives;proof.completed=value.completed;proof.currentLevel=value.currentLevel;proof.revision=value.revision;proof.starting=(int[])value.starting.Clone();proof.tools=(int[])value.tools.Clone();}
    void CheckWallet(){var value=server.Wallet;Check(server.PlayerId==proof.playerId&&value.playerId==proof.playerId&&value.coins==proof.coins&&value.stars==proof.stars&&value.lives==proof.lives&&value.completed==proof.completed&&value.currentLevel==proof.currentLevel&&value.revision==proof.revision&&value.starting.SequenceEqual(proof.starting)&&value.tools.SequenceEqual(proof.tools)&&value.activeAttempt==null,"ExactAuthoritativeWalletAfterProcessBoundary");Check(IdentityProtocol82.Digest(proof.identityKeyFingerprint)&&server.Connected84IdentityKeyFingerprint==proof.identityKeyFingerprint,"BoundDeviceKeyPersistsAcrossProcessBoundary");report.exactWalletRestored=true;}
    IEnumerator Await(Func<bool> condition,string timeout){while(!condition()){if(Time.realtimeSinceStartupAsDouble>deadline){report.errorCode=timeout;throw new InvalidOperationException(timeout);}yield return null;}}
    IEnumerator Ready(){yield return Await(()=>server!=null&&!server.Busy&&(server.Ready||server.AccountBlocked),"SessionInitializationTimeout");}
    IEnumerator Invoke(Action<Action<bool,string>> operation){done=false;success=false;resultCode=null;operation(Complete);yield return Await(()=>done,"AccountOrWalletRequestTimeout");Check(success,KnownCode(resultCode));}
    static string KnownCode(string value){switch(value){case "AccountBusy":case "AccountSessionClosed":case "AccountPendingActions":case "AccountActiveAttempt":case "AccountRecoveryInputInvalid":case "AccountRecoveryUnknown":case "AccountRecoveryUnavailable":case "AccountRecoveryCodeRequired":case "AccountIntentSaveUnconfirmed":case "AccountSelectionConfirmationUnconfirmed":case "IdentityHttp401":case "IdentityHttp422":case "IdentityNetworkUnavailable":case "ServerVerificationPending":case "ServerModelMismatch":case "ServerSessionUnavailable":case "ServerJournalUnavailable":return value;default:return "RequestNotConfirmed";}}
    IEnumerator Start(){
        report=new Report{utc=DateTime.UtcNow.ToString("O"),unity=Application.unityVersion,package=Application.identifier};
        try{
#if UNITY_ANDROID && !UNITY_EDITOR
            using(var unity=new AndroidJavaClass("com.unity3d.player.UnityPlayer"))using(var activity=unity.GetStatic<AndroidJavaObject>("currentActivity"))using(var intent=activity.Call<AndroidJavaObject>("getIntent")){
                scope=intent.Call<string>("getStringExtra","connected84_scope");stage=intent.Call<string>("getStringExtra","connected84_stage");origin=intent.Call<string>("getStringExtra","connected84_origin");
            }
            using(var process=new AndroidJavaClass("android.os.Process"))report.pid=process.CallStatic<int>("myPid");using(var version=new AndroidJavaClass("android.os.Build$VERSION"))report.sdk=version.GetStatic<int>("SDK_INT");
            report.actualAndroid=true;
#if ENABLE_IL2CPP
            report.actualIl2cpp=true;
#endif
#endif
            if(scope==null||!Regex.IsMatch(scope,@"\Aqa84-[0-9a-f]{32}\z")||!Stages.Contains(stage)||!RuStoreBackendClient.IsAllowedOrigin(origin,true)||!new Uri(origin).IsLoopback||Application.identifier!="com.heartoftherain.connected84fixture"||!Debug.isDebugBuild)throw new InvalidOperationException("ExplicitIsolatedFixtureArgumentsRequired");
            origin=new Uri(origin).GetLeftPart(UriPartial.Authority);report.stage=stage;report.scopeHash=IdentityProtocol82.Sha(scope);report.originHash=IdentityProtocol82.Sha(origin);deadline=Time.realtimeSinceStartupAsDouble+240;
            reportPath=Path.Combine(Application.persistentDataPath,"Connected84","Reports",report.scopeHash,"Stage_"+stage+".json");if(File.Exists(reportPath))throw new InvalidOperationException("StageReportAlreadyExists");
            Check(report.actualAndroid&&report.actualIl2cpp&&report.sdk>=26,"ActualAndroidIl2cppApi26");report.ordinaryProfilesBefore=ProfilesDigest();
            protectedStore=new AndroidDeviceIdentity82("review-c84-proof-"+scope.Substring(5));report.proofKeyFingerprint=IdentityProtocol82.Sha(protectedStore.PublicSpkiDer());ReadProof();if(stage!="setup")Check(proof!=null,"PriorProtectedProofRequired");else Check(proof==null,"FreshProtectedScopeRequired");report.stageBefore=proof?.lastStage;
            string configuration=Path.Combine(Application.persistentDataPath,"ServerReview","configuration.json");string json=JsonUtility.ToJson(new ServerGameplayConfiguration{version=1,mode="ManagedGuestServer",origin=origin,identityScope="review-c84-"+scope.Substring(5),allowDevelopmentLoopback=true,socialEnabled=false});
            if(File.Exists(configuration))Check(File.ReadAllText(configuration)==json,"ExistingFixtureConfigurationOwnerBound");else{Check(stage=="setup","InitialSetupRequiredBeforeConfiguration");Directory.CreateDirectory(Path.GetDirectoryName(configuration));File.WriteAllText(configuration,json,new UTF8Encoding(false));}
            Check(homePrefab&&levelAssets,"FrozenHomeAndLevelAssetsBound");var owner=Instantiate(homePrefab);home=owner.GetComponent<HomePage>();flow=owner.AddComponent<HomeLevelFlow>();flow.home=home;flow.assets=levelAssets;
        }catch(Exception error){Fail(error);yield break;}
        var work=new Stack<IEnumerator>();work.Push(RunStage());while(work.Count>0){bool more;object current=null;try{more=work.Peek().MoveNext();if(more)current=work.Peek().Current;}catch(Exception error){Fail(error);yield break;}if(!more){(work.Pop() as IDisposable)?.Dispose();continue;}if(current is IEnumerator nested){work.Push(nested);continue;}yield return current;}
        Finish();
    }
    IEnumerator RunStage(){
        yield return Await(()=>home.GetComponent<PlayerProfileHost>()!=null,"OrdinaryHostMissing");host=home.GetComponent<PlayerProfileHost>();yield return Await(()=>host.ServerSession!=null,"ExplicitServerFactoryMissing");server=host.ServerSession;yield return Ready();report.actualServerFactory=!host.IsTransient&&server!=null;
        Check(report.actualServerFactory,"OrdinaryHostSelectedExplicitServerFactory");bool rejected=false;try{host.Service.Change(p=>{p.coins+=1;return true;});}catch(InvalidOperationException){rejected=true;}Check(rejected,"ReadOnlyProjectionCannotGrantCoins");report.readOnlyProfile=true;
        if(stage=="setup"){
            Check(server.Ready&&server.Wallet.coins==1250&&server.Wallet.lives==5,"ServerGuestGenesis1250And5Lives");proof=new ProtectedProof{scopeHash=report.scopeHash,originHash=report.originHash,playerId=server.PlayerId,backupSecret=server.Connected84BackupForProtectedStore(),identityKeyFingerprint=server.Connected84IdentityKeyFingerprint,lastStage="prepared"};Check(IdentityProtocol82.Secret(proof.backupSecret)&&IdentityProtocol82.Digest(proof.identityKeyFingerprint),"BackupCanonicalAndPublicFingerprintBound");RememberWallet();SaveProof();report.backupOnlyProtectedStore=true;
            flow.Open(1);var preview=home.GetComponent<PreLevelModal>();preview.Requested("toggle:0");preview.Requested("play");yield return Await(()=>flow.Connected84ActualBoard&&flow.Connected84ActualBoard.Ready&&!flow.Connected84ActualBoard.Busy&&!flow.Connected84ActualBoard.ReviewInputBlocked&&!server.Busy&&flow.Loading&&!flow.Loading.IsVisible,"ActualGameplayInitializationTimeout");
            var board=flow.Connected84ActualBoard;Check(server.Wallet.starting[0]==proof.starting[0]-1&&server.Wallet.lives==5&&board.CurrentSeed==(uint)server.Attempt.seed,"ActualPlayConsumesSelectedRocketOnce");report.selectedStartingSpent=true;var gem=board.Model.Pieces.Values.Where(p=>p.family=="gem").OrderBy(p=>p.y).ThenBy(p=>p.x).First();board.UseBooster(BoosterKind.Hammer,gem.x,gem.y);
            yield return Await(()=>board&&board.Ready&&!board.Busy&&!board.ReviewInputBlocked&&!server.Busy&&server.LastOperation!=null,"PaidHammerVerificationTimeout");Check(server.Wallet.tools[0]==proof.tools[0]-1&&server.LastOperation.model?.checkpointSHA256==ProfileJson.Hash(JsonUtility.ToJson(board.Model.Checkpoint())),"ActualPaidHammerMatchesPinnedWorkerCheckpoint");report.paidToolVerified=true;flow.Connected84ExplicitForfeit();yield return Await(()=>!flow.Connected84ActualBoard&&!server.Busy,"ExplicitQuitTimeout");Check(server.Wallet.lives==4&&server.Wallet.activeAttempt==null&&server.Wallet.starting[0]==4&&server.Wallet.tools[0]==2,"ActualExplicitQuitLosesOneLifeKeepsSpentInventory");report.explicitQuit=true;RememberWallet();proof.lastStage="setup";SaveProof();
        }else if(stage=="reopen"||stage=="recovered"){
            Check(server.Ready,"ReopenedServerSessionReady");CheckWallet();if(stage=="reopen")Check(proof.lastStage=="setup","ReopenFollowsSetup");else Check(proof.lastStage=="recover","RecoveredReopenFollowsRecovery");proof.lastStage=stage;SaveProof();
        }else if(stage=="logout"){
            Check(server.Ready&&proof.lastStage=="reopen","LogoutFollowsVerifiedReopen");CheckWallet();yield return Invoke(callback=>server.AccountLogout(true,callback));Check(!server.Ready&&server.AccountBlocked&&server.AccountState=="closed","ExplicitLogoutClosed");Check(host.Service.Read().coins==0&&!host.Ready,"UnavailableProjectionAfterLogout");proof.lastStage="logout";SaveProof();
        }else if(stage=="closed"||stage=="deleted"){
            Check(proof.lastStage==(stage=="closed"?"logout":"delete"),"ClosedStageOrder");Check(server.AccountBlocked&&!server.Ready&&server.AccountState=="closed","ClosedStatePersistsAcrossNewProcess");server.RetryInitialize();double until=Time.realtimeSinceStartupAsDouble+1.0;while(Time.realtimeSinceStartupAsDouble<until)yield return null;Check(!server.Busy&&!server.Ready&&server.AccountState=="closed"&&host.Service.Read().coins==0,"ClosedDoesNotAutomaticallyCreateGuest");report.noAutomaticGuest=true;proof.lastStage=stage;SaveProof();
        }else if(stage=="recover"){
            Check(proof.lastStage=="closed"&&IdentityProtocol82.Secret(proof.backupSecret),"RecoveryUsesOnlyProtectedBackup");Check(server.AccountBlocked&&!server.Ready,"RecoveryStartsFromExplicitClosedState");yield return Invoke(callback=>server.AccountRecover(proof.playerId,proof.backupSecret,true,callback));Check(server.Ready&&!server.AccountBlocked,"ExplicitFreshKeyRecoveryReady");Check(IdentityProtocol82.Digest(server.Connected84IdentityKeyFingerprint)&&server.Connected84IdentityKeyFingerprint!=proof.identityKeyFingerprint,"RecoveryUsesADifferentPublicDeviceKey");report.recoveryChangedDeviceKey=true;proof.identityKeyFingerprint=server.Connected84IdentityKeyFingerprint;CheckWallet();proof.backupSecret="";proof.lastStage="recover";SaveProof();report.backupOnlyProtectedStore=true;
        }else if(stage=="delete"){
            Check(server.Ready&&proof.lastStage=="recovered","DeletionFollowsRecoveredProcessProof");CheckWallet();yield return Invoke(callback=>server.AccountRequestDeletion(true,callback));Check(!server.Ready&&server.AccountBlocked&&server.AccountState=="closed"&&host.Service.Read().coins==0,"ExplicitDeletionClosedWithoutLocalFallback");proof.backupSecret="";proof.lastStage="delete";SaveProof();report.deletionConfirmed=true;
        }
    }
    void Fail(Exception error){if(report==null)report=new Report();if(report.errorCode==null)report.errorCode=error.GetType().Name;Finish();}
    void Finish(){
        if(report==null||reportPath==null)return;
        try{
            report.ordinaryProfilesAfter=ProfilesDigest();if(report.ordinaryProfilesAfter!=report.ordinaryProfilesBefore)report.errorCode="IsolatedOrdinaryProfilesChanged";if(server){report.serverKeyFingerprint=server.Connected84IdentityKeyFingerprint;report.closed=server.AccountBlocked;report.ready=server.Ready;if(server.Ready){var wallet=server.Wallet;report.coins=wallet.coins;report.stars=wallet.stars;report.lives=wallet.lives;report.completed=wallet.completed;report.currentLevel=wallet.currentLevel;report.revision=wallet.revision;report.starting=wallet.starting;report.tools=wallet.tools;}}
            if(proof!=null)report.playerIdHash=IdentityProtocol82.Sha(proof.playerId);if(protectedStore!=null){var diagnostics=protectedStore.Diagnostics();report.androidSigningKeyNonexportable=diagnostics[0];report.androidEncryptionKeyNonexportable=diagnostics[1];report.hardwareBackedReported=diagnostics[3];if(!diagnostics[0]||!diagnostics[1])report.errorCode="KeystoreNonexportabilityRequired";}
            if(report.errorCode==null)report.status="PASS_ANDROID_CONNECTED84_STAGE";Directory.CreateDirectory(Path.GetDirectoryName(reportPath));using(var file=new FileStream(reportPath,FileMode.CreateNew,FileAccess.Write,FileShare.Read)){byte[] bytes=new UTF8Encoding(false).GetBytes(JsonUtility.ToJson(report,true));file.Write(bytes,0,bytes.Length);file.Flush(true);}Debug.Log("CONNECTED84_EXPLICIT_STAGE_COMPLETE");
        }finally{if(proof!=null)proof.backupSecret=null;proof=null;protectedStore?.Dispose();protectedStore=null;}
    }
}

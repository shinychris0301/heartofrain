#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
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
    // Copied into the isolated Editor project by the owned native runner only.
    // The private service owns the operator seed; no test endpoint ships.
    [InitializeOnLoad] public static class Refill101HttpVerification {
        const string Key="HOTR.Refill101.Http";const BindingFlags Hidden=BindingFlags.Instance|BindingFlags.NonPublic;
        [Serializable] sealed class Connection {public string runId=null,origin=null,serverConfigurationPath=null,operatorControlPath=null;}
        [Serializable] sealed class Seed {public string seedPlayerId;public bool seed=true;}
        [Serializable] sealed class TimerSeed {public string timerPlayerId;public bool timerSeed=true;}
        [Serializable] sealed class Report {
            public string status="RUNNING",utc,unity,error,ordinaryProfilesBefore,ordinaryProfilesAfter,playerHash,freshPlayerHash;
            public string scope="Actual Editor ordinary Home/ProfileHost and lives/refill UGUI against real managed identity and authoritative wallet HTTP. Reflected local access-lifetime expiry exercises actual EnsureIdentity session refresh. Private operator genesis adjustment, synthetic stale presentation tickets, and ephemeral Editor keys are controlled fixtures. Actual logout/recover/same-player ABA/fresh-player/destruction transitions exercise production ownership guards. No Android, provider login/payment, process-restart identity or production acceptance.";
            public bool actualHttp=true,editorIdentityEphemeral=true,syntheticLocalExpiry=true,android=false,productionEnabled=false;
            public bool actualRefillTap,renewalKeptOwnership,refillUnlocked,staleTicketsRejected,samePlayerAbaRejected,differentPlayerRejected,destroyRejected,blockedSourceRejected,openSheetRegenerated;
            public long generationBefore,generationAfter,ownershipBefore,ownershipAfter;
            public int checks,finalCoins,finalLives;public List<string> passed=new List<string>();
        }
        sealed class Preferences:ISettingsStore {public int Read(string key,int fallback)=>fallback;public void Write(string key,int value){}public void Flush(){}}
        static Report report;static Connection connection;static HomePage home;static HomeLevelFlow flow;static PlayerProfileHost host;static ServerGameSession server;static PreLevelModal modal;static GameObject owner;
        static RewardReceiptPresenter receipts;static ServerRewardsSession rewards;static PreLevelSession presentation;static PreLevelRefillTicket oldTicket;
        static bool launched,finished,done,ok;static string why,player,secret,output;static long epoch,afterAbaEpoch;static int phase,seedFrame;static double deadline;
        static Refill101HttpVerification(){if(SessionState.GetBool(Key,false))EditorApplication.update+=Tick;}
        static T Field<T>(object value,string name)=>(T)value.GetType().GetField(name,Hidden).GetValue(value);
        static void Check(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);report.passed.Add(label);}
        static void Complete(bool value,string error){done=true;ok=value;why=error;}
        static string ProfileDigest(){string root=Path.Combine(Application.persistentDataPath,"Profiles");return IdentityProtocol82.Sha(!Directory.Exists(root)?"absent":string.Join("\n",Directory.GetFiles(root,"*",SearchOption.AllDirectories).OrderBy(p=>p,StringComparer.Ordinal).Select(p=>p.Substring(root.Length)+":"+IdentityProtocol82.Sha(File.ReadAllBytes(p)))));}
        static Connection ReadConnection()=>JsonUtility.FromJson<Connection>(File.ReadAllText(Environment.GetEnvironmentVariable("HOTR_REFILL101_HTTP_CONFIG")));
        public static void Run(){
            connection=ReadConnection();
            if(!Application.isBatchMode||!IdentityProtocol82.Id(connection.runId)||!RuStoreBackendClient.IsAllowedOrigin(connection.origin,true)||!new Uri(connection.origin).IsLoopback||!File.Exists(connection.serverConfigurationPath))throw new InvalidOperationException("ExplicitPrivateRefill101FixtureRequired");
            SessionState.SetString(Key+".previousConfig",Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG")??"");Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",connection.serverConfigurationPath);
            SessionState.SetBool(Key,true);EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorApplication.update-=Tick;EditorApplication.update+=Tick;EditorApplication.isPlaying=true;
        }
        static void Launch(){
            launched=true;connection=ReadConnection();deadline=EditorApplication.timeSinceStartup+240;output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW101_OUT")??"../Verification/Evidence/Review101/RefillHttp");
            report=new Report{utc=DateTime.UtcNow.ToString("O"),unity=Application.unityVersion,ordinaryProfilesBefore=ProfileDigest()};
            owner=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab"));home=owner.GetComponent<HomePage>();flow=owner.GetComponent<HomeLevelFlow>();if(!flow)flow=owner.AddComponent<HomeLevelFlow>();flow.home=home;flow.assets=AssetDatabase.LoadAssetAtPath<PreLevelAssets>("Assets/HeartOfTheRain/App/PreLevel/PreLevelAssets.asset");
            var settings=owner.GetComponent<AppSettingsPage>();if(!settings)settings=owner.AddComponent<AppSettingsPage>();settings.home=home;settings.assets=AssetDatabase.LoadAssetAtPath<AppSettingsAssets>("Assets/HeartOfTheRain/App/AppSettings/AppSettingsAssets.asset");settings.VerificationStore=new Preferences();
        }
        static void TapHeart(){
            Canvas.ForceUpdateCanvases();var nodes=Field<Dictionary<string,RectTransform>>(home,"nodes");var header=nodes["header"];var button=nodes["lives"].GetComponent<Button>();
            var point=RectTransformUtility.WorldToScreenPoint(null,header.TransformPoint(new Vector3(header.rect.width*.60f,-header.rect.height*.5f,0)));
            var data=new PointerEventData(EventSystem.current){position=point,button=PointerEventData.InputButton.Left};var hits=new List<RaycastResult>();EventSystem.current.RaycastAll(data,hits);Check(hits.Count>0&&hits[0].gameObject.GetComponentInParent<Button>()==button,"Actual header heart raycast reaches the lives control");ExecuteEvents.Execute(button.gameObject,data,ExecuteEvents.pointerClickHandler);
        }
        static void CheckOwner(long captured,string expectedPlayer,bool expected,string label)=>Check(server.OwnsPlayer(captured,connection.origin,expectedPlayer)==expected,label);
        static void Tick(){
            if(finished||!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
            try{
                if(!launched){Launch();return;}if(EditorApplication.timeSinceStartup>deadline)throw new TimeoutException("Refill101 HTTP phase "+phase);
                switch(phase){
                    case 0:
                        host=home.GetComponent<PlayerProfileHost>();if(!host||!host.Ready||!host.ServerSession||host.ServerSession.Busy||!flow.CanOpenAppSettings)return;server=host.ServerSession;modal=home.GetComponent<PreLevelModal>();
                        Check(server.Ready&&!host.IsTransient&&server.Origin==connection.origin,"Ordinary host selects the isolated real managed service");Check(server.Wallet.coins==1250&&server.Wallet.lives==5,"Actual guest genesis starts1250 coins5 lives");
                        player=server.PlayerId;report.playerHash=IdentityProtocol82.Sha(player);home.State.reduceMotion=true;host.enabled=false;receipts=home.GetComponent<RewardReceiptPresenter>();if(receipts)receipts.enabled=false;rewards=home.GetComponent<ServerRewardsSession>();phase=1;return;
                    case 1:
                        if(server.Busy||(receipts&&Field<bool>(receipts,"recovering"))||(rewards&&(rewards.Coordinator==null||rewards.Coordinator.Busy||rewards.HomeMetadataBusy)))return;if(rewards)rewards.enabled=false;
                        Check(!server.HasPending&&server.Wallet.activeAttempt==null,"No attempt or pending financial action before fixture seed");File.WriteAllText(connection.operatorControlPath,JsonUtility.ToJson(new Seed{seedPlayerId=player}));done=false;server.Refresh(Complete);phase=2;return;
                    case 2:
                        if(!done)return;Check(ok&&server.Wallet.coins==900&&server.Wallet.lives==0&&host.Refresh(),"Private immutable operator seed produces actual900coins0lives projection");
                        report.generationBefore=server.SessionGeneration;epoch=server.PlayerOwnershipEpoch;report.ownershipBefore=epoch;CheckOwner(epoch,player,true,"Ready player owns the current presentation epoch");
                        var identity=Field<ManagedIdentitySession82>(server,"identity");secret=identity.RecoverySecretForExplicitBackup();Check(IdentityProtocol82.Secret(secret),"Isolated recovery material is available only in memory for actual ABA test");
                        typeof(ManagedIdentitySession82).GetField("accessSeconds",Hidden).SetValue(identity,0d);Check(!identity.HasAccess,"Synthetic local access expiry requires actual EnsureIdentity renewal");seedFrame=Time.frameCount;phase=20;return;
                    case 20:
                        if(Time.frameCount<=seedFrame)return;TapHeart();Check(modal.IsVisible&&flow.Preview.livesOnly&&flow.Preview.lives==0,"Actual heart control opens dedicated zero-life view");seedFrame=Time.frameCount;phase=21;return;
                    case 21:
                        if(Time.frameCount<=seedFrame)return;
                        var nodes=Field<Dictionary<string,RectTransform>>(modal,"nodes");var button=nodes["play"].GetComponent<Button>();Check(button.IsInteractable(),"900coin refill is available before actual tap");ExecuteEvents.Execute(button.gameObject,new PointerEventData(EventSystem.current){button=PointerEventData.InputButton.Left},ExecuteEvents.pointerClickHandler);
                        presentation=Field<PreLevelSession>(flow,"session");oldTicket=Field<PreLevelRefillTicket>(presentation,"pendingRefill");Check(oldTicket!=null&&flow.Preview.busy&&server.Busy,"Actual refill tap reserves presentation while real HTTP is pending");report.actualRefillTap=true;phase=3;return;
                    case 3:
                        if(server.Busy||flow.Preview.busy)return;
                        report.generationAfter=server.SessionGeneration;report.ownershipAfter=server.PlayerOwnershipEpoch;
                        Check(report.generationAfter>report.generationBefore&&server.PlayerId==player&&server.PlayerOwnershipEpoch==epoch,"Actual same-player HTTP renewal changes access generation and preserves ownership");report.renewalKeptOwnership=true;
                        CheckOwner(epoch,player,true,"Original presentation owner survives actual bearer renewal");CheckOwner(epoch,new string('f',32),false,"Different player cannot own this presentation");Check(!server.OwnsPlayer(epoch,connection.origin+"/wrong",player),"Different origin cannot own this presentation");
                        Check(server.Wallet.coins==0&&server.Wallet.lives==5&&!server.HasPending&&server.Wallet.activeAttempt==null,"Real service refill deducts900once and restores5lives without attempt");
                        Check(modal.IsVisible&&flow.Preview.livesOnly&&flow.Preview.lives==5&&!flow.Preview.busy&&!flow.Playing&&!flow.Loading.IsVisible&&Field<Dictionary<string,RectTransform>>(modal,"nodes")["lives-count"].GetComponent<Text>().text=="5 / 5","Actual pending refill ticket unlocks and renders fresh full-life state");report.refillUnlocked=true;report.finalCoins=server.Wallet.coins;report.finalLives=server.Wallet.lives;
                        Check(!presentation.CompleteRefill(oldTicket),"Duplicate completed real refill ticket cannot complete twice");modal.Requested("close");
                        presentation.OpenLives(0,5);PreLevelRefillTicket freshTicket;Check(presentation.TryBeginRefill(out freshTicket),"Synthetic later view obtains a separate presentation ticket without HTTP purchase");Check(!presentation.CompleteRefill(oldTicket)&&presentation.View.busy&&presentation.OwnsRefill(freshTicket),"Stale previous-view ticket cannot unlock the newer pending view");Check(presentation.CompleteRefill(freshTicket)&&!presentation.CompleteRefill(freshTicket)&&presentation.Close(),"New synthetic presentation ticket completes once");report.staleTicketsRejected=true;
                        done=false;server.AccountLogout(true,Complete);phase=4;return;
                    case 4:
                        if(!done)return;Check(ok&&server.AccountBlocked&&!server.Ready&&server.PlayerOwnershipEpoch>epoch,"Actual logout invalidates player ownership and closes session");CheckOwner(epoch,player,false,"Original pending owner is rejected after actual logout");
                        presentation.OpenLives(0,5);modal.Show(presentation.View);modal.Requested("refill");Check(!presentation.View.busy&&Field<PreLevelRefillTicket>(presentation,"pendingRefill")==null&&!string.IsNullOrEmpty(presentation.View.message),"Synthetic refill on an actually closed source is rejected before reserving any ticket");modal.Requested("close");Check(!modal.IsVisible,"Invalid-source lives sheet remains closable");report.blockedSourceRejected=true;
                        done=false;server.AccountRecover(player,secret,true,Complete);phase=5;return;
                    case 5:
                        if(!done)return;Check(ok&&server.Ready&&server.PlayerId==player&&server.PlayerOwnershipEpoch>epoch,"Actual recovery returns to the same player with a fresh account epoch");secret=null;CheckOwner(epoch,player,false,"Same-player logout/recovery ABA cannot revive an old presentation");afterAbaEpoch=server.PlayerOwnershipEpoch;CheckOwner(afterAbaEpoch,player,true,"Recovered same-player account has its own valid ownership epoch");Check(server.Wallet.coins==0&&server.Wallet.lives==5,"Actual recovery preserves the single committed refill wallet");report.samePlayerAbaRejected=true;done=false;server.AccountLogout(true,Complete);phase=6;return;
                    case 6:
                        if(!done)return;Check(ok&&server.AccountBlocked,"Second actual logout permits explicit fresh guest");done=false;server.AccountStartFresh(true,Complete);phase=7;return;
                    case 7:
                        if(!done)return;Check(ok&&server.Ready&&server.PlayerId!=player&&server.PlayerOwnershipEpoch>afterAbaEpoch,"Actual fresh guest promotes a different player and account epoch");CheckOwner(afterAbaEpoch,player,false,"Different-player promotion rejects previous player's ownership");CheckOwner(epoch,player,false,"Original owner remains rejected after ABA and different-player switch");report.freshPlayerHash=IdentityProtocol82.Sha(server.PlayerId);report.differentPlayerRejected=true;
                        Check(server.Wallet.coins==1250&&server.Wallet.lives==5,"Fresh guest genesis is isolated from the paid refill audit");File.WriteAllText(connection.operatorControlPath,JsonUtility.ToJson(new TimerSeed{timerPlayerId=server.PlayerId}));done=false;server.Refresh(Complete);phase=8;return;
                    case 8:
                        if(!done)return;Check(ok&&server.Wallet.coins==1250&&server.Wallet.lives==3&&host.Refresh(),"Private immutable timer seed produces actual3of5 partial lives");seedFrame=Time.frameCount;phase=80;return;
                    case 80:
                        if(Time.frameCount<=seedFrame)return;TapHeart();Check(modal.IsVisible&&flow.Preview.livesOnly&&flow.Preview.lives==3,"Actual heart opens partial-lives sheet before trusted life timer is due");phase=9;return;
                    case 9:
                        if(server.Busy||flow.Preview.lives<4)return;Check(modal.IsVisible&&flow.Preview.livesOnly&&flow.Preview.lives==4&&server.Wallet.lives==4&&server.Wallet.coins==1250&&server.Wallet.activeAttempt==null,"Open lives sheet requests actual due-time wallet read and displays4of5 without spend or attempt");Check(string.IsNullOrEmpty(flow.Preview.message)&&Field<Dictionary<string,RectTransform>>(modal,"nodes")["lives-count"].GetComponent<Text>().text=="4 / 5","Authoritative natural regeneration clears updating state and rerenders the visible count");report.openSheetRegenerated=true;modal.Requested("close");
                        long beforeDestroy=server.PlayerOwnershipEpoch;string freshPlayer=server.PlayerId;bool destroyedFence=false;server.IdentityChanged+=()=>{if(server.PlayerOwnershipEpoch>beforeDestroy&&!server.OwnsPlayer(beforeDestroy,connection.origin,freshPlayer))destroyedFence=true;};
                        UnityEngine.Object.DestroyImmediate(owner);Check(destroyedFence,"Actual component destruction advances account epoch and rejects old ownership");report.destroyRejected=true;Finish(true);return;
                }
            }catch(Exception error){if(report!=null)report.error=error is InvalidOperationException||error is TimeoutException?error.Message:error.GetType().Name+" at phase "+phase;Finish(false);}
        }
        static void Finish(bool success){
            if(finished)return;finished=true;EditorApplication.update-=Tick;secret=null;Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",SessionState.GetString(Key+".previousConfig", ""));SessionState.EraseString(Key+".previousConfig");SessionState.EraseBool(Key);
            if(report==null)report=new Report{error="Fixture setup failed"};report.ordinaryProfilesAfter=ProfileDigest();if(report.ordinaryProfilesBefore!=report.ordinaryProfilesAfter){success=false;report.error="Ordinary profile files changed";}report.status=success?"PASS_NATIVE_REFILL101_HTTP":"FAIL_NATIVE_REFILL101_HTTP";
            Directory.CreateDirectory(Path.Combine(output,"Native"));File.WriteAllText(Path.Combine(output,"Native/Refill101Http.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(success?0:1);
        }
    }
}
#endif

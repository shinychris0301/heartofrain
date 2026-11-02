#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.AccountDesign;
using HeartOfTheRain.App.AppSettings;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.ServerAccount;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.Settings;
using HeartOfTheRain.App.RuStore;

namespace HeartOfTheRain.Verification {
    // Actual service + ordinary Settings/Account UI. The Editor key provider is
    // explicitly ephemeral; this is not Android/process-restart identity proof.
    [InitializeOnLoad] public static class ServerAccount83HttpVerification {
        const string Key="HOTR.ServerAccount83.Http";
        static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        [Serializable] sealed class Report {
            public string status,utc,unity,scope,playerIdHash,newPlayerIdHash,ordinaryProfilesBefore,ordinaryProfilesAfter;
            public int checks,finalCoins,finalLives,recoveredLives;public bool recoveredRemoteAttemptPreserved,remoteAttemptExplicitlyForfeited;public string remotePlayerIdHash;public bool actualHttp=true,editorIdentityEphemeral=true,android=false,productionEnabled=false;
            public int[] rejectedRecoveryHttpStatuses=new int[0];public bool rejectedRecoveryBlocked,rejectedRecoveryReady,rejectedRecoveryCanRestart;
            public bool selectedThroughOrdinaryHost,maskedRecovery,clipboardOnly,explicitLogout,explicitRecovery,explicitDeletion,explicitFreshGuest,settingsReturn,localAppearanceUnchanged;
            public bool gatewayBusyWhenAccountOpened,backupActionDispatched,backupWarningShown,copyActionDispatched,copyNoticeSuccess,clipboardReadbackValid;public int accountUiWaits,clipboardReadbackLength=-1;
            public List<string> passed=new List<string>(),errors=new List<string>(),captures=new List<string>();
        }
        sealed class Preferences:ISettingsStore {readonly Dictionary<string,int> values=new Dictionary<string,int>();public int Read(string key,int fallback)=>values.TryGetValue(key,out var value)?value:fallback;public void Write(string key,int value)=>values[key]=value;public void Flush(){}}
        static Report report;static HomePage home;static HomeLevelFlow flow;static PlayerProfileHost host;static ServerGameSession server;static AppSettingsPage settings;static ProfilePage profile;
        static EditorEphemeralIdentity82 remoteVault;static ManagedIdentitySession82 remoteIdentity;static IdentityHttpTransport82 remoteTransport;static RuStoreBackendClient remoteClient;static IdentityReply82<IdentityView82> remoteIdentityReply;static PayReply<RuStoreServerWallet> remoteWalletReply;static PayReply<RuStoreWalletMutation> remoteMutation;static string remoteAttemptId;
        static int phase,idleFrame;static bool launched,finished,done,ok;static string why,output,playerId,recoveryCode,oldClipboard,appearanceBefore;static double deadline;
        static ServerAccount83HttpVerification(){if(SessionState.GetBool(Key,false))EditorApplication.update+=Tick;}
        static T Field<T>(object owner,string name)=>(T)owner.GetType().GetField(name,Private).GetValue(owner);
        static void Check(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);report.passed.Add(label);}
        static void Complete(bool value,string error){done=true;ok=value;why=error;}
        static string ProfileDigest(){string root=Path.Combine(Application.persistentDataPath,"Profiles");return IdentityProtocol82.Sha(!Directory.Exists(root)?"absent":string.Join("\n",Directory.GetFiles(root,"*",SearchOption.AllDirectories).OrderBy(p=>p,StringComparer.Ordinal).Select(p=>p.Substring(root.Length)+":"+IdentityProtocol82.Sha(File.ReadAllBytes(p)))));}
        static object SizeGroup(){var assembly=typeof(UnityEditor.Editor).Assembly;var type=assembly.GetType("UnityEditor.GameViewSizes");var singleton=typeof(ScriptableSingleton<>).MakeGenericType(type).GetProperty("instance",BindingFlags.Public|BindingFlags.Static).GetValue(null);return type.GetMethod("GetGroup").Invoke(singleton,new[]{Enum.Parse(assembly.GetType("UnityEditor.GameViewSizeGroupType"),EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android?"Android":"Standalone")});}
        static EditorWindow GameView()=>EditorWindow.GetWindow(typeof(UnityEditor.Editor).Assembly.GetType("UnityEditor.GameView"));
        static void SetPortrait(){var group=SizeGroup();var view=GameView();int first=(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null);SessionState.SetInt(Key+".first",first);SessionState.SetInt(Key+".previous",(int)view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).GetValue(view));var assembly=typeof(UnityEditor.Editor).Assembly;var size=Activator.CreateInstance(assembly.GetType("UnityEditor.GameViewSize"),BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic,null,new object[]{Enum.Parse(assembly.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),900,1600,"HOTR Account83 portrait"},null);group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{size});SessionState.SetBool(Key+".portrait",true);view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(view,first);view.Repaint();}
        static void RestorePortrait(){if(!SessionState.GetBool(Key+".portrait",false))return;var view=GameView();view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(view,SessionState.GetInt(Key+".previous",0));var group=SizeGroup();group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{SessionState.GetInt(Key+".first",0)});SessionState.EraseBool(Key+".portrait");}
        public static void Run(){
            string origin=Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_HTTP_ORIGIN");if(Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_HTTP_ALLOWED")!="1"||!HeartOfTheRain.App.RuStore.RuStoreBackendClient.IsAllowedOrigin(origin,true)||!new Uri(origin).IsLoopback)throw new InvalidOperationException("ExplicitIsolatedAccountFixtureRequired");
            string directory=Path.GetFullPath("../.verification-cache/ServerAccount83/Http/"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(directory);string config=Path.Combine(directory,"configuration.json");File.WriteAllText(config,JsonUtility.ToJson(new ServerGameplayConfiguration{version=1,mode="ManagedGuestServer",origin=origin,identityScope="review-account-http-83",allowDevelopmentLoopback=true,socialEnabled=true}),new UTF8Encoding(false));
            SessionState.SetString(Key+".previousConfig",Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG")??"");Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",config);SessionState.SetBool(Key,true);SetPortrait();EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorApplication.update-=Tick;EditorApplication.update+=Tick;EditorApplication.isPlaying=true;
        }
        static void Launch(){
            launched=true;deadline=EditorApplication.timeSinceStartup+240;oldClipboard=GUIUtility.systemCopyBuffer;output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_OUTPUT")??"../Verification/Evidence/ServerGameplay83");Directory.CreateDirectory(Path.Combine(output,"Native"));
            report=new Report{utc=DateTime.UtcNow.ToString("O"),unity=Application.unityVersion,scope="Actual Editor Play Mode ordinary Home/ProfileHost and Settings Save Progress/Account controls against real loopback managed-identity and authoritative wallet HTTP. Typed reserve/start/explicit quit blocks identity transition while active; clipboard-only backup, masked account recovery through a fresh ephemeral key, a second real remote guest/Started attempt preserved until explicit forfeit with a durable attemptId decision, logout/no automatic guest, explicit deletion/no physical-purge claim and explicit fresh guest. No Android Keystore, process restart, provider SDK login, live payments, new model/verifier certification, automatic visual approval or performance claim."};report.ordinaryProfilesBefore=ProfileDigest();
            var prefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab");var owner=UnityEngine.Object.Instantiate(prefab);home=owner.GetComponent<HomePage>();flow=owner.AddComponent<HomeLevelFlow>();flow.home=home;flow.assets=AssetDatabase.LoadAssetAtPath<PreLevelAssets>("Assets/HeartOfTheRain/App/PreLevel/PreLevelAssets.asset");settings=owner.AddComponent<AppSettingsPage>();settings.home=home;settings.assets=AssetDatabase.LoadAssetAtPath<AppSettingsAssets>("Assets/HeartOfTheRain/App/AppSettings/AppSettingsAssets.asset");settings.VerificationStore=new Preferences();
        }
        static void Capture(string name){
            Check(Screen.width==900&&Screen.height==1600,"Account portrait capture900x1600");var canvases=UnityEngine.Object.FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID).Where(c=>c.isActiveAndEnabled&&c.renderMode==RenderMode.ScreenSpaceOverlay).OrderBy(c=>c.sortingOrder).ToArray();var cameras=canvases.Select(c=>c.worldCamera).ToArray();var distances=canvases.Select(c=>c.planeDistance).ToArray();var node=new GameObject("Account83 native capture");node.transform.position=new Vector3(-10000,0,-10);var camera=node.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;var target=RenderTexture.GetTemporary(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);var previous=RenderTexture.active;Texture2D image=null;
            try{camera.targetTexture=target;foreach(var canvas in canvases){canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=1;}Canvas.ForceUpdateCanvases();camera.Render();camera.Render();RenderTexture.active=target;image=new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);image.ReadPixels(new Rect(0,0,target.width,target.height),0,0);image.Apply();string relative="Native/Account/"+name+".png";Directory.CreateDirectory(Path.GetDirectoryName(Path.Combine(output,relative)));File.WriteAllBytes(Path.Combine(output,relative),image.EncodeToPNG());report.captures.Add(relative);}
            finally{for(int n=0;n<canvases.Length;n++){canvases[n].renderMode=RenderMode.ScreenSpaceOverlay;canvases[n].worldCamera=cameras[n];canvases[n].planeDistance=distances[n];}RenderTexture.active=previous;RenderTexture.ReleaseTemporary(target);if(image)UnityEngine.Object.Destroy(image);UnityEngine.Object.Destroy(node);Canvas.ForceUpdateCanvases();}
        }
        static void NoRenderedSecret(){Check(!home.GetComponentsInChildren<Text>(true).Any(t=>!string.IsNullOrEmpty(recoveryCode)&&t.text.Contains(recoveryCode)),"Recovery code absent from rendered text");}
        // Respect the same asynchronous availability and scroll viewport as a
        // person using these controls. Never poll or substitute clipboard data.
        static bool ReadyAccountButton(string name,out Button button){
            button=null;if(server.Busy||settings.AccountView.IsBusy){report.accountUiWaits++;return false;}
            button=settings.AccountView.GetComponentsInChildren<Button>().FirstOrDefault(b=>b.name==name&&b.gameObject.activeInHierarchy);
            if(!button||!button.IsInteractable()){report.accountUiWaits++;return false;}
            Canvas.ForceUpdateCanvases();var scroll=Field<ScrollRect>(settings.AccountView,"scroll");var viewport=scroll.viewport;
            var bounds=RectTransformUtility.CalculateRelativeRectTransformBounds(viewport,button.transform);float delta=bounds.max.y>viewport.rect.yMax?viewport.rect.yMax-bounds.max.y:bounds.min.y<viewport.rect.yMin?viewport.rect.yMin-bounds.min.y:0;
            if(Mathf.Abs(delta)>.1f){
                scroll.StopMovement();var position=scroll.content.anchoredPosition;float maximum=Mathf.Max(0,scroll.content.rect.height-viewport.rect.height);position.y=Mathf.Clamp(position.y+delta,0,maximum);scroll.content.anchoredPosition=position;
                report.accountUiWaits++;return false;
            }
            return bounds.min.x>=viewport.rect.xMin-.1f&&bounds.max.x<=viewport.rect.xMax+.1f&&bounds.min.y>=viewport.rect.yMin-.1f&&bounds.max.y<=viewport.rect.yMax+.1f;
        }
        static void Tick(){
            if(finished||!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
            try{
                if(!launched){Launch();return;}if(EditorApplication.timeSinceStartup>deadline)throw new TimeoutException("Account stage "+phase);if(Screen.width!=900||Screen.height!=1600)return;
                switch(phase){
                    case 0:
                        host=home.GetComponent<PlayerProfileHost>();if(!host||!host.Ready||settings.ReviewSession==null||host.ServerSession.Busy)return;server=host.ServerSession;Check(server&&server.Ready&&!host.IsTransient,"Ordinary host selected explicit server factory");report.selectedThroughOrdinaryHost=true;playerId=server.PlayerId;report.playerIdHash=IdentityProtocol82.Sha(playerId);Check(server.Wallet.coins==1250&&server.Wallet.lives==5,"Server genesis starts1250 coins5 lives");profile=ProfilePage.Attach(home);appearanceBefore=JsonUtility.ToJson(Field<ProfileStore>(profile,"store").Snapshot);done=false;server.Reserve(1,new[]{1,0,0,0},Complete);phase=1;return;
                    case 1:
                        if(!done)return;Check(ok,"Reserve actual server attempt");done=false;server.StartAttempt(Complete);phase=2;return;
                    case 2:
                        if(!done)return;Check(ok&&server.Wallet.starting[0]==4,"Start spends selected Rocket once");done=false;server.AccountLogout(true,Complete);Check(done&&!ok&&why=="AccountActiveAttempt"&&server.Ready,"Active attempt blocks identity close");done=false;server.AccountEndAttempt(true,Complete);phase=3;return;
                    case 3:
                        if(!done)return;Check(ok&&server.Wallet.lives==4&&server.Wallet.activeAttempt==null,"Explicit forfeit settles one loss before identity transition");settings.Show();Capture("Settings_Save_Progress");settings.Request("save-progress");Check(settings.AccountView.IsVisible&&settings.AccountView.ScreenKey=="server"&&settings.AccountView.Snapshot.ServerSaved&&!settings.AccountView.Snapshot.linked,"Ordinary Save Progress opens truthful managed guest");var settingsCanvas=Field<Canvas>(settings,"canvas");var fade=Field<CanvasGroup>(settings,"fade");Check(fade.alpha==0&&!fade.blocksRaycasts&&!settingsCanvas.GetComponent<GraphicRaycaster>().enabled,"Suspended Settings is not invisible blocking input");Capture("Server_Saved");
                        report.gatewayBusyWhenAccountOpened=server.Busy;idleFrame=Time.frameCount;phase=31;return;
                    case 31:
                        if(Time.frameCount<=idleFrame)return;Button backup;
                        if(!ReadyAccountButton("Back up account",out backup))return;
                        Check(backup.IsInteractable()&&backup.gameObject.activeInHierarchy,"Backup control is visible and enabled after provider/session preparation");
                        backup.onClick.Invoke();report.backupActionDispatched=true;
                        Check(Field<string>(settings.AccountView,"serverScreen")=="backup","Explicit Backup button opens the backup screen");
                        report.backupWarningShown=settings.AccountView.GetComponentsInChildren<Text>().Any(t=>t.name=="Recovery privacy warning"&&t.gameObject.activeInHierarchy);
                        Check(report.backupWarningShown,"Actual backup warning is present before Copy");Capture("Backup_Warning");idleFrame=Time.frameCount;phase=32;return;
                    case 32:
                        if(Time.frameCount<=idleFrame)return;Button copy;
                        if(!ReadyAccountButton("Copy recovery code",out copy))return;
                        Check(Field<string>(settings.AccountView,"serverScreen")=="backup","Copy remains on the backup warning screen");
                        copy.onClick.Invoke();report.copyActionDispatched=true;report.copyNoticeSuccess=Field<string>(settings.AccountView,"serverNotice")=="serverCodeCopied";
                        Check(report.copyNoticeSuccess,"Explicit Copy dispatch reaches the managed service successfully");
                        recoveryCode=GUIUtility.systemCopyBuffer;report.clipboardReadbackLength=recoveryCode?.Length??0;report.clipboardReadbackValid=IdentityProtocol82.Secret(recoveryCode);
                        Check(report.clipboardReadbackValid,"Explicit Copy returns a valid recovery code only to clipboard");report.clipboardOnly=true;NoRenderedSecret();settings.AccountView.Request("server-logout");settings.AccountView.Request("server-confirm-action");phase=4;return;
                    case 4:
                        if(server.Busy)return;Check(!server.Ready&&server.AccountBlocked&&server.AccountState=="closed"&&!host.Ready&&home.State.coins==0,"Logout closes identity and clears unavailable private projection");report.explicitLogout=true;server.RetryInitialize();idleFrame=Time.frameCount;phase=5;return;
                    case 5:
                        if(Time.frameCount<=idleFrame+2)return;Check(!server.Ready&&server.AccountState=="closed","Retry does not automatically create guest after logout");Capture("Signed_Out");settings.AccountView.Request("server-recover");Field<InputField>(settings.AccountView,"recoveryPlayerInput").text=playerId;var input=Field<InputField>(settings.AccountView,"recoveryCodeInput");string wrongCode=IdentityProtocol82.NewSecret();while(wrongCode==recoveryCode)wrongCode=IdentityProtocol82.NewSecret();input.text=wrongCode;Check(IdentityProtocol82.Secret(wrongCode),"Rejected-code fixture is canonical and distinct from real backup");Check(input.contentType==InputField.ContentType.Password,"Ordinary recovery input is masked");report.maskedRecovery=true;NoRenderedSecret();Capture("Recovery_Masked_Entry");settings.AccountView.Request("server-review-switch");Check(Field<string>(settings.AccountView,"serverScreen")=="switchConfirm","Actual recovery review reaches explicit switch confirmation");NoRenderedSecret();Capture("Recovery_Switch_Confirmation");settings.AccountView.Request("server-confirm-switch");phase=50;return;
                    case 50:
                        if(server.Busy)return;report.rejectedRecoveryHttpStatuses=Field<IdentityHttpTransport82>(server,"pendingIdentityTransport")?.VerificationStatuses??new int[0];report.rejectedRecoveryBlocked=server.AccountBlocked;report.rejectedRecoveryReady=server.Ready;report.rejectedRecoveryCanRestart=server.AccountCanStartAnotherRecovery;Check(!server.Ready&&server.AccountCanStartAnotherRecovery&&server.AccountState=="recover","Actual rejected recovery stays blocked and permits explicit different-code action");Check(home.GetComponentsInChildren<Button>().Any(b=>b.name=="Use another recovery code"&&b.interactable),"Actual rejected recovery exposes another-code control");Capture("Recovery_Rejected_Pending");settings.AccountView.Request("server-recover");Field<InputField>(settings.AccountView,"recoveryPlayerInput").text=playerId;Field<InputField>(settings.AccountView,"recoveryCodeInput").text=recoveryCode;settings.AccountView.Request("server-review-switch");Check(Field<string>(settings.AccountView,"serverScreen")=="switchConfirm","Canonical corrected code reaches retained-request warning");NoRenderedSecret();Capture("Retained_Recovery_Warning");settings.AccountView.Request("server-confirm-switch");phase=6;return;
                    case 6:
                        if(server.Busy)return;Check(server.Ready&&server.PlayerId==playerId&&server.Wallet.lives==4&&server.Wallet.starting[0]==4&&server.Wallet.coins==1250,"Recovery preserves authoritative account and spent inventory/life without new genesis");report.explicitRecovery=true;report.recoveredLives=server.Wallet.lives;Check(JsonUtility.ToJson(Field<ProfileStore>(profile,"store").Snapshot)==appearanceBefore,"Local appearance preferences stay unchanged across recovery");report.localAppearanceUnchanged=true;NoRenderedSecret();
                        remoteVault=new EditorEphemeralIdentity82();remoteTransport=new IdentityHttpTransport82(server.Origin,r=>server.StartCoroutine(r),true);remoteIdentity=new ManagedIdentitySession82(remoteVault.CreateKey(),new OriginBoundIdentityStore82(remoteVault.CreateStore(Path.GetFullPath("../.verification-cache/Launch82/ServerAccount83/Remote/"+Guid.NewGuid().ToString("N")+".sealed")),server.Origin),remoteTransport);remoteIdentity.CreateGuest(Guid.NewGuid().ToString("N"),r=>remoteIdentityReply=r);phase=60;return;
                    case 60:
                        if(remoteIdentityReply==null)return;Check(remoteIdentityReply.Succeeded,"Separate explicit remote-device guest created through real identity HTTP");remoteClient=new RuStoreBackendClient(server.Origin,remoteIdentity.AccessToken,remoteIdentity.View.playerId,true,true,r=>server.StartCoroutine(r));remoteClient.GetWallet(r=>remoteWalletReply=r);phase=61;return;
                    case 61:
                        if(remoteWalletReply==null)return;Check(remoteWalletReply.Succeeded&&remoteWalletReply.value.lives==5,"Separate remote account has authoritative initial wallet");remoteClient.Reserve(Guid.NewGuid().ToString("N"),remoteWalletReply.value.revision,1,new int[4],r=>remoteMutation=r);phase=62;return;
                    case 62:
                        if(remoteMutation==null)return;Check(remoteMutation.Succeeded,"Remote account reserved a real service-owned attempt");var reserved=remoteMutation.value;remoteAttemptId=reserved.attempt.attemptId;remoteMutation=null;remoteClient.Start(Guid.NewGuid().ToString("N"),reserved.wallet.revision,remoteAttemptId,r=>remoteMutation=r);phase=63;return;
                    case 63:
                        if(remoteMutation==null)return;Check(remoteMutation.Succeeded&&remoteMutation.value.attempt.state=="Started"&&remoteMutation.value.wallet.lives==5,"Remote Started attempt has not lost a life");playerId=remoteIdentity.View.playerId;report.remotePlayerIdHash=IdentityProtocol82.Sha(playerId);recoveryCode=remoteIdentity.RecoverySecretForExplicitBackup();settings.AccountView.Request("server-recover");Field<InputField>(settings.AccountView,"recoveryPlayerInput").text=playerId;Field<InputField>(settings.AccountView,"recoveryCodeInput").text=recoveryCode;settings.AccountView.Request("server-review-switch");NoRenderedSecret();settings.AccountView.Request("server-confirm-switch");phase=64;return;
                    case 64:
                        if(server.Busy)return;Check(server.Ready&&server.PlayerId==playerId&&server.Wallet.activeAttempt?.attemptId==remoteAttemptId&&server.Wallet.lives==5,"Recovering account does not silently forfeit its remote Started attempt");idleFrame=Time.frameCount;phase=65;return;
                    case 65:
                        if(Time.frameCount<=idleFrame+4)return;Check(server.Wallet.activeAttempt?.attemptId==remoteAttemptId&&server.Wallet.lives==5,"Recovered remote attempt remains unchanged while awaiting explicit decision");var selection=Field<AccountSelection83>(server,"accountSelector").Read();Check(selection.recoveredAttemptDecision&&selection.recoveredAttemptId==remoteAttemptId,"Remote-attempt decision is durably bound to its own attemptId");report.recoveredRemoteAttemptPreserved=true;Capture("Recovered_Remote_Attempt_Decision");settings.AccountView.Request("server-forfeit");Check(server.Wallet.lives==5,"Forfeit warning has not charged a life");settings.AccountView.Request("server-confirm-action");phase=66;return;
                    case 66:
                        if(server.Busy)return;Check(server.Ready&&server.Wallet.activeAttempt==null&&server.Wallet.lives==4&&!Field<AccountSelection83>(server,"accountSelector").Read().recoveredAttemptDecision,"Only explicit confirmed forfeit settles remote attempt and clears persisted decision");report.remoteAttemptExplicitlyForfeited=true;settings.AccountView.Request("server-delete");Capture("Deletion_Retention_Warning");Check(server.Ready,"First deletion warning has not closed account");settings.AccountView.Request("server-delete-next");Check(server.Ready,"Second deletion screen still requires explicit final action");Capture("Deletion_Final_Confirmation");settings.AccountView.Request("server-delete-next");phase=7;return;
                    case 7:
                        if(server.Busy)return;Check(!server.Ready&&server.AccountBlocked&&server.AccountState=="closed"&&!host.Ready&&home.State.coins==0,"Confirmed deletion closes guest without local wallet fallback");report.explicitDeletion=true;server.RetryInitialize();idleFrame=Time.frameCount;phase=8;return;
                    case 8:
                        if(Time.frameCount<=idleFrame+2)return;Check(!server.Ready&&server.AccountState=="closed","Deleted account does not auto-register another guest");settings.AccountView.Request("server-fresh");Check(!server.Ready,"Fresh guest warning is not registration");Capture("Fresh_Guest_Confirmation");settings.AccountView.Request("server-confirm-action");phase=9;return;
                    case 9:
                        if(server.Busy)return;Check(server.Ready&&server.PlayerId!=playerId&&server.Wallet.coins==1250&&server.Wallet.lives==5&&server.Wallet.starting[0]==5,"Explicit fresh guest gets its own genesis without old spent state");report.explicitFreshGuest=true;report.newPlayerIdHash=IdentityProtocol82.Sha(server.PlayerId);report.finalCoins=server.Wallet.coins;report.finalLives=server.Wallet.lives;Check(JsonUtility.ToJson(Field<ProfileStore>(profile,"store").Snapshot)==appearanceBefore,"Fresh guest leaves device appearance preferences unchanged");settings.AccountView.Request("dismiss");var restored=Field<CanvasGroup>(settings,"fade");Check(settings.IsVisible&&!settings.AccountView.IsVisible&&restored.alpha==1&&restored.blocksRaycasts&&Field<Canvas>(settings,"canvas").GetComponent<GraphicRaycaster>().enabled,"Closing Account returns to visible interactive Settings");report.settingsReturn=true;Finish();return;
                }
            }catch(Exception e){if(report==null)report=new Report();report.errors.Add("Stage"+phase+": "+e.GetType().Name+": "+e.Message);Finish();}
        }
        static void Finish(){
            if(finished)return;finished=true;EditorApplication.update-=Tick;recoveryCode=null;playerId=null;remoteClient?.Dispose();remoteIdentity?.Dispose();remoteTransport?.Dispose();remoteVault?.Dispose();GUIUtility.systemCopyBuffer=oldClipboard??"";try{RestorePortrait();}catch(Exception){report.errors.Add("PortraitRestoreFailed");}report.ordinaryProfilesAfter=ProfileDigest();if(report.ordinaryProfilesAfter!=report.ordinaryProfilesBefore)report.errors.Add("OrdinaryProfileBytesChanged");Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",SessionState.GetString(Key+".previousConfig","") is string previous&&previous.Length>0?previous:null);SessionState.EraseBool(Key);report.status=report.errors.Count==0?"PASS_NATIVE_SERVER_ACCOUNT83_CONNECTED_HTTP":"FAIL_NATIVE_SERVER_ACCOUNT83_CONNECTED_HTTP";Directory.CreateDirectory(Path.Combine(output,"Native"));File.WriteAllText(Path.Combine(output,"Native","AccountHTTP.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));if(Application.isBatchMode)EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif

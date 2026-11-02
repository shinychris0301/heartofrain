#if UNITY_EDITOR
using System;
using System.Collections;
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
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.ServerAccount;
using HeartOfTheRain.App.ServerGameplay;

namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class ServerAccount83Verification {
        const string Key="HOTR.ServerAccount83.Contracts";
        static ServerAccount83Verification(){if(SessionState.GetBool(Key,false))EditorApplication.update+=Tick;}
        public static void Run(){SessionState.SetBool(Key,true);EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorApplication.update-=Tick;EditorApplication.update+=Tick;EditorApplication.isPlaying=true;}
        static void Tick(){if(!EditorApplication.isPlaying||EditorApplication.isCompiling)return;EditorApplication.update-=Tick;SessionState.SetBool(Key,false);RunChecks();}
        [Serializable] sealed class Report{public string status,utc,unity,scope;public int checks,cases;public bool actualHttp=false,androidKeystore=false;public int copyCalls,clipboardReadbackLength=-1;public string copyScreen;public bool clipboardReadbackMatched;public List<string> passed=new List<string>(),errors=new List<string>();}
        static Report report;static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static void Check(bool ok,string label){report.checks++;if(!ok)throw new InvalidOperationException(label);}
        static void Reject(Action run,string label){bool threw=false;try{run();}catch(Exception){threw=true;}Check(threw,label);}
        static void Case(string label,Action run){report.cases++;try{run();report.passed.Add(label);}catch(Exception e){report.errors.Add(label+": "+e.GetType().Name+": "+e.Message);}}
        static string Temporary=>Path.GetFullPath("../.verification-cache/Launch82/ServerAccount83/Native/"+Guid.NewGuid().ToString("N")+".sealed");
        static string Id()=>Guid.NewGuid().ToString("N");
        sealed class ManagedFixture:IManagedServerAccount83 {
            // Passive fixture: state is set explicitly by each test; it emits no changes.
            public event Action Changed { add { } remove { } }public int copies,recoveries,anotherRecoveries,deletions,logouts,fresh;public string receivedCode;
            public readonly ServerAccountControls83 state=new ServerAccountControls83{ready=true,canCopyRecovery=true,playerId=new string('a',32)};
            public ServerAccountControls83 Controls=>state;
            public AccountStatus Read()=>new AccountStatus{managed=true,serverSaved=true,confirmedServerSaveUtc=100,playerId=state.playerId,online=true,sync=AccountSync.Synced};
            public void Link(string provider,Action<AccountLinkResult> done)=>done(AccountLinkResult.Failed);
            public void Refresh(Action<bool,string> done)=>done(true,null);
            public bool CopyRecovery(){copies++;GUIUtility.systemCopyBuffer=new string('A',43);return true;}
            public void Recover(string id,string code,bool confirmed,Action<bool,string> done){if(confirmed){recoveries++;receivedCode=code;}done(true,null);}
            public void StartAnotherRecovery(string id,string code,bool confirmed,Action<bool,string> done){if(confirmed)anotherRecoveries++;Recover(id,code,confirmed,done);}
            public void Logout(bool confirmed,Action<bool,string> done){if(confirmed)logouts++;done(true,null);}
            public void Delete(bool confirmed,Action<bool,string> done){if(confirmed)deletions++;done(true,null);}
            public void StartFresh(bool confirmed,Action<bool,string> done){if(confirmed)fresh++;done(true,null);}
            public void Resume(Action<bool,string> done)=>done(true,null);
            public void EndAttempt(bool confirmed,Action<bool,string> done)=>done(confirmed,null);
        }
        static void RunChecks(){
            report=new Report{utc=DateTime.UtcNow.ToString("O"),unity=Application.unityVersion,scope="Actual Editor encrypted selection CAS/crash cuts and AccountModal controls using an explicitly synthetic managed-service fixture. Verifies no provider-link claim, clipboard-only code, password masking and confirmation gates. Not HTTP, Android Keystore, real account deletion, or rendering certification."};
            Case("managed_guest_status_is_not_provider_link",()=>{var status=new AccountStatus{managed=true,serverSaved=true,confirmedServerSaveUtc=100,sync=AccountSync.Synced};Check(status.StatusKey=="serverSaved"&&status.EntryStatusKey=="serverSaved"&&!status.linked&&!status.CloudSaved,"server saved is distinct from linked provider");status.serverSaved=false;Check(status.StatusKey=="serverUnavailable","unconfirmed server save unavailable");});
            Case("encrypted_selector_reopens_fixed_pending_scope_and_id",()=>{
                using(var vault=new EditorEphemeralIdentity82()){
                    string path=Temporary;using(var selector=new AccountSelection83(new OriginBoundIdentityStore82(vault.CreateStore(path),"http://127.0.0.1:18383|selector"),"http://127.0.0.1:18383","review-base")){
                        var value=selector.Read();Check(value.currentScope=="review-base"&&!value.blocked,"default scope preserves existing explicit server identity");value.blocked=true;value.purpose="recover";value.pendingScope="review-next";value.requestId=Id();value.targetPlayer=new string('b',32);value=selector.Save(value);string id=value.requestId;
                        using(var reopened=new AccountSelection83(new OriginBoundIdentityStore82(vault.CreateStore(path),"http://127.0.0.1:18383|selector"),"http://127.0.0.1:18383","review-base")){var actual=reopened.Read();Check(actual.blocked&&actual.requestId==id&&actual.pendingScope=="review-next"&&actual.currentScope=="review-base","missing identity intent cannot become guest or switch fallback");}
                        using(var wrong=new AccountSelection83(new OriginBoundIdentityStore82(vault.CreateStore(path),"http://127.0.0.1:18384|selector"),"http://127.0.0.1:18384","review-base"))Reject(()=>wrong.Read(),"origin binding");
                        value.retainedRecoveryScopes=Enumerable.Repeat("review-old",9).ToArray();Reject(()=>selector.Save(value),"bounded retained private attempts");
                    }
                }
            });
            Case("encrypted_selector_pre_and_post_commit_cuts",()=>{
                using(var vault=new EditorEphemeralIdentity82()){
                    string path=Temporary;using(var selector=new AccountSelection83(vault.CreateStore(path),"https://server.example.org","review-base")){
                        var value=selector.Read();value.blocked=true;value.purpose="logout";value.requestId=Id();
                        vault.VerificationCheckpoint=stage=>{if(stage=="BeforeCommit")throw new IOException();};Reject(()=>selector.Save(value),"before commit cut");vault.VerificationCheckpoint=null;Check(!selector.Read().blocked,"no committed close before durable write");
                        value=selector.Read();value.blocked=true;value.purpose="logout";value.requestId=Id();vault.VerificationCheckpoint=stage=>{if(stage=="AfterCommit")throw new IOException();};Reject(()=>selector.Save(value),"after commit acknowledgement cut");vault.VerificationCheckpoint=null;Check(selector.Read().blocked&&selector.Read().purpose=="logout","committed close survives lost acknowledgement");
                    }
                }
            });
            Case("closed_gateway_never_automatically_creates_guest",()=>{
                var owner=new GameObject("Closed account policy fixture");try{var gateway=owner.AddComponent<ServerGameSession>();typeof(ServerGameSession).GetField("accountBlocked",Private).SetValue(gateway,true);bool done=false,ok=true;string why=null;
                    var routine=(IEnumerator)typeof(ServerGameSession).GetMethod("EnsureIdentity",Private).Invoke(gateway,new object[]{new Action<bool,string>((value,error)=>{done=true;ok=value;why=error;})});Check(!routine.MoveNext()&&done&&!ok&&why=="AccountSessionClosed","closed session blocks the automatic guest branch before transport");
                    typeof(ServerGameSession).GetField("accountSelection",Private).SetValue(gateway,new AccountSelectionState83{purpose="recover",pendingScope="review-pending",targetPlayer=new string('a',32),requestId=Id(),blocked=true});Check(!gateway.AccountRecoveryRequiresEntry&&gateway.AccountIdentityPending,"unopened encrypted recovery scope offers exact retry before asking for code");gateway.AccountStartFresh(false,(value,error)=>{ok=value;why=error;});Check(!ok&&why=="AccountConfirmationRequired","fresh guest requires explicit confirmation");
                }finally{UnityEngine.Object.DestroyImmediate(owner);}
            });
            Case("selector_lost_ack_requires_exact_successor_content",()=>{
                using(var vault=new EditorEphemeralIdentity82()){
                    string path=Temporary;using(var selector=new AccountSelection83(vault.CreateStore(path),"http://127.0.0.1:18383","review-base")){
                        var owner=new GameObject("Selector acknowledgement fixture");try{
                            var gateway=owner.AddComponent<ServerGameSession>();var value=selector.Read();value.blocked=true;value.purpose="logout";value.requestId=Id();
                            typeof(ServerGameSession).GetField("accountSelector",Private).SetValue(gateway,selector);typeof(ServerGameSession).GetField("accountSelection",Private).SetValue(gateway,value);
                            var save=typeof(ServerGameSession).GetMethod("SaveAccountSelection",Private);
                            vault.VerificationCheckpoint=stage=>{if(stage=="BeforeCommit")throw new IOException();};Reject(()=>save.Invoke(gateway,null),"before commit remains unconfirmed");vault.VerificationCheckpoint=null;
                            Check((bool)typeof(ServerGameSession).GetField("accountSelectionDirty",Private).GetValue(gateway)&&!(bool)typeof(ServerGameSession).GetField("accountSelectionConflict",Private).GetValue(gateway),"unchanged original selector remains retryable");
                            vault.VerificationCheckpoint=stage=>{if(stage=="AfterCommit")throw new IOException();};save.Invoke(gateway,null);vault.VerificationCheckpoint=null;
                            Check(!(bool)typeof(ServerGameSession).GetField("accountSelectionDirty",Private).GetValue(gateway),"exact committed lost acknowledgement proceeds");
                            value=(AccountSelectionState83)typeof(ServerGameSession).GetField("accountSelection",Private).GetValue(gateway);Check(value.revision==1&&value.purpose=="logout","adopt only own exact successor");
                            using(var other=new AccountSelection83(vault.CreateStore(path),"http://127.0.0.1:18383","review-base")){var foreign=other.Read();foreign.purpose="delete";foreign.requestId=Id();other.Save(foreign);}
                            value.purpose="closed";value.requestId="";Reject(()=>save.Invoke(gateway,null),"foreign newer selector cannot confirm old promotion");
                            Check((bool)typeof(ServerGameSession).GetField("accountSelectionConflict",Private).GetValue(gateway),"foreign content creates persistent fence");Reject(()=>save.Invoke(gateway,null),"retry cannot overwrite foreign selector after readback");Check(selector.Read().purpose=="delete","foreign explicit decision retained");
                        }finally{vault.VerificationCheckpoint=null;UnityEngine.Object.DestroyImmediate(owner);}
                    }
                }
            });
            Case("disposed_service_and_busy_recovery_cannot_dispatch",()=>{
                var owner=new GameObject("Disposed account policy fixture");try{
                    var gateway=owner.AddComponent<ServerGameSession>();typeof(ServerGameSession).GetField("busy",Private).SetValue(gateway,true);bool ok=true;string why=null;
                    gateway.AccountRecover(new string('a',32),new string('x',43),true,(value,error)=>{ok=value;why=error;});Check(!ok&&why=="AccountBusy","busy recovery blocked before coroutine or selector");
                    var service=new ServerAccountService83(gateway);service.Dispose();int callbacks=0;Action<bool,string> denied=(value,error)=>{Check(!value&&error=="AccountServiceClosed","disposed service denies action");callbacks++;};
                    service.Refresh(denied);service.Recover(new string('a',32),new string('x',43),true,denied);service.StartAnotherRecovery(new string('a',32),new string('x',43),true,denied);service.Logout(true,denied);service.Delete(true,denied);service.StartFresh(true,denied);service.Resume(denied);service.EndAttempt(true,denied);Check(callbacks==8&&!service.CopyRecovery()&&!service.Controls.ready,"all disposed service dispatch paths fenced");
                }finally{UnityEngine.Object.DestroyImmediate(owner);}
            });
            Case("recovered_attempt_decision_is_durable_and_id_scoped",()=>{
                using(var vault=new EditorEphemeralIdentity82()){
                    string path=Temporary;using(var selector=new AccountSelection83(vault.CreateStore(path),"http://127.0.0.1:18383","review-base")){
                        var value=selector.Read();value.recoveredAttemptDecision=true;value.recoveredAttemptId=Id();value=selector.Save(value);
                        using(var reopened=new AccountSelection83(vault.CreateStore(path),"http://127.0.0.1:18383","review-base"))Check(reopened.Read().recoveredAttemptId==value.recoveredAttemptId&&reopened.Read().recoveredAttemptDecision,"restart retains exact remote attempt decision");
                        var owner=new GameObject("Recovered remote attempt decision fixture");try{
                            var gateway=owner.AddComponent<ServerGameSession>();typeof(ServerGameSession).GetField("accountSelection",Private).SetValue(gateway,value);typeof(ServerGameSession).GetField("accountSelector",Private).SetValue(gateway,selector);
                            value.purpose="recover";value.pendingScope="review-next";value.targetPlayer=new string('b',32);value.requestId=Id();value.blocked=true;var prepare=typeof(ServerGameSession).GetMethod("PrepareRecoveredAttemptDecision",Private);prepare.Invoke(gateway,null);value.purpose="";value.requestId="";value.targetPlayer="";value.pendingScope="";value.currentScope="review-next";value.blocked=false;
                            vault.VerificationCheckpoint=stage=>{if(stage=="BeforeCommit")throw new IOException();};Reject(()=>typeof(ServerGameSession).GetMethod("SaveAccountSelection",Private).Invoke(gateway,null),"promotion selector precommit cut");vault.VerificationCheckpoint=null;prepare.Invoke(gateway,null);Check(value.recoveredAttemptDecision,"promotion retry after cleared purpose preserves remote decision");typeof(ServerGameSession).GetMethod("SaveAccountSelection",Private).Invoke(gateway,null);value=(AccountSelectionState83)typeof(ServerGameSession).GetField("accountSelection",Private).GetValue(gateway);Check(selector.Read().recoveredAttemptDecision,"promotion retry durably retains decision");value.recoveredAttemptId=Id();value=selector.Save(value);typeof(ServerGameSession).GetField("accountSelection",Private).SetValue(gateway,value);
                            var wallet=new HeartOfTheRain.App.RuStore.RuStoreServerWallet{lives=5,activeAttempt=new HeartOfTheRain.App.RuStore.RuStoreServerAttempt{attemptId=value.recoveredAttemptId,state="Started"}};typeof(ServerGameSession).GetField("wallet",Private).SetValue(gateway,wallet);var hold=typeof(ServerGameSession).GetProperty("HoldRecoveredAttemptDecision",Private);
                            Check((bool)hold.GetValue(gateway),"same remote attempt waits for explicit decision");wallet.activeAttempt.attemptId=Id();Check(!(bool)hold.GetValue(gateway),"decision cannot exempt a later ordinary attempt from interruption rule");wallet.activeAttempt=null;typeof(ServerGameSession).GetMethod("BindRecoveredAttemptDecision",Private).Invoke(gateway,null);Check(!selector.Read().recoveredAttemptDecision&&wallet.lives==5,"authenticated no-active projection clears decision without charging life");
                        }finally{UnityEngine.Object.DestroyImmediate(owner);}
                    }
                }
            });
            Case("approved_modal_code_is_clipboard_only_and_actions_are_confirmed",()=>{
                var prefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab");var owner=UnityEngine.Object.Instantiate(prefab);string oldClipboard=GUIUtility.systemCopyBuffer;
                try{
                    var home=owner.GetComponent<HomePage>();home.Build();var modal=owner.AddComponent<AccountModal>();modal.Configure(home,AccountDesignAssets.Load());var service=new ManagedFixture();int dismissals=0;modal.Dismissed+=()=>dismissals++;
                    Check(modal.Show(service)&&modal.ScreenKey=="server","managed account uses separate truthful server branch");Check(!owner.GetComponentsInChildren<Button>(true).Any(b=>b.name=="Provider Google"||b.name=="Provider Apple"),"no linked-provider buttons in server guest state");
                    modal.Request("server-copy-code");Check(service.copies==0,"clipboard Copy requires warning screen");modal.Request("server-backup");modal.Request("server-copy-code");
                    report.copyCalls=service.copies;report.copyScreen=(string)typeof(AccountModal).GetField("serverScreen",Private).GetValue(modal);
                    // Redacted diagnostics only: never serialize clipboard bytes,
                    // its previous contents, a recovery code or a digest of it.
                    string readback=GUIUtility.systemCopyBuffer;report.clipboardReadbackLength=readback?.Length??0;report.clipboardReadbackMatched=readback==new string('A',43);readback=null;
                    Check(report.copyCalls==1,"explicit Copy invokes service exactly once");Check(report.copyScreen=="backup","explicit Copy retains warning screen");Check(report.clipboardReadbackMatched,"explicit Copy real clipboard readback matches");Check(!owner.GetComponentsInChildren<Text>(true).Any(t=>t.text.Contains(new string('A',43))),"code never rendered");
                    modal.Request("server-recover");var id=(InputField)typeof(AccountModal).GetField("recoveryPlayerInput",Private).GetValue(modal);var code=(InputField)typeof(AccountModal).GetField("recoveryCodeInput",Private).GetValue(modal);id.text=new string('b',32);code.text=new string('B',42)+"A";Check(code.contentType==InputField.ContentType.Password,"recovery entry is masked");modal.Request("server-confirm-switch");Check(service.recoveries==0,"switch cannot dispatch before its confirmation screen");modal.Request("server-review-switch");Check((string)typeof(AccountModal).GetField("serverScreen",Private).GetValue(modal)=="switchConfirm","canonical code reaches actual switch warning");Check(service.recoveries==0,"review does not switch account");modal.Request("server-confirm-switch");Check(service.recoveries==1&&service.receivedCode==new string('B',42)+"A","explicit switch forwards only memory input");
                    modal.Request("server-delete");modal.Request("server-delete-next");Check(service.deletions==0,"first delete confirmation has no effect");modal.Request("server-delete-next");Check(service.deletions==1,"second delete confirmation invokes service once");
                    modal.Hide(false);service.state.ready=false;service.state.blocked=true;service.state.pending=true;service.state.canRestartRecovery=true;service.state.recoveryTarget=new string('b',32);Check(modal.Show(service),"reopen explicit rejected-recovery fixture");
                    Check(owner.GetComponentsInChildren<Button>().Any(b=>b.name=="Use another recovery code"&&b.interactable),"confirmed rejection exposes different-code action");Check(owner.GetComponentsInChildren<Button>().Any(b=>b.name=="Resume server account"&&b.interactable),"exact pending retry remains available");
                    modal.Request("server-recover");((InputField)typeof(AccountModal).GetField("recoveryPlayerInput",Private).GetValue(modal)).text=new string('b',32);((InputField)typeof(AccountModal).GetField("recoveryCodeInput",Private).GetValue(modal)).text=new string('B',42)+"A";modal.Request("server-review-switch");Check(service.anotherRecoveries==0,"retained-intent warning does not create a new request");modal.Request("server-confirm-switch");Check(service.anotherRecoveries==1,"explicit confirmation dispatches another recovery only after service permission");
                    foreach(var button in owner.GetComponentsInChildren<Button>(true)){var image=button.targetGraphic as Image;if(image&&image.sprite&&button.GetComponent<RectTransform>().rect.height==46&&button.name!="Account close")Check(Mathf.Abs(image.pixelsPerUnitMultiplier-13.33f)<.001f,"46-high primary slice retained");}
                    modal.Hide();modal.Hide();Check(dismissals==1,"one dismissal returns to settings");Check((string)typeof(AccountModal).GetField("recoveryEntry",Private).GetValue(modal)=="","masked memory entry cleared on close");
                }finally{GUIUtility.systemCopyBuffer=oldClipboard;UnityEngine.Object.DestroyImmediate(owner);}
            });
            report.status=report.errors.Count==0?"PASS_NATIVE_SERVER_ACCOUNT83_CONTRACTS":"FAIL_NATIVE_SERVER_ACCOUNT83_CONTRACTS";string root=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_OUTPUT")??"../Verification/Evidence/ServerGameplay83");Directory.CreateDirectory(Path.Combine(root,"Native"));File.WriteAllText(Path.Combine(root,"Native","AccountContracts.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));if(Application.isBatchMode)EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif

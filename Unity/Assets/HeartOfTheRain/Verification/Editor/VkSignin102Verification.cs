#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Reflection;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using HeartOfTheRain.App.AccountDesign;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.ServerAccount;
using HeartOfTheRain.App.ServerGameplay;

namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class VkSignin102Verification {
        const string Key="HOTR.VkSignin102.Native";const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static readonly string Player=new string('a',32),Target=new string('b',32),Flow=new string('c',32),Family=new string('d',32);
        [Serializable] sealed class Report {
            public string status,utc,unity,scope="Actual Editor PlayMode UGUI, Windows CNG P256 and isolated encrypted/CAS storage with explicit simulated protocol/service responses. No real HTTP/VK account/Android/native SDK/browser/provider acceptance or ordinary profile changes.";
            public int checks,cases,layouts;public List<string> failures=new List<string>(),engineErrors=new List<string>(),captures=new List<string>();
        }
        sealed class Bytes {public byte[] value;public bool failBefore,failAfter,failRead;}
        sealed class Store:IProtectedSessionStore82 {
            readonly Bytes bytes;public Store(Bytes bytes){this.bytes=bytes;}public byte[] Read(){if(bytes.failRead)throw new IOException("FixtureProtectedReadUnavailable");return bytes.value==null?null:(byte[])bytes.value.Clone();}
            public void CompareExchange(string expected,byte[] next){if(bytes.failBefore)throw new IOException("FixtureBeforeCommit");if(expected!=(bytes.value==null?"":IdentityProtocol82.Sha(bytes.value)))throw new InvalidOperationException("FixtureCASConflict");bytes.value=(byte[])next.Clone();if(bytes.failAfter)throw new IOException("FixtureAfterCommit");}
            public void Dispose(){}
        }
        sealed class Transport:IIdentityTransport82,IVkIdentityTransport102 {
            readonly EditorEphemeralIdentity82 vault;public IdentityChallenge82 challenge;public bool loseReply,wrongTarget,duplicate;public int calls,commits;bool committed;
            public Transport(EditorEphemeralIdentity82 vault){this.vault=vault;}
            public void Challenge(IdentityChallengeRequest82 request,Action<IdentityReply82<IdentityChallenge82>> done){
                challenge=new IdentityChallenge82{purpose=request.purpose,requestId=request.requestId,keyFingerprint=IdentityProtocol82.Fingerprint(request.publicKey),payloadDigest=request.payloadDigest,challengeId=Guid.NewGuid().ToString("N"),nonce=IdentityProtocol82.NewSecret(),algorithm="ES256-DER",serverUtc=100,expiresAt=160};
                string json="{\"challengeId\":\""+challenge.challengeId+"\",\"expiresAt\":160,\"keyFingerprint\":\""+challenge.keyFingerprint+"\",\"nonce\":\""+challenge.nonce+"\",\"payloadDigest\":\""+challenge.payloadDigest+"\",\"purpose\":\""+challenge.purpose+"\",\"requestId\":\""+challenge.requestId+"\"}";
                challenge.signingBytes=Convert.ToBase64String(Encoding.ASCII.GetBytes(IdentityProtocol82.Protocol+"\n"+json));done(IdentityReply82<IdentityChallenge82>.Ok(challenge));if(duplicate)done(IdentityReply82<IdentityChallenge82>.Ok(challenge));
            }
            public void SubmitVk(VkCompletionIntent102 intent,string challengeId,string signature,Action<IdentityReply82<IdentitySessionResponse82>> done){
                calls++;Check(challengeId==challenge.challengeId&&vault.Verify(Convert.FromBase64String(challenge.signingBytes),Convert.FromBase64String(signature)),"Actual CNG VK proof signature verifies");
                if(!committed){commits++;committed=true;}
                if(loseReply){loseReply=false;done(IdentityReply82<IdentitySessionResponse82>.Fail("FixtureLostReply",true));return;}
                var reply=new IdentitySessionResponse82{playerId=wrongTarget?Player:intent.targetPlayerId,familyId=Family,keyFingerprint=IdentityProtocol82.Fingerprint(intent.publicKey),accessToken=IdentityProtocol82.NewSecret(),requestId=intent.requestId,accountState="Active",expiresAt=1000,refreshExpiresAt=5000};
                done(IdentityReply82<IdentitySessionResponse82>.Ok(reply));if(duplicate)done(IdentityReply82<IdentitySessionResponse82>.Ok(reply));
            }
            public void Submit(IdentityIntent82 intent,string challengeId,string signature,Action<IdentityReply82<IdentitySessionResponse82>> done){
                Check(intent.purpose=="session","Provider-created scope can use ordinary identity refresh");
                done(IdentityReply82<IdentitySessionResponse82>.Ok(new IdentitySessionResponse82{playerId=Target,familyId=Family,keyFingerprint=IdentityProtocol82.Fingerprint(intent.publicKey),accessToken=IdentityProtocol82.NewSecret(),requestId=intent.requestId,accountState="Active",expiresAt=1000,refreshExpiresAt=5000}));
            }
            public void Cancel(){}
        }
        sealed class Managed:IManagedServerAccount83,IProviderAccount89,IProviderSignin102 {
            public event Action Changed{add{}remove{}}
            public bool available=true;public VkSigninStatus102 signin;public int begun,finished,cancelled,checkedStatus,legacy;public string receivedTarget;public bool confirmed;
            public ProviderStatus89 VkStatus=>new ProviderStatus89{available=available,playerId=Player,provider="vk",samePlayer=true,phase="Idle",serverUtc=100};
            public bool ProviderBusy=>false;public VkSigninStatus102 VkSignin=>signin?.Copy();
            public ServerAccountControls83 Controls=>new ServerAccountControls83{ready=signin?.phase!="Committing",blocked=signin?.phase=="Committing",pending=signin?.phase=="Committing",purpose=signin?.phase=="Committing"?"vk":"",playerId=Player,canCopyRecovery=false};
            public AccountStatus Read()=>new AccountStatus{managed=true,serverSaved=Controls.ready,confirmedServerSaveUtc=Controls.ready?100:0,playerId=Player,online=true,sync=Controls.ready?AccountSync.Synced:AccountSync.Failed};
            public void Link(string p,Action<AccountLinkResult> done)=>throw new InvalidOperationException("No real provider in UI fixture");
            public void RefreshProviders(){}public void BeginVk(Action<bool,string> done){legacy++;done(false,"Legacy");}public void CancelVk(Action<bool,string> done){legacy++;done(false,"Legacy");}
            public void BeginVkSignin(Action<bool,string> done){begun++;done(true,null);}public void RefreshVkSignin(Action<bool,string> done){checkedStatus++;done(true,null);}public void CancelVkSignin(Action<bool,string> done){cancelled++;done(true,null);}
            public void CompleteVkSignin(string target,bool consent,Action<bool,string> done){finished++;receivedTarget=target;confirmed=consent;done(target==signin.targetPlayerId&&consent,null);}
            public void Refresh(Action<bool,string> done)=>done(true,null);public bool CopyRecovery()=>false;
            public void Recover(string id,string code,bool yes,Action<bool,string> done)=>done(false,"Unused");public void StartAnotherRecovery(string id,string code,bool yes,Action<bool,string> done)=>done(false,"Unused");
            public void Logout(bool yes,Action<bool,string> done)=>done(false,"Unused");public void Delete(bool yes,Action<bool,string> done)=>done(false,"Unused");public void StartFresh(bool yes,Action<bool,string> done)=>done(false,"Unused");public void Resume(Action<bool,string> done)=>done(false,"Unused");public void EndAttempt(bool yes,Action<bool,string> done)=>done(false,"Unused");
        }
        static Report report;static string output;static double began;static int previousLocale;static bool ran;
        static object Group(){var asm=typeof(Editor).Assembly;var type=asm.GetType("UnityEditor.GameViewSizes");var singleton=typeof(ScriptableSingleton<>).MakeGenericType(type).GetProperty("instance",BindingFlags.Static|BindingFlags.Public).GetValue(null);string group=EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android?"Android":EditorUserBuildSettings.activeBuildTarget==BuildTarget.iOS?"iOS":"Standalone";return type.GetMethod("GetGroup").Invoke(singleton,new[]{Enum.Parse(asm.GetType("UnityEditor.GameViewSizeGroupType"),group)});}
        static EditorWindow View()=>EditorWindow.GetWindow(typeof(Editor).Assembly.GetType("UnityEditor.GameView"));
        static void Size(){var group=Group();var view=View();var property=view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic);SessionState.SetInt(Key+".previous",(int)property.GetValue(view));int count=(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null);SessionState.SetInt(Key+".custom",count);var asm=typeof(Editor).Assembly;var size=Activator.CreateInstance(asm.GetType("UnityEditor.GameViewSize"),BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance,null,new object[]{Enum.Parse(asm.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),720,1600,"HOTR VK102"},null);group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{size});property.SetValue(view,count);view.Repaint();}
        static void RestoreSize(){try{var view=View();view.GetType().GetProperty("selectedSizeIndex",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).SetValue(view,SessionState.GetInt(Key+".previous",0));Group().GetType().GetMethod("RemoveCustomSize").Invoke(Group(),new object[]{SessionState.GetInt(Key+".custom",0)});}catch(Exception e){report.engineErrors.Add("Size cleanup: "+e.GetType().Name);}}
        static VkSignin102Verification(){if(SessionState.GetBool(Key,false)){report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};output=Environment.GetEnvironmentVariable("HOTR_REVIEW102_OUT")??Path.GetFullPath("../Verification/Evidence/Review102");Directory.CreateDirectory(Path.Combine(output,"Native","VkSignin102"));began=EditorApplication.timeSinceStartup;previousLocale=GameLocale.Current;EditorApplication.update+=Tick;Application.logMessageReceived+=Log;}}
        public static void Run(){SessionState.SetBool(Key,true);Size();EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorApplication.isPlaying=true;}
        static void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.engineErrors.Add(text+"\n"+stack);}
        static void Check(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);}
        static void Reject(Action action,string label){bool rejected=false;try{action();}catch(Exception){rejected=true;}Check(rejected,label);}
        static void Case(string name,Action run){report.cases++;try{run();}catch(Exception e){report.failures.Add(name+": "+e);}}
        static VkSigninDocument102 Prepared()=>new VkSigninDocument102{origin="https://account.example.org",sourceScope="review-source",pendingScope="review-vk-next",sourcePlayerId=Player,requestId=Flow,flowSecret=IdentityProtocol82.NewSecret(),refreshToken=IdentityProtocol82.NewSecret(),phase="Prepared"};
        static void Tick(){
            if(!EditorApplication.isPlaying||EditorApplication.isCompiling){if(EditorApplication.timeSinceStartup-began>180)Finish();return;}if(ran)return;ran=true;
            Case("Flow parser rejects cross-owner, target and malformed booleans",()=>{
                var value=new VkSigninStatus102{playerId=Player,provider="vk",available=true,phase="Ready",flowId=Flow,requestId=Flow,serverUtc=100,expiresAt=700,targetPlayerId=Target,requiresConfirmation=true};string json=JsonUtility.ToJson(value);
                Check(VkSigninClient102.Parse(json,Player,Flow).targetPlayerId==Target,"Ready target parsed");
                foreach(string bad in new[]{json.Replace(Player,new string('e',32)),json.Replace("\"requiresConfirmation\":true","\"requiresConfirmation\":false"),json.Replace("\"available\":true","\"available\":\"true\""),json.Replace("\"available\":true","\"available\":true,\"available\":false"),json.Replace("\"targetPlayerId\":\""+Target+"\"","\"targetPlayerId\":\"\""),json.Replace("\"expiresAt\":700","\"expiresAt\":100")})Reject(()=>VkSigninClient102.Parse(bad,Player,Flow),"Unbound status rejected");
                foreach(string phase in new[]{"Cancelled","Expired"}){value.phase=phase;value.targetPlayerId="";value.requiresConfirmation=false;Check(VkSigninClient102.Parse(JsonUtility.ToJson(value),Player,Flow).Terminal,"Ready-to-terminal response hides target");value.targetPlayerId=Target;Reject(()=>VkSigninClient102.Parse(JsonUtility.ToJson(value),Player,Flow),"Terminal target cannot leak or strand parser");}
                Check(!ProviderIdentityClient89.SafeAuthorizeUrl("https://id.vk.com.evil.example/authorize"),"Foreign browser origin rejected");
            });
            Case("Durable encrypted flow and writer-conflict retry fences",()=>{
                var bytes=new Bytes();using(var first=new VkSigninJournal102(new Store(bytes),"https://account.example.org"))using(var second=new VkSigninJournal102(new Store(bytes),"https://account.example.org")){
                    first.Read();second.Read();var a=first.Save(Prepared());var stale=Prepared();Reject(()=>second.Save(stale),"Stale first CAS fails");Reject(()=>second.Save(stale),"Failed readback cannot upgrade stale writer to winning digest");Check(first.Read().requestId==a.requestId,"Winning proof retained");
                    second.Read();Reject(()=>second.Save(stale),"Explicit newer read rejects old revision too");
                    a=first.Read();a.phase="Ready";a.targetPlayerId=Target;bytes.failBefore=true;Reject(()=>first.Save(a),"Before-commit proof cut retains prior state");bytes.failBefore=false;Check(first.Read().phase=="Prepared","No phantom Ready after failed write");
                    a=first.Read();a.phase="Ready";a.targetPlayerId=Target;bytes.failAfter=true;var committed=first.Save(a);bytes.failAfter=false;Check(committed.phase=="Ready"&&first.Read().targetPlayerId==Target,"Exact after-commit readback confirms once");
                    bytes.value=Encoding.UTF8.GetBytes("{}");Reject(()=>first.Read(),"Corrupt flow never becomes fresh guest");
                }
                using(var vault=new EditorEphemeralIdentity82()){
                    string path=Path.GetFullPath("../.verification-cache/Launch82/Vk102/"+Guid.NewGuid().ToString("N")+".sealed");var state=Prepared();using(var store=new VkSigninJournal102(vault.CreateStore(path),state.origin)){store.Read();store.Save(state);}
                    Check(!Encoding.UTF8.GetString(File.ReadAllBytes(path)).Contains(state.flowSecret),"Actual encrypted file does not expose flow proof");
                    using(var reopened=new VkSigninJournal102(vault.CreateStore(path),state.origin))Check(reopened.Read().flowSecret==state.flowSecret,"Actual encrypted proof survives reopen");
                }
            });
            Case("Signed completion retry, exact target and no recovery rotation",()=>{
                using(var vault=new EditorEphemeralIdentity82()){
                    string path=Path.GetFullPath("../.verification-cache/Launch82/Vk102/"+Guid.NewGuid().ToString("N")+".sealed");
                    var transport=new Transport(vault){loseReply=true,duplicate=true};var manager=new ManagedIdentitySession82(vault.CreateKey(),vault.CreateStore(path),transport);
                    try{
                        var intent=Prepared();intent.phase="Committing";intent.targetPlayerId=Target;var completion=intent.Completion(manager.DevicePublicKey);string digest=VkSigninProtocol102.PayloadDigest(completion);var changed=completion.Copy();changed.targetPlayerId=Player;Check(VkSigninProtocol102.PayloadDigest(changed)!=digest,"Displayed target is in signed digest");changed=completion.Copy();changed.confirmed=false;Reject(()=>VkSigninProtocol102.PayloadDigest(changed),"Unconfirmed completion cannot be signed");
                        IdentityReply82<IdentityView82> reply=null;manager.CompleteVk(completion,"",r=>reply=r);Check(reply!=null&&!reply.Succeeded&&!manager.View.hasSession,"Lost reply does not invent local credentials");
                        manager.Dispose();manager=new ManagedIdentitySession82(vault.CreateKey(),vault.CreateStore(path),transport);reply=null;manager.CompleteVk(completion,"",r=>reply=r);Check(reply!=null&&reply.Succeeded&&manager.View.playerId==Target&&transport.commits==1,"Exact retried completion promotes one simulated session");
                        Check(!manager.HasRecoveryBackup&&manager.RecoverySecretForExplicitBackup()=="","Existing owner's unknown recovery code is not rotated or fabricated");
                        string canonical=Encoding.UTF8.GetString(vault.CreateStore(path).Read());Check(!canonical.Contains("flowId")&&!canonical.Contains("targetPlayerId"),"Existing v1 credential JSON gains no new serialized fields");
                        reply=null;manager.Refresh(Guid.NewGuid().ToString("N"),r=>reply=r);Check(reply!=null&&reply.Succeeded&&!manager.HasRecoveryBackup,"Empty provider backup remains valid through normal refresh");
                        manager.Dispose();using(var storage=vault.CreateStore(path)){
                            byte[] valid=storage.Read();string raw=Encoding.UTF8.GetString(valid);byte[] malformed=Encoding.UTF8.GetBytes(raw.Replace("\"recoverySecret\":\"\"","\"recoverySecret\":null"));
                            storage.CompareExchange(IdentityProtocol82.Sha(valid),malformed);Reject(()=>new ManagedIdentitySession82(vault.CreateKey(),vault.CreateStore(path),transport),"Null recovery backup remains invalid; only exact empty string is allowed");storage.CompareExchange(IdentityProtocol82.Sha(malformed),valid);
                            using(var reopened=new ManagedIdentitySession82(vault.CreateKey(),vault.CreateStore(path),transport))Check(reopened.View.playerId==Target&&!reopened.HasRecoveryBackup,"Canonical v1 provider credential reopens after refresh");
                        }
                    }finally{manager.Dispose();}
                }
                using(var vault=new EditorEphemeralIdentity82()){
                    var bytes=new Bytes();var transport=new Transport(vault){wrongTarget=true};using(var manager=new ManagedIdentitySession82(vault.CreateKey(),new Store(bytes),transport)){
                        var state=Prepared();state.phase="Committing";state.targetPlayerId=Target;IdentityReply82<IdentityView82> reply=null;manager.CompleteVk(state.Completion(manager.DevicePublicKey),"",r=>reply=r);Check(reply!=null&&!reply.Succeeded&&!manager.View.hasSession&&bytes.value==null,"Wrong target response never publishes credentials");
                    }
                }
            });
            Case("Protected pending reads fail closably and recover without losing intent",()=>{
                using(var vault=new EditorEphemeralIdentity82()){
                    var bytes=new Bytes();var transport=new Transport(vault);var manager=new ManagedIdentitySession82(vault.CreateKey(),new Store(bytes),transport);var node=new GameObject("VK102 protected read failure fixture");
                    try{
                        var gateway=node.AddComponent<ServerGameSession>();var value=Prepared();value.phase="Committing";value.targetPlayerId=Target;var selection=new AccountSelectionState83{purpose="vk",blocked=true,requestId=value.requestId,currentScope=value.sourceScope,pendingScope=value.pendingScope,targetPlayer=Target};
                        typeof(ServerGameSession).GetField("pendingIdentity",Private).SetValue(gateway,manager);typeof(ServerGameSession).GetField("accountBlocked",Private).SetValue(gateway,true);typeof(ServerGameSession).GetField("accountSelection",Private).SetValue(gateway,selection);typeof(ServerGameSession).GetField("vkDocument",Private).SetValue(gateway,value);typeof(ServerGameSession).GetField("busy",Private).SetValue(gateway,true);
                        string proof=value.flowSecret;bytes.failRead=true;int callbacks=0;string error=null;Action<bool,string> done=(ok,why)=>{Check(!ok,"Unavailable protected read never reports success");callbacks++;error=why;};
                        Check(gateway.AccountIdentityPending,"Durable pending selector does not dereference temporarily unreadable credentials");
                        object[] arguments={false,done};bool read=(bool)typeof(ServerGameSession).GetMethod("TryReadVkPendingSession",Private).Invoke(gateway,arguments);
                        Check(!read&&!gateway.Busy&&callbacks==1&&error=="VkProtectedReadUnconfirmed","Protected read failure releases busy and delivers typed retryable failure");
                        Check(gateway.AccountBlocked&&gateway.AccountIdentityPending&&value.phase=="Committing"&&value.flowSecret==proof&&selection.requestId==value.requestId,"Failure preserves exact blocked intent instead of rolling back or starting a guest");
                        bytes.failRead=false;typeof(ServerGameSession).GetField("busy",Private).SetValue(gateway,true);callbacks=0;arguments=new object[]{false,done};read=(bool)typeof(ServerGameSession).GetMethod("TryReadVkPendingSession",Private).Invoke(gateway,arguments);
                        Check(read&&!(bool)arguments[0]&&callbacks==0&&gateway.Busy&&value.flowSecret==proof,"Recovered storage lets the same pending operation continue without a new intent");
                    }finally{bytes.failRead=false;UnityEngine.Object.DestroyImmediate(node);manager.Dispose();}
                }
            });
            Case("Terminal reconciliation cannot clear another durable selector",()=>{
                var value=Prepared();value.phase="Committing";value.targetPlayerId=Target;var selection=new AccountSelectionState83{purpose="vk",blocked=true,currentScope=value.sourceScope,pendingScope=value.pendingScope,requestId=value.requestId,targetPlayer=Target};
                Check(VkSigninProtocol102.OwnsSelection(value,selection),"Exact confirmed selector owns its flow");
                selection.requestId=new string('e',32);Check(!VkSigninProtocol102.OwnsSelection(value,selection),"Another pending request cannot be rolled back");selection.requestId=value.requestId;
                selection.pendingScope="review-foreign";Check(!VkSigninProtocol102.OwnsSelection(value,selection),"Another pending key scope cannot be rolled back");selection.pendingScope=value.pendingScope;
                selection.targetPlayer=Player;Check(!VkSigninProtocol102.OwnsSelection(value,selection),"Another confirmed target cannot be rolled back");selection.targetPlayer=Target;
                value.phase="Expired";value.targetPlayerId="";Check(VkSigninProtocol102.OwnsSelection(value,selection),"Own cleared terminal journal can finish selector rollback after a cut");selection.requestId=new string('e',32);Check(!VkSigninProtocol102.OwnsSelection(value,selection),"Cleared terminal journal still cannot clear another request");
            });
            Case("Completed provider presentation remains owned by exact journey scope",()=>{
                using(var vault=new EditorEphemeralIdentity82()){
                    var transport=new Transport(vault);var bytes=new Bytes();var manager=new ManagedIdentitySession82(vault.CreateKey(),new Store(bytes),transport);var node=new GameObject("VK102 presentation owner fixture");
                    try{
                        var value=Prepared();value.phase="Committing";value.targetPlayerId=Target;IdentityReply82<IdentityView82> reply=null;manager.CompleteVk(value.Completion(manager.DevicePublicKey),"",r=>reply=r);Check(reply!=null&&reply.Succeeded,"Owned presentation fixture has real protected VK successor");value.phase="Completed";value.flowSecret=value.refreshToken="";
                        var gateway=node.AddComponent<ServerGameSession>();typeof(ServerGameSession).GetField("identity",Private).SetValue(gateway,manager);typeof(ServerGameSession).GetField("vkDocument",Private).SetValue(gateway,value);typeof(ServerGameSession).GetField("vkSigninStatus",Private).SetValue(gateway,new VkSigninStatus102{phase="Completed",targetPlayerId=Target});
                        var selection=new AccountSelectionState83{currentScope=value.pendingScope,purpose=""};typeof(ServerGameSession).GetField("accountSelection",Private).SetValue(gateway,selection);
                        Check(gateway.AccountVkStatus!=null,"Exact promoted scope sees its linked status");selection.currentScope="review-other";Check(gateway.AccountVkStatus==null,"Same-player recovery into another scope cannot reuse old provider presentation");selection.currentScope=value.pendingScope;selection.purpose="logout";Check(gateway.AccountVkStatus==null,"Logout/closed transition hides prior linked presentation");selection.purpose="recover";Check(gateway.AccountVkStatus==null,"Pending recovery cannot show previous account's provider status");
                    }finally{UnityEngine.Object.DestroyImmediate(node);manager.Dispose();}
                }
            });
            foreach(int locale in new[]{0,1,2,3,4})foreach(string phase in new[]{"Unavailable","Idle","Pending","Exchanging","ReadySame","ReadyOther","Completed","Cancelled","Committing"}){int language=locale;string state=phase;Case("VK UGUI "+state+" "+language,()=>Ui(language,state));}
            Finish();
        }
        static void Ui(int locale,string phase){
            GameLocale.Select(locale);GameObject owner=null,eventOwner=null;
            try{
                owner=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab"));var home=owner.GetComponent<HomePage>();home.enabled=false;if(!EventSystem.current)eventOwner=new GameObject("VK102 test EventSystem",typeof(EventSystem));
                var fixture=new Managed{available=phase!="Unavailable"};if(phase!="Unavailable"&&phase!="Idle")fixture.signin=new VkSigninStatus102{playerId=Player,provider="vk",available=true,phase=phase.StartsWith("Ready",StringComparison.Ordinal)?"Ready":phase,targetPlayerId=phase=="ReadySame"?Player:phase=="ReadyOther"||phase=="Completed"?Target:"",requiresConfirmation=phase=="ReadyOther",flowId=Flow,requestId=Flow,expiresAt=700,serverUtc=100};
                var modal=owner.AddComponent<AccountModal>();modal.Configure(home,AccountDesignAssets.Load());Check(modal.Show(fixture),"Existing approved account modal opens");Canvas.ForceUpdateCanvases();
                var canvas=(Canvas)typeof(AccountModal).GetField("canvas",Private).GetValue(modal);var buttons=canvas.GetComponentsInChildren<Button>().Where(b=>b.gameObject.activeInHierarchy).ToArray();var begin=buttons.Single(b=>b.name=="VK registration or sign in");
                Check(begin.interactable==(phase=="Idle"||phase=="Completed"||phase=="Cancelled"),"VK begin follows availability and flow state");Check(!buttons.Any(b=>b.name=="Server provider Google"),"Unsupported Google sign-in is hidden");Check(!canvas.GetComponentsInChildren<Text>().Any(t=>t.text.Contains("Google")),"Managed modal has no Google sign-in copy");
                Check(canvas.GetComponentsInChildren<Text>().Any(t=>t.text.Contains("VK")),"VK text available in supported locale");
                var body=(RectTransform)typeof(AccountModal).GetField("body",Private).GetValue(modal);var viewport=(RectTransform)typeof(AccountModal).GetField("viewport",Private).GetValue(modal);Check(viewport.GetComponent<RectMask2D>()&&viewport.GetComponent<ScrollRect>().vertical,"Account content stays masked and scrollable");
                foreach(var button in buttons.Where(b=>b.transform.parent==body))Check(((RectTransform)button.transform).rect.width<=body.rect.width+.01f,"VK button contained in body");
                var footer=(RectTransform)typeof(AccountModal).GetField("footer",Private).GetValue(modal);var panel=(RectTransform)typeof(AccountModal).GetField("panel",Private).GetValue(modal);
                if(phase.StartsWith("Ready",StringComparison.Ordinal)||phase=="Committing"){
                    var action=buttons.Single(b=>b.name==(phase=="Committing"?"Resume confirmed VK sign in":"Confirm VK saved game"));
                    Check(action.transform.parent==footer,"The meaningful VK action is pinned in the existing footer");
                    Check(Inside((RectTransform)action.transform,footer)&&Inside((RectTransform)action.transform,panel),"Rendered footer action stays inside footer and panel bounds");
                    var fc=new Vector3[4];var vc=new Vector3[4];footer.GetWorldCorners(fc);viewport.GetWorldCorners(vc);Check(fc.Max(p=>p.y)<=vc.Min(p=>p.y)+.01f,"Pinned action stays below the masked scrolling viewport");
                    Check(!buttons.Any(b=>b.name=="Account return"),"Generic closing Continue cannot replace VK confirmation or pending Resume");
                    Check(action.GetComponent<HomeControlLabel>().action==(phase=="Committing"?"server-resume":"vk102-complete"),"Pinned action has the exact authentication command");
                }
                if(locale==4&&(phase=="Idle"||phase=="ReadySame"||phase=="ReadyOther"||phase=="Completed"))Capture(canvas,"VK_"+phase+"_ru.png");
                if(phase=="Idle"){begin.onClick.Invoke();Check(fixture.begun==1&&fixture.legacy==0&&!modal.IsBusy,"Actual UGUI routes signup to new authentication service");}
                if(phase=="ReadyOther"){
                    modal.Request("server-backup");Canvas.ForceUpdateCanvases();var backup=canvas.GetComponentsInChildren<Button>().Where(b=>b.gameObject.activeInHierarchy).ToArray();
                    Check(backup.Any(b=>b.name=="Account return")&&!backup.Any(b=>b.name=="Confirm VK saved game"),"Backup subpage keeps ordinary Continue and cannot hide a VK confirmation");modal.Request("vk102-complete");Check(fixture.finished==0,"Hidden VK callback on a subpage has no captured target");
                    modal.Request("server-refresh");Canvas.ForceUpdateCanvases();var finish=canvas.GetComponentsInChildren<Button>().Single(b=>b.gameObject.activeInHierarchy&&b.name=="Confirm VK saved game");fixture.signin.targetPlayerId=new string('e',32);finish.onClick.Invoke();Check(fixture.finished==1&&fixture.receivedTarget==Target&&fixture.confirmed,"Confirmation binds target displayed before later status changed");
                }
                if(phase=="Pending"){buttons.Single(b=>b.name=="Cancel VK sign in").onClick.Invoke();Check(fixture.cancelled==1&&fixture.legacy==0,"Actual cancel uses signup flow service");}
                if(phase=="Committing")Check(buttons.Any(b=>b.GetComponent<HomeControlLabel>()?.action=="server-resume"),"Confirmed pending sign-in keeps the existing Resume action available");
                if(phase=="Unavailable"){modal.Request("VK");Check(fixture.begun==0&&!modal.Snapshot.linked,"Local/unconfigured mode cannot fabricate VK signup");}
                report.layouts++;
            }finally{if(owner)UnityEngine.Object.DestroyImmediate(owner);if(eventOwner)UnityEngine.Object.DestroyImmediate(eventOwner);}
        }
        static bool Inside(RectTransform inner,RectTransform outer){var corners=new Vector3[4];inner.GetWorldCorners(corners);foreach(var corner in corners){Vector3 point=outer.InverseTransformPoint(corner);if(point.x<outer.rect.xMin-.01f||point.x>outer.rect.xMax+.01f||point.y<outer.rect.yMin-.01f||point.y>outer.rect.yMax+.01f)return false;}return true;}
        static void Capture(Canvas canvas,string filename){
            var root=new GameObject("VK102 UI capture");var camera=root.AddComponent<Camera>();camera.enabled=false;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.02f,.07f,.15f,1);camera.transform.position=new Vector3(-10000,0,-10);camera.orthographic=true;camera.nearClipPlane=.1f;camera.farClipPlane=100;
            var target=new RenderTexture(Screen.width,Screen.height,24);target.Create();var mode=canvas.renderMode;var previous=canvas.worldCamera;float distance=canvas.planeDistance;var active=RenderTexture.active;Texture2D pixels=null;
            try{camera.targetTexture=target;canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=camera;canvas.planeDistance=1;Canvas.ForceUpdateCanvases();camera.Render();Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;pixels=new Texture2D(target.width,target.height,TextureFormat.RGB24,false);pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0);pixels.Apply();File.WriteAllBytes(Path.Combine(output,"Native","VkSignin102",filename),pixels.EncodeToPNG());report.captures.Add("Native/VkSignin102/"+filename);}
            finally{canvas.renderMode=mode;canvas.worldCamera=previous;canvas.planeDistance=distance;camera.targetTexture=null;RenderTexture.active=active;if(pixels)UnityEngine.Object.DestroyImmediate(pixels);target.Release();UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(root);}
        }
        static void Finish(){EditorApplication.update-=Tick;if(report==null)return;GameLocale.Select(previousLocale);RestoreSize();Application.logMessageReceived-=Log;SessionState.SetBool(Key,false);int code=report.failures.Count==0&&report.engineErrors.Count==0&&report.checks>0?0:1;report.status=code==0?"PASS_NATIVE_VK_SIGNIN102":"FAIL_NATIVE_VK_SIGNIN102";File.WriteAllText(Path.Combine(output,"Native","VkSignin102.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));EditorApplication.Exit(code);}
    }
}
#endif

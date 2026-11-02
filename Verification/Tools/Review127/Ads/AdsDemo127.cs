using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.App.Advertising;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.ServerGameplay;

namespace HeartOfTheRain.Verification127 {
    // Private diagnostic scene only. Every SDK signal and authority result is
    // forwarded unchanged; there is no success injection or direct grant call.
    public sealed class AdsDemo127:MonoBehaviour {
        public const string Package="com.heartoftherain.ads127demo",Origin="https://api.novamind-it.ru",Unit="demo-rewarded-yandex";
        const string Scope="review-ad-demo127";
        [Serializable] sealed class Evidence {
            public int version=1;public string package=Package,unit=Unit,engine,phase="Disconnected",error="",actorDigest="",utc;
            public int connectActions,consentedWatchActions,loadRequests,loaded,loadFailed,shown,rewardedSignals,closed,showFailed,
                reportResponses,claimResponses,distinctReceipts,coins,coinsBeforeWatch,coinsAfterRefresh,claimedToday,remainingToday,cooldownSeconds;
            public long walletRevision;public bool connected,consent,pending,busy,presenting;
            public string journalPhase="None";public string[] receiptDigests=Array.Empty<string>();
            public string scope="Actual Yandex demo SDK callbacks + owned staging API. Completion remains sdk_client_reported_capped; no provider SSV, payment, shipping-app or production acceptance.";
        }
        Evidence evidence=new Evidence();readonly ConcurrentQueue<Action> callbacks=new ConcurrentQueue<Action>();
        ManagedIdentitySession82 identity;IdentityHttpTransport82 identityTransport;RuStoreBackendClient walletClient;
        RewardedAdsFlow85 flow;RewardedAdsJournal85 journal;RewardedAdsClient85 actualApi;
        RuStoreServerWallet wallet;bool busy,consent,closed,fixtureValid;Vector2 scroll;
        string evidencePath;string actor;long contextGeneration;
        string Safe(string value)=>value!=null&&value.Length<=80&&System.Text.RegularExpressions.Regex.IsMatch(value,"^[A-Za-z0-9_.-]*$")?value:"DiagnosticUnavailable";
        void Awake(){
#if HOTR_YANDEX_ADS && HOTR_YANDEX_ADS_ISOLATED_FIXTURE && DEVELOPMENT_BUILD && UNITY_ANDROID && !UNITY_EDITOR
            fixtureValid=Application.identifier==Package&&Debug.isDebugBuild;
#else
            fixtureValid=false;
#endif
            evidencePath=Path.Combine(Application.persistentDataPath,"Diagnostics","AdsDemo127.json");
            try{if(File.Exists(evidencePath)){var old=JsonUtility.FromJson<Evidence>(File.ReadAllText(evidencePath));if(old!=null&&old.version==1&&old.package==Package&&old.unit==Unit&&old.receiptDigests!=null&&old.receiptDigests.Length<=1000&&old.receiptDigests.All(x=>x!=null&&System.Text.RegularExpressions.Regex.IsMatch(x,"^[a-f0-9]{64}$")))evidence=old;}}catch{}
            evidence.engine=Application.unityVersion;evidence.phase=fixtureValid?"Disconnected":"BlockedFixtureProfile";
            evidence.connected=evidence.consent=evidence.busy=evidence.presenting=false;Persist();
        }
        void Update(){int n=0;Action action;while(n++<32&&callbacks.TryDequeue(out action))action();}
        void Post(Action action){if(action!=null&&!closed)callbacks.Enqueue(action);}
        void Persist(){try{PersistCore();}catch{evidence.error="DiagnosticPersistenceUnavailable";}}
        void PersistCore(){
            evidence.utc=DateTime.UtcNow.ToString("o");evidence.busy=busy||(flow!=null&&flow.Busy);
            evidence.pending=flow!=null&&flow.Pending;evidence.presenting=flow!=null&&flow.Presenting;
            evidence.consent=consent;evidence.connected=identity!=null&&identity.HasAccess&&wallet!=null;
            if(wallet!=null){evidence.coins=wallet.coins;evidence.walletRevision=wallet.revision;}
            var status=flow?.Status;if(status!=null){evidence.claimedToday=status.claimedToday;evidence.remainingToday=status.remainingToday;evidence.cooldownSeconds=status.cooldownRemainingSeconds;}
            var receipt=flow?.Receipt;
            if(receipt!=null){string digest=IdentityProtocol82.Sha(receipt.id);if(!evidence.receiptDigests.Contains(digest))evidence.receiptDigests=evidence.receiptDigests.Concat(new[]{digest}).ToArray();evidence.distinctReceipts=evidence.receiptDigests.Length;}
            try{
                Directory.CreateDirectory(Path.GetDirectoryName(evidencePath));string temp=evidencePath+".tmp";
                byte[] bytes=System.Text.Encoding.UTF8.GetBytes(JsonUtility.ToJson(evidence,true)+"\n");
                using(var stream=new FileStream(temp,FileMode.Create,FileAccess.Write,FileShare.None)){stream.Write(bytes,0,bytes.Length);stream.Flush(true);}
                if(File.Exists(evidencePath))File.Replace(temp,evidencePath,null);else File.Move(temp,evidencePath);
            }catch{evidence.error="DiagnosticPersistenceUnavailable";}
        }
        void Phase(string phase,string error=null){evidence.phase=Safe(phase);evidence.error=Safe(error??"");Persist();}
        IEnumerator EnsureSession(bool explicitConnect,Action<bool,string> done){
            if(identity==null){done(false,"ExplicitConnectRequired");yield break;}
            if(identity.HasAccess){done(true,null);yield break;}
            IdentityReply82<IdentityView82> reply=null;
            try{
                if(identity.View.hasPending)identity.Resume(r=>reply=r);
                else if(identity.View.hasSession)identity.Refresh(Guid.NewGuid().ToString("N"),r=>reply=r);
                else if(explicitConnect)identity.CreateGuest(Guid.NewGuid().ToString("N"),r=>reply=r);
                else{done(false,"ExplicitConnectRequired");yield break;}
            }catch{done(false,"ProtectedSessionUnavailable");yield break;}
            while(reply==null&&!closed)yield return null;
            done(reply!=null&&reply.Succeeded,reply?.error??"IdentityUnavailable");
        }
        IEnumerator FetchWallet(Action<bool,string> done){
            bool ready=false;string why=null;yield return EnsureSession(false,(ok,error)=>{ready=ok;why=error;});
            if(!ready){done(false,why);yield break;}
            string expected=identity.ActivePlayerId;
            if(actor!=null&&actor!=expected){done(false,"FixtureOwnerChanged");yield break;}
            walletClient?.Dispose();walletClient=new RuStoreBackendClient(Origin,identity.AccessToken,expected,true,false,r=>StartCoroutine(r),false);
            PayReply<RuStoreServerWallet> reply=null;walletClient.GetWallet(r=>reply=r);while(reply==null&&!closed)yield return null;
            if(reply==null||!reply.Succeeded||!reply.value.initialized||reply.value.playerId!=expected){done(false,"WalletUnavailable");yield break;}
            wallet=reply.value;actor=expected;evidence.actorDigest=IdentityProtocol82.Sha(actor);evidence.coinsAfterRefresh=wallet.coins;Persist();done(true,null);
        }
        IEnumerator Authorize(Action<ServerAuthorizedContext,string> done){
            bool ready=false;string why=null;yield return EnsureSession(false,(ok,error)=>{ready=ok;why=error;});
            if(!ready||identity.ActivePlayerId!=actor){done(null,why??"FixtureOwnerChanged");yield break;}
            long generation=contextGeneration;
            done(new ServerAuthorizedContext(Origin,actor,generation,false,
                ()=>!closed&&contextGeneration==generation&&identity!=null&&identity.ActivePlayerId==actor?identity.AccessToken:null,false),null);
        }
        IEnumerator Connect(){
            if(busy||flow!=null&&flow.Busy)yield break;busy=true;evidence.connectActions++;Phase("Connecting");
            try{
                if(identity==null){
                    var device=new AndroidDeviceIdentity82(Scope);
                    identityTransport=new IdentityHttpTransport82(Origin,r=>StartCoroutine(r),false,false);
                    identity=new ManagedIdentitySession82(device,new OriginBoundIdentityStore82(device,Origin),identityTransport,false);
                }
            }catch{busy=false;Phase("Blocked","ProtectedIdentityUnavailable");yield break;}
            bool ready=false;string why=null;yield return EnsureSession(true,(ok,error)=>{ready=ok;why=error;});
            if(!ready){busy=false;Phase("Blocked",why);yield break;}
            yield return FetchWallet((ok,error)=>{ready=ok;why=error;});
            if(!ready){busy=false;Phase("Blocked",why);yield break;}
            if(flow==null){
                contextGeneration++;actualApi=new RewardedAdsClient85();
                string path=Path.Combine(Application.persistentDataPath,"ServerReview","Advertising",IdentityProtocol82.Sha(Origin),actor,"intent.json");
                journal=new RewardedAdsJournal85(path);
                journal.VerificationCheckpoint=phase=>{evidence.journalPhase=Safe(phase);Persist();};
                flow=new RewardedAdsFlow85(new ObservedApi(this,actualApi),journal,Authorize,FetchWallet,
                    privacy=>new ObservedProvider(this,new YandexRewardedAdsProvider85(Unit,privacy,Post,allowFixtureDemo:true)));
                flow.Changed+=FlowChanged;
            }
            busy=false;Phase("ConnectedProtectedTestGuest");
            yield return flow.Guard(flow.Refresh());FlowChanged();
        }
        void FlowChanged(){
            if(flow==null)return;evidence.error=Safe(flow.Error??"");
            evidence.phase=flow.Presenting?"ShowingDemo":flow.Busy?"RealFlowBusy":flow.Receipt!=null?"DurableRewardObserved":flow.Pending?"PendingRecovery":"Connected";
            Persist();
        }
        void OnGUI(){
            float scale=Mathf.Max(1,Screen.width/440f);GUI.matrix=Matrix4x4.Scale(new Vector3(scale,scale,1));
            GUILayout.BeginArea(new Rect(12,Mathf.Max(12,Screen.safeArea.yMin/scale),Screen.width/scale-24,Screen.height/scale-24));
            scroll=GUILayout.BeginScrollView(scroll);GUILayout.Label("YANDEX DEMO ADS 127 — separate test app");
            GUILayout.Label("Only demo-rewarded-yandex. No live placement or ad creative clicks.");
            GUILayout.Label("Phase: "+evidence.phase+"  "+evidence.error);GUILayout.Label("Coins: "+evidence.coins+" | reward receipts: "+evidence.distinctReceipts);
            GUILayout.Label("SDK load/shown/rewarded/closed: "+evidence.loadRequests+" / "+evidence.shown+" / "+evidence.rewardedSignals+" / "+evidence.closed);
            GUILayout.Label("Today: "+evidence.claimedToday+" | cooldown: "+evidence.cooldownSeconds+" | pending: "+evidence.pending);
            GUI.enabled=fixtureValid&&!busy&&!(flow!=null&&flow.Busy);
            if(GUILayout.Button("Connect / resume this separate test guest",GUILayout.Height(46)))StartCoroutine(Connect());
            GUI.enabled=fixtureValid&&flow!=null&&!busy&&!flow.Busy;
            consent=GUILayout.Toggle(consent,"I choose an optional DEMO video. Non-personalized, location off, age-restricted.",GUILayout.Height(52));
            GUILayout.Label("A completed demo video may grant the fixed server policy: 400 coins, 3/day, 600s cooldown. Early close grants nothing.");
            GUI.enabled=fixtureValid&&flow!=null&&!busy&&!flow.Busy&&consent&&!flow.Pending;
            if(GUILayout.Button("Watch real SDK DEMO video",GUILayout.Height(52))){evidence.consentedWatchActions++;evidence.coinsBeforeWatch=wallet.coins;consent=false;Persist();StartCoroutine(flow.Guard(flow.Watch(new AdPrivacy85(true,false,true))));}
            GUI.enabled=fixtureValid&&flow!=null&&!busy&&!flow.Busy;
            if(GUILayout.Button("Recover pending result — no new video",GUILayout.Height(46)))StartCoroutine(flow.Guard(flow.Recover()));
            if(GUILayout.Button("Refresh server offer / quota",GUILayout.Height(46)))StartCoroutine(flow.Guard(flow.Refresh()));
            GUI.enabled=true;GUILayout.Label("Do not tap the ad creative. Watch to completion, then use its normal close control.");
            GUILayout.EndScrollView();GUILayout.EndArea();
        }
        sealed class ObservedProvider:IRewardedAdsProvider85 {
            readonly AdsDemo127 host;readonly IRewardedAdsProvider85 actual;
            public ObservedProvider(AdsDemo127 h,IRewardedAdsProvider85 p){host=h;actual=p;}
            public bool Installed=>actual.Installed;
            public void Load(Action<bool,string> done){host.evidence.loadRequests++;host.Persist();actual.Load((ok,error)=>{if(ok)host.evidence.loaded++;else host.evidence.loadFailed++;host.Persist();done(ok,error);});}
            public void Show(Action<RewardedSignal85> done){actual.Show(signal=>{switch(signal){case RewardedSignal85.Shown:host.evidence.shown++;break;case RewardedSignal85.CompletedInfoOnly:host.evidence.rewardedSignals++;break;case RewardedSignal85.Closed:host.evidence.closed++;break;case RewardedSignal85.Failed:host.evidence.showFailed++;break;}host.Persist();done(signal);});}
            public void Dispose()=>actual.Dispose();
        }
        sealed class ObservedApi:IRewardedAdsApi85 {
            readonly AdsDemo127 host;readonly IRewardedAdsApi85 actual;
            public ObservedApi(AdsDemo127 h,IRewardedAdsApi85 p){host=h;actual=p;}
            public IEnumerator Status(ServerAuthorizedContext a,Action<AdReply85<AdStatus85>> done)=>actual.Status(a,done);
            public IEnumerator Reserve(ServerAuthorizedContext a,string id,Action<AdReply85<AdOpportunity85>> done)=>actual.Reserve(a,id,done);
            public IEnumerator Read(ServerAuthorizedContext a,string id,Action<AdReply85<AdOpportunity85>> done)=>actual.Read(a,id,done);
            public IEnumerator Report(ServerAuthorizedContext a,string id,string command,Action<AdReply85<AdOpportunity85>> done)=>actual.Report(a,id,command,r=>{host.evidence.reportResponses++;host.Persist();done(r);});
            public IEnumerator Claim(ServerAuthorizedContext a,string id,string command,Action<AdReply85<AdOpportunity85>> done)=>actual.Claim(a,id,command,r=>{host.evidence.claimResponses++;host.Persist();done(r);});
            public IEnumerator Cancel(ServerAuthorizedContext a,string id,string command,Action<AdReply85<AdOpportunity85>> done)=>actual.Cancel(a,id,command,done);
        }
        void OnDestroy(){closed=true;contextGeneration++;flow?.Dispose();actualApi?.Dispose();walletClient?.Dispose();identity?.Dispose();identityTransport?.Dispose();}
    }
}

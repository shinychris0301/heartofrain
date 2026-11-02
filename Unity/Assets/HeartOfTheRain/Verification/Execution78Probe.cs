#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;
using UnityEngine.SceneManagement;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
    // Explicit memory-profile fixture. Timed pure commands are distinct from
    // natural frame pacing and frozen same-pose Render calls. No real attempts.
    public sealed class Execution78Probe:MonoBehaviour {
        public const string Request="HOTR_RunExecution78";
        const float FrozenAge=2.5761447f;
        static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        [Serializable] public struct Span {
            public int frame,gc0Before,gc0After,gc1Before,gc1After,gc2Before,gc2After,gcMax;
            public long startedTicks,finishedTicks;public double startedWall,finishedWall,milliseconds;
        }
        [Serializable] public sealed class ModelPair {
            public int index;public bool controlFirst;public Span control,current;
            public string controlTurnHash,currentTurnHash,controlFinalHash,currentFinalHash,controlCheckpointHash,currentCheckpointHash,controlOrderHash,currentOrderHash;
        }
        [Serializable] public sealed class ModelRow {
            public string name;public List<ModelPair> pairs=new List<ModelPair>();
            public BoardModel.ModelWork controlStages,currentStages;
        }
        [Serializable] public sealed class ResourcePair {
            public int index,phases;public bool controlFirst;public Span controlInitial,currentInitial,controlTraversal,currentTraversal;
            public string controlHash,currentHash;
        }
        [Serializable] public sealed class ResourceRow {
            public string name,turnBeforeHash,turnAfterHash,queueBeforeHash,queueAfterHash;
            public List<ResourcePair> pairs=new List<ResourcePair>();
        }
        [Serializable] public sealed class NaturalRow {
            public string name,fixture,turnHash,finalHash;public int repeat,commandFrame,frameStart,frameCount;
            public bool checkpoint77;public double preparationSeconds,commandStartedWall,commandFinishedWall,modelMs,acceptMs,commandMs,settleSeconds;
            public GameplayScreen.CommandCost enqueueCost;
        }
        [Serializable] public struct FrozenPair {
            public int index;public bool controlFirst;public Span control,current;
            public GameplayScreen.FrameCost controlCost,currentCost;
        }
        [Serializable] public sealed class FrozenRow {
            public string name,family,turnHash,finalHash,queueHash,beforeControlDrawHash,beforeCurrentDrawHash,afterControlDrawHash,afterCurrentDrawHash,beforeControlMeshHash,beforeCurrentMeshHash,afterControlMeshHash,afterCurrentMeshHash;
            public int count,phaseIndex;public float age,clock,phaseDuration;
            public bool resourcesReady,preparationPending;public FrozenPair[] pairs=new FrozenPair[8];
        }
        [Serializable] public sealed class Report {
            public string status="RUNNING",utc,platform,graphics;
            public string scope="Checkpoint78 same-APK controls: natural combined77/current turns on fresh banks; pure model and resource preparation AB/BA pairs; frozen same-bank/same-pose actual GameplayScreen Update/Render calls varying only effect submission. Two untimed natural warmups, no cache flush. Hashes/signatures/I/O outside timed calls. Coarse Render instrumentation; elapsed includes observer, native dispatch and host scheduling. Pure model spans exclude construction. Resource Initial+Traversal includes plan construction and live sequence-match guards, but excludes Ready/callback/loading work. Development retains both buffer implementations. Pure benchmark frame stalls are not gameplay pacing. No physical-device, exclusive stall-cause, universal speedup or hitch-free certification.";
            public int schema=1,targetFps=60,bufferCapacity=8192,pairsPerModel=8,pairsPerResource=8,sourceCheckpoint=79;public bool naturalUsesSynchronousCheckpoint78Startup=true;
            public long stopwatchFrequency;public bool isolatedProfile,launchCleared;
            public List<ModelRow> modelRows=new List<ModelRow>();public List<ResourceRow> resourceRows=new List<ResourceRow>();
            public List<NaturalRow> naturalRows=new List<NaturalRow>();public List<FrozenRow> frozenRows=new List<FrozenRow>();
            public PowerFall77Probe.Frame[] frames;public List<string> errors=new List<string>();
        }
        [Serializable] sealed class DrawState {public List<DrawSprite> draws;}
        [Serializable] sealed class MeshState {public string name;public int order,materialId,textureId;public Vector3 localPosition,localScale,boundsCenter,boundsSize;public Quaternion localRotation;public Vector3[] vertices;public Vector2[] uv;public Color32[] colors;public int[] triangles;}
        [Serializable] sealed class MeshStates {public List<MeshState> meshes=new List<MeshState>();}
        sealed class ResourceResult {public HashSet<string> all;public HashSet<string>[] phases;}
        Report report;GameplayUIAssets ui;GameplayScreen game;M46AtlasBank bank;BoardPresentation presentation;
        Action<TurnResult> accept;Action updateGame;Canvas[] hidden;bool[] wasEnabled;
        PowerFall77Probe.Frame[] buffered;int used,recording=-1;double deadline;string memoryPlayerId;
        static bool pending;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)] static void Boot(){
            SceneManager.sceneLoaded-=Attach;pending=false;var path=Path.Combine(Application.persistentDataPath,Request);
            if(!File.Exists(path))return;File.Delete(path);pending=true;SceneManager.sceneLoaded+=Attach;
        }
        static void Attach(Scene scene,LoadSceneMode mode){
            if(!pending)return;var first=FindFirstObjectByType<FirstStartPage>();if(!first)return;pending=false;SceneManager.sceneLoaded-=Attach;first.reviewAlways=true;
            var host=first.home.GetComponent<PlayerProfileHost>();if(!host)host=first.home.gameObject.AddComponent<PlayerProfileHost>();var profile=PlayerProfile.New(new[]{5,5,3,2});
            host.VerificationRepository=new MemoryProfileRepository(profile);host.VerificationAuthorityFactory=_=>new UnavailableGiftAuthority();host.VerificationLivesClock=()=>1000;
            var node=new GameObject("Opt-in checkpoint78 execution controls");DontDestroyOnLoad(node);node.AddComponent<Execution78Probe>().memoryPlayerId=profile.playerId;
        }
        void Start(){report=new Report{utc=DateTime.UtcNow.ToString("o"),platform=Application.platform.ToString(),graphics=SystemInfo.graphicsDeviceName,stopwatchFrequency=Stopwatch.Frequency};
            buffered=new PowerFall77Probe.Frame[report.bufferCapacity];deadline=Time.realtimeSinceStartupAsDouble+600;Application.targetFrameRate=report.targetFps;Application.logMessageReceived+=Log;StartCoroutine(Run());}
        void Log(string value,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)Fail(value+"\n"+stack);}
        void Update(){if(report!=null&&report.status=="RUNNING"&&Time.realtimeSinceStartupAsDouble>deadline)Fail("Execution78 timeout");}
        void LateUpdate(){
            if(recording<0||!game||game.LastFrameCost.frame!=Time.frameCount)return;if(used==buffered.Length){Fail("Execution78 buffer overflow");return;}
            buffered[used++]=new PowerFall77Probe.Frame{row=recording,frame=Time.frameCount,intervalMs=Time.unscaledDeltaTime*1000,absoluteWall=Time.realtimeSinceStartupAsDouble,cost=game.LastFrameCost,
                spriteCreates=bank.SpriteCreates,spriteEvictions=bank.SpriteEvictions,synchronousLoads=bank.SynchronousLoads,cachedSprites=bank.SpriteCount,cachedTextures=bank.TextureCount,
                preparationPending=bank.PowerPreparationPending,preparation=bank.LastPowerPreparationBatch,preparationBatches=bank.PowerPreparationBatches,preparationFrames=bank.PowerPreparationFrames,preparationCreates=bank.PowerPreparationCreates};
        }
        T Get<T>(string name)=>(T)typeof(GameplayScreen).GetField(name,Private).GetValue(game);
        void Set(string name,object value)=>typeof(GameplayScreen).GetField(name,Private).SetValue(game,value);
        IEnumerator Ready(){while(!game.CanAct)yield return null;yield return null;bank=Get<M46AtlasBank>("bank");presentation=Get<BoardPresentation>("presentation");game.GetComponent<GameplayHUD>().ResultRequested=(won,level)=>true;}
        void Check(bool ok,string text){if(!ok)throw new InvalidOperationException(text);}
        static string Hash(string value){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(Encoding.UTF8.GetBytes(value))).Replace("-","").ToLowerInvariant();}
        static string JsonHash(object value)=>Hash(JsonUtility.ToJson(value));
        static Span BeginSpan(){int max=GC.MaxGeneration;return new Span{frame=Time.frameCount,gcMax=max,gc0Before=GC.CollectionCount(0),gc1Before=max>=1?GC.CollectionCount(1):-1,gc2Before=max>=2?GC.CollectionCount(2):-1,startedWall=Time.realtimeSinceStartupAsDouble,startedTicks=Stopwatch.GetTimestamp()};}
        static void EndSpan(ref Span span){span.finishedTicks=Stopwatch.GetTimestamp();span.finishedWall=Time.realtimeSinceStartupAsDouble;span.milliseconds=(span.finishedTicks-span.startedTicks)*1000.0/Stopwatch.Frequency;span.gc0After=GC.CollectionCount(0);span.gc1After=span.gcMax>=1?GC.CollectionCount(1):-1;span.gc2After=span.gcMax>=2?GC.CollectionCount(2):-1;}
        IEnumerator Run(){
            FirstStartPage first;while(!(first=FindFirstObjectByType<FirstStartPage>())||!first.Initialized)yield return null;
            while(FindFirstObjectByType<HeartOfTheRain.App.Launch.LaunchPage>())yield return null;report.launchCleared=true;
            var host=first.home.GetComponent<PlayerProfileHost>();report.isolatedProfile=host&&host.Ready&&host.VerificationRepository is MemoryProfileRepository&&host.Service.Read().playerId==memoryPlayerId;
            if(!report.isolatedProfile){Fail("Execution78 profile isolation failed");yield break;}
            ui=first.assets.Gameplay;hidden=FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID);wasEnabled=hidden.Select(c=>c.enabled).ToArray();foreach(var c in hidden)c.enabled=false;
            game=new GameObject("Isolated execution78 board").AddComponent<GameplayScreen>();game.uiAssets=ui;game.initialLevel=1;game.showLevelIntro=false;game.HintsEnabled=false;
            game.DeferTerminalPresentation=true;game.MeasureFrameCosts=true;game.MeasureDetailedDrawCosts=false;game.VerificationRendererCapacity=1182;
            accept=(Action<TurnResult>)Delegate.CreateDelegate(typeof(Action<TurnResult>),game,typeof(GameplayScreen).GetMethod("Accept",Private));updateGame=(Action)Delegate.CreateDelegate(typeof(Action),game,typeof(GameplayScreen).GetMethod("Update",Private));yield return Ready();
            // Warm code/driver paths only; every subsequent Load owns a new bank.
            for(int warm=0;warm<2;warm++){yield return Natural("L1_golden_bomb",0,warm==0,false);}
            foreach(string fixture in new[]{"L1_golden_bomb","L1_orb_rocket"})for(int repeat=0;repeat<2;repeat++)for(int branch=0;branch<2;branch++)yield return Natural(fixture,repeat,(branch==0)==(repeat%2==0),true);
            game.gameObject.SetActive(false);
            foreach(string name in ModelWork78Proof.BenchmarkNames){
                for(int warm=0;warm<2;warm++){ModelWork78Proof.Prepare(ui.boards,name,true).Solve();ModelWork78Proof.Prepare(ui.boards,name,false).Solve();}
                var row=new ModelRow{name=name};report.modelRows.Add(row);
                for(int index=0;index<report.pairsPerModel;index++){
                    var control=ModelWork78Proof.Prepare(ui.boards,name,true);var current=ModelWork78Proof.Prepare(ui.boards,name,false);
                    control.model.VerificationMeasureWork=current.model.VerificationMeasureWork=false;var pair=new ModelPair{index=index,controlFirst=index%2==0};TurnResult a=null,b=null;
                    if(pair.controlFirst){a=TimedModel(control,out pair.control);b=TimedModel(current,out pair.current);}else{b=TimedModel(current,out pair.current);a=TimedModel(control,out pair.control);}
                    pair.controlTurnHash=JsonHash(a);pair.currentTurnHash=JsonHash(b);pair.controlFinalHash=JsonHash(control.model.Snapshot());pair.currentFinalHash=JsonHash(current.model.Snapshot());
                    pair.controlCheckpointHash=JsonHash(control.model.Checkpoint());pair.currentCheckpointHash=JsonHash(current.model.Checkpoint());
                    pair.controlOrderHash=Hash(string.Join(";",control.model.Pieces.Select(p=>p.Key+":"+p.Value.id)));pair.currentOrderHash=Hash(string.Join(";",current.model.Pieces.Select(p=>p.Key+":"+p.Value.id)));
                    Check(a.accepted&&b.accepted&&pair.controlTurnHash==pair.currentTurnHash&&pair.controlFinalHash==pair.currentFinalHash&&pair.controlCheckpointHash==pair.currentCheckpointHash&&pair.controlOrderHash==pair.currentOrderHash,"Paired model78 outcome "+name+"/"+index);
                    row.pairs.Add(pair);yield return null;
                }
                // Stage timers are separate diagnostics, never mixed into the primary pairs.
                var ca=ModelWork78Proof.Measure(ModelWork78Proof.Prepare(ui.boards,name,true),true);var cb=ModelWork78Proof.Measure(ModelWork78Proof.Prepare(ui.boards,name,false),true);
                row.controlStages=ca.work;row.currentStages=cb.work;Check(JsonHash(ca.turn)==row.pairs[0].controlTurnHash&&JsonHash(cb.turn)==row.pairs[0].currentTurnHash,"Stage diagnostics preserve outputs "+name);
            }
            foreach(string name in ModelWork78Proof.BenchmarkNames){
                var fixture=ModelWork78Proof.Prepare(ui.boards,name);var turn=fixture.Solve();var queue=BoardPlayback.Build(turn.steps,fixture.model.Level);
                var row=new ResourceRow{name=name,turnBeforeHash=JsonHash(turn),queueBeforeHash=SmoothnessCommandProof.Signature(queue,false)};report.resourceRows.Add(row);
                var resourceBank=new M46AtlasBank(ui.boards);var context=new CommandResourcePreparation(ui.boards);
                try{
                    for(int warm=0;warm<2;warm++){ResourceMeasure(resourceBank,context,queue,true,out _,out _);ResourceMeasure(resourceBank,context,queue,false,out _,out _);}
                    for(int index=0;index<report.pairsPerResource;index++){
                        var pair=new ResourcePair{index=index,controlFirst=index%2==0,phases=queue.Count};ResourceResult a,b;
                        if(pair.controlFirst){a=ResourceMeasure(resourceBank,context,queue,true,out pair.controlInitial,out pair.controlTraversal);b=ResourceMeasure(resourceBank,context,queue,false,out pair.currentInitial,out pair.currentTraversal);}
                        else{b=ResourceMeasure(resourceBank,context,queue,false,out pair.currentInitial,out pair.currentTraversal);a=ResourceMeasure(resourceBank,context,queue,true,out pair.controlInitial,out pair.controlTraversal);}
                        pair.controlHash=ResourceHash(a);pair.currentHash=ResourceHash(b);Check(pair.controlHash==pair.currentHash,"Ordered per-phase/whole resource parity "+name);row.pairs.Add(pair);yield return null;
                    }
                    row.turnAfterHash=JsonHash(turn);row.queueAfterHash=SmoothnessCommandProof.Signature(queue,false);Check(row.turnBeforeHash==row.turnAfterHash&&row.queueBeforeHash==row.queueAfterHash,"Resource planning input immutability "+name);
                }finally{resourceBank.Dispose();}
            }
            game.gameObject.SetActive(true);
            foreach(string family in new[]{"crate","stone"})foreach(int count in new[]{1,45})yield return Frozen(family,count);
            for(int i=0;i<used;i++){string error;Check(PowerFall77Probe.ValidateFrameCost(buffered[i].cost,out error),"Natural cost hierarchy: "+error);}
            foreach(var row in report.frozenRows)foreach(var pair in row.pairs){string error;Check(PowerFall77Probe.ValidateFrameCost(pair.controlCost,out error)&&PowerFall77Probe.ValidateFrameCost(pair.currentCost,out error),"Frozen cost hierarchy: "+error);}
            Finish(true);
        }
        TurnResult TimedModel(ModelWork78Proof.Prepared prepared,out Span timing){timing=BeginSpan();var turn=prepared.Solve();EndSpan(ref timing);return turn;}
        static ResourceResult ResourceMeasure(M46AtlasBank bank,CommandResourcePreparation context,IList<BoardStep> queue,bool old,out Span initial,out Span traversal){
            var result=new ResourceResult{phases=new HashSet<string>[queue.Count]};CommandResourcePreparation.Plan plan=null;
            initial=BeginSpan();if(old){result.phases[0]=bank.RequiredResources(new[]{queue[0]});result.all=bank.RequiredResources(queue);}else{plan=context.Build(queue);if(!plan.Matches(queue))throw new InvalidOperationException("Prepared phase ownership differs");result.phases[0]=plan.Phase(0);if(!plan.Matches(queue))throw new InvalidOperationException("Prepared queue ownership differs");result.all=plan.All;}EndSpan(ref initial);
            traversal=BeginSpan();for(int i=1;i<queue.Count;i++){if(!old&&!plan.Matches(queue))throw new InvalidOperationException("Prepared traversal ownership differs");result.phases[i]=old?bank.RequiredResources(new[]{queue[i]}):plan.Phase(i);}EndSpan(ref traversal);return result;
        }
        static string ResourceHash(ResourceResult result){var s=new StringBuilder();s.Append("all:").Append(string.Join("\n",result.all));foreach(var phase in result.phases)s.Append("\nphase:").Append(string.Join("\n",phase));return Hash(s.ToString());}
        IEnumerator Natural(string fixture,int repeat,bool old,bool measured){
            // This historical command-cost experiment retains its synchronous
            // startup contract in both branches. FirstPose79 measures the new
            // deferred default separately; no await is folded into Accept.
            game.VerificationUseCheckpoint78Startup=true;
            var prepared=ModelWork78Proof.Prepare(ui.boards,fixture,old);game.VerificationUseCheckpoint77Resources=old;game.VerificationUseCheckpoint77Submission=old;
            game.VerificationLevelOverride=prepared.model.Level;double loaded=Time.realtimeSinceStartupAsDouble;game.Load(prepared.model.Level.globalLevel-1);yield return Ready();
            // Replace the isolated fixture's model before command timing. Queue
            // callbacks never point at a real profile/attempt or player wallet.
            Set("board",prepared.model);Set("idle",prepared.model.Snapshot());
            var row=new NaturalRow{name=fixture+"_"+repeat+(old?"_control77":"_current78"),fixture=fixture,repeat=repeat,checkpoint77=old,preparationSeconds=Time.realtimeSinceStartupAsDouble-loaded,frameStart=used};
            if(measured){report.naturalRows.Add(row);recording=report.naturalRows.Count-1;}
            row.commandFrame=Time.frameCount;row.commandStartedWall=Time.realtimeSinceStartupAsDouble;var turn=prepared.Solve();row.modelMs=(Time.realtimeSinceStartupAsDouble-row.commandStartedWall)*1000;
            double at=Time.realtimeSinceStartupAsDouble;accept(turn);row.acceptMs=(Time.realtimeSinceStartupAsDouble-at)*1000;row.commandFinishedWall=Time.realtimeSinceStartupAsDouble;row.commandMs=(row.commandFinishedWall-row.commandStartedWall)*1000;row.enqueueCost=game.LastCommandCost;
            Check(turn.accepted,"Natural fixture rejected "+fixture);while(game.Busy||game.VerificationTurnPreparationPending)yield return null;yield return null;yield return null;
            if(measured){recording=-1;row.frameCount=used-row.frameStart;row.settleSeconds=Time.realtimeSinceStartupAsDouble-row.commandStartedWall;row.turnHash=JsonHash(turn);row.finalHash=JsonHash(prepared.model.Snapshot());}
        }
        IEnumerator Frozen(string family,int count){
            game.VerificationUseCheckpoint78Startup=false;game.VerificationUseCheckpoint77Resources=false;game.VerificationUseCheckpoint77Submission=false;
            game.VerificationLevelOverride=ObstacleDensityFixture.Level(JsonUtility.FromJson<LevelData>(ui.boards.levels[25].text),count,family);game.Load(25);yield return Ready();
            var turn=ObstacleDensityFixture.Solve(game.Model);Check(turn.accepted,"Frozen fixture rejected");accept(turn);
            // Metadata completion is an untimed fixture prerequisite, before
            // pausing and selecting the fixed pose. It is not Accept latency.
            while(game.VerificationStartupPending)yield return null;
            Set("pause",true);var queue=Get<List<BoardStep>>("queue");var required=bank.RequiredResources(queue);yield return null;
            while(game.VerificationPreparing||game.VerificationTurnPreparationPending||!bank.Ready(required))yield return null;yield return null;while(game.VerificationTurnPreparationPending)yield return null;game.enabled=false;
            int index=queue.FindIndex(s=>s.kind=="powerFall");Check(index>=0&&queue[index].duration>=FrozenAge,"Frozen pose unavailable");float start=0;presentation.history.Clear();for(int i=0;i<=index;i++){presentation.Add(queue[i],start);if(i<index)start+=queue[i].duration;}
            var step=queue[index];Set("current",step);Set("idle",step.before);Set("clock",start+FrozenAge);Set("started",start);Set("queueIndex",index+1);Set("pause",true);Set("awaitingPlaybackPose",false);Set("playbackPoseAnchor",false);
            var row=new FrozenRow{name=family+"_"+count,family=family,count=count,phaseIndex=index,age=FrozenAge,clock=start+FrozenAge,phaseDuration=step.duration,resourcesReady=bank.Ready(required),preparationPending=game.VerificationTurnPreparationPending,turnHash=JsonHash(turn),finalHash=JsonHash(game.Model.Snapshot()),queueHash=SmoothnessCommandProof.Signature(queue,false)};
            report.frozenRows.Add(row);Check(row.resourcesReady&&!row.preparationPending,"Frozen preparation incomplete");
            for(int warm=0;warm<2;warm++){game.VerificationUseCheckpoint77Submission=true;updateGame();game.VerificationUseCheckpoint77Submission=false;updateGame();}Capture(row,true);
            for(int indexPair=0;indexPair<row.pairs.Length;indexPair++){
                var pair=new FrozenPair{index=indexPair,controlFirst=indexPair%2==0};if(pair.controlFirst){FrozenTimed(true,ref pair);FrozenTimed(false,ref pair);}else{FrozenTimed(false,ref pair);FrozenTimed(true,ref pair);}row.pairs[indexPair]=pair;yield return null;
            }
            Capture(row,false);Check(new[]{row.beforeControlDrawHash,row.beforeCurrentDrawHash,row.afterControlDrawHash,row.afterCurrentDrawHash}.Distinct().Count()==1&&new[]{row.beforeControlMeshHash,row.beforeCurrentMeshHash,row.afterControlMeshHash,row.afterCurrentMeshHash}.Distinct().Count()==1,"Frozen exact draw/mesh parity "+row.name);
            game.VerificationUseCheckpoint77Submission=false;game.enabled=true;Set("pause",false);
        }
        void FrozenTimed(bool old,ref FrozenPair pair){game.VerificationUseCheckpoint77Submission=old;var span=BeginSpan();updateGame();EndSpan(ref span);if(old){pair.control=span;pair.controlCost=game.LastFrameCost;}else{pair.current=span;pair.currentCost=game.LastFrameCost;}}
        void Capture(FrozenRow row,bool before){game.VerificationUseCheckpoint77Submission=true;updateGame();string a=DrawHash(),b=MeshHash();game.VerificationUseCheckpoint77Submission=false;updateGame();string c=DrawHash(),d=MeshHash();if(before){row.beforeControlDrawHash=a;row.beforeControlMeshHash=b;row.beforeCurrentDrawHash=c;row.beforeCurrentMeshHash=d;}else{row.afterControlDrawHash=a;row.afterControlMeshHash=b;row.afterCurrentDrawHash=c;row.afterCurrentMeshHash=d;}}
        string DrawHash()=>JsonHash(new DrawState{draws=presentation.SampleLive(Get<BoardStep>("current"),Get<BoardSnapshot>("idle"),Get<float>("clock"),Get<float>("started"))});
        string MeshHash(){var state=new MeshStates();foreach(var filter in Get<Transform>("root").GetComponentsInChildren<MeshFilter>(true)){var renderer=filter.GetComponent<MeshRenderer>();if(!renderer||!renderer.enabled)continue;var mesh=filter.sharedMesh;if(!mesh)continue;var block=new MaterialPropertyBlock();renderer.GetPropertyBlock(block);var texture=block.GetTexture(Shader.PropertyToID("_MainTex"));var material=renderer.sharedMaterial;state.meshes.Add(new MeshState{name=filter.name,order=renderer.sortingOrder,materialId=material?material.GetInstanceID():0,textureId=texture?texture.GetInstanceID():0,localPosition=filter.transform.localPosition,localRotation=filter.transform.localRotation,localScale=filter.transform.localScale,boundsCenter=mesh.bounds.center,boundsSize=mesh.bounds.size,vertices=mesh.vertices,uv=mesh.uv,colors=mesh.colors32,triangles=mesh.triangles});}return JsonHash(state);}
        void Fail(string error){if(report==null||report.status!="RUNNING")return;report.errors.Add(error);Finish(false);}
        void Finish(bool ok){if(report==null||report.status!="RUNNING")return;recording=-1;StopAllCoroutines();report.frames=new PowerFall77Probe.Frame[used];Array.Copy(buffered,report.frames,used);report.status=ok&&report.errors.Count==0?"PASS_NATIVE_EXECUTION78":"FAIL_NATIVE_EXECUTION78";Application.logMessageReceived-=Log;if(game){game.gameObject.SetActive(false);Destroy(game.gameObject);}if(hidden!=null)for(int i=0;i<hidden.Length;i++)if(hidden[i])hidden[i].enabled=wasEnabled[i];string folder=Path.Combine(Application.persistentDataPath,"Execution78");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"Report.json"),JsonUtility.ToJson(report,true));}
        void OnDestroy(){Application.logMessageReceived-=Log;}
    }
}
#endif

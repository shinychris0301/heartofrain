#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEngine;
using UnityEngine.Profiling;
using UnityEngine.SceneManagement;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Celebrations;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification
{
    // Same probe can be compiled with the previous and current runtime. No
    // screenshots, PNG encoding, disk writes or accelerated playback while timed.
    public sealed class FluidityDeviceProbe:MonoBehaviour
    {
        public const string Request="HOTR_RunFluidity";
        [Serializable] public sealed class Phase {public string name;public int frames,over33ms,over50ms,gen0Collections,synchronousTextureLoads,spriteCreates,spriteEvictions,peakCachedSprites,peakActiveSprites,peakHistorySteps,bankSpriteHighWater,poolAtReady,poolAtEnd,commandFrame;public float p50Ms,p95Ms,worstMs;public double modelMs,acceptMs,commandMs,firstPresentationMs,settleSeconds,preparationSeconds;public long allocatedMemoryBytes,textureBytes,managedAllocatedBytes,cachedSpriteRuntimeBytes;}
        [Serializable] public struct FrameSample {public int phase,frame,poolCreated,spriteCreated,draws;public float intervalMs;public double updateMs,renderMs,sampleMs;}
        [Serializable] public sealed class Report {public string status="RUNNING",utc,unity,platform,graphics,variant,scope="Unaccelerated isolated native emulator Update intervals and command CPU times; memory-only review profile/tutorial and no campaign hooks on the measured board. No screenshot/readback during timing. Includes CPU/GPU waits and emulator scheduling. Thread allocation counter is disabled on this player; GC collection counts remain available. StepStarted dispatch is not first visible frame or touch latency. Not physical-device certification.";public bool isolatedProfile,launchCleared,allocationCounterUsable;public long allocationPositiveControlBytes;public List<Phase> phases=new List<Phase>();public List<FrameSample> frameSamples=new List<FrameSample>(8192);public List<string> errors=new List<string>();}
        Report report;GameplayScreen game;M46AtlasBank phaseBank;readonly List<float> frames=new List<float>(3000);Phase phase;int gc,loads,spriteCreates,spriteEvictions;double began,commandAt,preparationSeconds;bool hasStep;float timeout;string variant,reviewPlayerId;bool baseline,focus;
        static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static string pendingVariant;
        // Launch is now the first scene. Attach before FirstStart/Home Start,
        // so a returning profile cannot bypass the review tutorial or be read.
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)] static void Boot(){
            SceneManager.sceneLoaded-=Attach;pendingVariant=null;var file=Path.Combine(Application.persistentDataPath,Request);if(!File.Exists(file))return;
            pendingVariant=File.ReadAllText(file).Trim();File.Delete(file);SceneManager.sceneLoaded+=Attach;
        }
        static void Attach(Scene scene,LoadSceneMode mode){
            var first=FindFirstObjectByType<FirstStartPage>();if(!first)return;SceneManager.sceneLoaded-=Attach;first.reviewAlways=true;
            var host=first.home.GetComponent<PlayerProfileHost>();if(!host)host=first.home.gameObject.AddComponent<PlayerProfileHost>();
            var profile=PlayerProfile.New(new[]{5,5,3,2});host.VerificationRepository=new MemoryProfileRepository(profile);host.VerificationAuthorityFactory=_=>new UnavailableGiftAuthority();host.VerificationLivesClock=()=>1000;
            var node=new GameObject("Opt-in fluidity measurement");DontDestroyOnLoad(node);var probe=node.AddComponent<FluidityDeviceProbe>();probe.variant=pendingVariant;probe.reviewPlayerId=profile.playerId;pendingVariant=null;
        }
        void Start(){baseline=variant.StartsWith("baseline")||variant.StartsWith("cache");focus=variant.EndsWith("focus");report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,platform=Application.platform.ToString(),graphics=SystemInfo.graphicsDeviceName,variant=variant};report.allocationCounterUsable=false;report.allocationPositiveControlBytes=-1;Application.logMessageReceived+=Log;timeout=Time.realtimeSinceStartup+210;StartCoroutine(Run());}
        void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert){report.errors.Add(message);Finish(false);}}
        void Update(){if(report.status!="RUNNING")return;if(Time.realtimeSinceStartup>timeout){report.errors.Add("Measurement timeout");Finish(false);return;}if(phase!=null){frames.Add(Time.unscaledDeltaTime*1000);phase.peakCachedSprites=Math.Max(phase.peakCachedSprites,game.CachedSpriteCount);phase.peakActiveSprites=Math.Max(phase.peakActiveSprites,game.ActiveSpriteCount);phase.peakHistorySteps=Math.Max(phase.peakHistorySteps,game.HistoryCount);}}
        void LateUpdate(){if(phase==null||!game||game.LastFrameCost.frame!=Time.frameCount)return;var f=game.LastFrameCost;report.frameSamples.Add(new FrameSample{phase=report.phases.Count,frame=f.frame,intervalMs=Time.unscaledDeltaTime*1000,poolCreated=f.poolCreated,spriteCreated=f.spriteCreated,draws=f.draws,updateMs=f.updateMs,renderMs=f.renderMs,sampleMs=f.sampleMs});}
        IEnumerator Ready(){while(game&&!game.CanAct)yield return null;yield return null;}
        void Begin(string name){frames.Clear();phase=new Phase{name=name,poolAtReady=game.RendererPoolCount,preparationSeconds=preparationSeconds};phaseBank=(M46AtlasBank)typeof(GameplayScreen).GetField("bank",Private).GetValue(game);spriteCreates=phaseBank.SpriteCreates;spriteEvictions=phaseBank.SpriteEvictions;gc=GC.CollectionCount(0);loads=game.SynchronousTextureLoads;began=Time.realtimeSinceStartupAsDouble;hasStep=false;}
        void End(){var row=phase;phase=null;row.poolAtEnd=game.RendererPoolCount;row.managedAllocatedBytes=-1;row.spriteCreates=phaseBank.SpriteCreates-spriteCreates;row.spriteEvictions=phaseBank.SpriteEvictions-spriteEvictions;row.gen0Collections=GC.CollectionCount(0)-gc;row.synchronousTextureLoads=game.SynchronousTextureLoads-loads;row.settleSeconds=Time.realtimeSinceStartupAsDouble-began;row.allocatedMemoryBytes=Profiler.GetTotalAllocatedMemoryLong();row.textureBytes=game.CachedTextureBytes;row.bankSpriteHighWater=phaseBank.SpriteHighWaterMark;row.cachedSpriteRuntimeBytes=phaseBank.CachedSpriteRuntimeBytes;var values=frames.OrderBy(v=>v).ToArray();row.frames=values.Length;if(values.Length>0){row.p50Ms=values[values.Length/2];row.p95Ms=values[Math.Min(values.Length-1,(int)(values.Length*.95))];row.worstMs=values[values.Length-1];row.over33ms=values.Count(v=>v>33.34f);row.over50ms=values.Count(v=>v>50);}report.phases.Add(row);}
        void Accept(TurnResult turn){if(!turn.accepted)throw new Exception("Fixture action rejected: "+turn.reason);typeof(GameplayScreen).GetMethod("Accept",Private).Invoke(game,new object[]{turn});}
        IEnumerator Run()
        {
            while(!FindFirstObjectByType<FirstStartPage>()||!FindFirstObjectByType<FirstStartPage>().Initialized||!FindFirstObjectByType<FirstStartPage>().IsVisible)yield return null;
            // Launch must observe its destination before the probe hides it.
            // Hiding tutorial/Home in that same frame would strand the shield.
            while(FindFirstObjectByType<HeartOfTheRain.App.Launch.LaunchPage>())yield return null;report.launchCleared=true;
            var first=FindFirstObjectByType<FirstStartPage>();var host=first.home.GetComponent<PlayerProfileHost>();report.isolatedProfile=host&&host.Ready&&host.VerificationRepository is MemoryProfileRepository&&host.Service.Read().playerId==reviewPlayerId;
            if(!report.isolatedProfile){report.errors.Add("Fluidity review did not initialize its isolated memory profile");Finish(false);yield break;}
            var home=first.home;var ui=first.assets.Gameplay;first.Request("skip");first.Request("skip");yield return null;home.SetPresentation(false,false);
            double loadAt=Time.realtimeSinceStartupAsDouble;game=new GameObject("Measured board").AddComponent<GameplayScreen>();game.uiAssets=ui;game.showLevelIntro=false;game.initialLevel=1;game.VerificationSkipWarmup=baseline;game.VerificationSkipFastCache=variant.StartsWith("baseline")||variant.StartsWith("warm");game.MeasureFrameCosts=true;
            yield return Ready();game.GetComponent<GameplayHUD>().ResultRequested=(won,number)=>true;game.StepStarted+=s=>{if(phase!=null&&!hasStep){hasStep=true;phase.firstPresentationMs=(Time.realtimeSinceStartupAsDouble-commandAt)*1000;}};
            preparationSeconds=Time.realtimeSinceStartupAsDouble-loadAt;
            yield return new WaitForSecondsRealtime(1);Begin("idle_including_hint_search");yield return new WaitForSecondsRealtime(focus?2:8);End();
            foreach(string caseName in focus?new[]{"orb_rocket_1","golden_bomb_1","orb_rocket_2","golden_bomb_2","orb_rocket_3","golden_bomb_3"}:new[]{"natural_first","natural_second","rocket","three_rocket_chain","orb_rocket","golden_bomb"}){
                string name=focus?caseName.Substring(0,caseName.LastIndexOf('_')):caseName;
                if(!name.StartsWith("natural")){loadAt=Time.realtimeSinceStartupAsDouble;game.Load(0);yield return Ready();preparationSeconds=Time.realtimeSinceStartupAsDouble-loadAt;}
                var board=game.Model;Cell[] move=null;Piece source=null,partner=null;
                if(name.StartsWith("natural"))move=board.LegalSwaps().First();
                else if(name=="three_rocket_chain"){var row=board.Pieces.Values.Where(p=>p.family=="gem").GroupBy(p=>p.y).First(g=>g.Count()>=3).OrderBy(p=>p.x).Take(3).ToArray();source=row[0];foreach(var p in row)board.InjectReviewPower(p.x,p.y,4);}
                else {source=board.Pieces.Values.First(p=>p.family=="gem"&&board.At(p.x+1,p.y)?.family=="gem");if(name=="rocket")board.InjectReviewPower(source.x,source.y,4);else {partner=board.At(source.x+1,source.y);board.InjectReviewPower(source.x,source.y,name=="orb_rocket"?7:16);board.InjectReviewPower(partner.x,partner.y,name=="orb_rocket"?4:21);}}
                yield return null;Begin(caseName);phase.commandFrame=Time.frameCount;commandAt=Time.realtimeSinceStartupAsDouble;
                TurnResult turn=move!=null?board.Swap(move[0].x,move[0].y,move[1].x,move[1].y):partner!=null?board.Swap(source.x,source.y,partner.x,partner.y):board.Tap(source.x,source.y);phase.modelMs=(Time.realtimeSinceStartupAsDouble-commandAt)*1000;double acceptAt=Time.realtimeSinceStartupAsDouble;Accept(turn);phase.acceptMs=(Time.realtimeSinceStartupAsDouble-acceptAt)*1000;phase.commandMs=(Time.realtimeSinceStartupAsDouble-commandAt)*1000;
                while(game.Busy)yield return null;yield return new WaitForSecondsRealtime(.25f);End();
            }
            if(!focus){game.ReviewInputBlocked=true;Begin("victory_animation");bool done=false;if(!VictoryCelebrationPlayer.TryPlayStandalone(game,1,()=>done=true))throw new Exception("Victory did not start");while(!done)yield return null;End();}
            Finish(true);game.gameObject.SetActive(false);Destroy(game.gameObject);game=null;home.SetPresentation(true,true);
        }
        void Finish(bool ok){if(report.status!="RUNNING")return;report.status=ok&&report.errors.Count==0?"RECORDED_NATIVE_FLUIDITY":"FAIL_NATIVE_FLUIDITY";Application.logMessageReceived-=Log;string path=Path.Combine(Application.persistentDataPath,"Fluidity");Directory.CreateDirectory(path);File.WriteAllText(Path.Combine(path,"Measurement.json"),JsonUtility.ToJson(report,true));}
        void OnDestroy(){Application.logMessageReceived-=Log;}
    }
}
#endif

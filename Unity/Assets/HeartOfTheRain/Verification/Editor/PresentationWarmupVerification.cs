#if UNITY_EDITOR
using System;using System.IO;using System.Linq;using System.Reflection;using System.Collections.Generic;using UnityEditor;using UnityEditor.SceneManagement;using UnityEngine;using HeartOfTheRain.M46;using HeartOfTheRain.M47;using HeartOfTheRain.App.FirstStart;
namespace HeartOfTheRain.Verification {
 [InitializeOnLoad] public static class PresentationWarmupVerification {
  const string Key="HOTR.Warmup.Native";const BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
  [Serializable] class Report {public string status,utc,startupMode,scope="Native Unity Play Mode pool/resource lifecycle and renderer-property checks. Default79 startup observes an actual own-camera witness or supplies an offscreen render when batchmode has no GameView. The witness may show an active head or a held post-swap pose; Lifecycle79 separately verifies the first head. Android timing, performance and visible review are separate.";public int checks,initialPool,retainedPool,largestWarmupLevel,largestCommonCaptured,largestCommonRetained,largestWarmupFrames,largestReadySpriteEvictions,startupHeadSubmittedFrame,startupCameraWitnessFrame,startupJobStartedFrame;public bool startupWitnessed,startupExplicitOffscreenWitness;public GameplayScreen.StartupTrace79 startupTrace;public List<string> passed=new List<string>(),failures=new List<string>();}
  static Report report;static GameplayScreen game;static GameplayUIAssets ui;static int phase,lastFrame;static int[] ids;static string expected;static double at;
  static string[] commonKeys;static Dictionary<string,Sprite> largestCommon;static int largestCaptureFrame,largestObservedFrame=-1;
  static PresentationWarmupVerification(){if(SessionState.GetBool(Key,false)){report=new Report{utc=DateTime.UtcNow.ToString("o")};EditorApplication.update+=Tick;Application.logMessageReceived+=Log;at=EditorApplication.timeSinceStartup;}}
  public static void Run(){SessionState.SetBool(Key,true);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");var f=UnityEngine.Object.FindFirstObjectByType<FirstStartPage>();if(f)f.reviewAlways=true;EditorApplication.isPlaying=true;}
  static T Field<T>(string name)=>(T)typeof(GameplayScreen).GetField(name,Flags).GetValue(game);
  static void Invoke(string name,params object[] args)=>typeof(GameplayScreen).GetMethod(name,Flags).Invoke(game,args);
  static List<SpriteRenderer> Pool()=>Field<List<SpriteRenderer>>("pool");
  static Dictionary<string,Sprite> CommonSnapshot(M46AtlasBank bank){
   var entries=(System.Collections.IDictionary)typeof(M46AtlasBank).GetField("sprites",Flags).GetValue(bank);var result=new Dictionary<string,Sprite>();
   foreach(string key in commonKeys){if(!entries.Contains(key))return null;var entry=entries[key];result.Add(key,(Sprite)entry.GetType().GetField("sprite").GetValue(entry));}return result;
  }
  static void CacheCheck(){
   var bank=Field<M46AtlasBank>("bank");bank.BeginFrame();
   foreach(int atlas in new[]{2,3,4,12}){var manifest=JsonUtility.FromJson<HeartOfTheRain.M05.SpriteManifest>(ui.boards.powerManifests[atlas].text);foreach(var clip in manifest.clips)for(int n=0;n<clip.count;n++){
    var d=new DrawSprite{bank="power",atlas=atlas,key=clip.name,age=(n+.1f)/clip.fps};bank.VerificationSkipCachedLookup=true;var slow=bank.Get(d);bank.VerificationSkipCachedLookup=false;var fast=bank.Get(d);Check(fast==slow,"Cached lookup preserves authored sprite "+atlas+"/"+clip.name+"/"+n);
   }}
   bank.EndFrame(false);
   var entries=(System.Collections.IDictionary)typeof(M46AtlasBank).GetField("sprites",Flags).GetValue(bank);
   var dBody=new DrawSprite{bank="body",key="tile0"};var body=bank.Get(dBody);var entry=entries["tile0"];var owner=entry.GetType().GetField("owner").GetValue(entry);
   Check(owner!=null,"Resource sprite retains texture ownership");int oldFrame=(int)entry.GetType().GetField("frame").GetValue(entry);owner.GetType().GetField("used").SetValue(owner,-100f);bank.BeginFrame();Check(bank.Get(dBody)==body,"Cache hit returns existing body");
   Check((int)entry.GetType().GetField("frame").GetValue(entry)==oldFrame+1,"Cache hit marks current frame");Check((float)owner.GetType().GetField("used").GetValue(owner)>=Time.unscaledTime-.001f,"Cache hit refreshes texture LRU age");
   int limit=bank.SpriteLimit;long budget=bank.TextureBudget;bank.SpriteLimit=0;bank.TextureBudget=0;bank.EndFrame(true);Check(entries.Contains("tile0")&&bank.Get(dBody)==body,"Visible cached body survives sprite/texture budget pressure");
   bank.BeginFrame();bank.EndFrame(true);Check(!entries.Contains("tile0"),"Old unpinned cached body is evicted under pressure");Check(bank.Get(dBody)!=body,"Evicted cached body is recreated safely");bank.SpriteLimit=limit;bank.TextureBudget=budget;
  }
  static void Check(bool ok,string name){report.checks++;if(!ok)throw new Exception(name);report.passed.Add(name);}
  static void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Assert||type==LogType.Exception)Finish(text+"\n"+stack);}
  static void WitnessStartup(){
   if(report.startupWitnessed)return;var trace=game.VerificationStartup;
   // A visible GameView may already have rendered the own camera, even if
   // compilation completed before the harness observes this request.
   if(trace.jobStartedFrame>0||trace.cameraWitnessFrame>0){RecordStartupWitness(false);return;}
   if(!game.VerificationStartupPending)return;
   // The fixture injects its powers after level warmup, so the prefix may
   // still be waiting for body textures. Retry after its real head is ready.
   if(Field<BoardStep>("current")==null&&!trace.held)return;
   Invoke("Render");Check(Field<int>("startupSubmitted79")==Time.frameCount,"Default startup submits its real head in the camera witness frame");
   var camera=Field<Camera>("view");var previous=camera.targetTexture;var active=RenderTexture.active;var target=new RenderTexture(720,1280,24);
   try{camera.targetTexture=target;camera.Render();}finally{camera.targetTexture=previous;RenderTexture.active=active;UnityEngine.Object.Destroy(target);}
   trace=game.VerificationStartup;Check(trace.cameraWitnessFrame==Time.frameCount&&trace.jobStartedFrame==Time.frameCount,"Explicit own-camera render witnesses startup and starts work in its actual frame");RecordStartupWitness(true);
  }
  static void RecordStartupWitness(bool offscreen){
   var trace=game.VerificationStartup;report.startupHeadSubmittedFrame=trace.headSubmittedFrame;report.startupCameraWitnessFrame=trace.cameraWitnessFrame;report.startupJobStartedFrame=trace.jobStartedFrame;
   report.startupWitnessed=trace.cameraWitnessFrame>0&&trace.cameraWitnessFrame==trace.jobStartedFrame;report.startupExplicitOffscreenWitness=offscreen;
   report.startupMode=offscreen?"default79-leading-swap-offscreen-own-camera":"default79-leading-swap-automatic-own-camera";
   Check(report.startupWitnessed&&trace.headSubmittedTicks>0&&trace.headSubmittedTicks<=trace.cameraWitnessTicks&&trace.cameraWitnessTicks<=trace.jobStartedTicks,"Actual own-camera onPostRender witnesses a submitted pose before starting managed work");
  }
  static void RenderCheck(){
   Invoke("Render");var view=Field<BoardPresentation>("presentation");var draws=view.SampleLive(Field<BoardStep>("current"),Field<BoardSnapshot>("idle"),Field<float>("clock"),Field<float>("started"));var bank=Field<M46AtlasBank>("bank");int i=0,batched=0;
   // Checkpoint 60: unmasked, non-glow effects draw through the mesh batcher, not pool renderers.
   var effects=Field<EffectMeshBatcher>("effects");bool batching=!game.VerificationUseSpriteRenderersForEffects&&effects!=null;
   foreach(var d in draws){var sprite=bank.Get(d);bank.VerificationSkipCachedLookup=true;Check(bank.Get(d)==sprite,"Cached body/obstacle/frame identity preserved");bank.VerificationSkipCachedLookup=false;if(!sprite||d.alpha<=0||d.uiOverlay)continue;if(batching&&!d.masked&&d.glow<=0){batched++;continue;}var sr=Pool()[i++];Check(sr.enabled&&sr.sprite==sprite,"Reload binds correct live sprite "+i);var pos=new Vector3(d.x-(game.Model.Level.columns-1)*.5f,d.y-(game.Model.Level.rows-1)*.5f,0);Check((sr.transform.localPosition-pos).sqrMagnitude<.000001f,"Reload resets old transform "+i);Check(sr.maskInteraction==(d.masked?SpriteMaskInteraction.VisibleInsideMask:SpriteMaskInteraction.None),"Reload resets old mask "+i);var block=new MaterialPropertyBlock();sr.GetPropertyBlock(block);Check(d.glow>0||block.GetFloat("_Glow")==0,"Reload clears old glow override "+i);}
   foreach(var sr in Pool().Skip(i))Check(!sr.enabled&&sr.sprite==null,"Unused retained renderer is hidden and releases its sprite");
   Check(!batching||effects.Quads==batched,"Batched effect quads equal the sampled unmasked non-glow draws ("+effects?.Quads+" vs "+batched+")");
  }
  static void Tick(){try{
   if(!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;if(EditorApplication.timeSinceStartup-at>180)throw new TimeoutException("Warmup phase "+phase);
   if(game&&phase==2){WitnessStartup();if(game.LastFrameCost.frame!=lastFrame){lastFrame=game.LastFrameCost.frame;Check(game.LastFrameCost.poolCreated==0,"Orb/Rocket playback uses prepared renderers frame "+lastFrame);}}
   switch(phase){
    case 0:var f=UnityEngine.Object.FindFirstObjectByType<FirstStartPage>();if(!f||!f.IsVisible)return;ui=f.assets.Gameplay;f.Request("skip");f.Request("skip");f.home.SetPresentation(false,false);game=new GameObject("Native warmup verification").AddComponent<GameplayScreen>();game.uiAssets=ui;game.showLevelIntro=false;game.MeasureFrameCosts=true;phase++;break;
    case 1:if(!game.CanAct)return;game.GetComponent<GameplayHUD>().ResultRequested=(won,level)=>true;report.initialPool=game.RendererPoolCount;Check(report.initialPool>=GameplayScreen.WarmRendererCapacity(9,9),"Renderer reserve ready before accepting input");var bank=Field<M46AtlasBank>("bank");Check(bank.SpriteCount>=352,"All352 common sprite frames prepared");RenderCheck();var source=game.Model.Pieces.Values.First(p=>p.family=="gem"&&game.Model.At(p.x+1,p.y)?.family=="gem");int x=source.x,y=source.y;game.Model.InjectReviewPower(x,y,7);game.Model.InjectReviewPower(x+1,y,4);var turn=game.Model.Swap(x,y,x+1,y);Check(turn.accepted,"Orb/Rocket accepted");expected=JsonUtility.ToJson(game.Model.Snapshot());Invoke("Accept",turn);report.startupMode="default79-leading-swap-awaiting-own-camera";Check(game.VerificationStartupPending&&game.VerificationStartup.eligible,"Warmup exercises the default leading-swap startup path");game.playbackSpeed=12;phase++;break;
    case 2:if(game.Busy)return;report.startupTrace=game.VerificationStartup;Check(report.startupWitnessed&&!game.VerificationStartupPending&&report.startupTrace.tailInstalledFrame>0,"Default startup tail installs after the actual camera witness");Check(JsonUtility.ToJson(game.Model.Snapshot())==expected,"Warm playback preserves solved state");Check(game.RendererPoolCount==report.initialPool,"Heavy turn does not grow renderer pool");ids=Pool().Select(s=>s.GetInstanceID()).ToArray();foreach(var sr in Pool()){sr.transform.localPosition=new Vector3(99,99,99);sr.maskInteraction=SpriteMaskInteraction.VisibleOutsideMask;var b=new MaterialPropertyBlock();b.SetFloat("_Glow",42);sr.SetPropertyBlock(b);}int index=Array.FindIndex(ui.boards.levels,t=>{var l=JsonUtility.FromJson<LevelData>(t.text);return l.columns==11&&l.rows==11;});Check(index>=0,"Authored larger board available");game.Load(index);Check(!game.CanAct&&!game.InitializationComplete,"Reload gate holds while preparing");Check(ids.SequenceEqual(Pool().Take(ids.Length).Select(s=>s.GetInstanceID())),"Reload retains existing renderer identities");phase++;break;
    case 3:if(!game.CanAct)return;report.retainedPool=game.RendererPoolCount;Check(report.retainedPool>=605,"Larger board prepares its bounded reserve");RenderCheck();ids=Pool().Select(s=>s.GetInstanceID()).ToArray();game.showLevelIntro=true;game.pendingStartingPowers=new[]{4,7,16};game.Load(0);Check(!game.CanAct,"Starting reveal waits for preparation");phase++;break;
    case 4:if(game.InitializationComplete)return;game.showLevelIntro=false;game.Load(0,0,"verification-retry-during-warmup");Check(!game.HasStartedWithPowers,"Retry cancels old starting grant");phase++;break;
    case 5:if(!game.CanAct)return;Check(ids.SequenceEqual(Pool().Select(s=>s.GetInstanceID())),"Interrupted preparation/retry retains pool without duplicates");var fresh=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[0].text));Check(JsonUtility.ToJson(game.Model.Snapshot())==JsonUtility.ToJson(fresh.Snapshot()),"Retry has fresh model and no delayed old grant");RenderCheck();CacheCheck();
     commonKeys=new[]{2,3,4,12}.SelectMany(atlas=>Enumerable.Range(0,JsonUtility.FromJson<HeartOfTheRain.M05.SpriteManifest>(ui.boards.powerManifests[atlas].text).frames.Length).Select(n=>"p/"+atlas+"/"+n)).ToArray();Check(commonKeys.Length==352,"Largest-board probe knows all352 common frame identities");largestCommon=null;largestObservedFrame=-1;report.largestWarmupLevel=30;game.Load(29);Check(!game.CanAct,"Largest-board input stays gated during real coroutine preparation");phase++;break;
    case 6:var largestBank=Field<M46AtlasBank>("bank");if(largestObservedFrame!=Time.frameCount){largestObservedFrame=Time.frameCount;report.largestWarmupFrames++;}
     if(largestCommon==null){var captured=CommonSnapshot(largestBank);if(captured!=null){largestCommon=captured;largestCaptureFrame=Time.frameCount;report.largestCommonCaptured=captured.Count;Check(!game.InitializationComplete&&largestBank.SpriteEvictions==0,"Actual Play Mode captures all common identities before obstacle-frame eviction or readiness");}}
     if(!game.CanAct)return;Check(largestCommon!=null&&Time.frameCount>largestCaptureFrame,"Actual largest-board warmup spans rendered frames after common capture");var retained=CommonSnapshot(largestBank);Check(retained!=null,"All common frames remain resident at actual Ready");report.largestCommonRetained=largestCommon.Count(p=>retained.ContainsKey(p.Key)&&ReferenceEquals(p.Value,retained[p.Key]));report.largestReadySpriteEvictions=largestBank.SpriteEvictions;Check(report.largestCommonRetained==352&&largestBank.SpriteEvictions==0,"Actual Play Mode retains the same352 native sprites through largest-board warmup");Check(largestBank.SpriteLimit==M46AtlasBank.WorkingSetSpriteLimit+largestBank.PinnedSprites,"Actual largest-board warmup keeps the approved final working budget");RenderCheck();Finish(null);break;
   }
  }catch(Exception e){Finish(e.ToString());}}
  static void Finish(string error){if(report==null||report.status!=null)return;report.status=error==null?"PASS_NATIVE_PRESENTATION_WARMUP":"FAIL_NATIVE_PRESENTATION_WARMUP";if(error!=null)report.failures.Add(error);SessionState.EraseBool(Key);EditorApplication.update-=Tick;Application.logMessageReceived-=Log;string dir=Path.GetFullPath("../Verification/Evidence/PowerWarmup");Directory.CreateDirectory(dir);File.WriteAllText(Path.Combine(dir,"Native_Checks.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(error==null?0:1);}
 }
}
#endif

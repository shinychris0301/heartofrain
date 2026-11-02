#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using UnityEngine.Profiling;
using UnityEngine.Scripting;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 public static class GameplayPerformanceVerification {
  [Serializable] public sealed class Row {public string name,poseSignature;public int maxDraws,history,samples;public float peakTime;public double millisecondsPerSample,coldSampleMs;public long bytesPerSample;}
  [Serializable] public sealed class AtlasRow {public string name;public int coldCreates,warmCreates,coldEvictions,warmEvictions,peakCachedSprites,draws;public long cachedTextureBytes,cachedSpriteRuntimeBytes;public double coldMilliseconds,warmMilliseconds;}
  [Serializable] public sealed class Report {public string utc,status,variant,allocationCounter,scope="Native Unity Editor sampler/atlas CPU microbenchmarks. Full draw signatures compare sampled poses; timings exclude GPU/display. Atlas sequence CPU includes synchronous first texture load and native Sprite.Create; counter differences identify cache churn. Mono heap fallback measures heap growth with GC temporarily disabled, not per-thread allocated bytes. Device measurements are separate.";public bool allocationCounterUsable;public long allocationPositiveControlBytes,threadCounterPositiveControlBytes,monoHeapPositiveControlBytes;public int checks;public List<string> failures=new List<string>();public List<Row> samplers=new List<Row>();public List<AtlasRow> atlases=new List<AtlasRow>();}
  static Report report;static GameplayUIAssets ui;static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
  public static void Baseline(){Measure("Before");}
  public static void Run(){Measure("After");}
  static void Check(bool ok,string name){report.checks++;if(!ok)report.failures.Add(name);}
  static BoardPresentation View(int columns,int rows){var view=new BoardPresentation{columns=columns,rows=rows};foreach(var p in ui.boards.debrisProfiles)view.profiles[p.family]=JsonUtility.FromJson<DebrisProfile>(p.metadata.text);return view;}
  static BoardSnapshot Gems(int columns,int rows){var pieces=new List<Piece>();for(int y=0;y<rows;y++)for(int x=0;x<columns;x++)pieces.Add(new Piece{id=y*columns+x+1,x=x,y=y,color=(x*3+y*5)%6,family="gem"});return new BoardSnapshot{pieces=pieces.ToArray(),goals=new Goal[0]};}
  static void Hash(ref ulong signature,int value){unchecked{signature^=(uint)value;signature*=1099511628211UL;}}
  static void Hash(ref ulong signature,string value){if(value==null){Hash(ref signature,-1);return;}foreach(char c in value)Hash(ref signature,c);Hash(ref signature,0);}
  static void Hash(ref ulong signature,DrawSprite d){Hash(ref signature,d.bank);Hash(ref signature,d.key);Hash(ref signature,d.atlas);Hash(ref signature,d.order);Hash(ref signature,d.pieceId);Hash(ref signature,d.age.GetHashCode());Hash(ref signature,d.x.GetHashCode());Hash(ref signature,d.y.GetHashCode());Hash(ref signature,d.sx.GetHashCode());Hash(ref signature,d.sy.GetHashCode());Hash(ref signature,d.angle.GetHashCode());Hash(ref signature,d.alpha.GetHashCode());Hash(ref signature,d.glow.GetHashCode());Hash(ref signature,d.red.GetHashCode());Hash(ref signature,d.green.GetHashCode());Hash(ref signature,d.blue.GetHashCode());Hash(ref signature,d.masked?1:0);Hash(ref signature,d.uiOverlay?1:0);}
  static void Sampler(string name,BoardStep step,int columns,int rows){
   var view=View(columns,rows);view.Add(step,0);var row=new Row{name=name,history=view.history.Count};var watch=Stopwatch.StartNew();view.SampleLive(step,step.before,0,0);watch.Stop();row.coldSampleMs=watch.Elapsed.TotalMilliseconds;
   ulong signature=14695981039346656037UL;const int poses=180;for(int n=0;n<=poses;n++){float at=step.duration*n/poses;var draws=view.SampleLive(step,step.before,at,0);Hash(ref signature,n);Hash(ref signature,draws.Count);foreach(var d in draws)Hash(ref signature,d);if(draws.Count>row.maxDraws){row.maxDraws=draws.Count;row.peakTime=at;}}
   row.poseSignature=signature.ToString("x16");for(int n=0;n<30;n++)view.SampleLive(step,step.before,row.peakTime,0);
   const int samples=512;var previous=GarbageCollector.GCMode;bool heap=report.allocationCounter=="MonoUsedHeapWithGCDisabled";if(heap)GarbageCollector.GCMode=GarbageCollector.Mode.Disabled;try{long bytes=Counter();watch.Restart();for(int n=0;n<samples;n++)view.SampleLive(step,step.before,row.peakTime,0);watch.Stop();row.millisecondsPerSample=watch.Elapsed.TotalMilliseconds/samples;row.bytesPerSample=report.allocationCounterUsable?(Counter()-bytes)/samples:-1;}finally{if(heap)GarbageCollector.GCMode=previous;}row.samples=samples;report.samplers.Add(row);
   Check(row.maxDraws>0&&row.millisecondsPerSample>=0,"Finite sampler "+name);
   if(report.variant=="After"&&report.allocationCounterUsable)Check(row.bytesPerSample==0,"Warmed sampler allocation budget "+name+": "+row.bytesPerSample);
  }
  static long Counter()=>report.allocationCounter=="MonoUsedHeapWithGCDisabled"?Profiler.GetMonoUsedSizeLong():GC.GetAllocatedBytesForCurrentThread();
  static void AllocationControl(){long before=GC.GetAllocatedBytesForCurrentThread();var allocation=new byte[65536];GC.KeepAlive(allocation);report.threadCounterPositiveControlBytes=GC.GetAllocatedBytesForCurrentThread()-before;if(report.threadCounterPositiveControlBytes>=65536){report.allocationCounterUsable=true;report.allocationCounter="GC.GetAllocatedBytesForCurrentThread";report.allocationPositiveControlBytes=report.threadCounterPositiveControlBytes;return;}var previous=GarbageCollector.GCMode;try{GC.Collect();GarbageCollector.GCMode=GarbageCollector.Mode.Disabled;before=Profiler.GetMonoUsedSizeLong();allocation=new byte[65536];report.monoHeapPositiveControlBytes=Profiler.GetMonoUsedSizeLong()-before;GC.KeepAlive(allocation);}catch(Exception){report.monoHeapPositiveControlBytes=-1;}finally{GarbageCollector.GCMode=previous;}if(report.monoHeapPositiveControlBytes>=65536){report.allocationCounterUsable=true;report.allocationCounter="MonoUsedHeapWithGCDisabled";report.allocationPositiveControlBytes=report.monoHeapPositiveControlBytes;}else report.allocationCounter="UNAVAILABLE";}
  static void DestroyBank(M46AtlasBank bank){var cache=(IDictionary)typeof(M46AtlasBank).GetField("sprites",Private).GetValue(bank);foreach(var entry in cache.Values){var sprite=(Sprite)entry.GetType().GetField("sprite").GetValue(entry);if(sprite)UnityEngine.Object.DestroyImmediate(sprite);}cache.Clear();bank.Dispose();}
  static void Atlas(string name,List<BoardStep> steps,int columns,int rows){
   var bank=new M46AtlasBank(ui.boards);try{var row=new AtlasRow{name=name};var watch=new Stopwatch();
    for(int pass=0;pass<2;pass++){int creates=bank.SpriteCreates,evictions=bank.SpriteEvictions;var view=View(columns,rows);float time=0;watch.Restart();foreach(var step in steps){view.Add(step,time);int frames=Math.Max(1,(int)Math.Ceiling(step.duration*30));for(int n=0;n<frames;n++){float at=time+step.duration*(n+.1f)/frames;bank.BeginFrame();view.PruneHistory(at);var draws=view.SampleLive(step,step.before,at,time);row.draws+=draws.Count;foreach(var d in draws)if(d.alpha>0)bank.Get(d);bank.EndFrame(false);}time+=step.duration;}watch.Stop();
     if(pass==0){row.coldCreates=bank.SpriteCreates-creates;row.coldEvictions=bank.SpriteEvictions-evictions;row.coldMilliseconds=watch.Elapsed.TotalMilliseconds;}else{row.warmCreates=bank.SpriteCreates-creates;row.warmEvictions=bank.SpriteEvictions-evictions;row.warmMilliseconds=watch.Elapsed.TotalMilliseconds;}
    }row.peakCachedSprites=bank.SpriteHighWaterMark;row.cachedTextureBytes=bank.TextureBytes;var spriteMemory=typeof(M46AtlasBank).GetProperty("CachedSpriteRuntimeBytes");row.cachedSpriteRuntimeBytes=spriteMemory==null?-1:(long)spriteMemory.GetValue(bank);report.atlases.Add(row);Check(row.cachedTextureBytes>0,"Atlas bytes tracked "+name);if(report.variant=="After")Check(row.warmCreates==0&&row.warmEvictions==0,"Repeated combo retains bounded sprite working set "+name);
    long sum=0;var textures=(IDictionary)typeof(M46AtlasBank).GetField("textures",Private).GetValue(bank);foreach(var entry in textures.Values)sum+=(long)entry.GetType().GetField("bytes").GetValue(entry);Check(sum==bank.TextureBytes,"Atlas tracked byte total equals entries "+name);
   }finally{DestroyBank(bank);}
  }
  static void CacheBudget(){var bank=new M46AtlasBank(ui.boards){SpriteLimit=16};try{bank.BeginFrame();bank.Whole("budget/pinned",Texture2D.whiteTexture,1,true);for(int n=0;n<64;n++){bank.BeginFrame();bank.Whole("budget/"+n,Texture2D.whiteTexture,1);bank.EndFrame(false);}Check(bank.SpriteCount>=2&&bank.SpriteCount<=bank.SpriteLimit,"Sprite cache enforces finite LRU budget");Check(bank.SpriteEvictions==65-bank.SpriteCount,"Sprite cache accounts for all evicted frames");var cache=(IDictionary)typeof(M46AtlasBank).GetField("sprites",Private).GetValue(bank);Check(cache.Contains("budget/pinned"),"Pinned sprite survives cache pressure");Check(cache.Contains("budget/63")&&!cache.Contains("budget/0"),"LRU retains recent frames and evicts oldest frames");bank.BeginFrame();for(int n=0;n<20;n++)bank.Whole("visible/"+n,Texture2D.whiteTexture,1);bank.EndFrame(false);Check(bank.SpriteCount==21,"Visible and pinned sprites survive active-frame pressure");bank.BeginFrame();bank.EndFrame(false);Check(bank.SpriteCount>=1&&bank.SpriteCount<=bank.SpriteLimit,"Cache returns to finite budget after visible pressure");}finally{DestroyBank(bank);}Check(bank.TextureBytes==0&&bank.SpriteCount==0,"Disposal clears owned cache counters");}
  static void Measure(string variant){
   report=new Report{utc=DateTime.UtcNow.ToString("o"),variant=variant};try{
    AllocationControl();
    ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
    foreach(var shape in new[]{new[]{9,9},new[]{9,11},new[]{11,11}})foreach(int kind in Enumerable.Range(0,22)){var snap=Gems(shape[0],shape[1]);var plan=ReviewPlan.Build(shape[0],shape[1],kind,new Vector2Int(4,4),false);Sampler("plan_"+kind+"_"+shape[0]+"x"+shape[1],new BoardStep{kind="power",before=snap,after=snap,powerPlan=plan,duration=plan.duration},shape[0],shape[1]);}
    foreach(int level in new[]{0,20,49})foreach(string kind in new[]{"three_rocket_chain","orb_rocket","golden_bomb"}){
     var board=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[level].text));Piece source,partner=null;if(kind=="three_rocket_chain"){var row=board.Pieces.Values.Where(p=>p.family=="gem").GroupBy(p=>p.y).First(g=>g.Count()>=3).OrderBy(p=>p.x).Take(3).ToArray();source=row[0];foreach(var p in row)board.InjectReviewPower(p.x,p.y,4);}else{source=board.Pieces.Values.First(p=>p.family=="gem"&&board.At(p.x+1,p.y)?.family=="gem");partner=board.At(source.x+1,source.y);board.InjectReviewPower(source.x,source.y,kind=="orb_rocket"?7:16);board.InjectReviewPower(partner.x,partner.y,kind=="orb_rocket"?4:21);}
     var turn=partner==null?board.Tap(source.x,source.y):board.Swap(source.x,source.y,partner.x,partner.y);Check(turn.accepted,"Real combo accepted "+level+kind);var steps=BoardPlayback.Build(turn.steps,board.Level);foreach(var s in steps.Where(s=>s.playbackTracks!=null))Sampler("live_L"+(level+1)+"_"+kind, s,board.Level.columns,board.Level.rows);if(level==0)Atlas(kind,steps,board.Level.columns,board.Level.rows);
    }
    var crystal=new Piece{id=1,x=0,y=0,family="crystal",hp=7};var crystalSnapshot=new BoardSnapshot{pieces=new[]{crystal},goals=new Goal[0]};Sampler("crystal_idle",new BoardStep{kind="settled",duration=2,before=crystalSnapshot,after=crystalSnapshot},9,9);
    if(variant=="After")CacheBudget();
    if(variant=="After"){string baseline=Path.GetFullPath("../Verification/Evidence/GameplayAudit/Before/Sampler_Atlas.json");Check(File.Exists(baseline),"Fresh native sampler baseline available");if(File.Exists(baseline)){var before=JsonUtility.FromJson<Report>(File.ReadAllText(baseline));foreach(var row in report.samplers.Where(r=>r.name.StartsWith("plan_",StringComparison.Ordinal)||r.name=="crystal_idle")){var old=before.samplers.FirstOrDefault(r=>r.name==row.name);Check(old!=null&&old.poseSignature==row.poseSignature,"Unchanged authored sampler poses "+row.name);}}}
   }catch(Exception error){report.failures.Add(error.ToString());}
   report.status=report.failures.Count==0?"PASS_NATIVE_GAMEPLAY_PERFORMANCE":"FAIL_NATIVE_GAMEPLAY_PERFORMANCE";string dir=Path.GetFullPath("../Verification/Evidence/GameplayAudit/"+variant);Directory.CreateDirectory(dir);File.WriteAllText(Path.Combine(dir,"Sampler_Atlas.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.failures.Count==0?0:1);
  }
 }
}
#endif

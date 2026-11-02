#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using Object=UnityEngine.Object;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 // Checkpoint 60: the effect mesh batcher must draw the same pixels as one
 // SpriteRenderer per effect, and must fold a dense burst into a few meshes
 // for every family the density fixtures break (crate, stone, sluice, tiles).
 public static class EffectBatchVerification {
  enum Plate {SpritesUnityOrder,SpritesListOrder,MeshExactOrder,MeshGrouped,MeshPrepared,MeshBaseline74,MeshBaseline75}
  [Serializable] public sealed class FamilyRow {public string family;public int obstacles,peakDraws,batchedDraws,quads,meshes,pooledSprites;public float peakAge;}
  [Serializable] public sealed class PreparationRow {public string name;public int snapshotSprites,preparedGeometry,preparedSlots,batches,yields,firstReplayGeometryMisses,firstReplaySlotCreates;public double milliseconds,maxBatchMilliseconds;}
  [Serializable] public sealed class ConstructionRow {
   public string name;public int draws,iterations,baselineMeshes,optimizedMeshes;
   public double baselineAddMedianMs,optimizedAddMedianMs,baselineAddP95Ms,optimizedAddP95Ms,baselineUploadMedianMs,optimizedUploadMedianMs,baselineFrameMedianMs,optimizedFrameMedianMs;
  }
  [Serializable] public sealed class ConstructionParityRow {public string name,baselineHash,optimizedHash;public int quads,meshes;public bool keepDrawOrder;}
  [Serializable] public sealed class TransformTimingRow {
   public string name;public int draws,zeroAngleDraws,nonzeroAngleDraws,iterations;
   public double baselineAddMedianMs,currentAddMedianMs,baselineAddP95Ms,currentAddP95Ms,baselineUploadMedianMs,currentUploadMedianMs,baselineFrameMedianMs,currentFrameMedianMs;
  }
  [Serializable] public sealed class TransformPixelRow {public string name;public int differingPixels,maxChannelDelta;}
  struct BatchInput {public Sprite sprite;public int order;public Vector3 position;public float angle,sx,sy;public Color color;}
  [Serializable] public sealed class Report {
   public string status,utc,error,scope="Native Unity Editor camera plates and batching statistics. Pixel comparison uses the same material, sprites and poses through both paths; GPU rendering is untimed. Not device frame pacing.";
   public string comparison="exact: a mesh per contiguous run (verification mode) against SpriteRenderers depth-stepped into list order, which proves quad geometry, UVs and colour. grouped: the live per-page meshes against the same list-order plate; the remainder is composition order among overlapping effects that share a sorting order, which the SpriteRenderer path never defined (unity: the grouped meshes against SpriteRenderers left to Unity's own tie-break).";
   public int checks,width=900,height=1600,draws,batchedDraws,quads,meshes,exactMeshes,comparedPixels;
   public int exactDifferingPixels,exactMaxChannelDelta,groupedDifferingPixels,groupedMaxChannelDelta,unityDifferingPixels,unityMaxChannelDelta;
   public int preparedDifferingPixels,preparedMaxChannelDelta,authoredPreparationPlans,largestPreparationLevel,largestPlannedFrames,futurePressureSprites;
   public int interleavedWarmupYields,interleavedCommonRetained,interleavedSpriteEvictions,historicalCapCommonRetained,historicalCapSpriteEvictions;
   public int optimizedBaselineDifferingPixels,optimizedBaselineMaxChannelDelta,constructionParityFrames;
   public int transformParityFrames;public string frozen75SourceSHA256,compiled75BodySHA256;
   public string transformScope="Exact archived75 uploaded mesh/pixel comparisons, with zero/nonzero/tiny angles, signed-zero coordinates/scales, flips, tint, shrink/regrow and ordered/fallback uploads. Vertex arithmetic remains unchanged and no float epsilon is accepted. Alternating warmed native CPU spans exclude sampling, lookup, rendering and GPU completion; zero-only/rotated variants change test poses only. No Android performance or universal improvement claim.";
   public string frozenBaselineSourceSHA256,compiledBaselineBodySHA256,constructionScope="Matched native Editor batch construction/upload CPU spans, precomputed sprite references, warmed caches and alternating execution order. Exact archived74 implementation is compiled only in Editor verification. Sampling, bank lookup, camera rendering and GPU completion are outside these spans; no Android frame-rate or end-to-end speedup claim.";
   public double exactDifferingShare,groupedDifferingShare,unityDifferingShare;
   public List<FamilyRow> families=new List<FamilyRow>();public List<string> frames=new List<string>();public List<PreparationRow> preparationRows=new List<PreparationRow>();
   public List<ConstructionRow> constructionRows=new List<ConstructionRow>();
   public List<ConstructionParityRow> constructionParityRows=new List<ConstructionParityRow>();
   public List<ConstructionParityRow> transformParityRows=new List<ConstructionParityRow>();public List<TransformTimingRow> transformRows=new List<TransformTimingRow>();public List<TransformPixelRow> transformPixelRows=new List<TransformPixelRow>();
  }
  static Report report;static GameplayUIAssets ui;static string output;
  static void Check(bool ok,string name){report.checks++;if(!ok)throw new Exception(name);}
  public static void Run(){
   report=new Report{utc=DateTime.UtcNow.ToString("o")};output=Path.GetFullPath("../Verification/Evidence/EffectBatch/Native");Directory.CreateDirectory(output);
   bool previousTransform=EffectMeshBatcher.VerificationUseCheckpoint75Transform;EffectMeshBatcher.VerificationUseCheckpoint75Transform=false;
   try{
    ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
    VerifyFrozenBaseline();VerifyFrozen75();
    // Peak of the level-42 Double Orb burst, as the crate-burst suite samples it.
    var b=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[41].text));var turn=CrateBurstVerification.Solve(b,"double_orb");Check(turn.accepted,"Peak turn accepted");
    var steps=BoardPlayback.Build(turn.steps,b.Level);var bank=new M46AtlasBank(ui.boards);
    try{
     CrateBurstVerification.Warm(bank,b.Snapshot());var load=typeof(M46AtlasBank).GetMethod("Texture",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic);foreach(var path in bank.RequiredResources(steps))load.Invoke(bank,new object[]{null,path});
     var peak=Peak(bank,steps,b.Level.columns,b.Level.rows);report.draws=peak.Count;
     var unity=Render(bank,b.Level,peak,Plate.SpritesUnityOrder,"Sprites.png");var listed=Render(bank,b.Level,peak,Plate.SpritesListOrder,"SpritesListOrder.png");
     var exact=Render(bank,b.Level,peak,Plate.MeshExactOrder,"MeshesExactOrder.png");var grouped=Render(bank,b.Level,peak,Plate.MeshGrouped,"Meshes.png");
     var prepared=Render(bank,b.Level,peak,Plate.MeshPrepared,"MeshesPrepared.png");
     var baseline=Render(bank,b.Level,peak,Plate.MeshBaseline74,"MeshesBaseline74.png");
     int max;
     report.exactDifferingPixels=Compare(listed,exact,"DifferenceExactOrder.png",out max);report.exactMaxChannelDelta=max;report.exactDifferingShare=(double)report.exactDifferingPixels/listed.Length;
     report.groupedDifferingPixels=Compare(listed,grouped,"Difference.png",out max);report.groupedMaxChannelDelta=max;report.groupedDifferingShare=(double)report.groupedDifferingPixels/listed.Length;
     report.unityDifferingPixels=Compare(unity,grouped,"DifferenceUnityOrder.png",out max);report.unityMaxChannelDelta=max;report.unityDifferingShare=(double)report.unityDifferingPixels/unity.Length;
     report.preparedDifferingPixels=Compare(grouped,prepared,"DifferencePrepared.png",out max);report.preparedMaxChannelDelta=max;
     report.optimizedBaselineDifferingPixels=Compare(baseline,grouped,"DifferenceBaseline74.png",out max);report.optimizedBaselineMaxChannelDelta=max;
     Check(report.optimizedBaselineDifferingPixels==0&&max==0,"Optimized grouped meshes retain every archived74 pixel/channel exactly");
     Check(report.preparedDifferingPixels==0,"Prepared meshes retain cold grouped pixels exactly within the existing two-channel tolerance");
     PreparationLifecycle(bank);
     ConstructionProof("level42_double_orb_peak",bank,peak);
     report.comparedPixels=listed.Length;
     Check(report.batchedDraws>0&&report.quads==report.batchedDraws,"Every unmasked non-glow draw became one quad");
     Check(report.meshes>=1&&report.meshes<=32,"A dense burst folds into a bounded number of meshes: "+report.meshes);
     Check(report.exactMeshes>=report.meshes,"Exact-order meshes are at least the grouped count");
     Check(report.exactDifferingShare<=.0025,"Exact-order mesh plate matches the list-order SpriteRenderer plate: "+report.exactDifferingPixels+" of "+report.comparedPixels+" pixels differ ("+(report.exactDifferingShare*100).ToString("0.00")+"%), max channel delta "+report.exactMaxChannelDelta);
     Check(report.groupedDifferingShare<=.05,"Grouped mesh plate differs from the list-order plate only where equal-order effects overlap: "+report.groupedDifferingPixels+" of "+report.comparedPixels+" pixels differ ("+(report.groupedDifferingShare*100).ToString("0.00")+"%)");
     TransformPixels75(bank,b.Level,peak,grouped);
    }finally{Dispose(bank);}
    // Every density family at its densest fixture batches cleanly.
    var source=JsonUtility.FromJson<LevelData>(ui.boards.levels[25].text);
    foreach(var family in ObstacleDensityFixture.Families){
     var level=ObstacleDensityFixture.Level(source,45,family);var board=new BoardModel(level);var t=ObstacleDensityFixture.Solve(board);Check(t.accepted,"Density fixture accepted "+family);
     var built=BoardPlayback.Build(t.steps,level);var familyBank=new M46AtlasBank(ui.boards);
     try{
      CrateBurstVerification.Warm(familyBank,board.Snapshot());var load=typeof(M46AtlasBank).GetMethod("Texture",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic);foreach(var path in familyBank.RequiredResources(built))load.Invoke(familyBank,new object[]{null,path});
      float age;var draws=Peak(familyBank,built,level.columns,level.rows,out age);
      var root=new GameObject("Family batch").transform;var batcher=new EffectMeshBatcher(root,ui.boards.effectsMaterial,new Bounds(Vector3.zero,new Vector3(64,64,2)));
      try{
       batcher.Begin();int pooled=0,batched=0;foreach(var d in draws){var sprite=familyBank.Get(d);if(!sprite||d.alpha<=0||d.uiOverlay)continue;if(d.masked||d.glow>0){pooled++;continue;}batched++;batcher.Add(sprite,d.order,new Vector3(d.x,d.y,0),d.angle,d.sx,d.sy,new Color(d.red,d.green,d.blue,d.alpha));}
       batcher.End();
       var row=new FamilyRow{family=family,obstacles=level.obstacles.Count(o=>o.family==family),peakDraws=draws.Count,batchedDraws=batched,quads=batcher.Quads,meshes=batcher.Meshes,pooledSprites=pooled,peakAge=age};report.families.Add(row);
       Check(row.quads==row.batchedDraws&&row.meshes>=1&&row.meshes<=32,"Family "+family+" batches its peak: "+row.batchedDraws+" draws into "+row.meshes+" meshes");
       int vertices=0;foreach(var filter in root.GetComponentsInChildren<MeshFilter>())if(filter.GetComponent<MeshRenderer>().enabled)vertices+=filter.sharedMesh.vertexCount;
       Check(vertices==row.quads*4,"Family "+family+" mesh vertex count matches quads");
       ConstructionProof("density_"+family+"_45_peak",familyBank,draws);
      }finally{batcher.Dispose();UnityEngine.Object.DestroyImmediate(root.gameObject);}
     }finally{Dispose(familyBank);}
    }
    LargestPreparation();
    Check(report.transformParityFrames==65&&report.transformParityRows.Count==65&&report.transformRows.Count==15&&report.transformPixelRows.Count==2,"All five archived75 transform fixtures,65 upload states,15 paired timing rows and2 strict pixel controls completed");
    report.status="PASS_NATIVE_EFFECT_BATCH";
   }catch(Exception e){report.status="FAIL_NATIVE_EFFECT_BATCH";report.error=e.ToString();}finally{EffectMeshBatcher.VerificationUseCheckpoint75Transform=previousTransform;}
   File.WriteAllText(Path.Combine(output,"Report.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.error==null?0:1);
  }
  static string Hash(byte[] bytes){using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
  static void VerifyFrozenBaseline(){
   var originalPath=Path.GetFullPath("../.verification-cache/Gameplay75/BaselineSources/Unity/Assets/HeartOfTheRain/M47/Runtime/EffectMeshBatcher.cs");
   report.frozenBaselineSourceSHA256=Hash(File.ReadAllBytes(originalPath));
   Check(report.frozenBaselineSourceSHA256=="fa4a2ceb07d12f7835143a01216cfc2009aa6695d7b0fe39bdccf5bf2aebea97","Native control binds exact archived74 batcher source");
   var original=File.ReadAllText(originalPath).Replace("\r\n","\n");original=original.Substring(original.IndexOf("namespace HeartOfTheRain.M47 {",StringComparison.Ordinal)).Trim();
   original=original.Replace("namespace HeartOfTheRain.M47 {","namespace HeartOfTheRain.Verification.Baseline74 {").Replace("EffectMeshBatcher","ArchivedEffectMeshBatcher74");
   var current=File.ReadAllText("Assets/HeartOfTheRain/Verification/Editor/EffectBatchVerification.cs").Replace("\r\n","\n");
   const string begin="\n// BEGIN FROZEN_CHECKPOINT74_EFFECT_BATCHER\n",end="\n// END FROZEN_CHECKPOINT74_EFFECT_BATCHER";
   int start=current.IndexOf(begin,StringComparison.Ordinal)+begin.Length,finish=current.IndexOf(end,StringComparison.Ordinal);Check(start>=begin.Length&&finish>start,"Compiled native control region exists");
   var compiled=current.Substring(start,finish-start).Trim();Check(compiled==original,"Compiled native control is byte-for-byte archived74 body apart from namespace/type rename");report.compiledBaselineBodySHA256=Hash(Encoding.UTF8.GetBytes(compiled));
  }
  static void VerifyFrozen75(){
   var path=Path.GetFullPath("../.verification-cache/Gameplay76/BaselineSources/Unity/Assets/HeartOfTheRain/M47/Runtime/EffectMeshBatcher.cs");report.frozen75SourceSHA256=Hash(File.ReadAllBytes(path));Check(report.frozen75SourceSHA256=="346d1a40be8df1fad764b66f00f1aa167b802be8f97d77c0a7e15427f81e2371","Native transform control binds exact archived75 source");
   var original=File.ReadAllText(path).Replace("\r\n","\n");original=original.Substring(original.IndexOf("namespace HeartOfTheRain.M47 {",StringComparison.Ordinal)).Trim().Replace("namespace HeartOfTheRain.M47 {","namespace HeartOfTheRain.Verification.Baseline75 {").Replace("EffectMeshBatcher","ArchivedEffectMeshBatcher75");
   var own=File.ReadAllText("Assets/HeartOfTheRain/Verification/Editor/EffectBatchVerification.cs").Replace("\r\n","\n");const string begin="\n// BEGIN FROZEN_CHECKPOINT75_EFFECT_BATCHER\n",end="\n// END FROZEN_CHECKPOINT75_EFFECT_BATCHER";int start=own.IndexOf(begin,StringComparison.Ordinal)+begin.Length,finish=own.IndexOf(end,StringComparison.Ordinal);Check(start>=begin.Length&&finish>start,"Compiled archived75 region exists");var compiled=own.Substring(start,finish-start).Trim();Check(compiled==original,"Compiled transform control matches archived75 body except namespace/type rename");report.compiled75BodySHA256=Hash(Encoding.UTF8.GetBytes(compiled));
  }
  static void Vector(BinaryWriter writer,Vector3 v){writer.Write(v.x);writer.Write(v.y);writer.Write(v.z);}
  static string MeshSignature(Transform root){
   using(var bytes=new MemoryStream())using(var writer=new BinaryWriter(bytes)){
    foreach(var filter in root.GetComponentsInChildren<MeshFilter>()){
     var renderer=filter.GetComponent<MeshRenderer>();if(!renderer.enabled)continue;
     var mesh=filter.sharedMesh;writer.Write(renderer.sortingOrder);writer.Write(renderer.sharedMaterial.GetInstanceID());
     var block=new MaterialPropertyBlock();renderer.GetPropertyBlock(block);var texture=block.GetTexture(Shader.PropertyToID("_MainTex"));writer.Write(texture?texture.GetInstanceID():0);
     Vector(writer,filter.transform.localPosition);Vector(writer,mesh.bounds.center);Vector(writer,mesh.bounds.size);
     var vertices=mesh.vertices;writer.Write(vertices.Length);foreach(var v in vertices)Vector(writer,v);
     var uv=mesh.uv;writer.Write(uv.Length);foreach(var v in uv){writer.Write(v.x);writer.Write(v.y);}
     var colors=mesh.colors32;writer.Write(colors.Length);foreach(var c in colors){writer.Write(c.r);writer.Write(c.g);writer.Write(c.b);writer.Write(c.a);}
     var triangles=mesh.triangles;writer.Write(triangles.Length);foreach(var i in triangles)writer.Write(i);
    }
    writer.Flush();return Hash(bytes.ToArray());
   }
  }
  static void Replay(EffectMeshBatcher batcher,BatchInput[] inputs){batcher.Begin();foreach(var d in inputs)batcher.Add(d.sprite,d.order,d.position,d.angle,d.sx,d.sy,d.color);batcher.End();}
  static void Replay(Baseline74.ArchivedEffectMeshBatcher74 batcher,BatchInput[] inputs){batcher.Begin();foreach(var d in inputs)batcher.Add(d.sprite,d.order,d.position,d.angle,d.sx,d.sy,d.color);batcher.End();}
  static void Parity(string name,EffectMeshBatcher optimized,Baseline74.ArchivedEffectMeshBatcher74 baseline,Transform optimizedRoot,Transform baselineRoot,BatchInput[] inputs,bool ordered=false){
   optimized.KeepDrawOrder=baseline.KeepDrawOrder=ordered;Replay(baseline,inputs);Replay(optimized,inputs);
   string a=MeshSignature(baselineRoot),b=MeshSignature(optimizedRoot);Check(a==b&&baseline.Quads==optimized.Quads&&baseline.Meshes==optimized.Meshes,"All uploaded vertices/UV/colors/indices/material/texture/order/depth/bounds match archived74: "+name);
   report.constructionParityFrames++;report.constructionParityRows.Add(new ConstructionParityRow{name=name,baselineHash=a,optimizedHash=b,quads=optimized.Quads,meshes=optimized.Meshes,keepDrawOrder=ordered});
  }
  static double Ms(long ticks)=>ticks*1000.0/System.Diagnostics.Stopwatch.Frequency;
  static void Timed(EffectMeshBatcher batcher,BatchInput[] inputs,List<double> add,List<double> upload,List<double> full){
   long begin=System.Diagnostics.Stopwatch.GetTimestamp();batcher.Begin();foreach(var d in inputs)batcher.Add(d.sprite,d.order,d.position,d.angle,d.sx,d.sy,d.color);long built=System.Diagnostics.Stopwatch.GetTimestamp();batcher.End();long done=System.Diagnostics.Stopwatch.GetTimestamp();add.Add(Ms(built-begin));upload.Add(Ms(done-built));full.Add(Ms(done-begin));
  }
  static void Timed(Baseline74.ArchivedEffectMeshBatcher74 batcher,BatchInput[] inputs,List<double> add,List<double> upload,List<double> full){
   long begin=System.Diagnostics.Stopwatch.GetTimestamp();batcher.Begin();foreach(var d in inputs)batcher.Add(d.sprite,d.order,d.position,d.angle,d.sx,d.sy,d.color);long built=System.Diagnostics.Stopwatch.GetTimestamp();batcher.End();long done=System.Diagnostics.Stopwatch.GetTimestamp();add.Add(Ms(built-begin));upload.Add(Ms(done-built));full.Add(Ms(done-begin));
  }
  static double Percentile(List<double> values,double p){var sorted=values.OrderBy(x=>x).ToArray();return sorted[Math.Min(sorted.Length-1,(int)Math.Ceiling(sorted.Length*p)-1)];}
  static void ConstructionProof(string name,M46AtlasBank bank,List<DrawSprite> draws){
   var inputs=new List<BatchInput>();foreach(var d in draws){var sprite=bank.Get(d);if(!sprite||d.alpha<=0||d.uiOverlay||d.masked||d.glow>0)continue;inputs.Add(new BatchInput{sprite=sprite,order=d.order,position=new Vector3(d.x,d.y,0),angle=d.angle,sx=d.sx,sy=d.sy,color=new Color(d.red,d.green,d.blue,d.alpha)});}var full=inputs.ToArray();Check(full.Length>0,"Native benchmark contains real effect sprites: "+name);
   var optimizedRoot=new GameObject("Optimized construction").transform;var baselineRoot=new GameObject("Archived74 construction").transform;var bounds=new Bounds(Vector3.zero,new Vector3(64,64,2));
   var optimized=new EffectMeshBatcher(optimizedRoot,ui.boards.effectsMaterial,bounds);var baseline=new Baseline74.ArchivedEffectMeshBatcher74(baselineRoot,ui.boards.effectsMaterial,bounds);
   try{
    var snapshot=bank.CachedEffectSpritesSnapshot();Drain(optimized.Prepare(snapshot));Drain(baseline.Prepare(snapshot));
    Parity(name+"/full",optimized,baseline,optimizedRoot,baselineRoot,full);
    Parity(name+"/shrink",optimized,baseline,optimizedRoot,baselineRoot,full.Take(1).ToArray());
    Parity(name+"/empty",optimized,baseline,optimizedRoot,baselineRoot,new BatchInput[0]);
    Parity(name+"/regrow",optimized,baseline,optimizedRoot,baselineRoot,full);
    Parity(name+"/reverse",optimized,baseline,optimizedRoot,baselineRoot,full.Reverse().ToArray());
    var varied=full.Take(16).ToArray();for(int i=0;i<varied.Length;i++){varied[i].order=i%2==0?int.MinValue:int.MaxValue;varied[i].angle=i%3==0?0:i*23.75f;varied[i].sx=i%2==0?-1:0;varied[i].sy=.5f+i*.03f;varied[i].color=new Color(.25f,.75f,1,.5f);}
    Parity(name+"/signed_orders_transforms",optimized,baseline,optimizedRoot,baselineRoot,varied);
    var fallback=new BatchInput[EffectMeshBatcher.PreparedSlotReserve+5];for(int i=0;i<fallback.Length;i++){fallback[i]=full[i%full.Length];fallback[i].order=i;}
    Parity(name+"/beyond_reserve",optimized,baseline,optimizedRoot,baselineRoot,fallback);
    Check(optimized.Meshes==fallback.Length&&optimized.SlotCount>=fallback.Length,"Retained topology keeps demand fallback beyond32 slots");
    Parity(name+"/ordered_runs",optimized,baseline,optimizedRoot,baselineRoot,fallback,true);
    optimized.KeepDrawOrder=baseline.KeepDrawOrder=false;for(int i=0;i<4;i++){Replay(baseline,full);Replay(optimized,full);}
    const int iterations=64;var a=new List<double>(iterations);var b=new List<double>(iterations);var au=new List<double>(iterations);var bu=new List<double>(iterations);var af=new List<double>(iterations);var bf=new List<double>(iterations);
    for(int i=0;i<iterations;i++)if(i%2==0){Timed(baseline,full,a,au,af);Timed(optimized,full,b,bu,bf);}else{Timed(optimized,full,b,bu,bf);Timed(baseline,full,a,au,af);}
    report.constructionRows.Add(new ConstructionRow{name=name,draws=full.Length,iterations=iterations,baselineMeshes=baseline.Meshes,optimizedMeshes=optimized.Meshes,baselineAddMedianMs=Percentile(a,.5),optimizedAddMedianMs=Percentile(b,.5),baselineAddP95Ms=Percentile(a,.95),optimizedAddP95Ms=Percentile(b,.95),baselineUploadMedianMs=Percentile(au,.5),optimizedUploadMedianMs=Percentile(bu,.5),baselineFrameMedianMs=Percentile(af,.5),optimizedFrameMedianMs=Percentile(bf,.5)});
    Parity(name+"/after_benchmark",optimized,baseline,optimizedRoot,baselineRoot,full);
    TransformProof75(name,bank,full);
   }finally{optimized.Dispose();baseline.Dispose();Check(optimized.SlotCount==0&&optimized.GeometryCount==0&&baseline.SlotCount==0&&baseline.GeometryCount==0,"Both native implementations release managed cache/slot ownership: "+name);UnityEngine.Object.DestroyImmediate(optimizedRoot.gameObject);UnityEngine.Object.DestroyImmediate(baselineRoot.gameObject);}
  }
  static void Replay(Baseline75.ArchivedEffectMeshBatcher75 batcher,BatchInput[] inputs){batcher.Begin();foreach(var d in inputs)batcher.Add(d.sprite,d.order,d.position,d.angle,d.sx,d.sy,d.color);batcher.End();}
  static void Timed(Baseline75.ArchivedEffectMeshBatcher75 batcher,BatchInput[] inputs,List<double> add,List<double> upload,List<double> full){
   long begin=System.Diagnostics.Stopwatch.GetTimestamp();batcher.Begin();foreach(var d in inputs)batcher.Add(d.sprite,d.order,d.position,d.angle,d.sx,d.sy,d.color);long built=System.Diagnostics.Stopwatch.GetTimestamp();batcher.End();long done=System.Diagnostics.Stopwatch.GetTimestamp();add.Add(Ms(built-begin));upload.Add(Ms(done-built));full.Add(Ms(done-begin));
  }
  static void TransformParity75(string name,EffectMeshBatcher current,Baseline75.ArchivedEffectMeshBatcher75 baseline,Transform currentRoot,Transform baselineRoot,BatchInput[] inputs,bool ordered=false){
   current.KeepDrawOrder=baseline.KeepDrawOrder=ordered;Replay(baseline,inputs);Replay(current,inputs);string a=MeshSignature(baselineRoot),b=MeshSignature(currentRoot);Check(a==b&&baseline.Quads==current.Quads&&baseline.Meshes==current.Meshes,"Bit-exact archived75 upload/UV/color/indices/material/order/depth: "+name);report.transformParityFrames++;report.transformParityRows.Add(new ConstructionParityRow{name=name,baselineHash=a,optimizedHash=b,quads=current.Quads,meshes=current.Meshes,keepDrawOrder=ordered});
  }
  static void TransformProof75(string name,M46AtlasBank bank,BatchInput[] full){
   var currentRoot=new GameObject("Current zero-angle construction").transform;var baselineRoot=new GameObject("Archived75 construction").transform;var bounds=new Bounds(Vector3.zero,new Vector3(64,64,2));var current=new EffectMeshBatcher(currentRoot,ui.boards.effectsMaterial,bounds);var baseline=new Baseline75.ArchivedEffectMeshBatcher75(baselineRoot,ui.boards.effectsMaterial,bounds);bool previous=EffectMeshBatcher.VerificationUseCheckpoint75Transform;
   try{
    EffectMeshBatcher.VerificationUseCheckpoint75Transform=false;var snapshot=bank.CachedEffectSpritesSnapshot();Drain(current.Prepare(snapshot));Drain(baseline.Prepare(snapshot));
    var zero=full.ToArray();for(int i=0;i<zero.Length;i++)zero[i].angle=0;
    float negativeZero=BitConverter.ToSingle(new byte[]{0,0,0,128},0);var signed=full.Take(32).ToArray();for(int i=0;i<signed.Length;i++){signed[i].angle=i%2==0?0:negativeZero;signed[i].position=new Vector3(i%2==0?negativeZero:0,i%3==0?negativeZero:0,0);signed[i].sx=i%3==0?negativeZero:i%3==1?0:-1;signed[i].sy=i%2==0?-1:negativeZero;signed[i].color=new Color(.2f,.7f,1.2f,.55f);}
    var tiny=full.Take(32).ToArray();for(int i=0;i<tiny.Length;i++)tiny[i].angle=new[]{float.Epsilon,-float.Epsilon,.000001f,-.000001f}[i%4];
    var mixed=full.Take(32).ToArray();for(int i=0;i<mixed.Length;i++){mixed[i].angle=i%3==0?0:(i%2==0?-1:1)*(13.75f+i*19.125f);mixed[i].sx=i%4==0?-1:i%4==1?0:.35f+i*.05f;mixed[i].sy=i%3==0?-.75f:1.25f;mixed[i].color=new Color(.25f+i*.01f,.7f,.9f,.4f+i*.01f);}
    TransformParity75(name+"/actual",current,baseline,currentRoot,baselineRoot,full);
    TransformParity75(name+"/all_zero",current,baseline,currentRoot,baselineRoot,zero);
    TransformParity75(name+"/signed_zero_scales_positions",current,baseline,currentRoot,baselineRoot,signed);
    TransformParity75(name+"/tiny_nonzero_angles",current,baseline,currentRoot,baselineRoot,tiny);
    TransformParity75(name+"/mixed_rotation_scale_tint",current,baseline,currentRoot,baselineRoot,mixed);
    TransformParity75(name+"/shrink",current,baseline,currentRoot,baselineRoot,zero.Take(1).ToArray());
    TransformParity75(name+"/empty",current,baseline,currentRoot,baselineRoot,new BatchInput[0]);
    TransformParity75(name+"/regrow",current,baseline,currentRoot,baselineRoot,zero);
    TransformParity75(name+"/reverse",current,baseline,currentRoot,baselineRoot,zero.Reverse().ToArray());
    var fallback=new BatchInput[EffectMeshBatcher.PreparedSlotReserve+5];for(int i=0;i<fallback.Length;i++){fallback[i]=mixed[i%mixed.Length];fallback[i].order=i;}
    TransformParity75(name+"/ordered_runs",current,baseline,currentRoot,baselineRoot,fallback,true);
    TransformParity75(name+"/beyond_reserve",current,baseline,currentRoot,baselineRoot,fallback);
    EffectMeshBatcher.VerificationUseCheckpoint75Transform=true;TransformParity75(name+"/same_apk_legacy_math",current,baseline,currentRoot,baselineRoot,mixed);EffectMeshBatcher.VerificationUseCheckpoint75Transform=false;
    current.KeepDrawOrder=baseline.KeepDrawOrder=false;
    foreach(string mode in new[]{"actual","all_zero","all_rotated"}){
     var inputs=mode=="all_zero"?zero:full.ToArray();if(mode=="all_rotated")for(int i=0;i<inputs.Length;i++)inputs[i].angle=11.25f+i%31;
     for(int warm=0;warm<4;warm++){Replay(baseline,inputs);Replay(current,inputs);}const int iterations=64;var a=new List<double>();var b=new List<double>();var au=new List<double>();var bu=new List<double>();var af=new List<double>();var bf=new List<double>();
     for(int i=0;i<iterations;i++)if(i%2==0){Timed(baseline,inputs,a,au,af);Timed(current,inputs,b,bu,bf);}else{Timed(current,inputs,b,bu,bf);Timed(baseline,inputs,a,au,af);}
     report.transformRows.Add(new TransformTimingRow{name=name+"/"+mode,draws=inputs.Length,zeroAngleDraws=inputs.Count(d=>d.angle==0),nonzeroAngleDraws=inputs.Count(d=>d.angle!=0),iterations=iterations,baselineAddMedianMs=Percentile(a,.5),currentAddMedianMs=Percentile(b,.5),baselineAddP95Ms=Percentile(a,.95),currentAddP95Ms=Percentile(b,.95),baselineUploadMedianMs=Percentile(au,.5),currentUploadMedianMs=Percentile(bu,.5),baselineFrameMedianMs=Percentile(af,.5),currentFrameMedianMs=Percentile(bf,.5)});
    }
    TransformParity75(name+"/after_benchmark",current,baseline,currentRoot,baselineRoot,full);
   }finally{EffectMeshBatcher.VerificationUseCheckpoint75Transform=previous;current.Dispose();baseline.Dispose();Check(current.SlotCount==0&&current.GeometryCount==0&&baseline.SlotCount==0&&baseline.GeometryCount==0,"Archived75/current transform proof releases ownership: "+name);UnityEngine.Object.DestroyImmediate(currentRoot.gameObject);UnityEngine.Object.DestroyImmediate(baselineRoot.gameObject);}
  }
  static void TransformPixels75(M46AtlasBank bank,LevelData level,List<DrawSprite> peak,Color32[] currentActual){
   var baseline=Render(bank,level,peak,Plate.MeshBaseline75,"MeshesBaseline75.png");int max;int different=Compare(baseline,currentActual,"DifferenceBaseline75.png",out max);Check(different==0&&max==0,"Archived75 actual effect pixels are exactly identical");report.transformPixelRows.Add(new TransformPixelRow{name="actual_peak",differingPixels=different,maxChannelDelta=max});
   var mixed=peak.Select(d=>d.Copy()).ToList();int n=0;foreach(var d in mixed)if(!d.masked&&!d.uiOverlay&&d.glow<=0&&d.alpha>0){d.angle=n%3==0?0:n%2==0?-37.25f:53.125f;d.sx*=n%4==0?-1:n%4==1?0:.7f;d.sy*=n%2==0?-.8f:1.2f;d.red*=.6f;d.green*=.8f;d.alpha*=.65f;n++;}
   var old=Render(bank,level,mixed,Plate.MeshBaseline75,"TransformsBaseline75.png");var updated=Render(bank,level,mixed,Plate.MeshGrouped,"TransformsCurrent76.png");different=Compare(old,updated,"DifferenceTransforms75.png",out max);Check(different==0&&max==0,"Archived75 zero/rotated/flipped/scaled/tinted pixels are exactly identical");report.transformPixelRows.Add(new TransformPixelRow{name="mixed_zero_rotation_flip_scale_tint",differingPixels=different,maxChannelDelta=max});
  }
  static void Drain(IEnumerator routine){while(routine.MoveNext())Check(routine.Current==null,"Effect preparation yields only for completed CPU-budget batches");}
  static PreparationRow Prepared(string name,EffectMeshBatcher batcher,int snapshot)=>new PreparationRow{name=name,snapshotSprites=snapshot,preparedGeometry=batcher.PreparedGeometryCount,preparedSlots=batcher.PreparedSlotCount,batches=batcher.PreparationBatches,yields=batcher.PreparationYields,milliseconds=batcher.PreparationMilliseconds,maxBatchMilliseconds=batcher.PreparationMaxBatchMilliseconds};
  static void PreparationLifecycle(M46AtlasBank bank){
   var snapshot=bank.CachedEffectSpritesSnapshot();Check(snapshot.Length>0&&snapshot.Length<=EffectMeshBatcher.PreparedGeometryLimit,"Cached effect snapshot is nonempty and bounded");
   var root=new GameObject("Prepared effect lifecycle").transform;var batcher=new EffectMeshBatcher(root,ui.boards.effectsMaterial,new Bounds(Vector3.zero,new Vector3(64,64,2)));
   try{
    int textures=bank.TextureCount,created=bank.SpriteCreates,loads=bank.SynchronousLoads;Drain(batcher.Prepare(snapshot));var row=Prepared("snapshot_replay_and_slot_fallback",batcher,snapshot.Length);report.preparationRows.Add(row);
    Check(bank.TextureCount==textures&&bank.SpriteCreates==created&&bank.SynchronousLoads==loads,"Preparation does not load textures or create native sprites");
    Check(batcher.GeometryCount==snapshot.Length&&batcher.SlotCount==EffectMeshBatcher.PreparedSlotReserve,"Geometry and disabled slot reserve are complete before first replay");
    Check(root.GetComponentsInChildren<MeshRenderer>().All(r=>!r.enabled),"All prepared slots start disabled");
    batcher.Begin();foreach(var sprite in snapshot)batcher.Add(sprite,40,Vector3.zero,0,1,1,Color.white);batcher.End();
    row.firstReplayGeometryMisses=batcher.GeometryMisses;row.firstReplaySlotCreates=batcher.SlotCreates;Check(batcher.GeometryMisses==0,"First replay of prepared native sprites has no geometry misses");
    batcher.Begin();batcher.End();Check(root.GetComponentsInChildren<MeshRenderer>().All(r=>!r.enabled),"An empty following frame disables every used/reserved slot");
    var alreadyReady=batcher.Prepare(new Sprite[0],0);Check(!alreadyReady.MoveNext(),"No-work preparation has no minimum frame delay");
    int demand=Math.Max(batcher.SlotCount,EffectMeshBatcher.PreparedSlotReserve)+5;
    batcher.KeepDrawOrder=true;batcher.Begin();for(int i=0;i<demand;i++)batcher.Add(snapshot[0],i,Vector3.zero,0,1,1,Color.white);batcher.End();
    Check(batcher.Meshes==demand&&batcher.SlotCount>=batcher.Meshes&&batcher.SlotCreates>=5,"Demand path grows beyond existing/prepared slots without dropping quads");
   }finally{batcher.Dispose();Check(batcher.GeometryCount==0&&batcher.SlotCount==0,"Disposal releases all prepared managed ownership");UnityEngine.Object.DestroyImmediate(root.gameObject);}
   // Distinct native sprites share an existing texture: this stresses the
   // geometry bound without inventing an artwork or texture dependency.
   var sprites=new List<Sprite>();root=new GameObject("Prepared geometry pressure").transform;batcher=new EffectMeshBatcher(root,ui.boards.effectsMaterial,new Bounds(Vector3.zero,new Vector3(64,64,2)));
   try{
    int pressure=1400,total=EffectMeshBatcher.PreparedGeometryLimit+pressure;var texture=snapshot[0].texture;
    for(int i=0;i<total;i++)sprites.Add(Sprite.Create(texture,new Rect(0,0,1,1),new Vector2(.5f,.5f),64,0,SpriteMeshType.FullRect));
    Drain(batcher.Prepare(sprites.ToArray(),0));report.preparationRows.Add(Prepared("geometry_headroom",batcher,sprites.Count));
    Check(batcher.GeometryCount==EffectMeshBatcher.PreparedGeometryLimit,"Oversized snapshot stops at the preparation ceiling");
    batcher.Begin();foreach(var sprite in sprites.Skip(EffectMeshBatcher.PreparedGeometryLimit))batcher.Add(sprite,40,Vector3.zero,0,1,1,Color.white);batcher.End();
    Check(batcher.GeometryCount==total,"Future unprepared sprites still grow the live geometry cache");report.futurePressureSprites=pressure;
    batcher.Begin();batcher.Add(sprites[0],40,Vector3.zero,0,1,1,Color.white);batcher.End();Check(batcher.GeometryMisses==0&&batcher.GeometryCount==total,"Prepared geometry survives an additional 1,400 distinct future power-like frames");
    var cancelledRoot=new GameObject("Cancelled effect preparation").transform;var cancelled=new EffectMeshBatcher(cancelledRoot,ui.boards.effectsMaterial,new Bounds(Vector3.zero,new Vector3(64,64,2)));
    // This synchronous Editor case proves partial reservation/disposal only.
    // Actual StopAllCoroutines retry behavior is covered by warmup Play Mode cases4/5.
    try{var routine=cancelled.Prepare(sprites.ToArray(),EffectMeshBatcher.PreparedSlotReserve,.1);Check(routine.MoveNext(),"Real preparation can yield before completion");Check(cancelledRoot.GetComponentsInChildren<MeshRenderer>().All(r=>!r.enabled),"Partly reserved slots never become visible");((IDisposable)routine).Dispose();cancelled.Dispose();Check(cancelled.GeometryCount==0&&cancelled.SlotCount==0,"Partial preparation disposal releases managed ownership");}
    finally{cancelled.Dispose();UnityEngine.Object.DestroyImmediate(cancelledRoot.gameObject);}
   }finally{batcher.Dispose();UnityEngine.Object.DestroyImmediate(root.gameObject);foreach(var sprite in sprites)UnityEngine.Object.DestroyImmediate(sprite);}
  }
  static void LargestPreparation(){
   var counts=ui.boards.obstacleClips.ToDictionary(c=>c.key,c=>JsonUtility.FromJson<ClipData>(c.metadata.text).frames.Length);int common=0;foreach(int atlas in new[]{2,3,4,12})common+=JsonUtility.FromJson<HeartOfTheRain.M05.SpriteManifest>(ui.boards.powerManifests[atlas].text).frames.Length;
   LevelData largest=null;int planned=-1;
   foreach(var text in ui.boards.levels){var level=JsonUtility.FromJson<LevelData>(text.text);var families=new HashSet<string>(level.obstacles.Select(o=>o.family));int frames=common+counts.Where(c=>families.Any(f=>c.Key.StartsWith(f+"/",StringComparison.Ordinal))).Sum(c=>c.Value);report.authoredPreparationPlans++;if(frames>planned){planned=frames;largest=level;}}
   Check(report.authoredPreparationPlans==50&&largest!=null,"All 50 authored preparation frame plans inspected");report.largestPreparationLevel=largest.globalLevel;report.largestPlannedFrames=planned;
   var bank=new M46AtlasBank(ui.boards);var root=new GameObject("Largest authored effect preparation").transform;var batcher=new EffectMeshBatcher(root,ui.boards.effectsMaterial,new Bounds(Vector3.zero,new Vector3(64,64,2)));
   try{WarmInterleaved(bank,new BoardModel(largest).Snapshot(),false);var full=bank.CachedEffectSpritesSnapshot(int.MaxValue);var snapshot=bank.CachedEffectSpritesSnapshot();Check(full.Length==planned,"Largest authored cached effect set matches its real metadata plan");int textures=bank.TextureCount,loads=bank.SynchronousLoads;Drain(batcher.Prepare(snapshot));report.preparationRows.Add(Prepared("largest_authored_level_"+largest.globalLevel,batcher,full.Length));Check(batcher.GeometryCount<=EffectMeshBatcher.PreparedGeometryLimit&&bank.TextureCount==textures&&bank.SynchronousLoads==loads,"Largest authored preparation remains bounded without new resources");batcher.Begin();foreach(var sprite in snapshot)batcher.Add(sprite,40,Vector3.zero,0,1,1,Color.white);batcher.End();Check(batcher.GeometryMisses==0,"Largest authored prepared subset survives the next Begin without a full cache flush");}
   finally{batcher.Dispose();UnityEngine.Object.DestroyImmediate(root.gameObject);Dispose(bank);}
   var control=new M46AtlasBank(ui.boards);try{WarmInterleaved(control,new BoardModel(largest).Snapshot(),true);}finally{Dispose(control);}
  }
  static void WarmInterleaved(M46AtlasBank bank,BoardSnapshot snapshot,bool historicalCap){
   var load=typeof(M46AtlasBank).GetMethod("Texture",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic);foreach(var path in bank.CommonResources(snapshot))load.Invoke(bank,new object[]{null,path});
   Drain(bank.WarmCommonFrames());var common=bank.CachedEffectSpritesSnapshot(int.MaxValue);Check(common.Length==352,"All common native sprite identities captured before obstacle preparation");
   var warm=bank.WarmObstacleFrames(snapshot,48);int yields=0;
   while(warm.MoveNext()){
    Check(warm.Current==null,"Actual native obstacle iterator yields at a frame boundary");yields++;bank.BeginFrame();
    // Controlled counterexample: reproduce only the old budget at each real
    // EndFrame call. This is native bank interleaving, not a Play Mode claim.
    if(historicalCap)bank.SpriteLimit=M46AtlasBank.WorkingSetSpriteLimit;
    bank.EndFrame(false);
   }
   var resident=new HashSet<Sprite>(bank.CachedEffectSpritesSnapshot(int.MaxValue));int retained=common.Count(resident.Contains);
   if(historicalCap){report.historicalCapCommonRetained=retained;report.historicalCapSpriteEvictions=bank.SpriteEvictions;Check(retained<352&&bank.SpriteEvictions>0,"Holding the old2048 cap across native yields reproduces common-frame eviction");}
   else{report.interleavedWarmupYields=yields;report.interleavedCommonRetained=retained;report.interleavedSpriteEvictions=bank.SpriteEvictions;Check(yields>0&&retained==352&&bank.SpriteEvictions==0,"Incremental pinned budget retains all original common identities across native frame-end interleaving");Check(bank.SpriteLimit==M46AtlasBank.WorkingSetSpriteLimit+bank.PinnedSprites,"Incremental budget ends at the original final pinned-plus-working cap");}
  }
  static List<DrawSprite> Peak(M46AtlasBank bank,List<BoardStep> steps,int columns,int rows){float age;return Peak(bank,steps,columns,rows,out age);}
  static List<DrawSprite> Peak(M46AtlasBank bank,List<BoardStep> steps,int columns,int rows,out float peakAge){
   var v=CrateBurstVerification.View(ui,columns,rows);float start=0;List<DrawSprite> peak=null;peakAge=0;
   foreach(var step in steps){v.Add(step,start);int count=Math.Max(1,Mathf.CeilToInt(step.duration*30));for(int frame=0;frame<count;frame++){float t=start+step.duration*(frame+.1f)/count;bank.BeginFrame();v.PruneHistory(t);var draws=v.SampleLive(step,step.before,t,start);if(peak==null||draws.Count>peak.Count){peak=draws.Select(d=>d.Copy()).ToList();peakAge=t;}bank.EndFrame(false);}start+=step.duration;}
   return peak;
  }
  // Same camera and poses as the crate-burst plate; effects use the live
  // effects material in every plate so only the drawing path differs.
  static Color32[] Render(M46AtlasBank bank,LevelData level,List<DrawSprite> draws,Plate plate,string name){
   var root=new GameObject(plate.ToString());root.transform.position=new Vector3(1000,0,0);var previous=RenderTexture.active;var target=new RenderTexture(report.width,report.height,24);Material body=null;EffectMeshBatcher batcher=null;Baseline74.ArchivedEffectMeshBatcher74 baseline=null;Baseline75.ArchivedEffectMeshBatcher75 baseline75=null;
   bool mesh=plate==Plate.MeshExactOrder||plate==Plate.MeshGrouped||plate==Plate.MeshPrepared||plate==Plate.MeshBaseline74||plate==Plate.MeshBaseline75;
   try{
    var cam=new GameObject("Camera").AddComponent<Camera>();cam.transform.SetParent(root.transform,false);cam.transform.localPosition=new Vector3((level.columns-1)*.5f,(level.rows-1)*.5f,-10);cam.orthographic=true;cam.orthographicSize=BoardPresentation.CameraHalfHeight(level.columns,level.rows,(float)report.width/report.height);cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=new Color(.035f,.05f,.07f);cam.targetTexture=target;
    body=new Material(ui.bodyShader?ui.bodyShader:Shader.Find("Sprites/Default"));var effects=ui.boards.effectsMaterial;
    if(plate==Plate.MeshBaseline74){baseline=new Baseline74.ArchivedEffectMeshBatcher74(root.transform,effects,new Bounds(new Vector3((level.columns-1)*.5f,(level.rows-1)*.5f,0),new Vector3(level.columns+16,level.rows+20,2)));Drain(baseline.Prepare(bank.CachedEffectSpritesSnapshot()));baseline.Begin();}
    else if(plate==Plate.MeshBaseline75){baseline75=new Baseline75.ArchivedEffectMeshBatcher75(root.transform,effects,new Bounds(new Vector3((level.columns-1)*.5f,(level.rows-1)*.5f,0),new Vector3(level.columns+16,level.rows+20,2)));Drain(baseline75.Prepare(bank.CachedEffectSpritesSnapshot()));baseline75.Begin();}
    else if(mesh){batcher=new EffectMeshBatcher(root.transform,effects,new Bounds(new Vector3((level.columns-1)*.5f,(level.rows-1)*.5f,0),new Vector3(level.columns+16,level.rows+20,2))){KeepDrawOrder=plate==Plate.MeshExactOrder};
     if(plate==Plate.MeshPrepared){var snapshot=bank.CachedEffectSpritesSnapshot();int textures=bank.TextureCount,created=bank.SpriteCreates,loads=bank.SynchronousLoads;Drain(batcher.Prepare(snapshot));Check(bank.TextureCount==textures&&bank.SpriteCreates==created&&bank.SynchronousLoads==loads,"Effect geometry preparation uses only already-owned sprites/textures");Check(root.GetComponentsInChildren<MeshRenderer>().All(r=>!r.enabled),"Reserved mesh slots remain hidden before first draw");report.preparationRows.Add(Prepared("approved_peak",batcher,snapshot.Length));}
     batcher.Begin();}
    int batched=0;
    foreach(var d in draws){var sprite=bank.Get(d);if(!sprite||d.alpha<=0||d.uiOverlay)continue;bool effect=!d.masked&&d.glow<=0;
     if(mesh&&effect){if(baseline!=null)baseline.Add(sprite,d.order,new Vector3(d.x,d.y,0),d.angle,d.sx,d.sy,new Color(d.red,d.green,d.blue,d.alpha));else if(baseline75!=null)baseline75.Add(sprite,d.order,new Vector3(d.x,d.y,0),d.angle,d.sx,d.sy,new Color(d.red,d.green,d.blue,d.alpha));else batcher.Add(sprite,d.order,new Vector3(d.x,d.y,0),d.angle,d.sx,d.sy,new Color(d.red,d.green,d.blue,d.alpha));batched++;continue;}
     // The list-order control composes sprites in list order through the same depth step the batcher
     // uses; the Unity-order control leaves equal sorting orders to Unity's undefined tie-break, as the
     // SpriteRenderer path always did.
     var sr=new GameObject(d.key).AddComponent<SpriteRenderer>();sr.transform.SetParent(root.transform,false);sr.transform.localPosition=new Vector3(d.x,d.y,plate==Plate.SpritesListOrder?-.001f*(batched+1):0);sr.transform.localScale=new Vector3(d.sx,d.sy,1);sr.transform.localRotation=Quaternion.Euler(0,0,d.angle);sr.sprite=sprite;sr.sharedMaterial=effect?effects:body;sr.sortingOrder=d.order;sr.color=new Color(d.red,d.green,d.blue,d.alpha);if(!mesh&&effect)batched++;}
    if(baseline!=null){baseline.End();Check(baseline.Quads==batched,"Archived74 native plate preserves every effect quad");}
    else if(baseline75!=null){baseline75.End();Check(baseline75.Quads==batched,"Archived75 native plate preserves every effect quad");}
    else if(mesh){batcher.End();if(plate==Plate.MeshGrouped){report.batchedDraws=batched;report.quads=batcher.Quads;report.meshes=batcher.Meshes;}else if(plate==Plate.MeshExactOrder){Check(batcher.Quads==batched,"Exact-order batcher made one quad per effect");report.exactMeshes=batcher.Meshes;}else{Check(batcher.Quads==batched,"Prepared plate preserves one quad per effect");var row=report.preparationRows.Last();row.firstReplayGeometryMisses=batcher.GeometryMisses;row.firstReplaySlotCreates=batcher.SlotCreates;}}
    cam.Render();RenderTexture.active=target;var pixels=new Texture2D(report.width,report.height,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,report.width,report.height),0,0);pixels.Apply();
    File.WriteAllBytes(Path.Combine(output,name),pixels.EncodeToPNG());report.frames.Add(name);var result=pixels.GetPixels32();UnityEngine.Object.DestroyImmediate(pixels);return result;
   }finally{RenderTexture.active=previous;batcher?.Dispose();baseline?.Dispose();baseline75?.Dispose();UnityEngine.Object.DestroyImmediate(root);if(body)UnityEngine.Object.DestroyImmediate(body);UnityEngine.Object.DestroyImmediate(target);}
  }
  static int Compare(Color32[] a,Color32[] b,string name,out int max){
   Check(a.Length==b.Length,"Plates have equal size");var diff=new Texture2D(report.width,report.height,TextureFormat.RGBA32,false);var pixels=new Color32[a.Length];int differing=0;max=0;
   for(int i=0;i<a.Length;i++){int d=Math.Max(Math.Max(Math.Abs(a[i].r-b[i].r),Math.Abs(a[i].g-b[i].g)),Math.Max(Math.Abs(a[i].b-b[i].b),Math.Abs(a[i].a-b[i].a)));max=Math.Max(max,d);bool differs=d>2;if(differs)differing++;pixels[i]=differs?new Color32(255,0,0,255):new Color32((byte)(a[i].r/3),(byte)(a[i].g/3),(byte)(a[i].b/3),255);}
   diff.SetPixels32(pixels);diff.Apply();File.WriteAllBytes(Path.Combine(output,name),diff.EncodeToPNG());report.frames.Add(name);UnityEngine.Object.DestroyImmediate(diff);return differing;
  }
  static void Dispose(M46AtlasBank bank){var cache=(System.Collections.IDictionary)typeof(M46AtlasBank).GetField("sprites",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic).GetValue(bank);foreach(var entry in cache.Values){var s=(Sprite)entry.GetType().GetField("sprite").GetValue(entry);if(s)UnityEngine.Object.DestroyImmediate(s);}cache.Clear();bank.Dispose();}
 }
}

// BEGIN FROZEN_CHECKPOINT74_EFFECT_BATCHER
namespace HeartOfTheRain.Verification.Baseline74 {
    // Draws one frame's unmasked, non-glow effect sprites (fragments, accents,
    // tile breaks, power clips) as a few procedural meshes instead of one
    // SpriteRenderer each. Geometry, UVs, material, sorting order and colour
    // match the SpriteRenderer path exactly; one mesh per texture page and
    // sorting order, so a dense burst costs a handful of renderers instead
    // of hundreds.
    public sealed class ArchivedEffectMeshBatcher74 {
        // Preparation is bounded; later effects still grow through the same
        // demand path. Leave headroom under the existing 4,096-entry cache flush.
        public const int PreparedGeometryLimit=2048,PreparedSlotReserve=32;
        // Verification only: one mesh per contiguous run instead of per page,
        // which keeps exact list order at the cost of many more meshes.
        public bool KeepDrawOrder;
        sealed class Slot {
            public GameObject node;public MeshFilter filter;public MeshRenderer renderer;public Mesh mesh;public MaterialPropertyBlock block;
            public Texture2D texture;public int order=int.MinValue;public bool enabled;
            public readonly List<Vector3> vertices=new List<Vector3>(512);public readonly List<Vector2> uvs=new List<Vector2>(512);
            public readonly List<Color32> colors=new List<Color32>(512);public readonly List<int> triangles=new List<int>(768);
        }
        // A sprite's quad in its own units, as SpriteRenderer builds it: rect
        // corners relative to the pivot, divided by pixels per unit.
        sealed class SpriteGeometry {public Texture2D texture;public float left,right,bottom,top;public Vector2 uvMin,uvMax;}
        static readonly int MainTexture=Shader.PropertyToID("_MainTex");
        readonly Transform root;readonly Material material;readonly Bounds bounds;
        readonly List<Slot> slots=new List<Slot>();readonly Dictionary<Sprite,SpriteGeometry> geometry=new Dictionary<Sprite,SpriteGeometry>();
        // One mesh per (texture, sorting order) per frame, in order of first
        // appearance. Within a mesh the quads keep draw order; sprites that
        // share a sorting order but not a texture page compose in page order,
        // which the SpriteRenderer path never defined either.
        readonly Dictionary<long,Slot> open=new Dictionary<long,Slot>();
        Slot current;Texture2D currentTexture;int currentOrder=int.MinValue,used;
        public int Quads {get;private set;}
        public int Meshes=>used;
        public int SlotCount=>slots.Count;
        public int GeometryCount=>geometry.Count;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        public int GeometryMisses {get;private set;}
        public int SlotCreates {get;private set;}
        public int PreparedGeometryCount {get;private set;}
        public int PreparedSlotCount {get;private set;}
        public int PreparationBatches {get;private set;}
        public int PreparationYields {get;private set;}
        public double PreparationMilliseconds {get;private set;}
        public double PreparationMaxBatchMilliseconds {get;private set;}
#endif
        public ArchivedEffectMeshBatcher74(Transform root,Material material,Bounds bounds){this.root=root;this.material=material;this.bounds=bounds;}
        public void Begin(){
            used=0;current=null;currentTexture=null;currentOrder=int.MinValue;Quads=0;open.Clear();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            GeometryMisses=SlotCreates=0;
#endif
            // Sprites the bank evicted stay as keys; bound the cache instead of tracking them.
            if(geometry.Count>4096)geometry.Clear();
        }
        SpriteGeometry Geometry(Sprite sprite){
            SpriteGeometry g;
            if(!geometry.TryGetValue(sprite,out g)){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                GeometryMisses++;
#endif
                var rect=sprite.textureRect;var texture=sprite.texture;float ppu=sprite.pixelsPerUnit;var pivot=sprite.pivot;
                g=new SpriteGeometry{texture=texture,left=-pivot.x/ppu,right=(rect.width-pivot.x)/ppu,bottom=-pivot.y/ppu,top=(rect.height-pivot.y)/ppu,
                    uvMin=new Vector2(rect.xMin/texture.width,rect.yMin/texture.height),uvMax=new Vector2(rect.xMax/texture.width,rect.yMax/texture.height)};
                geometry.Add(sprite,g);
            }
            return g;
        }
        // The bank has already copied these references before this iterator can
        // yield. Reading quad geometry never requests a texture or changes its
        // residency. Actual work, rather than a fixed frame count, gates readiness.
        public IEnumerator Prepare(Sprite[] cachedSprites,int reserve=PreparedSlotReserve,double budgetMilliseconds=2){
            int count=cachedSprites==null?0:System.Math.Min(PreparedGeometryLimit,cachedSprites.Length);
            reserve=System.Math.Max(0,reserve);budgetMilliseconds=System.Math.Max(.1,budgetMilliseconds);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            int geometryBefore=geometry.Count,slotsBefore=slots.Count;
            PreparedGeometryCount=PreparedSlotCount=PreparationBatches=PreparationYields=0;
            PreparationMilliseconds=PreparationMaxBatchMilliseconds=0;
#endif
            var watch=System.Diagnostics.Stopwatch.StartNew();bool worked=false;
            for(int i=0;i<count;i++){
                var sprite=cachedSprites[i];
                if(sprite!=null&&(geometry.Count<PreparedGeometryLimit||geometry.ContainsKey(sprite))){Geometry(sprite);worked=true;}
                if(worked&&(i+1<count||slots.Count<reserve)&&watch.Elapsed.TotalMilliseconds>=budgetMilliseconds){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    RecordPreparationBatch(watch.Elapsed.TotalMilliseconds);PreparationYields++;
#endif
                    yield return null;watch.Restart();worked=false;
                }
            }
            while(slots.Count<reserve){
                CreateSlot();worked=true;
                if(slots.Count<reserve&&watch.Elapsed.TotalMilliseconds>=budgetMilliseconds){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    RecordPreparationBatch(watch.Elapsed.TotalMilliseconds);PreparationYields++;
#endif
                    yield return null;watch.Restart();worked=false;
                }
            }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(worked)RecordPreparationBatch(watch.Elapsed.TotalMilliseconds);
            PreparedGeometryCount=geometry.Count-geometryBefore;PreparedSlotCount=slots.Count-slotsBefore;
#endif
        }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        void RecordPreparationBatch(double milliseconds){PreparationBatches++;PreparationMilliseconds+=milliseconds;PreparationMaxBatchMilliseconds=System.Math.Max(PreparationMaxBatchMilliseconds,milliseconds);}
#endif
        public void Add(Sprite sprite,int order,Vector3 position,float angle,float sx,float sy,Color color){
            var g=Geometry(sprite);
            if(current==null||currentTexture!=g.texture||currentOrder!=order){
                long key=((long)g.texture.GetInstanceID()<<32)^(uint)order;
                if(KeepDrawOrder)current=Open(g.texture,order);
                else if(!open.TryGetValue(key,out current)){current=Open(g.texture,order);open.Add(key,current);}
                currentTexture=g.texture;currentOrder=order;
            }
            float radians=angle*Mathf.Deg2Rad,cos=Mathf.Cos(radians),sin=Mathf.Sin(radians);
            float l=g.left*sx,r=g.right*sx,b=g.bottom*sy,t=g.top*sy;int v=current.vertices.Count;
            current.vertices.Add(new Vector3(position.x+l*cos-b*sin,position.y+l*sin+b*cos,0));
            current.vertices.Add(new Vector3(position.x+l*cos-t*sin,position.y+l*sin+t*cos,0));
            current.vertices.Add(new Vector3(position.x+r*cos-t*sin,position.y+r*sin+t*cos,0));
            current.vertices.Add(new Vector3(position.x+r*cos-b*sin,position.y+r*sin+b*cos,0));
            current.uvs.Add(new Vector2(g.uvMin.x,g.uvMin.y));current.uvs.Add(new Vector2(g.uvMin.x,g.uvMax.y));current.uvs.Add(new Vector2(g.uvMax.x,g.uvMax.y));current.uvs.Add(new Vector2(g.uvMax.x,g.uvMin.y));
            Color32 c=color;current.colors.Add(c);current.colors.Add(c);current.colors.Add(c);current.colors.Add(c);
            current.triangles.Add(v);current.triangles.Add(v+1);current.triangles.Add(v+2);current.triangles.Add(v);current.triangles.Add(v+2);current.triangles.Add(v+3);
            Quads++;
        }
        Slot CreateSlot(){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            SlotCreates++;
#endif
                var slot=new Slot{node=new GameObject("Effect mesh "+slots.Count)};slot.node.transform.SetParent(root,false);
                slot.filter=slot.node.AddComponent<MeshFilter>();slot.renderer=slot.node.AddComponent<MeshRenderer>();
                slot.mesh=new Mesh{name="Effect mesh"};slot.mesh.MarkDynamic();slot.mesh.bounds=bounds;slot.filter.sharedMesh=slot.mesh;
                slot.renderer.sharedMaterial=material;slot.renderer.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;slot.renderer.receiveShadows=false;
                slot.renderer.lightProbeUsage=UnityEngine.Rendering.LightProbeUsage.Off;slot.renderer.reflectionProbeUsage=UnityEngine.Rendering.ReflectionProbeUsage.Off;slot.renderer.motionVectorGenerationMode=MotionVectorGenerationMode.ForceNoMotion;
                slot.block=new MaterialPropertyBlock();slot.renderer.enabled=false;slots.Add(slot);return slot;
        }
        Slot Open(Texture2D texture,int order){
            var slot=used<slots.Count?slots[used]:CreateSlot();
            // Later runs sit a hair nearer the orthographic camera so equal
            // sorting orders still draw in list order.
            slot.node.transform.localPosition=new Vector3(0,0,-.001f*(used+1));
            if(slot.texture!=texture){slot.texture=texture;slot.block.SetTexture(MainTexture,texture);slot.renderer.SetPropertyBlock(slot.block);}
            if(slot.order!=order){slot.order=order;slot.renderer.sortingOrder=order;}
            slot.vertices.Clear();slot.uvs.Clear();slot.colors.Clear();slot.triangles.Clear();
            used++;return slot;
        }
        public void End(){
            for(int i=0;i<used;i++){
                var slot=slots[i];var mesh=slot.mesh;mesh.Clear(false);
                mesh.SetVertices(slot.vertices);mesh.SetUVs(0,slot.uvs);mesh.SetColors(slot.colors);mesh.SetTriangles(slot.triangles,0,false);mesh.bounds=bounds;
                if(!slot.enabled){slot.renderer.enabled=true;slot.enabled=true;}
            }
            for(int i=used;i<slots.Count;i++)if(slots[i].enabled){slots[i].renderer.enabled=false;slots[i].enabled=false;}
        }
        public void Dispose(){
            foreach(var slot in slots){if(slot.mesh)Object.Destroy(slot.mesh);if(slot.node)Object.Destroy(slot.node);}
            slots.Clear();geometry.Clear();used=0;current=null;Quads=0;
        }
    }
}
// END FROZEN_CHECKPOINT74_EFFECT_BATCHER

// BEGIN FROZEN_CHECKPOINT75_EFFECT_BATCHER
namespace HeartOfTheRain.Verification.Baseline75 {
    // Draws one frame's unmasked, non-glow effect sprites (fragments, accents,
    // tile breaks, power clips) as a few procedural meshes instead of one
    // SpriteRenderer each. Geometry, UVs, material, sorting order and colour
    // match the SpriteRenderer path exactly; one mesh per texture page and
    // sorting order, so a dense burst costs a handful of renderers instead
    // of hundreds.
    public sealed class ArchivedEffectMeshBatcher75 {
        // Preparation is bounded; later effects still grow through the same
        // demand path. Leave headroom under the existing 4,096-entry cache flush.
        public const int PreparedGeometryLimit=2048,PreparedSlotReserve=32;
        // Verification only: one mesh per contiguous run instead of per page,
        // which keeps exact list order at the cost of many more meshes.
        public bool KeepDrawOrder;
        sealed class Slot {
            public GameObject node;public MeshFilter filter;public MeshRenderer renderer;public Mesh mesh;public MaterialPropertyBlock block;
            public Texture2D texture;public int order=int.MinValue,indexCount;public bool enabled;
            public readonly List<Vector3> vertices=new List<Vector3>(512);public readonly List<Vector2> uvs=new List<Vector2>(512);
            public readonly List<Color32> colors=new List<Color32>(512);public readonly List<int> triangles=new List<int>(768);
        }
        // A sprite's quad in its own units, as SpriteRenderer builds it: rect
        // corners relative to the pivot, divided by pixels per unit.
        sealed class SpriteGeometry {public Texture2D texture;public int textureId;public float left,right,bottom,top;public Vector2 uvMin,uvMax;}
        static readonly int MainTexture=Shader.PropertyToID("_MainTex");
        readonly Transform root;readonly Material material;readonly Bounds bounds;
        readonly List<Slot> slots=new List<Slot>();readonly Dictionary<Sprite,SpriteGeometry> geometry=new Dictionary<Sprite,SpriteGeometry>();
        // One mesh per (texture, sorting order) per frame, in order of first
        // appearance. Within a mesh the quads keep draw order; sprites that
        // share a sorting order but not a texture page compose in page order,
        // which the SpriteRenderer path never defined either.
        readonly Dictionary<long,Slot> open=new Dictionary<long,Slot>();
        Slot current;long currentKey;int used;
        public int Quads {get;private set;}
        public int Meshes=>used;
        public int SlotCount=>slots.Count;
        public int GeometryCount=>geometry.Count;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        public int GeometryMisses {get;private set;}
        public int SlotCreates {get;private set;}
        public int PreparedGeometryCount {get;private set;}
        public int PreparedSlotCount {get;private set;}
        public int PreparationBatches {get;private set;}
        public int PreparationYields {get;private set;}
        public double PreparationMilliseconds {get;private set;}
        public double PreparationMaxBatchMilliseconds {get;private set;}
#endif
        public ArchivedEffectMeshBatcher75(Transform root,Material material,Bounds bounds){this.root=root;this.material=material;this.bounds=bounds;}
        public void Begin(){
            used=0;current=null;currentKey=0;Quads=0;open.Clear();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            GeometryMisses=SlotCreates=0;
#endif
            // Sprites the bank evicted stay as keys; bound the cache instead of tracking them.
            if(geometry.Count>4096)geometry.Clear();
        }
        SpriteGeometry Geometry(Sprite sprite){
            SpriteGeometry g;
            if(!geometry.TryGetValue(sprite,out g)){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                GeometryMisses++;
#endif
                var rect=sprite.textureRect;var texture=sprite.texture;float ppu=sprite.pixelsPerUnit;var pivot=sprite.pivot;
                g=new SpriteGeometry{texture=texture,textureId=texture.GetInstanceID(),left=-pivot.x/ppu,right=(rect.width-pivot.x)/ppu,bottom=-pivot.y/ppu,top=(rect.height-pivot.y)/ppu,
                    uvMin=new Vector2(rect.xMin/texture.width,rect.yMin/texture.height),uvMax=new Vector2(rect.xMax/texture.width,rect.yMax/texture.height)};
                geometry.Add(sprite,g);
            }
            return g;
        }
        // The bank has already copied these references before this iterator can
        // yield. Reading quad geometry never requests a texture or changes its
        // residency. Actual work, rather than a fixed frame count, gates readiness.
        public IEnumerator Prepare(Sprite[] cachedSprites,int reserve=PreparedSlotReserve,double budgetMilliseconds=2){
            int count=cachedSprites==null?0:System.Math.Min(PreparedGeometryLimit,cachedSprites.Length);
            reserve=System.Math.Max(0,reserve);budgetMilliseconds=System.Math.Max(.1,budgetMilliseconds);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            int geometryBefore=geometry.Count,slotsBefore=slots.Count;
            PreparedGeometryCount=PreparedSlotCount=PreparationBatches=PreparationYields=0;
            PreparationMilliseconds=PreparationMaxBatchMilliseconds=0;
#endif
            var watch=System.Diagnostics.Stopwatch.StartNew();bool worked=false;
            for(int i=0;i<count;i++){
                var sprite=cachedSprites[i];
                if(sprite!=null&&(geometry.Count<PreparedGeometryLimit||geometry.ContainsKey(sprite))){Geometry(sprite);worked=true;}
                if(worked&&(i+1<count||slots.Count<reserve)&&watch.Elapsed.TotalMilliseconds>=budgetMilliseconds){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    RecordPreparationBatch(watch.Elapsed.TotalMilliseconds);PreparationYields++;
#endif
                    yield return null;watch.Restart();worked=false;
                }
            }
            while(slots.Count<reserve){
                CreateSlot();worked=true;
                if(slots.Count<reserve&&watch.Elapsed.TotalMilliseconds>=budgetMilliseconds){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    RecordPreparationBatch(watch.Elapsed.TotalMilliseconds);PreparationYields++;
#endif
                    yield return null;watch.Restart();worked=false;
                }
            }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(worked)RecordPreparationBatch(watch.Elapsed.TotalMilliseconds);
            PreparedGeometryCount=geometry.Count-geometryBefore;PreparedSlotCount=slots.Count-slotsBefore;
#endif
        }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        void RecordPreparationBatch(double milliseconds){PreparationBatches++;PreparationMilliseconds+=milliseconds;PreparationMaxBatchMilliseconds=System.Math.Max(PreparationMaxBatchMilliseconds,milliseconds);}
#endif
        public void Add(Sprite sprite,int order,Vector3 position,float angle,float sx,float sy,Color color){
            var g=Geometry(sprite);
            // Same page/order grouping as before; the immutable texture ID was
            // already read when this sprite's geometry was cached.
            long key=((long)g.textureId<<32)^(uint)order;
            if(current==null||currentKey!=key){
                if(KeepDrawOrder)current=Open(g.texture,order);
                else if(!open.TryGetValue(key,out current)){current=Open(g.texture,order);open.Add(key,current);}
                currentKey=key;
            }
            float radians=angle*Mathf.Deg2Rad,cos=Mathf.Cos(radians),sin=Mathf.Sin(radians);
            float l=g.left*sx,r=g.right*sx,b=g.bottom*sy,t=g.top*sy;int v=current.vertices.Count;
            current.vertices.Add(new Vector3(position.x+l*cos-b*sin,position.y+l*sin+b*cos,0));
            current.vertices.Add(new Vector3(position.x+l*cos-t*sin,position.y+l*sin+t*cos,0));
            current.vertices.Add(new Vector3(position.x+r*cos-t*sin,position.y+r*sin+t*cos,0));
            current.vertices.Add(new Vector3(position.x+r*cos-b*sin,position.y+r*sin+b*cos,0));
            current.uvs.Add(new Vector2(g.uvMin.x,g.uvMin.y));current.uvs.Add(new Vector2(g.uvMin.x,g.uvMax.y));current.uvs.Add(new Vector2(g.uvMax.x,g.uvMax.y));current.uvs.Add(new Vector2(g.uvMax.x,g.uvMin.y));
            Color32 c=color;current.colors.Add(c);current.colors.Add(c);current.colors.Add(c);current.colors.Add(c);
            // Quad topology is an immutable prefix. Grow its retained high-water
            // list only when this slot has more quads than on any earlier frame.
            if(current.indexCount==current.triangles.Count){
                current.triangles.Add(v);current.triangles.Add(v+1);current.triangles.Add(v+2);current.triangles.Add(v);current.triangles.Add(v+2);current.triangles.Add(v+3);
            }
            current.indexCount+=6;
            Quads++;
        }
        Slot CreateSlot(){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            SlotCreates++;
#endif
                var slot=new Slot{node=new GameObject("Effect mesh "+slots.Count)};slot.node.transform.SetParent(root,false);
                slot.filter=slot.node.AddComponent<MeshFilter>();slot.renderer=slot.node.AddComponent<MeshRenderer>();
                slot.mesh=new Mesh{name="Effect mesh"};slot.mesh.MarkDynamic();slot.mesh.bounds=bounds;slot.filter.sharedMesh=slot.mesh;
                slot.renderer.sharedMaterial=material;slot.renderer.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;slot.renderer.receiveShadows=false;
                slot.renderer.lightProbeUsage=UnityEngine.Rendering.LightProbeUsage.Off;slot.renderer.reflectionProbeUsage=UnityEngine.Rendering.ReflectionProbeUsage.Off;slot.renderer.motionVectorGenerationMode=MotionVectorGenerationMode.ForceNoMotion;
                slot.block=new MaterialPropertyBlock();slot.renderer.enabled=false;slots.Add(slot);return slot;
        }
        Slot Open(Texture2D texture,int order){
            var slot=used<slots.Count?slots[used]:CreateSlot();
            // Later runs sit a hair nearer the orthographic camera so equal
            // sorting orders still draw in list order.
            slot.node.transform.localPosition=new Vector3(0,0,-.001f*(used+1));
            if(slot.texture!=texture){slot.texture=texture;slot.block.SetTexture(MainTexture,texture);slot.renderer.SetPropertyBlock(slot.block);}
            if(slot.order!=order){slot.order=order;slot.renderer.sortingOrder=order;}
            slot.vertices.Clear();slot.uvs.Clear();slot.colors.Clear();slot.indexCount=0;
            used++;return slot;
        }
        public void End(){
            for(int i=0;i<used;i++){
                var slot=slots[i];var mesh=slot.mesh;mesh.Clear(false);
                mesh.SetVertices(slot.vertices);mesh.SetUVs(0,slot.uvs);mesh.SetColors(slot.colors);mesh.SetTriangles(slot.triangles,0,slot.indexCount,0,false,0);mesh.bounds=bounds;
                if(!slot.enabled){slot.renderer.enabled=true;slot.enabled=true;}
            }
            for(int i=used;i<slots.Count;i++)if(slots[i].enabled){slots[i].renderer.enabled=false;slots[i].enabled=false;}
        }
        public void Dispose(){
            foreach(var slot in slots){if(slot.mesh)Object.Destroy(slot.mesh);if(slot.node)Object.Destroy(slot.node);}
            slots.Clear();geometry.Clear();used=0;current=null;Quads=0;
        }
    }
}
// END FROZEN_CHECKPOINT75_EFFECT_BATCHER
#endif

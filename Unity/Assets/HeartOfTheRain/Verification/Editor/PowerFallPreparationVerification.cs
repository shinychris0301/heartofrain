#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using Object=UnityEngine.Object;
namespace HeartOfTheRain.Verification {
 public static class PowerFallPreparationVerification {
  const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
  [Serializable] public class RecordedFrame {public int phase,frame,spritesCreated;public string step;public float playbackAge;public GameplayScreen.FrameCost cost;}
  [Serializable] public class RecordedRow {public string name,turnHash,finalHash;}
  [Serializable] public class RecordedReport {public string status;public List<RecordedRow> rows;public List<RecordedFrame> frames;}
  [Serializable] public class ReplayRow {public int frame,coldCreates,preparedCreates,coldGeometryMisses,preparedGeometryMisses;public float age;public string coldPoseHash,preparedPoseHash,coldMeshHash,preparedMeshHash;public string[] coldKeys;}
  [Serializable] public class SourceRow {public string path,currentSHA256,archivedSHA256;}
  [Serializable] sealed class ModelProofBinding {public string path,currentSHA256,archived77SHA256;}
  [Serializable] sealed class ModelProofRow {public string name;}
  [Serializable] sealed class ModelProof {
   public string status,utc,controlSourceSHA256,verificationSourceSHA256;public int modelCases;
   public bool rawParity,finalParity,checkpointParity,dictionaryParity,controlSourceParity;
   public List<string> errors;public List<ModelProofBinding> currentProductionSourceBindings;public List<ModelProofRow> rows;
  }
  [Serializable] sealed class WorkerSource {public string name,archivedSHA256;public bool exact;}
  [Serializable] sealed class WorkerRow {public string name,archivedQueueHash,detachedQueueHash;}
  [Serializable] sealed class WorkerProof {
   public string status,utc;public int modelCases,queueComparisons;public bool compiledSourceMatchesArchive,queueParity,rawParity,pathOrderParity,poseParity,metadataManagedOnly;
   public List<string> errors;public List<WorkerSource> sources;public List<WorkerRow> rows;
  }
  [Serializable] sealed class WorkerProcess {public string mode,method,version,startedUtc,finishedUtc,sourceManifest,sourceSHA256;public int exitCode;public bool timedOut;}
  [Serializable] public class Result {
   public string status,utc,baselineReportSHA256,turnHash,finalHash,androidTurnHash,coldBeforeHash,coldAfterHash,preparedBeforeHash,preparedAfterHash,sourceParityMode,model78ProofPath,model78ProofSHA256,fixture77TurnHash,fixture77FinalHash;
   public string worker79ProofPath,worker79ProofSHA256,worker79ProcessPath,worker79ProcessSHA256,worker79SourceManifestPath,worker79SourceManifestSHA256;
   public int worker79SourceInputs;public bool worker79CurrentSourceBound;
   public string scope="Native Unity Editor replay of original checkpoint76 frame clocks, sprite demand and uploaded mesh state. Unchanged files retain exact archived76 source bindings; permitted78 model changes require the fresh350 model proof. Only explicit79 playback/continuation/resource-resolver changes may use the fresh exact78 compiled-control worker queue/path/pose proof, successful process chronology and full input manifest matched against current Unity source bytes. This fixture also requires exact77 raw/final comparison before replay. Android final state must match exactly. Editor/Android raw serialized turn hashes are recorded separately; an observed difference has no proven serialization/math cause and is not waived as byte parity. Preparation iterators are explicitly advanced with frame-end interleaving; this is not Play Mode scheduling, device frame pacing, pixel capture or exclusive attribution of the prior stall.";
   public int checks,replayedFrames,coldCreates,preparedDemandCreates,preparedDemandGeometryMisses,preparationFrames,preparationCreates,preparationBatches,overlapFrames,skippedEvictedAtlases;
   public bool rawTurnParity,rawTurnHashMatchesAndroid,finalSnapshotMatchesAndroid,poseParity,meshParity,noAdditionalTextureLoads,workingCapsUnchanged,disposedWorkerStops,overlapDeduplicated,conflictingOwnerRejected,evictedFrameRecreated,fixture77RawParity,fixture77FinalParity;
   public List<SourceRow> sourceBindings=new List<SourceRow>();public List<ReplayRow> rows=new List<ReplayRow>();public List<M46AtlasBank.PowerPreparationBatch> batches=new List<M46AtlasBank.PowerPreparationBatch>();public List<string> errors=new List<string>();
  }
  sealed class Replay {public List<ReplayRow> rows=new List<ReplayRow>();public int preparationFrames,preparationCreates,preparationBatches;}
  static GameplayUIAssets ui;static Result result;
  static string Hash(byte[] bytes){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
  static string Hash(string text)=>Hash(Encoding.UTF8.GetBytes(text));
  static void Check(bool okay,string label){result.checks++;if(!okay)throw new Exception(label);}
  static ModelProof LoadModel78Proof(){
   string path=Environment.GetEnvironmentVariable("HOTR_MODEL78_PROOF");if(string.IsNullOrEmpty(path)){string root=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY78_OUTPUT");if(string.IsNullOrEmpty(root))root=Path.GetFullPath("../Verification/Evidence/Gameplay78");path=Path.Combine(root,"Native/ModelWork78.json");}path=Path.GetFullPath(path);
   Check(File.Exists(path),"Fresh source-bound native78 model equivalence proof exists before migration replay");var bytes=File.ReadAllBytes(path);var proof=JsonUtility.FromJson<ModelProof>(Encoding.UTF8.GetString(bytes));
   Check(proof.status=="PASS_NATIVE_MODEL_WORK78"&&proof.errors!=null&&proof.errors.Count==0&&proof.modelCases==350&&proof.rows!=null&&proof.rows.Count==350&&proof.rows.Select(r=>r.name).Distinct().Count()==350,"Native78 proof passed all350 unique model cases");
   Check(proof.rawParity&&proof.finalParity&&proof.checkpointParity&&proof.dictionaryParity&&proof.controlSourceParity,"Native78 proof preserves raw/final/checkpoint/order and exact77 control source");
   Check(proof.controlSourceSHA256==Hash(File.ReadAllBytes("Assets/HeartOfTheRain/Verification/Model77Control78.cs"))&&proof.verificationSourceSHA256==Hash(File.ReadAllBytes("Assets/HeartOfTheRain/Verification/Editor/ModelWork78Verification.cs")),"Native78 proof binds actual compiled-control and verification sources");
   var paths=new[]{"M46/Runtime/BoardModel.cs","M46/Runtime/LivePowerPlan.cs","M48/Runtime/AdvancedObstacleRulesPure.cs"};Check(proof.currentProductionSourceBindings!=null&&proof.currentProductionSourceBindings.Count==paths.Length,"Native78 proof binds all3 changed production files");
   foreach(string relative in paths){string full="Unity/Assets/HeartOfTheRain/"+relative;var binding=proof.currentProductionSourceBindings.SingleOrDefault(r=>r.path==full);Check(binding!=null&&binding.currentSHA256==Hash(File.ReadAllBytes(Path.GetFullPath("../"+full)))&&binding.archived77SHA256==Hash(File.ReadAllBytes(Path.GetFullPath("../.verification-cache/Gameplay78/BaselineSources/"+full))),"Native78 equivalence proof is current for "+relative);}
   result.model78ProofPath=path;result.model78ProofSHA256=Hash(bytes);return proof;
  }
  static void LoadWorker79Proof(){
   string path=Environment.GetEnvironmentVariable("HOTR_WORKER79_PROOF");if(string.IsNullOrEmpty(path)){string output=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY79_OUTPUT");if(string.IsNullOrEmpty(output))output=Path.GetFullPath("../Verification/Evidence/Gameplay79");path=Path.Combine(output,"Native/Worker79.json");}path=Path.GetFullPath(path);
   Check(File.Exists(path),"Fresh native79 exact78 worker proof exists before preparation migration");var bytes=File.ReadAllBytes(path);var proof=JsonUtility.FromJson<WorkerProof>(Encoding.UTF8.GetString(bytes));
   Check(proof.status=="PASS_NATIVE_PLAYBACK_PREPARATION79"&&proof.errors!=null&&proof.errors.Count==0&&proof.modelCases==350&&proof.queueComparisons>=350&&proof.rows!=null&&proof.rows.Count==350&&proof.rows.Select(r=>r.name).Distinct().Count()==350,"Native79 worker proof passed350 unique model commands");
   Check(proof.compiledSourceMatchesArchive&&proof.queueParity&&proof.rawParity&&proof.pathOrderParity&&proof.poseParity&&proof.metadataManagedOnly&&proof.rows.All(r=>r.archivedQueueHash==r.detachedQueueHash),"Native79 worker preserves exact78 compiled queues, raw outcomes, ordered paths and poses with managed metadata");
   var names=new[]{"BoardPlayback.cs","LocalCascadeContinuation.cs","LocalCascadePlayback.cs"};Check(proof.sources!=null&&proof.sources.Count==names.Length,"Native79 worker binds all3 exact78 compiled controls");
   foreach(string name in names){var binding=proof.sources.SingleOrDefault(r=>r.name==name);Check(binding!=null&&binding.exact&&binding.archivedSHA256==Hash(File.ReadAllText(Path.GetFullPath("../.verification-cache/Gameplay79/BaselineSources/Unity/Assets/HeartOfTheRain/M46/Runtime/"+name))),"Native79 worker compiled control retains archived78 source: "+name);}
   string runPath=Path.Combine(Path.GetDirectoryName(path),"Worker79_Process.json");var runBytes=File.ReadAllBytes(runPath);var run=JsonUtility.FromJson<WorkerProcess>(Encoding.UTF8.GetString(runBytes).TrimStart('\uFEFF'));
   Check(run.mode=="Worker79"&&run.method=="PlaybackPreparation79Verification.Run"&&run.exitCode==0&&!run.timedOut&&run.version.StartsWith("2022.3.62f3",StringComparison.Ordinal),"Native79 worker ran successfully in the pinned Editor");
   DateTimeOffset began=DateTimeOffset.Parse(run.startedUtc),reported=DateTimeOffset.Parse(proof.utc),finished=DateTimeOffset.Parse(run.finishedUtc),now=DateTimeOffset.Parse(result.utc);Check(began<=reported&&reported<=finished&&finished<=now,"Native79 worker report/process precede this preparation replay");
   string outputRoot=Path.GetFullPath(Path.Combine(Path.GetDirectoryName(path),"..")),manifestPath=Path.GetFullPath(Path.Combine(outputRoot,run.sourceManifest));Check(manifestPath.StartsWith(outputRoot+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase),"Native79 worker manifest stays within its evidence root");var manifestBytes=File.ReadAllBytes(manifestPath);Check(Hash(manifestBytes)==run.sourceSHA256,"Native79 worker manifest bytes match its successful process");
   // The generated manifest has a string-to-SHA files object. Parse only that
   // restricted format, reject unconsumed entries, and check its full file set.
   string manifest=Encoding.UTF8.GetString(manifestBytes);var section=Regex.Match(manifest,"\"files\"\\s*:\\s*\\{(?<entries>[^{}]*)\\}",RegexOptions.Singleline);Check(section.Success,"Native79 full source manifest contains a files object");string entries=section.Groups["entries"].Value;
   const string pattern="\"(?<path>Unity/[^\"\\\\]+)\"\\s*:\\s*\"(?<sha>[0-9a-f]{64})\"";var matches=Regex.Matches(entries,pattern);Check(Regex.Replace(Regex.Replace(entries,pattern,""),"[\\s,]","")=="","Native79 manifest contains only complete path/SHA entries");
   var sources=new Dictionary<string,string>(StringComparer.Ordinal);foreach(Match entry in matches)sources.Add(entry.Groups["path"].Value,entry.Groups["sha"].Value);
   string projectRoot=Path.GetFullPath("..");var actual=new List<string>();foreach(string folder in new[]{"Assets","Packages","ProjectSettings"})foreach(string full in Directory.GetFiles(Path.GetFullPath(folder),"*",SearchOption.AllDirectories))actual.Add(full.Substring(projectRoot.Length+1).Replace('\\','/'));
   Check(actual.Count==sources.Count&&actual.All(sources.ContainsKey),"Native79 full source manifest covers every current Unity input without extras");foreach(string full in actual)Check(sources[full]==Hash(File.ReadAllBytes(Path.Combine(projectRoot,full))),"Native79 worker input remains current: "+full);
   result.worker79ProofPath=path;result.worker79ProofSHA256=Hash(bytes);result.worker79ProcessPath=runPath;result.worker79ProcessSHA256=Hash(runBytes);result.worker79SourceManifestPath=manifestPath;result.worker79SourceManifestSHA256=Hash(manifestBytes);result.worker79SourceInputs=sources.Count;result.worker79CurrentSourceBound=true;
  }
  static void Load(M46AtlasBank bank,IEnumerable<string> paths){var method=typeof(M46AtlasBank).GetMethod("Texture",Private);foreach(var path in paths)method.Invoke(bank,new object[]{null,path});}
  static IDictionary Entries(M46AtlasBank bank)=>(IDictionary)typeof(M46AtlasBank).GetField("sprites",Private).GetValue(bank);
  static void Dispose(M46AtlasBank bank){foreach(var entry in Entries(bank).Values){var sprite=(Sprite)entry.GetType().GetField("sprite").GetValue(entry);if(sprite)Object.DestroyImmediate(sprite);}Entries(bank).Clear();bank.Dispose();}
  static void Drain(IEnumerator iterator,M46AtlasBank bank,bool power=false){int advances=0;while(iterator.MoveNext()){Check(++advances<10000,"Preparation terminates");if(power&&bank.PowerPreparationBatches>result.batches.Count)result.batches.Add(bank.LastPowerPreparationBatch);bank.BeginFrame();bank.EndFrame(false);}if(power&&bank.PowerPreparationBatches>result.batches.Count)result.batches.Add(bank.LastPowerPreparationBatch);}
  static void Vector(BinaryWriter w,Vector3 v){w.Write(v.x);w.Write(v.y);w.Write(v.z);}
  static string MeshHash(Transform root){using(var memory=new MemoryStream())using(var w=new BinaryWriter(memory)){
   foreach(var f in root.GetComponentsInChildren<MeshFilter>()){var r=f.GetComponent<MeshRenderer>();if(!r.enabled)continue;var mesh=f.sharedMesh;w.Write(r.sortingOrder);w.Write(r.sharedMaterial.name);var block=new MaterialPropertyBlock();r.GetPropertyBlock(block);var texture=block.GetTexture(Shader.PropertyToID("_MainTex"));w.Write(texture?texture.name:"");Vector(w,f.transform.localPosition);Vector(w,mesh.bounds.center);Vector(w,mesh.bounds.size);var vertices=mesh.vertices;w.Write(vertices.Length);foreach(var v in vertices)Vector(w,v);var uv=mesh.uv;w.Write(uv.Length);foreach(var v in uv){w.Write(v.x);w.Write(v.y);}var colors=mesh.colors32;w.Write(colors.Length);foreach(var c in colors){w.Write(c.r);w.Write(c.g);w.Write(c.b);w.Write(c.a);}var triangles=mesh.triangles;w.Write(triangles.Length);foreach(int index in triangles)w.Write(index);}
   w.Flush();return Hash(memory.ToArray());}}
  public static void Run(){
   result=new Result{utc=DateTime.UtcNow.ToString("o")};
   try{
    ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
    ModelProof modelProof=null;bool workerProof=false;result.sourceParityMode="EXACT_ARCHIVED76_SOURCE";
    foreach(string path in new[]{"M46/Runtime/BoardModel.cs","M46/Runtime/LivePowerPlan.cs","M46/Runtime/ReviewPlan.cs","M46/Runtime/BoardPlayback.cs","Verification/ObstacleDensityFixture.cs","M46/Runtime/LocalCascadeContinuation.cs","M48/Runtime/EffectResourcesPure.cs"}){
     string relative="Unity/Assets/HeartOfTheRain/"+path;var row=new SourceRow{path=relative,currentSHA256=Hash(File.ReadAllBytes(Path.GetFullPath("../"+relative))),archivedSHA256=Hash(File.ReadAllBytes(Path.GetFullPath("../.verification-cache/Gameplay77/BaselineSources/"+relative)))};
     if(row.currentSHA256==row.archivedSHA256)Check(true,"Exact archived76 model/planner/fixture source bytes: "+path);
     else if(path=="M46/Runtime/BoardModel.cs"||path=="M46/Runtime/LivePowerPlan.cs"){if(modelProof==null)modelProof=LoadModel78Proof();var binding=modelProof.currentProductionSourceBindings.Single(r=>r.path==relative);Check(binding.currentSHA256==row.currentSHA256&&binding.archived77SHA256==row.archivedSHA256,"Current78 equivalence proof retains this exact archived76/77 binding: "+path);}
     else {Check(path=="M46/Runtime/BoardPlayback.cs"||path=="M46/Runtime/LocalCascadeContinuation.cs"||path=="M48/Runtime/EffectResourcesPure.cs","Only explicitly proven79 playback/continuation/resource files may additionally differ: "+path);if(!workerProof){LoadWorker79Proof();workerProof=true;}}
     result.sourceBindings.Add(row);
    }
    if(workerProof)result.sourceParityMode="ARCHIVED76_UNCHANGED_PLUS_MODEL78_AND_WORKER79_EQUIVALENCE";else if(modelProof!=null)result.sourceParityMode="ARCHIVED76_UNCHANGED_PLUS_MODEL78_EQUIVALENCE";
    string oldPath=Path.GetFullPath("../Verification/Evidence/Gameplay76/PairedDensity/paired_1-stone/Report.json");var bytes=File.ReadAllBytes(oldPath);result.baselineReportSHA256=Hash(bytes);var old=JsonUtility.FromJson<RecordedReport>(Encoding.UTF8.GetString(bytes));Check(old.status=="PASS_OBSTACLE_DENSITY_PLAYBACK","Original paired report passed");
    int phase=old.rows.FindIndex(r=>r.name=="stone_1_0_current76");Check(phase>=0,"Original sparse stone row exists");var recorded=old.frames.Where(f=>f.phase==phase&&f.step=="powerFall").ToArray();Check(recorded.Any(f=>f.frame==1247)&&recorded.Any(f=>f.frame==1248),"Original late resource frames retained");
    var level=ObstacleDensityFixture.Level(JsonUtility.FromJson<LevelData>(ui.boards.levels[25].text),1,"stone");var model=new BoardModel(level);var initial=model.Snapshot();var turn=ObstacleDensityFixture.Solve(model);Check(turn.accepted,"Original command accepted");result.turnHash=Hash(JsonUtility.ToJson(turn));result.finalHash=Hash(JsonUtility.ToJson(model.Snapshot()));result.androidTurnHash=old.rows[phase].turnHash;result.rawTurnHashMatchesAndroid=result.turnHash==result.androidTurnHash;result.finalSnapshotMatchesAndroid=result.finalHash==old.rows[phase].finalHash;Check(result.finalSnapshotMatchesAndroid,"Actual final state matches archived76 Android exactly");
    var controlModel=new BoardModel(level){VerificationUseCheckpoint77Model78=true};Check(Hash(JsonUtility.ToJson(controlModel.Snapshot()))==Hash(JsonUtility.ToJson(initial)),"This original DoubleOrb/stone fixture has exact77 initial state");var controlTurn=ObstacleDensityFixture.Solve(controlModel);result.fixture77TurnHash=Hash(JsonUtility.ToJson(controlTurn));result.fixture77FinalHash=Hash(JsonUtility.ToJson(controlModel.Snapshot()));result.fixture77RawParity=controlTurn.accepted&&result.fixture77TurnHash==result.turnHash;result.fixture77FinalParity=result.fixture77FinalHash==result.finalHash;Check(result.fixture77RawParity&&result.fixture77FinalParity,"This original DoubleOrb/stone fixture preserves exact77 raw turn and final state before replay");
    var queue=BoardPlayback.Build(turn.steps,level);var power=queue.Single(s=>s.kind=="powerFall"&&s.playbackTracks!=null&&s.playbackTracks.Any(t=>t.step.powerPlan!=null&&t.step.powerPlan.kind==10));
    result.coldBeforeHash=Hash(JsonUtility.ToJson(turn));var cold=ReplayRecorded(initial,level,power,queue,recorded,false);result.coldAfterHash=Hash(JsonUtility.ToJson(turn));result.preparedBeforeHash=Hash(JsonUtility.ToJson(turn));var prepared=ReplayRecorded(initial,level,power,queue,recorded,true);result.preparedAfterHash=Hash(JsonUtility.ToJson(turn));result.rawTurnParity=new[]{result.coldBeforeHash,result.coldAfterHash,result.preparedBeforeHash,result.preparedAfterHash}.All(hash=>hash==result.turnHash);Check(result.rawTurnParity,"Build and both native replay paths preserve the exact native raw turn");
    for(int i=0;i<cold.rows.Count;i++){var a=cold.rows[i];var b=prepared.rows[i];a.preparedCreates=b.coldCreates;a.preparedGeometryMisses=b.coldGeometryMisses;a.preparedPoseHash=b.coldPoseHash;a.preparedMeshHash=b.coldMeshHash;Check(a.coldPoseHash==a.preparedPoseHash,"Exact sampled draws/sprite rects at original frame "+a.frame);Check(a.coldMeshHash==a.preparedMeshHash,"Exact uploaded geometry/UV/colors/indices/material/order at "+a.frame);Check(a.preparedCreates==0&&a.preparedGeometryMisses==0,"Prepared original fall has no demand sprite or geometry miss at "+a.frame);result.rows.Add(a);}
    foreach(var r in result.rows.Where(x=>x.frame>=1238&&x.frame<=1249))Check(r.coldCreates==recorded.Single(x=>x.frame==r.frame).spritesCreated,"Original late first-use count reproduced at "+r.frame);
    foreach(int frame in new[]{1247,1248}){var r=result.rows.Single(x=>x.frame==frame);var expected=frame==1247?new[]{"p/21/44","p/28/27"}:new[]{"p/21/45","p/28/29"};Check(r.coldKeys.OrderBy(x=>x).SequenceEqual(expected),"Native first-use keys reproduce source diagnosis at "+frame);}
    result.replayedFrames=result.rows.Count;result.coldCreates=result.rows.Sum(r=>r.coldCreates);result.preparedDemandCreates=result.rows.Sum(r=>r.preparedCreates);result.preparedDemandGeometryMisses=result.rows.Sum(r=>r.preparedGeometryMisses);result.poseParity=result.rows.All(r=>r.coldPoseHash==r.preparedPoseHash);result.meshParity=result.rows.All(r=>r.coldMeshHash==r.preparedMeshHash);result.preparationFrames=prepared.preparationFrames;result.preparationCreates=prepared.preparationCreates;result.preparationBatches=prepared.preparationBatches;
    Lifecycle();
   }catch(Exception e){result.errors.Add(e.ToString());}
   result.status=result.errors.Count==0?"PASS_NATIVE_POWER_FALL_PREPARATION77":"FAIL_NATIVE_POWER_FALL_PREPARATION77";
   string folder=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY77_OUTPUT");if(string.IsNullOrEmpty(folder))folder=Path.GetFullPath("../Verification/Evidence/Gameplay77");folder=Path.Combine(folder,"Native");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"PowerFallPreparation.json"),JsonUtility.ToJson(result,true));EditorApplication.Exit(result.errors.Count==0?0:1);
  }
  static Replay ReplayRecorded(BoardSnapshot initial,LevelData level,BoardStep power,List<BoardStep> queue,RecordedFrame[] frames,bool prepare){
   var bank=new M46AtlasBank(ui.boards);var root=new GameObject("Power fall resource replay").transform;var batcher=new EffectMeshBatcher(root,ui.boards.effectsMaterial,new Bounds(Vector3.zero,new Vector3(64,64,2)));var replay=new Replay();
   try{
    CrateBurstVerification.Warm(bank,initial);foreach(var piece in initial.pieces)bank.Get(new DrawSprite{bank="body",key=BoardPresentation.BodyKey(piece)});Load(bank,bank.RequiredResources(queue));Drain(batcher.Prepare(bank.CachedEffectSpritesSnapshot()),bank);int textureCount=bank.TextureCount,sync=bank.SynchronousLoads,pinned=bank.PinnedSprites,limit=bank.SpriteLimit;long budget=bank.TextureBudget;
    if(prepare){int created=bank.SpriteCreates;var warm=bank.WarmPowerFrames(bank.RequiredResources(queue),batcher.PrepareSprite,1,16);Check(warm.MoveNext()&&bank.SpriteCreates==created&&bank.PowerPreparationBatches==0,"First worker advance yields before native sprite/geometry work");Drain(warm,bank,true);Check(!bank.PowerPreparationPending,"Worker completes actual resident manifests");Check(bank.SynchronousLoads==sync&&bank.TextureCount==textureCount,"Preparation never loads an additional texture");Check(bank.PinnedSprites==pinned&&bank.SpriteLimit==limit&&bank.TextureBudget==budget,"Preparation preserves pins and both caps");result.noAdditionalTextureLoads=true;result.workingCapsUnchanged=true;replay.preparationFrames=bank.PowerPreparationFrames;replay.preparationCreates=bank.PowerPreparationCreates;replay.preparationBatches=bank.PowerPreparationBatches;Check(result.batches.All(b=>b.frames<=16&&b.startedWall<=b.finishedWall&&b.milliseconds>=0),"Every actual preparation batch respects frame-count bound and records elapsed cost");}
    float start=frames[0].cost.clock-frames[0].playbackAge;var view=CrateBurstVerification.View(ui,level.columns,level.rows);view.Add(power,start);
    foreach(var frame in frames){bank.BeginFrame();batcher.Begin();view.PruneHistory(frame.cost.clock);var draws=view.SampleLive(power,power.before,frame.cost.clock,start);int before=bank.SpriteCreates;var keys=new List<string>();var signature=new StringBuilder();
     foreach(var d in draws){signature.Append(JsonUtility.ToJson(d));int prior=bank.SpriteCreates;var sprite=bank.Get(d);if(bank.SpriteCreates!=prior)keys.Add(sprite.name);if(sprite){signature.Append(sprite.name).Append(JsonUtility.ToJson(sprite.rect)).Append(sprite.texture.name);if(d.alpha>0&&!d.uiOverlay&&!d.masked&&d.glow<=0)batcher.Add(sprite,d.order,new Vector3(d.x,d.y,0),d.angle,d.sx,d.sy,new Color(d.red,d.green,d.blue,d.alpha));}}
     batcher.End();replay.rows.Add(new ReplayRow{frame=frame.frame,age=frame.playbackAge,coldCreates=bank.SpriteCreates-before,coldGeometryMisses=batcher.GeometryMisses,coldKeys=keys.ToArray(),coldPoseHash=Hash(signature.ToString()),coldMeshHash=MeshHash(root)});bank.EndFrame(false);
    }
    Check(bank.SynchronousLoads==sync,"Recorded fall performs no synchronous texture load");
   }finally{batcher.Dispose();Object.DestroyImmediate(root.gameObject);Dispose(bank);}return replay;
  }
  static void Lifecycle(){
   var bank=new M46AtlasBank(ui.boards);try{
    string a=ui.boards.powerResources[28],b=ui.boards.powerResources[21],excluded=ui.boards.powerResources[9];Load(bank,new[]{a,b,excluded});int textures=bank.TextureCount,sync=bank.SynchronousLoads;int callbacks=0;Action<Sprite> owner=s=>callbacks++;var first=bank.WarmPowerFrames(new[]{a},owner,100,7);Check(first.MoveNext()&&callbacks==0&&bank.SpriteCreates==0,"First request only enqueues");var overlap=bank.WarmPowerFrames(new[]{a,b},owner,100,5);Check(!overlap.MoveNext()&&callbacks==0,"Overlapping request enqueues without doing duplicate worker work");Drain(first,bank);result.overlapFrames=bank.PowerPreparationFrames;Check(callbacks==94&&bank.PowerPreparationFrames==94&&bank.SpriteCreates==94,"Overlapping32/62-frame manifests run once each");Check(Entries(bank).Keys.Cast<string>().All(k=>k.StartsWith("p/28/")||k.StartsWith("p/21/")),"Resident unrequested atlas remains untouched");Check(bank.TextureCount==textures&&bank.SynchronousLoads==sync&&bank.PinnedSprites==0&&bank.SpriteLimit==2048,"Overlap does not add textures, pins or cap");Check(bank.LastPowerPreparationBatch.frames<=5,"Overlapping stricter frame limit applies to serial worker");result.overlapDeduplicated=true;
    int count=bank.SpriteCreates;bool rejected=false;try{bank.WarmPowerFrames(new[]{excluded},s=>{},1,16).MoveNext();}catch(InvalidOperationException){rejected=true;}Check(rejected&&bank.SpriteCreates==count&&!bank.PowerPreparationPending,"Conflicting geometry owner rejected before enqueue");result.conflictingOwnerRejected=true;
    var original=bank.Get(new DrawSprite{bank="power",atlas=28,key="DO_Wave",age=27.1f/60});bank.SpriteLimit=0;bank.BeginFrame();bank.EndFrame(false);Check(bank.SpriteEvictions>0,"Prepared frames remain evictable under real sprite pressure");int before=bank.SpriteCreates;var recreated=bank.Get(new DrawSprite{bank="power",atlas=28,key="DO_Wave",age=27.1f/60});Check(!ReferenceEquals(original,recreated)&&bank.SpriteCreates==before+1,"Evicted prepared frame uses ordinary demand fallback");result.evictedFrameRecreated=true;
   }finally{Dispose(bank);}
   var cancelled=new M46AtlasBank(ui.boards);Load(cancelled,new[]{ui.boards.powerResources[28]});var pending=cancelled.WarmPowerFrames(new[]{ui.boards.powerResources[28]},null);Check(pending.MoveNext()&&cancelled.PowerPreparationPending,"Disposed control has pending work");Dispose(cancelled);Check(!pending.MoveNext()&&!cancelled.PowerPreparationPending&&cancelled.SpriteCount==0&&cancelled.TextureCount==0,"Disposed worker cannot recreate native resources");result.disposedWorkerStops=true;
   var evicted=new M46AtlasBank(ui.boards);try{string path=ui.boards.powerResources[28];Load(evicted,new[]{path});var work=evicted.WarmPowerFrames(new[]{path},null);Check(work.MoveNext(),"Eviction control starts deferred");var textures=(IDictionary)typeof(M46AtlasBank).GetField("textures",Private).GetValue(evicted);var entry=textures[path];entry.GetType().GetField("used").SetValue(entry,-100f);evicted.TextureBudget=0;evicted.BeginFrame();evicted.EndFrame(true);Check(evicted.TextureCount==0,"Real idle LRU evicts pending atlas texture");int sync=evicted.SynchronousLoads;Drain(work,evicted);Check(evicted.SpriteCreates==0&&evicted.SynchronousLoads==sync&&evicted.PowerPreparationSkippedAtlases==1,"Texture evicted between yields is skipped without synchronous reload");result.skippedEvictedAtlases=evicted.PowerPreparationSkippedAtlases;}finally{Dispose(evicted);}
  }
 }
}
#endif

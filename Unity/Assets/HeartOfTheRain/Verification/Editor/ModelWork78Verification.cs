#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 public static class ModelWork78Verification {
  [Serializable] public sealed class SourceBinding {public string path,sha256,compiledBodySHA256;public bool exact;}
  [Serializable] public sealed class ProductionSourceBinding {public string path,currentSHA256,archived77SHA256;}
  [Serializable] public sealed class ModelRow {public string name,rawHash,finalHash,checkpointHash,dictionaryOrder;public int steps;public BoardModel.ModelWork work,controlWork;}
  [Serializable] public sealed class Pair {public int index;public bool controlFirst;public double controlMs,currentMs;public int controlCollections,currentCollections;}
  [Serializable] public sealed class Timing {public string name;public double controlMedianMs,currentMedianMs,controlMaxMs,currentMaxMs;public int slowerPairs;public List<Pair> pairs=new List<Pair>();}
  [Serializable] public sealed class Report {
   public string status,utc,controlSourceSHA256,verificationSourceSHA256,scope="Pinned native Unity model-only verification. Exact archived77 helper controls use the same DTO/model command path; setup, hashing, checkpoints and serialization are outside paired timing. Full raw/final/RNG/dictionary parity plus snapshot and invalid-state controls. Timing is descriptive Editor CPU, separate from Android pacing. No allocation-byte or universal speedup claim.";
   public int checks,modelCases,pairCases,plannerCases,snapshotCases,invalidCases;public bool rawParity=true,finalParity=true,checkpointParity=true,dictionaryParity=true,controlSourceParity=true;
   public List<string> errors=new List<string>();public List<SourceBinding> sources=new List<SourceBinding>();public List<ProductionSourceBinding> currentProductionSourceBindings=new List<ProductionSourceBinding>();public List<ModelRow> rows=new List<ModelRow>();public List<Timing> timings=new List<Timing>();
  }
  [Serializable] sealed class ArchivedRow {public string name,turnHash,finalHash;}
  [Serializable] sealed class ArchivedReport {public string status;public List<ArchivedRow> rows;}
  static Report report;static M46Assets assets;const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
  static string Hash(string value){using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(value))).Replace("-","").ToLowerInvariant();}
  static string FileHash(string path){using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
  static void Check(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);}
  static string Normalize(string value)=>value.Replace("\r\n","\n").Trim();
  static string Method(string text,string marker){int start=text.IndexOf(marker,StringComparison.Ordinal);if(start<0)throw new InvalidOperationException("Missing method "+marker);int end=text.IndexOf('{',start)+1,depth=1;while(depth>0){if(text[end]=='{')depth++;else if(text[end]=='}')depth--;end++;}return text.Substring(start,end-start);}
  static string Section(string text,string name){string begin="// BEGIN EXACT77 "+name,end="// END EXACT77 "+name;int start=text.IndexOf(begin,StringComparison.Ordinal)+begin.Length;int stop=text.IndexOf(end,start,StringComparison.Ordinal);return text.Substring(start,stop-start);}
  static void SourceProof(){
   var root=Path.GetFullPath("../.verification-cache/Gameplay78/BaselineSources/Unity/Assets/HeartOfTheRain");var compiled=File.ReadAllText("Assets/HeartOfTheRain/Verification/Model77Control78.cs");
   report.controlSourceSHA256=FileHash("Assets/HeartOfTheRain/Verification/Model77Control78.cs");report.verificationSourceSHA256=FileHash("Assets/HeartOfTheRain/Verification/Editor/ModelWork78Verification.cs");
   string model=File.ReadAllText(Path.Combine(root,"M46/Runtime/BoardModel.cs")),foot=File.ReadAllText(Path.Combine(root,"M48/Runtime/AdvancedObstacleRulesPure.cs")),plan=File.ReadAllText(Path.Combine(root,"M46/Runtime/LivePowerPlan.cs"));
   var files=new[]{"M46/Runtime/BoardModel.cs","M48/Runtime/AdvancedObstacleRulesPure.cs","M46/Runtime/LivePowerPlan.cs"};var sealedHashes=new[]{"de48eb92d95f6fa79937fb8c1afd9f4ac03ff208a74bdb1f9708daf1044ade40","e6bb01ac36398784672eee76c9ee3e722db5a09829c6b19be9cfc7094e1ca063","2fa218f5615f3fdcceebc5eb619e8a2025f60027a7cbb85bb5ac23c7a434f495"};
   for(int i=0;i<files.Length;i++){Check(FileHash(Path.Combine(root,files[i]))==sealedHashes[i],"Sealed77 source bytes "+files[i]);report.currentProductionSourceBindings.Add(new ProductionSourceBinding{path="Unity/Assets/HeartOfTheRain/"+files[i],currentSHA256=FileHash("Assets/HeartOfTheRain/"+files[i]),archived77SHA256=sealedHashes[i]});}
   string[] names={"SnapshotFromScratch","Validate","ValidateFootprints","LivePowerPlan"};
   string[] expected={Method(model,"        BoardSnapshot SnapshotFromScratch()").Replace("SnapshotFromScratch()","SnapshotFromCheckpoint77Model78()"),Method(model,"        public void Validate()").Replace("public void Validate()","void ValidateCheckpoint77Model78()"),Method(foot,"        void ValidateFootprints()").Replace("ValidateFootprints()","ValidateFootprintsCheckpoint77Model78()"),plan.Substring(plan.IndexOf("    public static class LivePowerPlan",StringComparison.Ordinal),plan.LastIndexOf('}')-plan.IndexOf("    public static class LivePowerPlan",StringComparison.Ordinal)).Replace("public static class LivePowerPlan","public static class LivePowerPlan77")};
   for(int i=0;i<names.Length;i++){string actual=Section(compiled,names[i]);bool exact=Normalize(actual)==Normalize(expected[i]);report.controlSourceParity&=exact;report.sources.Add(new SourceBinding{path=names[i],sha256=Hash(Normalize(expected[i])),compiledBodySHA256=Hash(Normalize(actual)),exact=exact});Check(exact,"Compiled exact77 control "+names[i]);}
  }
  static string Counts(BoardModel.ModelWork w)=>string.Join(",",new[]{w.snapshotCalls,w.copiedPieces,w.validationCalls,w.footprintCalls,w.matchCalls,w.gravityCalls,w.verticalCalls,w.activationCalls,w.planningCalls,w.legalQueryCalls});
  static ModelRow Compare(ModelWork78Proof.Prepared current,ModelWork78Proof.Prepared control,string expectedRaw=null,string expectedFinal=null){
   var old=ModelWork78Proof.Measure(control);var now=ModelWork78Proof.Measure(current);Check(old.turn.accepted&&now.turn.accepted,"Accepted paired command "+current.name);
   string raw=Hash(JsonUtility.ToJson(now.turn)),oldRaw=Hash(JsonUtility.ToJson(old.turn));string final=Hash(JsonUtility.ToJson(current.model.Snapshot())),oldFinal=Hash(JsonUtility.ToJson(control.model.Snapshot()));
   string checkpoint=Hash(JsonUtility.ToJson(current.model.Checkpoint())),oldCheckpoint=Hash(JsonUtility.ToJson(control.model.Checkpoint()));string order=string.Join(";",current.model.Pieces.Select(p=>p.Key+":"+p.Value.id)),oldOrder=string.Join(";",control.model.Pieces.Select(p=>p.Key+":"+p.Value.id));
   bool r=raw==oldRaw&&(expectedRaw==null||raw==expectedRaw),f=final==oldFinal&&(expectedFinal==null||final==expectedFinal),c=checkpoint==oldCheckpoint,o=order==oldOrder;
   report.rawParity&=r;report.finalParity&=f;report.checkpointParity&=c;report.dictionaryParity&=o;
   Check(r,"Exact77 raw steps/plans/motions "+current.name);Check(f,"Exact77 final state "+current.name);Check(c,"Exact77 RNG/checkpoint "+current.name);Check(o,"Exact77 live dictionary order "+current.name);Check(Counts(now.work)==Counts(old.work),"Same deterministic validation/planning/snapshot counts "+current.name);
   return new ModelRow{name=current.name,rawHash=raw,finalHash=final,checkpointHash=checkpoint,dictionaryOrder=order,steps=now.turn.steps.Count,work=now.work,controlWork=old.work};
  }
  static void Snapshot(BoardModel board,string name){
   report.snapshotCases++;var entries=board.Pieces.ToArray();var goals=board.Goals.ToArray();board.VerificationUseCheckpoint77Model78=true;var control=board.Snapshot();string expected=JsonUtility.ToJson(control);board.VerificationUseCheckpoint77Model78=false;var current=board.Snapshot();
   Check(expected==JsonUtility.ToJson(current),"Snapshot ordered field parity "+name);Check(entries.Select(p=>p.Key).SequenceEqual(board.Pieces.Keys)&&entries.All(p=>ReferenceEquals(p.Value,board.Pieces[p.Key]))&&goals.SequenceEqual(board.Goals),"Snapshot preserves live dictionaries "+name);
   Check(current.pieces.All(p=>!entries.Any(e=>ReferenceEquals(e.Value,p)))&&current.pieces.All(p=>!control.pieces.Any(old=>ReferenceEquals(old,p)))&&current.goals.All(g=>!control.goals.Any(old=>ReferenceEquals(old,g))),"Snapshot copies remain independently owned "+name);
   if(current.pieces.Length>0){current.pieces[0].x+=1000;current.pieces[0].family="snapshot_only";}if(current.goals.Length>0)current.goals[0].count+=1000;
   for(int i=0;i<3;i++)Check(expected==JsonUtility.ToJson(board.Snapshot())&&expected==JsonUtility.ToJson(control),"Caller mutation and repeated reuse preserve prior/source state "+name);
  }
  static void SnapshotControls(){
   var data=JsonUtility.FromJson<LevelData>(assets.levels[0].text);var board=new BoardModel(data);Snapshot(board,"initial");var gems=board.Pieces.Values.Where(p=>p.family=="gem").Take(3).ToArray();
   var replacement=gems[0].Copy();replacement.color=(replacement.color+1)%6;board.Pieces[board.Key(replacement.x,replacement.y)]=replacement;Snapshot(board,"same_id_new_reference");
   int key=board.Key(gems[1].x,gems[1].y);board.Pieces.Remove(key);var added=gems[1].Copy();added.id=int.MaxValue;board.Pieces.Add(key,added);Snapshot(board,"same_count_replaced_identity");
   int first=replacement.id;replacement.id=gems[2].id;gems[2].id=first;Snapshot(board,"same_count_swapped_live_ids");added.id=replacement.id;Snapshot(board,"duplicate_id_stable_fallback");added.id=-17;Snapshot(board,"negative_identity_diagnostic");
   var removed=board.Pieces.Take(11).ToArray();foreach(var item in removed)board.Pieces.Remove(item.Key);Snapshot(board,"shrunk");foreach(var item in removed)board.Pieces.Add(item.Key,item.Value);Snapshot(board,"regrown_and_reinserted");
   typeof(BoardModel).GetField("snapshotGeneration",Private).SetValue(board,-1);Snapshot(board,"generation_reset");
   board.Pieces.Clear();for(int i=0;i<300;i++)board.Pieces.Add(i,new Piece{id=300-i,x=i,y=0,family="gem",color=i%6});Snapshot(board,"control_resized_scratch_300");board.VerificationUseCheckpoint77Model78=true;board.Snapshot();board.VerificationUseCheckpoint77Model78=false;Snapshot(board,"toggle_control_after_growth");
   board.Pieces.Clear();board.Goals.Clear();Snapshot(board,"empty");var culture=Thread.CurrentThread.CurrentCulture;try{foreach(string locale in new[]{"en-US","tr-TR","fr-FR","sv-SE"}){Thread.CurrentThread.CurrentCulture=CultureInfo.GetCultureInfo(locale);var b=new BoardModel(data);foreach(string family in new[]{"\u00e9","e\u0301","a","A","I","\u0131"})b.Goals[family]=0;Snapshot(b,"culture_"+locale);}}finally{Thread.CurrentThread.CurrentCulture=culture;}
  }
  static string ValidationError(BoardModel board){try{board.Validate();return "OK";}catch(Exception e){return e.GetType().FullName+":"+e.Message;}}
  static void Invalid(int level,string name,Action<BoardModel> mutate,string expected){
   var data=JsonUtility.FromJson<LevelData>(assets.levels[level].text);var current=new BoardModel(data);var old=new BoardModel(data){VerificationUseCheckpoint77Model78=true};current.Snapshot();old.Snapshot();mutate(current);mutate(old);string before=JsonUtility.ToJson(current.Snapshot()),oldBefore=JsonUtility.ToJson(old.Snapshot());string a=ValidationError(current),b=ValidationError(old);report.invalidCases++;
   Check(a==b&&a.EndsWith(expected,StringComparison.Ordinal),"Identical invalid-state exception/guard order "+name+": "+a+" / "+b);Check(before==JsonUtility.ToJson(current.Snapshot())&&oldBefore==JsonUtility.ToJson(old.Snapshot()),"Validation leaves model intact "+name);
  }
  static void InvalidControls(){
   Invalid(0,"gem_color",b=>b.Pieces.Values.First(p=>p.family=="gem").color=6,"Invalid gem color");
   Invalid(0,"negative_obstacle_hp",b=>b.Pieces.Values.First(p=>p.family!="gem"&&p.family!="power").hp=0,"Invalid obstacle HP");
   Invalid(0,"occupancy",b=>b.Pieces.Values.First().x+=100,"Occupancy invariant failed");
   Invalid(0,"duplicate_ids_before_owner",b=>{var p=b.Pieces.Values.Take(2).ToArray();p[1].id=p[0].id;p[1].ownerId=int.MaxValue;},"Occupancy invariant failed");
   Invalid(0,"missing_owner_before_goal",b=>{b.Pieces.Values.First(p=>p.family=="gem").ownerId=int.MaxValue;b.Goals[b.Goals.Keys.First()]=-1;},"Invalid shared obstacle owner");
   Invalid(0,"goals",b=>b.Goals[b.Goals.Keys.First()]=-1,"Goal count mismatch: "+new BoardModel(JsonUtility.FromJson<LevelData>(assets.levels[0].text)).Goals.Keys.First());
   for(int level=0;level<assets.levels.Length;level++){var data=JsonUtility.FromJson<LevelData>(assets.levels[level].text);var sample=new BoardModel(data);if(!sample.Pieces.Values.Any(p=>p.ownerId!=0&&!p.IsAnchor))continue;
    Invalid(level,"shared_hp",b=>b.Pieces.Values.First(p=>p.ownerId!=0&&!p.IsAnchor).hp++,"Invalid shared obstacle owner");
    Invalid(level,"shared_missing_member",b=>{var p=b.Pieces.Values.First(q=>q.ownerId!=0&&!q.IsAnchor);b.Pieces.Remove(b.Key(p.x,p.y));},"Incomplete obstacle footprint");
    Invalid(level,"shared_broken_cell",b=>{var p=b.Pieces.Values.First(q=>q.ownerId!=0&&!q.IsAnchor);var target=b.Pieces.Values.First(q=>q.family=="gem");b.Pieces.Remove(b.Key(p.x,p.y));b.Pieces.Remove(b.Key(target.x,target.y));p.x=target.x;p.y=target.y;b.Pieces.Add(b.Key(p.x,p.y),p);},"Broken footprint");
    var repair=new BoardModel(data);var member=repair.Pieces.Values.First(p=>p.ownerId!=0&&!p.IsAnchor);int hp=member.hp;member.hp++;
    Check(ValidationError(repair).EndsWith("Invalid shared obstacle owner",StringComparison.Ordinal),"Failed footprint validation exercises reusable owner/count maps");
    Check(((System.Collections.IDictionary)typeof(BoardModel).GetField("footprintOwners",Private).GetValue(repair)).Count==0&&((System.Collections.IDictionary)typeof(BoardModel).GetField("footprintCounts",Private).GetValue(repair)).Count==0,"Failed footprint validation releases owner/count scratch");
    member.hp=hp;Check(ValidationError(repair)=="OK","Same-instance footprint repair validates after failure");break;
   }
   var repaired=new BoardModel(JsonUtility.FromJson<LevelData>(assets.levels[0].text));var gem=repaired.Pieces.Values.First(p=>p.family=="gem");gem.color=9;Check(ValidationError(repaired).EndsWith("Invalid gem color",StringComparison.Ordinal),"Failed validation exercised reused scratch");gem.color=0;Check(ValidationError(repaired)=="OK","Validation scratch resets after failure");
  }
  static void PairControls(){
   int[][] pairs={new[]{4,5},new[]{4,21},new[]{21,21},new[]{7,4},new[]{7,21},new[]{7,7},new[]{11,5},new[]{11,21},new[]{11,11},new[]{7,11},new[]{16,5},new[]{16,21},new[]{16,11},new[]{7,16}};
   foreach(int level in new[]{0,13,25,47,49})foreach(var pair in pairs){
    ModelWork78Proof.Prepared Make(bool old){var model=new BoardModel(JsonUtility.FromJson<LevelData>(assets.levels[level].text)){VerificationUseCheckpoint77Model78=old};var a=model.Pieces.Values.First(p=>p.family=="gem"&&model.At(p.x+1,p.y)?.family=="gem");var b=model.At(a.x+1,a.y);model.InjectReviewPower(a.x,a.y,pair[0]);model.InjectReviewPower(b.x,b.y,pair[1]);return new ModelWork78Proof.Prepared{name="L"+(level+1)+"_pair"+pair[0]+"_"+pair[1],model=model,from=new Cell(a.x,a.y),to=new Cell(b.x,b.y)};}
    Compare(Make(false),Make(true));report.pairCases++;
   }
  }
  static void PlannerControls(){
   foreach(int level in new[]{0,13,25,47,49})foreach(int kind in Enumerable.Range(0,22)){
    var board=new BoardModel(JsonUtility.FromJson<LevelData>(assets.levels[level].text));var origin=board.Pieces.Values.First(p=>p.family=="gem");board.InjectReviewPower(origin.x,origin.y,7);var live=new LiveBoardInput(board,origin,null);var request=new Activation{kind=kind,color=-1};
    board.VerificationUseCheckpoint77Model78=true;string old=JsonUtility.ToJson(LivePowerPlan.Build(board,request,live));board.VerificationUseCheckpoint77Model78=false;string now=JsonUtility.ToJson(LivePowerPlan.Build(board,request,live));Check(old==now,"Exact direct planner priority/filter output L"+(level+1)+"/"+kind);report.plannerCases++;
   }
  }
  static double Median(IEnumerable<double> values){var v=values.OrderBy(x=>x).ToArray();return v.Length%2==0?(v[v.Length/2-1]+v[v.Length/2])*.5:v[v.Length/2];}
  static void Timings(){
   foreach(string name in ModelWork78Proof.BenchmarkNames){var timing=new Timing{name=name};for(int warm=0;warm<2;warm++){ModelWork78Proof.Measure(ModelWork78Proof.Prepare(assets,name,true),false);ModelWork78Proof.Measure(ModelWork78Proof.Prepare(assets,name),false);}
    for(int n=0;n<12;n++){var old=ModelWork78Proof.Prepare(assets,name,true);var current=ModelWork78Proof.Prepare(assets,name);ModelWork78Proof.Sample a,b;int ga,gb;bool controlFirst=n%2==0;
     if(controlFirst){int gc=GC.CollectionCount(0);a=ModelWork78Proof.Measure(old,false);ga=GC.CollectionCount(0)-gc;gc=GC.CollectionCount(0);b=ModelWork78Proof.Measure(current,false);gb=GC.CollectionCount(0)-gc;}else{int gc=GC.CollectionCount(0);b=ModelWork78Proof.Measure(current,false);gb=GC.CollectionCount(0)-gc;gc=GC.CollectionCount(0);a=ModelWork78Proof.Measure(old,false);ga=GC.CollectionCount(0)-gc;}
     Check(JsonUtility.ToJson(a.turn)==JsonUtility.ToJson(b.turn)&&JsonUtility.ToJson(old.model.Checkpoint())==JsonUtility.ToJson(current.model.Checkpoint()),"Alternating pair outcome/RNG parity "+name+"/"+n);timing.pairs.Add(new Pair{index=n,controlFirst=controlFirst,controlMs=a.milliseconds,currentMs=b.milliseconds,controlCollections=ga,currentCollections=gb});
    }
    timing.controlMedianMs=Median(timing.pairs.Select(p=>p.controlMs));timing.currentMedianMs=Median(timing.pairs.Select(p=>p.currentMs));timing.controlMaxMs=timing.pairs.Max(p=>p.controlMs);timing.currentMaxMs=timing.pairs.Max(p=>p.currentMs);timing.slowerPairs=timing.pairs.Count(p=>p.currentMs>p.controlMs);report.timings.Add(timing);
   }
  }
  public static void Run(){
   report=new Report{utc=DateTime.UtcNow.ToString("o")};try{SourceProof();var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");assets=ui.boards;Check(assets.levels.Length==50,"All50 authored boards");
    var frozen=JsonUtility.FromJson<ArchivedReport>(File.ReadAllText(Path.GetFullPath("../Verification/Evidence/Gameplay77/Native/ModelCommands.json")));Check(frozen.status=="PASS_NATIVE_MODEL_COMMANDS75"&&frozen.rows.Count==350,"Sealed77 native350 model rows");var expected=frozen.rows.ToDictionary(r=>r.name);
    for(int level=0;level<50;level++)foreach(int kind in new[]{-1,4,5,7,11,16,21}){var current=ModelWork78Proof.Corpus(assets,level,kind);var control=ModelWork78Proof.Corpus(assets,level,kind,true);var prior=expected[current.name];report.rows.Add(Compare(current,control,prior.turnHash,prior.finalHash));report.modelCases++;}
    SnapshotControls();InvalidControls();PairControls();PlannerControls();Timings();Check(report.modelCases==350&&report.pairCases==70&&report.plannerCases==110&&report.timings.Count==8,"Required corpus/pair/planner/timing coverage");
   }catch(Exception error){report.errors.Add(error.ToString());}
   report.status=report.errors.Count==0?"PASS_NATIVE_MODEL_WORK78":"FAIL_NATIVE_MODEL_WORK78";string root=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY78_OUTPUT");if(string.IsNullOrEmpty(root))root=Path.GetFullPath("../Verification/Evidence/Gameplay78");string dir=Path.Combine(root,"Native");Directory.CreateDirectory(dir);File.WriteAllText(Path.Combine(dir,"ModelWork78.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.errors.Count==0?0:1);
  }
 }
}
#endif

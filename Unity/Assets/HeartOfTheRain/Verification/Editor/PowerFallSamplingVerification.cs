#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using Motion=HeartOfTheRain.M46.Motion;
namespace HeartOfTheRain.Verification {
 public static class PowerFallSamplingVerification {
  [Serializable] public sealed class FamilyRow {public string family;public int hpLayers,cases,samples,comparedDraws;}
  [Serializable] public sealed class ActualRow {public string name,turnBeforeHash,turnAfterHash,finalBeforeHash,finalAfterHash;public int steps,samples,comparedDraws;}
  [Serializable] public sealed class TimingRow {
   public string name,scope="Alternating warmed native SampleLive only; same real phase/times, separate samplers and profiles. No lookup, mesh upload, rendering, GPU or device performance claim.";
   public int pairs,samplesPerBatch,currentSlowerPairs;public double legacyMedianMs,currentMedianMs,legacyP95Ms,currentP95Ms;
   public List<double> legacyMs=new List<double>(),currentMs=new List<double>();
  }
  [Serializable] public sealed class Report {
   public string status,utc,unity,error,scope="Native Editor bit-exact archived76/current draw sampling, actual model input immutability and matched warmed sampler CPU spans. No Unity camera/device timing or allocation measurement claim.";
   public string archivedMainSHA256,archivedAdvancedSHA256,compiledMainSHA256,compiledAdvancedSHA256;
   public bool compiledSourceMatchesArchive,rawTurnParity=true,finalSnapshotParity=true;
   public int checks,familyCases,familySamples,actualTurns,actualSamples,comparedDraws,controlSamples,negativeControls,syntheticDelayCases,coldFallbackSamples;
   public List<FamilyRow> families=new List<FamilyRow>();public List<ActualRow> actualRows=new List<ActualRow>();public List<TimingRow> timings=new List<TimingRow>();
  }
  sealed class Fixture {public string name;public LevelData level;public TurnResult turn;public BoardSnapshot final;}
  [Serializable] sealed class Steps {public List<BoardStep> steps;}
  static Report report;static GameplayUIAssets assets;static readonly Dictionary<string,string> profileText=new Dictionary<string,string>();
  static void Check(bool ok,string message){report.checks++;if(!ok)throw new Exception(message);}
  static string Hash(byte[] data){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(data)).Replace("-","").ToLowerInvariant();}
  static string Hash(string text)=>Hash(Encoding.UTF8.GetBytes(text));
  static string Json(TurnResult turn)=>JsonUtility.ToJson(turn);
  static string Json(BoardSnapshot snapshot)=>JsonUtility.ToJson(snapshot);
  static string DrawHash(List<DrawSprite> draws){
   using(var memory=new MemoryStream())using(var writer=new BinaryWriter(memory)){
    writer.Write(draws.Count);foreach(var d in draws){writer.Write(d.bank??"");writer.Write(d.key??"");writer.Write(d.atlas);writer.Write(d.order);writer.Write(d.pieceId);
     writer.Write(d.age);writer.Write(d.x);writer.Write(d.y);writer.Write(d.sx);writer.Write(d.sy);writer.Write(d.angle);writer.Write(d.alpha);writer.Write(d.glow);writer.Write(d.masked);writer.Write(d.uiOverlay);writer.Write(d.red);writer.Write(d.green);writer.Write(d.blue);}
    writer.Flush();return Hash(memory.ToArray());
   }
  }
  static DebrisProfile Profile(string text){var p=JsonUtility.FromJson<DebrisProfile>(text);foreach(var piece in p.pieces){if(piece.scaleMultiplier<=0)piece.scaleMultiplier=1;if(piece.spinMultiplier<=0)piece.spinMultiplier=1;}return p;}
  static BoardPresentation Current(int columns=9,int rows=9,int viewport=0,bool control=false,bool prepare=true){
   var p=new BoardPresentation{columns=columns,rows=rows,VerificationUseCheckpoint76Sampling=control};Bounds(p,viewport);
   foreach(var entry in profileText)p.profiles.Add(entry.Key,Profile(entry.Value));if(prepare)p.PrepareDebrisGeometry();return p;
  }
  static FrozenBoardPresentation76 Legacy(int columns=9,int rows=9,int viewport=0){
   var p=new FrozenBoardPresentation76{columns=columns,rows=rows};Bounds(p,viewport);
   foreach(var entry in profileText)p.profiles.Add(entry.Key,Profile(entry.Value));p.PrepareDebrisGeometry();return p;
  }
  static void Bounds(BoardPresentation p,int viewport){p.left=viewport==0?-1:viewport==1?-.25f:-3;p.right=viewport==0?11:viewport==1?8.25f:14;p.bottom=viewport==0?-5:viewport==1?-.1f:-10;p.goalTargets["pod"]=new Vector2(2,11);p.goalTargets["rainlight"]=new Vector2(6,12);}
  static void Bounds(FrozenBoardPresentation76 p,int viewport){p.left=viewport==0?-1:viewport==1?-.25f:-3;p.right=viewport==0?11:viewport==1?8.25f:14;p.bottom=viewport==0?-5:viewport==1?-.1f:-10;p.goalTargets["pod"]=new Vector2(2,11);p.goalTargets["rainlight"]=new Vector2(6,12);}
  static string Region(string text,string name){string begin="// BEGIN EXACT76 "+name,end="// END EXACT76 "+name;int first=text.IndexOf(begin,StringComparison.Ordinal),last=text.IndexOf(end,StringComparison.Ordinal);Check(first>=0&&last>first,"Independent compiled76 region exists: "+name);return text.Substring(first+begin.Length,last-first-begin.Length).Trim();}
  static string AdaptMain(string text){text=text.Replace("\r\n","\n");int first=text.IndexOf("    public sealed partial class BoardPresentation",StringComparison.Ordinal);return ("namespace HeartOfTheRain.M46 {\n"+text.Substring(first)).Replace("partial class BoardPresentation","partial class FrozenBoardPresentation76").Trim();}
  static string AdaptAdvanced(string text){text=text.Replace("\r\n","\n");return text.Substring(text.IndexOf("namespace HeartOfTheRain.M46",StringComparison.Ordinal)).Replace("partial class BoardPresentation","partial class FrozenBoardPresentation76").Trim();}
  static void FrozenProof(){
   string basePath=Path.GetFullPath("../.verification-cache/Gameplay77/BaselineSources/Unity/Assets/HeartOfTheRain/");
   var main=File.ReadAllBytes(Path.Combine(basePath,"M46/Runtime/BoardPresentation.cs"));var advanced=File.ReadAllBytes(Path.Combine(basePath,"M48/Runtime/AdvancedObstaclePresentationPure.cs"));
   report.archivedMainSHA256=Hash(main);report.archivedAdvancedSHA256=Hash(advanced);
   Check(report.archivedMainSHA256=="f1efb88987ae1e5ec1156c1049380fc8df2f91571fbb6471ef9730f1834ab38a","Exact archived76 main sampler source binding");
   Check(report.archivedAdvancedSHA256=="5e780b22019e6880966b1ee25e39a48e059435e0b9afb1a093ee2febfa459005","Exact archived76 advanced partial source binding");
   string own=File.ReadAllText("Assets/HeartOfTheRain/Verification/PowerFall76Control.cs").Replace("\r\n","\n");
   var a=Region(own,"BoardPresentation.cs");var b=Region(own,"AdvancedObstaclePresentationPure.cs");
   report.compiledSourceMatchesArchive=a==AdaptMain(Encoding.UTF8.GetString(main))&&b==AdaptAdvanced(Encoding.UTF8.GetString(advanced));Check(report.compiledSourceMatchesArchive,"Compiled control only renames both classes and shares existing DTO declarations");
   report.compiledMainSHA256=Hash(a);report.compiledAdvancedSHA256=Hash(b);
  }
  public static void Run(){
   report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};
   try{
    FrozenProof();assets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");Check(assets!=null&&assets.boards.levels.Length==50,"Actual approved asset and50-level bindings");
    profileText.Clear();foreach(var entry in assets.boards.debrisProfiles)profileText.Add(entry.family,entry.metadata.text);
    FamilyProof();SyntheticDelayProof();ColdFallbackProof();HashNegativeControls();
    var fixtures=Fixtures();foreach(var fixture in fixtures)ActualProof(fixture);
    foreach(var fixture in fixtures.Where(f=>f.name.EndsWith("45",StringComparison.Ordinal)||f.name=="L4_match"||f.name=="L31_match"))Timing(fixture);
    Check(report.familyCases>1000&&report.familySamples>20000&&report.actualTurns==18&&report.actualSamples>1000,"Broad authored layers/kinds/bounds/time and18 real turn samples completed");
    Check(report.timings.Count==6&&report.controlSamples==report.familySamples+report.actualSamples+report.syntheticDelayCases+report.coldFallbackSamples,"All native sampler controls exercised without omitting a slow row");
    report.status="PASS_NATIVE_POWER_FALL_SAMPLING77";
   }catch(Exception e){report.status="FAIL_NATIVE_POWER_FALL_SAMPLING77";report.error=e.ToString();}
   string output=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY77_OUTPUT");if(string.IsNullOrEmpty(output))output=Path.GetFullPath("../Verification/Evidence/Gameplay77");output=Path.Combine(output,"Native");Directory.CreateDirectory(output);
   File.WriteAllText(Path.Combine(output,"PowerFallSampling.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.error==null?0:1);
  }
  static BoardStep Hit(string family,int hp,int kind,int viewport,bool vertical){
   int x=viewport==0?0:viewport==1?4:8,y=viewport==0?0:viewport==1?4:8;var piece=new Piece{id=1,x=x,y=y,family=family,hp=hp};
   var before=new BoardSnapshot{pieces=new[]{piece},goals=new[]{new Goal{family=family,count=1}},moves=20,status="Playing"};var after=new BoardSnapshot{pieces=hp>1?new[]{new Piece{id=1,x=x,y=y,family=family,hp=hp-1}}:Array.Empty<Piece>(),goals=before.goals,moves=19,status="Playing"};
   var step=new BoardStep{kind="powerFall",duration=4,before=before,after=after,powerPlan=new ReviewPlan{kind=kind,columns=9,rows=9,rocketVertical=vertical,effects=Array.Empty<ReviewFx>(),beams=Array.Empty<ReviewBeam>(),powers=Array.Empty<ReviewPower>(),tiles=Array.Empty<ReviewTile>()}};
   step.damage.Add(new Damage{id=1,x=x,y=y,family=family,beforeHP=hp,afterHP=hp-1,time=.04f});if(hp==1)step.removed.Add(new Removed{piece=piece,time=.04f,cause="obstacle"});return step;
  }
  static float[] Times(BoardStep step,DebrisProfile profile=null){
   var times=new HashSet<float>{0,.03999f,.04f,.04001f,.065f,.1f,.14f,.18f,.24f,.28f,.4f,.5f,.64f,.8f,.84f,1f,1.04f,1.2f,2f,3f,4f,6f,8f};
   if(profile!=null)foreach(var damage in step.damage)foreach(var p in profile.pieces){float at=damage.time+(damage.family=="crystal"||damage.family=="pod"?.1f:0)+p.launchDelay+.012f*((damage.x*31+damage.y*17)%11%4);times.Add(at-.00001f);times.Add(at);times.Add(at+.00001f);}
   foreach(var m in step.motion)foreach(float at in new[]{m.delay,m.delay+m.seconds,m.delay+m.seconds+m.landing}){times.Add(at-.00001f);times.Add(at);times.Add(at+.00001f);}
   if(step.duration>0){times.Add(step.duration-.00001f);times.Add(step.duration);times.Add(step.duration+.00001f);}
   return times.Where(t=>t>=0).OrderBy(t=>t).ToArray();
  }
  static int Compare(BoardPresentation current,BoardPresentation control,FrozenBoardPresentation76 legacy,BoardStep step,BoardSnapshot idle,float time,float start,string label){
   var a=legacy.SampleLive(step,idle,time,start);string before=DrawHash(a);int count=a.Count;
   var b=current.SampleLive(step,idle,time,start);Check(before==DrawHash(b),"Bit-exact draw list vs compiled76: "+label+"@"+time.ToString("R"));
   var c=control.SampleLive(step,idle,time,start);Check(before==DrawHash(c),"Same-APK76 sampling control: "+label);report.controlSamples++;report.comparedDraws+=count;return count;
  }
  static void FamilyProof(){
   foreach(var entry in profileText){var profile=Profile(entry.Value);var layers=entry.Key=="crate"?new[]{1,2,3}:profile.pieces.Select(p=>p.beforeHP).Where(h=>h>0).Concat(new[]{1}).Distinct().OrderBy(h=>h).ToArray();var row=new FamilyRow{family=entry.Key,hpLayers=layers.Length};
    foreach(int viewport in new[]{0,1,2}){
     var current=Current(viewport:viewport);var control=Current(viewport:viewport,control:true);var legacy=Legacy(viewport:viewport);
     foreach(int hp in layers)foreach(int kind in Enumerable.Range(0,22))foreach(bool vertical in new[]{false,true}){
      current.history.Clear();control.history.Clear();legacy.history.Clear();var step=Hit(entry.Key,hp,kind,viewport,vertical);current.Add(step,0);control.Add(step,0);legacy.Add(step,0);
      foreach(float t in Times(step,profile)){row.comparedDraws+=Compare(current,control,legacy,step,step.before,t,0,entry.Key+"/"+hp+"/"+kind+"/"+viewport+"/"+vertical);row.samples++;report.familySamples++;}
      row.cases++;report.familyCases++;
     }
    }
    report.families.Add(row);
   }
   // Cabinet uses its own star accent rather than a DebrisProfile.
   var cabinet=new FamilyRow{family="cabinet",hpLayers=3};foreach(int hp in new[]{1,2,5})foreach(int viewport in new[]{0,1,2}){var a=Current(viewport:viewport);var b=Current(viewport:viewport,control:true);var c=Legacy(viewport:viewport);var s=Hit("cabinet",hp,4,viewport,false);a.Add(s,0);b.Add(s,0);c.Add(s,0);foreach(float t in Times(s)){cabinet.comparedDraws+=Compare(a,b,c,s,s.before,t,0,"cabinet/"+hp);cabinet.samples++;report.familySamples++;}cabinet.cases++;report.familyCases++;}report.families.Add(cabinet);
  }
  static void SyntheticDelayProof(){
   // Multiple equal-age fragments exercise shared Exp; nonzero delays retain
   // their distinct call/age. Signed-zero and adjacent-float boundaries remain exact.
   foreach(float delay in new[]{0f,BitConverter.ToSingle(BitConverter.GetBytes(int.MinValue),0),.018f,.036f}){
    var a=Current();var b=Current(control:true);var c=Legacy();foreach(var profile in new[]{a.profiles["stone"],b.profiles["stone"],c.profiles["stone"]}){foreach(var piece in profile.pieces)piece.launchDelay=piece.beforeHP==1?delay:piece.launchDelay;}
    var s=Hit("stone",1,21,1,false);a.Add(s,0);b.Add(s,0);c.Add(s,0);foreach(float t in Times(s,a.profiles["stone"])){Compare(a,b,c,s,s.before,t,0,"synthetic-delay/"+delay);report.syntheticDelayCases++;}
   }
  }
  static void HashNegativeControls(){
   var d=new DrawSprite{bank="body",key="tile0",pieceId=7,x=2,y=3,sx=1,sy=1,masked=true};var list=new List<DrawSprite>{d};string before=DrawHash(list);
   d.x=BitConverter.ToSingle(BitConverter.GetBytes(BitConverter.ToInt32(BitConverter.GetBytes(d.x),0)+1),0);Check(before!=DrawHash(list),"Draw signature rejects a one-ULP position change");report.negativeControls++;
   d.x=2;d.blue=.5f;Check(before!=DrawHash(list),"Draw signature rejects changed tint");report.negativeControls++;
   d.blue=1;d.masked=false;Check(before!=DrawHash(list),"Draw signature rejects changed portal masking");report.negativeControls++;
   d.masked=true;d.key="tile1";Check(before!=DrawHash(list),"Draw signature rejects changed sprite key");report.negativeControls++;
  }
  static void ColdFallbackProof(){
   foreach(string family in profileText.Keys){var a=Current(prepare:false);var b=Current(control:true,prepare:false);var c=Legacy();var s=Hit(family,1,5,1,true);a.Add(s,0);b.Add(s,0);c.Add(s,0);foreach(float t in Times(s,a.profiles[family])){Compare(a,b,c,s,s.before,t,0,"cold-fallback/"+family);report.coldFallbackSamples++;}}
  }
  static List<Fixture> Fixtures(){
   var fixtures=new List<Fixture>();var source=JsonUtility.FromJson<LevelData>(assets.boards.levels[25].text);
   foreach(string family in ObstacleDensityFixture.Families)foreach(int count in new[]{1,45}){var board=new BoardModel(ObstacleDensityFixture.Level(source,count,family));var turn=ObstacleDensityFixture.Solve(board);fixtures.Add(new Fixture{name="density_"+family+"_"+count,level=board.Level,turn=turn,final=board.Snapshot()});}
   foreach(int level in new[]{4,14,31,33}){var board=new BoardModel(JsonUtility.FromJson<LevelData>(assets.boards.levels[level-1].text));var swap=board.LegalSwaps().First();var turn=board.Swap(swap[0].x,swap[0].y,swap[1].x,swap[1].y);fixtures.Add(new Fixture{name="L"+level+"_match",level=board.Level,turn=turn,final=board.Snapshot()});}
   foreach(int power in new[]{4,5,21,7,11,16}){var board=new BoardModel(MixedPowerSwapFixtures.Match(4));var from=MixedPowerSwapFixtures.From(4);var to=MixedPowerSwapFixtures.To();Check(board.InjectReviewPower(to.x,to.y,power),"Mixed sampling source installed "+power);var turn=board.Swap(from.x,from.y,to.x,to.y);fixtures.Add(new Fixture{name="mixed_"+power,level=board.Level,turn=turn,final=board.Snapshot()});}
   return fixtures;
  }
  static void ActualProof(Fixture fixture){
   Check(fixture.turn.accepted,"Actual sampled turn accepted "+fixture.name);var row=new ActualRow{name=fixture.name,turnBeforeHash=Hash(Json(fixture.turn)),finalBeforeHash=Hash(Json(fixture.final))};
   var steps=BoardPlayback.Build(fixture.turn.steps,fixture.level);var a=Current(fixture.level.columns,fixture.level.rows);var b=Current(fixture.level.columns,fixture.level.rows,control:true);var c=Legacy(fixture.level.columns,fixture.level.rows);float start=0;
   foreach(var step in steps){a.Add(step,start);b.Add(step,start);c.Add(step,start);foreach(float age in Times(step).Where(t=>t<=step.duration)){
     row.comparedDraws+=Compare(a,b,c,step,step.before,start+age,start,fixture.name+"/"+row.steps);row.samples++;report.actualSamples++;
    }start+=step.duration;row.steps++;}
   foreach(float tail in new[]{0f,.025f,.05f,.1f,.2f,.5f,1f}){row.comparedDraws+=Compare(a,b,c,null,fixture.final,start+tail,start,fixture.name+"/idle");row.samples++;report.actualSamples++;}
   row.turnAfterHash=Hash(Json(fixture.turn));row.finalAfterHash=Hash(Json(fixture.final));bool raw=row.turnBeforeHash==row.turnAfterHash,final=row.finalBeforeHash==row.finalAfterHash;report.rawTurnParity&=raw;report.finalSnapshotParity&=final;Check(raw&&final,"Sampling never changes raw turn/final snapshot "+fixture.name);report.actualTurns++;report.actualRows.Add(row);
  }
  static double Median(List<double> values,double quantile){var sorted=values.OrderBy(v=>v).ToArray();return sorted[(int)Math.Floor((sorted.Length-1)*quantile)];}
  static double Batch(BoardPresentation sampler,BoardStep phase,float[] times){long at=System.Diagnostics.Stopwatch.GetTimestamp();foreach(float t in times)sampler.SampleLive(phase,phase.before,t,0);return (System.Diagnostics.Stopwatch.GetTimestamp()-at)*1000.0/System.Diagnostics.Stopwatch.Frequency;}
  static double Batch(FrozenBoardPresentation76 sampler,BoardStep phase,float[] times){long at=System.Diagnostics.Stopwatch.GetTimestamp();foreach(float t in times)sampler.SampleLive(phase,phase.before,t,0);return (System.Diagnostics.Stopwatch.GetTimestamp()-at)*1000.0/System.Diagnostics.Stopwatch.Frequency;}
  static void Timing(Fixture fixture){
   var phase=BoardPlayback.Build(fixture.turn.steps,fixture.level).Where(s=>s.kind=="powerFall").OrderByDescending(s=>s.motion.Count+s.damage.Count*3).First();
   var a=Current(fixture.level.columns,fixture.level.rows);var b=Legacy(fixture.level.columns,fixture.level.rows);a.ReserveDrawCapacity(2048);b.ReserveDrawCapacity(2048);a.Add(phase,0);b.Add(phase,0);
   float[] times=Enumerable.Range(0,16).Select(i=>phase.duration*i/15).ToArray();for(int i=0;i<8;i++){Batch(a,phase,times);Batch(b,phase,times);}
   var row=new TimingRow{name=fixture.name,pairs=32,samplesPerBatch=times.Length};for(int i=0;i<row.pairs;i++){double old,current;if((i&1)==0){old=Batch(b,phase,times);current=Batch(a,phase,times);}else{current=Batch(a,phase,times);old=Batch(b,phase,times);}row.legacyMs.Add(old);row.currentMs.Add(current);if(current>old)row.currentSlowerPairs++;}
   row.legacyMedianMs=Median(row.legacyMs,.5);row.currentMedianMs=Median(row.currentMs,.5);row.legacyP95Ms=Median(row.legacyMs,.95);row.currentP95Ms=Median(row.currentMs,.95);report.timings.Add(row);
  }
 }
}

#endif

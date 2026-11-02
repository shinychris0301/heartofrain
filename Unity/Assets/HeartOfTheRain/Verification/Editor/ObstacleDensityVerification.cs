#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 public static class ObstacleDensityVerification {
  [Serializable] public class Row {public int count,damage,cleared,maxDraws,samples,originX,originY;public string turnHash,finalHash,poseHash;public double sampleMs,peakSampleMs,modelMs;}
  [Serializable] public class Report {public string status,utc,phase,error,scope="Native Unity Editor fixed geometry/seed/one-layer crate density controls with fixed swap cells (4,5)/(5,5). Before selects current same-source legacy calculations; After selects optimized calculations. CPU sampler microbenchmark excludes renderer, GPU and Android. Full real turns/final states/draw signatures compare paths.";public int checks;public List<Row> rows=new List<Row>();}
  public static void Before()=>Run("Before");public static void After()=>Run("After");
  public static void Compare(){
   var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");var b=new BoardModel(ObstacleDensityFixture.Level(JsonUtility.FromJson<LevelData>(ui.boards.levels[25].text),45));var steps=BoardPlayback.Build(ObstacleDensityFixture.Solve(b).steps,b.Level);
   var old=CrateBurstVerification.View(ui,b.Level.columns,b.Level.rows);old.VerificationUseLegacyDensityWork=true;var next=CrateBurstVerification.View(ui,b.Level.columns,b.Level.rows);float start=0;int differences=0;float max=0;var text=new StringBuilder();
   foreach(var step in steps){old.Add(step,start);next.Add(step,start);int samples=Math.Max(1,Mathf.CeilToInt(step.duration*60));for(int i=0;i<samples;i++){float at=start+step.duration*(i+.1f)/samples;old.PruneHistory(at);next.PruneHistory(at);var a=old.SampleLive(step,step.before,at,start);var c=next.SampleLive(step,step.before,at,start);if(a.Count!=c.Count)throw new Exception("Draw counts differ");for(int j=0;j<a.Count;j++){var x=JsonUtility.ToJson(a[j]);var y=JsonUtility.ToJson(c[j]);if(x==y)continue;differences++;max=Math.Max(max,Math.Max(Math.Abs(a[j].x-c[j].x),Math.Abs(a[j].y-c[j].y)));if(differences<=6)text.Append(at+" old "+x+"\n new "+y+"\n");}}
    start+=step.duration;
   }
   text.Insert(0,"Differences "+differences+"; maximum coordinate delta "+max+"\n");File.WriteAllText(Path.GetFullPath("../Verification/Evidence/ObstacleDensity/Comparison_Diagnostic.txt"),text.ToString());EditorApplication.Exit(0);
  }
  static string Hash(string value){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(Encoding.UTF8.GetBytes(value))).Replace("-","").ToLowerInvariant();}
  static void Run(string phase){
   var report=new Report{utc=DateTime.UtcNow.ToString("o"),phase=phase};string folder=Path.GetFullPath("../Verification/Evidence/ObstacleDensity/"+phase);Directory.CreateDirectory(folder);
   try{
    var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");var source=JsonUtility.FromJson<LevelData>(ui.boards.levels[25].text);
    foreach(int count in new[]{1,8,16,32,45}){
     var b=new BoardModel(ObstacleDensityFixture.Level(source,count));var watch=Stopwatch.StartNew();var turn=ObstacleDensityFixture.Solve(b);watch.Stop();if(!turn.accepted)throw new Exception("Rejected density "+count);b.Validate();
     var row=new Row{count=count,turnHash=Hash(JsonUtility.ToJson(turn)),finalHash=Hash(JsonUtility.ToJson(b.Snapshot())),modelMs=watch.Elapsed.TotalMilliseconds,damage=turn.steps.Sum(s=>s.damage.Count(d=>d.family=="crate")),cleared=turn.steps.Sum(s=>s.removed.Count(r=>r.piece.family=="crate"))};
     if(row.cleared!=count)throw new Exception("Fixture does not clear the required count");report.checks++;
     var power=turn.steps.First(s=>s.powerPlan!=null).powerPlan;row.originX=power.originX;row.originY=power.originY;
     var steps=BoardPlayback.Build(turn.steps,b.Level);var view=CrateBurstVerification.View(ui,b.Level.columns,b.Level.rows);view.VerificationUseLegacyDensityWork=phase=="Before";view.ReserveDrawCapacity(GameplayScreen.WarmRendererCapacity(b.Level.columns,b.Level.rows,b.Snapshot())+count*10);float start=0;var signature=new StringBuilder();BoardStep peak=null;float peakTime=0,peakStart=0;
     foreach(var step in steps){view.Add(step,start);int samples=Math.Max(1,Mathf.CeilToInt(step.duration*60));for(int i=0;i<samples;i++){float at=start+step.duration*(i+.1f)/samples;view.PruneHistory(at);watch.Restart();var draws=view.SampleLive(step,step.before,at,start);watch.Stop();row.sampleMs+=watch.Elapsed.TotalMilliseconds;row.samples++;if(draws.Count>row.maxDraws){row.maxDraws=draws.Count;peak=step;peakTime=at;peakStart=start;}foreach(var d in draws)signature.Append(JsonUtility.ToJson(d)).Append('\n');}start+=step.duration;}
     row.poseHash=Hash(signature.ToString());row.sampleMs/=row.samples;
     // Fresh retained history for a repeatable peak workload, not the pruned tail.
     view=CrateBurstVerification.View(ui,b.Level.columns,b.Level.rows);view.VerificationUseLegacyDensityWork=phase=="Before";view.ReserveDrawCapacity(row.maxDraws);start=0;foreach(var step in steps){view.Add(step,start);start+=step.duration;if(step==peak)break;}
     for(int i=0;i<30;i++)view.SampleLive(peak,peak.before,peakTime,peakStart);watch.Restart();for(int i=0;i<1024;i++)view.SampleLive(peak,peak.before,peakTime,peakStart);watch.Stop();row.peakSampleMs=watch.Elapsed.TotalMilliseconds/1024;report.rows.Add(row);
    }
    if(phase=="After"){var before=JsonUtility.FromJson<Report>(File.ReadAllText(Path.Combine(folder,"../Before/Report.json")));if(before.status!="PASS_NATIVE_OBSTACLE_DENSITY")throw new Exception("Baseline failed");foreach(var row in report.rows){var old=before.rows.Single(r=>r.count==row.count);if(old.turnHash!=row.turnHash||old.finalHash!=row.finalHash||old.poseHash!=row.poseHash)throw new Exception("Changed density semantics/poses "+row.count);report.checks++;}}
    report.status="PASS_NATIVE_OBSTACLE_DENSITY";
   }catch(Exception e){report.status="FAIL_NATIVE_OBSTACLE_DENSITY";report.error=e.ToString();}
   File.WriteAllText(Path.Combine(folder,"Report.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.error==null?0:1);
  }
 }
}
#endif

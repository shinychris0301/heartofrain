#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 public static class IndividualFallVerification {
  [Serializable] class Report {public string utc,status,scope="Native Unity continuous-route, stagger, snapshot and sampled body checks. Device rendering is separate.";public int checks,routes,bentRoutes;public double maxBuildMs,maxBuildWithoutGC;public string slowestBuild;public float maxStepSeconds;public List<string> failures=new List<string>();}
  public static void Run(){
   var r=new Report{utc=DateTime.UtcNow.ToString("o")};void Check(bool ok,string label){r.checks++;if(!ok&&r.failures.Count<100)r.failures.Add(label);}
   bool recorded=false;try {
    var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
    void Inspect(BoardModel b,TurnResult turn,string label){
     string raw=JsonUtility.ToJson(turn),state=JsonUtility.ToJson(b.Snapshot());int gc=GC.CollectionCount(0);var timer=System.Diagnostics.Stopwatch.StartNew();var schedule=BoardPlayback.Build(turn.steps,b.Level);timer.Stop();if(timer.Elapsed.TotalMilliseconds>r.maxBuildMs){r.maxBuildMs=timer.Elapsed.TotalMilliseconds;r.slowestBuild=label;}if(gc==GC.CollectionCount(0))r.maxBuildWithoutGC=Math.Max(r.maxBuildWithoutGC,timer.Elapsed.TotalMilliseconds);
     Check(raw==JsonUtility.ToJson(turn)&&state==JsonUtility.ToJson(b.Snapshot()),label+" immutable solve");
     Check(ReferenceEquals(schedule.Last().after,turn.steps.Last().after),label+" final snapshot");
     Check(!schedule.Zip(schedule.Skip(1),(a,z)=>a.kind=="gravity"&&z.kind=="gravity").Any(v=>v),label+" no gravity-wave barriers");
     foreach(var step in schedule.Where(s=>s.kind=="gravity"||s.kind=="powerFall")){
      r.maxStepSeconds=Math.Max(r.maxStepSeconds,step.duration);Check(step.duration<20,"Bounded local scheduling "+label);Check(step.motion.Select(m=>m.id).Distinct().Count()==step.motion.Count,label+" one continuous route per identity");
      var view=new BoardPresentation();float routeEnd=Math.Max(step.duration,step.motion.Count==0?0:step.motion.Max(m=>m.delay+m.seconds));
      foreach(var m in step.motion){r.routes++;if(m.path!=null){r.bentRoutes++;for(int j=1;j<m.path.Count;j++)Check(m.path[j-1].toX==m.path[j].fromX&&m.path[j-1].toY==m.path[j].fromY,label+" continuous route joint");}
       Check(m.seconds+.0001f>=TileFall.Duration(TileFall.Distance(m)),label+" acceleration spans complete route");
       var end=view.Sample(step,step.before,routeEnd+TileFall.LandingSeconds,0).SingleOrDefault(d=>d.pieceId==m.id);
       Check(end!=null&&Math.Abs(end.x-m.toX)<.001f&&Math.Abs(end.y-m.toY)<.001f&&Math.Abs(end.sx-end.sy)<.001f,label+" exact final rendered cell");
       if(m.path!=null){float distance=0;for(int j=0;j<m.path.Count-1;j++){distance+=TileFall.Distance(m.path[j]);float t=m.path[j].delay+m.path[j].seconds;float ax,ay,bx,by;TileFall.Position(m,t-.0001f,out ax,out ay);TileFall.Position(m,t+.0001f,out bx,out by);Check(Math.Abs(ax-bx)+Math.Abs(ay-by)<.02f,label+" no teleport at elbow");}}
      }
      for(int n=0;n<=100;n++){
       float t=routeEnd*n/100f;var bodies=view.Sample(step,step.before,t,0).Where(d=>step.motion.Any(m=>m.id==d.pieceId)).ToArray();
       bool clear=true;string witness="";for(int a=0;a<bodies.Length;a++)for(int z=a+1;z<bodies.Length;z++)if(Math.Abs(bodies[a].x-bodies[z].x)<.001f&&Math.Abs(bodies[a].y-bodies[z].y)<.95f){clear=false;witness=" ids "+bodies[a].pieceId+"/"+bodies[z].pieceId+" xy "+bodies[a].x+","+bodies[a].y+" / "+bodies[z].x+","+bodies[z].y;}
       if(!clear&&!recorded){recorded=true;File.WriteAllText(Path.GetFullPath("../Verification/Evidence/IndividualFall/Collision.json"),JsonUtility.ToJson(step,true));}Check(clear,label+" rendered column order sample "+n+witness);
      }
     }
    }
    foreach(int c in new[]{0,4,8}){var b=new BoardModel(PlaybackFixtures.StackedStones(c));Inspect(b,b.UseBooster(BoosterKind.Hammer,c,2,new BoosterInventory()),"Stack "+c);}
    var pocket=new BoardModel(PlaybackFixtures.LargeObstacleGap());Inspect(pocket,pocket.UseBooster(BoosterKind.Hammer,3,1,new BoosterInventory()),"Large blocked gap");
    var cabinet=new BoardModel(PlaybackFixtures.ClearingCabinet());var clear=cabinet.UseBooster(BoosterKind.Hammer,3,0,new BoosterInventory());Inspect(cabinet,clear,"Large cabinet gap");
    var refill=BoardPlayback.Build(clear.steps,cabinet.Level).First();var column=refill.motion.Where(m=>m.fromX==3&&!m.spawned).OrderBy(m=>m.fromY).ToArray();
    Check(column.Length>=3,"Large gap has a following column");Check(column.Zip(column.Skip(1),(a,b)=>b.delay-a.delay>=.034f).All(v=>v),"Existing tiles start individually");Check(column[1].delay<column[0].delay+column[0].seconds,"Following tiles overlap flights");
    for(int level=0;level<50;level++)foreach(int kind in new[]{4,5,7,11,16,21}){var b=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[level].text));var p=b.Pieces.Values.First(v=>v.family=="gem");b.InjectReviewPower(p.x,p.y,kind);Inspect(b,b.Tap(p.x,p.y),"L"+(level+1)+" P"+kind);}
    Check(r.bentRoutes>0,"Exercise stitched routes around blockers");
    var emptyPath=new HeartOfTheRain.M46.Motion{fromX=0,fromY=2,toX=0,toY=1,seconds=.15f,path=new List<FallLeg>()};float ex,ey;TileFall.Position(emptyPath,.15f,out ex,out ey);Check(TileFall.Distance(emptyPath)==1&&ey==1,"Empty serialized route retains straight-motion semantics");
    var route=refill.motion.First();route.path=new List<FallLeg>{new FallLeg{fromX=0,fromY=3,toX=0,toY=2,delay=0,seconds=.15f},new FallLeg{fromX=0,fromY=2,toX=1,toY=1,delay=.15f,seconds=.15f,distance=1}};
    float px,py;TileFall.Position(route,.2f,out px,out py);TileFall.Moving(route,.2f);TileFall.Distance(route);
    long allocated=GC.GetAllocatedBytesForCurrentThread();for(int n=0;n<10000;n++){TileFall.Position(route,.2f,out px,out py);TileFall.Moving(route,.2f);TileFall.Distance(route);}Check(GC.GetAllocatedBytesForCurrentThread()==allocated,"Per-frame route helpers allocate zero managed bytes after warmup");
   }catch(Exception e){r.failures.Add(e.ToString());}
   r.status=r.failures.Count==0?"PASS_NATIVE_INDIVIDUAL_FALL":"FAIL_NATIVE_INDIVIDUAL_FALL";var folder=Path.GetFullPath("../Verification/Evidence/IndividualFall");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"Native_Checks.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(r.failures.Count==0?0:1);
  }
 }
}
#endif

#if UNITY_EDITOR
// Native sampler/clock checks for restricted local cascade handoffs.
// Called by LocalCascadeVerification; Android visibility is verified separately.
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using Motion=HeartOfTheRain.M46.Motion;
namespace HeartOfTheRain.Verification {
 public static class LocalCascadeRendererChecks {
  [Serializable] public sealed class Row {
   public string caseName;
   public int phaseIndex,samples,carryCount;public float handoff,previousDuration,lastParticipatingContact,residualLocalWait,secondsSaved,maxBoundaryPositionJump,maxBoundaryScaleJump;
  }
  const float Epsilon=.00015f;
  static bool Near(float a,float b)=>Math.Abs(a-b)<Epsilon;
  static bool Pose(DrawSprite a,DrawSprite b)=>a.bank==b.bank&&a.key==b.key&&a.atlas==b.atlas&&Near(a.x,b.x)&&Near(a.y,b.y)&&Near(a.sx,b.sx)&&Near(a.sy,b.sy)&&Near(a.angle,b.angle)&&Near(a.alpha,b.alpha);
  static Dictionary<int,DrawSprite> Bodies(List<DrawSprite> draws,Action<bool,string> check,string label){
   var groups=draws.Where(d=>d.pieceId>0).GroupBy(d=>d.pieceId).ToArray();check(groups.All(g=>g.Count()==1),label+": one rendered body per identity");return groups.ToDictionary(g=>g.Key,g=>g.First());
  }
  static Goal[] Goals(BoardPresentation view,BoardStep current,BoardSnapshot idle,float time,float start)=>view.DisplayGoalsLive(current,idle,time-start,time).Select(g=>new Goal{family=g.family,count=g.count}).ToArray();
  static bool SameGoals(Goal[] a,Goal[] b)=>a.Length==b.Length&&a.All(g=>b.Any(h=>h.family==g.family&&h.count==g.count));
  static List<DrawSprite> Sample(BoardPresentation view,BoardStep step,float time,float start,BoardSnapshot idle)=>view.Sample(step,idle,time,start);
  static IEnumerable<int> MutationIds(BoardStep next)=>next.removed.Select(r=>r.piece.id).Concat(next.damage.Select(d=>d.id)).Concat(next.created.Select(p=>p.id));
  public static List<Row> Inspect(List<BoardStep> baseline,List<BoardStep> refined,List<LocalCascadeDecision> decisions,Action<bool,string> check){
   var rows=new List<Row>();check(baseline.Count==refined.Count,"Postpass retains phase count");if(baseline.Count!=refined.Count)return rows;
   string frozen=JsonUtility.ToJson(new Steps{steps=baseline});
   float saved=decisions.Where(d=>d.accepted).Sum(d=>d.previousDuration-d.handoff),scheduled=refined.Sum(s=>s.duration);
   check(Math.Abs(baseline.Sum(s=>s.duration)-scheduled-saved)<.0002f,"Only accepted handoff savings change total phase clock");
   foreach(int fps in new[]{15,30,60}){float wall=CascadeTimingVerification.Wall(refined,fps);check(wall+Epsilon>=scheduled&&wall<=scheduled+(fps==15?.15f:fps==30?.10f:.06f),"Full frame-clock simulation has no lost time or new cascade debt "+fps);}
   check(JsonUtility.ToJson(baseline.Last().after)==JsonUtility.ToJson(refined.Last().after),"Final model state/status/moves/goals stay identical");
   for(int k=0;k<baseline.Count;k++){
    check(JsonUtility.ToJson(baseline[k].before)==JsonUtility.ToJson(refined[k].before),"Before snapshot unchanged "+k);
    check(JsonUtility.ToJson(baseline[k].after)==JsonUtility.ToJson(refined[k].after),"After snapshot unchanged "+k);
    check(baseline[k].kind==refined[k].kind&&baseline[k].label==refined[k].label,"Phase identity unchanged "+k);
   }
   foreach(var decision in decisions.Where(d=>d.accepted)){
    int k=decision.phaseIndex;check(k>=0&&k+1<baseline.Count,"Valid handoff phase index");if(k<0||k+1>=baseline.Count)continue;
    var old=baseline[k];var previous=refined[k];var next=refined[k+1];float handoff=previous.duration;
    var carry=new HashSet<int>(decision.carryIds);var local=MutationIds(next).ToHashSet();
    var contact=old.motion.Where(m=>local.Contains(m.id)).Select(m=>m.delay+m.seconds).DefaultIfEmpty(0).Max();
    var row=new Row{phaseIndex=k,handoff=handoff,previousDuration=old.duration,lastParticipatingContact=contact,residualLocalWait=handoff-contact,secondsSaved=old.duration-handoff,carryCount=carry.Count};rows.Add(row);
    check(Near(handoff,decision.handoff)&&handoff<old.duration-.01f,"Actual shortening is represented by decision "+k);
    check(handoff+Epsilon>=contact,"Matched/changed piece contacts precede handoff "+k);
    check(carry.Count>0,"Accepted handoff has real unfinished carries "+k);
    check(!carry.Overlaps(local),"Carried IDs are disjoint from immediate mutations "+k);
    check(next.duration+handoff+Epsilon>=old.motion.Where(m=>carry.Contains(m.id)).Max(m=>m.delay+m.seconds),"Next phase covers every carried contact "+k);
    check(next.duration>0&&!float.IsNaN(next.duration)&&!float.IsInfinity(next.duration),"Finite positive destination phase "+k);
    check(FeedbackPlan.Build(old).Where(c=>c.time>handoff+Epsilon).All(c=>c.id=="tile_land"),"No pending old hit/create/collection cue is lost by the handoff "+k);
    var nextFeedback=FeedbackPlan.Build(next);
    foreach(int id in carry){
     var a=old.motion.Single(m=>m.id==id);var b=next.motion.Single(m=>m.id==id);
     check(nextFeedback.Any(c=>c.id=="tile_land"&&Math.Abs(c.time+handoff-a.delay-a.seconds)<.0601f),"A carried contact keeps a landing cue at its original absolute contact "+id);
     check(Near(a.delay,b.delay+handoff)&&Near(a.seconds,b.seconds)&&Near(a.landing,b.landing),"Carry retains contact and landing clocks "+id);
     check(Near(a.fromX,b.fromX)&&Near(a.fromY,b.fromY)&&Near(a.toX,b.toX)&&Near(a.toY,b.toY)&&a.spawned==b.spawned&&a.clipSpawn==b.clipSpawn&&a.spawnTop==b.spawnTop,"Carry retains full route/portal metadata "+id);
     if(a.path!=null){check(b.path!=null&&a.path.Count==b.path.Count,"Carry retains all path legs "+id);if(b.path!=null&&a.path.Count==b.path.Count)for(int leg=0;leg<a.path.Count;leg++){var x=a.path[leg];var y=b.path[leg];check(Near(x.delay,y.delay+handoff)&&Near(x.seconds,y.seconds)&&Near(x.distance,y.distance)&&Near(x.fromX,y.fromX)&&Near(x.fromY,y.fromY)&&Near(x.toX,y.toX)&&Near(x.toY,y.toY),"Unchanged carry leg "+id+"/"+leg);}}
     foreach(float delta in new[]{-.0001f,0f,.0001f,.001f,.016f,.033f,.10f,.2f}){
      float age=Math.Max(0,delta);TileFall.Position(a,handoff+age,out float ax,out float ay);TileFall.Position(b,age,out float bx,out float by);check(Near(ax,bx)&&Near(ay,by),"Carry route continuous at and beyond boundary "+id+"/"+delta);
     }
    }
    var oldView=new BoardPresentation();oldView.Add(old,0);
    var newView=new BoardPresentation();newView.Add(previous,0);newView.Add(next,handoff);
    foreach(var future in baseline[k+1].motion){var prior=old.motion.FirstOrDefault(m=>m.id==future.id);if(prior==null||prior.delay+prior.seconds+prior.landing<=handoff)continue;check(handoff+future.delay+Epsilon>=prior.delay+prior.seconds+prior.landing,"Next motion leaves time for original landing to finish "+future.id);}
    var oldBoundary=Bodies(Sample(oldView,old,handoff,0,old.before),check,"Before handoff boundary");
    var newBoundary=Bodies(Sample(newView,next,handoff,handoff,next.before),check,"After handoff boundary");
    foreach(var gem in old.after.pieces.Where(p=>p.family=="gem")){
     if(!oldBoundary.TryGetValue(gem.id,out var a)||!newBoundary.TryGetValue(gem.id,out var b))continue;
     float position=Math.Abs(a.x-b.x)+Math.Abs(a.y-b.y),scale=Math.Abs(a.sx-b.sx)+Math.Abs(a.sy-b.sy);
     row.maxBoundaryPositionJump=Math.Max(row.maxBoundaryPositionJump,position);row.maxBoundaryScaleJump=Math.Max(row.maxBoundaryScaleJump,scale);
     check(position<.001f&&scale<.001f,"All gem bodies retain their exact boundary pose, including closed-column landing squash "+gem.id);
    }
    check(SameGoals(Goals(oldView,old,old.before,handoff,0),Goals(newView,next,next.before,handoff,handoff)),"Counter does not jump at early handoff "+k);
    // At the exact new match onset, all matched bodies remain at their settled
    // cells. At the existing .035 s removal marker they disappear; neither
    // their prior landing nor unrelated carry positions may be skipped.
    foreach(float age in new[]{0f,.02f,.036f,.08f}){
     var draws=Sample(newView,next,handoff+age,handoff,next.before);
     foreach(var removed in next.removed.Where(r=>r.cause=="match"&&r.piece.family=="gem")){
      bool visible=draws.Any(d=>d.pieceId==removed.piece.id);check(visible==(age<removed.time+.035f),"Local matched body follows existing clear marker "+removed.piece.id+"/"+age);
     }
    }
    float end=Math.Max(old.duration,handoff+next.duration)+TileFall.LandingSeconds+.001f;
    for(float t=handoff;t<=end;t+=1f/240){
     var oldActive=t<old.duration?old:null;var newActive=t<handoff+next.duration?next:null;
     var oldDraw=Sample(oldView,oldActive,t,0,old.after);var newDraw=Sample(newView,newActive,t,handoff,next.after);
     var a=Bodies(oldDraw,check,"Original "+k);var b=Bodies(newDraw,check,"Retimed "+k);row.samples++;
     foreach(int id in carry){
      bool was=a.TryGetValue(id,out var pa),now=b.TryGetValue(id,out var pb);check(was==now,"Carry clipping/visibility unchanged "+id+" at "+t);
      if(was&&now){check(Pose(pa,pb),"Actual renderer sample keeps carry position, stretch and squash "+id+" at "+t);
       foreach(var other in b.Values)if(other.pieceId!=id&&Math.Abs(other.x-pb.x)<.001f)check(Math.Abs(other.y-pb.y)>=.90f,"No newly interpenetrating carry column "+id+"/"+other.pieceId+" at "+t);
      }
     }
     foreach(var future in baseline[k+1].motion){
      var prior=old.motion.FirstOrDefault(m=>m.id==future.id);if(prior==null||t>=handoff+future.delay||t>=prior.delay+prior.seconds+prior.landing)continue;
      if(a.TryGetValue(future.id,out var pa)&&b.TryGetValue(future.id,out var pb))check(Pose(pa,pb),"Closed-column old landing remains continuous until new motion starts "+future.id+" at "+t);
     }
     // Old effects continue at their original absolute age. New effects may
     // coexist, but no prior tile debris sample may vanish due to the handoff.
     foreach(var effect in oldDraw.Where(d=>d.pieceId==0&&d.key.StartsWith("Tile",StringComparison.Ordinal)))check(newDraw.Any(d=>d.pieceId==0&&Pose(effect,d)&&Near(effect.age,d.age)),"Existing debris keeps absolute phase age "+k+" at "+t);
    }
    check(!decisions.Any(d=>d.accepted&&d.phaseIndex==k+1),"An active carry cannot start a second overlap "+k);
   }
   check(JsonUtility.ToJson(new Steps{steps=baseline})==frozen,"Renderer checks do not mutate baseline playback");return rows;
  }
  public static void AssertL4PartialHandoff(List<Row> rows,Action<bool,string> check){
   var row=rows.FirstOrDefault(r=>r.phaseIndex==1);check(row!=null,"Exact L4 red+moss fixture qualifies for the restricted handoff");if(row==null)return;
   check(Math.Abs(row.previousDuration-.71142137f)<.00002f,"L4 original right-column global contact is retained as baseline");
   check(Math.Abs(row.handoff-.51142137f)<.00002f,"L4 waits for all affected-column routes; no premature local handoff");
   check(Math.Abs(row.lastParticipatingContact-.26642137f)<.00002f,"L4 matching heart contact is measured independently");
   check(Math.Abs(row.secondsSaved-.20f)<.00002f,"L4 saves200ms rather than claiming full local-gap removal");
   check(Math.Abs(row.residualLocalWait-.245f)<.00002f,"L4 retains245ms scheduled contact-to-next-phase wait");
  }
  // L4 must be constructed from ui.boards.levels[3], with the first LegalSwaps
  // entry, exactly as CascadeTimingProbe does. Report qualification, actual
  // ready contact and residual wait; never assert near-reference timing merely
  // because some early handoff exists. The .035 stagger in a matched column
  // may force a later safe boundary. A rejected L4 is an explicit no-fix result.
  [Serializable] sealed class Steps {public List<BoardStep> steps;}
 }
}
#endif

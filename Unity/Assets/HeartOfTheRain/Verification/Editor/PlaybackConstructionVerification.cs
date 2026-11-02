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
using Motion=HeartOfTheRain.M46.Motion;
namespace HeartOfTheRain.Verification {
 public static class PlaybackConstructionVerification {
  [Serializable] public sealed class Row {public string name;public int iterations;public double legacyMedianMs,currentMedianMs;public List<double> legacyMs=new List<double>(),currentMs=new List<double>();}
  [Serializable] public sealed class Report {public string status,utc,baselineSourceSHA256;public int checks,modelCases,queueComparisons;public bool exactQueueParity=true,rawInputUnchanged=true,compiledSourceMatchesArchive,comparedNonserializedTracks=true,comparedContinuationSegments=true;public List<string> errors=new List<string>();public List<Row> timings=new List<Row>();public string scope="Native compiled exact74 playback construction under74 scheduling, compared with allocation-only current construction. Serialized queue fields plus recursive nonserialized tracks, continuation segments/contacts/poses and unchanged raw turns; alternating warmed CPU spans are descriptive, separate from current75 scheduler and Android input/frame timing.";}
  [Serializable] sealed class Queue {public List<BoardStep> steps;}
  static Report report;
  static void Check(bool value,string name){report.checks++;if(!value)throw new InvalidOperationException(name);}
  static string Json(List<BoardStep> q){
   var text=new StringBuilder();
   void Number(float value){text.Append(value.ToString("R",System.Globalization.CultureInfo.InvariantCulture)).Append(';');}
   void Step(BoardStep s,int depth){
    if(depth>32)throw new InvalidOperationException("Unexpected cyclic playback graph");
    text.Append(JsonUtility.ToJson(s));text.Append("tracks:").Append(s.playbackTracks==null?-1:s.playbackTracks.Count);
    if(s.playbackTracks!=null)foreach(var track in s.playbackTracks){Number(track.start);Number(track.leadIn);Step(track.step,depth+1);}
    foreach(var motion in s.motion){
     text.Append("continued:").Append(LocalCascadeContinuation.IsContinuation(motion));
     foreach(float at in new[]{-1f,0f,motion.delay,motion.delay+motion.seconds,s.duration+1}){
      float local;var segment=LocalCascadeContinuation.Segment(motion,at,out local);Number(local);text.Append(JsonUtility.ToJson(segment));
      float x,y;TileFall.Position(motion,at,out x,out y);Number(x);Number(y);text.Append(TileFall.Moving(motion,at));
     }
     text.Append("contacts:");foreach(float contact in LocalCascadeContinuation.LandingContacts(motion))Number(contact);
    }
   }
   foreach(var step in q)Step(step,0);return text.ToString();
  }
  static string Hash(string text){using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(text))).Replace("-","").ToLowerInvariant();}
  public static void Run(){
   report=new Report{utc=DateTime.UtcNow.ToString("o")};bool previous=LocalCascadeContinuation.VerificationUseCheckpoint74;
   try {
    string baseline=Path.GetFullPath("../.verification-cache/Gameplay75/BaselineSources/Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPlayback.cs");string source=File.ReadAllText(baseline);report.baselineSourceSHA256=Hash(source);
    string own=File.ReadAllText("Assets/HeartOfTheRain/Verification/Editor/PlaybackConstructionVerification.cs");string marker="// BEGIN COMPILED ARCHIVED74";string compiled=own.Substring(own.LastIndexOf(marker,StringComparison.Ordinal)+marker.Length).Trim();compiled=compiled.Substring(0,compiled.LastIndexOf("#endif",StringComparison.Ordinal)).Trim();
    string expected=source.Substring(source.IndexOf("namespace HeartOfTheRain.M46",StringComparison.Ordinal)).Replace("namespace HeartOfTheRain.M46","namespace HeartOfTheRain.Verification.Checkpoint74Playback").Replace("    public sealed class PlaybackTrack { public BoardStep step; public float start,leadIn; }","");report.compiledSourceMatchesArchive=compiled.Replace("\r\n","\n")==expected.Trim().Replace("\r\n","\n");Check(report.compiledSourceMatchesArchive,"Compiled control is exact archived74 text except namespace/import/shared record declaration");
    var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
    LocalCascadeContinuation.VerificationUseCheckpoint74=true;
    var benchmarks=new List<Tuple<string,TurnResult,LevelData>>();
    for(int level=0;level<50;level++)foreach(int kind in new[]{-1,4,5,7,11,16,21}){
     var model=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[level].text));TurnResult turn;
     if(kind<0){var swap=model.LegalSwaps().First();turn=model.Swap(swap[0].x,swap[0].y,swap[1].x,swap[1].y);}else{var p=model.Pieces.Values.First(v=>v.family=="gem");model.InjectReviewPower(p.x,p.y,kind);turn=model.Tap(p.x,p.y);}
     Check(turn.accepted,"Fixture accepted");string raw=JsonUtility.ToJson(turn);
     foreach(bool geometry in new[]{true,false})foreach(bool overlap in new[]{true,false}){
      var old=Checkpoint74Playback.BoardPlayback.Build(turn.steps,geometry?model.Level:null,overlap,true);var current=BoardPlayback.Build(turn.steps,geometry?model.Level:null,overlap,true);bool equal=Json(old)==Json(current);report.exactQueueParity&=equal;report.queueComparisons++;Check(equal,"Exact74 queue "+level+"/"+kind+"/"+geometry+"/"+overlap);
     }
     bool unchanged=raw==JsonUtility.ToJson(turn);report.rawInputUnchanged&=unchanged;Check(unchanged,"Raw turn remains unchanged");report.modelCases++;
     if(level==3&&kind<0||level==47&&kind==16||level==25&&kind==7)benchmarks.Add(Tuple.Create("L"+(level+1)+"/"+kind,turn,model.Level));
    }
    foreach(var fixture in benchmarks){
     var row=new Row{name=fixture.Item1,iterations=24};Action<bool> build=old=>{if(old)Checkpoint74Playback.BoardPlayback.Build(fixture.Item2.steps,fixture.Item3);else BoardPlayback.Build(fixture.Item2.steps,fixture.Item3);};
     for(int n=0;n<8;n++){build(true);build(false);}
     for(int n=0;n<row.iterations;n++){
      double Measure(bool old){long start=Stopwatch.GetTimestamp();for(int repeat=0;repeat<8;repeat++)build(old);return (Stopwatch.GetTimestamp()-start)*1000.0/Stopwatch.Frequency/8;}
      if(n%2==0){row.legacyMs.Add(Measure(true));row.currentMs.Add(Measure(false));}else{row.currentMs.Add(Measure(false));row.legacyMs.Add(Measure(true));}
     }
     row.legacyMedianMs=row.legacyMs.OrderBy(x=>x).ElementAt(row.iterations/2);row.currentMedianMs=row.currentMs.OrderBy(x=>x).ElementAt(row.iterations/2);report.timings.Add(row);
    }
    Check(report.modelCases==350&&report.queueComparisons==1400,"All350commands and1400queues checked");
   }catch(Exception e){report.errors.Add(e.ToString());}finally{LocalCascadeContinuation.VerificationUseCheckpoint74=previous;}
   report.status=report.errors.Count==0?"PASS_NATIVE_PLAYBACK_CONSTRUCTION75":"FAIL_NATIVE_PLAYBACK_CONSTRUCTION75";string folder=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY75_OUTPUT");if(string.IsNullOrEmpty(folder))folder=Path.GetFullPath("../Verification/Evidence/Gameplay75");folder=Path.Combine(folder,"Native");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"PlaybackConstruction.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.errors.Count==0?0:1);
  }
 }
}
// BEGIN COMPILED ARCHIVED74
namespace HeartOfTheRain.Verification.Checkpoint74Playback
{

    public static class TileFall
    {
        public const float LandingSeconds=.10f;
        public static float Distance(FallLeg m){float x=m.toX-m.fromX,y=m.toY-m.fromY;return (float)Math.Sqrt(x*x+y*y);}
        public static float Distance(Motion m){if(m.path!=null&&m.path.Count>0){float length=0;foreach(var leg in m.path)length+=Distance(leg);return length;}float x=m.toX-m.fromX,y=m.toY-m.fromY;return (float)Math.Sqrt(x*x+y*y);}
        public static void Position(Motion m,float age,out float x,out float y){
            float segmentAge;var segment=LocalCascadeContinuation.Segment(m,age,out segmentAge);
            if(!ReferenceEquals(segment,m)){Position(segment,segmentAge,out x,out y);return;}
            if(m.path!=null&&m.path.Count>0){x=m.fromX;y=m.fromY;foreach(var leg in m.path){if(age<leg.delay)return;float elapsed=Math.Max(0,Math.Min(leg.seconds,age-leg.delay));float span=Distance(leg),travel=Travel(Duration(leg.distance)+elapsed)-leg.distance;float f=span>0?Math.Max(0,Math.Min(1,travel/span)):1;x=leg.fromX+(leg.toX-leg.fromX)*f;y=leg.fromY+(leg.toY-leg.fromY)*f;if(age<leg.delay+leg.seconds)return;}return;}
            float u=Math.Max(0,Math.Min(1,(age-m.delay)/m.seconds)),e=Progress(Distance(m),u);x=m.fromX+(m.toX-m.fromX)*e;y=m.fromY+(m.toY-m.fromY)*e;
        }
        static float Travel(float t){float ramp=TerminalSpeed/Acceleration;return t<=ramp?.5f*Acceleration*t*t:.5f*Acceleration*ramp*ramp+TerminalSpeed*(t-ramp);}
        public static bool Moving(Motion m,float age){float segmentAge;var segment=LocalCascadeContinuation.Segment(m,age,out segmentAge);if(!ReferenceEquals(segment,m))return Moving(segment,segmentAge);if(m.path==null||m.path.Count==0)return age>=m.delay&&age<m.delay+m.seconds;foreach(var leg in m.path)if(age>=leg.delay&&age<leg.delay+leg.seconds)return true;return false;}
        const float Acceleration=100,TerminalSpeed=28;
        public static float Duration(float distance){distance=Math.Abs(distance);float ramp=TerminalSpeed/Acceleration,span=.5f*Acceleration*ramp*ramp;return distance<=span?(float)Math.Sqrt(2*distance/Acceleration):ramp+(distance-span)/TerminalSpeed;}
        public static float Progress(float distance,float fraction){distance=Math.Abs(distance);if(distance<.0001f||fraction>=1)return 1;if(fraction<=0)return 0;float t=fraction*Duration(distance),ramp=TerminalSpeed/Acceleration;float travelled=t<=ramp?.5f*Acceleration*t*t:.5f*Acceleration*ramp*ramp+TerminalSpeed*(t-ramp);return Math.Min(1,travelled/distance);}
    }
    // Presentation only: retain every model snapshot, target and damage operation.
    // Track-local time skips idle anticipation; cells release independently of VFX tails.
    public static class BoardPlayback
    {
        struct PowerClock {public float model,start,leadIn;}
        static long Key(int x,int y)=>((long)x<<32)|(uint)y;
        static float Local(float time,float leadIn)=>Math.Max(0,time-leadIn);
        static float LeadIn(BoardStep s,bool hit){
            if(s.powerPlan==null)return 0;
            switch(s.powerPlan.kind){case 4:case 5:case 21:return hit?.90f:.84f;case 7:return hit?1.28f:1.15f;case 11:case 16:return hit?.95f:.87f;default:return 0;}
        }
        // A late frame must not consume the whole input tween or newborn power
        // before intermediate poses reach the renderer. Other phases retain their clock.
        public static float VisibleAdvance(BoardStep step,float advance,float age=0){
            if(step==null)return advance;
            if(step.kind=="swap"||step.kind=="match"&&step.created.Count>0)return Math.Min(advance,step.duration/3f);
            // Ordinary 15/30/60 Hz frames use real elapsed time. The old
            // per-motion 28 ms cap stretched every fall at 30 Hz (and some
            // shorter route tails even at 60 Hz). Only an exceptional stall
            // needs pose protection; it must not become permanent slow motion.
            if(advance<=.10f)return advance;
            if(step.kind=="gravity"||step.kind=="powerFall")foreach(var m in step.motion){
                // Skip quiet anticipation normally, but sample the flight/settle
                // before a late frame can jump over the complete movement.
                float end=m.delay+m.seconds+m.landing;
                if(end-age>.0005f&&age+advance>m.delay){float next=Math.Min(end,Math.Max(age,m.delay)+Math.Min(1f/30,m.seconds/5));advance=Math.Min(advance,next-age);}
            }
            return advance;
        }
        public static float InputStableAt(BoardStep s){
            float ready=0;foreach(var m in s.motion)ready=Math.Max(ready,m.delay+m.seconds);foreach(var d in s.damage)ready=Math.Max(ready,d.time);foreach(var r in s.removed)ready=Math.Max(ready,r.time);
            if(s.playbackTracks!=null)foreach(var t in s.playbackTracks)if(t.step.powerPlan!=null)ready=Math.Max(ready,t.start+Local(t.step.powerPlan.primary,t.leadIn));
            return ready;
        }
        // Stitch only consecutive gravity snapshots. Delivery, matches and new
        // power contacts remain boundaries owned by the model.
        static void Fall(BoardStep output,List<BoardStep> falls,Dictionary<long,float> released,LevelData geometry,float firstStart=0){
            var first=falls[0];var last=falls[falls.Count-1];output.after=last.after;
            var active=geometry==null?new HashSet<long>(first.before.pieces.Concat(last.after.pieces).Select(p=>Key(p.x,p.y))):new HashSet<long>(geometry.activeCells.Select(p=>Key(p.x,p.y)));
            var blockers=new HashSet<long>(last.after.pieces.Where(p=>!p.Movable).Select(p=>Key(p.x,p.y)));
            var routes=new List<Motion>();
            foreach(var group in falls.SelectMany(s=>s.motion).GroupBy(m=>m.id)){
                var legs=group.ToList();var a=legs[0];var z=legs[legs.Count-1];
                int top=(int)a.toY,x=(int)a.toX;while(active.Contains(Key(x,top+1))&&!blockers.Contains(Key(x,top+1)))top++;
                var move=new Motion{id=a.id,fromX=a.fromX,fromY=a.fromY,toX=z.toX,toY=z.toY,spawned=a.spawned,clipSpawn=a.spawned,spawnTop=top,path=legs.Count>1?legs.Select(l=>new FallLeg{fromX=l.fromX,fromY=l.fromY,toX=l.toX,toY=l.toY}).ToList():null,landing=TileFall.LandingSeconds};
                move.seconds=TileFall.Duration(TileFall.Distance(move));
                routes.Add(move);
            }
            var byId=routes.ToDictionary(m=>m.id);var tails=new Dictionary<int,FallLeg>();var indices=new Dictionary<int,int>();
            var vacated=new Dictionary<long,float>();var previous=new Dictionary<long,FallLeg>();
            foreach(var raw in falls.SelectMany(s=>s.motion)){
                var move=byId[raw.id];int index;indices.TryGetValue(raw.id,out index);indices[raw.id]=index+1;
                var leg=move.path==null?new FallLeg{fromX=raw.fromX,fromY=raw.fromY,toX=raw.toX,toY=raw.toY}:move.path[index];
                FallLeg tail;bool continuing=tails.TryGetValue(raw.id,out tail);float earliest=continuing?tail.delay+tail.seconds:firstStart;
                float offset=continuing?tail.distance+TileFall.Distance(tail):0;
                var cells=RouteCells(raw).ToList();
                float ContactReady(){float ready=0;foreach(var cell in cells){float release;if(released.TryGetValue(cell.key,out release))ready=Math.Max(ready,release);}if(raw.fromX!=raw.toX){float release;if(released.TryGetValue(Key((int)raw.fromX,(int)raw.toY),out release))ready=Math.Max(ready,release);}return ready;}
                earliest=Math.Max(earliest,ContactReady());
                FallLeg ahead;
                // Existing neighbors also stagger; fresh portal feeds retain causal order.
                if(!continuing){int bottom=(int)raw.toY;while(active.Contains(Key((int)raw.fromX,bottom-1))&&!blockers.Contains(Key((int)raw.fromX,bottom-1)))bottom--;long section=Key((int)raw.fromX,bottom);if(previous.TryGetValue(section,out ahead))earliest=Math.Max(earliest,ahead.delay+.035f);previous[section]=leg;}
                float Start(float initial,float distance){float ready=initial;foreach(var cell in cells){float time;if(vacated.TryGetValue(cell.key,out time))ready=Math.Max(ready,time-(TileFall.Duration(distance+cell.distance)-TileFall.Duration(distance)));}return ready;}
                float start=Start(earliest,offset);
                // Only a tile whose route really needs to yield waits at a cell.
                // Other tiles and columns continue; there is no wave-wide landing barrier.
                if(continuing&&start>tail.delay+tail.seconds+.00001f){offset=0;start=Start(earliest,0);}
                leg.delay=start;leg.distance=offset;leg.seconds=TileFall.Duration(offset+TileFall.Distance(raw))-TileFall.Duration(offset);
                foreach(var cell in cells)if(cell.distance<TileFall.Distance(raw)-.001f){float ready=start+TileFall.Duration(offset+Math.Min(TileFall.Distance(raw),cell.distance+1))-TileFall.Duration(offset);float prior;vacated.TryGetValue(cell.key,out prior);vacated[cell.key]=Math.Max(prior,ready+.015f);}
                if(!continuing)move.delay=start;move.seconds=start+leg.seconds-move.delay;tails[raw.id]=leg;
            }
            // Landing squash continues in presentation history. A new match
            // can react at contact, without a board-wide decorative pause.
            foreach(var move in routes){output.motion.Add(move);output.duration=Math.Max(output.duration,move.delay+move.seconds);}
            output.duration=Math.Max(.08f,output.duration);
        }
        static IEnumerable<(long key,float distance)> RouteCells(Motion move){
            yield return (Key((int)move.fromX,(int)move.fromY),0);float distance=0;
            var legs=move.path!=null&&move.path.Count>0?move.path:new List<FallLeg>{new FallLeg{fromX=move.fromX,fromY=move.fromY,toX=move.toX,toY=move.toY}};
            foreach(var leg in legs){int count=Math.Max(1,(int)(leg.fromY-leg.toY));float length=TileFall.Distance(leg);for(int i=1;i<=count;i++){float f=(float)i/count;yield return (Key((int)Math.Round(leg.fromX+(leg.toX-leg.fromX)*f),(int)Math.Round(leg.fromY+(leg.toY-leg.fromY)*f)),distance+length*f);}distance+=length;}
        }
        static List<BoardStep> GravityRun(List<BoardStep> steps,ref int index){var run=new List<BoardStep>{steps[index]};while(index+1<steps.Count&&steps[index+1].kind=="gravity")run.Add(steps[++index]);return run;}
        public static List<BoardStep> Build(IEnumerable<BoardStep> source,LevelData geometry=null,bool localCascades=true,bool localContinuations=true)
        {
            var steps=source.ToList();var output=new List<BoardStep>();
            for(int i=0;i<steps.Count;i++){
                bool tool=steps[i].booster!=null&&steps[i].booster.kind!=BoosterKind.Atlas;
                // A basic obstacle can still occupy its cell after the short
                // match beat. Let unrelated columns refill while only paths
                // through that obstacle wait for its authored clear marker.
                // Hit-body animation continues independently through history.
                if(steps[i].kind=="match"&&steps[i].duration<=.28f&&i+1<steps.Count&&steps[i+1].kind=="gravity"){
                    var s=steps[i];var matched=new BoardStep{kind="powerFall",label="Match and refill",duration=.09f,before=s.before,after=s.after,removed=s.removed,damage=s.damage,created=s.created,collections=s.collections,playbackTracks=new List<PlaybackTrack>{new PlaybackTrack{step=s,start=0}}};
                    var matchReleased=new Dictionary<long,float>();
                    void ReserveMatch(int x,int y,float time){long key=Key(x,y);float prior;matchReleased.TryGetValue(key,out prior);matchReleased[key]=Math.Max(prior,time);}
                    foreach(var r in s.removed){float release=r.time+(r.cause=="obstacle"?.24f:.04f);ReserveMatch(r.piece.x,r.piece.y,release);matched.duration=Math.Max(matched.duration,release);}
                    foreach(var d in s.damage)ReserveMatch(d.x,d.y,d.time+.12f);
                    i++;Fall(matched,GravityRun(steps,ref i),matchReleased,geometry,.09f);output.Add(matched);continue;
                }
                if(steps[i].kind!="power"&&!tool){
                    var s=steps[i];var copy=new BoardStep{kind=s.kind,label=s.label,duration=s.kind=="swap"?.12f:s.kind=="gravity"?0:s.kind=="match"?(s.duration>.28f?s.duration:.16f):s.duration,before=s.before,after=s.after,powerPlan=s.powerPlan,booster=s.booster,removed=s.removed,damage=s.damage,created=s.created,collections=s.collections};
                    if(s.kind=="gravity")Fall(copy,GravityRun(steps,ref i),new Dictionary<long,float>(),geometry);else copy.motion=s.motion;
                    if(s.kind=="match")foreach(var r in s.removed)if(r.cause=="obstacle")copy.duration=Math.Max(copy.duration,r.time+.24f);
                    output.Add(copy);continue;
                }
                var first=steps[i];var merged=new BoardStep{kind="powerFall",label="Power chain and refill",before=first.before,after=first.after,booster=first.booster,playbackTracks=new List<PlaybackTrack>()};
                var released=new Dictionary<long,float>();var lastDamage=new Dictionary<int,float>();var parents=new Dictionary<int,PowerClock>();float end=0;
                void Reserve(int x,int y,float time){long key=Key(x,y);float old;released.TryGetValue(key,out old);released[key]=Math.Max(old,time);end=Math.Max(end,time);}
                void ReserveOwner(int id,int x,int y,float time){Reserve(x,y,time);foreach(var member in first.before.pieces)if(member.ownerId==id)Reserve(member.x,member.y,time);}
                do{
                    var s=steps[i];PowerClock parent;bool child=s.kind=="power"&&(s.triggerOriginId!=0||s.triggerTime>0);
                    float lead=LeadIn(s,child),at=parents.TryGetValue(s.triggerOriginId,out parent)?parent.start+Local(s.triggerTime-parent.model,parent.leadIn):s.triggerTime;
                    // Shared-obstacle damage and all descendant triggers remain causal.
                    foreach(var d in s.damage){float previous;if(lastDamage.TryGetValue(d.id,out previous))at=Math.Max(at,previous-Local(d.time,lead)+.001f);}
                    foreach(var r in s.removed)if(r.cause=="source")parents[r.piece.id]=new PowerClock{model=s.triggerTime,start=at,leadIn=lead};
                    merged.playbackTracks.Add(new PlaybackTrack{step=s,start=at,leadIn=lead});merged.after=s.after;
                    foreach(var r in s.removed){var copy=new Removed{piece=r.piece,time=at+Local(r.time,lead),cause=r.cause};merged.removed.Add(copy);float clearance=r.cause!="obstacle"?.04f:r.piece.family=="cabinet"?.8f:.24f;ReserveOwner(r.piece.id,r.piece.x,r.piece.y,copy.time+clearance);}
                    foreach(var d in s.damage){float time=at+Local(d.time,lead);merged.damage.Add(new Damage{x=d.x,y=d.y,id=d.id,family=d.family,beforeHP=d.beforeHP,afterHP=d.afterHP,time=time,activation=d.activation});lastDamage[d.id]=time;ReserveOwner(d.id,d.x,d.y,time+(d.family=="crystal"?.24f:.12f));}
                    foreach(var c in s.collections){var copy=new GoalCollection{x=c.x,y=c.y,family=c.family,amount=c.amount,launch=at+Local(c.launch,lead),arrival=at+Local(c.arrival,lead),offsetX=c.offsetX,offsetY=c.offsetY};merged.collections.Add(copy);}
                    if(s.powerPlan!=null){var plan=s.powerPlan;foreach(var p in plan.powers??new ReviewPower[0])Reserve(p.x,p.y,at+Local(p.end,lead)+.025f);
                        // Orbs/seeker origins have authored bodies but no ReviewPower carrier.
                        if(plan.kind==7)Reserve(plan.originX,plan.originY,at+Local(plan.primary,lead)+8f/60);
                        if(plan.kind==11||plan.kind==16)Reserve(plan.originX,plan.originY,at+Local(32f/30,lead)+.12f);
                        end=Math.Max(end,at+Local(plan.primary,lead)+.04f);
                    }else if(s.booster!=null)foreach(var c in s.booster.contacts)Reserve(c.x,c.y,at+c.time+.04f);
                    i++;
                }while(i<steps.Count&&steps[i].kind=="power");
                merged.duration=Math.Max(.08f,end);
                if(i<steps.Count&&steps[i].kind=="gravity"){Fall(merged,GravityRun(steps,ref i),released,geometry);}else i--;
                output.Add(merged);
            }
            // Finish final-goal flights before the win flow takes the board
            // away. Playing turns/cascades never wait for those HUD effects.
            if(output.Count>0&&output[output.Count-1].kind=="settled"&&output[output.Count-1].after.status=="Won"){
                float start=0,arrival=0;foreach(var s in output){foreach(var c in s.collections)arrival=Math.Max(arrival,start+c.arrival);if(s==output[output.Count-1])s.duration=Math.Max(s.duration,arrival-start);start+=s.duration;}
            }
            return localCascades?(localContinuations?LocalCascadeContinuation.Apply(output):LocalCascadePlayback.Apply(output)):output;
        }
    }
}

#endif

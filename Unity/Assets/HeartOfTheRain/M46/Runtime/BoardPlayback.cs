using System;
using System.Collections.Generic;
using System.Linq;
namespace HeartOfTheRain.M46
{
    public sealed class PlaybackTrack { public BoardStep step; public float start,leadIn; }
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
        static void ThrowIfCancelled(Func<bool> cancelled){if(cancelled!=null&&cancelled())throw new OperationCanceledException("Playback preparation cancelled");}
        static void Fall(BoardStep output,List<BoardStep> falls,Dictionary<long,float> released,LevelData geometry,ref HashSet<long> authoredActive,float firstStart=0,Func<bool> cancelled=null){
            var first=falls[0];var last=falls[falls.Count-1];output.after=last.after;
            if(geometry!=null&&authoredActive==null)authoredActive=new HashSet<long>(geometry.activeCells.Select(p=>Key(p.x,p.y)));
            var active=geometry==null?new HashSet<long>(first.before.pieces.Concat(last.after.pieces).Select(p=>Key(p.x,p.y))):authoredActive;
            var blockers=new HashSet<long>(last.after.pieces.Where(p=>!p.Movable).Select(p=>Key(p.x,p.y)));
            var routes=new List<Motion>();var byId=new Dictionary<int,Motion>();
            // Preserve first-seen route/leg order without a GroupBy, a second
            // per-owner leg list and another route dictionary traversal.
            foreach(var fall in falls)foreach(var raw in fall.motion){
                ThrowIfCancelled(cancelled);
                Motion move;
                if(!byId.TryGetValue(raw.id,out move)){
                    int top=(int)raw.toY,x=(int)raw.toX;while(active.Contains(Key(x,top+1))&&!blockers.Contains(Key(x,top+1)))top++;
                    move=new Motion{id=raw.id,fromX=raw.fromX,fromY=raw.fromY,toX=raw.toX,toY=raw.toY,spawned=raw.spawned,clipSpawn=raw.spawned,spawnTop=top,landing=TileFall.LandingSeconds};
                    byId.Add(raw.id,move);routes.Add(move);
                }else{
                    if(move.path==null)move.path=new List<FallLeg>{new FallLeg{fromX=move.fromX,fromY=move.fromY,toX=move.toX,toY=move.toY}};
                    move.path.Add(new FallLeg{fromX=raw.fromX,fromY=raw.fromY,toX=raw.toX,toY=raw.toY});move.toX=raw.toX;move.toY=raw.toY;
                }
            }
            var tails=new Dictionary<int,FallLeg>();var indices=new Dictionary<int,int>();
            var vacated=new Dictionary<long,float>();var previous=new Dictionary<long,FallLeg>();
            foreach(var fall in falls)foreach(var raw in fall.motion){
                ThrowIfCancelled(cancelled);
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
                float Start(float initial,float distance){float ready=initial,originTime=TileFall.Duration(distance);foreach(var cell in cells){float time;if(vacated.TryGetValue(cell.key,out time))ready=Math.Max(ready,time-(TileFall.Duration(distance+cell.distance)-originTime));}return ready;}
                float start=Start(earliest,offset);
                // Only a tile whose route really needs to yield waits at a cell.
                // Other tiles and columns continue; there is no wave-wide landing barrier.
                if(continuing&&start>tail.delay+tail.seconds+.00001f){offset=0;start=Start(earliest,0);}
                float length=TileFall.Distance(raw),originTime=TileFall.Duration(offset);
                leg.delay=start;leg.distance=offset;leg.seconds=TileFall.Duration(offset+length)-originTime;
                foreach(var cell in cells)if(cell.distance<length-.001f){float ready=start+TileFall.Duration(offset+Math.Min(length,cell.distance+1))-originTime;float prior;vacated.TryGetValue(cell.key,out prior);vacated[cell.key]=Math.Max(prior,ready+.015f);}
                if(!continuing)move.delay=start;move.seconds=start+leg.seconds-move.delay;tails[raw.id]=leg;
            }
            // Landing squash continues in presentation history. A new match
            // can react at contact, without a board-wide decorative pause.
            foreach(var move in routes){output.motion.Add(move);output.duration=Math.Max(output.duration,move.delay+move.seconds);}
            output.duration=Math.Max(.08f,output.duration);
        }
        static IEnumerable<(long key,float distance)> RouteCells(Motion move){
            yield return (Key((int)move.fromX,(int)move.fromY),0);float distance=0;
            if(move.path==null||move.path.Count==0){
                int count=Math.Max(1,(int)(move.fromY-move.toY));float length=TileFall.Distance(move);
                for(int i=1;i<=count;i++){float f=(float)i/count;yield return (Key((int)Math.Round(move.fromX+(move.toX-move.fromX)*f),(int)Math.Round(move.fromY+(move.toY-move.fromY)*f)),distance+length*f);}yield break;
            }
            foreach(var leg in move.path){int count=Math.Max(1,(int)(leg.fromY-leg.toY));float length=TileFall.Distance(leg);for(int i=1;i<=count;i++){float f=(float)i/count;yield return (Key((int)Math.Round(leg.fromX+(leg.toX-leg.fromX)*f),(int)Math.Round(leg.fromY+(leg.toY-leg.fromY)*f)),distance+length*f);}distance+=length;}
        }
        static List<BoardStep> GravityRun(List<BoardStep> steps,ref int index){var run=new List<BoardStep>{steps[index]};while(index+1<steps.Count&&steps[index+1].kind=="gravity")run.Add(steps[++index]);return run;}
        public static List<BoardStep> Build(IEnumerable<BoardStep> source,LevelData geometry=null,bool localCascades=true,bool localContinuations=true)
        {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            return BuildCore(source,geometry,localCascades,localContinuations,LocalCascadeContinuation.VerificationUseCheckpoint74,null);
#else
            return BuildCore(source,geometry,localCascades,localContinuations,false,null);
#endif
        }
        // Pure managed compilation. Callers capture the development policy on
        // their own thread and own immutable raw DTOs/geometry for this call.
        public static List<BoardStep> BuildDetached(IEnumerable<BoardStep> source,LevelData geometry,bool checkpoint74,bool localCascades=true,bool localContinuations=true,Func<bool> cancelled=null)
            =>BuildCore(source,geometry,localCascades,localContinuations,checkpoint74,cancelled);
        static List<BoardStep> BuildCore(IEnumerable<BoardStep> source,LevelData geometry,bool localCascades,bool localContinuations,bool checkpoint74,Func<bool> cancelled)
        {
            ThrowIfCancelled(cancelled);
            var steps=source.ToList();var output=new List<BoardStep>();HashSet<long> authoredActive=null;
            for(int i=0;i<steps.Count;i++){
                ThrowIfCancelled(cancelled);
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
                    i++;Fall(matched,GravityRun(steps,ref i),matchReleased,geometry,ref authoredActive,.09f,cancelled);output.Add(matched);continue;
                }
                if(steps[i].kind!="power"&&!tool){
                    var s=steps[i];var copy=new BoardStep{kind=s.kind,label=s.label,duration=s.kind=="swap"?.12f:s.kind=="gravity"?0:s.kind=="match"?(s.duration>.28f?s.duration:.16f):s.duration,before=s.before,after=s.after,powerPlan=s.powerPlan,booster=s.booster,removed=s.removed,damage=s.damage,created=s.created,collections=s.collections};
                    if(s.kind=="gravity")Fall(copy,GravityRun(steps,ref i),new Dictionary<long,float>(),geometry,ref authoredActive,0,cancelled);else copy.motion=s.motion;
                    if(s.kind=="match")foreach(var r in s.removed)if(r.cause=="obstacle")copy.duration=Math.Max(copy.duration,r.time+.24f);
                    output.Add(copy);continue;
                }
                var first=steps[i];var merged=new BoardStep{kind="powerFall",label="Power chain and refill",before=first.before,after=first.after,booster=first.booster,playbackTracks=new List<PlaybackTrack>()};
                var released=new Dictionary<long,float>();var lastDamage=new Dictionary<int,float>();var parents=new Dictionary<int,PowerClock>();float end=0;
                void Reserve(int x,int y,float time){long key=Key(x,y);float old;released.TryGetValue(key,out old);released[key]=Math.Max(old,time);end=Math.Max(end,time);}
                void ReserveOwner(int id,int x,int y,float time){Reserve(x,y,time);foreach(var member in first.before.pieces)if(member.ownerId==id)Reserve(member.x,member.y,time);}
                do{
                    ThrowIfCancelled(cancelled);
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
                if(i<steps.Count&&steps[i].kind=="gravity"){Fall(merged,GravityRun(steps,ref i),released,geometry,ref authoredActive,0,cancelled);}else i--;
                output.Add(merged);
            }
            // Finish final-goal flights before the win flow takes the board
            // away. Playing turns/cascades never wait for those HUD effects.
            if(output.Count>0&&output[output.Count-1].kind=="settled"&&output[output.Count-1].after.status=="Won"){
                float start=0,arrival=0;foreach(var s in output){foreach(var c in s.collections)arrival=Math.Max(arrival,start+c.arrival);if(s==output[output.Count-1])s.duration=Math.Max(s.duration,arrival-start);start+=s.duration;}
            }
            ThrowIfCancelled(cancelled);
            var compiled=localCascades?(localContinuations?(checkpoint74?LocalCascadeContinuation.ApplyCheckpoint74(output):LocalCascadeContinuation.ApplyCurrent(output)):LocalCascadePlayback.Apply(output)):output;
            ThrowIfCancelled(cancelled);return compiled;
        }
    }
}

#if UNITY_EDITOR || DEVELOPMENT_BUILD
// Exact checkpoint75 construction controls. Never submit foreign motions to GameplayScreen.
using System;
using System.Collections.Generic;
using System.Linq;
using HeartOfTheRain.M46;

// BEGIN EXACT75 BoardPlayback.cs
namespace HeartOfTheRain.Verification.Checkpoint75Control
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
        static void Fall(BoardStep output,List<BoardStep> falls,Dictionary<long,float> released,LevelData geometry,ref HashSet<long> authoredActive,float firstStart=0){
            var first=falls[0];var last=falls[falls.Count-1];output.after=last.after;
            if(geometry!=null&&authoredActive==null)authoredActive=new HashSet<long>(geometry.activeCells.Select(p=>Key(p.x,p.y)));
            var active=geometry==null?new HashSet<long>(first.before.pieces.Concat(last.after.pieces).Select(p=>Key(p.x,p.y))):authoredActive;
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
            if(move.path==null||move.path.Count==0){
                int count=Math.Max(1,(int)(move.fromY-move.toY));float length=TileFall.Distance(move);
                for(int i=1;i<=count;i++){float f=(float)i/count;yield return (Key((int)Math.Round(move.fromX+(move.toX-move.fromX)*f),(int)Math.Round(move.fromY+(move.toY-move.fromY)*f)),distance+length*f);}yield break;
            }
            foreach(var leg in move.path){int count=Math.Max(1,(int)(leg.fromY-leg.toY));float length=TileFall.Distance(leg);for(int i=1;i<=count;i++){float f=(float)i/count;yield return (Key((int)Math.Round(leg.fromX+(leg.toX-leg.fromX)*f),(int)Math.Round(leg.fromY+(leg.toY-leg.fromY)*f)),distance+length*f);}distance+=length;}
        }
        static List<BoardStep> GravityRun(List<BoardStep> steps,ref int index){var run=new List<BoardStep>{steps[index]};while(index+1<steps.Count&&steps[index+1].kind=="gravity")run.Add(steps[++index]);return run;}
        public static List<BoardStep> Build(IEnumerable<BoardStep> source,LevelData geometry=null,bool localCascades=true,bool localContinuations=true)
        {
            var steps=source.ToList();var output=new List<BoardStep>();HashSet<long> authoredActive=null;
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
                    i++;Fall(matched,GravityRun(steps,ref i),matchReleased,geometry,ref authoredActive,.09f);output.Add(matched);continue;
                }
                if(steps[i].kind!="power"&&!tool){
                    var s=steps[i];var copy=new BoardStep{kind=s.kind,label=s.label,duration=s.kind=="swap"?.12f:s.kind=="gravity"?0:s.kind=="match"?(s.duration>.28f?s.duration:.16f):s.duration,before=s.before,after=s.after,powerPlan=s.powerPlan,booster=s.booster,removed=s.removed,damage=s.damage,created=s.created,collections=s.collections};
                    if(s.kind=="gravity")Fall(copy,GravityRun(steps,ref i),new Dictionary<long,float>(),geometry,ref authoredActive);else copy.motion=s.motion;
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
                if(i<steps.Count&&steps[i].kind=="gravity"){Fall(merged,GravityRun(steps,ref i),released,geometry,ref authoredActive);}else i--;
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
// END EXACT75 BoardPlayback.cs

// BEGIN EXACT75 LocalCascadeContinuation.cs
namespace HeartOfTheRain.Verification.Checkpoint75Control {
    // Playback-only ownership. No added model fields or serialized raw-turn data.
    internal sealed class ContinuedMotion : Motion {
        internal Motion previous,following;
        internal float handoff;
    }

    [Serializable] public sealed class LocalContinuationColumn {
        public int column;
        public float padding;
    }
    [Serializable] public sealed class LocalContinuationDecision {
        public int phaseIndex;
        public float handoff,previousDuration,nextDuration,nextOriginalDuration,matchReady,ownershipClosedAt;
        public int[] carryIds=new int[0],continuedIds=new int[0],columns=new int[0];
        public List<LocalContinuationColumn> columnPads=new List<LocalContinuationColumn>();
        public bool accepted,terminalIdleLanding;
        public string reason;
    }

    // One restricted match/refill handoff per turn. A body keeps its original
    // flight and landing before beginning its next, column-retimed flight.
    // Terminal expansion is allowed only before unchanged Playing settlement;
    // unsafe pairs retain the independently verified checkpoint74 scheduler.
    public static class LocalCascadeContinuation {
        const float Epsilon=.00001f,MaximumColumnPadding=.12f;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        // Isolated, opt-in verification only. Ordinary and release playback
        // always use the guarded current path.
        public static bool VerificationUseCheckpoint74;
#endif

        public static bool IsContinuation(Motion motion)=>motion is ContinuedMotion;

        public static Motion Segment(Motion motion,float age,out float segmentAge) {
            var continued=motion as ContinuedMotion;
            if(continued==null){segmentAge=age;return motion;}
            if(age<continued.following.delay){segmentAge=age+continued.handoff;return continued.previous;}
            segmentAge=age;return continued.following;
        }

        // Old contacts at/before the handoff have already been played by the
        // outgoing feedback owner. Only a strictly future contact is transferred.
        public static IEnumerable<float> LandingContacts(Motion motion) {
            var continued=motion as ContinuedMotion;
            if(continued!=null) {
                float old=Contact(continued.previous)-continued.handoff;
                if(old>Epsilon)yield return old;
                yield return Contact(continued.following);
            } else if(Contact(motion)>=0)yield return Contact(motion);
        }

        public static List<BoardStep> Apply(IEnumerable<BoardStep> source,List<LocalContinuationDecision> decisions=null) {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(VerificationUseCheckpoint74)return ApplyCheckpoint74(source,decisions);
#endif
            var input=source.ToList();
            if(input.Any(s=>s.motion.Any(IsContinuation))||input.Any(s=>s.motion.Any(m=>Contact(m)>s.duration+Epsilon))) {
                decisions?.Add(new LocalContinuationDecision{reason="already_scheduled_handoff"});return input;
            }
            var result=new List<BoardStep>(input);var findings=new List<LocalContinuationDecision>();
            float start=0;
            for(int i=0;i+1<input.Count;i++) {
                LocalContinuationDecision d;bool eligible=TryDescribe(input[i],input[i+1],out d);
                if(!eligible&&(d.reason=="following_landing_exceeds_ownership_window"||d.reason=="carry_landing_exceeds_ownership_window")&&i+2==input.Count-1)
                    eligible=TryDescribeTerminal(input[i],input[i+1],input[i+2],out d);
                d.phaseIndex=i;
                findings.Add(d);
                if(!eligible){start+=result[i].duration;continue;}
                var old=input[i];var next=input[i+1];var oldRoutes=old.motion.ToDictionary(m=>m.id);
                var continued=new HashSet<int>(d.continuedIds);var carries=new HashSet<int>(d.carryIds);
                var pads=d.columnPads.ToDictionary(p=>p.column,p=>p.padding);
                var a=Copy(old);a.duration=d.handoff;var b=Copy(next);b.duration=d.nextDuration;b.motion=new List<Motion>();
                foreach(var following in next.motion) {
                    float pad;pads.TryGetValue((int)following.fromX,out pad);var retimed=Shift(following,pad);
                    b.motion.Add(continued.Contains(following.id)?Continue(oldRoutes[following.id],retimed,d.handoff):retimed);
                }
                foreach(var motion in old.motion)if(carries.Contains(motion.id))b.motion.Add(Shift(motion,-d.handoff));
                result[i]=a;result[i+1]=b;
                d.ownershipClosedAt=start+a.duration+b.motion.Max(m=>Contact(m)+m.landing);
                if(d.terminalIdleLanding) {
                    var legacyDecisions=new List<LocalContinuationDecision>();var legacy=ApplyCheckpoint74(input,legacyDecisions);
                    if(result.Sum(s=>s.duration)>legacy.Sum(s=>s.duration)+Epsilon) {
                        decisions?.Add(new LocalContinuationDecision{reason="expansion_would_outgrow_checkpoint74"});decisions?.AddRange(legacyDecisions);return legacy;
                    }
                }
                for(int j=i+1;j+1<input.Count;j++)findings.Add(new LocalContinuationDecision{phaseIndex=j,reason="second_overlap_disabled"});
                decisions?.AddRange(findings);return result;
            }
            decisions?.AddRange(findings);return LocalCascadePlayback.Apply(input);
        }

        // Frozen checkpoint74 control: one handoff, with its original strict
        // successor landing-window guard and exact checkpoint73 fallback.
        public static List<BoardStep> ApplyCheckpoint74(IEnumerable<BoardStep> source,List<LocalContinuationDecision> decisions=null) {
            var input=source.ToList();
            if(input.Any(s=>s.motion.Any(IsContinuation))||input.Any(s=>s.motion.Any(m=>Contact(m)>s.duration+Epsilon))) {
                decisions?.Add(new LocalContinuationDecision{reason="already_scheduled_handoff"});return input;
            }
            for(int i=0;i+1<input.Count;i++) {
                LocalContinuationDecision decision;
                bool eligible=TryDescribe(input[i],input[i+1],out decision);decision.phaseIndex=i;decisions?.Add(decision);
                if(!eligible)continue;
                var old=input[i];var next=input[i+1];var oldRoutes=old.motion.ToDictionary(m=>m.id);
                var continuedIds=new HashSet<int>(decision.continuedIds);var carries=new HashSet<int>(decision.carryIds);
                var pads=decision.columnPads.ToDictionary(p=>p.column,p=>p.padding);
                var a=Copy(old);a.duration=decision.handoff;
                var b=Copy(next);b.motion=new List<Motion>();
                foreach(var following in next.motion) {
                    float pad;pads.TryGetValue((int)following.fromX,out pad);
                    var retimed=Shift(following,pad);
                    b.motion.Add(continuedIds.Contains(following.id)?Continue(oldRoutes[following.id],retimed,decision.handoff):retimed);
                }
                foreach(var motion in old.motion)if(carries.Contains(motion.id))b.motion.Add(Shift(motion,-decision.handoff));
                var result=new List<BoardStep>(input);result[i]=a;result[i+1]=b;
                // Never open another ownership boundary while these bodies live.
                for(int j=i+1;j+1<input.Count;j++)decisions?.Add(new LocalContinuationDecision{phaseIndex=j,reason="second_overlap_disabled"});
                return result;
            }
            return LocalCascadePlayback.Apply(input);
        }

        public static bool TryDescribe(BoardStep previous,BoardStep next,out LocalContinuationDecision decision) {
            return Describe(previous,next,false,out decision);
        }

        public static bool TryDescribeTerminal(BoardStep previous,BoardStep next,BoardStep settled,out LocalContinuationDecision decision) {
            if(!TerminalIdle(next,settled)) {
                decision=new LocalContinuationDecision{previousDuration=previous?.duration??0,nextDuration=next?.duration??0,nextOriginalDuration=next?.duration??0,reason="terminal_successor_not_unchanged_playing_idle"};return false;
            }
            return Describe(previous,next,true,out decision);
        }

        static bool Describe(BoardStep previous,BoardStep next,bool terminalIdle,out LocalContinuationDecision decision) {
            var d=new LocalContinuationDecision{previousDuration=previous?.duration??0,nextDuration=next?.duration??0,nextOriginalDuration=next?.duration??0};decision=d;
            bool Reject(string why){d.reason=why;return false;}
            if(previous==null||next==null||!Finite(previous.duration)||!Finite(next.duration))return Reject("invalid_phase");
            if(!Simple(previous,true)||!Simple(next,false))return Reject("not_plain_match_refill");
            if(previous.motion.Count==0||next.motion.Count==0)return Reject("no_refill_routes");
            if(!SameSnapshot(previous.after,next.before))return Reject("snapshot_boundary_mismatch");
            if(new[]{previous.before,previous.after,next.before,next.after}.Any(s=>s.pieces.Any(p=>p.family=="power"||p.family=="pail"||p.family=="crystal"||p.family=="cabinet"||p.family=="pod")))return Reject("power_delivery_or_advanced_body");
            if(previous.motion.Concat(next.motion).Any(m=>!Valid(m)))return Reject("invalid_or_previously_shifted_route");
            if(previous.motion.GroupBy(m=>m.id).Any(g=>g.Count()!=1)||next.motion.GroupBy(m=>m.id).Any(g=>g.Count()!=1))return Reject("duplicate_route_owner");
            if(previous.motion.Any(m=>!Vertical(m)))return Reject("old_route_not_single_vertical_fall");
            var routes=previous.motion.ToDictionary(m=>m.id);var nextRoutes=next.motion.ToDictionary(m=>m.id);
            var oldBefore=previous.before.pieces.ToDictionary(p=>p.id);var before=next.before.pieces.ToDictionary(p=>p.id);var after=next.after.pieces.ToDictionary(p=>p.id);
            var oldColumns=new HashSet<int>(previous.motion.Select(m=>(int)m.toX));
            foreach(var m in previous.motion) {
                Piece p;if(!before.TryGetValue(m.id,out p)||p.ownerId!=0||(p.family!="gem"&&p.family!="crate")||p.x!=m.toX||p.y!=m.toY)return Reject("old_route_body_or_destination_mismatch");
                if(!m.spawned&&(!oldBefore.TryGetValue(m.id,out p)||p.x!=m.fromX||p.y!=m.fromY))return Reject("old_route_source_mismatch");
            }
            foreach(var m in next.motion) {
                Piece body;if(!before.TryGetValue(m.id,out body)&&!after.TryGetValue(m.id,out body))return Reject("following_route_has_no_body");
                if(body.family!="gem"||body.ownerId!=0||!after.ContainsKey(m.id)||after[m.id].x!=m.toX||after[m.id].y!=m.toY)return Reject("following_route_not_plain_gem");
                if(!m.spawned&&(!before.ContainsKey(m.id)||before[m.id].x!=m.fromX||before[m.id].y!=m.fromY))return Reject("following_route_source_mismatch");
                if(!Vertical(m)&&Columns(m).Any(oldColumns.Contains))return Reject("following_side_feed_touches_old_motion_column");
            }
            var matches=next.removed.Where(r=>r.cause=="match"&&r.piece.family=="gem").ToArray();
            if(matches.Length<3)return Reject("no_plain_match");
            foreach(var removed in matches){Motion old;if(routes.TryGetValue(removed.piece.id,out old))d.matchReady=Math.Max(d.matchReady,Contact(old));}
            float handoff=Math.Max(.08f,d.matchReady);
            foreach(var r in previous.removed)handoff=Math.Max(handoff,r.time+(r.cause=="obstacle"?.24f:.035f));
            foreach(var hit in previous.damage)handoff=Math.Max(handoff,hit.time+.12f);
            d.handoff=handoff;
            if(previous.duration-handoff<.01f)return Reject("no_safe_overlap_saving");
            if(next.removed.Where(r=>r.cause!="match").Any(r=>oldColumns.Contains(r.piece.x))||next.damage.Any(h=>oldColumns.Contains(h.x)))return Reject("following_obstacle_changes_old_motion_column");
            var changed=new HashSet<int>(next.removed.Select(r=>r.piece.id).Concat(next.damage.Select(h=>h.id)).Concat(next.created.Select(p=>p.id)));
            foreach(var r in next.removed){Motion old;if(routes.TryGetValue(r.piece.id,out old)&&Contact(old)>handoff+Epsilon)return Reject("matched_body_still_in_flight");}
            // Every old column must already be ordered bottom-to-top. With that
            // condition, a following body cannot overtake an unfinished lower one.
            foreach(var group in previous.motion.GroupBy(m=>(int)m.toX)) {
                var ordered=group.OrderBy(m=>m.toY).ToArray();
                for(int j=1;j<ordered.Length;j++)if(ordered[j].toY<=ordered[j-1].toY||Contact(ordered[j])+ordered[j].landing+Epsilon<Contact(ordered[j-1])+ordered[j-1].landing)return Reject("old_column_ready_order_not_monotone");
            }
            var affected=new HashSet<int>();
            foreach(var m in next.motion)if(Vertical(m)&&oldColumns.Contains((int)m.toX))affected.Add((int)m.toX);
            if(affected.Count==0)return Reject("no_shared_vertical_column");
            d.columns=affected.OrderBy(x=>x).ToArray();
            var pads=new Dictionary<int,float>();
            foreach(int x in d.columns) {
                float pad=0;
                foreach(var m in next.motion.Where(m=>m.fromX==x)) {
                    Motion old;if(routes.TryGetValue(m.id,out old)) {
                        if(!Vertical(m)||old.toX!=m.fromX||old.toY!=m.fromY||changed.Contains(m.id)||previous.damage.Any(h=>h.id==m.id)||!SameIdentity(before[m.id],after[m.id]))return Reject("shared_body_or_leg_changes");
                        pad=Math.Max(pad,Contact(old)+old.landing-handoff-m.delay);
                    } else if(m.spawned)pad=Math.Max(pad,previous.motion.Where(a=>a.toX==x).Max(a=>Contact(a)+a.landing)-handoff-m.delay);
                    else return Reject("unowned_following_body_in_shared_column");
                }
                if(pad>MaximumColumnPadding+Epsilon)return Reject("column_padding_exceeds_bounded_window");
                pads[x]=Math.Max(0,pad);d.columnPads.Add(new LocalContinuationColumn{column=x,padding=Math.Max(0,pad)});
            }
            if(terminalIdle) {
                // Flights still finish before settlement/input. Only their
                // ordinary decorative landing may continue into the exact
                // unchanged Playing snapshot already handled by presentation.
                float required=next.duration;
                foreach(var m in next.motion){float pad;pads.TryGetValue((int)m.fromX,out pad);required=Math.Max(required,Contact(m)+pad);}
                foreach(var m in previous.motion)if(!nextRoutes.ContainsKey(m.id))required=Math.Max(required,Contact(m)-handoff);
                if(required-next.duration>MaximumColumnPadding+Epsilon)return Reject("terminal_flight_extension_exceeds_bound");
                if(previous.duration-handoff-(required-next.duration)<.01f)return Reject("terminal_extension_has_no_net_saving");
                d.nextDuration=required;d.terminalIdleLanding=true;
            }
            var continued=new List<int>();
            foreach(var m in next.motion) {
                float pad;pads.TryGetValue((int)m.fromX,out pad);
                Motion old;
                bool shared=routes.TryGetValue(m.id,out old);
                // Untouched destination routes keep the existing cross-phase
                // landing history. Only the newly retimed/compound routes must
                // finish their entire tail inside this one ownership window.
                bool retimed=pad>Epsilon||shared&&Contact(old)+old.landing>handoff+Epsilon;
                if(Contact(m)+pad+(retimed&&!terminalIdle?m.landing:0)>d.nextDuration+Epsilon)return Reject("following_landing_exceeds_ownership_window");
                if(shared) {
                    if(Contact(old)+old.landing>handoff+m.delay+pad+Epsilon)return Reject("old_landing_overlaps_following_start");
                    if(Contact(old)+old.landing>handoff+Epsilon)continued.Add(m.id);
                }
            }
            var carries=new List<int>();
            foreach(var old in previous.motion) {
                if(nextRoutes.ContainsKey(old.id)||Contact(old)<=handoff+Epsilon)continue;
                Piece p,q;if(changed.Contains(old.id)||!before.TryGetValue(old.id,out p)||!after.TryGetValue(old.id,out q)||!SamePiece(p,q)||previous.damage.Any(h=>h.id==old.id))return Reject("unowned_carry_body_changes");
                if(Columns(old).Any(x=>next.motion.Any(m=>Columns(m).Contains(x))||next.removed.Any(r=>r.piece.x==x)||next.damage.Any(h=>h.x==x)))return Reject("unchanged_carry_intersects_following_paths");
                if(Contact(old)+(terminalIdle?0:old.landing)-handoff>d.nextDuration+Epsilon)return Reject("carry_landing_exceeds_ownership_window");
                carries.Add(old.id);
            }
            if(continued.Count==0)return Reject("no_unfinished_shared_body");
            d.continuedIds=continued.OrderBy(id=>id).ToArray();d.carryIds=carries.OrderBy(id=>id).ToArray();
            d.accepted=true;d.reason=terminalIdle?"terminal_vertical_continuation_with_idle_landing":"single_vertical_column_continuation";return true;
        }

        static bool TerminalIdle(BoardStep next,BoardStep settled)=>next!=null&&settled!=null&&settled.kind=="settled"&&Finite(settled.duration)&&settled.duration>=0&&settled.before?.status=="Playing"&&settled.after?.status=="Playing"&&SameSnapshot(next.after,settled.before)&&SameSnapshot(settled.before,settled.after)&&settled.powerPlan==null&&settled.booster==null&&settled.motion.Count==0&&settled.damage.Count==0&&settled.removed.Count==0&&settled.created.Count==0&&settled.collections.Count==0&&(settled.playbackTracks==null||settled.playbackTracks.Count==0);

        static ContinuedMotion Continue(Motion old,Motion following,float handoff) {
            var first=Clone(old);
            return new ContinuedMotion{id=old.id,fromX=old.fromX,fromY=old.fromY,toX=following.toX,toY=following.toY,delay=old.delay-handoff,seconds=Contact(following)-(old.delay-handoff),landing=following.landing,spawned=old.spawned,clipSpawn=old.clipSpawn,spawnTop=old.spawnTop,previous=first,following=following,handoff=handoff,path=new List<FallLeg>{new FallLeg{fromX=old.fromX,fromY=old.fromY,toX=old.toX,toY=old.toY,delay=old.delay-handoff,seconds=old.seconds,distance=0},new FallLeg{fromX=following.fromX,fromY=following.fromY,toX=following.toX,toY=following.toY,delay=following.delay,seconds=following.seconds,distance=0}}};
        }
        static float Contact(Motion motion)=>motion.delay+motion.seconds;
        static bool Finite(float n)=>!float.IsNaN(n)&&!float.IsInfinity(n);
        static bool Integer(float n)=>Math.Abs(n-(float)Math.Round(n))<Epsilon;
        static bool Vertical(Motion m)=>m.fromX==m.toX&&m.fromY>m.toY&&(m.path==null||m.path.Count==0||m.path.Count==1&&m.path[0].fromX==m.fromX&&m.path[0].fromY==m.fromY&&m.path[0].toX==m.toX&&m.path[0].toY==m.toY&&Math.Abs(m.path[0].delay-m.delay)<Epsilon&&Math.Abs(m.path[0].seconds-m.seconds)<Epsilon&&m.path[0].distance==0);
        static bool Valid(Motion m)=>m!=null&&!(m is ContinuedMotion)&&Finite(m.delay)&&m.delay>=0&&Finite(m.seconds)&&m.seconds>0&&Finite(m.landing)&&m.landing>=0&&m.landing<=TileFall.LandingSeconds+Epsilon&&Finite(m.fromX)&&Finite(m.fromY)&&Finite(m.toX)&&Finite(m.toY)&&Integer(m.fromX)&&Integer(m.toX)&&Integer(m.fromY)&&Integer(m.toY)&&(m.path==null||m.path.All(l=>l!=null&&Finite(l.delay)&&l.delay>=0&&Finite(l.seconds)&&l.seconds>0&&Finite(l.distance)&&l.distance>=0&&Finite(l.fromX)&&Finite(l.fromY)&&Finite(l.toX)&&Finite(l.toY)));
        static bool Simple(BoardStep s,bool crate) {
            if(s==null||s.kind!="powerFall"||s.before?.pieces==null||s.after?.pieces==null||s.before.goals==null||s.after.goals==null||s.powerPlan!=null||s.booster!=null||s.created.Count!=0||s.collections.Count!=0||s.playbackTracks==null||s.playbackTracks.Count!=1)return false;
            var track=s.playbackTracks[0];var match=track.step;
            if(match==null||match.kind!="match"||track.start!=0||track.leadIn!=0||match.powerPlan!=null||match.booster!=null||match.created.Count!=0||match.collections.Count!=0)return false;
            if(s.removed.Any(r=>r.piece==null||!(r.piece.family=="gem"&&r.cause=="match")&&!(r.cause=="obstacle"&&r.piece.hp==1&&(r.piece.family=="moss"||crate&&r.piece.family=="crate"))))return false;
            foreach(var hit in s.damage){var body=s.before.pieces.FirstOrDefault(p=>p.id==hit.id);if(hit.beforeHP!=1||hit.afterHP!=0||hit.family!="moss"&&!(crate&&hit.family=="crate")||body==null||body.ownerId!=0||body.family!=hit.family)return false;}
            return true;
        }
        static IEnumerable<int> Columns(Motion m) {var result=new HashSet<int>();void Span(float a,float b){for(int x=(int)Math.Floor(Math.Min(a,b));x<=(int)Math.Ceiling(Math.Max(a,b));x++)result.Add(x);}Span(m.fromX,m.toX);if(m.path!=null)foreach(var l in m.path)Span(l.fromX,l.toX);return result;}
        static bool SameIdentity(Piece a,Piece b)=>a.id==b.id&&a.family==b.family&&a.color==b.color&&a.hp==b.hp&&a.power==b.power&&a.ownerId==b.ownerId;
        static bool SamePiece(Piece a,Piece b)=>SameIdentity(a,b)&&a.x==b.x&&a.y==b.y;
        static bool SameSnapshot(BoardSnapshot a,BoardSnapshot b) {
            if(a==null||b==null||a.pieces==null||b.pieces==null||a.goals==null||b.goals==null||a.moves!=b.moves||a.turn!=b.turn||a.status!=b.status||a.pieces.Length!=b.pieces.Length||a.goals.Length!=b.goals.Length)return false;
            if(a.pieces.GroupBy(p=>p.id).Any(g=>g.Count()!=1)||b.pieces.GroupBy(p=>p.id).Any(g=>g.Count()!=1))return false;
            var pieces=b.pieces.ToDictionary(p=>p.id);if(a.pieces.Any(p=>!pieces.ContainsKey(p.id)||!SamePiece(p,pieces[p.id])))return false;
            return a.goals.All(g=>b.goals.Any(h=>g.family==h.family&&g.count==h.count));
        }
        static BoardStep Copy(BoardStep s)=>new BoardStep{kind=s.kind,label=s.label,duration=s.duration,triggerTime=s.triggerTime,triggerOriginId=s.triggerOriginId,before=s.before,after=s.after,powerPlan=s.powerPlan,booster=s.booster,playbackTracks=s.playbackTracks,damage=s.damage,removed=s.removed,motion=s.motion,created=s.created,collections=s.collections};
        static Motion Clone(Motion m)=>Shift(m,0);
        static Motion Shift(Motion m,float offset)=>new Motion{id=m.id,fromX=m.fromX,fromY=m.fromY,toX=m.toX,toY=m.toY,delay=m.delay+offset,seconds=m.seconds,landing=m.landing,spawnTop=m.spawnTop,spawned=m.spawned,clipSpawn=m.clipSpawn,path=m.path==null?null:m.path.Select(l=>new FallLeg{fromX=l.fromX,fromY=l.fromY,toX=l.toX,toY=l.toY,delay=l.delay+offset,seconds=l.seconds,distance=l.distance}).ToList()};
    }
}
// END EXACT75 LocalCascadeContinuation.cs

// BEGIN EXACT75 LocalCascadePlayback.cs
namespace HeartOfTheRain.Verification.Checkpoint75Control {
    [Serializable] public sealed class LocalCascadeDecision {
        public int phaseIndex;
        public float handoff,previousDuration,nextDuration,matchReady;
        public int[] carryIds=new int[0],blockingColumns=new int[0];
        public string reason;
        public bool accepted;
    }

    // Conservative scheduling of playback copies; never mutate model steps,
    // snapshots, randomness, match recipes, damage or reward transactions.
    public static class LocalCascadePlayback {
        const float Epsilon=.00001f;

        public static List<BoardStep> Apply(IEnumerable<BoardStep> source,List<LocalCascadeDecision> decisions=null) {
            var result=source.ToList();bool applied=false;
            // Sequential playback never ends a phase before one of its own
            // routes. This signature also detects every previous application
            // of this pass, including carries that had not started at handoff.
            int prior=result.FindIndex(s=>s.motion.Any(m=>Contact(m)>s.duration+Epsilon));
            if(prior>=0){decisions?.Add(new LocalCascadeDecision{phaseIndex=prior,previousDuration=result[prior].duration,reason="already_has_unfinished_phase_routes"});return result;}
            for(int i=0;i+1<result.Count;i++) {
                LocalCascadeDecision decision;
                bool eligible=TryDescribe(result[i],result[i+1],out decision);
                decision.phaseIndex=i;
                if(applied) {decision.accepted=false;decision.reason="second_overlap_disabled";eligible=false;}
                decisions?.Add(decision);
                if(!eligible)continue;
                var previous=result[i];var next=result[i+1];
                var carry=new HashSet<int>(decision.carryIds);
                var shortened=Copy(previous);shortened.duration=decision.handoff;
                var continued=Copy(next);continued.motion=new List<Motion>(next.motion);
                foreach(var motion in previous.motion)if(carry.Contains(motion.id))continued.motion.Add(Shift(motion,-decision.handoff));
                result[i]=shortened;result[i+1]=continued;applied=true;
            }
            return result;
        }

        public static bool TryDescribe(BoardStep previous,BoardStep next,out LocalCascadeDecision decision) {
            var d=new LocalCascadeDecision{previousDuration=previous?.duration??0,nextDuration=next?.duration??0};decision=d;
            bool Reject(string reason){d.reason=reason;return false;}
            if(previous==null||next==null||!Finite(previous.duration)||!Finite(next.duration))return Reject("invalid_phase");
            if(!SimpleMatchFall(previous,true)||!SimpleMatchFall(next,false))return Reject("phase_boundary_not_simple_match_refill");
            if(previous.motion.Count==0||next.motion.Count==0)return Reject("no_refill_routes");
            if(!SameSnapshot(previous.after,next.before))return Reject("snapshot_boundary_mismatch");
            if(new[]{previous.before,previous.after,next.before,next.after}.Any(s=>s==null||s.pieces==null||s.pieces.Any(p=>p.family=="power"||p.family=="pail"||p.family=="crystal"||p.family=="cabinet"||p.family=="pod")))return Reject("power_delivery_or_advanced_body");
            if(previous.motion.Concat(next.motion).Any(m=>!Valid(m)))return Reject("invalid_or_already_shifted_route");
            if(previous.motion.GroupBy(m=>m.id).Any(g=>g.Count()!=1)||next.motion.GroupBy(m=>m.id).Any(g=>g.Count()!=1))return Reject("duplicate_route_owner");
            if(previous.motion.Any(m=>m.path!=null&&m.path.Count>1||m.fromX!=m.toX))return Reject("previous_side_feed_requires_general_scheduler");
            var before=next.before.pieces.ToDictionary(p=>p.id);var after=next.after.pieces.ToDictionary(p=>p.id);
            foreach(var motion in next.motion) {
                Piece body;if(!before.TryGetValue(motion.id,out body)&&!after.TryGetValue(motion.id,out body))return Reject("next_route_has_no_body");
                if(body.family!="gem"||body.ownerId!=0)return Reject("next_route_is_not_plain_gem");
            }
            var matched=next.removed.Where(r=>r.cause=="match"&&r.piece.family=="gem").Select(r=>r.piece.id).ToArray();
            if(matched.Length<3)return Reject("no_plain_match");
            var changed=new HashSet<int>(next.removed.Select(r=>r.piece.id).Concat(next.damage.Select(h=>h.id)).Concat(next.created.Select(p=>p.id)).Concat(next.motion.Select(m=>m.id)));
            var columns=new HashSet<int>();
            foreach(var r in next.removed)columns.Add(r.piece.x);
            foreach(var h in next.damage)columns.Add(h.x);
            foreach(var motion in next.motion)AddColumns(columns,motion);
            d.blockingColumns=columns.OrderBy(x=>x).ToArray();
            var routes=previous.motion.ToDictionary(m=>m.id);
            foreach(int id in matched){Motion motion;if(routes.TryGetValue(id,out motion))d.matchReady=Math.Max(d.matchReady,Contact(motion));}
            float handoff=Math.Max(.08f,d.matchReady);
            // The next snapshot already contains these model deltas. Do not
            // hand it ownership while a preceding clear/body/counter is pending.
            foreach(var r in previous.removed)handoff=Math.Max(handoff,r.time+(r.cause=="obstacle"?.24f:.035f));
            foreach(var hit in previous.damage)handoff=Math.Max(handoff,hit.time+.12f);
            // A conservative whole-column closure includes every route leg,
            // source, destination and diagonal corner. Routes sharing any of
            // those columns must finish before the next phase starts.
            foreach(var motion in previous.motion)if(Columns(motion).Any(columns.Contains))handoff=Math.Max(handoff,Contact(motion));
            d.handoff=handoff;
            if(previous.duration-handoff<.01f)return Reject("no_safe_overlap_saving");
            var carrying=previous.motion.Where(m=>Contact(m)>handoff+Epsilon).ToArray();
            if(carrying.Length==0)return Reject("no_unfinished_disjoint_route");
            if(carrying.Max(m=>Contact(m)+m.landing)-handoff>next.duration+Epsilon)return Reject("next_phase_too_short_for_carry_landing");
            foreach(var motion in next.motion) {
                Motion old;
                if(routes.TryGetValue(motion.id,out old)&&Contact(old)+old.landing>handoff+motion.delay+Epsilon)return Reject("prior_landing_overlaps_next_motion");
            }
            var oldAfter=previous.after.pieces.ToDictionary(p=>p.id);
            foreach(var motion in carrying) {
                Piece old,entry,exit;
                if(changed.Contains(motion.id)||Columns(motion).Any(columns.Contains))return Reject("carry_intersects_next_change");
                if(!oldAfter.TryGetValue(motion.id,out old)||!before.TryGetValue(motion.id,out entry)||!after.TryGetValue(motion.id,out exit)||!SamePiece(old,entry)||!SamePiece(entry,exit))return Reject("carry_body_state_changes");
                if(entry.family!="gem"&&entry.family!="crate"||entry.ownerId!=0||previous.damage.Any(h=>h.id==motion.id))return Reject("carry_body_requires_hit_or_delivery_history");
                if(Math.Abs(entry.x-motion.toX)>Epsilon||Math.Abs(entry.y-motion.toY)>Epsilon)return Reject("carry_destination_mismatch");
            }
            d.carryIds=carrying.Select(m=>m.id).OrderBy(id=>id).ToArray();d.accepted=true;d.reason="single_disjoint_refill_handoff";return true;
        }

        static bool SimpleMatchFall(BoardStep s,bool allowPriorCrate) {
            if(s==null||s.kind!="powerFall"||s.before==null||s.after==null||s.powerPlan!=null||s.booster!=null||s.created.Count!=0||s.collections.Count!=0||s.playbackTracks==null||s.playbackTracks.Count!=1)return false;
            var track=s.playbackTracks[0];var match=track.step;
            if(match==null||match.kind!="match"||track.start!=0||track.leadIn!=0||match.powerPlan!=null||match.booster!=null||match.created.Count!=0||match.collections.Count!=0)return false;
            foreach(var removed in s.removed)if(!(removed.piece.family=="gem"&&removed.cause=="match")&&!(removed.cause=="obstacle"&&removed.piece.hp==1&&(removed.piece.family=="moss"||allowPriorCrate&&removed.piece.family=="crate")))return false;
            foreach(var hit in s.damage) {
                if(hit.beforeHP!=1||hit.afterHP!=0||hit.family!="moss"&&!(allowPriorCrate&&hit.family=="crate"))return false;
                var body=s.before.pieces.FirstOrDefault(p=>p.id==hit.id);
                if(body==null||body.ownerId!=0||body.family!=hit.family)return false;
            }
            return true;
        }
        static float Contact(Motion motion)=>motion.delay+motion.seconds;
        static bool Finite(float value)=>!float.IsNaN(value)&&!float.IsInfinity(value);
        static bool Valid(Motion m) {
            if(m==null||!Finite(m.delay)||!Finite(m.seconds)||m.delay<0||m.seconds<=0||!Finite(m.fromX)||!Finite(m.fromY)||!Finite(m.toX)||!Finite(m.toY))return false;
            return m.path==null||m.path.All(l=>Finite(l.delay)&&Finite(l.seconds)&&l.delay>=0&&l.seconds>0&&Finite(l.fromX)&&Finite(l.fromY)&&Finite(l.toX)&&Finite(l.toY));
        }
        static IEnumerable<int> Columns(Motion motion) {var columns=new HashSet<int>();AddColumns(columns,motion);return columns;}
        static void AddColumns(HashSet<int> columns,Motion motion) {
            void Span(float from,float to){int low=(int)Math.Floor(Math.Min(from,to)),high=(int)Math.Ceiling(Math.Max(from,to));for(int x=low;x<=high;x++)columns.Add(x);}
            Span(motion.fromX,motion.toX);if(motion.path!=null)foreach(var leg in motion.path)Span(leg.fromX,leg.toX);
        }
        static bool SameSnapshot(BoardSnapshot a,BoardSnapshot b) {
            if(a==null||b==null||a.pieces==null||b.pieces==null||a.goals==null||b.goals==null||a.moves!=b.moves||a.turn!=b.turn||a.status!=b.status||a.pieces.Length!=b.pieces.Length||a.goals.Length!=b.goals.Length)return false;
            var pieces=b.pieces.ToDictionary(p=>p.id);foreach(var p in a.pieces){Piece other;if(!pieces.TryGetValue(p.id,out other)||!SamePiece(p,other))return false;}
            var goals=b.goals.ToDictionary(g=>g.family,g=>g.count);foreach(var g in a.goals){int count;if(!goals.TryGetValue(g.family,out count)||count!=g.count)return false;}return true;
        }
        static bool SamePiece(Piece a,Piece b)=>a.id==b.id&&a.x==b.x&&a.y==b.y&&a.family==b.family&&a.color==b.color&&a.hp==b.hp&&a.power==b.power&&a.ownerId==b.ownerId;
        static BoardStep Copy(BoardStep s)=>new BoardStep{kind=s.kind,label=s.label,duration=s.duration,triggerTime=s.triggerTime,triggerOriginId=s.triggerOriginId,before=s.before,after=s.after,powerPlan=s.powerPlan,booster=s.booster,playbackTracks=s.playbackTracks,damage=s.damage,removed=s.removed,motion=s.motion,created=s.created,collections=s.collections};
        static Motion Shift(Motion m,float offset)=>new Motion{id=m.id,fromX=m.fromX,fromY=m.fromY,toX=m.toX,toY=m.toY,delay=m.delay+offset,seconds=m.seconds,landing=m.landing,spawnTop=m.spawnTop,spawned=m.spawned,clipSpawn=m.clipSpawn,path=m.path==null?null:m.path.Select(l=>new FallLeg{fromX=l.fromX,fromY=l.fromY,toX=l.toX,toY=l.toY,delay=l.delay+offset,seconds=l.seconds,distance=l.distance}).ToList()};
    }
}
// END EXACT75 LocalCascadePlayback.cs

#endif

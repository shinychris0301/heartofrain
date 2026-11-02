using System;
using System.Collections.Generic;
using System.Linq;

namespace HeartOfTheRain.M46 {
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

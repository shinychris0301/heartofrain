using System;
using System.Collections.Generic;
using System.Linq;

namespace HeartOfTheRain.M46 {
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
        // Describe's shared validation is independent of its final landing-window
        // policy. Keep the validated inputs on the stack when the strict pass
        // needs the existing terminal retry; never cache across commands.
        struct Prepared {
            public BoardStep previous,next;
            public Dictionary<int,Motion> routes,nextRoutes;
            public Dictionary<int,Piece> before,after;
            public HashSet<int> changed;
            public Dictionary<int,float> pads;
            public float handoff;
        }
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
            return ApplyCurrent(source,decisions);
        }

        // Detached compilers receive their policy explicitly. They must never
        // observe the development-only mutable global control on another thread.
        public static List<BoardStep> ApplyCurrent(IEnumerable<BoardStep> source,List<LocalContinuationDecision> decisions=null) {
            var input=source.ToList();
            if(input.Any(s=>s.motion.Any(IsContinuation))||input.Any(s=>s.motion.Any(m=>Contact(m)>s.duration+Epsilon))) {
                decisions?.Add(new LocalContinuationDecision{reason="already_scheduled_handoff"});return input;
            }
            var result=new List<BoardStep>(input);var findings=new List<LocalContinuationDecision>();
            float start=0;
            for(int i=0;i+1<input.Count;i++) {
                LocalContinuationDecision d;Prepared prepared;
                bool eligible=Describe(input[i],input[i+1],false,out d,out prepared);
                var strict=d;
                if(!eligible&&(d.reason=="following_landing_exceeds_ownership_window"||d.reason=="carry_landing_exceeds_ownership_window")&&i+2==input.Count-1) {
                    if(!TerminalIdle(input[i+1],input[i+2]))d=InvalidTerminal(input[i],input[i+1]);
                    else {d=CopyPrefix(strict);eligible=Complete(ref prepared,true,d);}
                }
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
                    // Every earlier strict candidate and this one already failed.
                    // The only remaining pair ends in the validated settled step,
                    // so checkpoint74 necessarily takes its disjoint fallback.
                    var legacy=LocalCascadePlayback.Apply(input);
                    if(result.Sum(s=>s.duration)>legacy.Sum(s=>s.duration)+Epsilon) {
                        if(decisions!=null) {
                            decisions.Add(new LocalContinuationDecision{reason="expansion_would_outgrow_checkpoint74"});
                            for(int j=0;j+1<findings.Count;j++)decisions.Add(findings[j]);
                            strict.phaseIndex=i;decisions.Add(strict);
                            LocalContinuationDecision tail;TryDescribe(input[i+1],input[i+2],out tail);tail.phaseIndex=i+1;decisions.Add(tail);
                        }
                        return legacy;
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
                decision=InvalidTerminal(previous,next);return false;
            }
            return Describe(previous,next,true,out decision);
        }

        static bool Describe(BoardStep previous,BoardStep next,bool terminalIdle,out LocalContinuationDecision decision) {
            Prepared prepared;return Describe(previous,next,terminalIdle,out decision,out prepared);
        }

        static bool Describe(BoardStep previous,BoardStep next,bool terminalIdle,out LocalContinuationDecision decision,out Prepared prepared) {
            prepared=default(Prepared);
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
            prepared=new Prepared{previous=previous,next=next,routes=routes,nextRoutes=nextRoutes,before=before,after=after,changed=changed,pads=pads,handoff=handoff};
            return Complete(ref prepared,terminalIdle,d);
        }

        static bool Complete(ref Prepared prepared,bool terminalIdle,LocalContinuationDecision d) {
            bool Reject(string why){d.reason=why;return false;}
            var previous=prepared.previous;var next=prepared.next;
            var routes=prepared.routes;var nextRoutes=prepared.nextRoutes;
            var before=prepared.before;var after=prepared.after;
            var changed=prepared.changed;var pads=prepared.pads;float handoff=prepared.handoff;
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

        static LocalContinuationDecision InvalidTerminal(BoardStep previous,BoardStep next)=>new LocalContinuationDecision{previousDuration=previous?.duration??0,nextDuration=next?.duration??0,nextOriginalDuration=next?.duration??0,reason="terminal_successor_not_unchanged_playing_idle"};
        static LocalContinuationDecision CopyPrefix(LocalContinuationDecision source) {
            var result=new LocalContinuationDecision{previousDuration=source.previousDuration,nextDuration=source.nextOriginalDuration,nextOriginalDuration=source.nextOriginalDuration,matchReady=source.matchReady,handoff=source.handoff,columns=(int[])source.columns.Clone()};
            foreach(var pad in source.columnPads)result.columnPads.Add(new LocalContinuationColumn{column=pad.column,padding=pad.padding});
            return result;
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

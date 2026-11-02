#if UNITY_EDITOR
// Exact checkpoint76 sampler, compiled in Assembly-CSharp so its unchanged
// DTO cache fields remain internal. Neither Android configuration includes it.
// Adaptation only: rename both partial classes and share the unchanged DTOs.
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

// BEGIN EXACT76 BoardPresentation.cs
namespace HeartOfTheRain.M46 {
    public sealed partial class FrozenBoardPresentation76 {
        public readonly Dictionary<string,DebrisProfile> profiles=new Dictionary<string,DebrisProfile>();
        public readonly List<TimedStep> history=new List<TimedStep>();
        public int columns,rows;public float bottom=-5,left=-1,right=11;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        public bool VerificationUseLegacyDensityWork,MeasureSamplingCosts;
        public struct SamplingCosts {public double bodiesMs,effectsMs,sortMs;}
        public SamplingCosts LastSamplingCosts {get;private set;}
#endif
        bool OptimizeDensity {get{
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            return !VerificationUseLegacyDensityWork;
#else
            return true;
#endif
        }}
        public void PrepareDebrisGeometry(){foreach(var pair in profiles)if(pair.Key=="crate")PrepareCrateGeometry(pair.Value);}
        static void PrepareCrateGeometry(DebrisProfile profile){
            if(profile.crateAngles!=null&&profile.crateAngles.Length==profile.pieces.Length)return;
            int count=profile.pieces.Length;profile.crateAngles=new float[count];profile.crateSines=new float[count];profile.crateCosines=new float[count];
            for(int i=0;i<count;i++){var p=profile.pieces[i];float angle=Mathf.Atan2(p.centerY,p.centerX)+.24f*Mathf.Sin(i*3.1f);profile.crateAngles[i]=angle;profile.crateSines[i]=Mathf.Sin(angle);profile.crateCosines[i]=Mathf.Cos(angle);}
        }
        public static float CameraHalfHeight(int c,int r,float aspect){return .5f*Mathf.Max(r+6.6f,(c+1.4f)/Mathf.Max(.2f,aspect));}
        static readonly string[] TileKeys={"tile0","tile1","tile2","tile3","tile4","tile5"};
        static readonly string[,] TileBreakKeys=MakeTileBreakKeys();
        static string[,] MakeTileBreakKeys(){var keys=new string[6,3];for(int color=0;color<6;color++)for(int variant=0;variant<3;variant++)keys[color,variant]="Tile"+color+"_V"+variant;return keys;}
        static readonly Dictionary<string,string[]> BodyKeys=new Dictionary<string,string[]>();
        public static string BodyKey(Piece p){if(p.family=="crystal")return "crystalIcon";if(p.family=="gem")return TileKeys[p.color];if(p.family=="pail")return "pail_Full";return BodyHPKey(p.family,p.hp);}
        static string BodyHPKey(string family,int hp){string[] keys;if(!BodyKeys.TryGetValue(family,out keys)){keys=new string[16];for(int i=0;i<keys.Length;i++)keys[i]=family+"_"+i;BodyKeys[family]=keys;}return hp>=0&&hp<keys.Length?keys[hp]:family+"_"+hp;}
        static readonly Dictionary<string,string[]> HitKeys=new Dictionary<string,string[]>();
        static string HitKey(string family,int hp){string[] keys;if(!HitKeys.TryGetValue(family,out keys)){keys=new string[16];string prefix=family+"/"+(family=="pod"?"Pod":Prefix(family))+"_Hit_";for(int i=0;i<keys.Length;i++)keys[i]=prefix+i;HitKeys[family]=keys;}return hp>=0&&hp<keys.Length?keys[hp]:family+"/"+Prefix(family)+"_Hit_"+hp;}
        public static int PowerAtlas(int k){switch(k){case 4:return 9;case 5:return 10;case 7:return 19;case 11:return 29;case 16:return 40;default:return 6;}}
        public static string Idle(int atlas){return atlas==19?"OR_Idle":atlas==29?"RS_Idle":atlas==40?"GS_Idle":"Idle";}
        // M70 body density keeps world size; Seeker FX poses already include their own scale.
        public static float PowerDisplayScale(int atlas)=>atlas==29||atlas==40?1.4f:1f;
        public static string Prefix(string f){switch(f){case "case":return "Case";case "gate":return "Sluice";case "moss":return "Overgrowth";default:return "Stone";}}
        // M70 R2: creation follows a piece across match, gravity and idle.
        sealed class PowerBirth {public int atlas;public float start;}
        readonly Dictionary<int,PowerBirth> powerBirths=new Dictionary<int,PowerBirth>();
        readonly List<int> expiredBirths=new List<int>();
        struct Landing {public Motion motion;public float start;}
        readonly Dictionary<int,Landing> landings=new Dictionary<int,Landing>();
        // A safe early handoff can select a future motion before the previous
        // landing finishes. Retain that old pose until its original expiry.
        readonly Dictionary<int,Landing> priorLandings=new Dictionary<int,Landing>(128);
        readonly List<int> expiredLandings=new List<int>();
        public static string CreationClip(int atlas)=>atlas==19?"OR_Create":atlas==29?"RS_Create":atlas==40?"GS_Create":"Create";
        public static float CreationDuration(int atlas)=>atlas==29||atlas==40?.3f:.6f;
        public static void GeneratedBodyPhase(int atlas,float elapsed,float available,out string key,out float sampleAge){
            float duration=CreationDuration(atlas),window=Mathf.Min(duration,Mathf.Max(0,available));elapsed=Mathf.Max(0,elapsed);
            if(window>0&&elapsed<window){key=CreationClip(atlas);sampleAge=elapsed*duration/window;}
            else {key=Idle(atlas);sampleAge=Mathf.Max(0,elapsed-window);}
        }
        public void RegisterPowerCreation(Piece piece,float start){if(piece.family=="power")powerBirths[piece.id]=new PowerBirth{atlas=PowerAtlas(piece.power),start=start};}
        public void Add(BoardStep step,float start,float leadIn=0)=>AddTrack(step,start,leadIn,step);
        void AddTrack(BoardStep step,float start,float leadIn,BoardStep group){
            foreach(var piece in step.created)RegisterPowerCreation(piece,start);
            if(step.kind=="gravity"||step.kind=="powerFall")foreach(var m in step.motion)if(m.landing>0){
                float contact=start+m.delay+m.seconds;Landing prior;
                if(landings.TryGetValue(m.id,out prior)&&contact>prior.start+.00001f&&prior.start+prior.motion.landing>start&&m.delay>0&&prior.start+prior.motion.landing<=start+m.delay+.00001f&&prior.motion.toX==m.fromX&&prior.motion.toY==m.fromY)priorLandings[m.id]=prior;
                landings[m.id]=new Landing{motion=m,start=contact};
            }
            if(step.playbackTracks!=null){foreach(var track in step.playbackTracks)AddTrack(track.step,start+track.start,track.leadIn,group);return;}
            history.Add(new TimedStep{step=step,group=group,start=start,leadIn=leadIn,expires=start+Mathf.Max(0,HistoryLifetime(step)-leadIn)});
        }
        public void PruneHistory(float time){
            for(int i=history.Count-1;i>=0;i--)if(time>history[i].expires)history.RemoveAt(i);
            expiredLandings.Clear();foreach(var pair in landings)if(time>=pair.Value.start+pair.Value.motion.landing)expiredLandings.Add(pair.Key);
            foreach(int id in expiredLandings)landings.Remove(id);
            expiredLandings.Clear();foreach(var pair in priorLandings)if(time>=pair.Value.start+pair.Value.motion.landing)expiredLandings.Add(pair.Key);
            foreach(int id in expiredLandings)priorLandings.Remove(id);
        }
        public float HistoryLifetime(BoardStep s){
            float end=Mathf.Max(1.1f,s.duration+.3f);
            foreach(var c in s.collections)end=Mathf.Max(end,c.arrival+.3f);
            if(s.powerPlan!=null){foreach(var f in s.powerPlan.effects??new ReviewFx[0])end=Mathf.Max(end,f.start+f.duration+1);foreach(var b in s.powerPlan.beams??new ReviewBeam[0])end=Mathf.Max(end,b.end+1);foreach(var p in s.powerPlan.powers??new ReviewPower[0])end=Mathf.Max(end,p.end+1);}
            foreach(var d in s.damage){DebrisProfile pr;if(!profiles.TryGetValue(d.family,out pr))continue;
                // A profile without gravity never falls off the board: keep its step
                // for a bounded time instead of for the rest of the level.
                if(pr.gravity<=0){end=Mathf.Max(end,d.time+4);continue;}
                foreach(var p in pr.pieces){float scale=pr.pieceScale*p.scaleMultiplier,half=pr.canvasCells*scale*.5f;
                    // Upper bound includes bomb amplification, variation, lift and launch delay.
                    float up=d.family=="crate"?6:(Mathf.Abs(pr.launchSpeed)+2*Mathf.Abs(pr.launchSpeedVariation))*Mathf.Max(1,Mathf.Abs(pr.finalSpeedMultiplier))*1.5f+Mathf.Abs(pr.lift)+3;
                    float distance=Mathf.Max(0,d.y+Mathf.Abs(p.centerY)+half-bottom);
                    float flight=(up+Mathf.Sqrt(up*up+2*pr.gravity*distance))/pr.gravity;
                    end=Mathf.Max(end,d.time+p.launchDelay+.1f+flight+1);
                }
            }
            return end;
        }
        sealed class DrawBuffer:List<DrawSprite>{public readonly List<DrawSprite> pool=new List<DrawSprite>();}
        readonly DrawBuffer drawBuffer=new DrawBuffer();
        DrawSprite[] sortScratch=Array.Empty<DrawSprite>();readonly int[] orderCounts=new int[256];
        public void ReserveDrawCapacity(int capacity){
            if(drawBuffer.Capacity<capacity)drawBuffer.Capacity=capacity;
            if(drawBuffer.pool.Capacity<capacity)drawBuffer.pool.Capacity=capacity;
            while(drawBuffer.pool.Count<capacity)drawBuffer.pool.Add(new DrawSprite());
            if(sortScratch.Length<capacity)Array.Resize(ref sortScratch,capacity);
        }
        void SortDraws(List<DrawSprite> list){
            if(!OptimizeDensity){for(int i=0;i<list.Count;i++)list[i].sequence=i;list.Sort((a,b)=>{int order=a.order.CompareTo(b.order);return order!=0?order:a.sequence.CompareTo(b.sequence);});return;}
            int min=int.MaxValue,max=int.MinValue;for(int i=0;i<list.Count;i++){var d=list[i];d.sequence=i;min=Math.Min(min,d.order);max=Math.Max(max,d.order);}
            long range=(long)max-min+1;
            if(list.Count<32||range>orderCounts.Length){list.Sort((a,b)=>{int order=a.order.CompareTo(b.order);return order!=0?order:a.sequence.CompareTo(b.sequence);});return;}
            // Stable counting sort retains the exact submission sequence within
            // each layer, without comparing every pair of debris sprites.
            if(sortScratch.Length<list.Count)Array.Resize(ref sortScratch,Math.Max(list.Count,sortScratch.Length*2));
            Array.Clear(orderCounts,0,(int)range);for(int i=0;i<list.Count;i++)orderCounts[list[i].order-min]++;
            int offset=0;for(int i=0;i<range;i++){int count=orderCounts[i];orderCounts[i]=offset;offset+=count;}
            for(int i=0;i<list.Count;i++){var d=list[i];sortScratch[orderCounts[d.order-min]++]=d;}
            for(int i=0;i<list.Count;i++)list[i]=sortScratch[i];
        }
        readonly List<Piece> bodyCache=new List<Piece>();readonly HashSet<int> bodyIds=new HashSet<int>();
        BoardStep cachedStep;BoardSnapshot cachedSnapshot;
        readonly Piece scratch=new Piece();
        readonly Dictionary<int,Removed> removals=new Dictionary<int,Removed>();readonly Dictionary<int,Motion> motions=new Dictionary<int,Motion>();readonly Dictionary<int,Piece> creations=new Dictionary<int,Piece>();
        // Current authored boards have at most 121 cells. Reserve before input
        // so the first dense hit cannot grow this per-frame lookup.
        readonly Dictionary<int,Damage> activeDamage=new Dictionary<int,Damage>(128);
        void CacheActiveDamage(BoardStep step,float age){
            activeDamage.Clear();if(step==null||!OptimizeDensity)return;
            foreach(var hit in step.damage){if(!(hit.time<=age))continue;Damage previous;if(!activeDamage.TryGetValue(hit.id,out previous)||hit.time>=previous.time)activeDamage[hit.id]=hit;}
        }
        Damage ActiveDamage(BoardStep step,int id,float age){if(!OptimizeDensity)return LastDamage(step,id,age);Damage hit;activeDamage.TryGetValue(id,out hit);return hit;}
        struct BasicHit {public Damage damage;public float at,age;}
        readonly Dictionary<int,BasicHit> recentBasicHits=new Dictionary<int,BasicHit>();
        void CacheBasicHits(float time){
            recentBasicHits.Clear();
            foreach(var entry in history){if(time<entry.start)continue;float local=time-entry.start+entry.leadIn;
                foreach(var damage in entry.step.damage){if(damage.family!="stone"&&damage.family!="moss"&&damage.family!="case"&&damage.family!="gate")continue;float age=local-damage.time;if(age<0||age>=.8f)continue;float at=entry.start+damage.time-entry.leadIn;BasicHit old;if(!recentBasicHits.TryGetValue(damage.id,out old)||at>=old.at)recentBasicHits[damage.id]=new BasicHit{damage=damage,at=at,age=age};}
            }
        }
        Damage BodyDamage(BoardStep active,int id,float activeAge,float time,out float hitAge){
            var hit=ActiveDamage(active,id,activeAge);hitAge=hit==null?0:activeAge-hit.time;BasicHit recent;
            // Keep the active sample on equal contacts. A later visual phase can
            // retain the newest unfinished hit without retaining an old body.
            if(recentBasicHits.TryGetValue(id,out recent)&&(hit==null||recent.at>time-activeAge+hit.time+.00001f)){hit=recent.damage;hitAge=recent.age;}
            return hit;
        }
        void CacheBodies(BoardStep step,BoardSnapshot snapshot){
            if(step==cachedStep&&snapshot==cachedSnapshot)return;cachedStep=step;cachedSnapshot=snapshot;bodyCache.Clear();bodyIds.Clear();removals.Clear();motions.Clear();creations.Clear();
            foreach(var p in snapshot.pieces){bodyCache.Add(p);bodyIds.Add(p.id);}
            if(step!=null){
            foreach(var p in step.after.pieces)if(bodyIds.Add(p.id))bodyCache.Add(p);
            foreach(var r in step.removed)removals[r.piece.id]=r;
            foreach(var m in step.motion)motions[m.id]=m;
            foreach(var p in step.created)creations[p.id]=p;
            }
            // Only rebuild this set on snapshot/step changes; keep sampling pooled.
            expiredBirths.Clear();foreach(var pair in powerBirths)if(!bodyIds.Contains(pair.Key))expiredBirths.Add(pair.Key);
            foreach(int id in expiredBirths)powerBirths.Remove(id);
        }
        static DrawSprite Draw(List<DrawSprite> list,string bank,string key,float age,float x,float y,int order=10,float scale=1,int atlas=0){
            var buffer=list as DrawBuffer;DrawSprite d;
            if(buffer!=null){while(buffer.pool.Count<=list.Count)buffer.pool.Add(new DrawSprite());d=buffer.pool[list.Count];}else d=new DrawSprite();
            d.bank=bank;d.key=key;d.age=age;d.x=x;d.y=y;d.order=order;d.sx=d.sy=scale;d.atlas=atlas;d.angle=d.glow=0;d.alpha=d.red=d.green=d.blue=1;d.masked=d.uiOverlay=false;d.pieceId=0;d.sequence=list.Count;list.Add(d);return d;
        }
        internal static Damage LastDamage(BoardStep step,int id,float age){Damage hit=null;if(step!=null)foreach(var d in step.damage)if(d.id==id&&d.time<=age&&(hit==null||d.time>=hit.time))hit=d;return hit;}
        static float Ease(float t){return Mathf.SmoothStep(0,1,Mathf.Clamp01(t));}
        static Piece ShufflePiece(Piece[] pieces,int id){foreach(var piece in pieces)if(piece.id==id)return piece;throw new InvalidOperationException("Piece missing from shuffle snapshot");}
        // Keep snapshot ownership for offline/review callers. The live renderer
        // consumes SampleLive synchronously and never retains its pooled output.
        public List<DrawSprite> Sample(BoardStep active,BoardSnapshot idle,float time,float stepStart)=>SampleLive(active,idle,time,stepStart).Select(d=>d.Copy()).ToList();
        public List<DrawSprite> SampleLive(BoardStep active,BoardSnapshot idle,float time,float stepStart){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            long bodyStamp=MeasureSamplingCosts?System.Diagnostics.Stopwatch.GetTimestamp():0;
#endif
            var list=drawBuffer;list.Clear();float age=time-stepStart;var snapshot=active==null?idle:active.before;CacheBodies(active,snapshot);CacheBasicHits(time);CacheActiveDamage(active,age);
            if(active!=null)foreach(var made in active.created)if(made.family=="power"&&!powerBirths.ContainsKey(made.id))RegisterPowerCreation(made,stepStart);
            foreach(var original in bodyCache){var p=scratch;p.x=original.x;p.y=original.y;p.id=original.id;p.color=original.color;p.hp=original.hp;p.power=original.power;p.ownerId=original.ownerId;p.family=original.family;if(!p.IsAnchor)continue;if(AdvancedBody(list,p,active,age,time))continue;float scale=1,x=p.x,y=p.y,glow=0,landing=0,stretch=0;bool visible=true;string bank="body",key=BodyKey(p);int atlas=0;float sampleAge=time;
                if(active!=null){
                    Removed removed;removals.TryGetValue(p.id,out removed);
                    if(removed!=null){float end=removed.time+(removed.cause=="obstacle"?.24f:removed.cause=="delivery"?0:.035f);if(age>=end)visible=false;}
                }
                float da;var damage=BodyDamage(active,p.id,age,time,out da);
                    if(damage!=null){if(p.family=="crate"){if(da>=.1f){p.hp=Math.Max(1,damage.afterHP);key=BodyKey(p);}scale=1+.05f*Mathf.Sin(Mathf.Clamp01(da/.18f)*Mathf.PI);}
                        else if(da<.8f&&visible){bank="obstacle";key=HitKey(p.family,damage.beforeHP);sampleAge=da;}
                        else {p.hp=Math.Max(1,damage.afterHP);key=BodyKey(p);}}
                if(active!=null){
                    Removed removed;removals.TryGetValue(p.id,out removed);
                    Motion motion;motions.TryGetValue(p.id,out motion);
                    if(motion!=null){float motionAge;var pose=LocalCascadeContinuation.Segment(motion,age,out motionAge);float seconds=pose.seconds>0?pose.seconds:active.duration,u=Mathf.Clamp01((motionAge-pose.delay)/seconds);bool falling=active.kind=="gravity"||active.kind=="powerFall";float e=active.kind=="reject"?Mathf.Sin(u*Mathf.PI):falling?TileFall.Progress(TileFall.Distance(pose),u):Ease(u);x=pose.fromX+(pose.toX-pose.fromX)*e;y=pose.fromY+(pose.toY-pose.fromY)*e;if(falling)TileFall.Position(motion,age,out x,out y);
                        if(falling&&TileFall.Moving(motion,age)&&(p.family=="gem"||p.family=="power"))stretch=.05f*Mathf.Sin(u*Mathf.PI);
                        if(falling&&pose.landing>0){float v=(motionAge-pose.delay-seconds)/pose.landing;if(v>0&&v<1)landing=Mathf.Sin(v*Mathf.PI)*Mathf.Exp(-2*v);y-=.075f*landing;}
                        if(pose.clipSpawn&&(motionAge<pose.delay||y>pose.spawnTop+1))visible=false;
                        if(p.family=="pail"&&falling){bank="obstacle";key="pail/Pail_Fall";sampleAge=Mathf.Max(0,motionAge-pose.delay);}}
                    if(active.kind=="deliver"&&p.family=="pail"&&removed!=null){bank="obstacle";key="pail/Pail_Collect";sampleAge=age;}
                    Piece made;creations.TryGetValue(p.id,out made);
                    if(made!=null){if(active.kind=="grow"){bank="obstacle";key="moss/Overgrowth_Grow";sampleAge=age;}else{p=made;if(p.family!="power")scale=.65f+.35f*Ease(age/.22f)+.12f*Mathf.Sin(Mathf.Clamp01(age/.28f)*Mathf.PI);}}
                    if(active.kind=="shuffle"&&age>=.22f){p=ShufflePiece(active.after.pieces,p.id);key=BodyKey(p);}
                    if(active.powerPlan!=null&&p.family=="gem"){var tile=active.powerPlan.TileAt(p.x,p.y);if(tile!=null)glow=active.powerPlan.TargetGlow(tile,age);}
                    if(active.playbackTracks!=null&&p.family=="gem"&&motion==null)foreach(var track in active.playbackTracks){if(age<track.start||track.step.powerPlan==null)continue;float a=age-track.start+track.leadIn;var tile=track.step.powerPlan.TileAt(p.x,p.y);if(tile!=null)glow=Mathf.Max(glow,track.step.powerPlan.TargetGlow(tile,a));}
                }
                // A completed fall no longer blocks the next match. Retain
                // its short landing pose on bodies still at that cell.
                Landing landed=default(Landing);Motion upcoming;
                bool oldLanding=active!=null&&motions.TryGetValue(p.id,out upcoming)&&age<upcoming.delay&&priorLandings.TryGetValue(p.id,out landed);
                if(!oldLanding)oldLanding=(active==null||!motions.ContainsKey(p.id))&&landings.TryGetValue(p.id,out landed);
                if(oldLanding&&p.x==landed.motion.toX&&p.y==landed.motion.toY){float v=(time-landed.start)/landed.motion.landing;if(v>0&&v<1){landing=Mathf.Sin(v*Mathf.PI)*Mathf.Exp(-2*v);y-=.075f*landing;}}
                if(!visible)continue;
                if(p.family=="power"){
                    bank="power";atlas=PowerAtlas(p.power);key=Idle(atlas);sampleAge=time;scale*=PowerDisplayScale(atlas);
                    PowerBirth birth;if(powerBirths.TryGetValue(p.id,out birth)&&birth.atlas==atlas&&time>=birth.start){
                        float bornAge=time-birth.start;GeneratedBodyPhase(atlas,bornAge,CreationDuration(atlas),out key,out sampleAge);
                        if(bornAge<10f/30f)Draw(list,"power","StarCreate",bornAge,x,y,35,1,12);
                    }
                }
                var body=Draw(list,bank,key,sampleAge,x,y,10,scale,atlas);body.pieceId=p.id;body.sx*=1-.5f*stretch+.10f*landing;body.sy*=1+stretch-.14f*landing;body.masked=true;body.glow=glow;
                if(active!=null&&active.booster!=null)BoosterTimeline.Body(active,p,body,age);
            }
            // Effects are independent of the settling phase. Fragments survive into refill.
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            long effectStamp=MeasureSamplingCosts?System.Diagnostics.Stopwatch.GetTimestamp():0;
#endif
            foreach(var entry in history){if(time<entry.start)continue;float t=time-entry.start+entry.leadIn;var s=entry.step;
                if(s.powerPlan!=null)PowerEffects(list,s.powerPlan,t,s);
                if(s.booster!=null)BoosterTimeline.Effects(list,s,t);
                foreach(var r in s.removed){float a=t-r.time;if(r.piece.family=="gem"&&(r.cause=="match"||r.cause=="power")&&a>=0&&a<16f/30f){int variant=(r.piece.x*7+r.piece.y*11)%3;Draw(list,"power",TileBreakKeys[r.piece.color,variant],a,r.piece.x,r.piece.y,40,1,2+variant);if(a>=.025f)Draw(list,"power","StarBurst",a-.025f,r.piece.x,r.piece.y,45,.72f,12);}
                    if(r.cause=="delivery"&&t<1.1f)Draw(list,"obstacle","pail/Pail_Collection_FX",t,r.piece.x,r.piece.y,35);}
                foreach(var d in s.damage)ObstacleEffects(list,d,t-d.time,s);
                CollectionEffects(list,s,t);
            }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            long sortStamp=MeasureSamplingCosts?System.Diagnostics.Stopwatch.GetTimestamp():0;
#endif
            SortDraws(list);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(MeasureSamplingCosts){double factor=1000.0/System.Diagnostics.Stopwatch.Frequency;LastSamplingCosts=new SamplingCosts{bodiesMs=(effectStamp-bodyStamp)*factor,effectsMs=(sortStamp-effectStamp)*factor,sortMs=(System.Diagnostics.Stopwatch.GetTimestamp()-sortStamp)*factor};}
#endif
            return list;
        }
        void PowerEffects(List<DrawSprite> list,ReviewPlan plan,float t,BoardStep step){
            foreach(var e in plan.effects??Array.Empty<ReviewFx>()){float age=t-e.start;if(age<0||age>=e.duration)continue;var pose=plan.EffectTransform(e,age);var d=Draw(list,"power",e.clip,age,pose.x,pose.y,e.order,pose.z,e.atlas);d.angle=plan.EffectAngle(e,age);float opacity=e.ramp>0?Ease(age/e.ramp):1;
                if(e.clip=="OR_Target")opacity*=1-Ease((age-e.duration+.08f)/.08f);
                if(e.clip=="OR_Orbit"||e.clip=="OR_SpinStars"||e.clip=="DO_SpinLight"||e.clip=="DO_SpinStars")opacity*=1-Ease((age-e.duration+.075f)/.075f);
                if(e.fadeIn>0)opacity*=Ease(age/e.fadeIn);if(e.fadeOut>0)opacity*=1-Ease((age-e.duration+e.fadeOut)/e.fadeOut);d.alpha=opacity;
            }
            foreach(var b in plan.beams??Array.Empty<ReviewBeam>()){float a=t-b.start;if(a<0||t>=b.end)continue;float progress=Mathf.Clamp01(a/b.travel);var start=ReviewPlan.BeamPoint(b,0);var end=ReviewPlan.BeamPoint(b,progress);float length=Vector2.Distance(start,end);float angle=Mathf.Atan2(end.y-start.y,end.x-start.x)*Mathf.Rad2Deg;
                if(length>.001f){var d=Draw(list,"power","OR_Link",a,(start.x+end.x)*.5f,(start.y+end.y)*.5f,16,1,20);d.sx=length;d.angle=angle;d.alpha=(1-Ease((a-b.travel-.025f)/.16f))*(1-Ease((t-b.end+.04f)/.04f));}
                if(a<b.travel){var d=Draw(list,"power","OR_Packet",a,end.x,end.y,18,1,20);d.angle=angle;}}
            int sourceCount=0;foreach(var source in step.removed)if(source.cause=="source")sourceCount++;
            foreach(var p in plan.powers??Array.Empty<ReviewPower>()){if(t<p.begin||t>=p.end)continue;float charge=p.charge>0?Mathf.Clamp01((t-p.end+p.charge)/p.charge):0;float appear=p.begin>0?Ease((t-p.begin)/.12f):1;float x=p.x,y=p.y;
                // Approved merge sheets are authored horizontally. A vertical partner
                // moves into that visual pose; its real cell remains reserved by logic.
                if(p.begin==0&&p.y!=plan.originY&&sourceCount==2&&p.x==plan.originX){float u=Ease((t-.15f)/.3f);float side=plan.originX+1<columns?1:-1;x+=(plan.originX+side-x)*u;y+=(plan.originY-y)*u;}
                string bodyKey=charge>0?"Charge":Idle(p.atlas);float bodyAge=charge>0?charge*.4f:t-p.begin;
                float window=p.end-Mathf.Max(0,p.charge)-p.begin;bool forming=p.begin>0&&charge<=0&&window>0;
                if(forming)GeneratedBodyPhase(p.atlas,t-p.begin,window,out bodyKey,out bodyAge);
                float reveal=forming?1:appear;
                var d=Draw(list,"power",bodyKey,bodyAge,x,y,20,PowerDisplayScale(p.atlas)*(1+.13f*charge)*(.15f+.85f*reveal),p.atlas);d.alpha=reveal;
            }
        }
        void ObstacleEffects(List<DrawSprite> list,Damage d,float t,BoardStep step){if(t<0)return;
            if(d.family=="cabinet"){if(t<.8f)Draw(list,"obstacle","cabinet/Star_Accent",t,d.x+.5f,d.y+.5f,32,.7f);return;}
            if(d.family=="crystal"||d.family=="pod")t-=.1f;if(t<0)return;
            DebrisProfile pr;if(!profiles.TryGetValue(d.family,out pr))return;
            if(pr.renderFamily!=d.family||pr.pieceKeys==null||pr.pieceKeys.Length!=pr.pieces.Length){
                pr.renderFamily=d.family;pr.pieceKeys=new string[pr.pieces.Length];for(int i=0;i<pr.pieces.Length;i++)pr.pieceKeys[i]=d.family+"/"+pr.pieces[i].name;
                string hit=d.family=="crate"?"Star_Accent":d.family=="gate"?"Sluice_Hit_Accent":d.family=="crystal"?"Crystal_Impact_Burst":d.family=="pod"?"Pod_Hit_Accent":Prefix(d.family)+"_Hit_Accent";
                string clear=d.family=="crate"?"Star_Accent":d.family=="gate"?"Sluice_Water_Release":d.family=="crystal"?"Crystal_Final_Burst":d.family=="pod"?"Pod_Release_Burst":Prefix(d.family)+"_Clear_Accent";
                pr.hitAccentKey=d.family+"/"+hit;pr.clearAccentKey=d.family+"/"+clear;
            }
            bool clearAccent=d.family=="crystal"||d.family=="pod"?d.afterHP==0:d.beforeHP==1;
            if(t<1)Draw(list,"obstacle",clearAccent?pr.clearAccentKey:pr.hitAccentKey,t,d.x,d.y,32);
            int kind=step.powerPlan==null?-1:step.powerPlan.kind;
            bool bomb=kind==2||kind==3||kind==9||kind==13||kind==18||kind==21,rocket=kind==4||kind==5||kind==6||kind==8||kind==12||kind==17,vertical=step.powerPlan!=null&&(kind==5||step.powerPlan.rocketVertical);
            bool cachedCrate=d.family=="crate"&&OptimizeDensity;int variation=(d.x*31+d.y*17)%11;
            float commonAge=t-.012f*(variation%4),commonExp=0;
            if(cachedCrate){PrepareCrateGeometry(pr);commonExp=Mathf.Exp(-commonAge*pr.drag);}
            int k=0;for(int pieceIndex=0;pieceIndex<pr.pieces.Length;pieceIndex++){var p=pr.pieces[pieceIndex];if(d.family!="crate"&&p.beforeHP!=d.beforeHP)continue;if(d.family=="crate"&&k>=(d.beforeHP==1?8:4))break;int v=(d.x*31+d.y*17)%11;float a=t-p.launchDelay-.012f*(v%4);int i=k++;if(a<0)continue;float theta,speed,vx,vy,lift;
                if(d.family=="crate"){theta=cachedCrate?pr.crateAngles[i]:Mathf.Atan2(p.centerY,p.centerX)+.24f*Mathf.Sin(i*3.1f);speed=(2+.15f*(i%4))*(bomb?1.3f:1);vx=rocket?2.5f+.16f*i:(cachedCrate?pr.crateCosines[i]:Mathf.Cos(theta))*speed;vy=(cachedCrate?pr.crateSines[i]:Mathf.Sin(theta))*(rocket?.9f:speed);lift=.8f;}
                else {theta=p.angleDegrees*Mathf.Deg2Rad;speed=(pr.launchSpeed+pr.launchSpeedVariation*(i%3))*(d.beforeHP==1?pr.finalSpeedMultiplier:1)*(bomb?1.18f:1);vx=rocket?3.4f+.12f*i:Mathf.Cos(theta)*speed;vy=Mathf.Sin(theta)*speed*(rocket?.8f:1);lift=pr.lift;}
                if(rocket&&vertical){vx=(cachedCrate?pr.crateCosines[i]:Mathf.Cos(theta))*speed*.8f;vy=-1.2f-.09f*i;}vx*=.9f+.02f*v;vy*=.94f+.015f*v;
                float scale=pr.pieceScale*p.scaleMultiplier,half=pr.canvasCells*scale*.5f,x=d.x+p.centerX,y=d.y+p.centerY+(d.family=="crystal"?-.25f:0);
                x=Mathf.Clamp(x,left+half,right-half);vx=Mathf.Clamp(vx,(left+half-x)*pr.drag,(right-half-x)*pr.drag);
                bool common=cachedCrate&&p.launchDelay==0;
                x+=vx*(1-(common?commonExp:Mathf.Exp(-a*pr.drag)))/pr.drag;y+=(vy+lift)*a-.5f*pr.gravity*a*a;
                if(y+half<bottom)continue;
                Draw(list,"obstacle",pr.pieceKeys[pieceIndex],a*p.spinMultiplier*(.86f+.026f*v),x,y,43,scale);
            }
        }
        Goal[] displayedGoals;
        public bool GoalFlightsPending(float time){foreach(var e in history)foreach(var c in e.step.collections)if(time<e.start+c.arrival-e.leadIn)return true;return false;}
        public Goal[] DisplayGoals(BoardStep step,BoardSnapshot idle,float age)=>step==null?idle.goals:DisplayGoalsLive(step,idle,age).Select(g=>new Goal{family=g.family,count=g.count}).ToArray();
        public Goal[] DisplayGoalsLive(BoardStep step,BoardSnapshot idle,float age,float time=float.NaN){
            var source=step==null?idle.goals:step.before.goals;if(displayedGoals==null||displayedGoals.Length!=source.Length){displayedGoals=new Goal[source.Length];for(int i=0;i<source.Length;i++)displayedGoals[i]=new Goal();}var goals=displayedGoals;for(int i=0;i<goals.Length;i++){goals[i].family=source[i].family;goals[i].count=source[i].count;}
            // Later snapshots already contain earlier model deltas. Hold only
            // their unfinished flights in the displayed counter, once, until
            // arrival; the model and durable reward settlement are untouched.
            if(!float.IsNaN(time))foreach(var entry in history)if(!ReferenceEquals(entry.group,step))foreach(var c in entry.step.collections)if(time<entry.start+c.arrival-entry.leadIn)foreach(var g in goals)if(g.family==c.family){g.count+=c.amount;break;}
            if(step==null)return goals;
            foreach(var r in step.removed)if((r.cause=="obstacle"||r.cause=="delivery")&&r.piece.family!="pod"&&r.piece.family!="cabinet"){float when=r.time+(r.cause=="obstacle"?.24f:0);if(age>=when)foreach(var g in goals)if(g.family==r.piece.family){g.count--;break;}}
            foreach(var c in step.collections)if(age>=c.arrival)foreach(var g in goals)if(g.family==c.family){g.count-=c.amount;break;}
            if(step.kind=="grow"&&age>=.3f)foreach(var g in goals)if(g.family=="moss"){g.count++;break;}return goals;
        }
    }
}
// END EXACT76 BoardPresentation.cs

// BEGIN EXACT76 AdvancedObstaclePresentationPure.cs
namespace HeartOfTheRain.M46 {
    public sealed partial class FrozenBoardPresentation76 {
        static readonly string[] CrystalPulseKeys={"crystal/Crystal_Pulse_Base","crystal/Crystal_Pulse_Middle","crystal/Crystal_Pulse_Top"};
        public readonly Dictionary<string,Vector2> goalTargets=new Dictionary<string,Vector2>();
        bool AdvancedBody(List<DrawSprite> list,Piece p,BoardStep step,float age,float time){
            if(p.family!="crystal"&&p.family!="cabinet"&&p.family!="pod")return false;
            var hit=ActiveDamage(step,p.id,age);
            float t=hit==null?-1:age-hit.time;
            if(p.family=="crystal"){
                float height=hit==null?p.hp:CrystalHeight(hit.beforeHP,t);
                float b=height>=2?1:height>=1?.34f+.66f*(height-1):.34f*height;
                float middle=Mathf.Max(0,height-2),c=height-b-middle,bottom=p.y-.5f;
                for(int i=0;i<3;i++){
                    float size=i==0?b:i==1?middle:c;
                    if(size>.00001f){var d=Draw(list,"obstacle",CrystalPulseKeys[i],t<0?.8f:t,p.x,bottom+size/2,10);d.sy=size;d.masked=true;}
                    bottom+=size;
                }
                return true;
            }
            if(p.family=="pod"){
                if(hit!=null&&hit.afterHP==0&&t>=.24f)return true;
                if(hit!=null&&t<.8f){var d=Draw(list,"obstacle",HitKey("pod",hit.beforeHP),t,p.x,p.y,10);d.masked=true;}
                else {var d=Draw(list,"body",BodyHPKey("pod",hit==null?p.hp:hit.afterHP),time,p.x,p.y,10);d.masked=true;}
                return true;
            }
            if(hit!=null&&hit.afterHP==0&&t>=.8f)return true;
            DrawSprite body;
            if(hit!=null&&hit.beforeHP==5&&t<.9f)body=Draw(list,"obstacle","cabinet/Cabinet_Open",t,p.x+.5f,p.y+.5f,10);
            else if(hit!=null&&hit.afterHP==0)body=Draw(list,"obstacle","cabinet/Cabinet_Clear",t,p.x+.5f,p.y+.5f,10);
            else body=Draw(list,"body",BodyHPKey("cabinet",hit==null?p.hp:t<.1f?hit.beforeHP:hit.afterHP),time,p.x+.5f,p.y+.5f,10);
            body.masked=true;return true;
        }
        static float CrystalHeight(int before,float t){
            if(t<.1f)return before-.055f*Mathf.Sin(Mathf.PI*t/.1f);
            float u=Mathf.Clamp01((t-.1f)/.1f),h=before-u*u*(3-2*u);
            if(before>1&&t>=.2f&&t<.48f)h-=.045f*Mathf.Sin(Mathf.PI*(t-.2f)/.28f)*Mathf.Exp(-(t-.2f)*9);
            return Mathf.Max(0,h);
        }
        static Vector2 FlightPoint(GoalCollection c,float t,Vector2 target){
            var origin=new Vector2(c.x+c.offsetX,c.y+c.offsetY);
            float duration=c.arrival-c.launch,side=target.x<origin.x?-1:1;
            if(c.family=="pod"&&t<.28f)return new Vector2(origin.x,origin.y+.7f*Ease(t/.28f));
            float u=Ease(c.family=="pod"?(t-.28f)/(duration-.28f):t/duration),v=1-u;
            if(c.family=="pod")origin.y+=.7f;
            var a=new Vector2(origin.x+side*(c.family=="pod"?.9f:1.15f),origin.y+(c.family=="pod"?2:.85f));
            var b=new Vector2(target.x-side*1.25f,target.y+.8f);
            return new Vector2(v*v*v*origin.x+3*v*v*u*a.x+3*v*u*u*b.x+u*u*u*target.x,v*v*v*origin.y+3*v*v*u*a.y+3*v*u*u*b.y+u*u*u*target.y);
        }
        void CollectionEffects(List<DrawSprite> list,BoardStep step,float time){
            foreach(var c in step.collections){
                float age=time-c.launch,duration=c.arrival-c.launch;if(age<0||age>duration+.25f)continue;
                Vector2 target;if(!goalTargets.TryGetValue(c.family,out target))target=new Vector2((columns-1)*.5f,rows+1.6f);
                if(age>=duration){var d=Draw(list,"body","collectionGlint",0,target.x,target.y,72,.55f+.4f*Ease((age-duration)/.25f));d.alpha=1-(age-duration)/.25f;d.uiOverlay=true;continue;}
                var pos=FlightPoint(c,age,target);float u=Mathf.Clamp01(age/duration);
                var body=Draw(list,"body",c.family=="pod"?"waterSpirit":"rainlight",0,pos.x,pos.y,70,c.family=="pod"?(age<.28f?.38f+.42f*Ease(age/.28f):.8f-.38f*Ease((age-.28f)/(duration-.28f))):.55f*(1+.28f*Mathf.Sin(Mathf.PI*u))*(1-.48f*Mathf.Pow(u,5)));
                body.uiOverlay=true;body.angle=10*Mathf.Sin(age*10)*Mathf.Sin(Mathf.PI*u);
                for(int i=1;i<=3;i++){float past=age-.07f*i;if(past<0)continue;var pt=FlightPoint(c,past,target);var glint=Draw(list,"body","collectionGlint",0,pt.x,pt.y,69,.18f-.025f*i);glint.alpha=.7f-.13f*i;glint.uiOverlay=true;}
            }
        }
    }
}
// END EXACT76 AdvancedObstaclePresentationPure.cs
#endif

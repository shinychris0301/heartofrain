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
    public static class LocalCascadeVerification {
        [Serializable] public sealed class Row {
            public string name,turnHash,finalHash,sequentialTurnHash,refinedTurnHash,sequentialFinalHash,refinedFinalHash;
            public int accepted;public float sequentialSeconds,refinedSeconds;
            public List<LocalCascadeDecision> decisions=new List<LocalCascadeDecision>();
        }
        [Serializable] public sealed class Timing {
            public string name,scope="Warm native Editor elapsed planner work; not Android frame/touch latency";
            public int iterations,gen0Collections;public double medianMs,p95Ms,maxMs;
        }
        [Serializable] public sealed class Report {
            public string status,utc,scope="Native Unity model hashes, restricted presentation planner, actual BoardPresentation samples and deterministic clock checks. Android visibility/performance requires a separately built APK.";
            public int checks,modelCases,mixedCases,acceptedHandoffs,guardCases;
            public bool rawTurnParity=true,finalSnapshotParity=true;
            public List<string> errors=new List<string>();
            public List<Row> rows=new List<Row>();
            public List<LocalCascadeRendererChecks.Row> rendererRows=new List<LocalCascadeRendererChecks.Row>();
            public List<Timing> plannerTimings=new List<Timing>();
        }
        [Serializable] sealed class Steps {public List<BoardStep> steps;}
        static string Hash(string value){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(Encoding.UTF8.GetBytes(value))).Replace("-","").ToLowerInvariant();}
        static string Json(List<BoardStep> steps)=>JsonUtility.ToJson(new Steps{steps=steps});
        static BoardStep Copy(BoardStep s)=>new BoardStep{kind=s.kind,label=s.label,duration=s.duration,triggerTime=s.triggerTime,triggerOriginId=s.triggerOriginId,before=s.before,after=s.after,powerPlan=s.powerPlan,booster=s.booster,playbackTracks=s.playbackTracks,damage=s.damage,removed=s.removed,motion=s.motion,created=s.created,collections=s.collections};
        static BoardSnapshot SnapshotCopy(BoardSnapshot s)=>new BoardSnapshot{pieces=s.pieces.Select(p=>p.Copy()).ToArray(),goals=s.goals.Select(g=>new Goal{family=g.family,count=g.count}).ToArray(),moves=s.moves,turn=s.turn,status=s.status};

        public static void Run() {
            var report=new Report{utc=DateTime.UtcNow.ToString("o")};
            void Check(bool ok,string name){report.checks++;if(!ok&&report.errors.Count<100)report.errors.Add(name);}
            try {
                var assets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
                Check(assets!=null&&assets.boards.levels.Length==50,"Approved 50-level fixture bindings");
                List<BoardStep> l4=null;var natural=new List<List<BoardStep>>();
                for(int level=0;level<50;level++)foreach(int kind in new[]{-1,4,5,7,11,16,21}) {
                    var board=new BoardModel(JsonUtility.FromJson<LevelData>(assets.boards.levels[level].text));TurnResult turn;
                    if(kind<0){var move=board.LegalSwaps().First();turn=board.Swap(move[0].x,move[0].y,move[1].x,move[1].y);}
                    else {var source=board.Pieces.Values.First(p=>p.family=="gem");board.InjectReviewPower(source.x,source.y,kind);turn=board.Tap(source.x,source.y);}
                    string name="L"+(level+1)+"_"+(kind<0?"match":"power"+kind);report.modelCases++;
                    var row=Inspect(board,turn,name,report,Check,true);report.rows.Add(row);
                    var sequential=BoardPlayback.Build(turn.steps,board.Level,false);
                    if(kind<0){natural.Add(sequential);if(level==3)l4=sequential;}
                }
                Check(report.modelCases==350,"All 350 deterministic baseline commands checked");
                foreach(int recipe in new[]{4,5,21,7,11})foreach(int sourceKind in new[]{4,5,21,7,11,16}) {
                    var level=MixedPowerSwapFixtures.Match(recipe);var board=new BoardModel(level);var from=MixedPowerSwapFixtures.From(recipe);var to=MixedPowerSwapFixtures.To();
                    int rewardId=board.At(from.x,from.y).id;board.InjectReviewPower(to.x,to.y,sourceKind);int sourceId=board.At(to.x,to.y).id;
                    var turn=board.Swap(from.x,from.y,to.x,to.y);var row=Inspect(board,turn,"mixed_"+recipe+"_"+sourceKind,report,Check,false);report.mixedCases++;
                    Check(row.accepted==0,"Mixed power transaction retains sequential presentation fallback "+row.name);
                    Check(turn.steps.Any(s=>s.kind=="power"&&s.removed.Any(r=>r.piece.id==sourceId&&r.cause=="source")),"Original swapped power still executes "+row.name);
                    Check(board.Pieces.Values.Any(p=>p.id==rewardId&&p.family=="power")&&!turn.steps.Any(s=>s.removed.Any(r=>r.piece.id==rewardId)),"Protected reward survives originating wave "+row.name);
                }
                ExistingChains(report,Check);
                Check(l4!=null,"Actual deterministic L4 fixture is available");
                if(l4!=null) {
                    var decisions=new List<LocalCascadeDecision>();var refined=LocalCascadePlayback.Apply(l4,decisions);
                    var renderer=LocalCascadeRendererChecks.Inspect(l4,refined,decisions,Check);foreach(var r in renderer)r.caseName="L4_match_confirmation";
                    LocalCascadeRendererChecks.AssertL4PartialHandoff(renderer,Check);
                    var accepted=decisions.Single(d=>d.accepted);Check(accepted.phaseIndex==1&&accepted.carryIds.SequenceEqual(new[]{64,65,66,67,68,77}),"Actual L4 right-column carried owners are retained");
                    Check(l4[2].damage.Any(h=>h.family=="moss"&&h.x==1&&h.y==1),"Actual red-row adjacency includes the real one-layer moss contact");
                    Guards(l4,report,Check);
                    PriorLandingExpiry(Check);
                    foreach(int fps in new[]{15,30,60})Clock(refined,fps,false,Check);
                    Clock(refined,30,true,Check);
                    Benchmark(l4,natural,report);
                }
                Check(report.rawTurnParity&&report.finalSnapshotParity,"Every raw turn and final model hash is preserved");
            } catch(Exception error){report.errors.Add(error.ToString());}
            report.status=report.errors.Count==0?"PASS_NATIVE_LOCAL_CASCADE73":"FAIL_NATIVE_LOCAL_CASCADE73";
            string folder=Environment.GetEnvironmentVariable("HOTR_LOCAL_CASCADE73_OUTPUT");if(string.IsNullOrEmpty(folder))folder=Path.GetFullPath("../Verification/Evidence/LocalCascade73");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"LocalCascade.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.errors.Count==0?0:1);
        }

        static Row Inspect(BoardModel board,TurnResult turn,string name,Report report,Action<bool,string> check,bool render) {
            check(turn.accepted,name+": accepted command");string raw=JsonUtility.ToJson(turn),final=JsonUtility.ToJson(board.Snapshot());
            var sequential=BoardPlayback.Build(turn.steps,board.Level,false);var row=new Row{name=name,sequentialTurnHash=Hash(JsonUtility.ToJson(turn)),sequentialFinalHash=Hash(JsonUtility.ToJson(board.Snapshot()))};
            string frozen=Json(sequential);var refined=LocalCascadePlayback.Apply(sequential,row.decisions);var built=BoardPlayback.Build(turn.steps,board.Level,true,false);
            check(Json(refined)==Json(built),name+": explicit checkpoint73 control selects the same restricted postpass");
            row.refinedTurnHash=Hash(JsonUtility.ToJson(turn));row.refinedFinalHash=Hash(JsonUtility.ToJson(board.Snapshot()));row.turnHash=Hash(raw);row.finalHash=Hash(final);
            bool rawParity=raw==JsonUtility.ToJson(turn)&&row.sequentialTurnHash==row.refinedTurnHash,finalParity=final==JsonUtility.ToJson(board.Snapshot())&&row.sequentialFinalHash==row.refinedFinalHash;
            report.rawTurnParity&=rawParity;report.finalSnapshotParity&=finalParity;check(rawParity&&finalParity,name+": byte-identical raw turn and final model");check(frozen==Json(sequential),name+": input playback remains immutable");
            check(ReferenceEquals(sequential.Last().after,refined.Last().after),name+": final snapshot identity retained");
            row.sequentialSeconds=sequential.Sum(s=>s.duration);row.refinedSeconds=refined.Sum(s=>s.duration);row.accepted=row.decisions.Count(d=>d.accepted);report.acceptedHandoffs+=row.accepted;
            check(row.accepted<=1,name+": at most one handoff in a turn");check(row.refinedSeconds<=row.sequentialSeconds+.0001f,name+": no longer turn schedule");
            var second=LocalCascadePlayback.Apply(refined);check(Json(refined)==Json(second),name+": repeated Apply is idempotent");
            foreach(var s in refined){check(s.duration>0&&!float.IsNaN(s.duration)&&!float.IsInfinity(s.duration),name+": finite positive phase");check(s.motion.GroupBy(m=>m.id).All(g=>g.Count()==1),name+": one route owner per phase");}
            if(row.accepted==0)check(frozen==Json(refined),name+": unsafe/unqualified fallback is exact");
            if(render&&row.accepted>0){var rows=LocalCascadeRendererChecks.Inspect(sequential,refined,row.decisions,check);foreach(var r in rows)r.caseName=name;report.rendererRows.AddRange(rows);}
            board.Validate();return row;
        }

        static void ExistingChains(Report report,Action<bool,string> check) {
            foreach(int rotation in new[]{0,1,2,3}) {
                var level=MixedPowerSwapFixtures.Match(4,rotation);var board=new BoardModel(level);var from=MixedPowerSwapFixtures.From(4,rotation);var to=MixedPowerSwapFixtures.To(rotation);var other=MixedPowerSwapFixtures.Rotate(6,4,rotation,9,9);
                int reward=board.At(from.x,from.y).id;board.InjectReviewPower(to.x,to.y,(rotation&1)==0?4:5);board.InjectReviewPower(other.x,other.y,21);int chain=board.At(other.x,other.y).id;
                var turn=board.Swap(from.x,from.y,to.x,to.y);var row=Inspect(board,turn,"existing_chain_"+rotation,report,check,false);
                check(row.accepted==0&&turn.steps.Any(s=>s.kind=="power"&&s.removed.Any(r=>r.piece.id==chain&&r.cause=="source")),"Existing Bomb chain remains intact "+rotation);
                check(board.Pieces.Values.Any(p=>p.id==reward&&p.family=="power"),"Existing chain still preserves earned newborn "+rotation);
            }
        }

        static void Guards(List<BoardStep> source,Report report,Action<bool,string> check) {
            void Rejected(string name,Action<BoardStep,BoardStep> mutate) {
                var a=Copy(source[1]);var b=Copy(source[2]);mutate(a,b);string frozen=Json(new List<BoardStep>{a,b});var decisions=new List<LocalCascadeDecision>();var output=LocalCascadePlayback.Apply(new[]{a,b},decisions);report.guardCases++;
                LocalCascadeDecision direct;check(!LocalCascadePlayback.TryDescribe(a,b,out direct),"Direct guard rejects unsafe pair: "+name);
                check(!decisions.Any(d=>d.accepted),"Safe fallback: "+name);check(frozen==Json(output),"Fallback keeps exact source playback: "+name);
            }
            Rejected("original power action",(a,b)=>b.powerPlan=new ReviewPlan());
            Rejected("tool action",(a,b)=>b.booster=new BoosterPlan());
            Rejected("power creation",(a,b)=>b.created=new List<Piece>{new Piece{id=999,family="power",power=4}});
            Rejected("delivery collection",(a,b)=>b.collections=new List<GoalCollection>{new GoalCollection{family="pail",arrival=.1f}});
            Rejected("advanced/shared obstacle",(a,b)=>b.damage=new List<Damage>{new Damage{id=1,family="cabinet",beforeHP=1,afterHP=0}});
            Rejected("partial obstacle hit",(a,b)=>b.damage=new List<Damage>{new Damage{id=1,family="moss",beforeHP=2,afterHP=1}});
            Rejected("destination shorter than carry",(a,b)=>b.duration=.1f);
            Rejected("carry landing cannot finish",(a,b)=>b.duration=.25f);
            Rejected("intersecting next path column",(a,b)=>{b.motion=new List<Motion>(b.motion);var m=b.motion[0];b.motion[0]=new Motion{id=m.id,fromX=7,fromY=m.fromY,toX=m.toX,toY=m.toY,delay=m.delay,seconds=m.seconds,landing=m.landing,spawned=m.spawned,clipSpawn=m.clipSpawn,spawnTop=m.spawnTop,path=m.path};});
            Rejected("previous diagonal flow",(a,b)=>{a.motion=a.motion.Select(m=>new Motion{id=m.id,fromX=m.fromX,fromY=m.fromY,toX=m.toX,toY=m.toY,delay=m.delay,seconds=m.seconds,landing=m.landing,spawned=m.spawned,clipSpawn=m.clipSpawn,spawnTop=m.spawnTop,path=m.path}).ToList();a.motion[0].fromX-=1;});
            Rejected("carry body HP changes",(a,b)=>{b.after=SnapshotCopy(b.after);b.after.pieces.Single(p=>p.id==64).hp++;});
            Rejected("old obstacle body not clear",(a,b)=>a.removed=a.removed.Select(r=>new Removed{piece=r.piece,time=r.cause=="obstacle"?.7f:r.time,cause=r.cause}).ToList());
            Rejected("prior squash would be cut by next motion",(a,b)=>{b.motion=b.motion.Select(m=>new Motion{id=m.id,fromX=m.fromX,fromY=m.fromY,toX=m.toX,toY=m.toY,delay=m.id==74?0:m.delay,seconds=m.seconds,landing=m.landing,spawned=m.spawned,clipSpawn=m.clipSpawn,spawnTop=m.spawnTop,path=m.path}).ToList();});
            var decisions2=new List<LocalCascadeDecision>();LocalCascadePlayback.Apply(source.Concat(source),decisions2);report.guardCases++;check(decisions2.Count(d=>d.accepted)==1&&decisions2.Any(d=>d.reason=="second_overlap_disabled"),"Second overlap is disabled across the whole turn");
        }

        static void PriorLandingExpiry(Action<bool,string> check) {
            float contact=TileFall.Duration(1);var p=new Piece{id=1,x=0,y=0,family="gem",color=0};
            var at=new BoardSnapshot{pieces=new[]{p},goals=new Goal[0],status="Playing"};var below=SnapshotCopy(at);below.pieces[0].y=-1;
            var first=new BoardStep{kind="gravity",before=at,after=at,duration=contact};first.motion.Add(new Motion{id=1,fromX=0,fromY=1,toX=0,toY=0,seconds=contact,landing=.1f});
            var next=new BoardStep{kind="gravity",before=at,after=below,duration=.2f+contact};next.motion.Add(new Motion{id=1,fromX=0,fromY=0,toX=0,toY=-1,delay=.2f,seconds=contact,landing=.1f});
            var original=new BoardPresentation();original.Add(first,0);var held=new BoardPresentation();held.Add(first,0);held.Add(next,contact);
            foreach(float age in new[]{0f,.001f,.016f,.033f,.065f,.099f}) {
                var old=original.Sample(first,at,contact+age,0).Single(d=>d.pieceId==1);var pose=held.Sample(next,at,contact+age,contact).Single(d=>d.pieceId==1);
                check(Math.Abs(old.y-pose.y)<.0001f&&Math.Abs(old.sx-pose.sx)<.0001f&&Math.Abs(old.sy-pose.sy)<.0001f,"Previous landing retains exact original pose and expiry "+age);
            }
            held.PruneHistory(contact+.101f);var expired=held.Sample(next,at,contact+.101f,contact).Single(d=>d.pieceId==1);
            check(expired.y==0&&expired.sx==1&&expired.sy==1,"Previous landing expires before the future motion without restarting");
            var standalone=new BoardPresentation();standalone.Add(next,contact);
            foreach(float age in new[]{.1999f,.2f,.2001f,.216f,.25f,.34f,.4f}) {
                var expected=standalone.Sample(next,at,contact+age,contact).Single(d=>d.pieceId==1);var pose=held.Sample(next,at,contact+age,contact).Single(d=>d.pieceId==1);
                check(Math.Abs(expected.y-pose.y)<.0001f&&Math.Abs(expected.sx-pose.sx)<.0001f&&Math.Abs(expected.sy-pose.sy)<.0001f,"Future flight/landing owns the body continuously "+age);
            }
        }

        static void Clock(List<BoardStep> steps,int fps,bool stall,Action<bool,string> check) {
            var view=new BoardPresentation();float clock=0,start=0,wall=0;int index=0,frames=0;view.Add(steps[0],0);
            while(index<steps.Count&&frames++<10000) {
                var current=steps[index];var before=view.Sample(current,current.before,clock,start);var paused=view.Sample(current,current.before,clock,start);
                check(JsonUtility.ToJson(new Draws{draws=before})==JsonUtility.ToJson(new Draws{draws=paused}),"Paused sampler holds its exact pose "+fps+"/"+frames);
                float advance=stall&&frames==12?.20f:1f/fps;wall+=advance;
                while(index<steps.Count&&advance>0) {
                    current=steps[index];advance=BoardPlayback.VisibleAdvance(current,advance,clock-start);float remaining=current.duration-(clock-start);
                    if(advance<remaining){clock+=advance;advance=0;}else {clock+=remaining;advance-=remaining;index++;start=clock;if(index<steps.Count)view.Add(steps[index],start);}
                }
                if(index<steps.Count){var draws=view.Sample(steps[index],steps[index].before,clock,start);check(draws.Where(d=>d.pieceId>0).GroupBy(d=>d.pieceId).All(g=>g.Count()==1),"Clock has no duplicate rendered body "+fps+"/"+frames);}
            }
            check(index==steps.Count&&frames<10000,"Frame clock reaches settlement "+fps+" stall="+stall);
            if(!stall)check(wall<=steps.Sum(s=>s.duration)+.2f,"Normal cadence does not add a new timing barrier "+fps);
        }
        [Serializable] sealed class Draws {public List<DrawSprite> draws;}
        static void Benchmark(List<BoardStep> l4,List<List<BoardStep>> natural,Report report) {
            void Measure(string name,Action work,int count) {
                for(int i=0;i<10;i++)work();var times=new List<double>();int gc=GC.CollectionCount(0);
                for(int i=0;i<count;i++){long start=Stopwatch.GetTimestamp();work();times.Add((Stopwatch.GetTimestamp()-start)*1000.0/Stopwatch.Frequency);}
                times.Sort();report.plannerTimings.Add(new Timing{name=name,iterations=count,gen0Collections=GC.CollectionCount(0)-gc,medianMs=times[times.Count/2],p95Ms=times[(int)((times.Count-1)*.95)],maxMs=times[times.Count-1]});
            }
            Measure("L4_restricted_postpass",()=>LocalCascadePlayback.Apply(l4),150);int fixture=0;
            Measure("rotating_50_natural_postpasses",()=>{LocalCascadePlayback.Apply(natural[fixture++%natural.Count]);},150);
        }
    }
}
#endif

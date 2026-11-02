#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using Motion=HeartOfTheRain.M46.Motion;
using Checkpoint75=HeartOfTheRain.Verification.Checkpoint75Control;

namespace HeartOfTheRain.Verification {
    public static class LocalContinuationVerification {
        const float Epsilon=.00015f;
        [Serializable] public sealed class Row {
            public string name,sequentialTurnHash,refinedTurnHash,sequentialFinalHash,refinedFinalHash;
            public float sequentialSeconds,checkpoint73Seconds,checkpoint74Seconds,refinedSeconds;
            public int accepted,checkpoint74Accepted;
            public List<LocalContinuationDecision> decisions=new List<LocalContinuationDecision>();
        }
        [Serializable] public sealed class RendererRow {
            public string caseName;
            public int phaseIndex,continuedCount,carryCount,poseSamples,routeSamples,collisionSamples;
            public float handoff,lastParticipatingContact,residualLocalWait,successorExtension,secondsSavedVsSequential,secondsSavedVs73,secondsSavedVs74,maxBoundaryPositionJump,maxBoundaryScaleJump,minimumColumnClearance=1000;
            public bool terminalIdleLanding;public int landingTailsBeyondSuccessor,priorEffectSamples;
        }
        [Serializable] public sealed class Report {
            public string status,utc,unity,scope="Native Unity Editor model hashes, actual BoardPresentation body samples and feedback/clock tests. This entry does not claim connected Play Mode or Android verification.";
            public int checks,modelCases,mixedCases,existingChainCases,guardCases,acceptedHandoffs,qualifyingTurns,newQualifyingTurns,terminalHandoffs,seededCases,seededAcceptedHandoffs,checkpoint74Comparisons;
            public bool rawTurnParity=true,finalSnapshotParity=true;
            public List<string> errors=new List<string>();
            public List<Row> rows=new List<Row>();
            public List<Row> seededRows=new List<Row>();
            public List<RendererRow> rendererRows=new List<RendererRow>();
            public int checkpoint75Comparisons,checkpoint75GuardComparisons,checkpoint75PublicDecisionComparisons;
            public bool checkpoint75QueueParity=true,checkpoint75DecisionParity=true,compiledCheckpoint75SourceMatchesArchive;
            public string checkpoint75SourceSHA256;
            public List<PlannerTiming> checkpoint75PlannerTimings=new List<PlannerTiming>();
        }
        [Serializable] public sealed class PlannerTiming {public string name,scope="Alternating warmed native Apply only; same prepared input, separate from full Build and Android command/frame spans.";public int iterations;public double legacyMedianMs,currentMedianMs;public List<double> legacyMs=new List<double>(),currentMs=new List<double>();}
        [Serializable] sealed class Steps {public List<BoardStep> steps;}
        [Serializable] sealed class Draws {public List<DrawSprite> draws;}
        static readonly Dictionary<string,DebrisProfile> Profiles=new Dictionary<string,DebrisProfile>();
        static BoardPresentation View() {var view=new BoardPresentation();foreach(var p in Profiles)view.profiles.Add(p.Key,p.Value);view.PrepareDebrisGeometry();return view;}
        static string Json(List<BoardStep> steps)=>JsonUtility.ToJson(new Steps{steps=steps});
        static string Hash(string text){using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(text))).Replace("-","").ToLowerInvariant();}
        static float Contact(Motion m)=>m.delay+m.seconds;
        static bool Near(float a,float b)=>Math.Abs(a-b)<Epsilon;
        static bool Pose(DrawSprite a,DrawSprite b)=>a.bank==b.bank&&a.key==b.key&&a.atlas==b.atlas&&Near(a.x,b.x)&&Near(a.y,b.y)&&Near(a.sx,b.sx)&&Near(a.sy,b.sy)&&Near(a.angle,b.angle)&&Near(a.alpha,b.alpha);
        static BoardStep Copy(BoardStep s)=>new BoardStep{kind=s.kind,label=s.label,duration=s.duration,triggerTime=s.triggerTime,triggerOriginId=s.triggerOriginId,before=s.before,after=s.after,powerPlan=s.powerPlan,booster=s.booster,playbackTracks=s.playbackTracks,damage=s.damage,removed=s.removed,motion=s.motion,created=s.created,collections=s.collections};
        static Motion Shift(Motion m,float offset)=>new Motion{id=m.id,fromX=m.fromX,fromY=m.fromY,toX=m.toX,toY=m.toY,delay=m.delay+offset,seconds=m.seconds,landing=m.landing,spawned=m.spawned,clipSpawn=m.clipSpawn,spawnTop=m.spawnTop,path=m.path==null?null:m.path.Select(l=>new FallLeg{fromX=l.fromX,fromY=l.fromY,toX=l.toX,toY=l.toY,delay=l.delay+offset,seconds=l.seconds,distance=l.distance}).ToList()};
        static BoardSnapshot SnapshotCopy(BoardSnapshot s)=>new BoardSnapshot{pieces=s.pieces.Select(p=>p.Copy()).ToArray(),goals=s.goals.Select(g=>new Goal{family=g.family,count=g.count}).ToArray(),moves=s.moves,turn=s.turn,status=s.status};

        // Compatibility entrypoint; these are native Editor tests, with the
        // report scope stated explicitly rather than labelling them Play Mode.
        public static void RunPlayMode()=>Run();
        public static void Run() {
            var report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};
            bool priorControl=LocalCascadeContinuation.VerificationUseCheckpoint74,prior75Control=Checkpoint75.LocalCascadeContinuation.VerificationUseCheckpoint74;LocalCascadeContinuation.VerificationUseCheckpoint74=false;Checkpoint75.LocalCascadeContinuation.VerificationUseCheckpoint74=false;
            void Check(bool ok,string name){report.checks++;if(!ok&&report.errors.Count<150)report.errors.Add(name);}
            try {
                string archived75=File.ReadAllText(Path.GetFullPath("../.verification-cache/Gameplay76/BaselineSources/Unity/Assets/HeartOfTheRain/M46/Runtime/LocalCascadeContinuation.cs"));
                string compiled75=File.ReadAllText("Assets/HeartOfTheRain/Verification/Smoothness75Control.cs"),begin75="// BEGIN EXACT75 LocalCascadeContinuation.cs",end75="// END EXACT75 LocalCascadeContinuation.cs";
                compiled75=compiled75.Substring(compiled75.IndexOf(begin75,StringComparison.Ordinal)+begin75.Length);compiled75=compiled75.Substring(0,compiled75.IndexOf(end75,StringComparison.Ordinal)).Trim();
                string expected75=archived75.Substring(archived75.IndexOf("namespace HeartOfTheRain.M46",StringComparison.Ordinal)).Replace("namespace HeartOfTheRain.M46","namespace HeartOfTheRain.Verification.Checkpoint75Control").Trim();
                report.checkpoint75SourceSHA256=Hash(archived75);report.compiledCheckpoint75SourceMatchesArchive=compiled75.Replace("\r\n","\n")==expected75.Replace("\r\n","\n");Check(report.compiledCheckpoint75SourceMatchesArchive,"Independent compiled75 continuation control is exact archived source except namespace/imports");
                var assets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
                Check(assets!=null&&assets.boards.levels.Length==50,"Approved 50-level fixture bindings");
                Profiles.Clear();foreach(var entry in assets.boards.debrisProfiles){var profile=JsonUtility.FromJson<DebrisProfile>(entry.metadata.text);foreach(var p in profile.pieces){if(p.scaleMultiplier<=0)p.scaleMultiplier=1;if(p.spinMultiplier<=0)p.spinMultiplier=1;}Profiles.Add(entry.family,profile);}
                string baselineFolder=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY75_BASELINE");if(string.IsNullOrEmpty(baselineFolder))baselineFolder=Path.GetFullPath("../Verification/Evidence/Gameplay74");
                var baseline=JsonUtility.FromJson<Report>(File.ReadAllText(Path.Combine(baselineFolder,"Native","LocalContinuation.json")));
                Check(baseline.status=="PASS_NATIVE_LOCAL_CONTINUATION74"&&baseline.modelCases==350,"Actual archived checkpoint74 native corpus is available");var priorRows=baseline.rows.ToDictionary(r=>r.name);
                List<BoardStep> l4=null,l14=null;
                for(int level=0;level<50;level++)foreach(int kind in new[]{-1,4,5,7,11,16,21}) {
                    var board=new BoardModel(JsonUtility.FromJson<LevelData>(assets.boards.levels[level].text));TurnResult turn;
                    if(kind<0){var move=board.LegalSwaps().First();turn=board.Swap(move[0].x,move[0].y,move[1].x,move[1].y);}
                    else {var source=board.Pieces.Values.First(p=>p.family=="gem");board.InjectReviewPower(source.x,source.y,kind);turn=board.Tap(source.x,source.y);}
                    string name="L"+(level+1)+"_"+(kind<0?"match":"power"+kind);report.modelCases++;
                    var row=Inspect(board,turn,name,report,Check,kind<0);report.rows.Add(row);
                    var prior=priorRows[name];Check(row.sequentialTurnHash==prior.sequentialTurnHash&&row.sequentialFinalHash==prior.sequentialFinalHash,name+": exact archived74 raw/final corpus hashes");
                    Check(Near(row.checkpoint74Seconds,prior.refinedSeconds)&&row.checkpoint74Accepted==prior.accepted,name+": preserved74 planner matches archived native duration/qualification");report.checkpoint74Comparisons++;
                    if(level==3&&kind<0)l4=BoardPlayback.Build(turn.steps,board.Level,false,false);
                    if(level==13&&kind<0)l14=BoardPlayback.Build(turn.steps,board.Level,false,false);
                }
                Check(report.modelCases==350,"All350 deterministic baseline commands checked");
                report.qualifyingTurns=report.rows.Count(r=>r.accepted>0);report.newQualifyingTurns=report.rows.Count(r=>r.accepted>0&&r.checkpoint74Accepted==0);report.terminalHandoffs=report.rows.Sum(r=>r.decisions.Count(d=>d.accepted&&d.terminalIdleLanding));
                Check(report.qualifyingTurns==4&&report.newQualifyingTurns==3&&report.terminalHandoffs==3,"Actual authored coverage expands from one to four turns with three guarded terminal continuations");
                Check(report.rows.Where(r=>r.accepted>0).Select(r=>r.name).SequenceEqual(new[]{"L4_match","L14_match","L31_match","L33_match"}),"Exact added authored fixtures qualify without power/advanced expansion");
                foreach(var fixture in new[]{new[]{6,8},new[]{14,12},new[]{31,4},new[]{33,1}}) {
                    var board=new BoardModel(JsonUtility.FromJson<LevelData>(assets.boards.levels[fixture[0]-1].text),(uint)fixture[1]);var move=board.LegalSwaps().First();var turn=board.Swap(move[0].x,move[0].y,move[1].x,move[1].y);
                    var row=Inspect(board,turn,"seed_L"+fixture[0]+"_"+fixture[1],report,Check,true,false);report.seededRows.Add(row);report.seededCases++;report.seededAcceptedHandoffs+=row.accepted;
                    Check(row.accepted==1&&row.checkpoint74Accepted==0&&row.refinedSeconds<row.checkpoint74Seconds-.01f,"Additional seeded native terminal fixture qualifies "+row.name);
                }
                foreach(int recipe in new[]{4,5,21,7,11})foreach(int sourceKind in new[]{4,5,21,7,11,16}) {
                    var board=new BoardModel(MixedPowerSwapFixtures.Match(recipe));var from=MixedPowerSwapFixtures.From(recipe);var to=MixedPowerSwapFixtures.To();
                    int reward=board.At(from.x,from.y).id;board.InjectReviewPower(to.x,to.y,sourceKind);int source=board.At(to.x,to.y).id;
                    var turn=board.Swap(from.x,from.y,to.x,to.y);var row=Inspect(board,turn,"mixed_"+recipe+"_"+sourceKind,report,Check,false);report.mixedCases++;
                    Check(row.accepted==0,"Mixed power presentation uses the conservative fallback "+row.name);
                    Check(turn.steps.Any(s=>s.kind=="power"&&s.removed.Any(r=>r.piece.id==source&&r.cause=="source")),"Swapped source executes "+row.name);
                    Check(board.Pieces.Values.Any(p=>p.id==reward&&p.family=="power")&&!turn.steps.Any(s=>s.removed.Any(r=>r.piece.id==reward)),"Earned newborn remains protected "+row.name);
                }
                foreach(int rotation in new[]{0,1,2,3}) {
                    var board=new BoardModel(MixedPowerSwapFixtures.Match(4,rotation));var from=MixedPowerSwapFixtures.From(4,rotation);var to=MixedPowerSwapFixtures.To(rotation);var at=MixedPowerSwapFixtures.Rotate(6,4,rotation,9,9);
                    int reward=board.At(from.x,from.y).id;board.InjectReviewPower(to.x,to.y,(rotation&1)==0?4:5);board.InjectReviewPower(at.x,at.y,21);int chained=board.At(at.x,at.y).id;
                    var turn=board.Swap(from.x,from.y,to.x,to.y);var row=Inspect(board,turn,"existing_chain_"+rotation,report,Check,false);report.existingChainCases++;
                    Check(row.accepted==0&&turn.steps.Any(s=>s.kind=="power"&&s.removed.Any(r=>r.piece.id==chained&&r.cause=="source")),"Pre-existing Bomb chain preserved "+rotation);
                    Check(board.Pieces.Values.Any(p=>p.id==reward&&p.family=="power"),"Existing chain preserves protected newborn "+rotation);
                }
                Check(l4!=null,"Exact L4 red-row+moss fixture available");
                if(l4!=null) {
                    var decisions=new List<LocalContinuationDecision>();var refined=LocalCascadeContinuation.Apply(l4,decisions);var d=decisions.Single(x=>x.accepted);
                    var row=InspectRenderer(l4,refined,d,"L4_confirmation",Check);report.rendererRows.Add(row);
                    Check(d.phaseIndex==1&&Near(d.handoff,.29f)&&Near(d.matchReady,.26642137f),"L4 handoff waits red contact and original crate clear");
                    Check(d.continuedIds.SequenceEqual(new[]{22,23,24,25,26,27,74}),"Exact seven unfinished col4 owners continue");
                    Check(d.columnPads.Count==1&&d.columnPads[0].column==4&&Near(d.columnPads[0].padding,.02142137f),"L4 whole-column padding is21.421ms");
                    Check(Near(row.residualLocalWait,.02357863f)&&Near(row.secondsSavedVs73,.22142137f),"L4 scheduled residual23.579ms and additional saving221.421ms are reported separately from device timing");
                    Check(l4[2].damage.Any(h=>h.family=="moss"&&h.x==1&&h.y==1),"Actual moss-side-feed interaction remains in the qualifying fixture");
                    Guards(l4,report,Check);BoundaryFeedback(l4,Check);LandingAtHandoff(l4,report,Check);
                    foreach(int fps in new[]{15,30,60})Clock(refined,fps,false,Check);Clock(refined,30,true,Check);
                }
                if(l14!=null)TerminalGuards(l14,report,Check);
                Check(report.rawTurnParity&&report.finalSnapshotParity,"All raw turn/final snapshot hashes retain exact parity");
                Check(report.checkpoint75Comparisons==388&&report.checkpoint75GuardComparisons==43,"Independent75 parity covers350 authored, four seeded,30 mixed, four existing chains and43 guard inputs");
            }catch(Exception error){report.errors.Add(error.ToString());}finally{LocalCascadeContinuation.VerificationUseCheckpoint74=priorControl;Checkpoint75.LocalCascadeContinuation.VerificationUseCheckpoint74=prior75Control;}
            report.status=report.errors.Count==0?"PASS_NATIVE_LOCAL_CONTINUATION75":"FAIL_NATIVE_LOCAL_CONTINUATION75";
            string folder=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY75_OUTPUT");if(string.IsNullOrEmpty(folder))folder=Path.GetFullPath("../Verification/Evidence/Gameplay75");folder=Path.Combine(folder,"Native");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"LocalContinuation.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.errors.Count==0?0:1);
        }

        static Row Inspect(BoardModel board,TurnResult turn,string name,Report report,Action<bool,string> check,bool render,bool corpus=true) {
            check(turn.accepted,name+": model command accepted");string raw=JsonUtility.ToJson(turn),final=JsonUtility.ToJson(board.Snapshot());
            var sequential=BoardPlayback.Build(turn.steps,board.Level,false,false);var row=new Row{name=name,sequentialTurnHash=Hash(raw),sequentialFinalHash=Hash(final)};string frozen=Json(sequential);
            var control=LocalCascadePlayback.Apply(sequential);var checkpoint74Decisions=new List<LocalContinuationDecision>();var checkpoint74=LocalCascadeContinuation.ApplyCheckpoint74(sequential,checkpoint74Decisions);var refined=LocalCascadeContinuation.Apply(sequential,row.decisions);var live=BoardPlayback.Build(turn.steps,board.Level);
            CompareCheckpoint75(sequential,name,report,check,false);
            if(corpus&&(name=="L4_match"||name=="L14_match"||name=="L31_match"||name=="L33_match"))BenchmarkCheckpoint75(sequential,name,report);
            check(Json(refined)==Json(live)&&refined.SelectMany(s=>s.motion).Where(LocalCascadeContinuation.IsContinuation).Select(m=>m.id).SequenceEqual(live.SelectMany(s=>s.motion).Where(LocalCascadeContinuation.IsContinuation).Select(m=>m.id)),name+": live default Build preserves actual continuation metadata");
            check(Json(control)==Json(BoardPlayback.Build(turn.steps,board.Level,true,false)),name+": explicit checkpoint73 control remains available");
            try{LocalCascadeContinuation.VerificationUseCheckpoint74=true;var selected=BoardPlayback.Build(turn.steps,board.Level);check(Json(selected)==Json(checkpoint74)&&selected.SelectMany(s=>s.motion).Where(LocalCascadeContinuation.IsContinuation).Select(m=>m.id).SequenceEqual(checkpoint74.SelectMany(s=>s.motion).Where(LocalCascadeContinuation.IsContinuation).Select(m=>m.id)),name+": opt-in real Build selects exact74 control");}finally{LocalCascadeContinuation.VerificationUseCheckpoint74=false;}
            row.refinedTurnHash=Hash(JsonUtility.ToJson(turn));row.refinedFinalHash=Hash(JsonUtility.ToJson(board.Snapshot()));bool rawParity=row.sequentialTurnHash==row.refinedTurnHash&&raw==JsonUtility.ToJson(turn),finalParity=row.sequentialFinalHash==row.refinedFinalHash&&final==JsonUtility.ToJson(board.Snapshot());
            report.rawTurnParity&=rawParity;report.finalSnapshotParity&=finalParity;check(rawParity&&finalParity,name+": raw turn/final snapshot byte parity");check(frozen==Json(sequential),name+": planner input remains immutable");
            row.sequentialSeconds=sequential.Sum(s=>s.duration);row.checkpoint73Seconds=control.Sum(s=>s.duration);row.checkpoint74Seconds=checkpoint74.Sum(s=>s.duration);row.checkpoint74Accepted=checkpoint74Decisions.Count(d=>d.accepted);row.refinedSeconds=refined.Sum(s=>s.duration);row.accepted=row.decisions.Count(d=>d.accepted);if(corpus)report.acceptedHandoffs+=row.accepted;
            check(row.accepted<=1,name+": no nested/second overlap");check(row.refinedSeconds<=row.sequentialSeconds+Epsilon,name+": schedule never grows");
            check(row.refinedSeconds<=row.checkpoint74Seconds+Epsilon,name+": schedule never exceeds preserved74 control");
            var second=LocalCascadeContinuation.Apply(refined);check(Json(second)==Json(refined)&&second.SelectMany(s=>s.motion).Where(LocalCascadeContinuation.IsContinuation).All(m=>refined.Any(s=>s.motion.Contains(m))),name+": repeated planning is idempotent without losing subtype ownership");
            if(row.accepted==0)check(Json(checkpoint74)==Json(refined),name+": rejected75 uses exact74 fallback");
            for(int i=0;i<refined.Count;i++) {
                check(ReferenceEquals(refined[i].before,sequential[i].before)&&ReferenceEquals(refined[i].after,sequential[i].after),name+": snapshot identity preserved "+i);
                check(ReferenceEquals(refined[i].damage,sequential[i].damage)&&ReferenceEquals(refined[i].removed,sequential[i].removed)&&ReferenceEquals(refined[i].created,sequential[i].created)&&ReferenceEquals(refined[i].collections,sequential[i].collections),name+": mutation/event ownership retained "+i);
                check(refined[i].motion.GroupBy(m=>m.id).All(g=>g.Count()==1),name+": unique phase body owner "+i);
            }
            if(render&&row.accepted>0)report.rendererRows.Add(InspectRenderer(sequential,refined,row.decisions.Single(d=>d.accepted),name,check));
            board.Validate();return row;
        }

        static string Queue75(List<BoardStep> steps,bool legacy) {
            var text=new StringBuilder();
            void Number(float n){text.Append(n.ToString("R",System.Globalization.CultureInfo.InvariantCulture)).Append(';');}
            void MotionData(Motion m,int depth) {
                if(depth>32)throw new InvalidOperationException("Unexpected cyclic continuation");
                text.Append(JsonUtility.ToJson(m));bool continued=legacy?Checkpoint75.LocalCascadeContinuation.IsContinuation(m):LocalCascadeContinuation.IsContinuation(m);text.Append("continued:").Append(continued);
                if(continued) {
                    var flags=System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic;var type=m.GetType();
                    Number((float)type.GetField("handoff",flags).GetValue(m));
                    MotionData((Motion)type.GetField("previous",flags).GetValue(m),depth+1);MotionData((Motion)type.GetField("following",flags).GetValue(m),depth+1);
                }
                foreach(float at in new[]{-1f,0f,m.delay,m.delay+m.seconds,m.delay+m.seconds+m.landing+1f}) {
                    float age;var segment=legacy?Checkpoint75.LocalCascadeContinuation.Segment(m,at,out age):LocalCascadeContinuation.Segment(m,at,out age);Number(age);text.Append(JsonUtility.ToJson(segment));
                    float x,y;if(legacy)Checkpoint75.TileFall.Position(m,at,out x,out y);else TileFall.Position(m,at,out x,out y);Number(x);Number(y);text.Append(legacy?Checkpoint75.TileFall.Moving(m,at):TileFall.Moving(m,at));
                }
                foreach(float contact in legacy?Checkpoint75.LocalCascadeContinuation.LandingContacts(m):LocalCascadeContinuation.LandingContacts(m))Number(contact);
            }
            void Step(BoardStep s,int depth) {
                if(depth>32)throw new InvalidOperationException("Unexpected cyclic playback track");
                text.Append(JsonUtility.ToJson(s)).Append("tracks:").Append(s.playbackTracks==null?-1:s.playbackTracks.Count);
                if(s.playbackTracks!=null)foreach(var track in s.playbackTracks){Number(track.start);Number(track.leadIn);Step(track.step,depth+1);}
                foreach(var m in s.motion)MotionData(m,0);
            }
            foreach(var s in steps)Step(s,0);return text.ToString();
        }

        static void CompareCheckpoint75(List<BoardStep> source,string name,Report report,Action<bool,string> check,bool guard) {
            string frozen=Json(source);var oldDecisions=new List<Checkpoint75.LocalContinuationDecision>();var currentDecisions=new List<LocalContinuationDecision>();
            var old=Checkpoint75.LocalCascadeContinuation.Apply(source,oldDecisions);var current=LocalCascadeContinuation.Apply(source,currentDecisions);
            bool queue=Queue75(old,true)==Queue75(current,false),decisions=string.Join("|",oldDecisions.Select(d=>JsonUtility.ToJson(d)))==string.Join("|",currentDecisions.Select(d=>JsonUtility.ToJson(d)));
            report.checkpoint75QueueParity&=queue;report.checkpoint75DecisionParity&=decisions;
            check(queue,name+": exact independently compiled75 serialized/recursive-track/composite/route/pose queue");check(decisions,name+": exact75 strict/terminal priority and complete decision records");
            check(frozen==Json(source),name+": both independent planners retain original input");
            for(int i=0;i+1<source.Count;i++) {
                Checkpoint75.LocalContinuationDecision a;LocalContinuationDecision b;
                bool oa=Checkpoint75.LocalCascadeContinuation.TryDescribe(source[i],source[i+1],out a),ob=LocalCascadeContinuation.TryDescribe(source[i],source[i+1],out b);
                check(oa==ob&&JsonUtility.ToJson(a)==JsonUtility.ToJson(b),name+": public strict result/reason/pads unchanged "+i);report.checkpoint75PublicDecisionComparisons++;
                if(i+2<source.Count) {
                    oa=Checkpoint75.LocalCascadeContinuation.TryDescribeTerminal(source[i],source[i+1],source[i+2],out a);ob=LocalCascadeContinuation.TryDescribeTerminal(source[i],source[i+1],source[i+2],out b);
                    check(oa==ob&&JsonUtility.ToJson(a)==JsonUtility.ToJson(b),name+": public terminal result/reason/pads unchanged "+i);report.checkpoint75PublicDecisionComparisons++;
                }
            }
            if(guard)report.checkpoint75GuardComparisons++;else report.checkpoint75Comparisons++;
        }

        static void BenchmarkCheckpoint75(List<BoardStep> source,string name,Report report) {
            var row=new PlannerTiming{name=name,iterations=24};
            List<BoardStep> Build(bool old)=>old?Checkpoint75.LocalCascadeContinuation.Apply(source):LocalCascadeContinuation.Apply(source);
            for(int i=0;i<8;i++){Build(true);Build(false);}
            double Measure(bool old) {List<BoardStep> last=null;long start=System.Diagnostics.Stopwatch.GetTimestamp();for(int n=0;n<8;n++)last=Build(old);double elapsed=(System.Diagnostics.Stopwatch.GetTimestamp()-start)*1000.0/System.Diagnostics.Stopwatch.Frequency/8;GC.KeepAlive(last);return elapsed;}
            for(int i=0;i<row.iterations;i++)if(i%2==0){row.legacyMs.Add(Measure(true));row.currentMs.Add(Measure(false));}else{row.currentMs.Add(Measure(false));row.legacyMs.Add(Measure(true));}
            row.legacyMedianMs=row.legacyMs.OrderBy(n=>n).ElementAt(row.iterations/2);row.currentMedianMs=row.currentMs.OrderBy(n=>n).ElementAt(row.iterations/2);report.checkpoint75PlannerTimings.Add(row);
        }

        static Dictionary<int,DrawSprite> Bodies(List<DrawSprite> draws,Action<bool,string> check,string label) {
            var groups=draws.Where(d=>d.pieceId>0).GroupBy(d=>d.pieceId).ToArray();check(groups.All(g=>g.Count()==1),label+": unique rendered body per ID");return groups.ToDictionary(g=>g.Key,g=>g.First());
        }
        static bool Goals(BoardPresentation a,BoardStep sa,float ta,float starta,BoardPresentation b,BoardStep sb,float tb,float startb) {
            var ga=a.DisplayGoalsLive(sa,sa.before,ta-starta,ta).Select(g=>new Goal{family=g.family,count=g.count}).ToArray();var gb=b.DisplayGoalsLive(sb,sb.before,tb-startb,tb);return ga.Length==gb.Length&&ga.All(g=>gb.Any(h=>h.family==g.family&&h.count==g.count));
        }
        static RendererRow InspectRenderer(List<BoardStep> source,List<BoardStep> refined,LocalContinuationDecision d,string name,Action<bool,string> check) {
            int k=d.phaseIndex;var old=source[k];var originalNext=source[k+1];var previous=refined[k];var next=refined[k+1];float t0=d.handoff;
            var row=new RendererRow{caseName=name,phaseIndex=k,handoff=t0,lastParticipatingContact=d.matchReady,residualLocalWait=t0-d.matchReady,successorExtension=next.duration-originalNext.duration,terminalIdleLanding=d.terminalIdleLanding,secondsSavedVsSequential=source.Sum(s=>s.duration)-refined.Sum(s=>s.duration),secondsSavedVs73=LocalCascadePlayback.Apply(source).Sum(s=>s.duration)-refined.Sum(s=>s.duration),secondsSavedVs74=LocalCascadeContinuation.ApplyCheckpoint74(source).Sum(s=>s.duration)-refined.Sum(s=>s.duration),continuedCount=d.continuedIds.Length,carryCount=d.carryIds.Length};
            var pads=d.columnPads.ToDictionary(p=>p.column,p=>p.padding);var retimed=Copy(originalNext);retimed.duration=next.duration;retimed.motion=originalNext.motion.Select(m=>Shift(m,pads.TryGetValue((int)m.fromX,out float pad)?pad:0)).ToList();
            var expectedOld=View();var expectedNext=View();var actual=View();float prefix=-source.Take(k).Sum(s=>s.duration);
            for(int i=0;i<k;i++){expectedOld.Add(source[i],prefix);expectedNext.Add(source[i],prefix);actual.Add(refined[i],prefix);prefix+=source[i].duration;}
            expectedOld.Add(old,0);expectedNext.Add(retimed,t0);actual.Add(previous,0);actual.Add(next,t0);bool addedSettled=false;
            var oldBoundary=Bodies(expectedOld.Sample(old,old.before,t0,0),check,name+" old boundary");var newBoundary=Bodies(actual.Sample(next,next.before,t0,t0),check,name+" new boundary");
            foreach(var p in oldBoundary.Values)if(newBoundary.TryGetValue(p.pieceId,out var q)) {
                row.maxBoundaryPositionJump=Math.Max(row.maxBoundaryPositionJump,Math.Abs(p.x-q.x)+Math.Abs(p.y-q.y));row.maxBoundaryScaleJump=Math.Max(row.maxBoundaryScaleJump,Math.Abs(p.sx-q.sx)+Math.Abs(p.sy-q.sy));
                check(Pose(p,q),name+": exact all-body boundary pose "+p.pieceId);
            }
            check(oldBoundary.Keys.OrderBy(id=>id).SequenceEqual(newBoundary.Keys.OrderBy(id=>id)),name+": all visible body identities retained at handoff");
            check(Goals(expectedOld,old,t0,0,actual,next,t0,t0),name+": prior obstacle counter is complete with no boundary jump");
            check(FeedbackPlan.Build(old).Where(c=>c.time>t0+Epsilon).All(c=>c.id=="tile_land"),name+": no old pending nonlanding feedback is discarded");
            var feedback=FeedbackPlan.Build(next);
            foreach(var m in next.motion)foreach(float contact in LocalCascadeContinuation.LandingContacts(m))check(feedback.Any(c=>c.id=="tile_land"&&Math.Abs(c.time-contact)<.0601f),name+": feedback owns each future old/new landing once "+m.id+"/"+contact);
            foreach(var group in feedback.Where(c=>c.id=="tile_land").GroupBy(c=>(int)Math.Round(c.time*100000)))check(group.Count()==1,name+": no duplicated exact landing cue");
            var carries=new HashSet<int>(d.carryIds);var continued=new HashSet<int>(d.continuedIds);var relevant=new HashSet<int>(carries.Concat(continued));
            foreach(var m in retimed.motion)if(d.columns.Contains((int)m.fromX))relevant.Add(m.id);
            var times=new SortedSet<float>{t0,t0+.0001f,t0+next.duration,t0+next.duration+TileFall.LandingSeconds+.001f};
            for(float t=t0;t<t0+next.duration+TileFall.LandingSeconds+.001f;t+=1f/240)times.Add(t);
            foreach(var m in old.motion)foreach(float eventTime in new[]{m.delay,Contact(m),Contact(m)+m.landing})foreach(float delta in new[]{-.0001f,0f,.0001f})if(eventTime+delta>=t0)times.Add(eventTime+delta);
            foreach(var m in retimed.motion)foreach(float eventTime in new[]{t0+m.delay,t0+Contact(m),t0+Contact(m)+m.landing})foreach(float delta in new[]{-.0001f,0f,.0001f})if(eventTime+delta>=t0)times.Add(eventTime+delta);
            foreach(float time in times) {
                float age=time-t0;
                if(d.terminalIdleLanding&&!addedSettled&&age>=next.duration){expectedNext.Add(refined[k+2],t0+next.duration);actual.Add(refined[k+2],t0+next.duration);addedSettled=true;}
                var nextActive=time<t0+next.duration?next:d.terminalIdleLanding&&time<t0+next.duration+refined[k+2].duration?refined[k+2]:null;
                var expectedActive=time<t0+retimed.duration?retimed:d.terminalIdleLanding&&time<t0+next.duration+refined[k+2].duration?refined[k+2]:null;
                float sampleStart=nextActive==null||nextActive==next?t0:t0+next.duration,expectedStart=expectedActive==null||expectedActive==retimed?t0:t0+next.duration;
                var prior=Bodies(expectedOld.Sample(time<old.duration?old:null,old.after,time,0),check,name+" old "+time);
                var following=Bodies(expectedNext.Sample(expectedActive,retimed.after,time,expectedStart),check,name+" next "+time);
                var bodies=Bodies(actual.Sample(nextActive,next.after,time,sampleStart),check,name+" actual "+time);row.poseSamples++;
                foreach(int id in relevant) {
                    var future=retimed.motion.FirstOrDefault(m=>m.id==id);var priorRoute=old.motion.FirstOrDefault(m=>m.id==id);bool useOld=priorRoute!=null&&(future==null||age<future.delay);var expected=useOld?prior:following;
                    bool a=expected.TryGetValue(id,out var p),b=bodies.TryGetValue(id,out var q);check(a==b,name+": original segment clipping/visibility "+id+" at "+time);if(a&&b)check(Pose(p,q),name+": exact segment flight/stretch/squash "+id+" at "+time);
                    var route=next.motion.Single(m=>m.id==id);var original=useOld?priorRoute:future;
                    TileFall.Position(original,useOld?time:age,out float ex,out float ey);TileFall.Position(route,age,out float ax,out float ay);row.routeSamples++;check(Near(ex,ax)&&Near(ey,ay),name+": route position remains continuous "+id+" at "+time);
                }
                var allBodies=bodies.Values.ToArray();
                for(int ai=0;ai<allBodies.Length;ai++)for(int bi=ai+1;bi<allBodies.Length;bi++) {
                    var body=allBodies[ai];var other=allBodies[bi];
                    if(!relevant.Contains(body.pieceId)&&!relevant.Contains(other.pieceId)||Math.Abs(body.x-other.x)>.001f)continue;
                    float clearance=Math.Abs(body.y-other.y);row.minimumColumnClearance=Math.Min(row.minimumColumnClearance,clearance);row.collisionSamples++;check(clearance>=.90f,name+": independent cross-owner column clearance "+body.pieceId+"/"+other.pieceId+" at "+time);
                }
                // Original fragments retain absolute ages; the new match may
                // add its own effects without replacing any old debris sample.
                var oldDraw=expectedOld.Sample(time<old.duration?old:null,old.after,time,0);var newDraw=actual.Sample(nextActive,next.after,time,sampleStart);
                foreach(var effect in oldDraw.Where(p=>p.pieceId==0)){check(newDraw.Any(q=>q.pieceId==0&&Pose(effect,q)&&Near(effect.age,q.age)),name+": every prior tile/obstacle/power effect retains absolute age");row.priorEffectSamples++;}
            }
            foreach(var removed in next.removed)foreach(float delta in new[]{-.0001f,.0001f}) {
                float clear=removed.time+(removed.cause=="obstacle"?.24f:.035f),age=clear+delta;var draws=actual.Sample(next,next.before,t0+age,t0);
                check(draws.Any(p=>p.pieceId==removed.piece.id)==(delta<0),name+": exact body clear marker "+removed.piece.id);
                check(Goals(expectedNext,retimed,t0+age,t0,actual,next,t0+age,t0),name+": counter follows original relative clear timing "+removed.piece.id);
            }
            foreach(int id in continued) {
                var future=retimed.motion.Single(m=>m.id==id);var oldMotion=old.motion.Single(m=>m.id==id);
                check(Contact(oldMotion)+oldMotion.landing<=t0+future.delay+Epsilon,name+": old squash expires before next flight "+id);
                var compound=next.motion.Single(m=>m.id==id);float a,b;var first=LocalCascadeContinuation.Segment(compound,Math.Max(0,future.delay-.0001f),out a);var second=LocalCascadeContinuation.Segment(compound,future.delay,out b);
                check(first.toX==future.fromX&&first.toY==future.fromY&&Near(a,Math.Max(0,future.delay-.0001f)+t0)&&Near(b,future.delay)&&Near(second.delay,future.delay),name+": bounded segment clock switches exactly once "+id);
            }
            if(d.terminalIdleLanding) {
                check(next.motion.All(m=>Contact(m)<=next.duration+Epsilon),name+": every actual flight/contact finishes before terminal settlement or input");
                row.landingTailsBeyondSuccessor=next.motion.Count(m=>Contact(m)+m.landing>next.duration+Epsilon);
                check(row.landingTailsBeyondSuccessor>0&&row.successorExtension<=.12f+Epsilon&&row.secondsSavedVs74>.01f,name+": terminal landing tails are exercised with bounded positive net improvement");
                check(k+2==refined.Count-1&&refined[k+2].kind=="settled"&&refined[k+2].before.status=="Playing"&&ReferenceEquals(refined[k+2],source[k+2]),name+": terminal recipient is the original unchanged Playing settlement");
                foreach(var m in next.motion.Where(m=>Contact(m)+m.landing>next.duration+Epsilon)) {
                    float t=t0+Contact(m)+m.landing*.75f;var idle=actual.Sample(null,next.after,t,0);var expected=retimed.motion.Any(v=>v.id==m.id)?expectedNext.Sample(null,retimed.after,t,0):expectedOld.Sample(null,old.after,t,0);
                    var q=idle.SingleOrDefault(v=>v.pieceId==m.id);var p=expected.SingleOrDefault(v=>v.pieceId==m.id);
                    check(q!=null&&p!=null&&Pose(p,q),name+": ordinary terminal landing survives into settled/idle "+m.id);
                }
                foreach(int fps in new[]{15,30,60})Clock(refined,fps,false,check);Clock(refined,30,true,check);
            } else check(next.motion.Where(m=>continued.Contains(m.id)||carries.Contains(m.id)).All(m=>Contact(m)+m.landing<=next.duration+Epsilon),name+": no carried/continued tail leaks into another active boundary");
            return row;
        }

        static void Guards(List<BoardStep> source,Report report,Action<bool,string> check) {
            void Reject(string name,Action<BoardStep,BoardStep> mutate) {
                var a=Copy(source[1]);var b=Copy(source[2]);a.motion=a.motion.Select(m=>Shift(m,0)).ToList();b.motion=b.motion.Select(m=>Shift(m,0)).ToList();mutate(a,b);var pair=new List<BoardStep>{a,b};string frozen=Json(pair);
                LocalContinuationDecision d;check(!LocalCascadeContinuation.TryDescribe(a,b,out d),"74 guard rejects "+name);var decisions=new List<LocalContinuationDecision>();var result=LocalCascadeContinuation.Apply(pair,decisions);report.guardCases++;
                CompareCheckpoint75(pair,"guard_"+name,report,check,true);
                check(!decisions.Any(x=>x.accepted),"No74 handoff for "+name);check(Json(result)==Json(LocalCascadePlayback.Apply(pair)),"Exact73 fallback for "+name);check(frozen==Json(pair),"Rejected source remains immutable "+name);
            }
            Reject("power action",(a,b)=>b.powerPlan=new ReviewPlan());
            Reject("tool action",(a,b)=>b.booster=new BoosterPlan());
            Reject("power creation",(a,b)=>b.created=new List<Piece>{new Piece{id=999,family="power",power=4}});
            Reject("delivery collection",(a,b)=>b.collections=new List<GoalCollection>{new GoalCollection{family="pail",arrival=.1f}});
            Reject("advanced obstacle",(a,b)=>b.damage=new List<Damage>{new Damage{id=1,family="cabinet",beforeHP=1,afterHP=0}});
            Reject("partial moss damage",(a,b)=>b.damage=new List<Damage>{new Damage{id=1,family="moss",beforeHP=2,afterHP=1}});
            Reject("short destination",(a,b)=>b.duration=.1f);
            Reject("old body still clearing",(a,b)=>a.removed=a.removed.Select(r=>new Removed{piece=r.piece,time=r.cause=="obstacle"?.7f:r.time,cause=r.cause}).ToList());
            Reject("old diagonal",(a,b)=>a.motion[0].fromX--);
            Reject("old upward",(a,b)=>a.motion[0].fromY=a.motion[0].toY-1);
            Reject("old inconsistent path",(a,b)=>{var m=a.motion[0];m.path=new List<FallLeg>{new FallLeg{fromX=m.fromX,fromY=m.fromY,toX=m.toX,toY=m.toY,delay=m.delay,seconds=m.seconds,distance=1}};});
            Reject("old source mismatch",(a,b)=>a.motion[0].fromY++);
            Reject("following source mismatch",(a,b)=>b.motion.Single(m=>m.id==22).fromY++);
            Reject("following sidefeed intersects old column",(a,b)=>b.motion.First(m=>m.fromX!=m.toX).toX=4);
            Reject("duplicate old route",(a,b)=>a.motion.Add(Shift(a.motion[0],0)));
            Reject("duplicate following route",(a,b)=>b.motion.Add(Shift(b.motion[0],0)));
            Reject("excess column padding",(a,b)=>b.motion.Single(m=>m.id==74).delay=0);
            Reject("old readiness out of order",(a,b)=>a.motion.Single(m=>m.id==22).landing=0);
            Reject("shared body identity changes",(a,b)=>{b.after=SnapshotCopy(b.after);b.after.pieces.Single(p=>p.id==22).color=(b.after.pieces.Single(p=>p.id==22).color+1)%6;});
            Reject("unchanged carried HP changes",(a,b)=>{b.after=SnapshotCopy(b.after);b.after.pieces.Single(p=>p.id==64).hp++;});
            Reject("power elsewhere in snapshot",(a,b)=>{b.after=SnapshotCopy(b.after);b.after.pieces.Single(p=>p.id==64).family="power";});
            Reject("nonfinite landing",(a,b)=>a.motion[0].landing=float.NaN);
            Reject("excess decorative landing",(a,b)=>a.motion[0].landing=.2f);
            var decisions=new List<LocalContinuationDecision>();var twice=LocalCascadeContinuation.Apply(source.Concat(source),decisions);report.guardCases++;check(decisions.Count(x=>x.accepted)==1&&decisions.Any(x=>x.reason=="second_overlap_disabled"),"Only one overlap across repeated phase sequences");
            CompareCheckpoint75(source.Concat(source).ToList(),"guard_repeated_sequence",report,check,true);
            var again=LocalCascadeContinuation.Apply(twice);check(Json(twice)==Json(again)&&again.SelectMany(s=>s.motion).Where(LocalCascadeContinuation.IsContinuation).All(m=>twice.Any(s=>s.motion.Contains(m))),"Idempotence retains original continuation ownership");
        }

        static void TerminalGuards(List<BoardStep> source,Report report,Action<bool,string> check) {
            void Reject(string name,Action<BoardStep,BoardStep,BoardStep> mutate) {
                var a=Copy(source[1]);var b=Copy(source[2]);var tail=Copy(source[3]);a.motion=a.motion.Select(m=>Shift(m,0)).ToList();b.motion=b.motion.Select(m=>Shift(m,0)).ToList();mutate(a,b,tail);
                var input=new List<BoardStep>{a,b,tail};string frozen=Json(input);LocalContinuationDecision d;
                check(!LocalCascadeContinuation.TryDescribeTerminal(a,b,tail,out d),"75 terminal guard rejects "+name);
                var decisions=new List<LocalContinuationDecision>();var actual=LocalCascadeContinuation.Apply(input,decisions);
                CompareCheckpoint75(input,"terminal_guard_"+name,report,check,true);
                check(!decisions.Any(x=>x.accepted&&x.terminalIdleLanding),"No terminal expansion for "+name);
                check(Json(actual)==Json(LocalCascadeContinuation.ApplyCheckpoint74(input)),"Exact74 fallback for terminal guard "+name);
                check(frozen==Json(input),"Terminal rejection keeps input immutable "+name);report.guardCases++;
            }
            Reject("win settlement",(a,b,s)=>{s.before=SnapshotCopy(s.before);s.after=SnapshotCopy(s.after);s.before.status=s.after.status="Won";});
            Reject("loss settlement",(a,b,s)=>{s.before=SnapshotCopy(s.before);s.after=SnapshotCopy(s.after);s.before.status=s.after.status="Lost";});
            Reject("active following phase",(a,b,s)=>s.kind="powerFall");
            Reject("terminal moves differ",(a,b,s)=>{s.after=SnapshotCopy(s.after);s.after.moves--;});
            Reject("terminal goals differ",(a,b,s)=>{s.after=SnapshotCopy(s.after);s.after.goals[0].count++;});
            Reject("terminal body position differs",(a,b,s)=>{s.after=SnapshotCopy(s.after);s.after.pieces[0].y++;});
            Reject("terminal motion",(a,b,s)=>s.motion=new List<Motion>{Shift(b.motion[0],0)});
            Reject("terminal damage",(a,b,s)=>s.damage=new List<Damage>{new Damage{id=1,family="moss",beforeHP=1,afterHP=0}});
            Reject("terminal removal",(a,b,s)=>s.removed=new List<Removed>{new Removed{piece=b.after.pieces[0],cause="match"}});
            Reject("terminal creation",(a,b,s)=>s.created=new List<Piece>{new Piece{id=999,family="power",power=4}});
            Reject("terminal delivery",(a,b,s)=>s.collections=new List<GoalCollection>{new GoalCollection{family="pail",arrival=.1f}});
            Reject("terminal power",(a,b,s)=>s.powerPlan=new ReviewPlan());
            Reject("terminal tool",(a,b,s)=>s.booster=new BoosterPlan());
            Reject("terminal playback track",(a,b,s)=>s.playbackTracks=new List<PlaybackTrack>{new PlaybackTrack{step=a}});
            Reject("invalid terminal duration",(a,b,s)=>s.duration=float.NaN);
            Reject("no net saving after padded flight",(a,b,s)=>{LocalContinuationDecision d;LocalCascadeContinuation.TryDescribe(a,b,out d);a.duration=d.handoff+.03f;});
            Reject("unbounded flight extension",(a,b,s)=>b.duration=.10f);
            Reject("terminal snapshot missing",(a,b,s)=>s.before=null);
            var blocked=new List<BoardStep>{source[1],source[2],new BoardStep{kind="waiting",before=source[2].after,after=source[2].after,duration=.2f},source[3]};var decisions=new List<LocalContinuationDecision>();
            var fallback=LocalCascadeContinuation.Apply(blocked,decisions);report.guardCases++;
            CompareCheckpoint75(blocked,"terminal_guard_intervening_active_phase",report,check,true);
            check(!decisions.Any(d=>d.accepted&&d.terminalIdleLanding)&&Json(fallback)==Json(LocalCascadeContinuation.ApplyCheckpoint74(blocked)),"Terminal relaxation is unavailable across an intervening active/unknown phase");
            var refined=LocalCascadeContinuation.Apply(source);var d0=new List<LocalContinuationDecision>();var twice=LocalCascadeContinuation.Apply(refined,d0);report.guardCases++;
            check(Json(twice)==Json(refined)&&!d0.Any(d=>d.accepted),"Replanning a terminal composite retains subtype ownership and creates no second handoff");
        }

        static void BoundaryFeedback(List<BoardStep> source,Action<bool,string> check) {
            var a=Copy(source[1]);a.motion=a.motion.Select(m=>Shift(m,0)).ToList();var old=a.motion.Single(m=>m.id==22);old.delay=.29f-old.seconds;
            var decisions=new List<LocalContinuationDecision>();var pair=LocalCascadeContinuation.Apply(new[]{a,source[2]},decisions);check(decisions.Any(d=>d.accepted),"Exact boundary landing still qualifies");
            if(!decisions.Any(d=>d.accepted))return;
            var compound=pair[1].motion.Single(m=>m.id==22);var contacts=LocalCascadeContinuation.LandingContacts(compound).ToArray();
            check(LocalCascadeContinuation.IsContinuation(compound)&&contacts.Length==1&&contacts[0]>0,"Old contact exactly at handoff is not replayed at zero");
            check(!FeedbackPlan.Build(pair[1]).Any(c=>c.id=="tile_land"&&Math.Abs(c.time)<.00001f),"Feedback.Begin does not repeat the outgoing boundary landing");
            var positive=source[1].motion.Single(m=>m.id==22);var original=LocalCascadeContinuation.Apply(new[]{source[1],source[2]})[1].motion.Single(m=>m.id==22);
            check(LocalCascadeContinuation.LandingContacts(original).Any(c=>Near(c,Contact(positive)-.29f)),"A genuinely pending old contact transfers once");
        }

        static void LandingAtHandoff(List<BoardStep> source,Report report,Action<bool,string> check) {
            var a=Copy(source[1]);a.motion=a.motion.Select(m=>Shift(m,0)).ToList();var landing=a.motion.Single(m=>m.id==22);landing.delay=.28f-landing.seconds;
            var input=new List<BoardStep>{a,source[2]};var decisions=new List<LocalContinuationDecision>();var refined=LocalCascadeContinuation.Apply(input,decisions);var d=decisions.FirstOrDefault(x=>x.accepted);
            check(d!=null,"A contacted shared body with unfinished landing qualifies");if(d==null)return;
            check(Contact(landing)<d.handoff&&Contact(landing)+landing.landing>d.handoff&&d.continuedIds.Contains(22),"A finished flight keeps its still-active landing segment at handoff");
            report.rendererRows.Add(InspectRenderer(input,refined,d,"contacted_body_still_landing",check));
        }

        static void Clock(List<BoardStep> steps,int fps,bool lateFrame,Action<bool,string> check) {
            var view=View();int index=0,frames=0;float clock=0,start=0,wall=0;view.Add(steps[0],0);
            while(index<steps.Count&&frames++<10000) {
                var current=steps[index];string a=JsonUtility.ToJson(new Draws{draws=view.Sample(current,current.before,clock,start)});string b=JsonUtility.ToJson(new Draws{draws=view.Sample(current,current.before,clock,start)});check(a==b,"Pause holds compound and carried poses "+fps+"/"+frames);
                float advance=lateFrame&&frames==12?.20f:1f/fps;wall+=advance;
                while(index<steps.Count&&advance>0) {
                    current=steps[index];advance=BoardPlayback.VisibleAdvance(current,advance,clock-start);float remaining=current.duration-(clock-start);
                    if(advance<remaining){clock+=advance;advance=0;}else{clock+=remaining;advance-=remaining;index++;start=clock;if(index<steps.Count)view.Add(steps[index],start);}
                }
                if(index<steps.Count)Bodies(view.Sample(steps[index],steps[index].before,clock,start),check,"Frame clock "+fps+"/"+frames);
            }
            check(index==steps.Count&&frames<10000,"Compound clock reaches settlement "+fps+" late="+lateFrame);
            if(!lateFrame)check(wall<=steps.Sum(s=>s.duration)+.2f,"Normal cadence adds no continuation debt "+fps);
            var final=steps.Last().after;var idle=view.Sample(null,final,clock,0);
            check(idle.Where(d=>d.pieceId>0).Select(d=>d.pieceId).OrderBy(id=>id).SequenceEqual(final.pieces.Where(p=>p.IsAnchor).Select(p=>p.id).OrderBy(id=>id)),"Clock settlement renders exactly the final model body identities");
        }
    }
}
#endif

#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;

namespace HeartOfTheRain.Verification
{
    // Native Editor model stress and sampled presentation diagnostics. This does
    // not measure device frame times or certify human balance or store services.
    public static class GameplayAuditVerification
    {
        [Serializable] sealed class ObstacleBoundary
        {
            public string family, status, matchBody, nextBody;
            public int hp, pieceId, shownAtMatchEnd, actualAfterMatch;
            public float matchSeconds, hitAt, sampledClipSeconds;
        }
        [Serializable] sealed class Report
        {
            public string utc, status, allocationCounter;
            public string scope="Native Unity custom model/stress checks and sampled obstacle phase diagnostics. No physical-device, balance, durable-profile or service certification.";
            public int checks, naturalBoards, naturalActions, pairCases, toolCases;
            public List<string> failures=new List<string>();
            public List<ObstacleBoundary> obstacleBoundaries=new List<ObstacleBoundary>();
        }
        static readonly MethodInfo MatchMethod=typeof(BoardModel).GetMethod("Matches",BindingFlags.NonPublic|BindingFlags.Instance);
        static readonly MethodInfo GravityMethod=typeof(BoardModel).GetMethod("Gravity",BindingFlags.NonPublic|BindingFlags.Instance);

        public static void Run()=>Execute(true,true);
        public static void Baseline()=>Execute(true,false);
        public static void RunObstacleChecks()=>Execute(false,true);
        static void Execute(bool stress,bool verifyBoundary)
        {
            var r=new Report{utc=DateTime.UtcNow.ToString("o")};
            void Check(bool ok,string label){r.checks++;if(!ok&&r.failures.Count<100)r.failures.Add(label);}
            void Stable(BoardModel board,string label)
            {
                board.Validate();
                Check(board.Status!="Resolution limit",label+": resolution guard");
                Check(((IList)MatchMethod.Invoke(board,new object[]{null})).Count==0,label+": unresolved stable match");
                string before=JsonUtility.ToJson(board.Snapshot());var additional=new TurnResult();GravityMethod.Invoke(board,new object[]{additional});
                Check(additional.steps.Count==0&&before==JsonUtility.ToJson(board.Snapshot()),label+": gravity reached fixed point");
                Check(board.Status!="Playing"||board.LegalSwaps().Count>0||board.Pieces.Values.Any(p=>p.family=="power"),label+": stable board has legal action");
            }
            void Charges(BoardModel board,TurnResult turn,int moves,int priorTurn,string label)
            {
                Check(turn.accepted,label+": accepted action");
                Check(board.Moves==moves-1&&board.Turn==priorTurn+1,label+": one move and one turn");
                Check(turn.steps.Count>0&&turn.steps.Last().kind=="settled",label+": settlement snapshot");
                Check(JsonUtility.ToJson(turn.steps.Last().after)==JsonUtility.ToJson(board.Snapshot()),label+": final model snapshot");
                Stable(board,label);
            }
            try
            {
                var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
                Check(ui!=null&&ui.boards!=null&&ui.boards.levels.Length==50,"Live 50-level bindings");
                long allocationControl=GC.GetAllocatedBytesForCurrentThread();var knownAllocation=new byte[4096];GC.KeepAlive(knownAllocation);
                bool allocationSupported=GC.GetAllocatedBytesForCurrentThread()>allocationControl;
                r.allocationCounter=allocationSupported?"AVAILABLE_WITH_POSITIVE_CONTROL":"UNAVAILABLE_POSITIVE_CONTROL_NOT_OBSERVED; no zero-allocation claim";
                if(stress)for(int level=0;level<50;level++)
                {
                    var data=JsonUtility.FromJson<LevelData>(ui.boards.levels[level].text);
                    foreach(uint seed in new[]{(uint)data.tileSeed,(uint)(data.tileSeed+317),(uint)(data.tileSeed+7751)})
                    {
                        var board=new BoardModel(data,seed);var twin=new BoardModel(data,seed);r.naturalBoards++;
                        for(int move=0;move<8&&board.Status=="Playing";move++)
                        {
                            string label="L"+(level+1)+" seed "+seed+" action "+move;var options=board.LegalSwaps();
                            TurnResult turn,mirror;int before=board.Moves,priorTurn=board.Turn;
                            if(options.Count>0)
                            {
                                var chosen=options[(move*17+level+(int)(seed%101))%options.Count];
                                turn=board.Swap(chosen[0].x,chosen[0].y,chosen[1].x,chosen[1].y);
                                mirror=twin.Swap(chosen[0].x,chosen[0].y,chosen[1].x,chosen[1].y);
                            }
                            else
                            {
                                var power=board.Pieces.Values.Where(p=>p.family=="power").OrderBy(p=>p.id).FirstOrDefault();
                                Check(power!=null,label+": no unavailable continuation");if(power==null)break;
                                turn=board.Tap(power.x,power.y);mirror=twin.Tap(power.x,power.y);
                            }
                            r.naturalActions++;Charges(board,turn,before,priorTurn,label);
                            Check(mirror.accepted&&JsonUtility.ToJson(board.Snapshot())==JsonUtility.ToJson(twin.Snapshot()),label+": deterministic replay");
                        }
                    }
                    int[][] pairs={new[]{4,5},new[]{4,21},new[]{21,21},new[]{7,4},new[]{7,21},new[]{7,7},new[]{11,5},new[]{11,21},new[]{11,11},new[]{7,11},new[]{16,5},new[]{16,21},new[]{16,11},new[]{7,16}};
                    foreach(var pair in pairs)
                    {
                        var board=new BoardModel(data);var a=board.Pieces.Values.OrderBy(p=>p.y).ThenBy(p=>p.x).First(p=>p.family=="gem"&&board.At(p.x+1,p.y)?.family=="gem");
                        int x=a.x,y=a.y;board.InjectReviewPower(x,y,pair[0]);board.InjectReviewPower(x+1,y,pair[1]);int before=board.Moves,priorTurn=board.Turn;
                        var turn=board.Swap(x,y,x+1,y);r.pairCases++;Charges(board,turn,before,priorTurn,"L"+(level+1)+" pair "+pair[0]+"+"+pair[1]);
                    }
                    foreach(BoosterKind tool in Enum.GetValues(typeof(BoosterKind)))
                    {
                        var board=new BoardModel(data);var stock=new BoosterInventory();int moves=board.Moves,turn=board.Turn;var target=board.Pieces.Values.OrderBy(p=>p.id).First(p=>p.family=="gem");
                        var action=board.UseBooster(tool,target.x,target.y,stock);r.toolCases++;
                        string label="L"+(level+1)+" tool "+tool;
                        Check(action.accepted,label+": accepted tool");Check(board.Moves==moves&&board.Turn==turn,label+": no move or threat-clock charge");
                        Check(stock.Count(tool)==2,label+": one inventory debit");Stable(board,label);
                        var before=JsonUtility.ToJson(board.Snapshot());
                        if(tool!=BoosterKind.Atlas){Check(!board.UseBooster(tool,-1,-1,stock).accepted,label+": rejects invalid cell");Check(stock.Count(tool)==2&&before==JsonUtility.ToJson(board.Snapshot()),label+": invalid use is atomic");}
                    }
                }
                foreach(string family in new[]{"stone","moss","case","gate"})foreach(int hp in new[]{1,2})
                {
                    // Direct Hammer works for every basic family, including case;
                    // natural adjacency is tested separately for stone/moss/gate.
                    if(family=="case")continue;
                    var fixture=GameplayAuditFixtures.Obstacle(family,hp);var board=new BoardModel(fixture);int id=board.At(4,4).id;
                    var action=board.Swap(4,2,4,3);Check(action.accepted,family+" adjacency fixture accepted");
                    var schedule=BoardPlayback.Build(action.steps,fixture);var match=schedule.First(s=>s.kind=="match"||s.playbackTracks!=null&&s.playbackTracks.Any(t=>t.step.kind=="match"));var hit=match.damage.First(d=>d.id==id);
                    int index=schedule.IndexOf(match);var next=schedule[index+1];var view=new BoardPresentation();view.Add(match,0);
                    var oldBody=view.Sample(match,match.before,Math.Max(0,match.duration-.001f),0).FirstOrDefault(d=>d.pieceId==id);
                    view.Add(next,match.duration);var nextBody=view.Sample(next,next.before,match.duration+.001f,match.duration).FirstOrDefault(d=>d.pieceId==id);
                    var shown=view.DisplayGoals(match,match.before,match.duration).First(g=>g.family==family).count;
                    string expected=family+"/"+BoardPresentation.Prefix(family)+"_Hit_"+hp;
                    bool needsCarry=hp>1&&match.duration+.001f-hit.time<.8f;
                    string status=needsCarry&&(nextBody==null||nextBody.bank!="obstacle"||nextBody.key!=expected)?"HIT_BODY_CUT_AT_PHASE_BOUNDARY":shown!=match.after.goals.First(g=>g.family==family).count?"GOAL_HANDOFF_BEFORE_CONTACT_CLEARANCE":"NO_BOUNDARY_DISCONTINUITY";
                    r.obstacleBoundaries.Add(new ObstacleBoundary{family=family,hp=hp,pieceId=id,matchSeconds=match.duration,hitAt=hit.time,sampledClipSeconds=match.duration-hit.time,matchBody=oldBody==null?"absent":oldBody.bank+"/"+oldBody.key,nextBody=nextBody==null?"absent":nextBody.bank+"/"+nextBody.key,shownAtMatchEnd=shown,actualAfterMatch=match.after.goals.First(g=>g.family==family).count,status=status});
                    if(verifyBoundary)
                    {
                        Check(status=="NO_BOUNDARY_DISCONTINUITY",family+" HP"+hp+": continuous phase handoff");
                        Check(match.kind=="powerFall"&&match.playbackTracks.Count==1,family+" HP"+hp+": match and refill share contact timeline");
                        Check(match.motion.Any(m=>(m.fromX==3||m.fromX==5)&&m.delay<hit.time+.24f-.001f),family+" HP"+hp+": unrelated columns start before obstacle clear");
                        if(hp==1)
                        {
                            var above=match.motion.Where(m=>m.fromX==4&&m.fromY>4&&m.toY<=4).ToArray();
                            Check(above.Length>0&&above.All(m=>m.delay>=hit.time+.24f-.001f),family+": falling bodies respect occupied obstacle cell");
                            var mid=view.Sample(match,match.before,hit.time+.16f,0);Check(mid.Any(d=>d.pieceId==id),family+": final hit retains body before clearance");
                            var cleared=view.Sample(match,match.before,hit.time+.241f,0);Check(cleared.All(d=>d.pieceId!=id),family+": body disappears at clear marker");
                            Check(view.DisplayGoals(match,match.before,hit.time+.16f).Single(g=>g.family==family).count==1&&view.DisplayGoals(match,match.before,hit.time+.241f).Single(g=>g.family==family).count==0,family+": displayed target follows clear marker");
                        }
                    }
                }
                if(verifyBoundary)foreach(string family in new[]{"stone","moss","case","gate"})
                {
                    var data=GameplayAuditFixtures.Obstacle(family,2);var board=new BoardModel(data);var prior=board.At(4,4).Copy();
                    var action=family=="case"?board.UseBooster(BoosterKind.Hammer,4,4,new BoosterInventory()):board.Swap(4,2,4,3);
                    var raw=action.steps.First(s=>s.damage.Any(d=>d.id==prior.id));var damage=raw.damage.First(d=>d.id==prior.id);float firstAt=damage.time;
                    var view=new BoardPresentation();view.Add(raw,0);string hit2=family+"/"+BoardPresentation.Prefix(family)+"_Hit_2";
                    var carried=view.Sample(null,raw.after,firstAt+.2f,0).Single(d=>d.pieceId==prior.id);
                    Check(carried.bank=="obstacle"&&carried.key==hit2&&Math.Abs(carried.age-.2f)<.001f,family+": partial hit continues into idle with absolute age");
                    var finished=view.Sample(null,raw.after,firstAt+.801f,0).Single(d=>d.pieceId==prior.id);
                    Check(finished.bank=="body"&&finished.key==family+"_1",family+": hit returns to current lower-HP body after authored window");
                    var after=new BoardSnapshot{pieces=raw.after.pieces.Where(p=>p.id!=prior.id).Select(p=>p.Copy()).ToArray(),goals=new[]{new Goal{family=family,count=0}}};
                    var last=prior.Copy();last.hp=1;
                    var newer=new BoardStep{kind="match",before=raw.after,after=after,duration=.28f};newer.damage.Add(new Damage{id=prior.id,x=4,y=4,family=family,beforeHP=1,afterHP=0,time=.05f});newer.removed.Add(new Removed{piece=last,time=.05f,cause="obstacle"});
                    float secondStart=firstAt+.3f;view.Add(newer,secondStart);
                    var newest=view.Sample(newer,newer.before,secondStart+.06f,secondStart).Single(d=>d.pieceId==prior.id);
                    Check(newest.bank=="obstacle"&&newest.key==family+"/"+BoardPresentation.Prefix(family)+"_Hit_1"&&Math.Abs(newest.age-.01f)<.001f,family+": newer active hit replaces carried history");
                    var oldStill=view.Sample(null,raw.after,firstAt+.2f,0).Single(d=>d.pieceId==prior.id);
                    Check(oldStill.key==hit2&&Math.Abs(oldStill.age-.2f)<.001f,family+": future hit cannot replace current animation early");
                    Check(view.Sample(null,after,secondStart+.06f,0).All(d=>d.pieceId!=prior.id),family+": carried hit cannot resurrect absent piece");
                    var terminal=BoardPlayback.Build(new[]{newer,new BoardStep{kind="settled",before=after,after=after,duration=.06f}},data).First();
                    Check(terminal.duration>=.29f-.001f,family+": terminal match retains final clear marker without gravity");
                    // Isolate the carried body from the separate manual-tool
                    // effect sampler, which has its own allocation behavior.
                    var allocationView=new BoardPresentation();allocationView.Add(new BoardStep{kind="match",before=raw.before,after=raw.after,duration=.28f,damage=raw.damage},0);
                    for(int n=0;n<20;n++)allocationView.SampleLive(null,raw.after,firstAt+.2f,0);
                    if(allocationSupported)
                    {
                        long allocated=GC.GetAllocatedBytesForCurrentThread();for(int n=0;n<1000;n++)allocationView.SampleLive(null,raw.after,firstAt+.2f,0);
                        Check(GC.GetAllocatedBytesForCurrentThread()==allocated,family+": carried-hit sampling reuses its hot-path storage");
                    }
                }
            }
            catch(Exception ex){r.failures.Add(ex.ToString());}
            r.status=r.failures.Count==0?"PASS_NATIVE_GAMEPLAY_AUDIT_WITH_DIAGNOSTICS":"FAIL_NATIVE_GAMEPLAY_AUDIT";
            string folder=Path.GetFullPath("../Verification/Evidence/GameplayAudit");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,stress?"Audit_Checks.json":"Obstacle_Checks.json"),JsonUtility.ToJson(r,true));
            EditorApplication.Exit(r.failures.Count==0?0:1);
        }
    }
}
#endif

#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using Motion=HeartOfTheRain.M46.Motion;

namespace HeartOfTheRain.Verification {
    public static class LegalSwapExistenceVerification {
        [Serializable] public sealed class Row {
            public string name,checkpointHash,orderedSwaps;
            public int legalSwaps;public bool exists;
        }
        [Serializable] public sealed class Timing {
            public string name;public int iterations;
            public double fullListMilliseconds,existenceMilliseconds;
            public long fullListAllocatedBytes,existenceAllocatedBytes;
        }
        [Serializable] public sealed class Report {
            public string utc,status,scope="Native Editor legal-swap parity, exact350 archived73 raw-turn/final hashes, and gravity snapshot/order/RNG controls against the eager73 reference. Warm CPU/allocation diagnostics are not Android frame or input-latency measurements.";
            public int checks,boards,naturalCommands,powerCommands,toolCommands,guardCases;
            public int baselineModelCases,gravityCases;
            public bool baselineRawTurnParity=true,baselineFinalSnapshotParity=true;
            public string baselineReportPath,baselineReportSHA256;
            public bool allocationCounterUsable;public long allocationPositiveControlBytes;
            public List<string> errors=new List<string>();
            public List<Row> rows=new List<Row>();public List<Timing> timings=new List<Timing>();
            public List<ModelParityRow> modelParity=new List<ModelParityRow>();
            public List<GravityRow> gravityRows=new List<GravityRow>();
            public List<GravityTiming> gravityTimings=new List<GravityTiming>();
        }
        [Serializable] public sealed class ModelParityRow {public string name,archivedTurnHash,archivedFinalHash,turnHash,finalHash;}
        [Serializable] public sealed class GravityRow {public string name,legacyResultHash,optimizedResultHash,checkpointHash,orderedKeys;public bool fullGravity;public int legacySteps,optimizedSteps;}
        [Serializable] public sealed class GravityTiming {public string name;public int iterations;public double legacyMilliseconds,optimizedMilliseconds;public long legacyAllocatedBytes,optimizedAllocatedBytes;}
        [Serializable] sealed class ArchivedRow {public string name,turnHash,finalHash;}
        [Serializable] sealed class ArchivedReport {public string status;public int modelCases;public List<ArchivedRow> rows;}
        static readonly MethodInfo ExistsMethod=typeof(BoardModel).GetMethod("HasLegalSwap",BindingFlags.Instance|BindingFlags.NonPublic);
        static readonly MethodInfo GravityMethod=typeof(BoardModel).GetMethod("Gravity",BindingFlags.Instance|BindingFlags.NonPublic),VerticalMethod=typeof(BoardModel).GetMethod("VerticalGravity",BindingFlags.Instance|BindingFlags.NonPublic),NewColorMethod=typeof(BoardModel).GetMethod("NewColor",BindingFlags.Instance|BindingFlags.NonPublic);
        static readonly FieldInfo NextIdField=typeof(BoardModel).GetField("nextId",BindingFlags.Instance|BindingFlags.NonPublic);
        static Func<bool> Query(BoardModel board)=>(Func<bool>)Delegate.CreateDelegate(typeof(Func<bool>),board,ExistsMethod);
        static string Hash(string value)=>HashBytes(Encoding.UTF8.GetBytes(value));
        static string HashBytes(byte[] value){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(value)).Replace("-","").ToLowerInvariant();}
        static string Ordered(List<Cell[]> swaps)=>string.Join(";",swaps.Select(p=>p[0].x+","+p[0].y+":"+p[1].x+","+p[1].y));

        public static void Run() {
            var r=new Report{utc=DateTime.UtcNow.ToString("o")};
            void Check(bool ok,string label){r.checks++;if(!ok&&r.errors.Count<100)r.errors.Add(label);}
            try {
                Check(ExistsMethod!=null,"Live model existence probe is available");
                var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
                Check(ui!=null&&ui.boards!=null&&ui.boards.levels.Length==50,"All 50 approved authored boards are bound");
                r.baselineReportPath=Path.GetFullPath(Path.Combine(Application.dataPath,"../../Verification/Evidence/LocalCascade73/Native/LocalCascade.json"));
                string archivedText=File.ReadAllText(r.baselineReportPath);var archived=JsonUtility.FromJson<ArchivedReport>(archivedText);r.baselineReportSHA256=HashBytes(File.ReadAllBytes(r.baselineReportPath));
                Check(archived.status=="PASS_NATIVE_LOCAL_CASCADE73"&&archived.modelCases==350&&archived.rows.Count==350,"Immutable checkpoint73 native350 model hashes are available");
                var baseline=archived.rows.ToDictionary(row=>row.name);
                var benchmarks=new List<KeyValuePair<string,BoardModel>>();
                for(int index=0;index<50;index++) {
                    var level=JsonUtility.FromJson<LevelData>(ui.boards.levels[index].text);string name="L"+(index+1);
                    var initial=new BoardModel(level);r.boards++;Inspect(initial,name+"/initial",r,Check);
                    benchmarks.Add(new KeyValuePair<string,BoardModel>(name,initial));
                    var natural=new BoardModel(level);var move=natural.LegalSwaps().First();
                    var turn=natural.Swap(move[0].x,move[0].y,move[1].x,move[1].y);r.naturalCommands++;
                    ModelParity(name+"_match",natural,turn,baseline,r,Check);
                    Check(turn.accepted&&natural.Status!="Resolution limit",name+": natural command settles");Inspect(natural,name+"/after_natural",r,Check);
                    foreach(int kind in new[]{4,5,7,11,16,21}) {
                        var board=new BoardModel(level);var source=board.Pieces.Values.First(p=>p.family=="gem");
                        Check(board.InjectReviewPower(source.x,source.y,kind),name+": power fixture injected "+kind);
                        Inspect(board,name+"/before_power"+kind,r,Check);
                        turn=board.Tap(source.x,source.y);r.powerCommands++;
                        ModelParity(name+"_power"+kind,board,turn,baseline,r,Check);
                        Check(turn.accepted&&board.Status!="Resolution limit",name+": power command settles "+kind);Inspect(board,name+"/after_power"+kind,r,Check);
                    }
                    foreach(BoosterKind tool in new[]{BoosterKind.Hammer,BoosterKind.Axe,BoosterKind.Ram,BoosterKind.Atlas}) {
                        var board=new BoardModel(level);var source=board.Pieces.Values.First(p=>p.family=="gem");var inventory=new BoosterInventory();
                        turn=board.UseBooster(tool,source.x,source.y,inventory);r.toolCommands++;
                        Check(turn.accepted&&inventory.Count(tool)==2&&board.Status!="Resolution limit",name+": tool command settles/spends once "+tool);Inspect(board,name+"/after_tool"+tool,r,Check);
                    }
                }
                Guards(JsonUtility.FromJson<LevelData>(ui.boards.levels[0].text),r,Check,benchmarks);
                GravityCases(r,Check);
                long before=GC.GetAllocatedBytesForCurrentThread();var known=new byte[4096];r.allocationPositiveControlBytes=GC.GetAllocatedBytesForCurrentThread()-before;GC.KeepAlive(known);
                r.allocationCounterUsable=r.allocationPositiveControlBytes>=4096;
                foreach(var fixture in benchmarks)Benchmark(fixture.Key,fixture.Value,r,Check);
                GravityBenchmark(r,Check);
                Check(r.boards==50&&r.naturalCommands==50&&r.powerCommands==300&&r.toolCommands==200,"All authored action/state branches inspected");
                Check(r.baselineModelCases==350&&r.baselineRawTurnParity&&r.baselineFinalSnapshotParity,"All350 raw turn/final hashes exactly equal archived73");
            }catch(Exception e){r.errors.Add(e.ToString());}
            r.status=r.errors.Count==0?"PASS_NATIVE_LEGAL_SWAP_EXISTENCE74":"FAIL_NATIVE_LEGAL_SWAP_EXISTENCE74";
            string folder=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY74_OUTPUT");if(string.IsNullOrEmpty(folder))folder=Path.GetFullPath("../Verification/Evidence/Gameplay74");
            folder=Path.Combine(folder,"Native");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"LegalSwapExistence.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(r.errors.Count==0?0:1);
        }

        static void Inspect(BoardModel board,string name,Report r,Action<bool,string> check) {
            string before=JsonUtility.ToJson(board.Checkpoint());var occupants=board.Pieces.ToArray();
            var full=board.LegalSwaps();string ordered=Ordered(full);var query=Query(board);bool exists=query();
            check(exists==(full.Count>0),name+": existence equals public legal actions");
            for(int repeat=0;repeat<3;repeat++)check(query()==exists,name+": repeat query is stable "+repeat);
            check(before==JsonUtility.ToJson(board.Checkpoint()),name+": IDs/RNG/moves/goals/attempt checkpoint unchanged");
            check(occupants.Select(p=>p.Key).SequenceEqual(board.Pieces.Keys)&&occupants.All(p=>ReferenceEquals(p.Value,board.Pieces[p.Key])),name+": occupant references and enumeration order unchanged");
            check(ordered==Ordered(board.LegalSwaps()),name+": public ordered hint/replay choices unchanged");
            board.Validate();r.rows.Add(new Row{name=name,checkpointHash=Hash(before),orderedSwaps=ordered,legalSwaps=full.Count,exists=exists});
        }

        static void ModelParity(string name,BoardModel board,TurnResult turn,Dictionary<string,ArchivedRow> baseline,Report r,Action<bool,string> check) {
            ArchivedRow old;check(baseline.TryGetValue(name,out old),name+": archived73 model command is present");if(old==null)return;
            var row=new ModelParityRow{name=name,archivedTurnHash=old.turnHash,archivedFinalHash=old.finalHash,turnHash=Hash(JsonUtility.ToJson(turn)),finalHash=Hash(JsonUtility.ToJson(board.Snapshot()))};
            bool raw=row.turnHash==row.archivedTurnHash,final=row.finalHash==row.archivedFinalHash;r.baselineRawTurnParity&=raw;r.baselineFinalSnapshotParity&=final;r.baselineModelCases++;
            check(raw,name+": raw turn hash equals archived73");check(final,name+": final model hash equals archived73");r.modelParity.Add(row);
        }

        static LevelData GravityLevel(string id,Cell[] holes=null,ObstacleCell[] blockers=null,bool spawn=true) {
            const int columns=3,rows=5;var missing=new HashSet<int>((holes??new Cell[0]).Select(c=>c.y*columns+c.x));var obstacles=blockers??new ObstacleCell[0];var occupied=new HashSet<int>(obstacles.Select(c=>c.y*columns+c.x));
            var cells=new List<Cell>();var gems=new List<GemCell>();for(int y=0;y<rows;y++)for(int x=0;x<columns;x++)if(!missing.Contains(y*columns+x)){cells.Add(new Cell(x,y));if(!occupied.Contains(y*columns+x))gems.Add(new GemCell{x=x,y=y,color=(x+2*y)%6});}
            return new LevelData{id=id,columns=columns,rows=rows,movesProposal=10,tileSeed=719,globalLevel=1,activeCells=cells.ToArray(),initialTiles=gems.ToArray(),obstacles=obstacles,goals=obstacles.GroupBy(o=>o.family).Select(g=>new Goal{family=g.Key,count=g.Count()}).ToArray(),spawnPoints=spawn?Enumerable.Range(0,columns).Where(x=>!missing.Contains((rows-1)*columns+x)).Select(x=>new Cell(x,rows-1)).ToArray():new Cell[0],deliveryExits=new Cell[0],activeColors=new[]{0,1,2,3,4,5}};
        }

        static void GravityCases(Report r,Action<bool,string> check) {
            check(GravityMethod!=null&&VerticalMethod!=null&&NewColorMethod!=null&&NextIdField!=null,"Native gravity/reference seams are present");
            void Case(string name,LevelData level,Cell[] removed,bool full,int minimumSteps,int maximumSteps) {
                var actual=new BoardModel(level,81273);var legacy=new BoardModel(level,81273);
                foreach(var cell in removed??new Cell[0]){check(actual.At(cell.x,cell.y)?.family=="gem"&&legacy.At(cell.x,cell.y)?.family=="gem",name+": only plain fixture gems are removed");actual.Pieces.Remove(actual.Key(cell.x,cell.y));legacy.Pieces.Remove(legacy.Key(cell.x,cell.y));}
                var identities=actual.Pieces.Values.ToDictionary(p=>p.id);r.gravityCases++;
                for(int repeat=0;repeat<3;repeat++) {
                    var expected=new TurnResult();var observed=new TurnResult();var oldDirty=new HashSet<int>();var newDirty=new HashSet<int>();
                    if(full){oldDirty=LegacyGravity(legacy,expected);newDirty=(HashSet<int>)GravityMethod.Invoke(actual,new object[]{observed});}
                    else {LegacyVertical(legacy,expected,oldDirty);VerticalMethod.Invoke(actual,new object[]{observed,newDirty});}
                    string expectedJson=JsonUtility.ToJson(expected),actualJson=JsonUtility.ToJson(observed),checkpoint=JsonUtility.ToJson(actual.Checkpoint());
                    check(expectedJson==actualJson,name+": exact old gravity steps/snapshots/routes "+repeat);
                    check(checkpoint==JsonUtility.ToJson(legacy.Checkpoint()),name+": identical occupants/RNG/nextId/moves/goals "+repeat);
                    check(oldDirty.SetEquals(newDirty),name+": exact dirty match-candidate identities "+repeat);
                    check(actual.Pieces.Keys.SequenceEqual(legacy.Pieces.Keys)&&actual.Pieces.Values.Select(p=>p.id).SequenceEqual(legacy.Pieces.Values.Select(p=>p.id)),name+": old remove/reinsert enumeration is preserved "+repeat);
                    check(identities.All(pair=>actual.Pieces.Values.Any(p=>p.id==pair.Key&&ReferenceEquals(p,pair.Value))),name+": existing piece objects are preserved "+repeat);
                    foreach(var step in observed.steps){check(step.before.pieces.Select(p=>p.id).SequenceEqual(step.before.pieces.Select(p=>p.id).OrderBy(id=>id)),name+": before snapshot remains sorted by ID");check(step.after.pieces.Select(p=>p.id).SequenceEqual(step.after.pieces.Select(p=>p.id).OrderBy(id=>id)),name+": after snapshot remains sorted by ID");}
                    if(repeat==0)check(observed.steps.Count>=minimumSteps&&observed.steps.Count<=maximumSteps,name+": expected changing/no-op branch was exercised");
                    actual.Validate();legacy.Validate();r.gravityRows.Add(new GravityRow{name=name+"/"+repeat,fullGravity=full,legacyResultHash=Hash(expectedJson),optimizedResultHash=Hash(actualJson),checkpointHash=Hash(checkpoint),orderedKeys=string.Join(",",actual.Pieces.Keys),legacySteps=expected.steps.Count,optimizedSteps=observed.steps.Count});
                }
            }
            var stone=new ObstacleCell{x=1,y=2,family="stone",hp=1};
            Case("gravity/full_noop",GravityLevel("VERIFY_LAZY_FULL"),null,true,0,0);
            Case("vertical/full_noop",GravityLevel("VERIFY_LAZY_VERTICAL"),null,false,0,0);
            Case("vertical/top_spawn_only",GravityLevel("VERIFY_LAZY_SPAWN"),new[]{new Cell(1,4)},false,1,1);
            Case("vertical/leading_noop_then_lower_and_upper_change",GravityLevel("VERIFY_LAZY_SEGMENTS",blockers:new[]{stone}),new[]{new Cell(1,0),new Cell(1,3)},false,1,1);
            Case("vertical/mask_separated_sections",GravityLevel("VERIFY_LAZY_MASK",new[]{new Cell(1,2)}),new[]{new Cell(1,0),new Cell(1,3)},false,1,1);
            Case("vertical/no_spawn_empty_lower_segment",GravityLevel("VERIFY_LAZY_EMPTY",blockers:new[]{stone},spawn:false),new[]{new Cell(1,0),new Cell(1,1)},false,0,0);
            Case("gravity/sidefeed_beneath_fixed_ceiling",GravityLevel("VERIFY_LAZY_SLIDE",blockers:new[]{new ObstacleCell{x=1,y=1,family="stone",hp=1}}),new[]{new Cell(1,0)},true,2,8);
            Case("gravity/mask_and_fixed_corner_reject_sidefeed",GravityLevel("VERIFY_LAZY_CORNER",new[]{new Cell(0,0)},new[]{new ObstacleCell{x=1,y=1,family="stone",hp=1},new ObstacleCell{x=2,y=0,family="stone",hp=1}}),new[]{new Cell(1,0)},true,0,0);
            Case("vertical/no_spawn_real_fall",GravityLevel("VERIFY_LAZY_CLOSED",spawn:false),new[]{new Cell(2,0),new Cell(2,2)},false,1,1);
        }

        // Checkpoint73 reference algorithms, kept only in this Editor suite.
        // They intentionally retain eager Start snapshots and the old exact
        // remove/reinsert loops; they never run in the application.
        static BoardStep LegacyStart(BoardModel board,float duration,string label)=>new BoardStep{kind="gravity",duration=duration,label=label,before=board.Snapshot()};
        static void LegacyFinish(BoardModel board,BoardStep step,TurnResult result){board.Validate();step.after=board.Snapshot();result.steps.Add(step);}
        static HashSet<int> LegacyGravity(BoardModel board,TurnResult result) {
            var dirty=new HashSet<int>();var crystalLanes=new HashSet<int>(board.Pieces.Values.Where(p=>p.family=="crystal").Select(p=>p.x));
            while(true) {
                LegacyVertical(board,result,dirty);var slide=LegacyStart(board,.2f,"Slide beneath obstacles");var used=new HashSet<int>();var vacancies=new HashSet<int>(board.Active.Where(k=>!board.Pieces.ContainsKey(k)));
                for(int y=0;y<board.Level.rows-1;y++)for(int x=0;x<board.Level.columns;x++) {
                    if(!vacancies.Contains(board.Key(x,y))||board.At(x,y)!=null)continue;
                    for(int side=0;side<2;side++) {
                        int sx=x+(side==0?-1:1);var source=board.At(sx,y+1);var corner=board.At(sx,y);
                        if(source==null||!source.Movable||used.Contains(source.id)||!board.Inside(sx,y)||(corner!=null&&!corner.Movable)||(source.family=="pail"&&board.Exits.Contains(board.Key(sx,y+1))))continue;
                        if(crystalLanes.Contains(x)&&source.family!="gem"&&source.family!="power")continue;
                        board.Pieces.Remove(board.Key(sx,y+1));source.x=x;source.y=y;board.Pieces.Add(board.Key(x,y),source);used.Add(source.id);dirty.Add(source.id);slide.motion.Add(new Motion{id=source.id,fromX=sx,fromY=y+1,toX=x,toY=y});break;
                    }
                }
                if(slide.motion.Count==0)break;LegacyFinish(board,slide,result);
            }
            return dirty;
        }
        static void LegacyVertical(BoardModel board,TurnResult result,HashSet<int> dirty) {
            var step=LegacyStart(board,.62f,"Fall and refill");
            for(int x=0;x<board.Level.columns;x++) {
                int y=0;while(y<board.Level.rows){var at=board.At(x,y);if(!board.Inside(x,y)||(at!=null&&!at.Movable)){y++;continue;}
                    int bottom=y;while(y<board.Level.rows&&board.Inside(x,y)&&(board.At(x,y)==null||board.At(x,y).Movable))y++;int top=y-1;
                    var movable=new List<Piece>();for(int yy=bottom;yy<=top;yy++){var p=board.At(x,yy);if(p!=null){movable.Add(p);board.Pieces.Remove(board.Key(x,yy));}}
                    int dest=bottom;foreach(var p in movable){int from=p.y;p.y=dest++;board.Pieces[board.Key(x,p.y)]=p;if(from!=p.y){step.motion.Add(new Motion{id=p.id,fromX=x,fromY=from,toX=x,toY=p.y});dirty.Add(p.id);}}
                    if(board.Spawns.Contains(board.Key(x,top)))for(int offset=0;dest<=top;offset++,dest++) {
                        int id=(int)NextIdField.GetValue(board);NextIdField.SetValue(board,id+1);var p=new Piece{id=id,x=x,y=dest,family="gem",color=(int)NewColorMethod.Invoke(board,null)};
                        board.Pieces.Add(board.Key(x,dest),p);step.motion.Add(new Motion{id=p.id,fromX=x,fromY=top+1+offset,toX=x,toY=dest,spawned=true});dirty.Add(p.id);
                    }
                }
            }
            if(step.motion.Count>0)LegacyFinish(board,step,result);
        }

        static void GravityBenchmark(Report r,Action<bool,string> check) {
            var level=GravityLevel("VERIFY_LAZY_BENCH");var optimized=new BoardModel(level);var legacy=new BoardModel(level);var fast=(Func<TurnResult,HashSet<int>>)Delegate.CreateDelegate(typeof(Func<TurnResult,HashSet<int>>),optimized,GravityMethod);
            for(int i=0;i<16;i++){fast(new TurnResult());LegacyGravity(legacy,new TurnResult());}
            const int iterations=128;var row=new GravityTiming{name="stable_full_board_noop_gravity",iterations=iterations};var watch=new Stopwatch();
            void Measure(bool lazy){long before=GC.GetAllocatedBytesForCurrentThread();watch.Restart();for(int i=0;i<iterations;i++){var result=new TurnResult();if(lazy)fast(result);else LegacyGravity(legacy,result);check(result.steps.Count==0,"Timed no-op gravity emits no phase "+lazy);}watch.Stop();long allocated=GC.GetAllocatedBytesForCurrentThread()-before;if(lazy){row.optimizedMilliseconds=watch.Elapsed.TotalMilliseconds;row.optimizedAllocatedBytes=allocated;}else{row.legacyMilliseconds=watch.Elapsed.TotalMilliseconds;row.legacyAllocatedBytes=allocated;}}
            Measure(false);Measure(true);if(r.allocationCounterUsable)check(row.optimizedAllocatedBytes<row.legacyAllocatedBytes,"Lazy no-op gravity avoids discarded full-board snapshot allocation");
            check(JsonUtility.ToJson(optimized.Checkpoint())==JsonUtility.ToJson(legacy.Checkpoint())&&optimized.Pieces.Keys.SequenceEqual(legacy.Pieces.Keys),"Repeated optimized/reference no-op gravity keeps identical state and enumeration");r.gravityTimings.Add(row);
        }

        static LevelData Corner() => new LevelData{id="VERIFY_EXISTENCE_DEADLOCK",columns=3,rows=3,globalLevel=1,movesProposal=10,tileSeed=7,
            activeCells=new[]{new Cell(0,0),new Cell(1,0),new Cell(0,1),new Cell(1,1)},spawnPoints=new[]{new Cell(0,1),new Cell(1,1)},deliveryExits=new Cell[0],
            initialTiles=new[]{new GemCell{x=0,y=0,color=0},new GemCell{x=1,y=0,color=0},new GemCell{x=0,y=1,color=0}},
            obstacles=new[]{new ObstacleCell{x=1,y=1,family="crate",hp=3}},goals=new[]{new Goal{family="crate",count=1}},activeColors=new[]{0}};
        static LevelData Pair() => new LevelData{id="VERIFY_EXISTENCE_MASKED_PAIR",columns=3,rows=3,movesProposal=10,tileSeed=7,
            activeCells=new[]{new Cell(0,0),new Cell(1,0)},spawnPoints=new Cell[0],deliveryExits=new Cell[0],
            initialTiles=new[]{new GemCell{x=0,y=0,color=0},new GemCell{x=1,y=0,color=1}},obstacles=new ObstacleCell[0],goals=new Goal[0],activeColors=new[]{0,1}};
        static void Guards(LevelData authored,Report r,Action<bool,string> check,List<KeyValuePair<string,BoardModel>> benchmarks) {
            void Case(BoardModel b,string label){r.guardCases++;Inspect(b,label,r,check);}
            var dead=new BoardModel(Corner());check(!Query(dead)(),"Masked L-shaped gems cannot form a line/square");Case(dead,"guard/no_legal_move");benchmarks.Add(new KeyValuePair<string,BoardModel>("masked_no_legal_move",dead));
            check(dead.InjectReviewPower(0,0,4),"Deadlock control source injected");Case(dead,"guard/power_on_deadlock");
            var turn=dead.Tap(0,0);check(turn.accepted&&dead.Status=="No legal moves"&&dead.Moves==9&&turn.steps.Last().label=="No legal moves","Failed 100-attempt reshuffle retains terminal reason and single move debit");Case(dead,"guard/failed_shuffle");
            var golden=new BoardModel(Pair());golden.InjectReviewPower(0,0,16);golden.InjectReviewPower(1,0,16);
            check(!Query(golden)(),"Unapproved Golden+Golden remains excluded");Case(golden,"guard/golden_golden");
            string old=JsonUtility.ToJson(golden.Checkpoint());turn=golden.Swap(0,0,1,0);
            check(!turn.accepted&&turn.reason=="This combination has no approved rule"&&old==JsonUtility.ToJson(golden.Checkpoint()),"Rejected unapproved combination is atomic");Case(golden,"guard/rejected_combo");
            var mixed=new BoardModel(Pair());mixed.InjectReviewPower(0,0,16);check(Query(mixed)(),"Power plus plain gem remains a legal action");Case(mixed,"guard/power_gem");
            var approved=new BoardModel(Pair());approved.InjectReviewPower(0,0,16);approved.InjectReviewPower(1,0,4);check(Query(approved)(),"Approved Golden+Rocket remains a legal action");Case(approved,"guard/approved_combo");
            var tied=new BoardModel(authored);foreach(var p in tied.Pieces.Values)if(p.family=="gem")p.color=0;
            check(tied.LegalSwaps().Count>1,"Multiple equivalent matching choices are present");Case(tied,"guard/multiple_matching_choices");benchmarks.Add(new KeyValuePair<string,BoardModel>("many_matching_choices",tied));
            foreach(string status in new[]{"Out of moves","No legal moves","Resolution limit","Engine fault"}) {
                var ended=new BoardModel(authored);ended.VerificationForceStatus(status);Case(ended,"guard/"+status);
                old=JsonUtility.ToJson(ended.Checkpoint());var swap=ended.LegalSwaps().First();turn=ended.Swap(swap[0].x,swap[0].y,swap[1].x,swap[1].y);
                check(!turn.accepted&&old==JsonUtility.ToJson(ended.Checkpoint()),status+": query does not reenable ended command");
            }
            var zero=new BoardModel(authored);var saved=zero.Checkpoint();saved.board.moves=0;zero=BoardModel.FromCheckpoint(authored,saved);Case(zero,"guard/zero_budget");
            old=JsonUtility.ToJson(zero.Checkpoint());var legal=zero.LegalSwaps().First();check(!zero.Swap(legal[0].x,legal[0].y,legal[1].x,legal[1].y).accepted&&old==JsonUtility.ToJson(zero.Checkpoint()),"Existence does not bypass zero move budget");
        }

        static void Benchmark(string name,BoardModel board,Report r,Action<bool,string> check) {
            var fast=Query(board);Func<bool> full=()=>board.LegalSwaps().Count>0;bool expected=full();
            for(int i=0;i<16;i++){full();fast();}
            const int iterations=128;var row=new Timing{name=name,iterations=iterations};var watch=new Stopwatch();
            // Alternate ordering by fixture; diagnostics never assert noisy wall-clock speedups.
            void Measure(bool existence) {
                var query=existence?fast:full;int yes=0;long before=GC.GetAllocatedBytesForCurrentThread();watch.Restart();
                for(int i=0;i<iterations;i++)if(query())yes++;
                watch.Stop();long allocated=GC.GetAllocatedBytesForCurrentThread()-before;
                check(yes==(expected?iterations:0),name+": repeated timed query result "+existence);
                if(existence){row.existenceMilliseconds=watch.Elapsed.TotalMilliseconds;row.existenceAllocatedBytes=allocated;}
                else {row.fullListMilliseconds=watch.Elapsed.TotalMilliseconds;row.fullListAllocatedBytes=allocated;}
            }
            if(r.timings.Count%2==0){Measure(false);Measure(true);}else{Measure(true);Measure(false);}
            if(r.allocationCounterUsable)check(row.existenceAllocatedBytes<row.fullListAllocatedBytes,name+": existence avoids complete-list allocation");
            r.timings.Add(row);
        }
    }
}
#endif

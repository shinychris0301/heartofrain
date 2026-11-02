#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using UnityEditor;
using UnityEngine;
namespace HeartOfTheRain.Verification {
    public static class Snapshot79Verification {
        [Serializable] public sealed class ModelRow {public string name,rawHash,finalHash,checkpointHash,dictionaryOrder;}
        [Serializable] public sealed class Transition {public string name,currentHash,checkpoint77Hash,checkpoint78Exception;public bool fixedOutputMatches77;}
        [Serializable] public sealed class TraceRow {public string name,traceHash,rawHash,finalHash,checkpointHash,dictionaryOrder;public int frames;public BoardModel.Snapshot79Work current,control78;}
        [Serializable] public sealed class Pair {
            public int index;public bool controlFirst;public double controlMs,currentMs;public int controlCollections,currentCollections;public string controlHash,currentHash;
            public double[] controlCalls,currentCalls;public int[] controlCallCollections,currentCallCollections;
        }
        [Serializable] public sealed class Timing {
            public string name,mode,traceHash;public int calls,slowerPairs;public double controlMedianMs,currentMedianMs;
            public BoardModel.Snapshot79Work controlDiagnostic,currentDiagnostic;public List<Pair> pairs=new List<Pair>();
        }
        [Serializable] public sealed class Report {
            public string status,utc,archived78ModelSHA256,currentModelSHA256,controlSourceSHA256,proofSourceSHA256,verificationSourceSHA256,baseline78ModelReportSHA256,archivedMethodSHA256,compiledMethodSHA256;
            public string scope="Pinned native Unity snapshot isolation. Exact archived78 Snapshot helper plus existing77 control use live DTOs; primary direct timings exclude construction, trace application/capture, serialization, diagnostics and hashing. Actual command traces retain dictionary order. All signed/slower pairs and completed-collection counts retained. State/ownership and350 raw/final/RNG/order cases are checked. One known invalid-state78 crash is a positive control, not required parity. No allocation-byte, release-memory, Android or universal speedup claim.";
            public int checks,modelCases,transitionCases,ownershipCases,presentationFaultCases;public bool exact78Control,rawParity=true,finalParity=true,checkpointParity=true,dictionaryParity=true;
            public List<string> errors=new List<string>();public List<ModelRow> rows=new List<ModelRow>();public List<Transition> transitions=new List<Transition>();public List<TraceRow> traces=new List<TraceRow>();public List<Timing> timings=new List<Timing>();
        }
        [Serializable] sealed class ArchivedRow {public string name,rawHash,finalHash,checkpointHash,dictionaryOrder;}
        [Serializable] sealed class ArchivedReport {public string status;public List<ArchivedRow> rows;}
        static Report report;static M46Assets assets;const BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static string Hash(string value)=>Snapshot79Proof.Hash(value);
        static string JsonHash(object value)=>Snapshot79Proof.JsonHash(value);
        static string FileHash(string path){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
        static void Check(bool value,string text){report.checks++;if(!value)throw new InvalidOperationException(text);}
        static string Normalize(string value)=>value.Replace("\r\n","\n").Trim();
        static string Method(string text,string marker){int start=text.IndexOf(marker,StringComparison.Ordinal);if(start<0)throw new InvalidOperationException("Missing method "+marker);int end=text.IndexOf('{',start)+1,depth=1;while(depth>0){if(text[end]=='{')depth++;else if(text[end]=='}')depth--;end++;}return text.Substring(start,end-start);}
        static void SourceProof(){
            string path="Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs",archive=Path.GetFullPath("../.verification-cache/Gameplay79/BaselineSources/Unity/"+path);
            report.archived78ModelSHA256=FileHash(archive);report.currentModelSHA256=FileHash(path);
            Check(report.archived78ModelSHA256=="5008fc2d98f4e961133fb0bddb24ee97af0e7ef740d8f2e52a82f3c6a8688d76","Pinned78 BoardModel source bytes");
            string control="Assets/HeartOfTheRain/Verification/Snapshot78Control79.cs",compiled=File.ReadAllText(control);report.controlSourceSHA256=FileHash(control);report.proofSourceSHA256=FileHash("Assets/HeartOfTheRain/Verification/Snapshot79Proof.cs");report.verificationSourceSHA256=FileHash("Assets/HeartOfTheRain/Verification/Editor/Snapshot79Verification.cs");
            string expected=Method(File.ReadAllText(archive),"        BoardSnapshot SnapshotFromScratch()").Replace("SnapshotFromScratch()","SnapshotFromCheckpoint78Snapshot79()");
            const string begin="// BEGIN EXACT78 SnapshotFromScratch",end="// END EXACT78 SnapshotFromScratch";int start=compiled.IndexOf(begin,StringComparison.Ordinal)+begin.Length;int stop=compiled.IndexOf(end,start,StringComparison.Ordinal);string actual=compiled.Substring(start,stop-start);
            report.archivedMethodSHA256=Hash(Normalize(expected));report.compiledMethodSHA256=Hash(Normalize(actual));report.exact78Control=report.archivedMethodSHA256==report.compiledMethodSHA256;Check(report.exact78Control,"Compiled exact78 Snapshot helper binding");
            string prior=Path.GetFullPath("../Verification/Evidence/Gameplay78/Native/ModelWork78.json");report.baseline78ModelReportSHA256=FileHash(prior);Check(report.baseline78ModelReportSHA256=="0fff46626cc978986ca1b4d2c5ed76774857cbe9febae6c846f593e7accbbf8a","Pinned78 native350 model proof");
        }
        static void Corpus(){
            var prior=JsonUtility.FromJson<ArchivedReport>(File.ReadAllText(Path.GetFullPath("../Verification/Evidence/Gameplay78/Native/ModelWork78.json")));
            Check(prior.status=="PASS_NATIVE_MODEL_WORK78"&&prior.rows.Count==350,"Complete frozen78 native command corpus");var expected=prior.rows.ToDictionary(row=>row.name);
            for(int level=0;level<50;level++)foreach(int kind in new[]{-1,4,5,7,11,16,21}){
                var now=ModelWork78Proof.Corpus(assets,level,kind);var old=ModelWork78Proof.Corpus(assets,level,kind);var legacy=ModelWork78Proof.Corpus(assets,level,kind,true);
                Snapshot79Proof.Select(old.model,Snapshot79Proof.Branch.Checkpoint78);var a=now.Solve();var b=old.Solve();var c=legacy.Solve();var frozen=expected[now.name];
                string raw=JsonHash(a),final=JsonHash(now.model.Snapshot()),checkpoint=JsonHash(now.model.Checkpoint()),order=string.Join(";",now.model.Pieces.Select(p=>p.Key+":"+p.Value.id));
                bool r=a.accepted&&b.accepted&&c.accepted&&raw==JsonHash(b)&&raw==JsonHash(c)&&raw==frozen.rawHash;
                bool f=final==JsonHash(old.model.Snapshot())&&final==JsonHash(legacy.model.Snapshot())&&final==frozen.finalHash;
                bool cp=checkpoint==JsonHash(old.model.Checkpoint())&&checkpoint==JsonHash(legacy.model.Checkpoint())&&checkpoint==frozen.checkpointHash;
                bool o=order==string.Join(";",old.model.Pieces.Select(p=>p.Key+":"+p.Value.id))&&order==string.Join(";",legacy.model.Pieces.Select(p=>p.Key+":"+p.Value.id))&&order==frozen.dictionaryOrder;
                report.rawParity&=r;report.finalParity&=f;report.checkpointParity&=cp;report.dictionaryParity&=o;
                Check(r,"Current79/exact78/exact77/frozen78 raw command "+now.name);Check(f,"Snapshot final state "+now.name);Check(cp,"Snapshot RNG/checkpoint "+now.name);Check(o,"Snapshot dictionary order "+now.name);
                report.rows.Add(new ModelRow{name=now.name,rawHash=raw,finalHash=final,checkpointHash=checkpoint,dictionaryOrder=order});report.modelCases++;
            }
        }
        static void Ownership(BoardModel board,string name){
            var entries=board.Pieces.ToArray();var goals=board.Goals.ToArray();Snapshot79Proof.Select(board,Snapshot79Proof.Branch.Checkpoint77);var prior=board.Snapshot();string expected=JsonUtility.ToJson(prior);
            Snapshot79Proof.Select(board,Snapshot79Proof.Branch.Current79);var now=board.Snapshot();var again=board.Snapshot();
            Check(expected==JsonUtility.ToJson(now)&&expected==JsonUtility.ToJson(again),"Exact77 stable snapshot fields "+name);
            Check(entries.Select(p=>p.Key).SequenceEqual(board.Pieces.Keys)&&entries.All(p=>ReferenceEquals(p.Value,board.Pieces[p.Key]))&&goals.SequenceEqual(board.Goals),"Snapshot preserves source dictionaries "+name);
            Check(now.pieces.All(p=>!entries.Any(e=>ReferenceEquals(e.Value,p)))&&now.pieces.All(p=>!prior.pieces.Contains(p)&&!again.pieces.Contains(p))&&now.goals.All(g=>!prior.goals.Contains(g)&&!again.goals.Contains(g)),"Snapshot owns each copied body/goal "+name);
            if(now.pieces.Length>0){now.pieces[0].x+=700;now.pieces[0].family="snapshot_only";}if(now.goals.Length>0)now.goals[0].count+=700;
            Check(expected==JsonUtility.ToJson(board.Snapshot())&&expected==JsonUtility.ToJson(prior)&&expected==JsonUtility.ToJson(again),"Mutation cannot alias source or prior snapshot "+name);
            Check(((Piece[])typeof(BoardModel).GetField("snapshotPieces",Private).GetValue(board)).All(p=>p==null)&&((Piece[])typeof(BoardModel).GetField("snapshotMerge",Private).GetValue(board)).All(p=>p==null),"Scratch releases live body references "+name);report.ownershipCases++;
        }
        static BoardModel Diagnostic(Snapshot79Proof.Branch branch){
            var board=new BoardModel(new LevelData{id="snapshot79_diagnostic",columns=3,rows=3,movesProposal=5,tileSeed=1,activeCells=new[]{new Cell(0,0),new Cell(1,0),new Cell(2,0)},initialTiles=new[]{new GemCell{x=0,y=0,color=0},new GemCell{x=1,y=0,color=1},new GemCell{x=2,y=0,color=2}},obstacles=Array.Empty<ObstacleCell>(),goals=Array.Empty<Goal>()});
            Snapshot79Proof.Select(board,branch);return board;
        }
        static string Error(Action action){try{action();return "OK";}catch(Exception e){return e.GetType().FullName;}}
        static string FullError(Action action){try{action();return "OK";}catch(Exception e){return e.GetType().FullName+":"+e.Message;}}
        static void DuplicateTransition(int removeKey){
            var now=Diagnostic(Snapshot79Proof.Branch.Current79);var old=Diagnostic(Snapshot79Proof.Branch.Checkpoint78);var legacy=Diagnostic(Snapshot79Proof.Branch.Checkpoint77);
            foreach(var b in new[]{now,old,legacy})b.Pieces[1].id=1;
            string expected=JsonHash(legacy.Snapshot());Check(JsonHash(now.Snapshot())==expected&&JsonHash(old.Snapshot())==expected,"All branches preserve stable duplicate snapshot before shrink");
            Check(FullError(()=>now.Validate())==FullError(()=>legacy.Validate()),"Duplicate validation exception type/message unchanged");
            foreach(var b in new[]{now,old,legacy})b.Pieces.Remove(removeKey);
            string oldError=Error(()=>old.Snapshot()),current=JsonHash(now.Snapshot()),prior=JsonHash(legacy.Snapshot());
            Check(oldError==typeof(NullReferenceException).FullName,"Exact78 positive control reproduces duplicate-to-shrink crash");Check(current==prior,"Current79 returns exact77 output after duplicate shrink");
            Check(JsonHash(now.Snapshot())==prior,"Repaired rank cache remains valid on repeat");Ownership(now,"duplicate_remove_"+removeKey);
            report.transitions.Add(new Transition{name="duplicate_remove_"+removeKey,currentHash=current,checkpoint77Hash=prior,checkpoint78Exception=oldError,fixedOutputMatches77=current==prior});report.transitionCases++;
        }
        static void SnapshotControls(){
            DuplicateTransition(0);DuplicateTransition(1);
            var board=new BoardModel(JsonUtility.FromJson<LevelData>(assets.levels[3].text));Ownership(board,"initial");var pieces=board.Pieces.Values.Take(3).ToArray();
            var replacement=pieces[0].Copy();replacement.color=(replacement.color+1)%6;board.Pieces[board.Key(replacement.x,replacement.y)]=replacement;Ownership(board,"same_id_new_object");
            int id=replacement.id;replacement.id=pieces[1].id;pieces[1].id=id;Ownership(board,"swapped_mutable_ids");
            int key=board.Key(pieces[2].x,pieces[2].y);board.Pieces.Remove(key);var added=pieces[2].Copy();added.id=int.MaxValue;board.Pieces.Add(key,added);Ownership(board,"same_count_new_id_reinsert");
            added.id=replacement.id;Ownership(board,"duplicate_stable_fallback");added.id=int.MinValue;Ownership(board,"negative_identity_repair");
            typeof(BoardModel).GetField("snapshotGeneration",Private).SetValue(board,-1);Ownership(board,"generation_reset");
            var entries=board.Pieces.Take(11).ToArray();foreach(var pair in entries)board.Pieces.Remove(pair.Key);Ownership(board,"shrink");foreach(var pair in entries.Reverse())board.Pieces.Add(pair.Key,pair.Value);Ownership(board,"reverse_regrow");
            board.Pieces.Clear();for(int i=0;i<300;i++)board.Pieces.Add(i,new Piece{id=300-i,x=i,y=0,color=i%6,family="gem"});Ownership(board,"scratch_growth_300");
            Snapshot79Proof.Select(board,Snapshot79Proof.Branch.Checkpoint78);board.Snapshot();Snapshot79Proof.Select(board,Snapshot79Proof.Branch.Current79);Ownership(board,"switch_after_control_growth");
            board.Pieces.Clear();board.Goals.Clear();Ownership(board,"empty");
            var culture=Thread.CurrentThread.CurrentCulture;try{foreach(string locale in new[]{"en-US","fr-FR","tr-TR","sv-SE"}){Thread.CurrentThread.CurrentCulture=CultureInfo.GetCultureInfo(locale);var b=new BoardModel(JsonUtility.FromJson<LevelData>(assets.levels[3].text));foreach(string family in new[]{"a","A","I","\u0131","\u00e9","e\u0301"})b.Goals[family]=0;Ownership(b,"goal_culture_"+locale);}}finally{Thread.CurrentThread.CurrentCulture=culture;}
            var repaired=Diagnostic(Snapshot79Proof.Branch.Current79);repaired.VerificationMeasureSnapshot79=true;repaired.Pieces[1].id=1;repaired.Snapshot();repaired.Pieces.Remove(1);repaired.Snapshot();repaired.Snapshot();var w=repaired.VerificationGetSnapshot79();
            Check(w.calls==3&&w.rebuilds==2&&w.cacheHits==1&&w.nonReusableBuilds==1,"Actual duplicate-invalid cache rebuild/hit counters");
            // Public diagnostic snapshots also accept invalid duplicate/negative
            // identities. Vary membership/order on one cache, retaining77's
            // stable output even when the distinct-ID count matches a shrink.
            var diagnostic=Diagnostic(Snapshot79Proof.Branch.Current79);var random=new System.Random(79031);
            for(int iteration=0;iteration<64;iteration++){
                diagnostic.Pieces.Clear();int count=random.Next(1,138);
                for(int i=0;i<count;i++)diagnostic.Pieces.Add(i,new Piece{id=iteration%3==0?random.Next(-7,10):count-i,x=i,y=0,color=i%6,family="gem"});
                Ownership(diagnostic,"deterministic_mutable_identity_sequence_"+iteration);
            }
            var failed=Diagnostic(Snapshot79Proof.Branch.Current79);failed.Snapshot();var body=failed.Pieces[1];failed.Pieces[1]=null;
            Check(Error(()=>failed.Snapshot())==typeof(NullReferenceException).FullName,"Null body keeps original Snapshot exception type");failed.Pieces[1]=body;Ownership(failed,"same_instance_repair_after_null_snapshot");
        }
        static double Median(IEnumerable<double> values){var a=values.OrderBy(v=>v).ToArray();return (a[(a.Length-1)/2]+a[a.Length/2])*.5;}
        static void PresentationFaults(){
            foreach(string status in new[]{"Playing","Out of moves","No legal moves","Resolution limit"}){
                var board=Diagnostic(Snapshot79Proof.Branch.Current79);if(status!="Playing")board.VerificationForceStatus(status);
                string before=JsonUtility.ToJson(board.Snapshot());var pieces=board.Pieces.ToArray();var goals=board.Goals.ToArray();
                board.RecordPresentationFault("playback compile failed");var after=board.Snapshot();after.status=status;
                Check(board.Status=="Engine fault"&&board.FaultDetail=="playback compile failed","Presentation failure supersedes "+status);
                Check(JsonUtility.ToJson(after)==before&&pieces.All(p=>ReferenceEquals(p.Value,board.Pieces[p.Key]))&&goals.SequenceEqual(board.Goals),"Presentation failure preserves pieces/goals/moves/turn "+status);
                board.RecordPresentationFault("later diagnosis");Check(board.FaultDetail=="playback compile failed","Repeated presentation failure preserves first diagnosis "+status);report.presentationFaultCases++;
            }
            var faulted=Diagnostic(Snapshot79Proof.Branch.Current79);faulted.RecordFault("command failure");faulted.RecordPresentationFault("later presentation failure");Check(faulted.Status=="Engine fault"&&faulted.FaultDetail=="command failure","Existing command fault diagnosis is preserved");report.presentationFaultCases++;
            var won=Diagnostic(Snapshot79Proof.Branch.Current79);Check(won.InjectReviewPower(0,0,4),"Winning presentation-fault fixture power installed");var turn=won.Tap(0,0);Check(turn.accepted&&won.Status=="Won","Winning fixture reaches Won through an accepted command");string checkpoint=JsonUtility.ToJson(won.Checkpoint());
            won.RecordPresentationFault("post-win presentation failure");won.RecordPresentationFault("retry");Check(won.Status=="Won"&&won.FaultDetail==null&&JsonUtility.ToJson(won.Checkpoint())==checkpoint,"Presentation failure preserves model win and checkpoint for receipt recovery");report.presentationFaultCases++;
        }
        static void VerifyDirect(Snapshot79Proof.Trace trace,Snapshot79Proof.DirectSample sample,string label){
            Check(sample.values.Length==trace.frames.Length,"Direct snapshot call count "+label);
            for(int i=0;i<sample.values.Length;i++)Check(JsonUtility.ToJson(sample.values[i])==JsonUtility.ToJson(trace.frames[i].state),"Direct exact source fields "+label+"/"+i);
        }
        static void Benchmark(Snapshot79Proof.Trace trace){
            foreach(var frame in trace.frames){Check(frame.state.pieces.Select(p=>p.id).SequenceEqual(frame.state.pieces.OrderBy(p=>p.id).Select(p=>p.id)),"Expected snapshot fixture is sorted by actual identity "+trace.name);Check(frame.keys.Length==frame.state.pieces.Length&&frame.order.OrderBy(i=>i).SequenceEqual(Enumerable.Range(0,frame.state.pieces.Length)),"Fixture dictionary mapping retains every body once "+trace.name);}
            string inputHash=Snapshot79Proof.TraceHash(trace);
            foreach(string mode in new[]{"cold","warm"}){
                var row=new Timing{name=trace.name,mode=mode,traceHash=inputHash,calls=trace.frames.Length};
                var old=Snapshot79Proof.PrepareDirect(trace,Snapshot79Proof.Branch.Checkpoint78);var now=Snapshot79Proof.PrepareDirect(trace,Snapshot79Proof.Branch.Current79);
                if(mode=="warm")for(int i=0;i<2;i++){Snapshot79Proof.MeasureDirect(old);Snapshot79Proof.MeasureDirect(now);}
                for(int i=0;i<12;i++){
                    if(mode=="cold"){old=Snapshot79Proof.PrepareDirect(trace,Snapshot79Proof.Branch.Checkpoint78);now=Snapshot79Proof.PrepareDirect(trace,Snapshot79Proof.Branch.Current79);}
                    var pair=new Pair{index=i,controlFirst=i%2==0};Snapshot79Proof.DirectSample a,b;
                    if(pair.controlFirst){a=Snapshot79Proof.MeasureDirect(old);b=Snapshot79Proof.MeasureDirect(now);}else{b=Snapshot79Proof.MeasureDirect(now);a=Snapshot79Proof.MeasureDirect(old);}
                    pair.controlMs=a.totalMilliseconds;pair.currentMs=b.totalMilliseconds;pair.controlCalls=a.milliseconds;pair.currentCalls=b.milliseconds;pair.controlCallCollections=a.completedCollections;pair.currentCallCollections=b.completedCollections;pair.controlCollections=a.completedCollections.Sum();pair.currentCollections=b.completedCollections.Sum();pair.controlHash=Snapshot79Proof.ResultHash(a);pair.currentHash=Snapshot79Proof.ResultHash(b);
                    Check(pair.controlHash==pair.currentHash,"Primary direct paired output "+trace.name+"/"+mode+"/"+i);VerifyDirect(trace,a,"78_"+trace.name);VerifyDirect(trace,b,"79_"+trace.name);
                    Check(a.work.calls==0&&b.work.calls==0,"Primary snapshot diagnostics disabled");row.pairs.Add(pair);
                }
                var oldDiagnostic=Snapshot79Proof.PrepareDirect(trace,Snapshot79Proof.Branch.Checkpoint78);var currentDiagnostic=Snapshot79Proof.PrepareDirect(trace,Snapshot79Proof.Branch.Current79);
                if(mode=="warm"){Snapshot79Proof.MeasureDirect(oldDiagnostic);Snapshot79Proof.MeasureDirect(currentDiagnostic);}
                var da=Snapshot79Proof.MeasureDirect(oldDiagnostic,true);var db=Snapshot79Proof.MeasureDirect(currentDiagnostic,true);row.controlDiagnostic=da.work;row.currentDiagnostic=db.work;
                Check(da.work.calls==trace.frames.Length&&db.work.calls==trace.frames.Length&&da.work.cacheHits+da.work.rebuilds==da.work.calls&&db.work.cacheHits+db.work.rebuilds==db.work.calls,"Actual direct branch counts "+trace.name+"/"+mode);
                Check(da.work.cacheHits==db.work.cacheHits&&da.work.rebuilds==db.work.rebuilds&&da.work.copiedPieces==db.work.copiedPieces&&da.work.rebuiltPieces==db.work.rebuiltPieces,"Valid-state cache decisions preserved "+trace.name+"/"+mode);
                if(Snapshot79Proof.SyntheticNames.Contains(trace.name)){int rebuilds=trace.name=="L4_stable32"||trace.name=="L4_reordered_dictionary32"?(mode=="cold"?1:0):32;Check(db.work.rebuilds==rebuilds&&db.work.cacheHits==32-rebuilds,"Stable/churn counters discriminate actual paths "+trace.name+"/"+mode);}
                Check(Snapshot79Proof.TraceHash(trace)==inputHash,"Benchmark inputs remain immutable "+trace.name);row.controlMedianMs=Median(row.pairs.Select(p=>p.controlMs));row.currentMedianMs=Median(row.pairs.Select(p=>p.currentMs));row.slowerPairs=row.pairs.Count(p=>p.currentMs>p.controlMs);report.timings.Add(row);
            }
        }
        static void Traces(){
            foreach(string name in ModelWork78Proof.BenchmarkNames){
                var current=Snapshot79Proof.Capture(assets,name);var old=Snapshot79Proof.Capture(assets,name,Snapshot79Proof.Branch.Checkpoint78);
                Check(current.rawHash==old.rawHash&&current.finalHash==old.finalHash&&current.checkpointHash==old.checkpointHash&&current.dictionaryOrder==old.dictionaryOrder,"Diagnostic command parity "+name);
                string hash=Snapshot79Proof.TraceHash(current);Check(hash==Snapshot79Proof.TraceHash(old),"Actual Snapshot-call state/order sequence parity "+name);
                Check(current.work.calls==current.frames.Length&&old.work.calls==old.frames.Length,"Actual command counters cover each captured Snapshot "+name);
                Check(current.work.calls==old.work.calls&&current.work.copiedPieces==old.work.copiedPieces&&current.work.cacheHits==old.work.cacheHits&&current.work.rebuilds==old.work.rebuilds,"Valid command rank-cache decision parity "+name);
                report.traces.Add(new TraceRow{name=name,traceHash=hash,rawHash=current.rawHash,finalHash=current.finalHash,checkpointHash=current.checkpointHash,dictionaryOrder=current.dictionaryOrder,frames=current.frames.Length,current=current.work,control78=old.work});Benchmark(current);
            }
            foreach(string name in Snapshot79Proof.SyntheticNames)Benchmark(Snapshot79Proof.Synthetic(assets,name));
        }
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o")};try{SourceProof();assets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset").boards;Check(assets.levels.Length==50,"All50 authored levels");Corpus();SnapshotControls();PresentationFaults();Traces();Check(report.modelCases==350&&report.transitions.Count==2&&report.presentationFaultCases==6&&report.traces.Count==8&&report.timings.Count==24,"Complete snapshot79 scope");}catch(Exception e){report.errors.Add(e.ToString());}
            report.status=report.errors.Count==0?"PASS_NATIVE_SNAPSHOT79":"FAIL_NATIVE_SNAPSHOT79";string root=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY79_OUTPUT");if(string.IsNullOrEmpty(root))root=Path.GetFullPath("../Verification/Evidence/Gameplay79");string dir=Path.Combine(root,"Native");Directory.CreateDirectory(dir);File.WriteAllText(Path.Combine(dir,"Snapshot79.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif

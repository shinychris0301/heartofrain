#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using UnityEditor;
using UnityEngine;
using UnityEngine.Profiling;
using UnityEngine.Scripting;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;

namespace HeartOfTheRain.Verification {
    public static class ModelCommandPerformanceVerification {
        [Serializable] public sealed class Row {
            public string name,turnHash,finalHash,baselineTurnHash,baselineFinalHash,checkpointHash,dictionaryOrder,legacyTurnHash,legacyFinalHash,legacyCheckpointHash,legacyDictionaryOrder;
            public int steps,matchSteps,powerSteps;public double milliseconds;public long allocatedBytes;
            public double legacyMilliseconds;public long legacyAllocatedBytes;
            public BoardModel.ModelWork work,legacyWork;
        }
        [Serializable] public sealed class Repeated {
            public string name;public int iterations;public double medianMs,p95Ms,maxMs;public long medianAllocatedBytes;
            public double legacyMedianMs,legacyP95Ms,legacyMaxMs;public long legacyMedianAllocatedBytes;
            public List<Row> samples=new List<Row>();
            public List<Row> legacySamples=new List<Row>();
        }
        [Serializable] public sealed class SnapshotSample {
            public double batchMilliseconds,perSnapshotMs;public long allocatedBytes;public string finalHash;
        }
        [Serializable] public sealed class SnapshotRepeated {
            public string name;public int pieces,goals,batch,iterations;
            public double medianMs,p95Ms,maxMs,legacyMedianMs,legacyP95Ms,legacyMaxMs;
            public List<SnapshotSample> samples=new List<SnapshotSample>(),legacySamples=new List<SnapshotSample>();
        }
        [Serializable] public sealed class Report {
            public string status,utc,baselineReportPath,baselineReportSHA256;
            public string scope="Native Unity Editor model-only command measurements paired with the exact archived74 Snapshot expression; fixture creation/legal search/injection, final hashing and report serialization are outside the measured command. Stage times are inclusive and cannot be summed. Instrumentation adds overhead; Mono heap allocation fallback temporarily disables GC for both paired command spans. CPU/allocation results are descriptive, not Android frame or touch latency.";
            public int checks,modelCases,snapshotControls;public bool rawTurnParity=true,finalSnapshotParity=true,pairedCheckpointParity=true,pairedDictionaryParity=true,allocationCounterUsable,snapshotControlMatchesArchived74;public long allocationPositiveControlBytes,threadAllocationPositiveControlBytes,heapAllocationPositiveControlBytes;
            public string allocationCounter,baselineModelSourceSHA256;
            public List<string> errors=new List<string>();public List<Row> rows=new List<Row>();public List<Repeated> repeated=new List<Repeated>();public List<SnapshotRepeated> snapshotRepeated=new List<SnapshotRepeated>();
        }
        [Serializable] sealed class BaselineRow {public string name,turnHash,finalHash;}
        [Serializable] sealed class Baseline {public string status;public int baselineModelCases;public List<BaselineRow> modelParity;}
        static bool heapCounter;
        static string Hash(byte[] bytes){using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
        static string Hash(string text)=>Hash(Encoding.UTF8.GetBytes(text));
        static string Counts(BoardModel.ModelWork w)=>string.Join(",",new[]{w.snapshotCalls,w.copiedPieces,w.validationCalls,w.footprintCalls,w.matchCalls,w.gravityCalls,w.verticalCalls,w.activationCalls,w.planningCalls,w.legalQueryCalls});
        static long Counter()=>heapCounter?Profiler.GetMonoUsedSizeLong():GC.GetAllocatedBytesForCurrentThread();

        static void AllocationControl(Report report) {
            heapCounter=false;long before=GC.GetAllocatedBytesForCurrentThread();var block=new byte[65536];report.threadAllocationPositiveControlBytes=GC.GetAllocatedBytesForCurrentThread()-before;GC.KeepAlive(block);
            if(report.threadAllocationPositiveControlBytes>=65536){report.allocationCounterUsable=true;report.allocationCounter="GC.GetAllocatedBytesForCurrentThread";report.allocationPositiveControlBytes=report.threadAllocationPositiveControlBytes;return;}
            var mode=GarbageCollector.GCMode;
            try{GC.Collect();GarbageCollector.GCMode=GarbageCollector.Mode.Disabled;before=Profiler.GetMonoUsedSizeLong();block=new byte[65536];report.heapAllocationPositiveControlBytes=Profiler.GetMonoUsedSizeLong()-before;GC.KeepAlive(block);}catch(Exception){report.heapAllocationPositiveControlBytes=-1;}finally{GarbageCollector.GCMode=mode;}
            if(report.heapAllocationPositiveControlBytes>=65536){heapCounter=true;report.allocationCounterUsable=true;report.allocationCounter="MonoUsedHeapWithGCDisabled";report.allocationPositiveControlBytes=report.heapAllocationPositiveControlBytes;}else report.allocationCounter="UNAVAILABLE";
        }

        static void VerifySnapshotControl(Report report,Action<bool,string> check) {
            var path=Path.GetFullPath(Path.Combine(Application.dataPath,"../../.verification-cache/Gameplay75/BaselineSources/Unity/Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs"));var original=File.ReadAllText(path);report.baselineModelSourceSHA256=Hash(File.ReadAllBytes(path));
            check(report.baselineModelSourceSHA256=="524f758ff5b2bce3c81a85e6a67c743116e36436f6ee7882d2227946bd7054be","Snapshot control source is exact archived74 model");
            var oldExpression=Regex.Match(original,@"public BoardSnapshot Snapshot\(\)\{return (.*?);\}",RegexOptions.Singleline);
            var current=File.ReadAllText(Path.Combine(Application.dataPath,"HeartOfTheRain/M46/Runtime/BoardModel.cs"));var control=Regex.Match(current,@"BoardSnapshot LegacySnapshot\(\)=>([^\r\n]+);");
            report.snapshotControlMatchesArchived74=oldExpression.Success&&control.Success&&oldExpression.Groups[1].Value==control.Groups[1].Value;
            check(report.snapshotControlMatchesArchived74,"Development snapshot control expression exactly matches archived74 LINQ body");
        }

        static void SnapshotControls(GameplayUIAssets ui,Report report,Action<bool,string> check) {
            void Inspect(BoardModel board,string name) {
                report.snapshotControls++;var occupants=board.Pieces.ToArray();var goals=board.Goals.ToArray();board.VerificationUseLegacySnapshot=true;var legacy=board.Snapshot();string expected=JsonUtility.ToJson(legacy);board.VerificationUseLegacySnapshot=false;var optimized=board.Snapshot();
                check(expected==JsonUtility.ToJson(optimized),name+": exact stable snapshot field/order parity");
                check(occupants.Select(p=>p.Key).SequenceEqual(board.Pieces.Keys)&&occupants.All(p=>ReferenceEquals(p.Value,board.Pieces[p.Key]))&&goals.SequenceEqual(board.Goals),name+": snapshot does not reorder or mutate live dictionaries");
                check(optimized.pieces.All(p=>!occupants.Any(o=>ReferenceEquals(p,o.Value)))&&optimized.goals.All(g=>!legacy.goals.Any(o=>ReferenceEquals(g,o))),name+": every returned mutable body/goal is detached");
                if(optimized.pieces.Length>0){optimized.pieces[0].x+=100;optimized.pieces[0].family="verification_snapshot_only";check(!ReferenceEquals(optimized.pieces,legacy.pieces),name+": nonempty piece arrays are independently owned");}
                if(optimized.goals.Length>0){optimized.goals[0].count+=100;check(!ReferenceEquals(optimized.goals,legacy.goals),name+": nonempty goal arrays are independently owned");}
                check(expected==JsonUtility.ToJson(board.Snapshot())&&expected==JsonUtility.ToJson(legacy),name+": later scratch reuse and caller mutation do not alter prior/source state");
            }
            foreach(int index in new[]{0,3,29,47,49})Inspect(new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[index].text)),"snapshot/L"+(index+1));
            var level=JsonUtility.FromJson<LevelData>(ui.boards.levels[0].text);var changing=new BoardModel(level);var removed=changing.Pieces.Where(p=>p.Value.family=="gem").Take(7).ToArray();foreach(var p in removed)changing.Pieces.Remove(p.Key);Inspect(changing,"snapshot/shrunk_count");foreach(var p in removed)changing.Pieces.Add(p.Key,p.Value);Inspect(changing,"snapshot/regrown_reinserted_count");
            var tied=new BoardModel(level);var pair=tied.Pieces.Values.Where(p=>p.family=="gem").Take(2).ToArray();pair[1].id=pair[0].id;Inspect(tied,"snapshot/stable_equal_id_diagnostic");
            var empty=new BoardModel(level);empty.Pieces.Clear();empty.Goals.Clear();Inspect(empty,"snapshot/empty_diagnostic");
            var culture=Thread.CurrentThread.CurrentCulture;
            try{foreach(string name in new[]{"en-US","tr-TR","fr-FR","sv-SE"}){Thread.CurrentThread.CurrentCulture=CultureInfo.GetCultureInfo(name);var board=new BoardModel(level);foreach(string family in new[]{"é","e\u0301","a","A","I","ı"})board.Goals[family]=0;Inspect(board,"snapshot/culture_"+name);}}finally{Thread.CurrentThread.CurrentCulture=culture;}
        }

        public static void RunBaseline()=>Run();
        public static void Run() {
            var report=new Report{utc=DateTime.UtcNow.ToString("o")};
            void Check(bool ok,string label){report.checks++;if(!ok&&report.errors.Count<100)report.errors.Add(label);}
            try {
                var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");Check(ui!=null&&ui.boards.levels.Length==50,"Approved50 level bindings");
                report.baselineReportPath=Path.GetFullPath(Path.Combine(Application.dataPath,"../../Verification/Evidence/Gameplay74/Native/LegalSwapExistence.json"));var bytes=File.ReadAllBytes(report.baselineReportPath);report.baselineReportSHA256=Hash(bytes);
                var baseline=JsonUtility.FromJson<Baseline>(File.ReadAllText(report.baselineReportPath));Check(baseline.status=="PASS_NATIVE_LEGAL_SWAP_EXISTENCE74"&&baseline.baselineModelCases==350&&baseline.modelParity.Count==350,"Frozen74 native350 paired model hashes available");var expected=baseline.modelParity.ToDictionary(r=>r.name);
                VerifySnapshotControl(report,Check);AllocationControl(report);
                for(int level=0;level<50;level++)foreach(int kind in new[]{-1,4,5,7,11,16,21}) {
                    var data=JsonUtility.FromJson<LevelData>(ui.boards.levels[level].text);var row=Measure(data,kind,report.allocationCounterUsable,true);var legacy=Measure(data,kind,report.allocationCounterUsable,true,true);var old=expected[row.name];row.baselineTurnHash=old.turnHash;row.baselineFinalHash=old.finalHash;
                    row.legacyTurnHash=legacy.turnHash;row.legacyFinalHash=legacy.finalHash;row.legacyCheckpointHash=legacy.checkpointHash;row.legacyDictionaryOrder=legacy.dictionaryOrder;row.legacyMilliseconds=legacy.milliseconds;row.legacyAllocatedBytes=legacy.allocatedBytes;row.legacyWork=legacy.work;
                    bool raw=row.turnHash==old.turnHash,final=row.finalHash==old.finalHash;report.rawTurnParity&=raw;report.finalSnapshotParity&=final;Check(raw&&final,row.name+": exact74 raw turn and final state");Check(row.work.snapshotCalls>0&&row.work.validationCalls>0,row.name+": snapshot/validation work is counted");
                    Check(row.work.planningCalls==row.powerSteps,row.name+": each actual source action owns one measured plan");Check(row.work.snapshotMs>=0&&row.work.validationMs>=row.work.footprintMs,row.name+": inclusive stages have finite nonnegative bounds");report.modelCases++;report.rows.Add(row);
                    bool checkpoint=row.checkpointHash==legacy.checkpointHash,order=row.dictionaryOrder==legacy.dictionaryOrder;report.pairedCheckpointParity&=checkpoint;report.pairedDictionaryParity&=order;
                    report.rawTurnParity&=row.turnHash==legacy.turnHash;report.finalSnapshotParity&=row.finalHash==legacy.finalHash;
                    Check(row.turnHash==legacy.turnHash&&row.finalHash==legacy.finalHash&&checkpoint&&order,row.name+": exact paired74-control turn/final/RNG/checkpoint/dictionary order");Check(Counts(row.work)==Counts(legacy.work),row.name+": snapshot optimization preserves deterministic operation counts");
                }
                foreach(var spec in new[]{new[]{3,-1},new[]{47,16},new[]{0,21},new[]{25,7}}) {
                    var level=JsonUtility.FromJson<LevelData>(ui.boards.levels[spec[0]].text);int kind=spec[1];
                    var unmeasured=Measure(level,kind,report.allocationCounterUsable,false);var measured=Measure(level,kind,report.allocationCounterUsable,true);Check(unmeasured.turnHash==measured.turnHash&&unmeasured.finalHash==measured.finalHash,"Diagnostics preserve full command outputs "+measured.name);Check(Counts(unmeasured.work)=="0,0,0,0,0,0,0,0,0,0","Disabled diagnostics retain zero counters "+measured.name);
                    var repeated=new Repeated{name=measured.name,iterations=20};
                    for(int warm=0;warm<3;warm++){Measure(level,kind,false,true);Measure(level,kind,false,true,true);}
                    for(int iteration=0;iteration<repeated.iterations;iteration++) {
                        Row row,legacy;
                        if(iteration%2==0){legacy=Measure(level,kind,report.allocationCounterUsable,true,true);row=Measure(level,kind,report.allocationCounterUsable,true);}else{row=Measure(level,kind,report.allocationCounterUsable,true);legacy=Measure(level,kind,report.allocationCounterUsable,true,true);}
                        Check(row.turnHash==measured.turnHash&&row.finalHash==measured.finalHash&&Counts(row.work)==Counts(measured.work),row.name+": deterministic repeated output/stage counts "+iteration);
                        Check(row.turnHash==legacy.turnHash&&row.finalHash==legacy.finalHash&&row.checkpointHash==legacy.checkpointHash&&row.dictionaryOrder==legacy.dictionaryOrder&&Counts(row.work)==Counts(legacy.work),row.name+": alternating paired legacy/control semantics "+iteration);repeated.samples.Add(row);repeated.legacySamples.Add(legacy);
                    }
                    var times=repeated.samples.Select(r=>r.milliseconds).OrderBy(t=>t).ToArray();repeated.medianMs=times[times.Length/2];repeated.p95Ms=times[(int)((times.Length-1)*.95)];repeated.maxMs=times.Last();repeated.medianAllocatedBytes=repeated.samples.Select(r=>r.allocatedBytes).OrderBy(n=>n).ElementAt(repeated.iterations/2);report.repeated.Add(repeated);
                    times=repeated.legacySamples.Select(r=>r.milliseconds).OrderBy(t=>t).ToArray();repeated.legacyMedianMs=times[times.Length/2];repeated.legacyP95Ms=times[(int)((times.Length-1)*.95)];repeated.legacyMaxMs=times.Last();repeated.legacyMedianAllocatedBytes=repeated.legacySamples.Select(r=>r.allocatedBytes).OrderBy(n=>n).ElementAt(repeated.iterations/2);
                    SnapshotBenchmark(level,kind,report,Check);
                }
                SnapshotControls(ui,report,Check);Check(report.snapshotControls==13,"All13 snapshot ownership/order/culture controls ran");
                Check(report.modelCases==350&&report.rawTurnParity&&report.finalSnapshotParity&&report.pairedCheckpointParity&&report.pairedDictionaryParity,"All350 model commands preserve frozen74 hashes and paired durable/order state");
            }catch(Exception error){report.errors.Add(error.ToString());}
            report.status=report.errors.Count==0?"PASS_NATIVE_MODEL_COMMANDS75":"FAIL_NATIVE_MODEL_COMMANDS75";string folder=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY75_OUTPUT");if(string.IsNullOrEmpty(folder))folder=Path.GetFullPath("../Verification/Evidence/Gameplay75");folder=Path.Combine(folder,"Native");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"ModelCommands.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.errors.Count==0?0:1);
        }

        static void SnapshotBenchmark(LevelData level,int kind,Report report,Action<bool,string> check) {
            var board=new BoardModel(level);TurnResult result;
            if(kind<0){var move=board.LegalSwaps().First();result=board.Swap(move[0].x,move[0].y,move[1].x,move[1].y);}
            else{var piece=board.Pieces.Values.First(p=>p.family=="gem");int x=piece.x,y=piece.y;board.InjectReviewPower(x,y,kind);result=board.Tap(x,y);}
            check(result.accepted,"Isolated Snapshot benchmark command accepted");var expected=Hash(JsonUtility.ToJson(board.Snapshot()));var record=new SnapshotRepeated{name="L"+level.globalLevel+"_"+(kind<0?"match":"power"+kind)+"/after_command",pieces=board.Pieces.Count,goals=board.Goals.Count,batch=64,iterations=20};
            for(int warm=0;warm<2;warm++){SnapshotBatch(board,false,record.batch,false);SnapshotBatch(board,true,record.batch,false);}
            for(int iteration=0;iteration<record.iterations;iteration++){
                SnapshotSample sample,legacy;if(iteration%2==0){legacy=SnapshotBatch(board,true,record.batch,report.allocationCounterUsable);sample=SnapshotBatch(board,false,record.batch,report.allocationCounterUsable);}else{sample=SnapshotBatch(board,false,record.batch,report.allocationCounterUsable);legacy=SnapshotBatch(board,true,record.batch,report.allocationCounterUsable);}
                check(sample.finalHash==expected&&legacy.finalHash==expected,record.name+": isolated alternating snapshot parity "+iteration);record.samples.Add(sample);record.legacySamples.Add(legacy);
            }
            var times=record.samples.Select(s=>s.perSnapshotMs).OrderBy(t=>t).ToArray();record.medianMs=times[times.Length/2];record.p95Ms=times[(int)((times.Length-1)*.95)];record.maxMs=times.Last();times=record.legacySamples.Select(s=>s.perSnapshotMs).OrderBy(t=>t).ToArray();record.legacyMedianMs=times[times.Length/2];record.legacyP95Ms=times[(int)((times.Length-1)*.95)];record.legacyMaxMs=times.Last();report.snapshotRepeated.Add(record);
        }

        static SnapshotSample SnapshotBatch(BoardModel board,bool legacy,int batch,bool allocationCounter) {
            board.VerificationUseLegacySnapshot=legacy;var priorMode=GarbageCollector.GCMode;BoardSnapshot snapshot=null;double elapsed;long bytes;
            try{if(allocationCounter&&heapCounter)GarbageCollector.GCMode=GarbageCollector.Mode.Disabled;long allocated=allocationCounter?Counter():0;long start=Stopwatch.GetTimestamp();for(int i=0;i<batch;i++)snapshot=board.Snapshot();elapsed=(Stopwatch.GetTimestamp()-start)*1000.0/Stopwatch.Frequency;bytes=allocationCounter?Counter()-allocated:-1;}finally{GarbageCollector.GCMode=priorMode;}
            return new SnapshotSample{batchMilliseconds=elapsed,perSnapshotMs=elapsed/batch,allocatedBytes=bytes,finalHash=Hash(JsonUtility.ToJson(snapshot))};
        }

        static Row Measure(LevelData level,int kind,bool allocationCounter,bool profile,bool legacySnapshot=false) {
            var board=new BoardModel(level){VerificationUseLegacySnapshot=legacySnapshot};Func<TurnResult> command;
            if(kind<0){var move=board.LegalSwaps().First();command=()=>board.Swap(move[0].x,move[0].y,move[1].x,move[1].y);}
            else {var piece=board.Pieces.Values.First(p=>p.family=="gem");int x=piece.x,y=piece.y;board.InjectReviewPower(x,y,kind);command=()=>board.Tap(x,y);}
            board.VerificationResetWork();board.VerificationMeasureWork=profile;var priorMode=GarbageCollector.GCMode;TurnResult result;double elapsed;long bytes;
            try{if(allocationCounter&&heapCounter)GarbageCollector.GCMode=GarbageCollector.Mode.Disabled;long allocated=allocationCounter?Counter():0;long start=Stopwatch.GetTimestamp();result=command();elapsed=(Stopwatch.GetTimestamp()-start)*1000.0/Stopwatch.Frequency;bytes=allocationCounter?Counter()-allocated:-1;}finally{GarbageCollector.GCMode=priorMode;board.VerificationMeasureWork=false;}
            var work=board.VerificationGetWork();
            if(!result.accepted)throw new InvalidOperationException("Fixture command rejected: "+level.id+"/"+kind);
            return new Row{name="L"+level.globalLevel+"_"+(kind<0?"match":"power"+kind),turnHash=Hash(JsonUtility.ToJson(result)),finalHash=Hash(JsonUtility.ToJson(board.Snapshot())),checkpointHash=Hash(JsonUtility.ToJson(board.Checkpoint())),dictionaryOrder=string.Join(";",board.Pieces.Select(p=>p.Key+":"+p.Value.id)),steps=result.steps.Count,matchSteps=result.steps.Count(s=>s.kind=="match"),powerSteps=result.steps.Count(s=>s.kind=="power"),milliseconds=elapsed,allocatedBytes=bytes,work=work};
        }
    }
}
#endif

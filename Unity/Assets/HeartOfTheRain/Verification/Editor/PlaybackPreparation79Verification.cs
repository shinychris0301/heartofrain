#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.M48;
using Old=HeartOfTheRain.Verification.Checkpoint78Playback79;
using Object=UnityEngine.Object;
namespace HeartOfTheRain.Verification {
    public static class PlaybackPreparation79Verification {
        [Serializable] public sealed class SourceRow {public string name,archivedSHA256,compiledBodySHA256;public bool exact;}
        [Serializable] public sealed class Row {public string name,rawHash,finalHash,archivedQueueHash,detachedQueueHash,wholePathsHash;public int phases,workerThread;public bool eligiblePrefix;}
        [Serializable] public sealed class JobRow {public string name;public long generation;public PlaybackPreparationJob79.WorkTiming timing;}
        [Serializable] public sealed class Report {
            public string status,utc,unity;
            public string scope="Pinned native Editor managed worker proof: exact compiled78 queues, recursive tracks/continuation segments/contacts/poses and ordered dependencies;350 model commands, leading-swap jobs, captured policy, immutable metadata and bounded block/fault/cancel/once-only controls. Raw/model/service state is never mutated by the worker. Thread waits are native test coordination, not gameplay frame pacing or camera/UI proof; those require separate PlayMode/Android tests. No CPU speedup threshold.";
            public int checks,modelCases,queueComparisons,workerRequests,eligibleSwaps,jobCases,policyCases,syntheticCases,cancellationCases,negativeCases,mainThreadId;
            public bool compiledSourceMatchesArchive=true,queueParity=true,rawParity=true,pathOrderParity=true,poseParity=true,metadataManagedOnly=true;
            public List<SourceRow> sources=new List<SourceRow>();public List<Row> rows=new List<Row>();public List<JobRow> jobs=new List<JobRow>();public List<string> controls=new List<string>(),errors=new List<string>();
        }
        sealed class Work {public List<BoardStep> queue;public CommandResourcePreparation.Plan paths;public int thread;}
        static Report report;static M46Assets assets;static CommandResourcePreparation context;static CommandPreparation77Control pathControl;
        static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static string Hash(string text){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(text))).Replace("-","").ToLowerInvariant();}
        static void Check(bool okay,string label){report.checks++;if(!okay)throw new InvalidOperationException(label);}
        static string LF(string text)=>text.Replace("\r\n","\n").Trim();
        static void SourceControl(){
            string compiled=File.ReadAllText("Assets/HeartOfTheRain/Verification/Playback78Control79.cs");
            foreach(string name in new[]{"BoardPlayback.cs","LocalCascadeContinuation.cs","LocalCascadePlayback.cs"}){
                string source=File.ReadAllText(Path.GetFullPath("../.verification-cache/Gameplay79/BaselineSources/Unity/Assets/HeartOfTheRain/M46/Runtime/"+name));
                string expected=source.Substring(source.IndexOf("namespace HeartOfTheRain.M46",StringComparison.Ordinal)).Replace("namespace HeartOfTheRain.M46","namespace HeartOfTheRain.Verification.Checkpoint78Playback79").Replace("    public sealed class PlaybackTrack { public BoardStep step; public float start,leadIn; }","");
                string begin="// BEGIN EXACT78 "+name,end="// END EXACT78 "+name;int at=compiled.IndexOf(begin,StringComparison.Ordinal)+begin.Length;string actual=compiled.Substring(at,compiled.IndexOf(end,at,StringComparison.Ordinal)-at);
                bool equal=LF(expected)==LF(actual);report.sources.Add(new SourceRow{name=name,archivedSHA256=Hash(source),compiledBodySHA256=Hash(LF(actual)),exact=equal});report.compiledSourceMatchesArchive&=equal;Check(equal,"Independent exact78 compiled source "+name);
            }
        }
        static T Worker<T>(Func<T> function){
            T value=default(T);Exception failure=null;var done=new ManualResetEventSlim(false);try{
                Check(ThreadPool.QueueUserWorkItem(_=>{try{value=function();}catch(Exception ex){failure=ex;}finally{done.Set();}}),"Native worker queued");
                Check(done.Wait(TimeSpan.FromSeconds(20)),"Native worker finished within coordination timeout");
            }finally{if(done.IsSet)done.Dispose();}if(failure!=null)throw new InvalidOperationException("Managed worker failed",failure);report.workerRequests++;return value;
        }
        static string Signature(List<BoardStep> queue,bool archived){
            var text=new StringBuilder();void Number(float n){text.Append(n.ToString("R",System.Globalization.CultureInfo.InvariantCulture)).Append(';');}
            void Step(BoardStep step,int depth){
                if(depth>32)throw new InvalidOperationException("Unexpected cyclic playback graph");text.Append(JsonUtility.ToJson(step));text.Append("tracks:").Append(step.playbackTracks==null?-1:step.playbackTracks.Count);
                if(step.playbackTracks!=null)foreach(var track in step.playbackTracks){Number(track.start);Number(track.leadIn);Step(track.step,depth+1);}
                foreach(var motion in step.motion){
                    text.Append(archived?Old.LocalCascadeContinuation.IsContinuation(motion):LocalCascadeContinuation.IsContinuation(motion));
                    foreach(float age in new[]{-1f,0f,motion.delay,motion.delay+motion.seconds*.5f,motion.delay+motion.seconds,motion.delay+motion.seconds+.05f,step.duration+.11f}){
                        float segmentAge;var segment=archived?Old.LocalCascadeContinuation.Segment(motion,age,out segmentAge):LocalCascadeContinuation.Segment(motion,age,out segmentAge);Number(segmentAge);text.Append(JsonUtility.ToJson(segment));
                        float x,y;if(archived)Old.TileFall.Position(motion,age,out x,out y);else TileFall.Position(motion,age,out x,out y);Number(x);Number(y);text.Append(archived?Old.TileFall.Moving(motion,age):TileFall.Moving(motion,age));
                    }
                    foreach(float contact in archived?Old.LocalCascadeContinuation.LandingContacts(motion):LocalCascadeContinuation.LandingContacts(motion))Number(contact);
                }
            }
            foreach(var phase in queue)Step(phase,0);return Hash(text.ToString());
        }
        static void Paths(List<BoardStep> queue,CommandResourcePreparation.Plan plan,string label){
            var whole=pathControl.RequiredResources(queue);Check(whole.SequenceEqual(plan.All),label+" whole request order");Check(plan.Matches(queue)&&plan.Count==queue.Count,label+" plan phase references");
            for(int i=0;i<queue.Count;i++)Check(pathControl.RequiredResources(new[]{queue[i]}).SequenceEqual(plan.Phase(i)),label+" phase request order "+i);
        }
        static Work Compile(BoardStep[] raw,LevelData geometry,bool policy){
            var detached=context.Detach();return Worker(()=>{var queue=BoardPlayback.BuildDetached(raw,geometry,policy);return new Work{queue=queue,paths=detached.Build(queue),thread=Thread.CurrentThread.ManagedThreadId};});
        }
        static PlaybackPreparationJob79.Result Take(PlaybackPreparationJob79 job){
            var began=Stopwatch.StartNew();while(!job.IsCompleted&&began.Elapsed.TotalSeconds<20)Thread.Sleep(1);
            Check(job.IsCompleted,"Job completed within coordination timeout");bool taken=job.TryTake(out var result,out var failure);Check(taken,"Job completion can be taken");if(failure!=null)throw new InvalidOperationException("Job failed",failure);Check(result!=null,"Successful job returns queue/plan");return result;
        }
        static void Timing(PlaybackPreparationJob79.WorkTiming t){
            Check(t.CallerThreadId==report.mainThreadId&&t.WorkerThreadId!=report.mainThreadId&&t.WorkerThreadId>0,"Worker and caller managed threads differ");
            var stamps=new[]{t.QueuedAtTicks,t.StartedAtTicks,t.BuildStartedAtTicks,t.BuildFinishedAtTicks,t.ResourcesStartedAtTicks,t.ResourcesFinishedAtTicks,t.FinishedAtTicks};Check(stamps.All(v=>v>0)&&stamps.SequenceEqual(stamps.OrderBy(v=>v)),"Worker stage ticks are ordered");
            Check(t.Frequency==Stopwatch.Frequency&&Math.Abs(t.BuildMs-(t.BuildFinishedAtTicks-t.BuildStartedAtTicks)*1000.0/t.Frequency)<.000001&&Math.Abs(t.ResourceMs-(t.ResourcesFinishedAtTicks-t.ResourcesStartedAtTicks)*1000.0/t.Frequency)<.000001,"Worker timers use exact Stopwatch conversion");
            Check(t.TotalMs+.1>=t.BuildMs+t.ResourceMs+t.PrefixValidationMs+t.ControlledWorkMs&&t.QueueWaitMs>=0,"Worker timing owners include nested work");
        }
        static void JobCase(string name,BoardStep[] raw,LevelData geometry,string expected){
            Check(PlaybackPreparationJob79.TryCreatePureSwapPrefix(raw,out var prefix),name+" leading pure swap qualifies");
            using(var job=new PlaybackPreparationJob79(raw,geometry,prefix,context,false,report.jobCases+1000)){
                Check(!job.Started&&!job.IsCompleted&&!job.TryTake(out _,out _),"Job is inert before explicit Start");job.Start();job.Start();var result=Take(job);Timing(result.Timing);
                Check(ReferenceEquals(result.Queue[0],prefix)&&result.Queue[0].duration==.12f,"Published swap instance/duration retained");
                Check(Signature(result.Queue,false)==expected,name+" actual job exact78 queue/segment/pose parity");Paths(result.Queue,result.Resources,name+" job");
                Check(result.Generation==job.Generation&&!job.TryTake(out _,out _),"Result generation and once-only take");report.jobs.Add(new JobRow{name=name,generation=result.Generation,timing=result.Timing});report.jobCases++;
            }
        }
        static Dictionary<string,Tuple<BoardStep[],LevelData,string>> Corpus(){
            var selected=new Dictionary<string,Tuple<BoardStep[],LevelData,string>>();
            for(int level=0;level<50;level++)foreach(int kind in new[]{-1,4,5,7,11,16,21}){
                var model=new BoardModel(JsonUtility.FromJson<LevelData>(assets.levels[level].text));TurnResult turn;
                if(kind<0){var swap=model.LegalSwaps().First();turn=model.Swap(swap[0].x,swap[0].y,swap[1].x,swap[1].y);}else{var gem=model.Pieces.Values.First(p=>p.family=="gem");model.InjectReviewPower(gem.x,gem.y,kind);turn=model.Tap(gem.x,gem.y);}
                string name="L"+(level+1)+"_"+(kind<0?"match":"power"+kind);Check(turn.accepted,name+" accepted");string before=Hash(JsonUtility.ToJson(turn)),final=Hash(JsonUtility.ToJson(model.Snapshot()));var raw=turn.steps.ToArray();
                Old.LocalCascadeContinuation.VerificationUseCheckpoint74=false;var old=Old.BoardPlayback.Build(raw,model.Level);string expected=Signature(old,true);
                // The global switch deliberately disagrees with the captured
                // worker policy. No worker is allowed to consult that switch.
                LocalCascadeContinuation.VerificationUseCheckpoint74=true;var work=Compile(raw,PlaybackPreparationJob79.CaptureGeometry(model.Level),false);
                string actual=Signature(work.queue,false);Check(expected==actual,name+" detached queue/track/route/pose parity");Check(work.thread!=report.mainThreadId,name+" pure request runs off caller");Paths(work.queue,work.paths,name);
                bool eligible=PlaybackPreparationJob79.TryCreatePureSwapPrefix(raw,out _);if(eligible){report.eligibleSwaps++;JobCase(name,raw,model.Level,expected);}
                Check(before==Hash(JsonUtility.ToJson(turn))&&final==Hash(JsonUtility.ToJson(model.Snapshot())),name+" raw/model final immutable");report.modelCases++;report.queueComparisons++;
                report.rows.Add(new Row{name=name,rawHash=before,finalHash=final,archivedQueueHash=expected,detachedQueueHash=actual,wholePathsHash=Hash(string.Join("\n",work.paths.All)),phases=work.queue.Count,workerThread=work.thread,eligiblePrefix=eligible});
                if(kind<0&&new[]{4,14,31,33}.Contains(level+1))selected.Add(name,Tuple.Create(raw,model.Level,expected));
            }
            Check(report.modelCases==350&&report.eligibleSwaps==50,"Full350 corpus/50 natural swaps retained");return selected;
        }
        static void Policies(Dictionary<string,Tuple<BoardStep[],LevelData,string>> selected){
            foreach(var item in selected)foreach(bool geometry in new[]{true,false})foreach(bool policy in new[]{true,false}){
                Old.LocalCascadeContinuation.VerificationUseCheckpoint74=policy;var cells=geometry?item.Value.Item2:null;var expected=Old.BoardPlayback.Build(item.Value.Item1,cells);
                LocalCascadeContinuation.VerificationUseCheckpoint74=!policy;var actual=Compile(item.Value.Item1,PlaybackPreparationJob79.CaptureGeometry(cells),policy);Check(Signature(expected,true)==Signature(actual.queue,false),item.Key+" captured policy/geometry "+policy+"/"+geometry);Paths(actual.queue,actual.paths,"Policy");report.policyCases++;report.queueComparisons++;
            }
        }
        static void Synthetics(){
            foreach(string name in ModelWork78Proof.BenchmarkNames.Where(n=>n=="L1_orb_rocket"||n=="L1_golden_bomb")){
                var p=ModelWork78Proof.Prepare(assets,name);var turn=p.Solve();Old.LocalCascadeContinuation.VerificationUseCheckpoint74=false;var expected=Old.BoardPlayback.Build(turn.steps,p.model.Level);JobCase(name,turn.steps.ToArray(),p.model.Level,Signature(expected,true));report.syntheticCases++;
            }
            var mixed=new BoardModel(MixedPowerSwapFixtures.Match(4));var from=MixedPowerSwapFixtures.From(4);var to=MixedPowerSwapFixtures.To();mixed.InjectReviewPower(to.x,to.y,5);var result=mixed.Swap(from.x,from.y,to.x,to.y);Old.LocalCascadeContinuation.VerificationUseCheckpoint74=false;JobCase("mixed_protected_birth",result.steps.ToArray(),mixed.Level,Signature(Old.BoardPlayback.Build(result.steps,mixed.Level),true));report.syntheticCases++;
            var source=ModelWork78Proof.Prepare(assets,"L4_match");var raw=source.Solve().steps.ToArray();var mutated=(BoardStep[])raw.Clone();mutated[0]=new BoardStep{kind="power"};Check(!PlaybackPreparationJob79.TryCreatePureSwapPrefix(mutated,out _),"Power-first command retains synchronous fallback");Check(!PlaybackPreparationJob79.TryCreatePureSwapPrefix(new[]{raw[0]},out _),"No-tail command is ineligible");Check(!PlaybackPreparationJob79.TryCreatePureSwapPrefix(null,out _),"Null command is ineligible");report.negativeCases+=3;
            // Metadata containers detach from both asset arrays and Unity
            // lifetime. Destroying the source before work proves no asset read.
            var clone=Object.Instantiate(assets);var detached=new CommandResourcePreparation(clone);var expectedPaths=detached.Build(BoardPlayback.BuildDetached(raw,source.model.Level,false));
            if(clone.powerResources.Length>0)clone.powerResources[0]="changed_after_capture";if(clone.bodies.Length>0)clone.bodies[0].resource="changed_after_capture";foreach(var clip in clone.obstacleClips)if(clip.pageResources?.Length>0){clip.pageResources[0]="changed_after_capture";break;}Object.DestroyImmediate(clone);
            PlaybackPreparationJob79.TryCreatePureSwapPrefix(raw,out var head);using(var job=new PlaybackPreparationJob79(raw,source.model.Level,head,detached,false,8000)){job.Start();var answer=Take(job);Check(expectedPaths.All.SequenceEqual(answer.Resources.All),"Captured metadata survives source mutation and destruction");}
            var metadata=typeof(CommandResourcePreparation).GetField("metadata",Private).GetValue(detached);Check(!ContainsUnity(metadata,new HashSet<object>()),"Detached metadata graph contains no Unity objects");
            var keys=(IDictionary)typeof(BoardPresentation).GetField("BodyKeys",BindingFlags.Static|BindingFlags.NonPublic).GetValue(null);string family="native_worker_only_79_"+Guid.NewGuid().ToString("N");Check(!keys.Contains(family),"Unique body-key family absent from main cache");
            var snap=new BoardSnapshot{pieces=new[]{new Piece{id=1,family=family,hp=2}},goals=Array.Empty<Goal>(),status="Playing"};var step=new BoardStep{kind="settled",before=snap,after=snap};var isolated=detached.Detach();Worker(()=>isolated.Build(new[]{step}));Check(!keys.Contains(family),"Detached walker never mutates BoardPresentation static key cache");
            report.controls.Add("String-only metadata, source-array mutation/destruction and worker-owned BodyKey cache");
        }
        static bool ContainsUnity(object value,HashSet<object> seen){
            if(value==null||value is string||value.GetType().IsPrimitive||value.GetType().IsEnum)return false;if(value is Object)return true;if(!seen.Add(value))return false;
            if(value is IDictionary dictionary){foreach(DictionaryEntry e in dictionary)if(ContainsUnity(e.Key,seen)||ContainsUnity(e.Value,seen))return true;return false;}
            if(value is IEnumerable sequence){foreach(var entry in sequence)if(ContainsUnity(entry,seen))return true;return false;}
            foreach(var field in value.GetType().GetFields(BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic))if(ContainsUnity(field.GetValue(value),seen))return true;return false;
        }
        static void Cancellation(Dictionary<string,Tuple<BoardStep[],LevelData,string>> selected){
            var fixture=selected["L4_match"];var raw=fixture.Item1;PlaybackPreparationJob79.TryCreatePureSwapPrefix(raw,out var head);
            using(var never=new PlaybackPreparationJob79(raw,fixture.Item2,head,context,false,9000)){never.Cancel();never.Start();Check(!never.Started&&never.Cancelled&&never.TryTake(out var none,out var cancelled)&&none==null&&cancelled is OperationCanceledException,"Cancel-before-start never queues work");report.cancellationCases++;}
            foreach(var stage in new[]{PlaybackPreparationJob79.WorkStage.BeforeBuild,PlaybackPreparationJob79.WorkStage.BeforeResources}){
                using(var entered=new ManualResetEventSlim(false))using(var release=new ManualResetEventSlim(false))using(var job=new PlaybackPreparationJob79(raw,fixture.Item2,head,context,false,9001)){
                    job.VerificationWorkHook=at=>{if(at==stage){entered.Set();if(!release.Wait(TimeSpan.FromSeconds(10)))throw new TimeoutException("Native controlled worker gate");}};
                    try{job.Start();Check(entered.Wait(TimeSpan.FromSeconds(10))&&!job.IsCompleted,"Controlled worker remains pending");Check(job.Timing.WorkerThreadId!=report.mainThreadId,"Blocked work has separate managed thread");job.Cancel();}finally{release.Set();}
                    var watch=Stopwatch.StartNew();while(!job.IsCompleted&&watch.Elapsed.TotalSeconds<10)Thread.Sleep(1);Check(job.TryTake(out var value,out var failure)&&value==null&&failure is OperationCanceledException,"Cancelled in-flight work cannot install a queue");report.cancellationCases++;
                }
            }
            using(var job=new PlaybackPreparationJob79(raw,fixture.Item2,head,context,false,9002)){
                job.VerificationWorkHook=stage=>{if(stage==PlaybackPreparationJob79.WorkStage.BeforeResources)throw new InvalidOperationException("Controlled pure worker failure");};job.Start();var wait=Stopwatch.StartNew();while(!job.IsCompleted&&wait.Elapsed.TotalSeconds<10)Thread.Sleep(1);
                Check(job.TryTake(out var answer,out var error)&&answer==null&&error is InvalidOperationException&&!job.Cancelled,"Pure worker failure is explicit without model/service mutation");Check(!job.TryTake(out _,out _),"Fault result is once-only");report.negativeCases++;
            }
            bool aborted=false;try{BoardPlayback.BuildDetached(raw,fixture.Item2,false,cancelled:()=>true);}catch(OperationCanceledException){aborted=true;}Check(aborted,"Coarse cancellation boundary rejects compilation");report.cancellationCases++;
            report.controls.AddRange(new[]{"Captured74 policy independent of global switch","Exact published swap identity","Explicit Start/once-only result","Blocked worker cancellation before Build/resources","Pure worker failure","No model/service callbacks inside helper"});
        }
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,mainThreadId=Thread.CurrentThread.ManagedThreadId};bool current=LocalCascadeContinuation.VerificationUseCheckpoint74,old=Old.LocalCascadeContinuation.VerificationUseCheckpoint74;
            try{SourceControl();var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");Check(ui&&ui.boards,"Approved assets available");assets=ui.boards;context=new CommandResourcePreparation(assets);pathControl=new CommandPreparation77Control(assets);var selected=Corpus();Policies(selected);Synthetics();Cancellation(selected);}
            catch(Exception ex){report.errors.Add(ex.ToString());report.queueParity=report.rawParity=report.pathOrderParity=report.poseParity=report.metadataManagedOnly=false;}
            finally{LocalCascadeContinuation.VerificationUseCheckpoint74=current;Old.LocalCascadeContinuation.VerificationUseCheckpoint74=old;}
            report.status=report.errors.Count==0?"PASS_NATIVE_PLAYBACK_PREPARATION79":"FAIL_NATIVE_PLAYBACK_PREPARATION79";string output=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY79_OUTPUT");if(string.IsNullOrEmpty(output))output=Path.GetFullPath("../Verification/Evidence/Gameplay79");Directory.CreateDirectory(Path.Combine(output,"Native"));File.WriteAllText(Path.Combine(output,"Native/Worker79.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif

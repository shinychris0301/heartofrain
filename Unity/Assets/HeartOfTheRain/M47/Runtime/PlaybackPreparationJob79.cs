using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.Linq;
using System.Threading;
using HeartOfTheRain.M46;

namespace HeartOfTheRain.M47 {
    // Managed presentation work only. The caller owns lifecycle/generation,
    // first-camera witness, bank readiness and all model/service callbacks.
    // Raw DTO contents and the published prefix are shared read-only; this job
    // defensively owns their array and the geometry/string-metadata containers.
    public sealed class PlaybackPreparationJob79:IDisposable {
        public enum WorkStage { BeforeBuild,AfterBuild,BeforeResources,AfterResources }
        [Serializable] public struct WorkTiming {
            public int CallerThreadId,WorkerThreadId;
            public long Frequency,QueuedAtTicks,StartedAtTicks,BuildStartedAtTicks,BuildFinishedAtTicks,
                ResourcesStartedAtTicks,ResourcesFinishedAtTicks,FinishedAtTicks;
            public double QueueWaitMs,BuildMs,PrefixValidationMs,ResourceMs,ControlledWorkMs,TotalMs;
        }
        public sealed class Result {
            public readonly List<BoardStep> Queue;
            public readonly CommandResourcePreparation.Plan Resources;
            public readonly WorkTiming Timing;
            public readonly long Generation;
            internal Result(List<BoardStep> queue,CommandResourcePreparation.Plan resources,WorkTiming timing,long generation){Queue=queue;Resources=resources;Timing=timing;Generation=generation;}
        }
        readonly object gate=new object();
        readonly CultureInfo culture;
        readonly bool checkpoint74;
        readonly long generation;
        readonly int callerThreadId;
        readonly Func<bool> cancellation;
        BoardStep[] raw;
        LevelData geometry;
        BoardStep prefix;
        CommandResourcePreparation resources;
        int cancelled;
        bool started,completed,taken;
        Result result;
        Exception error;
        WorkTiming timing;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        // Native opt-in tests may block/throw at a managed boundary. Hooks run
        // on the worker: they must never invoke Unity or touch live game state.
        [NonSerialized] public Action<WorkStage> VerificationWorkHook;
#endif
        public long Generation=>generation;
        public bool Started {get{lock(gate)return started;}}
        public bool IsCompleted {get{lock(gate)return completed;}}
        public WorkTiming Timing {get{lock(gate)return timing;}}
        public bool Cancelled=>Volatile.Read(ref cancelled)!=0;

        public PlaybackPreparationJob79(BoardStep[] immutableSteps,LevelData detachedGeometry,BoardStep publishedPrefix,CommandResourcePreparation detachedContext,bool capturedCheckpoint74,long generation){
            if(immutableSteps==null)throw new ArgumentNullException(nameof(immutableSteps));
            if(publishedPrefix==null)throw new ArgumentNullException(nameof(publishedPrefix));
            if(detachedContext==null)throw new ArgumentNullException(nameof(detachedContext));
            BoardStep expected;if(!TryCreatePureSwapPrefix(immutableSteps,out expected)||!SameHead(expected,publishedPrefix))throw new ArgumentException("A matching pure leading swap is required",nameof(publishedPrefix));
            raw=(BoardStep[])immutableSteps.Clone();geometry=CaptureGeometry(detachedGeometry);prefix=publishedPrefix;
            resources=detachedContext.Detach();checkpoint74=capturedCheckpoint74;this.generation=generation;
            callerThreadId=Thread.CurrentThread.ManagedThreadId;
            culture=CultureInfo.ReadOnly((CultureInfo)CultureInfo.CurrentCulture.Clone());
            cancellation=()=>Volatile.Read(ref cancelled)!=0;
        }
        public static LevelData CaptureGeometry(LevelData source){
            if(source==null)return null;
            return new LevelData{columns=source.columns,rows=source.rows,globalLevel=source.globalLevel,
                activeCells=source.activeCells==null?null:source.activeCells.Select(c=>c==null?null:new Cell(c.x,c.y)).ToArray()};
        }
        public static bool TryCreatePureSwapPrefix(IList<BoardStep> source,out BoardStep head){
            head=null;if(source==null||source.Count<2)return false;var step=source[0];
            if(step==null||step.kind!="swap"||step.before==null||step.after==null||step.powerPlan!=null||step.booster!=null
                ||step.triggerOriginId!=0||step.triggerTime!=0||step.playbackTracks!=null&&step.playbackTracks.Count!=0
                ||step.damage==null||step.damage.Count!=0||step.removed==null||step.removed.Count!=0||step.created==null||step.created.Count!=0
                ||step.collections==null||step.collections.Count!=0||step.motion==null||step.motion.Count!=2
                ||step.motion[0]==null||step.motion[1]==null||step.motion[0].id==step.motion[1].id)return false;
            head=new BoardStep{kind=step.kind,label=step.label,duration=.12f,before=step.before,after=step.after,
                powerPlan=step.powerPlan,booster=step.booster,removed=step.removed,damage=step.damage,
                created=step.created,collections=step.collections,motion=step.motion};return true;
        }
        static bool SameHead(BoardStep a,BoardStep b)=>a!=null&&b!=null&&a.kind==b.kind&&a.label==b.label&&a.duration==b.duration
            &&a.triggerTime==b.triggerTime&&a.triggerOriginId==b.triggerOriginId&&ReferenceEquals(a.before,b.before)&&ReferenceEquals(a.after,b.after)
            &&ReferenceEquals(a.powerPlan,b.powerPlan)&&ReferenceEquals(a.booster,b.booster)&&ReferenceEquals(a.motion,b.motion)
            &&ReferenceEquals(a.damage,b.damage)&&ReferenceEquals(a.removed,b.removed)&&ReferenceEquals(a.created,b.created)
            &&ReferenceEquals(a.collections,b.collections)&&a.playbackTracks==null&&b.playbackTracks==null;
        static double Milliseconds(long ticks)=>ticks*(1000.0/Stopwatch.Frequency);
        void ThrowIfCancelled(){if(Cancelled)throw new OperationCanceledException("Playback preparation cancelled");}
        public void Start(){
            lock(gate){
                if(started||completed)return;
                started=true;timing=new WorkTiming{CallerThreadId=callerThreadId,Frequency=Stopwatch.Frequency,QueuedAtTicks=Stopwatch.GetTimestamp()};
                try{if(!ThreadPool.QueueUserWorkItem(_=>Run()))Complete(null,new InvalidOperationException("Unable to queue playback preparation"),timing);}
                catch(Exception ex){Complete(null,ex,timing);}
            }
        }
        void Run(){
            WorkTiming measured;BoardStep[] source;LevelData cells;BoardStep head;CommandResourcePreparation context;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            Action<WorkStage> hook;
#endif
            lock(gate){measured=timing;source=raw;cells=geometry;head=prefix;context=resources;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                hook=VerificationWorkHook;
#endif
            }
            measured.StartedAtTicks=Stopwatch.GetTimestamp();measured.WorkerThreadId=Thread.CurrentThread.ManagedThreadId;
            measured.QueueWaitMs=Milliseconds(measured.StartedAtTicks-measured.QueuedAtTicks);
            lock(gate)timing=measured;
            var previousCulture=CultureInfo.CurrentCulture;
            Result output=null;Exception failure=null;
            void Boundary(WorkStage stage){ThrowIfCancelled();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                if(hook!=null){long began=Stopwatch.GetTimestamp();try{hook(stage);}finally{measured.ControlledWorkMs+=Milliseconds(Stopwatch.GetTimestamp()-began);}}
#endif
                ThrowIfCancelled();}
            try{
                CultureInfo.CurrentCulture=culture;
                if(measured.WorkerThreadId==callerThreadId)throw new InvalidOperationException("Presentation work must run on a separate managed thread");
                Boundary(WorkStage.BeforeBuild);measured.BuildStartedAtTicks=Stopwatch.GetTimestamp();
                var queue=BoardPlayback.BuildDetached(source,cells,checkpoint74,cancelled:cancellation);
                measured.BuildFinishedAtTicks=Stopwatch.GetTimestamp();measured.BuildMs=Milliseconds(measured.BuildFinishedAtTicks-measured.BuildStartedAtTicks);
                lock(gate)timing=measured;
                Boundary(WorkStage.AfterBuild);long prefixAt=Stopwatch.GetTimestamp();
                if(queue.Count==0||!SameHead(queue[0],head))throw new InvalidOperationException("Detached compilation changed the published swap");
                queue[0]=head;measured.PrefixValidationMs=Milliseconds(Stopwatch.GetTimestamp()-prefixAt);
                Boundary(WorkStage.BeforeResources);measured.ResourcesStartedAtTicks=Stopwatch.GetTimestamp();
                var plan=context.Build(queue);
                measured.ResourcesFinishedAtTicks=Stopwatch.GetTimestamp();measured.ResourceMs=Milliseconds(measured.ResourcesFinishedAtTicks-measured.ResourcesStartedAtTicks);
                lock(gate)timing=measured;
                Boundary(WorkStage.AfterResources);ThrowIfCancelled();
                output=new Result(queue,plan,measured,generation);
            }catch(Exception ex){failure=ex;}
            finally{
                CultureInfo.CurrentCulture=previousCulture;measured.FinishedAtTicks=Stopwatch.GetTimestamp();measured.TotalMs=Milliseconds(measured.FinishedAtTicks-measured.StartedAtTicks);
                if(output!=null)output=new Result(output.Queue,output.Resources,measured,generation);
                Complete(output,failure,measured);
            }
        }
        void Complete(Result output,Exception failure,WorkTiming measured){
            lock(gate){
                if(completed)return;
                timing=measured;if(Cancelled){result=null;error=new OperationCanceledException("Playback preparation cancelled");}else{result=output;error=failure;}
                raw=null;geometry=null;prefix=null;resources=null;completed=true;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                VerificationWorkHook=null;
#endif
            }
        }
        // The caller must additionally match Generation, board, bank and active
        // head before installing. Taking is once-only even for faults/cancels.
        public bool TryTake(out Result output,out Exception failure){
            lock(gate){output=null;failure=null;if(!completed||taken)return false;taken=true;
                if(Cancelled)failure=new OperationCanceledException("Playback preparation cancelled");else{output=result;failure=error;}
                result=null;error=null;return true;}
        }
        public void Cancel(){
            Interlocked.Exchange(ref cancelled,1);
            lock(gate){
                if(completed){result=null;error=new OperationCanceledException("Playback preparation cancelled");}
                else if(!started)Complete(null,new OperationCanceledException("Playback preparation cancelled"),new WorkTiming{CallerThreadId=callerThreadId,Frequency=Stopwatch.Frequency});
            }
        }
        public void Dispose()=>Cancel();
    }
}

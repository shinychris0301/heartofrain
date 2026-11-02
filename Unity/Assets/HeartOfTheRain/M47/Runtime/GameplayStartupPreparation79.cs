using System;
using System.Collections.Generic;
using System.Linq;
using HeartOfTheRain.M46;
using UnityEngine;

namespace HeartOfTheRain.M47 {
    public sealed partial class GameplayScreen {
        sealed class StartupRequest79 {
            public BoardStep[] raw; public LevelData geometry; public BoardStep head;
            public BoardModel board; public M46AtlasBank bank; public bool checkpoint74;
        }
        StartupRequest79 startupRequest79;
        PlaybackPreparationJob79 startupJob79;
        long startupGeneration79;
        bool startupHolding79;
        int startupSubmitted79=-1;
        bool StartupPending79=>startupRequest79!=null;
        static long StartupStamp79()=>System.Diagnostics.Stopwatch.GetTimestamp();
        static double StartupMs79(long ticks)=>ticks*1000.0/System.Diagnostics.Stopwatch.Frequency;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        [NonSerialized] public bool VerificationUseCheckpoint78Startup;
        [NonSerialized] public Action<PlaybackPreparationJob79.WorkStage> VerificationStartupWorkHook;
        [Serializable] public struct StartupTrace79 {
            public long generation;
            public bool eligible,pending,resumed,held,cancelled,workerFailed;
            public string reason,error;
            public int acceptedFrame,headSubmittedFrame,cameraWitnessFrame,jobStartedFrame,jobCompletedFrame,tailInstalledFrame,headEndedFrame,holdFrames,callerThreadId,workerThreadId;
            public long acceptedTicks,headSubmittedTicks,cameraWitnessTicks,jobStartedTicks,jobCompletedTicks,tailInstalledTicks,headEndedTicks,workerQueuedTicks,workerStartedTicks,workerFinishedTicks;
            public double acceptedWall,headSubmittedWall,cameraWitnessWall,jobStartedWall,jobCompletedWall,tailInstalledWall,headEndedWall,headDuration,mainCaptureMs,mainInstallMs,holdMs,buildWorkerMs,resourceWorkerMs,totalWorkerMs,workerQueueMs;
        }
        StartupTrace79 startupTrace79;
        BoardStep[] startupQueue79=Array.Empty<BoardStep>();
        CommandResourcePreparation.Plan startupResources79;
        public bool VerificationStartupPending=>StartupPending79;
        public bool VerificationCanBuffer=>CanBuffer;
        public StartupTrace79 VerificationStartup=>startupTrace79;
        public BoardStep[] VerificationStartupQueue=>startupQueue79;
        public CommandResourcePreparation.Plan VerificationStartupResources=>startupResources79;
#endif
        void SubscribeStartupCamera79(){Camera.onPostRender-=StartupCameraRendered79;Camera.onPostRender+=StartupCameraRendered79;ResumeStartup79();}
        void UnsubscribeStartupCamera79(){Camera.onPostRender-=StartupCameraRendered79;SuspendStartup79();}
        void CancelStartup79(bool discard){
            startupGeneration79++;startupJob79?.Dispose();startupJob79=null;startupSubmitted79=-1;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(StartupPending79){startupTrace79.cancelled=true;startupTrace79.pending=!discard;}
#endif
            if(discard){startupRequest79=null;startupHolding79=false;}
        }
        void SuspendStartup79(){if(StartupPending79)CancelStartup79(false);}
        void ResumeStartup79(){
            if(!StartupPending79||startupJob79!=null)return;
            if(startupRequest79.board!=board||startupRequest79.bank!=bank){CancelStartup79(true);return;}
            try{CreateStartupJob79();}catch(Exception e){FailStartup79(e);return;}
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            startupTrace79.resumed=true;startupTrace79.cancelled=false;startupTrace79.generation=startupGeneration79;
#endif
        }
        void CreateStartupJob79(){
            var r=startupRequest79;
            startupJob79=new PlaybackPreparationJob79(r.raw,r.geometry,r.head,commandResourcePreparation,r.checkpoint74,++startupGeneration79);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            startupJob79.VerificationWorkHook=VerificationStartupWorkHook;
#endif
        }
        bool TryEnqueueStartup79(ref IEnumerable<BoardStep> steps){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            startupQueue79=Array.Empty<BoardStep>();startupResources79=null;startupTrace79=default(StartupTrace79);
            if(VerificationUseCheckpoint78Startup)return false;
#endif
            if(StartupPending79||current!=null||preparing||queue.Count!=0||queueIndex!=0||bank==null||!UsePreparedCommandResources||!isActiveAndEnabled)return false;
            long began=StartupStamp79();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            double acceptedWall=Time.realtimeSinceStartupAsDouble;
#endif
            var raw=steps as BoardStep[]??steps.ToArray();steps=raw;BoardStep head;
            if(!PlaybackPreparationJob79.TryCreatePureSwapPrefix(raw,out head))return false;
            if(commandResourceOwner!=bank||commandResourcePreparation==null)ResetCommandPreparation();
            bool old74=false;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            old74=LocalCascadeContinuation.VerificationUseCheckpoint74;
#endif
            startupRequest79=new StartupRequest79{raw=(BoardStep[])raw.Clone(),geometry=PlaybackPreparationJob79.CaptureGeometry(board.Level),head=head,board=board,bank=bank,checkpoint74=old74};
            startupHolding79=false;startupSubmitted79=-1;
            var acceptedBoard=board;var acceptedRequest=startupRequest79;
            try {
                CreateStartupJob79();queue.Add(head);PrepareCommandResources();
                awaitingPlaybackPose=true;playbackPoseAnchor=false;selected=pressed=null;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                startupTrace79=new StartupTrace79{generation=startupGeneration79,eligible=true,pending=true,acceptedFrame=Time.frameCount,acceptedTicks=began,acceptedWall=acceptedWall,headDuration=head.duration,reason="pure leading swap"};
#endif
                long generation=startupGeneration79;Next();
                if(generation!=startupGeneration79)return true;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                startupTrace79.mainCaptureMs=StartupMs79(StartupStamp79()-began);
                if(MeasureFrameCosts)LastCommandCost=new CommandCost{frame=Time.frameCount,phases=queue.Count,totalMs=startupTrace79.mainCaptureMs};
#endif
            }catch(Exception e){if(acceptedBoard==board&&ReferenceEquals(acceptedRequest,startupRequest79))FailStartup79(e,acceptedBoard);}
            return true;
        }
        void StartupPoseSubmitted79(){
            if(!StartupPending79||startupJob79==null||startupJob79.Started||startupRequest79.board!=board||startupRequest79.bank!=bank)return;
            if(current!=startupRequest79.head&&!startupHolding79)return;
            startupSubmitted79=Time.frameCount;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(startupTrace79.headSubmittedFrame==0){startupTrace79.headSubmittedFrame=Time.frameCount;startupTrace79.headSubmittedTicks=StartupStamp79();startupTrace79.headSubmittedWall=Time.realtimeSinceStartupAsDouble;}
#endif
        }
        void StartupCameraRendered79(Camera rendered){
            if(rendered!=view||!isActiveAndEnabled||!StartupPending79||startupJob79==null||startupJob79.Started||startupSubmitted79!=Time.frameCount)return;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            startupTrace79.cameraWitnessFrame=Time.frameCount;startupTrace79.cameraWitnessTicks=StartupStamp79();startupTrace79.cameraWitnessWall=Time.realtimeSinceStartupAsDouble;
            startupTrace79.jobStartedFrame=Time.frameCount;startupTrace79.jobStartedTicks=StartupStamp79();startupTrace79.jobStartedWall=Time.realtimeSinceStartupAsDouble;
#endif
            startupJob79.Start();
        }
        bool HoldStartupTail79(){
            if(!StartupPending79)return false;
            current=null;startupHolding79=true;awaitingPlaybackPose=playbackPoseAnchor=false;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(startupTrace79.headEndedFrame==0){startupTrace79.held=true;startupTrace79.headEndedFrame=Time.frameCount;startupTrace79.headEndedTicks=StartupStamp79();startupTrace79.headEndedWall=Time.realtimeSinceStartupAsDouble;}
#endif
            return true;
        }
        void PollStartup79(){
            if(!StartupPending79||startupJob79==null)return;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(startupHolding79)startupTrace79.holdFrames++;
#endif
            PlaybackPreparationJob79.Result result;Exception error;if(!startupJob79.TryTake(out result,out error))return;
            if(startupRequest79.board!=board||startupRequest79.bank!=bank||startupJob79.Generation!=startupGeneration79){CancelStartup79(true);return;}
            if(error!=null){FailStartup79(error);return;}
            long began=StartupStamp79();var ownedBoard=startupRequest79.board;long ownedGeneration=startupGeneration79;
            try {
                if(result==null||result.Generation!=startupGeneration79||queue.Count!=1||!ReferenceEquals(queue[0],startupRequest79.head)||result.Queue.Count<2||!ReferenceEquals(result.Queue[0],queue[0])||!result.Resources.Matches(result.Queue))throw new InvalidOperationException("Playback preparation ownership mismatch");
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                startupTrace79.jobCompletedFrame=Time.frameCount;startupTrace79.jobCompletedTicks=began;startupTrace79.jobCompletedWall=Time.realtimeSinceStartupAsDouble;
                var t=result.Timing;startupTrace79.callerThreadId=t.CallerThreadId;startupTrace79.workerThreadId=t.WorkerThreadId;
                startupTrace79.buildWorkerMs=t.BuildMs;startupTrace79.resourceWorkerMs=t.ResourceMs;startupTrace79.totalWorkerMs=t.TotalMs;startupTrace79.workerQueueMs=t.QueueWaitMs;
                startupTrace79.workerQueuedTicks=t.QueuedAtTicks;startupTrace79.workerStartedTicks=t.StartedAtTicks;startupTrace79.workerFinishedTicks=t.FinishedAtTicks;
                startupQueue79=result.Queue.ToArray();startupResources79=result.Resources;
#endif
                for(int i=1;i<result.Queue.Count;i++)queue.Add(result.Queue[i]);
                commandResourcePlan=result.Resources;commandResourceOwner=bank;
                bool held=startupHolding79;startupRequest79=null;startupHolding79=false;startupJob79.Dispose();startupJob79=null;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                startupTrace79.pending=false;startupTrace79.tailInstalledFrame=Time.frameCount;startupTrace79.tailInstalledTicks=StartupStamp79();startupTrace79.tailInstalledWall=Time.realtimeSinceStartupAsDouble;
                if(held)startupTrace79.holdMs=StartupMs79(startupTrace79.tailInstalledTicks-startupTrace79.headEndedTicks);
#endif
                long generation=startupGeneration79;
                if(held){awaitingPlaybackPose=true;playbackPoseAnchor=false;Next();}
                if(generation!=startupGeneration79)return;
                StartCoroutine(PrefetchQueuePresentation(commandResourcePlan.All));
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                startupTrace79.mainInstallMs=StartupMs79(StartupStamp79()-began);
#endif
            }catch(Exception e){if(ownedBoard==board&&ownedGeneration==startupGeneration79)FailStartup79(e,ownedBoard);}
        }
        void FailStartup79(Exception error,BoardModel owner=null){
            owner=owner??(startupRequest79==null?board:startupRequest79.board);
            CancelStartup79(true);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            startupTrace79.pending=false;startupTrace79.workerFailed=true;startupTrace79.error=error.GetType().Name+": "+error.Message;
#endif
            if(owner!=board||board==null)return;
            queue.Clear();queueIndex=0;current=null;preparing=false;ClearCommandResources();awaitingPlaybackPose=playbackPoseAnchor=false;
            if(!RecoverFirstPresentationFault||presentationFaultRecovered)board.RecordPresentationFault("playback: "+error.GetType().Name+": "+error.Message);
            presentationFaultRecovered=true;idle=board.Snapshot();
            selected=pressed=null;pendingGesture.Clear();uiHint="";feedback.Play("ui_invalid",.65f);
            Debug.LogException(error,this);TurnSettled?.Invoke(board.Status);
        }
    }
}

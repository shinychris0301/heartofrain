using System;
using System.Collections.Generic;
using System.Linq;

namespace HeartOfTheRain.M48 {
    [Serializable] public sealed class ReplayPlaybackReport {
        public string milestone="M52 R1",runId,unity,platform,startedUTC,finishedUTC,status="IN_PROGRESS",message="",finalStatus="",finalFingerprint="";
        public int level,seed,expectedActions,settledActions,width,height;
        public bool recordingWasActive;
        public string scope="Observed action/settling checks in the running player. Image quality, sound sync and human difficulty require separate review.";
    }
    [Serializable] public sealed class ReviewSessionRun {
        public int level,seed,expectedActions,settledActions;
        public string runId="",status="NOT_RUN",message="",replayFile="",captureFile="",captureStatus="NOT_REQUESTED";
        public string visualReview="PENDING",notes="";
    }
    [Serializable] public sealed class ReviewSessionReport {
        public string milestone="M52 R1",sessionId,unity,platform,startedUTC,finishedUTC="",status="READY";
        public string fixtureSha256,importReport="Unity_Import_Report.json",message="";
        public bool captureRequested;
        public string visualStatus="PENDING",devicePerformance="NOT_REVIEWED",humanDifficulty="NOT_REVIEWED";
        public List<ReviewSessionRun> runs=new List<ReviewSessionRun>();
        public List<string> consoleErrors=new List<string>();
        public string scope="Five seeded Unity replays. Logic completion and file presence do not approve image quality, audio synchronization, all power-up coverage, device performance or human difficulty.";
    }
    public sealed class ReviewSessionLedger {
        public ReviewSessionReport Report {get;private set;}
        public ReviewSessionRun Current {get;private set;}
        public bool Active=>Report.status=="RUNNING";
        public ReviewSessionLedger(CampaignReplaySet set,bool capture) {
            if(set==null||set.runs==null||set.runs.Any(r=>r==null)||!set.runs.Select(r=>r.level).OrderBy(n=>n).SequenceEqual(CampaignValidation.RequiredReplays))
                throw new ArgumentException("Expected exactly the five approved replay fixtures.");
            Report=new ReviewSessionReport{sessionId=Guid.NewGuid().ToString("N"),startedUTC=DateTime.UtcNow.ToString("o"),captureRequested=capture,status="RUNNING"};
            foreach(var n in CampaignValidation.RequiredReplays) {
                var r=set.runs.Single(x=>x.level==n);
                if(r.seed<=0||r.actions==null||r.actions.Length==0)throw new ArgumentException("Incomplete replay fixture.");
                Report.runs.Add(new ReviewSessionRun{level=n,seed=r.seed,expectedActions=r.actions.Length,captureStatus=capture?"PENDING":"NOT_REQUESTED"});
            }
        }
        public ReviewSessionRun BeginNext() {
            if(!Active||Current!=null)throw new InvalidOperationException("Session is not ready for another run.");
            Current=Report.runs.FirstOrDefault(r=>r.status=="NOT_RUN");
            if(Current==null)throw new InvalidOperationException("No remaining replay.");
            Current.status="RUNNING";return Current;
        }
        public void BindRun(string id) {
            if(Current==null||!string.IsNullOrEmpty(Current.runId)||string.IsNullOrEmpty(id))throw new InvalidOperationException("Invalid replay identity binding.");
            Current.runId=id;
        }
        public void Complete(ReplayPlaybackReport replay,string replayFile,string captureFile,bool captureComplete,string captureDetail) {
            if(!Active||Current==null)throw new InvalidOperationException("No active session replay.");
            var row=Current;row.replayFile=replayFile??"";row.captureFile=captureFile??"";
            row.captureStatus=Report.captureRequested?(captureComplete?"FILE_PRESENT":"FAILED"):"NOT_REQUESTED";
            if(replay!=null)row.settledActions=replay.settledActions;
            if(replay==null||string.IsNullOrEmpty(row.runId)||replay.runId!=row.runId||replay.level!=row.level||replay.seed!=row.seed) {Fail("Missing, stale or mismatched replay result.");return;}
            if(string.IsNullOrEmpty(row.replayFile)||replay.status!="PASS_REPLAY_ACTIONS_AND_SETTLING"||replay.finalStatus!="Won"||replay.expectedActions!=row.expectedActions||replay.settledActions!=row.expectedActions) {Fail("Replay did not complete all expected actions: "+replay.message);return;}
            if(Report.captureRequested&&(!captureComplete||!replay.recordingWasActive||string.IsNullOrEmpty(captureFile))) {Fail("Capture is incomplete: "+captureDetail);return;}
            row.status="PASS_REPLAY";row.message="Recorded actions and settling verified. Visual review remains separate.";Current=null;
            if(Report.runs.All(r=>r.status=="PASS_REPLAY")){Report.status="PASS_REPLAY_SUITE";Report.finishedUTC=DateTime.UtcNow.ToString("o");}
        }
        public void Fail(string reason) {
            if(!Active)return;
            if(Current!=null){Current.status="FAIL_REPLAY";Current.message=reason;Current=null;}
            Report.status="FAIL_REPLAY_SUITE";Report.message=reason;Report.finishedUTC=DateTime.UtcNow.ToString("o");
        }
        public void Cancel(string reason) {
            if(!Active)return;
            if(Current!=null){Current.status="CANCELLED";Current.message=reason;Current=null;}
            Report.status="CANCELLED";Report.message=reason;Report.finishedUTC=DateTime.UtcNow.ToString("o");
        }
        public static void SetVisualReview(ReviewSessionReport report,int level,string verdict,string notes) {
            if(report==null||report.status=="RUNNING")throw new InvalidOperationException("Finish the session before visual review.");
            if(!new[]{"PENDING","ACCEPTED","NEEDS_CHANGES"}.Contains(verdict))throw new ArgumentException("Invalid visual verdict.");
            var row=report.runs.Single(r=>r.level==level);
            if(row.status!="PASS_REPLAY"&&verdict=="ACCEPTED")throw new InvalidOperationException("An incomplete replay cannot be approved.");
            row.visualReview=verdict;row.notes=notes??"";
            report.visualStatus=report.runs.Any(r=>r.visualReview=="NEEDS_CHANGES")?"NEEDS_CHANGES":
                report.status=="PASS_REPLAY_SUITE"&&report.runs.All(r=>r.visualReview=="ACCEPTED")?"ACCEPTED_BY_REVIEWER":"PENDING";
        }
        public static void MarkInterrupted(ReviewSessionReport report) {
            if(report==null||report.status!="RUNNING")return;
            foreach(var row in report.runs.Where(r=>r.status=="RUNNING")){row.status="INTERRUPTED";row.message="Recovered from an unfinished session.";}
            report.status="INTERRUPTED";report.message="Recovered after interruption. Unfinished runs are not passes; start a fresh session to repeat them.";
            report.finishedUTC=DateTime.UtcNow.ToString("o");report.visualStatus="PENDING";
        }
    }
}

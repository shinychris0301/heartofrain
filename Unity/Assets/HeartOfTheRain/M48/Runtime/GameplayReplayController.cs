using System;
using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.M46;

namespace HeartOfTheRain.M48 {
    public sealed partial class GameplayReviewTools {
        Coroutine replayRoutine;bool replayIntro,replayPriorBlock;BoardModel replayBoard;ReplayPlaybackReport replayReport;
        public bool Replaying {get;private set;}
        public string ActiveReplayId {get;private set;}="";
        public int ReplaySettledActions=>replayReport==null?0:replayReport.settledActions;
        public string ReplayStatus {get;private set;}="";
        public string LastReplayOutput {get;private set;}="";
        public bool StartReplay(int level) {
            if(ManualPlaytestRunning||Replaying||Showcasing||screen==null||!screen.Ready||screen.Busy){ReplayStatus="Wait for the current review to finish.";return false;}
            CampaignReplay run;
            try {
                var text=Resources.Load<TextAsset>("HOTR_Playtests/Campaign_Replays");
                if(text==null)throw new InvalidOperationException("Replay data is missing.");
                var set=JsonUtility.FromJson<CampaignReplaySet>(text.text);
                if(set==null||set.runs==null||set.runs.Any(r=>r==null)||set.runs.Count(r=>r.level==level)!=1)
                    throw new InvalidOperationException("Expected one replay for level "+level+".");
                run=set.runs.First(r=>r.level==level);
                var definitions=screen.uiAssets.boards.levels;
                if(level<1||level>definitions.Length||definitions[level-1]==null)throw new InvalidOperationException("Replay level binding is missing.");
                CampaignValidation.ValidateReplayContract(run,JsonUtility.FromJson<LevelData>(definitions[level-1].text));
            } catch(Exception ex){ReplayStatus="Replay rejected: "+ex.Message;Debug.LogError(ReplayStatus);return false;}
            SetDrawer(false);screen.ResumeReview();
            replayIntro=screen.showLevelIntro;replayPriorBlock=screen.ReviewInputBlocked;
            screen.showLevelIntro=false;Replaying=true;screen.ReviewInputBlocked=true;replayBoard=null;LastReplayOutput="";ActiveReplayId=Guid.NewGuid().ToString("N");
            replayReport=new ReplayPlaybackReport{runId=ActiveReplayId,unity=Application.unityVersion,platform=Application.platform.ToString(),startedUTC=DateTime.UtcNow.ToString("o"),level=run.level,seed=run.seed,expectedActions=run.actions.Length,width=Screen.width,height=Screen.height,recordingWasActive=Capturing};
            ReplayStatus="Loading recorded level "+level+"…";
            try {screen.Load(run.level-1,(uint)run.seed);replayBoard=screen.Model;}catch(Exception ex){FailReplay("Replay stopped: "+ex.Message);FinishReplay();return false;}
            replayRoutine=StartCoroutine(GuardReplay(run));return true;
        }
        IEnumerator GuardReplay(CampaignReplay run) {
            // Delay once so a Coroutine handle exists before any failure or completion.
            yield return null;var sequence=Replay(run);
            try {
                while(true) {
                    bool more=false;object next=null;Exception failure=null;
                    try {more=sequence.MoveNext();if(more)next=sequence.Current;}catch(Exception ex){failure=ex;}
                    if(failure!=null){FailReplay("Replay stopped: "+failure.Message);break;}
                    if(!more)break;yield return next;
                }
            } finally {(sequence as IDisposable)?.Dispose();FinishReplay();}
        }
        IEnumerator Replay(CampaignReplay run) {
            yield return null;
            for(int i=0;i<run.actions.Length;i++) {
                while(screen.Paused){CheckReplayBoard();yield return null;}
                CheckReplayBoard();ReplayStatus="Level "+run.level+" · recorded move "+(i+1)+" / "+run.actions.Length;
                string error;if(!screen.ReviewReplayMove(run.actions[i],out error))throw new InvalidOperationException(error);
                float activeWait=0;
                while(screen.Busy) {
                    CheckReplayBoard();if(!screen.Paused)activeWait+=Time.unscaledDeltaTime;
                    if(activeWait>120)throw new TimeoutException("Animation did not settle within 120 active seconds.");
                    yield return null;
                }
                CheckReplayBoard();replayReport.settledActions=i+1;
                // A win modal pauses the game; completion must not wait for it to close.
                if(i+1<run.actions.Length) {
                    float gap=0;while(gap<.25f){CheckReplayBoard();if(!screen.Paused)gap+=Time.unscaledDeltaTime;yield return null;}
                }
            }
            if(screen.Model.Status!=run.expectedStatus)throw new InvalidOperationException("Final result differs from the fixture.");
            replayReport.status="PASS_REPLAY_ACTIONS_AND_SETTLING";ReplayStatus="Replay verified: "+screen.Model.Status;
        }
        void CheckReplayBoard(){
            if(screen==null||screen.Model!=replayBoard)throw new InvalidOperationException("Level changed during replay.");
            replayReport.recordingWasActive|=Capturing;
        }
        void FailReplay(string message){ReplayStatus=message;if(replayReport!=null)replayReport.status="FAIL_REPLAY";Debug.LogError(message);}
        void FinishReplay(){
            if(!Replaying)return;Replaying=false;replayRoutine=null;
            if(screen!=null){screen.ReviewInputBlocked=replayPriorBlock;screen.showLevelIntro=replayIntro;}
            if(replayReport==null)return;
            if(replayReport.status=="IN_PROGRESS")replayReport.status="STOPPED";
            replayReport.message=ReplayStatus;replayReport.finishedUTC=DateTime.UtcNow.ToString("o");
            if(replayBoard!=null){replayReport.finalStatus=replayBoard.Status;replayReport.finalFingerprint=CampaignReplayRules.Fingerprint(replayBoard);}
            try {
                var folder=Path.Combine(Application.persistentDataPath,"M48Review");Directory.CreateDirectory(folder);
                LastReplayOutput=Path.Combine(folder,"replay_L"+replayReport.level.ToString("000")+"_"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff")+".json");
                File.WriteAllText(LastReplayOutput,JsonUtility.ToJson(replayReport,true));Debug.Log("Replay report: "+LastReplayOutput);
            }catch(Exception ex){Debug.LogError("Could not save replay report: "+ex.Message);LastReplayOutput="";}
            replayReport=null;replayBoard=null;
        }
        public void StopReplay(){
            if(!Replaying)return;ReplayStatus="Replay stopped by reviewer.";
            if(replayReport!=null)replayReport.status="STOPPED_BY_REVIEWER";
            if(replayRoutine!=null)StopCoroutine(replayRoutine);
            // Explicit cleanup also covers Unity stopping an iterator without disposing it.
            FinishReplay();
        }
    }
}

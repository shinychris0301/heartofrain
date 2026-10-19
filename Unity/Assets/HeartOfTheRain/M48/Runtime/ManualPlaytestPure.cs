using System;
using System.Collections.Generic;
using System.Linq;
using HeartOfTheRain.M46;

namespace HeartOfTheRain.M48 {
    // Emitted only by the normal pointer/booster input path, before animation starts.
    [Serializable] public sealed class PlayerActionRecord {
        public string kind,reason; public int x,y,toX=-1,toY=-1,booster=-1;
        public bool accepted;
    }
    [Serializable] public sealed class PlaytestBoardState {
        public int moves,turn; public string status,fingerprint; public Goal[] goals;
        public static PlaytestBoardState Read(BoardModel board){return new PlaytestBoardState{
            moves=board.Moves,turn=board.Turn,status=board.Status,fingerprint=CampaignReplayRules.Fingerprint(board),
            goals=board.Goals.OrderBy(g=>g.Key).Select(g=>new Goal{family=g.Key,count=g.Value}).ToArray()};}
    }
    [Serializable] public sealed class ManualPlaytestAction {
        public int sequence;public PlayerActionRecord input;public PlaytestBoardState after;
        public double activeSeconds;public bool animationSettled;
    }
    [Serializable] public sealed class ManualPlaytestAttempt {
        public string id=Guid.NewGuid().ToString("N"),startedUTC,finishedUTC,outcome="IN_PROGRESS",endReason;
        public int level,attemptForLevel,acceptedActions,rejectedActions,settledActions;
        public uint seed;public string levelDefinitionSha256;
        public PlaytestBoardState initial,latest;
        public int[] boostersUsed=new int[4];public bool assisted;
        public double activeSeconds,pausedSeconds,animationSeconds,decisionSeconds;
        public List<ManualPlaytestAction> actions=new List<ManualPlaytestAction>();
    }
    [Serializable] public sealed class ManualPlaytestReport {
        public string milestone="M53 R1",schema="hotr.manual-playtest.v1",sessionId=Guid.NewGuid().ToString("N");
        public string startedUTC,finishedUTC,status="RUNNING",endReason,unity,platform,environment,notes="";
        public int width,height;public bool recordingWasActive;
        public List<ManualPlaytestAttempt> attempts=new List<ManualPlaytestAttempt>();
        public string scope="Opt-in normal input observations. No automatic proof of a human participant, first exposure, visual quality, performance or difficulty. Replays and staged effects are excluded. Booster-assisted attempts must be analyzed separately. RUNNING reports are incomplete checkpoints.";
    }
    public sealed class ManualPlaytestLedger {
        public ManualPlaytestReport Report {get;}=new ManualPlaytestReport();
        public ManualPlaytestAttempt Current {get;private set;}
        public bool Active=>Report.status=="RUNNING";
        public ManualPlaytestLedger(){Report.startedUTC=Utc();}
        static string Utc()=>DateTime.UtcNow.ToString("o");
        public static string Environment(bool editor,bool mobile)=>editor?"EDITOR_MANUAL_INPUT":mobile?"MOBILE_MANUAL_INPUT":"DESKTOP_MANUAL_INPUT";
        public void BeginAttempt(BoardModel board,uint seed,string hash){
            if(!Active||Current!=null&&Current.outcome=="IN_PROGRESS")throw new InvalidOperationException("Finish the current attempt first.");
            if(seed==0||board==null||board.Status!="Playing"||string.IsNullOrEmpty(hash))throw new ArgumentException("A fresh board, seed and definition hash are required.");
            Current=new ManualPlaytestAttempt{level=board.Level.globalLevel,seed=seed,levelDefinitionSha256=hash,startedUTC=Utc(),initial=PlaytestBoardState.Read(board),latest=PlaytestBoardState.Read(board),attemptForLevel=1+Report.attempts.Count(a=>a.level==board.Level.globalLevel)};
            Report.attempts.Add(Current);
        }
        public void Tick(double seconds,bool paused,bool animating,bool canAct){
            if(!Active||Current==null||Current.outcome!="IN_PROGRESS"||double.IsNaN(seconds)||double.IsInfinity(seconds)||seconds<0)return;
            if(paused)Current.pausedSeconds+=seconds;
            else {Current.activeSeconds+=seconds;if(animating)Current.animationSeconds+=seconds;else if(canAct)Current.decisionSeconds+=seconds;}
        }
        public void Record(PlayerActionRecord input,BoardModel board){
            if(!Active||Current==null||Current.outcome!="IN_PROGRESS")return;
            if(Current.actions.Any(a=>a.input.accepted&&!a.animationSettled))throw new InvalidOperationException("Previous action has not settled.");
            if(input==null||!(input.kind=="swap"||input.kind=="tap"||input.kind=="booster"))throw new ArgumentException("Unknown player action.");
            if(input.kind=="booster"&&(input.booster<0||input.booster>3))throw new ArgumentException("Unknown booster.");
            Current.latest=PlaytestBoardState.Read(board);
            Current.actions.Add(new ManualPlaytestAction{sequence=Current.actions.Count+1,input=input,after=Current.latest,activeSeconds=Current.activeSeconds});
            if(input.accepted){Current.acceptedActions++;if(input.kind=="booster"){Current.boostersUsed[input.booster]++;Current.assisted=true;}}
            else Current.rejectedActions++;
            // Logical Won/Out of moves is not a rendered completion. Settle owns the result.
        }
        public void Settle(BoardModel board){
            if(!Active||Current==null||Current.outcome!="IN_PROGRESS")return;
            var pending=Current.actions.LastOrDefault(a=>a.input.accepted&&!a.animationSettled);
            if(pending==null)return;
            pending.animationSettled=true;Current.settledActions++;Current.latest=PlaytestBoardState.Read(board);
            if(board.Status!="Playing")FinishAttempt(board.Status=="Won"?"WON":board.Status=="Out of moves"?"OUT_OF_MOVES":"BOARD_ERROR","Final animation settled: "+board.Status);
        }
        public void FinishAttempt(string outcome,string reason){
            if(Current==null||Current.outcome!="IN_PROGRESS")return;
            Current.outcome=Current.actions.Any(a=>a.input.accepted&&!a.animationSettled)?"INTERRUPTED_ANIMATION":outcome;
            Current.endReason=reason;Current.finishedUTC=Utc();
        }
        public void Finish(string status,string reason){
            if(!Active)return;
            FinishAttempt("ABANDONED",reason);Report.status=status;Report.endReason=reason;Report.finishedUTC=Utc();
        }
    }
}

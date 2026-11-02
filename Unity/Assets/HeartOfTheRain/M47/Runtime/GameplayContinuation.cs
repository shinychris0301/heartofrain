using System;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.App.Profile;
namespace HeartOfTheRain.M47 {
    public sealed partial class GameplayScreen {
        public bool ContinueCheckpointPending {get;private set;}
        public void ApplyContinuation(ContinueReceipt receipt){
            if(receipt==null||receipt.outcome!="Applied"||Busy)throw new InvalidOperationException("Continue is not ready");
            var before=board.Checkpoint();string raw=JsonUtility.ToJson(before);
            if(raw!=receipt.afterCheckpoint){
                if(ProfileJson.Hash(raw)!=receipt.beforeHash)throw new InvalidOperationException("Continue board changed");
                var candidate=BoardModel.FromCheckpoint(board.Level,before);candidate.ApplyContinue(receipt.operation,receipt.movesAfter);
                if(JsonUtility.ToJson(candidate.Checkpoint())!=receipt.afterCheckpoint)throw new InvalidOperationException("Continue receipt does not match this board");
                board.ApplyContinue(receipt.operation,receipt.movesAfter);
            }
            ContinueCheckpointPending=true;idle=board.Snapshot();resultShown=false;previousMoves=board.Moves;uiHint="";pendingGesture.Clear();CancelPointer();
        }
        public void ContinueCheckpointConsumed(){ContinueCheckpointPending=false;}
    }
}

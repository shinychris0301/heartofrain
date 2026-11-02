using System;
using HeartOfTheRain.M46;

namespace HeartOfTheRain.App.ServerVerification {
    [Serializable] public sealed class ReplaySourcePin { public string path,sha256;public long bytes; }
    [Serializable] public sealed class ReplayLevelPin { public int level,moves,columns,rows,tileSeed;public string id,path,sha256; }
    [Serializable] public sealed class ReplayPins {
        public int version=1;public string unity,scope;
        public ReplaySourcePin[] sources;public ReplayLevelPin[] levels;
    }
    // Only an authenticated server broker may create this file. Receipt syntax
    // is not proof of payment: the broker must read its durable ledger itself.
    [Serializable] public sealed class ReplayJob {
        public int version,level,initialMoves;public uint seed;
        public string jobId,playerId,attemptId,pinsSHA256,levelSHA256,startReceiptId;
        public int[] starting;public ReplayAction[] actions;public ReplayReceipt[] receipts;
    }
    [Serializable] public sealed class ReplayAction {
        public int index,ax,ay,bx,by,tool,movesAfter;public string kind,receiptId;
    }
    [Serializable] public sealed class ReplayReceipt {
        public string receiptId,attemptId,kind;public int actionIndex,tool,coins,quantity,movesAfter;
    }
    [Serializable] public sealed class ReplayActionResult {
        public int index,moves,turn;public string kind,status,checkpointSHA256;
    }
    [Serializable] public sealed class ReplayOutput {
        public int version=1,level,actions,moves,turn,remainingGoals;
        public string status="FAIL",code="replay_rejected",unity,jobSHA256,pinsSHA256,levelSHA256,checkpointSHA256,outcome;
        public bool productionEnabled=false,financialMutation=false;
        public ReplayActionResult[] actionResults;
    }
    public sealed class ReplayExecution {
        public ReplayOutput output;public BoardCheckpoint checkpoint;
        // Native tests may retain exact full states. The worker never writes
        // these boards, private counters or pseudonymous identities to logs.
        public string[] checkpointJSON;
    }
    public sealed class ReplayRejected : Exception {
        public readonly string Code;
        public ReplayRejected(string code):base(code){Code=code;}
    }
}

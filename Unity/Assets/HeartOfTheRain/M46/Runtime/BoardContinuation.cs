using System;
using System.Linq;
namespace HeartOfTheRain.M46 {
    [Serializable] public sealed class BoardCheckpoint {
        public int version=1,columns,rows,nextId,quietMoves,growthUsed,activationSerial,powerOrigin;
        public string levelId,lastContinue;public uint random;public bool mossHit,startingPowersApplied;public float powerStart;
        public BoardSnapshot board;public string[] acceptedDamage;public int[] queued;
    }
    public sealed partial class BoardModel {
        string lastContinue;
        // Only settled boards can be checkpointed. Geometry remains owned by
        // the approved level asset; the checkpoint retains RNG and identities.
        public BoardCheckpoint Checkpoint(){
            if(pending.Count!=0)throw new InvalidOperationException("The resolver is still active");
            Validate();return new BoardCheckpoint{levelId=Level.id,columns=Level.columns,rows=Level.rows,board=Snapshot(),random=random,nextId=nextId,quietMoves=QuietMoves,growthUsed=GrowthUsed,mossHit=mossHit,startingPowersApplied=startingPowersApplied,activationSerial=activationSerial,powerOrigin=powerOrigin,powerStart=powerStart,lastContinue=lastContinue,acceptedDamage=acceptedDamage.OrderBy(s=>s,StringComparer.Ordinal).ToArray(),queued=queued.OrderBy(v=>v).ToArray()};
        }
        public static BoardModel FromCheckpoint(LevelData level,BoardCheckpoint state){
            if(state==null||state.version!=1||state.levelId!=level.id||state.columns!=level.columns||state.rows!=level.rows||state.random==0||state.board==null||state.board.pieces==null||state.board.goals==null||state.nextId<1||state.quietMoves<0||state.growthUsed<0||state.board.turn<0||state.board.moves<0)throw new InvalidOperationException("Invalid board checkpoint");
            var model=new BoardModel(level);model.Pieces.Clear();model.Goals.Clear();
            foreach(var p in state.board.pieces){if(p==null||p.id<1||p.id>=state.nextId)throw new InvalidOperationException("Invalid checkpoint identity");model.Pieces.Add(model.Key(p.x,p.y),p.Copy());}
            foreach(var goal in state.board.goals)model.Goals.Add(goal.family,goal.count);
            if(!model.Goals.Keys.OrderBy(k=>k).SequenceEqual(level.goals.Select(g=>g.family).OrderBy(k=>k)))throw new InvalidOperationException("Checkpoint goals changed");
            model.random=state.random;model.nextId=state.nextId;model.Moves=state.board.moves;model.Turn=state.board.turn;model.Status=state.board.status;model.QuietMoves=state.quietMoves;model.GrowthUsed=state.growthUsed;model.mossHit=state.mossHit;model.activationSerial=state.activationSerial;model.powerOrigin=state.powerOrigin;model.powerStart=state.powerStart;model.lastContinue=state.lastContinue;
            foreach(var s in state.acceptedDamage??new string[0])model.acceptedDamage.Add(s);foreach(int id in state.queued??new int[0])model.queued.Add(id);
            model.startingPowersApplied=state.startingPowersApplied;model.Validate();return model;
        }
        // The caller has committed a durable receipt first. An absolute move
        // state and command identity make replay safe without resetting RNG.
        public void ApplyContinue(string operation,int movesAfter){
            if(string.IsNullOrEmpty(operation)||movesAfter<1||movesAfter>999)throw new ArgumentException("Invalid continue receipt");
            if(lastContinue==operation)return;
            if(Status!="Out of moves"||Moves!=0||Goals.Values.All(n=>n==0)||pending.Count!=0)throw new InvalidOperationException("This board cannot continue");
            Moves=movesAfter;Status="Playing";lastContinue=operation;Validate();
        }
    }
}

using System;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.RuStore;

namespace HeartOfTheRain.App.ServerGameplay {
    [Serializable] public sealed class ServerMove {
        public int index,x,y,toX=-1,toY=-1; public string kind;
    }
    [Serializable] public sealed class ServerModelState {
        public string outcome,checkpointSHA256; public int moves,turn;
    }
    [Serializable] public sealed class ServerDisplayReceipt {
        public string receiptId,outcome; public int awardedCoins,awardedStars,completedBefore,completedAfter,livesAfter; public bool firstClear;
    }
    [Serializable] public sealed class ServerBrokerOperation {
        public string operationId,attemptId,state,code,paidReceiptId; public int prefixRevision,acceptedActions,addedMoves;
        public ServerModelState model; public RuStoreServerWallet wallet; public RuStoreServerAttempt attempt;
        public ServerDisplayReceipt displayReceipt; public bool productionEnabled,acknowledgementRequired;
    }
    public sealed class ServerGameReply<T> where T:class {
        public readonly T value; public readonly string error; public readonly bool unknown;
        public bool Succeeded=>value!=null&&error==null;
        ServerGameReply(T value,string error,bool unknown){this.value=value;this.error=error;this.unknown=unknown;}
        public static ServerGameReply<T> Ok(T value)=>new ServerGameReply<T>(value??throw new ArgumentNullException(nameof(value)),null,false);
        public static ServerGameReply<T> Fail(string error,bool unknown=false)=>new ServerGameReply<T>(null,error??"ServerUnavailable",unknown);
    }
    [Serializable] public class ServerVerifyRequest {
        public string commandId; public int expectedPrefixRevision; public ServerMove[] actions=new ServerMove[0];
    }
    [Serializable] public sealed class ServerToolRequest:ServerVerifyRequest {
        public long expectedWalletRevision; public int tool,x,y;
    }
    [Serializable] public sealed class ServerContinueRequest:ServerVerifyRequest { public long expectedWalletRevision; }
    public interface IServerGameplayBroker {
        void Verify(string attempt,ServerVerifyRequest request,Action<ServerGameReply<ServerBrokerOperation>> done);
        void Tool(string attempt,ServerToolRequest request,Action<ServerGameReply<ServerBrokerOperation>> done);
        void Continue(string attempt,ServerContinueRequest request,Action<ServerGameReply<ServerBrokerOperation>> done);
        void Operation(string attempt,string command,bool resume,Action<ServerGameReply<ServerBrokerOperation>> done);
        void Cancel();
    }
    // One-way UI projection. A missed legacy mutation fails closed instead of
    // silently crediting/debiting a local wallet beside the server wallet.
    public sealed class ServerProfileProjection:IProfileRepository {
        PlayerProfile value=new PlayerProfile{playerId=new string('0',32),coins=0,stars=0,lives=0,maxLives=5,starting=new int[4],tools=new int[4]};
        public PlayerProfile Read()=>UnityEngine.JsonUtility.FromJson<PlayerProfile>(UnityEngine.JsonUtility.ToJson(value));
        public PlayerProfile Commit(long revision,PlayerProfile next)=>throw new InvalidOperationException("ServerWalletIsAuthoritative");
        internal void Apply(RuStoreServerWallet wallet,AttemptRecord attempt){
            var next=new PlayerProfile{playerId=wallet.playerId,revision=wallet.revision,coins=wallet.coins,stars=wallet.stars,lives=wallet.lives,maxLives=wallet.maxLives,
                completed=wallet.completed,currentLevel=wallet.currentLevel,starting=(int[])wallet.starting.Clone(),tools=(int[])wallet.tools.Clone(),livesRefillDueUnix=wallet.nextLifeAt};
            if(attempt!=null)next.attempts.Add(attempt); value=next;
        }
    }
}

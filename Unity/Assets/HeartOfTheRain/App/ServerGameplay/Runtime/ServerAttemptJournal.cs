using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;
using HeartOfTheRain.App.OnlineIdentity;

namespace HeartOfTheRain.App.ServerGameplay {
    [Serializable] public sealed class ServerPendingCommand {
        public string operation,commandId,attemptId,payload; public long expectedRevision;
    }
    [Serializable] public sealed class ServerAttemptDocument {
        public int version=1;public long revision;public string origin,playerId;
        public string attemptId,configHash,checkpoint,phase="",view="offer";public int level,initialMoves,prefixRevision,acceptedActions;public long seed;
        public int[] selected=new int[4];public List<ServerMove> delta=new List<ServerMove>();
        public int paidTool=-1,paidX,paidY;
        public bool hasPending;public ServerPendingCommand pending=new ServerPendingCommand();
        public bool hasAbandonedPending;public ServerPendingCommand abandonedPending=new ServerPendingCommand();
        public bool hasLastOperation;public ServerBrokerOperation lastOperation=new ServerBrokerOperation();
        public bool hasAttempt;public HeartOfTheRain.App.RuStore.RuStoreServerAttempt attempt=new HeartOfTheRain.App.RuStore.RuStoreServerAttempt();
    }
    // Credential-free durable intent. Neither the checksum nor a cached board
    // authorizes rewards: the server reconstructs every accepted prefix from
    // its own seed/configuration and actual financial receipts.
    public sealed class ServerAttemptJournal {
        [Serializable] sealed class Envelope{public string payload,sha256;}
        readonly string path,origin,player;const int Limit=2097152;readonly UTF8Encoding utf8=new UTF8Encoding(false,true);
        public Action<string> VerificationCheckpoint;
        public ServerAttemptJournal(string path,string origin,string player){this.path=Path.GetFullPath(path);this.origin=origin;this.player=player;if(!IdentityProtocol82.Id(player)||string.IsNullOrEmpty(origin))throw new ArgumentException("ServerJournalBindingRequired");Directory.CreateDirectory(Path.GetDirectoryName(this.path));}
        static T Copy<T>(T value)=>JsonUtility.FromJson<T>(JsonUtility.ToJson(value));
        void Validate(ServerAttemptDocument value){
            if(value==null||value.version!=1||value.revision<0||value.origin!=origin||value.playerId!=player||value.delta==null||value.delta.Count>128||value.acceptedActions<0||value.acceptedActions>1000||value.prefixRevision<0||value.selected==null||value.selected.Length!=4||(value.checkpoint??"").Length>1000000)throw new InvalidOperationException("ServerJournalInvalid");
            if(value.hasPending&&(value.pending==null||!IdentityProtocol82.Id(value.pending.commandId)||(value.pending.payload??"").Length>65536||string.IsNullOrEmpty(value.pending.operation)))throw new InvalidOperationException("ServerPendingIntentInvalid");
            if(value.selected.Any(n=>n<0||n>1)||value.acceptedActions+value.delta.Count>1000||!new[]{"","Awaiting","Purchased","ToolCommitted"}.Contains(value.phase)||(value.view!="offer"&&value.view!="shop"))throw new InvalidOperationException("ServerJournalStateInvalid");
            for(int n=0;n<value.delta.Count;n++){
                var move=value.delta[n];if(move==null||move.index!=value.acceptedActions+n||move.index>999||(move.kind!="Swap"&&move.kind!="Tap")||move.x<0||move.x>14||move.y<0||move.y>14||move.toX< -1||move.toX>14||move.toY< -1||move.toY>14)throw new InvalidOperationException("ServerMoveIntentInvalid");
            }
            if(value.hasAttempt&&(!IdentityProtocol82.Id(value.attemptId)||!IdentityProtocol82.Digest(value.configHash)||value.seed<1||value.seed>uint.MaxValue||value.level<1||value.level>50||value.attempt==null||value.attempt.attemptId!=value.attemptId))throw new InvalidOperationException("ServerAttemptBindingInvalid");
        }
        ServerAttemptDocument ReadCore(){
            if(!File.Exists(path))return new ServerAttemptDocument{origin=origin,playerId=player};
            ServerAttemptDocument value=null;bool damaged=false;
            using(var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)){
                if(file.Length<2||file.Length>Limit)damaged=true;
                else{
                    var bytes=new byte[(int)file.Length];int at=0;while(at<bytes.Length){int n=file.Read(bytes,at,bytes.Length-at);if(n<=0)throw new IOException();at+=n;}
                    try{var envelope=JsonUtility.FromJson<Envelope>(utf8.GetString(bytes));if(envelope==null||!IdentityProtocol82.Digest(envelope.sha256)||IdentityProtocol82.Sha(utf8.GetBytes(envelope.payload??""))!=envelope.sha256)damaged=true;else value=JsonUtility.FromJson<ServerAttemptDocument>(envelope.payload);}catch(ArgumentException){damaged=true;}
                }
            }
            if(!damaged){Validate(value);return value;}
            // A damaged journal must not hold Home on "—" for good. The server owns the wallet and the
            // attempt, so start empty and rebind from it. The backup is not used: an older unresolved
            // command for an ended attempt would block the session. Lost: moves not yet verified.
            string corrupt=path+".corrupt";if(File.Exists(corrupt))File.Delete(corrupt);File.Move(path,corrupt);if(File.Exists(path+".bak"))File.Delete(path+".bak");
            return new ServerAttemptDocument{origin=origin,playerId=player};
        }
        public ServerAttemptDocument Read(){using(var held=new FileStream(path+".lock",FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None))return Copy(ReadCore());}
        public ServerAttemptDocument Save(ServerAttemptDocument value){
            Validate(value);string temporary=null;
            try{using(var held=new FileStream(path+".lock",FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)){
                var before=ReadCore();if(before.revision!=value.revision)throw new InvalidOperationException("ServerJournalConflict");
                var next=Copy(value);next.revision=checked(value.revision+1);if(!next.hasPending)next.pending=new ServerPendingCommand();if(!next.hasLastOperation)next.lastOperation=new ServerBrokerOperation();
                string payload=JsonUtility.ToJson(next);byte[] bytes=utf8.GetBytes(JsonUtility.ToJson(new Envelope{payload=payload,sha256=IdentityProtocol82.Sha(utf8.GetBytes(payload))}));if(bytes.Length>Limit)throw new InvalidOperationException("ServerJournalSize");
                temporary=path+"."+Guid.NewGuid().ToString("N")+".tmp";using(var file=new FileStream(temporary,FileMode.CreateNew,FileAccess.Write,FileShare.None)){file.Write(bytes,0,bytes.Length);file.Flush(true);}
                VerificationCheckpoint?.Invoke("BeforeCommit");if(File.Exists(path))File.Replace(temporary,path,path+".bak");else File.Move(temporary,path);temporary=null;VerificationCheckpoint?.Invoke("AfterCommit");return Copy(next);
            }}finally{if(temporary!=null&&File.Exists(temporary))File.Delete(temporary);}
        }
    }
}

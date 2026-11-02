using System;
using System.IO;
using System.Text;
using UnityEngine;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.OnlineSocial;

namespace HeartOfTheRain.App.ServerRewards {
    [Serializable] public sealed class RewardIntent {public string kind,target,commandId,payload;}
    [Serializable] public sealed class RewardIntentDocument {public int version=1;public long revision;public string origin,playerId;public bool hasPending;public RewardIntent pending=new RewardIntent();}
    // This checksum detects accidental corruption; it is not reward authority.
    // The file contains only a public request, never credentials or wallet data.
    public sealed class ServerRewardJournal {
        [Serializable] sealed class Envelope {public string payload,sha256;}
        readonly string path,origin,player;readonly UTF8Encoding utf8=new UTF8Encoding(false,true);const int Limit=32768;
        public Action<string> VerificationCheckpoint;
        public ServerRewardJournal(string path,string origin,string player){this.path=Path.GetFullPath(path);this.origin=origin;this.player=player;if(!IdentityProtocol82.Id(player)||string.IsNullOrEmpty(origin))throw new ArgumentException("RewardJournalBindingRequired");Directory.CreateDirectory(Path.GetDirectoryName(this.path));}
        public static void ValidateIntent(RewardIntent intent){
            if(intent==null||!IdentityProtocol82.Id(intent.commandId)||string.IsNullOrEmpty(intent.target)||intent.target.Length>256||intent.payload==null||intent.payload.Length>8192)throw new InvalidOperationException("RewardIntentInvalid");
            var row=SocialJson82.Read(intent.payload);string idKey=intent.kind=="Daily"?"requestId":"commandId";if(SocialJson82.Text(row,idKey,32)!=intent.commandId)throw new InvalidOperationException("RewardIntentBindingInvalid");
            switch(intent.kind){
                case "Daily":if(row.Count!=6||SocialJson82.Text(row,"offerId",256)!=intent.target)throw new InvalidOperationException("RewardIntentBindingInvalid");var d=JsonUtility.FromJson<HeartOfTheRain.App.Profile.PendingGift>(intent.payload);ServerRewardClient.ParseDaily(JsonUtility.ToJson(new HeartOfTheRain.App.Profile.BackendDecision{playerId=new string('a',32),receiptId=d.offerId,requestId=d.requestId,schedule=d.schedule,day=d.day,step=d.step,grant=d.expectedGrant}),new string('a',32),d);break;
                case "Wellworks":if(row.Count!=2||SocialJson82.Number(row,"level",1,50).ToString(System.Globalization.CultureInfo.InvariantCulture)!=intent.target)throw new InvalidOperationException("RewardIntentBindingInvalid");break;
                case "CupJoin":if(row.Count!=1||intent.target!="join")throw new InvalidOperationException("RewardIntentBindingInvalid");break;
                case "CupClaim":if(row.Count!=2||!IdentityProtocol82.Id(SocialJson82.Text(row,"runId",32))||SocialJson82.Text(row,"runId",32)!=intent.target)throw new InvalidOperationException("RewardIntentBindingInvalid");break;
                default:throw new InvalidOperationException("RewardIntentKindInvalid");
            }
        }
        void Validate(RewardIntentDocument document){if(document==null||document.version!=1||document.revision<0||document.origin!=origin||document.playerId!=player)throw new InvalidOperationException("RewardJournalBindingInvalid");if(document.hasPending)ValidateIntent(document.pending);}
        static RewardIntentDocument Copy(RewardIntentDocument value)=>JsonUtility.FromJson<RewardIntentDocument>(JsonUtility.ToJson(value));
        RewardIntentDocument ReadCore(){
            if(!File.Exists(path))return new RewardIntentDocument{origin=origin,playerId=player};
            // A damaged file holds no authority: the server owns rewards, and a saved claim is
            // idempotent. Use the backup, otherwise start empty. A wrong account stays refused.
            var document=Decode(path);
            if(document==null){string backup=path+".bak";var restored=File.Exists(backup)?Decode(backup):null;string corrupt=path+".corrupt";if(File.Exists(corrupt))File.Delete(corrupt);File.Move(path,corrupt);if(restored!=null)File.Copy(backup,path);else{if(File.Exists(backup))File.Delete(backup);return new RewardIntentDocument{origin=origin,playerId=player};}document=restored;}
            Validate(document);return document;
        }
        RewardIntentDocument Decode(string file){
            byte[] bytes;using(var stream=new FileStream(file,FileMode.Open,FileAccess.Read,FileShare.Read)){if(stream.Length<2||stream.Length>Limit)return null;bytes=new byte[(int)stream.Length];int at=0;while(at<bytes.Length){int read=stream.Read(bytes,at,bytes.Length-at);if(read<=0)throw new IOException();at+=read;}}
            try{var envelope=JsonUtility.FromJson<Envelope>(utf8.GetString(bytes));if(envelope==null||!IdentityProtocol82.Digest(envelope.sha256)||IdentityProtocol82.Sha(utf8.GetBytes(envelope.payload??""))!=envelope.sha256)return null;return JsonUtility.FromJson<RewardIntentDocument>(envelope.payload);}catch(ArgumentException){return null;}
        }
        public RewardIntentDocument Read(){using(var held=new FileStream(path+".lock",FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None))return Copy(ReadCore());}
        public RewardIntentDocument Save(RewardIntentDocument document){Validate(document);string temporary=null;try{using(var held=new FileStream(path+".lock",FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)){
            if(ReadCore().revision!=document.revision)throw new InvalidOperationException("RewardJournalConflict");var next=Copy(document);next.revision=checked(document.revision+1);if(!next.hasPending)next.pending=new RewardIntent();string payload=JsonUtility.ToJson(next);byte[] bytes=utf8.GetBytes(JsonUtility.ToJson(new Envelope{payload=payload,sha256=IdentityProtocol82.Sha(utf8.GetBytes(payload))}));if(bytes.Length>Limit)throw new InvalidOperationException("RewardJournalSize");
            // Keep the full random identifier without repeating the journal
            // filename: deeply bound Windows paths can otherwise exceed260.
            temporary=Path.Combine(Path.GetDirectoryName(path),"r-"+Guid.NewGuid().ToString("N")+".tmp");using(var file=new FileStream(temporary,FileMode.CreateNew,FileAccess.Write,FileShare.None)){file.Write(bytes,0,bytes.Length);file.Flush(true);}VerificationCheckpoint?.Invoke("BeforeCommit");if(File.Exists(path))File.Replace(temporary,path,path+".bak");else File.Move(temporary,path);temporary=null;VerificationCheckpoint?.Invoke("AfterCommit");return Copy(next);
        }}finally{if(temporary!=null&&File.Exists(temporary))File.Delete(temporary);}}
    }
}

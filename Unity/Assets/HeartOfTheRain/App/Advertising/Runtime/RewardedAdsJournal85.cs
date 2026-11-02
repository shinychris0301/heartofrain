using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

namespace HeartOfTheRain.App.Advertising {
    [Serializable] public sealed class AdIntent85 {
        public string origin="",playerId="",opportunityId="",reserveCommandId="",reportCommandId="",claimCommandId="",cancelCommandId="",state="";
        public bool CompletionReported;
    }
    // Credential-free local correlation, not ad-completion or reward authority.
    // A checksum detects corruption; authenticated server reads still decide
    // completion, eligibility and grants. At most one unresolved intent exists.
    public sealed class RewardedAdsJournal85 {
        [Serializable] sealed class Envelope {public int version=1;public string payload,sha256;}
        sealed class JournalFault:Exception {public readonly string Code;public JournalFault(string code){Code=code;}}
        const int Limit=8192;
        static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
        readonly string path;
#if UNITY_EDITOR
        public Action<string,int> VerificationException116;
#endif
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        public Action<string> VerificationCheckpoint;
#endif
        public RewardedAdsJournal85(string path){
            if(string.IsNullOrWhiteSpace(path))throw new ArgumentException("AdJournalPathInvalid");
            this.path=Path.GetFullPath(path);Directory.CreateDirectory(Path.GetDirectoryName(this.path));
        }
        static void Require(bool value,string code){if(!value)throw new JournalFault(code);}
        static bool Hex(string value,int length)=>value!=null&&value.Length==length&&value.All(c=>c>='0'&&c<='9'||c>='a'&&c<='f');
        static bool Origin(string value){
            Uri uri;return value!=null&&value.Length>0&&value.Length<=512&&!value.Any(c=>c<33||c>126)&&Uri.TryCreate(value,UriKind.Absolute,out uri)&&
                (uri.Scheme==Uri.UriSchemeHttps||uri.Scheme==Uri.UriSchemeHttp&&uri.IsLoopback)&&!string.IsNullOrEmpty(uri.Host)&&uri.UserInfo==""&&uri.Query==""&&uri.Fragment==""&&uri.AbsolutePath=="/";
        }
        static string Hash(string value){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(Utf8.GetBytes(value))).Replace("-","").ToLowerInvariant();}
        static AdIntent85 Copy(AdIntent85 value)=>JsonUtility.FromJson<AdIntent85>(JsonUtility.ToJson(value));
        static void ValidateOwner(string origin,string player){Require(Origin(origin)&&Hex(player,32),"AdJournalOwnerInvalid");}
        static void Validate(AdIntent85 value){
            Require(value!=null,"AdJournalIntentInvalid");ValidateOwner(value.origin,value.playerId);
            var commands=new[]{value.reserveCommandId,value.reportCommandId,value.claimCommandId,value.cancelCommandId};
            Require(commands.All(c=>Hex(c,32))&&commands.Distinct(StringComparer.Ordinal).Count()==4,"AdJournalCommandsInvalid");
            Require(new[]{"Reserving","Reserved","CompletionReported","Claiming","Cancelling","Resolved"}.Contains(value.state),"AdJournalStateInvalid");
            Require(value.opportunityId!=null&&(value.opportunityId==""||Hex(value.opportunityId,32)),"AdJournalOpportunityInvalid");
            if(value.state=="Reserving")Require(value.opportunityId==""&&!value.CompletionReported,"AdJournalStateInvalid");
            else if(value.state!="Resolved")Require(Hex(value.opportunityId,32),"AdJournalStateInvalid");
            if(value.state=="Reserved")Require(!value.CompletionReported,"AdJournalStateInvalid");
            if(value.state=="CompletionReported")Require(value.CompletionReported,"AdJournalStateInvalid");
            if(value.CompletionReported)Require(Hex(value.opportunityId,32),"AdJournalStateInvalid");
        }
        static bool Transition(string before,string after){
            if(before==after)return true;
            switch(before){
                case "Reserving":return after=="Reserved"||after=="Resolved";
                case "Reserved":return after=="CompletionReported"||after=="Claiming"||after=="Cancelling"||after=="Resolved";
                case "CompletionReported":return after=="Claiming"||after=="Cancelling"||after=="Resolved";
                case "Claiming":return after=="Resolved";
                case "Cancelling":return after=="Claiming"||after=="Resolved";
                default:return false;
            }
        }
        static void ValidateSuccessor(AdIntent85 before,AdIntent85 after){
            if(before==null){Require(after.state=="Reserving"&&after.opportunityId==""&&!after.CompletionReported,"AdJournalInitialStateInvalid");return;}
            Require(before.origin==after.origin&&before.playerId==after.playerId,"AdJournalOwnerMismatch");
            Require(before.reserveCommandId==after.reserveCommandId&&before.reportCommandId==after.reportCommandId&&before.claimCommandId==after.claimCommandId&&before.cancelCommandId==after.cancelCommandId,"AdJournalOutstandingIntent");
            Require(before.opportunityId==""||before.opportunityId==after.opportunityId,"AdJournalOpportunityChanged");
            Require(!before.CompletionReported||after.CompletionReported,"AdJournalCompletionErased");
            Require(Transition(before.state,after.state),"AdJournalStateRegression");
        }
        FileStream Lock()=>new FileStream(path+".lock",FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None);
#if UNITY_EDITOR_WIN || UNITY_STANDALONE_WIN
        [System.Runtime.InteropServices.DllImport("kernel32.dll",EntryPoint="MoveFileExW",CharSet=System.Runtime.InteropServices.CharSet.Unicode,SetLastError=true)]
        [return:System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.Bool)]
        static extern bool MoveFileEx126(string existing,string destination,uint flags);
#endif
        void Commit(string temporary){
            if(!File.Exists(path)){File.Move(temporary,path);return;}
#if UNITY_EDITOR_WIN || UNITY_STANDALONE_WIN
            // A single same-directory Windows rename avoids Mono's repeatedly
            // failing ReplaceFile path (1175). Never enable cross-volume copy,
            // delete the destination first, or replay an unconfirmed mutation.
            // The temporary file already inherited this directory's ACL and was
            // flushed; this journal contains public correlation, not credentials.
            if(!MoveFileEx126(temporary,path,0x1u|0x8u)){
                int error=System.Runtime.InteropServices.Marshal.GetLastWin32Error();
                throw new IOException("AdJournalAtomicRenameUnavailable",unchecked((int)(0x80070000u|(uint)error)));
            }
#else
            File.Replace(temporary,path,null);
#endif
        }
        AdIntent85 ReadCore(){
            FileStream file;try{file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read);}catch(FileNotFoundException){return null;}
            using(file){
                Require(file.Length>=2&&file.Length<=Limit,"AdJournalSizeInvalid");var bytes=new byte[(int)file.Length];int offset=0;
                while(offset<bytes.Length){int read=file.Read(bytes,offset,bytes.Length-offset);Require(read>0,"AdJournalReadIncomplete");offset+=read;}
                string json=Utf8.GetString(bytes);var envelope=JsonUtility.FromJson<Envelope>(json);
                Require(envelope!=null&&envelope.version==1&&Hex(envelope.sha256,64)&&envelope.payload!=null&&Hash(envelope.payload)==envelope.sha256&&JsonUtility.ToJson(envelope)==json,"AdJournalCorrupt");
                var value=JsonUtility.FromJson<AdIntent85>(envelope.payload);Validate(value);Require(JsonUtility.ToJson(value)==envelope.payload,"AdJournalCorrupt");return value;
            }
        }
        public bool TryLoad(string origin,string playerId,out AdIntent85 intent,out string error){
            intent=null;error=null;
            try{ValidateOwner(origin,playerId);using(Lock()){
                var value=ReadCore();if(value==null)return false;Require(value.origin==origin&&value.playerId==playerId,"AdJournalOwnerMismatch");intent=Copy(value);return true;
            }}catch(JournalFault fault){error=fault.Code;return false;}catch(Exception){error="AdJournalUnavailable";return false;}
        }
        public void Save(AdIntent85 value){
            string temporary=null;
            try{Validate(value);var next=Copy(value);Validate(next);using(Lock()){
                ValidateSuccessor(ReadCore(),next);string payload=JsonUtility.ToJson(next);var bytes=Utf8.GetBytes(JsonUtility.ToJson(new Envelope{payload=payload,sha256=Hash(payload)}));Require(bytes.Length<=Limit,"AdJournalSizeInvalid");
                // Short random sibling names avoid the Windows long-path bug
                // from repeating an already account-bound journal filename.
                temporary=Path.Combine(Path.GetDirectoryName(path),"ad-"+Guid.NewGuid().ToString("N")+".tmp");
                using(var file=new FileStream(temporary,FileMode.CreateNew,FileAccess.Write,FileShare.None)){file.Write(bytes,0,bytes.Length);file.Flush(true);}
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                VerificationCheckpoint?.Invoke("BeforeCommit");
#endif
                Commit(temporary);temporary=null;
                Require(JsonUtility.ToJson(ReadCore())==payload,"AdJournalCommitUnconfirmed");
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                VerificationCheckpoint?.Invoke("AfterCommit");
#endif
            }}catch(JournalFault fault){throw new InvalidOperationException(fault.Code);}
#if UNITY_EDITOR
            catch(Exception error){VerificationException116?.Invoke(error.GetType().FullName,error.HResult);throw new InvalidOperationException("AdJournalSaveUnavailable");}
#else
            catch(Exception){throw new InvalidOperationException("AdJournalSaveUnavailable");}
#endif
            finally{if(temporary!=null)try{File.Delete(temporary);}catch(Exception){}}
        }
        public void Clear(string expectedOrigin,string expectedPlayer){
            try{ValidateOwner(expectedOrigin,expectedPlayer);using(Lock()){
                var value=ReadCore();if(value==null)return;Require(value.origin==expectedOrigin&&value.playerId==expectedPlayer,"AdJournalOwnerMismatch");Require(value.state=="Resolved","AdJournalNotResolved");
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                VerificationCheckpoint?.Invoke("BeforeClear");
#endif
                File.Delete(path);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                VerificationCheckpoint?.Invoke("AfterClear");
#endif
            }}catch(JournalFault fault){throw new InvalidOperationException(fault.Code);}catch(Exception){throw new InvalidOperationException("AdJournalClearUnavailable");}
        }
    }
}

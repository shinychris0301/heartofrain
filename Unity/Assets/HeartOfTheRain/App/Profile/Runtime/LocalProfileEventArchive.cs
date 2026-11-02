#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text;
using UnityEngine;
namespace HeartOfTheRain.App.Profile {
    // Explicit local diagnostic delivery only. It is never a production sender.
    // Source receipts remain the outbox; stable IDs allow replay after any crash.
    public sealed class LocalProfileEventArchive {
        [Serializable] sealed class Envelope {public int format=1;public string payload,sha256;}
        public sealed class Result {public int written,existing,remaining;}
        readonly string root;public Action<string> Checkpoint;
        public LocalProfileEventArchive(string root){this.root=Path.GetFullPath(root);}
        static string Encode(ProfileAuditEvent e){e.Validate();string payload=JsonUtility.ToJson(e);return JsonUtility.ToJson(new Envelope{payload=payload,sha256=ProfileJson.Hash(payload)});}
        static void Verify(string path,string expected){
            if(new FileInfo(path).Length>16384)throw new InvalidDataException("Audit record too large");
            string text=File.ReadAllText(path,Encoding.UTF8);var envelope=JsonUtility.FromJson<Envelope>(text);
            if(envelope==null||envelope.format!=1||string.IsNullOrEmpty(envelope.payload)||ProfileJson.Hash(envelope.payload)!=envelope.sha256||text!=expected)throw new InvalidDataException("Audit identity has conflicting contents");
        }
        public Result Flush(ProfileEventFeed feed,int maximum=100){
            if(feed==null)throw new ArgumentNullException(nameof(feed));if(maximum<1||maximum>1000)throw new ArgumentOutOfRangeException(nameof(maximum));
            var snapshot=feed.Capture();string directory=Path.Combine(root,snapshot.stream);Directory.CreateDirectory(directory);var result=new Result();
            using(new FileStream(Path.Combine(directory,"archive.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)){
                var known=new HashSet<string>(snapshot.events.Select(e=>e.id));
                foreach(string saved in Directory.GetFiles(directory,"*.json"))if(!known.Contains(Path.GetFileNameWithoutExtension(saved)))throw new InvalidDataException("Audit archive diverges from current profile history");
                foreach(var e in snapshot.events){string path=Path.Combine(directory,e.id+".json"),encoded=Encode(e);
                    if(File.Exists(path)){Verify(path,encoded);result.existing++;continue;}
                    if(result.written>=maximum){result.remaining++;continue;}
                    string temp=Path.Combine(directory,Guid.NewGuid().ToString("N")+".tmp");
                    try{byte[] bytes=Encoding.UTF8.GetBytes(encoded);using(var file=new FileStream(temp,FileMode.CreateNew,FileAccess.Write,FileShare.None)){file.Write(bytes,0,bytes.Length);file.Flush(true);}Checkpoint?.Invoke("EventFlushed");File.Move(temp,path);Checkpoint?.Invoke("EventCommitted");result.written++;}
                    finally{if(File.Exists(temp))File.Delete(temp);}
                }
            }
            return result;
        }
    }
}
#endif

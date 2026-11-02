using System;
using System.IO;
using System.Text;
using System.Security.Cryptography;
using UnityEngine;
namespace HeartOfTheRain.App.Profile {
    public static class ProfileJson {
        public static PlayerProfile Copy(PlayerProfile p)=>JsonUtility.FromJson<PlayerProfile>(JsonUtility.ToJson(p));
        public static string Hash(string s){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(s))).Replace("-","").ToLowerInvariant();}
    }
    public sealed class MemoryProfileRepository:IProfileRepository {
        PlayerProfile current;readonly object gate=new object();
        public MemoryProfileRepository(PlayerProfile initial){initial.Validate();current=ProfileJson.Copy(initial);}
        public PlayerProfile Read(){lock(gate)return ProfileJson.Copy(current);}
        public PlayerProfile Commit(long expectedRevision,PlayerProfile next){lock(gate){if(expectedRevision!=current.revision)throw new ProfileConflictException();if(next.playerId!=current.playerId)throw new InvalidOperationException("Profile identity changed");var copy=ProfileJson.Copy(next);copy.revision=checked(expectedRevision+1);copy.Validate();current=copy;return ProfileJson.Copy(copy);}}
    }
    // No delete-and-rename fallback: unsupported atomic replacement fails closed.
    // A checksum detects accidental corruption; it is not an anti-cheat signature.
    public sealed class FileProfileRepository:IProfileRepository {
        [Serializable] sealed class Envelope {public int format=1;public string payload,sha256;}
        readonly string directory,current,backup,lockPath;readonly Func<PlayerProfile> create;
        public Action<string> Checkpoint;public bool RecoveredBackup {get;private set;}
        public FileProfileRepository(string directory,Func<PlayerProfile> create){this.directory=Path.GetFullPath(directory);current=Path.Combine(this.directory,"profile.json");backup=Path.Combine(this.directory,"profile.backup.json");lockPath=Path.Combine(this.directory,"profile.lock");this.create=create??throw new ArgumentNullException(nameof(create));}
        FileStream Lock(){Directory.CreateDirectory(directory);return new FileStream(lockPath,FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None);}
        static string Encode(PlayerProfile p){p.Validate();string payload=JsonUtility.ToJson(p);return JsonUtility.ToJson(new Envelope{payload=payload,sha256=ProfileJson.Hash(payload)});}
        static PlayerProfile Decode(string text){
            var e=JsonUtility.FromJson<Envelope>(text);if(e==null||e.format!=1)throw new NotSupportedException("Unsupported profile envelope");
            if(string.IsNullOrEmpty(e.payload)||e.sha256!=ProfileJson.Hash(e.payload))throw new InvalidDataException("Profile checksum mismatch");
            var p=JsonUtility.FromJson<PlayerProfile>(e.payload);if(p==null)throw new InvalidDataException("Profile is missing");if(p.schemaVersion!=1)throw new NotSupportedException("Unsupported profile version");p.Validate();return p;
        }
        string ReadText(string path){var f=new FileInfo(path);if(f.Length>16*1024*1024)throw new InvalidDataException("Profile exceeds supported size");return File.ReadAllText(path,Encoding.UTF8);}
        string WriteTemp(string contents){byte[] data=Encoding.UTF8.GetBytes(contents);if(data.Length>16*1024*1024)throw new InvalidDataException("Profile exceeds supported size");string temp=Path.Combine(directory,"profile."+Guid.NewGuid().ToString("N")+".tmp");using(var stream=new FileStream(temp,FileMode.CreateNew,FileAccess.Write,FileShare.None)){stream.Write(data,0,data.Length);stream.Flush(true);}return temp;}
        PlayerProfile Load(){
            if(!File.Exists(current)){
                if(File.Exists(backup)){string text=ReadText(backup);var saved=Decode(text);File.Move(WriteTemp(text),current);RecoveredBackup=true;return saved;}
                var initial=create();File.Move(WriteTemp(Encode(initial)),current);return ProfileJson.Copy(initial);
            }
            try{return Decode(ReadText(current));}
            catch(NotSupportedException){throw;} // Never downgrade a future save.
            catch(Exception error) when(error is InvalidDataException||error is ArgumentException||error is InvalidOperationException){
                if(!File.Exists(backup))throw new InvalidDataException("Saved profile cannot be recovered",error);
                string text=ReadText(backup);var saved=Decode(text);
                // Preserve both the good backup and the corrupt primary.
                File.Replace(WriteTemp(text),current,Path.Combine(directory,"profile.corrupt."+Guid.NewGuid().ToString("N")+".json"));RecoveredBackup=true;return saved;
            }
        }
        public PlayerProfile Read(){using(Lock())return Load();}
        public PlayerProfile Commit(long expectedRevision,PlayerProfile next){using(Lock()){
            var previous=Load();if(previous.revision!=expectedRevision)throw new ProfileConflictException();if(next.playerId!=previous.playerId)throw new InvalidOperationException("Profile identity changed");
            var saved=ProfileJson.Copy(next);saved.revision=checked(expectedRevision+1);saved.Validate();string temp=WriteTemp(Encode(saved));Checkpoint?.Invoke("TempFlushed");
            File.Replace(temp,current,backup);Checkpoint?.Invoke("Committed");return ProfileJson.Copy(saved);
        }}
    }
}

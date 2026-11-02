// The ordinary game has no replay-worker bootstrap, HTTP route or credentials.
#if HOTR_SERVER_REPLAY_WORKER && UNITY_STANDALONE_WIN && !UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;

namespace HeartOfTheRain.App.ServerVerification {
    public static class PinnedReplayWorker {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Main(){
            string output=null;var result=new ReplayOutput{unity=Application.unityVersion};int exit=1;
            try{
                var args=Environment.GetCommandLineArgs();Require(args.Contains("-batchmode")&&args.Contains("-nographics"));
                string input=Argument(args,"--job");output=Argument(args,"--out");Require(Path.IsPathRooted(input)&&Path.IsPathRooted(output)&&!File.Exists(output)&&Directory.Exists(Path.GetDirectoryName(output)));
                string directory=Path.GetFullPath(Path.Combine(Application.dataPath,"../ReplayPins"));string pinsHash;var pins=PinnedReplayEngine.ReadPins(directory,out pinsHash);string json=PinnedReplayEngine.ReadBounded(input,PinnedReplayEngine.MaximumJobBytes);result.jobSHA256=PinnedReplayEngine.SHA(json);var job=PinnedReplayEngine.ParseJob(json);Require(job.level>=1&&job.level<=50);var pin=pins.levels[job.level-1];var level=PinnedReplayEngine.Level(directory,pin);result=PinnedReplayEngine.Execute(job,level,pin,pinsHash,result.jobSHA256).output;exit=0;
            }catch(ReplayRejected error){result.code=error.Code;}catch(Exception){result.code="worker_unavailable";}
            try{if(output!=null){byte[] bytes=new UTF8Encoding(false,true).GetBytes(JsonUtility.ToJson(result));if(bytes.Length>PinnedReplayEngine.MaximumJobBytes)throw new InvalidOperationException();using(var file=new FileStream(output,FileMode.CreateNew,FileAccess.Write,FileShare.None)){file.Write(bytes,0,bytes.Length);file.Flush(true);}}else exit=2;}catch(Exception){exit=2;}
            // Never log job content, tokens, model internals or raw exceptions.
            Application.Quit(exit);
        }
        static string Argument(string[] args,string flag){Require(args.Count(a=>a==flag)==1);int at=Array.IndexOf(args,flag);Require(at+1<args.Length&&!string.IsNullOrWhiteSpace(args[at+1])&&Path.IsPathRooted(args[at+1]));return Path.GetFullPath(args[at+1]);}
        static void Require(bool valid){if(!valid)throw new ReplayRejected("invalid_worker_arguments");}
    }
}
#endif

using System;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M47;

namespace HeartOfTheRain.M48 {
    [InitializeOnLoad]
    public static class M52ReviewSession {
        static ReviewSessionLedger ledger;static GameplayReviewTools tools;static GameplayScreen screen;
        static double readyAt,completedAt=-1;static bool priorBlock,priorRunInBackground;
        public static bool Active=>ledger!=null&&ledger.Active;
        public static ReviewSessionReport Report=>ledger==null?null:ledger.Report;
        public static string Folder {get;private set;}="";
        static M52ReviewSession(){
            EditorApplication.update+=Tick;
            EditorApplication.playModeStateChanged+=state=>{if(state==PlayModeStateChange.ExitingPlayMode)Cancel("Play Mode ended.");};
            AssemblyReloadEvents.beforeAssemblyReload+=()=>Cancel("Scripts reloaded.");
            EditorApplication.quitting+=()=>Cancel("Editor closed.");
            Application.logMessageReceived+=OnLog;
        }
        public static void Begin(bool capture){
            if(Active)throw new InvalidOperationException("A review session is already running.");
            if(!EditorApplication.isPlaying||EditorApplication.isPaused)throw new InvalidOperationException("Enter Play Mode and resume the Editor first.");
            tools=UnityEngine.Object.FindObjectOfType<GameplayReviewTools>();screen=UnityEngine.Object.FindObjectOfType<GameplayScreen>();
            if(tools==null||screen==null||!screen.Ready||screen.gameObject.scene.path!=M48ReviewMenu.Scene||screen.Busy||tools.ManualPlaytestRunning||tools.Replaying||tools.Showcasing||tools.IsMeasuring||M48Recording.IsRecording)
                throw new InvalidOperationException("Open the review scene, wait for the current action and end manual logging and stop performance measurement/recording.");
            if(capture&&Application.platform==RuntimePlatform.LinuxEditor)throw new NotSupportedException("Use playback-only on Linux. This MP4 configuration requires Windows/macOS.");
            M48ReviewMenu.Validate();
            var fixture=Resources.Load<TextAsset>("HOTR_Playtests/Campaign_Replays");
            var next=new ReviewSessionLedger(JsonUtility.FromJson<CampaignReplaySet>(fixture.text),capture);
            var folder=Path.GetFullPath("ReviewSessions/M52_"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss")+"_"+next.Report.sessionId.Substring(0,8));
            Directory.CreateDirectory(folder);File.Copy("Builds/Validation/Unity_Import_Report.json",Path.Combine(folder,"Unity_Import_Report.json"));
            next.Report.unity=Application.unityVersion;next.Report.platform=Application.platform.ToString();
            using(var hash=SHA256.Create())next.Report.fixtureSha256=BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(fixture.text))).Replace("-","").ToLowerInvariant();
            tools.SetDrawer(false);priorBlock=screen.ReviewInputBlocked;priorRunInBackground=Application.runInBackground;
            Application.runInBackground=true;tools.SessionRunning=true;screen.ReviewInputBlocked=true;
            ledger=next;Folder=folder;readyAt=EditorApplication.timeSinceStartup+.2;completedAt=-1;
            try {Save();}catch {ledger.Cancel("Could not save the new session.");Release();throw;}
        }
        static void Tick(){
            if(!Active)return;
            try {
                if(!EditorApplication.isPlaying||tools==null||screen==null){Cancel("Review scene or player became unavailable.");return;}
                if(EditorApplication.isPaused)return;
                if(Report.consoleErrors.Count>0)throw new InvalidOperationException("Unity logged an error during this session. See consoleErrors in session.json.");
                if(ledger.Current==null){
                    if(EditorApplication.timeSinceStartup<readyAt)return;
                    if(screen.Busy)throw new InvalidOperationException("The board is unexpectedly busy between session replays.");
                    var row=ledger.BeginNext();Save();
                    if(Report.captureRequested)M48Recording.CaptureReplay(row.level,true,Path.Combine(Folder,"L"+row.level.ToString("000")+"_capture"));
                    else if(!tools.StartReplay(row.level))throw new InvalidOperationException(tools.ReplayStatus);
                    ledger.BindRun(tools.ActiveReplayId);completedAt=-1;Save();return;
                }
                if(tools.Replaying){
                    if(Report.captureRequested&&!M48Recording.IsRecording)throw new InvalidOperationException("Recording stopped before the replay ended.");
                    ledger.Current.settledActions=tools.ReplaySettledActions;return;
                }
                if(completedAt<0)completedAt=EditorApplication.timeSinceStartup;
                var current=ledger.Current;
                bool captureReady=!Report.captureRequested;
                if(Report.captureRequested){
                    if(M48Recording.IsRecording){if(EditorApplication.timeSinceStartup-completedAt>30)throw new TimeoutException("Recorder did not stop after the replay.");return;}
                    if(M48Recording.LastCaptureStatus!="COMPLETED")throw new InvalidOperationException("Recording ended early or failed: "+M48Recording.LastCaptureStatus+" "+M48Recording.LastCaptureError);
                    var expected=Path.Combine(Folder,"L"+current.level.ToString("000")+"_capture.mp4");
                    if(M48Recording.LastRecordingPath!=expected)throw new InvalidOperationException("Recording path changed during the session.");
                    captureReady=File.Exists(expected)&&new FileInfo(expected).Length>0;
                    if(!captureReady){if(EditorApplication.timeSinceStartup-completedAt>30)throw new IOException("Recorder produced no nonempty MP4 file.");return;}
                }
                var replayFile=CopyReplay(current.level);
                var replay=JsonUtility.FromJson<ReplayPlaybackReport>(File.ReadAllText(Path.Combine(Folder,replayFile)));
                ledger.Complete(replay,replayFile,Report.captureRequested?"L"+current.level.ToString("000")+"_capture.mp4":"",captureReady,M48Recording.LastCaptureStatus);
                Save();readyAt=EditorApplication.timeSinceStartup+1;completedAt=-1;
                if(!Active)Release();
            }catch(Exception ex){Fail(ex.Message);}
        }
        static string CopyReplay(int level){
            if(tools==null||string.IsNullOrEmpty(tools.LastReplayOutput)||!File.Exists(tools.LastReplayOutput))throw new IOException("No fresh replay JSON was saved.");
            var current=ledger.Current;
            var result=JsonUtility.FromJson<ReplayPlaybackReport>(File.ReadAllText(tools.LastReplayOutput));
            if(current==null||string.IsNullOrEmpty(current.runId)||result==null||result.runId!=current.runId||result.level!=level||result.seed!=current.seed)throw new IOException("Replay result identity does not match this session run.");
            var name="L"+level.ToString("000")+"_replay.json";File.Copy(tools.LastReplayOutput,Path.Combine(Folder,name),true);return name;
        }
        static void PreservePartial(){
            if(ledger.Current==null||tools==null)return;
            try {if(tools.Replaying)tools.StopReplay();ledger.Current.replayFile=CopyReplay(ledger.Current.level);}catch(Exception ex){Report.consoleErrors.Add("Partial replay report: "+ex.Message);}
            if(Report.captureRequested){
                M48Recording.Stop();var name="L"+ledger.Current.level.ToString("000")+"_capture.mp4";
                if(File.Exists(Path.Combine(Folder,name)))ledger.Current.captureFile=name;
                ledger.Current.captureStatus=M48Recording.LastCaptureStatus;
            }
        }
        public static void Cancel(string reason){if(!Active)return;PreservePartial();ledger.Cancel(reason);FinishSave();}
        static void Fail(string reason){if(!Active)return;PreservePartial();ledger.Fail(reason);FinishSave();Debug.LogError("M52 session stopped: "+reason);}
        static void FinishSave(){try{Save();}catch(Exception ex){Debug.LogError("Session report could not be saved: "+ex.Message);}finally{Release();}}
        static void Release(){if(tools!=null)tools.SessionRunning=false;if(screen!=null)screen.ReviewInputBlocked=priorBlock;Application.runInBackground=priorRunInBackground;}
        static void OnLog(string message,string stack,LogType kind){
            if(!Active||(kind!=LogType.Error&&kind!=LogType.Exception&&kind!=LogType.Assert)||Report.consoleErrors.Count>=40)return;
            string entry=kind+": "+message+"\n"+stack;Report.consoleErrors.Add(entry.Length>4096?entry.Substring(0,4096):entry);
        }
        public static void Save(){if(Report!=null)SaveReport(Report,Folder);}
        public static void SaveReport(ReviewSessionReport report,string folder){
            var output=Path.Combine(folder,"session.json");var temp=Path.Combine(folder,"session.pending.json");
            File.WriteAllText(temp,JsonUtility.ToJson(report,true));File.Copy(temp,output,true);File.Delete(temp);
        }
        public static string Export(ReviewSessionReport report,string folder){
            if(report==null||report.status=="RUNNING")throw new InvalidOperationException("Finish the session before export.");
            SaveReport(report,folder);
            var output=folder+"_review_"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff")+".zip";
            using(var stream=new FileStream(output,FileMode.CreateNew))using(var zip=new ZipArchive(stream,ZipArchiveMode.Create)){
                // Fixed filenames only: importing a session cannot make export read arbitrary paths.
                var names=new[]{"session.json","Unity_Import_Report.json"}.Concat(CampaignValidation.RequiredReplays.SelectMany(n=>new[]{"L"+n.ToString("000")+"_replay.json","L"+n.ToString("000")+"_capture.mp4"}));
                foreach(var name in names){var path=Path.Combine(folder,name);if(!File.Exists(path))continue;if((File.GetAttributes(path)&FileAttributes.ReparsePoint)!=0)throw new IOException("Refusing linked evidence file: "+name);var entry=zip.CreateEntry(name,name.EndsWith(".mp4")?CompressionLevel.NoCompression:CompressionLevel.Optimal);using(var source=File.OpenRead(path))using(var target=entry.Open())source.CopyTo(target);}
            }
            return output;
        }
    }

    public sealed class M52ReviewWindow:EditorWindow {
        bool capture=true,wasRunning;Vector2 scroll;string message="",loadedFolder="";ReviewSessionReport loaded;
        static readonly string[] Verdicts={"PENDING","ACCEPTED","NEEDS_CHANGES"};
        static readonly string[] VerdictLabels={"Not reviewed","Accepted","Needs changes"};
        [MenuItem("Heart of the Rain/M48/4 Guided Review Session")]
        public static void Open(){GetWindow<M52ReviewWindow>("Gameplay Review").minSize=new Vector2(470,480);}
        void OnEnable(){EditorApplication.update+=Refresh;}
        void OnDisable(){EditorApplication.update-=Refresh;}
        void Refresh(){if(M52ReviewSession.Active||wasRunning)Repaint();wasRunning=M52ReviewSession.Active;}
        void Action(Action work){try{work();message="";}catch(Exception ex){message=ex.Message;}}
        void OnGUI(){
            GUILayout.Label("Chapter 1 · guided gameplay review",EditorStyles.boldLabel);
            EditorGUILayout.HelpBox("Runs 21 → 28 → 36 → 49 → 50. Playback completion is separate from your visual judgment. Phone performance and human difficulty still need their own review.",MessageType.Info);
            using(new EditorGUI.DisabledScope(M52ReviewSession.Active)){
                GUILayout.BeginHorizontal();if(GUILayout.Button("Open review scene"))Action(M48ReviewMenu.Open);if(GUILayout.Button("Validate imported assets"))Action(M48ReviewMenu.Validate);GUILayout.EndHorizontal();
                capture=EditorGUILayout.Toggle("Record each replay with audio",capture);
                if(GUILayout.Button("Run five-level session"))Action(()=>{M52ReviewSession.Begin(capture);loaded=null;loadedFolder="";});
                if(GUILayout.Button("Open previous session.json…"))Action(()=>{var path=EditorUtility.OpenFilePanel("Open review session","ReviewSessions","json");if(string.IsNullOrEmpty(path))return;var report=JsonUtility.FromJson<ReviewSessionReport>(File.ReadAllText(path));if(report==null||report.milestone!="M52 R1"||report.runs==null||report.runs.Count!=5||report.runs.Any(r=>r==null)||!report.runs.Select(r=>r.level).OrderBy(n=>n).SequenceEqual(CampaignValidation.RequiredReplays))throw new InvalidOperationException("Not an M52 five-level session report.");loaded=report;loadedFolder=Path.GetDirectoryName(path);if(loaded.status=="RUNNING"){ReviewSessionLedger.MarkInterrupted(loaded);M52ReviewSession.SaveReport(loaded,loadedFolder);}});
            }
            if(!EditorApplication.isPlaying)EditorGUILayout.HelpBox("Enter Play Mode in the review scene before running the session.",MessageType.None);
            if(M52ReviewSession.Active&&GUILayout.Button("Stop session and recording"))M52ReviewSession.Cancel("Stopped from the review window.");
            if(!string.IsNullOrEmpty(message))EditorGUILayout.HelpBox(message,MessageType.Error);
            var reportView=loaded??M52ReviewSession.Report;var folder=loaded!=null?loadedFolder:M52ReviewSession.Folder;
            if(reportView==null)return;
            GUILayout.Label("Playback: "+reportView.status,EditorStyles.boldLabel);GUILayout.Label("Visual review: "+reportView.visualStatus);
            if(!string.IsNullOrEmpty(reportView.message))EditorGUILayout.HelpBox(reportView.message,MessageType.Warning);
            if(reportView.consoleErrors.Count>0)EditorGUILayout.HelpBox(reportView.consoleErrors.Count+" error(s) recorded in session.json.",MessageType.Error);
            scroll=EditorGUILayout.BeginScrollView(scroll);
            foreach(var row in reportView.runs){
                GUILayout.BeginVertical(EditorStyles.helpBox);GUILayout.Label("Level "+row.level+"  ·  "+row.status,EditorStyles.boldLabel);
                GUILayout.Label(row.settledActions+" / "+row.expectedActions+" settled actions  ·  Capture: "+row.captureStatus);
                if(!string.IsNullOrEmpty(row.message))GUILayout.Label(row.message,EditorStyles.wordWrappedLabel);
                using(new EditorGUI.DisabledScope(reportView.status=="RUNNING")){
                    EditorGUI.BeginChangeCheck();int selected=Array.IndexOf(Verdicts,row.visualReview);selected=EditorGUILayout.Popup("Visual result",Math.Max(0,selected),VerdictLabels);
                    GUILayout.Label("Notes (effect, move number, video time)");string notes=EditorGUILayout.TextArea(row.notes??"",GUILayout.MinHeight(42));
                    if(EditorGUI.EndChangeCheck())Action(()=>{ReviewSessionLedger.SetVisualReview(reportView,row.level,Verdicts[selected],notes);M52ReviewSession.SaveReport(reportView,folder);});
                }
                GUILayout.EndVertical();
            }
            EditorGUILayout.EndScrollView();
            GUILayout.BeginHorizontal();if(GUILayout.Button("Open results folder"))EditorUtility.RevealInFinder(folder);
            using(new EditorGUI.DisabledScope(reportView.status=="RUNNING")){if(GUILayout.Button("Export review ZIP"))Action(()=>EditorUtility.RevealInFinder(M52ReviewSession.Export(reportView,folder)));}
            GUILayout.EndHorizontal();
        }
    }
}

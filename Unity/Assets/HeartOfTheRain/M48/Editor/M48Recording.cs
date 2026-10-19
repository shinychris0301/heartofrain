using System;
using System.Collections;
using System.IO;
using UnityEditor;
using UnityEditor.Recorder;
using UnityEditor.Recorder.Encoder;
using UnityEditor.Recorder.Input;
using UnityEngine;
namespace HeartOfTheRain.M48 {
    [InitializeOnLoad]
    public static class M48Recording {
        static RecorderController recorder;static GameplayReviewTools review;static RecorderControllerSettings settings;static MovieRecorderSettings movie;
        static bool stopAfterReplay;static double finishAt=-1;
        public static bool IsRecording=>recorder!=null&&recorder.IsRecording();
        public static string LastRecordingPath {get;private set;}="";
        public static string LastCaptureStatus {get;private set;}="NOT_STARTED";
        public static string LastCaptureError {get;private set;}="";
        static M48Recording(){EditorApplication.playModeStateChanged+=s=>{if(s==PlayModeStateChange.ExitingPlayMode)Stop();};AssemblyReloadEvents.beforeAssemblyReload+=Stop;EditorApplication.update+=WatchReplay;}
        static void WatchReplay(){
            if(!stopAfterReplay||recorder==null)return;
            if(review==null){Stop();return;}
            if(!recorder.IsRecording()){StopCore(false);LastCaptureError="Recorder became inactive before the requested stop.";return;}
            if(review.Replaying){finishAt=-1;return;}
            if(finishAt<0)finishAt=EditorApplication.timeSinceStartup+1;
            if(EditorApplication.timeSinceStartup>=finishAt)StopCore(true);
        }
        [MenuItem("Heart of the Rain/M48/Recording/Record Replay/Level 21 - Storm Crystal")]
        public static void Replay21(){CaptureReplay(21);}
        [MenuItem("Heart of the Rain/M48/Recording/Record Replay/Level 28 - Water Spirit Pod")]
        public static void Replay28(){CaptureReplay(28);}
        [MenuItem("Heart of the Rain/M48/Recording/Record Replay/Level 36 - Rainlight Cabinet")]
        public static void Replay36(){CaptureReplay(36);}
        [MenuItem("Heart of the Rain/M48/Recording/Record Replay/Level 49 - Late Challenge")]
        public static void Replay49(){CaptureReplay(49);}
        [MenuItem("Heart of the Rain/M48/Recording/Record Replay/Level 50 - Chapter Finale")]
        public static void Replay50(){CaptureReplay(50);}
        public static void CaptureReplay(int level,bool sessionOwned=false,string outputBase=null){
            if(recorder!=null)throw new InvalidOperationException("Stop the current recording first.");
            if(Application.platform==RuntimePlatform.LinuxEditor)throw new NotSupportedException("MP4 capture is configured for Windows/macOS; use playback-only on Linux.");
            var tools=UnityEngine.Object.FindObjectOfType<GameplayReviewTools>();
            var screen=UnityEngine.Object.FindObjectOfType<HeartOfTheRain.M47.GameplayScreen>();
            if(!EditorApplication.isPlaying||tools==null||screen==null||!screen.Ready||screen.Busy||tools.ManualPlaytestRunning||tools.Replaying||tools.Showcasing||(tools.SessionRunning&&!sessionOwned))
                throw new InvalidOperationException("Enter Play Mode in the review scene and wait for the current action/review to finish.");
            // Load the recorded board before capture begins; avoid a frame of the previous level.
            if(!tools.StartReplay(level))throw new InvalidOperationException(tools.ReplayStatus);
            try {StartCore(sessionOwned,outputBase);stopAfterReplay=true;finishAt=-1;}
            catch {tools.StopReplay();throw;}
            Debug.Log("Recording replay "+level+". Capture stops one second after the replay ends. A replay JSON is saved separately.");
        }
        [MenuItem("Heart of the Rain/M48/Recording/Start MP4 with Audio")]
        public static void Start(){StartCore(false,null);}
        static void StartCore(bool sessionOwned,string outputBase){
            if(!EditorApplication.isPlaying)throw new InvalidOperationException("Enter Play Mode first");
            if(Application.platform==RuntimePlatform.LinuxEditor)throw new NotSupportedException("Use Unity Recorder on Windows or macOS for this MP4 capture configuration.");
            if(recorder!=null)return;review=UnityEngine.Object.FindObjectOfType<GameplayReviewTools>();
            if(review==null||(review.SessionRunning&&!sessionOwned))throw new InvalidOperationException("Open the review scene and finish the current guided session first.");
            LastRecordingPath="";LastCaptureError="";LastCaptureStatus="PREPARING";
            try {
                review.SetDrawer(false);settings=ScriptableObject.CreateInstance<RecorderControllerSettings>();
                movie=ScriptableObject.CreateInstance<MovieRecorderSettings>();movie.name="M52 Gameplay";movie.Enabled=true;movie.CaptureAudio=true;
                movie.EncoderSettings=new CoreEncoderSettings{EncodingQuality=CoreEncoderSettings.VideoEncodingQuality.High,Codec=CoreEncoderSettings.OutputCodec.MP4};
                movie.ImageInputSettings=new GameViewInputSettings{OutputWidth=720,OutputHeight=1280};
                var output=Path.GetFullPath(outputBase??("Recordings/M52_"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff")+"_"+Guid.NewGuid().ToString("N").Substring(0,8)));
                Directory.CreateDirectory(Path.GetDirectoryName(output));movie.OutputFile=output;LastRecordingPath=output+".mp4";
                settings.AddRecorderSettings(movie);settings.SetRecordModeToManual();settings.FrameRate=30;
                recorder=new RecorderController(settings);review.Capturing=true;
                recorder.PrepareRecording();if(!recorder.StartRecording())throw new Exception("Recorder could not start");
                LastCaptureStatus="RECORDING";
            }catch(Exception ex){StopCore(false);LastCaptureStatus="FAILED";LastCaptureError=ex.Message;throw;}
        }
        [MenuItem("Heart of the Rain/M48/Recording/Start MP4 and Staged Showcase")]
        public static void Showcase(){var tools=UnityEngine.Object.FindObjectOfType<GameplayReviewTools>();if(tools==null||tools.SessionRunning||tools.ManualPlaytestRunning||tools.Replaying||tools.Showcasing)throw new InvalidOperationException("Finish the current review first.");Start();review.StartCoroutine(CaptureShowcase());}
        static IEnumerator CaptureShowcase(){try{yield return review.RunShowcase();}finally{Stop();}}
        [MenuItem("Heart of the Rain/M48/Recording/Stop MP4")]
        public static void Stop(){StopCore(false);}
        static void StopCore(bool completed){
            stopAfterReplay=false;finishAt=-1;bool hadRecorder=recorder!=null;
            try {if(hadRecorder){recorder.StopRecording();LastCaptureStatus=completed?"COMPLETED":"STOPPED_EARLY";}}
            catch(Exception ex){LastCaptureStatus="FAILED";LastCaptureError=ex.Message;Debug.LogError("Recorder stop failed: "+ex.Message);}
            finally {recorder=null;if(review!=null)review.Capturing=false;if(movie!=null)UnityEngine.Object.DestroyImmediate(movie);if(settings!=null)UnityEngine.Object.DestroyImmediate(settings);movie=null;settings=null;}
        }
        [MenuItem("Heart of the Rain/M48/Recording/Stop Replay and MP4")]
        public static void StopReplayAndRecording(){try{if(review!=null)review.StopReplay();}finally{Stop();}}
    }
}

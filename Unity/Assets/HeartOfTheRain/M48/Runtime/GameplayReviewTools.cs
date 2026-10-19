using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.Profiling;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.M48 {
    [Serializable] public class ReviewSample {
        public float milliseconds; public int level,sprites,cachedSprites,textures,history;
        public long textureBytes,allocatedBytes; public int gen0Collections;
    }
    [Serializable] public class DeviceReviewReport {
        public string milestone="M54 R1",unity,platform,device,gpu,startedUTC,finishedUTC,status,endReason;
        public double activeSeconds,requestedSeconds;public int excludedIntervals;
        public int width,height,frames; public bool recordingWasActive,manualLoggingWasActive;public string manualSessionId;
        public float p50Milliseconds,p95Milliseconds,maxMilliseconds;
        public long peakTextureBytes,peakAllocatedBytes;
        public List<ReviewSample> samples;
        public string limitation="Frame intervals include CPU, GPU waits and scheduling; not a GPU timing measurement. Recording/logging runs include instrumentation overhead and are excluded from performance approval. Editor measurements are not phone results.";
    }
    [DisallowMultipleComponent]
    public sealed partial class GameplayReviewTools:MonoBehaviour {
        public bool showReviewButton=true;
        public bool Capturing {get;set;}
        public bool SessionRunning {get;set;}
        public bool IsMeasuring {get;private set;}
        public string LastOutput {get;private set;}="";
        readonly ReviewMeasurementClock measurementClock=new ReviewMeasurementClock();
        public string MeasurementStatus {get;private set;}="";
        GameplayScreen screen; bool open,wasPaused,captureDuringMeasure,manualDuringMeasure;string measureSessionId="",levelText="21",startedUTC;
        readonly List<ReviewSample> samples=new List<ReviewSample>();
        Vector2 scroll;
        public static readonly string[] PresetNames={"Bomb","Rocket","Rainbow Orb","Rain Seeker","Golden Seeker","Rocket + Bomb","Double Bomb","Double Rocket","Double Orb","Rain + Rocket","Rain + Bomb","Rain + Rain","Orb + Rocket","Orb + Bomb","Orb + Rain","Golden + Rocket","Golden + Bomb","Golden + Rain","Golden + Orb"};
        public static readonly int[,] Presets={{21,-1},{4,-1},{7,-1},{11,-1},{16,-1},{4,21},{21,21},{4,5},{7,7},{11,4},{11,21},{11,11},{7,4},{7,21},{7,11},{16,4},{16,21},{16,11},{16,7}};
        void Start(){screen=GetComponent<GameplayScreen>();if(!Application.isEditor&&!Debug.isDebugBuild){showReviewButton=false;enabled=false;}}
        void Update(){TickManualPlaytest();if(!IsMeasuring)return;
            captureDuringMeasure|=Capturing;manualDuringMeasure|=ManualPlaytestRunning;
            if(measurementClock.Observe(Time.unscaledDeltaTime,screen!=null&&screen.Ready&&!screen.Paused&&!manualSuspended&&!manualUnfocused))samples.Add(new ReviewSample{milliseconds=Time.unscaledDeltaTime*1000,level=screen.CurrentLevel,sprites=screen.ActiveSpriteCount,cachedSprites=screen.CachedSpriteCount,textures=screen.CachedTextureCount,history=screen.HistoryCount,textureBytes=screen.CachedTextureBytes,allocatedBytes=Profiler.GetTotalAllocatedMemoryLong(),gen0Collections=GC.CollectionCount(0)});
            if(measurementClock.EndReason!="")StopMeasurement(measurementClock.EndReason);
        }
        public void BeginMeasurement(){
            if(!Application.isEditor&&!Debug.isDebugBuild||screen==null||!screen.Ready||SessionRunning||ManualPlaytestRunning||Capturing||IsMeasuring){MeasurementStatus="Finish logging, recording or the current measurement first.";return;}
            samples.Clear();measurementClock.Begin();LastOutput="";MeasurementStatus="Measuring 600 active seconds; pause/background time is excluded.";startedUTC=DateTime.UtcNow.ToString("o");captureDuringMeasure=Capturing;manualDuringMeasure=ManualPlaytestRunning;measureSessionId=ManualPlaytestRunning?manual.Report.sessionId:"";IsMeasuring=true;}
        public void StopMeasurement(string reason="STOPPED_BY_REVIEWER"){if(!IsMeasuring)return;IsMeasuring=false;
            var sorted=samples.Select(s=>s.milliseconds).OrderBy(v=>v).ToArray();
            var report=new DeviceReviewReport{finishedUTC=DateTime.UtcNow.ToString("o"),endReason=reason,activeSeconds=measurementClock.ActiveSeconds,requestedSeconds=measurementClock.RequestedSeconds,excludedIntervals=measurementClock.ExcludedIntervals,status=Application.isEditor?"RECORDED_IN_EDITOR":Application.isMobilePlatform?"RECORDED_ON_MOBILE":"RECORDED_ON_DESKTOP",manualLoggingWasActive=manualDuringMeasure,manualSessionId=measureSessionId,unity=Application.unityVersion,platform=Application.platform.ToString(),device=SystemInfo.deviceModel,gpu=SystemInfo.graphicsDeviceName,startedUTC=startedUTC,width=Screen.width,height=Screen.height,frames=samples.Count,recordingWasActive=captureDuringMeasure,samples=new List<ReviewSample>(samples)};
            if(sorted.Length>0){report.p50Milliseconds=sorted[(sorted.Length-1)/2];report.p95Milliseconds=sorted[(int)((sorted.Length-1)*.95)];report.maxMilliseconds=sorted[sorted.Length-1];report.peakTextureBytes=samples.Max(s=>s.textureBytes);report.peakAllocatedBytes=samples.Max(s=>s.allocatedBytes);}
            if(samples.Count==0)report.status="NO_VALID_SAMPLES";
            LastOutput="";
            try {
                var folder=Path.Combine(Application.persistentDataPath,"M48Review");Directory.CreateDirectory(folder);
                var path=Path.Combine(folder,"device_"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff")+"_"+Guid.NewGuid().ToString("N")+".json");
                File.WriteAllText(path+".tmp",JsonUtility.ToJson(report,true));File.Move(path+".tmp",path);LastOutput=path;
                MeasurementStatus="Saved "+report.activeSeconds.ToString("F1")+" active seconds: "+report.endReason;Debug.Log("M54 report: "+LastOutput);
            }catch(Exception ex){MeasurementStatus="Performance report could not be saved: "+ex.Message;Debug.LogError(MeasurementStatus);}
        }
        public void SetDrawer(bool value){if(screen==null)return;if(value&&!open){wasPaused=screen.Paused;screen.SetPause(true);}open=value;screen.ReviewInputBlocked=value||Replaying||SessionRunning;if(!value&&!wasPaused)screen.SetPause(false);}
        public void LoadReviewLevel(int level){if(ManualPlaytestRunning||SessionRunning||Replaying||Showcasing||screen==null||!screen.Ready)return;SetDrawer(false);screen.Load(Mathf.Clamp(level,1,50)-1);}
        public void RunPreset(int preset){if(ManualPlaytestRunning||SessionRunning||Replaying||Showcasing||screen==null||!screen.Ready||preset<0||preset>=PresetNames.Length)return;SetDrawer(false);screen.ResumeReview();screen.ReviewActivate(Presets[preset,0],Presets[preset,1]);}
        public bool Showcasing {get;private set;} bool showcaseIntro;
        public IEnumerator RunShowcase(){if(ManualPlaytestRunning||SessionRunning||Replaying||Showcasing||screen==null||!screen.Ready||screen.Busy)yield break;SetDrawer(false);screen.ResumeReview();Showcasing=true;showcaseIntro=screen.showLevelIntro;screen.showLevelIntro=false;
            try {foreach(int preset in new[]{0,1,5,6,8,4,15,16,17,18}){
                screen.Load(17);yield return null;yield return new WaitForSeconds(.7f);
                if(!screen.ReviewActivate(Presets[preset,0],Presets[preset,1]))throw new InvalidOperationException("Cannot stage "+PresetNames[preset]);
                float deadline=Time.realtimeSinceStartup+120;while(screen.Busy){if(Time.realtimeSinceStartup>deadline)throw new TimeoutException("Showcase stalled: "+PresetNames[preset]);yield return null;}yield return new WaitForSeconds(2.5f);
            }} finally {Showcasing=false;if(screen!=null)screen.showLevelIntro=showcaseIntro;}
        }
        void OnGUI(){if(!showReviewButton||screen==null||!screen.Ready||Capturing||Showcasing||SessionRunning)return;
            float scale=Mathf.Max(.5f,Screen.width/720f);var matrix=GUI.matrix;GUI.matrix=Matrix4x4.TRS(Vector3.zero,Quaternion.identity,new Vector3(scale,scale,1));
            if(Replaying){if(GUI.Button(new Rect(592,4,116,32),"Stop replay"))StopReplay();GUI.matrix=matrix;return;}
            if(GUI.Button(new Rect(592,4,116,32),open?"Close review":"Review"))SetDrawer(!open);
            if(open){GUILayout.BeginArea(new Rect(24,248,672,Mathf.Max(300,Screen.height/scale-440)),GUI.skin.box);scroll=GUILayout.BeginScrollView(scroll);
                GUILayout.Label("M54 gameplay review");
                GUILayout.Label("Manual playtest — normal play, retries and booster use");
                GUILayout.Label("Notes (experience / first exposure / feedback; no personal details)");
                ManualPlaytestNotes=GUILayout.TextArea(ManualPlaytestNotes??"",1024);
                if(ManualPlaytestRunning){
                    GUILayout.Label("Logging level "+screen.CurrentLevel+" · "+manual.Report.attempts.Count+" attempt(s)");
                    GUILayout.Label("Staged effects and replays are unavailable until you end this session.");
                    if(GUILayout.Button("End manual session and export JSON"))StopManualPlaytest();
                    if(GUILayout.Button("Resume normal play"))SetDrawer(false);
                    GUILayout.Label(ManualPlaytestStatus);GUILayout.Label(LastManualPlaytestOutput);
                    GUILayout.EndScrollView();GUILayout.EndArea();GUI.matrix=matrix;return;
                }
                GUILayout.BeginHorizontal();GUILayout.Label("Start at level",GUILayout.Width(100));levelText=GUILayout.TextField(levelText,GUILayout.Width(100));
                if(GUILayout.Button("Start fresh manual session")){int n;if(int.TryParse(levelText,out n))BeginManualPlaytest(n);}GUILayout.EndHorizontal();
                if(!string.IsNullOrEmpty(ManualPlaytestStatus))GUILayout.Label(ManualPlaytestStatus);
                if(!string.IsNullOrEmpty(LastManualPlaytestOutput))GUILayout.Label(LastManualPlaytestOutput);
                GUILayout.Label("Replay recorded play — no boosters or injected power-ups");
                GUILayout.BeginHorizontal();foreach(int n in new[]{21,28,36,49,50})if(GUILayout.Button("Replay "+n))StartReplay(n);GUILayout.EndHorizontal();
                if(!string.IsNullOrEmpty(ReplayStatus))GUILayout.Label(ReplayStatus);
                if(!string.IsNullOrEmpty(LastReplayOutput))GUILayout.Label(LastReplayOutput);
                GUILayout.BeginHorizontal();GUILayout.Label("Level 1–50",GUILayout.Width(100));levelText=GUILayout.TextField(levelText,GUILayout.Width(100));if(GUILayout.Button("Load")){int n;if(int.TryParse(levelText,out n))LoadReviewLevel(n);}GUILayout.EndHorizontal();
                GUILayout.Label("Board "+screen.Model.Level.columns+"×"+screen.Model.Level.rows+" | "+screen.ActiveSpriteCount+" sprites | "+(screen.CachedTextureBytes/1048576f).ToString("F1")+" MiB cached textures");
                GUI.enabled=!screen.Busy;
                for(int i=0;i<PresetNames.Length;i+=2){GUILayout.BeginHorizontal();if(GUILayout.Button(PresetNames[i]))RunPreset(i);if(i+1<PresetNames.Length&&GUILayout.Button(PresetNames[i+1]))RunPreset(i+1);GUILayout.EndHorizontal();}
                GUILayout.Label("Obstacle review — staged hits use no stock");
                GUILayout.BeginHorizontal();foreach(string family in new[]{"crystal","pod","cabinet"})if(GUILayout.Button("Hit "+family)){SetDrawer(false);screen.ResumeReview();screen.ReviewObstacleHit(family);}GUILayout.EndHorizontal();
                GUILayout.BeginHorizontal();foreach(int n in new[]{21,28,36,49,50})if(GUILayout.Button("Level "+n))LoadReviewLevel(n);GUILayout.EndHorizontal();
                if(GUILayout.Button("Play one legal move")){SetDrawer(false);screen.ResumeReview();screen.ReviewNaturalMove();}
                GUI.enabled=true;
                GUILayout.BeginHorizontal();if(GUILayout.Button("Tutorial")){SetDrawer(false);screen.ReviewTutorial();}if(GUILayout.Button("Success UI")){SetDrawer(false);screen.ReviewSuccess();}if(GUILayout.Button("Failure UI")){SetDrawer(false);screen.ReviewLoss();}GUILayout.EndHorizontal();
                if(GUILayout.Button(IsMeasuring?"Stop and export performance report":"Start performance measurement")){if(IsMeasuring)StopMeasurement();else BeginMeasurement();SetDrawer(false);}
                if(GUILayout.Button("Play staged showcase"))StartCoroutine(RunShowcase());
                if(!string.IsNullOrEmpty(MeasurementStatus))GUILayout.Label(MeasurementStatus);
                if(IsMeasuring)GUILayout.Label(measurementClock.ActiveSeconds.ToString("F1")+" / 600 active seconds");
                if(!string.IsNullOrEmpty(LastOutput))GUILayout.Label(LastOutput);
                GUILayout.EndScrollView();GUILayout.EndArea();
            }GUI.matrix=matrix;
        }
        void OnDisable(){if(ManualPlaytestRunning)StopManualPlaytest("INTERRUPTED","Review component disabled or scene closed.");if(open)SetDrawer(false);if(Replaying)StopReplay();StopAllCoroutines();if(Showcasing&&screen!=null)screen.showLevelIntro=showcaseIntro;Showcasing=false;if(screen!=null)screen.ReviewInputBlocked=false;if(IsMeasuring)StopMeasurement("COMPONENT_DISABLED");}
    }
}

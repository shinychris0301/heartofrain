using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

namespace HeartOfTheRain.M48 {
    public sealed partial class GameplayReviewTools {
        ManualPlaytestLedger manual;bool manualSubscribed,manualSuspended,manualUnfocused,skipManualTick;float checkpointSeconds;
        public bool ManualPlaytestRunning=>manual!=null&&manual.Active;
        public string LastManualPlaytestOutput {get;private set;}="";
        public string ManualPlaytestStatus {get;private set;}="";
        public string ManualPlaytestNotes="";
        public ManualPlaytestReport ManualPlaytestReport=>manual==null?null:manual.Report;
        public bool BeginManualPlaytest(int level){
            if(!Application.isEditor&&!Debug.isDebugBuild){ManualPlaytestStatus="Manual logging is available in Editor/development builds.";return false;}
            if(ManualPlaytestRunning||SessionRunning||Replaying||Showcasing||Capturing||IsMeasuring||screen==null||!screen.Ready||screen.Busy){ManualPlaytestStatus="Finish the current review, capture or measurement first.";return false;}
            if(level<1||level>screen.uiAssets.boards.levels.Length){ManualPlaytestStatus="Choose a level from 1 to 50.";return false;}
            try {
                // A manual session always starts on a fresh authored board, never the remainder of a replay.
                SetDrawer(false);screen.Load(level-1);
                LastManualPlaytestOutput="";manual=new ManualPlaytestLedger();manual.Report.unity=Application.unityVersion;manual.Report.platform=Application.platform.ToString();
                manual.Report.environment=ManualPlaytestLedger.Environment(Application.isEditor,Application.isMobilePlatform);
                manual.Report.width=Screen.width;manual.Report.height=Screen.height;manual.Report.notes=ManualPlaytestNotes??"";
                var folder=Path.Combine(Application.persistentDataPath,"M48Review");Directory.CreateDirectory(folder);
                LastManualPlaytestOutput=Path.Combine(folder,"manual_"+manual.Report.sessionId+".json");
                BeginManualAttempt();SubscribeManual();screen.ManualPlaytestProtected=true;checkpointSeconds=0;
                ManualPlaytestStatus="Recording normal play. Use the game's Retry/Continue buttons; end this session in Review.";return true;
            }catch(Exception ex){StopManualPlaytest("ERROR",ex.Message);ManualPlaytestStatus="Could not start manual logging: "+ex.Message;return false;}
        }
        void SubscribeManual(){if(manualSubscribed)return;screen.LevelLeaving+=ManualLevelLeaving;screen.LevelLoaded+=ManualLevelLoaded;screen.PlayerActionCompleted+=ManualAction;screen.TurnSettled+=ManualSettled;manualSubscribed=true;}
        void UnsubscribeManual(){if(!manualSubscribed||screen==null)return;screen.LevelLeaving-=ManualLevelLeaving;screen.LevelLoaded-=ManualLevelLoaded;screen.PlayerActionCompleted-=ManualAction;screen.TurnSettled-=ManualSettled;manualSubscribed=false;}
        void BeginManualAttempt(){
            string hash;using(var sha=SHA256.Create())hash=BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(screen.uiAssets.boards.levels[screen.CurrentLevel-1].text))).Replace("-","").ToLowerInvariant();
            manual.BeginAttempt(screen.Model,screen.CurrentSeed,hash);SaveManual();
        }
        void ManualLevelLeaving(string reason){
            if(!ManualPlaytestRunning)return;
            if(reason!="retry"&&reason!="continue"){StopManualPlaytest("INTERRUPTED","Level changed outside normal Retry/Continue.");return;}
            manual.FinishAttempt(reason=="retry"?"RESTARTED":"LEFT_LEVEL",reason);TrySaveManual();
        }
        void ManualLevelLoaded(int level){if(!ManualPlaytestRunning)return;try{BeginManualAttempt();}catch(Exception ex){StopManualPlaytest("ERROR",ex.Message);}}
        void ManualAction(PlayerActionRecord input){if(!ManualPlaytestRunning)return;try{manual.Record(input,screen.Model);SaveManual();}catch(Exception ex){StopManualPlaytest("ERROR",ex.Message);}}
        void ManualSettled(string status){if(!ManualPlaytestRunning)return;try{manual.Settle(screen.Model);SaveManual();}catch(Exception ex){StopManualPlaytest("ERROR",ex.Message);}}
        void TickManualPlaytest(){
            if(!ManualPlaytestRunning||screen==null)return;
            manual.Report.recordingWasActive|=Capturing;if(skipManualTick){skipManualTick=false;return;}
            manual.Tick(Time.unscaledDeltaTime,screen.Paused||manualSuspended||manualUnfocused,screen.Busy,screen.CanAct);
            checkpointSeconds+=Time.unscaledDeltaTime;if(checkpointSeconds>=10){checkpointSeconds=0;TrySaveManual();}
        }
        void SaveManual(){
            manual.Report.notes=ManualPlaytestNotes??"";
            // Preserve the previous checkpoint if serialization/write fails. .tmp is never a completed report.
            var path=LastManualPlaytestOutput;if(string.IsNullOrEmpty(path))throw new IOException("No report path was created.");var temporary=path+".tmp";
            File.WriteAllText(temporary,JsonUtility.ToJson(manual.Report,true));if(File.Exists(path))File.Replace(temporary,path,null);else File.Move(temporary,path);
        }
        void TrySaveManual(){try{SaveManual();}catch(Exception ex){StopManualPlaytest("SAVE_FAILED",ex.Message);}}
        public void StopManualPlaytest(string status="ENDED",string reason="Ended by reviewer."){
            if(manual==null)return;
            manual.Finish(status,reason);UnsubscribeManual();if(screen!=null)screen.ManualPlaytestProtected=false;
            try{SaveManual();ManualPlaytestStatus="Saved manual session: "+manual.Report.status;}catch(Exception ex){ManualPlaytestStatus="Manual report could not be saved: "+ex.Message;Debug.LogError(ManualPlaytestStatus);}
        }
        void OnApplicationPause(bool paused){manualSuspended=paused;skipManualTick=true;measurementClock.Interrupt();if(ManualPlaytestRunning)TrySaveManual();}
        void OnApplicationFocus(bool focused){manualUnfocused=!focused;skipManualTick=true;measurementClock.Interrupt();if(ManualPlaytestRunning)TrySaveManual();}
        void OnApplicationQuit(){if(ManualPlaytestRunning)StopManualPlaytest("INTERRUPTED","Application closed.");}
    }
}

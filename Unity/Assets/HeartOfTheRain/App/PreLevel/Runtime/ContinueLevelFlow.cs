using System;
using System.Collections;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.App.NoMoves;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.Settings;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.App.PreLevel {
    public sealed partial class HomeLevelFlow {
        void ConfigureContinuation(GameplayScreen source){
            var controller=source.gameObject.AddComponent<NoMovesController>();
            controller.Configure(source,home,profile,attemptId,()=>source&&source==gameplay,()=>SettleLoss(source,source.CurrentLevel));
            var hud=source.GetComponent<GameplayHUD>();hud.ExternalResultVisible=()=>completion.IsOpen||controller.Active;
            source.BeforePlayerCommand=()=>ConsumeContinueCheckpoint(source);
        }
        bool ConsumeContinueCheckpoint(GameplayScreen source){
            if(!source||source!=gameplay)return false;
            if(Server)return ServerBeforeCommand(source);
            if(!source.ContinueCheckpointPending)return true;
            try{var a=profile.Service.Read().attempts.First(v=>v.id==attemptId);if(a.continuation.phase=="Purchased")profile.Service.LeaveContinueCheckpoint(attemptId);source.ContinueCheckpointConsumed();return true;}
            catch(Exception){source.ReviewInputBlocked=true;source.SetPause(true);profile.ShowSaveError(()=>{if(ConsumeContinueCheckpoint(source)){source.SetPause(false);source.ReviewInputBlocked=false;}});return false;}
        }
        // A saved attempt this app can't rebuild would otherwise trap every launch. In server mode
        // the player can leave it through the normal one-loss rule and get back to Home.
        Action AbandonUnrestorable(){
            if(!Server)return null;
            return ()=>{home.SetPresentation(true,false);Server.Quit((ok,why)=>{if(ok){profile.Refresh();home.SetPresentation(true,true);}else profile.ShowHomeError(()=>AbandonUnrestorable()());});};
        }
        IEnumerator RestoreContinueAttempt(){
            // Reuse this exact saved attempt. No reservation, starting grant,
            // life loss or level retry is dispatched during restoration.
            yield return null;
            var first=home.GetComponent<FirstStartPage>();while(first&&(!first.Initialized||first.IsVisible))yield return null;
            AttemptRecord saved=null;LevelData savedLevel=null;LegacyLevelGraphics117 savedGraphics=null;Exception error=null;
            try{saved=Server?Server.CompletionReceipt():profile.Service.Read().attempts.Single(a=>a.state=="Started"&&ContinueJournal.Restorable(a));savedLevel=VersionedLevel117.Resolve(assets.gameplay.boards,saved.level,saved.config);savedGraphics=VersionedLevel117.ResolveGraphics(assets.gameplay.boards,saved.level,saved.config);}
            catch(Exception e){error=e;}
            if(error!=null){profile.ShowSaveError(()=>StartCoroutine(RestoreContinueAttempt()),AbandonUnrestorable());yield break;}
            if(gameplay)yield break;attemptId=saved.id;toolSpend.BeginAttempt(attemptId);cupWinTimeCaptured=false;cupWinTime=null;failureSettled=false;SyncTools();
            var go=new GameObject("Restored continue level "+saved.level);gameplay=go.AddComponent<GameplayScreen>();var source=gameplay;source.SettingsBlocked=()=>serverToolPending;source.RecoverFirstPresentationFault=Server;
            source.uiAssets=assets.gameplay;source.initialLevel=saved.level;source.initialSeed=(uint)saved.seed;source.showLevelIntro=false;source.SharedToolInventory=tools;source.ReviewInputBlocked=true;source.DeferTerminalPresentation=true;source.RestoredLevelConfiguration=savedLevel;source.RestoredLevelGraphics=savedGraphics;source.pendingCheckpoint=JsonUtility.FromJson<BoardCheckpoint>(saved.continuation.checkpoint);
            source.ModelTurnAccepted+=turn=>CommitWonModel(source);source.CommitToolSpend=CommitTool;ObserveServerActions(source);home.SetPresentation(false,false);
            launchDeadline=Time.realtimeSinceStartup+15;
            while(source&&source==gameplay&&!source.InitializationComplete&&Time.realtimeSinceStartup<launchDeadline)yield return null;
            if(!source||source!=gameplay)yield break;
            if(!source.InitializationComplete||!source.Ready||!string.IsNullOrEmpty(source.StartingPowerError)){
                Action drop=()=>{if(gameplay){Destroy(gameplay.gameObject);gameplay=null;}};var abandon=AbandonUnrestorable();
                profile.ShowSaveError(()=>{drop();StartCoroutine(RestoreContinueAttempt());},abandon==null?null:(Action)(()=>{drop();abandon();}));yield break;
            }
            if(settingsAssets)source.gameObject.AddComponent<GameplaySettingsController>().Configure(source,settingsAssets,home,decision=>ConfirmExit(source,decision),endLevelAssets);
            completion.Arm(++completionSerial,saved.level);var hud=source.GetComponent<GameplayHUD>();hud.ResultRequested=(won,n)=>won?TryShowCompletion(source,true,n):TrySettleFailure(source,n);hud.RetryPressed=null;
            ConfigureContinuation(source);source.GetComponent<NoMovesController>().Open(true);source.DeferTerminalPresentation=false;
        }
    }
}

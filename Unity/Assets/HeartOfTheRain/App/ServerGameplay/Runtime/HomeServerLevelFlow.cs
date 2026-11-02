using System;
using System.Collections;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.Settings;
using HeartOfTheRain.App.EndLevel;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;

namespace HeartOfTheRain.App.PreLevel {
    public sealed partial class HomeLevelFlow {
        ServerGameSession Server=>profile&&!profile.LocalEconomyMode?profile.ServerSession:null;
        bool serverStartConfirmed,serverVerifying,serverToolPending,serverQuitPending,serverLifeReading;float nextServerLifeRead;Action serverVerifyWaiters;GameplayScreen serverWinSource;int serverWinVerifies;
        readonly ServerCapacityGate86 serverCapacity=new ServerCapacityGate86();
        void ShowServerCapacityExit(GameplayScreen source)=>serverCapacity.Show(source,()=>source&&source==gameplay,()=>SettleLoss(source,source.CurrentLevel));
        void ServerReserve(PreLevelTicket ticket,int generation){
            Server.Reserve(ticket.level,ticket.chosen.Select(v=>v?1:0).ToArray(),(ok,why)=>{
                if(!CurrentLaunch(ticket,generation))return;
                if(!ok){
                    if(!Server.HasPending){profile.Refresh();session.Fail(ticket,home.State.lives<=0?"No lives remaining":"Could not start. Please try again.");launchTicket=null;loading.Hide();session.RefreshLives(home.State.lives);session.RefreshStock(profile.Service.Read().starting);modal.Show(session.View);return;}
                    profile.ShowSaveError(()=>ServerReserve(ticket,generation));return;
                }
                var a=Server.Attempt;
                if(a==null||a.state!="Reserved"||a.level!=ticket.level||!KnownLevelVersion(a.level,a.configHash)||a.seed<=0||a.seed>uint.MaxValue){FailLaunch(ticket,generation);return;}
                attemptId=a.attemptId;toolSpend.BeginAttempt(attemptId);serverStartConfirmed=false;
                StartCoroutine(Launch(ticket,generation));
            });
        }
        // The server binds an attempt to one exact level version. An app newer than the
        // server's catalog still plays that version from its retained originals.
        bool KnownLevelVersion(int level,string config){try{VersionedLevel117.Resolve(assets.gameplay.boards,level,config);return true;}catch(Exception){return false;}}
        LevelData RetainedLevel(int level,string config)=>ProfileJson.Hash(assets.gameplay.boards.levels[level-1].text)==config?null:VersionedLevel117.Resolve(assets.gameplay.boards,level,config);
        void ServerStart(PreLevelTicket ticket,int generation){
            finishingLaunch=true;Server.StartAttempt((ok,why)=>{
                finishingLaunch=false;if(!CurrentLaunch(ticket,generation))return;
                if(!ok){if(!Server.HasPending){FailLaunch(ticket,generation);return;}profile.ShowSaveError(()=>CompleteLaunch(ticket,generation));return;}
                serverStartConfirmed=true;CompleteLaunch(ticket,generation);
            });
        }
        void ServerFailLaunch(PreLevelTicket ticket,int generation){
            Server.CancelReservation((ok,why)=>{
                if(!CurrentLaunch(ticket,generation))return;
                if(!ok){profile.ShowSaveError(()=>FailLaunch(ticket,generation));return;}
                profile.Refresh();session.Fail(ticket,"Could not start. Please try again.");EnsureLoadingArt();loading.ShowFailure();
            });
        }
        void ServerRefill(){
            var source=Server;var requestedSession=session;
            if(!source||!source.Ready||source.AccountBlocked||source.Busy){if(session!=null&&session.IsOpen){session.View.message="Please try again later.";modal.Show(session.View);}return;}
            PreLevelRefillTicket ticket;if(!requestedSession.TryBeginRefill(out ticket))return;var view=ticket.View;
            long ownerEpoch=source.PlayerOwnershipEpoch;string ownerOrigin=source.Origin,ownerPlayer=source.PlayerId;view.message="";modal.Show(view);
            Func<bool> current=()=>this&&source&&Server==source&&source.OwnsPlayer(ownerEpoch,ownerOrigin,ownerPlayer)&&ReferenceEquals(session,requestedSession)&&requestedSession.IsOpen&&ReferenceEquals(requestedSession.View,view);
            // A committed refill needs only a fresh projection if its UI read
            // fails. Retrying that read must not issue another purchase.
            Action refresh=null;refresh=()=>{
                if(!current())return;
                if(!profile.Refresh()){profile.ShowSaveError(refresh);return;}
                RefreshLifeState();modal.Show(view);
            };
            Action<bool,string> completed=(ok,why)=>{
                if(!current()||!requestedSession.OwnsRefill(ticket))return;
                if(!ok&&source.HasPending){
                    // Keep Close and synthetic actions locked until the exact
                    // durable intent is explicitly reconciled.
                    profile.ShowSaveError(()=>{if(current()&&requestedSession.CompleteRefill(ticket))RefillLives();});return;
                }
                if(!requestedSession.CompleteRefill(ticket))return;
                // Transport/unavailable/conflict errors are not proof of an
                // insufficient balance. Keep those failures truthful.
                if(!ok)view.message=source.Wallet!=null&&source.Wallet.coins<LifeRules.RefillCoins?"Not enough coins":"Please try again later.";
                refresh();
            };
            try{source.RefillLives(completed);}catch(Exception){completed(false,"ServerDispatchUnavailable");}
        }
        // An open modal suspends idle Home polling. Its due timer therefore
        // requests one authoritative read rather than regenerating a projection.
        void RefreshServerLifeDue(){
            var source=Server;var requestedSession=session;
            if(serverLifeReading||Time.unscaledTime<nextServerLifeRead||!source||!source.Ready||source.AccountBlocked||source.Busy||requestedSession==null||!requestedSession.IsOpen||requestedSession.View.busy)return;
            var view=requestedSession.View;long ownerEpoch=source.PlayerOwnershipEpoch;string ownerOrigin=source.Origin,ownerPlayer=source.PlayerId;
            Func<bool> current=()=>this&&source&&Server==source&&source.OwnsPlayer(ownerEpoch,ownerOrigin,ownerPlayer)&&ReferenceEquals(session,requestedSession)&&requestedSession.IsOpen&&ReferenceEquals(requestedSession.View,view)&&!view.busy;
            serverLifeReading=true;nextServerLifeRead=Time.unscaledTime+10;view.message=HomeLivesText.T("sync");modal.Show(view);
            Action<bool,string> completed=(ok,why)=>{
                serverLifeReading=false;if(!current())return;
                if(ok&&profile.Refresh()){view.message="";RefreshLifeState();}
                else view.message="Please try again later.";
                modal.Show(view);
            };
            try{source.Refresh(completed);}catch(Exception){completed(false,"ServerDispatchUnavailable");}
        }
        void ObserveServerActions(GameplayScreen source){
            if(!Server)return;
            source.PlayerActionCompleted+=action=>{
                if(!source||source!=gameplay||!action.accepted)return;
                if(!Server.RecordAction(action,source.Model.Checkpoint())){
                    source.ReviewInputBlocked=true;
                    profile.ShowSaveError(()=>Server.Reconcile((ok,why)=>{if(ok&&source&&source==gameplay)source.ReviewInputBlocked=false;}));
                }
            };
        }
        bool ServerCommitTool(BoosterKind kind,int x,int y){
            if(Server.ConsumeToolPermit(kind,x,y))return true;
            if(!Server.HasPending&&!Server.HasToolActionCapacity(gameplay.Model.Moves)){ShowServerCapacityExit(gameplay);return false;}
            if(serverToolPending)return false;
            // Input stays blocked for the round trip, but effects already flying keep playing.
            serverToolPending=true;var source=gameplay;source.ReviewInputBlocked=true;source.ToolSpendDeferred=true;
            StartCoroutine(ServerToolAfterRollback(source,kind,x,y));return false;
        }
        IEnumerator ServerToolAfterRollback(GameplayScreen source,BoosterKind kind,int x,int y){
            // Atlas authorizes inside a speculative permutation. The rejected
            // command restores that permutation and RNG before this capture.
            yield return null;if(!source||source!=gameplay){serverToolPending=false;yield break;}
            var checkpoint=source.Model.Checkpoint();
            Action retry=null;retry=()=>Server.SpendTool(kind,x,y,checkpoint,(ok,why)=>{
                if(!source||source!=gameplay)return;
                if(!ok){
                    if(ServerCapacityGate86.IsCapacityError(why)){serverToolPending=false;ShowServerCapacityExit(source);}
                    // The server refused this tool and spent nothing: back to the board with the real stock.
                    else if(!Server.HasPending&&ServerRefusal(why)){serverToolPending=false;source.ReviewInputBlocked=false;profile.Refresh();SyncTools();}
                    else profile.ShowSaveError(retry);
                    return;
                }
                if(Server.LastOperation?.displayReceipt?.outcome=="Fault"){serverToolPending=false;FinishServerFault(source);return;}
                StartCoroutine(ApplyCommittedTool(source,kind,x,y));
            });retry();
        }
        // Network failures keep their names; the server's own refusal codes and final HTTP refusals don't.
        static bool ServerRefusal(string why)=>!string.IsNullOrEmpty(why)&&(why=="BrokerHttp400"||why=="BrokerHttp409"||why=="BrokerHttp422"||why.IndexOf('_')>0&&why.ToLowerInvariant()==why);
        // The server has already charged this tool, so it is applied here and never sent again.
        // Settings can be open when the reply lands, or the app can come back paused on it.
        IEnumerator ApplyCommittedTool(GameplayScreen source,BoosterKind kind,int x,int y){
            var hud=source.GetComponent<GameplayHUD>();
            while(source&&source==gameplay&&(hud&&hud.IsBlocking||source.Busy))yield return null;
            if(!source||source!=gameplay){serverToolPending=false;yield break;}
            try{
                Server.ArmCommittedTool(kind,x,y);source.SetPause(false);source.ReviewInputBlocked=false;
                // Keep the old shared stock until this deterministic retry
                // spends its one item; then display the server inventory.
                source.UseBooster(kind,x,y);SyncTools();serverToolPending=false;
                if(Server.ToolPermitPending)throw new InvalidOperationException("PaidToolWasNotApplied");
            }catch(Exception){serverToolPending=true;source.ReviewInputBlocked=true;source.SetPause(true);profile.ShowSaveError(()=>StartCoroutine(ApplyCommittedTool(source,kind,x,y)));}
        }
        void VerifyServerBoard(GameplayScreen source,Action ready=null){
            if(source&&source==gameplay&&serverVerifying&&ready!=null){serverVerifyWaiters+=ready;return;}
            if(!source||source!=gameplay||serverVerifying)return;
            serverVerifying=true;source.ReviewInputBlocked=true;var checkpoint=source.Model.Checkpoint();
            Action retry=null;retry=()=>{
                Action<bool,string> completed=(ok,why)=>{
                    if(!source||source!=gameplay){serverVerifying=false;return;}
                    if(!ok){
                        if(ServerCapacityGate86.IsCapacityError(why)){serverVerifying=false;ShowServerCapacityExit(source);return;}
                        if(why=="ServerModelMismatch"||ServerRefusal(why)||source.Model.Status=="Engine fault"||source.Model.Status=="Resolution limit"){
                            serverVerifying=false;
                            source.GetComponent<GameplayHUD>().ShowExitConfirmation(()=>{if(source&&source==gameplay){source.SetPause(false);VerifyServerBoard(source,ready);}},()=>SettleLoss(source,source.CurrentLevel));
                        }else profile.ShowSaveError(retry);
                        return;
                    }
                    serverVerifying=false;profile.Refresh();
                    if(Server.LastOperation?.displayReceipt?.outcome=="Fault"){FinishServerFault(source);return;}
                    if(source.Model.Status=="Playing")source.ReviewInputBlocked=false;
                    var waiting=serverVerifyWaiters;serverVerifyWaiters=null;
                    ready?.Invoke();waiting?.Invoke();
                };
                if(Server.HasPending)Server.Reconcile(completed);else Server.Verify(checkpoint,completed);
            };retry();
        }
        // The final cascade can end before this board's verification returns.
        // Show the result when it does, with a bound in case no receipt arrives.
        void ServerVerifyWin(GameplayScreen source,int number){
            if(serverWinSource!=source){serverWinSource=source;serverWinVerifies=0;}
            if(serverWinVerifies++<3)VerifyServerBoard(source,()=>TryShowCompletion(source,true,number));
        }
        void FinishServerFault(GameplayScreen source){
            if(!source||source!=gameplay)return;int number=source.CurrentLevel;profile.Refresh();
            source.gameObject.SetActive(false);Destroy(source.gameObject);gameplay=null;modal.Hide();OpenPreview(number,true);
        }
        public void AcceptVerifiedServerFault(GameplayScreen source){if(Server&&Server.LastOperation?.displayReceipt?.outcome=="Fault")FinishServerFault(source);}
        void ServerConfirmExit(GameplayScreen source,EndLevelDecision decision){
            if(serverQuitPending)return;serverQuitPending=true;source.ReviewInputBlocked=true;
            Server.Quit((ok,why)=>{
                serverQuitPending=false;if(!source||source!=gameplay)return;
                if(!ok){
                    // Nothing was sent if no command is saved, so the player can go back to the board.
                    Action stay=null;if(!Server.HasPending)stay=()=>{if(!source||source!=gameplay)return;var settings=source.GetComponent<GameplaySettingsController>();if(settings)settings.CancelExit();source.SetPause(false);source.ReviewInputBlocked=false;};
                    profile.ShowSaveError(()=>ConfirmExit(source,decision),stay);return;
                }
                profile.Refresh();var current=Server.CompletionReceipt();
                if(current!=null&&current.state=="Won"){
                    var controller=source.GetComponent<GameplaySettingsController>();if(controller)controller.CancelExit();
                    source.SetPause(false);TryShowCompletion(source,true,decision.Level);return;
                }
                gameplay.gameObject.SetActive(false);Destroy(gameplay.gameObject);gameplay=null;modal.Hide();OpenPreview(decision.Level,true);
            });
        }
        bool ServerBeforeCommand(GameplayScreen source){
            if(Server.Busy||Server.HasPending)return false;
            if(!serverCapacity.BeforeCommand(Server,source,()=>source&&source==gameplay,()=>SettleLoss(source,source.CurrentLevel)))return false;
            if(!Server.ConsumeContinueCheckpoint()){
                source.ReviewInputBlocked=true;source.SetPause(true);profile.ShowSaveError(()=>{if(Server.ConsumeContinueCheckpoint()&&source&&source==gameplay){source.ContinueCheckpointConsumed();source.SetPause(false);source.ReviewInputBlocked=false;}});return false;
            }
            if(source.ContinueCheckpointPending)source.ContinueCheckpointConsumed();
            if(Server.PrefixFlushRequired){VerifyServerBoard(source);return false;}
            return true;
        }
        IEnumerator AwaitServerRestore(){
            while(Server&&!Server.Ready)yield return null;
            while(Server&&Server.Busy)yield return null;
            if(Server&&Server.HasRestorableContinue)yield return RestoreContinueAttempt();
        }
    }
}

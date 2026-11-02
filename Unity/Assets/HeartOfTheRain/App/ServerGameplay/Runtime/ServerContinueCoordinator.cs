using System;
using System.Collections;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.NoMoves;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;

namespace HeartOfTheRain.App.ServerGameplay {
    // Uses the approved Continue/Shop page. All financial and model authority
    // remains in the replay broker; this component only presents receipts.
    public sealed class ServerContinueCoordinator:MonoBehaviour {
        GameplayScreen game;HomePage home;PlayerProfileHost profile;ServerGameSession session;Func<bool> current;Action decline;
        NoMovesPage page;ResourceRequest art;bool active,busy;ContinueOffer offer;
        public bool Active=>active;public NoMovesPage Page=>page;public ContinueOffer Offer=>offer;
        bool Valid=>game&&current!=null&&current();
        public void Configure(GameplayScreen game,HomePage home,PlayerProfileHost profile,Func<bool> current,Action decline){
            this.game=game;this.home=home;this.profile=profile;this.current=current;this.decline=decline;session=profile.ServerSession;
            page=gameObject.AddComponent<NoMovesPage>();page.home=home;page.Requested=Request;
        }
        public void Open(bool restoring=false){
            if(active||!Valid)return;if(art==null)art=NoMovesAssets.LoadAsync();active=true;busy=true;game.ReviewInputBlocked=true;game.SetPause(true);if(art.isDone)page.art=art.asset as NoMovesAssets;if(!restoring)page.ShowExhaustionNotice(home.State.coins);page.Show(restoring&&(!page.art||!page.art.continuePrefab)?"waiting":"loading",null,home.State.coins,true);StartCoroutine(Begin());
        }
        IEnumerator Begin(){
            yield return art;if(!Valid||!active)yield break;page.art=art.asset as NoMovesAssets;
            if(!page.art||!page.art.continuePrefab){Error();yield break;}
            page.Show("loading",null,home.State.coins,true);
            if(session.HasPending){Reconcile();yield break;}
            if(session.HasRestorableContinue){Ready();yield break;}
            session.Verify(game.Model.Checkpoint(),(ok,why)=>{if(!Valid||!active)return;if(ok)Ready();else Error();});
        }
        void Ready(){
            if(!Valid||!active)return;
            var operation=session.LastOperation;
            if(operation?.displayReceipt?.outcome=="Fault"){
                active=busy=false;page.Hide();home.GetComponent<HeartOfTheRain.App.PreLevel.HomeLevelFlow>()?.AcceptVerifiedServerFault(game);return;
            }
            if(operation!=null&&operation.addedMoves==5&&operation.model?.outcome=="Playing"){
                try{
                    var level=game.Model.Level;
                    var receipt=session.PrepareLocalContinue(level);game.ApplyContinuation(receipt);session.AcknowledgeLocalContinue(receipt.afterCheckpoint);
                    profile.Refresh();active=busy=false;page.Hide();game.SetPause(false);game.ReviewInputBlocked=false;
                }catch(Exception){Error();}return;
            }
            if(operation==null||operation.model?.outcome!="Out of moves"){Error();return;}
            if(!session.HasPending&&!session.HasContinueActionCapacity){offer=null;busy=false;page.Status="";Show("offer");return;}
            offer=new ContinueOffer{id=operation.operationId,attempt=operation.attemptId,policy="ServerReplay-900-5",cost=900,moves=5,balance=session.Wallet.coins,expires=session.ServerTimeNow+300};
            busy=false;page.Status="";Show(session.ContinueView=="shop"?"shop":"offer");
        }
        void Show(string screen){if(Valid&&active)page.Show(screen,offer,session.Wallet?.coins??0,busy);}
        void Error(){
            if(!Valid||!active)return;busy=false;page.Status="";
            // The existing error panel keeps Retry and Close available. An
            // unresolved request can be reconciled or explicitly forfeited.
            page.Show("error",null,session.Wallet?.coins??0,false);
        }
        void Reconcile(){busy=true;page.SetBusy(true);session.Reconcile((ok,why)=>{if(!Valid||!active)return;if(ok)Ready();else Error();});}
        public void Request(string action){
            if(!active||!Valid||busy||page.Screen=="notice"||page.Screen=="waiting")return;
            if(page.CheckoutBusy86)return;
            try{
                if(action=="checkout:complete"){session.SetContinueView("offer");profile.Refresh();Ready();return;}
                if(action!=null&&action.StartsWith("checkout:",StringComparison.Ordinal)){page.CheckoutRequest86(action);return;}
                if(action=="retryQuote"||action=="check"){if(session.HasPending)Reconcile();else{busy=true;page.SetBusy(true);session.Verify(game.Model.Checkpoint(),(ok,why)=>{if(ok)Ready();else Error();});}return;}
                if(action=="back"){
                    if(page.Screen=="shop"){session.SetContinueView("offer");Show("offer");}
                    else if(page.Screen=="confirm")Show(offer==null&&(session.HasPending||session.HasContinueActionCapacity)?"error":"offer");else Show("confirm");return;
                }
                if(action=="end"&&page.Screen=="confirm"){busy=true;page.SetBusy(true);decline?.Invoke();return;}
                if(action=="shop"){session.SetContinueView("shop");Show("shop");return;}
                if(action=="store"){page.Status=NoMovesText.T("storeUnavailable");Show("shop");return;}
                if(action!="play"||page.Screen!="offer"||offer==null)return;
                if(!session.HasPending&&!session.HasContinueActionCapacity){Ready();return;}
                if(session.Wallet.coins<900){Request("shop");return;}
                busy=true;page.SetBusy(true);session.PurchaseContinue((ok,why)=>{
                    if(!Valid||!active)return;if(ok){Ready();return;}
                    // A refused affordability/revision check may be resolved
                    // by the fresh wallet; unknown outcomes retain the intent.
                    if(!session.HasPending&&session.Wallet.coins<900){busy=false;session.SetContinueView("shop");Show("shop");}else Error();
                });
            }catch(Exception){Error();}
        }
        void OnDestroy(){if(page)page.Hide();}
    }
}

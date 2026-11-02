using System;
using System.Collections;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.App.NoMoves {
    public sealed class NoMovesController:MonoBehaviour {
        GameplayScreen game;HomePage home;PlayerProfileHost profile;string attempt;Func<bool> current;Action decline;
        ServerContinueCoordinator server;DevelopmentContinueService service;NoMovesPage page;ResourceRequest request;ContinueOffer quote;bool active,busy;string operation;int balance;float nextWalletCheck;
        public bool Active=>server?server.Active:active;public NoMovesPage Page=>server?server.Page:page;public ContinueOffer Offer=>server?server.Offer:quote;
        public void Configure(GameplayScreen game,HomePage home,PlayerProfileHost profile,string attempt,Func<bool> current,Action decline){
            this.game=game;this.home=home;this.profile=profile;this.attempt=attempt;this.current=current;this.decline=decline;
            if(profile.ServerSession&&!profile.LocalEconomyMode){server=gameObject.AddComponent<ServerContinueCoordinator>();server.Configure(game,home,profile,current,decline);return;}
            page=gameObject.AddComponent<NoMovesPage>();page.home=home;page.Requested=Request;
        }
        bool Valid=>game&&current!=null&&current();
        public void Open(bool restoring=false){if(server){server.Open(restoring);return;}if(active||!Valid)return;if(request==null)request=NoMovesAssets.LoadAsync();active=true;busy=true;quote=null;operation=null;page.Status="";game.ReviewInputBlocked=true;game.SetPause(true);if(request.isDone)page.art=request.asset as NoMovesAssets;if(!restoring)page.ShowExhaustionNotice(home.State.coins);page.Show(restoring&&(!page.art||!page.art.continuePrefab)?"waiting":"loading",null,home.State.coins,true);StartCoroutine(Begin(restoring));}
        IEnumerator Begin(bool restoring){
            yield return request;if(!active||!Valid)yield break;
            page.art=request.asset as NoMovesAssets;
            bool enabled=profile.LocalEconomyMode;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            enabled=profile.BackendGifts==null;
#endif
            if(!page.art||!page.art.continuePrefab){busy=false;page.Show("error",null,home.State.coins,false);yield break;}
            page.Show("loading",null,home.State.coins,true);
            service=new DevelopmentContinueService(profile.Service,page.art.rules,profile.Now,n=>JsonUtility.FromJson<LevelData>(game.uiAssets.boards.levels[n-1].text),enabled,a=>VersionedLevel117.Resolve(game.uiAssets.boards,a.level,a.config));
            if(!restoring){if(!Try(()=>service.Capture(attempt,game.Model.Checkpoint()),()=>StartCoroutine(Begin(false))))yield break;}
            AttemptRecord saved=null;if(!Try(()=>saved=service.Read(attempt),()=>StartCoroutine(Begin(true))))yield break;operation=saved.continuation.pending;
            if(!string.IsNullOrEmpty(operation)){Reconcile();yield break;}
            if(saved.continuation.phase=="Purchased"){
                var receipt=saved.continuation.receipts.Last(r=>r.outcome=="Applied");Apply(receipt);yield break;
            }
            if(!Try(()=>quote=service.Quote(attempt),RefreshOffer))yield break;
            // The notice is presented once while the quote is prepared.
            if(!Valid||!active)yield break;busy=false;
            Show(restoring&&saved.continuation.view=="shop"?"shop":"offer");
        }
        bool Try(Action action,Action retry){try{action();return true;}catch(Exception){page.SetBusy(true);profile.ShowSaveError(()=>{if(!Valid||!active)return;page.SetBusy(false);retry();});return false;}}
        void Show(string screen){if(!Valid||!active)return;try{balance=profile.Service.Read().coins;page.Show(screen,quote,balance,busy);}catch(Exception){Unknown();}}
        void RefreshOffer(){if(!Valid||!active||service==null)return;if(!Try(()=>quote=service.Quote(attempt),RefreshOffer))return;profile.Refresh();busy=false;Show("offer");}
        public void Request(string action){if(server){server.Request(action);return;}try{Handle(action);}catch(Exception){Unknown();}}
        void Handle(string action){
            if(!active||!Valid||busy||page.Screen=="notice"||page.Screen=="waiting")return;
            if(page.Screen=="unknown"&&action!="check")return;
            if(action=="play"&&page.Screen!="offer")return;
            if(action=="store"&&page.Screen!="shop")return;
            if(action=="check"&&page.Screen!="unknown")return;
            if(action=="retryQuote"&&page.Screen=="error"){if(service!=null)RefreshOffer();else{busy=true;page.Show(page.art&&page.art.continuePrefab?"loading":"waiting",null,home.State.coins,true);request=NoMovesAssets.LoadAsync();StartCoroutine(Begin(false));}return;}
            if(action=="back"){
                if(page.Screen=="shop"){if(Try(()=>service.SetView(attempt,"offer"),()=>Request("back")))RefreshOffer();}
                else if(page.Screen=="confirm")Show("offer");else Show("confirm");return;
            }
            if(action=="end"){if(page.Screen!="confirm")return;busy=true;page.SetBusy(true);decline();return;}
            if(action=="shop"){if(Try(()=>service.SetView(attempt,"shop"),()=>Request("shop")))Show("shop");return;}
            if(action=="store"){page.Status=NoMovesText.T("storeUnavailable");Show("shop");return;}
            if(action=="check"){Reconcile();return;}
            if(action!="play")return;
            if(quote==null){Show("confirm");return;}
            if(profile.Service.Read().coins<quote.cost){Request("shop");return;}
            if(quote.expires<=profile.Now()){RefreshOffer();page.Status=NoMovesText.T("updated");Show("offer");return;}
            busy=true;page.SetBusy(true);
            try{operation=service.Prepare(attempt,quote.id);}
            catch(InvalidOperationException){busy=false;page.SetBusy(false);RefreshOffer();return;}
            catch(Exception){Unknown();return;}
            Reconcile();
        }
        void Unknown(){busy=false;page.Status="";page.Show("unknown",quote,balance,false);}
        void Reconcile(){
            if(!Valid||!active||service==null)return;busy=true;page.SetBusy(true);
            try{
                var saved=service.Read(attempt);operation=saved.continuation.pending;
                if(string.IsNullOrEmpty(operation)){
                    var committed=saved.continuation.receipts.LastOrDefault(r=>r.outcome=="Applied");
                    if(saved.continuation.phase=="Purchased"&&committed!=null){Apply(committed);return;}
                    // A failed prepare may never have committed. Reading the
                    // durable local store resolves it; no network is in flight.
                    busy=false;RefreshOffer();return;
                }
                var receipt=service.Purchase(attempt,operation);
                if(receipt.outcome=="Applied"){Apply(receipt);return;}
                service.Acknowledge(attempt,operation);operation=null;busy=false;RefreshOffer();if(receipt.outcome=="InsufficientCoins")Request("shop");
            }catch(Exception){Unknown();}
        }
        void Apply(ContinueReceipt receipt){
            try{
                if(!Valid||!active||receipt.attempt!=attempt)return;game.ApplyContinuation(receipt);service.Acknowledge(attempt,receipt.operation);
                if(!profile.Refresh())throw new InvalidOperationException("Profile view unavailable");
                active=false;busy=false;operation=null;page.Hide();game.SetPause(false);game.ReviewInputBlocked=false;
            }catch(Exception){Unknown();}
        }
        void Update(){if(!active||busy||service==null||!Valid||Time.unscaledTime<nextWalletCheck)return;nextWalletCheck=Time.unscaledTime+.5f;try{int coins=profile.Service.Read().coins;if(coins!=balance){balance=coins;Show(page.Screen);}}catch(Exception){Unknown();}}
        void OnDestroy(){if(page)page.Hide();}
    }
}

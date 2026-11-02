#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;
using System.Reflection;
using HeartOfTheRain.M46;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.NoMoves;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
    // Marker opt-in BEFORE Home starts. Every mutation stays in an isolated
    // memory profile; regular app profiles/preferences are never substituted.
    public sealed class NoMovesDeviceProbe:MonoBehaviour {
        public const string Marker="HOTR_RunNoMovesR2";
        [Serializable] public sealed class Fixture {public string scenario,checkpoint;public PlayerProfile profile;public int coinsAfter,movesAfter,countAfter;}
        [Serializable] public sealed class Fixtures {public Fixture[] entries;}
        [Serializable] public sealed class Report {public string status="STARTING",utc,scenario,error,scope="Explicit Android fixture, fixed test clock, isolated memory profile and real connected board/UI. Interactive cases wait for actual device taps; prepared/committed recovery is automatic. No IAP or owner-data mutation.";public int x,y,endX,endY,coins,lives,moves,purchases,playedMoves,boundsChecks;public bool boardPreserved;}
        static Fixture pending;Fixture fixture;Report report;PlayerProfileHost host;HomeLevelFlow flow;GameplayScreen game;NoMovesController controller;HeartOfTheRain.M46.BoardModel originalModel;double deadline;bool replaying;
        static string Output=>Path.Combine(Application.persistentDataPath,"NoMovesR2Device");
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]static void Boot(){var file=Path.Combine(Application.persistentDataPath,Marker);if(!File.Exists(file))return;pending=JsonUtility.FromJson<Fixture>(File.ReadAllText(file));File.Delete(file);pending.profile.Validate();SceneManager.sceneLoaded+=Attach;}
        static void Attach(Scene scene,LoadSceneMode mode){
            var first=FindFirstObjectByType<FirstStartPage>();if(!first)return;SceneManager.sceneLoaded-=Attach;first.reviewAlways=true;
            var host=first.home.GetComponent<PlayerProfileHost>();if(!host)host=first.home.gameObject.AddComponent<PlayerProfileHost>();host.VerificationRepository=new MemoryProfileRepository(pending.profile);host.VerificationAuthorityFactory=_=>new UnavailableGiftAuthority();host.VerificationLivesClock=()=>1000;
            var node=new GameObject("Opt-in No Moves Android verification");DontDestroyOnLoad(node);var probe=node.AddComponent<NoMovesDeviceProbe>();probe.fixture=pending;pending=null;
        }
        void Start(){report=new Report{utc=DateTime.UtcNow.ToString("o"),scenario=fixture.scenario};deadline=Time.realtimeSinceStartupAsDouble+150;Application.logMessageReceived+=Log;StartCoroutine(Ready());}
        void Log(string message,string trace,LogType type){if(type==LogType.Exception||type==LogType.Error||type==LogType.Assert)Finish(new Exception(message+"\n"+trace));}
        IEnumerator Ready(){FirstStartPage first;while(!(first=FindFirstObjectByType<FirstStartPage>())||!first.Initialized)yield return null;first.Request("skip");first.Request("skip");host=first.home.GetComponent<PlayerProfileHost>();flow=first.home.GetComponent<HomeLevelFlow>();
            while(!(game=FindFirstObjectByType<GameplayScreen>())||!game.Ready)yield return null;
            originalModel=game.Model;controller=game.GetComponent<NoMovesController>();while(!controller||!controller.Page){controller=game.GetComponent<NoMovesController>();yield return null;}
            if(fixture.scenario=="prepared"||fixture.scenario=="committed"){
                while(controller.Active||game.ReviewInputBlocked)yield return null;Verify(true);yield break;
            }
            while(!controller.Active||(controller.Page.Screen=="notice"||controller.Page.Screen=="loading"))yield return null;
            VerifyBoard();
            if(fixture.scenario=="shop_bounds"){
                CheckShop(false);var viewport=controller.Page.Nodes["Coin pack viewport"];Vector2 from=RectTransformUtility.WorldToScreenPoint(null,viewport.TransformPoint(new Vector3(viewport.rect.center.x,viewport.rect.yMin+12,0)));Vector2 to=RectTransformUtility.WorldToScreenPoint(null,viewport.TransformPoint(new Vector3(viewport.rect.center.x,viewport.rect.yMax-12,0)));
                report.x=Mathf.RoundToInt(from.x);report.y=Screen.height-Mathf.RoundToInt(from.y);report.endX=Mathf.RoundToInt(to.x);report.endY=Screen.height-Mathf.RoundToInt(to.y);report.status="READY_FOR_SCROLL";Save();yield break;
            }
            if(controller.Page.R3){var v=controller.Page.R3;if(v.Amount.text!="+5"||v.Price.text!="900"||!v.PlayButton.interactable||v.WalletButton.GetComponent<RectTransform>().anchoredPosition.x>=20||!v.Pack.gameObject.activeSelf||v.Primary.rectTransform.rect.width>=v.Band.rect.width-45)throw new Exception("R3 live offer layout/low-balance regression");}
            Button next;
            if(fixture.scenario=="shop"){if(controller.Page.Screen!="shop")throw new Exception("Saved Shop was not restored");next=controller.Page.Nodes["Shop back"].GetComponent<Button>();}
            else if(fixture.scenario=="end")next=controller.Page.Nodes["Continue close"].GetComponent<Button>();
            else next=controller.Page.Nodes["Play on"].GetComponent<Button>();
            OfferTap(next,"READY_FOR_TAP");
        }
        // Inspect actual instantiated button geometry, not only the layout formula.
        public static void VerifyConfirmation(NoMovesPage page,Action<bool,string> check){
            Canvas.ForceUpdateCanvases();var panel=page.Nodes["No Moves content"];
            var keep=page.Nodes["Keep attempt"];var end=page.Nodes["End attempt"];
            check(keep.rect.height>=57&&end.rect.height>=48,"Confirmation buttons keep full touch heights");
            foreach(var button in new[]{keep,end}){
                check(Mathf.Abs(button.anchoredPosition.x+button.rect.width/2-panel.rect.width/2)<.1f,"Confirmation button is centered: "+button.name);
                check(button.rect.width<=panel.rect.width-39.9f&&button.anchoredPosition.y-button.rect.height>=-panel.rect.height+17.9f,"Confirmation button stays within panel: "+button.name);
                var face=button.GetComponent<Button>().targetGraphic as Image;
                check(face&&face.type==Image.Type.Sliced,"Confirmation uses approved sliced artwork: "+button.name);
                float density=face.pixelsPerUnitMultiplier*face.sprite.pixelsPerUnit/face.canvas.referencePixelsPerUnit;
                check(Mathf.Abs(density-(button==keep?300f/35:4))<.01f,"Confirmation preserves source corner density: "+button.name);
            }
            check(keep.anchoredPosition.y-keep.rect.height>end.anchoredPosition.y+8,"Confirmation buttons have clear separation");
        }
        void CheckShop(bool bottom){VerifyShopBounds(controller.Page,(ok,message)=>{report.boundsChecks++;if(!ok)throw new Exception(message);},bottom);}
        // Inspect actual native transforms, including slice-safe margins and bottom reachability.
        public static void VerifyShopBounds(NoMovesPage page,Action<bool,string> check,bool bottom=false){
            Canvas.ForceUpdateCanvases();var inner=page.Nodes["Shop interior"];var panel=page.Nodes["Shop panel"];var wallet=page.Nodes["Wallet"];var view=page.Nodes["Coin pack viewport"];var footer=page.Nodes["Shop back"];
            Func<RectTransform,RectTransform,Rect> bounds=(root,node)=>{var corners=new Vector3[4];node.GetWorldCorners(corners);var lo=new Vector2(float.MaxValue,float.MaxValue);var hi=new Vector2(float.MinValue,float.MinValue);foreach(var corner in corners){Vector2 p=root.InverseTransformPoint(corner);lo=Vector2.Min(lo,p);hi=Vector2.Max(hi,p);}return Rect.MinMaxRect(lo.x,lo.y,hi.x,hi.y);};
            Action<Rect,Rect,string> contains=(outer,r,label)=>check(r.xMin>=outer.xMin-.1f&&r.xMax<=outer.xMax+.1f&&r.yMin>=outer.yMin-.1f&&r.yMax<=outer.yMax+.1f,label);
            var inset=bounds(panel,inner);check(inset.xMin-panel.rect.xMin>=30&&panel.rect.xMax-inset.xMax>=30&&inset.yMin-panel.rect.yMin>=30&&panel.rect.yMax-inset.yMax>=80,"Shop content stays inside cream surface with frame clearance");
            foreach(var node in new[]{wallet,view,footer,page.Nodes["Shop availability"]})contains(inner.rect,bounds(inner,node),"Shop inner containment: "+node.name);
            var v=bounds(inner,view);var f=bounds(inner,footer);var a=bounds(inner,page.Nodes["Shop availability"]);check(v.height>=100&&v.yMin-f.yMax>=12&&a.yMin-v.yMax>=12,"List has positive height and clear separation from header/footer");check(footer.rect.height>=48&&Mathf.Abs(f.center.x-inner.rect.center.x)<.1f,"Shop Back has full touch height and is centered");
            var scroll=view.GetComponent<ScrollRect>();check(scroll.viewport==view&&view.GetComponent<RectMask2D>()&&scroll.movementType==ScrollRect.MovementType.Clamped,"Coin list is clipped to the bounded viewport");
            foreach(RectTransform row in scroll.content){var r=bounds(view,row);check(r.xMin>=view.rect.xMin-.1f&&r.xMax<=view.rect.xMax+.1f,"Coin row horizontal containment");foreach(RectTransform child in row)contains(row.rect,bounds(row,child),"Coin row child containment: "+child.name);}
            if(bottom&&scroll.content.childCount>0){var last=(RectTransform)scroll.content.GetChild(scroll.content.childCount-1);contains(view.rect,bounds(view,last),"Last coin pack is fully reachable above footer");check(scroll.verticalNormalizedPosition<.01f,"Coin list reached its actual bottom after scrolling");}
        }
        void OfferTap(Button button,string status){Canvas.ForceUpdateCanvases();Vector3 p=button.transform.TransformPoint(button.GetComponent<RectTransform>().rect.center);Vector2 screen=RectTransformUtility.WorldToScreenPoint(null,p);report.x=Mathf.RoundToInt(screen.x);report.y=Screen.height-Mathf.RoundToInt(screen.y);report.status=status;Save();}
        void VerifyBoard(){if(firstHomeVisible())throw new Exception("Home is visible over restored gameplay");if(JsonUtility.ToJson(game.Model.Checkpoint())!=fixture.checkpoint)throw new Exception("Restored board/RNG differs from fixture");report.boardPreserved=true;}
        bool firstHomeVisible()=>FindFirstObjectByType<HomePage>().PresentationVisible;
        void Verify(bool resumed){
            if(firstHomeVisible())throw new Exception("Home is visible over restored gameplay");
            var p=host.Service.Read();var attempt=p.attempts.Last();if(p.coins!=fixture.coinsAfter||p.lives!=5||game.Model.Moves!=fixture.movesAfter||attempt.state!="Started")throw new Exception("Unexpected continue balances/state");
            if(resumed){if(game.Model.Status!="Playing"||controller.Active||game.ReviewInputBlocked||attempt.continuation.count!=(fixture.countAfter>0?fixture.countAfter:1)||!string.IsNullOrEmpty(attempt.continuation.pending)||!ReferenceEquals(originalModel,game.Model)||JsonUtility.ToJson(game.Model.Checkpoint())!=attempt.continuation.checkpoint)throw new Exception("Continue not reconciled");report.boardPreserved=true;}
            else VerifyBoard();if(attempt.continuation.count!=fixture.countAfter)throw new Exception("Unexpected repeat purchase count");report.purchases=attempt.continuation.count;report.coins=p.coins;report.lives=p.lives;report.moves=game.Model.Moves;Finish(null);
        }
        void Update(){if(report==null||report.status.StartsWith("PASS")||report.status.StartsWith("FAIL"))return;if(Time.realtimeSinceStartupAsDouble>deadline){Finish(new TimeoutException("Android No Moves probe timeout"));return;}
            try{
                if(report.status=="READY_FOR_SCROLL"&&controller.Page.Nodes["Coin pack viewport"].GetComponent<ScrollRect>().verticalNormalizedPosition<.001f){CheckShop(true);OfferTap(controller.Page.Nodes["Shop back"].GetComponent<Button>(),"READY_FOR_BACK");return;}
                if(report.status=="READY_FOR_BACK"&&controller.Page.Screen=="offer"){Verify(false);return;}
                if(report.status=="READY_FOR_TAP"){
                    if(fixture.scenario=="repeat"&&!controller.Active&&!replaying){
                        replaying=true;var p=host.Service.Read();if(p.coins!=1250||p.lives!=5||p.attempts.Last().continuation.count!=2||game.Model.Moves!=5)throw new Exception("Second purchase failed");StartCoroutine(ExhaustAndOffer());return;
                    }
                    if((fixture.scenario=="offer"||fixture.scenario=="exact")&&!controller.Active){Verify(true);return;}
                    if((fixture.scenario=="insufficient"||fixture.scenario=="repeat_insufficient"||fixture.scenario=="zero"||fixture.scenario=="below")&&controller.Page.Screen=="shop"){if(!string.IsNullOrEmpty(host.Service.Read().attempts.Last().continuation.pending))throw new Exception("Insufficient tap dispatched a spend");Verify(false);return;}
                    if(fixture.scenario=="shop"&&controller.Page.Screen=="offer"){Verify(false);return;}
                    if(fixture.scenario=="end"&&controller.Page.Screen=="confirm"){VerifyConfirmation(controller.Page,(ok,label)=>{report.boundsChecks++;if(!ok)throw new Exception(label);});OfferTap(controller.Page.Nodes["End attempt"].GetComponent<Button>(),"READY_TO_END");}
                }
                if(report.status=="READY_FOR_REPEAT"&&!controller.Active){Verify(true);return;}
                if(report.status=="READY_TO_END"&&flow.RetryVisible){var p=host.Service.Read();if(p.lives!=4||p.coins!=fixture.coinsAfter||p.attempts.Last().state!="Lost")throw new Exception("End did not settle once");report.purchases=p.attempts.Last().continuation.count;report.coins=p.coins;report.lives=p.lives;report.moves=0;Finish(null);}
            }catch(Exception e){Finish(e);}
        }
        // Test-only move choice avoids completing the fixture while consuming
        // every granted move through the real gameplay command/animation path.
        public static Cell[] SafeSwap(BoardModel board){
            Cell[] best=null;int remaining=int.MinValue;
            foreach(var m in board.LegalSwaps()){
                var candidate=BoardModel.FromCheckpoint(board.Level,board.Checkpoint());candidate.Swap(m[0].x,m[0].y,m[1].x,m[1].y);
                if(candidate.Status=="Won")continue;int goals=candidate.Goals.Values.Sum();
                if(goals>remaining){remaining=goals;best=m;if(goals==board.Goals.Values.Sum())break;}
            }
            return best??throw new InvalidOperationException("No nonwinning fixture swap");
        }
        IEnumerator ExhaustAndOffer(){
            while(game.Model.Status=="Playing"){
                while(!game.CanAct)yield return null;var m=SafeSwap(game.Model);
                typeof(GameplayScreen).GetMethod("PlayerSwap",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(game,new object[]{m[0].x,m[0].y,m[1].x,m[1].y});report.playedMoves++;
                while(game.Busy)yield return null;
            }
            while(!controller.Active||(controller.Page.Screen=="notice"||controller.Page.Screen=="loading"))yield return null;
            if(report.playedMoves!=5||controller.Offer==null||controller.Offer.cost!=900||controller.Offer.moves!=5||host.Service.Read().lives!=5)throw new Exception("Third offer did not appear after all five moves");
            OfferTap(controller.Page.Nodes["Play on"].GetComponent<Button>(),"READY_FOR_REPEAT");
        }
        void Save(){Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"Report.json"),JsonUtility.ToJson(report,true));}
        void Finish(Exception error){if(report==null||report.status.StartsWith("PASS")||report.status.StartsWith("FAIL"))return;report.status=error==null?"PASS_ANDROID_NO_MOVES":"FAIL_ANDROID_NO_MOVES";report.error=error==null?"":error.ToString();Application.logMessageReceived-=Log;Save();}
        void OnDestroy(){Application.logMessageReceived-=Log;}
    }
}
#endif

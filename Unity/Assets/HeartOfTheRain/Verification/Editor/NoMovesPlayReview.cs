#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.NoMoves;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 [InitializeOnLoad] public static class NoMovesPlayReview {
  const string Key="HOTR.NoMoves.Play";static bool launched;static int original,first;
  static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
  static EditorWindow View()=>EditorWindow.GetWindow(typeof(UnityEditor.Editor).Assembly.GetType("UnityEditor.GameView"));
  static object Group(){var a=typeof(UnityEditor.Editor).Assembly;var t=a.GetType("UnityEditor.GameViewSizes");var instance=typeof(ScriptableSingleton<>).MakeGenericType(t).GetProperty("instance",BindingFlags.Public|BindingFlags.Static).GetValue(null);return t.GetMethod("GetGroup").Invoke(instance,new[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeGroupType"),EditorUserBuildSettings.activeBuildTarget==BuildTarget.Android?"Android":"Standalone")});}
  static readonly Vector2Int[] Sizes={new Vector2Int(393,852),new Vector2Int(320,568),new Vector2Int(768,1024),new Vector2Int(1179,2556),new Vector2Int(1572,3408)};
  static NoMovesPlayReview(){if(SessionState.GetBool(Key,false)){original=SessionState.GetInt(Key+".original",0);first=SessionState.GetInt(Key+".first",0);EditorApplication.update+=Tick;}}
  public static void Run(){var group=Group();first=(int)group.GetType().GetMethod("GetTotalCount").Invoke(group,null);original=(int)View().GetType().GetProperty("selectedSizeIndex",Private|BindingFlags.Public).GetValue(View());SessionState.SetInt(Key+".original",original);SessionState.SetInt(Key+".first",first);
   var a=typeof(UnityEditor.Editor).Assembly;foreach(var s in Sizes){var v=Activator.CreateInstance(a.GetType("UnityEditor.GameViewSize"),BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance,null,new object[]{Enum.Parse(a.GetType("UnityEditor.GameViewSizeType"),"FixedResolution"),s.x,s.y,"HOTR No Moves R2"},null);group.GetType().GetMethod("AddCustomSize").Invoke(group,new[]{v});}
   SessionState.SetBool(Key,true);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");UnityEngine.Object.FindFirstObjectByType<FirstStartPage>().reviewAlways=true;EditorApplication.isPlaying=true;
  }
  static void Tick(){if(!EditorApplication.isPlaying||EditorApplication.isCompiling||launched)return;launched=true;var probe=new GameObject("No Moves native connected verification").AddComponent<NoMovesReviewProbe>();probe.SetSize=n=>View().GetType().GetProperty("selectedSizeIndex",Private|BindingFlags.Public).SetValue(View(),first+n);probe.Finished=code=>{SessionState.EraseBool(Key);View().GetType().GetProperty("selectedSizeIndex",Private|BindingFlags.Public).SetValue(View(),original);var group=Group();for(int n=Sizes.Length-1;n>=0;n--)group.GetType().GetMethod("RemoveCustomSize").Invoke(group,new object[]{first+n});EditorApplication.Exit(code);};}
 }
 public sealed class NoMovesReviewProbe:MonoBehaviour {
  [Serializable] public sealed class Report {public string status="RUNNING",utc,error,scope="Native Editor live connected GameplayScreen, isolated memory profile, synthetic one-move budget, modal/shop/continue/restart/confirmed-loss routing and native camera+UGUI composites. Timed card rendering uses an explicit simulated foreground in the offscreen Editor. Not owner save, physical input, IAP or device certification.";public int checks,layouts;public List<string> frames=new List<string>(),flow=new List<string>();}
  public Action<int> SetSize,Finished;Report report;HomePage home;HomeLevelFlow flow;PlayerProfileHost host;GameplayScreen game;NoMovesController controller;double deadline;int oldLocale;
  // Exact approved copy, independently checked against the rendered R3 labels;
  // glyph-presence checks alone cannot catch literal question-mark corruption.
  static readonly string[] ExpectedLoading={"Loading offer...","Cargando oferta...","Chargement de l\u2019offre...","Angebot wird geladen...","\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u044f..."};
  static readonly string[] ExpectedOfferError={"Could not load the offer.","No se pudo cargar la oferta.","Impossible de charger l\u2019offre.","Angebot konnte nicht geladen werden.","\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u0435."};
  static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
  static string Output=>Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_NO_MOVES_OUTPUT")??"../Verification/Evidence/NoMovesR2");
  static T Field<T>(object o,string n)=>(T)o.GetType().GetField(n,Private).GetValue(o);
  static void Set(object o,string n,object v)=>o.GetType().GetField(n,Private).SetValue(o,v);
  void Check(bool value,string label){report.checks++;if(!value)throw new Exception(label);}
  void Start(){report=new Report{utc=DateTime.UtcNow.ToString("o")};Directory.CreateDirectory(Output);deadline=Time.realtimeSinceStartupAsDouble+480;oldLocale=GameLocale.Current;Application.logMessageReceived+=Log;StartCoroutine(Run());}
  void Update(){if(report.status=="RUNNING"&&Time.realtimeSinceStartupAsDouble>deadline)Finish(new TimeoutException("No Moves connected review timeout"));}
  void Log(string text,string trace,LogType type){if(type==LogType.Exception||type==LogType.Error||type==LogType.Assert)Finish(new Exception(text+"\n"+trace));}
  IEnumerator WaitReady(){while(!(game=UnityEngine.Object.FindFirstObjectByType<GameplayScreen>())||!game.Ready||game.ReviewInputBlocked)yield return null;yield return null;}
  void BudgetOne(){var c=game.Model.Checkpoint();c.board.moves=1;var b=BoardModel.FromCheckpoint(game.Model.Level,c);Set(game,"board",b);Set(game,"idle",b.Snapshot());}
  void Swap(){var p=game.Model.LegalSwaps().First();typeof(GameplayScreen).GetMethod("PlayerSwap",Private).Invoke(game,new object[]{p[0].x,p[0].y,p[1].x,p[1].y});}
  IEnumerator Run(){
   SetSize(0);yield return null;var first=UnityEngine.Object.FindFirstObjectByType<FirstStartPage>();while(!first||!first.Initialized){first=UnityEngine.Object.FindFirstObjectByType<FirstStartPage>();yield return null;}
   first.Request("skip");first.Request("skip");home=UnityEngine.Object.FindFirstObjectByType<HomePage>();flow=home.GetComponent<HomeLevelFlow>();host=home.GetComponent<PlayerProfileHost>();flow.Open(1);home.GetComponent<PreLevelModal>().Requested("play");yield return WaitReady();
   host.Service.Change(p=>{p.coins=1600;return true;});host.Refresh();BudgetOne();Swap();while(game.Busy)yield return null;controller=game.GetComponent<NoMovesController>();while(!controller.Active)yield return null;
   Check(controller.Page.Screen=="notice"&&controller.Page.Visible,"The zero-move turn shows one out-of-moves notice first");
   Check(game.ReviewInputBlocked&&controller.Page.R3==null,"The board is blocked and no Continue prefab flashes behind the notice");Capture("Connected_Notice_EN.png");
   controller.Request("back");Check(controller.Page.Screen=="notice"&&host.Service.Read().lives==5,"Back cannot dismiss or settle the timed notice");
   yield return new WaitForSecondsRealtime(.25f);Check(controller.Page.Screen=="notice","Notice remains visible long enough to read");
   HeartOfTheRain.NoMovesUI.NoMovesOverlayView firstOverlay=null;
   while(controller.Page.Screen=="notice"||controller.Page.Screen=="loading"){
    if(controller.Page.Screen=="loading"){Check(controller.Page.R3!=null,"Loading never displays the obsolete fallback Continue panel");if(firstOverlay==null)firstOverlay=controller.Page.R3;else Check(firstOverlay==controller.Page.R3,"Loading uses one Continue instance");}
    yield return null;
   }
   Check(game.Model.Status=="Out of moves"&&!game.GetComponent<GameplayHUD>().LossPending,"Zero-move turn is intercepted before old loss settlement");Check(controller.Page.Screen=="offer"&&host.Service.Read().lives==5,"The notice transitions to the Continue offer without a life debit");Check(firstOverlay==null||firstOverlay==controller.Page.R3,"Resolved offer reuses the same loading prefab");
   string attempt=Field<string>(flow,"attemptId");var beforeBoard=game.Model;string checkpoint=JsonUtility.ToJson(beforeBoard.Checkpoint());Check(host.Service.Read().attempts.Last().state=="Started","Attempt remains started");Capture("Connected_Offer_EN.png");
   // Exercise the actual page with a deliberately delayed asset/error and a
   // cancelled presentation. These are UI-only fixtures: no profile mutation.
   var timingObject=new GameObject("No Moves delayed-art fixture");var timing=timingObject.AddComponent<NoMovesPage>();timing.home=home;timing.ShowExhaustionNotice(0);timing.Show("loading",null,0,true);
   yield return new WaitForSecondsRealtime(1.3f);Check(timing.Screen=="notice"&&timing.Visible&&timing.R3==null,"Slow asset load keeps the notice instead of flashing an old Continue layout");
   timing.Show("error",null,0,false);float noticeDeadline=Time.realtimeSinceStartup+5;while(timing.Screen=="notice"&&Time.realtimeSinceStartup<noticeDeadline)yield return null;
   Check(timing.Screen=="error"&&timing.Visible,"A final load error replaces the notice with a recoverable error");
   timing.ShowExhaustionNotice(0);timing.Show("error",null,0,false);timing.Hide();yield return new WaitForSecondsRealtime(1.2f);Check(!timing.Visible,"Closing the page cancels a queued notice transition");Destroy(timingObject);
   controller.Page.R3.PackButton.onClick.Invoke();Check(controller.Page.Screen=="shop"&&host.Service.Read().coins==1600&&host.Service.Read().lives==5,"R3 coin card opens existing Shop without spending");controller.Request("back");
   controller.Page.R3.WalletButton.onClick.Invoke();Check(controller.Page.Screen=="shop","R3 wallet plus opens Shop");controller.Request("back");
   controller.Page.Show("error",null,1600,false);controller.Page.R3.PlayButton.onClick.Invoke();Check(controller.Page.Screen=="offer"&&controller.Offer!=null,"R3 error retries the offer rather than ending level");

   game.GetComponent<GameplayHUD>().ShowPause();Check(!game.GetComponent<HeartOfTheRain.App.Settings.GameplaySettingsController>().IsVisible,"Settings cannot cover Continue");
   for(int size=0;size<5;size++)for(int locale=0;locale<5;locale++)foreach(string screen in new[]{"offer","shop","confirm","unknown","loading","error"}){
    SetSize(size);GameLocale.Select(locale);yield return null;yield return null;controller.Page.Show(screen,controller.Offer,host.Service.Read().coins,false);yield return null;Canvas.ForceUpdateCanvases();InspectText();
    if(screen=="loading"||screen=="error"){
     string expected=screen=="loading"?ExpectedLoading[locale]:ExpectedOfferError[locale];var overlay=controller.Page.R3;
     Check(NoMovesText.T(screen=="loading"?"loadingOffer":"offerError")==expected,"Exact localized transient copy survives source encoding: "+GameLocale.Codes[locale]+"/"+screen);
     Check(overlay&&overlay.Copy.text==expected,"Actual R3 body contains the exact localized transient copy: "+GameLocale.Codes[locale]+"/"+screen);
     Check(overlay.PlayLabel.text==(screen=="loading"?ExpectedLoading[locale]:GameLocale.T("Try again")),"Actual R3 button has correct localized loading/retry text: "+GameLocale.Codes[locale]+"/"+screen);
     Check(screen!="loading"||!overlay.PlayButton.interactable,"Loading copy remains a disabled offer action");
    }
    if(screen=="offer"){
     foreach(int wallet in new[]{0,700,899,900,1600}){controller.Page.Show("offer",controller.Offer,wallet,false);Canvas.ForceUpdateCanvases();var v=controller.Page.R3;Check(v&&v.Amount.text=="+5"&&v.Price.text=="900"&&v.PlayButton.interactable,"R3 offer independent of balance");Check(v.WalletButton.GetComponent<RectTransform>().anchoredPosition.x<20&&v.WalletPlus.sprite,"R3 wallet is left with plus");Check(v.Primary.type==Image.Type.Sliced&&v.Primary.rectTransform.rect.width<v.Band.rect.width-45&&Mathf.Abs(v.Primary.rectTransform.rect.height-57)<.1f,"R3 compact sliced Play On");Check(v.Pack.gameObject.activeSelf,"R3 coin browse card exists");float density=v.Primary.sprite.pixelsPerUnit/v.Primary.canvas.referencePixelsPerUnit*v.Primary.pixelsPerUnitMultiplier;Check(Mathf.Abs(density-300f/35)<.01f,"R3 primary corner density");InspectText();}
     controller.Page.Show("offer",controller.Offer,host.Service.Read().coins,false);
    }if(screen=="confirm")NoMovesDeviceProbe.VerifyConfirmation(controller.Page,Check);if(screen=="shop")foreach(var button in controller.Page.GetComponentsInChildren<Button>()){if(button.name!="Unavailable store purchase")continue;var rect=button.GetComponent<RectTransform>().rect;var image=button.targetGraphic as Image;Check(rect.height>=48&&rect.width<((RectTransform)button.transform.parent).rect.width*.5f,"Shop purchase buttons are compact with full touch height");Check(image&&Mathf.Abs(image.pixelsPerUnitMultiplier*image.sprite.pixelsPerUnit/image.canvas.referencePixelsPerUnit-10)<.01f,"Shop button corners use R3 density");}if(screen=="shop"){NoMovesDeviceProbe.VerifyShopBounds(controller.Page,Check);var scroll=controller.Page.Nodes["Coin pack viewport"].GetComponent<ScrollRect>();scroll.verticalNormalizedPosition=0;Canvas.ForceUpdateCanvases();NoMovesDeviceProbe.VerifyShopBounds(controller.Page,Check,true);if(size<3&&locale==0)Capture("Layout_"+size+"_en_shop_bottom.png");scroll.verticalNormalizedPosition=1;Canvas.ForceUpdateCanvases();}report.layouts++;
    if((size<3&&locale==0)||(size==0&&locale==4))Capture("Layout_"+size+"_"+GameLocale.Codes[locale]+"_"+screen+".png");
   }
   // Actual timed HUD cards in the offscreen Editor use an explicitly
   // simulated foreground; device lifecycle timing is accepted separately.
   controller.Page.Hide();var introHud=game.GetComponent<GameplayHUD>();introHud.VerificationObstacleForeground=true;
   report.checks+=NativeVerification.ObstacleTimingChecks99();
   for(int size=0;size<3;size++)for(int lang=0;lang<5;lang++)foreach(var card in ObstacleIntroductionRules.All.Where(c=>c.Family!="crate"&&c.Family!="moss")){
    SetSize(size);GameLocale.Select(lang);yield return null;yield return null;
    int completed=0;introHud.ShowObstacleIntroduction(card,()=>completed++,game.ObstacleIntroductionSprite(card.ArtKey));yield return null;Canvas.ForceUpdateCanvases();
    Check(introHud.ObstacleIntroductionVisible&&introHud.ObstacleIntroductionFamily==card.Family,"Actual HUD shows correct newcomer card");
    var dialog=Field<RectTransform>(introHud,"modal").Find("Dialog");Check(dialog.GetComponentsInChildren<Button>().Length==0,"Obstacle card has no Continue button or other manual action");InspectText(introHud.gameObject);
    if(lang==4&&(size==0||card.Family=="stone"))Capture("Obstacle_"+card.Family+"_ru_"+size+".png");
    if(size==0&&lang==0&&card.Family=="stone"){
     while(introHud.ObstacleIntroductionFullyVisibleSeconds<.2)yield return null;
     introHud.VerificationObstacleForeground=false;yield return null;double paused=introHud.ObstacleIntroductionFullyVisibleSeconds;
     yield return new WaitForSecondsRealtime(.25f);Check(completed==0&&introHud.ObstacleIntroductionVisible&&Math.Abs(introHud.ObstacleIntroductionFullyVisibleSeconds-paused)<.01,"Simulated background freezes the actual HUD card dwell");introHud.VerificationObstacleForeground=true;
    }
    float until=Time.realtimeSinceStartup+5;
    while(completed==0){if(Time.realtimeSinceStartup>until)throw new TimeoutException("Timed obstacle card did not dismiss");Check(introHud.ObstacleIntroductionVisible,"Card remains visible before its timed completion");yield return null;}
    Check(completed==1&&!introHud.ObstacleIntroductionVisible&&introHud.LastObstacleIntroductionVisibleSeconds>=1.5,"Timed card dismisses after1.5fully visible foreground seconds");
    yield return null;Check(completed==1,"Timed completion cannot invoke the callback twice");report.layouts++;
   }
   introHud.VerificationObstacleForeground=null;
   GameLocale.Select(0);SetSize(0);yield return null;controller.Page.Show("offer",controller.Offer,1600,false);
   host.Service.Change(p=>{p.coins=700;return true;});controller.Request("play");Check(controller.Page.Screen=="shop","Insufficient Play On opens Shop in the same action");Check(string.IsNullOrEmpty(host.Service.Read().attempts.Last().continuation.pending),"Insufficient Play On dispatches no spend");Check(!home.PresentationVisible,"Home remains hidden after unpaid restoration");Check(JsonUtility.ToJson(game.Model.Checkpoint())==checkpoint&&host.Service.Read().lives==5,"Shop preserves board, RNG, life");Capture("Connected_Shop_Insufficient.png");
   controller.Request("store");Check(host.Service.Read().coins==700&&controller.Page.Screen=="shop","Unavailable preview store grants no coins");
   Set(flow,"gameplay",null);game.gameObject.SetActive(false);Destroy(game.gameObject);host.Service.RecoverInterrupted();flow.StartCoroutine((IEnumerator)typeof(HomeLevelFlow).GetMethod("RestoreContinueAttempt",Private).Invoke(flow,null));yield return null;
   while(!(game=UnityEngine.Object.FindFirstObjectByType<GameplayScreen>())||!game.Ready)yield return null;controller=game.GetComponent<NoMovesController>();while(!controller||controller.Page.Screen!="shop"){controller=game.GetComponent<NoMovesController>();yield return null;}
   Check(!home.PresentationVisible,"Home remains hidden after unpaid restoration");Check(JsonUtility.ToJson(game.Model.Checkpoint())==checkpoint&&host.Service.Read().coins==700&&host.Service.Read().lives==5,"Reopening Shop restores the exact zero-move board without settlement");beforeBoard=game.Model;report.flow.Add("Unpaid Shop reconstruction / same checkpoint / no life loss");Capture("Connected_Restored_Shop.png");controller.Request("back");Check(controller.Page.Screen=="offer","Shop Back restores same offer");controller.Request("back");Check(controller.Page.Screen=="confirm","Close requires end confirmation");controller.Request("back");Check(controller.Page.Screen=="offer"&&game.Model.Moves==0,"Cancel returns to offer, never zero-move gameplay");
   var stalePlay=controller.Page.Nodes["Play on"].GetComponent<Button>();controller.Request("shop");host.Service.Grant("NoMovesReview/credit","verification",new RewardGrant{coins=1300});stalePlay.onClick.Invoke();controller.Request("play");Check(game.Model.Moves==0&&host.Service.Read().coins==2000,"Stale offer callback and Shop state cannot spend after a coin credit");controller.Request("back");controller.Request("play");while(controller.Active)yield return null;
   Check(ReferenceEquals(game.Model,beforeBoard)&&game.Model.Moves==5&&game.Model.Status=="Playing","Purchase resumes same board instance with five moves");Check(host.Service.Read().coins==1100&&host.Service.Read().lives==5,"One 900-coin debit, no life debit");controller.Request("play");Check(host.Service.Read().coins==1100,"Repeated callback cannot charge twice");report.flow.Add("Single Continue panel / offer / settings gate / insufficient direct Shop / preview store / Back / confirmed exit cancel / atomic continue");Capture("Connected_Resumed.png");
   // Recreate gameplay against the same durable-shaped journal. The profile
   // repository is intentionally memory-only; disk crashes are covered separately.
   string continued=JsonUtility.ToJson(game.Model.Checkpoint());Set(flow,"gameplay",null);game.gameObject.SetActive(false);Destroy(game.gameObject);host.Service.RecoverInterrupted();var restore=(IEnumerator)typeof(HomeLevelFlow).GetMethod("RestoreContinueAttempt",Private).Invoke(flow,null);flow.StartCoroutine(restore);yield return null;
   while(!(game=UnityEngine.Object.FindFirstObjectByType<GameplayScreen>())||!game.Ready)yield return null;controller=game.GetComponent<NoMovesController>();while(!controller||controller.Active||game.ReviewInputBlocked){controller=game.GetComponent<NoMovesController>();yield return null;}
   Check(!home.PresentationVisible,"Home remains hidden after paid restoration");Check(JsonUtility.ToJson(game.Model.Checkpoint())==continued&&host.Service.Read().coins==1100&&host.Service.Read().lives==5,"Reopening restores committed unused moves and exact RNG");report.flow.Add("Live board reconstruction / pending paid checkpoint reconciliation");
   var firstReceipt=host.Service.Read().attempts.Last().continuation.receipts.Last(r=>r.outcome=="Applied");
   for(int purchase=2;purchase<=3;purchase++){
    while(game.Model.Status=="Playing"){var m=NoMovesDeviceProbe.SafeSwap(game.Model);typeof(GameplayScreen).GetMethod("PlayerSwap",Private).Invoke(game,new object[]{m[0].x,m[0].y,m[1].x,m[1].y});while(game.Busy)yield return null;}
    while(!controller.Active||(controller.Page.Screen=="notice"||controller.Page.Screen=="loading"))yield return null;
    Check(controller.Offer!=null&&controller.Offer.cost==900&&controller.Offer.moves==5,"Repeat exhaustion offers the same five moves / 900 coins");
    Check(!controller.Page.Status.Contains("Unavailable"),"Repeat panel has no stale status");
    host.Service.Grant("RepeatReview/credit/"+purchase,"verification",new RewardGrant{coins=900});int balance=host.Service.Read().coins;var sameBoard=game.Model;
    if(purchase==2){Capture("Connected_Second_Offer.png");Check(controller.Offer.id!=firstReceipt.quote,"Second purchase has a new quote");}
    controller.Request("play");while(controller.Active)yield return null;
    Check(ReferenceEquals(game.Model,sameBoard)&&game.Model.Moves==5&&host.Service.Read().coins==balance-900&&host.Service.Read().lives==5,"Repeat purchase preserves live board and charges once");
    Check(host.Service.Read().attempts.Last().continuation.count==purchase,"Repeat purchase journal survives validation");
    string unchanged=JsonUtility.ToJson(game.Model.Checkpoint());bool rejected=false;try{game.ApplyContinuation(firstReceipt);}catch(InvalidOperationException){rejected=true;}Check(rejected&&JsonUtility.ToJson(game.Model.Checkpoint())==unchanged,"Earlier receipt cannot reset a newer board or grant moves");
    controller.Request("play");Check(host.Service.Read().coins==balance-900,"Repeated UI callback cannot charge again");Capture("Connected_Purchase_"+purchase+".png");
   }
   report.flow.Add("Three purchases in one attempt / all five granted moves consumed between offers / no life debit / stale receipt rejected");
   BudgetOne();Swap();while(game.Busy)yield return null;while(!controller.Active||(controller.Page.Screen=="notice"||controller.Page.Screen=="loading"))yield return null;Check(controller.Offer!=null&&controller.Page.Screen=="offer","A further purchase remains available");Check(!ContinueJournal.Restorable(new AttemptRecord{continuation=new ContinueJournal()}),"Empty journal is not resumable");controller.Request("back");Capture("Connected_End_Confirmation.png");controller.Request("end");
   while(!flow.RetryVisible)yield return null;Check(host.Service.Read().lives==4&&host.Service.Read().attempts.Last().state=="Lost","Confirmed end reaches existing Try Again with one life debit");report.flow.Add("Voluntary confirmed loss after repeated purchases / existing Try Again");Capture("Connected_Try_Again.png");
   // A natural one-move model fixture proves win priority without changing a level asset.
   var win=WinningFixture();var wb=new BoardModel(win);var won=wb.Swap(1,1,1,0);Check(won.accepted&&wb.Moves==0&&wb.Status=="Won","Final-move clear wins before out-of-moves offer");
   Finish(null);
  }
  void InspectText(GameObject content=null){var texts=content?content.GetComponentsInChildren<Text>():controller.Page.GetComponentsInChildren<Text>();foreach(var t in texts){
    if(!t.isActiveAndEnabled||string.IsNullOrWhiteSpace(t.text))continue;var r=t.rectTransform.rect;var g=new TextGenerator();var settings=t.GetGenerationSettings(r.size);settings.resizeTextForBestFit=false;settings.fontSize=t.resizeTextForBestFit?t.resizeTextMinSize:t.fontSize;settings.verticalOverflow=VerticalWrapMode.Overflow;
    float height=g.GetPreferredHeight(t.text,settings)/t.pixelsPerUnit;Check(height<=r.height+2,"Text fits at minimum size: "+t.name+" / "+GameLocale.Codes[GameLocale.Current]+" "+Screen.width+"x"+Screen.height+" needs "+height+" has "+r.height);
    t.font.RequestCharactersInTexture(t.text,settings.fontSize,t.fontStyle);foreach(char c in t.text)if(!char.IsWhiteSpace(c)){CharacterInfo info;Check(t.font.GetCharacterInfo(c,out info,settings.fontSize,t.fontStyle),"Missing glyph "+((int)c)+" in "+t.name);}
   }}
  static LevelData WinningFixture(){var cells=new List<Cell>();var gems=new List<GemCell>();var spawn=new List<Cell>();int[,] colors={{0,1,0},{0,0,2},{2,1,2}};for(int y=0;y<3;y++)for(int x=0;x<3;x++){cells.Add(new Cell(x,y));if(y==2)spawn.Add(new Cell(x,y));if(x==0&&y==1)continue;gems.Add(new GemCell{x=x,y=y,color=colors[y,x]});}return new LevelData{id="no-moves-final-win",globalLevel=1,columns=3,rows=3,movesProposal=1,tileSeed=1,activeCells=cells.ToArray(),spawnPoints=spawn.ToArray(),initialTiles=gems.ToArray(),obstacles=new[]{new ObstacleCell{x=0,y=1,family="crate",hp=1}},goals=new[]{new Goal{family="crate",count=1}},activeColors=new[]{0,1,2,3,4,5}};}
  void Capture(string name){
   var canvases=UnityEngine.Object.FindObjectsByType<Canvas>(FindObjectsSortMode.InstanceID).Where(c=>c.isActiveAndEnabled&&c.renderMode==RenderMode.ScreenSpaceOverlay).ToArray();var cameras=canvases.Select(c=>c.worldCamera).ToArray();var distances=canvases.Select(c=>c.planeDistance).ToArray();var node=new GameObject("No Moves native UGUI camera");node.transform.position=new Vector3(-10000,0,-10);var camera=node.AddComponent<Camera>();camera.clearFlags=CameraClearFlags.Depth;var target=RenderTexture.GetTemporary(Screen.width,Screen.height,24,RenderTextureFormat.ARGB32);var previous=RenderTexture.active;Texture2D image=null;
   try{var board=game?Field<Camera>(game,"view"):null;if(board){var old=board.targetTexture;board.targetTexture=target;board.Render();board.targetTexture=old;}else{camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=Color.black;}
    camera.targetTexture=target;foreach(var c in canvases){c.renderMode=RenderMode.ScreenSpaceCamera;c.worldCamera=camera;c.planeDistance=1;}Canvas.ForceUpdateCanvases();camera.Render();RenderTexture.active=target;image=new Texture2D(target.width,target.height,TextureFormat.RGBA32,false);image.ReadPixels(new Rect(0,0,target.width,target.height),0,0);image.Apply();File.WriteAllBytes(Path.Combine(Output,name),image.EncodeToPNG());report.frames.Add(name);
   }finally{for(int i=0;i<canvases.Length;i++){canvases[i].renderMode=RenderMode.ScreenSpaceOverlay;canvases[i].worldCamera=cameras[i];canvases[i].planeDistance=distances[i];}RenderTexture.active=previous;RenderTexture.ReleaseTemporary(target);if(image)Destroy(image);Destroy(node);Canvas.ForceUpdateCanvases();}
  }
  void Finish(Exception e){if(report.status!="RUNNING")return;report.status=e==null?"PASS_NO_MOVES_NATIVE_PLAY":"FAIL_NO_MOVES_NATIVE_PLAY";report.error=e==null?"":e.ToString();Application.logMessageReceived-=Log;File.WriteAllText(Path.Combine(Output,"NativePlay.json"),JsonUtility.ToJson(report,true));GameLocale.Select(oldLocale);Finished?.Invoke(e==null?0:1);}
 }
}
#endif

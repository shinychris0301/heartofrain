using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.Celebrations;
using HeartOfTheRain.App.Home;
using System;using System.Collections.Generic;using UnityEngine;using UnityEngine.UI;using UnityEngine.EventSystems;using HeartOfTheRain.M46;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem.UI;
#endif
namespace HeartOfTheRain.M47 {
 public sealed class GameplayHUD:MonoBehaviour {
  public GameplayUIAssets assets;public GameplayFeedback feedback;
  public Action<int> BoosterPressed;public Action<bool> PauseChanged;public Action RetryPressed,ContinuePressed;
  public Action SettingsRequested,CloseExternalSettings;public Func<bool> ExternalSettingsVisible,ExternalResultVisible;public Func<bool,int,bool> ResultRequested;
  VictoryCelebrationPlayer standaloneVictory;Action lossRetry;string lossTitle;
  public bool LossPending=>lossRetry!=null;public string LossTitle=>lossTitle;
  public string ObstacleIntroductionFamily{get;private set;}
  public bool ObstacleIntroductionVisible=>modal!=null&&!string.IsNullOrEmpty(ObstacleIntroductionFamily);
  HeartOfTheRain.App.PreLevel.ObstacleIntroductionClock introductionClock;Action introductionFinished;bool applicationPaused,applicationFocused=true;
  public double ObstacleIntroductionFullyVisibleSeconds=>introductionClock?.FullyVisibleSeconds??0;
  public double LastObstacleIntroductionVisibleSeconds{get;private set;}
  public string LastObstacleIntroductionFamily{get;private set;}
#if UNITY_EDITOR
  // Explicit simulated foreground for offscreen UI fixtures only; absent on devices.
  [NonSerialized]public bool? VerificationObstacleForeground;
#endif
  bool IntroductionForeground{
   get{
#if UNITY_EDITOR
    if(VerificationObstacleForeground.HasValue)return VerificationObstacleForeground.Value;
#endif
    return applicationFocused&&!applicationPaused;
   }
  }

 public bool IsBlocking=>(standaloneVictory&&standaloneVictory.IsVisible)||modal!=null||(ExternalSettingsVisible!=null&&ExternalSettingsVisible())||(ExternalResultVisible!=null&&ExternalResultVisible());public float Height{get;private set;}=1280;
  Canvas canvas;CanvasScaler scaler;RectTransform safe,modal,header;Text moves,helper;Image movesPanel;readonly List<GameObject> goalObjects=new List<GameObject>();
  readonly Image[] boosterFrames=new Image[4];readonly Text[] counts=new Text[4];readonly Button[] boosterButtons=new Button[4];
  readonly string[] boosterIds={"boosterHammer","boosterAxe","boosterRam","boosterAtlas"};readonly string[] boosterNames={"Hammer","Axe","Ram","Atlas"};
  int selected=-1;float modalOpened;Rect previousSafe;bool first=true;RectTransform bar;Button settings;
  string[] goalFamilies=new string[0];int[] previousGoalCounts=new int[0];readonly int[] previousStock={-1,-1,-1,-1};int previousMoves=-1,previousLocale=-1;string previousHint;int previousSelection=-2;
  readonly Dictionary<string,RectTransform> goalRects=new Dictionary<string,RectTransform>();
  readonly List<float> goalPulse=new List<float>();
  readonly List<Image> collectionImages=new List<Image>();int collectionCount;
  public void BeginCollections(){collectionCount=0;}
  public void DrawCollection(Sprite sprite,Vector2 screen,Vector2 pixelSize,float angle,Color color){
   if(collectionCount>=collectionImages.Count){var go=GO("Goal collection",safe);var im=go.AddComponent<Image>();im.raycastTarget=false;collectionImages.Add(im);}
   var image=collectionImages[collectionCount++];image.enabled=!IsBlocking;image.sprite=sprite;image.color=color;
   var rect=image.rectTransform;rect.anchorMin=rect.anchorMax=new Vector2(.5f,.5f);rect.pivot=new Vector2(.5f,.5f);
   Vector2 local;RectTransformUtility.ScreenPointToLocalPointInRectangle(safe,screen,null,out local);rect.localPosition=new Vector3(local.x,local.y,0);rect.sizeDelta=pixelSize/canvas.scaleFactor;rect.localRotation=Quaternion.Euler(0,0,angle);rect.SetAsLastSibling();
  }
  public void EndCollections(){for(int i=collectionCount;i<collectionImages.Count;i++){collectionImages[i].enabled=false;collectionImages[i].sprite=null;}}
  readonly Color ink=new Color(32f/255f,48f/255f,68f/255f),cream=new Color(1,.96f,.84f);List<Text> goalCounters=new List<Text>();
  GameObject GO(string n,Transform parent){var o=new GameObject(n,typeof(RectTransform));o.transform.SetParent(parent,false);return o;}
  RectTransform Place(GameObject o,float x,float y,float w,float h){var t=(RectTransform)o.transform;t.anchorMin=t.anchorMax=new Vector2(0,1);t.pivot=new Vector2(0,1);t.anchoredPosition=new Vector2(x,-y);t.sizeDelta=new Vector2(w,h);return t;}
  Image Picture(Transform p,string id,float x,float y,float w,float h,bool slice=false){if(id=="Button_Settings")slice=false;var o=GO(id,p);Place(o,x,y,w,h);var v=o.AddComponent<Image>();v.sprite=assets.Get(id);v.type=slice?Image.Type.Sliced:Image.Type.Simple;v.preserveAspect=!slice;v.raycastTarget=false;return v;}
  Text Label(Transform p,string text,float x,float y,float w,float h,int size,Color color,bool bold=true){var o=GO("Text",p);Place(o,x,y,w,h);var t=o.AddComponent<Text>();t.text=GameLocale.T(text);t.font=bold?assets.bold:assets.regular;t.fontSize=size;t.color=color;t.alignment=TextAnchor.MiddleCenter;t.horizontalOverflow=HorizontalWrapMode.Wrap;t.verticalOverflow=VerticalWrapMode.Truncate;t.raycastTarget=false;t.resizeTextForBestFit=true;t.resizeTextMinSize=Math.Max(10,size/2);t.resizeTextMaxSize=size;return t;}
  Button Click(Transform p,string id,string title,float x,float y,float w,float h,Action action){var im=Picture(p,id,x,y,w,h,true);im.raycastTarget=true;var b=im.gameObject.AddComponent<Button>();b.targetGraphic=im;var colors=b.colors;colors.pressedColor=new Color(.86f,.83f,.78f);colors.highlightedColor=Color.white;colors.disabledColor=new Color(.65f,.70f,.72f);b.colors=colors;b.onClick.AddListener(()=>{feedback.Play("ui_tap",.65f);action?.Invoke();});if(title!=null)Label(im.transform,title,5,0,w-10,h-8,26,cream);return b;}
  public void Build(){
   if(FindFirstObjectByType<EventSystem>()==null){var es=new GameObject("Gameplay input",typeof(EventSystem));es.transform.SetParent(transform,false);
#if ENABLE_INPUT_SYSTEM
    es.AddComponent<InputSystemUIInputModule>();
#else
    es.AddComponent<StandaloneInputModule>();
#endif
   }
   var c=GO("Gameplay Canvas",transform);canvas=c.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=100;scaler=c.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;c.AddComponent<GraphicRaycaster>();
   safe=Place(GO("Safe area",c.transform),0,0,720,1280);Fit();
   header=Place(GO("Header container",safe),30,38,660,192);
   Picture(header,"Panel_Header",0,0,660,192);
   movesPanel=Picture(header,"Panel_Moves",12,44,112,120,true);Picture(header,"Label_Tab",20,28,96,34,true);Label(header,"Moves",22,27,92,34,22,Color.white);moves=Label(header,"26",18,67,100,84,58,ink);
   Picture(header,"Panel_Goals",136,44,324,122,true);Picture(header,"Label_Tab",234,28,128,34,true);Label(header,"Targets",236,27,124,34,22,Color.white);
   var avatar=Picture(header,"Avatar_Mask",472,6,180,180);var avatarMask=avatar.gameObject.AddComponent<Mask>();avatarMask.showMaskGraphic=false;
   Picture(avatar.transform,"Avatar_Ivan",-200,0,512,768);Picture(header,"Avatar_Frame",472,6,180,180);
   bar=Place(GO("Gameplay controls",safe),0,Height-166,720,166);
   for(int i=0;i<4;i++){int k=i;float x=26+i*140;var outline=Picture(bar,"Booster_Outline",x-7,-3,144,148);outline.name=boosterNames[i]+" outline";var b=Click(bar,"Booster_Default",null,x,4,126,126,()=>BoosterPressed?.Invoke(k));b.name=boosterNames[i]+" booster";boosterButtons[i]=b;boosterFrames[i]=b.GetComponent<Image>();float ix,iy,isz;HeartOfTheRain.App.Home.RewardIconLayout.ToolBounds(i,11,7,104,out ix,out iy,out isz);Picture(b.transform,boosterIds[i],ix,iy,isz,isz);Picture(b.transform,"Badge_Count",88,90,44,44);counts[i]=Label(b.transform,"3",90,89,40,44,25,Color.white);}
   settings=Click(bar,"Button_Settings",null,590,17,98,98,ShowPause);settings.name="Settings";Picture(settings.transform,"Icon_Settings",24,23,50,50);
   helper=Label(safe,"",34,6,652,28,19,Color.white);
  }
  public void Fit(){if(canvas==null)return;var s=Screen.safeArea;float scale=s.width/720f;scaler.scaleFactor=scale;Height=s.height/scale;safe.anchoredPosition=new Vector2(s.x/scale,-(Screen.height-s.yMax)/scale);safe.sizeDelta=new Vector2(720,Height);if(bar!=null)bar.anchoredPosition=new Vector2(0,-(Height-166));if(modal!=null){modal.sizeDelta=new Vector2(720,Height);var shade=modal.Find("Full display modal shade");if(shade)PageBackdrop90.Fill(shade.GetComponent<Image>(),canvas);var panel=modal.Find("Dialog") as RectTransform;if(panel!=null)panel.anchoredPosition=new Vector2(80,-(Height-584)/2);}}
  void Update(){if(Screen.safeArea!=previousSafe||first){previousSafe=Screen.safeArea;first=false;Fit();}
   for(int i=0;i<goalCounters.Count;i++){float t=Time.unscaledTime-goalPulse[i];goalCounters[i].rectTransform.localScale=Vector3.one*(1+(t>=0&&t<.24f?.16f*Mathf.Sin(t/.24f*Mathf.PI):0));}
   if(modal!=null){
    if(introductionClock!=null)introductionClock.Sample(Time.realtimeSinceStartupAsDouble,IntroductionForeground&&canvas.isActiveAndEnabled&&modal.gameObject.activeInHierarchy);
    var panel=modal.Find("Dialog") as RectTransform;if(panel!=null){float t=introductionClock!=null?introductionClock.RevealProgress:Mathf.Clamp01((Time.unscaledTime-modalOpened)/.18f);panel.localScale=Vector3.one*(.96f+.04f*(1-Mathf.Pow(1-t,3)));}
    if(introductionClock!=null&&introductionClock.Finished){var complete=introductionFinished;LastObstacleIntroductionVisibleSeconds=introductionClock.FullyVisibleSeconds;LastObstacleIntroductionFamily=ObstacleIntroductionFamily;Close(false);complete?.Invoke();}
   }
  }
  public void UpdateState(int number,int moveCount,Goal[] goals,BoosterInventory stock,int selection,bool busy,string hint){
   if(previousMoves!=moveCount){moves.text=moveCount.ToString();moves.color=moveCount<=5?new Color(.65f,.325f,.133f):ink;previousMoves=moveCount;}if(previousHint!=hint||previousLocale!=GameLocale.Revision){helper.text=GameLocale.T(hint??"");previousHint=hint;previousLocale=GameLocale.Revision;}selected=selection;
   bool changed=goalFamilies.Length!=goals.Length;for(int i=0;!changed&&i<goals.Length;i++)changed=goalFamilies[i]!=goals[i].family;
   if(changed){foreach(var go in goalObjects){go.SetActive(false);Destroy(go);}goalObjects.Clear();goalCounters.Clear();goalPulse.Clear();goalRects.Clear();goalFamilies=new string[goals.Length];previousGoalCounts=new int[goals.Length];
    float span=Math.Min(296,goals.Length*104),w=span/Math.Max(1,goals.Length);for(int i=0;i<goals.Length;i++){
     goalFamilies[i]=goals[i].family;previousGoalCounts[i]=-1;var root=GO("Goal "+goals[i].family,header);Place(root,298-span/2+i*w,GoalIconLayout106.GoalTop,w,GoalIconLayout106.GoalHeight);goalObjects.Add(root);goalRects[goals[i].family]=(RectTransform)root.transform;
     var slot=GO("Objective artwork slot",root.transform);Place(slot,(w-GoalIconLayout106.SlotSize)/2,0,GoalIconLayout106.SlotSize,GoalIconLayout106.SlotSize);slot.AddComponent<RectMask2D>();string id=GoalSprite(goals[i].family);var icon=Picture(slot.transform,id,0,0,GoalIconLayout106.SlotSize,GoalIconLayout106.SlotSize);GoalIconLayout106.Fit(icon,id);
     float counterWidth=GoalIconLayout106.CounterWidth(w);var counter=Label(root.transform,"",(w-counterWidth)/2,GoalIconLayout106.CounterTop,counterWidth,GoalIconLayout106.CounterHeight,26,ink);var counterRect=counter.rectTransform;counterRect.pivot=new Vector2(.5f,.5f);counterRect.anchoredPosition=new Vector2(w/2,-GoalIconLayout106.CounterTop-GoalIconLayout106.CounterHeight/2);goalCounters.Add(counter);goalPulse.Add(-10);
    }}

   for(int i=0;i<goals.Length;i++){if(previousGoalCounts[i]==goals[i].count)continue;if(previousGoalCounts[i]>=0){goalPulse[i]=Time.unscaledTime;if(goals[i].count==0)feedback.Play("goal_complete",.65f,"success");}previousGoalCounts[i]=goals[i].count;goalCounters[i].text=goals[i].count==0?"✓":goals[i].count.ToString();goalCounters[i].color=goals[i].count==0?new Color(.13f,.51f,.43f):ink;}
   for(int i=0;i<4;i++){int n=stock.Count((BoosterKind)i);if(previousStock[i]!=n||previousSelection!=selection){counts[i].text=n.ToString();boosterFrames[i].sprite=assets.Get(n<=0?"Booster_Disabled":selection==i?"Booster_Selected":"Booster_Default");previousStock[i]=n;}boosterButtons[i].interactable=!busy&&n>0;}previousSelection=selection;
  }
  public static string GoalSprite(string family){switch(family){case "crystal":return "crystalIcon";case "pod":return "waterSpirit";case "rainlight":return "rainlight";case "crate":return "crate_1";case "moss":return "moss_1";case "stone":return "stone_1";case "pail":return "pail_Full";case "case":return "case_1";default:return "gate_1";}}
  public bool TryGoalScreenPoint(string family,out Vector2 point){
   RectTransform rect;point=Vector2.zero;if(!goalRects.TryGetValue(family,out rect))return false;point=RectTransformUtility.WorldToScreenPoint(null,rect.TransformPoint(new Vector3(rect.rect.width*.5f,-GoalIconLayout106.SlotSize*.5f,0)));return true;
  }
  RectTransform Dialog(string title,string body){Close(false);modalOpened=Time.unscaledTime;modal=Place(GO("Modal",safe),0,0,720,Height);var shield=modal.gameObject.AddComponent<Image>();shield.color=Color.clear;shield.raycastTarget=true;var dim=GO("Full display modal shade",modal).AddComponent<Image>();dim.color=new Color(.015f,.07f,.10f,.78f);PageBackdrop90.Fill(dim,canvas);var panel=Picture(modal,"Panel_Modal",80,(Height-584)/2,560,584,true);panel.name="Dialog";Label(panel.transform,title,34,30,492,75,32,ink);Label(panel.transform,body,48,125,464,88,22,ink,false);return panel.rectTransform;}
  public void ShowPause(){var owner=GetComponent<GameplayScreen>();if(owner&&owner.SettingsBlocked!=null&&owner.SettingsBlocked())return;if(ExternalResultVisible!=null&&ExternalResultVisible())return;if(SettingsRequested!=null){SettingsRequested();return;}PauseChanged?.Invoke(true);feedback.Play("ui_open",.7f);var p=Dialog("Take a breath","Your board will be right here.");
   var sound=Click(p,feedback.soundEnabled?"Button_Teal":"Button_Disabled",null,50,230,220,92,null);Picture(sound.transform,"Icon_Sound",18,21,44,44);var soundText=Label(sound.transform,feedback.soundEnabled?"Sound\nOn":"Sound\nOff",66,0,140,80,20,cream);sound.onClick.AddListener(()=>{feedback.soundEnabled=!feedback.soundEnabled;soundText.text=GameLocale.T(feedback.soundEnabled?"Sound\nOn":"Sound\nOff");sound.GetComponent<Image>().sprite=assets.Get(feedback.soundEnabled?"Button_Teal":"Button_Disabled");});
   var touch=Click(p,feedback.hapticsEnabled?"Button_Teal":"Button_Disabled",null,290,230,220,92,null);Picture(touch.transform,"Icon_Haptic",18,21,44,44);var touchText=Label(touch.transform,feedback.hapticsEnabled?"Haptics\nOn":"Haptics\nOff",66,0,140,80,20,cream);touch.onClick.AddListener(()=>{feedback.hapticsEnabled=!feedback.hapticsEnabled;touchText.text=GameLocale.T(feedback.hapticsEnabled?"Haptics\nOn":"Haptics\nOff");touch.GetComponent<Image>().sprite=assets.Get(feedback.hapticsEnabled?"Button_Teal":"Button_Disabled");});
   Click(p,"Button_Teal","Resume",64,342,432,94,()=>Close(true));if(RetryPressed!=null)Click(p,"Button_Burgundy","Restart level",64,446,432,88,()=>{Close(true);RetryPressed?.Invoke();});
  }
  public void ShowIntro(int n,Goal[] goals,string title=null,string instruction=null){PauseChanged?.Invoke(true);var p=Dialog(string.IsNullOrEmpty(title)?"Clear these targets":title,string.IsNullOrEmpty(instruction)?"Clear the targets to restore the village.":instruction);float span=Math.Min(424,goals.Length*108),w=span/Math.Max(1,goals.Length);for(int i=0;i<goals.Length;i++){Picture(p,GoalSprite(goals[i].family),280-span/2+i*w+(w-72)/2,249,72,72);Label(p,goals[i].count.ToString(),280-span/2+i*w,329,w,42,30,ink);}Click(p,"Button_Teal","Play",64,446,432,94,()=>Close(true));}
  public void ShowObstacleIntroduction(HeartOfTheRain.App.PreLevel.ObstacleIntroductionCard card,Action next,Sprite obstacleSprite=null){
   if(card==null)throw new ArgumentNullException(nameof(card));
   PauseChanged?.Invoke(true);var p=Dialog(card.Title(GameLocale.Current),card.Instruction(GameLocale.Current));
   ObstacleIntroductionFamily=card.Family;
   var artwork=Picture(p,card.ArtKey,208,240,144,144);if(obstacleSprite)artwork.sprite=obstacleSprite;
   applicationFocused=Application.isFocused;
   introductionClock=new HeartOfTheRain.App.PreLevel.ObstacleIntroductionClock();introductionClock.Reset(Time.realtimeSinceStartupAsDouble,IntroductionForeground);
   introductionFinished=next;if(EventSystem.current)EventSystem.current.SetSelectedGameObject(null);
  }
  void OnApplicationPause(bool paused){introductionClock?.Sample(Time.realtimeSinceStartupAsDouble,IntroductionForeground);applicationPaused=paused;introductionClock?.Sample(Time.realtimeSinceStartupAsDouble,IntroductionForeground);}
  void OnApplicationFocus(bool focused){introductionClock?.Sample(Time.realtimeSinceStartupAsDouble,IntroductionForeground);applicationFocused=focused;introductionClock?.Sample(Time.realtimeSinceStartupAsDouble,IntroductionForeground);}
  void OnDisable(){introductionClock?.Sample(Time.realtimeSinceStartupAsDouble,false);}
  void OnEnable(){introductionClock?.Sample(Time.realtimeSinceStartupAsDouble,IntroductionForeground);}
  public void ShowResult(bool won,int number,string status=null){
   if(ResultRequested!=null&&ResultRequested(won,number))return;
   if(standaloneVictory&&standaloneVictory.IsVisible)return;
   // Without a retry owner this dialog could only offer an unsettled reload.
   if(!won){if(RetryPressed!=null)ShowLoss(LossTitleFor(status),()=>RetryPressed?.Invoke());return;}
   PauseChanged?.Invoke(true);
   if(!VictoryCelebrationPlayer.TryPlayStandalone(this,number,()=>{Close(true);ContinuePressed?.Invoke();})){Close(true);ContinuePressed?.Invoke();}
   standaloneVictory=GetComponent<VictoryCelebrationPlayer>();
  }
  public static string LossTitleFor(string status)=>status=="No legal moves"?"No moves left":"Out of moves";
  // Loss beat (owner decision, 22 October 2026): the approved dialog shows
  // while the cue plays; whoever owns the outcome acts on acknowledgement.
  public void ShowLoss(string title,Action acknowledge){
   if(standaloneVictory&&standaloneVictory.IsVisible)return;
   PauseChanged?.Invoke(true);feedback.Play("level_lose",1);lossRetry=acknowledge;lossTitle=title;
   var p=Dialog(title,"Try a new route through the obstacles.");Picture(p,"Button_Settings",212,236,136,136,true);Picture(p,"Icon_Retry",239,258,82,82);
   Click(p,"Button_Teal","Try again",64,446,432,94,AcknowledgeLoss);
  }
  // The dialog button and verification share this path; the board stays
  // paused so settlement or a retry load decides what resumes.
  public void AcknowledgeLoss(){var acknowledge=lossRetry;if(acknowledge==null)return;lossRetry=null;lossTitle=null;Close(false);acknowledge();}

  public void ShowTutorial(){PauseChanged?.Invoke(true);var p=Dialog("Your first match","Swap two neighboring tiles to line up three of the same kind.");Picture(p,"Button_Settings",212,236,136,136,true);Picture(p,"Icon_Hand",239,258,82,82);Click(p,"Button_Teal","Got it",64,446,432,94,()=>Close(true));}
  public void ShowExitConfirmation(Action cancel,Action confirm){PauseChanged?.Invoke(true);var p=Dialog("Exit level?","If you exit now, you will lose a life.");Picture(p,"Icon_Retry",238,230,84,84);Click(p,"Button_Teal","Keep playing",64,342,432,94,()=>{Close(false);cancel?.Invoke();});Click(p,"Button_Burgundy","Exit",64,446,432,88,()=>{Close(false);confirm?.Invoke();});}
  public void Close(bool resume){introductionClock=null;introductionFinished=null;ObstacleIntroductionFamily=null;CloseExternalSettings?.Invoke();if(modal!=null){modal.gameObject.SetActive(false);Destroy(modal.gameObject);modal=null;}if(resume)PauseChanged?.Invoke(false);}
 }
}

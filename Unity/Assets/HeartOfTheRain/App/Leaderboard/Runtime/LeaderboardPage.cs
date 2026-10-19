using System;using System.Collections.Generic;using UnityEngine;using UnityEngine.UI;using UnityEngine.EventSystems;
using HeartOfTheRain.App.Home;using HeartOfTheRain.App.PreLevel;using HeartOfTheRain.App.Journey;
namespace HeartOfTheRain.App.Leaderboard
{
 [DisallowMultipleComponent] public sealed class LeaderboardPage:MonoBehaviour
 {
  public HomePage home;public LeaderboardAssets assets;public bool openOnStart;
  LeaderboardSession session;Canvas canvas;CanvasScaler scaler;CanvasGroup fade;RectTransform safe,chrome,viewport,content,overlay;ScrollRect scroll;
  Vector2Int lastSize;Rect lastSafe;float lastScale,opened;string draft="";bool submitSearch;
  readonly Dictionary<string,RectTransform> nodes=new Dictionary<string,RectTransform>();readonly Dictionary<string,float> positions=new Dictionary<string,float>();
  public bool IsVisible=>canvas&&canvas.gameObject.activeSelf;public LeaderboardSession ReviewSession=>session;
  string ScrollKey=>session.Tab+":"+session.Local+":"+session.Finding+":"+session.Query;
  void Start()
  {
   if(!home||!assets||!assets.demoData){Debug.LogError("Assign Leaderboard assets, Home and review fixture.",this);enabled=false;return;}
   home.Build();if(session==null)session=new LeaderboardSession(JsonUtility.FromJson<LeaderboardSnapshot>(assets.demoData.text));home.NavigationRequested.AddListener(Route);if(openOnStart)Show();
  }
  // Supply authenticated snapshots from a future ranking service. Non-demo snapshots
  // render read-only until real friend request/response handling is integrated.
  public void ApplySnapshot(LeaderboardSnapshot snapshot){if(session==null)session=new LeaderboardSession(snapshot);else session.ApplySnapshot(snapshot);positions.Clear();if(IsVisible)Reflow(1);}
  public void ResetDemo(){session=new LeaderboardSession(JsonUtility.FromJson<LeaderboardSnapshot>(assets.demoData.text));draft="";positions.Clear();if(IsVisible)Reflow(1);}
  void Route(string action){if(action=="leaderboard")Show();else if(action=="journey"||action=="home")Hide(false);}
  public void Show()
  {
   if(session==null)return;var flow=home.GetComponent<HomeLevelFlow>();var modal=home.GetComponent<PreLevelModal>();if((flow&&flow.Playing)||(modal&&modal.IsVisible))return;
   var journey=home.GetComponent<JourneyPage>();if(journey)journey.Hide(false);if(session.Data.isDemo)session.UpdateSelfLevel(home.State.currentLevel);
   Build();canvas.gameObject.SetActive(true);home.SetPresentation(false,false);opened=Time.unscaledTime;Reflow(positions.ContainsKey(ScrollKey)?positions[ScrollKey]:1);Focus("tab-"+(int)session.Tab);
  }
  public void Hide(bool showHome=true)
  {
   if(!IsVisible)return;positions[ScrollKey]=scroll.verticalNormalizedPosition;session.CancelRemove();canvas.gameObject.SetActive(false);
   if(showHome){home.SetPresentation(true,true);if(EventSystem.current)foreach(var c in home.GetComponentsInChildren<HomeControlLabel>())if(c.action=="leaderboard"){var b=c.GetComponent<Button>();if(b&&b.interactable&&b.gameObject.activeInHierarchy){EventSystem.current.SetSelectedGameObject(b.gameObject);break;}}}
  }
  public void Request(string action)
  {
   if(!IsVisible||string.IsNullOrEmpty(action)||action=="disabled")return;
   if(session.ConfirmRemoveId.Length>0&&action!="cancel-remove"&&action!="confirm-remove")return;
   submitSearch=false;positions[ScrollKey]=scroll.verticalNormalizedPosition;float pos=scroll.verticalNormalizedPosition;string focus="";
   if(action=="home"){Hide();return;}if(action=="journey"||action=="teams"||action=="shop"){Hide(false);home.NavigationRequested.Invoke(action);return;}if(action=="leaderboard")return;
   if(action.StartsWith("tab:",StringComparison.Ordinal)){int n;if(!int.TryParse(action.Substring(4),out n)||n<0||n>2)return;session.Select((LeaderboardTab)n);pos=positions.ContainsKey(ScrollKey)?positions[ScrollKey]:1;focus="tab-"+n;}
   else if(action=="world"||action=="local"){session.SetLocal(action=="local");pos=positions.ContainsKey(ScrollKey)?positions[ScrollKey]:1;focus=action;}
   else if(action=="list"||action=="find"){session.SetFinding(action=="find");draft="";pos=1;focus=action=="find"?"search":"friends-list";}
   else if(action=="search"){if(session.Tab!=LeaderboardTab.Friends||!session.Finding)return;session.Search(draft);pos=1;focus="search-submit";}
   else if(action.StartsWith("add:",StringComparison.Ordinal)){string id=action.Substring(4);session.Add(id);focus="friend-"+id+"-action";}
   else if(action.StartsWith("cancel-request:",StringComparison.Ordinal)){string id=action.Substring(15);session.CancelRequest(id);focus="friend-"+id+"-action";}
   else if(action.StartsWith("remove:",StringComparison.Ordinal)){if(session.AskRemove(action.Substring(7)))focus="confirm-cancel";}
   else if(action=="cancel-remove"){string id=session.ConfirmRemoveId;session.CancelRemove();focus="friend-"+id+"-action";}
   else if(action=="confirm-remove"){session.ConfirmRemove();focus="friends-list";}
   else return;
   Reflow(pos);if(focus.Length>0)Focus(focus);
  }
  void Build()
  {
   if(canvas)return;var root=Rect("Leaderboard Canvas",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=60;
#if UNITY_2022_3_OR_NEWER
   canvas.vertexColorAlwaysGammaSpace=true;
#endif
   scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;root.gameObject.AddComponent<GraphicRaycaster>();fade=root.gameObject.AddComponent<CanvasGroup>();
   var matte=Rect("Safe-area matte",root);matte.anchorMin=Vector2.zero;matte.anchorMax=Vector2.one;matte.sizeDelta=Vector2.zero;matte.gameObject.AddComponent<Image>().color=ColorOf("#071A30");
   safe=Rect("Leaderboard safe area",root);safe.gameObject.AddComponent<RectMask2D>();chrome=Rect("Fixed header and navigation",safe);
   viewport=Rect("Ranking viewport",safe);viewport.gameObject.AddComponent<Image>().color=Color.clear;viewport.gameObject.AddComponent<RectMask2D>();scroll=viewport.gameObject.AddComponent<ScrollRect>();scroll.viewport=viewport;scroll.horizontal=false;scroll.vertical=true;scroll.movementType=ScrollRect.MovementType.Clamped;scroll.scrollSensitivity=35;
   content=Rect("Ranking rows",viewport);scroll.content=content;overlay=Rect("Friend confirmation",safe);
  }
  void Update()
  {
   if(!IsVisible)return;if(lastSize.x!=Screen.width||lastSize.y!=Screen.height||lastSafe!=Screen.safeArea||Mathf.Abs(lastScale-home.CurrentUIScale)>.01f)Reflow(scroll.verticalNormalizedPosition);
   fade.alpha=home.State.reduceMotion?1:Mathf.Clamp01((Time.unscaledTime-opened)/.2f);
   if(submitSearch){submitSearch=false;Request("search");}
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
   bool back=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
   bool back=Input.GetKeyDown(KeyCode.Escape);
#endif
   if(back){if(session.ConfirmRemoveId.Length>0)Request("cancel-remove");else Hide();}
  }
  void Reflow(float position)
  {
   string focus="";if(EventSystem.current&&EventSystem.current.currentSelectedGameObject)focus=EventSystem.current.currentSelectedGameObject.name;
   foreach(var root in new[]{chrome,content,overlay})foreach(Transform t in root){t.gameObject.SetActive(false);Destroy(t.gameObject);}nodes.Clear();
   float scale=home.CurrentUIScale;scaler.scaleFactor=scale;canvas.scaleFactor=scale;Rect sr=Screen.safeArea;if(sr.width<=0||sr.height<=0)sr=new Rect(0,0,Screen.width,Screen.height);
   float w=sr.width/scale,h=sr.height/scale;Place(safe,sr.x/scale,(Screen.height-sr.yMax)/scale,w,h);var frame=LeaderboardLayout.Build(w,h,session);
   Place(chrome,0,0,frame.width,frame.height);Place(overlay,0,0,frame.width,frame.height);Place(viewport,0,frame.viewportY,frame.width,frame.viewportHeight);Place(content,0,0,frame.content.width,frame.content.height);
   Render(frame.chrome,chrome);Render(frame.content,content);Render(frame.overlay,overlay);
   bool modal=session.ConfirmRemoveId.Length>0;foreach(var section in new[]{chrome,viewport}){var group=section.GetComponent<CanvasGroup>();if(!group)group=section.gameObject.AddComponent<CanvasGroup>();group.interactable=!modal;group.blocksRaycasts=!modal;}scroll.enabled=!modal;
   MainNavigationFeedback.Bind(nodes,home.State.reduceMotion);
   Canvas.ForceUpdateCanvases();scroll.verticalNormalizedPosition=position;
   lastSize=new Vector2Int(Screen.width,Screen.height);lastSafe=Screen.safeArea;lastScale=scale;if(focus.Length>0)Focus(focus);
  }
  void Render(HomeFrame frame,RectTransform root)
  {
   foreach(var e in frame.elements)
   {
    var parent=string.IsNullOrEmpty(e.parent)?root:nodes[e.parent];var rt=Rect(e.id,parent);Place(rt,e.x,e.y,e.width,e.height);nodes[e.id]=rt;
    if(e.kind=="group")
    {
     if(string.IsNullOrEmpty(e.action))continue;var im=rt.gameObject.AddComponent<Image>();im.color=Color.clear;var b=rt.gameObject.AddComponent<Button>();b.targetGraphic=im;b.transition=Selectable.Transition.None;b.interactable=e.action!="disabled";string action=e.action;b.onClick.AddListener(()=>Request(action));var a=rt.gameObject.AddComponent<HomeControlLabel>();a.action=action;a.label=e.label;
    }
    else if(e.kind=="input")
    {
     var im=rt.gameObject.AddComponent<Image>();im.color=Color.clear;var field=rt.gameObject.AddComponent<InputField>();field.targetGraphic=im;field.characterLimit=32;field.lineType=InputField.LineType.SingleLine;
     var tr=Rect("Input text",rt);Place(tr,0,4,e.width,e.height-8);var t=tr.gameObject.AddComponent<Text>();t.font=assets.journey.home.regularFont;t.fontSize=e.fontSize;t.color=ColorOf(e.color);t.alignment=TextAnchor.MiddleLeft;t.supportRichText=false;t.raycastTarget=false;field.textComponent=t;
     var ph=Rect("Placeholder",rt);Place(ph,0,4,e.width,e.height-8);var pt=ph.gameObject.AddComponent<Text>();pt.font=t.font;pt.fontSize=e.fontSize;pt.color=ColorOf("#73818B");pt.alignment=TextAnchor.MiddleLeft;pt.text=e.label;pt.raycastTarget=false;field.placeholder=pt;
     field.text=draft;field.onValueChanged.AddListener(v=>draft=v);field.onEndEdit.AddListener(v=>{draft=v;submitSearch=true;});var label=rt.gameObject.AddComponent<HomeControlLabel>();label.action="search-input";label.label=e.label;
    }
    else if(e.kind=="text"||e.kind=="lefttext"||e.kind=="subtext"||e.kind=="leftsubtext")
    {
     var t=rt.gameObject.AddComponent<Text>();t.font=e.kind.Contains("subtext")?assets.journey.home.regularFont:assets.journey.home.boldFont;t.text=e.text;t.color=ColorOf(e.color);t.fontSize=e.fontSize;t.supportRichText=false;t.raycastTarget=false;t.alignment=e.kind.StartsWith("left",StringComparison.Ordinal)?TextAnchor.MiddleLeft:TextAnchor.MiddleCenter;t.horizontalOverflow=HorizontalWrapMode.Overflow;t.verticalOverflow=VerticalWrapMode.Truncate;
     while(t.fontSize>9&&t.preferredWidth>e.width)t.fontSize--;if(e.shadow){var sh=rt.gameObject.AddComponent<Shadow>();sh.effectColor=new Color(0,.02f,.05f,.8f);sh.effectDistance=new Vector2(0,-1);}
    }
    else if(e.kind=="cover")
    {var sp=assets.Find(e.asset);var im=rt.gameObject.AddComponent<RawImage>();im.texture=sp.texture;im.uvRect=JourneyPage.CoverUV(sp,e.width,e.height);im.color=ColorOf(e.color);im.raycastTarget=false;}
    else
    {
     var im=rt.gameObject.AddComponent<Image>();if(e.kind!="color")im.sprite=assets.Find(e.asset);im.color=ColorOf(e.color);im.type=e.sliced?Image.Type.Sliced:Image.Type.Simple;im.pixelsPerUnitMultiplier=e.sliced?4:1;im.preserveAspect=e.preserveAspect;im.raycastTarget=false;if(e.kind=="mask"){var m=rt.gameObject.AddComponent<Mask>();m.showMaskGraphic=false;}
    }
   }
   foreach(var e in frame.elements)if(!string.IsNullOrEmpty(e.action)&&e.action!="disabled"&&!e.id.StartsWith("nav-",StringComparison.Ordinal))
   {var gs=new List<Graphic>();foreach(var n in nodes)if(n.Key.StartsWith(e.id+"-",StringComparison.Ordinal)){var g=n.Value.GetComponent<Graphic>();if(g)gs.Add(g);}nodes[e.id].gameObject.AddComponent<PreLevelButtonFeedback>().Configure(gs.ToArray(),home.State.reduceMotion);}
  }
  void Focus(string id){RectTransform rt;if(!EventSystem.current||!nodes.TryGetValue(id,out rt))return;var s=rt.GetComponent<Selectable>();if(s&&s.interactable)EventSystem.current.SetSelectedGameObject(rt.gameObject);}
  static Color ColorOf(string value){Color c;return ColorUtility.TryParseHtmlString(value,out c)?c:Color.white;}
  static RectTransform Rect(string name,Transform parent){var g=new GameObject(name,typeof(RectTransform));g.transform.SetParent(parent,false);return (RectTransform)g.transform;}
  static void Place(RectTransform r,float x,float y,float w,float h){r.anchorMin=r.anchorMax=r.pivot=new Vector2(0,1);r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(w,h);}
  void OnDestroy(){if(home)home.NavigationRequested.RemoveListener(Route);}
 }
}

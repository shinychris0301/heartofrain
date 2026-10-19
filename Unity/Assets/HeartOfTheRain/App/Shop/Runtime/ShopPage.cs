using System;using System.Collections.Generic;using UnityEngine;using UnityEngine.UI;using UnityEngine.EventSystems;
using HeartOfTheRain.App.Home;using HeartOfTheRain.App.PreLevel;using HeartOfTheRain.App.Journey;using HeartOfTheRain.App.Leaderboard;using HeartOfTheRain.App.Teams;
namespace HeartOfTheRain.App.Shop
{
 [DisallowMultipleComponent] public sealed class ShopPage:MonoBehaviour
 {
  public HomePage home;public ShopAssets assets;public bool openOnStart;
  ShopSession session;Canvas canvas;CanvasScaler scaler;CanvasGroup fade;RectTransform safe,chrome,viewport,content,overlay;ScrollRect scroll;
  ShopCarouselInput carousel;RectTransform carouselViewport,carouselTrack;
  Vector2Int lastSize;Rect lastSafe;float lastScale,opened,savedPosition=1;string returnFocus="nav-shop";
  readonly Dictionary<string,RectTransform> nodes=new Dictionary<string,RectTransform>();
  public bool IsVisible=>canvas&&canvas.gameObject.activeSelf;public ShopSession ReviewSession=>session;
  Font BodyFont=>assets.teams.leaderboard.journey.home.regularFont;Font BoldFont=>assets.teams.leaderboard.journey.home.boldFont;
  void Start()
  {
   if(!home||!assets||!assets.catalog){Debug.LogError("Assign Shop assets, Home and catalogue.",this);enabled=false;return;}
   home.Build();if(session==null)session=new ShopSession(JsonUtility.FromJson<ShopCatalog>(assets.catalog.text));home.NavigationRequested.AddListener(Route);if(openOnStart)Show();
  }
  public void ApplyCatalog(ShopCatalog value){if(session==null)session=new ShopSession(value);else session.ApplyCatalog(value);savedPosition=1;if(IsVisible)Reflow(1);}
  public void ResetPreview(){ApplyCatalog(JsonUtility.FromJson<ShopCatalog>(assets.catalog.text));}
  void Route(string action){if(action=="shop"||action=="coins")Show();else if(action=="home"||action=="journey"||action=="leaderboard"||action=="teams"||action=="team")Hide(false);}
  public void Show()
  {
   if(session==null)return;var flow=home.GetComponent<HomeLevelFlow>();var modal=home.GetComponent<PreLevelModal>();if((flow&&flow.Playing)||(modal&&modal.IsVisible))return;
   var journey=home.GetComponent<JourneyPage>();if(journey)journey.Hide(false);var ranks=home.GetComponent<LeaderboardPage>();if(ranks)ranks.Hide(false);var team=home.GetComponent<TeamsPage>();if(team)team.Hide(false);
   home.ShowEvents(false);session.Close();Build();canvas.gameObject.SetActive(true);home.SetPresentation(false,false);opened=Time.unscaledTime;Reflow(savedPosition);Focus("nav-shop");
  }
  public void Hide(bool showHome=true)
  {
   if(!IsVisible)return;savedPosition=scroll.verticalNormalizedPosition;session.Close();canvas.gameObject.SetActive(false);
   if(showHome){home.SetPresentation(true,true);if(EventSystem.current)foreach(var c in home.GetComponentsInChildren<HomeControlLabel>())if(c.action=="shop"){var b=c.GetComponent<Button>();if(b&&b.interactable&&b.gameObject.activeInHierarchy){EventSystem.current.SetSelectedGameObject(b.gameObject);break;}}}
  }
  public void Request(string action)
  {
   if(!IsVisible||string.IsNullOrEmpty(action)||action=="disabled")return;
   if(session.Modal&&action!="close")return;
   if(action=="home"){Hide();return;}
   if(action=="journey"||action=="leaderboard"||action=="teams"){Hide(false);home.NavigationRequested.Invoke(action);return;}
   if(action=="shop")return;
   float position=scroll.verticalNormalizedPosition;string focus="";
   if(action.StartsWith("offer:",StringComparison.Ordinal)){string id=action.Substring(6);int special=Array.FindIndex(session.Specials,o=>o.id==id);if(special>=0){if(carousel&&carousel.Busy)return;session.SelectSpecial(special);}if(!session.Open(id))return;returnFocus="offer-"+id+"-view";focus="detail-close";}
   else if(action=="close"){session.Close();focus=returnFocus;}
   else return;
   Reflow(position);if(focus.Length>0)Focus(focus);
  }
  void Build()
  {
   if(canvas)return;var root=Rect("Shop Canvas",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=70;
#if UNITY_2022_3_OR_NEWER
   canvas.vertexColorAlwaysGammaSpace=true;
#endif
   scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;root.gameObject.AddComponent<GraphicRaycaster>();fade=root.gameObject.AddComponent<CanvasGroup>();
   var matte=Rect("Safe-area matte",root);matte.anchorMin=Vector2.zero;matte.anchorMax=Vector2.one;matte.sizeDelta=Vector2.zero;matte.gameObject.AddComponent<Image>().color=ColorOf("#102D44");
   safe=Rect("Shop safe area",root);safe.gameObject.AddComponent<RectMask2D>();chrome=Rect("Shop fixed header and navigation",safe);
   viewport=Rect("Shop viewport",safe);viewport.gameObject.AddComponent<Image>().color=Color.clear;viewport.gameObject.AddComponent<RectMask2D>();scroll=viewport.gameObject.AddComponent<ScrollRect>();scroll.viewport=viewport;scroll.horizontal=false;scroll.vertical=true;scroll.movementType=ScrollRect.MovementType.Clamped;scroll.scrollSensitivity=35;
   content=Rect("Shop offers",viewport);scroll.content=content;overlay=Rect("Offer details",safe);
  }
  void Update()
  {
   if(!IsVisible)return;if(lastSize.x!=Screen.width||lastSize.y!=Screen.height||lastSafe!=Screen.safeArea||Mathf.Abs(lastScale-home.CurrentUIScale)>.01f)Reflow(scroll.verticalNormalizedPosition);
   fade.alpha=home.State.reduceMotion?1:Mathf.Clamp01((Time.unscaledTime-opened)/.2f);
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
   bool back=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
   bool back=Input.GetKeyDown(KeyCode.Escape);
#endif
   if(back){if(session.Modal)Request("close");else Hide();}
  }
  void Reflow(float position)
  {
   string focus="";if(EventSystem.current&&EventSystem.current.currentSelectedGameObject)focus=EventSystem.current.currentSelectedGameObject.name;
   foreach(var root in new[]{chrome,content,overlay})foreach(Transform t in root){t.gameObject.SetActive(false);Destroy(t.gameObject);}nodes.Clear();
   float scale=home.CurrentUIScale;scaler.scaleFactor=scale;canvas.scaleFactor=scale;Rect sr=Screen.safeArea;if(sr.width<=0||sr.height<=0)sr=new Rect(0,0,Screen.width,Screen.height);
   float w=sr.width/scale,h=sr.height/scale;Place(safe,sr.x/scale,(Screen.height-sr.yMax)/scale,w,h);var frame=ShopLayout.Build(w,h,session,home.State.coins);
   Place(chrome,0,0,frame.width,frame.height);Place(overlay,0,0,frame.width,frame.height);Place(viewport,0,frame.viewportY,frame.width,frame.viewportHeight);Place(content,0,0,frame.content.width,frame.content.height);
   Render(frame.chrome,chrome);Render(frame.content,content);
   carousel=null;
   if(frame.specials.elements.Count>0)
   {
    carouselViewport=Rect("Special Offers swipe area",content);Place(carouselViewport,frame.carouselX,frame.carouselY,frame.carouselWidth,frame.carouselHeight);
    carouselViewport.gameObject.AddComponent<Image>().color=Color.clear;carouselViewport.gameObject.AddComponent<RectMask2D>();
    carouselTrack=Rect("Special Offers sliding track",carouselViewport);Place(carouselTrack,-frame.carouselOffset,0,frame.specials.width,frame.specials.height);Render(frame.specials,carouselTrack);
    carousel=carouselViewport.gameObject.AddComponent<ShopCarouselInput>();carousel.Configure(carouselTrack,scroll,frame.carouselStride,scale,session.Specials.Length,session.SpecialIndex,()=>!IsVisible||session.Modal,()=>home.State.reduceMotion,i=>{session.SelectSpecial(i);SetCarouselButtons();},FocusSpecial);
    foreach(var button in carouselTrack.GetComponentsInChildren<Button>()){var nav=button.navigation;nav.mode=Navigation.Mode.Vertical;button.navigation=nav;button.gameObject.AddComponent<ShopCarouselNavigation>().carousel=carousel;}
    SetCarouselButtons();
   }
   Render(frame.overlay,overlay);
   foreach(var section in new[]{chrome,viewport}){var group=section.GetComponent<CanvasGroup>();if(!group)group=section.gameObject.AddComponent<CanvasGroup>();group.interactable=!session.Modal;group.blocksRaycasts=!session.Modal;}scroll.enabled=!session.Modal;
   MainNavigationFeedback.Bind(nodes,home.State.reduceMotion);Canvas.ForceUpdateCanvases();scroll.verticalNormalizedPosition=position;
   lastSize=new Vector2Int(Screen.width,Screen.height);lastSafe=Screen.safeArea;lastScale=scale;if(focus.Length>0)Focus(focus);
  }
  void Render(HomeFrame frame,RectTransform root)
  {
   foreach(var e in frame.elements)
   {
    var parent=string.IsNullOrEmpty(e.parent)?root:nodes[e.parent];var rt=Rect(e.id,parent);Place(rt,e.x,e.y,e.width,e.height);nodes[e.id]=rt;
    if(e.kind=="group")
    {if(string.IsNullOrEmpty(e.action))continue;var im=rt.gameObject.AddComponent<Image>();im.color=Color.clear;var b=rt.gameObject.AddComponent<Button>();b.targetGraphic=im;b.transition=Selectable.Transition.None;b.interactable=e.action!="disabled";string action=e.action;b.onClick.AddListener(()=>Request(action));var label=rt.gameObject.AddComponent<HomeControlLabel>();label.action=action;label.label=e.label;}
    else if(e.kind=="text"||e.kind=="lefttext"||e.kind=="subtext"||e.kind=="leftsubtext")
    {var t=rt.gameObject.AddComponent<Text>();t.font=e.kind.Contains("subtext")?BodyFont:BoldFont;t.text=e.text;t.color=ColorOf(e.color);t.fontSize=e.fontSize;t.supportRichText=false;t.raycastTarget=false;t.alignment=e.kind.StartsWith("left",StringComparison.Ordinal)?TextAnchor.MiddleLeft:TextAnchor.MiddleCenter;t.horizontalOverflow=HorizontalWrapMode.Overflow;t.verticalOverflow=VerticalWrapMode.Truncate;while(t.fontSize>9&&t.preferredWidth>e.width)t.fontSize--;if(e.shadow){var shadow=rt.gameObject.AddComponent<Shadow>();shadow.effectColor=new Color(0,.035f,.08f,.9f);shadow.effectDistance=new Vector2(0,-1);}}
    else
    {var im=rt.gameObject.AddComponent<Image>();if(e.kind!="color")im.sprite=assets.Find(e.asset);im.color=ColorOf(e.color);im.type=e.sliced?Image.Type.Sliced:Image.Type.Simple;im.pixelsPerUnitMultiplier=e.sliced?4:1;im.preserveAspect=e.preserveAspect;im.raycastTarget=false;}
   }
   foreach(var e in frame.elements)if(!string.IsNullOrEmpty(e.action)&&e.action!="disabled"&&!e.id.StartsWith("nav-",StringComparison.Ordinal))
   {var gs=new List<Graphic>();foreach(var n in nodes)if(n.Key.StartsWith(e.id+"-",StringComparison.Ordinal)){var g=n.Value.GetComponent<Graphic>();if(g)gs.Add(g);}nodes[e.id].gameObject.AddComponent<PreLevelButtonFeedback>().Configure(gs.ToArray(),home.State.reduceMotion);}
  }
  void SetCarouselButtons()
  {
   string prefix="slide-"+(session.Specials.Length>1?session.SpecialIndex+1:0)+"-";
   foreach(var button in carouselTrack.GetComponentsInChildren<Button>())button.interactable=button.name.StartsWith(prefix,StringComparison.Ordinal);
  }
  void FocusSpecial(){if(session.CurrentSpecial!=null)Focus("slide-"+(session.Specials.Length>1?session.SpecialIndex+1:0)+"-offer-"+session.CurrentSpecial.id+"-view");}
  void Focus(string id){RectTransform rt;if(!EventSystem.current)return;if(!nodes.TryGetValue(id,out rt)){if(id.StartsWith("offer-",StringComparison.Ordinal)&&session.CurrentSpecial!=null&&id=="offer-"+session.CurrentSpecial.id+"-view")FocusSpecial();return;}var b=rt.GetComponent<Selectable>();if(b&&b.IsInteractable())EventSystem.current.SetSelectedGameObject(rt.gameObject);}
  static Color ColorOf(string value){Color c;return ColorUtility.TryParseHtmlString(value,out c)?c:Color.white;}
  static RectTransform Rect(string name,Transform parent){var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);return (RectTransform)go.transform;}
  static void Place(RectTransform rt,float x,float y,float w,float h){rt.anchorMin=rt.anchorMax=rt.pivot=new Vector2(0,1);rt.anchoredPosition=new Vector2(x,-y);rt.sizeDelta=new Vector2(w,h);}
  void OnDestroy(){if(home)home.NavigationRequested.RemoveListener(Route);}
 }
}

using System;using System.Collections;using System.Collections.Generic;
using UnityEngine;using UnityEngine.UI;using UnityEngine.EventSystems;
using HeartOfTheRain.App.Home;using HeartOfTheRain.App.PreLevel;using HeartOfTheRain.App.Settings;
using HeartOfTheRain.App.Journey;using HeartOfTheRain.App.Leaderboard;using HeartOfTheRain.App.Teams;using HeartOfTheRain.App.Shop;using HeartOfTheRain.M46;
namespace HeartOfTheRain.App.AppSettings
{
 [DisallowMultipleComponent] public sealed class AppSettingsPage:MonoBehaviour
 {
  sealed class Preferences:ISettingsStore
  {public int Read(string key,int fallback){return PlayerPrefs.GetInt(key,fallback);}public void Write(string key,int value){PlayerPrefs.SetInt(key,value);}public void Flush(){PlayerPrefs.Save();}}
  public HomePage home;public AppSettingsAssets assets;public bool openOnStart;
  AppSettingsSession session;Canvas canvas;CanvasScaler scaler;CanvasGroup fade;RectTransform safe,chrome,viewport,content,indicator;ScrollRect scroll;
  Vector2Int lastSize;Rect lastSafe;float lastScale,opened;string lastSection="inventory";
  readonly Dictionary<string,RectTransform> nodes=new Dictionary<string,RectTransform>();
  public bool IsVisible=>canvas&&canvas.gameObject.activeSelf;public AppSettingsSession ReviewSession=>session;
  void Start()
  {
   if(!home||!assets||!assets.shop||!assets.gameplaySettings||!assets.destinations){Debug.LogError("Assign Home and main Settings assets.",this);enabled=false;return;}
   home.Build();session=new AppSettingsSession(new Preferences(),JsonUtility.FromJson<AppSettingsLinks>(assets.destinations.text));home.NavigationRequested.AddListener(Route);
   if(openOnStart)StartCoroutine(OpenAfterStart());
  }
  IEnumerator OpenAfterStart(){yield return null;Show();}
  void Route(string action)
  {if(action=="settings")Show();else if(action=="home")Hide();else if(action=="journey"||action=="leaderboard"||action=="teams"||action=="team"||action=="shop"||action=="coins")Hide(false);}
  public void Show()
  {
   if(session==null)return;var flow=home.GetComponent<HomeLevelFlow>();if(!flow||!flow.CanOpenAppSettings)return;
   var journey=home.GetComponent<JourneyPage>();if(journey)journey.Hide(false);var ranks=home.GetComponent<LeaderboardPage>();if(ranks)ranks.Hide(false);var teams=home.GetComponent<TeamsPage>();if(teams)teams.Hide(false);var shop=home.GetComponent<ShopPage>();if(shop)shop.Hide(false);
   home.ShowEvents(false);var tools=new BoosterInventory();session.Open(flow.StartingStockSnapshot(),new[]{tools.hammer,tools.axe,tools.ram,tools.atlas});
   Build();canvas.gameObject.SetActive(true);home.SetPresentation(true,false);opened=Time.unscaledTime;Reflow(1);Focus("close");
  }
  public void Hide(bool showHome=true)
  {
   if(!IsVisible)return;canvas.gameObject.SetActive(false);
   if(showHome){home.SetPresentation(true,true);if(EventSystem.current)foreach(var label in home.GetComponentsInChildren<HomeControlLabel>())if(label.action=="settings"){var b=label.GetComponent<Button>();if(b&&b.IsInteractable()&&b.gameObject.activeInHierarchy){EventSystem.current.SetSelectedGameObject(b.gameObject);break;}}}
  }
  public void Request(string action)
  {
   if(!IsVisible||string.IsNullOrEmpty(action)||action=="disabled")return;
   if(action=="close"){Hide();return;}
   if(action=="shop"&&session.Page=="inventory"){Hide(false);home.NavigationRequested.Invoke("shop");return;}
   float position=scroll.verticalNormalizedPosition;string focus="";
   if(action=="back"){session.Back();position=1;focus=session.Page=="main"?lastSection:"return";}
   else if(action.StartsWith("toggle:",StringComparison.Ordinal)){if(!session.Toggle(action.Substring(7)))return;focus="preference-"+action.Substring(7);}
   else if(action.StartsWith("language:",StringComparison.Ordinal)){int i;if(!int.TryParse(action.Substring(9),out i)||!session.ChooseLanguage(i))return;focus="language-"+i;}
   else if(action.StartsWith("faq:",StringComparison.Ordinal)){int i;if(!int.TryParse(action.Substring(4),out i)||!session.ToggleHelp(i))return;focus="help-"+i;}
   else if(action.StartsWith("link:",StringComparison.Ordinal))
   {string url;if(session.TryLink(action.Substring(5),out url)){Application.OpenURL(url);return;}if(session.Page!="notice")return;position=1;focus="return";}
   else {if(session.Page!="main"||!session.Navigate(action))return;lastSection=action;position=1;focus="return";}
   Reflow(position);if(focus.Length>0)Focus(focus);
  }
  void Build()
  {
   if(canvas)return;var root=Rect("Main Settings Canvas",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=90;
#if UNITY_2022_3_OR_NEWER
   canvas.vertexColorAlwaysGammaSpace=true;
#endif
   scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;root.gameObject.AddComponent<GraphicRaycaster>();fade=root.gameObject.AddComponent<CanvasGroup>();
   var blocker=Rect("Full screen input shield",root);blocker.anchorMin=Vector2.zero;blocker.anchorMax=Vector2.one;blocker.sizeDelta=Vector2.zero;blocker.gameObject.AddComponent<Image>().color=Color.clear;
   safe=Rect("Settings safe area",root);safe.gameObject.AddComponent<RectMask2D>();chrome=Rect("Settings shell and controls",safe);
   viewport=Rect("Settings scroll viewport",safe);viewport.gameObject.AddComponent<Image>().color=Color.clear;viewport.gameObject.AddComponent<RectMask2D>();scroll=viewport.gameObject.AddComponent<ScrollRect>();scroll.viewport=viewport;scroll.horizontal=false;scroll.vertical=true;scroll.movementType=ScrollRect.MovementType.Clamped;scroll.scrollSensitivity=32;
   content=Rect("Settings content",viewport);scroll.content=content;indicator=Rect("Scroll position",safe);var mark=indicator.gameObject.AddComponent<Image>();mark.color=ColorOf("#607F9277");mark.raycastTarget=false;scroll.onValueChanged.AddListener(value=>UpdateIndicator());
  }
  void Update()
  {
   if(!IsVisible)return;if(lastSize.x!=Screen.width||lastSize.y!=Screen.height||lastSafe!=Screen.safeArea||Mathf.Abs(lastScale-home.CurrentUIScale)>.01f)Reflow(scroll.verticalNormalizedPosition);
   fade.alpha=home.State.reduceMotion?1:Mathf.Clamp01((Time.unscaledTime-opened)/.18f);
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
   bool back=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
   bool back=Input.GetKeyDown(KeyCode.Escape);
#endif
   if(back){if(session.Page=="main")Hide();else Request("back");}
  }
  void Reflow(float position)
  {
   string focus=EventSystem.current&&EventSystem.current.currentSelectedGameObject?EventSystem.current.currentSelectedGameObject.name:"";
   foreach(var root in new[]{chrome,content})foreach(Transform child in root){child.gameObject.SetActive(false);Destroy(child.gameObject);}nodes.Clear();
   Rect sr=Screen.safeArea;if(sr.width<=0||sr.height<=0)sr=new Rect(0,0,Screen.width,Screen.height);
   float scale=Mathf.Max(.25f,Mathf.Min(home.CurrentUIScale,Mathf.Min(sr.width/320f,sr.height/300f)));scaler.scaleFactor=scale;canvas.scaleFactor=scale;
   float w=sr.width/scale,h=sr.height/scale;Place(safe,sr.x/scale,(Screen.height-sr.yMax)/scale,w,h);var f=AppSettingsLayout.Build(w,h,session);
   Place(chrome,0,0,f.width,f.height);Place(viewport,f.viewportX,f.viewportY,f.viewportWidth,f.viewportHeight);Place(content,0,0,f.content.width,f.content.height);
   Render(f.chrome,chrome);Render(f.content,content);Canvas.ForceUpdateCanvases();scroll.verticalNormalizedPosition=position;UpdateIndicator();lastSize=new Vector2Int(Screen.width,Screen.height);lastSafe=Screen.safeArea;lastScale=home.CurrentUIScale;
   if(focus.Length>0)Focus(focus);
  }
  void Render(HomeFrame frame,RectTransform root)
  {
   foreach(var e in frame.elements)
   {
    var parent=string.IsNullOrEmpty(e.parent)?root:nodes[e.parent];var rt=Rect(e.id,parent);Place(rt,e.x,e.y,e.width,e.height);nodes[e.id]=rt;
    if(e.kind=="group")
    {if(string.IsNullOrEmpty(e.action))continue;var im=rt.gameObject.AddComponent<Image>();im.color=Color.clear;var b=rt.gameObject.AddComponent<Button>();b.targetGraphic=im;b.transition=Selectable.Transition.None;b.interactable=e.action!="disabled";string action=e.action;b.onClick.AddListener(()=>Request(action));var label=rt.gameObject.AddComponent<HomeControlLabel>();label.action=action;label.label=e.label;rt.gameObject.AddComponent<AppSettingsFocusScroll>().owner=this;}
    else if(e.kind=="text"||e.kind=="lefttext")
    {var t=rt.gameObject.AddComponent<Text>();t.font=assets.Home.boldFont;t.text=e.text;t.color=ColorOf(e.color);t.fontSize=e.fontSize;t.supportRichText=false;t.raycastTarget=false;t.alignment=e.kind=="lefttext"?TextAnchor.MiddleLeft:TextAnchor.MiddleCenter;t.horizontalOverflow=HorizontalWrapMode.Overflow;t.verticalOverflow=VerticalWrapMode.Truncate;while(t.fontSize>10&&t.preferredWidth>e.width)t.fontSize--;}
    else
    {var im=rt.gameObject.AddComponent<Image>();if(e.kind!="color")im.sprite=assets.Find(e.asset);im.color=ColorOf(e.color);im.type=e.sliced?Image.Type.Sliced:Image.Type.Simple;im.pixelsPerUnitMultiplier=e.sliced?4:1;im.preserveAspect=e.preserveAspect;im.raycastTarget=false;}
   }
   foreach(var e in frame.elements)if(!string.IsNullOrEmpty(e.action)&&e.action!="disabled")
   {var gs=new List<Graphic>();foreach(var n in nodes)if(n.Key.StartsWith(e.id+"-",StringComparison.Ordinal)){var g=n.Value.GetComponent<Graphic>();if(g)gs.Add(g);}nodes[e.id].gameObject.AddComponent<PreLevelButtonFeedback>().Configure(gs.ToArray(),home.State.reduceMotion);}
  }
  void UpdateIndicator()
  {if(!indicator)return;float vh=viewport.rect.height,ch=content.rect.height;indicator.gameObject.SetActive(ch>vh+.5f);if(ch<=vh)return;float hh=Mathf.Min(vh,Mathf.Max(22,vh*vh/ch));Place(indicator,viewport.anchoredPosition.x+viewport.rect.width+5,-viewport.anchoredPosition.y+(vh-hh)*(1-scroll.verticalNormalizedPosition),3,hh);}
  public void Reveal(RectTransform target)
  {
   if(!IsVisible||!target.IsChildOf(content))return;Canvas.ForceUpdateCanvases();var b=RectTransformUtility.CalculateRelativeRectTransformBounds(viewport,target);float delta=b.max.y>0?-b.max.y:b.min.y<-viewport.rect.height?-viewport.rect.height-b.min.y:0;
   var p=content.anchoredPosition;p.y=Mathf.Clamp(p.y+delta,0,Mathf.Max(0,content.rect.height-viewport.rect.height));content.anchoredPosition=p;
  }
  void Focus(string id){RectTransform rt;if(!EventSystem.current||!nodes.TryGetValue(id,out rt))return;var b=rt.GetComponent<Selectable>();if(b&&b.IsInteractable())EventSystem.current.SetSelectedGameObject(rt.gameObject);}
  static Color ColorOf(string value){Color c;return ColorUtility.TryParseHtmlString(value,out c)?c:Color.white;}
  static RectTransform Rect(string name,Transform parent){var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);return (RectTransform)go.transform;}
  static void Place(RectTransform rt,float x,float y,float w,float h){rt.anchorMin=rt.anchorMax=rt.pivot=new Vector2(0,1);rt.anchoredPosition=new Vector2(x,-y);rt.sizeDelta=new Vector2(w,h);}
  void OnDestroy(){if(home)home.NavigationRequested.RemoveListener(Route);}
 }
}

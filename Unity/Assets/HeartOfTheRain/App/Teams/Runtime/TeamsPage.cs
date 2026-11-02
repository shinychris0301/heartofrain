using System;using System.Collections.Generic;using UnityEngine;using UnityEngine.UI;using UnityEngine.EventSystems;
using HeartOfTheRain.App.Home;using HeartOfTheRain.App.PreLevel;using HeartOfTheRain.App.Journey;using HeartOfTheRain.App.Leaderboard;
namespace HeartOfTheRain.App.Teams
{
 [DisallowMultipleComponent] public sealed class TeamsPage:MonoBehaviour
 {
  public HomePage home;public TeamsAssets assets;public bool openOnStart;
  TeamsSession session;Canvas canvas;CanvasScaler scaler;CanvasGroup fade;RectTransform safe,chrome,viewport,content,overlay;ScrollRect scroll;
  Vector2Int lastSize;Rect lastSafe;float lastScale,opened;string draft="",countryDraft="";
  readonly Dictionary<string,RectTransform> nodes=new Dictionary<string,RectTransform>();readonly Dictionary<string,float> positions=new Dictionary<string,float>();
  HeartOfTheRain.App.OnlineSocial.OnlineTeamsPage82 online;
#if UNITY_EDITOR
  bool reviewSampleTeam;
#endif
  public bool IsVisible=>(online&&online.IsVisible)||(canvas&&canvas.gameObject.activeSelf);public TeamsSession ReviewSession=>session;
  bool ServerSelected=>home&&home.GetComponent<HeartOfTheRain.App.Profile.PlayerProfileHost>()&&home.GetComponent<HeartOfTheRain.App.Profile.PlayerProfileHost>().ServerSession;
  bool ReviewSelected {
   get {
#if UNITY_EDITOR
    return reviewSampleTeam||gameObject.scene.name=="M62_Teams_Review";
#else
    return false;
#endif
   }
  }
  bool UseOnline(){if(!ServerSelected&&ReviewSelected)return false;if(!online)online=gameObject.AddComponent<HeartOfTheRain.App.OnlineSocial.OnlineTeamsPage82>();if(ServerSelected)online.Configure(home,assets,home.GetComponent<HeartOfTheRain.App.Profile.PlayerProfileHost>().ServerSession);else online.ConfigureUnavailable(home,assets);return true;}
  string ScrollKey=>session.Tab+":"+session.OpenMailId;
  Font BodyFont=>assets.leaderboard.journey.home.regularFont;Font BoldFont=>assets.leaderboard.journey.home.boldFont;
  void Start()
  {
   if(!home||!assets||(ReviewSelected&&!assets.demoData&&!ServerSelected)){Debug.LogError("Assign Teams assets, Home and review fixture.",this);enabled=false;return;}
   if(UseOnline()){home.Build();home.NavigationRequested.AddListener(Route);if(openOnStart)Show();return;}
   home.Build();if(session==null)session=new TeamsSession(JsonUtility.FromJson<TeamsSnapshot>(assets.demoData.text));home.NavigationRequested.AddListener(Route);if(openOnStart)Show();
  }
  // Live snapshots are read-only until a real social service handles actions.
  public void ApplySnapshot(TeamsSnapshot snapshot){
#if UNITY_EDITOR
   if(ServerSelected)return;bool showing=IsVisible;reviewSampleTeam=true;if(online&&online.IsVisible)online.Hide(false);if(session==null)session=new TeamsSession(snapshot);else session.ApplySnapshot(snapshot);draft="";positions.Clear();if(showing)Show();
#endif
  }
  public void ResetDemo(){
#if UNITY_EDITOR
   if(ServerSelected)return;bool showing=IsVisible;reviewSampleTeam=true;if(online&&online.IsVisible)online.Hide(false);session=new TeamsSession(JsonUtility.FromJson<TeamsSnapshot>(assets.demoData.text));draft="";positions.Clear();if(showing)Show();
#endif
  }
  void Route(string action){if(action=="teams"||action=="team")Show();else if(action=="journey"||action=="leaderboard"||action=="home")Hide(false);}
  public void Show()
  {
   if(UseOnline()){if(canvas)canvas.gameObject.SetActive(false);online.Show();return;}
   if(session==null){if(!ReviewSelected||!assets.demoData)return;session=new TeamsSession(JsonUtility.FromJson<TeamsSnapshot>(assets.demoData.text));}var flow=home.GetComponent<HomeLevelFlow>();var modal=home.GetComponent<PreLevelModal>();if((flow&&flow.Playing)||(modal&&modal.IsVisible))return;
   var journey=home.GetComponent<JourneyPage>();if(journey)journey.Hide(false);var ranks=home.GetComponent<LeaderboardPage>();if(ranks)ranks.Hide(false);session.UpdateSelfLevel(home.State.currentLevel);
   if(session.Rankings==null)session.Rankings=new LeaderboardSession(JsonUtility.FromJson<LeaderboardSnapshot>(assets.leaderboard.demoData.text));session.Rankings.SetRegion(HeartOfTheRain.App.OnlineSocial.CountryRegion89.Saved);
   Build();canvas.gameObject.SetActive(true);home.SetPresentation(false,false);opened=Time.unscaledTime;Reflow(positions.ContainsKey(ScrollKey)?positions[ScrollKey]:1);Focus("tab-"+(int)session.Tab);
  }
  public void Hide(bool showHome=true)
  {
   if(online&&online.IsVisible)online.Hide(showHome);
   if(!IsVisible)return;positions[ScrollKey]=scroll.verticalNormalizedPosition;session.CancelCompose();draft="";canvas.gameObject.SetActive(false);
   if(showHome){home.SetPresentation(true,true);if(EventSystem.current)foreach(var c in home.GetComponentsInChildren<HomeControlLabel>())if(c.action=="teams"){var b=c.GetComponent<Button>();if(b&&b.interactable&&b.gameObject.activeInHierarchy){EventSystem.current.SetSelectedGameObject(b.gameObject);break;}}}
  }
  public void Request(string action)
  {
   if(online&&online.IsVisible){online.Request(action);return;}
   if(!IsVisible||string.IsNullOrEmpty(action)||action=="disabled")return;
   if(session.Rankings?.RegionOpen==true&&!HeartOfTheRain.App.OnlineSocial.CountryRegion89.DialogAction(action))return;
   if(session.Composing&&action!="cancel-compose"&&action!="post-preview")return;
   positions[ScrollKey]=scroll.verticalNormalizedPosition;float pos=scroll.verticalNormalizedPosition;string focus="";bool revealNewest=false;
   if(action=="home"){Hide();return;}if(action=="journey"||action=="leaderboard"||action=="shop"){Hide(false);home.NavigationRequested.Invoke(action);return;}if(action=="teams")return;
   if(action=="choose-country"&&session.Rankings!=null){countryDraft="";session.Rankings.OpenRegion();focus="country-code-input";}
   else if(action=="cancel-country"){session.Rankings?.CloseRegion();focus="choose-country";}
   else if(action=="search-country"&&session.Rankings!=null){session.Rankings.SearchRegion(countryDraft);}
   else if((action=="country-prev"||action=="country-next")&&session.Rankings!=null){session.Rankings.RegionNext(action=="country-next"?1:-1);}
   else if(action=="save-country"||action.StartsWith("country:",StringComparison.Ordinal)){string country=action=="save-country"?countryDraft:action.Substring(8);if(HeartOfTheRain.App.OnlineSocial.CountryRegion89.Save(country)){session.Rankings.SetRegion(country);pos=1;}else session.Rankings.InvalidRegion();}
   else if((action=="scope-global"||action=="scope-regional")&&session.Rankings!=null){session.Rankings.SetLocal(action=="scope-regional");pos=1;}
   else if(action.StartsWith("tab:",StringComparison.Ordinal)){int n;if(!int.TryParse(action.Substring(4),out n)||n<0||n>3)return;session.Select((TeamsTab)n);pos=positions.ContainsKey(ScrollKey)?positions[ScrollKey]:1;focus="tab-"+n;}
   else if(action=="compose"){if(!session.BeginCompose())return;draft="";focus="message-input";}
   else if(action=="cancel-compose"){session.CancelCompose();draft="";focus="compose";}
   else if(action=="post-preview"){if(!session.PostPreview(draft)){Focus("message-input");return;}draft="";pos=0;revealNewest=true;focus="compose";}
   else if(action=="request-lives"){if(!session.RequestLives())return;pos=0;revealNewest=true;focus="compose";}
   else if(action.StartsWith("help:",StringComparison.Ordinal)){session.Help(action.Substring(5));focus="chat-"+action.Substring(5)+"-help";}
   else if(action.StartsWith("mail:",StringComparison.Ordinal)){if(!session.OpenMail(action.Substring(5)))return;pos=1;focus="mail-back";}
   else if(action=="close-mail"){string id=session.OpenMailId;session.CloseMail();pos=positions.ContainsKey(ScrollKey)?positions[ScrollKey]:1;focus="mail-"+id+"-open";}
   else return;
   Reflow(pos);if(revealNewest)RevealNewest();if(focus.Length>0)Focus(focus);
  }
  void RevealNewest()
  {
   if(session.Data.chat.Length==0)return;RectTransform rt;if(!nodes.TryGetValue("chat-"+session.Data.chat[session.Data.chat.Length-1].id,out rt))return;
   float overflow=content.rect.height-viewport.rect.height;if(overflow<=0)return;float bottom=-rt.anchoredPosition.y+rt.rect.height;scroll.verticalNormalizedPosition=1-Mathf.Clamp01((bottom-viewport.rect.height)/overflow);
  }
  void Build()
  {
   if(canvas)return;var root=Rect("Teams Canvas",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=65;
#if UNITY_2022_3_OR_NEWER
   canvas.vertexColorAlwaysGammaSpace=true;
#endif
   scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;root.gameObject.AddComponent<GraphicRaycaster>();fade=root.gameObject.AddComponent<CanvasGroup>();
   safe=Rect("Teams safe area",root);safe.gameObject.AddComponent<RectMask2D>();chrome=Rect("Fixed header and navigation",safe);
   viewport=Rect("Teams viewport",safe);viewport.gameObject.AddComponent<Image>().color=Color.clear;viewport.gameObject.AddComponent<RectMask2D>();scroll=viewport.gameObject.AddComponent<ScrollRect>();scroll.viewport=viewport;scroll.horizontal=false;scroll.vertical=true;scroll.movementType=ScrollRect.MovementType.Clamped;scroll.scrollSensitivity=35;
   content=Rect("Teams content",viewport);scroll.content=content;overlay=Rect("Message composer",safe);
  }
  void Update()
  {
   if(online&&online.IsVisible)return;
   if(!IsVisible)return;if(lastSize.x!=Screen.width||lastSize.y!=Screen.height||lastSafe!=Screen.safeArea||Mathf.Abs(lastScale-home.CurrentUIScale)>.01f)Reflow(scroll.verticalNormalizedPosition);
   fade.alpha=home.State.reduceMotion?1:Mathf.Clamp01((Time.unscaledTime-opened)/.2f);
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
   bool back=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
   bool back=Input.GetKeyDown(KeyCode.Escape);
#endif
   if(back){if(session.Rankings?.RegionOpen==true)Request("cancel-country");else if(session.Composing)Request("cancel-compose");else if(session.OpenMailId.Length>0)Request("close-mail");else Hide();}
  }
  void Reflow(float position)
  {
   string focus="";if(EventSystem.current&&EventSystem.current.currentSelectedGameObject)focus=EventSystem.current.currentSelectedGameObject.name;
   foreach(var root in new[]{chrome,content,overlay})foreach(Transform t in root){t.gameObject.SetActive(false);Destroy(t.gameObject);}nodes.Clear();
   float scale=home.CurrentUIScale;scaler.scaleFactor=scale;canvas.scaleFactor=scale;Rect sr=Screen.safeArea;if(sr.width<=0||sr.height<=0)sr=new Rect(0,0,Screen.width,Screen.height);
   float w=sr.width/scale,h=sr.height/scale;Place(safe,sr.x/scale,(Screen.height-sr.yMax)/scale,w,h);var frame=TeamsLayout.Build(w,h,session);
   Place(chrome,0,0,frame.width,frame.height);Place(overlay,0,0,frame.width,frame.height);Place(viewport,0,frame.viewportY,frame.width,frame.viewportHeight);Place(content,0,0,frame.content.width,frame.content.height);
   Render(frame.chrome,chrome);Render(frame.content,content);Render(frame.overlay,overlay);
   foreach(var section in new[]{chrome,viewport}){var group=section.GetComponent<CanvasGroup>();if(!group)group=section.gameObject.AddComponent<CanvasGroup>();group.interactable=!session.Modal;group.blocksRaycasts=!session.Modal;}scroll.enabled=!session.Modal;
   MainNavigationFeedback.Bind(nodes,home.State.reduceMotion);
   Canvas.ForceUpdateCanvases();scroll.verticalNormalizedPosition=position;lastSize=new Vector2Int(Screen.width,Screen.height);lastSafe=Screen.safeArea;lastScale=scale;if(focus.Length>0)Focus(focus);
  }
  void Render(HomeFrame frame,RectTransform root)
  {
   foreach(var e in frame.elements)
   {
    var parent=string.IsNullOrEmpty(e.parent)?root:nodes[e.parent];var rt=Rect(e.id,parent);Place(rt,e.x,e.y,e.width,e.height);nodes[e.id]=rt;
    if(e.kind=="group")
    {if(e.id.EndsWith("-progress-clip",StringComparison.Ordinal)){rt.gameObject.AddComponent<RectMask2D>();rt.gameObject.SetActive(e.width>0);}if(string.IsNullOrEmpty(e.action))continue;var im=rt.gameObject.AddComponent<Image>();im.color=Color.clear;var b=rt.gameObject.AddComponent<Button>();b.targetGraphic=im;b.transition=Selectable.Transition.None;b.interactable=e.action!="disabled";string action=e.action;b.onClick.AddListener(()=>Request(action));var label=rt.gameObject.AddComponent<HomeControlLabel>();label.action=action;label.label=e.label;}
    else if(e.kind=="input")
    {
     rt.gameObject.AddComponent<RectMask2D>();var im=rt.gameObject.AddComponent<Image>();im.color=Color.clear;var field=rt.gameObject.AddComponent<InputField>();field.targetGraphic=im;bool country=e.id=="country-code-input";field.characterLimit=country?80:120;field.lineType=country?InputField.LineType.SingleLine:InputField.LineType.MultiLineNewline;
     var tr=Rect("Input text",rt);Place(tr,0,0,e.width,e.height);var t=tr.gameObject.AddComponent<Text>();t.font=BodyFont;t.fontSize=e.fontSize;t.color=ColorOf(e.color);t.alignment=TextAnchor.UpperLeft;t.supportRichText=false;t.raycastTarget=false;t.horizontalOverflow=HorizontalWrapMode.Wrap;field.textComponent=t;
     var ph=Rect("Placeholder",rt);Place(ph,0,0,e.width,e.height);var pt=ph.gameObject.AddComponent<Text>();pt.font=t.font;pt.fontSize=e.fontSize;pt.color=ColorOf("#73818B");pt.alignment=TextAnchor.UpperLeft;pt.text=e.label;pt.raycastTarget=false;field.placeholder=pt;field.text=country?countryDraft:draft;field.onValueChanged.AddListener(v=>{if(country)countryDraft=v;else draft=v;});
     var label=rt.gameObject.AddComponent<HomeControlLabel>();label.action="message-input";label.label=e.label;
    }
    else if(e.kind=="paragraph")
    {var lines=e.text.Split('\n');for(int i=0;i<lines.Length;i++){var line=Rect("Line "+i,rt);Place(line,0,i*(e.fontSize+6),e.width,e.fontSize+6);var t=line.gameObject.AddComponent<Text>();t.font=BodyFont;t.text=lines[i];t.fontSize=e.fontSize;t.supportRichText=false;t.raycastTarget=false;t.alignment=TextAnchor.MiddleLeft;t.horizontalOverflow=HorizontalWrapMode.Overflow;t.color=ColorOf(e.color);}}
    else if(e.kind=="text"||e.kind=="lefttext"||e.kind=="subtext"||e.kind=="leftsubtext")
    {var t=rt.gameObject.AddComponent<Text>();t.font=e.kind.Contains("subtext")?BodyFont:BoldFont;t.text=e.text;t.color=ColorOf(e.color);t.fontSize=e.fontSize;t.supportRichText=false;t.raycastTarget=false;t.alignment=e.kind.StartsWith("left",StringComparison.Ordinal)?TextAnchor.MiddleLeft:TextAnchor.MiddleCenter;t.horizontalOverflow=HorizontalWrapMode.Overflow;t.verticalOverflow=VerticalWrapMode.Truncate;LabelFit.Apply(t,e.width,e.height,9);}
    else if(e.kind=="cover")
    {var sp=assets.Find(e.asset);var im=rt.gameObject.AddComponent<RawImage>();im.texture=sp.texture;im.uvRect=JourneyPage.CoverUV(sp,e.width,e.height);im.color=ColorOf(e.color);im.raycastTarget=false;}
    else
    {var im=rt.gameObject.AddComponent<Image>();if(e.kind!="color")im.sprite=assets.Find(e.asset);im.color=ColorOf(e.color);im.type=e.sliced?Image.Type.Sliced:Image.Type.Simple;im.pixelsPerUnitMultiplier=e.sliced?4:1;im.preserveAspect=e.preserveAspect;SpriteFit.Center(im);im.raycastTarget=false;if(e.kind=="mask"){var mask=rt.gameObject.AddComponent<Mask>();mask.showMaskGraphic=false;}}
   }
   foreach(var e in frame.elements)if(e.id=="background"||e.id=="modal-shade"||e.id=="country-shade")PageBackdrop90.Fill(nodes[e.id].GetComponent<MaskableGraphic>(),canvas);
   foreach(var e in frame.elements)if(!string.IsNullOrEmpty(e.action)&&e.action!="disabled"&&!e.id.StartsWith("nav-",StringComparison.Ordinal))
   {var gs=new List<Graphic>();foreach(var n in nodes)if(n.Key.StartsWith(e.id+"-",StringComparison.Ordinal)){var g=n.Value.GetComponent<Graphic>();if(g)gs.Add(g);}nodes[e.id].gameObject.AddComponent<PreLevelButtonFeedback>().Configure(gs.ToArray(),home.State.reduceMotion);}
  }
  void Focus(string id){RectTransform rt;if(!EventSystem.current||!nodes.TryGetValue(id,out rt))return;var select=rt.GetComponent<Selectable>();if(select&&select.interactable)EventSystem.current.SetSelectedGameObject(rt.gameObject);}
  static Color ColorOf(string value){Color c;return ColorUtility.TryParseHtmlString(value,out c)?c:Color.white;}
  static RectTransform Rect(string name,Transform parent){var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);return (RectTransform)go.transform;}
  static void Place(RectTransform rt,float x,float y,float w,float h){rt.anchorMin=rt.anchorMax=rt.pivot=new Vector2(0,1);rt.anchoredPosition=new Vector2(x,-y);rt.sizeDelta=new Vector2(w,h);}
  void OnDestroy(){if(home)home.NavigationRequested.RemoveListener(Route);}
 }
}

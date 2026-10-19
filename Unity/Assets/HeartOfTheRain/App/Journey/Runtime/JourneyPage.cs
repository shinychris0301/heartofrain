using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.Celebrations;
using System;using System.Collections.Generic;using UnityEngine;using UnityEngine.UI;using UnityEngine.EventSystems;
using HeartOfTheRain.App.Home;using HeartOfTheRain.App.PreLevel;
namespace HeartOfTheRain.App.Journey
{
 [DisallowMultipleComponent]
 public sealed class JourneyPage:MonoBehaviour
 {
  public HomePage home;public JourneyAssets assets;public bool openOnStart;
  JourneySession session;Canvas canvas;CanvasScaler scaler;CanvasGroup fade;RectTransform safe,chrome,viewport,content;ScrollRect scroll;
  int localeRevision=-1;int campaignProgress=-1;Vector2Int lastSize;Rect lastSafe;float lastScale,opened,archivePosition=1;
  readonly Dictionary<string,RectTransform> nodes=new Dictionary<string,RectTransform>();
  public bool IsVisible=>canvas&&canvas.gameObject.activeSelf;
  public bool Reading=>session!=null&&session.Reading;
  public JourneyState ReviewState=>session==null?null:session.State;
  void Start()
  {
   if(!home||!assets||!assets.catalog){Debug.LogError("Assign Journey assets, catalog and Home.",this);enabled=false;return;}
   home.Build();session=new JourneySession(JsonUtility.FromJson<JourneyCatalog>(assets.catalog.text));RefreshProgress();home.NavigationRequested.AddListener(Route);if(openOnStart)Show();
  }
  int CompletedLevels()=>campaignProgress>=0?campaignProgress:Math.Max(home.State.currentLevel-1,(home.State.chapterNumber-1)*JourneySession.LevelsPerChapter+home.State.completedLevelsInChapter);
  void RefreshProgress(){session.SetProgress(CompletedLevels());}
  // Adapter for the campaign save system; this reader never writes progress back.
  public void ApplyCampaignProgress(int completedLevels){campaignProgress=Math.Max(0,completedLevels);if(session!=null){RefreshProgress();if(IsVisible)Reflow(false);}}
  public void UseHomeProgress(){campaignProgress=-1;if(session!=null){RefreshProgress();if(IsVisible)Reflow(false);}}
  void Route(string action){if(action=="journey")Show();}
  public void Show()
  {
   if(session==null)return;var flow=home.GetComponent<HomeLevelFlow>();var modal=home.GetComponent<PreLevelModal>();if((flow&&flow.Playing)||(modal&&modal.IsVisible))return;
   RefreshProgress();session.Close();Build();canvas.gameObject.SetActive(true);opened=Time.unscaledTime;home.SetPresentation(false,false);Reflow(true);Focus("chapter-"+session.Cards()[0].number+"-view");
  }
  public void Hide(bool showHome=true)
  {
   if(!IsVisible)return;session.Close();canvas.gameObject.SetActive(false);if(!showHome)return;home.SetPresentation(true,true);
   if(EventSystem.current)foreach(var c in home.GetComponentsInChildren<HomeControlLabel>())if(c.action=="journey"){var b=c.GetComponent<Button>();if(b&&b.interactable){EventSystem.current.SetSelectedGameObject(b.gameObject);break;}}
  }
  public void Request(string action)
  {
   if(!IsVisible||action=="disabled"||ChapterCelebrationPlayer.IsPlaying(home))return;
   if(action=="celebration"){if(Reading&&session.State.beat==1&&session.Complete(session.State.readingChapter))ChapterCelebrationPlayer.TryPlay(home,session.State.readingChapter,()=>Focus("reader-watch"));return;}
   if(action=="home"){Hide();return;}
   if(action=="leaderboard"||action=="teams"||action=="shop"){Hide(false);home.NavigationRequested.Invoke(action);return;}
   if(action=="journey"){if(Reading){session.Close();Reflow(false,archivePosition);}return;}
   if(action=="reader-close"){int chapter=session.State.readingChapter;session.Close();Reflow(false,archivePosition);Focus("chapter-"+chapter+"-view");return;}
   if(action.StartsWith("view:",StringComparison.Ordinal)){int chapter;if(int.TryParse(action.Substring(5),out chapter)&&session.Open(chapter)){archivePosition=scroll.verticalNormalizedPosition;opened=Time.unscaledTime;Reflow(true);Focus("reader-close");}return;}
   if((action=="next"&&session.Next())||(action=="previous"&&session.Previous())){opened=Time.unscaledTime;Reflow(true);Focus("reader-next");}
  }
  void Build()
  {
   if(canvas)return;var root=Rect("Journey Canvas",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=60;
#if UNITY_2022_3_OR_NEWER
   canvas.vertexColorAlwaysGammaSpace=true;
#endif
   scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;root.gameObject.AddComponent<GraphicRaycaster>();fade=root.gameObject.AddComponent<CanvasGroup>();
   var matte=Rect("Safe-area matte",root);matte.anchorMin=Vector2.zero;matte.anchorMax=Vector2.one;matte.sizeDelta=Vector2.zero;var bg=matte.gameObject.AddComponent<Image>();bg.color=ColorOf("#071A30");
   safe=Rect("Journey safe area",root);safe.gameObject.AddComponent<RectMask2D>();chrome=Rect("Fixed header and navigation",safe);
   viewport=Rect("Chapter viewport",safe);var target=viewport.gameObject.AddComponent<Image>();target.color=Color.clear;viewport.gameObject.AddComponent<RectMask2D>();
   scroll=viewport.gameObject.AddComponent<ScrollRect>();scroll.viewport=viewport;scroll.horizontal=false;scroll.vertical=true;scroll.movementType=ScrollRect.MovementType.Clamped;scroll.scrollSensitivity=35;
   content=Rect("Journey content",viewport);scroll.content=content;
  }
  void Update()
  {
   if(!IsVisible||ChapterCelebrationPlayer.IsPlaying(home)||ChapterCelebrationPlayer.ConsumedInputThisFrame)return;
   if(localeRevision!=GameLocale.Revision||lastSize.x!=Screen.width||lastSize.y!=Screen.height||lastSafe!=Screen.safeArea||Mathf.Abs(lastScale-home.CurrentUIScale)>.01f)Reflow(false);
   fade.alpha=home.State.reduceMotion?1:Mathf.Clamp01((Time.unscaledTime-opened)/.2f);
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
   bool back=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
   bool back=Input.GetKeyDown(KeyCode.Escape);
#endif
   if(back){if(Reading)Request("reader-close");else Hide();}
  }
  void Reflow(bool reset,float restore=-1)
  {
   float position=restore>=0?restore:reset?1:scroll.verticalNormalizedPosition;
   string focus="";if(EventSystem.current&&EventSystem.current.currentSelectedGameObject){var label=EventSystem.current.currentSelectedGameObject.GetComponent<HomeControlLabel>();if(label)focus=label.action;}
   foreach(Transform t in chrome){t.gameObject.SetActive(false);Destroy(t.gameObject);}foreach(Transform t in content){t.gameObject.SetActive(false);Destroy(t.gameObject);}nodes.Clear();
   float scale=home.CurrentUIScale;scaler.scaleFactor=scale;canvas.scaleFactor=scale;Rect sr=Screen.safeArea;if(sr.width<=0||sr.height<=0)sr=new Rect(0,0,Screen.width,Screen.height);
   float w=sr.width/scale,h=sr.height/scale;Place(safe,sr.x/scale,(Screen.height-sr.yMax)/scale,w,h);var frame=JourneyLayout.Build(w,h,session,Reading&&ChapterCelebrationPlayer.Available(session.State.readingChapter));
   Place(chrome,0,0,frame.width,frame.height);Place(viewport,0,frame.viewportY,frame.width,frame.viewportHeight);Place(content,0,0,frame.content.width,frame.content.height);
   Render(frame.chrome,chrome);Render(frame.content,content);MainNavigationFeedback.Bind(nodes,home.State.reduceMotion);Canvas.ForceUpdateCanvases();scroll.verticalNormalizedPosition=position;
   localeRevision=GameLocale.Revision;lastSize=new Vector2Int(Screen.width,Screen.height);lastSafe=Screen.safeArea;lastScale=scale;
   if(!string.IsNullOrEmpty(focus))foreach(var e in frame.content.elements)if(e.action==focus){Focus(e.id);break;}
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
    else if(e.kind=="paragraph"||e.kind=="story-title")
    {
     // One Text per measured line prevents engine rewrapping from clipping translated prose.
     var lines=e.text.Split('\n');float step=e.kind=="paragraph"?24:(e.id=="reader-heading"?e.fontSize+6:e.fontSize+3);
     for(int i=0;i<lines.Length;i++){var line=Rect(e.id+"-line-"+i,rt);Place(line,0,i*step,e.width,step);var t=line.gameObject.AddComponent<Text>();t.font=e.kind=="paragraph"?assets.home.regularFont:assets.home.boldFont;t.text=lines[i];t.fontSize=e.fontSize;t.color=ColorOf(e.color);t.supportRichText=false;t.raycastTarget=false;t.alignment=e.kind=="paragraph"?TextAnchor.UpperLeft:TextAnchor.MiddleCenter;t.horizontalOverflow=HorizontalWrapMode.Overflow;t.verticalOverflow=VerticalWrapMode.Truncate;
      if(e.shadow){var sh=line.gameObject.AddComponent<Shadow>();sh.effectColor=new Color(0,.02f,.05f,.8f);sh.effectDistance=new Vector2(0,-1);}
     }
    }
    else if(e.kind=="text")
    {
     var t=rt.gameObject.AddComponent<Text>();t.font=e.kind=="paragraph"?assets.home.regularFont:assets.home.boldFont;t.text=e.text;t.color=ColorOf(e.color);t.fontSize=e.fontSize;t.supportRichText=false;t.raycastTarget=false;t.alignment=e.kind=="paragraph"?TextAnchor.UpperLeft:TextAnchor.MiddleCenter;
     t.horizontalOverflow=e.kind=="paragraph"?HorizontalWrapMode.Wrap:HorizontalWrapMode.Overflow;t.verticalOverflow=VerticalWrapMode.Truncate;t.lineSpacing=e.kind=="paragraph"?1.10f:1;
     if(e.kind=="text")while(t.fontSize>10&&t.preferredWidth>e.width)t.fontSize--;
     if(e.shadow){var sh=rt.gameObject.AddComponent<Shadow>();sh.effectColor=new Color(0,.02f,.05f,.8f);sh.effectDistance=new Vector2(0,-1);}
    }
    else if(e.kind=="cover")
    {
     var sp=assets.Find(e.asset);var im=rt.gameObject.AddComponent<RawImage>();im.texture=sp.texture;im.uvRect=CoverUV(sp,e.width,e.height);im.color=ColorOf(e.color);im.raycastTarget=false;
    }
    else
    {
     var im=rt.gameObject.AddComponent<Image>();im.sprite=assets.Find(e.asset);im.color=ColorOf(e.color);im.type=e.sliced?Image.Type.Sliced:Image.Type.Simple;im.pixelsPerUnitMultiplier=e.sliced?4:1;im.preserveAspect=e.preserveAspect;im.raycastTarget=false;if(e.kind=="mask"){var m=rt.gameObject.AddComponent<Mask>();m.showMaskGraphic=false;}
    }
   }
   foreach(var e in frame.elements)if(!string.IsNullOrEmpty(e.action)&&e.action!="disabled"&&!e.id.StartsWith("nav-",StringComparison.Ordinal))
   {var graphics=new List<Graphic>();foreach(var n in nodes)if(n.Key.StartsWith(e.id+"-",StringComparison.Ordinal)){var g=n.Value.GetComponent<Graphic>();if(g)graphics.Add(g);}nodes[e.id].gameObject.AddComponent<PreLevelButtonFeedback>().Configure(graphics.ToArray(),home.State.reduceMotion);}
  }
  public static Rect CoverUV(Sprite sp,float w,float h)
  {Rect t=sp.textureRect;float scale=Mathf.Max(w/t.width,h/t.height),fx=w/(t.width*scale),fy=h/(t.height*scale);return new Rect((t.x+(1-fx)*t.width*.5f)/sp.texture.width,(t.y+(1-fy)*t.height*.88f)/sp.texture.height,fx*t.width/sp.texture.width,fy*t.height/sp.texture.height);}
  void Focus(string id){RectTransform r;if(EventSystem.current&&nodes.TryGetValue(id,out r)){var b=r.GetComponent<Button>();if(b&&b.interactable)EventSystem.current.SetSelectedGameObject(b.gameObject);}}
  static Color ColorOf(string s){Color c;return ColorUtility.TryParseHtmlString(s,out c)?c:Color.white;}
  static RectTransform Rect(string name,Transform parent){var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);return (RectTransform)go.transform;}
  static void Place(RectTransform r,float x,float y,float w,float h){r.anchorMin=r.anchorMax=r.pivot=new Vector2(0,1);r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(w,h);}
  void OnDestroy(){if(home)home.NavigationRequested.RemoveListener(Route);}
 }
}

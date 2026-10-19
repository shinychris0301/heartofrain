using HeartOfTheRain.App.Localization;
using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace HeartOfTheRain.App.Home
{
    [Serializable] public sealed class HomeRouteEvent : UnityEvent<string> { }
    [Serializable] public sealed class HomeLevelEvent : UnityEvent<int> { }
    [DisallowMultipleComponent]
    public sealed class HomePage : MonoBehaviour
    {
        [SerializeField] private HomePageAssets assets;
        [SerializeField] private HomeState state = new HomeState();
        [SerializeField] private bool usePreviewState = true;
        [Tooltip("0 uses a deterministic resolution scale, identical in Editor and player. Override for UI scale preferences.")]
        [SerializeField, Min(0)] private float uiScaleOverride;
        [SerializeField] private HomeRouteEvent navigationRequested = new HomeRouteEvent();
        [SerializeField] private HomeLevelEvent preLevelRequested = new HomeLevelEvent();
        [SerializeField] private string lastRequestedAction;
        private Canvas canvas;
        private CanvasScaler scaler;
        private RectTransform canvasRect, safeViewport, content;
        private RawImage background;
        private CanvasGroup fade;
        private ScrollRect scroll;
        private EventSystem ownedEvents;
        private readonly Dictionary<string,RectTransform> nodes = new Dictionary<string,RectTransform>();
        private readonly Dictionary<string,Button> actions = new Dictionary<string,Button>();
        private HomeFrame frame;
        private Vector2Int previousSize;
        private Rect previousSafe;
        private float previousScale, openedAt;
        private int localeRevision=-1;
        private bool drawer;
        private Sprite backgroundOverride;
        private string returnFocus = "events";
        public HomeRouteEvent NavigationRequested { get { return navigationRequested; } }
        public HomeLevelEvent PreLevelRequested { get { return preLevelRequested; } }
        public string LastRequestedAction { get { return lastRequestedAction; } }
        public HomeState State { get { return state; } }
        public float CurrentUIScale { get { return Scale(); } }
        public void SetPresentation(bool visible,bool interactable)
        {if(!canvas)Build();canvas.gameObject.SetActive(visible);fade.blocksRaycasts=interactable;fade.interactable=interactable;}
        public bool EventsOpen { get { return drawer; } }

        private void Start() { Build(); }
        private void OnEnable() { openedAt=Time.unscaledTime; if(canvas)canvas.gameObject.SetActive(true); }
        private void OnDisable() { if(canvas)canvas.gameObject.SetActive(false); }
        public void Build()
        {
            if(canvas) return;
            if(!assets) { Debug.LogError("HomePage requires HomePageAssets.",this);enabled=false;return; }
            if(usePreviewState && assets.previewState) state=JsonUtility.FromJson<HomeState>(assets.previewState.text) ?? new HomeState();
            state.Normalize();
            canvasRect=Rect("Home Canvas",transform);
            canvas=canvasRect.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=20;
#if UNITY_2022_3_OR_NEWER
            canvas.vertexColorAlwaysGammaSpace=true;
#endif
            scaler=canvasRect.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;
            canvasRect.gameObject.AddComponent<GraphicRaycaster>();
            fade=canvasRect.gameObject.AddComponent<CanvasGroup>();
            var matte=Rect("Safe area matte",canvasRect);matte.anchorMin=Vector2.zero;matte.anchorMax=Vector2.one;matte.sizeDelta=Vector2.zero;var matteImage=matte.gameObject.AddComponent<Image>();matteImage.color=Parse("#08192D");matteImage.raycastTarget=false;
            safeViewport=Rect("Safe area viewport",canvasRect);safeViewport.gameObject.AddComponent<RectMask2D>();
            var backdrop=Rect("Chapter artwork",safeViewport);background=backdrop.gameObject.AddComponent<RawImage>();background.raycastTarget=false;
            scroll=safeViewport.gameObject.AddComponent<ScrollRect>();scroll.viewport=safeViewport;scroll.movementType=ScrollRect.MovementType.Clamped;scroll.scrollSensitivity=32;
            content=Rect("Responsive content",safeViewport);scroll.content=content;
            if(!EventSystem.current)
            {
                var e=new GameObject("Home EventSystem");ownedEvents=e.AddComponent<EventSystem>();
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
                e.AddComponent<UnityEngine.InputSystem.UI.InputSystemUIInputModule>();
#else
                e.AddComponent<StandaloneInputModule>();
#endif
            }
            Reflow();
        }
        public void ApplyState(HomeState next)
        {
            if(next==null)throw new ArgumentNullException("next");
            next.Normalize();state=next;if(canvas)Reflow();
        }
        public void SetChapterBackground(Sprite sprite)
        { backgroundOverride=sprite; if(canvas)Reflow(); }
        public void SetUIScale(float scale)
        { uiScaleOverride=Mathf.Max(0,scale);if(canvas)Reflow(); }
        public void ShowEvents(bool visible)
        {
            if(drawer==visible)return;drawer=visible;
            if(canvas) { Reflow(); Focus(visible?"drawer-close":returnFocus); }
        }
        public void Request(string action)
        {
            if(string.IsNullOrEmpty(action))return;
            if(action=="events") { returnFocus="events";ShowEvents(true);return; }
            if(action=="close-events") { ShowEvents(false);return; }
            if(action.StartsWith("drawer-",StringComparison.Ordinal)) action=action.Substring(7);
            lastRequestedAction=action=="prelevel"?"prelevel:"+state.currentLevel:action;
            if(action=="home") { if(drawer)ShowEvents(false);return; }
            if(action=="prelevel")preLevelRequested.Invoke(state.currentLevel);
            else navigationRequested.Invoke(action);
#if UNITY_EDITOR
            Debug.Log("Home request: "+lastRequestedAction,this);
#endif
        }
        private float Scale()
        {
            if(uiScaleOverride>0)return Mathf.Clamp(uiScaleOverride,.5f,5);
            float aspect=Screen.width/(float)Mathf.Max(1,Screen.height);
            float reference=(aspect<.68f||aspect>1.8f)?393:768;
            return Mathf.Max(1,Mathf.Min(Screen.width,Screen.height)/reference);
        }

        private void Update()
        {
            if(!canvas)return;
            float scale=Scale();
            if(localeRevision!=GameLocale.Revision||previousSize.x!=Screen.width||previousSize.y!=Screen.height||previousSafe!=Screen.safeArea||Mathf.Abs(previousScale-scale)>.01f)Reflow();
            fade.alpha=state.reduceMotion?1:Mathf.Clamp01((Time.unscaledTime-openedAt)/.22f);
            if(drawer && CancelPressed())ShowEvents(false);
        }
        private static bool CancelPressed()
        {
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
            return UnityEngine.InputSystem.Keyboard.current!=null && UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
            return Input.GetKeyDown(KeyCode.Escape);
#endif
        }
        private void Reflow()
        {
            string focus="";
            if(EventSystem.current && EventSystem.current.currentSelectedGameObject)
                foreach(var p in actions)if(p.Value.gameObject==EventSystem.current.currentSelectedGameObject){focus=p.Key;break;}
            foreach(Transform child in content){child.gameObject.SetActive(false);Destroy(child.gameObject);}
            nodes.Clear();actions.Clear();
            float scale=Scale();scaler.scaleFactor=scale;canvas.scaleFactor=scale;
            var safe=Screen.safeArea;
            if(safe.width<=0||safe.height<=0)safe=new Rect(0,0,Screen.width,Screen.height);
            float sw=safe.width/scale,sh=safe.height/scale;
            Place(safeViewport,safe.x/scale,(Screen.height-safe.yMax)/scale,sw,sh);
            frame=HomeLayoutEngine.Build(sw,sh,state,drawer);localeRevision=GameLocale.Revision;
            Place(content,0,0,frame.width,frame.height);
            scroll.horizontal=frame.width>sw+.1f;scroll.vertical=frame.height>sh+.1f;
            scroll.enabled=scroll.horizontal||scroll.vertical;
            scroll.horizontalNormalizedPosition=0;scroll.verticalNormalizedPosition=1;
            foreach(var e in frame.elements)
            {
                RectTransform parent=string.IsNullOrEmpty(e.parent)?content:nodes[e.parent];
                var r=Rect(e.id,parent);Place(r,e.x,e.y,e.width,e.height);nodes.Add(e.id,r);
                if(e.kind=="group")
                {
                    bool isDrawer=e.id.StartsWith("drawer-",StringComparison.Ordinal);
                    if(!string.IsNullOrEmpty(e.action))
                    {
                        var hit=r.gameObject.AddComponent<Image>();hit.color=Color.clear;
                        var button=r.gameObject.AddComponent<Button>();button.targetGraphic=hit;button.transition=Selectable.Transition.None;
                        button.interactable=e.action!="disabled"&&(!drawer||isDrawer);
                        string action=e.action;button.onClick.AddListener(()=>Request(action));actions.Add(e.id,button);
                        var access=r.gameObject.AddComponent<HomeControlLabel>();access.label=e.label;access.action=e.action;
                        var feedback=r.gameObject.AddComponent<HomeButtonFeedback>();feedback.reduceMotion=state.reduceMotion;
                        feedback.enabled=button.interactable&&!e.id.StartsWith("nav-",StringComparison.Ordinal);
                    }
                    else if(e.id=="drawer-panel") {var blocker=r.gameObject.AddComponent<Image>();blocker.color=Color.clear;}
                    continue;
                }
                if(e.kind=="text")
                {
                    var label=r.gameObject.AddComponent<Text>();label.font=assets.boldFont;label.text=e.text;label.color=Parse(e.color);
                    label.alignment=TextAnchor.MiddleCenter;label.horizontalOverflow=HorizontalWrapMode.Overflow;label.verticalOverflow=VerticalWrapMode.Truncate;
                    label.raycastTarget=false;label.supportRichText=false;label.fontSize=e.fontSize;
                    int minimum=Math.Min(e.fontSize,12);
                    while(label.fontSize>minimum && label.preferredWidth>e.width)label.fontSize--;
                    if(label.preferredWidth>e.width)
                    {
                        string original=e.text;
                        while(original.Length>1 && label.preferredWidth>e.width)
                        {original=original.Substring(0,original.Length-1);label.text=original+"…";}
                    }
                    if(e.shadow){var shadow=r.gameObject.AddComponent<Shadow>();shadow.effectColor=new Color(0,.035f,.08f,.9f);shadow.effectDistance=new Vector2(0,-1);}
                }
                else
                {
                    var im=r.gameObject.AddComponent<Image>();im.raycastTarget=false;im.color=Parse(e.color);
                    if(e.kind=="sprite")
                    {im.sprite=assets.Find(e.asset);im.type=e.sliced?Image.Type.Sliced:Image.Type.Simple;im.preserveAspect=e.preserveAspect;im.pixelsPerUnitMultiplier=e.sliced?(e.asset.StartsWith("Nav_",StringComparison.Ordinal)?4:e.height>100?3:im.sprite.rect.height/Mathf.Max(1,e.height)):1;}
                }
            }
            // Shared button feedback transforms only child visuals, leaving anchors and touch bounds fixed.
            foreach(var button in actions.Values)button.GetComponent<HomeButtonFeedback>().CaptureVisuals();
            MainNavigationFeedback.Bind(nodes,state.reduceMotion);
            bool tablet=!frame.landscape&&sw/sh>=.68f&&sw>=480;
            Sprite art=backgroundOverride?backgroundOverride:assets.Find(frame.landscape?(sw/sh>2?"Chapter01_VillageWell_Ultrawide":"Chapter01_VillageWell_Landscape"):tablet?"Chapter01_VillageWell_Tablet":"Chapter01_VillageWell");
            if(art)
            {
                background.texture=art.texture;
                float cover=Mathf.Max(sw/art.rect.width,sh/art.rect.height);
                float artW=art.rect.width*cover,artH=art.rect.height*cover;
                Rect tr=art.textureRect;
                background.uvRect=new Rect((tr.x+(1-sw/artW)*tr.width/2)/art.texture.width,
                    (tr.y+(1-sh/artH)*tr.height/2)/art.texture.height,
                    sw/artW*tr.width/art.texture.width,sh/artH*tr.height/art.texture.height);
                Place(background.rectTransform,0,0,sw,sh);
            }
            previousSize=new Vector2Int(Screen.width,Screen.height);previousSafe=Screen.safeArea;previousScale=scale;
            if(!string.IsNullOrEmpty(focus))Focus(focus);
        }
        private void Focus(string id)
        {Button b;if(EventSystem.current && actions.TryGetValue(id,out b)&&b.interactable)EventSystem.current.SetSelectedGameObject(b.gameObject);}
        private static Color Parse(string value){Color c;return ColorUtility.TryParseHtmlString(value,out c)?c:Color.white;}
        private static RectTransform Rect(string name,Transform parent)
        {var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);return (RectTransform)go.transform;}
        private static void Place(RectTransform r,float x,float y,float w,float h)
        {r.anchorMin=r.anchorMax=r.pivot=new Vector2(0,1);r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(w,h);}
        private void OnDestroy(){if(ownedEvents)Destroy(ownedEvents.gameObject);}
    }
}

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
        private Sprite profileAvatar, profileFrame, profileMask;
        private HomeHeaderSprites headerSprites;
        public HomeLivesFeedback LifeFeedback {get;private set;}
        private RectTransform selectedAvatar;
        private string returnFocus = "events";
        public HomeRouteEvent NavigationRequested { get { return navigationRequested; } }
        public HomeLevelEvent PreLevelRequested { get { return preLevelRequested; } }
        public string LastRequestedAction { get { return lastRequestedAction; } }
        public HomeState State { get { return state; } }
        public float CurrentUIScale { get { return Scale(); } }
        Coroutine rewardReveal;
        RectTransform receiptVisual;
        bool committedReveal;
        bool rewardFocused,rewardPaused;
        public bool RewardPresentationForeground=>rewardFocused&&!rewardPaused;
        public bool RewardRevealPlaying=>rewardReveal!=null;
        // The model already settled the grant. This only interpolates visible
        // counters/progress; Home stays interactive and artwork stays clear.
        public void PlayRewardReveal(int coins,int stars,int completedBefore)
        {
            CancelRewardReveal();
            if(coins<=0&&stars<=0){rewardReveal=null;return;}
            rewardReveal=StartCoroutine(RevealReward(coins,completedBefore));
        }
        // A receipt shows what was committed, while the header continues to
        // show the actual current wallet (the player may have spent it since).
        // Completion acknowledges presentation only, never grants inventory.
        public void PlayCommittedReward(HeartOfTheRain.App.Profile.RewardGrant grant,HeartOfTheRain.App.PreLevel.PreLevelAssets icons,Action complete)
        {
            if(grant==null||!icons)throw new ArgumentNullException();grant.Validate();
            CancelRewardReveal();if(!PresentationInteractable||!RewardPresentationForeground)return;
            committedReveal=true;rewardReveal=StartCoroutine(RevealCommittedReward(grant.Copy(),icons,complete));
        }
        System.Collections.IEnumerator RevealCommittedReward(HeartOfTheRain.App.Profile.RewardGrant grant,HeartOfTheRain.App.PreLevel.PreLevelAssets icons,Action complete)
        {
            yield return null;
            if(!PresentationInteractable||!RewardPresentationForeground){CancelRewardReveal();yield break;}
            var keys=new List<string>();var amounts=new List<int>();
            if(grant.coins>0){keys.Add("RewardCoin");amounts.Add(grant.coins);}if(grant.stars>0){keys.Add("RewardStar_R2");amounts.Add(grant.stars);}
            for(int i=0;i<4;i++)if(grant.starting[i]>0){keys.Add(new[]{"Rocket","Bomb","RainbowOrb_R2","GoldenSeeker_R2"}[i]);amounts.Add(grant.starting[i]);}
            for(int i=0;i<4;i++)if(grant.tools[i]>0){keys.Add(new[]{"boosterHammer","boosterAxe","boosterRam","boosterAtlas"}[i]);amounts.Add(grant.tools[i]);}
            float width=Mathf.Min(350,safeViewport.rect.width-16),cell=width/Mathf.Min(5,Mathf.Max(1,keys.Count));int rows=(keys.Count+4)/5;
            receiptVisual=Rect("Committed reward receipt",safeViewport);Place(receiptVisual,(safeViewport.rect.width-width)/2,105,width,rows*66+12);
            var panel=receiptVisual.gameObject.AddComponent<Image>();panel.sprite=icons.Find("IvoryInset");panel.type=Image.Type.Sliced;panel.pixelsPerUnitMultiplier=4;panel.raycastTarget=false;
            var alpha=receiptVisual.gameObject.AddComponent<CanvasGroup>();alpha.blocksRaycasts=false;alpha.interactable=false;
            for(int i=0;i<keys.Count;i++){
                int inRow=Mathf.Min(5,keys.Count-i/5*5);float x=(width-inRow*cell)/2+i%5*cell;
                var image=Rect("Receipt "+keys[i],receiptVisual).gameObject.AddComponent<Image>();Place(image.rectTransform,x+(cell-40)/2,6+i/5*66,40,40);image.sprite=icons.Find(keys[i]);image.preserveAspect=true;image.raycastTarget=false;
                if(!image.sprite){CancelRewardReveal();yield break;}
                var label=Rect("Receipt quantity "+keys[i],receiptVisual).gameObject.AddComponent<Text>();Place(label.rectTransform,x,46+i/5*66,cell,20);label.font=assets.boldFont;label.fontSize=14;label.text="+"+amounts[i].ToString(System.Globalization.CultureInfo.InvariantCulture);label.alignment=TextAnchor.MiddleCenter;label.color=Parse("#173B52");label.raycastTarget=false;
                LabelFit.Apply(label,cell,20,9);
            }
            float elapsed=0,duration=state.reduceMotion?1.5f:2;
            while(elapsed<duration){if(!PresentationInteractable||!RewardPresentationForeground){CancelRewardReveal();yield break;}elapsed+=Time.unscaledDeltaTime;float u=Mathf.Clamp01(elapsed/duration);alpha.alpha=state.reduceMotion?1:Mathf.Clamp01(Mathf.Min(elapsed/.15f,(duration-elapsed)/.2f));receiptVisual.localScale=Vector3.one*(state.reduceMotion?1:1+.025f*Mathf.Sin(u*Mathf.PI));yield return null;}
            if(!RewardPresentationForeground){CancelRewardReveal();yield break;}
            if(receiptVisual){receiptVisual.gameObject.SetActive(false);Destroy(receiptVisual.gameObject);}receiptVisual=null;committedReveal=false;rewardReveal=null;complete?.Invoke();
        }
        void CancelRewardReveal()
        {
            if(rewardReveal!=null)StopCoroutine(rewardReveal);rewardReveal=null;committedReveal=false;
            if(receiptVisual){receiptVisual.gameObject.SetActive(false);Destroy(receiptVisual.gameObject);}receiptVisual=null;
            foreach(string id in new[]{"coin-count","progress-count","progress-fill"})if(nodes.TryGetValue(id,out var node)&&node){node.localScale=Vector3.one;var element=frame?.elements.Find(e=>e.id==id);if(element!=null){var label=node.GetComponent<Text>();if(label){label.text=id=="coin-count"?HomeLayoutEngine.CompactNumber(state.coins):state.completedLevelsInChapter+" / "+state.levelsPerChapter;label.color=Parse(element.color);}else if(id=="progress-fill")node.sizeDelta=new Vector2(element.width,node.sizeDelta.y);}}
        }
        void OnApplicationPause(bool paused){rewardPaused=paused;if(paused){NavigationDiagnostics124.Shared.Save();if(committedReveal)CancelRewardReveal();}}
        void OnApplicationQuit(){NavigationDiagnostics124.Shared.Save();}
        void OnApplicationFocus(bool focused){rewardFocused=focused;if(!focused&&committedReveal)CancelRewardReveal();}
        System.Collections.IEnumerator RevealReward(int coins,int completedBefore)
        {
            float elapsed=0,duration=state.reduceMotion?.35f:1.05f;
            RectTransform count;var ink=nodes.TryGetValue("coin-count",out count)?count.GetComponent<Text>().color:Color.white;
            while(elapsed<duration){elapsed+=Time.unscaledDeltaTime;float u=Mathf.SmoothStep(0,1,Mathf.Clamp01(elapsed/duration));RectTransform node;
                float pulse=state.reduceMotion?0:Mathf.Sin(u*Mathf.PI);
                if(nodes.TryGetValue("coin-count",out node)){var label=node.GetComponent<Text>();label.text=HomeLayoutEngine.CompactNumber(Mathf.RoundToInt(state.coins-coins+coins*u));label.color=Color.Lerp(ink,new Color(.65f,.42f,.12f),pulse*.7f);node.localScale=Vector3.one*(1+.06f*pulse);}
                if(nodes.TryGetValue("progress-count",out node)){node.GetComponent<Text>().text=Mathf.RoundToInt(completedBefore%50+(state.completedLevelsInChapter-completedBefore%50)*u)+" / "+state.levelsPerChapter;node.localScale=Vector3.one*(1+.06f*pulse);}
                if(nodes.TryGetValue("progress-fill",out node)){var e=frame.elements.Find(x=>x.id=="progress-fill");float full=e.width*state.levelsPerChapter/Mathf.Max(1,state.completedLevelsInChapter);node.sizeDelta=new Vector2(full*Mathf.Lerp(completedBefore%50,state.completedLevelsInChapter,u)/state.levelsPerChapter,node.sizeDelta.y);}
                yield return null;
            }
            rewardReveal=null;
        }
        bool reflowPending;
        public void SetPresentation(bool visible,bool interactable)
        {if(!canvas)Build();if(!canvas)return;if(!visible||!interactable){if(LifeFeedback)LifeFeedback.Cancel();if(committedReveal)CancelRewardReveal();}canvas.gameObject.SetActive(visible);if(visible&&reflowPending){reflowPending=false;Reflow();}fade.blocksRaycasts=interactable;fade.interactable=interactable;}
        // Live text for a status badge (event timers): patches the label in
        // place so Home is not rebuilt under a tap or a scroll every minute.
        public bool UpdateLabel(string id,string text)
        {
            RectTransform node;if(!canvas||frame==null||!nodes.TryGetValue(id,out node))return false;
            var label=node.GetComponent<Text>();var e=frame.elements.Find(x=>x.id==id);if(!label||e==null)return false;
            e.text=GameLocale.Element(id,text);label.text=e.text;label.fontSize=e.fontSize;LabelFit.Apply(label,e.width,e.height,Math.Min(e.fontSize,12));return true;
        }
        public bool EventsOpen { get { return drawer; } }
        public bool PresentationVisible=>canvas&&canvas.gameObject.activeInHierarchy;
        public bool PresentationInteractable=>PresentationVisible&&fade&&fade.interactable;

        private void Start() { Build();NavigationDiagnostics124.Shared.Read(); }
        private void OnEnable() { rewardFocused=Application.isFocused;rewardPaused=false;openedAt=Time.unscaledTime; if(canvas)canvas.gameObject.SetActive(true); }
        private void OnDisable() { UnityEngine.Rendering.OnDemandRendering.renderFrameInterval=1;CancelRewardReveal();if(canvas)canvas.gameObject.SetActive(false); }
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
            var backdrop=Rect("Chapter artwork",canvasRect);backdrop.SetSiblingIndex(safeViewport.GetSiblingIndex());background=backdrop.gameObject.AddComponent<RawImage>();background.raycastTarget=false;
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
            LifeFeedback=gameObject.AddComponent<HomeLivesFeedback>();LifeFeedback.Configure(this,assets.boldFont,canvasRect);
            Reflow();
            HeartOfTheRain.App.Profile.ProfilePage.Attach(this);
        }
        public void SetProfileAvatar(Sprite portrait,Sprite frameSprite,Sprite maskSprite)
        {
            if(profileAvatar==portrait&&profileFrame==frameSprite&&profileMask==maskSprite)return;
            profileAvatar=portrait;profileFrame=frameSprite;profileMask=maskSprite;
            if(canvas)
            {
                RenderHomeAvatar();
                Button button;if(actions.TryGetValue("avatar",out button))button.GetComponent<HomeButtonFeedback>().CaptureVisuals();
            }
        }
        public void ApplyState(HomeState next)
        {
            if(next==null)throw new ArgumentNullException("next");
            var profile=GetComponent<HeartOfTheRain.App.Profile.PlayerProfileHost>();if(profile)profile.ImportTransientView(next);
            CancelRewardReveal();
            // A hidden Home rebuilds once when shown, not during gameplay or other pages.
            next.rewardedVisible=state.rewardedVisible;next.rewardedEligible=state.rewardedEligible;next.rewardedStatus=state.rewardedStatus;
            next.Normalize();state=next;if(canvas){if(canvas.gameObject.activeInHierarchy)Reflow();else reflowPending=true;}
        }
        public void SetRewardedShortcut(bool visible,bool eligible,string status)
        {
            status=status??"";
            if(state.rewardedVisible==visible&&state.rewardedEligible==eligible&&state.rewardedStatus==status)return;
            state.rewardedVisible=visible;state.rewardedEligible=eligible;state.rewardedStatus=status;
            if(canvas){if(canvas.gameObject.activeInHierarchy)Reflow();else reflowPending=true;}
        }
        public Sprite ProfileBackground => backgroundOverride ? backgroundOverride : assets.chapterBackground;
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
            else {
                switch(action){
                    case "teams":case "team":NavigationDiagnostics124.Shared.Record(NavigationEvent124.HomeTeams,0);break;
                    case "leaderboard":NavigationDiagnostics124.Shared.Record(NavigationEvent124.HomeLeaderboard,0);break;
                    case "journey":NavigationDiagnostics124.Shared.Record(NavigationEvent124.HomeJourney,0);break;
                    case "shop":NavigationDiagnostics124.Shared.Record(NavigationEvent124.HomeShop,0);break;
                }
                navigationRequested.Invoke(action);
            }
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
            bool settled=wasInteractable;wasInteractable=PresentationInteractable;
            if(drawer){if(CancelPressed())ShowEvents(false);}
            // Back leaves the game for the launcher, once Home has been on top since last frame:
            // a page closing on this same key press must not also close the app.
            else if(settled&&wasInteractable&&CancelPressed())MoveToBackground();
            SaveIdlePower();
        }
        bool wasInteractable;float lastTouch;
        const float IdleRenderDelay=3;const int IdleRenderInterval=3;
        // Home is still art between taps. Drawing every third frame saves power; Update keeps
        // running at full rate, and the first touch or page change restores full rendering.
        void SaveIdlePower(){
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
            bool touched=UnityEngine.InputSystem.Pointer.current!=null&&UnityEngine.InputSystem.Pointer.current.press.isPressed;
#else
            bool touched=Input.touchCount>0||Input.GetMouseButton(0);
#endif
            if(touched||!wasInteractable||RewardRevealPlaying||drawer)lastTouch=Time.unscaledTime;
            int interval=Time.unscaledTime-lastTouch>=IdleRenderDelay?IdleRenderInterval:1;
            if(UnityEngine.Rendering.OnDemandRendering.renderFrameInterval!=interval)UnityEngine.Rendering.OnDemandRendering.renderFrameInterval=interval;
        }
        static void MoveToBackground(){
#if UNITY_ANDROID && !UNITY_EDITOR
            try{using(var player=new AndroidJavaClass("com.unity3d.player.UnityPlayer"))using(var activity=player.GetStatic<AndroidJavaObject>("currentActivity"))activity.Call<bool>("moveTaskToBack",true);}catch(Exception){}
#endif
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
            if(committedReveal)CancelRewardReveal();
            string focus="";
            if(EventSystem.current && EventSystem.current.currentSelectedGameObject)
                foreach(var p in actions)if(p.Value.gameObject==EventSystem.current.currentSelectedGameObject){focus=p.Key;break;}
            foreach(Transform child in content){child.gameObject.SetActive(false);Destroy(child.gameObject);}
            nodes.Clear();actions.Clear();selectedAvatar=null;
            if(headerSprites==null)headerSprites=new HomeHeaderSprites(assets.Find("R4_Header"));
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
                    if(e.id=="avatar-slot")r.gameObject.AddComponent<RectMask2D>();
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
                    LabelFit.Apply(label,e.width,e.height,minimum);
                    if(label.preferredWidth>e.width)
                    {
                        string original=e.text;
                        while(original.Length>1 && label.preferredWidth>e.width)
                        {original=original.Substring(0,original.Length-1);label.text=original+"…";}
                    }
                    if(e.id=="life-count"||e.id=="life-refill-status"){label.text=e.text;label.fontSize=e.fontSize;label.verticalOverflow=VerticalWrapMode.Overflow;}
                    if(e.shadow){var shadow=r.gameObject.AddComponent<Shadow>();shadow.effectColor=new Color(0,.035f,.08f,.9f);shadow.effectDistance=new Vector2(0,-1);}
                }
                else
                {
                    var im=r.gameObject.AddComponent<Image>();im.raycastTarget=false;im.color=Parse(e.color);
                    if(e.kind=="sprite")
                    {im.sprite=e.asset=="HomeHeaderPanel"?headerSprites.Panel:e.asset=="HomeHeaderDefaultAvatar"?headerSprites.DefaultAvatar:e.asset=="HomeHeaderConnector"?headerSprites.Connector:assets.Find(e.asset);im.type=e.sliced?Image.Type.Sliced:Image.Type.Simple;im.preserveAspect=e.preserveAspect;if(e.asset=="HomeHeaderConnector")r.sizeDelta+=new Vector2(2/scale,0); // Cover the shared edge beneath the wallet in framebuffer pixels.
                        SpriteFit.Center(im);im.pixelsPerUnitMultiplier=e.sliced?(e.asset.StartsWith("Nav_",StringComparison.Ordinal)?4:e.height>100?3:im.sprite.rect.height/Mathf.Max(1,e.height)):1;}
                }
            }
            if(drawer)PageBackdrop90.Fill(nodes["drawer-shade"].GetComponent<MaskableGraphic>(),canvas);
            RenderHomeAvatar();
            if(LifeFeedback)LifeFeedback.Bind(nodes["header"],nodes["life-count"].GetComponent<Text>(),nodes["life-refill-status"].GetComponent<Text>());
            // Shared button feedback transforms only child visuals, leaving anchors and touch bounds fixed.
            foreach(var button in actions.Values)button.GetComponent<HomeButtonFeedback>().CaptureVisuals();
            MainNavigationFeedback.Bind(nodes,state.reduceMotion);
            // All portrait viewports share the approved Chapter 1 artwork and cover crop.
            Sprite art=backgroundOverride?backgroundOverride:assets.Find(frame.landscape?(sw/sh>2?"Chapter01_VillageWell_Ultrawide":"Chapter01_VillageWell_Landscape"):"Chapter01_VillageWell");
            if(art)
            {
                background.texture=art.texture;
                // Artwork fills the display; only interactive content is clipped to the safe area.
                float bw=Screen.width/scale,bh=Screen.height/scale;
                float cover=Mathf.Max(bw/art.rect.width,bh/art.rect.height);
                float artW=art.rect.width*cover,artH=art.rect.height*cover;
                Rect tr=art.textureRect;
                // The revised portrait composition keeps the face below the HUD when top-aligned.
                float verticalAnchor=!frame.landscape&&!backgroundOverride?1f:.5f;
                background.uvRect=new Rect((tr.x+(1-bw/artW)*tr.width/2)/art.texture.width,
                    (tr.y+(1-bh/artH)*tr.height*verticalAnchor)/art.texture.height,
                    bw/artW*tr.width/art.texture.width,bh/artH*tr.height/art.texture.height);
                Place(background.rectTransform,0,0,bw,bh);
            }
            previousSize=new Vector2Int(Screen.width,Screen.height);previousSafe=Screen.safeArea;previousScale=scale;
            if(!string.IsNullOrEmpty(focus))Focus(focus);
        }
        private void RenderHomeAvatar()
        {
            RectTransform host;if(!nodes.TryGetValue("avatar-slot",out host))return;
            if(selectedAvatar){selectedAvatar.gameObject.SetActive(false);Destroy(selectedAvatar.gameObject);selectedAvatar=null;}
            bool custom=profileAvatar&&profileFrame&&profileMask;
            RectTransform fallback;if(nodes.TryGetValue("avatar-default",out fallback))fallback.gameObject.SetActive(!custom);
            if(!custom)return;
            float width=host.sizeDelta.y,height=host.sizeDelta.y;
            selectedAvatar=Rect("Selected profile avatar",host);
            Place(selectedAvatar,0,0,width,height);
            var crop=Rect("Portrait crop",selectedAvatar);
            crop.anchorMin=new Vector2(.057f,.057f);crop.anchorMax=new Vector2(.943f,.943f);crop.offsetMin=Vector2.zero;crop.offsetMax=Vector2.zero;
            var cropImage=crop.gameObject.AddComponent<Image>();cropImage.sprite=profileMask;cropImage.raycastTarget=false;crop.gameObject.AddComponent<Mask>().showMaskGraphic=false;
            float cropW=width*.886f,cropH=height*.886f;
            float cover=Mathf.Max(cropW/profileAvatar.rect.width,cropH/profileAvatar.rect.height);
            float portraitW=profileAvatar.rect.width*cover,portraitH=profileAvatar.rect.height*cover;
            var portrait=Rect("Portrait",crop);Place(portrait,(cropW-portraitW)/2,(cropH-portraitH)/2,portraitW,portraitH);
            var image=portrait.gameObject.AddComponent<Image>();image.sprite=profileAvatar;image.raycastTarget=false;
            var top=Rect("Profile frame",selectedAvatar);top.anchorMin=Vector2.zero;top.anchorMax=Vector2.one;top.offsetMin=Vector2.zero;top.offsetMax=Vector2.zero;
            var frameImage=top.gameObject.AddComponent<Image>();frameImage.sprite=profileFrame;frameImage.raycastTarget=false;
        }
        private void Focus(string id)
        {Button b;if(EventSystem.current && actions.TryGetValue(id,out b)&&b.interactable)EventSystem.current.SetSelectedGameObject(b.gameObject);}
        private static Color Parse(string value){Color c;return ColorUtility.TryParseHtmlString(value,out c)?c:Color.white;}
        private static RectTransform Rect(string name,Transform parent)
        {var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);return (RectTransform)go.transform;}
        private static void Place(RectTransform r,float x,float y,float w,float h)
        {r.anchorMin=r.anchorMax=r.pivot=new Vector2(0,1);r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(w,h);}
        private void OnDestroy(){if(headerSprites!=null)headerSprites.Dispose();if(ownedEvents)Destroy(ownedEvents.gameObject);}
    }
}

using System;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;

namespace HeartOfTheRain.App.GameplayLoading {
    // Presentation only. Reservations, starting items and failures belong to HomeLevelFlow/profile services.
    public sealed class GameplayLoadingPage:MonoBehaviour {
        public HomePage home;public Font font;public GameplayLoadingAssets art;
        public Action RetryRequested,BackRequested;
        Canvas canvas;CanvasGroup group;RectTransform safe,diagram;Text title,status,detail;Image pattern;
        readonly Text[] dots=new Text[3];Button retry,back;Vector2Int size;Rect safeArea;float scale;int locale=-1;
        string tip="",lastTip="";bool failed;float began;static int consumedFrame=-1;
        // The frame in which the failure screen answered Escape/back, so the pre-level it re-shows does not close on the same press.
        public static bool ConsumedInputThisFrame=>consumedFrame==Time.frameCount;
        public bool IsVisible=>canvas&&canvas.gameObject.activeSelf;
        public bool IsFailure=>IsVisible&&failed;
        public string Tip=>tip;
        public string LastAnnouncement {get;private set;}
        public event Action<string> Announcement;
        public bool DecorativeReady=>art&&art.Find("LT_Background")&&art.Find("LT_RainPattern");

        public void Prepare(){Build();Hide();}
        public void Begin(bool hints,bool rainEligible,bool orbEligible,bool keepTip=false){
            Build();if(!keepTip){tip=SelectTip(hints,rainEligible,orbEligible,lastTip);if(tip!="")lastTip=tip;}
            failed=false;began=Time.unscaledTime;canvas.gameObject.SetActive(true);Reflow();Announce(GameplayLoadingText.T("loading"));
        }
        // The current M46 rules permit both kinds from the first board (no progression unlock table).
        // Explicit eligibility arguments keep the presentation ready for an authoritative unlock source.
        public static string SelectTip(bool hints,bool rain,bool orb,string last){if(!hints)return "";if(rain&&orb)return last=="rain"?"orb":"rain";return rain?"rain":orb?"orb":"";}
        public void ShowFailure(){Build();canvas.gameObject.SetActive(true);failed=true;Reflow();Announce(GameplayLoadingText.T("error"));}
        public void Hide(){if(canvas)canvas.gameObject.SetActive(false);failed=false;}
        // Art arrives or leaves while the overlay exists: rebuild the bound images, keeping the visible state.
        public void Rebuild(){if(!canvas)return;bool visible=IsVisible;canvas.gameObject.SetActive(false);Destroy(canvas.gameObject);canvas=null;Build();canvas.gameObject.SetActive(visible);if(visible)Reflow();}
        void Announce(string value){LastAnnouncement=value;Announcement?.Invoke(value);}
        void Build(){
            if(canvas)return;var root=Rect("Gameplay Loading Canvas",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=280;
#if UNITY_2022_3_OR_NEWER
            canvas.vertexColorAlwaysGammaSpace=true;
#endif
            root.gameObject.AddComponent<CanvasScaler>().uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;
            root.gameObject.AddComponent<GraphicRaycaster>();group=root.gameObject.AddComponent<CanvasGroup>();group.alpha=1;
            var bg=CreateImage("Sapphire background",root,"LT_Background");Stretch(bg.rectTransform);bg.color=bg.sprite?Color.white:new Color(.025f,.12f,.3f);bg.raycastTarget=true;
            pattern=CreateImage("Raindrops",root,"LT_RainPattern");Stretch(pattern.rectTransform);pattern.type=Image.Type.Tiled;pattern.pixelsPerUnitMultiplier=1;pattern.gameObject.SetActive(pattern.sprite);pattern.raycastTarget=false;
            safe=Rect("Safe area",root);title=Label("Power-up tip",safe,40);title.color=new Color(1,.953f,.851f);title.resizeTextForBestFit=true;title.resizeTextMinSize=24;title.resizeTextMaxSize=40;
            var outline=title.gameObject.AddComponent<Outline>();outline.effectColor=new Color(.043f,.18f,.357f);outline.effectDistance=new Vector2(1,-1);
            diagram=Rect("Static ability diagram",safe);status=Label("Loading status",safe,26);status.resizeTextForBestFit=true;status.resizeTextMinSize=16;status.resizeTextMaxSize=26;
            // The animated dots live on a nested canvas so their per-frame alpha does not re-batch the whole overlay during the prewarm.
            var dotsRoot=Rect("Loading dots",safe);Stretch(dotsRoot);dotsRoot.gameObject.AddComponent<Canvas>();
            for(int i=0;i<3;i++){dots[i]=Label("Decorative dot "+i,dotsRoot,26);dots[i].text=".";}
            detail=Label("Recovery detail",safe,18);detail.resizeTextForBestFit=true;detail.resizeTextMinSize=14;detail.resizeTextMaxSize=18;
            retry=Button("Retry loading",safe,"GL_Primary",()=>{if(IsFailure)RetryRequested?.Invoke();});back=Button("Back to level",safe,"GL_Secondary",()=>{if(IsFailure)BackRequested?.Invoke();});
        }
        void Update(){
            if(!IsVisible)return;
            if(size.x!=Screen.width||size.y!=Screen.height||safeArea!=Screen.safeArea||Math.Abs(scale-home.CurrentUIScale)>.01f||locale!=GameLocale.Current)Reflow();
            for(int i=0;i<3;i++){var c=dots[i].color;c.a=home.State.reduceMotion?1:DotAlpha(Time.unscaledTime-began,i);dots[i].color=c;}
            // Recovery alone can go back. No cancellation while a reservation is unresolved.
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
            bool escape=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
            bool escape=Input.GetKeyDown(KeyCode.Escape);
#endif
            if(failed&&escape){consumedFrame=Time.frameCount;BackRequested?.Invoke();}
        }
        public static float DotAlpha(float elapsed,int index){float t=Mathf.Repeat((elapsed-index*.16f)/1.2f,1);if(t<.28f)return Mathf.Lerp(.3f,1,t/.28f);if(t<.48f)return 1;if(t<.75f)return Mathf.Lerp(1,.3f,(t-.48f)/.27f);return .3f;}
        void Reflow(){
            if(!canvas)return;scale=home.CurrentUIScale;canvas.GetComponent<CanvasScaler>().scaleFactor=scale;canvas.scaleFactor=scale;
            var r=Screen.safeArea;if(r.width<=0||r.height<=0)r=new Rect(0,0,Screen.width,Screen.height);safeArea=Screen.safeArea;size=new Vector2Int(Screen.width,Screen.height);locale=GameLocale.Current;
            float w=r.width/scale,h=r.height/scale;Place(safe,r.x/scale,(Screen.height-r.yMax)/scale,w,h);bool wide=w/h>=1.18f;
            float dw=Mathf.Min(360,w-28),dh=dw*2/3,tx=18,tw=w-36,ty=h*.19f,dy=Mathf.Max(h*.5f-dh/2,ty+100),dx=(w-dw)/2,fy=failed?h-222:Mathf.Min(h*.87f,h-66);
            if(wide){dw=Mathf.Min(300,w*.44f,(h-30)*1.5f);dh=dw*2/3;tw=Mathf.Min(360,w-dw-54);dx=(w-dw-24-tw)/2;tx=dx+dw+24;ty=(h-(failed?298:148))/2;fy=ty+96;dy=(h-dh)/2;}
            bool showTip=tip!=""&&art&&art.Find(tip=="rain"?"Rain_Seeker_Original":"Rainbow_Orb_Original");
            if(failed&&!wide){float available=fy-16-dy;dw=Mathf.Min(dw,Mathf.Max(0,available)*1.5f);dh=dw*2/3;dx=(w-dw)/2;if(dh<120)showTip=false;}
            title.gameObject.SetActive(showTip);diagram.gameObject.SetActive(showTip);title.text=GameplayLoadingText.T(tip);title.resizeTextMaxSize=wide?34:Mathf.Min(40,Mathf.FloorToInt(w*.104f));Place(title.rectTransform,tx,ty,tw,wide?76:84);
            Place(diagram,dx,dy,360,240);diagram.localScale=Vector3.one*(dw/360);BuildDiagram();
            string label=GameplayLoadingText.T(failed?"error":"loading");status.text=label;status.resizeTextMaxSize=failed?22:26;
            float sw=Mathf.Min(tw-(failed?0:30),status.preferredWidth+4);float sx=tx+(tw-sw-(failed?0:26))/2;Place(status.rectTransform,sx,fy,sw,42);
            for(int i=0;i<3;i++){dots[i].gameObject.SetActive(!failed);Place(dots[i].rectTransform,sx+sw+i*8,fy,8,42);}
            detail.text=GameplayLoadingText.T("detail");detail.gameObject.SetActive(failed);Place(detail.rectTransform,tx,fy+42,tw,32);
            retry.gameObject.SetActive(failed);back.gameObject.SetActive(failed);float bw=Mathf.Min(280,tw);Place(retry.GetComponent<RectTransform>(),tx+(tw-bw)/2,fy+82,bw,48);Place(back.GetComponent<RectTransform>(),tx+(tw-bw)/2,fy+139,bw,48);
            SetButton(retry,GameplayLoadingText.T("retry"));SetButton(back,GameplayLoadingText.T("back"));
            // Fixed decorative dots are excluded from announcements; no percentage is invented.
            var tipLabel=diagram.GetComponent<HomeControlLabel>();if(!tipLabel)tipLabel=diagram.gameObject.AddComponent<HomeControlLabel>();tipLabel.action="loading-tip";tipLabel.label=showTip?GameplayLoadingText.T(tip=="rain"?"rainAlt":"orbAlt"):"";
        }
        void BuildDiagram(){
            foreach(Transform child in diagram){child.gameObject.SetActive(false);Destroy(child.gameObject);}if(!diagram.gameObject.activeSelf)return;
            Art("Original power-up",tip=="rain"?"Rain_Seeker_Original":"Rainbow_Orb_Original",4,64,146,146);
            string[] tiles=tip=="rain"?new[]{"Water_Drop","Leaf","Ribbon","Stone_Rune","Water_Drop","Leaf","Ribbon","Leaf","Water_Drop"}:new[]{"Stone_Rune","Water_Drop","Ribbon","Leaf","Stone_Rune","Water_Drop","Ribbon","Leaf","Stone_Rune"};
            for(int i=0;i<9;i++){float x=198+i%3*49,y=56+i/3*49;Art("Cell "+i,"LT_Tip_Cell",x,y,46,46,true);Art("Tile "+i,"TILE_"+tiles[i]+"_V2",x+3,y+3,40,40);}
            if(tip=="rain")Art("Flight arrow","LT_Flight_Arrow",132,96,72,29);else Art("Color links","LT_Orb_Links",0,0,360,240);
            foreach(int i in tip=="rain"?new[]{3}:new[]{0,4,8})Art("Target "+i,"LT_Target",196+i%3*49,54+i/3*49,50,50,true);
        }
        void Art(string name,string key,float x,float y,float w,float h,bool sliced=false){var im=CreateImage(name,diagram,key);Place(im.rectTransform,x,y,w,h);im.type=sliced?Image.Type.Sliced:Image.Type.Simple;im.pixelsPerUnitMultiplier=1;im.preserveAspect=!sliced;im.raycastTarget=false;}
        Image CreateImage(string name,Transform parent,string key){var rt=Rect(name,parent);var im=rt.gameObject.AddComponent<Image>();im.sprite=art?art.Find(key):null;im.raycastTarget=false;if(!im.sprite)im.color=Color.clear;return im;}
        Text Label(string name,Transform parent,int fontSize){var rt=Rect(name,parent);var t=rt.gameObject.AddComponent<Text>();t.font=font;t.fontSize=fontSize;t.alignment=TextAnchor.MiddleCenter;t.color=new Color(1,.953f,.851f);t.raycastTarget=false;t.supportRichText=false;t.horizontalOverflow=HorizontalWrapMode.Wrap;t.verticalOverflow=VerticalWrapMode.Truncate;return t;}
        Button Button(string name,Transform parent,string key,Action action){var im=CreateImage(name,parent,key);im.type=Image.Type.Sliced;im.pixelsPerUnitMultiplier=1;im.raycastTarget=true;var b=im.gameObject.AddComponent<Button>();b.targetGraphic=im;b.onClick.AddListener(()=>action());var text=Label("Label",im.transform,16);Stretch(text.rectTransform);im.gameObject.AddComponent<HomeControlLabel>();return b;}
        static void SetButton(Button b,string label){b.GetComponentInChildren<Text>().text=label;var a=b.GetComponent<HomeControlLabel>();a.label=label;a.action=b.name;}
        static RectTransform Rect(string name,Transform parent){var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);return (RectTransform)go.transform;}
        static void Stretch(RectTransform r){r.anchorMin=Vector2.zero;r.anchorMax=Vector2.one;r.offsetMin=r.offsetMax=Vector2.zero;}
        static void Place(RectTransform r,float x,float y,float w,float h){r.anchorMin=r.anchorMax=r.pivot=new Vector2(0,1);r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(w,h);}
        void OnDestroy(){if(canvas)Destroy(canvas.gameObject);}
    }
}

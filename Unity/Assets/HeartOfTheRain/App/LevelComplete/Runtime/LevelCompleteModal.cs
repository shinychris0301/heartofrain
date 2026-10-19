using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.Celebrations;
using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.PreLevel;
namespace HeartOfTheRain.App.LevelComplete
{
    public sealed class LevelCompleteModal:MonoBehaviour
    {
        public LevelCompleteAssets assets;public HomePage home;public Action<string> Requested;
        Canvas canvas;CanvasScaler scaler;RectTransform safe,content;ScrollRect scroll;CanvasGroup fade;float elapsed;bool focused=true,suspended;int localeRevision=-1;
        DariaCelebrationView daria;CelebrationAssets celebrationAssets;
        LevelCompleteViewData data;Vector2Int lastSize;Rect lastSafe;float lastScale,opened;Vector2 panelOrigin;
        readonly Dictionary<string,RectTransform> nodes=new Dictionary<string,RectTransform>();
        public bool IsVisible {get{return canvas&&canvas.gameObject.activeSelf;}}
        public void Show(LevelCompleteViewData state)
        {
            data=state;celebrationAssets=CelebrationAssets.Load();
            if(!canvas)
            {
                var root=Rect("Level Complete Canvas",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=230;
#if UNITY_2022_3_OR_NEWER
                canvas.vertexColorAlwaysGammaSpace=true;
#endif
                scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;
                root.gameObject.AddComponent<GraphicRaycaster>();fade=root.gameObject.AddComponent<CanvasGroup>();
                var dim=Rect("Modal shade",root);dim.anchorMin=Vector2.zero;dim.anchorMax=Vector2.one;dim.sizeDelta=Vector2.zero;
                var shade=dim.gameObject.AddComponent<Image>();shade.color=new Color(.02f,.04f,.08f,.74f);shade.raycastTarget=true;
                safe=Rect("Safe area",root);safe.gameObject.AddComponent<RectMask2D>();scroll=safe.gameObject.AddComponent<ScrollRect>();scroll.viewport=safe;scroll.movementType=ScrollRect.MovementType.Clamped;
                content=Rect("Modal content",safe);scroll.content=content;
            }
            bool wasVisible=canvas.gameObject.activeSelf&&opened>0;canvas.gameObject.SetActive(true);if(!wasVisible){opened=Time.unscaledTime;elapsed=state.chapterComplete?3:0;}
            Reflow();
        }
        public void Hide(){if(canvas)canvas.gameObject.SetActive(false);opened=0;}
        void Update()
        {
            if(!IsVisible)return;
            if(localeRevision!=GameLocale.Revision||lastSize.x!=Screen.width||lastSize.y!=Screen.height||lastSafe!=Screen.safeArea||Mathf.Abs(lastScale-Scale())>.01f)Reflow();
            if(focused&&!suspended)elapsed+=Time.unscaledDeltaTime;
            Animate();RevealFocus();
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
            bool back=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
            bool back=Input.GetKeyDown(KeyCode.Escape);
#endif
            if(back&&!ChapterCelebrationPlayer.ConsumedInputThisFrame)Requested?.Invoke("home");
        }
        void Reflow()
        {
            float scrollPosition=scroll.verticalNormalizedPosition;string focusedAction="continue";
            if(EventSystem.current&&EventSystem.current.currentSelectedGameObject){var label=EventSystem.current.currentSelectedGameObject.GetComponent<HomeControlLabel>();if(label)focusedAction=label.action;}
            foreach(Transform t in content){t.gameObject.SetActive(false);Destroy(t.gameObject);}nodes.Clear();
            float scale=Scale();scaler.scaleFactor=scale;canvas.scaleFactor=scale;
            var r=Screen.safeArea;if(r.width<=0||r.height<=0)r=new Rect(0,0,Screen.width,Screen.height);
            float w=r.width/scale,h=r.height/scale;Place(safe,r.x/scale,(Screen.height-r.yMax)/scale,w,h);
            var frame=LevelCompleteLayout.Build(w,h,data);Place(content,0,0,frame.width,frame.height);
            scroll.horizontal=frame.width>w+.1f;scroll.vertical=frame.height>h+.1f;scroll.enabled=scroll.horizontal||scroll.vertical;
            scroll.horizontalNormalizedPosition=0;scroll.verticalNormalizedPosition=scrollPosition;
            foreach(var e in frame.elements)
            {
                var parent=string.IsNullOrEmpty(e.parent)?content:nodes[e.parent];var rt=Rect(e.id,parent);Place(rt,e.x,e.y,e.width,e.height);nodes.Add(e.id,rt);
                if(e.kind=="group")
                {
                    if(string.IsNullOrEmpty(e.action))continue;
                    var hit=rt.gameObject.AddComponent<Image>();hit.color=Color.clear;
                    var b=rt.gameObject.AddComponent<Button>();b.targetGraphic=hit;b.transition=Selectable.Transition.None;b.interactable=true;
                    string action=e.action;b.onClick.AddListener(()=>Requested?.Invoke(action));
                    var a=rt.gameObject.AddComponent<HomeControlLabel>();a.action=action;a.label=e.label;
                }
                else if(e.kind=="daria")
                {daria=rt.gameObject.AddComponent<DariaCelebrationView>();if(celebrationAssets)daria.Configure(celebrationAssets.dariaAtlas);}
                else if(e.kind=="text")
                {
                    var t=rt.gameObject.AddComponent<Text>();t.font=assets.preLevel.home.boldFont;t.text=e.text;t.color=ColorOf(e.color);t.fontSize=e.fontSize;
                    t.alignment=TextAnchor.MiddleCenter;t.raycastTarget=false;t.supportRichText=false;t.horizontalOverflow=HorizontalWrapMode.Overflow;t.verticalOverflow=VerticalWrapMode.Truncate;
                    while(t.fontSize>10&&t.preferredWidth>e.width)t.fontSize--;
                    if(e.shadow){var shadow=rt.gameObject.AddComponent<Shadow>();shadow.effectColor=new Color(0,.025f,.06f,.9f);shadow.effectDistance=new Vector2(0,-1);}
                }
                else
                {
                    var im=rt.gameObject.AddComponent<Image>();im.sprite=assets.Find(e.asset);im.color=ColorOf(e.color);im.raycastTarget=false;
                    im.type=e.sliced?Image.Type.Sliced:Image.Type.Simple;im.preserveAspect=e.preserveAspect;im.pixelsPerUnitMultiplier=e.sliced?4:1;
                }
            }
            // Art and labels deliberately stay siblings so they can share exported geometry.
            foreach(var e in frame.elements)if(!string.IsNullOrEmpty(e.action))
            {
                var visuals=new List<Graphic>();
                foreach(var pair in nodes)if(pair.Key.StartsWith(e.id+"-",StringComparison.Ordinal))
                {var graphic=pair.Value.GetComponent<Graphic>();if(graphic)visuals.Add(graphic);}
                nodes[e.id].gameObject.AddComponent<PreLevelButtonFeedback>().Configure(visuals.ToArray(),home.State.reduceMotion);
            }
            foreach(var id in new[]{"halo","hero-star"}){var heroRect=nodes[id];var size=heroRect.sizeDelta;heroRect.pivot=new Vector2(.5f,.5f);heroRect.anchoredPosition+=new Vector2(size.x/2,-size.y/2);}
            for(int i=0;i<18;i++)nodes["spark-"+i].pivot=new Vector2(.5f,.5f);
            panelOrigin=nodes["panel"].anchoredPosition;
            if(EventSystem.current)EventSystem.current.SetSelectedGameObject(nodes[focusedAction=="home"?"home":"continue"].gameObject);
            lastSize=new Vector2Int(Screen.width,Screen.height);lastSafe=Screen.safeArea;lastScale=scale;localeRevision=GameLocale.Revision;Animate();
        }
        float Scale(){var r=Screen.safeArea;if(r.width<=0)r=new Rect(0,0,Screen.width,Screen.height);return Mathf.Min(home.CurrentUIScale,Mathf.Max(.3f,r.width/320),Mathf.Max(.3f,r.height/320));}
        void Animate(){if(!nodes.ContainsKey("hero"))return;var p=LevelCompleteMotion.Sample(elapsed,home.State.reduceMotion||data.chapterComplete);if(daria)daria.Sample(elapsed,data.level,home.State.reduceMotion||data.chapterComplete);fade.alpha=p.alpha;nodes["hero-star"].localScale=Vector3.one*p.starScale;nodes["halo"].localRotation=Quaternion.Euler(0,0,-p.haloAngle);nodes["halo"].GetComponent<Image>().color=new Color(1,1,1,p.haloAlpha);var hero=nodes["hero"].sizeDelta;
            for(int i=0;i<18;i++){var r=nodes["spark-"+i];var v=p.particles[i];r.anchoredPosition=new Vector2(hero.x/2+v.x,-hero.y*.43f-v.y);r.localScale=Vector3.one*v.scale;r.localRotation=Quaternion.Euler(0,0,-v.angle);r.GetComponent<Image>().color=new Color(1,1,1,v.alpha);}
            nodes["reward-count-0"].GetComponent<Text>().text="+"+(int)Math.Min(int.MaxValue,Math.Round((double)data.coins*p.reward));nodes["reward-count-1"].GetComponent<Text>().text="+"+(int)Math.Min(int.MaxValue,Math.Round((double)data.stars*p.reward));
            float before=Mathf.Clamp(data.completedBefore-(data.chapter-1)*50,0,50),after=Mathf.Clamp(data.completedAfter-(data.chapter-1)*50,0,50);float value=Mathf.Lerp(before,after,p.progress);var track=nodes["progress-track"];var fill=nodes["progress-fill"];fill.sizeDelta=new Vector2(Mathf.Max(.01f,(track.sizeDelta.x-4)*value/50),9);nodes["progress-count"].GetComponent<Text>().text=Mathf.RoundToInt(value)+" / 50";
        }
        GameObject priorFocus;void RevealFocus(){if(!EventSystem.current)return;var go=EventSystem.current.currentSelectedGameObject;if(!go||go==priorFocus)return;priorFocus=go;var rt=go.transform as RectTransform;if(!rt||!rt.IsChildOf(content))return;Canvas.ForceUpdateCanvases();var bounds=RectTransformUtility.CalculateRelativeRectTransformBounds(safe,rt);float delta=bounds.max.y>safe.rect.yMax?bounds.max.y-safe.rect.yMax:bounds.min.y<safe.rect.yMin?bounds.min.y-safe.rect.yMin:0;var pos=content.anchoredPosition;pos.y=Mathf.Clamp(pos.y+delta,0,Mathf.Max(0,content.rect.height-safe.rect.height));content.anchoredPosition=pos;}
        void OnApplicationPause(bool value){suspended=value;}void OnApplicationFocus(bool value){focused=value;}
        static Color ColorOf(string value){Color c;return ColorUtility.TryParseHtmlString(value,out c)?c:Color.white;}
        static RectTransform Rect(string name,Transform parent){var g=new GameObject(name,typeof(RectTransform));g.transform.SetParent(parent,false);return (RectTransform)g.transform;}
        static void Place(RectTransform r,float x,float y,float w,float h){r.anchorMin=r.anchorMax=r.pivot=new Vector2(0,1);r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(w,h);}
    }
}

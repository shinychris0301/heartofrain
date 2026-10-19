using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.PreLevel;
namespace HeartOfTheRain.App.EndLevel
{
    public sealed class EndLevelModal:MonoBehaviour
    {
        public EndLevelAssets assets;public HomePage home;public Action<string> Requested;
        Canvas canvas;CanvasScaler scaler;RectTransform safe,content;ScrollRect scroll;CanvasGroup fade;
        EndLevelViewData data;Vector2Int lastSize;Rect lastSafe;float lastScale,opened;Vector2 panelOrigin;
        readonly Dictionary<string,RectTransform> nodes=new Dictionary<string,RectTransform>();
        public bool IsVisible {get{return canvas&&canvas.gameObject.activeSelf;}}
        public void Show(EndLevelViewData state)
        {
            data=state;
            if(!canvas)
            {
                var root=Rect("End Level Canvas",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=230;
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
            bool wasVisible=canvas.gameObject.activeSelf&&opened>0;canvas.gameObject.SetActive(true);if(!wasVisible)opened=Time.unscaledTime;
            Reflow();
        }
        public void Hide(){if(canvas)canvas.gameObject.SetActive(false);opened=0;}
        void Update()
        {
            if(!IsVisible)return;
            if(lastSize.x!=Screen.width||lastSize.y!=Screen.height||lastSafe!=Screen.safeArea||Mathf.Abs(lastScale-home.CurrentUIScale)>.01f)Reflow();
            float progress=home.State.reduceMotion?1:Mathf.Clamp01((Time.unscaledTime-opened)/.22f);
            fade.alpha=Mathf.Min(1,progress*1.5f);
            RectTransform panel;if(nodes.TryGetValue("panel",out panel))panel.anchoredPosition=panelOrigin+new Vector2(0,-8*Mathf.Pow(1-progress,3));
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
            bool back=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
            bool back=Input.GetKeyDown(KeyCode.Escape);
#endif
            if(back)Requested?.Invoke("cancel");
        }
        void Reflow()
        {
            foreach(Transform t in content){t.gameObject.SetActive(false);Destroy(t.gameObject);}nodes.Clear();
            float scale=home.CurrentUIScale;scaler.scaleFactor=scale;canvas.scaleFactor=scale;
            var r=Screen.safeArea;if(r.width<=0||r.height<=0)r=new Rect(0,0,Screen.width,Screen.height);
            float w=r.width/scale,h=r.height/scale;Place(safe,r.x/scale,(Screen.height-r.yMax)/scale,w,h);
            var frame=EndLevelLayout.Build(w,h,data);Place(content,0,0,frame.width,frame.height);
            scroll.horizontal=frame.width>w+.1f;scroll.vertical=frame.height>h+.1f;scroll.enabled=scroll.horizontal||scroll.vertical;
            scroll.horizontalNormalizedPosition=0;scroll.verticalNormalizedPosition=1;
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
                else if(e.kind=="text")
                {
                    var t=rt.gameObject.AddComponent<Text>();t.font=assets.approvedSettings.approvedUI.home.boldFont;t.text=e.text;t.color=ColorOf(e.color);t.fontSize=e.fontSize;
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
            panelOrigin=nodes["panel"].anchoredPosition;
            if(EventSystem.current)EventSystem.current.SetSelectedGameObject(nodes["keep"].gameObject);
            lastSize=new Vector2Int(Screen.width,Screen.height);lastSafe=Screen.safeArea;lastScale=scale;
        }
        static Color ColorOf(string value){Color c;return ColorUtility.TryParseHtmlString(value,out c)?c:Color.white;}
        static RectTransform Rect(string name,Transform parent){var g=new GameObject(name,typeof(RectTransform));g.transform.SetParent(parent,false);return (RectTransform)g.transform;}
        static void Place(RectTransform r,float x,float y,float w,float h){r.anchorMin=r.anchorMax=r.pivot=new Vector2(0,1);r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(w,h);}
    }
}

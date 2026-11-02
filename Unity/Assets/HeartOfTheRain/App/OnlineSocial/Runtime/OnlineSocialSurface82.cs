using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.PreLevel;

namespace HeartOfTheRain.App.OnlineSocial
{
    // Shared approved UGUI primitives for the connected player/friend component.
    // This is a presentation helper; it never receives credentials or balances.
    public sealed class OnlineSocialSurface82
    {
        public readonly Canvas canvas;public readonly ScrollRect scroll;
        public readonly Dictionary<string,RectTransform> nodes=new Dictionary<string,RectTransform>();
        readonly CanvasScaler scaler;readonly RectTransform safe,chrome,viewport,content,overlay;
        readonly Func<string,Sprite> find;readonly Font regular,bold;readonly Action<string> request;readonly Func<string,string> draft;readonly Action<string,string> changed;
        public OnlineSocialSurface82(Transform parent,Func<string,Sprite> art,Font regular,Font bold,Action<string> request,Func<string,string> draft,Action<string,string> changed) {
            find=art;this.regular=regular;this.bold=bold;this.request=request;this.draft=draft;this.changed=changed;
            var root=Rect("Connected Players Canvas82",parent);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=66;
#if UNITY_2022_3_OR_NEWER
            canvas.vertexColorAlwaysGammaSpace=true;
#endif
            scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;root.gameObject.AddComponent<GraphicRaycaster>();
            safe=Rect("Safe area",root);safe.gameObject.AddComponent<RectMask2D>();chrome=Rect("Chrome",safe);
            viewport=Rect("Viewport",safe);viewport.gameObject.AddComponent<Image>().color=Color.clear;viewport.gameObject.AddComponent<RectMask2D>();scroll=viewport.gameObject.AddComponent<ScrollRect>();scroll.viewport=viewport;scroll.horizontal=false;scroll.movementType=ScrollRect.MovementType.Clamped;scroll.scrollSensitivity=35;
            content=Rect("Content",viewport);scroll.content=content;overlay=Rect("Dialogs",safe);
        }
        float artScale115=1;
        HeartOfTheRain.App.TeamsAccess.TeamsAccessAssets109 access115;
        float Slice115(string id){if(!access115)access115=Resources.Load<HeartOfTheRain.App.TeamsAccess.TeamsAccessAssets109>("HOTR_TeamsAccess109/Assets");return access115?access115.SliceMultiplier(id,artScale115):4;}
        public void Apply(float width,float height,float scale,Rect physical,int physicalHeight,float viewportY,float viewportHeight,HomeFrame fixedFrame,HomeFrame body,HomeFrame dialog,bool modal,bool reduced,bool preserveTop=true,float position=1,float artScale=1,bool r3SliceScale118=false) {
            artScale115=artScale;
            float top=Math.Max(0,content.anchoredPosition.y);
            foreach(var root in new[]{chrome,content,overlay})foreach(Transform child in root.Cast<Transform>().ToArray()){child.gameObject.SetActive(false);if(Application.isPlaying)UnityEngine.Object.Destroy(child.gameObject);else UnityEngine.Object.DestroyImmediate(child.gameObject);}nodes.Clear();
            scaler.scaleFactor=scale;canvas.scaleFactor=scale;Place(safe,physical.x/scale,(physicalHeight-physical.yMax)/scale,width,height);
            Place(chrome,0,0,width,height);Place(overlay,0,0,width,height);Place(viewport,0,viewportY,width,viewportHeight);Place(content,0,0,width,body.height);
            Render(fixedFrame,chrome,reduced,r3SliceScale118);Render(body,content,reduced,r3SliceScale118);Render(dialog,overlay,reduced,false);
            foreach(var root in new[]{chrome,viewport}){var group=root.GetComponent<CanvasGroup>();if(!group)group=root.gameObject.AddComponent<CanvasGroup>();group.interactable=!modal;group.blocksRaycasts=!modal;}scroll.enabled=!modal;
            MainNavigationFeedback.Bind(nodes,reduced);Canvas.ForceUpdateCanvases();float range=Math.Max(0,body.height-viewportHeight);scroll.verticalNormalizedPosition=preserveTop?(range<.01f?1:1-Mathf.Clamp01(top/range)):position;
        }
        void Render(HomeFrame model,RectTransform root,bool reduced,bool r3SliceScale118) {
            foreach(var e in model.elements){var parent=string.IsNullOrEmpty(e.parent)?root:nodes[e.parent];var rt=Rect(e.id,parent);Place(rt,e.x,e.y,e.width,e.height);nodes[e.id]=rt;
                if(e.kind=="rankbody115"){var image=rt.gameObject.AddComponent<Image>();image.color=Color.clear;rt.gameObject.AddComponent<RectMask2D>();var inner=rt.gameObject.AddComponent<ScrollRect>();inner.viewport=rt;inner.horizontal=false;inner.movementType=ScrollRect.MovementType.Clamped;inner.scrollSensitivity=35;}
                else if(e.kind=="group") {if(string.IsNullOrEmpty(e.action))continue;var image=rt.gameObject.AddComponent<Image>();image.color=Color.clear;var button=rt.gameObject.AddComponent<Button>();button.targetGraphic=image;button.transition=Selectable.Transition.None;button.interactable=e.action!="disabled";string action=e.action;button.onClick.AddListener(()=>request(action));var label=rt.gameObject.AddComponent<HomeControlLabel>();label.action=action;label.label=e.label;}
                else if(e.kind=="input") {rt.gameObject.AddComponent<RectMask2D>();var image=rt.gameObject.AddComponent<Image>();image.color=Color.clear;var input=rt.gameObject.AddComponent<InputField>();input.targetGraphic=image;bool code=e.id=="online-player-code-input",country=e.id=="country-code-input";input.characterLimit=country?80:code?128:120;input.lineType=code||country?InputField.LineType.SingleLine:InputField.LineType.MultiLineNewline;
                    var tr=Rect("Text",rt);Place(tr,0,0,e.width,e.height);var text=tr.gameObject.AddComponent<Text>();text.font=regular;text.fontSize=e.fontSize;text.color=ColorOf(e.color);text.alignment=code?TextAnchor.MiddleLeft:TextAnchor.UpperLeft;text.supportRichText=false;text.raycastTarget=false;input.textComponent=text;
                    var ph=Rect("Placeholder",rt);Place(ph,0,0,e.width,e.height);var placeholder=ph.gameObject.AddComponent<Text>();placeholder.font=regular;placeholder.fontSize=e.fontSize;placeholder.text=e.label;placeholder.alignment=code?TextAnchor.MiddleLeft:TextAnchor.UpperLeft;placeholder.color=ColorOf("#73818B");placeholder.supportRichText=false;placeholder.raycastTarget=false;input.placeholder=placeholder;input.text=draft(e.id);input.onValueChanged.AddListener(value=>changed(e.id,value));}
                else if(e.kind=="text"||e.kind=="lefttext"||e.kind=="rankname115"||e.kind=="ranknameleft115"||e.kind=="paragraph") {var text=rt.gameObject.AddComponent<Text>();text.font=e.kind=="paragraph"?regular:bold;text.fontSize=e.fontSize;text.text=e.text;text.color=ColorOf(e.color);text.supportRichText=false;text.raycastTarget=false;text.horizontalOverflow=HorizontalWrapMode.Overflow;text.verticalOverflow=VerticalWrapMode.Truncate;text.alignment=e.kind=="paragraph"?TextAnchor.UpperLeft:(e.kind=="lefttext"||e.kind=="ranknameleft115")?TextAnchor.MiddleLeft:TextAnchor.MiddleCenter;
                    // This empty-state paragraph is a leaf, with no bubble or
                    // following rows to reposition. Reserve its actual font
                    // metric rather than assuming fontSize+6 fits each line.
                    if(e.id=="online-direct-empty"){float required=Mathf.Ceil(text.preferredHeight)+4;if(required>e.height){e.height=required;Place(rt,e.x,e.y,e.width,e.height);}}
                    if(e.kind!="paragraph")LabelFit.Apply(text,e.width,e.height,9);if(e.kind=="rankname115"||e.kind=="ranknameleft115"){rt.gameObject.AddComponent<RectMask2D>();Ellipsize115(text,e.width);}if(e.shadow){var shadow=rt.gameObject.AddComponent<Shadow>();shadow.effectColor=new Color(0,.02f,.05f,.8f);shadow.effectDistance=new Vector2(0,-1);}}
                else {var image=rt.gameObject.AddComponent<Image>();if(e.kind!="color")image.sprite=find(e.asset);image.color=ColorOf(e.color);image.type=e.sliced?Image.Type.Sliced:Image.Type.Simple;image.pixelsPerUnitMultiplier=e.sliced&&e.asset!=null&&e.asset.StartsWith("TA_",StringComparison.Ordinal)?Slice115(e.asset):e.sliced?4:1;
                    // The R3 source proof scales each border with the page.
                    // Slice115 already accounts for artScale, so extra corner
                    // shrinking or scale cancellation distorts tabs and cards.
                    image.preserveAspect=e.preserveAspect;image.raycastTarget=false;if(e.kind=="mask"){var mask=rt.gameObject.AddComponent<Mask>();mask.showMaskGraphic=false;}SpriteFit.Center(image);}
            }
            foreach(var e in model.elements)if(e.kind=="rankbody115"){RectTransform inner;if(nodes.TryGetValue(e.label,out inner))nodes[e.id].GetComponent<ScrollRect>().content=inner;}
            foreach(var e in model.elements)if(e.id=="online-players-background"||e.id=="online-player-modal-shade"||e.id=="country-shade")PageBackdrop90.Fill(nodes[e.id].GetComponent<MaskableGraphic>(),canvas);
            foreach(var e in model.elements)if(!string.IsNullOrEmpty(e.action)&&e.action!="disabled"&&!e.id.StartsWith("nav-",StringComparison.Ordinal)){var graphics=nodes.Where(pair=>pair.Key.StartsWith(e.id+"-",StringComparison.Ordinal)).Select(pair=>pair.Value.GetComponent<Graphic>()).Where(value=>value).ToArray();nodes[e.id].gameObject.AddComponent<PreLevelButtonFeedback>().Configure(graphics,reduced);}
        }
        // Limit untrusted names to their visual cell while retaining the full name in the action label.
        static void Ellipsize115(Text text,float width) {
            string original=text.text??"";if(original.Length==0||width<=0)return;
            var settings=text.GetGenerationSettings(new Vector2(width,10000));
            var generator=new TextGenerator();float pixels=text.pixelsPerUnit;
            if(generator.GetPreferredWidth(original,settings)/pixels<=width)return;
            int[] elements=System.Globalization.StringInfo.ParseCombiningCharacters(original);int lo=0,hi=elements.Length;
            while(lo<hi){int mid=(lo+hi+1)/2;int end=mid==elements.Length?original.Length:elements[mid];string candidate=original.Substring(0,end)+"...";
                if(generator.GetPreferredWidth(candidate,settings)/pixels<=width)lo=mid;else hi=mid-1;}
            int cut=lo==elements.Length?original.Length:elements[lo];text.text=original.Substring(0,cut)+"...";
        }
        // End-of-message visibility is a presentation observation, not a read
        // side effect of loading/caching HTTP. Long bodies qualify only once
        // their final line reaches the viewport; hidden/modalled pages do not.
        public static bool MessageEndVisible(ScrollRect view,IReadOnlyDictionary<string,RectTransform> elements,string messageId) {
            if(!view||!view.viewport||!view.enabled||!view.gameObject.activeInHierarchy||view.verticalNormalizedPosition>.02f)return false;
            RectTransform body;if(!elements.TryGetValue("online-message-"+messageId+"-body",out body)||!body.gameObject.activeInHierarchy)return false;
            var corners=new Vector3[4];body.GetWorldCorners(corners);var point=view.viewport.InverseTransformPoint((corners[0]+corners[3])/2);var area=view.viewport.rect;
            return point.x>=area.xMin-1&&point.x<=area.xMax+1&&point.y>=area.yMin-1&&point.y<=area.yMax+1;
        }
        static RectTransform Rect(string name,Transform parent){var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);return (RectTransform)go.transform;}
        static void Place(RectTransform rt,float x,float y,float w,float h){rt.anchorMin=rt.anchorMax=rt.pivot=new Vector2(0,1);rt.anchoredPosition=new Vector2(x,-y);rt.sizeDelta=new Vector2(w,h);}
        static Color ColorOf(string value){Color c;return ColorUtility.TryParseHtmlString(value,out c)?c:Color.white;}
    }
}

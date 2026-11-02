using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
namespace HeartOfTheRain.App.Home
{
    // Selection is driven by the current page after click/tap. Hover does not
    // reveal another panel. Every tab uses the same Home-derived panel asset.
    // The icon pulses inside a stationary selected frame; tint still animates
    // both. Label space and touch bounds stay fixed throughout the interaction.
    public sealed class MainNavigationFeedback : MonoBehaviour, IPointerDownHandler,
        IPointerUpHandler, IPointerExitHandler, IDeselectHandler
    {
        Button button; Graphic plate,icon; bool held,reduced,idle;string id;
        float amount;static string lastPressed;static float pressedAt=-10;
        public static void Bind(Dictionary<string,RectTransform> nodes,bool reducedMotion)
        {
            FitClippedViewport(nodes);
            foreach(string name in new[]{"journey","leaderboard","home","teams","shop"})
            {
                string id="nav-"+name;RectTransform hit,p,i;
                if(!nodes.TryGetValue(id,out hit)||!nodes.TryGetValue(id+"-plate",out p)||
                   !nodes.TryGetValue(id+"-icon",out i))continue;
                CenterPivot(p);CenterPivot(i);
                if(nodes.TryGetValue(id+"-label",out var label))FitLabel(label.GetComponent<Text>());
                var existing=hit.GetComponent<MainNavigationFeedback>();if(existing){existing.reduced=reducedMotion;continue;}
                var v=hit.gameObject.AddComponent<MainNavigationFeedback>();
                v.button=hit.GetComponent<Button>();v.plate=p.GetComponent<Graphic>();
                v.icon=i.GetComponent<Graphic>();
                v.id=id;v.reduced=reducedMotion;v.button.onClick.AddListener(()=>Pulse(id));
            }
        }
        static void CenterPivot(RectTransform rect)
        {
            if(rect.pivot==Vector2.one*.5f)return;
            Vector3 center=rect.TransformPoint(rect.rect.center);rect.pivot=Vector2.one*.5f;rect.position=center;
        }
        static void FitLabel(Text label)
        {
            if(!label)return;float width=label.rectTransform.rect.width,height=label.rectTransform.rect.height;
            if(height<10){label.text="";return;} // Keep the full accessible name; do not squeeze ink into an unreadable blue inset.
            LabelFit.Apply(label,width,height,9);var shadow=label.GetComponent<Shadow>();if(shadow)shadow.effectDistance=new Vector2(0,-Mathf.Min(1,height*.08f));
            if(label.preferredHeight>height+.01f){label.text="";return;}
            if(label.preferredWidth<=width)return;
            string text=label.text;while(text.Length>0&&label.preferredWidth>width){text=text.Substring(0,text.Length-1);label.text=text+"\u2026";}
            if(label.preferredWidth>width)label.text=""; // Full accessible name stays on the fixed hit target.
        }
        static void FitClippedViewport(Dictionary<string,RectTransform> nodes)
        {
            if(!nodes.TryGetValue("dock-bg",out var dock))return;
            var parent=dock.parent as RectTransform;var mask=dock.GetComponentInParent<RectMask2D>();if(!parent||!mask)return;
            var safe=mask.transform as RectTransform;float width=safe.rect.width,height=safe.rect.height;
            if(width<=0||height<=0||(parent.rect.width<=width+.01f&&parent.rect.height<=height+.01f))return;
            int active=-1;string[] names={"journey","leaderboard","home","teams","shop"};
            for(int n=0;n<names.Length;n++)if(nodes.TryGetValue("nav-"+names[n]+"-plate",out var p)&&p.GetComponent<Graphic>().color.a>.5f)active=n;
            var frame=new HomeFrame{width=width,height=height};MainNavigationLayout.AddDock(frame,width,height,active);
            Vector3 origin=parent.InverseTransformPoint(safe.TransformPoint(new Vector3(safe.rect.xMin,safe.rect.yMax,0)));
            float dx=origin.x-parent.rect.xMin,dy=parent.rect.yMax-origin.y;
            foreach(var e in frame.elements)if(nodes.TryGetValue(e.id,out var rect)){
                rect.anchorMin=rect.anchorMax=new Vector2(0,1);rect.sizeDelta=new Vector2(e.width,e.height);
                rect.anchoredPosition=new Vector2(dx+e.x+e.width*rect.pivot.x,-dy-e.y-e.height*(1-rect.pivot.y));
                var label=rect.GetComponent<Text>();if(label){label.text=e.text;label.fontSize=e.fontSize;FitLabel(label);}
            }
        }
        static void Pulse(string name){lastPressed=name;pressedAt=Time.unscaledTime;}
        public void OnPointerDown(PointerEventData e){if(button&&button.IsInteractable()){held=true;Pulse(id);}}
        public void OnPointerUp(PointerEventData e){held=false;}
        public void OnPointerExit(PointerEventData e){held=false;}
        public void OnDeselect(BaseEventData e){held=false;}
        void LateUpdate()
        {
            if(!button||!button.IsInteractable())held=false;
            float elapsed=Time.unscaledTime-pressedAt;
            float target=held?1:lastPressed==id&&elapsed<.28f?Mathf.Sin(Mathf.Clamp01(elapsed/.28f)*Mathf.PI):0;
            // At rest nothing is written: a transform write per tab per frame would re-batch the Home canvas.
            if(idle&&target==0&&amount==0)return;
            amount=Mathf.MoveTowards(amount,target,Time.unscaledDeltaTime*16);Apply(1-.12f*amount);
            float scale=reduced?1:1-.08f*amount;if(icon)icon.rectTransform.localScale=Vector3.one*scale;
            idle=amount==0;
        }
        void Apply(float tint)
        {var c=new Color(tint,tint,tint,1);if(icon)icon.canvasRenderer.SetColor(c);if(plate)plate.canvasRenderer.SetColor(c);}
        void OnDisable(){held=false;amount=0;idle=true;Apply(1);if(icon)icon.rectTransform.localScale=Vector3.one;if(plate)plate.rectTransform.localScale=Vector3.one;}
    }
}

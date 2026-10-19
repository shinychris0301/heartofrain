using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
namespace HeartOfTheRain.App.Home
{
    // Selection is driven by the current page after click/tap. Hover does not
    // reveal another panel. Every tab uses the same Home-derived panel asset.
    // Press tint leaves the selected panel, icon sizes and hit bounds fixed.
    public sealed class MainNavigationFeedback : MonoBehaviour, IPointerDownHandler,
        IPointerUpHandler, IPointerExitHandler, IDeselectHandler
    {
        Button button; Graphic plate,icon; bool held;
        public static void Bind(Dictionary<string,RectTransform> nodes,bool reducedMotion)
        {
            foreach(string name in new[]{"journey","leaderboard","home","teams","shop"})
            {
                string id="nav-"+name;RectTransform hit,p,i;
                if(!nodes.TryGetValue(id,out hit)||!nodes.TryGetValue(id+"-plate",out p)||
                   !nodes.TryGetValue(id+"-icon",out i))continue;
                var v=hit.gameObject.AddComponent<MainNavigationFeedback>();
                v.button=hit.GetComponent<Button>();v.plate=p.GetComponent<Graphic>();
                v.icon=i.GetComponent<Graphic>();
            }
        }
        public void OnPointerDown(PointerEventData e){if(button&&button.IsInteractable())held=true;}
        public void OnPointerUp(PointerEventData e){held=false;}
        public void OnPointerExit(PointerEventData e){held=false;}
        public void OnDeselect(BaseEventData e){held=false;}
        void LateUpdate()
        {
            if(!button||!button.IsInteractable())held=false;
            Apply(held?.9f:1);
        }
        void Apply(float tint)
        {var c=new Color(tint,tint,tint,1);if(icon)icon.canvasRenderer.SetColor(c);if(plate)plate.canvasRenderer.SetColor(c);}
        void OnDisable(){held=false;Apply(1);}
    }
}

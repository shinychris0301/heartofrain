using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
namespace HeartOfTheRain.App.Home
{
    public sealed class HomeButtonFeedback : MonoBehaviour, IPointerDownHandler, IPointerUpHandler, IPointerExitHandler, ISelectHandler, IDeselectHandler
    {
        public bool reduceMotion;
        private bool held,selected;
        private readonly List<Graphic> visuals=new List<Graphic>();
        public void CaptureVisuals(){visuals.Clear();foreach(var g in GetComponentsInChildren<Graphic>())if(g.gameObject!=gameObject)visuals.Add(g);}
        public void OnPointerDown(PointerEventData e){held=true;}
        public void OnPointerUp(PointerEventData e){held=false;}
        public void OnPointerExit(PointerEventData e){held=false;}
        public void OnSelect(BaseEventData e){selected=true;}
        public void OnDeselect(BaseEventData e){selected=false;held=false;}
        private void Update()
        {
            // Tint preserves text positions, touch geometry and sprite aspect ratios.
            float tint=held?.88f:1;
            foreach(var g in visuals)if(g)g.canvasRenderer.SetColor(new Color(tint,tint,tint,1));
        }
        private void OnDisable(){held=false;selected=false;foreach(var g in visuals)if(g)g.canvasRenderer.SetColor(Color.white);}
    }
}

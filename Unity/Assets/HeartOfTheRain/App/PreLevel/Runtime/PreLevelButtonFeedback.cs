using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
namespace HeartOfTheRain.App.PreLevel
{
    // Animate the visual siblings only. Touch bounds remain fixed during a press.
    public sealed class PreLevelButtonFeedback:MonoBehaviour,IPointerDownHandler,IPointerUpHandler,IPointerExitHandler,IDeselectHandler
    {
        Graphic[] visuals=new Graphic[0];Vector2[] origins=new Vector2[0];
        Button button;bool held,reduceMotion;float amount;
        public void Configure(Graphic[] targets,bool reducedMotion)
        {
            visuals=targets;origins=new Vector2[targets.Length];reduceMotion=reducedMotion;button=GetComponent<Button>();
            for(int i=0;i<targets.Length;i++)origins[i]=targets[i].rectTransform.anchoredPosition;
        }
        public void OnPointerDown(PointerEventData e){if(button&&button.IsInteractable())held=true;}
        public void OnPointerUp(PointerEventData e){held=false;}
        public void OnPointerExit(PointerEventData e){held=false;}
        public void OnDeselect(BaseEventData e){held=false;}
        void Update()
        {
            if(!button||!button.IsInteractable())held=false;
            if(!held&&amount<=0)return;
            amount=Mathf.MoveTowards(amount,held?1:0,Time.unscaledDeltaTime/(held?.055f:.11f));
            for(int i=0;i<visuals.Length;i++)if(visuals[i])
            {
                float tint=1-.13f*amount;visuals[i].canvasRenderer.SetColor(new Color(tint,tint,tint,1));
                visuals[i].rectTransform.anchoredPosition=origins[i]+new Vector2(0,reduceMotion?0:-1.25f*amount);
            }
        }
        void OnDisable()
        {
            held=false;amount=0;
            for(int i=0;i<visuals.Length;i++)if(visuals[i]){visuals[i].canvasRenderer.SetColor(Color.white);visuals[i].rectTransform.anchoredPosition=origins[i];}
        }
    }
}

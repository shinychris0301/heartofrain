using System;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.App.TeamsSocial
{
    // Confirmed presentation only: no balance, service, profile or completion
    // callback is accepted by this component.
    public sealed class TeamsHelpFeedback110 : MonoBehaviour
    {
        public string ReceiptId { get; private set; }
        public string Operation { get; private set; }
        public bool Running { get; private set; }
        public float Elapsed { get; private set; }
        public bool Reduced { get; private set; }
        public RectTransform Heart { get; private set; }
        readonly RectTransform[] stars=new RectTransform[3];
        RectTransform[] requestTargets;Vector3[] requestPositions;CanvasGroup[] requestAlpha;float requestRise;
        CanvasGroup alpha;Vector3 from,to;float duration;
        public void Begin(string receiptId,string operation,Vector3 start,Vector3 destination,Sprite heart,Sprite star,bool reduced)
        {
            if(string.IsNullOrEmpty(receiptId)||operation==null||!operation.StartsWith("life.",StringComparison.Ordinal))throw new ArgumentException();
            ReceiptId=receiptId;Operation=operation;from=start;to=destination;Reduced=reduced;duration=reduced?.1f:operation=="life.request"?.18f:.6f;
            alpha=gameObject.AddComponent<CanvasGroup>();alpha.blocksRaycasts=alpha.interactable=false;
            Heart=Graphic("Heart",heart,24);for(int i=0;i<stars.Length;i++)stars[i]=Graphic("Star "+i,star,8);
            Elapsed=0;Running=true;Apply();
        }
        public void AnimateRequest(RectTransform[] targets,float rise)
        {
            if(Operation!="life.request"||targets==null)return;requestTargets=targets;requestRise=Math.Max(0,rise);requestPositions=new Vector3[targets.Length];requestAlpha=new CanvasGroup[targets.Length];
            for(int i=0;i<targets.Length;i++)if(targets[i]){requestPositions[i]=targets[i].localPosition;requestAlpha[i]=targets[i].GetComponent<CanvasGroup>();if(!requestAlpha[i])requestAlpha[i]=targets[i].gameObject.AddComponent<CanvasGroup>();}Heart.gameObject.SetActive(false);Apply();
        }
        RectTransform Graphic(string name,Sprite art,float size){var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(transform,false);var rt=(RectTransform)go.transform;rt.anchorMin=rt.anchorMax=rt.pivot=new Vector2(.5f,.5f);rt.sizeDelta=Vector2.one*size;var image=go.AddComponent<Image>();image.sprite=art;image.preserveAspect=true;image.raycastTarget=false;return rt;}
        public void Advance(float seconds){if(!Running||seconds<0||float.IsNaN(seconds)||float.IsInfinity(seconds))return;Elapsed=Math.Min(duration,Elapsed+seconds);Apply();if(Elapsed>=duration){Running=false;gameObject.SetActive(false);}}
        void Apply(){float u=duration<=0?1:Mathf.Clamp01(Elapsed/duration);alpha.alpha=Reduced?1-u:Mathf.Clamp01((1-u)*5);Vector3 position;
            if(Reduced)position=to;else{position=Vector3.Lerp(from,to,u);position.y+=Mathf.Sin(u*Mathf.PI)*22;}
            Heart.localPosition=position;Heart.localScale=Vector3.one*(Reduced?1:1+.25f*Mathf.Sin(u*Mathf.PI));
            if(requestTargets!=null)for(int i=0;i<requestTargets.Length;i++)if(requestTargets[i]){requestTargets[i].localPosition=requestPositions[i]+Vector3.up*(Reduced?0:(1-u)*requestRise);if(requestAlpha[i])requestAlpha[i].alpha=u;}
            for(int i=0;i<stars.Length;i++){var image=stars[i].GetComponent<Image>();bool visible=!Reduced&&Operation=="life.help"&&u>.65f;image.enabled=visible;float t=Mathf.Clamp01((u-.65f)/.35f),angle=(i*120+20)*Mathf.Deg2Rad;stars[i].localPosition=to+new Vector3(Mathf.Cos(angle),Mathf.Sin(angle),0)*t*18;image.color=new Color(1,1,1,1-t);}
        }
        public void Cancel(){if(requestTargets!=null)for(int i=0;i<requestTargets.Length;i++)if(requestTargets[i]){requestTargets[i].localPosition=requestPositions[i];if(requestAlpha[i])requestAlpha[i].alpha=1;}Running=false;gameObject.SetActive(false);}
        void OnDestroy(){if(requestTargets!=null)for(int i=0;i<requestTargets.Length;i++)if(requestTargets[i]){requestTargets[i].localPosition=requestPositions[i];if(requestAlpha[i])requestAlpha[i].alpha=1;}}
        void Update(){Advance(Time.unscaledDeltaTime);}
    }
}

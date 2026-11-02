using System;using System.Collections;using UnityEngine;using UnityEngine.UI;
using HeartOfTheRain.App.Profile;using HeartOfTheRain.App.PreLevel;
namespace HeartOfTheRain.App.Home {
    [DisallowMultipleComponent] public sealed class HomeLivesFeedback:MonoBehaviour {
        public readonly HomeLivesPresentation View=new HomeLivesPresentation();
        public string LastAnnouncement{get;private set;}public event Action<string> Announcement;
        HomePage home;HomeLivesAssets assets;Font font;RectTransform root,header;Text count,status;Image clock;
        RectTransform fx;CanvasGroup fxAlpha;Image heart;Text amount;readonly Image[] stars=new Image[4];Coroutine motion;
        Vector2 countPosition;float statusX,statusY,statusW,statusH;int statusFont,playing;long paintRemaining=-2;bool paintClock,paintReady;int paintLives,paintMax,paintLocale=-1;HomeLevelFlow flow;
        public bool Playing=>motion!=null;
        public void Configure(HomePage owner,Font textFont,RectTransform canvas){home=owner;font=textFont;root=canvas;assets=HomeLivesAssets.Load();if(!assets)throw new InvalidOperationException("Home Lives bindings missing");}
        public void Bind(RectTransform head,Text counter,Text timer){
            if(Playing)View.Requeue(playing);Cancel();paintRemaining=-2;header=head;count=counter;status=timer;
            var rt=count.rectTransform;rt.pivot=Vector2.one*.5f;rt.anchoredPosition+=new Vector2(rt.rect.width*.5f,-rt.rect.height*.5f);countPosition=rt.anchoredPosition;
            rt=status.rectTransform;statusX=rt.anchoredPosition.x;statusY=-rt.anchoredPosition.y;statusW=rt.rect.width;statusH=rt.rect.height;statusFont=status.fontSize;
            var c=new GameObject("life-refill-clock",typeof(RectTransform),typeof(Image));c.transform.SetParent(header,false);clock=c.GetComponent<Image>();clock.sprite=assets.clock;clock.preserveAspect=true;clock.raycastTarget=false;Paint();
        }
        public void Observe(PlayerProfile p,long now){View.Accept(p,now,Time.realtimeSinceStartupAsDouble);Paint();}
        public void Unavailable(){View.Unavailable();Paint();}
        void Update(){
            if(!home)return;if(!home.PresentationVisible||!home.PresentationInteractable){if(Playing)Cancel();}
            if(!home.PresentationVisible)return;Paint();
            // Expiry is observed by PlayerProfileHost's own gated refresh (LifeDue); painting never rebuilds Home.
            if(!flow)flow=home.GetComponent<HomeLevelFlow>();
            if(Playing||!home.PresentationInteractable||home.EventsOpen||!flow||!flow.CanOpenAppSettings)return;
            int next=View.Take();if(next==0)return;LastAnnouncement=HomeLivesText.Count(next<0?"lost":"gained",View.Lives,View.Max);Announcement?.Invoke(LastAnnouncement);
            if(!home.State.reduceMotion){playing=next;motion=StartCoroutine(Play(next));}
        }
        public void Paint(){
            if(!status||!count)return;double elapsed=Time.realtimeSinceStartupAsDouble;long remaining=View.Remaining(elapsed);bool hasClock=View.Clock(elapsed);int locale=HeartOfTheRain.App.Localization.GameLocale.Revision;
            // Numeric change detection: no strings are built on an unchanged second.
            if(remaining==paintRemaining&&hasClock==paintClock&&View.Ready==paintReady&&View.Lives==paintLives&&View.Max==paintMax&&locale==paintLocale)return;
            paintRemaining=remaining;paintClock=hasClock;paintReady=View.Ready;paintLives=View.Lives;paintMax=View.Max;paintLocale=locale;string value=View.Status(elapsed);float cs=Mathf.Clamp(header.rect.width*.025f,8,15),gap=2;
            status.text=value;status.fontSize=statusFont;status.horizontalOverflow=HorizontalWrapMode.Overflow;status.verticalOverflow=VerticalWrapMode.Overflow;
            float available=statusW-(hasClock?cs+gap:0);while(status.fontSize>8&&status.preferredWidth>available)status.fontSize--;
            float tw=Mathf.Min(available,status.preferredWidth+1),total=tw+(hasClock?cs+gap:0),x=statusX+(statusW-total)/2;
            clock.gameObject.SetActive(hasClock);Place(clock.rectTransform,x,statusY+(statusH-cs)/2,cs,cs);Place(status.rectTransform,x+(hasClock?cs+gap:0),statusY,tw,statusH);
            status.color=View.Ready&&View.Lives>=View.Max?ColorOf("#377347"):ColorOf("#425F79");
            if(!Playing)count.color=CountColor();
            count.text=View.Ready?View.Lives+"/"+View.Max:home.State.walletUnavailable?"\u2014/"+home.State.maxLives:home.State.lives+"/"+home.State.maxLives;
            home.State.lifeRefillStatus=value;home.State.lifeRefillClock=hasClock;
            var access=header.parent.Find("lives")?.GetComponent<HomeControlLabel>();if(access){string detail=View.Ready&&View.Lives>=View.Max?HomeLivesText.T("full"):remaining<=0?HomeLivesText.T("sync"):HomeLivesText.T("nextLife").Replace("{time}",value);access.label=home.State.walletUnavailable?HeartOfTheRain.App.Localization.GameLocale.T("Unavailable"):HomeLivesText.Count("counter",View.Ready?View.Lives:home.State.lives,View.Ready?View.Max:home.State.maxLives)+". "+detail+". "+HomeLivesText.T("action");}
        }
        Color CountColor()=>ColorOf(home.State.walletUnavailable?"#425F79":(View.Ready?View.Lives:home.State.lives)==0?"#B12640":(View.Ready?View.Lives:home.State.lives)==1?"#945522":"#101A29");
        void Pool(){if(fx)return;fx=Rect("Home life feedback",root);fxAlpha=fx.gameObject.AddComponent<CanvasGroup>();fxAlpha.interactable=false;fxAlpha.blocksRaycasts=false;
            heart=Rect("Life particle",fx).gameObject.AddComponent<Image>();heart.sprite=assets.heart;heart.preserveAspect=true;heart.raycastTarget=false;
            amount=Rect("Life delta",fx).gameObject.AddComponent<Text>();amount.font=font;amount.raycastTarget=false;amount.alignment=TextAnchor.MiddleCenter;amount.horizontalOverflow=HorizontalWrapMode.Overflow;amount.verticalOverflow=VerticalWrapMode.Overflow;var shadow=amount.gameObject.AddComponent<Shadow>();shadow.effectDistance=new Vector2(0,-1);shadow.effectColor=new Color(.18f,.08f,.12f,.8f);
            for(int i=0;i<4;i++){stars[i]=Rect("Life star "+i,root).gameObject.AddComponent<Image>();stars[i].sprite=assets.star;stars[i].raycastTarget=false;stars[i].gameObject.SetActive(false);}}
        IEnumerator Play(int delta){
            Pool();bool loss=delta<0;float w=header.rect.width,h=header.rect.height,icon=w*.055f;amount.text=loss?"\u22121":"+1";amount.fontSize=Mathf.RoundToInt(w*.046f);amount.color=ColorOf(loss?"#FFF4DC":"#E5FFD3");float tw=amount.preferredWidth+2;
            Place(heart.rectTransform,0,0,icon,icon);Place(amount.rectTransform,icon+3,0,tw,icon);fx.sizeDelta=new Vector2(icon+3+tw,icon);fx.pivot=new Vector2(0,1);fx.anchorMin=fx.anchorMax=root.pivot;fx.gameObject.SetActive(true);
            Vector2 origin=root.InverseTransformPoint(header.TransformPoint(new Vector3(w*.68f,-(loss?h*.87f:h),0))),spark=root.InverseTransformPoint(header.TransformPoint(new Vector3(w*.75f,-h*.5f,0)));
            for(int i=0;i<4;i++){var rt=stars[i].rectTransform;rt.anchorMin=rt.anchorMax=root.pivot;rt.pivot=Vector2.one*.5f;rt.sizeDelta=Vector2.one*8;stars[i].gameObject.SetActive(!loss);}
            Vector2[] offsets={new Vector2(24,11),new Vector2(-23,16),new Vector2(17,-18),new Vector2(-16,-20)};
            float duration=loss?.9f:.8f;
            for(float t=0;t<duration;t+=Time.unscaledDeltaTime){if(!home.PresentationInteractable||home.State.reduceMotion)break;float p=t/duration;
                float y=loss?p<.15f?Mathf.Lerp(-4,0,p/.15f):Mathf.Lerp(0,32,(p-.15f)/.85f):Mathf.Lerp(17,-18,p);
                fx.anchoredPosition=origin+Vector2.down*y;fx.localScale=Vector3.one*(loss?p<.15f?Mathf.Lerp(.9f,1,p/.15f):Mathf.Lerp(1,.92f,(p-.15f)/.85f):Mathf.Lerp(.9f,1,p));fxAlpha.alpha=p<.15f?p/.15f:p<.65f?1:1-(p-.65f)/.35f;
                float q=Mathf.Clamp01(t/(loss?.46f:.6f)),scale=loss?q<.3f?Mathf.Lerp(1,.93f,q/.3f):q<.55f?Mathf.Lerp(.93f,1,(q-.3f)/.25f):1:q<.4f?Mathf.Lerp(1,1.1f,q/.4f):Mathf.Lerp(1.1f,1,(q-.4f)/.6f);
                float dx=loss?q<.3f?Mathf.Lerp(0,-2,q/.3f):q<.55f?Mathf.Lerp(-2,2,(q-.3f)/.25f):q<.8f?Mathf.Lerp(2,-1,(q-.55f)/.25f):Mathf.Lerp(-1,0,(q-.8f)/.2f):0;
                count.rectTransform.localScale=Vector3.one*scale;count.rectTransform.anchoredPosition=countPosition+Vector2.right*dx;count.color=Color.Lerp(CountColor(),ColorOf(loss?"#B12640":"#377347"),Mathf.Sin(q*Mathf.PI));
                for(int i=0;i<4&&!loss;i++){float k=Mathf.Clamp01(t/.65f);stars[i].rectTransform.anchoredPosition=spark+offsets[i]*k;stars[i].rectTransform.localScale=Vector3.one*(k<.2f?Mathf.Lerp(.2f,1,k/.2f):Mathf.Lerp(1,.3f,(k-.2f)/.8f));stars[i].color=new Color(1,1,1,k<.2f?k/.2f:1-(k-.2f)/.8f);}yield return null;
            }
            ResetVisuals();motion=null;playing=0;
        }
        public void Cancel(){if(motion!=null)StopCoroutine(motion);motion=null;playing=0;ResetVisuals();}
        void ResetVisuals(){if(count){count.rectTransform.localScale=Vector3.one;count.rectTransform.anchoredPosition=countPosition;count.color=CountColor();}if(fx)fx.gameObject.SetActive(false);foreach(var star in stars)if(star)star.gameObject.SetActive(false);}
        void OnDisable(){Cancel();}
        static Color ColorOf(string value){ColorUtility.TryParseHtmlString(value,out var c);return c;}
        static RectTransform Rect(string name,Transform parent){var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);return (RectTransform)go.transform;}
        static void Place(RectTransform rt,float x,float y,float w,float h){rt.anchorMin=rt.anchorMax=rt.pivot=new Vector2(0,1);rt.anchoredPosition=new Vector2(x,-y);rt.sizeDelta=new Vector2(w,h);}
    }
}

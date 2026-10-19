using System;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using HeartOfTheRain.App.Home;
namespace HeartOfTheRain.App.Celebrations
{
    // A transparent animation layer above the live board. No results modal or UI labels.
    public sealed class VictoryCelebrationPlayer:MonoBehaviour
    {
        HomePage home;CelebrationAssets assets;Canvas canvas;CanvasScaler scaler;
        RectTransform safe,actor;DariaCelebrationView daria;Image shade,halo;Image[] particles;
        Button input;Action complete;GameObject previousFocus;int variant;
        readonly VictoryPlaybackSession clock=new VictoryPlaybackSession();
        bool focused=true,suspended;Vector2Int lastSize;Rect lastSafe;float lastScale;
        VictoryGeometry geometry;static int closedFrame=-1;
        public static bool ConsumedInputThisFrame=>closedFrame==Time.frameCount;
        public bool IsVisible=>canvas&&canvas.gameObject.activeSelf;
        public static bool IsPlaying(HomePage h){var p=h?h.GetComponent<VictoryCelebrationPlayer>():null;return p&&p.IsVisible;}
        float UIScale=>home?home.CurrentUIScale:Mathf.Max(.25f,Screen.safeArea.width/430f);
        public static bool TryPlay(HomePage h,int level,Action after)
        {return h&&PlayOn(h.gameObject,h,level,h.State.reduceMotion,after);}
        public static bool TryPlayStandalone(MonoBehaviour owner,int level,Action after)
        {return owner&&PlayOn(owner.gameObject,null,level,false,after);}
        static bool PlayOn(GameObject owner,HomePage h,int level,bool reduced,Action after)
        {
            var a=CelebrationAssets.Load();if(!a||!a.dariaAtlas||!a.dariaBlend||!a.ui)return false;
            var p=owner.GetComponent<VictoryCelebrationPlayer>();if(p&&p.IsVisible)return false;
            if(!p)p=owner.AddComponent<VictoryCelebrationPlayer>();
            p.home=h;p.assets=a;p.variant=level;p.complete=after;p.clock.Open(reduced);
            p.previousFocus=EventSystem.current?EventSystem.current.currentSelectedGameObject:null;
            if(!p.canvas)p.Build();p.canvas.gameObject.SetActive(true);p.Reflow();p.Sample();
            if(EventSystem.current)EventSystem.current.SetSelectedGameObject(p.input.gameObject);return true;
        }
        void Build()
        {
            var root=Rect("Victory animation",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=260;
            scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;root.gameObject.AddComponent<GraphicRaycaster>();
            shade=Rect("Tap to skip animation",root).gameObject.AddComponent<Image>();Stretch(shade.rectTransform);shade.raycastTarget=true;
            input=shade.gameObject.AddComponent<Button>();input.targetGraphic=shade;input.transition=Selectable.Transition.None;input.onClick.AddListener(Skip);
            safe=Rect("Safe area",root);safe.gameObject.AddComponent<RectMask2D>();
            halo=Art("Warm light",safe,assets.ui.Find("LC_Halo"));
            actor=Rect("Daria",safe);actor.pivot=new Vector2(.5f,.5f);daria=actor.gameObject.AddComponent<DariaCelebrationView>();daria.Configure(assets.dariaAtlas);
            particles=new Image[VictoryMotion.ParticleCount];
            for(int i=0;i<particles.Length;i++)particles[i]=Art("Confetti "+i,safe,i%5==0?assets.ui.Find("RewardStar_R2"):null);
        }
        void Reflow()
        {
            var sr=Screen.safeArea;if(sr.width<=0||sr.height<=0)sr=new Rect(0,0,Screen.width,Screen.height);
            float scale=Mathf.Max(.1f,Mathf.Min(UIScale,sr.width/320,sr.height/320));scaler.scaleFactor=canvas.scaleFactor=scale;
            geometry=VictoryGeometry.Build(sr.width/scale,sr.height/scale);
            Place(safe,sr.x/scale,(Screen.height-sr.yMax)/scale,geometry.width,geometry.height);
            lastSize=new Vector2Int(Screen.width,Screen.height);lastSafe=Screen.safeArea;lastScale=UIScale;
        }
        void Update()
        {
            if(!IsVisible)return;
            if(lastSize.x!=Screen.width||lastSize.y!=Screen.height||lastSafe!=Screen.safeArea||lastScale!=UIScale)Reflow();
            clock.Advance(Time.unscaledDeltaTime,focused&&!suspended);Sample();
            if(clock.Finished){Finish();return;}
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
            bool back=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
            bool back=Input.GetKeyDown(KeyCode.Escape);
#endif
            if(back)Skip();
        }
        void Sample()
        {
            float t=clock.Elapsed;var g=geometry;var p=VictoryMotion.Sample(t,clock.Reduced);
            shade.color=new Color(0,0,0,p.dim);input.interactable=clock.CanSkip;
            float size=g.size*p.scale;Place(actor,g.x+(g.size-size)/2,g.y+(g.size-size)/2+p.lift,size,size);
            daria.Sample(Mathf.Max(0,t-.18f),variant,clock.Reduced,p.alpha);
            float hs=g.size*p.haloScale;Place(halo.rectTransform,g.x+(g.size-hs)/2,g.y+(g.size-hs)/2,hs,hs);halo.color=new Color(1,1,1,p.haloAlpha);halo.rectTransform.localRotation=Quaternion.Euler(0,0,p.haloAngle);
            for(int i=0;i<particles.Length;i++)
            {
                var v=VictoryMotion.Particle(t,i,g,clock.Reduced);var im=particles[i];Place(im.rectTransform,v.x-v.width/2,v.y-v.height/2,v.width,v.height);im.rectTransform.localRotation=Quaternion.Euler(0,0,v.angle);
                var c=v.star?Color.white:v.color==0?new Color(.94f,.73f,.32f):v.color==1?new Color(.97f,.91f,.76f):new Color(.49f,.53f,.30f);c.a=v.alpha*p.alpha;im.color=c;
            }
        }
        public void Skip(){if(clock.CanSkip)Finish();}
        public void Finish()
        {
            if(!IsVisible||!clock.Close())return;closedFrame=Time.frameCount;canvas.gameObject.SetActive(false);
            if(EventSystem.current&&previousFocus&&previousFocus.activeInHierarchy)EventSystem.current.SetSelectedGameObject(previousFocus);
            var done=complete;complete=null;done?.Invoke();
        }
        public void Cancel(){complete=null;Finish();}
        void OnApplicationFocus(bool value){focused=value;}void OnApplicationPause(bool value){suspended=value;}
        void OnDestroy(){clock.Close();complete=null;}
        static RectTransform Rect(string name,Transform parent){var g=new GameObject(name,typeof(RectTransform));g.transform.SetParent(parent,false);return (RectTransform)g.transform;}
        static Image Art(string name,Transform parent,Sprite sprite){var im=Rect(name,parent).gameObject.AddComponent<Image>();im.sprite=sprite;im.raycastTarget=false;return im;}
        static void Stretch(RectTransform r){r.anchorMin=Vector2.zero;r.anchorMax=Vector2.one;r.offsetMin=r.offsetMax=Vector2.zero;}
        static void Place(RectTransform r,float x,float y,float w,float h){r.anchorMin=r.anchorMax=new Vector2(0,1);r.pivot=new Vector2(.5f,.5f);r.anchoredPosition=new Vector2(x+w/2,-y-h/2);r.sizeDelta=new Vector2(w,h);}
    }
}

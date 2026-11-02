using System;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using HeartOfTheRain.App.Home;
namespace HeartOfTheRain.App.Celebrations
{
    // Presentation only. Model settlement precedes playback; finish/skip never grant.
    public sealed class VictoryCelebrationPlayer:MonoBehaviour
    {
        HomePage home;M68CelebrationAssets data;Canvas canvas;CanvasScaler scaler;
        RectTransform safe,actor;DariaCelebrationView daria;Image shade;RawImage halo;RawImage[] particles;
        Button input;AudioSource sound;AudioListener ownedListener;Action complete;GameObject previousFocus;
        readonly CelebrationFrameTiming timing=new CelebrationFrameTiming();
        public CelebrationTimingReport LastTiming=>timing.Report;
        readonly VictoryPlaybackSession clock=new VictoryPlaybackSession();
        bool focused=true,suspended,soundStarted,skipping;float skipTime;Vector2Int lastSize;Rect lastSafe;float lastScale;
        VictoryGeometry geometry;static int closedFrame=-1;
        public static bool ConsumedInputThisFrame=>closedFrame==Time.frameCount;
        public bool IsVisible=>canvas&&canvas.gameObject.activeSelf;
        public static bool IsPlaying(HomePage h){var p=h?h.GetComponent<VictoryCelebrationPlayer>():null;return p&&p.IsVisible;}
        float UIScale=>home?home.CurrentUIScale:Mathf.Max(.25f,Screen.safeArea.width/430f);
        public static bool TryPlay(HomePage h,int level,Action after)=>h&&PlayOn(h.gameObject,h,h.State.reduceMotion,after);
        public static bool TryPlayStandalone(MonoBehaviour owner,int level,Action after)=>owner&&PlayOn(owner.gameObject,null,false,after);
        static bool PlayOn(GameObject owner,HomePage h,bool reduced,Action after)
        {
            var a=M68CelebrationAssets.Load();if(!a)return false;
            var p=owner.GetComponent<VictoryCelebrationPlayer>();if(p&&p.IsVisible)return false;if(!p)p=owner.AddComponent<VictoryCelebrationPlayer>();
            p.home=h;p.data=a;p.complete=after;p.clock.Open(reduced);p.timing.Reset();p.soundStarted=false;p.skipping=false;p.skipTime=0;
            p.previousFocus=EventSystem.current?EventSystem.current.currentSelectedGameObject:null;
            if(!p.canvas)p.Build();p.canvas.gameObject.SetActive(true);p.Reflow();p.Sample();
            if(EventSystem.current)EventSystem.current.SetSelectedGameObject(p.input.gameObject);return true;
        }
        void Build()
        {
            var root=Rect("Victory animation",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=260;
            canvas.vertexColorAlwaysGammaSpace=true;scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;root.gameObject.AddComponent<GraphicRaycaster>();
            shade=Rect("Tap to skip animation",root).gameObject.AddComponent<Image>();Stretch(shade.rectTransform);shade.raycastTarget=true;
            input=shade.gameObject.AddComponent<Button>();input.targetGraphic=shade;input.transition=Selectable.Transition.None;input.onClick.AddListener(Skip);
            safe=Rect("Safe area",root);safe.gameObject.AddComponent<RectMask2D>();
            halo=Art("M68 warm light",safe,data.halo);particles=new RawImage[data.Design.seeds.Length];
            foreach(var seed in data.Design.seeds)particles[seed.id]=Art("M68 particle "+seed.id,safe,seed.star?data.star:Texture2D.whiteTexture);
            actor=Rect("Daria",safe);daria=actor.gameObject.AddComponent<DariaCelebrationView>();daria.Configure((CelebrationAssets)null);
            sound=gameObject.AddComponent<AudioSource>();sound.playOnAwake=false;sound.spatialBlend=0;sound.volume=.60f;sound.clip=data.sound;
        }
        void Reflow()
        {
            var sr=Screen.safeArea;if(sr.width<=0||sr.height<=0)sr=new Rect(0,0,Screen.width,Screen.height);
            float scale=Mathf.Max(.1f,Mathf.Min(UIScale,sr.width/320,sr.height/320));scaler.scaleFactor=canvas.scaleFactor=scale;
            geometry=VictoryGeometry.Build(sr.width/scale,sr.height/scale);Place(safe,sr.x/scale,(Screen.height-sr.yMax)/scale,geometry.width,geometry.height);
            Place(actor,geometry.x,geometry.y,geometry.size,geometry.size);lastSize=new Vector2Int(Screen.width,Screen.height);lastSafe=Screen.safeArea;lastScale=UIScale;
        }
        void Update()
        {
            if(!IsVisible)return;if(lastSize.x!=Screen.width||lastSize.y!=Screen.height||lastSafe!=Screen.safeArea||lastScale!=UIScale)Reflow();
            bool active=focused&&!suspended;timing.Record(Time.unscaledDeltaTime,active);clock.Advance(Time.unscaledDeltaTime,active);if(skipping&&active)skipTime+=Time.unscaledDeltaTime;
            if(!soundStarted&&clock.Elapsed>=.18f){soundStarted=true;if(PlayerPrefs.GetInt("HeartOfTheRain.Settings.v1.sound",1)!=0&&data.sound){if(FindObjectsByType<AudioListener>(UnityEngine.FindObjectsSortMode.InstanceID).Length==0)ownedListener=gameObject.AddComponent<AudioListener>();sound.Play();}}
            Sample();if(clock.Finished||skipping&&skipTime>=.18f){Finish();return;}
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
            bool back=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
            bool back=Input.GetKeyDown(KeyCode.Escape);
#endif
            if(back)Skip();
        }
        void Sample()
        {
            float t=clock.Elapsed,fade=skipping?1-Mathf.SmoothStep(0,1,skipTime/.18f):1;var g=geometry;var sample=data.Effects.samples[M68CelebrationAssets.Frame(t)];
            float dim=clock.Reduced?.96f*Mathf.Clamp01(t/.18f)*(1-Mathf.Clamp01((t-1.68f)/.2f)):sample.scrim_alpha;dim*=fade;
            if(QualitySettings.activeColorSpace==ColorSpace.Linear)dim=1-Mathf.GammaToLinearSpace(1-dim);shade.color=new Color(0,0,0,dim);input.interactable=clock.CanSkip&&!skipping;
            daria.SampleLevel(t,clock.Reduced,fade);halo.enabled=!clock.Reduced;
            float hs=g.size*sample.halo_size;Place(halo.rectTransform,g.x+g.size*sample.halo_center[0]-hs/2,g.y+g.size*sample.halo_center[1]-hs/2,hs,hs);halo.color=new Color(1,1,1,sample.halo_alpha*fade);halo.rectTransform.localRotation=Quaternion.Euler(0,0,sample.halo_angle);
            foreach(var particle in particles)particle.enabled=false;
            if(!clock.Reduced)foreach(var v in sample.particles){var im=particles[v.id];im.enabled=true;float size=g.size*v.size;Place(im.rectTransform,g.x+g.size*v.x-size/2,g.y+g.size*v.y-size*v.height_ratio/2,size,size*v.height_ratio);im.rectTransform.localRotation=Quaternion.Euler(0,0,v.angle);var c=data.Design.seeds[v.id].star?Color.white:data.Colors[v.id];c.a=v.opacity*fade;im.color=c;}
        }
        public void Skip(){if(clock.CanSkip&&!skipping){skipping=true;skipTime=0;}}
        public void Finish()
        {
            if(!IsVisible||!clock.Close())return;closedFrame=Time.frameCount;canvas.gameObject.SetActive(false);if(sound)sound.Stop();if(ownedListener){Destroy(ownedListener);ownedListener=null;}
            if(EventSystem.current&&previousFocus&&previousFocus.activeInHierarchy)EventSystem.current.SetSelectedGameObject(previousFocus);var done=complete;complete=null;done?.Invoke();
        }
        public void Cancel(){complete=null;Finish();}
        void OnApplicationFocus(bool value){focused=value;AudioFocus();}void OnApplicationPause(bool value){suspended=value;AudioFocus();}
        void AudioFocus(){if(!sound)return;if(!focused||suspended)sound.Pause();else if(IsVisible&&soundStarted)sound.UnPause();}
        void OnDestroy(){clock.Close();complete=null;if(sound)sound.Stop();if(ownedListener)Destroy(ownedListener);}
        static RectTransform Rect(string name,Transform parent){var g=new GameObject(name,typeof(RectTransform));g.transform.SetParent(parent,false);return (RectTransform)g.transform;}
        static RawImage Art(string name,Transform parent,Texture texture){var im=Rect(name,parent).gameObject.AddComponent<RawImage>();im.texture=texture;im.raycastTarget=false;return im;}
        static void Stretch(RectTransform r){r.anchorMin=Vector2.zero;r.anchorMax=Vector2.one;r.offsetMin=r.offsetMax=Vector2.zero;}
        static void Place(RectTransform r,float x,float y,float w,float h){r.anchorMin=r.anchorMax=new Vector2(0,1);r.pivot=new Vector2(.5f,.5f);r.anchoredPosition=new Vector2(x+w/2,-y-h/2);r.sizeDelta=new Vector2(w,h);}
    }
}

using System;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
namespace HeartOfTheRain.App.Celebrations
{
    // Presentation only. Rewards and progression belong to LevelCompleteSession.
    public sealed class ChapterCelebrationPlayer:MonoBehaviour
    {
        CelebrationAssets assets;ChapterCelebrationArt chapter;HomePage home;
        Canvas canvas;CanvasScaler scaler;RectTransform safe,stage,caption;
        RawImage well,hook;Image halo;DariaCelebrationView daria;
        Text title,chapterName,range,speaker,copy,buttonText;Button close;
        RectTransform[] stars;AudioSource music;AudioListener ownedListener;
        Action closed;GameObject previousFocus;readonly CelebrationPlaybackSession playback=new CelebrationPlaybackSession();float elapsed=>playback.Elapsed;int locale=-1;
        bool focused=true,suspended;Vector2Int lastSize;Rect lastSafe;
        float lastScale;CelebrationGeometry geometry;
        static int closedFrame=-1;
        public static bool ConsumedInputThisFrame=>closedFrame==Time.frameCount;
        public bool IsVisible=>canvas&&canvas.gameObject.activeSelf;
        public static bool IsPlaying(HomePage home)
        {var p=home?home.GetComponent<ChapterCelebrationPlayer>():null;return p&&p.IsVisible;}
        public static bool Available(int chapter)
        {var a=CelebrationAssets.Load();var c=a?a.Chapter(chapter):null;return c!=null&&c.restoration&&c.hook&&a.ui;}
        public static bool TryPlay(HomePage home,int chapter,Action after)
        {
            if(!home||!Available(chapter)||IsPlaying(home))return false;
            var p=home.GetComponent<ChapterCelebrationPlayer>();if(!p)p=home.gameObject.AddComponent<ChapterCelebrationPlayer>();
            p.home=home;p.assets=CelebrationAssets.Load();p.chapter=p.assets.Chapter(chapter);p.closed=after;
            p.playback.Open();p.locale=-1;p.previousFocus=EventSystem.current?EventSystem.current.currentSelectedGameObject:null;
            if(!p.canvas)p.Build();p.canvas.gameObject.SetActive(true);p.Reflow();p.Sample();
            if(EventSystem.current)EventSystem.current.SetSelectedGameObject(p.close.gameObject);
            p.PlayMusic();return true;
        }
        void Build()
        {
            var root=Rect("Chapter celebration",transform);canvas=root.gameObject.AddComponent<Canvas>();
            canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=260;
#if UNITY_2022_3_OR_NEWER
            canvas.vertexColorAlwaysGammaSpace=true;
#endif
            scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;
            root.gameObject.AddComponent<GraphicRaycaster>();
            var matte=Rect("Input shield",root);matte.anchorMin=Vector2.zero;matte.anchorMax=Vector2.one;matte.offsetMin=matte.offsetMax=Vector2.zero;
            var block=matte.gameObject.AddComponent<Image>();block.color=new Color(.035f,.075f,.12f);block.raycastTarget=true;
            safe=Rect("Safe area",root);safe.gameObject.AddComponent<RectMask2D>();stage=Rect("Story stage",safe);stage.gameObject.AddComponent<RectMask2D>();
            well=Raw("Restored well",stage);hook=Raw("Messenger arrives",stage);
            var dr=Rect("Animated Daria",safe);daria=dr.gameObject.AddComponent<DariaCelebrationView>();daria.Configure(assets.dariaAtlas);
            stars=new RectTransform[12];
            for(int i=0;i<stars.Length;i++){var s=Sprite("Celebration mote "+i,safe,assets.ui.Find("RewardStar_R2"),false);stars[i]=s.rectTransform;}
            var plaque=Sprite("Chapter plaque",safe,assets.ui.Find("R4_Chapter"),false);plaque.name="Chapter plaque";
            title=Label("Chapter title",safe,24,Color.white);chapterName=Label("Chapter name",safe,16,new Color(1,.94f,.80f));range=Label("Chapter range",safe,12,new Color(1,.88f,.64f));
            caption=Rect("Story caption",safe);var panel=Sprite("Caption well",caption,assets.ui.Find("LC_RewardWell"),true);Stretch(panel.rectTransform);
            speaker=Label("Speaker",caption,14,new Color(.53f,.38f,.16f));
            copy=Label("Story text",caption,17,new Color(.09f,.20f,.30f));copy.font=assets.ui.preLevel.home.regularFont;copy.horizontalOverflow=HorizontalWrapMode.Wrap;
            var br=Rect("Continue",safe);var bi=br.gameObject.AddComponent<Image>();bi.sprite=assets.ui.Find("R4_Start");bi.preserveAspect=false;
            close=br.gameObject.AddComponent<Button>();close.targetGraphic=bi;close.onClick.AddListener(Finish);
            buttonText=Label("Continue text",br,22,Color.white);Stretch(buttonText.rectTransform);
        }
        void Reflow()
        {
            var sr=Screen.safeArea;if(sr.width<=0||sr.height<=0)sr=new Rect(0,0,Screen.width,Screen.height);
            float scale=Mathf.Min(home.CurrentUIScale,Mathf.Max(.25f,sr.width/320),Mathf.Max(.25f,sr.height/320));
            scaler.scaleFactor=canvas.scaleFactor=scale;
            geometry=CelebrationGeometry.Build(sr.width/scale,sr.height/scale);var g=geometry;
            Place(safe,sr.x/scale,(Screen.height-sr.yMax)/scale,g.width,g.height);
            Place(stage,g.stageX,g.stageY,g.stageW,g.stageH);Place(well.rectTransform,0,0,g.stageW,g.stageH);Place(hook.rectTransform,0,0,g.stageW,g.stageH);
            well.texture=chapter.restoration.texture;hook.texture=chapter.hook.texture;
            Place((RectTransform)daria.transform,g.dariaX,g.dariaY,g.dariaSize,g.dariaSize);
            float plaqueW=g.landscape?g.captionW:Math.Min(360,g.width-28),plaqueX=g.landscape?g.captionX:(g.width-plaqueW)/2;
            Place((RectTransform)safe.Find("Chapter plaque"),plaqueX,12,plaqueW,96);
            Place(title.rectTransform,plaqueX+18,23,plaqueW-36,30);Place(chapterName.rectTransform,plaqueX+18,51,plaqueW-36,24);Place(range.rectTransform,plaqueX+18,76,plaqueW-36,20);
            Place(caption,g.captionX,g.captionY,g.captionW,g.captionH);
            Place(speaker.rectTransform,16,12,g.captionW-32,22);
            Place(copy.rectTransform,18,38,g.captionW-36,g.captionH-111);
            Place(close.GetComponent<RectTransform>(),g.buttonX,g.buttonY,g.buttonW,56);
            chapterName.text=StoryLocale.Title(chapter.chapter,chapter.title);Fit(chapterName);
            title.text=CelebrationText.Format("Chapter {0} complete",chapter.chapter);Fit(title);
            range.text=CelebrationText.Format("Levels {0}–{1}",CelebrationMotion.FirstLevel(chapter.chapter),CelebrationMotion.LastLevel(chapter.chapter));
            lastSize=new Vector2Int(Screen.width,Screen.height);lastSafe=Screen.safeArea;lastScale=home.CurrentUIScale;locale=GameLocale.Revision;
        }
        void Update()
        {
            if(!IsVisible)return;
            if(lastSize.x!=Screen.width||lastSize.y!=Screen.height||lastSafe!=Screen.safeArea||lastScale!=home.CurrentUIScale||locale!=GameLocale.Revision)Reflow();
            playback.Advance(Time.unscaledDeltaTime,focused&&!suspended);
            Sample();
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
            bool back=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
            bool back=Input.GetKeyDown(KeyCode.Escape);
#endif
            if(back)Finish();
            if(music){music.mute=PlayerPrefs.GetInt("HeartOfTheRain.Settings.v1.music",1)==0;music.volume=.14f*Mathf.Clamp01((CelebrationMotion.FinaleDuration-elapsed)/1.2f);}
        }
        void Sample()
        {
            bool reduced=home.State.reduceMotion;var g=geometry;var pose=CelebrationMotion.Finale(elapsed,reduced);int beat=pose.beat;
            float mix=pose.mix;
            well.color=Color.white;hook.color=new Color(1,1,1,mix);
            float zoom=pose.wellZoom;
            well.uvRect=Cover(well.texture,g.stageW,g.stageH,zoom);hook.uvRect=Cover(hook.texture,g.stageW,g.stageH,pose.hookZoom);
            daria.Sample(Mathf.Max(0,elapsed-2.4f),0,reduced,pose.dariaAlpha);
            speaker.text=CelebrationText.T(beat==0?"Village restored":beat==1?"Daria":"A message from the city");Fit(speaker);
            copy.text=CelebrationText.T(chapter.captions[Mathf.Min(beat,chapter.captions.Length-1)]);copy.fontSize=17;
            while(copy.fontSize>12&&copy.preferredHeight>copy.rectTransform.rect.height)copy.fontSize--;
            buttonText.text=CelebrationText.T(elapsed>=CelebrationMotion.FinaleDuration?"Continue":"Skip");Fit(buttonText);
            for(int i=0;i<stars.Length;i++)
            {
                float phase=(elapsed*.28f+i*.173f)%1;float x=g.stageW*(.08f+.84f*((i*.618f)%1));float y=g.stageH*(.25f+.53f*(1-phase));
                float size=5+i%4;Place(stars[i],x,y,size,size);stars[i].localRotation=Quaternion.Euler(0,0,elapsed*24+i*39);
                stars[i].GetComponent<Image>().color=new Color(1,.91f,.68f,reduced?0:Mathf.Sin(phase*Mathf.PI)*.65f*(1-mix));
            }
        }
        static Rect Cover(Texture t,float w,float h,float zoom)
        {
            float scale=Mathf.Max(w/t.width,h/t.height)*zoom,fx=w/(t.width*scale),fy=h/(t.height*scale);
            return new Rect((1-fx)*.5f,(1-fy)*.68f,fx,fy);
        }
        void PlayMusic()
        {
            if(!assets.music)return;if(!music){music=gameObject.AddComponent<AudioSource>();music.playOnAwake=false;music.spatialBlend=0;}
            if(FindObjectsOfType<AudioListener>().Length==0)ownedListener=gameObject.AddComponent<AudioListener>();
            music.clip=assets.music;music.loop=false;music.volume=.14f;music.mute=PlayerPrefs.GetInt("HeartOfTheRain.Settings.v1.music",1)==0;music.Play();
        }
        public void Finish()
        {
            if(!IsVisible||!playback.Close())return;closedFrame=Time.frameCount;canvas.gameObject.SetActive(false);if(music)music.Stop();
            if(ownedListener){Destroy(ownedListener);ownedListener=null;}
            if(EventSystem.current&&previousFocus&&previousFocus.activeInHierarchy)EventSystem.current.SetSelectedGameObject(previousFocus);
            var callback=closed;closed=null;callback?.Invoke();
        }
        public void Cancel(){closed=null;Finish();}
        void OnApplicationPause(bool value){suspended=value;AudioFocus();}
        void OnApplicationFocus(bool value){focused=value;AudioFocus();}
        void AudioFocus(){if(!music)return;if(suspended||!focused)music.Pause();else if(IsVisible)music.UnPause();}
        void OnDestroy(){playback.Close();closed=null;if(music)music.Stop();if(ownedListener)Destroy(ownedListener);}
        Text Label(string name,Transform parent,int size,Color color)
        {var t=Rect(name,parent).gameObject.AddComponent<Text>();t.font=assets.ui.preLevel.home.boldFont;t.fontSize=size;t.color=color;t.alignment=TextAnchor.MiddleCenter;t.raycastTarget=false;t.supportRichText=false;t.horizontalOverflow=HorizontalWrapMode.Overflow;t.verticalOverflow=VerticalWrapMode.Truncate;return t;}
        static void Fit(Text t){int start=t.name=="Chapter title"?24:t.name=="Continue text"?22:t.name=="Chapter name"?16:14;t.fontSize=start;while(t.fontSize>11&&t.preferredWidth>t.rectTransform.rect.width-12)t.fontSize--;}
        static RawImage Raw(string name,Transform parent){var r=Rect(name,parent).gameObject.AddComponent<RawImage>();r.raycastTarget=false;return r;}
        static Image Sprite(string name,Transform parent,Sprite sprite,bool sliced){var im=Rect(name,parent).gameObject.AddComponent<Image>();im.sprite=sprite;im.type=sliced?Image.Type.Sliced:Image.Type.Simple;im.pixelsPerUnitMultiplier=sliced?4:1;im.raycastTarget=false;return im;}
        static RectTransform Rect(string name,Transform parent){var g=new GameObject(name,typeof(RectTransform));g.transform.SetParent(parent,false);return (RectTransform)g.transform;}
        static void Stretch(RectTransform r){r.anchorMin=Vector2.zero;r.anchorMax=Vector2.one;r.offsetMin=r.offsetMax=Vector2.zero;}
        static void Place(RectTransform r,float x,float y,float w,float h){r.anchorMin=r.anchorMax=r.pivot=new Vector2(0,1);r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(w,h);}
    }
}

using System;
using System.Collections;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace HeartOfTheRain.App.Launch
{
    // Only this lightweight scene owns the transient launch artwork. The original
    // game scene remains responsible for saved-game recovery and tutorial routing.
    public sealed class LaunchPage:MonoBehaviour
    {
        public const string ScenePath="Assets/HeartOfTheRain/App/Launch/Scenes/Launch.unity";
        public const string GameScenePath="Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity";
        public Texture2D keyArt,title;
        public Sprite loadingTrack,loadingFill,loadingFrame;
        public Font font;
        Canvas canvas;
        RawImage art,logo;
        Image footer,track,fill,outline;
        RectTransform fillArea;
        Text status;
        Vector2Int dimensions;
        Rect safe;
        int locale=-1;
        bool failed,finishing;
        public float Progress {get;private set;}
        public bool Failed=>failed;
#if UNITY_EDITOR
        [HideInInspector] public bool HoldForReview;
#endif
        static readonly string[] Loading={"Loading…","Cargando…","Chargement…","Wird geladen…","Загрузка…"};
        static readonly string[] Error={"Unable to start. Please restart the app.","No se pudo iniciar. Reinicia la aplicación.","Démarrage impossible. Redémarrez l’application.","Start nicht möglich. Bitte starte die App neu.","Не удалось запустить. Перезапустите приложение."};

        void Awake()
        {
            Application.targetFrameRate=60;
            StartupMilestones99.Mark("launch_awake");
            DontDestroyOnLoad(gameObject);
            var root=Node("Launch Canvas",transform);canvas=root.gameObject.AddComponent<Canvas>();
            canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=32760;canvas.referencePixelsPerUnit=100;
#if UNITY_2022_3_OR_NEWER
            canvas.vertexColorAlwaysGammaSpace=true;
#endif
            root.gameObject.AddComponent<GraphicRaycaster>();
            var matte=Node("Launch matte and input shield",root);matte.anchorMin=Vector2.zero;matte.anchorMax=Vector2.one;matte.sizeDelta=Vector2.zero;
            matte.gameObject.AddComponent<Image>().color=new Color(.035f,.085f,.16f,1);
            art=Node("Opening artwork",root).gameObject.AddComponent<RawImage>();art.texture=keyArt;art.raycastTarget=false;
            logo=Node("Title artwork",root).gameObject.AddComponent<RawImage>();logo.texture=title;logo.raycastTarget=false;
            footer=Node("Loading footer",root).gameObject.AddComponent<Image>();footer.color=Color.clear;footer.raycastTarget=false;
            track=Skin("Loading track",root,loadingTrack);
            fillArea=Node("Loading fill area",track.transform);fillArea.anchorMin=Vector2.zero;fillArea.anchorMax=Vector2.one;
            fill=Skin("Actual loading progress",fillArea,loadingFill);
            outline=Skin("Loading frame",track.transform,loadingFrame);outline.rectTransform.anchorMin=Vector2.zero;outline.rectTransform.anchorMax=Vector2.one;outline.rectTransform.offsetMin=outline.rectTransform.offsetMax=Vector2.zero;
            status=Node("Loading status",root).gameObject.AddComponent<Text>();status.font=font;status.alignment=TextAnchor.MiddleCenter;status.color=new Color(1,.96f,.85f);status.raycastTarget=false;
            status.resizeTextForBestFit=true;status.resizeTextMinSize=10;status.resizeTextMaxSize=28;
            status.horizontalOverflow=HorizontalWrapMode.Wrap;status.verticalOverflow=VerticalWrapMode.Truncate;
            var shadow=status.gameObject.AddComponent<Outline>();shadow.effectColor=new Color(0,.025f,.07f,.9f);shadow.effectDistance=new Vector2(1,-1);
            Reflow();SetProgress(0);
            StartupMilestones99.Mark("launch_ui_created");
            StartCoroutine(TraceSubmittedLaunchFrame());
        }

        IEnumerator Start()
        {
#if UNITY_EDITOR
            if(HoldForReview)yield break;
#endif
            // Render the supplied artwork before starting scene IO; no branding timer.
            yield return null;
            StartupMilestones99.Mark("begin_game_scene_load");
            AsyncOperation operation=BeginLoad();
            if(operation==null)yield break;
            while(!operation.isDone){SetProgress(Mathf.Min(.9f,operation.progress));yield return null;}
            StartupMilestones99.Mark("game_scene_loaded");
            // FirstStart yields once while Home/profile initialization runs. Do not
            // dismiss the shield during that frame or manufacture 100% readiness.
            float deadline=Time.realtimeSinceStartup+30;
            string readyRoute="route_unknown";
            while(true)
            {
                var first=FindFirstObjectByType<FirstStartPage>();
                if(first&&first.Failed){Fail();yield break;}
                if(first&&first.Initialized)
                {
                    var home=first.home;
                    if(home&&(first.IsVisible||home.PresentationVisible)){readyRoute=first.IsVisible?"route_tutorial":"route_home";break;}
                }
                if(Time.realtimeSinceStartup>deadline){Fail();yield break;}
                yield return null;
            }
            SetProgress(1);yield return null;
            StartupMilestones99.Mark(readyRoute);
            finishing=true;ReleaseArtwork();Destroy(gameObject);
        }
        IEnumerator TraceSubmittedLaunchFrame()
        {
            // The first frame is still in the render and present queue at its end of frame.
            // Removing the native cover then exposed one to two grey or black frames.
            yield return new WaitForEndOfFrame();yield return null;yield return null;yield return new WaitForEndOfFrame();
            StartupMilestones99.SubmitLogoFrame();
        }

        AsyncOperation BeginLoad()
        {
            try
            {
                if(!Application.CanStreamedLevelBeLoaded(GameScenePath))throw new InvalidOperationException("Game scene is missing from the build.");
                return SceneManager.LoadSceneAsync(GameScenePath,LoadSceneMode.Single);
            }
            catch(Exception e){Debug.LogError("Launch failed: "+e.Message,this);Fail();return null;}
        }
        void Fail(){failed=true;track.gameObject.SetActive(false);RefreshText();}
        void SetProgress(float value)
        {
            Progress=Mathf.Max(Progress,Mathf.Clamp01(value));
            if(fill){fill.gameObject.SetActive(Progress>0);var r=fill.rectTransform;r.anchorMin=Vector2.zero;r.anchorMax=new Vector2(Progress,1);r.offsetMin=r.offsetMax=Vector2.zero;}
        }
        void RefreshText(){locale=GameLocale.Current;if(status)status.text=(failed?Error:Loading)[GameLocale.Valid(locale)?locale:0];}
        void Update()
        {
            if(dimensions.x!=Screen.width||dimensions.y!=Screen.height||safe!=Screen.safeArea)Reflow();
            if(locale!=GameLocale.Current)RefreshText();
        }
        public void Reflow()
        {
            if(!canvas)return;dimensions=new Vector2Int(Screen.width,Screen.height);safe=Screen.safeArea;
            var f=LaunchLayout.Build(Screen.width,Screen.height,safe);
            Place(art.rectTransform,f.art);art.uvRect=f.uv;Place(logo.rectTransform,f.logo);
            Place(footer.rectTransform,f.footer);Place(track.rectTransform,f.track);Place(status.rectTransform,f.status);
            // Four source pixels per reference unit; scale the complete 240x12
            // composition uniformly, including its inset and sliced round ends.
            float barScale=f.track.height/12f;
            fillArea.offsetMin=Vector2.one*barScale;fillArea.offsetMax=-Vector2.one*barScale;
            track.pixelsPerUnitMultiplier=fill.pixelsPerUnitMultiplier=outline.pixelsPerUnitMultiplier=1/barScale;
            status.fontSize=Mathf.Clamp(Mathf.RoundToInt(f.status.width*.055f),14,28);RefreshText();
        }
        void ReleaseArtwork()
        {
            if(art)art.texture=null;if(logo)logo.texture=null;
            var a=keyArt;var t=title;keyArt=null;title=null;
            if(a)Resources.UnloadAsset(a);if(t&&t!=a)Resources.UnloadAsset(t);
            var skins=new[]{loadingTrack,loadingFill,loadingFrame};track.sprite=fill.sprite=outline.sprite=null;loadingTrack=loadingFill=loadingFrame=null;
            foreach(var sprite in skins)if(sprite){var texture=sprite.texture;Resources.UnloadAsset(sprite);if(texture)Resources.UnloadAsset(texture);}
        }
        void OnDestroy()
        {
            // Editor review scenes share AssetDatabase objects. Only the completed
            // real load explicitly releases its private launch textures.
            if(!finishing){if(art)art.texture=null;if(logo)logo.texture=null;}
        }
        static RectTransform Node(string name,Transform parent){var r=new GameObject(name,typeof(RectTransform)).GetComponent<RectTransform>();r.SetParent(parent,false);r.anchorMin=r.anchorMax=r.pivot=Vector2.zero;return r;}
        static Image Skin(string name,Transform parent,Sprite sprite){var image=Node(name,parent).gameObject.AddComponent<Image>();image.sprite=sprite;image.color=Color.white;image.type=Image.Type.Sliced;image.raycastTarget=false;return image;}
        static void Place(RectTransform node,Rect r){node.anchorMin=node.anchorMax=node.pivot=Vector2.zero;node.anchoredPosition=r.position;node.sizeDelta=r.size;}
    }
}

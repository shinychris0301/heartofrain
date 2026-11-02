using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.ServerRewards;
namespace HeartOfTheRain.App.Profile {
    [DisallowMultipleComponent] public sealed class DailyGiftPage:MonoBehaviour {
        HomePage home;PreLevelAssets assets;PlayerProfileHost profile;Canvas canvas;CanvasScaler scaler;RectTransform safe,content,panel,viewport;ScrollRect scroll;CanvasGroup fade;DailyGiftDesignAssets design;RawImage backdrop;Image shade;RenderTexture blurred;Sprite backdropSource;Coroutine motion,opening;int presentationEpoch;
        readonly Dictionary<string,RectTransform> nodes=new Dictionary<string,RectTransform>();DailyGiftView view;Action retry;bool busy;int revision;Vector2Int dimensions;Rect lastSafe;float scale;
        bool remoteBusy,remoteClaim,remoteError,remoteRetryClaim,remoteReceived;
        ServerRewardsSession serverRewards;bool ServerMode=>profile&&profile.ServerSession&&!profile.LocalEconomyMode;
        public bool IsVisible=>canvas&&canvas.gameObject.activeSelf;
        public bool IsNetworkBusy=>remoteBusy;
        public void Configure(HomePage home,PreLevelAssets assets,PlayerProfileHost profile){this.home=home;this.assets=assets;this.profile=profile;home.NavigationRequested.AddListener(Route);}
        void Route(string route){if(route=="daily"||route=="drawer-daily")Show();else if(route=="home"||route=="journey"||route=="leaderboard"||route=="teams"||route=="team"||route=="shop"||route=="settings"||route=="coins"||route=="wellworks"||route=="drawer-wellworks")Hide(false);}
        // First use from Home loads the art off the tap frame, so Home stays responsive.
        // A switch from another open page keeps its immediate hand-over.
        bool designLoading;
        System.Collections.IEnumerator LoadDesignThenShow(){designLoading=true;yield return DailyGiftDesignAssets.LoadAsync();designLoading=false;design=DailyGiftDesignAssets.Load();Show();}
        public void Show(){var flow=home.GetComponent<HomeLevelFlow>();if(!flow||!flow.CanOpenAppSettings||designLoading)return;if(!design&&home.PresentationInteractable){StartCoroutine(LoadDesignThenShow());return;}presentationEpoch++;retry=null;LoadView();
            var cup=home.GetComponent<RainCupPage>();if(cup)cup.Hide(false);
            var works=home.GetComponent<WellworksPage>();if(works)works.Hide(false);
            var journey=home.GetComponent<HeartOfTheRain.App.Journey.JourneyPage>();if(journey)journey.Hide(false);
            var ranks=home.GetComponent<HeartOfTheRain.App.Leaderboard.LeaderboardPage>();if(ranks)ranks.Hide(false);
            var teams=home.GetComponent<HeartOfTheRain.App.Teams.TeamsPage>();if(teams)teams.Hide(false);
            var shop=home.GetComponent<HeartOfTheRain.App.Shop.ShopPage>();if(shop)shop.Hide(false);
            var settings=home.GetComponent<HeartOfTheRain.App.AppSettings.AppSettingsPage>();if(settings)settings.Hide(false);
            home.ShowEvents(false);Open();if(ServerMode){if(!remoteBusy)BeginServer(false);}else if(profile.BackendGifts!=null&&!view.error&&!remoteBusy){remoteReceived=false;BeginRemote(false);}}
        void LoadView(){
            if(ServerMode){serverRewards=ServerRewardsSession.Select(profile.ServerSession);var state=serverRewards.Coordinator;bool bound=state.PlayerId==profile.ServerSession.PlayerId;var offer=bound?state.Offer:null;view=new DailyGiftView{schedule=profile.Schedule,offer=offer?.Offer(),claims=offer==null?0:offer.step+(offer.claimed?1:0),development=false,loading=remoteBusy,claiming=remoteClaim,networkError=remoteError,received=remoteReceived,pending=bound&&state.HasPending};return;}
            view=new DailyGiftView{schedule=profile.Schedule,development=profile.Gifts!=null&&profile.Gifts.IsDevelopment};
            try{if(!profile.Ready&&!profile.Refresh())throw new InvalidOperationException("Save unavailable");view.schedule=profile.Schedule;view.development=profile.Gifts.IsDevelopment||profile.BackendGifts!=null;var p=profile.Service.Read();view.claims=p.giftClaims;view.pending=p.pendingGift!=null;view.offer=profile.BackendGifts!=null?profile.BackendGifts.Offer:profile.Gifts.Offer();if(p.pendingGift!=null){var pending=p.pendingGift;view.offer=new GiftOffer{id=pending.offerId,schedule=pending.schedule,day=pending.day,step=pending.step,grant=pending.expectedGrant.Copy()};}if(profile.BackendGifts!=null){view.loading=remoteBusy;view.claiming=remoteClaim;view.networkError=remoteError;view.received=remoteReceived;}}catch(Exception){view.error=true;retry=()=>{profile.Refresh();Show();};}
        }
        Action dismissError;Func<bool> errorSettled;bool errorOverHome;
        public void ShowError(Action retry,Action dismiss=null,Func<bool> settled=null,bool connection=false){this.retry=retry;dismissError=dismiss;errorSettled=settled;errorOverHome=home.PresentationInteractable;view=new DailyGiftView{schedule=profile.Schedule,error=true,errorDismissible=dismiss!=null,errorConnection=connection};Open();}
        void Open(){Build();canvas.gameObject.SetActive(true);home.SetPresentation(!view.error||home.PresentationVisible,false);Render();Focus(view.error?"claim":"close");if(!home.State.reduceMotion)opening=StartCoroutine(OpenMotion());}
        void Build(){if(canvas)return;var root=Rect("Daily Gift Canvas",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=310;
#if UNITY_2022_3_OR_NEWER
            canvas.vertexColorAlwaysGammaSpace=true;
#endif
            scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;root.gameObject.AddComponent<GraphicRaycaster>();fade=root.gameObject.AddComponent<CanvasGroup>();
            design=DailyGiftDesignAssets.Load();if(!design)throw new InvalidOperationException("Daily Gift design bindings missing");
            var bg=Rect("Chapter backdrop",root);Stretch(bg);backdrop=bg.gameObject.AddComponent<RawImage>();backdrop.raycastTarget=false;
            var dim=Rect("Modal shade",root);Stretch(dim);shade=dim.gameObject.AddComponent<Image>();shade.color=new Color(7/255f,18/255f,40/255f,.439f);
            safe=Rect("Safe area",root);content=Rect("Gift content",safe);
        }
        public void Hide(bool restore=true){if(!IsVisible||busy)return;if(view.error&&retry!=null){if(!restore||dismissError==null)return;var leave=dismissError;retry=null;dismissError=null;errorSettled=null;errorOverHome=false;canvas.gameObject.SetActive(false);leave();return;}presentationEpoch++;CancelMotion();canvas.gameObject.SetActive(false);if(design)design.ReleaseArt();if(restore)home.SetPresentation(true,true);}
        public void Request(string action){
            if(!IsVisible||busy||string.IsNullOrEmpty(action)||action=="disabled")return;
            if(action=="close"){Hide();return;}if(action!="claim"||view.loading)return;
            if(view.error&&retry!=null){
                // Home goes back to how it was first: the retry may open nothing, and must not leave Home dead.
                var callback=retry;bool overHome=errorOverHome;canvas.gameObject.SetActive(false);retry=null;dismissError=null;errorSettled=null;errorOverHome=false;
                if(overHome)home.SetPresentation(true,true);callback();return;
            }
            if(ServerMode){if(!remoteBusy)BeginServer(!remoteError||remoteRetryClaim);return;}
            if(profile.BackendGifts!=null){if(!remoteBusy)BeginRemote(!remoteError||remoteRetryClaim);return;}
            busy=true;
            try{
                var grant=profile.Gifts.Claim();profile.Refresh();LoadView();view.received=grant!=null;Render();
                // Inventory/wallet are already committed; this is cosmetic.
                if(grant!=null){home.PlayRewardReveal(grant.coins,grant.stars,home.State.completedLevelsInChapter);PlayCollection();}
            }catch(Exception){LoadView();view.pending=true;Render();}
            finally{busy=false;}
        }
        void BeginServer(bool claim){remoteBusy=true;remoteClaim=claim;remoteError=false;remoteRetryClaim=claim;remoteReceived=false;LoadView();if(IsVisible){Render();Focus("close");}StartCoroutine(ServerRemote(claim,presentationEpoch));}
        IEnumerator ServerRemote(bool claim,int epoch){
            var session=profile.ServerSession;var coordinator=ServerRewardsSession.Select(session).Coordinator;RewardCompletion completion=null;
            try{yield return claim?coordinator.ClaimDaily(value=>completion=value):coordinator.Refresh("Daily",value=>completion=value);}finally{remoteBusy=false;}
            if(!this||profile.ServerSession!=session)yield break;remoteError=completion==null||!completion.ok;remoteReceived=!remoteError&&completion.kind=="Daily"&&completion.grant!=null;
            if(IsVisible&&!(view.error&&retry!=null)){LoadView();Render();Focus("close");if(remoteReceived&&epoch==presentationEpoch)PlayCollection();}
        }
        void BeginRemote(bool claim){remoteBusy=true;remoteClaim=claim;remoteError=false;remoteRetryClaim=claim;LoadView();if(IsVisible){Render();Focus("close");}StartCoroutine(Remote(claim,presentationEpoch));}
        IEnumerator Remote(bool claim,int epoch){
            RewardGrant grant=null;string error=null;
            try{
                if(claim)yield return profile.BackendGifts.Claim((value,why)=>{grant=value;error=why;});
                else yield return profile.BackendGifts.Refresh((ok,why)=>error=ok?null:why);
            }finally{remoteBusy=false;}
            remoteError=error!=null;remoteReceived=grant!=null;profile.Refresh();
            // Closing or navigating away never cancels a durable intent or
            // reopens the modal when the request completes. Fatal save dialogs
            // retain their own retry callback and cannot be replaced here.
            if(IsVisible&&!(view.error&&retry!=null)){LoadView();Render();Focus("close");}
            if(grant!=null&&home.PresentationVisible){home.PlayRewardReveal(grant.coins,grant.stars,home.State.completedLevelsInChapter);if(IsVisible&&epoch==presentationEpoch)PlayCollection();}
        }
        void PlayCollection(){CancelMotion();if(IsVisible&&!home.State.reduceMotion)motion=StartCoroutine(Collection());}
        void CancelMotion(){if(motion!=null)StopCoroutine(motion);if(opening!=null)StopCoroutine(opening);motion=opening=null;if(fade)fade.alpha=1;if(panel)panel.localScale=Vector3.one;foreach(string id in new[]{"chest","reward"})if(nodes.TryGetValue(id,out var n)&&n){n.localScale=Vector3.one;n.localRotation=Quaternion.Euler(0,0,id=="chest"?-4:0);}if(nodes.TryGetValue("hero",out var hero)&&hero){var fx=hero.Find("Collection effects");if(fx){fx.gameObject.SetActive(false);Destroy(fx.gameObject);}}}
        IEnumerator OpenMotion(){var start=panel.anchoredPosition;for(float t=0;t<.25f;t+=Time.unscaledDeltaTime){float u=1-Mathf.Pow(1-t/.25f,3);fade.alpha=u;panel.localScale=Vector3.one*Mathf.Lerp(.98f,1,u);panel.anchoredPosition=start+Vector2.down*10*(1-u);yield return null;}fade.alpha=1;panel.localScale=Vector3.one;panel.anchoredPosition=start;opening=null;}
        IEnumerator Collection(){
            if(!nodes.TryGetValue("hero",out var hero)||!nodes.TryGetValue("chest",out var chest)||!nodes.TryGetValue("reward",out var reward))yield break;
            var fx=Rect("Collection effects",hero);Stretch(fx);var light=Rect("Warm light",fx);Place(light,0,0,hero.rect.width,hero.rect.height);light.pivot=new Vector2(.5f,.5f);light.anchoredPosition=new Vector2(hero.rect.width*.5f,-hero.rect.height*.5f);var glow=light.gameObject.AddComponent<DailyGiftGlow>();glow.raycastTarget=false;
            var stars=new Image[14];var origin=new Vector2(hero.rect.width*.5f,-hero.rect.height*.3f);
            for(int i=0;i<stars.Length;i++){var r=Rect("Gold glint "+i,fx);r.anchorMin=r.anchorMax=r.pivot=new Vector2(.5f,.5f);r.anchorMin=r.anchorMax=new Vector2(0,1);r.sizeDelta=Vector2.one*22;r.anchoredPosition=origin;stars[i]=r.gameObject.AddComponent<Image>();stars[i].sprite=design.star;stars[i].raycastTarget=false;stars[i].color=new Color(1,1,1,0);}
            for(float t=0;t<.925f;t+=Time.unscaledDeltaTime){
                if(!IsVisible||home.State.reduceMotion)break;
                float u=Mathf.Clamp01(t/.65f),angle=u<.3f?Mathf.Lerp(-4,3,u/.3f):u<.65f?Mathf.Lerp(3,-6,(u-.3f)/.35f):Mathf.Lerp(-6,-4,(u-.65f)/.35f);
                float cs=u<.3f?Mathf.Lerp(1,1.12f,u/.3f):u<.65f?Mathf.Lerp(1.12f,.99f,(u-.3f)/.35f):Mathf.Lerp(.99f,1,(u-.65f)/.35f);
                chest.localRotation=Quaternion.Euler(0,0,angle);chest.localScale=Vector3.one*cs;
                float v=Mathf.Clamp01(t/.6f);reward.localScale=Vector3.one*(v<.4f?Mathf.Lerp(.85f,1.15f,v/.4f):Mathf.Lerp(1.15f,1,(v-.4f)/.6f));
                glow.color=new Color(1,.86f,.5f,.4f*(1-Mathf.Clamp01(t/.7f)));light.localScale=Vector3.one*Mathf.Lerp(.7f,1.2f,Mathf.Clamp01(t/.7f));
                for(int i=0;i<stars.Length;i++){float k=Mathf.Clamp01((t-i%4*.025f)/.85f),a=i/14f*Mathf.PI*2;var r=stars[i].rectTransform;r.anchoredPosition=origin+new Vector2(Mathf.Cos(a)*(90+i%3*18),-Mathf.Sin(a)*75+25)*k;r.localRotation=Quaternion.Euler(0,0,i*39*k);r.localScale=Vector3.one*Mathf.Lerp(.2f,.5f,k);stars[i].color=new Color(1,1,1,k<.18f?k/.18f:1-(k-.18f)/.82f);}
                yield return null;
            }
            chest.localScale=reward.localScale=Vector3.one;chest.localRotation=Quaternion.Euler(0,0,-4);fx.gameObject.SetActive(false);Destroy(fx.gameObject);motion=null;
        }
        float DesiredScale(Rect area)=>Mathf.Max(.25f,Mathf.Min(home.CurrentUIScale,Mathf.Min((area.width>0?area.width:Screen.width)/320,(area.height>0?area.height:Screen.height)/300)));
        void Update(){if(!IsVisible)return;if(view.error&&retry!=null&&errorSettled!=null&&errorSettled()){Request("claim");return;}if(dimensions.x!=Screen.width||dimensions.y!=Screen.height||lastSafe!=Screen.safeArea||revision!=GameLocale.Revision||Mathf.Abs(scale-DesiredScale(Screen.safeArea))>.01f)Render();
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
            bool back=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
            bool back=Input.GetKeyDown(KeyCode.Escape);
#endif
            if(back)Request("close");
        }
        void Render(){
            CancelMotion();foreach(Transform t in content){t.gameObject.SetActive(false);Destroy(t.gameObject);}nodes.Clear();var sr=Screen.safeArea;if(sr.width<=0||sr.height<=0)sr=new Rect(0,0,Screen.width,Screen.height);
            scale=DesiredScale(sr);scaler.scaleFactor=canvas.scaleFactor=scale;scaler.referencePixelsPerUnit=100;Place(safe,sr.x/scale,(Screen.height-sr.yMax)/scale,sr.width/scale,sr.height/scale);
            var frame=DailyGiftLayout.Build(sr.width/scale,sr.height/scale,view);Place(content,0,0,frame.width,frame.height);
            foreach(var e in frame.elements){var parent=string.IsNullOrEmpty(e.parent)?content:nodes[e.parent];var rt=Rect(e.id,parent);Place(rt,e.x,e.y,e.width,e.height);nodes[e.id]=rt;
                if(e.kind=="group"){
                    if(e.id=="panel")panel=rt;
                    if(e.id=="viewport"){viewport=rt;rt.gameObject.AddComponent<Image>().color=Color.clear;rt.gameObject.AddComponent<RectMask2D>();scroll=rt.gameObject.AddComponent<ScrollRect>();scroll.viewport=rt;scroll.horizontal=false;scroll.movementType=ScrollRect.MovementType.Clamped;scroll.scrollSensitivity=32;}
                    if(e.id=="body")scroll.content=rt;
                    if(string.IsNullOrEmpty(e.action))continue;var hit=rt.gameObject.AddComponent<Image>();hit.color=Color.clear;var button=rt.gameObject.AddComponent<Button>();button.targetGraphic=hit;button.transition=Selectable.Transition.None;button.interactable=e.action!="disabled";string action=e.action;button.onClick.AddListener(()=>Request(action));var label=rt.gameObject.AddComponent<HomeControlLabel>();label.action=action;label.label=e.id=="close"?DailyGiftDesignText.T("close"):DailyGiftDesignText.T("claim");
                }else if(e.kind=="text"){
                    var t=rt.gameObject.AddComponent<Text>();bool title=e.id=="title"||e.id.Contains("label")||e.id.Contains("quantity")||e.id.Contains("heading");t.font=title?design.titleFont:design.bodyFont;t.text=e.text;t.fontSize=e.fontSize;ColorUtility.TryParseHtmlString(e.color,out var color);t.color=color;t.alignment=TextAnchor.MiddleCenter;t.raycastTarget=false;t.supportRichText=false;t.horizontalOverflow=HorizontalWrapMode.Wrap;t.verticalOverflow=VerticalWrapMode.Truncate;
                    if(e.id=="title"){t.fontSize=e.width<=250?22:24;if(GameLocale.Current!=4)t.fontSize=e.fontSize;t.lineSpacing=.9f;var shadow=t.gameObject.AddComponent<Shadow>();shadow.effectColor=new Color(0,.05f,.15f,.9f);shadow.effectDistance=new Vector2(0,-2);}
                    while(t.preferredHeight>e.height+.1f&&t.fontSize>10)t.fontSize--;
                }else if(e.kind=="dot"){var dot=rt.gameObject.AddComponent<DailyGiftGlow>();dot.solidCircle=true;ColorUtility.TryParseHtmlString(e.color,out var c);dot.color=c;dot.raycastTarget=false;
                }else{var im=rt.gameObject.AddComponent<Image>();im.sprite=design.Find(e.asset);if(!im.sprite)throw new InvalidOperationException("Missing Daily Gift sprite: "+e.asset);im.raycastTarget=false;im.type=e.sliced?Image.Type.Sliced:Image.Type.Simple;im.preserveAspect=e.preserveAspect;im.pixelsPerUnitMultiplier=e.asset=="DG_Chrome"?3.891f:e.asset=="DG_Primary"?8.57f:e.sliced?6:1;im.color=Color.white;if(e.id=="chest")rt.localRotation=Quaternion.Euler(0,0,-4);}
            }
            scroll.vertical=scroll.content.rect.height>viewport.rect.height+.1f;scroll.verticalNormalizedPosition=1;
            nodes["claim"].GetComponent<HomeControlLabel>().label=nodes["claim-label"].GetComponent<Text>().text;
            foreach(string id in new[]{"close","claim"})if(nodes.TryGetValue(id,out var rt)){var graphics=new List<Graphic>();foreach(var g in rt.GetComponentsInChildren<Graphic>())if(g.transform!=rt)graphics.Add(g);rt.gameObject.AddComponent<PreLevelButtonFeedback>().Configure(graphics.ToArray(),home.State.reduceMotion);}
            // The node's own clear hit image stays invisible; only the art and label dim.
            if(nodes.TryGetValue("claim",out var primary)&&!primary.GetComponent<Button>().interactable)foreach(var graphic in primary.GetComponentsInChildren<Graphic>())if(graphic.transform!=primary)graphic.color=new Color(graphic.color.r,graphic.color.g,graphic.color.b,.65f);
            // The protected save-error dialog can open over a paused board: keep the board visible
            // behind a stronger shade instead of painting Home's chapter art and a blur over it.
            backdrop.gameObject.SetActive(!view.error);shade.color=new Color(7/255f,18/255f,40/255f,view.error?.74f:.439f);
            var source=view.error?null:home.ProfileBackground;if(source&&(!blurred||source!=backdropSource)){ProfileBackdrop.Release(blurred);blurred=ProfileBackdrop.Blur(source.texture);backdropSource=source;backdrop.texture=blurred?(Texture)blurred:source.texture;}
            if(!view.error&&backdrop.texture){float a=Screen.width/(float)Screen.height,b=backdrop.texture.width/(float)backdrop.texture.height;backdrop.uvRect=a>b?new Rect(0,(1-b/a)/2,1,b/a):new Rect((1-a/b)/2,0,a/b,1);}
            dimensions=new Vector2Int(Screen.width,Screen.height);lastSafe=sr;revision=GameLocale.Revision;
        }
        public static void FitText(Text text,float width,float height,bool paragraph){text.horizontalOverflow=paragraph?HorizontalWrapMode.Wrap:HorizontalWrapMode.Overflow;if(paragraph){while(text.fontSize>9&&text.preferredHeight>height+.01f)text.fontSize--;}else LabelFit.Apply(text,width,height,9);}
        void Focus(string id){RectTransform rt;if(EventSystem.current&&nodes.TryGetValue(id,out rt))EventSystem.current.SetSelectedGameObject(rt.gameObject);}
        void OnDestroy(){ProfileBackdrop.Release(blurred);if(home)home.NavigationRequested.RemoveListener(Route);}
        static RectTransform Rect(string name,Transform parent){var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);return (RectTransform)go.transform;}
        static void Stretch(RectTransform rt){rt.anchorMin=Vector2.zero;rt.anchorMax=Vector2.one;rt.offsetMin=rt.offsetMax=Vector2.zero;}
        static void Place(RectTransform rt,float x,float y,float w,float h){rt.anchorMin=rt.anchorMax=rt.pivot=new Vector2(0,1);rt.anchoredPosition=new Vector2(x,-y);rt.sizeDelta=new Vector2(w,h);}
    }
}

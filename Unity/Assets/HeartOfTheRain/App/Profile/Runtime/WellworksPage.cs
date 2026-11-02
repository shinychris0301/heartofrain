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
    [DisallowMultipleComponent] public sealed class WellworksPage:MonoBehaviour {
        HomePage home;PreLevelAssets assets;PlayerProfileHost profile;Canvas canvas;CanvasScaler scaler;RectTransform safe,content,panel,viewport;ScrollRect scroll;CanvasGroup fade,panelFade;WellworksDesignAssets design;RawImage backdrop;RenderTexture blurred;Sprite backdropSource;Coroutine motion,opening,progressMotion;int shownProgress=-1;
        ServerRewardsSession serverRewards;bool serverBusy,serverError,serverReceived;int presentationEpoch;bool ServerMode=>profile&&profile.ServerSession&&!profile.LocalEconomyMode;
        readonly Dictionary<string,RectTransform> nodes=new Dictionary<string,RectTransform>();WellworksView view;Action retry;bool busy;int revision;Vector2Int dimensions;Rect lastSafe;float scale;
        public bool IsVisible=>canvas&&canvas.gameObject.activeSelf;
        public void Configure(HomePage home,PreLevelAssets assets,PlayerProfileHost profile){this.home=home;this.assets=assets;this.profile=profile;home.NavigationRequested.AddListener(Route);}
        void Route(string route){if(route=="wellworks"||route=="drawer-wellworks")Show();else if(route=="home"||route=="journey"||route=="leaderboard"||route=="teams"||route=="team"||route=="shop"||route=="settings"||route=="coins"||route=="daily"||route=="drawer-daily")Hide(false);}
        // First use from Home loads the art off the tap frame, so Home stays responsive.
        // A switch from another open page keeps its immediate hand-over.
        bool designLoading;
        System.Collections.IEnumerator LoadDesignThenShow(){designLoading=true;yield return WellworksDesignAssets.LoadAsync();designLoading=false;design=WellworksDesignAssets.Load();Show();}
        public void Show(){var flow=home.GetComponent<HomeLevelFlow>();if(!flow||!flow.CanOpenAppSettings||designLoading)return;if(!design&&home.PresentationInteractable){StartCoroutine(LoadDesignThenShow());return;}presentationEpoch++;retry=null;LoadView();
            var cup=home.GetComponent<RainCupPage>();if(cup)cup.Hide(false);
            var gift=home.GetComponent<DailyGiftPage>();if(gift)gift.Hide(false);
            var journey=home.GetComponent<HeartOfTheRain.App.Journey.JourneyPage>();if(journey)journey.Hide(false);
            var ranks=home.GetComponent<HeartOfTheRain.App.Leaderboard.LeaderboardPage>();if(ranks)ranks.Hide(false);
            var teams=home.GetComponent<HeartOfTheRain.App.Teams.TeamsPage>();if(teams)teams.Hide(false);
            var shop=home.GetComponent<HeartOfTheRain.App.Shop.ShopPage>();if(shop)shop.Hide(false);
            var settings=home.GetComponent<HeartOfTheRain.App.AppSettings.AppSettingsPage>();if(settings)settings.Hide(false);
            home.ShowEvents(false);Open();if(ServerMode&&!serverBusy)BeginServer(0);}
        void LoadView(){
            if(ServerMode){serverRewards=ServerRewardsSession.Select(profile.ServerSession);var state=serverRewards.Coordinator;var data=state.PlayerId==profile.ServerSession.PlayerId?state.Wellworks:null;view=data==null?new WellworksView{schedule=profile.Wellworks.Schedule}:ServerRewardProjection.Wellworks(data,state.PlayerId);view.error=serverError&&data==null;view.claimError=serverError&&data!=null;view.received=serverReceived;view.enabled=view.enabled&&!serverBusy;return;}
            view=new WellworksView();
            try{if(!profile.Ready&&!profile.Refresh())throw new InvalidOperationException("Save unavailable");view.schedule=profile.Wellworks.Schedule;view.enabled=profile.Wellworks.Enabled;view.player=profile.Service.Read();}catch(Exception){view.error=true;retry=()=>{profile.Refresh();Show();};}
        }
        void Open(){Build();canvas.gameObject.SetActive(true);home.SetPresentation(!view.error||home.PresentationVisible,false);Render();Focus(view.error?"retry":"close");if(!home.State.reduceMotion)opening=StartCoroutine(OpenMotion());}
        void Build(){if(canvas)return;var root=Rect("Wellworks Canvas",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=310;
#if UNITY_2022_3_OR_NEWER
            canvas.vertexColorAlwaysGammaSpace=true;
#endif
            scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;root.gameObject.AddComponent<GraphicRaycaster>();fade=root.gameObject.AddComponent<CanvasGroup>();
            design=WellworksDesignAssets.Load();if(!design)throw new InvalidOperationException("Missing Wellworks design bindings");
            var bg=Rect("Chapter backdrop",root);Stretch(bg);backdrop=bg.gameObject.AddComponent<RawImage>();backdrop.raycastTarget=false;
            var dim=Rect("Modal shade",root);Stretch(dim);dim.gameObject.AddComponent<Image>().color=new Color(7/255f,18/255f,40/255f,.439f);
            safe=Rect("Safe area",root);content=Rect("Wellworks content",safe);
        }
        public void Hide(bool restore=true){if(!IsVisible||busy)return;presentationEpoch++;CancelMotion();canvas.gameObject.SetActive(false);if(design)design.ReleaseArt();if(restore)home.SetPresentation(true,true);}
        public void Request(string action){
            if(!IsVisible||busy||string.IsNullOrEmpty(action)||action=="disabled")return;
            if(action=="close"){Hide();return;}
            if(action=="retry"&&ServerMode){if(!serverBusy)BeginServer(0);return;}
            if(action=="retry"){var callback=retry;retry=null;if(callback!=null)callback();else{profile.Refresh();LoadView();Render();}return;}
            int level;if(!action.StartsWith("claim-",StringComparison.Ordinal)||!int.TryParse(action.Substring(6),out level))return;
            if(ServerMode){if(!serverBusy)BeginServer(level);return;}
            float position=scroll?scroll.verticalNormalizedPosition:1;busy=true;
            try{
                var grant=profile.Wellworks.Claim(level);profile.Refresh();LoadView();view.received=grant!=null;Render();scroll.verticalNormalizedPosition=position;Focus("close");
                // The service commits the receipt and balances before cosmetics.
                if(grant!=null){home.PlayRewardReveal(grant.coins,grant.stars,home.State.completedLevelsInChapter);PlayCollection(level);}
            }catch(Exception){profile.Refresh();LoadView();bool saved=!view.error&&view.player!=null&&WellworksService.Claimed(view.player,level);view.received=saved;view.claimError=!view.error&&!saved;Render();scroll.verticalNormalizedPosition=position;Focus("close");}
            finally{busy=false;}
        }
        void BeginServer(int level){serverBusy=true;serverError=false;serverReceived=false;LoadView();if(IsVisible){Render();Focus("close");}StartCoroutine(ServerRemote(level,presentationEpoch));}
        IEnumerator ServerRemote(int level,int epoch){
            var session=profile.ServerSession;var coordinator=ServerRewardsSession.Select(session).Coordinator;RewardCompletion completion=null;float position=scroll?scroll.verticalNormalizedPosition:1;
            try{yield return level>0?coordinator.ClaimWellworks(level,value=>completion=value):coordinator.Refresh("Wellworks",value=>completion=value);}finally{serverBusy=false;}
            if(!this||profile.ServerSession!=session)yield break;serverError=completion==null||!completion.ok;serverReceived=!serverError&&completion.kind=="Wellworks"&&completion.grant!=null;
            if(IsVisible){LoadView();Render();if(scroll)scroll.verticalNormalizedPosition=position;Focus("close");if(serverReceived&&epoch==presentationEpoch&&int.TryParse(completion.target,out var receivedLevel))PlayCollection(receivedLevel);}
        }
        float DesiredScale(Rect area)=>Mathf.Max(.25f,Mathf.Min(home.CurrentUIScale,Mathf.Min((area.width>0?area.width:Screen.width)/320,(area.height>0?area.height:Screen.height)/300)));
        void Update(){if(!IsVisible)return;if(dimensions.x!=Screen.width||dimensions.y!=Screen.height||lastSafe!=Screen.safeArea||revision!=GameLocale.Revision||Mathf.Abs(scale-DesiredScale(Screen.safeArea))>.01f)Render();
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
            var frame=WellworksLayout.Build(sr.width/scale,sr.height/scale,view);Place(content,0,0,frame.width,frame.height);
            foreach(var e in frame.elements){var parent=string.IsNullOrEmpty(e.parent)?content:nodes[e.parent];var rt=Rect(e.id,parent);Place(rt,e.x,e.y,e.width,e.height);nodes[e.id]=rt;
                if(e.kind=="group"){
                    if(e.id=="panel"){panel=rt;panelFade=rt.gameObject.AddComponent<CanvasGroup>();}
                    if(e.id=="viewport"){viewport=rt;rt.gameObject.AddComponent<Image>().color=Color.clear;rt.gameObject.AddComponent<RectMask2D>();scroll=rt.gameObject.AddComponent<ScrollRect>();scroll.viewport=rt;scroll.horizontal=false;scroll.movementType=ScrollRect.MovementType.Clamped;scroll.scrollSensitivity=32;}
                    if(e.id=="body")scroll.content=rt;
                    if(e.id=="progress-clip"){rt.gameObject.AddComponent<RectMask2D>();rt.gameObject.SetActive(e.width>0);}
                    if(string.IsNullOrEmpty(e.action))continue;var hit=rt.gameObject.AddComponent<Image>();hit.color=Color.clear;var b=rt.gameObject.AddComponent<Button>();b.targetGraphic=hit;b.transition=Selectable.Transition.None;b.interactable=e.action!="disabled";string action=e.action;b.onClick.AddListener(()=>Request(action));var label=rt.gameObject.AddComponent<HomeControlLabel>();label.action=action;label.label=action=="close"?WellworksDesignText.T("close"):action=="retry"?WellworksText.T("Please try again"):WellworksDesignText.T("claim");
                }else if(e.kind=="text"){
                    var t=rt.gameObject.AddComponent<Text>();bool bold=e.id=="title"||e.id.Contains("label")||e.id.Contains("title")||e.id.Contains("quantity")||e.id=="heading"||e.id=="progress-count";t.font=bold?design.shared.titleFont:design.shared.bodyFont;t.text=e.text;t.fontSize=e.fontSize;ColorUtility.TryParseHtmlString(e.color,out var color);t.color=color;t.alignment=TextAnchor.MiddleCenter;t.raycastTarget=false;t.supportRichText=false;t.verticalOverflow=VerticalWrapMode.Truncate;
                    if(e.id.StartsWith("claim-",StringComparison.Ordinal)&&e.id.EndsWith("-label",StringComparison.Ordinal)){t.horizontalOverflow=HorizontalWrapMode.Overflow;while(t.fontSize>12&&t.preferredWidth>e.width+.01f)t.fontSize--;}
                    else{t.horizontalOverflow=HorizontalWrapMode.Wrap;while(t.fontSize>9&&t.preferredHeight>e.height+.01f)t.fontSize--;}
                    if(e.id=="title"){var shadow=t.gameObject.AddComponent<Shadow>();shadow.effectColor=new Color(0,.05f,.15f,.9f);shadow.effectDistance=new Vector2(0,-2);}
                }else{var im=rt.gameObject.AddComponent<Image>();im.sprite=design.Find(e.asset)??assets.Find(e.asset);if(!im.sprite)throw new InvalidOperationException("Missing Wellworks sprite: "+e.asset);im.raycastTarget=false;im.type=e.sliced?Image.Type.Sliced:Image.Type.Simple;im.preserveAspect=e.preserveAspect;im.pixelsPerUnitMultiplier=e.sliced?WellworksDesignAssets.Multiplier(e.asset):1;im.color=Color.white;}
            }
            scroll.vertical=scroll.content.rect.height>viewport.rect.height+.1f;scroll.verticalNormalizedPosition=1;
            foreach(var e in frame.elements)if(e.kind=="group"&&!string.IsNullOrEmpty(e.action)){var rt=nodes[e.id];var graphics=new List<Graphic>();foreach(var g in rt.GetComponentsInChildren<Graphic>())if(g.transform!=rt)graphics.Add(g);rt.gameObject.AddComponent<PreLevelButtonFeedback>().Configure(graphics.ToArray(),home.State.reduceMotion);}
            var source=home.ProfileBackground;if(source&&(!blurred||source!=backdropSource)){ProfileBackdrop.Release(blurred);blurred=ProfileBackdrop.Blur(source.texture);backdropSource=source;backdrop.texture=blurred?(Texture)blurred:source.texture;}
            if(backdrop.texture){float a=Screen.width/(float)Screen.height,b=backdrop.texture.width/(float)backdrop.texture.height;backdrop.uvRect=a>b?new Rect(0,(1-b/a)/2,1,b/a):new Rect((1-a/b)/2,0,a/b,1);}
            int now=view.player?.completed??0;if(shownProgress>=0&&now!=shownProgress&&!home.State.reduceMotion&&nodes.ContainsKey("progress-clip"))progressMotion=StartCoroutine(Progress(shownProgress,now));shownProgress=now;
            dimensions=new Vector2Int(Screen.width,Screen.height);lastSafe=Screen.safeArea;revision=GameLocale.Revision;
        }
        void CancelMotion(){if(motion!=null)StopCoroutine(motion);if(opening!=null)StopCoroutine(opening);if(progressMotion!=null)StopCoroutine(progressMotion);motion=opening=progressMotion=null;if(fade)fade.alpha=1;if(panelFade)panelFade.alpha=1;if(panel)panel.localScale=Vector3.one;foreach(var id in new[]{"well","rewards-0","rewards-1","rewards-2","rewards-3","rewards-4"})if(nodes.TryGetValue(id,out var rt)&&rt)rt.localScale=Vector3.one;if(panel){var fx=panel.Find("Milestone effects");if(fx){fx.gameObject.SetActive(false);Destroy(fx.gameObject);}}}
        IEnumerator OpenMotion(){var start=panel.anchoredPosition;for(float t=0;t<.25f;t+=Time.unscaledDeltaTime){float u=1-Mathf.Pow(1-t/.25f,3);panelFade.alpha=u;panel.localScale=Vector3.one*Mathf.Lerp(.98f,1,u);panel.anchoredPosition=start+Vector2.down*10*(1-u);yield return null;}panelFade.alpha=1;panel.localScale=Vector3.one;panel.anchoredPosition=start;opening=null;}
        IEnumerator Progress(int from,int to){for(float t=0;t<.4f;t+=Time.unscaledDeltaTime){SetProgress(Mathf.Lerp(from,to,1-Mathf.Pow(1-t/.4f,3))/50);yield return null;}SetProgress(to/50f);progressMotion=null;}
        void SetProgress(float value){if(!nodes.TryGetValue("progress-clip",out var clip))return;float width=(nodes["progress-track"].rect.width-8)*Mathf.Clamp01(value);clip.gameObject.SetActive(width>0);clip.SetSizeWithCurrentAnchors(RectTransform.Axis.Horizontal,width);nodes["fill"].SetSizeWithCurrentAnchors(RectTransform.Axis.Horizontal,Mathf.Max(12,width));}
        void PlayCollection(int level){if(home.State.reduceMotion||!IsVisible)return;if(motion!=null)StopCoroutine(motion);int i=Array.FindIndex(view.schedule.milestones,m=>m.level==level);if(i>=0)motion=StartCoroutine(Collection(i));}
        IEnumerator Collection(int index){
            var row=nodes["stage-"+index];var reward=nodes["rewards-"+index];bool final=true;foreach(var m in view.schedule.milestones)if(!WellworksService.Claimed(view.player,m.level))final=false;
            var fx=Rect("Milestone effects",panel);Stretch(fx);var origin=(Vector2)panel.InverseTransformPoint(row.TransformPoint(new Vector3(row.rect.width*.54f,-row.rect.height*.5f,0)));int count=final?14:10;var stars=new Image[count];
            for(int i=0;i<count;i++){var rt=Rect("Milestone glint "+i,fx);rt.anchorMin=rt.anchorMax=new Vector2(0,1);rt.pivot=Vector2.one*.5f;rt.anchoredPosition=origin;rt.sizeDelta=Vector2.one*20;var im=rt.gameObject.AddComponent<Image>();im.sprite=design.shared.star;im.raycastTarget=false;im.color=new Color(1,1,1,0);stars[i]=im;}
            for(float t=0;t<.84f;t+=Time.unscaledDeltaTime){if(!IsVisible||home.State.reduceMotion)break;float p=Mathf.Clamp01(t/.55f);reward.localScale=Vector3.one*(p<.45f?Mathf.Lerp(.88f,1.13f,p/.45f):Mathf.Lerp(1.13f,1,(p-.45f)/.55f));if(final){float k=Mathf.Clamp01(t/.65f);nodes["well"].localScale=Vector3.one*(k<.35f?Mathf.Lerp(1,1.06f,k/.35f):Mathf.Lerp(1.06f,1,(k-.35f)/.65f));}
                for(int i=0;i<count;i++){float k=Mathf.Clamp01((t-i%3*.02f)/.8f),a=i/(float)count*Mathf.PI*2;var rt=stars[i].rectTransform;rt.anchoredPosition=origin+new Vector2(Mathf.Cos(a)*(49+i%3*11),-Mathf.Sin(a)*41+18)*k;rt.localScale=Vector3.one*Mathf.Lerp(.2f,.4f,k);rt.localRotation=Quaternion.Euler(0,0,i*37*k);stars[i].color=new Color(1,1,1,k<.15f?k/.15f:1-(k-.15f)/.85f);}yield return null;
            }
            reward.localScale=Vector3.one;nodes["well"].localScale=Vector3.one;fx.gameObject.SetActive(false);Destroy(fx.gameObject);motion=null;
        }
        public static void FitText(Text text,float width,float height,bool paragraph){text.horizontalOverflow=paragraph?HorizontalWrapMode.Wrap:HorizontalWrapMode.Overflow;if(paragraph){while(text.fontSize>9&&text.preferredHeight>height+.01f)text.fontSize--;}else LabelFit.Apply(text,width,height,9);}
        void Focus(string id){RectTransform rt;if(EventSystem.current&&nodes.TryGetValue(id,out rt))EventSystem.current.SetSelectedGameObject(rt.gameObject);}
        void OnDestroy(){ProfileBackdrop.Release(blurred);if(home)home.NavigationRequested.RemoveListener(Route);}
        static RectTransform Rect(string name,Transform parent){var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);return (RectTransform)go.transform;}
        static void Stretch(RectTransform rt){rt.anchorMin=Vector2.zero;rt.anchorMax=Vector2.one;rt.offsetMin=rt.offsetMax=Vector2.zero;}
        static void Place(RectTransform rt,float x,float y,float w,float h){rt.anchorMin=rt.anchorMax=rt.pivot=new Vector2(0,1);rt.anchoredPosition=new Vector2(x,-y);rt.sizeDelta=new Vector2(w,h);}
    }
}

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
    [DisallowMultipleComponent] public sealed class RainCupPage:MonoBehaviour {
        HomePage home;PreLevelAssets assets;PlayerProfileHost profile;Canvas canvas;CanvasScaler scaler;RectTransform safe,content,panel,viewport;ScrollRect scroll;CanvasGroup fade,panelFade;RainCupDesignAssets design;RawImage backdrop;RenderTexture blurred;Sprite backdropSource;Coroutine opening,motion;Image[] stars;
        ServerRewardsSession serverRewards;bool serverBusy,serverError,serverReceived;int presentationEpoch;bool ServerMode=>profile&&profile.ServerSession&&!profile.LocalEconomyMode;
        readonly Dictionary<string,RectTransform> nodes=new Dictionary<string,RectTransform>();RainCupView view;bool busy;string joinCommand;long lastSecond=-1;int lastRivalHash;int revision;Vector2Int dimensions;Rect lastSafe;float scale;
        public bool IsVisible=>canvas&&canvas.gameObject.activeSelf;
        public void Configure(HomePage home,PreLevelAssets assets,PlayerProfileHost profile){this.home=home;this.assets=assets;this.profile=profile;home.NavigationRequested.AddListener(Route);}
        void Route(string route){if(route=="cup"||route=="drawer-cup")Show();else if(route=="home"||route=="journey"||route=="leaderboard"||route=="teams"||route=="team"||route=="shop"||route=="settings"||route=="coins"||route=="daily"||route=="drawer-daily"||route=="wellworks"||route=="drawer-wellworks")Hide(false);}
        // First use from Home loads the art off the tap frame, so Home stays responsive.
        // A switch from another open page keeps its immediate hand-over.
        bool designLoading;
        System.Collections.IEnumerator LoadDesignThenShow(){designLoading=true;yield return RainCupDesignAssets.LoadAsync();designLoading=false;design=RainCupDesignAssets.Load();Show();}
        public void Show(){var flow=home.GetComponent<HomeLevelFlow>();if(!flow||!flow.CanOpenAppSettings||designLoading)return;if(!design&&home.PresentationInteractable){StartCoroutine(LoadDesignThenShow());return;}presentationEpoch++;LoadView();
            var gift=home.GetComponent<DailyGiftPage>();if(gift)gift.Hide(false);
            var works=home.GetComponent<WellworksPage>();if(works)works.Hide(false);
            var journey=home.GetComponent<HeartOfTheRain.App.Journey.JourneyPage>();if(journey)journey.Hide(false);
            var ranks=home.GetComponent<HeartOfTheRain.App.Leaderboard.LeaderboardPage>();if(ranks)ranks.Hide(false);
            var teams=home.GetComponent<HeartOfTheRain.App.Teams.TeamsPage>();if(teams)teams.Hide(false);
            var shop=home.GetComponent<HeartOfTheRain.App.Shop.ShopPage>();if(shop)shop.Hide(false);
            var settings=home.GetComponent<HeartOfTheRain.App.AppSettings.AppSettingsPage>();if(settings)settings.Hide(false);
            home.ShowEvents(false);Open();if(ServerMode&&!serverBusy)BeginServer("refresh");}
        void LoadView(){
            if(ServerMode){bool show=view!=null&&view.showPrizes;serverRewards=ServerRewardsSession.Select(profile.ServerSession);var state=serverRewards.Coordinator;var data=state.PlayerId==profile.ServerSession.PlayerId?state.Cup:null;var snapshot=data==null?new RainCupSnapshot{state=serverError?"Unavailable":"Loading"}:ServerRewardProjection.Cup(data);if(serverBusy)snapshot.canJoin=false;var appearance=home.GetComponent<ProfilePage>();view=new RainCupView{showPrizes=show,snapshot=snapshot,remaining=snapshot.run==null?0:Math.Max(0,snapshot.run.endsAt-Math.Max(snapshot.observedNow,profile.ServerSession.ServerTimeNow)),error=serverError&&data==null,actionError=serverError&&data!=null,received=serverReceived,playerName=appearance?appearance.Snapshot.displayName:"",avatarId=appearance?appearance.Snapshot.avatarId:"Dariya"};if(snapshot.run==null||snapshot.state=="Finished"||snapshot.state=="Claimed")view.showPrizes=true;return;}
            bool prizes=view!=null&&view.showPrizes;view=new RainCupView{showPrizes=prizes};
            try{if(!profile.Ready&&!profile.Refresh())throw new InvalidOperationException("Save unavailable");view.snapshot=profile.Cup.View();view.remaining=profile.Cup.Remaining(view.snapshot);var appearance=home.GetComponent<ProfilePage>();view.playerName=appearance?appearance.Snapshot.displayName:"";view.avatarId=appearance?appearance.Snapshot.avatarId:"Dariya";if(view.snapshot.run==null||view.snapshot.state=="Finished"||view.snapshot.state=="Claimed")view.showPrizes=true;}catch(Exception){view.error=true;}
        }
        void Open(){Build();canvas.gameObject.SetActive(true);home.SetPresentation(!view.error||home.PresentationVisible,false);Render();Focus(view.error?"primary":"close");if(!home.State.reduceMotion)opening=StartCoroutine(OpenMotion());}
        void Build(){if(canvas)return;var root=Rect("RainCup Canvas",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=310;
#if UNITY_2022_3_OR_NEWER
            canvas.vertexColorAlwaysGammaSpace=true;
#endif
            scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;root.gameObject.AddComponent<GraphicRaycaster>();fade=root.gameObject.AddComponent<CanvasGroup>();
            design=RainCupDesignAssets.Load();if(!design)throw new InvalidOperationException("Missing RainCup design bindings");
            var bg=Rect("Chapter backdrop",root);Stretch(bg);backdrop=bg.gameObject.AddComponent<RawImage>();backdrop.raycastTarget=false;
            var dim=Rect("Modal shade",root);Stretch(dim);dim.gameObject.AddComponent<Image>().color=new Color(7/255f,18/255f,40/255f,.439f);
            safe=Rect("Safe area",root);content=Rect("RainCup content",safe);
        }
        public void Hide(bool restore=true){if(!IsVisible||busy)return;presentationEpoch++;CancelMotion();canvas.gameObject.SetActive(false);if(design)design.ReleaseArt();if(restore)home.SetPresentation(true,true);}
        public void Request(string action){
            if(!IsVisible||busy||string.IsNullOrEmpty(action)||action=="disabled")return;
            if(action=="close"){Hide();return;}
            if(action=="retry"&&ServerMode){if(!serverBusy)BeginServer("refresh");return;}
            if(action=="retry"){profile.Refresh();LoadView();Render();Focus(view.error?"primary":"close");return;}
            if(action=="standings"||action=="rewards"){view.showPrizes=action=="rewards";Render(false);Focus(action);return;}
            if(action=="play"){LoadView();if(!view.error&&RainCupDesignLayout.Action(view)=="play"){Hide();home.GetComponent<HomeLevelFlow>().Open(home.State.currentLevel);}else Render();return;}
            if(action!="join"&&action!="claim")return;if(ServerMode){if(!serverBusy)BeginServer(action);return;}busy=true;
            try{
                RewardGrant grant=null;
                if(action=="join"){if(joinCommand==null)joinCommand=Guid.NewGuid().ToString("N");profile.Cup.Join(joinCommand);joinCommand=null;}
                else if(view.snapshot?.run!=null)grant=profile.Cup.Claim(view.snapshot.run.id);
                profile.Refresh();LoadView();if(action=="join")view.showPrizes=false;view.received=grant!=null;Render();
                if(grant!=null){home.PlayRewardReveal(grant.coins,grant.stars,home.State.completedLevelsInChapter);PlayCollection();}
            }catch(Exception){
                // A commit can succeed while its acknowledgement is lost. Reconcile the receipt/state,
                // never infer inventory from an animation or resend a new enrollment command.
                profile.Refresh();LoadView();bool saved=!view.error&&(action=="claim"?view.snapshot?.state=="Claimed":view.snapshot?.run?.id==joinCommand);
                view.actionError=!view.error&&!saved;view.received=saved&&action=="claim";
                if(saved&&action=="join"){joinCommand=null;view.showPrizes=false;}Render();
            }finally{busy=false;Focus("close");}
        }
        void BeginServer(string action){serverBusy=true;serverError=false;serverReceived=false;LoadView();if(IsVisible){Render();Focus("close");}StartCoroutine(ServerRemote(action,presentationEpoch));}
        IEnumerator ServerRemote(string action,int epoch){
            var session=profile.ServerSession;var coordinator=ServerRewardsSession.Select(session).Coordinator;RewardCompletion completion=null;
            try{yield return action=="join"?coordinator.JoinCup(value=>completion=value):action=="claim"?coordinator.ClaimCup(view.snapshot?.run?.id,value=>completion=value):coordinator.Refresh("Cup",value=>completion=value);}finally{serverBusy=false;}
            if(!this||profile.ServerSession!=session)yield break;serverError=completion==null||!completion.ok;serverReceived=!serverError&&completion.kind=="CupClaim"&&completion.grant!=null;
            if(IsVisible){LoadView();if(completion?.ok==true&&completion.kind=="CupJoin")view.showPrizes=false;Render();Focus("close");if(serverReceived&&epoch==presentationEpoch)PlayCollection();}
        }
        float DesiredScale(Rect area)=>Mathf.Max(.25f,Mathf.Min(home.CurrentUIScale,Mathf.Min((area.width>0?area.width:Screen.width)/320,(area.height>0?area.height:Screen.height)/300)));
        void Update(){if(!IsVisible)return;if(dimensions.x!=Screen.width||dimensions.y!=Screen.height||lastSafe!=Screen.safeArea||revision!=GameLocale.Revision||Mathf.Abs(scale-DesiredScale(Screen.safeArea))>.01f)Render();
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
            bool back=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
            bool back=Input.GetKeyDown(KeyCode.Escape);
#endif
            if(back)Request("close");
            TickTimer();
        }
        void TickTimer(){
            if(view.error||view.snapshot?.run==null||view.snapshot.state!="Active")return;
            try{long remaining=ServerMode?Math.Max(0,view.snapshot.run.endsAt-Math.Max(view.snapshot.observedNow,profile.ServerSession.ServerTimeNow)):profile.Cup.Remaining(view.snapshot);if(remaining==lastSecond)return;lastSecond=remaining;view.remaining=remaining;
                if(remaining==0){if(ServerMode){if(!serverBusy)BeginServer("refresh");}else{profile.Refresh();LoadView();Render();}return;}
                RectTransform node;if(nodes.TryGetValue("timer",out node))node.GetComponent<Text>().text=RainCupText.Timer(remaining);
                view.snapshot.observedNow=view.snapshot.run.endsAt-remaining;int hash=17;foreach(int n in RainCupModel.RivalScores(view.snapshot.run,view.snapshot.observedNow))hash=hash*31+n;if(hash!=lastRivalHash){lastRivalHash=hash;if(!view.showPrizes)Render();}
            }catch(Exception){view.error=true;Render();}
        }
        void Render(bool preserveScroll=true){
            float scrollPosition=preserveScroll&&scroll?scroll.verticalNormalizedPosition:1;
            CancelMotion();foreach(Transform t in content){t.gameObject.SetActive(false);Destroy(t.gameObject);}nodes.Clear();var sr=Screen.safeArea;if(sr.width<=0||sr.height<=0)sr=new Rect(0,0,Screen.width,Screen.height);
            scale=DesiredScale(sr);scaler.scaleFactor=canvas.scaleFactor=scale;scaler.referencePixelsPerUnit=100;Place(safe,sr.x/scale,(Screen.height-sr.yMax)/scale,sr.width/scale,sr.height/scale);
            if(view.snapshot?.run!=null){lastRivalHash=17;foreach(int n in RainCupModel.RivalScores(view.snapshot.run,view.snapshot.observedNow))lastRivalHash=lastRivalHash*31+n;}lastSecond=view.remaining;
            var frame=RainCupLayout.Build(sr.width/scale,sr.height/scale,view);Place(content,0,0,frame.width,frame.height);
            foreach(var e in frame.elements){var parent=string.IsNullOrEmpty(e.parent)?content:nodes[e.parent];var rt=Rect(e.id,parent);Place(rt,e.x,e.y,e.width,e.height);nodes[e.id]=rt;if(e.id=="trophy"||e.id.StartsWith("reward-item-",StringComparison.Ordinal)){rt.pivot=Vector2.one*.5f;rt.anchoredPosition+=new Vector2(e.width*.5f,-e.height*.5f);}
                if(e.kind=="group"){
                    if(e.id=="panel"){panel=rt;panelFade=rt.gameObject.AddComponent<CanvasGroup>();}
                    if(e.id=="viewport"){viewport=rt;rt.gameObject.AddComponent<Image>().color=Color.clear;rt.gameObject.AddComponent<RectMask2D>();scroll=rt.gameObject.AddComponent<ScrollRect>();scroll.viewport=rt;scroll.horizontal=false;scroll.movementType=ScrollRect.MovementType.Clamped;scroll.scrollSensitivity=32;}
                    if(e.id=="body")scroll.content=rt;
                    if(e.id=="progress-clip"){rt.gameObject.AddComponent<RectMask2D>();rt.gameObject.SetActive(e.width>0);}

                    if(string.IsNullOrEmpty(e.action))continue;var hit=rt.gameObject.AddComponent<Image>();hit.color=Color.clear;var b=rt.gameObject.AddComponent<Button>();b.targetGraphic=hit;b.transition=Selectable.Transition.None;b.interactable=e.action!="disabled";string action=e.action;b.onClick.AddListener(()=>Request(action));var label=rt.gameObject.AddComponent<HomeControlLabel>();label.action=action;label.label=RainCupDesignText.T(action=="close"?"close":action=="join"?"join":action=="play"?"play":action=="standings"?"standings":action=="rewards"?"rewards":"claim");
                }else if(e.kind=="text"){
                    var t=rt.gameObject.AddComponent<Text>();bool bold=e.id=="title"||e.id.Contains("label")||e.id.Contains("title")||e.id.Contains("quantity")||e.id.StartsWith("rank-")||e.id.StartsWith("name-")||e.id.StartsWith("points-")||e.id=="score-count"||e.id=="heading"||e.id=="progress-count";t.font=bold?design.shared.shared.titleFont:design.shared.shared.bodyFont;t.text=e.text;t.fontSize=e.fontSize;ColorUtility.TryParseHtmlString(e.color,out var color);t.color=color;t.alignment=TextAnchor.MiddleCenter;t.raycastTarget=false;t.supportRichText=false;t.verticalOverflow=VerticalWrapMode.Truncate;
                    // Single-line labels and the one-line list note shrink to width (the note's 23-unit slot cannot hold a wrapped second line at 320 wide).
                    if(e.id=="primary-label"||e.id=="standings-label"||e.id=="rewards-label"||e.id=="list-heading"){t.horizontalOverflow=HorizontalWrapMode.Overflow;while(t.fontSize>(e.id=="primary-label"?14:e.id=="list-heading"?8:12)&&t.preferredWidth>e.width+.01f)t.fontSize--;}
                    else{t.horizontalOverflow=HorizontalWrapMode.Wrap;while(t.fontSize>9&&t.preferredHeight>e.height+.01f)t.fontSize--;}
                    if(e.id.StartsWith("name-",StringComparison.Ordinal)){t.horizontalOverflow=HorizontalWrapMode.Overflow;t.fontSize=e.fontSize;string full=t.text;var elements=System.Globalization.StringInfo.ParseCombiningCharacters(full);int count=elements.Length;while(count>1&&t.preferredWidth>e.width){count--;t.text=full.Substring(0,elements[count])+"\u2026";}var l=rt.gameObject.AddComponent<HomeControlLabel>();l.action="player-name";l.label=full;}
                    if(e.id=="title"){var shadow=t.gameObject.AddComponent<Shadow>();shadow.effectColor=new Color(0,.05f,.15f,.9f);shadow.effectDistance=new Vector2(0,-2);}
                }else if(e.kind=="avatar"){BuildAvatar(rt);
                }else{var im=rt.gameObject.AddComponent<Image>();im.sprite=design.Find(e.asset)??assets.Find(e.asset);if(!im.sprite)throw new InvalidOperationException("Missing RainCup sprite: "+e.asset);im.raycastTarget=false;im.type=e.sliced?Image.Type.Sliced:Image.Type.Simple;im.preserveAspect=e.preserveAspect;im.pixelsPerUnitMultiplier=e.sliced?RainCupDesignAssets.Multiplier(e.asset):1;im.color=Color.white;}
            }
            scroll.vertical=scroll.content.rect.height>viewport.rect.height+.1f;scroll.verticalNormalizedPosition=scrollPosition;
            foreach(var id in new[]{"standings","rewards"})if(nodes.TryGetValue(id,out var tab))tab.gameObject.AddComponent<RainCupTabState>().selected=view.showPrizes==(id=="rewards");
            if(nodes.TryGetValue("primary",out var primary)&&RainCupDesignLayout.Action(view)=="disabled")foreach(var g in primary.GetComponentsInChildren<Graphic>())g.color=new Color(g.color.r,g.color.g,g.color.b,g.color.a*.5f);
            foreach(var e in frame.elements)if(e.kind=="group"&&!string.IsNullOrEmpty(e.action)){var rt=nodes[e.id];if(nodes.TryGetValue(e.id+"-label",out var labelNode)&&labelNode.GetComponent<Text>())rt.GetComponent<HomeControlLabel>().label=labelNode.GetComponent<Text>().text;var graphics=new List<Graphic>();foreach(var g in rt.GetComponentsInChildren<Graphic>())if(g.transform!=rt)graphics.Add(g);rt.gameObject.AddComponent<PreLevelButtonFeedback>().Configure(graphics.ToArray(),home.State.reduceMotion);}
            var source=home.ProfileBackground;if(source&&(!blurred||source!=backdropSource)){ProfileBackdrop.Release(blurred);blurred=ProfileBackdrop.Blur(source.texture);backdropSource=source;backdrop.texture=blurred?(Texture)blurred:source.texture;}
            if(backdrop.texture){float a=Screen.width/(float)Screen.height,b=backdrop.texture.width/(float)backdrop.texture.height;backdrop.uvRect=a>b?new Rect(0,(1-b/a)/2,1,b/a):new Rect((1-a/b)/2,0,a/b,1);}
            dimensions=new Vector2Int(Screen.width,Screen.height);lastSafe=Screen.safeArea;revision=GameLocale.Revision;
        }
        void BuildAvatar(RectTransform rt){
            var mask=rt.gameObject.AddComponent<Image>();mask.sprite=design.mask;mask.raycastTarget=false;rt.gameObject.AddComponent<Mask>().showMaskGraphic=false;
            var bounds=Rect("Portrait bounds",rt);Place(bounds,rt.rect.width*.09375f,rt.rect.height*.0859375f,rt.rect.width*.8125f,rt.rect.height*.8125f);
            var pic=Rect("Current player portrait",bounds);Stretch(pic);var im=pic.gameObject.AddComponent<Image>();im.sprite=design.profile.Find("Avatar_"+(view.avatarId??"Dariya"));im.raycastTarget=false;var fit=pic.gameObject.AddComponent<AspectRatioFitter>();fit.aspectMode=AspectRatioFitter.AspectMode.EnvelopeParent;fit.aspectRatio=im.sprite.rect.width/im.sprite.rect.height;
        }
        void CancelMotion(){if(opening!=null)StopCoroutine(opening);if(motion!=null)StopCoroutine(motion);opening=motion=null;if(panelFade)panelFade.alpha=1;if(panel){panel.localScale=Vector3.one;panel.localRotation=Quaternion.identity;}if(stars!=null)foreach(var star in stars)if(star)star.gameObject.SetActive(false);foreach(var pair in nodes)if(pair.Key.StartsWith("reward-item-",StringComparison.Ordinal)&&pair.Value)pair.Value.localScale=Vector3.one;if(nodes.TryGetValue("trophy",out var trophy)&&trophy){trophy.localScale=Vector3.one;trophy.localRotation=Quaternion.identity;}}
        IEnumerator OpenMotion(){var start=panel.anchoredPosition;for(float t=0;t<.25f;t+=Time.unscaledDeltaTime){float u=1-Mathf.Pow(1-t/.25f,3);panelFade.alpha=u;panel.localScale=Vector3.one*Mathf.Lerp(.98f,1,u);panel.anchoredPosition=start+Vector2.down*10*(1-u);yield return null;}panelFade.alpha=1;panel.localScale=Vector3.one;panel.anchoredPosition=start;opening=null;}
        void PlayCollection(){if(home.State.reduceMotion||!IsVisible)return;scroll.verticalNormalizedPosition=1;Canvas.ForceUpdateCanvases();if(stars==null){stars=new Image[14];var root=(RectTransform)canvas.transform;for(int i=0;i<stars.Length;i++){var rt=Rect("Cup glint "+i,root);rt.pivot=Vector2.one*.5f;rt.sizeDelta=Vector2.one*20;var im=rt.gameObject.AddComponent<Image>();im.sprite=design.shared.shared.star;im.raycastTarget=false;stars[i]=im;}}motion=StartCoroutine(Collection());}
        IEnumerator Collection(){
            var trophy=nodes["trophy"];var hero=nodes["hero"];var root=(RectTransform)canvas.transform;Vector2 origin=root.InverseTransformPoint(hero.TransformPoint(new Vector3(hero.rect.width*.42f,-hero.rect.height*.48f,0)));for(int i=0;i<stars.Length;i++){stars[i].rectTransform.anchorMin=stars[i].rectTransform.anchorMax=root.pivot;stars[i].gameObject.SetActive(true);}
            for(float t=0;t<.9f;t+=Time.unscaledDeltaTime){if(!IsVisible||home.State.reduceMotion)break;float k=Mathf.Clamp01(t/.65f),sc=k<.35f?Mathf.Lerp(1,1.08f,k/.35f):k<.7f?Mathf.Lerp(1.08f,1.01f,(k-.35f)/.35f):Mathf.Lerp(1.01f,1,(k-.7f)/.3f);float z=k<.35f?Mathf.Lerp(0,-3,k/.35f):k<.7f?Mathf.Lerp(-3,2,(k-.35f)/.35f):Mathf.Lerp(2,0,(k-.7f)/.3f);trophy.localScale=Vector3.one*sc;trophy.localRotation=Quaternion.Euler(0,0,z);
                if(view.snapshot?.run!=null){float p=Mathf.Clamp01(t/.6f),pop=p<.4f?Mathf.Lerp(.9f,1.13f,p/.4f):Mathf.Lerp(1.13f,1,(p-.4f)/.6f);foreach(var pair in nodes)if(pair.Key.StartsWith("reward-item-"+(view.snapshot.run.finalRank-1)+"-",StringComparison.Ordinal))pair.Value.localScale=Vector3.one*pop;}
                for(int i=0;i<stars.Length;i++){float p=Mathf.Clamp01((t-i%3*.02f)/.85f),a=i/(float)stars.Length*Mathf.PI*2;var rt=stars[i].rectTransform;rt.anchoredPosition=origin+new Vector2(Mathf.Cos(a)*(56+i%3*12),-Mathf.Sin(a)*49+19)*p;rt.localRotation=Quaternion.Euler(0,0,i*37*p);rt.localScale=Vector3.one*(p<.15f?Mathf.Lerp(.2f,1,p/.15f):Mathf.Lerp(1,.4f,(p-.15f)/.85f));stars[i].color=new Color(1,1,1,p<.15f?p/.15f:1-(p-.15f)/.85f);}yield return null;
            }
            trophy.localScale=Vector3.one;trophy.localRotation=Quaternion.identity;foreach(var star in stars)star.gameObject.SetActive(false);foreach(var pair in nodes)if(pair.Key.StartsWith("reward-item-",StringComparison.Ordinal)&&pair.Value)pair.Value.localScale=Vector3.one;motion=null;
        }
        public static void FitText(Text text,float width,float height,bool paragraph){text.horizontalOverflow=paragraph?HorizontalWrapMode.Wrap:HorizontalWrapMode.Overflow;if(paragraph){while(text.fontSize>9&&text.preferredHeight>height+.01f)text.fontSize--;}else LabelFit.Apply(text,width,height,9);}
        void Focus(string id){RectTransform rt;if(EventSystem.current&&nodes.TryGetValue(id,out rt))EventSystem.current.SetSelectedGameObject(rt.gameObject);}
        void OnDestroy(){ProfileBackdrop.Release(blurred);if(home)home.NavigationRequested.RemoveListener(Route);}
        static RectTransform Rect(string name,Transform parent){var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);return (RectTransform)go.transform;}
        static void Stretch(RectTransform rt){rt.anchorMin=Vector2.zero;rt.anchorMax=Vector2.one;rt.offsetMin=rt.offsetMax=Vector2.zero;}
        static void Place(RectTransform rt,float x,float y,float w,float h){rt.anchorMin=rt.anchorMax=rt.pivot=new Vector2(0,1);rt.anchoredPosition=new Vector2(x,-y);rt.sizeDelta=new Vector2(w,h);}
    }
}

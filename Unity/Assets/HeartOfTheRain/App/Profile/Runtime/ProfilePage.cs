using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Localization;

namespace HeartOfTheRain.App.Profile
{
    [DisallowMultipleComponent] public sealed partial class ProfilePage:MonoBehaviour
    {
        HomePage home;ProfileAssets assets;ProfileStore store;Canvas canvas;CanvasScaler scaler;
        RectTransform safe,panel,collection,viewport,content,renameLayer,renameViewport,renameContent,renamePanel;
        RectTransform outerContent;ScrollRect outerScroll;RawImage backdrop;RenderTexture backdropTexture;Sprite backdropSource;Sprite circleMask,bannerClip;
        CanvasGroup mainGroup;ScrollRect scroll,renameScroll;InputField nameInput;
        Text title,nameLabel,teamLabel,levelTitle,levelValue,sectionTitle,status,renameTitle,renameHint,errorLabel;
        RawImage banner;Image statusCheck;RectTransform portrait;Button close,edit,join,renameClose,save,cancel;
        readonly Button[] tabs=new Button[4];readonly Dictionary<string,RectTransform> nodes=new Dictionary<string,RectTransform>();
        readonly float[] scrollPositions={1,1,1,1};int tab,locale=-1;bool renameOpen;string error="",selectionError="",teamName="",teamRole="";
        Vector2Int size;Rect safeRect;float lastScale,lastKeyboard=-1;GameObject previousFocus;
        string collectionKey,statsKey;bool prepared;
        public bool IsPrepared=>prepared;
        public bool IsVisible=>canvas&&canvas.gameObject.activeSelf;
        public bool IsRenaming=>renameOpen;
        public ProfileData Snapshot=>ViewSnapshot();
        public event Action<ProfileData> ProfileChanged;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        [NonSerialized] public ProfileStore VerificationStore;
#endif

        public static ProfilePage Attach(HomePage home)
        {
            var p=home.GetComponent<ProfilePage>();if(!p)p=home.gameObject.AddComponent<ProfilePage>();
            p.Initialize(home);return p;
        }
        public void Initialize(HomePage owner)
        {
            if(home)return;assets=Resources.Load<ProfileAssets>("HeartOfTheRainProfile/Config");
            if(!assets||!assets.home){Debug.LogWarning("Profile assets are missing. Import the complete M71 module.",owner);return;}
            home=owner;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            store=VerificationStore;
            var first=owner.GetComponent<HeartOfTheRain.App.FirstStart.FirstStartPage>();
            if(store==null&&first&&first.reviewAlways)store=new ProfileStore(new MemoryAppearancePreferences());
#endif
            if(store==null)store=new ProfileStore();store.Changed+=Changed;home.NavigationRequested.AddListener(Route);ApplyHomeAvatar();StartCoroutine(PreparePresentation());
        }
        IEnumerator PreparePresentation()
        {
            // Prepare while Home/onboarding is loading. Never yield with the modal visible.
            yield return null;if(IsVisible)yield break;Build();canvas.gameObject.SetActive(false);
            yield return null;if(IsVisible)yield break;RefreshBackdrop();
            yield return null;if(IsVisible)yield break;canvas.gameObject.SetActive(true);Layout();canvas.gameObject.SetActive(false);prepared=true;
        }
        void Route(string action){if(action=="profile")Show();else if(IsVisible)Hide(false);}
        public void SetTeam(string name,string role){teamName=name??"";teamRole=role??"";if(IsVisible)RefreshText();}
        public void Show()
        {
            if(!home||store==null||IsVisible||!home.PresentationInteractable)return;var flow=home.GetComponent<HomeLevelFlow>();if(flow&&!flow.CanOpenAppSettings)return;
            previousFocus=EventSystem.current?EventSystem.current.currentSelectedGameObject:null;
            home.ShowEvents(false);Build();RefreshBackdrop();canvas.gameObject.SetActive(true);home.SetPresentation(true,false);
            renameOpen=false;selectionError="";renameLayer.gameObject.SetActive(false);mainGroup.interactable=mainGroup.blocksRaycasts=true;
            Layout();Canvas.ForceUpdateCanvases();outerScroll.verticalNormalizedPosition=1;Focus(close.gameObject);if(ServerSelected)OpenServerProfile();
        }
        public void Hide(bool restoreHome=true)
        {
            if(!IsVisible)return;CancelRename();canvas.gameObject.SetActive(false);
            if(restoreHome){home.SetPresentation(true,true);if(previousFocus&&previousFocus.activeInHierarchy)Focus(previousFocus);else FocusHome();}
        }
        void FocusHome(){foreach(var c in home.GetComponentsInChildren<HomeControlLabel>())if(c.action=="profile"){Focus(c.gameObject);break;}}
        void Changed(ProfileData data){selectionError="";ApplyHomeAvatar();ProfileChanged?.Invoke(Snapshot);if(IsVisible){scrollPositions[tab]=scroll.enabled?scroll.verticalNormalizedPosition:1;RefreshText();RenderCollection();}}
        void ApplyHomeAvatar(){var d=store.Snapshot;home.SetProfileAvatar(assets.Find("Avatar_"+d.avatarId),assets.Find("Frame"+d.frameId),assets.Find("RoundMask"));}
        void Choose(int t,string id){string message;if(!store.Select(t,id,out message)){selectionError=message;RefreshText();return;}FocusTile(id);}
        void SelectTab(int value){selectionError="";scrollPositions[tab]=scroll.enabled?scroll.verticalNormalizedPosition:1;tab=value;RefreshText();RenderCollection();Focus(tabs[tab].gameObject);}
        void BeginRename()
        {
            renameOpen=true;error="";nameInput.text=Snapshot.displayName;
            renameLayer.gameObject.SetActive(true);mainGroup.interactable=mainGroup.blocksRaycasts=false;RefreshText();LayoutRename();
            Focus(nameInput.gameObject);nameInput.ActivateInputField();if(ServerSelected)OnlineProfileChanged();
        }
        void CancelRename()
        {
            if(!renameOpen)return;renameOpen=false;nameInput.DeactivateInputField();renameLayer.gameObject.SetActive(false);
            mainGroup.interactable=mainGroup.blocksRaycasts=true;error="";Focus(edit.gameObject);
        }
        void SaveName(){if(ServerSelected){SaveServerName();return;}if(store.Rename(nameInput.text,out error))CancelRename();else{errorLabel.text=ProfileText.T(error);Focus(nameInput.gameObject);nameInput.ActivateInputField();}}
        void Build()
        {
            if(canvas)return;
            var root=R("Profile Canvas",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=180;
#if UNITY_2022_3_OR_NEWER
            canvas.vertexColorAlwaysGammaSpace=true;
#endif
            scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;root.gameObject.AddComponent<GraphicRaycaster>();
            var bg=R("Profile backdrop",root);backdrop=bg.gameObject.AddComponent<RawImage>();Stretch(bg);backdrop.raycastTarget=false;
            var dim=Plain(root,"Dimmer",new Color(.028f,.07f,.16f,.22f));Stretch(dim.rectTransform);dim.raycastTarget=true;
            safe=R("Profile Safe Area",root);safe.gameObject.AddComponent<Image>().color=Color.clear;safe.gameObject.AddComponent<RectMask2D>();outerScroll=safe.gameObject.AddComponent<ScrollRect>();outerScroll.viewport=safe;outerScroll.horizontal=false;outerScroll.movementType=ScrollRect.MovementType.Clamped;outerScroll.scrollSensitivity=80;
            outerContent=R("Scrollable authored layout",safe);outerScroll.content=outerContent;panel=R("Profile Panel",outerContent);mainGroup=panel.gameObject.AddComponent<CanvasGroup>();
            ImageNode(panel,"Profile chrome","ProfileChrome");title=Label(panel,"Title",72,true,new Color32(255,246,223,255));Depth(title,2.5f,5);
            close=Icon(panel,"Close","CloseSource",()=>Hide());
            var bannerMask=R("Banner",panel);var bm=bannerMask.gameObject.AddComponent<Image>();bm.sprite=BannerMask();bm.raycastTarget=false;bannerMask.gameObject.AddComponent<Mask>().showMaskGraphic=false;
            var br=R("Banner image",bannerMask);Stretch(br);banner=br.gameObject.AddComponent<RawImage>();banner.raycastTarget=false;
            portrait=MakePortrait(panel,"Portrait",Snapshot.avatarId,Snapshot.frameId);
            nameLabel=Label(panel,"Player name",44,true,Color.white,TextAnchor.MiddleLeft);Depth(nameLabel,1,3);edit=Icon(panel,"Edit name","PencilSource",BeginRename);
            ImageNode(panel,"Team emblem","Team");teamLabel=Label(panel,"Team name",35,true,Ink,TextAnchor.MiddleLeft);
            join=ActionButton(panel,"Join","Join",()=>{Hide();home.Request("teams");},"Primary",34);
            levelTitle=Label(panel,"Level title",29,true,new Color32(69,102,141,255));levelValue=Label(panel,"Level value",62,true,Ink);
            for(int i=0;i<4;i++){int n=i;tabs[i]=ActionButton(panel,"Tab "+i,new[]{"Avatars","Banners","Frames","Stats"}[i],()=>SelectTab(n),"TabInactive",34);}
            collection=R("Collection",panel);sectionTitle=Label(collection,"Section title",43,true,Ink);
            viewport=R("Collection viewport",collection);var hit=Plain(viewport,"Scroll hit",Color.clear);Stretch(hit.rectTransform);hit.raycastTarget=true;viewport.gameObject.AddComponent<RectMask2D>();
            scroll=viewport.gameObject.AddComponent<ScrollRect>();scroll.viewport=viewport;scroll.horizontal=false;scroll.movementType=ScrollRect.MovementType.Clamped;scroll.scrollSensitivity=75;
            content=R("Items",viewport);scroll.content=content;status=Label(collection,"Selection status",28,true,Ink);statusCheck=CircleImage(collection,"Status check","CheckSource");
            BuildRename(root);
        }
        void BuildRename(RectTransform root)
        {
            renameLayer=R("Rename layer",root);Stretch(renameLayer);var dim=Plain(renameLayer,"Rename dimmer",new Color(0,0,0,.60f));Stretch(dim.rectTransform);dim.raycastTarget=true;
            renameViewport=R("Rename viewport",renameLayer);renameViewport.gameObject.AddComponent<Image>().color=Color.clear;renameViewport.gameObject.AddComponent<RectMask2D>();renameScroll=renameViewport.gameObject.AddComponent<ScrollRect>();renameScroll.viewport=renameViewport;renameScroll.horizontal=false;renameScroll.movementType=ScrollRect.MovementType.Clamped;
            renameContent=R("Rename scroll content",renameViewport);renameScroll.content=renameContent;renamePanel=R("Rename panel",renameContent);
            ImageNode(renamePanel,"Rename chrome","RenameChrome");renameTitle=Label(renamePanel,"Rename title",62,true,new Color32(255,246,223,255));Depth(renameTitle,2,4);renameClose=Icon(renamePanel,"Rename close","CloseSource",CancelRename);
            renameHint=Label(renamePanel,"Rename hint",33,true,Ink);var field=Skin(renamePanel,"Name input","Input");field.raycastTarget=true;
            nameInput=field.gameObject.AddComponent<InputField>();nameInput.targetGraphic=field;nameInput.lineType=InputField.LineType.SingleLine;nameInput.contentType=InputField.ContentType.Standard;
            var text=Label(field.transform,"Editable name",45,true,Ink,TextAnchor.MiddleLeft);Stretch(text.rectTransform);text.rectTransform.offsetMin=new Vector2(30,15);text.rectTransform.offsetMax=new Vector2(-30,-15);text.resizeTextForBestFit=false;text.horizontalOverflow=HorizontalWrapMode.Overflow;
            nameInput.textComponent=text;nameInput.onValueChanged.AddListener(_=>{error="";errorLabel.text="";UpdateFonts(nameInput.transform);});
            errorLabel=Label(renamePanel,"Name error",22,false,new Color(.65f,.11f,.10f));
            save=ActionButton(renamePanel,"Save","Save",SaveName,"Primary",57);cancel=ActionButton(renamePanel,"Cancel","Cancel",CancelRename,"",41);
            renameLayer.gameObject.SetActive(false);
        }
        void Update()
        {
            if(!IsVisible)return;float keyboard=TouchScreenKeyboard.visible?TouchScreenKeyboard.area.yMax:0;
            if(size.x!=Screen.width||size.y!=Screen.height||safeRect!=Screen.safeArea||Mathf.Abs(lastScale-home.CurrentUIScale)>.01f||locale!=GameLocale.Revision)Layout();
            if(statsKey!=StatsKey()){RefreshText();RenderCollection();}
            if(renameOpen&&Mathf.Abs(lastKeyboard-keyboard)>.5f)LayoutRename();
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
            bool back=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
            bool back=Input.GetKeyDown(KeyCode.Escape);
#endif
            if(back){if(renameOpen)CancelRename();else Hide();}
        }
        void Layout()
        {
            float pagePosition=outerScroll.verticalNormalizedPosition;
            if(content&&content.childCount>0)scrollPositions[tab]=scroll.enabled?scroll.verticalNormalizedPosition:1;
            Rect sr=Screen.safeArea;if(sr.width<=0||sr.height<=0)sr=new Rect(0,0,Screen.width,Screen.height);
            // Fixed authored coordinates keep art and controls aligned. Short displays scroll the full page.
            float q=Mathf.Min(sr.width/941f,650f/941f);scaler.scaleFactor=q;canvas.scaleFactor=q;
            float w=sr.width/q,h=sr.height/q;Place(safe,sr.x/q,(Screen.height-sr.yMax)/q,w,h);
            Place(outerContent,0,0,w,Mathf.Max(h,1672));Place(panel,(w-941)/2,Mathf.Max(0,(h-1672)/2),941,1672);outerScroll.vertical=h<1672;
            Box("Profile chrome",0,0,941,1672);Box("Title",195,111,554,89);ButtonBox(close,790,108,106,106);
            Box("Banner",80,226,780,279);Place(portrait,95,246,250,250);Box("Player name",355,418,236,76);ButtonBox(edit,597,423,68,69);
            Box("Team emblem",116,524,95,102);Box("Team name",223,550,160,51);ButtonBox(join,396,542,190,67);
            Box("Level title",620,526,142,38);Box("Level value",620,564,142,67);
            float[] xs={73,314,502,693},ws={241,188,191,179};for(int i=0;i<4;i++)ButtonBox(tabs[i],xs[i],658,ws[i],87);
            Place(collection,70,743,800,785);Place(sectionTitle.rectTransform,25,24,750,65);Place(viewport,28,108,742,tab==3?663:565);
            RefreshText();RenderCollection();LayoutRename();CoverBackdrop();
            Canvas.ForceUpdateCanvases();outerScroll.verticalNormalizedPosition=outerScroll.vertical?pagePosition:1;
            size=new Vector2Int(Screen.width,Screen.height);safeRect=Screen.safeArea;lastScale=home.CurrentUIScale;locale=GameLocale.Revision;
        }
        void RefreshText()
        {
            statsKey=StatsKey();
            if(!canvas)return;var d=Snapshot;title.text=ProfileText.T("Profile");nameLabel.text=d.displayName;
            teamLabel.text=teamName.Length==0?ProfileText.T("No team"):teamName;join.gameObject.SetActive(teamName.Length==0);
            levelTitle.text=ProfileText.T("Level");levelValue.text=StatsAvailable?home.State.currentLevel.ToString():"—";
            SetButton(join,"Join");SetButton(save,"Save");SetButton(cancel,"Cancel");
            string[] names={"Avatars","Banners","Frames","Stats"};for(int i=0;i<4;i++){SetButton(tabs[i],names[i]);tabs[i].transform.GetChild(0).GetComponent<Image>().sprite=assets.Find(tab==i?"TabActive":"TabInactive");tabs[i].GetComponentInChildren<Text>().color=tab==i?new Color32(255,231,121,255):new Color32(185,217,248,255);}
            sectionTitle.text=ProfileText.T(new[]{"Choose your avatar","Choose your banner","Choose your frame","Your journey"}[tab]);
            status.text=tab==3?(ServerSelected?ServerRecordsSummary():""):selectionError.Length>0?ProfileText.T(selectionError):ProfileText.T(tab==0?d.avatarId:tab==1?d.bannerId:d.frameId)+" "+ProfileText.T("Selected").ToLowerInvariant();
            UpdateFonts(panel);UpdatePortrait(portrait,d.avatarId,d.frameId);Cover(banner,assets.Find("Banner_"+d.bannerId));bool hasCheck=tab!=3&&selectionError.Length==0;statusCheck.transform.parent.gameObject.SetActive(hasCheck);float statusWidth=Mathf.Min(620,status.preferredWidth),checkSpace=hasCheck?73:0;float sx=(800-statusWidth-checkSpace)/2;Place((RectTransform)statusCheck.transform.parent,sx,696,58,59);Place(status.rectTransform,sx+checkSpace,696,statusWidth,65);
            renameTitle.text=ProfileText.T("Change name");renameHint.text=ProfileText.T("Name hint");errorLabel.text=error.Length==0?"":ProfileText.T(error);UpdateFonts(panel);UpdateFonts(renamePanel);
            FitName(nameLabel,d.displayName,44);
            if(teamName.Length>0)FitName(teamLabel,teamName,35);
            else{teamLabel.resizeTextForBestFit=true;teamLabel.fontSize=35;teamLabel.resizeTextMinSize=20;teamLabel.resizeTextMaxSize=35;teamLabel.horizontalOverflow=HorizontalWrapMode.Wrap;}
            PaintServerRename();
        }
        static void FitName(Text label,string full,int maximum)
        {
            label.resizeTextForBestFit=false;label.horizontalOverflow=HorizontalWrapMode.Overflow;label.fontSize=maximum;label.text=full;
            int minimum=Mathf.RoundToInt(maximum*.68f);float width=label.rectTransform.rect.width;
            while(label.fontSize>minimum&&label.preferredWidth>width)label.fontSize--;
            var elements=StringInfo.ParseCombiningCharacters(full);int count=elements.Length;
            while(count>0&&label.preferredWidth>width){count--;label.text=full.Substring(0,elements[count])+"…";}
        }
        void RenderCollection()
        {
            var current=Snapshot;string key=tab+"|"+current.avatarId+"|"+current.bannerId+"|"+current.frameId+"|"+GameLocale.Revision+"|"+StatsKey()+"|"+StatsColumns;
            if(collectionKey==key)return;
            Place(viewport,28,108,742,tab==3?663:565);
            for(int i=content.childCount-1;i>=0;i--){var old=content.GetChild(i);old.gameObject.SetActive(false);old.SetParent(null,false);Destroy(old.gameObject);}var d=Snapshot;float width=742,gap=22;
            if(tab==3)
            {
                RenderStats(width,gap);
            }
            else
            {
                var ids=tab==0?ProfileRules.Avatars:tab==1?ProfileRules.Banners:ProfileRules.Frames;int cols=tab==1?1:3;float cell=(width-gap*(cols-1))/cols;
                float visual=tab==1?186:230,rowH=tab==1?248:tab==2?328:293;
                for(int i=0;i<ids.Length;i++)
                {
                    string id=ids[i];int selectedTab=tab;var tile=R("Choice "+id,content);Place(tile,(i%cols)*(cell+gap),(i/cols)*rowH,cell,rowH-25);
                    var hit=tile.gameObject.AddComponent<Image>();hit.color=Color.clear;var btn=tile.gameObject.AddComponent<Button>();btn.targetGraphic=hit;btn.transition=Selectable.Transition.None;btn.onClick.AddListener(()=>Choose(selectedTab,id));
                    var access=tile.gameObject.AddComponent<HomeControlLabel>();access.label=ProfileText.T(id);access.action="profile-select:"+id;
                    if(tab==1){var rect=R("Banner choice "+i,tile,false);Place(rect,0,0,cell,visual);var im=rect.gameObject.AddComponent<RawImage>();im.raycastTarget=false;Cover(im,assets.Find("Banner_"+id));}
                    else{var pic=MakePortrait(tile,"Tile portrait "+i,tab==0?id:d.avatarId,tab==2?id:d.frameId,false);Place(pic,0,0,cell,visual);}
                    var label=Label(tile,"Choice label "+i,33,true,Ink);Place(label.rectTransform,0,visual,cell,tab==2?73:38);label.text=ProfileText.T(id);
                    bool active=tab==0?d.avatarId==id:tab==1?d.bannerId==id:d.frameId==id;
                    if(active){var tick=CircleImage(tile,"Selected "+i,"CheckSource");Place((RectTransform)tick.transform.parent,cell-58,visual-56,58,59);}
                }
                Place(content,0,0,width,Mathf.Ceil(ids.Length/(float)cols)*rowH-25);
            }
            UpdateFonts(content);Canvas.ForceUpdateCanvases();scroll.enabled=content.rect.height>viewport.rect.height+.1f;scroll.verticalNormalizedPosition=scrollPositions[tab];collectionKey=key;
        }
        bool StatsAvailable {get{var host=home.GetComponent<PlayerProfileHost>();return host&&host.Ready&&(!ServerSelected||onlineProfile?.Records!=null);}}
        int StatsColumns=>(Screen.safeArea.width>0?Screen.safeArea.width:Screen.width)<340?1:2;
        string StatsKey()=>StatsAvailable+"|"+home.State.currentLevel+"|"+home.State.chapterNumber+"|"+home.State.completedLevelsInChapter+"|"+home.State.levelsPerChapter+"|"+home.State.stars+ServerStatsKey();
        void RenderStats(float width,float gap)
        {
            bool ready=StatsAvailable,progress=ready&&home.State.levelsPerChapter>0;
            string[] labels={"Level","Chapter","Chapter progress","Stars"},icons={"Level","Chapter","Progress","Stars"};
            string[] values={ready?home.State.currentLevel.ToString():"—",ready?home.State.chapterNumber.ToString():"—",progress?home.State.completedLevelsInChapter+" / "+home.State.levelsPerChapter:"—",ready?home.State.stars.ToString():"—"};
            int cols=StatsColumns;float cell=(width-gap*(cols-1))/cols;
            for(int i=0;i<4;i++)
            {
                var rt=R("Stat "+i,content);Place(rt,(i%cols)*(cell+gap),(i/cols)*342,cell,320);
                var card=Skin(rt,"Stat surface "+i,"Ivory",false);card.type=Image.Type.Sliced;card.pixelsPerUnitMultiplier=80f/38f;
                var icon=ImageNode(rt,"Stat icon "+i,"Stat_"+icons[i],false);Place(icon.rectTransform,32,28,124,124);icon.preserveAspect=true;SpriteFit.Center(icon);
                var value=Label(rt,"Stat value "+i,i==2?60:80,true,Ink);Place(value.rectTransform,168,26,cell-194,128);value.text=values[i];
                var label=Label(rt,"Stat label "+i,36,true,Ink);Place(label.rectTransform,28,159,cell-56,112);label.text=ProfileText.T(labels[i]);
                if(i==2)
                {
                    var track=ImageNode(rt,"Stats progress track","Progress_Track",false);Place(track.rectTransform,36,283,cell-72,18);track.type=Image.Type.Sliced;track.pixelsPerUnitMultiplier=4;
                    float filled=(cell-72)*(progress?Mathf.Clamp01(home.State.completedLevelsInChapter/(float)home.State.levelsPerChapter):0);
                    var clip=R("Stats progress clip",rt,false);Place(clip,36,283,filled,18);clip.gameObject.AddComponent<RectMask2D>();clip.gameObject.SetActive(filled>0);
                    var fill=ImageNode(clip,"Stats progress fill","Progress_Fill",false);Place(fill.rectTransform,0,0,Mathf.Max(12,filled),18);fill.type=Image.Type.Sliced;fill.pixelsPerUnitMultiplier=4;
                }
            }
            Place(content,0,0,width,Mathf.Ceil(4f/cols)*342-22);
        }
        void LayoutRename()
        {
            if(!renameLayer)return;float scale=canvas.scaleFactor;Rect sr=Screen.safeArea;if(sr.width<=0||sr.height<=0)sr=new Rect(0,0,Screen.width,Screen.height);
            float keyboard=TouchScreenKeyboard.visible?TouchScreenKeyboard.area.yMax:0;float bottom=Mathf.Max(sr.y,keyboard),h=Mathf.Max(80,(sr.yMax-bottom)/scale),w=sr.width/scale;
            Place(renameViewport,sr.x/scale,(Screen.height-sr.yMax)/scale,w,h);
            float localScale=Mathf.Min((sr.width-20)/823f,560f/823f)/scale;float ph=668*localScale,pw=823*localScale;
            Place(renameContent,0,0,w,Mathf.Max(h,ph+16));Place(renamePanel,(w-pw)/2,Mathf.Max(8,(h-ph)/2),823,668);renamePanel.localScale=new Vector3(localScale,localScale,1);
            Box("Rename chrome",0,0,823,668);Place(renameTitle.rectTransform,92,32,620,76);ButtonBox(renameClose,706,23,103,103,localScale);
            Place(renameHint.rectTransform,105,174,620,77);Box("Name input",86,262,650,106);Place(errorLabel.rectTransform,88,376,646,33);
            ButtonBox(save,205,402,412,119,localScale);ButtonBox(cancel,250,539,323,70,localScale);
            renameScroll.vertical=h<ph+16;if(lastKeyboard!=keyboard){Canvas.ForceUpdateCanvases();renameScroll.verticalNormalizedPosition=renameScroll.vertical?.5f:1;}lastKeyboard=keyboard;
        }
        RectTransform MakePortrait(Transform parent,string name,string avatar,string frame,bool track=true)
        {
            var r=R(name,parent,track);r.gameObject.AddComponent<RectMask2D>();var mask=R("Crop",r,false);Stretch(mask);mask.anchorMin=new Vector2(.057f,.057f);mask.anchorMax=new Vector2(.943f,.943f);var m=mask.gameObject.AddComponent<Image>();m.sprite=assets.Find("RoundMask");m.raycastTarget=false;mask.gameObject.AddComponent<Mask>().showMaskGraphic=false;
            var im=ImageNode(mask,"Portrait image","Avatar_"+avatar,false);Stretch(im.rectTransform);var fit=im.gameObject.AddComponent<AspectRatioFitter>();fit.aspectMode=AspectRatioFitter.AspectMode.EnvelopeParent;fit.aspectRatio=im.sprite.rect.width/im.sprite.rect.height;var border=ImageNode(r,"Frame","Frame"+frame,false);Stretch(border.rectTransform);return r;
        }
        void UpdatePortrait(RectTransform r,string avatar,string frame){var image=r.GetChild(0).GetChild(0).GetComponent<Image>();image.sprite=assets.Find("Avatar_"+avatar);image.GetComponent<AspectRatioFitter>().aspectRatio=image.sprite.rect.width/image.sprite.rect.height;r.GetChild(1).GetComponent<Image>().sprite=assets.Find("Frame"+frame);}
        Font CurrentFont(){return assets.profileFont?assets.profileFont:assets.home.boldFont;}
        void UpdateFonts(Transform root){foreach(var t in root.GetComponentsInChildren<Text>(true)){var font=CurrentFont();foreach(char c in t.text)if(!font.HasCharacter(c)){font=assets.profileFont;break;}t.font=font;}}
        void Depth(Text t,float outline,float shadow){var o=t.gameObject.AddComponent<Outline>();o.effectColor=new Color32(19,32,51,255);o.effectDistance=new Vector2(outline,-outline);var s=t.gameObject.AddComponent<Shadow>();s.effectColor=new Color32(19,32,51,255);s.effectDistance=new Vector2(0,-shadow);}
        Sprite CircleMask()
        {
            if(circleMask)return circleMask;var t=new Texture2D(128,128,TextureFormat.RGBA32,false);t.name="Profile circular mask";var pixels=new Color32[128*128];for(int y=0;y<128;y++)for(int x=0;x<128;x++){float distance=Vector2.Distance(new Vector2(x+.5f,y+.5f),new Vector2(64,64));pixels[y*128+x]=new Color32(255,255,255,(byte)(255*Mathf.Clamp01(63-distance)));}t.SetPixels32(pixels);t.Apply();circleMask=Sprite.Create(t,new Rect(0,0,128,128),new Vector2(.5f,.5f));return circleMask;
        }
        Sprite BannerMask()
        {
            if(bannerClip)return bannerClip;const int w=780,h=279;const float r=31;var t=new Texture2D(w,h,TextureFormat.RGBA32,false);var pixels=new Color32[w*h];for(int y=0;y<h;y++)for(int x=0;x<w;x++){float dx=Mathf.Max(Mathf.Abs(x+.5f-w*.5f)-(w*.5f-r),0),dy=Mathf.Max(Mathf.Abs(y+.5f-h*.5f)-(h*.5f-r),0);float a=Mathf.Clamp01(r-Mathf.Sqrt(dx*dx+dy*dy));pixels[y*w+x]=new Color32(255,255,255,(byte)(255*a));}t.SetPixels32(pixels);t.Apply();bannerClip=Sprite.Create(t,new Rect(0,0,w,h),new Vector2(.5f,.5f));return bannerClip;
        }
        Image CircleImage(Transform parent,string name,string asset)
        {
            var mask=R(name,parent,false);var m=mask.gameObject.AddComponent<Image>();m.sprite=CircleMask();m.raycastTarget=false;mask.gameObject.AddComponent<Mask>().showMaskGraphic=false;var im=ImageNode(mask,"Art",asset,false);Stretch(im.rectTransform);return im;
        }
        void ButtonBox(Button b,float x,float y,float w,float h,float localScale=1)
        {
            float min=44/(canvas.scaleFactor*localScale),hitW=Mathf.Max(w,min),hitH=Mathf.Max(h,min);Place((RectTransform)b.transform,x+(w-hitW)/2,y+(h-hitH)/2,hitW,hitH);var visual=(RectTransform)b.transform.GetChild(0);Place(visual,(hitW-w)/2,(hitH-h)/2,w,h);var image=visual.GetComponent<Image>();if(image&&image.type==Image.Type.Sliced)image.pixelsPerUnitMultiplier=image.sprite.rect.height/h;
        }
        void RefreshBackdrop()
        {
            var source=home.ProfileBackground;if(!source||(source==backdropSource&&(!backdropTexture||backdropTexture.IsCreated())))return;backdropSource=source;
            ProfileBackdrop.Release(backdropTexture);backdropTexture=ProfileBackdrop.Blur(source.texture);backdrop.texture=backdropTexture?backdropTexture:source.texture;
        }
        void CoverBackdrop(){if(!backdrop||!backdrop.texture)return;float a=Screen.width/(float)Screen.height,b=backdrop.texture.width/(float)backdrop.texture.height;backdrop.uvRect=a>b?new Rect(0,(1-b/a)/2,1,b/a):new Rect((1-a/b)/2,0,a/b,1);}
        void Cover(RawImage image,Sprite sprite){image.texture=sprite.texture;float a=image.rectTransform.rect.width/Mathf.Max(1,image.rectTransform.rect.height),b=sprite.texture.width/(float)sprite.texture.height;image.uvRect=a>b?new Rect(0,(1-b/a)/2,1,b/a):new Rect((1-a/b)/2,0,a/b,1);}
        static Color Ink=>new Color32(9,29,85,255);
        RectTransform R(string name,Transform parent,bool track=true){var r=new GameObject(name,typeof(RectTransform)).GetComponent<RectTransform>();r.SetParent(parent,false);if(track)nodes[name]=r;return r;}
        Image Plain(Transform parent,string name,Color color){var im=R(name,parent).gameObject.AddComponent<Image>();im.color=color;im.raycastTarget=false;return im;}
        Image ImageNode(Transform parent,string name,string asset,bool track=true){var im=R(name,parent,track).gameObject.AddComponent<Image>();im.sprite=assets.Find(asset);im.raycastTarget=false;return im;}
        Image Skin(Transform parent,string name,string asset,bool track=true){var im=ImageNode(parent,name,asset,track);im.type=Image.Type.Simple;Stretch(im.rectTransform);return im;}
        Text Label(Transform parent,string name,int fontSize,bool bold,Color color,TextAnchor align=TextAnchor.MiddleCenter){var t=R(name,parent,false).gameObject.AddComponent<Text>();if(parent==panel||parent==renamePanel)nodes[name]=t.rectTransform;t.font=CurrentFont();t.text="";t.fontSize=fontSize;t.color=color;t.alignment=align;t.supportRichText=false;t.raycastTarget=false;t.resizeTextForBestFit=true;t.resizeTextMinSize=Mathf.RoundToInt(fontSize*.68f);t.resizeTextMaxSize=fontSize;t.horizontalOverflow=HorizontalWrapMode.Wrap;t.verticalOverflow=VerticalWrapMode.Truncate;return t;}
        Button Icon(Transform parent,string name,string asset,Action action)
        {
            var r=R(name,parent);var hit=r.gameObject.AddComponent<Image>();hit.color=Color.clear;var b=r.gameObject.AddComponent<Button>();b.targetGraphic=hit;b.transition=Selectable.Transition.None;b.onClick.AddListener(()=>action());CircleImage(r,"Visual",asset);var a=r.gameObject.AddComponent<HomeControlLabel>();a.label=ProfileText.T(name.Contains("close")||name=="Close"?"Close":"Change name");return b;
        }
        Button ActionButton(Transform parent,string name,string text,Action action,string skin="Primary",int fontSize=34)
        {
            var r=R(name,parent);var hit=r.gameObject.AddComponent<Image>();hit.color=Color.clear;var b=r.gameObject.AddComponent<Button>();b.targetGraphic=hit;b.transition=Selectable.Transition.None;b.onClick.AddListener(()=>action());
            var visual=R("Visual",r,false);if(skin.Length>0){var image=visual.gameObject.AddComponent<Image>();image.sprite=assets.Find(skin);image.raycastTarget=false;if(skin=="Primary")image.type=Image.Type.Sliced;}
            var l=Label(visual,"Label",fontSize,true,skin.Length==0?Ink:Color.white);Stretch(l.rectTransform);l.text=ProfileText.T(text);if(skin.Length>0)Depth(l,1.2f,2);return b;
        }
        static void SetButton(Button button,string text){button.GetComponentInChildren<Text>().text=ProfileText.T(text);}
        void Box(string name,float x,float y,float w,float h){Place(nodes[name],x,y,w,h);}
        static void Place(RectTransform r,float x,float y,float w,float h){r.anchorMin=r.anchorMax=r.pivot=new Vector2(0,1);r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(Mathf.Max(0,w),Mathf.Max(0,h));}
        static void Stretch(RectTransform r){r.anchorMin=Vector2.zero;r.anchorMax=Vector2.one;r.pivot=new Vector2(.5f,.5f);r.offsetMin=r.offsetMax=Vector2.zero;}
        static void Focus(GameObject go){if(EventSystem.current&&go&&go.activeInHierarchy)EventSystem.current.SetSelectedGameObject(go);}
        void FocusTile(string id){var t=content.Find("Choice "+id);if(t)Focus(t.gameObject);}
        void OnDisable(){if(IsVisible)Hide();}
        void OnDestroy(){CloseServerProfile();if(home)home.NavigationRequested.RemoveListener(Route);if(store!=null)store.Changed-=Changed;ProfileBackdrop.Release(backdropTexture);if(circleMask){Destroy(circleMask.texture);Destroy(circleMask);}if(bannerClip){Destroy(bannerClip.texture);Destroy(bannerClip);}}
    }
}

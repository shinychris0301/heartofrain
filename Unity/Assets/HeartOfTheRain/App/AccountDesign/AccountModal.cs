using System;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.Localization;
namespace HeartOfTheRain.App.AccountDesign {
    [DisallowMultipleComponent] public sealed partial class AccountModal:MonoBehaviour {
        HomePage home;AccountDesignAssets art;ProfileAssets profiles;IAccountService service;
        // Keep actions clear of the painted frame and separate scroll content from the fixed footer.
        const float ContentSideInset=28,ContentTopInset=72,FooterBottomInset=22,FooterHeight=46,FooterGap=12;
        const float ContentReservedHeight=ContentTopInset+FooterGap+FooterHeight+FooterBottomInset;
        Canvas canvas;CanvasScaler scaler;RectTransform safe,panel,header,viewport,body,footer;ScrollRect scroll;
        RawImage backdrop;RenderTexture blurred;Sprite backdropSource;
        AccountStatus status;bool busy,linkError;int generation,locale;Vector2Int size;Rect safeArea;float uiScale;
        public event Action Dismissed;
        public bool IsVisible=>canvas&&canvas.gameObject.activeSelf;
        public AccountStatus Snapshot=>status?.Copy();
        public bool IsBusy=>busy;
        public string ScreenKey=>Managed!=null?"server":linkError||status==null||!status.localSaved&&!status.linked?"error":status.linked?"connected":!status.online?"offline":"save";
        public void Configure(HomePage owner,AccountDesignAssets assets){home=owner;art=assets;profiles=Resources.Load<ProfileAssets>("HeartOfTheRainProfile/Config");}
        public bool Show(IAccountService source){
            if(IsVisible||!home||!art||source==null)return false;
            service=source;AttachManagedAccount();ClearServerAccountInput();generation++;busy=linkError=false;Refresh();Build();canvas.gameObject.SetActive(true);Layout();Focus("Account close");Providers?.RefreshProviders();return true;
        }
        void Refresh(){try{status=service.Read()?.Copy()??new AccountStatus();}catch(Exception){status=new AccountStatus();linkError=true;}}
        public void Hide(bool notify=true){if(!IsVisible)return;generation++;busy=false;ClearServerAccountInput();canvas.gameObject.SetActive(false);if(notify)Dismissed?.Invoke();}
        public void Request(string action){
            if(!IsVisible)return;
            if(action=="close"||action=="back"||action=="dismiss"){Hide();return;}
            if(action=="copy"){if(!string.IsNullOrEmpty(status.playerId))GUIUtility.systemCopyBuffer=status.playerId;return;}
            if(HandleServerAccount(action))return;
            if(HandleProviderAccount(action))return;
            if(busy)return;
            if(action=="retry"){linkError=false;Refresh();Layout();Focus("Account close");return;}
            if(action!="Google"&&action!="Apple")return;
            if(status.linked||!status.online||!status.localSaved||!status.canLink||action=="Apple"&&Application.platform!=RuntimePlatform.IPhonePlayer)return;
            busy=true;linkError=false;int request=++generation;Layout();
            try{service.Link(action,result=>{
                if(!this||!IsVisible||generation!=request)return;
                busy=false;linkError=result==AccountLinkResult.Failed;Refresh();Layout();Focus("Account close");
            });}catch(Exception){if(IsVisible&&generation==request){busy=false;linkError=true;Layout();Focus("Account close");}}
        }
        void Build(){
            if(canvas)return;var root=R("Account Canvas",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=190;
#if UNITY_2022_3_OR_NEWER
            canvas.vertexColorAlwaysGammaSpace=true;
#endif
            scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;root.gameObject.AddComponent<GraphicRaycaster>();
            backdrop=R("Account backdrop",root).gameObject.AddComponent<RawImage>();Stretch(backdrop.rectTransform);backdrop.raycastTarget=false;
            var dim=R("Account input shield",root).gameObject.AddComponent<Image>();Stretch(dim.rectTransform);dim.color=new Color(.008f,.047f,.133f,.17f);
            safe=R("Account safe area",root);panel=R("Account panel",safe);var chrome=panel.gameObject.AddComponent<Image>();chrome.sprite=art.chrome;chrome.type=Image.Type.Sliced;chrome.pixelsPerUnitMultiplier=3.891f;chrome.color=Color.white;
            header=R("Account header",panel);viewport=R("Account body viewport",panel);viewport.gameObject.AddComponent<RectMask2D>();viewport.gameObject.AddComponent<Image>().color=Color.clear;
            scroll=viewport.gameObject.AddComponent<ScrollRect>();scroll.viewport=viewport;scroll.horizontal=false;scroll.vertical=true;scroll.movementType=ScrollRect.MovementType.Clamped;scroll.scrollSensitivity=35;
            body=R("Account body",viewport);scroll.content=body;footer=R("Account footer",panel);
            var track=R("Account scroll track",viewport);track.anchorMin=new Vector2(1,0);track.anchorMax=Vector2.one;track.pivot=new Vector2(1,.5f);track.sizeDelta=new Vector2(3,0);track.anchoredPosition=Vector2.zero;
            var handle=R("Handle",track);Stretch(handle);var hi=handle.gameObject.AddComponent<Image>();hi.color=new Color(.12f,.32f,.46f,.45f);hi.raycastTarget=false;
            var bar=track.gameObject.AddComponent<Scrollbar>();bar.direction=Scrollbar.Direction.BottomToTop;bar.handleRect=handle;bar.targetGraphic=hi;scroll.verticalScrollbar=bar;scroll.verticalScrollbarVisibility=ScrollRect.ScrollbarVisibility.AutoHide;
        }
        void Layout(){
            vkShownTarget="";
            CaptureServerAccountInput();
            foreach(var root in new[]{header,body,footer})foreach(Transform child in root){child.gameObject.SetActive(false);Destroy(child.gameObject);}
            Rect sr=Screen.safeArea;if(sr.width<=0||sr.height<=0)sr=new Rect(0,0,Screen.width,Screen.height);
            float scale=Mathf.Max(.25f,Mathf.Min(home.CurrentUIScale,Mathf.Min(sr.width/320f,sr.height/300f)));scaler.scaleFactor=scale;canvas.scaleFactor=scale;
            float w=sr.width/scale,h=sr.height/scale,pw=Mathf.Min(w-24,420),ph=Mathf.Min(620,h-60),px=(w-pw)/2,py=Mathf.Max(46,(h-ph)/2);bool compact=h<650;
            Place(safe,sr.x/scale,(Screen.height-sr.yMax)/scale,w,h);Place(panel,px,py,pw,ph);Place(header,0,0,pw,68);Place(viewport,ContentSideInset,ContentTopInset,pw-2*ContentSideInset,ph-ContentReservedHeight);Place(footer,ContentSideInset,ph-FooterBottomInset-FooterHeight,pw-2*ContentSideInset,FooterHeight);
            string key=ScreenKey;var title=Label(header,"Account title",AccountText.T(key=="server"?"serverTitle":key=="connected"?"accountTitle":key=="offline"?"offlineTitle":key=="error"?"errorTitle":"saveTitle"),30,6,pw-60,56,28,true);
            string heading=title.text;title.text="A";float singleLine=title.preferredHeight;title.text=heading;bool multiline=title.preferredHeight>singleLine*1.5f;title.fontSize=multiline?(pw<=320?21:23):28;title.lineSpacing=multiline?.85f:1;
            title.verticalOverflow=VerticalWrapMode.Overflow;title.resizeTextForBestFit=false;while(title.preferredHeight>56&&title.fontSize>(pw<=320?21:23))title.fontSize--;title.color=new Color32(248,240,221,255);var shadow=title.gameObject.AddComponent<Shadow>();shadow.effectColor=new Color(0,.05f,.15f,.85f);shadow.effectDistance=new Vector2(0,-2);var outline=title.gameObject.AddComponent<Outline>();outline.effectColor=new Color(0,.05f,.15f,1);outline.effectDistance=Vector2.one;
            var close=Button(header,"Account close","close","",pw-52,-32,46,46);var image=Picture(close.transform,"Account close art",art.close,-2.3f,-2.3f,50.6f,50.6f);image.preserveAspect=true;
            float bw=pw-2*ContentSideInset,y=0;Banner(bw,compact?99:130);y+=compact?109:140;
            if(key=="server")y=LayoutServerAccount(bw,y);
            else if(key=="save"){
                y=Paragraph("Save introduction",AccountText.T("saveIntro"),y,bw,15);
                if(Application.platform==RuntimePlatform.IPhonePlayer)y=Provider("Apple",art.apple,y,bw);
                y=Provider("VK",null,y,bw);y=Paragraph("Save promise",AccountText.T("promise"),y,bw,12);
                if(!status.canLink)y=Paragraph("Link availability",AccountText.T("linkUnavailable"),y,bw,12);
            }else if(key=="connected"){
                float statusY=y;y=Paragraph("Sync status",AccountText.T(status.CloudSaved?"saved":status.StatusKey),y,bw,19,true);
                if(status.CloudSaved){var label=body.Find("Sync status").GetComponent<Text>();float tw=label.preferredWidth;if(tw+32<=bw){float x=(bw-tw-32)/2;Picture(body,"Verified cloud check",art.check,x,statusY+(label.rectTransform.rect.height-24)/2,24,24).preserveAspect=true;Place(label.rectTransform,x+32,statusY,tw,label.rectTransform.rect.height);}}
                y=Paragraph("Account provider",string.IsNullOrEmpty(status.provider)?AccountText.T("connected"):status.provider+" · "+AccountText.T("connected"),y,bw,14);
                if(status.CloudSaved)y=Paragraph("Cloud timestamp",AccountText.T("cloud")+"\n"+DateTimeOffset.FromUnixTimeSeconds(status.confirmedCloudSaveUtc).UtcDateTime.ToString("yyyy-MM-dd HH:mm 'UTC'"),y,bw,13);
                else y=Paragraph("Local status",AccountText.T(status.localSaved?"saveLocalStatus":"localUnverified"),y,bw,12);
            }else{
                Picture(body,"Rain shield",art.shield,(bw-56)/2,y,56,56).preserveAspect=true;y+=62;
                y=Paragraph("Connection status",AccountText.T(key=="offline"?"offlineIntro":status.localSaved?"errorIntro":"localUnverified"),y,bw,15);
                y=Paragraph("Local status",AccountText.T(status.localSaved?"saveLocalStatus":"localUnverified"),y,bw,12);
                Button(body,"Account retry","retry",AccountText.T("retry"),0,y,bw,46,true);y+=54;
            }
            if(!string.IsNullOrEmpty(status.playerId)){
                y=Paragraph("Player ID",status.playerId,y,bw,12);Button(body,"Copy player ID","copy",AccountText.T("copy"),0,y,bw,44);y+=50;
            }
            if(busy)y=Paragraph("Link busy",AccountText.T("saving"),y,bw,14);
            // Retain the approved server panel size; overflowing content scrolls inside it.
            if(key!="server")ph=Mathf.Min(ph,y+134);py=Mathf.Max(46,(h-ph)/2);Place(panel,px,py,pw,ph);Place(viewport,ContentSideInset,ContentTopInset,pw-2*ContentSideInset,ph-ContentReservedHeight);Place(footer,ContentSideInset,ph-FooterBottomInset-FooterHeight,pw-2*ContentSideInset,FooterHeight);
            Place(body,0,0,bw,Mathf.Max(y,ph-ContentReservedHeight));if(!LayoutVkFooter102(bw))Button(footer,"Account return","dismiss",AccountText.T(key=="save"?"notNow":key=="connected"||key=="server"?"continue":"keep"),0,0,bw,46,key=="connected"||key=="server");
            scroll.verticalNormalizedPosition=1;Canvas.ForceUpdateCanvases();locale=GameLocale.Revision;size=new Vector2Int(Screen.width,Screen.height);safeArea=Screen.safeArea;uiScale=home.CurrentUIScale;
            var source=home.ProfileBackground;if(source&&(!blurred||source!=backdropSource)){ProfileBackdrop.Release(blurred);blurred=ProfileBackdrop.Blur(source.texture);backdropSource=source;backdrop.texture=blurred?(Texture)blurred:source.texture;}
            if(backdrop.texture){float a=Screen.width/(float)Screen.height,b=backdrop.texture.width/(float)backdrop.texture.height;backdrop.uvRect=a>b?new Rect(0,(1-b/a)/2,1,b/a):new Rect((1-a/b)/2,0,a/b,1);}
        }
        void Banner(float w,float h){
            var selection=home.GetComponent<ProfilePage>()?.Snapshot??new ProfileData();var scene=R("Account banner",body);Place(scene,0,0,w,h);scene.gameObject.AddComponent<RectMask2D>();var raw=R("Village banner",scene).gameObject.AddComponent<RawImage>();Stretch(raw.rectTransform);var sprite=profiles?profiles.Find("Banner_"+selection.bannerId):art.banner;raw.texture=sprite.texture;raw.raycastTarget=false;
            float a=w/h,b=raw.texture.width/(float)raw.texture.height;raw.uvRect=a>b?new Rect(0,(1-b/a)/2,1,b/a):new Rect((1-a/b)/2,0,a/b,1);
            var shade=R("Banner shade",scene).gameObject.AddComponent<Image>();Stretch(shade.rectTransform);shade.color=new Color(0,.03f,.1f,.32f);shade.raycastTarget=false;
            float sz=h<120?64:82;var portrait=R("Account portrait",scene);Place(portrait,10,(h-sz)/2,sz,sz);
            if(profiles){var crop=R("Avatar crop",portrait);Place(crop,sz*.06f,sz*.06f,sz*.88f,sz*.88f);var mask=crop.gameObject.AddComponent<Image>();mask.sprite=profiles.Find("RoundMask");mask.raycastTarget=false;crop.gameObject.AddComponent<Mask>().showMaskGraphic=false;var avatar=Picture(crop,"Selected avatar",profiles.Find("Avatar_"+selection.avatarId),0,0,sz*.88f,sz*.88f);avatar.preserveAspect=true;Picture(portrait,"Selected frame",profiles.Find("Frame"+selection.frameId),0,0,sz,sz).preserveAspect=true;}
            var name=Label(scene,"Account display name",selection.displayName,sz+20,h/2-22,w-sz-30,28,18,true);name.color=Color.white;while(name.preferredHeight>28&&name.fontSize>12)name.fontSize--;
            var detail=Label(scene,"Journey level",GameLocale.Format("Level {0}",home.State.currentLevel)+" · "+ProfileText.T("Chapter")+" "+home.State.chapterNumber,sz+20,h/2+8,w-sz-30,24,12);detail.color=Color.white;
        }
        float Provider(string name,Sprite mark,float y,float w){var b=Button(body,"Provider "+name,name,AccountText.T(name.ToLowerInvariant()),0,y,w,50);b.interactable=name!="VK"&&status.canLink&&!busy;var text=b.GetComponentInChildren<Text>();Place(text.rectTransform,42,0,w-50,50);if(mark)Picture(b.transform,"Provider mark",mark,14,14,22,22).preserveAspect=true;else Label(b.transform,"VK label mark","VK",8,0,36,50,14,true).color=new Color32(0,119,255,255);var face=b.targetGraphic as Image;face.color=name=="Apple"?Color.black:Color.white;text.color=name=="Apple"?Color.white:new Color32(9,29,85,255);return y+60;}
        float Paragraph(string name,string text,float y,float w,int fontSize,bool bold=false){var label=Label(body,name,text,2,y,w-4,200,fontSize,bold);float h=Mathf.Max(fontSize*1.5f,label.preferredHeight+8);Place(label.rectTransform,2,y,w-4,h);return y+h+7;}
        Text Label(Transform parent,string name,string value,float x,float y,float w,float h,int fontSize,bool bold=false){var rt=R(name,parent);Place(rt,x,y,w,h);var t=rt.gameObject.AddComponent<Text>();t.font=bold?art.titleFont:art.bodyFont;t.text=value;t.fontSize=fontSize;t.alignment=TextAnchor.MiddleCenter;t.supportRichText=false;t.raycastTarget=false;t.horizontalOverflow=HorizontalWrapMode.Wrap;t.verticalOverflow=VerticalWrapMode.Truncate;t.color=new Color32(9,29,85,255);return t;}
        Button Button(Transform parent,string name,string action,string label,float x,float y,float w,float h,bool primary=false){var rt=R(name,parent);Place(rt,x,y,w,h);var face=rt.gameObject.AddComponent<Image>();face.color=primary?Color.white:Color.clear;if(primary){face.sprite=art.primary;face.type=Image.Type.Sliced;face.pixelsPerUnitMultiplier=h<56?13.33f:8.57f;}var b=rt.gameObject.AddComponent<Button>();b.targetGraphic=face;b.onClick.AddListener(()=>Request(action));if(label.Length>0){var t=Label(rt,name+" label",label,8,4,w-16,h-8,primary?19:14,primary);t.resizeTextForBestFit=true;t.resizeTextMinSize=primary?13:12;t.resizeTextMaxSize=primary?19:14;if(primary)t.color=Color.white;}var access=rt.gameObject.AddComponent<HomeControlLabel>();access.action=action;access.label=label.Length>0?label:AccountText.T("close");return b;}
        static Image Picture(Transform parent,string name,Sprite sprite,float x,float y,float w,float h){var rt=R(name,parent);Place(rt,x,y,w,h);var im=rt.gameObject.AddComponent<Image>();im.sprite=sprite;im.color=Color.white;im.raycastTarget=false;return im;}
        void Update(){if(!IsVisible)return;if(size.x!=Screen.width||size.y!=Screen.height||safeArea!=Screen.safeArea||locale!=GameLocale.Revision||Mathf.Abs(uiScale-home.CurrentUIScale)>.01f){Layout();Focus("Account close");}
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
            bool back=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
            bool back=Input.GetKeyDown(KeyCode.Escape);
#endif
            if(back)Hide();
        }
        void Focus(string name){if(!EventSystem.current)return;foreach(var b in canvas.GetComponentsInChildren<Button>())if(b.name==name){EventSystem.current.SetSelectedGameObject(b.gameObject);return;}}
        static RectTransform R(string name,Transform parent){var rt=new GameObject(name,typeof(RectTransform)).GetComponent<RectTransform>();rt.SetParent(parent,false);return rt;}
        static void Stretch(RectTransform rt){rt.anchorMin=Vector2.zero;rt.anchorMax=Vector2.one;rt.offsetMin=rt.offsetMax=Vector2.zero;}
        static void Place(RectTransform rt,float x,float y,float w,float h){rt.anchorMin=rt.anchorMax=rt.pivot=new Vector2(0,1);rt.anchoredPosition=new Vector2(x,-y);rt.sizeDelta=new Vector2(w,h);}
        void OnDestroy(){ReleaseManagedAccount();generation++;ProfileBackdrop.Release(blurred);}
    }
}

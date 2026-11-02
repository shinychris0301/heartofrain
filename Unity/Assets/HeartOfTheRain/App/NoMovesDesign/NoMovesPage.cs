using System;
using System.Collections.Generic;
using System.Collections;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.Shop;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.ShopCheckout86;
namespace HeartOfTheRain.App.NoMoves {
    public sealed partial class NoMovesPage:MonoBehaviour {
        public HomePage home;public NoMovesAssets art;public Action<string> Requested;public string Status="";
        public string Screen {get;private set;}public bool Visible=>(canvas&&canvas.gameObject.activeSelf)||(r3&&r3.gameObject.activeSelf);
        public readonly Dictionary<string,RectTransform> Nodes=new Dictionary<string,RectTransform>();
        Canvas canvas;CanvasScaler scaler;RectTransform safe,body;ContinueOffer quote;int coins,locale,generation;bool busy;Vector2Int size;Rect safeRect;
        // The notice owns the screen briefly while the offer is prepared in
        // parallel. Keep only the latest result: never flash a fallback modal.
        const float NoticeDuration=1f;
        bool noticePending,applicationPaused;string nextScreen;ContinueOffer nextQuote;int nextCoins;bool nextBusy;Coroutine noticeTimer;
        Font Title=>art&&art.titleFont?art.titleFont:Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        Font Regular=>art&&art.bodyFont?art.bodyFont:Title;
        public void Show(string screen,ContinueOffer offer,int balance,bool disabled){
            if(noticePending&&screen!="notice"){nextScreen=screen;nextQuote=offer;nextCoins=balance;nextBusy=disabled;return;}
            if(screen!="shop")checkout86Open=false;Screen=screen;quote=offer;coins=balance;busy=disabled;Build();canvas.gameObject.SetActive(true);Layout();
        }
        public void ShowExhaustionNotice(int balance){
            if(noticeTimer!=null)StopCoroutine(noticeTimer);
            noticePending=false;nextScreen=null;Show("notice",null,balance,true);noticePending=true;
            noticeTimer=StartCoroutine(CompleteNotice());
        }
        IEnumerator CompleteNotice(){
            float shown=0;yield return null;
            while(shown<NoticeDuration){if(!applicationPaused)shown+=Mathf.Min(Time.unscaledDeltaTime,.1f);yield return null;}
            // An asset load can outlast the notice. Keep the notice visible
            // until a real prefab or a final error exists, avoiding two modal layouts.
            while(noticePending&&(nextScreen==null||(nextScreen=="loading"&&(!art||!art.continuePrefab))))yield return null;
            if(!noticePending)yield break;
            noticePending=false;noticeTimer=null;Show(nextScreen,nextQuote,nextCoins,nextBusy);
        }
        public void Hide(){noticePending=false;nextScreen=null;if(noticeTimer!=null){StopCoroutine(noticeTimer);noticeTimer=null;}if(canvas)canvas.gameObject.SetActive(false);if(r3)r3.gameObject.SetActive(false);}
        void OnApplicationPause(bool paused){applicationPaused=paused;}
        public void SetBusy(bool value){busy=value;if(noticePending)nextBusy=value;if(r3&&r3.gameObject.activeSelf){r3.SetTransactionPending(value);return;}if(Visible)foreach(var b in canvas.GetComponentsInChildren<Button>())b.interactable=!value&&b.name!="Unavailable store purchase"&&(Screen!="unknown"||b.name=="Play on");CheckoutButtons86();}
        void Build(){if(canvas)return;var root=R("No Moves Canvas",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=200;scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;root.gameObject.AddComponent<GraphicRaycaster>();
            var shield=R("No Moves shield",root);shield.anchorMin=Vector2.zero;shield.anchorMax=Vector2.one;shield.offsetMin=shield.offsetMax=Vector2.zero;shield.gameObject.AddComponent<Image>().color=new Color(.008f,.039f,.094f,.74f);safe=R("No Moves safe area",root);}
        void Layout(){
            generation++;if(UseR3){RenderR3();return;}if(r3)r3.gameObject.SetActive(false);canvas.gameObject.SetActive(true);
            foreach(Transform child in safe){child.gameObject.SetActive(false);Destroy(child.gameObject);}Nodes.Clear();
            var sr=UnityEngine.Screen.safeArea;if(sr.width<=0||sr.height<=0)sr=new Rect(0,0,UnityEngine.Screen.width,UnityEngine.Screen.height);
            float scale=Mathf.Max(.25f,Mathf.Min(home.CurrentUIScale,Mathf.Min(sr.width/320,sr.height/520)));scaler.scaleFactor=scale;canvas.scaleFactor=scale;float w=sr.width/scale,h=sr.height/scale;Place(safe,sr.x/scale,(UnityEngine.Screen.height-sr.yMax)/scale,w,h);
            bool compact=h<680||w<345;float pw=Mathf.Min(w-16,430);body=R("No Moves content",safe);
            if(Screen=="notice"){
                Place(body,(w-pw)/2,(h-86)/2,pw,86);var band=Picture(body,"Notice band",art?art.notice:null,0,0,pw,86,true);if(!band.sprite)band.color=new Color32(18,64,107,255);Label(body,"Notice title",NoMovesText.T("out"),12,0,pw-24,86,30,true,new Color32(255,247,225,255));
            }else if(Screen=="waiting"){
                Place(body,(w-pw)/2,(h-70)/2,pw,70);Label(body,"Waiting title",NoMovesText.T("loadingOffer"),12,0,pw-24,70,22,true,Color.white);
            }else if(Screen=="shop")BuildShop(w,h,pw);
            else if(Screen=="confirm")BuildConfirm(w,h,pw);
            else{
                float hero=compact?153:196,ph=60+hero+79,total=ph+54,top=Mathf.Max(38,(h-total)/2);Place(body,(w-pw)/2,top,pw,total);
                Wallet(body,pw,0);var panel=R("Continue panel",body);Place(panel,0,54,pw,ph);Picture(panel,"Continue band",art?art.band:null,0,0,pw,ph,true);
                Label(panel,"Continue title",NoMovesText.T("continue"),24,4,pw-48,52,30,true,new Color32(255,247,225,255));Close(panel,pw);
                float left=pw*.46f;Picture(panel,"Dariya",art?art.hero:null,8,60,left-8,hero,false,true);
                float bw=compact?78:99,bh=compact?88:112,ox=left+(pw-left-bw)/2;Picture(panel,"Offer halo",art?art.halo:null,left,60,pw-left,hero,false,true);Picture(panel,"Moves badge",art?art.badge:null,ox,64,bw,bh,false,true);
                string moves=quote==null?"\u2014":"+"+quote.moves;Label(panel,"Extra move count",moves,ox,64,bw,bh,compact?36:44,true,Color.white);
                Label(panel,"Offer description",Screen=="error"?NoMovesText.T("offerError"):Screen=="loading"?NoMovesText.T("loadingOffer"):quote==null?NoMovesText.T("unavailable"):NoMovesText.T("addMoves").Replace("{n}",quote.moves.ToString()),left+4,64+bh,pw-left-8,Mathf.Max(35,hero-bh-8),compact?16:19,false,new Color32(30,54,74,255));
                string key=Screen=="error"?"retry":Screen=="loading"?"loadingOffer":Screen=="unknown"?"check":quote==null?"end":"play";string action=Screen=="error"?"retryQuote":Screen=="unknown"?"check":quote==null?"back":"play";
                var play=Button(panel,"Play on",action,(key=="retry"?GameLocale.T("Try again"):NoMovesText.T(key)),18,ph-69,pw-36,57,art?art.primary:null,24);if(quote!=null&&Screen!="unknown"){float actionWidth=pw-36;Place(play.transform.Find("Play on label").GetComponent<RectTransform>(),5,0,actionWidth*.61f,57);Picture(play.transform,"Price coin",art?art.coin:null,actionWidth*.65f,17,22,22,false,true);Label(play.transform,"Move price",quote.cost.ToString(),actionWidth*.73f,0,actionWidth*.24f,57,22,true,Color.white);}
                if(Screen=="unknown")Label(body,"Purchase reconciliation",NoMovesText.T("checking"),4,total+8,pw-8,62,14,false,Color.white);
                if(!string.IsNullOrEmpty(Status))Label(body,"Continue status",Status,4,total+6,pw-8,50,13,false,Color.white);
            }
            SetBusy(busy);Canvas.ForceUpdateCanvases();size=new Vector2Int(UnityEngine.Screen.width,UnityEngine.Screen.height);safeRect=UnityEngine.Screen.safeArea;locale=GameLocale.Revision;
            if(EventSystem.current){var target=Nodes.ContainsKey(Screen=="shop"?"Shop back":"Play on")?Nodes[Screen=="shop"?"Shop back":"Play on"].gameObject:null;EventSystem.current.SetSelectedGameObject(target);}
        }
        void Wallet(Transform root,float width,float y){var wallet=Button(root,"Wallet","shop","",Mathf.Max(0,width-158),y,158,42,art?art.wallet:null);Picture(wallet.transform,"Wallet coin",art?art.coin:null,9,9,24,24,false,true);Label(wallet.transform,"Wallet amount",coins.ToString("N0"),37,0,112,42,19,true,Color.white);}
        void BuildConfirm(float w,float h,float pw){
            const float ph=310;Place(body,(w-pw)/2,(h-ph)/2,pw,ph);
            Picture(body,"End panel",art?art.chrome:null,0,0,pw,ph,true,false,3.891f);
            Label(body,"End title",NoMovesText.T("endTitle"),20,12,pw-40,50,28,true,Color.white);
            Picture(body,"Lost heart",art?art.heart:null,(pw-54)/2,70,54,54,false,true);
            Label(body,"Life loss warning",NoMovesText.T("loseLife"),12,130,pw-24,38,18,false,new Color32(27,47,66,255));
            // Match the approved compact primary: fit localized copy and preserve its gold corners.
            float keepWidth=Mathf.Clamp(Measure(NoMovesText.T("keep"),22,true)+50,185,pw-40);
            float endWidth=Mathf.Clamp(Measure(NoMovesText.T("end"),18,true)+46,185,pw-40);
            Button(body,"Keep attempt","back",NoMovesText.T("keep"),(pw-keepWidth)/2,178,keepWidth,57,art?art.primary:null);
            Button(body,"End attempt","end",NoMovesText.T("end"),(pw-endWidth)/2,244,endWidth,48,art?art.secondary:null,18);
        }
        void BuildShop(float w,float h,float pw){
            pw=Mathf.Min(w-20,600);float ph=Mathf.Min(h-38,700);Place(body,(w-pw)/2,(h-ph)/2,pw,ph);Picture(body,"Shop panel",art?art.chrome:null,0,0,pw,ph,true,false,3.891f);Label(body,"Shop title",NoMovesText.T("shop"),20,3,pw-40,56,30,true,Color.white);Close(body,pw);
            // AccountChrome's cream surface is inset from its outer RectTransform.
            // Keep fixed header/footer controls and the masked list inside that surface.
            var interior=R("Shop interior",body);float iw=pw-64,ih=ph-116;Place(interior,32,82,iw,ih);Wallet(interior,iw,0);
            var checkout=CheckoutView86();Label(interior,"Shop availability",checkout!=null&&checkout.configured?checkout.Status:NoMovesText.T("storeUnavailable"),0,54,iw,62,14,false,new Color32(27,47,66,255));
            float footerY=ih-48,listHeight=footerY-14-130;
            var viewport=R("Coin pack viewport",interior);Place(viewport,0,130,iw,listHeight);viewport.gameObject.AddComponent<Image>().color=Color.clear;viewport.gameObject.AddComponent<RectMask2D>();var content=R("Coin packs",viewport);var scroll=viewport.gameObject.AddComponent<ScrollRect>();scroll.viewport=viewport;scroll.content=content;scroll.horizontal=false;scroll.movementType=ScrollRect.MovementType.Clamped;
            var existing=home.GetComponent<ShopPage>();var catalog=existing&&existing.assets&&existing.assets.catalog?new ShopSession(JsonUtility.FromJson<ShopCatalog>(existing.assets.catalog.text)):null;var packs=catalog==null?new ShopOffer[0]:catalog.Coins;float y=0;
            foreach(var pack in packs){
                float rw=iw,bw=Mathf.Max(104,(rw-20)*.34f),bx=rw-10-bw;
                var row=R("Coin pack "+pack.id,content);Place(row,0,y,rw,91);Picture(row,"Coin pack background",art?art.mega:null,0,0,rw,82,true,false,4*100/(art&&art.mega?art.mega.pixelsPerUnit:100));
                bool narrow=rw<265;float textX=narrow?50:62;
                Picture(row,"Coin pack art",art?art.pouch:null,narrow?8:10,narrow?22:18,narrow?36:45,narrow?36:45,false,true);
                Label(row,"Coin quantity",NoMovesText.T("coinAmount").Replace("{n}",pack.coins.ToString("N0")),textX,10,bx-textX-7,62,narrow?20:23,true,new Color32(27,47,66,255));
                bool selected=checkout!=null&&checkout.configured;bool pending=selected&&checkout.pending&&checkout.pendingProduct==pack.id;string amount=selected?checkout.price?.Invoke(pack.id):null;
                string action=selected?(pending?"checkout:retry":"checkout:buy:"+pack.id):"store";
                var buy=Button(row,selected?"Checkout purchase "+pack.id:"Unavailable store purchase",action,pending?NoMovesText.T("check"):amount??GameLocale.T("Unavailable"),bx,15,bw,51,art?art.primary:null,15);
                if(selected)FitCheckoutPrice86(buy,pending?CheckoutText86.T("retry"):amount==null?GameLocale.T("Unavailable"):CheckoutText86.Buy(amount),action);
                var face=buy.targetGraphic as Image;if(face&&face.sprite)face.pixelsPerUnitMultiplier=(300f/30)*canvas.referencePixelsPerUnit/face.sprite.pixelsPerUnit;
                buy.interactable=selected&&!checkout.busy&&(pending||checkout.canBuy?.Invoke(pack.id)==true);y+=91;
            }
            float backWidth=Mathf.Clamp(Regular?Measure(NoMovesText.T("return"),17)+46:185,160,iw);
            Place(content,0,0,iw,Mathf.Max(y,listHeight));var back=Button(interior,"Shop back","back",NoMovesText.T("return"),(iw-backWidth)/2,footerY,backWidth,48,art?art.secondary:null,17);
            var backFace=back.targetGraphic as Image;if(backFace&&backFace.sprite)backFace.pixelsPerUnitMultiplier=4*canvas.referencePixelsPerUnit/backFace.sprite.pixelsPerUnit;
        }
        float Measure(string text,int fontSize,bool title=false){var settings=new TextGenerationSettings{font=title?Title:Regular,fontSize=fontSize,scaleFactor=1,fontStyle=FontStyle.Normal,horizontalOverflow=HorizontalWrapMode.Overflow,verticalOverflow=VerticalWrapMode.Overflow,richText=false,lineSpacing=1};return new TextGenerator().GetPreferredWidth(text,settings);}
        void Close(Transform root,float width){var close=Button(root,"Continue close","back","",width-54,-19,48,48,null);Picture(close.transform,"Close art",art?art.close:null,-2,-2,52,52,false,true);}
        Button Button(Transform parent,string name,string action,string text,float x,float y,float w,float h,Sprite sprite,int font=22){var r=R(name,parent);Place(r,x,y,w,h);var hit=r.gameObject.AddComponent<Image>();hit.color=Color.clear;var button=r.gameObject.AddComponent<Button>();button.targetGraphic=hit;button.interactable=!busy;int binding=generation;button.onClick.AddListener(()=>{if(binding==generation&&Visible&&!busy)Requested?.Invoke(action);});var graphic=Picture(r,name+" art",sprite,0,0,w,h,true);if(graphic&&sprite){
                if(art&&(sprite==art.primary||sprite==art.secondary)){
                    float density=sprite==art.primary?Mathf.Max(300f/35,(sprite.border.y+sprite.border.w)/Mathf.Max(1,h)):4;
                    graphic.pixelsPerUnitMultiplier=density*canvas.referencePixelsPerUnit/sprite.pixelsPerUnit;
                }
                button.targetGraphic=graphic;button.colors=new ColorBlock{normalColor=Color.white,highlightedColor=new Color(1,1,.94f),pressedColor=new Color(.85f,.9f,1),selectedColor=Color.white,disabledColor=new Color(.65f,.65f,.65f),colorMultiplier=1,fadeDuration=.1f};}if(!string.IsNullOrEmpty(text))Label(r,name+" label",text,5,0,w-10,h,font,true,art&&sprite==art.secondary?new Color32(27,47,66,255):Color.white);return button;}
        Text Label(Transform parent,string name,string text,float x,float y,float w,float h,int size,bool title,Color color){var r=R(name,parent);Place(r,x,y,w,h);var t=r.gameObject.AddComponent<Text>();t.font=title?Title:Regular;t.text=text;t.fontSize=size;t.color=color;t.raycastTarget=false;t.supportRichText=false;t.alignment=TextAnchor.MiddleCenter;t.horizontalOverflow=HorizontalWrapMode.Wrap;t.verticalOverflow=VerticalWrapMode.Truncate;t.resizeTextForBestFit=true;t.resizeTextMinSize=Mathf.Max(11,size-5);t.resizeTextMaxSize=size;return t;}
        Image Picture(Transform parent,string name,Sprite sprite,float x,float y,float w,float h,bool sliced=false,bool aspect=false,float multiplier=1){var r=R(name,parent);Place(r,x,y,w,h);var im=r.gameObject.AddComponent<Image>();im.sprite=sprite;im.color=sprite?Color.white:Color.clear;im.raycastTarget=false;im.preserveAspect=aspect;im.type=sliced&&sprite&&sprite.border!=Vector4.zero?Image.Type.Sliced:Image.Type.Simple;im.pixelsPerUnitMultiplier=multiplier;return im;}
        RectTransform R(string name,Transform parent){var r=new GameObject(name,typeof(RectTransform)).GetComponent<RectTransform>();r.SetParent(parent,false);r.anchorMin=r.anchorMax=r.pivot=new Vector2(0,1);Nodes[name]=r;return r;}
        static void Place(RectTransform r,float x,float y,float w,float h){r.anchoredPosition=new Vector2(x,-y);r.sizeDelta=new Vector2(w,h);}
        void Update(){if(!Visible)return;if(size.x!=UnityEngine.Screen.width||size.y!=UnityEngine.Screen.height||safeRect!=UnityEngine.Screen.safeArea||locale!=GameLocale.Revision)Layout();if(Input.GetKeyDown(KeyCode.Escape)&&!busy)Requested?.Invoke("back");}
    }
}

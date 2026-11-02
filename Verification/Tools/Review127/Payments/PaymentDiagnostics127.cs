#if HOTR_DIAGNOSTICS127
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using HeartOfTheRain.App.AccountDesign;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.ShopCheckout86;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification.Diagnostics127 {
    [Serializable] public sealed class PaymentDiagnosticSnapshot127 {
        public int version=1,readCount,availabilityRequests;
        public string observation="NOT_READ",serverLastError="NONE",checkoutError="NONE",vkPhase="NONE",sdkResult="NOT_REQUESTED",sdkCause="NONE",sdkError="NONE",exceptionType="NONE";
        public bool privateDiagnostic=true,serverSelected,serverReady,serverBusy,accountBlocked,serverHasPending,activeAttempt;
        public bool checkoutPresent,checkoutConfigured,checkoutFlowKnown,checkoutFlowBound,checkoutBusy,checkoutPending,firstOfferPriced;
        public bool accountModalPresent,accountModalVisible,accountUiBusy,vkProviderPresent,vkProviderAvailable,vkProviderBusy,vkStatePresent,vkPending,vkBeginPresent,vkBeginActive,vkBeginInteractable;
        public bool sdkCompiled,availabilityBusy,sdkCallbackReceived,sdkAvailable,writeSucceeded;
    }

    // This component exists only in an explicitly prepared private diagnostic
    // copy. Boot creates UI only. Both reads and the sole SDK query are manual.
    public sealed class PaymentDiagnostics127:MonoBehaviour {
        const string Package="com.heartoftherain.game",FileName="PaymentDiagnostics127.json";
        readonly ConcurrentQueue<Action> callbacks=new ConcurrentQueue<Action>();
        readonly PaymentDiagnosticSnapshot127 state=new PaymentDiagnosticSnapshot127();
        Text text;GameObject expanded;bool querying;int queryGeneration,reads,requests;
        static PaymentDiagnostics127 singleton;
        static readonly Regex NamePattern=new Regex(@"\A[A-Za-z_][A-Za-z0-9_.]{0,95}\z",RegexOptions.CultureInvariant);
        static readonly HashSet<string> KnownNames=new HashSet<string>(PaymentDiagnosticNames127.Values,StringComparer.Ordinal);
        static readonly HashSet<string> Phases=new HashSet<string>(new[]{"Empty","Idle","Prepared","Pending","Ready","Committing","Completed","Cancelled","Canceled","Failed","Expired","Rejected","Exchanging"},StringComparer.Ordinal);
        static readonly HashSet<string> Results=new HashSet<string>(new[]{"NOT_REQUESTED","UNSUPPORTED_PRIVATE_CONTEXT","REQUESTED","FAILURE","NULL_RESULT","SUCCESS","EXCEPTION","SDK_NOT_COMPILED"},StringComparer.Ordinal);

        public static string SafeName(string value){
            if(string.IsNullOrEmpty(value))return "NONE";
            return value.Length<=96&&NamePattern.IsMatch(value)&&KnownNames.Contains(value)?value:"UNLISTED_NAME";
        }
        public static string SafePhase(string value)=>string.IsNullOrEmpty(value)||value=="NONE"?"NONE":Phases.Contains(value)?value:"UNLISTED_PHASE";
        public static string SafeException(Exception value)=>value==null?"NONE":SafeName(value.GetType().Name);
        public static string Serialize(PaymentDiagnosticSnapshot127 value){
            value.serverLastError=SafeName(value.serverLastError);value.checkoutError=SafeName(value.checkoutError);value.vkPhase=SafePhase(value.vkPhase);
            value.sdkCause=SafeName(value.sdkCause);value.sdkError=SafeName(value.sdkError);value.exceptionType=SafeName(value.exceptionType);
            value.sdkResult=Results.Contains(value.sdkResult??"")?value.sdkResult:"UNLISTED_RESULT";
            value.observation=value.observation=="NOT_READ"||value.observation=="LOCAL_STATUS_READ"||value.observation=="LOCAL_READ_EXCEPTION"?value.observation:"UNLISTED_OBSERVATION";
            value.readCount=Math.Max(0,Math.Min(999,value.readCount));value.availabilityRequests=Math.Max(0,Math.Min(20,value.availabilityRequests));
            string result=JsonUtility.ToJson(value,false);
            if(result.Length>8192)throw new InvalidOperationException("DiagnosticOutputBound127");
            return result;
        }
        public static bool PrivacyChecks(){
            foreach(string value in new[]{"Bearer private-token","https://private.invalid/?token=abc","7f6e5d4c3b2a1098","SECRET_SENSITIVE_12345","eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJwcml2YXRlIn0.signature",new string('A',400),"RuStoreException\nprivate"})
                if(SafeName(value)!="UNLISTED_NAME")return false;
            if(SafeName(null)!="NONE"||SafeName("CheckoutPaymentUnavailable")!="CheckoutPaymentUnavailable"||SafePhase("private-subject")!="UNLISTED_PHASE")return false;
            var probe=new PaymentDiagnosticSnapshot127{serverLastError="Bearer private-token",sdkError="SECRET_SENSITIVE_12345",sdkCause="https://private.invalid/",vkPhase="private-subject",sdkResult="private-result",observation="private-observation",exceptionType="private-exception"};
            string json=Serialize(probe);
            return !json.Contains("private-token")&&!json.Contains("SECRET_SENSITIVE")&&!json.Contains("private.invalid")&&!json.Contains("private-subject")&&!json.Contains("private-result")&&!json.Contains("private-observation")&&!json.Contains("private-exception")&&json.Length<8192;
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)] static void Bootstrap(){
#if UNITY_ANDROID && DEVELOPMENT_BUILD && !UNITY_EDITOR
            if(Application.identifier!=Package||singleton)return;
            var owner=new GameObject("Private payment diagnostics127",typeof(RectTransform));DontDestroyOnLoad(owner);singleton=owner.AddComponent<PaymentDiagnostics127>();
#endif
        }
        void Awake(){
            if(Application.isEditor||Application.platform!=RuntimePlatform.Android||Application.identifier!=Package||!Debug.isDebugBuild){enabled=false;return;}
#if HOTR_RUSTORE_PAY
            state.sdkCompiled=true;
#endif
            var canvas=gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=32760;
            var scaler=gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ScaleWithScreenSize;scaler.referenceResolution=new Vector2(900,1600);
            gameObject.AddComponent<GraphicRaycaster>();
            var root=Panel(transform,"Private diagnostic panel",new Vector2(430,810),new Vector2(-12,-110));
            root.GetComponent<Image>().color=Color.clear;root.GetComponent<Image>().raycastTarget=false;
            Button(root,"Diagnostics127",new Vector2(0,0),()=>expanded.SetActive(!expanded.activeSelf));
            expanded=Panel(root,"Manual diagnostic controls",new Vector2(430,750),new Vector2(0,-60)).gameObject;
            Button(expanded.transform,"Read local status",new Vector2(0,0),ReadStatus);
            Button(expanded.transform,"Query payment availability",new Vector2(0,-58),QueryAvailability);
            var label=new GameObject("Static diagnostic snapshot",typeof(RectTransform),typeof(Text));label.transform.SetParent(expanded.transform,false);
            var rect=(RectTransform)label.transform;rect.anchorMin=rect.anchorMax=rect.pivot=new Vector2(0,1);rect.anchoredPosition=new Vector2(12,-125);rect.sizeDelta=new Vector2(405,605);
            text=label.GetComponent<Text>();text.font=Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");text.fontSize=16;text.color=Color.white;text.horizontalOverflow=HorizontalWrapMode.Wrap;text.verticalOverflow=VerticalWrapMode.Truncate;text.raycastTarget=false;
            text.text="Private diagnostic127\nManual status only.\nThe availability button performs one SDK availability request.\nNo purchase, VK login or account action is invoked.";
            expanded.SetActive(false);
        }
        static RectTransform Panel(Transform parent,string name,Vector2 size,Vector2 position){
            var owner=new GameObject(name,typeof(RectTransform),typeof(Image));owner.transform.SetParent(parent,false);var rect=(RectTransform)owner.transform;
            rect.anchorMin=rect.anchorMax=rect.pivot=new Vector2(1,1);rect.anchoredPosition=position;rect.sizeDelta=size;
            var background=owner.GetComponent<Image>();background.color=new Color(.04f,.06f,.10f,.95f);background.raycastTarget=true;return rect;
        }
        static void Button(Transform parent,string label,Vector2 position,UnityEngine.Events.UnityAction action){
            var owner=new GameObject(label,typeof(RectTransform),typeof(Image),typeof(UnityEngine.UI.Button));owner.transform.SetParent(parent,false);
            var rect=(RectTransform)owner.transform;rect.anchorMin=rect.anchorMax=rect.pivot=new Vector2(1,1);rect.anchoredPosition=position;rect.sizeDelta=new Vector2(430,52);
            owner.GetComponent<Image>().color=new Color(.16f,.24f,.32f,1);var button=owner.GetComponent<UnityEngine.UI.Button>();button.onClick.AddListener(action);
            var caption=new GameObject("Label",typeof(RectTransform),typeof(Text));caption.transform.SetParent(owner.transform,false);var cr=(RectTransform)caption.transform;cr.anchorMin=Vector2.zero;cr.anchorMax=Vector2.one;cr.offsetMin=cr.offsetMax=Vector2.zero;
            var text=caption.GetComponent<Text>();text.font=Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");text.fontSize=20;text.color=Color.white;text.alignment=TextAnchor.MiddleCenter;text.text=label;text.raycastTarget=false;
        }
        void Update(){for(int n=0;n<8&&callbacks.TryDequeue(out Action callback);n++)callback();}
        void LocalRead(){
            reads=Math.Min(reads+1,999);state.readCount=reads;state.observation="LOCAL_STATUS_READ";
            var session=FindObjectOfType<ServerGameSession>(true);state.serverSelected=session;state.serverReady=session&&session.Ready;state.serverBusy=session&&session.Busy;
            state.accountBlocked=session&&session.AccountBlocked;state.serverHasPending=session&&session.HasPending;state.activeAttempt=session&&session.HasActiveServerAttempt;state.serverLastError=SafeName(session?session.LastError:null);
            var host=FindObjectOfType<ShopCheckoutHost86>(true);state.checkoutPresent=host;state.checkoutConfigured=host&&host.Configured;state.checkoutBusy=host&&host.Busy;state.checkoutPending=host&&host.Pending;state.checkoutError=SafeName(host?host.Error:null);
            state.firstOfferPriced=host&&!string.IsNullOrEmpty(host.Price("hotr_coins_1000"));state.checkoutFlowKnown=false;state.checkoutFlowBound=false;
            if(host){var field=typeof(ShopCheckoutHost86).GetField("flow",BindingFlags.NonPublic|BindingFlags.Instance);if(field!=null){state.checkoutFlowKnown=true;state.checkoutFlowBound=field.GetValue(host)!=null;}}
            state.accountModalVisible=state.accountUiBusy=state.vkProviderPresent=state.vkProviderAvailable=state.vkProviderBusy=state.vkStatePresent=state.vkPending=state.vkBeginPresent=state.vkBeginActive=state.vkBeginInteractable=false;state.vkPhase="NONE";
            var modal=FindObjectOfType<AccountModal>(true);state.accountModalPresent=modal;if(modal)modal.FillPrivateDiagnostic127(state);
        }
        void ReadStatus(){try{LocalRead();Persist();}catch(Exception failure){state.observation="LOCAL_READ_EXCEPTION";state.exceptionType=SafeException(failure);Persist();}}
        void QueryAvailability(){
            if(querying||requests>=20)return;
            try{LocalRead();}catch(Exception failure){state.observation="LOCAL_READ_EXCEPTION";state.exceptionType=SafeException(failure);Persist();return;}
            if(Application.isEditor||Application.platform!=RuntimePlatform.Android||Application.identifier!=Package||!Debug.isDebugBuild){state.sdkResult="UNSUPPORTED_PRIVATE_CONTEXT";Persist();return;}
            querying=true;state.availabilityBusy=true;state.sdkResult="REQUESTED";state.sdkCallbackReceived=false;state.sdkAvailable=false;state.sdkCause=state.sdkError=state.exceptionType="NONE";state.availabilityRequests=++requests;int generation=++queryGeneration;Persist();
#if UNITY_ANDROID && HOTR_RUSTORE_PAY
            try{
                RuStore.PayClient.RuStorePayClient.Instance.GetPurchaseAvailability(
                    error=>callbacks.Enqueue(()=>{if(!this||generation!=queryGeneration)return;querying=false;state.availabilityBusy=false;state.sdkCallbackReceived=true;state.sdkResult="FAILURE";state.sdkError=SafeName(error?.name);Persist();}),
                    result=>callbacks.Enqueue(()=>{if(!this||generation!=queryGeneration)return;querying=false;state.availabilityBusy=false;state.sdkCallbackReceived=true;state.sdkResult=result==null?"NULL_RESULT":"SUCCESS";state.sdkAvailable=result!=null&&result.isAvailable;state.sdkCause=SafeName(result?.cause?.name);Persist();}));
            }catch(Exception failure){querying=false;state.availabilityBusy=false;state.sdkResult="EXCEPTION";state.exceptionType=SafeException(failure);Persist();}
#else
            querying=false;state.availabilityBusy=false;state.sdkResult="SDK_NOT_COMPILED";Persist();
#endif
        }
        void Persist(){
            try{state.writeSucceeded=true;string json=Serialize(state);string path=Path.Combine(Application.persistentDataPath,FileName);using(var output=new FileStream(path,FileMode.Create,FileAccess.Write,FileShare.Read))using(var writer=new StreamWriter(output,new UTF8Encoding(false))){writer.Write(json);writer.Flush();output.Flush(true);}}
            catch(Exception failure){state.writeSucceeded=false;state.exceptionType=SafeException(failure);}Publish();
        }
        void Publish(){
            if(!text)return;Serialize(state);
            text.text="Private127 read="+state.readCount+" requests="+state.availabilityRequests+"\n"+
                "Server selected="+state.serverSelected+" ready="+state.serverReady+" busy="+state.serverBusy+"\n"+
                "Blocked="+state.accountBlocked+" pending="+state.serverHasPending+" attempt="+state.activeAttempt+"\n"+
                "Server error="+state.serverLastError+"\n"+
                "Checkout present="+state.checkoutPresent+" configured="+state.checkoutConfigured+"\n"+
                "Flow known="+state.checkoutFlowKnown+" bound="+state.checkoutFlowBound+" priced="+state.firstOfferPriced+"\n"+
                "Checkout busy="+state.checkoutBusy+" pending="+state.checkoutPending+"\n"+
                "Checkout error="+state.checkoutError+"\n"+
                "Account visible="+state.accountModalVisible+" UIbusy="+state.accountUiBusy+"\n"+
                "VK provider="+state.vkProviderPresent+" available="+state.vkProviderAvailable+" busy="+state.vkProviderBusy+"\n"+
                "VK state="+state.vkStatePresent+" phase="+state.vkPhase+" pending="+state.vkPending+"\n"+
                "VK begin present="+state.vkBeginPresent+" active="+state.vkBeginActive+" interactable="+state.vkBeginInteractable+"\n"+
                "SDK compiled="+state.sdkCompiled+" busy="+state.availabilityBusy+" callback="+state.sdkCallbackReceived+"\n"+
                "SDK result="+state.sdkResult+" available="+state.sdkAvailable+"\n"+
                "SDK cause="+state.sdkCause+"\nSDK error="+state.sdkError+"\n"+
                "Exception="+state.exceptionType+" write="+state.writeSucceeded;
        }
    }
}

namespace HeartOfTheRain.App.AccountDesign {
    // Reading the actual modal's existing service avoids a second provider
    // service/cache and never calls Refresh/Begin/Complete or copies IDs.
    public sealed partial class AccountModal {
        public void FillPrivateDiagnostic127(HeartOfTheRain.Verification.Diagnostics127.PaymentDiagnosticSnapshot127 value){
            value.accountModalVisible=IsVisible;value.accountUiBusy=busy;
            var providers=Providers;value.vkProviderPresent=providers!=null;value.vkProviderBusy=providers!=null&&providers.ProviderBusy;
            var provider=providers?.VkStatus;value.vkProviderAvailable=provider!=null&&provider.available;
            var current=VkSigninService?.VkSignin;value.vkStatePresent=current!=null;value.vkPhase=HeartOfTheRain.Verification.Diagnostics127.PaymentDiagnostics127.SafePhase(current?.phase);value.vkPending=current!=null&&current.Pending;
            value.vkBeginPresent=value.vkBeginActive=value.vkBeginInteractable=false;
            UnityEngine.UI.Button first=null,currentButton=null;
            foreach(var button in GetComponentsInChildren<UnityEngine.UI.Button>(true))if(button.gameObject.name=="VK registration or sign in"){
                if(!first)first=button;
                if(button.gameObject.activeInHierarchy){currentButton=button;break;}
            }
            var selected=currentButton?currentButton:first;
            if(selected){value.vkBeginPresent=true;value.vkBeginActive=selected.gameObject.activeInHierarchy;value.vkBeginInteractable=selected.interactable&&selected.IsInteractable();}
        }
    }
}
#endif

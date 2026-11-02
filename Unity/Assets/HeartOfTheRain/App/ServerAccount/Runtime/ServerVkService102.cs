using System;
using UnityEngine;
using HeartOfTheRain.App.OnlineIdentity;

namespace HeartOfTheRain.App.ServerAccount {
    public interface IProviderSignin102 {
        VkSigninStatus102 VkSignin{get;}
        void BeginVkSignin(Action<bool,string> done);
        void RefreshVkSignin(Action<bool,string> done);
        void CancelVkSignin(Action<bool,string> done);
        void CompleteVkSignin(string expectedTarget,bool confirmed,Action<bool,string> done);
    }
    public sealed partial class ServerAccountService83:IProviderSignin102 {
#if UNITY_EDITOR
        // Native verification can observe browser intent without contacting VK.
        public Action<string> VerificationBrowserOpened;
#endif
        public VkSigninStatus102 VkSignin=>disposed||!gateway?null:gateway.AccountVkStatus;
        void VkResult(Action<bool,string> done,bool ok,string why){if(!disposed)Notify();done?.Invoke(!disposed&&ok,disposed?"AccountServiceClosed":why);}
        public void BeginVkSignin(Action<bool,string> done){
            if(disposed||!gateway||VkStatus==null||!VkStatus.available){done?.Invoke(false,"ProviderUnavailable");return;}
            gateway.AccountVkBegin((ok,why)=>{
                if(!disposed&&ok&&gateway)OpenVkAuthorization();
                VkResult(done,ok,why);
            });
        }
        void OpenVkAuthorization(){
            var state=gateway.AccountVkStatus;if(state==null||state.phase!="Pending"||!ProviderIdentityClient89.SafeAuthorizeUrl(state.authorizeUrl))return;
#if UNITY_EDITOR
            if(VerificationBrowserOpened!=null)VerificationBrowserOpened(state.authorizeUrl);
            else
#endif
            Application.OpenURL(state.authorizeUrl);
        }
        public void RefreshVkSignin(Action<bool,string> done){if(disposed||!gateway){done?.Invoke(false,"AccountServiceClosed");return;}gateway.AccountVkRefresh((ok,why)=>{if(!disposed&&ok&&gateway)OpenVkAuthorization();VkResult(done,ok,why);});}
        public void CancelVkSignin(Action<bool,string> done){if(disposed||!gateway){done?.Invoke(false,"AccountServiceClosed");return;}gateway.AccountVkCancel((ok,why)=>VkResult(done,ok,why));}
        public void CompleteVkSignin(string expectedTarget,bool confirmed,Action<bool,string> done){if(disposed||!gateway){done?.Invoke(false,"AccountServiceClosed");return;}gateway.AccountVkComplete(expectedTarget,confirmed,(ok,why)=>VkResult(done,ok,why));}
    }
}

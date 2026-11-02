using System;
using UnityEngine;
using HeartOfTheRain.App.OnlineIdentity;

namespace HeartOfTheRain.App.ServerAccount {
    public interface IProviderAccount89 {
        ProviderStatus89 VkStatus{get;}
        bool ProviderBusy{get;}
        void RefreshProviders();
        void BeginVk(Action<bool,string> done);
        void CancelVk(Action<bool,string> done);
    }
    public sealed partial class ServerAccountService83:IProviderAccount89 {
        ProviderIdentityClient89 providerClient;ProviderStatus89 vkStatus;bool providerBusy;string providerOwner="";
        public ProviderStatus89 VkStatus=>disposed||!gateway||providerOwner!=gateway.PlayerId?null:vkStatus?.Copy();
        public bool ProviderBusy=>providerBusy;
        void DisposeProvider(){providerClient?.Dispose();providerClient=null;providerBusy=false;vkStatus=null;providerOwner="";}
        void ProviderRequest(Action<ProviderIdentityClient89,Action<ProviderStatus89,string>> operation,Action<bool,string> done){
            if(disposed||!gateway||!gateway.Ready||gateway.Busy||providerBusy){done?.Invoke(false,"ProviderUnavailable");return;}
            providerBusy=true;string player=gateway.PlayerId;
            gateway.WithAuthenticatedSession((context,error)=>{
                if(disposed||!gateway||context==null||gateway.PlayerId!=player){providerBusy=false;if(!disposed)Notify();done?.Invoke(false,"ProviderSessionChanged");return;}
                providerClient?.Dispose();providerClient=new ProviderIdentityClient89(context.Origin,context.PlayerId,()=>context.CurrentAccess,r=>gateway.StartCoroutine(r),context.AllowDevelopmentLoopback);
                operation(providerClient,(value,why)=>{
                    providerBusy=false;
                    if(disposed||!gateway||gateway.PlayerId!=player||string.IsNullOrEmpty(context.CurrentAccess)){vkStatus=null;if(!disposed)Notify();done?.Invoke(false,"ProviderSessionChanged");return;}
                    if(value!=null){vkStatus=value;providerOwner=player;}Notify();done?.Invoke(value!=null,why);
                });
            });
        }
        public void RefreshProviders(){
            if(disposed||!gateway)return;if(providerOwner!=gateway.PlayerId){vkStatus=null;providerOwner=gateway.PlayerId;}
            ProviderRequest((client,done)=>client.Status(done),(ok,why)=>{if(ok&&!disposed&&gateway)gateway.AccountVkRefresh((finished,error)=>{if(!disposed)Notify();});});
        }
        public void BeginVk(Action<bool,string> done){
            if(disposed||!gateway||providerOwner!=gateway.PlayerId||vkStatus==null||!vkStatus.available||vkStatus.linked){done?.Invoke(false,"ProviderUnavailable");return;}
            if(vkStatus.phase=="Pending"&&ProviderIdentityClient89.SafeAuthorizeUrl(vkStatus.authorizeUrl)){Application.OpenURL(vkStatus.authorizeUrl);done?.Invoke(true,null);return;}
            if(vkStatus.Pending){done?.Invoke(false,"ProviderPending");return;}
            if(gateway.AccountTransitionBlocker()!=null){done?.Invoke(false,"AccountPendingActions");return;}
            ProviderRequest((client,complete)=>client.Begin(Guid.NewGuid().ToString("N"),complete),(ok,why)=>{
                if(ok&&vkStatus!=null&&vkStatus.phase=="Pending"&&ProviderIdentityClient89.SafeAuthorizeUrl(vkStatus.authorizeUrl))Application.OpenURL(vkStatus.authorizeUrl);
                done?.Invoke(ok,why);
            });
        }
        public void CancelVk(Action<bool,string> done){if(disposed||!gateway||providerOwner!=gateway.PlayerId||vkStatus==null||!vkStatus.Pending){done?.Invoke(false,"ProviderUnavailable");return;}string flow=vkStatus.flowId;ProviderRequest((client,complete)=>client.Cancel(flow,complete),done);}
    }
}

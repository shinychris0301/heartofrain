using System;
using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.ServerGameplay;

namespace HeartOfTheRain.App.ServerRewards {
    // Exists only beside an explicitly selected server session. No automatic
    // server choice, player migration, inventory mutation or financial fallback.
    [DisallowMultipleComponent] public sealed class ServerRewardsSession:MonoBehaviour {
        ServerGameSession session;public ServerRewardsCoordinator Coordinator{get;private set;}
        BackendOffer homeOffer,seenOffer;ServerWellworks homeWorks,seenWorks;ServerCup homeCup,seenCup;
        string homeOrigin,homePlayer;long homeGeneration=-1,homeDay=-1;int homeCompleted=-1;
        float nextHomeRead,nextHomeRenew,homeRetry=5;bool homeReading,homeRenewing,homeReadFailed;
        public bool HomeMetadataBusy=>homeReading||homeRenewing;
        public bool HomeAccessRenewing=>homeRenewing;
        public int HomeAccessRenewals{get;private set;}
        public int HomeMetadataBatches{get;private set;}
        public bool HomeMetadataReady=>HomeOwnerCurrent&&homeOffer!=null&&homeWorks!=null&&homeCup!=null;
        bool HomeOwnerCurrent=>session&&session.Ready&&homeOrigin==session.Origin&&homePlayer==session.PlayerId&&homeGeneration==session.SessionGeneration;
        // Unavailable means a read failed. Until the first answer the badge only shows it is waiting.
        string HomeMissingBadge=>homeReadFailed||!session||!session.Ready&&!string.IsNullOrEmpty(session.LastError)?"Unavailable":"\u2026";
        public string HomeDailyBadge=>!HomeOwnerCurrent||homeOffer==null?HomeMissingBadge:homeOffer.claimed?DailyGiftText.T("Tomorrow"):"Ready";
        public string HomeWellworksBadge{get{if(!HomeOwnerCurrent||homeWorks==null)return HomeMissingBadge;if(homeWorks.milestones.Any(m=>m.eligible&&!m.claimed))return "Ready";var next=homeWorks.milestones.FirstOrDefault(m=>!m.claimed);return next==null?"\u2713":homeWorks.completed+"/"+next.level;}}
        public string HomeCupBadge{get{if(!HomeOwnerCurrent||homeCup==null)return HomeMissingBadge;if(homeCup.state=="Active"){long left=Math.Max(0,homeCup.run.endsAt-session.ServerTimeNow);return (left/3600).ToString("00")+":"+(left%3600/60).ToString("00");}if(homeCup.state=="Finished")return "Ready";if(homeCup.state=="Locked")return homeCup.completed+"/"+homeCup.rules.unlockClears;return homeCup.canJoin?"Ready":"\u2713";}}
        public static ServerRewardsSession Select(ServerGameSession session){if(!session)return null;var result=session.GetComponent<ServerRewardsSession>();if(!result){result=session.gameObject.AddComponent<ServerRewardsSession>();result.session=session;result.Coordinator=new ServerRewardsCoordinator(Path.Combine(Application.persistentDataPath,"ServerReview","Rewards"),result.Authorize,result.RefreshWallet,value=>RewardPresentationJournal.ForPlayer(value.Origin,value.PlayerId));session.IdentityChanged+=result.Invalidate;}return result;}
        void Invalidate(){Coordinator?.Invalidate();homeOffer=seenOffer=null;homeWorks=seenWorks=null;homeCup=seenCup=null;homeOrigin=homePlayer=null;homeGeneration=homeDay=-1;homeCompleted=-1;nextHomeRead=0;homeReadFailed=false;homeRetry=5;}
        void OnDestroy(){if(session)session.IdentityChanged-=Invalidate;Coordinator?.Invalidate();}
        // Called only by idle Home. This path never reconciles a claim, refreshes
        // the wallet, creates an intent, or invokes a local reward service.
        public void ObserveHomeScope(int completed,long day){
            if(!session||!session.Ready||Coordinator==null)return;
            if(!HomeOwnerCurrent){homeOrigin=session.Origin;homePlayer=session.PlayerId;homeGeneration=session.SessionGeneration;homeDay=-1;homeCompleted=-1;homeOffer=seenOffer=null;homeWorks=seenWorks=null;homeCup=seenCup=null;nextHomeRead=0;homeReadFailed=false;homeRetry=5;}
            if(homeDay!=day){homeDay=day;homeOffer=null;nextHomeRead=0;}
            // New progress refreshes these now. The last values stay on the badges meanwhile,
            // so a win never shows a false Unavailable.
            if(homeCompleted!=completed){homeCompleted=completed;nextHomeRead=0;}
        }
        public void PollHomeMetadata(int completed,long day){
            ObserveHomeScope(completed,day);if(!HomeOwnerCurrent)return;
            // Successful ordinary pages already have authenticated metadata.
            // Reuse only new references for this owner and current progression.
            if(!Coordinator.Busy&&Coordinator.PlayerId==homePlayer){
                if(Coordinator.Offer!=null&&!ReferenceEquals(seenOffer,Coordinator.Offer)&&Coordinator.Offer.day==day){seenOffer=homeOffer=Coordinator.Offer;}
                if(Coordinator.Wellworks!=null&&!ReferenceEquals(seenWorks,Coordinator.Wellworks)&&Coordinator.Wellworks.completed==completed){seenWorks=homeWorks=Coordinator.Wellworks;}
                if(Coordinator.Cup!=null&&!ReferenceEquals(seenCup,Coordinator.Cup)&&Coordinator.Cup.completed==completed){seenCup=homeCup=Coordinator.Cup;}
            }
            if(homeReading||homeRenewing||Coordinator.Busy||session.Busy)return;
            ServerAuthorizedContext context;if(!session.TryGetReadContext(out context)){if(Time.unscaledTime<nextHomeRenew)return;homeRenewing=true;nextHomeRenew=Time.unscaledTime+30;StartCoroutine(RenewHomeAccess(completed,day));return;}
            if(Time.unscaledTime<nextHomeRead)return;
            homeReading=true;nextHomeRead=Time.unscaledTime+60;StartCoroutine(ReadHomeMetadata(context,completed,day));
        }
        IEnumerator RenewHomeAccess(int completed,long day){
            string origin=session.Origin,player=session.PlayerId;bool done=false;ServerAuthorizedContext context=null;HomeAccessRenewals++;
            try{
                // Renewal is reserved for an idle Home with expired access.
                // Normal metadata reads do not publish/refresh the wallet.
                session.WithAuthenticatedSession((value,error)=>{context=value;done=true;});
                while(!done&&session)yield return null;
                if(session&&context!=null&&context.Origin==origin&&context.PlayerId==player&&!string.IsNullOrEmpty(context.CurrentAccess)){
                    ObserveHomeScope(completed,day);nextHomeRead=Time.unscaledTime;nextHomeRenew=Time.unscaledTime+10;
                }else{nextHomeRenew=Time.unscaledTime+30;homeReadFailed=true;}
            }finally{homeRenewing=false;}
        }
        bool CurrentHome(ServerAuthorizedContext context,int completed,long day)=>HomeOwnerCurrent&&homeGeneration==context.Generation&&homeCompleted==completed&&homeDay==day&&!string.IsNullOrEmpty(context.CurrentAccess);
        IEnumerator ReadHomeMetadata(ServerAuthorizedContext context,int completed,long day){
            var offerBefore=Coordinator.Offer;var worksBefore=Coordinator.Wellworks;var cupBefore=Coordinator.Cup;
            bool complete=false;HomeMetadataBatches++;
            Coroutine offerRead=null,worksRead=null,cupRead=null;
            bool offerDone=false,worksDone=false,cupDone=false;
            try{
                var client=new ServerRewardClient(new RewardAccess(context.Origin,context.PlayerId,context.Generation,()=>context.CurrentAccess,context.AllowDevelopmentLoopback));
                RewardReply<BackendOffer> offer=null;RewardReply<ServerWellworks> works=null;RewardReply<ServerCup> cup=null;
                // These are independent read-only snapshots. Waiting for each HTTP response
                // in series made the three Home badges inherit the sum of network latencies.
                offerRead=StartCoroutine(client.Offer(r=>{offer=r;offerDone=true;}));
                worksRead=StartCoroutine(client.Wellworks(r=>{works=r;worksDone=true;}));
                cupRead=StartCoroutine(client.Cup(r=>{cup=r;cupDone=true;}));
                while(!offerDone||!worksDone||!cupDone){if(!CurrentHome(context,completed,day)||Coordinator.Busy)yield break;yield return null;}
                if(!CurrentHome(context,completed,day)||Coordinator.Busy)yield break;
                if(ReferenceEquals(offerBefore,Coordinator.Offer))homeOffer=offer!=null&&offer.Ok&&offer.value.day==day?offer.value:null;
                if(ReferenceEquals(worksBefore,Coordinator.Wellworks))homeWorks=works!=null&&works.Ok&&works.value.completed==completed?works.value:null;
                if(ReferenceEquals(cupBefore,Coordinator.Cup))homeCup=cup!=null&&cup.Ok&&cup.value.completed==completed?cup.value:null;
                complete=offer!=null&&offer.Ok&&offer.value.day==day&&works!=null&&works.Ok&&works.value.completed==completed&&cup!=null&&cup.Ok&&cup.value.completed==completed;
                homeReadFailed=offer==null||!offer.Ok||works==null||!works.Ok||cup==null||!cup.Ok;
            }finally{
                if(offerRead!=null&&!offerDone)StopCoroutine(offerRead);
                if(worksRead!=null&&!worksDone)StopCoroutine(worksRead);
                if(cupRead!=null&&!cupDone)StopCoroutine(cupRead);
                homeReading=false;if(CurrentHome(context,completed,day)){nextHomeRead=Time.unscaledTime+(complete?60:homeRetry);homeRetry=complete?5:Mathf.Min(homeRetry*2,30);}
            }
        }
        IEnumerator Authorize(Action<RewardAccess,string> done){while(homeRenewing&&session)yield return null;ServerAuthorizedContext context=null;string why=null;bool finished=false;if(session)session.WithAuthenticatedSession((value,error)=>{context=value;why=error;finished=true;});while(!finished&&session)yield return null;if(!session||context==null){done(null,why??"RewardSessionUnavailable");yield break;}done(new RewardAccess(context.Origin,context.PlayerId,context.Generation,()=>context.CurrentAccess,context.AllowDevelopmentLoopback),null);}
        IEnumerator RefreshWallet(Action<bool,string> done){bool finished=false;bool success=false;string why=null;session.Refresh((ok,error)=>{success=ok;why=error;finished=true;});while(!finished&&session)yield return null;done(session&&success,why??(success?null:"RewardProjectionUnavailable"));}
    }
}

namespace HeartOfTheRain.App.ServerGameplay {
    public sealed partial class ServerGameSession {
        // Existing managed access only: readonly metadata does not renew the
        // session, publish a wallet, or occupy the financial-operation gate.
        public bool TryGetReadContext(out ServerAuthorizedContext context){
            context=null;if(!Ready||Busy||identity==null||!identity.HasAccess||identity.RenewalDue)return false;
            long ownerGeneration=generation;string player=PlayerId;
            context=new ServerAuthorizedContext(config.origin,player,ownerGeneration,config.allowDevelopmentLoopback,()=>!closed&&!accountBlocked&&generation==ownerGeneration&&PlayerId==player&&identity!=null&&identity.HasAccess?identity.AccessToken:null,config.productionEnabled);return true;
        }
    }
}

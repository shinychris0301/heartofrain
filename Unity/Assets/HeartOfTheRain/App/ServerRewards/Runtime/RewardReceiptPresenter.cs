using System;
using System.Collections;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.ServerGameplay;

namespace HeartOfTheRain.App.ServerRewards {
    // Idle Home drains committed notifications. Neither acknowledgement nor
    // cancellation calls ProfileService.Change or any grant/claim endpoint.
    [DisallowMultipleComponent] public sealed class RewardReceiptPresenter:MonoBehaviour {
        HomePage home;PlayerProfileHost profile;PreLevelAssets assets;
        string origin,player;long generation=-1;float nextRead,nextRecovery;
        RewardPresentationJournal journal;bool recovering;
        public string LastError{get;private set;}
        public void Configure(HomePage home,PlayerProfileHost profile,PreLevelAssets assets){this.home=home;this.profile=profile;this.assets=assets;}
        bool Current(ServerGameSession session,long captured)=>profile&&profile.ServerSession==session&&session&&session.Ready&&session.Origin==origin&&session.PlayerId==player&&session.SessionGeneration==captured;
        void OnApplicationFocus(bool value){if(value){nextRead=0;nextRecovery=0;}}
        void OnApplicationPause(bool value){if(!value){nextRead=0;nextRecovery=0;}}
        void Update(){
            if(!home||!profile||profile.LocalEconomyMode||!profile.Ready||!home.RewardPresentationForeground||!home.PresentationInteractable||home.EventsOpen||home.RewardRevealPlaying)return;
            var flow=home.GetComponent<HomeLevelFlow>();var session=profile.ServerSession;
            if(!flow||!flow.CanOpenAppSettings||!session||!session.Ready||session.Busy||recovering)return;
            if(origin!=session.Origin||player!=session.PlayerId||generation!=session.SessionGeneration){origin=session.Origin;player=session.PlayerId;generation=session.SessionGeneration;journal=null;nextRead=nextRecovery=0;}
            var rewards=ServerRewardsSession.Select(session).Coordinator;if(rewards.Busy)return;
            // Almost nothing is ever pending: only a saved intent is worth a wallet read and the transaction gate.
            if(Time.unscaledTime>=nextRecovery){nextRecovery=Time.unscaledTime+30;if(rewards.LocalPending(origin,player)){recovering=true;StartCoroutine(Recover(rewards));return;}}
            if(Time.unscaledTime<nextRead)return;nextRead=Time.unscaledTime+1;
            RewardPresentation receipt=null;
            try{if(journal==null)journal=RewardPresentationJournal.ForPlayer(origin,player);receipt=journal.Peek();LastError=null;}
            catch(Exception){LastError="RewardPresentationUnavailable";nextRead=Time.unscaledTime+30;return;}
            if(receipt==null)return;var capturedJournal=journal;long captured=generation;
            home.PlayCommittedReward(receipt.grant,assets,()=>{
                if(!Current(session,captured)||!home.RewardPresentationForeground)return;
                try{capturedJournal.MarkPresented(receipt.channel,receipt.id);LastError=null;}
                catch(Exception){LastError="RewardPresentationAcknowledgeUnavailable";nextRead=Time.unscaledTime+30;}
            });
        }
        IEnumerator Recover(ServerRewardsCoordinator rewards){
            try{RewardCompletion result=null;yield return rewards.RecoverPending(value=>result=value);if(result==null||!result.ok)LastError=result?.error??"RewardRecoveryUnavailable";else LastError=null;}
            finally{recovering=false;}
        }
    }
}

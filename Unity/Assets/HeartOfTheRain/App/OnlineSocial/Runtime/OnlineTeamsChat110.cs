using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.TeamsSocial;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace HeartOfTheRain.App.OnlineSocial
{
    public sealed partial class OnlineTeamsPage82
    {
        bool giftsOpen110,mail110,lifeRefreshing110,lifeWalletRefresh110,foregroundMessageWrite110;
        long ownedAfter110,lastLifeSecond110,messageAcknowledgement110;double lifePollAt110,lifeWalletRetryAt110;float lastKeyboardInset110;
        string lifeError110="",lifeReceipt110="",lifeWrite110="",lifeWriteRequest110="",lifeFeedback110="";
        readonly HashSet<string> feedbackSeen110=new HashSet<string>(StringComparer.Ordinal);
        TeamsHelpFeedback110 feedback110;
        bool Chat110 => tab==0&&!giftsOpen110&&!inspectDetails&&!accessCreate&&session?.Snapshot<SocialTeam82>(SocialPane82.TeamInfo)?.isMember==true;
        bool OfflineChat110=>session?.Status(SocialPane82.TeamChat).state==SocialViewState82.Offline;
        bool Keyboard110 {
            get {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                if(verificationView!=null)return verificationView.composing110&&TouchScreenKeyboard110;
#endif
                return modal=="compose110"&&TouchScreenKeyboard110;
            }
        }
        bool TouchScreenKeyboard110 {
            get {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                if(verificationKeyboard110>=0)return verificationKeyboard110>0;
#endif
                return TouchScreenKeyboard.visible;
            }
        }
        float KeyboardInset110 {
            get {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                if(verificationKeyboard110>=0)return verificationKeyboard110;
#endif
                if(!TouchScreenKeyboard.visible)return 0;return TouchScreenKeyboard.area.height>0?TouchScreenKeyboard.area.height:ScreenSize().y*.35f;
            }
        }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        float verificationKeyboard110=-1;bool? verificationReduced110;
        public TeamsHelpFeedback110 VerificationFeedback110=>feedback110;
        public bool VerificationWalletRefresh110=>lifeWalletRefresh110;
        public void VerificationKeyboard110(float physicalInset){verificationKeyboard110=Math.Max(0,physicalInset);if(IsVisible)Reflow(ScrollPosition,true);}
        public void VerificationReducedMotion110(bool value){verificationReduced110=value;}
        public void VerificationAdvance110(float seconds){if(feedback110)feedback110.Advance(seconds);}
#endif
        bool Reduced110 {
            get {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                if(verificationReduced110.HasValue)return verificationReduced110.Value;
#endif
                return home&&home.State.reduceMotion;
            }
        }
        void ResetChatOwner110()
        {
            ResetMail111();giftsOpen110=mail110=lifeRefreshing110=lifeWalletRefresh110=foregroundMessageWrite110=false;ownedAfter110=0;lifePollAt110=0;lifeError110=lifeReceipt110=lifeWrite110=lifeWriteRequest110=lifeFeedback110=submittedMessage110="";feedbackSeen110.Clear();CancelFeedback110();
        }
        void CancelFeedback110(){if(feedback110){feedback110.Cancel();if(Application.isPlaying)Destroy(feedback110.gameObject);else DestroyImmediate(feedback110.gameObject);feedback110=null;}}
        void ObserveLifeReceipt110()
        {
            var receipt=session?.LastLifeReceipt110;if(receipt==null||receipt.receiptId==lifeReceipt110)return;
            lifeReceipt110=receipt.receiptId;lifeError110="";lifeWrite110=lifeWriteRequest110="";
            if(receipt.operation=="life.claim")lifeWalletRefresh110=true;
            if((receipt.operation!="life.claim"||receipt.creditedLives>0)&&feedbackSeen110.Add(receipt.receiptId))lifeFeedback110=receipt.receiptId;
            lifePollAt110=0;
        }
        void PumpChat110()
        {
            ObserveLifeReceipt110();
            RestorePendingMessage110();
            PumpClaimWallet110();
            if(ownedMailOpen111){PumpOwnedMail111();return;}
            if(mail110){PumpMail111();return;}
            long second=session?.LifeServerNow110??0;float inset=Keyboard110?KeyboardInset110:0;
            // Rebuilding an active InputField replaces Android's live input
            // connection. In extract-mode keyboards that reopens the IME when
            // the player presses OK or Back. Keep the composer stable until
            // the keyboard has actually closed, then restore the full layout.
            if(Math.Abs(inset-lastKeyboardInset110)>.1f){lastKeyboardInset110=inset;if(!Keyboard110)Reflow(ScrollPosition,true);}
            if(second!=lastLifeSecond110){RectTransform label;var lives=session?.Snapshot<SocialLifeRequests110>(SocialPane82.TeamLives110);long wait=(lives?.nextRequestAt??0)-second,previous=(lives?.nextRequestAt??0)-lastLifeSecond110;lastLifeSecond110=second;if(nodes.TryGetValue("online-request-lives-label",out label)&&label.GetComponent<Text>()){label.GetComponent<Text>().text=session?.PendingCommand?.operation=="life.request"?TeamsSocialText110.T("request_pending"):wait>0?TeamsSocialText110.T("request_again")+"\n"+TeamsSocialLayout110.Countdown(wait):TeamsSocialText110.T("request_lives");if(previous>0&&wait<=0)lifePollAt110=0;}}
            // A refresh rebuilds the composer input. Keep it stable while the
            // player is writing or deciding in a modal.
            if(modal.Length>0||session==null||session.Busy||refreshing||lifeRefreshing110||session.PendingCommand!=null||AuthorizationNow<lifePollAt110)return;
            if(!Chat110&&!giftsOpen110)return;
            lifePollAt110=AuthorizationNow+10;Dispatch(RefreshLife110(session,loadGeneration));
        }
        void PumpClaimWallet110()
        {
            // The canvas can close while a durable social write completes.
            // Refresh its owner's wallet even then; visibility never decides
            // whether a committed reward reaches the managed projection.
            if(closed)return;
            if(lifeWalletRefresh110&&AuthorizationNow>=lifeWalletRetryAt110&&gateway&&gateway.Ready&&!gateway.Busy){
                var owner=gateway;string player=owner.PlayerId;long epoch=owner.PlayerOwnershipEpoch;lifeWalletRefresh110=false;
                owner.Refresh((ok,why)=>{if(!this||closed||owner!=gateway||!owner.OwnsPlayer(epoch,owner.Origin,player))return;if(!ok){lifeWalletRefresh110=true;lifeWalletRetryAt110=AuthorizationNow+10;lifeError110=TeamsSocialText110.T("claim_error");}if(IsVisible){Reflow(ScrollPosition,true);if(ok)StartMailFeedback111();}});
            }
        }
        IEnumerator RefreshLife110(SocialPageSession82 owner,int token)
        {
            lifeRefreshing110=true;
            try{
                if(Chat110&&owner.RefreshTeamLives110())while(owner.Busy)yield return null;
                if(closed||!IsVisible||session!=owner||token!=loadGeneration)yield break;
                if(Chat110&&ServiceUnreachable(owner,SocialPane82.TeamLives110))yield break;
                if(owner.RefreshOwnedLives110(ownedAfter110))while(owner.Busy)yield return null;
                if(closed||!IsVisible||session!=owner||token!=loadGeneration)yield break;
                if(ServiceUnreachable(owner,SocialPane82.OwnedLives110))yield break;
                if(Chat110&&!mail110&&owner.RefreshTeamMail111())while(owner.Busy)yield return null;
                if(closed||!IsVisible||session!=owner||token!=loadGeneration)yield break;
                if(Chat110&&!mail110&&scroll&&scroll.verticalNormalizedPosition>.02f&&owner.ProbeTeamMessages110())while(owner.Busy)yield return null;
                if(closed||!IsVisible||session!=owner||token!=loadGeneration)yield break;
                UpdateLifeReadNotice110();
            }finally{if(session==owner&&token==loadGeneration){lifeRefreshing110=false;lifePollAt110=AuthorizationNow+30;}if(!closed&&IsVisible&&session==owner&&token==loadGeneration){Reflow(ScrollPosition,true);StartFeedback110();}}
        }
        void UpdateLifeReadNotice110(){if(session==null)return;var target=session.Status(giftsOpen110?SocialPane82.OwnedLives110:SocialPane82.TeamLives110);if(target.state==SocialViewState82.Ready)lifeError110="";else if(target.state!=SocialViewState82.Loading&&target.state!=SocialViewState82.NotLoaded)lifeError110=TeamsSocialText110.T("service_unavailable");}
        void FillChatView110(OnlineTeamsView82 value)
        {
            double phase=AuthorizationNow;FillMailView111(value);NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsChatViewMail,(int)Math.Round((AuthorizationNow-phase)*1000));phase=AuthorizationNow;
            value.giftsOpen110=giftsOpen110;value.mail110=mail110;value.composing110=modal=="compose110";value.keyboard110=Keyboard110;value.font110=BodyFont;value.messageDraft110=messageDraft;value.lifeError110=lifeError110;
            // View() holds a presentation read lease. The layout only reads
            // this DTO, so avoid a JSON roundtrip of the cached life list on
            // the first Teams frame; commands still use Snapshot() copies.
            value.life110=value.tab==0&&!mail110&&!giftsOpen110&&value.team?.isMember==true?session?.PresentationSnapshot<SocialLifeRequests110>(SocialPane82.TeamLives110):null;
            value.ownedLives110=giftsOpen110||value.team?.isMember!=true?session?.PresentationSnapshot<SocialOwnedLives110>(SocialPane82.OwnedLives110):null;value.now110=session?.LifeServerNow110??0;
            var lifeState=session?.Status(giftsOpen110?SocialPane82.OwnedLives110:SocialPane82.TeamLives110);value.serviceReady110=lifeState?.state==SocialViewState82.Ready;
            NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsChatViewLife,(int)Math.Round((AuthorizationNow-phase)*1000));phase=AuthorizationNow;
            value.busy|=lifeRefreshing110;
            value.offline110=lifeState?.state==SocialViewState82.Offline||session?.Status(SocialPane82.TeamChat).state==SocialViewState82.Offline;
            value.hasNewMessages110=session?.HasNewTeamMessages110==true;
            // View() already holds the presentation lease and has the team
            // projection. Avoid cloning it again for this read-only flag.
            var chatStatus=value.tab==0&&session!=null?session.Status(SocialPane82.TeamChat):null;
            value.composerAvailable110=value.tab==0&&!giftsOpen110&&!inspectDetails&&!accessCreate&&value.team?.isMember==true
                &&(modal.Length==0||modal=="compose110")&&chatStatus?.hasCachedView==true
                &&chatStatus.state!=SocialViewState82.Offline&&session.PendingCommand==null
                &&(!session.Busy||session.ReadInFlight);
            var pending=session?.PendingCommand;value.lifePendingOperation110=pending?.operation??lifeWrite110;value.lifePendingRequestId110=lifeWriteRequest110;
            if(pending?.operation=="life.help")value.lifePendingRequestId110=pending.path.Split('/')[5];else if(pending?.operation=="life.claim")value.lifePendingRequestId110=pending.path.Split('/')[3];
            NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsChatViewAvailability,(int)Math.Round((AuthorizationNow-phase)*1000));
        }
        bool ComposerAvailable110()
        {
            return Chat110&&(modal.Length==0||modal=="compose110")&&session!=null
                &&session.Status(SocialPane82.TeamChat).hasCachedView&&!OfflineChat110
                &&session.PendingCommand==null&&(!session.Busy||session.ReadInFlight);
        }
        bool RequestChat110(string action)
        {
            if(RequestMail111(action))return true;
            if(action=="cancel-compose"||action=="cancel"&&modal=="compose110"){ReleaseComposerFocus110();modal="";Reflow(ScrollPosition,true);return true;}
            if(action=="close-saved-lives"){giftsOpen110=false;ownedAfter110=0;needsRefresh=session!=null;lifePollAt110=0;Reflow(1);Pump();return true;}
            if(action=="saved-lives"){if(modal.Length>0||session==null)return true;giftsOpen110=true;ownedAfter110=0;lifePollAt110=0;Reflow(1);PumpChat110();return true;}
            if(action=="tab-mail"){if(modal.Length>0||!Chat110)return true;mail110=true;Reflow(1);return true;}
            if(action=="tab-chat"){mail110=false;}
            if(action=="compose"&&Chat110){if(modal.Length>0||!ComposerAvailable110())return true;mail110=false;modal="compose110";Reflow(0);RectTransform input;if(nodes.TryGetValue("online-message-input",out input)){var field=input.GetComponent<InputField>();if(field&&EventSystem.current){EventSystem.current.SetSelectedGameObject(field.gameObject);field.ActivateInputField();}}return true;}
            if(action=="send"&&modal=="compose110"){
                string clean;if(!ComposerAvailable110()||!SocialBackendClient82.TryMessageDraft110(messageDraft,out clean))return true;
                // Keep the text until an acknowledged receipt; the outbox owns
                // the immutable submitted body across unknown commits/restarts.
                ReleaseComposerFocus110();
                bool replacedRead=session.Busy;
                if(replacedRead&&!session.YieldReadForForeground())return true;
                if(replacedRead||refreshing||lifeRefreshing110||mailRefreshing111){loadGeneration++;refreshing=lifeRefreshing110=mailRefreshing111=needsRefresh=false;lifePollAt110=AuthorizationNow+10;}
                submittedMessage110=messageDraft;messageAcknowledgement110=session.TeamMessageAcknowledged110;foregroundMessageWrite110=true;Write(()=>session.SendTeamMessage(Guid.NewGuid().ToString("N"),clean));
                if(!writing)foregroundMessageWrite110=false;
                if(writing||session.PendingCommand!=null){modal="";Reflow(0,true);}return true;
            }
            bool request=action=="request-lives",help=action.StartsWith("help-life:",StringComparison.Ordinal),claim=action.StartsWith("claim-life:",StringComparison.Ordinal);
            if(action=="more-saved-lives") {if(session?.Busy!=false||session.PendingCommand!=null)return true;var data=session.Snapshot<SocialOwnedLives110>(SocialPane82.OwnedLives110);if(data?.hasMore==true){ownedAfter110=data.nextCursor;lifePollAt110=0;PumpChat110();}return true;}
            if(!request&&!help&&!claim)return false;
            if(modal.Length>0||session==null||session.Busy||refreshing||lifeRefreshing110||OfflineChat110||session.PendingCommand!=null||!EnsureAuthorizedSocial())return true;
            string id=request?"":action.Substring(help?10:11);SocialLifeRequest110 row=null;
            var data110=session.Snapshot<SocialLifeRequests110>(SocialPane82.TeamLives110);var owned=session.Snapshot<SocialOwnedLives110>(SocialPane82.OwnedLives110);
            if(!request)row=(giftsOpen110?owned?.requests??new SocialLifeRequest110[0]:(data110?.requests??new SocialLifeRequest110[0]).Concat(data110?.ownRequest==null?new SocialLifeRequest110[0]:new[]{data110.ownRequest}).Concat(owned?.requests??new SocialLifeRequest110[0])).FirstOrDefault(value=>value.requestId==id);
            if(request){if(!Chat110||data110==null||session.Status(SocialPane82.TeamLives110).state!=SocialViewState82.Ready)return true;if(data110.ownRequest?.state=="Open"){ScrollToLife110(data110.ownRequest.requestId);return true;}if(data110.nextRequestAt>session.LifeServerNow110)return true;}
            else if(row==null||help&&!row.canHelp||claim&&!row.canCollect)return true;
            lifeWrite110=request?"life.request":help?"life.help":"life.claim";lifeWriteRequest110=id;lifeError110="";
            Write(()=>request?session.RequestTeamLives110(Guid.NewGuid().ToString("N")):help?session.HelpTeamLife110(Guid.NewGuid().ToString("N"),id):session.ClaimTeamLives110(Guid.NewGuid().ToString("N"),id));return true;
        }
        void ReleaseComposerFocus110()
        {
            // A synchronous service callback may rebuild/destroy the selected
            // UGUI objects. Unity's truthy check, rather than CLR ?. chaining,
            // is required both before dispatch and when cancelling stale focus.
            var events=EventSystem.current;if(!events)return;var selected=events.currentSelectedGameObject;
            if(selected){var field=selected.GetComponent<InputField>();if(field)field.DeactivateInputField();}
            if(events)events.SetSelectedGameObject(null);
        }
        string submittedMessage110="";
        void UpdateComposer110(){RectTransform item;string clean;bool enabled=ComposerAvailable110()&&SocialBackendClient82.TryMessageDraft110(messageDraft,out clean);if(nodes.TryGetValue("online-compose-send",out item)&&item.GetComponent<Button>())item.GetComponent<Button>().interactable=enabled;if(nodes.TryGetValue("online-compose-send-art",out item)&&item.GetComponent<Image>())item.GetComponent<Image>().sprite=assets.Find(enabled?"TA_Button_Blue":"TA_Button_Disabled");if(nodes.TryGetValue("online-message-count",out item)&&item.GetComponent<Text>()){bool invalid;var text=item.GetComponent<Text>();text.text=TeamsSocialLayout110.DraftCount110(messageDraft,out invalid);text.color=ColorOf(invalid?"#B2412C":"#688CA5");}}
        void ObserveLifeWriteStatus110(){if(lifeWrite110.Length==0||session==null||session.Busy)return;var status=session.Status(lifeWrite110=="life.claim"?SocialPane82.OwnedLives110:SocialPane82.TeamLives110);if(status.state!=SocialViewState82.Ready&&status.state!=SocialViewState82.Loading&&status.state!=SocialViewState82.NotLoaded)lifeError110=TeamsSocialText110.T(lifeWrite110=="life.claim"?"claim_error":lifeWrite110=="life.help"?"help_error":"request_error");}
        void ObserveMessageReceipt110()
        {
            if(submittedMessage110.Length==0||session==null||session.Busy)return;
            if(session.PendingCommand!=null)return;
            if(session.TeamMessageAcknowledged110<=messageAcknowledgement110)return;
            if(messageDraft==submittedMessage110)messageDraft="";submittedMessage110="";modal="";
        }
        void RestorePendingMessage110(){if(session==null||messageDraft.Length>0)return;var pending=session.PendingCommand;if(pending?.operation!="message.send"||!pending.path.StartsWith("/v1/messages/Team/",StringComparison.Ordinal))return;try{messageDraft=SocialJson82.Text(SocialJson82.Read(pending.body),"text",2000);submittedMessage110=messageDraft;messageAcknowledgement110=session.TeamMessageAcknowledged110;}catch(Exception){}}
        void ScrollToLife110(string requestId){RectTransform card;if(!nodes.TryGetValue("online-life-"+requestId+"-base",out card)||!scroll)return;float range=Math.Max(0,content.rect.height-viewport.rect.height);if(range>0)scroll.verticalNormalizedPosition=1-Mathf.Clamp01(-card.anchoredPosition.y/range);}
        void StartFeedback110()
        {
            if(lifeFeedback110.Length==0||!IsVisible)return;var receipt=session?.LastLifeReceipt110;if(receipt==null||receipt.receiptId!=lifeFeedback110)return;lifeFeedback110="";
            RectTransform action,heart;string prefix="online-life-"+receipt.requestId;
            if(!nodes.TryGetValue(prefix+"-action",out action))return;
            Vector3 from=overlay.InverseTransformPoint(action.TransformPoint(action.rect.center)),to=from+Vector3.up*30;
            if(receipt.operation=="life.help"&&nodes.TryGetValue(prefix+"-heart-"+Math.Max(0,receipt.received-1),out heart))to=overlay.InverseTransformPoint(heart.TransformPoint(heart.rect.center));
            CancelFeedback110();var go=new GameObject("Confirmed team help feedback110",typeof(RectTransform));go.transform.SetParent(overlay,false);Place((RectTransform)go.transform,0,0,frame.width,frame.height);feedback110=go.AddComponent<TeamsHelpFeedback110>();feedback110.Begin(receipt.receiptId,receipt.operation,from,to,assets.Find("TA_Stat_heart"),assets.Find("TA_Stat_star"),Reduced110);
            if(receipt.operation=="life.request")feedback110.AnimateRequest(nodes.Where(pair=>pair.Key.StartsWith(prefix+"-",StringComparison.Ordinal)).Select(pair=>pair.Value).ToArray(),12*frame.artScale);
        }
    }
}

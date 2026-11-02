using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Teams;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Journey;
using HeartOfTheRain.App.Leaderboard;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.TeamsAccess;

namespace HeartOfTheRain.App.OnlineSocial
{
    [DisallowMultipleComponent] public sealed partial class OnlineTeamsPage82 : MonoBehaviour
    {
        HomePage home; TeamsAssets assets; ServerGameSession gateway; SocialPageSession82 session;
        Action<IEnumerator> dispatcher; bool ownsSession=true,closed,refreshing,needsRefresh,writing,reporting,browsingOlder,unconfigured;int layoutFrame;
        Canvas canvas; CanvasScaler scaler; RectTransform safe,backdrop,chrome,viewport,content,overlay; ScrollRect scroll;
        readonly Dictionary<string,RectTransform> nodes=new Dictionary<string,RectTransform>();
        string modal="",messageDraft="",nameDraft="",descriptionDraft="",confirmationId,confirmationName="",discardId,reportId,reportKind,localNotice="",directoryAfter="";
        int tab,revision=-1,loadGeneration,refreshToken;long validatedViewRevision=-1; Vector2Int lastSize; Rect lastSafe; float lastScale;ulong renderedFrame;
        bool regional;int rankOffset,countryPage;string countryDraft="",countryQuery="",countryError="";
        bool authorizing;double authorizationRetryAt;long authorizationRequest;string socialOwner;
        bool warming,warmAttempted,suppressChangedReflow;int warmGeneration;double warmFreshUntil;
        TeamsAssets visualWarmOwner;
        bool accessCreate,inspectDetails;string rankDetail115="";string searchDraft="",searchQuery="",badgeId="drop",badgeDraft="drop",inputError="",inputErrorField="",returnFocus109="",focusAfter109="";
        bool trackTeamWrite109;SocialPane82 teamWritePane109;string mutationNotice109="";
        OnlineTeamsFrame82 frame;SocialPageSession82 renderedSession;long renderedPresentationRevision;bool renderedBaseChat;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        Vector2Int verificationSize;
        Rect verificationSafe;bool hasVerificationSafe;OnlineTeamsView82 verificationView;
        public Canvas VerificationCanvas=>canvas;
        public OnlineTeamsFrame82 VerificationFrame=>frame;
        public IReadOnlyDictionary<string,RectTransform> VerificationNodes=>nodes;
        public bool VerificationPending=>authorizing||refreshing||needsRefresh||(session!=null&&session.Busy);
        public SocialPageSession82 VerificationSession=>session;
        public void ConfigureForVerification(TeamsAssets art,SocialPageSession82 authenticatedSession,Action<IEnumerator> dispatch) {
            if(!art||authenticatedSession==null||dispatch==null)throw new ArgumentException();
            verificationView=null;unconfigured=false;assets=art;session=authenticatedSession;dispatcher=dispatch;ownsSession=false;session.Changed+=Changed;
        }
        public void ConfigureViewForVerification(TeamsAssets art,OnlineTeamsView82 value){if(!art||value==null)throw new ArgumentException();assets=art;verificationView=value;tab=value.tab;nameDraft=value.nameDraft;descriptionDraft=value.descriptionDraft;searchDraft=value.searchQuery;messageDraft=value.messageDraft110;value.font110=BodyFont;unconfigured=true;if(IsVisible)Reflow(1);}
        public void ClearViewForVerification(){verificationView=null;}
        public void VerificationSafeArea(Rect physicalSafe){verificationSafe=physicalSafe;hasVerificationSafe=true;if(IsVisible)Reflow(ScrollPosition);}
        public void VerificationViewport(int width,int height){verificationSize=new Vector2Int(width,height);if(IsVisible)Reflow(ScrollPosition);}
        public void VerificationPump(){PumpClaimWallet110();PumpLeave113();Pump();}
        public HeartOfTheRain.App.TeamsLifecycle.TeamsLifecycleMotion113 VerificationLeaveMotion113 { get { RectTransform node;return nodes.TryGetValue("leave-motion113",out node)?node.GetComponent<HeartOfTheRain.App.TeamsLifecycle.TeamsLifecycleMotion113>():null; } }
        public bool VerificationObserveRead()=>ObserveRead();
        public string VerificationBackAction()=>BackAction136(modal.Length>0,ownedMailOpen111,giftsOpen110,mail110,inspectDetails,accessCreate,tab);
        public void VerificationWarm()=>TryWarm();
#endif
        public bool IsVisible=>canvas&&canvas.gameObject.activeSelf;
        float ScrollPosition=>scroll?scroll.verticalNormalizedPosition:(tab==0?0:1);
        Font BodyFont=>assets.leaderboard.journey.home.regularFont;
        Font BoldFont=>assets.leaderboard.journey.home.boldFont;
        static int timestampWarmScheduled;
        static void WarmLocalTimeCache() {
            if(System.Threading.Interlocked.Exchange(ref timestampWarmScheduled,1)!=0)return;
            try{System.Threading.ThreadPool.QueueUserWorkItem(_=>{
                try{var sample=DateTimeOffset.FromUnixTimeSeconds(1700000000).ToLocalTime();foreach(var name in new[]{"en-US","es-ES","fr-FR","de-DE","ru-RU"})sample.ToString("g",System.Globalization.CultureInfo.GetCultureInfo(name));}
                catch(Exception){}
            });}catch(Exception){}
        }
        public void Configure(HomePage owner,TeamsAssets art,ServerGameSession server) {
            if(!owner||!art||!server)throw new ArgumentException();
            unconfigured=false;home=owner;assets=art;WarmLocalTimeCache();
            if(gateway!=server){if(gateway){gateway.IdentityChanged-=IdentityChanged;gateway.Changed-=GatewayChanged;}gateway=server;gateway.IdentityChanged+=IdentityChanged;gateway.Changed+=GatewayChanged;}
            if(!canvas){Build();canvas.gameObject.SetActive(false);}TrySession();TryWarm();
            if(Application.isPlaying&&visualWarmOwner!=art){visualWarmOwner=art;StartCoroutine(WarmVisualAssets(art));}
        }
        IEnumerator WarmVisualAssets(TeamsAssets art){
            double started=AuthorizationNow;
            var accessRequest=Resources.LoadAsync<TeamsAccessAssets109>("HOTR_TeamsAccess109/Assets");yield return accessRequest;
            if(closed||assets!=art)yield break;
            if(accessRequest.asset)art.access=accessRequest.asset as TeamsAccessAssets109;
            var socialRequest=Resources.LoadAsync<HeartOfTheRain.App.TeamsSocial.TeamsSocialAssets110>("HOTR_TeamsSocial110/Assets");yield return socialRequest;
            if(closed||assets!=art)yield break;
            if(socialRequest.asset)art.social=socialRequest.asset as HeartOfTheRain.App.TeamsSocial.TeamsSocialAssets110;
            var mailRequest=Resources.LoadAsync<HeartOfTheRain.App.TeamsMail.TeamsMailAssets111>("HOTR_TeamsMail111/Assets");yield return mailRequest;
            if(closed||assets!=art)yield break;
            if(mailRequest.asset)art.mail=mailRequest.asset as HeartOfTheRain.App.TeamsMail.TeamsMailAssets111;
            var inviteRequest=Resources.LoadAsync<HeartOfTheRain.App.TeamsInvites.TeamsInvitesAssets112>("HOTR_TeamsInvites112/Assets");yield return inviteRequest;
            if(closed||assets!=art)yield break;
            if(inviteRequest.asset)art.invites=inviteRequest.asset as HeartOfTheRain.App.TeamsInvites.TeamsInvitesAssets112;
            NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsAssetsReady,(int)Math.Round((AuthorizationNow-started)*1000));
        }
        // Ordinary local play has no social authority. Reuse the real page's
        // empty state without inventing membership, credentials or a network.
        public void ConfigureUnavailable(HomePage owner,TeamsAssets art){
            if(!owner||!art)throw new ArgumentException();
            if(gateway){gateway.IdentityChanged-=IdentityChanged;gateway.Changed-=GatewayChanged;gateway=null;}
            if(session!=null){session.Changed-=Changed;if(ownsSession)session.Dispose();session=null;}
            home=owner;assets=art;unconfigured=true;ownsSession=true;dispatcher=null;socialOwner=null;
            loadGeneration++;warmGeneration++;warming=warmAttempted=false;warmFreshUntil=0;authorizationRequest++;authorizing=refreshing=needsRefresh=writing=reporting=false;modal="";messageDraft=nameDraft=descriptionDraft=localNotice="";
            accessCreate=inspectDetails=false;searchDraft=searchQuery=inputError="";badgeId=badgeDraft="drop";
            trackTeamWrite109=false;mutationNotice109="";
            ResetChatOwner110();ResetInvite112();ResetInviteFeedbackOwner112();ResetLeave113();
            if(IsVisible)Reflow(1);
        }
        void Dispatch(IEnumerator routine){if(dispatcher!=null)dispatcher(routine);else StartCoroutine(routine);}
        void TrySession() {
            if(unconfigured||session!=null||closed||!gateway||!gateway.SocialEnabled)return;ServerAuthorizedContext access;if(!gateway.TryGetReadContext(out access))return;
            HeartOfTheRain.App.OnlineIdentity.IProtectedSessionStore82 store=null;
            try {store=gateway.CreateProtectedSocialStore();var client=gateway.CreateSocialClient(Dispatch,store);session=new SocialPageSession82(client,store,()=>gateway?gateway.SessionGeneration:long.MinValue);session.Changed+=Changed;socialOwner=gateway.PlayerId;needsRefresh=IsVisible;}
            catch(Exception){store?.Dispose();localNotice=OnlineTeamsText82.T("Unavailable");}
        }
        static double AuthorizationNow=>System.Diagnostics.Stopwatch.GetTimestamp()/(double)System.Diagnostics.Stopwatch.Frequency;
        bool EnsureAuthorizedSocial(){
            if(unconfigured)return false;
            if(!gateway)return true; // Explicit native component-only seam.
            if(closed||!gateway.Ready||!gateway.SocialEnabled||gateway.AccountBlocked)return false;
            if(authorizing||gateway.Busy)return false;
            ServerAuthorizedContext context;
            if(gateway.TryGetReadContext(out context)&&session?.PlayerId!=null)return true;
            if(AuthorizationNow<authorizationRetryAt)return false;
            authorizing=true;long request=++authorizationRequest;var owner=gateway;
            owner.WithAuthenticatedSession((access,why)=>{
                if(!this||closed||owner!=gateway||request!=authorizationRequest)return;
                authorizing=false;authorizationRetryAt=AuthorizationNow+10;
                if(access!=null&&owner.Ready&&access.PlayerId==owner.PlayerId){
                    if(session!=null){session.Changed-=Changed;if(ownsSession)session.Dispose();session=null;}
                    localNotice="";TrySession();needsRefresh=IsVisible&&session!=null;
                }else{needsRefresh=false;localNotice=OnlineTeamsText82.T("Unavailable");}
                if(IsVisible)Reflow(ScrollPosition,true);
            });
            return false;
        }
        void GatewayChanged(){TrySession();TryWarm();if(IsVisible)Reflow(ScrollPosition,true);}
        void IdentityChanged(){bool same=gateway&&!gateway.AccountBlocked&&gateway.PlayerId==socialOwner;rankDetail115="";loadGeneration++;warmGeneration++;warming=warmAttempted=false;warmFreshUntil=0;refreshing=needsRefresh=writing=false;
            if(!same){ResetChatOwner110();ResetInvite112();ResetInviteFeedbackOwner112();ResetLeave113();modal="";messageDraft=nameDraft=descriptionDraft=searchDraft=searchQuery=inputError=mutationNotice109="";trackTeamWrite109=false;badgeId=badgeDraft="drop";accessCreate=inspectDetails=false;browsingOlder=false;}
            if(session!=null){session.Changed-=Changed;if(ownsSession)session.Dispose();session=null;}localNotice="";if(IsVisible)Reflow(1);}

        void Changed() {
            if(closed)return;
            ObserveLifeReceipt110();ObserveMailReceipt111();ObserveInviteReceipt112();ObserveLeave113();ObserveMessageReceipt110();ObserveLifeWriteStatus110();
            // A refused write left nothing to check. Say why; the refresh that follows replaces its pane status.
            string refused=session?.TakeWriteRefusal();if(refused!=null){mutationNotice109=OnlineTeamsText82.Refusal(refused);lifeWrite110=lifeWriteRequest110="";leaveSubmitting113=false;invitePendingFriend112="";}
            if(writing&&session!=null&&!session.Busy){writing=false;if(trackTeamWrite109){var outcome=session.Status(teamWritePane109);if(outcome.state!=SocialViewState82.Ready&&outcome.state!=SocialViewState82.Loading&&outcome.state!=SocialViewState82.NotLoaded&&outcome.state!=SocialViewState82.CommitUnknown)mutationNotice109=OnlineTeamsText82.Status(outcome);trackTeamWrite109=false;}needsRefresh=session.PendingCommand==null;if(foregroundMessageWrite110){bool sent=needsRefresh&&session.TeamMessageAcknowledged110>messageAcknowledgement110;foregroundMessageWrite110=false;if(sent){needsRefresh=!session.RefreshTeamMessages();}}if(reporting){if(needsRefresh&&refused==null)localNotice=OnlinePlayersText82.T("ReportReceived");needsRefresh=false;reporting=false;}}
            // A read's Loading notification has no new data. Rebuilding every
            // node and forcing a Canvas update here adds a hitch per request.
            if(IsVisible){if(!suppressChangedReflow&&!warming&&!refreshing&&!lifeRefreshing110&&!mailRefreshing111&&(session==null||!session.ReadInFlight))Reflow(ScrollPosition,true);StartMailFeedback111();StartInviteFeedback112();}
        }
        public void Show() {
            if(closed||!assets)return;
            if(home){var flow=home.GetComponent<HomeLevelFlow>();var pre=home.GetComponent<PreLevelModal>();if((flow&&flow.Playing)||(pre&&pre.IsVisible))return;var journey=home.GetComponent<JourneyPage>();if(journey)journey.Hide(false);var ranks=home.GetComponent<LeaderboardPage>();if(ranks)ranks.Hide(false);}
            double started=AuthorizationNow;
            Build();canvas.gameObject.SetActive(true);if(home)home.SetPresentation(false,false);double phase=AuthorizationNow;NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsShowPrepare,(int)Math.Round((phase-started)*1000));
            TrySession();needsRefresh=session!=null&&(tab==2||giftsOpen110||ownedMailOpen111||!warming&&AuthorizationNow>=warmFreshUntil);
            if(session!=null){ShowPane(session,tab==0?SocialPane82.TeamChat:SocialPane82.TeamInfo);if(!needsRefresh&&!warming)session.DeferPolling(warmFreshUntil-AuthorizationNow);}
            double next=AuthorizationNow;NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsShowSession,(int)Math.Round((next-phase)*1000));
            bool reusable=renderedBaseChat&&tab==0&&!mail110&&!giftsOpen110&&!ownedMailOpen111&&modal.Length==0&&!accessCreate&&!inspectDetails&&frame!=null&&renderedSession==session&&session!=null&&renderedPresentationRevision==session.PresentationRevision&&lastSize==ScreenSize()&&lastSafe==Screen.safeArea&&revision==GameLocale.Revision;
            if(reusable){scroll.verticalNormalizedPosition=0;NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsFrameReuse,(int)Math.Round((AuthorizationNow-started)*1000));}
            else Reflow(tab==0?0:1);phase=AuthorizationNow;Pump(true);NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsShowPump,(int)Math.Round((AuthorizationNow-phase)*1000));
            NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsShow,(int)Math.Round((AuthorizationNow-started)*1000));
        }
        // Rank selection only reads team details; it never joins or leaves a team.
        public void OpenRankDetails115(string id) {
            if(!HeartOfTheRain.App.OnlineIdentity.IdentityProtocol82.Id(id)||!IsVisible)return;
            // Dismiss only transient page state. Durable claims and membership stay with their existing services.
            giftsOpen110=ownedMailOpen111=mail110=false;rankDetail115=id;inspectDetails=false;accessCreate=false;needsRefresh=true;Pump();
        }
        public void Hide(bool showHome=true) {
            if(!IsVisible)return;loadGeneration++;warmGeneration++;needsRefresh=refreshing=lifeRefreshing110=mailRefreshing111=false;rankDetail115="";modal="";nameDraft=descriptionDraft=mutationNotice109="";observedRevision=-2;CancelFeedback110();CancelMailFeedback111();CancelInviteFeedback112();canvas.gameObject.SetActive(false);session?.Hide();
            if(showHome&&home)home.SetPresentation(true,true);
        }
        void Update() {
            PumpClaimWallet110();PumpLeave113();
            if(!IsVisible){TryWarm();return;}Pump();
            if(lastSize!=ScreenSize()||lastSafe!=Screen.safeArea||revision!=GameLocale.Revision||Math.Abs(lastScale-Scale(SafeRect()))>.01f)Reflow(ScrollPosition,true);
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
            bool back=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
            bool back=Input.GetKeyDown(KeyCode.Escape);
#endif
            if(back){string target=BackAction136(modal.Length>0,ownedMailOpen111,giftsOpen110,mail110,inspectDetails,accessCreate,tab);if(target!=null)Request(target);else Hide();}
        }
        // Android Back steps out of the current Teams view before it leaves the page.
        public static string BackAction136(bool modalOpen,bool ownedMail,bool savedLives,bool teamMail,bool details,bool create,int openTab){
            if(modalOpen)return "cancel";if(ownedMail)return "mail-owned-close";if(savedLives)return "close-saved-lives";if(teamMail)return "tab-chat";
            if(details)return "close-details";if(create)return "access-find";return openTab!=0?"tab-chat":null;
        }
        void Pump(bool measure=false) {
            if(closed||!IsVisible)return;
            double phase=AuthorizationNow;TrySession();if(session?.FailStalledRead()==true)NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsReadTimeout,0);
            if(measure)NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsPumpSession,(int)Math.Round((AuthorizationNow-phase)*1000));
            phase=AuthorizationNow;if(!EnsureAuthorizedSocial()||session==null)return;
            if(measure)NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsPumpAuthorization,(int)Math.Round((AuthorizationNow-phase)*1000));
            phase=AuthorizationNow;PumpLeave113();
            if(needsRefresh&&!refreshing&&!warming&&!mailRefreshing111&&!session.Busy){needsRefresh=false;Dispatch(Refresh(++loadGeneration));}
            if(measure)NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsPumpRefresh,(int)Math.Round((AuthorizationNow-phase)*1000));
            phase=AuthorizationNow;if(!refreshing&&modal.Length==0)session.Tick();
            if(measure)NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsPumpTick,(int)Math.Round((AuthorizationNow-phase)*1000));
            phase=AuthorizationNow;PumpChat110();
            if(measure)NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsPumpChat,(int)Math.Round((AuthorizationNow-phase)*1000));
            phase=AuthorizationNow;PumpInvite112();
            if(measure)NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsPumpInvite,(int)Math.Round((AuthorizationNow-phase)*1000));
        }
        void TryWarm() {
            if(closed||unconfigured||IsVisible||warming||warmAttempted||session==null||session.Busy||session.PendingCommand!=null)return;
            if(home&&!home.PresentationVisible)return;
            if(gateway&&(!gateway.Ready||gateway.Busy||!gateway.SocialEnabled||gateway.AccountBlocked))return;
            warmAttempted=warming=true;Dispatch(Warm(++warmGeneration,session));
        }
        bool WarmCurrent(int token,SocialPageSession82 current)=>!closed&&token==warmGeneration&&session==current;
        void ShowPane(SocialPageSession82 current,SocialPane82 pane){suppressChangedReflow=true;try{current.Show(pane);}finally{suppressChangedReflow=false;}}
        IEnumerator Warm(int token,SocialPageSession82 current) {
            bool ready=false;double started=AuthorizationNow;
            try {
                // The owner directory is authoritative. Only a confirmed
                // membership may cause private detail or chat to be prefetched.
                if(!current.RefreshTeams())yield break;
                while(current.Busy){current.FailStalledRead();yield return null;}
                if(!WarmCurrent(token,current)||current.Status(SocialPane82.Teams).state!=SocialViewState82.Ready)yield break;
                var directory=current.Snapshot<SocialTeams82>(SocialPane82.Teams);
                if(directory==null)yield break;
                if(!string.IsNullOrEmpty(directory.myTeamId)) {
                    if(!current.RefreshTeam())yield break;
                    while(current.Busy){current.FailStalledRead();yield return null;}
                    if(!WarmCurrent(token,current)||current.Status(SocialPane82.TeamInfo).state!=SocialViewState82.Ready)yield break;
                    var team=current.Snapshot<SocialTeam82>(SocialPane82.TeamInfo);
                    if(team==null||!team.isMember)yield break;
                    if(!current.RefreshTeamMessages())yield break;
                    while(current.Busy){current.FailStalledRead();yield return null;}
                    if(!WarmCurrent(token,current)||current.Status(SocialPane82.TeamChat).state!=SocialViewState82.Ready)yield break;
                    ready=true;
                    if(IsVisible&&tab==0)Reflow(ScrollPosition,true);
                    if(current.RefreshTeamLives110())while(current.Busy){current.FailStalledRead();yield return null;}
                    if(!WarmCurrent(token,current))yield break;
                    if(current.RefreshTeamMail111())while(current.Busy){current.FailStalledRead();yield return null;}
                    if(!WarmCurrent(token,current))yield break;
                }else{ready=true;if(IsVisible)Reflow(ScrollPosition,true);}
                if(current.RefreshOwnedLives110(ownedAfter110))while(current.Busy){current.FailStalledRead();yield return null;}
                if(!WarmCurrent(token,current))yield break;
                if(current.RefreshOwnedMail111(ownedMailAfter111))while(current.Busy){current.FailStalledRead();yield return null;}
            } finally {
                if(token==warmGeneration){warming=false;warmFreshUntil=AuthorizationNow+(ready?30:10);lifePollAt110=mailPollAt111=AuthorizationNow+10;NavigationDiagnostics124.Shared.Record(ready?NavigationEvent124.TeamsWarmReady:NavigationEvent124.TeamsWarmUnavailable,(int)Math.Round((AuthorizationNow-started)*1000));if(IsVisible)Reflow(ScrollPosition,true);}
            }
        }
        bool ServiceUnreachable(SocialPageSession82 owner,SocialPane82 pane){var status=owner.Status(pane);if(status.state!=SocialViewState82.Offline&&status.state!=SocialViewState82.Unauthenticated)return false;localNotice=OnlineTeamsText82.Status(status);return true;}
        IEnumerator Refresh(int token) {
            if(closed||token!=loadGeneration||!IsVisible)yield break;
            var current=session;refreshToken=token;refreshing=true;localNotice="";if(current?.Snapshot<SocialTeams82>(SocialPane82.Teams)==null)Reflow(ScrollPosition,true);
            try {
                if(current==null)yield break;
                if(giftsOpen110||ownedMailOpen111){
                    if(current.RefreshOwnedLives110(ownedAfter110))while(current.Busy)yield return null;
                    if(closed||token!=loadGeneration||!IsVisible||session!=current)yield break;
                    if(ServiceUnreachable(current,SocialPane82.OwnedLives110))yield break;
                    if(current.RefreshOwnedMail111(ownedMailOpen111?ownedMailAfter111:0))while(current.Busy)yield return null;
                    if(closed||token!=loadGeneration||!IsVisible||session!=current)yield break;
                    ServiceUnreachable(current,SocialPane82.OwnedMail111);
                    yield break;
                }
                if(!string.IsNullOrEmpty(rankDetail115)){
                    string target=rankDetail115;rankDetail115="";inspectDetails=true;tab=1;
                    if(current.SelectTeam(target))while(current.Busy)yield return null;
                    yield break;
                }
                if(inspectDetails&&!string.IsNullOrEmpty(current.SelectedTeamId)){if(current.RefreshTeam())while(current.Busy)yield return null;yield break;}
                if(tab==2){
                    if(current.RefreshRegion())while(current.Busy)yield return null;
                    if(closed||token!=loadGeneration||!IsVisible||session!=current)yield break;
                    ShowPane(current,regional?SocialPane82.RegionalTeamRanks:SocialPane82.GlobalTeamRanks);
                    if(regional&&string.IsNullOrEmpty(current.Snapshot<SocialRegion89>(SocialPane82.Region)?.regionCode))yield break;
                    if(current.RefreshTeamRanks(regional?"regional":"global",rankOffset))while(current.Busy)yield return null;
                    yield break;
                }
                if(!current.RefreshTeams(directoryAfter,searchQuery))yield break;
                while(current.Busy)yield return null;
                if(closed||token!=loadGeneration||!IsVisible||session!=current)yield break;
                if(current.Status(SocialPane82.Teams).state!=SocialViewState82.Ready){localNotice=OnlineTeamsText82.Status(current.Status(SocialPane82.Teams));yield break;}
                var directory=current.Snapshot<SocialTeams82>(SocialPane82.Teams);
                if(directory==null)yield break;
                ObserveDeferredLeaveToast113(current,directory);
                if(string.IsNullOrEmpty(directory.myTeamId)){
                    inspectDetails=false;if(!accessCreate)tab=0;ShowPane(current,SocialPane82.Teams);
                    Reflow(ScrollPosition,true);
                    if(current.RefreshOwnedLives110(ownedAfter110))while(current.Busy)yield return null;
                    if(closed||token!=loadGeneration||!IsVisible||session!=current)yield break;
                    if(ServiceUnreachable(current,SocialPane82.OwnedLives110))yield break;
                    if(current.RefreshOwnedMail111(ownedMailOpen111?ownedMailAfter111:0))while(current.Busy)yield return null;
                    if(closed||token!=loadGeneration||!IsVisible||session!=current)yield break;
                    ServiceUnreachable(current,SocialPane82.OwnedMail111);
                    yield break;
                }
                if(!current.SelectTeam(directory.myTeamId))yield break;
                while(current.Busy)yield return null;
                if(closed||token!=loadGeneration||!IsVisible||session!=current)yield break;
                if(current.Status(SocialPane82.TeamInfo).state!=SocialViewState82.Ready){localNotice=OnlineTeamsText82.Status(current.Status(SocialPane82.TeamInfo));yield break;}
                var team=current.Snapshot<SocialTeam82>(SocialPane82.TeamInfo);
                if(team==null||!team.isMember)yield break;
                ShowPane(current,tab==0?SocialPane82.TeamChat:SocialPane82.TeamInfo);
                if(tab==0&&current.RefreshTeamMessages())while(current.Busy)yield return null;
                if(closed||token!=loadGeneration||!IsVisible||session!=current)yield break;
                if(tab==0&&ServiceUnreachable(current,SocialPane82.TeamChat))yield break;
                if(tab==0)Reflow(ScrollPosition,true);
                if(tab==0&&current.RefreshTeamLives110())while(current.Busy)yield return null;
                if(closed||token!=loadGeneration||!IsVisible||session!=current)yield break;
                if(current.RefreshOwnedLives110(ownedAfter110))while(current.Busy)yield return null;
                if(closed||token!=loadGeneration||!IsVisible||session!=current)yield break;
                if(ServiceUnreachable(current,SocialPane82.OwnedLives110))yield break;
                if(current.RefreshOwnedMail111(ownedMailOpen111?ownedMailAfter111:0))while(current.Busy)yield return null;
                if(closed||token!=loadGeneration||!IsVisible||session!=current)yield break;
                ServiceUnreachable(current,SocialPane82.OwnedMail111);
            } finally {if(refreshToken==token)refreshing=false;if(!closed&&token==loadGeneration&&IsVisible){lifePollAt110=AuthorizationNow+10;UpdateLifeReadNotice110();Reflow(ScrollPosition,true);StartFeedback110();}}
        }
        void Write(Func<bool> submit,SocialPane82? teamResultPane=null) {
            if(session==null||refreshing||session.Busy)return;
            if(session.PendingCommand!=null){localNotice=OnlineTeamsText82.T("Pending");Reflow(ScrollPosition);return;}
            writing=true;mutationNotice109="";if(teamResultPane.HasValue){teamWritePane109=teamResultPane.Value;trackTeamWrite109=true;}if(!submit()){writing=false;trackTeamWrite109=false;}
        }
        public void Request(string action) {
            if(!IsVisible||string.IsNullOrEmpty(action)||action=="disabled")return;
            if(RequestLeave113(action))return;
            if(RequestInvite112(action))return;
            if(RequestChat110(action))return;
            bool badgeAction=modal=="badge"&&(action=="badge-cancel"||action=="badge-confirm"||action.StartsWith("badge:",StringComparison.Ordinal));
            if(modal.Length>0&&action!="cancel"&&action!="send"&&action!="create-submit"&&action!="confirm"&&!(modal=="invite"&&action=="copy-invite")&&!badgeAction&&!CountryRegion89.DialogAction(action))return;
            if(action=="home"){Hide();return;}
            if(action=="journey"||action=="leaderboard"||action=="shop"){Hide(false);if(home)home.NavigationRequested.Invoke(action);return;}
            if(action=="teams")return;
            if(action=="cancel-country"){modal="";countryError="";Reflow(ScrollPosition);return;}
            if(action=="cancel"){if(modal=="badge"||modal=="invite")focusAfter109=returnFocus109;modal="";Reflow(ScrollPosition);return;}
            if(action=="tab-chat"||action=="tab-info"||action=="tab-ranks"){
                tab=action=="tab-chat"?0:action=="tab-info"?1:2;inspectDetails=accessCreate=false;rankOffset=0;browsingOlder=false;mutationNotice109="";
                if(session!=null)ShowPane(session,tab==0?SocialPane82.TeamChat:SocialPane82.TeamInfo);
                needsRefresh=session!=null;Reflow(tab==0?0:1);Pump();return;
            }
            if(action=="scope-global"||action=="scope-regional"){
                regional=action=="scope-regional";rankOffset=0;needsRefresh=session!=null;Reflow(1);Pump();return;
            }
            if(action=="access-find"||action=="access-create"||action=="create"){
                accessCreate=action!="access-find";inspectDetails=false;tab=accessCreate?1:0;inputError="";
                if(!accessCreate&&session!=null){directoryAfter="";needsRefresh=true;}Reflow(1);Pump();return;
            }
            // The picker edits a local draft. A missing social service must not
            // prevent choosing an emblem; only Create submits to the backend.
            if(action=="badge-open"){
                if(!accessCreate)return;
                badgeDraft=badgeId;returnFocus109="online-badge-choose";modal="badge";Reflow(ScrollPosition);return;
            }
            if(badgeAction){
                if(action=="badge-cancel"){modal="";focusAfter109=returnFocus109;}
                else if(action=="badge-confirm"){
                    badgeId=TeamsAccessBadges109.Resolve(badgeDraft);modal="";focusAfter109=returnFocus109;
                }else if(TeamsAccessBadges109.Valid(action.Substring(6)))badgeDraft=action.Substring(6);
                Reflow(ScrollPosition);return;
            }
            if(action=="close-details"){inspectDetails=false;accessCreate=false;tab=0;directoryAfter="";needsRefresh=session!=null;Reflow(1);Pump();return;}
            if(action=="retry")authorizationRetryAt=0;if(!EnsureAuthorizedSocial())return;
            if(session==null){if(action=="retry"){TrySession();needsRefresh=session!=null;}Reflow(1);return;}
            if(action=="search"){
                string clean;if(!SocialBackendClient82.TryTeamSearch109(searchDraft,out clean)){localNotice=OnlineTeamsText82.T("Rejected");Reflow(1);return;}
                searchQuery=clean;directoryAfter="";inspectDetails=accessCreate=false;tab=0;needsRefresh=true;Reflow(1);Pump();return;
            }
            if(action.StartsWith("detail:",StringComparison.Ordinal)){if(session.Busy||refreshing||session.PendingCommand!=null)return;if(session.SelectTeam(action.Substring(7))){inspectDetails=true;tab=1;needsRefresh=false;Reflow(1);}return;}
            if(action=="invite"){if(session.Busy||refreshing||session.PendingCommand!=null||session.Snapshot<SocialTeam82>(SocialPane82.TeamInfo)?.isMember!=true)return;returnFocus109="online-invite";modal="invite";Reflow(ScrollPosition);return;}
            if(action=="copy-invite"&&modal=="invite"){var invite=session.Snapshot<SocialTeam82>(SocialPane82.TeamInfo);if(invite?.isMember!=true)return;try{string value=invite.name+"\n"+invite.teamId;GUIUtility.systemCopyBuffer=value;localNotice=TeamsAccessText109.T(GUIUtility.systemCopyBuffer==value?"service_copied":"service_copy_failed");}catch(Exception){localNotice=TeamsAccessText109.T("service_copy_failed");}Reflow(ScrollPosition);return;}
            if(action=="retry"){directoryAfter="";needsRefresh=true;localNotice="";Pump();return;}
            if(action=="choose-country"){if(session.Busy||refreshing||session.PendingCommand!=null)return;countryDraft=countryQuery=countryError="";countryPage=0;modal="country";Reflow(ScrollPosition);return;}
            if(modal=="country"&&(action=="search-country"||action=="country-prev"||action=="country-next")){
                if(action=="search-country"){countryQuery=countryDraft.Trim();countryPage=0;}else countryPage=Math.Max(0,Math.Min(countryPage+(action=="country-next"?1:-1),Math.Max(0,(CountryRegion89.Countries(countryQuery).Length-1)/4)));countryError="";Reflow(ScrollPosition);return;
            }
            if(modal=="country"&&(action=="save-country"||action.StartsWith("country:",StringComparison.Ordinal))){string code=CountryRegion89.Normalize(action=="save-country"?countryDraft:action.Substring(8));if(code.Length==0){countryError=CountryRegion89.T("InvalidCountry");Reflow(ScrollPosition);return;}modal="";rankOffset=0;Write(()=>session.SetRegion(Guid.NewGuid().ToString("N"),code));return;}
            if(action=="more-ranks"){var ranks=session.Snapshot<SocialTeamLeaderboard89>(regional?SocialPane82.RegionalTeamRanks:SocialPane82.GlobalTeamRanks);if(ranks?.hasMore==true){rankOffset=ranks.nextOffset;needsRefresh=true;Pump();}return;}
            if(action=="check-pending"){writing=true;if(!session.ReconcilePending())writing=false;return;}
            if(action=="resume-pending"){writing=true;if(!session.ResumePending())writing=false;return;}
            if(action=="forget"){var pending=session.PendingCommand;if(pending==null)return;discardId=pending.commandId;modal="forget";}
            else if(action=="confirm"&&modal=="forget"){bool claim=session.PendingCommand?.operation=="life.claim"||(session.PendingCommand?.operation=="mail.claim"||session.PendingCommand?.operation=="mail.claim-owned");if(session.AcknowledgeAndDiscardPending(discardId,true)){if(claim)lifeWalletRefresh110=true;lifeWrite110=lifeWriteRequest110="";modal="";needsRefresh=true;}Reflow(ScrollPosition);return;}
            else if(action=="more"){var directory=session.Snapshot<SocialTeams82>(SocialPane82.Teams);if(directory!=null&&directory.hasMore){directoryAfter=directory.nextCursor;needsRefresh=true;Pump();}return;}
            else if(action=="older-messages"){browsingOlder=true;scroll.verticalNormalizedPosition=1;session.LoadOlderMessages();return;}
            else if(action=="latest-messages"){browsingOlder=false;session.LatestMessages();return;}
            else if(action=="create-submit") {
                if(session.Snapshot<SocialTeam82>(SocialPane82.TeamInfo)?.isMember==true)return;string name,description;
                if(!SocialBackendClient82.TryTeamDraft109(nameDraft,descriptionDraft,out name,out description,out inputErrorField)){inputError=TeamsAccessText109.T(inputErrorField=="description"?"service_invalid_description":"invalid_name");Reflow(ScrollPosition);return;}
                inputError=inputErrorField="";modal="";Write(()=>session.CreateTeam(Guid.NewGuid().ToString("N"),name,description,badgeId),SocialPane82.Teams);return;
            }
            else if(action.StartsWith("join:",StringComparison.Ordinal)){Write(()=>session.JoinTeam(Guid.NewGuid().ToString("N"),action.Substring(5)),SocialPane82.Teams);return;}
            else if(action=="compose"){modal="compose";}
            else if(action=="send") {
                string text=messageDraft.Trim();if(text.Length==0)return;modal="";
                Write(()=>session.SendTeamMessage(Guid.NewGuid().ToString("N"),text));messageDraft="";return;
            }
            else if(action=="leave"){modal="leave";confirmationName=session.Snapshot<SocialTeam82>(SocialPane82.TeamInfo)?.name??"";}
            else if(action=="report-team"){modal="report";reportKind="Team";reportId=session.SelectedTeamId;}
            else if(action.StartsWith("report-message:",StringComparison.Ordinal)){var item=session.Snapshot<SocialMessages82>(SocialPane82.TeamChat)?.messages?.FirstOrDefault(row=>row.messageId==action.Substring(15));if(item==null)return;modal="report";reportKind="Message";reportId=item.messageId;}
            else if(action.StartsWith("member:",StringComparison.Ordinal)){if(home){var ranks=home.GetComponent<LeaderboardPage>();if(ranks){Hide(false);ranks.ShowServerPlayer(action.Substring(7));}}return;}
            else if(action.StartsWith("transfer:",StringComparison.Ordinal)){confirmationId=action.Substring(9);confirmationName=session.Snapshot<SocialTeam82>(SocialPane82.TeamInfo)?.members?.FirstOrDefault(row=>row.playerId==confirmationId)?.displayName??"";modal="transfer";}
            else if(action=="confirm"&&modal=="leave"){modal="";Write(()=>session.LeaveTeam(Guid.NewGuid().ToString("N")),SocialPane82.TeamInfo);return;}
            else if(action=="confirm"&&modal=="transfer"){modal="";Write(()=>session.TransferLeadership(Guid.NewGuid().ToString("N"),confirmationId));return;}
            else if(action=="confirm"&&modal=="report"){modal="";reporting=true;Write(()=>reportKind=="Message"?session.ReportMessage(Guid.NewGuid().ToString("N"),reportId,"Other"):session.ReportPublicText(Guid.NewGuid().ToString("N"),reportKind,reportId,"Other"));return;}
            else return;
            Reflow(ScrollPosition);
        }
        OnlineTeamsView82 View() {
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(verificationView!=null){validatedViewRevision=session?.PresentationRevision??-1;return verificationView;}
#endif
            var presentation=session==null?default(SocialPageSession82.PresentationReadLease):session.BeginPresentationRead();
            try {
            double viewStarted=AuthorizationNow;
            var directory=session?.PresentationSnapshot<SocialTeams82>(SocialPane82.Teams);var team=session?.PresentationSnapshot<SocialTeam82>(SocialPane82.TeamInfo);var region=tab==2?session?.PresentationSnapshot<SocialRegion89>(SocialPane82.Region):null;
            bool pending=session?.PendingCommand!=null&&!session.Busy&&!refreshing;var status=session==null?null:tab==2?session.RankingStatus(session.Pane):session.Status(session.Pane);
            var result=new OnlineTeamsView82{selfId=session?.PlayerId,directory=directory,team=team,chat=tab==0?session?.PresentationSnapshot<SocialMessages82>(SocialPane82.TeamChat):null,
                busy=authorizing||refreshing||(session!=null&&session.Busy),pending=pending,connected=session!=null&&session.PlayerId!=null,unconfigured=unconfigured,tab=tab,regional=regional,regionCode=region?.regionCode??"",ranks=tab==2?session?.PresentationSnapshot<SocialTeamLeaderboard89>(regional?SocialPane82.RegionalTeamRanks:SocialPane82.GlobalTeamRanks):null,countryLoaded=region!=null,countryError=countryError,countryQuery=countryQuery,countryPage=countryPage,modal=modal,confirmationName=confirmationName,
                unavailableReason=(authorizing||refreshing)?"":unconfigured?OnlineTeamsText82.T("OnlineSetup"):gateway&&gateway.Ready&&!gateway.SocialEnabled?OnlineTeamsText82.T("SocialDisabled"):OnlineTeamsText82.T("Unavailable"),
                accessCreate=accessCreate,details=inspectDetails?team:null,detailsOpen=inspectDetails,nameDraft=nameDraft,descriptionDraft=descriptionDraft,nameCount=SocialBackendClient82.TeamTextLength109(nameDraft),badgeId=badgeId,badgeDraft=badgeDraft,inputError=inputError,inputErrorField=inputErrorField,searchQuery=searchQuery,inviteText=team==null?"":team.name+"\n"+team.teamId,mutationError=mutationNotice109,
                status=unconfigured?"":localNotice.Length>0?localNotice:mutationNotice109.Length>0?mutationNotice109:(authorizing||refreshing||status?.state==SocialViewState82.Loading)?"":session==null?OnlineTeamsText82.T("Unavailable"):OnlineTeamsText82.Status(status)};
            double phase=AuthorizationNow;NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsViewBase,(int)Math.Round((phase-viewStarted)*1000));
            FillChatView110(result);double next=AuthorizationNow;NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsViewChat,(int)Math.Round((next-phase)*1000));phase=next;
            if(modal=="invite"||modal=="invitations112"||modal=="invite-detail112")FillInviteView112(result);next=AuthorizationNow;NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsViewInvite,(int)Math.Round((next-phase)*1000));phase=next;
            FillLeaveView113(result);validatedViewRevision=session?.PresentationRevision??-1;NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsViewLeave,(int)Math.Round((AuthorizationNow-phase)*1000));return result;
            } finally { presentation.Dispose(); }
        }
        void Build() {
            if(canvas)return;var root=Rect("Online Teams Canvas82",transform);canvas=root.gameObject.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=65;
#if UNITY_2022_3_OR_NEWER
            canvas.vertexColorAlwaysGammaSpace=true;
#endif
            scaler=root.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ConstantPixelSize;root.gameObject.AddComponent<GraphicRaycaster>();
            safe=Rect("Online Teams safe area",root);safe.gameObject.AddComponent<RectMask2D>();backdrop=Rect("Online Teams backdrop",safe);backdrop.gameObject.AddComponent<CanvasGroup>().blocksRaycasts=false;chrome=Rect("Online Teams chrome",safe);
            viewport=Rect("Online Teams viewport",safe);viewport.gameObject.AddComponent<Image>().color=Color.clear;viewport.gameObject.AddComponent<RectMask2D>();
            scroll=viewport.gameObject.AddComponent<ScrollRect>();scroll.viewport=viewport;scroll.horizontal=false;scroll.vertical=true;scroll.movementType=ScrollRect.MovementType.Clamped;scroll.scrollSensitivity=35;
            content=Rect("Online Teams content",viewport);scroll.content=content;overlay=Rect("Online Teams dialogs",safe);
            // Background art must stay behind the clipped history. The chrome
            // remains above it so the composer and dock receive touches.
            backdrop.SetSiblingIndex(0);viewport.SetSiblingIndex(1);chrome.SetSiblingIndex(2);
        }
        Vector2Int ScreenSize(){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(verificationSize.x>0)return verificationSize;
#endif
            return new Vector2Int(Screen.width,Screen.height);
        }
        Rect SafeRect(){var size=ScreenSize();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(verificationSize.x>0)return hasVerificationSafe?verificationSafe:new Rect(0,0,size.x,size.y);
#endif
            var value=Screen.safeArea;return value.width>0&&value.height>0?value:new Rect(0,0,size.x,size.y);
        }
        float Scale(Rect physical){float value=home?home.CurrentUIScale:Math.Max(1,physical.width/420f);return Math.Max(.1f,Math.Min(value,Math.Min(physical.width/320f,physical.height/568f)));}
        static ulong Mix(ulong value,int part){unchecked{return (value^(uint)part)*1099511628211UL;}}
        static ulong Mix(ulong value,float part)=>Mix(value,part.GetHashCode());
        static ulong Mix(ulong value,string part){unchecked{foreach(char c in part??"")value=(value^c)*1099511628211UL;return Mix(value,(part??"").Length);}}
        internal static ulong FrameHash(OnlineTeamsFrame82 value){
            ulong hash=1469598103934665603UL;
            foreach(float part in new[]{value.width,value.height,value.viewportY,value.viewportHeight,value.artScale})hash=Mix(hash,part);
            hash=Mix(hash,value.r3SliceScale118?1:0);
            foreach(var group in new[]{value.chrome,value.content,value.overlay}){
                hash=Mix(hash,group.width);hash=Mix(hash,group.height);hash=Mix(hash,group.elements.Count);
                foreach(var e in group.elements){
                    hash=Mix(hash,e.id);hash=Mix(hash,e.parent);hash=Mix(hash,e.kind);hash=Mix(hash,e.asset);hash=Mix(hash,e.text);hash=Mix(hash,e.action);hash=Mix(hash,e.label);hash=Mix(hash,e.color);
                    hash=Mix(hash,e.x);hash=Mix(hash,e.y);hash=Mix(hash,e.width);hash=Mix(hash,e.height);
                    hash=Mix(hash,e.fontSize);hash=Mix(hash,e.sliced?1:0);hash=Mix(hash,e.preserveAspect?1:0);hash=Mix(hash,e.shadow?1:0);
                }
            }
            return hash;
        }
        void Reflow(float position,bool preserveTopOffset=false) {
            if(!canvas||!assets)return;
            double started=AuthorizationNow;
            float previousTop=content?Math.Max(0,content.anchoredPosition.y):0;RectTransform previousLeaveScroll;float leaveScroll=modal=="leave113"&&nodes.TryGetValue("leave-body113",out previousLeaveScroll)&&previousLeaveScroll.GetComponent<ScrollRect>()?previousLeaveScroll.GetComponent<ScrollRect>().verticalNormalizedPosition:1;RectTransform previousMailScroll;float mailScroll=modal=="mail-detail111"&&nodes.TryGetValue("mail-detail-scroll",out previousMailScroll)&&previousMailScroll.GetComponent<ScrollRect>()?previousMailScroll.GetComponent<ScrollRect>().verticalNormalizedPosition:1;RectTransform previousInviteScroll;if(nodes.TryGetValue("invite-list",out previousInviteScroll)&&previousInviteScroll.GetComponent<ScrollRect>())inviteScroll112=previousInviteScroll.GetComponent<ScrollRect>().verticalNormalizedPosition;float inviteScroll=modal=="invite"?inviteScroll112:nodes.TryGetValue("invite-incoming-list",out previousInviteScroll)&&previousInviteScroll.GetComponent<ScrollRect>()?previousInviteScroll.GetComponent<ScrollRect>().verticalNormalizedPosition:1;
            bool wasAtBottom=!scroll||scroll.verticalNormalizedPosition<=.02f;
            string focused=EventSystem.current&&EventSystem.current.currentSelectedGameObject?EventSystem.current.currentSelectedGameObject.name:"";
            var physical=SafeRect();float scale=Scale(physical),w=physical.width/scale,h=physical.height/scale;
            float keyboard=Keyboard110||Keyboard112?KeyboardInset110/scale:0;h=Math.Max(1,h-keyboard);double viewStarted=AuthorizationNow;var currentView=View();double layoutStarted=AuthorizationNow;if(currentView.detailsOpen&&!preserveTopOffset)position=1;currentView.mailFontScale111=scale;var next=OnlineTeamsLayout82.Build(w,h,currentView);double hashStarted=AuthorizationNow;ulong signature=FrameHash(next);double phase=AuthorizationNow;NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsView,(int)Math.Round((layoutStarted-viewStarted)*1000));NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsLayout,(int)Math.Round((hashStarted-layoutStarted)*1000));NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsHash,(int)Math.Round((phase-hashStarted)*1000));NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsModel,(int)Math.Round((phase-started)*1000));
            if(frame!=null&&signature==renderedFrame&&lastSize==ScreenSize()&&lastSafe==Screen.safeArea&&Math.Abs(lastScale-scale)<.01f){if(!preserveTopOffset)scroll.verticalNormalizedPosition=position;revision=GameLocale.Revision;renderedSession=session;renderedPresentationRevision=validatedViewRevision;renderedBaseChat=tab==0&&!mail110&&!giftsOpen110&&!ownedMailOpen111&&modal.Length==0&&!accessCreate&&!inspectDetails;NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsFrameReuse,(int)Math.Round((AuthorizationNow-started)*1000));return;}
            if((modal=="badge"||modal=="invite")&&EventSystem.current&&EventSystem.current.currentSelectedGameObject){var oldInput=EventSystem.current.currentSelectedGameObject.GetComponent<InputField>();if(oldInput)oldInput.DeactivateInputField();}
            foreach(var root in new[]{backdrop,chrome,content,overlay})foreach(Transform child in root.Cast<Transform>().ToArray()){child.gameObject.SetActive(false);if(Application.isPlaying)Destroy(child.gameObject);else DestroyImmediate(child.gameObject);}nodes.Clear();NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsClear,(int)Math.Round((AuthorizationNow-phase)*1000));phase=AuthorizationNow;
            scaler.scaleFactor=scale;canvas.scaleFactor=scale;Place(safe,physical.x/scale,(ScreenSize().y-physical.yMax)/scale,w,h);frame=next;renderedFrame=signature;
            Place(backdrop,0,0,w,h);Place(chrome,0,0,w,h);Place(overlay,0,0,w,h);Place(viewport,0,frame.viewportY,w,frame.viewportHeight);Place(content,0,0,w,frame.content.height);
            Render(frame.chrome,chrome);Render(frame.content,content);Render(frame.overlay,overlay);RectTransform leaveMotionNode;if(modal=="leave113"&&nodes.TryGetValue("leave-motion113",out leaveMotionNode)){var motion=leaveMotionNode.gameObject.AddComponent<HeartOfTheRain.App.TeamsLifecycle.TeamsLifecycleMotion113>();motion.Begin((float)Math.Max(0,AuthorizationNow-leaveMotionAt113),leaveClosing113,home&&home.State.reduceMotion);}RectTransform newLeaveScroll;if(nodes.TryGetValue("leave-body113",out newLeaveScroll)&&newLeaveScroll.GetComponent<ScrollRect>())newLeaveScroll.GetComponent<ScrollRect>().verticalNormalizedPosition=leaveScroll;RectTransform newMailScroll;if(nodes.TryGetValue("mail-detail-scroll",out newMailScroll)&&newMailScroll.GetComponent<ScrollRect>())newMailScroll.GetComponent<ScrollRect>().verticalNormalizedPosition=mailScroll;RectTransform newInviteScroll;if(nodes.TryGetValue(modal=="invite"?"invite-list":"invite-incoming-list",out newInviteScroll)&&newInviteScroll.GetComponent<ScrollRect>())newInviteScroll.GetComponent<ScrollRect>().verticalNormalizedPosition=inviteScroll;
            bool blocked=modal.Length>0&&modal!="compose110";foreach(var root in new[]{chrome,viewport}){var group=root.GetComponent<CanvasGroup>();if(!group)group=root.gameObject.AddComponent<CanvasGroup>();group.interactable=!blocked;group.blocksRaycasts=!blocked;}scroll.enabled=!blocked;
            MainNavigationFeedback.Bind(nodes,home&&home.State.reduceMotion);NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsRender,(int)Math.Round((AuthorizationNow-phase)*1000));phase=AuthorizationNow;Canvas.ForceUpdateCanvases();NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsCanvas,(int)Math.Round((AuthorizationNow-phase)*1000));
            float range=Math.Max(0,frame.content.height-frame.viewportHeight);
            bool follow=tab==0&&!giftsOpen110&&!mail110&&!browsingOlder&&(modal.Length==0||modal=="compose110")&&currentView.team?.isMember==true&&(!preserveTopOffset||wasAtBottom);
            scroll.verticalNormalizedPosition=follow?0:preserveTopOffset?(range<=.01f?1:1-Mathf.Clamp01(previousTop/range)):position;
            layoutFrame=Time.frameCount;lastSize=ScreenSize();lastSafe=Screen.safeArea;lastScale=scale;revision=GameLocale.Revision;renderedSession=session;renderedPresentationRevision=validatedViewRevision;renderedBaseChat=tab==0&&!mail110&&!giftsOpen110&&!ownedMailOpen111&&modal.Length==0&&!accessCreate&&!inspectDetails;
            string target=modal=="leave113"?(focused.Length>0&&nodes.ContainsKey(focused)&&nodes[focused].IsChildOf(overlay)?focused:"leave-cancel113"):modal=="mail-detail111"?"mail-close":modal=="badge"?"online-badge-confirm":modal=="invite"?(focused=="invite-search-input"?focused:"invite-close"):modal=="invitations112"||modal=="invite-detail112"?"invite-close":focusAfter109.Length>0?focusAfter109:focused;focusAfter109="";
            RectTransform selected;if(target.Length>0&&nodes.TryGetValue(target,out selected)&&EventSystem.current&&(modal.Length==0||selected.IsChildOf(overlay))){
                EventSystem.current.SetSelectedGameObject(selected.gameObject);
            }
            int elapsed=(int)Math.Round((AuthorizationNow-started)*1000);if(elapsed>16)NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsReflow,elapsed);
        }
        void Render(HomeFrame model,RectTransform parentRoot) {
            foreach(var e in model.elements) {
                var parent=string.IsNullOrEmpty(e.parent)?e.kind=="cover109"&&parentRoot==chrome?backdrop:parentRoot:nodes[e.parent];var rt=Rect(e.id,parent);Place(rt,e.x,e.y,e.width,e.height);nodes[e.id]=rt;
                if(e.kind=="group") {
                    if(string.IsNullOrEmpty(e.action))continue;var im=rt.gameObject.AddComponent<Image>();im.color=Color.clear;var button=rt.gameObject.AddComponent<Button>();button.targetGraphic=im;button.transition=Selectable.Transition.None;button.interactable=e.action!="disabled";
                    string action=e.id=="online-compose-send"?"send":e.action;button.onClick.AddListener(()=>Request(action));var label=rt.gameObject.AddComponent<HomeControlLabel>();label.action=action;label.label=e.id=="online-compose-send"?HeartOfTheRain.App.TeamsSocial.TeamsSocialText110.T("send"):HeartOfTheRain.App.TeamsSocial.TeamsSocialLayout110.PlainText118(e.label);
                } else if(e.kind=="badgegrid109"||e.kind=="mailbody111"||e.kind=="invitebody112") {
                    rt.gameObject.AddComponent<Image>().color=Color.clear;rt.gameObject.AddComponent<RectMask2D>();var grid=rt.gameObject.AddComponent<ScrollRect>();grid.viewport=rt;grid.horizontal=false;grid.vertical=true;grid.movementType=ScrollRect.MovementType.Clamped;grid.scrollSensitivity=30;
                } else if(e.kind=="cover109") {
                    var sprite=assets.Find(e.asset);var image=rt.gameObject.AddComponent<RawImage>();image.texture=sprite?sprite.texture:null;image.color=Color.white;image.raycastTarget=false;
                } else if(e.kind=="input") {
                    rt.gameObject.AddComponent<RectMask2D>();var im=rt.gameObject.AddComponent<Image>();im.color=Color.clear;var input=rt.gameObject.AddComponent<InputField>();input.targetGraphic=im;
                    bool message=e.id=="online-message-input",name=e.id=="online-team-name-input",country=e.id=="country-code-input",search=e.id=="online-team-search-input",inviteSearch=e.id=="invite-search-input";input.characterLimit=country?80:message?2000:name?64:search||inviteSearch?128:320;input.lineType=message?InputField.LineType.MultiLineNewline:name||country||search||inviteSearch?InputField.LineType.SingleLine:InputField.LineType.MultiLineSubmit;input.interactable=e.action!="disabled";
                    var tr=Rect("Input text",rt);Place(tr,0,0,e.width,e.height);var text=tr.gameObject.AddComponent<Text>();text.font=BodyFont;text.fontSize=e.fontSize;text.color=ColorOf(e.color);text.alignment=TextAnchor.UpperLeft;text.supportRichText=false;text.raycastTarget=false;input.textComponent=text;
                    var ph=Rect("Placeholder",rt);Place(ph,0,0,e.width,e.height);var placeholder=ph.gameObject.AddComponent<Text>();placeholder.font=BodyFont;placeholder.fontSize=e.fontSize;placeholder.text=e.label;placeholder.supportRichText=false;placeholder.raycastTarget=false;placeholder.color=ColorOf("#73818B");input.placeholder=placeholder;
                    input.text=country?countryDraft:message?messageDraft:name?nameDraft:search?searchDraft:inviteSearch?inviteSearch112:descriptionDraft;input.onValueChanged.AddListener(value=>{if(country)countryDraft=value;else if(message){messageDraft=value;UpdateComposer110();}else if(name){nameDraft=value;RectTransform counter;if(nodes.TryGetValue("online-name-count",out counter))counter.GetComponent<Text>().text=SocialBackendClient82.TeamTextLength109(value)+" / 32";}else if(search)searchDraft=value;else if(inviteSearch)ChangeInviteSearch112(value);else descriptionDraft=value;});
                    var focus=rt.gameObject.AddComponent<TeamsAccessInputFocus109>();focus.owner=this;
                } else if(e.kind=="leavename113") {
                    var text=rt.gameObject.AddComponent<Text>();text.font=BodyFont;text.fontSize=e.fontSize;text.color=ColorOf(e.color);text.alignment=TextAnchor.UpperLeft;text.supportRichText=false;text.raycastTarget=false;text.horizontalOverflow=HorizontalWrapMode.Wrap;text.verticalOverflow=VerticalWrapMode.Truncate;
                    text.text=HeartOfTheRain.App.TeamsLifecycle.TeamsLifecycleLayout113.TeamNameDisplay113(text,e.text,e.width,e.height);var readable=rt.gameObject.AddComponent<HomeControlLabel>();readable.label=HeartOfTheRain.App.TeamsSocial.TeamsSocialLayout110.PlainText118(e.text);
                } else if(e.kind=="chatbody110") {
                    var text=rt.gameObject.AddComponent<Text>();text.font=BodyFont;text.fontSize=e.fontSize;text.text=HeartOfTheRain.App.TeamsSocial.TeamsSocialLayout110.DisplayText110(e.text,BodyFont);text.color=ColorOf(e.color);text.alignment=TextAnchor.UpperLeft;text.supportRichText=false;text.raycastTarget=false;text.horizontalOverflow=HorizontalWrapMode.Wrap;text.verticalOverflow=VerticalWrapMode.Truncate;var readable=rt.gameObject.AddComponent<HomeControlLabel>();readable.label=HeartOfTheRain.App.TeamsSocial.TeamsSocialLayout110.PlainText118(e.text);
                } else if(e.kind=="chatname110") {
                    var text=rt.gameObject.AddComponent<Text>();text.font=BoldFont;text.fontSize=e.fontSize;text.text=HeartOfTheRain.App.TeamsSocial.TeamsSocialLayout110.PlainText118(e.text);text.color=ColorOf(e.color);text.alignment=TextAnchor.MiddleLeft;text.supportRichText=false;text.raycastTarget=false;text.horizontalOverflow=HorizontalWrapMode.Overflow;text.verticalOverflow=VerticalWrapMode.Truncate;
                    var settings=text.GetGenerationSettings(new Vector2(e.width,e.height));settings.horizontalOverflow=HorizontalWrapMode.Overflow;var generator=new TextGenerator();if(generator.GetPreferredWidth(text.text,settings)>e.width){string value=text.text;while(value.Length>0&&generator.GetPreferredWidth(value+"…",settings)>e.width)value=value.Substring(0,value.Length-(char.IsLowSurrogate(value[value.Length-1])&&value.Length>1?2:1));text.text=value+"…";}
                } else if(e.kind=="paragraph") {
                    var text=rt.gameObject.AddComponent<Text>();text.font=BodyFont;text.fontSize=e.fontSize;text.text=HeartOfTheRain.App.TeamsSocial.TeamsSocialLayout110.PlainText118(e.text);text.color=ColorOf(e.color);text.alignment=TextAnchor.UpperLeft;text.supportRichText=false;text.raycastTarget=false;text.horizontalOverflow=HorizontalWrapMode.Overflow;text.verticalOverflow=VerticalWrapMode.Truncate;
                } else if(e.kind=="text"||e.kind=="lefttext") {
                    var text=rt.gameObject.AddComponent<Text>();text.font=BoldFont;text.text=HeartOfTheRain.App.TeamsSocial.TeamsSocialLayout110.PlainText118(e.text);text.color=ColorOf(e.color);text.fontSize=e.fontSize;text.supportRichText=false;text.raycastTarget=false;text.alignment=e.kind=="lefttext"?TextAnchor.MiddleLeft:TextAnchor.MiddleCenter;text.horizontalOverflow=HorizontalWrapMode.Overflow;text.verticalOverflow=VerticalWrapMode.Truncate;LabelFit.Apply(text,e.width,e.height,9);if(e.id=="leave-title113"||e.id=="leave-toast113"){var semantic=rt.gameObject.AddComponent<HomeControlLabel>();semantic.label=text.text;}if(e.shadow){var shadow=rt.gameObject.AddComponent<Shadow>();shadow.effectColor=new Color(0,.02f,.05f,.8f);shadow.effectDistance=new Vector2(0,-1);}
                } else {
                    var image=rt.gameObject.AddComponent<Image>();if(e.kind!="color")image.sprite=assets.Find(e.asset);image.type=e.sliced?Image.Type.Sliced:Image.Type.Simple;image.pixelsPerUnitMultiplier=e.sliced?(e.asset!=null&&e.asset.StartsWith("TC_",StringComparison.Ordinal)&&assets.social?assets.social.SliceMultiplier(frame.artScale):e.asset!=null&&e.asset.StartsWith("TA_",StringComparison.Ordinal)&&assets.access?assets.access.SliceMultiplier(e.asset,frame.artScale):4):1;image.color=ColorOf(e.color);image.raycastTarget=false;image.preserveAspect=e.preserveAspect;SpriteFit.Center(image);
                }
            }
            foreach(var e in model.elements)if(e.id=="online-teams-background"||e.id=="online-modal-shade"||e.id=="country-shade")PageBackdrop90.Fill(nodes[e.id].GetComponent<MaskableGraphic>(),canvas);
            foreach(var e in model.elements)if(e.kind=="cover109")PageBackdrop90.Cover(nodes[e.id].GetComponent<RawImage>());else if(e.kind=="badgegrid109"||e.kind=="mailbody111"||e.kind=="invitebody112")nodes[e.id].GetComponent<ScrollRect>().content=nodes[e.label];
            foreach(var e in model.elements)if(!string.IsNullOrEmpty(e.action)&&e.action!="disabled"&&!e.id.StartsWith("nav-",StringComparison.Ordinal)) {
                var graphics=nodes.Where(pair=>pair.Key.StartsWith(e.id+"-",StringComparison.Ordinal)).Select(pair=>pair.Value.GetComponent<Graphic>()).Where(value=>value).ToArray();
                nodes[e.id].gameObject.AddComponent<PreLevelButtonFeedback>().Configure(graphics,home&&home.State.reduceMotion);
            }
        }
        static RectTransform Rect(string name,Transform parent){var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);return (RectTransform)go.transform;}
        static void Place(RectTransform value,float x,float y,float w,float h){value.anchorMin=value.anchorMax=value.pivot=new Vector2(0,1);value.anchoredPosition=new Vector2(x,-y);value.sizeDelta=new Vector2(w,h);}
        static Color ColorOf(string text){Color value;return ColorUtility.TryParseHtmlString(text,out value)?value:Color.white;}
        public void RevealInput109(RectTransform input){if(!input||!scroll||!viewport||!content||!input.IsChildOf(content))return;Canvas.ForceUpdateCanvases();var corners=new Vector3[4];input.GetWorldCorners(corners);var upper=viewport.InverseTransformPoint(corners[1]);var lower=viewport.InverseTransformPoint(corners[0]);float reserve=0;if(TouchScreenKeyboard.visible)reserve=TouchScreenKeyboard.area.height>0?TouchScreenKeyboard.area.height/Math.Max(.1f,canvas.scaleFactor):Screen.height*.35f/Math.Max(.1f,canvas.scaleFactor);float move=lower.y<viewport.rect.yMin+reserve+12?viewport.rect.yMin+reserve+12-lower.y:upper.y>viewport.rect.yMax-8?viewport.rect.yMax-8-upper.y:0;float range=Math.Max(0,content.rect.height-viewport.rect.height);if(range>0&&Math.Abs(move)>.1f){content.anchoredPosition+=new Vector2(0,move);scroll.verticalNormalizedPosition=Mathf.Clamp01(1-content.anchoredPosition.y/range);}}
        long observedRevision=-2;float observedPosition=-1;int observedLayout=-1;
        void LateUpdate(){if(Time.frameCount>layoutFrame&&(session==null||session.PresentationRevision!=observedRevision||scroll.verticalNormalizedPosition!=observedPosition||layoutFrame!=observedLayout))ObserveRead();if(TouchScreenKeyboard.visible&&EventSystem.current&&EventSystem.current.currentSelectedGameObject){var input=EventSystem.current.currentSelectedGameObject.GetComponent<InputField>();if(input&&input.isFocused)RevealInput109(input.GetComponent<RectTransform>());}}
        bool ObserveRead(){
            observedRevision=session?.PresentationRevision??-1;observedPosition=scroll?scroll.verticalNormalizedPosition:-1;observedLayout=layoutFrame;
            if(!IsVisible||tab!=0||mail110||modal.Length>0||refreshing||session==null||browsingOlder){session?.SetMessageViewportAtLatest(false);observedRevision=-2;return false;}
            var chat=session.PresentationSnapshot<SocialMessages82>(SocialPane82.TeamChat);var last=chat?.messages?.LastOrDefault();
            // An empty chat is already at its latest position. Keep polling so
            // the first message or a teammate's life request can arrive.
            bool visible=chat!=null&&!chat.hasNewer&&(last==null||OnlineSocialSurface82.MessageEndVisible(scroll,nodes,last.messageId));
            return session.ObserveVisibleMessages(last?.sequence??0,visible);
        }
        void OnDestroy(){CancelFeedback110();CancelMailFeedback111();closed=true;authorizationRequest++;authorizing=false;loadGeneration++;if(gateway){gateway.IdentityChanged-=IdentityChanged;gateway.Changed-=GatewayChanged;}if(session!=null){session.Changed-=Changed;if(ownsSession)session.Dispose();session=null;}}
    }
    public sealed class TeamsAccessInputFocus109:MonoBehaviour,ISelectHandler {public OnlineTeamsPage82 owner;public void OnSelect(BaseEventData value){if(owner)owner.RevealInput109((RectTransform)transform);}}
}

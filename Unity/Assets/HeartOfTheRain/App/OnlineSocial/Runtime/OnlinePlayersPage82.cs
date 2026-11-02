using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Leaderboard;
using HeartOfTheRain.App.Teams;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Journey;
using HeartOfTheRain.App.Localization;

namespace HeartOfTheRain.App.OnlineSocial
{
    [DisallowMultipleComponent]public sealed class OnlinePlayersPage82:MonoBehaviour {
        HomePage home;LeaderboardAssets assets;ServerGameSession gateway;SocialPageSession82 session;OnlineSocialSurface82 surface;Action<IEnumerator> dispatcher;
        bool owns=true,closed,refreshing,needsRefresh,writing,direct,reporting,browsingOlder;int layoutFrame;int tab,offset,generation,refreshToken,locale=-1;Vector2Int size;Rect safe;float scale;
        string peerId,peerName="",code="",draft="",modal="",modalName="",discardId,reportId,reportKind,notice="",writeNotice="",submittedDirect="";OnlineTeamsFrame82 frame;ulong renderedFrame;long observedRevision=-2;float observedPosition=-1;int observedLayout=-1;
        bool authorizing;double authorizationRetryAt;long authorizationRequest;string socialOwner;LeaderboardMotion115 motion115,tabMotion115;
        bool regional,teamRanking;int countryPage;string countryDraft="",countryQuery="",countryError="";
        SocialProfile82 ownProfile;string friendsAfter="",requestsAfter="",blocksAfter="";bool searchOpen115,friendsRank115,searchWriting115,friendSecondary118,privacyMenuOpen118;int friendsRankOffset115;string searchQuery115="",searchCursor115="",searchError115="";
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        Vector2Int reviewSize;
        public Canvas VerificationCanvas=>surface?.canvas;public OnlineTeamsFrame82 VerificationFrame=>frame;
        public IReadOnlyDictionary<string,RectTransform> VerificationNodes=>surface.nodes;
        public bool VerificationPending=>authorizing||refreshing||needsRefresh||(session!=null&&session.Busy);
        public SocialPageSession82 VerificationSession=>session;
        public string VerificationLastCommand{get;private set;}
        public void ConfigureForVerification(LeaderboardAssets art,SocialPageSession82 authenticated,Action<IEnumerator> dispatch){assets=art;session=authenticated;dispatcher=dispatch;owns=false;session.Changed+=Changed;}
        public void VerificationViewport(int w,int h){reviewSize=new Vector2Int(w,h);if(IsVisible)Render(false);}
        public void VerificationPump()=>Pump();
        public bool VerificationObserveRead()=>ObserveRead();
#endif
        public bool IsVisible=>surface!=null&&surface.canvas&&surface.canvas.gameObject.activeSelf;
        public void Configure(HomePage owner,LeaderboardAssets art,ServerGameSession server){home=owner;assets=art;if(gateway!=server){if(gateway){gateway.IdentityChanged-=IdentityChanged;gateway.Changed-=GatewayChanged;}gateway=server;if(gateway){gateway.IdentityChanged+=IdentityChanged;gateway.Changed+=GatewayChanged;}}TrySession();}
        void Dispatch(IEnumerator routine){if(dispatcher!=null)dispatcher(routine);else StartCoroutine(routine);}
        void TrySession(){if(session!=null||closed||!gateway||!gateway.SocialEnabled)return;ServerAuthorizedContext access;if(!gateway.TryGetReadContext(out access))return;HeartOfTheRain.App.OnlineIdentity.IProtectedSessionStore82 store=null;try{store=gateway.CreateProtectedSocialStore();session=new SocialPageSession82(gateway.CreateSocialClient(Dispatch,store),store,()=>gateway?gateway.SessionGeneration:long.MinValue);session.Changed+=Changed;socialOwner=gateway.PlayerId;needsRefresh=IsVisible;}catch(Exception){store?.Dispose();notice=OnlinePlayersText82.T("Unavailable");}}
        static double AuthorizationNow=>System.Diagnostics.Stopwatch.GetTimestamp()/(double)System.Diagnostics.Stopwatch.Frequency;
        bool EnsureAuthorizedSocial(){
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
                    if(session!=null){session.Changed-=Changed;if(owns)session.Dispose();session=null;}
                    notice="";TrySession();needsRefresh=IsVisible&&session!=null;
                }else{needsRefresh=false;notice=OnlinePlayersText82.T("Unavailable");}
                if(IsVisible)Render(true);
            });
            return false;
        }
        void GatewayChanged(){TrySession();if(IsVisible)Render(true);}
        void IdentityChanged(){bool same=gateway&&!gateway.AccountBlocked&&gateway.PlayerId==socialOwner;generation++;refreshing=needsRefresh=writing=searchWriting115=false;ownProfile=null;countryDraft=countryError="";
            if(!same){modal="";peerId=null;direct=false;browsingOlder=false;peerName=code=draft="";searchOpen115=searchWriting115=friendSecondary118=privacyMenuOpen118=false;searchQuery115=searchCursor115=searchError115="";}
            if(session!=null){session.Changed-=Changed;if(owns)session.Dispose();session=null;}if(IsVisible)Render(false);}

        void Changed(){if(closed)return;
            // A refused write left nothing to check. Say why, and keep a refused message's text.
            string refused=session?.TakeWriteRefusal();if(refused!=null){writeNotice=OnlineTeamsText82.Refusal(refused);if(submittedDirect.Length>0&&draft.Length==0)draft=submittedDirect;}
            if(writing&&session!=null&&!session.Busy){writing=false;if(refused==null&&session.PendingCommand==null)submittedDirect="";needsRefresh=session.PendingCommand==null;if(searchWriting115){if(session.PendingCommand==null&&session.Status(SocialPane82.Requests).state!=SocialViewState82.Ready&&session.Status(SocialPane82.Requests).state!=SocialViewState82.NotLoaded)searchError115=refused!=null?writeNotice:OnlinePlayersText82.T("Rejected");searchWriting115=false;}if(reporting){if(needsRefresh&&refused==null)notice=OnlinePlayersText82.T("ReportReceived");needsRefresh=false;reporting=false;}}if(IsVisible&&(session==null||!session.ReadInFlight))Render(true);}
        bool HasSelfAvatar115(){return FindArt115("SELF_AVATAR115")&&FindArt115("SELF_FRAME115");}
        Sprite FindArt115(string id){
            if(id=="SELF_AVATAR115"||id=="SELF_FRAME115"){
                if(!home)return null;
                var profile=home.GetComponent<HeartOfTheRain.App.Profile.ProfilePage>();
                var data=profile?profile.Snapshot:null;
                var art=Resources.Load<HeartOfTheRain.App.Profile.ProfileAssets>("HeartOfTheRainProfile/Config");
                if(data==null||!art)return null;
                return art.Find(id=="SELF_AVATAR115"?"Avatar_"+data.avatarId:"Frame"+data.frameId);
            }
            return assets?assets.Find(id):null;
        }
        void AnimatePage115(){if(surface==null||!surface.canvas)return;var go=surface.canvas.gameObject;var group=go.GetComponent<CanvasGroup>();if(!group)group=go.AddComponent<CanvasGroup>();if(!motion115)motion115=go.AddComponent<LeaderboardMotion115>();motion115.Begin(new[]{group},home&&home.State.reduceMotion ? 0.12f : 0.18f);}
        void AnimateTab115(string action){if(surface==null||!surface.canvas)return;string id=action=="primary-friends115"?"online-primary-friends":action=="primary-teams115"?"online-primary-teams":"online-primary-players";var targets=new System.Collections.Generic.List<CanvasGroup>();foreach(string suffix in new[]{"-selected","-label"}){RectTransform node;if(surface.nodes.TryGetValue(id+suffix,out node)&&node){var group=node.GetComponent<CanvasGroup>();if(!group)group=node.gameObject.AddComponent<CanvasGroup>();targets.Add(group);}}if(targets.Count==0)return;if(!tabMotion115)tabMotion115=surface.canvas.gameObject.AddComponent<LeaderboardMotion115>();tabMotion115.Begin(targets.ToArray(),home&&home.State.reduceMotion ? 0.12f : 0.14f);}
        void Build(){if(surface!=null)return;surface=new OnlineSocialSurface82(transform,FindArt115,assets.journey.home.regularFont,assets.journey.home.boldFont,Request,id=>id=="online-player-code-input"?code:id=="country-code-input"?countryDraft:draft,(id,value)=>{if(id=="online-player-code-input")code=value;else if(id=="country-code-input")countryDraft=value;else draft=value;});}
        public void Show(){if(closed||!assets)return;if(home){var flow=home.GetComponent<HomeLevelFlow>();var pre=home.GetComponent<PreLevelModal>();if((flow&&flow.Playing)||(pre&&pre.IsVisible))return;var journey=home.GetComponent<JourneyPage>();if(journey)journey.Hide(false);var teams=home.GetComponent<TeamsPage>();if(teams)teams.Hide(false);}
            Build();surface.canvas.gameObject.SetActive(true);if(home)home.SetPresentation(false,false);TrySession();needsRefresh=session!=null;Render(false);AnimatePage115();Pump();}
        public void ShowPlayer(string id,bool openDirect=false){if(!HeartOfTheRain.App.OnlineIdentity.IdentityProtocol82.Id(id))return;Show();if(!IsVisible)return;generation++;refreshing=false;session?.Hide();if(session==null&&gateway&&gateway.Ready)socialOwner=gateway.PlayerId;peerId=id;peerName="";direct=openDirect;browsingOlder=false;modal=openDirect?"":"profile";needsRefresh=true;Render(false);Pump();}
        public void Hide(bool showHome=true){if(!IsVisible)return;generation++;refreshing=needsRefresh=false;modal="";draft=code=writeNotice=submittedDirect="";searchOpen115=friendSecondary118=privacyMenuOpen118=false;session?.Hide();surface.canvas.gameObject.SetActive(false);if(showHome&&home)home.SetPresentation(true,true);}
        void Update(){if(!IsVisible)return;Pump();if(size!=ScreenSize()||safe!=Screen.safeArea||locale!=GameLocale.Revision)Render(true);
#if ENABLE_INPUT_SYSTEM && !ENABLE_LEGACY_INPUT_MANAGER
            bool back=UnityEngine.InputSystem.Keyboard.current!=null&&UnityEngine.InputSystem.Keyboard.current.escapeKey.wasPressedThisFrame;
#else
            bool back=Input.GetKeyDown(KeyCode.Escape);
#endif
            if(back){if(modal.Length>0)Request("cancel");else if(direct)Request("back");else if(searchOpen115)Request("search-back115");else if(friendSecondary118||tab==2||tab==3)Request("friends-secondary-back118");else if(privacyMenuOpen118)Request("privacy-close118");else Hide();}}
        void Pump(){if(closed||!IsVisible)return;TrySession();session?.FailStalledRead();if(!EnsureAuthorizedSocial()||session==null)return;if(needsRefresh&&!refreshing&&!session.Busy){needsRefresh=false;Dispatch(Refresh(++generation));}if(!refreshing&&modal.Length==0)session.Tick();}
        SocialPane82 Pane=>direct?SocialPane82.DirectChat:modal=="profile"?SocialPane82.PlayerProfile:tab==0?(teamRanking?(regional?SocialPane82.RegionalTeamRanks115:SocialPane82.GlobalTeamRanks115):(regional?SocialPane82.RegionalRanks115:SocialPane82.GlobalRanks115)):tab==1?(searchOpen115?SocialPane82.PlayerSearch115:friendsRank115?SocialPane82.FriendsRanks:SocialPane82.Friends):tab==2?SocialPane82.Requests:SocialPane82.Blocks;
        IEnumerator Refresh(int token){if(closed||token!=generation||!IsVisible)yield break;var current=session;refreshToken=token;refreshing=true;notice="";Render(true);try{
            if(current==null)yield break;current.Show(Pane);
            if(direct||modal=="profile"){
                if(peerId!=current.PlayerId){if(!current.RefreshRelationship(peerId))yield break;while(current.Busy)yield return null;
                    if(token!=generation||!IsVisible||session!=current)yield break;
                    var relationship=current.Snapshot<SocialRelationship82>(SocialPane82.Relationship);
                    if(direct&&relationship?.state!="Friends"){direct=false;modal="profile";}}
                if(!current.RefreshProfile(peerId))yield break;while(current.Busy)yield return null;
                if(token!=generation||!IsVisible||session!=current)yield break;
                var profile=current.Snapshot<SocialProfile82>(SocialPane82.PlayerProfile);if(profile?.playerId==peerId)peerName=profile.displayName;
                if(direct&&current.OpenDirect(peerId))while(current.Busy)yield return null;
            }else if(tab==0){
                // Global standings need nothing from the region read, so show them first.
                if(!regional&&(teamRanking?current.RefreshTeamRanks115("global",offset):current.RefreshRanks115("global",offset)))while(current.Busy)yield return null;
                if(token!=generation||session!=current||!IsVisible)yield break;
                if(current.RefreshRegion())while(current.Busy)yield return null;
                if(token!=generation||session!=current||!IsVisible)yield break;
                if(current.RefreshProfile(current.PlayerId))while(current.Busy)yield return null;
                if(token!=generation||session!=current||!IsVisible)yield break;ownProfile=current.Snapshot<SocialProfile82>(SocialPane82.PlayerProfile);
                if(regional&&string.IsNullOrEmpty(current.Snapshot<SocialRegion89>(SocialPane82.Region)?.regionCode)){if(current.Status(SocialPane82.Region).state==SocialViewState82.Ready)regional=false;else yield break;}
                if(regional&&(teamRanking?current.RefreshTeamRanks115("regional",offset):current.RefreshRanks115("regional",offset)))while(current.Busy)yield return null;
            }
            else if(tab==1){if(searchOpen115?current.SearchPlayers115(searchQuery115,searchCursor115):friendsRank115?current.RefreshRanks("friends",friendsRankOffset115):current.RefreshFriends(friendsAfter))while(current.Busy)yield return null;}
            else if(tab==2){if(current.RefreshRequests(requestsAfter))while(current.Busy)yield return null;}
            else if(current.RefreshBlocks(blocksAfter))while(current.Busy)yield return null;
        }finally{if(refreshToken==token)refreshing=false;if(!closed&&token==generation&&IsVisible)Render(true);}}
        // A read is replaceable, so navigation may supersede it. Writes keep their lock.
        bool YieldReads(){if(session.Busy&&!session.ReadInFlight)return false;generation++;refreshing=false;return session.YieldReadForForeground();}
        string Command(){var id=Guid.NewGuid().ToString("N");
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            VerificationLastCommand=id;
#endif
            return id;}
        void Write(Func<bool> operation){if(session==null||refreshing||session.Busy)return;if(session.PendingCommand!=null){notice=OnlinePlayersText82.T("Pending");Render(true);return;}writing=true;writeNotice="";if(!operation())writing=false;}
        public void Request(string action){if(!IsVisible||string.IsNullOrEmpty(action)||action=="disabled")return;writeNotice="";if(modal.Length>0&&!new[]{"cancel","send","confirm","add","open-direct","remove","block","report-profile","cancel-country","save-country"}.Contains(action)&&!CountryRegion89.DialogAction(action)&&!action.StartsWith("accept:",StringComparison.Ordinal)&&!action.StartsWith("cancel-request:",StringComparison.Ordinal))return;
            if(action=="home"){Hide();return;}if(action=="journey"||action=="teams"||action=="shop"){Hide(false);if(home)home.NavigationRequested.Invoke(action);return;}if(action=="leaderboard")return;
            // Page-only navigation remains available in honest offline views.
            // These routes never issue friend mutations or synthesize roster data.
            if(action=="privacy-open118"&&tab==0){privacyMenuOpen118=true;Render(false);return;}
            if(action=="privacy-close118"){privacyMenuOpen118=false;Render(false);return;}
            if(action=="friends-secondary118"&&tab==1){friendSecondary118=true;searchOpen115=false;Render(false);return;}
            if(action=="friends-secondary-back118"){
                if(tab==2||tab==3){tab=1;friendSecondary118=false;needsRefresh=session!=null;Render(false);Pump();}
                else {friendSecondary118=false;Render(false);}return;
            }
            if(action=="friends-open-search118"&&tab==1){friendSecondary118=friendsRank115=false;searchOpen115=true;code=searchQuery115=searchCursor115=searchError115="";needsRefresh=false;Render(false);return;}
            if(action=="search-back115"&&tab==1&&searchOpen115){if(refreshing||(session!=null&&session.Busy))return;searchOpen115=false;code=searchQuery115=searchCursor115=searchError115="";needsRefresh=session!=null;Render(false);Pump();return;}
            if(action=="friends-show-requests118"||action=="friends-show-blocked118"){
                tab=action=="friends-show-requests118"?2:3;friendSecondary118=searchOpen115=false;
                needsRefresh=session!=null;Render(false);Pump();return;
            }
            // Without a configured service, the same tabs still navigate
            // between honest unavailable states. No read or write is issued.
            if(session==null&&(action=="primary-friends115"||action=="primary-players115"||action=="primary-teams115")){
                searchOpen115=friendSecondary118=privacyMenuOpen118=false;
                tab=action=="primary-friends115"?1:0;teamRanking=action=="primary-teams115";
                direct=false;offset=0;needsRefresh=false;Render(false);AnimateTab115(action);return;
            }
            if(action=="cancel"){bool profile=modal=="profile";modal="";if(session!=null)session.Show(Pane);if(profile)needsRefresh=true;Render(true);Pump();return;}if(action=="retry")authorizationRetryAt=0;if(!EnsureAuthorizedSocial())return;if(session==null){if(action=="retry"){TrySession();needsRefresh=session!=null;Pump();}return;}
            if(action=="retry"){friendsAfter=requestsAfter=blocksAfter="";searchCursor115=searchError115="";offset=0;needsRefresh=true;Pump();return;}if(action=="check"){writing=true;if(!session.ReconcilePending())writing=false;return;}if(action=="resume"){writing=true;if(!session.ResumePending())writing=false;return;}
            if(action=="primary-friends115"||action=="primary-players115"||action=="primary-teams115"){if(!YieldReads())return;searchOpen115=friendSecondary118=privacyMenuOpen118=false;tab=action=="primary-friends115"?1:0;teamRanking=action=="primary-teams115";direct=false;offset=0;friendsAfter=requestsAfter=blocksAfter="";needsRefresh=true;Render(false);AnimateTab115(action);Pump();return;}
            if(action=="ranks-first115"){if(session.Busy||refreshing)return;offset=0;needsRefresh=true;Render(false);Pump();return;}
            if(action=="scope-global"||action=="scope-regional"||action=="rank-players"||action=="rank-teams"){
                if(!YieldReads())return;if(action=="scope-regional"&&string.IsNullOrEmpty(session.Snapshot<SocialRegion89>(SocialPane82.Region)?.regionCode))return;if(action=="scope-global"||action=="scope-regional")regional=action=="scope-regional";else teamRanking=action=="rank-teams";
                offset=0;needsRefresh=true;Render(false);Pump();return;
            }
            if(action=="consent"){if(ownProfile!=null)Write(()=>session.SetLeaderboardConsent(Command(),!ownProfile.leaderboardOptIn));return;}
            if(action=="forget"){var pending=session.PendingCommand;if(pending==null)return;discardId=pending.commandId;modal="forget";}
            else if(action=="confirm"&&modal=="forget"){if(session.AcknowledgeAndDiscardPending(discardId,true)){modal="";needsRefresh=true;}Render(true);return;}
            else if(action.StartsWith("tab:",StringComparison.Ordinal)){int next;if(!int.TryParse(action.Substring(4),out next)||next<0||next>3)return;tab=next;searchOpen115=friendSecondary118=privacyMenuOpen118=false;direct=false;browsingOlder=false;offset=0;friendsAfter=requestsAfter=blocksAfter="";modal="";needsRefresh=true;Render(false);Pump();return;}
            else if(action=="more-ranks"){var ranks=session.Snapshot<SocialRankRefresh115>(regional?SocialPane82.RegionalRanks115:SocialPane82.GlobalRanks115);var teams=session.Snapshot<SocialTeamRanksRefresh115>(regional?SocialPane82.RegionalTeamRanks115:SocialPane82.GlobalTeamRanks115);if(teamRanking?teams?.hasMore==true:ranks?.hasMore==true){offset=teamRanking?teams.nextOffset:ranks.nextOffset;needsRefresh=true;Pump();}return;}
            else if(action=="more-friends"||action=="more-requests"||action=="more-blocks"){
                if(action=="more-friends"){var page=session.Snapshot<SocialFriends82>(SocialPane82.Friends);if(page?.hasMore!=true)return;friendsAfter=page.nextCursor;}
                else if(action=="more-requests"){var page=session.Snapshot<SocialRequests82>(SocialPane82.Requests);if(page?.hasMore!=true)return;requestsAfter=page.nextCursor;}
                else{var page=session.Snapshot<SocialBlocks82>(SocialPane82.Blocks);if(page?.hasMore!=true)return;blocksAfter=page.nextCursor;}
                needsRefresh=true;Render(false);Pump();return;}
            else if(action=="older-messages"){browsingOlder=true;surface.scroll.verticalNormalizedPosition=1;session.LoadOlderMessages();return;}
            else if(action=="latest-messages"){browsingOlder=false;session.LatestMessages();return;}
            else if(action.StartsWith("unblock:",StringComparison.Ordinal)){peerId=action.Substring(8);modalName=peerId;modal="unblock";}
            else if(action.StartsWith("rank-team115:",StringComparison.Ordinal)){
                if(!YieldReads())return;string id=action.Substring(13);if(session.Busy||refreshing||session.PendingCommand!=null||!HeartOfTheRain.App.OnlineIdentity.IdentityProtocol82.Id(id)||!home)return;
                var teams=home.GetComponent<TeamsPage>();if(!teams)return;teams.Show();var online=home.GetComponent<OnlineTeamsPage82>();if(online&&online.IsVisible)online.OpenRankDetails115(id);return;
            }
            else if(action=="find"){if(session.Busy||refreshing)return;string value=(code??"").Trim(),id=value.ToLowerInvariant();if(HeartOfTheRain.App.OnlineIdentity.IdentityProtocol82.Id(id)){searchOpen115=false;peerId=id;peerName="";modal="profile";needsRefresh=true;Pump();return;}string clean;if(!SocialBackendClient82.TryPlayerSearch115(value,out clean)){searchError115=OnlinePlayersText82.T("Rejected");Render(true);return;}searchQuery115=clean;searchCursor115=searchError115="";searchOpen115=true;needsRefresh=true;Render(false);Pump();return;}
            else if(action=="friends-ranking115"||action=="friends-list115"){if(session.Busy||refreshing)return;friendsRank115=action=="friends-ranking115";friendsRankOffset115=0;searchOpen115=friendSecondary118=false;needsRefresh=true;Render(false);Pump();return;}
            else if(action=="friends-rank-first115"){if(session.Busy||refreshing)return;friendsRankOffset115=0;needsRefresh=true;Render(false);Pump();return;}
            else if(action=="friends-rank-more115"){if(session.Busy||refreshing)return;var page=session.Snapshot<SocialLeaderboard82>(SocialPane82.FriendsRanks);if(page?.hasMore!=true)return;friendsRankOffset115=page.nextOffset;needsRefresh=true;Render(false);Pump();return;}
            else if(action.StartsWith("search-add115:",StringComparison.Ordinal)||action.StartsWith("search-accept115:",StringComparison.Ordinal)){
                if(!searchOpen115||tab!=1||session.Busy||refreshing||needsRefresh||session.PendingCommand!=null||session.Status(SocialPane82.PlayerSearch115).state!=SocialViewState82.Ready)return;
                var page=session.Snapshot<SocialPlayerSearch115>(SocialPane82.PlayerSearch115);if(page==null||page.requestQuery!=searchQuery115||page.requestCursor!=searchCursor115||page.relationships==null)return;
                bool adding=action.StartsWith("search-add115:",StringComparison.Ordinal);string target=action.Substring(adding?14:17);
                var relation=page.relationships.FirstOrDefault(r=>adding?r.playerId==target&&r.state=="None":r.requestId==target&&r.state=="Incoming");if(relation==null)return;
                searchError115="";searchWriting115=true;Write(()=>adding?session.RequestFriend(Command(),relation.playerId):session.RespondFriend(Command(),relation.requestId,"accept"));if(!writing)searchWriting115=false;return;
            }
            else if(action=="search-more115"){if(session.Busy||refreshing)return;var page=session.Snapshot<SocialPlayerSearch115>(SocialPane82.PlayerSearch115);if(page==null||page.requestQuery!=searchQuery115||page.requestCursor!=searchCursor115||!page.hasMore)return;searchCursor115=page.nextCursor;needsRefresh=true;Render(false);Pump();return;}
            else if(action.StartsWith("player:",StringComparison.Ordinal)||action.StartsWith("direct:",StringComparison.Ordinal)){if(!YieldReads())return;peerId=action.Substring(action.IndexOf(':')+1);peerName="";direct=action.StartsWith("direct:",StringComparison.Ordinal);browsingOlder=false;modal=direct?"":"profile";needsRefresh=true;Render(false);Pump();return;}
            else if(action=="open-direct"){modal="";direct=true;browsingOlder=false;needsRefresh=true;Render(false);Pump();return;}
            else if(action=="back"){direct=false;tab=1;modal="";draft="";needsRefresh=true;Render(false);Pump();return;}
            else if(action=="add"){modal="";Write(()=>session.RequestFriend(Command(),peerId));return;}
            else if(action.StartsWith("accept:",StringComparison.Ordinal)||action.StartsWith("decline:",StringComparison.Ordinal)||action.StartsWith("cancel-request:",StringComparison.Ordinal)){int at=action.IndexOf(':');string kind=action.Substring(0,at);modal="";Write(()=>session.RespondFriend(Command(),action.Substring(at+1),kind=="cancel-request"?"cancel":kind));return;}
            else if(action=="compose"){modal="compose";}
            else if(action=="send"){string text=draft.Trim();if(text.Length==0)return;modal="";submittedDirect=draft;Write(()=>session.SendDirectMessage(Command(),text));draft="";return;}
            else if(action=="remove"||action=="block"){modal=action;modalName=peerName;}
            else if(action=="report-profile"){modal="report";reportKind="Profile";reportId=peerId;}
            else if(action.StartsWith("message:",StringComparison.Ordinal)){var message=session.Snapshot<SocialMessages82>(SocialPane82.DirectChat)?.messages?.FirstOrDefault(row=>row.messageId==action.Substring(8));if(message==null)return;modal="report";reportKind="Message";reportId=message.messageId;}
            else if(action=="confirm"&&modal=="remove"){modal="";Write(()=>session.RemoveFriend(Command(),peerId));return;}
            else if(action=="confirm"&&modal=="unblock"){modal="";blocksAfter="";Write(()=>session.Unblock(Command(),peerId));return;}
            else if(action=="confirm"&&modal=="block"){modal="";direct=false;Write(()=>session.Block(Command(),peerId));return;}
            else if(action=="confirm"&&modal=="report"){modal="";reporting=true;Write(()=>reportKind=="Message"?session.ReportMessage(Command(),reportId,"Other"):session.ReportPublicText(Command(),reportKind,reportId,"Other"));return;}
            else return;Render(true);
        }
        OnlinePlayersView82 View(){var presentation=session==null?default(SocialPageSession82.PresentationReadLease):session.BeginPresentationRead();try{var relationship=session?.PresentationSnapshot<SocialRelationship82>(SocialPane82.Relationship);if(relationship?.playerId!=peerId)relationship=null;var friends=session?.PresentationSnapshot<SocialFriends82>(SocialPane82.Friends);var profile=session?.PresentationSnapshot<SocialProfile82>(SocialPane82.PlayerProfile);if(profile?.playerId!=peerId)profile=null;return new OnlinePlayersView82{selfId=session?.PlayerId,connected=session!=null&&session.PlayerId!=null,busy=authorizing||refreshing||needsRefresh||(session!=null&&session.Busy),writing=writing,pending=session?.PendingCommand!=null&&!session.Busy&&!refreshing,tab=tab,offset=offset,regional=regional,teamRanking=teamRanking,regionCode=session?.PresentationSnapshot<SocialRegion89>(SocialPane82.Region)?.regionCode??"",countryLoaded=session?.PresentationSnapshot<SocialRegion89>(SocialPane82.Region)!=null,countryError=countryError,countryQuery=countryQuery,countryPage=countryPage,direct=direct,peerId=peerId,peerName=peerName,modal=modal,modalName=modalName,profile=profile,ownProfileLoaded=ownProfile!=null,ownOptIn=ownProfile?.leaderboardOptIn==true,relationship=relationship,isFriend=relationship?.state=="Friends",blocks=session?.PresentationSnapshot<SocialBlocks82>(SocialPane82.Blocks),friends=friends,ranks=session?.PresentationSnapshot<SocialLeaderboard82>(regional?SocialPane82.RegionalRanks:SocialPane82.GlobalRanks),teamRanks=session?.PresentationSnapshot<SocialTeamLeaderboard89>(regional?SocialPane82.RegionalTeamRanks:SocialPane82.GlobalTeamRanks),requests=session?.PresentationSnapshot<SocialRequests82>(SocialPane82.Requests),chat=session?.PresentationSnapshot<SocialMessages82>(SocialPane82.DirectChat),ranks115=session?.PresentationSnapshot<SocialRankRefresh115>(regional?SocialPane82.RegionalRanks115:SocialPane82.GlobalRanks115),teamRanks115=session?.PresentationSnapshot<SocialTeamRanksRefresh115>(regional?SocialPane82.RegionalTeamRanks115:SocialPane82.GlobalTeamRanks115),selfAvatarAvailable115=HasSelfAvatar115(),searchOpen115=searchOpen115,friendSecondary118=friendSecondary118,privacyMenuOpen118=privacyMenuOpen118,friendPending115=session?.PendingCommand?.operation=="friend.send"||session?.PendingCommand?.operation=="friend.respond",searchReady115=session?.Status(SocialPane82.PlayerSearch115).state==SocialViewState82.Ready,friendsRank115=friendsRank115,friendsRankOffset115=friendsRankOffset115,friendsRanks115=session?.PresentationSnapshot<SocialLeaderboard82>(SocialPane82.FriendsRanks),searchQuery115=searchQuery115,searchCursor115=searchCursor115,searchResults115=session?.PresentationSnapshot<SocialPlayerSearch115>(SocialPane82.PlayerSearch115),rowsReady136=!writing&&session!=null&&!authorizing&&session.PendingCommand==null&&(tab==0&&!direct&&modal.Length==0)&&session.Status(Pane).hasCachedView,status=notice.Length>0?notice:writeNotice.Length>0?writeNotice:searchOpen115&&searchError115.Length>0?searchError115:authorizing||refreshing?"":session==null?OnlinePlayersText82.T("Unavailable"):OnlinePlayersText82.Status(tab==0&&!direct&&modal!="profile"?(regional?session.RankingStatus(Pane):session.Status(Pane)):session.Status(Pane))};}finally{presentation.Dispose();}}
        Vector2Int ScreenSize(){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(reviewSize.x>0)return reviewSize;
#endif
            return new Vector2Int(Screen.width,Screen.height);}
        Rect Physical(){var s=ScreenSize();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(reviewSize.x>0)return new Rect(0,0,s.x,s.y);
#endif
            var value=Screen.safeArea;return value.width>0&&value.height>0?value:new Rect(0,0,s.x,s.y);}
        void Render(bool preserve){if(surface==null)return;var physical=Physical();float factor=home?home.CurrentUIScale:Math.Max(1,physical.width/420);factor=Math.Max(.1f,Math.Min(factor,Math.Min(physical.width/320,physical.height/(direct?568:320))));float topInset=Math.Max(0,ScreenSize().y-physical.yMax)/factor;var next=OnlinePlayersLayout82.Build(physical.width/factor,physical.height/factor,View(),topInset);bool follow=direct&&!browsingOlder&&modal.Length==0&&(!preserve||refreshing||surface.scroll.verticalNormalizedPosition<=.02f);
            // A read that changed nothing keeps the nodes under the player's finger.
            ulong signature=OnlineTeamsPage82.FrameHash(next);if(frame!=null&&signature==renderedFrame&&size==ScreenSize()&&safe==Screen.safeArea&&Math.Abs(scale-factor)<.01f&&locale==GameLocale.Revision){if(!preserve||follow)surface.scroll.verticalNormalizedPosition=direct&&!browsingOlder?0:1;return;}
            frame=next;renderedFrame=signature;surface.Apply(frame.width,frame.height,factor,physical,ScreenSize().y,frame.viewportY,frame.viewportHeight,frame.chrome,frame.content,frame.overlay,modal.Length>0,home&&home.State.reduceMotion,preserve&&!follow,direct&&!browsingOlder?0:1,frame.artScale,frame.r3SliceScale118);layoutFrame=Time.frameCount;size=ScreenSize();safe=Screen.safeArea;scale=factor;locale=GameLocale.Revision;}
        void LateUpdate(){if(Time.frameCount>layoutFrame&&IsVisible&&(session==null||session.PresentationRevision!=observedRevision||surface.scroll.verticalNormalizedPosition!=observedPosition||layoutFrame!=observedLayout))ObserveRead();}
        bool ObserveRead(){
            observedRevision=session?.PresentationRevision??-1;observedPosition=surface!=null&&surface.scroll?surface.scroll.verticalNormalizedPosition:-1;observedLayout=layoutFrame;
            if(!IsVisible||!direct||modal.Length>0||refreshing||session==null||browsingOlder){session?.SetMessageViewportAtLatest(false);observedRevision=-2;return false;}
            var chat=session.PresentationSnapshot<SocialMessages82>(SocialPane82.DirectChat);var last=chat?.messages?.LastOrDefault();
            bool visible=last!=null&&!chat.hasNewer&&OnlineSocialSurface82.MessageEndVisible(surface.scroll,surface.nodes,last.messageId);
            return session.ObserveVisibleMessages(last?.sequence??0,visible);
        }
        void OnDestroy(){closed=true;authorizationRequest++;authorizing=false;generation++;if(gateway){gateway.IdentityChanged-=IdentityChanged;gateway.Changed-=GatewayChanged;}if(session!=null){session.Changed-=Changed;if(owns)session.Dispose();session=null;}}
    }
}

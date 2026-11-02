using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using UnityEngine;

namespace HeartOfTheRain.App.OnlineSocial
{
    public enum SocialPane82 { Teams, TeamInfo, TeamChat, Friends, Requests, DirectChat, GlobalRanks, FriendsRanks, TeamRanks, Records, PlayerProfile, Relationship, Blocks,Region,RegionalRanks,GlobalTeamRanks,RegionalTeamRanks,TeamLives110,OwnedLives110,TeamTail110,TeamMail111,TeamMailDetail111,OwnedMail111,InviteFriends112,InviteReceived112,InviteDetail112,GlobalRanks115,RegionalRanks115,GlobalTeamRanks115,RegionalTeamRanks115,PlayerSearch115 }
    public enum SocialViewState82 { NotLoaded, Loading, Ready, Offline, Unavailable, Unauthenticated, Rejected, Cancelled, CommitUnknown }

    // Presentation state only. No demo data, wallet, profile grant, timers that
    // mutate services, or automatic write retry. Cached server views survive a
    // failed read; changing the managed owner clears every private view.
    public sealed partial class SocialPageSession82 : IDisposable
    {
        public sealed class ViewStatus {
            public readonly SocialViewState82 state; public readonly string error, reason; public readonly bool hasCachedView;
            public ViewStatus(SocialViewState82 state, string error, bool cached, string reason = null) { this.state = state; this.error = error; hasCachedView = cached; this.reason = reason; }
        }
        readonly SocialBackendClient82 client;
        readonly IDisposable protectedStore;
        readonly Func<long> ownerGeneration;
        readonly long generation;
        readonly Func<double> clock;
        readonly Dictionary<SocialPane82, ViewStatus> states = new Dictionary<SocialPane82, ViewStatus>();
        readonly Dictionary<SocialPane82, object> views = new Dictionary<SocialPane82, object>();
        public const int PageSize = 8;
        bool messageViewportAtLatest;
        double readStartedAt;
        bool disposed, ownerChanged, inFlight, writing, visible;
        long request;
        long presentationRevision;
        double pollAt;
        SocialPane82 pane = SocialPane82.Teams;
        SocialPane82 activePane;
        string teamId, directId;
        public event Action Changed;
        public SocialPageSession82(SocialBackendClient82 client, IDisposable ownedProtectedStore = null, Func<long> currentOwnerGeneration = null, Func<double> unscaledClock = null)
        {
            this.client = client ?? throw new ArgumentNullException(nameof(client)); protectedStore = ownedProtectedStore;
            ownerGeneration = currentOwnerGeneration; generation = ownerGeneration == null ? 0 : ownerGeneration();
            clock = unscaledClock ?? (() => Stopwatch.GetTimestamp() / (double)Stopwatch.Frequency);
        }
        public bool Busy => inFlight || client.Busy;
        public bool ReadInFlight => ActiveOwner() && inFlight && !writing;
        public long PresentationRevision => ActiveOwner() ? presentationRevision : -1;
        public bool IsVisible => visible;
        public SocialPane82 Pane => pane;
        public string PlayerId => ActiveOwner() ? client.PlayerId : null;
        public string SelectedTeamId => ActiveOwner() ? teamId : null;
        public string SelectedDirectPlayerId => ActiveOwner() ? directId : null;
        public SocialPendingCommand82 PendingCommand { get { if(!ActiveOwner()) return null; try { return client.PendingCommand; } catch(Exception) { return null; } } }
        public ViewStatus Status(SocialPane82 target) {
            if(!ActiveOwner()) return new ViewStatus(SocialViewState82.Unauthenticated, "SocialOwnerChanged", false);
            ViewStatus value; return states.TryGetValue(target, out value) ? value : new ViewStatus(SocialViewState82.NotLoaded, null, false);
        }
        public ViewStatus RankingStatus(SocialPane82 target){var country=Status(SocialPane82.Region);return country.state!=SocialViewState82.Ready&&country.state!=SocialViewState82.NotLoaded?country:Status(target);}
        public T Snapshot<T>(SocialPane82 target) where T : class {
            if(!ActiveOwner()) return null; object value;
            var result=views.TryGetValue(target, out value) && value is T ? JsonUtility.FromJson<T>(JsonUtility.ToJson(value)) : null;
            // Unity's value serialization materializes a null custom class as
            // an empty nested object. Preserve semantic absence at this cache
            // boundary; the HTTP parser still rejects malformed non-null rows.
            if(result is SocialLifeRequests110 lives&&string.IsNullOrEmpty(lives.ownRequest?.requestId))lives.ownRequest=null;
            return result;
        }
        // Render adapters only: never mutate the returned DTO. Commands and
        // gameplay services must keep using Snapshot(), which returns a copy.
        internal T PresentationSnapshot<T>(SocialPane82 target) where T : class {
            if(!ActiveOwner())return null;object value;
            return views.TryGetValue(target,out value)?value as T:null;
        }
        int presentationReaders;
        // A render has one protected owner check before reading its several
        // cached panes. Mutations and transport callbacks run outside this
        // short synchronous scope and continue to revalidate ownership.
        public readonly struct PresentationReadLease : IDisposable {
            readonly SocialPageSession82 owner;
            internal PresentationReadLease(SocialPageSession82 owner){this.owner=owner;}
            public void Dispose(){if(owner!=null)owner.presentationReaders--;}
        }
        public PresentationReadLease BeginPresentationRead(){
            if(!ActiveOwner())return default;
            presentationReaders++;
            return new PresentationReadLease(this);
        }
        bool ActiveOwner() {
            if(disposed || ownerChanged) return false;
            if(presentationReaders>0)return true;
            bool same; try { same = ownerGeneration == null ? client.Configured : client.Open && ownerGeneration() == generation; } catch(Exception) { same = false; }
            if(same) return true;
            ownerChanged = true; request++; visible = false; inFlight = writing = false;
            views.Clear(); states.Clear(); presentationRevision++; messageViewportAtLatest = false; teamId = directId = null; client.Cancel(); Notify(); return false;
        }
        void Notify() { var listeners = Changed; if(listeners == null) return; foreach(Action listener in listeners.GetInvocationList()) try { listener(); } catch(Exception) { } }
        void State(SocialPane82 target, SocialViewState82 state, string error = null, string reason = null) { bool cached=views.ContainsKey(target);states[target] = new ViewStatus(state, error, cached, reason);if(!cached||(state!=SocialViewState82.Loading&&state!=SocialViewState82.Cancelled))presentationRevision++; }
        bool Begin(SocialPane82 target, bool write, out long token) {
            token = 0; if(!ActiveOwner() || Busy) return false;
            inFlight = true; writing = write; if(!write)readStartedAt=clock(); activePane = target; token = ++request; State(target, SocialViewState82.Loading); Notify(); return !disposed && !ownerChanged && request == token && inFlight;
        }
        // UnityWebRequest's platform timeout can fail to resume a suspended
        // coroutine. A read has no durable mutation, so release its client
        // lease from the visible page after the transport deadline.
        public bool FailStalledRead(double seconds=20) {
            if(!ActiveOwner()||!inFlight||writing||clock()-readStartedAt<seconds)return false;
            request++;client.Cancel();inFlight=false;State(activePane,SocialViewState82.Offline,"SocialReadTimedOut");Notify();return true;
        }
        // A visible chat send takes priority over a replaceable GET. The
        // request token rejects its late callback; durable writes are never
        // cancelled by this path.
        public bool YieldReadForForeground() {
            if(!ActiveOwner())return false;
            if(!Busy)return true;
            if(!inFlight||writing)return false;
            request++;client.Cancel();inFlight=false;State(activePane,SocialViewState82.Cancelled,"SocialReadSuperseded");Notify();return !Busy;
        }
        bool Current(long token) => ActiveOwner() && request == token;
        static SocialViewState82 Failure(string error, bool unknown, bool pending) {
            if(error == "SocialHttp401" || error == "SocialHttp410" || error == "SocialClientNotConfigured") return SocialViewState82.Unauthenticated;
            if(unknown && pending) return SocialViewState82.CommitUnknown;
            if(error == "SocialClientCancelled" || error == "SocialIdentityChangedOrCancelled" || error == "SocialRequestStopped") return SocialViewState82.Cancelled;
            if(error == "SocialNetworkUnavailable" || error == "SocialRequestUnavailable" || error == "SocialDispatchUnavailable") return SocialViewState82.Offline;
            // Overload and server faults are retryable, not a refusal of the action.
            if(error == "SocialHttp429" || error == "SocialHttp200" || error != null && error.StartsWith("SocialHttp5", StringComparison.Ordinal)) return SocialViewState82.Offline;
            if(error != null && error.StartsWith("SocialHttp", StringComparison.Ordinal)) return SocialViewState82.Rejected;
            return SocialViewState82.Unavailable;
        }
        void Failed(SocialPane82 target, string error, bool unknown, string refusal = null) {
            bool pending; try { pending = client.PendingCommand != null; } catch(Exception) { pending = writing; }
            // Offline caches are useful. A permission/deletion response is not
            // permission to keep displaying the affected private conversation.
            if(error == "SocialHttp401" || error == "SocialHttp410") { views.Clear(); states.Clear(); messageViewportAtLatest = false; }
            else if(error == "SocialHttp403" || error == "SocialHttp404") {
                views.Remove(target);
                if(target == SocialPane82.TeamInfo || target == SocialPane82.TeamChat || target==SocialPane82.TeamMail111 || target==SocialPane82.TeamMailDetail111 || error=="SocialHttp403"&&(target==SocialPane82.TeamLives110 || target==SocialPane82.TeamTail110)) { views.Remove(SocialPane82.TeamInfo); views.Remove(SocialPane82.TeamChat);views.Remove(SocialPane82.TeamLives110);views.Remove(SocialPane82.TeamTail110);newTeamMessages110=false;ClearMail111();ClearInvites112(); }
            }
            State(target, refusal != null ? SocialViewState82.Rejected : Failure(error, unknown, pending), error, refusal);
        }
        bool Read<T>(SocialPane82 target, Action<Action<SocialReply82<T>>> send, Action<T> accepted = null) where T : class {
            long token; if(!Begin(target, false, out token)) return false;
            try { send(reply => {
                if(!Current(token)) return; inFlight = writing = false;
                if(reply != null && reply.Succeeded) {
                    views[target] = JsonUtility.FromJson<T>(JsonUtility.ToJson(reply.value)); State(target, SocialViewState82.Ready);
                    accepted?.Invoke(reply.value);
                } else Failed(target, reply == null ? "SocialNoReply" : reply.error, reply != null && reply.unknown);
                pollAt = clock() + 10; Notify();
            }); } catch(Exception) { if(Current(token)) { inFlight = writing = false; State(target, SocialViewState82.Unavailable, "SocialReadDispatchFailed"); Notify(); } }
            return true;
        }
        bool Mutate(SocialPane82 target, Action<Action<SocialReply82<SocialMutation82>>> send, Action<SocialMutation82> accepted = null, bool replaceable = false) {
            long token; if(!Begin(target, true, out token)) return false;
            try { send(reply => {
                if(!Current(token)) return; inFlight = false;
                if(reply != null && reply.Succeeded) { State(target, SocialViewState82.Ready); accepted?.Invoke(reply.value); pollAt = 0; }
                else if(replaceable) State(target, SocialViewState82.Ready);
                else { lastRefusal = reply?.refusal; Failed(target, reply == null ? "SocialNoReply" : reply.error, reply == null || reply.unknown, reply?.refusal); }
                writing = false; Notify();
            }); } catch(Exception) { if(Current(token)) { inFlight = false; Failed(target, "SocialMutationDispatchFailed", true); writing = false; Notify(); } }
            return true;
        }
        public void Show(SocialPane82 target) { if(!ActiveOwner()) return; pane = target; visible = true; pollAt = 0; Notify(); }
        public void DeferPolling(double seconds){if(ActiveOwner())pollAt=Math.Max(pollAt,clock()+Math.Max(0,Math.Min(10,seconds)));}
        public void Hide() {
            visible = false;
            // A submitted write continues under the durable owner. Hiding a page
            // never means that a possibly committed message should be forgotten.
            if(inFlight && !writing) { request++; client.Cancel(); inFlight = false; State(activePane, SocialViewState82.Cancelled, "SocialPageHidden"); }
            Notify();
        }
        public void Tick() {
            if(!ActiveOwner() || !visible || Busy || !messageViewportAtLatest || clock() < pollAt) return;
            pollAt = clock() + 10;
            if(pane == SocialPane82.TeamChat && teamId != null) RefreshTeamMessages();
            else if(pane == SocialPane82.DirectChat && directId != null) RefreshDirectMessages();
        }
        public bool RefreshTeams(string after = "",string query="") => Read<SocialTeams82>(SocialPane82.Teams, done => client.GetTeams(after, PageSize,query, done), value => {
            // JsonUtility snapshot cloning can turn an absent nullable string
            // into "". Wire validation remains strict; internal absence is null.
            string own=string.IsNullOrEmpty(value.myTeamId)?null:value.myTeamId;
            if(teamId != own) { views.Remove(SocialPane82.TeamInfo); views.Remove(SocialPane82.TeamChat);views.Remove(SocialPane82.TeamLives110);views.Remove(SocialPane82.TeamTail110);states.Remove(SocialPane82.TeamTail110);newTeamMessages110=false;states.Remove(SocialPane82.TeamLives110);states.Remove(SocialPane82.TeamInfo); states.Remove(SocialPane82.TeamChat);ClearMail111();ClearInvites112(); }
            value.myTeamId=own;teamId=own;
        });
        public bool SelectTeam(string id) {
            if(!ActiveOwner() || Busy || !HeartOfTheRain.App.OnlineIdentity.IdentityProtocol82.Id(id)) return false;
            if(teamId != id) { views.Remove(SocialPane82.TeamInfo); views.Remove(SocialPane82.TeamChat);views.Remove(SocialPane82.TeamLives110);views.Remove(SocialPane82.TeamTail110);states.Remove(SocialPane82.TeamTail110);newTeamMessages110=false;states.Remove(SocialPane82.TeamLives110);states.Remove(SocialPane82.TeamInfo); states.Remove(SocialPane82.TeamChat);ClearMail111();ClearInvites112(); }
            teamId = id; Show(SocialPane82.TeamInfo); return RefreshTeam();
        }
        public bool RefreshTeam() => teamId != null && Read<SocialTeam82>(SocialPane82.TeamInfo, done => client.GetTeam(teamId, done));
        public bool RefreshTeamMessages() => teamId != null && Messages(SocialPane82.TeamChat,"Team",teamId);
        public bool OpenDirect(string playerId) {
            if(!ActiveOwner()||Busy||!HeartOfTheRain.App.OnlineIdentity.IdentityProtocol82.Id(playerId))return false;
            if(directId!=playerId){views.Remove(SocialPane82.DirectChat);states.Remove(SocialPane82.DirectChat);messageViewportAtLatest=false;}
            directId=playerId;Show(SocialPane82.DirectChat);return RefreshDirectMessages();
        }
        public bool RefreshDirectMessages() => directId != null && Messages(SocialPane82.DirectChat,"Direct",directId);
        bool Messages(SocialPane82 target,string kind,string id) => Read<SocialMessages82>(target,done=>client.GetMessagesTail(kind,id,PageSize,done),value=>{if(target==SocialPane82.TeamChat)newTeamMessages110=false;});
        public bool LoadOlderMessages() {
            string id=pane==SocialPane82.TeamChat?teamId:pane==SocialPane82.DirectChat?directId:null;
            if(id==null)return false;var target=pane;var old=Snapshot<SocialMessages82>(target);
            if(old==null||!old.hasOlder||old.olderCursor<=0)return false;
            messageViewportAtLatest=false;
            // Explicit eight-message pages: no automatic scan from sequence0,
            // no hidden history accumulation and no growing response budget.
            return Read<SocialMessages82>(target,done=>client.GetMessagesBefore(target==SocialPane82.TeamChat?"Team":"Direct",id,old.olderCursor,PageSize,done));
        }
        public bool LatestMessages() {messageViewportAtLatest=false;return pane==SocialPane82.TeamChat?RefreshTeamMessages():pane==SocialPane82.DirectChat&&RefreshDirectMessages();}
        // Geometry is observed by the visible page after a stable layout. Never
        // mark a page merely because an HTTP response arrived or it was cached.
        public bool ObserveVisibleMessages(long lastVisibleSequence,bool atLatest) {
            messageViewportAtLatest=atLatest;
            if(!ActiveOwner()||!visible||Busy||PendingCommand!=null||!atLatest||(pane!=SocialPane82.TeamChat&&pane!=SocialPane82.DirectChat))return false;
            var target=pane;var value=PresentationSnapshot<SocialMessages82>(target);
            if(value==null||value.hasNewer||value.unreadCount==0||value.messages.Length==0||value.nextCursor!=lastVisibleSequence||value.messages[value.messages.Length-1].sequence!=lastVisibleSequence)return false;
            string command=Guid.NewGuid().ToString("N"),kind=target==SocialPane82.TeamChat?"Team":"Direct",id=target==SocialPane82.TeamChat?teamId:directId;
            return id!=null&&Mutate(target,done=>client.MarkRead(command,kind,id,lastVisibleSequence,done),receipt=>{object current;if(views.TryGetValue(target,out current)&&current is SocialMessages82 chat&&chat.nextCursor<=receipt.through)chat.unreadCount=0;},true);
        }
        public void SetMessageViewportAtLatest(bool value){messageViewportAtLatest=value;}
        public bool RefreshFriends(string after="") => Read<SocialFriends82>(SocialPane82.Friends,done=>client.GetFriends(after,PageSize,done));
        public bool RefreshRequests(string after="") => Read<SocialRequests82>(SocialPane82.Requests,done=>client.GetRequests(after,PageSize,done));
        public bool RefreshBlocks(string after="") => Read<SocialBlocks82>(SocialPane82.Blocks,done=>client.GetBlocks(after,PageSize,done));
        public bool RefreshRelationship(string id) => Read<SocialRelationship82>(SocialPane82.Relationship,done=>client.GetRelationship(id,done));
        public bool RefreshRecords(long after=0) => Read<SocialRecords82>(SocialPane82.Records,done=>client.GetRecords(after,PageSize,done));
        public bool RefreshProfile(string playerId) => Read<SocialProfile82>(SocialPane82.PlayerProfile,done=>client.GetProfile(playerId,done));
        public bool RefreshRegion()=>Read<SocialRegion89>(SocialPane82.Region,done=>client.GetRegion(done));
        public bool SetRegion(string commandId,string code)=>Mutate(SocialPane82.Region,done=>client.UpdateRegion(commandId,code,done),value=>{
            views[SocialPane82.Region]=new SocialRegion89{playerId=value.playerId,regionCode=value.regionCode,regionSource=value.regionSource,locationVerified=value.locationVerified};
            foreach(var key in new[]{SocialPane82.RegionalRanks,SocialPane82.GlobalTeamRanks,SocialPane82.RegionalTeamRanks}){views.Remove(key);states.Remove(key);}
        });
        public bool RefreshTeamRanks(string scope,int offset=0)=>Read<SocialTeamLeaderboard89>(scope=="regional"?SocialPane82.RegionalTeamRanks:SocialPane82.GlobalTeamRanks,done=>client.GetTeamLeaderboard(scope,offset,PageSize,done));
        public bool RefreshRanks(string scope,int offset=0) {
            SocialPane82 target=scope=="global"?SocialPane82.GlobalRanks:scope=="regional"?SocialPane82.RegionalRanks:scope=="friends"?SocialPane82.FriendsRanks:SocialPane82.TeamRanks;
            return Read<SocialLeaderboard82>(target,done=>client.GetLeaderboard(scope,offset,PageSize,done));
        }
        void Invalidate(params SocialPane82[] targets) { foreach(var target in targets) { states.Remove(target); } }
        void ClearRankings(){foreach(var target in new[]{SocialPane82.GlobalRanks,SocialPane82.RegionalRanks,SocialPane82.GlobalTeamRanks,SocialPane82.RegionalTeamRanks,SocialPane82.FriendsRanks,SocialPane82.TeamRanks,SocialPane82.GlobalRanks115,SocialPane82.RegionalRanks115,SocialPane82.GlobalTeamRanks115,SocialPane82.RegionalTeamRanks115}){views.Remove(target);states.Remove(target);}}
        public bool CreateTeam(string commandId, string name, string description) => Mutate(SocialPane82.Teams, done => client.CreateTeam(commandId, name, description, done), value => { teamId = value.teamId; Invalidate(SocialPane82.Teams, SocialPane82.TeamInfo, SocialPane82.TeamChat); });
        public bool CreateTeam(string commandId,string name,string description,string badgeId)=>Mutate(SocialPane82.Teams,done=>client.CreateTeam(commandId,name,description,badgeId,done),value=>{teamId=value.teamId;Invalidate(SocialPane82.Teams,SocialPane82.TeamInfo,SocialPane82.TeamChat);});
        public bool JoinTeam(string commandId, string id) => Mutate(SocialPane82.Teams, done => client.JoinTeam(commandId, id, done), value => { teamId = value.teamId; Invalidate(SocialPane82.Teams, SocialPane82.TeamInfo, SocialPane82.TeamChat); });
        public bool LeaveTeam(string commandId) => teamId != null && Mutate(SocialPane82.TeamInfo, done => client.LeaveTeam(commandId, teamId, done), value => { teamId = null; views.Remove(SocialPane82.TeamInfo); views.Remove(SocialPane82.TeamChat);views.Remove(SocialPane82.TeamLives110);views.Remove(SocialPane82.TeamTail110);states.Remove(SocialPane82.TeamTail110);newTeamMessages110=false;ClearMail111();ClearInvites112();Invalidate(SocialPane82.Teams, SocialPane82.TeamInfo, SocialPane82.TeamChat,SocialPane82.TeamLives110); });
        public bool TransferLeadership(string commandId, string playerId) => teamId != null && Mutate(SocialPane82.TeamInfo, done => client.ManageMember("transfer", commandId, teamId, playerId, done), value => Invalidate(SocialPane82.TeamInfo));
        public bool SendTeamMessage(string commandId, string text) => teamId != null && Mutate(SocialPane82.TeamChat, done => client.SendMessage(commandId, "Team", teamId, text, done),value=>AcknowledgeMessage110());
        public bool SendDirectMessage(string commandId, string text) => directId != null && Mutate(SocialPane82.DirectChat, done => client.SendMessage(commandId, "Direct", directId, text, done));
        public bool MarkTeamRead(string commandId, long through) => teamId != null && Mutate(SocialPane82.TeamChat, done => client.MarkRead(commandId, "Team", teamId, through, done));
        public bool MarkDirectRead(string commandId, long through) => directId != null && Mutate(SocialPane82.DirectChat, done => client.MarkRead(commandId, "Direct", directId, through, done));
        public bool RequestFriend(string commandId, string playerId) => Mutate(SocialPane82.Requests, done => client.RequestFriend(commandId, playerId, done), value => Invalidate(SocialPane82.Requests, SocialPane82.Friends));
        public bool RespondFriend(string commandId, string id, string action) => Mutate(SocialPane82.Requests, done => client.RespondFriend(commandId, id, action, done), value => Invalidate(SocialPane82.Requests, SocialPane82.Friends));
        public bool RemoveFriend(string commandId, string playerId) => Mutate(SocialPane82.Friends, done => client.RemoveFriend(commandId, playerId, done), value => Invalidate(SocialPane82.Friends, SocialPane82.Requests));
        public bool Block(string commandId, string playerId) => Mutate(SocialPane82.PlayerProfile, done => client.Block(commandId, playerId, done), value => { views.Remove(SocialPane82.PlayerProfile); views.Remove(SocialPane82.DirectChat); views.Remove(SocialPane82.Relationship); ClearRankings();Invalidate(SocialPane82.Blocks,SocialPane82.Friends, SocialPane82.Requests, SocialPane82.DirectChat); });
        public bool Unblock(string commandId, string playerId) => Mutate(SocialPane82.PlayerProfile, done => client.Unblock(commandId, playerId, done), value => { views.Remove(SocialPane82.Relationship); Invalidate(SocialPane82.Blocks,SocialPane82.Friends,SocialPane82.Requests); });
        public bool ReportMessage(string commandId,string messageId,string reason,string details="") => Mutate(pane,done=>client.ReportMessage(commandId,messageId,reason,details,done));
        public bool ReportPublicText(string commandId,string kind,string id,string reason,string details="") => Mutate(pane,done=>client.ReportPublicText(commandId,kind,id,reason,details,done));
        public bool SetLeaderboardConsent(string commandId,bool optIn) => Mutate(SocialPane82.GlobalRanks,done=>client.UpdateLeaderboardConsent(commandId,optIn,done),value=>ClearRankings());
        void Recovered(SocialPendingCommand82 pending,SocialMutation82 receipt=null){if(pending?.operation!="team.leave")ClearRankings();if(pending?.operation=="region.set")views.Remove(SocialPane82.Region);if(pending?.operation=="message.send"&&pending.path.StartsWith("/v1/messages/Team/",StringComparison.Ordinal))AcknowledgeMessage110();AcceptedLife110(receipt);AcceptedMail111(receipt);AcceptedLeave113(pending,receipt);if(pending?.operation=="invite.send"){ClearInvites112();AcceptedInvite112(receipt);}states.Clear();pollAt=0;}
        string lastRefusal;
        // The server code of the last refused write, once. Its pane status is replaced by the refresh that follows.
        public string TakeWriteRefusal(){var value=lastRefusal;lastRefusal=null;return value;}
        public bool ResumePending(){var pending=PendingCommand;return Mutate(pane,done=>client.ResumePending(done),value=>Recovered(pending,value));}
        public bool ReconcilePending() {
            var pending=PendingCommand;
            long token; if(!Begin(pane, false, out token)) return false;
            var target = pane;
            client.ReconcilePending(reply => {
                if(!Current(token)) return; inFlight = writing = false;
                if(reply.Succeeded && reply.value.status == "Committed") { Recovered(pending,reply.value.response);messageViewportAtLatest = false; State(target, SocialViewState82.Ready); }
                else if(reply.Succeeded) State(target, SocialViewState82.CommitUnknown, "SocialReceiptAbsentDoesNotProveFailure");
                else Failed(target, reply.error, reply.unknown);
                Notify();
            }); return true;
        }
        public bool AcknowledgeAndDiscardPending(string expectedCommandId, bool acknowledgesMayAlreadyBeCommitted) {
            if(!ActiveOwner() || Busy) return false;
            string error; bool saved = client.AcknowledgeAndDiscardPending(expectedCommandId, acknowledgesMayAlreadyBeCommitted, out error);
            State(pane, saved ? SocialViewState82.NotLoaded : SocialViewState82.Unavailable, saved ? "SocialIntentDiscardedRemoteMayAlreadyBeCommitted" : error);
            pollAt = 0; Notify(); return saved;
        }
        public void Dispose() {
            if(disposed) return; disposed = true; request++; visible = false; inFlight = writing = false; views.Clear(); states.Clear(); messageViewportAtLatest = false; teamId = directId = null;
            client.Dispose(); protectedStore?.Dispose(); Changed = null;
        }
    }
}

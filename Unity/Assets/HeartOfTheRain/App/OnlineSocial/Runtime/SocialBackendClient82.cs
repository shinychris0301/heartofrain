using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using UnityEngine;
using UnityEngine.Networking;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.Profile;

namespace HeartOfTheRain.App.OnlineSocial
{
    // Explicit service adapter only. No MonoBehaviour, login, local ProfileHost,
    // gameplay service, wallet grant, UI routing or automatic retry is installed.
    public sealed partial class SocialBackendClient82 : IDisposable
    {
        const int Limit = 65536;
        static readonly UTF8Encoding Utf8 = new UTF8Encoding(false, true);
        readonly string origin, player;
        readonly Func<SocialAccess82> credentials;
        readonly Func<bool> durableOwnerCheck;
        readonly Action<IEnumerator> dispatch;
        readonly ProtectedSocialCommandJournal82 journal;
        readonly int ownerThread = Thread.CurrentThread.ManagedThreadId;
        volatile bool disposed, revoked;
        long generation;
        Pending active;
        sealed class Pending {
            public long generation; public SocialAccess82 access; public UnityWebRequest request;
            public Action<string, string, bool> complete; public bool done, released; public string refusal;
            public void Release() { if(released) return; released = true; request?.Dispose(); access = null; }
        }
        sealed class Download : DownloadHandlerScript {
            readonly byte[] buffer = new byte[Limit]; int count; public bool exceeded;
            public Download() : base(new byte[8192]) { }
            protected override void ReceiveContentLengthHeader(ulong size) { if(size > Limit) exceeded = true; }
            protected override bool ReceiveData(byte[] bytes, int length) {
                if(exceeded || bytes == null || length < 0 || length > Limit - count) { exceeded = true; return false; }
                Buffer.BlockCopy(bytes, 0, buffer, count, length); count += length; return true;
            }
            public string Text() { if(exceeded || count == 0) throw new FormatException(); return Utf8.GetString(buffer, 0, count); }
        }
        [Serializable] class Command { public string commandId; }
        [Serializable] sealed class ProfileCommand : Command { public string displayName; public bool leaderboardOptIn; }
        [Serializable] sealed class ProfileNameCommand : Command { public string displayName; }
        [Serializable] sealed class ProfileConsentCommand : Command { public bool leaderboardOptIn; }
        [Serializable] sealed class RegionCommand : Command { public string regionCode; }
        [Serializable] sealed class TargetCommand : Command { public string playerId; }
        [Serializable] sealed class RespondCommand : Command { public string requestId, action; }
        [Serializable] sealed class TeamCommand : Command { public string name, description; }
        [Serializable] sealed class TeamBadgeCommand : Command { public string name, description,badgeId; }
        [Serializable] sealed class TextCommand : Command { public string text; }
        [Serializable] sealed class ReadCommand : Command { public long through; }
        [Serializable] sealed class ReportCommand : Command { public string messageId, reason, details; }
        [Serializable] sealed class UgcCommand : Command { public string kind, targetId, reason, details; }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        readonly List<int> statuses = new List<int>();
        public int VerificationRequests { get; private set; }
        public int[] VerificationStatuses => statuses.ToArray();
#endif
        public SocialBackendClient82(string backendOrigin, Func<SocialAccess82> currentAccess, Action<IEnumerator> dispatcher,
            IProtectedSessionStore82 protectedOutbox = null, bool explicitSocialOptIn = false, bool allowDevelopmentLoopback = false, Func<bool> durableOwnerCheck = null)
        {
            if(!explicitSocialOptIn || !RuStoreBackendClient.IsAllowedOrigin(backendOrigin, allowDevelopmentLoopback) || currentAccess == null || dispatcher == null)
                throw new ArgumentException("ExplicitSocialConfigurationRequired");
            origin = new Uri(backendOrigin).GetLeftPart(UriPartial.Authority); credentials = currentAccess; dispatch = dispatcher;this.durableOwnerCheck=durableOwnerCheck;
            var access = Current(); if(access == null) throw new ArgumentException("ActiveManagedIdentityRequired");
            player = access.playerId;
            if(protectedOutbox != null) journal = new ProtectedSocialCommandJournal82(protectedOutbox, player, origin);
        }
        SocialAccess82 Current() {
            try { var value = credentials?.Invoke(); return value != null && IdentityProtocol82.Id(value.playerId) && IdentityProtocol82.Secret(value.bearer) ? value : null; }
            catch(Exception) { return null; }
        }
        bool SameAccess(SocialAccess82 expected) { var value = Current(); return value != null && expected != null && value.playerId == player && value.playerId == expected.playerId; }
        // A temporarily absent token keeps the page's views. Another player's token never does.
        public bool Open { get { if(disposed || revoked) return false; var value = Current(); return value == null || value.playerId == player; } }
        public bool Configured => !disposed && !revoked && Current()?.playerId == player;
        public string PlayerId => player;
        public bool Busy => active != null;
        public SocialPendingCommand82 PendingCommand => journal?.CachedPending;
        bool DurableOwner(){if(durableOwnerCheck==null)return true;try{return durableOwnerCheck();}catch(Exception){return false;}}
        static void Deliver<T>(Action<SocialReply82<T>> done, SocialReply82<T> result) where T : class { try { done(result); } catch(Exception) { } }
        static bool Id(string value) => IdentityProtocol82.Id(value);
        static void Need(bool condition) { if(!condition) throw new FormatException(); }
        static string Cursor(string value) { Need(value == "" || Id(value)); return value; }
        static int Scalars(string value) {
            Need(value != null); int count=0;
            for(int i=0;i<value.Length;i++){if(char.IsHighSurrogate(value[i])){Need(i+1<value.Length&&char.IsLowSurrogate(value[i+1]));i++;}else Need(!char.IsLowSurrogate(value[i]));count++;}
            return count;
        }
        static string Name(string value) { string clean, error; Need(Scalars(value)<=256 && ProfileRules.TryName(value, out clean, out error) && clean == value); return value; }
        static string UserText(string value, int limit, bool empty = false, bool multiline = false) {
            Need(value != null && Scalars(value) <= limit && (empty || !string.IsNullOrWhiteSpace(value)));
            for(int i=0;i<value.Length;i++) {
                var category=CharUnicodeInfo.GetUnicodeCategory(value,i);
                // The server normalises CRLF to LF and accepts the joiner inside emoji such as a shrug with a gender sign.
                Need((category!=UnicodeCategory.Control||multiline&&(value[i]=='\n'||value[i]=='\r'))&&(category!=UnicodeCategory.Format||multiline&&value[i]=='‍')&&category!=UnicodeCategory.LineSeparator&&category!=UnicodeCategory.ParagraphSeparator);
                if(char.IsHighSurrogate(value[i]))i++;
            }
            return value;
        }
        public static int TeamTextLength109(string value){try{return Scalars(value);}catch(Exception){return int.MaxValue;}}
        public static bool TryTeamSearch109(string value,out string clean){clean=null;try{Need(value!=null&&value.Length<=128);UserText(value,128,true);string normalized=value.Normalize().Trim();UserText(normalized,64,true);clean=normalized;return true;}catch(Exception){return false;}}
        public static bool TryTeamDraft109(string name,string description,out string cleanName,out string cleanDescription){
            string field;return TryTeamDraft109(name,description,out cleanName,out cleanDescription,out field);
        }
        public static bool TryTeamDraft109(string name,string description,out string cleanName,out string cleanDescription,out string field){
            cleanName=cleanDescription=null;field="name";string n,d;try{n=name.Normalize().Trim();Need(Scalars(UserText(n,32))>=2);}catch(Exception){return false;}
            field="description";try{d=description.Normalize().Trim();UserText(d,160,true);}catch(Exception){return false;}cleanName=n;cleanDescription=d;field="";return true;
        }
        static Dictionary<string, object> Obj(object value) => SocialJson82.Object(value);
        static string Text(Dictionary<string, object> value, string key, int cap = 4096, bool empty = false) => SocialJson82.Text(value, key, cap, empty);
        static long Number(Dictionary<string, object> value, string key, long min = 0, long max = long.MaxValue) => SocialJson82.Number(value, key, min, max);
        static bool Flag(Dictionary<string, object> value, string key) => SocialJson82.Flag(value, key);
        static List<object> Array(Dictionary<string, object> value, string key, int cap = 100) => SocialJson82.Array(value, key, cap);
        static string Profile(Dictionary<string, object> value) {
            string id = Text(value, "playerId", 32); Need(Id(id)); Name(Text(value, "displayName", 512)); Number(value, "completedLevels", 0, 50); Flag(value, "leaderboardOptIn"); return id;
        }
        static void Page(Dictionary<string, object> value) { Flag(value, "hasMore"); Cursor(Text(value, "nextCursor", 32, true)); }
        static string Team(Dictionary<string, object> value) {
            string id = Text(value, "teamId", 32); Need(Id(id) && Id(Text(value, "ownerId", 32)));
            UserText(Text(value, "name", 64), 32); UserText(Text(value, "description", 320, true), 160, true);
            if(value.ContainsKey("badgeId"))Need(HeartOfTheRain.App.TeamsAccess.TeamsAccessBadges109.Valid(Text(value,"badgeId",16)));
            long capacity = Number(value, "capacity", 2, 100); Number(value, "memberCount", 1, capacity); return id;
        }
        T Read<T>(string json, Action<Dictionary<string, object>> check) where T : class {
            var value = SocialJson82.Read(json); check(value); var dto = JsonUtility.FromJson<T>(json); Need(dto != null); return dto;
        }
        void Complete(Pending value, string json, string error, bool unknown) {
            if(value.done) return; value.done = true; if(active == value) active = null;
            if(disposed || value.generation != Interlocked.Read(ref generation) || !SameAccess(value.access)) { json = null; error = "SocialIdentityChangedOrCancelled"; unknown = true; }
            value.complete(json, error, unknown);
        }
        void Send<T>(string method, string path, string body, Func<string, T> parse, Action<SocialReply82<T>> done) where T : class {
            if(done == null) throw new ArgumentNullException(nameof(done));
            if(method!="GET"&&!DurableOwner()){Deliver(done,SocialReply82<T>.Fail("SocialOwnerChanged"));return;}
            if(ownerThread != Thread.CurrentThread.ManagedThreadId || !Configured) { Deliver(done, SocialReply82<T>.Fail("SocialClientNotConfigured")); return; }
            if(Busy) { Deliver(done, SocialReply82<T>.Fail("SocialClientBusy")); return; }
            var pending = new Pending { generation = Interlocked.Read(ref generation), access = Current() };
            pending.complete = (json, error, unknown) => {
                if(method!="GET"&&!DurableOwner()){Deliver(done,SocialReply82<T>.Fail("SocialOwnerChanged",true));return;}
                if(error != null) { Deliver(done, SocialReply82<T>.Fail(error, unknown, unknown ? null : pending.refusal)); return; }
                T value; try { value = parse(json); } catch(Exception) { Deliver(done, SocialReply82<T>.Fail("SocialBoundResponseInvalid", method != "GET")); return; }
                Deliver(done, SocialReply82<T>.Ok(value));
            };
            active = pending;
            try { dispatch(Exchange(pending, method, path, body)); }
            catch(Exception) { Complete(pending, null, "SocialDispatchUnavailable", method != "GET"); pending.Release(); }
        }
        IEnumerator Exchange(Pending pending, string method, string path, string body) {
            try {
                UnityWebRequestAsyncOperation sent = null; Download download = null;
                try {
                    if(disposed || !SameAccess(pending.access) || pending.generation != Interlocked.Read(ref generation)) throw new InvalidOperationException();
                    var request = pending.request = new UnityWebRequest(origin + path, method); download = new Download();
                    request.downloadHandler = download; request.timeout = 15; request.redirectLimit = 0;
                    request.SetRequestHeader("Authorization", "Bearer " + pending.access.bearer); request.SetRequestHeader("Accept", "application/json");
                    if(body != null) { Need(Utf8.GetByteCount(body) <= 16384); request.uploadHandler = new UploadHandlerRaw(Utf8.GetBytes(body)); request.SetRequestHeader("Content-Type", "application/json"); }
                    sent = request.SendWebRequest();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    VerificationRequests++;
#endif
                } catch(Exception) { Complete(pending, null, "SocialRequestUnavailable", method != "GET"); }
                if(sent == null) yield break; yield return sent; if(pending.done) yield break;
                string text = null, error = null; bool unknown = method != "GET";
                try {
                    var request = pending.request; string type = request.GetResponseHeader("Content-Type");
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    if(statuses.Count < 256) statuses.Add((int)request.responseCode);
#endif
                    if(request.responseCode == 401 || request.responseCode == 410) revoked = true;
                    if(download.exceeded) error = "SocialResponseTooLarge";
                    else if(request.result != UnityWebRequest.Result.Success || request.responseCode != 200) { NetworkFailureLog.Report("social", request); error = request.responseCode == 0 ? "SocialNetworkUnavailable" : "SocialHttp" + request.responseCode; if(method != "GET" && FinalRefusal(request.responseCode)) { string wire = null; try { wire = download.Text(); } catch(Exception) { } unknown = false; pending.refusal = RefusalCode(request.responseCode, wire); } }
                    else if(type == null || !type.Split(';')[0].Trim().Equals("application/json", StringComparison.OrdinalIgnoreCase)) error = "SocialContentTypeInvalid";
                    else { text = download.Text(); unknown = false; }
                } catch(Exception) { error = "SocialResponseUnavailable"; }
                Complete(pending, text, error, unknown);
            } finally { if(!pending.done) Complete(pending, null, "SocialRequestStopped", method != "GET"); pending.Release(); }
        }
        // The server returns a command's committed reply before any rule check, so
        // one of these answers proves this command did not commit.
        public static bool FinalRefusal(long status) => status == 400 || status == 403 || status == 404 || status == 409 || status == 422 || status == 429;
        public static string RefusalCode(long status, string wire) {
            try { string code = SocialJson82.Text(SocialJson82.Read(wire), "error", 64); if(Regex.IsMatch(code, "\\A[a-z0-9_]{1,64}\\z")) return code; } catch(Exception) { }
            return status == 429 ? "rate_limited" : "refused";
        }
        bool Input<T>(Action<SocialReply82<T>> done, Action validate) where T : class {
            if(done == null) throw new ArgumentNullException(nameof(done));
            try { validate(); return true; } catch(Exception) { Deliver(done, SocialReply82<T>.Fail("InvalidExplicitSocialCommand")); return false; }
        }
        static string Segment(string value) { Need(Id(value)); return value; }
        static string Kind(string value) { Need(value == "Direct" || value == "Team"); return value; }
        static string PageQuery(string after, int limit) { Cursor(after); Need(limit >= 1 && limit <= 100); return "?after=" + after + "&limit=" + limit.ToString(CultureInfo.InvariantCulture); }
        public void GetProfile(string target, Action<SocialReply82<SocialProfile82>> done) {
            if(!Input(done, () => Segment(target))) return;
            Send("GET", "/v1/players/" + target, null, json => Read<SocialProfile82>(json, row => Need(Profile(row) == target)), done);
        }
        public void GetRelationship(string target, Action<SocialReply82<SocialRelationship82>> done) {
            if(!Input(done, () => { Segment(target); Need(target != player); })) return;
            Send("GET", "/v1/friends/relationship/" + target, null, json => Read<SocialRelationship82>(json, row => {
                Need(Text(row,"playerId",32)==target); string state=Text(row,"state",16);
                Need(new[]{"None","Friends","Incoming","Outgoing"}.Contains(state));
                if(state=="Incoming"||state=="Outgoing") Need(Id(Text(row,"requestId",32)));
                else Need(!row.ContainsKey("requestId"));
            }), done);
        }
        public void GetFriends(string after, int limit, Action<SocialReply82<SocialFriends82>> done) {
            string query = null; if(!Input(done, () => query = PageQuery(after, limit))) return;
            Send("GET", "/v1/friends" + query, null, json => Read<SocialFriends82>(json, row => { Page(row); foreach(var item in Array(row, "friends", limit)) Need(Profile(Obj(item)) != player); }), done);
        }
        public void GetRequests(string after, int limit, Action<SocialReply82<SocialRequests82>> done) {
            string query = null; if(!Input(done, () => query = PageQuery(after, limit))) return;
            Send("GET", "/v1/friends/requests" + query, null, json => Read<SocialRequests82>(json, row => {
                Page(row); foreach(var item in Array(row, "requests", limit)) { var value = Obj(item); Need(Id(Text(value, "requestId", 32)) && new[] { "incoming", "outgoing" }.Contains(Text(value, "direction", 8)) && Text(value, "state", 16) == "Pending"); Need(Profile(Obj(SocialJson82.Field(value, "profile"))) != player); Number(value, "createdAt", 1); }
            }), done);
        }
        public void GetBlocks(string after, int limit, Action<SocialReply82<SocialBlocks82>> done) {
            string query = null; if(!Input(done, () => query = PageQuery(after, limit))) return;
            Send("GET", "/v1/blocks" + query, null, json => Read<SocialBlocks82>(json, row => { Page(row); foreach(var item in Array(row, "blocks", limit)) { var value = Obj(item); Need(Id(Text(value, "playerId", 32))); Number(value, "createdAt", 1); } }), done);
        }
        public void GetTeams(string after, int limit, Action<SocialReply82<SocialTeams82>> done)=>GetTeams(after,limit,"",done);
        public void GetTeams(string after, int limit,string search, Action<SocialReply82<SocialTeams82>> done) {
            string query = null; if(!Input(done, () => {string clean;Need(TryTeamSearch109(search,out clean));query=PageQuery(after,limit)+(clean.Length==0?"":"&query="+Uri.EscapeDataString(clean));})) return;
            Send("GET", "/v1/teams" + query, null, json => Read<SocialTeams82>(json, row => {
                Page(row); object own = SocialJson82.Field(row, "myTeamId"); Need(own == null || own is string && Id((string)own)); foreach(var item in Array(row, "teams", limit)) Team(Obj(item));
            }), done);
        }
        public void GetTeam(string target, Action<SocialReply82<SocialTeam82>> done) {
            if(!Input(done, () => Segment(target))) return;
            Send("GET", "/v1/teams/" + target, null, json => Read<SocialTeam82>(json, row => {
                Need(Team(row) == target); bool member = Flag(row, "isMember"); if(member) foreach(var item in Array(row, "members")) { var value = Obj(item); Need(Id(Text(value, "playerId", 32))); Name(Text(value, "displayName", 512)); Flag(value, "isOwner"); }
                if(member && row.ContainsKey("membershipVersion")) { string version=Text(row,"membershipVersion",32,true); Need(version.Length==0 || Id(version)); Flag(row,"leaveClosesTeam"); Need(new[]{"","transfer_ownership_first"}.Contains(Text(row,"leaveRestrictionReason",64,true))); }
            }), done);
        }
        public void GetMessages(string kind, string target, long after, int limit, Action<SocialReply82<SocialMessages82>> done) {
            if(!Input(done, () => { Kind(kind); Segment(target); Need(after >= 0 && limit >= 1 && limit <= 100); })) return;
            string query = "?after=" + after.ToString(CultureInfo.InvariantCulture) + "&limit=" + limit.ToString(CultureInfo.InvariantCulture);
            Send("GET", "/v1/messages/" + kind + "/" + target + query, null, json => Read<SocialMessages82>(json, row => {
                Flag(row, "hasMore"); Number(row, "nextCursor", after); Number(row, "unreadCount"); long previous = after;
                foreach(var item in Array(row, "messages", limit)) { var value = Obj(item); Need(previous < long.MaxValue && Id(Text(value, "messageId", 32)) && Id(Text(value, "authorId", 32))); Name(Text(value, "displayName", 512)); UserText(Text(value, "text", 2000), 1000, multiline: true); previous = Number(value, "sequence", previous + 1); Number(value, "createdAt", 1); }
            }), done);
        }
        // Explicit bounded history modes; the historical forward API and its
        // response contract remain unchanged for existing callers.
        public void GetMessagesTail(string kind,string target,int limit,Action<SocialReply82<SocialMessages82>> done) => BoundedMessages(kind,target,0,true,limit,done);
        public void GetMessagesBefore(string kind,string target,long before,int limit,Action<SocialReply82<SocialMessages82>> done) => BoundedMessages(kind,target,before,false,limit,done);
        void BoundedMessages(string kind,string target,long before,bool tail,int limit,Action<SocialReply82<SocialMessages82>> done) {
            if(!Input(done,()=>{Kind(kind);Segment(target);Need(limit>=1&&limit<=8&&(tail||before>0));}))return;
            string query=(tail?"?tail=true":"?before="+before.ToString(CultureInfo.InvariantCulture))+"&limit="+limit.ToString(CultureInfo.InvariantCulture);
            Send("GET","/v1/messages/"+kind+"/"+target+query,null,json=>ReadBoundedMessages(json,before,tail,limit),done);
        }
        SocialMessages82 ReadBoundedMessages(string json,long before,bool tail,int limit) {
            Need(limit>=1&&limit<=8&&(tail||before>0)&&Utf8.GetByteCount(json)<=Limit);
            return Read<SocialMessages82>(json,row=>{
                bool newer=Flag(row,"hasNewer");Need(Flag(row,"hasMore")==newer&&(!tail||!newer));Flag(row,"hasOlder");Number(row,"unreadCount");
                var items=Array(row,"messages",limit);long previous=0,first=0;
                foreach(var item in items){var value=Obj(item);Need(Id(Text(value,"messageId",32))&&Id(Text(value,"authorId",32)));Name(Text(value,"displayName",512));UserText(Text(value,"text",2000),1000,multiline:true);Need(previous<long.MaxValue);previous=Number(value,"sequence",previous+1);if(first==0)first=previous;Need(tail||previous<before);Number(value,"createdAt",1);}
                Need(Number(row,"nextCursor")==previous&&Number(row,"olderCursor")==first);
                if(first==0)Need(!Flag(row,"hasOlder"));
            });
        }

        public void GetRecords(long after, int limit, Action<SocialReply82<SocialRecords82>> done) {
            if(!Input(done, () => Need(after >= 0 && limit >= 1 && limit <= 100))) return;
            Send("GET", "/v1/records?after=" + after.ToString(CultureInfo.InvariantCulture) + "&limit=" + limit, null, json => Read<SocialRecords82>(json, row => {
                Number(row, "completedLevels", 0, 50); Flag(row, "hasMore"); Need(!Flag(row, "clientScoresAccepted") && Text(row, "scoreSource", 64) == "server_verified_completed_levels"); Number(row, "nextCursor", after);
                foreach(var count in Obj(SocialJson82.Field(row, "attempts"))) Need(new[] { "Reserved", "Started", "AwaitingContinuation", "Won", "Lost", "Cancelled", "Released" }.Contains(count.Key) && count.Value is long && (long)count.Value >= 0 && (long)count.Value <= int.MaxValue);
                long previous = after; foreach(var item in Array(row, "firstClears", limit)) { var value = Obj(item); Need(previous < 50); previous = Number(value, "level", previous + 1, 50); Number(value, "verifiedAt", 1); }
            }), done);
        }
        public void GetLeaderboard(string scope, int offset, int limit, Action<SocialReply82<SocialLeaderboard82>> done) {
            if(!Input(done, () => Need(new[] { "global", "regional", "friends", "team" }.Contains(scope) && offset >= 0 && offset <= 10000 && limit >= 1 && limit <= 100))) return;
            Send("GET", "/v1/leaderboards/" + scope + "?offset=" + offset + "&limit=" + limit, null, json => Read<SocialLeaderboard82>(json, row => {
                Need(Text(row, "scope", 16) == scope && Text(row, "scoreSource", 64) == "server_verified_completed_levels" && Flag(row, "tiesShareRank") && !Flag(row, "rewardGranted")); Flag(row, "hasMore"); Number(row, "nextOffset", offset, offset + limit);
                if(scope=="regional")Need(CountryRegion89.Normalize(Text(row,"regionCode",2))==Text(row,"regionCode",2));
                foreach(var item in Array(row, "entries", limit)) { var value = Obj(item); Need(Id(Text(value, "playerId", 32))); Name(Text(value, "displayName", 512)); Number(value, "score", 0, 50); Number(value, "rank", 1); }
            }), done);
        }
        public void GetRegion(Action<SocialReply82<SocialRegion89>> done)=>Send("GET","/v1/region",null,json=>Read<SocialRegion89>(json,row=>{
            Need(Text(row,"playerId",32)==player&&Text(row,"regionSource",64)=="player_selected_country"&&!Flag(row,"locationVerified"));string code=Text(row,"regionCode",2,true);Need(code==""||CountryRegion89.Normalize(code)==code);
        }),done);
        public void GetTeamLeaderboard(string scope,int offset,int limit,Action<SocialReply82<SocialTeamLeaderboard89>> done){
            if(!Input(done,()=>Need((scope=="global"||scope=="regional")&&offset>=0&&offset<=10000&&limit>=1&&limit<=100)))return;
            Send("GET","/v1/team-leaderboards/"+scope+"?offset="+offset+"&limit="+limit,null,json=>Read<SocialTeamLeaderboard89>(json,row=>{
                Need(Text(row,"scope",16)==scope&&Text(row,"scoreSource",64)=="server_verified_opted_in_team_completed_levels"&&Text(row,"teamRegionSource",64)=="current_leader_selected_country"&&Flag(row,"tiesShareRank")&&!Flag(row,"rewardGranted"));
                Flag(row,"hasMore");Number(row,"nextOffset",offset,offset+limit);string code=Text(row,"regionCode",2,true);Need(scope=="global"?code=="":code.Length==2&&CountryRegion89.Normalize(code)==code);
                foreach(var item in Array(row,"entries",limit)){var value=Obj(item);Need(Id(Text(value,"teamId",32)));UserText(Text(value,"name",64),32);Number(value,"score",0,5000);Number(value,"memberCount",0,100);Number(value,"rank",1);}
            }),done);
        }
        void Mutate(string operation, string path, object body, string command, Action<SocialReply82<SocialMutation82>> done) {
            SocialPendingCommand82 pending = null;
            if(!Input(done, () => {
                Need(Id(command));
                // Validate original strings before a serializer could replace a
                // malformed UTF16 sequence with U+FFFD and silently change UGC.
                if(body is ProfileCommand profile) Name(profile.displayName);
                else if(body is ProfileNameCommand rename) Name(rename.displayName);
                else if(body is TeamCommand team) { Need(Scalars(UserText(team.name,32))>=2);UserText(team.description,160,true); }
                else if(body is TeamBadgeCommand badge) {Need(Scalars(UserText(badge.name,32))>=2);UserText(badge.description,160,true);Need(HeartOfTheRain.App.TeamsAccess.TeamsAccessBadges109.Valid(badge.badgeId));}
                else if(body is TextCommand text) UserText(text.text,1000,multiline:true);
                else if(body is ReportCommand report) UserText(report.details,500,true,true);
                else if(body is UgcCommand ugc) UserText(ugc.details,500,true,true);
                pending = new SocialPendingCommand82 { operation = operation, path = path, body = JsonUtility.ToJson(body), commandId = command }; ValidateCommand(pending);
            })) return;
            DispatchMutation(pending, done);
        }
        void DispatchMutation(SocialPendingCommand82 pending, Action<SocialReply82<SocialMutation82>> done) {
            if(done == null) throw new ArgumentNullException(nameof(done));
            if(ownerThread != Thread.CurrentThread.ManagedThreadId || !Configured || Busy) { Deliver(done, SocialReply82<SocialMutation82>.Fail("SocialClientUnavailable")); return; }
            if(!DurableOwner()){Deliver(done,SocialReply82<SocialMutation82>.Fail("SocialOwnerChanged"));return;}
            if(journal == null) { Deliver(done, SocialReply82<SocialMutation82>.Fail("SocialProtectedOutboxRequired")); return; }
            try { ValidateCommand(pending); journal.Prepare(pending); }
            catch(Exception) { Deliver(done, SocialReply82<SocialMutation82>.Fail("SocialIntentSaveUnconfirmed", true)); return; }
            Send("POST", pending.path, pending.body, json => {
                var value = Mutation(json, pending);
                try { journal.Confirm(pending); }
                catch(Exception) { if(journal.Pending != null) throw; }
                return value;
            }, reply => {
                if(reply.refusal != null) {
                    try { journal.Confirm(pending); }
                    catch(Exception) {
                        bool remains = true; try { remains = journal.Pending != null; } catch(Exception) { }
                        if(remains) { Deliver(done, SocialReply82<SocialMutation82>.Fail("SocialRefusalClearUnconfirmed", true)); return; }
                    }
                }
                Deliver(done, reply);
            });
        }
        public void ResumePending(Action<SocialReply82<SocialMutation82>> done) {
            if(done == null) throw new ArgumentNullException(nameof(done));
            SocialPendingCommand82 pending;
            try { pending = journal?.Pending; if(pending == null) throw new InvalidOperationException(); }
            catch(Exception) { Deliver(done, SocialReply82<SocialMutation82>.Fail("NoReadablePendingSocialCommand")); return; }
            DispatchMutation(pending, done);
        }
        static string ServerOperation(SocialPendingCommand82 pending) {
            ValidateCommand(pending);
            if(pending.operation=="invite.send"){var parts=pending.path.Split('/');return "social.invite.send/"+parts[3]+"/"+parts[5];}
            if(pending.operation=="mail.claim-owned")return "social.mail.claim-owned/"+pending.path.Split('/')[4];
            if(pending.operation=="mail.read"||pending.operation=="mail.claim"){var parts=pending.path.Split('/');return "social."+pending.operation+"/"+parts[3]+"/"+parts[5];}
            if(pending.operation=="life.request")return "social.life.request/"+pending.path.Split('/')[3];
            if(pending.operation=="life.help"){var parts=pending.path.Split('/');return "social.life.help/"+parts[3]+"/"+parts[5];}
            if(pending.operation=="life.claim")return "social.life.claim/"+pending.path.Split('/')[3];
            if(pending.operation == "block.add") return "social.block";
            if(pending.operation == "block.remove") return "social.unblock";
            if(pending.operation == "message.report") return "social.report";
            if(pending.operation == "message.send" || pending.operation == "message.read") {
                var path = pending.path.Split('/'); return "social." + pending.operation + "/" + path[3] + "/" + path[4];
            }
            if(pending.operation.StartsWith("team.", StringComparison.Ordinal) && pending.operation != "team.create") return "social." + pending.operation + "/" + pending.path.Split('/')[3];
            return "social." + pending.operation;
        }
        public void ReconcilePending(Action<SocialReply82<SocialOperationReceipt82>> done) {
            if(done == null) throw new ArgumentNullException(nameof(done));
            SocialPendingCommand82 pending; string operation;
            try { pending = journal?.Pending; if(pending == null) throw new InvalidOperationException(); operation = ServerOperation(pending); }
            catch(Exception) { Deliver(done, SocialReply82<SocialOperationReceipt82>.Fail("NoReadablePendingSocialCommand")); return; }
            Send("GET", "/v1/social/operations/" + pending.commandId + "?operation=" + Uri.EscapeDataString(operation), null, json => Read<SocialOperationReceipt82>(json, row => {
                Need(Text(row, "commandId", 32) == pending.commandId && Text(row, "operation", 128) == operation && Text(row, "receiptScope", 64) == "owner_operation_receipt");
                string status = Text(row, "status", 16); Need(status == "Absent" || status == "Committed");
                if(status == "Committed") {
                    Need(Regex.IsMatch(Text(row, "payloadDigest", 64), "\\A[0-9a-f]{64}\\z") && Text(row, "digestScope", 64) == "server_normalized_model_not_client_json");
                    // The server hashes its normalized typed model. Do not
                    // pretend an arbitrary JsonUtility byte hash proves equality.
                    Mutation(SocialJson82.Write(Obj(SocialJson82.Field(row, "response"))), pending);
                } else Need(!row.ContainsKey("response") && !row.ContainsKey("payloadDigest"));
            }), reply => {
                if(reply.Succeeded && reply.value.status == "Committed") {
                    try { journal.Confirm(pending); }
                    catch(Exception) {
                        try { if(journal.Pending == null) { Deliver(done, reply); return; } } catch(Exception) { }
                        Deliver(done, SocialReply82<SocialOperationReceipt82>.Fail("SocialIntentClearUnconfirmed", true)); return;
                    }
                }
                // Absent is an observation, not proof that a concurrent send
                // failed. Keep the pending intent until explicit caller action.
                Deliver(done, reply);
            });
        }
        public bool AcknowledgeAndDiscardPending(string expectedCommandId, bool acknowledgesMayAlreadyBeCommitted, out string error) {
            error = null;
            if(ownerThread != Thread.CurrentThread.ManagedThreadId || !Configured || Busy || journal == null || !acknowledgesMayAlreadyBeCommitted) { error = "ExplicitSocialDiscardAcknowledgementRequired"; return false; }
            try { var pending = journal.Pending; if(pending == null || pending.commandId != expectedCommandId) { error = "SocialOutboxChanged"; return false; } }
            catch(Exception) { error = "SocialOutboxUnreadable"; return false; }
            try { journal.AcknowledgeAndDiscard(expectedCommandId, true); return true; }
            catch(Exception) {
                try { if(journal.Pending == null) return true; } catch(Exception) { }
                error = "SocialDiscardSaveUnconfirmed"; return false;
            }
        }
        static Dictionary<string, object> ValidateCommand(SocialPendingCommand82 pending) {
            Need(pending != null && Id(pending.commandId)); var row = SocialJson82.Read(pending.body); Need(Text(row, "commandId", 32) == pending.commandId);
            string expected = null;
            switch(pending.operation) {
                case "profile": expected = "/v1/profile"; Name(Text(row, "displayName", 512)); Flag(row, "leaderboardOptIn"); break;
                case "profile.name": expected = "/v1/profile/name"; Need(row.Count==2);Name(Text(row,"displayName",512));break;
                case "profile.consent": expected = "/v1/profile/leaderboard-consent";Need(row.Count==2);Flag(row,"leaderboardOptIn");break;
                case "region.set": expected="/v1/region";Need(row.Count==2&&CountryRegion89.Normalize(Text(row,"regionCode",2))==Text(row,"regionCode",2));break;
                case "friend.send": expected = "/v1/friends/request"; Segment(Text(row, "playerId", 32)); break;
                case "friend.remove": expected = "/v1/friends/remove"; Segment(Text(row, "playerId", 32)); break;
                case "friend.respond": expected = "/v1/friends/respond"; Segment(Text(row, "requestId", 32)); Need(new[] { "accept", "decline", "cancel" }.Contains(Text(row, "action", 16))); break;
                case "block.add": case "block.remove": expected = "/v1/blocks/" + (pending.operation == "block.add" ? "add" : "remove"); Segment(Text(row, "playerId", 32)); break;
                case "team.create": expected = "/v1/teams"; Need(Scalars(UserText(Text(row, "name", 64), 32)) >= 2); UserText(Text(row, "description", 320, true), 160, true);if(row.ContainsKey("badgeId"))Need(HeartOfTheRain.App.TeamsAccess.TeamsAccessBadges109.Valid(Text(row,"badgeId",16))); break;
                case "team.join": case "team.leave": case "team.transfer": case "team.kick": case "team.unban": {
                    string action = pending.operation.Substring(5); Need(Regex.IsMatch(pending.path ?? "", "\\A/v1/teams/[0-9a-f]{32}/" + (action == "join" || action == "leave" ? action : "members/" + action) + "\\z"));
                    if(action != "join" && action != "leave") Segment(Text(row, "playerId", 32)); if(action=="leave" && row.ContainsKey("expectedMembershipVersion")) { Need(row.Count==2); Segment(Text(row,"expectedMembershipVersion",32)); } break;
                }
                case "message.send": case "message.read": Need(Regex.IsMatch(pending.path ?? "", "\\A/v1/messages/(Direct|Team)/[0-9a-f]{32}" + (pending.operation == "message.read" ? "/read" : "") + "\\z")); if(pending.operation == "message.send") UserText(Text(row, "text", 2000), 1000, multiline: true); else Number(row, "through"); break;
                case "message.report": expected = "/v1/reports"; Segment(Text(row, "messageId", 32)); Need(new[] { "Spam", "Abuse", "Threat", "Other" }.Contains(Text(row, "reason", 32))); UserText(Text(row, "details", 1000, true), 500, true, true); break;
                case "ugc.report": expected = "/v1/ugc/reports"; Need(new[] { "Profile", "Team" }.Contains(Text(row, "kind", 16))); Segment(Text(row, "targetId", 32)); Need(new[] { "Spam", "Abuse", "Threat", "Impersonation", "Other" }.Contains(Text(row, "reason", 32))); UserText(Text(row, "details", 1000, true), 500, true, true); break;
                case "mail.claim-owned":Need(row.Count==1&&Regex.IsMatch(pending.path??"","\\A/v1/mail/rewards/[0-9a-f]{32}/claim\\z"));break;
                case "invite.send":Need(row.Count==1&&Regex.IsMatch(pending.path??"","\\A/v1/teams/[0-9a-f]{32}/invitations/[0-9a-f]{32}\\z"));break;
                case "mail.read":case "mail.claim":Need(row.Count==1&&Regex.IsMatch(pending.path??"","\\A/v1/teams/[0-9a-f]{32}/mail/[0-9a-f]{32}/"+(pending.operation=="mail.read"?"read":"claim")+"\\z"));break;
                case "life.request":Need(row.Count==1&&Regex.IsMatch(pending.path??"","\\A/v1/teams/[0-9a-f]{32}/life-requests\\z"));break;
                case "life.help":Need(row.Count==1&&Regex.IsMatch(pending.path??"","\\A/v1/teams/[0-9a-f]{32}/life-requests/[0-9a-f]{32}/help\\z"));break;
                case "life.claim":Need(row.Count==1&&Regex.IsMatch(pending.path??"","\\A/v1/life-requests/[0-9a-f]{32}/claim\\z"));break;
                default: throw new FormatException();
            }
            Need(expected == null || pending.path == expected); return row;
        }
        SocialMutation82 Mutation(string json, SocialPendingCommand82 pending) {
            var request = ValidateCommand(pending); return Read<SocialMutation82>(json, row => {
                switch(pending.operation) {
                    case "profile": Need(Profile(row) == player); break;
                    case "profile.name": Need(Profile(row)==player);break;
                    case "profile.consent": Need(Profile(row)==player&&Flag(row,"leaderboardOptIn")==Flag(request,"leaderboardOptIn"));break;
                    case "region.set": Need(Text(row,"playerId",32)==player&&Text(row,"regionCode",2)==Text(request,"regionCode",2)&&Text(row,"regionSource",64)=="player_selected_country"&&!Flag(row,"locationVerified"));break;
                    case "friend.send": Need(Text(row, "playerId", 32) == Text(request, "playerId", 32)); string state = Text(row, "state", 16); Need(state == "Pending" || state == "Friends"); if(state == "Pending") Need(Id(Text(row, "requestId", 32))); break;
                    case "friend.respond": Need(Text(row, "requestId", 32) == Text(request, "requestId", 32) && Id(Text(row, "playerId", 32)) && Text(row, "playerId", 32) != player); Need(Text(row, "state", 16) == new Dictionary<string, string> { { "accept", "Accepted" }, { "decline", "Declined" }, { "cancel", "Cancelled" } }[Text(request, "action", 16)]); break;
                    case "friend.remove": Need(Text(row, "playerId", 32) == Text(request, "playerId", 32) && Text(row, "state", 16) == "Removed"); break;
                    case "block.add": case "block.remove": Need(Text(row, "playerId", 32) == Text(request, "playerId", 32) && Flag(row, "blocked") == (pending.operation == "block.add")); break;
                    case "team.create": Need(Id(Text(row, "teamId", 32)) && Text(row, "state", 16) == "Joined"); break;
                    case "team.join": Need(Text(row,"teamId",32)==pending.path.Split('/')[3] && Text(row,"state",16)=="Joined"); break;
                    case "team.leave": {Need(Text(row,"teamId",32)==pending.path.Split('/')[3]);string leaveState=Text(row,"state",16);if(leaveState=="Rejected")Need(request.ContainsKey("expectedMembershipVersion")&&new[]{"team_membership_changed","transfer_ownership_first","team_permission_denied","team_not_found"}.Contains(Text(row,"reason",64)));else Need(leaveState=="Left");break;}
                    case "team.transfer": case "team.kick": case "team.unban": Need(Text(row, "teamId", 32) == pending.path.Split('/')[3] && Text(row, "playerId", 32) == Text(request, "playerId", 32) && Text(row, "action", 16) == pending.operation.Substring(5)); break;
                    case "message.send": Need(Id(Text(row, "messageId", 32)) && Text(row, "state", 16) == "Sent"); Number(row, "sequence", 1); Number(row, "createdAt", 1); break;
                    case "message.read": Number(row, "through", Number(request, "through")); break;
                    case "message.report": case "ugc.report": Need(Id(Text(row, "reportId", 32)) && Text(row, "state", 16) == "Received"); if(pending.operation == "ugc.report") { Flag(row, "reviewPendingAtAcceptance"); Need(!Flag(row, "automatedDecision") && Text(row, "receiptScope", 64) == "immutable_submission_receipt"); } break;
                    case "life.request":case "life.help":case "life.claim":LifeReceipt110(row,pending);break;
                    case "mail.read":case "mail.claim":case "mail.claim-owned":MailReceipt111(row,pending);break;
                    case "invite.send":InviteReceipt112(row,pending);break;
                    default: throw new FormatException();
                }
            });
        }
        public void UpdateProfile(string commandId, string name, bool optIn, Action<SocialReply82<SocialMutation82>> done) => Mutate("profile", "/v1/profile", new ProfileCommand { commandId = commandId, displayName = name, leaderboardOptIn = optIn }, commandId, done);
        public void UpdateName(string commandId,string name,Action<SocialReply82<SocialMutation82>> done)=>Mutate("profile.name","/v1/profile/name",new ProfileNameCommand{commandId=commandId,displayName=name},commandId,done);
        public void UpdateLeaderboardConsent(string commandId,bool optIn,Action<SocialReply82<SocialMutation82>> done)=>Mutate("profile.consent","/v1/profile/leaderboard-consent",new ProfileConsentCommand{commandId=commandId,leaderboardOptIn=optIn},commandId,done);
        public void UpdateRegion(string commandId,string code,Action<SocialReply82<SocialMutation82>> done)=>Mutate("region.set","/v1/region",new RegionCommand{commandId=commandId,regionCode=code},commandId,done);
        public void RequestFriend(string commandId, string target, Action<SocialReply82<SocialMutation82>> done) => TargetMutation("friend.send", "/v1/friends/request", commandId, target, done);
        public void RespondFriend(string commandId, string requestId, string action, Action<SocialReply82<SocialMutation82>> done) => Mutate("friend.respond", "/v1/friends/respond", new RespondCommand { commandId = commandId, requestId = requestId, action = action }, commandId, done);
        public void RemoveFriend(string commandId, string target, Action<SocialReply82<SocialMutation82>> done) => TargetMutation("friend.remove", "/v1/friends/remove", commandId, target, done);
        public void Block(string commandId, string target, Action<SocialReply82<SocialMutation82>> done) => TargetMutation("block.add", "/v1/blocks/add", commandId, target, done);
        public void Unblock(string commandId, string target, Action<SocialReply82<SocialMutation82>> done) => TargetMutation("block.remove", "/v1/blocks/remove", commandId, target, done);
        void TargetMutation(string operation, string path, string commandId, string target, Action<SocialReply82<SocialMutation82>> done) => Mutate(operation, path, new TargetCommand { commandId = commandId, playerId = target }, commandId, done);
        public void CreateTeam(string commandId, string name, string description, Action<SocialReply82<SocialMutation82>> done) => Mutate("team.create", "/v1/teams", new TeamCommand { commandId = commandId, name = name, description = description }, commandId, done);
        public void CreateTeam(string commandId,string name,string description,string badgeId,Action<SocialReply82<SocialMutation82>> done)=>Mutate("team.create","/v1/teams",new TeamBadgeCommand{commandId=commandId,name=name,description=description,badgeId=badgeId},commandId,done);
        public void JoinTeam(string commandId, string teamId, Action<SocialReply82<SocialMutation82>> done) => TeamOperation("join", commandId, teamId, null, done);
        public void LeaveTeam(string commandId, string teamId, Action<SocialReply82<SocialMutation82>> done) => TeamOperation("leave", commandId, teamId, null, done);
        [Serializable] sealed class VersionedLeave113 { public string commandId, expectedMembershipVersion; }
        public void LeaveTeam113(string commandId,string teamId,string membershipVersion,Action<SocialReply82<SocialMutation82>> done) { if(!Input(done,()=>{Segment(teamId);Segment(membershipVersion);}))return; Mutate("team.leave","/v1/teams/"+teamId+"/leave",new VersionedLeave113{commandId=commandId,expectedMembershipVersion=membershipVersion},commandId,done); }
        public void ManageMember(string action, string commandId, string teamId, string target, Action<SocialReply82<SocialMutation82>> done) => TeamOperation(action, commandId, teamId, target, done);
        void TeamOperation(string action, string commandId, string teamId, string target, Action<SocialReply82<SocialMutation82>> done) {
            if(!Input(done, () => { Segment(teamId); Need(new[] { "join", "leave", "transfer", "kick", "unban" }.Contains(action)); })) return;
            bool member = action != "join" && action != "leave"; string path = "/v1/teams/" + teamId + "/" + (member ? "members/" : "") + action;
            Mutate("team." + action, path, member ? (object)new TargetCommand { commandId = commandId, playerId = target } : new Command { commandId = commandId }, commandId, done);
        }
        public void SendMessage(string commandId, string kind, string target, string text, Action<SocialReply82<SocialMutation82>> done) {
            if(!Input(done, () => { Kind(kind); Segment(target); })) return;
            Mutate("message.send", "/v1/messages/" + kind + "/" + target, new TextCommand { commandId = commandId, text = text }, commandId, done);
        }
        public void MarkRead(string commandId, string kind, string target, long through, Action<SocialReply82<SocialMutation82>> done) {
            // A read marker only ever moves forward and the next view repeats it, so a
            // lost reply must not occupy the durable outbox and block real writes.
            SocialPendingCommand82 marker = null;
            if(!Input(done, () => { Kind(kind); Segment(target); Need(Id(commandId)); marker = new SocialPendingCommand82 { operation = "message.read", path = "/v1/messages/" + kind + "/" + target + "/read", body = JsonUtility.ToJson(new ReadCommand { commandId = commandId, through = through }), commandId = commandId }; ValidateCommand(marker); })) return;
            Send("POST", marker.path, marker.body, json => Mutation(json, marker), done);
        }
        public void ReportMessage(string commandId, string messageId, string reason, string details, Action<SocialReply82<SocialMutation82>> done) => Mutate("message.report", "/v1/reports", new ReportCommand { commandId = commandId, messageId = messageId, reason = reason, details = details }, commandId, done);
        public void ReportPublicText(string commandId, string kind, string targetId, string reason, string details, Action<SocialReply82<SocialMutation82>> done) => Mutate("ugc.report", "/v1/ugc/reports", new UgcCommand { commandId = commandId, kind = kind, targetId = targetId, reason = reason, details = details }, commandId, done);
        public void Cancel() {
            Interlocked.Increment(ref generation); var pending = active; if(pending == null || ownerThread != Thread.CurrentThread.ManagedThreadId) return;
            try { pending.request?.Abort(); } catch(Exception) { } Complete(pending, null, "SocialClientCancelled", true); pending.Release();
        }
        public void Dispose() { if(disposed) return; Cancel(); disposed = true; }
    }
}

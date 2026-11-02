using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;

namespace HeartOfTheRain.App.OnlineSocial
{
    public sealed partial class SocialBackendClient82
    {
        public const int TeamMessageLimit110 = 1000;
        public static bool TryMessageDraft110(string value, out string clean)
        {
            clean = null;
            try { Need(value != null && value.Length <= 2000);UserText(value,TeamMessageLimit110,true,true);string text = value.Trim(); UserText(text, TeamMessageLimit110, multiline: true); clean = text; return true; }
            catch(Exception) { return false; }
        }
        static void LifePolicy110(Dictionary<string, object> row)
        {
            Need(Text(row,"version",32)=="team_help110_review_v1");Number(row, "capacity", 1, 5); Number(row, "cooldownSeconds", 1, 604800); Number(row, "lifetimeSeconds", 1, 604800); Need(!Flag(row, "helpSpendsDonorLives"));
        }
        void LifeRequest110(Dictionary<string, object> row, string team, bool ownerOnly)
        {
            Need(Id(Text(row, "requestId", 32)) && Id(Text(row, "messageId", 32)) && Id(Text(row, "eventId", 32)));
            string owner = Text(row, "playerId", 32); Need(Id(owner) && (!ownerOnly || owner == player));
            string id = Text(row, "teamId", 32); Need(Id(id) && (team == null || id == team)); Name(Text(row, "displayName", 512));
            Number(row, "sequence", 1); long created = Number(row, "createdAt", 1); Number(row, "closesAt", created); Number(row, "nextRequestAt", created);
            long required = Number(row, "required", 1, 5), received = Number(row, "received", 0, required), claimed = Number(row, "claimed", 0, received);
            Need(Number(row, "remaining", 0, received) == received - claimed);
            string state = Text(row, "state", 16); Need(new[] { "Open", "Claimable", "Claimed", "Expired", "Closed" }.Contains(state));
            Need(new[] { "None", "Full", "Expired", "MembershipEnded", "TeamClosed", "Moderated" }.Contains(Text(row, "closeReason", 24)));
            Need(new[]{"None","NotOwner","NotClosed","NoEntitlement","FullLives","WalletMigrationRequired","WalletRefundReviewRequired"}.Contains(Text(row,"collectBlockedReason",32)));
            bool helped = Flag(row, "helped"), canHelp = Flag(row, "canHelp"), canCollect = Flag(row, "canCollect");
            Need(!canHelp || owner != player && !helped && state == "Open" && received < required);
            Need(!canCollect || owner == player && state != "Open" && received > claimed);
        }
        public void GetTeamLives110(string team, long before, string[] messageIds, Action<SocialReply82<SocialLifeRequests110>> done)
        {
            string query = null;
            if(!Input(done, () => {
                Segment(team); Need(before >= 0); string[] ids = messageIds ?? new string[0]; Need(ids.Length <= 8 && (before==0||ids.Length==0) && ids.Distinct().Count() == ids.Length); foreach(string id in ids) Segment(id);
                query = "?limit=8" + (before == 0 ? "" : "&before=" + before.ToString(CultureInfo.InvariantCulture)) + (ids.Length == 0 ? "" : "&messageIds=" + string.Join(",", ids));
            })) return;
            Send("GET", "/v1/teams/" + team + "/life-requests" + query, null, json => Read<SocialLifeRequests110>(json, row => {
                Need(Text(row, "teamId", 32) == team); Number(row, "serverUtc", 1); Number(row, "nextRequestAt"); Number(row, "olderCursor"); Flag(row, "hasOlder"); LifePolicy110(Obj(SocialJson82.Field(row, "policy")));
                var seen = new HashSet<string>(StringComparer.Ordinal);var messages=new HashSet<string>(StringComparer.Ordinal);long previous=0;foreach(var item in Array(row, "requests", 8)) { var value = Obj(item); LifeRequest110(value, team, false);long sequence=Number(value,"sequence",1);Need(sequence>previous&&seen.Add(Text(value, "requestId", 32))&&messages.Add(Text(value,"messageId",32)));previous=sequence; }
                object own = SocialJson82.Field(row, "ownRequest"); if(own != null) LifeRequest110(Obj(own), team, true);
            }), done);
        }
        public void GetOwnedLives110(long after, Action<SocialReply82<SocialOwnedLives110>> done)
        {
            if(!Input(done, () => Need(after >= 0))) return;
            Send("GET", "/v1/life-requests/owned?after=" + after.ToString(CultureInfo.InvariantCulture) + "&limit=8", null, json => Read<SocialOwnedLives110>(json, row => {
                Number(row, "serverUtc", 1); Number(row, "nextCursor"); Flag(row, "hasMore"); LifePolicy110(Obj(SocialJson82.Field(row, "policy")));
                var seen = new HashSet<string>(StringComparer.Ordinal);var messages=new HashSet<string>(StringComparer.Ordinal);long previous=after;foreach(var item in Array(row, "requests", 8)) { var value = Obj(item); LifeRequest110(value, null, true);long sequence=Number(value,"sequence",1);Need(sequence>previous&&Number(value, "remaining", 1, 5) > 0 && seen.Add(Text(value, "requestId", 32))&&messages.Add(Text(value,"messageId",32)));previous=sequence; }
            }), done);
        }
        public void RequestTeamLives110(string commandId, string team, Action<SocialReply82<SocialMutation82>> done) => Mutate("life.request", "/v1/teams/" + team + "/life-requests", new Command { commandId = commandId }, commandId, done);
        public void HelpTeamLife110(string commandId, string team, string requestId, Action<SocialReply82<SocialMutation82>> done) => Mutate("life.help", "/v1/teams/" + team + "/life-requests/" + requestId + "/help", new Command { commandId = commandId }, commandId, done);
        public void ClaimTeamLives110(string commandId, string requestId, Action<SocialReply82<SocialMutation82>> done) => Mutate("life.claim", "/v1/life-requests/" + requestId + "/claim", new Command { commandId = commandId }, commandId, done);
        void LifeReceipt110(Dictionary<string,object> row,SocialPendingCommand82 pending)
        {
            Need(Text(row,"operation",16)==pending.operation&&Id(Text(row,"receiptId",32))&&Id(Text(row,"requestId",32))&&Id(Text(row,"teamId",32))&&Id(Text(row,"messageId",32))&&Id(Text(row,"eventId",32)));
            var parts=pending.path.Split('/');string state=Text(row,"state",24);
            if(pending.operation=="life.request")Need(Text(row,"teamId",32)==parts[3]&&state=="Requested");
            else if(pending.operation=="life.help")Need(Text(row,"teamId",32)==parts[3]&&Text(row,"requestId",32)==parts[5]&&state=="Sent");
            else Need(Text(row,"requestId",32)==parts[3]&&new[]{"Collected","PartiallyCollected","Deferred"}.Contains(state));
            Number(row,"createdAt",1);Number(row,"serverUtc",1);long received=Number(row,"received",0,5),claimed=Number(row,"claimed",0,received);Need(Number(row,"remaining",0,received)==received-claimed);
            long credit=Number(row,"creditedLives",0,pending.operation=="life.claim"?5:0);
            if(pending.operation=="life.claim") {Number(row,"walletRevision",1);long max=Number(row,"maxLives",5,5);Number(row,"lives",0,max);Number(row,"nextLifeAt");Need(state=="Deferred"?credit==0:credit>0);Need(credit<=claimed&&(state!="Collected"||received==claimed)&&(state!="PartiallyCollected"||received>claimed));}
        }
    }
}

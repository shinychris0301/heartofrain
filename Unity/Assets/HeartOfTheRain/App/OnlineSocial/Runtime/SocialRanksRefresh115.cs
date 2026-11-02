using System;
using System.Collections.Generic;
using System.Globalization;
using HeartOfTheRain.App.TeamsAccess;

namespace HeartOfTheRain.App.OnlineSocial {
 [Serializable] public sealed class SocialRankRefresh115 {
  public string scope,regionCode,scoreSource;public bool tiesShareRank,hasMore,rewardGranted,hasSelfEntry;
  public SocialRank82[] entries;public SocialRank82 selfEntry;public int nextOffset;
 }
 [Serializable] public sealed class SocialTeamRankRefresh115 {
  public string teamId,name,badgeId;public int score,memberCount;public long rank;
 }
 [Serializable] public sealed class SocialTeamRanksRefresh115 {
  public string scope,regionCode,scoreSource,teamRegionSource;public bool tiesShareRank,hasMore,rewardGranted,hasSelfEntry,hasTeam;
  public SocialTeamRankRefresh115[] entries;public SocialTeamRankRefresh115 selfEntry;public int nextOffset;
 }
 [Serializable] public sealed class SocialPlayerSearch115 { public SocialProfile82[] players;public SocialRelationship82[] relationships;public bool hasMore;public string nextCursor,requestQuery,requestCursor; }
 public sealed partial class SocialBackendClient82 {
  public static bool TryPlayerSearch115(string value,out string clean) {
   clean=null;try{Need(value!=null&&value.Length<=128);string n=value.Normalize().Trim();UserText(n,128);int count=System.Globalization.StringInfo.ParseCombiningCharacters(n).Length;Need(count>=2&&count<=20);clean=n;return true;}catch(Exception){return false;}
  }
  static bool SearchCursor115(string cursor){if(cursor==null||cursor.Length>128)return false;foreach(char c in cursor)if(!(c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='_'||c=='-'))return false;return true;}
  public void GetPlayerSearch115(string query,string after,int limit,Action<SocialReply82<SocialPlayerSearch115>> done) {
   string normalized=null;if(!Input(done,()=>{Need(TryPlayerSearch115(query,out normalized)&&normalized==query&&SearchCursor115(after)&&limit>=1&&limit<=100);}))return;
   Send("GET","/v1/friends/search?q="+Uri.EscapeDataString(query)+"&after="+Uri.EscapeDataString(after)+"&limit="+limit.ToString(CultureInfo.InvariantCulture),null,json=>{
    var page=Read<SocialPlayerSearch115>(json,row=>{bool more=Flag(row,"hasMore");string cursor=Text(row,"nextCursor",128,true);Need(SearchCursor115(cursor)&&(more?cursor.Length>0:cursor.Length==0));var seen=new HashSet<string>(StringComparer.Ordinal);foreach(var item in Array(row,"players",limit)){var profile=Obj(item);string id=Profile(profile);Need(id!=player&&Flag(profile,"leaderboardOptIn")&&seen.Add(id));}
     var relations=new HashSet<string>(StringComparer.Ordinal);var pendingIds=new HashSet<string>(StringComparer.Ordinal);foreach(var item in Array(row,"relationships",limit)){var relation=Obj(item);string id=Text(relation,"playerId",32),state=Text(relation,"state",16);Need(seen.Contains(id)&&relations.Add(id));Need(state=="None"||state=="Friends"||state=="Incoming"||state=="Outgoing");if(state=="Incoming"||state=="Outgoing"){string request=Text(relation,"requestId",32);Need(Id(request)&&pendingIds.Add(request));}else Need(!relation.ContainsKey("requestId"));}Need(relations.Count==seen.Count);});
    page.requestQuery=query;page.requestCursor=after;return page;
   },done);
  }
  void RankEntry115(Dictionary<string,object> row) {
   Need(Id(Text(row,"playerId",32)));Name(Text(row,"displayName",512));Number(row,"score",0,50);Number(row,"rank",1);
  }
  void TeamRankEntry115(Dictionary<string,object> row) {
   Need(Id(Text(row,"teamId",32)));UserText(Text(row,"name",64),32);Need(TeamsAccessBadges109.Valid(Text(row,"badgeId",32)));
   Number(row,"score",0,5000);Number(row,"memberCount",0,100);Number(row,"rank",1);
  }
  public void GetRanksRefresh115(string scope,int offset,int limit,Action<SocialReply82<SocialRankRefresh115>> done) {
   if(!Input(done,()=>Need((scope=="global"||scope=="regional")&&offset>=0&&offset<=10000&&limit>=1&&limit<=100)))return;
   Send("GET","/v1/leaderboards-refresh/"+scope+"?offset="+offset.ToString(CultureInfo.InvariantCulture)+"&limit="+limit.ToString(CultureInfo.InvariantCulture),null,json=>Read<SocialRankRefresh115>(json,row=>{
    Need(Text(row,"scope",16)==scope&&Text(row,"scoreSource",64)=="server_verified_completed_levels"&&Flag(row,"tiesShareRank")&&!Flag(row,"rewardGranted"));
    bool more=Flag(row,"hasMore");long next=Number(row,"nextOffset",offset,offset+limit);string code=Text(row,"regionCode",2,true);Need(scope=="global"?code=="":CountryRegion89.Normalize(code)==code&&code.Length==2);
    var seen=new HashSet<string>(StringComparer.Ordinal);long last=0,lastScore=long.MaxValue;
    var entries=Array(row,"entries",limit);Need(next==offset+entries.Count&&(!more||entries.Count>0));
    foreach(var item in entries){var value=Obj(item);RankEntry115(value);Need(seen.Add(Text(value,"playerId",32)));long rank=Number(value,"rank",1),score=Number(value,"score",0,50);Need(rank>=last&&score<=lastScore&&(last==0||rank!=last||score==lastScore));last=rank;lastScore=score;}
    object self=SocialJson82.Field(row,"selfEntry");bool has=Flag(row,"hasSelfEntry");Need(has==(self!=null));if(has){var value=Obj(self);RankEntry115(value);Need(Text(value,"playerId",32)==player);}
   }),done);
  }
  public void GetTeamRanksRefresh115(string scope,int offset,int limit,Action<SocialReply82<SocialTeamRanksRefresh115>> done) {
   if(!Input(done,()=>Need((scope=="global"||scope=="regional")&&offset>=0&&offset<=10000&&limit>=1&&limit<=100)))return;
   Send("GET","/v1/team-leaderboards-refresh/"+scope+"?offset="+offset.ToString(CultureInfo.InvariantCulture)+"&limit="+limit.ToString(CultureInfo.InvariantCulture),null,json=>Read<SocialTeamRanksRefresh115>(json,row=>{
    Need(Text(row,"scope",16)==scope&&Text(row,"scoreSource",64)=="server_verified_opted_in_team_completed_levels"&&Text(row,"teamRegionSource",64)=="current_leader_selected_country"&&Flag(row,"tiesShareRank")&&!Flag(row,"rewardGranted"));
    bool more=Flag(row,"hasMore");long next=Number(row,"nextOffset",offset,offset+limit);string code=Text(row,"regionCode",2,true);Need(scope=="global"?code=="":CountryRegion89.Normalize(code)==code&&code.Length==2);
    var seen=new HashSet<string>(StringComparer.Ordinal);long last=0,lastScore=long.MaxValue;
    var entries=Array(row,"entries",limit);Need(next==offset+entries.Count&&(!more||entries.Count>0));
    foreach(var item in entries){var value=Obj(item);TeamRankEntry115(value);Need(seen.Add(Text(value,"teamId",32)));long rank=Number(value,"rank",1),score=Number(value,"score",0,5000);Need(rank>=last&&score<=lastScore&&(last==0||rank!=last||score==lastScore));last=rank;lastScore=score;}
    object self=SocialJson82.Field(row,"selfEntry");bool has=Flag(row,"hasSelfEntry"),team=Flag(row,"hasTeam");Need(has==(self!=null)&&(!has||team));if(has)TeamRankEntry115(Obj(self));
   }),done);
  }
 }
 public sealed partial class SocialPageSession82 {
  public bool SearchPlayers115(string query,string cursor="")=>Read<SocialPlayerSearch115>(SocialPane82.PlayerSearch115,done=>client.GetPlayerSearch115(query,cursor,PageSize,done));
  public bool RefreshRanks115(string scope,int offset=0)=>Read<SocialRankRefresh115>(scope=="regional"?SocialPane82.RegionalRanks115:SocialPane82.GlobalRanks115,done=>client.GetRanksRefresh115(scope,offset,PageSize,done));
  public bool RefreshTeamRanks115(string scope,int offset=0)=>Read<SocialTeamRanksRefresh115>(scope=="regional"?SocialPane82.RegionalTeamRanks115:SocialPane82.GlobalTeamRanks115,done=>client.GetTeamRanksRefresh115(scope,offset,PageSize,done));
 }
}

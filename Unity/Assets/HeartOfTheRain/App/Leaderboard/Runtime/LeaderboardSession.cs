using System;using System.Collections.Generic;using System.Linq;
namespace HeartOfTheRain.App.Leaderboard
{
 [Serializable] public sealed class RankedPlayer {public string id,name,team,region,portrait,banner;public int level;public bool isSelf;}
 [Serializable] public sealed class RankedTeam {public string id,name,region,crest;public int members,capacity,score;}
 [Serializable] public sealed class LeaderboardSnapshot {public bool isDemo;public string localRegion;public RankedPlayer[] players;public RankedTeam[] teams;public string[] friendIds;}
 public enum LeaderboardTab {Friends,Players,Teams}
 public sealed class LeaderboardSession
 {
  public LeaderboardSnapshot Data {get;private set;}
  public LeaderboardTab Tab {get;private set;}=LeaderboardTab.Players;
  public bool Local {get;private set;} public bool Finding {get;private set;}
  public string Query {get;private set;}=""; public string ConfirmRemoveId {get;private set;}="";
  public string Notice {get;private set;}="";
  readonly HashSet<string> friends=new HashSet<string>(StringComparer.Ordinal),pending=new HashSet<string>(StringComparer.Ordinal);
  public LeaderboardSession(LeaderboardSnapshot data){ApplySnapshot(data);}
  public void ApplySnapshot(LeaderboardSnapshot data)
  {
   if(data==null||data.players==null||data.teams==null)throw new ArgumentException("Leaderboard snapshot is incomplete.");
   if(data.players.Any(p=>p==null||string.IsNullOrEmpty(p.id)||string.IsNullOrEmpty(p.name))||data.players.Select(p=>p.id).Distinct(StringComparer.Ordinal).Count()!=data.players.Length)throw new ArgumentException("Player IDs must be unique and named.");
   if(data.teams.Any(t=>t==null||string.IsNullOrEmpty(t.id)||string.IsNullOrEmpty(t.name))||data.teams.Select(t=>t.id).Distinct(StringComparer.Ordinal).Count()!=data.teams.Length)throw new ArgumentException("Team IDs must be unique and named.");
   if(data.players.Count(p=>p.isSelf)>1||data.players.Any(p=>p.level<1)||data.teams.Any(t=>t.members<0||t.capacity<1||t.members>t.capacity||t.score<0))throw new ArgumentException("Invalid ranking values.");
   Data=data;friends.Clear();pending.Clear();foreach(var id in data.friendIds??new string[0])if(Player(id)!=null&&!Player(id).isSelf)friends.Add(id);ConfirmRemoveId="";Notice="";
  }
  public RankedPlayer Player(string id)=>Data.players.FirstOrDefault(p=>p.id==id);
  public bool IsFriend(string id)=>friends.Contains(id);public bool IsPending(string id)=>pending.Contains(id);
  public void Select(LeaderboardTab tab){Tab=tab;ConfirmRemoveId="";Notice="";}
  public void SetLocal(bool value){Local=value;Notice="";}
  public void SetFinding(bool value){Finding=value;Query="";Notice="";ConfirmRemoveId="";}
  public void Search(string text){Query=(text??"").Trim();if(Query.Length>32)Query=Query.Substring(0,32);Notice="";}
  public RankedPlayer[] Players()=>Data.players.Where(p=>!Local||p.region==Data.localRegion).OrderByDescending(p=>p.level).ThenBy(p=>p.id,StringComparer.Ordinal).ToArray();
  public RankedTeam[] Teams()=>Data.teams.Where(t=>!Local||t.region==Data.localRegion).OrderByDescending(t=>t.score).ThenBy(t=>t.id,StringComparer.Ordinal).ToArray();
  public RankedPlayer[] Friends()=>Data.players.Where(p=>!p.isSelf&&(Finding?!friends.Contains(p.id):friends.Contains(p.id))&&(Query.Length==0||p.name.IndexOf(Query,StringComparison.OrdinalIgnoreCase)>=0||p.id.IndexOf(Query.TrimStart('#'),StringComparison.OrdinalIgnoreCase)>=0)).OrderBy(p=>p.name,StringComparer.OrdinalIgnoreCase).ThenBy(p=>p.id,StringComparer.Ordinal).ToArray();
  public int Rank(string id){return Array.FindIndex(Players(),p=>p.id==id)+1;}
  public bool Add(string id)
  {var p=Player(id);if(!Data.isDemo||p==null||p.isSelf||friends.Contains(id)||!pending.Add(id))return false;Notice="Request saved in this preview";return true;}
  public bool CancelRequest(string id){if(!Data.isDemo||!pending.Remove(id))return false;Notice="Preview request cancelled";return true;}
  public bool AskRemove(string id){if(!Data.isDemo||!friends.Contains(id))return false;ConfirmRemoveId=id;return true;}
  public bool ConfirmRemove(){string id=ConfirmRemoveId;ConfirmRemoveId="";if(!Data.isDemo||!friends.Remove(id))return false;Notice="Removed from preview friends";return true;}
  public void CancelRemove(){ConfirmRemoveId="";}
  public void UpdateSelfLevel(int level){var p=Data.players.FirstOrDefault(v=>v.isSelf);if(p!=null)p.level=Math.Max(1,level);}
 }
}

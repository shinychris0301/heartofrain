using System;using System.Linq;using System.Collections.Generic;
namespace HeartOfTheRain.App.Teams
{
 [Serializable] public sealed class TeamMember {public string id,name,role,portrait;public int level,helps;public bool online;}
 [Serializable] public sealed class TeamProfile {public string id,name,crest,description;public int score,capacity;public TeamMember[] members;}
 [Serializable] public sealed class TeamChatEntry {public string id,memberId,kind,body,timeLabel;public int received,goal;}
 [Serializable] public sealed class TeamLetter {public string id,subject,sender,summary,body,dateLabel;public bool unread;}
 [Serializable] public sealed class TeamsSnapshot {public bool isDemo;public string selfId,eventTitle,eventDetail;public int eventProgress,eventGoal;public TeamProfile team;public TeamChatEntry[] chat;public TeamLetter[] mail;}
 public enum TeamsTab {Chat,Info,Mail}
 public sealed class TeamsSession
 {
  public TeamsSnapshot Data {get;private set;}
  public TeamsTab Tab {get;private set;}=TeamsTab.Chat;
  public string OpenMailId {get;private set;}="";
  public bool Composing {get;private set;}
  public string Notice {get;private set;}="";
  readonly HashSet<string> helped=new HashSet<string>(StringComparer.Ordinal),read=new HashSet<string>(StringComparer.Ordinal);int sequence;
  public bool Modal=>Composing;
  public TeamsSession(TeamsSnapshot data){ApplySnapshot(data);}
  static bool Bad(string s)=>string.IsNullOrWhiteSpace(s);
  public void ApplySnapshot(TeamsSnapshot d)
  {
   if(d==null||d.team==null||d.team.members==null||d.chat==null||d.mail==null||Bad(d.selfId)||Bad(d.team.id)||Bad(d.team.name)||Bad(d.team.crest))throw new ArgumentException("Incomplete Teams snapshot.");
   var m=d.team.members;if(m.Length==0||m.Length>d.team.capacity||d.team.capacity<1||d.team.score<0||d.eventGoal<=0||d.eventProgress<0)throw new ArgumentException("Invalid team or event values.");
   if(m.Any(v=>v==null||Bad(v.id)||Bad(v.name)||Bad(v.portrait)||v.level<1||v.helps<0)||m.Select(v=>v.id).Distinct(StringComparer.Ordinal).Count()!=m.Length||!m.Any(v=>v.id==d.selfId))throw new ArgumentException("Invalid team member IDs or values.");
   if(d.chat.Any(c=>c==null||Bad(c.id)||!m.Any(v=>v.id==c.memberId)||(c.kind!="message"&&c.kind!="life")||(c.kind=="message"&&Bad(c.body))||(c.kind=="life"&&(c.goal<1||c.received<0||c.received>c.goal)))||d.chat.Select(c=>c.id).Distinct(StringComparer.Ordinal).Count()!=d.chat.Length)throw new ArgumentException("Invalid chat entries.");
   if(d.mail.Any(v=>v==null||Bad(v.id)||Bad(v.subject)||Bad(v.body))||d.mail.Select(v=>v.id).Distinct(StringComparer.Ordinal).Count()!=d.mail.Length)throw new ArgumentException("Invalid letters.");
   Data=new TeamsSnapshot{isDemo=d.isDemo,selfId=d.selfId,eventTitle=d.eventTitle??"",eventDetail=d.eventDetail??"",eventProgress=d.eventProgress,eventGoal=d.eventGoal,team=new TeamProfile{id=d.team.id,name=d.team.name,crest=d.team.crest,description=d.team.description??"",score=d.team.score,capacity=d.team.capacity,members=m.Select(v=>new TeamMember{id=v.id,name=v.name,role=v.role??"Member",portrait=v.portrait,level=v.level,helps=v.helps,online=v.online}).ToArray()},chat=d.chat.Select(c=>new TeamChatEntry{id=c.id,memberId=c.memberId,kind=c.kind,body=c.body??"",timeLabel=c.timeLabel??"",received=c.received,goal=c.goal}).ToArray(),mail=d.mail.Select(v=>new TeamLetter{id=v.id,subject=v.subject,sender=v.sender??"",summary=v.summary??"",body=v.body,dateLabel=v.dateLabel??"",unread=v.unread}).ToArray()};
   helped.Clear();read.Clear();sequence=0;Tab=TeamsTab.Chat;OpenMailId="";Composing=false;Notice="";
  }
  public TeamMember Member(string id)=>Data.team.members.FirstOrDefault(v=>v.id==id);
  public TeamMember[] Members()=>Data.team.members.OrderBy(v=>v.role=="Leader"?0:v.role=="Co-leader"?1:2).ThenByDescending(v=>v.level).ThenBy(v=>v.id,StringComparer.Ordinal).ToArray();
  public int UnreadCount=>Data.mail.Count(v=>v.unread&&!read.Contains(v.id));
  public bool IsUnread(string id)=>Data.mail.Any(v=>v.id==id&&v.unread)&&!read.Contains(id);
  public void Select(TeamsTab tab){if(!Enum.IsDefined(typeof(TeamsTab),tab))return;Tab=tab;OpenMailId="";Composing=false;Notice="";}
  public bool OpenMail(string id){if(!Data.mail.Any(v=>v.id==id))return false;Tab=TeamsTab.Mail;OpenMailId=id;read.Add(id);return true;}
  public void CloseMail(){OpenMailId="";}
  public bool BeginCompose(){if(!Data.isDemo||Tab!=TeamsTab.Chat)return false;Composing=true;Notice="";return true;}
  public void CancelCompose(){Composing=false;}
  public static string CleanMessage(string text)=>TeamsText.Limit(new string((text??"").Select(c=>char.IsControl(c)?' ':c).ToArray()).Trim(),120);
  string NextId(){string id;do{id="preview-"+(++sequence);}while(Data.chat.Any(v=>v.id==id));return id;}
  void Append(TeamChatEntry e){Data.chat=Data.chat.Concat(new[]{e}).ToArray();}
  public bool PostPreview(string text){string clean=CleanMessage(text);if(!Data.isDemo||!Composing||clean.Length==0)return false;Append(new TeamChatEntry{id=NextId(),memberId=Data.selfId,kind="message",body=clean,timeLabel="Now"});Composing=false;Notice="Added to this preview only";return true;}
  public bool HasLifeRequest=>Data.chat.Any(v=>v.kind=="life"&&v.memberId==Data.selfId&&v.received<v.goal);
  public bool RequestLives(){if(!Data.isDemo||HasLifeRequest||Composing)return false;Append(new TeamChatEntry{id=NextId(),memberId=Data.selfId,kind="life",body="",timeLabel="Now",received=0,goal=5});Tab=TeamsTab.Chat;Notice="Life request added to this preview";return true;}
  public bool CanHelp(string id){var v=Data.chat.FirstOrDefault(c=>c.id==id);return Data.isDemo&&v!=null&&v.kind=="life"&&v.memberId!=Data.selfId&&v.received<v.goal&&!helped.Contains(id);}
  public bool Help(string id){if(Composing||!CanHelp(id))return false;helped.Add(id);Data.chat.First(v=>v.id==id).received++;Member(Data.selfId).helps++;Notice="Help recorded in this preview";return true;}
  public bool Helped(string id)=>helped.Contains(id);
  public void UpdateSelfLevel(int level){if(Data.isDemo)Member(Data.selfId).level=Math.Max(1,level);}
 }
}

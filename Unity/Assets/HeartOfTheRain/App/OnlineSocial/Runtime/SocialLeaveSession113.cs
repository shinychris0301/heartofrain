using System;
namespace HeartOfTheRain.App.OnlineSocial {
 public sealed partial class SocialPageSession82 {
  string lastLeaveTeam113,lastLeaveCommand113,lastLeaveState113,lastLeaveReason113,lastLeaveVersion113;
  [Serializable] sealed class LeaveIntent113 { public string commandId,expectedMembershipVersion; }
  public string LastLeaveTeam113=>ActiveOwner()?lastLeaveTeam113:null;
  public string LastLeaveCommand113=>ActiveOwner()?lastLeaveCommand113:null;
  public string LastLeaveState113=>ActiveOwner()?lastLeaveState113:null;
  public string LastLeaveReason113=>ActiveOwner()?lastLeaveReason113:null;
  public string LastLeaveVersion113=>ActiveOwner()?lastLeaveVersion113:null;
  void AcceptedLeave113(SocialPendingCommand82 pending,SocialMutation82 receipt){
   if(pending==null||pending.operation!="team.leave"||receipt==null||(receipt.state!="Left"&&receipt.state!="Rejected"))return;
   var parts=pending.path.Split('/');if(parts.Length!=5||receipt.teamId!=parts[3])return;
   lastLeaveTeam113=parts[3];lastLeaveCommand113=pending.commandId;lastLeaveState113=receipt.state;lastLeaveReason113=receipt.reason;lastLeaveVersion113="";
   try{var body=SocialJson82.Read(pending.body);if(body.ContainsKey("expectedMembershipVersion"))lastLeaveVersion113=SocialJson82.Text(body,"expectedMembershipVersion",32);}catch(Exception){}
   if(receipt.state=="Left")InvalidateDepartedTeam113(parts[3],lastLeaveVersion113);
   // Membership may have changed again since the leave committed. The UI must
   // refresh the directory before routing; do not clear a later team's cache.
  }
  void InvalidateDepartedTeam113(string previousTeam,string previousVersion){
   if(teamId!=previousTeam)return;object cached;var team=views.TryGetValue(SocialPane82.TeamInfo,out cached)?cached as SocialTeam82:null;
   // A differing, already-confirmed membership version may belong to a newer
   // incarnation. Do not erase that newer team; otherwise clear only old scope.
   if(team!=null&&!string.IsNullOrEmpty(team.membershipVersion)&&!string.IsNullOrEmpty(previousVersion)&&team.membershipVersion!=previousVersion)return;
   foreach(var pane113 in new[]{SocialPane82.TeamInfo,SocialPane82.TeamChat,SocialPane82.TeamLives110,SocialPane82.TeamTail110,SocialPane82.TeamMail111,SocialPane82.TeamMailDetail111,SocialPane82.InviteFriends112}){views.Remove(pane113);states.Remove(pane113);}
   newTeamMessages110=false;messageViewportAtLatest=false;
  }
  public bool LeaveTeam113(string command,string expectedTeam,string version){
   if(teamId!=expectedTeam||string.IsNullOrEmpty(version))return false;
   var target=teamId;var pending=new SocialPendingCommand82{commandId=command,operation="team.leave",path="/v1/teams/"+target+"/leave",body=UnityEngine.JsonUtility.ToJson(new LeaveIntent113{commandId=command,expectedMembershipVersion=version})};
   return Mutate(SocialPane82.TeamInfo,done=>client.LeaveTeam113(command,target,version,done),value=>AcceptedLeave113(pending,value));
  }
 }
}

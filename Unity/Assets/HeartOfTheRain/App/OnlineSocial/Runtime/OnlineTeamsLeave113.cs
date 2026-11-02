using System;
using System.Collections;
using HeartOfTheRain.App.TeamsLifecycle;
namespace HeartOfTheRain.App.OnlineSocial {
 public sealed partial class OnlineTeamsPage82 {
  string leaveTeam113="",leaveVersion113="",leaveName113="",leaveBadge113="",leaveSeen113="",leaveResult113="",leaveFailure113="";
  bool leaveCloses113,leaveSubmitting113,leaveNeedMembership113,leaveRefreshing113,leaveDismissed113,leaveAutoChecked113,leaveClosing113,leaveDeferredToast113;double leaveToastUntil113,leaveMotionAt113,leaveRetryAt113;
  void ResetLeave113(){leaveTeam113=leaveVersion113=leaveName113=leaveBadge113=leaveSeen113=leaveResult113=leaveFailure113="";leaveCloses113=leaveSubmitting113=leaveNeedMembership113=leaveRefreshing113=leaveDismissed113=leaveAutoChecked113=leaveClosing113=leaveDeferredToast113=false;leaveToastUntil113=leaveMotionAt113=leaveRetryAt113=0;}
  void ObserveLeave113(){
   if(session==null)return;
   var receipt=session.LastLeaveCommand113;
   if(!string.IsNullOrEmpty(receipt)&&receipt!=leaveSeen113){leaveSeen113=receipt;leaveTeam113=session.LastLeaveTeam113??"";leaveResult113=session.LastLeaveState113??"";leaveFailure113=session.LastLeaveReason113??"";leaveVersion113=session.LastLeaveVersion113??"";leaveNeedMembership113=true;leaveSubmitting113=false;}
   if(leaveSubmitting113&&!session.Busy)leaveSubmitting113=false;
  }
  string LeaveState113(){
   if(leaveRefreshing113||leaveSubmitting113)return "pending";if(leaveNeedMembership113)return "unknown";
   var pending=session?.PendingCommand;if(pending?.operation=="team.leave")return session.Busy?"pending":"unknown";
   if(session==null)return "unavailable";var state=session.Status(SocialPane82.TeamInfo);var team=session.Snapshot<SocialTeam82>(SocialPane82.TeamInfo);
   if(state.state==SocialViewState82.Offline)return "offline";
   if(state.state!=SocialViewState82.Ready||team==null||!team.isMember||team.teamId!=leaveTeam113||string.IsNullOrEmpty(team.membershipVersion)||team.membershipVersion!=leaveVersion113)return "unavailable";
   if(team.leaveRestrictionReason=="transfer_ownership_first"||leaveFailure113=="transfer_ownership_first")return "role";return !string.IsNullOrEmpty(leaveFailure113)?"failed":"confirm";
  }
  void FillLeaveView113(OnlineTeamsView82 value){
   // LeaveState113 validates a defensive team copy. Only the open modal
   // consumes that state; ordinary chat frames have no leave controls.
   value.leaveState113=modal=="leave113"?LeaveState113():"";value.leaveTeamName113=leaveName113;value.leaveBadge113=leaveBadge113;value.leaveClosesTeam113=leaveCloses113;value.leaveBusy113=session?.Busy==true||refreshing||leaveRefreshing113;value.leaveToast113=leaveToastUntil113>AuthorizationNow?TeamsLifecycleText113.T("left_toast"):"";
  }
  void PumpLeave113(){
   ObserveLeave113();if(session==null||closed)return;
   if(IsVisible&&modal=="leave113"&&leaveClosing113&&AuthorizationNow-leaveMotionAt113>=(home&&home.State.reduceMotion ? 0.12 : 0.16)){modal="";leaveClosing113=false;focusAfter109=returnFocus109;Reflow(ScrollPosition,true);}
   if(leaveToastUntil113>0&&AuthorizationNow>=leaveToastUntil113){leaveToastUntil113=0;if(IsVisible)Reflow(ScrollPosition,true);}
   var pending=session.PendingCommand;
   if(IsVisible&&pending?.operation=="team.leave"&&!leaveDismissed113&&modal.Length==0){
    var parts=pending.path.Split('/');if(parts.Length==5){leaveTeam113=parts[3];var team=session.Snapshot<SocialTeam82>(SocialPane82.TeamInfo);if(team?.teamId==leaveTeam113){leaveName113=team.name;leaveBadge113=team.badgeId;leaveVersion113=team.membershipVersion;leaveCloses113=team.leaveClosesTeam;}modal="leave113";leaveClosing113=false;leaveMotionAt113=AuthorizationNow;Reflow(ScrollPosition,true);}
   }
   if(pending?.operation=="team.leave"&&!leaveAutoChecked113&&!session.Busy&&!refreshing){leaveAutoChecked113=true;session.ReconcilePending();return;}
   if(!leaveNeedMembership113||leaveRefreshing113||session.Busy||refreshing||pending!=null||AuthorizationNow<leaveRetryAt113)return;
   leaveRefreshing113=true;Dispatch(RefreshAfterLeave113(session,loadGeneration,leaveTeam113,leaveSeen113));
  }
  IEnumerator RefreshAfterLeave113(SocialPageSession82 owner,int token,string previousTeam,string command){
   if(!owner.RefreshTeams()){leaveRefreshing113=false;leaveRetryAt113=AuthorizationNow+10;yield break;}while(owner.Busy)yield return null;
   if(closed||owner!=session||token!=loadGeneration){leaveRefreshing113=false;yield break;}
   if(owner.Status(SocialPane82.Teams).state!=SocialViewState82.Ready){leaveRefreshing113=false;leaveRetryAt113=AuthorizationNow+10;if(IsVisible)Reflow(ScrollPosition,true);yield break;}
   var directory=owner.Snapshot<SocialTeams82>(SocialPane82.Teams);if(directory==null){leaveRefreshing113=false;leaveRetryAt113=AuthorizationNow+10;if(IsVisible)Reflow(ScrollPosition,true);yield break;}
   if(leaveResult113=="Left"&&directory.myTeamId==previousTeam){
    // A new membership of the same team is possible after the old leave.
    // Do not render either cached incarnation until fresh detail proves it.
    if(!owner.RefreshTeam()){leaveRefreshing113=false;leaveRetryAt113=AuthorizationNow+10;yield break;}while(owner.Busy)yield return null;
    if(closed||owner!=session||token!=loadGeneration){leaveRefreshing113=false;yield break;}
    var current=owner.Snapshot<SocialTeam82>(SocialPane82.TeamInfo);
    if(owner.Status(SocialPane82.TeamInfo).state!=SocialViewState82.Ready||current==null||!current.isMember||current.teamId!=previousTeam||string.IsNullOrEmpty(current.membershipVersion)||(!string.IsNullOrEmpty(leaveVersion113)&&current.membershipVersion==leaveVersion113)){leaveRefreshing113=false;leaveRetryAt113=AuthorizationNow+10;if(IsVisible)Reflow(ScrollPosition,true);yield break;}
   }
   if(leaveResult113=="Rejected"&&directory.myTeamId==previousTeam){
    if(!owner.RefreshTeam()){leaveRefreshing113=false;leaveRetryAt113=AuthorizationNow+10;yield break;}while(owner.Busy)yield return null;
    if(closed||owner!=session||token!=loadGeneration){leaveRefreshing113=false;yield break;}
    if(owner.Status(SocialPane82.TeamInfo).state!=SocialViewState82.Ready){leaveRefreshing113=false;leaveRetryAt113=AuthorizationNow+10;if(IsVisible)Reflow(ScrollPosition,true);yield break;}
    var team=owner.Snapshot<SocialTeam82>(SocialPane82.TeamInfo);if(team==null||!team.isMember||team.teamId!=previousTeam){leaveRefreshing113=false;leaveRetryAt113=AuthorizationNow+10;yield break;}
    leaveRefreshing113=false;leaveNeedMembership113=false;leaveSubmitting113=false;
    // Only an explicit durable rejection followed by a fresh, unchanged
    // membership may display Failed. A new incarnation requires reconfirmation.
    if(team.membershipVersion!=leaveVersion113)leaveFailure113="";
    if(IsVisible)Reflow(ScrollPosition,true);yield break;
   }
   leaveRefreshing113=false;leaveNeedMembership113=false;leaveSubmitting113=false;leaveDismissed113=true;modal="";inspectDetails=accessCreate=false;directoryAfter="";searchQuery="";
   if(string.IsNullOrEmpty(directory.myTeamId)){tab=0;if(leaveResult113=="Left"){if(IsVisible)leaveToastUntil113=AuthorizationNow+2.6;else leaveDeferredToast113=true;}if(IsVisible)owner.Show(SocialPane82.Teams);}else{tab=0;leaveDeferredToast113=false;if(IsVisible)owner.Show(SocialPane82.TeamChat);}
   needsRefresh=true;if(IsVisible){Reflow(1);Pump();}
  }
  void ObserveDeferredLeaveToast113(SocialPageSession82 owner,SocialTeams82 directory){
   if(!leaveDeferredToast113||owner!=session||directory==null||owner.Status(SocialPane82.Teams).state!=SocialViewState82.Ready)return;
   leaveDeferredToast113=false;if(string.IsNullOrEmpty(directory.myTeamId))leaveToastUntil113=AuthorizationNow+2.6;
  }
  void OnApplicationFocus(bool focused){if(focused){leaveAutoChecked113=false;leaveRetryAt113=0;}}
  bool RequestLeave113(string action){
   if(action=="leave"){
    if(modal.Length>0||session==null||session.Busy||refreshing||session.PendingCommand!=null||!EnsureAuthorizedSocial())return true;
    var team=session.Snapshot<SocialTeam82>(SocialPane82.TeamInfo);if(team==null||!team.isMember||team.teamId!=session.SelectedTeamId)return true;
    leaveTeam113=team.teamId;leaveVersion113=team.membershipVersion??"";leaveName113=team.name??"";leaveBadge113=team.badgeId??"drop";leaveCloses113=team.leaveClosesTeam;leaveFailure113=leaveResult113="";leaveDismissed113=false;returnFocus109="online-leave";modal="leave113";leaveClosing113=false;leaveMotionAt113=AuthorizationNow;Reflow(ScrollPosition,true);return true;
   }
   if(modal!="leave113")return false;
   if(leaveClosing113)return true;
   if(action=="cancel"||action=="leave-close113"){leaveClosing113=true;leaveMotionAt113=AuthorizationNow;leaveDismissed113=true;Reflow(ScrollPosition,true);return true;}
   if(action=="leave-refresh113"){if(session!=null&&!session.Busy&&!refreshing&&session.PendingCommand==null){modal="";leaveDismissed113=true;focusAfter109=returnFocus109;needsRefresh=true;Reflow(ScrollPosition,true);Pump();}return true;}
   if(action=="leave-check113"){if(session!=null&&!session.Busy){if(session.PendingCommand?.operation=="team.leave")session.ReconcilePending();else if(leaveNeedMembership113){leaveRetryAt113=0;PumpLeave113();}}return true;}
   if(action=="leave-confirm113"){
    if(session==null||session.Busy||refreshing||session.PendingCommand!=null||LeaveState113()!="confirm"||!EnsureAuthorizedSocial())return true;
    leaveSubmitting113=true;leaveAutoChecked113=false;leaveDismissed113=false;string command=Guid.NewGuid().ToString("N");if(!session.LeaveTeam113(command,leaveTeam113,leaveVersion113))leaveSubmitting113=false;Reflow(ScrollPosition,true);return true;
   }
   return true;
  }
 }
}

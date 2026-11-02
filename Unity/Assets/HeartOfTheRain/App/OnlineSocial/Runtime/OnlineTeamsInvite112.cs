using System;
using System.Linq;
using System.Collections.Generic;
using HeartOfTheRain.App.TeamsInvites;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
namespace HeartOfTheRain.App.OnlineSocial {
 public sealed partial class OnlineTeamsPage82 {
  bool inviteShare112,inviteLoading112,inviteRefresh112;string inviteSearch112="",inviteQuery112="",inviteActiveQuery112="",inviteAfter112="",inviteNotice112="",inviteSelected112="",invitePendingFriend112="";long inviteBefore112,inviteLastSecond112=-1;int inviteEpoch112;double inviteSearchAt112;float inviteKeyboardInset112,inviteScroll112=1;string inviteReceipt112="",inviteFeedbackReceipt112="";double inviteNoticeUntil112;readonly HashSet<string> inviteFeedbackSeen112=new HashSet<string>(StringComparer.Ordinal);TeamsInviteFeedback112 inviteFeedback112,inviteTabFeedback112;
  bool Keyboard112=>modal=="invite"&&!inviteShare112&&TouchScreenKeyboard110;
  void ResetInvite112(){CancelInviteFeedback112();inviteFeedbackReceipt112="";inviteNoticeUntil112=0;inviteEpoch112++;inviteShare112=inviteLoading112=inviteRefresh112=false;inviteSearch112=inviteQuery112=inviteActiveQuery112=inviteAfter112=inviteNotice112=inviteSelected112=invitePendingFriend112="";inviteBefore112=0;inviteLastSecond112=-1;inviteSearchAt112=0;inviteScroll112=1;}
  void ResetInviteFeedbackOwner112(){inviteReceipt112=inviteFeedbackReceipt112="";inviteNoticeUntil112=0;inviteFeedbackSeen112.Clear();CancelInviteFeedback112();}
  void CancelInviteFeedback112(){if(inviteFeedback112){if(Application.isPlaying)Destroy(inviteFeedback112.gameObject);else DestroyImmediate(inviteFeedback112.gameObject);inviteFeedback112=null;}if(inviteTabFeedback112){if(Application.isPlaying)Destroy(inviteTabFeedback112.gameObject);else DestroyImmediate(inviteTabFeedback112.gameObject);inviteTabFeedback112=null;}}
  void ObserveInviteReceipt112(){var receipt=session?.LastInviteReceipt112;if(receipt==null||receipt.receiptId==inviteReceipt112)return;inviteReceipt112=receipt.receiptId;if(!inviteFeedbackSeen112.Add(receipt.receiptId))return;if(IsVisible&&modal=="invite")inviteFeedbackReceipt112=receipt.receiptId;}
  void StartInviteFeedback112(){if(inviteFeedbackReceipt112.Length==0||!IsVisible||modal!="invite"||inviteShare112||session==null||session.Busy||refreshing||inviteLoading112||session.PendingCommand!=null||session.Status(SocialPane82.InviteFriends112).state!=SocialViewState82.Ready)return;
   var receipt=session.LastInviteReceipt112;var row=session.Snapshot<SocialInviteFriends112>(SocialPane82.InviteFriends112)?.friends?.FirstOrDefault(value=>value.friendId==receipt?.friendId&&value.inviteState=="Invited"&&value.inviteId==receipt.inviteId);if(receipt==null||receipt.receiptId!=inviteFeedbackReceipt112||row==null)return;
   RectTransform label;if(!nodes.TryGetValue("invite-friend-"+row.friendId+"-action-label",out label)||!label.GetComponent<Text>())return;inviteFeedbackReceipt112="";if(inviteFeedback112){if(Application.isPlaying)Destroy(inviteFeedback112.gameObject);else DestroyImmediate(inviteFeedback112.gameObject);}var go=new GameObject("Confirmed invite feedback112",typeof(RectTransform));go.transform.SetParent(overlay,false);inviteFeedback112=go.AddComponent<TeamsInviteFeedback112>();inviteFeedback112.BeginConfirmed(receipt.receiptId,label.GetComponent<Text>(),TeamsInvitesText112.T("inviting"),Reduced110);
   inviteNotice112=TeamsInvitesText112.T("sent_notice").Replace("{name}",row.displayName);inviteNoticeUntil112=AuthorizationNow+2.2;RectTransform notice;if(nodes.TryGetValue("invite-notice",out notice)&&notice.GetComponent<Text>())notice.GetComponent<Text>().text=inviteNotice112;
  }
  void StartInviteTabFeedback112(){RectTransform selected;if(!nodes.TryGetValue("invite-tab-selected",out selected)||!selected.GetComponent<Graphic>())return;if(inviteTabFeedback112){if(Application.isPlaying)Destroy(inviteTabFeedback112.gameObject);else DestroyImmediate(inviteTabFeedback112.gameObject);}var go=new GameObject("Invite tab feedback112",typeof(RectTransform));go.transform.SetParent(overlay,false);inviteTabFeedback112=go.AddComponent<TeamsInviteFeedback112>();inviteTabFeedback112.BeginTab(selected.GetComponent<Graphic>(),Reduced110);}
#if UNITY_EDITOR || DEVELOPMENT_BUILD
  public TeamsInviteFeedback112 VerificationInviteFeedback112=>inviteFeedback112;
  public TeamsInviteFeedback112 VerificationInviteTabFeedback112=>inviteTabFeedback112;
  public void VerificationAdvanceInvite112(float seconds){if(inviteFeedback112)inviteFeedback112.Advance(seconds);if(inviteTabFeedback112)inviteTabFeedback112.Advance(seconds);}
#endif
  void ChangeInviteSearch112(string value){inviteSearch112=value??"";inviteSearchAt112=AuthorizationNow+.35;inviteRefresh112=true;}
  void FillInviteView112(OnlineTeamsView82 view){view.inviteHasBack112=inviteAfter112.Length>0;view.inviteIncomingHasBack112=inviteBefore112>0;view.inviteShare112=inviteShare112;view.inviteQuery112=inviteSearch112;view.inviteLoading112=inviteLoading112;view.inviteNotice112=inviteNotice112;view.invitePendingFriend112=invitePendingFriend112;var pending=session?.PendingCommand;if(pending?.operation=="invite.send"){view.inviteNotice112=TeamsInvitesText112.T("unconfirmed");var parts=pending.path.Split('/');if(parts.Length>5)view.invitePendingFriend112=parts[5];}
   var pane=modal=="invitations112"?SocialPane82.InviteReceived112:modal=="invite-detail112"?SocialPane82.InviteDetail112:SocialPane82.InviteFriends112;var state=session?.Status(pane);view.inviteOffline112=state?.state==SocialViewState82.Offline;view.inviteReady112=state?.state==SocialViewState82.Ready;
   view.inviteFriends112=inviteSearch112.Trim()==inviteActiveQuery112?session?.PresentationSnapshot<SocialInviteFriends112>(SocialPane82.InviteFriends112):null;view.inviteReceived112=session?.PresentationSnapshot<SocialInvitations112>(SocialPane82.InviteReceived112);var selected=session?.PresentationSnapshot<SocialInvitationDetail112>(SocialPane82.InviteDetail112)?.invitation;view.inviteDetail112=selected?.inviteId==inviteSelected112?selected:null;
  }
  void PumpInvite112(){
   if(modal!="invite"&&modal!="invitations112"&&modal!="invite-detail112")return;
   if(inviteNoticeUntil112>0&&AuthorizationNow>=inviteNoticeUntil112){inviteNoticeUntil112=0;inviteNotice112="";RectTransform notice;if(nodes.TryGetValue("invite-notice",out notice)&&notice.GetComponent<Text>())notice.GetComponent<Text>().text="";}
   if(modal=="invite-detail112"&&session!=null){long now=session.LifeServerNow110;var detail=now>0&&now!=inviteLastSecond112?session.PresentationSnapshot<SocialInvitationDetail112>(SocialPane82.InviteDetail112)?.invitation:null;
    if(detail!=null&&detail.inviteId==inviteSelected112&&session.Status(SocialPane82.InviteDetail112).state==SocialViewState82.Ready){inviteLastSecond112=now;RectTransform label;if(nodes.TryGetValue("invite-detail-status",out label)&&label.GetComponent<Text>())label.GetComponent<Text>().text=TeamsInvitesLayout112.DetailStatus(detail,now);if(now>=detail.expiresAtUtc&&detail.state!="Expired"&&detail.state!="Unavailable"){inviteRefresh112=true;inviteSearchAt112=0;}}
   }
   float inset=Keyboard112?KeyboardInset110:0;if(Math.Abs(inset-inviteKeyboardInset112)>.1f){inviteKeyboardInset112=inset;Reflow(ScrollPosition,true);}
   if(session==null||session.Busy||refreshing||session.PendingCommand!=null||inviteLoading112||!inviteRefresh112||AuthorizationNow<inviteSearchAt112)return;
   if(modal=="invite"&&inviteSearch112.Trim()!=inviteQuery112){inviteQuery112=inviteSearch112.Trim();inviteAfter112="";}
   inviteRefresh112=false;inviteLoading112=true;bool started;
   if(modal=="invite"){inviteActiveQuery112=inviteQuery112;started=session.RefreshInviteFriends112(inviteAfter112,inviteQuery112);}
   else if(modal=="invitations112")started=session.RefreshReceivedInvites112(inviteBefore112);
   else started=session.RefreshInviteDetail112(inviteSelected112);
   if(!started)inviteLoading112=false;else Dispatch(InviteFinish112(session,modal,loadGeneration,inviteEpoch112));
  }
  System.Collections.IEnumerator InviteFinish112(SocialPageSession82 owner,string destination,int token,int epoch){while(owner.Busy)yield return null;if(owner!=session||closed||token!=loadGeneration)yield break;if(epoch!=inviteEpoch112||destination!=modal)yield break;inviteLoading112=false;if(destination=="invite"&&inviteActiveQuery112!=inviteSearch112.Trim()){inviteRefresh112=true;inviteSearchAt112=AuthorizationNow+.35;owner.ClearInviteFriends112();}if(IsVisible){Reflow(ScrollPosition,true);StartInviteFeedback112();}}
  void QueueInviteRead112(){inviteRefresh112=true;inviteSearchAt112=0;PumpInvite112();}
  bool RequestInvite112(string action){
   if(action=="invite"){
    if(modal.Length>0||session==null||session.Busy||refreshing||session.PendingCommand!=null||session.Snapshot<SocialTeam82>(SocialPane82.TeamInfo)?.isMember!=true||!EnsureAuthorizedSocial())return true;
    returnFocus109="online-invite";ResetInvite112();session.ClearInviteFriends112();modal="invite";Reflow(ScrollPosition,true);QueueInviteRead112();return true;
   }
   if(action=="invite-received"){
    if(modal.Length>0||session==null||session.Busy||refreshing||session.PendingCommand!=null||!EnsureAuthorizedSocial())return true;
    ResetInvite112();session.ClearInviteReceived112();modal="invitations112";returnFocus109="invite-received-entry";Reflow(ScrollPosition,true);QueueInviteRead112();return true;
   }
   if(modal!="invite"&&modal!="invitations112"&&modal!="invite-detail112")return false;
   if(action=="invite-close"||action=="cancel") {CancelInviteFeedback112();inviteFeedbackReceipt112="";inviteNoticeUntil112=0;modal="";inviteEpoch112++;inviteRefresh112=inviteLoading112=false;focusAfter109=returnFocus109;Reflow(ScrollPosition,true);return true;}
   if(action=="invite-friends"||action=="invite-share"){bool next=action=="invite-share",changed=next!=inviteShare112;inviteShare112=next;inviteNotice112="";Reflow(ScrollPosition,true);if(changed)StartInviteTabFeedback112();if(!inviteShare112)StartInviteFeedback112();return true;}
   if(action=="invite-copy") {var data=session?.Snapshot<SocialInviteFriends112>(SocialPane82.InviteFriends112);if(data==null||string.IsNullOrEmpty(data.publicTeamCode))return true;try{GUIUtility.systemCopyBuffer=data.publicTeamCode;inviteNotice112=TeamsInvitesText112.T(GUIUtility.systemCopyBuffer==data.publicTeamCode?"copied":"copy_failed");}catch(Exception){inviteNotice112=TeamsInvitesText112.T("copy_failed");}Reflow(ScrollPosition,true);return true;}
   if(action=="invite-check"||action=="invite-retry"){if(session==null||session.Busy||session.PendingCommand==null)return true;writing=true;bool sent=action=="invite-check"?session.ReconcilePending():session.ResumePending();if(!sent)writing=false;inviteNotice112=TeamsInvitesText112.T("unconfirmed");inviteRefresh112=true;return true;}
   if(action=="invite-refresh"){if(session?.Busy==false&&session.PendingCommand==null)QueueInviteRead112();return true;}
   if(action=="invite-first"){if(session?.Busy==false&&session.PendingCommand==null){inviteAfter112="";QueueInviteRead112();}return true;}
   if(action=="invite-incoming-first"){if(session?.Busy==false&&session.PendingCommand==null){inviteBefore112=0;QueueInviteRead112();}return true;}
   if(action=="invite-more"){var data=session?.Snapshot<SocialInviteFriends112>(SocialPane82.InviteFriends112);if(data?.hasMore==true&&!session.Busy&&session.PendingCommand==null){inviteAfter112=data.nextCursor;QueueInviteRead112();}return true;}
   if(action=="invite-incoming-more"){var data=session?.Snapshot<SocialInvitations112>(SocialPane82.InviteReceived112);if(data?.hasMore==true&&!session.Busy){inviteBefore112=data.nextCursor;QueueInviteRead112();}return true;}
   if(action.StartsWith("invite-friend:",StringComparison.Ordinal)){
    if(session==null||session.Busy||refreshing||session.PendingCommand!=null||!EnsureAuthorizedSocial())return true;string friend=action.Substring(14);var data=session.Snapshot<SocialInviteFriends112>(SocialPane82.InviteFriends112);var row=data?.friends?.FirstOrDefault(v=>v.friendId==friend);if(row==null||row.inviteState!="Ready"||!data.canInvite||inviteLoading112||session.Status(SocialPane82.InviteFriends112).state!=SocialViewState82.Ready)return true;
    invitePendingFriend112=friend;inviteNotice112="";Write(()=>session.SendInvite112(Guid.NewGuid().ToString("N"),friend));inviteRefresh112=true;return true;
   }
   if(action.StartsWith("invite-open:",StringComparison.Ordinal)){if(session==null||session.Busy)return true;string id=action.Substring(12);if(!(session.Snapshot<SocialInvitations112>(SocialPane82.InviteReceived112)?.invitations??new SocialInvitation112[0]).Any(v=>v.inviteId==id))return true;inviteSelected112=id;modal="invite-detail112";Reflow(ScrollPosition,true);QueueInviteRead112();return true;}
   if(action=="invite-view"){
    if(session==null||session.Busy||refreshing||session.PendingCommand!=null||inviteLoading112)return true;var item=session.Snapshot<SocialInvitationDetail112>(SocialPane82.InviteDetail112)?.invitation;if(item==null||item.inviteId!=inviteSelected112||item.state=="Unavailable"||item.state=="Expired")return true;
    inviteLoading112=true;Dispatch(OpenInviteTeam112(session,inviteSelected112,loadGeneration,inviteEpoch112));return true;
   }
   return action.StartsWith("invite-",StringComparison.Ordinal);
  }
  System.Collections.IEnumerator OpenInviteTeam112(SocialPageSession82 owner,string id,int token,int epoch){
   bool started=owner.RefreshInviteDetail112(id);if(!started){inviteLoading112=false;if(IsVisible)Reflow(ScrollPosition,true);yield break;}while(owner.Busy)yield return null;
   if(closed||!IsVisible||owner!=session||token!=loadGeneration||epoch!=inviteEpoch112||modal!="invite-detail112")yield break;
   inviteLoading112=false;var item=owner.Snapshot<SocialInvitationDetail112>(SocialPane82.InviteDetail112)?.invitation;
   if(owner.Status(SocialPane82.InviteDetail112).state!=SocialViewState82.Ready||item==null||item.inviteId!=id||item.state=="Expired"||item.state=="Unavailable"){Reflow(ScrollPosition,true);yield break;}
   modal="";inviteEpoch112++;inviteRefresh112=false;
   if(item.state=="AlreadyMember"){tab=0;inspectDetails=accessCreate=false;owner.Show(SocialPane82.TeamChat);needsRefresh=true;Reflow(0);Pump();yield break;}
   if(owner.SelectTeam(item.teamId)){inspectDetails=true;accessCreate=false;tab=1;needsRefresh=false;Reflow(1);}
  }

 }
}

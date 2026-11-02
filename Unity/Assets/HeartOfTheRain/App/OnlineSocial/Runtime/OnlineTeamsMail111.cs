using System;
using System.Collections;
using System.Linq;
using HeartOfTheRain.App.TeamsMail;
using System.Collections.Generic;
using UnityEngine;
namespace HeartOfTheRain.App.OnlineSocial {
 public sealed partial class OnlineTeamsPage82 {
  bool mailRefreshing111,ownedMailOpen111;long ownedMailAfter111,mailBefore111;double mailPollAt111;float mailReturnScroll111=1;string mailSelected111="",mailReceipt111="",mailError111="",mailFeedback111="";readonly HashSet<string> mailFeedbackSeen111=new HashSet<string>(StringComparer.Ordinal);TeamsMailFeedback111 mailAnimation111;
  void ResetMail111(){CancelMailFeedback111();mailRefreshing111=ownedMailOpen111=false;ownedMailAfter111=mailBefore111=0;mailPollAt111=0;mailSelected111=mailReceipt111=mailError111=mailFeedback111="";mailFeedbackSeen111.Clear();}
  void ObserveMailReceipt111(){var receipt=session?.LastMailReceipt111;if(receipt==null||receipt.receiptId==mailReceipt111)return;mailReceipt111=receipt.receiptId;mailError111="";if(receipt.operation=="mail.claim"){lifeWalletRefresh110=true;if(receipt.state=="Claimed"&&IsVisible&&(ownedMailOpen111||modal=="mail-detail111"&&receipt.messageId==mailSelected111)&&mailFeedbackSeen111.Add(receipt.receiptId))mailFeedback111=receipt.receiptId;}mailPollAt111=0;}
  void CancelMailFeedback111(){if(mailAnimation111){if(Application.isPlaying)Destroy(mailAnimation111.gameObject);else DestroyImmediate(mailAnimation111.gameObject);mailAnimation111=null;}mailFeedback111="";}
  void StartMailFeedback111(){if(mailFeedback111.Length==0||!IsVisible||lifeWalletRefresh110||!gateway||gateway.Busy)return;var receipt=session?.LastMailReceipt111;if(receipt==null||receipt.receiptId!=mailFeedback111)return;UnityEngine.RectTransform target=MailFeedbackTarget111(receipt.messageId,ownedMailOpen111);mailFeedback111="";if(!target)return;CancelMailFeedback111();var go=new GameObject("Confirmed mail reward feedback111",typeof(RectTransform));go.transform.SetParent(safe,false);var rect=(RectTransform)go.transform;rect.anchorMin=rect.anchorMax=rect.pivot=new Vector2(.5f,.5f);rect.position=target.TransformPoint(target.rect.center);rect.sizeDelta=Vector2.one*80;mailAnimation111=go.AddComponent<TeamsMailFeedback111>();mailAnimation111.Begin(receipt.receiptId,assets.Find("TM_Letter_Open"),assets.Find("TA_Icon_Check"),assets.Find("TA_Stat_star"),Reduced110);}
  UnityEngine.RectTransform MailFeedbackTarget111(string id,bool owned){UnityEngine.RectTransform target;if(owned){if(nodes.TryGetValue("mail-owned-"+id+"-action",out target)&&target)return target;return nodes.TryGetValue("mail-owned-feedback-anchor",out target)?target:null;}return modal=="mail-detail111"&&id==mailSelected111&&nodes.TryGetValue("mail-detail-action",out target)?target:null;}
#if UNITY_EDITOR || DEVELOPMENT_BUILD
  public UnityEngine.RectTransform VerificationMailFeedbackTarget111(string id,bool owned)=>MailFeedbackTarget111(id,owned);
#endif
  void FillMailView111(OnlineTeamsView82 value){
   value.ownedMailOpen111=ownedMailOpen111;value.ownedMailReady111=session?.Status(SocialPane82.OwnedMail111).state==SocialViewState82.Ready;value.ownedMailHasBack111=ownedMailAfter111>0;value.ownedMail111=ownedMailOpen111||mail110||value.team?.isMember!=true?session?.PresentationSnapshot<SocialOwnedMail111>(SocialPane82.OwnedMail111):null;value.mailHasBack111=mailBefore111>0;value.mailList111=value.tab==0||mail110||modal=="mail-detail111"?session?.PresentationSnapshot<SocialMailList111>(SocialPane82.TeamMail111):null;var detail=modal=="mail-detail111"?session?.PresentationSnapshot<SocialMailDetail111>(SocialPane82.TeamMailDetail111):null;value.mailDetail111=detail?.message?.messageId==mailSelected111?detail.message:value.mailList111?.messages?.FirstOrDefault(m=>m.messageId==mailSelected111);
   var status=session?.Status(SocialPane82.TeamMail111);value.mailOffline111=status?.state==SocialViewState82.Offline;value.mailReady111=status?.state==SocialViewState82.Ready;value.mailStatus111=mailError111;
   var pending=session?.PendingCommand;if(pending!=null&&pending.operation.StartsWith("mail.",StringComparison.Ordinal))value.mailStatus111=session.Busy?TeamsMailText111.T("claim_pending_note"):TeamsMailText111.T(pending.operation=="mail.read"?"load_error":"claim_error");
   if(value.mailStatus111.Length==0&&value.mailOffline111)value.mailStatus111=TeamsMailText111.T("offline_note");
   value.busy|=mailRefreshing111;
  }
  void PumpMail111(){if(!mail110||session==null||session.Busy||refreshing||mailRefreshing111||session.PendingCommand!=null||AuthorizationNow<mailPollAt111||!Chat110)return;mailPollAt111=AuthorizationNow+10;Dispatch(RefreshMail111(session,loadGeneration));}
  IEnumerator RefreshMail111(SocialPageSession82 owner,int token){
   mailRefreshing111=true;try{
    if(owner.RefreshTeamMail111(mailBefore111))while(owner.Busy)yield return null;
    if(closed||!IsVisible||session!=owner||token!=loadGeneration||!mail110)yield break;
    var status=owner.Status(SocialPane82.TeamMail111);mailError111=status.state==SocialViewState82.Ready?"":TeamsMailText111.T(status.state==SocialViewState82.Offline?"offline_note":"load_error");
    if(status.state!=SocialViewState82.Ready||mailSelected111.Length==0)yield break;
    string selected=mailSelected111;if(owner.RefreshMailDetail111(selected))while(owner.Busy)yield return null;
    if(closed||!IsVisible||session!=owner||token!=loadGeneration||!mail110||selected!=mailSelected111)yield break;
    var detail=owner.Snapshot<SocialMailDetail111>(SocialPane82.TeamMailDetail111);if(owner.Status(SocialPane82.TeamMailDetail111).state!=SocialViewState82.Ready){mailError111=TeamsMailText111.T("load_error");yield break;}
    if(detail?.message?.messageId==selected&&detail.message.readAtUtc==0&&owner.PendingCommand==null){
     if(owner.ReadMail111(Guid.NewGuid().ToString("N"),selected))while(owner.Busy)yield return null;
     if(closed||!IsVisible||session!=owner||token!=loadGeneration||!mail110||selected!=mailSelected111)yield break;
     if(owner.PendingCommand!=null){mailError111=TeamsMailText111.T("claim_error");yield break;}
     if(owner.Status(SocialPane82.TeamMailDetail111).state!=SocialViewState82.Ready){mailError111=TeamsMailText111.T("load_error");yield break;}
     if(owner.RefreshTeamMail111(mailBefore111))while(owner.Busy)yield return null;
     if(closed||!IsVisible||session!=owner||token!=loadGeneration||!mail110||selected!=mailSelected111)yield break;
     if(owner.RefreshMailDetail111(selected))while(owner.Busy)yield return null;
    }
   }finally{if(session==owner&&token==loadGeneration){mailRefreshing111=false;mailPollAt111=AuthorizationNow+30;}if(!closed&&IsVisible&&session==owner&&token==loadGeneration)Reflow(ScrollPosition,true);}
  }
  void PumpOwnedMail111(){if(!ownedMailOpen111||session==null||session.Busy||refreshing||mailRefreshing111||session.PendingCommand!=null||AuthorizationNow<mailPollAt111)return;mailPollAt111=AuthorizationNow+10;Dispatch(RefreshOwnedMail111(session,loadGeneration));}
  IEnumerator RefreshOwnedMail111(SocialPageSession82 owner,int token){mailRefreshing111=true;try{if(owner.RefreshOwnedMail111(ownedMailAfter111))while(owner.Busy)yield return null;if(closed||!IsVisible||session!=owner||token!=loadGeneration||!ownedMailOpen111)yield break;var status=owner.Status(SocialPane82.OwnedMail111);mailError111=status.state==SocialViewState82.Ready?"":TeamsMailText111.T(status.state==SocialViewState82.Offline?"offline_note":"load_error");}finally{if(session==owner&&token==loadGeneration){mailRefreshing111=false;mailPollAt111=AuthorizationNow+30;}if(!closed&&IsVisible&&session==owner&&token==loadGeneration)Reflow(ScrollPosition,true);}}
  bool RequestMail111(string action){
   if(action=="mail-owned"){if(session==null||modal.Length>0)return true;ownedMailOpen111=true;mail110=false;ownedMailAfter111=0;mailPollAt111=0;Reflow(1);PumpOwnedMail111();return true;}
   if(action=="mail-owned-close"){ownedMailOpen111=false;ownedMailAfter111=0;needsRefresh=session!=null;Reflow(1);Pump();return true;}
   if(action=="mail-owned-more"){var data=session?.Snapshot<SocialOwnedMail111>(SocialPane82.OwnedMail111);if(data?.hasMore==true&&session.Busy==false&&session.PendingCommand==null){ownedMailAfter111=data.nextCursor;mailPollAt111=0;PumpOwnedMail111();}return true;}
   if(action=="mail-owned-latest"){if(session?.Busy==false&&session.PendingCommand==null){ownedMailAfter111=0;mailPollAt111=0;PumpOwnedMail111();}return true;}
   if(action.StartsWith("mail-owned-claim:",StringComparison.Ordinal)){string id=action.Substring(17);var data=session?.Snapshot<SocialOwnedMail111>(SocialPane82.OwnedMail111);var item=data?.rewards?.FirstOrDefault(value=>value.messageId==id);if(!ownedMailOpen111||item==null||!item.canClaim||session.Busy||refreshing||mailRefreshing111||session.PendingCommand!=null||session.Status(SocialPane82.OwnedMail111).state!=SocialViewState82.Ready||!EnsureAuthorizedSocial())return true;Write(()=>session.ClaimOwnedMail111(Guid.NewGuid().ToString("N"),id));return true;}
   if(action=="tab-mail"){if(modal.Length>0||!Chat110)return true;mail110=true;mailSelected111="";mailBefore111=0;mailPollAt111=0;Reflow(1);PumpMail111();return true;}
   if(action=="tab-chat"&&mail110){mail110=false;mailSelected111="";mailBefore111=0;mailError111="";return false;}
   if(!mail110)return false;
   if(action=="mail-close"||action=="cancel"&&modal=="mail-detail111"){modal="";mailSelected111="";mailPollAt111=0;focusAfter109=returnFocus109;Reflow(mailReturnScroll111);PumpMail111();return true;}
   if(action=="mail-refresh"){if(session?.Busy==false&&!refreshing&&session.PendingCommand==null){mailPollAt111=0;PumpMail111();}return true;}
   if(action=="mail-latest"){if(session?.Busy==false&&session.PendingCommand==null){mailBefore111=0;mailPollAt111=0;PumpMail111();}return true;}
   if(action=="mail-older"){var list=session?.Snapshot<SocialMailList111>(SocialPane82.TeamMail111);if(list?.hasOlder==true&&session.Busy==false&&session.PendingCommand==null){mailBefore111=list.olderCursor;mailPollAt111=0;PumpMail111();}return true;}
   if(action.StartsWith("mail-open:",StringComparison.Ordinal)){
    if(modal.Length>0)return true;string id=action.Substring(10);var list=session?.Snapshot<SocialMailList111>(SocialPane82.TeamMail111);if(list?.messages?.Any(m=>m.messageId==id)!=true)return true;
    mailReturnScroll111=ScrollPosition;returnFocus109="mail-row-"+id;mailSelected111=id;modal="mail-detail111";mailPollAt111=0;Reflow(mailReturnScroll111,true);PumpMail111();return true;
   }
   if(action=="mail-claim"){
    var view=View();var mail=view.mailDetail111;if(modal!="mail-detail111"||mail==null||mail.messageId!=mailSelected111||!mail.canClaim||!view.mailReady111||view.mailOffline111||session==null||session.Busy||refreshing||mailRefreshing111||session.PendingCommand!=null||!EnsureAuthorizedSocial())return true;
    mailError111="";Write(()=>session.ClaimMail111(Guid.NewGuid().ToString("N"),mailSelected111));return true;
   }
   if(action=="mail-check"||action=="mail-retry"){if(session==null||session.Busy||session.PendingCommand==null)return true;writing=true;if(!(action=="mail-check"?session.ReconcilePending():session.ResumePending()))writing=false;return true;}
   return false;
  }
 }
}

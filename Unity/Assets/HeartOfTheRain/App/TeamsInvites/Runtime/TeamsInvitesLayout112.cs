using System;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.TeamsAccess;
using UnityEngine;
namespace HeartOfTheRain.App.TeamsInvites {
 public static class TeamsInvitesLayout112 {
  static string T(string k)=>TeamsInvitesText112.T(k);
  static HomeElement Add(HomeFrame f,string id,string kind,float x,float y,float w,float h,string parent=""){var e=new HomeElement{id=id,kind=kind,x=x,y=y,width=w,height=h,parent=parent};f.elements.Add(e);return e;}
  static void Art(HomeFrame f,string id,string asset,float x,float y,float w,float h,bool slice=true,string parent=""){var e=Add(f,id,"sprite",x,y,w,h,parent);e.asset=asset;e.sliced=slice;e.preserveAspect=!slice;e.color="#FFFFFF";}
  static void Text(HomeFrame f,string id,string value,float x,float y,float w,float h,int size=14,string color="#21465E",string kind="text",string parent=""){var e=Add(f,id,kind,x,y,w,h,parent);e.text=value??"";e.fontSize=size;e.color=color;}
  static void Button(HomeFrame f,string id,string action,string caption,float x,float y,float w,float h,bool enabled=true,string tone="Blue",string parent=""){Art(f,id+"-art",enabled?"TA_Button_"+tone:"TA_Button_Disabled",x,y,w,h,true,parent);Text(f,id+"-label",caption,x+7,y+3,w-14,h-6,14,enabled?"#FFFFFF":"#617F90","text",parent);var e=Add(f,id,"group",x,y,w,h,parent);e.action=enabled?action:"disabled";e.label=caption;}
  public static string DetailStatus(SocialInvitation112 detail,long now){
   if(detail==null)return "";if(detail.state=="Expired")return T("invite_expired");if(detail.state=="Unavailable")return T("team_unavailable");
   string status=detail.state=="TeamFull"?T("team_full"):detail.state=="AlreadyMember"?T("you_are_member"):"";
   if(now>0){string expiry=T("expires_in").Replace("{time}",HeartOfTheRain.App.TeamsSocial.TeamsSocialLayout110.Countdown(Math.Max(0,detail.expiresAtUtc-now)));status=status.Length>0?status+"\n"+expiry:expiry;}
   return status;
  }
  public static void Decorate(OnlineTeamsFrame82 frame,OnlineTeamsView82 view){
   if(view.connected&&!view.detailsOpen&&!view.giftsOpen110&&!view.ownedMailOpen111&&view.tab!=2&&!(view.team?.isMember==true&&view.tab==0)){
    foreach(var e in frame.content.elements)if(string.IsNullOrEmpty(e.parent))e.y+=60;float entryWidth=Math.Min(320,frame.width-40),entryX=(frame.width-entryWidth)/2;Button(frame.content,"invite-received-entry","invite-received",T("invite_received"),entryX,4,entryWidth,48,!view.busy&&!view.pending);frame.content.height+=60;
   }
   if(view.modal!="invite"&&view.modal!="invitations112"&&view.modal!="invite-detail112")return;
   var f=new HomeFrame{width=frame.width,height=frame.height};frame.overlay=f;float w=frame.width,h=frame.height,cw=Math.Min(460,w*.85f);
   bool compactFriends=view.modal=="invite"&&!view.inviteShare112;
   // The 360x640 Android safe area is shorter than the Editor Game view.
   // Reserve enough list height for three 50-unit rows before the fixed footer.
   float compactHeight=Math.Max(435,h*.68f);
   float mh=compactFriends?Math.Min(455,Math.Min(h-32,compactHeight)):Math.Min(610,h-20),x=(w-cw)/2;
   float topOffset=compactFriends?(h<630?2:12):0,top=(h-mh)/2+topOffset;
   var shade=Add(f,"invite-shade","color",0,0,w,h);shade.color="#000000B8";
   Art(f,"invite-frame","TA_Panel_Blue",x,top,cw,mh);
   Art(f,"invite-crest","TA_Badge_banners",x+cw/2-32,top-39,64,64,false);
   float closeX=Math.Min(x+cw-32,w-48);
   Art(f,"invite-close-art","TA_Close_Disc",closeX,top-9,48,48,false);
   Art(f,"invite-close-icon","TA_Icon_Close",closeX+12,top+3,24,24,false);
   var close=Add(f,"invite-close","group",Math.Min(x+cw-48,w-80),top-9,80,48);close.action="invite-close";close.label=T("close");
   if(view.modal=="invite"){
    bool compact=!view.inviteShare112;Text(f,"invite-title",T("invite_title"),x+16,top+(compact?47:65),cw-32,compact?32:40,20,"#FFFFFF");bool subtitle=compact||mh>=590;if(subtitle)Text(f,"invite-subtitle",T("invite_subtitle"),x+16,top+(compact?79:103),cw-32,compact?19:24,13,"#BDDFFF");float tabs=top+(compact?100:subtitle?130:109);Art(f,"invite-tabs","TA_Tab_Track",x+12,tabs,cw-24,48);Art(f,"invite-tab-selected","TA_Tab_Selected",view.inviteShare112?x+cw/2:x+12,tabs,(cw-24)/2,48);Text(f,"invite-friends-tab-label",T("friends_tab"),x+18,tabs+4,(cw-24)/2-12,40,15,view.inviteShare112?"#BDDFFF":"#FFFFFF");Text(f,"invite-share-tab-label",T("share_tab"),x+cw/2+6,tabs+4,(cw-24)/2-12,40,15,view.inviteShare112?"#FFFFFF":"#BDDFFF");var friendsTab=Add(f,"invite-friends-tab","group",x+12,tabs,(cw-24)/2,48);friendsTab.action="invite-friends";friendsTab.label=T("friends_tab");var shareTab=Add(f,"invite-share-tab","group",x+cw/2,tabs,(cw-24)/2,48);shareTab.action="invite-share";shareTab.label=T("share_tab");
    if(view.inviteShare112){var data=view.inviteFriends112;Art(f,"invite-share-card","TA_Panel_Cream",x+12,tabs+58,cw-24,mh-180-(subtitle?21:0));Text(f,"invite-team-name",data?.teamName??"",x+24,tabs+70,cw-48,34,18,"#073354","chatname110");Art(f,"invite-team-badge",TeamsAccessBadges109.Asset(data?.badgeId),x+cw/2-35,tabs+108,70,70,false);Text(f,"invite-team-count",data==null?"":data.memberCount+" / "+data.capacity,x+24,tabs+182,cw-48,28,14);Text(f,"invite-code-title",T("team_code"),x+24,tabs+216,cw-48,28,14);Text(f,"invite-code",data?.publicTeamCode??T("code_unavailable"),x+24,tabs+246,cw-48,36,20,"#073354");float bottom=top+mh-128;Button(f,"invite-copy","invite-copy",T("copy_code"),x+24,bottom,cw-48,48,data!=null&&!string.IsNullOrEmpty(data.publicTeamCode));Art(f,"invite-copy-icon","TI_Icon_Copy",x+35,bottom+12,24,24,false);Button(f,"invite-share-disabled","disabled",T("share_action"),x+24,bottom+56,cw-48,48,false);Art(f,"invite-share-icon","TI_Icon_Share",x+35,bottom+68,24,24,false);Text(f,"invite-share-notice",view.inviteNotice112.Length>0?view.inviteNotice112:T("share_not_configured"),x+24,bottom-34,cw-48,30,12,"#21465E");return;}
    float sy=tabs+54;Art(f,"invite-search-art","TA_Field",x+12,sy,cw-24,48);var input=Add(f,"invite-search-input","input",x+24,sy+6,cw-48,36);input.label=T("search_friend");input.fontSize=14;input.color="#073354";float bodyY=sy+52,bodyH=Math.Max(40,top+mh-70-bodyY);var body=Add(f,"invite-list","invitebody112",x+12,bodyY,cw-24,bodyH);body.label="invite-list-content";var content=Add(f,"invite-list-content","group",0,0,cw-24,bodyH,"invite-list");float y=5;var rows=view.inviteFriends112;if(rows!=null&&view.inviteOffline112){Text(f,"invite-offline-notice",T("offline_invite"),8,y,cw-40,44,14,"#FFFFFF","text",content.id);y+=48;Button(f,"invite-offline-retry","invite-refresh",T("retry"),4,y,cw-40,48,!view.busy&&!view.pending,"Blue",content.id);y+=58;}if(rows!=null&&!rows.canInvite){Text(f,"invite-disabled-reason",T(rows.memberCount>=rows.capacity?"team_full":"invite_restricted"),8,y,cw-40,48,14,"#FFFFFF","text",content.id);y+=54;}if(view.inviteHasBack112){Button(f,"invite-first","invite-first",T("first"),4,y,cw-40,48,!view.busy&&!view.pending,"Blue",content.id);y+=58;}
    if(view.inviteLoading112&&rows==null){Text(f,"invite-loading",T("friends_loading"),8,y,cw-40,50,14,"#E7F6FC","text",content.id);y+=55;}
    else if(rows==null){Text(f,"invite-error",view.inviteOffline112?T("offline_invite"):T("friends_error"),8,y,cw-40,55,14,"#E7F6FC","text",content.id);y+=60;Button(f,"invite-refresh","invite-refresh",T("retry"),4,y,cw-40,48,!view.busy&&!view.pending,"Blue",content.id);y+=58;}
    else if(rows.friends.Length==0){Text(f,"invite-empty",T(view.inviteQuery112.Length==0?"no_friends":"no_results"),8,y,cw-40,55,16,"#FFFFFF","text",content.id);y+=60;}
    else foreach(var row in rows.friends){
     string id="invite-friend-"+row.friendId;float rw=cw-40;Art(f,id+"-card","TA_Panel_Cream",4,y,rw,50,true,content.id);Art(f,id+"-avatar","TA_Icon_People",13,y+7,36,36,false,content.id);f.elements[f.elements.Count-1].color="#05426B";Text(f,id+"-name",row.displayName,55,y+3,rw-174,22,14,"#073354","chatname110",content.id);Text(f,id+"-level",T("level_value").Replace("{level}",Math.Max(1,row.completedLevels+1).ToString()),55,y+27,rw-174,18,11,"#527487","lefttext",content.id);
     if(row.inviteState=="Member"){
      Art(f,id+"-member-check","TA_Icon_Check",rw-64,y+5,20,20,false,content.id);f.elements[f.elements.Count-1].color="#168744";Text(f,id+"-member-label",T("in_team"),rw-112,y+23,102,21,13,"#315366","text",content.id);
     }else{
      bool ready=row.inviteState=="Ready"&&rows.canInvite&&!view.busy&&!view.pending&&!view.inviteOffline112;string caption=row.inviteState=="Invited"?T("invited"):view.invitePendingFriend112==row.friendId?T("inviting"):T("invite_action");Button(f,id+"-action","invite-friend:"+row.friendId,caption,rw-110,y+1,110,48,ready,"Blue",content.id);f.elements[f.elements.Count-1].label=caption+": "+row.displayName;
     }
     y+=52;
    }
    if(rows?.hasMore==true){Button(f,"invite-more","invite-more",T("more"),4,y,cw-40,48,!view.busy&&!view.pending,"Blue",content.id);y+=58;}content.height=Math.Max(bodyH,y+8);
    if(view.pending){Text(f,"invite-pending-notice",view.inviteNotice112,x+14,top+mh-88,cw-28,27,11,"#FFFFFF");float p=(cw-36)/2;Button(f,"invite-check","invite-check",HeartOfTheRain.App.OnlineSocial.OnlineTeamsText82.T("Check"),x+12,top+mh-57,p,48,!view.busy);Button(f,"invite-retry","invite-retry",T("retry"),x+24+p,top+mh-57,p,48,!view.busy);}else if(!string.IsNullOrEmpty(view.inviteNotice112))Text(f,"invite-notice",view.inviteNotice112,x+14,top+mh-60,cw-28,46,12,"#FFFFFF");else Button(f,"invite-footer-close","invite-close",T("close"),x+24,top+mh-57,cw-48,48,true);return;
   }
   Text(f,"invite-title",T("invite_received"),x+15,top+65,cw-30,38,20,"#FFFFFF");
   if(view.modal=="invitations112"){
    float by=top+110,bh=Math.Max(40,mh-180);var body=Add(f,"invite-incoming-list","invitebody112",x+12,by,cw-24,bh);body.label="invite-incoming-content";var content=Add(f,"invite-incoming-content","group",0,0,cw-24,bh,"invite-incoming-list");float y=4;var data=view.inviteReceived112;if(view.inviteIncomingHasBack112){Button(f,"invite-incoming-first","invite-incoming-first",T("first"),4,y,cw-40,48,!view.busy,"Blue",content.id);y+=58;}
    if(data==null){Text(f,"invite-incoming-loading",view.inviteLoading112?T("friends_loading"):T("incoming_error"),8,y,cw-40,52,14,"#FFFFFF","text",content.id);y+=60;if(!view.inviteLoading112){Button(f,"invite-incoming-retry","invite-refresh",T("retry"),4,y,cw-40,48,!view.busy,"Blue",content.id);y+=58;}}
    else if(data.invitations.Length==0){Text(f,"invite-incoming-empty",T("no_invites"),8,y,cw-40,52,14,"#FFFFFF","text",content.id);y+=60;}
    else foreach(var item in data.invitations){string id="invite-incoming-"+item.inviteId;Art(f,id+"-card","TA_Panel_Cream",4,y,cw-40,76,true,content.id);Text(f,id+"-name",item.state=="Unavailable"?T("team_unavailable"):item.teamName,12,y+6,cw-170,32,15,"#073354","chatname110",content.id);Button(f,id+"-open","invite-open:"+item.inviteId,T("view_team"),cw-156,y+13,118,48,!view.busy,"Blue",content.id);y+=86;}
    if(data?.hasMore==true){Button(f,"invite-incoming-more","invite-incoming-more",T("more"),4,y,cw-40,48,!view.busy,"Blue",content.id);y+=58;}content.height=Math.Max(bh,y+8);return;
   }
   var detail=view.inviteDetail112;Art(f,"invite-detail-card","TA_Panel_Cream",x+12,top+112,cw-24,mh-190);Text(f,"invite-detail-name",detail==null?T("friends_loading"):detail.state=="Unavailable"?T("team_unavailable"):detail.teamName,x+26,top+126,cw-52,38,18,"#073354");if(detail!=null&&detail.state!="Unavailable"){Art(f,"invite-detail-badge",TeamsAccessBadges109.Asset(detail.badgeId),x+cw/2-34,top+174,68,68,false);Text(f,"invite-detail-sender",T("sender_invites").Replace("{name}",detail.senderName),x+30,top+252,cw-60,55,14,"#527487");Text(f,"invite-detail-count",detail.memberCount+" / "+detail.capacity,x+30,top+312,cw-60,30,14);}
   string status=!view.inviteReady112&&!view.inviteLoading112?T("detail_unavailable"):DetailStatus(detail,view.now110);Text(f,"invite-detail-status",status,x+24,top+mh-132,cw-48,34,13,"#527487");bool available=detail!=null&&(detail.state=="Ready"||detail.state=="TeamFull"||detail.state=="AlreadyMember");Button(f,"invite-detail-view",view.inviteReady112?"invite-view":"invite-refresh",!view.inviteReady112?T("retry"):detail?.state=="AlreadyMember"?T("open_chat"):T("view_team"),x+24,top+mh-64,cw-48,48,!view.busy&&(!view.inviteReady112||available));
  }
 }
}

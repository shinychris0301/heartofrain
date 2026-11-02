using System;
using System.Globalization;
using System.Linq;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.OnlineSocial;
namespace HeartOfTheRain.App.TeamsAccess {
 public static class TeamsAccessLayout109 {
  static string T(string k)=>TeamsAccessText109.T(k);
  static HomeElement Add(HomeFrame f,string id,string kind,float x,float y,float w,float h,string parent=""){var e=new HomeElement{id=id,kind=kind,x=x,y=y,width=w,height=h,parent=parent,color="#FFFFFF"};f.elements.Add(e);return e;}
  static void Art(HomeFrame f,string id,string asset,float x,float y,float w,float h,bool sliced=true,string parent="",string tint="#FFFFFF"){var e=Add(f,id,"sprite",x,y,w,h,parent);e.asset=asset;e.sliced=sliced;e.preserveAspect=!sliced;e.color=tint;}
  static void Text(HomeFrame f,string id,string value,float x,float y,float w,float h,int size=16,string color="#0B3B54",bool left=true,string parent=""){var e=Add(f,id,left?"lefttext":"text",x,y,w,h,parent);e.text=value??"";e.fontSize=size;e.color=color;}
  static float Para(HomeFrame f,string id,string value,float x,float y,float w,int size=14,string color="#527487",string parent=""){string wrap=HeartOfTheRain.App.Teams.TeamsText.Wrap(value??"",w-2,size);float h=wrap.Split('\n').Length*(size+7);var e=Add(f,id,"paragraph",x,y,w,h,parent);e.text=wrap;e.fontSize=size;e.color=color;return h;}
  static void Button(HomeFrame f,string id,string action,string value,float x,float y,float w,float h,bool enabled=true,string tone="Blue",string parent=""){Art(f,id+"-art",enabled?"TA_Button_"+tone:"TA_Button_Disabled",x,y,w,h,true,parent);Text(f,id+"-label",value,x+10,y+5,w-20,h-10,17,enabled?"#FFFFFF":"#617F90",false,parent);var e=Add(f,id,"group",x,y,w,h,parent);e.action=enabled?action:"disabled";e.label=value;}
  static void CloseDisc(HomeFrame f,string id,string action,float x,float y){Art(f,id+"-art","TA_Close_Disc",x,y,48,48,false);Art(f,id+"-icon","TA_Icon_Close",x+12,y+12,24,24,false);var hit=Add(f,id,"group",x,y,48,48);hit.action=action;hit.label=T("cancel");}
  static void Input(HomeFrame f,string id,string hint,float x,float y,float w,float h,bool enabled=true){Art(f,id+"-art","TA_Field",x,y,w,h);var e=Add(f,id,"input",x+13,y+10,w-26,h-20);e.label=hint;e.fontSize=17;e.color="#0B3B54";e.action=enabled?"":"disabled";}
  static string N(int n)=>n.ToString("N0",CultureInfo.GetCultureInfo(new[]{"en-US","es-ES","fr-FR","de-DE","ru-RU"}[HeartOfTheRain.App.Localization.GameLocale.Current]));
  static void Badge(HomeFrame f,string id,string badge,float x,float y,float size)=>Art(f,id,TeamsAccessBadges109.Asset(badge),x,y,size,size,false);
  public static void Decorate(OnlineTeamsFrame82 r,OnlineTeamsView82 view){r.artScale=Math.Min(520,r.width-28)/1000f;foreach(var e in r.chrome.elements){if(e.id=="online-teams-background"){e.asset="TA_Background";e.sliced=false;e.preserveAspect=true;e.kind="cover109";}if(e.id=="online-team-crest"){e.asset=TeamsAccessBadges109.Asset(view.team?.badgeId);e.sliced=false;e.preserveAspect=true;}}}
  public static OnlineTeamsFrame82 Build(float width,float height,OnlineTeamsView82 view){
   float w=Math.Max(320,width),h=Math.Max(568,height),cw=Math.Min(520,w-28),cx=(w-cw)/2,dh=MainNavigationLayout.ReservedHeight(w,h);
   var r=new OnlineTeamsFrame82{width=w,height=h,artScale=cw/1000};r.chrome.width=r.overlay.width=w;r.chrome.height=r.overlay.height=h;r.content.width=w;
   var bg=Add(r.chrome,"online-teams-background","cover109",0,0,w,h);bg.asset="TA_Background";
   bool member=view.team?.isMember==true,details=view.details!=null||view.detailsOpen||member;float top;
   Text(r.chrome,"online-teams-title",T(details?"team_details":"teams"),cx+(details?4:35),22,cw-(details?68:70),43,29,"#FFFFFF",false);
   if(details){CloseDisc(r.chrome,"online-details-close","close-details",cx+cw-48,20);top=83;}
   else{
    Art(r.chrome,"online-access-tabs","TA_Tab_Track",cx+22,80,cw-44,48);float half=(cw-44)/2;
    Art(r.chrome,"online-access-selected","TA_Tab_Selected",cx+22+(view.accessCreate?half:0),80,half,48);
    Text(r.chrome,"online-access-find-label",T("find_tab"),cx+26,84,half-8,40,20,view.accessCreate?"#BDDFFF":"#FFFFFF",false);
    Text(r.chrome,"online-access-create-label",T("create_tab"),cx+26+half,84,half-8,40,20,view.accessCreate?"#FFFFFF":"#BDDFFF",false);
    var find=Add(r.chrome,"online-access-find","group",cx+22,80,half,48);find.action="access-find";find.label=T("find_tab");
    var create=Add(r.chrome,"online-create","group",cx+22+half,80,half,48);create.action="access-create";create.label=T("create_tab");
    top=142;
    if(!view.accessCreate){float bw=Math.Min(100,cw*.29f);Input(r.chrome,"online-team-search-input",T("search_placeholder"),cx,146,cw-bw-10,48,view.connected);Button(r.chrome,"online-team-search","search",T("search"),cx+cw-bw,146,bw,48,view.connected,"Green");Text(r.chrome,"online-recommended",T("recommended"),cx,210,cw-100,30,18,"#FFFFFF");Button(r.chrome,"online-tab-ranks","tab-ranks",CountryRegion89.T("Rankings"),cx+cw-96,202,96,48,true);top=251;}
   }
   float statusHeight=view.pending?(PendingMessage(view)==T("Pending")?112:160):string.IsNullOrEmpty(view.status)?0:84;
   r.viewportY=top;r.viewportHeight=Math.Max(40,h-dh-statusHeight-top-8);float y=4;
   if(details)Details(r,view,cx,cw,ref y);
   else if(view.accessCreate)Create(r,view,cx,cw,ref y);
   else if(!view.connected&&!string.IsNullOrEmpty(view.unavailableReason)&&view.unavailableReason!=view.status){y+=Para(r.content,"online-unavailable",view.unavailableReason,cx+14,y+15,cw-28,16,"#E7F6FC")+30;}
   else if(view.directory!=null){
    foreach(var team in view.directory.teams??new SocialTeam82[0]){
     string id="online-directory-"+team.teamId;float rh=112;Art(r.content,id+"-base","TA_Panel_Cream",cx,y,cw,rh);Badge(r.content,id+"-badge",team.badgeId,cx+6,y+17,70);
     Text(r.content,id+"-name",team.name,cx+84,y+8,cw-96,31,18);Text(r.content,id+"-count",N(team.memberCount)+" / "+N(team.capacity),cx+87,y+44,cw-195,22,14);
     Text(r.content,id+"-type",T("open"),cx+87,y+72,cw-195,23,14,"#527487");Button(r.content,id,"detail:"+team.teamId,T("details"),cx+cw-101,y+52,91,48,!view.busy&&!view.pending);y+=122;
    }
    if(view.directory.teams==null||view.directory.teams.Length==0)y+=Para(r.content,"online-empty-directory",T(view.searchQuery.Length>0?"no_results":"EmptyTeams"),cx+10,y+16,cw-20,17,"#E7F6FC")+36;
    if(view.directory.hasMore){Button(r.content,"online-more-teams","more",T("More"),cx,y,cw,48,!view.busy&&!view.pending);y+=58;}
   }
   r.content.height=Math.Max(r.viewportHeight,y+8);Status(r,view,cx,cw,dh,statusHeight);MainNavigationLayout.AddDock(r.chrome,w,h,3);
   if(view.modal=="badge")BadgeModal(r,view);else if(view.modal=="invite")Invite(r,view);else if(!string.IsNullOrEmpty(view.modal))r.overlay=OnlineTeamsLayout82.BuildLegacy(w,h,view).overlay;
   return r;
  }
  static void Create(OnlineTeamsFrame82 r,OnlineTeamsView82 v,float x,float w,ref float y){
   float start=y;bool editable=!v.busy&&!v.pending,canSubmit=editable&&v.connected;Art(r.content,"online-create-panel","TA_Panel_Cream",x,start,w,770);
   Text(r.content,"online-name-title",T("team_name"),x+16,y+13,w-32,30,20);Input(r.content,"online-team-name-input",T("team_name"),x+16,y+51,w-32,54,editable);
   Text(r.content,"online-name-count",SocialBackendClient82.TeamTextLength109(v.nameDraft)+" / 32",x+w-130,y+108,110,22,13,"#698896",false);y+=142;if(v.inputError.Length>0&&v.inputErrorField!="description")y+=Para(r.content,"online-name-error",v.inputError,x+18,y-4,w-36,14,"#AB3030")+12;
   Text(r.content,"online-badge-title",T("badge"),x+16,y,w-32,29,20);Badge(r.content,"online-draft-badge",v.badgeId,x+16,y+33,82);Button(r.content,"online-badge-choose","badge-open",T("choose"),x+124,y+48,Math.Min(156,w-146),48,editable);y+=133;
   Text(r.content,"online-description-title",T("description"),x+16,y,w-32,30,20);Input(r.content,"online-team-description-input",T("description"),x+16,y+38,w-32,104,editable);y+=162;if(v.inputError.Length>0&&v.inputErrorField=="description")y+=Para(r.content,"online-description-error",v.inputError,x+18,y-5,w-36,14,"#AB3030")+12;
   Text(r.content,"online-level-title",T("required_level"),x+16,y,w-32,28,18);Text(r.content,"online-level-value",T("service_no_gate"),x+16,y+31,w-32,25,16,"#527487");y+=75;
   Text(r.content,"online-type-title",T("team_type"),x+16,y,w-32,28,18);Art(r.content,"online-type-field","TA_Field",x+16,y+34,w-32,48);Text(r.content,"online-type-value",T("open"),x+30,y+39,w-60,36,18);y+=102;
   string explanation=!v.connected?v.unavailableReason:T("service_free");float note=Para(r.content,"online-create-explanation",explanation,x+18,y,w-36,14);y+=note+12;
   Button(r.content,"online-create-submit","create-submit",T("create"),x+30,y,w-60,52,canSubmit,"Green");y+=71;
   r.content.elements.First(e=>e.id=="online-create-panel").height=y-start+8;y+=20;
  }
  static void Details(OnlineTeamsFrame82 r,OnlineTeamsView82 v,float x,float w,ref float y){
   var team=v.details??v.team;if(team==null)return;
   float start=y;Art(r.content,"online-summary-base","TA_Panel_Cream",x,y,w,390);Badge(r.content,"online-summary-badge",team.badgeId,x+8,y+12,82);
   Text(r.content,"online-summary-name",team.name,x+100,y+12,w-112,36,21);Text(r.content,"online-summary-count",N(team.memberCount)+" / "+N(team.capacity),x+100,y+50,w-112,25,16);
   y+=108;float desc=Para(r.content,"online-about",team.description,x+18,y,w-36,16);y+=Math.Max(28,desc)+15;
   float sw=(w-42)/2;
   string[] labels={"team_score","weekly_helps","required_level","team_type"},icons={"TA_Stat_star","TA_Icon_Help","TA_Stat_up","TA_Icon_People"};
   for(int i=0;i<4;i++){float sx=x+15+i%2*(sw+12),sy=y+i/2*88;Art(r.content,"online-stat-"+i,"TA_Stat",sx,sy,sw,78);Text(r.content,"online-stat-title-"+i,T(labels[i]),sx+6,sy+5,sw-12,27,13,"#527487",false);Art(r.content,"online-stat-icon-"+i,icons[i],sx+11,sy+37,28,28,false,tint:i==1?"#064873":i==3?"#05426B":"#FFFFFF");Text(r.content,"online-stat-value-"+i,i<2?"—":i==2?T("service_none"):T("open"),sx+45,sy+34,sw-54,32,16);}
   y+=181;y+=Para(r.content,"online-stat-service-note",T("service_stats"),x+18,y,w-36,12)+12;
   if(team.isMember){Button(r.content,"online-invite","invite",T("invite"),x+16,y,(w-42)/2,50,!v.busy&&!v.pending);Art(r.content,"online-invite-icon","TA_Icon_Invite",x+28,y+13,24,24,false);var invite=r.content.elements.First(e=>e.id=="online-invite-label");invite.x+=28;invite.width-=28;Button(r.content,"online-leave","leave",T("leave"),x+26+(w-42)/2,y,(w-42)/2,50,!v.busy&&!v.pending,"Red");}
   else Button(r.content,"online-join","join:"+team.teamId,T(team.memberCount>=team.capacity?"team_full":"join"),x+16,y,w-32,52,v.connected&&!v.busy&&!v.pending&&team.memberCount<team.capacity,"Green");
   y+=70;r.content.elements.First(e=>e.id=="online-summary-base").height=y-start+8;y+=27;
   Text(r.content,"online-members",T("members"),x,y,w,32,24,"#FFFFFF");y+=43;
   if(!team.isMember){y+=Para(r.content,"online-private-roster",T("service_private_roster"),x+10,y,w-20,15,"#DAEDF7")+28;return;}
   foreach(var member in team.members??new SocialTeamMember82[0]){
    string id="online-member-"+member.playerId;bool transfer=team.ownerId==v.selfId&&member.playerId!=v.selfId;float rowHeight=transfer?144:84;Art(r.content,id+"-base","TA_Panel_Cream",x,y,w,rowHeight);Art(r.content,id+"-neutral-avatar","TA_Icon_People",x+12,y+22,36,36,false,tint:"#05426B");
    Text(r.content,id+"-name",member.playerId==v.selfId?T("You"):member.displayName,x+60,y+11,w-72,27,18);Text(r.content,id+"-role",T(member.isOwner?"leader":"member"),x+60,y+44,w-72,22,14,"#527487");
    if(member.playerId!=v.selfId){var open=Add(r.content,id+"-open","group",x+54,y+9,w-66,60);open.action="member:"+member.playerId;open.label=member.displayName;}
    if(transfer)Button(r.content,id,"transfer:"+member.playerId,T("Transfer"),x+16,y+80,w-32,48,!v.busy&&!v.pending);y+=rowHeight+10;
   }
   Button(r.content,"online-report-team","report-team",OnlinePlayersText82.T("ReportTeam"),x,y+8,w,48,!v.busy&&!v.pending&&team.ownerId!=v.selfId);y+=66;
  }
  static string PendingMessage(OnlineTeamsView82 v){string reason=v.mutationError.Length>0?v.mutationError:v.status;return string.IsNullOrEmpty(reason)||reason==T("Pending")||reason==T("Loading")?T("Pending"):T("Pending")+"\n"+reason;}
  static void RecoveryCaption(HomeFrame f,string id){
   var hit=f.elements.First(e=>e.id==id);var label=f.elements.First(e=>e.id==id+"-label");label.x=hit.x+5;label.width=hit.width-10;label.fontSize=14;
   // Fixed localized captions only: split at a word boundary into at most
   // two complete lines. The full accessible name on the hit stays unchanged.
   string[] words=label.text.Split(new[]{' '},StringSplitOptions.RemoveEmptyEntries);if(words.Length<2)return;int best=1,spread=int.MaxValue;
   for(int i=1;i<words.Length;i++){int value=Math.Abs(string.Join(" ",words.Take(i)).Length-string.Join(" ",words.Skip(i)).Length);if(value<spread){best=i;spread=value;}}
   label.text=string.Join(" ",words.Take(best))+"\n"+string.Join(" ",words.Skip(best));
  }
  static void Status(OnlineTeamsFrame82 r,OnlineTeamsView82 v,float x,float w,float dock,float h){if(h<=0)return;float y=r.height-dock-h;if(v.pending){float textHeight=Para(r.chrome,"online-status",PendingMessage(v),x+4,y,w-8,12,"#E2F3FA"),by=y+Math.Max(48,textHeight+8),bw=(w-12)/3;Button(r.chrome,"online-check","check-pending",T("Check"),x,by,bw,48,!v.busy);Button(r.chrome,"online-resume","resume-pending",T("Retry"),x+bw+6,by,bw,48,!v.busy);Button(r.chrome,"online-forget","forget",T("Forget"),x+2*(bw+6),by,bw,48,!v.busy);foreach(string id in new[]{"online-check","online-resume","online-forget"})RecoveryCaption(r.chrome,id);}else{Text(r.chrome,"online-status",v.status,x+4,y,w-8,30,12,"#E2F3FA",false);Button(r.chrome,"online-retry","retry",T("Retry"),x,y+32,w,48,!v.busy);}}
  static void Shade(OnlineTeamsFrame82 r){Add(r.overlay,"online-modal-shade","color",0,0,r.width,r.height).color="#061423A6";var block=Add(r.overlay,"online-modal-block","group",0,0,r.width,r.height);block.action="disabled";}
  static void BadgeModal(OnlineTeamsFrame82 r,OnlineTeamsView82 v){
   Shade(r);var f=r.overlay;float mw=Math.Min(390,r.width-24),mh=Math.Min(650,r.height-72),x=(r.width-mw)/2,y=Math.Max(40,(r.height-mh)/2);Art(f,"online-badge-panel","TA_Panel_Blue",x,y,mw,mh);Badge(f,"online-badge-crest",v.badgeDraft,x+(mw-68)/2,y-32,68);
   CloseDisc(f,"online-badge-close","badge-cancel",x+mw-42,y-8);Text(f,"online-badge-title",T("select_badge"),x+18,y+44,mw-36,37,23,"#FFFFFF",false);Text(f,"online-badge-subtitle",T("badge_subtitle"),x+18,y+82,mw-36,28,15,"#BBDDFF",false);
   float gridY=y+122,gridH=mh-260,cell=(mw-54)/3;var grid=Add(f,"online-badge-grid","badgegrid109",x+15,gridY,mw-30,gridH);grid.label="online-badge-grid-content";Add(f,"online-badge-grid-content","group",0,0,mw-30,4*(cell+9),"online-badge-grid");
   for(int i=0;i<12;i++){string badge=TeamsAccessBadges109.Ids[i],id="online-badge-"+badge;float bx=6+i%3*(cell+6),by=i/3*(cell+9);Art(f,id+"-cell",badge==v.badgeDraft?"TA_Badge_Selected":"TA_Badge_Cell",bx,by,cell,cell,true,"online-badge-grid-content");Badge(f,id+"-image",badge,bx+4,by+3,cell-8);f.elements.Last().parent="online-badge-grid-content";if(badge==v.badgeDraft){Art(f,id+"-check","TA_Check_Disc",bx+cell-27,by+cell-27,28,28,false,"online-badge-grid-content");Art(f,id+"-tick","TA_Icon_Check",bx+cell-21,by+cell-21,16,16,false,"online-badge-grid-content");}var hit=Add(f,id,"group",bx,by,cell,cell,"online-badge-grid-content");hit.action="badge:"+badge;hit.label=T("badge_"+badge);}
   float sy=y+mh-125;Art(f,"online-badge-selection","TA_Panel_Inner",x+15,sy,mw-30,54);Badge(f,"online-badge-preview",v.badgeDraft,x+22,sy+2,49);Text(f,"online-badge-name",T("badge_"+TeamsAccessBadges109.Resolve(v.badgeDraft)),x+78,sy+7,mw-100,39,17,"#FFFFFF");Button(f,"online-badge-confirm","badge-confirm",T("choose"),x+38,y+mh-59,mw-76,48,!v.busy&&!v.pending,"Green");
  }
  static void Invite(OnlineTeamsFrame82 r,OnlineTeamsView82 v){Shade(r);var f=r.overlay;float mw=Math.Min(390,r.width-24),mh=310,x=(r.width-mw)/2,y=Math.Max(16,(r.height-mh)/2);Art(f,"online-invite-panel","TA_Panel_Cream",x,y,mw,mh);Text(f,"online-invite-title",T("invite"),x+20,y+17,mw-40,36,23);Para(f,"online-invite-hint",T("service_share"),x+20,y+65,mw-40,15);Text(f,"online-invite-text",v.inviteText,x+20,y+137,mw-40,65,14);Button(f,"online-invite-cancel","cancel",T("cancel"),x+18,y+mh-62,(mw-42)/2,48);Button(f,"online-invite-copy","copy-invite",T("service_copy"),x+24+(mw-42)/2,y+mh-62,(mw-42)/2,48,true,"Green");}
 }
}

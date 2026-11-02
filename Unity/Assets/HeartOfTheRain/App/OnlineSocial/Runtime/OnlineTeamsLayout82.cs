using System;
using System.Linq;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Teams;

namespace HeartOfTheRain.App.OnlineSocial
{
    public sealed class OnlineTeamsView82 {
        public string selfId, status = "", modal = "", confirmationName = "",unavailableReason="";
        public bool busy, pending, connected,unconfigured;
        public int tab;public bool regional,countryLoaded;public string regionCode="",countryError="",countryQuery="";public int countryPage;public SocialTeamLeaderboard89 ranks;
        public SocialTeams82 directory;
        public SocialTeam82 team;
        public SocialMessages82 chat;
        public bool accessCreate,detailsOpen;public int nameCount;public SocialTeam82 details;public string searchQuery="",nameDraft="",descriptionDraft="",badgeId="drop",badgeDraft="drop",inputError="",inputErrorField="",inviteText="",mutationError="";
        public bool giftsOpen110,mail110,composing110,keyboard110,serviceReady110,offline110,hasNewMessages110,composerAvailable110;
        public string leaveState113="",leaveTeamName113="",leaveBadge113="",leaveToast113=""; public bool leaveClosesTeam113,leaveBusy113;
        public UnityEngine.Font font110;public string messageDraft110="",lifeError110="",lifePendingOperation110="",lifePendingRequestId110="";
        public SocialOwnedMail111 ownedMail111;public bool ownedMailOpen111,ownedMailReady111,ownedMailHasBack111;public SocialMailList111 mailList111;public SocialMailMessage111 mailDetail111;public string mailStatus111="";public bool mailOffline111,mailReady111,mailHasBack111;public float mailFontScale111=1;
        public SocialLifeRequests110 life110;public SocialOwnedLives110 ownedLives110;public long now110;
        public SocialInviteFriends112 inviteFriends112;public SocialInvitations112 inviteReceived112;public SocialInvitation112 inviteDetail112;public string inviteQuery112="",inviteNotice112="",invitePendingFriend112="";public bool inviteShare112,inviteLoading112,inviteOffline112,inviteReady112,inviteHasBack112,inviteIncomingHasBack112;
    }
    public sealed class OnlineTeamsFrame82 {
        public float width,height,viewportY,viewportHeight,artScale=1;
        public bool r3SliceScale118;
        public HomeFrame chrome=new HomeFrame(),content=new HomeFrame(),overlay=new HomeFrame();
    }
    public static class OnlineTeamsLayout82
    {
        static string T(string key)=>OnlineTeamsText82.T(key);
        internal static HomeElement Add(HomeFrame f,string id,string kind,float x,float y,float w,float h,string parent="") {
            var value=new HomeElement{id=id,kind=kind,x=x,y=y,width=w,height=h,parent=parent};f.elements.Add(value);return value;
        }
        internal static void Art(HomeFrame f,string id,string asset,float x,float y,float w,float h,string parent="",bool slice=true) {
            var e=Add(f,id,"sprite",x,y,w,h,parent);e.asset=asset;e.sliced=slice;e.color="#FFFFFF";
        }
        internal static void Text(HomeFrame f,string id,string text,float x,float y,float w,float h,int size,string parent="",string color="#21465E",bool left=false) {
            var e=Add(f,id,left?"lefttext":"text",x,y,w,h,parent);e.text=text??"";e.fontSize=size;e.color=color;
        }
        internal static float Para(HomeFrame f,string id,string text,float x,float y,float w,int size,string parent="",string color="#527487") {
            string wrap=TeamsText.Wrap(text,w-2,size);float h=wrap.Split('\n').Length*(size+6);var e=Add(f,id,"paragraph",x,y,w,h,parent);e.text=wrap;e.fontSize=size;e.color=color;return h;
        }
        internal static void Button(HomeFrame f,string id,string action,string text,float x,float y,float w,float h,bool enabled=true,string parent="",bool neutral=false) {
            Art(f,id+"-art",neutral?"LB2_ButtonNeutral":"LB2_TabActive",x,y,w,h,parent);
            Text(f,id+"-label",text,x+7,y+5,w-14,h-11,15,parent,neutral?"#244D66":"#FFFFFF");
            var e=Add(f,id,"group",x,y,w,h,parent);e.action=enabled?action:"disabled";e.label=text;
        }
        internal static void Input(HomeFrame f,string id,string placeholder,float x,float y,float w,float h,string parent="") {
            Art(f,id+"-art","LB2_Search",x,y,w,h,parent);var e=Add(f,id,"input",x+12,y+8,w-24,h-16,parent);e.label=placeholder;e.fontSize=15;e.color="#21465E";
        }
        internal static float Message(HomeFrame f,SocialMessage82 value,bool self,float x,float y,float width,bool actions=false) {
            string id="online-message-"+value.messageId;float inset=self?0:8,w=width-8;
            string wrap=TeamsText.Wrap(value.text,w-28,14);float height=Math.Max(74,46+wrap.Split('\n').Length*20);
            Art(f,id+"-base",self?"LB2_RowSelf":"LB2_Row",x+inset,y,w,height);
            Text(f,id+"-name",self?T("You"):value.displayName,x+inset+14,y+8,w-(actions?82:28),24,15,left:true);
            Para(f,id+"-body",value.text,x+inset+14,y+36,w-28,14);
            return height;
        }
        public static OnlineTeamsFrame82 Build(float width,float height,OnlineTeamsView82 view) {
            long started=System.Diagnostics.Stopwatch.GetTimestamp();
            var frame=BuildBeforeInvites112(width,height,view);
            long phase=System.Diagnostics.Stopwatch.GetTimestamp();NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsLayoutBase,(int)Math.Round((phase-started)*1000.0/System.Diagnostics.Stopwatch.Frequency));
            HeartOfTheRain.App.TeamsInvites.TeamsInvitesLayout112.Decorate(frame,view);
            long next=System.Diagnostics.Stopwatch.GetTimestamp();NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsLayoutInvite,(int)Math.Round((next-phase)*1000.0/System.Diagnostics.Stopwatch.Frequency));
            HeartOfTheRain.App.TeamsLifecycle.TeamsLifecycleLayout113.Decorate(frame,view,width,height);
            NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsLayoutLifecycle,(int)Math.Round((System.Diagnostics.Stopwatch.GetTimestamp()-next)*1000.0/System.Diagnostics.Stopwatch.Frequency));
            if(view.modal=="invite"||view.modal=="invitations112"||view.modal=="invite-detail112")GroupModal118(frame.overlay,"invite-frame","invite-root118","invite-shade");
            else if(view.modal=="mail-detail111")GroupModal118(frame.overlay,"mail-detail-frame","mail-detail-root118","online-modal-shade");
            return frame;
        }
        // Keep the frame, header, body, footer and hit targets on one transform.
        // Nested list content retains its own ScrollRect and is the only moving content.
        static void GroupModal118(HomeFrame overlay,string panelId,string rootId,string shadeId) {
            var panel=overlay.elements.FirstOrDefault(e=>e.id==panelId);if(panel==null)return;
            // The crest deliberately protrudes above the blue panel. Reserve
            // that space in the common root without clipping it.
            float rootY=Math.Max(0,panel.y-40);
            // The close hit area and disc extend beyond the painted panel.
            // Keep that reserved overhang inside the same safe-area root.
            var root=new HomeElement{id=rootId,kind="group",x=panel.x,y=rootY,width=Math.Min(overlay.width-panel.x,panel.width+32),height=panel.y+panel.height-rootY};
            int index=overlay.elements.IndexOf(panel);overlay.elements.Insert(index,root);
            foreach(var e in overlay.elements){
                if(e==root||e.id==shadeId||!string.IsNullOrEmpty(e.parent))continue;
                e.parent=rootId;e.x-=root.x;e.y-=root.y;
            }
        }
        static OnlineTeamsFrame82 BuildBeforeInvites112(float width,float height,OnlineTeamsView82 view) {
            if(view.ownedMailOpen111)return HeartOfTheRain.App.TeamsMail.TeamsMailLayout111.BuildOwned(width,height,view);
            bool member=view.team!=null&&view.team.isMember;
            if(view.giftsOpen110||member&&view.tab==0&&!view.detailsOpen)return HeartOfTheRain.App.TeamsSocial.TeamsSocialLayout110.Build(width,height,view);
            if(view.tab!=2&&(!member||view.tab==1||view.details!=null||view.detailsOpen)){var access=HeartOfTheRain.App.TeamsAccess.TeamsAccessLayout109.Build(width,height,view);HeartOfTheRain.App.TeamsSocial.TeamsSocialLayout110.AddRecoveryEntry(access,view);return access;}
            var result=BuildLegacy(width,height,view);HeartOfTheRain.App.TeamsAccess.TeamsAccessLayout109.Decorate(result,view);return result;
        }
        internal static OnlineTeamsFrame82 BuildLegacy(float width,float height,OnlineTeamsView82 view) {
            if(view==null)throw new ArgumentNullException(nameof(view));
            var r=new OnlineTeamsFrame82{width=Math.Max(320,width),height=Math.Max(568,height)};
            float w=r.width,h=r.height,cw=Math.Min(w-28,720),cx=(w-cw)/2,dh=MainNavigationLayout.ReservedHeight(w,h);
            foreach(var f in new[]{r.chrome,r.overlay}){f.width=w;f.height=h;}r.content.width=w;
            Art(r.chrome,"online-teams-background","LB2_Background",0,0,w,h,"",false);
            Text(r.chrome,"online-teams-title",T("Teams"),30,8,w-60,38,28,color:"#FFFFFF");
            bool member=view.team!=null&&view.team.isMember;
            float top;
            if(member) {
                Art(r.chrome,"online-team-header","LB2_Row",cx,52,cw,68);
                Art(r.chrome,"online-team-crest","LB_CrestWell_R2",cx+8,57,58,58,"",false);
                Text(r.chrome,"online-team-name",view.team.name,cx+75,62,cw-90,24,20,left:true);
                Text(r.chrome,"online-team-count",OnlineTeamsText82.Format("Count",view.team.memberCount,view.team.capacity),cx+75,89,cw-90,19,12,left:true);
                float bw=(cw-12)/3;
                Button(r.chrome,"online-tab-chat","tab-chat",T("Chat"),cx,132,bw,44,true,"",view.tab!=0);
                Button(r.chrome,"online-tab-info","tab-info",T("Info"),cx+bw+6,132,bw,44,true,"",view.tab!=1);
                Button(r.chrome,"online-tab-ranks","tab-ranks",CountryRegion89.T("Rankings"),cx+2*(bw+6),132,bw,44,true,"",view.tab!=2);
                top=188;
            } else {
                Text(r.chrome,"online-no-team",T("NoTeam"),cx,52,cw,32,22,color:"#FFFFFF");
                Text(r.chrome,"online-no-team-hint",view.unconfigured?T("OnlineRequired"):view.connected?T("NoTeamHint"):T("Unavailable"),cx,87,cw,36,12,color:"#BDD8E9");
                float bw=(cw-6)/2;Button(r.chrome,"online-create","create",T("Create"),cx,132,bw,44,view.connected,neutral:!view.connected);
                if(view.connected)Button(r.chrome,"online-tab-ranks","tab-ranks",CountryRegion89.T("Rankings"),cx+bw+6,132,bw,44,true,neutral:view.tab!=2);
                else {Button(r.chrome,"online-join","join",T("JoinTeam"),cx+bw+6,132,bw,44,false,neutral:true);foreach(var e in r.chrome.elements)if(e.id=="online-create-art"||e.id=="online-join-art")e.color="#B9CAD2";}
                top=188;
            }
            if(view.tab==2)top=CountryRegion89.Controls(r.chrome,cx,top,cw,view.regional,view.regionCode,true,"teams-region");
            float statusHeight=view.pending?108:string.IsNullOrEmpty(view.status)?0:72;
            float footer=member&&view.tab==0?60:0;
            r.viewportY=top;r.viewportHeight=Math.Max(40,h-dh-statusHeight-footer-10-top);
            float y=4;
            if(!view.connected&&view.directory==null&&view.team==null) {
                y+=Para(r.content,"online-unavailable",string.IsNullOrEmpty(view.unavailableReason)?T("Unavailable"):view.unavailableReason,cx+8,y+8,cw-16,16,color:"#E7F6FC")+35;
            } else if(view.tab==2){
                if(view.regional&&CountryRegion89.Normalize(view.regionCode).Length==0)y+=Para(r.content,"online-team-country-required",(view.countryLoaded?CountryRegion89.T("SelectCountry"):T("Unavailable")),cx+8,y+15,cw-16,16,color:"#E7F6FC")+35;
                else OnlinePlayersLayout82.TeamRankingContent(r.content,view.ranks,view.regional,view.regionCode,cx,ref y,cw,view.busy);
            } else if(!member) {
                if(view.directory!=null) {
                    foreach(var team in view.directory.teams) {
                        string id="online-directory-"+team.teamId;
                        Art(r.content,id+"-base","LB2_Row",cx,y,cw,94);
                        Text(r.content,id+"-name",team.name,cx+12,y+10,cw-118,25,18,left:true);
                        Text(r.content,id+"-count",OnlineTeamsText82.Format("Count",team.memberCount,team.capacity),cx+12,y+44,cw-118,31,11,left:true);
                        Button(r.content,id,"join:"+team.teamId,T(team.memberCount>=team.capacity?"Full":"Join"),cx+cw-101,y+25,89,45,!view.busy&&!view.pending&&team.memberCount<team.capacity);
                        y+=104;
                    }
                    if(view.directory.teams.Length==0) y+=Para(r.content,"online-empty-directory",T("EmptyTeams"),cx+8,y+15,cw-16,17,color:"#E7F6FC")+35;
                    if(view.directory.hasMore){Button(r.content,"online-more-teams","more",T("More"),cx,y,cw,44,!view.busy);y+=54;}
                }
            } else if(view.tab==0) {
                if(view.chat!=null&&(view.chat.hasOlder||view.chat.hasNewer))OnlinePlayersLayout82.HistoryControls(r.content,"online-team",cx,ref y,cw,view.busy,view.chat.hasOlder);
                foreach(var message in view.chat?.messages??new SocialMessage82[0]) {
                    bool other=message.authorId!=view.selfId;float messageHeight=Message(r.content,message,!other,cx,y,cw,other);
                    if(other){Button(r.content,"online-message-menu-"+message.messageId,"report-message:"+message.messageId,"⋯",cx+cw-54,y+5,38,28,!view.busy&&!view.pending,neutral:true);var author=Add(r.content,"online-message-author-"+message.messageId,"group",cx+22,y+8,cw-96,24);author.action="member:"+message.authorId;author.label=message.displayName;}
                    y+=messageHeight+8;
                }
                if(view.chat!=null&&view.chat.messages.Length==0)y+=Para(r.content,"online-empty-chat",T("EmptyChat"),cx+8,y+15,cw-16,18,color:"#E7F6FC")+40;
                Button(r.chrome,"online-compose","compose",T("Message"),cx,h-dh-statusHeight-54,cw,48,!view.busy&&!view.pending);
            } else {
                float about=Para(new HomeFrame(),"measure",view.team.description,0,0,cw-28,14)+30;
                Art(r.content,"online-about-base","LB2_RowSelf",cx,y,cw,about);
                Para(r.content,"online-about",view.team.description,cx+14,y+15,cw-28,14);y+=about+16;
                Text(r.content,"online-members",T("Members"),cx+6,y,cw-12,25,17,color:"#E7F6FC",left:true);y+=35;
                foreach(var memberValue in view.team.members??new SocialTeamMember82[0]) {
                    string id="online-member-"+memberValue.playerId;bool transfer=view.team.ownerId==view.selfId&&memberValue.playerId!=view.selfId;
                    Art(r.content,id+"-base","LB2_Row",cx,y,cw,76);
                    Text(r.content,id+"-name",memberValue.playerId==view.selfId?T("You"):memberValue.displayName,cx+12,y+9,cw-(transfer?132:24),25,17,left:true);
                    Text(r.content,id+"-role",T(memberValue.isOwner?"Leader":"Member"),cx+12,y+40,cw-(transfer?132:24),19,11,left:true);
                    if(memberValue.playerId!=view.selfId){var open=Add(r.content,id+"-open","group",cx+12,y+8,cw-(transfer?140:24),54);open.action="member:"+memberValue.playerId;open.label=memberValue.displayName;}
                    if(transfer)Button(r.content,id,"transfer:"+memberValue.playerId,T("Transfer"),cx+cw-116,y+16,104,45,!view.busy&&!view.pending,neutral:true);
                    y+=85;
                }
                Button(r.content,"online-report-team","report-team",OnlinePlayersText82.T("ReportTeam"),cx,y+8,cw,46,!view.busy&&!view.pending&&view.team.ownerId!=view.selfId,neutral:true);y+=60;
                Button(r.content,"online-leave","leave",T("Leave"),cx,y+8,cw,46,!view.busy&&!view.pending,neutral:true);y+=65;
            }
            r.content.height=Math.Max(r.viewportHeight,y+5);
            if(statusHeight>0) {
                float sy=h-dh-statusHeight;
                Text(r.chrome,"online-status",view.pending?T("Pending"):view.status,cx+4,sy+1,cw-8,view.pending?42:32,11,color:"#E0EFF8");
                if(view.pending) {
                    float third=(cw-12)/3;Button(r.chrome,"online-check","check-pending",T("Check"),cx,sy+49,third,44,!view.busy);
                    Button(r.chrome,"online-resume","resume-pending",T("Retry"),cx+third+6,sy+49,third,44,!view.busy);
                    Button(r.chrome,"online-forget","forget",T("Forget"),cx+2*(third+6),sy+49,third,44,!view.busy,neutral:true);
                } else Button(r.chrome,"online-retry","retry",T("Retry"),cx,sy+34,cw,34,!view.busy);
            }
            MainNavigationLayout.AddDock(r.chrome,w,h,3);
            if(!string.IsNullOrEmpty(view.modal)) Modal(r,view,cx,cw);
            return r;
        }
        static void Modal(OnlineTeamsFrame82 r,OnlineTeamsView82 view,float cx,float cw) {
            if(view.modal=="country"){CountryRegion89.Modal(r.overlay,r.width,r.height,view.busy,view.countryError,view.countryQuery,view.countryPage);return;}
            var f=r.overlay;float w=r.width,h=r.height,mw=Math.Min(380,w-24),mx=(w-mw)/2;
            bool create=view.modal=="create",compose=view.modal=="compose",forget=view.modal=="forget";
            float mh=create?378:compose?294:forget?Math.Max(300,145+Para(new HomeFrame(),"measure",T("ForgetWarning"),0,0,mw-40,14)):232,my=Math.Max(8,(h-mh)/2);
            var shade=Add(f,"online-modal-shade","color",0,0,w,h);shade.color="#061423B8";
            var block=Add(f,"online-modal-block","group",0,0,w,h);block.action="disabled";block.label=T("Cancel");
            Art(f,"online-modal-base","LB2_Dialog",mx,my,mw,mh);
            string title=view.modal=="report"?OnlinePlayersText82.T("Report"):T(create?"Create":compose?"Message":forget?"ForgetTitle":view.modal=="leave"?"LeaveTitle":"TransferTitle");
            Text(f,"online-modal-title",title,mx+18,my+19,mw-75,34,22,left:true);
            Button(f,"online-modal-cancel","cancel",T("Cancel"),mx+18,my+mh-57,(mw-42)/2,44,!view.busy,neutral:true);
            Button(f,"online-modal-confirm",create?"create-submit":compose?"send":"confirm",T(create?"Create":compose?"Send":"Confirm"),mx+24+(mw-42)/2,my+mh-57,(mw-42)/2,44,!view.busy);
            if(create) {Input(f,"online-team-name-input",T("Name"),mx+16,my+70,mw-32,52);Input(f,"online-team-description-input",T("Description"),mx+16,my+137,mw-32,158);}
            else if(compose) Input(f,"online-message-input",T("Write"),mx+16,my+76,mw-32,138);
            else if(forget) Para(f,"online-forget-warning",T("ForgetWarning"),mx+20,my+70,mw-40,14);
            else Para(f,"online-confirmation-name",view.modal=="report"?OnlinePlayersText82.T("ReviewHint"):view.confirmationName,mx+20,my+73,mw-40,17);
        }
    }
}

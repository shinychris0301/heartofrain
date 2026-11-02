using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.Teams;
using HeartOfTheRain.App.TeamsAccess;
using UnityEngine;

namespace HeartOfTheRain.App.TeamsSocial
{
    public static class TeamsSocialLayout110
    {
        // Layout runs on Unity's main thread. Reusing the native generator
        // avoids allocating and initializing one for every chat bubble.
        static readonly TextGenerator BodyMeasure110=new TextGenerator();
        static string T(string key) => TeamsSocialText110.T(key);
        static HomeElement Add(HomeFrame f,string id,string kind,float x,float y,float w,float h) { var e=new HomeElement{id=id,kind=kind,x=x,y=y,width=w,height=h};f.elements.Add(e);return e; }
        static void Art(HomeFrame f,string id,string asset,float x,float y,float w,float h,bool sliced=true,string tint="#FFFFFF") { var e=Add(f,id,"sprite",x,y,w,h);e.asset=asset;e.sliced=sliced;e.preserveAspect=!sliced;e.color=tint; }
        static void Text(HomeFrame f,string id,string value,float x,float y,float w,float h,int size=14,string color="#3B5D77",bool left=true,string kind=null) {var e=Add(f,id,kind??(left?"lefttext":"text"),x,y,w,h);e.text=value??"";e.fontSize=size;e.color=color;}
        static void Button(HomeFrame f,string id,string action,string value,float x,float y,float w,float h,bool enabled=true,string tone="Blue") {Art(f,id+"-art",enabled?"TA_Button_"+tone:"TA_Button_Disabled",x,y,w,h);Text(f,id+"-label",value,x+9,y+4,w-18,h-8,15,enabled?"#FFFFFF":"#617F90",false);var e=Add(f,id,"group",x,y,w,h);e.action=enabled?action:"disabled";e.label=value;}
        static void RecoveryCaption(HomeFrame frame,string id)
        {
            var hit=frame.elements.First(value=>value.id==id);var label=frame.elements.First(value=>value.id==id+"-label");label.x=hit.x+5;label.width=hit.width-10;label.fontSize=14;
            // Only fixed localized captions are split. Keep every word and the
            // unchanged full accessible name/action on the 48-unit touch target.
            string[] words=label.text.Split(new[]{' '},StringSplitOptions.RemoveEmptyEntries);if(words.Length<2)return;int best=1,spread=int.MaxValue;
            for(int i=1;i<words.Length;i++){int difference=Math.Abs(string.Join(" ",words.Take(i)).Length-string.Join(" ",words.Skip(i)).Length);if(difference<spread){best=i;spread=difference;}}
            label.text=string.Join(" ",words.Take(best))+"\n"+string.Join(" ",words.Skip(best));
        }
        static float BodyHeight(string value,float width,int size,Font font)
        {
            long started=System.Diagnostics.Stopwatch.GetTimestamp();
            try {
                value=DisplayText110(value,font);
                if(font){var settings=new TextGenerationSettings{font=font,fontSize=size,scaleFactor=1,lineSpacing=1,richText=false,fontStyle=FontStyle.Normal,horizontalOverflow=HorizontalWrapMode.Wrap,verticalOverflow=VerticalWrapMode.Overflow,generationExtents=new Vector2(width,10000),textAnchor=TextAnchor.UpperLeft,alignByGeometry=false};return Math.Max(size+6,Mathf.Ceil(BodyMeasure110.GetPreferredHeight(value??"",settings))+6);}
                return Math.Max(size+6,TeamsText.Wrap(value,width,size).Split('\n').Length*(size+8));
            } finally {
                int elapsed=(int)Math.Round((System.Diagnostics.Stopwatch.GetTimestamp()-started)*1000.0/System.Diagnostics.Stopwatch.Frequency);
                if(elapsed>=5)NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsBodyMeasure,elapsed);
            }
        }
        public static string DisplayText110(string value,Font font)
        {
            value=PlainText118(value);if(!font)return value;var text=new System.Text.StringBuilder();string fallback=font.HasCharacter('□')?"□":"?";
            for(int i=0;i<value.Length;i++){char c=value[i];if(char.IsHighSurrogate(c)&&i+1<value.Length&&char.IsLowSurrogate(value[i+1])){text.Append(fallback);i++;}else if(char.IsWhiteSpace(c)||font.HasCharacter(c))text.Append(c);else text.Append(fallback);}return text.ToString();
        }
        static readonly HashSet<string> RichTags118=new HashSet<string>(StringComparer.OrdinalIgnoreCase){"b","i","u","s","size","color","material","quad","sprite","sub","sup","mark","link","align","font","noparse"};
        // Only known rich-text tags are removed for display. The server's
        // original message remains untouched and ordinary comparisons survive.
        public static string PlainText118(string value){
            if(string.IsNullOrEmpty(value))return "";
            var text=new System.Text.StringBuilder(value.Length);
            for(int i=0;i<value.Length;i++){
                if(value[i]=='<'&&i+2<value.Length){int start=i+1;if(value[start]=='/')start++;int nameEnd=start;
                    while(nameEnd<value.Length&&(char.IsLetter(value[nameEnd])||value[nameEnd]=='-'))nameEnd++;
                    if(nameEnd>start&&RichTags118.Contains(value.Substring(start,nameEnd-start))){
                        int count=Math.Min(64,value.Length-nameEnd);int end=value.IndexOf('>',nameEnd,count);
                        if(end>=nameEnd&&end-start<=64&&value.IndexOf('<',nameEnd,end-nameEnd)<0&&value.IndexOf('\n',nameEnd,end-nameEnd)<0){i=end;continue;}
                    }
                }
                text.Append(value[i]);
            }
            return text.ToString();
        }
        static string TimeLabel(long utc)
        {
            long started=System.Diagnostics.Stopwatch.GetTimestamp();
            try{return DateTimeOffset.FromUnixTimeSeconds(utc).ToLocalTime().ToString("g",CultureInfo.GetCultureInfo(new[]{"en-US","es-ES","fr-FR","de-DE","ru-RU"}[HeartOfTheRain.App.Localization.GameLocale.Current]));}catch(Exception){return "";}
            finally{int elapsed=(int)Math.Round((System.Diagnostics.Stopwatch.GetTimestamp()-started)*1000.0/System.Diagnostics.Stopwatch.Frequency);if(elapsed>=5)NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsTimestamp,elapsed);}
        }
        public static string Countdown(long seconds) {seconds=Math.Max(0,seconds);return ((int)(seconds/3600)).ToString("00")+":"+((seconds/60)%60).ToString("00")+":"+(seconds%60).ToString("00");}
        public static string DraftCount110(string draft,out bool invalid){string clean;int count=SocialBackendClient82.TeamTextLength109(draft);invalid=!string.IsNullOrWhiteSpace(draft)&&!SocialBackendClient82.TryMessageDraft110(draft,out clean);string value=(count==int.MaxValue?"—":count.ToString(CultureInfo.InvariantCulture))+" / "+SocialBackendClient82.TeamMessageLimit110;return invalid&&count<=SocialBackendClient82.TeamMessageLimit110?T("invalid_message")+" · "+value:value;}
        static float Message(OnlineTeamsFrame82 r,OnlineTeamsView82 v,SocialMessage82 message,float x,float y,float width)
        {
            bool own=message.authorId==v.selfId;string id="online-message-"+message.messageId;float aw=46,gap=12,bw=width-aw-gap,bx=own?x:x+aw+gap;
            Art(r.content,id+"-avatar-base","TA_Badge_Cell",own?x+width-aw:x,y+5,aw,aw);Art(r.content,id+"-neutral-avatar","TA_Icon_People",own?x+width-aw+9:x+9,y+14,28,28,false,"#E7F6FC");
            // Keep the timestamp above the painted bubble's bottom border.
            float body=BodyHeight(message.text,bw-30,14,v.font110),height=22+body+49;
            Art(r.content,id+"-base",own?"TC_Bubble_Outgoing":"TC_Bubble_Incoming",bx,y,bw,height);
            Text(r.content,id+"-name",own?T("you"):message.displayName,bx+16,y+7,bw-(own?30:70),23,15,"#073354");
            Text(r.content,id+"-body",message.text,bx+16,y+33,bw-32,body,14,"#3B5D77",true,"chatbody110");
            Text(r.content,id+"-timestamp",TimeLabel(message.createdAt),bx+16,y+34+body,bw-32,21,10,"#688CA5",false);
            if(!own){var menu=Add(r.content,"online-message-menu-"+message.messageId,"group",bx+bw-48,y,48,48);menu.action=v.busy||v.pending?"disabled":"report-message:"+message.messageId;menu.label=T("report");Art(r.content,menu.id+"-icon","TC_Icon_More",bx+bw-34,y+11,22,22,false,"#3B5D77");var author=Add(r.content,"online-message-author-"+message.messageId,"group",bx+12,y+1,bw-65,48);author.action="member:"+message.authorId;author.label=message.displayName;}
            return height+12;
        }
        static float RequestCard(OnlineTeamsFrame82 r,OnlineTeamsView82 v,SocialLifeRequest110 request,float x,float y,float width,bool saved=false)
        {
            bool own=request.playerId==v.selfId;string id="online-life-"+request.requestId;float aw=saved?0:46,gap=saved?0:12,bw=width-aw-gap,bx=own?x:x+aw+gap;
            if(!saved){Art(r.content,id+"-avatar-base","TA_Badge_Cell",own?x+width-aw:x,y+5,aw,aw);Art(r.content,id+"-neutral-avatar","TA_Icon_People",own?x+width-aw+9:x+9,y+14,28,28,false,"#E7F6FC");}
            float actionW=Math.Min(124,bw*.47f),actionX=bx+bw-actionW-10;float heartsW=bw-actionW-28,hs=Math.Min(19,(heartsW-4*(float)Math.Min(3,heartsW*.025))/5),step=hs+Math.Min(3,heartsW*.025f);
            string hint=own&&request.remaining>0&&request.state!="Open"&&!request.canCollect?T(request.collectBlockedReason=="FullLives"?"lives_full_hint":"service_unavailable"):"";
            float hintHeight=hint.Length==0?0:BodyHeight(hint,bw-28,12,v.font110)+8;
            float h=158+hintHeight;Art(r.content,id+"-base","TA_Panel_Cream",bx,y,bw,h);
            Text(r.content,id+"-name",own?T("you"):request.displayName,bx+14,y+8,bw-28,24,15,"#073354");
            string state=own?(request.remaining>0&&request.state!="Open"?T("ready"):request.state=="Claimed"?T("claimed"):request.state=="Open"?T("request_title"):T("request_closed")):T("request_title");
            Text(r.content,id+"-state",state,bx+14,y+34,bw-28,25,13,own&&request.canCollect?"#098A2B":"#527487");
            for(int i=0;i<request.required;i++)Art(r.content,id+"-heart-"+i,"TA_Stat_heart",bx+14+i*step,y+78,hs,hs,false,i<request.received?"#FFFFFF":"#A9C0CF");
            Text(r.content,id+"-count",request.received+" / "+request.required,bx+12,y+102,Math.Max(40,heartsW),22,12,"#073354",false);
            bool pending=v.lifePendingRequestId110==request.requestId||v.lifePendingOperation110=="life.request"&&own;
            bool enabled=v.connected&&!v.busy&&!v.pending&&!v.offline110&&v.serviceReady110;
            string caption,action="disabled",tone="Green";
            if(pending){caption=T(v.lifePendingOperation110=="life.claim"?"claim_pending":v.lifePendingOperation110=="life.help"?"sending":"request_pending");if(!string.IsNullOrEmpty(v.lifeError110)){caption=T("retry");action="resume-pending";}}
            else if(own){if(request.canCollect){caption=T("claim");action="claim-life:"+request.requestId;}else if(request.remaining>0&&request.state!="Open"){caption=T("collect_later");}else caption=T(request.state=="Claimed"?"claimed":request.state=="Open"?"waiting":"request_closed");}
            else if(request.canHelp){caption=T("help");action="help-life:"+request.requestId;}
            else caption=T(request.helped?"help_sent":request.state=="Open"?"waiting":request.received>=request.required?"request_full":"request_expired");
            Button(r.content,id+"-action",action,caption,actionX,y+74,actionW,48,(enabled||pending&&action=="resume-pending"&&v.connected&&!v.busy)&&action!="disabled",tone);
            if(request.helped)Art(r.content,id+"-sent-check","TA_Icon_Check",actionX+actionW/2-7,y+59,14,14,false,"#527487");
            string note=own&&request.remaining>0&&request.claimed>0?TeamsSocialText110.Format("claim_remainder","count",request.remaining):TimeLabel(request.createdAt);
            Text(r.content,id+"-timestamp",note,bx+12,y+129,bw-24,20,10,"#688CA5",false);
            if(hintHeight>0)Text(r.content,id+"-capacity-hint",hint,bx+14,y+152,bw-28,hintHeight-8,12,"#527487",true,"chatbody110");
            return h+12;
        }
        public static OnlineTeamsFrame82 Build(float width,float height,OnlineTeamsView82 v)
        {
            long started=System.Diagnostics.Stopwatch.GetTimestamp();
            float w=Math.Max(320,width),h=Math.Max(1,height),cw=Math.Min(520,w-28),x=(w-cw)/2,dh=MainNavigationLayout.ReservedHeight(w,h);
            var r=new OnlineTeamsFrame82{width=w,height=h,artScale=cw/1000};r.chrome.width=r.overlay.width=w;r.chrome.height=r.overlay.height=h;r.content.width=w;
            var bg=Add(r.chrome,"online-teams-background","cover109",0,0,w,h);bg.asset="TA_Background";
            bool compactPending=v.pending&&!v.giftsOpen110&&!v.keyboard110;
            if(!v.keyboard110)Text(r.chrome,"online-teams-title",T(v.giftsOpen110?"saved_lives":"teams"),x+(compactPending?8:35),13,cw-(compactPending?116:70),38,28,"#FFFFFF",false);
            bool enabled=v.connected&&!v.busy&&!v.pending&&!v.offline110;
            float top;
            if(v.giftsOpen110){Button(r.chrome,"online-saved-close","close-saved-lives",T("cancel"),x+cw-96,59,96,48,true);top=118;}
            else {
                float sy=v.keyboard110?4:61,sh=v.keyboard110?56:compactPending?82:110,ty=sy+sh+12;
                Art(r.chrome,"online-team-header","TA_Panel_Cream",x,sy,cw,sh);Art(r.chrome,"online-team-crest",TeamsAccessBadges109.Asset(v.team?.badgeId),x+7,sy+(v.keyboard110?6:compactPending?9:12),v.keyboard110?44:64,v.keyboard110?44:64,false);
                float nameX=x+(v.keyboard110?60:78),nameW=cw-(v.keyboard110?163:181);Text(r.chrome,"online-team-name",v.team?.name,nameX,sy+9,nameW,31,17,"#073354",true,"chatname110");var fullName=Add(r.chrome,"online-team-name-open","group",nameX-1,sy+1,nameW+3,48);fullName.action=v.composing110?"disabled":"tab-info";fullName.label=v.team?.name??"";
                if(!v.keyboard110){Art(r.chrome,"online-team-count-icon","TA_Icon_People",x+80,sy+50,20,20,false,"#05426B");Text(r.chrome,"online-team-count",(v.team?.memberCount??0)+" / "+(v.team?.capacity??0),x+104,sy+48,cw-213,23,12,"#073354");}
                Button(r.chrome,v.composing110?"online-compose-cancel":"online-tab-info",v.composing110?"cancel-compose":"tab-info",T(v.composing110?"cancel":"team_info"),x+cw-96,sy+(v.keyboard110?4:compactPending?16:6),88,48,true);if(!v.keyboard110)Button(r.chrome,"online-tab-ranks","tab-ranks",T("rankings"),x+cw-96,compactPending?9:sy+58,88,48,!v.composing110);
                Art(r.chrome,"online-chat-tabs-base","TA_Tab_Track",x,ty,cw,48);Art(r.chrome,"online-chat-tab-selected","TA_Tab_Selected",x+(v.mail110?cw/2:0),ty,cw/2,48);
                Text(r.chrome,"online-chat-tab-label",T("chat"),x+30,ty+6,cw/2-40,34,19,"#FFFFFF",false);Text(r.chrome,"online-mail-tab-label",T("mail"),x+cw/2+30,ty+6,cw/2-40,34,19,v.mail110?"#FFFFFF":"#BDDFFF",false);
                Art(r.chrome,"online-chat-tab-icon","TC_Icon_Chat",x+12,ty+16,21,21,false,"#FFFFFF");Art(r.chrome,"online-mail-tab-icon","TC_Icon_Mail",x+cw/2+12,ty+16,21,21,false,"#BDDFFF");
                if(v.mailList111!=null&&v.mailList111.unreadCount>0){Art(r.chrome,"mail-unread-disc","TC_Notification_Disc",x+cw-44,ty+7,34,34,false);Text(r.chrome,"mail-unread-badge",v.mailList111.unreadCount>99?"99+":v.mailList111.unreadCount.ToString(),x+cw-44,ty+7,34,34,11,"#FFFFFF",false);}
                var chat=Add(r.chrome,"online-tab-chat","group",x,ty,cw/2,48);chat.action=v.composing110?"disabled":"tab-chat";chat.label=T("chat");var mail=Add(r.chrome,"online-tab-mail","group",x+cw/2,ty,cw/2,48);mail.action=v.composing110?"disabled":"tab-mail";mail.label=T("mail");top=ty+59;
            }
            long phase=System.Diagnostics.Stopwatch.GetTimestamp();NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsChatHeader,(int)Math.Round((phase-started)*1000.0/System.Diagnostics.Stopwatch.Frequency));
            float status=v.pending?154:string.IsNullOrEmpty(v.lifeError110)&&string.IsNullOrEmpty(v.status)?0:64;
            float actions=v.giftsOpen110||v.mail110||v.pending?0:v.composing110?98:60;float bottom=v.keyboard110?10:dh;
            r.viewportY=top;r.viewportHeight=Math.Max(0,h-bottom-actions-status-top-9);float y=5;
            if(v.giftsOpen110){foreach(var request in v.ownedLives110?.requests??new SocialLifeRequest110[0])y+=RequestCard(r,v,request,x,y,cw,true);if(v.ownedLives110?.hasMore==true){Button(r.content,"online-saved-more","more-saved-lives",OnlineTeamsText82.T("More"),x,y,cw,48,enabled);y+=58;}if(v.ownedLives110!=null&&v.ownedLives110.requests.Length==0)Text(r.content,"online-saved-empty",T("claimed"),x+12,y,cw-24,48,17,"#E7F6FC",false);}
            else if(v.mail110){HeartOfTheRain.App.TeamsMail.TeamsMailLayout111.Content(r,v,x,ref y,cw);}
            else {
                if(v.ownedMail111?.rewards?.Length>0){Button(r.content,"online-mail-owned","mail-owned",HeartOfTheRain.App.TeamsMail.TeamsMailText111.T("saved_rewards"),x,y,cw,48,enabled);y+=58;}
                if(v.ownedLives110?.requests?.Any(row=>row.remaining>0)==true){Button(r.content,"online-saved-lives","saved-lives",T("saved_lives"),x,y,cw,48,enabled);y+=58;}
                if(v.chat?.hasOlder==true){Button(r.content,"online-team-older","older-messages",OnlinePlayersText82.T("Older"),x,y,cw,48,enabled);y+=58;}
                var requests=(v.life110?.requests??new SocialLifeRequest110[0]).ToDictionary(value=>value.messageId,StringComparer.Ordinal);
                var own=v.life110?.ownRequest;if(own!=null&&!(v.chat?.messages??new SocialMessage82[0]).Any(m=>m.messageId==own.messageId)){y+=RequestCard(r,v,own,x,y,cw);}
                foreach(var message in v.chat?.messages??new SocialMessage82[0]){SocialLifeRequest110 request;if(requests.TryGetValue(message.messageId,out request))y+=RequestCard(r,v,request,x,y,cw);else y+=Message(r,v,message,x,y,cw);}
                if(v.chat!=null&&v.chat.messages.Length==0){Art(r.content,"online-chat-empty-badge",TeamsAccessBadges109.Asset(v.team?.badgeId),x+cw/2-37,y+10,74,74,false);Text(r.content,"online-empty-chat",T("empty_chat"),x+12,y+92,cw-24,34,20,"#FFFFFF",false);float body=BodyHeight(T("welcome_text"),cw-36,15,v.font110);Text(r.content,"online-chat-welcome",T("welcome_text"),x+18,y+134,cw-36,body,15,"#D9EBF6",false,"chatbody110");y+=145+body;}
                if(v.chat?.hasNewer==true){Button(r.content,"online-team-latest","latest-messages",T("new_messages"),x,y,cw,48,enabled);y+=58;}
                else if(v.hasNewMessages110)Button(r.chrome,"online-team-latest","latest-messages",T("new_messages"),x+cw-150,r.viewportY+r.viewportHeight-50,150,48,enabled);
                float ay=h-bottom-status-actions;
                if(!v.pending&&v.composing110){Art(r.chrome,"online-composer-base","TA_Panel_Cream",x,ay,cw,92);Art(r.chrome,"online-message-input-art","TA_Field",x+9,ay+9,cw-80,64);var input=Add(r.chrome,"online-message-input","input",x+20,ay+17,cw-103,46);input.label=T("compose_placeholder");input.fontSize=15;input.color="#073354";input.action=v.composerAvailable110?"":"disabled";
                    string clean;Button(r.chrome,"online-compose-send","send","",x+cw-66,ay+10,56,56,v.composerAvailable110&&SocialBackendClient82.TryMessageDraft110(v.messageDraft110,out clean));Art(r.chrome,"online-compose-send-icon","TC_Icon_Send",x+cw-54,ay+22,32,32,false,"#FFFFFF");bool invalid;string count=DraftCount110(v.messageDraft110,out invalid);Text(r.chrome,"online-message-count",count,x+12,ay+72,cw-24,18,11,invalid?"#B2412C":"#688CA5");
                }else if(!v.pending){float half=(cw-12)/2;long wait=(v.life110?.nextRequestAt??0)-v.now110;string caption=v.lifePendingOperation110=="life.request"?T("request_pending"):wait>0?T("request_again")+"\n"+Countdown(wait):T("request_lives");bool existing=v.life110?.ownRequest?.state=="Open";Button(r.chrome,"online-request-lives","request-lives",caption,x,ay,half,48,enabled&&v.serviceReady110&&(wait<=0||existing),"Green");Button(r.chrome,"online-compose","compose",T("message"),x+half+12,ay,half,48,v.composerAvailable110);}
            }
            r.content.height=Math.Max(r.viewportHeight,y+8);
            long next=System.Diagnostics.Stopwatch.GetTimestamp();NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsChatContent,(int)Math.Round((next-phase)*1000.0/System.Diagnostics.Stopwatch.Frequency));
            if(status>0){float sy=h-bottom-status;string notice=string.IsNullOrEmpty(v.lifeError110)?v.status:v.lifeError110;Text(r.chrome,"online-status",v.pending?OnlineTeamsText82.T("Pending")+ (notice.Length>0?"\n"+notice:""):notice,x+6,sy+4,cw-12,v.pending?84:50,12,"#E7F6FC",false);
                if(v.pending){float bw=(cw-12)/3;string[] ids={"check","resume","forget"},acts={"check-pending","resume-pending","forget"},keys={"Check","Retry","Forget"};for(int i=0;i<3;i++){Button(r.chrome,"online-"+ids[i],acts[i],OnlineTeamsText82.T(keys[i]),x+i*(bw+6),sy+96,bw,48,!v.busy);RecoveryCaption(r.chrome,"online-"+ids[i]);}}
            }
            if(!v.keyboard110)MainNavigationLayout.AddDock(r.chrome,w,h,3);
            if(v.modal=="mail-detail111")HeartOfTheRain.App.TeamsMail.TeamsMailLayout111.Detail(r,v);
            else if(!string.IsNullOrEmpty(v.modal)&&v.modal!="compose110")r.overlay=OnlineTeamsLayout82.BuildLegacy(w,h,v).overlay;
            NavigationDiagnostics124.Shared.Record(NavigationEvent124.TeamsChatFooter,(int)Math.Round((System.Diagnostics.Stopwatch.GetTimestamp()-next)*1000.0/System.Diagnostics.Stopwatch.Frequency));
            return r;
        }
        public static void AddRecoveryEntry(OnlineTeamsFrame82 frame,OnlineTeamsView82 view)
        {
            bool lives=view.ownedLives110?.requests?.Any(value=>value.remaining>0)==true,mail=view.ownedMail111?.rewards?.Length>0;if(!lives&&!mail)return;
            int count=(lives?1:0)+(mail?1:0);foreach(var element in frame.content.elements)if(string.IsNullOrEmpty(element.parent))element.y+=60*count;
            float width=Math.Min(320,frame.width-40),x=(frame.width-width)/2,y=4;if(mail){Button(frame.content,"online-mail-owned","mail-owned",HeartOfTheRain.App.TeamsMail.TeamsMailText111.T("saved_rewards"),x,y,width,48,!view.busy&&!view.pending);y+=60;}if(lives)Button(frame.content,"online-saved-lives","saved-lives",T("saved_lives"),x,y,width,48,!view.busy&&!view.pending);frame.content.height+=60*count;
        }
    }
}

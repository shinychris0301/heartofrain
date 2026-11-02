using System;
using System.Globalization;
using System.Linq;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.TeamsSocial;
using UnityEngine;
namespace HeartOfTheRain.App.TeamsMail {
 public static class TeamsMailLayout111 {
  static string T(string key)=>TeamsMailText111.T(key);
  static HomeElement Add(HomeFrame f,string id,string kind,float x,float y,float w,float h,string parent="") { var e=new HomeElement{id=id,kind=kind,x=x,y=y,width=w,height=h,parent=parent};f.elements.Add(e);return e; }
  static void Art(HomeFrame f,string id,string asset,float x,float y,float w,float h,bool slice=true,string parent="") {var e=Add(f,id,"sprite",x,y,w,h,parent);e.asset=asset;e.sliced=slice;e.preserveAspect=!slice;e.color="#FFFFFF";}
  static void Text(HomeFrame f,string id,string value,float x,float y,float w,float h,int size=14,string color="#3B5D77",string kind="text",string parent="") {var e=Add(f,id,kind,x,y,w,h,parent);e.text=value??"";e.fontSize=size;e.color=color;}
  static void Button(HomeFrame f,string id,string action,string text,float x,float y,float w,float h,bool enabled=true,string tone="Blue") {Art(f,id+"-art",enabled?"TA_Button_"+tone:"TA_Button_Disabled",x,y,w,h);Text(f,id+"-label",text,x+8,y+4,w-16,h-8,14,enabled?"#FFFFFF":"#617F90");var e=Add(f,id,"group",x,y,w,h);e.action=enabled?action:"disabled";e.label=text;}
  static string When(long utc){try{return DateTimeOffset.FromUnixTimeSeconds(utc).ToLocalTime().ToString("g",CultureInfo.GetCultureInfo(new[]{"en-US","es-ES","fr-FR","de-DE","ru-RU"}[HeartOfTheRain.App.Localization.GameLocale.Current]));}catch(Exception){return "";}}
  static float Height(string value,float width,int size,Font font,float canvasScale){value=TeamsSocialLayout110.DisplayText110(value,font);if(!font)return Math.Max(size+8,(value??"").Length/Math.Max(1,(int)(width/(size*.6f))+1)*(size+7));float ppu=font.dynamic?Math.Max(.1f,canvasScale):(font.fontSize<=0||font.fontSize==size?1:font.fontSize/(float)size);var settings=new TextGenerationSettings{font=font,fontSize=size,scaleFactor=ppu,lineSpacing=1,richText=false,fontStyle=FontStyle.Normal,horizontalOverflow=HorizontalWrapMode.Wrap,verticalOverflow=VerticalWrapMode.Overflow,generationExtents=new Vector2(width,20000),textAnchor=TextAnchor.UpperLeft};return Math.Max(size+8,Mathf.Ceil(new TextGenerator().GetPreferredHeight(value??"",settings)/ppu)+8);}
  static string Preview(string body,float width,Font font,float canvasScale){
   if(string.IsNullOrEmpty(body))return "";string value=body.Replace("\n"," ").Trim();if(!font)return value.Length<=80?value:value.Substring(0,Math.Min(80,value.Length))+"?";
   float ppu=font.dynamic?Math.Max(.1f,canvasScale):(font.fontSize<=0||font.fontSize==13?1:font.fontSize/13f);var settings=new TextGenerationSettings{font=font,fontSize=13,scaleFactor=ppu,lineSpacing=1,richText=false,fontStyle=FontStyle.Normal,horizontalOverflow=HorizontalWrapMode.Wrap,verticalOverflow=VerticalWrapMode.Overflow,generationExtents=new Vector2(width,10000),textAnchor=TextAnchor.UpperLeft};var gen=new TextGenerator();
   if(gen.GetPreferredHeight(TeamsSocialLayout110.DisplayText110(value,font),settings)/ppu<=38)return value;
   int[] elements=StringInfo.ParseCombiningCharacters(value);int lo=0,hi=elements.Length;while(lo<hi){int mid=(lo+hi+1)/2;int end=mid==elements.Length?value.Length:elements[mid];string candidate=value.Substring(0,end).TrimEnd()+"?";if(gen.GetPreferredHeight(TeamsSocialLayout110.DisplayText110(candidate,font),settings)/ppu<=38)lo=mid;else hi=mid-1;}int cut=lo==elements.Length?value.Length:elements[lo];return value.Substring(0,cut).TrimEnd()+"?";
  }
  public static void Content(OnlineTeamsFrame82 r,OnlineTeamsView82 v,float x,ref float y,float width) {
   bool online=v.connected&&!v.busy&&!v.pending&&!v.mailOffline111;var list=v.mailList111;
   if(v.mailOffline111||!string.IsNullOrEmpty(v.mailStatus111)){Text(r.content,"mail-status",v.mailStatus111,x+4,y,width-8,48,14,"#E7F6FC");y+=55;}
   if(list==null){Text(r.content,"mail-load",T(v.mailStatus111.Length==0?"loading":"load_error"),x+10,y+18,width-20,50,17,"#E7F6FC");Button(r.content,"mail-refresh","mail-refresh",T("retry"),x+width/2-70,y+78,140,48,!v.busy);y+=140;return;}
   Text(r.content,"mail-unread",TeamsMailText111.Count(list.unreadCount),x+8,y,width-90,35,14,"#D9EBF6","lefttext");Button(r.content,"mail-refresh","mail-refresh",T("refresh"),x+width-84,y,84,48,!v.busy);y+=56;
   if(v.mailHasBack111){Button(r.content,"mail-latest","mail-latest",T("refresh"),x,y,width,48,!v.busy);y+=58;}
   if(list.messages.Length==0){Art(r.content,"mail-empty-letter","TM_Letter_Open",x+width/2-43,y+18,86,86,false);Text(r.content,"mail-empty-title",T("no_mail"),x+10,y+111,width-20,36,20,"#FFFFFF");Text(r.content,"mail-empty-body",T("empty_note"),x+12,y+150,width-24,55,14,"#D9EBF6");y+=220;return;}
   foreach(var mail in list.messages){string id="mail-row-"+mail.messageId;bool hasReward=mail.rewardCoins>0||mail.rewardLives>0;string title=hasReward?T("team_reward"):mail.title;float hh=hasReward?174:120;Art(r.content,id+"-base","TA_Panel_Cream",x,y,width,hh);Art(r.content,id+"-letter",mail.readAtUtc==0?"TM_Letter_Closed":"TM_Letter_Open",x+6,y+18,70,70,false);Text(r.content,id+"-title",title,x+82,y+11,width-94,25,16,"#073354","chatname110");Text(r.content,id+"-preview",Preview(mail.body,width-94,v.font110,v.mailFontScale111),x+82,y+38,width-94,38,13,"#3B5D77","chatbody110");Text(r.content,id+"-read",T(mail.readAtUtc==0?"unread":"read"),x+82,y+80,90,22,11,"#527487","lefttext");Text(r.content,id+"-time",When(mail.sentAtUtc),x+175,y+80,width-187,22,10,"#688CA5");if(hasReward){if(mail.rewardCoins>0){Art(r.content,id+"-coin","TM_Coin",x+82,y+109,26,26,false);Text(r.content,id+"-coins",mail.rewardCoins.ToString("N0"),x+112,y+106,82,30,12,"#073354","lefttext");}if(mail.rewardLives>0){Art(r.content,id+"-heart","TA_Stat_heart",x+202,y+109,26,26,false);Text(r.content,id+"-lives",mail.rewardLives.ToString(),x+232,y+106,30,30,12,"#073354","lefttext");}string rewardStatus=mail.claimState=="Claimed"?T("reward_collected"):mail.claimState=="Expired"?T("reward_expired"):mail.claimState=="CapacityBlocked"?T("lives_full"):T("reward_status_ready");Text(r.content,id+"-reward-status",rewardStatus,x+78,y+135,width-90,17,10,"#527487");}var hit=Add(r.content,id,"group",x,y,width,hh);hit.action="mail-open:"+mail.messageId;hit.label=T("open_message")+": "+title;y+=hh+10;}
   if(list.hasOlder){Button(r.content,"mail-older","mail-older",HeartOfTheRain.App.OnlineSocial.OnlineTeamsText82.T("More"),x,y,width,48,online);y+=58;}
  }
  public static OnlineTeamsFrame82 BuildOwned(float width,float height,OnlineTeamsView82 v){
   float w=Math.Max(320,width),h=Math.Max(260,height),cw=Math.Min(520,w-28),x=(w-cw)/2,dh=MainNavigationLayout.ReservedHeight(w,h);var r=new OnlineTeamsFrame82{width=w,height=h,artScale=cw/1000};r.chrome.width=r.overlay.width=w;r.chrome.height=r.overlay.height=h;r.content.width=w;
   var bg=Add(r.chrome,"online-teams-background","cover109",0,0,w,h);bg.asset="TA_Background";Text(r.chrome,"mail-owned-title",T("saved_rewards"),x,12,cw-100,42,21,"#FFFFFF");Button(r.chrome,"mail-owned-close","mail-owned-close",T("close"),x+cw-96,12,96,48,true);
   Add(r.chrome,"mail-owned-feedback-anchor","group",x+cw/2-24,60,48,48);
   float status=v.pending?150:string.IsNullOrEmpty(v.mailStatus111)?0:60;r.viewportY=75;r.viewportHeight=Math.Max(40,h-dh-status-r.viewportY-8);float y=4;
   var data=v.ownedMail111;if(v.ownedMailHasBack111){Button(r.content,"mail-owned-latest","mail-owned-latest",T("refresh"),x,y,cw,48,!v.busy&&!v.pending);y+=58;}
   if(data==null){Text(r.content,"mail-owned-loading",T("loading"),x,y,cw,54,16,"#FFFFFF");y+=65;}
   else if(data.rewards.Length==0){Text(r.content,"mail-owned-empty",T("no_mail"),x,y+20,cw,54,16,"#FFFFFF");y+=84;}
   else foreach(var reward in data.rewards){string id="mail-owned-"+reward.messageId;float card=138;Art(r.content,id+"-base","TA_Panel_Cream",x,y,cw,card);Art(r.content,id+"-letter","TM_Letter_Closed",x+8,y+15,62,62,false);Text(r.content,id+"-title",T("reward_details"),x+76,y+10,cw-88,28,16,"#073354","lefttext");if(reward.rewardCoins>0){Art(r.content,id+"-coin","TM_Coin",x+78,y+48,32,32,false);Text(r.content,id+"-coins",reward.rewardCoins.ToString("N0"),x+115,y+48,82,30,13,"#073354","lefttext");}if(reward.rewardLives>0){Art(r.content,id+"-heart","TA_Stat_heart",x+205,y+48,32,32,false);Text(r.content,id+"-lives",reward.rewardLives.ToString(),x+240,y+48,35,30,13,"#073354","lefttext");}string caption=reward.canClaim?T("collect"):reward.claimBlockedReason=="FullLives"?T("lives_full"):T("load_error");Button(r.content,id+"-action","mail-owned-claim:"+reward.messageId,caption,x+cw-130,y+83,120,48,reward.canClaim&&v.ownedMailReady111&&!v.busy&&!v.pending,"Green");y+=card+10;}
   if(data?.hasMore==true){Button(r.content,"mail-owned-more","mail-owned-more",OnlineTeamsText82.T("More"),x,y,cw,48,!v.busy&&!v.pending);y+=58;}r.content.height=Math.Max(r.viewportHeight,y+8);
   if(status>0){float sy=h-dh-status;Text(r.chrome,"mail-owned-status",v.pending?OnlineTeamsText82.T("Pending")+(string.IsNullOrEmpty(v.mailStatus111)?"":"\n"+v.mailStatus111):v.mailStatus111,x+4,sy+4,cw-8,v.pending?75:46,12,"#E7F6FC");if(v.pending){float part=(cw-12)/3;Button(r.chrome,"mail-owned-check","check-pending",OnlineTeamsText82.T("Check"),x,sy+92,part,48,!v.busy);Button(r.chrome,"mail-owned-retry","resume-pending",T("retry"),x+part+6,sy+92,part,48,!v.busy);Button(r.chrome,"mail-owned-forget","forget",OnlineTeamsText82.T("Forget"),x+2*(part+6),sy+92,part,48,!v.busy);}}
   MainNavigationLayout.AddDock(r.chrome,w,h,3);if(!string.IsNullOrEmpty(v.modal))r.overlay=OnlineTeamsLayout82.BuildLegacy(w,h,v).overlay;return r;
  }
  public static void Detail(OnlineTeamsFrame82 r,OnlineTeamsView82 v){
   var mail=v.mailDetail111;bool reward=mail!=null&&(mail.rewardCoins>0||mail.rewardLives>0);
   var f=r.overlay;float w=r.width,h=r.height,cw=reward?Math.Min(330,w*.82f):Math.Min(420,w-28),x=(w-cw)/2,mh=reward?Math.Min(406,h*.64f):Math.Min(540,h-28),top=(h-mh)/2+(reward?14:0);var shade=Add(f,"online-modal-shade","color",0,0,w,h);shade.color="#000000B8";
   Art(f,"mail-detail-frame","TA_Panel_Blue",x,top,cw,mh);
   // Keep the letter above the panel and the close disc at its right edge,
   // matching the R3 proof. The transparent sprite bounds are larger than
   // their painted content, so the source rect deliberately protrudes.
   Art(f,"mail-detail-crest","TM_Letter_Closed",x+cw/2-38,top-39,76,76,false);
   float closeX=x+cw-32;
   Art(f,"mail-close-art","TA_Close_Disc",closeX,top-9,48,48,false);
   Art(f,"mail-close-icon","TA_Icon_Close",closeX+12,top+3,24,24,false);
   var close=Add(f,"mail-close","group",Math.Min(x+cw-48,w-80),top-9,80,48);close.action="mail-close";close.label=T("close");
   Text(f,"mail-detail-title",reward?T("team_reward"):mail?.title??T("loading"),x+18,top+(reward?62:68),cw-36,54,20,"#FFFFFF");
   float bx=x+13,by=top+(reward?116:126),bw=cw-26,bh=Math.Max(50,mh-(reward?200:198)-(v.pending?40:0));Art(f,"mail-detail-inner","TA_Panel_Cream",bx,by,bw,bh);
   float innerW=bw-24;var view=Add(f,"mail-detail-scroll","mailbody111",bx+10,by+10,bw-20,bh-20);view.label="mail-detail-scroll-content";
   float y=8;string sender=reward||string.IsNullOrEmpty(mail?.senderLabel)?"":T("sender").Replace("{name}",mail.senderLabel);float senderHeight=sender.Length==0?0:Height(sender,innerW-10,13,v.font110,v.mailFontScale111);float bodyHeight=Height(mail?.body,innerW-10,15,v.font110,v.mailFontScale111);float card=reward?80:0;string state=mail==null?"":mail.claimState=="Expired"?T("expired_note"):mail.claimState=="CapacityBlocked"?T("full_note"):mail.claimState=="Claimed"?T("collected_note"):mail.claimBlockedReason!="None"?T("load_error"):v.mailOffline111?T("connect_claim"):"";if(mail!=null&&mail.expiresAtUtc>0&&mail.claimState!="Claimed"&&mail.claimState!="Expired"&&v.now110>0){string until=T("expiry_short").Replace("{time}",TeamsSocialLayout110.Countdown(Math.Max(0,mail.expiresAtUtc-v.now110)));state=state.Length==0?until:state+"\n"+until;}float stateHeight=state.Length==0?0:Height(state,innerW-10,13,v.font110,v.mailFontScale111);
   var content=Add(f,"mail-detail-scroll-content","group",0,0,bw-20,Math.Max(bh-20,y+senderHeight+bodyHeight+card+stateHeight+26),"mail-detail-scroll");
   if(senderHeight>0){Text(f,"mail-detail-sender",sender,6,y,innerW-10,senderHeight,13,"#527487","chatbody110",content.id);y+=senderHeight;}
   Text(f,"mail-detail-body",mail?.body??"",6,y,innerW-10,bodyHeight,15,"#21465E","chatbody110",content.id);y+=bodyHeight+8;
   if(card>0){
    float cardW=Math.Min(100,innerW*.38f),gap=20;int count=(mail.rewardCoins>0?1:0)+(mail.rewardLives>0?1:0);float tileX=6+(innerW-count*cardW-(count-1)*gap)/2;
    if(mail.rewardCoins>0){Art(f,"mail-detail-coin-card","TA_Field",tileX,y,cardW,78,true,content.id);Art(f,"mail-detail-coin","TM_Coin",tileX+(cardW-37)/2,y+3,37,37,false,content.id);Text(f,"mail-detail-coins",mail.rewardCoins.ToString("N0"),tileX+4,y+37,cardW-8,20,15,"#073354","text",content.id);Text(f,"mail-detail-coins-label",T("coins"),tileX+4,y+50,cardW-8,17,11,"#527487","text",content.id);tileX+=cardW+gap;}
    if(mail.rewardLives>0){Art(f,"mail-detail-life-card","TA_Field",tileX,y,cardW,78,true,content.id);Art(f,"mail-detail-heart","TA_Stat_heart",tileX+(cardW-37)/2,y+3,37,37,false,content.id);Text(f,"mail-detail-lives",mail.rewardLives.ToString(),tileX+4,y+37,cardW-8,20,15,"#073354","text",content.id);Text(f,"mail-detail-lives-label",T("lives"),tileX+4,y+50,cardW-8,17,11,"#527487","text",content.id);}y+=card;
   }
   if(stateHeight>0)Text(f,"mail-detail-state",state,6,y,innerW-10,stateHeight,13,"#527487","chatbody110",content.id);
   bool pending=v.pending;if(pending)Text(f,"mail-detail-pending-notice",string.IsNullOrEmpty(v.mailStatus111)?T("claim_pending_note"):v.mailStatus111,x+16,top+mh-108,cw-32,38,12,"#FFFFFF");bool claim=mail!=null&&(mail.rewardCoins>0||mail.rewardLives>0)&&mail.claimState!="Claimed"&&mail.claimState!="Expired";string label=claim?T("collect"):T("done");if(pending){float part=(cw-38)/2;Button(f,"mail-detail-check","mail-check",HeartOfTheRain.App.OnlineSocial.OnlineTeamsText82.T("Check"),x+13,top+mh-64,part,48,!v.busy);Button(f,"mail-detail-retry","mail-retry",T("retry"),x+25+part,top+mh-64,part,48,!v.busy);}else Button(f,"mail-detail-action",claim?"mail-claim":"mail-close",label,x+cw/2-88,top+mh-64,176,48,!claim||mail.canClaim&&v.mailReady111&&!v.mailOffline111,claim?"Green":"Blue");
  }
 }
}

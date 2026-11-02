using System;
using System.Globalization;
using System.Linq;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.TeamsAccess;

namespace HeartOfTheRain.App.OnlineSocial {
 // Reusable R3 ranking cards shared by Players, My region and Teams. Data comes
 // only from the authenticated ranking snapshot; the Editor proof is explicit.
 public static class LeaderboardR3Layout118 {
  static string T(string key)=>OnlinePlayersText82.T(key);
  static string N(long n)=>n.ToString("N0",CultureInfo.GetCultureInfo(new[]{"en-US","es-ES","fr-FR","de-DE","ru-RU"}[GameLocale.ResolveStored(GameLocale.Current)]));
  static string Word(string en,string es,string fr,string de,string ru)=>new[]{en,es,fr,de,ru}[GameLocale.ResolveStored(GameLocale.Current)];
  static string Title=>Word("Rankings","Clasificación","Classements","Ranglisten","Рейтинг");
  static string Best=>Word("Top players","Mejores jugadores","Meilleurs joueurs","Beste Spieler","Лучшие игроки");
  static string BestTeams=>Word("Top teams","Mejores equipos","Meilleures équipes","Beste Teams","Лучшие команды");
  static string YourPlace=>Word("Your place","Tu puesto","Votre place","Dein Platz","Ваше место");
  static string YourTeam=>Word("Your team","Tu equipo","Votre équipe","Dein Team","Ваша команда");
  static string LevelLabel=>Word("Level","Nivel","Niveau","Level","Уровень");
  static string ScoreLabel=>Word("Points","Puntos","Points","Punkte","Очки");
  static string Unranked=>Word("Unranked","Sin clasificar","Non classé","Nicht platziert","Нет места");
  static string Privacy=>Word("Ranking privacy","Privacidad del ranking","Confidentialité du classement","Ranglisten Datenschutz","Видимость результата");
  static HomeElement Add(HomeFrame f,string id,string kind,float x,float y,float w,float h,string parent="") {var e=new HomeElement{id=id,kind=kind,x=x,y=y,width=w,height=h,parent=parent};f.elements.Add(e);return e;}
  static void Art(HomeFrame f,string id,string asset,float x,float y,float w,float h,bool sliced=true,string parent="") {var e=Add(f,id,"sprite",x,y,w,h,parent);e.asset=asset;e.sliced=sliced;e.preserveAspect=!sliced;e.color="#FFFFFF";}
  static void Label(HomeFrame f,string id,string value,float x,float y,float w,float h,int size,string color="#073354",bool left=false) {var e=Add(f,id,left?"ranknameleft115":"rankname115",x,y,w,h);e.text=value??"";e.fontSize=size;e.color=color;}
  static void Text(HomeFrame f,string id,string value,float x,float y,float w,float h,int size,string color="#073354",bool left=false) {var e=Add(f,id,left?"lefttext":"text",x,y,w,h);e.text=value??"";e.fontSize=size;e.color=color;}
  static void Hit(HomeFrame f,string id,string action,string label,float x,float y,float w,float h,bool enabled) {var e=Add(f,id,"group",x,y,w,h);e.action=enabled?action:"disabled";e.label=label;}
  static void Button(HomeFrame f,string id,string action,string label,float x,float y,float w,float h,bool enabled) {Art(f,id+"-art",enabled?"TA_Button_Blue":"TA_Button_Disabled",x,y,w,h);Text(f,id+"-label",label,x+7,y+5,w-14,h-10,14,enabled?"#FFFFFF":"#617F90");Hit(f,id,action,label,x,y,w,h,enabled);}
  static void Tab(HomeFrame f,string id,string action,string label,float x,float y,float w,float h,bool selected,bool enabled) {if(selected)Art(f,id+"-selected","TA_Tab_Selected",x,y,w,h);Text(f,id+"-label",label,x+4,y+3,w-8,h-6,15,selected?"#FFFFFF":"#BDDFFF");float hitH=Math.Max(48,h);Hit(f,id,action,label,x,y-(hitH-h)/2,w,hitH,enabled);}
  static void Medal(HomeFrame f,string id,long rank,float x,float y,float size) {
   string asset=rank==1?"TA_Rank_Gold":rank==2?"TA_Rank_Silver":rank==3?"TA_Rank_Bronze":null;
   if(asset!=null){Art(f,id+"-medal",asset,x,y,size,size,false);Text(f,id+"-rank",N(rank),x+1,y+1,size-2,size*.66f,13,"#29435A");}
   else Text(f,id+"-rank",N(rank),x,y,size,size,15,"#537187");
  }
  static bool PlayerMatches(OnlinePlayersView82 v)=>v.ranks115!=null&&v.ranks115.entries!=null&&v.ranks115.nextOffset-v.ranks115.entries.Length==v.offset&&v.ranks115.scope==(v.regional?"regional":"global")&&(!v.regional||v.ranks115.regionCode==v.regionCode);
  static bool TeamMatches(OnlinePlayersView82 v)=>v.teamRanks115!=null&&v.teamRanks115.entries!=null&&v.teamRanks115.nextOffset-v.teamRanks115.entries.Length==v.offset&&v.teamRanks115.scope==(v.regional?"regional":"global")&&(!v.regional||v.teamRanks115.regionCode==v.regionCode);
  static string ReviewPortrait(SocialRank82 player,OnlinePlayersView82 view) {
#if UNITY_EDITOR
   if(view.editorVisualFixture118&&player!=null){switch(player.displayName){case "Aurora":return "Portrait_Weaver_R2";case "Old Oak":return "Portrait_Scholar_R2";case "Riverlight":return "Portrait_Ivan_R2";case "Mira":return "TA_Badge_oak";case "Northstar":return "TA_Badge_crystal";}}
#endif
   return null;
  }
  static void Avatar(HomeFrame f,string id,bool self,bool selfAvailable,string portrait,float x,float y,float side) {
   Art(f,id+"-frame",self&&selfAvailable?"SELF_FRAME115":"TA_Button_Blue",x,y,side,side,!self||!selfAvailable);
   string art=self&&selfAvailable?"SELF_AVATAR115":portrait;
   if(art!=null){Art(f,id+"-mask","LB2_AvatarMask",x+3,y+3,side-6,side-6,false);f.elements[f.elements.Count-1].kind="mask";Art(f,id+"-portrait",art,0,0,side-6,side-6,false,id+"-mask");}
   else Art(f,id+"-neutral","TA_Icon_People",x+side*.25f,y+side*.25f,side*.5f,side*.5f,false);
  }
  static void PlayerCard(HomeFrame f,SocialRank82 p,OnlinePlayersView82 v,float x,float y,float w,float h,bool podium) {
   string id="online-rank-"+p.playerId;bool own=p.playerId==v.selfId,first=podium&&p.rank==1;
   Art(f,id+"-base",first?"TA_Panel_Blue":"TA_Panel_Cream",x,y,w,h);
   string ink=first?"#FFFFFF":"#073354",muted=first?"#D5ECF8":"#527487";
   if(podium){float s=Math.Min(58,w-15);Avatar(f,id+"-avatar",own,v.selfAvatarAvailable115,ReviewPortrait(p,v),x+(w-s)/2,y+8,s);Label(f,id+"-name",own?T("You"):p.displayName,x+8,y+68,w-16,20,14,ink);Text(f,id+"-score-label",LevelLabel,x+8,y+88,w-16,12,10,muted);Art(f,id+"-score-icon","TA_Stat_up",x+w*.5f-23,y+101,16,16,false);Text(f,id+"-score",N(p.score),x+w*.5f-3,y+100,38,18,13,ink);Medal(f,id,p.rank,x+(w-32)/2,y+h-15,32);}
   else {Medal(f,id,p.rank,x+5,y+14,28);Avatar(f,id+"-avatar",own,v.selfAvatarAvailable115,ReviewPortrait(p,v),x+37,y+6,45);Label(f,id+"-name",own?T("You"):p.displayName,x+91,y+6,w-170,25,15,ink,true);Art(f,id+"-metric-art","TA_Stat",x+w-65,y+7,60,43);Art(f,id+"-score-icon","TA_Stat_up",x+w-60,y+18,15,15,false);Text(f,id+"-score",N(p.score),x+w-44,y+9,37,35,14,"#073354");}
   Hit(f,id,"player:"+p.playerId,p.displayName,x,y,w,h,(!v.busy||v.rowsReady136)&&!v.pending);
  }
  static void TeamCard(HomeFrame f,SocialTeamRankRefresh115 p,OnlinePlayersView82 v,float x,float y,float w,float h,bool podium) {
   string id="online-team-rank-"+p.teamId;bool first=podium&&p.rank==1;
   Art(f,id+"-base",first?"TA_Panel_Blue":"TA_Panel_Cream",x,y,w,h);string ink=first?"#FFFFFF":"#073354";
   if(podium){float s=Math.Min(58,w-15);Art(f,id+"-badge",TeamsAccessBadges109.Asset(p.badgeId),x+(w-s)/2,y+8,s,s,false);Label(f,id+"-name",p.name,x+7,y+68,w-14,20,14,ink);Text(f,id+"-score-label",ScoreLabel,x+7,y+88,w-14,12,10,first?"#D5ECF8":"#527487");Art(f,id+"-star","TA_Stat_star",x+w*.5f-23,y+101,16,16,false);Text(f,id+"-score",N(p.score),x+w*.5f-2,y+100,46,18,13,ink);Medal(f,id,p.rank,x+(w-32)/2,y+h-15,32);}
   else {Medal(f,id,p.rank,x+5,y+14,28);Art(f,id+"-badge",TeamsAccessBadges109.Asset(p.badgeId),x+38,y+7,44,44,false);Label(f,id+"-name",p.name,x+91,y+7,w-170,24,15,ink,true);Art(f,id+"-member-icon","TA_Icon_People",x+92,y+31,13,13,false);f.elements[f.elements.Count-1].color="#527487";Text(f,id+"-members",N(p.memberCount),x+108,y+29,w-190,18,10,"#527487",true);Art(f,id+"-metric-art","TA_Stat",x+w-67,y+7,62,43);Art(f,id+"-star","TA_Stat_star",x+w-62,y+18,15,15,false);Text(f,id+"-score",N(p.score),x+w-43,y+9,35,35,14,"#073354");}
   Hit(f,id,"rank-team115:"+p.teamId,p.name,x,y,w,h,(!v.busy||v.rowsReady136)&&!v.pending);
  }
  static void Pin(HomeFrame f,OnlinePlayersView82 v,float x,float y,float w) {
   Art(f,"online-pin-base","TA_Panel_Blue",x,y,w,45);
   if(v.teamRanking){var row=v.teamRanks115.hasSelfEntry?v.teamRanks115.selfEntry:null;Text(f,"online-pin-rank",row==null?"—":N(row.rank),x+5,y+3,27,39,15,"#FFFFFF");if(row!=null)Art(f,"online-pin-badge",TeamsAccessBadges109.Asset(row.badgeId),x+37,y+1,43,43,false);Label(f,"online-pin-name",row==null?YourTeam:row.name,x+86,y+2,w-175,20,14,"#FFFFFF",true);Text(f,"online-pin-place",YourPlace,x+86,y+24,w-175,16,10,"#C7E4F3",true);Text(f,"online-pin-score",row==null?Unranked:N(row.score),x+w-82,y+4,76,38,14,"#FFFFFF");}
   else {var row=v.ranks115.hasSelfEntry?v.ranks115.selfEntry:null;Text(f,"online-pin-rank",row==null?"—":N(row.rank),x+5,y+3,27,39,15,"#FFFFFF");string proofPortrait=null;
#if UNITY_EDITOR
    if(v.editorVisualFixture118)proofPortrait="Portrait_Ivan_R2";
#endif
    Avatar(f,"online-pin-avatar",true,v.selfAvatarAvailable115,proofPortrait,x+37,y+1,43);Label(f,"online-pin-name",T("You"),x+86,y+2,w-175,20,14,"#FFFFFF",true);Text(f,"online-pin-place",YourPlace,x+86,y+24,w-175,16,10,"#C7E4F3",true);Art(f,"online-pin-score-icon","TA_Stat_up",x+w-56,y+13,16,16,false);Text(f,"online-pin-score",row==null?Unranked:N(row.score),x+w-38,y+4,34,38,14,"#FFFFFF");}
  }
  public static OnlineTeamsFrame82 Build(float width,float height,OnlinePlayersView82 v,float topInset=0) {
   var r=new OnlineTeamsFrame82{width=Math.Max(320,width),height=Math.Max(540,height),r3SliceScale118=true};
   float w=r.width,h=r.height,cw=Math.Min(w-28,520),x=(w-cw)/2,bodyW=Math.Min(w-28,540),bodyX=(w-bodyW)/2,dh=MainNavigationLayout.ReservedHeight(w,h);r.artScale=cw/1000;
   float headerShift=Math.Max(0,Math.Min(28,topInset));
   foreach(var f in new[]{r.chrome,r.overlay}){f.width=w;f.height=h;}r.content.width=w;
   Art(r.chrome,"online-players-background","TA_Background",0,0,w,h,false);r.chrome.elements[r.chrome.elements.Count-1].preserveAspect=false;
   Text(r.chrome,"online-players-title",Title,x+20,18-Math.Min(18,headerShift),cw-40,45,25,"#FFFFFF");
   float tabsY=74-headerShift,third=cw/3;bool enabled=!v.writing&&!v.pending;
   Art(r.chrome,"online-tabs","TA_Tab_Track",x,tabsY,cw,44);
   // The selected Friends tab doubles as the search return control, as in R3.
   Tab(r.chrome,"online-primary-friends",v.tab==1&&v.searchOpen115?"search-back115":"primary-friends115",T("Friends"),x,tabsY,third,44,v.tab!=0,enabled);
   Tab(r.chrome,"online-primary-players","primary-players115",T("Players"),x+third,tabsY,third,44,v.tab==0&&!v.teamRanking,enabled);
   Tab(r.chrome,"online-primary-teams","primary-teams115",CountryRegion89.T("Teams"),x+2*third,tabsY,third,44,v.tab==0&&v.teamRanking,enabled);
   float status=v.pending?106:string.IsNullOrEmpty(v.status)?0:70;
   bool showPin=v.tab==0&&(v.teamRanking?TeamMatches(v)&&v.teamRanks115.hasTeam:PlayerMatches(v));
   float pin=showPin?49:0;
   if(v.tab==0){
    bool haveRegion=!string.IsNullOrEmpty(v.regionCode);float sw=Math.Min(220,cw-40),sx=(w-sw)/2,half=haveRegion?sw/2:sw;
    Art(r.chrome,"online-scopes","TA_Tab_Track",sx,119-headerShift,sw,36);
    Tab(r.chrome,"online-scope-global","scope-global",CountryRegion89.T("Global"),sx,119-headerShift,half,36,!v.regional,enabled);
    if(haveRegion)Tab(r.chrome,"online-scope-regional","scope-regional",CountryRegion89.T("Regional"),sx+half,119-headerShift,half,36,v.regional,enabled);
    r.viewportY=174-headerShift;
    Text(r.content,v.teamRanking?"online-team-score-note":"online-player-score-note",v.teamRanking?BestTeams:Best,x+2,0,cw-67,21,11,"#FFFFFF",true);
    if(!v.teamRanking){Art(r.chrome,"online-privacy118-art","TC_Icon_More",x+cw-39,168-headerShift,24,24,false);Hit(r.chrome,"online-privacy118","privacy-open118",Privacy,x+cw-49,156-headerShift,49,48,enabled);}
    float stretch=Math.Max(0,Math.Min(1,(h-640)/204));float y=22;float gap=8,cell=(bodyW-2*gap)/3,featuredH=139+26*stretch,otherH=133+23*stretch,rowHeight=56+6*stretch,rowStep=62+7*stretch,afterFeatured=155+28*stretch;
    if(v.offset>0){Button(r.content,"online-ranks-first","ranks-first115",T("Back"),x,y,cw,48,enabled);y+=55;}
    if(v.teamRanking){
     var rows=TeamMatches(v)?v.teamRanks115.entries:new SocialTeamRankRefresh115[0];int featured=v.offset==0?Math.Min(3,rows.TakeWhile(p=>p.rank<=3).Count()):0;
     for(int i=0;i<featured;i++){int slot=i==0?1:i==1?0:2;TeamCard(r.content,rows[i],v,bodyX+slot*(cell+gap)-(slot==1?7:0),y+(slot==1?-12:7),cell+(slot==1?14:0),slot==1?featuredH:otherH,true);}
     if(featured>0)y+=afterFeatured;
     for(int i=featured;i<rows.Length;i++){TeamCard(r.content,rows[i],v,bodyX,y,bodyW,rowHeight,false);y+=rowStep;}
     if(TeamMatches(v)&&rows.Length==0){Text(r.content,"online-ranks-empty",CountryRegion89.T("EmptyTeams"),x+8,y+8,cw-16,66,14,"#E7F6FC");y+=74;}
     if(TeamMatches(v)&&v.teamRanks115.hasMore){Button(r.content,"online-ranks-more","more-ranks",T("More"),x,y,cw,48,enabled);y+=55;}
    }else{
     var rows=PlayerMatches(v)?v.ranks115.entries:new SocialRank82[0];int featured=v.offset==0?Math.Min(3,rows.TakeWhile(p=>p.rank<=3).Count()):0;
     for(int i=0;i<featured;i++){int slot=i==0?1:i==1?0:2;PlayerCard(r.content,rows[i],v,bodyX+slot*(cell+gap)-(slot==1?7:0),y+(slot==1?-12:7),cell+(slot==1?14:0),slot==1?featuredH:otherH,true);}
     if(featured>0)y+=afterFeatured;
     for(int i=featured;i<rows.Length;i++){PlayerCard(r.content,rows[i],v,bodyX,y,bodyW,rowHeight,false);y+=rowStep;}
     if(PlayerMatches(v)&&rows.Length==0){Text(r.content,"online-ranks-empty",T("EmptyRanks"),x+8,y+8,cw-16,66,14,"#E7F6FC");y+=74;}
     if(PlayerMatches(v)&&v.ranks115.hasMore){Button(r.content,"online-ranks-more","more-ranks",T("More"),x,y,cw,48,enabled);y+=55;}
    }
    r.content.height=Math.Max(1,y+8);
   }else{
    r.viewportY=123-headerShift;
    float y=0;
    y=FriendsParity118.Populate(r,v,x,cw,y,enabled);
    r.content.height=Math.Max(1,y+8);
    if(v.tab==1&&!v.searchOpen115){Art(r.chrome,"online-friends-secondary118-art","TC_Icon_More",x+cw-39,20-Math.Min(20,headerShift),24,24,false);Hit(r.chrome,"online-friends-secondary118","friends-secondary118",T("Requests"),x+cw-49,9-Math.Min(9,headerShift),49,49,enabled);}
   }
   if(showPin&&h-dh-status-r.viewportY<228){showPin=false;pin=0;}
   float bottom=h-dh-status-pin-4;r.viewportHeight=Math.Max(40,bottom-r.viewportY);
   if(showPin)Pin(r.chrome,v,bodyX,h-dh-status-45,bodyW);
   if(status>0){float sy=h-dh-status;Text(r.chrome,"online-players-status",v.pending?T("Pending"):v.status,x+2,sy+1,cw-4,v.pending?37:24,11,"#E0EFF8");if(v.pending){float bw=(cw-12)/3;Button(r.chrome,"online-players-check","check",T("Check"),x,sy+48,bw,48,!v.busy);Button(r.chrome,"online-players-resume","resume",T("Retry"),x+bw+6,sy+48,bw,48,!v.busy);Button(r.chrome,"online-players-forget","forget",T("Forget"),x+2*(bw+6),sy+48,bw,48,!v.busy);}else Button(r.chrome,"online-players-retry","retry",T("Retry"),x,sy+22,cw,48,!v.busy);}
   MainNavigationLayout.AddDock(r.chrome,w,h,1);
   if(v.tab==0&&!v.teamRanking&&v.privacyMenuOpen118){
    float pw=Math.Min(206,cw-12),px=x+cw-pw,py=194-headerShift;
    Art(r.overlay,"online-privacy-menu118","TA_Panel_Cream",px,py,pw,105);
    Label(r.overlay,"online-privacy-title118",Privacy,px+12,py+7,pw-68,33,13,"#073354",true);
    Hit(r.overlay,"online-privacy-close118","privacy-close118",T("Cancel"),px+pw-49,py+4,48,48,true);
    Text(r.overlay,"online-privacy-close-glyph118","×",px+pw-49,py+4,48,48,25);
    Button(r.overlay,"online-ranking-consent","consent",T(v.ownOptIn?"HideRanking":"ShowRanking"),px+10,py+49,pw-20,48,enabled&&v.ownProfileLoaded);
   }
   if(!string.IsNullOrEmpty(v.modal))LeaderboardRefresh115.ThemeModal(r,v);
   return r;
  }
 }
}

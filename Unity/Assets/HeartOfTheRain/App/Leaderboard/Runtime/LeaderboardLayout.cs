using HeartOfTheRain.App.Localization;
using System;using System.Linq;using System.Globalization;using HeartOfTheRain.App.Home;
namespace HeartOfTheRain.App.Leaderboard
{
 [Serializable] public sealed class LeaderboardFrame {public float width,height,viewportY,viewportHeight;public HomeFrame chrome=new HomeFrame(),content=new HomeFrame(),overlay=new HomeFrame();}
 public static class LeaderboardLayout
 {
  static HomeElement Add(HomeFrame f,string id,string kind,float x,float y,float w,float h,string parent=""){var e=new HomeElement{id=id,kind=kind,parent=parent,x=x,y=y,width=w,height=h};f.elements.Add(e);return e;}
  static void Group(HomeFrame f,string id,float x,float y,float w,float h,string parent=""){Add(f,id,"group",x,y,w,h,parent);}
  static void Art(HomeFrame f,string id,string asset,float x,float y,float w,float h,string parent="",bool slice=false,bool aspect=false,string color="#FFFFFF",string kind="sprite"){var e=Add(f,id,kind,x,y,w,h,parent);e.asset=asset;e.sliced=slice;e.preserveAspect=aspect;e.color=color;}
  static void Text(HomeFrame f,string id,string text,float x,float y,float w,float h,int size,string parent="",string color="#FFFFFF",bool left=false,bool shadow=false){var e=Add(f,id,left?"lefttext":"text",x,y,w,h,parent);e.text=GameLocale.Element(id,text);e.fontSize=size;e.color=color;e.shadow=shadow;}
  static void Sub(HomeFrame f,string id,string text,float x,float y,float w,float h,int size,string parent="",string color="#607C8C",bool left=true){var e=Add(f,id,left?"leftsubtext":"subtext",x,y,w,h,parent);e.text=GameLocale.Element(id,text);e.fontSize=size;e.color=color;}
  static void Avatar(HomeFrame f,string id,string art,float x,float y,float size,string parent)
  {Art(f,id+"-plate","LB2_AvatarPlate",x-2,y-2,size+4,size+4,parent,false,true);Art(f,id+"-mask","LB2_AvatarMask",x,y,size,size,parent,false,false,"#FFFFFF","mask");Art(f,id+"-portrait",art,0,0,size,size,id+"-mask",false,false,"#FFFFFF","cover");}
  static void Hit(HomeFrame f,string id,string action,float x,float y,float w,float h,string label,string parent=""){var e=Add(f,id,"group",x,y,w,h,parent);e.action=action;e.label=GameLocale.T(label);}
  static void Button(HomeFrame f,string id,string action,string label,float x,float y,float w,float h,bool active=false,string parent="")
  {
   bool main=id.StartsWith("tab-",StringComparison.Ordinal),confirm=id.StartsWith("confirm-",StringComparison.Ordinal);
   string art=confirm?(active?"LB2_Danger":"LB2_ButtonNeutral"):active?(main?"LB2_TabActive":"LB2_FilterActive"):"LB2_Empty";
   Art(f,id+"-art",art,x,y,w,h,parent,art!="LB2_Empty");Text(f,id+"-text",label,x+7,y+6,w-14,h-14,main||confirm?17:14,parent,confirm?(active?"#FFFFFF":"#264F68"):active&&!main?"#244D66":"#EDF7FD");Hit(f,id,action,x,y,w,h,label,parent);
  }
  static void IconButton(HomeFrame f,string id,string action,string asset,float x,float y,string label,string parent="")
  {Art(f,id+"-art",asset,x,y,44,44,parent,false,true);Hit(f,id,action,x,y,44,44,label,parent);}
  static void Dock(LeaderboardFrame r,float dh)
  {float dw=Math.Min(r.width,620);MainNavigationLayout.Add(r.chrome,(r.width-dw)/2,r.height-dh,dw,dh,1);}
  static void Rank(HomeFrame f,string id,int rank,float x,float y,string parent,bool dark=false)
  {
   if(rank<=3&&rank>0)Art(f,id+"-medal","LB2_Medal"+rank,x,y,30,33,parent,false,true);
   Text(f,id+"-rank",rank>0?rank.ToString(CultureInfo.InvariantCulture):"–",x,y+2,30,25,17,parent,rank==1?"#805820":rank==3?"#85533F":"#49677D");
  }
  static void PlayerRow(HomeFrame f,RankedPlayer p,int rank,float x,float y,float w,bool pinned=false)
  {
   float h=pinned?54:88;string id=(pinned?"self":"player-"+p.id);Group(f,id,x,y,w,h);
   if(pinned){Art(f,id+"-base","LB2_RowSelf",0,0,w,h,id,true);Rank(f,id,rank,7,10,id,true);Avatar(f,id+"-avatar",p.portrait,45,6,38,id);Text(f,id+"-name","You",94,7,w-176,21,16,id,"#1B435B",true);Sub(f,id+"-sub","Your rank",94,28,w-176,15,10,id);Text(f,id+"-level","Level "+p.level,w-84,13,74,23,14,id,"#275C75");return;}
   Art(f,id+"-base",rank==1?"LB2_RowTop":"LB2_Row",0,0,w,h,id,true);Rank(f,id,rank,7,26,id,true);
   Avatar(f,id+"-avatar",p.portrait,45,11,61,id);
   Text(f,id+"-name",p.isSelf?"You":p.name,119,17,w-189,25,18,id,"#21465E",true);
   Sub(f,id+"-team",string.IsNullOrEmpty(p.team)?"Independent":p.team,119,44,w-189,20,12,id);
   Art(f,id+"-score","LB2_Level",w-62,18,50,48,id);Sub(f,id+"-level-label","LEVEL",w-59,23,44,13,9,id,"#4C788B",false);Text(f,id+"-level",p.level.ToString(CultureInfo.InvariantCulture),w-58,36,42,26,22,id,"#235870");
  }
  static void TeamRow(HomeFrame f,RankedTeam t,int rank,float x,float y,float w)
  {
   string id="team-"+t.id;Group(f,id,x,y,w,84);Art(f,id+"-base",rank==1?"LB2_RowTop":"LB2_Row",0,0,w,84,id,true);Rank(f,id,rank,7,25,id,true);
   Art(f,id+"-crest",t.crest,40,9,62,62,id,false,true);
   Text(f,id+"-name",t.name,111,15,w-200,24,17,id,"#21465E",true);Sub(f,id+"-members",t.members+" / "+t.capacity+" members",111,42,w-200,19,12,id);
   Sub(f,id+"-score-label","SCORE",w-80,16,66,16,9,id,"#66808C",false);Text(f,id+"-score",t.score.ToString("N0",CultureInfo.InvariantCulture),w-83,34,70,28,21,id,"#285C75");
  }
  static void FriendRow(HomeFrame f,LeaderboardSession s,RankedPlayer p,float x,float y,float w)
  {
   string id="friend-"+p.id;Group(f,id,x,y,w,80);Art(f,id+"-base","LB2_Row",0,0,w,80,id,true);Avatar(f,id+"-avatar",p.portrait,13,9,56,id);
   Text(f,id+"-name",p.name,84,13,w-151,24,17,id,"#21465E",true);Sub(f,id+"-sub",s.IsPending(p.id)?"Request pending":"Level "+p.level+" · #"+p.id,84,40,w-151,19,11,id);
   string asset=s.IsFriend(p.id)?"LB2_Remove":s.IsPending(p.id)?"LB2_Pending":"LB2_Add";string action=s.IsFriend(p.id)?"remove:":s.IsPending(p.id)?"cancel-request:":"add:";
   IconButton(f,id+"-action",s.Data.isDemo?action+p.id:"disabled",asset,w-56,15,s.IsFriend(p.id)?"Remove "+p.name:s.IsPending(p.id)?"Cancel request to "+p.name:"Add "+p.name,id);
  }
  public static LeaderboardFrame Build(float width,float height,LeaderboardSession s)
  {
   var r=new LeaderboardFrame{width=Math.Max(320,width),height=Math.Max(width/Math.Max(1,height)>1.5f?320:420,height)};float w=r.width,h=r.height;bool wide=w/h>1.5f;
   foreach(var f in new[]{r.chrome,r.overlay}){f.width=w;f.height=h;}var c=r.chrome;float dh=MainNavigationLayout.Height(w,h);float cw=Math.Min(w-28,760),cx=(w-cw)/2;
   Art(c,"backdrop","LB2_Background",0,0,w,h);
   Text(c,"title","Leaderboard",wide?20:35,wide?11:12,wide?245:w-70,36,28);
   float tw=wide?Math.Min(420,w-295):Math.Min(w-40,520),tx=wide?w-tw-20:(w-tw)/2,ty=wide?11:66;
   Art(c,"tab-track","LB2_Track",tx-3,ty-4,tw+2,51,"",true);
   for(int i=0;i<3;i++)Button(c,"tab-"+i,"tab:"+i,((LeaderboardTab)i).ToString(),tx+i*tw/3,ty,tw/3-4,44,s.Tab==(LeaderboardTab)i);
   float sy=wide?60:119;float sw=s.Tab==LeaderboardTab.Friends?Math.Min(cw,368):Math.Min(cw,296);float sx=(w-sw)/2;
   Art(c,"scope-track","LB2_Track",sx-3,sy-3,sw+6,49,"",true);
   if(s.Tab==LeaderboardTab.Friends){Button(c,"friends-list","list","Friends List",sx,sy,sw/2-4,44,!s.Finding);Button(c,"friends-find","find","Add Friends",sx+sw/2+4,sy,sw/2-4,44,s.Finding);}
   else{Button(c,"world","world","World",sx,sy,sw/2-4,44,!s.Local);Button(c,"local","local",s.Data.localRegion=="US"?"United States":s.Data.localRegion=="GB"?"United Kingdom":"Local",sx+sw/2+4,sy,sw/2-4,44,s.Local);}
   float vy=sy+70;
   if(s.Tab==LeaderboardTab.Friends&&s.Finding){float inputW=Math.Min(cw-54,430),ix=(w-inputW-50)/2;Art(c,"search-art","LB2_Search",ix,sy+51,inputW,44,"",true);var inp=Add(c,"search","input",ix+12,sy+51,inputW-22,44);inp.text=s.Query;inp.label=GameLocale.T("Name or player ID");inp.fontSize=15;inp.color="#203F52";IconButton(c,"search-submit","search","LB2_Find",ix+inputW+6,sy+51,"Search players");vy=sy+119;}
   string legend=s.Tab==LeaderboardTab.Friends?(s.Finding?(s.Query.Length>0?"Search results":"Suggested friends"):"Your friends"):s.Tab==LeaderboardTab.Players?"Player rankings":"Team rankings";
   Text(c,"legend",legend,cx+4,vy-22,cw-98,18,11,"","#D5DFE4",true);Text(c,"sample",s.Data.isDemo?"Sample data":"",cx+cw-92,vy-22,88,18,10,"","#9CBBCB");
   float footer=s.Tab==LeaderboardTab.Players?60:(h<360?0:32);float bottom=h-dh-footer;
   r.viewportY=vy;r.viewportHeight=Math.Max(44,bottom-vy);if(vy+r.viewportHeight>h-dh)r.viewportHeight=Math.Max(44,h-dh-vy);
   r.content.width=w;float y=5;
   if(s.Tab==LeaderboardTab.Players){var rows=s.Players();for(int i=0;i<rows.Length;i++){PlayerRow(r.content,rows[i],i+1,cx,y,cw);y+=96;}var self=s.Data.players.FirstOrDefault(p=>p.isSelf);if(self!=null)PlayerRow(c,self,s.Rank(self.id),cx,h-dh-58,cw,true);}
   else if(s.Tab==LeaderboardTab.Teams){var rows=s.Teams();for(int i=0;i<rows.Length;i++){TeamRow(r.content,rows[i],i+1,cx,y,cw);y+=92;}if(h>=360)Text(c,"team-note","Ranked by total team score",cx,h-dh-28,cw,20,11,"","#B8CAD7");}
   else{var rows=s.Friends();foreach(var p in rows){FriendRow(r.content,s,p,cx,y,cw);y+=88;}if(h>=360)Text(c,"friend-note",string.IsNullOrEmpty(s.Notice)?(s.Data.isDemo?"Local preview · no requests are sent":""):s.Notice,cx,h-dh-29,cw,22,11,"","#9CBBCB");}
   if(y==5){Art(r.content,"empty-icon",s.Tab==LeaderboardTab.Teams?"R3_Teams":"R3_Leaderboard",w/2-40,22,80,80,"",false,true);Text(r.content,"empty-title",s.Tab==LeaderboardTab.Friends?(s.Finding?"No players found":"Your friends will appear here"):"No rankings yet",cx,115,cw,28,20);Text(r.content,"empty-help",s.Tab==LeaderboardTab.Friends?(s.Finding?"Try a name or player ID.":"Open Add Friends to find players."):"Check back when rankings are available.",cx,152,cw,24,13,"","#B9D0E1");y=198;}
   r.content.height=Math.Max(r.viewportHeight,y+6);Dock(r,dh);
   if(!string.IsNullOrEmpty(s.ConfirmRemoveId))
   {
    var o=r.overlay;var dim=Add(o,"modal-shade","color",0,0,w,h);dim.color="#061423B8";Hit(o,"modal-block","disabled",0,0,w,h,"Remove friend confirmation");
    float mw=Math.Min(330,w-24),mh=250,mx=(w-mw)/2,my=(h-mh)/2;Group(o,"confirm",mx,my,mw,mh);Art(o,"confirm-panel","LB2_Dialog",0,0,mw,mh,"confirm",true);
    Text(o,"confirm-title","Remove friend?",20,24,mw-40,34,25,"confirm","#193B53");Text(o,"confirm-name",s.Player(s.ConfirmRemoveId).name,20,75,mw-40,27,20,"confirm","#1C5F7A");Text(o,"confirm-help","You can find them again later.",18,117,mw-36,24,13,"confirm","#6C715F");
    Button(o,"confirm-cancel","cancel-remove","Cancel",18,171,(mw-48)/2,50,false,"confirm");Button(o,"confirm-remove","confirm-remove","Remove",mw/2+6,171,(mw-48)/2,50,true,"confirm");
   }
   return r;
  }
 }
}

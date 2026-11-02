using System;
using System.Globalization;
using UnityEngine;
using UnityEngine.UI;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.OnlineSocial;
using HeartOfTheRain.App.TeamsAccess;
namespace HeartOfTheRain.App.TeamsLifecycle {
 public static class TeamsLifecycleLayout113 {
  static string T(string key)=>TeamsLifecycleText113.T(key);
  static HomeElement Add(HomeFrame f,string id,string kind,float x,float y,float w,float h,string parent="") {var e=new HomeElement{id=id,kind=kind,x=x,y=y,width=w,height=h,parent=parent};f.elements.Add(e);return e;}
  static void Art(HomeFrame f,string id,string asset,float x,float y,float w,float h,bool slice=true,string parent="") {var e=Add(f,id,"sprite",x,y,w,h,parent);e.asset=asset;e.sliced=slice;e.preserveAspect=!slice;e.color="#FFFFFF";}
  static void Text(HomeFrame f,string id,string text,float x,float y,float w,float h,int size=14,string color="#21465E",string kind="text",string parent="") {var e=Add(f,id,kind,x,y,w,h,parent);e.text=text??"";e.fontSize=size;e.color=color;}
  static void Button(HomeFrame f,string id,string action,string label,float x,float y,float w,float h,bool enabled,string tone="Blue") {Art(f,id+"-art",enabled?"TA_Button_"+tone:"TA_Button_Disabled",x,y,w,h);Text(f,id+"-label",label,x+7,y+3,w-14,h-6,14,enabled?"#FFFFFF":"#617F90");var e=Add(f,id,"group",x,y,w,h);e.action=enabled?action:"disabled";e.label=label;}
  public static string TeamNameDisplay113(Text target,string original,float width,float height){
   original=original??"";if(!target||!target.font||original.Length==0)return original;
   var font=target.font;var settings=target.GetGenerationSettings(new Vector2(width,height));settings.horizontalOverflow=HorizontalWrapMode.Wrap;settings.verticalOverflow=VerticalWrapMode.Overflow;settings.generationExtents=new Vector2(width,10000);settings.richText=false;
   var generator=new TextGenerator();float ppu=Math.Max(.1f,target.pixelsPerUnit);
   Func<string,string> display=value=>HeartOfTheRain.App.TeamsSocial.TeamsSocialLayout110.DisplayText110(value,font);
   Func<string,bool> fits=value=>{string safe=display(value);generator.Populate(safe,settings);return generator.lines.Count<=2&&generator.GetPreferredHeight(safe,settings)/ppu<=height+.25f;};
   if(fits(original))return display(original);
   if(font.dynamic)font.RequestCharactersInTexture("\u2026",target.fontSize,target.fontStyle);string suffix=font.HasCharacter('\u2026')?"\u2026":"...";
   int[] starts=StringInfo.ParseCombiningCharacters(original);int low=0,high=starts.Length;
   while(low<high){int mid=(low+high+1)/2,end=mid==starts.Length?original.Length:starts[mid];string candidate=original.Substring(0,end).TrimEnd()+suffix;if(fits(candidate))low=mid;else high=mid-1;}
   int cut=low==starts.Length?original.Length:starts[low];return display(original.Substring(0,cut).TrimEnd()+suffix);
  }
  public static void Decorate(OnlineTeamsFrame82 frame,OnlineTeamsView82 view,float safeWidth,float safeHeight){
   float actualW=Math.Max(1,safeWidth),actualH=Math.Max(1,safeHeight);
   if(!string.IsNullOrEmpty(view.leaveToast113)){float tw=Math.Min(360,actualW-28),tx=(actualW-tw)/2,ty=actualH-MainNavigationLayout.ReservedHeight(actualW,actualH)-62;Art(frame.chrome,"leave-toast113-base","TA_Panel_Blue",tx,ty,tw,48);Text(frame.chrome,"leave-toast113",view.leaveToast113,tx+12,ty+5,tw-24,38,14,"#FFFFFF");}
   if(view.modal!="leave113")return;
   var f=new HomeFrame{width=actualW,height=actualH};frame.overlay=f;float w=actualW,h=actualH,mw=Math.Min(330,w*.82f),mh=Math.Min(322,Math.Min(h-32,h*.56f)),mx=(w-mw)/2,my=Math.Max(10,(h-mh)/2+9);
   var shade=Add(f,"leave-shade113","color",0,0,w,h);shade.color="#000000AD";var block=Add(f,"leave-block113","group",0,0,w,h);block.action="disabled";block.label=T("close_accessibility");Add(f,"leave-motion113","group",0,0,w,h);
   Art(f,"leave-panel113","TA_Panel_Blue",mx,my,mw,mh);
   // R3 crest and close protrude above the panel; the close disc sits near
   // its right edge while its full 80x48 touch target stays inside safe bounds.
   Art(f,"leave-crest113","TA_Badge_banners",mx+mw/2-32,my-39,64,64,false);
   Art(f,"leave-close113-art","TA_Close_Disc",mx+mw-40,my-9,48,48,false);
   Art(f,"leave-close113-icon","TA_Icon_Close",mx+mw-28,my+3,24,24,false);
   var close=Add(f,"leave-close113","group",mx+mw-56,my-9,80,48);close.action="leave-close113";close.label=T("close_accessibility");
   string state=view.leaveState113??"confirm";string title=state=="pending"?"pending_title":state=="unknown"?"unknown_title":state=="offline"?"offline_title":state=="role"?"role_title":state=="failed"?"failed_title":state=="unavailable"?"unknown_title":"leave_title";
   string body=state=="pending"?"pending_body":state=="unknown"?"unknown_body":state=="offline"?"offline_body":state=="role"?"role_body":state=="failed"?"failed_body":state=="unavailable"?"unavailable_body":view.leaveClosesTeam113?"sole_owner_body":"leave_body";
   Text(f,"leave-title113",T(title),mx+12,my+48,mw-24,44,21,"#FFFFFF");float bx=mx+14,by=my+97,bw=mw-28,bh=Math.Max(40,mh-170);Art(f,"leave-cream113","TA_Panel_Cream",bx,by,bw,bh);
   var scroll=Add(f,"leave-body113","invitebody112",bx+8,by+8,bw-16,Math.Max(24,bh-16));scroll.label="leave-body-content113";
   var content=Add(f,"leave-body-content113","group",0,0,bw-16,Math.Max(bh-16,150),scroll.id);
   Art(f,"leave-team-badge113",TeamsAccessBadges109.Asset(view.leaveBadge113),10,8,62,62,false,content.id);Text(f,"leave-team-name113",view.leaveTeamName113,80,12,bw-112,52,17,"#073354","leavename113",content.id);
   Text(f,"leave-body-text113",T(body),14,72,bw-44,70,15,"#21465E","chatbody110",content.id);
   float buttonY=my+mh-62,gap=10,half=(mw-38-gap)/2;bool role=state=="role";
   if(role)Button(f,"leave-cancel113","leave-close113",T("close_action"),mx+19,buttonY,mw-38,48,true);
   else {Button(f,"leave-cancel113","leave-close113",T(state=="pending"||state=="unknown"?"close_action":"cancel_action"),mx+19,buttonY,half,48,true);string key=state=="pending"?"leaving":state=="unknown"?"check_status":(state=="unavailable"||state=="failed")?"retry_action":"leave_action";string action=state=="unknown"?"leave-check113":(state=="unavailable"||state=="failed")?"leave-refresh113":"leave-confirm113";bool enabled=!view.leaveBusy113&&(state=="unknown"||state=="unavailable"||state=="failed"||state=="confirm");Button(f,"leave-action113",action,T(key),mx+19+half+gap,buttonY,half,48,enabled,state=="confirm"?"Red":"Blue");}
   foreach(var element in f.elements)if(string.IsNullOrEmpty(element.parent)&&element.id!="leave-shade113"&&element.id!="leave-block113"&&element.id!="leave-motion113")element.parent="leave-motion113";
  }
 }
}

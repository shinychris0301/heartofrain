using HeartOfTheRain.App.Localization;
using HeartOfTheRain.App.Celebrations;
using System;using System.Linq;using HeartOfTheRain.App.Home;
namespace HeartOfTheRain.App.Journey
{
 [Serializable] public sealed class JourneyFrame {public float width,height,viewportY,viewportHeight;public bool reading;public HomeFrame chrome=new HomeFrame(),content=new HomeFrame();}
 public static class JourneyLayout
 {
  static HomeElement Add(HomeFrame f,string id,string kind,string parent,float x,float y,float w,float h){var e=new HomeElement{id=id,kind=kind,parent=parent,x=x,y=y,width=w,height=h};f.elements.Add(e);return e;}
  static void Group(HomeFrame f,string id,float x,float y,float w,float h,string parent=""){Add(f,id,"group",parent,x,y,w,h);}
  static void Art(HomeFrame f,string id,string asset,float x,float y,float w,float h,string parent="",bool slice=false,string color="#FFFFFF",string kind="sprite"){var e=Add(f,id,kind,parent,x,y,w,h);e.asset=asset;e.sliced=slice;e.color=color;e.preserveAspect=!slice&&((asset.StartsWith("R3_",StringComparison.Ordinal)&&asset!="R3_Header")||asset=="Lock"||asset=="Close");}
  static void Label(HomeFrame f,string id,string text,float x,float y,float w,float h,int size,string parent="",string color="#FFFFFF",bool shadow=true){var e=Add(f,id,"text",parent,x,y,w,h);e.text=GameLocale.Element(id,text);e.fontSize=size;e.color=color;e.shadow=shadow;}
  static void Hit(HomeFrame f,string id,string action,float x,float y,float w,float h,string label,string parent=""){var e=Add(f,id,"group",parent,x,y,w,h);e.action=action;e.label=GameLocale.T(label);}
  static void Button(HomeFrame f,string id,string action,string text,float x,float y,float w,float h,string parent="",bool enabled=true,int size=22)
  {Art(f,id+"-art","R4_Start",x,y,w,h,parent,false,enabled?"#FFFFFF":"#788A9D");Label(f,id+"-text",text,x+12,y+7,w-24,h-14,size,parent);Hit(f,id,enabled?action:"disabled",x,y,w,h,text,parent);}
  static void Chrome(JourneyFrame r)
  {
   var f=r.chrome;float w=r.width,h=r.height;bool wide=w/h>1.4f;float head=wide?70:92;
   Art(f,"backdrop","ArchiveBackdrop",0,0,w,h);Art(f,"top-bar","HeaderBar",0,0,w,head);
   Label(f,"title",r.reading?"Story":"Journey",52,wide?8:14,w-104,42,32);
   if(r.reading){Art(f,"reader-close-art","Close",w-46,16,30,30);Hit(f,"reader-close","reader-close",w-53,9,44,44,"Return to Journey");}
   float dw=Math.Min(w,620),dh=MainNavigationLayout.Height(w,h),dx=(w-dw)/2,dy=h-dh;
   MainNavigationLayout.Add(f,dx,dy,dw,dh,0);
   r.viewportY=head;r.viewportHeight=Math.Max(120,dy-head-2);
  }
  static void Card(HomeFrame f,JourneySession s,JourneyChapter c,float x,float y,float w,float h)
  {
   string id="chapter-"+c.number;Group(f,id,x,y,w,h);string mask=id+"-mask";
   Art(f,mask,"CoverMask",6,31,w-12,h-54,id,true,"#FFFFFF","mask");
   Art(f,id+"-cover",c.art,0,0,w-12,h-54,mask,false,s.Unlocked(c.number)?"#FFFFFF":"#8C9DAF","cover");
   if(c.art=="Unrevealed")Art(f,id+"-book","R3_Journey",(w-142)/2,65,130,105,mask);
   Art(f,id+"-shade","CardShade",0,h-226,w-12,172,mask);
   Art(f,id+"-frame","ChapterFrame",0,25,w,h-44,id,true);
   Art(f,id+"-plaque","R4_Chapter",4,0,w-8,66,id);
   Label(f,id+"-number","CHAPTER "+c.number,18,12,w-36,17,11,id,"#EBD6A8");
   int titleSize=21;string title=JourneyText.Wrap(StoryLocale.Title(c.number,c.title),w-44,titleSize,true);if(title.Contains("\n")){titleSize=14;title=JourneyText.Wrap(StoryLocale.Title(c.number,c.title),w-44,titleSize,true);}while(title.Count(ch=>ch=='\n')>1&&titleSize>10){titleSize--;title=JourneyText.Wrap(StoryLocale.Title(c.number,c.title),w-44,titleSize,true);}
   var heading=Add(f,id+"-title","story-title",id,22,29,w-44,34);heading.text=title;heading.fontSize=titleSize;heading.color="#FFFFFF";heading.shadow=true;
   if(s.Unlocked(c.number))
   {
    string progress=s.Complete(c.number)?"Chapter complete":Math.Max(0,s.State.completedLevels-JourneySession.FirstLevel(c.number)+1)+" / 50 levels";
    Label(f,id+"-progress",progress,28,h-133,w-56,24,14,id,"#FFF1CF");
    Button(f,id+"-view","view:"+c.number,"View Story",(w-178)/2,h-102,178,55,id);
   }
   else
   {
    Art(f,id+"-lock","Lock",(w-48)/2,(h-72)/2,48,54,id);
    Label(f,id+"-locked","Locked",24,h-108,w-48,30,23,id);
    Label(f,id+"-unlock","Opens at Level "+JourneySession.FirstLevel(c.number),18,h-78,w-36,23,14,id,"#E8D6B6");
   }
   Art(f,id+"-range-art","R3_Header",(w-146)/2,h-33,146,30,id,true);
   Label(f,id+"-range","Levels "+JourneySession.FirstLevel(c.number)+"–"+JourneySession.LastLevel(c.number),(w-134)/2,h-29,134,20,12,id);
  }
  static void Archive(JourneyFrame r,JourneySession s)
  {
   var f=r.content;float w=r.width;int columns=w>=660?2:1;float cw=Math.Min(316,(w-(columns+1)*32)/columns);float gap=28;float total=cw*columns+gap*(columns-1);float x0=(w-total)/2;
   float ch=w/r.height>1.4f?250:Math.Max(330,Math.Min(cw*1.28f,r.viewportHeight-28));var cards=s.Cards();
   for(int i=0;i<cards.Length;i++)Card(f,s,cards[i],x0+(i%columns)*(cw+gap),14+(i/columns)*(ch+28),cw,ch);
   f.height=Math.Max(r.viewportHeight,28+(float)Math.Ceiling(cards.Length/(float)columns)*(ch+28));f.width=w;
  }
  static void Reader(JourneyFrame r,JourneySession s,bool animationAvailable)
  {
   var f=r.content;var c=s.Current;float w=r.width;bool wide=w>=660;float pw=Math.Min(w-28,wide?820:520),x=(w-pw)/2;
   string body=s.State.beat==0?StoryLocale.Opening(c.number,c.opening):StoryLocale.Ending(c.number,c.ending);int size=16;float artW=wide?pw*.42f:pw-12,artH=wide?330:160,textW=wide?pw-artW-40:pw-40;
   string wrapped=JourneyText.Wrap(body,textW-4,size);float textH=(wrapped.Count(ch=>ch=='\n')+1)*24+4;
   string title=JourneyText.Wrap(StoryLocale.Title(c.number,c.title),textW-4,23,true);float titleH=(title.Count(ch=>ch=='\n')+1)*29;
   float textY=(wide?18:artH+22)+26+titleH+15;bool watch=animationAvailable&&s.State.beat==1&&s.Complete(c.number);float ph=Math.Max(wide?390:0,textY+textH+139+(watch?62:0));
   Group(f,"reader",x,14,pw,ph);Art(f,"reader-panel","ReaderPanel",0,0,pw,ph,"reader",true);
   Art(f,"reader-art-mask","CoverMask",6,6,artW,artH,"reader",true,"#FFFFFF","mask");Art(f,"reader-art",c.art,0,0,artW,artH,"reader-art-mask",false,"#FFFFFF","cover");
   float tx=wide?artW+22:20,ty=wide?18:artH+22;
   Label(f,"reader-chapter",GameLocale.Format("CHAPTER {0}",c.number)+"  ·  "+GameLocale.T(s.State.beat==0?"OPENING":"ENDING"),tx,ty,textW,21,12,"reader","#776442",false);
   var heading=Add(f,"reader-heading","story-title","reader",tx,ty+26,textW,titleH);heading.text=title;heading.fontSize=23;heading.color="#17354E";
   var p=Add(f,"reader-copy","paragraph","reader",tx,textY,textW,textH);p.text=wrapped;p.fontSize=size;p.color="#244255";
   float by=textY+textH+18;
   if(s.State.beat==0&&!s.Complete(c.number))Label(f,"reader-next-lock","Ending unlocks after Level "+JourneySession.LastLevel(c.number),tx,by,textW,22,12,"reader","#6C6455",false);
   else Label(f,"reader-page",(s.State.beat+1)+" / 2",tx,by,textW,22,13,"reader","#6C6455",false);
   if(watch){Button(f,"reader-watch","celebration",CelebrationText.T("Watch celebration"),tx,by+32,textW,48,"reader",true,17);by+=62;}
   float bw=Math.Min(150,(textW-12)/2),start=tx+(textW-(bw*2+12))/2;
   Button(f,"reader-prev","previous","Back",start,by+34,bw,46,"reader",s.State.beat>0,18);
   Button(f,"reader-next",s.State.beat==1?"reader-close":"next",s.State.beat==1?"Done":"Next",start+bw+12,by+34,bw,46,"reader",s.State.beat==1||s.Complete(c.number),18);
   f.width=w;f.height=Math.Max(r.viewportHeight,ph+28);
  }
  public static JourneyFrame Build(float width,float height,JourneySession session,bool animationAvailable=false)
  {
   var r=new JourneyFrame{width=Math.Max(280,width),height=Math.Max(320,height),reading=session.Reading};r.chrome.width=r.width;r.chrome.height=r.height;Chrome(r);if(r.reading)Reader(r,session,animationAvailable);else Archive(r,session);return r;
  }
 }
}

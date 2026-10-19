using HeartOfTheRain.App.Celebrations;
using System;using System.Linq;using HeartOfTheRain.App.Home;using HeartOfTheRain.App.Journey;using HeartOfTheRain.App.Localization;
namespace HeartOfTheRain.App.FirstStart {
 [Serializable]public sealed class FirstStartFrame {public float width,height,viewportX,viewportY,viewportWidth,viewportHeight;public HomeFrame chrome=new HomeFrame(),content=new HomeFrame(),overlay=new HomeFrame();}
 public static class FirstStartLayout {
  static HomeElement Add(HomeFrame f,string id,string kind,float x,float y,float w,float h,string parent=""){var e=new HomeElement{id=id,kind=kind,x=x,y=y,width=w,height=h,parent=parent};f.elements.Add(e);return e;}
  static void Sprite(HomeFrame f,string id,string asset,float x,float y,float w,float h,bool sliced=false,string parent="",string color="#FFFFFF"){var e=Add(f,id,"sprite",x,y,w,h,parent);e.asset=asset;e.sliced=sliced;e.preserveAspect=!sliced;e.color=color;}
  static void Label(HomeFrame f,string id,string text,float x,float y,float w,float h,int size,string color="#17354E"){var e=Add(f,id,"text",x,y,w,h);e.text=FirstStartText.T(text);e.fontSize=size;e.color=color;}
  static float Paragraph(HomeFrame f,string id,string text,float x,float y,float w,int size,bool bold=false){string wrapped=JourneyText.Wrap(text,w-4,size,bold);float step=size+(bold?6:8),h=wrapped.Split('\n').Length*step;var e=Add(f,id,bold?"heading":"paragraph",x,y,w,h);e.text=wrapped;e.fontSize=size;e.color="#17354E";return h;}
  static void Hit(HomeFrame f,string id,string action,float x,float y,float w,float h,string label){var e=Add(f,id,"group",x,y,w,h);e.action=action;e.label=FirstStartText.T(label);}
  public static FirstStartFrame Build(float width,float height,FirstStartSession session,string chapterOpening,bool music=true,bool languages=false,string status=""){
   var r=new FirstStartFrame{width=Math.Max(320,width),height=Math.Max(360,height)};float w=r.width,h=r.height;bool wide=w>=660&&w/h>1.25f;var f=r.chrome;f.width=w;f.height=h;r.overlay.width=w;r.overlay.height=h;
   bool practice=session.Practice;var stage=session.Stage;string art=stage==FirstStartStage.Prologue?"Chapter02_Chamber":"Chapter01_VillageWell";
   var bg=Add(f,"scene-art","cover",0,0,w,h);bg.asset=art;
   if(practice){var shade=Add(f,"scene-shade","color",0,0,w,h);shade.color="#102B4290";}
   float panelW=wide?w*.52f-18:Math.Min(540,w-28),panelX=wide?w*.48f:(w-panelW)/2;
   float panelY=wide||practice?76:Math.Min(h*.40f,340);float panelH=h-panelY-14;
   Sprite(f,"story-shell","FS_Panel",panelX,panelY,panelW,panelH,true);
   Sprite(f,"language-pill","FS_Chip",14,12,128,44,true);Sprite(f,"language-globe","AS_Globe",23,22,25,25);Label(f,"language-label",GameLocale.Names[GameLocale.Current],48,16,87,36,14,"#FFF4DB");Hit(f,"language","language",14,12,128,44,"Language");
   Sprite(f,"music-pill","FS_Chip",w-142,12,48,44,true);Sprite(f,"music-icon","MusicGlyph",w-133,22,28,25);if(!music)Sprite(f,"music-off","OffSlash",w-135,19,32,32);Hit(f,"music","music",w-142,12,48,44,music?"Music on":"Music off");
   Sprite(f,"skip-pill","FS_Chip",w-86,12,72,44,true);Label(f,"skip-label","Skip",w-83,16,66,36,14,"#FFF4DB");Hit(f,"skip","skip",w-86,12,72,44,stage<FirstStartStage.Match?"Skip intro":"Skip tutorial");
   r.viewportX=panelX+18;r.viewportY=panelY+20;r.viewportWidth=panelW-36;r.viewportHeight=Math.Max(80,panelH-102);var c=r.content;c.width=r.viewportWidth;float cw=c.width,y=0;
   string eyebrow=stage==FirstStartStage.Prologue?FirstStartText.T("PROLOGUE"):stage==FirstStartStage.Chapter?GameLocale.Format("CHAPTER {0}",1)+" · "+GameLocale.T("OPENING"):practice?string.Format(FirstStartText.T("LESSON {0} / 3"),(int)stage-1):FirstStartText.T("Ready for Level 1");Label(c,"eyebrow",eyebrow,0,y,cw,22,12,"#8A6A32");y+=29;
   string heading=stage==FirstStartStage.Prologue?"A light worth protecting":stage==FirstStartStage.Chapter?StoryLocale.Title(1,"The Village Well"):stage==FirstStartStage.Match?"Match three":stage==FirstStartStage.Rocket?"Make a Rocket":stage==FirstStartStage.Clear?"Clear the target":"Your journey begins";
   y+=Paragraph(c,"heading",FirstStartText.T(heading),0,y,cw,24,true)+12;
   if(stage==FirstStartStage.Chapter){Label(c,"chapter-range",CelebrationText.Format("Levels {0}–{1}",1,50),0,y,cw,22,12,"#8A6A32");y+=30;}
   string copy=stage==FirstStartStage.Prologue?"Beneath Ancient Moscow, a sacred Heart sends light through the wells, gardens, and protective wards. Far from the city, Ivan returns to the village where his journey began.":stage==FirstStartStage.Chapter?StoryLocale.Opening(1,chapterOpening):stage==FirstStartStage.Match?"Swap the highlighted tiles to match three of the same color.":stage==FirstStartStage.Rocket?"Match four in a line to create a Rocket. Try the highlighted swap.":stage==FirstStartStage.Clear?"Tap the Rocket to clear its row and break the crate. Clear all targets before your moves run out.":"Help Ivan restore the village well. Your first level is ready.";
   y+=Paragraph(c,"copy",FirstStartText.T(copy),0,y,cw,16)+14;
   if(practice){float bw=Math.Min(320,cw);var board=Add(c,"practice-board","board",(cw-bw)/2,y,bw,bw);y+=bw+8;
    string message=status!=""?status:session.Solved?(stage==FirstStartStage.Match?"Nice match!":stage==FirstStartStage.Rocket?"Rocket created!":"Target cleared!"):stage==FirstStartStage.Clear?GameLocale.T("Targets")+": 1":"Try the move";
    string wrapped=JourneyText.Wrap(FirstStartText.T(message),cw-4,17,true);float statusH=Math.Max(26,wrapped.Split('\n').Length*23);Label(c,"practice-status",wrapped,0,y,cw,statusH,17,session.Solved?"#28744C":"#45647A");y+=statusH+6; y+=Paragraph(c,"practice-note",FirstStartText.T("No lives or boosters are used here."),0,y,cw,12)+8;}
   else if(stage==FirstStartStage.Ready){Sprite(c,"ready-star","RewardStar_R2",(cw-94)/2,y,94,94);y+=110;}
   panelH=Math.Min(h-90,Math.Max(240,y+102));panelY=wide?Math.Max(76,(h-panelH)/2):h-panelH-14;var shell=f.elements.Find(e=>e.id=="story-shell");shell.y=panelY;shell.height=panelH;r.viewportY=panelY+20;r.viewportHeight=panelH-102;if(y>r.viewportHeight){r.viewportHeight-=12;Label(f,"scroll-cue","Scroll for more",panelX+18,panelY+panelH-87,panelW-36,14,10,"#45647A");}c.height=Math.Max(r.viewportHeight,y);
   float buttonW=Math.Min(258,panelW-36),buttonX=panelX+(panelW-buttonW)/2,buttonY=panelY+panelH-70;
   Sprite(f,"next-art","R4_Start",buttonX,buttonY,buttonW,58,false,color:session.CanContinue?"#FFFFFF":"#90A19C");string next=stage==FirstStartStage.Ready?"Start Level 1":session.CanContinue?"Continue":"Try the move";Label(f,"next-label",next,buttonX+15,buttonY+11,buttonW-30,34,21,"#FFFFFF");Hit(f,"next",session.CanContinue?"next":"disabled",buttonX,buttonY,buttonW,58,next);
   if(status=="Could not load. Retry or skip."){Label(f,"next-label-retry","Retry",buttonX+15,buttonY+11,buttonW-30,34,21,"#FFFFFF");f.elements.RemoveAll(e=>e.id=="next-label");f.elements.Find(e=>e.id=="next").action="retry";}
   if(languages){var o=r.overlay;var shade=Add(o,"language-shade","color",0,0,w,h);shade.color="#061426D8";Hit(o,"language-dismiss","language",0,0,w,h,"Close");float lw=Math.Min(326,w-32),lh=342,lx=(w-lw)/2,ly=(h-lh)/2;Sprite(o,"language-shell","FS_Panel",lx,ly,lw,lh,true);Label(o,"language-title","Language",lx+20,ly+16,lw-40,34,24);
    for(int i=0;i<5;i++){float yy=ly+62+i*52;Sprite(o,"locale-row-"+i,"AS_Row",lx+14,yy,lw-28,46,true);Label(o,"locale-name-"+i,GameLocale.Names[i],lx+28,yy+5,lw-86,36,18);if(i==GameLocale.Current)Sprite(o,"locale-tick-"+i,"SelectionTick_R2",lx+lw-52,yy+9,28,28);Hit(o,"locale-"+i,"locale:"+i,lx+14,yy,lw-28,46,GameLocale.Names[i]);}}
   return r;
  }
 }
}

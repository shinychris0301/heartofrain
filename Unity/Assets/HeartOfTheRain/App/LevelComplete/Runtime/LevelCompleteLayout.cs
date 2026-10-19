using System;
using HeartOfTheRain.App.Celebrations;
using HeartOfTheRain.App.Home;
namespace HeartOfTheRain.App.LevelComplete {
 public static class LevelCompleteLayout {
  static HomeElement Add(HomeFrame f,string id,string kind,float x,float y,float w,float h,string parent="panel"){var e=new HomeElement{id=id,kind=kind,x=x,y=y,width=w,height=h,parent=parent};f.elements.Add(e);return e;}
  static void Art(HomeFrame f,string id,string asset,float x,float y,float w,float h,bool sliced=false,string parent="panel"){var e=Add(f,id,"sprite",x,y,w,h,parent);e.asset=asset;e.sliced=sliced;e.preserveAspect=!sliced;}
  static void Text(HomeFrame f,string id,string text,float x,float y,float w,float h,int size,string color="#17354E"){var e=Add(f,id,"text",x,y,w,h);e.text=LevelCompleteText.T(text);e.fontSize=size;e.color=color;}
  static void Hit(HomeFrame f,string id,string action,float x,float y,float w,float h,string label){var e=Add(f,id,"group",x,y,w,h);e.action=action;e.label=LevelCompleteText.T(label);}
  public static HomeFrame Build(float width,float height,LevelCompleteViewData s){
   float w=Math.Max(320,width),h=Math.Max(320,height);bool wide=w>=640&&w/h>=1.3f;float pw=wide?580:Math.Min(368,w-24),ph=wide?332:h<600?456:524;
   var f=new HomeFrame{width=w,height=Math.Max(h,ph+24),landscape=wide,compact=h<570};Add(f,"panel","group",(w-pw)/2,(f.height-ph)/2,pw,ph,"");
   Art(f,"shell","ModalShell_R2",0,0,pw,ph,true);Text(f,"title",s.chapterComplete?"Chapter complete!":"Level complete!",26,25,pw-80,34,27,"#FFFFFF");
   Art(f,"home-art","LC_Home",pw-43,31,27,27);Hit(f,"home","home",pw-50,24,44,44,"Home");
   float heroSize=wide?194:h<600?150:218,heroX=wide?22:(pw-heroSize)/2,heroY=wide?74:75;
   Add(f,"hero","group",heroX,heroY,heroSize,heroSize);
   Art(f,"halo","LC_Halo",0,0,heroSize,heroSize,false,"hero");
   float ds=heroSize*.72f;Add(f,"daria","daria",(heroSize-ds)/2,0,ds,ds,"hero");
   Art(f,"hero-star","RewardStar_R2",heroSize*.73f,heroSize*.60f,heroSize*.20f,heroSize*.20f,false,"hero");
   for(int i=0;i<18;i++)Art(f,"spark-"+i,"RewardStar_R2",heroSize/2-6,heroSize*.43f-6,12,12,false,"hero");
   Text(f,"praise",CelebrationText.Praise(s.level),heroX,heroY+heroSize*.75f,heroSize,25,18);
   Text(f,"level",LevelCompleteText.Format("Level {0}",s.level),heroX,heroY+heroSize*.87f,heroSize,20,12);
   float x=wide?248:24,y=wide?82:76+heroSize,area=wide?pw-276:pw-48;
   Text(f,"reward-title",s.firstClear?"Rewards earned":"Already cleared",x,y,area,25,17);y+=32;
   float gap=10,card=(area-gap)/2;
   for(int i=0;i<2;i++){float xx=x+i*(card+gap);Art(f,"reward-well-"+i,"LC_RewardWell",xx,y,card,62,true);Art(f,"reward-icon-"+i,i==0?"RewardCoin":"RewardStar_R2",xx+8,y+10,39,39);Text(f,"reward-count-"+i,"+"+(i==0?s.coins:s.stars),xx+49,y+9,card-55,42,25,s.firstClear?"#17354E":"#6A7E89");}
   y+=74;Text(f,"progress-label",LevelCompleteText.Format(s.chapterComplete?"Chapter {0} restored":"Chapter {0} progress",s.chapter),x,y,area-66,22,12);Text(f,"progress-count",Math.Min(50,s.completedAfter-(s.chapter-1)*50)+" / 50",x+area-65,y,65,22,14);
   y+=26;Art(f,"progress-track","LC_Track",x,y,area,13,true);float value=Math.Max(0,Math.Min(50,s.completedAfter-(s.chapter-1)*50))/50f;Art(f,"progress-fill","LC_Fill",x+2,y+2,Math.Max(.01f,(area-4)*value),9,true);
   float bx=wide?286:(pw-228)/2,by=ph-72;Art(f,"continue-art","R4_Start",bx,by,228,66);Text(f,"continue-text",s.chapterComplete?"View story":s.hasNext?"Continue":"Home",bx+15,by+12,198,38,24,"#FFFFFF");Hit(f,"continue","continue",bx,by,228,66,s.chapterComplete?"View story":s.hasNext?"Continue":"Home");
   if(wide)Text(f,"success-note","All targets cleared",25,ph-53,200,24,12,"#FFFFFF");
   return f;
  }
 }
}

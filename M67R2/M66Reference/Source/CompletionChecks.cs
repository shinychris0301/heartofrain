using System;using System.IO;using System.Linq;using System.Collections.Generic;using System.Text.Json;
using HeartOfTheRain.App.Home;using HeartOfTheRain.App.LevelComplete;using HeartOfTheRain.App.Localization;using HeartOfTheRain.App.Journey;
class CompletionChecks {
 static int count;static void Check(bool ok,string why){count++;if(!ok)throw new Exception(why);}static JsonSerializerOptions json=new JsonSerializerOptions{IncludeFields=true,WriteIndented=true};
 static HomeState Home(int completed)=>new HomeState{currentLevel=Math.Min(50,completed+1),completedLevelsInChapter=completed,coins=1250,stars=3,lives=4};
 static void Main(string[] args){var r=args[0];var s=new LevelCompleteSession();var home=Home(17);Check(!s.TrySettle(18,"Won",false,home,50,50,1),"unarmed grant");Check(s.Arm(1,18),"arm");Check(!s.Arm(1,18),"duplicate arm");Check(!s.TrySettle(18,"Playing",false,home,50,50,1),"premature grant");Check(!s.TrySettle(18,"Out of moves",false,home,50,50,1),"loss grant");Check(!s.TrySettle(18,"Won",true,home,50,50,1),"busy grant");Check(!s.TrySettle(19,"Won",false,home,50,50,1),"foreign level");Check(home.coins==1250&&home.stars==3&&home.currentLevel==18,"failed action changed home");
 Check(s.TrySettle(18,"Won",false,home,50,50,1),"real win rejected");Check(home.coins==1300&&home.stars==4&&home.lives==4&&home.currentLevel==19&&home.completedLevelsInChapter==18,"settlement wrong");Check(!s.TrySettle(18,"Won",false,home,50,50,1),"duplicate receipt");Check(!s.Arm(2,19),"open result overwritten");Check(s.Close()&&!s.Close(),"duplicate close");Check(!s.TrySettle(18,"Won",false,home,50,50,1),"closed receipt regranted");Check(s.Arm(2,18)&&s.TrySettle(18,"Won",false,home,50,50,1),"replay result missing");Check(!s.View.firstClear&&s.View.coins==0&&s.View.stars==0&&home.coins==1300&&home.currentLevel==19,"replay farm");
 var profiles=new List<object>();
 foreach(var tuple in new[]{(0,1),(17,18),(49,50),(50,50)}){
  var h=Home(tuple.Item1);var policy=new LevelCompleteSession();policy.Arm(1,tuple.Item2);Check(policy.TrySettle(tuple.Item2,"Won",false,h,50,50,1),"fixture");var v=policy.View;
  if(tuple.Item2==50)Check(v.chapterComplete&&!v.hasNext&&v.nextLevel==50&&h.currentLevel==50&&h.completedLevelsInChapter==50,"finale loop");
  for(int lang=0;lang<5;lang++)foreach(var size in new[]{(320,480),(393,698),(430,852),(768,1024),(750,369),(1280,800),(320,320),(1024,600)}){
   GameLocale.Select(lang);var f=LevelCompleteLayout.Build(size.Item1,size.Item2,v);var parents=new Dictionary<string,HomeElement>();
   foreach(var e in f.elements){float w=f.width,hh=f.height;if(e.parent!=""){Check(parents.ContainsKey(e.parent),"unresolved parent");w=parents[e.parent].width;hh=parents[e.parent].height;}
    Check(e.x>=-.01&&e.y>=-.01&&e.width>0&&e.height>0&&e.x+e.width<=w+.01&&e.y+e.height<=hh+.01,"bounds "+e.id);if(e.action!="")Check(e.width>=44&&e.height>=44,"small hit");parents[e.id]=e;
   }
   Check(f.elements.Count(e=>e.action=="continue")==1&&f.elements.Count(e=>e.action=="home")==1,"duplicated navigation");
   profiles.Add(new{name=GameLocale.Codes[lang]+"-"+tuple.Item1+"-"+size.Item1+"x"+size.Item2,locale=GameLocale.Codes[lang],width=size.Item1,height=size.Item2,data=v,frame=f});
  }
 }
 foreach(var h in new[]{Home(0),Home(49)}){h.coins=int.MaxValue-1;h.stars=int.MaxValue-1;var p=new LevelCompleteSession();p.Arm(1,h.currentLevel);Check(p.TrySettle(h.currentLevel,"Won",false,h,50,int.MaxValue,int.MaxValue),"large rewards");Check(h.coins==int.MaxValue&&h.stars==int.MaxValue,"overflow");}
 var skip=new LevelCompleteSession();skip.Arm(1,20);var fresh=Home(0);Check(!skip.TrySettle(20,"Won",false,fresh,50,50,1)&&fresh.currentLevel==1,"skip progression");
 var poses=new List<object>();for(int i=0;i<=72;i++)foreach(bool reduce in new[]{false,true}){float t=i/24f;var p=LevelCompleteMotion.Sample(t,reduce);Check(p.alpha>=0&&p.alpha<=1&&p.reward>=0&&p.reward<=1&&p.progress>=0&&p.progress<=1&&p.starScale>0,"pose bounds");foreach(var star in p.particles)Check(!float.IsNaN(star.x)&&star.alpha>=0&&star.alpha<=1&&star.scale>0,"particle pose");if(reduce)Check(p.reward==1&&p.progress==1&&p.starScale==1&&p.particles.All(a=>a.alpha==0),"reduced motion");poses.Add(new{time=t,reduced=reduce,pose=p});}
 GameLocale.Select(0);File.WriteAllText(Path.Combine(r,"Validation/Runtime_Layouts.json"),JsonSerializer.Serialize(profiles,json));File.WriteAllText(Path.Combine(r,"Validation/Motion_Samples.json"),JsonSerializer.Serialize(poses,json));var report=new{status="PASS_COMPLETION_POLICY_LAYOUT_AND_MOTION",checks=count,layouts=profiles.Count,motionSamples=poses.Count,languages=GameLocale.Codes,priorLifeAndBoosterBehavior="Lives untouched by win settlement; booster stock remains in existing launch session",UnityAPICompilation="NOT_RUN",UnityPlayMode="NOT_RUN",DeviceInput="NOT_RUN"};File.WriteAllText(Path.Combine(r,"Validation/Completion_Checks.json"),JsonSerializer.Serialize(report,json));Console.WriteLine(JsonSerializer.Serialize(report,json));
 }
}

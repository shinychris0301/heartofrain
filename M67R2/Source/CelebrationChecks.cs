using System;using System.IO;using System.Linq;using System.Collections.Generic;using System.Text.Json;
using HeartOfTheRain.App.Journey;using HeartOfTheRain.App.Celebrations;using HeartOfTheRain.App.Localization;using HeartOfTheRain.App.Home;using HeartOfTheRain.App.LevelComplete;
class CelebrationChecks
{
 static int checks;static void Check(bool yes,string why){checks++;if(!yes)throw new Exception(why);}
 static void Main(string[] args){var output=args[0];var json=new JsonSerializerOptions{IncludeFields=true,WriteIndented=true};
 var frames=new List<object>();
 for(int v=0;v<3;v++)for(int i=0;i<=240;i++)foreach(bool reduced in new[]{false,true}){
  float time=i/60f;var p=CelebrationMotion.Daria(time,v,reduced);
  Check(p.frame>=0&&p.frame<16&&p.nextFrame>=0&&p.nextFrame<16&&p.blend>=0&&p.blend<=1,"invalid atlas pose");
  if(reduced||time>=CelebrationMotion.DariaDuration)Check(p.frame==15&&p.nextFrame==15&&p.lift==0,"settled / reduced pose moved");
  frames.Add(new{time,variant=v,reduced,pose=p});
 }
 var finale=new List<object>();for(int i=0;i<=240;i++)foreach(bool reduced in new[]{false,true})finale.Add(new{time=i/60f,reduced,pose=CelebrationMotion.Finale(i/24f,reduced)});
 File.WriteAllText(output+"/Validation/Finale_Poses.json",JsonSerializer.Serialize(finale,json));
 var scenes=new List<object>();
 foreach(var wh in new[]{(320,320),(320,480),(393,698),(430,852),(750,369),(768,1024),(1280,800)}){
  var g=CelebrationGeometry.Build(wh.Item1,wh.Item2);
  Check(g.captionX>=0&&g.captionY>=0&&g.captionX+g.captionW<=g.width&&g.captionY+g.captionH<=g.height,"caption outside viewport");
  Check(g.dariaX>=0&&g.dariaY>=0&&g.dariaX+g.dariaSize<=g.width&&g.dariaY+g.dariaSize<=g.height,"Daria outside viewport");
  Check(g.buttonW>=44&&g.buttonY+56<=g.height,"CTA bounds");
  scenes.Add(new{width=wh.Item1,height=wh.Item2,geometry=g});
 }
 for(int n=1;n<=5000;n++){
  Check(CelebrationMotion.ShouldPlayFinale(n,true,n)==(n%50==0),"chapter boundary incorrect");
  Check(!CelebrationMotion.ShouldPlayFinale(n,false,n),"replay triggered automatic finale");
  Check(!CelebrationMotion.ShouldPlayFinale(n,true,n-1),"incomplete chapter triggered finale");
 }
 for(int c=1;c<=100;c++)Check(CelebrationMotion.LastLevel(c)-CelebrationMotion.FirstLevel(c)==49,"chapter range is not 50 levels");
 var session=new CelebrationPlaybackSession();Check(session.Open()&&!session.Open(),"reentrant playback");
 session.Advance(1,true);Check(session.Elapsed==1,"active time");session.Advance(100,false);Check(session.Elapsed==1,"background consumed story");
 session.Advance(float.NaN,true);session.Advance(-1,true);Check(session.Elapsed==1,"invalid clock delta");session.Advance(100,true);Check(session.Elapsed==9.4f&&session.Active,"final frame must hold until Continue");
 Check(session.Close()&&!session.Close(),"duplicate close callback");session.Advance(1,true);Check(session.Elapsed==9.4f,"closed clock advanced");Check(session.Open()&&session.Elapsed==0,"replay restart");
 Check(CelebrationMotion.Beat(2.39f)==0&&CelebrationMotion.Beat(2.4f)==1&&CelebrationMotion.Beat(5)==2,"narrative beat boundary");
 for(int i=0;i<=240;i++){float t=i/24f;foreach(bool reduced in new[]{false,true}){float a=CelebrationMotion.DariaAlpha(t,reduced),b=CelebrationMotion.HookMix(t,reduced);Check(a>=0&&a<=1&&b>=0&&b<=1,"story alpha outside range");}}
 var h=new HomeState{currentLevel=50,completedLevelsInChapter=50};var replay=new LevelCompleteSession();replay.Arm(1,18);Check(replay.TrySettle(18,"Won",false,h,50,50,1)&&!replay.View.chapterComplete&&!replay.View.firstClear,"earlier-level replay mislabeled chapter finale");
 var chapters=new JourneyCatalog{chapters=new[]{new JourneyChapter{number=1,title="The Village Well",art="Chapter01_VillageWell",opening="Ivan returns to the village.",ending="The village well is restored. A messenger arrives with news from the city."}}};
 var reader=new JourneySession(chapters);reader.SetProgress(49);reader.Open(1);Check(!reader.Next(),"chapter ending unlocked early");
 Check(!JourneyLayout.Build(393,698,reader,true).content.elements.Any(e=>e.action=="celebration"),"locked story can replay finale");
 reader.SetProgress(50);reader.Next();
 foreach(int lang in Enumerable.Range(0,5))foreach(var size in new[]{(320,480),(393,698),(750,369),(768,1024)}){
  GameLocale.Select(lang);var layout=JourneyLayout.Build(size.Item1,size.Item2,reader,true);var watch=layout.content.elements.Single(e=>e.action=="celebration");Check(watch.width>=44&&watch.height>=44,"replay target too small");
  var button=layout.content.elements.Single(e=>e.id=="reader-next");Check(button.y>=watch.y+watch.height,"replay overlaps navigation");
 }
 Check(!JourneyLayout.Build(393,698,reader,false).content.elements.Any(e=>e.action=="celebration"),"missing chapter art exposed replay");
 var translations=new List<object>();for(int lang=0;lang<5;lang++){GameLocale.Select(lang);foreach(var row in CelebrationText.Entries){Check(row.Value.Length==5&&row.Value.All(v=>!string.IsNullOrWhiteSpace(v)),"missing localization");translations.Add(new{locale=GameLocale.Codes[lang],key=row.Key,text=CelebrationText.T(row.Key)});}}
 File.WriteAllText(output+"/Validation/Daria_Poses.json",JsonSerializer.Serialize(frames,json));
 File.WriteAllText(output+"/Validation/Cinematic_Layouts.json",JsonSerializer.Serialize(scenes,json));
 File.WriteAllText(output+"/Validation/Celebration_Translations.json",JsonSerializer.Serialize(translations,json));
 var report=new{status="PASS_PURE_CSHARP_CELEBRATION_POLICY_MOTION_AND_LAYOUT",checks,poseSamples=frames.Count,layouts=scenes.Count,languages=GameLocale.Codes,UnityAPICompilation="NOT_RUN",ShaderCompilation="NOT_RUN",DeviceTesting="NOT_RUN"};
 File.WriteAllText(output+"/Validation/Celebration_Checks.json",JsonSerializer.Serialize(report,json));Console.WriteLine(JsonSerializer.Serialize(report,json));
 }
}

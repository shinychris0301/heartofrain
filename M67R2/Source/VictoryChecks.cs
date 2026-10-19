using System;using System.IO;using System.Collections.Generic;using System.Text.Json;
using HeartOfTheRain.App.Celebrations;
class VictoryChecks
{
 static int checks;static void Check(bool yes,string why){checks++;if(!yes)throw new Exception(why);}
 static void Main(string[] args){var r=args[0];var json=new JsonSerializerOptions{IncludeFields=true,WriteIndented=true};var poses=new List<object>();var layouts=new List<object>();var particles=new List<object>();
 foreach(bool reduced in new[]{false,true})for(int i=0;i<=210;i++){float t=i/60f;var p=VictoryMotion.Sample(t,reduced);Check(p.alpha>=0&&p.alpha<=1&&p.dim<=.24f&&p.scale>0,"invalid overlay pose");poses.Add(new{time=t,reduced,pose=p});}
 for(int n=0;n<=210;n++){var list=new List<VictoryParticle>();for(int i=0;i<VictoryMotion.ParticleCount;i++)list.Add(VictoryMotion.Particle(n/60f,i,VictoryGeometry.Build(430,852),false));particles.Add(new{time=n/60f,particles=list});}
 foreach(var size in new[]{(320,320),(320,480),(393,698),(430,852),(750,369),(768,1024),(1280,800)}){
  var g=VictoryGeometry.Build(size.Item1,size.Item2);Check(g.x>=0&&g.y>=0&&g.x+g.size<=g.width&&g.y+g.size<=g.height,"character outside safe viewport");layouts.Add(new{width=size.Item1,height=size.Item2,geometry=g});
  for(int i=0;i<VictoryMotion.ParticleCount;i++)for(int t=0;t<=210;t++){var p=VictoryMotion.Particle(t/60f,i,g,false);Check(!float.IsNaN(p.x)&&!float.IsNaN(p.y)&&p.width>0&&p.height>0&&p.alpha>=0&&p.alpha<=1,"bad confetti");}
 }
 foreach(bool reduced in new[]{false,true}){
  var c=new VictoryPlaybackSession();Check(c.Open(reduced)&&!c.Open(reduced),"duplicate animation open");c.Advance(.5f,true);Check(!c.CanSkip,"unintended initial tap skip");c.Advance(30,false);Check(c.Elapsed==.5f,"background consumed celebration");c.Advance(float.NaN,true);c.Advance(float.PositiveInfinity,true);c.Advance(-1,true);Check(c.Elapsed==.5f,"invalid delta");c.Advance(.2f,true);Check(c.CanSkip,"skip unavailable");c.Advance(100,true);Check(c.Finished&&c.Active,"automatic finish gate");Check(c.Close()&&!c.Close(),"duplicate completion");Check(c.Open(reduced)&&c.Elapsed==0,"replay did not reset");
 }
 File.WriteAllText(r+"/Validation/Victory_Particles.json",JsonSerializer.Serialize(particles,json));
 File.WriteAllText(r+"/Validation/Victory_Poses.json",JsonSerializer.Serialize(poses,json));File.WriteAllText(r+"/Validation/Victory_Layouts.json",JsonSerializer.Serialize(layouts,json));
 var report=new{status="PASS_OVERLAY_GEOMETRY_PARTICLES_PLAYBACK_GATES",checks,layouts=layouts.Count,UnityAPICompilation="NOT_RUN"};File.WriteAllText(r+"/Validation/Victory_Checks.json",JsonSerializer.Serialize(report,json));Console.WriteLine(JsonSerializer.Serialize(report,json));
 }
}

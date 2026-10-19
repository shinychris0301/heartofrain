using System;using System.Linq;using System.Collections.Generic;using HeartOfTheRain.M46;
namespace HeartOfTheRain.M47 {
 [Serializable] public class FeedbackCue {public string id,haptic;public float time,gain=1;}
 public static class FeedbackPlan {
  public static List<FeedbackCue> Build(BoardStep s){
   var list=new List<FeedbackCue>();var keys=new HashSet<string>();
   void Add(string id,float t,float gain=1,string haptic=null){t=Math.Max(0,Math.Min(s.duration,t));var key=id+"/"+(int)(t/.045f);if(keys.Add(key))list.Add(new FeedbackCue{id=id,time=t,gain=gain,haptic=haptic});}
   if(s.kind=="swap")Add("tile_swap",0,.75f);
   if(s.kind=="match")Add("tile_match",.08f,.8f);
   if(s.kind=="gravity"&&s.motion.Count>0)Add("tile_land",Math.Max(0,s.duration-.1f),.65f);
   if(s.kind=="deliver")Add("jar_collect",.7f,1,"success");
   if(s.kind=="grow")Add("foliage_clear",.18f,.4f);
   if(s.kind=="shuffle")Add("atlas_shuffle",0,.6f);
   if(s.created.Any(p=>p.family=="power"))Add("power_create",.18f,.8f);
   if(s.booster!=null){var b=s.booster;
    if(b.kind==BoosterKind.Hammer){Add("hammer_swing",.58f,.8f);Add("hammer_hit",.8f,1,"impact");}
    if(b.kind==BoosterKind.Axe){Add("axe_sweep",.46f,.9f);Add("seeker_hit",.64f,.55f,"impact");}
    if(b.kind==BoosterKind.Ram){Add("ram_charge",.15f,.65f);Add("ram_hit",.64f,1,"impact");}
    if(b.kind==BoosterKind.Atlas){Add("atlas_open",.12f,.8f);Add("atlas_shuffle",.78f,.9f);Add("ui_select",2.1f,.6f,"select");}
   }
   var p=s.powerPlan;if(p!=null){int k=p.kind;float t=p.primary;
    bool orb=k==7||k==8||k==9||k==10||k==15||k==20;
    if(orb){Add("orb_spin",Math.Max(0,t-.9f),.8f);foreach(var b in p.beams??new ReviewBeam[0])Add("orb_beam",b.start,.32f);Add("orb_starlight",t,.75f,"impact");}
    else if(k==4||k==5||k==6)Add("rocket_launch",t,.9f,"impact");
    else if(k==21){Add("bomb_charge",Math.Max(0,t-.5f),.7f);Add("bomb_blast",t,1,"impact");}
    else if(k==2||k==3){Add("combo_merge",Math.Max(0,t-.8f),.7f);Add("combo_blast",t,1,"combo");}
    if(k==16||k>=17&&k<=20)Add("golden_split",Math.Max(0,p.launchTime-.25f),.7f);
    var flights=new List<ReviewFlight>(p.flights??new ReviewFlight[0]);if(p.flight!=null&&!flights.Contains(p.flight))flights.Add(p.flight);
    foreach(var f in flights){Add("seeker_launch",f.start,.5f);Add(f.payload==21?"bomb_blast":f.payload==4||f.payload==5?"rocket_launch":"seeker_hit",f.start+f.travel,.65f,"impact");}
    foreach(var b in p.blasts??new ReviewBlast[0])if(b.affectsCells)Add("bomb_blast",b.start,.45f);
   }
   foreach(var d in s.damage){string id=d.afterHP>0?"obstacle_crack":(d.family=="crate"||d.family=="cabinet")?"wood_break":(d.family=="moss"||d.family=="pod")?"foliage_clear":(d.family=="stone"||d.family=="crystal")?"stone_break":"metal_break";Add(id,d.time,.5f);}
   foreach(var c in s.collections)Add("jar_collect",c.arrival,.6f);
   return list.OrderBy(c=>c.time).ToList();
  }
 }
}

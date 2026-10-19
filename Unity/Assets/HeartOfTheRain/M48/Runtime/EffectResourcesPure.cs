using System;
using System.Collections.Generic;
using System.Linq;
using HeartOfTheRain.M46;
namespace HeartOfTheRain.M48 {
    // Describes dependencies before playback. Tests compare this with the actual sampled draws.
    public sealed class EffectResources {
        public readonly HashSet<int> powers=new HashSet<int>();
        public readonly HashSet<string> bodies=new HashSet<string>(),obstacleFamilies=new HashSet<string>();
        public static EffectResources ForSteps(IEnumerable<BoardStep> steps){
            var n=new EffectResources();
            foreach(var s in steps){
                foreach(var p in s.before.pieces.Concat(s.after.pieces)){
                    if(p.family=="power")n.powers.Add(BoardPresentation.PowerAtlas(p.power));else n.bodies.Add(BoardPresentation.BodyKey(p));
                    if(p.family=="crystal")n.obstacleFamilies.Add("crystal");
                }
                if(s.removed.Any(r=>r.piece.family=="gem")){n.powers.UnionWith(new[]{2,3,4,12});}
                if(s.created.Count>0)n.powers.Add(12);
                foreach(var d in s.damage){n.obstacleFamilies.Add(d.family);if(d.family=="pod"||d.family=="cabinet")for(int hp=Math.Max(1,d.afterHP);hp<=d.beforeHP;hp++)n.bodies.Add(d.family+"_"+hp);}
                if(s.collections.Count>0){n.bodies.Add("collectionGlint");foreach(var c in s.collections)n.bodies.Add(c.family=="pod"?"waterSpirit":"rainlight");}
                if(s.kind=="grow")n.obstacleFamilies.Add("moss");
                if(s.kind=="deliver"||s.motion.Any(m=>s.before.pieces.Any(p=>p.id==m.id&&p.family=="pail")))n.obstacleFamilies.Add("pail");
                if(s.powerPlan!=null){foreach(var e in s.powerPlan.effects??new ReviewFx[0])n.powers.Add(e.atlas);foreach(var p in s.powerPlan.powers??new ReviewPower[0])n.powers.Add(p.atlas);if((s.powerPlan.beams?.Length??0)>0)n.powers.Add(20);}
                if(s.booster!=null){n.powers.UnionWith(new[]{0,1,12,20});n.bodies.Add("booster"+s.booster.kind);if(s.booster.kind==BoosterKind.Atlas)n.powers.Add(21);}
            }return n;
        }
    }
}

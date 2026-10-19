using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace HeartOfTheRain.M46 {
    // Pure sampling layer: Unity and the offline review consume these same poses.
    [Serializable] public class DebrisPiece {public string name;public int beforeHP;public float centerX,centerY,spinMultiplier=1,scaleMultiplier=1,angleDegrees,launchDelay;}
    [Serializable] public class DebrisProfile {public DebrisPiece[] pieces;public float gravity,drag,pieceScale,canvasCells,launchSpeed,launchSpeedVariation,lift,finalSpeedMultiplier=1;}
    [Serializable] public class DrawSprite {public string bank,key;public int atlas,order;public float age,x,y,sx=1,sy=1,angle,alpha=1,glow;public bool masked,uiOverlay;public float red=1,green=1,blue=1;}
    public class TimedStep {public BoardStep step;public float start;}
    public sealed partial class BoardPresentation {
        public readonly Dictionary<string,DebrisProfile> profiles=new Dictionary<string,DebrisProfile>();
        public readonly List<TimedStep> history=new List<TimedStep>();
        public int columns,rows;public float bottom=-5,left=-1,right=11;
        public static float CameraHalfHeight(int c,int r,float aspect){return .5f*Mathf.Max(r+6.6f,(c+1.4f)/Mathf.Max(.2f,aspect));}
        public static string BodyKey(Piece p){return p.family=="crystal"?"crystalIcon":p.family=="gem"?"tile"+p.color:p.family=="pail"?"pail_Full":p.family+"_"+p.hp;}
        public static int PowerAtlas(int k){switch(k){case 4:return 9;case 5:return 10;case 7:return 19;case 11:return 29;case 16:return 40;default:return 6;}}
        public static string Idle(int atlas){return atlas==19?"OR_Idle":atlas==29?"RS_Idle":atlas==40?"GS_Idle":"Idle";}
        public static string Prefix(string f){switch(f){case "case":return "Case";case "gate":return "Sluice";case "moss":return "Overgrowth";default:return "Stone";}}
        public void Add(BoardStep step,float start){history.Add(new TimedStep{step=step,start=start});}
        public void PruneHistory(float time){
            history.RemoveAll(e=>time-e.start>HistoryLifetime(e.step));
        }
        public float HistoryLifetime(BoardStep s){
            float end=Mathf.Max(30,s.duration+1);
            if(s.powerPlan!=null){foreach(var f in s.powerPlan.effects??new ReviewFx[0])end=Mathf.Max(end,f.start+f.duration+1);foreach(var b in s.powerPlan.beams??new ReviewBeam[0])end=Mathf.Max(end,b.end+1);foreach(var p in s.powerPlan.powers??new ReviewPower[0])end=Mathf.Max(end,p.end+1);}
            foreach(var d in s.damage){DebrisProfile pr;if(!profiles.TryGetValue(d.family,out pr))continue;if(pr.gravity<=0)return float.PositiveInfinity;
                foreach(var p in pr.pieces){float scale=pr.pieceScale*p.scaleMultiplier,half=pr.canvasCells*scale*.5f;
                    // Upper bound includes bomb amplification, variation, lift and launch delay.
                    float up=d.family=="crate"?6:(Mathf.Abs(pr.launchSpeed)+2*Mathf.Abs(pr.launchSpeedVariation))*Mathf.Max(1,Mathf.Abs(pr.finalSpeedMultiplier))*1.5f+Mathf.Abs(pr.lift)+3;
                    float distance=Mathf.Max(0,d.y+Mathf.Abs(p.centerY)+half-bottom);
                    float flight=(up+Mathf.Sqrt(up*up+2*pr.gravity*distance))/pr.gravity;
                    end=Mathf.Max(end,d.time+p.launchDelay+.1f+flight+1);
                }
            }
            return end;
        }
        static DrawSprite Draw(List<DrawSprite> list,string bank,string key,float age,float x,float y,int order=10,float scale=1,int atlas=0){var d=new DrawSprite{bank=bank,key=key,age=age,x=x,y=y,order=order,sx=scale,sy=scale,atlas=atlas};list.Add(d);return d;}
        static float Ease(float t){return Mathf.SmoothStep(0,1,Mathf.Clamp01(t));}
        public List<DrawSprite> Sample(BoardStep active,BoardSnapshot idle,float time,float stepStart){
            var list=new List<DrawSprite>();float age=time-stepStart;var snapshot=active==null?idle:active.before;
            var bodies=snapshot.pieces.Select(p=>p.Copy()).ToList();
            if(active!=null){foreach(var p in active.after.pieces)if(!bodies.Any(q=>q.id==p.id))bodies.Add(p.Copy());}
            foreach(var original in bodies){var p=original.Copy();if(!p.IsAnchor)continue;if(AdvancedBody(list,p,active,age,time))continue;float scale=1,x=p.x,y=p.y,glow=0;bool visible=true;string bank="body",key=BodyKey(p);int atlas=0;float sampleAge=time;
                if(active!=null){
                    var removed=active.removed.FirstOrDefault(q=>q.piece.id==p.id);
                    if(removed!=null){float end=removed.time+(removed.cause=="obstacle"?.24f:removed.cause=="delivery"?0:.035f);if(age>=end)visible=false;}
                    var damage=active.damage.Where(q=>q.id==p.id&&age>=q.time).OrderBy(q=>q.time).LastOrDefault();
                    if(damage!=null){float da=age-damage.time;if(p.family=="crate"){if(da>=.1f){p.hp=Math.Max(1,damage.afterHP);key=BodyKey(p);}scale=1+.05f*Mathf.Sin(Mathf.Clamp01(da/.18f)*Mathf.PI);}
                        else if(da<.8f&&visible){bank="obstacle";key=p.family+"/"+Prefix(p.family)+"_Hit_"+damage.beforeHP;sampleAge=da;}
                        else {p.hp=Math.Max(1,damage.afterHP);key=BodyKey(p);}}
                    var motion=active.motion.FirstOrDefault(q=>q.id==p.id);
                    if(motion!=null){float u=Mathf.Clamp01(age/active.duration);float e=active.kind=="swap"?Ease(u):1-Mathf.Pow(1-u,3);x=motion.fromX+(motion.toX-motion.fromX)*e;y=motion.fromY+(motion.toY-motion.fromY)*e;if(active.kind=="gravity")y+=.055f*Mathf.Sin(u*Mathf.PI*2)*Mathf.Sin(u*Mathf.PI);if(p.family=="pail"&&active.kind=="gravity"){bank="obstacle";key="pail/Pail_Fall";sampleAge=age;}}
                    if(active.kind=="deliver"&&p.family=="pail"&&removed!=null){bank="obstacle";key="pail/Pail_Collect";sampleAge=age;}
                    var made=active.created.FirstOrDefault(q=>q.id==p.id);
                    if(made!=null){if(active.kind=="grow"){bank="obstacle";key="moss/Overgrowth_Grow";sampleAge=age;}else{p=made;scale=.65f+.35f*Ease(age/.22f)+.12f*Mathf.Sin(Mathf.Clamp01(age/.28f)*Mathf.PI);}}
                    if(active.kind=="shuffle"&&age>=.22f){p=active.after.pieces.First(q=>q.id==p.id);key=BodyKey(p);}
                    if(active.powerPlan!=null&&p.family=="gem"){var tile=active.powerPlan.tiles.FirstOrDefault(q=>q.x==p.x&&q.y==p.y);if(tile!=null)glow=active.powerPlan.TargetGlow(tile,age);}
                }
                if(!visible)continue;
                if(p.family=="power"){bank="power";atlas=PowerAtlas(p.power);key=Idle(atlas);sampleAge=time;}
                var body=Draw(list,bank,key,sampleAge,x,y,10,scale,atlas);body.masked=true;body.glow=glow;
                if(active!=null&&active.booster!=null)BoosterTimeline.Body(active,p,body,age);
            }
            // Effects are independent of the settling phase. Fragments survive into refill.
            foreach(var entry in history){float t=time-entry.start;if(t<0)continue;var s=entry.step;
                if(s.powerPlan!=null)PowerEffects(list,s.powerPlan,t,s);
                if(s.booster!=null)BoosterTimeline.Effects(list,s,t);
                foreach(var r in s.removed){float a=t-r.time;if(r.piece.family=="gem"&&(r.cause=="match"||r.cause=="power")&&a>=0&&a<16f/30f){int variant=(r.piece.x*7+r.piece.y*11)%3;Draw(list,"power","Tile"+r.piece.color+"_V"+variant,a,r.piece.x,r.piece.y,40,1,2+variant);if(a>=.025f)Draw(list,"power","StarBurst",a-.025f,r.piece.x,r.piece.y,45,.72f,12);}
                    if(r.cause=="delivery"&&t<1.1f)Draw(list,"obstacle","pail/Pail_Collection_FX",t,r.piece.x,r.piece.y,35);}
                foreach(var d in s.damage)ObstacleEffects(list,d,t-d.time,s);
                CollectionEffects(list,s,t);
                if(s.kind=="match")foreach(var p in s.created)if(t<.6f)Draw(list,"power","StarCreate",t,p.x,p.y,35,1,12);
            }
            return list.OrderBy(d=>d.order).ToList();
        }
        void PowerEffects(List<DrawSprite> list,ReviewPlan plan,float t,BoardStep step){
            foreach(var e in plan.effects??new ReviewFx[0]){float age=t-e.start;if(age<0||age>=e.duration)continue;var pose=plan.EffectTransform(e,age);var d=Draw(list,"power",e.clip,age,pose.x,pose.y,e.order,pose.z,e.atlas);d.angle=plan.EffectAngle(e,age);float opacity=e.ramp>0?Ease(age/e.ramp):1;
                if(e.clip=="OR_Target")opacity*=1-Ease((age-e.duration+.08f)/.08f);
                if(e.clip=="OR_Orbit"||e.clip=="OR_SpinStars"||e.clip=="DO_SpinLight"||e.clip=="DO_SpinStars")opacity*=1-Ease((age-e.duration+.075f)/.075f);
                if(e.fadeIn>0)opacity*=Ease(age/e.fadeIn);if(e.fadeOut>0)opacity*=1-Ease((age-e.duration+e.fadeOut)/e.fadeOut);d.alpha=opacity;
            }
            foreach(var b in plan.beams??new ReviewBeam[0]){float a=t-b.start;if(a<0||t>=b.end)continue;float progress=Mathf.Clamp01(a/b.travel);var start=ReviewPlan.BeamPoint(b,0);var end=ReviewPlan.BeamPoint(b,progress);float length=Vector2.Distance(start,end);float angle=Mathf.Atan2(end.y-start.y,end.x-start.x)*Mathf.Rad2Deg;
                if(length>.001f){var d=Draw(list,"power","OR_Link",a,(start.x+end.x)*.5f,(start.y+end.y)*.5f,16,1,20);d.sx=length;d.angle=angle;d.alpha=(1-Ease((a-b.travel-.025f)/.16f))*(1-Ease((t-b.end+.04f)/.04f));}
                if(a<b.travel){var d=Draw(list,"power","OR_Packet",a,end.x,end.y,18,1,20);d.angle=angle;}}
            foreach(var p in plan.powers??new ReviewPower[0]){if(t<p.begin||t>=p.end)continue;float charge=p.charge>0?Mathf.Clamp01((t-p.end+p.charge)/p.charge):0;float appear=p.begin>0?Ease((t-p.begin)/.12f):1;float x=p.x,y=p.y;
                // Approved merge sheets are authored horizontally. A vertical partner
                // moves into that visual pose; its real cell remains reserved by logic.
                if(p.begin==0&&p.y!=plan.originY&&step.removed.Count(r=>r.cause=="source")==2&&p.x==plan.originX){float u=Ease((t-.15f)/.3f);float side=plan.originX+1<columns?1:-1;x+=(plan.originX+side-x)*u;y+=(plan.originY-y)*u;}
                var d=Draw(list,"power",charge>0?"Charge":Idle(p.atlas),charge*.4f,x,y,20,(1+.13f*charge)*(.15f+.85f*appear),p.atlas);d.alpha=appear;
            }
        }
        void ObstacleEffects(List<DrawSprite> list,Damage d,float t,BoardStep step){if(t<0)return;
            if(d.family=="cabinet"){if(t<.8f)Draw(list,"obstacle","cabinet/Star_Accent",t,d.x+.5f,d.y+.5f,32,.7f);return;}
            if(d.family=="crystal"||d.family=="pod")t-=.1f;if(t<0)return;
            DebrisProfile pr;if(!profiles.TryGetValue(d.family,out pr))return;
            string accent=d.family=="crate"?"Star_Accent":d.family=="gate"?(d.beforeHP==1?"Sluice_Water_Release":"Sluice_Hit_Accent"):Prefix(d.family)+(d.beforeHP==1?"_Clear_Accent":"_Hit_Accent");
            if(d.family=="crystal")accent=d.afterHP==0?"Crystal_Final_Burst":"Crystal_Impact_Burst";
            if(d.family=="pod")accent=d.afterHP==0?"Pod_Release_Burst":"Pod_Hit_Accent";
            if(t<1)Draw(list,"obstacle",d.family+"/"+accent,t,d.x,d.y,32);
            var pieces=d.family=="crate"?pr.pieces.Take(d.beforeHP==1?8:4):pr.pieces.Where(p=>p.beforeHP==d.beforeHP);
            bool bomb=step.powerPlan!=null&&new[]{2,3,9,13,18,21}.Contains(step.powerPlan.kind),rocket=step.powerPlan!=null&&new[]{4,5,6,8,12,17}.Contains(step.powerPlan.kind),vertical=step.powerPlan!=null&&(step.powerPlan.kind==5||step.powerPlan.rocketVertical);
            int k=0;foreach(var p in pieces){int v=(d.x*31+d.y*17)%11;float a=t-p.launchDelay-.012f*(v%4);int i=k++;if(a<0)continue;float theta,speed,vx,vy,lift;
                if(d.family=="crate"){theta=Mathf.Atan2(p.centerY,p.centerX)+.24f*Mathf.Sin(i*3.1f);speed=(2+.15f*(i%4))*(bomb?1.3f:1);vx=rocket?2.5f+.16f*i:Mathf.Cos(theta)*speed;vy=Mathf.Sin(theta)*(rocket?.9f:speed);lift=.8f;}
                else {theta=p.angleDegrees*Mathf.Deg2Rad;speed=(pr.launchSpeed+pr.launchSpeedVariation*(i%3))*(d.beforeHP==1?pr.finalSpeedMultiplier:1)*(bomb?1.18f:1);vx=rocket?3.4f+.12f*i:Mathf.Cos(theta)*speed;vy=Mathf.Sin(theta)*speed*(rocket?.8f:1);lift=pr.lift;}
                if(rocket&&vertical){vx=Mathf.Cos(theta)*speed*.8f;vy=-1.2f-.09f*i;}vx*=.9f+.02f*v;vy*=.94f+.015f*v;
                float scale=pr.pieceScale*p.scaleMultiplier,half=pr.canvasCells*scale*.5f,x=d.x+p.centerX,y=d.y+p.centerY+(d.family=="crystal"?-.25f:0);
                x=Mathf.Clamp(x,left+half,right-half);vx=Mathf.Clamp(vx,(left+half-x)*pr.drag,(right-half-x)*pr.drag);
                x+=vx*(1-Mathf.Exp(-a*pr.drag))/pr.drag;y+=(vy+lift)*a-.5f*pr.gravity*a*a;
                if(y+half<bottom)continue;
                Draw(list,"obstacle",d.family+"/"+p.name,a*p.spinMultiplier*(.86f+.026f*v),x,y,43,scale);
            }
        }
        public Goal[] DisplayGoals(BoardStep step,BoardSnapshot idle,float age){
            if(step==null)return idle.goals;var goals=step.before.goals.Select(g=>new Goal{family=g.family,count=g.count}).ToArray();
            foreach(var r in step.removed)if((r.cause=="obstacle"||r.cause=="delivery")&&r.piece.family!="pod"&&r.piece.family!="cabinet"){float when=r.time+(r.cause=="obstacle"?.24f:0);if(age>=when){var g=goals.FirstOrDefault(g=>g.family==r.piece.family);if(g!=null)g.count--;}}
            foreach(var c in step.collections)if(age>=c.arrival){var g=goals.FirstOrDefault(q=>q.family==c.family);if(g!=null)g.count-=c.amount;}
            if(step.kind=="grow"&&age>=.3f){var g=goals.FirstOrDefault(q=>q.family=="moss");if(g!=null)g.count++;}return goals;
        }
    }
}

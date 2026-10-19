using System;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;
namespace HeartOfTheRain.M46 {
    // Deterministic cell-space choreography, sampled by Unity AND the review exporter.
    // No frame-count timers, coroutines or random particle placement.
    public static class BoosterTimeline {
        // Measured on the unchanged 1254x1254 PNG, in top-left pixel coordinates.
        // The contact is the outer edge of the dark steel striking face, not
        // the head center or the handle. Local sprite coordinates are Y-up.
        public static readonly Vector2 HammerGrip=new Vector2(330f/1254f-.5f,.5f-875f/1254f);
        public static readonly Vector2 HammerFace=new Vector2(1031.614286f/1254f-.5f,.5f-785.157143f/1254f);
        public const float HammerSize=2.95f,HammerContactAngle=-45f;
        static Vector2 Rotate(Vector2 v,float degrees){float a=degrees*Mathf.Deg2Rad;return new Vector2(v.x*Mathf.Cos(a)-v.y*Mathf.Sin(a),v.x*Mathf.Sin(a)+v.y*Mathf.Cos(a));}
        public static Vector2 HammerLocalToWorld(DrawSprite d,Vector2 point){return new Vector2(d.x,d.y)+Rotate(new Vector2(point.x*d.sx,point.y*d.sy),d.angle);}
        public static DrawSprite HammerPose(BoosterPlan p,float t){
            float appear=E((t-.05f)/.20f),angle;
            if(t<.58f)angle=10+38*E((t-.22f)/.36f);
            else if(t<.80f){float u=Mathf.Pow(Mathf.Clamp01((t-.58f)/.22f),2.2f);angle=48+(HammerContactAngle-48)*u;}
            else if(t<.875f)angle=HammerContactAngle;
            else if(t<1.15f)angle=HammerContactAngle+25*E((t-.875f)/.275f);
            else angle=-20-7*E((t-1.15f)/.27f);
            // The grip stays fixed during the swing. Solving this pivot from
            // the face at the contact angle places the face exactly on (x,y).
            var grip=new Vector2(p.x,p.y)-Rotate(HammerFace-HammerGrip,HammerContactAngle)*HammerSize;
            float size=HammerSize*(.9f+.1f*appear);var center=grip-Rotate(HammerGrip,angle)*size;
            return new DrawSprite{bank="body",key="boosterHammer",x=center.x,y=center.y,sx=size,sy=size,angle=angle,order=68,alpha=appear*(1-E((t-1.18f)/.24f))};
        }
        static float E(float t){return Mathf.SmoothStep(0,1,Mathf.Clamp01(t));}
        static DrawSprite Add(List<DrawSprite> a,string bank,string key,int atlas,float age,float x,float y,float sx,float sy,int order=34,float alpha=1,float angle=0){
            var d=new DrawSprite{bank=bank,key=key,atlas=atlas,age=age,x=x,y=y,sx=sx,sy=sy,order=order,alpha=alpha,angle=angle};a.Add(d);return d;
        }
        static DrawSprite FX(List<DrawSprite> a,int atlas,string key,float age,float x,float y,float scale,int order=34,float alpha=1,float angle=0){return Add(a,"power",key,atlas,age,x,y,scale,scale,order,alpha,angle);}
        static void Tint(DrawSprite d,float r,float g,float b){d.red=r;d.green=g;d.blue=b;}
        // A small, damped displacement of the board, never of the HUD.
        public static Vector2 BoardKick(IEnumerable<TimedStep> history,float time,float strength=1){
            float x=0,y=0;
            foreach(var entry in history){var p=entry.step.booster;if(p==null||p.kind==BoosterKind.Atlas)continue;float t=time-entry.start;
                float first=p.kind==BoosterKind.Hammer?.8f:.64f;
                float magnitude=p.kind==BoosterKind.Hammer?.115f:p.kind==BoosterKind.Axe?.045f:.065f;
                float a=t-first;if(a>=0&&a<.24f){float decay=Mathf.Pow(1-a/.24f,2);x+=Mathf.Sin(a*83+1.2f)*magnitude*decay;y-=Mathf.Cos(a*71)*magnitude*decay;}
            }
            return new Vector2(Mathf.Clamp(x,-.12f,.12f)*strength,Mathf.Clamp(y,-.12f,.12f)*strength);
        }
        static void Shockwave(List<DrawSprite> a,float age,float x,float y,float radius,float alpha=1){
            if(age<0||age>.38f)return;float u=Mathf.Clamp01(age/.38f),scale=.24f+radius*(1-Mathf.Pow(1-u,3));
            var ring=FX(a,20,"OR_Target",.16f,x,y,scale,55,alpha*(1-u)*(1-u));ring.sy*=.68f;
        }
        static void Link(List<DrawSprite> a,float x0,float y0,float x1,float y1,float age,float width,float alpha=1,bool teal=false){
            float dx=x1-x0,dy=y1-y0,length=Mathf.Sqrt(dx*dx+dy*dy);if(length<.01f)return;
            var d=Add(a,"power","OR_Link",20,age,(x0+x1)*.5f,(y0+y1)*.5f,length,width,31,alpha,Mathf.Atan2(dy,dx)*Mathf.Rad2Deg);if(teal)Tint(d,.62f,1,1);
        }
        public static Vector2 TilePoint(Motion m,float t){
            float u=E((t-.78f-(m.id%5)*.035f)/1.18f),s=Mathf.Sin(u*Mathf.PI);
            float dx=m.toX-m.fromX,dy=m.toY-m.fromY,len=Mathf.Max(1,Mathf.Sqrt(dx*dx+dy*dy));
            float arc=((m.id&1)==0?1:-1)*(.5f+.1f*(m.id%4));
            return new Vector2(m.fromX+dx*u-dy/len*arc*s,m.fromY+dy*u+dx/len*arc*s+.18f*s);
        }
        public static void Body(BoardStep s,Piece p,DrawSprite d,float t){
            var plan=s.booster;
            if(plan.kind==BoosterKind.Atlas){
                var m=s.motion.FirstOrDefault(q=>q.id==p.id);if(m==null)return;
                float u=Mathf.Clamp01((t-.78f-(m.id%5)*.035f)/1.18f);var point=TilePoint(m,t);d.x=point.x;d.y=point.y;
                float lift=Mathf.Sin(u*Mathf.PI);d.sx=d.sy=1+.1f*lift;d.angle=(((p.id&1)==0)?1:-1)*12*lift;
                d.glow=.24f*lift;d.order=lift>.01f?18:10;d.masked=lift<.01f;
            }else{
                var c=plan.contacts.FirstOrDefault(q=>q.x==p.x&&q.y==p.y);if(c==null||p.family=="pail")return;
                float age=t-c.time;if(age<0&&age>-.14f)d.glow=.32f*E((age+.14f)/.14f);
                if(age>=0&&age<.17f){float hit=Mathf.Sin(Mathf.Clamp01(age/.17f)*Mathf.PI);d.sx*=1+.14f*hit;d.sy*=1-.16f*hit;}
            }
        }
        static void Tool(List<DrawSprite> a,string key,float hx,float hy,float angle,float size,float alpha=1,int order=58,float stretchX=1,float stretchY=1){
            // Anchor points are measured on the approved transparent source canvases.
            float ax=key=="Axe"?.26f:key=="Ram"?.36f:0;
            float ay=key=="Axe"?.06f:key=="Ram"?-.07f:0;
            float r=angle*Mathf.Deg2Rad,dx=ax*size*stretchX,dy=ay*size*stretchY;
            Add(a,"body","booster"+key,0,0,hx-dx*Mathf.Cos(r)+dy*Mathf.Sin(r),hy-dx*Mathf.Sin(r)-dy*Mathf.Cos(r),size*stretchX,size*stretchY,order,alpha,angle);
        }
        public static string Phase(BoosterPlan p,float t){
            if(p.kind==BoosterKind.Atlas)return t<.78f?"Lift and chart the route":t<2.1f?"Curved tile flight":"Land and settle";
            float first=p.contacts.Length>0?p.contacts[0].time:.8f,last=p.contacts.Length>0?p.contacts[p.contacts.Length-1].time:first;
            return t<.3f?"Select and arrive":t<first?"Anticipation":t<last+.16f?"Impact":"Recoil and debris";
        }
        public static void Effects(List<DrawSprite> a,BoardStep s,float t){
            var p=s.booster;if(t<0||t>p.duration+.5f)return;
            if(p.kind==BoosterKind.Atlas){Atlas(a,s,t);return;}
            foreach(var c in p.contacts){
                var piece=s.before.pieces.First(q=>q.x==c.x&&q.y==c.y);if(piece.family=="pail")continue;
                if(t<c.time&&t<.63f){var ring=FX(a,20,"OR_Target",t%.4f,c.x,c.y,.72f,15,.58f*E(t/.15f));ring.masked=true;}
                float hit=t-c.time;
                // Hammer light radiates from the face beneath its opaque silhouette.
                if(hit>=0&&hit<.24f)FX(a,0,"Flash",hit*.83f,c.x,c.y,p.kind==BoosterKind.Hammer?.50f:.29f,p.kind==BoosterKind.Hammer?54:64);
                if(hit>=0&&hit<.16f)FX(a,1,"Contact",hit*.82f,c.x,c.y,p.kind==BoosterKind.Hammer?1.15f:.82f,p.kind==BoosterKind.Hammer?56:65,1,p.kind==BoosterKind.Axe?-90:0);
                if(hit>=.02f&&hit<.55f)FX(a,12,"StarBurst",(hit-.02f)*.88f,c.x,c.y,p.kind==BoosterKind.Hammer?1.42f:.92f,63);
                Shockwave(a,hit,c.x,c.y,p.kind==BoosterKind.Hammer?2.45f:1.13f,p.kind==BoosterKind.Hammer?1:.75f);
                if(p.kind==BoosterKind.Hammer&&hit>=.01f&&hit<.47f)FX(a,0,"Rays",hit-.01f,c.x,c.y,.62f,33);
            }
            if(p.kind==BoosterKind.Hammer)Hammer(a,p,t);
            else if(p.kind==BoosterKind.Axe)Axe(a,p,t);
            else Ram(a,p,t);
        }
        static void Hammer(List<DrawSprite> a,BoosterPlan p,float t){
            if(t<.05f||t>1.49f)return;
            var hero=HammerPose(p,t);
            if(t>=.58f&&t<.80f){
                for(int k=2;k>=1;k--){var ghost=HammerPose(p,Mathf.Max(.58f,t-k*.022f));ghost.order=50;ghost.alpha*=k==1?.15f:.075f;a.Add(ghost);}
                for(int k=0;k<3;k++){var from=HammerPose(p,Mathf.Max(.58f,t-(k+1)*.022f));var to=HammerPose(p,Mathf.Max(.58f,t-k*.022f));var p0=HammerLocalToWorld(from,HammerFace);var p1=HammerLocalToWorld(to,HammerFace);Link(a,p0.x,p0.y,p1.x,p1.y,t,.85f,.6f-k*.13f);}
            }
            a.Add(hero);
            if(t>.80f&&t<1.13f)FX(a,12,"StarHit1",t-.80f,p.x,p.y,1.3f,57);
        }
        static void Axe(List<DrawSprite> a,BoosterPlan p,float t){
            if(t<.04f||t>p.duration-.05f)return;
            float top=p.rows-1,hy,angle;
            if(t<.64f){float u=E((t-.08f)/.44f);hy=top+1.0f+.55f*Mathf.Sin(u*Mathf.PI);angle=10-60*u;}
            else{hy=top-(t-.64f)/.065f;angle=-50+10*Mathf.Sin(Mathf.Clamp01((t-.64f)/.5f)*Mathf.PI);}
            if(hy<-2.2f)return;
            float alpha=E((t-.04f)/.17f)*(1-E((-hy-1)/1.1f));
            if(t>=.64f){float end=Mathf.Min(top+.6f,hy+4.1f);Link(a,p.x,hy,p.x,end,t,1.75f,alpha,true);Link(a,p.x,hy,p.x,end,t,.55f,alpha);
                Link(a,p.x-.20f,hy+.65f,p.x-.20f,end,t,.38f,alpha*.7f,true);Link(a,p.x+.20f,hy+.65f,p.x+.20f,end,t,.38f,alpha*.7f,true);
                for(int k=1;k<=3;k++)Tool(a,"Axe",p.x,hy+k*.29f,angle,2.95f,alpha*.085f*(4-k),49);
                FX(a,12,"StarTrail",(t-.64f)%.3f,p.x,hy+.45f,1.10f,54,alpha,-90);
            }
            Tool(a,"Axe",p.x,hy,angle,2.95f,alpha);
        }
        static void Ram(List<DrawSprite> a,BoosterPlan p,float t){
            if(t<.04f||t>p.duration-.05f)return;
            float hx=t<.64f?-.65f-.65f*E((t-.1f)/.4f):(t-.64f)/.065f;
            float alpha=E((t-.04f)/.17f)*(1-E((hx-p.columns-.4f)/1.6f));if(alpha<=0)return;
            float sy=t<.64f?1+.22f*E((t-.25f)/.3f):1,sx=t<.64f?1-.20f*E((t-.25f)/.3f):1.12f;
            if(t>=.64f){Link(a,hx-4.3f,p.y,hx-.1f,p.y,t,1.9f,alpha);Link(a,hx-4.3f,p.y,hx-.1f,p.y,t,.60f,alpha);
                Link(a,hx-3.7f,p.y-.22f,hx-.5f,p.y-.22f,t,.44f,alpha*.8f);Link(a,hx-3.7f,p.y+.22f,hx-.5f,p.y+.22f,t,.44f,alpha*.8f);
                var glow=FX(a,1,"Jet",(t-.64f)%.4f,hx-1.6f,p.y,.95f,32,alpha);Tint(glow,.66f,.8f,1);
                for(int k=1;k<=3;k++)Tool(a,"Ram",hx-k*.3f,p.y,0,2.95f,alpha*.08f*(4-k),49);
                FX(a,12,"StarTrail",(t-.64f)%.3f,hx-1.1f,p.y,.8f,61,alpha);
            }
            Tool(a,"Ram",hx,p.y,0,2.95f,alpha,58,sx,sy);
        }
        static void Atlas(List<DrawSprite> a,BoardStep s,float t){
            var p=s.booster;if(t>p.duration)return;
            float cx=(p.columns-1)*.5f,cy=(p.rows-1)*.5f,fly=E((t-.32f)/.48f);
            // Keep the larger orbit below the portrait HUD for every supplied size.
            float parked=Mathf.Min(p.rows+.25f,cy+BoardPresentation.CameraHalfHeight(p.columns,p.rows,720f/1280)*.50f),by=cy+(parked-cy)*fly;
            float alpha=E(t/.18f)*(1-E((t-2.35f)/.35f)),size=3.0f-.45f*fly;
            if(t<.7f)FX(a,12,"StarCreate",Mathf.Max(0,t-.10f)*.75f,cx,by,size*.55f,62,alpha);
            if(t>.16f&&t<2.48f){float spin=.08f+(t-.16f)%.32f;var orbit=FX(a,21,"OR_Orbit",spin,cx,by,1.30f,49,alpha,-t*240);Tint(orbit,1,.8f,1);
                FX(a,21,"OR_SpinStars",spin,cx,by,1.18f,60,alpha,-t*240);
                for(int i=0;i<2;i++){float angle=-t*4.2f+i*Mathf.PI;float px=cx+1.50f*Mathf.Cos(angle),py=by+.90f*Mathf.Sin(angle);FX(a,12,"StarTrail",.05f+(t+i*.15f)%.22f,px,py,.65f,62,alpha,angle*Mathf.Rad2Deg-90);}
            }
            if(t>.59f&&t<1.0f)Shockwave(a,t-.59f,cx,by,1.95f,.85f);
            if(t>.78f&&t<1.11f)FX(a,12,"StarCreate",t-.78f,cx,by,1.10f,62,alpha);
            Tool(a,"Atlas",cx,by,Mathf.Sin(t*6)*4,size,alpha,58,1,1-.1f*Mathf.Sin(Mathf.Clamp01(t/.45f)*Mathf.PI));
            foreach(var m in s.motion){
                float local=t-.78f-(m.id%5)*.035f;var pos=TilePoint(m,t);
                if(local>0&&local<1.18f&&m.id%3==0){
                    var prev=TilePoint(m,t-.035f);float direction=Mathf.Atan2(pos.y-prev.y,pos.x-prev.x)*Mathf.Rad2Deg;
                    // Small tapered sprites follow the sampled curve, avoiding rigid bars.
                    for(int tail=1;tail<=4;tail++){var q=TilePoint(m,t-tail*.035f);var d=FX(a,12,"StarTrail",.08f+tail*.035f,q.x,q.y,.62f-tail*.075f,17,(1-tail*.17f),direction);Tint(d,1,.82f,1);}
                    FX(a,20,"OR_Packet",.08f,pos.x,pos.y,.50f,30,.88f,direction);
                }
                float land=local-1.18f;if(land>=0&&land<.38f&&m.id%2==0)FX(a,12,"StarHit2",land*.87f,m.toX,m.toY,.63f,31,.95f);
            }
        }
    }
}

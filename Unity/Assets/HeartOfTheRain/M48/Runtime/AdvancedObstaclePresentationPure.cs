using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace HeartOfTheRain.M46 {
    public sealed partial class BoardPresentation {
        public readonly Dictionary<string,Vector2> goalTargets=new Dictionary<string,Vector2>();
        bool AdvancedBody(List<DrawSprite> list,Piece p,BoardStep step,float age,float time){
            if(p.family!="crystal"&&p.family!="cabinet"&&p.family!="pod")return false;
            var hit=step==null?null:step.damage.Where(d=>d.id==p.id&&d.time<=age).OrderBy(d=>d.time).LastOrDefault();
            float t=hit==null?-1:age-hit.time;
            if(p.family=="crystal"){
                float height=hit==null?p.hp:CrystalHeight(hit.beforeHP,t);
                float b=height>=2?1:height>=1?.34f+.66f*(height-1):.34f*height;
                float middle=Mathf.Max(0,height-2),c=height-b-middle,bottom=p.y-.5f;
                float[] sizes={b,middle,c};string[] names={"Base","Middle","Top"};
                for(int i=0;i<3;i++){
                    if(sizes[i]>.00001f){var d=Draw(list,"obstacle","crystal/Crystal_Pulse_"+names[i],t<0?.8f:t,p.x,bottom+sizes[i]/2,10);d.sy=sizes[i];d.masked=true;}
                    bottom+=sizes[i];
                }
                return true;
            }
            if(p.family=="pod"){
                if(hit!=null&&hit.afterHP==0&&t>=.24f)return true;
                if(hit!=null&&t<.8f){var d=Draw(list,"obstacle","pod/Pod_Hit_"+hit.beforeHP,t,p.x,p.y,10);d.masked=true;}
                else {var d=Draw(list,"body","pod_"+(hit==null?p.hp:hit.afterHP),time,p.x,p.y,10);d.masked=true;}
                return true;
            }
            if(hit!=null&&hit.afterHP==0&&t>=.8f)return true;
            DrawSprite body;
            if(hit!=null&&hit.beforeHP==5&&t<.9f)body=Draw(list,"obstacle","cabinet/Cabinet_Open",t,p.x+.5f,p.y+.5f,10);
            else if(hit!=null&&hit.afterHP==0)body=Draw(list,"obstacle","cabinet/Cabinet_Clear",t,p.x+.5f,p.y+.5f,10);
            else body=Draw(list,"body","cabinet_"+(hit==null?p.hp:t<.1f?hit.beforeHP:hit.afterHP),time,p.x+.5f,p.y+.5f,10);
            body.masked=true;return true;
        }
        static float CrystalHeight(int before,float t){
            if(t<.1f)return before-.055f*Mathf.Sin(Mathf.PI*t/.1f);
            float u=Mathf.Clamp01((t-.1f)/.1f),h=before-u*u*(3-2*u);
            if(before>1&&t>=.2f&&t<.48f)h-=.045f*Mathf.Sin(Mathf.PI*(t-.2f)/.28f)*Mathf.Exp(-(t-.2f)*9);
            return Mathf.Max(0,h);
        }
        static Vector2 FlightPoint(GoalCollection c,float t,Vector2 target){
            var origin=new Vector2(c.x+c.offsetX,c.y+c.offsetY);
            float duration=c.arrival-c.launch,side=target.x<origin.x?-1:1;
            if(c.family=="pod"&&t<.28f)return new Vector2(origin.x,origin.y+.7f*Ease(t/.28f));
            float u=Ease(c.family=="pod"?(t-.28f)/(duration-.28f):t/duration),v=1-u;
            if(c.family=="pod")origin.y+=.7f;
            var a=new Vector2(origin.x+side*(c.family=="pod"?.9f:1.15f),origin.y+(c.family=="pod"?2:.85f));
            var b=new Vector2(target.x-side*1.25f,target.y+.8f);
            return new Vector2(v*v*v*origin.x+3*v*v*u*a.x+3*v*u*u*b.x+u*u*u*target.x,v*v*v*origin.y+3*v*v*u*a.y+3*v*u*u*b.y+u*u*u*target.y);
        }
        void CollectionEffects(List<DrawSprite> list,BoardStep step,float time){
            foreach(var c in step.collections){
                float age=time-c.launch,duration=c.arrival-c.launch;if(age<0||age>duration+.25f)continue;
                Vector2 target;if(!goalTargets.TryGetValue(c.family,out target))target=new Vector2((columns-1)*.5f,rows+1.6f);
                if(age>=duration){var d=Draw(list,"body","collectionGlint",0,target.x,target.y,72,.55f+.4f*Ease((age-duration)/.25f));d.alpha=1-(age-duration)/.25f;d.uiOverlay=true;continue;}
                var pos=FlightPoint(c,age,target);float u=Mathf.Clamp01(age/duration);
                var body=Draw(list,"body",c.family=="pod"?"waterSpirit":"rainlight",0,pos.x,pos.y,70,c.family=="pod"?(age<.28f?.38f+.42f*Ease(age/.28f):.8f-.38f*Ease((age-.28f)/(duration-.28f))):.55f*(1+.28f*Mathf.Sin(Mathf.PI*u))*(1-.48f*Mathf.Pow(u,5)));
                body.uiOverlay=true;body.angle=10*Mathf.Sin(age*10)*Mathf.Sin(Mathf.PI*u);
                for(int i=1;i<=3;i++){float past=age-.07f*i;if(past<0)continue;var pt=FlightPoint(c,past,target);var glint=Draw(list,"body","collectionGlint",0,pt.x,pt.y,69,.18f-.025f*i);glint.alpha=.7f-.13f*i;glint.uiOverlay=true;}
            }
        }
    }
}

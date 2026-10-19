// M46 adaptation of approved M33 choreography: actual masks/colors/targets,
// no demonstration refill or duplicate tile debris. Source PNGs are unchanged.
using System;
using System.Collections.Generic;
using UnityEngine;
using Layout = HeartOfTheRain.M46.LiveBoardInput;

namespace HeartOfTheRain.M46
{
    [Serializable] public class ReviewTile { public int x,y,tile; public float convertedAt=-1,hit=-1,destY,fallStart=99,fallDuration; public bool wood,reserved,incoming; }
    [Serializable] public class ReviewFx
    {
        public int atlas,order,flightMotion,flightIndex;public string clip;public float start,duration,x,y,scale=1,angle,vx,vy,driftX,driftY,gravity,ramp;
        public bool tween,hasPayload;public float moveX,moveY,endScale=1,payloadOffset,fadeIn,fadeOut;
    }
    [Serializable] public class ReviewFlight {public float x,y,controlX,controlY,control2X,control2Y,start,travel;public int targetX,targetY;public bool golden;public int payload=-1;}
    [Serializable] public class ReviewGoldenGroup {public int x,y,goldenCreated=2,flightCount;public float departure;}
    [Serializable] public class ReviewSeekerLaunch {public int x,y,flightIndex=-1;public float conversion,start;}
    [Serializable] public class ReviewBeam {public float x,y,start,travel,bend,end;public int targetX,targetY;}
    [Serializable] public class ReviewPower {public int atlas,x,y;public float end,charge,begin;}
    [Serializable] public class ReviewBlast {public int x,y;public float start,scale;public bool affectsCells=true;}
    [Serializable] public class ReviewPlan
    {
        public int columns,rows,kind,originX,originY;public ReviewFlight flight;public ReviewFlight[] flights;public ReviewSeekerLaunch[] seekerLaunches;public float launchTime;public bool rocketVertical;public int requestedTargetX=-1,requestedTargetY=-1;public float primary,duration=4.1f;
        public ReviewTile[] tiles;public ReviewFx[] effects;public ReviewPower[] powers;public ReviewBlast[] blasts;public ReviewBeam[] beams;public int targetColor;public float activation;
        public ReviewGoldenGroup[] goldenGroups;public int convertedCount,createdSeekers,unassignedSeekers;public float settleAfter;
        struct Hit {public float time,dx,dy;public Hit(float t,float x,float y){time=t;dx=x;dy=y;}}
        public static ReviewPlan Build(int c,int r,int kind,Vector2Int origin,bool blockers,int targetColor=5,Vector2Int? targetCell=null,bool rocketVertical=false,LiveBoardInput live=null)
        {
            if(kind>=17&&kind<=20)return GoldenSeekerComboPlan.Build(c,r,kind,origin,blockers,targetColor,targetCell,rocketVertical,live);
            c=Mathf.Clamp(c,3,15);r=Mathf.Clamp(r,3,15);kind=Mathf.Clamp(kind,0,21);bool autoColor=(kind==8||kind==9||kind==15)&&targetColor<0;targetColor=Mathf.Clamp(targetColor,0,5);
            int ox=origin.x<0?c/2:Mathf.Clamp(origin.x,0,c-1),oy=origin.y<0?r/2:Mathf.Clamp(origin.y,0,r-1),partner=live!=null?live.PartnerX:ox+1<c?ox+1:ox-1,partnerY=live!=null?live.PartnerY:oy;
            var requested=targetCell??new Vector2Int(-1,-1);ReviewFlight flight=null;var flights=new List<ReviewFlight>();var seekerLaunches=new List<ReviewSeekerLaunch>();float launchTime=0;var aimedTargets=new HashSet<int>();var covered=new HashSet<int>();var converted=new Dictionary<int,float>();var beams=new List<ReviewBeam>();int[,] grid=live!=null?live.Grid:Layout.MakeLayout(c,r);if(live!=null)covered.UnionWith(live.Obstacles);float activation=0;
            var fx=new List<ReviewFx>();var tiles=new List<ReviewTile>();var powers=new List<ReviewPower>();var blasts=new List<ReviewBlast>();var hits=new Dictionary<int,Hit>();float speed=kind==2?22:(kind==4||kind==5)?18:24;
            void Emit(int atlas,string clip,float start,float duration,float x,float y,int order=30,float scale=1,float angle=0,float vx=0,float vy=0,float dx=0,float dy=0,float gravity=0,float ramp=0)
            {fx.Add(new ReviewFx{atlas=atlas,clip=clip,start=start,duration=duration,x=x,y=y,order=order,scale=scale,angle=angle,vx=vx,vy=vy,driftX=dx,driftY=dy,gravity=gravity,ramp=ramp});}
            void Power(int atlas,int x,int y,float end,float charge=.18f,float begin=0){powers.Add(new ReviewPower{atlas=atlas,x=x,y=y,end=end,charge=charge,begin=begin});}
            void Touch(int x,int y,float t,float dx,float dy){int key=y*c+x;if(live!=null&&!live.Active.Contains(key))return;if(!hits.ContainsKey(key)||t<hits[key].time)hits[key]=new Hit(t,dx,dy);}
            void Blast(int x,int y,float t,int radius=2,float scale=1,bool affectsCells=true)
            {
                blasts.Add(new ReviewBlast{x=x,y=y,start=t,scale=scale,affectsCells=affectsCells});Emit(0,"Flash",t,.2f,x,y,26,scale);Emit(0,"Rays",t+.02f,16f/30f,x,y,27,scale);Emit(12,"StarBurst",t+.065f,14f/30f,x,y,45,scale*1.45f);
                if(!affectsCells)return;
                for(int yy=Mathf.Max(0,y-radius);yy<Mathf.Min(r,y+radius+1);yy++)for(int xx=Mathf.Max(0,x-radius);xx<Mathf.Min(c,x+radius+1);xx++)
                {float dx=xx-x,dy=yy-y,norm=Mathf.Max(.001f,Mathf.Sqrt(dx*dx+dy*dy));Touch(xx,yy,t+Mathf.Max(Mathf.Abs(dx),Mathf.Abs(dy))/40,dx/norm*.38f,dy/norm*.38f);}
            }
            void Lane(int x,int y,float t,bool vertical)
            {
                int neg=vertical?y:x,pos=vertical?r-1-y:c-1-x;
                if(kind==4||kind==5||kind==8)Emit(1,"Ignition",t,.2f,x,y,31,1,vertical?90:0);
                for(int side=0;side<2;side++)
                {
                    int sign=side==0?1:-1,limit=side==0?pos:neg;float vx=vertical?0:sign*speed,vy=vertical?sign*speed:0,angle=vertical?(sign>0?90:270):(sign>0?0:180),dur=(limit+.7f)/speed;
                    Emit(vertical?10:9,"Flight",t,dur,x,y,32,1,sign>0?0:180,vx,vy);Emit(1,"Jet",t,dur,x,y,29,kind==2?1.12f:1,angle,vx,vy);
                }
                for(int i=-neg;i<=pos;i++)
                {
                    int xx=vertical?x:x+i,yy=vertical?y+i:y,sign=i<0?-1:1,v=(xx*7+yy*11)%2;float age=t+Mathf.Abs(i)/speed,angle=vertical?(sign>0?90:270):(sign>0?0:180);
                    Emit(1,"Wake"+v,age,.4f,xx,yy,24,(.90f+.04f*((xx*3+yy*7)%4))*(kind==2?1.12f:1),angle+((xx*13+yy*5)%7-3));
                    int key=yy*c+xx;bool fresh=kind!=8||(!converted.ContainsKey(key)&&!(yy==oy&&(xx==ox||xx==partner))&&(!hits.ContainsKey(key)||age<hits[key].time));
                    if(fresh){Emit(1,"Contact",age,8f/60f,xx,yy,31,(.75f+.07f*((xx+yy)%3))*(kind==2?1.15f:1),angle);if((i+neg)%2==0)Emit(12,"StarTrail",age+.035f,10f/30f,xx,yy,44,1,angle);}
                    Touch(xx,yy,age,vertical?0:sign*.55f,vertical?sign*.55f:0);
                }
            }
            float primary;
            if(kind==21){primary=1;Power(6,ox,oy,primary);Blast(ox,oy,primary);}
            else if(kind==0){primary=1;float secondary=1+Mathf.Abs(partner-ox)/40f+.15f;Power(6,ox,oy,primary);Power(9,partner,partnerY,secondary);Blast(ox,oy,primary);Lane(partner,partnerY,secondary,false);}
            else if(kind==1){int sy=oy+2<r?oy+2:oy>=2?oy-2:(oy+1)%r;primary=1;float secondary=primary+Mathf.Abs(sy-oy)/speed+.13f;Power(10,ox,oy,primary);Power(6,ox,sy,secondary);Lane(ox,oy,primary,true);Blast(ox,sy,secondary);}
            else if(kind==7)
            {
                activation=43f/30f;var targets=new List<Vector2Int>();
                for(int y=0;y<r;y++)for(int x=0;x<c;x++)
                {bool wood=blockers&&((x-ox==-2&&y==oy)||(x-ox==1&&y-oy==1)||(x==ox&&y-oy==2));if(grid[x,y]==targetColor&&(x!=ox||y!=oy)&&!wood)targets.Add(new Vector2Int(x,y));}
                targets.Sort((a,b)=>{int da=(a.x-ox)*(a.x-ox)+(a.y-oy)*(a.y-oy),db=(b.x-ox)*(b.x-ox)+(b.y-oy)*(b.y-oy);if(da!=db)return da.CompareTo(db);return a.y!=b.y?a.y.CompareTo(b.y):a.x.CompareTo(b.x);});
                primary=activation;
                for(int k=0;k<targets.Count;k++)
                {var cell=targets[k];float distance=Vector2.Distance(new Vector2(ox,oy+.18f),cell);var b=new ReviewBeam{x=ox,y=oy+.18f,targetX=cell.x,targetY=cell.y,start=activation+k*.032f,travel=.075f+distance/65,bend=0};beams.Add(b);primary=Mathf.Max(primary,b.start+b.travel);}
                primary+=.09f;
                Emit(19,"OR_Create",.2f,.6f,ox,oy,22);Emit(19,"OR_Idle",.8f,.3f,ox,oy,22);Emit(19,"OR_Charge",1.1f,10f/30f,ox,oy,22);
                Emit(19,"OR_Channel",activation,primary-activation,ox,oy,22);Emit(19,"OR_Release",primary,8f/60f,ox,oy,22);
                Emit(20,"OR_Gather",.2f,.6f,ox,oy,19);Emit(20,"OR_Pulse",1.18f,8f/30f,ox,oy,19);Emit(20,"OR_Flash",primary,10f/60f,ox,oy,26);
                Emit(21,"OR_Orbit",activation,primary-activation,ox,oy,19,ramp:.045f);
                Emit(21,"OR_SpinStars",activation,primary-activation,ox,oy,24,ramp:.045f);
                Touch(ox,oy,primary,0,0);
                for(int k=0;k<beams.Count;k++)
                {var b=beams[k];float arrival=b.start+b.travel,contact=primary+k*.004f;b.end=contact+.06f;Emit(20,"OR_Target",arrival,contact-arrival+.035f,b.targetX,b.targetY,31);Emit(21,"OR_Hit",contact,16f/60f,b.targetX,b.targetY,36);Emit(21,"OR_Stars",contact+.025f,14f/30f,b.targetX,b.targetY,46,1,((b.targetX*17+b.targetY*11)%5-2)*12);float dx=b.targetX-ox,dy=b.targetY-oy,norm=Mathf.Max(.001f,Mathf.Sqrt(dx*dx+dy*dy));Touch(b.targetX,b.targetY,contact,dx/norm*.25f,dy/norm*.25f);}
            }
            else if(kind==8)
            {
                activation=1.25f+8f/30f;var eligible=new List<Vector2Int>();var counts=new int[6];
                for(int y=0;y<r;y++)for(int x=0;x<c;x++)
                {bool source=((y==oy&&x==ox)||(y==partnerY&&x==partner)),wood=blockers&&((x-ox==-2&&y==oy)||(x-ox==1&&y-oy==1)||(x==ox&&y-oy==2));if(!source&&!wood){if(live==null||live.CanConvert(x,y)){eligible.Add(new Vector2Int(x,y));counts[grid[x,y]]++;}}}
                if(autoColor){targetColor=0;for(int color=1;color<6;color++)if(counts[color]>counts[targetColor])targetColor=color;}
                var targets=new List<Vector2Int>();foreach(var cell in eligible)if(grid[cell.x,cell.y]==targetColor)targets.Add(cell);
                targets.Sort((a,b)=>{int da=(a.x-ox)*(a.x-ox)+(a.y-oy)*(a.y-oy),db=(b.x-ox)*(b.x-ox)+(b.y-oy)*(b.y-oy);if(da!=db)return da.CompareTo(db);return a.y!=b.y?a.y.CompareTo(b.y):a.x.CompareTo(b.x);});
                primary=activation;
                for(int k=0;k<targets.Count;k++)
                {var cell=targets[k];float start=activation+k*.024f,travel=.075f+Vector2.Distance(new Vector2(ox,oy+.18f),cell)/65,conversion=start+travel+.04f;converted[cell.y*c+cell.x]=conversion;primary=Mathf.Max(primary,conversion);beams.Add(new ReviewBeam{x=ox,y=oy+.18f,targetX=cell.x,targetY=cell.y,start=start,travel=travel,bend=0,end=conversion+.06f});}
                primary+=.24f;
                Emit(19,"OR_Idle",0,.45f,ox,oy,22);Power(9,partner,partnerY,.45f,0);
                Emit(22,(live==null?partner:live.VisualPartnerX)>ox?"ORC_Merge_Right":"ORC_Merge_Left",.45f,.8f,ox,oy,22);Emit(22,"ORC_Charge",1.25f,8f/30f,ox,oy,22);Emit(23,"ORC_Gather",.45f,.8f,ox,oy,19);
                Emit(20,"OR_Pulse",1.25f,8f/30f,ox,oy,19);Emit(19,"OR_Channel",activation,primary-activation,ox,oy,22);Emit(19,"OR_Release",primary,8f/60f,ox,oy,22);
                Emit(21,"OR_Orbit",activation,primary-activation,ox,oy,19,ramp:.045f);Emit(21,"OR_SpinStars",activation,primary-activation,ox,oy,24,ramp:.045f);Emit(20,"OR_Flash",primary,10f/60f,ox,oy,26);
                for(int k=0;k<beams.Count;k++)
                {var b=beams[k];int x=b.targetX,y=b.targetY;float arrival=b.start+b.travel,conversion=converted[y*c+x],launch=primary+k*.045f;bool vertical=(x*7+y*11+k)%2==1;
                    Emit(20,"OR_Target",arrival,.10f,x,y,31);Emit(23,"ORC_Convert",conversion-.018f,.2f,x,y,36);Emit(23,"ORC_ArmPulse",launch-8f/30f,8f/30f,x,y,19);
                    Power(vertical?10:9,x,y,launch,.16f,conversion);Emit(23,"ORC_Launch",launch,.2f,x,y,33,1,vertical?90:0);Lane(x,y,launch,vertical);
                }
                for(int k=0;k<targets.Count;k++){var cell=targets[k];hits[cell.y*c+cell.x]=new Hit(primary+k*.045f,0,0);}
                hits[oy*c+ox]=new Hit(primary,0,0);hits[partnerY*c+partner]=new Hit(primary,0,0);
            }
            else if(kind==9)
            {
                activation=1.25f+8f/30f;var eligible=new List<Vector2Int>();var counts=new int[6];
                for(int y=0;y<r;y++)for(int x=0;x<c;x++)
                {bool source=((y==oy&&x==ox)||(y==partnerY&&x==partner)),wood=blockers&&((x-ox==-2&&y==oy)||(x-ox==1&&y-oy==1)||(x==ox&&y-oy==2));if(!source&&!wood){if(live==null||live.CanConvert(x,y)){eligible.Add(new Vector2Int(x,y));counts[grid[x,y]]++;}}}
                if(autoColor){targetColor=0;for(int color=1;color<6;color++)if(counts[color]>counts[targetColor])targetColor=color;}
                var targets=new List<Vector2Int>();foreach(var cell in eligible)if(grid[cell.x,cell.y]==targetColor)targets.Add(cell);
                targets.Sort((a,b)=>{int da=(a.x-ox)*(a.x-ox)+(a.y-oy)*(a.y-oy),db=(b.x-ox)*(b.x-ox)+(b.y-oy)*(b.y-oy);if(da!=db)return da.CompareTo(db);return a.y!=b.y?a.y.CompareTo(b.y):a.x.CompareTo(b.x);});
                primary=activation;
                for(int k=0;k<targets.Count;k++)
                {var cell=targets[k];float start=activation+k*.024f,travel=.075f+Vector2.Distance(new Vector2(ox,oy+.18f),cell)/65,conversion=start+travel+.04f;converted[cell.y*c+cell.x]=conversion;primary=Mathf.Max(primary,conversion);beams.Add(new ReviewBeam{x=ox,y=oy+.18f,targetX=cell.x,targetY=cell.y,start=start,travel=travel,bend=0,end=conversion+.06f});}
                primary+=.28f;
                Emit(19,"OR_Idle",0,.45f,ox,oy,22);Power(6,partner,partnerY,.45f,0);
                Emit(24,(live==null?partner:live.VisualPartnerX)>ox?"OB_Merge_Right":"OB_Merge_Left",.45f,.8f,ox,oy,22);Emit(24,"OB_Charge",1.25f,8f/30f,ox,oy,22);Emit(25,"OB_Gather",.45f,.8f,ox,oy,19);
                Emit(20,"OR_Pulse",1.25f,8f/30f,ox,oy,19);Emit(19,"OR_Channel",activation,primary-activation,ox,oy,22);Emit(19,"OR_Release",primary,8f/60f,ox,oy,22);
                Emit(21,"OR_Orbit",activation,primary-activation,ox,oy,19,ramp:.045f);Emit(21,"OR_SpinStars",activation,primary-activation,ox,oy,24,ramp:.045f);Emit(20,"OR_Flash",primary,10f/60f,ox,oy,26);
                for(int k=0;k<beams.Count;k++)
                {var b=beams[k];int x=b.targetX,y=b.targetY;float arrival=b.start+b.travel,conversion=converted[y*c+x],launch=primary+k*.075f;
                    Emit(20,"OR_Target",arrival,.10f,x,y,31);Emit(25,"OB_Convert",conversion-.018f,.2f,x,y,36);Emit(25,"OB_ArmPulse",launch-8f/30f,8f/30f,x,y,19);
                    Power(6,x,y,launch,.22f,conversion);Emit(25,"OB_Shock",launch+.015f,20f/60f,x,y,27);Blast(x,y,launch);
                }
                for(int k=0;k<targets.Count;k++){var cell=targets[k];hits[cell.y*c+cell.x]=new Hit(primary+k*.075f,0,0);}
                hits[oy*c+ox]=new Hit(primary,0,0);hits[partnerY*c+partner]=new Hit(primary,0,0);
            }
            else if(kind==10)
            {
                float cx=(ox+(live==null?partner:live.VisualPartnerX))*.5f,cy=oy+.24f;activation=1.05f+8f/30f;primary=activation+.8f;float farthest=0;
                foreach(int x in new[]{0,c-1})foreach(int y in new[]{0,r-1})farthest=Mathf.Max(farthest,Vector2.Distance(new Vector2(cx,cy),new Vector2(x,y)));
                float waveScale=(farthest+.55f)/3.35f;
                Emit(19,"OR_Idle",0,.45f,ox,oy,22);Emit(19,"OR_Idle",0,.45f,partner,partnerY,22);
                Emit(26,(live==null?partner:live.VisualPartnerX)>ox?"DO_Merge_Right":"DO_Merge_Left",.45f,.6f,cx,oy,22);Emit(26,"DO_Charge",1.05f,8f/30f,cx,oy,22);Emit(26,"DO_Channel",activation,.8f,cx,oy,22);Emit(26,"DO_Release",primary,8f/60f,cx,oy,22);
                Emit(27,"DO_Gather",.45f,.6f,cx,oy,19);Emit(27,"DO_Pulse",1.05f,8f/30f,cx,oy,19);Emit(27,"DO_SpinLight",activation,.8f,cx,oy,19,ramp:.045f);Emit(27,"DO_SpinStars",activation,.8f,cx,oy,24,ramp:.045f);
                Emit(27,"DO_Flash",primary,14f/60f,cx,oy,26);Emit(28,"DO_Wave",primary,32f/60f,cx,cy,28,waveScale);blasts.Add(new ReviewBlast{x=ox,y=oy,start=primary,scale=1.75f,affectsCells=false});
                for(int y=0;y<r;y++)for(int x=0;x<c;x++)
                {
                    if(((y==oy&&x==ox)||(y==partnerY&&x==partner))){Touch(x,y,primary,0,0);continue;}
                    float dx=x-cx,dy=y-cy,distance=Mathf.Sqrt(dx*dx+dy*dy),u=Mathf.Clamp01((distance/waveScale-.28f)/3.07f),age=.46f*(1-Mathf.Sqrt(1-u)),contact=primary+Mathf.Ceil(age*60-.0001f)/60,norm=Mathf.Max(.001f,distance);
                    Touch(x,y,contact,dx/norm*.32f,dy/norm*.32f);Emit(21,"OR_Hit",contact,16f/60f,x,y,36,.85f);Emit(21,"OR_Stars",contact+.025f,14f/30f,x,y,46,.85f,((x*17+y*11)%5-2)*12);
                }
            }
            else if(kind==11)
            {
                float launch=32f/30f;activation=37f/30f;var cross=new HashSet<int>();
                foreach(var q in new[]{new Vector2Int(ox,oy),new Vector2Int(ox-1,oy),new Vector2Int(ox+1,oy),new Vector2Int(ox,oy-1),new Vector2Int(ox,oy+1)})if(q.x>=0&&q.x<c&&q.y>=0&&q.y<r)cross.Add(q.y*c+q.x);
                if(blockers)foreach(var q in new[]{new Vector2Int(1,r-2),new Vector2Int(c-2,r-2),new Vector2Int(c-2,1)})if(q.x!=ox||q.y!=oy)covered.Add(q.y*c+q.x);
                var candidates=new List<Vector2Int>();for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(covered.Contains(y*c+x)&&!cross.Contains(y*c+x))if(live==null||live.CanTarget(x,y))candidates.Add(new Vector2Int(x,y));
                if(candidates.Count==0)for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(!cross.Contains(y*c+x))if(live==null||live.CanTarget(x,y))candidates.Add(new Vector2Int(x,y));
                candidates.Sort((a,b)=>{int da=(a.x-ox)*(a.x-ox)+(a.y-oy)*(a.y-oy),db=(b.x-ox)*(b.x-ox)+(b.y-oy)*(b.y-oy);if(da!=db)return db.CompareTo(da);return a.y!=b.y?a.y.CompareTo(b.y):a.x.CompareTo(b.x);});
                var target=requested.x>=0&&requested.x<c&&requested.y>=0&&requested.y<r&&!cross.Contains(requested.y*c+requested.x)?requested:candidates[0];int tx=target.x,ty=target.y;
                float dx=tx-ox,dy=ty-oy,distance=Mathf.Sqrt(dx*dx+dy*dy),mx=(ox+tx)*.5f,my=(oy+ty)*.5f,nx=-dy/distance,ny=dx/distance,sign=nx*((c-1)*.5f-mx)+ny*((r-1)*.5f-my)>=0?1:-1,bend=Mathf.Min(3.2f,.32f*distance+1.10f);
                flight=new ReviewFlight{x=ox,y=oy,targetX=tx,targetY=ty,start=activation,travel=Mathf.Ceil(Mathf.Clamp(.70f+distance/20,.8f,1.4f)/.2f-1e-5f)*.2f,controlX=Mathf.Clamp(ox+.12f*dx+nx*bend*sign,.15f,c-1.15f),controlY=Mathf.Clamp(oy+.12f*dy+ny*bend*sign,.15f,r-1.15f),control2X=Mathf.Clamp(ox+.72f*dx-nx*bend*.85f*sign,.15f,c-1.15f),control2Y=Mathf.Clamp(oy+.72f*dy-ny*bend*.85f*sign,.15f,r-1.15f)};primary=activation+flight.travel;
                Emit(29,"RS_Create",.1f,.3f,ox,oy,22,1.4f);Emit(29,"RS_Idle",.4f,.4f,ox,oy,22,1.4f);Emit(29,"RS_Charge",.8f,8f/30f,ox,oy,22,1.4f);Emit(29,"RS_Lift",launch,10f/60f,ox,oy,50,1.4f);
                Emit(30,"RS_Focus",.1f,.3f,ox,oy,19,1.12f);Emit(30,"RS_Focus",.8f,8f/30f,ox,oy,19,1.4f);Emit(30,"RS_Takeoff",launch,.2f,ox,oy,26);Emit(29,"RS_Shadow",launch,10f/60f,ox,oy,16,1.05f);
                Emit(29,"RS_Flight",activation,flight.travel-12f/60f,ox,oy,50,1.4f);fx[fx.Count-1].flightMotion=1;
                Emit(29,"RS_Dive",primary-12f/60f,12f/60f,ox,oy,50,1.4f);fx[fx.Count-1].flightMotion=1;
                Emit(30,"RS_WingLight",activation,flight.travel,ox,oy,49,1.2f);fx[fx.Count-1].flightMotion=2;
                Emit(29,"RS_Shadow",activation,flight.travel,ox,oy,16);fx[fx.Count-1].flightMotion=3;
                int trailCount=Mathf.Max(2,Mathf.CeilToInt(flight.travel/.04f-1e-5f));
                for(int k=0;k<trailCount;k++){float u=(float)k/trailCount;var point=FlightPoint(flight,u);float height=FlightHeight(flight,u);Emit(30,"RS_Trail",activation+u*flight.travel,.2f,point.x,point.y+height,47,.85f);}
                Emit(20,"OR_Target",activation,flight.travel,tx,ty,31,.82f);Emit(30,"RS_Impact",primary,16f/60f,tx,ty,36);Emit(21,"OR_Stars",primary+.025f,14f/30f,tx,ty,46,.9f);
                blasts.Add(new ReviewBlast{x=ox,y=oy,start=launch,scale=.45f,affectsCells=false});blasts.Add(new ReviewBlast{x=tx,y=ty,start=primary,scale=.75f,affectsCells=false});
                for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(cross.Contains(y*c+x))
                {int ddx=x-ox,ddy=y-oy;float contact=launch+.025f*(Mathf.Abs(ddx)+Mathf.Abs(ddy));Touch(x,y,contact,ddx*.30f,ddy*.30f);if(x!=ox||y!=oy){Emit(21,"OR_Hit",contact,16f/60f,x,y,36,.55f);Emit(21,"OR_Stars",contact+.025f,14f/30f,x,y,46,.55f);}}
                Touch(tx,ty,primary,.15f*(tx-ox)/distance,.15f*(ty-oy)/distance);
            }
            else if(kind==12)
            {
                float launch=1.05f;activation=1.05f+10f/60f;var cross=new HashSet<int>();
                foreach(var q in new[]{new Vector2Int(ox,oy),new Vector2Int(ox-1,oy),new Vector2Int(ox+1,oy),new Vector2Int(ox,oy-1),new Vector2Int(ox,oy+1)})if(q.x>=0&&q.x<c&&q.y>=0&&q.y<r)cross.Add(q.y*c+q.x);
                if(blockers)foreach(var q in new[]{new Vector2Int(1,r-2),new Vector2Int(c-2,r-2),new Vector2Int(c-2,1)})if(q.y!=oy||(q.x!=ox&&q.x!=partner))covered.Add(q.y*c+q.x);
                var candidates=new List<Vector2Int>();for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(covered.Contains(y*c+x)&&!cross.Contains(y*c+x))if(live==null||live.CanTarget(x,y))candidates.Add(new Vector2Int(x,y));
                if(candidates.Count==0)for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(!cross.Contains(y*c+x))if(live==null||live.CanTarget(x,y))candidates.Add(new Vector2Int(x,y));
                candidates.Sort((a,b)=>{int da=(a.x-ox)*(a.x-ox)+(a.y-oy)*(a.y-oy),db=(b.x-ox)*(b.x-ox)+(b.y-oy)*(b.y-oy);if(da!=db)return db.CompareTo(da);return a.y!=b.y?a.y.CompareTo(b.y):a.x.CompareTo(b.x);});
                var target=requested.x>=0&&requested.x<c&&requested.y>=0&&requested.y<r&&!cross.Contains(requested.y*c+requested.x)?requested:candidates[0];int tx=target.x,ty=target.y;
                float dx=tx-ox,dy=ty-oy,distance=Mathf.Sqrt(dx*dx+dy*dy),mx=(ox+tx)*.5f,my=(oy+ty)*.5f,nx=-dy/distance,ny=dx/distance,sign=nx*((c-1)*.5f-mx)+ny*((r-1)*.5f-my)>=0?1:-1,bend=Mathf.Min(3.2f,.32f*distance+1.10f);
                flight=new ReviewFlight{x=ox,y=oy,targetX=tx,targetY=ty,start=activation,travel=Mathf.Ceil(Mathf.Clamp(.70f+distance/20,.8f,1.4f)/.2f-1e-5f)*.2f,controlX=Mathf.Clamp(ox+.12f*dx+nx*bend*sign,.15f,c-1.15f),controlY=Mathf.Clamp(oy+.12f*dy+ny*bend*sign,.15f,r-1.15f),control2X=Mathf.Clamp(ox+.72f*dx-nx*bend*.85f*sign,.15f,c-1.15f),control2Y=Mathf.Clamp(oy+.72f*dy-ny*bend*.85f*sign,.15f,r-1.15f)};primary=activation+flight.travel;
                int body=rocketVertical?32:31;string prefix=rocketVertical?"RX_V_":"RX_H_";
                Emit(29,"RS_Idle",0,.45f,ox,oy,22,1.4f);Power(rocketVertical?10:9,partner,partnerY,.45f,0);
                Emit(body,prefix+((live==null?partner:live.VisualPartnerX)>ox?"Merge_Right":"Merge_Left"),.45f,.4f,ox,oy,22,1.4f);
                Emit(body,prefix+"Charge",.85f,.2f,ox,oy,22,1.4f);Emit(body,prefix+"Lift",launch,10f/60f,ox,oy,50,1.4f);
                Emit(33,"RX_Gather",.45f,.4f,ox,oy,19);Emit(30,"RS_Focus",.85f,.2f,ox,oy,19,1.05f);Emit(33,"RX_Takeoff",launch,.2f,ox,oy,26);Emit(29,"RS_Shadow",launch,10f/60f,ox,oy,16,1.05f);
                Emit(body,prefix+"Flight",activation,flight.travel-12f/60f,ox,oy,50,1.4f);fx[fx.Count-1].flightMotion=1;
                Emit(body,prefix+"Deploy",primary-12f/60f,12f/60f,ox,oy,50,1.4f);fx[fx.Count-1].flightMotion=1;
                Emit(33,"RX_WingLight",activation,flight.travel,ox,oy,49,1.2f);fx[fx.Count-1].flightMotion=2;
                Emit(29,"RS_Shadow",activation,flight.travel,ox,oy,16);fx[fx.Count-1].flightMotion=3;
                int trailCount=Mathf.Max(2,Mathf.CeilToInt(flight.travel/.04f-1e-5f));
                for(int k=0;k<trailCount;k++){float u=(float)k/trailCount;var point=FlightPoint(flight,u);float height=FlightHeight(flight,u);Emit(30,"RS_Trail",activation+u*flight.travel,.2f,point.x,point.y+height,47,.85f);}
                Emit(20,"OR_Target",activation,flight.travel,tx,ty,31,.82f);Emit(33,"RX_Release",primary,16f/60f,tx,ty,36,1,rocketVertical?90:0);Emit(21,"OR_Stars",primary+.025f,14f/30f,tx,ty,46,1.1f);
                blasts.Add(new ReviewBlast{x=ox,y=oy,start=launch,scale=.45f,affectsCells=false});blasts.Add(new ReviewBlast{x=tx,y=ty,start=primary,scale=.75f,affectsCells=false});
                for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(cross.Contains(y*c+x))
                {int ddx=x-ox,ddy=y-oy;float contact=launch+.025f*(Mathf.Abs(ddx)+Mathf.Abs(ddy));Touch(x,y,contact,ddx*.30f,ddy*.30f);if(!((y==oy&&x==ox)||(y==partnerY&&x==partner))){Emit(21,"OR_Hit",contact,16f/60f,x,y,36,.55f);Emit(21,"OR_Stars",contact+.025f,14f/30f,x,y,46,.55f);}}
                Lane(tx,ty,primary+.035f,rocketVertical);
            }
            else if(kind==13)
            {
                float launch=1.05f;activation=1.05f+10f/60f;var cross=new HashSet<int>();
                foreach(var q in new[]{new Vector2Int(ox,oy),new Vector2Int(ox-1,oy),new Vector2Int(ox+1,oy),new Vector2Int(ox,oy-1),new Vector2Int(ox,oy+1)})if(q.x>=0&&q.x<c&&q.y>=0&&q.y<r)cross.Add(q.y*c+q.x);
                if(blockers)foreach(var q in new[]{new Vector2Int(1,r-2),new Vector2Int(c-2,r-2),new Vector2Int(c-2,1)})if(q.y!=oy||(q.x!=ox&&q.x!=partner))covered.Add(q.y*c+q.x);
                var candidates=new List<Vector2Int>();for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(covered.Contains(y*c+x)&&!cross.Contains(y*c+x))if(live==null||live.CanTarget(x,y))candidates.Add(new Vector2Int(x,y));
                if(candidates.Count==0)for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(!cross.Contains(y*c+x))if(live==null||live.CanTarget(x,y))candidates.Add(new Vector2Int(x,y));
                candidates.Sort((a,b)=>{int da=(a.x-ox)*(a.x-ox)+(a.y-oy)*(a.y-oy),db=(b.x-ox)*(b.x-ox)+(b.y-oy)*(b.y-oy);if(da!=db)return db.CompareTo(da);return a.y!=b.y?a.y.CompareTo(b.y):a.x.CompareTo(b.x);});
                var target=requested.x>=0&&requested.x<c&&requested.y>=0&&requested.y<r&&!cross.Contains(requested.y*c+requested.x)?requested:candidates[0];int tx=target.x,ty=target.y;
                float dx=tx-ox,dy=ty-oy,distance=Mathf.Sqrt(dx*dx+dy*dy),mx=(ox+tx)*.5f,my=(oy+ty)*.5f,nx=-dy/distance,ny=dx/distance,sign=nx*((c-1)*.5f-mx)+ny*((r-1)*.5f-my)>=0?1:-1,bend=Mathf.Min(3.2f,.32f*distance+1.10f);
                flight=new ReviewFlight{x=ox,y=oy,targetX=tx,targetY=ty,start=activation,travel=Mathf.Ceil(Mathf.Clamp(.70f+distance/20,.8f,1.4f)/.2f-1e-5f)*.2f,controlX=Mathf.Clamp(ox+.12f*dx+nx*bend*sign,.15f,c-1.15f),controlY=Mathf.Clamp(oy+.12f*dy+ny*bend*sign,.15f,r-1.15f),control2X=Mathf.Clamp(ox+.72f*dx-nx*bend*.85f*sign,.15f,c-1.15f),control2Y=Mathf.Clamp(oy+.72f*dy-ny*bend*.85f*sign,.15f,r-1.15f)};primary=activation+flight.travel;
                int body=34;string prefix="SB_";
                Emit(29,"RS_Idle",0,.45f,ox,oy,22,1.4f);Power(6,partner,partnerY,.45f,0);
                Emit(body,prefix+((live==null?partner:live.VisualPartnerX)>ox?"Merge_Right":"Merge_Left"),.45f,.4f,ox,oy,22,1.4f);
                Emit(body,prefix+"Charge",.85f,.2f,ox,oy,22,1.4f);Emit(body,prefix+"Lift",launch,10f/60f,ox,oy,50,1.4f);
                Emit(35,"SB_Gather",.45f,.4f,ox,oy,19);Emit(30,"RS_Focus",.85f,.2f,ox,oy,19,1.05f);Emit(35,"SB_Takeoff",launch,.2f,ox,oy,26);Emit(29,"RS_Shadow",launch,10f/60f,ox,oy,16,1.05f);
                Emit(body,prefix+"Flight",activation,flight.travel-12f/60f,ox,oy,50,1.4f);fx[fx.Count-1].flightMotion=1;
                Emit(body,prefix+"Deploy",primary-12f/60f,12f/60f,ox,oy,50,1.4f);fx[fx.Count-1].flightMotion=1;
                Emit(35,"SB_WingLight",activation,flight.travel,ox,oy,49,1.2f);fx[fx.Count-1].flightMotion=2;
                Emit(29,"RS_Shadow",activation,flight.travel,ox,oy,16);fx[fx.Count-1].flightMotion=3;
                int trailCount=Mathf.Max(2,Mathf.CeilToInt(flight.travel/.04f-1e-5f));
                for(int k=0;k<trailCount;k++){float u=(float)k/trailCount;var point=FlightPoint(flight,u);float height=FlightHeight(flight,u);Emit(30,"RS_Trail",activation+u*flight.travel,.2f,point.x,point.y+height,47,.85f);}
                Emit(20,"OR_Target",activation,flight.travel,tx,ty,31,.82f);Emit(35,"SB_Release",primary,16f/60f,tx,ty,36,1,0);
                blasts.Add(new ReviewBlast{x=ox,y=oy,start=launch,scale=.45f,affectsCells=false});
                for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(cross.Contains(y*c+x))
                {int ddx=x-ox,ddy=y-oy;float contact=launch+.025f*(Mathf.Abs(ddx)+Mathf.Abs(ddy));Touch(x,y,contact,ddx*.30f,ddy*.30f);if(!((y==oy&&x==ox)||(y==partnerY&&x==partner))){Emit(21,"OR_Hit",contact,16f/60f,x,y,36,.55f);Emit(21,"OR_Stars",contact+.025f,14f/30f,x,y,46,.55f);}}
                Blast(tx,ty,primary,2,1.1f);
            }
            else if(kind==14)
            {
                float launch=1.05f,split=launch+10f/60f,cx=(ox+partner)/2f;activation=split+.3f;
                var cross=new HashSet<int>();
                foreach(var q in new[]{new Vector2Int(ox,oy),new Vector2Int(ox-1,oy),new Vector2Int(ox+1,oy),new Vector2Int(ox,oy-1),new Vector2Int(ox,oy+1)})if(q.x>=0&&q.x<c&&q.y>=0&&q.y<r)cross.Add(q.y*c+q.x);
                if(blockers)foreach(var q in new[]{new Vector2Int(1,r-2),new Vector2Int(c-2,r-2),new Vector2Int(c-2,1)})if(q.y!=oy||(q.x!=ox&&q.x!=partner))covered.Add(q.y*c+q.x);
                var available=new List<Vector2Int>();var selected=new List<Vector2Int>();
                for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(!cross.Contains(y*c+x))if(live==null||live.CanTarget(x,y))available.Add(new Vector2Int(x,y));
                if(available.Contains(requested)){selected.Add(requested);available.Remove(requested);}
                while(selected.Count<3&&available.Count>0)
                {
                    var pool=available.FindAll(q=>covered.Contains(q.y*c+q.x));if(pool.Count==0)pool=new List<Vector2Int>(available);
                    float Spread(Vector2Int q){float best=selected.Count==0?0:float.PositiveInfinity;foreach(var v in selected)best=Mathf.Min(best,(q-v).sqrMagnitude);return best;}
                    pool.Sort((a,b)=>{int order=Spread(b).CompareTo(Spread(a));if(order!=0)return order;float da=(a.x-cx)*(a.x-cx)+(a.y-oy)*(a.y-oy),db=(b.x-cx)*(b.x-cx)+(b.y-oy)*(b.y-oy);order=db.CompareTo(da);return order!=0?order:a.y!=b.y?a.y.CompareTo(b.y):a.x.CompareTo(b.x);});
                    selected.Add(pool[0]);available.Remove(pool[0]);
                }
                selected.Sort((a,b)=>a.x!=b.x?a.x.CompareTo(b.x):a.y.CompareTo(b.y));
                Emit(29,"RS_Idle",0,.45f,ox,oy,22,1.4f);Emit(29,"RS_Idle",0,.45f,partner,partnerY,22,1.4f);
                Emit(36,"DS_Merge",.45f,.4f,cx,oy,22,1.4f);Emit(36,"DS_Charge",.85f,.2f,cx,oy,22,1.4f);
                Emit(36,"DS_Lift",launch,10f/60f,cx,oy,50,1.4f);Emit(36,"DS_Split",split,.3f,cx,oy,50,1.4f);
                Emit(37,"DS_Gather",.45f,.4f,cx,oy,19);Emit(30,"RS_Focus",.85f,.2f,cx,oy,19,1.05f);
                Emit(35,"SB_Takeoff",launch,.2f,cx,oy,26);Emit(37,"DS_SplitLight",split,16f/60f,cx,oy,49);Emit(29,"RS_Shadow",launch,10f/60f+.3f,cx,oy,16,1.05f);
                primary=0;
                for(int i=0;i<selected.Count;i++)
                {
                    int tx=selected[i].x,ty=selected[i].y;float sx=cx+(i-1)*.476f,sy=oy+(i==1?.42f:0),start=activation+i*.08f;
                    float dx=tx-sx,dy=ty-sy,distance=Mathf.Sqrt(dx*dx+dy*dy),nx=-dy/distance,ny=dx/distance,mx=(sx+tx)/2,my=(sy+ty)/2;
                    float sign=nx*((c-1)/2f-mx)+ny*((r-1)/2f-my)>=0?1:-1,bend=Mathf.Min(3.2f,.32f*distance+1.10f);
                    var f=new ReviewFlight{x=sx,y=sy,targetX=tx,targetY=ty,start=start,travel=Mathf.Ceil(Mathf.Clamp(.70f+distance/20,.8f,1.4f)/.2f-1e-5f)*.2f,controlX=Mathf.Clamp(sx+.12f*dx+nx*bend*sign,.15f,c-1.15f),controlY=Mathf.Clamp(sy+.12f*dy+ny*bend*sign,.15f,r-1.15f),control2X=Mathf.Clamp(sx+.72f*dx-nx*bend*.85f*sign,.15f,c-1.15f),control2Y=Mathf.Clamp(sy+.72f*dy-ny*bend*.85f*sign,.15f,r-1.15f)};
                    flights.Add(f);float arrival=start+f.travel;primary=Mathf.Max(primary,arrival);
                    if(i>0)Emit(29,"RS_Flight",activation,i*.08f,sx,sy+.49f,50,1.61f);
                    Emit(29,"RS_Flight",start,f.travel-.2f,sx,sy,50,1.4f);fx[fx.Count-1].flightMotion=1;fx[fx.Count-1].flightIndex=i;
                    Emit(29,"RS_Dive",arrival-.2f,.2f,sx,sy,50,1.4f);fx[fx.Count-1].flightMotion=1;fx[fx.Count-1].flightIndex=i;
                    Emit(30,"RS_WingLight",start,f.travel,sx,sy,49,1.2f);fx[fx.Count-1].flightMotion=2;fx[fx.Count-1].flightIndex=i;
                    Emit(29,"RS_Shadow",start,f.travel,sx,sy,16);fx[fx.Count-1].flightMotion=3;fx[fx.Count-1].flightIndex=i;
                    int count=Mathf.Max(2,Mathf.CeilToInt(f.travel/.04f-1e-5f));
                    for(int k=0;k<count;k++){float u=(float)k/count;var point=FlightPoint(f,u);Emit(30,"RS_Trail",start+u*f.travel,.2f,point.x,point.y+FlightHeight(f,u),47,.78f);}
                    Emit(20,"OR_Target",start,f.travel,tx,ty,31,.82f);Emit(30,"RS_Impact",arrival,16f/60f,tx,ty,36,1.12f);Emit(21,"OR_Stars",arrival+.025f,14f/30f,tx,ty,46,1.05f);
                    blasts.Add(new ReviewBlast{x=tx,y=ty,start=arrival,scale=.75f,affectsCells=false});Touch(tx,ty,arrival,dx/distance*.18f,dy/distance*.18f);
                }
                blasts.Add(new ReviewBlast{x=ox,y=oy,start=launch,scale=.50f,affectsCells=false});
                for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(cross.Contains(y*c+x))
                {int dx=x-ox,dy=y-oy;float contact=launch+.025f*(Mathf.Abs(dx)+Mathf.Abs(dy));Touch(x,y,contact,dx*.30f,dy*.30f);if(!((y==oy&&x==ox)||(y==partnerY&&x==partner))){Emit(21,"OR_Hit",contact,16f/60f,x,y,36,.55f);Emit(21,"OR_Stars",contact+.025f,14f/30f,x,y,46,.55f);}}
            }
            else if(kind==15)
            {
                activation=.85f+8f/30f;var source=new HashSet<int>{oy*c+ox,partnerY*c+partner};
                if(blockers)foreach(var q in new[]{new Vector2Int(1,r-2),new Vector2Int(c-2,r-2),new Vector2Int(c-2,1)})if(!source.Contains(q.y*c+q.x))covered.Add(q.y*c+q.x);
                var eligible=new List<Vector2Int>();var counts=new int[6];
                for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(!source.Contains(y*c+x)&&!covered.Contains(y*c+x)){if(live==null||live.CanConvert(x,y)){eligible.Add(new Vector2Int(x,y));counts[grid[x,y]]++;}}
                if(autoColor){targetColor=0;for(int color=1;color<6;color++)if(counts[color]>counts[targetColor])targetColor=color;}
                var targets=eligible.FindAll(q=>grid[q.x,q.y]==targetColor);
                targets.Sort((a,b)=>{int da=(a.x-ox)*(a.x-ox)+(a.y-oy)*(a.y-oy),db=(b.x-ox)*(b.x-ox)+(b.y-oy)*(b.y-oy);return da!=db?da.CompareTo(db):a.y!=b.y?a.y.CompareTo(b.y):a.x.CompareTo(b.x);});
                launchTime=activation;
                for(int i=0;i<targets.Count;i++)
                {var q=targets[i];float start=activation+i*.024f,travel=.075f+Vector2.Distance(new Vector2(ox,oy+.18f),q)/65,conversion=start+travel+.04f;converted[q.y*c+q.x]=conversion;launchTime=Mathf.Max(launchTime,conversion);beams.Add(new ReviewBeam{x=ox,y=oy+.18f,targetX=q.x,targetY=q.y,start=start,travel=travel,bend=0,end=conversion+.06f});}
                launchTime+=.50f;
                Emit(19,"OR_Idle",0,.85f,ox,oy,22);Emit(29,"RS_Idle",0,.45f,partner,partnerY,22,1.4f);
                Emit(38,(live==null?partner:live.VisualPartnerX)>ox?"OS_Merge_Right":"OS_Merge_Left",.45f,.4f,ox,oy,23,1.4f);Emit(39,"OS_Gather",.45f,.4f,ox,oy,19);
                Emit(19,"OR_Charge",.85f,8f/30f,ox,oy,22);Emit(20,"OR_Pulse",.85f,8f/30f,ox,oy,19);
                Emit(19,"OR_Channel",activation,launchTime-activation,ox,oy,22);Emit(19,"OR_Release",launchTime,8f/60f,ox,oy,22);
                Emit(21,"OR_Orbit",activation,launchTime-activation,ox,oy,19,ramp:.045f);Emit(21,"OR_SpinStars",activation,launchTime-activation,ox,oy,24,ramp:.045f);Emit(20,"OR_Flash",launchTime,10f/60f,ox,oy,26);
                var offsets=new[]{new Vector2Int(0,0),new Vector2Int(-1,0),new Vector2Int(1,0),new Vector2Int(0,-1),new Vector2Int(0,1)};
                var crossUnion=new HashSet<int>();foreach(var q in targets)foreach(var d in offsets){var v=q+d;if(v.x>=0&&v.x<c&&v.y>=0&&v.y<r)crossUnion.Add(v.y*c+v.x);}
                var available=new List<Vector2Int>();for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(!crossUnion.Contains(y*c+x)&&!source.Contains(y*c+x))if(live==null||live.CanTarget(x,y))available.Add(new Vector2Int(x,y));
                primary=launchTime;
                for(int i=0;i<targets.Count;i++)
                {
                    int x=targets[i].x,y=targets[i].y;var b=beams[i];float conversion=converted[y*c+x],launch=launchTime+(i/4)*.8f+(i%4)*.06f;
                    Emit(20,"OR_Target",b.start+b.travel,.10f,x,y,31);Emit(39,"OS_Convert",conversion-.018f,16f/60f,x,y,26,.85f);Emit(38,"OS_Form",conversion,.2f,x,y,22,1.4f);
                    float idleStart=conversion+.2f,chargeStart=launch-8f/30f;if(chargeStart>idleStart)Emit(29,"RS_Idle",idleStart,chargeStart-idleStart,x,y,22,1.4f);
                    Emit(29,"RS_Charge",chargeStart,8f/30f,x,y,22,1.4f);Emit(39,"OS_Launch",launch,.2f,x,y,26,.9f);
                    var record=new ReviewSeekerLaunch{x=x,y=y,conversion=conversion,start=launch};seekerLaunches.Add(record);
                    foreach(var d in offsets){int xx=x+d.x,yy=y+d.y;if(xx>=0&&xx<c&&yy>=0&&yy<r)Touch(xx,yy,launch+.025f*(Mathf.Abs(d.x)+Mathf.Abs(d.y)),d.x*.30f,d.y*.30f);}
                    if(available.Count==0){Emit(38,"OS_Dissolve",launch,8f/60f,x,y,22,1.4f);primary=Mathf.Max(primary,launch);continue;}
                    var pool=available.FindAll(q=>covered.Contains(q.y*c+q.x));if(pool.Count==0)pool=new List<Vector2Int>(available);
                    pool.Sort((a,q)=>{int da=(a.x-x)*(a.x-x)+(a.y-y)*(a.y-y),db=(q.x-x)*(q.x-x)+(q.y-y)*(q.y-y);return da!=db?db.CompareTo(da):a.y!=q.y?a.y.CompareTo(q.y):a.x.CompareTo(q.x);});
                    var target=pool[0];available.Remove(target);int tx=target.x,ty=target.y;aimedTargets.Add(ty*c+tx);
                    float start=launch+10f/60f,dx=tx-x,dy=ty-y,distance=Mathf.Sqrt(dx*dx+dy*dy),nx=-dy/distance,ny=dx/distance,mx=(x+tx)/2f,my=(y+ty)/2f;
                    float sign=nx*((c-1)/2f-mx)+ny*((r-1)/2f-my)>=0?1:-1,bend=Mathf.Min(3.2f,.32f*distance+1.10f);
                    var f=new ReviewFlight{x=x,y=y,targetX=tx,targetY=ty,start=start,travel=Mathf.Ceil(Mathf.Clamp(.70f+distance/20,.8f,1.4f)/.2f-1e-5f)*.2f,controlX=Mathf.Clamp(x+.12f*dx+nx*bend*sign,.15f,c-1.15f),controlY=Mathf.Clamp(y+.12f*dy+ny*bend*sign,.15f,r-1.15f),control2X=Mathf.Clamp(x+.72f*dx-nx*bend*.85f*sign,.15f,c-1.15f),control2Y=Mathf.Clamp(y+.72f*dy-ny*bend*.85f*sign,.15f,r-1.15f)};
                    int index=flights.Count;record.flightIndex=index;flights.Add(f);float arrival=start+f.travel;primary=Mathf.Max(primary,arrival);
                    Emit(29,"RS_Lift",launch,10f/60f,x,y,50,1.4f);Emit(29,"RS_Shadow",launch,10f/60f,x,y,16,1.05f);
                    Emit(29,"RS_Flight",start,f.travel-.2f,x,y,50,1.4f);fx[fx.Count-1].flightMotion=1;fx[fx.Count-1].flightIndex=index;
                    Emit(29,"RS_Dive",arrival-.2f,.2f,x,y,50,1.4f);fx[fx.Count-1].flightMotion=1;fx[fx.Count-1].flightIndex=index;
                    Emit(30,"RS_WingLight",start,f.travel,x,y,49,1.05f);fx[fx.Count-1].flightMotion=2;fx[fx.Count-1].flightIndex=index;
                    Emit(29,"RS_Shadow",start,f.travel,x,y,16);fx[fx.Count-1].flightMotion=3;fx[fx.Count-1].flightIndex=index;
                    int count=Mathf.Max(2,Mathf.CeilToInt(f.travel/.05f-1e-5f));for(int k=0;k<count;k++){float u=(float)k/count;var point=FlightPoint(f,u);Emit(30,"RS_Trail",start+u*f.travel,.2f,point.x,point.y+FlightHeight(f,u),47,.65f);}
                    Emit(20,"OR_Target",start,f.travel,tx,ty,31,.82f);Emit(30,"RS_Impact",arrival,16f/60f,tx,ty,36,1.12f);Emit(21,"OR_Stars",arrival+.025f,14f/30f,tx,ty,46,1.05f);
                    blasts.Add(new ReviewBlast{x=tx,y=ty,start=arrival,scale=.65f,affectsCells=false});Touch(tx,ty,arrival,dx/distance*.18f,dy/distance*.18f);
                }
                foreach(var rec in seekerLaunches)hits[rec.y*c+rec.x]=new Hit(rec.start,0,0);
                hits[oy*c+ox]=new Hit(launchTime,0,0);hits[partnerY*c+partner]=new Hit(launchTime,0,0);foreach(var hit in hits.Values)primary=Mathf.Max(primary,hit.time);
            }
            else if(kind==16)
            {
                float launch=32f/30f,split=launch+10f/60f,cx=ox;activation=split+.4f;launchTime=launch;
                var cross=new HashSet<int>();
                foreach(var q in new[]{new Vector2Int(ox,oy),new Vector2Int(ox-1,oy),new Vector2Int(ox+1,oy),new Vector2Int(ox,oy-1),new Vector2Int(ox,oy+1)})if(q.x>=0&&q.x<c&&q.y>=0&&q.y<r)cross.Add(q.y*c+q.x);
                if(blockers)foreach(var q in new[]{new Vector2Int(1,r-2),new Vector2Int(c-2,r-2),new Vector2Int(c-2,1)})if(q.y!=oy||q.x!=ox)covered.Add(q.y*c+q.x);
                var available=new List<Vector2Int>();var selected=new List<Vector2Int>();
                for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(!cross.Contains(y*c+x))if(live==null||live.CanTarget(x,y))available.Add(new Vector2Int(x,y));
                if(available.Contains(requested)){selected.Add(requested);available.Remove(requested);}
                while(selected.Count<2&&available.Count>0)
                {
                    var pool=available.FindAll(q=>covered.Contains(q.y*c+q.x));if(pool.Count==0)pool=new List<Vector2Int>(available);
                    float Spread(Vector2Int q){float best=selected.Count==0?0:float.PositiveInfinity;foreach(var v in selected)best=Mathf.Min(best,(q-v).sqrMagnitude);return best;}
                    pool.Sort((a,b)=>{int order=Spread(b).CompareTo(Spread(a));if(order!=0)return order;float da=(a.x-cx)*(a.x-cx)+(a.y-oy)*(a.y-oy),db=(b.x-cx)*(b.x-cx)+(b.y-oy)*(b.y-oy);order=db.CompareTo(da);return order!=0?order:a.y!=b.y?a.y.CompareTo(b.y):a.x.CompareTo(b.x);});
                    selected.Add(pool[0]);available.Remove(pool[0]);
                }
                selected.Sort((a,b)=>a.x!=b.x?a.x.CompareTo(b.x):a.y.CompareTo(b.y));
                Emit(40,"GS_Create",.1f,.3f,ox,oy,22,1.4f);Emit(40,"GS_Idle",.4f,.4f,ox,oy,22,1.4f);Emit(40,"GS_Charge",.8f,8f/30f,ox,oy,22,1.4f);
                Emit(40,"GS_Lift",launch,10f/60f,ox,oy,50,1.4f);Emit(41,"GS_Duplicate",split,.4f,ox,oy,50,1.4f);
                Emit(30,"RS_Focus",.1f,.3f,ox,oy,19,1.12f);Emit(30,"RS_Focus",.8f,8f/30f,ox,oy,19,1.4f);
                Emit(30,"RS_Takeoff",launch,.2f,ox,oy,26);Emit(41,"GS_TwinFlash",split,20f/60f,ox,oy,49);
                Emit(40,"GS_Shadow",launch,10f/60f+.4f,ox,oy,16,1.05f);
                primary=0;
                for(int i=0;i<selected.Count;i++)
                {
                    int tx=selected[i].x,ty=selected[i].y;float sx=cx+(i==0?-.532f:.532f),sy=oy,start=activation;
                    float dx=tx-sx,dy=ty-sy,distance=Mathf.Sqrt(dx*dx+dy*dy),nx=-dy/distance,ny=dx/distance,mx=(sx+tx)/2,my=(sy+ty)/2;
                    float sign=nx*((c-1)/2f-mx)+ny*((r-1)/2f-my)>=0?1:-1,bend=Mathf.Min(3.2f,.32f*distance+1.10f);
                    var f=new ReviewFlight{x=sx,y=sy,targetX=tx,targetY=ty,start=start,travel=Mathf.Ceil(Mathf.Clamp(.70f+distance/20,.8f,1.4f)/.2f-1e-5f)*.2f,controlX=Mathf.Clamp(sx+.12f*dx+nx*bend*sign,.15f,c-1.15f),controlY=Mathf.Clamp(sy+.12f*dy+ny*bend*sign,.15f,r-1.15f),control2X=Mathf.Clamp(sx+.72f*dx-nx*bend*.85f*sign,.15f,c-1.15f),control2Y=Mathf.Clamp(sy+.72f*dy-ny*bend*.85f*sign,.15f,r-1.15f)};
                    flights.Add(f);float arrival=start+f.travel;primary=Mathf.Max(primary,arrival);
                    Emit(40,"GS_Flight",start,f.travel-.2f,sx,sy,50,1.4f);fx[fx.Count-1].flightMotion=1;fx[fx.Count-1].flightIndex=i;
                    Emit(40,"GS_Dive",arrival-.2f,.2f,sx,sy,50,1.4f);fx[fx.Count-1].flightMotion=1;fx[fx.Count-1].flightIndex=i;
                    Emit(30,"RS_WingLight",start,f.travel,sx,sy,49,1.2f);fx[fx.Count-1].flightMotion=2;fx[fx.Count-1].flightIndex=i;
                    Emit(40,"GS_Shadow",start,f.travel,sx,sy,16);fx[fx.Count-1].flightMotion=3;fx[fx.Count-1].flightIndex=i;
                    int count=Mathf.Max(2,Mathf.CeilToInt(f.travel/.04f-1e-5f));
                    for(int k=0;k<count;k++){float u=(float)k/count;var point=FlightPoint(f,u);Emit(30,"RS_Trail",start+u*f.travel,.2f,point.x,point.y+FlightHeight(f,u),47,.78f);}
                    Emit(20,"OR_Target",start,f.travel,tx,ty,31,.82f);Emit(30,"RS_Impact",arrival,16f/60f,tx,ty,36,1);Emit(21,"OR_Stars",arrival+.025f,14f/30f,tx,ty,46,.9f);
                    blasts.Add(new ReviewBlast{x=tx,y=ty,start=arrival,scale=.75f,affectsCells=false});Touch(tx,ty,arrival,dx/distance*.15f,dy/distance*.15f);
                }
                blasts.Add(new ReviewBlast{x=ox,y=oy,start=launch,scale=.50f,affectsCells=false});
                for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(cross.Contains(y*c+x))
                {int dx=x-ox,dy=y-oy;float contact=launch+.025f*(Mathf.Abs(dx)+Mathf.Abs(dy));Touch(x,y,contact,dx*.30f,dy*.30f);if(y!=oy||x!=ox){Emit(21,"OR_Hit",contact,16f/60f,x,y,36,.55f);Emit(21,"OR_Stars",contact+.025f,14f/30f,x,y,46,.55f);}}
            }
            else if(kind==4||kind==5)
            {primary=1;bool vertical=kind==5;Power(vertical?10:9,ox,oy,primary,.22f);Lane(ox,oy,primary,vertical);}
            else if(kind==2)
            {
                primary=47f/30f;Power(6,ox,oy,.5f,0);Power(9,partner,partnerY,.5f,0);
                Emit(13,(live==null?partner:live.VisualPartnerX)>ox?"RB_Merge_Right":"RB_Merge_Left",.5f,.8f,ox,oy,22);
                Emit(13,"RB_Charge",1.3f,8f/30f,ox,oy,22);Emit(13,"RB_Release",primary,7f/60f,ox,oy,22);
                Emit(14,"RB_Gather",.5f,.8f,ox,oy,19,1,(live==null?partner:live.VisualPartnerX)>ox?0:180);Emit(14,"RB_Pulse",1.3f,8f/30f,ox,oy,19);
                Emit(14,"RB_Flash",primary,.2f,ox,oy,26);Emit(14,"RB_CrossBurst",primary+.025f,20f/30f,ox,oy,27);
                Emit(12,"StarBurst",primary+.08f,14f/30f,ox,oy,45,1.7f);
                blasts.Add(new ReviewBlast{x=ox,y=oy,start=primary,scale=1.45f,affectsCells=false});
                for(int axis=0;axis<2;axis++)for(int b=-1;b<=1;b++){bool v=axis==1;int x=v?ox+b:ox,y=v?oy:oy+b;if(x>=0&&x<c&&y>=0&&y<r)Lane(x,y,primary+.08f+Mathf.Abs(b)*.04f,v);}
            }
            else if(kind==6)
            {
                primary=1.3f;Power(9,ox,oy,.5f,0);Power(10,partner,partnerY,.5f,0);
                Emit(17,(live==null?partner:live.VisualPartnerX)>ox?"RR_Merge_Right":"RR_Merge_Left",.5f,.6f,ox,oy,22);
                Emit(17,"RR_Charge",1.1f,.2f,ox,oy,22);Emit(17,"RR_Release",primary,5f/60f,ox,oy,22);
                Emit(18,"RR_Gather",.5f,.6f,ox,oy,19,1,(live==null?partner:live.VisualPartnerX)>ox?0:180);Emit(18,"RR_Pulse",1.1f,.2f,ox,oy,19);
                Emit(18,"RR_Flash",primary,10f/60f,ox,oy,26);Emit(18,"RR_Launch",primary+.015f,14f/30f,ox,oy,27);
                Emit(12,"StarCreate",.84f,10f/30f,ox,oy,45,.85f);Emit(12,"StarBurst",primary+.045f,14f/30f,ox,oy,45,1);
                blasts.Add(new ReviewBlast{x=ox,y=oy,start=primary,scale=.8f,affectsCells=false});
                Lane(ox,oy,primary+.035f,false);Lane(ox,oy,primary+.035f,true);
            }
            else
            {
                primary=47f/30f;Power(6,ox,oy,.5f,0);Power(6,partner,partnerY,.5f,0);
                Emit(15,(live==null?partner:live.VisualPartnerX)>ox?"BB_Merge_Right":"BB_Merge_Left",.5f,.8f,ox,oy,22);
                Emit(15,"BB_Charge",1.3f,8f/30f,ox,oy,22);Emit(15,"BB_Release",primary,7f/60f,ox,oy,22);
                Emit(16,"BB_Gather",.5f,.8f,ox,oy,19,1,(live==null?partner:live.VisualPartnerX)>ox?0:180);Emit(16,"BB_Pulse",1.3f,8f/30f,ox,oy,19);
                Emit(16,"BB_Flash",primary,.2f,ox,oy,26);Emit(16,"BB_RadialBurst",primary+.025f,20f/30f,ox,oy,27);
                Emit(12,"StarBurst",primary+.07f,14f/30f,ox,oy,45,1.8f);
                blasts.Add(new ReviewBlast{x=ox,y=oy,start=primary,scale=1.8f,affectsCells=true});
                for(int yy=Mathf.Max(0,oy-3);yy<Mathf.Min(r,oy+4);yy++)for(int xx=Mathf.Max(0,ox-3);xx<Mathf.Min(c,ox+4);xx++)
                {float dx=xx-ox,dy=yy-oy,distance=Mathf.Sqrt(dx*dx+dy*dy),norm=Mathf.Max(.001f,distance);Touch(xx,yy,primary+distance/32,dx/norm*.46f,dy/norm*.46f);}
            }
            foreach(var p in powers)if(kind!=8&&(p.atlas==9||p.atlas==10)&&p.end>=1)Emit(12,"StarBurst",p.end+.03f,14f/30f,p.x,p.y,45,.65f);
            if(kind==2||kind==3)Emit(12,"StarCreate",1f,10f/30f,ox,oy,45,1);
            var reserved=new HashSet<int>();foreach(var p in powers)reserved.Add(p.y*c+p.x);if(kind==7||kind==11||kind==16)reserved.Add(oy*c+ox);if(kind==8||kind==9||kind==10||kind==12||kind==13||kind==14||kind==15){reserved.Clear();reserved.Add(oy*c+ox);reserved.Add(partnerY*c+partner);}var byCell=new ReviewTile[c,r];
            for(int y=0;y<r;y++)for(int x=0;x<c;x++)
            {
                int key=y*c+x;bool has=hits.TryGetValue(key,out Hit h),wood=(kind==11||kind==12||kind==13||kind==14||kind==15||kind==16)?covered.Contains(key):blockers&&!reserved.Contains(key)&&(has||kind==7||kind==8||kind==9)&&((x-ox==-2&&y==oy)||(x-ox==1&&y-oy==1)||(x==ox&&y-oy==2));
                var tile=new ReviewTile{x=x,y=y,tile=grid[x,y],hit=has?h.time:-1,wood=wood,reserved=reserved.Contains(key),destY=y};if(converted.TryGetValue(key,out float conversionTime))tile.convertedAt=conversionTime;tiles.Add(tile);byCell[x,y]=tile;
                if(live!=null||!has||tile.reserved||converted.ContainsKey(key))continue;int variant=(x*17+y*31+x*y)%3;
                Emit(wood?5:2+variant,wood?"Wood_V"+((x+y)%2):"Tile"+grid[x,y]+"_V"+variant,h.time,wood?.8f:16f/30f,x,y,wood?42:38,1,0,0,0,h.dx,h.dy,wood?2.1f:2.7f,.022f);
                if(kind==15&&!aimedTargets.Contains(key)){Emit(21,"OR_Hit",h.time,16f/60f,x,y,36,.55f);Emit(21,"OR_Stars",h.time+.025f,14f/30f,x,y,46,.55f);}
                if(kind!=7&&kind!=10&&kind!=11&&kind!=12&&kind!=14&&kind!=15&&kind!=16)Emit(0,"GlintHit",h.time,8f/60f,x,y,35,.14f+.015f*((x+y)%3));
                if(kind!=7&&kind!=10&&kind!=11&&kind!=12&&kind!=14&&kind!=15&&kind!=16)Emit(12,"StarHit"+variant,h.time+.025f,10f/30f,x,y,44,1,0,0,0,h.dx*.35f,h.dy*.35f);
            }
            if(live==null)for(int x=0;x<c;x++)
            {
                var survivors=new List<int>();int cleared=0;float ready=0;
                for(int y=0;y<r;y++){if(hits.TryGetValue(y*c+x,out Hit hit)){cleared++;ready=Mathf.Max(ready,hit.time);}else survivors.Add(y);}
                if(cleared==0)continue;if(kind==8||kind==9||kind==10||kind==11||kind==12||kind==13||kind==14||kind==15||kind==16){ready=0;foreach(var h in hits.Values)ready=Mathf.Max(ready,h.time);ready+=(kind==9||kind==10||kind==11||kind==12||kind==13||kind==14||kind==15||kind==16)?.18f:.12f;}else ready+=.16f;
                for(int dest=0;dest<survivors.Count;dest++){int old=survivors[dest];if(old==dest)continue;var tile=byCell[x,old];tile.destY=dest;tile.fallStart=ready;tile.fallDuration=.17f+.085f*Mathf.Sqrt(old-dest);}
                for(int k=0;k<cleared;k++){int old=r+k,dest=survivors.Count+k;tiles.Add(new ReviewTile{x=x,y=old,tile=(x*5+k*3+k/2+kind+2)%6,destY=dest,fallStart=ready+.018f*k,fallDuration=.17f+.085f*Mathf.Sqrt(old-dest),incoming=true});}
            }
            float duration=(kind==14||kind==16)?5f:(kind==11||kind==12||kind==13||kind==14)?4.6f:kind==10?5.2f:(kind==8||kind==9)?6.2f:4.1f;
            if(kind==9||kind==15){foreach(var e in fx)duration=Mathf.Max(duration,e.start+e.duration+.25f);foreach(var t in tiles)if(t.fallDuration>0)duration=Mathf.Max(duration,t.fallStart+t.fallDuration+.25f);}
            return new ReviewPlan{columns=c,rows=r,kind=kind,originX=ox,originY=oy,primary=primary,duration=duration,tiles=tiles.ToArray(),effects=fx.ToArray(),powers=powers.ToArray(),blasts=blasts.ToArray(),beams=beams.ToArray(),flight=flight,flights=flights.ToArray(),seekerLaunches=seekerLaunches.ToArray(),launchTime=launchTime,requestedTargetX=(kind==11||kind==12||kind==13||kind==14||kind==16)?requested.x:-1,requestedTargetY=(kind==11||kind==12||kind==13||kind==14||kind==16)?requested.y:-1,rocketVertical=kind==12&&rocketVertical,targetColor=(kind==10||kind==11||kind==12||kind==13||kind==14||kind==16)?-1:(kind==7||kind==8||kind==9||kind==15)?targetColor:0,activation=activation};
        }
        static void FlightPhase(ReviewFlight f,float u,out float w,out float v)
        {u=Mathf.Clamp01(u);float split=1-.2f/f.travel;w=u<=split?u/split:1;v=Mathf.Max(0,(u-split)/(1-split));}
        public static float FlightProgress(ReviewFlight f,float u)
        {FlightPhase(f,u,out float w,out float v);return v==0?.78f*w*w*(3-2*w):.78f+.22f*v*v;}
        public static float FlightHeight(ReviewFlight f,float u)
        {FlightPhase(f,u,out float w,out float v);return v==0?.49f+1.06f*Mathf.Sin(Mathf.PI*.5f*w*w*(3-2*w)):1.55f*(1-v*v);}
        public static Vector2 FlightPoint(ReviewFlight f,float u)
        {
            float s=FlightProgress(f,u),v=1-s;
            return new Vector2(v*v*v*f.x+3*v*v*s*f.controlX+3*v*s*s*f.control2X+s*s*s*f.targetX,v*v*v*f.y+3*v*v*s*f.controlY+3*v*s*s*f.control2Y+s*s*s*f.targetY);
        }
        public Vector3 EffectTransform(ReviewFx e,float age)
        {
            var result=CoreEffectTransform(e,age);
            if(e.tween)
            {
                float u=Mathf.SmoothStep(0,1,age/e.duration);
                result=new Vector3(Mathf.Lerp(e.x,e.moveX,u),Mathf.Lerp(e.y,e.moveY,u),Mathf.Lerp(e.scale,e.endScale,u));
            }
            if(e.hasPayload)
            {
                var f=flights[e.flightIndex];float u=(e.start+age-f.start)/f.travel;
                float offset=e.payloadOffset*(1-Mathf.SmoothStep(0,1,(u-.82f)/.18f)),angle=EffectAngle(e,age)*Mathf.Deg2Rad;
                result.x-=Mathf.Sin(angle)*offset;result.y+=Mathf.Cos(angle)*offset;
            }
            if(e.fadeIn>0)result.z*=.25f+.75f*Mathf.SmoothStep(0,1,age/e.fadeIn);
            return result;
        }
        Vector3 CoreEffectTransform(ReviewFx e,float age)
        {
            if(e.flightMotion>0)
            {
                var flight=(kind>=14&&kind<=20)?flights[e.flightIndex]:this.flight;
                float u=Mathf.Clamp01((e.start+age-flight.start)/flight.travel);var point=FlightPoint(flight,u);float height=FlightHeight(flight,u);
                FlightPhase(flight,u,out float w,out float v);
                if(e.flightMotion==3)return new Vector3(point.x,point.y,1.05f+.18f*Mathf.Sin(Mathf.PI*u));
                float scale=v==0?1.15f+.26f*w*w*(3-2*w):1.41f-.41f*v*v;
                return new Vector3(point.x,point.y+height,scale*e.scale);
            }
            float carry=1-Mathf.Exp(-6*age);return new Vector3(e.x+e.vx*age+e.driftX*carry,e.y+e.vy*age+e.driftY*carry-e.gravity*age*age,e.scale);
        }
        public float EffectAngle(ReviewFx e,float age)
        {
            if(kind>=11&&kind<=20&&e.flightMotion==1)
            {
                var flight=(kind>=14&&kind<=20)?flights[e.flightIndex]:this.flight;
                float u=Mathf.Clamp01((e.start+age-flight.start)/flight.travel),s=FlightProgress(flight,u),v=1-s;
                float dx=3*v*v*(flight.controlX-flight.x)+6*v*s*(flight.control2X-flight.controlX)+3*s*s*(flight.targetX-flight.control2X),dy=3*v*v*(flight.controlY-flight.y)+6*v*s*(flight.control2Y-flight.controlY)+3*s*s*(flight.targetY-flight.control2Y);
                return Mathf.Clamp(-Mathf.Atan2(dx,Mathf.Abs(dy)+.5f)*Mathf.Rad2Deg*.75f,-38,38)*Mathf.SmoothStep(0,1,u/.14f);
            }
            return e.angle;
        }
        public float TargetGlow(ReviewTile tile,float t)
        {
            if((kind>=11&&kind<=20)&&!((kind==15||kind==20)&&tile.convertedAt>=0)){var flight=(kind>=14&&kind<=20)?Array.Find(flights,f=>f.targetX==tile.x&&f.targetY==tile.y):this.flight;if(flight==null)return 0;float age=t-flight.start-.1f;if(tile.incoming||tile.reserved||tile.wood||tile.x!=flight.targetX||tile.y!=flight.targetY||age<0||t>=tile.hit+.035f)return 0;return .55f*Mathf.SmoothStep(0,1,age/.15f);}
            if(kind==10){float age=t-(primary-.22f);if(tile.incoming||tile.reserved||tile.wood||tile.hit<0||age<0||t>=tile.hit+.035f)return 0;float pulse=Mathf.Sin(age*18);return Mathf.SmoothStep(0,1,age/.22f)*(.40f+.12f*pulse*pulse);}
            if((kind!=7&&kind!=8&&kind!=9&&kind!=15&&kind!=20)||tile.incoming||tile.reserved||tile.wood||tile.hit<0)return 0;
            foreach(var b in beams)
            {
                if(b.targetX!=tile.x||b.targetY!=tile.y)continue;
                float age=t-b.start-b.travel;if(age<0||t>=(tile.convertedAt>=0?tile.convertedAt:tile.hit)+.035f)return 0;
                float pulse=Mathf.Sin(age*24);
                return Mathf.SmoothStep(0,1,age/.055f)*(.78f+.12f*pulse*pulse+.10f*Mathf.Clamp01((t-(primary-.10f))/.10f));
            }
            return 0;
        }
        public static Vector2 BeamPoint(ReviewBeam b,float u)
        {
            float dx=b.targetX-b.x,dy=b.targetY-b.y,d=Mathf.Max(.001f,Mathf.Sqrt(dx*dx+dy*dy)),arc=b.bend*4*u*(1-u);
            return new Vector2(b.x+dx*u-dy/d*arc,b.y+dy*u+dx/d*arc);
        }
        public static float FallY(ReviewTile tile,float time)
        {
            if(time<tile.fallStart||tile.fallDuration==0)return tile.y;
            float u=Mathf.Min(1,(time-tile.fallStart)/tile.fallDuration);
            if(u<.82f)return tile.y+(tile.destY-tile.y)*Mathf.Pow(u/.82f,2);
            float v=(u-.82f)/.18f;return tile.destY+.10f*Mathf.Sin(Mathf.PI*v)*(1-v);
        }
    }
}

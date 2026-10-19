// M46 adaptation of approved M33 choreography: actual masks/colors/targets,
// no demonstration refill or duplicate tile debris. Source PNGs are unchanged.
using System;
using System.Collections.Generic;
using UnityEngine;
using Layout = HeartOfTheRain.M46.LiveBoardInput;

namespace HeartOfTheRain.M46
{
    /// <summary>Deterministic Golden Seeker combinations for the existing 2D board player.
    /// One Golden source creates exactly two; created seekers never duplicate again.</summary>
    public static class GoldenSeekerComboPlan
    {
        public static ReviewPlan Build(int columns,int rows,int kind,Vector2Int origin,bool blockers,
            int targetColor=5,Vector2Int? requestedTarget=null,bool rocketVertical=false,LiveBoardInput live=null)
        {
            if(kind<17||kind>20)throw new ArgumentOutOfRangeException(nameof(kind));
            return new Builder(columns,rows,kind,origin,blockers,targetColor,requestedTarget,rocketVertical,live).Build();
        }

        sealed class Builder
        {
            readonly int c,r,kind,combo,ox,oy,partner,partnerY;readonly LiveBoardInput live;
            readonly bool vertical;
            int color;readonly bool autoColor;readonly Vector2Int requested;
            readonly int[,] grid;
            readonly HashSet<int> source=new HashSet<int>(),covered=new HashSet<int>();
            readonly List<ReviewFx> fx=new List<ReviewFx>();
            readonly List<ReviewFlight> flights=new List<ReviewFlight>();
            readonly List<ReviewBlast> blasts=new List<ReviewBlast>();
            readonly List<ReviewBeam> beams=new List<ReviewBeam>();
            readonly List<ReviewGoldenGroup> groups=new List<ReviewGoldenGroup>();
            readonly Dictionary<int,float> converted=new Dictionary<int,float>();
            readonly Dictionary<int,Hit> hits=new Dictionary<int,Hit>();
            int unassigned,created;float activation,launchTime;
            struct Hit {public float time,dx,dy;public Hit(float t,float x,float y){time=t;dx=x;dy=y;}}
            static readonly Vector2Int[] CrossOffsets={Vector2Int.zero,Vector2Int.left,Vector2Int.right,Vector2Int.down,Vector2Int.up};

            public Builder(int columns,int rows,int k,Vector2Int origin,bool blockers,int targetColor,Vector2Int? target,bool rocketVertical,LiveBoardInput live)
            {
                this.live=live;c=Mathf.Clamp(columns,3,15);r=Mathf.Clamp(rows,3,15);kind=k;combo=k-17;
                ox=origin.x<0?c/2:Mathf.Clamp(origin.x,0,c-1);oy=origin.y<0?r/2:Mathf.Clamp(origin.y,0,r-1);
                partner=live!=null?live.PartnerX:ox+1<c?ox+1:ox-1;partnerY=live!=null?live.PartnerY:oy;vertical=combo==0&&rocketVertical;
                color=Mathf.Clamp(targetColor,0,5);autoColor=targetColor<0;requested=target??new Vector2Int(-1,-1);
                grid=live!=null?live.Grid:Layout.MakeLayout(c,r);if(live!=null)covered.UnionWith(live.Obstacles);source.Add(Key(ox,oy));source.Add(Key(partner,partnerY));
                if(blockers)foreach(var q in new[]{new Vector2Int(1,r-2),new Vector2Int(c-2,r-2),new Vector2Int(c-2,1)})
                    if(!source.Contains(Key(q.x,q.y)))covered.Add(Key(q.x,q.y));
            }
            int Key(int x,int y)=>y*c+x;
            bool Inside(int x,int y)=>x>=0&&x<c&&y>=0&&y<r&&(live==null||live.Active.Contains(Key(x,y)));
            ReviewFx Emit(int atlas,string clip,float start,float duration,float x,float y,int order=30,float scale=1)
            {
                var e=new ReviewFx{atlas=atlas,clip=clip,start=start,duration=duration,x=x,y=y,order=order,scale=scale,endScale=scale};fx.Add(e);return e;
            }
            void Tween(ReviewFx e,float x,float y,float endScale){e.tween=true;e.moveX=x;e.moveY=y;e.endScale=endScale;}
            void Touch(int x,int y,float time,float dx=0,float dy=0)
            {
                if(!Inside(x,y))return;int key=Key(x,y);
                if(!hits.TryGetValue(key,out Hit old)||time<old.time)hits[key]=new Hit(time,dx,dy);
            }
            void Cross(int x,int y,float time)
            {
                foreach(var d in CrossOffsets)
                {
                    int xx=x+d.x,yy=y+d.y;if(!Inside(xx,yy))continue;int key=Key(xx,yy);
                    float t=time+.025f*(Mathf.Abs(d.x)+Mathf.Abs(d.y));bool fresh=!hits.TryGetValue(key,out Hit old)||t<old.time;
                    Touch(xx,yy,t,d.x*.30f,d.y*.30f);
                    if(fresh&&d!=Vector2Int.zero&&!source.Contains(key)&&!converted.ContainsKey(key))
                    {Emit(21,"OR_Hit",t,16f/60,xx,yy,36,.55f);Emit(21,"OR_Stars",t+.025f,14f/30,xx,yy,46,.55f);}
                }
            }
            void Bomb(int x,int y,float time)
            {
                blasts.Add(new ReviewBlast{x=x,y=y,start=time,scale=1.1f,affectsCells=true});
                Emit(0,"Flash",time,.2f,x,y,26,1.1f);Emit(0,"Rays",time+.02f,16f/30,x,y,27,1.1f);Emit(12,"StarBurst",time+.065f,14f/30,x,y,45,1.6f);
                for(int yy=Mathf.Max(0,y-2);yy<Mathf.Min(r,y+3);yy++)for(int xx=Mathf.Max(0,x-2);xx<Mathf.Min(c,x+3);xx++)
                {float dx=xx-x,dy=yy-y,n=Mathf.Max(.001f,Mathf.Sqrt(dx*dx+dy*dy));Touch(xx,yy,time+Mathf.Max(Mathf.Abs(dx),Mathf.Abs(dy))/40,dx/n*.38f,dy/n*.38f);}
            }
            void Rocket(int x,int y,float time)
            {
                int neg=vertical?y:x,pos=vertical?r-1-y:c-1-x;const float speed=24;
                Emit(1,"Ignition",time,.2f,x,y,31).angle=vertical?90:0;
                for(int side=0;side<2;side++)
                {
                    int sign=side==0?1:-1,limit=side==0?pos:neg;float vx=vertical?0:sign*speed,vy=vertical?sign*speed:0;
                    var a=Emit(vertical?10:9,"Flight",time,(limit+.7f)/speed,x,y,32);a.angle=sign>0?0:180;a.vx=vx;a.vy=vy;
                    var b=Emit(1,"Jet",time,(limit+.7f)/speed,x,y,29);b.angle=vertical?(sign>0?90:270):(sign>0?0:180);b.vx=vx;b.vy=vy;
                }
                for(int i=-neg;i<=pos;i++)
                {
                    int xx=vertical?x:x+i,yy=vertical?y+i:y,sign=i<0?-1:1;float t=time+Mathf.Abs(i)/speed,angle=vertical?(sign>0?90:270):(sign>0?0:180);
                    Emit(1,"Wake"+((xx*7+yy*11)%2),t,.4f,xx,yy,24,.95f).angle=angle;
                    Emit(1,"Contact",t,8f/60,xx,yy,31,.85f).angle=angle;
                    if((i+neg)%2==0)Emit(12,"StarTrail",t+.035f,10f/30,xx,yy,44).angle=angle;
                    Touch(xx,yy,t,vertical?0:sign*.55f,vertical?sign*.55f:0);
                }
            }
            HashSet<int> Available(HashSet<int> excluded)
            {var result=new HashSet<int>();for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(!source.Contains(Key(x,y))&&!excluded.Contains(Key(x,y)))if(live==null||live.CanTarget(x,y))result.Add(Key(x,y));return result;}
            void ExcludeCross(HashSet<int> cells,int x,int y)
            {foreach(var d in CrossOffsets)if(Inside(x+d.x,y+d.y))cells.Add(Key(x+d.x,y+d.y));}

            // Reserve before launch. Obstacle priority, target spread, distance, then row/column provide stable ties.
            List<Vector2Int> Select(HashSet<int> available,int count,float fromX,float fromY,bool differentLines=false,bool honorOverride=false)
            {
                var result=new List<Vector2Int>();
                if(honorOverride&&Inside(requested.x,requested.y)&&available.Remove(Key(requested.x,requested.y)))result.Add(requested);
                while(result.Count<count)
                {
                    int best=-1;bool bestWood=false;float bestSpread=-1,bestDistance=-1;
                    for(int y=0;y<r;y++)for(int x=0;x<c;x++)
                    {
                        int key=Key(x,y);if(!available.Contains(key))continue;
                        bool same=false;foreach(var q in result)if(differentLines&&(vertical?q.x==x:q.y==y))same=true;if(same)continue;
                        bool wood=covered.Contains(key);float spread=result.Count==0?0:float.MaxValue;
                        foreach(var q in result)spread=Mathf.Min(spread,(x-q.x)*(x-q.x)+(y-q.y)*(y-q.y));
                        float distance=(x-fromX)*(x-fromX)+(y-fromY)*(y-fromY);
                        if(best<0||(wood&&!bestWood)||(wood==bestWood&&(spread>bestSpread||(spread==bestSpread&&distance>bestDistance))))
                        {best=key;bestWood=wood;bestSpread=spread;bestDistance=distance;}
                    }
                    if(best<0)break;available.Remove(best);result.Add(new Vector2Int(best%c,best/c));
                }
                return result;
            }
            ReviewGoldenGroup GoldenPair(int x,int y,float charge,float form=-1,int payload=-1)
            {
                float lift=charge+8f/30,split=lift+10f/60,departure=split+.4f,idle=0;
                if(form>=0){Emit(40,"GS_Create",form,.3f,x,y,22,1.4f);idle=form+.3f;}
                if(charge>idle)Emit(40,"GS_Idle",idle,charge-idle,x,y,22,1.4f);
                Emit(40,"GS_Charge",charge,8f/30,x,y,22,1.4f);Emit(30,"RS_Focus",charge,8f/30,x,y,19,1.4f);
                Emit(40,"GS_Lift",lift,10f/60,x,y,50,1.4f);Emit(41,"GS_Duplicate",split,.4f,x,y,50,1.4f);
                Emit(41,"GS_TwinFlash",split,20f/60,x,y,49);Emit(30,"RS_Takeoff",lift,.2f,x,y,26);Emit(40,"GS_Shadow",lift,10f/60+.4f,x,y,16,1.05f);
                if(payload>=0)
                {
                    Tween(Emit(payload,"Idle",.45f,.35f,partner,partnerY,51),x,y-.28f,.62f);
                    Emit(payload,"Idle",.8f,lift-.8f,x,y-.28f,51,.62f);
                    Tween(Emit(payload,"Idle",lift,10f/60,x,y-.28f,51,.62f),x,y+.14f,.62f);
                    for(int i=0;i<2;i++){var e=Emit(payload,"Idle",split,.4f,x,y+.14f,51,.62f);Tween(e,x+(i==0?-.532f:.532f),y+.14f,.62f);e.fadeIn=.06f;}
                }
                var group=new ReviewGoldenGroup{x=x,y=y,departure=departure};groups.Add(group);created+=2;return group;
            }
            void Dissolve(float x,float y,float time,bool golden,int payload=-1)
            {
                unassigned++;var e=Emit(golden?40:29,golden?"GS_Flight":"RS_Flight",time,.3f,x,y+.49f,50,1.61f);e.fadeOut=.3f;
                Emit(21,"OR_Stars",time,14f/30,x,y+.49f,46,.5f);
                if(payload>=0)Emit(payload,"Idle",time,.3f,x,y+.13f,51,.713f).fadeOut=.3f;
            }
            void Flight(float sx,float sy,Vector2Int target,float start,bool golden,int payload=-1)
            {
                int tx=target.x,ty=target.y;float dx=tx-sx,dy=ty-sy,distance=Mathf.Sqrt(dx*dx+dy*dy),nx=-dy/distance,ny=dx/distance;
                float sign=nx*((c-1)*.5f-(sx+tx)*.5f)+ny*((r-1)*.5f-(sy+ty)*.5f)>=0?1:-1,bend=Mathf.Min(3.2f,.32f*distance+1.1f);
                var f=new ReviewFlight{x=sx,y=sy,targetX=tx,targetY=ty,start=start,travel=Mathf.Ceil(Mathf.Clamp(.70f+distance/20,.8f,1.4f)/.2f-1e-5f)*.2f,
                    controlX=Mathf.Clamp(sx+.12f*dx+nx*bend*sign,.15f,c-1.15f),controlY=Mathf.Clamp(sy+.12f*dy+ny*bend*sign,.15f,r-1.15f),
                    control2X=Mathf.Clamp(sx+.72f*dx-nx*bend*.85f*sign,.15f,c-1.15f),control2Y=Mathf.Clamp(sy+.72f*dy-ny*bend*.85f*sign,.15f,r-1.15f),golden=golden,payload=payload};
                int index=flights.Count;flights.Add(f);float arrival=start+f.travel;int atlas=golden?40:29;string prefix=golden?"GS":"RS";
                void Moving(int a,string clip,float t,float duration,int order,int motion,float scale)
                {var e=Emit(a,clip,t,duration,sx,sy,order,scale);e.flightMotion=motion;e.flightIndex=index;}
                Moving(atlas,prefix+"_Flight",start,f.travel-.2f,50,1,1.4f);Moving(atlas,prefix+"_Dive",arrival-.2f,.2f,50,1,1.4f);
                Moving(30,"RS_WingLight",start,f.travel,49,2,1.2f);Moving(atlas,prefix+"_Shadow",start,f.travel,16,3,1);
                if(payload>=0){Moving(payload,"Idle",start,f.travel,51,1,.62f);var e=fx[fx.Count-1];e.hasPayload=true;e.payloadOffset=-.36f;}
                int count=Mathf.CeilToInt(f.travel/.05f-1e-5f);
                for(int k=0;k<count;k++){float u=(float)k/count;var q=ReviewPlan.FlightPoint(f,u);Emit(30,"RS_Trail",start+u*f.travel,.2f,q.x,q.y+ReviewPlan.FlightHeight(f,u),47,.72f);}
                Emit(20,"OR_Target",start,f.travel,tx,ty,31,.82f);Emit(30,"RS_Impact",arrival,16f/60,tx,ty,36);Emit(21,"OR_Stars",arrival+.025f,14f/30,tx,ty,46);
                blasts.Add(new ReviewBlast{x=tx,y=ty,start=arrival,scale=.75f,affectsCells=false});Touch(tx,ty,arrival,dx/distance*.15f,dy/distance*.15f);
                if(payload==9||payload==10){Emit(33,"RX_Release",arrival,10f/60,tx,ty,48,1.2f);Rocket(tx,ty,arrival+.035f);}
                else if(payload==6){Emit(35,"SB_Release",arrival,10f/60,tx,ty,48,1.2f);Bomb(tx,ty,arrival+.035f);}
            }
            void PairFlights(ReviewGoldenGroup group,List<Vector2Int> targets,int payload=-1)
            {
                targets.Sort((a,b)=>a.x!=b.x?a.x.CompareTo(b.x):a.y.CompareTo(b.y));group.flightCount=targets.Count;
                for(int i=0;i<2;i++)
                {float sx=group.x+(i==0?-.532f:.532f);if(i<targets.Count)Flight(sx,group.y,targets[i],group.departure,true,payload);else Dissolve(sx,group.y,group.departure,true,payload);}
            }
            void BuildDirect()
            {
                int payload=combo==0?(vertical?10:9):combo==1?6:-1;
                var group=GoldenPair(ox,oy,.8f,payload:payload);float lift=group.departure-.4f-10f/60;
                if(payload>=0)Emit(payload,"Idle",0,.45f,partner,partnerY,22);
                var excluded=new HashSet<int>();ExcludeCross(excluded,ox,oy);if(combo==2)ExcludeCross(excluded,partner,partnerY);
                var targets=Select(Available(excluded),combo==2?4:2,ox,oy,combo==0,true);
                PairFlights(group,targets.GetRange(0,Mathf.Min(2,targets.Count)),payload);Cross(ox,oy,lift);Touch(partner,partnerY,lift);
                if(combo==2)
                {
                    created+=2;Emit(29,"RS_Idle",0,.8f,partner,partnerY,22,1.4f);Emit(29,"RS_Charge",.8f,8f/30,partner,partnerY,22,1.4f);
                    Emit(29,"RS_Lift",lift,10f/60,partner,partnerY,50,1.4f);Emit(41,"GS_TwinFlash",lift+10f/60,20f/60,partner,partnerY,49);
                    for(int i=0;i<2;i++)
                    {
                        float sx=partner+.30f,sy=oy+(i==0?-.55f:.55f);var e=Emit(29,"RS_Flight",lift+10f/60,.4f,partner,partnerY+.49f,50,1.61f);Tween(e,sx,sy+.49f,1.61f);e.fadeIn=.05f;
                        if(i+2<targets.Count)Flight(sx,sy,targets[i+2],group.departure,false);else Dissolve(sx,sy,group.departure,false);
                    }
                    Cross(partner,partnerY,lift);
                }
                activation=group.departure;launchTime=lift;
            }
            void BuildOrb()
            {
                activation=.85f+8f/30;var eligible=new List<Vector2Int>();var counts=new int[6];
                for(int y=0;y<r;y++)for(int x=0;x<c;x++)if(!source.Contains(Key(x,y))&&!covered.Contains(Key(x,y)))
                {if(live==null||live.CanConvert(x,y)){eligible.Add(new Vector2Int(x,y));counts[grid[x,y]]++;}}
                if(autoColor){color=0;for(int k=1;k<6;k++)if(counts[k]>counts[color])color=k;}
                var targets=eligible.FindAll(q=>grid[q.x,q.y]==color);
                targets.Sort((a,b)=>{int da=(a.x-ox)*(a.x-ox)+(a.y-oy)*(a.y-oy),db=(b.x-ox)*(b.x-ox)+(b.y-oy)*(b.y-oy);return da!=db?da.CompareTo(db):a.y!=b.y?a.y.CompareTo(b.y):a.x.CompareTo(b.x);});
                Emit(19,"OR_Idle",0,.85f,ox,oy,22);Emit(40,"GS_Idle",0,.45f,partner,partnerY,22,1.4f);
                Tween(Emit(40,"GS_Idle",.45f,.4f,partner,partnerY,23,1.4f),ox,oy,.25f);Emit(39,"OS_Gather",.45f,.4f,ox,oy,19);
                Emit(19,"OR_Charge",.85f,8f/30,ox,oy,22);Emit(20,"OR_Pulse",.85f,8f/30,ox,oy,19);
                float lastConversion=activation;
                for(int i=0;i<targets.Count;i++)
                {
                    var q=targets[i];float start=activation+i*.024f,travel=.075f+Vector2.Distance(new Vector2(ox,oy),q)/65,conversion=start+travel+.04f;
                    converted[Key(q.x,q.y)]=conversion;lastConversion=Mathf.Max(lastConversion,conversion);
                    beams.Add(new ReviewBeam{x=ox,y=oy+.18f,targetX=q.x,targetY=q.y,start=start,travel=travel,bend=0,end=conversion+.06f});
                    Emit(20,"OR_Target",start+travel,.10f,q.x,q.y,31);Emit(39,"OS_Convert",conversion-.018f,16f/60,q.x,q.y,26,.85f);
                }
                float firstCharge=lastConversion+.36f,firstDeparture=firstCharge+8f/30+10f/60+.4f;launchTime=firstDeparture;
                Emit(19,"OR_Channel",activation,firstDeparture-activation,ox,oy,22);Emit(19,"OR_Release",firstDeparture,8f/60,ox,oy,22);
                Emit(21,"OR_Orbit",activation,firstDeparture-activation,ox,oy,19).ramp=.045f;Emit(21,"OR_SpinStars",activation,firstDeparture-activation,ox,oy,24).ramp=.045f;
                Emit(20,"OR_Flash",firstDeparture,10f/60,ox,oy,26);
                var excluded=new HashSet<int>();foreach(var q in targets)ExcludeCross(excluded,q.x,q.y);var available=Available(excluded);
                for(int i=0;i<targets.Count;i++)
                {
                    var q=targets[i];float charge=firstCharge+(i/2)*.8f+(i%2)*.08f;
                    var group=GoldenPair(q.x,q.y,charge,converted[Key(q.x,q.y)]);Cross(q.x,q.y,group.departure-.4f-10f/60);
                    PairFlights(group,Select(available,2,q.x,q.y));
                }
                // Converted sources stay protected until their own scheduled launch.
                foreach(var g in groups)hits[Key(g.x,g.y)]=new Hit(g.departure-.4f-10f/60,0,0);
                Touch(ox,oy,firstDeparture);Touch(partner,partnerY,firstDeparture);
            }
            public ReviewPlan Build()
            {
                if(combo==3)BuildOrb();else BuildDirect();
                float primary=0,lastDeparture=0;foreach(var h in hits.Values)primary=Mathf.Max(primary,h.time);foreach(var g in groups)lastDeparture=Mathf.Max(lastDeparture,g.departure);
                // Overlapping bombs may clear the second destination early; the second carrier must still arrive and release.
                foreach(var f in flights)primary=Mathf.Max(primary,f.start+f.travel);
                foreach(var b in blasts)if(b.affectsCells)primary=Mathf.Max(primary,b.start+.05f);
                // Exhausted targets still finish their visible creation/fade before the board settles.
                float ready=Mathf.Max(primary+.18f,unassigned>0?lastDeparture+.3f:0);
                var tiles=new List<ReviewTile>();var byCell=new ReviewTile[c,r];
                for(int y=0;y<r;y++)for(int x=0;x<c;x++)
                {
                    int key=Key(x,y);bool has=hits.TryGetValue(key,out Hit h),wood=covered.Contains(key);
                    var tile=new ReviewTile{x=x,y=y,tile=grid[x,y],hit=has?h.time:-1,wood=wood,reserved=source.Contains(key),destY=y,convertedAt=converted.TryGetValue(key,out float conv)?conv:-1};tiles.Add(tile);byCell[x,y]=tile;
                    if(live!=null||!has||tile.reserved||converted.ContainsKey(key))continue;int v=(x*17+y*31+x*y)%3;
                    var e=Emit(wood?5:2+v,wood?"Wood_V"+((x+y)%2):"Tile"+grid[x,y]+"_V"+v,h.time,wood?.8f:16f/30,x,y,wood?42:38);
                    e.driftX=h.dx;e.driftY=h.dy;e.gravity=wood?2.1f:2.7f;e.ramp=.022f;
                }
                if(live==null)for(int x=0;x<c;x++)
                {
                    var survivors=new List<int>();int cleared=0;for(int y=0;y<r;y++)if(hits.ContainsKey(Key(x,y)))cleared++;else survivors.Add(y);
                    for(int dest=0;dest<survivors.Count;dest++){int old=survivors[dest];if(old==dest)continue;var tile=byCell[x,old];tile.destY=dest;tile.fallStart=ready;tile.fallDuration=.17f+.085f*Mathf.Sqrt(old-dest);}
                    for(int k=0;k<cleared;k++){int old=r+k,dest=survivors.Count+k;tiles.Add(new ReviewTile{x=x,y=old,tile=(x*5+k*3+k/2+combo+2)%6,destY=dest,fallStart=ready+.018f*k,fallDuration=.17f+.085f*Mathf.Sqrt(old-dest),incoming=true});}
                }
                float duration=primary+1.15f;foreach(var e in fx)duration=Mathf.Max(duration,e.start+e.duration+.25f);foreach(var t in tiles)if(t.fallDuration>0)duration=Mathf.Max(duration,t.fallStart+t.fallDuration+.3f);
                return new ReviewPlan{columns=c,rows=r,kind=kind,originX=ox,originY=oy,primary=primary,duration=duration,activation=activation,launchTime=launchTime,
                    tiles=tiles.ToArray(),effects=fx.ToArray(),powers=new ReviewPower[0],blasts=blasts.ToArray(),beams=beams.ToArray(),flights=flights.ToArray(),
                    seekerLaunches=new ReviewSeekerLaunch[0],goldenGroups=groups.ToArray(),targetColor=combo==3?color:-1,rocketVertical=vertical,
                    requestedTargetX=combo==3?-1:requested.x,requestedTargetY=combo==3?-1:requested.y,convertedCount=converted.Count,createdSeekers=created,unassignedSeekers=unassigned,settleAfter=ready};
            }
        }
    }
}

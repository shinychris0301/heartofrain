using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace HeartOfTheRain.M46 {
    public sealed class LiveBoardInput {
        public readonly int[,] Grid; public readonly HashSet<int> Active,Obstacles=new HashSet<int>();
        readonly Dictionary<int,Piece> occupants; readonly HashSet<int> sources=new HashSet<int>();
        public readonly int Columns,Rows,PartnerX,PartnerY,VisualPartnerX,OriginX,OriginY;
        public readonly Piece Origin,Partner;
        public LiveBoardInput(BoardModel board,Piece origin,Piece partner){
            Columns=board.Level.columns;Rows=board.Level.rows;Origin=origin.Copy();Partner=partner==null?null:partner.Copy();OriginX=origin.x;OriginY=origin.y;
            Active=new HashSet<int>(board.Active);occupants=board.Pieces.ToDictionary(p=>p.Key,p=>p.Value.Copy());sources.Add(origin.id);if(partner!=null)sources.Add(partner.id);
            VisualPartnerX=partner!=null&&partner.y==origin.y?partner.x:origin.x+1<Columns?origin.x+1:origin.x-1;
            PartnerX=partner==null?VisualPartnerX:partner.x;PartnerY=partner==null?origin.y:partner.y;
            Grid=new int[Columns,Rows];for(int y=0;y<Rows;y++)for(int x=0;x<Columns;x++){Piece p;Grid[x,y]=occupants.TryGetValue(y*Columns+x,out p)&&p.family=="gem"?p.color:-1;
                if(p!=null&&p.family!="gem"&&p.family!="power"&&p.family!="pail")Obstacles.Add(y*Columns+x);}
        }
        public bool CanTarget(int x,int y){Piece p;return x>=0&&y>=0&&x<Columns&&y<Rows&&occupants.TryGetValue(y*Columns+x,out p)&&!sources.Contains(p.id)&&p.family!="pail";}
        public bool CanConvert(int x,int y){Piece p;return CanTarget(x,y)&&occupants.TryGetValue(y*Columns+x,out p)&&p.family=="gem";}
        public int SharedOwnerAt(int x,int y){Piece p;return occupants.TryGetValue(y*Columns+x,out p)?p.ownerId:0;}
        public static int[,] MakeLayout(int w,int h){var grid=new int[w,h];for(int y=0;y<h;y++)for(int x=0;x<w;x++)grid[x,y]=(x+2*y)%6;return grid;}
    }
    public static class LivePowerPlan {
        public static ReviewPlan Build(BoardModel board,Activation request,LiveBoardInput live){
            int color=request.color;
            if(color<0){var counts=new int[6];foreach(var p in board.Pieces.Values)if(p.family=="gem")counts[p.color]++;color=Enumerable.Range(0,6).OrderByDescending(i=>counts[i]).ThenBy(i=>i).First();}
            int kind=request.kind;var targets=new List<Vector2Int>();
            for(int y=0;y<live.Rows;y++)for(int x=0;x<live.Columns;x++)if(live.CanTarget(x,y)&&Math.Abs(x-live.OriginX)+Math.Abs(y-live.OriginY)>1)targets.Add(new Vector2Int(x,y));
            targets=targets.OrderByDescending(q=>live.Obstacles.Contains(q.y*live.Columns+q.x)).ThenByDescending(q=>(q.x-live.OriginX)*(q.x-live.OriginX)+(q.y-live.OriginY)*(q.y-live.OriginY)).ThenBy(q=>q.y).ThenBy(q=>q.x).ToList();
            if((kind==11||kind==12||kind==13)&&targets.Count==0)return NoTarget(live,kind);
            var target=targets.Count>0?targets[0]:new Vector2Int(-1,-1);
            var plan=ReviewPlan.Build(live.Columns,live.Rows,kind,new Vector2Int(live.OriginX,live.OriginY),false,color,target,request.vertical,live);
            // Cell-centred impacts only appear in active cells; broad explosions,
            // flight paths and solid debris may extend beyond the board.
            plan.effects=plan.effects.Where(e=>!new[]{"OR_Hit","OR_Stars","OR_Target","Contact","Wake0","Wake1"}.Contains(e.clip)||live.Active.Contains((int)Math.Round(e.y)*live.Columns+(int)Math.Round(e.x))).ToArray();
            if(kind==16||kind==14){
                int expected=kind==16?2:3;var fx=plan.effects.ToList();int existing=plan.flights==null?0:plan.flights.Length;
                if(kind==16)foreach(var f in plan.flights)f.golden=true;
                for(int i=existing;i<expected;i++){
                    float x=live.OriginX+(i==0?-.532f:.532f);fx.Add(new ReviewFx{atlas=kind==16?40:29,clip=kind==16?"GS_Flight":"RS_Flight",x=x,y=live.OriginY+.49f,start=plan.activation,duration=.3f,scale=1.61f,order=50,fadeOut=.3f});
                    fx.Add(new ReviewFx{atlas=21,clip="OR_Stars",x=x,y=live.OriginY+.49f,start=plan.activation,duration=14f/30,scale=.5f,order=46});
                }
                plan.effects=fx.ToArray();plan.createdSeekers=expected;plan.unassignedSeekers=expected-existing;plan.settleAfter=Math.Max(plan.primary+.24f,plan.activation+.3f);
            }
            // The approved merge sheets are horizontal. For a vertical pair,
            // the view slides the partner to that pose before sampling the merge;
            // the live cells, targeting and reservations remain at actual positions.
            foreach(var p in plan.powers??new ReviewPower[0])if(p.begin==0&&p.end<=.8f){if(p.x==live.OriginX&&p.y==live.OriginY)p.atlas=IconAtlas(live.Origin.power);else if(live.Partner!=null&&p.x==live.PartnerX&&p.y==live.PartnerY)p.atlas=IconAtlas(live.Partner.power);}
            return plan;
        }
        public static int IconAtlas(int kind){switch(kind){case 4:return 9;case 5:return 10;case 7:return 19;case 11:return 29;case 16:return 40;default:return 6;}}
        public static string IdleClip(int kind){return kind==7?"OR_Idle":kind==11?"RS_Idle":kind==16?"GS_Idle":"Idle";}
        static ReviewPlan NoTarget(LiveBoardInput l,int kind){
            var tiles=new List<ReviewTile>();foreach(int key in l.Active){int x=key%l.Columns,y=key/l.Columns;tiles.Add(new ReviewTile{x=x,y=y,tile=l.Grid[x,y],hit=Math.Abs(x-l.OriginX)+Math.Abs(y-l.OriginY)<=1?1.07f:-1});}
            return new ReviewPlan{columns=l.Columns,rows=l.Rows,kind=kind,originX=l.OriginX,originY=l.OriginY,primary=1.1f,activation=1.23f,settleAfter=1.6f,duration=1.6f,tiles=tiles.ToArray(),powers=new ReviewPower[0],beams=new ReviewBeam[0],flights=new ReviewFlight[0],blasts=new ReviewBlast[0],seekerLaunches=new ReviewSeekerLaunch[0],goldenGroups=new ReviewGoldenGroup[0],effects=new[]{
                new ReviewFx{atlas=29,clip="RS_Charge",x=l.OriginX,y=l.OriginY,start=.8f,duration=8f/30,scale=1.4f,order=22},
                new ReviewFx{atlas=29,clip="RS_Lift",x=l.OriginX,y=l.OriginY,start=1.0667f,duration=10f/60,scale=1.4f,order=50},
                new ReviewFx{atlas=29,clip="RS_Flight",x=l.OriginX,y=l.OriginY+.49f,start=1.2334f,duration=.3f,scale=1.61f,order=50,fadeOut=.3f},
                new ReviewFx{atlas=21,clip="OR_Stars",x=l.OriginX,y=l.OriginY+.49f,start=1.2334f,duration=.4667f,scale=.5f,order=46}}};
        }
        public static List<Contact> Contacts(ReviewPlan p,LiveBoardInput l,string root){
            var result=new List<Contact>();int serial=0;
            void Add(int x,int y,float time,string id,bool colorClear=false){if(x>=0&&y>=0&&x<l.Columns&&y<l.Rows&&l.Active.Contains(y*l.Columns+x))result.Add(new Contact{x=x,y=y,time=time,activation=id,adjacentColorClear=colorClear,color=p.targetColor});}
            void Cross(int x,int y,float time,string id){Add(x,y,time,id);Add(x-1,y,time+.025f,id);Add(x+1,y,time+.025f,id);Add(x,y-1,time+.025f,id);Add(x,y+1,time+.025f,id);}
            void Bomb(int x,int y,float time,string id){for(int yy=y-2;yy<=y+2;yy++)for(int xx=x-2;xx<=x+2;xx++)Add(xx,yy,time+Math.Max(Math.Abs(xx-x),Math.Abs(yy-y))/40f,id);}
            void Lane(int x,int y,float time,bool vertical,string id){for(int i=0;i<(vertical?l.Rows:l.Columns);i++)Add(vertical?x:i,vertical?i:y,time+Math.Abs(i-(vertical?y:x))/24f,id);}
            var flights=p.flights??new ReviewFlight[0];if(p.flight!=null)flights=new[]{p.flight};
            if(new[]{11,12,13,14,16,17,18,19}.Contains(p.kind)){
                float first=flights.Length>0?flights.Min(f=>f.start+f.travel):float.MaxValue;
                foreach(var t in p.tiles??new ReviewTile[0])if(t.hit>=0&&t.hit<first-.001f)Add(t.x,t.y,t.hit,root+"/launch");
                foreach(var f in flights){string id=root+"/child_"+(serial++);float arrival=f.start+f.travel;Add(f.targetX,f.targetY,arrival,id);
                    if(p.kind==12||p.kind==17)Lane(f.targetX,f.targetY,arrival+.035f,p.rocketVertical||p.kind==12&&l.Partner!=null&&l.Partner.power==5,id);
                    else if(p.kind==13||p.kind==18)Bomb(f.targetX,f.targetY,arrival+(p.kind==13?0:.035f),id);}
            }else if(p.kind==8){foreach(var power in p.powers??new ReviewPower[0])if(power.begin>0)Lane(power.x,power.y,power.end,power.atlas==10,root+"/converted_"+(serial++));}
            else if(p.kind==9){foreach(var blast in p.blasts??new ReviewBlast[0])if(blast.affectsCells)Bomb(blast.x,blast.y,blast.start,root+"/converted_"+(serial++));}
            else if(p.kind==15){foreach(var launch in p.seekerLaunches??new ReviewSeekerLaunch[0])Cross(launch.x,launch.y,launch.start,root+"/launch_"+(serial++));foreach(var f in flights)Add(f.targetX,f.targetY,f.start+f.travel,root+"/child_"+(serial++));}
            else if(p.kind==20){foreach(var group in p.goldenGroups??new ReviewGoldenGroup[0])Cross(group.x,group.y,group.departure-.4f-10f/60,root+"/launch_"+(serial++));foreach(var f in flights)Add(f.targetX,f.targetY,f.start+f.travel,root+"/child_"+(serial++));}
            else foreach(var t in p.tiles??new ReviewTile[0])if(t.hit>=0)Add(t.x,t.y,t.hit,root,p.kind==7);
            return result.OrderBy(c=>c.time).ThenBy(c=>c.y).ThenBy(c=>c.x).ToList();
        }
    }
}

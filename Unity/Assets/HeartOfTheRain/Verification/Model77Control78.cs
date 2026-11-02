#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.M46;
namespace HeartOfTheRain.M46 {
    public sealed partial class BoardModel {
        [NonSerialized] public bool VerificationUseCheckpoint77Model78;
// BEGIN EXACT77 SnapshotFromScratch
        BoardSnapshot SnapshotFromCheckpoint77Model78(){
            // Stable merges compare IDs directly, avoiding comparer callbacks
            // and larger sort-entry swaps. Scratch never owns returned bodies.
            int count=Pieces.Count;if(snapshotPieces.Length<count){int capacity=Math.Max(count,snapshotPieces.Length*2);snapshotPieces=new Piece[capacity];snapshotMerge=new Piece[capacity];}
            int index=0;foreach(var piece in Pieces.Values)snapshotPieces[index++]=piece;
            var source=snapshotPieces;var target=snapshotMerge;
            for(int width=1;width<count;width*=2){
                for(int start=0;start<count;start+=width*2){
                    int middle=Math.Min(start+width,count),end=Math.Min(start+width*2,count),left=start,right=middle,write=start;
                    while(left<middle&&right<end){if(source[left].id<=source[right].id)target[write++]=source[left++];else target[write++]=source[right++];}
                    while(left<middle)target[write++]=source[left++];while(right<end)target[write++]=source[right++];
                }
                var swap=source;source=target;target=swap;
            }
            var pieces=count==0?Array.Empty<Piece>():new Piece[count];for(int i=0;i<count;i++)pieces[i]=source[i].Copy();
            // Do not retain removed live bodies after the snapshot completes.
            Array.Clear(snapshotPieces,0,count);Array.Clear(snapshotMerge,0,count);
            count=Goals.Count;if(snapshotGoals.Length<count)snapshotGoals=new SnapshotGoal[Math.Max(count,snapshotGoals.Length*2)];index=0;
            foreach(var goal in Goals){int at=index++;while(at>0&&GoalSnapshotOrder.Compare(snapshotGoals[at-1].family,goal.Key)>0){snapshotGoals[at]=snapshotGoals[at-1];at--;}snapshotGoals[at]=new SnapshotGoal{family=goal.Key,count=goal.Value};}
            var goals=count==0?Array.Empty<Goal>():new Goal[count];for(int i=0;i<count;i++){var goal=snapshotGoals[i];goals[i]=new Goal{family=goal.family,count=goal.count};}Array.Clear(snapshotGoals,0,count);
            return new BoardSnapshot{pieces=pieces,goals=goals,moves=Moves,turn=Turn,status=Status};
        }
// END EXACT77 SnapshotFromScratch
// BEGIN EXACT77 Validate
        void ValidateCheckpoint77Model78(){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            long work=WorkStart();
#endif
            var ids=new HashSet<int>();var counts=new Dictionary<string,int>();
            foreach(var kv in Pieces){var p=kv.Value;if(!Inside(p.x,p.y)||kv.Key!=Key(p.x,p.y)||!ids.Add(p.id))throw new InvalidOperationException("Occupancy invariant failed");
                if(p.family=="gem"&&(p.color<0||p.color>5))throw new InvalidOperationException("Invalid gem color");
                if(p.family!="gem"&&p.family!="power"){if(p.family!="pail"&&p.hp<1)throw new InvalidOperationException("Invalid obstacle HP");if(p.IsAnchor){string family=GoalFamily(p);if(!counts.ContainsKey(family))counts[family]=0;counts[family]+=GoalUnits(p);}}}
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            long footprint=WorkStart();
#endif
            ValidateFootprints();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            WorkDone(WorkStage.Footprint,footprint);
#endif
            foreach(var g in Goals){int n;counts.TryGetValue(g.Key,out n);if(g.Value<0||g.Value!=n)throw new InvalidOperationException("Goal count mismatch: "+g.Key);}
            if(Moves<0)throw new InvalidOperationException("Negative move budget");
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            WorkDone(WorkStage.Validation,work);
#endif
        }
// END EXACT77 Validate
// BEGIN EXACT77 ValidateFootprints
        void ValidateFootprintsCheckpoint77Model78(){
            foreach(var p in Pieces.Values.Where(q=>q.ownerId!=0)){
                var root=Pieces.Values.FirstOrDefault(q=>q.id==p.ownerId);
                if(root==null||!root.IsAnchor||root.family!=p.family||root.hp!=p.hp)throw new InvalidOperationException("Invalid shared obstacle owner");
            }
            foreach(var root in Pieces.Values.Where(q=>q.IsAnchor&&(q.family=="cabinet"||q.family=="crystal"))){
                int w=root.family=="cabinet"?2:1,h=root.family=="cabinet"?2:root.hp;
                var members=Pieces.Values.Where(q=>q.ownerId==root.id).ToArray();
                if(members.Length!=w*h)throw new InvalidOperationException("Incomplete obstacle footprint");
                for(int dy=0;dy<h;dy++)for(int dx=0;dx<w;dx++)if(At(root.x+dx,root.y+dy)?.ownerId!=root.id)throw new InvalidOperationException("Broken footprint");
                if(root.family=="crystal"&&Pieces.Values.Any(q=>q.x==root.x&&q.family!="gem"&&q.family!="power"&&q.ownerId!=root.id))
                    throw new InvalidOperationException("Crystal lane must exclude other obstacles");
            }
        }
// END EXACT77 ValidateFootprints
    }
}
namespace HeartOfTheRain.Verification.Checkpoint77Model78Control {
// BEGIN EXACT77 LivePowerPlan
    public static class LivePowerPlan77 {
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

// END EXACT77 LivePowerPlan
}
#endif

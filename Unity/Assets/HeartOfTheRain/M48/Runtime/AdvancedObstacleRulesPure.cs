using System;
using System.Linq;
using System.Collections.Generic;
namespace HeartOfTheRain.M46 {
    public sealed partial class BoardModel {
        public static string GoalFamily(Piece p)=>p.family=="cabinet"?"rainlight":p.family;
        public static int GoalUnits(Piece p)=>p.family=="cabinet"?Math.Min(4,p.hp):1;
        void AddObstacle(ObstacleCell o){
            if(o.family=="crystal"&&(o.hp<5||o.hp>9))throw new ArgumentException("Storm Crystal must start with 5–9 segments");
            if(o.family=="cabinet"&&(o.hp<1||o.hp>5))throw new ArgumentException("Cabinet stage must be 1–5");
            if(o.family=="pod"&&(o.hp<1||o.hp>3))throw new ArgumentException("Pod stage must be 1–3");
            var p=new Piece{x=o.x,y=o.y,hp=o.hp,family=o.family};Add(p);
            if(o.family!="crystal"&&o.family!="cabinet")return;
            p.ownerId=p.id;int width=o.family=="cabinet"?2:1,height=o.family=="cabinet"?2:o.hp;
            for(int dy=0;dy<height;dy++)for(int dx=0;dx<width;dx++)if(dx!=0||dy!=0)
                Add(new Piece{x=o.x+dx,y=o.y+dy,hp=o.hp,family=o.family,ownerId=p.id});
            if(o.family=="crystal"&&(Inside(o.x,o.y-1)||Inside(o.x-1,o.y)&&Inside(o.x+1,o.y)))
                throw new ArgumentException("Storm Crystal must anchor at a bottom outer perimeter");
        }
        void ValidateFootprints(){
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
        bool HitAdvanced(Piece p,BoardStep step,float time,string activation){
            if(p.family!="crystal"&&p.family!="cabinet"&&p.family!="pod")return false;
            var prior=step.damage.LastOrDefault(d=>d.id==p.id);
            if(prior!=null)time=Math.Max(time,prior.time+(p.family=="cabinet"?.9f:.8f));
            int before=p.hp;p.hp--;
            step.damage.Add(new Damage{id=p.id,x=p.x,y=p.y,family=p.family,beforeHP=before,afterHP=p.hp,time=time,activation=activation});
            var members=p.ownerId==0?new[]{p}:Pieces.Values.Where(q=>q.ownerId==p.id).ToArray();
            foreach(var member in members)member.hp=p.hp;
            if(p.family=="crystal"&&p.hp>0)Pieces.Remove(Key(p.x,p.y+p.hp));
            if(p.family=="cabinet"&&before<5){
                int slot=4-before;GoalDelta("rainlight",-1);step.collections.Add(new GoalCollection{family="rainlight",x=p.x,y=p.y,offsetX=.5f+(slot%2==0?-.345f:.345f),offsetY=.5f+(slot<2?.24f:-.36f),launch=time+.1f,arrival=time+.82f});
                step.duration=Math.Max(step.duration,time+1.1f);
            }
            if(p.hp==0){
                foreach(var member in members)Pieces.Remove(Key(member.x,member.y));
                if(p.family!="cabinet")GoalDelta(p.family,-1);
                var old=p.Copy();old.hp=before;step.removed.Add(new Removed{piece=old,time=time,cause="obstacle"});
                if(p.family=="pod"){
                    step.collections.Add(new GoalCollection{family="pod",x=p.x,y=p.y,launch=time+.1f,arrival=time+1.45f});
                    step.duration=Math.Max(step.duration,time+1.7f);
                }
            }
            step.duration=Math.Max(step.duration,time+(p.family=="cabinet"?.9f:.8f));
            return true;
        }
    }
}

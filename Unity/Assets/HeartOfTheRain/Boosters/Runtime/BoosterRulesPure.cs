using System;
using System.Linq;
using System.Collections.Generic;
namespace HeartOfTheRain.M46 {
    public enum BoosterKind { Hammer, Axe, Ram, Atlas }
    [Serializable] public sealed class BoosterInventory {
        public int hammer=3,axe=3,ram=3,atlas=3;
        public int Count(BoosterKind k){switch(k){case BoosterKind.Hammer:return hammer;case BoosterKind.Axe:return axe;case BoosterKind.Ram:return ram;default:return atlas;}}
        internal void Spend(BoosterKind k){switch(k){case BoosterKind.Hammer:hammer--;break;case BoosterKind.Axe:axe--;break;case BoosterKind.Ram:ram--;break;case BoosterKind.Atlas:atlas--;break;}}
    }
    [Serializable] public sealed class BoosterPlan {
        public BoosterKind kind;public int x,y,columns,rows;
        public float duration;public Contact[] contacts;
        public static string Name(BoosterKind k){switch(k){case BoosterKind.Hammer:return "Mason's Hammer";case BoosterKind.Axe:return "Woodcutter's Axe";case BoosterKind.Ram:return "Channel Ram";default:return "Daria's Atlas";}}
        public static float HitTime(BoosterKind k,int x,int y,int rows){return k==BoosterKind.Hammer?.80f:k==BoosterKind.Axe?.64f+(rows-1-y)*.065f:.64f+x*.065f;}
        public static BoosterPlan Build(BoardModel b,BoosterKind k,int x,int y){
            var p=new BoosterPlan{kind=k,x=x,y=y,columns=b.Level.columns,rows=b.Level.rows};
            p.duration=k==BoosterKind.Hammer?1.55f:k==BoosterKind.Atlas?2.75f:1.3f+Math.Max(p.columns,p.rows)*.065f;
            p.contacts=k==BoosterKind.Atlas?new Contact[0]:b.Pieces.Values.Where(q=>k==BoosterKind.Hammer?q.x==x&&q.y==y:k==BoosterKind.Axe?q.x==x:q.y==y).Select(q=>new Contact{x=q.x,y=q.y,time=HitTime(k,q.x,q.y,p.rows),activation="booster"}).OrderBy(c=>c.time).ToArray();
            return p;
        }
    }
    public sealed partial class BoardModel {
        // Called only on a stable board. Selection/cancel are presentation-only;
        // inventory is charged exactly once after a valid plan has been accepted.
        public TurnResult UseBooster(BoosterKind kind,int x,int y,BoosterInventory inventory){
            var result=new TurnResult();
            if(!Enum.IsDefined(typeof(BoosterKind),kind)||inventory==null||inventory.Count(kind)<=0){result.reason="No booster available";return result;}
            if(Status!="Playing"){result.reason="The board is not ready";return result;}
            if(kind!=BoosterKind.Atlas&&!Inside(x,y)){result.reason="Choose an active cell";return result;}
            var plan=BoosterPlan.Build(this,kind,x,y);
            if(kind!=BoosterKind.Atlas&&!plan.contacts.Any(c=>At(c.x,c.y)!=null&&At(c.x,c.y).family!="pail")){result.reason="No affected pieces";return result;}
            var step=Start("booster",plan.duration,BoosterPlan.Name(kind));step.booster=plan;
            if(kind==BoosterKind.Atlas){
                if(!AtlasPermutation(step)){result.reason="No legal rearrangement found; booster retained";return result;}
                result.accepted=true;inventory.Spend(kind);Finish(step,result);return result;
            }
            activationSerial=0;acceptedDamage.Clear();pending.Clear();queued.Clear();mossHit=false;
            result.accepted=true;inventory.Spend(kind);string id=ActivationId("manual_"+kind);
            foreach(var c in plan.contacts)Hit(At(c.x,c.y),step,c.time,id,true,-1);
            Finish(step,result);Settle(result,new HashSet<int>(),false);return result;
        }
        bool AtlasPermutation(BoardStep step){
            // The same piece IDs, colors and power-ups move; no recoloring.
            // Crates, jars, fixed obstacles and voids never enter the permutation.
            var pieces=Pieces.Values.Where(p=>p.Swappable).OrderBy(p=>p.id).ToArray();
            if(pieces.Length<3)return false;
            uint priorRandom=random;var cells=pieces.Select(p=>new Cell(p.x,p.y)).ToArray();
            for(int attempt=0;attempt<800;attempt++){
                foreach(var p in pieces)Pieces.Remove(Key(p.x,p.y));
                var order=Enumerable.Range(0,pieces.Length).ToArray();
                for(int i=order.Length-1;i>0;i--){int j=Rand(i+1),tmp=order[i];order[i]=order[j];order[j]=tmp;}
                int moved=0;
                for(int i=0;i<pieces.Length;i++){var p=pieces[i];p.x=cells[order[i]].x;p.y=cells[order[i]].y;Pieces.Add(Key(p.x,p.y),p);if(order[i]!=i)moved++;}
                if(moved>=Math.Max(2,pieces.Length/2)&&Matches(null).Count==0&&LegalSwaps().Count>0){
                    for(int i=0;i<pieces.Length;i++)step.motion.Add(new Motion{id=pieces[i].id,fromX=cells[i].x,fromY=cells[i].y,toX=pieces[i].x,toY=pieces[i].y});
                    return true;
                }
            }
            foreach(var p in pieces)Pieces.Remove(Key(p.x,p.y));
            for(int i=0;i<pieces.Length;i++){pieces[i].x=cells[i].x;pieces[i].y=cells[i].y;Pieces.Add(Key(pieces[i].x,pieces[i].y),pieces[i]);}
            random=priorRandom;return false;
        }
    }
}

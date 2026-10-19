using System;
using System.Collections.Generic;
using System.Linq;
namespace HeartOfTheRain.M46
{
    [Serializable] public class Cell { public int x,y; public Cell(){} public Cell(int x,int y){this.x=x;this.y=y;} }
    [Serializable] public class GemCell:Cell { public int color; }
    [Serializable] public class ObstacleCell:Cell { public string family; public int hp; }
    [Serializable] public class Goal { public string family; public int count; }
    [Serializable] public class GrowthRule { public bool enabled; public int undamagedMoves,maxNewClumps; }
    [Serializable] public class LevelData {
        public string id,name,introductionTitle,introductionInstruction; public int columns,rows,globalLevel,movesProposal,tileSeed;
        public Cell[] activeCells,spawnPoints,deliveryExits; public GemCell[] initialTiles;
        public ObstacleCell[] obstacles; public Goal[] goals; public int[] activeColors; public GrowthRule mossRegrowth;
    }
    [Serializable] public class Piece:Cell {
        public int id,color=-1,hp,power=-1,ownerId; public string family;
        public bool IsAnchor {get{return ownerId==0||ownerId==id;}}
        public Piece Copy(){return (Piece)MemberwiseClone();}
        public bool Movable { get {return family=="gem"||family=="power"||family=="crate"||family=="pail";} }
        public bool Swappable {get{return family=="gem"||family=="power";}}
    }
    [Serializable] public class BoardSnapshot { public Piece[] pieces; public Goal[] goals; public int moves,turn; public string status; }
    [Serializable] public class Damage:Cell { public int id,beforeHP,afterHP; public string family,activation; public float time; }
    [Serializable] public class Removed { public Piece piece; public float time; public string cause; }
    [Serializable] public class Motion { public int id; public float fromX,fromY,toX,toY; public bool spawned; }
    [Serializable] public class Contact:Cell { public float time; public string activation; public bool adjacentColorClear; public int color=-1; }
    [Serializable] public class GoalCollection:Cell {public string family;public int amount=1;public float launch,arrival,offsetX,offsetY;}
    [Serializable] public class BoardStep {
        public string kind,label; public float duration; public BoardSnapshot before,after; public ReviewPlan powerPlan; public BoosterPlan booster;
        public List<Damage> damage=new List<Damage>(); public List<Removed> removed=new List<Removed>();
        public List<Motion> motion=new List<Motion>(); public List<Piece> created=new List<Piece>();
        public List<GoalCollection> collections=new List<GoalCollection>();
    }
    [Serializable] public class TurnResult { public bool accepted; public string reason; public List<BoardStep> steps=new List<BoardStep>(); }
    public class Activation { public int kind,originId,partnerId=-1,color=-1; public bool vertical; }
    public sealed partial class BoardModel {
        public readonly LevelData Level;
        public readonly Dictionary<int,Piece> Pieces=new Dictionary<int,Piece>();
        public readonly HashSet<int> Active=new HashSet<int>(),Spawns=new HashSet<int>(),Exits=new HashSet<int>();
        public readonly Dictionary<string,int> Goals=new Dictionary<string,int>();
        public int Moves {get;private set;} public int Turn {get;private set;} public string Status {get;private set;}="Playing";
        public int QuietMoves {get;private set;} public int GrowthUsed {get;private set;}
        uint random; int nextId=1,activationSerial; bool mossHit;
        readonly HashSet<string> acceptedDamage=new HashSet<string>();
        readonly Queue<Activation> pending=new Queue<Activation>(); readonly HashSet<int> queued=new HashSet<int>();
        static readonly Cell[] D={new Cell(-1,0),new Cell(1,0),new Cell(0,-1),new Cell(0,1)};
        public BoardModel(LevelData level,uint seed=0){
            if(level==null||level.columns<3||level.rows<3)throw new ArgumentException("Invalid level");
            Level=level; random=seed==0?(uint)Math.Max(1,level.tileSeed):seed; Moves=level.movesProposal;
            foreach(var c in level.activeCells){if(c.x<0||c.y<0||c.x>=level.columns||c.y>=level.rows||!Active.Add(Key(c.x,c.y)))throw new ArgumentException("Invalid active cells");}
            foreach(var c in level.spawnPoints??new Cell[0])Spawns.Add(Key(c.x,c.y));
            foreach(var c in level.deliveryExits??new Cell[0])Exits.Add(Key(c.x,c.y));
            foreach(var g in level.goals)Goals.Add(g.family,g.count);
            foreach(var g in level.initialTiles)Add(new Piece{x=g.x,y=g.y,color=g.color,family="gem"});
            foreach(var o in level.obstacles)AddObstacle(o);
            Validate();
        }
        public int Key(int x,int y){return y*Level.columns+x;}
        public bool Inside(int x,int y){return x>=0&&y>=0&&x<Level.columns&&y<Level.rows&&Active.Contains(Key(x,y));}
        public Piece At(int x,int y){Piece p;return Inside(x,y)&&Pieces.TryGetValue(Key(x,y),out p)?p:null;}
        void Add(Piece p){if(!Inside(p.x,p.y)||At(p.x,p.y)!=null)throw new InvalidOperationException("Occupied or inactive cell");if(p.id==0)p.id=nextId++;Pieces.Add(Key(p.x,p.y),p);}
        int Rand(int max){random^=random<<13;random^=random>>17;random^=random<<5;return (int)(random%(uint)max);}
        int NewColor(){var c=Level.activeColors;return c!=null&&c.Length>0?c[Rand(c.Length)]:Rand(6);}
        public BoardSnapshot Snapshot(){return new BoardSnapshot{pieces=Pieces.Values.OrderBy(p=>p.id).Select(p=>p.Copy()).ToArray(),goals=Goals.OrderBy(p=>p.Key).Select(p=>new Goal{family=p.Key,count=p.Value}).ToArray(),moves=Moves,turn=Turn,status=Status};}
        BoardStep Start(string kind,float duration,string label){return new BoardStep{kind=kind,duration=duration,label=label,before=Snapshot()};}
        void Finish(BoardStep s,TurnResult result){Validate();s.after=Snapshot();result.steps.Add(s);}
        void GoalDelta(string f,int delta){if(Goals.ContainsKey(f))Goals[f]+=delta;}
        public void Validate(){
            var ids=new HashSet<int>();var counts=new Dictionary<string,int>();
            foreach(var kv in Pieces){var p=kv.Value;if(!Inside(p.x,p.y)||kv.Key!=Key(p.x,p.y)||!ids.Add(p.id))throw new InvalidOperationException("Occupancy invariant failed");
                if(p.family=="gem"&&(p.color<0||p.color>5))throw new InvalidOperationException("Invalid gem color");
                if(p.family!="gem"&&p.family!="power"){if(p.family!="pail"&&p.hp<1)throw new InvalidOperationException("Invalid obstacle HP");if(p.IsAnchor){string family=GoalFamily(p);if(!counts.ContainsKey(family))counts[family]=0;counts[family]+=GoalUnits(p);}}}
            ValidateFootprints();
            foreach(var g in Goals){int n;counts.TryGetValue(g.Key,out n);if(g.Value<0||g.Value!=n)throw new InvalidOperationException("Goal count mismatch: "+g.Key);}
            if(Moves<0)throw new InvalidOperationException("Negative move budget");
        }
        public bool InjectReviewPower(int x,int y,int kind){
            if(Status!="Playing"||!new[]{4,5,7,11,16,21}.Contains(kind))return false;
            var p=At(x,y);if(p==null||p.family!="gem")return false;p.family="power";p.power=kind;p.color=-1;Validate();return true;
        }
        sealed class Match {public HashSet<int> cells=new HashSet<int>();public int color,maxH,maxV;public bool square;}
        List<Match> Matches(HashSet<int> dirty){
            var patterns=new List<Match>();
            foreach(var p in Pieces.Values.Where(p=>p.family=="gem").OrderBy(p=>p.y).ThenBy(p=>p.x)){
                foreach(var d in new[]{new Cell(1,0),new Cell(0,1)}){
                    var prev=At(p.x-d.x,p.y-d.y);if(prev!=null&&prev.family=="gem"&&prev.color==p.color)continue;
                    var run=new Match{color=p.color};var q=p;int x=p.x,y=p.y;
                    while(q!=null&&q.family=="gem"&&q.color==p.color){run.cells.Add(Key(x,y));x+=d.x;y+=d.y;q=At(x,y);}
                    if(run.cells.Count>=3){if(d.x==1)run.maxH=run.cells.Count;else run.maxV=run.cells.Count;patterns.Add(run);}
                }
                var square=new Match{color=p.color,square=true};bool ok=true;
                for(int dy=0;dy<2;dy++)for(int dx=0;dx<2;dx++){var q=At(p.x+dx,p.y+dy);if(q==null||q.family!="gem"||q.color!=p.color)ok=false;else square.cells.Add(Key(q.x,q.y));}
                if(ok)patterns.Add(square);
            }
            for(int i=0;i<patterns.Count;i++)for(int j=i+1;j<patterns.Count;j++)if(patterns[i].color==patterns[j].color&&patterns[i].cells.Overlaps(patterns[j].cells)){
                patterns[i].cells.UnionWith(patterns[j].cells);patterns[i].maxH=Math.Max(patterns[i].maxH,patterns[j].maxH);patterns[i].maxV=Math.Max(patterns[i].maxV,patterns[j].maxV);patterns[i].square|=patterns[j].square;patterns.RemoveAt(j);j=i;
            }
            return patterns.Where(m=>dirty==null||m.cells.Any(k=>dirty.Contains(Pieces[k].id))).ToList();
        }
        static int CreatedKind(Match m){if(Math.Max(m.maxH,m.maxV)>=5)return 7;if(m.maxH>=3&&m.maxV>=3)return 21;if(m.maxH>=4)return 4;if(m.maxV>=4)return 5;if(m.square)return 11;return -1;}
        void Exchange(Piece a,Piece b){int x=a.x,y=a.y;a.x=b.x;a.y=b.y;b.x=x;b.y=y;Pieces[Key(a.x,a.y)]=a;Pieces[Key(b.x,b.y)]=b;}
        public static int Combo(int a,int b){
            bool ar=a==4||a==5,br=b==4||b==5;
            if(ar&&br)return 6;if((ar&&b==21)||(br&&a==21))return 2;if(a==21&&b==21)return 3;
            if(a==7&&b==7)return 10;if((a==7&&br)||(b==7&&ar))return 8;if((a==7&&b==21)||(b==7&&a==21))return 9;
            if((a==11&&br)||(b==11&&ar))return 12;if((a==11&&b==21)||(b==11&&a==21))return 13;if(a==11&&b==11)return 14;
            if((a==7&&b==11)||(b==7&&a==11))return 15;if((a==16&&br)||(b==16&&ar))return 17;if((a==16&&b==21)||(b==16&&a==21))return 18;
            if((a==16&&b==11)||(b==16&&a==11))return 19;if((a==16&&b==7)||(b==16&&a==7))return 20;return -1;
        }
        public List<Cell[]> LegalSwaps(){
            var result=new List<Cell[]>();foreach(var a in Pieces.Values.OrderBy(p=>p.y).ThenBy(p=>p.x).ToArray())if(a.Swappable)foreach(var d in new[]{new Cell(1,0),new Cell(0,1)}){
                var b=At(a.x+d.x,a.y+d.y);if(b==null||!b.Swappable)continue;
                if(a.family=="power"||b.family=="power"){if(a.family!="power"||b.family!="power"||Combo(a.power,b.power)>=0)result.Add(new[]{new Cell(a.x,a.y),new Cell(b.x,b.y)});continue;}
                Exchange(a,b);bool ok=Matches(new HashSet<int>{a.id,b.id}).Count>0;Exchange(a,b);if(ok)result.Add(new[]{new Cell(a.x,a.y),new Cell(b.x,b.y)});
            }return result;
        }
        public TurnResult Swap(int ax,int ay,int bx,int by){
            var result=new TurnResult();var a=At(ax,ay);var b=At(bx,by);
            if(Status!="Playing"||Moves==0||a==null||b==null||!a.Swappable||!b.Swappable||Math.Abs(ax-bx)+Math.Abs(ay-by)!=1){result.reason="Choose adjacent gems or power-ups";return result;}
            int combo=a.family=="power"&&b.family=="power"?Combo(a.power,b.power):-1;
            if(a.family=="power"&&b.family=="power"&&combo<0){result.reason="This combination has no approved rule";return result;}
            var step=Start("swap",.18f,"Swap");Exchange(a,b);var dirty=new HashSet<int>{a.id,b.id};var groups=Matches(dirty);
            if(a.family!="power"&&b.family!="power"&&groups.Count==0){Exchange(a,b);result.reason="No match";return result;}
            BeginTurn(result);step.motion.Add(new Motion{id=a.id,fromX=ax,fromY=ay,toX=bx,toY=by});step.motion.Add(new Motion{id=b.id,fromX=bx,fromY=by,toX=ax,toY=ay});Finish(step,result);
            if(combo>=0){var source=a;var partner=b;if(combo==2&&source.power!=21){source=b;partner=a;}else if((combo==8||combo==9||combo==10||combo==15||combo==20)&&source.power!=7){source=b;partner=a;}else if(combo>=17&&combo<=19&&source.power!=16){source=b;partner=a;}else if(combo>=12&&combo<=14&&source.power!=11){source=b;partner=a;}
                pending.Enqueue(new Activation{kind=combo,originId=source.id,partnerId=partner.id,vertical=a.power==5||b.power==5});queued.Add(a.id);queued.Add(b.id);}
            else if(a.family=="power"||b.family=="power"){var p=a.family=="power"?a:b;var other=p==a?b:a;pending.Enqueue(new Activation{kind=p.power,originId=p.id,color=other.color});queued.Add(p.id);}
            else ResolveMatches(groups,result,b.id);
            Settle(result,dirty);return result;
        }
        public TurnResult Tap(int x,int y){
            var result=new TurnResult();var p=At(x,y);if(Status!="Playing"||Moves==0||p==null||p.family!="power"){result.reason="Tap a power-up";return result;}
            BeginTurn(result);pending.Enqueue(new Activation{kind=p.power,originId=p.id});queued.Add(p.id);Settle(result,new HashSet<int>());return result;
        }
        void BeginTurn(TurnResult result){result.accepted=true;Moves--;Turn++;mossHit=false;activationSerial=0;acceptedDamage.Clear();pending.Clear();queued.Clear();}
        string ActivationId(string label){return "turn_"+Turn+"_"+label+"_"+(++activationSerial);}
        void RemoveGem(Piece p,BoardStep step,float time,string cause){Pieces.Remove(Key(p.x,p.y));step.removed.Add(new Removed{piece=p.Copy(),time=time,cause=cause});}
        void Hit(Piece p,BoardStep step,float time,string activation,bool direct,int color){
            if(p==null)return;
            if(p.ownerId!=0&&!p.IsAnchor)p=Pieces.Values.FirstOrDefault(q=>q.id==p.ownerId);
            if(p==null)return;
            if(p.family=="gem"){if(direct)RemoveGem(p,step,time,"power");return;}
            if(p.family=="power"){if(direct&&queued.Add(p.id))pending.Enqueue(new Activation{kind=p.power,originId=p.id});return;}
            if(p.family=="pail"||(!direct&&(p.family=="case"||(p.family=="gate"&&color!=5))))return;
            if(!acceptedDamage.Add(activation+"/"+p.id))return;
            if(HitAdvanced(p,step,time,activation))return;
            int hp=p.hp;p.hp--;if(p.family=="moss")mossHit=true;
            step.damage.Add(new Damage{x=p.x,y=p.y,id=p.id,family=p.family,beforeHP=hp,afterHP=p.hp,time=time,activation=activation});
            if(p.hp==0){Pieces.Remove(Key(p.x,p.y));GoalDelta(p.family,-1);var old=p.Copy();old.hp=hp;step.removed.Add(new Removed{piece=old,time=time,cause="obstacle"});}
        }
        void Adjacent(int x,int y,int color,string id,float time,BoardStep step){foreach(var d in D)Hit(At(x+d.x,y+d.y),step,time,id,false,color);}
        void ResolveMatches(List<Match> groups,TurnResult result,int preferred=-1){
            if(groups.Count==0)return;var step=Start("match",.28f,"Match and obstacle contact");
            foreach(var m in groups){string id=ActivationId("match");int kind=CreatedKind(m);int keep=m.cells.Where(Pieces.ContainsKey).OrderBy(k=>Pieces[k].id==preferred?0:1).ThenBy(k=>k).First();
                foreach(int k in m.cells.OrderBy(k=>k)){Piece p;if(!Pieces.TryGetValue(k,out p)||p.family!="gem")continue;Adjacent(p.x,p.y,m.color,id,.05f,step);
                    if(k==keep&&kind>=0){p.family="power";p.power=kind;p.color=-1;step.created.Add(p.Copy());}
                    else RemoveGem(p,step,.05f,"match");}
            }Finish(step,result);
        }
        void ResolveActivation(Activation request,TurnResult result){
            var origin=Pieces.Values.FirstOrDefault(p=>p.id==request.originId);if(origin==null||origin.family!="power")return;
            var partner=Pieces.Values.FirstOrDefault(p=>p.id==request.partnerId);
            var step=Start("power",1,"Power-up activation");string id=ActivationId("power");
            var live=new LiveBoardInput(this,origin,partner);var plan=LivePowerPlan.Build(this,request,live);step.powerPlan=plan;
            var contacts=LivePowerPlan.Contacts(plan,live,id);step.duration=Math.Max(.5f,Math.Max(plan.settleAfter,contacts.Count>0?contacts.Max(c=>c.time)+.26f:plan.primary+.4f));
            RemoveGem(origin,step,0,"source");if(partner!=null)RemoveGem(partner,step,0,"source");
            // Converted bodies are owned by the power-up timeline. Their cells
            // remain visually reserved until all carriers/payloads finish.
            var conversions=(plan.tiles??new ReviewTile[0]).Where(t=>t.convertedAt>=0&&live.CanConvert(t.x,t.y)).ToArray();
            var operations=new List<Tuple<float,int,object>>();foreach(var t in conversions)operations.Add(Tuple.Create(t.convertedAt,0,(object)t));foreach(var c in contacts)operations.Add(Tuple.Create(c.time,1,(object)c));
            foreach(var op in operations.OrderBy(q=>q.Item1).ThenBy(q=>q.Item2)){
                if(op.Item2==0){var t=(ReviewTile)op.Item3;var p=At(t.x,t.y);if(p!=null&&p.family=="gem")RemoveGem(p,step,t.convertedAt,"convert");continue;}
                var c=(Contact)op.Item3;var piece=At(c.x,c.y);int sharedOwner=live.SharedOwnerAt(c.x,c.y);
                // Later child projectiles retain their obstacle reservation even
                // when an earlier child has already released its targeted top cell.
                if(sharedOwner!=0)piece=Pieces.Values.FirstOrDefault(q=>q.id==sharedOwner);
                if(c.adjacentColorClear&&piece!=null&&piece.family=="gem")Adjacent(c.x,c.y,c.color,c.activation,c.time,step);
                Hit(piece,step,c.time,c.activation,true,c.color);
            }
            Finish(step,result);
        }
        HashSet<int> Gravity(TurnResult result){
            var dirty=new HashSet<int>();var step=Start("gravity",.62f,"Fall and refill");
            for(int x=0;x<Level.columns;x++){
                int y=0;while(y<Level.rows){var at=At(x,y);if(!Inside(x,y)||(at!=null&&!at.Movable)){y++;continue;}
                    int bottom=y;while(y<Level.rows&&Inside(x,y)&&(At(x,y)==null||At(x,y).Movable))y++;int top=y-1;
                    var movable=new List<Piece>();for(int yy=bottom;yy<=top;yy++){var p=At(x,yy);if(p!=null){movable.Add(p);Pieces.Remove(Key(x,yy));}}
                    int dest=bottom;foreach(var p in movable){int from=p.y;p.y=dest++;Pieces[Key(x,p.y)]=p;if(from!=p.y){step.motion.Add(new Motion{id=p.id,fromX=x,fromY=from,toX=x,toY=p.y});dirty.Add(p.id);}}
                    if(Spawns.Contains(Key(x,top)))for(int offset=0;dest<=top;offset++,dest++){
                        var p=new Piece{id=nextId++,x=x,y=dest,family="gem",color=NewColor()};Pieces.Add(Key(x,dest),p);step.motion.Add(new Motion{id=p.id,fromX=x,fromY=top+1+offset,toX=x,toY=dest,spawned=true});dirty.Add(p.id);
                    }
                }
            }
            if(step.motion.Count>0)Finish(step,result);return dirty;
        }
        bool Deliver(TurnResult result){
            var jars=Pieces.Values.Where(p=>p.family=="pail"&&Exits.Contains(Key(p.x,p.y))).ToArray();if(jars.Length==0)return false;
            var step=Start("deliver",.8f,"Restoration jar delivered");foreach(var p in jars){RemoveGem(p,step,.7f,"delivery");GoalDelta("pail",-1);}Finish(step,result);return true;
        }
        void Settle(TurnResult result,HashSet<int> dirty,bool advanceThreatClock=true){
            int waves=0;while(true){if(++waves>128){Status="Resolution limit";break;}
                while(pending.Count>0){ResolveActivation(pending.Dequeue(),result);if(result.steps.Count>512){Status="Resolution limit";break;}}
                if(Status!="Playing")break;
                // Collection is a separate phase so new gems cannot enter a jar
                // cell while its approved collection sprite still occupies it.
                if(Deliver(result))continue;
                dirty.UnionWith(Gravity(result));if(Deliver(result))continue;
                var matches=Matches(dirty);if(matches.Count==0)break;ResolveMatches(matches,result);dirty.Clear();
            }
            if(Status=="Playing"){
                if(Goals.Values.All(n=>n==0))Status="Won";
                else if(Moves==0)Status="Out of moves";
                else {if(advanceThreatClock)Regrow(result);if(!Pieces.Values.Any(p=>p.family=="power")&&LegalSwaps().Count==0)Shuffle(result);}
            }
            var end=Start("settled",.06f,Status);Finish(end,result);
        }
        void Regrow(TurnResult result){
            bool enabled=Level.mossRegrowth!=null?Level.mossRegrowth.enabled:Level.globalLevel>=27;
            if(!enabled)return;if(mossHit){QuietMoves=0;return;}QuietMoves=Math.Min(2,QuietMoves+1);if(QuietMoves<2||GrowthUsed>=3)return;
            var options=new HashSet<int>();foreach(var p in Pieces.Values.Where(p=>p.family=="moss"))foreach(var d in D){var q=At(p.x+d.x,p.y+d.y);if(q!=null&&q.family=="gem"&&!Exits.Contains(Key(q.x,q.y)))options.Add(Key(q.x,q.y));}
            if(options.Count==0)return;int key=options.OrderBy(k=>k/Level.columns).ThenBy(k=>k%Level.columns).First();var step=Start("grow",.6f,"Overgrowth spreads");var old=Pieces[key];RemoveGem(old,step,0,"growth");var growth=new Piece{x=old.x,y=old.y,family="moss",hp=1};Add(growth);GoalDelta("moss",1);step.created.Add(growth.Copy());GrowthUsed++;QuietMoves=0;Finish(step,result);
        }
        void Shuffle(TurnResult result){
            var step=Start("shuffle",.45f,"Reshuffle");var gems=Pieces.Values.Where(p=>p.family=="gem").OrderBy(p=>p.id).ToArray();var original=gems.Select(p=>p.color).ToArray();
            for(int attempt=0;attempt<100;attempt++){
                var colors=(int[])original.Clone();for(int i=colors.Length-1;i>0;i--){int j=Rand(i+1),v=colors[i];colors[i]=colors[j];colors[j]=v;}
                for(int i=0;i<gems.Length;i++)gems[i].color=colors[i];
                if(Matches(null).Count==0&&LegalSwaps().Count>0){Finish(step,result);return;}
            }
            for(int i=0;i<gems.Length;i++)gems[i].color=original[i];Status="No legal moves";
        }
    }
}

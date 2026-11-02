using System;
using HeartOfTheRain.M46;
namespace HeartOfTheRain.M48 {
    // One intent captured only against a visually settled board. The owner
    // revalidates both piece identities and the model instance before applying it.
    public sealed class BoardGestureBuffer {
        BoardModel owner;int turn,fromId,toId,fromX,fromY,toX,toY;
        public bool HasPending=>owner!=null;
        public int FromX=>fromX;public int FromY=>fromY;
        public void Clear(){owner=null;}
        public bool Capture(BoardModel board,int x,int y,int targetX=-1,int targetY=-1){
            if(HasPending||board==null||board.Status!="Playing")return false;var a=board.At(x,y);var b=targetX<0?null:board.At(targetX,targetY);
            if(a==null||!a.Swappable||(targetX<0?a.family!="power":b==null||!b.Swappable||Math.Abs(x-targetX)+Math.Abs(y-targetY)!=1))return false;
            owner=board;turn=board.Turn;fromId=a.id;toId=b==null?0:b.id;fromX=x;fromY=y;toX=targetX;toY=targetY;return true;
        }
        public bool Take(BoardModel board,out Cell from,out Cell to){
            from=to=null;if(!HasPending)return false;var expected=owner;Clear();
            if(board!=expected||board.Status!="Playing"||board.Turn!=turn||board.At(fromX,fromY)?.id!=fromId||(toId!=0&&board.At(toX,toY)?.id!=toId))return false;
            from=new Cell(fromX,fromY);if(toId!=0)to=new Cell(toX,toY);return true;
        }
    }
    public static class InteractionGate {
        public static bool CanAct(bool ready,bool busy,bool paused,bool blocked,string status)=>ready&&!busy&&!paused&&!blocked&&status=="Playing";
    }
    public struct ReviewLayout {
        public float height,cell;
        public static ReviewLayout Compute(float width,float height,int columns,int rows) {
            if(width<=0||height<=0||columns<1||rows<1)throw new ArgumentOutOfRangeException("Invalid safe area or board dimensions");
            float logicalHeight=height*720/width;
            return new ReviewLayout{height=logicalHeight,cell=Math.Max(1,Math.Min(676f/columns,(logicalHeight-460)/rows))};
        }
    }
}

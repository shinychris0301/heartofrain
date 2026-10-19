using System;
using System.Collections.Generic;
using System.Linq;
namespace HeartOfTheRain.M46 {
    public static class ReviewScenario {
        static void Append(List<BoardStep> steps,TurnResult result){if(!result.accepted)throw new InvalidOperationException(result.reason);steps.AddRange(result.steps);}
        static BoardStep Hold(BoardModel board,float seconds,string label){return new BoardStep{kind="hold",duration=seconds,label=label,before=board.Snapshot(),after=board.Snapshot()};}
        static Piece Install(BoardModel board,List<BoardStep> steps,int kind,int nearX,int nearY){var p=board.Pieces.Values.Where(p=>p.family=="gem").OrderBy(p=>Math.Abs(p.x-nearX)+Math.Abs(p.y-nearY)).ThenBy(p=>p.id).FirstOrDefault();if(p==null||board.Status!="Playing")return null;var s=Hold(board,.65f,"Review setup: place "+Name(kind));board.InjectReviewPower(p.x,p.y,kind);s.kind="review_setup";s.created.Add(p.Copy());s.after=board.Snapshot();steps.Add(s);return p;}
        public static string Name(int kind){switch(kind){case 4:return "Rocket H";case 5:return "Rocket V";case 7:return "Rainbow Orb";case 11:return "Rain Seeker";case 16:return "Golden Seeker";default:return "Bomb";}}
        public static List<BoardStep> Build(BoardModel board){
            var steps=new List<BoardStep>();steps.Add(Hold(board,.8f,"Approved level layout"));var legal=board.LegalSwaps();if(legal.Count>0){var m=legal[0];Append(steps,board.Swap(m[0].x,m[0].y,m[1].x,m[1].y));}steps.Add(Hold(board,.5f,"Match, damage, gravity and refill"));
            if(board.Level.globalLevel==10){for(int i=0;i<5&&board.Status=="Playing";i++){var p=Install(board,steps,4,2,3);if(p==null)break;Append(steps,board.Tap(p.x,p.y));}}
            else {foreach(int kind in board.Level.globalLevel==18?new[]{5,11,16}:new[]{21,21,21,16}){var p=Install(board,steps,kind,board.Level.globalLevel==18?4:2,3);if(p==null)break;Append(steps,board.Tap(p.x,p.y));}}
            if(board.Level.globalLevel==41&&board.Status=="Playing"){
                var pair=board.Pieces.Values.Where(p=>p.family=="gem"&&board.At(p.x,p.y+1)?.family=="gem").OrderBy(p=>Math.Abs(p.x-5)+Math.Abs(p.y-5)).FirstOrDefault();
                if(pair!=null){var setup=Hold(board,.8f,"Review setup: Golden Seeker + Rocket");setup.kind="review_setup";int x=pair.x,y=pair.y;board.InjectReviewPower(x,y,16);board.InjectReviewPower(x,y+1,5);setup.created.Add(board.At(x,y).Copy());setup.created.Add(board.At(x,y+1).Copy());setup.after=board.Snapshot();steps.Add(setup);Append(steps,board.Swap(x,y,x,y+1));}
            }
            steps.Add(Hold(board,2,"Review complete"));return steps;
        }
    }
}

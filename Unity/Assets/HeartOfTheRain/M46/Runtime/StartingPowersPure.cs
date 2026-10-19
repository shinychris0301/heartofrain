using System;
using System.Linq;
using System.Collections.Generic;
namespace HeartOfTheRain.M46
{
    public sealed partial class BoardModel
    {
        bool startingPowersApplied;
        // Atomic, one-shot grant on a fresh board. Goal objects, moves and level data are untouched.
        public bool TryPlaceStartingPowers(int[] kinds,out string error)
        {
            error="";kinds=kinds??new int[0];
            if(startingPowersApplied||Turn!=0||Status!="Playing"){error="Starting powers can only be granted once on a fresh board.";return false;}
            if(kinds.Length>4||kinds.Any(k=>k!=4&&k!=21&&k!=7&&k!=16)){error="Unsupported starting powers.";return false;}
            float cx=(Level.columns-1)*.5f,cy=(Level.rows-1)*.5f;
            var gems=Pieces.Values.Where(p=>p.family=="gem").OrderBy(p=>Math.Abs(p.x-cx)+Math.Abs(p.y-cy)).ThenBy(p=>Key(p.x,p.y)).ToList();
            if(gems.Count<kinds.Length){error="This board has too few available gem cells.";return false;}
            var chosen=new List<Piece>();
            foreach(int kind in kinds)
            {
                Piece pick;
                if(chosen.Count==0)pick=gems[0];
                else if(chosen.Count==1&&kinds[0]==4&&kind==21)
                    pick=gems.OrderBy(p=>Math.Abs(p.x-chosen[0].x)+Math.Abs(p.y-chosen[0].y)).ThenBy(p=>Key(p.x,p.y)).First();
                else pick=gems.OrderByDescending(p=>chosen.Min(q=>Math.Abs(p.x-q.x)+Math.Abs(p.y-q.y))).ThenBy(p=>Key(p.x,p.y)).First();
                chosen.Add(pick);gems.Remove(pick);
            }
            for(int i=0;i<chosen.Count;i++){chosen[i].family="power";chosen[i].power=kinds[i];chosen[i].color=-1;}
            startingPowersApplied=true;Validate();return true;
        }
    }
}

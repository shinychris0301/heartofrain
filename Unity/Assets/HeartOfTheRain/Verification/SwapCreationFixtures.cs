#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System.Collections.Generic;
using HeartOfTheRain.M46;
namespace HeartOfTheRain.Verification
{
    public static class SwapCreationFixtures
    {
        // A horizontal gesture completes a vertical four at the destination.
        // Transposition and reflection exercise all four gesture directions.
        public static LevelData Rocket(bool vertical=false,bool reverse=false,int length=4)
        {
            var colors=new int[9,9];for(int y=0;y<9;y++)for(int x=0;x<9;x++)colors[x,y]=(x+2*y)%6;
            colors[3,4]=0;colors[4,4]=5;
            for(int y=2;y<2+length;y++)if(y!=4)colors[4,y]=0;
            colors[4,1]=2;colors[4,2+length]=3;
            var cells=new List<Cell>();var gems=new List<GemCell>();var spawns=new List<Cell>();
            for(int y=0;y<9;y++)for(int x=0;x<9;x++){
                int px=vertical?y:x,py=vertical?x:y;if(reverse){if(vertical)py=8-py;else px=8-px;}
                cells.Add(new Cell(px,py));if(py==8)spawns.Add(new Cell(px,py));if(px==0&&py==0)continue;gems.Add(new GemCell{x=px,y=py,color=colors[x,y]});
            }
            return new LevelData{id="verification-swap-creation",globalLevel=1,columns=9,rows=9,movesProposal=20,tileSeed=17,activeCells=cells.ToArray(),spawnPoints=spawns.ToArray(),initialTiles=gems.ToArray(),obstacles=new[]{new ObstacleCell{x=0,y=0,family="stone",hp=3}},goals=new[]{new Goal{family="stone",count=1}},activeColors=new[]{0,1,2,3,4,5}};
        }
        public static Cell From(bool vertical,bool reverse)=>vertical?new Cell(4,reverse?5:3):new Cell(reverse?5:3,4);
        public static Cell To()=>new Cell(4,4);
    }
}
#endif

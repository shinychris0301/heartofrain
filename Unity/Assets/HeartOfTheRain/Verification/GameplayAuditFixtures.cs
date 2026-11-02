#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System.Collections.Generic;
using HeartOfTheRain.M46;
namespace HeartOfTheRain.Verification
{
    public static class GameplayAuditFixtures
    {
        // Swipe (4,2) -> (4,3) to make a three-match next to the obstacle.
        // Color 5 also exercises the sluice's approved water adjacency rule.
        public static LevelData Obstacle(string family="stone",int hp=1)
        {
            var cells=new List<Cell>();var gems=new List<GemCell>();var spawns=new List<Cell>();
            for(int y=0;y<9;y++)for(int x=0;x<9;x++)
            {
                cells.Add(new Cell(x,y));if(y==8)spawns.Add(new Cell(x,y));if(x==4&&y==4)continue;
                int color=(x+2*y)%6;if(y==3&&(x==3||x==5)||x==4&&y==2)color=5;if(x==4&&y==3)color=0;
                gems.Add(new GemCell{x=x,y=y,color=color});
            }
            return new LevelData{id="verification-basic-hit-boundary",globalLevel=7,columns=9,rows=9,movesProposal=20,tileSeed=17,activeCells=cells.ToArray(),spawnPoints=spawns.ToArray(),initialTiles=gems.ToArray(),obstacles=new[]{new ObstacleCell{x=4,y=4,family=family,hp=hp}},goals=new[]{new Goal{family=family,count=1}},activeColors=new[]{0,1,2,3,4,5},mossRegrowth=new GrowthRule{enabled=false}};
        }
    }
}
#endif

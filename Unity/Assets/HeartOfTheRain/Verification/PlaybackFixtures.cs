#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System.Collections.Generic;
using HeartOfTheRain.M46;
namespace HeartOfTheRain.Verification
{
    public static class PlaybackFixtures
    {
        public static LevelData StackedStones(int column=4)
        {
            var cells=new List<Cell>();var gems=new List<GemCell>();var spawns=new List<Cell>();
            for(int y=0;y<9;y++)for(int x=0;x<9;x++){cells.Add(new Cell(x,y));if(y==8)spawns.Add(new Cell(x,y));if(x==column&&y>=2&&y<=4)continue;gems.Add(new GemCell{x=x,y=y,color=(x+2*y)%6});}
            return new LevelData{id="verification-stacked-stones",globalLevel=7,columns=9,rows=9,movesProposal=20,tileSeed=17,activeCells=cells.ToArray(),spawnPoints=spawns.ToArray(),initialTiles=gems.ToArray(),obstacles=new[]{new ObstacleCell{family="stone",hp=1,x=column,y=2},new ObstacleCell{family="stone",hp=3,x=column,y=3},new ObstacleCell{family="stone",hp=3,x=column,y=4}},goals=new[]{new Goal{family="stone",count=3}},activeColors=new[]{0,1,2,3,4,5}};
        }
        public static LevelData LargeObstacleGap()
        {
            var level=ClearingCabinet();level.id="verification-large-obstacle-gap";
            var gems=new List<GemCell>();foreach(var g in level.initialTiles)if(!((g.x==3||g.x==4)&&g.y<=3))gems.Add(g);
            foreach(int x in new[]{3,4})gems.Add(new GemCell{x=x,y=0,color=(x+0*2)%6});
            level.initialTiles=gems.ToArray();level.obstacles=new[]{new ObstacleCell{family="cabinet",hp=1,x=3,y=1},new ObstacleCell{family="stone",hp=3,x=3,y=3},new ObstacleCell{family="stone",hp=3,x=4,y=3}};
            level.goals=new[]{new Goal{family="rainlight",count=1},new Goal{family="stone",count=2}};return level;
        }
        public static LevelData ClearingCabinet()
        {
            var cells=new List<Cell>();var gems=new List<GemCell>();var spawns=new List<Cell>();
            for(int y=0;y<9;y++)for(int x=0;x<9;x++){cells.Add(new Cell(x,y));if(y==8)spawns.Add(new Cell(x,y));if((x==3||x==4)&&(y==0||y==1))continue;gems.Add(new GemCell{x=x,y=y,color=(x+2*y)%6});}
            return new LevelData{id="verification-cabinet-clear",globalLevel=1,columns=9,rows=9,movesProposal=10,tileSeed=1,activeCells=cells.ToArray(),spawnPoints=spawns.ToArray(),initialTiles=gems.ToArray(),obstacles=new[]{new ObstacleCell{family="cabinet",hp=1,x=3,y=0}},goals=new[]{new Goal{family="rainlight",count=1}},activeColors=new[]{0,1,2,3,4,5}};
        }
    }
}
#endif

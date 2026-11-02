#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System.Collections.Generic;
using HeartOfTheRain.M46;
namespace HeartOfTheRain.Verification
{
    public static class MixedPowerSwapFixtures
    {
        // The power starts at To; the ordinary gem at From completes the
        // recipe after their exchange. Rotations exercise all gesture axes.
        public static LevelData Match(int recipe,int rotation=0,int columns=9,int rows=9)
        {
            var source=M70R2Fixtures.Match(recipe,columns,rows);
            var cells=new List<Cell>();var gems=new List<GemCell>();var spawns=new List<Cell>();var obstacles=new List<ObstacleCell>();
            foreach(var p in source.activeCells)cells.Add(Rotate(p.x,p.y,rotation,columns,rows));
            foreach(var p in source.initialTiles){var at=Rotate(p.x,p.y,rotation,columns,rows);gems.Add(new GemCell{x=at.x,y=at.y,color=p.color});}
            foreach(var p in source.obstacles){var at=Rotate(p.x,p.y,rotation,columns,rows);obstacles.Add(new ObstacleCell{x=at.x,y=at.y,family=p.family,hp=p.hp});}
            // Preserve a normal top-edge refill portal on rectangular boards.
            int width=(rotation&1)==0?columns:rows,height=(rotation&1)==0?rows:columns;
            foreach(var p in cells)if(p.y==height-1)spawns.Add(new Cell(p.x,p.y));
            source.id="verification-mixed-power-swap";source.columns=width;source.rows=height;source.activeCells=cells.ToArray();source.initialTiles=gems.ToArray();source.spawnPoints=spawns.ToArray();source.obstacles=obstacles.ToArray();return source;
        }
        public static Cell From(int recipe,int rotation=0,int columns=9,int rows=9){var p=M70R2Fixtures.From(recipe);return Rotate(p.x,p.y,rotation,columns,rows);}
        public static Cell To(int rotation=0,int columns=9,int rows=9)=>Rotate(4,4,rotation,columns,rows);
        public static Cell Rotate(int x,int y,int rotation,int columns,int rows)
        {
            switch(rotation&3){case 1:return new Cell(rows-1-y,x);case 2:return new Cell(columns-1-x,rows-1-y);case 3:return new Cell(y,columns-1-x);default:return new Cell(x,y);}
        }
    }
}
#endif

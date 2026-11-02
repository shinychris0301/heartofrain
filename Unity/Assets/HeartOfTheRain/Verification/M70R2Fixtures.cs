#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System.Collections.Generic;
using HeartOfTheRain.M46;
namespace HeartOfTheRain.Verification {
 public static class M70R2Fixtures {
  public static LevelData Match(int kind,int columns=9,int rows=9){
   var colors=new int[columns,rows];for(int y=0;y<rows;y++)for(int x=0;x<columns;x++)colors[x,y]=(x+2*y)%6;
   colors[4,4]=5;
   if(kind==5){colors[4,3]=0;foreach(int x in new[]{2,3,5})colors[x,4]=0;}
   else if(kind==21){colors[4,5]=0;colors[4,2]=colors[4,3]=colors[3,4]=colors[5,4]=0;}
   else if(kind==11){colors[5,4]=0;colors[3,3]=colors[4,3]=colors[3,4]=0;}
   else {colors[4,1]=2;colors[3,4]=0;foreach(int y in new[]{2,3,5})colors[4,y]=0;if(kind==7){colors[4,6]=0;colors[4,7]=3;}}
   var cells=new List<Cell>();var gems=new List<GemCell>();var spawns=new List<Cell>();
   for(int y=0;y<rows;y++)for(int x=0;x<columns;x++){cells.Add(new Cell(x,y));if(y==rows-1)spawns.Add(new Cell(x,y));if(x==0&&y==0)continue;gems.Add(new GemCell{x=x,y=y,color=colors[x,y]});}
   return new LevelData{id="verification-M70R2-creation",globalLevel=1,columns=columns,rows=rows,movesProposal=20,tileSeed=17,activeCells=cells.ToArray(),spawnPoints=spawns.ToArray(),initialTiles=gems.ToArray(),obstacles=new[]{new ObstacleCell{x=0,y=0,family="stone",hp=3}},goals=new[]{new Goal{family="stone",count=1}},activeColors=new[]{0,1,2,3,4,5}};
  }
  public static Cell From(int kind)=>kind==5?new Cell(4,3):kind==21?new Cell(4,5):kind==11?new Cell(5,4):new Cell(3,4);
 }
}
#endif

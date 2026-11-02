#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;
using HeartOfTheRain.M46;
namespace HeartOfTheRain.Verification {
 // Isolated cloned level geometry. Never writes an authored asset or profile.
 public static class ObstacleDensityFixture {
  // Families a Double Orb at (4,5)/(5,5) damages through adjacency on the
  // cloned level-26 crate positions: crates fall, stones and sluices are fixed.
  // "tiles" keeps no obstacle at all, so the burst is gem breaks only.
  public static readonly string[] Families={"crate","stone","gate","tiles"};
  public static LevelData Level(LevelData source,int count,string family="crate"){
   if(Array.IndexOf(Families,family)<0)throw new ArgumentOutOfRangeException(nameof(family));
   var level=JsonUtility.FromJson<LevelData>(JsonUtility.ToJson(source));
   var positions=source.obstacles.Where(o=>o.family=="crate").OrderBy(o=>o.y).ThenBy(o=>o.x).ToArray();
   if(family=="tiles")count=0;
   if(count<0||count>positions.Length||(family!="tiles"&&count<1))throw new ArgumentOutOfRangeException(nameof(count));
   // Spread a fixed deterministic subset over the field, avoiding a density-
   // dependent clustering bias. All obstacles have one layer in these controls.
   var selected=Enumerable.Range(0,count).Select(i=>positions[i*positions.Length/count]).ToArray();
   var cells=new HashSet<int>(selected.Select(p=>p.y*level.columns+p.x));
   level.obstacles=selected.Select(p=>new ObstacleCell{x=p.x,y=p.y,family=family,hp=1}).ToArray();
   level.initialTiles=level.activeCells.Where(p=>!cells.Contains(p.y*level.columns+p.x)).Select(p=>new GemCell{x=p.x,y=p.y,color=(p.x+2*p.y)%6}).ToArray();
   level.activeColors=new[]{0,1,2,3,4,5};level.goals=count>0?new[]{new Goal{family=family,count=count}}:new[]{new Goal{family="crate",count=0}};level.deliveryExits=new Cell[0];level.mossRegrowth=null;
   // A gem-only board must not count as already won: keep one unreachable
   // crate goal out of the picture by giving it a real crate far from the orb.
   if(count==0){var far=positions.Last();level.obstacles=new[]{new ObstacleCell{x=far.x,y=far.y,family="crate",hp=3}};level.initialTiles=level.initialTiles.Where(t=>t.x!=far.x||t.y!=far.y).ToArray();level.goals=new[]{new Goal{family="crate",count=1}};}
   return level;
  }
  public static TurnResult Solve(BoardModel board){
   // These two authored gem cells stay gems in every cloned density. Keep the
   // power origin/partner fixed instead of choosing a density-dependent pair.
   var a=board.At(4,5);var b=board.At(5,5);
   if(a==null||b==null||a.family!="gem"||b.family!="gem")throw new InvalidOperationException("Fixed density swap cells unavailable");
   board.InjectReviewPower(a.x,a.y,7);board.InjectReviewPower(b.x,b.y,7);return board.Swap(a.x,a.y,b.x,b.y);
  }
 }
}
#endif

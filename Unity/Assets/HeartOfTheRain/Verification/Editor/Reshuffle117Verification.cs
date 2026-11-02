#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using UnityEditor;
using UnityEngine;
namespace HeartOfTheRain.Verification {
 public static class Reshuffle117Verification {
  [Serializable] public sealed class Report {public string status,scope="Unity Editor sampled reshuffle animation and real model reshuffle; not Android performance or visual acceptance.";public int checks;public List<string> errors=new List<string>();}
  public static void Run(){
   var r=new Report();void Check(bool ok,string message){r.checks++;if(!ok)r.errors.Add(message);}
   try {
    var gemA=new Piece{id=1,x=0,y=0,family="gem",color=0};
    var gemB=new Piece{id=2,x=8,y=8,family="gem",color=1};
    var fixedPiece=new Piece{id=3,x=4,y=5,family="crate",hp=1};
    var before=new BoardSnapshot{pieces=new[]{gemA,gemB,fixedPiece},goals=Array.Empty<Goal>()};
    var after=new BoardSnapshot{pieces=new[]{new Piece{id=1,x=0,y=0,family="gem",color=1},new Piece{id=2,x=8,y=8,family="gem",color=0},fixedPiece.Copy()},goals=Array.Empty<Goal>()};
    var phase=new BoardStep{kind="shuffle",duration=.45f,before=before,after=after};
    var view=new BoardPresentation{columns=9,rows=9};
    Func<float,int,DrawSprite> sample=(t,id)=>view.Sample(phase,before,t,0).Single(d=>d.pieceId==id);
    var start=sample(0,1);var early=sample(.1125f,1);var midpoint=sample(.225f,1);var late=sample(.3375f,1);var end=sample(.45f,1);
    Check(start.key=="tile0"&&Mathf.Abs(start.x)<.00001f&&Mathf.Abs(start.y)<.00001f&&Mathf.Abs(start.alpha-1)<.00001f,"Original gem starts in its original cell and colour");
    Check(early.x>0&&early.y>0&&early.sx<start.sx&&sample(.2025f,1).alpha<start.alpha,"Gem gathers and fades toward board centre");
    Check(midpoint.alpha<.001f&&midpoint.key=="tile1","New colour appears only when gem is invisible");
    Check(late.key=="tile1"&&late.x>0&&late.y>0&&late.sx<1&&sample(.2475f,1).alpha<1,"New gem releases from gathered pose");
    Check(end.key=="tile1"&&Mathf.Abs(end.x)<.00001f&&Mathf.Abs(end.y)<.00001f&&Mathf.Abs(end.sx-1)<.00001f&&Mathf.Abs(end.alpha-1)<.00001f,"New gem ends in exact target cell");
    var far=sample(.1125f,2);Check(far.x<8&&far.y<8,"Opposite gem also gathers inward");
    foreach(float t in new[]{0f,.1125f,.225f,.3375f,.45f}){var obstacle=sample(t,3);Check(obstacle.x==4&&obstacle.y==5&&obstacle.sx==1&&obstacle.alpha==1,"Obstacle stays fixed at "+t);}
    var savedBefore=JsonUtility.ToJson(before);var savedAfter=JsonUtility.ToJson(after);
    for(int i=0;i<=120;i++){float t=phase.duration*i/120;var d=sample(t,1);Check(d.x>=-.0001f&&d.y>=-.0001f&&d.x+d.sx*.5f<=.5001f&&d.y+d.sy*.5f<=.5001f&&d.alpha>=0&&d.alpha<=1,"Pose stays within the originating masked cell at "+i);}
    Check(savedBefore==JsonUtility.ToJson(before)&&savedAfter==JsonUtility.ToJson(after),"Sampling never mutates either snapshot");
    var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
    Check(ui&&ui.boards&&ui.boards.levels.Length==50,"Authored levels available");
    var level=JsonUtility.FromJson<LevelData>(ui.boards.levels[0].text);var board=new BoardModel(level);var result=new TurnResult();
    var shuffle=typeof(BoardModel).GetMethod("Shuffle",BindingFlags.NonPublic|BindingFlags.Instance);shuffle.Invoke(board,new object[]{result});
    Check(result.steps.Count==1&&result.steps[0].kind=="shuffle"&&Mathf.Abs(result.steps[0].duration-.45f)<.00001f,"Actual model produces existing bounded shuffle phase");
    var step=result.steps[0];Check(board.LegalSwaps().Count>0,"Actual shuffled model has an available move");
    Check(step.before.pieces.Length==step.after.pieces.Length&&step.before.pieces.All(p=>step.after.pieces.Any(q=>q.id==p.id&&q.x==p.x&&q.y==p.y&&q.family==p.family)),"Shuffle preserves identities and coordinates");
    Check(step.before.pieces.Where(p=>p.family=="gem").Select(p=>p.color).OrderBy(x=>x).SequenceEqual(step.after.pieces.Where(p=>p.family=="gem").Select(p=>p.color).OrderBy(x=>x)),"Shuffle preserves gem colour inventory");
    var actual=new BoardPresentation{columns=level.columns,rows=level.rows};
    foreach(var p in step.before.pieces.Where(q=>q.family=="gem")){
      var draw=actual.Sample(step,step.before,step.duration,0).Single(d=>d.pieceId==p.id);var final=step.after.pieces.Single(q=>q.id==p.id);
      Check(draw.key==BoardPresentation.BodyKey(final)&&Mathf.Abs(draw.x-final.x)<.00001f&&Mathf.Abs(draw.y-final.y)<.00001f,"Actual shuffled gem ends on its model colour and cell "+p.id);
    }
   }catch(Exception e){r.errors.Add(e.ToString());}
   r.status=r.errors.Count==0?"PASS_RESHUFFLE117":"FAIL_RESHUFFLE117";
   string folder=Environment.GetEnvironmentVariable("HOTR_RESHUFFLE117_OUTPUT")??"../Verification/Evidence/Review117/Reshuffle";
   Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"Reshuffle117.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(r.errors.Count==0?0:1);
  }
 }
}
#endif

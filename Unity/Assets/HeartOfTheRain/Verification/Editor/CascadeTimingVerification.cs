#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using Motion=HeartOfTheRain.M46.Motion;
namespace HeartOfTheRain.Verification {
 public static class CascadeTimingVerification {
  [Serializable] public class Row {public string name,turnHash,finalHash;public int matches,steps;public float seconds,wall15,wall30,wall60,maxLandingWait;}
  [Serializable] public class Report {public string status,utc,scope="Native Unity scheduling and deterministic frame-clock simulation; not measured Android frame rate.";public int checks;public List<Row> rows=new List<Row>();public List<string> errors=new List<string>();}
  static string Hash(string s){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(Encoding.UTF8.GetBytes(s))).Replace("-","").ToLowerInvariant();}
  public static float Wall(List<BoardStep> steps,int fps){float clock=0,started=0,wall=0;int index=0,guard=0;while(index<steps.Count&&guard++<100000){float advance=1f/fps;wall+=advance;while(index<steps.Count&&advance>0){var s=steps[index];advance=BoardPlayback.VisibleAdvance(s,advance,clock-started);float remaining=s.duration-(clock-started);if(advance<remaining){clock+=advance;advance=0;}else{clock+=remaining;advance-=remaining;index++;started=clock;}}}return wall;}
  public static void Baseline()=>Run(true);
  public static void Run()=>Run(false);
  static void Run(bool baseline){
   var r=new Report{utc=DateTime.UtcNow.ToString("o")};void Check(bool ok,string name){r.checks++;if(!ok&&r.errors.Count<80)r.errors.Add(name);}
   try{
    var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
    void Inspect(BoardModel board,TurnResult turn,string name){
     string raw=JsonUtility.ToJson(turn),state=JsonUtility.ToJson(board.Snapshot());var steps=BoardPlayback.Build(turn.steps,board.Level);
     Check(raw==JsonUtility.ToJson(turn)&&state==JsonUtility.ToJson(board.Snapshot()),name+" immutable solve");
     Check(ReferenceEquals(steps.Last().after,turn.steps.Last().after),name+" final snapshot");
     var row=new Row{name=name,turnHash=Hash(raw),finalHash=Hash(state),steps=steps.Count,matches=turn.steps.Count(s=>s.kind=="match"),seconds=steps.Sum(s=>s.duration),wall15=Wall(steps,15),wall30=Wall(steps,30),wall60=Wall(steps,60)};
     foreach(var s in steps){Check(s.duration>0&&!float.IsNaN(s.duration)&&!float.IsInfinity(s.duration),name+" finite phase");if(s.motion.Count>0&&(s.kind=="gravity"||s.kind=="powerFall"))row.maxLandingWait=Math.Max(row.maxLandingWait,s.duration-s.motion.Max(m=>m.delay+m.seconds));}
     if(!baseline){Check(row.wall15<=row.seconds+.15f,name+" 15fps clock does not dilate");Check(row.wall30<=row.seconds+.10f,name+" 30fps clock does not dilate");Check(row.wall60<=row.seconds+.06f,name+" 60fps clock does not dilate");}
     r.rows.Add(row);
    }
    for(int level=0;level<50;level++)foreach(int kind in new[]{-1,4,5,7,11,16,21}){
     var b=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[level].text));TurnResult turn;
     if(kind<0){var swap=b.LegalSwaps().FirstOrDefault();if(swap==null)continue;turn=b.Swap(swap[0].x,swap[0].y,swap[1].x,swap[1].y);}
     else {var p=b.Pieces.Values.First(v=>v.family=="gem");b.InjectReviewPower(p.x,p.y,kind);turn=b.Tap(p.x,p.y);}
     Inspect(b,turn,"L"+(level+1)+"_"+(kind<0?"match":"power"+kind));
    }
    if(!baseline)PresentationChecks(Check);
   }catch(Exception e){r.errors.Add(e.ToString());}
   r.status=r.errors.Count==0?"PASS_NATIVE_CASCADE_TIMING":"FAIL_NATIVE_CASCADE_TIMING";var folder=Path.GetFullPath("../Verification/Evidence/CascadeResponsiveness");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,baseline?"Before.json":"After.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(r.errors.Count==0?0:1);
  }
  static void PresentationChecks(Action<bool,string> check){
   var gem=new Piece{id=1,x=0,y=0,family="gem",color=0};var snapshot=new BoardSnapshot{pieces=new[]{gem},goals=new[]{new Goal{family="pod",count=1}},status="Playing"};
   var before=new BoardSnapshot{pieces=new[]{gem},goals=new[]{new Goal{family="pod",count=2}},status="Playing"};
   var flight=new BoardStep{kind="power",duration=.2f,before=before,after=snapshot};flight.collections.Add(new GoalCollection{family="pod",launch=.1f,arrival=1.45f});
   var next=new BoardStep{kind="match",duration=.16f,before=snapshot,after=snapshot};var view=new BoardPresentation{columns=1,rows=1};view.Add(flight,0);view.Add(next,.2f);
   check(view.HistoryLifetime(flight)>=1.70f,"Full collection/glint lifetime retained");
   check(view.DisplayGoalsLive(next,snapshot,.4f,.6f)[0].count==2,"Earlier flight does not debit next phase early");
   check(view.DisplayGoalsLive(null,snapshot,0,.6f)[0].count==2,"Idle counter holds unfinished collection");
   check(view.DisplayGoalsLive(null,snapshot,0,1.46f)[0].count==1,"Collection debits displayed goal exactly at arrival");
   check(view.Sample(next,snapshot,.6f,.2f).Any(d=>d.key=="waterSpirit"),"Full collection art survives phase transition");
   var root=new BoardStep{kind="powerFall",before=before,after=snapshot,playbackTracks=new List<PlaybackTrack>{new PlaybackTrack{step=flight,start=.3f,leadIn=.08f}}};var grouped=new BoardPresentation();grouped.Add(root,0);
   check(grouped.DisplayGoalsLive(root,snapshot,.6f,.6f)[0].count==2,"Active nested track is not counted twice");
   check(grouped.DisplayGoalsLive(next,snapshot,.1f,.8f)[0].count==2,"Earlier nested track holds counter once");
   check(grouped.DisplayGoalsLive(null,snapshot,0,1.68f)[0].count==1,"Nested track arrival uses retimed clock");
   grouped=new BoardPresentation();grouped.Add(root,10000);check(grouped.DisplayGoalsLive(root,snapshot,.4995f,10000.5f)[0].count==2,"Active collection ownership survives long-session clock precision");
   var fall=new BoardStep{kind="gravity",duration=TileFall.Duration(1),before=snapshot,after=snapshot};fall.motion.Add(new Motion{id=1,fromX=0,fromY=1,toX=0,toY=0,seconds=fall.duration,landing=TileFall.LandingSeconds});var landed=new BoardPresentation();landed.Add(fall,0);var settle=new BoardStep{kind="settled",before=snapshot,after=snapshot};landed.Add(settle,fall.duration);
   var pose=landed.Sample(settle,snapshot,fall.duration+.03f,fall.duration).Single(d=>d.pieceId==1);check(pose.y<0&&pose.sx>pose.sy,"Landing pose continues into following phase");
   landed.PruneHistory(fall.duration+.2f);pose=landed.Sample(null,snapshot,fall.duration+.2f,0).Single(d=>d.pieceId==1);check(pose.y==0&&pose.sx==pose.sy,"Landing ends at exact resting pose");
   foreach(int fps in new[]{15,20,24,30,60,120})check(Math.Abs(BoardPlayback.VisibleAdvance(fall,1f/fps,.02f)-1f/fps)<.000001f,"Normal frame advances wall time "+fps);
   foreach(float delta in new[]{.067f,.075f,.09f,.10f})check(BoardPlayback.VisibleAdvance(fall,delta,.02f)==delta,"Frame jitter does not enable slow motion "+delta);
   check(BoardPlayback.VisibleAdvance(fall,.18f,.02f)<.18f,"Exceptional stall retains visible flight poses");
  }
 }
}
#endif

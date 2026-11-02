#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using Motion=HeartOfTheRain.M46.Motion;
namespace HeartOfTheRain.Verification {
 public static class ObstacleFallVerification {
  [Serializable] class Report { public string status,utc,scope="Native Unity presentation checks against observed reference ranges; no pixel-identity or physical-device claim."; public int checks;public float oneCell,diagonal,landing,peakStretch;public List<string> failures=new List<string>(); }
  public static void Baseline()=>Run(true);
  public static void Run()=>Run(false);
  static float Advance(BoardStep s,float delta,float age){var m=typeof(BoardPlayback).GetMethod("VisibleAdvance");return (float)m.Invoke(null,m.GetParameters().Length==3?new object[]{s,delta,age}:new object[]{s,delta});}
  static void Run(bool baseline){
   var r=new Report{utc=DateTime.UtcNow.ToString("o")};void Check(bool ok,string label){r.checks++;if(!ok)r.failures.Add(label);}
   try {
    r.oneCell=TileFall.Duration(1);Check(r.oneCell>=.13f&&r.oneCell<=.18f,"One-cell flight stays within sampled reference range");
    foreach(int column in new[]{0,4,8}){
     var b=new BoardModel(PlaybackFixtures.StackedStones(column));var turn=b.UseBooster(BoosterKind.Hammer,column,2,new BoosterInventory());string model=JsonUtility.ToJson(b.Snapshot()),raw=JsonUtility.ToJson(turn);var schedule=BoardPlayback.Build(turn.steps,b.Level);
     Check(JsonUtility.ToJson(b.Snapshot())==model&&JsonUtility.ToJson(turn)==raw,"Presentation preserves model and raw steps "+column);
     var s=schedule.First(v=>v.motion.Any(m=>m.fromX!=m.toX));var motion=s.motion.First(m=>m.fromX!=m.toX);r.diagonal=motion.seconds;r.landing=motion.landing;
     Check(Math.Abs(motion.seconds-TileFall.Duration((float)Math.Sqrt(2)))<.0001f,"Diagonal duration includes full travel distance "+column);
     Check(motion.landing>=.09f&&motion.landing<=.13f,"Short reference-like landing settle "+column);
     var view=new BoardPresentation();var mid=view.Sample(s,s.before,motion.delay+motion.seconds*.5f,0).Single(d=>d.pieceId==motion.id);r.peakStretch=mid.sy/mid.sx;
     Check(r.peakStretch>=1.04f&&r.peakStretch<=1.10f,"Subtle visible stretch during travel "+column);
     var start=view.Sample(s,s.before,0,0).Single(d=>d.pieceId==motion.id);var end=view.Sample(s,s.before,s.duration+TileFall.LandingSeconds,0).Single(d=>d.pieceId==motion.id);
     Check(start.x==motion.fromX&&start.y==motion.fromY,"Exact fall source "+column);Check(Math.Abs(end.x-motion.toX)<.0001f&&Math.Abs(end.y-motion.toY)<.0001f&&Math.Abs(end.sx-end.sy)<.0001f,"Exact resting cell and scale "+column);
     float age=0;int visible=0,guard=0;while(age<s.duration&&guard++<100){age+=Advance(s,.5f,age);if(age>motion.delay&&age<motion.delay+motion.seconds)visible++;}
     Check(visible>=4,"Late frame retains at least four moving poses "+column);Check(guard<100,"Late-frame playback terminates "+column);
     Check(Advance(s,.01f,0)==.01f,"Normal frame speed unchanged "+column);
     for(int i=0;i<=60;i++){float t=s.duration*i/60;var body=view.Sample(s,s.before,t,0).Single(d=>d.pieceId==motion.id);Check(body.x>=Math.Min(motion.fromX,motion.toX)-.001f&&body.x<=Math.Max(motion.fromX,motion.toX)+.001f&&body.y>=motion.toY-.05f&&body.y<=motion.fromY+.001f,"Fall stays within reserved route "+column+"/"+i);}
     b.Validate();
    }
    var natural=new BoardModel(ObstacleFallTouchProbe.MatchFixture());int feeding=natural.At(3,4).id;var action=natural.Swap(3,0,3,1);
    Check(action.accepted&&natural.Moves==19,"Natural-match input accepted once");Check(natural.At(4,2)?.id==feeding,"Natural match feeds the released obstacle cell");Check(natural.At(4,3)?.family=="stone"&&natural.At(4,4)?.family=="stone"&&natural.Goals["stone"]==2,"Natural match preserves upper blockers");
    var delayed=new BoardStep{kind="powerFall",duration=4};delayed.motion.Add(new Motion{delay=2,seconds=.15f,landing=.1f});
    Check(Advance(delayed,.5f,0)==.5f,"Unrelated anticipation is not slowed");Check(Advance(delayed,3,0)<=2.04f,"Late frame stops inside the future fall");
    Check(Advance(new BoardStep{kind="powerFall",duration=4},.5f,0)==.5f,"VFX-only tails retain original clock");
   }catch(Exception e){r.failures.Add(e.ToString());}
   r.status=r.failures.Count==0?"PASS_NATIVE_OBSTACLE_FALL":"FAIL_NATIVE_OBSTACLE_FALL";string folder=Path.GetFullPath("../Verification/Evidence/ObstacleFall");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,baseline?"Recorded_Before.json":"Native_Checks.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(baseline?0:r.failures.Count==0?0:1);
  }
 }
}
#endif

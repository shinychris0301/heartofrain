#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 public static class M70R2Verification {
  [Serializable] class Supplied {public bool passed;public string[] checks,errors;}
  [Serializable] class Report {public string utc,status,scope="Native Unity supplied sampler runner plus live atlas binding, real model recipes, continuous falls, conversion phases and pooled sampling checks. Device evidence is separate.";public int checks,creationFrames,conversionBodies;public List<string> failures=new List<string>();}
  public static void Run(){
   var r=new Report{utc=DateTime.UtcNow.ToString("o")};var dir=Path.GetFullPath("../Verification/Evidence/M70R2");Directory.CreateDirectory(dir);M46AtlasBank bank=null;
   void Check(bool value,string label){r.checks++;if(!value)r.failures.Add(label);}
   try{
    HeartOfTheRain.M69.M70PowerCreationCheck.Validate();File.Copy("Temp/M70R2_CreationChecks.json",Path.Combine(dir,"Supplied_Checks.json"),true);var supplied=JsonUtility.FromJson<Supplied>(File.ReadAllText("Temp/M70R2_CreationChecks.json"));Check(supplied.passed,"Supplied R2 runner: "+string.Join(";",supplied.errors));
    var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");bank=new M46AtlasBank(ui.boards);
    foreach(int kind in new[]{4,5,21,7,11,16}){
     int atlas=BoardPresentation.PowerAtlas(kind);var p=new Piece{id=1,x=2,y=3,family="power",power=kind};var snap=new BoardSnapshot{pieces=new[]{p},goals=new Goal[0]};var view=new BoardPresentation();view.RegisterPowerCreation(p,0);
     int frames=kind==11||kind==16?9:18;
     for(int n=0;n<frames;n++){float time=(n+.1f)/30;var d=view.Sample(null,snap,time,0).Single(x=>x.pieceId==1);Check(d.key==BoardPresentation.CreationClip(atlas),"Authored creation selected "+kind+"/"+n);var sprite=bank.Get(d);Check(sprite&&sprite.rect.width>0&&sprite.rect.height>0,"Actual bound creation frame "+kind+"/"+n);r.creationFrames++;}
     var end=view.Sample(null,snap,BoardPresentation.CreationDuration(atlas)+.1f,0).Single(d=>d.pieceId==1);Check(end.key==BoardPresentation.Idle(atlas)&&Math.Abs(end.age-.1f)<.001f,"Creation enters uninterrupted idle "+kind);
     for(int n=0;n<20;n++)view.SampleLive(null,snap,2,0);long bytes=GC.GetAllocatedBytesForCurrentThread();for(int n=0;n<1000;n++)view.SampleLive(null,snap,2,0);Check(GC.GetAllocatedBytesForCurrentThread()==bytes,"No added per-frame allocations for birth/idle "+kind);
    }
    foreach(var shape in new[]{new[]{9,9},new[]{9,11},new[]{11,11}})foreach(int kind in new[]{4,5,21,7,11}){
     var board=new BoardModel(M70R2Fixtures.Match(kind,shape[0],shape[1]));var from=M70R2Fixtures.From(kind);var turn=board.Swap(from.x,from.y,4,4);var raw=JsonUtility.ToJson(turn);var final=JsonUtility.ToJson(board.Snapshot());var made=turn.steps.First(s=>s.kind=="match").created.Single();Check(turn.accepted&&made.power==kind&&made.x==4&&made.y==4,"Real match recipe and anchor "+kind+"/"+shape[1]);
     var view=new BoardPresentation();float time=0,born=-1;bool sawCreate=false,sawMovingStar=false;
     foreach(var step in BoardPlayback.Build(turn.steps,board.Level)){
      view.Add(step,time);if(step.created.Any(p=>p.id==made.id))born=time;
      for(int n=1;n<20;n++){float at=time+step.duration*n/20;var draws=view.Sample(step,step.before,at,time);var body=draws.FirstOrDefault(d=>d.pieceId==made.id&&d.bank=="power");if(body==null||born<0)continue;
       if(at-born<BoardPresentation.CreationDuration(body.atlas)){Check(body.key==BoardPresentation.CreationClip(body.atlas),"Birth clock survives active step "+kind);sawCreate=true;}
       if(at-born<10f/30f){var stars=draws.Where(d=>d.key=="StarCreate").ToArray();Check(stars.Any(d=>Math.Abs(d.x-body.x)<.001f&&Math.Abs(d.y-body.y)<.001f),"Star follows newborn position "+kind);if(step.kind=="gravity"||step.kind=="powerFall")sawMovingStar=true;}
       bank.Get(body);
      }time+=step.duration;
     }
     Check(sawCreate,"Real recipe draws creation "+kind);Check(sawMovingStar,"Creation accent continues into refill "+kind);Check(raw==JsonUtility.ToJson(turn)&&final==JsonUtility.ToJson(board.Snapshot()),"Visual clocks do not mutate solve "+kind);board.Validate();
    }
    foreach(int kind in Enumerable.Range(0,22)){
     var plan=ReviewPlan.Build(9,9,kind,new Vector2Int(4,4),false);var empty=new BoardSnapshot{pieces=new Piece[0],goals=new Goal[0]};var step=new BoardStep{kind="power",before=empty,after=empty,powerPlan=plan};var view=new BoardPresentation();view.Add(step,0);
     foreach(var power in plan.powers.Where(p=>p.begin>0)){
      float window=power.end-Math.Max(0,power.charge)-power.begin;if(window<=0)continue;float at=power.begin+Math.Min(window,BoardPresentation.CreationDuration(power.atlas))*.5f;
      var body=view.Sample(step,empty,at,0).First(d=>d.order==20&&d.atlas==power.atlas&&Math.Abs(d.x-power.x)<.001f&&Math.Abs(d.y-power.y)<.001f);Check(body.key==BoardPresentation.CreationClip(power.atlas)&&body.alpha==1,"Converted body uses authored formation "+kind);Check(bank.Get(body),"Converted creation clip exists "+kind);r.conversionBodies++;
     }
    }
   }catch(Exception e){r.failures.Add(e.ToString());}
   finally{if(bank!=null){var cache=(IDictionary)typeof(M46AtlasBank).GetField("sprites",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(bank);foreach(var entry in cache.Values){var sprite=(Sprite)entry.GetType().GetField("sprite").GetValue(entry);if(sprite)UnityEngine.Object.DestroyImmediate(sprite);}cache.Clear();bank.Dispose();}}
   r.status=r.failures.Count==0?"PASS_NATIVE_M70R2_CREATION":"FAIL_NATIVE_M70R2_CREATION";File.WriteAllText(Path.Combine(dir,"Native_Checks.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(r.failures.Count==0?0:1);
  }
 }
}
#endif

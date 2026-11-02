#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 public static class ObstacleDensityChecks {
  [Serializable]class Report {public string status,utc,error;public int checks,damageQueries,sortCases,realReplays;}
  static Report report;static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
  static void Check(bool ok,string name){report.checks++;if(!ok)throw new Exception(name);}
  public static void Run(){
   report=new Report{utc=DateTime.UtcNow.ToString("o")};try{
    var view=new BoardPresentation();var cache=typeof(BoardPresentation).GetMethod("CacheActiveDamage",Private);var query=typeof(BoardPresentation).GetMethod("ActiveDamage",Private);var reference=typeof(BoardPresentation).GetMethod("LastDamage",BindingFlags.Static|BindingFlags.NonPublic);var rng=new System.Random(74219);
    var lookup=typeof(BoardPresentation).GetField("activeDamage",Private).GetValue(view);var storage=lookup.GetType().GetFields(Private).Where(f=>f.FieldType.IsArray).Select(f=>new {field=f,array=(Array)f.GetValue(lookup)}).Where(x=>x.array!=null).ToArray();Check(storage.Length>0&&storage.All(x=>x.array.Length>=128),"Damage cache storage reserved before first hit");var full=new BoardStep();for(int i=0;i<121;i++)full.damage.Add(new Damage{id=i,time=0});cache.Invoke(view,new object[]{full,0f});Check(storage.All(x=>ReferenceEquals(x.array,x.field.GetValue(lookup))),"Full authored-board hit does not grow cache storage");
    for(int trial=0;trial<20;trial++){
     var step=new BoardStep();for(int i=0;i<80;i++)step.damage.Add(new Damage{id=rng.Next(12),time=i%17==0?float.NaN:rng.Next(5)*.15f,beforeHP=3,afterHP=2,family="crate"});
     foreach(float age in new[]{-1,0,.15f,.3f,.45f,1,.3f,-1,float.NaN,float.PositiveInfinity,float.NegativeInfinity}){
      cache.Invoke(view,new object[]{step,age});for(int id=0;id<13;id++){var a=reference.Invoke(null,new object[]{step,id,age});var b=query.Invoke(view,new object[]{step,id,age});Check(ReferenceEquals(a,b),"Damage ordering/time boundary "+trial+"/"+age+"/"+id);report.damageQueries++;}
     }
    }
    var sort=typeof(BoardPresentation).GetMethod("SortDraws",Private);
    foreach(int count in new[]{0,1,2,31,32,33,128,512})foreach(int width in new[]{8,256,257,int.MaxValue}){
     var list=new List<DrawSprite>();for(int i=0;i<count;i++)list.Add(new DrawSprite{order=width==int.MaxValue?(i%2==0?int.MinValue:int.MaxValue):rng.Next(width)-width/2,pieceId=i});var expected=list.OrderBy(d=>d.order).ToArray();sort.Invoke(view,new object[]{list});Check(list.SequenceEqual(expected),"Stable sort boundary "+count+"/"+width);report.sortCases++;
    }
    var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
    foreach(int level in new[]{11,22,25,41,48})foreach(string kind in new[]{"double_orb","orb_rocket","rocket_chain"}){
     var board=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[level].text));var turn=CrateBurstVerification.Solve(board,kind);Check(turn.accepted,"Real turn accepted");var steps=BoardPlayback.Build(turn.steps,board.Level);var a=CrateBurstVerification.View(ui,board.Level.columns,board.Level.rows);a.VerificationUseLegacyDensityWork=true;var b=CrateBurstVerification.View(ui,board.Level.columns,board.Level.rows);float start=0;
     foreach(var step in steps){a.Add(step,start);b.Add(step,start);int frames=Math.Max(1,Mathf.CeilToInt(step.duration*30));for(int frame=0;frame<frames;frame++){float at=start+step.duration*(frame+.1f)/frames;a.PruneHistory(at);b.PruneHistory(at);var old=a.SampleLive(step,step.before,at,start);var current=b.SampleLive(step,step.before,at,start);Check(old.Count==current.Count,"Draw count");for(int i=0;i<old.Count;i++)Check(JsonUtility.ToJson(old[i])==JsonUtility.ToJson(current[i]),"Exact real replay pose "+level+kind+"/"+frame+"/"+i);}start+=step.duration;}report.realReplays++;
    }
    report.status="PASS_NATIVE_DENSITY_REGRESSION";
   }catch(Exception e){report.status="FAIL_NATIVE_DENSITY_REGRESSION";report.error=e.ToString();}
   File.WriteAllText(Path.GetFullPath("../Verification/Evidence/ObstacleDensity/Regression_Checks.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.error==null?0:1);
  }
 }
}
#endif

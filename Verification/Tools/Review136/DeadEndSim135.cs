// Not part of the Unity project. To rerun, copy to Assets/<any>/Editor/ in an isolated project copy, set
// HOTR_SIM135_OUT, run with -batchmode -nographics -executeMethod DeadEndSim135.Run, then remove it.
// Plays the real BoardModel with simple policies and records how each run ends. "hint" plays legal[0], the move the game's hint shows.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
public static class DeadEndSim135
{
    static string Out=>Environment.GetEnvironmentVariable("HOTR_SIM135_OUT");
    static int Touching(BoardModel b,Cell[] m){int n=0;var seen=new HashSet<int>();foreach(var c in m)foreach(var d in new[]{(1,0),(-1,0),(0,1),(0,-1)}){var key=(c.x+d.Item1)+(c.y+d.Item2)*b.Level.columns;if(seen.Add(key)&&b.Pieces.TryGetValue(key,out var p)&&p.family!="gem"&&p.family!="power")n++;}return n;}
    static Cell[] Pick(BoardModel b,List<Cell[]> legal,string policy,System.Random r){
        if(policy=="random")return legal[r.Next(legal.Count)];
        if(policy=="lowest")return legal.OrderBy(m=>Math.Min(m[0].y,m[1].y)).ThenBy(_=>r.Next()).First();
        if(policy=="highest")return legal.OrderByDescending(m=>Math.Max(m[0].y,m[1].y)).ThenBy(_=>r.Next()).First();
        if(policy=="hint")return legal[0];
        return legal.OrderByDescending(m=>Touching(b,m)).ThenBy(_=>r.Next()).First();
    }
    public static void Run(){
        var sb=new StringBuilder();var dir=Path.Combine(Application.dataPath,"HeartOfTheRain/M47/Data/Levels");
        foreach(var entry in new[]{(from:1,to:50,runs:40),(from:17,to:17,runs:300)})
        for(int n=entry.from;n<=entry.to;n++){
            var level=JsonUtility.FromJson<LevelData>(File.ReadAllText(Path.Combine(dir,$"C01_L{n:000}.json")));
            foreach(var policy in new[]{"random","lowest","highest","hint","obstacle"}){
                var ends=new Dictionary<string,int>();int usedAtDead=0,dead=0;
                for(int run=0;run<entry.runs;run++){
                    var r=new System.Random(n*1000+run);var b=new BoardModel(level,(uint)(77001+run*13+n));int start=b.Moves,guard=0;
                    while(b.Status=="Playing"&&guard++<400){
                        var power=b.Pieces.Values.Where(p=>p.family=="power").OrderBy(p=>p.id).FirstOrDefault();var legal=b.LegalSwaps();
                        if(power!=null&&(legal.Count==0||r.Next(3)==0)){b.Tap(power.x,power.y);continue;}
                        if(legal.Count==0)break;var m=Pick(b,legal,policy,r);b.Swap(m[0].x,m[0].y,m[1].x,m[1].y);
                    }
                    ends.TryGetValue(b.Status,out var c);ends[b.Status]=c+1;if(b.Status=="No legal moves"){dead++;usedAtDead+=start-b.Moves;}
                }
                sb.AppendLine($"L{n} runs={entry.runs} {policy}: "+string.Join(", ",ends.OrderBy(k=>k.Key).Select(k=>k.Key+"="+k.Value))+(dead>0?$" avgMovesUsedAtDeadEnd={usedAtDead/dead}":""));
                File.WriteAllText(Out,sb.ToString());
            }
        }
        sb.AppendLine("DONE");File.WriteAllText(Out,sb.ToString());EditorApplication.Exit(0);
    }
}

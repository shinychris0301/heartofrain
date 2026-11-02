#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;

namespace HeartOfTheRain.Verification {
    // Review 136: Level 17 through the real BoardModel. The opened spawn must end the dead end
    // for every play style, stay winnable, and leave the retained original playable by hash.
    public static class Level17Review136Verification {
        [Serializable] sealed class Report{public string status="FAIL";public int checks,runs,deadEnds,wins;public List<string> passed=new List<string>(),errors=new List<string>();}
        static Report report;
        static void Check(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);report.passed.Add(label);}
        static int Touching(BoardModel b,Cell[] m){int n=0;var seen=new HashSet<int>();foreach(var c in m)foreach(var d in new[]{(1,0),(-1,0),(0,1),(0,-1)}){int key=(c.x+d.Item1)+(c.y+d.Item2)*b.Level.columns;if(seen.Add(key)&&b.Pieces.TryGetValue(key,out var p)&&p.family!="gem"&&p.family!="power")n++;}return n;}
        static Cell[] Pick(BoardModel b,List<Cell[]> legal,int policy,System.Random r){
            switch(policy){
                case 0:return legal[r.Next(legal.Count)];
                case 1:return legal.OrderBy(m=>Math.Min(m[0].y,m[1].y)).ThenBy(_=>r.Next()).First();
                case 2:return legal.OrderByDescending(m=>Math.Max(m[0].y,m[1].y)).ThenBy(_=>r.Next()).First();
                case 3:return legal[0];
                default:return legal.OrderByDescending(m=>Touching(b,m)).ThenBy(_=>r.Next()).First();
            }
        }
        public static void Run(){
            report=new Report();
            try{
                string current=File.ReadAllText("Assets/HeartOfTheRain/M47/Data/Levels/C01_L017.json");var level=JsonUtility.FromJson<LevelData>(current);
                Check(level.spawnPoints.Any(s=>!level.obstacles.Any(o=>o.x==s.x&&o.y==s.y)),"At least one Level 17 spawn is open");
                Check(level.initialTiles.Any(t=>t.x==4&&t.y==10)&&level.goals.First(g=>g.family=="moss").count==level.obstacles.Count(o=>o.family=="moss"),"Opened cell holds a gem and the moss goal matches the board");
                var opening=new BoardModel(level);opening.Validate();Check(opening.LegalSwaps().Count>0&&opening.Status=="Playing","Level 17 opens valid with legal moves");
                string original=File.ReadAllText("Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117/C01_L017.json");var kept=JsonUtility.FromJson<LevelData>(original);
                Check(kept.spawnPoints.All(s=>kept.obstacles.Any(o=>o.x==s.x&&o.y==s.y)),"Retained original keeps its old layout for attempts bound to it");
                var catalog=File.ReadAllText("../Backend/config/levels.json");Check(catalog.Contains(ProfileJson.Hash(current)),"Server catalog names the new Level 17");
                foreach(var policy in Enumerable.Range(0,5))for(int run=0;run<200;run++){
                    var r=new System.Random(170000+run);var b=new BoardModel(level,(uint)(77001+run*13));int guard=0;report.runs++;
                    while(b.Status=="Playing"&&guard++<400){
                        var power=b.Pieces.Values.Where(p=>p.family=="power").OrderBy(p=>p.id).FirstOrDefault();var legal=b.LegalSwaps();
                        if(power!=null&&(legal.Count==0||r.Next(3)==0)){b.Tap(power.x,power.y);continue;}
                        if(legal.Count==0)break;var m=Pick(b,legal,policy,r);b.Swap(m[0].x,m[0].y,m[1].x,m[1].y);
                    }
                    if(b.Status=="No legal moves")report.deadEnds++;if(b.Status=="Won")report.wins++;
                }
                Check(report.deadEnds==0,"No play style reaches a dead end on Level 17");Check(report.wins>0,"Level 17 stays winnable");
                report.status="PASS_NATIVE_LEVEL17_REVIEW136";
            }catch(Exception problem){report.errors.Add(problem.Message);}
            string output=Environment.GetEnvironmentVariable("HOTR_VERIFICATION_OUTPUT");output=string.IsNullOrEmpty(output)?Path.GetFullPath("../Verification/Evidence/Review136"):output;Directory.CreateDirectory(output);
            File.WriteAllText(Path.Combine(output,"Level17Review136.json"),JsonUtility.ToJson(report,true));
            EditorApplication.Exit(report.status.StartsWith("PASS")?0:1);
        }
    }
}
#endif

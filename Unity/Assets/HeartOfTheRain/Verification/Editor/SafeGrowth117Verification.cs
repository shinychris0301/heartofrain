#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;

namespace HeartOfTheRain.Verification {
    // White-box clock/eligibility fixtures for opt-in growth only. They use
    // temporary in-memory boards and do not alter campaign assets or profiles.
    public static class SafeGrowth117Verification {
        [Serializable] sealed class Report { public string status="FAIL",scope="White-box temporary board fixtures; no gameplay playback, backend, device or balance acceptance."; public int checks; public List<string> failures=new List<string>(); }
        static Report report;
        static void Check(bool ok,string why){report.checks++;if(!ok)report.failures.Add(why);}
        static void Set(BoardModel b,string name,object value){var f=typeof(BoardModel).GetField(name,BindingFlags.NonPublic|BindingFlags.Instance);if(f==null)throw new InvalidOperationException("Missing fixture field "+name);f.SetValue(b,value);}
        static void Grow(BoardModel b){var method=typeof(BoardModel).GetMethod("Regrow",BindingFlags.NonPublic|BindingFlags.Instance);if(method==null)throw new InvalidOperationException("Missing growth method");method.Invoke(b,new object[]{new TurnResult()});}
        static BoardModel Board(bool safe){
            var cells=new List<Cell>();var gems=new List<GemCell>();var spawns=new List<Cell>();
            for(int x=0;x<3;x++)for(int y=0;y<3;y++){cells.Add(new Cell(x,y));if(y>0)gems.Add(new GemCell{x=x,y=y,color=(x+2*y)%4});if(y==2)spawns.Add(new Cell(x,y));}
            return new BoardModel(new LevelData{id="safe-growth-fixture",globalLevel=27,columns=3,rows=3,movesProposal=20,tileSeed=17,activeCells=cells.ToArray(),initialTiles=gems.ToArray(),spawnPoints=spawns.ToArray(),deliveryExits=Array.Empty<Cell>(),
                obstacles=new[]{new ObstacleCell{x=0,y=0,family="moss",hp=1},new ObstacleCell{x=1,y=0,family="moss",hp=1},new ObstacleCell{x=2,y=0,family="moss",hp=1}},
                goals=new[]{new Goal{family="moss",count=3}},activeColors=new[]{0,1,2,3},mossRegrowth=new GrowthRule{enabled=true,safeSegmentBottom=safe,undamagedMoves=2,maxNewClumps=3}});
        }
        public static void Run(){
            report=new Report();string root=Path.GetFullPath("..");string output=Environment.GetEnvironmentVariable("HOTR_CAMPAIGN117_OUTPUT");if(string.IsNullOrEmpty(output))output=Path.Combine(root,"Verification/Evidence/Review117");Directory.CreateDirectory(output);
            try {
                var legacy=Board(false);Set(legacy,"<QuietMoves>k__BackingField",1);Grow(legacy);
                Check(legacy.GrowthUsed==1&&legacy.At(0,1).family=="moss","Legacy no-flag board grows at its original upper option");
                Check(legacy.Goals["moss"]==4&&legacy.QuietMoves==0,"Legacy growth increments its goal and resets clock");
                var safe=Board(true);string before=JsonUtility.ToJson(safe.Snapshot());Set(safe,"<QuietMoves>k__BackingField",1);Grow(safe);
                Check(safe.GrowthUsed==0&&safe.QuietMoves==2,"No safe target defers without consuming growth or resetting clock");
                Check(JsonUtility.ToJson(safe.Snapshot())==before,"Deferral leaves pieces, moves, goals and status unchanged");
                var freed=safe.At(1,0);freed.family="gem";freed.hp=0;freed.color=1;safe.Goals["moss"]--;safe.Validate();Grow(safe);
                Check(safe.GrowthUsed==1&&safe.At(1,0).family=="moss","Saturated clock retries when a safe bottom cell becomes eligible");
                Check(safe.Goals["moss"]==3&&safe.QuietMoves==0,"Successful safe growth increments the goal exactly once and resets clock");
                var hit=Board(true);Set(hit,"<QuietMoves>k__BackingField",2);Set(hit,"mossHit",true);Grow(hit);
                Check(hit.QuietMoves==0&&hit.GrowthUsed==0,"Damage resets the clock without growth");
                var limited=Board(true);Set(limited,"<QuietMoves>k__BackingField",1);Set(limited,"<GrowthUsed>k__BackingField",3);Grow(limited);
                Check(limited.GrowthUsed==3&&limited.Goals["moss"]==3,"Growth limit remains enforced");
                if(report.failures.Count==0)report.status="PASS_WHITE_BOX";
            }catch(Exception e){report.failures.Add(e.ToString());}
            File.WriteAllText(Path.Combine(output,"SafeGrowth117.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.failures.Count==0?0:1);
        }
    }
}
#endif

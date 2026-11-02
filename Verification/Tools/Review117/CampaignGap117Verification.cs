#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M48;

namespace HeartOfTheRain.Verification {
    // Replays already-verified diagnostic wins to inspect settled vacant cells.
    public static class CampaignGap117Verification {
        [Serializable] sealed class SolverRow { public int level; public string status; public CampaignReplay replay; }
        [Serializable] sealed class SolverReport { public SolverRow[] levels; }
        [Serializable] sealed class EmptyCell { public int x,y,segmentTop,blockerY; public bool hasSpawn; public string blockerFamily; }
        [Serializable] sealed class Gap { public int actionIndex,turn; public BoardSnapshot snapshot; public List<EmptyCell> cells=new List<EmptyCell>(); }
        [Serializable] sealed class Row { public int level;public string error,status;public uint seed; public List<Gap> gaps=new List<Gap>(); }
        [Serializable] sealed class Report { public string status="FAIL",scope="Replayed bounded model wins only; no visual, device or complete-coverage claim."; public int errors;public List<Row> levels=new List<Row>(); }
        static void Need(bool ok,string why){if(!ok)throw new InvalidOperationException(why);}
        public static void Run(){
            string root=Path.GetFullPath("..");string input=Environment.GetEnvironmentVariable("HOTR_CAMPAIGN117_INPUT");
            if(string.IsNullOrEmpty(input))input=Path.Combine(root,".verification-cache/Review117/CampaignVaried03");
            string replay=Environment.GetEnvironmentVariable("HOTR_GAP117_REPLAY");
            if(string.IsNullOrEmpty(replay))replay=Path.Combine(root,"Verification/Evidence/Review117/Native/SolverVaried02/CampaignSolver117.json");
            string output=Environment.GetEnvironmentVariable("HOTR_CAMPAIGN117_OUTPUT");if(string.IsNullOrEmpty(output))output=Path.Combine(root,"Verification/Evidence/Review117");
            Directory.CreateDirectory(output);var report=new Report();
            try {
                var data=JsonUtility.FromJson<SolverReport>(File.ReadAllText(replay));Need(data!=null&&data.levels!=null,"Missing solver report");
                foreach(var entry in data.levels){
                    var row=new Row{level=entry.level};report.levels.Add(row);
                    try {
                        Need(entry.replay!=null&&entry.status=="WIN_REPLAY_VERIFIED","Missing verified winning replay");
                        var path=Path.Combine(input,"C01_L"+entry.level.ToString("000")+".json");var level=JsonUtility.FromJson<LevelData>(File.ReadAllText(path));
                        row.seed=(uint)entry.replay.seed;var board=new BoardModel(level,row.seed);
                        for(int i=0;i<entry.replay.actions.Length;i++){
                            TurnResult result;string error;Need(CampaignReplayRules.Apply(board,entry.replay.actions[i],out result,out error),"Replay mismatch: "+error);board.Validate();
                            var missing=board.Active.Where(k=>!board.Pieces.ContainsKey(k)).OrderBy(k=>k).ToArray();
                            if(missing.Length==0||row.gaps.Count>=3)continue;
                            var gap=new Gap{actionIndex=i,turn=board.Turn,snapshot=board.Snapshot()};row.gaps.Add(gap);
                            foreach(int k in missing){
                                int x=k%level.columns,y=k/level.columns,top=y;
                                while(top+1<level.rows&&board.Inside(x,top+1)){
                                    var next=board.At(x,top+1);if(next!=null&&!next.Movable)break;top++;
                                }
                                var blocker=top+1<level.rows?board.At(x,top+1):null;
                                gap.cells.Add(new EmptyCell{x=x,y=y,segmentTop=top,hasSpawn=board.Spawns.Contains(board.Key(x,top)),
                                    blockerY=blocker==null?-1:blocker.y,blockerFamily=blocker==null?"":blocker.family});
                            }
                        }
                        Need(board.Status=="Won","Replay did not win");row.status="REPLAYED";
                    }catch(Exception e){row.status="ERROR";row.error=e.ToString();report.errors++;}
                }
                if(report.errors==0)report.status="PASS_CAPTURED";
            }catch(Exception e){report.errors++;Debug.LogError(e);}
            File.WriteAllText(Path.Combine(output,"CampaignGaps117.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.errors==0?0:1);
        }
    }
}
#endif

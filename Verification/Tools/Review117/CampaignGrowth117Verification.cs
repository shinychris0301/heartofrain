#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M48;

namespace HeartOfTheRain.Verification {
    // Attempts to trigger original moss growth through ordinary legal actions.
    // No level, model, RNG, or power is directly altered.
    public static class CampaignGrowth117Verification {
        [Serializable] sealed class Trial { public uint seed;public string status,error;public int actions,growth,turnsWithGaps,maxGaps,discardedHazards;public BoardSnapshot firstGap;public List<ReplayMove> history=new List<ReplayMove>(); }
        [Serializable] sealed class Row { public int level,growthTrials,gapTrials,errors;public string levelSHA256;public List<Trial> trials=new List<Trial>(); }
        [Serializable] sealed class Report { public string status="FAIL",scope="Bounded ordinary-move model search; a gap-free sample does not prove all future states safe or establish human balance/device acceptance.";public int errors,gapTrials;public List<Row> levels=new List<Row>(); }
        static void Need(bool ok,string why){if(!ok)throw new InvalidOperationException(why);}
        static string Sha(string path){using(var h=SHA256.Create())using(var f=File.OpenRead(path))return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
        static List<ReplayMove> Actions(BoardModel b){var a=new List<ReplayMove>();foreach(var p in b.Pieces.Values.Where(p=>p.family=="power").OrderBy(p=>p.id))a.Add(new ReplayMove{kind="tap",ax=p.x,ay=p.y});foreach(var pair in b.LegalSwaps())a.Add(new ReplayMove{kind="swap",ax=pair[0].x,ay=pair[0].y,bx=pair[1].x,by=pair[1].y});return a;}
        static TurnResult Apply(BoardModel b,ReplayMove m)=>m.kind=="tap"?b.Tap(m.ax,m.ay):b.Swap(m.ax,m.ay,m.bx,m.by);
        static Trial Play(LevelData level,uint seed){
            var r=new Trial{seed=seed};
            try{
                var b=new BoardModel(level,seed);var random=new System.Random((int)(seed%int.MaxValue));
                while(b.Status=="Playing"&&b.Moves>0&&r.history.Count<level.movesProposal+10){
                    var actions=Actions(b);Need(actions.Count>0,"Playing board has no legal action");
                    var sampled=actions.OrderBy(x=>random.Next()).Take(12).ToArray();var checkpoint=b.Checkpoint();double best=double.NegativeInfinity;ReplayMove chosen=null;BoardModel next=null;
                    foreach(var action in sampled){
                        try{
                            var c=BoardModel.FromCheckpoint(level,checkpoint);var result=Apply(c,action);
                            if(result==null||!result.accepted||c.Status=="No legal moves"||c.Status=="Resolution limit"||c.Status=="Engine fault"){r.discardedHazards++;continue;}
                            // Before the first growth prefer quiet moves, then
                            // continue with a bounded ordinary random policy.
                            double score=b.GrowthUsed==0?c.GrowthUsed*10000+c.QuietMoves*100-(b.Goals["moss"]-c.Goals["moss"])*20+random.NextDouble():random.NextDouble();
                            if(c.Status=="Won"&&c.GrowthUsed==0)score-=100000;
                            if(score>best){best=score;chosen=action;next=c;}
                        }catch(Exception){r.discardedHazards++;}
                    }
                    Need(chosen!=null&&next!=null,"All sampled actions hit a fault");chosen.before=CampaignReplayRules.Fingerprint(b);b=next;b.Validate();chosen.after=CampaignReplayRules.Fingerprint(b);r.history.Add(chosen);
                    r.growth=Math.Max(r.growth,b.GrowthUsed);int gaps=b.Active.Count-b.Pieces.Count;if(gaps>0){r.turnsWithGaps++;r.maxGaps=Math.Max(r.maxGaps,gaps);if(r.firstGap==null)r.firstGap=b.Snapshot();}
                }
                r.actions=r.history.Count;r.status=b.Status;
                Need(r.actions<level.movesProposal+10||b.Status!="Playing","Action bound exceeded");
                var verify=new BoardModel(level,seed);foreach(var move in r.history){TurnResult result;string error;Need(CampaignReplayRules.Apply(verify,move,out result,out error),"History mismatch: "+error);}
            }catch(Exception e){r.error=e.ToString();r.status="ERROR";}
            return r;
        }
        public static void Run(){
            var report=new Report();string root=Path.GetFullPath("..");string input=Environment.GetEnvironmentVariable("HOTR_CAMPAIGN117_INPUT");if(string.IsNullOrEmpty(input))input=Path.Combine(root,".verification-cache/Review117/CampaignAllBottom01");
            string output=Environment.GetEnvironmentVariable("HOTR_CAMPAIGN117_OUTPUT");if(string.IsNullOrEmpty(output))output=Path.Combine(root,"Verification/Evidence/Review117");Directory.CreateDirectory(output);
            try{
                foreach(int n in new[]{27,44}){
                    var row=new Row{level=n};report.levels.Add(row);string path=Path.Combine(input,"C01_L"+n.ToString("000")+".json");row.levelSHA256=Sha(path);var level=JsonUtility.FromJson<LevelData>(File.ReadAllText(path));
                    Need(level!=null&&level.mossRegrowth!=null&&level.mossRegrowth.enabled,"Missing enabled moss growth");new BoardModel(level).ValidateCampaignOpening();
                    for(int i=0;i<8;i++){
                        var trial=Play(level,(uint)(level.tileSeed+i*7919));row.trials.Add(trial);
                        if(trial.growth>0)row.growthTrials++;if(trial.turnsWithGaps>0){row.gapTrials++;report.gapTrials++;}if(trial.error!=null){row.errors++;report.errors++;}
                    }
                }
                report.status=report.errors>0?"ERROR":report.gapTrials>0?"GAPS_OBSERVED":report.levels.Any(x=>x.growthTrials==0)?"INCOMPLETE_GROWTH_NOT_TRIGGERED":"PASS_BOUNDED_GROWTH_RUNS";
            }catch(Exception e){report.errors++;Debug.LogError(e);}
            File.WriteAllText(Path.Combine(output,"CampaignGrowth117.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.errors>0||report.gapTrials>0?1:0);
        }
    }
}
#endif

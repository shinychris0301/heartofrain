#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M48;

namespace HeartOfTheRain.Verification {
    // Replays recorded diagnostic-only solver branches; samples recolorings on
    // a detached model only. Does not modify campaign files or game profiles.
    public static class CampaignHazard117Verification {
        [Serializable] sealed class Hazard { public int turn; public string reason,boardStatus,boardFingerprint; public ReplayMove attempted; public ReplayMove[] priorActions; }
        [Serializable] sealed class Trial { public uint seed; public Hazard[] hazards; }
        [Serializable] sealed class Row { public int level; public Trial[] trials; }
        [Serializable] sealed class Input { public Row[] levels; }
        [Serializable] sealed class ColorCount { public int color,count; }
        [Serializable] sealed class Result { public int level,turn; public uint seed; public string status,error,beforeFingerprint,afterFingerprint; public ReplayMove attempted; public BoardSnapshot before,after; public int gemCount,samples,permutationsWithNoMatch,permutationsPlayable; public List<ColorCount> colors=new List<ColorCount>(); }
        [Serializable] sealed class Report { public string status="FAIL",scope="Reproduced speculative diagnostic branches and sampled detached-board permutations. Sampling cannot prove no valid permutation exists; no device or balance acceptance."; public int errors; public List<Result> hazards=new List<Result>(); }
        static void Need(bool ok,string why){if(!ok)throw new InvalidOperationException(why);}
        static TurnResult Apply(BoardModel b,ReplayMove m)=>m.kind=="tap"?b.Tap(m.ax,m.ay):b.Swap(m.ax,m.ay,m.bx,m.by);
        public static void Run(){
            string root=Path.GetFullPath("..");string input=Environment.GetEnvironmentVariable("HOTR_HAZARD117_INPUT");
            if(string.IsNullOrEmpty(input))input=Path.Combine(root,"Verification/Evidence/Review117/Native/Hazards01/CampaignSolver117.json");
            string levels=Environment.GetEnvironmentVariable("HOTR_CAMPAIGN117_INPUT");if(string.IsNullOrEmpty(levels))levels=Path.Combine(root,".verification-cache/Review117/CampaignDrafts02");
            string output=Environment.GetEnvironmentVariable("HOTR_CAMPAIGN117_OUTPUT");if(string.IsNullOrEmpty(output))output=Path.Combine(root,"Verification/Evidence/Review117");
            Directory.CreateDirectory(output);var report=new Report();
            try {
                var data=JsonUtility.FromJson<Input>(File.ReadAllText(input));Need(data!=null&&data.levels!=null,"Missing hazard report");
                var matches=typeof(BoardModel).GetMethod("Matches",BindingFlags.Instance|BindingFlags.NonPublic);Need(matches!=null,"Production matcher unavailable");
                foreach(var row in data.levels)foreach(var trial in row.trials??Array.Empty<Trial>())foreach(var hazard in trial.hazards??Array.Empty<Hazard>()){
                    var r=new Result{level=row.level,seed=trial.seed,turn=hazard.turn,attempted=hazard.attempted};report.hazards.Add(r);
                    try {
                        var path=Path.Combine(levels,"C01_L"+row.level.ToString("000")+".json");var level=JsonUtility.FromJson<LevelData>(File.ReadAllText(path));var b=new BoardModel(level,trial.seed);
                        foreach(var move in hazard.priorActions??Array.Empty<ReplayMove>()){TurnResult result;string error;Need(CampaignReplayRules.Apply(b,move,out result,out error),"Prior action mismatch: "+error);}
                        r.beforeFingerprint=CampaignReplayRules.Fingerprint(b);Need(r.beforeFingerprint==hazard.boardFingerprint,"Hazard fingerprint mismatch");r.before=b.Snapshot();
                        var turn=Apply(b,hazard.attempted);Need(turn!=null&&turn.accepted,"Hazard action rejected");r.after=b.Snapshot();r.afterFingerprint=CampaignReplayRules.Fingerprint(b);r.status=b.Status;
                        Need(r.status==hazard.boardStatus,"Hazard terminal status differs");
                        var gems=b.Pieces.Values.Where(p=>p.family=="gem").OrderBy(p=>p.id).ToArray();r.gemCount=gems.Length;
                        foreach(var g in gems.GroupBy(p=>p.color).OrderBy(g=>g.Key))r.colors.Add(new ColorCount{color=g.Key,count=g.Count()});
                        var colors=gems.Select(p=>p.color).ToArray();var rnd=new System.Random(117+row.level+(int)(trial.seed%100000));
                        for(int i=0;i<2000;i++){
                            for(int j=colors.Length-1;j>0;j--){int k=rnd.Next(j+1),v=colors[j];colors[j]=colors[k];colors[k]=v;}
                            for(int j=0;j<gems.Length;j++)gems[j].color=colors[j];r.samples++;
                            if(((ICollection)matches.Invoke(b,new object[]{null})).Count==0){r.permutationsWithNoMatch++;if(b.LegalSwaps().Count>0)r.permutationsPlayable++;}
                        }
                    }catch(Exception e){r.error=e.ToString();report.errors++;}
                }
                Need(report.hazards.Count>0,"No recorded hazards");if(report.errors==0)report.status="PASS_REPRODUCED";
            }catch(Exception e){report.errors++;Debug.LogError(e);}
            File.WriteAllText(Path.Combine(output,"CampaignHazards117.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.errors==0?0:1);
        }
    }
}
#endif

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
    // Bounded diagnostic search using only normal moves. No paid actions,
    // model manipulation, external data, or campaign-asset mutations.
    public static class CampaignSolver117Verification {
        [Serializable] sealed class Hazard { public int turn; public string reason,boardStatus,boardFingerprint; public ReplayMove attempted; public List<ReplayMove> priorActions; }
        [Serializable] sealed class Trial { public uint seed; public int actions,remaining,discardedHazards,turnsWithEmptyCells,maxEmptyCells; public string strategy,status,error; public List<Hazard> hazards=new List<Hazard>(); }
        [Serializable] sealed class Row { public int level; public string levelSHA256,status,error; public List<Trial> trials=new List<Trial>(); public CampaignReplay replay; }
        [Serializable] sealed class Report { public string status="INCOMPLETE",scope="Bounded diagnostic search on candidate model; failure to find a win does not prove unsolvability. Wins are replayed from the same seed without tools or extra moves. No human balance, device or backend acceptance."; public int wins,notSolved,errors,discardedHazards; public List<Row> levels=new List<Row>(); }
        static string Sha(string p){using(var h=SHA256.Create())using(var f=File.OpenRead(p))return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
        static void Need(bool ok,string why){if(!ok)throw new InvalidOperationException(why);}
        static TurnResult Apply(BoardModel b,ReplayMove m)=>m.kind=="tap"?b.Tap(m.ax,m.ay):b.Swap(m.ax,m.ay,m.bx,m.by);
        static void RecordHazard(Trial t,BoardModel before,List<ReplayMove> moves,ReplayMove attempted,string reason,string status){
            t.discardedHazards++;
            if(t.hazards.Count<100)t.hazards.Add(new Hazard{turn=before.Turn,reason=reason,boardStatus=status,
                boardFingerprint=CampaignReplayRules.Fingerprint(before),attempted=attempted,priorActions=new List<ReplayMove>(moves)});
        }
        static List<ReplayMove> Actions(BoardModel b){var a=new List<ReplayMove>();foreach(var p in b.Pieces.Values.Where(p=>p.family=="power").OrderBy(p=>p.id))a.Add(new ReplayMove{kind="tap",ax=p.x,ay=p.y});foreach(var pair in b.LegalSwaps())a.Add(new ReplayMove{kind="swap",ax=pair[0].x,ay=pair[0].y,bx=pair[1].x,by=pair[1].y});return a;}
        static double Cost(BoardModel b){
            double value=b.Goals.Values.Sum()*100;
            foreach(var p in b.Pieces.Values.Where(p=>p.IsAnchor&&p.family!="gem"&&p.family!="power")){
                if(p.family!="pail")value+=Math.Max(0,p.hp)*5;
                else {var exits=b.Level.deliveryExits??Array.Empty<Cell>();if(exits.Length>0)value+=exits.Min(e=>Math.Abs(e.x-p.x)+Math.Abs(e.y-p.y))*3;}
            }
            foreach(var p in b.Pieces.Values.Where(p=>p.family=="power"))value-=p.power==7?55:p.power==21?32:20;
            return value;
        }
        static CampaignReplay Search(LevelData level,uint seed,string strategy,int maxCandidates,Trial trial){
            var b=new BoardModel(level,seed);var random=new System.Random((int)(seed%int.MaxValue));var moves=new List<ReplayMove>();
            while(b.Status=="Playing"&&b.Moves>0&&moves.Count<level.movesProposal+10){
                var choices=Actions(b);if(choices.Count==0)throw new InvalidOperationException("Playing board has no legal action");ReplayMove chosen=null;BoardModel chosenModel=null;
                if(strategy=="random"){
                    // Exactly reproduces the CampaignDraft117 random action policy.
                    var powers=choices.Where(x=>x.kind=="tap").ToArray();var swaps=choices.Where(x=>x.kind=="swap").ToArray();
                    if(powers.Length>0&&random.Next(3)!=0)chosen=powers[random.Next(powers.Length)];
                    else if(swaps.Length>0)chosen=swaps[random.Next(swaps.Length)];
                    else chosen=powers[random.Next(powers.Length)];
                } else {
                    // Evaluate a bounded random subset, always including one
                    // power tap when present, and minimize remaining targets.
                    var sampled=choices.OrderBy(x=>random.Next()).Take(maxCandidates).ToList();
                    var tap=choices.FirstOrDefault(x=>x.kind=="tap");if(tap!=null&&!sampled.Contains(tap))sampled[0]=tap;
                    var snapshot=b.Checkpoint();double best=double.NegativeInfinity;
                    foreach(var action in sampled){
                        try {
                            var c=BoardModel.FromCheckpoint(level,snapshot);var t=Apply(c,action);
                            if(t==null||!t.accepted||c.Status=="Engine fault"||c.Status=="Resolution limit"||c.Status=="No legal moves"){
                                RecordHazard(trial,b,moves,action,t==null?"null result":!t.accepted?"rejected: "+t.reason:"model terminal status",c.Status);continue;
                            }
                            double score=Cost(b)-Cost(c)+(c.Status=="Won"?100000:0)+random.NextDouble()*14;
                            if(score>best){best=score;chosen=action;chosenModel=c;}
                        }catch(Exception e){RecordHazard(trial,b,moves,action,e.ToString(),"exception");}
                    }
                    if(chosen==null)throw new InvalidOperationException("All sampled actions failed or reached a model fault");
                }
                chosen.before=CampaignReplayRules.Fingerprint(b);
                if(chosenModel==null){var t=Apply(b,chosen);Need(t!=null&&t.accepted,"Chosen action rejected");}
                else b=chosenModel;
                b.Validate();int empty=b.Active.Count-b.Pieces.Count;if(empty>0){trial.turnsWithEmptyCells++;trial.maxEmptyCells=Math.Max(trial.maxEmptyCells,empty);}
                chosen.after=CampaignReplayRules.Fingerprint(b);moves.Add(chosen);
                Need(b.Status!="Engine fault"&&b.Status!="Resolution limit"&&b.Status!="No legal moves","Committed move encountered model hazard: "+b.Status);
            }
            trial.actions=moves.Count;trial.remaining=b.Goals.Values.Sum();trial.status=b.Status;
            Need(moves.Count<level.movesProposal+10||b.Status!="Playing","Action limit exceeded");
            if(b.Status!="Won")return null;
            var replay=new CampaignReplay{level=level.globalLevel,seed=(int)seed,budget=level.movesProposal,expectedStatus="Won",actions=moves.ToArray()};
            var verify=new BoardModel(level,seed);
            foreach(var action in replay.actions){TurnResult result;string error;Need(CampaignReplayRules.Apply(verify,action,out result,out error),"Replay mismatch: "+error);}
            Need(verify.Status=="Won"&&verify.Goals.Values.All(g=>g==0),"Winning replay did not clear all objectives");
            return replay;
        }
        static int Number(string name,int fallback,int min,int max){int x;var s=Environment.GetEnvironmentVariable(name);return int.TryParse(s,out x)&&x>=min&&x<=max?x:fallback;}
        public static void Run(){
            var report=new Report();string root=Path.GetFullPath("..");
            string input=Environment.GetEnvironmentVariable("HOTR_CAMPAIGN117_INPUT");if(string.IsNullOrEmpty(input))input=Path.Combine(root,".verification-cache/Review117/CampaignDrafts02");
            string output=Environment.GetEnvironmentVariable("HOTR_CAMPAIGN117_OUTPUT");if(string.IsNullOrEmpty(output))output=Path.Combine(root,"Verification/Evidence/Review117");
            input=Path.GetFullPath(input);output=Path.GetFullPath(output);Directory.CreateDirectory(output);
            int attempts=Number("HOTR_CAMPAIGN117_ATTEMPTS",8,3,30),maxCandidates=Number("HOTR_CAMPAIGN117_CANDIDATES",8,1,30);
            bool exhaustive=Environment.GetEnvironmentVariable("HOTR_CAMPAIGN117_EXHAUSTIVE")=="1";
            var wanted=Environment.GetEnvironmentVariable("HOTR_CAMPAIGN117_LEVELS");var levels=string.IsNullOrEmpty(wanted)?Enumerable.Range(11,40).ToArray():wanted.Split(',').Select(int.Parse).Where(x=>x>=1&&x<=50).Distinct().OrderBy(x=>x).ToArray();
            try {
                foreach(int n in levels){
                    var row=new Row{level=n,status="NOT_SOLVED_WITHIN_BUDGET"};report.levels.Add(row);
                    try {
                        string path=Path.Combine(input,"C01_L"+n.ToString("000")+".json");row.levelSHA256=Sha(path);var level=JsonUtility.FromJson<LevelData>(File.ReadAllText(path));
                        Need(level!=null&&level.globalLevel==n,"Wrong level file");new BoardModel(level).ValidateCampaignOpening();
                        for(int a=0;a<attempts&&(row.replay==null||exhaustive);a++){
                            uint seed=(uint)(level.tileSeed+a*7919);var trial=new Trial{seed=seed,strategy=a<3?"random":"objective"};row.trials.Add(trial);
                            try{var found=Search(level,seed,trial.strategy,maxCandidates,trial);if(row.replay==null)row.replay=found;}
                            catch(Exception e){trial.status="ERROR";trial.error=e.ToString();}
                            report.discardedHazards+=trial.discardedHazards;
                            if(trial.status=="ERROR"){row.error=trial.error;break;}
                        }
                        if(row.error!=null){row.status="ERROR";report.errors++;}
                        else if(row.replay!=null){row.status="WIN_REPLAY_VERIFIED";report.wins++;}
                        else report.notSolved++;
                    }catch(Exception e){row.status="ERROR";row.error=e.ToString();report.errors++;}
                    Debug.Log("Campaign solver "+n+": "+row.status+" trials="+row.trials.Count);
                }
                report.status=report.errors>0?"ERROR":report.notSolved>0?"BOUNDED_SEARCH_INCOMPLETE":"ALL_REPLAYS_VERIFIED";
            }catch(Exception e){report.errors++;report.status="ERROR";Debug.LogError(e);}
            File.WriteAllText(Path.Combine(output,"CampaignSolver117.json"),JsonUtility.ToJson(report,true));
            EditorApplication.Exit(report.errors==0?0:1);
        }
    }
}
#endif

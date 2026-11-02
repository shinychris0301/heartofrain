#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;

namespace HeartOfTheRain.Verification {
    // Candidate files remain outside Assets; never changes levels or a profile.
    public static class CampaignVaried117Verification {
        [Serializable] sealed class Route { public Cell start,exit; public Cell[] cells; }
        [Serializable] sealed class RouteData { public Route[] deliveryRoutes; }
        [Serializable] sealed class Simulation { public uint seed; public int actions,remaining; public string status,error; }
        [Serializable] sealed class Result { public int level,active,goals,legalSwaps; public string sourceSHA256,status,error; public List<Simulation> runs=new List<Simulation>(); }
        [Serializable] sealed class Report { public string scope="Candidate Unity model only; bounded agent runs do not establish human balance, replay, device or production acceptance.",status="FAIL"; public int openings,errors,wins,losses,noLegal,limits; public List<Result> levels=new List<Result>(); }
        static void Need(bool ok,string error){if(!ok)throw new InvalidOperationException(error);}
        static string Sha(string path){using(var hash=SHA256.Create())using(var f=File.OpenRead(path))return BitConverter.ToString(hash.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
        static int K(int x,int y,int columns)=>y*columns+x;
        static void CheckRoutes(LevelData level,RouteData data,BoardModel board) {
            var pails=level.obstacles.Where(o=>o.family=="pail").ToArray();var routes=data.deliveryRoutes??Array.Empty<Route>();
            Need(routes.Length==pails.Length,"Pail/route count mismatch");
            var used=new HashSet<int>();
            foreach(var r in routes){
                Need(r!=null&&r.start!=null&&r.exit!=null&&r.cells!=null&&r.cells.Length>0,"Invalid delivery route");
                Need(pails.Any(p=>p.x==r.start.x&&p.y==r.start.y),"Route has no pail");
                Need(used.Add(K(r.start.x,r.start.y,level.columns)),"Duplicate pail route");
                Need(level.deliveryExits.Any(c=>c.x==r.exit.x&&c.y==r.exit.y),"Route exit missing");
                Need(r.start.x==r.exit.x&&r.start.y>=r.exit.y&&r.cells.Length==r.start.y-r.exit.y+1,"Route is not a downwards vertical path");
                for(int i=0;i<r.cells.Length;i++)Need(r.cells[i].x==r.exit.x&&r.cells[i].y==r.exit.y+i&&board.Inside(r.cells[i].x,r.cells[i].y),"Route leaves active mask");
            }
            Need(level.deliveryExits.Length==routes.Select(r=>K(r.exit.x,r.exit.y,level.columns)).Distinct().Count(),"Exit count differs from routes");
        }
        static Simulation Play(LevelData level,uint seed) {
            var s=new Simulation{seed=seed};
            try {
                var b=new BoardModel(level,seed);var random=new System.Random((int)(seed%int.MaxValue));
                while(b.Status=="Playing"&&b.Moves>0&&s.actions<level.movesProposal+10){
                    var powers=b.Pieces.Values.Where(p=>p.family=="power").OrderBy(p=>p.id).ToArray();
                    var swaps=b.LegalSwaps();TurnResult turn;
                    if(powers.Length>0&&random.Next(3)!=0){var p=powers[random.Next(powers.Length)];turn=b.Tap(p.x,p.y);}
                    else if(swaps.Count>0){var m=swaps[random.Next(swaps.Count)];turn=b.Swap(m[0].x,m[0].y,m[1].x,m[1].y);}
                    else if(powers.Length>0){var p=powers[random.Next(powers.Length)];turn=b.Tap(p.x,p.y);}
                    else throw new InvalidOperationException("Playing board has no legal action");
                    Need(turn!=null&&turn.accepted,"Model rejected chosen legal action");b.Validate();s.actions++;
                }
                s.status=b.Status;s.remaining=b.Goals.Values.Sum();
                Need(s.actions<level.movesProposal+10||b.Status!="Playing","Action guard exceeded");
                Need(b.Status!="Engine fault"&&b.Status!="Resolution limit"&&b.Status!="No legal moves","Board ended with model fault or unsolvable shuffle");
            } catch(Exception e){s.error=e.ToString();s.status="ERROR";}
            return s;
        }
        public static void Run(){
            var report=new Report();string root=Path.GetFullPath("..");string input=Environment.GetEnvironmentVariable("HOTR_CAMPAIGN117_INPUT");
            if(string.IsNullOrEmpty(input))input=Path.Combine(root,".verification-cache/Review117/CampaignVaried01");input=Path.GetFullPath(input);
            string outputDir=Environment.GetEnvironmentVariable("HOTR_CAMPAIGN117_OUTPUT");
            if(string.IsNullOrEmpty(outputDir))outputDir=Path.Combine(root,"Verification/Evidence/Review117");
            string output=Path.Combine(Path.GetFullPath(outputDir),"CampaignVariedUnity117.json");
            try {
                Directory.CreateDirectory(Path.GetDirectoryName(output));
                for(int n=11;n<=50;n++){
                    var row=new Result{level=n,status="FAIL"};report.levels.Add(row);
                    try {
                        var path=Path.Combine(input,"C01_L"+n.ToString("000")+".json");row.sourceSHA256=Sha(path);string json=File.ReadAllText(path);
                        var level=JsonUtility.FromJson<LevelData>(json);var routes=JsonUtility.FromJson<RouteData>(json);
                        var original=JsonUtility.FromJson<LevelData>(File.ReadAllText(Path.Combine(root,"Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117/C01_L"+n.ToString("000")+".json")));
                        Need(level!=null&&original!=null&&level.globalLevel==n&&level.columns>=9&&level.columns<=11&&level.rows==9,"Level identity or dimensions differ");
                        Need(level.goals.Select(g=>g.family).OrderBy(x=>x).SequenceEqual(original.goals.Select(g=>g.family).OrderBy(x=>x)),"Original goal families changed");
                        var board=new BoardModel(level);board.ValidateCampaignOpening();
                        var counts=board.Pieces.Values.Where(p=>p.IsAnchor&&p.family!="gem"&&p.family!="power")
                            .GroupBy(BoardModel.GoalFamily).ToDictionary(g=>g.Key,g=>g.Sum(BoardModel.GoalUnits));
                        Need(counts.Count==board.Goals.Count&&board.Goals.All(g=>counts.TryGetValue(g.Key,out int total)&&total==g.Value),"Goal count differs from initial targets");
                        foreach(var key in board.Active){int x=key%level.columns,y=key/level.columns;if(!board.Active.Contains(K(x,y+1,level.columns)))Need(board.Spawns.Contains(key),"Active segment lacks top spawn");}
                        CheckRoutes(level,routes,board);row.active=board.Active.Count;row.goals=board.Goals.Values.Sum();row.legalSwaps=board.LegalSwaps().Count;report.openings++;
                        for(int i=0;i<3;i++){
                            var sim=Play(level,(uint)(level.tileSeed+i*7919));row.runs.Add(sim);
                            if(sim.status=="Won")report.wins++;else if(sim.status=="Out of moves")report.losses++;else if(sim.status=="No legal moves")report.noLegal++;else if(sim.status=="Resolution limit")report.limits++;
                            Need(sim.error==null,"Simulation failed: "+sim.error);
                        }
                        row.status="PASS";
                    } catch(Exception e){row.error=e.ToString();report.errors++;}
                }
                if(report.errors==0&&report.openings==40)report.status="PASS_BOUNDED_MODEL_CHECKS";
            } catch(Exception e){report.errors++;Debug.LogError(e);}
            File.WriteAllText(output,JsonUtility.ToJson(report,true));
            Debug.Log("Campaign draft checks: "+report.status+" openings="+report.openings+" errors="+report.errors+" wins="+report.wins+" losses="+report.losses);
            EditorApplication.Exit(report.errors==0?0:1);
        }
    }
}
#endif

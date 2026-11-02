#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification
{
    public static class GameModelPerformanceVerification
    {
        [Serializable] public sealed class Row
        {
            public string name,turnSHA256,finalSHA256;public int steps,matchSteps,powerSteps,created;
            public double meanMilliseconds,minMilliseconds,maxMilliseconds;public double[] milliseconds;
        }
        [Serializable] public sealed class Report
        {
            public string utc,status,variant,boardModelSHA256;
            public string scope="Native Unity Editor CPU-only live BoardModel commands across all 50 authored boards: one warm-up then two timed independent solves per case. Setup, serialization and hashing are outside the timer. Raw turn and final snapshot hashes verify exact deterministic semantics; no GPU, display, Android or allocation claim.";
            public int checks,boards=50,scenarios=4,warmupSolves=200,timedSolves=400;
            public List<string> failures=new List<string>();public List<Row> commands=new List<Row>();
        }
        sealed class Scenario
        {
            public BoardModel board;public Cell[] swap;public Piece source;
            public TurnResult Solve()=>swap==null?board.Tap(source.x,source.y):board.Swap(swap[0].x,swap[0].y,swap[1].x,swap[1].y);
        }
        public static void Baseline()=>Measure("Before");
        public static void Run()=>Measure("After");
        static string Hash(string text){using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(text))).Replace("-","").ToLowerInvariant();}
        static Scenario Prepare(LevelData level,string kind)
        {
            var board=new BoardModel(level);var scenario=new Scenario{board=board};
            if(kind=="natural_first"){scenario.swap=board.LegalSwaps().First();return scenario;}
            if(kind=="three_rocket_chain")
            {
                var row=board.Pieces.Values.Where(p=>p.family=="gem").GroupBy(p=>p.y).First(g=>g.Count()>=3).OrderBy(p=>p.x).Take(3).ToArray();scenario.source=row[0];foreach(var p in row)board.InjectReviewPower(p.x,p.y,4);return scenario;
            }
            var source=board.Pieces.Values.First(p=>p.family=="gem"&&board.At(p.x+1,p.y)?.family=="gem");var partner=board.At(source.x+1,source.y);
            board.InjectReviewPower(source.x,source.y,kind=="orb_rocket"?7:16);board.InjectReviewPower(partner.x,partner.y,kind=="orb_rocket"?4:21);
            scenario.swap=new[]{new Cell(source.x,source.y),new Cell(partner.x,partner.y)};return scenario;
        }
        static void Measure(string variant)
        {
            var report=new Report{utc=DateTime.UtcNow.ToString("o"),variant=variant};
            void Check(bool condition,string label){report.checks++;if(!condition)report.failures.Add(label);}
            string folder=Path.GetFullPath("../Verification/Evidence/GameplayAudit/"+variant);Directory.CreateDirectory(folder);
            try
            {
                string model=File.ReadAllText("Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs");report.boardModelSHA256=Hash(model);
                if(variant=="Before")
                {
                    Check(model.Contains("newborn powers remain eligible"),"Baseline contains the approved mixed-swap creation repair");
                    string snapshot=Path.GetFullPath("../.verification-cache/GameplayAudit/ModelBaseline/BoardModel.cs");Directory.CreateDirectory(Path.GetDirectoryName(snapshot));
                    if(File.Exists(snapshot))Check(File.ReadAllText(snapshot)==model,"Existing fixed-creation baseline is unchanged");else File.Copy("Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs",snapshot);
                }
                var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");Check(ui&&ui.boards&&ui.boards.levels.Length==50,"All authored boards imported");
                for(int n=0;n<50;n++)foreach(string kind in new[]{"natural_first","three_rocket_chain","orb_rocket","golden_bomb"})
                {
                    var data=JsonUtility.FromJson<LevelData>(ui.boards.levels[n].text);string label="L"+(n+1).ToString("000")+"/"+kind;
                    var warm=Prepare(data,kind);Check(warm.Solve().accepted,label+" warm-up accepted");
                    var row=new Row{name=label,milliseconds=new double[2]};string turnHash=null,finalHash=null;
                    for(int repeat=0;repeat<2;repeat++)
                    {
                        var scenario=Prepare(data,kind);var watch=Stopwatch.StartNew();var result=scenario.Solve();watch.Stop();row.milliseconds[repeat]=watch.Elapsed.TotalMilliseconds;
                        Check(result.accepted&&scenario.board.Status!="Resolution limit",label+" timed solve accepted "+repeat);scenario.board.Validate();
                        string raw=Hash(JsonUtility.ToJson(result)),final=Hash(JsonUtility.ToJson(scenario.board.Snapshot()));
                        if(turnHash!=null)Check(raw==turnHash&&final==finalHash,label+" repeats preserve exact turn and final snapshot");else {turnHash=raw;finalHash=final;}
                        row.steps=result.steps.Count;row.matchSteps=result.steps.Count(s=>s.kind=="match");row.powerSteps=result.steps.Count(s=>s.kind=="power");row.created=result.steps.Sum(s=>s.created.Count);
                    }
                    row.turnSHA256=turnHash;row.finalSHA256=finalHash;row.meanMilliseconds=row.milliseconds.Average();row.minMilliseconds=row.milliseconds.Min();row.maxMilliseconds=row.milliseconds.Max();report.commands.Add(row);
                }
                if(variant=="After")
                {
                    var baseline=JsonUtility.FromJson<Report>(File.ReadAllText(Path.GetFullPath("../Verification/Evidence/GameplayAudit/Before/Model_Commands.json")));Check(baseline.status=="PASS_NATIVE_MODEL_COMMANDS"&&baseline.commands.Count==200,"Fixed-creation model baseline passed");
                    foreach(var row in report.commands)
                    {
                        var old=baseline.commands.Single(x=>x.name==row.name);Check(old.turnSHA256==row.turnSHA256&&old.finalSHA256==row.finalSHA256&&old.steps==row.steps&&old.created==row.created,"Exact before/after model semantics "+row.name);
                    }
                }
            }
            catch(Exception error){report.failures.Add(error.ToString());}
            report.status=report.failures.Count==0?"PASS_NATIVE_MODEL_COMMANDS":"FAIL_NATIVE_MODEL_COMMANDS";File.WriteAllText(Path.Combine(folder,"Model_Commands.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.failures.Count==0?0:1);
        }
    }
}
#endif

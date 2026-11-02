#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using Old = HeartOfTheRain.Verification.Checkpoint75Control;

namespace HeartOfTheRain.Verification {
    public static class SmoothnessCommandVerification {
        [Serializable] public sealed class SourceBinding {
            public string path,sha256,compiledBodySHA256;public bool compiledExactAdaptation;
        }
        [Serializable] public sealed class ModelRow {
            public string name,turnHash,finalHash;public int comparisons;
        }
        [Serializable] public sealed class Report {
            public string status,utc,baselineReportSHA256;
            public string scope="Native Editor exact compiled75/current construction on350 accepted natural/power turns, with geometry present/absent and scheduling enabled/sequential. Full recursive nonserialized tracks, branch-correct continuation segments, landing contacts and TileFall poses are compared. Raw input/model hashes match frozen75. Eight fixtures additionally use12 alternating warmed pure Build pairs. No live-render, Android frame-rate, allocation-savings or universal CPU-speedup claim.";
            public int checks,modelCases,queueComparisons,sourceFiles;public long stopwatchFrequency;
            public bool exactQueueParity=true,rawInputUnchanged=true,rawTurnParity=true,finalSnapshotParity=true,compiledSourceMatchesArchive=true;
            public List<SourceBinding> sourceBindings=new List<SourceBinding>();public List<ModelRow> rows=new List<ModelRow>();
            public List<SmoothnessCommandProof.Row> timings=new List<SmoothnessCommandProof.Row>();public List<string> errors=new List<string>();
        }
        [Serializable] sealed class BaselineRow {public string name,turnHash,finalHash;}
        [Serializable] sealed class BaselineReport {public string status;public List<BaselineRow> rows;}
        static Report report;
        static void Check(bool ok,string label){report.checks++;if(!ok)throw new InvalidOperationException(label);}
        static string FileHash(string path){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
        static string Normalize(string text)=>text.Replace("\r\n","\n").Trim();
        static void SourceProof(){
            string root=Path.GetFullPath("..");
            string compiled=File.ReadAllText("Assets/HeartOfTheRain/Verification/Smoothness75Control.cs");
            var frozen=new Dictionary<string,string>{
                {"BoardPlayback.cs","b52f193b9b0e7d1edeeecdf5726091338d25f57a8df7fb7e465010c80ddc6ac7"},
                {"LocalCascadeContinuation.cs","01954b52182ef0cc36cb5785e816a642b28c2cbc35b364676ffe2875c4ba4b5e"},
                {"LocalCascadePlayback.cs","fd4e78da01f36e4d8d107bb54f3ab5d2b802a17749d9fc351e4eab498e659918"}};
            foreach(string name in new[]{"BoardPlayback.cs","LocalCascadeContinuation.cs","LocalCascadePlayback.cs"}){
                string relative="Unity/Assets/HeartOfTheRain/M46/Runtime/"+name;
                string original=Path.Combine(root,".verification-cache/Gameplay76/BaselineSources",relative);
                string source=File.ReadAllText(original);string expected=source.Substring(source.IndexOf("namespace HeartOfTheRain.M46",StringComparison.Ordinal)).Trim().Replace("namespace HeartOfTheRain.M46","namespace HeartOfTheRain.Verification.Checkpoint75Control");
                if(name=="BoardPlayback.cs")expected=expected.Replace("    public sealed class PlaybackTrack { public BoardStep step; public float start,leadIn; }","");
                string begin="// BEGIN EXACT75 "+name,end="// END EXACT75 "+name;int at=compiled.IndexOf(begin,StringComparison.Ordinal)+begin.Length;int stop=compiled.IndexOf(end,at,StringComparison.Ordinal);
                string actual=at>=begin.Length&&stop>at?compiled.Substring(at,stop-at):"";
                bool equal=Normalize(actual)==Normalize(expected);
                var binding=new SourceBinding{path=relative,sha256=FileHash(original),compiledBodySHA256=SmoothnessCommandProof.Hash(Normalize(actual)),compiledExactAdaptation=equal};
                Check(binding.sha256==frozen[name],"Archived source matches sealed75 bytes: "+name);
                report.sourceBindings.Add(binding);report.sourceFiles++;report.compiledSourceMatchesArchive&=equal;Check(equal,"Compiled source75 control exact except namespace/shared PlaybackTrack: "+name);
            }
        }
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),stopwatchFrequency=System.Diagnostics.Stopwatch.Frequency};
            bool prior=LocalCascadeContinuation.VerificationUseCheckpoint74,oldPrior=Old.LocalCascadeContinuation.VerificationUseCheckpoint74;
            try{
                LocalCascadeContinuation.VerificationUseCheckpoint74=false;Old.LocalCascadeContinuation.VerificationUseCheckpoint74=false;SourceProof();
                string baseline=Path.GetFullPath("../Verification/Evidence/Gameplay75/Native/ModelCommands.json");report.baselineReportSHA256=FileHash(baseline);
                var reference=JsonUtility.FromJson<BaselineReport>(File.ReadAllText(baseline));Check(reference.status=="PASS_NATIVE_MODEL_COMMANDS75"&&reference.rows.Count==350,"Sealed75 model corpus available");
                var byName=reference.rows.ToDictionary(r=>r.name);
                var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");Check(ui&&ui.boards.levels.Length==50,"Approved50-level bindings");
                for(int level=0;level<50;level++)foreach(int kind in new[]{-1,4,5,7,11,16,21}){
                    var fixture=SmoothnessCommandProof.Solve(JsonUtility.FromJson<LevelData>(ui.boards.levels[level].text),kind);var row=new ModelRow{name=fixture.name,turnHash=fixture.turnHash,finalHash=fixture.finalHash};
                    var expected=byName[fixture.name];bool raw=fixture.turnHash==expected.turnHash,final=fixture.finalHash==expected.finalHash;report.rawTurnParity&=raw;report.finalSnapshotParity&=final;Check(raw&&final,"Frozen75 model hashes "+fixture.name);
                    foreach(bool geometry in new[]{true,false})foreach(bool scheduled in new[]{true,false}){
                        string before=SmoothnessCommandProof.RawHash(fixture.turn);
                        var old=SmoothnessCommandProof.Build(fixture,true,geometry,scheduled);var current=SmoothnessCommandProof.Build(fixture,false,geometry,scheduled);
                        bool same=SmoothnessCommandProof.Signature(old,true)==SmoothnessCommandProof.Signature(current,false);
                        bool unchanged=before==SmoothnessCommandProof.RawHash(fixture.turn)&&before==fixture.turnHash;
                        report.exactQueueParity&=same;report.rawInputUnchanged&=unchanged;report.queueComparisons++;row.comparisons++;
                        Check(same,"Complete geometry/scheduling queue parity "+fixture.name+"/"+geometry+"/"+scheduled);Check(unchanged,"Raw turn unchanged "+fixture.name);
                    }
                    report.rows.Add(row);report.modelCases++;
                }
                foreach(var fixture in SmoothnessCommandProof.Benchmarks(ui)){
                    SmoothnessCommandProof.Warm(fixture);var row=SmoothnessCommandProof.RowFor(fixture);
                    for(int n=0;n<12;n++)row.pairs.Add(SmoothnessCommandProof.Measure(fixture,n,Check));SmoothnessCommandProof.Summarize(row);report.timings.Add(row);
                }
                Check(report.modelCases==350&&report.queueComparisons==1400&&report.timings.Count==8,"Full corpus/benchmark coverage");
            }catch(Exception error){report.errors.Add(error.ToString());}
            finally{LocalCascadeContinuation.VerificationUseCheckpoint74=prior;Old.LocalCascadeContinuation.VerificationUseCheckpoint74=oldPrior;}
            report.status=report.errors.Count==0?"PASS_NATIVE_SMOOTHNESS_COMMAND76":"FAIL_NATIVE_SMOOTHNESS_COMMAND76";
            string folder=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY76_OUTPUT");if(string.IsNullOrEmpty(folder))folder=Path.GetFullPath("../Verification/Evidence/Gameplay76");folder=Path.Combine(folder,"Native");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"SmoothnessCommand.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif

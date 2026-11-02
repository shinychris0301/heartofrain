#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.M48;
using Motion = HeartOfTheRain.M46.Motion;
namespace HeartOfTheRain.Verification {
    // Retains the pre-change dependency walker as an independent parity control.
    // Timing covers the complete resource walk, without asset loads or rendering.
    public static class ResourceScanVerification {
        [Serializable] public sealed class Row {
            public string name;public int cells,motions,iterations,blocks;public double legacyMicroseconds,currentMicroseconds,speedup;public double[] legacyBlocks,currentBlocks;
        }
        [Serializable] public sealed class Report {
            public string status,utc,unity;
            public string scope="Native Unity Editor dependency-scan parity and warmed CPU microbenchmark. All resource sets and enumeration order are compared against the preceding walker. Timings exclude BoardModel solve, playback construction, disk/texture loads, GPU, Android and touch latency.";
            public int checks,authoredTurns,edgeCases;public List<string> failures=new List<string>();public List<Row> benchmarks=new List<Row>();
        }
        static Report report;static int checksum;
        static void Check(bool ok,string label){report.checks++;if(!ok)throw new InvalidOperationException(label);}
        static EffectResources Legacy(IEnumerable<BoardStep> steps){
            var n=new EffectResources();
            foreach(var s in steps){
                foreach(var p in s.before.pieces.Concat(s.after.pieces)){
                    if(p.family=="power")n.powers.Add(BoardPresentation.PowerAtlas(p.power));else n.bodies.Add(BoardPresentation.BodyKey(p));
                    if(p.family=="crystal")n.obstacleFamilies.Add("crystal");
                }
                if(s.removed.Any(r=>r.piece.family=="gem"))n.powers.UnionWith(new[]{2,3,4,12});
                if(s.created.Count>0)n.powers.Add(12);
                foreach(var d in s.damage){n.obstacleFamilies.Add(d.family);if(d.family=="pod"||d.family=="cabinet")for(int hp=Math.Max(1,d.afterHP);hp<=d.beforeHP;hp++)n.bodies.Add(d.family+"_"+hp);}
                if(s.collections.Count>0){n.bodies.Add("collectionGlint");foreach(var c in s.collections)n.bodies.Add(c.family=="pod"?"waterSpirit":"rainlight");}
                if(s.kind=="grow")n.obstacleFamilies.Add("moss");
                if(s.kind=="deliver"||s.motion.Any(m=>s.before.pieces.Any(p=>p.id==m.id&&p.family=="pail")))n.obstacleFamilies.Add("pail");
                if(s.powerPlan!=null){foreach(var e in s.powerPlan.effects??new ReviewFx[0])n.powers.Add(e.atlas);foreach(var p in s.powerPlan.powers??new ReviewPower[0])n.powers.Add(p.atlas);if((s.powerPlan.beams?.Length??0)>0)n.powers.Add(20);}
                if(s.booster!=null){n.powers.UnionWith(new[]{0,1,12,20});n.bodies.Add("booster"+s.booster.kind);if(s.booster.kind==BoosterKind.Atlas)n.powers.Add(21);}
            }
            return n;
        }
        static IEnumerable<BoardStep> Flatten(IEnumerable<BoardStep> source)=>source.SelectMany(s=>s.playbackTracks==null?new[]{s}:new[]{s}.Concat(s.playbackTracks.Select(t=>t.step)));
        static void Parity(IEnumerable<BoardStep> steps,string name){
            var list=steps.ToArray();var before=Legacy(list);var after=EffectResources.ForSteps(list);
            Check(before.powers.SetEquals(after.powers)&&before.bodies.SetEquals(after.bodies)&&before.obstacleFamilies.SetEquals(after.obstacleFamilies),name+" resource sets");
            Check(before.powers.SequenceEqual(after.powers)&&before.bodies.SequenceEqual(after.bodies)&&before.obstacleFamilies.SequenceEqual(after.obstacleFamilies),name+" resource insertion order");
        }
        static BoardStep Fixture(int cells,int motions,int jar,int jarMotion=-1){
            var pieces=Enumerable.Range(1,cells).Select(i=>new Piece{id=i,x=(i-1)%11,y=(i-1)/11,family=i==jar?"pail":"gem",color=(i-1)%6}).ToArray();
            var snap=new BoardSnapshot{pieces=pieces,goals=new Goal[0],status="Playing"};
            var step=new BoardStep{kind="gravity",before=snap,after=snap};
            for(int i=0;i<motions;i++)step.motion.Add(new Motion{id=i+1,fromX=i%11,toX=i%11,fromY=1,toY=0});
            if(jarMotion>=0)step.motion.Add(new Motion{id=jarMotion,fromY=1,toY=0});
            return step;
        }
        static void Edges(){
            foreach(int cells in new[]{1,9,81,99,121})foreach(int motions in new[]{0,1,cells/2,cells})foreach(int jar in new[]{0,1,cells}){
                var s=Fixture(cells,motions,jar);Parity(new[]{s},"fixture "+cells+"/"+motions+"/"+jar);report.edgeCases++;
                bool expected=s.before.pieces.Any(p=>p.family=="pail"&&s.motion.Any(m=>m.id==p.id));
                Check(EffectResources.ForSteps(new[]{s}).obstacleFamilies.Contains("pail")==expected,"Only moving jar requires its clip family");
            }
            var missing=Fixture(121,121,121);missing.motion.Clear();missing.motion.Add(new Motion{id=1000});Parity(new[]{missing},"Unmatched motion identity");Check(!EffectResources.ForSteps(new[]{missing}).obstacleFamilies.Contains("pail"),"Stationary jar is not animated by unrelated motion");
            var deliver=Fixture(121,0,0);deliver.kind="deliver";Parity(new[]{deliver},"Delivery without motion");Check(EffectResources.ForSteps(new[]{deliver}).obstacleFamilies.Contains("pail"),"Delivery retains its clip dependency without a motion");report.edgeCases+=2;
        }
        static void Authored(){
            var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
            Check(ui&&ui.boards&&ui.boards.levels.Length==50,"All fifty authored boards available");
            foreach(var text in ui.boards.levels){var level=JsonUtility.FromJson<LevelData>(text.text);
                foreach(int kind in new[]{-1,4,5,7,11,16,21}){
                    var b=new BoardModel(level);TurnResult turn;
                    if(kind<0){var move=b.LegalSwaps().First();turn=b.Swap(move[0].x,move[0].y,move[1].x,move[1].y);}
                    else {var p=b.Pieces.Values.First(v=>v.family=="gem");b.InjectReviewPower(p.x,p.y,kind);turn=b.Tap(p.x,p.y);}
                    Check(turn.accepted,"Authored turn accepted L"+level.globalLevel+"/"+kind);b.Validate();
                    Parity(turn.steps,"Raw L"+level.globalLevel+"/"+kind);
                    Parity(Flatten(BoardPlayback.Build(turn.steps,b.Level)),"Playback L"+level.globalLevel+"/"+kind);report.authoredTurns++;
                }
            }
        }
        static double Time(Func<EffectResources> scan,int iterations){var watch=Stopwatch.StartNew();for(int i=0;i<iterations;i++){var n=scan();checksum^=n.powers.Count+n.bodies.Count+n.obstacleFamilies.Count;}watch.Stop();return watch.Elapsed.TotalMilliseconds*1000/iterations;}
        static void Benchmark(int cells,int jar,bool moving){
            var s=Fixture(cells,moving?cells:cells-1,jar);var input=new[]{s};Parity(input,"Benchmark "+cells+"/"+jar+"/"+moving);
            Func<EffectResources> before=()=>Legacy(input),after=()=>EffectResources.ForSteps(input);
            for(int i=0;i<32;i++){before();after();}
            var old=new List<double>();var now=new List<double>();const int iterations=128,blocks=8;
            for(int block=0;block<blocks;block++){if(block%2==0){old.Add(Time(before,iterations));now.Add(Time(after,iterations));}else{now.Add(Time(after,iterations));old.Add(Time(before,iterations));}}
            var oldBlocks=old.ToArray();var nowBlocks=now.ToArray();old.Sort();now.Sort();double a=(old[3]+old[4])*.5,b=(now[3]+now[4])*.5;
            report.benchmarks.Add(new Row{name=jar==0?"no_jar":moving?"moving_jar":"stationary_jar",cells=cells,motions=s.motion.Count,iterations=iterations,blocks=blocks,legacyMicroseconds=a,currentMicroseconds=b,speedup=a/b,legacyBlocks=oldBlocks,currentBlocks=nowBlocks});
            Check(a>0&&b>0&&!double.IsInfinity(a/b),"Finite native microbenchmark");
        }
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};
            try{Edges();Authored();foreach(int cells in new[]{81,99,121}){Benchmark(cells,0,true);Benchmark(cells,cells,false);Benchmark(cells,cells,true);}}
            catch(Exception e){report.failures.Add(e.ToString());}
            report.status=report.failures.Count==0?"PASS_NATIVE_RESOURCE_SCAN":"FAIL_NATIVE_RESOURCE_SCAN";
            var output=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY72_OUTPUT");if(string.IsNullOrEmpty(output))output="../Verification/Evidence/Gameplay72";output=Path.GetFullPath(output);Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"ResourceScan.json"),JsonUtility.ToJson(report,true));
            GC.KeepAlive(checksum);EditorApplication.Exit(report.failures.Count==0?0:1);
        }
    }
}
#endif

#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using Object=UnityEngine.Object;
namespace HeartOfTheRain.Verification {
    public static class CommandPreparation78Verification {
        [Serializable] public sealed class Row {public string name,queueBeforeHash,queueAfterHash,wholePathsHash;public int phases,paths;}
        [Serializable] public sealed class Benchmark {public string name,scenario;public int phases,iterations,blocks,legacyWalkerCalls,currentWalkerCalls;public double legacyMedianMs,currentMedianMs;public double[] legacyBlocks,currentBlocks;}
        [Serializable] public sealed class Report {
            public string status,utc,unity,archivedMethodSHA256,compiledMethodSHA256,effectResourcesSHA256,
                archivedEffectResourcesSHA256,archivedWalkerSHA256,currentNormalizedWalkerSHA256,effectResourcesBindingMode;
            public string scope="Native Unity Editor exact77 compiled resource-method control, ordered per-phase/full-queue dependency parity, model/queue immutability, real texture residency/eviction and helper-owner lifecycle. Benchmarks measure dependency construction/lookups only; initial and complete traversal/retry workloads retain all alternating blocks, including slower results. They exclude asset loads, model solve, playback construction, GPU, Android and touch latency. Helper callback-boundary replacement is a data-only state test, not a UI/PlayMode callback run.";
            public int checks,authoredTurns,queues,phaseComparisons,compositePhases,continuedMotions,syntheticCases;
            public bool compiledSourceMatchesArchive,pathSetParity=true,pathOrderParity=true,rawTurnParity=true,queueUnchanged=true,evictionReadinessPreserved,ownerReloadPreserved,legacyControlPreserved,defaultResolverBinding,normalizedWalkerMatchesArchive;
            public List<Row> rows=new List<Row>();public List<Benchmark> benchmarks=new List<Benchmark>();public List<string> lifecycle=new List<string>(),errors=new List<string>();
        }
        [Serializable] sealed class Steps {public List<BoardStep> steps;}
        static Report report;static M46Assets assets;static CommandResourcePreparation context;static CommandPreparation77Control control;static M46AtlasBank bank;static int checksum;
        static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
        static string Hash(string value){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(Encoding.UTF8.GetBytes(value))).Replace("-","").ToLowerInvariant();}
        static void Check(bool okay,string label){report.checks++;if(!okay)throw new InvalidOperationException(label);}
        static string QueueHash(IList<BoardStep> queue){var text=new StringBuilder(JsonUtility.ToJson(new Steps{steps=queue.ToList()}));foreach(var phase in queue)if(phase.playbackTracks!=null)foreach(var track in phase.playbackTracks)text.Append(track.start.ToString("R",System.Globalization.CultureInfo.InvariantCulture)).Append('/').Append(track.leadIn.ToString("R",System.Globalization.CultureInfo.InvariantCulture)).Append(JsonUtility.ToJson(track.step));return Hash(text.ToString());}
        static void Paths(IEnumerable<string> expected,IEnumerable<string> actual,string label){Check(expected.ToHashSet().SetEquals(actual),label+" exact path set");Check(expected.SequenceEqual(actual),label+" exact request enumeration order");}
        static CommandResourcePreparation.Plan Inspect(string name,List<BoardStep> queue){
            string before=QueueHash(queue);var plan=context.Build(queue);Paths(control.RequiredResources(queue),bank.RequiredResources(queue),name+" current bank retains77 control");Paths(control.RequiredResources(queue),plan.All,name+" whole queue");Check(plan.Count==queue.Count&&plan.Matches(queue),name+" queue reference identity");
            for(int i=0;i<queue.Count;i++){
                var expected=control.RequiredResources(new[]{queue[i]});Paths(expected,plan.Phase(i),name+" phase "+i);Check(plan.MatchesPhase(i,queue[i]),name+" phase reference identity "+i);report.phaseComparisons++;
                if(queue[i].playbackTracks!=null&&queue[i].playbackTracks.Count>0)report.compositePhases++;
                report.continuedMotions+=queue[i].motion.Count(LocalCascadeContinuation.IsContinuation);
            }
            string after=QueueHash(queue);Check(before==after,name+" raw fields/track order unchanged");report.queues++;report.rows.Add(new Row{name=name,phases=queue.Count,paths=plan.All.Count,queueBeforeHash=before,queueAfterHash=after,wholePathsHash=Hash(string.Join("\n",plan.All))});return plan;
        }
        static string Method(string text){int start=text.IndexOf("        public HashSet<string> RequiredResources(",StringComparison.Ordinal);int end=text.IndexOf("        public void BeginFrame()",start,StringComparison.Ordinal);return text.Substring(start,end-start).Replace("\r\n","\n").Trim();}
        static string Compact(string text)=>new string(text.Where(c=>!char.IsWhiteSpace(c)).ToArray());
        static string Body(string text,string marker){int at=text.IndexOf(marker,StringComparison.Ordinal);if(at<0)throw new InvalidOperationException("Missing walker declaration");int first=text.IndexOf('{',at),depth=0;for(int i=first;i<text.Length;i++){if(text[i]=='{')depth++;else if(text[i]=='}'&&--depth==0)return text.Substring(first,i-first+1);}throw new InvalidOperationException("Unclosed walker declaration");}
        static void SourceControl(){
            string baseline=Path.GetFullPath("../.verification-cache/Gameplay78/BaselineSources/Unity/Assets/HeartOfTheRain/M46/Runtime/M46AtlasBank.cs");string archived=Method(File.ReadAllText(baseline));string compiled=File.ReadAllText("Assets/HeartOfTheRain/Verification/CommandPreparation77Control.cs");string begin="// BEGIN EXACT77 RequiredResources",end="// END EXACT77 RequiredResources";compiled=compiled.Substring(compiled.IndexOf(begin,StringComparison.Ordinal)+begin.Length);compiled=compiled.Substring(0,compiled.IndexOf(end,StringComparison.Ordinal)).Replace("\r\n","\n").Trim();report.archivedMethodSHA256=Hash(archived);report.compiledMethodSHA256=Hash(compiled);report.compiledSourceMatchesArchive=archived==compiled;Check(report.compiledSourceMatchesArchive,"Compiled control method is exact frozen77 source");
            string effects=File.ReadAllText("Assets/HeartOfTheRain/M48/Runtime/EffectResourcesPure.cs"),prior=File.ReadAllText(Path.GetFullPath("../.verification-cache/Gameplay78/BaselineSources/Unity/Assets/HeartOfTheRain/M48/Runtime/EffectResourcesPure.cs"));
            report.effectResourcesSHA256=Hash(effects);report.archivedEffectResourcesSHA256=Hash(prior);
            // Source79 adds resolver injection for workers. Independently pin
            // the old walker body and default bindings, rather than claiming
            // that the deliberately changed whole source file is unchanged.
            string archivedWalker=Compact(Body(prior,"public static EffectResources ForSteps(").Replace("BoardPresentation.PowerAtlas","powerAtlas").Replace("BoardPresentation.BodyKey","bodyKey"));
            string currentWalker=Compact(Body(effects,"public static EffectResources ForSteps(IEnumerable<BoardStep> steps,Func<Piece,string> bodyKey,Func<int,int> powerAtlas)"));
            currentWalker=currentWalker.Replace(Compact("if(bodyKey==null)throw new ArgumentNullException(nameof(bodyKey));"),"").Replace(Compact("if(powerAtlas==null)throw new ArgumentNullException(nameof(powerAtlas));"),"");
            report.archivedWalkerSHA256=Hash(archivedWalker);report.currentNormalizedWalkerSHA256=Hash(currentWalker);report.normalizedWalkerMatchesArchive=archivedWalker==currentWalker;
            report.defaultResolverBinding=Compact(effects).Contains(Compact("public static EffectResources ForSteps(IEnumerable<BoardStep> steps)=>ForSteps(steps,BoardPresentation.BodyKey,BoardPresentation.PowerAtlas);"));
            report.effectResourcesBindingMode="normalized_exact77_walker_plus_default_resolver_bindings";
            Check(report.normalizedWalkerMatchesArchive,"Typed dependency walker core retains independent normalized77 body");Check(report.defaultResolverBinding,"Default walker retains original BodyKey/PowerAtlas bindings");
        }
        static Dictionary<string,List<BoardStep>> Authored(){
            var selected=new Dictionary<string,List<BoardStep>>();
            for(int level=0;level<50;level++)foreach(int kind in new[]{-1,4,5,7,11,16,21}){
                var model=new BoardModel(JsonUtility.FromJson<LevelData>(assets.levels[level].text));TurnResult turn;
                if(kind<0){var move=model.LegalSwaps().First();turn=model.Swap(move[0].x,move[0].y,move[1].x,move[1].y);}else{var piece=model.Pieces.Values.First(p=>p.family=="gem");model.InjectReviewPower(piece.x,piece.y,kind);turn=model.Tap(piece.x,piece.y);}
                string name="L"+(level+1)+"_"+(kind<0?"match":"power"+kind);Check(turn.accepted,name+" accepted");string before=Hash(JsonUtility.ToJson(turn)),final=Hash(JsonUtility.ToJson(model.Snapshot()));Inspect(name+"_raw",turn.steps);var queue=BoardPlayback.Build(turn.steps,model.Level);Inspect(name+"_playback",queue);Check(before==Hash(JsonUtility.ToJson(turn))&&final==Hash(JsonUtility.ToJson(model.Snapshot())),name+" model turn/final immutable");report.authoredTurns++;
                if((kind<0&&new[]{4,14,31,33}.Contains(level+1))||(level==25&&new[]{4,7,16,21}.Contains(kind)))selected.Add(name,queue);
            }
            Check(report.authoredTurns==350&&report.compositePhases>0&&report.continuedMotions>0,"Actual350-turn corpus includes composite/carry continuation dependencies");return selected;
        }
        static BoardSnapshot Snapshot(params Piece[] pieces)=>new BoardSnapshot{pieces=pieces,goals=Array.Empty<Goal>(),status="Playing"};
        static BoardStep Simple(string kind="match",string family="gem",int color=0){var snap=Snapshot(new Piece{id=1,family=family,power=4,color=color,hp=3});return new BoardStep{kind=kind,before=snap,after=snap};}
        static string ExceptionType(Action action){try{action();return "none";}catch(Exception ex){return ex.GetType().Name;}}
        static void GuardControls(){
            var queue=new List<BoardStep>{Simple(),Simple(family:"power")};var plan=context.Build(queue);var naive=new HashSet<string>();foreach(var phase in queue)naive.UnionWith(control.RequiredResources(new[]{phase}));Check(naive.SetEquals(plan.All)&&!naive.SequenceEqual(plan.All),"Naive phase-path union is rejected by real category-order counterexample");
            Check(plan.Matches(new List<BoardStep>(queue))&&!plan.Matches(null),"Queue list identity is independent from its immutable phase identities");queue.Reverse();Check(!plan.Matches(queue),"Same-count phase reordering invalidates plan");Check(!plan.MatchesPhase(-1,null)&&!plan.MatchesPhase(plan.Count,null),"Out-of-range phase identities are rejected");Check(ExceptionType(()=>plan.Phase(-1))==nameof(ArgumentOutOfRangeException),"Invalid lookup retains guarded phase-index failure");
            var malformed=Simple();malformed.before=null;var invalid=new List<BoardStep>{malformed};Check(ExceptionType(()=>control.RequiredResources(invalid))==ExceptionType(()=>context.Build(invalid)),"Malformed snapshot preserves old exception type");Check(ExceptionType(()=>control.RequiredResources(null))==ExceptionType(()=>context.Build(null)),"Null command preserves old argument failure type");report.syntheticCases+=2;
        }
        static void Synthetic(){
            var advanced=Simple();advanced.before=Snapshot(new Piece{id=1,family="pod",hp=3},new Piece{id=2,family="cabinet",hp=3},new Piece{id=3,family="crystal",hp=2},new Piece{id=4,family="pail"},new Piece{id=5,family="power",power=16});advanced.after=advanced.before;advanced.damage.AddRange(new[]{new Damage{id=1,family="pod",beforeHP=3,afterHP=1},new Damage{id=2,family="cabinet",beforeHP=3,afterHP=2},new Damage{id=3,family="crystal",beforeHP=2,afterHP=1}});advanced.collections.AddRange(new[]{new GoalCollection{family="pod"},new GoalCollection{family="cabinet"}});advanced.motion.Add(new HeartOfTheRain.M46.Motion{id=4,fromY=2,toY=0});Inspect("advanced_collections_moving_jar",new List<BoardStep>{advanced});report.syntheticCases++;
            foreach(var kind in new[]{BoosterKind.Hammer,BoosterKind.Axe,BoosterKind.Ram,BoosterKind.Atlas}){var tool=Simple("booster");tool.booster=new BoosterPlan{kind=kind,contacts=Array.Empty<Contact>()};Inspect("tool_"+kind,new List<BoardStep>{tool});report.syntheticCases++;}
            var grow=Simple("grow","moss");var deliver=Simple("deliver","pail");Inspect("grow_deliver",new List<BoardStep>{grow,deliver});report.syntheticCases++;
            var track=Simple("power");track.powerPlan=new ReviewPlan{effects=new[]{new ReviewFx{atlas=28},new ReviewFx{atlas=21}},powers=new[]{new ReviewPower{atlas=9}},beams=new[]{new ReviewBeam()}};var outer=Simple("powerFall");outer.playbackTracks=new List<PlaybackTrack>{new PlaybackTrack{step=track,start=.4f}};Inspect("composite_actual_effect_categories",new List<BoardStep>{outer});report.syntheticCases++;
            var grandchild=Simple("power");grandchild.powerPlan=new ReviewPlan{effects=new[]{new ReviewFx{atlas=40}}};track.playbackTracks=new List<PlaybackTrack>{new PlaybackTrack{step=grandchild}};Inspect("nested_tracks_preserve_old_one_level_policy",new List<BoardStep>{outer});report.syntheticCases++;
            var fault=Simple("settled");fault.before.status=fault.after.status="Fault";fault.damage.Add(new Damage{family="unmapped_family",beforeHP=1});Inspect("faulted_snapshot_unknown_family",new List<BoardStep>{fault});Inspect("empty_queue",new List<BoardStep>());report.syntheticCases+=2;
            foreach(int recipe in new[]{4,5,7,21}){var model=new BoardModel(MixedPowerSwapFixtures.Match(recipe));var from=MixedPowerSwapFixtures.From(recipe);var to=MixedPowerSwapFixtures.To();model.InjectReviewPower(to.x,to.y,recipe==5||recipe==21?4:5);var turn=model.Swap(from.x,from.y,to.x,to.y);Check(turn.accepted,"Mixed creation fixture accepted "+recipe);Inspect("mixed_birth_"+recipe,BoardPlayback.Build(turn.steps,model.Level));report.syntheticCases++;}
        }
        static object Field(object owner,string name)=>owner.GetType().GetField(name,Private).GetValue(owner);
        static void Set(object owner,string name,object value)=>owner.GetType().GetField(name,Private).SetValue(owner,value);
        static object Call(object owner,string method)=>owner.GetType().GetMethod(method,Private).Invoke(owner,null);
        static void Lifecycle(){
            var node=new GameObject("Command resource lifecycle only");var game=node.AddComponent<GameplayScreen>();var second=new M46AtlasBank(assets);
            try{
                Set(game,"assets",assets);Set(game,"bank",bank);var queue=(List<BoardStep>)Field(game,"queue");var a=Simple();var b=Simple(color:1);queue.Add(a);Set(game,"queueIndex",0);Call(game,"ResetCommandPreparation");Call(game,"PrepareCommandResources");var paths=(HashSet<string>)Call(game,"CurrentPhaseResources");Check(ReferenceEquals(paths,Call(game,"CurrentPhaseResources")),"Repeated phase/PrepareQueue lookup reuses immutable paths");Paths(control.RequiredResources(queue),(HashSet<string>)Call(game,"WholeQueueResources"),"Initial live helper");
                queue.Add(b);Paths(control.RequiredResources(queue),(HashSet<string>)Call(game,"WholeQueueResources"),"Appended queue rebuild");Check(((CommandResourcePreparation.Plan)Field(game,"commandResourcePlan")).Count==2,"Append invalidates phase references/count");
                queue[0]=Simple(color:2);Check(!ReferenceEquals(paths,Call(game,"CurrentPhaseResources")),"Same-count reference replacement invalidates plan");Paths(control.RequiredResources(new[]{queue[0]}),(HashSet<string>)Call(game,"CurrentPhaseResources"),"Reference replacement paths");
                var oldPlan=Field(game,"commandResourcePlan");Set(game,"bank",second);Call(game,"WholeQueueResources");Check(!ReferenceEquals(oldPlan,Field(game,"commandResourcePlan")),"Bank owner replacement rebuilds metadata without stale residency");
                // Reentrant callback boundaries can replace queue and bank
                // before Enqueue subsequently asks for whole-queue prefetch.
                Action boundary=()=>{queue.Clear();queue.Add(Simple(color:3));Set(game,"queueIndex",0);Set(game,"bank",bank);Call(game,"ResetCommandPreparation");};boundary();Paths(control.RequiredResources(queue),(HashSet<string>)Call(game,"WholeQueueResources"),"Callback-boundary queue/bank reset");report.ownerReloadPreserved=true;
                Call(game,"ClearCommandResources");Check(Field(game,"commandResourcePlan")==null,"Settled completion clears plan");game.VerificationUseCheckpoint77Resources=true;Call(game,"PrepareCommandResources");Check(Field(game,"commandResourcePlan")==null,"77 control does no eager planning");var legacy=(HashSet<string>)Call(game,"CurrentPhaseResources");Check(!ReferenceEquals(legacy,Call(game,"CurrentPhaseResources")),"77 control repeats original phase walker");Paths(control.RequiredResources(queue),(HashSet<string>)Call(game,"WholeQueueResources"),"77 control full queue");report.legacyControlPreserved=true;
            }finally{Set(game,"bank",null);Object.DestroyImmediate(node);second.Dispose();}
            var resident=new M46AtlasBank(assets);try{
                var queue=new List<BoardStep>{Simple()};var plan=context.Build(queue);var paths=plan.Phase(0);Check(paths.Count==1,"Simple tile fixture owns one actual texture path");Check(!resident.Ready(paths)&&!resident.Ready(control.RequiredResources(queue)),"Cold plan preserves live false readiness");var textureMethod=typeof(M46AtlasBank).GetMethod("Texture",Private);string path=paths.First();textureMethod.Invoke(resident,new object[]{null,path});Check(resident.Ready(paths)&&resident.Ready(control.RequiredResources(queue)),"Real resident texture makes old/new readiness true");
                var entries=(IDictionary)Field(resident,"textures");foreach(DictionaryEntry pair in entries)pair.Value.GetType().GetField("used").SetValue(pair.Value,-1000f);resident.TextureBudget=0;resident.BeginFrame();resident.EndFrame(true);Check(!resident.Ready(paths)&&!resident.Ready(control.RequiredResources(queue)),"Real texture eviction makes cached plan readiness false again");Paths(control.RequiredResources(queue),plan.All,"Eviction does not mutate dependency paths");report.evictionReadinessPreserved=true;
            }finally{resident.Dispose();}
            var changed=Object.Instantiate(assets);try{changed.bodies.Single(b=>b.key=="tile0").resource="Verification/Missing_Command78_Texture";var missingContext=new CommandResourcePreparation(changed);var missingControl=new CommandPreparation77Control(changed);var missingBank=new M46AtlasBank(changed);try{var queue=new List<BoardStep>{Simple()};var plan=missingContext.Build(queue);Paths(missingControl.RequiredResources(queue),plan.All,"Missing resource retains exact old load path");Check(!missingBank.Ready(plan.All),"Missing resource cannot be mislabeled resident by plan");}finally{missingBank.Dispose();}}finally{Object.DestroyImmediate(changed);}
            report.lifecycle.AddRange(new[]{"cached phase reuse","queue append","same-count replacement","bank-owner reset","callback-boundary replacement (data only)","settled clear","development77 control","real load/eviction readiness","unknown resource path"});
        }
        static void Consume(HashSet<string> paths){checksum^=paths.Count;foreach(var path in paths)checksum^=path.Length;}
        static void Work(List<BoardStep> queue,bool legacy,int scenario){
            if(legacy){if(queue.Count>0)Consume(control.RequiredResources(new[]{queue[0]}));Consume(control.RequiredResources(queue));if(scenario>0)for(int i=1;i<queue.Count;i++)Consume(control.RequiredResources(new[]{queue[i]}));if(scenario==2)for(int i=0;i<queue.Count;i++){Consume(control.RequiredResources(new[]{queue[i]}));Consume(control.RequiredResources(new[]{queue[i]}));}}
            else{var plan=context.Build(queue);if(queue.Count>0){checksum^=plan.Matches(queue)?1:0;Consume(plan.Phase(0));}checksum^=plan.Matches(queue)?1:0;Consume(plan.All);if(scenario>0)for(int i=1;i<queue.Count;i++){checksum^=plan.Matches(queue)?1:0;Consume(plan.Phase(i));}if(scenario==2)for(int i=0;i<queue.Count;i++)for(int retry=0;retry<2;retry++){checksum^=plan.Matches(queue)?1:0;Consume(plan.Phase(i));}}
        }
        static double Time(List<BoardStep> queue,bool legacy,int scenario,int iterations){var watch=Stopwatch.StartNew();for(int i=0;i<iterations;i++)Work(queue,legacy,scenario);watch.Stop();return watch.Elapsed.TotalMilliseconds/iterations;}
        static double Median(double[] values){var ordered=(double[])values.Clone();Array.Sort(ordered);return(ordered[ordered.Length/2-1]+ordered[ordered.Length/2])*.5;}
        static void Benchmarks(Dictionary<string,List<BoardStep>> fixtures){
            foreach(var fixture in fixtures)for(int scenario=0;scenario<3;scenario++){
                for(int i=0;i<8;i++){Work(fixture.Value,true,scenario);Work(fixture.Value,false,scenario);}const int blocks=8,iterations=16;var old=new double[blocks];var current=new double[blocks];
                for(int block=0;block<blocks;block++)if(block%2==0){old[block]=Time(fixture.Value,true,scenario,iterations);current[block]=Time(fixture.Value,false,scenario,iterations);}else{current[block]=Time(fixture.Value,false,scenario,iterations);old[block]=Time(fixture.Value,true,scenario,iterations);}
                int n=fixture.Value.Count;report.benchmarks.Add(new Benchmark{name=fixture.Key,scenario=scenario==0?"initial_phase_and_whole_queue":scenario==1?"all_phase_entries":"all_phase_entries_plus_two_retry_lookups",phases=n,blocks=blocks,iterations=iterations,legacyWalkerCalls=scenario==0?(n>0?2:1):scenario==1?n+1:n*3+1,currentWalkerCalls=n,legacyMedianMs=Median(old),currentMedianMs=Median(current),legacyBlocks=old,currentBlocks=current});Check(old.All(x=>x>0)&&current.All(x=>x>0),"Finite complete matched dependency timing "+fixture.Key+"/"+scenario);
            }
        }
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};try{
                SourceControl();var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");Check(ui&&ui.boards&&ui.boards.levels.Length==50,"Approved50-level assets available");assets=ui.boards;context=new CommandResourcePreparation(assets);control=new CommandPreparation77Control(assets);bank=new M46AtlasBank(assets);var selected=Authored();Synthetic();GuardControls();Lifecycle();Benchmarks(selected);
            }catch(Exception ex){report.errors.Add(ex.ToString());report.pathSetParity=report.pathOrderParity=report.rawTurnParity=report.queueUnchanged=false;}finally{bank?.Dispose();}
            report.status=report.errors.Count==0?"PASS_NATIVE_COMMAND_PREPARATION78":"FAIL_NATIVE_COMMAND_PREPARATION78";string output=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY78_OUTPUT");if(string.IsNullOrEmpty(output))output=Path.GetFullPath("../Verification/Evidence/Gameplay78");Directory.CreateDirectory(Path.Combine(output,"Native"));File.WriteAllText(Path.Combine(output,"Native/CommandPreparation78.json"),JsonUtility.ToJson(report,true));GC.KeepAlive(checksum);EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif

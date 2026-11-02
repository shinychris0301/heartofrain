#if UNITY_EDITOR || DEVELOPMENT_BUILD
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;
using UnityEngine.SceneManagement;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using Old = HeartOfTheRain.Verification.Checkpoint75Control;

namespace HeartOfTheRain.Verification {
    // Pure construction controls. Neither returned queue is submitted to the
    // live game; the archived queue owns a different ContinuedMotion subtype.
    public static class SmoothnessCommandProof {
        public sealed class Fixture {
            public string name,turnHash,finalHash;public int levelNumber,kind;
            public LevelData geometry;public TurnResult turn;
        }
        [Serializable] public sealed class Pair {
            public int index,frame,baselineGc0Before,baselineGc0After,currentGc0Before,currentGc0After;
            public bool baselineFirst,rawUnchanged,queueParity;
            public long baselineStartedTicks,baselineFinishedTicks,currentStartedTicks,currentFinishedTicks;
            public double baselineMs,currentMs;public int baselinePhases,currentPhases;
            public string baselineQueueHash,currentQueueHash,rawBeforeHash,rawAfterHash;
        }
        [Serializable] public sealed class Row {
            public string name,turnHash,finalHash;public int levelNumber,kind;
            public double baselineMedianMs,currentMedianMs,baselineP95Ms,currentP95Ms,baselineMaxMs,currentMaxMs;
            public List<Pair> pairs=new List<Pair>();
        }
        public static string Hash(string text){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(Encoding.UTF8.GetBytes(text))).Replace("-","").ToLowerInvariant();}
        public static string RawHash(TurnResult turn)=>Hash(JsonUtility.ToJson(turn));
        public static List<BoardStep> Build(Fixture f,bool baseline,bool geometry=true,bool scheduled=true)
            =>baseline?Old.BoardPlayback.Build(f.turn.steps,geometry?f.geometry:null,scheduled,true)
                      :BoardPlayback.Build(f.turn.steps,geometry?f.geometry:null,scheduled,true);
        public static Fixture Solve(LevelData level,int kind,string name=null){
            var model=new BoardModel(level);TurnResult turn;
            if(kind<0){var move=model.LegalSwaps().First();turn=model.Swap(move[0].x,move[0].y,move[1].x,move[1].y);}
            else if(kind==100)turn=ObstacleDensityFixture.Solve(model);
            else{var p=model.Pieces.Values.First(v=>v.family=="gem");model.InjectReviewPower(p.x,p.y,kind);turn=model.Tap(p.x,p.y);}
            if(!turn.accepted)throw new InvalidOperationException("Construction fixture rejected");
            return new Fixture{name=name??("L"+level.globalLevel+(kind<0?"_match":"_power"+kind)),
                levelNumber=level.globalLevel,kind=kind,geometry=level,turn=turn,
                turnHash=RawHash(turn),finalHash=Hash(JsonUtility.ToJson(model.Snapshot()))};
        }
        public static IEnumerable<Fixture> Benchmarks(GameplayUIAssets ui){
            foreach(int level in new[]{4,14,31,33})yield return Solve(JsonUtility.FromJson<LevelData>(ui.boards.levels[level-1].text),-1);
            yield return Solve(JsonUtility.FromJson<LevelData>(ui.boards.levels[0].text),16,"L1_Golden");
            yield return Solve(JsonUtility.FromJson<LevelData>(ui.boards.levels[25].text),21,"L26_Bomb");
            yield return Solve(JsonUtility.FromJson<LevelData>(ui.boards.levels[47].text),7,"L48_Orb");
            var dense=ObstacleDensityFixture.Level(JsonUtility.FromJson<LevelData>(ui.boards.levels[25].text),45,"crate");
            yield return Solve(dense,100,"DenseCrate45_DoubleOrb");
        }
        public static string Signature(List<BoardStep> queue,bool baseline){
            var text=new StringBuilder();
            void Number(float value){text.Append(value.ToString("R",CultureInfo.InvariantCulture)).Append(';');}
            void Step(BoardStep s,int depth){
                if(depth>32)throw new InvalidOperationException("Cyclic playback tracks");
                text.Append(JsonUtility.ToJson(s));text.Append("tracks:").Append(s.playbackTracks==null?-1:s.playbackTracks.Count);
                if(s.playbackTracks!=null)foreach(var t in s.playbackTracks){Number(t.start);Number(t.leadIn);Step(t.step,depth+1);}
                foreach(var motion in s.motion){
                    text.Append("continued:").Append(baseline?Old.LocalCascadeContinuation.IsContinuation(motion):LocalCascadeContinuation.IsContinuation(motion));
                    var contacts=(baseline?Old.LocalCascadeContinuation.LandingContacts(motion):LocalCascadeContinuation.LandingContacts(motion)).ToArray();
                    var times=new SortedSet<float>{-1,0,motion.delay,motion.delay+motion.seconds*.5f,motion.delay+motion.seconds,s.duration,s.duration+1};
                    foreach(float contact in contacts){Number(contact);times.Add(contact-.0001f);times.Add(contact);times.Add(contact+.0001f);}
                    foreach(float at in times){
                        float local;var segment=baseline?Old.LocalCascadeContinuation.Segment(motion,at,out local):LocalCascadeContinuation.Segment(motion,at,out local);
                        Number(at);Number(local);text.Append(JsonUtility.ToJson(segment));float x,y;
                        if(baseline)Old.TileFall.Position(motion,at,out x,out y);else TileFall.Position(motion,at,out x,out y);
                        Number(x);Number(y);text.Append(baseline?Old.TileFall.Moving(motion,at):TileFall.Moving(motion,at));
                    }
                }
            }
            foreach(var step in queue)Step(step,0);return Hash(text.ToString());
        }
        public static void Warm(Fixture f){for(int n=0;n<2;n++){Build(f,true);Build(f,false);}}
        public static Pair Measure(Fixture f,int index,Action<bool,string> check){
            var pair=new Pair{index=index,frame=Time.frameCount,baselineFirst=index%2==0,rawBeforeHash=RawHash(f.turn)};
            List<BoardStep> baseline=null,current=null;
            void Timed(bool old){
                int gcBefore=GC.CollectionCount(0);long start=Stopwatch.GetTimestamp();
                var queue=Build(f,old);long end=Stopwatch.GetTimestamp();int gcAfter=GC.CollectionCount(0);
                if(old){baseline=queue;pair.baselineStartedTicks=start;pair.baselineFinishedTicks=end;pair.baselineGc0Before=gcBefore;pair.baselineGc0After=gcAfter;}
                else{current=queue;pair.currentStartedTicks=start;pair.currentFinishedTicks=end;pair.currentGc0Before=gcBefore;pair.currentGc0After=gcAfter;}
            }
            if(pair.baselineFirst){Timed(true);Timed(false);}else{Timed(false);Timed(true);}
            pair.baselineMs=(pair.baselineFinishedTicks-pair.baselineStartedTicks)*1000.0/Stopwatch.Frequency;
            pair.currentMs=(pair.currentFinishedTicks-pair.currentStartedTicks)*1000.0/Stopwatch.Frequency;
            // Serialization, recursive graph/pose validation and raw hashes are
            // deliberately after BOTH measured calls, never between branches.
            pair.baselinePhases=baseline.Count;pair.currentPhases=current.Count;
            pair.baselineQueueHash=Signature(baseline,true);pair.currentQueueHash=Signature(current,false);
            pair.rawAfterHash=RawHash(f.turn);pair.rawUnchanged=pair.rawBeforeHash==pair.rawAfterHash&&pair.rawAfterHash==f.turnHash;
            pair.queueParity=pair.baselineQueueHash==pair.currentQueueHash;
            check(pair.rawUnchanged,"Immutable raw turn "+f.name+"/"+index);check(pair.queueParity,"Complete queue parity "+f.name+"/"+index);
            return pair;
        }
        public static Row RowFor(Fixture f)=>new Row{name=f.name,levelNumber=f.levelNumber,kind=f.kind,turnHash=f.turnHash,finalHash=f.finalHash};
        public static void Summarize(Row row){
            var a=row.pairs.Select(p=>p.baselineMs).OrderBy(x=>x).ToArray();var b=row.pairs.Select(p=>p.currentMs).OrderBy(x=>x).ToArray();
            row.baselineMedianMs=(a[(a.Length-1)/2]+a[a.Length/2])*.5;row.currentMedianMs=(b[(b.Length-1)/2]+b[b.Length/2])*.5;
            row.baselineP95Ms=a[(int)Math.Ceiling(a.Length*.95)-1];row.currentP95Ms=b[(int)Math.Ceiling(b.Length*.95)-1];row.baselineMaxMs=a.Last();row.currentMaxMs=b.Last();
        }
    }

    public sealed class SmoothnessCommandProbe:MonoBehaviour {
        public const string Request="HOTR_RunSmoothnessCommand";
        [Serializable] public sealed class Report {
            public string status="RUNNING",utc,platform,graphics,device;
            public string scope="Same-process, same-APK archived75/current pure playback construction on identical immutable turns. Two warm builds per branch, twelve balanced AB/BA pairs per fixture, one yield per pair. No model solve, hashing, queue comparison, Accept, Next, event callbacks, resource loading, rendering or report I/O inside timed Build calls. Times include managed dispatch/timestamp and OS/emulator scheduling; development/debug code and outside-span validation can affect subsequent GC/cache state. Not frame pacing, input latency, GPU completion, allocation savings or a universal speedup claim. Archived queues never enter GameplayScreen.";
            public int baselineCheckpoint=75,checks,fixtures,pairsPerFixture=12,warmBuildsPerBranch=2;
            public long stopwatchFrequency;public bool sameProcess=true,rawInputUnchanged=true,completeQueueParity=true;
            public List<SmoothnessCommandProof.Row> rows=new List<SmoothnessCommandProof.Row>();public List<string> errors=new List<string>();
        }
        Report report;string memoryPlayerId;double deadline;Canvas[] hidden;bool[] canvasEnabled;bool finished;
        static bool pending;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]static void Boot(){
            SceneManager.sceneLoaded-=Attach;pending=false;var path=Path.Combine(Application.persistentDataPath,Request);if(!File.Exists(path))return;
            File.Delete(path);pending=true;SceneManager.sceneLoaded+=Attach;
        }
        static void Attach(Scene scene,LoadSceneMode mode){
            if(!pending)return;var first=FindFirstObjectByType<FirstStartPage>();if(!first)return;pending=false;SceneManager.sceneLoaded-=Attach;first.reviewAlways=true;
            var host=first.home.GetComponent<PlayerProfileHost>();if(!host)host=first.home.gameObject.AddComponent<PlayerProfileHost>();var profile=PlayerProfile.New(new[]{5,5,3,2});
            host.VerificationRepository=new MemoryProfileRepository(profile);host.VerificationAuthorityFactory=_=>new UnavailableGiftAuthority();host.VerificationLivesClock=()=>1000;
            var node=new GameObject("Opt-in same-process playback construction");DontDestroyOnLoad(node);node.AddComponent<SmoothnessCommandProbe>().memoryPlayerId=profile.playerId;
        }
        void Start(){report=new Report{utc=DateTime.UtcNow.ToString("o"),platform=Application.platform.ToString(),graphics=SystemInfo.graphicsDeviceName,device=SystemInfo.deviceModel,stopwatchFrequency=Stopwatch.Frequency};deadline=Time.realtimeSinceStartupAsDouble+240;Application.logMessageReceived+=Log;StartCoroutine(Guard(Run()));}
        void Check(bool ok,string label){report.checks++;if(!ok)throw new InvalidOperationException(label);}
        void Log(string message,string trace,LogType type){if(type==LogType.Exception||type==LogType.Error||type==LogType.Assert){report.errors.Add(message+"\n"+trace);Finish();}}
        IEnumerator Guard(IEnumerator routine){
            while(!finished){object next=null;bool more=false;try{if(Time.realtimeSinceStartupAsDouble>deadline)throw new TimeoutException("Same-process construction probe");more=routine.MoveNext();if(more)next=routine.Current;}catch(Exception error){report.errors.Add(error.ToString());Finish();}if(finished)yield break;if(!more){Finish();yield break;}yield return next;}
        }
        IEnumerator Run(){
            FirstStartPage first;while(!(first=FindFirstObjectByType<FirstStartPage>())||!first.Initialized||FindFirstObjectByType<HeartOfTheRain.App.Launch.LaunchPage>())yield return null;
            var host=first.home.GetComponent<PlayerProfileHost>();Check(host&&host.Ready&&host.VerificationRepository is MemoryProfileRepository&&host.Service.Read().playerId==memoryPlayerId,"Isolated memory profile ready");
            hidden=FindObjectsByType<Canvas>(UnityEngine.FindObjectsSortMode.InstanceID);canvasEnabled=hidden.Select(c=>c.enabled).ToArray();foreach(var c in hidden)c.enabled=false;
            Check(!LocalCascadeContinuation.VerificationUseCheckpoint74&&!Old.LocalCascadeContinuation.VerificationUseCheckpoint74,"Ordinary75/current scheduling controls selected");
            foreach(var fixture in SmoothnessCommandProof.Benchmarks(first.assets.Gameplay)){
                SmoothnessCommandProof.Warm(fixture);var row=SmoothnessCommandProof.RowFor(fixture);
                for(int n=0;n<12;n++){var pair=SmoothnessCommandProof.Measure(fixture,n,Check);row.pairs.Add(pair);report.rawInputUnchanged&=pair.rawUnchanged;report.completeQueueParity&=pair.queueParity;yield return null;}
                SmoothnessCommandProof.Summarize(row);report.rows.Add(row);report.fixtures++;
            }
            Check(report.fixtures==8&&report.rows.All(r=>r.pairs.Count==12),"Eight complete balanced construction fixtures");
        }
        void Finish(){
            if(finished)return;finished=true;Application.logMessageReceived-=Log;report.status=report.errors.Count==0?"PASS_SAME_APK_COMMAND_CONSTRUCTION76":"FAIL_SAME_APK_COMMAND_CONSTRUCTION76";
            if(hidden!=null)for(int i=0;i<hidden.Length;i++)if(hidden[i])hidden[i].enabled=canvasEnabled[i];
            string folder=Path.Combine(Application.persistentDataPath,"SmoothnessCommand");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"Report.json"),JsonUtility.ToJson(report,true));
        }
        void OnDestroy(){Application.logMessageReceived-=Log;SceneManager.sceneLoaded-=Attach;}
    }
}
#endif

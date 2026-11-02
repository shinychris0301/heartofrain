#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using HeartOfTheRain.App.FirstStart;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace HeartOfTheRain.Verification {
    // Real Resources.LoadAsync failure and live local flow, using only the
    // existing review scene's disposable memory profile. Never a player save.
    [InitializeOnLoad] public static class ResourcePreparation93Verification {
        const string Key="HOTR.ResourcePreparation93";
        const string Missing="HOTR_ResourcePreparation93_Intentional_Missing_Texture";
        const BindingFlags Hidden=BindingFlags.Instance|BindingFlags.NonPublic;
        static readonly string[] Cases={"live_playing_fault_refund","live_out_of_moves_fault_refund","valid_resource_gate","stale_board_completion"};
        [Serializable] sealed class Row {public string name,beforeCheckpoint,afterCheckpoint,attemptState;public int missingResourceErrors,faultExceptions,flowFaultErrors,settlements;public bool passed;}
        [Serializable] sealed class Report {
            public string status="RUNNING",utc,unity,scope="Actual Unity Editor Play Mode Resources.LoadAsync missing-texture failures, GameplayScreen foreground preparation and HomeLevelFlow local fault settlement. Review-only in-memory profile verifies no life loss, once-only starting-item refund, valid preparation and stale-board fencing. Controlled queue dependency injection uses the production plan type; it does not mutate authored assets. No Android, real player save, server replay, provider or performance acceptance.";
            public int checks,cases;public List<Row> rows=new List<Row>();public List<string> passed=new List<string>(),errors=new List<string>();
        }
        static Report report;static Row row;static HomePage home;static HomeLevelFlow flow;static PlayerProfileHost profile;static PreLevelModal modal;static GameplayScreen game;
        static bool begun,finished,expectMissing;static int index,phase,settlements,missingErrors,faultExceptions,flowFaultErrors;static double deadline,caseDeadline;
        static string output,attempt,checkpoint;static PlayerProfile before;static IEnumerator stale,staleWarm;static BoardModel staleBoard;static M46AtlasBank staleBank;
        static ResourcePreparation93Verification(){if(SessionState.GetBool(Key,false))EditorApplication.update+=Tick;}
        public static void Run(){SessionState.SetBool(Key,true);EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity");UnityEngine.Object.FindFirstObjectByType<FirstStartPage>().reviewAlways=true;EditorApplication.update-=Tick;EditorApplication.update+=Tick;EditorApplication.isPlaying=true;}
        static T Field<T>(object owner,string name)=>(T)owner.GetType().GetField(name,Hidden).GetValue(owner);
        static void Set(object owner,string name,object value)=>owner.GetType().GetField(name,Hidden).SetValue(owner,value);
        static object Call(object owner,string name,params object[] arguments)=>owner.GetType().GetMethod(name,Hidden).Invoke(owner,arguments);
        static void Need(bool value,string message){report.checks++;if(!value)throw new InvalidOperationException(Cases[index]+": "+message);report.passed.Add(Cases[index]+": "+message);}
        static string Hash(BoardCheckpoint value)=>ProfileJson.Hash(JsonUtility.ToJson(value));
        static void Log(string text,string stack,LogType type){
            if(type!=LogType.Error&&type!=LogType.Exception&&type!=LogType.Assert)return;
            if(expectMissing&&text.Contains(Missing)){
                if(type==LogType.Error&&text.StartsWith("Missing texture resource: ",StringComparison.Ordinal)){missingErrors++;return;}
                if(type==LogType.Exception&&text.Contains("InvalidOperationException")){faultExceptions++;return;}
                if(type==LogType.Error&&text.StartsWith("Engine fault (playback: ",StringComparison.Ordinal)&&text.EndsWith(" released without charge.",StringComparison.Ordinal)){flowFaultErrors++;return;}
            }
            if(report!=null)report.errors.Add(text+"\n"+stack);
        }
        static void Initialize(){
            begun=true;report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};deadline=EditorApplication.timeSinceStartup+300;
            output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW93_OUT")??"../Verification/Evidence/Review93/Native/ResourcePreparation93");
            Application.logMessageReceived+=Log;
        }
        static void StartCase(){
            row=new Row{name=Cases[index]};settlements=missingErrors=faultExceptions=flowFaultErrors=0;expectMissing=index!=2;stale=staleWarm=null;
            before=profile.Service.Read();Need(before.attempts.All(a=>a.state!="Started"&&a.state!="Reserved"),"Previous isolated attempt is settled");
            if(modal.IsVisible)modal.Requested("close");flow.Open(1);Need(modal.IsVisible,"Actual pre-level opens");
            if(!flow.Preview.selected[0])modal.Requested("toggle:0");Need(flow.Preview.selected[0],"One starting Rocket is selected for debit/refund proof");
            modal.Requested("play");phase=2;caseDeadline=EditorApplication.timeSinceStartup+60;
        }
        static void InjectQueue(string path){
            var snapshot=game.Model.Snapshot();var step=new BoardStep{kind="settled",label="Controlled resource gate",duration=.06f,before=snapshot,after=snapshot};
            var queue=Field<List<BoardStep>>(game,"queue");Need(queue.Count==0&&!game.Busy,"Injection starts only from the ready idle board");queue.Add(step);Set(game,"queueIndex",0);Set(game,"current",null);
            var factory=typeof(CommandResourcePreparation.Plan).GetConstructors(Hidden).Single();
            var plan=factory.Invoke(new object[]{new[]{step},new[]{new HashSet<string>{path}},new HashSet<string>{path}});
            Set(game,"commandResourcePlan",plan);Set(game,"commandResourceOwner",Field<M46AtlasBank>(game,"bank"));
            Need(((CommandResourcePreparation.Plan)plan).Matches(queue),"Actual immutable dependency plan owns the injected phase");
        }
        static void BeginGate(){
            Need(profile.IsTransient&&!profile.ServerSession,"All settlement uses the disposable local review profile");
            game=Field<GameplayScreen>(flow,"gameplay");game.HintsEnabled=false;game.DeferTerminalPresentation=true;game.SetPause(true);
            attempt=Field<string>(flow,"attemptId");Need(profile.Service.Read().attempts.Single(a=>a.id==attempt).state=="Started","Live flow durably starts the isolated attempt");
            Need(profile.Service.Read().starting[0]==before.starting[0]-1,"Start debits exactly one selected item");
            game.TurnSettled+=status=>settlements++;
            if(index==1)game.Model.VerificationForceStatus("Out of moves");checkpoint=Hash(game.Model.Checkpoint());row.beforeCheckpoint=checkpoint;
            string path=index==2?Field<M46AtlasBank>(game,"bank").CommonResources(game.Model.Snapshot()).First():Missing;InjectQueue(path);
            if(index==3){
                staleBoard=game.Model;staleBank=Field<M46AtlasBank>(game,"bank");stale=(IEnumerator)Call(game,"PrepareQueue");Need(stale.MoveNext()&&stale.Current is IEnumerator,"Foreground gate captures its owner before yielding real Prewarm");staleWarm=(IEnumerator)stale.Current;phase=5;
            }else{game.StartCoroutine((IEnumerator)Call(game,"PrepareQueue"));phase=3;}
        }
        static void FaultChecks(){
            Need(missingErrors==1&&faultExceptions==1,"One actual missing-resource error and one routed preparation exception are recorded");
            Need(game.Model.Status=="Engine fault"&&game.Model.FaultDetail.Contains(Missing),"Playing or exhausted model becomes the existing engine-fault outcome");
            var after=game.Model.Checkpoint();after.board.status=index==1?"Out of moves":"Playing";row.afterCheckpoint=Hash(after);
            Need(row.afterCheckpoint==checkpoint,"Resource failure preserves solved board, RNG, goals, moves and inventory state");
            Need(!game.Busy&&!Field<bool>(game,"preparing")&&!game.CanAct,"Fault clears the resource wait and prevents further player input");
            Need(Field<List<BoardStep>>(game,"queue").Count==0&&Field<BoardStep>(game,"current")==null&&settlements==1,"Fault discards its presentation queue and publishes one terminal settlement");
            game.DeferTerminalPresentation=false;game.SetPause(false);phase=4;
        }
        static void AcceptedFault(){
            var current=profile.Service.Read();var record=current.attempts.Single(a=>a.id==attempt);row.attemptState=record.state;
            Need(record.state=="Released"&&flowFaultErrors==1,"Actual HomeLevelFlow releases the faulty attempt with one diagnostic");
            Need(current.lives==before.lives&&current.coins==before.coins&&current.stars==before.stars&&current.completed==before.completed,"Resource fault charges no life and grants no reward/progression");
            Need(current.starting.SequenceEqual(before.starting)&&current.tools.SequenceEqual(before.tools),"Fault restores the start debit and preserves all tool inventory");
            Need(modal.IsVisible&&flow.RetryVisible&&!flow.Playing,"Actual flow returns to the retry pre-level without a frozen board");
            string committed=JsonUtility.ToJson(current);profile.Service.ReleaseFault(attempt);var repeated=profile.Service.Read();repeated.revision=current.revision;
            Need(JsonUtility.ToJson(repeated)==committed,"Repeated fault release changes only repository revision, never receipts, inventory or balances");CompleteCase();
        }
        static void CompleteCase(){
            row.missingResourceErrors=missingErrors;row.faultExceptions=faultExceptions;row.flowFaultErrors=flowFaultErrors;row.settlements=settlements;row.passed=true;report.rows.Add(row);report.cases++;
            expectMissing=false;index++;phase=1;if(index==Cases.Length)Finish(null);
        }
        static void Tick(){try{
            if(finished||!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;if(!begun)Initialize();
            if(report.errors.Count>0)throw new InvalidOperationException(report.errors[0]);
            if(EditorApplication.timeSinceStartup>deadline||(phase>=2&&EditorApplication.timeSinceStartup>caseDeadline))throw new TimeoutException("Resource93 case "+index+" phase "+phase);
            if(phase==0){
                home=UnityEngine.Object.FindFirstObjectByType<HomePage>();flow=UnityEngine.Object.FindFirstObjectByType<HomeLevelFlow>();var first=home?home.GetComponent<FirstStartPage>():null;
                if(!home||!flow||!flow.Loading||!first||!first.Initialized)return;if(first.IsVisible){first.Request("skip");first.Request("skip");return;}
                profile=home.GetComponent<PlayerProfileHost>();modal=home.GetComponent<PreLevelModal>();Need(profile&&profile.Ready&&profile.IsTransient,"Ready review scene owns an isolated memory profile");phase=1;
            }
            if(phase==1){StartCase();return;}
            if(phase==2){if(!flow.Playing||flow.Loading.IsVisible)return;game=Field<GameplayScreen>(flow,"gameplay");if(!game.CanAct)return;BeginGate();return;}
            if(phase==3){
                if(index==2){if(Field<bool>(game,"preparing"))return;Need(missingErrors==0&&faultExceptions==0&&game.Model.Status=="Playing"&&Hash(game.Model.Checkpoint())==checkpoint,"Resident valid dependencies leave the model unchanged");Need(Field<BoardStep>(game,"current")!=null&&game.Busy&&settlements==0,"Successful gate starts the actual queued phase");game.SetPause(false);phase=7;return;}
                if(game.Model.Status!="Engine fault")return;FaultChecks();return;
            }
            if(phase==4){if(Field<GameplayScreen>(flow,"gameplay"))return;AcceptedFault();return;}
            if(phase==5){
                if(staleWarm.MoveNext())return;Need(missingErrors==1&&faultExceptions==0,"Real old-owner prewarm records its controlled missing resource");
                game.Load(0);Need(!ReferenceEquals(game.Model,staleBoard)&&!ReferenceEquals(Field<M46AtlasBank>(game,"bank"),staleBank)&&Field<bool>(game,"preparing"),"Reload owns a new board and bank with independent initialization");
                Need(!stale.MoveNext(),"Old gate stops after its yielded resource work completes");Need(Field<bool>(game,"preparing")&&game.Model.Status=="Playing"&&settlements==0,"Late old resource failure cannot clear new preparation, fault or settle the replacement board");phase=6;return;
            }
            if(phase==6){if(!game.CanAct)return;Need(game.Model.Status=="Playing"&&settlements==0&&faultExceptions==0,"Replacement board finishes its normal preparation independently");flow.ReturnHomeForReview();CompleteCase();return;}
            if(phase==7){if(game.Busy)return;Need(game.Model.Status=="Playing"&&Hash(game.Model.Checkpoint())==checkpoint&&settlements==1,"Valid prepared phase settles once without changing the model");Need(profile.Service.Read().lives==before.lives,"Valid gate charges no life");flow.ReturnHomeForReview();CompleteCase();}
        }catch(Exception error){Finish(error.ToString());}}
        static void Finish(string error){
            if(finished)return;finished=true;expectMissing=false;Application.logMessageReceived-=Log;EditorApplication.update-=Tick;SessionState.EraseBool(Key);
            if(report==null)report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};if(error!=null)report.errors.Add(error);
            report.status=report.errors.Count==0&&report.cases==Cases.Length?"PASS_NATIVE_RESOURCE_PREPARATION93":"FAIL_NATIVE_RESOURCE_PREPARATION93";
            (staleWarm as IDisposable)?.Dispose();(stale as IDisposable)?.Dispose();if(flow&&profile&&profile.IsTransient)flow.ReturnHomeForReview();
            if(string.IsNullOrEmpty(output))output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REVIEW93_OUT")??"../Verification/Evidence/Review93/Native/ResourcePreparation93");Directory.CreateDirectory(Path.Combine(output,"Native"));
            File.WriteAllText(Path.Combine(output,"Native/ResourcePreparation93.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.status.StartsWith("PASS",StringComparison.Ordinal)?0:1);
        }
    }
}
#endif

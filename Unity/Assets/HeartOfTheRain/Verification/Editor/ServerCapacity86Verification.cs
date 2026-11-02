#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.PreLevel;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.M48;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;

namespace HeartOfTheRain.Verification {
    [InitializeOnLoad] public static class ServerCapacity86Verification {
        const string Key="HOTR.ServerCapacity86";
        const string Player="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",Attempt="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
        static readonly BindingFlags Hidden=BindingFlags.Instance|BindingFlags.NonPublic;
        [Serializable] sealed class Report {
            public string status,utc,unity,scope;public int checks,cases,modelCommands,blockedCommands,confirmations;
            public bool actualPlayMode=true,actualUGui=true,actualHttp=false,serverSettlement=false,syntheticHistoryCounters=true;
            public List<string> passed=new List<string>(),errors=new List<string>(),unityErrors=new List<string>();
        }
        static Report report;static bool started,finished;
        static ServerCapacity86Verification(){if(SessionState.GetBool(Key,false))EditorApplication.update+=Tick;}
        static void OnLog(string message,string trace,LogType type){if(report!=null&&(type==LogType.Error||type==LogType.Exception||type==LogType.Assert))report.unityErrors.Add(type+":"+(message.Length>240?message.Substring(0,240):message));}
        static void Need(bool value,string code){report.checks++;if(!value)throw new InvalidOperationException(code);}
        static void Case(string name,Action body){report.cases++;try{body();report.passed.Add(name);}catch(Exception error){while(error is TargetInvocationException&&error.InnerException!=null)error=error.InnerException;report.errors.Add(name+":"+(error is InvalidOperationException?error.Message:error.GetType().Name));}}
        static void Set(object owner,string name,object value)=>owner.GetType().GetField(name,Hidden).SetValue(owner,value);
        static object Call(object owner,string name,params object[] values)=>owner.GetType().GetMethod(name,Hidden).Invoke(owner,values);
        static string Hash(BoardModel board)=>IdentityProtocol82.Sha(JsonUtility.ToJson(board.Checkpoint()));
        sealed class Fixture:IDisposable {
            public readonly GameObject root=new GameObject("Capacity86 isolated ordinary command gate");
            public readonly GameObject screenRoot=new GameObject("Capacity86 actual gameplay command and HUD");
            public readonly ServerGameSession session;public readonly ServerAttemptDocument doc;
            public readonly GameplayScreen screen;public readonly GameplayHUD hud;public readonly HomeLevelFlow flow;
            public readonly BoardModel board;public readonly LevelData level;public readonly ServerAttemptJournal journal;
            public int dispatched;
            public Fixture(int accepted){
                var assets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");Need(assets&&assets.boards.levels.Length==50,"ApprovedNativeAssets");
                level=JsonUtility.FromJson<LevelData>(assets.boards.levels[0].text);board=new BoardModel(level,23018u);
                session=root.AddComponent<ServerGameSession>();session.enabled=false;
                journal=new ServerAttemptJournal(Path.GetFullPath("../.verification-cache/Review86/Capacity/"+Guid.NewGuid().ToString("N")+"/attempt.json"),"http://127.0.0.1:18686",Player);
                doc=journal.Read();doc.acceptedActions=accepted;Set(session,"document",doc);Set(session,"journal",journal);
                Set(session,"wallet",new RuStoreServerWallet{playerId=Player,initialized=true,coins=1250,lives=5,maxLives=5,starting=new[]{5,5,3,2},tools=new[]{3,3,3,3},activeAttempt=new RuStoreServerAttempt{attemptId=Attempt,state="Started"}});
                Set(session,"broker",new ServerGameplayBrokerClient("http://127.0.0.1:18686",Player,()=>IdentityProtocol82.NewSecret(),r=>dispatched++,true));
                var host=root.AddComponent<PlayerProfileHost>();host.enabled=false;typeof(PlayerProfileHost).GetProperty("ServerSession").GetSetMethod(true).Invoke(host,new object[]{session});
                flow=root.AddComponent<HomeLevelFlow>();flow.enabled=false;Set(flow,"profile",host);
                screen=screenRoot.AddComponent<GameplayScreen>();screen.enabled=false;screen.uiAssets=assets;Set(screen,"board",board);
                var feedback=screenRoot.AddComponent<GameplayFeedback>();feedback.assets=assets;feedback.soundEnabled=false;Set(screen,"feedback",feedback);
                hud=screenRoot.AddComponent<GameplayHUD>();hud.assets=assets;hud.feedback=feedback;hud.PauseChanged=screen.SetPause;hud.Build();Set(screen,"hud",hud);
                Set(flow,"gameplay",screen);screen.BeforePlayerCommand=()=> (bool)Call(flow,"ServerBeforeCommand",screen);
            }
            public TurnResult Command(Func<TurnResult> run)=>(TurnResult)Call(screen,"Command",run);
            public Button Button(string name)=>screenRoot.GetComponentsInChildren<Button>().Single(b=>b.name==name);
            public void Back(){Button("Button_Teal").onClick.Invoke();}
            public void Dispose(){UnityEngine.Object.DestroyImmediate(root);UnityEngine.Object.DestroyImmediate(screenRoot);}
        }
        static void Boundaries(){using(var f=new Fixture(994)){
            Need(f.session.RemainingActionCapacity==6&&f.session.HasContinueActionCapacity,"994FitsContinueAndAllFiveMoves");
            foreach(int accepted in new[]{995,999,1000}){f.doc.acceptedActions=accepted;Need(!f.session.HasContinueActionCapacity,"995OrLaterCannotBuyUnrepresentableFiveMoves");}
            f.doc.acceptedActions=994;f.doc.delta.Add(new ServerMove{index=994,kind="Tap"});Need(f.session.RemainingActionCapacity==5&&!f.session.HasContinueActionCapacity,"UnverifiedDeltaCountsAgainstCapacity");
            f.doc.delta.Clear();f.doc.acceptedActions=994;Need(f.session.HasToolActionCapacity(5),"ToolAt994PreservesFiveMoveSlots");f.doc.acceptedActions=995;Need(!f.session.HasToolActionCapacity(5),"ToolAt995CannotTakePurchasedMoveSlot");
            Need(f.session.RemainingActionCapacity==5,"ToolRefusalDoesNotConsumeFreeMoveSlots");
        }}
        static void BeforeModel(){using(var f=new Fixture(1000)){
            string hash=Hash(f.board),intent=JsonUtility.ToJson(f.doc);int model=0;
            Func<TurnResult> run=()=>{model++;return f.board.Tap(0,0);};
            for(int n=0;n<2;n++){
                var result=f.Command(run);report.blockedCommands++;
                Need(!result.accepted&&model==0&&Hash(f.board)==hash,"ActualCommandGateBlocksBeforeModelAndRng");
                Need(f.hud.IsBlocking&&f.screen.ReviewInputBlocked&&JsonUtility.ToJson(f.doc)==intent&&f.dispatched==0,"CapShowsExistingExitWithoutRequestOrSettlement");
                f.Back();Need(!f.hud.IsBlocking&&!f.screen.ReviewInputBlocked&&Hash(f.board)==hash&&JsonUtility.ToJson(f.doc)==intent,"KeepPlayingPreservesBoardAttemptAndCanReopenExit");
            }
        }}
        static void LastFreeAction(){using(var f=new Fixture(999)){
            var control=BoardModel.FromCheckpoint(f.level,f.board.Checkpoint());var move=f.board.LegalSwaps()[0];
            var expected=control.Swap(move[0].x,move[0].y,move[1].x,move[1].y);
            var actual=f.Command(()=>{report.modelCommands++;return f.board.Swap(move[0].x,move[0].y,move[1].x,move[1].y);});
            Need(actual.accepted&&JsonUtility.ToJson(expected)==JsonUtility.ToJson(actual)&&Hash(control)==Hash(f.board),"LastFreeMoveRetainsExactModelOutcome");
            Need(f.session.RecordAction(new PlayerActionRecord{accepted=true,kind="swap",x=move[0].x,y=move[0].y,toX=move[1].x,toY=move[1].y},f.board.Checkpoint())&&f.session.RemainingActionCapacity==0,"LastAcceptedMoveIsRecordedAtIndex999");
            string hash=Hash(f.board);bool invoked=false;f.Command(()=>{invoked=true;return f.board.Tap(0,0);});report.blockedCommands++;
            Need(!invoked&&Hash(f.board)==hash,"FollowingFreeCommandCannotAdvanceModel");f.Back();
        }}
        static void PaidGuards(){using(var f=new Fixture(995)){
            f.doc.phase="Awaiting";f.doc.attemptId=Attempt;f.doc.checkpoint=JsonUtility.ToJson(f.board.Checkpoint());string before=JsonUtility.ToJson(f.doc);int replies=0;string code=null;
            f.session.PurchaseContinue((ok,why)=>{Need(!ok,"ContinueCapRefused");code=why;replies++;});
            Need(replies==1&&code=="ReviewReplayActionLimit"&&!f.session.Busy&&!f.session.HasPending&&f.dispatched==0&&JsonUtility.ToJson(f.doc)==before,"ContinueDeniedBeforeWalletRefreshIntentOrPaidRequest");
            var checkpoint=f.board.Checkpoint();checkpoint.board.moves=5;
            f.session.SpendTool(BoosterKind.Hammer,0,0,checkpoint,(ok,why)=>{Need(!ok&&why=="ReviewReplayActionLimit","ToolCapRefused");replies++;});
            Need(replies==2&&f.dispatched==0&&JsonUtility.ToJson(f.doc)==before,"ToolCannotSpendFutureMoveCapacity");
        }}
        static void ToolRollback(){using(var f=new Fixture(995)){
            string before=Hash(f.board);var stock=new BoosterInventory();int count=stock.atlas;
            var result=f.board.UseBooster(BoosterKind.Atlas,0,0,stock,()=> (bool)Call(f.flow,"ServerCommitTool",BoosterKind.Atlas,0,0));
            Need(!result.accepted&&stock.atlas==count&&Hash(f.board)==before&&f.dispatched==0,"CapacityRefusalRollsBackActualAtlasPermutationAndRng");
            Need(f.hud.IsBlocking&&f.screen.ReviewInputBlocked,"ToolRefusalOffersExplicitExit");f.Back();
            bool run=false;f.Command(()=>{run=true;return new TurnResult();});Need(run&&!f.screen.ReviewInputBlocked,"KeepPlayingAfterToolRefusalStillAllowsFreeCommand");
        }}
        static void CommittedTool(){using(var f=new Fixture(1000)){
            var target=f.board.Pieces.Values.First(p=>p.family=="gem");var control=BoardModel.FromCheckpoint(f.level,f.board.Checkpoint());var expected=control.UseBooster(BoosterKind.Hammer,target.x,target.y,new BoosterInventory(),()=>true);
            f.doc.phase="ToolCommitted";f.doc.paidTool=0;f.doc.paidX=target.x;f.doc.paidY=target.y;f.doc.hasLastOperation=true;
            f.doc.lastOperation=new ServerBrokerOperation{operationId=new string('c',32),model=new ServerModelState{checkpointSHA256=Hash(control)}};
            f.session.ArmCommittedTool(BoosterKind.Hammer,target.x,target.y);var stock=new BoosterInventory();
            var result=f.Command(()=>f.board.UseBooster(BoosterKind.Hammer,target.x,target.y,stock,()=> (bool)Call(f.flow,"ServerCommitTool",BoosterKind.Hammer,target.x,target.y)));
            Need(result.accepted&&JsonUtility.ToJson(result)==JsonUtility.ToJson(expected)&&Hash(f.board)==Hash(control)&&stock.hammer==2&&!f.session.ToolPermitPending,"AlreadyPaidToolAppliesAtFullCapWithoutNewEntry");
            Need(f.session.RecordAction(new PlayerActionRecord{accepted=true,kind="booster"},f.board.Checkpoint())&&f.session.RemainingActionCapacity==0&&f.dispatched==0,"CommittedToolAcknowledgesItsExistingEntry");
        }}
        static void LegacyExit(){using(var f=new Fixture(1000)){
            Need(ServerCapacityGate86.IsCapacityError("ReviewReplayActionLimit")&&ServerCapacityGate86.IsCapacityError("gameplay_history_capacity")&&!ServerCapacityGate86.IsCapacityError("ServerVerificationUnknown"),"OnlyCapacityErrorsTakeExplicitExitRoute");
            Call(f.flow,"ShowServerCapacityExit",f.screen);Need(f.hud.IsBlocking,"LegacyCapacityRefusalHasExitNotRetryOnly");f.Back();
            int exits=0;var gate=new ServerCapacityGate86();gate.Show(f.screen,()=>true,()=>{exits++;report.confirmations++;});var exit=f.Button("Button_Burgundy");exit.onClick.Invoke();exit.onClick.Invoke();
            Need(exits==1&&!gate.Showing&&f.dispatched==0,"ExistingConfirmationInvokesForfeitRouteOnce");
        }}
        static void UnavailableContinueR3(){using(var f=new Fixture(995)){
            var owner=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HeartOfTheRain/App/Home/HomePage.prefab"));
            try{
                var home=owner.GetComponent<HomePage>();home.Build();var page=owner.AddComponent<HeartOfTheRain.App.NoMoves.NoMovesPage>();page.home=home;page.art=Resources.Load<HeartOfTheRain.App.NoMoves.NoMovesAssets>("HOTR_NoMoves/Design");Need(page.art&&page.art.continuePrefab,"ApprovedR3UnavailableArt");
                var controller=owner.AddComponent<ServerContinueCoordinator>();controller.enabled=false;
                Set(controller,"game",f.screen);Set(controller,"home",home);Set(controller,"session",f.session);Set(controller,"page",page);Set(controller,"current",(Func<bool>)(()=>true));Set(controller,"active",true);
                int exits=0;Set(controller,"decline",(Action)(()=>exits++));page.Requested=controller.Request;
                f.doc.hasLastOperation=true;f.doc.lastOperation=new ServerBrokerOperation{state="Committed",model=new ServerModelState{outcome="Out of moves"}};
                string before=JsonUtility.ToJson(f.doc);Call(controller,"Ready");
                Need(page.Screen=="offer"&&page.R3&&controller.Offer==null,"CapacityUsesApprovedR3ConfirmedUnavailableOffer");
                var model=(HeartOfTheRain.ContinueReference.ContinueOfferViewModel)page.R3.GetType().GetField("model",Hidden).GetValue(page.R3);
                Need(model.Status==HeartOfTheRain.ContinueReference.ContinueOfferStatus.ConfirmedUnavailable&&page.R3.PlayLabel.text==HeartOfTheRain.App.NoMoves.NoMovesText.T("end")&&!page.R3.PriceGroup.gameObject.activeSelf,"UnavailableUsesEndLevelWithoutRetryOrPrice");
                var approvedView=page.R3;page.R3.PlayButton.onClick.Invoke();Need(page.Screen=="confirm"&&exits==0,"UnavailableEndLevelRequiresExplicitConfirmation");
                page.Nodes["Keep attempt"].GetComponent<Button>().onClick.Invoke();Need(page.Screen=="offer"&&page.R3==approvedView&&page.R3.PlayLabel.text==HeartOfTheRain.App.NoMoves.NoMovesText.T("end"),"BackFromConfirmationReturnsSameUnavailableR3");
                controller.Request("play");Need(exits==0&&!f.session.HasPending&&f.dispatched==0&&f.session.Wallet.coins==1250&&f.session.Wallet.lives==5&&JsonUtility.ToJson(f.doc)==before,"UnavailableCannotDispatchPurchaseOrChargeOnBack");
                page.R3.PlayButton.onClick.Invoke();page.Nodes["End attempt"].GetComponent<Button>().onClick.Invoke();controller.Request("end");
                Need(exits==1&&f.dispatched==0&&JsonUtility.ToJson(f.doc)==before,"ExplicitEndForwardsOnceWithoutFixtureSettlement");
            }finally{UnityEngine.Object.DestroyImmediate(owner);}
        }}
        public static void Run(){
            if(EditorApplication.isPlayingOrWillChangePlaymode)throw new InvalidOperationException("Capacity86RequiresOwnedEditorPlayMode");
            SessionState.SetBool(Key,true);EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorApplication.update-=Tick;EditorApplication.update+=Tick;EditorApplication.isPlaying=true;
        }
        static void Tick(){
            if(finished||started||!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorApplication.isUpdating)return;
            started=true;report=new Report{status="FAIL_NATIVE_SERVER_CAPACITY86",utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion,scope="Actual pinned Editor Play Mode model/RNG, GameplayScreen.Command, ordinary Home server guard, approved HUD Exit/Keep playing controls, real GameplayFeedback.Awake and actual disk journal. Synthetic near-cap counters exercise index999, Continue six-slot and Tool future-move reservation, already-paid tool replay and legacy refusal routing. Requires zero unexpected Unity error/exception/assert logs. No HTTP/life settlement, genuine1000-move playthrough, Android or production claim."};
            Application.logMessageReceived+=OnLog;
            try{
                Need(Application.unityVersion=="2022.3.62f3","PinnedEditor");Case("CapacityBoundariesAndPendingDelta",Boundaries);Case("ActualPreModelGuardAndKeepPlaying",BeforeModel);Case("LastFreeCommandAndIndex999",LastFreeAction);Case("PaidRequestsRefusedBeforeDispatch",PaidGuards);Case("ToolRefusalRestoresAtlasAndKeepsFreeMoves",ToolRollback);Case("CommittedToolAtFullCapacityStillApplies",CommittedTool);Case("LegacyRefusalAndSingleExplicitExit",LegacyExit);Case("ConfirmedUnavailableR3AndExplicitEnd",UnavailableContinueR3);
                Need(report.unityErrors.Count==0,"ZeroUnexpectedUnityErrorLogs");
            }catch(Exception error){report.errors.Add(error is InvalidOperationException?error.Message:error.GetType().Name);}
            finally{Application.logMessageReceived-=OnLog;}
            finished=true;if(report.errors.Count==0)report.status="PASS_NATIVE_SERVER_CAPACITY86";
            string output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_CAPACITY86_OUTPUT")??"../Verification/Evidence/Review86");Directory.CreateDirectory(Path.Combine(output,"Native"));File.WriteAllText(Path.Combine(output,"Native/ServerCapacity86.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));SessionState.EraseBool(Key);EditorApplication.update-=Tick;
            if(Application.isBatchMode)EditorApplication.Exit(report.errors.Count==0?0:1);else EditorApplication.isPlaying=false;
        }
    }
}
#endif

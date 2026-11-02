#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.App.RuStore;
using HeartOfTheRain.App.ServerGameplay;
using HeartOfTheRain.App.OnlineIdentity;
using HeartOfTheRain.App.ServerVerification;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;

namespace HeartOfTheRain.Verification {
    public static class ServerGameplay83Verification {
        [Serializable] sealed class Report {
            public string status,utc,unity,scope;public int checks,cases;
            public bool actualHttp=false,androidKeystore=false,ordinaryFactorySelected=false;
            public int restoreComparisons,restoreFutureCommands,restoreContinues,restoreDifferentOrders;
            public List<string> restoreCounterexamples=new List<string>();
            public List<string> passed=new List<string>(),errors=new List<string>();
        }
        static Report report;
        static readonly string Player=new string('a',32),Attempt=new string('b',32),Command=new string('c',32),Digest=new string('d',64);
        static void Check(bool value,string label){report.checks++;if(!value)throw new InvalidOperationException(label);}
        static void Reject(Action action,string label){bool rejected=false;try{action();}catch(Exception){rejected=true;}Check(rejected,label);}
        static void Case(string name,Action action){report.cases++;try{action();report.passed.Add(name);}catch(Exception e){report.errors.Add(name+": "+e.GetType().Name+": "+e.Message);}}
        static string DirectoryFor()=>Path.GetFullPath("../.verification-cache/ServerGameplay83/Native/"+Guid.NewGuid().ToString("N"));
        static RuStoreServerWallet Wallet()=>new RuStoreServerWallet{playerId=Player,balanceScope="server_wallet",initialized=true,revision=3,coins=1250,lives=5,maxLives=5,currentLevel=1,serverUtc=100,starting=new[]{5,5,3,2},tools=new[]{3,3,3,3},activeAttempt=null};
        static RuStoreServerAttempt BoardAttempt()=>new RuStoreServerAttempt{attemptId=Attempt,state="Started",level=1,configHash=Digest,seed=uint.MaxValue,moves=20,starting=new int[4],reward=new RuStoreServerReward{coins=50,stars=1}};
        static ServerAttemptJournal Journal(string root,string origin="https://staging.invalid",string player=null)=>new ServerAttemptJournal(Path.Combine(root,"intent.json"),origin,player??Player);
        static ServerPendingCommand Pending()=>new ServerPendingCommand{operation="Continue",commandId=Command,attemptId=Attempt,expectedRevision=3,payload="{\"commandId\":\""+Command+"\",\"expectedPrefixRevision\":1,\"expectedWalletRevision\":3,\"actions\":[]}"};
        static void PendingDocument(ServerAttemptDocument value){value.hasPending=true;value.pending=Pending();value.attemptId=Attempt;}
        static string Raw(ServerBrokerOperation value){
            string json=JsonUtility.ToJson(value);
            if(value.model==null)json=json.Replace("\"model\":"+JsonUtility.ToJson(new ServerModelState()),"\"model\":null");
            if(value.wallet==null)json=json.Replace("\"wallet\":"+JsonUtility.ToJson(new RuStoreServerWallet()),"\"wallet\":null");
            if(value.attempt==null)json=json.Replace("\"attempt\":"+JsonUtility.ToJson(new RuStoreServerAttempt()),"\"attempt\":null");
            if(value.displayReceipt==null)json=json.Replace("\"displayReceipt\":"+JsonUtility.ToJson(new ServerDisplayReceipt()),"\"displayReceipt\":null");
            if(value.wallet!=null&&value.wallet.activeAttempt==null)json=json.Replace("\"activeAttempt\":"+JsonUtility.ToJson(new RuStoreServerAttempt()),"\"activeAttempt\":null");
            return json;
        }
        static ServerBrokerOperation Parse(string json,string expectedAttempt=null,string expectedCommand=null){
            using(var client=new ServerGameplayBrokerClient("http://127.0.0.1:18483",Player,()=>IdentityProtocol82.NewSecret(),r=>{},true))
                return (ServerBrokerOperation)typeof(ServerGameplayBrokerClient).GetMethod("Parse",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(client,new object[]{json,expectedAttempt??Attempt,expectedCommand??Command});
        }
        static ServerBrokerOperation Operation()=>new ServerBrokerOperation{operationId=Command,attemptId=Attempt,state="Committed",code="",paidReceiptId="",model=new ServerModelState{outcome="Playing",moves=20,turn=1,checkpointSHA256=Digest},wallet=Wallet(),attempt=BoardAttempt(),displayReceipt=null};
        static TurnResult ReplayActionOn(BoardModel board,ReplayAction action){
            if(action.kind=="Swap")return board.Swap(action.ax,action.ay,action.bx,action.by);
            if(action.kind=="Tap")return board.Tap(action.ax,action.ay);
            if(action.kind=="Continue"){board.ApplyContinue(action.receiptId,5);return null;}
            var stock=new BoosterInventory{hammer=1,axe=1,ram=1,atlas=1};return board.UseBooster((BoosterKind)action.tool,action.ax,action.ay,stock,()=>true);
        }
        static string Order(BoardModel board)=>string.Join(",",board.Pieces.Values.Select(p=>p.id));
        static bool CompareFuture(BoardModel live,LevelData level,string label){
            var restored=BoardModel.FromCheckpoint(level,live.Checkpoint());report.restoreComparisons++;
            Check(JsonUtility.ToJson(live.Checkpoint())==JsonUtility.ToJson(restored.Checkpoint()),label+" initial roundtrip");
            if(Order(live)!=Order(restored))report.restoreDifferentOrders++;
            for(int n=0;n<8&&live.Status=="Playing";n++){
                var legal=live.LegalSwaps();if(legal.Count==0)break;var move=legal[(n*7)%legal.Count];
                var expected=live.Swap(move[0].x,move[0].y,move[1].x,move[1].y);var actual=restored.Swap(move[0].x,move[0].y,move[1].x,move[1].y);report.restoreFutureCommands++;
                if(JsonUtility.ToJson(expected)!=JsonUtility.ToJson(actual)||JsonUtility.ToJson(live.Checkpoint())!=JsonUtility.ToJson(restored.Checkpoint())){
                    report.restoreCounterexamples.Add(label+" / future "+n+" / live="+ProfileJson.Hash(JsonUtility.ToJson(live.Checkpoint()))+" / restored="+ProfileJson.Hash(JsonUtility.ToJson(restored.Checkpoint())));
                    return false;
                }
            }
            return true;
        }
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("O"),unity=Application.unityVersion,scope="Native Editor core contracts: read-only projection, disk intent crash/CAS/account binding, strict replay responses and paid/fault identity. No HTTP, device, connected gameplay or production approval."};
            Case("projection_has_no_local_genesis",()=>{var p=new ServerProfileProjection();var value=p.Read();Check(value.coins==0&&value.lives==0&&value.starting[0]==0&&value.tools[0]==0,"unbound zero display");Reject(()=>p.Commit(0,PlayerProfile.New(new[]{5,5,3,2})),"local commit forbidden");});
            Case("projection_owned_read_and_replay_awards",()=>{
                var p=new ServerProfileProjection();var method=typeof(ServerProfileProjection).GetMethod("Apply",BindingFlags.Instance|BindingFlags.NonPublic);
                var attempt=new AttemptRecord{id=Attempt,config=Digest,level=1,state="Won",seed=uint.MaxValue,firstClear=false,awardedCoins=0,awardedStars=0,livesAfter=5};
                method.Invoke(p,new object[]{Wallet(),attempt});var value=p.Read();Check(value.coins==1250&&value.attempts[0].awardedCoins==0,"replay never nominal reward");value.coins=9999;value.tools[0]=99;Check(p.Read().coins==1250&&p.Read().tools[0]==3,"owned read");Reject(()=>new ProfileService(p).Win(Attempt),"legacy win cannot grant");
            });
            Case("intent_reopen_cas_and_origin_player",()=>{
                string root=DirectoryFor();var journal=Journal(root);var value=journal.Read();PendingDocument(value);value=journal.Save(value);
                var reopened=Journal(root).Read();Check(reopened.revision==1&&reopened.pending.commandId==Command&&reopened.pending.payload==Pending().payload,"exact persisted intent");
                Reject(()=>journal.Save(new ServerAttemptDocument{origin=value.origin,playerId=Player}),"stale CAS");Reject(()=>Journal(root,"https://other.invalid").Read(),"origin binding");Reject(()=>Journal(root,player:new string('e',32)).Read(),"account binding");
            });
            Case("intent_beforecommit_failure_does_not_dispatch",()=>{string root=DirectoryFor();var journal=Journal(root);var value=journal.Read();PendingDocument(value);journal.VerificationCheckpoint=stage=>{if(stage=="BeforeCommit")throw new IOException("InjectedBeforeCommit");};Reject(()=>journal.Save(value),"precommit injected");Check(!Journal(root).Read().hasPending,"no committed intent");});
            Case("intent_aftercommit_reopens_exact_id",()=>{string root=DirectoryFor();var journal=Journal(root);var value=journal.Read();PendingDocument(value);journal.VerificationCheckpoint=stage=>{if(stage=="AfterCommit")throw new IOException("InjectedAfterCommit");};Reject(()=>journal.Save(value),"postcommit injected");var reopened=Journal(root).Read();Check(reopened.hasPending&&reopened.pending.commandId==Command&&reopened.revision==1,"lost acknowledgement retains same ID");});
            Case("session_save_preserves_unsaved_delta_and_recovers_committed_revision",()=>{
                var journal=Journal(DirectoryFor());var value=journal.Save(journal.Read());value.delta.Add(new ServerMove{index=0,kind="Tap",x=1,y=2});
                var owner=new GameObject("Server save crash-cut fixture");
                try{
                    var session=owner.AddComponent<ServerGameSession>();var flags=BindingFlags.Instance|BindingFlags.NonPublic;var type=typeof(ServerGameSession);
                    type.GetField("journal",flags).SetValue(session,journal);type.GetField("document",flags).SetValue(session,value);var save=type.GetMethod("Save",flags);
                    journal.VerificationCheckpoint=stage=>{if(stage=="BeforeCommit")throw new IOException("InjectedBeforeCommit");};Reject(()=>save.Invoke(session,null),"session precommit cut");
                    var kept=(ServerAttemptDocument)type.GetField("document",flags).GetValue(session);Check(kept.delta.Count==1&&kept.revision==1&&(bool)type.GetField("journalDirty",flags).GetValue(session),"unsaved accepted prefix retained and dirty");
                    journal.VerificationCheckpoint=null;save.Invoke(session,null);Check(journal.Read().delta.Count==1&&journal.Read().revision==2,"retry saves exact accepted prefix before dispatch");
                    kept=(ServerAttemptDocument)type.GetField("document",flags).GetValue(session);kept.view="shop";
                    journal.VerificationCheckpoint=stage=>{if(stage=="AfterCommit")throw new IOException("InjectedAfterCommit");};Reject(()=>save.Invoke(session,null),"session postcommit cut");
                    var recovered=(ServerAttemptDocument)type.GetField("document",flags).GetValue(session);Check(recovered.revision==3&&recovered.view=="shop"&&!(bool)type.GetField("journalDirty",flags).GetValue(session),"new durable revision adopted after lost acknowledgement");
                    journal.VerificationCheckpoint=null;save.Invoke(session,null);Check(journal.Read().revision==4&&journal.Read().view=="shop","ack retry can progress without CAS dead end");
                }finally{UnityEngine.Object.DestroyImmediate(owner);}
            });
            Case("intent_corruption_never_promotes_backup",()=>{string root=DirectoryFor();var journal=Journal(root);var value=journal.Read();value=journal.Save(value);PendingDocument(value);journal.Save(value);File.WriteAllText(Path.Combine(root,"intent.json"),"{}",new UTF8Encoding(false));var rebuilt=Journal(root).Read();Check(!rebuilt.hasPending&&rebuilt.revision==0&&File.Exists(Path.Combine(root,"intent.json.corrupt"))&&!File.Exists(Path.Combine(root,"intent.json")),"corrupt primary is quarantined and rebuilt from the server, never from its backup");});
            Case("intent_action_cap_and_owned_copy",()=>{var journal=Journal(DirectoryFor());var value=journal.Read();value.acceptedActions=1001;Reject(()=>journal.Save(value),"global cap");value.acceptedActions=0;for(int n=0;n<129;n++)value.delta.Add(new ServerMove{index=n,kind="Tap"});Reject(()=>journal.Save(value),"delta cap");value.delta.Clear();value=journal.Save(value);value.selected[0]=1;Check(journal.Read().selected[0]==0,"save owns arrays");});
            Case("strict_pending_null_and_commit_requirements",()=>{
                string json="{\"operationId\":\""+Command+"\",\"attemptId\":\""+Attempt+"\",\"state\":\"Pending\",\"code\":\"worker_pending\",\"paidReceiptId\":\"\",\"prefixRevision\":0,\"acceptedActions\":0,\"addedMoves\":0,\"model\":null,\"wallet\":null,\"attempt\":null,\"displayReceipt\":null,\"productionEnabled\":false,\"acknowledgementRequired\":false}";
                var value=Parse(json);Check(value.model==null&&value.wallet==null&&value.attempt==null&&value.displayReceipt==null,"real nulls retained");Reject(()=>Parse(json.Replace("Pending","Committed")),"committed cannot have null model/wallet");Reject(()=>Parse(json.Replace("\"prefixRevision\":0","\"prefixRevision\":\"0\"")),"raw numeric type");Reject(()=>Parse(json.Replace("\"productionEnabled\":false","\"productionEnabled\":true")),"production flag false");
            });
            Case("strict_owner_seed_and_paid_receipt",()=>{
                var operation=Operation();operation.paidReceiptId="wallet/"+Digest;operation.addedMoves=5;var value=Parse(Raw(operation));Check(value.attempt.seed==uint.MaxValue&&value.paidReceiptId==operation.paidReceiptId,"uint seed and actual paid receipt");
                Reject(()=>Parse(Raw(operation),new string('f',32)),"attempt binding");Reject(()=>Parse(Raw(operation),expectedCommand:new string('f',32)),"operation binding");operation.wallet.playerId=new string('f',32);Reject(()=>Parse(Raw(operation)),"wallet owner binding");operation.wallet=Wallet();operation.paidReceiptId=Command;Reject(()=>Parse(Raw(operation)),"command ID is not paid receipt");
            });
            Case("trusted_fault_is_not_paid_apply",()=>{
                var operation=Operation();operation.model=null;operation.attempt.state="Released";operation.displayReceipt=new ServerDisplayReceipt{receiptId="wallet/"+Digest,outcome="Fault",livesAfter=5};var value=Parse(Raw(operation));Check(value.model==null&&value.attempt.state=="Released","trusted fault release");operation.addedMoves=5;Reject(()=>Parse(Raw(operation)),"fault cannot add moves");operation.addedMoves=0;operation.paidReceiptId="wallet/"+Digest;Reject(()=>Parse(Raw(operation)),"fault cannot issue paid permit");
            });
            Case("external_config_absence_and_invalid_closed",()=>{
                string old=Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG"),root=DirectoryFor(),path=Path.Combine(root,"configuration.json");Directory.CreateDirectory(root);
                try{Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",path);ServerGameplayConfiguration config;string error;Check(ServerGameplayConfiguration.TryRead(out config,out error)&&config==null&&error=="ExplicitServerConfigurationInvalid","missing explicit override fails closed");File.WriteAllText(path,"{}",new UTF8Encoding(false));Check(ServerGameplayConfiguration.TryRead(out config,out error)&&config==null&&error=="ExplicitServerConfigurationInvalid","present invalid config cannot fall back");File.WriteAllText(path,"{\"version\":1,\"mode\":\"ManagedGuestServer\",\"origin\":\"http://127.0.0.1:18483\",\"allowDevelopmentLoopback\":true,\"identityScope\":\"review-native-83\"}",new UTF8Encoding(false));Check(ServerGameplayConfiguration.TryRead(out config,out error)&&config!=null,"explicit config only");}
                finally{Environment.SetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_CONFIG",old);}
            });
            Case("checkpoint_restore_future_natural_commands",()=>{
                var assets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
                Check(assets&&assets.boards.levels.Length==50,"approved fifty levels");
                bool all=true;foreach(int number in new[]{1,4,8,14,26,30,31,33,40,48,50}){
                    var level=JsonUtility.FromJson<LevelData>(assets.boards.levels[number-1].text);var board=new BoardModel(level,(uint)(23017+number));
                    for(int turn=0;turn<Math.Min(4,level.movesProposal)&&board.Status=="Playing";turn++){
                        var legal=board.LegalSwaps();if(legal.Count==0)break;var move=legal[(turn*3)%legal.Count];board.Swap(move[0].x,move[0].y,move[1].x,move[1].y);
                    }
                    all=CompareFuture(board,level,"L"+number+" natural")&&all;
                }
                Check(all,"all full future natural turns match after checkpoint restore");
            });
            Case("checkpoint_restore_after_real_continue_history",()=>{
                string fixtures=Path.GetFullPath("../Verification/Evidence/ServerReplay83/Native/Fixtures");var paths=Directory.GetFiles(fixtures,"*_Continue*.job.json");Check(paths.Length>0,"real sealed natural Continue fixture exists");
                var assets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
                foreach(string path in paths){
                    var job=JsonUtility.FromJson<ReplayJob>(File.ReadAllText(path));var level=JsonUtility.FromJson<LevelData>(assets.boards.levels[job.level-1].text);var live=new BoardModel(level,job.seed);string why;
                    Check(live.TryPlaceStartingPowers(Enumerable.Range(0,4).Where(i=>job.starting[i]!=0).Select(i=>new[]{4,21,7,16}[i]).ToArray(),out why),"same starting grant");
                    BoardModel restored=null;
                    foreach(var action in job.actions){
                        if(action.kind=="Continue"){
                            restored=BoardModel.FromCheckpoint(level,live.Checkpoint());report.restoreComparisons++;report.restoreContinues++;
                            if(Order(live)!=Order(restored))report.restoreDifferentOrders++;
                        }
                        var expected=ReplayActionOn(live,action);
                        if(restored!=null){
                            var actual=ReplayActionOn(restored,action);report.restoreFutureCommands++;
                            bool same=(expected==null&&actual==null||expected!=null&&actual!=null&&JsonUtility.ToJson(expected)==JsonUtility.ToJson(actual))&&JsonUtility.ToJson(live.Checkpoint())==JsonUtility.ToJson(restored.Checkpoint());
                            if(!same)report.restoreCounterexamples.Add(Path.GetFileName(path)+" / action "+action.index+" / live="+ProfileJson.Hash(JsonUtility.ToJson(live.Checkpoint()))+" / restored="+ProfileJson.Hash(JsonUtility.ToJson(restored.Checkpoint())));
                            Check(same,"full future Continue history / "+action.index);
                        }
                    }
                }
            });
            report.status=report.errors.Count==0?"PASS_NATIVE_SERVER_GAMEPLAY83_CORE":"FAIL_NATIVE_SERVER_GAMEPLAY83_CORE";
            string output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_SERVER_GAMEPLAY_OUTPUT")??"../Verification/Evidence/ServerGameplay83");Directory.CreateDirectory(Path.Combine(output,"Native"));File.WriteAllText(Path.Combine(output,"Native","ServerGameplay.json"),JsonUtility.ToJson(report,true),new UTF8Encoding(false));
            if(report.errors.Count!=0)throw new InvalidOperationException(report.status+": "+report.errors.Count+" failed cases");
        }
    }
}
#endif

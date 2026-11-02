#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.App.Profile;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;

namespace HeartOfTheRain.Verification {
    public static class RepeatMovesVerification {
        [Serializable] sealed class Report {
            public string status,utc,error="",scope="Native Unity repeat-purchase model/profile checks and actual file-repository crash cuts. Device UI is separate.";
            public int checks,restarts,purchases;
        }
        static string Output=>Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_NO_MOVES_OUTPUT")??"../Verification/Evidence/RepeatMoves");
        static void Exhaust(BoardModel board){
            while(board.Status=="Playing"){
                var m=NoMovesDeviceProbe.SafeSwap(board);board.Swap(m[0].x,m[0].y,m[1].x,m[1].y);
            }
            if(board.Status!="Out of moves")throw new Exception("Fixture ended before exhaustion");
        }
        public static void Run(){
            var report=new Report{utc=DateTime.UtcNow.ToString("o")};
            void Check(bool ok,string label){report.checks++;if(!ok)throw new Exception(label);}
            void Throws(Action action,string label){bool threw=false;try{action();}catch(InvalidOperationException){threw=true;}Check(threw,label);}
            try{
                var assets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
                string raw=assets.boards.levels[0].text;var level=JsonUtility.FromJson<LevelData>(raw);level.movesProposal=1;
                var rules=new ContinueRules{enabled=true};Check(rules.maximumContinues==0,"Default has no configured purchase limit");
                PlayerProfile NewProfile(){var p=PlayerProfile.New(new[]{5,5,3,2});p.coins=4500;return p;}
                string Start(ProfileService p){var id=Guid.NewGuid().ToString("N");p.Reserve(id,1,ProfileJson.Hash(raw),new int[4],100,1);p.CommitStart(id);return id;}
                DevelopmentContinueService Service(ProfileService p)=>new DevelopmentContinueService(p,rules,()=>1000,_=>level,true);
                var profile=new ProfileService(new MemoryProfileRepository(NewProfile()));string attempt=Start(profile);var service=Service(profile);var board=new BoardModel(level);Exhaust(board);
                var receipts=new List<ContinueReceipt>();
                for(int ordinal=1;ordinal<=5;ordinal++){
                    service.Capture(attempt,board.Checkpoint());var before=JsonUtility.ToJson(board.Checkpoint());var quote=service.Quote(attempt);
                    Check(quote!=null&&quote.cost==900&&quote.moves==5,"Repeat offer "+ordinal);
                    if(receipts.Count>0){
                        Throws(()=>service.Prepare(attempt,receipts[0].quote),"Old quote rejected for a later exhaustion");
                        var old=service.Purchase(attempt,receipts[0].operation);Check(old.operation==receipts[0].operation&&service.Read(attempt).continuation.checkpoint==before,"Old receipt does not change current checkpoint");
                    }
                    string op=service.Prepare(attempt,quote.id);if(receipts.Count>0){service.Acknowledge(attempt,receipts[0].operation);Check(service.Read(attempt).continuation.pending==op,"Old acknowledgement cannot clear a newer command");}
                    var receipt=service.Purchase(attempt,op);report.purchases++;receipts.Add(receipt);
                    Check(receipt.outcome=="Applied"&&profile.Read().coins==4500-ordinal*900&&profile.Read().lives==5,"Repeat spend is exactly once, no life debit");
                    service.Purchase(attempt,op);Check(profile.Read().coins==4500-ordinal*900,"Duplicate callback does not spend again");
                    board.ApplyContinue(op,receipt.movesAfter);Check(JsonUtility.ToJson(board.Checkpoint())==receipt.afterCheckpoint,"Live repeat grant preserves board/RNG");
                    service.Acknowledge(attempt,op);profile.RecoverInterrupted();Check(service.Read(attempt).continuation.count==ordinal&&service.Read(attempt).state=="Started","Repeated count validates and remains restorable");
                    profile.LeaveContinueCheckpoint(attempt);Exhaust(board);
                }
                service.Capture(attempt,board.Checkpoint());var unaffordable=service.Quote(attempt);Check(unaffordable!=null&&unaffordable.balance==0,"A further offer remains available at zero coins");
                Throws(()=>service.Prepare(attempt,unaffordable.id),"Insufficient balance blocks the sixth spend");
                service.SetView(attempt,"shop");profile.RecoverInterrupted();Check(profile.Read().lives==5&&service.Read(attempt).continuation.view=="shop","Shop after repeats remains restorable without life loss");

                // Upgrade a checkpoint-68 pending command without resetting its quote,
                // attempt, balance or the previously committed move purchase.
                var upgrade=new ProfileService(new MemoryProfileRepository(NewProfile()));string oldId=Start(upgrade);var oldRules=new ContinueRules{enabled=true,maximumContinues=1,policy="NoMovesR2-Development-v1"};
                var oldService=new DevelopmentContinueService(upgrade,oldRules,()=>1000,_=>level,true);var oldBoard=new BoardModel(level);Exhaust(oldBoard);oldService.Capture(oldId,oldBoard.Checkpoint());var oldQuote=oldService.Quote(oldId);string pending=oldService.Prepare(oldId,oldQuote.id);
                var upgraded=Service(upgrade);var migrated=upgraded.Purchase(oldId,pending);upgraded.Acknowledge(oldId,pending);oldBoard.ApplyContinue(pending,migrated.movesAfter);upgrade.LeaveContinueCheckpoint(oldId);Exhaust(oldBoard);upgraded.Capture(oldId,oldBoard.Checkpoint());Check(upgraded.Quote(oldId)!=null&&upgrade.Read().coins==3600,"Checkpoint-68 pending purchase migrates and can buy again");

                foreach(int ordinal in new[]{1,2,3})foreach(string phase in new[]{"prepare","purchase","acknowledge"})foreach(string cut in new[]{"TempFlushed","Committed"}){
                    report.restarts++;string dir=Path.GetFullPath("../.verification-cache/RepeatMoves/Faults/"+Guid.NewGuid().ToString("N"));
                    var repository=new FileProfileRepository(dir,NewProfile);var p=new ProfileService(repository);string id=Start(p);var s=Service(p);var b=new BoardModel(level);Exhaust(b);
                    for(int n=1;n<ordinal;n++){s.Capture(id,b.Checkpoint());var q=s.Quote(id);string op=s.Prepare(id,q.id);var rr=s.Purchase(id,op);b.ApplyContinue(op,rr.movesAfter);s.Acknowledge(id,op);p.LeaveContinueCheckpoint(id);Exhaust(b);}
                    s.Capture(id,b.Checkpoint());var offer=s.Quote(id);string command=null;
                    if(phase!="prepare")command=s.Prepare(id,offer.id);if(phase=="acknowledge")s.Purchase(id,command);
                    bool failed=false;repository.Checkpoint=where=>{if(where==cut&&!failed){failed=true;throw new IOException("Injected repeat purchase boundary");}};
                    try{if(phase=="prepare")s.Prepare(id,offer.id);else if(phase=="purchase")s.Purchase(id,command);else s.Acknowledge(id,command);}catch(IOException){}
                    Check(failed,"Disk cut exercised");
                    p=new ProfileService(new FileProfileRepository(dir,()=>throw new Exception("Existing profile expected")));p.RecoverInterrupted();s=Service(p);var journal=s.Read(id).continuation;command=journal.pending;
                    if(string.IsNullOrEmpty(command)&&journal.phase=="Awaiting")command=s.Prepare(id,s.Quote(id).id);
                    if(!string.IsNullOrEmpty(command)){var rr=s.Purchase(id,command);Check(rr.outcome=="Applied","Pending repeat recovered");s.Acknowledge(id,command);}
                    journal=s.Read(id).continuation;Check(p.Read().coins==4500-ordinal*900&&p.Read().lives==5&&journal.count==ordinal&&JsonUtility.FromJson<BoardCheckpoint>(journal.checkpoint).board.moves==5,"No duplicate spend/grant across ordinal "+ordinal+" / "+phase+" / "+cut);
                }

                var fixtures=new List<NoMovesDeviceProbe.Fixture>();
                bool r3=Output.EndsWith("NoMovesR3",StringComparison.Ordinal);
                foreach(string name in (r3?new[]{"offer","insufficient","shop","prepared","committed","repeat","repeat_insufficient","end","zero","below","exact"}:new[]{"offer","insufficient","shop","prepared","committed","repeat","repeat_insufficient","end"})){
                    var initial=NewProfile();initial.coins=name=="insufficient"||name=="shop"?710:name=="repeat_insufficient"?2510:name=="repeat"||name=="prepared"||name=="committed"?3050:1250;
                    if(r3){if(name=="offer")initial.coins=1600;if(name=="insufficient"||name=="shop")initial.coins=700;if(name=="repeat_insufficient")initial.coins=2500;if(name=="zero")initial.coins=0;if(name=="below")initial.coins=899;if(name=="exact")initial.coins=900;}
                    var p=new ProfileService(new MemoryProfileRepository(initial));string id=Start(p);var s=Service(p);var b=new BoardModel(level,ProfileService.AttemptSeed(id));Exhaust(b);
                    int previous=name=="prepared"||name=="committed"||name=="repeat_insufficient"?2:name=="repeat"||name=="end"?1:0;
                    for(int n=0;n<previous;n++){s.Capture(id,b.Checkpoint());string op=s.Prepare(id,s.Quote(id).id);var rr=s.Purchase(id,op);s.Acknowledge(id,op);b.ApplyContinue(op,rr.movesAfter);p.LeaveContinueCheckpoint(id);Exhaust(b);}
                    s.Capture(id,b.Checkpoint());var q=s.Quote(id);
                    if(name=="shop")s.SetView(id,"shop");
                    if(name=="prepared"||name=="committed"){string op=s.Prepare(id,q.id);if(name=="committed")s.Purchase(id,op);}
                    var saved=p.Read();bool poor=name=="insufficient"||name=="shop"||name=="repeat_insufficient"||name=="zero"||name=="below";fixtures.Add(new NoMovesDeviceProbe.Fixture{scenario=name,profile=saved,checkpoint=saved.attempts.Last().continuation.checkpoint,movesAfter=poor||name=="end"?0:5,coinsAfter=poor?saved.coins:name=="offer"&&r3?700:name=="exact"?0:350,countAfter=name=="prepared"||name=="committed"||name=="repeat"?3:name=="repeat_insufficient"?2:poor?0:1});
                }
                Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"Device_Fixtures.json"),JsonUtility.ToJson(new NoMovesDeviceProbe.Fixtures{entries=fixtures.ToArray()},true));
            }catch(Exception error){report.error=error.ToString();}
            report.status=report.error==""?"PASS_NATIVE_REPEAT_MOVES":"FAIL_NATIVE_REPEAT_MOVES";Directory.CreateDirectory(Output);File.WriteAllText(Path.Combine(Output,"RepeatTransactions.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.error==""?0:1);
        }
    }
}
#endif

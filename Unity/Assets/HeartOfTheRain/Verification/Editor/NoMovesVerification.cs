#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.App.Profile;
namespace HeartOfTheRain.Verification {
    public static class NoMovesVerification {
        [Serializable] public class Report {public string status,utc,scope="Native Unity model/profile transactions, disk fault/restart recovery and resource checks. Rendering, input and Android are separate.";public int checks,boards,restarts;public List<string> errors=new List<string>();}
        static string Output=>Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_NO_MOVES_OUTPUT")??"../Verification/Evidence/NoMovesR2");
        public static void Run(){var r=new Report{utc=DateTime.UtcNow.ToString("o")};void Check(bool value,string label){r.checks++;if(!value&&r.errors.Count<80)r.errors.Add(label);}void Throws(Action call,string label){try{call();Check(false,label);}catch(Exception){Check(true,label);}}
            try{
                var assets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
                LevelData Level(int index){var v=JsonUtility.FromJson<LevelData>(assets.boards.levels[index].text);v.movesProposal=1;return v;}
                var art=Resources.Load<HeartOfTheRain.App.NoMoves.NoMovesAssets>("HOTR_NoMoves/Design");Check(art&&art.hero&&art.band&&art.primary&&art.titleFont&&art.bodyFont,"Native design bindings");Check(art.rules.enabled&&art.rules.coinCost==900&&art.rules.extraMoves==5&&art.rules.maximumContinues==0,"Owner-approved development offer");
                var rules=new ContinueRules{enabled=true};long clock=1000;
                for(int n=0;n<50;n++)foreach(int kind in new[]{-1,4,5,7,11,16,21}){
                    var level=Level(n);var board=new BoardModel(level);TurnResult turn;
                    if(kind<0){var move=board.LegalSwaps().FirstOrDefault();if(move==null)continue;turn=board.Swap(move[0].x,move[0].y,move[1].x,move[1].y);}else{var gem=board.Pieces.Values.First(p=>p.family=="gem");board.InjectReviewPower(gem.x,gem.y,kind);turn=board.Tap(gem.x,gem.y);}
                    if(board.Status!="Out of moves")continue;r.boards++;string label="L"+(n+1)+" kind "+kind;
                    var checkpoint=board.Checkpoint();string original=JsonUtility.ToJson(checkpoint);var restored=BoardModel.FromCheckpoint(level,JsonUtility.FromJson<BoardCheckpoint>(original));Check(original==JsonUtility.ToJson(restored.Checkpoint()),label+" exact checkpoint/RNG/private counters");
                    var p=PlayerProfile.New(new[]{5,5,3,2});p.completed=n;p.currentLevel=n+1;var repo=new MemoryProfileRepository(p);var profiles=new ProfileService(repo);string id=Guid.NewGuid().ToString("N");profiles.Reserve(id,n+1,"fixture",new int[4],100,1);
                    // Match the durable attempt to this exact level and board.
                    profiles.CommitStart(id);var service=new DevelopmentContinueService(profiles,rules,()=>clock,_=>level,true);service.Capture(id,checkpoint);var quote=service.Quote(id);Check(quote!=null&&quote.cost==900&&quote.moves==5,label+" bound quote");
                    string op=service.Prepare(id,quote.id);profiles.RecoverInterrupted();Check(profiles.Read().lives==5&&service.Read(id).state=="Started",label+" awaiting/pending recovery keeps life");
                    var receipt=service.Purchase(id,op);Check(receipt.outcome=="Applied"&&profiles.Read().coins==350,label+" atomic exact debit");
                    for(int repeat=0;repeat<3;repeat++)service.Purchase(id,op);Check(profiles.Read().coins==350&&service.Read(id).continuation.count==1,label+" duplicate receipt does not debit again");
                    board.ApplyContinue(op,receipt.movesAfter);board.ApplyContinue(op,receipt.movesAfter);Check(board.Moves==5&&board.Status=="Playing",label+" absolute move application");
                    var after=board.Checkpoint();Check(after.random==checkpoint.random&&after.nextId==checkpoint.nextId&&after.quietMoves==checkpoint.quietMoves&&after.growthUsed==checkpoint.growthUsed&&JsonUtility.ToJson(new BoardSnapshot{pieces=after.board.pieces,goals=after.board.goals})==JsonUtility.ToJson(new BoardSnapshot{pieces=checkpoint.board.pieces,goals=checkpoint.board.goals}),label+" same pieces/goals/RNG");
                    Check(JsonUtility.ToJson(after)==receipt.afterCheckpoint,label+" receipt checkpoint matches live board");
                    service.Acknowledge(id,op);profiles.RecoverInterrupted();Check(profiles.Read().lives==5&&service.Read(id).state=="Started",label+" committed unused moves recover without a life");
                    var same=BoardModel.FromCheckpoint(level,after);var a=board.LegalSwaps().FirstOrDefault();if(a!=null){var next=board.Swap(a[0].x,a[0].y,a[1].x,a[1].y);var other=same.Swap(a[0].x,a[0].y,a[1].x,a[1].y);Check(JsonUtility.ToJson(next)==JsonUtility.ToJson(other),label+" next resolution and refill RNG identical");board.ApplyContinue(op,receipt.movesAfter);Check(board.Moves==same.Moves,label+" stale receipt cannot replenish later turns");}
                    profiles.LeaveContinueCheckpoint(id);profiles.RecoverInterrupted();profiles.RecoverInterrupted();Check(profiles.Read().lives==4&&service.Read(id).state=="Interrupted",label+" ordinary gameplay interruption settles once");
                }
                void Scenario(Action<ProfileService,DevelopmentContinueService,BoardModel,string> inspect,int coins=1250){var level=Level(0);var b=new BoardModel(level);var m=b.LegalSwaps().First();b.Swap(m[0].x,m[0].y,m[1].x,m[1].y);var p=PlayerProfile.New(new[]{5,5,3,2});p.coins=coins;var profile=new ProfileService(new MemoryProfileRepository(p));string id=Guid.NewGuid().ToString("N");profile.Reserve(id,1,"fixture",new int[4],100,1);profile.CommitStart(id);var s=new DevelopmentContinueService(profile,rules,()=>clock,_=>level,true);s.Capture(id,b.Checkpoint());inspect(profile,s,b,id);}
                Scenario((p,s,b,id)=>{var q=s.Quote(id);var op=s.Prepare(id,q.id);Throws(()=>p.Lose(id),"Cannot settle a pending spend");p.Change(x=>{x.coins=899;return true;});var rr=s.Purchase(id,op);Check(rr.outcome=="InsufficientCoins"&&p.Read().coins==899&&b.Moves==0,"Concurrent wallet debit refuses moves without overspending");s.Acknowledge(id,op);s.SetView(id,"shop");p.RecoverInterrupted();Check(p.Read().lives==5&&s.Read(id).continuation.view=="shop","Shop/reopening preserves attempt and life");p.Lose(id);p.Lose(id);Check(p.Read().lives==4,"Confirmed end settles once");});
                Scenario((p,s,b,id)=>{var q=s.Quote(id);Throws(()=>s.Prepare(id,q.id),"Insufficient balance does not prepare spend");Check(p.Read().coins==899&&string.IsNullOrEmpty(s.Read(id).continuation.pending),"No pending command for insufficient coins");},899);
                Scenario((p,s,b,id)=>{s=new DevelopmentContinueService(p,new ContinueRules{enabled=true,maximumContinues=1},()=>clock,_=>b.Level,true);var q=s.Quote(id);var op=s.Prepare(id,q.id);var rr=s.Purchase(id,op);Check(p.Read().coins==0&&rr.outcome=="Applied","Exact balance accepted");s.Acknowledge(id,op);p.LeaveContinueCheckpoint(id);var v=BoardModel.FromCheckpoint(b.Level,JsonUtility.FromJson<BoardCheckpoint>(rr.afterCheckpoint));while(v.Status=="Playing"){var move=v.LegalSwaps().FirstOrDefault();if(move==null)break;v.Swap(move[0].x,move[0].y,move[1].x,move[1].y);}if(v.Status=="Out of moves"){s.Capture(id,v.Checkpoint());Check(s.Quote(id)==null,"Explicit finite test policy still limits purchases");}},900);
                Scenario((p,s,b,id)=>{var q=s.Quote(id);var op=s.Prepare(id,q.id);clock+=301;var rr=s.Purchase(id,op);Check(rr.outcome=="StaleQuote"&&p.Read().coins==1250,"Expired quote never debits");s.Acknowledge(id,op);Check(s.Quote(id).id!=q.id,"Expiry requires refreshed quote");clock=1000;});
                foreach(string phase in new[]{"prepare","purchase","acknowledge"})foreach(string cut in new[]{"TempFlushed","Committed"}){
                    r.restarts++;var level=Level(0);var b=new BoardModel(level);var m=b.LegalSwaps().First();b.Swap(m[0].x,m[0].y,m[1].x,m[1].y);string dir=Path.GetFullPath("../.verification-cache/NoMovesR2/Faults/"+Guid.NewGuid().ToString("N"));
                    var repo=new FileProfileRepository(dir,()=>PlayerProfile.New(new[]{5,5,3,2}));var profiles=new ProfileService(repo);string id=Guid.NewGuid().ToString("N");profiles.Reserve(id,1,"fixture",new int[4],100,1);profiles.CommitStart(id);var s=new DevelopmentContinueService(profiles,rules,()=>clock,_=>level,true);s.Capture(id,b.Checkpoint());var q=s.Quote(id);string op=null;
                    if(phase!="prepare")op=s.Prepare(id,q.id);if(phase=="acknowledge")s.Purchase(id,op);
                    bool failed=false;repo.Checkpoint=where=>{if(where==cut&&!failed){failed=true;throw new IOException("Injected durable boundary");}};
                    try{if(phase=="prepare")s.Prepare(id,q.id);else if(phase=="purchase")s.Purchase(id,op);else s.Acknowledge(id,op);}catch(IOException){}
                    Check(failed,"Exercised disk cut "+phase+" "+cut);
                    profiles=new ProfileService(new FileProfileRepository(dir,()=>throw new Exception("Must recover existing save")));profiles.RecoverInterrupted();s=new DevelopmentContinueService(profiles,rules,()=>clock,_=>level,true);var saved=s.Read(id);Check(profiles.Read().lives==5&&saved.state=="Started","Disk restart preserves pending attempt "+phase+" "+cut);
                    op=saved.continuation.pending;if(string.IsNullOrEmpty(op)&&saved.continuation.phase=="Awaiting")op=s.Prepare(id,s.Quote(id).id);
                    if(!string.IsNullOrEmpty(op)){var rr=s.Purchase(id,op);Check(rr.outcome=="Applied","Recovered original spend "+phase+" "+cut);s.Acknowledge(id,op);}
                    saved=s.Read(id);Check(profiles.Read().coins==350&&saved.continuation.count==1&&JsonUtility.FromJson<BoardCheckpoint>(saved.continuation.checkpoint).board.moves==5,"Exactly once across disk cut "+phase+" "+cut);
                }
                var old=JsonUtility.ToJson(PlayerProfile.New(new[]{5,5,3,2}));Check(JsonUtility.FromJson<PlayerProfile>(old).schemaVersion==1,"Profile schema remains compatible");
                var fixtures=new List<NoMovesDeviceProbe.Fixture>();
                foreach(string scenario in new[]{"offer","insufficient","shop","prepared","committed","limit"}){
                    string rawLevel=assets.boards.levels[0].text;var data=JsonUtility.FromJson<LevelData>(rawLevel);data.movesProposal=1;
                    var p=PlayerProfile.New(new[]{5,5,3,2});p.coins=scenario=="insufficient"||scenario=="shop"?710:1250;var profiles=new ProfileService(new MemoryProfileRepository(p));string id=Guid.NewGuid().ToString("N");profiles.Reserve(id,1,ProfileJson.Hash(rawLevel),new int[4],100,1);profiles.CommitStart(id);
                    var board=new BoardModel(data,ProfileService.AttemptSeed(id));var move=board.LegalSwaps().First();board.Swap(move[0].x,move[0].y,move[1].x,move[1].y);var s=new DevelopmentContinueService(profiles,rules,()=>1000,_=>data,true);s.Capture(id,board.Checkpoint());var q=s.Quote(id);
                    if(scenario=="shop")s.SetView(id,"shop");
                    if(scenario=="prepared"||scenario=="committed"||scenario=="limit"){
                        string op=s.Prepare(id,q.id);if(scenario!="prepared"){
                            var receipt=s.Purchase(id,op);
                            if(scenario=="limit"){s.Acknowledge(id,op);profiles.LeaveContinueCheckpoint(id);var c=JsonUtility.FromJson<BoardCheckpoint>(receipt.afterCheckpoint);c.board.moves=1;board=BoardModel.FromCheckpoint(data,c);move=board.LegalSwaps().First();board.Swap(move[0].x,move[0].y,move[1].x,move[1].y);s.Capture(id,board.Checkpoint());}
                        }
                    }
                    var saved=profiles.Read();fixtures.Add(new NoMovesDeviceProbe.Fixture{scenario=scenario,profile=saved,checkpoint=saved.attempts.Last().continuation.checkpoint,movesAfter=scenario=="insufficient"||scenario=="shop"||scenario=="limit"?0:5,coinsAfter=scenario=="insufficient"||scenario=="shop"?710:350});
                }
                File.WriteAllText(Path.Combine(Output,"Device_Fixtures.json"),JsonUtility.ToJson(new NoMovesDeviceProbe.Fixtures{entries=fixtures.ToArray()},true));
            }catch(Exception e){r.errors.Add(e.ToString());}
            r.status=r.errors.Count==0?"PASS_NO_MOVES_TRANSACTIONS":"FAIL_NO_MOVES_TRANSACTIONS";var output=Output;Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"Transactions.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(r.errors.Count==0?0:1);
        }
    }
}
#endif

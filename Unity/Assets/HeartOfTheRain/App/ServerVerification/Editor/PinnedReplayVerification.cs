#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;

namespace HeartOfTheRain.App.ServerVerification.Editor {
    public static class PinnedReplayVerification {
        [Serializable] sealed class Case {public string name,job,jobSHA256,expected,checkpointSHA256,outcome;public int actions,continues,tools,starting;}
        [Serializable] sealed class Report {public string status="FAIL",utc,unity,pinsSHA256,error="",scope="Pinned native actual M46/M48 model versus shared worker engine; no deployed gateway, real player submission, bank payment or production activation.";public int checks,cases,levels,actions,tools,continues,fullCheckpointComparisons,restoreRoundTrips,negativeControls;public List<Case> fixtures=new List<Case>();public bool productionEnabled=false;}
        static Report report;static string directory,pinsDirectory,pinsHash;static ReplayPins pins;
        static void Check(bool value,string reason){report.checks++;if(!value)throw new InvalidOperationException(reason);}
        static string Id()=>Guid.NewGuid().ToString("N");
        static string Receipt()=>"wallet/"+PinnedReplayEngine.SHA(Id());
        static ReplayJob Job(int level,int variant=0)=>new ReplayJob{version=1,jobId=Id(),playerId=Id(),attemptId=Id(),pinsSHA256=pinsHash,levelSHA256=pins.levels[level-1].sha256,level=level,initialMoves=pins.levels[level-1].moves,seed=(uint)(982451653+level*31+variant),startReceiptId=Receipt(),starting=new int[4],actions=new ReplayAction[0],receipts=new ReplayReceipt[0]};
        static BoardModel Board(ReplayJob job){var board=new BoardModel(PinnedReplayEngine.Level(pinsDirectory,pins.levels[job.level-1]),job.seed);string error;var kinds=new[]{4,21,7,16};Check(board.TryPlaceStartingPowers(Enumerable.Range(0,4).Where(i=>job.starting[i]!=0).Select(i=>kinds[i]).ToArray(),out error),"Native starting grant rejected");return board;}
        static ReplayAction Move(BoardModel board,int index,int choice=0){var power=board.Pieces.Values.Where(p=>p.family=="power").OrderBy(p=>p.id).FirstOrDefault();if(power!=null)return new ReplayAction{index=index,kind="Tap",ax=power.x,ay=power.y,bx=-1,by=-1,tool=-1,movesAfter=0,receiptId=""};var legal=board.LegalSwaps();Check(legal.Count>0,"No native legal action");var cells=legal[choice%legal.Count];return new ReplayAction{index=index,kind="Swap",ax=cells[0].x,ay=cells[0].y,bx=cells[1].x,by=cells[1].y,tool=-1,movesAfter=0,receiptId=""};}
        static void Apply(BoardModel board,ReplayAction action){TurnResult result=null;switch(action.kind){case "Swap":result=board.Swap(action.ax,action.ay,action.bx,action.by);break;case "Tap":result=board.Tap(action.ax,action.ay);break;case "Tool":var stock=new BoosterInventory{hammer=0,axe=0,ram=0,atlas=0};switch(action.tool){case 0:stock.hammer=1;break;case 1:stock.axe=1;break;case 2:stock.ram=1;break;default:stock.atlas=1;break;}result=board.UseBooster((BoosterKind)action.tool,action.ax,action.ay,stock,()=>true);Check(stock.Count((BoosterKind)action.tool)==0,"Native tool not spent once");break;case "Continue":board.ApplyContinue(action.receiptId,action.movesAfter);break;default:throw new InvalidOperationException();}if(result!=null)Check(result.accepted,"Native command rejected");}
        static void AddReceipt(ReplayJob job,ReplayAction action,List<ReplayReceipt> receipts){action.receiptId=Receipt();receipts.Add(new ReplayReceipt{receiptId=action.receiptId,attemptId=job.attemptId,kind=action.kind,actionIndex=action.index,tool=action.tool,coins=action.kind=="Continue"?900:0,quantity=action.kind=="Tool"?1:0,movesAfter=action.movesAfter});}
        static void Verify(string name,ReplayJob job){
            string json=JsonUtility.ToJson(job);var parsed=PinnedReplayEngine.ParseJob(json);string hash=PinnedReplayEngine.SHA(json);var direct=Board(job);var states=new List<string>();
            foreach(var action in job.actions){Apply(direct,action);string state=JsonUtility.ToJson(direct.Checkpoint());states.Add(state);var restored=BoardModel.FromCheckpoint(PinnedReplayEngine.Level(pinsDirectory,pins.levels[job.level-1]),direct.Checkpoint());Check(JsonUtility.ToJson(restored.Checkpoint())==state,"Full checkpoint restore roundtrip");report.restoreRoundTrips++;}
            var actual=PinnedReplayEngine.Execute(parsed,PinnedReplayEngine.Level(pinsDirectory,pins.levels[job.level-1]),pins.levels[job.level-1],pinsHash,hash,true);
            Check(actual.output.status=="PASS_PINNED_MODEL_REPLAY"&&actual.output.jobSHA256==hash,"Worker engine status/job binding");Check(actual.checkpointJSON.Length==states.Count,"Checkpoint action count");for(int i=0;i<states.Count;i++){Check(actual.checkpointJSON[i]==states[i],"Full native/engine checkpoint mismatch: "+name+"/"+i);report.fullCheckpointComparisons++;}
            Check(JsonUtility.ToJson(actual.checkpoint)==JsonUtility.ToJson(direct.Checkpoint()),"Final full model checkpoint");Check(actual.output.checkpointSHA256==PinnedReplayEngine.SHA(JsonUtility.ToJson(direct.Checkpoint())),"Final checkpoint SHA256");
            string jobPath="Fixtures/"+name+".job.json",expected="Fixtures/"+name+".expected.json";File.WriteAllText(Path.Combine(directory,jobPath),json,new System.Text.UTF8Encoding(false));File.WriteAllText(Path.Combine(directory,expected),JsonUtility.ToJson(actual.output),new System.Text.UTF8Encoding(false));int tools=job.actions.Count(a=>a.kind=="Tool"),continues=job.actions.Count(a=>a.kind=="Continue");report.fixtures.Add(new Case{name=name,job=jobPath,jobSHA256=hash,expected=expected,checkpointSHA256=actual.output.checkpointSHA256,outcome=actual.output.outcome,actions=job.actions.Length,tools=tools,continues=continues,starting=job.starting.Sum()});report.cases++;report.actions+=job.actions.Length;report.tools+=tools;report.continues+=continues;
        }
        static void Negative(Action action,string name){bool failed=false;try{action();}catch(ReplayRejected){failed=true;}Check(failed,"Negative control accepted: "+name);report.negativeControls++;}
        public static void Run(){
            report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};directory=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REPLAY_OUTPUT")??"../Verification/Evidence/ServerReplay83/Native");Directory.CreateDirectory(Path.Combine(directory,"Fixtures"));pinsDirectory=Path.Combine(Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_REPLAY_PROJECT")??"../.verification-cache/PinnedReplay83/Project"),"ReplayPins");
            try{
                Check(Application.unityVersion=="2022.3.62f3","Wrong pinned Unity");pins=PinnedReplayEngine.ReadPins(pinsDirectory,out pinsHash);report.pinsSHA256=pinsHash;
                for(int level=1;level<=50;level++){
                    // Seven independent source-bound commands per authored board.
                    for(int choice=0;choice<7;choice++){var job=Job(level,choice);if(choice==6)job.starting=new[]{1,1,1,1};var board=Board(job);job.actions=new[]{Move(board,0,choice)};Verify("L"+level.ToString("00")+"_"+choice,job);}report.levels++;
                }
                foreach(int level in new[]{1,14,31,33,50})for(int tool=0;tool<4;tool++){
                    var job=Job(level,100+tool);var board=Board(job);var cell=board.Pieces.Values.Where(p=>p.family!="pail").OrderBy(p=>p.y).ThenBy(p=>p.x).First();var action=new ReplayAction{index=0,kind="Tool",ax=tool==3?-1:cell.x,ay=tool==3?-1:cell.y,bx=-1,by=-1,tool=tool,movesAfter=0};var receipts=new List<ReplayReceipt>();AddReceipt(job,action,receipts);job.actions=new[]{action};job.receipts=receipts.ToArray();Verify("L"+level.ToString("00")+"_Tool"+tool,job);
                }
                bool continued=false;
                for(int level=1;level<=50&&!continued;level++){
                    var job=Job(level,500);var board=Board(job);var actions=new List<ReplayAction>();var receipts=new List<ReplayReceipt>();int count=0;
                    while(board.Status=="Playing"&&actions.Count<200){var action=Move(board,actions.Count);Apply(board,action);actions.Add(action);}
                    if(board.Status!="Out of moves")continue;
                    while(count<2&&board.Status=="Out of moves"){
                        var action=new ReplayAction{index=actions.Count,kind="Continue",ax=-1,ay=-1,bx=-1,by=-1,tool=-1,movesAfter=5};AddReceipt(job,action,receipts);Apply(board,action);actions.Add(action);count++;
                        while(board.Status=="Playing"&&actions.Count<300){var move=Move(board,actions.Count);Apply(board,move);actions.Add(move);}
                    }
                    Check(count>0,"No continue tested");job.actions=actions.ToArray();job.receipts=receipts.ToArray();Verify("L"+level.ToString("00")+"_Continue"+count,job);continued=true;
                }
                Check(continued&&report.continues>0,"No authored natural out-of-moves continuation found");
                var valid=Job(1);string encoded=JsonUtility.ToJson(valid);Negative(()=>PinnedReplayEngine.ParseJob(encoded.Insert(1,"\"version\":1,")),"duplicate root key");Negative(()=>PinnedReplayEngine.ParseJob(encoded.Insert(1,"\"expectedWon\":true,")),"client win claim");Negative(()=>PinnedReplayEngine.ParseJob(encoded.Replace("\"seed\":"+valid.seed,"\"seed\":true")),"wrong scalar type");
                valid.initialMoves++;Negative(()=>PinnedReplayEngine.Execute(valid,PinnedReplayEngine.Level(pinsDirectory,pins.levels[0]),pins.levels[0],pinsHash,PinnedReplayEngine.SHA("fixture")),"move budget override");valid=Job(1);valid.starting[0]=2;Negative(()=>PinnedReplayEngine.Execute(valid,PinnedReplayEngine.Level(pinsDirectory,pins.levels[0]),pins.levels[0],pinsHash,PinnedReplayEngine.SHA("fixture")),"starting override");
                var missing=Job(1);missing.actions=new[]{new ReplayAction{index=0,kind="Tool",ax=0,ay=0,bx=-1,by=-1,tool=0,movesAfter=0,receiptId=Receipt()}};Negative(()=>PinnedReplayEngine.Execute(missing,PinnedReplayEngine.Level(pinsDirectory,pins.levels[0]),pins.levels[0],pinsHash,PinnedReplayEngine.SHA("fixture")),"uncommitted tool");
                report.status="PASS_PINNED_NATIVE_REPLAY_CORPUS";
            }catch(Exception error){report.error=error.ToString();}
            File.WriteAllText(Path.Combine(directory,"ReplayNative.json"),JsonUtility.ToJson(report,true));if(report.status.StartsWith("FAIL",StringComparison.Ordinal))EditorApplication.Exit(1);
        }
    }
}
#endif

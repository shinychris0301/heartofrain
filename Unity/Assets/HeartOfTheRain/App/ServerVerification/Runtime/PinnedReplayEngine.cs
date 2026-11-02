using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;
using HeartOfTheRain.M46;

namespace HeartOfTheRain.App.ServerVerification {
    public static class PinnedReplayEngine {
        public const int MaximumJobBytes=1048576,MaximumActions=1000;
        static bool Id(string s)=>s!=null&&Regex.IsMatch(s,"\\A[0-9a-f]{32}\\z");
        static bool Hash(string s)=>s!=null&&Regex.IsMatch(s,"\\A[0-9a-f]{64}\\z");
        static bool Receipt(string s)=>s!=null&&Regex.IsMatch(s,"\\Awallet/[0-9a-f]{64}\\z");
        public static string SHA(byte[] value){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(value)).Replace("-","").ToLowerInvariant();}
        public static string SHA(string value)=>SHA(new UTF8Encoding(false,true).GetBytes(value));
        public static string ReadBounded(string path,int maximum){using(var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)){if(file.Length<2||file.Length>maximum)throw new ReplayRejected("input_size");var bytes=new byte[(int)file.Length];int offset=0;while(offset<bytes.Length){int count=file.Read(bytes,offset,bytes.Length-offset);if(count==0)throw new ReplayRejected("input_size");offset+=count;}return new UTF8Encoding(false,true).GetString(bytes);}}
        public static ReplayJob ParseJob(string json){if(json==null||Encoding.UTF8.GetByteCount(json)>MaximumJobBytes)throw new ReplayRejected("input_size");ReplayStrictJson.ValidateJob(json);return JsonUtility.FromJson<ReplayJob>(json);}
        public static ReplayPins ReadPins(string directory,out string hash){
            string json=ReadBounded(Path.Combine(directory,"manifest.json"),MaximumJobBytes);hash=SHA(json);var pins=JsonUtility.FromJson<ReplayPins>(json);
            if(pins==null||pins.version!=1||pins.unity!="2022.3.62f3"||pins.levels==null||pins.levels.Length!=50||pins.sources==null||pins.sources.Length<11)throw new ReplayRejected("invalid_pins");
            for(int i=0;i<50;i++){var p=pins.levels[i];if(p==null||p.level!=i+1||p.id!="C01_L"+(i+1).ToString("000")||p.path!="Levels/"+p.id+".json"||!Hash(p.sha256)||p.moves<1||p.moves>1000)throw new ReplayRejected("invalid_pins");}
            return pins;
        }
        public static LevelData Level(string directory,ReplayLevelPin pin){string json=ReadBounded(Path.Combine(directory,pin.path.Replace('/',Path.DirectorySeparatorChar)),MaximumJobBytes);if(SHA(json)!=pin.sha256)throw new ReplayRejected("level_hash_mismatch");var level=JsonUtility.FromJson<LevelData>(json);if(level==null||level.id!=pin.id||level.globalLevel!=pin.level||level.movesProposal!=pin.moves||level.columns!=pin.columns||level.rows!=pin.rows||level.tileSeed!=pin.tileSeed)throw new ReplayRejected("level_pin_mismatch");return level;}
        static void Require(bool condition,string code){if(!condition)throw new ReplayRejected(code);}
        public static ReplayExecution Execute(ReplayJob job,LevelData level,ReplayLevelPin pin,string pinsHash,string jobHash,bool captureCheckpoints=false){
            Require(Application.unityVersion=="2022.3.62f3","wrong_unity");
            Require(job!=null&&job.version==1&&Id(job.jobId)&&Id(job.playerId)&&Id(job.attemptId)&&Receipt(job.startReceiptId),"invalid_job_binding");
            Require(Hash(pinsHash)&&job.pinsSHA256==pinsHash&&job.levelSHA256==pin.sha256&&job.level==pin.level&&job.initialMoves==pin.moves&&job.seed!=0,"job_pin_mismatch");
            Require(job.starting!=null&&job.starting.Length==4&&job.starting.All(n=>n==0||n==1)&&job.actions!=null&&job.actions.Length<=MaximumActions&&job.receipts!=null&&job.receipts.Length<=MaximumActions,"invalid_job_bounds");
            // Deep-copy the trusted authored definition. A verifier never
            // accepts a client's board/checkpoint, modified mask or move limit.
            level=JsonUtility.FromJson<LevelData>(JsonUtility.ToJson(level));
            Require(level.id==pin.id&&level.globalLevel==pin.level&&level.movesProposal==pin.moves,"level_pin_mismatch");
            var receipts=new Dictionary<string,ReplayReceipt>(StringComparer.Ordinal);foreach(var r in job.receipts){Require(r!=null&&Receipt(r.receiptId)&&r.receiptId!=job.startReceiptId&&r.attemptId==job.attemptId&&r.actionIndex>=0&&r.actionIndex<job.actions.Length&&!receipts.ContainsKey(r.receiptId),"invalid_receipt_binding");receipts.Add(r.receiptId,r);}
            var board=new BoardModel(level,job.seed);string error;var kinds=new[]{4,21,7,16};Require(board.TryPlaceStartingPowers(Enumerable.Range(0,4).Where(i=>job.starting[i]!=0).Select(i=>kinds[i]).ToArray(),out error),"starting_rejected");
            var outputs=new List<ReplayActionResult>();var states=captureCheckpoints?new List<string>():null;var used=new HashSet<string>(StringComparer.Ordinal);var clock=Stopwatch.StartNew();
            foreach(var a in job.actions){
                Require(clock.Elapsed.TotalSeconds<=30,"replay_cpu_budget");Require(a!=null&&a.index==outputs.Count,"action_order");TurnResult result=null;
                if(a.kind=="Swap"||a.kind=="Tap"){
                    Require(a.receiptId==""&&a.tool==-1&&a.movesAfter==0,"unexpected_receipt");
                    if(a.kind=="Swap")result=board.Swap(a.ax,a.ay,a.bx,a.by);
                    else{Require(a.bx==-1&&a.by==-1,"invalid_coordinates");result=board.Tap(a.ax,a.ay);}
                }else{
                    ReplayReceipt receipt;Require(Receipt(a.receiptId)&&receipts.TryGetValue(a.receiptId,out receipt),"missing_server_receipt");receipt=receipts[a.receiptId];Require(used.Add(receipt.receiptId)&&receipt.actionIndex==a.index&&receipt.kind==a.kind,"receipt_reuse_or_kind");
                    if(a.kind=="Tool"){
                        Require(a.tool>=0&&a.tool<4&&a.bx==-1&&a.by==-1&&a.movesAfter==0&&receipt.tool==a.tool&&receipt.coins==0&&receipt.quantity==1&&receipt.movesAfter==0,"invalid_tool_receipt");
                        var stock=new BoosterInventory{hammer=0,axe=0,ram=0,atlas=0};switch(a.tool){case 0:stock.hammer=1;break;case 1:stock.axe=1;break;case 2:stock.ram=1;break;case 3:stock.atlas=1;break;}
                        result=board.UseBooster((BoosterKind)a.tool,a.ax,a.ay,stock,()=>true);Require(stock.Count((BoosterKind)a.tool)==(result.accepted?0:1),"tool_accounting");
                    }else if(a.kind=="Continue"){
                        Require(a.ax==-1&&a.ay==-1&&a.bx==-1&&a.by==-1&&a.tool==-1&&a.movesAfter==5&&receipt.tool==-1&&receipt.coins==900&&receipt.quantity==0&&receipt.movesAfter==5,"invalid_continue_receipt");board.ApplyContinue(a.receiptId,receipt.movesAfter);
                    }else throw new ReplayRejected("unknown_action");
                }
                if(result!=null)Require(result.accepted,"model_action_rejected");
                Require(board.Status!="Resolution limit"&&board.Status!="Engine fault","model_fault");board.Validate();string state=JsonUtility.ToJson(board.Checkpoint());states?.Add(state);outputs.Add(new ReplayActionResult{index=a.index,kind=a.kind,status=board.Status,moves=board.Moves,turn=board.Turn,checkpointSHA256=SHA(state)});
            }
            Require(used.Count==receipts.Count,"unused_server_receipt");Require(clock.Elapsed.TotalSeconds<=30,"replay_cpu_budget");var checkpoint=board.Checkpoint();string final=JsonUtility.ToJson(checkpoint);
            return new ReplayExecution{checkpoint=checkpoint,checkpointJSON=states?.ToArray(),output=new ReplayOutput{status="PASS_PINNED_MODEL_REPLAY",code="",unity=Application.unityVersion,jobSHA256=jobHash,pinsSHA256=pinsHash,levelSHA256=pin.sha256,level=pin.level,actions=outputs.Count,moves=board.Moves,turn=board.Turn,outcome=board.Status,remainingGoals=board.Goals.Values.Sum(),checkpointSHA256=SHA(final),actionResults=outputs.ToArray()}};
        }
    }
}

using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using HeartOfTheRain.M46;
namespace HeartOfTheRain.App.Profile {
    [Serializable] public sealed class ContinueRules {
        public bool enabled;public int coinCost=900,extraMoves=5,maximumContinues=0,quoteSeconds=300;public string policy="NoMovesR2-Repeat-Development-v2";
        // Zero means no configured purchase limit; each quote still costs coins.
        public bool Allows(int count)=>maximumContinues==0||count<maximumContinues;
        public void Validate(){if(coinCost<1||extraMoves<1||extraMoves>99||maximumContinues<0||quoteSeconds<30||quoteSeconds>3600||string.IsNullOrEmpty(policy))throw new InvalidOperationException("Invalid continue policy");}
    }
    [Serializable] public sealed class ContinueReceipt {
        public string operation,attempt,quote,outcome,beforeHash,afterCheckpoint;public int cost,movesAfter,coinsAfter;
    }
    [Serializable] public sealed class ContinueJournal {
        public string phase="",checkpoint="",view="offer",quote="",policy="",pending="",pendingQuote="";
        public long expires;public int count,coinCost,extraMoves;public List<ContinueReceipt> receipts=new List<ContinueReceipt>();
        public static bool Restorable(AttemptRecord a)=>a.continuation!=null&&(a.continuation.phase=="Awaiting"||a.continuation.phase=="Purchased")&&!string.IsNullOrEmpty(a.continuation.checkpoint);
        public static void Validate(AttemptRecord a){
            if(a.continuation==null)a.continuation=new ContinueJournal();var j=a.continuation;
            j.phase=j.phase??"";j.view=string.IsNullOrEmpty(j.view)?"offer":j.view;
            if(j.receipts==null)j.receipts=new List<ContinueReceipt>();
            if(j.count<0||j.expires<0||j.receipts.Count>1024||j.coinCost<0||j.extraMoves<0||(j.checkpoint??"").Length>1000000||(j.phase!=""&&j.phase!="Awaiting"&&j.phase!="Purchased")||(j.view!="offer"&&j.view!="shop"))throw new InvalidOperationException("Invalid continue journal");
            if(j.phase!=""&&string.IsNullOrEmpty(j.checkpoint))throw new InvalidOperationException("Missing continue board");
            if(!string.IsNullOrEmpty(j.pending)&&string.IsNullOrEmpty(j.pendingQuote))throw new InvalidOperationException("Missing pending quote");
            var ids=new HashSet<string>();foreach(var r in j.receipts)if(r==null||string.IsNullOrEmpty(r.operation)||!ids.Add(r.operation)||r.attempt!=a.id||string.IsNullOrEmpty(r.quote)||(r.outcome!="Applied"&&r.outcome!="InsufficientCoins"&&r.outcome!="StaleQuote"&&r.outcome!="Unavailable")||r.cost<0||r.coinsAfter<0||r.movesAfter<0||(r.outcome=="Applied"&&(r.cost==0||r.movesAfter<1||string.IsNullOrEmpty(r.afterCheckpoint))))throw new InvalidOperationException("Invalid continue receipt");
        }
    }
    public sealed class ContinueOffer {
        public string id,attempt,policy;public int cost,moves,balance;public long expires;
    }
    // Local development authority, sharing the SAME atomic profile commit as
    // every wallet writer. This is not a remote trusted wallet or IAP validator.
    public sealed class DevelopmentContinueService {
        readonly ProfileService profiles;readonly ContinueRules rules;readonly Func<long> now;readonly Func<int,LevelData> level;readonly Func<AttemptRecord,LevelData> attemptLevel;readonly bool enabled;
        public DevelopmentContinueService(ProfileService profile,ContinueRules rules,Func<long> clock,Func<int,LevelData> level,bool enabled,Func<AttemptRecord,LevelData> attemptLevel=null){this.profiles=profile;this.rules=JsonUtility.FromJson<ContinueRules>(JsonUtility.ToJson(rules));this.rules.Validate();now=clock;this.level=level;this.attemptLevel=attemptLevel;this.enabled=enabled&&rules.enabled;}
        LevelData LevelFor(AttemptRecord attempt)=>attemptLevel!=null?attemptLevel(attempt):level(attempt.level);
        static AttemptRecord Find(PlayerProfile p,string id)=>p.attempts.First(a=>a.id==id);
        public AttemptRecord Read(string id)=>Find(profiles.Read(),id);
        public void Capture(string id,BoardCheckpoint board){
            if(board.board.status!="Out of moves"||board.board.moves!=0||board.board.goals.All(g=>g.count==0))throw new InvalidOperationException("The board has not exhausted its moves");
            string json=JsonUtility.ToJson(board);profiles.Change(p=>{var a=Find(p,id);if(a.state!="Started")throw new InvalidOperationException("Attempt ended");var j=a.continuation;
                if(j.phase=="Awaiting"){if(j.checkpoint!=json)throw new InvalidOperationException("Continue board changed");return false;}
                if(j.phase=="Purchased"||!string.IsNullOrEmpty(j.pending))throw new InvalidOperationException("Continue requires reconciliation");
                var restored=BoardModel.FromCheckpoint(LevelFor(a),board);restored.Validate();j.phase="Awaiting";j.checkpoint=json;j.view="offer";j.quote="";return true;});
        }
        public ContinueOffer Quote(string id){
            return profiles.Change(p=>{var a=Find(p,id);var j=a.continuation;if(!enabled||a.state!="Started"||j.phase!="Awaiting"||!rules.Allows(j.count))return null;
                if(string.IsNullOrEmpty(j.quote)||j.expires<=now()){
                    if(!string.IsNullOrEmpty(j.pending))throw new InvalidOperationException("Pending continue must be reconciled");
                    j.quote=Guid.NewGuid().ToString("N");j.expires=checked(now()+rules.quoteSeconds);j.coinCost=rules.coinCost;j.extraMoves=rules.extraMoves;j.policy=rules.policy;
                }
                return new ContinueOffer{id=j.quote,attempt=id,cost=j.coinCost,moves=j.extraMoves,policy=j.policy,expires=j.expires,balance=p.coins};});
        }
        public void SetView(string id,string view){if(view!="offer"&&view!="shop")throw new ArgumentException("Invalid continue view");profiles.Change(p=>{var a=Find(p,id);if(a.state!="Started"||a.continuation.phase!="Awaiting"||!string.IsNullOrEmpty(a.continuation.pending))throw new InvalidOperationException("Continue is busy");a.continuation.view=view;return true;});}
        public string Prepare(string id,string quote){
            return profiles.Change(p=>{var a=Find(p,id);var j=a.continuation;if(!string.IsNullOrEmpty(j.pending)){if(j.pendingQuote!=quote)throw new InvalidOperationException("Pending command changed");return j.pending;}
                if(!enabled||a.state!="Started"||j.phase!="Awaiting"||j.quote!=quote||j.expires<=now()||!rules.Allows(j.count))throw new InvalidOperationException("Offer changed");
                if(p.coins<j.coinCost)throw new InvalidOperationException("Not enough coins");
                j.pending=Guid.NewGuid().ToString("N");j.pendingQuote=quote;return j.pending;});
        }
        public ContinueReceipt Purchase(string id,string operation){
            return profiles.Change(p=>{var a=Find(p,id);var j=a.continuation;var prior=j.receipts.FirstOrDefault(r=>r.operation==operation);if(prior!=null)return prior;
                if(string.IsNullOrEmpty(operation)||j.pending!=operation||string.IsNullOrEmpty(j.pendingQuote))throw new InvalidOperationException("Unprepared continue command");
                var r=new ContinueReceipt{operation=operation,attempt=id,quote=j.pendingQuote,outcome="Unavailable",coinsAfter=p.coins,beforeHash=ProfileJson.Hash(j.checkpoint)};
                if(enabled&&a.state=="Started"&&j.phase=="Awaiting"&&rules.Allows(j.count)){
                    if(j.pendingQuote!=j.quote||j.expires<=now())r.outcome="StaleQuote";
                    else if(p.coins<j.coinCost)r.outcome="InsufficientCoins";
                    else{
                        var board=BoardModel.FromCheckpoint(LevelFor(a),JsonUtility.FromJson<BoardCheckpoint>(j.checkpoint));board.ApplyContinue(operation,j.extraMoves);
                        r.outcome="Applied";r.cost=j.coinCost;r.movesAfter=board.Moves;r.afterCheckpoint=JsonUtility.ToJson(board.Checkpoint());p.coins=checked(p.coins-r.cost);r.coinsAfter=p.coins;
                        j.count=checked(j.count+1);j.phase="Purchased";j.checkpoint=r.afterCheckpoint;j.view="offer";
                    }
                }
                j.receipts.Add(r);return r;});
        }
        public void Acknowledge(string id,string operation){profiles.Change(p=>{var a=Find(p,id);var j=a.continuation;var r=j.receipts.FirstOrDefault(v=>v.operation==operation);if(r==null)throw new InvalidOperationException("Receipt not committed");if(j.pending==operation){j.pending="";j.pendingQuote="";}return true;});}
    }
    public sealed partial class ProfileService {
        // Invalidate a resumable continue checkpoint before the next gameplay
        // command mutates the board. Normal interruption settlement then applies.
        public void LeaveContinueCheckpoint(string id){Change(p=>{var a=Find(p,id);var j=a.continuation;if(a.state!="Started"||j.phase!="Purchased"||!string.IsNullOrEmpty(j.pending))throw new InvalidOperationException("Continue has not been applied");j.phase="";j.checkpoint="";j.quote="";return true;});}
    }
}

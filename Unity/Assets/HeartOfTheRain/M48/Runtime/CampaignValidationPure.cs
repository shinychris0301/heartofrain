using System;
using System.Collections.Generic;
using System.Linq;
using HeartOfTheRain.M46;

namespace HeartOfTheRain.M46 {
    public sealed partial class BoardModel {
        // Uses the production matcher, including 2x2 Seeker creation patterns.
        public void ValidateCampaignOpening() {
            Validate();
            if (Moves <= 0) throw new InvalidOperationException("Opening move budget must be positive.");
            if (Pieces.Count != Active.Count) throw new InvalidOperationException("Opening contains unfilled active cells.");
            if (Goals.Count < 2 || Goals.Count > 4 || Goals.Any(g => g.Value <= 0))
                throw new InvalidOperationException("Chapter 1 requires 2–4 positive target counts.");
            if (Pieces.Values.Where(p => p.IsAnchor && p.family != "gem" && p.family != "power").Any(p => !Goals.ContainsKey(GoalFamily(p))))
                throw new InvalidOperationException("Obstacle family is missing from the targets.");
            if (Level.activeColors == null || Level.activeColors.Length == 0 || Level.activeColors.Distinct().Count() != Level.activeColors.Length || Level.activeColors.Any(c => c < 0 || c > 5))
                throw new InvalidOperationException("Invalid active color palette.");
            if (Pieces.Values.Any(p => p.family == "gem" && !Level.activeColors.Contains(p.color)))
                throw new InvalidOperationException("Opening gem is outside the level palette.");
            if (Matches(null).Count != 0) throw new InvalidOperationException("Opening contains a matching line or square.");
            if (LegalSwaps().Count == 0 && !Pieces.Values.Any(p => p.family == "power"))
                throw new InvalidOperationException("Opening has no legal action.");
        }
    }
}

namespace HeartOfTheRain.M48 {
    [Serializable] public sealed class CampaignLevelCheck {
        public int level,columns,rows,activeCells,targetTypes,legalSwaps;
        public string status="PASS",error="";
    }
    [Serializable] public sealed class CampaignReplayCheck {
        public int level,seed,actions,verifiedActions;
        public string status="PASS",error="",finalStatus="";
    }
    [Serializable] public sealed class CampaignValidationReport {
        public string status="PASS_CAMPAIGN_LOGIC",scope="Level definitions and replay logic only; no rendered playback or human difficulty approval.";
        public List<string> errors=new List<string>();
        public List<CampaignLevelCheck> levels=new List<CampaignLevelCheck>();
        public List<CampaignReplayCheck> replays=new List<CampaignReplayCheck>();
    }
    public static class CampaignValidation {
        public static readonly int[] RequiredReplays={21,28,36,49,50};
        public static void ValidateReplayContract(CampaignReplay run,LevelData level) {
            if (run==null || level==null || run.level!=level.globalLevel) throw new InvalidOperationException("Replay level does not match its definition.");
            if (run.seed<=0 || run.budget<=0 || run.budget!=level.movesProposal) throw new InvalidOperationException("Replay seed or move budget is invalid.");
            if (run.expectedStatus!="Won" || run.actions==null || run.actions.Length==0 || run.actions.Length>run.budget)
                throw new InvalidOperationException("Replay must contain a complete clear within its move budget.");
            string previous=null;
            foreach(var move in run.actions) {
                if(move==null || (move.kind!="tap" && move.kind!="swap")) throw new InvalidOperationException("Unsupported or missing replay action.");
                if(!Hash(move.before)||!Hash(move.after)) throw new InvalidOperationException("Invalid replay fingerprint.");
                if(previous!=null&&previous!=move.before) throw new InvalidOperationException("Replay fingerprint chain is broken.");
                if(!InBounds(level,move.ax,move.ay) || (move.kind=="swap" && (!InBounds(level,move.bx,move.by)||Math.Abs(move.ax-move.bx)+Math.Abs(move.ay-move.by)!=1)))
                    throw new InvalidOperationException("Replay coordinates are invalid.");
                previous=move.after;
            }
        }
        static bool Hash(string value)=>value!=null&&value.Length==16&&value.All(c=>c>='0'&&c<='9'||c>='a'&&c<='f');
        static bool InBounds(LevelData level,int x,int y)=>x>=0&&y>=0&&x<level.columns&&y<level.rows;
        public static CampaignValidationReport Run(LevelData[] levels,CampaignReplaySet set) {
            var report=new CampaignValidationReport();
            if(levels==null||levels.Length!=50) report.errors.Add("Expected exactly 50 ordered level definitions.");
            foreach(var level in levels??new LevelData[0]) {
                var row=new CampaignLevelCheck{level=level==null?0:level.globalLevel};report.levels.Add(row);
                try {
                    if(level==null||level.globalLevel!=report.levels.Count||level.id!="C01_L"+level.globalLevel.ToString("000")) throw new InvalidOperationException("Level identity or order differs.");
                    var board=new BoardModel(level);board.ValidateCampaignOpening();
                    row.columns=level.columns;row.rows=level.rows;row.activeCells=board.Active.Count;row.targetTypes=board.Goals.Count;row.legalSwaps=board.LegalSwaps().Count;
                } catch(Exception ex) {row.status="FAIL";row.error=ex.Message;report.errors.Add("Level "+row.level+": "+ex.Message);}
            }
            var runs=set==null?null:set.runs;
            if(runs==null || runs.Length!=RequiredReplays.Length || !runs.Where(r=>r!=null).Select(r=>r.level).OrderBy(n=>n).SequenceEqual(RequiredReplays))
                report.errors.Add("Expected exactly one replay each for levels 21, 28, 36, 49 and 50.");
            foreach(var run in runs??new CampaignReplay[0]) {
                var row=new CampaignReplayCheck{level=run==null?0:run.level};report.replays.Add(row);
                try {
                    var level=levels==null?null:levels.FirstOrDefault(l=>l!=null&&l.globalLevel==row.level);ValidateReplayContract(run,level);
                    row.seed=run.seed;row.actions=run.actions.Length;var board=new BoardModel(level,(uint)run.seed);
                    foreach(var move in run.actions) {
                        var before=board.Moves;TurnResult result;string error;
                        if(!CampaignReplayRules.Apply(board,move,out result,out error)) throw new InvalidOperationException(error);
                        board.Validate();if(board.Moves!=before-1) throw new InvalidOperationException("Replay move charge differs.");
                        row.verifiedActions++;
                    }
                    row.finalStatus=board.Status;
                    if(board.Status!=run.expectedStatus||board.Goals.Any(g=>g.Value!=0)) throw new InvalidOperationException("Replay did not finish with all targets cleared.");
                } catch(Exception ex) {row.status="FAIL";row.error=ex.Message;report.errors.Add("Replay "+row.level+": "+ex.Message);}
            }
            if(report.errors.Count>0)report.status="FAIL_CAMPAIGN_LOGIC";
            return report;
        }
    }
}

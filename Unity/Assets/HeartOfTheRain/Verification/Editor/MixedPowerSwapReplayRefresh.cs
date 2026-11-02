#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.M48;
namespace HeartOfTheRain.Verification
{
    // Refresh only stale legal-clear fixtures affected by the approved mixed
    // swap repair. Never changes level content, tools, powers or move budgets.
    public static class MixedPowerSwapReplayRefresh
    {
        const string ReplayPath="Assets/HeartOfTheRain/M48/Resources/HOTR_Playtests/Campaign_Replays.json";
        [Serializable] public sealed class Difference
        {
            public int level,action,ax,ay,bx,by,firstPower,secondPower,oldSeed,newSeed,oldActions,newActions,budget,attempts;
            public string kind,firstFamily,secondFamily,expectedAfter,actualAfter,finalStatus;
            public int[] createdPowers;public bool accepted,mixedSwap,immediateMatch;
        }
        [Serializable] public sealed class AssetHash {public string path,sha256;}
        [Serializable] public sealed class Report
        {
            public string utc,status,beforeSHA256,afterSHA256;
            public string scope="Native model diagnosis and narrowly refreshed legal campaign clears for levels21/49 only; authored level files, move budgets, other replay records and artwork unchanged. No human balance or rendered/device certification.";
            public bool changed,otherReplaysUnchanged,levelFilesUnchanged;
            public List<Difference> differences=new List<Difference>();public List<AssetHash> levelHashes=new List<AssetHash>();
            public List<string> errors=new List<string>();public CampaignValidationReport campaign;
        }
        public static void Diagnose()=>Execute(false);
        public static void Run()=>Execute(true);
        static string Hash(byte[] bytes){using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
        static BoardModel Copy(BoardModel board)
        {
            var copy=new BoardModel(board.Level);copy.Pieces.Clear();foreach(var pair in board.Pieces)copy.Pieces.Add(pair.Key,pair.Value.Copy());copy.Goals.Clear();foreach(var pair in board.Goals)copy.Goals.Add(pair.Key,pair.Value);
            foreach(string name in new[]{"random","nextId","activationSerial","<Moves>k__BackingField","<Turn>k__BackingField","<Status>k__BackingField","<QuietMoves>k__BackingField","<GrowthUsed>k__BackingField"}){var field=typeof(BoardModel).GetField(name,BindingFlags.Instance|BindingFlags.NonPublic);field.SetValue(copy,field.GetValue(board));}return copy;
        }
        static ReplayMove Move(ReplayMove old)=>new ReplayMove{kind=old.kind,ax=old.ax,ay=old.ay,bx=old.bx,by=old.by};
        static TurnResult Apply(BoardModel board,ReplayMove move)=>move.kind=="tap"?board.Tap(move.ax,move.ay):board.Swap(move.ax,move.ay,move.bx,move.by);
        static IEnumerable<ReplayMove> Actions(BoardModel board)
        {
            foreach(var pair in board.LegalSwaps())yield return new ReplayMove{kind="swap",ax=pair[0].x,ay=pair[0].y,bx=pair[1].x,by=pair[1].y};
            foreach(var p in board.Pieces.Values.Where(p=>p.family=="power").OrderBy(p=>p.id))yield return new ReplayMove{kind="tap",ax=p.x,ay=p.y};
        }
        static float Cost(BoardModel board)=>board.Goals.Values.Sum()*100+board.Pieces.Values.Where(p=>p.IsAnchor&&!p.Movable).Sum(p=>p.hp)*9-board.Pieces.Values.Where(p=>p.family=="power").Sum(p=>p.power==7?55:p.power==21?28:20);
        static Difference Diagnose(LevelData level,CampaignReplay old)
        {
            var board=new BoardModel(level,(uint)old.seed);
            for(int n=0;n<old.actions.Length;n++)
            {
                var move=old.actions[n];if(CampaignReplayRules.Fingerprint(board)!=move.before)throw new Exception("L"+old.level+" diverged before the first changed action "+(n+1));
                var a=board.At(move.ax,move.ay);var b=board.At(move.bx,move.by);string af=a?.family,bf=b?.family;int ap=a?.power??-1,bp=b?.power??-1;
                var turn=Apply(board,move);string after=CampaignReplayRules.Fingerprint(board);
                if(!turn.accepted)throw new Exception("L"+old.level+" old action rejected before any fingerprint divergence "+(n+1));
                if(after==move.after)continue;
                var difference=new Difference{level=old.level,action=n+1,kind=move.kind,ax=move.ax,ay=move.ay,bx=move.bx,by=move.by,firstFamily=af,secondFamily=bf,firstPower=ap,secondPower=bp,oldSeed=old.seed,oldActions=old.actions.Length,budget=level.movesProposal,expectedAfter=move.after,actualAfter=after,accepted=turn.accepted,mixedSwap=move.kind=="swap"&&(af=="gem"&&bf=="power"||af=="power"&&bf=="gem"),immediateMatch=turn.steps.Count>1&&turn.steps[1].kind=="match",createdPowers=turn.steps.Count>1?turn.steps[1].created.Where(p=>p.family=="power").Select(p=>p.power).ToArray():new int[0]};
                if(!difference.mixedSwap||!difference.immediateMatch)throw new Exception("L"+old.level+" first divergence is not caused by repaired initial mixed-swap match");return difference;
            }
            throw new Exception("L"+old.level+" has no stale replay fingerprint; refusing unnecessary refresh");
        }
        static CampaignReplay Solve(LevelData level,CampaignReplay old,Difference difference)
        {
            // First try every original action at the original seed. Changed
            // fingerprints alone never justify asserting a successful clear.
            for(int attempt=0;attempt<97;attempt++)
            {
                int seed=attempt<33?old.seed:old.seed+(attempt-32)*7919;var board=new BoardModel(level,(uint)seed);var moves=new List<ReplayMove>();var random=new System.Random(seed+attempt*613);
                int fixedPrefix=attempt==0?old.actions.Length:attempt<17?difference.action:attempt<33?difference.action-1:0;
                bool followOld=true;
                while(board.Status=="Playing"&&board.Moves>0)
                {
                    ReplayMove chosen=null;
                    if(followOld&&moves.Count<Math.Min(fixedPrefix,old.actions.Length))
                    {
                        var prior=Move(old.actions[moves.Count]);if(Apply(Copy(board),prior).accepted)chosen=prior;else followOld=false;
                    }
                    if(chosen==null)
                    {
                        float best=float.NegativeInfinity;
                        foreach(var option in Actions(board))
                        {
                            var candidate=Copy(board);var result=Apply(candidate,option);if(!result.accepted||candidate.Status=="Resolution limit")continue;
                            float score=Cost(board)-Cost(candidate)+(candidate.Status=="Won"?100000:0)+(float)random.NextDouble()*(attempt%4==0?1:18);
                            if(score>best){best=score;chosen=option;}
                        }
                    }
                    if(chosen==null)break;chosen.before=CampaignReplayRules.Fingerprint(board);var turn=Apply(board,chosen);if(!turn.accepted)throw new Exception("Search chose rejected action");chosen.after=CampaignReplayRules.Fingerprint(board);moves.Add(chosen);
                }
                if(board.Status=="Won")
                {
                    board.Validate();if(moves.Count>level.movesProposal)throw new Exception("Search exceeded authored budget");difference.newSeed=seed;difference.newActions=moves.Count;difference.attempts=attempt+1;difference.finalStatus=board.Status;
                    return new CampaignReplay{level=old.level,seed=seed,budget=level.movesProposal,expectedStatus="Won",actions=moves.ToArray()};
                }
                if(attempt%8==0)Debug.Log("Mixed-swap replay L"+old.level+" attempt "+attempt+" remaining goals "+board.Goals.Values.Sum());
            }
            throw new Exception("No verified legal clear found for L"+old.level+"; campaign file was not written");
        }
        static void Execute(bool refresh)
        {
            var report=new Report{utc=DateTime.UtcNow.ToString("o")};string folder=Path.GetFullPath("../Verification/Evidence/GameplayAudit");Directory.CreateDirectory(folder);
            try
            {
                byte[] original=File.ReadAllBytes(ReplayPath);report.beforeSHA256=Hash(original);var set=JsonUtility.FromJson<CampaignReplaySet>(Encoding.UTF8.GetString(original));var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");var levels=ui.boards.levels.Select(a=>JsonUtility.FromJson<LevelData>(a.text)).ToArray();
                var others=set.runs.Where(r=>r.level!=21&&r.level!=49).ToDictionary(r=>r.level,r=>JsonUtility.ToJson(r));
                foreach(var asset in ui.boards.levels){string path=AssetDatabase.GetAssetPath(asset);report.levelHashes.Add(new AssetHash{path=path,sha256=Hash(File.ReadAllBytes(path))});}
                foreach(int number in new[]{21,49})
                {
                    int index=Array.FindIndex(set.runs,r=>r.level==number);if(index<0)throw new Exception("Missing L"+number+" replay");var old=set.runs[index];var level=levels[number-1];if(old.budget!=level.movesProposal)throw new Exception("Existing L"+number+" replay budget differs from authored level");
                    var difference=Diagnose(level,old);report.differences.Add(difference);Debug.Log("Mixed-swap replay diagnosis L"+number+" action "+difference.action+": "+difference.firstFamily+" + "+difference.secondFamily+" created ["+string.Join(",",difference.createdPowers)+"]");
                    if(refresh)set.runs[index]=Solve(level,old,difference);
                }
                report.otherReplaysUnchanged=others.All(pair=>JsonUtility.ToJson(set.runs.Single(r=>r.level==pair.Key))==pair.Value);report.levelFilesUnchanged=report.levelHashes.All(entry=>Hash(File.ReadAllBytes(entry.path))==entry.sha256);
                if(!report.otherReplaysUnchanged||!report.levelFilesUnchanged)throw new Exception("Unrelated replay or level changed");
                if(refresh)
                {
                    report.campaign=CampaignValidation.Run(levels,set);if(report.campaign.errors.Count>0)throw new Exception(string.Join("; ",report.campaign.errors));
                    string backup=Path.Combine(folder,"Before/Campaign_Replays.json");Directory.CreateDirectory(Path.GetDirectoryName(backup));if(!File.Exists(backup))File.WriteAllBytes(backup,original);else if(Hash(File.ReadAllBytes(backup))!=report.beforeSHA256)throw new Exception("Existing replay baseline differs; refusing to overwrite");
                    set.milestone="M67R4 + approved obstacle gravity and mixed-swap match creation repairs";set.scope="Deterministic native model clears using legal actions and unchanged authored budgets after mixed-swap match repair. Not human balance approval.";
                    File.WriteAllText(ReplayPath,JsonUtility.ToJson(set,true)+"\n");report.changed=true;AssetDatabase.ImportAsset(ReplayPath,ImportAssetOptions.ForceUpdate);
                }
                report.afterSHA256=Hash(File.ReadAllBytes(ReplayPath));report.status=refresh?"PASS_NATIVE_MIXED_SWAP_REPLAY_REFRESH":"PASS_NATIVE_MIXED_SWAP_REPLAY_DIAGNOSIS";
            }
            catch(Exception error){report.status="FAIL_NATIVE_MIXED_SWAP_REPLAY_REFRESH";report.errors.Add(error.ToString());Debug.LogError(error);}
            File.WriteAllText(Path.Combine(folder,refresh?"Campaign_Replay_Refresh.json":"Replay_Diagnosis.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.errors.Count==0?0:1);
        }
    }
}
#endif

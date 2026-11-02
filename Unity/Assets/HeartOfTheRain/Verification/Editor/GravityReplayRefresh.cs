#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using HeartOfTheRain.M48;
namespace HeartOfTheRain.Verification
{
    // Explicit verification-data refresh after the approved gravity rule repair.
    // Never modifies a level, injects a power or changes a move budget.
    public static class GravityReplayRefresh
    {
        static BoardModel Copy(BoardModel b){
            var c=new BoardModel(b.Level);c.Pieces.Clear();foreach(var kv in b.Pieces)c.Pieces.Add(kv.Key,kv.Value.Copy());c.Goals.Clear();foreach(var kv in b.Goals)c.Goals.Add(kv.Key,kv.Value);
            foreach(string name in new[]{"random","nextId","activationSerial","<Moves>k__BackingField","<Turn>k__BackingField","<Status>k__BackingField","<QuietMoves>k__BackingField","<GrowthUsed>k__BackingField"}){var f=typeof(BoardModel).GetField(name,BindingFlags.Instance|BindingFlags.NonPublic);f.SetValue(c,f.GetValue(b));}return c;
        }
        static TurnResult Apply(BoardModel b,ReplayMove m)=>m.kind=="tap"?b.Tap(m.ax,m.ay):b.Swap(m.ax,m.ay,m.bx,m.by);
        static float Cost(BoardModel b)=>b.Goals.Values.Sum()*100+b.Pieces.Values.Where(p=>p.IsAnchor&&!p.Movable).Sum(p=>p.hp)*9-b.Pieces.Values.Where(p=>p.family=="power").Sum(p=>p.power==7?55: p.power==21?28:20);
        static IEnumerable<ReplayMove> Actions(BoardModel b){foreach(var pair in b.LegalSwaps())yield return new ReplayMove{kind="swap",ax=pair[0].x,ay=pair[0].y,bx=pair[1].x,by=pair[1].y};foreach(var p in b.Pieces.Values.Where(p=>p.family=="power").OrderBy(p=>p.id))yield return new ReplayMove{kind="tap",ax=p.x,ay=p.y};}
        public static void Run(){
            try{
                string path="Assets/HeartOfTheRain/M48/Resources/HOTR_Playtests/Campaign_Replays.json";var set=JsonUtility.FromJson<CampaignReplaySet>(File.ReadAllText(path));var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
                foreach(var old in set.runs){
                    var level=JsonUtility.FromJson<LevelData>(ui.boards.levels[old.level-1].text);var original=new BoardModel(level,(uint)old.seed);bool unchanged=true;foreach(var m in old.actions){TurnResult t;string error;if(!CampaignReplayRules.Apply(original,m,out t,out error)){unchanged=false;break;}}if(unchanged&&original.Status=="Won")continue;
                    CampaignReplay replacement=null;
                    for(int attempt=0;attempt<160&&replacement==null;attempt++){
                        int seed=old.seed+attempt*7919;var b=new BoardModel(level,(uint)seed);var moves=new List<ReplayMove>();var random=new System.Random(seed);bool followOld=attempt==0;
                        while(b.Status=="Playing"&&b.Moves>0){
                            ReplayMove chosen=null;
                            if(followOld&&moves.Count<old.actions.Length){var prior=old.actions[moves.Count];if(Apply(Copy(b),prior).accepted)chosen=new ReplayMove{kind=prior.kind,ax=prior.ax,ay=prior.ay,bx=prior.bx,by=prior.by};else followOld=false;}
                            if(chosen==null){float best=float.NegativeInfinity;foreach(var m in Actions(b)){var c=Copy(b);var t=Apply(c,m);if(!t.accepted||c.Status=="Resolution limit")continue;float score=Cost(b)-Cost(c)+(c.Status=="Won"?100000:0)+(float)random.NextDouble()*(attempt%4==0?1:18);if(score>best){best=score;chosen=m;}}}
                            if(chosen==null)break;chosen.before=CampaignReplayRules.Fingerprint(b);var turn=Apply(b,chosen);if(!turn.accepted)throw new Exception("Solver chose rejected action");chosen.after=CampaignReplayRules.Fingerprint(b);moves.Add(chosen);
                        }
                        if(b.Status=="Won")replacement=new CampaignReplay{level=old.level,seed=seed,budget=level.movesProposal,expectedStatus="Won",actions=moves.ToArray()};
                        if(attempt%10==0)Debug.Log("Gravity replay search L"+old.level+" attempt "+attempt+" remaining "+b.Goals.Values.Sum());
                    }
                    if(replacement==null)throw new Exception("No legal clear found for L"+old.level);
                    int index=Array.IndexOf(set.runs,old);set.runs[index]=replacement;Debug.Log("Gravity replay verified L"+old.level+" seed "+replacement.seed+" actions "+replacement.actions.Length);
                }
                var levels=ui.boards.levels.Select(a=>JsonUtility.FromJson<LevelData>(a.text)).ToArray();var report=CampaignValidation.Run(levels,set);if(report.errors.Count>0)throw new Exception(string.Join("; ",report.errors));
                set.milestone="M67R4 + approved obstacle gravity repair";set.scope="Deterministic native model clears after diagonal gravity repair; legal actions and authored budgets only. Not human balance approval.";File.WriteAllText(path,JsonUtility.ToJson(set,true)+"\n");AssetDatabase.Refresh();File.WriteAllText(Path.GetFullPath("../Verification/Evidence/ObstacleGravity/Campaign_Replay_Refresh.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(0);
            }catch(Exception e){Debug.LogError(e);EditorApplication.Exit(1);}
        }
    }
}
#endif

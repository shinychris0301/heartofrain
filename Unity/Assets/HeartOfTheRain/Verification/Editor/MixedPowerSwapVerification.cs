#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
namespace HeartOfTheRain.Verification
{
    public static class MixedPowerSwapVerification
    {
        [Serializable] sealed class CaseResult {public string name;public int sourcePower,recipe,createdId,createdKind;public bool chained,sourceHitsBirthCell,protectedBirth;}
        [Serializable] sealed class Report
        {
            public string utc,status,scope="Native Unity live-model and playback checks. Device input/rendering/performance evidence is separate.";
            public int checks,turns,chainedBirths,protectedBirths,sourceHitBirthCells,existingChainControls;public List<string> failures=new List<string>();public List<CaseResult> cases=new List<CaseResult>();
        }
        public static void Run()
        {
            var report=new Report{utc=DateTime.UtcNow.ToString("o")};
            void Check(bool ok,string label){report.checks++;if(!ok)report.failures.Add(label);}
            try
            {
                foreach(int recipe in new[]{4,5,21,7,11})foreach(int sourcePower in new[]{4,5,21,7,11,16})foreach(int rotation in new[]{0,1,2,3})foreach(bool powerDragged in new[]{false,true})
                    Exercise(recipe,sourcePower,rotation,powerDragged,9,9,report,Check);
                foreach(var shape in new[]{new[]{9,11},new[]{11,11}})foreach(int recipe in new[]{4,5,21,7,11})foreach(int sourcePower in new[]{4,5,21,7,11,16})foreach(bool powerDragged in new[]{false,true})
                    Exercise(recipe,sourcePower,0,powerDragged,shape[0],shape[1],report,Check);
                Check(report.chainedBirths==0&&report.protectedBirths==report.turns,"All mixed-swap rewards survive their originating power wave");
                Check(report.sourceHitBirthCells>0,"Protection controls include actual source hits on the birth cell");
                foreach(int rotation in new[]{0,1,2,3})ExistingChainAndExpiry(rotation,report,Check);
                foreach(int sourcePower in new[]{4,5,21,7,11,16})foreach(bool threeMatch in new[]{false,true})
                {
                    var level=MixedPowerSwapFixtures.Match(4);var gem=level.initialTiles.Single(p=>p.x==4&&p.y==2);gem.color=2;
                    if(!threeMatch)level.initialTiles.Single(p=>p.x==4&&p.y==3).color=3;
                    var board=new BoardModel(level);board.InjectReviewPower(4,4,sourcePower);var sourceId=board.At(4,4).id;var turn=board.Swap(3,4,4,4);var initial=turn.steps.Skip(1).First();
                    Check(turn.accepted,"Mixed swap accepted without four-match "+sourcePower+"/"+threeMatch);
                    Check(initial.kind==(threeMatch?"match":"power"),"Mixed swap resolves only an actual initial match "+sourcePower+"/"+threeMatch);
                    if(threeMatch)Check(initial.created.Count==0,"Three gems do not invent a power "+sourcePower);
                    Check(turn.steps.Any(s=>s.kind=="power"&&s.removed.Any(p=>p.piece.id==sourceId&&p.cause=="source")),"Original power still activates "+sourcePower+"/"+threeMatch);
                    Check(board.Moves==19&&board.Turn==1&&board.Status!="Resolution limit","Single move settlement for mixed control "+sourcePower+"/"+threeMatch);board.Validate();
                }
                var unsupported=new BoardModel(MixedPowerSwapFixtures.Match(4));unsupported.InjectReviewPower(3,4,16);unsupported.InjectReviewPower(4,4,16);string before=JsonUtility.ToJson(unsupported.Snapshot());var rejected=unsupported.Swap(3,4,4,4);
                Check(!rejected.accepted&&JsonUtility.ToJson(unsupported.Snapshot())==before,"Golden + Golden remains undefined and mutation-free");
            }
            catch(Exception error){report.failures.Add(error.ToString());}
            report.status=report.failures.Count==0?"PASS_NATIVE_MIXED_POWER_SWAP":"FAIL_NATIVE_MIXED_POWER_SWAP";string folder=Path.GetFullPath(System.Environment.GetEnvironmentVariable("HOTR_REVIEW93_OUT")??"../Verification/Evidence/GameplayAudit");Directory.CreateDirectory(folder);File.WriteAllText(Path.Combine(folder,"Mixed_Swap_Checks.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.failures.Count==0?0:1);
        }
        static void Exercise(int recipe,int sourcePower,int rotation,bool powerDragged,int columns,int rows,Report report,Action<bool,string> check)
        {
            string label=recipe+"/"+sourcePower+"/"+rotation+"/"+powerDragged+"/"+columns+"x"+rows;var board=new BoardModel(MixedPowerSwapFixtures.Match(recipe,rotation,columns,rows));var from=MixedPowerSwapFixtures.From(recipe,rotation,columns,rows);var to=MixedPowerSwapFixtures.To(rotation,columns,rows);
            check(board.InjectReviewPower(to.x,to.y,sourcePower),"Install source power "+label);var gem=board.At(from.x,from.y).Copy();int sourceId=board.At(to.x,to.y).id;
            var turn=powerDragged?board.Swap(to.x,to.y,from.x,from.y):board.Swap(from.x,from.y,to.x,to.y);report.turns++;
            check(turn.accepted,"Accept gem + power exchange "+label);check(turn.steps[0].kind=="swap"&&turn.steps[1].kind=="match","Resolve initial match immediately after accepted swap "+label);
            var match=turn.steps.First(s=>s.kind=="match");var made=match.created.SingleOrDefault(p=>p.id==gem.id);check(made!=null,"Create item from moved matching gem "+label);if(made==null)return;
            int expected=(recipe==4||recipe==5)?(from.x!=to.x?4:5):recipe;
            check(made.power==expected&&made.x==to.x&&made.y==to.y,"Keep recipe priority, matching endpoint and gesture axis "+label);
            var source=turn.steps.First(s=>s.kind=="power");check(source.removed.Any(p=>p.piece.id==sourceId&&p.cause=="source"),"Activate original source after match "+label);
            if(sourcePower==7)check(source.powerPlan.kind==7&&source.powerPlan.targetColor==gem.color,"Orb preserves swapped gem color before creation "+label);
            bool chained=turn.steps.Any(s=>s.kind=="power"&&s.removed.Any(p=>p.piece.id==made.id&&p.cause=="source"));if(chained)report.chainedBirths++;
            bool contacted=source.powerPlan.tiles.Any(t=>t.x==made.x&&t.y==made.y&&t.hit>=0);if(contacted)report.sourceHitBirthCells++;
            var reward=board.Pieces.Values.SingleOrDefault(p=>p.id==made.id);bool protectedBirth=!chained&&reward!=null&&reward.family=="power"&&reward.power==expected;if(protectedBirth)report.protectedBirths++;
            check(protectedBirth,"New reward is neither consumed nor chained by the originating source "+label);
            int gravity=turn.steps.FindIndex(s=>s.kind=="gravity");var wave=turn.steps.Take(gravity<0?turn.steps.Count:gravity).Where(s=>s.kind=="power").ToArray();
            check(wave.All(s=>s.after.pieces.Any(p=>p.id==made.id&&p.family=="power"&&p.power==expected)),"Reward survives every action in the originating wave "+label);
            check(wave.All(s=>(s.powerPlan.flight!=null?new[]{s.powerPlan.flight}:s.powerPlan.flights??new ReviewFlight[0]).All(f=>f.targetX!=made.x||f.targetY!=made.y)),"Actual aimed projectiles select another eligible cell "+label);
            check(board.Moves==19&&board.Turn==1&&board.Status!="Resolution limit","Exactly one settled move and turn "+label);board.Validate();
            var playback=BoardPlayback.Build(turn.steps,board.Level);var creation=playback.First(s=>s.created.Any(p=>p.id==made.id));var view=new BoardPresentation();view.Add(creation,0);var draw=view.Sample(creation,creation.before,.08f,0).FirstOrDefault(d=>d.pieceId==made.id&&d.bank=="power");
            check(draw!=null&&draw.key==BoardPresentation.CreationClip(BoardPresentation.PowerAtlas(expected)),"Generated item receives authored creation playback "+label);
            report.cases.Add(new CaseResult{name=label,sourcePower=sourcePower,recipe=recipe,createdId=made.id,createdKind=made.power,chained=chained,sourceHitsBirthCell=contacted,protectedBirth=protectedBirth});
        }
        static void ExistingChainAndExpiry(int rotation,Report report,Action<bool,string> check)
        {
            string label="Existing chain and expiry rotation "+rotation;var level=MixedPowerSwapFixtures.Match(4,rotation);var board=new BoardModel(level);var from=MixedPowerSwapFixtures.From(4,rotation);var to=MixedPowerSwapFixtures.To(rotation);var target=MixedPowerSwapFixtures.Rotate(6,4,rotation,9,9);
            int sourceKind=(rotation&1)==0?4:5;check(board.InjectReviewPower(to.x,to.y,sourceKind)&&board.InjectReviewPower(target.x,target.y,21),label+": install source and pre-existing Bomb");
            int rewardId=board.At(from.x,from.y).id,sourceId=board.At(to.x,to.y).id,chainId=board.At(target.x,target.y).id;var turn=board.Swap(from.x,from.y,to.x,to.y);report.existingChainControls++;
            check(turn.accepted&&turn.steps.Any(s=>s.kind=="power"&&s.removed.Any(r=>r.piece.id==sourceId&&r.cause=="source")),label+": swapped Rocket executes");
            check(turn.steps.Any(s=>s.kind=="power"&&s.removed.Any(r=>r.piece.id==chainId&&r.cause=="source")),label+": pre-existing Bomb still chains");
            var reward=board.Pieces.Values.SingleOrDefault(p=>p.id==rewardId);check(reward!=null&&reward.family=="power"&&!turn.steps.Any(s=>s.removed.Any(r=>r.piece.id==rewardId)),label+": newborn survives source and chained Bomb");
            if(reward==null)return;
            // The reservation is transient. It must not survive settlement,
            // checkpoint restore or the next deliberate activation.
            var restored=BoardModel.FromCheckpoint(level,board.Checkpoint());var next=restored.Tap(reward.x,reward.y);
            check(next.accepted&&next.steps.Any(s=>s.kind=="power"&&s.removed.Any(r=>r.piece.id==rewardId&&r.cause=="source")),label+": reward activates normally after restore");
            check(restored.Moves==18&&restored.Turn==2,label+": two commands spend exactly two moves");restored.Validate();
            var nextSource=board.Pieces.Values.Where(p=>p.family=="gem"&&Math.Max(Math.Abs(p.x-reward.x),Math.Abs(p.y-reward.y))<=2).OrderBy(p=>Math.Abs(p.x-reward.x)+Math.Abs(p.y-reward.y)).FirstOrDefault();
            check(nextSource!=null,label+": later hit control has a nearby source");
            if(nextSource!=null){board.InjectReviewPower(nextSource.x,nextSource.y,21);var hit=board.Tap(nextSource.x,nextSource.y);check(hit.accepted&&hit.steps.Any(s=>s.kind=="power"&&s.removed.Any(r=>r.piece.id==rewardId&&r.cause=="source")),label+": later command can hit and chain the former reward");board.Validate();}
            // An aimed projectile must not reserve the protected newborn as its
            // target, while the pre-existing power remains a valid target.
            var aimBoard=new BoardModel(level);aimBoard.InjectReviewPower(to.x,to.y,sourceKind);aimBoard.InjectReviewPower(target.x,target.y,21);aimBoard.InjectReviewPower(from.x,from.y,4);var newborn=aimBoard.At(from.x,from.y);
            var aim=new LiveBoardInput(aimBoard,aimBoard.At(to.x,to.y),null,new[]{newborn.id});
            check(!aim.CanTarget(newborn.x,newborn.y)&&aim.CanTarget(target.x,target.y),label+": aiming excludes only the reserved reward");
        }
    }
}
#endif

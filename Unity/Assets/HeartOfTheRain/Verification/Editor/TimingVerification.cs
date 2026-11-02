#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using Motion=HeartOfTheRain.M46.Motion;
using HeartOfTheRain.M48;
namespace HeartOfTheRain.Verification
{
    public static class TimingVerification
    {
        [Serializable] public sealed class Report {public string status="PASS_NATIVE_TIMING_CHECKS",utc,scope="Native Unity model-preservation, contact timing, fall paths and segment reservations. Rendered/device evidence is separate.";public int checks;public string[] failures;public float directRocketIgnition,hitRocketIgnition,oneCellFall,threeCellFall,nineCellFall;}
        public static void Run()
        {
            var r=new Report{utc=DateTime.UtcNow.ToString("o")};var failures=new List<string>();
            void Check(bool ok,string label){r.checks++;if(!ok)failures.Add(label);}
            try{
                r.oneCellFall=TileFall.Duration(1);r.threeCellFall=TileFall.Duration(3);r.nineCellFall=TileFall.Duration(9);
                Check(r.oneCellFall<r.threeCellFall&&r.threeCellFall<r.nineCellFall,"Distance-aware flight time");
                foreach(float distance in new[]{1f,3f,9f}){float previous=-1;for(int i=0;i<=120;i++){float progress=TileFall.Progress(distance,i/120f);Check(progress>=previous&&progress>=0&&progress<=1,"Monotonic fall "+distance+" sample "+i);previous=progress;}Check(TileFall.Progress(distance,.2f)<.2f,"Fall accelerates from rest "+distance);}
                var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
                for(int level=0;level<50;level++)foreach(int kind in new[]{4,5,7,11,16,21}){
                    var b=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[level].text));var p=b.Pieces.Values.First(v=>v.family=="gem");b.InjectReviewPower(p.x,p.y,kind);var turn=b.Tap(p.x,p.y);string model=JsonUtility.ToJson(b.Snapshot()),raw=JsonUtility.ToJson(turn);var schedule=BoardPlayback.Build(turn.steps,b.Level);
                    Check(JsonUtility.ToJson(b.Snapshot())==model&&JsonUtility.ToJson(turn)==raw,"Immutable model/steps L"+(level+1)+" kind "+kind);
                    Check(ReferenceEquals(schedule.Last().after,turn.steps.Last().after),"Final snapshot L"+(level+1)+" kind "+kind);
                    foreach(var s in schedule){Check(s.duration>0&&!float.IsInfinity(s.duration)&&!float.IsNaN(s.duration),"Finite duration");Check(s.motion.All(m=>m.delay>=0&&m.seconds>0&&m.delay+m.seconds<=s.duration+.001f),"All flights reach their cells before the next phase");Check(s.collections.All(c=>c.arrival+.25f<=new BoardPresentation().HistoryLifetime(s)+.001f),"Collection survives in presentation history L"+(level+1)+" kind "+kind+" step "+s.kind);
                        // Adjacent falling bodies stay ordered, including delayed incoming pieces.
                        foreach(var column in s.motion.GroupBy(m=>m.toX)){
                            var moves=column.OrderBy(m=>m.toY).ToArray();for(int i=1;i<moves.Length;i++){var lower=moves[i-1];var upper=moves[i];if(upper.toY>lower.fromY||upper.fromY<=lower.fromY||upper.path!=null||lower.path!=null||upper.fromX!=upper.toX||lower.fromX!=lower.toX)continue;bool splitPath=false;for(int y=(int)lower.toY+1;y<(int)upper.toY;y++)if(!b.Active.Contains(b.Key((int)lower.toX,y))||s.after.pieces.Any(p=>p.x==lower.toX&&p.y==y&&!p.Movable)){splitPath=true;break;}if(splitPath)continue;bool clearPath=true;string witness="";for(int n=0;n<=120;n++){float t=s.duration*n/120f;float Y(Motion m){float x,y;TileFall.Position(m,t,out x,out y);return y;}if(Y(upper)-Y(lower)<.999f){clearPath=false;witness=" at "+t+" lower "+lower.id+":"+lower.fromY+">"+lower.toY+" delay "+lower.delay+" upper "+upper.id+":"+upper.fromY+">"+upper.toY+" delay "+upper.delay+" column "+lower.toX+" after "+string.Join(";",s.after.pieces.Where(p=>p.x==lower.toX).Select(p=>p.id+":"+p.family+"@"+p.y));break;}}Check(clearPath,"Falling order L"+(level+1)+" kind "+kind+" step "+s.kind+witness);}
                        }
                    }
                }
                var board=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[0].text));var row=board.Pieces.Values.Where(p=>p.family=="gem").GroupBy(p=>p.y).Where(g=>g.Count()>=3).OrderByDescending(g=>g.Key).First().OrderBy(p=>p.x).Take(3).ToArray();foreach(var p in row)board.InjectReviewPower(p.x,p.y,4);
                var chain=BoardPlayback.Build(board.Tap(row[0].x,row[0].y).steps,board.Level).First();var root=chain.playbackTracks.First();r.directRocketIgnition=root.step.powerPlan.primary-root.leadIn;Check(r.directRocketIgnition<=.17f,"Direct rocket ignites within 170 ms");
                foreach(var child in chain.playbackTracks.Skip(1)){r.hitRocketIgnition=child.step.powerPlan.primary-child.leadIn;Check(r.hitRocketIgnition<=.11f,"Hit rocket ignites within 110 ms");float contact=root.start+child.step.triggerTime-root.step.triggerTime-root.leadIn;Check(Math.Abs(child.start-contact)<.001f,"Child starts at retimed parent contact");}
                var empty=new BoardSnapshot{pieces=new Piece[0],goals=new Goal[0]};var late=new BoardStep{kind="power",duration=2,before=empty,after=empty,powerPlan=new ReviewPlan{effects=new[]{new ReviewFx{clip="Late",start=.95f,duration=.4f}},tiles=new ReviewTile[0]}};
                var combined=new BoardStep{before=empty,after=empty,playbackTracks=new List<PlaybackTrack>{new PlaybackTrack{step=late,start=1,leadIn=.9f}}};var view=new BoardPresentation();view.Add(combined,0);Check(!view.Sample(combined,empty,.95f,0).Any(d=>d.key=="Late"),"Future track never draws early");Check(view.Sample(combined,empty,1.06f,0).Any(d=>d.key=="Late"),"Track-local visual time advances after contact");
                var cells=Enumerable.Range(0,7).Select(y=>new Cell(0,y)).ToArray();var geometry=new LevelData{columns=1,rows=7,activeCells=cells};
                var before=new BoardSnapshot{pieces=new[]{new Piece{id=1,x=0,y=0,family="gem"},new Piece{id=2,x=0,y=1,family="gem"},new Piece{id=3,x=0,y=3,family="stone",hp=1},new Piece{id=4,x=0,y=4,family="gem"},new Piece{id=5,x=0,y=5,family="gem"}},goals=new Goal[0]};
                var after=new BoardSnapshot{pieces=new[]{new Piece{id=2,x=0,y=0,family="gem"},before.pieces[2].Copy(),new Piece{id=5,x=0,y=4,family="gem"}},goals=new Goal[0]};
                var hit=new BoardStep{kind="power",before=before,after=before,powerPlan=new ReviewPlan{primary=2}};hit.removed.Add(new Removed{piece=before.pieces[0],time=2,cause="power"});hit.removed.Add(new Removed{piece=before.pieces[3],time=.1f,cause="power"});var fall=new BoardStep{kind="gravity",before=before,after=after};fall.motion.Add(new Motion{id=2,fromX=0,toX=0,fromY=1,toY=0});fall.motion.Add(new Motion{id=5,fromX=0,toX=0,fromY=5,toY=4});
                var split=BoardPlayback.Build(new[]{hit,fall},geometry).First();Check(split.motion.First(m=>m.id==2).delay>=2.04f-.001f,"Late lower vacancy remains reserved");Check(split.motion.First(m=>m.id==5).delay<.2f,"Independent upper segment refills early");
                var cabinet=new BoardModel(PlaybackFixtures.ClearingCabinet());var clear=BoardPlayback.Build(cabinet.UseBooster(BoosterKind.Hammer,3,0,new BoosterInventory()).steps,cabinet.Level).First();Check(clear.motion.Where(m=>m.toX==3||m.toX==4).All(m=>m.delay>=1.6f-.001f),"Cabinet complete footprint remains reserved");Check(clear.collections.All(c=>c.arrival+.25f<=new BoardPresentation().HistoryLifetime(clear)+.001f),"Cabinet goal flight survives beyond the refill phase");
                var portalBoard=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[41].text));var firstGem=portalBoard.Pieces.Values.First(p=>p.family=="gem");portalBoard.InjectReviewPower(firstGem.x,firstGem.y,21);var portal=BoardPlayback.Build(portalBoard.Tap(firstGem.x,firstGem.y).steps,portalBoard.Level).First();var portalView=new BoardPresentation();var lowerSpawn=portal.motion.First(m=>m.spawned&&m.toX==1&&m.toY==4);Check(lowerSpawn.clipSpawn&&lowerSpawn.spawnTop==4,"Lower-section spawn retains its portal boundary");Check(!portalView.Sample(portal,portal.after,0,0).Any(d=>d.pieceId==lowerSpawn.id),"Virtual lower spawn is hidden in the upper island");Check(portalView.Sample(portal,portal.after,portal.duration,0).Any(d=>d.pieceId==lowerSpawn.id&&Math.Abs(d.y-4)<.001f),"Lower spawn arrives in its own section");
                var cues=FeedbackPlan.Build(chain);Check(cues.Any(c=>c.id=="rocket_launch"&&Math.Abs(c.time-r.directRocketIgnition)<.001f),"Audio launch follows retimed visual launch");
                var inputBoard=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[0].text));var legal=inputBoard.LegalSwaps().First();var buffer=new BoardGestureBuffer();string state=JsonUtility.ToJson(inputBoard.Snapshot());
                Check(buffer.Capture(inputBoard,legal[0].x,legal[0].y,legal[1].x,legal[1].y),"Capture one pending intent");Check(JsonUtility.ToJson(inputBoard.Snapshot())==state,"Buffer never mutates the model");Check(!buffer.Capture(inputBoard,legal[0].x,legal[0].y,legal[1].x,legal[1].y),"No unbounded gesture queue");
                Cell from,to;Check(buffer.Take(inputBoard,out from,out to)&&from.x==legal[0].x&&to.y==legal[1].y,"Stable identities accepted once");Check(!buffer.Take(inputBoard,out from,out to),"Pending intent cannot execute twice");
                buffer.Capture(inputBoard,legal[0].x,legal[0].y,legal[1].x,legal[1].y);inputBoard.Swap(legal[0].x,legal[0].y,legal[1].x,legal[1].y);Check(!buffer.Take(inputBoard,out from,out to),"Turn changes invalidate an intent");
                var replacement=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[0].text));legal=replacement.LegalSwaps().First();buffer.Capture(replacement,legal[0].x,legal[0].y,legal[1].x,legal[1].y);Check(!buffer.Take(new BoardModel(replacement.Level),out from,out to),"Reload with identical IDs cannot reuse an intent");
                buffer.Capture(replacement,legal[0].x,legal[0].y,legal[1].x,legal[1].y);buffer.Clear();Check(!buffer.Take(replacement,out from,out to),"Cancellation removes queued input");
                var rejectBefore=replacement.Snapshot();var a=rejectBefore.pieces.First(p=>p.family=="gem");var other=rejectBefore.pieces.First(p=>p.family=="gem"&&Math.Abs(p.x-a.x)+Math.Abs(p.y-a.y)==1);var reject=new BoardStep{kind="reject",duration=.22f,before=rejectBefore,after=rejectBefore};reject.motion.Add(new Motion{id=a.id,fromX=a.x,fromY=a.y,toX=other.x,toY=other.y});var sampler=new BoardPresentation();
                var startPose=sampler.Sample(reject,rejectBefore,0,0).First(d=>d.key==BoardPresentation.BodyKey(a)&&Math.Abs(d.x-a.x)<.001f&&Math.Abs(d.y-a.y)<.001f);Check(startPose!=null,"Rejected-swap body starts at its original cell");var endPose=sampler.Sample(reject,rejectBefore,.22f,0);Check(endPose.Any(d=>d.key==BoardPresentation.BodyKey(a)&&Math.Abs(d.x-a.x)<.001f&&Math.Abs(d.y-a.y)<.001f),"Rejected-swap body returns to its original cell");Check(ReferenceEquals(reject.before,reject.after),"Rejected-swap presentation has no model mutation");
            }catch(Exception e){failures.Add(e.ToString());}
            r.failures=failures.ToArray();if(failures.Count>0)r.status="FAIL_NATIVE_TIMING_CHECKS";string output=Path.GetFullPath("../Verification/Evidence/Timing");Directory.CreateDirectory(output);File.WriteAllText(Path.Combine(output,"Native_Checks.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(failures.Count==0?0:1);
        }
    }
}
#endif

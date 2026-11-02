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
using Motion=HeartOfTheRain.M46.Motion;
namespace HeartOfTheRain.Verification
{
    public static class ObstacleGravityVerification
    {
        [Serializable] public class Report {public string status,utc,scope="Native Unity model checks and GPU board render; Android evidence is separate.";public int checks,gapsBeneathStack,diagonalMoves;public string[] failures;}
        public static void Baseline(){Run(true);}
        public static void Run(){Run(false);}
        static void Run(bool baseline)
        {
            string output=Path.GetFullPath("../Verification/Evidence/ObstacleGravity");Directory.CreateDirectory(output);var r=new Report{utc=DateTime.UtcNow.ToString("o")};var failures=new List<string>();
            void Check(bool ok,string name){r.checks++;if(!ok)failures.Add(name);}
            try{
                var b=new BoardModel(PlaybackFixtures.StackedStones());var turn=b.UseBooster(BoosterKind.Hammer,4,2,new BoosterInventory());
                r.gapsBeneathStack=b.At(4,2)==null?1:0;r.diagonalMoves=turn.steps.Sum(s=>s.motion.Count(m=>m.fromX!=m.toX));
                Check(turn.accepted,"Hammer accepted");Check(b.At(4,2)!=null,"Broken bottom obstacle refills beneath surviving stack");Check(b.At(4,3)?.family=="stone"&&b.At(4,4)?.family=="stone","Upper fixed stones stay in their original cells");Check(b.Goals["stone"]==2,"Exactly one stone goal removed");Check(b.Moves==20,"Hammer does not spend a move");b.Validate();
                if(!baseline){var opening=BoardPlayback.Build(turn.steps,b.Level).First();var view=new BoardPresentation();float contact=opening.removed.First(rm=>rm.piece.x==4&&rm.piece.y==2).time;var early=view.Sample(opening,opening.after,contact-.05f,0).Where(d=>d.pieceId!=0).ToArray();Check(opening.before.pieces.Where(p=>p.Movable).All(p=>early.Any(d=>d.pieceId==p.id&&Math.Abs(d.x-p.x)<.001f&&Math.Abs(d.y-p.y)<.001f)),"No upstream tile moves before the original obstacle hit");}
                Render(b,Path.Combine(output,baseline?"Stack_Before.png":"Stack_After.png"));
                if(!baseline){
                    var gravity=typeof(BoardModel).GetMethod("Gravity",BindingFlags.Instance|BindingFlags.NonPublic);
                    TurnResult Fall(BoardModel board){var t=new TurnResult();gravity.Invoke(board,new object[]{t});board.Validate();return t;}
                    BoardModel Gap(){var board=new BoardModel(PlaybackFixtures.StackedStones());board.Pieces.Remove(board.Key(4,2));board.Goals["stone"]--;return board;}
                    var pose=new BoardSnapshot{pieces=new[]{new Piece{id=1,x=3,y=3,family="crate",hp=1}},goals=new Goal[0]};var landed=new BoardSnapshot{pieces=new[]{new Piece{id=1,x=4,y=2,family="crate",hp=1}},goals=new Goal[0]};
                    var clearing=new BoardStep{kind="power",before=pose,after=pose,powerPlan=new ReviewPlan{kind=21,primary=1},duration=3};clearing.removed.Add(new Removed{piece=new Piece{id=2,x=3,y=2,family="stone",hp=1},cause="obstacle",time=2});
                    var elbow=new BoardStep{kind="gravity",before=pose,after=landed};elbow.motion.Add(new Motion{id=1,fromX=3,fromY=3,toX=4,toY=2});var cellGeometry=new LevelData{columns=9,rows=9,activeCells=PlaybackFixtures.StackedStones().activeCells};
                    var reserved=BoardPlayback.Build(new[]{clearing,elbow},cellGeometry).First();Check(reserved.motion[0].delay>=2-.84f+.24f-.001f,"Diagonal waits for late corner removal");
                    clearing.damage.Add(new Damage{id=1,x=3,y=3,family="crate",beforeHP=2,afterHP=1,time=2.5f});reserved=BoardPlayback.Build(new[]{clearing,elbow},cellGeometry).First();Check(reserved.motion[0].delay>=2.5f-.84f+.12f-.001f,"Diagonal waits for source obstacle hit");
                    foreach(int column in new[]{0,4,8})foreach(int broken in new[]{2,3,4}){
                        var board=new BoardModel(PlaybackFixtures.StackedStones(column));var fixedBefore=board.Snapshot().pieces.Where(p=>!p.Movable&&p.y!=broken).ToArray();board.Pieces.Remove(board.Key(column,broken));board.Goals["stone"]--;Fall(board);
                        Check(board.Pieces.Count==board.Active.Count,"Full refill for stack column "+column+" broken row "+broken);Check(fixedBefore.All(p=>board.At(p.x,p.y)?.id==p.id),"Remaining stack positions preserved at column "+column+" row "+broken);
                    }
                    foreach(string family in new[]{"gem","power","crate","pail"}){
                        var board=Gap();var source=board.At(3,3);source.family=family;if(family=="power"){source.power=4;source.color=-1;}if(family=="crate"||family=="pail"){source.hp=1;board.Goals[family]=1;}
                        int id=source.id;var state=Fall(board);Check(board.At(4,2)?.id==id,"Diagonal feed preserves "+family+" identity");Check(board.Pieces.Count==board.Active.Count,"Stack refills all reachable cells for "+family);Check(state.steps.Any(s=>s.motion.Any(m=>m.id==id&&m.fromX==3&&m.toX==4&&m.fromY==3&&m.toY==2)),"Explicit elbow segment for "+family);Check(board.Moves==20&&board.Turn==0,"Gravity does not spend move or advance turn");
                    }
                    var vertical=Gap();vertical.Pieces.Remove(vertical.Key(2,2));int above=vertical.At(2,3).id;Fall(vertical);Check(vertical.At(2,2)?.id==above,"Straight-down source wins before diagonal source");
                    var sealedCorner=Gap();foreach(int x in new[]{3,5}){var p=sealedCorner.At(x,2);p.family="stone";p.hp=3;sealedCorner.Goals["stone"]++;}Fall(sealedCorner);Check(sealedCorner.At(4,2)==null,"Solid corners cannot be crossed");
                    var island=Gap();foreach(int x in new[]{3,5}){island.Pieces.Remove(island.Key(x,2));island.Active.Remove(island.Key(x,2));}island.Level.activeCells=island.Level.activeCells.Where(c=>island.Active.Contains(island.Key(c.x,c.y))).ToArray();Fall(island);Check(island.At(4,2)==null,"Mask holes cannot become diagonal portals");
                    var jar=Gap();var jp=jar.At(3,3);jp.family="pail";jp.hp=1;jar.Goals["pail"]=1;jar.Exits.Add(jar.Key(3,3));int jid=jp.id;Fall(jar);Check(jar.At(3,3)?.id==jid,"Jar already on exit is not diverted sideways");
                    var wide=new BoardModel(PlaybackFixtures.StackedStones());for(int x=2;x<=6;x++)for(int y=0;y<=2;y++){var p=wide.At(x,y);if(p?.family=="stone")wide.Goals["stone"]--;wide.Pieces.Remove(wide.Key(x,y));}for(int x=2;x<=6;x++){var p=wide.At(x,3);if(p.family!="stone"){p.family="stone";p.hp=3;wide.Goals["stone"]++;}}var wideFall=Fall(wide);Check(Enumerable.Range(2,5).All(x=>wide.At(x,0)!=null),"Wide pocket fills reachable bottom cells from edges");Check(wide.At(4,2)==null,"Solid ceiling does not acquire an unauthored spawn");Check(wideFall.steps.Count<40,"Wide pocket settles in bounded waves");
                    var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
                    var lane=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[48].text));var crystal=lane.Pieces.Values.First(p=>p.family=="crystal"&&p.IsAnchor);int laneX=crystal.x,edgeY=crystal.y+crystal.hp,neighbor=laneX==0?1:laneX-1;
                    foreach(var p in lane.Pieces.Values.Where(p=>p.x==laneX&&p.family=="gem").ToArray())lane.Pieces.Remove(lane.Key(p.x,p.y));lane.Spawns.Remove(lane.Key(laneX,lane.Level.rows-1));var incoming=lane.At(neighbor,edgeY+1);if(incoming==null||incoming.family!="gem")throw new Exception("Crystal regression source is not a gem");incoming.family="crate";incoming.hp=1;if(!lane.Goals.ContainsKey("crate"))lane.Goals["crate"]=0;lane.Goals["crate"]++;Fall(lane);Check(lane.Pieces.Values.Where(p=>p.x==laneX).All(p=>p.family=="crystal"||p.family=="gem"||p.family=="power"),"Side feeds preserve exclusive crystal lane");
                    for(int level=0;level<50;level++)foreach(int kind in new[]{4,5,7,11,16,21}){
                        var data=JsonUtility.FromJson<LevelData>(ui.boards.levels[level].text);var a=new BoardModel(data);var copy=new BoardModel(data);var p=a.Pieces.Values.First(v=>v.family=="gem");a.InjectReviewPower(p.x,p.y,kind);copy.InjectReviewPower(p.x,p.y,kind);var action=a.Tap(p.x,p.y);copy.Tap(p.x,p.y);
                        Check(a.Status!="Resolution limit","Gravity terminates L"+(level+1)+" power "+kind);Check(CampaignReplayRules.Fingerprint(a)==CampaignReplayRules.Fingerprint(copy),"Deterministic gravity L"+(level+1)+" power "+kind);var probe=Fall(a);Check(probe.steps.Count==0,"Settled gravity is idempotent L"+(level+1)+" power "+kind);
                        foreach(var s in action.steps.Where(s=>s.kind=="gravity")){
                            Check(s.motion.Select(m=>m.id).Distinct().Count()==s.motion.Count,"No tile moves twice within a gravity wave");Check(s.motion.All(m=>s.after.pieces.Any(q=>q.id==m.id&&q.x==m.toX&&q.y==m.toY)),"Gravity destinations match snapshot");
                            Check(s.motion.Where(m=>m.fromX!=m.toX).All(m=>Math.Abs(m.fromX-m.toX)==1&&m.fromY-m.toY==1&&!m.spawned&&s.before.pieces.Any(q=>q.id==m.id&&q.x==m.fromX&&q.y==m.fromY)),"Diagonal paths are adjacent descending cells");
                            Check(s.motion.Where(m=>m.fromX!=m.toX).All(m=>!s.before.pieces.Any(q=>q.x==m.toX&&q.y==m.toY)),"Diagonal waves use only initial vacancies");
                            Check(s.before.pieces.Where(q=>!q.Movable).All(q=>s.after.pieces.Any(v=>v.id==q.id&&v.x==q.x&&v.y==q.y&&v.hp==q.hp)),"Gravity preserves every fixed footprint");
                        }
                    }
                }
            }catch(Exception e){failures.Add(e.ToString());}
            r.failures=failures.ToArray();r.status=failures.Count==0?"PASS_NATIVE_OBSTACLE_GRAVITY":"FAIL_NATIVE_OBSTACLE_GRAVITY";File.WriteAllText(Path.Combine(output,baseline?"Baseline_Checks.json":"Native_Checks.json"),JsonUtility.ToJson(r,true));EditorApplication.Exit(baseline?0:failures.Count==0?0:1);
        }
        static void Render(BoardModel b,string path)
        {
            var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");var root=new GameObject("Native stacked obstacle render");var bank=new M46AtlasBank(ui.boards);var material=new Material(ui.bodyShader?ui.bodyShader:Shader.Find("Sprites/Default"));var target=new RenderTexture(900,900,24);Texture2D pixels=null;
            try{
                root.transform.position=new Vector3(1000,0,0);var cameraObject=new GameObject("Camera");cameraObject.transform.SetParent(root.transform,false);var camera=cameraObject.AddComponent<Camera>();camera.orthographic=true;camera.orthographicSize=5;camera.transform.localPosition=new Vector3(4,4,-10);camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.035f,.05f,.07f);camera.targetTexture=target;
                var surfaceObject=new GameObject("Board surface");surfaceObject.transform.SetParent(root.transform,false);surfaceObject.transform.localPosition=new Vector3(4,4,0);var surface=surfaceObject.AddComponent<SpriteRenderer>();surface.sharedMaterial=material;surface.sprite=bank.BoardSurface(0);surface.sortingOrder=0;
                bank.BeginFrame();foreach(var d in new BoardPresentation{columns=9,rows=9}.Sample(null,b.Snapshot(),0,0)){
                    var sprite=bank.Get(d);if(!sprite)continue;var go=new GameObject("Body "+d.pieceId);go.transform.SetParent(root.transform,false);go.transform.localPosition=new Vector3(d.x,d.y,0);go.transform.localScale=new Vector3(d.sx,d.sy,1);var sr=go.AddComponent<SpriteRenderer>();sr.sprite=sprite;sr.sharedMaterial=material;sr.sortingOrder=d.order;sr.color=new Color(d.red,d.green,d.blue,d.alpha);
                }
                camera.Render();RenderTexture.active=target;pixels=new Texture2D(900,900,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,900,900),0,0);pixels.Apply();File.WriteAllBytes(path,pixels.EncodeToPNG());
            }finally{RenderTexture.active=null;UnityEngine.Object.DestroyImmediate(root);UnityEngine.Object.DestroyImmediate(material);UnityEngine.Object.DestroyImmediate(target);if(pixels)UnityEngine.Object.DestroyImmediate(pixels);bank.Dispose();}
        }
    }
}
#endif

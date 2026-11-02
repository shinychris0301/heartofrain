#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 public static class CrateBurstVerification {
  [Serializable] public class Row {
   public string name,turnHash,finalHash,poseHash;public int crates,cleared,hits,powers,peakDraws,peakCrateDraws,preparedSprites,playbackCreates,playbackCrateCreates,playbackObstacleCreates,peakFrameCreates,evictions,synchronousLoads,reserve;
   public double preparationMs,modelMs,sampleMs,atlasMs,worstAtlasMs;public long spriteBytes,textureBytes;
  }
  [Serializable] public class Report {
   public string status,utc,phase,error,scope="Native Unity Editor CPU/atlas stress replay. Authored board models and full pose signatures are compared before/after. GPU renders are untimed; this is not Android frame pacing or physical-device certification.";
   public int checks;public bool pressureProtection,noCrateSkip;public List<Row> rows=new List<Row>();public List<string> frames=new List<string>();public List<string> familiesPrepared=new List<string>();
  }
  static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
  static Report report;static GameplayUIAssets ui;static string output;
  public static void Before()=>Run("Before");public static void After()=>Run("After");
  static void Check(bool ok,string name){report.checks++;if(!ok)throw new Exception(name);}
  static string Hash(string s){using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(s))).Replace("-","").ToLowerInvariant();}
  public static BoardPresentation View(GameplayUIAssets ui,int columns,int rows){var v=new BoardPresentation{columns=columns,rows=rows};foreach(var d in ui.boards.debrisProfiles){var p=JsonUtility.FromJson<DebrisProfile>(d.metadata.text);foreach(var piece in p.pieces){if(piece.scaleMultiplier<=0)piece.scaleMultiplier=1;if(piece.spinMultiplier<=0)piece.spinMultiplier=1;}v.profiles[d.family]=p;}return v;}
  public static TurnResult Solve(BoardModel b,string kind){
   if(kind=="rocket_chain"){var row=b.Pieces.Values.Where(p=>p.family=="gem").GroupBy(p=>p.y).OrderByDescending(g=>g.Count()).First().OrderBy(p=>p.x).ToArray();foreach(var p in row)b.InjectReviewPower(p.x,p.y,4);return b.Tap(row[0].x,row[0].y);}
   var a=b.Pieces.Values.First(p=>p.family=="gem"&&b.At(p.x+1,p.y)?.family=="gem");var partner=b.At(a.x+1,a.y);b.InjectReviewPower(a.x,a.y,7);b.InjectReviewPower(partner.x,partner.y,kind=="double_orb"?7:4);return b.Swap(a.x,a.y,partner.x,partner.y);
  }
  public static void Warm(M46AtlasBank bank,BoardSnapshot snapshot){
   var texture=typeof(M46AtlasBank).GetMethod("Texture",Private);foreach(var path in bank.CommonResources(snapshot))texture.Invoke(bank,new object[]{null,path});
   var common=bank.WarmCommonFrames();while(common.MoveNext()){}
   var method=typeof(M46AtlasBank).GetMethod("WarmObstacleFrames");if(method!=null){var warm=(IEnumerator)method.Invoke(bank,new object[]{snapshot,16});while(warm.MoveNext()){} }
  }
  static void Dispose(M46AtlasBank bank){var cache=(IDictionary)typeof(M46AtlasBank).GetField("sprites",Private).GetValue(bank);foreach(var entry in cache.Values){var s=(Sprite)entry.GetType().GetField("sprite").GetValue(entry);if(s)UnityEngine.Object.DestroyImmediate(s);}cache.Clear();bank.Dispose();}
  static void Run(string phase){
   report=new Report{utc=DateTime.UtcNow.ToString("o"),phase=phase};output=Path.GetFullPath("../Verification/Evidence/CrateBurst/"+phase);Directory.CreateDirectory(output);
   try{
    ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");
    foreach(int level in new[]{11,22,25,41,48})foreach(string kind in new[]{"double_orb","orb_rocket","rocket_chain"}){
     var b=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[level].text));var snapshot=b.Snapshot();var row=new Row{name="L"+(level+1)+"_"+kind,crates=snapshot.pieces.Count(p=>p.family=="crate"),reserve=phase=="After"?GameplayScreen.WarmRendererCapacity(b.Level.columns,b.Level.rows,snapshot,View(ui,b.Level.columns,b.Level.rows).profiles):GameplayScreen.WarmRendererCapacity(b.Level.columns,b.Level.rows)};
     var watch=Stopwatch.StartNew();var turn=Solve(b,kind);watch.Stop();row.modelMs=watch.Elapsed.TotalMilliseconds;Check(turn.accepted,"Accepted "+row.name);b.Validate();row.turnHash=Hash(JsonUtility.ToJson(turn));row.finalHash=Hash(JsonUtility.ToJson(b.Snapshot()));row.hits=turn.steps.Sum(s=>s.damage.Count(d=>d.family=="crate"));row.cleared=turn.steps.Sum(s=>s.removed.Count(r=>r.piece.family=="crate"));row.powers=turn.steps.Count(s=>s.kind=="power");
     var steps=BoardPlayback.Build(turn.steps,b.Level);var bank=new M46AtlasBank(ui.boards);try{
      watch.Restart();Warm(bank,snapshot);watch.Stop();row.preparationMs=watch.Elapsed.TotalMilliseconds;row.preparedSprites=bank.SpriteCount;
      // The runtime texture gate completes before each step starts. Keep that work outside frame sampling here.
      var load=typeof(M46AtlasBank).GetMethod("Texture",Private);foreach(var path in bank.RequiredResources(steps))load.Invoke(bank,new object[]{null,path});
      int created=bank.SpriteCreates,evicted=bank.SpriteEvictions,sync=bank.SynchronousLoads;var v=View(ui,b.Level.columns,b.Level.rows);float start=0;ulong hash=14695981039346656037UL;List<DrawSprite> peak=null;
      Action<string> digest=s=>{unchecked{foreach(char c in s){hash^=c;hash*=1099511628211UL;}}};
      foreach(var step in steps){v.Add(step,start);int count=Math.Max(1,Mathf.CeilToInt(step.duration*30));for(int frame=0;frame<count;frame++){
       float t=start+step.duration*(frame+.1f)/count;bank.BeginFrame();v.PruneHistory(t);watch.Restart();var draws=v.SampleLive(step,step.before,t,start);watch.Stop();row.sampleMs+=watch.Elapsed.TotalMilliseconds;
       int prior=bank.SpriteCreates;watch.Restart();foreach(var d in draws)if(d.alpha>0){int before=bank.SpriteCreates;bank.Get(d);if(d.bank=="obstacle"){int made=bank.SpriteCreates-before;row.playbackObstacleCreates+=made;if(d.key.StartsWith("crate/",StringComparison.Ordinal))row.playbackCrateCreates+=made;}}bank.EndFrame(false);watch.Stop();row.atlasMs+=watch.Elapsed.TotalMilliseconds;row.worstAtlasMs=Math.Max(row.worstAtlasMs,watch.Elapsed.TotalMilliseconds);row.peakFrameCreates=Math.Max(row.peakFrameCreates,bank.SpriteCreates-prior);row.peakCrateDraws=Math.Max(row.peakCrateDraws,draws.Count(d=>d.bank=="obstacle"&&d.key.StartsWith("crate/",StringComparison.Ordinal)));
       if(draws.Count>row.peakDraws){row.peakDraws=draws.Count;if(level==41&&kind=="double_orb")peak=draws.Select(d=>d.Copy()).ToList();}
       foreach(var d in draws)digest(JsonUtility.ToJson(d));
      }start+=step.duration;}
      row.playbackCreates=bank.SpriteCreates-created;row.evictions=bank.SpriteEvictions-evicted;row.synchronousLoads=bank.SynchronousLoads-sync;row.poseHash=hash.ToString("x16");row.spriteBytes=bank.CachedSpriteRuntimeBytes;row.textureBytes=bank.TextureBytes;
      if(peak!=null)Capture(bank,b.Level,peak,"L42_DoubleOrb_Peak.png");
     }finally{Dispose(bank);}report.rows.Add(row);
    }
    if(phase=="After"){
     var before=JsonUtility.FromJson<Report>(File.ReadAllText(Path.Combine(output,"../Before/Report.json")));Check(before.status=="PASS_NATIVE_CRATE_BURST","Valid baseline");
     foreach(var row in report.rows){var old=before.rows.Single(r=>r.name==row.name);Check(old.turnHash==row.turnHash&&old.finalHash==row.finalHash&&old.poseHash==row.poseHash,"Exact model/visual semantics "+row.name);Check(row.synchronousLoads==0,"No rendering texture load "+row.name);Check(row.playbackCrateCreates==0,"No cold crate sprite creation "+row.name);Check(row.playbackObstacleCreates==0,"No cold obstacle sprite creation "+row.name);Check(row.reserve>=row.peakDraws,"Prepared capacity covers burst "+row.name);}
     var bank=new M46AtlasBank(ui.boards);try{var empty=new BoardSnapshot{pieces=new Piece[0]};var warm=bank.WarmObstacleFrames(empty);while(warm.MoveNext()){}Check(bank.SpriteCreates==0&&bank.TextureCount==0,"No crate allocation for a board without crates");report.noCrateSkip=true;
      var snapshot=new BoardSnapshot{pieces=new[]{new Piece{family="crate",hp=3}}};Warm(bank,snapshot);int created=bank.SpriteCreates;var draw=new DrawSprite{bank="obstacle",key="crate/Wood_Tumble_7",age=.2f};var original=bank.Get(draw);bank.SpriteLimit=0;bank.TextureBudget=0;bank.BeginFrame();bank.EndFrame(true);Check(bank.Get(draw)==original&&bank.SpriteCreates==created,"Prepared crate survives idle sprite/texture budget pressure");report.pressureProtection=true;
     }finally{Dispose(bank);}
     // Every other family: level preparation must load each clip page and pin
     // every authored frame, so a later hit creates no sprite even after the
     // idle budgets have been exhausted by unrelated work.
     foreach(var family in new[]{"stone","moss","case","gate","crystal","pod","cabinet","pail"}){
      var familyBank=new M46AtlasBank(ui.boards);try{
       int hp=family=="crystal"?9:family=="cabinet"?5:family=="pod"||family=="stone"?3:family=="pail"?0:2;
       var snapshot=new BoardSnapshot{pieces=new[]{new Piece{id=1,family=family,hp=hp}},goals=new Goal[0]};
       var clips=ui.boards.obstacleClips.Where(c=>c.key.StartsWith(family+"/",StringComparison.Ordinal)).ToArray();
       var pages=clips.SelectMany(c=>c.pageResources??new string[0]).Where(p=>!string.IsNullOrEmpty(p)).Distinct().ToArray();
       var common=familyBank.CommonResources(snapshot);Check(clips.Length>0&&pages.Length>0&&pages.All(common.Contains),"Level preparation loads every "+family+" clip page");
       Warm(familyBank,snapshot);int created=familyBank.SpriteCreates,sync=familyBank.SynchronousLoads,pinned=familyBank.PinnedSprites;
       Check(pinned>0&&familyBank.SpriteLimit>=M46AtlasBank.WorkingSetSpriteLimit+pinned,"Pinned "+family+" frames sit outside the working-set sprite cap");
       familyBank.SpriteLimit=0;familyBank.TextureBudget=0;familyBank.BeginFrame();familyBank.EndFrame(true);
       foreach(var clip in clips){var meta=JsonUtility.FromJson<ClipData>(clip.metadata.text);for(int n=0;n<meta.frames.Length;n++)Check(familyBank.Get(new DrawSprite{bank="obstacle",key=clip.key,age=(n+.1f)/meta.fps})!=null,"Prepared "+clip.key+" frame "+n);}
       Check(familyBank.SpriteCreates==created&&familyBank.SynchronousLoads==sync,"Prepared "+family+" frames survive budget pressure without cold creation");
       report.familiesPrepared.Add(family);
      }finally{Dispose(familyBank);}
     }
    }
    report.status="PASS_NATIVE_CRATE_BURST";
   }catch(Exception e){report.status="FAIL_NATIVE_CRATE_BURST";report.error=e.ToString();}
   File.WriteAllText(Path.Combine(output,"Report.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.error==null?0:1);
  }
  static void Capture(M46AtlasBank bank,LevelData level,List<DrawSprite> draws,string name){
   var root=new GameObject("Crate burst untimed GPU sample");root.transform.position=new Vector3(1000,0,0);var previous=RenderTexture.active;var target=new RenderTexture(900,1600,24);Material material=null;
   try{var cam=new GameObject("Camera").AddComponent<Camera>();cam.transform.SetParent(root.transform,false);cam.transform.localPosition=new Vector3((level.columns-1)*.5f,(level.rows-1)*.5f,-10);cam.orthographic=true;cam.orthographicSize=BoardPresentation.CameraHalfHeight(level.columns,level.rows,900f/1600);cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=new Color(.035f,.05f,.07f);cam.targetTexture=target;material=new Material(ui.bodyShader?ui.bodyShader:Shader.Find("Sprites/Default"));
    foreach(var d in draws){var sprite=bank.Get(d);if(!sprite||d.alpha<=0)continue;var sr=new GameObject(d.key).AddComponent<SpriteRenderer>();sr.transform.SetParent(root.transform,false);sr.transform.localPosition=new Vector3(d.x,d.y,0);sr.transform.localScale=new Vector3(d.sx,d.sy,1);sr.transform.localRotation=Quaternion.Euler(0,0,d.angle);sr.sprite=sprite;sr.sharedMaterial=material;sr.sortingOrder=d.order;sr.color=new Color(d.red,d.green,d.blue,d.alpha);}
    cam.Render();RenderTexture.active=target;var pixels=new Texture2D(900,1600,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,900,1600),0,0);pixels.Apply();File.WriteAllBytes(Path.Combine(output,name),pixels.EncodeToPNG());UnityEngine.Object.DestroyImmediate(pixels);report.frames.Add(name);
   }finally{RenderTexture.active=previous;UnityEngine.Object.DestroyImmediate(root);if(material)UnityEngine.Object.DestroyImmediate(material);UnityEngine.Object.DestroyImmediate(target);}
  }
 }
}
#endif

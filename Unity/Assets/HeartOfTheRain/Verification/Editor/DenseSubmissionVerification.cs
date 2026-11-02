#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using Object=UnityEngine.Object;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
using Legacy=HeartOfTheRain.Verification.Submission77.ArchivedEffectMeshBatcher77;
namespace HeartOfTheRain.Verification {
 public static class DenseSubmissionVerification {
  struct Input {public Sprite sprite;public int order;public Vector3 position;public float angle,sx,sy;public Color color;}
  sealed class Fixture {public string name;public LevelData level;public List<DrawSprite> draws;public M46AtlasBank bank;}
  [Serializable] public sealed class ParityRow {public string name,archivedHash,arrayHash,controlHash;public int quads,meshes;public bool ordered;}
  [Serializable] public sealed class PixelRow {public string name;public int differingPixels,maxChannelDelta;}
  [Serializable] public sealed class TimingRow {
   public string name,scope="Alternating warmed native Begin/Add/End CPU spans using the same pre-resolved sprites; all64 primary pairs retained. Sampling, atlas lookup, camera rendering and GPU completion are excluded.";
   public int pairs,currentSlowerPairs,controlSlowerPairs;
   public double archivedAddMedianMs,arrayAddMedianMs,controlAddMedianMs,archivedUploadMedianMs,arrayUploadMedianMs,controlUploadMedianMs,archivedFrameMedianMs,arrayFrameMedianMs,controlFrameMedianMs,archivedFrameP95Ms,arrayFrameP95Ms,controlFrameP95Ms;
   public List<double> archivedAddMs=new List<double>(),arrayAddMs=new List<double>(),controlAddMs=new List<double>(),archivedUploadMs=new List<double>(),arrayUploadMs=new List<double>(),controlUploadMs=new List<double>(),archivedFrameMs=new List<double>(),arrayFrameMs=new List<double>(),controlFrameMs=new List<double>();
  }
  [Serializable] public sealed class Report {
   public string status,utc,unity,error,archivedSourceSHA256,compiledBodySHA256;
   public string scope="Native Unity Editor exact archived77/same-APK control mesh state and strict camera pixels, plus warmed CPU construction/upload. No device frame-pacing, input-latency, allocation-saving or universal speedup claim.";
   public string memoryScope="Development controls retain both List and array storage prepared before timing; release excludes old Lists. This extra development working set remains outside an allocation-saving claim.";
   public bool compiledSourceMatchesArchive,midFrameSwitchOwnership,disposedOwnershipReleased;
   public int checks,fixtures,parityFrames,negativeControls,width=900,height=1600;
   public List<ParityRow> parityRows=new List<ParityRow>();public List<PixelRow> pixelRows=new List<PixelRow>();public List<TimingRow> timings=new List<TimingRow>();public List<string> frames=new List<string>();
  }
  static Report report;static GameplayUIAssets ui;static string output;
  static void Check(bool okay,string message){report.checks++;if(!okay)throw new Exception(message);}
  static string Hash(byte[] bytes){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
  static string Hash(string text)=>Hash(Encoding.UTF8.GetBytes(text));
  static double Ms(long ticks)=>ticks*1000.0/System.Diagnostics.Stopwatch.Frequency;
  static double Quantile(List<double> values,double q){var sorted=values.OrderBy(x=>x).ToArray();if(q==.5&&sorted.Length%2==0)return (sorted[sorted.Length/2-1]+sorted[sorted.Length/2])*.5;return sorted[Math.Max(0,(int)Math.Ceiling(sorted.Length*q)-1)];}
  static void Drain(IEnumerator iterator){int work=0;try{while(iterator.MoveNext())Check(++work<10000,"Preparation iterator is bounded");}finally{(iterator as IDisposable)?.Dispose();}}
  static void VerifySource(){
   string path=Path.GetFullPath("../.verification-cache/Gameplay78/BaselineSources/Unity/Assets/HeartOfTheRain/M47/Runtime/EffectMeshBatcher.cs");var bytes=File.ReadAllBytes(path);report.archivedSourceSHA256=Hash(bytes);
   Check(report.archivedSourceSHA256=="5d0fc628430da9e342cb4d6c1c69229010960cac3118715a835cafa9fb8e4f7d","Exact archived77 effect batcher source");
   string original=Encoding.UTF8.GetString(bytes).Replace("\r\n","\n");original=original.Substring(original.IndexOf("namespace HeartOfTheRain.M47 {",StringComparison.Ordinal)).Trim().Replace("namespace HeartOfTheRain.M47 {","namespace HeartOfTheRain.Verification.Submission77 {").Replace("EffectMeshBatcher","ArchivedEffectMeshBatcher77");
   string own=File.ReadAllText("Assets/HeartOfTheRain/Verification/Editor/DenseSubmissionVerification.cs").Replace("\r\n","\n"),begin="\n// BEGIN EXACT77 EFFECT BATCHER\n",end="\n// END EXACT77 EFFECT BATCHER";int first=own.IndexOf(begin,StringComparison.Ordinal)+begin.Length,last=own.IndexOf(end,StringComparison.Ordinal);
   Check(first>=begin.Length&&last>first,"Independent77 compiled control region exists");var compiled=own.Substring(first,last-first).Trim();report.compiledSourceMatchesArchive=compiled==original;report.compiledBodySHA256=Hash(compiled);Check(report.compiledSourceMatchesArchive,"Independent control changes only namespace/type names");
  }
  static void Vector(BinaryWriter writer,Vector3 v){writer.Write(v.x);writer.Write(v.y);writer.Write(v.z);}
  static string MeshHash(Transform root){using(var memory=new MemoryStream())using(var writer=new BinaryWriter(memory)){
   foreach(var filter in root.GetComponentsInChildren<MeshFilter>()){var renderer=filter.GetComponent<MeshRenderer>();if(!renderer.enabled)continue;var mesh=filter.sharedMesh;writer.Write(renderer.sortingOrder);writer.Write(renderer.sharedMaterial.GetInstanceID());var block=new MaterialPropertyBlock();renderer.GetPropertyBlock(block);var texture=block.GetTexture(Shader.PropertyToID("_MainTex"));writer.Write(texture?texture.GetInstanceID():0);Vector(writer,filter.transform.localPosition);Vector(writer,mesh.bounds.center);Vector(writer,mesh.bounds.size);
    writer.Write(mesh.vertexCount);foreach(var v in mesh.vertices)Vector(writer,v);var uv=mesh.uv;writer.Write(uv.Length);foreach(var v in uv){writer.Write(v.x);writer.Write(v.y);}var colors=mesh.colors32;writer.Write(colors.Length);foreach(var c in colors){writer.Write(c.r);writer.Write(c.g);writer.Write(c.b);writer.Write(c.a);}var triangles=mesh.triangles;writer.Write(triangles.Length);foreach(int i in triangles)writer.Write(i);
   }writer.Flush();return Hash(memory.ToArray());}}
  static Input[] Inputs(M46AtlasBank bank,List<DrawSprite> draws){var result=new List<Input>();foreach(var d in draws){var sprite=bank.Get(d);if(!sprite||d.alpha<=0||d.uiOverlay||d.masked||d.glow>0)continue;result.Add(new Input{sprite=sprite,order=d.order,position=new Vector3(d.x,d.y,0),angle=d.angle,sx=d.sx,sy=d.sy,color=new Color(d.red,d.green,d.blue,d.alpha)});}return result.ToArray();}
  static void Replay(EffectMeshBatcher batch,Input[] inputs,bool control=false,int flip=-1){batch.VerificationUseCheckpoint77Submission=control;batch.Begin();for(int i=0;i<inputs.Length;i++){if(i==flip)batch.VerificationUseCheckpoint77Submission=!control;var d=inputs[i];batch.Add(d.sprite,d.order,d.position,d.angle,d.sx,d.sy,d.color);}batch.End();}
  static void Replay(Legacy batch,Input[] inputs){batch.Begin();foreach(var d in inputs)batch.Add(d.sprite,d.order,d.position,d.angle,d.sx,d.sy,d.color);batch.End();}
  static void Parity(string name,EffectMeshBatcher current,Legacy old,Transform currentRoot,Transform oldRoot,Input[] inputs,bool ordered=false,int flip=-1){
   current.KeepDrawOrder=old.KeepDrawOrder=ordered;Replay(old,inputs);string a=MeshHash(oldRoot);Replay(current,inputs,false,flip);string b=MeshHash(currentRoot);Check(a==b&&current.Quads==old.Quads&&current.Meshes==old.Meshes,"Bit-exact active prefix/order/material/texture/depth/bounds vs77: "+name);Replay(current,inputs,true,flip);string c=MeshHash(currentRoot);Check(a==c&&current.Quads==old.Quads&&current.Meshes==old.Meshes,"Same-APK old submission is exact77: "+name);
   int vertices=currentRoot.GetComponentsInChildren<MeshFilter>().Where(f=>f.GetComponent<MeshRenderer>().enabled).Sum(f=>f.sharedMesh.vertexCount);Check(vertices==inputs.Length*4,"Only active vertices uploaded after shrink/growth: "+name);report.parityFrames++;report.parityRows.Add(new ParityRow{name=name,archivedHash=a,arrayHash=b,controlHash=c,quads=current.Quads,meshes=current.Meshes,ordered=ordered});
  }
  static Input[] Varied(Input[] source){var a=(Input[])source.Clone();for(int i=0;i<a.Length;i++){a[i].angle=i%5==0?BitConverter.ToSingle(BitConverter.GetBytes(int.MinValue),0):i%5==1?.000001f:i%5==2?-135f:i%5==3?47f:0;a[i].sx*=i%3==0?-1:i%3==1?0:1.35f;a[i].sy*=i%4==0?-1:.73f;a[i].color=new Color((i%7)/6f,.64f,.21f,(i%5)/4f);}return a;}
  static void Proof(Fixture fixture){
   Input[] full=Inputs(fixture.bank,fixture.draws);Check(full.Length>0,"Actual batched pose contains effects "+fixture.name);var aRoot=new GameObject("Current78 submission").transform;var bRoot=new GameObject("Archived77 submission").transform;var bounds=new Bounds(Vector3.zero,new Vector3(64,64,2));var a=new EffectMeshBatcher(aRoot,ui.boards.effectsMaterial,bounds);var b=new Legacy(bRoot,ui.boards.effectsMaterial,bounds);
   try{var sprites=full.Select(d=>d.sprite).Distinct().ToArray();Drain(a.Prepare(sprites));Drain(b.Prepare(sprites));Check(aRoot.GetComponentsInChildren<MeshRenderer>().All(r=>!r.enabled),"Prepared slots remain invisible before input "+fixture.name);
    Parity(fixture.name+"/actual",a,b,aRoot,bRoot,full);Parity(fixture.name+"/empty",a,b,aRoot,bRoot,Array.Empty<Input>());Parity(fixture.name+"/one",a,b,aRoot,bRoot,full.Take(1).ToArray());Parity(fixture.name+"/quarter",a,b,aRoot,bRoot,full.Take(Math.Max(1,full.Length/4)).ToArray());Parity(fixture.name+"/regrow",a,b,aRoot,bRoot,full);Parity(fixture.name+"/reverse",a,b,aRoot,bRoot,full.Reverse().ToArray());var varied=Varied(full);Parity(fixture.name+"/signed_flipped_tinted",a,b,aRoot,bRoot,varied);Parity(fixture.name+"/ordered_runs",a,b,aRoot,bRoot,varied,true);
    var orders=(Input[])varied.Clone();for(int i=0;i<orders.Length;i++)orders[i].order=i%4==0?int.MinValue:i%4==1?int.MaxValue:i%4==2?-17:256;Parity(fixture.name+"/signed_orders",a,b,aRoot,bRoot,orders);
    var fallback=Enumerable.Range(0,37).Select(i=>{var d=full[i%full.Length];d.order=i;return d;}).ToArray();Parity(fixture.name+"/over32slots",a,b,aRoot,bRoot,fallback);Check(a.Meshes==37&&a.SlotCount>=37,"Demand fallback above32 retained "+fixture.name);
    var pressure=Enumerable.Repeat(full[0],700).ToArray();Parity(fixture.name+"/grow_buffers",a,b,aRoot,bRoot,pressure);Parity(fixture.name+"/shrink_after_growth",a,b,aRoot,bRoot,pressure.Take(2).ToArray());Parity(fixture.name+"/empty_after_growth",a,b,aRoot,bRoot,Array.Empty<Input>());Parity(fixture.name+"/regrow_after_empty",a,b,aRoot,bRoot,pressure);
    Parity(fixture.name+"/switch_after_Begin",a,b,aRoot,bRoot,full,false,Math.Min(1,full.Length-1));report.midFrameSwitchOwnership=true;
    a.KeepDrawOrder=b.KeepDrawOrder=false;for(int warm=0;warm<8;warm++){Replay(b,full);Replay(a,full);Replay(a,full,true);}Timing(fixture.name,a,b,full);
   }finally{a.Dispose();b.Dispose();Check(a.SlotCount==0&&a.GeometryCount==0&&b.SlotCount==0&&b.GeometryCount==0,"All submission/cache ownership released "+fixture.name);report.disposedOwnershipReleased=true;Object.DestroyImmediate(aRoot.gameObject);Object.DestroyImmediate(bRoot.gameObject);}
   report.fixtures++;
  }
  static void Timed(EffectMeshBatcher batch,Input[] inputs,bool control,List<double> add,List<double> upload,List<double> frame){batch.VerificationUseCheckpoint77Submission=control;long at=System.Diagnostics.Stopwatch.GetTimestamp();batch.Begin();foreach(var d in inputs)batch.Add(d.sprite,d.order,d.position,d.angle,d.sx,d.sy,d.color);long built=System.Diagnostics.Stopwatch.GetTimestamp();batch.End();long done=System.Diagnostics.Stopwatch.GetTimestamp();add.Add(Ms(built-at));upload.Add(Ms(done-built));frame.Add(Ms(done-at));}
  static void Timed(Legacy batch,Input[] inputs,List<double> add,List<double> upload,List<double> frame){long at=System.Diagnostics.Stopwatch.GetTimestamp();batch.Begin();foreach(var d in inputs)batch.Add(d.sprite,d.order,d.position,d.angle,d.sx,d.sy,d.color);long built=System.Diagnostics.Stopwatch.GetTimestamp();batch.End();long done=System.Diagnostics.Stopwatch.GetTimestamp();add.Add(Ms(built-at));upload.Add(Ms(done-built));frame.Add(Ms(done-at));}
  static void Timing(string name,EffectMeshBatcher a,Legacy b,Input[] input){var row=new TimingRow{name=name,pairs=64};for(int i=0;i<row.pairs;i++){
   if((i&1)==0){Timed(b,input,row.archivedAddMs,row.archivedUploadMs,row.archivedFrameMs);Timed(a,input,false,row.arrayAddMs,row.arrayUploadMs,row.arrayFrameMs);Timed(a,input,true,row.controlAddMs,row.controlUploadMs,row.controlFrameMs);}else{Timed(a,input,true,row.controlAddMs,row.controlUploadMs,row.controlFrameMs);Timed(a,input,false,row.arrayAddMs,row.arrayUploadMs,row.arrayFrameMs);Timed(b,input,row.archivedAddMs,row.archivedUploadMs,row.archivedFrameMs);}
   if(row.arrayFrameMs[i]>row.archivedFrameMs[i])row.currentSlowerPairs++;if(row.arrayFrameMs[i]>row.controlFrameMs[i])row.controlSlowerPairs++;
   }row.archivedAddMedianMs=Quantile(row.archivedAddMs,.5);row.arrayAddMedianMs=Quantile(row.arrayAddMs,.5);row.controlAddMedianMs=Quantile(row.controlAddMs,.5);row.archivedUploadMedianMs=Quantile(row.archivedUploadMs,.5);row.arrayUploadMedianMs=Quantile(row.arrayUploadMs,.5);row.controlUploadMedianMs=Quantile(row.controlUploadMs,.5);row.archivedFrameMedianMs=Quantile(row.archivedFrameMs,.5);row.arrayFrameMedianMs=Quantile(row.arrayFrameMs,.5);row.controlFrameMedianMs=Quantile(row.controlFrameMs,.5);row.archivedFrameP95Ms=Quantile(row.archivedFrameMs,.95);row.arrayFrameP95Ms=Quantile(row.arrayFrameMs,.95);row.controlFrameP95Ms=Quantile(row.controlFrameMs,.95);report.timings.Add(row);}
  static List<DrawSprite> Peak(M46AtlasBank bank,List<BoardStep> queue,LevelData level){var view=CrateBurstVerification.View(ui,level.columns,level.rows);List<DrawSprite> peak=null;int most=-1;float start=0;foreach(var step in queue){view.Add(step,start);for(float age=0;age<=step.duration+.00001f;age+=.05f){var draws=view.SampleLive(step,step.before,start+age,start);int count=draws.Count(d=>!d.masked&&!d.uiOverlay&&d.glow<=0&&d.alpha>0);if(count>most){most=count;peak=draws.Select(d=>d.Copy()).ToList();}}start+=step.duration;}return peak;}
  static Fixture Build(string name,LevelData level,bool fixedAge){var board=new BoardModel(level);var initial=board.Snapshot();var turn=ObstacleDensityFixture.Solve(board);Check(turn.accepted,"Native density command accepted "+name);var steps=BoardPlayback.Build(turn.steps,level);var bank=new M46AtlasBank(ui.boards);CrateBurstVerification.Warm(bank,initial);var texture=typeof(M46AtlasBank).GetMethod("Texture",BindingFlags.Instance|BindingFlags.NonPublic);foreach(var path in bank.RequiredResources(steps))texture.Invoke(bank,new object[]{null,path});List<DrawSprite> draws;
   if(fixedAge){var view=CrateBurstVerification.View(ui,level.columns,level.rows);float start=0;BoardStep phase=null;foreach(var step in steps){view.Add(step,start);if(step.kind=="powerFall"){phase=step;break;}start+=step.duration;}Check(phase!=null&&phase.duration>=2.5761447f,"Actual frozen phase contains requested age "+name);draws=view.Sample(phase,phase.before,start+2.5761447f,start);}else draws=Peak(bank,steps,level);return new Fixture{name=name,level=level,bank=bank,draws=draws};}
  static Color32[] Plate(Fixture fixture,int mode,string name,bool varied=false){var root=new GameObject(name);root.transform.position=new Vector3(1000,0,0);var active=RenderTexture.active;var target=new RenderTexture(report.width,report.height,24);Material body=null;EffectMeshBatcher current=null;Legacy old=null;
   try{var cam=new GameObject("Camera").AddComponent<Camera>();cam.transform.SetParent(root.transform,false);cam.transform.localPosition=new Vector3((fixture.level.columns-1)*.5f,(fixture.level.rows-1)*.5f,-10);cam.orthographic=true;cam.orthographicSize=BoardPresentation.CameraHalfHeight(fixture.level.columns,fixture.level.rows,(float)report.width/report.height);cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=new Color(.035f,.05f,.07f);cam.targetTexture=target;body=new Material(ui.bodyShader?ui.bodyShader:Shader.Find("Sprites/Default"));var bounds=new Bounds(new Vector3((fixture.level.columns-1)*.5f,(fixture.level.rows-1)*.5f,0),new Vector3(fixture.level.columns+16,fixture.level.rows+20,2));
    if(mode==0){old=new Legacy(root.transform,ui.boards.effectsMaterial,bounds);Drain(old.Prepare(fixture.bank.CachedEffectSpritesSnapshot()));old.Begin();}else{current=new EffectMeshBatcher(root.transform,ui.boards.effectsMaterial,bounds){VerificationUseCheckpoint77Submission=mode==2};Drain(current.Prepare(fixture.bank.CachedEffectSpritesSnapshot()));current.Begin();}
    int index=0;foreach(var original in fixture.draws){var d=original.Copy();if(varied&&!d.masked){d.angle=index%3==0?-35:index%3==1?0:117;d.sx*=index%5==0?-1:1.18f;d.sy*=index%4==0?-1:.79f;d.red=.35f;d.green=.8f;d.alpha*=.64f;}index++;var sprite=fixture.bank.Get(d);if(!sprite||d.alpha<=0||d.uiOverlay)continue;if(!d.masked&&d.glow<=0){if(old!=null)old.Add(sprite,d.order,new Vector3(d.x,d.y,0),d.angle,d.sx,d.sy,new Color(d.red,d.green,d.blue,d.alpha));else current.Add(sprite,d.order,new Vector3(d.x,d.y,0),d.angle,d.sx,d.sy,new Color(d.red,d.green,d.blue,d.alpha));continue;}var sr=new GameObject(d.key).AddComponent<SpriteRenderer>();sr.transform.SetParent(root.transform,false);sr.transform.localPosition=new Vector3(d.x,d.y,0);sr.transform.localScale=new Vector3(d.sx,d.sy,1);sr.transform.localRotation=Quaternion.Euler(0,0,d.angle);sr.sprite=sprite;sr.sharedMaterial=body;sr.sortingOrder=d.order;sr.color=new Color(d.red,d.green,d.blue,d.alpha);}
    old?.End();current?.End();cam.Render();RenderTexture.active=target;var pixels=new Texture2D(report.width,report.height,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,report.width,report.height),0,0);pixels.Apply();File.WriteAllBytes(Path.Combine(output,name),pixels.EncodeToPNG());report.frames.Add(name);var result=pixels.GetPixels32();Object.DestroyImmediate(pixels);return result;
   }finally{RenderTexture.active=active;old?.Dispose();current?.Dispose();Object.DestroyImmediate(root);if(body)Object.DestroyImmediate(body);Object.DestroyImmediate(target);}}
  static void Pixels(Fixture fixture,bool varied){var a=Plate(fixture,0,varied?"Transforms77.png":"Dense77.png",varied);var b=Plate(fixture,1,varied?"Transforms78.png":"Dense78.png",varied);var c=Plate(fixture,2,varied?"TransformsControl.png":"DenseControl.png",varied);int count=0,max=0,controlCount=0;for(int i=0;i<a.Length;i++){int d=Math.Max(Math.Max(Math.Abs(a[i].r-b[i].r),Math.Abs(a[i].g-b[i].g)),Math.Max(Math.Abs(a[i].b-b[i].b),Math.Abs(a[i].a-b[i].a)));if(d!=0)count++;max=Math.Max(max,d);if(a[i].r!=c[i].r||a[i].g!=c[i].g||a[i].b!=c[i].b||a[i].a!=c[i].a)controlCount++;}Check(controlCount==0,"Every same-APK77 control pixel channel matches");Check(count==0&&max==0,"Every native archived77/current pixel channel matches");report.pixelRows.Add(new PixelRow{name=varied?"rotated_flipped_scaled_tinted":"actual_dense",differingPixels=count,maxChannelDelta=max});}
  static void NegativeControl(){var root=new GameObject("Signature sensitivity").transform;var mesh=new Mesh();var filter=root.gameObject.AddComponent<MeshFilter>();filter.sharedMesh=mesh;var renderer=root.gameObject.AddComponent<MeshRenderer>();renderer.sharedMaterial=ui.boards.effectsMaterial;mesh.vertices=new[]{Vector3.right,new Vector3(2,0,0),Vector3.up};mesh.triangles=new[]{0,1,2};string before=MeshHash(root);var vertices=mesh.vertices;vertices[0].x=BitConverter.ToSingle(BitConverter.GetBytes(BitConverter.ToInt32(BitConverter.GetBytes(1f),0)+1),0);mesh.vertices=vertices;Check(before!=MeshHash(root),"Uploaded signature rejects a one-ULP geometry change");report.negativeControls++;Object.DestroyImmediate(mesh);Object.DestroyImmediate(root.gameObject);}
  static void Dispose(M46AtlasBank bank){var cache=(IDictionary)typeof(M46AtlasBank).GetField("sprites",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(bank);foreach(var entry in cache.Values){var sprite=(Sprite)entry.GetType().GetField("sprite").GetValue(entry);if(sprite)Object.DestroyImmediate(sprite);}cache.Clear();bank.Dispose();}
  public static void Run(){report=new Report{utc=DateTime.UtcNow.ToString("o"),unity=Application.unityVersion};string folder=Environment.GetEnvironmentVariable("HOTR_GAMEPLAY78_OUTPUT");if(string.IsNullOrEmpty(folder))folder=Path.GetFullPath("../Verification/Evidence/Gameplay78");output=Path.Combine(folder,"Native","DenseSubmission","Artifacts");Directory.CreateDirectory(output);bool transform=EffectMeshBatcher.VerificationUseCheckpoint75Transform;EffectMeshBatcher.VerificationUseCheckpoint75Transform=false;
   try{VerifySource();ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");Check(ui!=null,"Approved native UI/board binding");var source=JsonUtility.FromJson<LevelData>(ui.boards.levels[25].text);
    foreach(var family in ObstacleDensityFixture.Families){var f=Build("peak_"+family+"_45",ObstacleDensityFixture.Level(source,45,family),false);try{Proof(f);if(family=="stone"){Pixels(f,false);Pixels(f,true);}}finally{Dispose(f.bank);}}
    var authored=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[41].text));var initial=authored.Snapshot();var t=CrateBurstVerification.Solve(authored,"double_orb");Check(t.accepted,"Authored level42 Double Orb accepted");var q=BoardPlayback.Build(t.steps,authored.Level);var bank=new M46AtlasBank(ui.boards);try{CrateBurstVerification.Warm(bank,initial);var texture=typeof(M46AtlasBank).GetMethod("Texture",BindingFlags.Instance|BindingFlags.NonPublic);foreach(var path in bank.RequiredResources(q))texture.Invoke(bank,new object[]{null,path});Proof(new Fixture{name="authored42_double_orb",level=authored.Level,bank=bank,draws=Peak(bank,q,authored.Level)});}finally{Dispose(bank);}
    foreach(string family in new[]{"crate","stone"})foreach(int count in new[]{1,45}){var f=Build("frozen_"+family+"_"+count,ObstacleDensityFixture.Level(source,count,family),true);try{Proof(f);}finally{Dispose(f.bank);}}
    NegativeControl();Check(report.fixtures==9&&report.parityFrames==135&&report.timings.Count==9&&report.pixelRows.Count==2,"All nine poses/135 upload states/two strict pixel rows/nine raw timing rows completed");report.status="PASS_NATIVE_DENSE_SUBMISSION78";
   }catch(Exception e){report.status="FAIL_NATIVE_DENSE_SUBMISSION78";report.error=e.ToString();}finally{EffectMeshBatcher.VerificationUseCheckpoint75Transform=transform;}
   File.WriteAllText(Path.Combine(folder,"Native","DenseSubmission.json"),JsonUtility.ToJson(report,true));EditorApplication.Exit(report.error==null?0:1);
  }
 }
}

// BEGIN EXACT77 EFFECT BATCHER
namespace HeartOfTheRain.Verification.Submission77 {
    // Draws one frame's unmasked, non-glow effect sprites (fragments, accents,
    // tile breaks, power clips) as a few procedural meshes instead of one
    // SpriteRenderer each. Geometry, UVs, material, sorting order and colour
    // match the SpriteRenderer path exactly; one mesh per texture page and
    // sorting order, so a dense burst costs a handful of renderers instead
    // of hundreds.
    public sealed class ArchivedEffectMeshBatcher77 {
        // Preparation is bounded; later effects still grow through the same
        // demand path. Leave headroom under the existing 4,096-entry cache flush.
        public const int PreparedGeometryLimit=2048,PreparedSlotReserve=32;
        // Verification only: one mesh per contiguous run instead of per page,
        // which keeps exact list order at the cost of many more meshes.
        public bool KeepDrawOrder;
        sealed class Slot {
            public GameObject node;public MeshFilter filter;public MeshRenderer renderer;public Mesh mesh;public MaterialPropertyBlock block;
            public Texture2D texture;public int order=int.MinValue,indexCount;public bool enabled;
            public readonly List<Vector3> vertices=new List<Vector3>(512);public readonly List<Vector2> uvs=new List<Vector2>(512);
            public readonly List<Color32> colors=new List<Color32>(512);public readonly List<int> triangles=new List<int>(768);
        }
        // A sprite's quad in its own units, as SpriteRenderer builds it: rect
        // corners relative to the pivot, divided by pixels per unit.
        sealed class SpriteGeometry {public Texture2D texture;public int textureId;public float left,right,bottom,top;public Vector2 uvMin,uvMax;}
        static readonly int MainTexture=Shader.PropertyToID("_MainTex");
        readonly Transform root;readonly Material material;readonly Bounds bounds;
        readonly List<Slot> slots=new List<Slot>();readonly Dictionary<Sprite,SpriteGeometry> geometry=new Dictionary<Sprite,SpriteGeometry>();
        // One mesh per (texture, sorting order) per frame, in order of first
        // appearance. Within a mesh the quads keep draw order; sprites that
        // share a sorting order but not a texture page compose in page order,
        // which the SpriteRenderer path never defined either.
        readonly Dictionary<long,Slot> open=new Dictionary<long,Slot>();
        Slot current;long currentKey;int used;
        public int Quads {get;private set;}
        public int Meshes=>used;
        public int SlotCount=>slots.Count;
        public int GeometryCount=>geometry.Count;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        // Same-APK verification only; ordinary/release drawing uses the exact
        // zero-angle shortcut below. Never alter counts, geometry or quality.
        public static bool VerificationUseCheckpoint75Transform;
        public int GeometryMisses {get;private set;}
        public int SlotCreates {get;private set;}
        public int PreparedGeometryCount {get;private set;}
        public int PreparedSlotCount {get;private set;}
        public int PreparationBatches {get;private set;}
        public int PreparationYields {get;private set;}
        public double PreparationMilliseconds {get;private set;}
        public double PreparationMaxBatchMilliseconds {get;private set;}
#endif
        public ArchivedEffectMeshBatcher77(Transform root,Material material,Bounds bounds){this.root=root;this.material=material;this.bounds=bounds;}
        public void Begin(){
            used=0;current=null;currentKey=0;Quads=0;open.Clear();
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            GeometryMisses=SlotCreates=0;
#endif
            // Sprites the bank evicted stay as keys; bound the cache instead of tracking them.
            if(geometry.Count>4096)geometry.Clear();
        }
        SpriteGeometry Geometry(Sprite sprite){
            SpriteGeometry g;
            if(!geometry.TryGetValue(sprite,out g)){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                GeometryMisses++;
#endif
                var rect=sprite.textureRect;var texture=sprite.texture;float ppu=sprite.pixelsPerUnit;var pivot=sprite.pivot;
                g=new SpriteGeometry{texture=texture,textureId=texture.GetInstanceID(),left=-pivot.x/ppu,right=(rect.width-pivot.x)/ppu,bottom=-pivot.y/ppu,top=(rect.height-pivot.y)/ppu,
                    uvMin=new Vector2(rect.xMin/texture.width,rect.yMin/texture.height),uvMax=new Vector2(rect.xMax/texture.width,rect.yMax/texture.height)};
                geometry.Add(sprite,g);
            }
            return g;
        }
        // The bank has already copied these references before this iterator can
        // yield. Reading quad geometry never requests a texture or changes its
        // residency. Actual work, rather than a fixed frame count, gates readiness.
        public IEnumerator Prepare(Sprite[] cachedSprites,int reserve=PreparedSlotReserve,double budgetMilliseconds=2){
            int count=cachedSprites==null?0:System.Math.Min(PreparedGeometryLimit,cachedSprites.Length);
            reserve=System.Math.Max(0,reserve);budgetMilliseconds=System.Math.Max(.1,budgetMilliseconds);
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            int geometryBefore=geometry.Count,slotsBefore=slots.Count;
            PreparedGeometryCount=PreparedSlotCount=PreparationBatches=PreparationYields=0;
            PreparationMilliseconds=PreparationMaxBatchMilliseconds=0;
#endif
            var watch=System.Diagnostics.Stopwatch.StartNew();bool worked=false;
            for(int i=0;i<count;i++){
                var sprite=cachedSprites[i];
                if(sprite!=null&&(geometry.Count<PreparedGeometryLimit||geometry.ContainsKey(sprite))){Geometry(sprite);worked=true;}
                if(worked&&(i+1<count||slots.Count<reserve)&&watch.Elapsed.TotalMilliseconds>=budgetMilliseconds){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    RecordPreparationBatch(watch.Elapsed.TotalMilliseconds);PreparationYields++;
#endif
                    yield return null;watch.Restart();worked=false;
                }
            }
            while(slots.Count<reserve){
                CreateSlot();worked=true;
                if(slots.Count<reserve&&watch.Elapsed.TotalMilliseconds>=budgetMilliseconds){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
                    RecordPreparationBatch(watch.Elapsed.TotalMilliseconds);PreparationYields++;
#endif
                    yield return null;watch.Restart();worked=false;
                }
            }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            if(worked)RecordPreparationBatch(watch.Elapsed.TotalMilliseconds);
            PreparedGeometryCount=geometry.Count-geometryBefore;PreparedSlotCount=slots.Count-slotsBefore;
#endif
        }
        // Accepted-turn prefetch can prepare newly resident power frames while
        // earlier swap/merge poses play. Keep the existing preparation bound;
        // demand rendering remains responsible for anything outside it.
        public void PrepareSprite(Sprite sprite){
            if(sprite!=null&&(geometry.Count<PreparedGeometryLimit||geometry.ContainsKey(sprite)))Geometry(sprite);
        }
#if UNITY_EDITOR || DEVELOPMENT_BUILD
        void RecordPreparationBatch(double milliseconds){PreparationBatches++;PreparationMilliseconds+=milliseconds;PreparationMaxBatchMilliseconds=System.Math.Max(PreparationMaxBatchMilliseconds,milliseconds);}
#endif
        public void Add(Sprite sprite,int order,Vector3 position,float angle,float sx,float sy,Color color){
            var g=Geometry(sprite);
            // Same page/order grouping as before; the immutable texture ID was
            // already read when this sprite's geometry was cached.
            long key=((long)g.textureId<<32)^(uint)order;
            if(current==null||currentKey!=key){
                if(KeepDrawOrder)current=Open(g.texture,order);
                else if(!open.TryGetValue(key,out current)){current=Open(g.texture,order);open.Add(key,current);}
                currentKey=key;
            }
            // Exact zero alone avoids two engine trigonometry calls. Retain
            // signed-zero sine and the original vertex arithmetic/order.
            float radians=angle*Mathf.Deg2Rad,cos=1,sin=radians;bool rotate=angle!=0;
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            rotate|=VerificationUseCheckpoint75Transform;
#endif
            if(rotate){cos=Mathf.Cos(radians);sin=Mathf.Sin(radians);}
            float l=g.left*sx,r=g.right*sx,b=g.bottom*sy,t=g.top*sy;int v=current.vertices.Count;
            current.vertices.Add(new Vector3(position.x+l*cos-b*sin,position.y+l*sin+b*cos,0));
            current.vertices.Add(new Vector3(position.x+l*cos-t*sin,position.y+l*sin+t*cos,0));
            current.vertices.Add(new Vector3(position.x+r*cos-t*sin,position.y+r*sin+t*cos,0));
            current.vertices.Add(new Vector3(position.x+r*cos-b*sin,position.y+r*sin+b*cos,0));
            current.uvs.Add(new Vector2(g.uvMin.x,g.uvMin.y));current.uvs.Add(new Vector2(g.uvMin.x,g.uvMax.y));current.uvs.Add(new Vector2(g.uvMax.x,g.uvMax.y));current.uvs.Add(new Vector2(g.uvMax.x,g.uvMin.y));
            Color32 c=color;current.colors.Add(c);current.colors.Add(c);current.colors.Add(c);current.colors.Add(c);
            // Quad topology is an immutable prefix. Grow its retained high-water
            // list only when this slot has more quads than on any earlier frame.
            if(current.indexCount==current.triangles.Count){
                current.triangles.Add(v);current.triangles.Add(v+1);current.triangles.Add(v+2);current.triangles.Add(v);current.triangles.Add(v+2);current.triangles.Add(v+3);
            }
            current.indexCount+=6;
            Quads++;
        }
        Slot CreateSlot(){
#if UNITY_EDITOR || DEVELOPMENT_BUILD
            SlotCreates++;
#endif
                var slot=new Slot{node=new GameObject("Effect mesh "+slots.Count)};slot.node.transform.SetParent(root,false);
                slot.filter=slot.node.AddComponent<MeshFilter>();slot.renderer=slot.node.AddComponent<MeshRenderer>();
                slot.mesh=new Mesh{name="Effect mesh"};slot.mesh.MarkDynamic();slot.mesh.bounds=bounds;slot.filter.sharedMesh=slot.mesh;
                slot.renderer.sharedMaterial=material;slot.renderer.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;slot.renderer.receiveShadows=false;
                slot.renderer.lightProbeUsage=UnityEngine.Rendering.LightProbeUsage.Off;slot.renderer.reflectionProbeUsage=UnityEngine.Rendering.ReflectionProbeUsage.Off;slot.renderer.motionVectorGenerationMode=MotionVectorGenerationMode.ForceNoMotion;
                slot.block=new MaterialPropertyBlock();slot.renderer.enabled=false;slots.Add(slot);return slot;
        }
        Slot Open(Texture2D texture,int order){
            var slot=used<slots.Count?slots[used]:CreateSlot();
            // Later runs sit a hair nearer the orthographic camera so equal
            // sorting orders still draw in list order.
            slot.node.transform.localPosition=new Vector3(0,0,-.001f*(used+1));
            if(slot.texture!=texture){slot.texture=texture;slot.block.SetTexture(MainTexture,texture);slot.renderer.SetPropertyBlock(slot.block);}
            if(slot.order!=order){slot.order=order;slot.renderer.sortingOrder=order;}
            slot.vertices.Clear();slot.uvs.Clear();slot.colors.Clear();slot.indexCount=0;
            used++;return slot;
        }
        public void End(){
            for(int i=0;i<used;i++){
                var slot=slots[i];var mesh=slot.mesh;mesh.Clear(false);
                mesh.SetVertices(slot.vertices);mesh.SetUVs(0,slot.uvs);mesh.SetColors(slot.colors);mesh.SetTriangles(slot.triangles,0,slot.indexCount,0,false,0);mesh.bounds=bounds;
                if(!slot.enabled){slot.renderer.enabled=true;slot.enabled=true;}
            }
            for(int i=used;i<slots.Count;i++)if(slots[i].enabled){slots[i].renderer.enabled=false;slots[i].enabled=false;}
        }
        public void Dispose(){
            foreach(var slot in slots){if(slot.mesh)Object.Destroy(slot.mesh);if(slot.node)Object.Destroy(slot.node);}
            slots.Clear();geometry.Clear();used=0;current=null;Quads=0;
        }
    }
}
// END EXACT77 EFFECT BATCHER
#endif

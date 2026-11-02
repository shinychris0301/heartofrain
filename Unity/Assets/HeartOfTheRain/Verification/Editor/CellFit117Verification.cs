#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 public static class CellFit117Verification {
  [Serializable] class Report {public string status,error="",scope="Unity Editor pixel-alpha and offscreen GPU checks; synthetic 9/10/11-column boards, not physical device or production level/mask validation.";public int checks;public float[] gemRadius,obstacleRadius;public string[] frames;}
  public static void Run(){
   string output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_CELL_FIT117_OUTPUT")??"../Verification/Evidence/Review117/CellFit");Directory.CreateDirectory(output);var report=new Report();M46AtlasBank bank=null;GameObject root=null;Material material=null;RenderTexture target=null;Texture2D background=null,maskTexture=null;Sprite backgroundSprite=null,maskSprite=null;
   void Check(bool v,string m){report.checks++;if(!v)throw new Exception(m);}
   try{
    var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");Check(ui&&ui.boards,"Live board assets available");bank=new M46AtlasBank(ui.boards);material=new Material(ui.bodyShader?ui.bodyShader:Shader.Find("Sprites/Default"));
    var extent=new Dictionary<string,Vector2>();var keys=Enumerable.Range(0,6).Select(i=>"tile"+i).Concat(new[]{"crate_1","moss_1"}).ToArray();
    foreach(var key in keys){
     var body=ui.boards.bodies.Single(b=>b.key==key);string path="Assets/HeartOfTheRain/M48/Resources/"+body.resource+".png";var tex=new Texture2D(2,2,TextureFormat.RGBA32,false);Check(tex.LoadImage(File.ReadAllBytes(path)),"Read original approved artwork "+key);
     var pixels=tex.GetPixels32();float ex=0,ey=0;for(int y=0;y<tex.height;y++)for(int x=0;x<tex.width;x++)if(pixels[y*tex.width+x].a>0){ex=Mathf.Max(ex,Mathf.Abs((x+.5f)/tex.width-.5f)+.5f/tex.width);ey=Mathf.Max(ey,Mathf.Abs((y+.5f)/tex.height-.5f)+.5f/tex.height);}
     var sprite=bank.Get(new DrawSprite{bank="body",key=key});extent[key]=new Vector2(ex*sprite.bounds.size.x,ey*sprite.bounds.size.y);UnityEngine.Object.DestroyImmediate(tex);Check(extent[key].x>0&&extent[key].y>0,"Artwork has nonempty alpha "+key);
    }
    report.gemRadius=Enumerable.Range(0,6).Select(i=>Mathf.Max(extent["tile"+i].x,extent["tile"+i].y)).ToArray();report.obstacleRadius=new[]{Mathf.Max(extent["crate_1"].x,extent["crate_1"].y),Mathf.Max(extent["moss_1"].x,extent["moss_1"].y)};
    foreach(float r in report.gemRadius)Check(r<=.4501f&&r>=.445f,"Full nonzero gem alpha fits and uses the planned visible envelope");foreach(float r in report.obstacleRadius)Check(r<=.5001f,"Stationary obstacle footprint fits");
    var fit=typeof(BoardPresentation).GetMethod("FitGemToCell",BindingFlags.NonPublic|BindingFlags.Static);
    void Bounded(DrawSprite d,string context,float offsetX=0,float offsetY=0){var e=extent[d.key];float angle=d.angle*Mathf.Deg2Rad,c=Mathf.Abs(Mathf.Cos(angle)),s=Mathf.Abs(Mathf.Sin(angle));float x=e.x*Mathf.Abs(d.sx)*c+e.y*Mathf.Abs(d.sy)*s,y=e.x*Mathf.Abs(d.sx)*s+e.y*Mathf.Abs(d.sy)*c;Check(x+Mathf.Abs(offsetX)<=.5001f&&y+Mathf.Abs(offsetY)<=.5001f,context+" "+d.key);}
    foreach(var key in keys.Take(6))foreach(float angle in new[]{0f,12f,-12f,45f,90f})foreach(float scale in new[]{1f,1.14f}){var d=new DrawSprite{key=key,sx=scale,sy=scale,angle=angle};fit.Invoke(null,new object[]{d});Bounded(d,"Rotated/stretched footprint");}
    var frameNames=new List<string>();
    foreach(int columns in new[]{9,10,11}){
     var pieces=new List<Piece>();int id=1;for(int y=0;y<9;y++)for(int x=0;x<columns;x++){if((x==1||x==columns-2)&&y==8)continue;pieces.Add(new Piece{id=id++,x=x,y=y,family=(x==4&&y==4)?"crate":(x==5&&y==4)?"moss":"gem",hp=1,color=(x+2*y)%6});}
     var before=new BoardSnapshot{pieces=pieces.ToArray(),goals=Array.Empty<Goal>()};var after=new BoardSnapshot{pieces=pieces.Select(p=>{var q=p.Copy();if(q.family=="gem")q.color=(q.color+1)%6;return q;}).ToArray(),goals=Array.Empty<Goal>()};var view=new BoardPresentation{columns=columns,rows=9};
     var idle=view.Sample(null,before,0,0);foreach(var d in idle.Where(d=>d.bank=="body"&&extent.ContainsKey(d.key)))Bounded(d,"Static "+columns);
     var shuffle=new BoardStep{kind="shuffle",duration=.45f,before=before,after=after};
     for(int j=0;j<=40;j++){float t=shuffle.duration*j/40;foreach(var d in view.Sample(shuffle,before,t,0).Where(d=>d.key!=null&&d.key.StartsWith("tile",StringComparison.Ordinal))){var original=before.pieces.Single(p=>p.id==d.pieceId);Bounded(d,"Shuffle "+columns,d.x-original.x,d.y-original.y);}}
     var moving=pieces.First(p=>p.family=="gem"&&p.y==2);var gravity=new BoardStep{kind="gravity",duration=.5f,before=before,after=before};gravity.motion.Add(new HeartOfTheRain.M46.Motion{id=moving.id,fromX=moving.x,fromY=moving.y,toX=moving.x,toY=moving.y-1,seconds=.3f,landing=.15f});
     for(int j=0;j<=40;j++){var d=view.Sample(gravity,before,.5f*j/40,0).First(v=>v.pieceId==moving.id);Bounded(d,"Fall footprint around moving center "+columns);}
     // Draw a synthetic full-coverage checkerboard and mask with two holes;
     // preserve real sprite artwork and the real presentation transforms.
     root=new GameObject("CellFit synthetic board "+columns);root.transform.position=new Vector3(1000,0,0);int w=columns*64,h=9*64;var bg=new Color32[w*h];var mk=new Color32[w*h];
     for(int y=0;y<h;y++)for(int x=0;x<w;x++){int cx=x/64,cy=y/64;bool active=!((cx==1||cx==columns-2)&&cy==8);byte c=(byte)(((cx+cy)%2==0)?65:77);bg[y*w+x]=new Color32(c,(byte)(c+16),(byte)(c+34),(byte)(active?255:0));mk[y*w+x]=new Color32(255,255,255,(byte)(active?255:0));}
     background=new Texture2D(w,h,TextureFormat.RGBA32,false);background.SetPixels32(bg);background.Apply();maskTexture=new Texture2D(w,h,TextureFormat.RGBA32,false);maskTexture.SetPixels32(mk);maskTexture.Apply();backgroundSprite=Sprite.Create(background,new Rect(0,0,w,h),new Vector2(.5f,.5f),64);maskSprite=Sprite.Create(maskTexture,new Rect(0,0,w,h),new Vector2(.5f,.5f),64);
     var center=new Vector3((columns-1)*.5f,4,0);var bgObj=new GameObject("Synthetic complete cell backgrounds");bgObj.transform.SetParent(root.transform,false);bgObj.transform.localPosition=center;var bgr=bgObj.AddComponent<SpriteRenderer>();bgr.sprite=backgroundSprite;bgr.sharedMaterial=material;bgr.sortingOrder=0;
     var mObj=new GameObject("Synthetic cell mask");mObj.transform.SetParent(root.transform,false);mObj.transform.localPosition=center;var mask=mObj.AddComponent<SpriteMask>();mask.sprite=maskSprite;mask.isCustomRangeActive=true;mask.frontSortingOrder=15;mask.backSortingOrder=5;
     foreach(var d in idle.Where(d=>d.masked)){var sprite=bank.Get(d);Check(sprite!=null,"Sprite resolved for render");var go=new GameObject("Tile "+d.pieceId);go.transform.SetParent(root.transform,false);go.transform.localPosition=new Vector3(d.x,d.y,0);go.transform.localScale=new Vector3(d.sx,d.sy,1);go.transform.localRotation=Quaternion.Euler(0,0,d.angle);var sr=go.AddComponent<SpriteRenderer>();sr.sprite=sprite;sr.sharedMaterial=material;sr.sortingOrder=d.order;sr.maskInteraction=SpriteMaskInteraction.VisibleInsideMask;}
     var cameraObj=new GameObject("Synthetic board camera");cameraObj.transform.SetParent(root.transform,false);var camera=cameraObj.AddComponent<Camera>();camera.orthographic=true;camera.orthographicSize=BoardPresentation.CameraHalfHeight(columns,9,720f/1280f);camera.transform.localPosition=new Vector3(center.x,center.y,-10);camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.035f,.05f,.07f);target=new RenderTexture(720,1280,24);camera.targetTexture=target;camera.Render();RenderTexture.active=target;var capture=new Texture2D(720,1280,TextureFormat.RGBA32,false);capture.ReadPixels(new Rect(0,0,720,1280),0,0);capture.Apply();string name="Synthetic_"+columns+"x9.png";File.WriteAllBytes(Path.Combine(output,name),capture.EncodeToPNG());frameNames.Add(name);UnityEngine.Object.DestroyImmediate(capture);
     RenderTexture.active=null;UnityEngine.Object.DestroyImmediate(root);root=null;UnityEngine.Object.DestroyImmediate(target);target=null;UnityEngine.Object.DestroyImmediate(backgroundSprite);backgroundSprite=null;UnityEngine.Object.DestroyImmediate(maskSprite);maskSprite=null;UnityEngine.Object.DestroyImmediate(background);background=null;UnityEngine.Object.DestroyImmediate(maskTexture);maskTexture=null;
    }
    report.frames=frameNames.ToArray();report.status="PASS_CELL_FIT117";
   }catch(Exception e){report.status="FAIL_CELL_FIT117";report.error=e.ToString();}
   finally{RenderTexture.active=null;if(root)UnityEngine.Object.DestroyImmediate(root);if(target)UnityEngine.Object.DestroyImmediate(target);if(material)UnityEngine.Object.DestroyImmediate(material);if(backgroundSprite)UnityEngine.Object.DestroyImmediate(backgroundSprite);if(maskSprite)UnityEngine.Object.DestroyImmediate(maskSprite);if(background)UnityEngine.Object.DestroyImmediate(background);if(maskTexture)UnityEngine.Object.DestroyImmediate(maskTexture);if(bank!=null)bank.Dispose();File.WriteAllText(Path.Combine(output,"CellFit117.json"),JsonUtility.ToJson(report,true));}
   EditorApplication.Exit(report.status=="PASS_CELL_FIT117"?0:1);
  }
 }
}
#endif

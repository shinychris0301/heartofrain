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
 public static class ReshuffleVisual117Verification {
  [Serializable] sealed class Report {
   public string status,error="",scope="Unity Editor offscreen GPU render of real BoardModel.Shuffle and BoardPresentation samples on authored irregular level 5. Shuffle is forced, not naturally reached. No Android, device, full gameplay capture or performance claim.";
   public int level=5,columns,rows,activeCells,obstacles,changedColors,checks;public string[] frames;public int[] changedPixels;
  }
  public static void Run(){
   string output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_RESHUFFLE_VISUAL117_OUTPUT")??"../Verification/Evidence/Review117/ReshuffleVisual");Directory.CreateDirectory(output);
   var report=new Report();M46AtlasBank bank=null;GameObject root=null;RenderTexture target=null;Material material=null;var sprites=new List<GameObject>();
   void Check(bool ok,string name){report.checks++;if(!ok)throw new Exception(name);}
   try{
    var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");Check(ui&&ui.boards&&ui.boards.levels.Length>=5,"Campaign assets available");
    var level=JsonUtility.FromJson<LevelData>(ui.boards.levels[4].text);var board=new BoardModel(level);var result=new TurnResult();
    report.columns=level.columns;report.rows=level.rows;report.activeCells=level.activeCells.Length;report.obstacles=board.Pieces.Values.Count(p=>p.family!="gem"&&p.family!="power");
    Check(level.globalLevel==5&&report.activeCells<level.columns*level.rows&&report.obstacles>0,"Real irregular level with obstacles");
    typeof(BoardModel).GetMethod("Shuffle",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(board,new object[]{result});
    Check(result.steps.Count==1&&result.steps[0].kind=="shuffle"&&board.LegalSwaps().Count>0,"Actual model produces a playable shuffle");
    var step=result.steps[0];report.changedColors=step.before.pieces.Count(p=>p.family=="gem"&&step.after.pieces.Single(q=>q.id==p.id).color!=p.color);Check(report.changedColors>0,"Real shuffle changes tile colors");
    var presentation=new BoardPresentation{columns=level.columns,rows=level.rows};
    bank=new M46AtlasBank(ui.boards);material=new Material(ui.bodyShader?ui.bodyShader:Shader.Find("Sprites/Default"));root=new GameObject("Reshuffle117 render fixture");root.transform.position=new Vector3(1000,0,0);
    var camObj=new GameObject("Fixture camera");camObj.transform.SetParent(root.transform,false);var camera=camObj.AddComponent<Camera>();camera.orthographic=true;camera.orthographicSize=BoardPresentation.CameraHalfHeight(level.columns,level.rows,720f/1280f);camera.transform.localPosition=new Vector3((level.columns-1)*.5f,(level.rows-1)*.5f,-10);camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.035f,.05f,.07f);target=new RenderTexture(720,1280,24);camera.targetTexture=target;
    var maskObj=new GameObject("Authored active-cell mask");maskObj.transform.SetParent(root.transform,false);maskObj.transform.localPosition=new Vector3((level.columns-1)*.5f,(level.rows-1)*.5f,0);var mask=maskObj.AddComponent<SpriteMask>();mask.sprite=bank.BoardMask(4);mask.isCustomRangeActive=true;mask.frontSortingOrder=15;mask.backSortingOrder=5;
    var surfaceObj=new GameObject("Authored board surface");surfaceObj.transform.SetParent(root.transform,false);surfaceObj.transform.localPosition=maskObj.transform.localPosition;var surface=surfaceObj.AddComponent<SpriteRenderer>();surface.sharedMaterial=material;surface.sprite=bank.BoardSurface(4);surface.sortingOrder=0;
    Color32[] Capture(float progress,string name){
     foreach(var go in sprites)UnityEngine.Object.DestroyImmediate(go);sprites.Clear();bank.BeginFrame();var draws=presentation.Sample(step,step.before,step.duration*progress,0).Where(d=>d.masked).ToArray();
     Check(draws.Length>=report.obstacles,"All fixed obstacle bodies are sampled");
     if(progress==.5f)Check(draws.Where(d=>step.before.pieces.Any(p=>p.family=="gem"&&p.id==d.pieceId)).All(d=>d.alpha<.001f),"Color changes only at invisible midpoint");
     foreach(var d in draws){var sprite=bank.Get(d);if(!sprite)throw new Exception("Missing sprite "+d.bank+"/"+d.key);var go=new GameObject("body "+d.pieceId);go.transform.SetParent(root.transform,false);go.transform.localPosition=new Vector3(d.x,d.y,0);go.transform.localScale=new Vector3(d.sx,d.sy,1);go.transform.localRotation=Quaternion.Euler(0,0,d.angle);var sr=go.AddComponent<SpriteRenderer>();sr.sprite=sprite;sr.sharedMaterial=material;sr.sortingOrder=d.order;sr.maskInteraction=SpriteMaskInteraction.VisibleInsideMask;sr.color=new Color(d.red,d.green,d.blue,d.alpha);sprites.Add(go);}
     camera.Render();RenderTexture.active=target;var tex=new Texture2D(720,1280,TextureFormat.RGBA32,false);try{tex.ReadPixels(new Rect(0,0,720,1280),0,0);tex.Apply();File.WriteAllBytes(Path.Combine(output,name),tex.EncodeToPNG());return tex.GetPixels32();}finally{UnityEngine.Object.DestroyImmediate(tex);}
    }
    report.frames=new[]{"01_before.png","02_gather.png","03_hidden.png","04_release.png","05_after.png"};var samples=new[]{0f,.25f,.5f,.75f,1f};var captures=new List<Color32[]>();for(int i=0;i<samples.Length;i++)captures.Add(Capture(samples[i],report.frames[i]));
    report.changedPixels=new int[4];for(int i=1;i<captures.Count;i++){int changed=0;for(int j=0;j<captures[i].Length;j++)if(!captures[i-1][j].Equals(captures[i][j]))changed++;report.changedPixels[i-1]=changed;Check(changed>1000,"Adjacent rendered animation phases visibly differ");}
    report.status="PASS_RESHUFFLE_VISUAL117";
   }catch(Exception e){report.status="FAIL_RESHUFFLE_VISUAL117";report.error=e.ToString();}
   finally{RenderTexture.active=null;if(root)UnityEngine.Object.DestroyImmediate(root);if(material)UnityEngine.Object.DestroyImmediate(material);if(target)UnityEngine.Object.DestroyImmediate(target);if(bank!=null)bank.Dispose();File.WriteAllText(Path.Combine(output,"ReshuffleVisual117.json"),JsonUtility.ToJson(report,true));}
   EditorApplication.Exit(report.status=="PASS_RESHUFFLE_VISUAL117"?0:1);
  }
 }
}
#endif

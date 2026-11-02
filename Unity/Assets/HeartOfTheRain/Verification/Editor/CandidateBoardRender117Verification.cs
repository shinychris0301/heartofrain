#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 public static class CandidateBoardRender117Verification {
  [Serializable] sealed class Fingerprint {public LevelHash[] levels;}
  [Serializable] sealed class LevelHash {public int level;public string sha256;}
  [Serializable] sealed class ImageManifest {public Entry[] rows;}
  [Serializable] sealed class Entry {public int level;public string jsonSHA256,surfaceSHA256,maskSHA256;}
  [Serializable] sealed class Row {public int level,columns,rows,activeCells,checks;public string jsonSHA256,surfaceSHA256,maskSHA256,frame,error="";}
  [Serializable] sealed class Report {public string status,error="",scope="Unity Editor offscreen GPU render of staged level candidates and their staged generated matching surface/mask PNGs. The published campaign is unchanged. No gameplay balance, physical device, release or frame-rate certification.";public List<Row> rows=new List<Row>();}
  static string Hash(byte[] input){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(input)).Replace("-","").ToLowerInvariant();}
  public static void Run(){
   string output=Path.GetFullPath(Environment.GetEnvironmentVariable("HOTR_CANDIDATE_RENDER117_OUTPUT")??"../Verification/Evidence/Review117/CandidateRender");Directory.CreateDirectory(output);var report=new Report();M46AtlasBank bank=null;Material material=null;
   try{
    var fingerprint=JsonUtility.FromJson<Fingerprint>(File.ReadAllText("../Verification/Evidence/Review117/CampaignVaried03FullFingerprint.json"));var images=JsonUtility.FromJson<ImageManifest>(File.ReadAllText("../Verification/Evidence/Review117/BoardVaried03RepresentativeHashes.json"));
    var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");if(!ui||!ui.boards)throw new Exception("Missing current atlas");bank=new M46AtlasBank(ui.boards);material=new Material(ui.bodyShader?ui.bodyShader:Shader.Find("Sprites/Default"));
    foreach(int n in new[]{11,22,21}){
     var row=new Row{level=n};report.rows.Add(row);GameObject root=null;Texture2D surfaceTex=null,maskTex=null;Sprite surfaceSprite=null,maskSprite=null;RenderTexture target=null;
     void Check(bool v,string label){row.checks++;if(!v)throw new Exception(label);}
     try{
      string id="C01_L"+n.ToString("D3");byte[] data=File.ReadAllBytes("../.verification-cache/Review117/CampaignVaried03/"+id+".json"),surface=File.ReadAllBytes("../.verification-cache/Review117/BoardVaried03/"+id+"_Surface.png"),mask=File.ReadAllBytes("../.verification-cache/Review117/BoardVaried03/"+id+"_AlphaMask.png");
      row.jsonSHA256=Hash(data);row.surfaceSHA256=Hash(surface);row.maskSHA256=Hash(mask);var expected=images.rows.Single(x=>x.level==n);Check(row.jsonSHA256==expected.jsonSHA256&&row.jsonSHA256==fingerprint.levels.Single(x=>x.level==n).sha256&&row.surfaceSHA256==expected.surfaceSHA256&&row.maskSHA256==expected.maskSHA256,"Candidate JSON and graphics match pinned input hashes");
      var level=JsonUtility.FromJson<LevelData>(System.Text.Encoding.UTF8.GetString(data));row.columns=level.columns;row.rows=level.rows;row.activeCells=level.activeCells.Length;Check(level.globalLevel==n&&level.rows==9&&level.columns>=9&&level.columns<=11,"Expected candidate dimensions");var board=new BoardModel(level);board.Validate();
      surfaceTex=new Texture2D(2,2,TextureFormat.RGBA32,false);maskTex=new Texture2D(2,2,TextureFormat.RGBA32,false);Check(surfaceTex.LoadImage(surface)&&maskTex.LoadImage(mask),"Load staged approved-style source PNGs");
      Check(surfaceTex.width==level.columns*64+30&&surfaceTex.height==level.rows*64+30&&maskTex.width==surfaceTex.width&&maskTex.height==surfaceTex.height,"Candidate artwork dimensions match 64px board pitch");
      var active=new HashSet<int>(level.activeCells.Select(c=>c.y*level.columns+c.x));var mp=maskTex.GetPixels32();var sp=surfaceTex.GetPixels32();
      for(int y=0;y<level.rows;y++)for(int x=0;x<level.columns;x++)foreach(int dy in new[]{-24,0,24})foreach(int dx in new[]{-24,0,24}){int px=15+x*64+32+dx,py=15+y*64+32+dy;bool expectedActive=active.Contains(y*level.columns+x);var ma=mp[py*maskTex.width+px].a;var sa=sp[py*surfaceTex.width+px].a;Check(expectedActive?ma>=240:ma==0,"Candidate mask matches active and inactive cell interior");if(expectedActive)Check(sa>=240,"Candidate surface fully covers active cell interior");}
      surfaceSprite=Sprite.Create(surfaceTex,new Rect(0,0,surfaceTex.width,surfaceTex.height),new Vector2(.5f,.5f),64f);maskSprite=Sprite.Create(maskTex,new Rect(0,0,maskTex.width,maskTex.height),new Vector2(.5f,.5f),64f);
      root=new GameObject("Candidate board render "+n);root.transform.position=new Vector3(1000,0,0);Vector3 center=new Vector3((level.columns-1)*.5f,(level.rows-1)*.5f,0);
      var so=new GameObject("Candidate surface");so.transform.SetParent(root.transform,false);so.transform.localPosition=center;var sr=so.AddComponent<SpriteRenderer>();sr.sprite=surfaceSprite;sr.sharedMaterial=material;sr.sortingOrder=0;
      var mo=new GameObject("Candidate active mask");mo.transform.SetParent(root.transform,false);mo.transform.localPosition=center;var sm=mo.AddComponent<SpriteMask>();sm.sprite=maskSprite;sm.isCustomRangeActive=true;sm.frontSortingOrder=15;sm.backSortingOrder=5;
      bank.BeginFrame();var presentation=new BoardPresentation{columns=level.columns,rows=level.rows};var draws=presentation.Sample(null,board.Snapshot(),0,0);foreach(var d in draws.Where(d=>d.masked)){var sprite=bank.Get(d);Check(sprite!=null,"Actual atlas provides "+d.key);var go=new GameObject("Board piece "+d.pieceId);go.transform.SetParent(root.transform,false);go.transform.localPosition=new Vector3(d.x,d.y,0);go.transform.localScale=new Vector3(d.sx,d.sy,1);go.transform.localRotation=Quaternion.Euler(0,0,d.angle);var image=go.AddComponent<SpriteRenderer>();image.sprite=sprite;image.sharedMaterial=material;image.sortingOrder=d.order;image.maskInteraction=SpriteMaskInteraction.VisibleInsideMask;image.color=new Color(d.red,d.green,d.blue,d.alpha);}
      var cameraObject=new GameObject("Candidate capture camera");cameraObject.transform.SetParent(root.transform,false);var camera=cameraObject.AddComponent<Camera>();camera.orthographic=true;camera.orthographicSize=BoardPresentation.CameraHalfHeight(level.columns,level.rows,720f/1280f);camera.transform.localPosition=new Vector3(center.x,center.y,-10);camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.035f,.05f,.07f);target=new RenderTexture(720,1280,24);camera.targetTexture=target;camera.Render();RenderTexture.active=target;var pixels=new Texture2D(720,1280,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,720,1280),0,0);pixels.Apply();row.frame=id+"_"+level.columns+"x9.png";File.WriteAllBytes(Path.Combine(output,row.frame),pixels.EncodeToPNG());UnityEngine.Object.DestroyImmediate(pixels);
     }catch(Exception e){row.error=e.ToString();}
     finally{RenderTexture.active=null;if(root)UnityEngine.Object.DestroyImmediate(root);if(target)UnityEngine.Object.DestroyImmediate(target);if(surfaceSprite)UnityEngine.Object.DestroyImmediate(surfaceSprite);if(maskSprite)UnityEngine.Object.DestroyImmediate(maskSprite);if(surfaceTex)UnityEngine.Object.DestroyImmediate(surfaceTex);if(maskTex)UnityEngine.Object.DestroyImmediate(maskTex);}
    }
    report.status=report.rows.Count==3&&report.rows.All(r=>string.IsNullOrEmpty(r.error))?"PASS_CANDIDATE_BOARD_RENDER117":"FAIL_CANDIDATE_BOARD_RENDER117";
   }catch(Exception e){report.status="FAIL_CANDIDATE_BOARD_RENDER117";report.error=e.ToString();}
   finally{if(material)UnityEngine.Object.DestroyImmediate(material);if(bank!=null)bank.Dispose();File.WriteAllText(Path.Combine(output,"CandidateBoardRender117.json"),JsonUtility.ToJson(report,true));}
   EditorApplication.Exit(report.status=="PASS_CANDIDATE_BOARD_RENDER117"?0:1);
  }
 }
}
#endif

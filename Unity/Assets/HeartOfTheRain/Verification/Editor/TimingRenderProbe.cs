#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.M46;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification
{
    public static class TimingRenderProbe
    {
        [Serializable] class Report {public string status,utc,scope="Native Editor GPU board-body render. Control disables only the new spawn visibility boundary at the same current presentation pose; it is not a screenshot of the preceding APK. No frame-budget or device certification.";public int changedPixels;public string error;}
        public static void Run()
        {
            string output=Path.GetFullPath("../Verification/Evidence/Timing/Render");Directory.CreateDirectory(output);var report=new Report{utc=DateTime.UtcNow.ToString("o")};M46AtlasBank bank=null;GameObject root=null;RenderTexture target=null;Material material=null;
            try{
                var ui=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");var b=new BoardModel(JsonUtility.FromJson<LevelData>(ui.boards.levels[41].text));var source=b.Pieces.Values.First(p=>p.family=="gem");b.InjectReviewPower(source.x,source.y,21);var step=BoardPlayback.Build(b.Tap(source.x,source.y).steps,b.Level).First();var lower=step.motion.First(m=>m.spawned&&m.toX==1&&m.toY==4);var presentation=new BoardPresentation{columns=b.Level.columns,rows=b.Level.rows};
                bank=new M46AtlasBank(ui.boards);material=new Material(ui.bodyShader?ui.bodyShader:Shader.Find("Sprites/Default"));root=new GameObject("Native portal probe");root.transform.position=new Vector3(1000,0,0);
                var cameraObject=new GameObject("Portal camera");cameraObject.transform.SetParent(root.transform,false);var camera=cameraObject.AddComponent<Camera>();camera.orthographic=true;camera.orthographicSize=b.Level.rows*.5f+.8f;camera.transform.localPosition=new Vector3((b.Level.columns-1)*.5f,(b.Level.rows-1)*.5f,-10);camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.035f,.05f,.07f);target=new RenderTexture(768,768,24);camera.targetTexture=target;
                var maskObject=new GameObject("Authored active-cell mask");maskObject.transform.SetParent(root.transform,false);maskObject.transform.localPosition=new Vector3((b.Level.columns-1)*.5f,(b.Level.rows-1)*.5f,0);var mask=maskObject.AddComponent<SpriteMask>();mask.sprite=bank.BoardMask(41);mask.isCustomRangeActive=true;mask.frontSortingOrder=15;mask.backSortingOrder=5;
                var surfaceObject=new GameObject("Authored board");surfaceObject.transform.SetParent(root.transform,false);surfaceObject.transform.localPosition=maskObject.transform.localPosition;var surface=surfaceObject.AddComponent<SpriteRenderer>();surface.sharedMaterial=material;surface.sprite=bank.BoardSurface(41);surface.sortingOrder=0;
                var sprites=new List<GameObject>();
                Color32[] Capture(bool clip,string name){
                    foreach(var go in sprites)UnityEngine.Object.DestroyImmediate(go);sprites.Clear();lower.clipSpawn=clip;bank.BeginFrame();var draws=presentation.Sample(step,step.after,.20f,0).Where(d=>d.masked).ToArray();
                    if(draws.Any(d=>d.pieceId==lower.id)==clip)throw new Exception("Portal visibility does not follow its boundary.");
                    foreach(var d in draws){var sprite=bank.Get(d);if(!sprite)continue;var go=new GameObject("Body "+d.pieceId);go.transform.SetParent(root.transform,false);go.transform.localPosition=new Vector3(d.x,d.y,0);go.transform.localScale=new Vector3(d.sx,d.sy,1);go.transform.localRotation=Quaternion.Euler(0,0,d.angle);var sr=go.AddComponent<SpriteRenderer>();sr.sprite=sprite;sr.sharedMaterial=material;sr.sortingOrder=d.order;sr.maskInteraction=SpriteMaskInteraction.VisibleInsideMask;sr.color=new Color(d.red,d.green,d.blue,d.alpha);sprites.Add(go);}
                    camera.Render();RenderTexture.active=target;var pixels=new Texture2D(768,768,TextureFormat.RGBA32,false);pixels.ReadPixels(new Rect(0,0,768,768),0,0);pixels.Apply();File.WriteAllBytes(Path.Combine(output,name),pixels.EncodeToPNG());var result=pixels.GetPixels32();UnityEngine.Object.DestroyImmediate(pixels);return result;
                }
                var control=Capture(false,"L42_Portal_Control.png");var corrected=Capture(true,"L42_Portal_Corrected.png");report.changedPixels=control.Zip(corrected,(a,c)=>a.Equals(c)?0:1).Sum();if(report.changedPixels==0)throw new Exception("Native rendering produced no portal correction pixels.");report.status="PASS_NATIVE_PORTAL_RENDER";
            }catch(Exception e){report.status="FAIL_NATIVE_PORTAL_RENDER";report.error=e.ToString();}
            finally{RenderTexture.active=null;if(root)UnityEngine.Object.DestroyImmediate(root);if(material)UnityEngine.Object.DestroyImmediate(material);if(target)UnityEngine.Object.DestroyImmediate(target);if(bank!=null)bank.Dispose();File.WriteAllText(Path.Combine(output,"Report.json"),JsonUtility.ToJson(report,true));}
            EditorApplication.Exit(report.status=="PASS_NATIVE_PORTAL_RENDER"?0:1);
        }
    }
}
#endif

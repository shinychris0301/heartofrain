#if UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.Verification {
 [InitializeOnLoad]public static class ObstacleDensityPlayVerification {
  const string Key="HOTR.ObstacleDensity.NativePlay";static bool launched;static readonly BindingFlags Private=BindingFlags.Instance|BindingFlags.NonPublic;
  [Serializable]class Pixels {public string scope="Native gameplay camera at one fixed peak pose. Same live renderer pool, legacy versus optimized sampling/property path, HUD excluded. Not Android screenshots or a timing test.";public int width,height,changedPixels;public string status;}
  static ObstacleDensityPlayVerification(){if(SessionState.GetBool(Key,false))EditorApplication.update+=Tick;}
  public static void Run(){SessionState.SetBool(Key,true);EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);EditorApplication.isPlaying=true;}
  static void Tick(){if(!EditorApplication.isPlaying||EditorApplication.isCompiling||launched)return;launched=true;var probe=new GameObject("Native density verification").AddComponent<ObstacleDensityProbe>();probe.suppliedAssets=AssetDatabase.LoadAssetAtPath<GameplayUIAssets>("Assets/HeartOfTheRain/M48/M48GameplayUIAssets.asset");probe.InspectPeak=Capture;probe.Completed=report=>{bool ok=report.status=="PASS_OBSTACLE_DENSITY_PLAYBACK"&&report.rows.Count==10&&report.rows.TrueForAll(r=>r.renderersCreated==0&&r.crateSpritesCreated==0&&r.poolReady==1182&&r.poolEnd==1182&&r.cleared==r.crates)&&File.Exists(Path.GetFullPath("../Verification/Evidence/ObstacleDensity/Native_Pixels.json"));File.WriteAllText(Path.GetFullPath("../Verification/Evidence/ObstacleDensity/NativePlay.json"),JsonUtility.ToJson(report,true));SessionState.EraseBool(Key);EditorApplication.Exit(ok?0:1);};}
  static void Capture(GameplayScreen game){
   string dir=Path.GetFullPath("../Verification/Evidence/ObstacleDensity");Directory.CreateDirectory(dir);var camera=(Camera)typeof(GameplayScreen).GetField("view",Private).GetValue(game);var oldTarget=camera.targetTexture;var active=RenderTexture.active;var target=new RenderTexture(720,1280,24);bool legacy=game.VerificationUseLegacyDensityWork;var pixels=new Pixels{width=720,height=1280};
   try{
    Color32[] Shot(bool old,string name){game.VerificationUseLegacyDensityWork=old;typeof(GameplayScreen).GetMethod("Render",Private).Invoke(game,null);camera.targetTexture=target;camera.Render();RenderTexture.active=target;var image=new Texture2D(720,1280,TextureFormat.RGBA32,false);image.ReadPixels(new Rect(0,0,720,1280),0,0);image.Apply();File.WriteAllBytes(Path.Combine(dir,name),image.EncodeToPNG());var result=image.GetPixels32();UnityEngine.Object.Destroy(image);return result;}
    var before=Shot(true,"Native_Peak_Legacy.png");var after=Shot(false,"Native_Peak_Optimized.png");pixels.changedPixels=before.Zip(after,(a,b)=>a.Equals(b)?0:1).Sum();pixels.status=pixels.changedPixels==0?"PASS_NATIVE_PIXEL_PARITY":"FAIL_NATIVE_PIXEL_PARITY";
    File.WriteAllText(Path.Combine(dir,"Native_Pixels.json"),JsonUtility.ToJson(pixels,true));if(pixels.changedPixels!=0)throw new Exception("Native pixel parity differs: "+pixels.changedPixels);
   }finally{game.VerificationUseLegacyDensityWork=legacy;camera.targetTexture=oldTarget;RenderTexture.active=active;UnityEngine.Object.Destroy(target);}
  }
 }
}
#endif

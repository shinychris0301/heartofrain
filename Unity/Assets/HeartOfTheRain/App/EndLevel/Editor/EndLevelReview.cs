#if UNITY_EDITOR
using System.IO;using UnityEditor;using UnityEditor.SceneManagement;using UnityEngine;
using HeartOfTheRain.App.Settings;
namespace HeartOfTheRain.App.EndLevel.Editor
{
 public static class EndLevelReview
 {
  const string Root="Assets/HeartOfTheRain/App/EndLevel";
  [MenuItem("Heart of the Rain/App/M58/Open End Level Review")]
  public static void Open(){if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene(Root+"/Scenes/M58_EndLevel_Review.unity");}
  [MenuItem("Heart of the Rain/App/M58/Open Confirmation in Play Mode")]
  public static void Show(){var c=Object.FindObjectOfType<GameplaySettingsController>();if(c)c.ShowEndLevel();else Debug.LogWarning("Start a level from the app review scene first.");}
  [MenuItem("Heart of the Rain/App/M58/Validate End Level Assets")]
  public static void Validate()
  {
   var a=AssetDatabase.LoadAssetAtPath<EndLevelAssets>(Root+"/EndLevelAssets.asset");
   if(!a||!a.approvedSettings||!a.approvedSettings.approvedUI||!a.approvedSettings.approvedUI.home)throw new System.Exception("Incomplete M58 asset bindings");
   foreach(string id in new[]{"ModalShell_R2","R4_Start","Close","ExitButton","Avatar_Ivan_Home","QuantityBadge_R2","LifeLostHeart"})if(!a.Find(id))throw new System.Exception("Missing M58 sprite: "+id);
   var t=(TextureImporter)AssetImporter.GetAtPath(Root+"/Art/LifeLostHeart.png");
   if(!t.sRGBTexture||t.mipmapEnabled||t.textureCompression!=TextureImporterCompression.Uncompressed)throw new System.Exception("Unexpected M58 heart import policy");
   Debug.Log("M58 asset references and import policy pass. Run Play Mode to verify native rendering and behavior.");
  }
  [MenuItem("Heart of the Rain/App/M58/Capture Actual Confirmation Game View")]
  public static void Capture()
  {
   var c=Object.FindObjectOfType<GameplaySettingsController>();if(!Application.isPlaying||!c||!c.IsEndLevelVisible){Debug.LogWarning("Open the M58 confirmation in Play Mode first.");return;}
   string dir=Path.GetFullPath("../ReviewCaptures");Directory.CreateDirectory(dir);string path=Path.Combine(dir,"M58_EndLevel_"+System.DateTime.Now.ToString("yyyyMMdd_HHmmss")+".png");ScreenCapture.CaptureScreenshot(path);Debug.Log("Queued actual Game view capture: "+path);
  }
 }
 public sealed class EndLevelArtImportPolicy:AssetPostprocessor
 {
  void OnPreprocessTexture()
  {
   if(!assetPath.StartsWith("Assets/HeartOfTheRain/App/EndLevel/Art/",System.StringComparison.Ordinal))return;
   var t=(TextureImporter)assetImporter;t.textureType=TextureImporterType.Sprite;t.spriteImportMode=SpriteImportMode.Single;t.sRGBTexture=true;t.mipmapEnabled=false;t.alphaIsTransparency=true;t.textureCompression=TextureImporterCompression.Uncompressed;t.crunchedCompression=false;t.npotScale=TextureImporterNPOTScale.None;t.maxTextureSize=2048;t.filterMode=FilterMode.Bilinear;t.wrapMode=TextureWrapMode.Clamp;
   foreach(string name in new[]{"Android","iPhone","Standalone"}){var p=t.GetPlatformTextureSettings(name);p.overridden=false;t.SetPlatformTextureSettings(p);}
  }
 }
}
#endif

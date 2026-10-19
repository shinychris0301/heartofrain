#if UNITY_EDITOR
using System.IO;using UnityEditor;using UnityEditor.SceneManagement;using UnityEngine;
namespace HeartOfTheRain.App.Settings.Editor
{
 public static class GameplaySettingsMenu
 {
  const string Root="Assets/HeartOfTheRain/App/Settings";
  [MenuItem("Heart of the Rain/App/M57/Open Settings Review")]
  public static void Open(){if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene(Root+"/Scenes/M57_Settings_Review.unity");}
  [MenuItem("Heart of the Rain/App/M57/Open Settings in Play Mode")]
  public static void Show(){var c=Object.FindObjectOfType<GameplaySettingsController>();if(c)c.Show();else Debug.LogWarning("Start a level from the M57 review scene first.");}
  [MenuItem("Heart of the Rain/App/M57/Validate Settings Assets")]
  public static void Validate()
  {
   var a=AssetDatabase.LoadAssetAtPath<GameplaySettingsAssets>(Root+"/GameplaySettingsAssets.asset");
   if(!a||!a.approvedUI||!a.approvedUI.home||!a.approvedUI.home.boldFont||!a.reviewMusic)throw new System.Exception("Incomplete M57 settings assets.");
   foreach(string id in new[]{"ModalShell_R2","R4_Start","Close","ExitButton","ToggleOn","ToggleOff","MusicGlyph","SoundGlyph","HintGlyph","OffSlash"})if(!a.Find(id))throw new System.Exception("Missing settings sprite "+id);
   foreach(string guid in AssetDatabase.FindAssets("t:Texture2D",new[]{Root+"/Art"})){var t=(TextureImporter)AssetImporter.GetAtPath(AssetDatabase.GUIDToAssetPath(guid));if(!t.sRGBTexture||t.mipmapEnabled||t.textureCompression!=TextureImporterCompression.Uncompressed)throw new System.Exception("Unexpected settings import policy");}
   Debug.Log("M57 settings bindings and imports pass. Play Mode, sound and device behavior must be checked separately.");
  }
  [MenuItem("Heart of the Rain/App/M57/Capture Actual Settings Game View")]
  public static void Capture()
  {
   var c=Object.FindObjectOfType<GameplaySettingsController>();if(!Application.isPlaying||!c||!c.IsSettingsVisible){Debug.LogWarning("Open the M57 settings modal in Play mode first.");return;}
   string dir=Path.GetFullPath("../ReviewCaptures");Directory.CreateDirectory(dir);string path=Path.Combine(dir,"M57_Settings_"+System.DateTime.Now.ToString("yyyyMMdd_HHmmss")+".png");ScreenCapture.CaptureScreenshot(path);Debug.Log("Queued actual Game view capture: "+path);
  }
 }
 public sealed class SettingsArtImportPolicy:AssetPostprocessor
 {
  void OnPreprocessTexture()
  {
   if(!assetPath.StartsWith("Assets/HeartOfTheRain/App/Settings/Art/",System.StringComparison.Ordinal))return;
   var t=(TextureImporter)assetImporter;t.textureType=TextureImporterType.Sprite;t.spriteImportMode=SpriteImportMode.Single;t.sRGBTexture=true;t.mipmapEnabled=false;t.alphaIsTransparency=true;t.textureCompression=TextureImporterCompression.Uncompressed;t.crunchedCompression=false;t.npotScale=TextureImporterNPOTScale.None;t.maxTextureSize=2048;t.filterMode=FilterMode.Bilinear;t.wrapMode=TextureWrapMode.Clamp;
   foreach(string name in new[]{"Android","iPhone","Standalone"}){var p=t.GetPlatformTextureSettings(name);p.overridden=false;t.SetPlatformTextureSettings(p);}
  }
 }
}
#endif

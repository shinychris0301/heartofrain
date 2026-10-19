#if UNITY_EDITOR
using System.IO;using UnityEditor;using UnityEditor.SceneManagement;using UnityEngine;
namespace HeartOfTheRain.App.AppSettings.Editor
{
 public static class AppSettingsReview
 {
  [MenuItem("Heart of the Rain/App/M64/Open Main Settings Review")]
  public static void Open(){if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/AppSettings/Scenes/M64_App_Settings_Review.unity");}
  [MenuItem("Heart of the Rain/App/M64/Capture Actual Settings Game View")]
  public static void Capture(){var p=Object.FindObjectOfType<AppSettingsPage>();if(!Application.isPlaying||!p||!p.IsVisible){Debug.LogWarning("Open Settings in Play Mode first.");return;}string d=Path.GetFullPath("../ReviewCaptures");Directory.CreateDirectory(d);ScreenCapture.CaptureScreenshot(Path.Combine(d,"M64_Settings_"+System.DateTime.Now.ToString("yyyyMMdd_HHmmss")+".png"));}
  [MenuItem("Heart of the Rain/App/M64/Validate Main Settings Assets")]
  public static void Validate()
  {
   var a=AssetDatabase.LoadAssetAtPath<AppSettingsAssets>("Assets/HeartOfTheRain/App/AppSettings/AppSettingsAssets.asset");if(!a||!a.shop||!a.gameplaySettings||!a.destinations||!a.Home)throw new System.Exception("Missing main Settings binding");
   foreach(var s in a.sprites)if(!s.sprite)throw new System.Exception("Missing Settings sprite "+s.id);
   foreach(var key in new[]{"ModalShell_R2","Close","ToggleOn","ToggleOff","Rocket","Bomb","RainbowOrb_R2","GoldenSeeker_R2","ShopHammer","ShopAxe","ShopRam","ShopAtlas","AS_Globe","AS_Support"})if(!a.Find(key))throw new System.Exception("Missing shared sprite "+key);
   var links=JsonUtility.FromJson<AppSettingsLinks>(a.destinations.text);foreach(var key in new[]{"support","instagram","youtube","facebook","terms","privacy"}){string value=links.Get(key);if(!string.IsNullOrEmpty(value)&&!AppSettingsLinks.ValidURL(value))throw new System.Exception("Invalid HTTPS destination: "+key);}
   Debug.Log("M64 bindings valid. Empty official destinations show unavailable states; Unity rendering and native input still need review.");
  }
 }
}
#endif

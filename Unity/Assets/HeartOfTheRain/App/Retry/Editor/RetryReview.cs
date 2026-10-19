#if UNITY_EDITOR
using System.IO;using UnityEditor;using UnityEditor.SceneManagement;using UnityEngine;
using HeartOfTheRain.App.PreLevel;using HeartOfTheRain.App.Settings;
namespace HeartOfTheRain.App.Retry.Editor
{
 public static class RetryReview
 {
  [MenuItem("Heart of the Rain/App/M59/Open Try Again Review")]
  public static void Open(){if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/Retry/Scenes/M59_TryAgain_Review.unity");}
  [MenuItem("Heart of the Rain/App/M59/Open Exit Confirmation in Play Mode")]
  public static void Exit(){var c=Object.FindObjectOfType<GameplaySettingsController>();if(c)c.ShowEndLevel();else Debug.LogWarning("Start a level first; confirm Exit to review the real retry transition.");}
  [MenuItem("Heart of the Rain/App/M59/Validate Retry Bindings")]
  public static void Validate()
  {
   var a=AssetDatabase.LoadAssetAtPath<PreLevelAssets>("Assets/HeartOfTheRain/App/PreLevel/PreLevelAssets.asset");
   if(!a||!a.retryLifeIcon||!a.home||!a.gameplay||a.gameplay.boards.levels.Length!=50)throw new System.Exception("Incomplete retry bindings");
   Debug.Log("M59 retry bindings pass. Review exit-to-retry, booster stock and board reset in Play Mode.");
  }
  [MenuItem("Heart of the Rain/App/M59/Capture Actual Try Again Game View")]
  public static void Capture()
  {
   var flow=Object.FindObjectOfType<HomeLevelFlow>();if(!Application.isPlaying||!flow||!flow.RetryVisible){Debug.LogWarning("Confirm exit from a running level to open Try Again first.");return;}
   string dir=Path.GetFullPath("../ReviewCaptures");Directory.CreateDirectory(dir);string path=Path.Combine(dir,"M59_TryAgain_"+System.DateTime.Now.ToString("yyyyMMdd_HHmmss")+".png");ScreenCapture.CaptureScreenshot(path);Debug.Log("Queued actual Game view capture: "+path);
  }
 }
}
#endif

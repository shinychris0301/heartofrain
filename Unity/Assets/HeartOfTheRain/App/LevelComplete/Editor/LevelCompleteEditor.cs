#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace HeartOfTheRain.App.LevelComplete.Editor {
 public static class LevelCompleteEditor {
  const string Root="Assets/HeartOfTheRain/App/LevelComplete/";
  [MenuItem("Heart of the Rain/App/M66/Open Level Complete Review")]
  public static void Review(){Open("M66_Level_Complete_Review");}
  [MenuItem("Heart of the Rain/App/M66/Open Chapter 1 Finale Review")]
  public static void Finale(){Open("M66_Chapter_Finale_Review");}
  static void Open(string name){if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene(Root+"Scenes/"+name+".unity");}
  [MenuItem("Heart of the Rain/App/M66/Validate Level Complete Assets")]
  public static void Validate(){var a=AssetDatabase.LoadAssetAtPath<LevelCompleteAssets>(Root+"Resources/M66_LevelCompleteAssets.asset");if(!a||!a.shared||!a.preLevel)throw new Exception("Missing completion bindings");foreach(var k in new[]{"ModalShell_R2","RewardCoin","RewardStar_R2","R4_Start","LC_Home","LC_Halo","LC_Track","LC_Fill","LC_RewardWell"})if(!a.Find(k))throw new Exception("Missing "+k);Debug.Log("M66 asset bindings verified. Review scenes do not award campaign rewards.");}
  [MenuItem("Heart of the Rain/App/M66/Capture Actual Level Complete Game View")]
  public static void Capture(){var modal=UnityEngine.Object.FindObjectOfType<LevelCompleteModal>();if(!Application.isPlaying||!modal||!modal.IsVisible){Debug.LogWarning("Open a Level Complete modal in Play Mode first.");return;}var dir=Path.GetFullPath("../ReviewCaptures");Directory.CreateDirectory(dir);ScreenCapture.CaptureScreenshot(Path.Combine(dir,"M66_"+DateTime.Now.ToString("yyyyMMdd_HHmmss")+".png"));}
 }
}
#endif

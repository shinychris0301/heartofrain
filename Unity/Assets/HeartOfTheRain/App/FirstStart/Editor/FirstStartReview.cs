#if UNITY_EDITOR
using System;using System.IO;using System.Linq;using UnityEditor;using UnityEditor.SceneManagement;using UnityEngine;
namespace HeartOfTheRain.App.FirstStart.Editor {
 public static class FirstStartReview {
  const string Root="Assets/HeartOfTheRain/App/FirstStart/";
  [MenuItem("Heart of the Rain/App/M65/Open First Start Review")]
  public static void Review(){if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene(Root+"Scenes/M65_First_Start_Review.unity");}
  [MenuItem("Heart of the Rain/App/M65/Open First Run Entry")]
  public static void Entry(){if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene(Root+"Scenes/M65_First_Start.unity");}
  [MenuItem("Heart of the Rain/App/M65/Validate First Start Assets")]
  public static void Validate(){var a=AssetDatabase.LoadAssetAtPath<FirstStartAssets>(Root+"FirstStartAssets.asset");if(!a||!a.shared||!a.Home||!a.Gameplay||a.lessons==null||a.lessons.Length!=3||a.lessons.Any(v=>!v))throw new Exception("Missing First Start binding");foreach(string k in new[]{"FS_Panel","FS_Chip","FS_CellLight","FS_CellSlate","Chapter01_VillageWell","Chapter02_Chamber","AS_Globe","MusicGlyph","OffSlash","R4_Start","SelectionTick_R2"})if(!a.Find(k))throw new Exception("Missing "+k);if(!a.shared.gameplaySettings.reviewMusic)throw new Exception("Missing review music");Debug.Log("First Start bindings verified. Use both scenes to check replay and saved completion separately.");}
  [MenuItem("Heart of the Rain/App/M65/Capture Actual First Start Game View")]
  public static void Capture(){var p=UnityEngine.Object.FindObjectOfType<FirstStartPage>();if(!Application.isPlaying||!p||!p.IsVisible){Debug.LogWarning("Open First Start in Play Mode first.");return;}string d=Path.GetFullPath("../ReviewCaptures");Directory.CreateDirectory(d);ScreenCapture.CaptureScreenshot(Path.Combine(d,"M65_"+p.Stage+"_"+DateTime.Now.ToString("yyyyMMdd_HHmmss")+".png"));}
 }
}
#endif

#if UNITY_EDITOR
using System.IO;using UnityEditor;using UnityEditor.SceneManagement;using UnityEngine;
namespace HeartOfTheRain.App.Leaderboard.Editor
{
 public static class LeaderboardReview
 {
  [MenuItem("Heart of the Rain/App/M61/Open Leaderboard Review")]
  public static void Open(){if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/Leaderboard/Scenes/M61_Leaderboard_Review.unity");}
  [MenuItem("Heart of the Rain/App/M61/Reset Sample Friends and Rankings")]
  public static void Reset(){var p=Object.FindObjectOfType<LeaderboardPage>();if(Application.isPlaying&&p){p.ResetDemo();p.Show();}else Debug.LogWarning("Enter Play Mode in the M61 scene first.");}
  [MenuItem("Heart of the Rain/App/M61/Capture Actual Leaderboard Game View")]
  public static void Capture(){var p=Object.FindObjectOfType<LeaderboardPage>();if(!Application.isPlaying||!p||!p.IsVisible){Debug.LogWarning("Open Leaderboard in Play Mode first.");return;}string d=Path.GetFullPath("../ReviewCaptures");Directory.CreateDirectory(d);ScreenCapture.CaptureScreenshot(Path.Combine(d,"M61_Leaderboard_"+System.DateTime.Now.ToString("yyyyMMdd_HHmmss")+".png"));}
  [MenuItem("Heart of the Rain/App/M61/Validate Leaderboard Assets")]
  public static void Validate(){var a=AssetDatabase.LoadAssetAtPath<LeaderboardAssets>("Assets/HeartOfTheRain/App/Leaderboard/LeaderboardAssets.asset");if(!a||!a.journey||!a.demoData)throw new System.Exception("Missing Leaderboard binding");var s=new LeaderboardSession(JsonUtility.FromJson<LeaderboardSnapshot>(a.demoData.text));foreach(var v in a.sprites)if(!v.sprite)throw new System.Exception("Missing sprite "+v.id);foreach(var p in s.Data.players){a.Find(p.portrait);a.Find(p.banner);}foreach(var t in s.Data.teams)a.Find(t.crest);Debug.Log("Leaderboard bindings valid; live service and Unity/device review remain separate.");}
 }
}
#endif

#if UNITY_EDITOR
using System.IO;using UnityEditor;using UnityEditor.SceneManagement;using UnityEngine;
namespace HeartOfTheRain.App.Teams.Editor
{
 public static class TeamsReview
 {
  [MenuItem("Heart of the Rain/App/M62/Open Teams Review")]
  public static void Open(){if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/Teams/Scenes/M62_Teams_Review.unity");}
  [MenuItem("Heart of the Rain/App/M62/Reset Sample Team Activity")]
  public static void Reset(){var p=Object.FindObjectOfType<TeamsPage>();if(Application.isPlaying&&p){p.ResetDemo();p.Show();}else Debug.LogWarning("Enter Play Mode in the M62 scene first.");}
  [MenuItem("Heart of the Rain/App/M62/Capture Actual Teams Game View")]
  public static void Capture(){var p=Object.FindObjectOfType<TeamsPage>();if(!Application.isPlaying||!p||!p.IsVisible){Debug.LogWarning("Open Teams in Play Mode first.");return;}string d=Path.GetFullPath("../ReviewCaptures");Directory.CreateDirectory(d);ScreenCapture.CaptureScreenshot(Path.Combine(d,"M62_Teams_"+System.DateTime.Now.ToString("yyyyMMdd_HHmmss")+".png"));}
  [MenuItem("Heart of the Rain/App/M62/Validate Teams Assets")]
  public static void Validate(){var a=AssetDatabase.LoadAssetAtPath<TeamsAssets>("Assets/HeartOfTheRain/App/Teams/TeamsAssets.asset");if(!a||!a.leaderboard||!a.demoData)throw new System.Exception("Missing Teams binding");var s=new TeamsSession(JsonUtility.FromJson<TeamsSnapshot>(a.demoData.text));foreach(var v in a.sprites)if(!v.sprite)throw new System.Exception("Missing sprite "+v.id);foreach(var m in s.Data.team.members)a.Find(m.portrait);a.Find(s.Data.team.crest);Debug.Log("Teams bindings valid. Review data is local; Unity/device verification remains separate.");}
 }
}
#endif

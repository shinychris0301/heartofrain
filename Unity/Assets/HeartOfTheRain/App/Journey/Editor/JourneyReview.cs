#if UNITY_EDITOR
using System.IO;using UnityEditor;using UnityEditor.SceneManagement;using UnityEngine;
namespace HeartOfTheRain.App.Journey.Editor
{
 public static class JourneyReview
 {
  [MenuItem("Heart of the Rain/App/M60/Open Journey Review")]
  public static void Open(){if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/Journey/Scenes/M60_Journey_Review.unity");}
  [MenuItem("Heart of the Rain/App/M60/Preview Completed Chapter 1")]
  public static void Completed(){var p=Object.FindObjectOfType<JourneyPage>();if(Application.isPlaying&&p){p.ApplyCampaignProgress(50);p.Show();}else Debug.LogWarning("Enter Play Mode in the M60 scene first. This affects Journey preview only.");}
  [MenuItem("Heart of the Rain/App/M60/Use Current Home Progress")]
  public static void Live(){var p=Object.FindObjectOfType<JourneyPage>();if(Application.isPlaying&&p){p.UseHomeProgress();p.Show();}}
  [MenuItem("Heart of the Rain/App/M60/Capture Actual Journey Game View")]
  public static void Capture(){var p=Object.FindObjectOfType<JourneyPage>();if(!Application.isPlaying||!p||!p.IsVisible){Debug.LogWarning("Open Journey in Play Mode first.");return;}string d=Path.GetFullPath("../ReviewCaptures");Directory.CreateDirectory(d);ScreenCapture.CaptureScreenshot(Path.Combine(d,"M60_Journey_"+System.DateTime.Now.ToString("yyyyMMdd_HHmmss")+".png"));}
  [MenuItem("Heart of the Rain/App/M60/Validate Journey Assets")]
  public static void Validate(){var a=AssetDatabase.LoadAssetAtPath<JourneyAssets>("Assets/HeartOfTheRain/App/Journey/JourneyAssets.asset");if(!a||!a.home||!a.preLevel||!a.catalog)throw new System.Exception("Missing Journey binding");var c=JsonUtility.FromJson<JourneyCatalog>(a.catalog.text);if(c.chapters.Length!=100)throw new System.Exception("Expected 100 story chapters");foreach(var s in a.sprites)if(!s.sprite)throw new System.Exception("Missing sprite "+s.id);Debug.Log("Journey bindings valid. Actual Play Mode/rendering and device review still required.");}
 }
}
#endif

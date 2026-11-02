#if UNITY_EDITOR
using System.IO;using UnityEditor;using UnityEditor.SceneManagement;using UnityEngine;
namespace HeartOfTheRain.App.Shop.Editor
{
 public static class ShopReview
 {
  [MenuItem("Heart of the Rain/App/M63/Open Shop Review")]
  public static void Open(){if(EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())EditorSceneManager.OpenScene("Assets/HeartOfTheRain/App/Shop/Scenes/M63_Shop_Review.unity");}
  [MenuItem("Heart of the Rain/App/M63/Reset Shop Preview")]
  public static void Reset(){var p=Object.FindFirstObjectByType<ShopPage>();if(Application.isPlaying&&p){p.ResetPreview();p.Show();}else Debug.LogWarning("Enter Play Mode in the M63 scene first.");}
  [MenuItem("Heart of the Rain/App/M63/Capture Actual Shop Game View")]
  public static void Capture(){var p=Object.FindFirstObjectByType<ShopPage>();if(!Application.isPlaying||!p||!p.IsVisible){Debug.LogWarning("Open Shop in Play Mode first.");return;}string d=Path.GetFullPath("../ReviewCaptures");Directory.CreateDirectory(d);ScreenCapture.CaptureScreenshot(Path.Combine(d,"M63_Shop_"+System.DateTime.Now.ToString("yyyyMMdd_HHmmss")+".png"));}
  [MenuItem("Heart of the Rain/App/M63/Validate Shop Assets")]
  public static void Validate(){var a=AssetDatabase.LoadAssetAtPath<ShopAssets>("Assets/HeartOfTheRain/App/Shop/ShopAssets.asset");if(!a||!a.teams||!a.catalog)throw new System.Exception("Missing Shop binding");var s=new ShopSession(JsonUtility.FromJson<ShopCatalog>(a.catalog.text));foreach(var v in a.sprites)if(!v.sprite)throw new System.Exception("Missing sprite "+v.id);foreach(var o in s.Specials)a.Find(o.art);foreach(var o in s.Mega)a.Find(o.art);foreach(var o in s.Coins)a.Find(o.art);foreach(var key in new[]{"Rocket","Bomb","RainbowOrb_R2","GoldenSeeker_R2","RewardCoin","Nav_Active"})a.Find(key);var background=ShopLayout.Build(360,640,s,0).chrome.elements.Find(e=>e.id=="background");if(background==null||background.kind!="cover"||background.asset!="TA_Background"||!a.Find(background.asset))throw new System.Exception("Shop and Teams must resolve the same cover background");Debug.Log("Shop bindings, shared Teams background and sample catalogue valid. Purchases are unavailable in this design preview.");}
 }
}
#endif

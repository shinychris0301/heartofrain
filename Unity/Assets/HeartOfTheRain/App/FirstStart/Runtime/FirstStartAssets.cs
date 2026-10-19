using UnityEngine;using HeartOfTheRain.App.Home;using HeartOfTheRain.App.AppSettings;using HeartOfTheRain.M47;
namespace HeartOfTheRain.App.FirstStart {
 [CreateAssetMenu(menuName="Heart of the Rain/App/First Start Assets")]
 public sealed class FirstStartAssets:ScriptableObject {
  public AppSettingsAssets shared;public TextAsset[] lessons;public HomeSprite[] sprites;
  public HomePageAssets Home=>shared.Home;
  public GameplayUIAssets Gameplay=>shared.gameplaySettings.approvedUI.gameplay;
  public Sprite Find(string key){foreach(var p in sprites)if(p.id==key)return p.sprite;return shared.Find(key);}
 }
}

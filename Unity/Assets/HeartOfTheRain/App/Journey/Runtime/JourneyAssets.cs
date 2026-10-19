using UnityEngine;using HeartOfTheRain.App.Home;using HeartOfTheRain.App.PreLevel;
namespace HeartOfTheRain.App.Journey
{
 [CreateAssetMenu(menuName="Heart of the Rain/App/Journey Assets")]
 public sealed class JourneyAssets:ScriptableObject
 {
  public HomePageAssets home;public PreLevelAssets preLevel;public TextAsset catalog;public HomeSprite[] sprites;
  public Sprite Find(string id){foreach(var item in sprites)if(item.id==id)return item.sprite;return preLevel.Find(id);}
 }
}

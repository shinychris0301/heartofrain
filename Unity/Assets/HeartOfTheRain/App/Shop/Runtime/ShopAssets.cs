using UnityEngine;using HeartOfTheRain.App.Home;using HeartOfTheRain.App.Teams;
namespace HeartOfTheRain.App.Shop
{
 [CreateAssetMenu(menuName="Heart of the Rain/App/Shop Assets")]
 public sealed class ShopAssets:ScriptableObject
 {
  public TeamsAssets teams;public TextAsset catalog;public HomeSprite[] sprites;
  public Sprite Find(string key){foreach(var s in sprites)if(s.id==key)return s.sprite;return teams.Find(key);}
 }
}

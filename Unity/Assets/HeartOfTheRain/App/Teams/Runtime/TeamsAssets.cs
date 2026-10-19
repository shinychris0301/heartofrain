using UnityEngine;using HeartOfTheRain.App.Home;using HeartOfTheRain.App.Leaderboard;
namespace HeartOfTheRain.App.Teams
{
 [CreateAssetMenu(menuName="Heart of the Rain/App/Teams Assets")]
 public sealed class TeamsAssets:ScriptableObject
 {
  public LeaderboardAssets leaderboard;public TextAsset demoData;public HomeSprite[] sprites;
  public Sprite Find(string id){foreach(var item in sprites)if(item.id==id)return item.sprite;return leaderboard.Find(id);}
 }
}

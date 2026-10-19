using UnityEngine;using HeartOfTheRain.App.Home;using HeartOfTheRain.App.Journey;
namespace HeartOfTheRain.App.Leaderboard
{
 [CreateAssetMenu(menuName="Heart of the Rain/App/Leaderboard Assets")]
 public sealed class LeaderboardAssets:ScriptableObject
 {
  public JourneyAssets journey;public TextAsset demoData;public HomeSprite[] sprites;
  public Sprite Find(string id){foreach(var s in sprites)if(s.id==id)return s.sprite;return journey.Find(id);}
 }
}

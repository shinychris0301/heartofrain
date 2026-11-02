using UnityEngine;
namespace HeartOfTheRain.App.Leaderboard {
 [CreateAssetMenu(menuName="Heart of the Rain/App/Leaderboard Medals")]
 public sealed class LeaderboardMedals115:ScriptableObject {
  public Sprite gold,silver,bronze;
  public Sprite Find(string id){switch(id){case "TA_Rank_Gold":return gold;case "TA_Rank_Silver":return silver;case "TA_Rank_Bronze":return bronze;default:return null;}}
 }
}

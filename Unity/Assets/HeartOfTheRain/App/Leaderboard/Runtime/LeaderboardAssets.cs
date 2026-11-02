using UnityEngine;using HeartOfTheRain.App.Home;using HeartOfTheRain.App.Journey;
namespace HeartOfTheRain.App.Leaderboard
{
 [CreateAssetMenu(menuName="Heart of the Rain/App/Leaderboard Assets")]
 public sealed class LeaderboardAssets:ScriptableObject
 {
  public JourneyAssets journey;public HomeSprite[] sprites;
  // The review roster lives under Editor and has no serialized player-build edge.
  public TextAsset demoData {
   get {
#if UNITY_EDITOR
    return UnityEditor.AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/HeartOfTheRain/App/Leaderboard/Editor/LeaderboardDemo.json");
#else
    return null;
#endif
   }
  }
  [System.NonSerialized] HeartOfTheRain.App.TeamsAccess.TeamsAccessAssets109 sharedAccess115;
  [System.NonSerialized] HeartOfTheRain.App.TeamsSocial.TeamsSocialAssets110 sharedSocial115;
  [System.NonSerialized] LeaderboardMedals115 medals115;
  public Sprite Find(string id){
#if UNITY_EDITOR
   // Review-roster portraits have no serialized player-build edge either.
   if(id!=null&&id.StartsWith("Portrait_",System.StringComparison.Ordinal))return UnityEditor.AssetDatabase.LoadAssetAtPath<Sprite>("Assets/HeartOfTheRain/App/Leaderboard/Art/"+id+".png");
#endif
   if(id!=null&&id.StartsWith("TA_Rank_",System.StringComparison.Ordinal)){if(!medals115)medals115=Resources.Load<LeaderboardMedals115>("HOTR_Leaderboard115/Medals");var medal=medals115?medals115.Find(id):null;if(medal)return medal;}
   if(id!=null&&id.StartsWith("TA_",System.StringComparison.Ordinal)){if(!sharedAccess115)sharedAccess115=Resources.Load<HeartOfTheRain.App.TeamsAccess.TeamsAccessAssets109>("HOTR_TeamsAccess109/Assets");var found=sharedAccess115?sharedAccess115.Find(id):null;if(found)return found;}
   if(id!=null&&id.StartsWith("TC_",System.StringComparison.Ordinal)){if(!sharedSocial115)sharedSocial115=Resources.Load<HeartOfTheRain.App.TeamsSocial.TeamsSocialAssets110>("HOTR_TeamsSocial110/Assets");var found=sharedSocial115?sharedSocial115.Find(id):null;if(found)return found;}
   if(sprites!=null)foreach(var s in sprites)if(s.id==id)return s.sprite;return journey?journey.Find(id):null;
  }
  public float SliceMultiplier115(string id,float referenceScale){if(id!=null&&id.StartsWith("TA_",System.StringComparison.Ordinal)){if(!sharedAccess115)sharedAccess115=Resources.Load<HeartOfTheRain.App.TeamsAccess.TeamsAccessAssets109>("HOTR_TeamsAccess109/Assets");if(sharedAccess115)return sharedAccess115.SliceMultiplier(id,referenceScale);}return 4;}
 }
}

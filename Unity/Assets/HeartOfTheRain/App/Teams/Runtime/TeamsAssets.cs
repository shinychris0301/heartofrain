using UnityEngine;using HeartOfTheRain.App.Home;using HeartOfTheRain.App.Leaderboard;
namespace HeartOfTheRain.App.Teams
{
 [CreateAssetMenu(menuName="Heart of the Rain/App/Teams Assets")]
 public sealed class TeamsAssets:ScriptableObject
 {
  public LeaderboardAssets leaderboard;public HomeSprite[] sprites;
  // The review roster is an Editor fixture, never a player-build dependency.
  public TextAsset demoData {
   get {
#if UNITY_EDITOR
    return UnityEditor.AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/HeartOfTheRain/App/Teams/Editor/TeamsDemo.json");
#else
    return null;
#endif
   }
  }
  [System.NonSerialized] public HeartOfTheRain.App.TeamsAccess.TeamsAccessAssets109 access;
  [System.NonSerialized] public HeartOfTheRain.App.TeamsSocial.TeamsSocialAssets110 social;
  [System.NonSerialized] public HeartOfTheRain.App.TeamsMail.TeamsMailAssets111 mail;
  [System.NonSerialized] public HeartOfTheRain.App.TeamsInvites.TeamsInvitesAssets112 invites;
  public bool Access109Loaded=>access;
  public bool Social110Loaded=>social;
  public Sprite Find(string id){if(id!=null&&id.StartsWith("TI_",System.StringComparison.Ordinal)){if(!invites)invites=Resources.Load<HeartOfTheRain.App.TeamsInvites.TeamsInvitesAssets112>("HOTR_TeamsInvites112/Assets");var extra=invites?invites.Find(id):null;if(extra)return extra;}if(id!=null&&id.StartsWith("TM_",System.StringComparison.Ordinal)){if(!mail)mail=Resources.Load<HeartOfTheRain.App.TeamsMail.TeamsMailAssets111>("HOTR_TeamsMail111/Assets");var extra=mail?mail.Find(id):null;if(extra)return extra;}if(id!=null&&id.StartsWith("TC_",System.StringComparison.Ordinal)){if(!social)social=Resources.Load<HeartOfTheRain.App.TeamsSocial.TeamsSocialAssets110>("HOTR_TeamsSocial110/Assets");var extra=social?social.Find(id):null;if(extra)return extra;}if(id!=null&&id.StartsWith("TA_",System.StringComparison.Ordinal)){if(!access)access=Resources.Load<HeartOfTheRain.App.TeamsAccess.TeamsAccessAssets109>("HOTR_TeamsAccess109/Assets");var extra=access?access.Find(id):null;if(extra)return extra;}foreach(var item in sprites)if(item.id==id)return item.sprite;return leaderboard.Find(id);}
 }
}

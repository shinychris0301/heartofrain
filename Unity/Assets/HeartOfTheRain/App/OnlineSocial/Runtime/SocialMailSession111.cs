using System;
using UnityEngine;
namespace HeartOfTheRain.App.OnlineSocial {
 public sealed partial class SocialPageSession82 {
  SocialMutation82 lastMailReceipt111; public SocialMutation82 LastMailReceipt111=>!ActiveOwner()||lastMailReceipt111==null?null:JsonUtility.FromJson<SocialMutation82>(JsonUtility.ToJson(lastMailReceipt111));
  void AcceptedMail111(SocialMutation82 value){if(value==null||value.operation==null||!value.operation.StartsWith("mail.",StringComparison.Ordinal))return;lastMailReceipt111=JsonUtility.FromJson<SocialMutation82>(JsonUtility.ToJson(value));ObserveLifeClock110(value.serverUtc);states.Remove(SocialPane82.TeamMail111);states.Remove(SocialPane82.OwnedMail111);}
  void ClearMail111(){views.Remove(SocialPane82.TeamMail111);views.Remove(SocialPane82.TeamMailDetail111);states.Remove(SocialPane82.TeamMail111);states.Remove(SocialPane82.TeamMailDetail111);}
  public bool RefreshOwnedMail111(long after=0)=>Read<SocialOwnedMail111>(SocialPane82.OwnedMail111,done=>client.GetOwnedMail111(after,done),value=>ObserveLifeClock110(value.serverUtc));
  public bool ClaimOwnedMail111(string command,string id)=>Mutate(SocialPane82.OwnedMail111,done=>client.ClaimOwnedMail111(command,id,done),AcceptedMail111);
  public bool RefreshTeamMail111(long before=0)=>!string.IsNullOrEmpty(teamId)&&Read<SocialMailList111>(SocialPane82.TeamMail111,done=>client.GetTeamMail111(teamId,before,done),value=>ObserveLifeClock110(value.serverUtc));
  public bool RefreshMailDetail111(string id)=>!string.IsNullOrEmpty(teamId)&&Read<SocialMailDetail111>(SocialPane82.TeamMailDetail111,done=>client.GetTeamMailDetail111(teamId,id,done),value=>ObserveLifeClock110(value.serverUtc));
  public bool ReadMail111(string command,string id)=>!string.IsNullOrEmpty(teamId)&&Mutate(SocialPane82.TeamMailDetail111,done=>client.ReadTeamMail111(command,teamId,id,done),AcceptedMail111);
  public bool ClaimMail111(string command,string id)=>!string.IsNullOrEmpty(teamId)&&Mutate(SocialPane82.TeamMailDetail111,done=>client.ClaimTeamMail111(command,teamId,id,done),AcceptedMail111);
 }
}

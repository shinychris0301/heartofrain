using System;
using UnityEngine;
namespace HeartOfTheRain.App.OnlineSocial {
 public sealed partial class SocialPageSession82 {
  SocialMutation82 lastInviteReceipt112;
  public SocialMutation82 LastInviteReceipt112=>!ActiveOwner()||lastInviteReceipt112==null?null:JsonUtility.FromJson<SocialMutation82>(JsonUtility.ToJson(lastInviteReceipt112));
  void AcceptedInvite112(SocialMutation82 value){if(value==null||value.operation!="invite.send")return;lastInviteReceipt112=JsonUtility.FromJson<SocialMutation82>(JsonUtility.ToJson(value));ObserveLifeClock110(value.serverUtc);states.Remove(SocialPane82.InviteFriends112);}
  public bool RefreshInviteFriends112(string after,string query)=>!string.IsNullOrEmpty(teamId)&&Read<SocialInviteFriends112>(SocialPane82.InviteFriends112,done=>client.GetInvitableFriends112(teamId,after,query,done),value=>ObserveLifeClock110(value.serverUtc));
  public bool RefreshReceivedInvites112(long before)=>Read<SocialInvitations112>(SocialPane82.InviteReceived112,done=>client.GetReceivedInvitations112(before,done),value=>ObserveLifeClock110(value.serverUtc));
  public bool RefreshInviteDetail112(string id)=>Read<SocialInvitationDetail112>(SocialPane82.InviteDetail112,done=>client.GetInvitation112(id,done),value=>ObserveLifeClock110(value.serverUtc));
  public bool SendInvite112(string command,string friend)=>!string.IsNullOrEmpty(teamId)&&Mutate(SocialPane82.InviteFriends112,done=>client.SendInvitation112(command,teamId,friend,done),AcceptedInvite112);
  void ClearInvites112(){views.Remove(SocialPane82.InviteFriends112);states.Remove(SocialPane82.InviteFriends112);views.Remove(SocialPane82.InviteDetail112);states.Remove(SocialPane82.InviteDetail112);}
  public void ClearInviteFriends112(){views.Remove(SocialPane82.InviteFriends112);states.Remove(SocialPane82.InviteFriends112);}
  public void ClearInviteReceived112(){views.Remove(SocialPane82.InviteReceived112);states.Remove(SocialPane82.InviteReceived112);views.Remove(SocialPane82.InviteDetail112);states.Remove(SocialPane82.InviteDetail112);}
 }
}

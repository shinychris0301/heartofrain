using UnityEngine;

namespace HeartOfTheRain.App.OnlineSocial {
 // Purely visual opacity transitions. Never changes rank or action state.
 public sealed class LeaderboardMotion115:MonoBehaviour {
  CanvasGroup[] groups;float elapsed,duration;
  public void Begin(CanvasGroup[] targets,float seconds){groups=targets;elapsed=0;duration=Mathf.Max(.001f,seconds);Apply(0);}
  public void Advance(float seconds){if(groups==null)return;elapsed+=Mathf.Max(0,seconds);Apply(Mathf.Clamp01(elapsed/duration));if(elapsed>=duration)groups=null;}
  void Update()=>Advance(Time.unscaledDeltaTime);
  void Apply(float alpha){if(groups==null)return;foreach(var group in groups)if(group)group.alpha=alpha;}
  void OnDisable(){if(groups!=null)Apply(1);groups=null;}
 }
}

using UnityEngine;
namespace HeartOfTheRain.App.TeamsLifecycle {
 public sealed class TeamsLifecycleMotion113:MonoBehaviour {
  CanvasGroup group;RectTransform rect;float duration,elapsed;bool exit,reduced;
  public void Begin(float initial,bool exiting,bool reduce){group=GetComponent<CanvasGroup>();if(!group)group=gameObject.AddComponent<CanvasGroup>();rect=(RectTransform)transform;rect.pivot=new Vector2(.5f,.5f);rect.anchoredPosition=new Vector2(rect.rect.width/2,-rect.rect.height/2);exit=exiting;reduced=reduce;duration=reduce ? 0.12f : exiting ? 0.16f : 0.22f;elapsed=Mathf.Clamp(initial,0,duration);Apply();}
  public void Advance(float delta){elapsed=Mathf.Clamp(elapsed+Mathf.Max(0,delta),0,duration);Apply();}
  void Update(){Advance(Time.unscaledDeltaTime);}
  void Apply(){if(!group||!rect)return;float t=duration<=0?1:Mathf.Clamp01(elapsed/duration);float eased=1-Mathf.Pow(1-t,3);float value=exit?1-eased:eased;group.alpha=value;float size=reduced?1:.96f+.04f*value;rect.localScale=Vector3.one*size;}
 }
}

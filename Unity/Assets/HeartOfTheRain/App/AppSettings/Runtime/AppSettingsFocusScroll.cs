using UnityEngine;using UnityEngine.EventSystems;
namespace HeartOfTheRain.App.AppSettings
{
 public sealed class AppSettingsFocusScroll:MonoBehaviour,ISelectHandler
 {
  public AppSettingsPage owner;
  public void OnSelect(BaseEventData data){if(owner)owner.Reveal((RectTransform)transform);}
 }
}

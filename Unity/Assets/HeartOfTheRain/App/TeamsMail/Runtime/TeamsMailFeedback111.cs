using System;
using UnityEngine;
using UnityEngine.UI;
namespace HeartOfTheRain.App.TeamsMail {
 // Confirmed-only visual feedback; this component has no reward callbacks.
 public sealed class TeamsMailFeedback111:MonoBehaviour {
  CanvasGroup alpha;Image letter,check;float elapsed,duration;public bool Running{get;private set;}public string ReceiptId{get;private set;}
  public void Begin(string id,Sprite openedLetter,Sprite checkSprite,Sprite star,bool reduced){if(string.IsNullOrEmpty(id))throw new ArgumentException();ReceiptId=id;duration=reduced?.12f:.18f;alpha=gameObject.AddComponent<CanvasGroup>();alpha.interactable=alpha.blocksRaycasts=false;letter=Make("Letter",openedLetter,0,0,42);check=Make("Check",checkSprite,0,0,42);if(!reduced){Make("Star left",star,-32,12,14);Make("Star right",star,32,12,14);}Running=true;alpha.alpha=1;check.color=new Color(1,1,1,0);}
  Image Make(string name,Sprite sprite,float x,float y,float size){var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(transform,false);var rt=(RectTransform)go.transform;rt.anchorMin=rt.anchorMax=rt.pivot=new Vector2(.5f,.5f);rt.anchoredPosition=new Vector2(x,y);rt.sizeDelta=Vector2.one*size;var image=go.AddComponent<Image>();image.sprite=sprite;image.preserveAspect=true;image.raycastTarget=false;return image;}
  public void Advance(float seconds){if(!Running||seconds<0||float.IsNaN(seconds)||float.IsInfinity(seconds))return;elapsed=Math.Min(duration,elapsed+seconds);float t=Mathf.Clamp01(elapsed/duration);letter.color=new Color(1,1,1,1-t);check.color=new Color(1,1,1,t);if(elapsed>=duration){Running=false;if(Application.isPlaying)Destroy(gameObject);else DestroyImmediate(gameObject);}}
  void Update(){Advance(Time.unscaledDeltaTime);}
 }
}

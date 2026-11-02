using System;
using UnityEngine;
using UnityEngine.UI;
namespace HeartOfTheRain.App.TeamsInvites {
 // Pure presentation: receipt acceptance and authoritative refresh are owned by the service.
 public sealed class TeamsInviteFeedback112:MonoBehaviour {
  Graphic current;Text previous;Color original;float elapsed,duration;public bool Running{get;private set;}public string ReceiptId{get;private set;}public float Duration=>duration;
  public void BeginConfirmed(string receiptId,Text currentLabel,string pendingLabel,bool reduced){
   if(string.IsNullOrEmpty(receiptId)||!currentLabel)throw new ArgumentException();ReceiptId=receiptId;current=currentLabel;original=current.color;duration=reduced?.12f:.14f;
   var duplicate=Instantiate(currentLabel.gameObject,currentLabel.transform.parent);duplicate.name="Previous invitation caption";previous=duplicate.GetComponent<Text>();previous.text=pendingLabel??"";previous.raycastTarget=false;previous.color=original;current.color=new Color(original.r,original.g,original.b,0);Running=true;
  }
  public void BeginTab(Graphic selected,bool reduced){if(!selected)throw new ArgumentException();current=selected;original=selected.color;duration=reduced?.12f:.14f;current.color=new Color(original.r,original.g,original.b,0);Running=true;}
  public void Advance(float seconds){if(!Running||seconds<0||float.IsNaN(seconds)||float.IsInfinity(seconds))return;elapsed=Math.Min(duration,elapsed+seconds);float t=Mathf.Clamp01(elapsed/duration);if(current)current.color=new Color(original.r,original.g,original.b,original.a*t);if(previous)previous.color=new Color(original.r,original.g,original.b,original.a*(1-t));if(elapsed>=duration){Running=false;Finish();}}
  void Finish(){if(current)current.color=original;if(previous){if(Application.isPlaying)Destroy(previous.gameObject);else DestroyImmediate(previous.gameObject);previous=null;}if(Application.isPlaying)Destroy(gameObject);else DestroyImmediate(gameObject);}
  void OnDestroy(){if(current)current.color=original;if(previous){if(Application.isPlaying)Destroy(previous.gameObject);else DestroyImmediate(previous.gameObject);}}
  void Update(){Advance(Time.unscaledDeltaTime);}
 }
}

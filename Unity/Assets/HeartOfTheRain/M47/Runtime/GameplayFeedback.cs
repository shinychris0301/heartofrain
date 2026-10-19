using System;using System.Collections.Generic;using UnityEngine;using HeartOfTheRain.M46;
namespace HeartOfTheRain.M47 {
 public sealed class GameplayFeedback:MonoBehaviour {
  public GameplayUIAssets assets;public bool soundEnabled=true,hapticsEnabled;public float masterGain=.75f;
  public event Action<string> HapticRequested;
  readonly List<FeedbackCue> cues=new List<FeedbackCue>();readonly Dictionary<string,float> cooldown=new Dictionary<string,float>();
  AudioSource[] voices;int voice;float last=-1;bool paused;
  void Awake(){voices=new AudioSource[8];for(int i=0;i<voices.Length;i++){voices[i]=gameObject.AddComponent<AudioSource>();voices[i].playOnAwake=false;voices[i].spatialBlend=0;}}
  public void SetSoundEnabled(bool value){soundEnabled=value;if(!value&&voices!=null)foreach(var v in voices)v.Stop();}
  public void Play(string id,float gain=1,string haptic=null){
   if(hapticsEnabled&&haptic!=null)HapticRequested?.Invoke(haptic);
   if(!soundEnabled||assets==null)return;float previous;if(cooldown.TryGetValue(id,out previous)&&Time.unscaledTime-previous<.045f)return;
   var clip=assets.Sound(id);if(clip==null)return;cooldown[id]=Time.unscaledTime;var v=voices[voice++%voices.Length];v.Stop();v.clip=clip;v.volume=Mathf.Clamp01(gain*masterGain);v.Play();
  }
  public void Begin(BoardStep step){cues.Clear();cues.AddRange(FeedbackPlan.Build(step));last=-.001f;}
  public void Sample(float elapsed){if(paused)return;foreach(var c in cues)if(c.time>last&&c.time<=elapsed)Play(c.id,c.gain,c.haptic);last=elapsed;}
  public void Pause(bool state){paused=state;foreach(var v in voices)if(state)v.Pause();else v.UnPause();}
  public void ResetFeedback(){cues.Clear();last=-1;cooldown.Clear();foreach(var v in voices)v.Stop();paused=false;}
 }
}

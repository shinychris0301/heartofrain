using System;using UnityEngine;using HeartOfTheRain.M46;
namespace HeartOfTheRain.M47 {
 [Serializable] public class UISpriteBinding {public string id;public Sprite sprite;}
 [Serializable] public class AudioBinding {public string id;public AudioClip clip;}
 [CreateAssetMenu(menuName="Heart of the Rain/Gameplay UI assets")]
 public sealed class GameplayUIAssets:ScriptableObject {
  public M46Assets boards;public UISpriteBinding[] sprites;public AudioBinding[] sounds;public Font regular,bold;public Shader bodyShader;
  public Sprite Get(string key){var b=Array.Find(sprites,v=>v.id==key);return b==null?null:b.sprite;}
  public AudioClip Sound(string key){var b=Array.Find(sounds,v=>v.id==key);return b==null?null:b.clip;}
 }
}

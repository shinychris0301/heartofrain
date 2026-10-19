using System;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.AppSettings;
using HeartOfTheRain.App.PreLevel;
namespace HeartOfTheRain.App.LevelComplete {
 [CreateAssetMenu(menuName="Heart of the Rain/App/Level complete assets")]
 public sealed class LevelCompleteAssets:ScriptableObject {
  public AppSettingsAssets shared;public PreLevelAssets preLevel;public HomeSprite[] sprites;
  public Sprite Find(string key){var own=Array.Find(sprites,v=>v.id==key);return own!=null?own.sprite:preLevel.Find(key)?preLevel.Find(key):shared.Find(key);}
 }
}

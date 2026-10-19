using System;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Settings;
namespace HeartOfTheRain.App.EndLevel
{
    [CreateAssetMenu(menuName="Heart of the Rain/App/End level assets")]
    public sealed class EndLevelAssets:ScriptableObject
    {
        public GameplaySettingsAssets approvedSettings;public HomeSprite[] sprites;
        public Sprite Find(string key){var own=Array.Find(sprites,s=>s.id==key);return own!=null?own.sprite:approvedSettings.Find(key);}
    }
}

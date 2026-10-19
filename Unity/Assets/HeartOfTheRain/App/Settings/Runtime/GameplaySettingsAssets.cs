using System;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.PreLevel;
namespace HeartOfTheRain.App.Settings
{
    [CreateAssetMenu(menuName="Heart of the Rain/App/Gameplay settings assets")]
    public sealed class GameplaySettingsAssets:ScriptableObject
    {
        public PreLevelAssets approvedUI; public HomeSprite[] sprites;
        [Tooltip("Original review loop. Replace after music approval.")] public AudioClip reviewMusic;
        public Sprite Find(string key){var own=Array.Find(sprites,s=>s.id==key);return own!=null?own.sprite:approvedUI.Find(key);}
    }
}

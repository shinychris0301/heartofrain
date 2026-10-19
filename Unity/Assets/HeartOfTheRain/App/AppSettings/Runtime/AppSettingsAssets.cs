using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.App.Shop;
using HeartOfTheRain.App.Settings;
namespace HeartOfTheRain.App.AppSettings
{
    [CreateAssetMenu(menuName="Heart of the Rain/App/Main Settings Assets")]
    public sealed class AppSettingsAssets:ScriptableObject
    {
        public ShopAssets shop;public GameplaySettingsAssets gameplaySettings;
        public TextAsset destinations;public HomeSprite[] sprites;
        public HomePageAssets Home=>shop.teams.leaderboard.journey.home;
        public Sprite Find(string key)
        {
            foreach(var s in sprites)if(s.id==key)return s.sprite;
            foreach(var s in gameplaySettings.sprites)if(s.id==key)return s.sprite;
            return shop.Find(key);
        }
    }
}

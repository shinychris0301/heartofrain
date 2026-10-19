using System;
using UnityEngine;
using HeartOfTheRain.App.Home;
using HeartOfTheRain.M47;
namespace HeartOfTheRain.App.PreLevel
{
    [CreateAssetMenu(menuName="Heart of the Rain/App/Pre-level assets")]
    public sealed class PreLevelAssets:ScriptableObject
    {
        public HomePageAssets home;public GameplayUIAssets gameplay;
        public HomeSprite[] sprites;public Sprite retryLifeIcon;
        [Tooltip("Review stock: Rocket, Bomb, Rainbow Orb, Golden Seeker. Connect production inventory before release.")]
        public int[] initialStock={5,5,3,2};
        [Tooltip("First-clear reward values shared with M66. Balances remain local review state until a production save service is connected.")]
        public int rewardCoins=50,rewardStars=1;
        public Sprite Find(string key)
        {if(key=="RetryLife")return retryLifeIcon;var own=Array.Find(sprites,s=>s.id==key);return own!=null?own.sprite:home.Find(key)?home.Find(key):gameplay.Get(key);}
    }
}

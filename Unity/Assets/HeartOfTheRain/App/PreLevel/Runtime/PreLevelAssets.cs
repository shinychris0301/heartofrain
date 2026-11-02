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
        {
            if(key=="LivesHeart"||key=="LivesClock"){var lives=HomeLivesAssets.Load();return !lives?null:key=="LivesHeart"?lives.heart:lives.clock;}
            if(key=="RetryLife")return retryLifeIcon;
            var own=sprites==null?null:Array.Find(sprites,s=>s.id==key);
            if(own!=null)return own.sprite;
            var shared=home==null||home.sprites==null?null:Array.Find(home.sprites,s=>s.id==key);
            if(shared!=null)return shared.sprite;
            return gameplay==null?null:gameplay.Get(key);
        }
    }
}

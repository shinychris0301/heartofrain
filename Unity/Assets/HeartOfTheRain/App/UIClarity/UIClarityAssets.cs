using UnityEngine;
using HeartOfTheRain.App.PreLevel;
namespace HeartOfTheRain.App.Profile {
    public sealed class UIClarityAssets:ScriptableObject {
        public Sprite goldenSeeker;
        public static Sprite FindReward(string id,PreLevelAssets fallback){
            // Standalone UI artwork; leave the mixed gameplay atlas sampler unchanged.
            var daily=DailyGiftDesignAssets.Load();string key=id=="Rocket"?"DG_Rocket":id=="Bomb"?"DG_Bomb":id=="RainbowOrb"?"DG_Orb":id=="boosterHammer"?"DG_Hammer":id=="RewardCoin"?"DG_Coin":null;
            if(key!=null&&daily){var sprite=daily.Find(key);if(sprite)return sprite;}
            if(id=="GoldenSeeker"){var own=Resources.Load<UIClarityAssets>("HOTR_UIClarity/Config");if(own&&own.goldenSeeker)return own.goldenSeeker;}
            return fallback.Find(id);
        }
    }
}

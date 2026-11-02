using UnityEngine;
using HeartOfTheRain.App.Profile;
namespace HeartOfTheRain.App.NoMoves {
    public sealed class NoMovesAssets:ScriptableObject {
        public Sprite band,notice,hero,badge,coin,wallet,halo,secondary,heart,pouch,mega,primary,close,chrome;
        public GameObject continuePrefab;
        public Font titleFont,bodyFont;public TextAsset strings;public ContinueRules rules=new ContinueRules();
        public static ResourceRequest LoadAsync()=>Resources.LoadAsync<NoMovesAssets>("HOTR_NoMoves/Design");
    }
}

using UnityEngine;
namespace HeartOfTheRain.App.Home {
    public sealed class HomeLivesAssets:ScriptableObject {
        public Sprite clock,heart,star;
        public static HomeLivesAssets Load()=>Resources.Load<HomeLivesAssets>("HOTR_HomeLives/Design");
    }
}

using UnityEngine;
namespace HeartOfTheRain.App.GameplayLoading {
    public sealed class GameplayLoadingAssets:ScriptableObject {
        public Sprite[] sprites;
        public Sprite Find(string name){if(sprites!=null)foreach(var s in sprites)if(s&&s.name==name)return s;return null;}
        public static GameplayLoadingAssets Load()=>Resources.Load<GameplayLoadingAssets>("HOTR_GameplayLoading/Design");
        public static ResourceRequest LoadAsync()=>Resources.LoadAsync<GameplayLoadingAssets>("HOTR_GameplayLoading/Design");
        // The uncompressed pages are resident only between the pre-level opening and the board
        // handoff; the next access reloads them from Resources.
        public void Release(){if(sprites==null)return;foreach(var s in sprites)if(s&&s.texture)Resources.UnloadAsset(s.texture);}
    }
}

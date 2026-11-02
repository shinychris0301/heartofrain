using UnityEngine;
namespace HeartOfTheRain.App.Profile {
    public sealed class WellworksDesignAssets:ScriptableObject {
        public DailyGiftDesignAssets shared;
        public Sprite well,badge,locked,track,fill,golden;
        public Sprite[] OwnedArt=>new[]{well,badge,locked,track,fill};
        public void ReleaseArt(){if(!Application.isPlaying)return;foreach(var s in OwnedArt)if(s&&s.texture)Resources.UnloadAsset(s.texture);if(shared)shared.ReleaseArt();}
        public static WellworksDesignAssets Load()=>Resources.Load<WellworksDesignAssets>("HOTR_Wellworks/Design");
        public static ResourceRequest LoadAsync()=>Resources.LoadAsync<WellworksDesignAssets>("HOTR_Wellworks/Design");
        public Sprite Find(string id){switch(id){case "WW_Well":return well;case "WW_Badge":return badge;case "WW_Lock":return locked;case "WW_Track":return track;case "WW_Fill":return fill;case "WW_Golden":return golden;default:return shared.Find(id);}}
        public static float Multiplier(string id)=>id=="DG_Chrome"?3.891f:id=="DG_Primary"?13.333333f:id=="WW_Track"?6:id=="WW_Fill"?8:6;
    }
}

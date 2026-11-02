using UnityEngine;
namespace HeartOfTheRain.App.Profile {
    public sealed class RainCupDesignAssets:ScriptableObject {
        public WellworksDesignAssets shared;
        public ProfileAssets profile;
        public Sprite trophy,frame,mask,gold,silver,bronze,rival,tab,track;
        public Sprite[] OwnedArt=>new[]{trophy,frame,mask,gold,silver,bronze,rival,tab,track};
        public void ReleaseArt(){if(!Application.isPlaying)return;foreach(var s in OwnedArt)if(s&&s.texture)Resources.UnloadAsset(s.texture);if(shared)shared.ReleaseArt();}
        public static RainCupDesignAssets Load()=>Resources.Load<RainCupDesignAssets>("HOTR_RainCup/Design");
        public static ResourceRequest LoadAsync()=>Resources.LoadAsync<RainCupDesignAssets>("HOTR_RainCup/Design");
        public Sprite Find(string id){switch(id){case "RC_Trophy":return trophy;case "RC_Frame":return frame;case "RC_Mask":return mask;case "RC_Gold":return gold;case "RC_Silver":return silver;case "RC_Bronze":return bronze;case "RC_Rival":return rival;case "RC_Tab":return tab;case "RC_Track":return track;default:return shared.Find(id);}}
        public static float Multiplier(string id)=>id=="DG_Chrome"?3.891f:id=="DG_Primary"?8.57f:id=="RC_Track"||id=="RC_Tab"||id=="WW_Track"||id=="WW_Fill"?8:6;
    }
}

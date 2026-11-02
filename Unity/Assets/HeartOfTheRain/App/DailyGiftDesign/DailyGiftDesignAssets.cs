using UnityEngine;
namespace HeartOfTheRain.App.Profile {
    public sealed class DailyGiftDesignAssets:ScriptableObject {
        public Sprite chrome,close,primary,check,coin,chest,hero,star;
        public Sprite upcoming,today,collected,bonus,rocket,bomb,hammer,orb;
        public Font titleFont,bodyFont;
        // Only art no other page uses: chrome, close, primary, check and star are shared with Home's dialogs.
        public Sprite[] OwnedArt=>new[]{chest,hero,upcoming,today,collected,bonus,rocket,bomb,hammer,orb};
        // Unity reloads an unloaded texture when the page next draws it.
        public void ReleaseArt(){if(!Application.isPlaying)return;foreach(var s in OwnedArt)if(s&&s.texture)Resources.UnloadAsset(s.texture);}
        public static DailyGiftDesignAssets Load()=>Resources.Load<DailyGiftDesignAssets>("HOTR_DailyGift/Design");
        public static ResourceRequest LoadAsync()=>Resources.LoadAsync<DailyGiftDesignAssets>("HOTR_DailyGift/Design");
        public Sprite Find(string id){switch(id){
            case "DG_Chrome":return chrome;case "DG_Close":return close;case "DG_Primary":return primary;case "DG_Check":return check;
            case "DG_Coin":return coin;case "DG_Chest":return chest;case "DG_Hero":return hero;case "DG_Star":return star;
            case "DG_Upcoming":return upcoming;case "DG_Today":return today;case "DG_Collected":return collected;case "DG_Bonus":return bonus;
            case "DG_Rocket":return rocket;case "DG_Bomb":return bomb;case "DG_Hammer":return hammer;case "DG_Orb":return orb;default:return null;
        }}
    }
}

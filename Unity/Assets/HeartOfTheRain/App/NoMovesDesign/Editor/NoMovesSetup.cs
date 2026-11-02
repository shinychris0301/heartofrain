#if UNITY_EDITOR
using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using HeartOfTheRain.App.AccountDesign;
using HeartOfTheRain.App.Profile;
namespace HeartOfTheRain.App.NoMoves.Editor {
    public static class NoMovesSetup {
        public static void Configure(){
            const string root="Assets/HeartOfTheRain/App/NoMovesDesign/";
            Directory.CreateDirectory("Assets/HeartOfTheRain/Resources/HOTR_NoMoves");AssetDatabase.Refresh();
            var shared=AccountDesignAssets.Load();if(!shared)throw new InvalidOperationException("Shared Account art missing");
            const string path="Assets/HeartOfTheRain/Resources/HOTR_NoMoves/Design.asset";
            var a=AssetDatabase.LoadAssetAtPath<NoMovesAssets>(path);if(!a){a=ScriptableObject.CreateInstance<NoMovesAssets>();AssetDatabase.CreateAsset(a,path);}
            Sprite S(string name){var s=AssetDatabase.LoadAssetAtPath<Sprite>(root+"Art/"+name+".png");if(!s)throw new InvalidOperationException("Missing No Moves art: "+name);return s;}
            a.band=S("NM_Continue_Band");a.notice=S("NM_Notice_Band");a.hero=S("NM_Dariya_Continue");a.badge=S("NM_Moves_Badge");a.coin=S("NM_Coin_Glyph");a.wallet=S("NM_Wallet_Pill");a.halo=S("NM_Offer_Halo");a.secondary=S("NM_Secondary");a.heart=S("LifeLostHeart");a.pouch=S("SP_CoinPouch");a.mega=S("SP_Mega");
            a.primary=shared.primary;a.close=shared.close;a.chrome=shared.chrome;a.titleFont=shared.titleFont;a.bodyFont=shared.bodyFont;a.strings=AssetDatabase.LoadAssetAtPath<TextAsset>(root+"Localization/No_Moves_Strings.json");
            a.continuePrefab=AssetDatabase.LoadAssetAtPath<GameObject>(root+"Generated/ContinueOverlay_R3.prefab");if(!a.continuePrefab)throw new InvalidOperationException("Build Continue R3 prefab first");
            a.rules=new ContinueRules{enabled=true,coinCost=900,extraMoves=5,maximumContinues=0};EditorUtility.SetDirty(a);AssetDatabase.SaveAssets();
            Debug.Log("No Moves R2 configured with supplied import settings; shared importers preserved. Approved development policy only, no IAP or production wallet provider.");
        }
    }
}
#endif

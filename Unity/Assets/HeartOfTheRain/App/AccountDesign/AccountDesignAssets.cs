using UnityEngine;
namespace HeartOfTheRain.App.AccountDesign {
    public sealed class AccountDesignAssets:ScriptableObject {
        public Sprite chrome,close,primary,banner,apple,google,check,shield;
        public Font titleFont,bodyFont;
        public static AccountDesignAssets Load()=>Resources.Load<AccountDesignAssets>("HOTR_Account/Config");
    }
}

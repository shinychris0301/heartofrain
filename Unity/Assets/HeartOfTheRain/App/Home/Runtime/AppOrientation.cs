using UnityEngine;

namespace HeartOfTheRain.App
{
    // Launch and resume use the same policy, before any page chooses its layout.
    // The Android activity also declares portrait, covering the native splash.
    public static class AppOrientation
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSplashScreen)]
        static void Initialize()
        {
#if UNITY_ANDROID || UNITY_IOS
            if(Application.isEditor)return;
            Apply();
            Application.focusChanged-=OnFocus;
            Application.focusChanged+=OnFocus;
#endif
        }

        static void OnFocus(bool focused){if(focused)Apply();}

        public static void Apply()
        {
            Screen.autorotateToPortrait=true;
            Screen.autorotateToPortraitUpsideDown=false;
            Screen.autorotateToLandscapeLeft=false;
            Screen.autorotateToLandscapeRight=false;
            Screen.orientation=ScreenOrientation.Portrait;
        }
    }
}

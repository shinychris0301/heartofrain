using UnityEngine;
namespace HeartOfTheRain.App.Localization
{
    public static class LocaleBootstrap
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Initialize(){int value=PlayerPrefs.GetInt(GameLocale.PreferenceKey,0);GameLocale.Select(GameLocale.Valid(value)?value:0);}
    }
}

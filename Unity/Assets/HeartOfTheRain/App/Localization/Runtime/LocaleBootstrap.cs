using UnityEngine;
namespace HeartOfTheRain.App.Localization
{
    public static class LocaleBootstrap
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Initialize(){GameLocale.Select(GameLocale.ResolveStored(PlayerPrefs.GetInt(GameLocale.PreferenceKey,GameLocale.DefaultIndex)));}
    }
}

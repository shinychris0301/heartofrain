// BUILD-ONLY fixture. No scene component, bootstrap, SDK initialization or ad request.
using System;
using YandexMobileAds;
using YandexMobileAds.Base;

public static class Yandex85ApiReference {
    public static string VersionContract { get { return typeof(RewardedAdLoader).FullName + "/" + typeof(RewardedAd).FullName; } }
    // This method is intentionally never called. It checks the actual pinned
    // SDK signatures at compilation, including the Android build branch.
    private static void CompileOnly(RewardedAdLoader loader, RewardedAd ad) {
        loader.LoadAd(new AdRequest("demo-rewarded-yandex"), loaded => { }, failed => { });
        loader.CancelLoading();
        ad.OnRewarded += (sender, reward) => { int amount = reward.amount; string type = reward.type; };
        ad.OnAdShown += (sender, value) => { };
        ad.OnAdDismissed += (sender, value) => { };
        ad.OnAdFailedToShow += (sender, value) => { };
        YandexAds.SetUserConsent(false);
        YandexAds.SetLocationTracking(false);
        YandexAds.SetAgeRestricted(true);
        ad.Show();
        ad.Destroy();
    }
}

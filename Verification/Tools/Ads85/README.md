These tools prepare and compile a **separate build-only project**. They do not import the SDK into the ordinary game, launch an application, load an ad, claim a reward or change Unity's installed toolchain.

The vendor input is the official `yandex-mobileads-lite-8.6.0.unitypackage`, SHA256 `0d0a2546dd752d6b02864df5833767703ae88d5b292da0e0b8eec815d7f066c3`. Archive contents are read as data with bounds, traversal/link and case-collision checks. Official Android runtime and plugin bytes/GUIDs are preserved; vendor Editor/resolver hooks, inspector components and iOS implementations are excluded from this Android fixture. The omitted paths are recorded. Explicit Gradle dependencies replace the omitted resolver. AppMetrica is required by Yandex and remains a transitive dependency; the profile pins version8.6.0 rather than allowing the native SDK's open version range to drift.

Root-operated preparation, after the SDK package is present:

```powershell
.\.venv\Scripts\python.exe Verification/Tools/Ads85/prepare_yandex85_sdk.py `
  --integration Unity/Assets/HeartOfTheRain/App/Advertising/Runtime/RewardedAdsContracts85.cs `
  --integration Unity/Assets/HeartOfTheRain/App/Advertising/Runtime/YandexRewardedAdsProvider85.cs
```

The project must be new; previous exports and build attempts are retained. Only explicitly supplied Advertising C# files are copied from the main project. The isolated project's defines compile the actual SDK branch. The API-reference method is never invoked. The scene is an empty camera with no SDK bootstrap or ad-loading component.

Root runs these phases **sequentially**, with no other Unity process:

```powershell
.\.venv\Scripts\python.exe Verification/Tools/Ads85/run_yandex85_sdk_build.py --execute --phase export
.\.venv\Scripts\python.exe Verification/Tools/Ads85/run_yandex85_sdk_build.py --execute --phase assemble-stock
```

The export preserves the pinned Unity2022.3.62f3 Editor and its supported embedded Java11 preferences. The stock assembly is a compatibility control using installed Gradle7.5.1/AGP7.4.2. A failure is evidence, not permission to change the main engine or suppress incompatibility checks.

Only after reviewing the stock result, root may explicitly supply already-installed external Java17 and Gradle8.9 distributions:

```powershell
.\.venv\Scripts\python.exe Verification/Tools/Ads85/run_yandex85_sdk_build.py `
  --execute --phase assemble-modern --jdk17 <reviewed-Java17-directory> --gradle89 <reviewed-Gradle8.9-directory>
```

The modern phase copies the Gradle export, patches only that derivative to AGP8.7.0, removes Unity's older local AAPT2 override, and removes source-manifest package attributes only when an identical module namespace already exists. Every change and tool binary is hashed. It does not download or install toolchains. Gradle will resolve the declared public Maven dependencies; generated dependency locks and actual resolution/build output must be reviewed. A successful modern assembly is an **isolated external build-profile result**, not stock Unity support or approval to migrate the ordinary build automatically. A timeout stops the owned launcher only; root must confirm any single-use Gradle worker cleanup before another build.

Yandex's official Android8.6 integration guide requires AGP8.7 or newer and compileSdk35; its Unity quick-start text is less specific. Both sources are retained as a compatibility caveat. The actual native8.6.0 `YandexAds` class is Java11 bytecode and provides the four primitive-boolean privacy methods; that alone does not prove the complete dependency graph works with the stock toolchain.

Privacy must be checked again in the **merged** manifest and runtime: SDK automatic initialization disabled, no location permission, advertising-ID permission excluded in this conservative fixture, location tracking false, AppMetrica ad analytics reporting false and an explicit consent/age decision before a loader is constructed. AppMetrica's required internal SDK operation is not a claim that all provider processing has been eliminated. The adapter is dormant without `HOTR_YANDEX_ADS`; `demo-rewarded-yandex` additionally requires the isolated-fixture define plus a Development build. No live ad should be clicked or used in these build checks.

Yandex explicitly does not support server-side rewards. `OnRewarded` is client-reported information only. Capped server receipts may limit abuse but cannot turn that callback into provider-authenticated completion. No package ID, ad-unit ID, Yandex account, publisher approval, consent/legal policy, revenue, live reward or release certification is created by these tools.

Primary references:

- [Unity integration](https://ads.yandex.com/helpcenter/en/dev/unity/quick-start)
- [Android integration and automatic initialization](https://ads.yandex.com/helpcenter/en/dev/android/quick-start)
- [SDK8 privacy API migration](https://ads.yandex.com/helpcenter/en/dev/android/release/8-0-0-migration)
- [AppMetrica integration and analytics reporting control](https://yandex.com/support/appmetrica-io/en/common/ads-sdk-integration)
- [Yandex FAQ: no server-side rewards](https://ads.yandex.com/helpcenter/en/support/faq/sdk-integration)
- [Official AGP/Gradle version table](https://developer.android.com/build/releases/about-agp)

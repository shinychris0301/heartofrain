# First moderation and purchase-test sequence

1 November 2026. The owner approved this two-stage sequence. A signed first-moderation APK was built and installed on a physical Android phone. At that build checkpoint, Console submission and moderation had not occurred.

1 November follow-up: the owner reports that the product has now been submitted to RuStore for review. The Console submission receipt, exact uploaded APK hash and manual-publication setting have not been independently inspected in this workspace. The artifact JSON below remains the immutable build-time receipt. Current work and release gates are tracked in [AFTER_SUBMISSION_PLAN131.md](AFTER_SUBMISSION_PLAN131.md).

RuStore's current payment-testing guide says that sandbox payments require the app's first version to pass moderation. Its manual-release setting lets a moderated version remain at “Ready for publication” instead of publishing automatically. Product publication is not required for sandbox testing after moderation. See the official [payment-testing guide](https://www.rustore.ru/help/en/developers/monetization/sandbox) and [manual-release guide](https://www.rustore.ru/help/en/developers/publishing-and-verifying-apps/app-publication/setting-up-publication/instant-app-publishing).

The ordinary checkout guard still requires a Development build for sandbox checkout. The explicit `HOTR_FIRST_MODERATION130` profile permits a signed non-Development staging build only when checkout initiation is compiled out and its separate strict guard passes. The earlier `Verification/Tools/Review129/build_review129.py` inserts early returns into four guards; it was not used for this artifact.

## Approved sequence

1. Implement an explicit **first-moderation** build profile with its own testable guard. It must be signed with the existing release identity, non-debuggable, portrait, Android API 26+, and bound to the staging API. Checkout initiation and paid offers must be absent or visibly unavailable in that profile, both in runtime and build verification. Do not represent staged coins as a paid purchase. Guest gameplay, legal links, VK sign-in and supported social features must still work. Any advertising included must use the approved 1 November privacy version and real units, with no demo switch.
2. Run native Unity/Android tests, inspect APK manifest/signature and install the exact candidate on a physical device. Exercise first run, gameplay, navigation, legal links, VK return and unavailable-purchase behavior. Submit it for initial moderation with **manual publication**; supply moderator test instructions for any account-bound feature. Do not publish this temporary profile to players.
3. After first-version moderation, enable RuStore Console test mode for named tester accounts and test all 12 registered products on a correctly signed Android build: success, cancellation, interruption, duplicate callbacks, app restart and delivery recovery. Confirm product IDs, amount labels, wallet credits and order journals against the staging backend.
4. Build a new non-Development production candidate with purchases enabled only after production authority, product availability, full provider tests, refund handling, live ad behavior and account recovery are accepted. Reuse the same signing identity and increment versionCode. Submit that version for moderation and publish manually after final acceptance.

## Built first-moderation artifact

- Local file: `Release/RuStore/Builds/HeartOfTheRain_FirstModeration130.apk` (generated, ignored by Git; 302,091,130 bytes).
- SHA-256: `c91a32458b6feba3a50bd1f3cfd180efe2c2408d4b023486c227b5672c9068d3`.
- `com.heartoftherain.game`, versionCode 130, versionName `0.9.130`; API 26 minimum and API 36 target; portrait activity; Russian label.
- APK signature verified with the retained release certificate SHA-256 `7257537a5b329cc5b018d93299d748404432c1b49f1b2388444ab843a4ba170d`. BuildOptions.None and the manifest contains no debuggable flag.
- Checkout host is compiled inactive. On the realme RMX3938, tapping a shop offer displayed “Purchases are unavailable in this preview” and no checkout was launched. Home loaded the staging profile and Teams loaded its recommended list. Android installation preserved the existing package data. No Android fatal exception was observed in this smoke pass.
- The native Unity 6 build had zero errors and three IL2CPP compiler advisories for large methods (`M07.ReviewPlan.Build`, `M46.ReviewPlan.Build`, `JourneyText` static initializer). A duplicate `INTERNET` permission declaration was removed from this isolated build; the final merged APK retains the permission.
- The build runner reads signing credentials from the existing local Windows custody, keeps them out of source and its receipt, and scrubs generated text files afterward. Any repeat build must use a fresh isolated project without generated `Library/Bee` credential files.
- The final build starts the three independent Home reward metadata reads together. A single realme cold-start comparison showed the badges ready by a capture near 26 seconds, versus still pending near 22 seconds and ready by a later 40-second capture before this change. Network conditions were not held constant. Wallet/life data and the loading art still appeared later than desired; see `Verification/Evidence/Review130/FirstModerationDevice.json`.

The approved public privacy/terms pages and 1 November ad configuration are packaged. Actual rewarded/interstitial ad callbacks, successful VK authorization, every gameplay level, and Console moderation are **not** verified by this smoke pass. The staging recommended team list currently includes `QAStaging1030`; review its content before submission. The first version must remain under manual publication and must not be presented as a purchase-enabled public launch.

## Console handoff

1. In RuStore Console, select manual publication for this first version and upload the exact APK above. Keep it unpublished after moderation.
2. Confirm versionCode 130 and the package/signature in the Console upload result. Save the moderation result and any rejection details.
3. After the first version passes moderation, test registered products in RuStore sandbox on a physical device, including successful, cancelled, interrupted, duplicate and restart recovery paths. The later purchase build must use a higher versionCode and the same release signer.

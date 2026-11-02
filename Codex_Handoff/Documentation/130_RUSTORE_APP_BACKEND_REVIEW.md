# 130 — RuStore app and backend review

1 November 2026. This review covers the published privacy pages, Yandex ads, VK sign-in, RuStore checkout, Unity application and staging backend. A separate first-moderation APK has now been built and installed on a physical phone; this does not certify a purchase-enabled production release.

## First-moderation follow-up

The owner approved a signed first version with purchases disabled, to be held under manual publication until RuStore moderation permits sandbox payment testing. The explicit `HOTR_FIRST_MODERATION130` guard passed 10 Editor checks under both Unity 2022 and pinned Unity 6 conditions. The isolated Unity 6 release APK built with zero errors, three IL2CPP large-method advisories, versionCode 130, API 26/36 and the existing release signer. On the realme RMX3938 it installed over versionCode 127 without clearing data, Home and Teams loaded from staging, and the Shop offer detail stated purchases were unavailable; no payment interface opened. The duplicate Android `INTERNET` permission warning was removed in the isolated build while the final APK retains the permission. The three independent Home reward reads now run together; a single sampled cold start showed badges ready near 26 seconds instead of after a capture near 40 seconds, but loading art and placeholders remain visible. See `Release/RuStore/FIRST_MODERATION130.md` and `Verification/Evidence/Review130/FirstModerationDevice.json`.

## Corrections made

- The Settings page already had Privacy Policy, Terms of Service and Support actions, but `AppSettings/Data/OfficialLinks.json` left all three URLs empty. The actions now open the published HTTPS routes at `api.novamind-it.ru`. `AppSettingsReview.Validate` requires those three destinations to be present and HTTPS-valid. Social destinations remain empty until official channels exist.
- `InterstitialAds129` now records an impression only when the SDK reports `OnAdShown` or `OnAdDismissed`. An `OnAdFailedToShow` callback does not consume that level's placement. The scripted provider tests cover that case.
- Removed the unused `readRefreshing` field from `ServerGameSession`, which caused a Unity CS0414 warning.
- Published `Release/Production130/public` with owner approval: revised Russian privacy and terms text disclose the new pre-level interstitial and avoid treating `SetUserConsent(false)` as proof that all served ads are non-personalized. The 31 October edition remains pinned in `Release/Production122/public` for historical reference. The approved revision passed 163 local Chromium layout checks and live hash-pinned deployment; see `Release/Production130/PUBLISHED20261101.md`.

## Verification run

| Check | Result | Limit |
| --- | --- | --- |
| Backend `python -m unittest discover -s tests -t . -p test_*.py -q`, with both `Backend` and `Backend/tests` on `PYTHONPATH` | 962 run: 961 passed, 1 skipped, 420.063 s | The native full-history replay integration needs an explicit Unity worker. Test framework emitted one `StarletteDeprecationWarning`; no backend runtime exception was reported. |
| Unity 2022.3.62f3 `Interstitial129Verification.Run` | 98 checks passed; final log has no C# compile warning or error | Scripted provider, not a real Yandex inventory fill. |
| Unity `AdvertisingCombined126Verification.Run` | 24 checks passed | Scripted SDK and service boundaries. |
| Unity graphical `ShopCheckout86Verification.Run` | 3,530 checks and 14 UI captures passed | Scripted SDK and authority; no real RuStore purchase. Headless mode cannot validate image colors, so the graphics run is authoritative. |
| Unity graphical `VkSignin102Verification.Run` | 793 checks passed | Scripted provider; no completed VK login on a phone. |
| Unity `AppSettingsReview.Validate` after URL binding | Passed; no C# compile warning or error | Checks bindings and URLs, not a phone browser launch. |
| Live staging HTTPS `/healthz`, `/readyz`, and public privacy/terms/support | Healthy and HTTP 200 at review time | Backend reports `productionEnabled:false`. |
| Connected realme phone, installed versionCode 127 | No fatal Unity or Android exception in the sampled logcat window | This is the older development build; the new corrections were not installed or device-tested. |

Detailed local machine logs and reports are in `.verification-cache/Review130`. They are generated evidence, not release assets.

## Review-build and launch gates

1. The main Unity ad configuration remains intentionally disabled, with an empty privacy URL. The isolated first-moderation APK has the approved ads and legal version packaged, but its checkout host is compiled inactive. It has not been submitted or moderated. The earlier `build_review129.py` guard-bypass helper was not used.
2. The revised legal pages are published and independently verified. The first-moderation APK uses the 1 November advertising privacy version. Recheck all three public routes before Console submission. The main project's ordinary advertising resource remains intentionally disabled.
3. Test the actual Yandex rewarded and interstitial units on Android, including no fill, failed-to-show, cancellation, duplicate callbacks, and returning from an external ad page. The phone evidence so far used Yandex demo inventory.
4. Complete a real VK sign-in and callback on Android, including cancel, invalid state, restart, and account-link recovery. Current native tests use a scripted provider; earlier phone evidence reached the VK site but stopped at cancellation.
5. Confirm the RuStore Console app and all 12 products are published for the review package. The registration manifest says `registered:true`, while each `published` field and the application ID remain unverified. A prior real SDK attempt returned `Application not found` (4000002). Complete sandbox successful, cancelled, interrupted, duplicate and restore purchase tests on the actual signed Android build.
6. Backend purchase mode is currently owner-selected `sdk_client_reported`. The backend is idempotent and rejects incompatible amount/currency, but this mode accepts the authenticated client's SDK status; independent store-provider verification is available as `provider_api` and remains a stronger release choice. Production activation is still disabled.
7. The versionCode 130 APK passed only a narrow realme smoke run: Home, Shop disabled purchase detail, Teams and crash-free startup. Run broader physical-phone and tablet checks for Russian text, screen bounds, legal links, VK callback, ad transitions, restart recovery and backend reconnect. Payment tests require first moderation and the later purchase build.

No credentials, private keys, payment tokens or user chat content are recorded in this review.

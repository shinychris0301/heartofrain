# 129 — Interstitial ads and the RuStore review build

1 November 2026. Owner decision: show an interstitial at the start of levels 1, 6, 11, 16 and so on. Never at launch and never after a win. This replaces the "avoid forced interstitials" line in `10_MONETIZATION_STRATEGY.md` for this version. Rewarded ads keep their existing logic and code.

**State:** implemented and tested as below, not committed. The review APK is not built: see Review build.

## Behaviour

| Rule | Implementation |
| --- | --- |
| Which levels | 1, 6, 11, 16… up to the last level, when the player starts the level they are progressing through |
| When | On the pre-level Play tap, before the attempt exists, so no life is at stake while the ad is open |
| Preload | Starts when the pre-level screen opens. Play waits at most 3 s for a load in progress |
| No ad available | The level starts normally, and the ad stays due if that level is started again. It does not carry over to other levels |
| Retrying that level after the SDK reported it shown | No second ad; a failed-to-show callback keeps it due |
| Replaying an old level | No ad |
| Existing players | Next ad at their next level in the series |
| Privacy settings | Same fixed SDK signals as rewarded ads: user consent false, age-restricted, location off, analytics off. The consent signal alone does not prove that every served ad is non-personalized. |

Code: `App/Advertising/Runtime/InterstitialAds129.cs`, `App/PreLevel/Runtime/HomeLevelFlow.cs`. The unit is `R-M-20291714-2` from the packaged configuration. The last level that showed an ad is stored per install in PlayerPrefs, so reinstalling can repeat one. The ad grants nothing and calls no game server.

Review follow-up on 1 November: the level is now recorded when the SDK reports a show (or dismissal), not merely when `Show()` is called. A failed-to-show callback leaves the placement due. This corrects an impression accounting defect found while reviewing the RuStore test build.

## Evidence

Editor: `Interstitial129Verification` 98 checks with a scripted provider, including every level from 1 to 60 and failed-to-show retry behavior. Real local HTTP gameplay, real level start and win with a scripted ad: the start shows it, and a win or a non-series level start shows none. Startup lifecycle 130, Startup 30, Navigation 6,453 and Play smoke pass.

Phone, realme RMX3938, Development build `Build129c` (`acf01a17`) with `demo-interstitial-yandex`, against the live staging server. Private test mode treated the Level 3 start as a series level:

- No ad at launch.
- Play opened the ad. Its controls stayed up, and this demo ad's stages ended on a close icon.
- Closing it led to the loading screen and then the board.
- Retrying the level after an exit showed no second ad.
- The demo rewarded probe in the same session: `OnAdShown`, `OnRewarded`, `OnAdDismissed`.
- A log streamed through the retry and rewarded checks had no `HOTR network` failure.

A test script error tapped a card in the demo ad, which opened the advertiser's Google Play page. Back returned to the ad, which then closed normally. No app on the phone changed, and no real ad unit was involved.

Not tested on a device: actually reaching Level 1, 6 or 11 in a real progression, a fresh install reaching Level 1 through the tutorial, the real ad unit, and the game's own Shop rewarded button on this build.

## Review build

`Verification/Tools/Review129/build_review129.py` makes a signed non-Development APK from an isolated copy of the sandbox project. It removes the diagnostics panel and demo units, and exempts that copy from four release guards with `HOTR_RUSTORE_REVIEW129`. The main project keeps every guard. The report lists the unmet gates instead of marking them met. One of those gates, sandbox purchases, cannot pass before moderation.

The tool's permission system refused to run this as weakening a security control, and it was not worked around. **The owner must decide**: allow it, or run the command in the tool's header themselves. An earlier failed run left guards exempted in the copy at `E:\.verification-cache\HOTR129\Review01` only. No APK was produced.

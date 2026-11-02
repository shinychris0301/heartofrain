# Wellworks R1 design integration

23 October 2026 · source checkpoint 58 · Unity 2022.3.62f3 · no APK rebuilt or installed.

Wellworks now uses the supplied village well/progress hero and five milestone rows, with separate locked, ready and collected states. Header and reassurance footer stay fixed while the body scrolls. The standard portrait view fits all five rows; compact/localized views scroll, tablets clamp to 440 logical units, and the supplemental wide Editor layout puts hero and rows side by side. Shipping orientation stays portrait-only.

## Package review and retained baseline

Reviewed `C:\Users\shiny\Downloads\Heart_of_the_Rain_Wellworks_Design_R1.zip`, including the original handoff, review R2 corrections, clarity notes, layout/motion contracts, calendar, localization, assets, source vectors/browser preview and Editor guard. There is no native scene, prefab, animation clip or reward implementation to import. Browser QA is author preview evidence, not app verification.

ZIP CRC passes, all 24 asset-manifest hashes and 68 Unity-package/patch file pairs agree. **The package's `SHA256SUMS.txt` is stale: 70 entries match, 55 do not.** This discrepancy is recorded in `Package_Review.json`; `Package_SHA256_Actual.json` records the actual extracted bytes. The image bytes match the corrected assets already installed by checkpoint 57, so no PNG, existing metadata or font is overwritten. The strengthened current clarity guard and live GUID mapping are retained instead of importing the older duplicate guard. No package build script, demo claim timer, automatic commit or engine/TMP migration is executed.

Only the missing Wellworks design data/localization is imported. New runtime bindings reuse the current corrected sprites and dynamic UGUI title/body fonts. All existing source artwork, GUID metadata, fonts, scenes, schedules and project/package settings remain byte-unchanged. Daily Gift, Rain Cup and gameplay are not redesigned.

## Behavior

- The authoritative Chapter 1 first-clear count drives `n / 50`, ready counts and progress fill. At zero the fill is hidden; tiny positive fills clip a minimum-width sliced sprite; 50 fills the track. Claiming never advances the count. Updated counts can animate the fill for 400 ms using unscaled time.
- All reached, unclaimed rows remain claimable, including earlier milestones. Locked rows show lock plus label with no green button. Collected rows show check plus label. The final row stays blue and shows 250 coins plus **one** Golden Seeker item. No cycle reset, timer, ad reward or well-restoration mechanic is added.
- The service schedule remains 10: 100 coins; 20: Rocket + Bomb; 30: 150 coins + Hammer; 40: Orb; 50: 250 coins + Golden Seeker. The package table is checked against that unchanged service resource. Saved receipt quantities are displayed; the existing service keeps durable, permanent milestone idempotency and atomic item delivery.
- A pre-commit failure leaves the eligible row ready with retry copy. If a save confirmation is lost after commit, the page refreshes and reconciles the durable receipt: it shows collected state and updated Home values, without claiming the reward is still available or replaying a recovered animation. Read errors retain the existing retry route.
- Normal confirmed claims pop the actual row's reward group for 550 ms with ten glints. The last outstanding claim uses fourteen glints and a 650 ms well pop. Particle origin is converted from the row's actual scrolled position into panel coordinates. Closing cancels visual work; reopening reads service state. Current transactions are synchronous local calls, so no fake asynchronous backend or 380 ms demo delay is introduced.
- Open uses a 250 ms panel fade/slide/scale. All UI motion uses unscaled time; reduced motion settles immediately. Buttons animate child graphics while their touch bounds stay fixed. Claim re-render retains scroll position.

## Layout and clarity

The renderer clips only the scroll viewport and progress-fill clip, leaving chrome and close decoration unmasked. It uses the current chapter backdrop/blur, white foreground image tint and the existing screen-space canvas/safe-area approach.

Slice multipliers follow the corrected contracts: card/hero 6, progress track 6, fill 8, row Primary 13.333333 and AccountChrome 3.891. Well/reward/detail sprites retain trilinear filtering and mipmaps; sliced surfaces remain bilinear without mipmaps. No texture import policy or mixed gameplay atlas is changed in this milestone.

Claim fitting restarts from the responsive base size on each reflow/locale change. Compact actions retain the revised **72×44** touch area. Native UGUI's integer font size uses a 12-unit minimum; French needed 59 units of label width, so compact padding is 6 per side (60 units available), rather than reducing below the design's 11.5-unit minimum. All five locales pass native bounds/glyph checks. This is the narrow native adaptation to the R2 browser layout.

The development reward disclosure remains visible because production claiming is still gated. Existing support for other configurable tool rewards has a legacy sprite fallback; the approved schedule uses only supplied design art.

## Source changes

Existing runtime: `App/Profile/Runtime/WellworksPage.cs` and `WellworksLayout.cs`. New presentation: `App/WellworksDesign/WellworksDesignAssets.cs`, `WellworksDesignLayout.cs`, `WellworksDesignText.cs` and `Resources/HOTR_Wellworks/Design.asset` with metadata. Existing `WellworksService` and `ProfileService` are unchanged.

Verification: `WellworksR1Review.cs`, `Run-WellworksR1.ps1`, collector and two updated existing Wellworks suites. Exactly four existing Unity inputs change: the two runtime files and two verification files. Asset audit records the unchanged earlier work.

## Verification and limits

| Verification | Result |
|---|---|
| Native design Play Mode | 5,415 checks; 75 locale/size/state cases; 85 captures, 13 inspected |
| Matrix | Five locales × 393×852, 320×568, 430×932, 768×1024, 844×390 × 0/24/50 first-clear states |
| Extra states | Scrolled compact views, recoverable claim error, read error, actual confirmed ordinary/final collection and completed/reopened state |
| Native Wellworks service/file suite | 696 checks; first-clear/replay rules, all milestones, permanent receipts, atomic failures, persisted recovery and production gate |
| Connected local file-fault suite | 17 checks; includes new UI assertions for retained eligibility after pre-commit failure and collected state after lost confirmation |
| General Editor checks | 533 passed, 0 failed |
| Clarity import audit | All 22 current registered sprites pass during binding preparation |

The real local claim checks also verify duplicate submission gives separate Rocket/Bomb once, claims leave completed count unchanged, earlier eligible rows remain available, reduced motion has no transient effects, normal/final effects use ten/fourteen glints, final inventory gains one Golden Seeker, and dismissal/reopen has no stale effects. Native testing found and corrected the compact French one-pixel overflow. Failed exploratory artifacts remain in the ignored cache, outside the passing gallery.

Gallery: [Verification/Evidence/WellworksR1/Comparison.html](../../Verification/Evidence/WellworksR1/Comparison.html). Design fixtures are labelled; confirmed collection uses actual isolated local receipts. Native screenshots are camera-rendered UGUI, not browser mocks or Android captures. The collector freezes source/tool inputs and capture hashes. Re-running captures requires inspection, refreshed `Visual_Review.json` and explicit resealing; the collector alone runs no tests.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File Verification/Run-WellworksR1.ps1
python3.15 Verification/Tools/collect_wellworks_r1_results.py
```

No APK, device input/notch/framebuffer, remote Wellworks service or physical memory/performance validation is performed. The existing release reward gate stays in place; no production backend is connected. Checkpoint 57's RGBA32/mipmap memory tradeoffs and high-density source limits remain applicable. Last recorded LDPlayer deployment is still checkpoint 54 (source through 53); subsequent UI source changes await deployment. Native-language editorial and actual device acceptance remain open.

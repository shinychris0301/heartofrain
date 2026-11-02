# Daily Gift R1 native integration

23 October 2026 · Unity 2022.3.62f3 · source checkpoint 56 · no APK rebuilt or installed.

Daily Gift now uses the supplied village chest, larger three-column reward cards, collected checks, current-day marker and full-width Day 7 bonus. The header and Claim/Done footer stay fixed while the body scrolls on short screens. The modal clamps to 440 logical units on tablets and uses the current chapter backdrop with the established profile blur. The existing Home shortcut and protected save-error retry route remain connected.

## Package review and merge

Reviewed `C:\Users\shiny\Downloads\Heart_of_the_Rain_Daily_Gift_Design_R1.zip`, including its artwork, vector/browser sources, layout/motion contracts, calendar, localization, provenance, QA records and assets-only Unity package. ZIP CRC passes; all 103 supplied checksums and 52 Unity-package/patch file pairs agree. The supplied browser QA describes the author's preview, not native app verification. Its simulated 380 ms response and review selectors are not imported.

Eleven new images and their supplied GUIDs are imported under `App/DailyGiftDesign/Art`. Existing chrome, close button, primary button, check, coin and fonts are reused at their current paths/GUIDs; matching duplicate shared assets are not imported. The current Home background is retained. All existing metadata, original images, fonts, level data, schedule, settings and scenes are byte-unchanged from this turn's starting snapshot. Prior Account R6 work is preserved.

The renderer uses existing dynamic UGUI fonts, byte-identical to the supplied title/body TTFs, with native Cyrillic/Latin coverage. No TMP migration is needed for this component. Only the body viewport masks its children; the ornamental frame and close decoration are unmasked. Nine-slice multipliers follow the supplied contract. Bonus items use vertical icon/quantity pairs to retain space for localized copy. The supplemental wide Editor case uses the same clamped scroll layout; the shipping portrait-only policy is unchanged.

## Behavior and claim boundaries

The approved schedule remains 50 coins; Rocket; 75 coins; Bomb; 100 coins; Hammer; 150 coins + Orb. Availability, missed days, next-cycle rules, durable pending intent and inventory credit remain in the existing services. No reward/model/backend implementation is changed.

Confirmed success updates collected state and exposes Done, which returns to Home. Collection uses unscaled UI time: 650 ms chest keyframes, 600 ms reward pop, fourteen small glints with up to 75 ms stagger over 850 ms and a local 700 ms warm light mesh. Reduced motion shows the committed final state without transient effects. Dismissal cancels cosmetic coroutines/effects and advances a presentation generation; the HTTP transaction continues, and a late response cannot replay the collection effect in a reopened presentation. Opening uses the supplied 250 ms fade/slide/scale. Button feedback moves only child graphics, retaining touch bounds.

The default release authority remains unavailable. The portable backend is exercised only through an explicitly injected, isolated verification account; this integration does not configure production authentication, hosting or trusted time.

## Changed source

- `App/Profile/Runtime/DailyGiftPage.cs`: native renderer, fixed sections, backdrop, collection/open motion and dismissal generation; existing claim calls retained.
- `App/Profile/Runtime/DailyGiftLayout.cs`: delegates the live frame to the new layout; existing localized service/error copy and view model retained.
- `App/DailyGiftDesign/DailyGiftDesignAssets.cs`, `DailyGiftDesignLayout.cs`, `DailyGiftDesignText.cs`, `DailyGiftGlow.cs`: asset bindings, responsive layout, supplied five-language copy and bounded UI mesh.
- `Resources/HOTR_DailyGift/Design.asset`: explicit runtime asset references, with no scene/prefab replacement.
- `Verification/Editor/DailyGiftR1Review.cs`, two runners and the new collector: isolated native evidence. Existing backend UI assertions now expect Claim Gift/Done and the new artwork; the profile glyph test permits the intentional wrapping bonus caption.

## Verification

| Check | Result |
|---|---|
| Native design Play Mode | 2,966 checks; 30 locale/viewport cases; 45 captures; 13 inspected |
| Viewports | 393×852, 320×568, 430×932, 768×1024, supplemental 844×390, 320×480; five languages each |
| Actual isolated HTTP UI | 50 checks, including delay, 503, lost confirmation, close during request, durable retry, duplicate input and one server receipt |
| HTTP UI process restart | 9 checks; confirmed credit retained, repeat claim cannot credit again, compact scrolling |
| Native backend layout | 736 checks |
| Native profile transactions/glyphs | 13,571 checks; all cases pass |
| Connected Daily Gift/gameplay | 47 checks; isolated local authority/file profile |
| Existing general Editor checks | 533 passed, 0 failed |
| Portable backend service tests | 23 passed |

The design review also verifies the real seven-day grant sequence, both Day 7 items, next-day cycling, unavailable/failed claims, duplicate claim, Done, protected retry, glyphs/text bounds, fixed footer scrolling, reduced motion and collection dismissal/reopen. Native rendering exposed a missing CanvasRenderer on the light mesh; the required component is now explicit. An older single-line glyph assertion for the Russian bonus caption was corrected to allow the design's wrapping text. Failed exploratory artifacts are kept in the ignored verification cache, outside the passing gallery.

Evidence: [comparison gallery](../../Verification/Evidence/DailyGiftR1/Comparison.html), `Native_Review.json`, `Claims/*`, `Asset_Audit.json`, `Package_Review.json`, `Visual_Review.json`, `Source_SHA256.json` and `Verification_Summary.json`. Prior evidence is backed up/restored by the runners. Native screenshots are camera-rendered UGUI, not browser mocks or Android screenshots. Day/locale design states and network-state snapshots are explicitly labelled fixtures; HTTP fault/recovery reports use the real local service process.

Re-run from the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File Verification/Run-DailyGiftR1.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File Verification/Run-DailyGiftR1Claims.ps1
python3.15 Verification/Tools/collect_daily_gift_r1_results.py
```

The collector validates the frozen reviewed checkpoint; it does not run tests. Regenerating captures requires inspecting the fresh frames, updating `Visual_Review.json` and explicitly resealing with `--seal`. Do not relabel fresh random-account captures as the previously inspected hashes.

## Remaining scope

No Android APK is built/installed in this checkpoint. Last recorded deployment is checkpoint 54, with source through 53; Account R6 and this Daily Gift design await deployment. Device safe-area/notch input, physical-device rendering and effect performance remain open. The wide Editor fallback is supplementary, not a new supported landscape orientation. Production backend connection and native-language editorial approval remain separate gates.

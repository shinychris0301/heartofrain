# Gameplay loading R2 integration

23 October 2026. Current source checkpoint 63. The owner supplied `Heart_of_the_Rain_Gameplay_Loading_R1.zip`; its internal folder and handoff are revision R2. The owner explicitly selected the simpler R2 composition when asked about the conflict with the message's earlier bar/level-number description. Package instructions were reviewed as integration references, not authorization to overwrite the current project wholesale.

The screen now appears synchronously after an eligible Play request. It uses the supplied sapphire background, tiled raindrops, one static Rain Seeker/Rainbow Orb ability illustration and animated loading dots. There is no level number, fake percentage or progress bar. The app's initial Launch screen and first-time onboarding are unchanged.

## Launch and recovery behavior

`HomeLevelFlow` preloads the resource binding and builds the hidden overlay during Home setup. Accepted Play locks the session, hides pre-level, displays the opaque overlay and yields one frame before profile reservation or board construction, allowing the overlay to render before heavy work. Existing async texture preparation and batched warmup continue underneath it. Gameplay input stays blocked.

Handoff requires `InitializationComplete`, successful one-shot starting-power placement and no `StartingPowerError`, followed by the existing durable `CommitStart`. The overlay hides immediately at handoff: no minimum dwell, exit fade, simulated success timer or extra Start tap. This intentionally follows the owner's immediate-disappearance requirement rather than the package's optional 160 ms fade. Native observation saw at most one distinct rendered Unity frame between initialization readiness and coroutine handoff. This is scheduler observation, not an Android frame-time benchmark.

Starting-power creation remains held by the existing `startingCreationPending` / input gate until the board becomes visible. The loader does not wait for hidden creation playback. Existing inventory, life, seed, settlement, level masks and matching rules are preserved.

On initialization failure, partial gameplay is deactivated/destroyed and its reservation is cancelled before recovery controls become available. An uncertain cancellation is reconciled against the saved receipt; unresolved storage errors use the existing save-error modal above the overlay. Try again retains the level, selected boosters and chosen tip, creates a new attempt/operation token and reserves normally. Late callbacks from older operations and repeated Play input cannot complete, cancel or destroy the new operation. A failed reservation that never persisted also reaches recovery without requiring a nonexistent receipt to be cancelled. Back to level returns to the retained pre-level selection after cleanup. Loading itself cannot be cancelled; the existing 15-second initialization timeout is retained. Failures spend no life or starting booster.

## Presentation and assets

Only dots animate, using unscaled time and fixed positions. Reduced motion makes all dots opaque. The tip remains static throughout a load and retry; a new accepted launch avoids the preceding tip when both are eligible. Hints disabled produces the loading-only state. Current M46 matching rules enable both power kinds from the first board with no progression unlock table; eligibility therefore reflects that existing behavior. The view accepts explicit eligibility flags for a future authoritative unlock source, without introducing arbitrary unlock levels.

Safe-area geometry adapts the supplied portrait/tablet/landscape contract; the app's portrait-only device policy remains unchanged. Compact error layouts shrink/hide the diagram to prioritize two 48-unit recovery targets. Missing decorative art has an opaque sapphire/native-text fallback. Visible strings cover EN/ES/FR/DE/RU using the existing native UGUI Home font; no new TMP migration or Japanese support is introduced. Status/description hooks and localized control labels are exposed; no OS screen-reader provider is added.

All 14 supplied PNGs retain their bytes and loading-specific GUIDs. The Unitypackage's 28 asset/meta pairs match the UnityPatch. Existing font, gameplay textures/atlases, art, metadata, levels and ProjectSettings are unchanged. The package's older shared font/clarity guard/registry are not copied over the current versions. The current required clarity registry is merged from 34 to 48 entries, rather than importing optional older entries to reach the package's stated 57. Detailed artwork retains Box mipmaps and trilinear filtering; flat/sliced assets retain their separate filtering and native borders/PPU. Native import guard reports zero errors for all 48 entries.

## Changed files

Only three existing Unity inputs differ from the checkpoint-62/source-61 baseline:

- `App/PreLevel/Runtime/HomeLevelFlow.cs`: loading lifecycle and guarded recovery, preserving service-owned mutations.
- `App/PreLevel/Runtime/PreLevelLayout.cs`: removes the transient Starting label; Play/retry labels remain stable.
- `App/UIClarity/Editor/UIClarityRegistry.json`: adds the 14 loading assets.

New `App/GameplayLoadingDesign` contains the supplied Art/Data/Documentation/Localization plus `GameplayLoadingAssets`, `GameplayLoadingText` and `GameplayLoadingPage`. `Resources/HOTR_GameplayLoading/Design.asset` binds the sprites. New native review, runner scripts and collector own this checkpoint's evidence. `collect_results.py` selects the current collector. Full changed-existing-input hashes are in `Asset_Audit.json`.

## Verification

Pinned Unity 2022.3.62f3 native runs passed:

- Import/binding and current clarity guard: 14 new sprites; all 48 registered assets valid.
- Loading review: **8,076 checks, 150 locale/viewport/tip/state cases, 41 native UGUI captures**; 12 full images inspected.
- Five locales across 393x852, 320x568, 768x1024, 844x390 and 1179x2556 (3 physical pixels per reference unit); two tips plus loading-only, normal/error states. Native glyph rendering, viewport bounds, unchanged dot positions, source pixel budgets and recovery targets checked.
- Runtime checks: dots at timeScale zero, reduced motion, actual missing-art fallback, synchronous overlay before deferred work, duplicate Play, real invalid starting-power grant, cancelled reservation and untouched balances, retry token/tip/selection retention, stale failure/completion callbacks, starting creation held behind loading, one-time item debit and immediate handoff, duplicate completion, Back, zero lives and changed-stock rule rejection.
- Existing general checks: **534 passed, zero failed**.
- Existing connected Play smoke: **17 passed**, including natural input, pause/resume, loss acknowledgement, reshuffle loss, engine-fault and resolution-guard releases; no unexpected runtime errors.

Run `Verification/Run-GameplayLoadingR1.ps1`, `Verification/Run-GameplayLoadingR1Flow.ps1`, then `Verification/Tools/collect_gameplay_loading_r1_results.py`. Shared historical Native report/log files are preserved by the wrappers; this folder owns fresh copies. The legacy smoke's generated connected screenshots remain its normal shared outputs and are not loader visual evidence.

Gallery and reports: `Verification/Evidence/GameplayLoadingR1/Comparison.html`. These are native Editor renders and isolated connected actions, not device tests or browser mockups. No APK was rebuilt or installed for this request; main LDPlayer remains deployment 62. Fresh Android lifecycle/notch/touch, GPU/memory/load-performance and physical-device checks remain open, as does a full campaign rerun.

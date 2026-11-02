# Dense-burst effect batching and app defect review — checkpoint 60

23 October 2026. Unity 2022.3.62f3, LDPlayer 14. Evidence: `Verification/Evidence/EffectBatch` (`Native/Report.json` with six plates, `Android/<variant>/`, `Performance_Comparison.json`), `Verification/Evidence/Native` (`Native_Checks.json`, `Play_Smoke.json`), `Verification/Evidence/PowerWarmup/Native_Checks.json`, `Verification/Evidence/CrateBurst`.

Owner report: when many obstacles break at once, the destruction animation plays in slow motion — not a freeze (that first-hit hold was checkpoint 46). The same was to be checked for other obstacle families and plain tiles, followed by a comprehensive defect review with fixes.

## Mechanism

The slow motion is a frame-pacing effect, not an animation-timing bug. During gravity and power-fall steps `BoardPlayback.VisibleAdvance` caps the playback clock to at most 1/30 s per rendered frame while any piece is in flight, so a late frame cannot jump over a complete movement. Whenever a frame takes longer than 33 ms, the choreography therefore advances slower than wall time: at a 50 ms frame the whole burst — fragments, falls, accents — runs at two thirds speed. The rule itself is intended and unchanged; the defect is the frame time.

Checkpoint 46/47 device measurements already located the cost: at the 45-obstacle peak the C# sampling of a frame takes 2–3 ms, while Unity's per-renderer work for the ~800 `SpriteRenderer`s of a burst (transform, culling, sorting, batching) takes 10–13 ms (`otherRenderMs` p95 12.7 ms), and the emulator frame interval reaches 50 ms (p95). The cost scales with the number of effect sprites on screen, so every family and plain tile matches share it: a 45-stone or 45-sluice burst peaks at 782–786 draws, a plain double-Orb tile burst at 440 (`Native/Report.json`, `families`).

## Fix: effect mesh batcher

`M47/Runtime/EffectMeshBatcher.cs` (new). Each frame, every unmasked, non-glow effect draw (fragments, accents, tile breaks, power clips, star bursts) becomes one quad in a procedural mesh instead of one `SpriteRenderer`: one mesh per texture page and sorting order, in order of first appearance, uploaded with `Mesh.SetVertices/SetUVs/SetColors/SetTriangles` on `MarkDynamic` meshes with fixed bounds. The quad is built exactly as `SpriteRenderer` builds a runtime sprite's full-rect quad: texture rect corners relative to the pivot, divided by pixels per unit, rotated and scaled by the draw. Material, `_MainTex` (per-mesh property block), sorting order and vertex colour are the live ones; later meshes sit a hair nearer the orthographic camera so equal sorting orders still compose in order. Masked bodies, glowing bodies and HUD overlays keep their pooled `SpriteRenderer`s. A 45-crate peak now costs 16 meshes instead of 736 renderers; the level-42 double-Orb burst 25 meshes instead of 665.

`GameplayScreen.Render` routes draws accordingly, the batcher is created per level with the board's bounds and disposed on reload/destroy, and `ActiveSpriteCount`/`LastFrameCost` report `meshQuads`/`meshes`. Development builds keep a same-APK control: `VerificationUseSpriteRenderersForEffects` restores the old path for A/B runs.

### Pixel parity (native, `-Mode EffectBatchChecks`, status `PASS_NATIVE_EFFECT_BATCH`, 22 checks)

Four 900×1600 camera plates of the level-42 double-Orb peak (722 draws, 665 batched), same material, sprites and poses:

| Comparison | Pixels differing (of 1,440,000) | Max channel delta |
| --- | ---: | ---: |
| Exact-order meshes (verification mode, one mesh per run) vs SpriteRenderers depth-stepped into list order | 2 (0.0001 %) | 3 |
| Grouped meshes (live path) vs the list-order SpriteRenderer plate | 42,180 (2.93 %) | 252 |
| Grouped meshes vs SpriteRenderers left to Unity's own tie-break | 24,195 (1.68 %) | — |

The first row proves geometry, UVs and colour. The remaining differences are composition order among overlapping effects that share a sorting order (which fragment of the same crate draws on top): the `SpriteRenderer` path never defined that order (Unity's own tie-break differs from list order by a similar amount), the mesh path makes it deterministic by page. `Difference*.png` plates show the marks only where fragments overlap. The suite also checks every density family at 45 obstacles: quads equal batched draws, meshes ≤ 32, vertex count = 4 × quads.

### Device A/B (QA LDPlayer, same development APK)

One ARM64 IL2CPP development build (clean Gradle repackaging, 283,506,708 bytes, SHA-256 `50d36575fe59aa03…`) installed once on the QA instance (`emulator-5556`, data unchanged, no runtime errors); ten isolated density runs through `Tools/run_obstacle_density_device.py`: crate ×4 (both orders of the 1/8/16/32/45 fixtures, both paths), stone, sluice (`gate`) and plain-tile fixtures ×2 (one per path). `baseline` draws effects through SpriteRenderers (`VerificationUseSpriteRenderersForEffects`), `candidate` through the batcher; model turns and final boards hash identically across paths. Burst window = frames with at least half the turn's peak draw count; a long frame is above 41.7 ms (the point where the visible-advance cap slows playback is 33 ms).

| Fixture (peak draws) | Path | Burst frames | Long frames | Interval p50 / p95 / max (ms) | Peak meshes |
| --- | --- | ---: | ---: | --- | ---: |
| 45 crates (791) | baseline | 413 | 42 (10.2 %) | 16.7 / 50.0 / 133 | 0 |
| | candidate | 439 | 3 (0.7 %) | 16.8 / 33.6 / 50 | 17 |
| 16 crates (560) | baseline | 60 | 47 (78.3 %) | 50.0 / 83.3 / 117 | 0 |
| | candidate | 103 | 4 (3.9 %) | 16.8 / 33.6 / 50 | 17 |
| 45 stone (783) | baseline | 203 | 26 (12.8 %) | 16.7 / 50.0 / 83 | 0 |
| | candidate | 234 | 1 (0.4 %) | 16.6 / 33.2 / 50 | 17 |
| 8 stone (496) | baseline | 31 | 22 (71.0 %) | 50.0 / 66.6 / 83 | 0 |
| | candidate | 55 | 0 | 16.6 / 33.2 / 33 | 17 |
| 45 sluices (787) | baseline | 252 | 0 | 16.6 / 16.6 / 33 | 0 |
| | candidate | 257 | 0 | 16.7 / 16.7 / 33 | 17 |
| Plain tiles, double Orb (440) | baseline | 282 | 3 (1.1 %) | 16.7 / 33.3 / 67 | 0 |
| | candidate | 320 | 0 | 16.7 / 16.7 / 17 | 12 |

Over every measured turn (10 runs, 18,508 baseline frames and 19,381 candidate frames) the long frames fall from 490 to 65; within burst windows the candidate's interval p95 is at or below 33.6 ms for every family and count, where the baseline reaches 50–83 ms for crates and stone. Sluice bursts were already within budget on this emulator in both paths (one 200 ms scheduling outlier appears in the candidate's 32-sluice window: 4 long frames vs 2). The C# render section itself is not faster — mesh building replaces renderer updates (p95 12–17 ms at 45 obstacles either way); the gain is Unity's own per-renderer work outside it, which is what the interval measures. Full per-row metrics: `Performance_Comparison.json`.

The same APK is installed on the main instance (`emulator-5554`) with `install -r`: `Android/Main_Installation.json` records the saved profile unchanged by the install (lives 5, coins 1,300, level 1) and a clean launch (`Main_Home.png`, 0 runtime errors). QA is stopped afterwards, its prior state.

## Defects fixed in this checkpoint

From the 22 October analysis list and a second-pass review of the app layer:

| Id | Defect | Fix | Verified by |
| --- | --- | --- | --- |
| D6 | An exception thrown by a player command (swap, tap, tool) left a half-mutated board accepting input; no diagnosis, no settlement. | `GameplayScreen.Command/Fault`: every command runs through one guard; a throw is logged with the exception, `BoardModel.RecordFault` ends the board as `Engine fault` (first detail kept), and `HomeLevelFlow` treats it like the resolution guard — released without a life charge, starting items refunded, pre-level reopened, diagnostic logged with seed and turn. | `Checks` (model seam), `PlaySmoke` phases 11–12 (injected throw via `VerificationFaultOnNextInput`) |
| D9 | Per-gem scan of every power-plan tile each frame (and per track for merged chains). | `ReviewPlan.TileAt` cell index built once per tile array. | `Checks` replays, `CrateBurst`, `EffectBatchChecks` (same draws) |
| D12 | A tool that damaged moss did not break the regrowth quiet streak (tools skip `Regrow`). | `UseBooster` resets `QuietMoves` when `mossHit`. | `Checks`: "Moss honors interval…" (hammer on moss) |
| D14 | Exit confirmed while the attempt was already won left the settings controller in `leaving`, input blocked and music stopped for the rest of the win. | `GameplaySettingsController.CancelExit`, called from `HomeLevelFlow.ConfirmExit`'s won branch. | `PlaySmoke` (exit path unchanged), code path |
| D16 | `ProfileService.Lose` set `currentLevel` to the lost level, so losing a replayed earlier level moved Home's Play button back to it. | Loss no longer touches `currentLevel`. | `Checks`: "Reservation rules… loss keeps the current level" |
| D18 | `Reserve` threw one message for every rule, so a rule rejection (no lives, stock gone, level locked, attempt still open) was shown as "Could not save". | Distinct `InvalidOperationException` messages (`ProfileService.AttemptInProgress/NoLives/LevelLocked/BoosterUnavailable`, `IsReservationRule`); the flow shows them in the pre-level and keeps the save-failure path for everything else. | `Checks` (each rule's message), flow code path |
| D19 | Gameplay hints and command reasons were English-only. | `LocaleCatalog` entries (es/fr/de/ru) for the twelve hint, rejection and launch messages; the HUD and pre-level already translate through `GameLocale.T`. Non-English renderings await native review like the rest of the catalog. | `Checks` locale cases, catalog |
| R1 | Home was rebuilt every minute while a Rain Cup was active (badge text change → `ApplyState` → `Reflow`), losing a tap in progress and resetting scroll. | `HomePage.UpdateLabel` patches the `cup-status`/`drawer-cup-status` labels in place; `PlayerProfileHost` uses it and only falls back to `ApplyState` when no label exists. | `PlaySmoke` phase 0 (label patched, node count unchanged) |
| R3 | Sprite-cache eviction rebuilt and sorted the candidate list every frame at the cap. | Hysteresis: evict to 7/8 of `SpriteLimit`. | `WarmupChecks` cache cases |
| R5 | Chapter cinematic refit three labels, re-read a PlayerPref and did `GetComponent` ×12 every frame. | Labels refit on text/geometry change only, star images cached, mute read once. | Code path (cinematic plays at level 50) |
| R6 | Tutorial practice board used the allocating `Sample` copy and set a property block on every sprite every frame. | `SampleLive`; property block only while glowing. | `DailyGiftPlay`/first-start paths unchanged; code path |
| R10 | A debris profile without gravity kept its history entry forever. | Finite retention (`time + 4 s`). | Code path; all shipped profiles have gravity |
| R14 | An exception in First Start initialization froze the launch shield at 90 % for 30 s. | `FirstStartPage.Failed`; `LaunchPage` fails at once. | Code path |
| R15 | `HomePage.SetPresentation` threw when `Build` had bailed. | Guard. | Code path |
| R16 | Settings button read the profile file without a guard. | `ToolStockSnapshot`/`StartingStockSnapshot` fall back to in-memory stock. | Code path |
| R18 | Idle Home wrote canvas-renderer colours and tab transforms every frame. | Write on change only. | Code path |
| R20 | Batcher geometry cache kept evicted sprites. | Bounded (cleared above 4,096 entries). | `EffectBatchChecks` |

Not changed, recorded for the backlog (second-pass review): D10 (Atlas's 800 permutation passes and the reshuffle's 100 attempts can hitch on large boards; a constructive fallback is a mechanic decision), effect sampling cost per history entry (R2; ≤ 0.2 ms at the measured peaks), `LabelFit` linear passes (R4), booster choreography lookups (R7), string-keyed clip lookups (R8), reward-reveal tint after back-to-back claims (R11), leaderboard search on focus loss (R12, demo data), preview-state fallback when the save fails to load (R13, needs an owner decision on the shipped scene flag), ProfilePage per-frame stats key (R17), Rain Cup name ellipsis on surrogate pairs (R19, file owned by the concurrent design workstream), backend request disposal on teardown (R21), M68 celebration mesh rebuilt per frame (R22), legacy `LevelCompleteModal` allocations (R23, not in the live flow), practice board stuck status after a throw in `Prepare` (R24).

## Verification

| Suite | Result |
| --- | --- |
| `-Mode Checks` | `PASS_NATIVE_EDITOR_CHECKS`, 534 checks (533 before), 0 failures; new: tool damage resets the moss quiet streak, engine-fault seam, reservation rule reasons, loss keeps the current level |
| `-Mode PlaySmoke` | `PASS_NATIVE_PLAY_SMOKE`, 17 checks; new: Home badge patched in place, injected engine fault released without charge |
| `-Mode EffectBatchChecks` | `PASS_NATIVE_EFFECT_BATCH`, 22 checks (table above) |
| `-Mode WarmupChecks` | `PASS_NATIVE_PRESENTATION_WARMUP`, 4,582 checks (render check counts batched quads against sampled draws) |
| `-Mode ProfileChecks`, `ProfileEventChecks` | pass (runner-validated fresh reports) |
| `Run-CrateBurst.ps1` | `PASS_NATIVE_CRATE_BURST`, 3,720 checks, pose signatures identical before/after |
| Android | development build 0 errors; `PASS_CLEAN_GRADLE_APK_PACKAGING`; ten QA runs `PASS_OBSTACLE_DENSITY_PLAYBACK`; `PASS_EFFECT_BATCH_ANDROID_CONTROLS`; main `PASS_INSTALLED_DATA_PRESERVED_LAUNCHED` |

Source checks and Editor plates are not device evidence; the device section carries the frame-pacing result. Emulator intervals include host scheduling and are not physical-device certification (ENG-06 stays open). The full Android regression suite (`run_emulator_regression.py`, checkpoint 54) was not rerun in this checkpoint.

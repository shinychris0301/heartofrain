# Obstacle-density performance review — checkpoint 45

22 October 2026. Unity 2022.3.62f3. [Evidence gallery](../../Verification/Evidence/ObstacleDensity/Comparison.html).

Crate-count-dependent CPU work is reduced while full fragments, poses, destruction timing and refill behavior are retained. The final development APK is rebuilt and replacement-installed on main LDPlayer with preference/campaign hashes unchanged. QA data is preserved and its previous stopped state is restored.

## Cause and changes

Checkpoint 44 removed native sprite/renderer creation during bursts. Remaining work still grew with the body/damage count and visible fragment field:

- `M46/Runtime/BoardPresentation.cs`: build one latest-eligible-damage lookup per sample, replacing each body's full damage scan: O(D + P), previously O(P × D). Reserve 128 entries before input for the authored maximum of 121 cells. Stable counting sort handles at least 32 draws spanning at most 256 order values; other cases keep the original comparator. Reserve scratch storage with existing preparation. Cache crate profile angles/trigonometry and share raw exponentials only for equal zero launch delays. Preserve original float evaluation order, gravity expression, fragments, age, poses and order.
- `M48/Runtime/AdvancedObstaclePresentationPure.cs`: use the same cached damage lookup for advanced obstacle bodies.
- `M47/Runtime/GameplayScreen.cs`: cache Transform and input angle; avoid repeated native quaternion conversions for unchanged angles and ordinary non-glow texture reads. Preserve glow transitions and combine local position/rotation setters when both change. Reset cached state on reload.

[Exact runtime diff](../../Verification/Evidence/ObstacleDensity/Runtime_Changes.patch). These are the only three changed existing production inputs relative to checkpoint 44. Original art, metadata/GUIDs, masks, model rules, power creation, inventory, rewards, attempt settlement and services are unchanged.

## Fixed-origin Android controls

40 timed turns on QA LDPlayer, all using the same final APK: two repetitions of 1/8/16/32/45 one-layer crates per process; process order control / optimized / optimized / control. The second pair reverses density order. Each process first runs one untimed 45-crate prime.

The fixture clones authored level-26 geometry without writing that asset. Deterministic spread crate subsets/colors, fixed seed, Double Orb swap cells (4,5)/(5,5), recorded effect origin (5,5), and a constant 1,182-slot renderer/draw reserve control the workload. Controls retain checkpoint-44 preparation and restore prior damage/debris/sort/texture/rotation work. Transform object caching is shared between paths. These opt-in development fixtures have no attempt/inventory/progression callbacks.

Primary measurements use the same gameplay clock window at every count: `powerFall` age 2.3–2.8 seconds, chosen from exploratory traces before the final device run. Whole-turn and substantial-debris windows, medians/p95/maxima, command/preparation times and raw frames remain in the report. No screenshot/video/report serialization occurs during timed playback. Shared per-frame measurement objects add instrumentation cost; zero renderer/crate-sprite creation is not a claim of zero managed allocation.

| Crates | Peak render p95: control / optimized | Peak frame interval p95: control / optimized | Whole-turn intervals >41.7 ms: control / optimized |
|---:|---:|---:|---:|
| 1 | 7.72 / 7.56 ms | 49.74 / 33.36 ms | 9 / 3 |
| 8 | 10.03 / 8.46 ms | 49.74 / 48.79 ms | 9 / 6 |
| 16 | 11.89 / 11.35 ms | 49.74 / 48.79 ms | 13 / 7 |
| 32 | 15.28 / 15.49 ms | 33.37 / 50.04 ms | 7 / 9 |
| 45 | 17.38 / 14.81 ms | 49.74 / 50.04 ms | 11 / 11 |


[Full metrics/window definitions](../../Verification/Evidence/ObstacleDensity/Performance_Comparison.json). All final runs, including outliers, are retained. Other host/emulator activity was not held constant; main was found closed after controls. ABBA order does not eliminate this confound, so these timings are observations rather than a controlled device certification. A larger effect still renders more sprites; these elapsed CPU/interval measurements include emulator scheduling and are not GPU measurements or a sustained 60 fps certification.

All 40 turns clear the configured count, retain within-density turn signatures, match the expected final board, create zero renderers/crate sprites, and keep the 1,182-slot pool. Preferences/campaign hashes match before/after every process; detected fatal/runtime exceptions: zero. Raw reports and installation identities are in `Android/baseline_1`, `candidate_1`, `candidate_2`, `baseline_2` beneath this checkpoint's evidence folder.

Earlier variable-origin exploration was rejected as a cross-density control. A subsequent fixed-origin pass exposed repeated quaternion work and led to the final renderer change. Both exploratory datasets are archived locally outside final controls; neither supplies numbers for this table.

## Native verification

Five density cases preserve exact turn, final snapshot and complete sampled draw JSON signatures. The native peak-sampling microbenchmark at 45 crates is 0.3788 → 0.1596 ms. This excludes live renderer/GPU/Android cost; raw small-case timing noise is retained.

- 402,398 regression checks: 2,860 damage queries (including ties/backward time/nonfinite ages), 32 stable-sort boundaries, damage dictionary no-resize checks and 15 exact authored replays on levels 12/23/26/42/49 using Double Orb, Orb/Rocket and Rocket chains.
- 10 real native playback turns: expected clears, unchanged pool, zero renderer/crate-sprite creations.
- One fixed native camera peak: zero changed RGBA pixels between calculation/binding paths. The 720×1280 plate excludes the HUD and has a small board due to the Editor viewport; this verifies binding parity, not phone layout.
- 4,051 preparation/lifecycle/cache checks and 530 general Editor/model checks. All six native stages exit zero, without timeout.

An early algebraic gravity rewrite produced tiny float drift and was discarded. Final original arithmetic and all sampled poses match exactly. Fresh lifecycle results are copied into this checkpoint; historical PowerWarmup evidence is restored afterward.

Verification additions: density fixture/probe, three Editor density verifiers, `Run-ObstacleDensity.ps1`, Android runner and collector. `collect_results.py` dispatches to this installed checkpoint. New Unity metadata is retained; original metadata hashes match.

## Build, visual review and installation

All 4,656 frozen source/configuration/tool hashes match. ARM64 IL2CPP development build: zero errors, two existing warnings. Clean Gradle packaging preserves 1,020 nonsignature entry CRC/size pairs and the signer. APK CRC/signature, 4 KiB ZIP alignment and static 16 KiB ELF load-segment checks pass. PlayerSettings are restored byte for byte; the SDK repository timeout override is process-local, with no engine/SDK/configuration upgrade.

APK: `Unity/Builds/Verification/HeartOfTheRain_Development.apk`, **260,521,584 bytes**. SHA256: `4ad9b6f504d41ed34902212fe41a261166cb410f6121516bfdd850b5c3bfde33`. Both installed identities match. Internal development signing is not store release signing.

Separate compressed QA playback is excluded from timings. Inspected original-size frames show full wood breakup, overlapping refill and the refilled board; the native pair and direct main Home screenshot are reviewed separately. [Frame hashes/captions](../../Verification/Evidence/ObstacleDensity/Visual_Review.json). Main installation validates the current profile envelope and rejects an active attempt before stopping the app. No uninstall, data clear or gameplay taps are used. Saved preferences/campaign files retain their hashes and main is left on Home. QA is stopped after capture with saved data preserved. [Main installation](../../Verification/Evidence/ObstacleDensity/Android/Main_Installation.json).

Remaining limits: cold first-command latency, GPU/physical-device budgets, release memory/compression and whole-campaign performance are not certified by these warm controlled bursts. Existing production service/demo limitations remain unchanged.

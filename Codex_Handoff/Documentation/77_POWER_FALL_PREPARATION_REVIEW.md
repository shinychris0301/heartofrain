# Power-up falling preparation and sampling

25 October 2026. **PASS_TARGETED_POWER_FALL77_WITH_REMAINING_PERFORMANCE_GATES.** Baseline: verified checkpoint 76. Unity remains 2022.3.62f3. Frozen inputs: 5,125 files, source manifest SHA-256 `f16edd1b7872160e75a6c6da8b31a00f387cfb79d5eb3bb3e9a988a635c3fd2c`. Four existing C# inputs change and five C# files plus metadata are added. Existing artwork, metadata/GUIDs, masks, model/transaction code, packages and project settings are unchanged. The main LDPlayer installation is preserved.

## Concrete preparation gap

Checkpoint 76's detailed sparse-stone row `stone_1_0_current76` retained 68.1597 ms Render at frame 1247, followed by a 149.973129 ms frame interval. Native replay now reproduces the original first-use counts and identifies `p/28/27` (Double Orb wave) and `p/21/44` (Orb stars) at frame 1247; frame 1248 creates `p/28/29` and `p/21/45`. These are effect frames, so preparing power-body Idle/Create clips alone would miss this case.

The existing prefetcher prepared textures. Level preparation created common fragments and obstacle sprites, and mesh preparation could inspect only sprites already cached. Later power-effect sprites and their quad geometry therefore remained on the demand path during falling. This is a demonstrated preparation gap, not proof that two sprite creations exclusively caused the historical stall: several measured stages rose together, earlier timing left work outside its brackets, and checkpoint 76 had only a row-wide GC counter.

## Runtime changes

`M46AtlasBank.cs` adds a resident-only, serial power-frame preparation worker. It visits complete manifests belonging to already-required, already-loaded power atlas paths. It loads no additional texture, adds no permanent pin and raises neither cache cap. Overlapping requests coalesce into one worker; the first advance yields before native sprite/geometry work. Each batch stops after a soft 1 ms threshold or 16 frame visits, checked after an operation. Actual batch cost remains measured; one native operation can exceed the threshold. Eviction, unavailable geometry capacity and short lead times retain the existing demand fallback.

New `GameplayPowerFramePreparation.cs` continues the established texture prefetch into sprite/geometry preparation. `GameplayScreen.cs` starts this background work at the existing queue-prefetch point and clears its owner on reload. Swaps, model readiness, clocks and effect durations do not wait for this worker. Development pending state includes the preceding texture request interval, avoiding a false-ready observation before the sprite worker starts. `EffectMeshBatcher.PrepareSprite` respects the existing 2,048-entry preparation bound and never changes drawing, sorting or effect counts.

`BoardPresentation.cs` skips falling-position calculations whose results were immediately overwritten by the established routed-position calculation. The actual route, movement, stretch, spawn hiding and landing logic remain intact. Non-crate debris caches immutable profile sine/cosine values and shares the identical exponential result among zero-delay pieces. Nonzero launch delays retain distinct ages. A separate development control restores checkpoint 76's sampler calculations without changing the older density or transform controls.

Development instrumentation records disjoint outer Render stages and frame-local supported GC counters. Legacy sample/per-draw costs remain nested and must not be added again to the outer total. The opt-in probe uses a preallocated value buffer, records preparation outside Update/Render separately, and retains command-tail frames. Frame intervals can contain work from the preceding command, preparation, engine or scheduler; a post-command Render timestamp alone does not isolate the interval's cause.

Verification-only additions are `Verification/PowerFall76Control.cs`, `Verification/PowerFall77Probe.cs`, `Verification/Editor/PowerFallSamplingVerification.cs` and `Verification/Editor/PowerFallPreparationVerification.cs`, with new metadata. The comparison control bodies are compiled from the sealed checkpoint-76 source; release builds exclude these development/Editor controls.

## Verification scopes

The new sampling suite passes 217,280 native checks: exact archived-76 control bodies, 98,433 profile-family samples, representative cabinet states, 18 actual turns, synthetic launch-delay boundaries, cold fallback and four signature negative controls. It compares 2,739,238 draws, with warmed alternating timing rows retaining slower pairs. Native Editor CPU spans are separate from Android performance.

The new preparation suite passes 795 native checks. All 228 original falling frames retain exact sampled poses/sprite rectangles and uploaded mesh state, while 149 cold sprite creations become zero demand creations and zero demand geometry misses after preparation. That worker visits 748 manifest frames, creates 396 native sprites and uses 47 recorded batches. Overlap, first-yield, conflicting-owner, actual sprite/texture eviction and pending-disposal controls pass. These iterators are advanced manually with frame-end interleaving in the native Editor; this is not Play Mode coroutine scheduling or device frame pacing.

The preparation test also preserves an observed Editor/Android raw-turn hash difference. Exact native before/after turn hashes agree, the Android final snapshot matches, and five model/planner/fixture source files match archived 76 byte-for-byte. The differing serialized raw hashes are not labelled byte parity or assigned a proven serialization/math cause. Device raw outcomes must be checked against the Android baseline separately.

Instrumentation validation passes 19 native arithmetic/counter checks, including 17 deliberately invalid records. These validate measurement contracts, not gameplay performance.

The first compile rejected the new helper's invalid 33-character GUID; its corrected new GUID is valid and unique, and all existing metadata is preserved. That failed run is retained under `Attempts/FirstCompileFailure`. The initial preparation test incorrectly required Editor and Android serialized raw-turn hashes to match; its failed report is retained under `Attempts/FirstPreparationBaselineFailure`, and the corrected same-domain assertion keeps the differing hashes visible.

All 29 pinned-native suites pass 929,596 checks against the same frozen inputs. Required mesh, pixel, family and lifecycle coverage is preserved. The old suites have three fewer dynamic assertions because two preparation iterators yielded once less and accelerated playback sampled one fewer frame; fixed coverage is unchanged. Both development and non-development Android builds pass with zero errors. Clean packaging preserves the signer and all 1,088 non-signature entries; ZIP CRC/alignment and native-library checks pass. The development APK is `d4bb4e66e454db223871c91d66de4ee8e87fec05268aa9a27a3cf86da7930072` (302,321,954 bytes).

## Android power-fall controls

The final APK is installed and remotely hash-verified on QA LDPlayer (`emulator-5556`), with ordinary saves/preferences unchanged. The initial ADB preflight failed before reading the profile or installing; subsequent read-only readiness queries succeeded, with no reset, data clear or main-instance action.

The same-APK probe passes 16 natural AB/BA turns on fresh banks (4,164 retained frames) and four warmed, fixed-pose fixtures with 16 alternating pairs / 32 actual Update/Render calls. Android raw turn and final hashes match the sealed Android-76 baseline. Natural turns vary preparation only; fixed-pose pairs vary sampler calculations only. They are distinct experiments.

In the 2.44-2.62 second power-fall window, all eight prepared runs (57 samples) have zero demand sprite creations and zero geometry misses; skipped controls (59 samples) total 102 of each. Across 1,590 observed falling frames after the worker has performed work and completed, both demand counts are also zero. This closes the demonstrated requested-frame preparation gap within these fixtures, not every possible first-use or cache-pressure case.

Whole-render timing remains mixed. Fixed-pose medians, retaining every pair, are:

| Fixture | Archived-76 sampling (ms) | Current-77 sampling (ms) |
| --- | ---: | ---: |
| One crate | 7.116 | 6.918 |
| 45 crates | 11.378 | 11.597 |
| One stone | 6.067 | 6.280 |
| 45 stones | 11.598 | 12.754 |

These measure whole Render with only sampler calculations switched; they do not establish a universal Android speedup. Prepared natural frames whose Render starts after the command ends reach 42.319 ms Render and 83.278 ms reported interval; separate skipped-control maxima are 27.419/116.589 ms. Intervals can contain preceding work, so the analyzer preserves Update-start brackets, command/worker overlap tags and both worst-Render and worst-interval neighborhoods. The worst prepared Render has 35.570 ms in the disjoint drawing stage, no demand sprite/geometry creation, no pending worker and no completed GC within Update. A separate dense-crate outlier spends 26.052 ms sampling. This is remaining cost, not evidence that the historical stall was solely resource creation or that host scheduling is the exclusive cause.

The maximum observed preparation batch is 1.8984 ms; the 1 ms threshold is cooperative and checked after an operation. All slower rows, frame-local supported collection counters and original timestamps remain in `Performance_Analysis.json`.

All nine ordinary final-APK QA stages also pass, including 40 density turns, eight actual-input cases and the full campaign regression: 1,716 checks, 14,105 labels, 408 actions, 354 clips and 50 boards, with failures empty. Real saves/preferences match before/after every stage. Extra current L14/L31/L33 recordings pass their provenance and data checks. Ordinary detailed-density post-command Render reaches 25.087 ms (stone), separate from the coarse power-fall controls above. Ordinary six-case command spans still reach 77.888 ms, with an 83.340 ms interval in the 60 fps case. The eight-phase Fluidity run retains a 100.659 ms Golden/Bomb command and 100.019 ms maximum intervals. These separate probes retain observer overhead and do not establish sustained frame rate, input-to-display latency or universal improvement.

## Actual visual review

Parent inspection covers three full native plates; four current timing sheets and three full timing originals; two full MixedChain before/after stills; six regression sheets containing 68 thumbnails and five full regression originals. Independent reviewers inspect eight other regression sheets containing 88 thumbnails plus two full originals, and four fresh timing movies through indexed original-PTS frames/sheets plus a sampled MixedChain sequence. Scopes overlap: no reviewer is represented as personally viewing all images, and sheet thumbnails do not mean every constituent was viewed full-size.

No new sampled rendering discrepancy is identified. Carry and landing remain progressive, source Rocket effects execute, and the protected created Rocket survives/refills in the reviewed sequence. The native functional cases independently verify actions/protection. Existing sealed-Moss pockets remain qualified, not universally gap-free; independent decorative debris can remain after body settlement. A finale crossfade still is a transition, not a stable ghosting verdict. Variable optional tool captures are bounded accelerated samples, not missing functional tests.

Fresh contact-to-first-fragment bounds are L4 67.867-133.589 ms, L14 66.288-132.789 ms, L31 66.845-133.078 ms and L33 32.466-98.956 ms. Visible accepted-swap bounds are 67.055-133.233 ms and include the native 120 ms schedule. All overlap checkpoint 76. This work closes a demonstrated first-use preparation gap while preserving poses and schedules; it does not claim a newly shortened ideal fall or reaction schedule.

## Remaining limits

The worker prepares requested resident manifests, not the entire power library. Full-manifest visits and cooperative yielding can leave early frames on the demand path; later cache pressure can evict prepared entries. The preparation geometry cap, 4,096-entry demand-cache flush, first-use costs and long-session churn remain relevant. Fixed-pose sampling controls and separately played preparation controls answer different questions; neither supplies physical-device or sustained-frame-rate certification.

Original 120 ms accepted swaps, power birth protection, existing chains, conservative continuation eligibility, obstacle semantics, rewards, attempt settlement and the 900-coin full-life refill remain unchanged. Reference evidence remains archived Match Villains footage. Physical devices, rapid next-input transitions and wider whole-game smoothness remain open.

Evidence: [comparison](../../Verification/Evidence/Gameplay77/Comparison.html), [strict summary](../../Verification/Evidence/Gameplay77/Summary.json), [performance analysis](../../Verification/Evidence/Gameplay77/Performance_Analysis.json), [visual review](../../Verification/Evidence/Gameplay77/Visual_Review.json), [original-PTS notes](../../Verification/Evidence/Gameplay77/Timing_Visual_Notes.json). The strict collector rechecks source/build/APK identity, unchanged saves, matched measurements and actual inspection bindings. Android and native hashes compare within their respective sealed platform baselines. No whole-game smoothness approval is inferred from the targeted pass.

# Checkpoint 78 — command work and effect submission

25 October 2026. Verified targeted source checkpoint 78. Command/resource/submission improvements pass the current source, build, native, QA and sampled visual gates below. Material performance gates remain open; this is not whole-game smoothness approval.

The owner approved the next smoothness priorities after checkpoint 77: reduce synchronous command work and dense drawing costs. This change preserves the animation schedules, artwork, level masks, gameplay rules and conservative continuation eligibility. It does not broaden local cascade overlap or shorten the accepted 120 ms swap.

## Changes

`M46/Runtime/BoardModel.cs` reuses validated snapshot ID ranks after rescanning live IDs, plus validation scratch storage. Returned pieces/goals remain independent copies. Membership changes, replacements, mutable IDs, duplicate IDs and failure recovery have explicit controls. `M48/Runtime/AdvancedObstacleRulesPure.cs` builds reusable first-owner/member-count indexes for footprint validation instead of repeated searches and temporary arrays. References in scratch storage are cleared. `M46/Runtime/LivePowerPlan.cs` selects the same best target/color in one pass, preserving the priority, distance and coordinate tie order.

`M47/Runtime/GameplayCommandPreparation.cs` resolves ordered per-phase and whole-queue resource dependencies once per compiled command. `GameplayScreen.cs` uses the plan while the queue and asset bank still match. Queue changes, reloads and completion invalidate it. This relies on the existing immutable queued contents and asset bindings. Live bank readiness and the existing prefetch point remain authoritative; a cached dependency list never claims that a texture is resident.

`M47/Runtime/EffectMeshBatcher.cs` writes quads into retained arrays and uploads only the active prefix, retaining the exact vertex, UV, color, index and layer order. Growth, shrinking, empty frames, regrowth, slot overflow, public ownership reset on disposal and branch switching are covered. Arrays retain high-water capacity; a larger first burst still resizes and copies. Development builds retain the old List buffers for same-APK controls; release excludes those controls. Development memory is therefore not an allocation-saving or whole-old-APK comparison.

New verification files provide exact archived-77 helper controls and an opt-in, isolated Android probe. Model timing excludes construction, serialization, hashing and fixture setup. Resource comparisons include the eager construction and queue-identity guards in the full cost. Frozen render pairs change only effect submission. Natural command pairs change all three components together and do not assign exclusive causation to one component.

The added verification sources are `CommandPreparation77Control.cs`, `Editor/CommandPreparation78Verification.cs`, `Editor/DenseSubmissionVerification.cs`, `Editor/ModelWork78Verification.cs`, `Execution78Probe.cs`, `Model77Control78.cs` and `ModelWork78Proof.cs`, each with its own new metadata. The existing `Editor/PowerFallPreparationVerification.cs` now permits the two deliberately changed model files only after checking the fresh source-bound 350-case equivalence proof and a direct archived-77 comparison of its own fixture. It still requires the unchanged bindings for its other production files and all 228 replayed frames; the older test is not disabled or accepted solely because another suite reports success. The exact input inventory is [Source_Delta.json](../../Verification/Evidence/Gameplay78/Source_Delta.json).

## Native and build verification

The source snapshot contains 5,141 Unity inputs, SHA-256 `bb4957a736bd76bee426cbf2cc7ab1a6da3080e3c86d8ac07a89f45da51747c7`. The Unity source scope is six changed C# files and eight new C#/.meta pairs; existing artwork, metadata, packages and project settings are unchanged from the sealed checkpoint-77 baseline.

All 32 pinned-Unity suites pass 947,974 checks. The three new suites contribute: ModelWork78 2,855 checks; DenseSubmission 481; CommandPreparation78 15,000. Model proof includes 350 archived raw/final/RNG/dictionary-order cases, 70 actual power pairs, 110 direct planner cases, independent snapshots and invalid-state recovery. Resource proof covers 714 queues and 3,317 phase comparisons, including ordered path parity, real eviction/readiness and helper ownership. Mesh proof covers 135 uploaded states and strict zero-difference pixels against independently compiled archived code and the same-APK old branch. Existing command construction, resource scan, continuation, mixed-swap protection, route/creation/timing, profile transactions, connected smoke and Home lives suites pass again against the same frozen inputs.

Parent and independent inspection of all six fresh native plates found no new discrepancy between either three-way set. The deliberately transformed fixture has cyan tint/alpha/flip/scale changes in all controls. Broad-wave clipping at the camera sides and enlarged soft glow edges are shared fixture/art limits. These plates verify sampled rendering, not gameplay pacing.

Warmed Editor timing retains all slower pairs. Model medians improve in the eight sampled cases; several individual current calls remain slower. Initial resource preparation is mixed (for example, L14 is slower initially), while complete queue traversal is lower in the sampled native case. These dependency/model-only measurements are separate from Android input latency and natural frame pacing.

The first verification attempt stopped at compile with CS0819 in a new test's local declaration. That declaration was corrected; its old source, process and logs are preserved under `Verification/Evidence/Gameplay78/Attempts/FirstCompileFailure`. It is historical failure evidence, not a passing run. All final checks restart against the corrected snapshot.

Both non-development and development Android builds pass with zero errors. Import audits and the final frozen-source check pass. Clean packaging preserves all non-signature entries and the signer; CRC, ZIP alignment, development signature and static ELF checks pass. The final development APK is 302,532,059 bytes, SHA-256 `acecd407fac7de7e5fa8a6065189be2f4f0aa6ddf4c10d6fac668427e1567cc1`. The non-development build is an internal compile/build check, not a store release or a device-certified release build.

## Android execution measurements

The installed QA APK passes both isolated control experiments with unchanged real saves/preferences and no reported runtime errors. The repeated power-fall audit contains 16 natural turns, 4,643 frames and 16 frozen sampler pairs. The new execution audit contains eight natural turns, 3,226 frames, 64 pure model pairs, 64 resource pairs and 32 frozen actual Render pairs. All raw/final outcomes, model checkpoints, dictionary/path order and frozen draw/upload bindings match their same-platform controls. Native Editor and Android serialized raw hashes remain separate domains.

The Android pure model and full dependency-work medians are below. Each row retains eight alternating pairs, including every slower call. Model construction, fixture injection, serialization and hashing are outside Solve timing. Full resource work includes initial plan construction plus guarded traversal of every remaining phase; it excludes residency checks, loading and callbacks. The near-zero remaining-phase lookup cost alone is not the total plan cost.

| Fixture | Model control 77 (ms) | Model current 78 (ms) | Full resources control (ms) | Full resources current (ms) |
| --- | ---: | ---: | ---: | ---: |
| L4 match | 12.839 | 13.620 | 10.216 | 4.459 |
| L14 match | 5.701 | 4.930 | 5.317 | 2.451 |
| L31 match | 7.501 | 6.534 | 6.607 | 3.250 |
| L33 match | 5.187 | 4.912 | 5.060 | 2.606 |
| Three Rockets | 10.934 | 9.113 | 6.835 | 3.579 |
| Orb/Rocket | 15.748 | 13.923 | 10.724 | 5.085 |
| Golden/Bomb | 17.742 | 17.115 | 12.923 | 5.667 |
| L26 Orb | 14.647 | 14.380 | 12.745 | 5.764 |

All 64 complete resource-work pairs are lower, but initial work alone has 15 slower current pairs. Orb/Rocket's initial median is 5.003 to 5.079 ms. Seven model medians improve; L4 is 6.1% slower, with five of eight slower calls. Across all fixtures 24 of 64 current model calls are slower. L4's separate inclusive snapshot diagnostic is 2.603 to 4.301 ms for the same 36 snapshots/2,558 copied pieces. Six other snapshot diagnostics are lower. Membership churn and rank rebuilding are a plausible investigation target, not a proven cause. Removing the one L4 pair with a completed collection still leaves the descriptive median difference positive; GC does not explain the result away.

Frozen whole-Render medians, with only the submission implementation switched, are:

| Same-pose fixture | List control 77 (ms) | Arrays current 78 (ms) |
| --- | ---: | ---: |
| One crate | 4.188 | 3.993 |
| 45 crates | 8.853 | 8.492 |
| One stone | 3.818 | 3.587 |
| 45 stones | 9.292 | 8.979 |

These are modest sampled improvements; 12 of 32 individual current pairs are slower. Current frozen Render still reaches 11.421 ms. The other power-fall experiment switches the older sampler, not these buffers: three of its four medians are lower while dense stone is slower (9.110 to 9.319 ms). Those experiments are not combined into one claimed effect.

All four natural combined-control command pairs are lower: Golden/Bomb 56.861 to 49.830 ms and 49.525 to 36.384 ms; Orb/Rocket 43.294 to 37.741 ms and 37.007 to 36.656 ms. They restore only the targeted archived helpers inside the current APK; they do not restore the entire old application, heap, driver or startup state. First post-command idle rendering is slower in all four current branches. Both branches create two body sprites/load two textures there after fixture powers were injected following level loading. This establishes a synthetic first-use concern, not a proven ordinary-gameplay regression or exclusive texture-loading cause. Frame pacing remains mixed.

The current prepared power-fall rerun retains 77 late-window samples with zero demand sprite creations/geometry misses versus 121 of each in 80 skipped-control samples. All 1,830 falling frames after observed preparation completion also have zero demand. Prepared Render/interval maxima are 22.193/50.010 ms; the maximum preparation batch is 1.526 ms. The preparation threshold remains cooperative.

Separate ordinary probes reach 58.390 ms command spans and 43.694 ms detailed dense-gate Render. That gate frame has zero sprite/geometry/mesh-slot creation and zero completed GC within Update; disjoint sampling and drawing are 21.097 and 21.167 ms. A separate 100.071 ms interval follows a bracket overlapping its command while its own Render is only 2.468 ms. Per-draw observer modes and requested cadences differ from the coarse paired controls.

Fresh recorded first-input cases are a further explicit gate. L14 records 93.657 ms commands/116.366 ms intervals, L31 103.401/116.735 ms and L33 159.382/183.079 ms. L33 Accept is 118.012 ms, including a recorded 89.459 ms playback Build span. Its 183.079 ms interval follows an Update-start bracket overlapping command work; the frame's own swap Render is 3.411 ms. These measurements do not establish that recording, scheduling, GC or any one method exclusively caused the stall. The captured-mode costs are retained separately from unrecorded timing, not discarded as observer noise.

The raw analyzer preserves all pairs, command/pre-command/post-command Render partitions, worker/GC context and both worst-Render and worst-interval neighborhoods. The strict validator also rejects 55 deliberately damaged copies of the actual Android report while leaving the original bytes unchanged. Those are Python contract checks, not extra Unity/device tests.

## Android regression and actual visual review

All nine ordinary QA stages pass, including 40 density turns, eight actual-input cases, six unrecorded cadence cases and the full campaign regression: 1,716 checks, 14,105 labels, 408 actions, 354 clips and all 50 boards, with no failures. Real saves/preferences match before and after every stage. Three extra current cascade recordings also pass their provenance/data checks. Normal app relaunch after transient fixtures succeeds. Main LDPlayer deployment 64 is preserved; QA has the current APK.

Parent inspection covers all six full native plates; six current timing sheets and five full timing originals; two full MixedChain before/after images; and six regression sheets containing 68 thumbnails plus five full originals. Independent timing review covers 15 current sheets, 11 full timing originals and the same two MixedChain images. Inspection scopes overlap; a sheet thumbnail is not a claim that every constituent was viewed full-size.

The sampled motion retains progressive refill/carry and landing. The source Rocket executes horizontally and the earned Rocket survives into the refilled board; existing native functional tests independently verify source action and birth protection. The full stacked-stone settled image has a tile below the two surviving stones. Decorative debris can continue after body settlement. The sampled 900-coin refill produces five lives and a zero coin balance exactly once. The finale crossfade in a transition still is qualified separately from its stable city-hook image.

Fresh original-PTS contact-to-first-fragment bounds are L4 99.889–166.567 ms, L14 36.700–100.089 ms, L31 69.511–136.255 ms and L33 57.634–139.300 ms. Accepted-swap duration is bounded at 66.811–133.266 ms and includes the unchanged native 120 ms schedule. All overlap checkpoint-77 brackets; this does not establish faster ideal reaction or fresh Match Villains parity. Input timestamps, CPU spans, native schedules and encoded picture timestamps are distinct.

The independent power/tool review covers eight further regression sheets containing 89 thumbnails and two full originals. All 14 regression sheets therefore contain 157 sampled contributors; the current tile/tool set has one additional optional effect capture. No new sampled rendering discrepancy is identified. Parent and independent notes bind the actual current source/APK, inspected images, source movies, original timestamps, native processes and final performance analysis.

## Remaining limits

Remaining gates include synchronous spikes, dense rendering and sampling, cooperative resource preparation/cache pressure, rapid next input, long sessions, broader continuation coverage, fresh reference gameplay and physical Android devices. A targeted passing checkpoint will not imply hitch-free gameplay, a universal speedup, zero allocations or sustained 60 fps.

The next model investigation should isolate L4 rank-cache hits/rebuilds during cascades. First-playback-pose command work, including the retained recorded Build outlier, and dense body sampling/drawing remain higher priorities than expanding dependency caches. Existing continuation still qualifies only four of 350 sampled commands. Cache growth, the preparation cap and demand-cache flush remain unchanged; public disposal checks are not proof of release of every managed reference or a long-session memory audit.

Evidence: [comparison](../../Verification/Evidence/Gameplay78/Comparison.html), [strict summary](../../Verification/Evidence/Gameplay78/Summary.json), [execution analysis](../../Verification/Evidence/Gameplay78/Execution_Analysis.json), [sampled visual review](../../Verification/Evidence/Gameplay78/Visual_Review.json), [original-PTS notes](../../Verification/Evidence/Gameplay78/Timing_Visual_Notes.json). The strict collector recomputes the analysis and rechecks frozen inputs, archived same-platform controls, both builds, final APK, unchanged real data and actual inspection bindings before publication. Historical failures are retained separately from the final passing checks.

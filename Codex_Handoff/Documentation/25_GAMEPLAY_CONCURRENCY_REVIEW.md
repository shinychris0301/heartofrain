# Concurrent powers, mixed-swap creation and obstacle handoff review

21 October 2026. Unity 2022.3.62f3; live M46 board/model and M48 partials, with the M47 gameplay controller.

## Current checkpoint

Three defects are reproduced and repaired in source: a gem swapped with an existing power skipped its initial match recipe; the sprite cache repeatedly discarded and recreated frames during large combinations; and ordinary obstacle hits lost their body animation or cleared their displayed goal early at a phase boundary. The existing artwork, manifest/GUID bindings, authored level masks, move budgets, individual fall routes, portrait policy and completion/reward rules are preserved.

The combined ARM64 Android build passes with 0errors and the existing1 SDK/tooling warning. Final APK:207,164,595 bytes, SHA256 `d9a14f1dcd9a296399ce02525130c129d86f283d993d2b4d04fce7a27042fada`. Signing, ZIP/ELF alignment, portrait manifest and all seven M70 payload checks pass. All 4,273 frozen non-Editor asset/code/meta inputs match the build. Actual touch and timing evidence below belongs to this APK; the final campaign and installation results below pass. Earlier reviews retain their original APK scope.

## Confirmed defects and resulting behavior

| Finding | Reproduction and cause | Repair |
| --- | --- | --- |
| Missing power creation after a gem/power swap | `BoardModel.Swap` finds the newly formed gem match, but its one-power branch queued the existing power and skipped `ResolveMatches`. That power could erase the recipe before a subsequent cascade saw it. The baseline native mixed-swap regression fails on the missing birth. | Resolve the initial match before the original source power activates. Preserve the matching swap endpoint, gesture-axis Rocket rule, Orb target color and single move/turn charge. |
| Large combinations recreate native sprites during playback | A 768-entry sprite cache is smaller than the tested Orb/Rocket and Golden/Bomb frame working sets. Repeating an already warmed sequence still creates and evicts more than 1,000 sprites. | Retain a bounded 2,048-entry working set; preserve pinned and currently visible sprites; reuse eviction scratch lists and track texture bytes without repeated enumeration. No duplicate texture sheets or higher texture budget are introduced. |
| Basic obstacle hit animation cuts off | A normal match is shortened to 0.16 seconds. Its hit occurs at 0.05 seconds, leaving only 0.11 seconds of the existing 0.8-second hit body before the following phase replaces it with lower-HP idle artwork. | Continue the newest unfinished stone/moss/case/gate hit through gravity or idle using its absolute presentation clock. A later hit takes ownership; an absent piece is never recreated. |
| Final obstacle clear/counter handoff is premature | Basic removal/counter clearance occurs at hit + 0.24 seconds, or 0.29 seconds in the fixture. The old phase ended at 0.16 seconds and the next snapshot already omitted the obstacle and decremented its goal. | Schedule damaged basic matches together with their following gravity. Unaffected columns can begin after the existing 0.16-second match beat; routes through the cleared obstacle wait for its local clear marker. A terminal match without gravity also retains the clear marker. |

The mixed-swap change does not grant a newborn immunity. If the original power legitimately hits the newly created item, that item follows the normal chain rule. The targeted suite includes 240 such chained births; creation and activation are separate, recorded events. A player should not infer that creation failed merely because the item is then consumed by the same turn.

Golden + Golden remains undefined, Golden Seeker receives no new match recipe, and existing recipe priority remains five-line Orb, intersecting-line Bomb, four-line Rocket, then square Rain Seeker. Model/service code continues to own moves, damage, goals and stock. These visual changes add no reward or inventory mutation callbacks.

## Performance evidence and its limits

The fresh **before** Android capture uses the preceding M70R2 APK in LDPlayer. The timed probe records unaccelerated native Update intervals and command CPU paths without screenshot readback or video recording during the measurement. It includes emulator scheduling and CPU/GPU waits; it is not a physical-device GPU profile.

| Before phase | p95 Update interval | Worst interval | Command path |
| --- | ---: | ---: | ---: |
| Three-Rocket chain | 16.67 ms | 150.02 ms | 154.58 ms |
| Orb + Rocket | 33.34 ms | 233.37 ms | 111.13 ms |
| Golden + Bomb | 50.01 ms | 116.68 ms | 116.14 ms |

Source: [before device measurement](../../Verification/Evidence/GameplayAudit/Before/Measurement.json). The first two natural commands also took approximately 55.77 and 89.26 ms. There are therefore command-start costs as well as sustained heavy-effect pressure. The evidence does not justify describing every visible pause as one cache defect, or claiming that the app now holds 60 fps.

Native Unity Editor atlas playback isolates repeated cache churn. Each workload is sampled twice through the actual atlas bank; the second pass is warm. The following measurements exclude display/GPU presentation and are aggregate sequence CPU times, not frame times:

| Warm sequence | Before sprite creates/evictions | After sprite creates/evictions | Before / after aggregate CPU |
| --- | ---: | ---: | ---: |
| Three-Rocket chain | 0 / 0 | 0 / 0 | 4.23 / 6.27 ms |
| Orb + Rocket | 1,324 / 1,324 | 0 / 0 | 284.26 / 37.75 ms |
| Golden + Bomb | 1,132 / 1,132 | 0 / 0 | 220.09 / 45.89 ms |

The large-combination improvement is supported by native creation/eviction counters, rather than inferred from an unchanged texture-load count. The simpler warmed Rocket workload does not improve in this microbenchmark. Tested retained sprite metadata is approximately 1.24 MB for Orb/Rocket and 1.13 MB for Golden/Bomb; these are Unity-reported sprite-object sizes, not complete graphics-driver memory accounting. The texture budget remains 128 MiB.

The renderer also caches generated tile/debris/hit keys, removes recurring captured lookup predicates in sampled power glow, and reuses advanced obstacle size/name storage. The pure performance checkpoint passes 162 custom native checks, including67 unchanged authored pose signatures. The final combined-source run passes 174 checks including bounded cache/pinning/disposal controls. It was run **before** the intentional obstacle continuity/refill change, keeping optimization parity separate from an approved visual correction. Later actual sequence signatures may differ because of that correction.

Sources: [before sampler/atlas report](../../Verification/Evidence/GameplayAudit/Before/Sampler_Atlas.json), [pure performance after report](../../Verification/Evidence/GameplayAudit/After/Performance_Only_Sampler_Atlas.json). The final combined-source sampler/cache run passes 174 checks and retains all 67 authored/crystal pose signatures; its warmed heavy sequence CPU is 30.19 ms for Orb/Rocket and 27.15 ms for Golden/Bomb. The final Android measurements are recorded below.

Both tested allocation measurement routes in this native Editor environment fail their positive controls. Reports mark the counter **UNAVAILABLE** and do not claim zero allocated bytes. Source pooling and a flat or unavailable counter do not certify allocation-free playback. Earlier zero-byte observations in historical reviews must be read with this newly established limitation.

## Model command CPU and replay compatibility

The model command benchmark passes 1,002 native checks across 200 cases (all 50 boards times four command types), using200 warm-up and 400 timed independent solves. All 200 raw TurnResult hashes and final BoardSnapshot hashes match the fixed-creation baseline exactly. This isolates the allocation cleanup from the intentional gem/power rule repair.

| Command family | Median native Editor CPU before / after |
| --- | ---: |
| Natural swap | 0.922 /0.713 ms |
| Three-Rocket chain | 1.298 /1.187 ms |
| Orb + Rocket | 2.414 /1.690 ms |
| Golden + Bomb | 1.828 /1.349 ms |

These are command CPU measurements, not Android input latency. The matcher now creates storage only for actual runs or squares; it preserves traversal, merge order, priority, snapshots and validation. Sources are Before/Model_Commands.json and After/Model_Commands.json.

Two campaign recordings required new expected fingerprints after the intended match handling repair. L21 action13 now resolves its initial three-match; L49 action23 creates the previously missing horizontal Rocket. Both original seeds and every action coordinate/type are unchanged. Both still win (13/30 moves for L21,30/44 for L49), the other three clear records and all 50 authored level files are unchanged. Campaign_Replay_Refresh.json binds that diagnosis, old backup, updated resource and authored level hashes. The530-check native general suite then passes. The development replays do not establish human balance.

## Final Android performance and visual evidence

The same dedicated Android14 LDPlayer/ARM-translation profile ran the unrecorded before/after probes. Both runs contain eight phases and no runtime errors. The table uses the broader slow-frame counter because three-refresh intervals round to50.007 ms before and 49.976 ms after. A strict greater-than50 ms comparison would overstate the reduction.

| Phase | p95 before / after | Worst before / after | Intervals over33.34 ms before / after | Gen0 collections before / after | Command CPU before / after |
| --- | ---: | ---: | ---: | ---: | ---: |
| Three-Rocket chain | 16.67 /16.66 ms | 150.02 /49.98 ms | 1/168 /1/169 | 2 /1 | 154.58 /58.56 ms |
| Orb + Rocket | 33.34 /33.32 ms | 233.37 /99.95 ms | 23/497 /18/528 | 12 /2 | 111.13 /68.30 ms |
| Golden + Bomb | 50.01 /16.66 ms | 116.68 /49.98 ms | 28/463 /1/564 | 10 /1 | 116.14 /56.98 ms |

Sources: Before/Measurement.json, After/Measurement.json, and each variant's Installation.json. These are single controlled emulator runs, not a population benchmark. Command time includes model and presentation enqueue work; the new after probe records those separately. `firstPresentationMs` means the StepStarted event was dispatched, not that a frame was displayed or a physical touch completed. No synchronous texture loads or sprite evictions were observed in the after phases. Median frame intervals remain about 16.66 ms, but Orb/Rocket still reaches99.95 ms and has18 intervals over33.34 ms. Sustained60fps and removal of every hitch are not established.

Eight native Android gesture cases pass: MixedH, MixedV, MixedBomb, MixedOrb, MixedSeeker, MixedChain, ObstaclePartial and ObstacleClear. All eight full native videos and focused12-frame plates were reviewed. Creation is visible at the matching cell, then follows legal gravity; the hit newborn visibly chains. Partial stone hit animation continues through refill, and destroyed stone cells refill without a gap. Visual_Review.json freezes the reviewed videos, plates and pose reports. Recording overhead means these movies are visual evidence rather than frame-budget measurements.

The first expanded timing probe called a thread-allocation API that is unimplemented in this pinned IL2CPP player. The installed engine's GC.cpp and assertion macro confirm that diagnostic failure. It was removed from development instrumentation; production gameplay files were unchanged by that correction. Both failed starts/diagnostic captures are excluded, and the corrected player completes all eight phases. See Intermediate/Probe_Instrumentation_Correction.json. Native Editor counters remain unavailable and no zero-allocation claim is made.

## Reference comparison

Fresh actual Android recordings use the installed **Match Villains v7307** on the original LDPlayer instance. The comparison uses ordinary board actions and preserves the installed app's saved progress.

| Reference evidence | What it supports | Limit |
| --- | --- | --- |
| `Reference/MV_Natural_Refill.mp4` and frame sheet | Relative sequence of match contact, falling tiles and settling during ordinary play | The reference board, random colors and effect load differ from ours. |
| `Reference/MV_FourMatch_Creation.mp4` and frame sheet | Visible four-match creation and its relation to the moved matching tile | Reference progression/Lucky effects must not become an unapproved rule in our model. |
| `Reference/MV_Rocket_Hits_Bomb.mp4` and frame sheet | A rocket hitting another power, with the secondary reaction occurring within the continuing board sequence | Screen recording cannot isolate the reference app's CPU, GPU or model implementation. |

The exact gem/power swap completing a four-match was **not reproduced in the reference app**. Our repair is justified by the owner's explicit expected behavior and reproducible native model fixtures. It is not presented as direct proof of that exact competitor rule. Likewise, these recordings support sequencing and visual analysis, not pixel-perfect parity, identical acceleration curves or a controlled FPS comparison. ADB dispatch and screenrecord clocks are not synchronized.

The confirmed shortcomings are missing match handling, recurring frame recreation and premature visual phase handoff. The remaining apparent differences—effect density, particle occlusion, body scale during motion and perceived acceleration under load—require final current-build recordings and inspection before being called additional defects.

## Verification coverage

| Feature / risk | Current evidence | Practical limit |
| --- | --- | --- |
| Gem/power swaps and all normal power recipes | 2,996 native checks over 360 recipe/source/direction/endpoint/board-shape cases; 240 newborn chain cases; no-match, three-match and unsupported pair controls | All six actual Android mixed-swap cases pass and their frame plates are reviewed; two additional obstacle cases pass. |
| Natural model play | Final audit:18,134 checks overall; 150 board/seed combinations and 1,197 natural actions, with deterministic repeated solves, identity/goal validation, stable matching and fixed-point gravity | Eight-action sampling per run, shortened on a win; not a full human campaign or exhaustive state search. |
| All approved pair families | 700 native pair cases across all 50 boards | Staged initial powers, not every naturally obtainable arrangement or arbitrary chain topology. |
| Manual tools | 200 native tool cases; accepted/invalid stock charges, move/turn preservation, stable result checks | Actual tool animation/performance and persistent stock across process restarts are separate. |
| Basic obstacle damage and clear | All six native stone/moss/gate boundary cases become continuous; case covered through a direct tool hit; newest-hit, expiry, absent-piece, local-clearance and goal-marker controls | Actual Android partial-hit and clear movies/plates reviewed; native boundary checks cover exact local timing and goals. Advanced obstacle behavior is preserved and relies on its existing regressions plus refreshed runs. |
| Power rendering and cache | 174 final native checks,67 authored pose parity signatures, cold/warm native atlas workloads | Editor CPU/metadata measurements do not certify full Android frame budgets. |
| Individual falls, swaps, M70R2 creation, campaign definitions and replays | Fresh final-source suites pass:81,325 fall checks,10,681 timing checks,122 swap checks,1,173 creation checks and530 general checks; all recorded clears verified | Individual suites keep their stated coverage; historical APK results remain separate. |
| Portrait, navigation, first start, celebration and Home reward flow | Prior targeted native/device evidence remains available in reviews 16–24 | These pages were not redesigned in this repair; a full current-APK UI sweep remains separate. |
| Profiles, attempts, inventory, purchases and social services | Existing source audit and production backlog | Session-level checks do not close durable save/settlement/inventory gates. Shop, Leaderboard, Teams and timers remain demo data until services exist. |

The corrected final audit passes 18,134 checks and all six obstacle boundary regressions. Unsupported allocation counters are recorded as unavailable; no zero-byte allocation claim is made. The connected app smoke and general530 checks pass, as do2,996 mixed-swap checks,10,681 timing checks,81,325 individual-fall checks,122 swap/creation checks and 1,173 M70R2 checks. These are fresh combined-source runs in Native_Checkpoints. Timing-check counts differ from earlier runs because damaged matches now share a refill timeline; the new boundary assertions cover that change.

These are custom native Unity checks, not a claim that Unity Test Framework/NUnit, physical Android devices or a complete human playtest passed.

## Changed implementation and verification paths

| File | Purpose |
| --- | --- |
| `Unity/Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs` | Handle initial gem matches in the one-power swap path; preserve source color and normal hit chaining. Preflight candidate runs/squares and reuse direction entries before allocating match storage. |
| `Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPlayback.cs` | Merge basic obstacle match/refill timing, local clear reservations and terminal clear-marker handoff; retain existing per-tile routes. |
| `Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPresentation.cs` | Cached sampled keys/lookups and newest unfinished basic-hit continuity across presentation phases. |
| `Unity/Assets/HeartOfTheRain/M46/Runtime/M46AtlasBank.cs` | Bounded sprite working set, reusable eviction scratch storage, texture-byte accounting and diagnostic cache counters. |
| `Unity/Assets/HeartOfTheRain/M46/Runtime/ReviewPlan.cs` and `M48/Runtime/AdvancedObstaclePresentationPure.cs` | Remove recurring sampled lookup/temporary-storage work while retaining authored poses. |
| `Unity/Assets/HeartOfTheRain/Verification/MixedPowerSwapFixtures.cs` and `Editor/MixedPowerSwapVerification.cs` | Reproducible mixed-swap creation/chain tests. |
| `Unity/Assets/HeartOfTheRain/Verification/GameplayAuditFixtures.cs` and `Editor/GameplayAuditVerification.cs` | Shared transient obstacle boards, cross-level model stress and phase regression checks. |
| `Unity/Assets/HeartOfTheRain/Verification/Editor/GameplayPerformanceVerification.cs` and `GameModelPerformanceVerification.cs` | Native sampler/cache and isolated model command measurements, with scope/positive-control checks. |

`GameplayAuditVerification.Baseline()` retains observational boundary diagnostics without asserting the repaired behavior. `Run()` performs full stress plus the repair regressions. `RunObstacleChecks()` runs just the obstacle/carry-through checks. The shared development fixture `GameplayAuditFixtures.Obstacle("stone", hp)` uses a real swipe from `(4,2)` to `(4,3)`. These fixtures do not replace authored campaign data or write production progression.

## Remaining limits

Native checks, the combined build, actual Android mixed-swap/obstacle captures and separate timing measurements are complete. The final APK passes 1,705 Android checks across all 50 boards:13,976 visible-label inspections,354 clip samples and 408 programmatic live actions. All 304 fresh native GPU frames decode at900x1600; stale remote frame files are excluded. The connected celebrations, Home reward increase, failure and retry flows pass. Twenty app-page captures, eight gameplay sequences, the selected connected-flow plate and both final Home displays were visually reviewed. These samples do not imply exhaustive pixel review or human-language approval. Native timing remains separate from movie review.

The remaining Orb/Rocket workload reached 347 active sprites and created 1,268 native sprite frames with no evictions. First-use Sprite.Create, on-demand SpriteRenderer pool growth, transparent overdraw and model/enqueue CPU are follow-up profiling candidates; their individual contribution to each long frame is not isolated by the current interval probe. The after command splits into 41.67 ms model and 26.61 ms enqueue, while other frame spikes occur during playback. A larger cache closes measured eviction churn but does not establish a complete first-use or physical GPU budget.

Manual-tool rendering remains an unprofiled source hotspot: `BoosterTimelinePure` creates per-frame DrawSprite objects and uses recurring lookups. This is not evidence that it caused the measured simultaneous-power stalls, and it is not closed by the power cache repair. Cold resource prewarming can also gate the next presentation step; first-use holds should be distinguished from warm playback and synchronous model work.

Physical Android performance, device memory/thermal behavior, long sessions and resume, human difficulty, exhaustive human UI/campaign review, durable profiles/attempt settlement/inventory and real billing/social services remain open. No engine/SDK upgrade, art redesign or unresolved gameplay choice is implied by this review.

## Final installation and evidence

The exact final APK is installed and running on original LDPlayer instance 0 (`127.0.0.1:5555`) and dedicated QA instance 1 (`127.0.0.1:5557`). Both launch Home in portrait. Installed APK SHA256 matches the canonical artifact. No data clear or uninstall was performed; shared-preference hashes match across both final installs and across the entire current-build test span. This preservation check does not close durable profile/inventory service gaps.

Open [Comparison.html](../../Verification/Evidence/GameplayAudit/Comparison.html) for reference/native movies, plates and timing tables; [Verification_Summary.json](../../Verification/Evidence/GameplayAudit/Verification_Summary.json) contains the linked gates. Source_Changes.json and Gameplay_Changes.patch compare the six production files against the installed M70R2 baseline. Campaign_Replay_Refresh.json separately proves the narrow replay fingerprint update.

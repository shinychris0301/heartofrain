# Command construction and dense-effect smoothness

25 October 2026. **Targeted verification passed, with remaining performance gates.** Comparison baseline: checkpoint 75. Unity remains 2022.3.62f3. The current source is frozen at 5,115 inputs, SHA-256 `13dd5ea4f9179aaf52a111bceddffdc1dda84ca838797bf790c0ecc45b493641`. Seven existing C# files change and three verification files plus metadata are added. Artwork, existing metadata/GUIDs, level masks, packages and project settings are unchanged. The exact new APK is installed on QA; the main LDPlayer installation was not touched.

## Changes

`LocalCascadeContinuation.cs` reuses a validated strict-planning prefix when the same pair retries the existing terminal rule. The strict check still runs first. Only the same two landing-window rejections, at the same terminal position, can reuse the prefix. A fresh decision owns its copied columns and padding; public strict and terminal results retain their rejection order and fields. The accepted terminal path calls the established disjoint fallback for its duration comparison without rescanning all strict pairs: every earlier/current strict candidate has already failed, and the only unvisited pair ends in the validated settled step. The frozen checkpoint-74 entry remains unchanged. This reduces repeated planning without expanding eligibility or altering animation schedules.

`BoardPlayback.cs` constructs fall routes in first-seen ID order using one dictionary and ordered route list. Per-ID legs retain encounter order, the first raw leg owns spawn metadata, and subsequent legs update only the final destination after preserving the first leg. The unused provisional duration is removed. Repeated immutable distance/origin-duration calculations are hoisted without changing arithmetic order. Returned queues and raw model steps retain their original ownership.

`EffectMeshBatcher.cs` skips two trigonometry calls only for exactly zero rotation, retaining signed-zero sine and the original vertex arithmetic. Tiny/nonzero angles still use the original path. Geometry, UVs, colors, mesh grouping, topology, depth, material and effect counts are unchanged. A development-only control restores checkpoint-75 transform math for isolated comparisons.

`GameplayScreen.cs` adds a development-only option to omit per-draw Stopwatch calls while retaining whole-render, sample, upload and frame measurements. Existing probes default to detailed timing. Coarse per-draw zeros mean unmeasured work. `ObstacleDensityProbe.cs` adds alternating old/current transform pairs on the same process, using sparse/dense fixtures with fresh preparation per branch; detailed/coarse runs remain separate processes and cannot by themselves isolate timer overhead.

New `Smoothness75Control.cs`, `SmoothnessCommandProbe.cs` and `SmoothnessCommandVerification.cs` compile the exact archived-75 playback and continuation bodies under an isolated namespace. Archived foreign continuation objects never enter live gameplay. Eight immutable raw turns use 12 alternating warmed Build pairs per fixture; signatures, validation and serialization remain outside the measured construction spans. Their allocations can influence later collections, so all pairs and GC events are retained.

## Native proof

All 26 pinned-Unity suites pass 711,505 checks against identical frozen inputs. The new construction suite passes 3,351 checks, comparing 1,400 complete queues over 350 natural/power turns, with geometry present/absent and sequential/current scheduling. Recursive nonserialized tracks, branch-correct composite segments, contact/position/moving samples and unchanged raw inputs are included. Archived model outcomes remain identical.

Continuation verification passes 513,006 checks, including 388 main/seeded/mixed/chain comparisons, 43 independent guard inputs and 1,457 public decision comparisons against compiled checkpoint 75. The original 44 guards, four qualifying authored turns, seeded controls and body/landing/feedback continuity remain intact. Eligibility remains four of the sampled 350 commands, at most one handoff per turn.

Effect verification passes 339 checks, including 65 exact uploaded-mesh states, 15 alternating CPU rows and two pixel controls with zero channel differences against checkpoint 75. Zero/signed-zero/tiny/nonzero rotations, scales/flips/tints, empty/shrink/regrow, ordered drawing and growth beyond the reserved slots are covered. Parent inspection of six full native plates found no new visible discrepancy in that sampled scope. This does not equate the older SpriteRenderer composition path with grouped meshes.

Warmed Editor planner medians for the three terminal cases fall from 0.66-0.92 ms to 0.34-0.50 ms. Seven of eight full Build benchmark medians improve; L4's all-pair median increases from 0.642 to 0.989 ms, with six current-branch Gen0 events and none in the old branch. This correlation is not exclusive cause proof and no primary samples are excluded. Actual-fixture effect Add medians improve modestly; rotated controls remain flat/mixed. These are Editor CPU diagnostics, not Android frame-rate or allocation-saving claims.

## Android and remaining gates

Both Android builds pass with zero errors. The cleaned development APK is `d11c0dbccf00c2669a064128102846601792c1362d6cda79e3913d0359c0cefb` (302,230,150 bytes); signature, ZIP CRC/alignment and native-library checks pass. It is installed and remotely hash-verified on QA. The first ADB preflight query failed before installation, then the unchanged runner proceeded after readiness recovered; no reset, data clear or main-instance action occurred.

The same-APK command probe passes eight fixtures and 96 alternating construction pairs (192 Builds), with real saves/preferences unchanged. Median pure playback-construction spans are:

| Fixture | Archived 75 (ms) | Current 76 (ms) |
| --- | ---: | ---: |
| L4 match | 9.674 | 9.153 |
| L14 match | 11.626 | 6.766 |
| L31 match | 11.898 | 6.707 |
| L33 match | 8.067 | 4.935 |
| L1 Golden | 2.469 | 2.161 |
| L26 Bomb | 2.549 | 2.603 |
| L48 Orb | 1.440 | 1.254 |
| Dense crate / double Orb | 7.483 | 6.454 |

The three terminal fixture medians improve by 39-44%. Seven of eight primary all-pair medians improve; Bomb increases slightly. The current maximum is nevertheless 24.498 ms versus the archived-control maximum of 15.995 ms, and all GC events and slower pairs remain included. These are warmed pure construction spans, not whole input-to-display latency; allocations from validation outside the measured calls can affect subsequent collections.

All nine ordinary final-APK Android stages pass, including 40 density turns and the full campaign regression: 1,716 checks, 14,105 labels, 408 actions, 354 clips and 50 boards, with failures empty. Real saves/preferences match before and after every stage. Additional 64 alternating sparse/dense transform turns (32 pairs) and four current recordings pass their functional/data checks. Dense whole-render medians remain mixed across counts, families and detailed/coarse modes; native transform savings do not establish a universal Android rendering speedup. `Paired_Performance.json` retains every signed result.

The largest remaining paired-run result is **68.1597 ms Render at frame 1247, followed by a 149.973129 ms interval at frame 1248**, in detailed `stone_1_0_current76`. This is a sparse one-obstacle fixture, separate from the ordinary density maximum of 30.4363 ms. Its expensive Render starts 2.756 seconds after the initial 43.044 ms command completes, during `powerFall`; it is not the command-onset cost. That frame has 369 draws, 349 mesh quads and 16 meshes, with two new sprites/two geometry misses and no new renderers or mesh slots. Measured stages include sample 10.760 ms, lookup 14.565 ms, Add 13.291 ms, upload 1.572 ms and SpriteRenderer update 5.756 ms. Roughly 22.203 ms lies outside those brackets. These elapsed measurements do not prove an exclusive CPU, resource or host-scheduling cause. The one Gen0 event is row-wide, not frame-local. The following frame's Render is 18.344 ms. Separate control-75-transform maxima are 34.329 ms Render and 100.057 ms interval; only transform math differs in that branch, with all other code still current 76. All neighborhoods and mode-specific extrema are preserved.

Ordinary six-case commands reach 51.289 ms. The 60 fps case has a 50.021 ms interval; the overall 66.695 ms maximum belongs to the intentional 15 fps fixture and matches its requested pacing. The separate eight-phase Fluidity run retains a 54.369 ms command and a 66.708 ms interval in victory animation. Current recordings retain command/Build/interval maxima of 53.240/29.139/67.192 ms, separately from unrecorded timing. None establishes sustained 60 fps or a hitch-free game.

Actual review covers six full native plates; four fresh movies with original timestamps and sampled full frames; parent inspection of six regression sheets (68 constituent stills) plus five full Android originals; and independent inspection of eight power/tool sheets (89 constituent stills) plus two full originals. Sheet thumbnails do not imply every constituent was viewed at full resolution. No new rendering discrepancy was identified in this scope. Existing sealed moss pockets remain qualified, not declared universally gap-free. Recorded contact-to-first-fragments bounds are L4 100-167 ms, L14 69-136 ms, L31 67-133 ms and L33 65-135 ms. They overlap checkpoint 75; ideal queues and schedules are unchanged. The accepted-swap visible bound of 67-134 ms includes the preserved native 120 ms schedule. This pass improves CPU construction without claiming a newly shortened ideal fall or reaction schedule.

Existing power protection, source actions/chains, 120 ms accepted swaps, obstacle semantics, durable settlements and 900-coin full-life refill remain unchanged. Model construction, first-use costs, fallback waiting, host/emulator scheduling, physical devices, long sessions and rapid next-input decorative-landing transitions remain separate gates. Reference-app evidence remains archived; this pass does not establish fresh Match Villains parity.

Evidence: [comparison](../../Verification/Evidence/Gameplay76/Comparison.html), [strict summary](../../Verification/Evidence/Gameplay76/Summary.json), [paired analysis](../../Verification/Evidence/Gameplay76/Paired_Performance.json), [remaining gates](../../Verification/Evidence/Gameplay76/Performance_Gates.json), [visual review](../../Verification/Evidence/Gameplay76/Visual_Review.json). The collector independently rechecks source, native/build/device identity, unchanged saves, raw paired analysis and actual review bindings. Its targeted pass does not close the explicitly retained smoothness gates.

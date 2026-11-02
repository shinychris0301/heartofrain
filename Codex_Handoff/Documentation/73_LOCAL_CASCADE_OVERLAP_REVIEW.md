# Local cascade overlap and current gameplay review

24 October 2026. Unity remains 2022.3.62f3. This follow-up preserves the checkpoint 72 mixed-power protection, 900-coin life refill and first-pose clock repair. Approved artwork, existing GUIDs, levels, packages, engine settings and earlier checkpoint 65/66/67 corrections remain unchanged.

Collected status: **PASS_CONSERVATIVE_LOCAL_HANDOFF_WITH_REMAINING_GAMEPLAY_GATES**. The targeted rule/price fixes and restricted overlap pass their native/device checks; the remaining responsiveness and frame/command issues below are still open.

## Behavior and measured improvement

The swapped power still activates. A power earned by that initial mixed match survives the originating attack and its pre-existing chained powers. Its protection ends before gravity and later cascades; it can be activated normally by a later independent action. The full-life refill costs 900 coins, fills five lives from zero, and retains durable receipt/idempotency behavior. Checkpoint 72 documents those implementations and their transaction controls.

Detailed checkpoint 72 video review also found a separate responsiveness defect: a completed local match waited for unrelated refill. The reproduced level 4 red row took 505.312-575.578 ms from contact to first visible break. The new recording measures 299.456-367.133 ms using the same seeded turn, original video timestamps and conservative frame bounds. The observed improvement is 138.179-276.122 ms; the video does not establish an exact 200 ms gain.

The planner now permits one conservative handoff between two ordinary match/refill phases. It waits for every route in columns changed by the next phase, then carries unrelated unfinished routes into that phase with their original clocks. In the reproduced case, five existing crates and one spawned gem in column 7 keep falling while the red match and adjacent one-layer Moss reaction proceed in columns 1-4. Their identities, paths, spawn portals and landing poses are preserved.

The native handoff occurs at 0.511421 seconds instead of 0.711421 seconds, saving 200 ms of scheduled playback. Local matching contact occurred at 0.266421 seconds, leaving 245 ms of scheduled local waiting. The final video still contains 198.634-266.233 ms of stable waiting after landing deformation. This is a bounded improvement; immediate local reaction remains unfinished.

## Implementation and safeguards

`M46/Runtime/LocalCascadePlayback.cs` operates on playback copies after the existing planner. `BoardPlayback.Build` retains a sequential control for verification. Raw model turns, random outcomes, goals, checkpoints, rewards, inventory and transactions do not change. The pass is idempotent and permits at most one handoff per turn.

The successor must leave every carried identity and its state unchanged. Its changed cells and complete route-column footprint must be disjoint from carried paths, and its duration must cover every carried contact and landing tail. Previous body-clear and goal-visibility markers must already be complete. Powers, newly created powers, deliveries, advanced bodies, conflicting columns, unsafe side feeds, invalid route timings or coordinates, and multiple tracks keep sequential playback. Existing route validation still owns full path geometry. One-layer basic Moss is explicitly covered because it occurs in the reproduced case. Only one of the 350 sampled native turns qualified for overlap.

`BoardPresentation.cs` retains a bounded prior-landing cache when a future motion would otherwise replace an unfinished landing. It preserves the old pose until its original expiry, only at the same cell and when that landing finishes before the future motion begins. This avoids the position/scale pop found during review. Cache pruning uses the existing animation clock, including pause behavior.

`IndividualFallVerification.cs` checks route endpoints and collisions through the last contact even when a phase hands routes to its successor. Separate cross-phase renderer checks prove continuity and ownership; endpoint assertions remain in place.

## Native and Android evidence

All 20 fresh native suites pass 175,435 checks against the same 5,097 frozen Unity inputs. The local-cascade suite contributes 29,106 checks: 350 paired model commands, 30 mixed-power controls, four existing-chain controls, 14 unsafe-case guards, route/landing/counter/effect samples, pause controls and planner CPU diagnostics. The separate cascade suite contributes 2,858 checks. All 200 established model-command hashes match checkpoint 72.

The reproduced renderer control checks 177 dense sample instants at 240 Hz for six carried bodies, including the handoff. Separate deterministic controls cover 15/30/60 fps, late-frame and pause clocks. Maximum boundary position jump is zero; scale difference is floating-point noise. Raw turn and final snapshot parity pass. These are native model/sampler controls, separate from Android frame-rate measurements.

The rebuilt development APK is `2f235fb392d83392a67ae2b08b4f813968adbf4dad6c8fd14925913dc8758e07` (301,704,395 bytes), installed and hash-verified on QA LDPlayer. Build/import/ZIP/alignment/signature/ELF checks pass. Main LDPlayer retains deployment 64; QA is the current review target.

All nine final-APK Android stages pass with the real QA profile and preferences unchanged. Six actual mixed-power swipes visibly show the original Rocket firing while the newly earned horizontal/vertical Rocket, Bomb, Orb or Seeker falls and remains idle. Forty warmed density turns cover crate, stone, gate and tile destruction at 1/8/16/32/45 targets, twice each, without additional renderer or obstacle-sprite creation. These counters do not establish zero allocation.

The six-match level 4 sequence takes 3.543/3.527/3.626 seconds at 60/30/15 fps targets in separate unrecorded timing runs, preserving the same model hashes. All eight fluidity phases have a 16.7 ms frame p95; their worst frame is 83.3 ms and maximum synchronous command is 75.4 ms. A separate level 4 measurement still has one 183.3 ms interval. Warmed density diagnostics include an 84.5 ms command and a 23.7 ms burst render. Separate process/cache/scheduling conditions prevent attributing every before/after timing difference to this handoff.

The final accelerated regression passes 1,716 checks, 14,105 labels, 354 clips, 408 actions and all 50 authored boards with no failures. It exercises cabinet/case/crate/crystal/gate/moss/pod/stone damage, jar delivery, tools, individual powers, supported power pairs, continuation purchases and connected win/loss/finale flows. Fresh inspection covers full 899/900/full-life screenshots, two actual-swipe obstacle results, board/mask/route/power/flow sheets and the separately recorded videos. The refill screenshots visibly show No lives at 899, Refill 900 at exactly 900, and 0 coins with 5/5 Full after purchase. Accelerated campaign captures, actual swipes and unaccelerated timing measurements retain their separate scopes.

## Reference comparison and remaining work

The reference comparison uses archived actual Match Villains recordings, their original presentation timestamps, recorded capture dates and available version manifests. A current gameplay capture remained on TNT Snitch Loading at level 463; the cause was not established. The archive shows accepted swaps around 86-133 ms, a one-cell fall around 124-198 ms, and a different local green-row reaction within a conservative 0-80 ms sampling bound. Our accepted swap remains 120 ms and one-cell gravity about 141 ms. These different boards and visual endpoints support a responsiveness comparison, not identical internal physics or exact reference parity.

Full local immediacy needs causal continuation within affected columns. General power/advanced-obstacle/delivery cascades and further overlaps retain their existing barriers. Synchronous command/preparation costs and occasional long frame intervals remain independent issues. Sustained physical-device performance, cold/warm profiling, long-session testing, human campaign balance, audio/haptics and production purchasing services remain separate gates. This review does not certify every frame or the removal of every freeze.

Evidence is `Verification/Evidence/LocalCascade73`: `Comparison.html`, `Summary.json`, `Timing_Visual_Notes.json`, `Timing_Analysis.json`, `Power_Visual_Notes.json`, `Visual_Review.json`, frozen sources, native process reports and Android audits. `Baseline_72.json` binds the preserved baseline APK and reports. The evidence-only layout normalization preserves capture/report bytes and records original-to-canonical paths; it changes no Unity inputs, APK or saves.

Relative to checkpoint 72, source changes are limited to `BoardPlayback.cs`, `BoardPresentation.cs`, `IndividualFallVerification.cs` and three new runtime/verification files with fresh metadata. The runner, strict collector, analysis tools, gallery and this review document those changes. Earlier uncommitted checkpoints 67-71 remain intact.

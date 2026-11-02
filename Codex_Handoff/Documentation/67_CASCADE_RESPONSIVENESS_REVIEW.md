# Fall and cascade responsiveness

23 October 2026 (New York). Follow-up to checkpoint 66. Read the start/status documents and checkpoint 65's corrections first; retain those fixes and the committed Resources bindings. Runtime remains M46/M48 on Unity 2022.3.62f3.

## Findings and reference

The installed Match Villains was observed at level 450. `Verification/Evidence/CascadeResponsiveness/Reference` contains a normal match and a Seeker-triggered refill, recorded from LDPlayer at 720x1280. The normal sequence shows falling bodies while break fragments are still visible; the Seeker sequence shows refill while its flight/effects continue. These observations support overlapping presentation tails with board progress. They do not establish identical obstacle rules, physics or pixel timing between the two games. Earlier checkpoint 22 measured approximately 134–167 ms for a one-cell reference fall; our unchanged one-cell flight is 141 ms.

The larger delay was in scheduling, rather than the one-cell curve:

- `VisibleAdvance` limited every gravity update to about 28 ms, and sometimes less for short route tails. Discarding the rest of each frame caused real slow motion at lower frame rates. Across 350 native cases, median wall/scheduled ratios were 2.133 at 15 fps, 1.267 at 30 fps and 1.116 at 60 fps in deterministic frame-clock simulations.
- Every fall held the entire board for its 100 ms landing squash, even when the next match was ready. Ordinary matches also had a separate 160 ms pre-refill phase.
- Some goal flights extended each intermediate phase until their HUD arrival, introducing delays unrelated to cell clearance. These flights must survive phase transitions, rather than hold every cascade.

The initial full-size Android recording failed; subsequent captures explicitly select 720x1280. A later attempted reference capture showed unrelated advertising and was discarded, not used as gameplay evidence.

## Changes

`M46/Runtime/BoardPlayback.cs` now advances normal frames at elapsed time, with 100 ms of tolerance so ordinary frame jitter does not re-enable slow motion. An exceptional stall still retains intermediate moving poses. One-cell acceleration, terminal speed, individual feeds, route reservation, obstacle clearance and authored hit/trigger clocks remain unchanged.

Short matches and their following refill share a phase. Matched gem cells can release at 90 ms; obstacle routes still wait for their actual clearance markers. Consecutive matches start when the prior refill reaches its cells, without waiting for its decorative landing tail.

`M46/Runtime/BoardPresentation.cs` retains landing poses by tile identity across phases, preserving the full 100 ms squash and exact final resting pose. Landing records are value types, pruned after completion. Goal flights retain their complete authored duration and glint in history. The HUD counter holds each unfinished flight once until arrival, including during idle and later moves. History uses the owning phase reference, avoiding floating-point subtraction to determine ownership in long sessions. `M47/Runtime/GameplayScreen.cs` passes the current clock to this display calculation.

Final winning turns wait for their last goal flight before handing the board to the existing win flow. No board solve, random seed, obstacle damage, power recipe, inventory, reward, profile transaction, level mask, artwork, GUID or importer is changed.

## Verification

Evidence and video review: `Verification/Evidence/CascadeResponsiveness/Comparison.html`. Machine-readable final results: `Summary.json` in the same folder. `Source_SHA256.json` binds the complete Unity inputs to the Android build; native simulations and actual Android measurements are labelled separately.

- All 350 source turn/final-snapshot hashes match the recorded baseline: first legal swaps and six standalone powers across all 50 levels.
- 2,858 targeted native checks cover clock timing, frame jitter, deferred collections, nested power tracks, long-session ownership and landing continuity.
- 81,325 individual-route checks, 10,285 timing checks, 217 obstacle-fall checks, 824 M70 R2 creation checks, 122 swap checks, 534 general checks and 17 connected gameplay smoke checks pass. Older timing checks were updated to check flight completion and independent effect lifetime; they no longer require decorative tails to block a phase. The existing exact-route and creation assertions remain.
- Six unaccelerated native Play Mode cases exercise a six-match cascade at 60/30/15 fps targets, Bomb refill, dense Orb/Rocket chaining and a Golden Seeker/goal case.
- The final Android build, QA installation, six isolated playback cases and separate recorded visual run are bound by the final evidence collector. QA preferences/profile file hashes are checked before and after. These fixtures use the real renderer without campaign attempt or inventory callbacks; they are not physical-touch or full-campaign tests.

In the native frame simulation, the six-cascade level-four case improves from 6.33 to 3.67 seconds at 30 fps; the level-one Bomb case improves from 3.73 to 2.33 seconds. Scheduled one-cell travel remains 141 ms. Actual final Android values are recorded separately in `Summary.json` and the comparison page.

The final QA Android six-cascade measurements are **3.646 / 3.648 / 3.770 seconds** at 60 / 30 / 15 fps targets; Bomb takes 2.371 seconds and the dense Orb/Rocket fixture 5.383 seconds. Fifteen consecutive cascade transitions have no additional scheduled wait beyond their last tile's contact. All six final model snapshot hashes match native Play Mode. Raw serialized turns differ between Mono and IL2CPP for two power fixtures; those records include floating-point presentation plans. Their schedule differences are below one microsecond, but the exact differing fields were not exported, so cross-platform raw byte identity is not certified.

Final APK: 290,393,404 bytes, SHA256 `c129d84551122f668f106e7223fdc3eb83d197f8839b44963a21fcc84b489194`. Zero native build errors; clean Gradle packaging preserves all 1,073 nonsignature entries and the existing signer. The final QA video/sheet and two full-size frames were inspected. Its ordinary Home is left available after the isolated probes; main remains stopped. The build freeze contains 4,942 Unity input files. Older checkpoint reports were restored after collecting fresh copies into this review's folder.

## Scope and limits

The main LDPlayer instance had a live game when this task began. Its package was not replaced or force-stopped for these tests. It was subsequently observed stopped and was not restarted; its installed APK remains deployment 64. The rebuilt checkpoint-67 app is tested on the separate QA instance. This preserves the distinction between the user's installed game and isolated verification.

This is a targeted presentation repair. Physical-device performance, shipping GPU/memory budgets, long-session soak testing, all-feature certification and established production service gates remain open. Reference boards and obstacles differ. No claim of exact Match Villains implementation parity is made.

Reproduce native checks with `Verification/Run-CascadeResponsiveness.ps1`; build with `Run-UnityVerification.ps1 -Mode AndroidBuild`, clean/check packaging with the existing Android tools, then use `run_cascade_timing_device.py --serial emulator-5556 --variant measure --install` and a separate `--variant visual` run. The collector rejects a changed source or mismatched APK.

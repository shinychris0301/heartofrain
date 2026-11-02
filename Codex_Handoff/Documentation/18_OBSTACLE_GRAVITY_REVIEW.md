# Obstacle gravity repair — 20 October 2026

The owner reported empty cells beneath consecutive fixed obstacles after one breaks. This review follows the approved timing/M68 checkpoint in review 17. Engine remains Unity 2022.3.62f3.

## Cause and behavior

The live M46 model compacted each vertical column section independently. A surviving fixed obstacle cut off the section beneath it from its authored spawn. That section never considered neighboring tiles, so breaking the bottom stone in a three-stone stack left its cell empty. This was a model defect, not just a drawing offset.

`BoardModel.Gravity` now performs vertical compaction/refill first, then deterministic one-cell diagonal feeds into vacancies, repeating until stable. Each diagonal wave uses only the vacancies present when that wave starts; newly vacated source cells return to vertical gravity before any further side feeds. This prevents upstream tiles moving before the original hit. Each leg has its own before/after snapshot and motion so the existing playback shows the path around the blocker. A moving piece retains its identity, family and power kind. Fixed obstacles retain their coordinates and footprints. Diagonal movement does not cross inactive mask cells or corners sealed by fixed cells. Crates/jars cannot enter the reserved Storm Crystal lane; jars already on an exit are not diverted. New pieces still come only from authored spawn points. Left is chosen before right when both side feeds are eligible.

This fixes reachable gaps below a stack. A pocket with no descending route from a tile or authored spawn remains unreachable; the repair does not invent portals beneath a solid ceiling. Level masks, initial tiles, obstacle HP, goal counts, move budgets and art files are unchanged. Cascades after an affected refill can differ, as expected from correcting model occupancy. Rewards and inventory remain in their existing services.

## Reference comparison

Installed Match Villains version 7307 was inspected in original LDPlayer instance 0 on level 251. Four accepted normal actions reduced moves from 25 to 21; no premium tool, pre-level item or paid continuation was used. The rocket and adjacent matches retract spring obstacles and the released playable cells refill while other obstacle rows remain. This supports retaining blocker positions and filling released cells. Springs are a different obstacle mechanic: these captures do not establish its internal algorithm or prove an identical vertical-stone case. Our native stacked-stone fixture is the direct reproduction.

Local videos and selected plates are under `Verification/Evidence/ObstacleGravity`. Preliminary swaps aimed at the inactive right-hand mask cell were rejected and are excluded; an interrupted recording during an ADB reconnect is also excluded. The temporary portrait display override was reset to the original 1600×900 size. Match Villains data was not cleared.

## Evidence and changed files

- `Baseline_Checks.json`: original gravity fails the below-stack occupancy assertion; zero diagonal moves and one gap. `Stack_Before.png` is an actual native GPU render of that state before editing the model.
- `Native_Checks.json`: native checks cover bottom/middle/top breaks at both edges and the center, vertical priority, movable families, identity, sealed corners, mask holes, exit jars, crystal-lane exclusion, wide reachable pockets, determinism/idempotency and all 50 boards with six standalone powers. `Stack_After.png` is the corrected native GPU render.
- Existing native model, playback and input lifecycle suites are rerun. Android results and the final APK identity are recorded below when completed.

The production changes are in `M46/Runtime/BoardModel.cs` and `BoardPlayback.cs`. The latter reserves the diagonal source and lower corner until pending power hits/removals there finish, so the tile cannot cut through a disappearing blocker. `Verification/PlaybackFixtures.cs`, `PlayerRegressionSuite.cs` and the new Editor checks provide transient fixtures and native evidence. Four recorded campaign clears needed new action paths/fingerprints because gravity changes later cascades: L28, L36, L49 and L50. L21 remains unchanged. `GravityReplayRefresh.cs` generates and strictly validates legal clears with the authored budgets; it never injects powers or changes level data. This is automated logic coverage, not human balance certification.

Evidence collection/runbook tools and the repair allowlist are updated to distinguish the new APK from prior timing/performance evidence. Existing profile/inventory persistence, services, physical-device certification, human balance and heavy-combo performance gaps remain open. No new frame-budget improvement is claimed for this gravity pass.

## Native checks and artifact

- 6,010 targeted obstacle-gravity checks pass, including the late corner/source reservation cases.
- 14,100 playback checks, 530 general model/import checks, 1,865 fluidity/model checks, 14 input lifecycle checks and nine launch/exit smoke checks pass.
- Native Android ARM64 IL2CPP development build: zero errors, one warning. APK CRC, development signature, ZIP alignment and static ELF checks pass; five M68 runtime textures are included and 14 reference-atlas pages remain excluded.
- APK: `Unity/Builds/Verification/HeartOfTheRain_Development.apk`, 200,806,785 bytes. SHA-256: `493a1f9993b2eb0e2b5c4819536cc1ea01dc3354943c261436ea69686c573b46`.
- `Player_Source_SHA256.json` freezes all 125 non-Editor C# files. Compared with the preceding timing source cache, only the two production files above plus the two opt-in fixture/suite files changed.

Android regression, actual input review and final installation are separate from these Editor/build results. Device capture selects the actual in-flight interval; merely scheduling a delayed diagonal is not treated as movement evidence.

## Final Android result and installation

The final APK passed **1,684 Android checks**, **419 programmatic actions**, all **50 boards**, **354 effect samples**, five strict connected campaign clears and **272 fresh native captures**. `LDPlayer/Regression.json`, `Frame_Manifest.json` and `Stack_Render_Review.json` record the scope. The reviewed stack fixture shows 20 moves throughout, the target count changing from 3 to 2, both upper stones fixed, and a purple gem filling the cleared lower cell. The hammer partly obscures the in-flight body; no precise video latency is inferred. Phase-gated capture and a separate native assertion guard against movement before the original hit.

Actual ADB input was also reviewed: a four-second held drag resolved one move before release, a single rocket tap spent one move with visible clear/refill, and the shared navigation dock stayed aligned during press and page change. These are emulator input/render checks, not frame-budget measurements or human full-level playthroughs. `Touch/Touch_Smoke.json` and its contact sheets retain the observations.

Installed with `adb install -r` and launched in original LDPlayer instance 0 and QA instance 1. Both remote APK SHA-256 hashes match the artifact above. Shared preference files were byte-identical before and after this installation/launch interval; no data clear or uninstall was performed. This does not implement durable campaign/inventory storage. The summary and current campaign/feature coverage now select `ObstacleGravity`; prior timing performance remains historical.

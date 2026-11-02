# Obstacle-family preparation review — checkpoint 46

22 October 2026. Unity 2022.3.62f3. Evidence: `Verification/Evidence/CrateBurst` (refreshed by this checkpoint's native run; no new gallery).

The hold before the first obstacle break on a board is repaired at its source. Level preparation now loads and pins every present obstacle family's clip pages, fragments and layer bodies, not only the crate set from checkpoint 44, so the playback gate never waits for a texture and the first debris frame creates no native sprite. Model rules, damage, goals, refill routes, timings, fragment counts, original artwork and existing GUIDs are unchanged. No APK is rebuilt or installed; Android timing for non-crate families remains open.

## Cause

`M46AtlasBank.CommonResources` and `WarmObstacleFrames` prepared clip pages and native sprites only when the board held crates. For moss, stone, case, sluice, crystal, pod, cabinet and jar the first damage step of each level entry failed `bank.Ready`, `GameplayScreen.Next()` held the board on the previous snapshot with input blocked, and `Prewarm` loaded that family's 4–7 page textures one request at a time, waiting at least a frame on each. When the step finally started, every first-seen fragment and accent frame was created with `Sprite.Create` on the frame the debris appeared. Crystal boards also met the gate on the very first swap, because `EffectResources` requires the crystal family whenever a crystal is visible. The hold recurred after every retry or continue because `Load()` disposes the bank. Moss is on level 1; stone, case, sluice, crystal, pod and cabinet are each introduced on the level that first shows them.

## Changes

- `M46/Runtime/M46AtlasBank.cs`: `CommonResources` and `WarmObstacleFrames` enumerate the obstacle families present in the idle snapshot and prepare every clip with that family prefix plus the bodies of each layer it can reveal (and the glint, spirit and rainlight bodies when pods or cabinets are present). `Prewarm` issues every missing `Resources.LoadAsync` before waiting on any of them. The pinned authored set is counted (`PinnedSprites`) and added on top of the bounded working set: `SpriteLimit` and `TextureBudget` are raised by the pinned sprites and bytes after preparation, so the 2,048-sprite / 128 MB caps still bound powers and tiles exactly as before. `Frame` and `Dispose` maintain the pinned count.
- `M47/Runtime/GameplayScreen.cs`: `WarmRendererCapacity` gains a profile-aware overload that reserves each family's authored fragments per surviving layer plus one accent, from the debris profiles already loaded for presentation; the crate formula is unchanged and the older overloads remain for existing callers. Preparation warms obstacle frames 48 per frame (`ObstacleWarmBatch`), which keeps a four-family board of about 1,860 authored frames under 40 preparation frames. The `VerificationSkipCratePreparation` switch keeps its name and now gates every family.
- `Verification/Editor/CrateBurstVerification.cs`: every replay row records `playbackObstacleCreates` and the After phase requires it to be zero; the reserve check uses the profile-aware capacity; a per-family sweep (stone, moss, case, gate, crystal, pod, cabinet, pail) asserts that level preparation lists every clip page, that pinned frames sit outside the working-set cap, and that every authored frame of every clip is served after the idle budgets are exhausted without a sprite creation or a synchronous load.

Three existing files change; nothing else in `Assets` is touched. Exact diff: `git show` of this checkpoint's commit.

## Native verification

`Verification/Run-CrateBurst.ps1` (After, NativePlay, Warmup, Checks) exits zero at every stage.

| Stage | Result | Checkpoint 44 |
| --- | --- | ---: |
| Native replay After (levels 12/23/26/42/49 × Double Orb, Orb/Rocket, rocket chain) | 3,720 checks; turn, final-snapshot and full pose signatures identical to the checkpoint-44 baseline; `playbackObstacleCreates` 0 and `synchronousLoads` 0 in all 15 rows; reserve 837–1,991 covers peaks 224–778 | 78 checks |
| Prepared sprites per board | 810 (crate + jar) to 2,005 (crate + crystal + pod + cabinet) | 352–627 |
| Per-family sweep | All eight families: every clip page in `CommonResources`, every authored frame served under zero budgets with zero creations | not covered |
| Play Mode (`CrateBurstPlayVerification`, six unaccelerated `GameplayScreen` turns) | Zero renderer and crate-sprite creation; pool 837 / 1,010 / 1,254; preparation 0.83–1.79 s | pool 837 / 1,010 / 1,182; preparation 1.01–1.97 s |
| Warmup / reload / retry / cache lifecycle | 4,579 checks pass | 4,050 |
| General Editor and model checks | 530 / 530 | 530 / 530 |

Play Mode preparation moved by −0.21 s to +0.25 s per fixture; the increase is on the board that adds sluice frames (L42), the decreases are measurement noise on crate-and-jar boards. The native After preparation column rises to 150–1,280 ms because that path warms synchronously through reflection outside frames; it is not a runtime number.

The runner also rewrites `Verification/Evidence/PowerWarmup/Native_Checks.json` and `Verification/Evidence/Native/Native_Checks.json`; both are restored to their checkpoint-45 contents after copying the fresh results into `Evidence/CrateBurst`, as checkpoint 45 did.

## Remaining limits

- No Android build, installation or timing is part of this checkpoint. The fixed-origin density fixture of checkpoint 45 clears crates only; a stone, sluice or crystal variant is needed to measure first-command latency on the emulator and on physical devices. GPU cost, sustained 60 fps and physical-device certification remain open.
- Pinned texture memory per family is 2–3 MiB on Android (ASTC 6x6) and 4–20 MiB uncompressed in the Editor; a four-family board pins about 11 MiB on device. The budget rule keeps the unpinned working set at 128 MiB on top of that; release memory and compression evaluation remain open.
- Preparation cost on the densest four-family boards (for example L25: crate, stone, case, sluice) is not measured in Play Mode; the Editor sweep suggests under 40 preparation frames behind the launch wait.
- The terminal-status settlement gap (`Resolution limit`, `No legal moves`) and the launch-window pause dialog are separate defects, not addressed here.

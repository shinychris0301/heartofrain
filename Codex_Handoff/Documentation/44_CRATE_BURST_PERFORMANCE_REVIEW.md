# Crate destruction during simultaneous power-ups

22 October 2026. Source and Android deployment checkpoint 44. Unity 2022.3.62f3; live M46 presentation and M47 gameplay controller, with existing M48 model partials.

The crate-specific first-use allocation hitch is repaired and the verified development APK is installed on main LDPlayer. Damage rules, goals, refill routes, timing, fragment counts, original artwork and existing GUIDs are preserved. General command latency and sustained 60 fps remain separate open performance work.

## Cause and repair

The preceding preparation path warmed 352 common tile/particle sprite frames and reserved five renderers per rectangular board cell. It did not prepare crate clips or account for their overlapping wood fragments. Native level 26 Double Orb produces 778 sampled draw commands with only 605 prepared renderers. Sampled commands include clips that can resolve hidden; actual Android controls independently confirm renderer growth during the burst.

- `M46/Runtime/M46AtlasBank.cs`: boards containing crates preload their clip pages and lower-HP body resources. Bounded batches prepare the shared 274 crate animation frames (eight 32-frame wood loops and the 18-frame accent), plus required body sprites. The fixed crate set remains pinned until the bank is disposed so unrelated effects cannot evict it before another hit. Boards without crates skip the added preparation.
- `M46/Runtime/BoardPresentation.cs`: reserves pooled sampled-draw objects and list capacity before input, avoiding growth during a burst. Sampling and fragment trajectories are unchanged.
- `M47/Runtime/GameplayScreen.cs`: reserve capacity includes four chips per surviving crate layer, eight on final destruction, and overlapping hit accents. Preparation remains behind the existing readiness gate and runs in batches. Maximum reserve across the 50 current authored boards is 1,182 on level 42. Renderers remain reusable across reloads. The old two-argument capacity helper remains compatible with existing callers.
- One Editor-only general test now resolves the existing separated header sprites through `HomeHeaderSprites`, matching the runtime caller. Its previous direct asset lookup failed for the already-generated connector. No Home runtime or artwork changes were needed. Edit-mode test sprites use immediate cleanup.

The development-only `VerificationSkipCratePreparation` switch provides a same-APK control for sprite/draw preparation and renderer capacity: common sprite preparation and all other current gameplay code stay enabled. Both branches use the new common-resource discovery, so crate texture pages are prefetched in both; this is not an exact reproduction of every checkpoint-43 startup dependency. The control isolates the allocation changes. It is unavailable in a production build. No rewards, inventory, attempt settlement or backend code changes.

## Native verification

`Verification/Evidence/CrateBurst` contains the evidence and `Comparison.html` gallery.

- Fresh native baseline and candidate: 15 replays covering levels 12, 23, 26, 42 and 49, each with Double Orb, Orb/Rocket and a rocket chain. All raw model turns, final snapshots and complete sampled draw signatures match exactly. All 15 candidate reserves cover their sampled peaks; rendering creates no crate sprites. Seventy-eight candidate checks pass, including cache pressure and skipping preparation on crate-free boards.
- Six unaccelerated actual `GameplayScreen` Play Mode turns pass with zero renderer growth and zero crate-sprite growth. This uses isolated boards without campaign/economy callbacks.
- Existing warmup/reload/retry/property-reset/cache lifecycle suite passes 4,050 checks. General native imports, shaders and all-board model checks pass 530/530 after correcting the stale header test described above.
- Nine inspected/hash-frozen frames: two isolated native GPU effects plates; six original-size frames from a separate compressed Android visual recording; one direct main Home screenshot. Visible full wood breakup, particles, continuing refill and settled boards are retained. The recording is excluded from timing. Native plates test effects independently of the full UI and are not a pixel-equality assertion.

Native Before was collected against checkpoint-43 runtime files before modifying them; those three baseline files are retained locally with hashes matching that checkpoint. Do not overwrite this historical baseline by invoking `Before` against the optimized runtime. `Verification/Run-CrateBurst.ps1` runs the current After, Play Mode, warmup and general checks. Device runner: `Verification/Tools/run_crate_burst_device.py`.

## Android measurements

Same final cleaned APK and QA LDPlayer, normal playback speed, baseline/candidate/candidate/baseline process order. Each process executes two repetitions of three isolated fixtures: level 12 Double Orb (38 crates cleared), level 26 Double Orb (45 cleared), and level 42 Orb/Rocket (23 crate hits, 10 cleared). Twenty-four timed turns total; no capture, PNG encoding or report writes inside timed sections. Small report-presence polling is identical for all processes.

| Measurement | Baseline controls | Prepared candidate |
| --- | ---: | ---: |
| Renderers created during 12 turns | 566 | 0 |
| Crate sprites created during 12 turns | 3,288 | 0 |
| L12 p95 render elapsed CPU | 12.69 ms | 11.16 ms |
| L26 p95 render elapsed CPU | 13.39 ms | 14.20 ms |
| L42 p95 render elapsed CPU | 9.56 ms | 9.11 ms |
| Intervals above 41.7 ms / observed frames | 224 / 5,380 | 188 / 5,473 |

The allocation cause is eliminated in the measured bursts; a uniform render-CPU improvement is not established. Level 26 p95 is slightly higher. Median measured preparation increases about 0.35–0.41 seconds, depending on fixture. Preparing unused wood frames and extra renderer capacity consumes memory earlier; full-clearing turns already needed those resources. The native Editor crate-page working set is roughly 13 MiB; that counter is not an Android peak-memory budget.

The baseline's 549.57 ms worst interval coincides with a 516.71 ms first command. Candidate worst intervals still reach about 150 ms. These are not evidence that all command cost was caused by crate rendering or that this change solves every freeze. CPU sections are elapsed durations including preemption; display intervals also include GPU waits and emulator scheduling. Frame counts differ with playback progression. Android raw turns match exactly between controls and candidates, and final snapshots match native fixtures; serialized effect floats can differ between Mono/Windows and IL2CPP/ARM, so cross-platform raw effect hashes are not equated.

`Performance_Comparison.json` and the four Android reports retain raw measurements. An earlier diagnostic used the incremental APK while packaging/readback ran; it is archived locally and excluded from these results. A separate six-turn `visual_review` run passes with zero crate/renderer growth and unchanged data but is excluded from timings.

## Build and installation

ARM64 IL2CPP development build: zero errors, two existing unused-field warnings. Generated launcher packaging is cleaned; all 1,020 nonsignature entries and the signing certificate match the Unity build. ZIP CRC, 4 KiB alignment, signature and static ELF 16 KiB checks pass. PlayerSettings are restored byte-identically; all 4,644 frozen source/configuration/tool inputs match. Relative to checkpoint 43, only three existing production scripts and one Editor test change; the new scripts are opt-in verification tools. Existing artwork and metadata hashes are unchanged.

APK: `Unity/Builds/Verification/HeartOfTheRain_Development.apk`, 260,451,446 bytes, SHA256 `b01e09fbc119bc02023c87f3c56e0833086d6ef0c186a2df49999cca0a98c404`.

Main LDPlayer (`127.0.0.1:5555`) receives a replacement install without uninstall/data clearing. No active saved attempt exists before installation. Installed hash matches the artifact. Preference and campaign/economy file hashes remain identical after installation and launch. The direct Home capture retains Raindrop/Gold, 1,250 coins, 5/5 lives and Level 1. No selected runtime/fatal error signatures occur. QA also runs this APK for tests, preserves its normal data, and is stopped afterward to restore its previous running state.

The initial SDK metadata subprocess stalled; only that identified Java child was stopped, allowing normal build failure/settings restoration. The successful retry used process-local `_JAVA_OPTIONS` for repository refusal/timeouts with the existing SDK/JDK. No engine/SDK upgrade or persistent network change. Details are in `Build_Preparation.json`.

## Remaining limits

This closes crate sprite/renderer creation during the verified destruction bursts. Other power clip first-use work, command/model latency, GPU fill/driver cost, long-session memory and physical Android/iOS performance remain open. Sustained 60 fps and a full current-APK 50-level device campaign are not certified by this targeted pass. Previous service, campaign and UI evidence retains its original scope.

# Power presentation preparation and cache follow-up

21 October 2026 · Unity 2022.3.62f3 · live M46/M48 presentation, M47 controller

This continues the approved remaining performance work from review 25. Common native sprites and renderer capacity are now prepared before input. Board reloads retain and reset the renderers; validated sprite-cache hits avoid repeated native texture queries. Gameplay/model methods, artwork, asset GUIDs, level masks, replay actions and reward semantics are unchanged.

Evidence is in `Verification/Evidence/PowerWarmup`. The previous `GameplayAudit` branch retains its own APK and date. Its Match Villains v7307 recordings remain reference observations; this pass makes no new competitor or pixel-parity claim.

## Changes

- `M46/Runtime/M46AtlasBank.cs`: prepare the 352 common fragment/star frames in batches of 16 using already-required textures. Cache hits update sprite-frame and texture-LRU ownership directly. First creation still validates authored texture dimensions/rectangles; texture eviction removes its sprites and ownership. Existing 2,048-sprite/128 MiB budgets remain.
- `M47/Runtime/GameplayScreen.cs`: prepare a renderer reserve of 405/495/605 for the three authored board dimensions before initialization completes. Retain it on reload/retry; clear sprites/property blocks and force fresh transforms, material, mask, color and glow. Dense effects retain the existing growth fallback, so this is not a cap that discards artwork. Pool lifetime is the gameplay screen's lifetime.
- `Verification/FluidityDeviceProbe.cs`: opt-in development controls and preallocated frame-cost samples. Baseline disables both changes; WarmOnly enables preparation/retention; CacheOnly enables fast lookup; Candidate enables both. Default gameplay enables both; test controls are transient.
- Added native Play Mode preparation/cache-lifetime checks and branch-specific evidence tools. Historical runner reports are restored after copying fresh results into this branch.

## Controlled emulator measurements

Same APK, QA LDPlayer, unchanged fixture seed, no video/readback during timing. Each process repeats Orb+Rocket and Golden+Bomb three times. Baseline and Candidate were then repeated in reverse order: six repetitions per combo over two app processes per main control. This includes a cold first heavy command, unlike review 25's earlier natural-move-first sequence; absolute worst intervals across those different protocols are not directly comparable.

| Measurement | Baseline | Candidate |
| --- | ---: | ---: |
| Orb+Rocket p95 render CPU | 8.58ms | 6.45ms |
| Golden+Bomb p95 render CPU | 6.66ms | 4.82ms |
| Orb+Rocket new renderers during six turns | 1592 | 0 |
| Golden+Bomb new renderers during six turns | 1086 | 0 |
| Orb+Rocket intervals above41.7ms / frames | 84 /3,164 | 65 /3,178 |
| Golden+Bomb intervals above41.7ms / frames | 28 /3,255 | 9 /3,326 |
| Orb+Rocket worst interval | 283.47ms | 199.93ms |
| Golden+Bomb worst interval | 133.37ms | 116.95ms |
| Median board-reload preparation, Orb+Rocket fixtures | 0.20s | 0.58s |

Rendering CPU fell about 25% and 28% in these aggregated samples. Preparation moves some work before input and adds roughly 0.38 s to the measured reload gate. Common sprites and unused renderer capacity consume memory earlier; this is a latency/memory tradeoff, not free work.

Frame pacing remains uneven. The candidate's cold first Orb+Rocket command took 202 ms, including 156 ms in model resolution and 46 ms accepting/enqueuing presentation; that command coincides with its worst interval. Ordinary measured Update rendering is separate from that coroutine command. Later command timings and other long frames also vary. These observations identify additional work; they do not establish that every remaining stall comes from rendering or from the emulator.

WarmOnly/CacheOnly were substantially slower even in unchanged sampler work. Their full results are retained, but single-process control differences cannot establish isolated causality. The reverse-order main controls support the narrower CPU finding above. Display clocks also drift around 16.66/16.67 ms: strict 33.34/50 ms counts can change merely because a two/three-refresh interval crosses a rounded threshold. This review uses 25 ms and 41.7 ms, between refresh multiples, and retains raw samples. Stopwatch CPU-section values are elapsed durations including scheduling/preemption, not per-thread OS CPU utilization. No zero-allocation claim is made: the pinned player's thread allocation counter is unsupported; GC collection counts are separate.

## Verification

- Native Play Mode: 3,360 checks pass, covering readiness before input, common-frame identity against the original lookup, heavy-turn renderer reuse, larger-board reload, stale transform/mask/glow clearing, interrupted starting-grant/retry, cache LRU touches, active protection and eviction/recreation.
- Existing native checks pass: 174 sampler/cache checks with authored pose signatures preserved; 3,051 M70 asset/frame/replay checks; 1,173 M70R2 creation checks; 530 general checks; connected Play Mode smoke.
- Internal Android build, clean packaging, signature/alignment, portrait policy, seven runtime sheets with no duplicate reference payload, and source/GUID integrity pass. All 4,273 non-Editor player inputs are frozen; only the two runtime files and development probe differ from the preceding player manifest.
- Android: 1,705 checks,50 boards,408 actions,354 clips and 13,976 label checks pass. All 303 freshly manifested GPU frames are 900 x 1600. The optional third timed Atlas screenshot is absent; both earlier effect poses and the settled state were inspected, and stale unmanifested PNGs were excluded.
- Eight actual mixed-swap/obstacle cases and three starting-item controls pass native checks and visual inspection; actual pause-menu retry is reviewed separately from the native probe's false `retryChecked` flag. 29 selected app/flow/finale frames, five UI plates and the extra Atlas plate were inspected. Native automated coverage is distinct from visual approval; recordings are not performance benchmarks.
- Both LDPlayer instances run the final APK on normal portrait Home. Exact installed APK hashes match, and shared preference hashes are unchanged across the entire test span. This does not certify durable campaign/inventory storage.

## Final artifact and tools

APK: `Unity/Builds/Verification/HeartOfTheRain_Development.apk`; 207,201,414 bytes; SHA256 `2c9357a5ca7dc2f878dd475380ad15c1003ddea03af182f5fb1422cb2d3d3450`.

Open `Verification/Evidence/PowerWarmup/Comparison.html` for the measurements, inspected plates and scope. `Verification_Summary.json` binds current native/device/installation evidence. `Cold_Command_Review.json` records the remaining first-use command issue; `Device_Frame_Manifest_Review.json` freezes exactly the 303 manifested screenshots.

New native runner: `Unity/Assets/HeartOfTheRain/Verification/Editor/PresentationWarmupVerification.cs`. `Verification/Run-PowerWarmup.ps1` runs it plus the five existing native groups without reassigning historical reports to this APK. Branch-specific collection and plate/performance tools are under `Verification/Tools`.

## Remaining limits

Cold heavy-command latency and long frame intervals remain open; sustained 60 fps has not been established. Physical Android/iOS profiling, sensor/OS coverage, long-session stress and human balance remain pending. Durable profile/inventory, idempotent settlement and production billing/social/live services retain their existing release gates.

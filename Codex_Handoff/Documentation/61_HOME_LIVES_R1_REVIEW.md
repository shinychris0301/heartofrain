# 61 - Home Lives design R1 integration

23 October 2026. Unity 2022.3.62f3; runtime baseline M67R4. Source/Editor checkpoint. No new APK build/install. Gallery: `Verification/Evidence/HomeLivesR1/Comparison.html`.

## Request and package

The owner requested the supplied Home Lives R1 design: a brief confirmed-loss heart/minus-one, next-life countdown, Full/zero and single-refill states. Package instructions were reviewed as development context; browser fixture timing, simulated latency, source snapshots and TMP suggestions do not replace current services or authorize unrelated changes.

ZIP CRC passes; all five manifest hashes and 14 bundle/patch file pairs match. Four shared images/font are byte-identical to the live sources; only HL_Clock is new. Approved R4_Header/R3_Lives bytes, all original GUIDs and atlas slice/pivot/PPU metadata are preserved. The current hardened clarity registry is merged to 34 required sprites, rather than importing the package's older shared registry/tool. Original fallback and current profile portraits are retained; no sample portrait is imported.

## Changes and behavior

- `App/HomeLivesDesign`: asset resource, five-language live text, read-only presentation state and pooled feedback renderer. Old receipt IDs seed the session baseline; new confirmed Lost/Interrupted, single life-credit and single refill receipts produce cosmetics once. Balance differences alone never imply a loss. Stale revisions are ignored. Multi-life catch-up/full paid refills update directly, without a false +1. The existing model and profile schema are unchanged.
- `HomeLayoutEngine.cs`: existing count moves within the same ivory field, with a separate status row. Zero is red, last life amber; Full is localized. Existing square avatar/frame, wallet/connector slices, independent touch bounds and navigation geometry remain.
- `HomePage.cs`: binds the feedback presenter and cancels presentation when covered/closed. Countdown painting updates existing nodes in place; it does not rebuild Home each second. Live clock/status graphics do not intercept taps. A two-framebuffer-pixel connector underlap closes a thin join seen at 3x density; source slices and outer layout/hit geometry stay unchanged. `Slice_Audit.txt` records zero source padding; native before/after pixel samples record the repaired join.
- `PlayerProfileHost.cs`: seeds confirmed old receipts before interrupted-attempt recovery, then projects the resulting saved snapshot after recovery/regeneration. An unavailable read produces pending status, never an invented deadline. Existing explicitly transient review edits also refresh the projection; ordinary saves are not edited by presentation.
- `HomeLevelFlow.cs`: the previously unhandled Home `lives` action opens the existing current-level pre-level/refill flow. No new modal, purchase, pricing or settlement path is added.
- `HomeArtImportPolicy.cs`, two texture metadata files and clarity registry: narrowly exempt Header/Heart alongside the prior Coin exception. Header/heart now retain Box mipmaps, trilinear filtering, source-preserving RGBA32 platform overrides and quality-mip exemption. Original art, font, GUIDs, gameplay textures and project settings are unchanged. The new clock has the same reviewed sampling policy.

Countdown = ceiling of the next saved deadline minus snapshot clock plus monotonic unscaled elapsed time. Below an hour uses MM:SS and a clock; >=1 hour uses H:MM:SS without it. Missing/expired/unconfirmed time displays ellipsis. Expiry requests the existing service refresh; the header never grants a life. Existing 30-minute regeneration up to five and 500-coin full refill at zero remain authoritative. A second loss retains the running deadline. Resume still refreshes through the existing host.

Confirmed loss uses a 460 ms count response and 900 ms small heart/minus-one float. A confirmed single restoration uses a 600 ms count response, 800 ms plus-one float and four pooled gold stars. Effects run on unscaled time outside the header's clipping, do not block Home, stop when covered and obey reduced motion. Localized announcement hooks/control labels expose the result. Count and economy changes never depend on completing a coroutine.

## Verification

Native pinned Editor processes pass:

| Scope | Result |
| --- | --- |
| Import/resource and strict guard | 34 registered sprites, zero errors |
| Presentation, local transactions and UI | 3,266 checks; 168 cases; 73 framebuffer captures |
| Included file/service assertions | 40 checks: TempFlushed/Committed faults for loss, regeneration and full refill; retry/reopen de-duplication, active deadline preservation, catch-up/cap, interrupted attempt recovery |
| Existing general checks | 534/534 |
| Connected Play Mode flow | 17 checks, zero errors: exit cancel, loss acknowledgement, failed reshuffle, resolution/engine-fault release, input/resume and Home badge patching |

The visual matrix covers EN/ES/FR/DE/RU at 393x852, 320x568, 430x932, 768x1024 and 844x390, six states each. Eighteen additional English cases use 1179x2556/scale 3, 1536x2048/scale 2 and 2532x1170/scale 3. Wide windows are supplemental fixtures; app portrait-only settings remain intact. Actual glyph generation, text width, touch bounds, square avatar geometry, mipmaps, unchanged node identity and two-pixel join overlap are checked.

Loss/refill captures follow actual local receipts at gameplay timescale zero. Native tests verify delta glyphs drawn, effects inside safe area, hide/reopen without replay, reduced-motion announcements, queued hidden-Home loss, zero-life action routing, one 500-coin spend on duplicate input and no +1 for a five-life refill. All transaction files are isolated verification profiles. State snapshots are labelled fixtures; these are not natural gameplay/device or backend certification.

Ten full frames and seven exact native pixel crops are inspected. Crop source SHA, rectangle and output SHA are recorded, with every crop pixel verified equal to its source. A dedicated capture helper avoids the older screenshot helper's Home rebuild, which otherwise cancels live header feedback during capture. Full captures are untouched.

Eight existing Unity inputs change; all remaining additions are confined to the new component/resource and verification support. Pre-turn hashes preserve the earlier dirty work. Source freeze contains 4873 inputs; manifest SHA-256 `238a3d035a816469c6a93bd08b5c3f796be9375c62242688a89ab43de3fc877c`.

Run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File Verification/Run-HomeLivesR1.ps1`, then `Verification/Run-HomeLivesR1Flow.ps1`. The collector validates frozen evidence and does not execute Unity. Historical native reports are retained separately from this checkpoint's fresh copies.

## Remaining limits

No new Android/iOS build, LDPlayer or physical notch/touch/performance/memory certification. Last recorded main installation remains checkpoint 60 (`EffectBatch/Android/Main_Installation.json`, APK `50d36575...`). The existing service uses device UTC: changing wall time can still affect life grants until trusted time is connected. Monotonic header display is not a server authority or an economy-security fix.

Cosmetic queues/seen IDs are scoped to the current session. Process restart seeds durable old receipts and renders the correct balance without replaying them; an unseen old animation is not persisted. This design adds no remote life synchronization, cloud recovery or OS screen-reader provider. RGBA32/mipmap imports remain a clarity reference requiring device memory/compression evaluation. Other gameplay/performance changes in checkpoint 60 are preserved, not re-certified by this page review.

# Obstacle fall animation review

Follow-up: review23 replaces the grouped refill scheduling retained at this checkpoint with per-tile timed routes. This document and its APK/video evidence retain their historical scope. See `23_INDIVIDUAL_TILE_REFILL_REVIEW.md`.

20 October 2026, local date. Unity 2022.3.62f3, runtime M67R4 plus the preceding approved repairs/M68/M70 assets and swap-creation rule. Current evidence is `Verification/Evidence/ObstacleFall`.

## Reference and findings

The installed Match Villains 7307 was reviewed again at level 254. Two normal swaps reduced moves 22 to 20; no premium tool or pre-level booster was used. Its blue tile below a flower ceiling visibly traverses one cell, stretches slightly in flight and settles briefly. The 30fps decoded samples bound this travel at approximately 134?167ms; core-color deformation is approximately 6%, with sprite/occlusion and video-frame uncertainty. `Reference_Motion_Samples.json` records the source samples and limits. These observations measure visible presentation, not the reference app's internal physics. The different obstacle layouts do not establish pixel-for-pixel parity.

Our one-cell flight was already 141ms, within that observed range. The more material defect was that an uncapped late frame could consume an entire short fall without intermediate poses. In addition, a diagonal leg was incorrectly timed as a vertical one-cell journey despite covering a longer path. Flight had no stretching, and the 70ms settle was shorter than the visible reference treatment. The recorded baseline fails 13 of 214 targeted native checks.

## Implementation

- `M46/Runtime/BoardPlayback.cs`: use full two-axis travel distance when assigning fall duration; diagonal one-cell-side/one-cell-down travel now takes 168ms. Keep the existing vertical acceleration and terminal speed. Use a 100ms landing settle. The playback budget preserves at least four moving poses when a late frame would otherwise skip the flight, while quiet anticipation and effect-only tails keep their existing clock.
- `M46/Runtime/BoardPresentation.cs`: use that same path distance in sampling; add a 5% vertical stretch with 2.5% horizontal compression during gem/power travel. A small damped landing adjustment produces approximately 3px displacement at a 94px cell size, with modest squash. The draw ends at its exact resting position and scale.
- `M47/Runtime/GameplayScreen.cs`: pass the current phase age into the advancement rule.
- `Verification/Editor/ObstacleFallVerification.cs`, `Verification/ObstacleFallTouchProbe.cs` and verification tools: native before/after checks and opt-in Android fixture input/rendered-pose/video evidence. The Slow fixture deliberately introduces one 180ms frame stall; it is not normal gameplay or a performance benchmark.

The additional normal-match fixture confirms that breaking the lower stone with an adjacent three-match also refills correctly, without a hammer covering the movement. A second reference sequence is retained as a visual control; its plant effects/new power obscure the tile core, so it is excluded from terminal-speed fitting.

No board model, level mask, authored replay, obstacle damage, reward/inventory mutation, swap/rocket rule or artwork/GUID is changed. No new diagonal rule or portal mechanic is introduced. Consecutive model gravity waves remain separate; this repair does not claim to reproduce unknown reference scheduling internals.

## Validation

All 217 targeted native checks pass, including center/left/right obstacle gaps, exact final position/scale, full path duration, route bounds, flight deformation, late-frame pose retention, delayed starts and unchanged model/raw step serialization. The 14,100 native timing checks across all 50 boards/six standalone powers, 122 swap/creation checks, 530 general checks and connected Play Mode smoke pass. These custom native checks are distinct from physical touch and device certification.

The final Android APK passes six actual input/rendered-pose scenarios: normal match, center/left/right hammer, rocket contact and an induced 180ms stall during flight. Visible moving-pose counts are `{'Match': 5, 'Hammer': 6, 'EdgeLeft': 5, 'EdgeRight': 5, 'Rocket': 5, 'Slow': 5}`. Each scenario finishes with the expected model snapshot, move charge, goals and tile beneath the surviving upper stones. All six video frame sequences and the two selected reference details were visually inspected. The Slow case records its stall within the flight window; it is not a frame-budget measurement.

The final signed development APK is 206,975,800 bytes, SHA256 `f53f4c63486a0b4e02df2bca7957de8ef9e71481023e0664131ccfe83a083ca2`. Signature, ZIP CRC/alignment, static 16 KiB ELF segments, seven M70 runtime texture payloads without duplicate reference copies and the portrait/game manifest pass. Both LDPlayer installations are hash checked, with original preference file hashes unchanged and no uninstall/data clear. Both apps are returned to normal Home after the transient fixtures.

Open `Verification/Evidence/ObstacleFall/Comparison.html` for the reference/our-app videos, playback-speed controls and selected frame sequences. The earlier obstacle-gravity comparison links to this page. The reference layouts/obstacle types differ, and exact pixel/internal-physics parity remains unverified. Consecutive gravity waves have not been redesigned.

 Earlier full Android runs remain historical; the preceding swap APK passed 1,705 checks over 50 boards. Physical-device performance, long-session play and the established production persistence/service release gates remain open.

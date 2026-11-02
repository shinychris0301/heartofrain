# Swap and rocket creation review

20 October 2026. Runtime M67R4 with previous documented repairs and M68/M70 assets; Unity2022.3.62f3. This review addresses the owner's latest three swap/creation requests. Final Android verification is being collected in `Verification/Evidence/SwapCreation`.

## Behavior and causes

Accepted swaps already contained interpolated poses, but playback consumed uncapped `Time.deltaTime`. A synchronous accepted-turn model solve can delay the following frame enough to consume the short swap before intermediate poses reach the renderer. Rejected swaps avoid that solve and already include outward/return motion. Playback now limits catch-up advancement for the accepted swap and a match creating a power, preserving intermediate rendered poses. Normal frame advancement and gravity/power phase timing remain unchanged. This does not remove all heavy-combination CPU spikes or certify physical-device performance.

The initial match previously preferred the counter-piece ID and then the lowest cell key. When only the dragged tile formed a match, the new rocket could therefore appear at another cell of the four-line. It now prefers the dragged matching tile at its destination, then the matching counter-piece endpoint. Creation remains a model mutation. Gravity may subsequently move the new rocket normally; creation is not pinned against gravity.

For the initial swapped match, a four-line Rocket now follows the swipe axis, as requested: horizontal gesture creates power 4/H; vertical creates power 5/V. This intentionally changes the earlier line-axis recipe for player-created rockets. Cascade rockets keep their matched-line axis. Five-line Orb and other higher-priority recipes keep their priority; no Golden+Golden rule is added.

## Changed files

- `Unity/Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs`: matching endpoint preference and initial gesture-axis rocket choice.
- `Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPlayback.cs`: bounded late-frame advancement for swap/new-power phases.
- `Unity/Assets/HeartOfTheRain/M47/Runtime/GameplayScreen.cs`: consume playback time through that advancement rule.
- `Unity/Assets/HeartOfTheRain/Verification/SwapCreationFixtures.cs`, `SwapCreationTouchProbe.cs`, and `Verification/Editor/SwapCreationVerification.cs`: development-only transient fixtures, native assertions and actual Android input/rendered-pose evidence.
- `Unity/Assets/HeartOfTheRain/M48/Resources/HOTR_Playtests/Campaign_Replays.json`: legal verification actions refreshed against the approved creation rule. Only the level 21 and 50 recorded clears changed; level definitions, seeds and budgets are unchanged. Its retained historical milestone label describes the original fixture generator; the current refresh reason is in `SwapCreation/Campaign_Replay_Refresh.json`.
- Verification runner/tools, current documentation and evidence inventory.

## Validation

The recorded native before check fails the endpoint/direction assertions. After the repair, 122 targeted native Unity checks pass, covering all four directions, reversed argument order/other matching endpoint, fractional swap poses, creation atlas/cell, move charging, slow-frame presentation and five-line Orb priority. The 530 general native checks, 14,100 timing checks and connected Play Mode smoke also pass. These custom native assertions are distinct from Android gestures and human playtesting.

An initial development-only fixture used unsupported stone health 4 and raised a missing-art key error after its first gesture. The fixture now uses the supported health 3 state; no authored level or production art lookup was changed for this fixture correction.

All four real Android swipes pass with one move/turn per action. The right/left cases expose 6/7 rendered swap-phase samples and 9 creation-phase samples each; up/down expose 7/6 swap-phase samples and 7/8 creation-phase samples. All new rockets are first recorded at cell(4,4), using atlas 9/H for horizontal gestures and atlas 10/V for vertical. Actual video contact plates were visually inspected: motion, orientation and creation alignment agree with the native pose data. `Comparison.html` links the videos and retained frame sequences.

The signed development APK is 206,951,149 bytes, SHA256 `f3300f7c50184e260a77a411c97856ff22ae36faa5dfa6a24b6349e81810df5e`. ZIP CRC/alignment, static 16 KiB ELF load segments, signature, seven M70 runtime sheets with no duplicate reference sheets, and the compiled portrait/game manifest pass. A clean pinned Gradle assemble preserved 645 nonsignature entries and the signer while discarding incremental ZIP garbage.

The final APK passes **1,705 native Android regression checks**, **50 boards**, **408 actions**, and **354 effect clips**, with no failures or logged Unity exceptions. The action/check totals are lower than the preceding M70 run because the legal level 21/50 clears now require 11 fewer recorded actions, with two assertions per action. All **283 unique report-listed captures** are portrait. Representative power effects, stacked-stone break/refill and celebration-to-Home reward images were visually reviewed, alongside the four gesture sequences; the manifest does not imply individual visual inspection of every frame. The seven M70 body textures still have one loaded copy each, 2048px ASTC4x4, totaling 29,363,488 bytes in LDPlayer.

Final hash-checked installations are recorded in `MainInstance_Final_Installation.json` and `QA_Final_Installation.json`. Both instances are returned to normal app launch after the transient test fixtures. Installation uses `-r`, with no uninstall/data clear; original preference file hashes are recorded separately. No production persistence, settlement, service integration or physical-device release gate is closed by this repair.

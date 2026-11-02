# Attempt seed review — checkpoint 51

22 October 2026. Unity 2022.3.62f3. Evidence: `Verification/Evidence/DailyGift/Native_Profile_Checks.json`, `Verification/Evidence/Native/Play_Smoke.json`, `Verification/Evidence/Native/Native_Checks.json`.

Two owner decisions are recorded here. Leftover moves stay as they are: no end-of-level conversion and no per-move coin bonus. Each attempt of a level now plays with its own refill seed, derived from the durable attempt id and recorded in the attempt receipt, so a retry no longer replays the identical refill sequence while the authored opening board stays exactly as designed. Verification replays, review scenes and fixtures keep the authored `tileSeed` or their explicit replay seeds; no fixture or evidence changes.

## Decisions

| Topic | Decision (22 October 2026) |
| --- | --- |
| Leftover moves | Discarded at the win. No "sugar crush" sequence, no coin faucet. Recorded in docs 01 and 04. |
| Refill seed | `ProfileService.AttemptSeed(attemptId)`: the first 32 bits of SHA-256 over `hotr-attempt-seed-v1|<id>`, forced non-zero. Stored as `AttemptRecord.seed` at reservation; `HomeLevelFlow` passes it to `GameplayScreen.initialSeed`; `BoardModel` uses it for refills, reshuffles and Atlas. |

## Changes

- `App/Profile/Runtime/PlayerProfile.cs`: `AttemptRecord.seed` (validated 0..2³²−1), `ProfileService.AttemptSeed`, `Reserve` records the seed (a repeated reservation keeps it).
- `M47/Runtime/GameplayScreen.cs`: `initialSeed` (non-serialized; 0 keeps the authored `tileSeed`) passed to the first `Load`. Review scenes, probes and the standalone retry path still load with seed 0.
- `App/PreLevel/Runtime/HomeLevelFlow.cs`: `Launch` sets `initialSeed` from the attempt id, so the receipt and the board agree.
- Verification: a transaction case (deterministic, non-zero, distinct per attempt, rejected for an empty id, recorded and kept across repeated reservation, retry gets its own seed, authored opening board independent of the seed) and two smoke checks (first launch uses the recorded seed; the retry's differs and matches its receipt).
- Docs 01 (decisions table: leftover moves, refill seed) and 04 (resolution and LevelData paragraphs).

`PlayerRegressionSuite` reloads its connected replays with the recorded replay seed after launch, so it is unaffected.

## Native verification

| Suite | Result | Before |
| --- | --- | ---: |
| Profile transactions (`-Mode ProfileChecks`) | 10,139 checks, 22 cases, no failures | 10,132 / 21 |
| Connected Play Mode smoke (`-Mode PlaySmoke`) | 14 checks, no errors, both seed checks present | 12–13 |
| General Editor checks (`-Mode Checks`) | 533 / 533 | 533 / 533 |

## Remaining limits

- The seed is derived, not random: anyone who knows the attempt id can reproduce the refill sequence, which is the point for support replays. Exact board resume still needs the move list, not only the seed.
- Player reports now need the attempt id (the receipt) to reproduce a refill sequence; `ReleaseFaultedAttempt` already logs seed, turn and attempt id.
- No Android run.

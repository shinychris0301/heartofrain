# Terminal-status settlement review — checkpoint 47

22 October 2026. Unity 2022.3.62f3. Evidence: `Verification/Evidence/Native` (`Play_Smoke.json`, `Native_Checks.json` and their process records, refreshed by this checkpoint).

Every end state the board model can reach now settles through `HomeLevelFlow`. A failed reshuffle (`No legal moves`) is a loss with exactly one life charge and a `Lost` receipt; the resolution guard (`Resolution limit`) is logged as a diagnostic and releases the attempt without a charge; and backgrounding the app while the flow still blocks input no longer opens the legacy restart dialog. Gameplay rules, artwork, assets, saves and services are unchanged. No APK is rebuilt.

## Cause

`GameplayScreen` hands any status other than `Playing` to the HUD once playback is idle. `HomeLevelFlow.TrySettleFailure` accepted only `Out of moves`, so the two other terminal statuses the model produces — `No legal moves` after one hundred failed recolourings in `Shuffle`, and `Resolution limit` after 128 waves or 512 steps — fell through to the HUD's standalone "Out of moves / Try again" dialog. Its button called `GameplayScreen.Load(levelIndex,0,"retry")`, reloading the board inside the same screen: the durable attempt stayed `Started`, no life was charged, the starting powers already debited by `CommitStart` were not granted again, and a later win committed as an ordinary first clear. Nothing in the connected flow subscribed to `LevelLeaving`.

Separately, `OnApplicationPause` lacked the `ReviewInputBlocked` guard that `OnApplicationFocus` has. Backgrounding the app between `InitializationComplete` and `CompleteLaunch`, before `GameplaySettingsController` is attached, built the legacy "Take a breath / Restart level" dialog, whose restart used the same unsettled reload.

## Changes

- `App/PreLevel/Runtime/HomeLevelFlow.cs`: `TrySettleFailure` accepts every status that is neither `Playing` nor `Won`. `Out of moves` and `No legal moves` take the existing `EndLevelSession` → `ConfirmExit` → `ProfileService.Lose` path. `Resolution limit` takes `ReleaseFaultedAttempt`: one `Debug.LogError` naming level, seed, turn and attempt id, then `ProfileService.ReleaseFault`, the usual save-retry dialog on failure, board destruction and the pre-level reopened in retry mode. `CompleteLaunch` clears `hud.RetryPressed` so the HUD's standalone reload is unreachable in the connected flow.
- `App/Profile/Runtime/PlayerProfile.cs`: `ProfileService.ReleaseFault` moves a `Started` attempt to `Cancelled` (an existing valid state) without touching lives; starting items already spent stay spent. Idempotent on repeat.
- `M47/Runtime/GameplayHUD.cs`: `ShowResult` builds no dialog for a loss when no retry owner is wired; `ShowPause` omits the "Restart level" button in that case. Standalone review scenes, which wire `RetryPressed` in `GameplayScreen.Start`, keep both.
- `M47/Runtime/GameplayScreen.cs`: `OnApplicationPause` carries the same `Ready && !ReviewInputBlocked` guard as focus loss.
- `M46/Runtime/BoardModel.cs`: `VerificationForceStatus` (Editor/development builds only) sets one of the three terminal statuses on a playing board so the flow can be exercised without replaying a 100-recolouring shuffle or a 128-wave chain.
- `Verification/Editor/NativeVerification.cs`: a deadlock fixture proves the reshuffle status is reachable; `Verification/Editor/NativePlaySmoke.cs`: four connected-flow phases.

Seven scripts change; nothing else under `Assets` is touched.

## Native verification

| Suite | Result | Checkpoint 46 |
| --- | --- | ---: |
| General Editor checks (`-Mode Checks`) | 531 / 531. New case: a 3×3 grid with a 2×2 active corner, one colour and one crate; a rocket tap is accepted, charges one move, ends as `No legal moves` with the settled step carrying that label and a valid board; the seam rejects an ended board and any non-terminal status | 530 / 530 |
| Connected Play Mode smoke (`-Mode PlaySmoke`) | 13 checks on the transient in-memory review profile: confirmed exit also verifies the `Lost` receipt; backgrounding while input is blocked opens nothing; backgrounding during play opens the connected settings modal and closing it resumes; forced `No legal moves` charges one life, settles `Lost`, destroys the board and opens the retry pre-level with no legacy dialog; forced `Resolution limit` logs its diagnostic, charges nothing, settles `Cancelled` and reopens the pre-level | 9 checks |

The smoke's transient profile starts at five lives and ends at three; no developer save is read or written. The forced statuses are set through the verification seam, not by replaying a real deadlock or guard exhaustion inside the connected flow.

## Remaining limits

- The player sees a failed reshuffle as the retry pre-level, the same as running out of moves. An on-board "no moves left" beat and any different wording are owner decisions (gameplay review, loss feedback).
- Starting items consumed by a faulted attempt are not refunded; whether an engine fault should restore them is an economy decision for the owner.
- A real `Resolution limit` has never been observed in the authored campaign; the guard remains a diagnostic ceiling.
- The stale uncertain-tool command across attempts and the review scenes in Build Settings are separate items, not addressed here. No Android build or device run is part of this checkpoint.

# Fault release refund review — checkpoint 52

22 October 2026. Unity 2022.3.62f3. Evidence: `Verification/Evidence/DailyGift/Native_Profile_Checks.json`, `Verification/Evidence/ProfileEvents/Native_Checks.json`, `Verification/Evidence/Native/Play_Smoke.json`, `Verification/Evidence/Native/Native_Checks.json`, `Verification/Evidence/Backend/Service_Tests.json`.

Owner decision: an attempt released by the resolution guard (an engine fault, checkpoint 47) refunds the starting items it consumed. The player loses nothing to a fault: no life, no Rocket/Bomb/Orb/Golden; tools already used in the attempt stay spent because they did their work. Released attempts now carry their own `Released` state, which also closes an audit gap from checkpoint 47 where a release looked like a cancellation that never started.

## Cause of the audit gap

Checkpoint 47 stored a released attempt as `Cancelled`. The audit feed treats `Cancelled` as never started: it emits no `attempt_started` debit for it and rejects the profile outright if such an attempt has tool commands. A faulted attempt that had used a tool would therefore have made every later audit capture throw, and one without tools silently misattributed its item debit to the opening balance.

## Changes

- `App/Profile/Runtime/PlayerProfile.cs`: `Released` is a valid terminal state. `ProfileService.ReleaseFault` moves a `Started` attempt to `Released`, returns the selected starting items to stock (checked arithmetic), records `livesAfter` and is idempotent; a reservation that never started is still cancelled, not released.
- `App/Profile/Runtime/ProfileEventFeed.cs`: a `Released` attempt is a started attempt (its debit and tool events stay) plus one `attempt_released` event whose deltas are the refunded items (0 or 1 per slot, no life).
- `Backend/hotr_backend/schemas.py`: the same kind and delta rule.
- `HomeLevelFlow.ReleaseFaultedAttempt` is unchanged; the reopened pre-level refreshes stock from the profile, so the refunded items show immediately.
- Verification: a transaction case (debit two items and one tool, release, items back and tool spent, life kept, repeat is a no-op, cannot win or lose afterwards, audit shows debit/tool/release once with the exact refund deltas and reconciled opening balances, a new attempt starts normally, unknown and never-started attempts rejected); the connected smoke now expects `Released` and whole starting stock after the forced guard.

## Native verification

| Suite | Result | Before |
| --- | --- | ---: |
| Profile transactions (`-Mode ProfileChecks`) | 10,151 checks, 23 cases, no failures | 10,139 / 22 |
| Profile events (`-Mode ProfileEventChecks`) | 478 checks, 9 cases, no failures | 478 / 9 |
| Connected Play Mode smoke (`-Mode PlaySmoke`) | 14 checks, no errors; forced `Resolution limit` ends `Released` with stock 5/5/3/2 intact | 14 |
| General Editor checks (`-Mode Checks`) | 533 / 533 | 533 / 533 |
| Backend service tests | 23 / 23 | 23 / 23 |

## Remaining limits

- `ReturnHomeForReview` (review scenes only, transient profiles) still marks a started attempt `Cancelled`; it never touches a saved profile and is out of scope here.
- A real `Resolution limit` has never been observed in the authored campaign; the refund path is exercised through the verification seam.
- No Android run.

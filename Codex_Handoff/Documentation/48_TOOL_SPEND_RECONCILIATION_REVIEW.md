# Tool-spend reconciliation review — checkpoint 48

22 October 2026. Unity 2022.3.62f3. Evidence: `Verification/Evidence/DailyGift` (`Native_Profile_Checks.json`, `Native_Play_Checks.json`) and their process records under `Verification/Evidence/Native`.

An unconfirmed tool debit no longer outlives its attempt. The exactly-once reconciliation that `HomeLevelFlow.CommitTool` performed inline now lives in a small pure class, `ToolSpendReconciliation`, that is reset when each attempt begins, so a double save failure in one level can no longer silently refuse tool use, or spend under a stale command id, in the next. Gameplay rules, the durable receipt format, artwork and services are unchanged. No APK is rebuilt.

## Cause

When `ProfileService.SpendTool` threw and the confirming `Read()` threw as well, `HomeLevelFlow` stored the command id, tool and target in four fields and refused any tool input at a different target until that exact target was retried. The fields were cleared only on that retry. Starting a new attempt (`Handle("play")`), confirming an exit, finishing a win or releasing a fault did not clear them. After one such double fault followed by leaving the level, every booster use at a different cell in later attempts returned `false` (the board showed "Could not save. Please try again." with no dialog), and using the same tool at the same cell spent with the previous attempt's command id against the new attempt.

## Changes

- `App/PreLevel/Runtime/ToolSpendReconciliation.cs` (new): `BeginAttempt(id)` binds the attempt and clears any pending command; `TryCommit(service, kind, x, y, out unconfirmed)` performs the debit, confirms a thrown debit by reading the receipt, and on a second failure keeps the exact command/tool/target pending. It returns `true` when the debit is durable, `false` with `unconfirmed` when the player must retry this exact target, and `false` without it when the debit is refused (no attempt, another command pending, or the service rejected it and the read confirmed nothing was saved).
- `App/PreLevel/Runtime/HomeLevelFlow.cs`: the four fields become one `ToolSpendReconciliation`; `Handle("play")` calls `BeginAttempt` with the new attempt id; `CommitTool` delegates to `TryCommit` and keeps its existing behaviour on `unconfirmed` (block input, pause, save-error dialog whose retry replays `UseBooster` at the same target).
- `Verification/Editor/ProfileTransactionVerification.cs`: a `FaultRepository` with the same fault model as the connected probes (a commit can be saved and then lose its confirmation, after which reads fail until recovery) and one new case.

Two runtime scripts (one new) and one Editor suite change.

## Native verification

| Suite | Result | Before |
| --- | --- | ---: |
| Profile transactions (`-Mode ProfileChecks`) | 10,110 checks, 20 cases, no failures. New case: healthy debit spends once; save-then-read double fault leaves the exact command pending while the debit was in fact saved; other targets are refused with no second debit; retrying the exact target finds the saved command and debits nothing more; a second double fault left pending at the end of the attempt does not survive `BeginAttempt`; the next attempt spends normally at another cell and at the previously pending cell under a fresh command; each command is attributed to its own attempt; no attempt, no debit | 19 cases |
| Connected Daily Gift / gameplay fault probe (`-Mode DailyGiftPlay`) | 51 checks, no failures, including the existing unknown-tool-commit flow: conflicting input blocked and recovery exposed, board unchanged, debit committed despite lost confirmation, retry uses the original command without a second debit, reconciled action plays and restores input | 51 checks |

The connected probe exercises the same `HomeLevelFlow` wiring through an isolated file profile with injected faults; the new pure case is the one that covers the attempt boundary, which no earlier suite crossed.

## Remaining limits

- The player-facing message for a refused tool while a command is pending is still the board hint "Could not save. Please try again."; the save-error dialog appears only on the double fault itself. Whether the refusal should explain itself is an owner decision.
- No Android run. Review scenes in Build Settings and the life-regeneration policy remain the next items.

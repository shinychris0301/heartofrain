# Loss beat review — checkpoint 53

22 October 2026. Unity 2022.3.62f3. Evidence: `Verification/Evidence/Native/Native_Checks.json`, `Verification/Evidence/Native/Play_Smoke.json`, `Verification/Evidence/DailyGift/Native_Play_Checks.json`.

A loss now has a moment. By owner decision the connected flow shows the HUD's approved loss dialog — "Out of moves", or "No moves left" after a failed reshuffle, with "Try a new route through the obstacles." and one "Try again" button — while the loss cue plays on the still-visible board; the life is charged and the retry pre-level opens only when the player taps the button. No new art; one new string. This also closes the cut loss cue (defect D13 of the 22 October analysis). A second question, the wording of a refused tool while a save is unconfirmed, turned out to be unreachable: the save-error dialog has no close control, so the player can only retry the same target.

## Decision

| End state | Title | Settlement |
| --- | --- | --- |
| `Out of moves` | "Out of moves" (existing string) | life charged on acknowledgement, then retry pre-level |
| `No legal moves` (failed reshuffle) | "No moves left" (new string, five locales, native review pending) | same |
| `Resolution limit` (engine fault) | no dialog | released, items refunded (checkpoint 52) |
| Confirmed exit | unchanged (End Level confirmation) | life charged on confirm |

If the app is closed while the dialog is open the attempt is still `Started`, so the next launch settles it as one interrupted loss, as before.

## Changes

- `M47/Runtime/GameplayHUD.cs`: `ShowLoss(title, acknowledge)` builds the existing loss dialog, plays `level_lose` and keeps the acknowledgement; `AcknowledgeLoss()` is shared by the button and verification and leaves the board paused; `LossPending` / `LossTitle` for probes; `LossTitleFor(status)`; `ShowResult` gains the status and uses `ShowLoss` for standalone review scenes (their "Try again" still reloads in place).
- `M47/Runtime/GameplayScreen.cs`: passes the model status to `ShowResult`.
- `App/PreLevel/Runtime/HomeLevelFlow.cs`: `TrySettleFailure` shows the dialog and blocks input; `SettleLoss` (on acknowledgement) opens and confirms the `EndLevelSession` and runs the existing `ConfirmExit`, with its save-retry handling.
- `App/Localization/Data/Translations.json`, `Runtime/LocaleCatalog.cs`: "No moves left".
- Verification: the smoke's forced-reshuffle phase now asserts the dialog title and that the life and attempt are untouched until acknowledged; `PlayerRegressionSuite` (Android) acknowledges the dialog after driving a board out of moves; the general locale case covers both titles.

## Native verification

| Suite | Result | Before |
| --- | --- | ---: |
| General Editor checks (`-Mode Checks`) | 533 / 533 | 533 / 533 |
| Connected Play Mode smoke (`-Mode PlaySmoke`) | 15 checks, no errors: forced `No legal moves` shows "No moves left" with lives and attempt intact, acknowledgement charges one life and opens the retry pre-level | 14 |
| Connected Daily Gift / gameplay fault probe (`-Mode DailyGiftPlay`) | no failures; all 34 named checks pass as before (the assertion counter reads 50 against 51, one iteration of a repeated check, not a missing check) | 34 named |

`PlayerRegressionSuite` compiles with the acknowledgement step but was not run on the emulator in this checkpoint.

## Remaining limits

- The dialog is the existing approved panel; its wording and the new title await native review for es/fr/de/ru.
- The Android regression suite's updated failure phase is untested on a device until the next emulator pass.
- No on-board animation accompanies the loss beyond the dialog and cue.

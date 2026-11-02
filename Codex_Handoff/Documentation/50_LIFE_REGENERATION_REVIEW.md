# Life regeneration review — checkpoint 50

Follow-up: the owner-approved Home header countdown/feedback gap is closed by `61_HOME_LIVES_R1_REVIEW.md` (23 October). The original checkpoint results below remain historical; its device-time limitation still applies.

22 October 2026. Unity 2022.3.62f3. Evidence: `Verification/Evidence/DailyGift` (`Native_Profile_Checks.json`, `Native_Play_Checks.json`), `Verification/Evidence/ProfileEvents/Native_Checks.json`, `Verification/Evidence/Native` (`Native_Checks.json`, `Play_Smoke.json`) and `Verification/Evidence/Backend/Service_Tests.json`.

Lives now return. The owner decided on 22 October 2026: one life every 30 minutes up to five, and a full refill at zero lives for 500 coins. Both are durable profile transactions with receipts that the audit feed reconciles; the pre-level modal shows the countdown and offers the refill when affordable. Until a trusted time service exists the timer runs on device UTC, stalls if the clock moves backwards and credits lives if it jumps forward. Gameplay rules, artwork, the Home header, the shop and services are unchanged; no APK is rebuilt.

## Decision

| Rule | Value | Source |
| --- | --- | --- |
| Regeneration | one life per 1,800 s while below `maxLives` (5) | `LifeRules.RegenerationSeconds` |
| Timer start | first observation of a profile below `maxLives` (a loss itself writes nothing extra; older saves simply begin counting) | `ProfileService.RegenerateLives` |
| Refill | full refill to `maxLives` for 500 coins, only at zero lives, idempotent by key | `LifeRules.RefillCoins`, `ProfileService.RefillLives` |
| Clock | device UTC seconds; backwards movement stalls the timer, forward jumps credit | `PlayerProfileHost.Now` |
| Player-facing | pre-level Play button reads "Refill 500" (action `refill`) when affordable or "No lives", with "Next life in mm:ss" inside the button; Home header unchanged | `PreLevelLayout` |

The refill is the campaign's first coin sink. The Home header shows no countdown; adding one is a Home design change for the owner to review as a page. Non-English renderings of the four new strings await native review.

## Changes

- `App/Profile/Runtime/PlayerProfile.cs`: `LifeRules`; profile fields `livesRefillDueUnix`, `lifeCredits` (one receipt per credit occurrence, not per life) and `lifeRefills` (one receipt per paid refill), all validated; `ProfileService.RegenerateLives(now)` writes only when a life or the timer state changes; `ProfileService.RefillLives(key, now)` credits any due lives first, then requires zero lives and enough coins; `NextLifeIn` for display.
- `App/Profile/Runtime/ProfileEventFeed.cs`: audit kinds `lives_regenerated` (+lives) and `lives_refilled` (−coins, +lives), category `campaign`, level 0. Without them the inferred opening balance would exceed `maxLives` after the first credit.
- `Backend/hotr_backend/schemas.py`: the same two kinds and delta rules for untrusted diagnostic ingestion.
- `App/Profile/Runtime/PlayerProfileHost.cs`: `Now()` (with a verification override), `NextLifeIn`, `LifeDue`; `Refresh` regenerates before applying state; `Update` refreshes when a life is due while Home is visible.
- `App/PreLevel/Runtime/PreLevelSession.cs`, `PreLevelLayout.cs`, `HomeLevelFlow.cs`: view fields for the timer and refill; the modal counts down once a second at zero lives and picks up the credited life; `Handle("refill")` → `RefillLives` with a retained key so a lost save confirmation retries without a second debit; rule rejections show "Not enough coins" or "No lives remaining".
- `App/Localization/Data/Translations.json` and `Runtime/LocaleCatalog.cs`: "Refill {0}", "Next life in {0}", "Not enough coins", "Refill lives for {0} coins" in en/es/fr/de/ru.
- Verification: a transaction case (timer start, interval, cap, backwards and forward clock, receipts, audit reconciliation, refill rules and idempotency) and a general check that the pre-level layout offers the timer and refill only at zero lives and that the patterns translate in all five locales.

Nine runtime scripts, one backend module and two suites change. Profile schema version stays 1; the new fields default safely on existing saves.

## Native verification

| Suite | Result | Before |
| --- | --- | ---: |
| Profile transactions (`-Mode ProfileChecks`) | 10,132 checks, 21 cases, no failures | 10,110 / 20 |
| Profile events (`-Mode ProfileEventChecks`) | 478 checks, 9 cases, no failures, with the new kinds reconciling | 478 / 9 |
| General Editor checks (`-Mode Checks`) | 533 / 533, including the pre-level timer/refill/locale case | 532 / 532 |
| Connected Play Mode smoke (`-Mode PlaySmoke`) | 12 checks, no errors (the conditional first-start skip check did not fire this run: boot stage `Complete`) | 13 |
| Connected Daily Gift / gameplay fault probe (`-Mode DailyGiftPlay`) | 51 checks, no failures | 51 |
| Backend service tests (`Backend/tools/run_tests.py`) | 23 / 23 | 23 / 23 |

## Remaining limits

- Device time is untrusted: a player who sets the clock forward gains lives. The model is written so that swapping `PlayerProfileHost.Now` for server time needs no profile change.
- The Home header does not show the countdown; the player sees it in the pre-level. Owner decision.
- Refill is offered only at exactly zero lives, as decided; partial top-ups, team life gifts and shop life offers are not implemented.
- No Android run; the modal's zero-lives state was verified by layout geometry and locale patterns, not by device capture.

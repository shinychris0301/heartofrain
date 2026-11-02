# 137 — Review 136 fixes: app, backend and Level 17

2 November 2026. The owner approved review 136's three decisions and the fixes. Everything below is in the working tree and tested as stated. **Nothing is committed, deployed or submitted.** Build 130 stays compatible with the new backend; the Level 17 cutover is a separate, later step.

## Owner decisions, as implemented

| Decision | Implementation |
| --- | --- |
| Guest sessions never lock out | A valid device-key proof plus the current refresh token renews a session even after the 30-day idle or 90-day limit, keeping the same family and player; the 90-day limit slides on every renewal. Revoked families and devices, deleted accounts and reused tokens stay rejected. `identity.py:331-345`, `test_identity` 19 and 29 updated. On the client a terminal refusal (another device recovered the account) now stops retrying and lets Recover and Start fresh run. |
| Level 17 unblocked | Spawn cell (4,10) is open: one moss removed, a gem placed, moss goal 13→12. `C01_L017.json`, `Backend/config/levels.json`, pins and approval for the worker. The original stays in `Resources/HOTR_LegacyLevels117`, so an attempt bound to it still plays. Real engine, 200 runs × 5 play styles: 0 dead ends (was 99% following the hint), wins present. `Level17Review136Verification` 7 checks. |
| Late ad rewards | A reported completion never expires (`newads.py:147`); a completion reported up to 24 h after reservation is accepted in client-reported mode if nothing newer is open. Daily limit and cooldown still apply at claim. |

## Fixes by review 136 finding

| # | Fix | Where | Test |
| --- | --- | --- | --- |
| 3 | A tap while Home shows "Level —" waits up to 4 s for the account and opens the player's real level, never the placeholder | `HomeLevelFlow.Open/AwaitAccount` | HTTP gameplay: "Tap while the wallet is unknown opens the real current level" |
| 4 | A won board saves its moves before any network call, so a kill offline can't forfeit the win | `ServerGameBrokerOperations.Verify/SaveBrokerIntent/RunSavedBroker` | HTTP gameplay: winning move made with the broker offline, command on disk, nothing settled |
| 5, 14 | Play settles an attempt the server still holds before reserving; a pending Start for a still-Reserved attempt is dropped at launch (no life for a board never shown); a lost Reserve reply binds at launch | `ServerGameTransactions.Reserve`, `ServerGameSession.BootstrapCore` | HTTP gameplay: "Play settles an attempt the server still holds, then reserves" |
| 6 | Settings can't open while a paid tool confirms or a launch is unresolved; a confirmed tool is applied once the HUD is free; a server refusal returns to the board without spending again | `GameplayHUD.ShowPause`, `GameplayScreen.SettingsBlocked`, `HomeServerLevelFlow.ApplyCommittedTool/ServerRefusal` | HTTP gameplay: "Settings stays shut while a paid tool is confirming" |
| 7 | 400/403/404/409/422/429 on a social write are final: outbox cleared, the server's reason shown (10 new strings, five locales) | `SocialBackendClient82`, `SocialPageSession82`, pages | `ClientFixes136` social; friend HTTP case updated |
| 8 | Over Home the error dialog can be closed, names the connection, clears itself when the account loads, and restores Home before any retry; offline Exit and an unrestorable attempt have a way out | `PlayerProfileHost.ShowHomeError`, `DailyGiftPage.ShowError/Hide/Update`, `ContinueLevelFlow.AbandonUnrestorable` | HTTP gameplay: three dialog checks |
| 9 | No uvicorn concurrency limit; shedding at 256 in-flight with JSON 503 + Retry-After | `runtime136.py`, launchers | `test_review136` |
| 10 | Server-side first-come verification dispatcher; retry cap ends through the existing Fault route (no life); client waits 45 s | `replay_service.py:247-340`, `PendingWaitSeconds` | `test_review136`, scripted-worker load |
| 12, 31 | Rewarded flow: stall bound, lost close callback handled like the interstitial, Back during load cancels, honest card wording, countdown, Home plate from server time | `RewardedAdsFlow85/Client85/Shop85/Layout85` | `ClientFixes136` rewarded |
| 13 | A failed start behind the obstacle card shows the loading failure screen again | `GameplayLoadingPage.ShowFailure`, flow | reading only |
| 15 | A first presentation fault on a server attempt keeps the board instead of a mismatch exit | `GameplayStartupPreparation79`, `GameplayScreen.RecoverFirstPresentationFault` | reading only |
| 16 | Token age and server time move on by the device-clock gap after a sleep; a 401 on the wallet renews once and retries | `ServerGameSession.OnApplicationPause/FetchWallet`, `ManagedIdentitySession82.AdjustForSleep/ExpireAccess` | HTTP gameplay: simulated 901 s sleep renews |
| 17 | Stall bounds on the broker re-dispatch and polls, the Quit attempt read, reward and account waits | `ServerGameBrokerOperations`, `ServerGameTransactions`, `ServerRewardClient`, `ServerGameAccountOperations` | `ClientFixes136` |
| 18 | Refused reward intents clear on 4xx (not 401/429/attempt_active); damaged journals fall back or quarantine | `ServerRewardsCoordinator`, `ServerRewardJournal`, `ServerAttemptJournal` | `ClientFixes136` |
| 19 | Idle Home reads only the local journal; online only with a pending intent | `RewardReceiptPresenter` | `ClientFixes136` |
| 20 | A fresh command skips its second wallet read | `ResumePending(walletFresh)` | HTTP gameplay passes |
| 21–25 | Permit cached, memory rate windows, snapshot reads, FIFO writers, indexes, kick lookup, retention, one-time backfill, late listen | backend | `test_review136`; load below |
| 26 | Back on Home sends the game to the background; Teams sub-views step back | `HomePage.MoveToBackground`, `OnlineTeamsPage82.BackAction136` | `ClientFixes136` |
| 27 | Home renders every third frame after 3 s untouched | `HomePage.SaveIdlePower` | phone |
| 28, 29 | Shop and Ranks rebuild once per change; chat observes on revision or scroll change | `ShopPage`, `OnlinePlayersPage82`, `OnlineTeamsPage82` | existing suites pass |
| 30 | Reward page art released on Hide; review portraits Editor-only | design asset classes | `ClientFixes136` |
| 32 | The pre-level modal shows its busy state while an interstitial loads | `HomeLevelFlow.Handle` | reading only |
| 12 small | due-life race, unread seed on join, ZWJ/CRLF in chat (both sides) | backend, `SocialBackendClient82` | `test_review136` |

Left as rule-level, not changed: friend 24 h lockout, donated-life collection timing, Daily Gift UTC reset, team succession.

## Verification

Backend: 1,067 run, all passed, 1 skipped (opt-in real worker), 504 s, on the final sources.

| Unity 2022.3.62f3 | Result |
| --- | --- |
| `ClientFixes136Verification` (new) | 211 checks |
| `Level17Review136Verification` (new, real engine) | 7 checks, 1,000 runs |
| Real local HTTP gameplay with the new backend and worker bundle | 320 checks (306 + 14 new) |
| Real local HTTP: account, identity, rewards, expiry, friend | 59, 25, 45, 22, 48 |
| Interstitial, Startup lifecycle, Startup, Navigation, Play smoke | 98, 130, 30, 6,453, pass |
| Rewarded flow and UI, Shop checkout, Teams chat, Leaderboard parity | pass, pass, 3,530, 76,574, 689 |
| Daily Gift, Rain Cup, Wellworks play | 43, 36, 17 |
| `LeaderboardReview.Validate`, `ServerGameplay83Verification` | exit 0 (55 checks) |

Tests changed because they encoded the old rules: `LeaderboardRefresh115Http` (a 409 is final), `SocialExpiry83` (renewal proven by signed requests; a planted intent replaces the 422 one), `Social82`, `ServerRewards83`, `ServerGameplay83`, backend `test_identity` 19/29, `test_shared_clock86`, `test_actor_deadline93`, `test_newads` 25, `test_replay_contract` 15, `test_wallet` 27.

Still failing, pre-existing: `Social82Verification.RunHttp` (stale `online-player-code-input` step) and `TeamsAccess109` (capture geometry). The HTTP gameplay fixture stalled in 3 of 5 runs with the board paused and no dialog, at random actions, then passed with diagnostics added; cause unresolved, and the diagnostics stay in the test.

Local load, 16-core PC (the VPS is slower): 50 players with no think time went from about 30 successful requests/s with 45–70% refusals to 97.8/s with none; wallet read p95 at 10 players 447→52 ms; team read p95 with 20 writers 4,253→64 ms; paced 50 players, level reserve p95 223→45 ms. One worker still bounds wins: 20 simultaneous wins with a 2 s job finish 11 within the client wait (was 7); a 60 s hung job still delays those behind it.

## Deploy, in order

1. Backend: copy `Release/RuStore/WindowsVps/Deploy136.ps1` to the VPS; `-Check`, then run. Online backup, stop, 20 files, start, `/readyz` local and public; on failure it removes the `perf136_` objects and restores. Caddy and `levels.json` untouched. The database keeps schema 125; the new indexes make an older backend refuse it until removed, which the rollback does. `vk_provider.py` is left out because its working copy holds another workstream's edits.
2. App: ship a build carrying these fixes (candidate below). Build 130 keeps working against the new backend.
3. Level 17, only when players are on the new build: `CutoverLevel17.ps1` (`-Check` first) installs the catalog, the worker's level file, pins, approval and manifest hash together; build 130 then answers "Could not start" on Level 17 only.

## Device candidate

`Release/RuStore/Builds/HeartOfTheRain_Candidate136.apk` (generated, ignored by Git): versionCode 131, versionName 0.9.131, the first-moderation profile (purchases compiled out, staging backend, release signer `7257537a…`), built from `E:\.verification-cache\HOTR136\Candidate01` with `Verification/Tools/Review136/prepare_candidate136.py` and `build_candidate136.py` (zero errors, three IL2CPP advisories). It carries the whole working tree, so the other workstreams' uncommitted direct-pay, VK and Home-video work is in it too. It is a test candidate, not a submission.

Installed over build 130 on the realme RMX3938 with data kept; the on-device hash matched. Evidence: `Verification/Evidence/Review136/Phone`.

| Phone check | Result |
| --- | --- |
| Cold start to Home, 2 runs (video) | About 7.9 and 8.8 s after launch |
| Back on Home | The game goes to the launcher and relaunches where it was |
| Idle Home CPU after 10 s untouched | 22.8% of one core (33–40% on build 130) |
| Journey, Ranks, Teams, Shop, Home | All drew correctly; Shop's video card Ready; Home video plate Ready |
| Play to board, Level 3 | About 3.7 s |
| Exit through Settings | Charged one life (5→4, timer shown), Try Again offered |
| Offline tap on the level button (second build) | Nothing at 1 s, then at 3 s the dialog "The game could not reach the server. Check your connection and try again." with a Close button. Close returns to a working Home (Journey opened on the next tap). With the dialog up and the network restored, it cleared itself within about 36 s and opened the real Level 3 pre-level, not Level 1 |

Two builds were made: `c6feb369…` (4 s account wait, first pass above) and the installed `7cb984c6…` (2 s wait; the only source difference). Offline, the Shop header shows 0 coins and Journey "0 / 50 levels" while the wallet is unknown, where Home shows "—". Cosmetic, not fixed. The test account ended at Level 3, 850 coins, 4/5 lives; Wi-Fi and mobile data were restored.

## Limits

Not done: a longer client wait with a visible "verifying" state for queued wins; production and staging105 launchers lack the cached permit and skipped checks (not live); `commands` still grows (no timestamp); a replay-worker job that hangs for 60 s delays others; reward art reloads synchronously on reopen; the first-frame Shop "unavailable" flash on a first open. Deep sleep clock behaviour on a real phone is handled by the device-clock gap but not observed on a device.

# 136 — App and backend review: player inconvenience and delays

1 November 2026. Owner request: review the app and backend, excluding RuStore, real purchases and VK, for anything that could inconvenience or delay players.

**State:** review only at the time of writing; the owner then approved the decisions and the fixes, which are recorded in `137_REVIEW136_FIXES.md`. The working tree was reviewed, including docs 130–135.

## How each finding was checked

| Label | Meaning |
| --- | --- |
| Phone | Seen on the realme RMX3938 on versionCode 130, the installed build, against the live staging server over Wi-Fi |
| Engine | Run through the real `BoardModel` in the Unity Editor |
| Reproduced | Run through the in-process backend test client, or a local backend on this PC |
| Reading | Traced through the code only. Not run |

The Home video shortcut (doc 135) is in the working tree but not in the phone's build, so it was only read.

## Must fix before real players

| # | Finding | Player effect | Checked | Where |
| --- | --- | --- | --- | --- |
| 1 | Guest sessions end for good at day 90, or after 30 idle days. The absolute limit is never extended, and the old device key cannot start again | Home stuck on "Level —" with no explanation. Recovery and logout are refused because the session isn't Ready. Clearing data makes a new guest, so progress is lost unless the recovery code was saved, and nothing prompts for that. **Every player reaches this** | Reproduced (server), Reading (client) | `identity.py:25-26,234,322`; `ServerGameSession.cs:112-114`; `ServerGameAccountOperations.cs:94,131` |
| 2 | Level 17 has all nine spawn cells sealed by moss or case, so nothing refills until they break. It dead-ends with "No legal moves" | About 8–9 of 32 moves used, then the level ends. A life is charged and Continue isn't offered (Reading). **Following the game's own hints reaches it in 99% of runs** | Engine | `C01_L017.json`; `BoardModel.cs:447,492`; hint `GameplayScreen.cs:141` |
| 3 | A tap on the Play button while Home shows "Level —" opens Level 1, because the tap sends the placeholder level | A Level 3 player gets a Level 1 preview with 0 rewards. Playing it replays an old level, and losing costs a life. Happens on a normal online start | Phone | `HomePage.cs:213`; `PlayerProfileHost.cs:122`; `HomeLevelFlow.cs:56-58,63` |
| 4 | A winning board isn't saved until the wallet read succeeds. Moves stay in memory until then | Offline or on a bad network, a win shows "Could not save". If the app then dies, the next launch quits the attempt: win and reward lost, one life charged | Reading | `ServerGameBrokerOperations.cs:30,61-67`; `ServerGameSession.cs:101-103` |
| 5 | The automatic forfeit after a killed level is fire-and-forget and never retried | On a flaky reopen, Play shows "Could not start" or an endless Retry dialog until the app is force-closed | Reading | `ServerGameSession.cs:101-104`; `ServerGameTransactions.cs:46`; `HomeServerLevelFlow.cs:23-24` |
| 6 | If the gear is tapped while a paid tool is confirming, the tool isn't applied and Retry sends a new paid command | Each Retry spends another tool. The board and server then disagree, and the forced exit costs a life | Reading | `HomeServerLevelFlow.cs:113-123`; `GameplayHUD.cs:75`; `GameplayScreen.cs:164,338` |
| 7 | Any refusal of a team or friend action is treated as "unknown" and stays in the one-slot outbox | Helping a just-filled request, a full team, or an 11th chat message in a minute: all later Team and Friends actions show "An action needs checking" until the player taps Forget. The server's reason is never shown | Reproduced (server), Reading (client) | `SocialBackendClient82.cs:169,177,309-316`; `team_life110.py:209` |
| 8 | The save-error dialog is used for network failures and has only Try Again | "Your saved game could not be loaded" when only the network is down. Back and Close are ignored, it stays up after the account has loaded behind it, and offline there's no exit | Phone | `HomeLevelFlow.cs:50,64`; `DailyGiftPage.cs:39,51,55` |
| 9 | The 32-request limit answers instantly with plain-text 503, and idle keep-alive connections count toward it | 50 first requests at once through real Caddy: 19 failed at once. Any stall or restart can trip it | Reproduced (PC) | `staging_sdk126.py:404-405`; `staging105.py:513`; `production_runtime122.py:633` |
| 10 | One verification slot, no queue, and only client polls can claim it. The client gives up after about 24 s | 20 wins at once with a 2 s worker: 7 completed, 13 got the pending error. One 60 s job blocks everyone | Reproduced (scripted worker) | `replay_service.py:193-194,215-217`; `ServerGameBrokerOperations.cs:72,89,95` |

## Should fix

| # | Finding | Player effect | Checked | Where |
| --- | --- | --- | --- | --- |
| 11 | The rewarded opportunity expires 900 s after reservation, even once completed | Watched the whole ad, claim arrives late after a drop or kill: 0 coins, `ad_opportunity_closed` | Reproduced | `newads.py:250,272,305`; `config/ads.json` |
| 12 | The rewarded flow has no wall-clock limit and no guard for a lost close callback, though the interstitial has one | Shop stuck on a disabled "Please wait" with Back and the dock dead until the app is killed, if a callback is lost or the app suspends mid-request. Whether the SDK loses one is unproven | Reading | `RewardedAdsFlow85.cs:88,102`; `RewardedAdsClient85.cs:218`; `ShopPage.cs:33-42` |
| 13 | Levels 7, 10, 14, 18, 21, 28, 36: a failed start behind the obstacle card leaves a blank screen. The gear during Start can reload with the wrong seed | Blank screen until the app is killed; or a later forced exit costing a life | Reading | `HomeLevelFlow.cs:195,245`; `GameplayLoadingPage.cs:32`; `GameplayHUD.cs:108` |
| 14 | A kill during the end of loading re-sends Start and then quits the attempt | A life and the chosen boosters are charged for a board never played | Reading | `ServerGameTransactions.cs:59,77`; `ServerGameSession.cs:97-103` |
| 15 | An app-side playback or texture fault mismatches the server and costs a life, despite the no-charge intent | "Exit level?" is the only way out | Reading | `GameplayStartupPreparation79.cs:167`; `HomeServerLevelFlow.cs:135-137` |
| 16 | Token age and server time use `Stopwatch`, which likely stops in deep sleep. Wallet and gameplay have no 401 retry | After a long lock: Unavailable badges and "Could not start", up to about 14 min. **Clock behaviour unproven; USB power prevented a test** | Reading | `ManagedIdentitySession82.cs:22-26`; `ServerGameSession.cs:43,109` |
| 17 | Three broker waits and other reward and account waits lack the review 128 stall bound | After a suspend, `busy` holds, and verify, exit or start silently stop working until restart | Reading | `ServerGameBrokerOperations.cs:85,91`; `ServerGameTransactions.cs:53`; `ServerRewardsCoordinator.cs:43-60` |
| 18 | A reward intent the server permanently refuses is never cleared, and a corrupt journal has no recovery (`.bak` is never read) | Reward pages fail on every refresh, or Home stays on "—". Uncommon | Reading | `ServerRewardsCoordinator.cs:38-47`; `ServerAttemptJournal.cs:45-57` |
| 19 | Idle Home does a full wallet read every 30 s and holds the transaction gate during it | Keeps the radio awake; a Play tap can wait silently, up to 10 s on a dead network | Reading | `RewardReceiptPresenter.cs:27,40`; `ServerRewardsCoordinator.cs:27,35` |
| 20 | Every level start makes six sequential HTTPS calls, with duplicate wallet reads, behind a screen with no cancel | Measured 4 s from Play to board on good Wi-Fi. Worse on mobile | Phone (time), Reading (calls) | `ServerGameTransactions.cs:50,72` |
| 21 | Each request re-validates the runtime permit from files three times (7.8 ms, 267 `stat` calls), and a transient file error gives 503 | Capacity 32 requests/s, against 78 when checked every 5 s | Reproduced (PC) | `staging_sdk126.py:298-317`; `api.py:174-181` |
| 22 | Reads take the global write lock three times, and waiters aren't served in order | With 10 writers, read p95 reached 2.6 s; level reserve reached 10.4 s through Caddy | Reproduced (PC) | `storage.py:274-279`; `service.py:96-114` |
| 23 | The team view scans the whole `commands` table inside that lock, and several indexes are missing | At 1.5 M rows a team view takes 1.1–1.5 s and everyone waits behind it. Ranks at offset 5000 takes 1.9 s | Reproduced (grown synthetic DB) | `messaging.py:105-109`; `records.py:61-66,115-118`; `friends.py:275-276` |
| 24 | Nothing is pruned: `commands`, `credentials`, rate windows, identity tables, stored candidate jobs, worker folders | About 400 MB/day at 1,000 players (computed). Requests and restarts slow steadily | Reproduced (growth) | `service.py:114,140`; `replay_service.py:202,312` |
| 25 | Restart cost grows with the database, and the socket accepts requests before the app is ready | About 59 s after `listen()` at 50k players (computed from measured parts); clients time out rather than being refused | Reproduced (parts) | `staging_sdk126.py:338-395`; `sdk_schema125.py:32-33` |
| 26 | Android Back does nothing on Home, and from a Teams sub-view it skips to Home | Back seems broken. Sub-pages elsewhere return correctly | Phone (Home), Reading (Teams) | `HomePage.cs:241`; `OnlineTeamsPage82.cs:178` |
| 27 | Pages keep rendering at 62 fps while idle. Home appears static | 33–40% of one core on Home or Teams with nothing happening: battery and heat | Phone | `Application.targetFrameRate` since review 128 |
| 28 | Shop rebuilds about five times per open, and Ranks seven, with player rows dead until the third read | Shop tap to page 337–370 ms every time, against 15–50 ms for Home and Teams. A swipe or tap in that window can be lost | Phone (time), Reading (rebuilds) | `ShopPage.cs:87-93,130`; `OnlinePlayersPage82.cs:65-119` |
| 29 | Chat serializes and re-parses the message page about twice per frame while open | Likely GC stalls and battery drain. Size unmeasured | Reading | `OnlineTeamsPage82.cs:527,530` |
| 30 | Reward page art is kept after closing, Rain Cup pulls in all three sets, and unused portraits are referenced | About 57 MB held (estimate). Memory held steady at 647 MB graphics across page visits, so this affects long sessions and app switches | Reading | `DailyGiftPage.cs:24,46,51`; `RainCupDesignAssets.cs` |
| 31 | Video card and Home plate wording: "Checking pending reward" on every open, "Reward not confirmed" with nothing watched, a Home plate that never expires, and "unavailable" if Shop opens before the session is ready | Misleading states. The tap itself stays safe | Reading | `RewardedShop85.cs:34-58`; `RewardedAdsLayout85.cs:38-45`; `ShopPage.cs:130-134` |
| 32 | Interstitial wait has no feedback; Play looks live for up to 3 s | Bounded; no lock survives it | Reading | `HomeLevelFlow.cs:130-139`; `PreLevelModal.cs:49` |

**Smaller or rule-level items, for owner decision:** a due life during verification rejects a valid win once, and Retry works (`replay_service.py:285-301`). Removing a friend or unblocking locks both sides out for 24 h (`friends.py:298`). Donated lives can't be collected until the request fills or 4 h pass (`team_life110.py:225`). Daily Gift resets on UTC while ads use local midnight (`service.py:182`). New team members see all old chat as unread (`messaging.py:310`). ZWJ emoji and CRLF are refused in chat (`messaging.py:21`). Teams have no succession when the owner goes (`messaging.py:228`). A global 240 challenges per minute caps the game near 3,360 online players (`identity.py:129`). Android killing the game during an app switch counts as the one loss, with no message at next launch.

## Claimed but not confirmed

The UI review traced a permanent Home lock: Try Again while the session is Busy hides the dialog, the queued open then finds Home non-interactive, and nothing restores it (`HomeLevelFlow.cs:58`; `DailyGiftPage.cs:55`). Four phone attempts with Wi-Fi coming back did not reach it; Try Again reopened the dialog each time, and Home recovered after the next Try Again. The Busy window was probably missed, so the path remains possible. Keep it with finding 8.

## Measurements

Phone, versionCode 130, good Wi-Fi, from screen video unless stated.

| Measure | Result |
| --- | --- |
| Cold start to Home | About 8.5–10 s across 3 runs: native icon about 2.5 s, title art about 6 s |
| Wallet values after Home | About 1 s more. Doc 131's 14.74 s included screenshot overhead |
| Play to board, Level 3 | About 4 s |
| Tap to page: Home, Teams | 15–51 ms |
| Tap to page: Journey, Ranks | 100 ms; first Ranks 285 ms |
| Tap to page: Shop | 337–370 ms, every open |
| Tap to page, first open: Daily Gift, Wellworks, Rain Cup | 424, 387, 219 ms |
| Back from sub-pages | Works. Not timed precisely, because a key press leaves no touch mark on video |
| Memory | 647 MB graphics, 851–899 MB total, stable over two rounds of pages |
| Idle | 62 fps; 33–40% of one core |
| Idle Wi-Fi, one clean 2-minute window | Phone total 530 KB down, 300 KB up, against 109 and 97 with the game stopped. Not per-app; a second window was contaminated by another app |
| Offline in a level | A move works locally. After backgrounding, the game returns paused on Settings with the attempt kept |
| Failures in the live logs | No `HOTR network` failures in the one cold start and the level start whose streamed logs were read; no exceptions in that cold start. The logs of the other two cold starts were not read |

Local load test: 16-core PC, loopback, the real `staging_sdk126` runtime and uvicorn options, scripted replay worker, Python 3.12 (the VPS runs 3.14). The VPS is expected to be at least 2.4× slower, from one calibration point.

| p50 / p95 ms, successes only | 1 player | 10 players | 50 players |
| --- | --- | --- | --- |
| Wallet read | 40 / 48 | 256 / 447 | 1169 / 1874 (45% got 503) |
| Level reserve | 56 / 68 | 275 / 496 | 1260 / 1634 (53% got 503) |
| Chat send | 51 / 57 | 273 / 614 | 1156 / 1567 (57% got 503) |
| Leaderboard read | 40 / 54 | 269 / 554 | 1164 / 1577 (64% got 503) |

These are closed-loop runs with no think time and raised per-player limits, so they show the ceiling and not normal play. Paced at about 0.4 requests/s per player with real limits, 50 players saw level reserve at 81 / 223 ms.

**Level endings, real engine:** [LevelEndings_RealEngine.txt](../../Verification/Evidence/Review136/LevelEndings_RealEngine.txt). All 50 levels ran 40 times under five policies; no level other than 17 reached "No legal moves", and there were no engine faults or resolution limits. Level 17, 300 runs each:

| Policy | No legal moves | Out of moves |
| --- | --- | --- |
| Game's hint move | 297 | 3 |
| Random | 201 | 99 |
| Lowest first | 172 | 128 |
| Highest first | 0 | 300 |
| Most obstacle contact | 0 | 300 |

These simple bots won no Level 17 run and are not human rates. An earlier approximate Python simulation by the review did find wins under obstacle-first play.

## Regression baseline on this tree

Backend 962 run, 961 passed, 1 skipped (the opt-in real worker). Unity 2022.3.62f3: Interstitial 98, Startup lifecycle 130, Startup 30, Navigation 6,453, Play smoke pass. Real local HTTP gameplay with the approved worker passes 306 checks. **None of these catch the findings above.** Each fix needs a new test for its case.

## Checked and found correct

- Lives: regeneration, the cap, one charge per loss, free cancel of a reservation.
- No server-side attempt expiry, so a long level or a suspended phone can't time out.
- Wallet, reward and ad replays can't pay twice. Ad limits of 400 coins, 3 per local day and 600 s hold, including time-zone changes.
- All 50 levels: goal counts match pieces, palettes and footprints are valid, server hashes and move counts match the client.
- Interstitial: every path ends, and it runs before Reserve, so no life is at stake. A stuck SDK screen remains the known doc 128 issue.
- Every live `UnityWebRequest` has a timeout. Failed-start backoff works. Late replies are discarded. Chat and Ranks page at 8, so they need no virtualization.
- Online backup of 811 MB: wallet p95 unchanged at 28–29 ms. No 502s from Caddy in about 1,700 requests.

## Not tested

Mobile data or a slow network (Wi-Fi only), other phones or tablets, a real ad unit, deep sleep, the Home video shortcut on a device, level wins made in this review, a human playing Level 17, and the live server under load.

## Test effects on the account

Phone staging account: Level 3 was started, two moves were made, and it was exited, so lives went 5→4. Coins stayed 850. No ad was shown. Testing stopped when the phone appeared to be in use by someone else.

# 128 — App/backend end-to-end review, fixes and phone test

31 October 2026. Requested by the owner: review app/backend communication, frozen obstacle fragments, lag, screen delays and loading; fix what was found; build, install and test on the phone.

**State:** the fixed APK is installed on the realme, and the backend and Caddy fixes went live on the VPS at 21:50 UTC on 31 October through `Deploy128.ps1`. Rollback backup: `C:\ProgramData\HeartOfTheRain\Review128Backup\20261031215047`. Production remains false.

## Findings that changed the diagnosis

- **The server is healthy.** Public `/healthz` and `/readyz` pass. Loopback `/readyz` measured 31/33/121 ms (min/median/max of 20, idle). That request rolls back, so commit cost is unmeasured.
- **PC and emulator timeouts are not a server fault.** Through this PC's Astrill VPN, HTTPS to the API times out; bound to Ethernet (`curl --interface 192.168.2.109`) it succeeds. The emulator was not retested.
- **The phone reaches the live server,** before and after the fixes.
- **Memory is first-order.** Installed 127 used 1,038 MB PSS, 759 MB graphics, on a 2.86 GB phone.
- **The 1/30 s cap note in older docs is out of date.** Since checkpoint 67 it applies only to frames above 100 ms during falls. Fragment sprites were not the cause of this freeze: they are prepared and pinned. All effects share `GameplayScreen.clock`.
- **RuStore's server does not recognise the app.** The availability result is `RuStorePaymentNetworkException` with `code=4000002`, `message=Application not found`, so the request reaches RuStore and is answered. It is not a certificate fault: the SDK's `CompositeX509TrustManagerApi24` error is the system check failing before the SDK's bundled Russian CA check, and `api-m.rustore.ru`'s real chain verifies against the three CAs bundled in the APK (TLS 1.3). RuStore's sandbox page requires the first app version to pass moderation. The documented meaning of this code was not found, so moderation is the leading explanation, not a proven one. The configured Console application ID is `2063777840`.
- **The stuck ad close follows the package name, not our code.** See Ad close investigation.

## Fixed

| Area | Change |
| --- | --- |
| Token renewal | Old access token stays valid 30 s after rotation; logout, deletion and refresh reuse revoke at once. The client renews 60 s early, keeps the old token during renewal and keeps page views. |
| Rate limits | Staging reads a proxy-set verified client address from a loopback peer only. A source over its own limit stops spending the shared budget. |
| Transaction gate | Wallet reads no longer hold it. Actions wait up to 20 s instead of failing. |
| Verification | The client waits and resumes on `Pending` for about 20 s before showing an error. Unity runs below normal priority. The bundle is rehashed only if a file was added, removed or changed. A restart clears a leaked slot lease and returns its operation to Pending. |
| Late SDK confirmation | `CONFIRMED` after `CANCELLED` delivers once when no other order holds the offer. |
| VK | Records the token's owner. A saved flow is visible, resumable and cancellable; Check opens the authorization page; cancel of an intent the server never received ends it locally. |
| Stall deadlines | Identity, wallet, financial and broker waits give up after a bound across an app suspend; durable intents stay pending. |
| Reads | An unchanged clock is no longer written on every authenticated read. Account blockers are computed once a frame. Automatic chat read markers no longer use the durable outbox. |
| Failure logs | Safe transport codes and the RuStore unavailable cause only. |
| Fragments | Paid tools block input without pausing effects. The clock runs during the post-swap worker hold and behind finished-board dialogs. Stalled time is repaid at up to +50%, capped at 250 ms. |
| Stuck win | Completion follows a verification that outlasts the final cascade, at most three tries. |
| Home | A due life asks for one wallet read with 5–60 s backoff instead of rebuilding every frame. Hidden Home rebuilds once when shown; unchanged reads do not rebuild it. Play tapped during a brief wait opens afterwards. |
| Shop | Reads no longer block Back, navigation or scrolling. SDK reads have a 20 s deadline. A missing quote offers Try again. |
| Leaderboard | Loading notifications do not rebuild the page. Tabs work during reads. Global ranks load first. |
| First use | Reward pages load art off the tap frame from Home. No Moves art loads when first needed. Pages target 60 fps from launch. The native cover lifts two frames later. |
| Art | 82 textures use Android-only ASTC (4x4; 6x6 at 2048 for `TA_Background`). Estimated 263.8 MB becomes 56.7 MB. PNGs, GUIDs and other platforms are unchanged. Worst 36.9 dB, median 42.6 dB. |
| Cold start | Until the wallet answers, Home shows "Level —" and "— / 50", not Level 1 and 0 / 50. Reward badges show "…" while waiting and "Unavailable" only after a failed read; a failed read retries after 5 s, backing off to 30 s. |
| Failed start | A failed session start retries by itself at 5, 10, 20, 40 and then every 60 s, and at once when the player returns to the app. Previously nothing retried, so Home stayed on "—" until the game was restarted. Closed accounts are not retried. |

Six bugs were found only by phone testing and fixed: a false "Could not save" during a paid tool, a false "Cup unavailable" on first open, false "Unavailable" badges after a win, a Retry button labelled "Continue purchase", false Level 1 and "Unavailable" on every cold start, and Home never recovering from a failed start.

Tried and reverted: `Resources.UnloadUnusedAssets` after a level. It moved graphics 660→658 MB in the one reliable reading, and a later reading was unusable, so no benefit was shown.

## Phone test — realme RMX3938, signed sandbox APK

Installed: `Unity/Builds/Review128/HeartOfTheRain_Fixes128_Sandbox.apk` (`Build128h`), SHA256 `8a90bed4de932fecaa81b9944b72e0cfdc56093b88b7abbefc9695593450402b`, build and on-device hash identical. 18 build checks with 0 errors; 35 APK audit checks. In-place update, data kept. It is a Development sandbox build. Its private `Diagnostics127` panel covers part of the lives counter and holds a demo-ad layout probe; the panel exists only in the isolated build project. `Build128h` differs from `Build128g` only by the RuStore error detail and that probe.

The gameplay flows and frame figures below were measured on `Build128d`, against the live server, whose backend was then the older version. `Build128g` added the cold-start and failed-start fixes, and was retested for those plus the main pages.

Network-failure readings need care. The phone's log buffer is 256 KiB, so a log read after a test (`logcat -d`) can lose Unity lines once SDK logging overwrites them, and earlier "no network failures" results read that way are weak evidence. A log streamed live through a `Build128h` cold start, Home and Shop on the new backend held 374 Unity lines and no `HOTR network` failure.

| `Build128g` flow | Result |
| --- | --- |
| Normal cold start, 3 runs | Home at about 11 s after launch. "Level —" until the wallet answers about 3–5 s later, then Level 2. Badges "…", then correct within about 9 s of Home |
| Cold start with Wi-Fi and data off | Home shows "—" and Unavailable badges, with no false Level 1 |
| Network restored | Real values returned within 28 s with no touch on the phone |

| `Build128d` flow | Result |
| --- | --- |
| Home, Ranks, Teams, Shop, Journey | Fully drawn at the 1 s capture, no loading screen, no network failures. The staging Ranks board is empty, so ranked rows were not seen on the phone; they are covered by the local HTTP suite |
| Back during a Shop read | Returned to Home at once |
| Stale ad-reward check | Resolved to a clear message and an enabled Watch video |
| VK | Button enabled (was disabled in Review 127). Opens `id.vk.com`. The flow survives Android killing the game. Cancel works and re-enables the button. Login itself not tested |
| Daily Gift, Wellworks | Open within 0.4 s |
| Rain Cup | Correct at 1.6 s, no false unavailable |
| Fragments | Crate chips and gem breaks visibly in flight with a Hammer round trip following a burst |
| Level 1 win | Verified by the live server; celebration; coins 1,250→1,300; Level 2 unlocked |
| Ram, Axe, Hammer | Spend correctly through the server |
| No moves | Offer shows; paid Continue 1,300→400 coins, +5 moves, board preserved |
| Loss | Charged once, 5→4 lives with countdown |
| Teams | Join in under 0.6 s (2→3 of 50), chat history, Message enabled, Leave confirmation then leave |

The account was changed by testing: tools spent, lives lost and refilled. It also reached Level 3 with 450 coins between test runs, through a Level 2 win this testing did not make.

**Compositor frames (SurfaceFlinger timestats, Development build):**

| Run | Frames | Avg FPS | >33 ms | >100 ms | >250 ms |
| --- | --- | --- | --- | --- | --- |
| Idle board | 364 | 62 | 0 | 0 | 0 |
| Real play, no captures | 4,353 | 62 | 2 | 1 | 0 |
| Level 2 play, no captures | 4,315 | 62 | 1 | 0 | 0 |
| Busy level, no captures | 2,518 | 62 | 1 | 0 | 0 |
| Rocket then Hammer, with captures | 830 | 59 | 4 | 2 | 1 |
| Win with tools, with captures | 1,282 | 60 | 4 | 2 | 1 |

Review 87 recorded 83–100 ms intervals in the prepared probes on this phone, on an older build using a different in-game measure, so this is not a controlled before and after. Each capture run had one frame over 250 ms and screen captures are a likely contributor, not proven. One no-capture Level 2 run also had one such frame.

**Memory:** Home graphics about 600 MB, down from 759 MB; total about 865 MB, down from 1,038 MB. It still climbs: 690 MB after reward pages and 790 MB (1,099 MB total) after a long session. Android killed the game within seconds of the browser opening for VK.

## Ad close investigation

Review 127 saw a demo rewarded ad with no usable close for over 20 minutes. This was reproduced and isolated on the realme with `demo-rewarded-yandex` and SDK 8.6.0, the newest release. Controls were pressed only after the native view tree showed them visible. No creative was tapped and no live placement was used.

**The failure.** The ad's own top bar, which holds the skip and close controls, collapses to height 0 and turns `GONE` a few seconds in. The close icon later becomes visible with zero size inside that hidden bar, the video loops, and Back does nothing. Unity is paused meanwhile, so no game code runs. The view tree differs from its first frame: 51 lines against 47.

**The working flow.** With the 47-line layout the bar stays, the skip icon appears after the countdown, then an end card, then a close icon, then `OnRewarded` and `OnAdDismissed`.

| Tested on one package | Result |
| --- | --- |
| Minimal app against the same app with analytics off, location off, age restricted, consent false, all alone and together | All pass |
| Fixture manifest; `CancelLoading` after load; dropped loader; immediate `Show`; all together | All pass |
| Real provider class; real demo host with identity and HTTP; added `Status` and `Reserve`; full real flow | All pass |

| Same minimal code, only the package name changes | Result, repeated |
| --- | --- |
| `ads128fresh`, `ads128c` | Bar hidden |
| `adsmin128`, `ads128d` | Works |

The real flow also fails under `ads127demo` and `ads128fresh` at the same moment it works under `ads128bisect`. So the layout is decided per package, about half of those tried fail, and our code does not cause it. What assigns it is unproven; a server-side experiment is the likely explanation. Results held for about an hour on one phone.

**The real package.** `com.heartoftherain.game` with the release signature, through the private probe, gets the working layout and completes `OnAdShown`, `OnRewarded`, `OnAdDismissed`.

**400-coin acceptance.** Through the real flow and live staging server, under a working package: coins 1,250→1,650, one receipt, shown/rewarded/closed 1/1/1. After a restart, recover and refresh: still 1,650, one receipt, no new load, claimed today 1, cooldown counting down from under 600 s. An earlier stopped ad granted nothing on recovery.

Not covered: the backend's ledger was not read directly, the game's own Shop button with its real ad unit was not used, and early close and no-fill were not retested. A player assigned the failing layout would be stuck, and the game cannot fix that because the SDK owns the screen. Yandex needs to explain it.

Tools: `Verification/Tools/Review128/AdsComparison`. Evidence: `Verification/Evidence/Review128/Ads`.

## Evidence

Backend: 961 passed, 0 failed, 1 skipped (the opt-in real worker test), run alone on the final source. One proxy test failed only when run alongside Unity.

| Unity 2022.3.62f3 Editor suite | Result |
| --- | --- |
| General / Play smoke | 535 / pass |
| Startup lifecycle, Startup, Playback onset, Effect batch | 130, 30, 259, 340 |
| Cascade / Daily Gift / Wellworks / Rain Cup play | pass / 47–50 / 17 / 39 |
| Identity, Server capacity, No Moves | 69, 46, 4,232 |
| Navigation, Shop checkout, Rewarded flow and UI | 6,453, 3,530, pass |
| Teams chat, Leaderboard parity, Regional | 76,574, 689, 8,765 |
| Real local HTTP: identity, account, VK, Leaderboard | 25, 59, 44, 50 |
| Real local HTTP: gameplay with the approved worker | 304 |

After the last two fixes, Navigation, Startup lifecycle, Startup, Identity, Play smoke, and HTTP gameplay, account and identity were rerun and passed; the other suites last ran before them. The automatic start retry has no automated test: its evidence is the phone run above. The waiting badge has one HTTP check, and unknown progress has one layout check.

Cascade and the reward play suites need rendering, so they ran with an Editor window. Tests changed because they encoded old behaviour or stale UI: `StartupLifecycle79`, `VkSignin102Http`, `ShopCheckout86`, `test_identity` 06, `RainCupVerificationProbe`, `Regional89`, `Regional89Controlled`, `TeamsAccess109`, `Social82`.

Still failing, not resolved:
- `TeamsAccess109`: reaches 23,413 checks, then "Actual R4 background covers fixed capture canvas corners" in a visual-only capture path. A geometry check; not confirmed as predating this work.
- `Social82` HTTP: stops at `online-player-code-input`, a stale UI step from review 115. Social writes over real HTTP are partly covered; Teams join, chat and leave passed on the phone.

Key reports and comparison sheets are in `Verification/Evidence/Review128`.

## Deploy

Done. The owner ran `Release/RuStore/WindowsVps/Deploy128.ps1` in an elevated PowerShell on the VPS. It verifies each live file's hash, takes an online backup, updates Caddy, then the backend, and restores the previous state if a health check fails. The script reported 7 of 7 backend files changed and both services healthy. Its first attempt stopped before changing anything, because Windows PowerShell 5.1 made a Caddy formatting warning fatal; that was fixed and reproduced with the real binary.

Order matters if this is repeated: Caddy overwrites the client address header before a backend that trusts it runs.

Checked from outside after deployment: `/healthz`, `/readyz` and the public pages return 200; `/internal`, `/docs` and `/openapi.json` return 404; public `/readyz` took 0.36–0.42 s over 12 requests. On the phone with `Build128g`: cold start and main pages correct with no network failures; in Level 3 a move and a paid Ram verified through the server (Ram 2→1, crates 18→14, fragments in flight), 1,435 frames at 62 fps with 2 over 33 ms, and exit charged one life.

Not checked on the live server: the 30 s token grace at a real renewal, per-player rate limits under load, a server-verified win made by this test on the new backend, and the content of the new access log. These are covered by the local suites only.

Sync into the isolated Unity 6 project with `Pay01/Preparation128.json`. Before each signed build, delete `launcher/build.gradle` in both `Library/Bee/Android/Prj/IL2CPP/Gradle` and `Library/Bee/artifacts/Android/Gradle`, plus `Library/Bee/Player*-inputdata.json`. The previous build's password scrub leaves a placeholder there that Gradle reports as a wrong keystore password.

## Still open

- **RuStore availability.** The server answers `Application not found`. Needs the Console: confirm application ID `2063777840` belongs to package `com.heartoftherain.game` and that its first version has passed moderation. Then retest availability, and only then a sandbox purchase and exactly-once delivery.
- **Yandex layout.** Ask Yandex why some packages receive the layout that hides its own controls, and whether a production app can receive it. The real ad unit through the game's Shop is still untested.
- **VK login itself** needs a real VK account. The original disabled button is fixed and the flow reaches `id.vk.com`; callback and restoration after restart remain untested.
- **Real purchases** are blocked by RuStore availability.
- **Refund policy.** A real double payment or refund still freezes the wallet. A safe resolver needs a schema change plus an owner decision on who receives what.
- **Memory.** The 61 clarity-registered sprites (165.6 MB) stay lossless because their build guard requires it, and Profile/Account art still loads at Home start.
- **Booster pending indicator** needs an owner design review.
- **Grey startup frames.** The cover change is in, but no frame-by-frame recording was reviewed.
- **Account name** shows "—" until the online profile loads.
- **Cold-start waits.** Home takes about 11 s to appear on this phone and badges up to about 9 s more; they are now honest but not fast. Shop's video card says unavailable for about 1 s on first open.
- **Source state.** All results above come from the working tree, which still holds hundreds of earlier uncommitted paths. `master` alone has not been compiled.
- Main-thread journal flushes; SQLite commits on every read remain under load; `windows_vps_setup.py` still generates the old launcher.

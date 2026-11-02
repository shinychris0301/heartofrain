# Rain Cup — development practice

21 October 2026 · Unity 2022.3.62f3 · live HomeLevelFlow and durable local profile

The owner approved implementing a labelled practice event: unlock after ten first clears, manually join a 48-hour cup, one point per new level cleared during the cup, four explicitly simulated rivals, and shared ranks for equal scores. Replays and losses earn no points. Real competition stays disabled until a backend exists.

| Final rank | Approved provisional prize |
| --- | --- |
| 1 | 300 coins, one Rocket, one Bomb |
| 2 | 200 coins, one Hammer |
| 3 | 100 coins |
| 4 or 5 | 50 coins |

Prizes can be claimed once after the event ends, with no claim expiry. Stars and lives are not prize currencies. A new cup can be joined after claiming the preceding one while uncleared Chapter 1 levels remain. No event is offered at all 50 clears. Joining while an attempt is reserved/started or another cup is unclaimed is rejected. There is no entry fee or invented life regeneration.

## Implementation

`RainCupService.cs` defines rules, persisted runs, snapshot/interface, unavailable production adapter and the local development practice service. `Rules.json` contains approved thresholds, duration and prizes. Four plainly labelled simulated rivals follow a deterministic linear script to final scores 24/18/12/6; these configurable review values do not represent live players, matchmaking or adaptive competitors.

An attempt binds to its active cup when reserved. The model-win callback captures event time before visual playback. The campaign win, one eligible first-clear point and contribution receipt commit in the same profile transaction. A retry retains the original timestamp even if the deadline passes during a save error. The end is exclusive: a win at the exact end instant still progresses the campaign but earns no cup point. Duplicate win settlement cannot score again. Failed/uninitialized/interrupted/lost attempts earn no points.

Each joined cup freezes its duration, rivals, config version and prize table. Ranking uses the count of rivals with strictly more points, so ties receive the same rank and prize. Expiry freezes final standings; a backward clock cannot reopen a finished cup. Finish/claim changes and reward credit are service transactions, never animation callbacks. Overflow, compare-and-swap conflict and pre/post-commit recovery are tested. Stable command/run IDs prevent duplicate joins or payouts.

The existing version-one profile gains an additive cup journal and optional attempt contribution fields. A preceding Wellworks save without the cup field loads without rewriting or resetting its balances. Claim receipts share the existing wallet/inventories. Development and release profiles remain separate. Production selects the unavailable adapter and excludes local practice/scoring code.

`RainCupPage.cs` and `RainCupLayout.cs` use existing approved artwork, safe areas, five languages, scrolling, button feedback and Back/close. They show locked/ready, join duration, standings, prizes, active timer, final rank, claim and retry states. Simulated rivals and preview rewards are labelled explicitly. Home replaces its fixed sample timer with eligibility or the actual joined practice countdown. Timer ticks update the panel label directly; they do not rebuild the panel or read/write profile files each second. Home refreshes its badge only when its displayed minute changes. Daily Gift, Wellworks and Cup routes close each other.

## Verification

Evidence is `Verification/Evidence/RainCup`; `Verification_Summary.json` and `Comparison.html` bind final verification and reviewed native captures to their APK when complete. Earlier component galleries retain their original APK scope.

- 13,227 native Unity checks pass for rules, all five finishing prizes, old-save compatibility, join/attempt eligibility, atomic scoring, end boundaries, ties, frozen configuration, file interruption, conflict retries, overflow, optional clock failure, approved assets, text bounds and glyphs across five languages and all panel states.
- 34 connected Play Mode checks pass, including an authored level-11 win using seeded test Axe inventory, a failed win save retried after expiry with the original timestamp, point persistence before presentation, M68 celebration-to-Home, lost join/claim confirmation, shared stock and page routing. This is a staged integration test, not natural-play balance approval.
- Fresh profile, Daily Gift, Wellworks and general compatibility checks pass. Their original branch reports are restored after fresh copies are retained in this branch.
- Android fixtures opt in through an explicit marker and use isolated file repositories and fixed local time. Ordinary saves and preferences are hashed for preservation. Actual taps, restart controls, additional portrait sizes and explicit rendering review are recorded separately from native/source checks.

The final development APK is **207,769,059 bytes**, SHA-256 `c9e3928c5ae91aacaa047374550bf1f2ac532ab81c3e8039d0e52b554c1fc018`. Its **4,315 non-Editor asset/metadata inputs** are frozen and revalidated. Five existing runtime files change: profile model, profile host, HomeLevelFlow, and the two existing event presenters' navigation. Eleven player inputs/metadata are added for the three Rain Cup runtime files, rules resource and opt-in probe. Approved artwork, existing GUIDs, levels/masks and board mechanics match the preceding Wellworks build. Clean packaging preserves all 648 non-signature entry payloads and the signer; APK signature, alignment, ELF, seven power textures and portrait manifest audits pass.

All seven native suites pass: **35,000 assertions/checks total**, including the 13,227 Cup assertions and 34 connected Cup checks above, 10,099 profile checks, 51 connected Daily Gift checks, 11,046 Wellworks checks, 13 connected Wellworks checks and 530 general checks. Counts describe custom native Unity execution, including font/layout assertions, rather than 35,000 independent gameplay scenarios.

The matching APK passes **eight targeted Android cases, 51 checks and four actual taps** (Home shortcut, Join, Claim, Close). Controls cover first-place reward stock, claimed restart, active score/end-time restart, expiry while stopped, repeated claimed restart, join/claim response loss, unavailable reads and the staged level-11 win whose failed save is retried after expiry. Additional restart checks pass at **320×568** and **768×1024**, three assertions at each size, with actual drag and Android Back. Thirty-three targeted captures, six additional portrait captures and both ordinary Home captures were explicitly inspected and hash-frozen: **41 images**. Short-phone content scrolls to the primary action and footer; a fully visible tablet panel stays in place when dragged. Language captures verify rendering, not native-language editorial approval.

Both LDPlayer instances run the matching final APK after replacement installs without data clear. Ordinary profile and preference hashes match before/after installs and fixtures. Display overrides temporarily change only Unity's three documented resolution keys; restoring 900×1600 restores the complete preference-file hash. Ordinary profiles retain level one, 1,250 coins, five lives, Cup `0/10` and Wellworks `0/10`; isolated practice prizes were not credited to them. `Final_Runtime_Status.json` records both app processes present without a final relaunch being necessary. Earlier unexplained emulator exits remain undiagnosed; these observations do not certify long-session stability.

Repeat native checks with `powershell -NoProfile -ExecutionPolicy Bypass -File Verification/Run-RainCup.ps1`. Device tools are `Verification/Tools/check_rain_cup_device.py` and `check_rain_cup_profiles.py`, with an explicit serial and matching development APK. `collect_rain_cup_results.py` validates source, report, image and installation identities before generating the gallery. The general collector now selects this branch first; preceding component galleries retain their original APK scope.

## Remaining boundaries

This is local practice with untrusted device time and scripted rivals. The in-process clock and persisted observation prevent simple backward presentation/result changes; they do not provide secure time or anti-cheat protection. Invalid practice time disables event availability/scoring without blocking campaign settlement; production offline score capture/reconciliation needs a real authoritative design. No authenticated account, server schedule, matchmaking, real leaderboard, secure score validation, push notification or production reward service is implemented.

Profile backup recovery can roll back one commit; account/cloud recovery, exact board resume, life regeneration, long-lived journal archival and production economy validation remain open. Physical-device/FPS, long-session stability and native-language editorial approval remain unverified. This component does not close earlier heavy-power spikes or unexplained emulator exits, and does not claim a fresh full Android campaign regression.

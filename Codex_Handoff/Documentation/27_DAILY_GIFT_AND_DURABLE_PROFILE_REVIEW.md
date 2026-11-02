# Daily Gift and durable local gameplay

21 October 2026 · Unity 2022.3.62f3 · live M46/M48 board and HomeLevelFlow

The owner approved implementing Daily Gift first, using a development service until a backend exists. The owner also approved settling an initialized unfinished attempt as one loss on reopening: one life, once; used items remain spent. An uninitialized reservation costs nothing. Wellworks and Rain Cup remain demonstration content and require separate implementation and component review.

## Implemented behavior

The configurable seven-day review schedule is 50 coins; one Rocket; 75 coins; one Bomb; 100 coins; one Hammer; 150 coins plus one Orb. One claim is available per authority day. Missing days retains the next reward; seven claims wrap the cycle. The panel uses existing approved artwork, button feedback, safe-area layout and five languages. No new artwork, level data or power-up rules are introduced.

`App/Profile/Runtime` contains the version-one profile, atomic file repository, reward/attempt services, authority adapter, host, Daily Gift layout and presenter. Campaign progress, coins, stars, lives and all eight inventory fields share one local profile. Settings and tutorial state retain their existing preference adapters. A fresh profile starts at level one; Home's old level-18 preview never becomes saved progress. Legacy three-slot initial inventory expands into separate Rocket/Bomb counts. Previously volatile review progress has no durable record to migrate.

Writes validate balances/schema/identity, compare revisions, flush a temporary file and atomically replace the primary, retaining the last good backup. Corrupt primaries are quarantined and recovered from a validated backup; unreadable/future-version saves fail closed. A checksum detects accidental corruption and supplies no anti-cheat protection. Backup recovery can roll back one commit. File-system/power-loss and cross-device recovery require additional work; process interruption is the tested boundary.

An attempt reserves a stable identifier and level-config hash before initialization. Selected items are debited only after initialization succeeds. Tool plans validate before their persistent debit; a rejected/throwing save leaves the board, RNG and stock unchanged, including Atlas. A model win commits its outcome, first-clear reward and progression before visual playback. Celebrations present that receipt and return Home; their callbacks cannot issue another reward. Exit, normal failure and reopening use the same durable settlement. Receipt replay cannot award another first clear or charge another life.

Daily Gift first persists a claim intent and expected quantities, obtains an authority confirmation, then atomically credits the wallet/inventory and receipt. Retry recovers the original entitlement after a lost response or process restart, including a confirmed claim under an older schedule. Changed offer/confirmation quantities and stale unconfirmed days are rejected. Error states preserve retry intent and avoid a silent profile reset.

## Development authority and production boundary

The current authority is an explicitly local simulation, labelled **Preview rewards**. It has a separate ledger, simulates confirmation/retry, and uses untrusted local UTC for ordinary development play. Clock rollback cannot create a new entitlement behind its recorded day, but this is not secure time or a trusted backend. Configured quantities are provisional owner-approved review values.

Development profiles live under `Profiles/Development-v1`; release profiles use `Profiles/Player-v1`. Release compilation excludes the development authority and selects an unavailable adapter: production Daily Gift cannot claim until a real authenticated service is connected. Preview balances are not imported into release storage. No billing, account service, SDK upgrade, server deployment or real competition is included.

## Verification and evidence

Current evidence is `Verification/Evidence/DailyGift`; earlier branches retain their original APK/date scope. `Verification_Summary.json` records final APK identity, fresh native reports, Android checks and installation hashes. `Comparison.html` is the component review gallery when device verification is complete.

The final reviewed development APK is 207,489,530 bytes, SHA-256 `87a4e35845994dcaff72265ed2dbd7546eab1942684e11bb00a66641bec02920`. Its 4,293 non-Editor asset/metadata inputs are frozen. Six existing runtime files change; twenty new profile/resource/probe files and metadata are added. Approved artwork, existing GUIDs, levels/masks and the preceding presentation optimizations are preserved. Clean packaging retains every non-signature ZIP entry and the same signer.

| Current targeted evidence | Result |
| --- | --- |
| Native profile/transaction/layout/font/glyph checks | 10,099 pass; 9,780 are native font/glyph assertions across all states/locales/widths |
| Connected native Play Mode | 51 checks pass, including post-commit unreadable tool recovery with one command/debit |
| Android claim/restart/attempt/tool/win controls | Seven cases, 75 checks pass; two actual Android taps open and claim the gift |
| Additional Android portrait sizes | 320×568 and 768×1024 restart controls pass; actual panel drag and Back reviewed |
| New component/connected native visual review | 31 original captures explicitly inspected and hash-frozen |
| Existing native checks | 530 general, 3,051 M70, 1,173 M70R2, 3,359 renderer/cache lifecycle checks and connected smoke pass |
| Final APK Android regression | 1,704 checks pass across all 50 boards, 408 actions, 354 clips and 13,976 labels; 303 fresh 900×1600 captures |

Native captures exposed dark card/footer labels and long translated messages on narrow screens. The final build uses white labels on the dark wells/footer, compact claimed check marks and wrapping for explanatory/error text. The short-phone panel scrolls to its footer; a transparent viewport hit surface makes the full panel draggable. Layout compares the actual clamped scale, avoiding repeated rebuilds under a scale override.

The seven Android controls preserve ordinary profile files and preferences byte-for-byte. Display-size tests necessarily change Unity's three named `Screenmanager` preferences while the override is active; other preference keys and ordinary profiles remain unchanged. Restoring the original display also restores the complete original preference-file hash. No preference contents or player profile payloads are exported into evidence.

- Native Unity transaction checks cover file/CAS validation, explicit nullable claim serialization, pre/post-commit faults, corrupt backup recovery, future-schema rejection, attempt start/debit/settlement, all four tools, duplicate/overflow protection, seven-day/missed-day cycles, offline/rollback/tampered responses and schedule revisions.
- Connected native Play Mode covers all seven claims, shared inventories, confirmation-loss retry, level exit, natural authored level-one play, saving the win while presentation is active, and celebration-to-Home without the next-level modal.
- Android opt-in tests use isolated file repositories and fixed development time, with actual gift taps, process restart after a claim, force-stop after a started level/tool use, repeated recovery and a persisted win. They hash preferences and ordinary player-profile files to ensure fixtures leave them unchanged. Native panel images require explicit visual inspection; source/layout checks alone are not device rendering evidence.
- Existing native model, M70/M70R2, preparation and connected smoke checks are copied into this branch while historical reports are restored. Final current-APK campaign regression and installations are recorded separately; inspect their status before treating this review as complete.

The final campaign manifest contains the same 303 filenames as the preceding PowerWarmup run; all are present, hash-frozen and portrait. Six selected current campaign captures were additionally inspected: opening prologue, Home, inventory, normal failure retry and final Home rewards for levels 21 and 50. This does not claim visual inspection of all 303 frames or new physical-device frame-budget certification. The QA emulator stopped after its completed reports were collected; its restart/final installation check is separate from the passing suite, and the stop's cause is not established.

The final APK is installed and running on both LDPlayer instances (`127.0.0.1:5555` and `127.0.0.1:5557`) using replacement installs without data clear. Installed APK hashes match, preference-file hashes remain identical across each install, and both final portrait Home screens are inspected. Both ordinary profiles remain at fresh level one, 1,250 coins and five lives; the isolated test claims did not consume their Daily Gift entitlement. The QA final check follows its emulator restart.

After the QA VM boot, the main app also required a relaunch. `Final_Runtime_Status.json` records both processes present simultaneously with the final installed hashes. These successful final observations do not diagnose the earlier exits or certify long-session emulator/physical-device stability.

The `WonRestart` fixture deliberately starts its fixed test authority at day 100 after `Auto` reached day 110. Its Home badge therefore reads Unavailable under the rollback guard. Saved level two, 1,725 coins, one star and four lives are retained; this badge is not a lost-win defect. Ordinary development play uses local UTC, not that fixed fixture clock.

## Remaining work

Real authority time, authentication, request signing/transport, account/cloud recovery, production reward service and backend reconciliation remain open. Local files are not an authoritative purchase wallet. Journals are bounded and fail closed at their size limits; long-lived archival/compaction still needs design.

Exact board resume, life regeneration and monetized continues are not implemented. Persisted lives no longer reset on restart; the approved interruption policy applies until resume exists. Do not invent regeneration intervals, continues, Wellworks milestone quantities or Rain Cup scoring rules. Physical-device performance, native-language review, human balance, commerce/social/store release gates also remain open. This is a Daily Gift development review, not launch certification.

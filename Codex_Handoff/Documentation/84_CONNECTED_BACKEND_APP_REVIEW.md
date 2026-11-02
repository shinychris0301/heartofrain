# Connected backend and ordinary app integration

25 October 2026. This is the current integration workstream, following the
frozen checkpoint82 foundation and checkpoint83 gameplay verifier. The ordinary
installed QA2 APK remains81. **This document is an integration status record,
not production activation or a claim that an updated Android APK is installed.**
The final connected native candidate is frozen in `VerifiedAppWithJNI/`; compatibility
and Android compile checks are tracked separately. The earlier `VerifiedApp/`
remains historical evidence before the JNI and access-expiry corrections.

## Implemented behavior

The portable service implements managed guest identity and explicit recovery,
session revocation and account deletion, authoritative wallet/inventory,
idempotent reward claims and purchase delivery, server-owned attempts and pinned
gameplay verification. Unity selects these services only when an explicit
external server configuration exists. Missing configuration retains the existing
local factory; invalid explicit configuration fails closed. Local save balances,
completed levels and development rewards are never silently imported.

The connected social service and typed client implement:

- Exact player-code lookup, friend requests, acceptance/decline/cancellation,
  lists and removal. Public profile names are independent from local artwork.
- Friends-only direct messages and membership-checked team chat, durable command
  retries, current permission checks and owner-only receipt recovery.
- Open teams, join/leave, owner transfer, member removal and team bans.
- Reporting, bilateral blocking and restricted moderator actions. Server
  moderation tools require an explicit external operator grant; the app cannot
  grant itself moderator access.
- Private attempt/first-clear records and opt-in global/friends/team standings.
  Shared ranks derive from server-accepted completed levels, not client scores.
  Hidden, blocked and deletion-requested profiles obey current visibility rules.

The app exposes Players/global standings, Friends/Requests/Blocked lists, player-code
lookup, friend actions, direct messages, Teams, team chat, create/join/leave and
owner transfer. Kick/ban/unban and friends/team leaderboard scopes exist in the
service/client but do not yet have corresponding app controls. Profile displays
private record aggregates; a full attempt-history browser is not included.

The ordinary gameplay caller now reserves/starts attempts on the server, journals
accepted commands, verifies terminal history through the approved Unity worker,
and waits for a durable receipt before the existing M67 celebration and Home
reward reveal. Tool spending, repeated900-coin/+5 continuations and a900-coin full
refill use typed transactions. Continue/Shop retains the approved board state;
ordinary interrupted attempts retain the approved one-loss rule. Restored-board
future-command comparisons have their own native evidence.

Profile rename and personal records, Daily Gift, Wellworks and practice Rain Cup
have connected app paths. Claim results refresh the authoritative wallet before
cosmetic feedback; animation callbacks never grant rewards. Rain Cup remains the
approved practice event with explicitly simulated rivals, not real competition.
Avatar/banner/frame preferences remain local appearance settings.

Account Settings uses the approved Save Progress modal with truthful managed
guest status, explicit clipboard-only recovery backup, masked recovery entry,
sign-out, explicit account switching and double-confirm deletion. Unknown outcomes
retain protected intents; sign-out/deletion cannot silently create another guest.
Provider login/linking and automatic local/cloud account merge are separate,
unimplemented capabilities. Financial/security records may be retained; deletion
is not described as an immediate physical purge of every record.

## Frozen evidence available now

`Verification/Evidence/ServerGameplay83/` contains separate input archives and
per-suite scope statements. Reports must be read with those scopes; their check
counts are not a claim that every Android screen or every device was tested.

| Evidence | Result and boundary |
| --- | --- |
| `Backend/Verified324/Service_Tests.json` |324 executed Python/ASGI/SQLite tests, zero skips/failures/errors,192.328s;73 exact inputs archived. Includes the actual approved Windows Unity replay worker in the authenticated broker integration. Other model-fault/provider/progression controls are explicitly synthetic. |
| `VerifiedAppWithJNI/Native/ServerGameplay.json` |55 native core checks/14 cases;12 restored states,90 future commands, one actual continuation history and12 changed dictionary orders, zero counterexamples in this selected corpus. |
| `VerifiedAppWithJNI/Native/ConnectedHTTP.json` |302 checks against real managed identity/wallet/replay HTTP through ordinary Home/ProfileHost/gameplay/Profile/reward callers;27 actions, one paid tool, one continuation and one saved Shop-board restoration. Actual M67-to-Home and Daily Gift reveal observed. Final wallet450 coins/one star/four lives/eight completed; local saves/appearance unchanged. Seven actual900×1600 UGUI captures reviewed. |
| `VerifiedAppWithJNI/Native/Social82_HTTP.json` |17,896 checks/15 cases/175 layout cases and19 actual UGUI captures. Two independent signed managed guests; friend/DM/team/report/block/consent flows and protected recovery. Corrected rank glyphs, full empty-chat hint and neutral report prompt reviewed. Latest/older eight-row history, exact relationships, visible-current read acknowledgement and Blocked/Unblock are exercised; five final social captures are explicitly inspected. |
| `VerifiedAppWithJNI/Native/AccountContracts.json` |91 checks/eight cases: encrypted selector crash cuts, exact lost-ack/foreign-writer fencing, modal confirmation gates and attempt-bound recovery decisions. Synthetic managed-modal fixtures are labelled. |
| `VerifiedAppWithJNI/Native/AccountHTTP.json` |54 checks: actual ordinary Settings/Account HTTP lifecycle, rejected/corrected recovery, fresh key, second real guest with preserved remote attempt, explicit forfeit, deletion/no auto guest and explicit new guest; all12 portrait captures reviewed. Editor identities are ephemeral, not Android process-restart proof. |
| `VerifiedGatewayAndRewards/Rewards/NativeHTTP.json` |45 actual native reward-adapter HTTP checks, including lost confirmation/projection recovery and single grants. The Windows long-path temporary-file defect was repaired and its failed attempts preserved. |

The final connected freeze contains5,321 Unity inputs:155 changed/new inputs are
copied, with5,166 unchanged checkpoint81 inputs resolved by hash. The six final
suites have18,420 checks in total, with their distinct scopes retained. The sixth
suite, `VerifiedAppWithJNI/Native/SocialExpiry83_HTTP.json`, contributes22 checks: 
three local901-second access-age injections, six actual signed refresh requests,
retained player/wallet/protected intent/peer and fresh Home badge metadata. This
is deterministic expiry-path testing, not a15-minute soak or Android restart test. Twenty-five
current native captures are explicitly reviewed: all12 Account, all8 reward/Home
and five social frames; the remaining14 social frames are retained as evidence. The historical checkpoint82
foundation and checkpoint83 Windows/Android IL2CPP parity remain independently
frozen in their own evidence folders.

The first Account HTTP attempt is preserved under
`Attempts/004_account_recovery_response/`. Its proposed wrong recovery code was
noncanonical Base64URL and was rejected before a recovery request was dispatched.
The rerun uses a valid, distinct synthetic secret and explicitly checks the
confirmation screen. This failure is not evidence of a successful HTTP recovery
or a product-side401 rejection.

## Follow-up corrections verified in the final native candidate

- Ordinary Account HTTP lifecycle and all12 safe portrait captures pass. A
  recovered remote attempt stays active until explicit forfeiture; the durable
  decision is bound to its exact attempt ID. The encrypted-selector-before-journal
  crash cut asks for code entry only after loading proves no intent/session exists.
- Eight-message latest/older history, paginated friend/rank reads, exact relationship
  lookup, rendered-current read acknowledgement and Blocked/Unblock pass. Legal
  Unicode reproduces the old64KiB overflow while bounded pages fit; the transport
  cap remains unchanged. History uses explicit pages, not unbounded accumulation.
- Home badges use a read-only account/generation-bound metadata cache, with
  bounded refresh/backoff and no local grant or wallet revision. Native controls
  verify Ready to Tomorrow and7/10 to8/10 without a per-frame request loop.
- Expired social access renews through the authenticated session gateway, with
  bounded retry and same-player selection/protected-intent retention. Idle Home
  badges independently renew expired access before their read-only metadata batch.
- Both internal Android profiles initially failed because the existing JNI bridge
  required the pinned engine builtin AndroidJNI module. Adding version1.0.0 in the
  manifest and lock repairs compilation without an engine/SDK upgrade; failed
  attempt006 and the intermediate pre-expiry builds remain preserved separately.
- Seven fresh compatibility suites pass on the final source: identity, general,
  profile transactions, ordinary Play smoke, portrait, release guard and correctly
  blocked preflight. Final Android lifecycle/build acceptance is tracked below.
- The first preflight follow-up overwrote one historical81 preflight artifact due
  to an incorrect output route. Attempt005 and the historical artifact notice
  preserve this limitation; historical81 preflight is not recertified. The runner
  now copies the fresh report and restores the prior report folder.

Rejected recovery scopes are retained in encrypted storage and bounded to eight
explicit different-code attempts; exact retry remains available. This is a local
safety bound, not an advertised unlimited recovery mechanism. Team-help requests,
other demo event timers, push delivery, optional provider linking and real Cup
competition are not claimed as implemented by these social/reward pages.

## Final Android and build acceptance

Both final ordinary internal builds pass with the same5,321 source inputs and
zero input deltas. All nine compatibility suites pass, including the correctly
blocked preflight. SHA-checked engine logs retain actual native process IDs even
where the older delegated runner has a null wrapper PID.

- Development APK:328,618,824 bytes,
  `3a0c926ef8f9d2e54514ff4acc1f9e10f448e0bc171963f6988aecdff89f8602`.
- Non-development compile APK:266,189,850 bytes,
  `e32326d0f9f4ed4ada230506065dd1e27c016c0670e3b5a292f0dba414b59b11`.

These are internal development-signed artifacts, with verified ZIP CRC,
signature, alignment, ELF segments, Cyrillic label and identity Java bridge.
Native RuStore Pay/Core and its early ContentProvider remain absent. A build
report's Unity totalSize counter is not the final APK file length above.

`Android/Connected84/` preserves the separate test-package build, preparation,
exact fixture inputs, root process/cleanup report and eight raw Android reports.
All101 checks pass across PIDs3956,4136,4301,4461,4609,4763,4903 and5050 on the
Android34 emulator. Programmatic frozen ordinary Home/ProfileHost/Play callers
spend one selected Rocket and one paid Hammer, verify the actual pinned-worker
checkpoint and settle one explicit quit. Reopen preserves1,250 coins, four lives,
spent inventory and the exact wallet revision. Sign-out survives restart without
creating another guest; recovery uses a different protected device key and keeps
the wallet; deletion remains closed across restart. The separate encrypted proof
store never exports its recovery secret to evidence, clipboard or ordinary files.
Android Keystore reports both keys nonexportable and software-backed here; this
is not hardware attestation.

The host's seven completed levels are explicitly synthetic setup, not seven
verified campaign wins. This package instantiates the frozen ordinary host; it
does not establish ordinary configured startup, physical input, full device
visual acceptance, OS power-loss recovery or a store payment. The ordinary
installed app remains81. All324 ordinary external files and one preference file
match the original before hashes. Main and original QA1 remain protected; their
LDPlayer topology rows are unchanged. Only the dedicated QA2 was restarted.

Failures are retained rather than counted as passes. Attempt007 is the stalled
remote SDK listing; its retry uses the existing process-only local-toolchain
settings without changing the SDK. Attempts008?010 are external harness install-
path, Windows Python redirector and relative-path binding defects before any
Android stage. Attempt011 passed setup, then ADB device operations stalled during
restart polling. A targeted QA2 reboot restored transport; the ordinary hashes
matched the original baseline. The final successful run uses one bounded shell
read of the redacted report instead of repeated run-as/exec-out probes. This
observation does not identify an exclusive cause for the transport stall.

## Material release limitations

The exact approved replay bundle is a Windows Mono worker with Job Object
resource/process limits. Unsupported hosts fail closed. The Python API is
portable, but a Linux worker requires its own build, isolation and full parity
evidence. SQLite requires durable single-host storage and tested operations;
multi-region/PostgreSQL availability is not certified.

No HTTPS service, Console application/products, release signer or moderator team
has been provisioned. Production remains explicitly blocked. Ordinary Shop does
not yet expose a verified live checkout; the disabled SDK/receipt foundation and
isolated SDK assembly are separate from a real payment. Actual signed Android
sandbox success/cancellation/process death/duplicate delivery/bank return, then
controlled real-payment verification, remain necessary. Owner setup is in
`Release/RuStore/OWNER_SETUP.md`.

Russian legal/operator/support facts, retention policy, approved account migration,
public moderation operations, physical-device checks and existing dense-effect
performance limitations remain open. The license-required Unity splash remains.
No engine upgrade, artwork/GUID change or live-board mechanic redesign is included.

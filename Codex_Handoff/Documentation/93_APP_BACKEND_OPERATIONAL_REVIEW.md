# App and backend operational review — checkpoint 93

Review started 26 October 2026 from accepted checkpoint `89b32414` / Progress92.
The owner requested an honest accounting of unresolved errors, a broad app and
backend review with realistic operational testing, revised coin prices and a
detailed launch-information checklist. **Scoped review execution is complete,
with unresolved acceptance gates.** Passing checks, retained failures, sampled
visual reviews, diagnostic recordings and missing external acceptance are
reported separately. Historical results are not added to current-source totals.

Unity remains **2022.3.62f3**. Approved artwork, existing asset GUIDs, the 50 level
masks/budgets, M46/M48 gameplay semantics, first-time/returning routing and the
doc65 corrections remain preserved. No SDK/engine upgrade, license bypass,
production activation, local/cloud wallet import or ordinary-owner save reset is
authorized or supplied by this review.

## Answer to the owner's status question

**Not all historical errors and acceptance gaps are closed.** Checkpoints 88,
90 and 92 accepted targeted tutorial/display/background/progress repairs within
their reports. Review93 repeats the two strict Account clipboard failures and
retains unreached later account stages. Historical physical samples retain prepared
83–100 ms intervals and substantial memory use; the new quiet physical sample
still reaches **99.943 ms**, and a separate historical handoff stall remains
unattributed. Real hosted/provider flows and the broader
device/human campaign matrix have not become accepted because UI pages render
or internal APKs compile.

This review re-runs current-source checks and repairs newly reproduced defects.
It records Python/ASGI/SQLite tests, actual TCP processes, native Unity fixtures,
connected native HTTP, Android compile/static evidence and actual phone
observations as distinct scopes. It does not claim exhaustive production
simulation without the missing hosting/provider/operator inputs.

## Findings, modifications and verification plan

| Priority | Finding / requested change | Modification and required evidence | Current state |
| --- | --- | --- | --- |
| P1 | Six Shop preview prices must change from 199/699/1299/2699/4999/8999 to 99/299/699/1099/2099/4099 RUB | Update live Shop and Continue/Shop preview catalogs, proposal and disabled server deployment example; preserve coin quantities and SDK `amountLabel` checkout authority | Four focused host tests, current native checks and actual phone Shop review verify all six new prices |
| P0 | A handler can wait for a writer/provider after authentication and retain a credential whose deadline has since elapsed | Recheck the authenticated actor deadline at the actual transaction boundary using the durable high-water clock; preserve privileged worker capability and idempotent ownership | Expanded 20-case boundary regressions and final 472-test service/real-worker run pass |
| P1 | Rewarded-ad commit can use request-sampled time across midnight/expiry or writer contention | Sample trusted clock inside the relevant writer transaction; use actual commit-day quota/cooldown/opportunity deadline | Included in the final expanded 20-case boundary run; 17 explicit old-behavior failures and three positive controls are retained |
| P1 | Additional writer waits can cross Daily Gift midnight, Rain Cup expiry/join/score boundaries and natural life regeneration before a 900-coin refill | Reproduce the held-writer requests, move rule-time observations into the actual writer transaction and preserve committed receipt recovery | Narrow repair, expanded 20-case regression, Set03 operations and full 472-test final-source suite pass |
| P1 | An asynchronous missing gameplay texture can leave the resource readiness wait permanently busy | Convert resource preparation failure into the existing engine-fault release flow; preserve one settlement, no life charge, start-item refund and stale-board fencing | Actual `Resources.LoadAsync` native test passes 63 checks/four cases; its intentional missing-resource diagnostics remain retained |
| P1 evidence | Broad reused suites have fixed historical output paths | Route their output through the fresh Review93 directory while retaining assertions and historical evidence bytes | New root-only serial orchestration and source freezes; no old current-tree collector is called |
| P0 acceptance | Account clipboard failure can prevent later recovery/logout/deletion stages from executing | Rerun strict suites; preserve exact FAIL and attempted-check counts; classify only the exact observed assertion; do not treat unreached stages as passed | Current Account and AccountHttp repeat the exact clipboard FAILs; their 44 + 12 attempted checks stay separate from passing counts, as does the additional hidden non-batch 44-check repeat |
| P1 operations | Earlier in-process read tests do not exercise TCP/server restart/restore | Use disposable signed managed users, actual loopback Uvicorn processes, mixed social/reward reads/writes, lost reply, concurrency, restart and restored-snapshot startup | Final-source Set03 passes 199 checks/162 timed requests; no hosted HTTPS/capacity claim |
| P0 release | External registration/deployment/SDK/provider/signing/legal inputs remain missing | Publish concrete owner setup and explicit ordinary configured Android/provider/operations matrix | [Launch_Readiness93.md](../../Release/RuStore/Launch_Readiness93.md) prepared; no external account/domain invented |

## Price change

| Coins | Offer / proposed SKU | Approved RUB | Minor units |
| ---: | --- | ---: | ---: |
| 1,000 | `coins-1000` / `hotr_coins_1000` | 99 ₽ | 9,900 |
| 5,000 | `coins-5000` / `hotr_coins_5000` | 299 ₽ | 29,900 |
| 10,000 | `coins-10000` / `hotr_coins_10000` | 699 ₽ | 69,900 |
| 25,000 | `coins-25000` / `hotr_coins_25000` | 1,099 ₽ | 109,900 |
| 50,000 | `coins-50000` / `hotr_coins_50000` | 2,099 ₽ | 209,900 |
| 100,000 | `coins-100000` / `hotr_coins_100000` | 4,099 ₽ | 409,900 |

Quantities and all other approved economy rules are preserved. The template
remains disabled, app ID unset, and sandbox selected. These are not registered
Console products or live quotes. Configured checkout still uses the SDK's
returned formatted price and the server's catalog/order amount binding.
Arbitrary 199-RUB scripted payment fixtures remain quote-authority tests, rather
than claiming that the preview controls the provider price.

The approved table has a pricing tradeoff: two 5,000-coin packs cost 598 RUB,
less than one 10,000-coin pack at 699 RUB. These consumable offers currently have
no purchase limit or added bonus, so the 10,000 pack has worse unit value.
The requested prices remain unchanged; this is an owner-approved economy
choice to review before Console publication, not an unresolved runtime defect.

Focused evidence:
`Verification/Evidence/Review93/Pricing/FocusedTests.json`. Four host-side tests
check both catalogs, proposal, disabled backend example and registration IDs.
The retained initial environment/import failure precedes the successful command
and is not an app regression, native test or Console transaction.

## Backend boundary repairs

The request's authenticated actor capability now retains its credential deadline
and observes the same trusted clock inside downstream transactions. Waiting for
a database writer or invoice provider no longer permits an expired actor to
mutate data or recover a protected receipt. Invalid or backward clock cases fail
closed or preserve the durable high-water boundary. The server-only worker
capability stays distinct from a player credential; no client-controlled expiry
or arbitrary grant is introduced.

Ad eligibility/reservation/claim/cancel observation is transaction-bound where
required. Crossing a local midnight while waiting uses the current commit-day
quota and cooldown, and an opportunity expiring during the wait cannot credit.
The approved 400 coins, three credits per player-local day and 600-second cooldown
remain unchanged. No new time-specific Shop copy or provider verification claim
is introduced.

The additional reproduction binds all four stale timer outcomes before repair:
an old first Daily Gift claim can cross UTC midnight, a Cup can remain active
after its deadline, a late clear can still add a Cup point, and zero-life refill
can charge 900 coins even though natural regeneration became due while waiting.
The repair takes one fresh service-time snapshot inside each actual reward,
Cup, wallet and replay writer transaction; committed idempotent receipts retain
their original payload and time.

`Backend/Regressions/Final02/Service_Regressions.json` under Review93 records
**20 passing ASGI/SQLite boundary cases**. Separate in-memory old-behavior
controls produce **17 explicitly expected failures and three positive controls**,
zero errors; current source files are not reverted. The exact expected failing
test IDs are exported and checked. These establish regression sensitivity and
are not counted as passing backend tests or discarded errors. The earlier
ten-case/seven-failure supplement is retained with its original source map.

The final complete root-run backend suite passes **472 tests, zero skips,
failures or errors**, including the approved real Windows gameplay worker.
`Verification/Evidence/Review93/Backend/Final02/Service_Tests.json` and its
invocation bind **95 exact archived backend inputs**; before/after source maps
match. The earlier 462-test proof at `Backend/Final/` precedes the broader
timer repair and remains earlier-source evidence; it is not relabelled.
The prior 448-test checkpoint89 result retains its historical scope.

## Current native app execution

All **39 configured native suites** execute on one held **5,407-input Unity
map**: 34 independent Set01 suites and five connected HTTP suites.
**37 suites pass with 185,463 checks**. Strict Account and AccountHttp fail at
their exact clipboard readback assertions after **44 + 12 = 56 attempted
checks**, excluded from the passing total. Independent Set01 contributes
33 passing suites/166,152 checks; IdentityHttp, SocialHttp, ServerHttp and
PayHttp contribute four passing suites/19,311 checks.

The Account run's seven prior cases pass, while remaining actions after Copy
are not established. Connected AccountHttp likewise stops before its later
logout/recovery/deletion/fresh-guest stages. Fresh Win32 metadata permits opening
the clipboard, so the earlier Windows access-denied observation is not asserted
as this failure's cause. The exact current failures and metadata are retained in
`Verification/Evidence/Review93/NativeFailureClassification.json`; no assertion
was waived or Android clipboard defect inferred. Current internal Android
builds and physical-phone outcomes retain their separate scopes below.

[AccountClipboardAssessment.json](../../Verification/Evidence/Review93/AccountClipboardAssessment.json)
binds a read-only review of the exact current reports, logs and caller source.
The synthetic Account case writes a known valid-length string directly to
`GUIUtility.systemCopyBuffer`, bypassing the backend, and its immediate readback
is empty. This narrows that failure to the clipboard write/read boundary or host
environment; the precise Windows/Unity cause remains unproven. AccountHttp's
later false lifecycle flags are unreached coverage, not independently observed
recovery/logout/deletion defects.

The live copy method also returns optimistic success after a setter that does
not throw, and the modal uses that return value for its copied notice. Silent
copy failure can therefore produce misleading feedback where it occurs. This
is a source risk, not evidence of the same Android failure. No speculative
runtime change or assertion bypass is included.

The separate
[hidden non-batch Account invocation](../../Verification/Evidence/Review93/NonBatch/Account_11d4475b9a4a4e0cb5f599aa7723260d/Invocation.json)
then repeats the **same exact clipboard FAIL after 44 attempted checks/eight
cases**, with `actualBatchMode: 0`, one Copy dispatch and empty immediate
readback. The unchanged native test and all 5,407 source inputs are bound.
The owned Editor closes normally by `WM_CLOSE`, with exit 0, no forced cleanup,
no remaining Editor PID and no cleanup errors. Normal process exit does not
make the failed native assertions pass. Nine separate host controls check the
diagnostic helper, not app acceptance.

The failure therefore is **not confined to the batch-mode flag**. This was a
hidden launch; it does not establish visible foreground/manual or Android
clipboard behavior. Its additional **44 failed attempted checks remain
separate** from the original 39-suite aggregate and 56 failed attempts.
Next acceptance is the unchanged strict fixture in a disposable visible
foreground/manual Editor context, then explicit Copy, masked paste and full
lifecycle recovery on a disposable foreground Android identity. Recovery
secrets must remain unlogged, unrendered and outside owner account/profile data.

The connected run uses three separate disposable loopback services and the
approved real gameplay worker. Each process starts suspended and is assigned to
its owned kill-on-close job before its actual Python children execute. Cleanup
confirms stopped processes and closed actual loopback listeners. A separate
real-launcher child containment probe verifies this ownership mechanism. These
are not public hosting, real RuStore SDK/payment or ordinary configured Android
account acceptance.

The native result covers import/model/campaign definitions, profile/attempt
transactions, UI/reward pages, loading/lifetime, Continue/repeat moves, mixed
power creation/cascades, lifecycle/purchase recovery/capacity/release guards,
identity/account contracts, prices/ads, regional/provider fixtures, display,
progress, tutorial gestures, Russian defaults and snapshot invariants. It does
not establish normal-play smoothness, every human campaign outcome or live
services merely because assertions pass.

Root explicitly inspected **eight selected original native renders**:
`Verification/Evidence/Review93/NativeVisualReview.json`. They include the six
new RUB prices, compact Continue, Rain Cup progress, small-screen Daily Gift
initial/scrolled states, zero-progress Wellworks, the deliberately bottom-
scrolled Profile fixture and approved Orb loading design. The legacy
`Connected_Offer_EN.png` filename actually contains Russian in this run;
it is not English-language acceptance. The small Profile header/Close being
above the viewport is intentional outer-page scrolling, with a separate source
assessment. Not every matrix image was manually reviewed, and these images
are Editor offscreen renders rather than actual Android OS screenshots.

## Current internal Android builds

Both SDK-free IL2CPP ARM64 builds pass on the same **5,407-input** map after
exact settings restoration. Development APK SHA256 starts `e4bb5d8c`; the
non-development ReleaseCompile APK starts `a2d2718e`. Their full hashes, original
native build reports, owned-process cleanup, logs and before/after source maps
are bound by
`Verification/Evidence/Review93/Builds/ad6ac22c823a497d950bfc2036179176/Review93_Builds.json`.

`Verification/Evidence/Review93/Android/APK_Profile.json` passes static checks
for both exact APKs: ZIP CRC, development signature verification, alignment,
16 KiB ELF load segments, package/manifest/DEX and expected SDK-free profile.
The identity class is present; native payment/advertising SDKs are absent.
These are internal verification artifacts, not owner-signed configured
production builds or actual provider acceptance.

The frozen wrapper's descriptive scope retains the legacy word `Current92`.
Its current93 status, paths, helper hashes and exact current source/APK bindings
are verified independently. The retained descriptor is not a claim of old-source
certification; no receipt or runner was rewritten to hide it.

## Current physical-phone regression

The current development APK is replacement-installed on the same authorized
720×1600 owner phone, extending the accepted five-link history with a sixth
verified link. The ordinary owner profile remains revision **36**, **1,700
coins**, **five lives**, current **Level 9** and **eight completed levels**, with
no active attempt. Profile files, preferences and progression match before,
after and after normal relaunch; no pending marker remains.

`Phone/Device01/Regression/72260281e8d54fe7b3402b2e87bd6190/Invocation.json`
under Review93 passes **1,716 native Android checks across 50 authored boards,
408 programmatic actions and 354 clips**, with fresh resource/atlas proof.
The fixture uses transient memory-profile/settings state and does not spend
the ordinary owner's resources. It is not 50 human level wins, physical swipe
acceptance, ordinary saved progression, hosted/provider testing or proof of
whole-game smoothness.

Root inspected four retained original Unity camera renders on the phone:
gameplay HUD, a rocket, stacked-obstacle refill and temporary chapter-complete
Home. Their hash-bound `RootVisualReview.json` scopes each still explicitly.
They are not Android OS screenshots, a review of every clip, or frame-sequence
timing acceptance. The temporary completed-chapter values in a fixture render
are not the ordinary owner's save.

The separate
[ordinary phone visual review](../../Verification/Evidence/Review93/Phone/Device01/RootVisualReview.json)
accepts **11 scoped cases using 15 explicitly inspected original 720×1600
Android OS screenshots**: Home and normal relaunch; Shop with all six new coin
prices across scrolled rows; Profile avatar/Stats; local demo Teams; Settings;
local guest Account; Rain Cup at 8/10; Daily Gift; Wellworks at 8/50; Journey;
and the example Global Players leaderboard. These views show contained controls,
full-height proportional progress and no stray top color band or empty black
display gap in the captured states. Intended scroll clipping is retained.

No reward was claimed, saved appearance/switch changed, message sent or team
joined. The guest Account modal truthfully presents unavailable linking and
disabled Google/VK controls; it does not exercise the failed managed Copy path.
Rankings/Teams remain labelled local example/demo views. The final preservation
proof binds unchanged ordinary data before, after and after normal relaunch,
zero selected app-PID runtime error signatures and empty pending markers.
The fixed eight-second observation wait is not a startup SLA, and these images
do not accept every modal, locale, state or other physical device.

## Current physical timing diagnostic and next priorities

`Phone/Device01/Fluidity/cc77c5a1e16c492d88ee4543963be7b7/Manifest.json`
under Review93 records the current candidate on the actual phone. During the
**255-second quiet window**, the host made no screenshot/video, log, graphics,
memory, thermal or filesystem queries to the phone. Report polling happened
after that window. The unaccelerated isolated fixture retains all **1,983 frame
samples across eight phases**, with no native errors and unchanged ordinary
owner data before, after and after normal relaunch; markers remain empty.

| Phase | Frames | p95 interval ms | Worst interval ms | Command span ms |
| --- | ---: | ---: | ---: | ---: |
| Idle and hint search | 480 | 16.733 | 33.200 | 0 |
| First natural command | 68 | 16.844 | 50.206 | 45.002 |
| Second natural command | 159 | 16.726 | 16.760 | 24.461 |
| Rocket | 118 | 16.746 | 33.289 | 33.605 |
| Three-rocket chain | 118 | 16.736 | 16.751 | 19.068 |
| Orb plus rocket | 409 | 16.748 | 33.428 | 31.226 |
| Golden plus bomb | 427 | 16.740 | 16.826 | 23.011 |
| Victory animation | 204 | 16.720 | 99.943 | 0 |

All seven intervals above 33.34 ms are retained: one first-command interval,
five Orb/rocket intervals and one victory interval. Two exceed 50 ms:
**50.205982 ms** in the first natural command and **99.942909 ms** in victory.
The largest command span is **45.001692 ms** in the first natural command.
The victory slow sample has measured Update/render spans of approximately
0.983/0.891 ms and no pool/sprite creations; that does not identify the source
of the much longer frame interval or rule out platform/presentation waits.

This is **recorded diagnostic evidence, not a smoothness PASS**. There is no
paired baseline or fresh reference, no direct GPU/presentation/touch-latency
measurement and no universal frame-budget approval. `firstPresentationMs`
records dispatch, not the first visible frame; the allocation counter is
unusable in this player. The unchanged native report's legacy emulator wording
is preserved; actual target/APK/build receipts identify this run as physical.
Development instrumentation and platform scheduling remain relevant limits.

The next performance work should correlate CPU/render/GPU/presentation traces
at the first-command and victory boundaries, then reproduce the Orb/rocket
missed intervals and dense crate/power chains. Retain every slow sample and
compare exact seeds/actions/builds with controlled device conditions, including
a repeat without intrusive observation. Change runtime code only after a
reproduced cause is identified, preserving outcomes, paths and rewards. A
natural long session, lower-memory/Android 8/tablet coverage and a fresh reference
comparison remain separate acceptance work. This review does not demonstrate
a comparison speedup or close the older unattributed handoff stall.

## Actual TCP operational rehearsal

`Verification/Evidence/Review93/Backend/Operations/Set03/Operational_Rehearsal.json`
passes **199 checks**, with **162 timed HTTP requests**, **72 concurrent reads**
and **12 parallel Daily Gift retries** after a controlled lost 503 response.
The same durable claim/ledger origin survives retries, server restart, a
consistent backup, fresh-path restore and startup of the restored database.

Four disposable managed owners exercise signed guest/session/key recovery,
single genesis, friends/direct/team messages, blocking/reporting, explicit
operator-granted moderation, global/regional standings, private records,
revocation/deletion, rate limiting and unavailable checkout/ads. No ordinary
phone identity, real player or owner balance is read or modified. Progression
is not forged to unlock real rewards, and no live payment/ad provider is called.

Three actual owned, bounded Uvicorn process trees are started and stopped:
original service, same-database restart and restored-snapshot service. The
fixture alone adds the private operator-file lost-reply control. All bodies,
credentials, private keys and disposable databases remain ignored/private;
public evidence exports bounded status/timing/check metadata and source hashes.

All 162 timed requests are retained: median 31 ms, nearest-rank p95 125 ms and
maximum 375 ms. Routes include expected rejection/recovery responses; this is
not an all-200 metric. Host contention is uncontrolled. The separate 113
successful rate-limit reads and final 429 are untimed. One globally approved Windows
replay slot and serialized SQLite writers remain capacity constraints to
measure on the chosen deployment.

Backup and restore reports validate schema 8/new destinations and file fsync.
Windows inherited ACL/directory-fsync limitations remain explicit; no physical
power-loss durability is certified. TCP is loopback, so the rehearsal does not
test public DNS/TLS/reverse-proxy/cloud failures or establish production
throughput/availability. The user's actual traffic target is still needed.

**Retained Set01 failure:** the first harness expected the Windows virtualenv
launcher PID to equal the actual Python server PID and timed out during
readiness. It remains FAIL with zero checks. The repaired harness verifies the actual owned
parent/child process chain and uses kill-on-close ownership. No runtime assertion
or readiness requirement was waived. Set02 remains the earlier-source pass;
Set03 re-executes the rehearsal after the broader transaction-time repair.

## Dependency and primary-document review

`Backend/DependencyAudit/Report.json` under Review93 compares 19 installed package
versions with the pinned lock, records successful `pip check`, and binds the
bounded OSV response. No matching advisories were returned for that exact query.
This is a time-specific observation, not proof of no vulnerabilities, a
penetration test or permission to upgrade dependencies. The lock is unchanged.

`Verification/Evidence/Review93/LaunchAudit/Audit.json` binds the owner checklist
to 17 core source/evidence inputs, current scoped-report supplements and 15
official documentation references; 12 local links were checked. The audit
itself counts no native/device/provider execution. Current
RuStore/Yandex/VK/Unity documentation supports concrete registration, product,
manifest/return, notifications, signing, privacy/UGC and listing steps. The
current moderation guidance permits up to six days and additional-information
restarts; a two-to-three-day preparation target is not a guaranteed public date.

[PrivacyReview.json](../../Verification/Evidence/Review93/PrivacyReview.json)
records a separate read-only review of the **617 public text/source/log files**
present in its recorded corpus. Comparison with **58 selected known private
values** finds no matches, high-confidence credential candidates, unexpected
credential/database artifacts or public read/decode errors. Thirteen private
JSON reads/parses could not be used, and binary/OCR content is excluded; this is
bounded evidence, not exhaustive secret detection or a security certificate.
The same report confirms the exact tested 95-input backend map, unchanged
protected artwork/Resources/levels/Packages/ProjectSettings/existing metadata,
and disabled release/commerce/ad defaults. No penetration test, repository-
history scan or provider acceptance is implied.

## Broad app/backend acceptance matrix

[FeatureCoverage.json](../../Verification/Evidence/Review93/FeatureCoverage.json)
maps **25 feature areas** to representative actual passing test IDs, complete
native suite bindings and separate service/native/ordinary-Android/provider
acceptance. It is a source/report-derived assessment, not another executed test
suite. Its counts match the final 472 backend tests and 37 passing native suites;
both Account failures, simulated Cup/unavailable providers and physical/hosting
limits remain explicit.

| Feature group | Current review method | Material operational acceptance still required |
| --- | --- | --- |
| Tutorial, first/return startup and loading | Native lifecycle, rendering, tutorial gesture and real resource-failure controls | Ordinary configured cold/warm/recovery timing, background/kill points and more physical devices |
| Home/navigation/profile/settings | Native current-source UI/localization/geometry and progress checks; 11 actual phone cases/15 reviewed OS captures including normal relaunch | Full modal/locale/device accessibility matrix; managed account touch/recovery acceptance |
| Gameplay, obstacles/powers/tools/cascades | General/model, mixed-swap, cascade, snapshot, attempt/continue, real-worker tests and current 50-board transient Android fixture | Natural full campaign, fresh reference, sustained dense cascades, GPU/main/render traces and human balance |
| Wallet/lives/stock/Continue | Transaction/idempotency/capacity, repeated +5/900 and zero-life 900 refill contracts | Genuine upgrade/process-death/corruption cuts using disposable durable Android profiles |
| Daily Gift/Wellworks/practice Cup | Current native/service boundary/recovery and locked/claim fixture checks | Hosted timer/worker operation, natural event/milestone progression and deployed account/device acceptance |
| Friends/messages/Teams/records/ranks | Real SQLite/ASGI/TCP and connected Editor HTTP with isolated users | Ordinary configured phone multi-user touch, public load, moderator/support operations; no push/media/live Cup PvP is implemented |
| Identity/deletion/VK | Auth deadline tests and strict native/HTTP account runs | Unreached Account stages, real VK registration/consent/return and deletion/retention operations; Google remains unavailable |
| RuStore commerce | Order/provider/parser/recovery/checkout guarded fixtures and complete service regression | Registered signed SDK build, real sandbox/bank return/refund/restart/duplicates and controlled live-money tests |
| Ads | Quota/calendar/deadline/retry and UI/transport fixture coverage | Real Yandex unit/privacy/video/no-fill/restart acceptance; limited-trust completion risk remains disclosed |
| API/worker/operations | Complete current-source service regression plus bounded actual TCP/restart/restore | Owned HTTPS topology, chosen-host mixed-load saturation, storage/worker capacity, monitoring/on-call and rollback |

## Current evidence publication rules

New runners write only fresh Review93 directories and bind exact source,
configuration, actual process exits, native reports and raw logs. The collector
does not call a historical current-tree verifier, overwrite failed evidence,
convert host checks into Unity/device tests, or add failed-run attempted checks
to passing-suite totals. Intentional missing-resource diagnostics are validated
by the resource fixture's exact report rather than a blanket zero-log rule.

`Verification/Tools/Review93/collect_review93.py` writes `Draft.json` while proof
is incomplete. A completed scoped `Summary.json` requires all configured final
native suites on one exact Unity map, current zero-skip backend/real-worker
evidence, separate actual TCP operations, both fresh internal Android builds and
static checks. Only exact reviewed Account clipboard failures can remain in a
completed review; they stay FAIL and production/all-acceptance flags stay false.
Any unrelated/unclassified failure prevents completion.

Optional actual phone evidence must have its own exact APK/source, original OS
captures, reviewed cases, owner-save preservation and normal-relaunch receipts.
An earlier phone session is not relabelled as this build's test. Current native
render captures are not automatically marked visually accepted.

The final collector controls pass **30 host-only negative checks** at
`HostControls/Set04.json`. They reject changed hashes, unknown/extra native
failures, inflated labelled-check counts, missing process cleanup, changed
backend maps and incomplete restore evidence. A historical Account JSON is
strict-pattern input data, not a newly executed historical suite. Separate phone,
regression and fluidity helper controls pass 14, nine and seven host checks;
their initial fixture/wording failures are retained separately. None of these
host controls is counted as Unity, device or provider testing.

## Remaining launch sequence

1. Resolve the retained Account clipboard boundary in a disposable foreground
   context and complete the previously unreached account stages. Preserve both
   original strict FAILs and the separate hidden non-batch repeat; do not waive
   assertions or substitute the secret directly to manufacture a pass.
2. Complete ordinary configured payment/ad/provider acceptance and correlated
   physical performance/device/campaign work with disposable data; the scoped
   engineering review, current internal builds and preserved phone runs above
   are complete, not production approval.
3. Deploy isolated owned staging and rehearse the real topology's load, worker,
   monitoring, backup restoration, secret rotation and rollback procedures.
4. Supply real Console/products/signer/domain/VK/Yandex/legal/support/moderation
   inputs listed in [the launch checklist](../../Release/RuStore/Launch_Readiness93.md).
   Freeze accepted artifacts/config/schema and make an explicit go/no-go
   decision before production activation and store submission.

The required Unity splash remains under the owner's current entitlement. The
Pay SDK's Unity 6000 metadata versus the pinned engine remains a support gate;
neither JSON flags nor an isolated Java 17 compile replaces a supported and
accepted configured Android integration. No public launch approval is issued.

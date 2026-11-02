# App and backend review, checkpoint 86

Review started 26 October 2026, America/New_York. The owner requested a detailed
review, a modification plan and implementation. Baseline is committed source
`e3fc9865`, following checkpoint 85. The pinned engine is Unity 2022.3.62f3.
No production account, signing identity, provider unit or public backend is
created or activated by this review.

## Review and implementation plan

| Priority | Finding / task | Implementation and acceptance | State |
| --- | --- | --- | --- |
| P0 | Ordinary server bootstrap can re-enter from a failure notification through ProfileHost.Refresh. | Fence initialization through notification/unwind; native tests for synchronous protected-store failure, held identity and real HTTP wallet failure; later explicit retry still works. | Lifecycle passes 32 checks on current source; connected ServerHttp passes separately; no device claim |
| P0 | Invoice verification uses an obsolete purchase URL instead of the currently documented v2 invoice URL. | Use the official live and sandbox `/v2/invoices/{invoiceId}` endpoints; retain all amount, owner and product checks. | Implemented; targeted service verification passes |
| P1 | `REFUNDING` is accepted by notification ingress but rejected by invoice reconciliation. | Treat verified refund initiation as sticky refund review before/after credit; no new grant or automatic debit; test stale confirmation, restart and worker retry. | Implemented; targeted service verification passes |
| P1 | Identity proof/family expiry can use a time sampled before waiting for a write transaction. | Sample and validate server time inside the exact transaction, retaining the persisted high-water clock; signed request regressions for expiry and retry boundaries. | Implemented; final 397-test service run passes |
| P1 | HTTP JSON accepts duplicate names and non-UTF-8 encodings; body reads have a byte cap but no total receive deadline. | Reject ambiguous/invalid JSON before handlers; cap before copying chunks; bound body reception without timing out legitimate downstream gameplay/payment work. | Implemented; final 397-test service run passes |
| P1 | The payment adapter discards purchase identifiers supplied with cancellation/errors. Unknown orders can become permanently unrecoverable through a successful-only purchase list. | Retain a durable recovery hint, read old journals, query the exact purchase and resolve only a fully bound server-verified terminal decision; never infer cancellation from absence. | Recovery native suite passes 85 checks/12 cases; actual failures retained; real SDK/provider acceptance remains separate |
| P0 release | Ordinary Shop has no configured checkout caller. SDK fixture compilation alone is insufficient. | Disabled-by-default sandbox host now binds authenticated catalog, durable order, SDK purchase/recovery, server reconciliation, wallet refresh and acknowledgement. Preserve origin/player/generation ownership and explicit Continue. | Checkout283 checks/11 cases and SDK22 compile/API checks pass in their distinct scopes; actual configured SDK/Android/payment acceptance remains open |
| P1 | Near the 1000-action replay limit, a continuation can charge 900 coins without room for all five purchased moves; local input beyond the cap can leave a retry-only error. | Reserve six history entries for a new Continue; a new Tool must also preserve all remaining move slots. Guard before worker/debit/model mutation and expose explicit forfeit/Keep playing, while recovering committed receipts without a second charge. | Final 397-test backend and targeted native Capacity 46 checks/8 cases pass; provider/device scope unchanged |
| P0 release | Production and external services are still unconfigured/blocked. | Separate implementation gaps from missing operator inputs; validate deployment/readiness and final release configuration without converting booleans or local tests into approval. | Implementation and operator gates documented; production activation remains blocked |
| P1 documentation | Older current-state tables still describe delivered backend work as absent and list superseded life/continue rules. | Current tables distinguish explicit server mode from local demonstrations, 900-coin full refill and repeated +5/900 continues; historical dated evidence is retained. | Updated; no new runtime acceptance implied |
| Verification | Re-run the affected service/native suites and ordinary Android compilation after source is held. | Archive exact inputs, actual process results and failures; preserve earlier evidence and emulator saves. Exercise integration with isolated accounts only. | Backend397 passes; 13 native suites/21,562 checks pass, two Account suites fail with 56 attempted checks. SDK22 compile/API checks pass separately; both current internal Android builds and static checks pass; Account acceptance remains incomplete |

## Review coverage

The review traces actual callers and service mutations for startup/tutorial and
Home routing; managed accounts, recovery and deletion; wallet/inventory/lives;
verified attempts, tools, repeated continues and win settlement; Daily Gift,
Wellworks and practice Rain Cup; friends, team/direct messaging, records,
rankings, blocking/reporting/moderation; purchases, notifications and worker
recovery; rewarded ads; persistence, HTTP ingress, operations and release guards.
Each area will retain its own source, service, native, Android or externally
blocked evidence boundary. Reviewing code is not proof that every natural-play
combination, physical device or live provider flow has run.

| Area / actual path | Review findings and changes | Evidence boundary / remaining limit |
| --- | --- | --- |
| App/session: PlayerProfileHost, ServerGameSession and Home callers | Explicit server selection and generation fencing; bootstrap failure re-entry repaired without importing local balances | Targeted Lifecycle native execution exists; ordinary configured Android startup, touch and upgrade still require fresh acceptance |
| Identity/account: managed challenge/session/recovery/deletion and guards | Expiry observations moved inside the writer transaction; revoked/deleted actors are rechecked before mutation and cached replies | Current service run covers the held backend source; no provider linking, production account rollout or full physical purge is claimed |
| Social: friends/profile, Teams, direct/team messages, records/rankings and moderation | Permission, revocation, blocking, bounded paging, durable operations and explicit ranking consent reviewed; current real loopback SocialHttp passes 17,896 checks | Service/native scopes do not supply staffed moderation, push delivery, real-player load or public operations |
| Gameplay/wallet: approved replay broker, attempt/tool/continue settlement | Authoritative receipts, replay ownership and repeated continues preserved; new Tool/Continue guards protect purchased move capacity before debit | Final 397-test run includes the approved real worker; targeted native capacity controls pass, without new balance or physical-performance certification |
| Rewards: Daily Gift, Wellworks and practice Rain Cup | Existing server authority/protected intents and same-account wallet projection retained; no animation callback grants | Cup rivals remain simulated; no real PvP/team event or deployed scheduler claim |
| Advertising: Shop offer, protected flow and capped server claims | Accepted85 denial recovery preserved; 400 coins/three UTC+10 daily credits/600-second cooldown unchanged | Disabled by default; SDK-reported completion is lower-trust, not verified impression proof; no configured live/device ad test |
| Commerce: catalog/order, Pay adapter/coordinator/journals and backend authority | Normative invoice URLs, sticky REFUNDING review, durable purchase hints, exact terminal receipts and gated Shop host implemented; scripted host/native parser, actual loopback PayHttp and isolated real SDK API compilation pass | These separate scopes do not establish a real payment, external-bank return or configured Android SDK checkout acceptance |
| Operations/ingress: bounded HTTP, readiness, notifications/discovery, backup and release guards | Strict JSON/receive deadline and rolled-back database writer readiness implemented; existing hints only enqueue fresh provider reconciliation | Hosting, actual Console traffic, scheduled workers, restoration drills, legal retention and live signing remain operator/release gates |

Approved artwork, GUIDs, level masks, M46/M48 gameplay rules, presentation timing,
Russian branding and five supported languages remain the baseline. The Doc65
corrections remain in force. No Golden+Golden mechanic, economy redesign,
automatic engine/SDK upgrade or local/cloud migration is introduced.

## Current evidence and references

The final backend run passes **397 executed tests, zero skips** in 203.281 seconds,
including the approved real worker and the six capacity-boundary regressions.
Its report is `Verification/Evidence/Review86/Backend/Final/Service_Tests.json`;
84 exact tested inputs are archived in that final directory. The preceding
391-test/132.766-second run and its 84 inputs remain unchanged under
`Backend/Full/`; that earlier run predates the capacity repair. Neither backend
result is an Android, live payment or complete Unity execution claim.

`Review86/ReadLoad/Report.json` and `Samples.json` retain 80 actual in-process
ASGI/SQLite reads from four concurrent threads and four temporary owners.
All 80 returned 200 with matching owner/time contracts; median latency is 20.422 ms,
nearest-rank p95 is 74.156 ms and the retained maximum is 467.563 ms. Business-state
digests are unchanged; authentication clock/rate metadata is explicitly excluded
from that business digest. There is no TCP, public hosting, payment, Unity or
production-capacity measurement. Host scheduling/other review processes are not
controlled, and the largest request is not discarded.

The current default native run `a72a5dafcbff4dbd90de7d1881c8c3d6` passes nine
suites/3,301 checks: Lifecycle (32), Recovery (85), Checkout (283), Capacity (46), Guard (328),
Identity (69), ServerCore (55), Rubles (2212) and AdFlow (191). Account fails after 44 attempted
checks: its real Copy callback occurs once and backup acknowledgement is observed,
but the Editor clipboard readback is empty. The ten-target invocation remains
failed; its successful components retain their own actual process/source records.

Connected orchestrator `d98444ff300941c38efca7210c857347` invokes native run
`5e8cbc54730e412094c75c921b47db13` against isolated real loopback services and
the approved replay worker. IdentityHttp (25), SocialHttp (17,896), ServerHttp (302) and
PayHttp (38) pass: four suites/18,261 checks. AccountHttp fails after 12 attempted
checks at the clipboard copy step. Its later recovery, logout, deletion and
fresh-guest stages did not run; their descriptions in the fixture's scope are
not completed evidence. Neither connected invocation is a full pass.

Across these two invocations, **13 suites/21,562 checks pass**; **two failed
Account suites contain 56 attempted checks**, which are not counted as passed.
`Environment/ClipboardAccess.json` separately records five unsuccessful Windows
`OpenClipboard` calls with `ERROR_ACCESS_DENIED` (5). Those are current Python
process acquisition observations, not proof of the already-exited Unity
process's cause or Android clipboard behavior. The Account gap remains open.

`SDK/9168031b278e49fa84e58f6744a55041/Process.json` records a successful owned
pinned-Editor process with 22 real SDK API/compile checks. The four exact current
adapter/contracts/coordinator/file-journal files compile under `HOTR_RUSTORE_PAY`
against official stock Pay11.1.0/Core10.5.0 packages and metadata. No SDK singleton
was initialized, no payment/provider call ran, and no Android or ordinary-game
SDK integration was built or executed by that fixture. Earlier altered-metadata
and failed SDK attempts remain separate preserved evidence.

`VisualReview.json` binds six captures actually inspected by the root reviewer:
English/Russian sandbox Shop and NoMoves controls, ordinary Russian coin-list
preview and the largest coin offer at320×480. Reported text/quote/button/footer
containment passes within those sampled Editor frames. This is neither automatic
visual approval nor Android touch/provider acceptance. Both current internal
Android builds are running; their final artifact/source results are pending.

Actual native attempts are retained under `Review86/NativeRuns/`. They exposed a
fixture constant shadowed by its scripted store's `Purchase` method, and a real
terminal-response parser error: Unity JSON conversion did not preserve the
explicit null delivery-acknowledgement value. The parser now requires and
type-checks that field and preserves null; extra wrong-type/missing/empty-value
counterexamples were added. Source review also caught the SDK recovery helper
inside a lambda rather than class scope; its unchanged implementation was moved
under the class-level SDK guard. The stale guard fixture was also corrected to
the actual disabled notification status and required server-order acknowledgement
field. Corrected targeted native suites now pass as listed above, while the
original failed runs remain failures. The current isolated SDK compile result
closes its specific API-compilation check; overall acceptance still requires the
current build results and an explicit disposition of both Account failures.

The original checkpoint 85 records remain immutable under
`Verification/Evidence/ShopAds85`. Their backend358, native191/25 followup,
earlier UI captures and SDK compile/static scopes are the starting baseline,
not new checkpoint86 executions.

The current normative RuStore invoice reference specifies both `/public/v2/invoices`
and `/public/sandbox/v2/invoices`, and includes the `REFUNDING` state:
[official invoice API](https://www.rustore.ru/help/work-with-rustore-api/api-subscription-payment/v2-purchase-invoiceid).
Its illustrative response currently contains merge-conflict markers; endpoint
and field/status tables are used, not that malformed example.

HTTP receive deadlines are separate from Uvicorn's between-request keep-alive
timeout: [Uvicorn server behavior](https://uvicorn.dev/server-behavior/).
JSON interoperability and parser limits follow
[RFC 8259](https://www.rfc-editor.org/rfc/rfc8259).

`Review86/DependencyAudit/Report.json` records an actual OSV version query for
18 pinned Python dependencies: no matching advisory was returned for those
versions at the recorded time. This is a database lookup, not a penetration
test, complete supply-chain audit or security certification.
[OSV batch-query contract](https://google.github.io/osv.dev/post-v1-querybatch/).
Unity's release page confirms the pinned 2022.3.62f3 changeset `96770f904ca7`;
its September 2025 advisory lists 2022.3.62f2 as a patched 2022.3 LTS release for
that specific issue. This limited provenance check does not certify every SDK,
current vendor support or all security issues. The separately documented SDK
package/Unity-version compatibility mismatch remains an acceptance constraint;
no engine or SDK upgrade was made.
[Pinned release](https://unity.com/releases/editor/whats-new/2022.3.62f3),
[specific Unity advisory](https://unity.com/security/sept-2025-01).

Results, exact changed files, completed plan items and remaining launch gates
will be appended after implementation and verification are held.

## Remaining release work

1. Resolve or explicitly retain the Account/AccountHttp clipboard gap and execute
   the connected recovery/logout/deletion/fresh-guest stages that were not reached.
   Preserve their failed runs. The completed internal builds and isolated SDK
   API compile do not replace this acceptance or ordinary configured
   Android/payment verification.
2. Exercise an ordinary externally configured Android account through startup,
   session expiry/recovery, gameplay and connected pages; verify upgrade and
   existing-save isolation. A fixture package is not this acceptance route.
3. Register the real Console application/products, sandbox backend and signing
   identity. Test ordinary Shop success, cancellation, failed/unknown delivery,
   duplicate callbacks, process death, external-bank return, late refund and
   missed notifications against the real provider. Keep production disabled.
4. Profile physical low/mid-range devices and long sessions, including dense
   power-up cascades and the previously unresolved handoff stall; source review
   and isolated improvements do not establish hitch-free gameplay.
5. Deploy monitored HTTPS/API and the approved isolated Windows replay worker;
   rehearse scheduled reconciliation/discovery, locked/failed database readiness,
   backup restoration and secret rotation. Publish factual privacy/retention
   policy and staff report/moderation/support handling before public social use.


## Final internal build and source evidence

Both fresh SDK-free IL2CPP ARM64 compilations pass. The accepted run is
`Review86/Builds/40048737026f4ae4b689e2e6dfdb5c53/Invocation.json`.
It restores exact ProjectSettings bytes and all six historical native reports,
with all 5,373 current Unity inputs unchanged after restoration and no remaining
Editor process. The earlier run compiled both APKs but observed another Unity
process during cleanup and deferred restoration. That failed invocation remains
unchanged; `RestorationFollowup.json` records exact restoration after the process
exited, before the new accepted run. No foreign process was stopped.

`Review86/StaticAndroid/99438abcdab442739b9329a1444905f8/Report.json`
binds the accepted APKs to signature, CRC, alignment, 16-KiB ELF, Russian label,
portrait activity, ARM64, device identity and absent payment/ad SDK checks.
The internal APKs retain the original API22 minimum and auto-selected target36;
they are not store releases. Production preflight separately requires the
configured API26-or-higher minimum and an explicit matching target. The first
static helper attempt retained its partial checks after a CRLF field-parser
failure; the corrected helper ran fresh. Neither issue required a game change.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| `Unity/Builds/Verification/HeartOfTheRain_Development.apk` | 328,982,301 | `be4b1a1c0641adb97bc279b5f009e21630dc8fc30b802986590cc7a38a10ac68` |
| `Unity/Builds/Verification/HeartOfTheRain_ReleaseCompile.apk` | 266,321,229 | `e0bc123d0610fcf1d5287cdac7dde987a87d783ee5696128b2232048fd3db96e` |

`Review86/Inputs/Archive.json` lists exact changed Unity code/new metadata and
review tools, plus every unchanged committed Unity input checked against
`e3fc9865`. Existing art, asset GUIDs, level masks, M46/M48 model and presentation
timing remain unchanged. Backend final inputs have their separate 84-file
archive. The accepted process manifests bind the complete 5,373-input Unity tree.

Runtime changes are confined to backend ingress/readiness, identity/service
clocks, commerce/provider/replay capacity; the app's ServerGameSession and
server attempt/account/continue callers; the five payment-core files; the new
ShopCheckout86 service/host/journal/UI binding; and the existing Shop/NoMoves
callers. New and corrected Editor suites and review tools supply regression
proof. The archive contains the exact path list and bytes, rather than a claim
that every unchanged game file was newly executed.

The review dashboard and `Summary.json` use
`COMPLETED_TARGETED_APP_BACKEND_REVIEW86_WITH_UNRESOLVED_GATES`.
They retain both Account FAIL records and distinguish21,562 passing-suite checks
from56 attempted checks in failed runs. The collector accepts only the exact
recorded clipboard failures with the bound metadata-only Win32 probe; eight
classification counterexamples/checks verify that unrelated failures or invented
later account acceptance cannot be relabelled. This is a review completion
record, not an all-tests pass or release approval. No APK install, emulator
operation, public deployment, real payment or new full-game performance pass
occurred in checkpoint86.

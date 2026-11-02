# Heart of the Rain portable backend

## Checkpoint102 VK registration and sign-in

The optional browser flow now supports explicit registration of the current
managed guest and sign-in to an existing VK-linked player. Authenticated
`POST /v1/identity/vk/signin` binds a fresh device key and completion-secret
digest to a durable ten-minute OAuth flow. The shared HTTPS callback validates
VK and prepares an immutable target, but never issues a game session. The app
must confirm that exact target and submit a device-signed `vk` identity challenge
to `/v1/identity/vk/complete`. The transaction links/registers or restores that
target once, without importing, merging, resetting or rewarding a wallet, rotating
an existing recovery code, or settling another device's active attempt.

The additive schema9-to10 migration preserves existing challenges and all
financial/account records. Completed-response retries reconcile the same session
family after restart or OAuth expiry; cancellation, source logout, deletion,
wrong-device proof and changed target ownership cannot authorize a new session.
The old link-only endpoint retains its original conflict behavior. Configuration
is disabled by default, and real VK registration, hosted HTTPS configuration and
configured Android/provider acceptance remain required. Local automated tests
simulate VK HTTP explicitly and do not establish real-provider acceptance.

## Checkpoint100 full-inventory commerce

The additive [full-Grant contract](../Release/RuStore/COMMERCE_FULL_GRANT100.md)
freezes coin/starting-item/tool grants in schema9 orders and credits. Verified
CONFIRMED delivery projects the entire grant and consumes a stable-player Special
entitlement in one SQLite transaction. Concurrent one-time creates resume the same
order; trusted final cancellation/rejection/expiry releases an undelivered
reservation. Unknown/outage/client cancellation holds it. RefundReview remains
sticky with no automatic inventory clawback or cap reset; contradictory late paid
evidence needs operator reconciliation. Player-scoped pending-order pagination
supports another session/device, and provider acknowledgement is checked through
the existing reconcile endpoint. Legacy coin-only catalogs and receipts remain
compatible. Default checkout and real providers remain unconfigured/disabled.

`tests/test_commerce_grants100.py` covers actual SQLite/ASGI full-inventory,
concurrent, recovery, overflow, fault, refund, deletion and schema8→9 snapshot
cases with a scripted provider. Current receipts determine test acceptance; these
are not live payments or physical-device claims.

## Checkpoint93 review and operational rehearsal

Authenticated actors now retain a server-only clock sampler. Every existing
credential guard checks the actual transaction-time deadline as well as the
captured request time and persisted clock high-water. A handler queued behind a
SQLite writer, a cached receipt read, or a delayed invoice response cannot extend
an expired credential. Invalid late clock samples fail closed. No client field,
identity capability or public API changes.
An expired payment request keeps its pending invoice record, so a fresh credential
or the trusted reconciliation worker can deliver the same order exactly once.

Daily Gift offers/claims, practice Cup join/deadline/scoring/claims, permanent
Wellworks reward receipts, wallet regeneration/refill/attempt settlement and
replay result/fault commits take one fresh service-time snapshot inside their
actual writer transaction. Queuing across midnight cannot claim a stale first
offer; a clear committed after a Cup ends contributes no point; and a naturally
regenerated life prevents a stale zero-life purchase from charging coins. A loss
starts its life timer from its actual writer time. Committed idempotent receipts
retain their original payload/time, including recovery after expiry or restart.

Rewarded-ad claim time is sampled inside its writer transaction. A writer wait
across local midnight or opportunity expiry therefore uses the actual commit
day, full 600-second cooldown, and current expiry check. The 400-coin/three-per-day
policy, lower-trust SDK-reported completion and disabled default are unchanged.

`tests/test_actor_deadline93.py` supplies real ASGI/SQLite boundary regressions.
`tools/review_operational93.py` runs a bounded actual separate-process Uvicorn
loopback/TCP rehearsal: signed managed guests, social permissions/moderation,
regional standings, duplicate/concurrent/lost-response claims, read concurrency,
owned-process restart, online backup/new-file restore, recovery and deletion.
It uses disposable accounts and a private ignored database, never an ordinary
player save. The fixture has no public fault-control endpoint, and reports redact
credentials. Root separately runs the full suite with the approved Unity worker.
Fresh reports and exact inputs belong to `Verification/Evidence/Review93/Backend/`;
report status, not this implementation inventory, determines acceptance.

These local rehearsals do not certify public HTTPS hosting, live VK/Google,
RuStore purchases/bank return, Yandex impressions, staffed moderation, production
capacity, physical power loss, or the ordinary configured Android app. Historical
reports below remain tied to their original sources and limits.

## Checkpoint89 regional rankings, provider signup and local ad days

Players explicitly select a country/region independently of language and time zone.
`GET/POST /v1/region` stores that preference; player standings now support
`global` and `regional`, and `/v1/team-leaderboards/{global|regional}` ranks teams.
Regional team placement uses the captain's selected country. Scores use only
server-verified completed levels from active, opted-in, visible members. Country
selection is a preference, not verified residency or precise location.

VK signup/linking is configured separately from guest authentication. Its optional
browser flow uses server-owned PKCE and verified provider identity, preserves the
current stable player and never merges accounts. Google remains unavailable.
The original link-only endpoint produces an explicit conflict for an existing VK
identity on another player. Checkpoint102 adds the separate, explicitly confirmed
VK sign-in/restoration flow described above; recovery codes remain available as
an independent path. No live provider configuration is supplied. See
`Release/RuStore/VK_ID_SETUP.txt` for registration and HTTPS setup.

Rewarded ads retain400coins, three credits per player-local day and600seconds
between credits. Android supplies an IANA zone; server time and pinned timezone
rules calculate local midnight, including daylight-saving transitions. Changing
time zones retains the current quota through its existing reset. Fixed-offset and
older-client compatibility are documented in `Release/Advertising/README.md`.
The Shop note states that free rewards can be claimed three times a day.

Schema8 upgrades add these records transactionally, preserve existing wallets,
reservations and receipts, and extend validated backup/restore. Account deletion
also removes the optional region, provider association/flow and ad-calendar data.
Configured HTTPS/provider acceptance, deployed services, account recovery policy,
moderation and store release remain separate gates. Current test results and exact
inputs are recorded in `Verification/Evidence/RegionalAccounts89/` when collected;
these implementation statements do not claim a live service or provider test.

## Historical checkpoint85/86 acceptance below

## Current implementation and accepted evidence (26 October 2026)

The latest accepted backend checkpoint passes **358 executed tests, zero skips**,
including the approved real Unity replay worker integration.
`Verification/Evidence/ShopAds85/ReservationRecovery85/Backend358/` preserves its
report and 79 exact tested inputs. Earlier connected-app evidence remains in
`Verification/Evidence/ServerGameplay83/Backend/Verified324/` with its original
324-test, 73-input scope. Current checkpoint86 changes are under review; this
documentation update does not claim a new full-suite, SDK or device result.

Managed guest identity, recovery/deletion, server wallet,
friends, private/team messages, reports, blocking, opt-in leaderboards and
private records are implemented. Explicitly configured ordinary Unity server mode
now connects gameplay settlement, paid tools/continuation, account controls,
Profile rename/records, social pages, Daily Gift, Wellworks, practice Rain Cup and
Home reward badges. Six pinned-native suites pass 18,420 checks, including real
loopback HTTP and the approved replay worker. Three deterministic local access-age
injections exercise signed session renewal; they are not a 15-minute wall-clock
soak. Evidence is `Verification/Evidence/ServerGameplay83/VerifiedAppWithJNI/`.
Existing local saves are not imported or merged automatically.

Both final internal Android build profiles pass compilation and static APK checks.
A separate ARM64 IL2CPP test package passes101 checks across eight externally
observed Android processes: ordinary host/Play/paid Hammer/quit, identity reopen,
sign-out/closed restart, fresh-key recovery and deletion/closed restart. Its
protected keys are nonexportable; no hardware attestation is claimed. Existing
ordinary QA saves/preferences match their original hashes. This fixture does not
certify ordinary configured startup, touch interaction or production payments;
the ordinary installed QA app remains checkpoint81. Server mode requires explicit
external configuration, and production remains blocked.

The approved gameplay worker is a **Windows Mono executable**. Its launcher
requires Windows Job Objects and fails closed on other operating systems. The
Python API can be hosted separately, but a Linux gameplay worker is not supplied
or certified by the Windows build. Deploy the exact approved Windows bundle or
complete a separate host build, resource isolation and full parity acceptance.
See `83_PINNED_GAMEPLAY_VERIFIER_REVIEW.md` in the handoff documentation.

These results do not enable production, deploy HTTPS, register store products,
complete actual RuStore payments or staff moderation. The sections labelled
earlier checkpoints below retain their original historical boundaries.

### Current HTTP reception and readiness behavior

The current ingress implementation bounds each HTTP body to 65,536 bytes before
authentication, parsing or mutations, with a 15-second total body-receive
deadline. Oversize requests return 413; receive timeouts return 408. Nonempty JSON
bodies (including requests without a content type) require UTF-8, a maximum
nesting depth of 64, unique object keys, finite numbers and valid Unicode;
invalid JSON returns 422 without echoing its contents. This receive deadline
does not replace individual gameplay or provider-operation budgets.

`/healthz` is cheap process liveness. `/readyz` checks the current schema and real
SQLite writer access using a bounded `BEGIN IMMEDIATE` transaction and a no-op
clock update, then always rolls back; it returns 503 when that probe fails.
Authenticated reads also advance the durable clock, so read-only database access
is insufficient. Readiness does not certify HTTPS, provider credentials, gameplay
worker availability or production activation. These describe the current source
contract, not a new deployment or acceptance claim.


## Historical checkpoint82 foundation boundary

The following foundation record describes checkpoint82. Its statements about an
unconnected ordinary game, missing replay verifier or pending UI integration are
historical; the current connected review above supersedes those limitations.

Checkpoint82 added explicit managed guest identity, encrypted-notification ingress,
durable reconciliation/discovery, backup/restore and social APIs. These additions
were reviewed in `Verification/Evidence/Launch82`; the older checkpoint81
sections below remain a record of the earlier boundary. In particular, public
guest registration now exists **only** when `HOTR_MANAGED_IDENTITY_ENABLED=1`;
social routes require `HOTR_SOCIAL_ENABLED=1`. Both default to off. Production
activation remained blocked, and ordinary-game service selection and a real
gameplay verifier were subsequent work. A local service test alone does not
enable a live purchase or certify a connected page.

### Identity, social and operator integration

Managed identity routes are `/v1/identity/challenges`, `/guest`, `/session`,
`/recover`, `/logout` and `/v1/account/deletion`. Device-key challenge proofs bind
canonical payloads; refresh/recovery successors are saved by the client before
dispatch and only their digests persist on the server. Access bearers are short
lived. A new device can recover only with the independent recovery secret;
payment authorization is not game-account linking. No local coins or progress
are imported. This custom protocol is not an OAuth or hardware-attestation
certification. The new Unity identity component is explicit and has no automatic
normal-profile bootstrap.

Social API groups now cover:

| Routes | Server responsibility |
| --- | --- |
| `/v1/profile`, `/v1/players/{playerId}` | Bounded Unicode names, exact public-code lookup, explicit leaderboard opt-in; no private wallet/credential fields |
| `/v1/friends`, `/requests`, `/request`, `/respond`, `/remove` | Mutual acceptance, immutable request generations, bounded pending/friend counts and durable retries |
| `/v1/blocks`, `/add`, `/remove` | Bilateral visibility/message suppression; unblocking does not recreate friendship |
| `/v1/teams`, `/{teamId}`, `/join`, `/leave`, `/members/{action}` | Single-team membership, bounded capacity, owner transfer, kick/ban/unban; no automatic new owner on ordinary leave |
| `/v1/messages/{Direct|Team}/{targetId}`, `/read` | Friends-only direct text and members-only team text; cursor polling, unread markers, rate limits, encrypted client command outbox required for integration |
| `/v1/reports`, `/v1/ugc/reports` | Message, public-name and team-text reports; reporting an abusive direct message remains possible after blocking |
| `/v1/records`, `/v1/leaderboards/{global|friends|team}` | Private attempt/first-clear records and opt-in standings from server-verified completed levels; ties share rank; no client-authored score or leaderboard reward |
| `/internal/v1/moderation/reports`, `/messages`, `/ugc/reports`, `/ugc/actions` | Separately operator-granted credential scope; manual review, hide/delete or safe name/text reset, durable action audit |

The route table abbreviates suffixes within each API group. Direct messaging
requires current friendship for send/read; reports return submission receipts,
not evidence that a moderator has acted. Deleted messages cannot be restored.
These are HTTP cursor APIs, without WebSocket delivery, media attachments,
external push notifications, staffed moderation or a new UI claim. Existing
Teams/Leaderboard pages remain demo until explicitly connected and reviewed.
The Rain Cup service remains the labelled practice competition, not real PvP.

Account deletion revokes sessions in the same transaction as removing social
visibility, public names, authored message bodies and private social command
receipts. A deleted owner's team closes and **all** members are released, so no
one is stranded or silently promoted. Financial/security audit tombstones and
backups require the owner's retention policy; the response explicitly reports
that physical purge and policy configuration are incomplete.

Operator commands (run from `Backend` with its virtual environment):

```powershell
.venv/Scripts/python.exe -m hotr_backend backup --source .local/authority.sqlite3 --out .local/backups/new-snapshot.sqlite3
.venv/Scripts/python.exe -m hotr_backend restore --source .local/backups/new-snapshot.sqlite3 --out .local/restored-new.sqlite3
.venv/Scripts/python.exe -m hotr_backend reconcile-worker --mode staging --max-jobs 50
.venv/Scripts/python.exe -m hotr_backend.moderator_tools grant --database .local/authority.sqlite3 --credential-file .local/moderator.json
```

Backup includes live WAL data through SQLite's backup API, validates schema and
integrity and refuses overwrite. Restore targets a new path and never swaps a
running database. Restrict the parent directory's Windows ACL and external
backup access. Moderator input is an existing operator-provisioned player-role
credential file in ignored storage; no app endpoint can grant this scope. Keep
the grant/revoke summary in the operator audit, and revoke base credentials when
removing an operator. Never use a verifier token as a moderator token.

Authenticated notification paths are implemented but unregistered/unhosted.
Activation requires `HOTR_RUSTORE_NOTIFICATIONS_ENABLED=1`, the external
`HOTR_RUSTORE_NOTIFICATION_KEY_FILE` and explicit sender CIDRs. AES-GCM validates
the encrypted payload; callback status only queues work, and the worker performs
the provider lookup outside the database transaction before an atomic credit.
No raw notification, payment token, key or card data is retained. Trusted ingress
must preserve/enforce the actual sender; arbitrary forwarding headers are not
trusted. Lease/revision fencing and bounded retries survive process restarts.

The explicit `discover-invoices` operator command adds bounded app/date listing
hints for the lost-client-plus-lost-notification case. The documented listing
adapter is production-only: no sandbox URL is invented. Listing never grants;
it matches existing immutable orders and queues the same v2 verification. A
separately labelled synthetic sandbox lister covers service recovery tests.
Schedule overlapping dates and deliberate rescans for mutable pages; provider
timezone semantics and actual Console acceptance remain deployment checks.

Owner registration, configuration and release gates are in
[`Release/RuStore/OWNER_SETUP.md`](../Release/RuStore/OWNER_SETUP.md).

Checkpoint81 adds the staging wallet/attempt contract below, superseding the earlier checkpoints' reward-only authority boundary. `/v1/me.rewardTotals` and `/v1/commerce/credits` remain issuance/audit views, while `/v1/wallet` is the new authoritative **server** balance. Ordinary Unity local profiles are still unmigrated, and production is disabled. The older transport/workflow sections are explicitly retained history, not claims that the new wallet is absent.

This is a runnable local/staging authority service, approved before choosing hosting. It uses Python 3.12, FastAPI/Uvicorn and transactional SQLite on a persistent local disk. It has no provider-specific SDK or paid cloud resource. Dependencies are pinned in `requirements.lock`; Unity stays on 2022.3.62f3.

The service persists authenticated accounts, server-controlled UTC observations, issued offers, issuance totals, an authoritative staging wallet/inventory ledger, typed attempt spending, idempotent commands, reward/purchase receipts, trusted-verifier progression, practice cups and explicitly submitted client diagnostics. Daily Gift, Wellworks and Rain Cup quantities are byte-for-byte copies of the existing approved Unity resources. No economy rule or artwork is changed.

## Run locally on Windows

From the repository root, create the isolated backend environment if it does not exist, using the installed Python 3.12 executable:

```powershell
.venv/Scripts/python.exe -m venv Backend/.venv
Backend/.venv/Scripts/python.exe -m pip install -r Backend/requirements.lock
powershell -NoProfile -ExecutionPolicy Bypass -File Backend/Run-Local.ps1
```

The default listener is `127.0.0.1:8751`. `/healthz` and `/readyz` are public health controls. Game operations require a bearer credential; explicitly enabled managed-identity lifecycle routes instead require their device-key/refresh/recovery proofs. The encrypted store-notification ingress has separate authentication and sender controls. The default database is `Backend/.local/authority.sqlite3`. Set `HOTR_BACKEND_DATA_DIR` to another durable directory before starting if required. Keep the database, WAL and SHM under the same service account and persistent filesystem. Backups must use SQLite's backup API or a stopped, checkpointed database; copying only the main file while writers are active can omit WAL commits.

Provision a NEW isolated review account from a second shell:

```powershell
Push-Location Backend
.venv/Scripts/python.exe -m hotr_backend provision --out ../.verification-cache/Backend/Local/player.json
Pop-Location
```

The tool writes a newly generated credential to the ignored file and never prints its token. It refuses to overwrite credentials or export them to a source-controlled destination. `--player` binds an operator-approved profile ID; use this only for disposable review profiles until account migration is implemented. `--role verifier` is a separate privileged credential for a trusted server process, never for the Unity app. Managed guest registration and signed session/recovery routes exist only when explicitly enabled; there is no arbitrary public profile-import, clock-setting, balance-setting, privileged credential-issuing or reset endpoint. Operator tokens default to 24 hours; managed access tokens are short lived and renewed through the device-bound protocol. Both support server-side revocation. Raw bearer tokens are not stored in the database or evidence.

On Linux, create a Python 3.12 virtual environment, install the same lock, and start from `Backend`:

```sh
python -m uvicorn hotr_backend.api:create_app --factory --host 127.0.0.1 --port 8751 --no-access-log --no-proxy-headers --limit-concurrency 32
```

Linux/cloud execution is not certified by the Windows tests. The single-host SQLite deployment requires persistent storage; this is not a tested PostgreSQL or multi-region service. Managed identity and recovery code are implemented behind explicit activation, while actual hosting, HTTPS, protected operator configuration, the approved Windows gameplay worker and end-to-end device acceptance remain release work. `HOTR_BACKEND_MODE` accepts `local` or `staging`; production activation fails explicitly. Configuration alone does not certify or enable a live deployment.

## API and authority boundaries

This retained reward-only reference predates the current replay broker and
managed-account integration. Its missing-verifier/client-integration statements
describe that earlier checkpoint, not the current status at the top of this file.

The credential-free contract is [OpenAPI.json](../Verification/Evidence/Backend/OpenAPI.json). Browser documentation is disabled rather than loading a third-party UI. Requests are capped at 64 KiB, event batches at 100, receipt pages at 100 and authenticated credentials at 120 requests per server minute. Error responses omit request bodies, credentials and internal exception details. Access logging, proxy-header trust and cross-origin browser access are not enabled by the launch command.

| Endpoint | Behavior |
| --- | --- |
| `GET /v1/time` | Authenticated server UTC/day, with a persisted backward-clock guard |
| `GET /v1/me` | Server identity, verified completed count and **reward-credit totals**, not a full gameplay wallet |
| `GET /v1/daily-gift/offer` | One frozen offer per account/UTC day; approved seven-step cycle |
| `POST /v1/daily-gift/claim` | Validates issued quantities; commits receipt, credit and claim state together |
| `GET /v1/rewards?after=0&limit=100` | Durable authenticated recovery receipts with a stable pagination cursor |
| `GET /v1/wellworks` | Eligibility based on server-verified first clears |
| `POST /v1/wellworks/claim` | One permanent receipt per approved milestone |
| `GET /v1/rain-cup` | Server-timed **practice** state, explicitly simulated rivals and final rank |
| `POST /v1/rain-cup/join` | Manual 48-hour practice join after ten verified clears |
| `POST /v1/rain-cup/claim` | One frozen finishing prize, no claim expiry |
| `POST /v1/audit-events` | Idempotent explicit diagnostics, stored as **client_reported**, never rewarded |
| `POST /internal/v1/verified-first-clear` | Separate verifier credential; ordered first-clear acceptance contract |

A player token cannot call the verifier endpoint. The supplied service **does not implement a gameplay replay verifier**: it trusts the separately provisioned upstream verifier. A proof digest records that verifier's accepted evidence; it is not independently checked by this service. Test fixtures use privileged simulated first clears. Until a real verifier is connected, ordinary gameplay cannot unlock server Wellworks or score server Cup points. Accepted verifier requests use server observation time; the backend cannot yet preserve an offline win's original deadline through later verification. The checkpoint81 server attempt API below now reserves and settles attempts; exact playable-board resume and a real gameplay replay verifier remain separate work.

Rain Cup retains the owner-approved practice rules and four scripted rivals. Moving its clock and receipts to the server does not turn it into real competition. Matchmaking, real leaderboards and production score validation remain absent. The new server attempt table blocks a conflicting server Cup join. Existing local attempts stay in the ordinary Unity profile until an approved adapter/migration is connected; those local guards remain unchanged.

`rewardTotals` deliberately remains an issuance audit excluding genesis, purchases and spending; it is not a balance. Checkpoint81 projects trusted reward/purchase receipts into the new staging server wallet and implements typed spending there. Neither view replaces an ordinary Unity profile automatically. Existing local development rewards are not imported or regranted. Normal client synchronization, authenticated guest/account linking, merge/deletion/recovery and cloud profile migration are not implemented.

## Existing reward transport (earlier checkpoints, retained)

`BackendClient.cs` uses asynchronous UnityWebRequest coroutines with explicit endpoint/credential configuration, a timeout, redirects disabled and HTTPS required. Only Editor/development callers can explicitly permit loopback HTTP. Credentials stay in memory; no endpoint or token is embedded in an asset or player preference.

`BackendGiftSession.cs` checks the server account identity before issuing a claim. It uses a cache bridge around the established `DailyGiftService`: durable local intent, asynchronous HTTP, validation of the confirmed receipt, then the existing idempotent local credit transaction. A failed intent save cannot grant a remote gift; loss of remote or local confirmation can be retried. Bad authentication preserves pending intent. Account mismatch fails before making a remote claim. Receipt pagination is exposed for future recovery; automatic ordinary-profile restoration is not enabled.

These are explicit adapters. The ordinary `PlayerProfileHost` factory and existing synchronous modal are unchanged, and no background diagnostic upload is installed. The native HTTP suite drives the adapters with isolated file profiles; it is not a connected production UI or Android deployment. A hosted endpoint, identity storage and asynchronous page integration must be reviewed before normal players switch services.

The subsequent source checkpoint in `32_BACKEND_DAILY_GIFT_UI_REVIEW.md` connects the existing Daily Gift modal asynchronously for **explicit isolated Editor/development review profiles**. Loading, retry, close/reopen, late responses, saved claims and process restart are exercised against this real service. Ordinary profiles still use the existing factory; release selection, account migration and Android integration remain open. The review helper's `--gift-ui` option provisions a separate UI account and enables file-controlled delay/503/lost-response fixtures inside ignored storage. Those controls are absent from `create_app` and the regular local launcher; there are no HTTP fault endpoints. Run `Verification/Run-BackendGiftUI.ps1` for the expanded native/UI suite.

## Earlier verification workflow (retained)

Run `powershell -NoProfile -ExecutionPolicy Bypass -File Verification/Run-BackendVerification.ps1` from the root. It runs Python service tests, starts a separate hidden loopback HTTP process, provisions isolated accounts into ignored local files, runs actual native Unity HTTP and compatibility checks, restarts the server against the same database and verifies receipts through authenticated HTTP. The helper is stopped in cleanup. It never clears or migrates ordinary Unity/LDPlayer profiles. No verifier credential enters Unity.

Evidence is `Verification/Evidence/Backend`; the branch summary distinguishes service/ASGI tests, native Unity HTTP, native compatibility and actual process restart. Earlier component reports are restored after fresh compatibility copies are saved. This checkpoint does not rebuild/install an APK, certify Android TLS/network behavior, perform physical-device testing or deploy to a cloud account.

Hosting/database operations, managed identity, secure client credential storage, approved migration/recovery, gameplay verification, production privacy/retention/consent and live competition remain explicit integrations. The current limits and clock guard are engineering controls for staging, not a production security, availability or power-loss certification. Journals are not compacted and no retention policy is invented.

## RuStore commerce receipts (checkpoint81)

The additive schema1-to-2 commerce migration preserves existing accounts, credentials, rewards and command receipts. Schema3 then adds the staging server wallet described below. Commerce tables retain immutable server-created orders, unverified invoice requests, one confirmed receipt per invoice/purchase/order and a durable delivery marker. A new confirmation projects into the server wallet atomically; it does not alter the issuance-only `reward_totals` or any Unity local profile. Future schema versions fail closed; additive schema changes use the existing atomic SQLite transaction.

`config/commerce.json` is versioned and disabled: no Console app ID, product IDs, prices or live credentials are supplied. An operator can configure a disposable sandbox catalog for integration review. Even an enabled catalog cannot activate live payments: non-sandbox order creation/reconciliation is explicitly blocked until normal Unity wallet/identity production integrations are implemented. The legacy `/v1/me` issuance view continues to report `purchaseFulfillment: false` and `balanceScope: reward_credits_only`; current server balance/capabilities are exposed separately by `/v1/wallet` and the commerce catalog.

All new routes require the existing player bearer credential:

| Endpoint | Behavior |
| --- | --- |
| `GET /v1/commerce/catalog` | Read-only configured sandbox capability and product mapping; disabled by default |
| `POST /v1/commerce/orders` | Idempotent `{commandId, productId}`; freezes the server catalog version, product, one-pack quantity, amount/currency, player and random order binding before payment |
| `GET /v1/commerce/orders/{orderId}` | Only that authenticated player's order, committed credit, pending invoice verification and delivery marker |
| `POST /v1/commerce/orders/{orderId}/reconcile` | Accepts only `{invoiceId}`; queries the server provider and compares every binding before one atomic confirmed credit |
| `GET /v1/commerce/credits?after=0&limit=100` | Recoverable paginated **commerce receipt audit**, not a current balance; `/v1/wallet` exposes spendable server funds |

The SDK purchase must use the exact returned `sdk.orderId`, `sdk.productId`, `sdk.appUserId`, `sdk.developerPayload`, sandbox environment and quantity1. The backend compares provider-returned app ID, invoice ID, purchase UUID, order, store item code, player, random binding, amount and currency. It never trusts callback status/price/quantity or a client-provided coin grant. The v2 invoice API does not document a quantity field; this implementation restricts fulfillment to one preconfigured pack and exact captured total, and does not invent or multiply a verified quantity. Discounts/price changes need a separately approved pricing policy; outstanding orders retain their original terms.

`RuStoreInvoiceProvider` implements bounded HTTPS GET requests to the official Pay v2 invoice endpoint. The RSA/JWE supplier below is wired only for an explicitly enabled server catalog and both server-only secret references; the unconfigured default remains unavailable. Requests reject redirects, ignore environment proxies, have a10-second timeout and cap response bodies at64KiB. Only necessary normalized fields survive; card/payment-info objects and credentials are not recorded. Secret provisioning/operations, a public authenticated notification receiver and durable background reconciliation remain deployment work.

Only `CONFIRMED` can create credit. `PAID` is a hold and stays `Held`; cancellation, rejection, reversal and pre-credit refund create no credit. Confirmation and the `Pending` delivery marker commit together. SDK delivery acknowledgement should follow a committed receipt, then a fresh provider lookup can substantiate `ACKNOWLEDGED`; a client boolean cannot mark it delivered. Repeated callbacks, an unknown HTTP outcome and a process restart cannot grant twice. Provider queries happen outside database write locks. A rejected unverified invoice does not reserve its global invoice ID and cannot block its actual owner's order.

Any verified refund/reversal puts the order in sticky `RefundReview`, even before credit. Later held/created/confirmed observations and a delayed older confirmation cannot clear that quarantine or create a first credit. An already-created credit is retained for review rather than silently erased/regranted. An actual staging server wallet and typed spending now exist, as described below. A real refund/debt policy, trusted gameplay verifier, normal Unity wallet integration, guest identity/recovery, deletion/retention, authenticated encrypted RuStore notifications and final SDK/store sandbox acceptance remain required. Do not wire a commerce credit directly to local `ProfileService.Grant` and call it server-authoritative currency. No real purchase or remote service has been exercised by the service tests.

Run the expanded service tests without overwriting the historical backend report:

```powershell
Backend/.venv/Scripts/python.exe -B Backend/tools/run_tests.py --out .verification-cache/RuStore81/BackendTests
```

The new tests use temporary real SQLite databases and ASGI requests, synthetic provider outcomes and a mocked HTTP transport. They cover migration rollback, unchanged old rewards, ownership/binding rejection, replay/concurrency, before/after-commit faults, restart recovery, pending acknowledgement, held/cancelled/refunded states, overflow, no network-held write lock, and disabled live payments. These are Python/ASGI/transaction tests, not native Unity, Android or live RuStore payment verification.

## Checkpoint81 staging wallet and attempts (historical boundary)

This section retains the original staging-wallet contract. Statements about
missing public onboarding or ordinary-client selection belong to checkpoint81;
the current managed-account and connected-app implementation is summarized above.

Schema3 adds an actual server wallet/inventory and immutable revisioned ledger, rather than asking the Unity client to add up purchase credits. New operator-provisioned **player** profiles receive the approved genesis once: 1,250 coins, zero stars, five lives, starting items `[5,5,3,2]` and tools `[3,3,3,3]`. Reissuing a credential for the same ID never resets/grants it. There is no public registration, arbitrary credit, balance import, seed/config override or reset route. This is not managed guest onboarding, recovery or linked identity.

Existing schema1/2 server accounts backfill **only their trusted individual reward/purchase receipts** into unique ledger origins. Their aggregate `reward_totals` is not taken as independent evidence, no starting balance is invented, and they remain `initialized:false`/nonspendable pending an approved operator migration. No Unity local profile is read, copied, replaced or silently merged. Restarting replays each origin without crediting twice. Future schema versions still fail closed.

Daily Gift, Wellworks, practice Rain Cup and first-clear rewards project into the same coin/star/item balances in the receipt transaction. A matched `CONFIRMED` RuStore purchase projects its configured coins in the **same transaction** as the commerce credit and delivery marker. Either all commit or none do. `PAID` and unverified input never credit. Sticky refund/reversal evidence blocks wallet spending; existing receipts are retained for operator review. There is no invented automatic refund/debt policy and no live payment activation. The commerce credit view is an issuance audit; use `/v1/wallet` for current spendable server balances and its `refundReviewRequired` flag. An order exposes `balanceScope:server_wallet` and canonical `availableToSpend:true` only after a durable confirmed credit in an initialized, nonquarantined server wallet. `normalUnityProfileIntegrated:false` and `localProfileMutated:false` remain explicit; no automatic normal-profile grant is implied.

| Endpoint | Staging contract |
| --- | --- |
| `GET /v1/wallet` | Identity, initialized state, revision, coins/stars/lives/items, trusted progression, active attempt; server UTC regeneration at one life per1,800 seconds |
| `GET /v1/wallet/ledger` | Immutable ordered origins/deltas/revisions with bounded signed64 pagination |
| `POST /v1/attempts/reserve` | `{commandId,expectedRevision,level,starting[4]}`; one active attempt and stock/life/unlock checks |
| `POST /v1/attempts/{id}/start` | Commits selected starting stock once, without charging a life |
| `POST /v1/attempts/{id}/quit` | Cancels an unstarted reservation for free; started/continuation attempts lose one life once |
| `POST /v1/attempts/{id}/tools` | Typed tool index0..3, one stock debit per idempotent command; no arbitrary amount |
| `POST /v1/attempts/{id}/continue` | Only after trusted `OutOfMoves`:900 coins for five additional moves; repeatable on subsequent exhaustions |
| `POST /v1/wallet/refill` | At zero lives and without an active attempt:900 coins restores all five lives |
| `GET /v1/attempts/{id}` | Owner-only durable attempt and authorized move allowance |
| `POST /internal/v1/attempts/settle` | Separate verifier token: `{commandId,expectedRevision,playerId,attemptId,outcome,proofDigest}` |

The attempt ID and salted SHA256 refill seed are server-generated using the current Unity `AttemptSeed` policy. `config/levels.json` captures the exact approved50 M47 file hashes, goals, initial move allowances and50-coin/one-star first-clear reward. No client-selected board/config/seed/reward is accepted. `attempt.moves` is the **total authorized allowance**, not a client-reported remaining-moves counter. Reservation/start/settlement/spend receipts bind the command payload and expected wallet revision; exact retries recover the original committed response even after restart or a lost reply. Fetch the wallet again for a newer revision. A changed payload under the same command ID is a conflict.

Trusted outcomes are `Won`, `OutOfMoves`, `Lost` or `Fault`. A verified first win commits reward, progression, Cup contribution and settlement atomically; replays grant no first-clear reward. A final-move win must be classified as `Won` by the upstream verifier, not `OutOfMoves`; the service does **not** derive that from a client declaration or validate a board replay. `OutOfMoves` preserves the attempt/life until continuing or quitting. Engine `Fault` releases selected starting items without charging a life; previously spent tools remain spent. One active server attempt prevents a conflicting practice Cup join. The original privileged first-clear contract remains a trusted legacy adapter and does not manufacture missing historical gameplay rewards.

This contract persists the attempt and purchase receipts, **not an exact playable board**. The normal Unity lifecycle's interruption-on-reopen and Continue/Shop board journal are not automatically replaced by this API. A transport must reconcile durable command outcomes before resuming or quitting. Existing local Daily Gift adapters must not project a new server wallet credit a second time into a normal local profile. Production mode, real gameplay verification, normal client selection, hosting/HTTPS, secure guest/account recovery, deletion/retention, refund resolution, authenticated callbacks and real RuStore sandbox acceptance remain open. Sandbox credits are deliberately spendable in this isolated staging economy; never promote its database/balances into live production without environment isolation and an approved migration. Python/ASGI/SQLite tests do not certify these integrations or an Android payment.

## Server-only RuStore authentication

`RuStoreTokenSupplier` implements the official Public API authentication request using SHA512withRSA over the Console key ID plus an explicit UTC timestamp. Its fixed HTTPS request returns a bounded JWE with a monotonic cache shorter than the provider's at-most900-second TTL. Concurrent callers share the refresh lock; an expired/failed refresh does not return a stale token. Invoice401/403 invalidates the cache for the next request, without treating an unknown response as payment success. No real Console/key/endpoint configuration is present in this project.

To enable a disposable **sandbox** deployment, an operator must first provide an enabled server catalog with real Console app/product/price mappings, then set both `HOTR_RUSTORE_KEY_ID` and `HOTR_RUSTORE_PRIVATE_KEY_FILE` in the server process environment. The latter is a reference to a private RSA PEM or base64DER secret file, **not key content**. Keep it outside the repository and web root, restricted to the service account; use deployment secret storage, backup and rotation procedures. The application reads it only when refreshing the authentication token. Never put a private key or server JWE in Unity, PlayerPrefs, assets, source, screenshots or test reports. Partial environment configuration fails startup; disabled default catalog does not load a secret. Rotating the file is picked up at the next token refresh; restart/invalidate the supplier to force immediate refresh.

The server credential is separate from the public Console app ID/SKU/deeplink settings supplied to Unity. A configured provider still cannot create/reconcile live orders: the explicit production/client integration gate remains. Authentication tests use ephemeral RSA keys and mocked HTTPS, while invoice tests use synthetic verified responses; neither proves real store acceptance. Authenticated encrypted notification ingestion, durable asynchronous reconciliation/ack workers and live deployment operations remain separate work.

Official contracts: [Pay Unity SDK](https://www.rustore.ru/help/en/sdk/pay/unity/11-1-0), [v2 invoice lookup](https://www.rustore.ru/help/en/work-with-rustore-api/api-subscription-payment/v2-purchase-invoiceid), [Public API authentication](https://www.rustore.ru/help/work-with-rustore-api/api-authorization-token). Pay uses invoice IDs and separate payment/delivery states; it must not be mixed with deprecated BillingClient consumption semantics.

The ASGI launch follows [FastAPI's server documentation](https://fastapi.tiangolo.com/deployment/manually/). Local claim serialization uses explicit SQLite transactions; see [SQLite transaction behavior](https://www.sqlite.org/lang_transaction.html). Actual project test results, rather than those documentation pages, establish this implementation's verification scope.


## Rewarded Shop video (checkpoint85)

Schema 7 adds durable rewarded-ad opportunities, command results and receipts.
`config/ads.json` defaults disabled. The approved policy is 400 coins, three
credits per player-local day, with 600 seconds after each credit. The server
persists an IANA timezone or offset; travel changes wait for the current quota
window, and UTC+10 is only the compatibility fallback for older clients. Reservations,
no fill and cancellation do not spend quota; the cooldown survives midnight.
Authenticated routes under `/v1/ads/rewarded` provide `status`, `reserve`,
opportunity reads, `client-completion`, `claim` and `cancel`. Claims atomically
credit the authoritative wallet and are idempotent across retries/processes.
Account deletion/revocation/refund quarantine remain enforced. Backups include
the additive tables and restore validates their existence.

This integration has no authenticated Yandex server-side completion adapter. The selected explicit mode is
`sdk_client_reported_capped`; reports do not grant coins, and claim receipts
retain `completionAuthoritative=false` and the client-reported source. Modified
authenticated clients can falsely report viewing up to the fixed server cap;
this is a documented limited-trust monetization decision, not provider proof.
There is no public trusted grant/webhook route. The separate trusted-completion
seam and synthetic in-process local/staging verifier do not change that claim.

The owned staging launcher accepts optional `rewardedAdsEnabled` (omitted means
`false`). Public ad-unit IDs do not enable it. For an existing root, stop the
service and run `python -B -m hotr_backend.staging105 configure-rewarded-ads --manifest <reviewed-descriptor>` from `Backend`. The command takes the runtime
and control locks and atomically switches only the exact known owned ad policy.
Preflight/start reject descriptor-policy mismatches. Ownership, database,
pending claims, quota and receipts are preserved; commerce and production stay
disabled. Backup/restore retain the explicit policy selection and pending rows.
This opt-in still uses capped client reports and does not prove an impression,
enable a public verification webhook or establish live SDK/provider acceptance.

The 357-test service run includes 33 new ad tests and the real approved Windows
Unity replay-worker integration. Its exact inputs are archived under
`Verification/Evidence/ShopAds85/Backend/Inputs`; subsequent documentation edits
do not change executable verification. Native transport/UI/SDK checks have
separate scope. Publisher registration and full deployment/payment/privacy
configuration remain open. See `Release/Advertising/README.md`.

## Service runtime, review 136

The owned launchers pass `service_runtime=True`. That starts first-come verification dispatch (`ReplayBroker`), batched retention (`runtime136.Retention`, whose docstring lists exactly what is pruned and kept) and a counter line on the `hotr_backend.ops` logger when counts change, at most once a minute. These counters and `app.state.metrics136` hold no token, player ID or request content. Pure reads use `Database.read()`, a WAL snapshot that cannot write and does not wait for writers; writers queue in arrival order in `Database.transaction()`.

Objects prefixed `perf136_` are indexes and bookkeeping, created when the database opens. Schema validators ignore them and the schema version does not change, so a backend from before review 136 refuses the database until they are removed. `storage.remove_performance_objects` and `Release/RuStore/WindowsVps/Deploy136.ps1` do that on rollback.

An ordinary restart of the SDK launcher checks the schema only. The whole-file `quick_check` and foreign key check run in `staging_sdk126 preflight`, in backups and in restores.

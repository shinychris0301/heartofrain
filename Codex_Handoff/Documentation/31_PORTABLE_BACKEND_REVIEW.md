# Portable backend — local/staging foundation

21 October 2026. The owner approved building a portable backend first and choosing hosting afterward. This implements a runnable authority service and explicitly configured Unity HTTP adapters. It does not activate production services or migrate ordinary player profiles. The deployed Android APK remains the preceding Rain Cup build.

## Implemented behavior

`Backend/hotr_backend` provides a FastAPI/Uvicorn API over a durable SQLite database. Python 3.12 and all dependencies are pinned in `Backend/requirements.lock`; its virtual environment is separate from existing verification tools. No Unity engine/package upgrade, provider SDK or paid cloud resource is introduced. Windows local execution is verified; other hosting targets and PostgreSQL are not certified.

Operator-provisioned accounts use random expiring bearer credentials. The database stores credential digests, role, expiry and revocation state. Player and verifier scopes are separate. Credentials are never emitted to source, reports or console. The provisioning command writes only to a new ignored local file. There is no public account/credential issuer, profile import, balance mutation, clock-setting or reset route. Ordinary guest onboarding, managed identity and account recovery are not implemented.

The service observes its host's UTC and persists a high-water mark to prevent simple backward clock changes from reopening days or cups. This is server-controlled time, not a certified external clock authority; host time management belongs to deployment. Client times do not select gift days or backdate Cup contributions.

Daily Gift issues one frozen offer per account/UTC day. Requests must match its schedule, step and exact grant. Receipt, credit, day and next-cycle state commit in one database transaction. Stable command IDs bind their original payload; conflicting reuse fails. A claim whose response was lost remains recoverable after midnight. A new command for the same confirmed offer cannot grant again. Missed days preserve the next step. The seven approved provisional quantities are unchanged.

Wellworks has server eligibility and one permanent grant per approved 10/20/30/40/50 milestone. Server eligibility uses trusted-verifier first-clear records, not uploaded local profile totals. Already claimed milestones retain their saved grant when configuration changes.

Rain Cup has server-controlled practice joins, frozen 48-hour rules, scoring, expiry, final rank and one prize. The four rivals remain explicitly simulated. Ties share rank, claims do not expire, replays cannot score and all fifty first clears exhaust joining. Server time and durable receipts do not turn practice into real competition. Matchmaking, real players and leaderboards are not implemented.

The first-clear route accepts only a separately provisioned verifier credential. It binds an attempt key, next level and proof digest, then records progression and one eligible Cup point atomically. **This is a verifier acceptance contract, not an implementation of board replay/proof verification.** Privileged test fixtures supply those records. The Unity app never receives a verifier credential. Ordinary player tokens and self-reported telemetry cannot advance server progression. A real gameplay verifier and server attempt reservation/settlement still need implementation before live eligibility/scoring. Deferred verification currently uses server acceptance time; preserving an offline win's earlier event deadline is not implemented. The backend does not yet know active local attempt reservations.

The reward ledger stores issued Daily Gift, Wellworks and Cup grants with recoverable, paginated receipts. Its numeric totals are explicitly **reward credits only**. They are not a full wallet: starting balances, gameplay debits, campaign income, purchases, refunds and local development rewards are not silently imported or overwritten. Full wallet/account reconciliation needs an approved migration and recovery policy.

Explicit diagnostic batches use the preceding audit schema and stable IDs. Ingestion is authenticated, profile-stream-bound, schema-validated, conflict-detecting and atomic per batch. Every row is marked `client_reported`. Even a well-formed reported win or reward event cannot grant currency, unlock Wellworks or score a Cup point. No automatic audit sender or real-player data upload is installed.

Requests, batches, pagination and authenticated request rate are bounded. SQL parameters, explicit immediate transactions, foreign keys, unique receipt/command constraints, WAL and full synchronization protect the tested transaction paths. Responses omit submitted invalid input and internal error details. Unknown/corrupt database schemas fail without reset. There is no destructive schema upgrade or invented retention policy. Single-host durability, backup/restore, capacity, availability, security and physical power-loss certification remain deployment work.

## Unity behavior and isolation

`BackendClient.cs` is an asynchronous UnityWebRequest transport with no default origin or token. HTTPS is required; explicit loopback HTTP is permitted only in Editor/development builds. Redirects are disabled and credentials are kept in memory rather than serialized assets/preferences or logs. Requests have a timeout. The service never runs synchronously on a gameplay frame.

`BackendGiftSession.cs` verifies the server account identity before a claim. It bridges asynchronous HTTP into the existing `DailyGiftService` model: save pending intent, send request, validate server identity/receipt/quantities, then commit the existing idempotent local grant. Failed intent persistence cannot produce a remote credit. Lost remote confirmation, lost local credit confirmation, bad authentication and recreated sessions preserve or reconcile the original intent. A profile/account mismatch fails before a remote claim. Existing model settlement code is unchanged.

The ordinary `PlayerProfileHost`, Daily Gift modal, Wellworks/Cup pages and their factories are unchanged. The new adapters are explicitly driven by the native HTTP suite with isolated file profiles. There is no automatic server selection, production modal integration, credential storage, profile migration or APK deployment. That separation is necessary while hosting and identity/migration policy are unselected; it is not a claim that normal players already use the service.

## Files and operation

The runnable package is `Backend/`: API, strict schemas, SQLite storage, domain authority, operator CLI, approved configuration copies, locked dependencies, local launcher, tests and fixture/restart/schema tools. See `Backend/README.md` for commands, route table and integration boundaries. Local credentials/database/environment are ignored by `.gitignore`.

Unity adds only `App/Profile/Runtime/BackendClient.cs` and `BackendGiftSession.cs`, with new metadata. Native execution adds `Verification/Editor/BackendHttpVerification.cs` and metadata. All existing player inputs, including artwork, GUIDs, levels, gameplay and the ordinary host, match the preceding event-audit source checkpoint.

`Verification/Run-UnityVerification.ps1` adds the native HTTP entry point. `Run-BackendVerification.ps1` starts a separate hidden loopback server, creates isolated credentials, runs service/native suites, restarts the server against the same database and stops it in cleanup. Fresh compatibility reports are retained under this branch while historical component reports are restored. No ordinary profile, LDPlayer app data or preference is cleared or migrated.

`collect_backend_results.py` validates frozen backend/runtime/native inputs, fresh process/report identities, source boundaries, integrity, contract and absence of actual fixture tokens from exported sources/evidence. Its own collection-tool hash is recorded separately from the tested inputs. The general collector selects this source checkpoint first. `Verification/Evidence/Native_Source_Checkpoint.json` identifies the new source result separately from the preceding Android summary and its original APK scope.

Repeat verification from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Verification/Run-BackendVerification.ps1
.venv/Scripts/python.exe -X utf8 Verification/Tools/collect_results.py
```

Evidence is `Verification/Evidence/Backend`. `Service_Tests.json` is Python service/ASGI and SQLite execution, not Unity. `Native_HTTP_Checks.json` is actual Unity 2022.3.62f3 coroutine execution over HTTP to a separate Uvicorn process, not a fake transport or UI/device test. `HTTP_Process_Restart.json` records actual process stop/restart and authenticated recovery. `Native_Checkpoints` contains fresh compatibility suites. `OpenAPI.json`, source hashes, changed-input inventory and static integrity are separate artifacts. `Verification_Summary.json` is the final authoritative result.

Final result: **23 backend scenarios pass; all ten native suites pass with 35,515 custom assertions/checks; six authenticated real-HTTP checks pass after a server process restart.** The new native HTTP suite contributes 24 checks. Compatibility comprises the preceding event audit (478), connected audit (13), profile transactions (10,099), Rain Cup (13,227), connected Cup (34), connected Daily Gift (51), Wellworks (11,046), connected Wellworks (13) and general project checks (530). These are custom assertions, not 35,515 independent natural-play scenarios. The service scenario count and six restart checks are separate from the native total.

All **4,459 Unity assets/metadata and 19 backend source/config/lock files** match their tested frozen inputs. All **4,319 preceding player inputs are unchanged**; four are added for the two runtime scripts and metadata, giving 4,323 player inputs. One Editor suite and metadata are also added. Static GUID/reference/resource/art integrity passes with no unexpected original changes. Actual fixture tokens are checked against exported source/evidence and none appear. The collector's final hash and its earlier freeze hash are both recorded; collection-tool repairs do not replace tested runtime/backend hashes or reclassify Python checks as Unity execution.

The APK remains SHA-256 `c9e3928c5ae91aacaa047374550bf1f2ac532ab81c3e8039d0e52b554c1fc018`. No new build/install, Android networking test, ordinary-profile migration or physical-device observation is inferred from that file hash. The isolated server process is stopped by the verification wrapper; use `Backend/Run-Local.ps1` to start the regular local service when needed.

The native HTTP checks cover authenticated time, endpoint restrictions, approved offer, failed local intent, lost local credit confirmation, recreated sessions, durable receipt recovery, actual audit payload ingestion/resend, refusal to trust client wins, lost remote confirmation, authentication failure, profile/account mismatch and cross-player stream isolation. Service scenarios additionally cover 24 concurrent distinct-command claims producing one credit, every approved gift/milestone/Cup reward, UTC boundaries, old confirmation recovery, frozen config, key conflicts, overflow rollback, verifier scope/proof binding, event batch rollback, malformed/oversized input, credential expiry/revocation/rate limits, future/corrupt database rejection and disabled production activation. Privileged first-clear fixtures do not establish natural-play balance or a functioning gameplay verifier.

## Remaining launch integrations

Hosting/HTTPS and service operations; managed identity/onboarding, secure client credential storage and approved recovery/merge/deletion; full wallet/profile migration and synchronization; actual gameplay proof verification, server attempt settlement and offline deadline reconciliation; asynchronous normal-page service selection and Android network verification; real competition, commerce and production privacy/consent/retention remain open. Production mode intentionally cannot activate while those integrations are absent. Hosting was deliberately deferred by the owner; no cloud deployment or new APK is claimed.

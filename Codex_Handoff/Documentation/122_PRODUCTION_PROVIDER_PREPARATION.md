# Production provider preparation — 30 October 2026

The twelve registered products and supplied Yandex placements are accounted for.
Wellkeeper now uses `hotr_bundle_wellkeeper_c`; the other eleven IDs, full grants,
prices and purchase limits are preserved. Historical pending orders retain their
frozen terms. The existing HTTPS authority remains staging. Production support
is implemented and locally verified, with provider and release acceptance open.

The owner requested an explanation of the required materials. See
[WHY_THESE_INPUTS122.md](../../Release/Production122/WHY_THESE_INPUTS122.md):
RuStore's public application ID binds the store registration; VK's public app ID
enables optional VK authorization; public pages identify the actual operator and
support route; the private API signing key authorizes invoice verification and
bounded discovery; the separate notification key decrypts asynchronous payment
updates. Private contents remain server-only. The Android release keystore has a
separate purpose and is never replaced by either provider key.

## Implemented behavior and changed files

- `Backend/hotr_backend/production_runtime122.py` adds an explicitly owned,
  strict production lifecycle, immutable runtime permit, separate locks/DB,
  validated provider bindings and trusted notification ingress. Existing
  factories keep their staging/default-production guards. Narrow changes to
  identity, wallet, commerce, replay, ad and VK transports carry the explicit
  environment binding. Production cannot be enabled with an ambient flag alone.
- `production_ops122.py` adds exclusive operational leases, supervised
  reconciliation, bounded metrics, WAL-aware validated backups and permanent
  restore quarantine. `production_discovery122.py` covers lost client results
  plus lost notifications using bounded provider invoice listing. Discovery
  queues hints; fresh matching `CONFIRMED` evidence applies each grant once.
  Discovery currently requires pausing/resuming the reconciliation supervisor
  because they share the exclusive operations lease.
- The three RuStore API adapters now use the fixed origin in current Russian
  official documentation, `public-api-m.rustore.ru`. Test origins changed with
  them; no arbitrary-origin override or alternate-host fallback was added.
- `production_prepare122.py`, `payment_readiness122.py` and
  `provider_readiness122.py` generate/check disabled candidates with exact
  product, app, package, environment and public-resource contracts.
- Twenty Unity production-owned source files cover strict version-two packaged
  production profiles, explicit expected-environment propagation, checkout and
  recovery binding, and accurate release diagnostics. Seventeen existing source
  changes and three new files are inventoried by the native receipts. Source
  settings/art/GUIDs and the main Unity2022.3.62f3 baseline remain preserved.
- `Release/RuStore/commerce.example.json` and `bundles.pending.json` carry the
  corrected Wellkeeper SKU; `registered-products122.json` records owner-confirmed
  registration, while publication and the numeric app ID remain unknown.
- `Release/Production122/` contains disabled candidates, service/proxy templates,
  monitor/public-page/inactive-source installers, setup guidance and the detailed
  input rationale. `Backend/tools/run_tests.py` fixes shadowed test IDs and
  consistent parent/child import paths; no financial behavior changes there.

## Actual VPS changes and scope

`HOTRMonitor122` is installed as LocalService and runs every minute, with a
45-second limit and rotating local incident logs. All nine actual VPS checks
passed, including normal HTTPS, readiness, protected routes, backup metadata and
disk space. Same-host checks cannot report a total host outage from that host;
no external alert destination was requested.

The owner-authorized temporary pages are published at
`https://api.novamind-it.ru/privacy`, `/support` and `/terms`. Exact HTTPS response
bodies were verified from the VPS. They explicitly remain drafts awaiting the
actual operator/contact; no company, email or retention period was invented.
Independent external-browser acceptance and final legal content remain open.
The static routes are additive; the prior Caddy file was preserved. All 76
installed staging Python files and its manifest/owner marker stayed unchanged,
and both existing services continued running.

The separate inactive-source package was actually staged at 22:01 UTC: all 102
payload hashes were checked, including 83 tested modules and 95 total source
files. Python3.14.10, all 19 locked dependencies, interpreter/configuration
hashes and syntax passed. The new runtime was not executed. Its restricted
credentials directory remains empty; authority, database, active manifest and
production services remain absent. Existing staging pins stayed exact and all
nine monitor checks again passed. See
`Verification/Evidence/Review122/InactiveVps/InactiveVpsInstall122.json` and
`Release/Production122/InactiveVps/CURRENT_VPS_STATE122.txt`.

## Accepted verification

| Check | Accepted result | Scope |
| --- | --- | --- |
| Full backend, `Backend/Full05/Service_Tests.json` | 888 executed, zero failures/errors/skips; 167 inputs unchanged | Service/SQLite/ASGI/OS/process controls, including the separately enabled approved actual gameplay worker; no real payment/provider acceptance |
| Native client, `NativeClient/FinalClientSource122.json` | 4,047 assertions / 90 cases in five accepted invocations | Isolated Unity2022.3.62f3 Editor production, identity, checkout, configuration and RuStore suites |
| Independent native freshness, `FinalMainFreshness122.json` | All 20 owned source files and 3,153 sealed GUIDs exact | Newer unrelated main edits are preserved and excluded from certification |
| Preparation/provider/monitor controls, `FinalControls122_03.json` | 45 pass, stable input pins | Disabled candidate/reader/monitor checks, including disposable HTTP |
| Production lifecycle compatibility | 278 pass | Scripted provider plus actual transactions/ownership/locks, source-bound |
| Discovery and fixed-origin compatibility | 174 pass | Scripted provider HTTP and actual SQLite, source-bound |
| Operations and real isolated Caddy | 20 pass | Actual local proxy/OS/SQLite controls, scripted provider/worker factories |
| Inactive artifact controls | 13 pass | Archive completeness, source binding and restricted installer checks |

Focused backend counts overlap the full suite and must not be added. Earlier
failed native epochs, Full03/Full04 harness failures and the rejected packaging
attempts remain retained. The Starlette test-client deprecation remains recorded;
no dependency/engine/SDK upgrade was introduced. Native vendor SDK conditional
branches are unchanged from earlier actual compile evidence, not freshly compiled
by this review. No final release APK, Android install, real checkout, VK consent,
ad impression, production-authority initialization or cutover is claimed.

## Remaining sequence

1. Record the real numeric RuStore and VK app IDs and final registered Android
   package, payment-return scheme, release certificate fingerprint and version.
   Provision the API key ID and the two server-only private files. Keep private
   contents, tokens and signing passwords out of chat/source/logs.
2. Replace temporary page content with factual operator/support details and
   review the actual privacy/data-provider practices and purchase terms.
3. Qualify the separate Windows production runtime and approved verifier against
   the active campaign. Configure trusted notification ingress and supervised
   recovery; test Console notification delivery before enabling it.
4. Rehearse restore/quarantine, encrypted off-host backup and reboot persistence.
   A fresh backup timestamp alone proves neither integrity nor recoverability.
5. Test all twelve actual sandbox purchases and interrupted/duplicate/bank-return
   recovery; exercise VK consent/cancel/restore/delete and real Android ads.
   Rewarded Shop limits remain 400 coins, three daily claims and 600 seconds.
   Yandex completion is client SDK reported; no server-view verification is
   available in this integration. Interstitial display behavior was not added.
6. Build and inspect the SDK-enabled signed release artifact, complete device and
   provider acceptance, then perform the separate production cutover. Actual
   credentials and provider/device acceptance remain outstanding.

Full setup: [Release/Production122/SETUP.md](../../Release/Production122/SETUP.md).
The evidence index is `Verification/Evidence/Review122/`; the final summary and
individual source-bound receipts define the accepted scope.

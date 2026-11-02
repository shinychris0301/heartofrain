# Provider and VPS preparation — 30 October 2026

The existing HTTPS backend at `https://api.novamind-it.ru` is **staging**.
This preparation does not turn it into a production payment authority. Live
checkout now has an explicitly bound production path in the app and backend.
Provider credentials, a qualified deployment and actual Android/provider
acceptance remain required. The prepared configuration reports those remaining
requirements.

## Items and rewards

The twelve owner-confirmed product mappings are recorded in
[registered-products122.json](../RuStore/registered-products122.json).
Wellkeeper now uses **`hotr_bundle_wellkeeper_c`**. Its internal offer ID remains
`wellkeeper`, with 2,000 coins, its original starting items/tools, 99 RUB and the
existing once-per-player limit. The other eleven mappings and all approved
grants/prices remain unchanged. Existing pending orders keep their original
frozen store IDs; do not edit database orders during this catalogue change.

The Yandex placement IDs remain `R-M-20291714-1` (rewarded) and
`R-M-20291714-2` (interstitial). Rewarded Shop ads retain 400 coins, three claims
per player-local day and a 600-second cooldown. No interstitial placement was
added. Yandex completion is SDK-reported and capped; it is not a server-verified
impression. See [VK/ad preparation](../Advertising/PROVIDER_PREPARATION122.txt).

## Reviewable configuration

[Candidate/deployment.plan.json](Candidate/deployment.plan.json) is a server
preparation plan, **not a runtime manifest**. Its production directory and port
are proposals separate from the current staging authority. Credential references
are empty; no secret was read or generated. The complete disabled twelve-item
catalogue, checkout, release and provider candidates are beside it. The separate
version-two `ManagedProduction.template.json` and `CheckoutProduction.template.json`
are the public packaged-client formats; `production-runtime.template.json` is
the private server-manifest template. They require the actual registered package,
string Console application ID, credential references and worker/configuration
hashes before use. Product
registration is owner-confirmed; publication and the Console application ID
remain unknown.

To prepare another fresh candidate from the repository root:

```powershell
Set-Location Backend
& .\.venv\Scripts\python.exe -B -m hotr_backend.production_prepare122 prepare --directory <NEW_DIRECTORY> --environment production
& .\.venv\Scripts\python.exe -B -m hotr_backend.production_prepare122 check --directory <NEW_DIRECTORY>
```

Supply `--app-id <ISSUED_NUMERIC_ID>` to preparation when the actual RuStore
application ID is available. Existing output directories are preserved. Check
exits nonzero while required configuration is missing. A consistent candidate
still does not activate providers or certify live acceptance. Do not package the
server plan, provider keys or private operator files in Unity `Assets`.

The payment-specific check also compares actual Console observations with the
approved prices, consumable types, full grants, publication state and purchase
limits. See [payment setup](../RuStore/PRODUCTION_PAYMENTS122.md). Its normalized
inventory is an operator-maintained observation, not a native Console export or
a signed provider receipt.

## Windows checks and local incident logs

The owner selected one-minute Windows checks and local logs. The standalone
monitor can be deployed without replacing the installed backend source or
modifying its authority, service definitions or Caddy configuration. The fresh
`HOTRMonitor122` task uses LocalService, restricted code/status permissions and
a 45-second execution limit. It checks verified HTTPS, loopback health/readiness,
latency, protected routes and optionally owned backup metadata/disk space.
Sanitized incident logs rotate at four files of 256 KiB; repeated healthy states
are omitted. See [installation and verification](monitoring/SETUP122.txt).

The task was installed on the VPS and produced a healthy report: all nine
requested checks passed, including backup metadata and disk space. Its source
hash matches the reviewed monitor; LocalService, the 45-second task limit and
local event log were observed. The staging manifest and owner marker stayed
byte-identical, with both existing services running. The actual receipts are
`Monitoring/VpsInstall122.json` and `Monitoring/VpsObservation01_122.json` under
the Review122 evidence directory. The development PC's public probe cannot reach the
endpoint; this is consistent with the previously recorded egress concern and
does not prove that the VPS is down. A same-host monitor also cannot report a
complete host/network outage while that host is unavailable. External alerting
was not requested for this stage.

## Actual inactive production source deployment

The accepted Full05 source package was staged and verified on the VPS at
22:01 UTC on 30 October. `C:\Apps\HeartOfTheRain\Production122\Backend`
contains all 83 tested runtime modules. All 102 package files were checked against
their reviewed hashes. `C:\ProgramData\HeartOfTheRain\production-services`
contains disabled/incomplete configuration and manual service examples;
`C:\ProgramData\HeartOfTheRain\production-secrets` is restricted and empty.
Python3.14.10, the pinned launcher/base/configuration, all 19 locked dependencies
and syntax checks passed before installation. The new runtime was not executed.

The existing staging source, authority and Caddy hashes stayed unchanged, both
old services were running, and the monitor again passed all nine checks. No
production authority/database, active manifest, key files or production services
were created. See [current VPS state](InactiveVps/CURRENT_VPS_STATE122.txt) and
`InactiveVps/InactiveVpsInstall122.json` in the Review122 evidence directory.

## Remaining inputs and engineering

1. Record the issued numeric RuStore application ID, numeric VK application ID,
   actual registered Android package/payment-return scheme, release certificate
   fingerprint and version code. Finalize the published temporary privacy,
   support and terms pages with the actual operator and a working support contact.
   Keep provider key contents and signing passwords outside chat/source.
2. Provision the server-only `HOTR_RUSTORE_KEY_ID`,
   `HOTR_RUSTORE_PRIVATE_KEY_FILE` and
   `HOTR_RUSTORE_NOTIFICATION_KEY_FILE`. Register the exact VK callback
   `https://api.novamind-it.ru/v1/identity/vk/callback`.
3. Configure and qualify the new separately owned production launcher/lifecycle
   and packaged production client. The ordinary staging factory still rejects
   an ambient production toggle. Use the strict
   `Release/RuStore/production-runtime.example122.json` contract and the new
   `production_runtime122` CLI. Setting `HOTR_BACKEND_MODE=production` alone is
   not a supported activation procedure.
4. Establish trusted payment notification ingress and a supervised reconciliation
   worker. Current Caddy forwarding plus `proxy_headers=False` makes every
   request appear to be loopback. Adding loopback to RuStore sender networks
   would remove sender validation. The new production Caddy template overwrites
   `X-Hotr-Verified-Client-IP` from the real peer; the dedicated runtime validates
   that trusted hop and the provider CIDRs. Review the actual deployed topology
   before enabling notifications. Existing staging forwarding is unchanged.
5. Deploy and qualify the approved Windows gameplay verifier against the active
   campaign. Keep staging/production authorities separate. Rehearse encrypted
   off-host backup/restore and reboot persistence; metadata freshness is not a
   restore or integrity test.
6. Exercise actual sandbox purchases for all twelve items, duplicate and lost
   responses, bank return, process termination, recovery, acknowledgement and
   refund review. Exercise real VK consent/cancel/restore/delete and real ad
   completion/cancel/restart/cap boundaries in the configured Android app.
   Existing synthetic provider tests remain useful but do not replace these.
7. Complete the release signer and SDK-enabled ARM64 production build, inspect
   packaging and provider configuration, then perform the production cutover.
   No final release APK was compiled by this preparation.

## Recorded validation

The accepted full backend run is
`Backend/Full05/Service_Tests.json`: **888 tests executed**, zero failures,
errors or skips, including the approved actual gameplay verifier. All 167
source inputs stayed unchanged during the run and matched the final check.
Earlier Full03/Full04 failures are retained: the reporting harness needed
stable test identities and consistent parent/child import paths; the accepted
rerun contains those narrow fixes.

Payment configuration, actual SQLite grant/recovery, AES-GCM notification,
RSA-authentication, Windows restart and pricing suites passed **125 tests**.
The ad/VK backend suites passed **111 tests** with simulated provider HTTP.
The final preparation/provider/monitor controls passed **45 tests** with stable
source inputs (`Preparation/FinalControls122_03.json`). Six existing
readiness/Windows-generator tests also passed in the monitor review. The
production lifecycle compatibility suite passed 278 tests, discovery/fixed-origin
compatibility passed 174, and production operations/actual isolated Caddy passed
20; these overlap and must not be added as distinct backend coverage. Native
Unity 2022 production-client and affected regression checks passed **4,047
assertions across 90 cases** in an isolated source-bound project. Production-owned
main files match that tested snapshot; newer unrelated main paths remain
outside that certification (see `NativeClient/FinalMainFreshness122.json`).
Vendor conditional branches are unchanged from
their previous SDK compile evidence; no fresh SDK-enabled APK or Android/provider
acceptance is claimed. Earlier failed fixture/harness runs remain retained.

Evidence is under `Verification/Evidence/Review122/`; the final source-bound
preparation receipts and later full-backend/native receipts identify their exact
source epochs. Do not add repeated test runs to the distinct-test count.

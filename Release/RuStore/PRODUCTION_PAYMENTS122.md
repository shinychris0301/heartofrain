# Payment preparation after the VPS deployment

The owner subsequently selected **SDK checkout125**. Its current requirements
are in [sdk-checkout125/README.md](sdk-checkout125/README.md). That mode requires
no RuStore API key ID, private signing key or notification key. This document
retains the independently verified `provider_api` alternative and its original
operational requirements; use the SDK checklist for the selected mode.

30 October 2026. The deployed `api.novamind-it.ru` service is the controlled
staging authority described in [the VPS checkpoint](WindowsVps/DEPLOY.md).
It does not enable purchases merely by being reachable. Keep its existing
identity, wallets and pending transactions intact while preparing payment
configuration separately.

The approved twelve offers already have full server-side grants, frozen order
terms, stable-player eligibility, verified-invoice binding, atomic wallet
delivery and recovery. The owner has confirmed twelve registered consumable
product IDs in [registered-products122.json](registered-products122.json).
Publication status and the Console application ID are still unknown. Credential
provisioning, configured Android provider acceptance and a production runtime
remain required. The preparation tool makes those gaps explicit and never
activates checkout.

## Prepare the exact items

From `Backend`, using the project's locked virtual environment:

```powershell
.venv\Scripts\python.exe -B -m hotr_backend.payment_readiness122 prepare --output C:\HotrPrivate\payment-candidate --app-id <issued-numeric-console-id> --environment sandbox
```

The parent directory must already exist and the final directory must be new.
The tool refuses to overwrite any existing directory. It produces four public
configuration files, with every feature and item disabled:

| File | Purpose |
| --- | --- |
| `commerce.candidate.json` | Twelve approved server grant/price/eligibility definitions |
| `checkout.candidate.json` | Matching app-side Console ID and explicit environment |
| `console-inventory.template.json` | Operator-normalized observations to fill after inspecting Console |
| `console-products.csv` | Item-by-item registration and grant checklist |

The inventory template is a project checklist, not a native RuStore export or
proof of Console authenticity. It retains the owner's `registered:true`
confirmation and `published:null` until publication is checked. The current
registered IDs must match the approved catalogue and Console observations.
Rewards, prices and purchase limits remain the owner's approved definitions.

| Internal offer | Proposed store product | RUB | Coins | Each starting / each tool | Limit per player |
| --- | --- | ---: | ---: | --- | --- |
| `coins-1000` | `hotr_coins_1000` | 99 | 1,000 | 0 / 0 | Repeatable |
| `coins-5000` | `hotr_coins_5000` | 299 | 5,000 | 0 / 0 | Repeatable |
| `coins-10000` | `hotr_coins_10000` | 499 | 10,000 | 0 / 0 | Repeatable |
| `coins-25000` | `hotr_coins_25000` | 899 | 25,000 | 0 / 0 | Repeatable |
| `coins-50000` | `hotr_coins_50000` | 1,599 | 50,000 | 0 / 0 | Repeatable |
| `coins-100000` | `hotr_coins_100000` | 2,999 | 100,000 | 0 / 0 | Repeatable |
| `wellkeeper` | `hotr_bundle_wellkeeper_c` | 99 | 2,000 | 1 / 1 | Once |
| `rainy-day` | `hotr_bundle_rainy_day` | 199 | 3,500 | 2 / 2 | Once |
| `rainlight` | `hotr_bundle_rainlight` | 299 | 6,000 | 3 / 3 | Once |
| `village` | `hotr_bundle_village` | 399 | 5,000 | 3 / 2 | Repeatable |
| `festival` | `hotr_bundle_festival` | 599 | 10,000 | 6 / 4 | Repeatable |
| `keepers` | `hotr_bundle_keepers` | 999 | 25,000 | 12 / 8 | Repeatable |

Starting array order: Rocket, Bomb, Rainbow Orb, Golden Seeker. Tool order:
Hammer, Axe, Ram, Atlas. Story stars are never purchasable. The three Special
offers use durable server player/offer entitlements; they remain consumable
provider products with the once-per-player policy enforced by the game service.

The original `hotr_bundle_wellkeeper` was deleted after being created as a
nonconsumable product. All new candidate mappings use the registered consumable
`hotr_bundle_wellkeeper_c`; the internal offer remains `wellkeeper`. Existing
orders retain their original frozen SKU and terms. A callback for the deleted
SKU cannot satisfy a newly created order for the replacement product.

RuStore documents separate consumable/nonconsumable types. An unpublished
product can be bought in sandbox but is unavailable in production.
[Official product registration](https://www.rustore.ru/help/developers/monetization/create-paid-product-in-application).

## Bind credentials and notifications

1. Record the issued Console application ID, exact package, payment return
   scheme and public signing certificate fingerprint. Use the developer's
   release signer and secure backups; the current staging debug signer is not
   a production signing identity.
2. Provision `HOTR_RUSTORE_KEY_ID` and
   `HOTR_RUSTORE_PRIVATE_KEY_FILE` in restricted server/operator storage.
   Payment notification decryption uses the separate
   `HOTR_RUSTORE_NOTIFICATION_KEY_FILE`. Keep keys and tokens out of source,
   APKs, screenshots and logs. The read-only preparation tool never reads them.
3. Use a dedicated sandbox authority/configuration and callback path
   `/v1/commerce/notifications/rustore/sandbox`. Keep production data and
   `/v1/commerce/notifications/rustore/production` separate. Register real
   HTTPS receivers in Console and execute its delivery check before enabling
   that environment. [Official sandbox notification setup](https://www.rustore.ru/help/en/developers/monetization/payment-callback/pay-sandbox-notifications),
   [production notification setup](https://www.rustore.ru/help/en/developers/monetization/payment-callback/enable-notifications).
4. Preserve provider sender filtering at the trusted reverse proxy. A request
   arriving at the app from Caddy's loopback peer does not prove its public
   sender. Do not add loopback or arbitrary forwarded addresses to bypass
   sender checks. Recheck the current official networks during deployment;
   the provider currently documents four ranges. The notification payload
   also requires authenticated decryption. [Official server requirements](https://www.rustore.ru/help/developers/monetization/payment-callback/server-set-up).
5. Run the existing durable reconciliation worker under supervision. A
   notification is a hint to query the provider; a client success callback or
   `PAID` status cannot authorize inventory. Grant once after a matching
   `CONFIRMED` invoice, then verify delivery acknowledgement independently.

## Check the candidate

After recording the actual Console observations and explicitly preparing
enabled **sandbox-only** test inputs in private storage:

```powershell
.venv\Scripts\python.exe -B -m hotr_backend.payment_readiness122 check --commerce C:\HotrPrivate\payment-candidate\commerce.candidate.json --checkout C:\HotrPrivate\payment-candidate\checkout.candidate.json --console-inventory C:\HotrPrivate\payment-candidate\console-inventory.template.json --app-id <issued-numeric-console-id> --environment sandbox
```

`configurationValid:true` means these public inputs agree. It does not prove
keys work, Console observations are authentic, a provider payment succeeded,
or production is ready. Missing registration, changed grants/prices/one-time
limits, duplicate products, nonconsumable types, or a mixed application or
environment fail the check. Active subsets are supported when only some
approved products have been registered.

The `check` command exits `2` for production even if all public inputs match,
because it cannot establish deployment/provider/release acceptance. Preparation exits `0`
after writing a disabled candidate; that is not activation approval.

## Owned production runtime and remaining acceptance

`hotr_backend.production_runtime122` adds a distinct strict production launcher.
The existing local/staging factory still rejects ambient production activation;
`staging105.py` remains unchanged by this engineering. The new launcher requires
a fresh, separately owned authority, explicit public configuration and external
credential references, a pinned approved replay worker, live catalogue and
authenticated notifications. It reserves a loopback socket and runtime lease
before database creation. An existing staging database, a missing Ready database
or interrupted initialization is rejected and preserved.

Copy [production-runtime.example122.json](production-runtime.example122.json)
to restricted private storage and fill its reviewed paths, Console key ID,
catalogue SHA-256 and worker approval SHA-256. Its empty identifiers/hashes
deliberately fail validation. The template's public origin is currently the
staging host: it does not authorize switching that proxy or replacing accounts.
The candidate production listener is `127.0.0.1:8752`, separate from staging
port `8751`.

```powershell
.venv\Scripts\python.exe -B -m hotr_backend.production_runtime122 preflight --manifest C:\HotrPrivate\production-manifest.json
.venv\Scripts\python.exe -B -m hotr_backend.production_runtime122 initialize --manifest C:\HotrPrivate\production-manifest.json
```

Initialization creates owner/lock files and empty jobs/backup/restore directories,
without a database or server process. Only an explicitly reviewed `start` action
constructs the production application. Owner-bound snapshot, quarantine-restore
and reconciliation support is in `production_ops122` and
[the operations setup](../Production122/operations/SETUP122.txt).

The production permit emits `productionEnabled:true` consistently for managed
identity, wallet, commerce, gameplay and ad-status DTOs. Orders require
`sandbox:false`; matching verified final invoices retain the existing atomic
full-grant transaction. `normalUnityProfileIntegrated` and `localProfileMutated`
remain false because no local save is imported. The separate pure replay worker
still reports no financial mutation. Default staging responses remain unchanged.

The production application requires a trusted loopback proxy to overwrite
`X-Hotr-Verified-Client-IP` with the actual socket peer. Provider notification
networks are checked again in the service. Arbitrary forwarded headers and
non-proxy peers cannot supply that identity. The operations Caddy candidate
contains the matching rules; it has not replaced the running staging proxy.

The server runtime is exercised with actual SQLite/ASGI, real device signatures
and authenticated AES-GCM notifications, with explicitly scripted provider and
model-worker seams. These tests do not qualify real payments, a deployed replay
worker or an ordinary production Android build. Follow the final Review122
evidence for the separate Unity production configuration/transport checks.

The adapter constructor's boolean means `registeredConfiguration`; the legacy
backend-client opt-in means `stagingOptIn`. Neither chooses sandbox by itself.
Payment environment must match the packaged production configuration, server
catalogue, order and provider locator throughout recovery.

Use the already pinned Pay **11.1.0** / Core **10.5.0** integration and the
separately approved SDK-capable engine profile for candidate testing; no engine
or SDK upgrade is performed by this work. The provider's 11.1.0 instructions
now live under the history URL. They require matching manifest/deep-link
activity configuration and document SDK quotation and acknowledgement APIs.
[Pinned official Unity Pay integration](https://www.rustore.ru/help/sdk/pay/unity/history/11-1-0).

Before live enablement, execute ordinary configured Android tests for every
offer, external banking return, absent/outdated store, cancellation, failure,
held payment, duplicate/late callbacks, app termination before/after credit,
reinstall/recovery, account switch, acknowledgement retry and refund review.
Verify one durable full grant and no repeated dispatch or reward. Test
notifications and reconciliation across service restart and provider outage.
Configure alerting for rejection spikes, pending/held age, acknowledgement
backlog, dead-letter jobs, refund quarantine and reconciliation heartbeat.
Check off-VPS encrypted backup and restore before accepting real money.

These configuration checks are host tests. They are not Unity, device, provider
or deployed production acceptance evidence.

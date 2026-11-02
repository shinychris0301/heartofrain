# Monetization126 sandbox integration

The owner confirmed that RuStore monetization, all twelve consumable products
and the Yandex rewarded unit are ready for testing. These public profiles select
SDK-reported payments and capped SDK-reported ad rewards on the existing managed
wallet. They use **staging/sandbox; production remains false**.

The signed combined sandbox APK passes 16 native build checks and 31 actual APK
checks. All 959 backend tests and all 26 actual VPS focused tests pass. The
existing hosted authority has now been upgraded in place to schema 125 with
original accounts/wallets preserved. SDK payments, capped ad rewards, VK and
constrained original 50-level replay are enabled; production remains false.
The actual LocalService worker check passed one L1 replay in 0.44 seconds with
123 MiB peak job memory under its 256 MiB qualification cap. Full-corpus,
capacity and Server Core acceptance remain open. The post-125 backup, permanent
quarantine restore and fresh nine-check monitoring passed. The broader Windows
8.3 alias portability issue remains open. No device installation or real
RuStore/Yandex/VK acceptance has occurred. Synthetic financial observations
remain separate from provider transactions. Current evidence and the remaining
step-by-step plan are in
[Review126](../../Codex_Handoff/Documentation/126_SDK_PAYMENTS_AD_REWARDS_AND_VK_REVIEW.md).

The actual cutover completed with exit 0. A separate read-only 11:07 UTC check
verified the current service, original logical data/all 65 table counts, exact
source/worker pins, all three Ready snapshots and permanent quarantine. See the
[cutover receipt](../../Verification/Evidence/Review126/Operations/VpsCutover126.json)
and [current-state receipt](../../Verification/Evidence/Review126/Operations/VpsCurrentState126.json).

The supplied identifiers are complete for this sandbox configuration:

| Setting | Value |
| --- | --- |
| Registered game package | `com.heartoftherain.game` |
| RuStore application ID | `2063777840` |
| VK application ID | `54867814` |
| Owner-confirmed VK callback | `https://api.novamind-it.ru/v1/identity/vk/callback` |
| Payment-return scheme | `heartoftherain-pay` |
| Backend | `https://api.novamind-it.ru` |
| Existing managed scope | `review-novamind-vps-1` |
| Rewarded unit | `R-M-20291714-1` |
| Retained interstitial unit | `R-M-20291714-2` |

`managed-staging.json` preserves the existing backend/scope.
`checkout-sdk.sandbox.json` enables the explicit `sdk_client_reported` profile.
`commerce.sandbox.json` enables the twelve sandbox offers below.
`advertising.sandbox.json` selects the owner-confirmed units and draft privacy
version. `release.sandbox.json` supplies signed sandbox release metadata;
its retained candidate-product notes do not control the active commerce
catalogue. `provider-testing.json` records owner readiness separately from
device acceptance. `vk.staging.json` records the owner-confirmed browser
application/callback; it is a manifest fragment, not a provider authentication
receipt.

The voluntary Shop video grants **400 coins**, at most **three claims per
player-local day**, with a **600-second cooldown**. A missing ad, cancellation or
incomplete video consumes no reward quota. The active placement is
Shop rewarded video; the interstitial ID is retained configuration.

All twelve offers are consumables. Starting/tools quantities below mean the
quantity of **each of the four starting-item/tool types**. Coin offers contain
no starting items or tools. No offer grants story stars.

| Offer | Registered product | RUB | Coins | Starting each | Tools each | Eligibility |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| coins-1000 | `hotr_coins_1000` | 99 | 1,000 | 0 | 0 | Repeatable |
| coins-5000 | `hotr_coins_5000` | 299 | 5,000 | 0 | 0 | Repeatable |
| coins-10000 | `hotr_coins_10000` | 499 | 10,000 | 0 | 0 | Repeatable |
| coins-25000 | `hotr_coins_25000` | 899 | 25,000 | 0 | 0 | Repeatable |
| coins-50000 | `hotr_coins_50000` | 1,599 | 50,000 | 0 | 0 | Repeatable |
| coins-100000 | `hotr_coins_100000` | 2,999 | 100,000 | 0 | 0 | Repeatable |
| wellkeeper | `hotr_bundle_wellkeeper_c` | 99 | 2,000 | 1 | 1 | Once per stable player/offer |
| rainy-day | `hotr_bundle_rainy_day` | 199 | 3,500 | 2 | 2 | Once per stable player/offer |
| rainlight | `hotr_bundle_rainlight` | 299 | 6,000 | 3 | 3 | Once per stable player/offer |
| village | `hotr_bundle_village` | 399 | 5,000 | 3 | 2 | Repeatable |
| festival | `hotr_bundle_festival` | 599 | 10,000 | 6 | 4 | Repeatable |
| keepers | `hotr_bundle_keepers` | 999 | 25,000 | 12 | 8 | Repeatable |

**Completed staging transition / future operator reference.** The reviewed
SDK126_20261031 run has completed; do not repeat these fresh-name commands on the
already-upgraded authority. Keep the snapshots and use the SDK126 launcher.
Use the accepted frozen backend and freshly inventoried
absolute paths for `$backendPython`, `$stagingManifest` and `$commerceProfile`.
The last variable points to the deployed copy of `commerce.sandbox.json`.
Run from the tested backend directory. The machine-readable argument reference
is [OperatorCommands126.json](../../Verification/Evidence/Review126/Backend/OperatorCommands126.json).

1. Stop the existing owned staging service and verify its runtime lease is
   released. Preserve its source/manifest and validated snapshot. Keep the exact
   data directory, deployment ID, HTTPS origin, identity scope, owner nonce and
   qualified original-worker and owner-confirmed VK settings. Review126 must not initialize a second authority or replace
   the existing database.
2. In that same private manifest, set only `rewardedAdsEnabled` to `true`, then
   apply its explicit stopped-service policy transition:

   ~~~powershell
   & $backendPython -B -m hotr_backend.staging105 configure-rewarded-ads --manifest $stagingManifest
   ~~~

3. Prepare the same authority for SDK commerce. This requires the stopped runtime
   and control leases, backs up exact schema15 and upgrades the same database
   transactionally to schema125. Original accounts, credentials, wallets,
   inventory, receipts and gameplay history remain; historical API orders retain
   their frozen `provider_api` mode.

   ~~~powershell
   & $backendPython -B -m hotr_backend.staging_sdk126 prepare --manifest $stagingManifest --commerce-config $commerceProfile --package-name com.heartoftherain.game --name SDK126_20261031 --confirm-sdk-client-reported
   ~~~

   An interrupted operation retains its pending marker, backup and proof.
   Resume with exactly the same inputs/name; preserve unfamiliar artifacts.
4. Check the prepared ownership, catalogue hash, exact SDK schema, configured
   worker and ad policy:

   ~~~powershell
   & $backendPython -B -m hotr_backend.staging_sdk126 preflight --manifest $stagingManifest
   ~~~

5. Configure the existing staging service to use the accepted backend working
   directory/interpreter and the SDK126 launcher:

   ~~~powershell
   & $backendPython -B -m hotr_backend.staging_sdk126 start --manifest $stagingManifest
   ~~~

   It retains the loopback listener/runtime lease and drains financial work on
   shutdown. Verify actual HTTPS health/readiness, original managed-account
   access and both feature flags before device testing.
6. Capture a validated post-upgrade snapshot. Its original staging105 receipt
   kind/owner binding and schema125 support the existing monitor:

   ~~~powershell
   & $backendPython -B -m hotr_backend.staging_sdk_ops126 backup --manifest $stagingManifest --name SDK126_20261031_POST
   ~~~

7. Exercise a restore drill in a fresh, permanently quarantined destination:

   ~~~powershell
   & $backendPython -B -m hotr_backend.staging_sdk_ops126 restore-quarantine --manifest $stagingManifest --backup SDK126_20261031_POST --tag SDK126_20261031_DRILL
   ~~~

   The drill creates no serving owner/policy and never replaces or starts the
   original authority. Review its SQLite validation and ownership-bound receipt.

**Stopping and recovery.** Stop controlled app/server tests using their owned
process/service handles and preserve the database, snapshots and pending journals.
Once schema125 exists, restart with the SDK126 launcher; the original schema15
launcher deliberately refuses it. After any schema125 wallet/order/ad writes,
the pre-upgrade schema15 snapshot is not a safe rollback target: restoring it
over the authority would discard newer financial records. Keep recovery copies
quarantined until a separately reviewed data-preserving recovery is chosen.

Ads can be disabled or re-enabled after the transition: stop the SDK service,
change only `rewardedAdsEnabled` in the same manifest, run the original
`configure-rewarded-ads` command above, then restart SDK126. Disabling blocks new
reservations while existing pending claims recover. Re-enabling retains quota
and cooldown; it does not reset the player's reward calendar.

The registered game package has separate Android storage/device credentials
from installed QA/staging packages. Preserve those installations and data.
Use the managed-account flow or explicit account recovery to reach an existing
wallet from the game package. Installation does not copy device keys, merge
accounts or silently import a local wallet. An unreported anonymous SDK purchase
can require the original device or manual support; SDK history is not universal
cross-device restoration.

The server validates the frozen order, observed SKU/price/currency/quantity and
receipt identity, then commits the stored grant once before delivery
acknowledgement. Only matching SDK-reported `CONFIRMED` purchases grant inventory;
two-step `PAID` funds remain held without an automatic capture. Payments use
authenticated **client-reported** SDK observations;
ad completion is also client-reported and capped. Neither mode independently
authenticates a payment/ad impression to the server. This selected payment mode
needs **no additional RuStore API key ID, private API signing key or notification
decryption key**.

Privacy/support/terms pages remain temporary drafts. Final operator/support
content and production/device acceptance remain open. The signed Development
sandbox artifact is [HeartOfTheRain_SDK126_Sandbox.apk](../../Unity/Builds/Review126/HeartOfTheRain_SDK126_Sandbox.apk),
SHA256 `a5477b4e14e98b23a72c71fba1ee2e95a61a745b9df1d1034a8f8342aff62d3d`.
Before uploading it, follow the [signing recovery guide](../Signing/README.md).
Use only the Console-configured RuStore test account: the app/backend sandbox
policy does not turn an ordinary RuStore account into a tester. The release keystore and
password stay outside the repository; verified local custody does not complete
the still-pending off-device encrypted copy and independent owner password
retention.

A separate remediation item remains for `production_runtime122`: its module
CLI has an inferred `__main__`/package private-permit type risk. It was not
exercised or repaired by this staging126 qualification. Review that path and add
an actual production CLI regression before a future production cutover; this
runbook selects staging only.


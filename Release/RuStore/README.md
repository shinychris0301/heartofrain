# RuStore release configuration

The owner-approved first-moderation build is available locally at `Builds/HeartOfTheRain_FirstModeration130.apk`. It is a signed, non-debug staging review version with purchases compiled inactive and must be held under manual publication. See [FIRST_MODERATION130.md](FIRST_MODERATION130.md) and [first-moderation-130.artifact.json](first-moderation-130.artifact.json). The later purchase build remains unbuilt pending Console moderation and sandbox tests.

The owner's current choice is **SDK checkout with `sdk_client_reported`
fulfillment**. Start with [the simplified SDK checklist](sdk-checkout125/README.md).
The registered package is `com.heartoftherain.game`; all twelve product IDs are
recorded, and the owner supplied Console application ID `2063777840` on
31 October 2026. This
mode uses no RuStore API signing credentials or notification key. The older
`provider_api` setup below remains a separate supported verification choice.

This directory contains **disabled release configuration proposals** and the
owner-confirmed product registry. The ordinary game retains
its verification package, default local profile factory, approved artwork and
Unity2022.3.62f3. Explicit server configuration selects a separate managed account. No store purchase is enabled by these files.

| Configuration | Proposed value / source |
| --- | --- |
| Production Android package | `com.heartoftherain.game`, confirmed by the owner |
| Console Application ID | `2063777840`, owner-confirmed on 31 October 2026 |
| Payment-return scheme | `heartoftherain-pay`; candidate only, check ownership/collisions and register it in the SDK settings/manifest |
| HTTPS backend origin | `https://api.novamind-it.ru`; the installed authority remains staging |
| Notification endpoints | Used by `provider_api` mode; SDK client-reported mode does not require notifications |
| Minimum Android API | 26 for the future RuStore release; ordinary verification builds retain their existing settings |
| Target API | Explicit candidate35 in the template; confirm the applicable store policy and native compatibility before release |
| Signing identity | Developer-owned release key created 31 October 2026; [public certificate and recovery setup](../Signing/README.md). SDK125 metadata records its SHA256; actual release APK signing remains pending. |

All twelve coin/bundle product IDs are owner-confirmed as registered in
`registered-products122.json`; their publication remains unverified. The
approved Shop quantities and full inventory grants are preserved.
`pricing.proposal.json` records the approved prices of 27 October 2026; real
Console products supply SDK `amountLabel`. Checkout remains disabled pending the
configured SDK backend, actual Android acceptance and release
requirements. `commerce.example.json` is the legacy API-mode example;
`sdk-checkout125/commerce.example.json` selects the SDK mode explicitly.

The owner approved the six Special/Mega prices at checkpoint99 on 27 October
2026. Their exact existing coin, tool and starting-item rewards and proposed
registration IDs are listed in [bundles.pending.json](bundles.pending.json).
Normal Shop cards/details show these preview prices while purchase remains
unavailable. Checkpoint100 adds [atomic full-Grant fulfillment and stable-player
Special eligibility](COMMERCE_FULL_GRANT100.md), including pending-order recovery
and the existing manual RefundReview quarantine. Bundle sales still require
configured Console products, deployment, SDK quotations and Android/provider
acceptance. Never discard a bundle's non-coin grants or enable checkout solely
because its preview price is visible.

| Bundle | Coins | Each tool | Each starting item | Approved RUB price |
| --- | ---: | ---: | ---: | ---: |
| Wellkeeper Kit | 2,000 | 1 | 1 | 99 |
| Rainy Day Bundle | 3,500 | 2 | 2 | 199 |
| Rainlight Reserve | 6,000 | 3 | 3 | 299 |
| Village Treasury | 5,000 | 2 | 3 | 399 |
| Festival Chest | 10,000 | 4 | 6 | 599 |
| Keeper's Collection | 25,000 | 8 | 12 | 999 |

The four tools remain Hammer/Axe/Ram/Atlas; the four starting items remain
Rocket/Bomb/Rainbow Orb/Golden Seeker. Approval changes prices only, not rewards.
The owner also approved **one purchase per stable player and offer** for Special
promotions; Mega bundles remain repeatable. Schema9 implements eligibility under
internal player ID plus offer ID, with a durable reservation/consumed entitlement
and atomic inventory delivery. The disabled proposal does not imply deployed
enforcement or production acceptance. Device flags, reinstall state and labels
do not control this limit.

| Internal product | Proposed RuStore product ID | Coins | Approved RUB price |
| --- | --- | ---: | ---: |
| `coins-1000` | `hotr_coins_1000` | 1,000 | 99 |
| `coins-5000` | `hotr_coins_5000` | 5,000 | 299 |
| `coins-10000` | `hotr_coins_10000` | 10,000 | 499 |
| `coins-25000` | `hotr_coins_25000` | 25,000 | 899 |
| `coins-50000` | `hotr_coins_50000` | 50,000 | 1,599 |
| `coins-100000` | `hotr_coins_100000` | 100,000 | 2,999 |

Copy `release.example.json` to a location outside shipped Unity assets and fill
in the actual non-secret registration, backend, signing-certificate and Russian
legal/support URLs. Point `HOTR_RUSTORE_RELEASE_CONFIG` to that file. Keep private
keystores, passwords, bearer credentials, Console private keys and Public API
JWEs in external secret storage. The backend's
`HOTR_RUSTORE_PRIVATE_KEY_FILE` is a server-only file reference. No server secret
belongs in Unity or this template.

The new SDK adapter is behind `HOTR_RUSTORE_PAY`, with an explicit configuration
constructor and no automatic bootstrap. The ordinary project intentionally does
not include the native SDK: its Android ContentProvider initializes Pay before
project C# guards can run. Use a separate configured build profile with the
pinned official Pay11.1.0/Core10.5.0 packages. `GetProducts` supplies display
`amountLabel`. In `provider_api` mode the backend independently verifies the
invoice. In `sdk_client_reported` mode it accepts the authenticated app's SDK
observation against the frozen order; that observation is not independent store
proof. Both modes require an initialized, nonquarantined durable server wallet
credit before delivery acknowledgement.

The pinned Editor's supported embedded JDK is Java11 and rejects Java17 through
its public JDK setter. The compatibility check uses Unity's normal Gradle export
and separately invokes Gradle with Java17. `HOTR_RUSTORE_JDK17_ROOT` identifies
that external toolchain for the release preflight; it does not alter Unity's
global JDK selection. Isolated compilation is not vendor support certification,
a game release, a Console registration or a successful payment.

`RuStoreReleasePreflight.RequireReady` blocks a `HOTR_BUILD_CHANNEL=rustore`
build and non-development Android builds using a production package until
external configuration **and the remaining implementation gates** are resolved.
Managed identity/recovery, explicit normal-game server-wallet selection and
authenticated notification services are implemented for local/staging use.
They are not configured or accepted as a live deployment. JSON booleans cannot
replace ordinary configured Android acceptance, actual SDK sandbox/bank-return
tests, signing or legal/hosting review; older preflight gate names do not mean
the corresponding staging code is absent. Internal builds of
`com.heartoftherain.verification` remain available for regression testing.

The portable backend supports local/staging operation, atomic server rewards and
purchases, typed attempts, repeated 900-coin/+5-move continues and a 900-coin full
refill at zero lives. Managed guest registration is explicitly enabled and
creates isolated server players; operator provisioning remains a review/admin
tool. Old
reward-only server accounts remain nonspendable until migration is approved;
local Unity balances are never imported automatically. Keep sandbox databases,
credentials, receipts and balances separate from any future live environment.
See [backend operations and API boundaries](../../Backend/README.md).

The verified checkpoint82 foundation adds managed guest identity/recovery,
revocation/deletion, authenticated encrypted notifications, bounded recovery and
discovery workers, backup/restore and permission-checked social services. See
`Codex_Handoff/Documentation/82_IDENTITY_SOCIAL_AND_OPERATIONS_FOUNDATION_REVIEW.md`.
Its native/Android fixture results do not certify normal app integration.

Checkpoint83 verifies the pinned live gameplay model against371 native cases
on both the approved Windows worker and Android IL2CPP. Explicit external
server configuration now selects managed identity and the authoritative wallet
in ordinary app callers; connected native HTTP evidence covers gameplay,
Profile rename/records, reward adapters and social components. Current account
and complete-page acceptance is tracked under
`Verification/Evidence/ServerGameplay83/`, separately from installed APK81.
The approved worker is Windows-only; Linux requires its own build, resource
isolation and parity evidence.

Checkpoint84 passes324 backend tests,18,420 connected native checks, both final
internal builds and101 Android checks across eight processes in a separate
fixture package. That fixture verifies managed account recovery/closed states
and ordinary host/Play/Hammer/quit service callers; it does not certify the
ordinary app startup route, touch input, live SDK payments or physical devices.
See `84_CONNECTED_BACKEND_APP_REVIEW.md` and the current evidence summary.

The current checkpoint86 backend passes397 tests with zero skips and the approved real replay worker; 84 exact inputs are archived under `Verification/Evidence/Review86/Backend/Final/`. Thirteen Editor suites pass21,562 checks, while two Account suites retain clipboard failures and later account acceptance remains incomplete. Both internal SDK-free Android builds/static checks and a separate22-check stock SDK Editor API probe pass in their distinct scopes. No actual configured Android checkout or provider acceptance is implied. See `86_COMPREHENSIVE_APP_BACKEND_REVIEW.md` and `Verification/Evidence/Review86/Comparison.html`.

Before enabling production: complete ordinary configured Android startup and
page acceptance, an explicit account migration policy and Russian privacy/retention
policies; deploy/operate the HTTPS service with backups and environment
isolation; verify actual signed Android sandbox payments, cancellation,
termination/restart, duplicate delivery, external-bank return and upgrades.
Social services implement moderation/reporting/blocking; actual public
moderation operations must be staffed and verified. Optional provider linking
is distinct from managed guest recovery and is not supplied. The ordinary
installed game remains81.

Follow `OWNER_SETUP.md` for account, application, products, host/domain, signing
and legal setup. The desired October27–28 window is a preparation/submission
target; store moderation can extend beyond it.

## Configured sandbox Shop review (checkpoint86, provider/device acceptance pending)

The new ordinary-Shop caller is an explicitly selected sandbox integration;
its targeted Editor and isolated SDK API checks pass, with actual configured Android/provider acceptance still required. It does not enable
production or turn earlier SDK fixture compilation into a real payment test.

1. Use a separate sandbox database/account and the registered Console App ID.
   Configure the server's six approved coin products with exact SKU, quantity1,
   RUB price and coin mappings; keep live commerce disabled. Server private API
   and notification keys remain external, never in client configuration.
2. Select the managed-server app mode with an external
   `HOTR_SERVER_GAMEPLAY_CONFIG` file and the actual staging HTTPS origin.
   Preserve existing local saves; there is no automatic wallet/progress import.
3. Copy `checkout.example.json` outside shipped assets, supply the actual
   `consoleAppId` as a decimal string and set `enabled` only for this configured
   sandbox review, with `sandbox:true`. Point `HOTR_SHOP_CHECKOUT86_CONFIG` to
   that file, or explicitly provision it at the app's private
   `ServerReview/checkout.json` path. An absent/disabled file leaves ordinary
   checkout off.
4. Use the separately configured build with the pinned real Pay SDK branch,
   registered return scheme and matching Console settings. The authenticated
   server catalog, exact six SDK products/currency/prices and fresh account
   wallet must all agree before Buy is available. SDK display prices come from
   `amountLabel`; a client price proposal is not a charge authority.
5. Exercise Buy and recover the same durable order after cancellation, unknown
   response, process termination and external-bank return. Empty purchase lists
   never prove cancellation. Only fully bound server reconciliation can confirm
   a spendable credit or verified no-delivery terminal state. Refund review
   remains quarantined. Refresh the same account's wallet before showing success;
   returning from Shop still requires an explicit Play On to buy extra moves.

Preserve source/process/evidence bindings for these runs. Passing configuration,
scripted native controls or SDK compilation does not replace actual configured
Android sandbox testing, provider traffic or release preflight approval.

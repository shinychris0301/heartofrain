# SDK-handled RuStore purchases — 30 October 2026

The owner selected SDK checkout instead of independent RuStore API verification.
The owner also confirmed the registered package `com.heartoftherain.game` and,
on 31 October 2026, supplied Console application ID `2063777840`. All twelve registered
product IDs were already supplied, including `hotr_bundle_wellkeeper_c`.

The simple owner checklist is
[Release/RuStore/sdk-checkout125/README.md](../../Release/RuStore/sdk-checkout125/README.md).
The selected mode needs no RuStore API key ID, private API signing key or
notification key. VK setup is separate. Release signing remains developer-owned.

## Behavior

The existing managed account and server wallet remain the financial authority.
The app records its order before opening the SDK, then reads the purchase back
through `GetPurchase`. It sends an explicitly client-reported observation to
`POST /v1/commerce/orders/{id}/sdk-report`. The service matches the frozen order,
authenticated player, app/environment, identifiers, product, nonce, quantity,
price and currency. It commits the approved full grant, ledger credit and
one-time entitlement atomically before the app acknowledges delivery.

The new mode is named `sdk_client_reported`; the old `provider_api` mode remains
the default and still requires independent provider evidence. Per-order mode is
immutable. There is no silent API-to-SDK fallback, local wallet fork, local-save
import, animation-driven grant or fake `VerifiedInvoice` conversion.

All six coin packs and six bundles retain their approved prices, coins, tools,
starting items and Special once-per-player limits. Mega products remain
repeatable. SDK prices supply the displayed amount. Backend confirmation and
acknowledgment retries cannot add another credit for the same bound purchase.

Actual Pay11.1 phases are handled explicitly. Unknown/pending phases remain
recoverable; `UNDEFINED` may progress to a known purchase method. Refund review
remains sticky. Checkout uses `ONE_STEP`; an unexpected `TWO_STEP/PAID` observation
does not grant inventory. This review does not add a two-step capture workflow.

## Code and configuration

- Backend: explicit mode selection in commerce, strict SDK observation DTO,
  shared atomic settlement, separate schema125, exact readiness support and
  production lifecycle without RSA/notification sources in SDK mode.
- Operations: owned SDK125 snapshots and permanent restore quarantine use an
  exact private validator; existing API operations keep their schema15 defaults.
  Provider reconciliation/discovery is not an SDK payment-verification route.
- Unity: typed mode propagation, strict packaged `HOTR_RuStore/CheckoutSdk125`
  profile, SDK observation mapping, selected report transport and protected
  journal binding. Old API resources/journals retain their legacy interpretation.
- SDK: pinned Pay11.1.0/Core10.5.0 retained. SDK-lock changes describe only the
  mode-specific credential requirement; package/toolchain pins are unchanged.
- Release: disabled eight-field checkout example, exact twelve-offer catalogue,
  release metadata and owner inputs are under `Release/RuStore/sdk-checkout125/`.
  Actual package/domain/temporary page URLs are recorded. The owner-supplied
  app ID `2063777840` was added to disabled templates on 31 October 2026; the
  30 October test receipts retain their original synthetic/input values.

## Verification scope

The full backend run passed **933 executed tests**, zero failures/errors/skips,
including the approved actual gameplay worker. All 175 recorded source inputs
stayed unchanged during the run and matched the final check. See
`Verification/Evidence/Review125/Backend/Full01/Service_Tests.json`.

Source-bound focused backend compatibility passes 200 tests, including payment
binding, duplicate/concurrent delivery, full grants, mode isolation, pending and
refund behavior, restart/rollback, offline preparation and readiness. Operations
passes 43 tests with actual SQLite/OS ownership controls and legacy regressions.
These counts overlap the full backend suite and must not be summed.

Fresh actual vendor SDK checks pass 49 assertions in Unity2022.3.62f3, with all
315 resolved Pay/Core files matched to pinned archives. The unmodified packages
still declare Unity6000 minimum; this is measured Editor/API compatibility, not
vendor support certification. No SDK/JNI initialization or payment occurred.
The latest run includes the earlier 38 checks and additionally exercises actual
vendor settings, generated Android values and manifest binding through the
official Editor APIs. Do not add the repeated earlier run to this count.

The final source-bound native, Unity/loopback HTTP and full backend receipts are
indexed by `Verification/Evidence/Review125/Review125Summary.json`. Earlier failed
native test-harness epochs remain retained. Full source epochs, isolated-project
settings and newer unrelated main edits must be distinguished when using results.

Final native checks pass **4,172 assertions / 99 cases** across six suites.
Actual Unity-to-loopback HTTP passes **45 checks**, including backend restart;
SDK observations are synthetic. Independent SQLite inspection found one durable
1,000-coin credit/projection, zero provider invoice requests and preserved pending,
cancelled and refund-review states. The owned test listener was closed.
All 18 owned C# files match the accepted native epoch; all 3,154 original GUIDs
and main project settings match their pre125 bytes. Concrete parameterized
packaging instructions are in
`Verification/Evidence/Review125/NativeClient/PackagingEntry125.txt`.

## Remaining gates

RuStore SDK registration identifiers are complete: app ID **`2063777840`** and
package **`com.heartoftherain.game`**. Actual vendor binding with this ID is still
pending. Monetization/product availability, correct upload signing,
final operator/support/legal content and real Android sandbox/bank-return/restart
acceptance are additional release checks, not extra SDK API secrets.

The installed VPS remains staging105/schema15. This task does not deploy or
migrate it. The new SDK schema125 cannot silently open or upgrade that authority.
Existing accounts/wallets need a separately implemented, stopped and reviewed
same-wallet deployment/cutover before enabling the hosted SDK route.

The concrete `sdk_prepare125` command applies only to an already-owned
production122 API/schema15 authority. It takes a validated backup and creates a
permanently quarantined125 candidate, preserving original tables and historical
API-mode orders. It neither accepts the existing staging105/117 ownership format
nor starts/adopts the candidate. It is not a staging-to-production promotion.

SDK mode relies on the authenticated app's purchase reports. Modified clients
can forge those reports; durable idempotency and order binding do not establish
independent store proof. Anonymous SDK history is device scoped, so an unreported
payment after device loss/reinstall may need manual support. Already committed
grants remain in the managed wallet. Refund review depends on receiving the SDK
observation; this mode has no independent invoice polling/notification channel.
No real charge, final release APK, device
purchase, provider notification activation or production cutover is claimed.

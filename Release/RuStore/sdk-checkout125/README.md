# RuStore SDK checkout — simple owner checklist

The owner selected `sdk_client_reported` purchases. RuStore's SDK handles the
payment inside the Android app. The existing managed backend records the fixed
order's coin/tool/starting-item grant and keeps the wallet synchronized. It
accepts the authenticated app's SDK observation in this mode; it does not make
an independent RuStore invoice request.

## Recorded SDK identifiers

The owner supplied the numeric RuStore application ID **`2063777840`** on
31 October 2026. It is recorded in the checkout, commerce and release templates
beside this guide. The RuStore SDK identifiers are complete; the templates stay
disabled pending backend deployment and release acceptance.
[Official SDK initialization instructions](https://www.rustore.ru/help/sdk/pay/unity/history/11-1-0).

| Material | Current state |
| --- | --- |
| Android package | Owner confirmed `com.heartoftherain.game` on 30 October 2026 |
| Numeric RuStore application ID | `2063777840`, owner-confirmed on 31 October 2026 |
| All twelve product IDs | Already received and recorded in `../registered-products122.json` |
| Wellkeeper product | `hotr_bundle_wellkeeper_c`; the deleted old ID is not reused |
| Payment-return scheme | Build configuration uses `heartoftherain-pay` |
| Existing backend | `https://api.novamind-it.ru`; current hosted authority remains staging |

## What the owner checks in RuStore Console

1. Monetization is enabled for this application.
2. All twelve items have the agreed IDs, prices and consumable types. Make the
   products available for the relevant sandbox/production environment.
3. Configure the test account according to RuStore's testing instructions, then
   complete actual Android sandbox purchase and recovery checks before live sales.

These are Console/account actions, not additional secret values to send in chat.

## What the build handles

The pinned Pay11.1.0/Core10.5.0 SDK, return link, product mapping, price display,
pending-purchase recovery and delivery acknowledgment are engineering inputs.
The checkout profile is packaged at `HOTR_RuStore/CheckoutSdk125`; its strict
eight-field example is beside this guide. Leave it disabled until the SDK
backend is configured and Android acceptance is complete. Do not mix it with the
older API-verified checkout resource.

The app keeps its purchase intent before launching payment, reads the purchase
back through the SDK, commits one durable inventory grant before acknowledging
delivery and refreshes the wallet. An interrupted request remains pending for recovery.
Server orders and grants preserve the full approved bundle inventory and the
once-per-player Special limits.

Already committed grants remain in the managed account's wallet. Recovery of an
unreported anonymous SDK purchase is device scoped; replacing or uninstalling
the app can require manual payment support. SDK history is not universal
cross-device restoration. [RuStore payment guide](https://www.rustore.ru/help/guides/payments).

The existing hosted staging backend has not been upgraded to this SDK mode.
Deployment and preservation of its existing accounts/wallets are separate
engineering steps before live checkout; the SDK profile stays disabled meanwhile.

## Secrets and release requirements

This payment mode requires **no RuStore API key ID, private API signing key or
notification decryption key**. VK registration is separate from payments.
The developer-owned release keystore was created on 31 October 2026; its public
fingerprints and recovery instructions are in
[the signing setup](../../Signing/README.md). It is prepared for the final APK;
actual APK signing is still pending. Keep its contents and passwords outside
chat and the repository. The verified local backup still needs off-device
copying and independent password retention by the owner.

The published privacy/support/terms pages are temporary drafts. Final operator
and support details, release signing and actual device/SDK acceptance remain
necessary before the production release.

SDK observations are supplied by the app. A modified client can forge them;
durable order binding and idempotency prevent duplicate delivery, but do not
authenticate payment to the server. The independent API-verification mode remains
available as a separate choice.

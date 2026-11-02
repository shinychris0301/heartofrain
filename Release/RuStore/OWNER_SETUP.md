# RuStore launch: owner setup and release gates

31 October 2026: the owner selected SDK checkout. Use
[the simplified current checklist](sdk-checkout125/README.md): registered package
`com.heartoftherain.game`, all twelve product IDs and RuStore application ID
`2063777840` are recorded. API signing credentials and notification keys apply to the
separate `provider_api` option described below, not to the selected SDK mode.
The existing backend is hosted at `https://api.novamind-it.ru` in staging, and
temporary public pages are published. Earlier submission estimates below are
historical and do not establish release readiness.

Updated 26 October 2026. Target requested by the owner: launch within two to
three days, with real purchases. Treat 27–28 October as the desired submission
window, not a guaranteed public launch. RuStore's 13 October guidance allows up
to six days for moderation; requests for additional information can restart
review. [Current moderation guidance](https://www.rustore.ru/developer/en/blog/moderation-in-rustore-requirements-timelines-and-review-stages)

Development can continue while the owner completes the steps below. No account,
Console application, production origin, product, release signer or payment
acceptance is created by this document. The installed verification APK is not a
store release. The ordinary installed QA2 APK remains checkpoint81. The frozen
checkpoint82 foundation and checkpoint83 replay verifier are verified within
their documented scopes; current connected-page and account acceptance is
tracked separately in `Verification/Evidence/ServerGameplay83/`. Checkpoint84
now passes324 backend tests,18,420 connected native checks, both internal builds
and a separate101-check/eight-process Android lifecycle fixture. Ordinary
configured startup, live payments and public operations remain release gates.
The current checkpoint86 backend passes397 tests with zero skips and the approved real replay worker; 84 exact inputs are archived under `Verification/Evidence/Review86/Backend/Final/`. Thirteen Editor suites pass21,562 checks, while two Account suites retain clipboard failures and later account acceptance remains incomplete. Both internal SDK-free Android builds/static checks and a separate22-check stock SDK Editor API probe pass in their distinct scopes. No actual configured Android checkout or provider acceptance is implied. See `86_COMPREHENSIVE_APP_BACKEND_REVIEW.md` and `Verification/Evidence/Review86/Comparison.html`.

1. Register the owner-controlled RuStore developer account using the appropriate
   legal status, then complete the monetization and payout setup in Console.
   Keep account passwords, banking details and signing credentials outside the
   repository and chat. [Registration](https://www.rustore.ru/help/developers/developer-account/registration-developer),
   [Monetization](https://www.rustore.ru/help/developers/monetization).
2. Create the application named **Сердце дождя**. Check/reserve the proposed
   package `com.heartoftherain.game`; record the actual Console Application ID.
   The ID is assigned by RuStore and cannot be supplied in advance by Codex.
   Retain the same package and release signing identity for subsequent updates.
   [Application creation](https://www.rustore.ru/help/developers/publishing-and-verifying-apps/app-publication).
3. Create six **consumable** coin products from `pricing.proposal.json`. The
   proposed identifiers are `hotr_coins_1000`, `hotr_coins_5000`,
   `hotr_coins_10000`, `hotr_coins_25000`, `hotr_coins_50000` and
   `hotr_coins_100000`. Record the actual identifiers and RUB prices; they must
   match the server catalog. The owner-approved RUB prices, in that order, are
   **99 / 299 / 499 / 899 / 1599 / 2999** (27 October 2026). The disabled
   `commerce.example.json` contains their exact server-side minor-unit amounts.
   Unpublished products can be tested in sandbox;
   production availability requires publication. [Product setup](https://www.rustore.ru/help/developers/monetization/create-paid-product-in-application).
   The six existing Special/Mega bundles now also have approved prices in
   `bundles.pending.json`: Special **99 / 199 / 299 RUB**, Mega
   **399 / 599 / 999 RUB**. Their exact tool/starting-item rewards stay unchanged.
   The disabled `commerce.example.json` now includes their complete grants and
   policies. Schema9 implements atomic inventory delivery, pending recovery and
   manual RefundReview handling; see `COMMERCE_FULL_GRANT100.md`. Keep checkout
   unavailable until deployment and real Console/SDK/provider recovery are tested.
   Special promotions are approved once per stable player and offer; Mega
   bundles remain repeatable. Enforce this with server-persisted eligibility,
   not device preferences or reinstall state, before enabling bundle purchases.
4. Choose an owned domain and backend host. Supply its real HTTPS origin, not a
   temporary guessed URL. The service needs persistent database storage, a
   scheduled reconciliation worker, restricted secret files, tested backups,
   monitoring and separate sandbox/production databases. Decide and document
   personal-data storage locations and access before deployment. There is no
   deployed endpoint yet, and the current server explicitly blocks production.
   The currently approved gameplay replay bundle runs on Windows with Job
   Object process/resource limits. Choose a Windows worker host for that exact
   verified bundle, or budget a separate Linux worker build, sandbox and parity
   acceptance. The portable Python API alone does not make that worker portable.
   Monitor `/healthz` for process liveness and `/readyz` for the bounded,
   rolled-back SQLite writer/schema probe. Neither endpoint certifies provider
   credentials, worker availability or release readiness. The current ingress
   caps bodies at64 KiB, applies a15-second receive-only deadline and rejects
   ambiguous or malformed UTF-8 JSON; handler/provider budgets remain separate.
5. Generate or select the durable release keystore outside this project. Back
   it up securely and record its certificate SHA256. Do not use the development
   signer. Supply passwords through external secret storage at build time.
6. Supply factual Russian privacy, support and terms URLs, operator identity,
   contact details, retention/deletion policy and refund support process. These
   cannot be invented from the game artwork. Account deletion must describe any
   legally required financial retention accurately. Reporting, blocking and
   permission-checked moderation services are implemented; designate actual
   moderators, their restricted credentials and a monitored report-response
   process before enabling public Teams/chat.

## Non-secret configuration to return

| Value | Current proposal or required source |
| --- | --- |
| Android package | `com.heartoftherain.game`, subject to actual reservation |
| Console Application ID | Actual value from the newly created application |
| Product IDs and rewards | Six quantities above; confirm actual Console mappings |
| Payment-return scheme | `heartoftherain-pay`, verify ownership/collisions |
| Backend | Actual owned HTTPS origin after deployment |
| Legal/support URLs | Published Russian pages with the operator's factual details |
| Release certificate | Public SHA256 fingerprint; keep the keystore private |

Fill a copy of `release.example.json` outside shipped Unity assets. Do not mark
unmet implementation or device-test gates as complete merely to pass preflight.
Managed guest identity/recovery, authoritative wallet/attempt services and
explicit app service selection are implemented; hosting and store registration
are missing operator inputs, while actual configured Android checkout and
bank-return/restart acceptance are still engineering/release evidence gates.
Enabling a configuration flag alone cannot close either category.

## Server secrets and payment notifications

Create the required RuStore Public API key through the owner's Console. Store
the private key only on the server and reference its external path with
`HOTR_RUSTORE_PRIVATE_KEY_FILE`. The API key ID is configuration; the private key
and resulting API authorization material must never ship in Unity.

Configure a distinct sandbox notification URL first:
`<actual-origin>/v1/commerce/notifications/rustore/sandbox`. The production path
is `/v1/commerce/notifications/rustore/production` in the separately configured
production environment. Keep the Console-provided AES notification key in an
external server-only file referenced by
`HOTR_RUSTORE_NOTIFICATION_KEY_FILE`. Never paste it into this checklist.

Notification ingress must use TLS, enforce the configured sender networks, and
retain the real socket peer through the deployment topology. The application
does not trust arbitrary `X-Forwarded-For` headers. A proxy that makes every
sender appear to be loopback must not be accepted as sender validation: enforce
the current provider network list at a trusted ingress and configure the
verified topology explicitly. Complete Console's endpoint check and enable
notifications only after testing the deployed receiver.
[Notification setup](https://www.rustore.ru/help/en/developers/monetization/payment-callback/enable-notifications),
[Encryption and sender requirements](https://www.rustore.ru/help/developers/monetization/payment-callback/server-set-up).

The checkpoint82 receiver and durable worker have local transaction/HTTP
verification. They reconcile known invoice IDs using the provider API; neither
a callback status nor the client can grant currency directly. The case where
both the initial client result and every notification are lost is covered with
a clearly synthetic listing source and the real reconciliation adapter. The
official listing adapter is production-only; no sandbox listing endpoint is
invented. Actual Console traffic, ingress topology and scheduled deployed
workers remain required acceptance cases.

## Required release evidence before submission

- One configured, signed Android build: API26 baseline, Russian default/name,
  portrait phones/tablets, actual Console ID/deep link and SDK-return prices.
- Stable managed player identity, secure session/recovery, server wallet and
  inventory selected by ordinary gameplay, verified attempt outcomes and
  atomic repeated +5-move/900-coin continuations.
- Actual RuStore sandbox payments: success, cancellation, interruption,
  duplicate callbacks, process death/restart, external banking-app return,
  missed-notification recovery and update installation preserving progress.
- Durable delivery receipt before SDK acknowledgement, verified refund handling,
  backup/restore drill and a monitored worker in the deployed environment.
- Controlled real-payment verification after sandbox acceptance and owner setup;
  any money-spending test requires its explicit budget/authorization.
- Russian legal/support information and accurate account-deletion behavior.

The Unity splash remains required by the current license. No automatic engine
upgrade or splash bypass is included. Existing physical-device and dense-effect
performance limitations remain open; local test passes cannot certify store
moderation, production payments or all devices.

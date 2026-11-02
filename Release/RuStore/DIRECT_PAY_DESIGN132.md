# Direct RuStore Pay purchase design

1 November 2026. This design responds to the owner's requirement that the game initiate and complete purchases through RuStore Pay without a Heart of the Rain backend request in the purchase path. The code implementation is tracked in `Codex_Handoff/Documentation/132_DIRECT_RUSTORE_PAY_IMPLEMENTATION_REVIEW.md`; the submitted versionCode 130 APK still has paid checkout disabled.

RuStore says its Pay SDK can handle a basic payment flow without a developer server. Its [Unity Pay SDK documentation](https://www.rustore.ru/help/en/sdk/pay/unity/11-1-0) exposes `GetProducts`, `Purchase`, `GetPurchase`, `GetPurchases` and `UpdateAcknowledgementState`; its [payment guide](https://www.rustore.ru/developer/en/blog/how-to-set-up-payments-in-rustore-from-registration-to-your-first-payment) describes server verification as additional rather than mandatory. "No developer backend" does **not** mean offline payment: the SDK and RuStore still need their own network and account/payment services.

## Proposed device-only transaction

1. Show only Console products returned by `GetProducts`. Display the SDK `amountLabel`; compare each product ID, type, currency and minimum-unit price against a baked, versioned grant catalogue before enabling its button. A changed Console price or grant mapping stops purchase until an app update or explicit reviewed catalogue change.
2. On an explicit Buy tap, write an `Intent` row in a durable on-device purchase journal, then call the existing RuStore Pay adapter with `Purchase(..., ONE_STEP)`. Keep the return deep link and `UnityPlayerActivity` configuration. Use one-step payment to avoid an app-only two-step hold/confirm policy.
3. Treat the SDK callback as an observation. Call `GetPurchase(purchaseId)` and require `CONFIRMED`, the expected product ID, purchase ID, quantity, sandbox flag, price, currency and locally generated order correlation. `PAID` is a hold and grants nothing. Cancelled, rejected, expired, refunded and reversed states grant nothing.
4. In **one local database transaction**, insert a unique `(store, purchaseId)` receipt and apply the exact catalogue grant to a device wallet ledger. Repeated callbacks or `GetPurchases` scans find the existing receipt and do not grant again. Commit and flush before showing reward animation.
5. Only after the durable grant, call `UpdateAcknowledgementState(ACKNOWLEDGED)`. If acknowledgement fails, retain the pending row and retry after restart or reconnection. An acknowledgement by itself never grants an item.
6. At launch and when Shop reopens, enumerate relevant `GetPurchases` results and query any journaled purchase IDs. Reconcile `CONFIRMED` purchases not yet in the ledger, including a process death after payment but before the callback. Never start another `Purchase` from recovery.
7. Handle an observed refund by marking the receipt `RefundReview`, preventing the same purchase from regranting, and reconciling a remaining local balance or a debt. A locally spent grant may not be recoverable; support must have a clear refund policy.

The existing `RuStorePayAdapter` wraps product reads, purchase, lookup, listing and acknowledgement. The existing `ShopCheckoutFlow86` still requires a server order and server wallet. `DirectPurchaseCoordinator` and `DirectPurchaseLedger` now implement the separate device path behind an explicit build define. The submitted build continues to disable paid checkout.

## Required wallet migration

The active game uses a server-authoritative wallet for coins, starting boosters, tools and attempt settlement. A locally credited pack cannot be spent correctly by the current server-backed Continue, life refill, boosters or shop model. To remove the backend from purchases **and** use the goods, the app must make those purchased balances authoritative on the device, route every affected spend through the same local ledger, and define how server gameplay/account data relates to it. Server-awarded level, Daily Gift, Wellworks and ad rewards must also have an explicit migration rule; they cannot silently merge with locally purchased currency. Merely adding local and server balances on screen is not safe: a second device or a stale server response could double-spend or erase a purchase.

The device-only design therefore has these product limits unless the owner later authorizes a sync authority:

- A purchase is tied to the installation's local ledger. RuStore purchase history can reveal that a payment occurred, but it cannot reconstruct how many coins or tools were already spent after local data is lost. Exact reinstall or cross-device restoration of consumable balances is not possible from payment history alone.
- VK account linking and team services may continue to use the backend, but they cannot promise to carry device-only purchased balances to another phone. Shop and Save Progress must say this plainly before live sales.
- Repeatable coin and Mega packs fit RuStore `CONSUMABLE`. The approved one-time Special promotions require an account-wide entitlement. A local-only flag enforces them only on one installation. They must stay unavailable until a durable cross-device rule is approved, or be changed to RuStore `NON_CONSUMABLE` products with explicit restoration and spent-bundle semantics.
- Android Keystore protection and an append-only/transactional local ledger reduce accidental corruption and casual tampering, but they cannot prove an unmodified client. A patched device may fabricate local grants, leaderboard progress, or gameplay inputs. Backend social/reward services must not trust client-reported purchased balances.

## Work and acceptance gates

1. Implement a local purchase journal, unique purchase receipt and atomic wallet transaction; migrate **all** affected spenders to that ledger. The implementation uses the existing atomically replaced `FileProfileRepository` profile revision rather than SQLite. Preserve existing guest progress and inventory via a one-time, rollback-safe migration. Keep gameplay reward grants and paid grants separately sourced. Server reward integration remains an open gate.
2. Add SDK-driven Shop product/price discovery and the direct coordinator. Gate it to RuStore builds and the configured package/signature. Keep purchase UI disabled in the already submitted APK.
3. Add deterministic tests for duplicate callbacks, process death at every journal transition, callback loss, acknowledgement failure, PAID hold, refund, catalog mismatch, one-time offer policy and local wallet/spend atomicity.
4. After first-version moderation, test the exact later APK in RuStore sandbox on physical Android: all products, external banking return, cancellation, restart, two devices, reinstall and refund. Do not describe local simulated SDK tests as payment acceptance.
5. Review consumer support, disclosures and the business decision about cross-device consumable recovery before enabling live sales. The serverless architecture does not meet the earlier cross-device purchased-balance goal without a separate sync authority.

The release guard added during review 131 blocks the current **client-reported backend-credit** production mode, because that mode still asks the server to trust a client status and credit its wallet. It does not require a backend for the proposed device-only purchase path. A later, separately tested local mode can have its own release gate once it exists.

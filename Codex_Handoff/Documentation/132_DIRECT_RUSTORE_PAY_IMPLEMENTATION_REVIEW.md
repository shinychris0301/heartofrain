# Direct RuStore Pay implementation review (1 November 2026)

> Follow-up: [review 133](133_DIRECT_PAY_TWELVE_PRODUCT_REVIEW.md) extends product discovery to all twelve planned SKUs while retaining the purchase gate for the three Specials. The nine-product assertion counts below describe this earlier verification snapshot.

## Scope and release status

The owner's device-only purchase request is implemented behind `HOTR_DIRECT_PAY132`. It does not call the Heart of the Rain backend to create an order, verify a payment, or credit purchased goods. It still requires the RuStore Pay service and network. The submitted first-moderation versionCode 130 APK remains unchanged, with paid checkout compiled out.

The direct build is **not cleared for live sales**. RuStore is still reviewing the first version. The owner reports that products are published, but sandbox provider transactions and banking return cannot yet be accepted. No real RuStore payment has been made during this implementation review.

## Implemented path

- The nine repeatable products are six coin packs and three Mega bundles. Their IDs, grants and expected RUB prices are frozen in `DirectPurchaseCatalog`; one-time Special promotions stay unavailable. `GetProducts` supplies the displayed `amountLabel` and must match ID, consumable type, RUB and price before a button is enabled. Buy refreshes the quote.
- A unique on-device order intent is durably saved before calling SDK `Purchase(..., ONE_STEP)`. A distinct local device profile at `Profiles/Direct132-v1` carries wallet, game progress, pending purchase intents and receipts. The existing `FileProfileRepository` commits a whole profile revision by atomic replacement. The grant and unique receipt are committed in that same revision. This differs from the proposed SQLite journal but retains atomic wallet/receipt behavior in the current profile model.
- The SDK callback is never grant authority by itself. `GetPurchase` must return a bound `CONFIRMED` one-step consumable purchase with matching order, payload, product, quantity, sandbox flag, RUB and price. `PAID` grants nothing. The local grant is committed before `UpdateAcknowledgementState`. Failed acknowledgement remains retryable.
- Recovery reads a saved purchase ID or searches `GetPurchases` for the exact order; it never creates a second order. An intent saved before SDK dispatch can be closed safely on restart. A dispatched order with no conclusive provider result stays pending, because silently retrying could charge twice. Duplicate callbacks and repeated recovery cannot grant twice.
- Local gameplay spending, boosters, tools, Continue and life refill use the device profile after a one-time exact snapshot of the existing server wallet. Cutover waits until the server wallet is ready and no attempt is pending. VK sign-in and Teams remain separate services; account linking does not transfer purchased balances to another device.
- Shop displays a short device-only storage notice. Save Progress still needs a fuller lost-device disclosure. Server-backed Daily Gift, Wellworks, Rain Cup and ad rewards are not credited into the local wallet; those reward paths are disabled under direct mode rather than silently mixing two wallet authorities.

## Checks performed

- Unity 6000.3.27f1 Android-target Editor compilation with the real `ru.rustore.pay` 11.1.0 and `ru.rustore.core` 10.5.0 packages passed in the isolated `tm1030at` clone.
- The deterministic Editor suite passed **78 assertions**: every repeatable pack's full grant, the owner-approved RUB price table, Russian Shop copy, duplicate callback, disk restart, callback loss, acknowledgement failure/retry, PAID hold, price/type mismatch, purchase observation mismatch, bound cancellation and mismatched locator, refund review, cutover validation, first-intent persistence failure and dispatch-state persistence failure. Evidence: `.verification-cache/Review132/Direct132SdkFinal.json` and `Unity132Final78.log`.
- An isolated Unity 6 Android compile/build smoke passed with zero errors and one build warning (missing RuStore entry-point settings in this stripped verification clone). Its final verification-package APK is `.verification-cache/Review104/Candidates/tm1030at/Game/Builds/Hotr_Direct132_Smoke77.apk` (SHA-256 `86a15180c4fa2a425734b471a6e614f551f1f060eada4feac88c649c38aa84c5`). It cannot exercise RuStore provider payment and is not a release candidate. Evidence: `.verification-cache/Review132/Unity132AndroidSmoke77.log`.

## Open release gates

1. Finish an actual signed Android sandbox candidate with the registered package and return scheme, then exercise each product on a physical device after first-version moderation. Cover cancellation, banking return, process death, duplicate callback, acknowledgement retry, refund, reinstall and a second device. Compare exact Console prices and grants.
2. Decide how server events, ad rewards and gameplay records will coexist with the device wallet. In the current direct build these reward features are unavailable and social rankings may not reflect local progress. This is a material regression, so do not publish this mode as the next public update yet.
3. Decide and publish a support/consumer policy for lost-device, reinstall, refund and account-link cases. RuStore purchase history does not reconstruct spent consumables. Keep Specials unavailable until account-wide one-time entitlement rules exist.
4. Run native UI and gameplay checks, including wallet spend after a confirmed sandbox grant, on the exact signed build. Current Editor tests prove local state transitions; they do not prove provider behavior.
5. Bind the local profile to its installation and review Android backup/restore behavior. The current atomic file ledger detects corruption, but a restored stale copy could resurrect a prior balance. This must be addressed before live device-only sales.

# Direct Pay: twelve-product catalog review (1 November 2026)

## What changed

The direct RuStore Pay client now requests all twelve planned SKUs through `GetProducts`. Previously it requested six coin packs and three Mega bundles only. The three Special promotions can show a validated RuStore `amountLabel`, but their purchase buttons remain unavailable. The Shop UI, checkout host, coordinator, and ledger all enforce that gate. Nine repeatable offers remain eligible for checkout after an exact ID, RUB, price, and consumable-type match. Buy re-reads the selected quote before dispatch.

The local terms in `Release/RuStore/commerce.example.json` match the twelve IDs and expected prices in `DirectPurchaseCatalog`, and all twelve grants match `CheckoutCatalogRules86`. This is a **local configuration comparison**, not evidence that RuStore Console products have the same type, price, or publication state. The owner cannot provide a Console export yet.

| Offer | Planned SKU | Expected RUB | Checkout |
| --- | --- | ---: | --- |
| 1,000 coins | `hotr_coins_1000` | 99 | Enabled after validation |
| 5,000 coins | `hotr_coins_5000` | 299 | Enabled after validation |
| 10,000 coins | `hotr_coins_10000` | 499 | Enabled after validation |
| 25,000 coins | `hotr_coins_25000` | 899 | Enabled after validation |
| 50,000 coins | `hotr_coins_50000` | 1,599 | Enabled after validation |
| 100,000 coins | `hotr_coins_100000` | 2,999 | Enabled after validation |
| Wellkeeper Special: 2,000 coins + tools | `hotr_bundle_wellkeeper_c` | 99 | Gated |
| Rainy Day Special: 3,500 coins + tools | `hotr_bundle_rainy_day` | 199 | Gated |
| Rainlight Special: 6,000 coins + tools | `hotr_bundle_rainlight` | 299 | Gated |
| Village Mega: 5,000 coins + tools | `hotr_bundle_village` | 399 | Enabled after validation |
| Festival Mega: 10,000 coins + tools | `hotr_bundle_festival` | 599 | Enabled after validation |
| Keepers Mega: 25,000 coins + tools | `hotr_bundle_keepers` | 999 | Enabled after validation |

## One-time promotion decision

The three Specials give spendable coins and tools, so their RuStore product type must be confirmed from Console before checkout is enabled. The client does not assume they are non-consumables. A one-time promotion needs an entitlement that survives reinstall, device replacement, account linking, and refund. The current device-only profile cannot enforce that account-wide limit or restore already-spent currency. Therefore the three buttons remain gated even if a valid price is fetched. A true non-consumable should confer a durable, restorable entitlement such as a permanent feature or cosmetic, not a spendable wallet balance.

## Verification and remaining gate

The local catalog audit found twelve matching ID/SKU/price/grant entries. The pinned Unity 6000.3.27f1 Editor suite passed **84 assertions**, including all twelve product IDs being requested, all nine repeatable grants, and disabled Special checkout at UI and ledger layers. Evidence: `.verification-cache/Review132/Direct133CatalogFinal2.json` and `Unity133CatalogFinal2.log`. The final isolated Android smoke build passed with zero errors and one warning: the stripped verification clone lacks RuStore entry-point settings. APK: `.verification-cache/Review104/Candidates/tm1030at/Game/Builds/Direct133CatalogSmoke2.apk` (SHA-256 `11CCE2B22E150835032DFFC5C7FD06009C014D89BA76D0F9D18B941A4A2F2EB9`). Evidence: `.verification-cache/Review132/Unity133AndroidSmoke2.log`. This build does not prove a real RuStore transaction and must not be submitted as a release APK.

Before real sales, compare a RuStore Console export with all twelve local entries (type, price, publication status), finish first-version moderation, run sandbox purchase and recovery tests on a signed physical-device build, and resolve the device-only wallet/entitlement limitations listed in review 132.

# Commerce full-Grant contract 100

This is an additive staging-service contract, not production payment approval.
The shipped/default commerce configuration remains disabled. Real Console
products, Pay SDK quotations, hosted server verification, notification/acknowledgement
recovery and Android banking-app testing are still required. Existing prices,
reward schedules and bundle contents are unchanged.

`commerce.example.json` contains twelve disabled products: six legacy coin packs
and six full-inventory bundles. `release.example.json` keeps its six-coin
registration list; `bundles.pending.json` separately lists the six proposed
bundle registrations. Actual prices in the app must come from SDK `amountLabel`.
The backend compares the verified invoice amount/currency with frozen order terms.

## Additive fields

Existing request bodies, paths, product IDs, `coins`, invoice binding, receipt IDs
and cursor fields remain valid. A product configuration may now include:

```json
{
  "id": "wellkeeper",
  "storeProductId": "hotr_bundle_wellkeeper_c",
  "enabled": false,
  "coins": 2000,
  "grant": {"coins": 2000, "stars": 0, "starting": [1,1,1,1], "tools": [1,1,1,1]},
  "purchaseLimitPerPlayer": 1,
  "amountMinor": 9900,
  "currency": "RUB"
}
```

`starting` order is Rocket, Bomb, Rainbow Orb, Golden Seeker. `tools` order is
Hammer, Axe, Ram, Atlas. Quantities are nonnegative bounded integers and both
arrays have exactly four entries. Purchasable story stars are forbidden. Grant
coins must equal the retained legacy `coins` field. An omitted config `grant`
normalizes to coins only, preserving legacy catalogs; clients must require an
explicit complete grant for bundles rather than interpreting them as coins only.

Catalog products, order views, nested order `credit`, and paged credit rows add a
canonical `grant`. Catalog products and order views also add:

| Field | Meaning |
| --- | --- |
| `purchaseLimitPerPlayer` | `1` for a one-time Special, otherwise `null` |
| `repeatable` | Whether the offer has no one-time limit |
| `eligibility` | `Available`, `Pending`, `Purchased`, or `RefundReview` |
| `eligible` | `true` only for `Available`; does not override SDK/provider readiness |
| `pendingOrderId` | Owned reserved/recoverable order, or `null` |

Orders additionally expose `reservationReleased` for financial recovery/audit
and `creationCommandId`, the immutable original creation command (legacy `null`).
The order freezes the catalog version, product/store mapping, currency/amount,
complete grant and purchase policy. Editing or disabling a catalog after order
creation never changes that order's grant or paid amount.

## Recovery and eligibility

`POST /v1/commerce/orders` still accepts only `commandId` and `productId`.
Player-provided amounts, grants, statuses and quantities remain rejected. A new
command for an already reserved one-time offer returns the same frozen order.
Only a matching original `creationCommandId` can be considered for the client's
first explicit SDK dispatch. A follower's different command, or legacy `null`,
must adopt the order as lookup-only/unknown outcome; returning the same Created
order is not permission to dispatch a second purchase. The client persists its
dispatch intent before calling the SDK and never launches payment from recovery.
Once delivered, a new command returns `409 commerce_offer_already_purchased`.
Replaying a previously committed command retains its original response; fetch
the returned order to obtain current status.

`GET /v1/commerce/orders/pending?after=0&limit=100` is player-scoped and bounded
(`after` is a nonnegative rowid cursor, `limit` is 1–100). It returns
`{playerId, orders, nextCursor, hasMore, productionEnabled:false}`. Orders include
Created/Executed/Held, RefundReview, and Confirmed purchases whose acknowledgement
has not yet been verified. No automatic SDK purchase should start merely because
an order was recovered. An unbound Created order requires an explicit user tap;
known invoices recover through verified reconciliation.
Responses additionally stop before 48KiB, below the Unity client's 64KiB buffer;
`hasMore` and `nextCursor` refer to the last actually included order. This also
covers orders with long bounded verification histories. Begin a fresh recovery
cycle at cursor zero so later status changes to older orders are observed.

The Special reservation is unique under stable internal player ID plus offer
ID, in the same writer transaction as order creation. Concurrent devices/commands
cannot reserve separate one-time orders. Recovery under another credential for
the same player retains the reservation. Device reinstall state is not the cap.
Changing a catalog to repeatable cannot bypass an existing consumed entitlement.
Mega orders remain repeatable.

Only a matching server-verified CANCELLED/REJECTED/EXPIRED invoice releases an
undelivered reservation. Client cancellation, missing callbacks, provider outages,
unknown status, held PAID funds and elapsed wall time do not release it. A Created
order without provider proof stays recoverable/reserved; operator investigation
may be needed if a final invoice cannot be located. There is no client release
or wallet-import endpoint.

## Commit, acknowledgement, refund and deletion

Only a matching CONFIRMED invoice delivers. One SQLite transaction writes the
immutable full-Grant credit, all coin/starting/tool deltas in the wallet ledger,
delivery acknowledgement and consumed entitlement. Inventory overflow or a
pre-commit fault rolls everything back. Repeated callbacks and lost replies
recover the original receipt without issuing items again. Startup replay uses
the same frozen grant and immutable wallet origin.

After SDK acknowledgement, reconcile the same invoice again. The server marks
Acknowledged only when the provider reports ACKNOWLEDGED; a delayed provider
readback remains pending and recoverable. A client callback is not delivery proof.

Refund initiation/refund/reversal keeps the existing sticky `RefundReview` policy:
spending/new checkout is quarantined, issued inventory is not guessed or debited,
and a consumed one-time cap is not reset. A contradictory CONFIRMED response for
a previously terminal-released Special also enters RefundReview without a new
grant or automatic debit. This is a **paid-but-conflicting transaction requiring
operator refund/reconciliation**, not successful delivery. Existing delivered
duplicates keep their original receipt. Never silently retry into a new reward.

Account deletion retains the existing restricted financial/security audit and
entitlement rows. Transaction-bound active-account checks reject late provider
delivery, catalog/pending reads and new orders; startup backfill skips tombstoned
players. No deleted account or financial entitlement is recreated. Physical purge,
retention law/policy, cross-account merges and operator refund resolution remain
separate configured requirements.

## Schema and verification scope

Schema 9 is an explicit additive migration from schema 8: frozen grant/policy
columns plus a stable-player entitlement table. Legacy coin orders/credits gain
zero item arrays; no existing balances or receipts are repriced. Snapshot tools
accept and verify both old and current schemas, and restore into a new file before
an explicit migration. Tests exercise actual SQLite/ASGI transactions with a
scripted provider. They do not prove a real payment, hosting capacity, SDK banking
return or production eligibility enforcement on a deployed service.

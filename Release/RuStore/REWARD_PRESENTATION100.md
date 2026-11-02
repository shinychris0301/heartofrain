# Reward presentation contract 100

Implementation contract reviewed 28 October 2026. This document describes the
same-device presentation outbox and its integration points. It does not certify
native rendering, physical-device behavior, live payments or production rollout.
The [checkpoint 100 review](../../Codex_Handoff/Documentation/100_FULL_GRANT_COMMERCE_AND_REWARD_PRESENTATION_REVIEW.md) and [evidence gallery](../../Verification/Evidence/Review100/Comparison.html)
maintained by the native verification owner record executed results and remaining
acceptance gates. No new reward quantities or prices are approved here.

## Authority and receipt data

The existing model/services and server ledger remain authoritative for coins,
stars, four starting-item counts and four tool counts. An animation never grants,
claims, spends or refunds anything. The authoritative wallet is refreshed before
an already committed reward is put in this presentation queue.

`RewardPresentationJournal` stores public receipt metadata: channel, receipt ID,
a frozen complete `RewardGrant`, and whether its notification was presented.
`starting` order is Rocket, Bomb, Rainbow Orb, Golden Seeker; `tools` order is
Hammer, Axe, Ram, Atlas. A grant can describe earned stars, but configured coin
and inventory purchases still forbid purchasable story stars.

The journal is bound to the canonical backend origin and stable internal player
ID. The production factory is:

```csharp
RewardPresentationJournal.ForPlayer(origin, playerId)
    .Enqueue(channel, receiptId, committedGrant);
```

Its default location is under
`Application.persistentDataPath/ServerReview/RewardPresentation/<origin-hash>/<player-id>/receipts.json`.
The envelope's SHA-256 detects accidental corruption; it is not authentication,
encryption, financial authority or proof that the player earned a reward. Editing,
copying or replaying this file can affect a cosmetic notification only. Credentials
and payment tokens do not belong in it.

## Persist before acknowledging delivery

| Path | Commit and presentation ordering |
| --- | --- |
| Managed Daily Gift, Wellworks or practice Rain Cup claim | Keep the original durable claim intent; obtain the authoritative receipt; refresh the wallet; enqueue channel `reward`; then clear the claim intent. |
| Confirmed coin or inventory purchase | Verify the frozen order, complete credit and provider acknowledgement; refresh the authoritative wallet; enqueue channel `commerce` using `order.credit.receiptId` and `order.credit.grant`; then save the protected checkout journal as `Settled`. |
| Cup join or expired unclaimed Daily Gift | No reward receipt is manufactured when the service returns no grant. Existing eligibility and expired-offer rules remain in force. |

The ordinary `ShopCheckoutHost86` supplies the purchase hook to
`ShopCheckoutFlow86`. Its shared typed backend adapter and transport validate the
complete order/credit grant. SDK callbacks and SDK price quotations cannot create
a receipt or substitute for an authoritative credit. A successful coin purchase
returns to the continuation offer; buying extra moves still requires a separate
explicit Play On tap. See [commerce full-Grant contract](COMMERCE_FULL_GRANT100.md)
for payment recovery, frozen terms and one-time Special eligibility.

`Enqueue` deduplicates by channel plus receipt ID. The same key with a different
frozen grant is rejected. Writes use an exclusive file lock, flushed temporary
file and atomic replacement. A crash after enqueue but before clearing the
financial intent replays that same intent and finds the same presentation receipt.
It does not request a second grant or a second purchase.

Corrupt or unwritable presentation storage prevents clearing the corresponding
local claim intent or protected checkout settlement. The already committed
server balance remains authoritative. Retrying resolves the same durable command
and attempts the presentation write again. A post-commit lost acknowledgement is
also recoverable because enqueue is idempotent.

## Home notification and cancellation

`PlayerProfileHost.Initialize` attaches `RewardReceiptPresenter`. On an idle,
interactive Home with an explicitly selected managed server session, the presenter
first attempts recovery of a locally journalled reward claim, then drains pending
presentation receipts. It waits while gameplay, a modal, the event drawer, another
reveal, a financial/session operation or a reward operation occupies that flow.

`HomePage.PlayCommittedReward` uses the existing artwork and shows each positive
grant dimension as an icon and `+quantity`. Its notification runs for approximately
2 seconds, or 1.5 seconds with reduced motion. The Home header continues to show
the actual current wallet; it does not reconstruct an old balance by subtracting
the grant, because the player may already have spent some of it.

Opening another page/modal, rebuilding or resizing Home, changing its state,
disabling it, losing focus or pausing cancels the notification without marking the
receipt presented. It remains available for a later idle Home. Focus and pause
are separate flags: receiving resume does not imply regaining focus. Start,
playback and final presentation acknowledgement require the foreground Home.

Only successful completion marks the notification presented, and that callback
rechecks the same server/player/session generation. Marking presentation is a
local cosmetic acknowledgement, never a financial mutation. If that write fails,
the notification can be shown again; its grant cannot be duplicated.

## Retention and bounded failure

All pending receipts are retained. Each save retains the most recent 512 presented
receipts for cosmetic deduplication and retires older presented entries. The total
document remains limited to 8,192 receipts and 4 MiB. Reaching either bound with
unpresented work, corrupt bytes or a storage failure backpressures local
acknowledgement; pending notifications are not silently discarded to make room.

An ancient receipt replayed after its presented history was retired can show its
notification again. This is intentional bounded cosmetic deduplication. Financial
idempotency remains in the existing durable model/server ledger and does not rely
on retaining presentation history forever.

## Recovery scope and open acceptance

This is same-device recovery while the player's local intent/outbox survives.
It does not enumerate all server reward or commerce history, provide an
all-history inbox, or reconstruct presentation state on a different device or
after deleting local application data. Backend purchase-order recovery and stable
player identity are separate from this cosmetic limitation.

The first-clear Home reveal and rewarded-video presentation have not been migrated
to this outbox. Their existing financial durability is unchanged. Local/offline
review reward services are not silently replaced with server grants. Practice
Rain Cup remains labelled practice; no live competition or new prize schedule is
implied. Live SDK, backend hosting, provider configuration, bank-return/payment
acceptance and broader device/performance testing remain separate launch gates.

Native fixtures are prepared for full-grant dimensions, storage fault/restart
boundaries, cancellation and ownership; this contract does not label preparation
or source inspection as a passing Unity/device test. Consult the checkpoint 100
review and gallery for the actual executed evidence and its source epoch.

For native image captures, establish the final canvas and render-target scale
before building and fitting text, as ordinary page layout does. Changing scale
after fitting can clip a small label even though its earlier mesh was valid.
Check glyph geometry and pixels at the final scale, then inspect the saved image;
the existence of a text object or an earlier mesh does not prove visible text.

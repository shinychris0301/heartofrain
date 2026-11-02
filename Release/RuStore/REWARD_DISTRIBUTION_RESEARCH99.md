# Reward distribution research and recommendation — review 99

Reviewed 27 October 2026. This is a design recommendation and a review of the
current implementation, not a change to the approved reward quantities. Prices
and the one-time Special-offer policy are separately approved by the owner.

## Findings from existing games

| Game / official source | Verified pattern | Recommendation for Heart of the Rain |
| --- | --- | --- |
| [Royal Match — coins](https://dreamgames.helpshift.com/hc/en/3-royal-match/faq/21-how-can-i-obtain-and-use-coins/) | Coins come from completed levels, remaining moves, area chests, bonus levels, events and purchases; they pay for moves, lives and boosters. | Make ordinary progress a dependable resource source, with larger rewards at meaningful milestones. A remaining-move bonus is a candidate requiring a separately approved formula and replay rules. |
| [Royal Match — Team Battle](https://dreamgames.helpshift.com/hc/en/3-royal-match/faq/109-team-battle/) | Qualifying members of a top-five team get the same team prize; top contributors get additional rewards. Participation requires a completed level. | Publish eligibility before entry, freeze the eligible team roster, and distinguish shared team rewards from personal contribution bonuses. Do not launch prizes against simulated or demo standings as real competition. |
| [Homescapes — Daily Bonus](https://playrix.helpshift.com/hc/en/14-homescapes/faq/16310-daily-bonus/?f=what-power-ups-can-i-get-in-the-game-and-how&p=all&s=boosters-and-power-ups) | A daily calendar mixes resource types, with larger seventh-day and monthly rewards and an online claim requirement. Its missed-day rule restarts the sequence. | Keep the existing seven-day mixed-resource schedule and clear Day 7 emphasis. Preserve this project's existing missed-day behavior; copying another game's reset penalty is not part of this change. |
| [Candy Crush Saga — Daily Treat Machine](https://candycrush.zendesk.com/hc/en-us/articles/4402467400849--Daily-Treat-Machine) and [timed boosters](https://candycrush.zendesk.com/hc/en-us/articles/360002352858-What-are-timed-Boosters) | Login progression increases reward tiers. Timed boosters apply during their real-time duration, which continues while the player is away. | Offer a clear daily progression and keep durable item rewards distinct from timed entitlements. Do not add timed rewards until expiry, stacking, background behavior and UI are implemented. |
| [Match Villains — publisher listing](https://www.goodjobgames.com/games) | The publisher confirms the reference game's layered-obstacle/progression format, but this source does not publish a complete, authoritative payout table. | Continue using it as the gameplay reference. Do not present unverified fan/hub reward quantities, store prices or inferred backend rules as its official economy. |

These observations describe product patterns, not a universal industry price or
payout standard. Exact rewards can vary by event, account, platform and version;
the recommendation below is based on our own approved economy.

## Recommended reward layers

1. **Level completion:** retain 50 coins and one star for an eligible first clear.
   Losses and replays do not repeat that grant. Keep the victory celebration,
   return Home, then reveal the already committed reward there. An animation must
   never be the authority that grants it.
2. **Daily Gift:** retain the approved seven-day schedule: 50 coins; Rocket;
   75 coins; Bomb; 100 coins; Hammer; 150 coins plus Orb. Use one durable claim per
   eligible server-controlled day. Make the Day 7 reward visible in advance.
3. **Wellworks:** retain permanent first-clear milestones at 10/20/30/40/50.
   Treat each as a separate once-only entitlement; do not spend stars or advance
   it through replays. Keep coin and item rewards mixed.
4. **Rain Cup:** keep current practice labeling and existing provisional rewards.
   Real prizes require a real event service, verified scoring, a frozen end
   result, tie rules and durable once-only claims. Participation and team-change
   rules should be shown before joining.
5. **Rewarded video:** preserve the approved optional Shop offer, 400 coins,
   three completed rewards per player-local day and a 600-second cooldown.
   Availability and the day boundary must be server-controlled; changing a device
   clock or reinstalling must not create another allowance. The current capped,
   client-reported completion mode is not cryptographic proof of ad viewing.
6. **Purchases:** a verified coin or bundle purchase grants all advertised
   contents together. Returning from payment restores the waiting level or
   continuation offer; it does not automatically spend the purchased currency.
   Continue remains a separate explicit 900-coin purchase.

## Current budget and balance implications

These are arithmetic on existing configuration, excluding the initial wallet,
paid purchases, Cup prizes and item valuations:

| Source / sink | Current amount |
| --- | ---: |
| All 50 eligible first clears | 2,500 coins + 50 stars |
| All five Wellworks milestones | 500 coins plus the configured items |
| One seven-day Daily Gift cycle | 375 coins plus Rocket, Bomb, Hammer and Orb |
| Maximum three video rewards in one local day | 1,200 coins |
| Maximum video rewards across seven eligible local days | 8,400 coins |
| One extra-moves purchase | 900 coins for five moves |
| Full life refill at zero lives | 900 coins for five lives |

The entire chapter and Wellworks together supply 3,000 earned coins; seven fully
used ad days supply 2.8 times that amount. One video's 400 coins also exceed the
coin portion of a complete seven-day gift cycle. Items add value but have no
approved coin-equivalent valuation, so these are coin comparisons only.

Consequently, the approved ad offer can become the dominant renewable coin
source. Keep its approved values now; measure claims per active player, coins
earned per source, continuation/refill spend, inventory usage and first-clear
progress before recommending a balance revision. Do not change quantities on an
assumed competitor standard. After level 50, finite first-clear/milestone rewards
stop; the next-content and repeatable-event plan must account for that boundary.

## Approved shop policy and value review

| Offer | Coins | RUB | Availability policy |
| --- | ---: | ---: | --- |
| Wellkeeper | 2,000 | 99 | Special: one per stable player and offer |
| Rainy Day | 3,500 | 199 | Special: one per stable player and offer |
| Rainlight | 6,000 | 299 | Special: one per stable player and offer |
| Village | 5,000 | 399 | Mega: repeatable |
| Festival | 10,000 | 599 | Mega: repeatable |
| Keepers | 25,000 | 999 | Mega: repeatable |

All existing tool and starting-item quantities are preserved. The 6,000-coin
Special package provides more coins/tools than the 5,000-coin Mega package at a
lower price. The owner selected one-time Special promotions to distinguish them
from repeatable Mega packs. This is currently recorded as a configuration policy;
it must be enforced by a durable backend eligibility record, not by a device flag
or UI label. The real checkout remains disabled until implementation and provider
acceptance are complete. See `bundles.pending.json` for exact grants and limits.

## Delivery structure and remaining implementation

Use a versioned reward definition, a separately recorded entitlement and a durable
receipt. The server validates the stable player, source, eligibility and frozen
grant before changing balances. Source keys should distinguish an attempt, daily
claim, milestone, Cup result, ad opportunity and store transaction. Retries return
the original result; conflicting terms are rejected.

The current backend already supports a full `Grant` containing coins, stars,
four starting-item counts and four tool counts. `service.py::_grant` writes the
reward receipt and calls `wallet.py::reward_projection`; the wallet projection
records its immutable origin/delta in the surrounding database transaction.
Those are existing implementation facts, not evidence of configured production
services.

The purchase path is still coins-only: `wallet.py::commerce_projection` accepts a
coin amount. Bundle activation therefore requires freezing a full Grant in the
order, projecting the full inventory grant and receipt atomically, and reserving
the one-time Special entitlement under stable player/offer identity. A durable
pending order must be resumable without opening another one-time order; a failed
or cancelled order must release its reservation according to a defined policy.
Verified completed payment, repeat callbacks, lost acknowledgements, restart,
concurrent orders, recovery on another device, refunds and account deletion all
need explicit coverage before enabling checkout.

The UI should render pending/claimable/claiming/claimed/retry states from service
results and receipts. Queue Home reward reveals from committed receipts; dismiss,
skip, resize or termination during animation must not lose or duplicate a grant.
Provide a recovery/inbox route for already earned rewards that were not displayed.
Keep purchased inventory separate from promotional eligibility in the ledger.

**No new reward schedule, timed booster, live competition, bundle fulfillment or
production claim is implemented by this research document.** Only the approved
prices and one-time Special policy are being recorded/applied in checkpoint 99.

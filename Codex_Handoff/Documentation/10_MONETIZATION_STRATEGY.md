# Monetization strategy — proposed, testable plan
Commercial recommendations, not implemented features or guaranteed results. No actual revenue, retention, payer or acquisition dataset was supplied. Workbook values are illustrative assumptions, not market benchmarks.

## Objective
Optimize long-run **net contribution per acquired player**, while preserving the satisfying match loop and story. Gross sales alone can hide refunds, fees, advertising costs, churn and content expense. Establish retention, reliable state and enough content before scaling acquisition. Fifty levels can be exhausted; treat content supply as a commercial dependency.

## Recommended sequence
| Stage | Revenue design | Why / gate |
| --- | --- | --- |
| Reliability first | No live charging until save/attempt/ledger are durable | Prevent lost purchases, free stock resets and duplicate rewards |
| Initial soft launch | Transparent coin packs and a small bundle ladder | Easy to understand and reconcile; separate Rocket/Bomb and all tool quantities |
| First conversion test | One-time starter bundle after demonstrated engagement | Test eligibility/timing without blocking onboarding; no assumed price optimum |
| Retention/value test | Chapter-themed resource bundles or earned event rewards | Tie value to well restoration/craft/story, not generic pressure |
| Optional ad test | Voluntary rewarded placement outside critical gameplay/cinematics | Measure incremental contribution versus IAP cannibalization and retention |
| Later scale | Real events, team goals, potentially a pass | Only after cadence, backend and content capacity exist |

Avoid forced interstitials in the initial proposal. A voluntary reward should state the exact benefit before the player opts in; no-fill, cancel and failed validation must be clear. Any rewarded extra-move/continue offer needs a new approved mechanic and unified attempt handling; it does not exist now. Cosmetics or a pass need new design review rather than placeholder products.

## Current shop audit
There are 12 mock offers: three Special, three Mega and six coin packs. These are presentation data, not registered SKUs or validated prices. Important inconsistencies:
- Wellkeeper Kit has 2,000 coins plus items for the same displayed $1.99 as the 1,000-coin pack. This can be a deliberate restricted starter offer; unrestricted availability would undermine the coin pack.
- Rainlight Reserve displays 6,000 coins, three of each tool and three of each starting power for $6.99. Village Treasury displays 5,000 coins, two of each tool and three of each starting power for $9.99. Under the current contents/availability, the cheaper offer dominates the more expensive one.
- `boostersEach` and the four starting-power fields need an explicit grant breakdown; do not show Rocket+Bomb as a single reward.
- Hardcoded dollar labels must become store-supplied localized prices. Demo availability does not implement one-time limits, expiry or eligibility.

Before pricing, construct a value ladder using an approved economy. Define offer purpose, comparable item utility, eligibility, repeatability, region, product IDs, actual duration if any and a fallback when unavailable. Discount claims must compare a real reference value. Test different contents/timing independently so the cause of improvement is measurable.

## Economy design
Current first-clear reward is 50 coins +1 star; replay earns no new first-clear reward. Current initial stocks and lives are review defaults, not balanced production grants. Define each resource's use before selling it: coins as soft currency, stars as story/restoration progression if approved, lives as an attempt gate with explicit recovery, starting powers as planned assistance, tools as targeted control. Do not sell stars until their progression role is agreed.

Create a complete faucet/sink ledger: first clears, daily/event/team rewards, purchases and optional ads versus tools, refills, continues and cosmetics that are actually approved. Model per100 attempts and pernew-player cohort. Track free/paid currency separately for analysis, without hiding paid-item value. Tune resource availability against observed use and progression, not arbitrary scarcity. Keep all levels reasonably completable without purchase and never secretly change RNG/difficulty based on spend status.

The workbook's economy sheet proposes example tool/refill/continue costs only to expose balance mechanics. They are **not approved live prices or implemented sinks**. The current code has no complete coin-spend service or life-regeneration service.

## Offers and events in this story
Use restoration supplies, lantern craft, rainlight and the village well as content themes. A real event can reuse approved board/obstacle language with clearly scoped rules, earned progress and a transparent optional bundle. Don't add an event badge with a fake perpetual countdown. First-start story and chapter finales should have uninterrupted emotional pacing. In later tragic chapters, no “save Mila” sale or celebratory purchase framing around her death.

Home already reserves event positions, but current timer/status strings are samples. Proposed rollout: one real recurring event at a time, with server start/end, eligibility, reward claims, fallback, localized strings and support tooling. A pass needs enough reward content and consistent season cadence; do not use a subscription for benefits that do not recur reliably.

## Acquisition and retention economics
Use cohort install date, platform, country, campaign and content/config version. Compare actual net revenue and service cost against acquisition spend. Evaluate D1/D7/D30 retention, level completion/quit curves, session quality, payer conversion, repeat purchase, refund rates and content exhaustion together. High ARPPU with collapsing retention is not evidence of a healthy design.

Scale spend only when mature cohorts support contribution LTV above acquisition cost with an uncertainty margin and sufficient cash runway. The workbook's90-day horizon is not lifetime; linear retention interpolation is a sensitivity tool, not a forecast. Use measured country/platform-specific data and tax/fee treatment. Platform fees are eligibility/territory dependent; 15% is merely an editable example [S7, S8].

## Proposed experiment order
1. Onboarding clarity and first-session completion before offer pressure.
2. Starter-offer timing and eligibility; one variable at a time.
3. Bundle contents/value ladder; eliminate dominated options first.
4. Optional rewarded placement with an IAP/retention holdout.
5. Event participation and earned reward pacing.
6. Acquisition creative based on actual gameplay, then channel/country expansion.

For each experiment pre-register hypothesis, eligible population, primary metric, guardrails, minimum detectable effect/power based on baseline data, duration covering relevant cycles, and analysis date. Do not pick a fixed sample size without variance/base rate. Avoid repeated significance peeking. Report confidence intervals and absolute effects, not only percentage uplift.

## Operating dashboard
Daily: crashes, transaction failures/unacknowledged grants, currency anomalies, stuck levels, content exhaustion, revenue reconciliation. Weekly: cohorts, progression funnels, payer repeat rate, offer conversion, ad incremental value, support/refunds, content production throughput. Monthly: contribution by channel/region/platform, cash costs, experiments and release readiness. Assign an owner to each anomaly and a rollback path.

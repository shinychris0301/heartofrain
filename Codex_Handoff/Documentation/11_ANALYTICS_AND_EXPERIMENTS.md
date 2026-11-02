# Analytics and experiment specification — proposed

## Common envelope
Every event should have event_id, schema_version, occurred_at_utc, received_at_utc, pseudonymous_player_id, session_id, app/build version, platform, locale, content_version and config_version. Add experiment_id/variant only after stable assignment. Gameplay adds attempt_id, level_id, level_data_hash and RNG version/seed where diagnostic policy permits. A retry is a new attempt; cascades are not new moves.

Do not send names, chat contents, emails, raw purchase receipts or payment tokens into general analytics. Use redacted ledger references for commerce reconciliation. Apply consent/retention policies appropriate to actual SDK behavior. Keep analytics failure from blocking gameplay or purchase fulfillment.

## Event dictionary
The machine-readable version is `Analytics_Events.csv`.
| Event | Trigger | Essential fields / deduplication |
| --- | --- | --- |
| first_open | First install/profile initialization | install_id; once per install, distinct from returning login |
| session_start | Foreground session boundary | session_id; define inactivity boundary consistently |
| tutorial_step | Stage transition/skip | stage, action, elapsed; transition ID |
| level_start | Start grant committed | attempt_id, level, selected stock, moves, goals; once per attempt |
| level_end | Durable outcome committed | outcome, moves_used, duration, remaining goals, tools_used; once per attempt |
| booster_use | Accepted tool/start debit | item_id, count, attempt_id, transaction_ref; never on mere selection |
| power_activate | Model activation | kind, combo_kind, chain_depth; aggregate/sample if volume is high |
| currency_change | Ledger commit | currency, delta, reason, resulting_balance, ledger_ref; one per ledger entry |
| offer_impression | Offer meaningfully visible | offer_id/version, placement, eligibility; dedupe per visible interval |
| offer_click | Purchase detail/buy intent | offer_id, placement; not a purchase |
| purchase_start | Store flow initiated | product_id, platform, offer_version, request_id |
| purchase_result | Verified state transition | verified_state, ledger_ref, amount/currency/tax basis; distinguish paid/granted/refunded |
| ad_opportunity | Eligible reward placement shown | placement, reward, eligibility; denominator before request |
| ad_result | Request/show/complete/fail/verified reward | opportunity_id, network result, grant_ref; no reward from view alone |
| story_event | Opening/ending viewed/skipped/replayed | chapter, scene, locale, completion; no full story text |
| event_progress | Real event increment/claim | event/version, progress, claim_ref |
| error | Recoverable/fatal classified issue | code, subsystem, diagnostic reference; no sensitive payload |

Purchase revenue should come from the reconciled ledger/store reports, not button clicks or duplicated client callbacks. Server and client events must share correlation IDs, not both count as two purchases. Offline queues keep occurrence time and event ID; receiving a delayed level_end must not create a second attempt.

## Metric definitions
| Metric | Definition |
| --- | --- |
| Dn retention | Install-cohort users active on exact day n / eligible installs; separate rolling retention |
| Win rate | Unique won attempts / ended attempts; also report abandoned/incomplete attempts separately |
| First-attempt win rate | New levels won on attempt1 / new levels started; do not blend retries |
| Payer conversion | Unique verified payers / eligible active users over stated window |
| ARPDAU | Revenue with explicit gross/net basis / DAU, same day and population |
| ARPPU | Revenue / unique payers in the same window; not purchases per payer |
| Offer conversion | Unique verified purchasers attributed to offer / eligible exposed users |
| Ad completion | Completed rewarded views / started views; separately report request fill and opt-in |
| Cohort LTV90 | Cumulative90-day net contribution / cohort installs; horizon is explicit |
| Net ROAS90 | Cumulative90-day net revenue / paid acquisition spend; costs excluded, unlike contribution |
| Payback | Earliest day cumulative contribution covers acquisition spend; no payback if never reached |

## Experiments
Assign by stable player ID and experiment version; persist the assignment. Exclude QA and transaction-fraud traffic by predeclared rules. Keep an unexposed holdout for monetization additions. Segment results by platform/region/progression only where sample size supports it; avoid post-hoc cherry-picking. Refunds, crashes, support complaints and retention are guardrails. Freeze level/config behavior during the experiment or stratify/version it explicitly.

Suggested experiment records are in `Experiment_Backlog.csv`. All proposed treatments require implementation/design review; none is live. Use practical significance and uncertainty, not a revenue uplift claim unsupported by data.

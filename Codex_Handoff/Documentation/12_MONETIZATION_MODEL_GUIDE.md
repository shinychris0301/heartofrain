# Monetization model guide
Workbook: `Monetization/Heart_of_the_Rain_Monetization_Model.xlsx`.

All blue input cells are editable. Example assumptions are deliberately not labeled as market benchmarks. Replace them with actual data by platform/country/cohort. Black cells contain local formulas; green formulas reference another sheet. Do not overwrite calculated cells when running a scenario.

## Monthly Model
Inputs include days, average DAU, MAU, payer conversion, average monthly spend per payer, fee/refund rates, rewarded-ad participation/opportunities/fill/net publisher eCPM, service cost, fixed content/operations cost, paid installs and CPI. IAP input is ex-tax player spend before platform fee/refunds. Ad eCPM is publisher-net; it is not charged a second platform IAP fee. Monthly contribution subtracts service cost, fixed operating cost and acquisition spend; it is not audited accounting profit and omits financing/income taxes.

The model assumes MAU payer conversion and ARPPU in the same month. It does not derive MAU from DAU. Ad opportunities are per participating DAU-day; fill is the fraction becoming a paid impression. Do not multiply by opt-in twice. Use net settlement reports to calibrate the simplified refund/fee assumptions.

## Cohort 90d
This is a sensitivity model from Day0 through Day90 inclusive. Retention is piecewise-linear between editable D0/D1/D7/D30/D90 anchors. It is not fitted to real cohorts. A monotonicity/range flag warns about invalid anchors. Per-active-user-day IAP/ad/service rates are separate explicit assumptions; monthly payer conversion is not automatically a daily rate.

Outputs: LTV90 net revenue, LTV90 contribution before acquisition/fixed costs, net ROAS, paid cohort contribution after acquisition, and modeled payback day if any. Shared fee/refund assumptions link to Monthly Model. No extrapolation beyond Day90 is presented as lifetime value. Break-even CPI is contribution per install over the modeled horizon, before fixed costs and uncertainty reserve.

## Economy
The 50-coin first-clear reward is verified in PreLevelAssets. Other daily/level-use/cost inputs are examples for future design. First-clear share means the fraction of wins that are first clears. Gross faucets and sinks are calculated per100 attempts; there is no actual revenue or purchase conversion forecast on this sheet. Tool/refill/continue costs are proposed and not implemented. The estimated levels-to-afford indicator assumes first-clear rewards only and does not predict player behavior.

## Use safely as a decision tool
Run low/base/high cases, zero-ad cases and higher-fee/higher-CPI cases. Watch retention sensitivity: monetization uplift can be erased by churn. Compare mature measured cohorts rather than trusting a single input combination. Keep assumptions, period, geography, currency and source notes with exported results. Numeric targets for launch must be agreed using actual baseline data.

# 99 - Launch presentation and bundle prices

**REVIEWED_WITH_OPEN_ACCEPTANCE_GATES.** The requested startup/icon, automatic
obstacle-card and bundle-price changes are verified in the recorded cases.
Coverage is one physical phone and defined native fixtures. Whole-app/backend,
human-campaign, broader-device, provider and performance acceptance remain open;
`fullyVetted=false`, `taskComplete=false`, `productionApproved=false`.

[Current installed Android test APK](../../Unity/Builds/Review99/HeartOfTheRain_Review99_Android_Test.apk)
- **319,164,540 bytes**, SHA256
`3097318517a159affe2596d520909c5855e00c2f2d54fb76ca4389f74445d1f8`.
It is an SDK-free, test-signed Development build from the isolated Unity
**6000.3.27f1** copy, with remote script debugging/profiler attachment disabled.
The candidate package/signing identity is retained. Main Unity **2022.3.62f3** and
its settings are not promoted or upgraded. The startup/license gate preserves
required Unity2022 branding; the supported Unity6 splash settings are disabled.
[Exact artifact and native/static bindings](../../Verification/Evidence/Review99/AndroidArtifact99.json),
[gallery](../../Verification/Evidence/Review99/Comparison.html),
[summary](../../Verification/Evidence/Review99/Summary.json).

## Changes and evidence

| Item | Implemented behavior | Demonstrated scope |
| --- | --- | --- |
| Launcher icon | Derived adaptive padding keeps the existing heart/water motif inside the mask. Original PNGs and existing GUIDs remain unchanged. | Root viewed the actual phone launcher crop: tip and ring visible inside the rounded mask; native geometry checks pass. Other OEM launchers remain a device-matrix gate. |
| Screen before opening | A bounded native black/icon cover prevents the selected build's observed transition from becoming an iconless black gap before opening artwork. | Two selected-default startup sequences reviewed through their relevant frames. Full native frame31 is separately reviewed; no exact interactive-ready or universal startup-speed claim. |
| New obstacle cards | No Continue button. Existing 0.18s reveal, then 1.5 fully visible unscaled foreground seconds; pause/background time is excluded. Board stays ready/input-blocked and attempt Reserved before one existing start commit. | Native UI plus on-device foreground and corrected in-card pause/resume fixtures; 24 moves retained and selected Rocket 5 to 4 once. Generic HUD dialogs/art/rules are unchanged. |
| Special/Mega prices | Six approved RUB labels appear in normal Shop previews/details, even though the inventory products remain unavailable for purchase. | Fifteen native locale-size states/180 details and four actual Shop OS captures reviewed: all six prices fit. No real purchase or grant is inferred. |
| Special policy | Once per stable player and offer; Mega remains repeatable. | Disabled proposal metadata and configuration tests only. Actual backend eligibility/cap enforcement and full inventory delivery are not implemented by this label or price change. |

[Source comparison](../../Verification/Evidence/Review99/SourceDelta99.json)
records 12 changed and 21 added Unity inputs, with no removed inputs. Existing
PNGs, existing metadata/GUID files, main ProjectSettings and M46/M48 source bytes
are unchanged from the bound98 manifest. Changes are concentrated in launch
instrumentation/native integration, the HUD/level-flow timing, Shop presentation
and their verification. New script/library metadata is distinguished from changes
to existing asset identities.

## Approved prices and unchanged contents

| Offer | Coins | Each of four tools | Each of four starting items | RUB | Approved policy |
| --- | ---: | ---: | ---: | ---: | --- |
| Wellkeeper Kit | 2,000 | 1 | 1 | 99 | Once per stable player and offer |
| Rainy Day Bundle | 3,500 | 2 | 2 | 199 | Once per stable player and offer |
| Rainlight Reserve | 6,000 | 3 | 3 | 299 | Once per stable player and offer |
| Village Treasury | 5,000 | 2 | 3 | 399 | Repeatable |
| Festival Chest | 10,000 | 4 | 6 | 599 | Repeatable |
| Keeper's Collection | 25,000 | 8 | 12 | 999 | Repeatable |

Tools remain Hammer/Axe/Ram/Atlas; starting items remain Rocket/Bomb/Rainbow Orb/
Golden Seeker. Coin-only packs retain1,000/99,5,000/299,10,000/499,25,000/899,
50,000/1,599 and100,000/2,999 RUB. The exact parsed comparison to archived98 data
finds only six new Shop `priceLabel` values and zero reward changes.
[Reward/commerce preservation](../../Verification/Evidence/Review99/Commerce/RewardPreservation99.json).

Every bundle remains `available=false`; checkout is disabled. Preview labels
never enable delivery, and an unavailable non-preview product cannot fall back
to a preview quotation. Configured actual coin checkout still uses SDK
`GetProducts.amountLabel` and server-verified order terms. Current backend
commerce is coin-only; assigning a price cannot deliver advertised inventory.

The complete disabled plans and minor-unit amounts are in
[bundles.pending.json](../../Release/RuStore/bundles.pending.json). Special
eligibility must be persisted on the server by stable internal player ID plus
offer ID, with atomic reservation/delivery, retries/restart/recovery and refund
handling. A device preference, reinstall or UI label cannot enforce it. The
proposal explicitly records `purchasePolicyEnforced=false`. Real Console
products, full Grant order terms, inventory fulfillment/caps and provider
acceptance are required before activation. No star, reward quantity or mechanic
was changed. [Owner setup](../../Release/RuStore/OWNER_SETUP.md).

## Native and configuration verification

| Execution | Result | Limit |
| --- | --- | --- |
| Main2022 General |535 checks pass | Native import/model checks, not physical/human campaign certification |
| Main2022 Shop |2,236 checks,15 locale-size states,180 details pass;6 bundle mappings | Actual Editor rendering/listeners; no IAP/provider or device proof by this count |
| Main2022 NoMoves/timed UI |60,286 checks,255 layouts including105 timed cards pass | Offscreen Editor foreground is explicitly simulated |
| Main2022 final startup/license gate |28 checks pass | Earlier startup01/02 epochs retained; main mandatory branding preserved |
| Isolated6 configuration/core/startup |19 /7,429 /28 checks pass | Recorded configuration/source epochs; later compression selection is separate |
| Selected default Android build/static |0 errors/0 BuildReport warnings;22 native build checks/static validation pass | SDK-free Development/internal signing; three stock IL2CPP translation notices remain |
| Current price/policy tests |7 tests,0 failures/errors/skips | Python configuration/schema only; no native worker or real cap/delivery execution |

[Native index with individual source manifests](../../Verification/Evidence/Review99/NativeCoverage99.json),
[host price/policy tests](../../Verification/Evidence/Review99/Commerce/Policy02/PricingTests.json),
[non-runtime policy freeze](../../Verification/Evidence/Review99/Commerce/SourceFreeze99Policy02.json).
The earlier six-test policy epoch and first wrong-media-environment import failure
are retained separately. The successful tests use the existing Backend virtual
environment; no new dependency installation was needed.

[All 57 backend service-module and JSON-config files](../../Verification/Evidence/Review99/Commerce/BackendSourcePreservation99.json)
match archived98 bytes. The previous 473-test full suite and 199-check TCP/restart/
backup-restore rehearsal remain historical; they were not rerun in 99. Current
backend-side executions are the seven price/policy configuration tests above.
Neither old nor current local tests certify live hosting/providers or capacity.

Zero BuildReport warnings is not a universal toolchain-warning clearance. The
selected build retains three stock IL2CPP large-method translation notices.
The historical425 bundled C diagnostics remain separate/unmodified; no compiler
suppression or vendor patch is claimed.

## Physical startup, icon and size comparison

All media event times below are exact decoder PTS relative to each recording,
classified from actual root image views. They are not launch-request, Android
TTID/fully-drawn, touch latency or interactive readiness. Static-frame gaps are
retained rather than interpolated. Candidate thumbnail changes do not classify
semantic events automatically.

| Run | Opening artwork | Home observation | Scope |
| --- | --- | --- | --- |
| Previous98 baseline |First recorded frame49,5.025378s |First recorded frame166,12.313311s | Root viewed0-239 plus Representatives/full10/49/166; preceding frames via sheets |
| Selected default run1 |First recorded frame53,4.082611s |First recorded frame150,11.669511s | Root viewed0-239/full53/146-150;146-149 still opening. Native icon before logo, no extra iconless black frame at observed handoff |
| Selected default run2 |First recorded frame32,2.536611s |First recorded frame101,8.193644s | Root viewed0-119/full32/101;31 native icon/100 opening via sheet. No extra iconless black at observed handoff |
| Experimental LZ4HC |Recorded logo55,3.320456s |Home observed105,6.320489s; earliest Home not separately confirmed |600,188,497-byte experiment rejected; genuine black54 lasts14.133ms before55. Independent raw-pixel/index audit confirms no derivative corruption |

Runtime/assets are the same between the99 compression variants. The selected
prior/default compression is319,164,540 bytes; LZ4HC materially expands the APK.
The observed run-to-run variation and cache/order/configuration limits prevent a
universal or controlled causal speedup claim. The600 MB variant remains private
and unselected. [Confirmed startup/launcher review](../../Verification/Evidence/Review99/Phone/RootVisualReviewStartupVariants99.json),
[full selected native icon31](../../Verification/Evidence/Review99/Phone/RootVisualReviewNativeIcon31.json).

Raw video, OS launcher/home transitions and full contact sheets remain private.
Eight unedited safe app images are selected for the gallery, with original OS,
cropped OS and decoded-video derivatives labelled separately.

## Actual automatic introduction and pause boundary

The foreground Android fixture passes 198 checks and measures 1.505695 fully
visible foreground seconds. Root viewed Representatives/full190 card without
Continue/full284 board. The corrected same-APK Pause02 case passes 136 checks;
root viewed every frames 120-359 plus full186/251/308/333: card, OS leaving the
app, the same card resuming, then automatic dismissal. The recorded state is
Reserved at 0.101198 foreground seconds before Home, still Reserved/paused at
0.757138, then Started at 1.500285. Selected Rocket 5 to 4 occurs once; 24 moves,
wallet and life are retained within the disposable-memory fixture.

Approximately 3.21 seconds measures Home-command completion to resume request,
not exact `OnApplicationPause` duration. Native paused snapshots and the video
establish the tested visible boundary. Source clock checks and the105 Editor
card layouts remain complementary evidence, not physical foreground proof on
other devices. [Confirmed foreground/Shop review](../../Verification/Evidence/Review99/Phone/RootVisualReviewPricesForeground99.json),
[confirmed corrected pause review](../../Verification/Evidence/Review99/Phone/RootVisualReviewTimedPause99.json).

The original Background01 retains 212 native PASS checks and one gameplay
pause/resume. Its video shows that the intro had already dismissed before Home;
it does not establish the intro-pause rule. This scope limitation is retained,
then covered by the pre-armed same-APK Pause02 successor without a rebuild.
Only stone has this physical newcomer-card fixture; other families have native
selection/art/layout coverage. Existing connected fail-to-Home introduction
repetition remains the documented history limitation.

FinalHome03 is the latest fresh-process normal English Home readback, with the
original OS image reviewed. Candidate saves/preferences and current original
package absence are preserved by receipts. The cause of original-package absence
remains unknown; no owner data was recreated/restored. The existing valid English
preference and route are preserved. [Latest normal state](../../Verification/Evidence/Review99/Phone/FinalHome03/Report.json).

## Reward distribution and remaining launch work

[The research memo](../../Release/RuStore/REWARD_DISTRIBUTION_RESEARCH99.md)
uses primary Royal Match, Homescapes and Candy Crush patterns and excludes
unverified Match Villains payout quantities. It separates current implementation
from recommendations. [Bound arithmetic](../../Verification/Evidence/Review99/Research/RewardBudget99.json)
gives 2,500 chapter-first-clear coins, 500 Wellworks and 375 per seven-day gift
cycle. The potential capped ad allowance is 1,200/local day or 8,400/seven eligible
days, 2.8 times chapter plus milestones. This is a budget, not available/viewed
ads; items have no approved coin-equivalent valuation. Quantities, missed-day
rules, timed entitlements and remaining-move payouts were not changed. Measure
income/spend/claims/inventory before proposing another economy revision.

[Historical98 device coverage and corrective measures](../../Verification/Evidence/Review99/DeviceCoverageFrom98.json)
remain one-phone evidence, including prior refill/display corrections, partial
campaign FAIL and separate connected successor. The prior quiet diagnostic still
contains a 66.55ms interval and 47.26ms command span. No new full campaign/backend
suite, dense-effects benchmark, long-session result or whole-game smoothness
approval is inferred from99 startup/UI work.

Release still needs a human 50-level campaign/balance review, Android 8/API 26/
tablet/broader-device coverage, ordinary configured backend/account/social flows,
production hosting/HTTPS/operations, actual SDK/products/payment notifications/
bank-return/recovery tests, real ad/account providers, bundle inventory/cap
fulfillment, release signing and Russian legal/storage/retention/moderation setup.
The SDK-free internal APK and one-phone cases do not certify those integrations.
Current requested changes are verified within these exact scopes; full app,
backend, production and performance acceptance remain open.

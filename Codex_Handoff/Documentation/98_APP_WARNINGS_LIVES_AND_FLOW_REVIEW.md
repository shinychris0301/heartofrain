# 98 - App warnings, lives and gameplay flow review

**REVIEWED_WITH_OPEN_ACCEPTANCE_GATES - not complete, fully vetted or production approved.**

The requested UI, refill, pricing and introduction changes are implemented. Actual
phone testing also exposed a stripped SpriteMask native dependency and literal
question marks in Russian Continue loading text; both have scoped repaired-build
verification. The final internal APK builds with zero errors/zero BuildReport
warnings and runs on the real phone. Root reviewed the final loading/exhaustion
sequence and normal relaunch. Performance, human campaign/device coverage and
configured live-provider/production gates remain open.

[Current final internal test APK](../../Unity/Builds/Review98/HeartOfTheRain_Review98_Android_Test_04.apk)
and [current scoped summary](../../Verification/Evidence/Review98/Summary.json).

This review addresses the owner's refill, start-level, continuation, button artwork,
Shop pricing and obstacle-introduction reports. It also audits project warnings and
the existing backend. The original project remains on Unity **2022.3.62f3**; Android
verification uses a separate **6000.3.27f1 LTS** copy. Preparing or testing that copy
does not promote the main project. The original phone package is now absent in a
fresh read-only user0 inventory; its cause is unknown. Earlier preservation
receipts remain timestamp-scoped. The repair upgrade preserves the candidate's
own APK/data baseline and the original package's continued absence, without
recreating or restoring owner data.

## Findings and changes

| Owner report | Finding and current source change | Acceptance |
| --- | --- | --- |
| Missing zero-life refill | Affordability previously determined whether the refill was shown. At zero lives the existing primary slot now displays **Refill 900** consistently. An insufficient wallet retains the offer with an unavailable state and explanation. The countdown sits above the single-line button in space freed by booster labels; the existing modal shell is retained. | Previous834e actual899/900 phone fixtures pass15checks each; root reviewed fitting offer, unavailable note and0coins/5lives after refill. Transient memory wallet; configured durable acceptance remains open |
| Tap Home lives to open start-level | The existing `OpenLives` route was already present. Verification now exercises the actual heart-position raycast and pointer-click route instead of relying only on a direct method call. | Native route and actual phone header taps pass; root reviewed the opened modal |
| Two out-of-moves displays | The local and connected continuation controllers no longer insert a separate timed banner before the Continue panel. Loading and the resolved offer use that panel; the board remains paused. | Native/controlled HTTP pass. Final cb2d repeat frames0-599 show a single loading/offer Continue panel without a separate banner. The discovered loading-text defect is fixed and visually rechecked; this is a bounded sequence, not global timing acceptance |
| Booster text labels | Removed the visible names below the four starting boosters. Icons, inventory counts, selection behavior and semantic control names remain. | Native checks and actual phone899/900 layout review pass within scope |
| Stretched failure/abandon buttons | The screenshot is the retained-attempt abandonment confirmation. Its existing approved primary/secondary artwork receives appropriate slice density and compact content-sized button widths. No replacement artwork or reward/life mutation is placed in animation callbacks. | Native layout and actual NoMovesEnd02 OS confirmation reviewed: compact undistorted buttons; fixture ends with four lives after one loss |
| Shop coin prices | Updated the four larger packs across both previews, current planning/deployment examples, setup documents and verification assertions. The two smaller packs stay unchanged. Actual configured checkout still displays SDK `GetProducts.amountLabel`. | Python/native checks pass; root viewed all six exact RUB prices together in normal phone Shop scroll. Live checkout remains unconfigured |
| Special/Mega prices | Six current bundles have no approved RUB price, registered product or inventory-delivery implementation. Their exact existing rewards and proposed IDs are recorded in `bundles.pending.json`; they remain disabled. A price alone cannot make the coin-only gateway deliver their items. | Owner price decision and fulfillment/provider work remain open |
| New obstacle introductions | Seven later newcomers receive a brief card using existing HUD artwork and localized instructions, with an explicit Continue and no timed dwell. Cards occur after board readiness but before `CommitStart`; input stays blocked and the attempt remains Reserved. Crate/moss remain covered by the existing first-time tutorial. Replays, retries and known previously started local attempts skip the card. | Previous834e actual stone first-encounter fixture passes9checks, including blocked input/no debit before Continue and Started24moves after actual tap; root reviewed legible card/full board. Other families retain native scope |
| Additional refill race | Connected refill previously lacked a pending-action lock and stale-view guard. A unique presentation ticket now blocks competing actions; account-generation/session/view guards reject stale or duplicate completions. An already committed refill retries its projection read without issuing another purchase. Service errors are no longer all labelled insufficient funds. Durable financial authority remains in services. | New presenter contract regressions pass; ordinary configured Android acceptance pending |

The obstacle index is checked against all fifty actual referenced level documents:
stone **7**, restoration jar **10**, sealed case **14**, water sluice **18**, Storm
Crystal **21**, Water Spirit Pod **28**, Rainlight Cabinet **36**. Descriptions follow
the live M46/M48 rules, including water-drop matches for sluices, power/tool damage
for sealed cases, damage-immune jars delivered through exits, shared crystals and
cabinet rainlights. No level mask, authored obstacle placement or gameplay rule is
changed by these introductions.

Introduction history is intentionally bounded. This is a first-appearance-level
rule, not a globally durable once-per-family flag. Local durable attempt history
also suppresses cards after an earlier started attempt at that level. Connected
mode projects only the current attempt: a direct retry or completed-level replay
skips its card, but failing an introduction level, closing to Home and opening it
again can show the card again. No backend/profile schema or seen-state has been
invented. This connected UX limitation remains open alongside configured-service
acceptance.

## Warning scope

Checkpoint97's full-game BuildReport recorded **112 warnings**: obsolete project
lookups, private unused/member-hiding fields and an Android icon configuration
warning. Source cleanup preserves first-active-match and InstanceID ordering,
clarifies bounded-download buffer names and removes unused private state; it does
not suppress diagnostics. Android icon configuration uses the existing approved
artwork. The final isolated Development BuildReport records **zero errors /
zero warnings**, and its log has zero C# warning lines. The first full compile
retains one legacy-icon warning, corrected by supported private-copy icon
configuration before the second build. Main remains Unity2022; the adaptive icon
assignments and splash settings belong to the isolated Unity6 copy. The final Dev04 compile still emits **three IL2CPP large-method translation notices**; Dev03 emits two stock Clang command diagnostics and Dev04 none. Those native-toolchain messages are distinct from BuildReport/C# warning counts. [Final measured warning summary](../../Verification/Evidence/Review98/WarningSummary98Final.json).

The first full compile also emitted **three IL2CPP large-method notices** and
**two stock Clang command diagnostics**. The clean second build reused compiled
native objects, so its quiet cached output does not prove those toolchain
diagnostics repaired. No gameplay semantics, vendor sources/binaries or compiler
warning flags were changed to silence them. [Measured warning summary](../../Verification/Evidence/Review98/WarningSummary98.json).

Separately, the historical97 native compiler log contains **425 diagnostics from
Unity-bundled IL2CPP/Mono C sources**, plus **two compiler-command diagnostics**.
These are a different stream from the 112 BuildReport warnings. The baseline is
catalogued in `BundledNativeWarnings_Baseline.json`; vendor binaries/sources and
compiler-warning flags are not patched or silenced. Do not report a universal
warning-free result from a zero project-C# or BuildReport count alone.

The first current pinned-2022 General run retains **533 passed / one failed**
checks. The new five-locale check exposed a French reward-label fit failure at
320 x 568. The reward label is now 85 units wide; the assertion remains in place
and the current main-Editor retest passes. The same initial compile exposed six additional project
diagnostics (a hidden `light` member, three obsolete sprite-packing-tag accesses
and two unused fixture events). Their source fixes are included in the final
source freeze and current C# logs are clear. The initial HomeLives suite also
retains a failure at its actual-heart raycast assertion after 3,269 attempted
checks. Its second tap now follows the normal canvas/lifecycle tick and records
hit-depth diagnostics; the actual raycast assertion is retained and the current
native route test passes. Repaired phone fixtures now confirm the route separately. These failures must not be replaced by the six
other passing initial invocations (obstacle rules, continuation transactions,
repeat moves, profile transactions, NoMoves UI/intro cases and RUB previews).
[Initial eight-run set](../../Verification/Evidence/Review98/SuiteSets/Targeted01/SuiteSet.json),
[General failure](../../Verification/Evidence/Review98/Native/Targeted01_General/Invocation.json),
[HomeLives failure](../../Verification/Evidence/Review98/Native/Targeted01_HomeLives/Invocation.json).

Root's interim native image inspection found that the cabinet introduction used
the collectible rainlight glyph instead of the obstacle itself. The card artwork
now reuses the already warmed pod/cabinet board sprites, without adding textures
or changing asset GUIDs. Root viewed the corrected Final03 native Russian
confirmation, pod and cabinet captures: compact buttons, actual unopened
obstacles and legible text are visible. Those are paused-board UI fixtures,
not ordinary first-encounter gameplay or physical-device proof. Physical artwork
acceptance remains pending; a non-null sprite binding alone is not visual acceptance.

The subsequent Final02 General and HomeLives runs passed on their recorded
source epoch. Final02 ProfileDesign then failed before its first assertion:
warning cleanup had removed a readiness field still read through reflection.
The original flag is restored behind a typed `IsPrepared` property and all three
readers now use that property. The four-file correction creates a new source
epoch; earlier passing invocations are not relabelled as tests of that correction.
Affected Profile suites, General/HomeLives/NoMoves and the remaining matrix were
rerun before the fresh LTS build. Independent caller/state review found no
additional cleanup-related reflection/state defect in the inspected paths; this
is not a global absence-of-bugs claim.
[Retained ProfileDesign failure](../../Verification/Evidence/Review98/Native/Final02_ProfileDesign/Invocation.json).
The affected Final03 ProfileM71, ProfileDesign and ProfileClarity invocations now
pass **8,244**, **382** and **270** checks respectively; the earlier failure remains
retained. The actual Final03 set has now completed with **30/30 passing
invocations**, no source-drift flag and **148,848 recorded countable checks**
(the General array is counted by its length; the loading-lifetime result records
cycles/boolean observations separately). This is the Final03 source epoch only;
it does not turn the earlier Final02 results into same-source runs or establish
LTS build/device acceptance.

The fresh Final03 strict account contract also passes **101 checks / eight cases**.
Its original clipboard assertion is unchanged: readback length **43**, exact match
true, one copy call and zero errors. No policy change or clipboard API workaround
was used. The historical93 failures remain; their Windows cause is unproved.
The separate connected Account HTTP result below now also passes within its
Editor/loopback scope; neither result establishes configured Android/provider
account acceptance.
[Current strict account receipt](../../Verification/Evidence/Review98/Native/Final03_Account/Invocation.json).

Five connected Editor HTTP case outcomes now pass using real isolated loopback
services: Identity **25**, Social **18,946**, Server gameplay **302**, Payment
transport **38**, and the Account retry **59** checks. The first four pass in
`HTTP00f41c98`; its original Account run retains a twelve-check Stage3 failure
because the fixture attempted the disabled backup action while the gateway was
still busy. The retry waits for actual UI readiness, not clipboard polling:
gateway-busy-at-open is true, there are **32 UI readiness waits**, backup/copy are
explicitly dispatched once, and the original clipboard assertion validates
**43 characters**. Recovery, rejected-code correction, preserved remote attempt,
explicit forfeit/logout/deletion/fresh guest and return to Settings execute.
The two runs and their source/fixture epochs stay separate; the first combined
HTTP failure is not converted into a pass.

The connected tests use actual current backend/SQLite traffic and the approved
Windows model worker, but controlled provider fixtures and trusted operator
level/seed setup. They are not live VK/Google/RuStore, Android or public-service
tests. [Original HTTP outcomes](../../Verification/Evidence/Review98/SuiteSets/HTTP00f41c98/SuiteSet.json),
[successful Account HTTP retry](../../Verification/Evidence/Review98/ConnectedRuns/HTTP6816992f/Invocation.json),
[actual Account observations](../../Verification/Evidence/Review98/Native/HTTP6816992f_AccountHttp/Native/AccountHTTP.json).

A later LTS import exposed **19 additional Editor/test API deprecations**. The
source-compatible repair uses 14 NamedBuildTarget calls, supported legacy-icon
kind enumeration and a private-fixture Gradle-path read. Runtime code is unchanged
from Final03; these tooling/test edits form another explicitly recorded epoch.
The fresh main-2022 General and release guard pass **534 / 328 checks** after that
repair. The isolated **6000.3.27f1** CoreChecks invocation passes **7,414 checks**
with stable main/project inputs. These native core/configuration results remain
separate from the actual Android build below.
[Main compatibility recheck](../../Verification/Evidence/Review98/Native/EditorAPI04_General/Invocation.json),
[release guard recheck](../../Verification/Evidence/Review98/Native/EditorAPI04_Guard/Invocation.json),
[LTS core checks](../../Verification/Evidence/Review98/Native/LTSCore02/Invocation.json).

The historical clean Dev02 LTS Development APK passed compilation and static checks:
**319,164,074 bytes**, SHA256
`08ff697b66cc958c64dfd7f8960188fe5477d6e8fdf47121548b10160fdc59ec`,
package `com.heartoftherain.review98`, ARM64/IL2CPP, portrait, SDK-free and internal
test signing. Supported splash/logo getters are false. Static validation covers
signature, zip alignment, manifest identity/orientation and ARM64 ELF/16KiB
alignment. The first one-warning build remains a separate retained result.
[Clean build](../../Verification/Evidence/Review98/Native/LTSBuildDev02/Invocation.json),
[static APK](../../Verification/Evidence/Review98/Native/LTSBuildDev02/StaticApk98.json).

The historical Dev02 APK was separately installed on the inventoried realme phone. Install02
passes and records the original owner APK/profile/preferences preserved at that time. Install01
remains a retained failure. Cold01 stopped while the phone was locked. After
unlock, Cold02 recorded startup but retained a final-focus guard failure; strict
Cold03 recorded its successor. Root viewed every decoded frame/contact sheet in
both sequences plus full opening/prologue images: portrait full display and
legible Russian text, with no Made with Unity logo observed over the roughly
20-second sequences. A brief black native window preceded the opening; instant
startup is not claimed. Current-at-that-time Dev02 music sounded normal to the
owner. These observations apply only to old08ff startup/display/audio, not to
gameplay readiness or later repaired-build observations.
[Separate install](../../Verification/Evidence/Review98/Phone/Runs/Install02/Report.json),
[retained cold stop](../../Verification/Evidence/Review98/Phone/Runs/Cold01/Report.json),
[root old-artifact startup review](../../Verification/Evidence/Review98/Phone/RootVisualReviewCold03.json).

After owner unlock, physical testing found a **real Unity6 runtime blocker** in
the Dev02 APK: tutorial Skip reaches `PracticeBoardView.Configure`, but the
required native `SpriteMask` class is stripped. Refill899_01 and NoMovesEnd01 fail
before their intended balance changes; their original failure evidence and the
timestamp-scoped data-preservation receipts remain. Passing Editor/compile/static checks did not establish this
player-only dependency. Dev02 must not be described as runtime-vetted or as the
recommended repaired build.

The approved repair is isolated to the Unity6 copy: explicitly retain the
installed built-in `com.unity.modules.tilemap`1.0.0 dependency while keeping
engine stripping enabled. Main Unity2022, vendor files, artwork and GUIDs are
unchanged. Native class registration now includes SpriteMask in the generated C++ check.
The repaired **Dev03** build/static validation pass with **zero errors/zero
BuildReport warnings**, **354,675,521 bytes**, SHA256
`834e715d3ac28be7c09b5f2998fe9201c3bb0d262667f17db597d2ab725efbd5`.
The same-signer candidate-only upgrade passes, and the subsequent original OS
capture shows a rendered Lesson1 board. This closes the observed missing-class
blocker for that tested path; it does not certify all gameplay.
[Repair preparation and official issue references](../../Verification/Evidence/Review98/SpriteMaskRepairPreparation98.json),
[retained refill fixture failure](../../Verification/Evidence/Review98/Phone/Runs/Refill899_01/Report.json),
[retained NoMoves failure](../../Verification/Evidence/Review98/Phone/Runs/NoMovesEnd01/Report.json).

Root viewed every decoded Cold04 frame, representative images and the subsequent
original OS capture: the Russian opening fills the portrait display and no
Unity/cube branding is observed. A brief black native window remains visible.
The last decoded video frame still shows opening/loading; Lesson1 appears in the
later OS capture, so reaching the tutorial within the recorded20seconds or a
precise startup duration is not claimed. The899/900 fixtures each pass15checks
using actual header/refill taps with a disposable memory profile. The900 tap
debits900 and grants all five lives without starting a level; duplicate callback
replay is synthetic. Root reviewed the unavailable899 offer and the900 result,
normal Shop prices, and six normal navigation captures. Five pages fill the
display with aligned bottom navigation; Teams/Leaderboard remain local/demo.
[Repaired artifact](../../Verification/Evidence/Review98/AndroidArtifact98Repair.json),
[candidate upgrade](../../Verification/Evidence/Review98/Phone/Runs/MaskUpgrade02/Report.json),
[root repaired core review](../../Verification/Evidence/Review98/Phone/RootVisualReviewRepairedCore98.json),
[899fixture](../../Verification/Evidence/Review98/Phone/Runs/Refill899_02/Report.json),
[900fixture and navigation](../../Verification/Evidence/Review98/Phone/Runs/Refill900_01/Report.json).

Root also reviewed the six ExtraPages01 destination captures. Daily Gift, practice
Rain Cup, Wellworks, Profile and Settings fit without overflow; the file named
`Quest_OS.png` is actually the Teams destination, not a separate Quest modal.
All six return files are byte-identical to the already viewed Home capture;
that return finding is hash-based identity, not six additional visual inspections.
No reward claim or provider action was performed in this navigation scope.
The physical stone introduction fixture passes9checks and its actual Continue
tap commits the ready board without spending a move. NoMovesEnd02 uses actual
taps with a disposable profile; root viewed the compact abandonment confirmation
and the final four-life retry state. These still images alone do not establish
the absence of an earlier banner; the final repeated-Continue sequence is reviewed below.
[Extra-page review](../../Verification/Evidence/Review98/Phone/RootVisualReviewExtraPages98.json),
[stone/abandonment review](../../Verification/Evidence/Review98/Phone/RootVisualReviewIntroNoMoves98.json).

NoMovesRepeat01's actual taps purchase two further five-move additions around
five programmatic real-playback moves; the native transaction fixture reports
wallet2150→350, lives5 and board retained. Root then inspected Representatives,
full decodedFrame00267 and every-frame sheets01–03 and found the Russian
loading body/button displayed as literal question marks. The Continue title and
later offer remain legible. No separate banner was observed in that reviewed
exhaustion/second-Continue segment; the remaining video is not yet accepted. FullFrame00575 contains an Android volume overlay, which is not an app defect and remains private. This real visual
failure is retained independently from the passing transaction report. Its later
cb2d closure is recorded below; this old footage is not a corrected result or a performance measurement.
[Repeat receipt](../../Verification/Evidence/Review98/Phone/Runs/NoMovesRepeat01/Report.json),
[open loading-text finding](../../Verification/Evidence/Review98/Phone/LoadingCopyFinding98.json),
[additional frame review](../../Verification/Evidence/Review98/Phone/LoadingCopyReviewExtension98.json).

The first repair upgrade guard stopped when a fresh owner-package readback no
longer matched its old baseline. Read-only inventory then confirmed the original
package absent for user0; no cause is inferred and no owner data was recreated.
MaskUpgrade02 and subsequent fixtures compare the candidate against fresh intact
candidate bytes and confirm the original package remains absent. They do not
extend Install02's earlier original-owner preservation to the present.

Future isolated preparation retains this dependency automatically. Run
`python -B Verification/Tools/Review98/prepare_lts.py --execute` only for its
existing fresh-directory workflow: it adds or retains the installed built-in
`com.unity.modules.tilemap` version `1.0.0`, rejects an unexpected version and
records before/after manifest hashes. Main Unity2022's manifest is untouched.
`Unity6Build98.Inspect` requires the registered module with engine stripping
retained; `BuildDevelopment` requires the generated native SpriteMask
registration. This preparation hardening passed a pure transformation/syntax
control; fresh preparation was not rerun over the existing device evidence.

The optional non-development attempt retains **FAIL** at the existing RuStore
release preflight because production registration/SDK/server/signing/legal/provider
inputs are missing. The guard was not bypassed. This is distinct from the passing
internal Development compile and does not produce a store-ready release.
Its `external_java17` diagnostic belongs to the pinned-2022 export-oriented
preflight; the actual LTS JDK17 installation was validated. Do not interpret it
as a missing Java installation or bypass the remaining release checks.
[Retained release attempt](../../Verification/Evidence/Review98/Native/LTSRelease01/Invocation.json).

## Final physical follow-up and measured limits

The narrow loading-copy correction changes four Russian/French values in
`NoMovesText` and adds 200 semantic regression checks. Fresh main Unity2022 and
isolated Unity6 NoMoves reviews each pass **50,676 checks / 255 layouts**. These
are later targeted source epochs, not a rerun of the earlier entire43-case ledger.
The Development-only connected replay fixture also now acknowledges a real HUD
introduction and asserts no spending before waiting for gameplay input; gameplay
mechanics are unchanged.

The final **Dev04** artifact is **354,690,329 bytes**, SHA256
`cb2d4d11d90e190e5174c69d0356047828c05c6d5f3633c51bc99f15565c3e1b`.
Actual build/static checks pass, retaining SpriteMask, portrait orientation and
disabled Unity splash. FinalUpgrade01 preserves candidate profile/preferences
across a same-signer upgrade; the original package remains absent, without
reconstruction or an inferred cause. Repeat02's actual Continue taps buy further
moves and preserve the board. Root viewed decoded frames0-599, Representatives
and full39/278/456: Russian loading body/button are legible, no literal question
marks remain, and the observed exhaustion enters one loading/offer Continue panel
without a separate Out-of-Moves banner. The remaining1,120 video frames were not
claimed visually accepted. Root also reviewed all370 Cold05 decoded frames,
Representatives/full110 and the original end OS capture: brief black native
window, full Russian opening, rendered Lesson1 tutorial, no observed Unity/cube
branding, old top-black band or extra board projection. No precise startup-time
or instant-start claim is made.
[Final artifact](../../Verification/Evidence/Review98/AndroidArtifact98Final.json),
[final repeat review](../../Verification/Evidence/Review98/Phone/RootVisualReviewFinalRepeat98.json),
[final normal-relaunch review](../../Verification/Evidence/Review98/Phone/RootVisualReviewFinalCold98.json),
[low-coins Shop review](../../Verification/Evidence/Review98/Phone/RootVisualReviewLowCoins98.json).

The earlier **CampaignRegression01 remains FAIL**: on834e it completed50boards,
1,507checks,14,126label checks,354clips and316actions, then timed out at
`Connected_Exit` while the valid new Storm Crystal introduction awaited Continue.
That is a fixture integration failure, not a full campaign pass. The repaired
**ConnectedRegression02** on final cb2d passes **245checks /438labels /94actions**
in its explicit connected-only scope, with **boards=0 and clips=0**. This closes
the missed connected phase without relabelling the old full run or inventing a
fresh final50-board pass. These are automated disposable-profile gameplay/UI
fixtures, not a human campaign or hosted/live-provider test.
[Retained partial campaign failure](../../Verification/Evidence/Review98/Phone/Runs/CampaignRegression01/Report.json),
[focused connected successor](../../Verification/Evidence/Review98/Phone/Runs/ConnectedRegression02/Report.json).

A separate **255-second quiet diagnostic on previous834e** records1,982frames
across8phases, including dense powers and celebration: **9 intervals >33.34ms**,
**2 >50ms**, worst **66.55ms**, highest phase p95 **16.84ms**, and maximum measured
command span **47.26ms**. There were no ADB queries, screen recording or Editor
calls during sampling. The original collection wrapper retains FAIL because
its historical parser requires Unity2022. A separate strict Unity6000.3.27f1 /
Android98 validator reprocesses the unchanged raw data; its frozen source and
three host-only rejection controls (wrong runtime, missing phase, NaN) are bound.
This is diagnostic evidence, not a rerun, final-cb2d benchmark, touch-latency test,
controlled cross-build speedup or universal smoothness acceptance. Spikes and
whole-game/long-session performance remain open.
[Bound raw diagnostic and strict validation](../../Verification/Evidence/Review98/Phone/Runs/Fluidity01/Observations98Validated.json),
[retained collector failure](../../Verification/Evidence/Review98/Phone/Runs/Fluidity01/Report.json).

Source diff validation uses the CRLF-aware repository command
`git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --check`.
The default whole-tree command reports preserved CRLF as EOL whitespace under
`*-text`; it is not claimed clean. Only owned Markdown was normalized to its
repository LF style; frozen Unity sources were not normalized.

## Verification matrix

| Scope | Current result | Evidence |
| --- | --- | --- |
| Complete backend service suite | **PASS: 473 executed tests, zero failures/errors/skips**, including the exact previously approved Windows Mono gameplay worker; tested sources and commerce inputs remained stable | `Backend/Set01/Invocation.json`, `Service_Tests.json` and archived inputs |
| Actual separate-process TCP/SQLite rehearsal | **PASS: 199 checks / 162 requests**, including social permissions, lost/duplicate/concurrent claim handling, owned-process restart, backup/new-file restore, recovery and deletion | `Backend/Operational/Binding.json`; the unchanged fixture writes its fresh run to `Review93/Backend/Operational98_Set01` without changing earlier receipts |
| Backend dependency consistency | **PASS:** `pip check` reports no broken requirements | `Commerce/Review.json` |
| Price/registration consistency | **PASS:** six coin mappings agree; six bundles retain exact rewards and disabled/unpriced status | `Commerce/Review.json`, five pricing regression tests within the full suite |
| Main Unity native suites | **PASS within scope: Final03 30/30 invocations**, 148,848 recorded countable checks plus loading-lifetime observations; physical/live acceptance pending | `SuiteSets/Final03/SuiteSet.json`; earlier failures and source epochs remain distinct |
| Selected native coverage ledger | **43 unique passing case outcomes:**38 local Editor +5 actual loopback HTTP, explicitly selected across source/fixture epochs, not a single exact-source run | `NativeCoverage98.json`; all predecessor failures remain retained |
| Connected native HTTP | **Five case outcomes pass:** Identity 25 / Social 18,946 / Server 302 / Payment 38 plus Account retry 59; first combined failure retained | `SuiteSets/HTTP00f41c98/SuiteSet.json`, `ConnectedRuns/HTTP6816992f/Invocation.json`; real loopback/backend, controlled providers, not Android |
| Editor API compatibility / isolated LTS core | **PASS:** main-2022 General534 / guard328, isolated6000.3 CoreChecks7,414 after the later Editor/test API cleanup; runtime unchanged from Final03 | `Native/EditorAPI04_General`, `EditorAPI04_Guard`, `LTSCore02` invocations; separate source epoch |
| Isolated Unity 6 compile/static APK | **PASS:** final Dev04 build0errors/0BuildReport warnings; native SpriteMask registration and static validation pass | `Native/LTSFinalBuildDev04/Invocation.json`, `StaticApk98.json`, `AndroidArtifact98Final.json`; earlier artifacts retained |
| Separate physical installation/upgrade | **PASS:** candidate-only same-signer repaired upgrade preserves candidate profile/preferences. Original package currently absent, cause unknown; no reconstruction | `Phone/Runs/FinalUpgrade01/Report.json`; earlier Install02 owner-preservation is timestamp-scoped; stopped MaskUpgrade01 retained |
| Physical-device startup, UI, touch and lifecycle | **PARTIAL PASS:** final cb2d Repeat02 loading/exhaustion and unmarked Cold05 relaunch reviewed; earlier834e refill/navigation and focused connected scope retain exact limits; further performance/human coverage open | Realme/API36; `Phone/RootVisualReviewFinalRepeat98.json`, `RootVisualReviewFinalCold98.json`; previous core reviews/failures retained |
| Non-development release attempt | **FAIL retained at existing RuStore release preflight**, missing production inputs; no bypass | `Native/LTSRelease01/Invocation.json`; no release approval |
| Root visual review | **PARTIAL:** native UI, previous834e core/refill/pages and final cb2d loading/exhaustion/normal relaunch reviewed | root sidecars and exact media bindings; no full-video/human campaign/performance/provider claim |

Backend results are Python/ASGI/real SQLite tests and the explicitly named approved
worker, plus bounded local TCP operations. They do not establish public HTTPS,
production capacity, live VK/Google, RuStore payments/bank return or Yandex ad
delivery. No backend runtime defect requiring another code change was established
in this scope; the new backend test checks cross-surface commerce configuration.

## Current approved coin prices

| Coins | RUB | Server minor units |
| ---: | ---: | ---: |
| 1,000 | 99 | 9,900 |
| 5,000 | 299 | 29,900 |
| 10,000 | 499 | 49,900 |
| 25,000 | 899 | 89,900 |
| 50,000 | 1,599 | 159,900 |
| 100,000 | 2,999 | 299,900 |

These are requested configuration values, not actual Console quotations. Product
registration, server amount/currency mappings and SDK-returned prices must agree
before payment acceptance. Existing outstanding orders keep their frozen terms.

## Files and remaining gates

Changes are concentrated in PreLevel layout/session and local/connected launch
flows, NoMoves presentation/controllers, the existing HUD, Shop data/current release
configuration and verification. Warning cleanup also touches legacy review/probe
callers so the entire imported project can compile without obsolete API warnings.
New script metadata is added; existing artwork and asset identities are retained.

Configured ordinary Android account/provider acceptance, physical performance outliers, broader
device matrix/human campaign, backend hosting and operations, real provider
configuration, release signing, legal/retention and staffed moderation remain open
unless a specific new bound receipt closes them. The current strict clipboard
contract pass does not erase its historical failures or prove their cause.
Checkpoint97's LDPlayer VM fatal
and interrupted startup/regression proof remain historical failures. A new phone
test does not erase those receipts. This review is not production approval or a
claim that every possible defect has been removed.

Evidence: [gallery](../../Verification/Evidence/Review98/Comparison.html),
[commerce review](../../Verification/Evidence/Review98/Commerce/Review.json),
[backend suite](../../Verification/Evidence/Review98/Backend/Set01/Invocation.json),
[operational binding](../../Verification/Evidence/Review98/Backend/Operational/Binding.json),
[pending bundles](../../Release/RuStore/bundles.pending.json).

## Comprehensive feature checklist - current evidence and open work

This is an evidence map, not a blanket completed checklist. A native suite checks
the behavior described by its own report; a rendered page does not establish a
live service. Earlier source epochs are labelled below. Physical and configured
network/provider rows will be updated only from actual new receipts and root
visual inspection. Historical87/93 device results remain historical evidence.

| Feature and checks | Current demonstrated scope | Still required for full acceptance |
| --- | --- | --- |
| Startup, launch artwork, loading and routing | Native scopes and final LTS build/static checks pass. Root reviewed all370 Cold05 frames and final Lesson1 OS render; no Unity/cube branding observed, with brief black native window. Main remains pinned2022. | Ordinary returning-player routing and repeated background/relaunch/lifecycle checks; no precise startup timing or instant-start claim |
| Story and first-time tutorial | Final03 Tutorial passes 319 checks; RussianLocale passes 580. Existing first-time lessons remain distinct from later obstacle cards. | Actual ordinary phone story/three lessons, touch accuracy, skip/back behavior and audible output; no human first-time flow is inferred from source/Editor checks |
| Home, navigation, safe areas and display | Final03 Display passes14,780 and HomeLives3,276. Actual phone heart/refill taps and six normal navigation captures reviewed: five pages fill display, bottom bar aligned, no old top band/extra board. | Broader devices/safe areas, back/modal stacking and ordinary navigation after gameplay; local/demo rankings are not live-service proof |
| Profile, avatar, statistics and artwork clarity | Final03 ProfileM71 / ProfileDesign / ProfileClarity pass8,244/382/270; Progress2,043. Readiness-reflection failure retained/fixed. Current phone Profile page fits under root review. | Phone avatar/profile editing, cancellation, saved appearance/statistics after relaunch; visual page inspection alone does not prove mutations |
| Settings, music, sound, hints, language and reduced motion | General/RussianLocale validate assets/text/configuration. Current physical Settings fits. Owner reported normal music on oldDev02; repair changes no audio source, without a new listening claim. | Phone switches/persistence, effects listening, hint behavior, language ordering/accessibility/focus across ordinary modals |
| Lives, regeneration, zero-life refill and Home heart | Final03 General/HomeLives and backend473 pass. Actual899/900 phone memory-profile fixtures pass15checks each: visible900 offer, actual header tap,900debit/five lives/no attempt, synthetic duplicate replay. Root reviewed fitting modal and result. | Ordinary durable/connected refill failure/retry/session-transition and regeneration/time boundaries; memory fixture proof is not a production-wallet test |
| All fifty authored levels and model correctness | General imports/checks all 50 referenced definitions. Final03 Snapshot passes 18,313, Cascade 29,106 and MixedPowerSwap 4,113 within their defined model/presentation fixtures. | Previous834e full-run receipt remains partialFAIL after50boards; final focused connected245check pass is separate, boards/clips0. Human campaign/balance/solvability and long sessions remain open |
| Swaps, powers, cascades, falls, obstacles and debris | Current native model/presentation suites cover their exact fixtures; original rules, masks and power distinctions remain. New cards use actual warmed pod/cabinet artwork. | Physical motion/effect inspection, dense simultaneous powers/obstacle destruction, correlated frame/render/GPU timing and fresh reference comparison; no whole-game smoothness approval |
| Obstacle introduction and pre-start boundary | Final02 ObstacleIntro98566 and Final03 NoMoves105localized layouts pass. Root reviewed corrected native pod/cabinet art; actual stone fixture9checks proves pre-start block/no debit and Continue→Started24moves, with physical card/board review. | Other families/ordinary persisted progression and termination boundary; connected fail-to-Home repetition remains the documented local-history limitation |
| Out of moves, repeated Continue, Shop and abandonment | Final03 NoMoves50,476/RepeatMoves93 and earlier NoMovesTransactions4,232 pass. Actual repeat/abandonment fixtures preserve board/settle once, with compact confirmation reviewed. Earlier834e video exposes literal question marks; final cb2d frames0-599/full278 visibly close that loading-copy defect while transaction evidence remains separate. | Ordinary durable/interrupted Continue/Shop and configured server acceptance; only the recorded final exhaustion segment is visually accepted; stills cannot establish no-banner timing |
| Daily Gift, Wellworks and practice Rain Cup | Earlier Final02 suites2,968/5,415/8,081 and current backend473/operational claims pass within scope. Root reviewed current physical pages without overflow; returns are hash-identical to viewed Home. | Configured ordinary-app HTTP/physical claim/reopen/day boundaries; page rendering is not a claim test. Rain Cup remains labelled practice with simulated rivals |
| Shop coin display and Special/Mega offers | Final03 Rubles2,212/Checkout283 and configuration tests pass. Root reviewed all six99/299/499/899/1599/2999 RUB previews together on actual normal Shop scroll. | Console/SDK quotation matching. Six bundles still need approved prices, registration, atomic inventory delivery, recovery/refund handling and provider tests |
| Guest identity, account save/recovery/link/deletion | Final03 Identity 69, Account 101, Lifecycle 32 and Provider 280 pass in their specified scopes. Actual loopback Identity HTTP 25 and Account HTTP retry 59 now pass, including unchanged clipboard readback and full recovery/deletion lifecycle; original premature-action failure is retained. Backend 473 covers ASGI/SQLite operations. | Ordinary configured Android identity/keystore/recovery/deletion; live VK/Google registration and cross-device service acceptance. Editor/provider controls are not live signup |
| Global/regional standings, teams, friends, records and messaging | Final03 Regional 11,665 / ServerCore 55 / Capacity 46 and actual native Social HTTP 18,946 /Server HTTP 302 pass within their scopes. Backend 473 and TCP 199 exercise permissions, blocking/reporting, chat and durability using disposable users. | Ordinary configured Android/physical network interactions, moderation operations, reconnect/long polling and public hosting. Default/demo pages do not establish live global data; no external users were messaged |
| Rewarded advertising | Final03 AdFlow 191 / AdsParser 140 / AdsUi 736 / AdsJournal 96 pass; backend tests cover 400 coins, three per player-local day and 600-second cooldown. | Actual registered Yandex unit, SDK/device video completion/cancel/interruption, lifecycle recovery and provider delivery verification. Disabled/unavailable controls and scripted completion do not establish ad impressions |
| RuStore purchases, notifications and delivery recovery | Final03 Guard 328 / Recovery 85 / Checkout 283, actual controlled Payment HTTP 38 and backend473 exercise their scripted-provider/contract and transaction scopes, including duplicate/interrupted/refund handling. Runtime checkout uses SDK amountLabel. | Real Console app/products, server credentials/HTTPS notification setup, SDK-enabled Android build, sandbox/bank-return/termination/recovery and controlled real payments; release signing. SDK-free tests cannot certify money movement |
| Durable storage, concurrency, attempts and restart/restore | Current backend 473 plus actual TCP 199 checks cover SQLite transactions, duplicate/lost responses, owned-process restart and backup/new-file restore. Current native lifecycle/identity and earlier epoch profile/continuation transaction suites cover their stated stores. | Final candidate same-signer upgrade/unmarked relaunch preserve its save/preferences. Ordinary attempt interruption, process termination at sensitive boundaries, low-storage/power-loss cases and configured cloud reconciliation; separate-package preservation is not an in-place upgrade test |
| Device compatibility, resource lifetime and performance | Native contracts/loading observations and ARM64 ELF/16KiB static checks pass. Repaired realme/API36 cold/refill/navigation paths run after closing the observed SpriteMask dependency failure; prior performance outliers/LDPlayer fatal remain retained. | Further physical gameplay/performance; Android8/API26/tablets/16KiB runtime matrix, thermal/low-memory/long sessions and dense effects; no universal compatibility or production-capacity claim |

The documented source/runtime defects have scoped fixes and verification. The
final internal APK is installed and its loading/exhaustion and normal relaunch
are visually reviewed. Earlier core pages/refill, partial campaign and quiet
performance retain their exact previous-artifact scopes. This review is
**REVIEWED_WITH_OPEN_ACCEPTANCE_GATES**: `fullyVetted=false`, `taskComplete=false`
and `productionApproved=false`. Whole-game performance, human campaign/broader
devices, ordinary configured backend/providers and production operations remain
open. Results keep source epochs, memory fixtures, actual service traffic,
physical captures and live-provider acceptance distinct.

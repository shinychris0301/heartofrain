# 100 - Full-Grant commerce and committed-reward presentation

**REVIEWED_WITH_OPEN_ACCEPTANCE_GATES.** Backend, controlled HTTP, selected Unity
Editor, Android build/static checks and defined cases on one physical phone are
verified within their recorded scopes. Root reviewed the selected receipt and
preview images. Whole-app/backend, all-device, performance and production
acceptance remain open.
`fullyVetted=false`, `taskComplete=false`, `productionApproved=false`.

The main project remains Unity **2022.3.62f3**. The separately approved Unity
**6000.3.27f1** copy remains the Android testing path; no engine promotion is
implied. The checkpoint100 SDK-free, test-signed Development candidate is installed
on the inventoried phone and copied to
[HeartOfTheRain_Review100_Android_Test.apk](../../Unity/Builds/Review100/HeartOfTheRain_Review100_Android_Test.apk):
**319,164,540 bytes**, SHA256
`a476d2a36fa52d72aa9289bab4b40a099f49ccde4030a6f4d71e93a47c361aea`.
Its equal byte count to checkpoint99 does not imply equal contents: native code,
metadata and the checkpoint100 probe are bound in the new build provenance.
[Exact artifact binding](../../Verification/Evidence/Review100/AndroidArtifact100.json).

[Current evidence gallery](../../Verification/Evidence/Review100/Comparison.html),
[full backend run](../../Verification/Evidence/Review100/Backend/Full02/Service_Tests.json),
[commerce API and recovery contract](../../Release/RuStore/COMMERCE_FULL_GRANT100.md).

## Implemented behavior

Commerce orders freeze the complete server-owned Grant: coins, zero purchasable
story stars, four starting items and four tools. A matching server-verified
CONFIRMED invoice projects the full grant, immutable credit, wallet ledger and
Special entitlement in one transaction. Repeated callbacks, a lost reply or a
restart return the original receipt. Inventory overflow and pre-commit faults
leave no partial credit. Existing coin-pack configurations and legacy receipts
remain compatible with zero item arrays.

Special offers reserve one entitlement under stable internal player ID plus
offer ID. Concurrent commands/devices recover one reserved order. Its immutable
`creationCommandId` identifies the original creator: a follower or legacy-null
order is lookup-only, and cannot cause another SDK purchase dispatch. The Unity
client also persists dispatch intent before entering the SDK and preserves
unknown outcomes. Mega offers remain repeatable. No device/reinstall flag enforces
the Special policy.

Only matching provider-verified CANCELLED/REJECTED/EXPIRED evidence releases an
undelivered Special reservation. Client cancellation, network failure, PAID funds
on hold and missing callbacks keep it reserved. RefundReview remains sticky,
with no guessed inventory debit or eligibility reset. A late contradictory
CONFIRMED after a terminal release is quarantined without another grant; it needs
operator refund/reconciliation and is not silently reported as delivered.

The player-scoped pending-order feed supports recovery under another credential.
It is bounded by count and **48KiB per JSON response**, below the app's 64KiB
transport buffer, with a cursor for the last actually included order. The client
resumes verification instead of automatically launching payment. After SDK
acknowledgement, backend reconciliation must observe provider ACKNOWLEDGED before
the local transaction is cleared. Account-deletion guards fence late delivery;
restricted financial/security audit and entitlement rows retain their existing
retention-policy limitations.

Schema **8→9** is additive and preserves old balances/receipts. It freezes Grant,
purchase policy and creator binding and adds the entitlement table. The creator
column was added while schema9 was unreleased; pre-binding test epochs remain
separate. Snapshot validation was preserved, including exact schema8 backup,
new-file restore, explicit migration and migration rollback.

The Home notification journal is **presentation metadata, not a wallet**. The
claim/purchase path writes a committed receipt notification before clearing its
durable intent. Display, cancellation and acknowledgement never credit inventory.
Origin/player binding, detached Grant values, checksummed atomic replacement and
receipt deduplication protect local recovery. Home navigation, resize and loss of
foreground cancel a reveal without acknowledging it. The current wallet header
remains authoritative even if the player already spent part of an older receipt.

The journal retains the last **512 presented** records plus pending notifications,
bounded overall by **8,192 records/4MiB**. Pending entries are not retired. An
ancient callback beyond the cosmetic history can repeat a notification; the
server's financial idempotence is unaffected. An unwritable/corrupt journal or a
full pending queue applies recovery backpressure. Recovery here covers the local
pending intent and notification queue. It does **not** reconstruct every historical
reward presentation on a fresh device from the server rewards feed.

This presentation integration covers committed commerce receipts and the managed
Daily Gift/Wellworks/Cup claim path. **First-clear and rewarded-ad notifications
are not yet unified through this receipt presenter.** Their existing financial
rules and displays remain separate; a complete all-source reward inbox is still
engineering work, not a production-provider setting.

## Prices and activation

No approved price, reward quantity, Daily Gift/Wellworks/Cup/ad schedule, level,
artwork or gameplay rule changes in this checkpoint. The disabled twelve-product
deployment example contains these existing amounts:

| Product | Coins | Each tool | Each starting item | RUB | Policy |
| --- | ---: | ---: | ---: | ---: | --- |
| Coin pack | 1,000 | 0 | 0 | 99 | Repeatable |
| Coin pack | 5,000 | 0 | 0 | 299 | Repeatable |
| Coin pack | 10,000 | 0 | 0 | 499 | Repeatable |
| Coin pack | 25,000 | 0 | 0 | 899 | Repeatable |
| Coin pack | 50,000 | 0 | 0 | 1,599 | Repeatable |
| Coin pack | 100,000 | 0 | 0 | 2,999 | Repeatable |
| Wellkeeper Kit | 2,000 | 1 | 1 | 99 | Once per player/offer |
| Rainy Day Bundle | 3,500 | 2 | 2 | 199 | Once per player/offer |
| Rainlight Reserve | 6,000 | 3 | 3 | 299 | Once per player/offer |
| Village Treasury | 5,000 | 2 | 3 | 399 | Repeatable |
| Festival Chest | 10,000 | 4 | 6 | 599 | Repeatable |
| Keeper's Collection | 25,000 | 8 | 12 | 999 | Repeatable |

Tools remain Hammer/Axe/Ram/Atlas; starting items remain
Rocket/Bomb/Rainbow Orb/Golden Seeker. Actual checkout prices use SDK
`amountLabel`, with server-verified frozen amount/currency. Preview labels are not
payment quotations. Default checkout, production products and providers remain
unconfigured/disabled. Full-Grant implementation alone does not enable sales.

## Changed-file map

| Area | Main implementation locations | Purpose |
| --- | --- | --- |
| Backend commerce/API | `Backend/hotr_backend/commerce.py`, `commerce_schemas.py`, `api.py` | Frozen full Grant/policy/creator terms, eligibility, verified delivery/recovery and bounded pending feed |
| Backend schema/wallet/snapshots | `commerce_schema.py`, `storage.py`, `wallet.py`, `operations.py` | Additive schema9, atomic inventory projection, immutable replay and strict old/current snapshot compatibility |
| Unity RuStore contracts/delivery | `App/RuStore/Runtime/CommerceTerms100.cs`, `RuStoreBackendClient.cs`, `PayStoreContracts.cs`, `PayDeliveryCoordinator.cs`, `FilePayJournal.cs` | Typed Grant/eligibility/creator validation, frozen recovery, acknowledgement and compatibility |
| Unity checkout/shared adapter | `App/ShopCheckout86/Runtime/CheckoutBackend100.cs`, `ShopCheckoutContracts86.cs`, `ShopCheckoutFlow86.cs`, `ProtectedCheckoutJournal86.cs`, `ShopCheckoutHost86.cs`, `ShopCheckoutUi86.cs` | Shared backend adapter, durable SDK-dispatch ownership, UI eligibility and committed-receipt handoff |
| Committed-reward display | `App/ServerRewards/Runtime/RewardPresentationJournal.cs`, `RewardReceiptPresenter.cs`, `ServerRewardsCoordinator.cs`, `ServerRewardsSession.cs`; `App/Home/Runtime/HomePage.cs`; `App/Profile/Runtime/PlayerProfileHost.cs` | Cosmetic queue-before-intent-ack, bounded presented history, Home rendering and owner/lifecycle fencing |
| Verification | `Backend/tests/test_commerce_grants100.py`, `legacy_schema_fixture.py` and affected price/migration/operations/ad tests; native checkout/journal/UI/HTTP suites and development-only phone probe; `Verification/Tools/Review100/` | Financial/state regressions, real-worker full suite, controlled HTTP and scoped native/device evidence |
| Configuration/docs | `Release/RuStore/commerce.example.json`, `bundles.pending.json`, `COMMERCE_FULL_GRANT100.md`, setup/readme files and this review | Twelve disabled product definitions, exact approved contents/prices and remaining launch gates |

Unity paths above are relative to `Unity/Assets/HeartOfTheRain/`. Native capture
path/scale corrections are verification changes; approved Shop quantity layout,
artwork/GUIDs, level masks and gameplay semantics are preserved.

## Verification completed so far

| Evidence | Actual result | Scope and limit |
| --- | --- | --- |
| Focused03 | PASS 258 tests | SQLite/ASGI/scripted-provider financial set, including 25 new full-Grant/migration/recovery cases; earlier source epoch |
| PackageFix01 | PASS 29 tests, zero failures/errors/skips | Actual package-mode import successor, including all 25 new cases and four affected legacy fixture cases |
| Full02 | **PASS 500 executed, zero failures/errors/skips** | Full Python/SQLite/ASGI suite with explicitly approved immutable Mono replay worker; 176 approved worker hashes, unchanged source inputs; not ordinary Android or real payments |
| CheckoutMain06 | **PASS 3,410 checks / 21 controller cases / 125 UI states** | Actual Unity2022 Editor, encrypted CAS journal and UGUI, scripted SDK/authority/wallet; legacy cached-creator normalization, five locales/two widths/final pixel scales 1, 1.832, 3; no actual SDK/payment |
| RewardJournalMain01 | **PASS 30 checks** | Actual Unity2022 native journal checks including full Grant, ownership, atomic faults, deduplication and bounded presented history |
| RewardUiMain01 | **PASS 18,626 checks / 15 locale-size states / four lifecycle cases** | Actual Unity2022 PlayMode/imported sprites/UGUI. Foreground is explicitly simulated in the Editor. Generic earned-reward fixture includes one synthetic earned star, not a purchasable bundle |
| CommerceHttp03 | **PASS 182 checks / ten cases** | Actual UnityWebRequest, isolated FastAPI/SQLite, shared checkout adapter and protected CAS; controlled publisher/SDK, five purchase/ack calls, one duplicate callback, 101 pending orders over three pages; ordinary Editor profile hashes unchanged and owned listener closed |
| GeneralMain01 | **PASS 535 checks** | Current actual Unity2022 native baseline; not a human campaign or Android execution |
| Root native visual review | Three controlled-quote Russian detail views and two generic Home receipt views accepted | Wellkeeper 99 RUB and eight ×1 quantities; Rainlight 299 RUB and eight ×3; Village 399 RUB/tools ×2/starting ×3. Russian phone/tablet receipt images show all ten generic dimensions, including an earned-star fixture. Commerce grants have zero stars. This is not physical-device or provider approval |
| Isolated Unity6 LTS | **PASS Configure 19 / Core 7,429 / Build 22 checks** | Actual Unity6000.3.27f1 Android Development build, 0 BuildReport errors/warnings; main remains Unity2022 |
| APK static / candidate upgrade | **PASS** | Exact signature/zip alignment/portrait/SDK-free manifest/ARM64 16KiB checks and same-signer candidate replacement; not store-release signing or provider acceptance |
| SharedReward01 physical | **PASS 127 checks + scoped root visual review** | One phone, disposable precredited memory profile, nine positive approved Wellkeeper quantities, zero stars, one completion, identical full model digest before/after reveal; separate public journal reconstructed/deduplicated/acknowledged. No actual SDK/payment/HTTP or owner credit |
| Five-case phone preservation chain | **PASS within scope** | Upgrade01, NormalHome01, PreviewDetails01, SharedReward01 and FinalHome01 preserve candidate profile/preferences and old-owner absence; original99 candidate data equals final100 data. Root accepted normal Home, three preview details and selected receipt frames |

Each invocation binds its own source manifest. Do not merge these into one
unqualified source epoch or treat host assertions as native/device checks.
[Scoped invocation index](../../Verification/Evidence/Review100/NativeCoverage100.json).

The [physical preservation chain](../../Verification/Evidence/Review100/PhonePreservation100.json)
binds all five cases. Root viewed SharedReward01 Representatives and full decoded
frames **132** (recording-relative PTS approximately **8.567s**) and **168**.
The ribbon shows **+2,000 coins and eight +1 items**, no star; the temporary
header is already **3,250** before/during/after and the ribbon closes cleanly.
The model was credited once before this fixture displayed it. The recorded
1.617858s reveal elapsed value is not a fixed two-second timing certification;
the renderer supports normal and reduced-motion durations. This video is not
proof of an actual purchase or Android-to-backend transaction.

FinalHome01 is a separate unmarked ordinary relaunch: **1,250 saved coins, five
lives, Level1/zero clears**, English preference retained. Root reviewed its OS
image separately. The original owner package was already absent following an
external device-state change and remains absent; no owner data was reconstructed.
Raw video/launcher frames remain private. Only
[seven root-reviewed app images](../../Verification/Evidence/Review100/ReviewedImages100.json)
are copied into the gallery.
The complete native PNG capture sets stay local under the checkpoint100 ignore
rule; they are not shipped repository assets or additional published approvals.

[Controlled HTTP receipt](../../Verification/Evidence/Review100/Connected/CommerceHttp03/Report.json)
binds the native HTTP report and database audit. The ten cases cover full bundle,
unknown outcome, recovered order, frozen terms, verified cancellation, legacy coin
compatibility, byte/count pagination, foreign ownership, concurrent creator
binding and Daily Gift presentation-save recovery. These use disposable
operator-provisioned players, scripted SDK callbacks and controlled publisher
evidence, rather than real payment authorization or ordinary configured startup.

## Retained failures and corrections

Full01 retains **476 executed / five errors**, no skips, with the actual approved
worker. The focused loader used bare modules while the full runner discovered
`tests.*` packages. One new test module and four legacy-fixture calls used
unqualified imports. All five errors were reproduced, imports were qualified and
the focused loader was aligned with full discovery. No assertion, transaction
guard or snapshot validator was waived. Full02 then passes all 500 cases. All
52 compared backend runtime-module hashes are unchanged across that import fix.

Earlier Focused01 also remains FAIL: Windows multiprocessing cannot reopen a
stdin runner, and four old test fixtures copied current commerce columns while
labelling them schema4/6/7. A guarded script runner and exact historical schema
fixtures corrected the test construction. Original reports remain intact.

CheckoutMain01 retains its NullReference/input-delta failure. Main02 retains the
diagnostic helper compile error using GetMesh. Main03 passes 914 checks but did
not close the quantity-ink visual gate. Main04 retains the 371-check zero-ink
failure caused by changing capture scale after fitting text. Main05 fits and
renders at the final capture scale and passes 3,404 checks. Main06 subsequently
passes 3,410 checks with the legacy cached-creator case. The approved Shop
quantity layout/runtime was not patched to hide a fixture artifact.

CommerceHttp01 retains its fixture path-guard failure: the encrypted test vault
allows the approved Launch82 cache, while the first test used a Review100 path.
CommerceHttp02 retains its Daily Gift failure after the other cases: a historical
**268-character temporary test path** prevented intent persistence before its
intended presentation-save fault. CommerceHttp03 exercises that negative case,
then uses a shorter isolated fixture root to commit the real 50-coin claim,
inject the presentation-save fault, recreate the coordinator and recover once.
It finishes with all ten cases passing. Test paths were corrected; runtime
journal/Shop layout code was not weakened to bypass those guards. Earlier
controlled HTTP failures and database audits remain preserved.

## Remaining acceptance gates

[Measured warning categories](../../Verification/Evidence/Review100/WarningSummary100.json)
record **zero C# warnings in ten selected closed current logs**, **zero final
BuildReport errors/warnings** and **three retained IL2CPP large-method compilation
notices**. Engine/vendor/network/shutdown diagnostics and historical425 vendor
diagnostics are not claimed eliminated. One external Starlette/httpx TestClient
deprecation remains captured in the Python checks; no dependency upgrade or
suppression was applied.

Configured live RuStore products, SDK/core/deep-link setup, hosted HTTPS service,
server credentials, release signing, legal/privacy/retention policy, operator
refund handling and real banking-app/payment recovery remain external gates.
Real VK/Google, Yandex impressions and staffed social moderation are not proven
by these controlled checkout tests.

Physical coverage is one inventoried phone and the defined preview/memory-reward
cases above. The actual connected HTTP tests ran in the Editor, not on the phone.
Human campaign play, broader
phones/tablets/network conditions, production load and purchase interruption
remain open. The earlier 66.55ms worst-frame diagnostic remains an unresolved
performance limit; this checkpoint does not claim a smoothness speedup.

This is a scoped checkpoint review, not completion of every remaining engineering
or launch requirement. `fullyVetted`, `taskComplete` and `productionApproved`
remain false.

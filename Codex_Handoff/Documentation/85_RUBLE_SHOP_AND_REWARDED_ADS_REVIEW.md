# Checkpoint 85 — RUB Shop and optional rewarded video

Review date: 25 October 2026 local / 26 October UTC. User-approved advertising
policy: 400 coins, three rewards per fixed UTC+10 day, 600-second cooldown.

The live Shop preview now displays the existing launch proposal in rubles:
199 ₽, 699 ₽, 1,299 ₽, 2,699 ₽, 4,999 ₽ and 8,999 ₽ for the six unchanged coin quantities.
Unpriced Special/Mega bundles no longer display unsupported USD prices. They
remain unavailable. The No Moves preview catalog agrees; its actual purchase
buttons remain disabled. Real checkout continues to require RuStore
`GetProducts.amountLabel`, real products and the existing release gates.

## Implemented behavior

- A voluntary Shop video placement uses the existing artwork/fonts and a
  separate explicit explanation/privacy/start/cancel flow. There are no
  automatic SDK loads from page entry. Missing publisher/backend/SDK
  configuration displays an unavailable state. The placement is separate
  from gameplay, story, continuation purchases and level settlement.
- The backend owns 400-coin grants, three credits/day on UTC+10, and 600 seconds
  after a credit. Midnight is 14:00 UTC; it does not bypass the cooldown. No fill,
  incomplete videos, cancellation and reservations consume no quota.
- Durable origin/player-bound opportunities and immutable commands survive
  lost replies/restarts. SDK callbacks grant no money. An authenticated claim
  commits an idempotent server-wallet receipt, followed by a wallet refresh
  before feedback. Account transitions are blocked by unresolved ad intents.
- Recovery preserves a same-process completion through a transient disk write
  failure; canonical server completion can recover a missing local journal.
  Stable owner fencing is separate from bearer expiry during an external ad
  landing page. Old coroutine cleanup cannot dispose a newer operation's ad.
- Additive database schema 7 and backup/restore include ad state. Payment
  verification, trusted gameplay, account revocation/deletion and refund
  quarantine retain their existing authority.

## Trust and activation limits

Yandex does not support server-side reward verification. The explicit selected
mode is `sdk_client_reported_capped`, with
`completionAuthoritative=false`, `verifiedAt=0` and an honest receipt source.
A modified authenticated client can falsely report viewing up to the server
cap of 1,200 coins/day. Ownership, rate limits and idempotency do not prove an ad
impression. No Yandex signature, callback proof or public grant webhook is
invented. The separate server-only trusted-completion seam remains available
for a future verifiable provider; synthetic HMAC is in-process local/staging
test evidence only.

Publisher registration, a live unit, the actual HTTPS backend and privacy
configuration are absent. Advertising remains disabled by default. There is
no live ad/revenue or completed production rollout claim. Owner steps and the
disabled external configuration example are in
[Release/Advertising](../../Release/Advertising/README.md).

The official Yandex Unity SDK 8.6.0 is hash-pinned. Its actual provider branch
compiles in a separate ARM 64 IL 2CPP SDK fixture, which assembles with explicit
external Java 17/Gradle 8.9/AGP 8.7 and the installed pinned NDK. Main Unity
2022.3.62f 3, SDK packages and tool preferences are preserved. The stock control
failed resolving AGP 7.4.2; that failure alone establishes no SDK incompatibility.
The SDK-only APK was never launched. A later separate full-game profile also
exports the actual Launch and M65 First Start scenes, compiles the real adapter
branch and assembles successfully with the same explicit external tools. Its
277,140,711-byte internal APK passes 92 static checks: CRC/signature, ZIP/ELF
alignment, Russian name, portrait, API 26/35, device identity and actual
Yandex/AppMetrica classes. It was never installed or launched. These are compile
and packaged-configuration results; live SDK/reward/device acceptance remains
open. All 5,349 main inputs, original meta GUIDs and main tool settings remain
exact. The clone-only settings serialization and historical helper versions are
recorded separately, without treating them as main-project changes.

Static SDK review confirms automatic initialization is disabled and Google
AD_ID/location permissions are absent. Native initializer providers,
AppMetrica service/preload components and identifier/referrer/AppSet capability
remain packaged. The provider requests non-personalized age-restricted ads,
turns off location tracking and AppMetrica ad analytics reporting before its
first loader. No zero-pre-consent-network or full privacy-compliance claim is
made from static inspection.

## Original checkpoint 85 verification

| Evidence | Actual scope/result |
| --- | --- |
| Backend |357 tests, zero skips/failures/errors; includes 33 new ad cases and the real approved Windows Unity worker integration.79 exact inputs archived; later README edits are documentation only. |
| Native journal |96 checks, nine actual file lifecycle/fault/corruption cases. |
| Native parser |87 checks,12 positive and 39 malformed-response cases. |
| Native HTTP |31 checks; two signed managed guests,10 ad API requests, four identity requests/four wallet reads. Report alone credits zero; claim credits 400 once; foreign actor/stale access denied. |
| Native flow |64 checks,16 scripted-provider/API cases with the actual disk journal. These are not real ads or HTTP proof. |
| Native Shop |2,212 checks;15 phone/tablet/locale layouts,180 actual offer detail views and seven captures. |
| Native ad UI |676 checks;15 layouts and six captures. Consent is an explicit layout fixture, not a configured SDK display. |
| Visual review |Seven of 13 actual native PNGs inspected by root: RUB list/detail, No Moves store, unavailable ad card and consent phone/tablet views. No new discrepancy found in those samples. |
| Internal Android |Both development and non-development SDK-free APK compile checks pass, with exact project settings restored. Internal signing is not release signing. |
| SDK fixture |ActualSDK 8.6/provider branch compiled and external Android assembly passed; static manifest/dependency/privacy audit has 28 checks. No installation or ad request. |
| Later full-game SDK supplement |Actual two-scene ARM64 IL2CPP export and external assembly pass; 92 static checks. APK SHA256 `313c3cdc45c52847ce5b5e5ab635bb598c530eb3c1057de19dece037dde6815f`. No install, launch or SDK request. |

Six selected Unity suites total 3,166 checks. The four core suites and the two
UI suites retain separate exact input freezes; the only differences between
those freezes are the two corrected new UI fixtures. Runtime source is exact.
The current game contains 5,349 Unity input files:28 added and five existing
inputs changed relative to checkpoint 84. Original art/GUIDs/level masks and
gameplay timing/model files are unchanged.

Failed preliminary runs remain archived. The initial HTTP fixture was outside
the existing ephemeral vault's allowed ignored cache; the test path was fixed
without weakening the vault guard. The first Shop fixture incorrectly assumed
its review scene could not create a normal Editor profile. It now installs the
existing transient-review mechanism before Play Mode. The four newly generated
genesis files were verified and quarantined in ignored cache, restoring the
original absent Editor `Profiles` directory. No emulator was involved in that
correction. The first build wrapper also incorrectly compared Unity's total
build-product size with APK size; the corrected wrapper records them
separately. Its actual native compile had already succeeded.

Current evidence:
[Comparison.html](../../Verification/Evidence/ShopAds85/Comparison.html),
[Summary.json](../../Verification/Evidence/ShopAds85/Summary.json),
[static SDK audit](../../Verification/Evidence/ShopAds85/SDK/Provider_Privacy_Audit.json),
[later full-game SDK compile/static supplement](../../Verification/Evidence/ShopAds85/SDK/FullGameBuild/Report.json),
[Editor fixture correction](../../Verification/Evidence/ShopAds85/Editor_Fixture_Isolation_Correction.json).
The base Summary/gallery is an immutable earlier SDK-free snapshot. The global
verification summary independently rechecks and links the later full-game SDK
supplement without rewriting that snapshot. Each report retains its own
synthetic/native/HTTP/build limits. No fresh
whole-game smoothness, physical-device, live advertising, payment, publisher
revenue or production release certification is implied.

## Reservation denial followup

A final review found that an explicit rejection of a new reservation could
leave an empty local intent blocking account transitions. The client now
recognizes only six exact reserve-specific HTTP status/error pairs, with a
current owner, complete JSON error-only body and correct content type. Only
Watch's newly generated first send may resolve its intent from that proof.
Wallet/authentication guards, malformed responses and generic failures remain
uncertain. A later denial cannot prove that an earlier delayed request will
never commit; recovered/unknown histories retain their original identifiers.
No record is cleared merely because a status read has no active opportunity.

The fresh pinned Unity flow suite passes 191 checks across 25 cases, including
all prior 16 cases, six accepted/36 rejected classifier controls, six fresh
rejections, six unproven rejections and three uncertain/recovered sequences.
The fresh backend suite passes 358 tests with zero skips/failures/errors and
the real approved Unity worker. Its added regression proves rejected reserves
leave no financial/command/opportunity mutation and cached successful commands
replay before eligibility checks; wallet quarantine/migration remain guards.

Both current SDK-free internal Android builds also pass, followed by actual
CRC/signature, ZIP/ELF alignment, Russian label, package/manifest and DEX
inspection. Exact main settings and historical native reports are restored.
Neither APK was installed or launched; internal signing is not store signing.

Exactly four Unity files change from the committed original 85: the ad reply
contract, HTTP client, flow and its native verification suite. Backend runtime
and configuration are unchanged; one backend test is added. Prior UI captures,
parser/journal/HTTP tests and SDK fixture/full-game proofs retain their exact
earlier source scope. The SDK-enabled full-game clone predates these four
changes; the provider and native integration bytes remain exact. This is not
a fresh SDK-enabled runtime/device test.

Followup evidence is kept separately in
[ReservationRecovery85](../../Verification/Evidence/ShopAds85/ReservationRecovery85/Comparison.html).
The global verification collector checks this current supplement before the
immutable original 85 snapshot. Unknown ad reservations still require server
reconciliation before account transitions; no public abandonment/tombstone API
is introduced. Live ads and all existing release gates remain open.

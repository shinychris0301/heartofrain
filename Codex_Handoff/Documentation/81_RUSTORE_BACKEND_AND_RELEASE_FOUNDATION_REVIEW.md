# RuStore backend and release foundation — checkpoint81

25 October2026. Unity remains2022.3.62f3, runtime baseline M67R4. This checkpoint
implements a portable **local/staging** authority and explicit disabled client
adapters. Production payments and ordinary-profile migration remain blocked.
The current result and exact source/artifact bindings are collected in
`Verification/Evidence/RuStore81/Summary.json`; the readable evidence index is
`Verification/Evidence/RuStore81/Comparison.html`.

## Package review and retained decisions

The supplied `Heart_of_the_Rain_RuStore_Codex_Handoff_R1.zip` contains18 files:
17 UTF8 documents/configurations/scripts and327 DOCX paragraphs. All17 supplied
SHA256 entries match. The archive SHA256 is
`3fc1de25b93fc67a048cba32634a42469854226c35c93478e33c415107092880`.
Its contents are planning/contracts, not an installed SDK or working backend.
Packaged scripts were read, not executed. The inventory and nine review findings
are retained separately from test evidence.

The handoff's older source audit does not replace current durable attempts,
repeated continuation purchases or saved Continue/Shop recovery. Its proposed
new bundles/economy and ad priority are not adopted. The existing six Shop coin
quantities are retained as disabled registration proposals. The approved rules
remain **900 coins for five more moves, repeatedly**, and **900 coins for all
five lives at zero lives**. Artwork, GUIDs, level masks, M46/M48 gameplay,
celebrations, localization, approved pages and Resources remain byte-identical
to source80. No engine or SDK upgrade is applied to the ordinary project.

## Implemented backend

`Backend/hotr_backend/commerce.py` creates player-bound immutable orders before
checkout. Frozen terms include app/environment, product, quantity1, amount,
currency, reward, catalog version and an unpredictable order correlation. The
backend queries RuStore's official v2 invoice endpoint and compares every
documented binding. A callback cannot supply an authoritative status, price,
quantity or coin grant. `PAID` remains held; only matched `CONFIRMED` can credit.

Credit, server-wallet projection and delivery-pending marker commit in the same
SQLite transaction. Unique invoice/purchase/order identities prevent duplicate
delivery. Provider requests run outside database write locks. Refund/reversal
evidence is sticky, including a delayed confirmation that began before the
refund committed. It quarantines spending rather than inventing a refund/debt
policy. SDK acknowledgement follows a committed spendable receipt; a later
provider lookup substantiates acknowledgement. A client boolean cannot mark it
delivered.

`wallet.py` and the additive schema3 migration provide a shared revisioned
coin/star/item/life ledger, typed attempt reservation/start/tool/quit/settlement,
repeated continuation and zero-life refill. Gifts, Wellworks, practice Cup,
verified first-clear rewards and purchases share that ledger. The server owns
the approved50-level catalog, seed, allowed moves and rewards. Only a separately
provisioned upstream verifier can declare outcomes; this service does **not**
validate board replays. Practice rivals remain simulated.

New operator-provisioned server players receive the approved starting stock
once. Historic reward-only server accounts backfill unique trusted receipts
without a second genesis and remain nonspendable until migration is approved.
Unity local balances are never imported automatically. These staging databases
and sandbox credits must not be promoted into a live economy.

`rustore_auth.py` implements bounded fixed-origin Public API authentication with
SHA512withRSA, UTC timestamp, short monotonic JWE cache, concurrent-refresh
serialization and failure-safe rotation. Server-only key file references stay
outside Unity. Tests use ephemeral RSA keys and mocked HTTPS; no real Console
key or JWE is present. The default commerce catalog is disabled and empty.
Production backend mode and live checkout are explicitly blocked.

The current credential-free OpenAPI contract has29 paths. See `Backend/README.md`
for endpoint semantics, operator provisioning and the staging launcher.

## Unity integration boundary

`App/RuStore/Runtime` adds SDK-independent contracts, an explicit Pay adapter,
delivery coordinator, file journal and asynchronous staging backend client.
There is no automatic instance, checkout, local grant, profile-factory switch or
automatic Continue tap. Credentials stay in memory. The client bounds responses,
disables redirects, binds identity and frozen order terms, fences late callbacks
after revocation, and requires a fresh initialized nonquarantined server wallet.
Cleartext is limited to explicitly opted-in Editor/development loopback checks.

The journal saves correlation before checkout, atomically replaces a flushed
file, refuses a second dispatch claim, and fails closed on corruption or another
account. Its checksum is corruption detection, not server authority. Reopening
even an acknowledged record performs fresh SDK/server verification and never
repurchases automatically. Actual file tests exposed Unity's inline-class null
serialization; explicit presence flags and raw transport null/type checks now
preserve optional metadata without accepting malformed attempts.

`GetProducts` maps the SDK's `amountLabel` for presentation. Confirmation and
delivery acknowledgement remain separate APIs. The backend receipt can enable
staging delivery only after authoritative spendable credit; the ordinary game
still uses its unchanged local services.

## SDK and toolchain verification scope

Official Pay11.1.0 pins Core10.5.0. Both unmodified npm manifests declare
Unity6000.0; stock UPM nevertheless resolved and compiled their APIs in the pinned
2022.3.62f3 Editor. This is measured compatibility, **not vendor support
certification**. The alternate official Assets archive checksum also verifies
and was not redundantly imported. Artifact locks and reproducible fixture inputs
are included with the evidence.

Unity2022's public JDK setter rejects Java17. The isolated fixture therefore uses
the supported embedded Java11 for Unity Gradle export, then standalone Java17
with stock Gradle7.5.1/AGP7.4.2. There is no version-check bypass or global JDK
switch. The fixture minimum is API26 and its sample target is34; the release
template's target35 remains a candidate requiring actual policy review.
Ordinary verification builds retain their existing Android settings and are
not RuStore release artifacts.

The native SDK stays outside unconfigured ordinary APKs: the official Pay AAR
has an enabled ContentProvider that can initialize before C# guards run. A
compile define alone would not isolate it. The separate synthetic SDK APK is a
compatibility artifact and is never launched or installed as the game.

The pinned Editor includes the Unity advisory fix introduced in2022.3.62f2;
this does not certify every future security issue. The required Unity splash
remains because the owner has no eligible entitlement.

## Actual verification

90 Python/ASGI/SQLite/RSA tests pass, with30 backend inputs identical before and
after the final run. Coverage includes migration, concurrency, duplicate
invoices/commands, refund races, overflow, lost commit replies, inventory,
attempts, repeated continues,900-coin refill, regeneration and credential scopes.
Provider HTTPS responses are synthetic; they are not real payment acceptance.

The native release/recovery suite passes328 checks:102 configuration mutations,
13 coordinator scenarios, six actual file-journal scenarios and four client
scenarios. It also verifies both approved900-coin rules. Native compatibility
checks pass534 general,13,584 profile,18 connected gameplay and18 portrait
checks. The read-only preflight correctly reports release **blocked** without
changing settings, preferences, valid language choices or packages.

The actual UnityWebRequest test makes20 requests with38 checks and five exact
repeated commands against a separate FastAPI process. A synthetic confirmed
1000-coin purchase produces2250 server coins once; start/tool/quit leave four
lives, starting stock `[4,5,3,2]`, tools `[2,3,3,3]`, revision6. A real process
restart with a different PID preserves the complete wallet, six ledger entries
and purchase receipt. Acknowledgement remains pending because no SDK payment or
acknowledgement call is simulated as completed.

Both internal ARM64 Android build branches pass. The separate SDK export and
Java17 assembly pass, with88 actual static APK checks: pinned dependencies,
synthetic Console/deeplink resources, enabled private Pay ContentProvider,
API26/34 and ARM64 IL2CPP. Its13,346,880-byte APK is deliberately unlaunched.

The ordinary development APK passes clean packaging, CRC/signature/alignment/
ELF checks and native SDK absence inspection. Its303,092,264 bytes hash to
`7ef044dfbeadbbf38038a89204db85188db595511abcc7a83aea783eefafb6f6`.
Installation/startup on isolated QA2/index2/5558 preserves all saved files and
preferences, has no matched runtime exception signatures and retains portrait
Russian Prologue/first-language-menu presentation. Two actual screenshots were
visually inspected. No new gameplay, launch-video timing or tablet review is
claimed. Main stays64; original QA1 stays78 with its unfinished attempt preserved.

Final source has5182 Unity inputs, with17 additions and **zero changed or removed
source80 inputs**. The frozen manifest SHA256 is
`0206ea4d1e146d66e89880ba549c26d3cf2affa434772c7cc9883fcafbf92d19`.
The six counted native suites total14,520 checks; the seventh preflight run is a
correctly blocked readiness readback. Backend90 tests and SDK88 static checks
remain separate counts and scopes.

The initial new guard compiler ambiguity and actual optional-JSON failures are
preserved under `Attempts/001_packageinfo_ambiguity` and
`Attempts/002_inline_json_nulls`. SDK fixture attempts retain the unsupported
Editor-JDK assignment, interrupted remote SDK inventory query, short-process
exit-code capture fault and custom manifest-label conflict. Failed results do
not count as passes. No physical-device or OS power-loss certification is made.

## Registration and remaining release gates

`Release/RuStore/README.md` and `release.example.json` distinguish proposals from
real registration. Candidate package: `com.heartoftherain.game`; candidate
return scheme: `heartoftherain-pay`. The six `hotr_coins_*` identifiers preserve
current Shop quantities. The Console Application ID is assigned only after
creating the application; the HTTPS backend origin follows actual deployment.
Neither exists yet, and no working values are fabricated.

The release preflight blocks RuStore-channel builds and non-development Android
builds using a production package. Configuration syntax cannot override missing
managed guest identity/linking, secure recovery, approved account migration,
normal-game server-wallet routing, a real gameplay verifier, authenticated
encrypted notifications/workers, refund policy, hosted HTTPS/operations,
production signing or Russian privacy/deletion/retention review. Notification
URLs in the template are reserved names, not implemented handlers. Actual
sandbox success/cancellation/termination/deep-link/banking-return/update tests
remain required. Real teams/chat also need reporting, blocking and moderation
before replacing demo pages. No Google Play Integrity dependency is introduced.

Existing source79 gameplay smoothness limitations and archived-reference,
physical-device, whole-game translation and long-session gates remain open.
This checkpoint changes no swap, gravity, obstacle or effect timing.

Primary references: [Pay Unity11.1.0](https://www.rustore.ru/help/en/sdk/pay/unity/11-1-0),
[v2 invoices](https://www.rustore.ru/help/en/work-with-rustore-api/api-subscription-payment/v2-purchase-invoiceid),
[Public API authentication](https://www.rustore.ru/help/work-with-rustore-api/api-authorization-token),
[Unity Android export](https://docs.unity3d.com/2022.3/Documentation/Manual/android-export-process.html),
[Unity security advisory](https://unity.com/security/sept-2025-01).

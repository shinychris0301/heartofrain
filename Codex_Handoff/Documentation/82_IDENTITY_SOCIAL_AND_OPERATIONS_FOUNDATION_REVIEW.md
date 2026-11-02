# Identity, social services and operations foundation

Checkpoint82 is a verified service and client-transport foundation. The ordinary Android game remains checkpoint81 on isolated QA2. Connected app pages, server gameplay settlement and later replay-worker work have separate acceptance gates; this document does not certify those later changes.

The owner requested backend development for launch, including personal records, leaderboards, friends, messaging and team chat. The service now implements these features with authenticated ownership checks and durable transactions. The existing approved artwork, game rules, local profiles and production activation guards are preserved.

## Implemented behavior

- Managed guests use P256 device signatures, expiring sessions, rotating refresh credentials and a separate recovery secret. Guest creation cannot import a client wallet. Repeated signed requests recover their committed result. Account deletion revokes access and closes social participation; retained financial/security records and backups still require an approved retention policy.
- Friends require an explicit recipient acceptance. Blocking suppresses both directions and removes the friendship. Direct messages require an eligible friendship; team messages require current membership. Team creation, joining, ownership transfer, leaving and moderation are service operations. Message/profile/team reporting and operator moderation have their own durable records. Rich text is not trusted as user content.
- Personal records and global/friends/team leaderboards read service progression. Leaderboard participation is explicit. Client telemetry does not award progression. A trusted gameplay verifier is still a separate requirement at this checkpoint.
- RuStore notifications authenticate the documented encrypted payload, bind application/environment identifiers and durably enqueue reconciliation before acknowledgement. Workers query final provider status independently; a callback cannot credit coins. Invoice discovery recovers only known orders and never trusts listing status as delivery authority. Public HTTPS and real Console notifications have not been exercised.
- Backup and restore use SQLite's backup API, validate schema/integrity and require a new destination. Bounded reconciliation/discovery commands and explicit moderator credential tools are available. Production host permissions, restore drills, monitoring and retention remain deployment work.
- Unity identity and social HTTP clients use durable journals and explicit configuration. Android identity uses nonexportable Android Keystore keys and encrypted compare-and-swap storage outside backup. The isolated emulator reports software-backed keys; no hardware-attestation claim is made.

Implementation is in `Backend/hotr_backend/` and `Unity/Assets/HeartOfTheRain/App/OnlineIdentity/` plus `OnlineSocial/`. Operator instructions are in `Backend/README.md`. Owner registration, hosting and signing steps are in `Release/RuStore/OWNER_SETUP.md`.

## Verification

| Evidence | Result and actual scope |
| --- | --- |
| `Verification/Evidence/Launch82/Backend/Verified250/Service_Tests.json` | 250 Python service/ASGI/SQLite tests pass; 62 exact inputs retained; before/after hashes agree. Includes races, idempotency, deletion, revocation, permissions, social isolation, notification recovery and backup/restore. |
| Frozen pinned Unity Editor identity suite | 69 checks / 13 cases pass. |
| Frozen actual Unity HTTP identity suite | 25 checks / 8 cases / 19 requests pass against an isolated loopback service. |
| Frozen actual two-account Unity HTTP social suite | 65 checks / 7 cases; 30 social, four signed identity and four wallet requests pass. Duplicate-message and encrypted outbox recovery, block/report/read checks and unchanged local profile/language/economy are recorded. This is Editor HTTP, not Play Mode or a connected app page. |
| Actual separate Android identity fixture | 24 checks pass across three distinct processes, including signing, stale-write rejection and restart persistence. APK SHA256 `8aca7ff06462c107a117dad50f78aca4dbc28be785c963b6eac0193957b9ce62`. Only `com.heartoftherain.identity82fixture` on QA2/5558 is installed/stopped; ordinary game saves and preferences are unchanged. |
| `Verification/Tools/collect_launch82_foundation.py` | Revalidates the frozen reports, process/log hashes, source manifests, archived inputs and device evidence. All 5,182 checkpoint81 Unity inputs are unchanged in this foundation; 60 new inputs make 5,242. Later edits are intentionally excluded. |

The first full Windows test runs exposed a test-runner multiprocessing recursion: imported child processes ran the complete suite again. The runner now has a main guard. The failed reports and exact inputs are retained; timeouts were not relaxed to hide the issue. An Android fixture build initially omitted the Java source because Unity's generated Gradle source sets require `src/main/java`; the corrected source location is proven by the actual successful fixture. Failed build/device attempts remain in the evidence directory.

## Remaining launch gates

Normal app selection of managed identity/server wallet, connected social pages, backend reward adapters and trusted gameplay verification are not certified here. The installed ordinary APK remains81. A new account does not silently merge existing local balances; migration and optional provider linking require an approved policy and actual provider setup.

RuStore application/product registration, a real HTTPS origin, release signing, Russian privacy/support/deletion information, moderation operations and actual signed Android sandbox/banking-return/restart/upgrade tests remain necessary. No live checkout, public deployment or real-money payment has occurred. `Release/RuStore/pricing.proposal.json` is a configurable recommendation, not a verified RuStore tariff or runtime price source; SDK `amountLabel` remains the display authority.

The requested two-to-three-day window can target submission preparation. RuStore's documented moderation timeline can extend beyond that window; it is not a guaranteed public launch date. The existing Unity license-required splash and earlier measured gameplay stalls remain open and unchanged by this foundation.

Evidence entry: `Verification/Evidence/Launch82/Comparison.html`. Subsequent replay and ordinary-client integration must keep this historical proof intact.

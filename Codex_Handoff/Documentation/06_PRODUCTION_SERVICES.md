# Production state and service design — proposed
This document is an implementation contract to build next. These services do not exist in the baseline.

Daily Gift UI follow-up: `32_BACKEND_DAILY_GIFT_UI_REVIEW.md` adds asynchronous use of the real service through the existing modal for guarded, isolated Editor/development review profiles. Loading, close/reopen, HTTP retry, pending recovery and late-response behavior are verified separately from ordinary account migration and production service selection, which remain open. No default endpoint, token, background sender or account import is introduced. Backend authority/configuration is unchanged; response faults are restricted to the opt-in test helper. Evidence is `Verification/Evidence/BackendGiftUI`, with native UGUI rendering rather than new device screenshots.

Portable-backend follow-up: the owner approved local implementation before choosing hosting. `31_PORTABLE_BACKEND_REVIEW.md` and `Backend/README.md` now describe a runnable authenticated FastAPI/SQLite service with server-controlled UTC, atomic reward receipts, gift/milestone/practice-Cup endpoints, a privileged first-clear acceptance contract and explicitly untrusted diagnostic ingestion. Unity's asynchronous HTTP adapters are tested against a separate real process with isolated accounts. This is a local/staging source checkpoint; the ordinary app factory and deployed Rain Cup APK are unchanged. Actual gameplay verification, production identity/onboarding/recovery, full wallet/profile sync, normal-page/Android integration and hosting remain open. This supersedes earlier statements that no backend code exists, without claiming a production service.

Local event instrumentation is now implemented in the native source checkpoint documented by `30_PROFILE_EVENT_AUDIT_REVIEW.md`. `PlayerProfileHost.Events` projects durable receipt events on explicit capture; an Editor/development archive supports bounded, idempotent local delivery. It performs no automatic capture, upload or gameplay-frame work. Opening balances are inferred rather than fabricated historical events. No real analytics provider, consent/privacy integration, trusted account or production sender is connected. Evidence is `Verification/Evidence/ProfileEvents`; the deployed APK remains the preceding Rain Cup build.

Current local implementation, 21 October: `27_DAILY_GIFT_AND_DURABLE_PROFILE_REVIEW.md` supersedes the baseline's memory-only state. A version-one atomic file repository now persists progression, wallet, lives, all eight stock fields and attempt/reward receipts; settings/tutorial adapters remain unchanged. The owner approved one loss on reopening an initialized unfinished attempt, with used items spent and no charge for an uninitialized reservation. Daily Gift has a labelled local development authority and durable confirmation/retry flow. Development and release storage are separate; production claiming selects an unavailable adapter. No account, trusted-time, commerce, social or competition backend is implemented. Life regeneration, cloud recovery, future migrations and board/RNG resume remain open.

Wellworks follow-up: `28_WELLWORKS_REVIEW.md` adds owner-approved permanent Chapter 1 first-clear milestones using atomic local reward receipts and the shared wallet/inventory. No profile schema migration or timer is introduced. It is a development preview; release claims remain disabled pending production authority. Targeted native/Android verification and final installations are recorded in `Verification/Evidence/Wellworks`; this does not implement an account or competition backend.

Rain Cup follow-up: `29_RAIN_CUP_REVIEW.md` implements the approved development practice with four explicitly scripted rivals, frozen joined rules, atomic campaign-win/point receipts and one finishing prize. The local timer is untrusted; real competition and release claims remain unavailable. Native/targeted Android review and matching final installations are under `Verification/Evidence/RainCup`. Production needs authoritative time, authenticated participation, validated scores, matchmaking/ranking, offline reconciliation and reward fulfillment; none is supplied by the local practice adapter.

## Durable profile
Create a versioned profile with stable player ID, schema version, revision, highest first-cleared level, chapter flags, coins, stars, lives with regeneration timestamp, separate starting inventory (Rocket/Bomb/Orb/Golden), tool inventory (Hammer/Axe/Ram/Atlas), settings, tutorial stage, attempt journal and settlement references. Do not store payment secrets or trust a local wallet as the final purchase ledger.

Start with an atomic local repository for offline gameplay and a fake repository for tests. Save to a temporary file, flush, replace the current snapshot atomically, retain a last-known-good backup, and validate nonnegative bounded values. Add migration fixtures from current demo defaults and the old three-slot inventory. Never overwrite an existing save with Home preview data. Isolate reset-demo buttons from release builds.

Life policy, decided 22 October 2026 (`50_LIFE_REGENERATION_REVIEW.md`): one life every 30 minutes up to five, timer started at the first observation below max, and a full refill at zero lives for 500 coins; both are receipted profile transactions (`lifeCredits`, `lifeRefills`) audited as `lives_regenerated` / `lives_refilled`. The clock is device UTC through `PlayerProfileHost.Now` until server time replaces it; no profile change is needed for that swap. Paid continues remain undecided. Home presentation is connected in `61_HOME_LIVES_R1_REVIEW.md`: next-life countdown, confirmed receipt feedback and the existing refill route; authority/rules remain unchanged.

Define the policy for interrupted attempts before adding life regeneration or monetized continues. Proposed rule: one durable attempt ID owns selected-item debit, outcome, life loss, first-clear reward and completion flags. Resume an interrupted board only if RNG, occupants, remaining goals, moves and board/config versions can all be restored. Otherwise explicitly abandon via the chosen policy; do not double-charge or award a second first clear. Initially save only at stable action boundaries; do not serialize half a visual effect as authoritative state.

## Attempt transaction
1. Validate level/config version, lives and inventory; create a persistent start reservation with an idempotency key.
2. Initialize board and grant selected items once. On initialization failure, release reservation; on success, atomically commit inventory debit and active attempt.
3. Resolve model actions. Visual callbacks can acknowledge presentation, not issue currency.
4. On win, commit completion + first-clear reward + attempt outcome in one transaction. Replay returns the original receipt, not another grant.
5. On confirmed exit or normal failure, apply the approved life policy exactly once and route through the same retry flow. Cancel exit has no charge. On an engine fault (resolution guard) release the attempt as `Released`: refund the starting items, charge no life, keep used tools spent (owner decision, 22 October 2026).
6. On restart, recover committed outcomes, unresolved reservations and pending purchases before allowing conflicting operations.

Current normal out-of-moves, confirmed exit and startup interruption now settle through the durable HomeLevelFlow attempt service. Tool stock persists across loads/restarts; save failure rejects the board action, and an unreadable post-commit confirmation blocks input until the original command is reconciled. Wins persist before presentation, whose callbacks only reveal the saved receipt. These local repairs do not supply a trusted purchase ledger or account recovery.

## Suggested interfaces
| Boundary | Operations | Required behavior |
| --- | --- | --- |
| Profile repository | Load, migrate, commit expected revision | Atomic write, backup/recovery, stale-write rejection |
| Attempt service | ReserveStart, CommitStart, SettleWin, SettleFailure, Abandon | Idempotent attempt ID, clear outcome contract |
| Wallet/inventory | Credit/Debit with transaction key | Audit trail, bounded values, no UI-side mutation |
| Catalog/config | Load version, validate, activate, rollback | Cached safe defaults; no mid-attempt rule change |
| Commerce | Fetch metadata, initiate purchase, verify/reconcile | Store price display, server verification, durable grant |
| Live operations | Server UTC, eligibility, claim | Actual schedules; claims idempotent |
| Social | Friends, rankings, teams, chat/mail | Authenticated access, pagination, rate limits, moderation |
| Telemetry | Enqueue typed event, flush | Stable IDs, deduplication, privacy controls, offline queue |

Use adapters so pure gameplay remains testable without network access. The owner selected a portable backend first; hosting/provider, managed identity and account recovery remain unselected. Backend credentials stay server-side. Version board data and remote parameters so replays and experiment results remain attributable.

## Commerce fulfillment
Select and pin a Unity-compatible billing SDK only after the baseline builds. Unity's current IAP installation guide calls out additional Android configuration for IAP 5.4.0 on Unity 2022.3 [S1]. Do not blindly install the newest package into this project.

The proposed flow is: store purchase → receipt/token to backend → store verification and account/product checks → deduplicated ledger entry and atomic inventory grant → durable confirmation → store completion/acknowledgment → UI refresh. Retries return the same entitlement receipt. Test network loss and app termination at every boundary.

**Terminology matters:** Unity IAP's `PendingOrder` is awaiting fulfillment; Google Play's platform purchase state `PENDING` is awaiting payment. Verify the platform transaction is eligible/paid before granting. Do not grant a Google `PENDING` purchase. On Google, use the purchase token for duplicate detection, not the optional order ID [S2]. Unity can redeliver callbacks, and consumed consumables require the app's own durable history [S3]. Avoid mixing multiple acknowledgment owners; choose SDK/client versus backend responsibility and document the recovery path.

Keep a ledger containing player/platform/product/catalog version, verified transaction identifier, item quantities, currency/tax basis, state timestamps and grant/refund references. Receipts/tokens belong in restricted commerce storage, not general analytics. Handle cancellations, deferred payments, already-owned results, pending recovery, refunds, chargebacks and account changes. Reconcile consumables through the game's ledger; restoring permanent entitlements is not permission to regrant consumed coins.

## Social and live operations
Replace `LeaderboardDemo.json` and `TeamsDemo.json` behind service interfaces. Do not present bots/demo names as live players. Real chat requires reporting, blocking, moderation and support operations; rankings require server-authoritative scoring and season boundaries. Team life-help claims must use a wallet transaction, not only a chat message. Define guest/account merge and deletion before launch.

Event timers must use server UTC and cached schedule versions; no perpetual fake countdowns. Existing Home strings such as “2d 06h” are samples. Invalid/offline config should preserve gameplay and disable unavailable purchases/events cleanly.

## Release privacy and store setup
Prepare real support/contact, Terms and Privacy destinations; current official links are empty. Choose launch territories and intended audience, then review applicable store/payment/privacy requirements. Apple's review rules and Google Payments policy vary by eligibility/territory; do not assume a universal external-checkout entitlement [S4, S5]. Tracking consent and privacy declarations must match actual SDK behavior [S6]. These are implementation dependencies, not a legal certification.

Source URLs and checked date are in `13_SOURCES_AND_PROVENANCE.md`.

# Implementation backlog and Codex milestones
Priorities are proposed engineering order. Existing approved visual designs remain the baseline.

23 October dense-burst follow-up: review `60_DENSE_BURST_EFFECT_BATCHING_REVIEW.md` closes the slow-motion burst under ENG-06's heavy-effect evidence (effect mesh batcher; native parity plus same-APK QA A/B for every obstacle family and plain tiles) and settles D6, D9, D12, D14, D16, D18 and D19 from the 22 October analysis with tests. Backlog from the second-pass app review: D10 (Atlas/reshuffle attempt budgets on large boards need a constructive fallback — mechanic decision), per-entry effect sampling cost, `LabelFit` linear passes, booster choreography lookups, string-keyed clip lookups, reward-reveal tint after back-to-back claims, leaderboard search on focus loss, preview-state fallback on a failed save load (owner decision on the shipped scene flag), Rain Cup name ellipsis on surrogate pairs, backend request disposal on teardown, M68 celebration mesh rebuilt per frame. ENG-06 physical-device evidence remains open.

22 October device pass: review `54_ANDROID_REGRESSION_AND_INSTALL.md` restores the full Android regression (broken since checkpoint 41) and re-certifies checkpoints 46–53 on the emulator: 1,706 checks, 50 boards. ENG-06 physical-device evidence remains open.

22 October loss beat: review `53_LOSS_BEAT_REVIEW.md` adds the owner-decided loss dialog to the unified failure flow (ENG-03/04) and closes the cut loss cue. The Android regression suite's failure phase needs its next emulator pass to re-certify.

22 October fault release refund: review `52_FAULT_RELEASE_REFUND_REVIEW.md` settles the ENG-03 edge for engine faults (refund items, spare the life, `Released` state, `attempt_released` audit kind) and repairs the checkpoint-47 audit gap for released attempts with tool use.

22 October attempt seed: review `51_ATTEMPT_SEED_REVIEW.md` closes the "RNG snapshot" half of ENG-07 for the connected flow (each attempt's refill seed is recorded in its receipt); exact board resume still needs the move list and a stable-boundary policy. Leftover-move conversion is decided against; do not reopen without a new owner decision.

22 October life regeneration: review `50_LIFE_REGENERATION_REVIEW.md` implements the owner's decided policy (30-minute regeneration to five, 500-coin refill at zero) as durable, audited transactions; this closes the "life regeneration" entry in the known gaps below for the local profile. A Home countdown, trusted time and store life offers remain open design/service items.

22 October build-scope follow-up: review `49_SHIPPING_BUILD_SCOPE_REVIEW.md` closes the "remove review-only scenes from the shipping build" task from `03_UNITY_SETUP_AND_ARCHITECTURE.md` and guards the review/QA runtime scripts; `-Mode AndroidReleaseBuild` now proves the non-development compile. Store identifier, signing and release settings (ENG-01 production settings, ENG-12) remain open.

22 October tool-inventory follow-up: review `48_TOOL_SPEND_RECONCILIATION_REVIEW.md` closes an ENG-05 edge: the unconfirmed-save reconciliation is now per attempt (`ToolSpendReconciliation`), verified by a fault-repository case that crosses the attempt boundary. Production account reconciliation remains open.

22 October settlement follow-up: review `47_TERMINAL_STATUS_SETTLEMENT_REVIEW.md` extends ENG-03/ENG-04 to the two terminal statuses the unified attempt flow did not cover (`No legal moves`, `Resolution limit`) and removes the HUD's unsettled in-place reload from the connected flow. Guard exhaustion is now a diagnostic release, not a player outcome, as `04_GAMEPLAY_AND_LEVEL_SPEC.md` requires. Refund of items spent on a faulted attempt and the wording of a failed-reshuffle end state are owner decisions.

22 October presentation follow-up: review `46_OBSTACLE_FAMILY_PREPARATION_REVIEW.md` extends the checkpoint-44 crate preparation to every obstacle family, closing the first-hit playback hold that ENG-06 lists under heavy-effect evidence. Native evidence is refreshed under `Verification/Evidence/CrateBurst`. Android timing for non-crate families, physical-device frame budgets (ENG-06) and release memory/compression (ENG-10) remain open; no APK is claimed.

21 October local appearance follow-up: review `34_PROFILE_M71_INTEGRATION_REVIEW.md` integrates the supplied Profile/Change Name page, preferences and Home portrait updates. Native local-state, rendering, scrolling and compatibility evidence is `Verification/Evidence/ProfileM71`. This closes local Home appearance UI only; real identity/team services, entitlements, other-page portrait wiring and device/release verification remain open. No new APK is claimed.

21 October backend Daily Gift UI follow-up: review `32_BACKEND_DAILY_GIFT_UI_REVIEW.md` closes the review modal's asynchronous backend gap: loading, retry, closable pending work, protected save dialogs, navigation races, receipt recovery and cached claimed state. It uses explicit isolated Editor/development profiles. Ordinary production selection, account migration, secure onboarding, hosting and Android integration remain open. Evidence is `Verification/Evidence/BackendGiftUI`; no new APK is claimed.

21 October portable-backend source checkpoint: review `31_PORTABLE_BACKEND_REVIEW.md` implements a runnable local/staging authority, atomic reward claims, authenticated receipt recovery, explicit client-reported diagnostic ingestion and native Unity HTTP adapters. The owner deferred hosting. The first-clear verifier contract is privileged but its actual gameplay validator is not implemented. Ordinary factory/profile migration, full wallet sync, production identity/recovery, normal-page/Android integration and real competition remain open. Evidence is `Verification/Evidence/Backend`; the deployed APK remains Rain Cup.

21 October next engineering source checkpoint: review `30_PROFILE_EVENT_AUDIT_REVIEW.md` implements the local ENG-09 event layer: receipt-backed typed events, stable IDs, arithmetic reconciliation and explicit development archive delivery. It introduces no automatic transmission or invented timestamps. Native evidence is `Verification/Evidence/ProfileEvents`; production privacy/consent, authenticated delivery and long-lived archival remain open. The deployed Android APK remains the Rain Cup build.

21 October local-state update: review `27_DAILY_GIFT_AND_DURABLE_PROFILE_REVIEW.md` closes the memory-only gameplay/profile gap for the development build. Native repository/transaction/layout/font checks and targeted Android file/restart/retry checks pass. Daily Gift is the first component implemented for review; its quantities and local development authority were explicitly approved. Review `28_WELLWORKS_REVIEW.md` now adds verified permanent first-clear Wellworks development rewards. Review `29_RAIN_CUP_REVIEW.md` adds verified local Rain Cup practice; production authority/account services, real competition, life regeneration and exact resume remain open. Daily Gift campaign evidence retains its preceding APK. Current targeted review/installation evidence is `Verification/Evidence/RainCup`; a fresh full Android campaign pass is not claimed.

The owner's subsequent M68/fluidity update is tracked in `17_FLUIDITY_AND_M68_REVIEW.md`. Native timing/input/renderer optimizations and Home reward presentation close specific engineering defects. Heavy-combo frame budgets, physical-device certification, durable profiles/attempts and services remain open; presentation improvements do not complete those production milestones.

Verification update, 19 October 2026: native compile, 530 Editor checks and the refreshed connected smoke pass. The first expanded native Play Mode suite passed 1,183 checks. See `16_PLAYBACK_AND_UI_REVIEW.md` for effects/UI repairs and subsequent Android coverage; `15_VERIFICATION_REVIEW.md` records the initial environment. Normal failure now uses connected life/retry handling and tools retain spending within an app session. Durable repository/attempt work and physical certification remain open; these narrower repairs do not complete ENG-02/03/05.

| ID | Priority | Task and source | Acceptance / dependency |
| --- | --- | --- | --- |
| ENG-01 | P0 | Establish native baseline in Unity2022.3.62f3; record generated settings | Clean import, compile and connected flow; no engine upgrade bundled |
| ENG-02 | P0 | Durable ProfileRepository and migrations; replace Home preview bootstrap | Local v1 implemented and restart/backup tested; legacy initial inventory splits Rocket/Bomb. Future durable schema migrations and cloud/account recovery remain open |
| ENG-03 | P0 | Unified AttemptService around HomeLevelFlow/LevelCompleteSession/EndLevelSession | Durable local reservation/start/tool/outcome receipts implemented; replay/retry cannot duplicate. Initialized interruption is one loss on reopening, once |
| ENG-04 | P0 | Route normal failure through retry/attempt flow | Connected normal failure, exit and reopening now use durable settlement |
| ENG-05 | P0 | Inject persistent tool inventory into GameplayScreen | Durable local inventory integrated; failed/unknown saves reject or reconcile the original tool command before board mutation |
| ENG-06 | P0 | Add Unity/device visual and performance evidence | Current board/UI/VFX and R4 arm seam match references; actual frame timing recorded |
| ENG-07 | P1 | Versioned level/save schema and RNG snapshot | Deterministic restore or explicit stable-boundary restart policy; migrations tested |
| ENG-08 | P1 | Honor validated moss growth parameters; correct stale L50 note | Repaired with native interval/cap/legacy/invalid-rule tests; default behavior and L50's 44 moves preserved |
| ENG-09 | P1 | Instrument attempt/progression/economy events | Local receipt projection and archive (review 30), authenticated staging ingestion and native HTTP resend (review 31) implemented; client reports never grant rewards. Production consent/privacy, automatic delivery/acknowledgement and archival remain open |
| ENG-10 | P1 | Optimize atlas residency/allocation/import settings | Measured device budgets met without visual regression |
| ENG-11 | P1 | Human balance/locale pass on all50 levels | Recorded cohorts/sample sizes, complete goals and no critical dead ends |
| ENG-12 | P1 | Store integration + backend fulfillment | Platform sandbox matrix passes; localized prices; paid state verified; recovery/refunds |
| ENG-13 | P1 | Real support/legal/account operations | Working URLs, account deletion/recovery policy, actual privacy declarations |
| ENG-14 | P2 | Correct offer ladder and eligibility | No unintended dominated offer; all bundle quantities explicit; no fake timers |
| ENG-15 | P2 | Optional rewarded-ad experiment | Verified reward callback/claim, no-fill/offline path, frequency cap, holdout |
| ENG-16 | P2 | Production friends/teams/rankings | Real authenticated data, report/block/moderation, server scoring and claims |
| ENG-17 | P2 | Real events and remote config | Server schedule, claim idempotency, rollback, deterministic experiment assignment |
| ENG-18 | P2 | Chapter2 production plan | 50 playable levels, localized beginning/ending, art/VFX and design approval |

## First Codex task
Ask Codex to inspect the baseline, run the available native import/compile checks, and report exact blockers. Then implement ENG-02 with a narrowly scoped repository and tests before connecting commerce. Do not ask it to “finish all monetization” in one change. Each task should have a concrete acceptance check and a small reviewable diff.

## Known gaps to keep visible
Campaign rewards, lives and all stock now persist locally with attempt receipts. Life regeneration, exact board resume, future save migrations, account/cloud recovery and a trusted wallet remain open. Daily Gift is a development preview; production claiming is disabled pending a real authority. Wellworks now has permanent development milestones and durable claims (review 28); production authority remains open. Rain Cup now has local practice, durable points and prize claims (review 29); real competition/backend authority remain open. Demo Shop has no purchase API. Social pages are local snapshots. Official links are empty. Internal Android development builds exist; shipping signing/settings and physical-device performance certification remain open. Some gameplay/error strings may bypass localization. No editable 3D model source files exist in the supplied Unity tree.

Do not resolve design questions such as Golden+Golden, new power recipes, new art palettes, live prices or later chapter endings by inventing an answer. Continue with engineering work that is already defined, and bring those specific design choices back to the user.

## Definition of done for a change
Explain the problem, changed paths, resulting behavior and validation scope. Preserve unaffected assets/levels by hash when appropriate. Include a deterministic regression test for transactional/gameplay bugs, or visual/device evidence for rendering changes. Update the corresponding docs and known-gap status. Distinguish passing source tests from passing Unity/device tests. Keep design approval and deployment/store publication separate from code completion.

# Checkpoint 79 — first-pose preparation and snapshot repair

25 October 2026. Targeted source checkpoint 79: eligible swaps present their unchanged 120 ms head to the gameplay camera before managed tail/resource preparation starts on a worker. A duplicate-ID snapshot cache transition is repaired. Native, build and Android checks pass; the sampled visual review finds no new discrepancy. One 366 ms recorded interval remains unresolved, so this is not whole-game smoothness approval.

The owner approved the next engineering priorities after checkpoint 78. Gameplay rules, masks, approved art/GUIDs, reward ownership and conservative cascade eligibility remain preserved. Evidence: [Comparison.html](../../Verification/Evidence/Gameplay79/Comparison.html).

## Runtime changes and scope

The change lets an eligible accepted swap submit its first presentation pose before compiling the rest of its playback queue. The model command still runs synchronously and remains authoritative for moves, inventory, goals and the accepted outcome. The new worker performs managed presentation compilation and dependency-path preparation; it does not execute model commands, grant rewards, release attempts or call Unity rendering/loading APIs.

An eligible command has a pure leading swap with two distinct motions and no power plan, booster, damage, removals, creations, collections or existing playback tracks on that first step. Its published head retains the existing 120 ms duration and original snapshot/motion references. Other commands retain the established synchronous path. Main-thread request capture and any head-resource readiness work also remain synchronous; this is not a claim that all command work has moved off the main thread.

`GameplayStartupPreparation79` waits for the gameplay screen's own camera to finish rendering a submitted pose in the same frame before starting the job. The job receives a private raw-step array, copied level-mask geometry, captured development policy/culture and detached string-only resource metadata. The DTO contents shared with the published head are read-only. Resource resolver caches are per context, so the worker and renderer do not share mutable resolver dictionaries. Texture/sprite loading, GPU work, playback feedback and app callbacks stay on the main thread.

Completion is accepted only for the same generation, board, bank, published head and compiled resource-plan references. A reload or destroyed screen discards the old request. Disable cancels the old job while retaining the request; re-enable creates a new generation and requires a fresh own-camera witness. Cancellation does not join or block the main thread; managed work stops at its cancellation boundaries, and a stale completion cannot install its tail.

If the 120 ms head ends before preparation completes, presentation holds the post-swap board and retains Busy. It accepts neither a new command nor a buffered gesture, does not emit an early settlement, and does not accumulate playback-clock debt. Installing a completed tail preserves the established queue, schedule and readiness checks. A slow worker can therefore still produce a visible hold; Android evidence must quantify how often and how long this occurs.

`BoardModel.RecordPresentationFault` gives a post-accept presentation error an explicit model-owned outcome. It preserves a committed `Won` result and an existing engine-fault diagnosis. Other statuses, including a last-move `Out of moves`, become `Engine fault` so the established flow can release a failed attempt rather than treating the presentation failure as a normal loss. The new lifecycle suite verifies model statuses and one settlement callback. It does not independently prove durable HomeLevelFlow release, win receipts, starting-item refunds or service idempotency.

Snapshot rebuilding receives a separate narrow repair. A rank cache is reusable only if it was built from unique piece IDs. In checkpoint 78, a duplicate-ID snapshot followed by removal could leave the cache count equal to the new piece count while retaining an out-of-range rank; the old helper then left a null result slot and threw. Checkpoint 79 explicitly disables reuse for that cache and preserves the stable fallback ordering. Rebuilding ranks also uses one dictionary indexer assignment per piece instead of a membership lookup followed by an insert. Full current-ID/reference checks, copied snapshot pieces and deterministic ordering remain intact.

The final source manifest is `a325a4ca542347925dffe9bdfd85f99a9597f52a6e1de0379df44db5b25ec6a4`, covering 5,159 Unity inputs. Compared with the frozen checkpoint-78 manifest, 13 existing inputs change and nine new C# files each have a new `.meta` file. No existing `.meta`, approved artwork, shader, level mask, project setting or package setting changes in this delta.

| Source group | Final delta |
| --- | --- |
| Existing runtime | `BoardModel`, `BoardPlayback`, `LocalCascadeContinuation`, `GameplayCommandPreparation`, `GameplayScreen`, `EffectResourcesPure` |
| Existing verification | `CascadeTimingProbe`, `Execution78Probe`, `PowerFall77Probe`, `CommandPreparation78Verification`, `PowerFallPreparationVerification`, `PresentationWarmupVerification`, `NativePlaySmoke` |
| New runtime pairs | `GameplayStartupPreparation79.cs/.meta`, `PlaybackPreparationJob79.cs/.meta` |
| New verification pairs | `PlaybackPreparation79Verification`, `Snapshot79Verification`, `StartupLifecycle79Verification`, `FirstPose79Probe`, `Playback78Control79`, `Snapshot78Control79`, `Snapshot79Proof`, each with `.meta` |

## Final native verification

All 35 pinned Unity 2022.3.62f3 suites pass 976,622 reported checks in fresh recorded processes. Their suite manifests bind to the final frozen input set. This is native Editor/Play Mode evidence; check counts are custom assertions, not an equivalent number of independent player scenarios.

| New suite | Final result and coverage |
| --- | --- |
| `Snapshot79` | 18,313 checks; 350 model commands; two reproduced archived-78 duplicate/remove crashes; 83 ownership/state cases; six presentation-fault model cases; eight actual snapshot traces and four synthetic trace families |
| `Worker79` | 5,039 checks; 350 model commands; 366 queue comparisons; 367 worker requests; 50 eligible corpus swaps; 53 leading-swap job cases; 16 policy cases; three synthetic cases; four cancellation and four negative cases |
| `StartupLifecycle79` | 130 checks across six real GameplayScreen Play Mode cases, with actual `Camera.Render`/`onPostRender` witnesses and controlled worker gates |

The 350-command model proof retains raw steps, final snapshots, checkpoints/RNG and dictionary order against the sealed earlier corpus and exact archived controls. Snapshot ownership tests include replacement/reinserted pieces, mutable IDs, duplicate IDs, growth, culture and repaired state. Both duplicate/remove positive controls reproduce `NullReferenceException` in the exact checkpoint-78 helper; the repaired current result matches the checkpoint-77 output. These are invalid-state transition controls, not evidence that ordinary authored boards routinely contain duplicate IDs.

The worker proof compares exact compiled queues, recursive playback tracks, continuation segments, contacts, poses and ordered dependency paths with its archived checkpoint-78 control. It also checks captured policy, detached metadata, explicit start, once-only take, cancellation, exceptions and source/raw immutability. The control binding is to archived source bytes rather than a newly invented approximation. The worker suite's thread waits coordinate tests; their elapsed time is not gameplay performance.

The six lifecycle cases are:

1. A leading swap renders before a held `BeforeBuild` boundary. Holding beyond the head duration keeps Busy, excludes rapid swaps/taps/tools and buffered input, and emits no early settlement; releasing the gate installs the exact tail and settles once.
2. Reload cancels the old request; its late result is discarded and cannot alter the replacement board.
3. Disable/re-enable creates a new generation and requires another actual camera witness before continuing the same accepted request.
4. Pause allows worker completion/tail installation without advancing the playback clock.
5. A post-accept presentation fault after actual move exhaustion settles once as `Engine fault`.
6. The same injected fault after an explicit goal-free winning fixture retains `Won` and the accepted model checkpoint.

The fault cases expect and count their injected exception logs. The winning fixture deliberately removes goals/obstacles and has no HomeLevelFlow or persistent receipt integration; it is not a full production win-flow test.

Existing warmup and app-smoke harnesses now supply an actual offscreen own-camera render when batchmode has no GameView. Both final reports use `default 79-leading-swap-offscreen-own-camera`, record the camera/job-start witness and retain completed traces. Their witness may show the active head or an already-held post-swap pose. The separate lifecycle suite is the first-head-before-work proof; the legacy harness witnesses must not be presented as a second performance or first-head experiment. All prior warmup/smoke assertions remain enabled.

The preparation replay retains all 228 original frame samples and pose/mesh parity controls. Its source guard explicitly records unchanged archived-76 files plus fresh model-78 and worker-79 equivalence proofs for permitted changed files; it does not claim those changed source bytes are unchanged. Current raw native replay hashes remain stable, and the final snapshot matches the historical Android fixture. Native and Android raw serialized turn hashes differ in the existing preparation comparison; that difference remains recorded without an invented serialization/math explanation or a cross-platform byte-parity claim.

## Snapshot measurements and interpretation

The direct snapshot experiment measures only actual `Snapshot` calls. Fixture construction, applying trace state, capture, result serialization and hashing occur outside each measured span. Diagnostics are recorded separately. Twelve alternating pairs are retained per cold/warm mode, including slower current samples and completed-collection counts. Cold/warm describe cache setup within this isolated experiment; they do not represent Android cold launch or a long-running player session.

For L4, both implementations record 36 calls, 21 cache hits and 15 rebuilds, with 2,558 copied pieces and 1,064 rebuilt ranks. All 15 rebuilds are classified as cache-eligibility/count rebuilds, not misses caused by the full identity scan. The other actual traces also rebuild repeatedly; Golden/Bomb records the same 15 rebuilds and more rebuilt ranks. The evidence therefore does not show a new L4-only cache churn mechanism.

In the final native run, L4 direct cold medians are 0.4695 ms for the archived-78 helper and 0.4552 ms for current; seven of 12 current samples are slower. Warm medians are 0.4512 and 0.44285 ms; six of 12 current samples are slower. Across all eight actual traces and both modes, 10 of 16 current branch medians are lower, with 99 of 192 current pairs slower. The four synthetic families have three of eight lower current medians and 44 of 96 slower current pairs. These mixed short CPU spans support the narrow correctness repair and reduced rebuild lookup count, not a universal speedup or allocation-saving claim.

This Editor 78-to-79 direct-helper comparison cannot establish the cause of the earlier Android 77-to-78 whole-command L4 regression. The earlier inclusive snapshot diagnostic also contains observer/timer overhead and was not a standalone repeated direct-helper experiment. That causation question remains open after the scoped Android controls; do not dismiss the earlier regression as noise or equate cross-instance timings.

## Preserved failed attempts

Five failed native attempts are retained with their source/report/process evidence under `Verification/Evidence/Gameplay79/Attempts`. None produced the accepted final Android build or installation.

| Attempt | Failure and correction |
| --- | --- |
| `001_snapshot_fixture` | The new synthetic duplicate-ID fixture omitted required level metadata and threw during construction after the 350-command corpus passed. Required fixture metadata was supplied. |
| `002_snapshot_direct_fixture` | A synthetic same-count/new-ID benchmark compared against incorrectly ordered expected IDs after the corpus, reproduced crash, ownership and fault controls passed. Expected synthetic ordering was repaired; strict raw/final/ID comparisons remain enabled. |
| `003_legacy_source_guard` | The old preparation guard rejected intentionally changed playback source after the three new suites and preceding checks passed. The permitted migration now requires fresh exact archived-control queue/path/pose proof and current process/source bindings. |
| `004_worker_process_bom` | The migrated test guard passed a PowerShell UTF-8 BOM to `JsonUtility`. The parser now trims the BOM; production runtime did not change for this correction. |
| `005_batchmode_camera_witness` | Warmup timed out after 32 preceding suites passed. Batchmode never rendered the camera required by the new runtime witness. Warmup and app-smoke harnesses now explicitly submit/render the real own camera and assert the actual witness; the runtime gate is retained. |

The count for attempt 005 is 32 preceding passing suites; an earlier reason note said 31 and contains an appended correction. These failures are not silently replaced by final pass reports and do not waive their original assertions.

## Actual native still inspection

Seven actual lifecycle originals were individually viewed in the earlier preserved run. All seven final PNGs are byte-identical to those inspected originals, so the final notes explicitly reuse only those exact-pixel observations and rebind the fresh report, process and suite manifest to the final source. The final files were not reopened. Five ordinary first-pose captures share one byte-identical starting layout; the resume and synthetic winning fixtures supply the other two views.

The inspected lifecycle stills show the supplied backdrop/mask, gem bodies and obstacle formation without an obvious new missing-texture material or displaced duplicate board. They are 720x1280 direct camera targets with no HUD overlays and a small central board. They do not approve production viewport scale, HUD readability, animation trajectories, sustained smoothness or Android output. The goal-free winning fixture's empty former obstacle cells are intentional fixture state.

The parent also viewed the dense and transformed native pixel originals under the earlier candidate. Both final files are byte-identical to the preserved inspected copies; the final notes explicitly record that reuse. The fresh dense suite reports strict pixel parity separately. The other four comparison originals were not manually viewed in this review. Neither these synthetic density stills nor automated pixel equality approve effect density, animation timing or physical-device quality.

Bindings and exact inspected-file hashes are recorded in `Native_Lifecycle_Visual_Notes.json` and `Native_Pixel_Visual_Notes.json`. The inspection scope remains separate from native assertions and the Android visual review below.

## Builds, target isolation and saved data

Both pinned Unity non-development and development ARM64 builds pass with zero errors, as do import audits and the final 5159-input freeze check. Clean packaging preserves all 1088 non-signature entries and the signer. Development signature, ZIP4 KiB alignment and static ELF16 KiB load-segment checks pass. The final development APK is 302,775,024 bytes, SHA-256 `2bfa6c2690889df0bbf749545f01b85a5a16ea39979b45ad7e954ea266ea71b5`. The non-development artifact is an internal compile/build check, not a certified store release.

The existing QA1/5556 preflight found one active attempt and correctly blocked installation/testing there. Its failed read-only preflight is preserved under Diagnostics. A fresh LDPlayer instance was added as **Heart of the Rain QA79 isolated**, index 2/5558, at 900 × 1600, 240 dpi, 4 CPU cores and 4096 MiB. It was not copied from the active save and required no app-data clear. The initial `add` command returned the new index 2 rather than zero; exact list/config/ADB checks established creation before proceeding. ADB was enabled only on this stopped new instance. `QA_Target.json` authorizes explicit target-aware runners while retaining every attempt/save guard.

All Android tests ran on this separate target. Final read-only hashes confirm the original QA1 preferences, profile/authority files and checkpoint 78 APK are unchanged: revision 111 and one active attempt remain. QA1 is restored to stopped. Main index 0 remains stopped on deployment 64. New QA2 has checkpoint 79, its fresh profile remains unchanged, and normal first-time Prologue startup is inspected and left running. `QA_Isolation.json`, `Protected_Original_Final.json` and `Normal_Startup.json` bind these distinct facts.

## Android first-pose controls

The actual 18-row first-pose experiment passes 16 natural rows/eight alternating startup-only pairs plus two deliberately held workers, retaining 2051 frame samples. All eight sampled current commands return sooner, with no natural head-end metadata hold. Each branch retains identical turn/final/checkpoint/dictionary-order/compiled-queue/resource signatures, the same published head object and 120 ms schedule. The two forced holds prove Busy/input/buffer gating and once-only settlement.

| Fixture / dispatch | Sync startup command ms | Worker startup command ms | Sync presentation ms | Worker presentation ms |
| --- | ---: | ---: | ---: | ---: |
| L4 / update | 135.119 | 26.431 | 87.477 | 3.173 |
| L4 / coroutine | 48.305 | 36.096 | 22.555 | 1.914 |
| L14 / update | 27.889 | 8.387 | 19.402 | 2.421 |
| L14 / coroutine | 27.987 | 10.890 | 15.011 | 1.894 |
| L31 / update | 26.646 | 12.490 | 17.608 | 2.351 |
| L31 / coroutine | 22.695 | 18.537 | 15.158 | 1.420 |
| L33 / update | 20.514 | 9.231 | 12.129 | 1.458 |
| L33 / coroutine | 17.274 | 7.359 | 10.093 | 1.473 |

These are one matched pair per level/dispatch in the current APK, with fresh banks. The synchronous control restores the archived 78 startup helper; Snapshot79 remains active in both branches. This is not a whole-old-app comparison or an exclusive model/worker speedup estimate. Actual runtime PlayerSwap delegate calls in Update/coroutines are distinct from OS touch-to-display latency. Hashing occurs after idle and outside command spans.

Across these eight current natural rows, initial command/pre-Accept/presentation maxima are 36.096/34.182/3.173 ms; main tail installation reaches 2.063 ms. Current post-head Render/Update/interval maxima are 6.467/10.483/50.316 ms **within this first-pose experiment only**. Worker elapsed and all slower/post-head neighborhoods remain in `Performance_Analysis.json`; induced waits are correctness controls excluded from natural performance maxima.

## Wider Android controls and remaining stall

The power-fall rerun passes 16 natural turns/4671 frames and 16 frozen sampler pairs. Prepared late windows have zero demand sprite/geometry creation versus 123 of each in skipped controls; all 1838 post-preparation falling frames have zero demand. The maximum preparation batch is 1.224 ms. These resource facts do not certify frame pacing.

The execution rerun passes eight natural turns/3204 frames, 64 model pairs, 64 resource pairs and 32 frozen Render pairs against their explicit same-APK controls. All slower samples remain. Fifteen model pairs, 16 initial-resource pairs and one complete-resource pair are slower. All four frozen submission medians are lower, with 10 of 32 individual current pairs slower. This repeats the earlier targeted helpers; it does not isolate Snapshot79's contribution or settle the historical L4 regression. Native and Android raw serialized hashes remain separate domains.

All nine ordinary Android stages pass: Fluidity, eight actual native gesture cases, measured/recorded cascades, four obstacle-density families and full campaign regression. Three additional L14/L31/L33 recordings also pass. Campaign coverage is 50 boards, 1716 checks, 14105 labels, 408 actions and 354 clips. Life refill spends 900 coins and fills five lives, repeated callbacks charge once, and confirmed decline spends one life/no coins. Nine stage audits and the three control audits retain exact real QA2 save/preference hashes.

**Smoothness remains open.** Prepared power-fall row `crate_1_0_prepared` retains a 366.029 ms interval at frame 1378 following a 359.614 ms Update at 1377, with only 3.423 ms Render. Approximately 356 ms precedes Render during a later powerFall handoff. The worker tail was already installed before the earlier powerFall; recorded preparation finished at 1221. Probe callbacks/hash/serialization are outside this frame. No demand creations/misses or completed GC collection are recorded in that bracket. These facts do not identify an exclusive cause or exclude incremental GC/native/driver/host scheduling time. Next/feedback/audio/history/readiness/pointer/native spans need separate instrumentation; no speculative production fix is applied.

Detailed ordinary density Render still reaches 29.441 ms, and prepared power-fall Render 33.879 ms in a different observer mode. Their differing cadences and VM history are retained; neither is substituted for the first-pose maxima or claimed as a cross-instance speedup. `Android_Metrics_Review.json` preserves the outlier neighborhood and separate gates.

## Actual sampled visual review and evidence contracts

Independent reviewers actually opened all eight fresh timing sheets and four selected full timing originals, all eight touch sheets and 16 selected full touch images, and all 14 campaign sheets plus listed full originals. The parent additionally opened normal startup, MixedChain's overview and the two full stone-refill frames. Exact inspected files/scopes/hashes are in the three visual notes and `Visual_Review.json`.

Samples show intermediate swaps, source-power flights, retained earned Rockets, separate refill/debris, reachable cells filling beneath retained stones, the 900-coin refill UI, Continue/reward/Home/celebration/finale states and contained portrait startup. The matching pre-existing sealed moss pocket in current and archived 78 L1 stills is recorded with its preserved fixed-corner/source rule. No new sampled visual discrepancy is identified. Thumbnail contributions are not claims of every original being opened; sparse PTS samples do not establish exact contact endpoints or universal smoothness.

Original-PTS extraction retains 461 source frames from four timing movies and 143 selected source frames from four touch movies without CFR interpolation. All presentation tools label sheets as awaiting actual review. Sixty-two Python corrupted-copy controls reject all 62 counterexamples while preserving the actual report bytes; 13 mocked QA target/attempt guards also pass. These are evidence-contract checks and are excluded from native/device check counts.

The strict collector validates final source/process/build/APK/raw control/save/review bindings before explicit publication. Its initial read-only precheck correctly stopped while actual `Visual_Review.json` was pending; it did not approve an unreviewed checkpoint.

## Remaining priorities

1. Instrument the later phase-handoff/feedback/native boundary responsible for the unresolved observed stall, preserving same-APK controls and all outliers.
2. Reduce dense sampling/drawing and synchronous model work without changing effects, masks or event ownership.
3. Test cold first use, long sessions/memory pressure and physical Android devices; broaden continuation only with deterministic pose/model proof.
4. Obtain a fresh playable reference session. Current reference evidence is archived; exact Match Villains parity is not newly established.

The current APK is installed only on the new isolated QA2. Original active QA1 remains 78 and main remains 64. No production backend/store/social, physical-device, allocation-elimination, sustained 60 fps or whole-project completion claim is made.

# QA, performance and release plan

## Evidence available
The recovered M67R4 validation records cover source/asset consistency and headless behavior, including 900,622 rig checks over 482 regular/reduced-motion samples, zero shoulder-root drift in those samples and non-inverted mesh triangles. Prior flow tests use fake Unity hosts. The current handoff independently inventories the 4,218 Unity files and statically validates 50 level masks/footprints, target-type ranges and source mappings.

These checks do **not** establish Unity API compilation, actual shader output, touch behavior, mobile frame rate, native store billing, level win rates or end-to-end release readiness. Keep that distinction in release notes and screenshots. Review videos are offline renders unless explicitly captured in Unity/device.

## Test matrix
| Risk | Required check | Acceptance |
| --- | --- | --- |
| Import/build | Clean Unity 2022.3.62f3 import, compile, Android/iOS development builds | No missing script/assets or unhandled runtime errors |
| Invalid actions | Invalid swaps, occupied footprints, canceled tool use | Exact state/stock/moves preserved |
| Power pairs | Each of 14 pairs; both orientations/orders; near edges and holes | Model contacts and approved presentation agree; no duplicate damage |
| Seekers | Zero/one/many valid targets; jars excluded; shared owners | Correct child count and no invented hit or multiplied owner damage |
| Obstacles | Every HP state, crystal5–9, cabinet2×2, pod delivery | Goal counts track logical units once |
| Resolution | Last-move win, cascades, no legal moves, guard exhaustion | Correct outcome; diagnostic faults distinct from player failure |
| Inventory | Grant failure, cancel, restart, repeated callback, crash | Exactly-once debit; no free reset or double consume |
| Save | Force quit at each commit boundary, corrupt/truncated file, migration | Recover valid state; no duplicate reward or silent progress reset |
| Retry/lives | Confirm/cancel exit, out-of-moves, zero lives, reload | One consistent, explicitly approved life policy |
| Victory | Ordinary first-clear, replay, L50 first-clear/replay, skip, reduced motion | Correct reward once; no modal; correct chapter ending route |
| UI/locales | Safe areas, 2/3/4 goals, long text, all five locales | No clipping, missing glyphs or obscured input |
| Commerce | Sandbox success/failure/deferred/duplicate/offline/refund/restore | Ledger equals verified entitlements and displayed balance |
| Social | Offline/empty/loading/paging/report/block/spam/account switch | No data leakage, demo leakage or duplicate life claim |

## Performance work
The raster inventory sums about 3.17 GiB of hypothetical RGBA32 base texels across every image, including duplicates and review assets. This is **not measured memory or simultaneous residency**. The earlier M46 effect-atlas subset alone estimated roughly 1,023.5 MiB uncompressed. Selective loading and mobile compression need deliberate verification.

Profile cold launch, level load, multi-power chains, broad obstacle destruction, full-screen debris, Orb conversion and Daria overlay. Record peak resident memory, GPU texture memory where available, draw calls, frame-time distribution, GC allocations, thermal behavior, battery impact and pause/resume. Target 60 fps on supported devices with a planned lower-tier policy if required; agree actual budgets after measurements. A nominal 16.7 ms budget leaves no license to hide hitching behind average fps.

Use existing resource mappings and lazy atlas caching as a starting point. Check unused review assets and duplicates; do not delete them before tracing GUID/resource references. Compression presets must preserve alpha, small highlights and text. Compare ASTC output against approved textures on supported GPUs. Reduce allocation and pool renderers/effects before sacrificing approved animation fidelity. Dispose transient resources and test repeated level loads for growth.

## Release gates
Gate A — Reproducible baseline: clean import/build, source-controlled settings, all current connected flows reviewed.
Gate B — Reliability: durable profile, unified attempt outcome, inventory/life recovery, no critical known progression defects.
Gate C — Content: human playtests for 50 levels, difficulty pacing, localization and final art QA; Chapter 2 supply decision if players can exhaust content.
Gate D — Commerce: verified sandbox transactions/recovery, store products/localized prices, real support/legal links, privacy disclosures.
Gate E — Soft launch: telemetry reconciliation, crash/performance dashboards, controlled cohorts and experiment holdouts; marketing spend capped by observed cohort contribution.
Gate F — Broader launch: repeatable content/operations cadence and positive economics under measured uncertainty. No numeric retention benchmark is certified by this handoff.

## Defect report template
Record build/commit, Unity/device/OS, locale, level ID/data hash/seed, attempt ID, steps, expected/actual result, video and logs. For design defects include identical-size approved/current frames and color-space/import settings. For economy defects include redacted transaction/attempt IDs and before/after stock, not raw payment tokens. Assign owner, severity, acceptance and retest build.

# Physical phone review — checkpoint87 evidence, unchanged source86

26 October 2026. The owner connected a real phone and requested all-checklist testing. This review installs and tests the accepted source86 development APK on that phone. No Unity/backend runtime, approved art, GUID, level mask, gameplay schedule, SDK or engine changed. Docs00/01 and doc65's corrections remain preserved.

**Result: scoped physical checks completed with open failures and release gates.** The39-row checklist has2 PASS,21 PARTIAL,1 FAIL,2 NOT_RUN,7 BLOCKED_ENVIRONMENT and6 BLOCKED_EXTERNAL rows. Each aggregate row includes its incomplete variants; the many individual fixture/ordinary passes do not certify every variant of a broad row. This is not release approval or whole-game smoothness acceptance.

Open the [native evidence dashboard](../../Verification/Evidence/Physical87/20261026_e71bc9d09515/Comparison.html), [all39 rows](../../Verification/Evidence/Physical87/20261026_e71bc9d09515/Checklist.json), [ordinary observations](../../Verification/Evidence/Physical87/20261026_e71bc9d09515/OrdinarySummary.json) and [performance analysis](../../Verification/Evidence/Physical87/20261026_e71bc9d09515/Probes/PerformanceAnalysis.json). Immutable Review86 and its two failed Windows clipboard suites remain distinct.

## Device and build

| Item | Actual target |
| --- | --- |
| Physical device | realme RMX3938, ARM64, Android16/API36 |
| Display / renderer |720×1600, density320; Vulkan / Mali-G57 |
| Package / version |`com.heartoftherain.verification`,1.0/code1, internal development build |
| APK |`Unity/Builds/Verification/HeartOfTheRain_Development.apk` |
| APK SHA256 |`be4b1a1c0641adb97bc279b5f009e21630dc8fc30b802986590cc7a38a10ac68` |
| Frozen source |5,373 Unity inputs; manifest SHA256`2994d45407a8f8c3126813affee9530c4acb1ac12968f5f817d3a8296a13acbe` |

The package and its persistent directory were absent before installation. Every ADB operation explicitly selected the authorized USB phone; there was no emulator fallback, uninstall or data clear. The public evidence contains a serial hash; its raw selector stays in the ignored local cache. No unrelated apps, notifications, contacts or personal files were captured. Phone clock, resolution, density, audio volume, network and other system settings were unchanged. The existing USB stay-awake value was observed, not changed. No backend configuration, ADB reverse or provider service was activated.

The internal APK still has minimumAPI22/target36 and a development signer. The agreed production baseline26, production signing/package configuration, configured SDK/device acceptance and existing RuStore gates remain. No eligible Unity splash-removal entitlement was available; no bypass or engine upgrade is included.

## Executed checks

**Transient physical native regression:**1,716 assertions,50 boards,408 programmatic actions,354 rendered animation clips and14,365 generated labels pass. The native report exercises tools, obstacles, stacked refill, approved power combinations/chains,900-coin refill boundaries, attempts and seeded win/finale routes. These use isolated memory state and accelerated playback. They are neither human50-level wins nor ordinary durable account/service acceptance. M70 textures use actual ASTC support on the Mali device; texture format/load-copy evidence is retained.

**Continue/Shop:** all12 isolated native cases pass. Real Android taps/swipes cover affordable and insufficient offers, Shop/back/scroll, prepared/committed state, repeat purchases, repeat-insufficient, abandonment and zero/below/exact balances. Selected actual OS captures confirm centered Continue, wallet/offer-card placement and contained scrolling/footer. The profile is isolated memory; automatic prepared/committed cases do not establish Android process-death recovery of the ordinary file-backed game.

**Nine performance suites:** Fluidity, PowerFall, crate/stone/gate/tile-control density, FirstPose, Execution and command-construction comparison finish with their expected fixture statuses. Raw samples and worse branches are retained. No screen recording, screenshot readback, graphics dump or memory/thermal query runs inside the timed fixtures; bounded stat polling still adds observer overhead. Native draw/mesh witnesses are not GPU-completion measurements. Ordinary profile/preferences hashes remain unchanged through these isolated suites. A subsequent ordinary Home capture confirms the fresh starting profile is still intact.

**Ordinary phone UI and durable state:**

- Russian portrait prologue/chapter/practice appear without seeded campaign progress. Practice is completed using two taps where the swipe fails; see the retained failure below.
- Music, sound and hints persist Off through background/resume and relaunch, then are restored On. The owner separately answered **“Music sounds normal.”** This listening result does not certify every sound effect or all source-overlap transitions.
- Save progress opens the guest/local-only panel and closing returns to Settings. Russian is first in the language menu. Profile avatar/frame changes persist across relaunch; original Ivan/gold appearance is restored. Selected profile banners/stats/frame-scroll, rewards and safe-area screens are inspected.
- Development Daily Gift Day1 adds50 coins once and reopens as collected after restart. Wellworks/Cup locked states are inspected; the ordinary first clear advances Home's first-clear counters to1/10. Later milestones/event joining/finishing/claims remain outside this ordinary run.
- Ranks/Teams identify demo/local data; no real friend request or message is sent. Shop displays all six RUB preview prices199/699/1299/2699/4999/8999. It labels preview prices; these are not Console products. The400-coin optional video panel states UTC+10,three rewards/day and10-minute cooldown and truthfully remains unavailable.
- Play shows the approved sapphire/raindrop/Seeker loading presentation, then the ready board. Capture times include observer overhead and do not establish exact gameplay-ready latency.
- A normal gameplay swipe succeeds, producing cascades and new powers. Hammer selection/cancellation does not spend stock; accepted use debits once. A natural Level1 first clear through actual inputs credits50 coins/1star, shows Dariya and returnsHome without a next-level modal. Normal restart retains that reward and all stock.
- A selected Rocket is debited on accepted Level2 start, retained as spent through a confirmed quit/restart, and not replenished on retry. Confirmed quit costs one life. A later deliberately interrupted new retry eventually costs one more life once; the early failed observation and late follow-up are both retained.
- Exact same development APK `install -r` replacement preserves the complete ordinary profile/preferences hashes and returns to an inspected Home. Development-v1 and non-development Player-v1 are separate stores; ReleaseCompile was not installed or presented as progress migration. Real release/schema/pending-purchase upgrades remain unverified.

Before the naturally timed refill, the recorded fresh test profile is Level2,one completed level,1,350 coins,one star,three lives, starting inventory4/5/3/2 and tools2/3/3/3. Its attempts are Won/Lost/Interrupted, with no active attempt or pending probe marker. The100-coin net increase is50 gift plus50 first clear. One Hammer and one starting Rocket were consumed; one confirmed and one interrupted loss were intentional tests. A later natural30-minute refill adds exactly one life-credit receipt and changes3 to4 lives, with the next countdown and no clock change. The brief+1 animation was not captured. No real purchase, ad reward or owner account was used. The app remains installed and usable at Home.

## Findings retained

1. **Tutorial swipe failure.** Highlighted Rocket-lesson vertical swipes remain unaccepted, including a600ms swipe after stage restart. Two taps succeed. The ordinary gameplay180ms swipe succeeds. Input/focus/scroll/coordinate handling needs instrumented reproduction; a particular source cause is not established. No speculative runtime patch was made. Some early capture names describe intended steps: `07_Tutorial_Rocket_Created.png` and `08_Tutorial_Clear_Before.png` actually show the still-unsolved Rocket lesson. [VisualReview.json](../../Verification/Evidence/Physical87/20261026_e71bc9d09515/VisualReview.json) records these corrections.

2. **Residual burst stalls.** Idle p95 is16.74ms in481 sampled frames, but Orb+Rocket reaches66.684ms with five intervals over50ms. Prepared PowerFall rows still reach approximately83–100ms. Increasing crates1→45 raises sampled Render CPU p95 from4.25→6.67ms; stone3.92→7.10ms. Tile-only controls also retain roughly100ms intervals, so obstacle count is not an exclusive cause. Current natural FirstPose command returns6.53–16.52ms, with separate asynchronous metadata wait24.4–40.51ms. The783ms worst sample belongs to an intentionally skipped-preparation control; the two held-worker controls are also excluded from ordinary-current timing. Update/Render metrics are nested and are not added together. CPU spans alone do not attribute the residual to GPU, driver, OS, GC or scheduling.

3. **Early restart observation fails before recovery finishes.** `Interruption/Invocation.json` retains FAIL: after the seven-second postlaunch wait its profile observation still sees Started. The profile modification later occurs at13:40:36UTC; late inspection sees the correct Interrupted receipt and one life charged. A separate15-second normal-relaunch observation returns to actualHome with identical saved files and no second debit. No initial report was overwritten or assertion waived. This establishes eventual single settlement for this attempt, while exact startup-ready latency and phase attribution remain open. An early normal-relaunch capture also shows launch artwork rather thanHome. Android activity launch time is not app-ready time.

4. **Memory/device coverage.** Outside-fixture app PSS ranges561,191–974,932KiB and Graphics350,192–603,756KiB across different processes/scenes. This is substantial; it does not prove a leak or a measured peak. Coarse thermal status is0 before/after every probe, which does not provide continuous thermals or exclusive stall attribution. App-scoped logcat also retains Mali allocator R8/RGBA_10101010 format-support errors and a deprecated ashmem message across multiple starts (`NativeLogWarnings.json`). Zero selected fatal/managed-exception signatures does not mean error-free platform logcat. These messages do not establish a failed gameplay draw or the stall cause. One phone does not close low-memory devices, Android8, tablets, every cutout/aspect ratio, sustained sessions or true multi-contact input. No fresh Match Villains physical session was compared in this run; earlier reference comparisons remain archived evidence.

5. **Offscreen capture caveat.** Some regression finale/footer PNGs clip at the bottom. That capture reuses the gameplay camera's reduced safe-area viewport while converting overlay canvases to camera space; Chapter Celebration also applies safe area. Its ordinary layout algebra is contained. These PNGs alone do not prove an on-screen defect. Actual ordinary victory, Home and controls are inspected separately; an actual OS L50 finale frame is still required.

## Remaining execution plan

| Priority | Work / acceptance |
| --- | --- |
| P0 input | Instrument pointer ownership, start/end coordinates, focus/layout and cancellation in an isolated tutorial build; reproduce the failing gesture and verify both swipe and tap paths without changing authored practice rules. |
| P0 connected release | Supply owned HTTPS/backend configuration or a separate development-only loopback build. Run actual ordinary managed account/recovery/deletion, friends, DM/team chat, moderation/records/rankings with synthetic accounts. Current APK disallows cleartext; no phone-wide CA or TLS bypass is appropriate. |
| P0 purchases/ads | Resolve the pinned-engine/vendor SDK compatibility gate, build the configured Android SDK profile, supply Console/application/product/unit IDs and backend/signing configuration, then execute actual sandbox success/cancel/interruption/duplicate/bank-return/fulfilment and video-reward cases. Current APK is SDK-free; IDs alone do not close the engineering gap. |
| P1 smoothness | Capture app-scoped main/render/worker/GPU-present/resource traces for the retained slow prepared rows and tile-only controls; separate cache/texture lifetime, phase handoff and command work before changing code. Recheck exact semantics, poses and worse samples. |
| P1 startup | Measure first app-ready/recovery milestones rather than fixed waits or Android activity start. Keep the retained early failure; bound cold/warm/after-loss startup and resource preparation separately. |
| P1 durable acceptance | Use disposable file-backed test profiles for exact celebration/Continue/purchase termination cuts, corruption/truncation/commit/migration, genuine signed-version upgrades, all eight ordinary item types and full reward/event variants. Never corrupt the ordinary owner profile. |
| P1 campaign/layout | Human50-level session records, true multitouch, complete locale/popup review and additional physical API/device/tablet/low-memory coverage. Programmed board actions cannot populate the human campaign worksheet. |

Account/social rows are blocked by test transport/configuration; payment/ad rows additionally require configured Android engineering and provider/operator setup. These are not inferred as working because pages render. Support/privacy/legal/moderation operations, production signer/hosting/storage and real-payment acceptance remain in the release checklist. Nothing was publicly deployed.

## Evidence and reproducibility

`Verification/Tools/Physical87/` contains explicit physical selection, ordinary actions, audited opt-in marker runners, the retained early interruption observation and separate follow-up, safe same-bytes replacement and a host-only publisher/verifier. The historical emulator guard remains unchanged. `collect_results.py` validates the optional Physical87 supplement without replacing Review86's failed suites or status.

All structured/raw timing reports, failure records, logs and selected original captures are retained. Full offscreen regression PNGs remain local under the existing repository retention policy; their sizes/hashes and retention classes are in `ArtifactInventory.json`. No raw image is deleted or retouched. Retained files are required by the verifier; missing optional raw files in a fresh clone are explicitly unverified.

Run the host-only evidence check with:

```powershell
.\.venv\Scripts\python.exe -B Verification/Tools/Physical87/report.py --out Verification/Evidence/Physical87/20261026_e71bc9d09515 --verify --require-raw
```

This rehashes evidence and available held Unity inputs/APK. It does not repeat device execution, waive failures or approve launch. Native/player reports, actual Android input observations and source-only audits retain their distinct scopes.

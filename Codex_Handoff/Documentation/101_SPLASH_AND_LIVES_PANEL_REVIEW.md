# 101 - Startup icon continuity and the Lives panel

**REVIEWED_WITH_OPEN_ACCEPTANCE_GATES.** Startup XML/art checks, final local Lives behavior/layout
checks, selected native visual review and focused managed HTTP refill tests pass
in their recorded scopes. The first Android build/static checks pass, but its
physical startup still flashes blank frames. A Java-only readiness experiment
stalled Unity initialization and was rejected; exact working Java is restored.
Defined Lives/Level phone cases and final ordinary preservation are reviewed; the brief startup flash remains open.
`fullyVetted=false`, `taskComplete=false`, `productionApproved=false`.

The main project remains Unity **2022.3.62f3**. The already approved isolated
Unity **6000.3.27f1** copy is the Android test path; this checkpoint does not
promote the main engine or upgrade an SDK. The working checkpoint 101 **Dev01**
candidate is built/static-checked and selected again after the failed experiment.
Its duplicate-size correction works in the recorded cases; a brief handoff
flash remains open, so it is not a complete seamless-startup acceptance.
It is 319,164,540 bytes with SHA256
`b74b4f419c7754c72f2b534f191537c78f6b53f0c968aed9cf27ee8df9134030`.
The Java-only **Dev02** experiment was also built/static-checked at 319,164,540
bytes, SHA256 `e959e320752be7120c93de080f8dc6929583da41108d244845a31cf99d5cd7fe`.
It is rejected for a real startup dependency failure and is not the final app.
The baseline phone observations below use the accepted checkpoint 100 candidate,
SHA256 `a476d2a36fa52d72aa9289bab4b40a099f49ccde4030a6f4d71e93a47c361aea`.

[Evidence gallery](../../Verification/Evidence/Review101/Comparison.html),
[checkpoint summary](../../Verification/Evidence/Review101/Summary.json),
[individual native source epochs](../../Verification/Evidence/Review101/NativeCoverage101.json),
[bounded preparation plan](../../Verification/Evidence/Review101/PreparationPlan101.json),
[actual launch-state classification](../../Verification/Evidence/Review101/BaselineLaunchClassification101.json).

## Requested behavior and interpretation

The owner reported two app icons at different sizes before the loading artwork,
and reported that tapping the Home heart opens the level-start modal.

For the heart, the earlier explicit heart-to-level-preview request is historical.
The latest report is being handled under the root agent's stated working
assumption: the heart should open a dedicated **Lives** information/refill panel,
while the explicit Level button retains the normal level-start preview. This is
an implementation interpretation after an optional preference request, not a
fabricated explicit new design choice from the owner. The component remains
available for design review.

The Lives panel uses existing approved artwork and shows the current count,
Full or next-life state, and the existing **900-coin full refill at zero lives**.
It does not offer a paid partial refill, reserve a level, select boosters or start
gameplay. Zero lives with 899 coins still shows the 900-coin offer and an
insufficient-balance message; the purchase control is unavailable. No economy,
regeneration interval, inventory quantity, level mask or gameplay rule changes.

## Startup diagnosis and implementation

The duplicate is produced by independent native icon paths. Android 12+ first
displays the framework splash icon. The old activity theme retained a separate
**192dp bitmap window background**, and `LaunchCurtain99` installed its own
**192dp ImageView**, with independent sizing and oval clipping. The larger
app-managed presentation therefore followed the system icon instead of preserving
one continuous splash. The correction removes both modern app-managed icon paths.

Root reviewed the accepted checkpoint 100 `BaselineCold02` chronological images. They show
the smaller system icon followed by the larger custom icon, and one intervening
plain dark frame 53 before the first loading artwork at frame 54. These are
recorded-frame classifications, not a universal startup duration, Android TTID
or claim of evicted disk caches. Successor recordings must inspect the complete
handoff for both the size switch and an uncovered frame.

Android's [splash-screen guide](https://developer.android.com/develop/ui/views/launch/splash-screen)
describes the system splash on cold/warm starts and the exit-animation listener.
The [SplashScreenView API](https://developer.android.com/reference/android/window/SplashScreenView#remove())
provides explicit removal of the transferred view. The first checkpoint 101
build, **Dev01**, used that existing platform view rather than a second image:

- **API 31+:** install the exit listener after Unity's content setup, retain the
  actual framework `SplashScreenView`, and remove it after the existing real
  first-logo-frame signal. The underlying activity window is plain black, so
  it cannot expose another themed icon. There is no fixed dwell, GPU timing
  guess, new Activity or AndroidX dependency.
- **API 26-30:** reuse the exact generated starting-window drawable for the
  legacy cover, including its existing 192dp geometry. There is no independent
  image resizing or extra clipping pass.
- The current Activity owner is a volatile weak reference. Ready-before-exit
  and exit-before-ready ordering are handled; identity-guarded cleanup avoids
  removing a replacement Activity's view. View mutations remain on the UI thread.
- The existing provider/resource licensing gate is unchanged. It is enabled
  only when the supported PlayerSettings disable both splash and Unity logo.
  Required Unity 2022 branding is not covered or bypassed.

Original PNG bytes, existing asset GUIDs, launcher artwork/insets, `LaunchPage`,
the C# first-frame bridge and first-time/returning-player routing are preserved.
Dev01 compiled the retained-view path, but source/XML and compilation checks do
not certify a seamless physical handoff.

Read-only APK provenance initially sampled the unchanged primary Unity DEX,
which did not contain the application splash class. Inspecting all DEX entries
resolves that scope question: `classes4.dex` contains the actual framework exit
listener, `SplashScreenView` and retained-view log marker. The corrected
[provenance report](../../Verification/Evidence/Review101/ArtifactProvenance101.json)
records the distinct Java entry. This is a read-only provenance clarification,
not a stale-build defect or an additional code fix.

Actual root review of **Dev01 CandidateCold01** shows one constant-size icon,
but grey decoded frame 44 (PTS 3.546), grey frame 64 (5.328) and black frame 65
(5.350) precede first logo frame 66 (5.364). A second cold control repeats the
flash: icon through frame 50 (3.491), grey frames 51/52 (4.540/4.561), then logo
53 (4.571). Direct decoding independently confirms the blank pixels. These are
positions within the preserved recordings, not app-start durations or TTID.
The native stages prove the retained-view callback/signal/removal path ran;
they do not prove composited pixels. Dev01 is not accepted as a completed
startup fix, and both recordings remain retained.

The rejected **Java-only Dev02 experiment** replaced the API 31+ transferred-view
hold with a readiness `OnPreDrawListener` on Unity's existing content root. It
keeps the original system starting window until the existing real `logoReady`
signal. The callback returns immediately: false while unready, then unregisters
and permits drawing. Ready invalidates the content root; owner-specific cleanup,
weak Activity identity, changed-root matching and ready-before-install handling
prevent a stale listener from controlling a replacement Activity. There is no
timer, extra dwell, GPU wait, new Activity, AndroidX dependency, C# change or
legacy-API change. Frozen Java SHA256:
`958f72069f27ac8b2c7645c9f5262f7d6f2072ba4c145cece8fbcb8bba9fbffa`.

The official guide documents delaying the initial draw with an
[OnPreDrawListener](https://developer.android.com/reference/android/view/ViewTreeObserver.OnPreDrawListener).
The AOSP [SurfaceView implementation](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/core/java/android/view/SurfaceView.java)
updates its surface during its own pre-draw callback; [ViewTreeObserver](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/core/java/android/view/ViewTreeObserver.java)
dispatches all listeners before combining draw cancellation. **Inference:** the
readiness predicate does not inherently suppress SurfaceView creation callbacks.
That is not proof that Unity's native render/window synchronization is free of
a dependency cycle. Actual [Dev02Cold01](../../Verification/Evidence/Review101/Phone/Dev02Cold01/Report.json)
failed: only gate-installed/waiting stages appeared, with no managed-before-splash,
logo or Home signal during the 25-second observation. The system icon remained
visible. ActivityManager reported **UNKNOWN (-1)**, not a successful COLD start;
profile/preferences and original-owner absence were preserved. This rejects
the whole-root pre-draw hold for this Unity/device path, despite successful
compilation and the valid general Android guidance.

The exact working retained-view Java was restored by checked reverse patch,
SHA256 `1de78774460c27255e52ce87efd24d05c8398ad6d23353564d9d2ff9131c8222`.
The phone was returned to the b74 Dev01 candidate by guarded
[RestoreWorking01](../../Verification/Evidence/Review101/Phone/RestoreWorking01/Report.json).
No timer, GPU wait,
additional image or C# workaround was added. The original duplicate-size switch
is absent in both Dev01 recordings, but its brief grey/black handoff flash
remains explicitly unresolved. Dev02's failed invocation/video remain retained.

## Lives routing and transaction boundaries

The existing pre-level shell now has a distinct `livesOnly` view. The header
heart opens that view; the Level route continues to open goals, starting-item
selection and Play. Lives-only mode rejects hidden Play/toggle commands in both
the controller and session. Opening it skips gameplay-loading artwork preparation.
Closing it returns to Home without an attempt or life-loss settlement.

The service/model retains refill authority and durable idempotency. The UI's
refill ticket locks repeated actions while a request is unresolved, and only a
matching ticket can unlock its view. A committed refill followed by a projection
failure retries the projection read rather than starting another purchase.
Natural regeneration is refreshed while a partial/empty Lives panel is open;
if a life becomes due at the refill tap, existing model rules prevent a charge.

Independent source review found a concrete renewal regression in the first
server handler: it captured `SessionGeneration` before refill. An ordinary
expired-access refresh increments that value for the same player, so a valid
callback could be discarded and leave the sheet busy after a real refill.
The repair uses a separate player-ownership epoch, origin and stable player ID.
Credential renewal retains that ownership; account changes/recovery/disposal
invalidate it. The refill ticket and view-reference fences remain in place.
The focused real managed-session HTTP test now passes 40 assertions: actual
access renewal moves generation 1 to 2 while ownership stays 0, the refill
unlocks, and real logout/recovery ABA, fresh-player and component-destruction
transitions invalidate old ownership. Backend financial service/schema/config
code is not changed for this UI ownership fix.

The source now guards a not-ready server before taking a refill ticket and
refreshes the actual server wallet when a natural life becomes due
with the sheet open. A projection-only read cannot credit that server life, and
the ordinary idle-Home refresh is gated while this modal is open. Final timer/read
ownership behavior passes the focused native/HTTP fixture. A separate fresh
guest moves from 3 to 4 lives while the sheet stays open; the SQLite audit records
one natural-life receipt, no coin debit and no attempt. These are actual local
HTTP/Editor cases with controlled private operator seeds, ephemeral Editor keys
and synthetic local access expiry; they do not certify a phone or hosted service.

The first completed Lives run also exposed a visual correction during root's
actual review of the Russian phone-sized captures: the Full/countdown row
straddles the approved shell's cream/footer seam. A positive-life-only layout
adjustment is now verified in its native scope: the original 80px heart stays intact
at y=60..140, the count occupies y=142..171, the status y=174..198 and the clock
y=177..194. Those elements remain above the conservative cream boundary y=200;
the unchanged shell's fixed footer begins at y=210. Positive-life feedback uses
white text in the blue footer. The 338px zero-life shell, 900-coin control and
zero-life geometry are unchanged. Root accepted the existing zero-899 and
zero-900 captures. Root then actually viewed the final Full/partial Russian
393x852 and 768x1024 captures individually and accepted the clear cream margin
and separation. Final `LivesMain04` passes 1,539 checks, 75 layouts and 4 state
cases; actual world-corner assertions preserve strict 2px separation and keep
the dark status/count and clock inside the cream region. This closes the native
seam gate; it is not a physical-device or all-locale human visual acceptance.

Selected working-b74 phone views now also pass root's actual visual review:
ordinary full Lives and the original explicit Level preview before the
experiment, then partial 3/5, zero lives with 899 coins and the completed 900-coin
refill after restoration. The three balance cases use an explicitly disposable
development memory profile: 14/16/17 fixture checks respectively; the paid case
ends at 0 coins/5 lives with one receipt, no attempt and no inventory change.
No ordinary saved balance is spent by these fixtures.

The memory probe freezes its authoritative clock at 1000. Its modal can therefore
show 30:00 while the header presentation ticks to 29:58. Those images certify
layout/input and the scoped refill model, **not continuous device-clock or
natural-regeneration behavior**. Timer proof remains separately scoped to the
native clock-advance cases and real managed HTTP due-read. Root also accepted
the final ordinary saved Home image after all memory cases: 1,250 coins, 5 lives,
Level 1 and full-screen presentation. Final ordinary-route repetition closed with byte-identical accepted Full/Level/Home images.

The healthy heart and countdown clock come from existing `HomeLivesAssets`.
The broken-heart retry artwork remains unchanged. Approved artwork, palette,
metadata and the original level-start/retry behavior are retained.

## Changed-file map

| Area | Primary files | Behavior |
| --- | --- | --- |
| Native startup | `App/Launch/Editor/AndroidLaunch99.cs`; `App/Launch/Plugins/Android/HeartRainLaunch99.androidlib/src/main/java/com/heartoftherain/launch99/LaunchCurtain99.java` | Black modern activity background and working retained platform splash restored exactly after rejected readiness experiment; exact legacy drawable and owner cleanup retained; brief flash open |
| Startup checks | `Verification/Editor/Startup99Verification.cs` | Generated Android XML/art/layout assertions; existing licensing and artwork checks remain |
| Lives session and layout | `App/PreLevel/Runtime/PreLevelSession.cs`, `PreLevelLayout.cs` | Separate Lives view, hidden-start/toggle barriers, refill presentation ticket and compact positive-life information geometry |
| Existing art lookup | `App/PreLevel/Runtime/PreLevelAssets.cs` | Resolve healthy heart and clock from existing approved `HomeLivesAssets`; retain broken retry art |
| Home route and timer | `App/PreLevel/Runtime/HomeLevelFlow.cs`; `App/Home/Runtime/HomeLayoutEngine.cs` | Heart opens Lives, explicit Level/retry retains level preview, local due-state refresh and localized header accessibility action |
| Managed refill ownership | `App/ServerGameplay/Runtime/HomeServerLevelFlow.cs`, `ServerGameSession.cs`; `App/ServerAccount/Runtime/ServerGameAccountOperations.cs` | Stable player epoch across access renewal, account-transition invalidation, not-ready preflight, actual authoritative due-life reads and stale UI rejection |
| Editor verification | New `Verification/Editor/Lives101Verification.cs`, copied `Verification/Editor/Refill101HttpVerification.cs` and their `.meta` files; existing `Verification/Review98DeviceProbe.cs` | Strict actual UGUI hit/command barriers, state/financial/timer fixture, controlled actual managed HTTP fixture and bounded physical-test probe support |
| External HTTP/build preparation | `Verification/Tools/Review101/Refill101HttpVerification.cs` and runners in that tools directory | Outside-Assets HTTP template and scoped runners; native owner retains and source-binds the Editor-only copy used by actual invocations |
| Documentation/evidence | This review and `Verification/Evidence/Review101/` | Source-bound receipts, retained failures and bounded acceptance status |

Unity paths in this table are relative to `Unity/Assets/HeartOfTheRain/`.
`Verification/Tools/Review101/` paths are relative to the repository root.
The existing `HomeLivesText` translations are reused, not changed in this checkpoint.
The map records the intended checkpoint 101 scope, not every older uncommitted project change.

[Final working source binding](../../Verification/Evidence/Review101/SourceDelta101_Final.json)
and [exact restoration](../../Verification/Evidence/Review101/RestoredWorkingSource101.json)
bind the restored main/private inputs to b74. The rejected Dev02 source delta
remains a separate historical receipt. HTTP40 predates the positive-life layout
correction; its financial ownership/due-read runtime was unchanged afterward.
No single identical source epoch is claimed across all suites.

Checkpoint 101 follows the existing 98-100 evidence policy: `.gitignore` excludes
raw native PNGs beneath `Verification/Evidence/Review101/Native/`. The captures
are retained locally, not deleted. The gallery publishes four selected reviewed
Full/partial copies with their [source receipt and hashes](../../Verification/Evidence/Review101/Reviewed/Selection101.json); generated contact sheets and launcher media
remain private. A locally retained capture is not acceptance by itself.

## Closed baseline evidence and pending acceptance

| Case | Closed observation | Limit |
| --- | --- | --- |
| BaselineCold01 | ActivityManager reports COLD on accepted checkpoint 100; original data preserved | First decoded frame was already the larger icon, so the early phase is incomplete |
| BaselineCold02 | COLD, with longer recorder pre-roll; root sees small icon, larger icon, dark53, logo54 | Baseline defect evidence only; no disk-cache eviction or startup-speed claim |
| Historical filename BaselineWarm01 | ActivityManager reports **HOT**, same process and Activity; data preserved | It is not a recreated-Activity warm launch |
| StartupMain01 | Native invocation fails compilation; no startup test executes | `CS0246`: verification fixture missing `ISettingsStore` namespace import |
| StartupMain02 | Native invocation fails compilation; no startup test executes | `CS0165`: verification fixture's `play` definite assignment |
| [StartupMain03](../../Verification/Evidence/Review101/Native/StartupMain03/Invocation.json) | **PASS**, 30 generated XML/art/layout assertions in actual Unity 2022.3.62f3; zero C# warnings/errors | No Java lifecycle, Android build, physical start, routing or performance claim |
| [LivesMain01](../../Verification/Evidence/Review101/Native/LivesMain01/Invocation.json) | **FAIL**, 1,409 checks and 75 layouts completed | Strict healthy-heart raycast failed in the later financial fixture; it seeded and tapped in the same frame. The fixture now waits for a subsequent actual UGUI frame; no assertion is waived. Root also found the status-row seam issue in captures |
| [LivesMain02](../../Verification/Evidence/Review101/Native/LivesMain02/Invocation.json) | **PASS**, 1,419 checks, 75 layouts and 4 state cases | Local fixture timing repaired; root visual acceptance still fails for the positive-life status/footer seam. This receipt precedes the pending layout fix |
| [LivesMain03](../../Verification/Evidence/Review101/Native/LivesMain03/Invocation.json) | **FAIL**, 21 checks before any layout capture | New geometry assertion treated a center-pivot fitted image's anchored position as its top edge. The final test compares actual world corners in panel space; strict 2px separation and cream-region checks remain. No runtime change is inferred from this fixture failure |
| [LivesMain04](../../Verification/Evidence/Review101/Native/LivesMain04/Invocation.json) | **PASS**, 1,539 checks, 75 layouts, 4 state cases and no geometry failures | Final positive-life layout; actual world-corner measurement, strict hit testing and unwaived separation/cream assertions. Root accepted four final Russian Full/partial phone/tablet images; zero-899/900 geometry is unchanged and previously reviewed |
| [RefillRenewal01](../../Verification/Evidence/Review101/Connected/RefillRenewal01/Report.json) | **PASS**, 40 native assertions plus closed HTTP/SQLite wrapper audit | Actual renewal/refill and account transitions; one -900/+5 receipt, one separate timer +1 receipt, zero attempts, ordinary profiles preserved and owned service listener closed. Predates final positive-only layout change; not Android/provider/production proof |
| Corrected dedicated Lives native visual layout | **PASS within selected scope** | Final Full/partial Russian phone/tablet captures accepted; not Android or every-language/device human visual proof |
| [GeneralMain01](../../Verification/Evidence/Review101/Native/GeneralMain01/Invocation.json) | **PASS**, 535 actual Unity 2022 native checks | Current general native suite, not an exhaustive human campaign or physical-device run |
| [LTSConfigure01](../../Verification/Evidence/Review101/Native/LTSConfigure01/Invocation.json) | **PASS**, 19 checks | Private Unity 6000.3.27f1 test configuration; no main project engine promotion |
| [LTSLives01](../../Verification/Evidence/Review101/Native/LTSLives01/Invocation.json) | **FAIL**, 0 behavior checks | Stock `UnityEditor.Search` first-use exception before a default Assets index existed; no app assertion executed |
| [LTSSearchPreparation01](../../Verification/Evidence/Review101/Native/LTSSearchPreparation01/Invocation.json) | **FAIL**, 3 preparation checks | Normal idle Editor generated its own defaults; the older observer's schema/hash expectations treated that first-use generation as a failure |
| [LTSSearchPreparation02](../../Verification/Evidence/Review101/Native/LTSSearchPreparation02/Invocation.json) | **PASS**, 3 preparation checks | Valid generated enabled Assets index; settings and PlayerSettings stable, zero captured errors; no Play, cache deletion, preference/vendor edit or exception filtering |
| [LTSLives02](../../Verification/Evidence/Review101/Native/LTSLives02/Invocation.json) | **PASS**, 1,539 checks, 75 layouts and 4 cases | Final state/layout fixture in the actual target Editor; root viewed Russian partial 393x852 and found it consistent with final main rendering |
| [LTSCore01](../../Verification/Evidence/Review101/Native/LTSCore01/Invocation.json) | **PASS**, 7,429 checks | Actual isolated target-engine core suite; source epoch individually bound |
| [LTSBuildDefault01](../../Verification/Evidence/Review101/Native/LTSBuildDefault01/Invocation.json) | **PASS**, 22 checks, zero BuildReport errors/warnings | Actual Unity 6000.3.27f1 Development ARM64/IL2CPP APK, SDK-free internal test signing, retained review98 package; not release signing or physical acceptance |
| [StaticApk101](../../Verification/Evidence/Review101/Native/LTSBuildDefault01/StaticApk101.json) | **PASS within static scope** | Signature, zip alignment, manifest, portrait, non-exported curtain, SDK-free manifest and ARM64/16KiB checks; does not certify compositor/lifecycle behavior |
| Dev01 CandidateCold01/02 root review | **Physical startup flash gate FAIL** | Duplicate-size switch is absent in these recordings, but actual grey/black frames repeat before logo. Mechanical data guards pass; these are not an accepted startup fix |
| [LTSBuildDefault02](../../Verification/Evidence/Review101/Native/LTSBuildDefault02/Invocation.json) and [Dev02 static](../../Verification/Evidence/Review101/Native/LTSBuildDefault02/StaticApk101.json) | **PASS native/static only**, 22 build checks, zero BuildReport errors/warnings | Java-only e959 experiment; subsequent physical startup fails, so this is not the final artifact |
| [Dev02Cold01](../../Verification/Evidence/Review101/Phone/Dev02Cold01/Report.json) | **FAIL: ready stage absent** | Only pre-draw installed/waiting, no managed initialization/Home; ActivityManager UNKNOWN. Data preserved. Rejected and exact working Java restored |
| [RestoreWorking01](../../Verification/Evidence/Review101/Phone/RestoreWorking01/Report.json) | **PASS within restoration scope** | Exact same-signed working b74 candidate restored with original source hash 1de; candidate profile/preferences and observed original-owner absence preserved. No flash-free claim |
| [Working89901](../../Verification/Evidence/Review101/Phone/Working89901/Report.json) | **FAIL/stopped**, 12 fixture checks | Development memory fixture could not read the verification step marker during concurrent host publication (`UnauthorizedAccessException`). The completed zero-balance tap verification did not run; original failure is retained. Host publication was repaired atomically in the successor, without app-source change or rebuild |
| [WorkingPartial01](../../Verification/Evidence/Review101/Phone/WorkingPartial01/Report.json) | **PASS**, 14 physical-fixture checks and selected root visual review | Disposable frozen-authority memory, 3/5; no purchase/attempt. Does not prove live continuous countdown |
| [Working89902](../../Verification/Evidence/Review101/Phone/Working89902/Report.json) | **PASS**, 16 physical-fixture checks and final-image visual review | Host marker publication made atomic; 0/5, visible disabled 900 offer, 899 coins preserved, no receipt/attempt. No app source/rebuild or assertion waiver |
| [Working90001](../../Verification/Evidence/Review101/Phone/Working90001/Report.json) | **PASS**, 17 physical-fixture checks and initial/final visual review | Actual refill tap, one 900 debit/receipt, 5 lives, duplicate-safe, no attempt/inventory change; disposable frozen-authority memory, not owner spending/backend/provider proof |
| [FinalWorkingHome01](../../Verification/Evidence/Review101/Phone/FinalWorkingHome01/Report.json) | End Home image root visual **PASS** | Ordinary saved 1,250 coins/5 lives/Level 1 after all memory cases; not flash-free startup proof. Final ordinary-route repeat is closed with byte-identical accepted images |
| Final ordinary route/preservation | **PASS within scope** | Fourteen recorded case states, including failures, preserve candidate data/owner absence; final data equals accepted 100. Constant-size startup observed, brief blank handoff OPEN |

The original compile failures remain preserved at
[StartupMain01](../../Verification/Evidence/Review101/Native/StartupMain01/Invocation.json)
and [StartupMain02](../../Verification/Evidence/Review101/Native/StartupMain02/Invocation.json).
The fixture import/assignment repairs do not waive any assertion. Their failure
is not reported as a passing startup test or an Android runtime defect.
The separate LivesMain01 failure and its original captures, LivesMain03's
geometry-measurement failure before capture, and the two target-Editor first-use
failures are also preserved. The Search cases are private Editor-environment
and observer preparation epochs, not a source fix for an Android app defect.
The successful observer reads Unity's generated defaults; no source cache,
Search preference, vendor file or runtime setting is manually rewritten.

The previous 500-test backend result belongs to checkpoint 100. It is historical
here and has not been rerun in checkpoint 101. Preserve every invocation's own source epoch;
do not relabel source checks, scripted callbacks or offscreen foreground
simulation as physical-device or configured-provider tests.

## Remaining gates

The defined Lives/Level, local refill and final preservation cases are reviewed. The
[14-case preservation chain](../../Verification/Evidence/Review101/PhonePreservation101.json)
binds the final working b74 APK and unchanged accepted-100 candidate data, including
failed experiments. The original owner package remains absent without reconstruction.
The brief recorded grey/black startup handoff remains open. A recreated-Activity
warm case is distinct from the recorded hot resume. API 26-30 behavior and other
OEM launchers remain separate device-matrix limits unless actually tested.

The selected physical phone disconnected after the preserved checkpoint 100
baseline captures. [PreUpgradePreflight01](../../Verification/Evidence/Review101/Phone/PreUpgradePreflight01/Report.json)
stopped on a read-only device-not-found result; [RosterPreflight01](../../Verification/Evidence/Review101/Phone/RosterPreflight01/Report.json)
found no attached devices. After the owner reconnected and unlocked it,
[ReconnectedPreflight01](../../Verification/Evidence/Review101/Phone/ReconnectedPreflight01/Report.json)
verified the original candidate 100, no active attempt, awake/unlocked state and
continued original-owner-package absence. The stopped checks remain preserved;
they are not evidence of successful launch or input. Successor physical cases
are closed in their stated scopes; the known brief startup flash is not accepted as gap-free.

No account/provider, real payment, advertising, hosted-backend, full campaign,
global performance or production acceptance is implied. Existing launch gates
and the prior 66.55ms diagnostic remain open. The actual
[working compiler audit](../../Verification/Evidence/Review101/CompilerWarnings101_Working.json)
binds b74 and records zero selected C# errors/warnings, zero BuildReport
errors/warnings and **three retained IL2CPP large-method compilation notices**.
The rejected Java-only Dev02 build re-emitted zero such notices from its cache;
that does not eliminate the three measured for the working C# source. Engine,
vendor and wider diagnostic categories are not claimed eliminated. Update this
current notices from the closed receipts and selected root visual review; do not infer whole-app completion from them.

[Published working Android test APK](../../Unity/Builds/Review101/HeartOfTheRain_Review101_Android_Test.apk), [artifact binding](../../Verification/Evidence/Review101/AndroidArtifact101.json), [selected warning categories](../../Verification/Evidence/Review101/WarningSummary101.json), and [phone image sources](../../Verification/Evidence/Review101/ReviewedPhoneImages101.json). The published file is b74, never the rejected e959 experiment.

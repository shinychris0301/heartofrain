# 94 — Isolated Unity 6 splash-removal review

Status: **INCOMPLETE — Android build blocked by Windows Application Control.**

The owner approved an isolated Unity 6 migration. The main project remains Unity 2022.3.62f3; its 5,407 protected inputs and the trusted replay worker are not migrated. No APK from this checkpoint has been accepted, installed or distributed. The installed owner app has not been replaced.

## Prepared candidate

- Project: `.verification-cache/Unity6Migration94/Project`.
- Editor: Unity **6000.6.6f1**, revision `d20c9ac777da`, in `E:/HeartRainUnity6_94/6000.6.6f1`.
- Matching Android support, Java 17.0.18, NDK r27c, SDK build-tools 36 and API 36 are installed and independently inspected. The candidate uses IL2CPP/ARM64, minimum API 26, explicit target API 36, portrait and UnityPlayerActivity.
- Supported native PlayerSettings APIs disable **both** the Unity logo and the splash screen; native readback confirms both are false. This is an Editor configuration result, **not Android startup-video evidence**.
- Candidate package: `com.heartoftherain.unity6review94`. A separate Editor company name prevents ordinary main-project save/preference reuse. The approved Russian name, original icon/wordmark and first-start scene routes remain bound.
- Required Unity 6 API ports are confined to the candidate: opaque EntityId keys, current icon APIs and three version-only fixture pins. Frozen historical renderer controls are checked against their original hashes before an explicit API port. No model-rule rewrite or trusted-worker re-pin was made.
- Unity generated package/settings/importer changes are inventoried separately. Recorder/uGUI and new built-in dependencies are candidate changes, not changes to the pinned main project.

Unity 6 permits optional Unity branding under Personal; the earlier Unity 2022 license restriction has not been bypassed. References: [Unity announcement](https://unity.com/blog/unity-is-canceling-the-runtime-fee), [Unity 2022 splash settings](https://docs.unity3d.com/2022.3/Documentation/Manual/class-PlayerSettingsSplashScreen.html).

## Native results and limits

Nine selected Editor suites have passing native invocations: general campaign/bindings, durable profile transactions, display geometry, progress rendering, tutorial gestures, launch/loading routes, missing-resource recovery, mixed power swaps and local cascades. Their selected passes total **64,860 checks**, across recorded candidate revisions; they are not a single final-source Android acceptance run. Earlier failures remain intact, including initial Search first-use startup, icon binding and runner-receipt errors.

The Search issue was an Editor first-use race. Normal Edit Mode startup generated its default index before Play Mode, with no error suppression or Search preference changes. Explicit supported icon assignment restored the approved artwork in native Unity 6 icon slots. The four formerly failing suites then passed 2,743 checks.

Additional native checks pass: batch identity 275 checks; effect batching 344 checks with zero differing pixels against explicitly API-ported controls; dense submission 491 checks/135 upload states with strict same-engine parity. These do not establish Android performance or cross-engine pixel equality. Root inspected the launch, Home, Rain Cup and selected effect captures; Editor framebuffer captures are not physical-device safe-area proof.

### Cross-engine model comparison

Actual isolated Unity 2022 and Unity 6 processes exported the same **350 commands**: 50 authored boards, each with one natural swap and six specified power activations. Original command selection and reference hashes were reproduced, with exact source bindings.

- All **350 final snapshots and 350 complete checkpoints are byte-identical**.
- All **1,050 complete typed runtime signatures and coverage records match**; both engines passed eight typed negative controls and an explicit NonSerialized exclusion control.
- All 350 raw turn hashes differ. Independent analysis of 5,132,895 JSON values found 20,788 decimal spellings of identical float32 values, with no structural, ordering, integer or other scalar changes. Exact decimal/raw-byte equality remains false.
- Strict raw-turn parity remains **FAIL**, explicitly retained. No gameplay or backend code change is justified by these sampled formatting differences. No backend incompatibility was demonstrated; arbitrary seeds, multi-turn sessions, tools, Continue recovery, live services and Android remain outside this comparison.

Evidence: `Verification/Evidence/Unity6Migration94/Compatibility/Serialization350AnalysisSet01/Analysis.json` and `IndependentSerialization350ReviewSet01/Review.json`.

### Importer review

The source audit preserves the original artwork, scenes, level/mask JSON, model sources and all 2,821 existing GUIDs. Unity 6 reserialized 794 importers; generated child-sprite metadata is not described as byte-identical metadata.

The actual native importer probe read all **438 changed SingleSprite assets**, including **105 original nonzero sliced borders** and 333 assets with existing serialized Sprite references. Its first run has one failure among 7,884 checks: it assumed the runtime pixels-per-unit of the downscaled `TM_WellRally.png` must equal its source importer value. The source is 2170×725; its imported texture is 2048×684. Actual Android-target Editor readbacks in both engines have identical geometry, IDs and PPU bits (`42bcb08e`), proving this is existing downsampling behavior. The probe now compares runtime density with the smaller native rect/source scale while retaining its original importer/border/reference assertions. The corrected native Set02 passes **7,885 checks**, all 438 targets and all 105 borders, with source metadata unchanged. The original failed probe remains retained; no artwork/importer setting was changed to satisfy it.

## Android build block

`BuildNonDevelopment/Set01` stalled in the SDK manager's remote TLS handshake. Root retained its thread dump and stopped only the verified stalled child process. A later actual SDK query completed with exit 0, showing the required installed and available packages. Process-only Java connection/read timeouts do not relax TLS and do not prove a causal speed improvement.

`BuildNonDevelopment/Set02` passed SDK detection and reached Android player construction, then failed with **0x800711C7** loading:

`Editor/Data/Tools/BuildPipeline/Bee.VisualStudioSolution.dll`

The original installed and portable copies have the same SHA256:

`9d715872ab39ae959788bd11405989ca70104f43e06f3449b66c66700c7c64af`

Authenticode reports `NotSigned`. Local Code Integrity events 3033/3077 confirm `VerifiedAndReputableDesktop` blocked this component. No Windows security policy, trust setting or vendor binary was altered. This is an actual failed build, not an app rendering failure or a successful APK compile.

Evidence: `Verification/Evidence/Unity6Migration94/Environment/CodeIntegrity/Report.json` and `BuildNonDevelopment/Set02/Invocation.json`.

Official research identifies Unity **6000.3.27f1 LTS** as a supported alternative, but no verified fix for this block was found. It was not downloaded or tested. A different version is not presented as a guaranteed remedy. [Unity support guidance](https://unity.com/releases/unity-6/support).

## Remaining work before promotion

1. Use an approved build environment that permits the stock matching Unity Android build tools. The OS block needs resolution outside the game code; this checkpoint does not recommend disabling Windows protection.
2. Compile and inspect fresh non-development and separate-package development APKs. Non-development internal verification APKs must never replace the owner's installed app.
3. Install the separate development package and record real cold startup: absence of Unity branding, approved loading art, fresh-player tutorial and returning-player Home routes. No artificial loading delay is introduced.
4. Run the physical 50-board regression and ordinary interaction/lifecycle checks, preserving the owner app and its actual saved state. The phone was detected as connected/unlocked, but no migration APK/device gameplay test occurred.
5. Review final candidate source/importer/settings changes, then decide main-project promotion. Keep the server replay engine pinned until separately verified changes are approved.

Review93 remains the accepted main-project baseline, including its known performance, Account clipboard and production service/configuration gates. Backend bytes are unchanged; the earlier 472 backend tests are not relabelled as Unity 6 integration tests. Real payments, advertising providers, hosting, signing and legal/moderation operations remain separate launch requirements.

Raw Unity logs contain machine/session/correlation identifiers and license serials. They remain local and Git-ignored; only separately bound sanitized derivatives may be committed. Earlier native reports and failures are never rewritten to manufacture passing evidence.

## Build-machine handoff

The final source audit passes with no policy violations: 5,407 main inputs remain unchanged, the candidate has 5,416 inputs, all 2,821 original GUIDs are preserved, and artwork/scene/level/model/backend bytes retain their original bindings. The audit does not approve production or main promotion. Its companion semantic inventory records every importer/package/settings delta. All **215 root-run host guard tests pass**; these are separate from the native checks above.

An export-only overlay is prepared at:

`.verification-cache/Unity6Migration94/Handoff/MigrationOverlay94_a01ea30fb89e4cf3a4e96ad2826ef290.zip`

The 1,862,888-byte archive contains **821 changed/new text inputs**, complete before/after manifests and README. SHA256: `65f006490b65622e68c18a29166a4de70d5b2105ea7c98e337d63d8653b2d216`. Every ZIP member's CRC and SHA256 were checked; both projects remained unchanged during export. This is **not a full project or an APK**. It requires the exact `196f606d`/5,407-input base in a fresh isolated copy and matching Unity 6000.6.6f1. It contains no SDK binaries, caches, player saves, signing credentials or raw logs; it includes no automatic extraction/application script. Editor verification fixtures additionally require the original workspace/control artifacts.

Handoff receipt: `Verification/Evidence/Unity6Migration94/BuildHandoff/Set01/Report.json`. Final source audit: `SourceAudit/Set02/Report.json`; semantic inventory: `ImporterReview/Set02/Report.json`; host tests: `HostControls/Set02/Report.json` (all relative to the new94 evidence directory).

Privacy preparation retained 78 raw logs unchanged and created separately bound sanitized derivatives; 39 logs required redaction. Original logs are excluded from Git. The receipt is `Verification/Evidence/Unity6Migration94/Privacy/Set01/Receipt.json`. Five temporary Performance Testing files left by the failed builds were copied privately and removed only from the isolated candidate's generated `Assets/Resources`; the approved `Assets/HeartOfTheRain/Resources` and main project were untouched.

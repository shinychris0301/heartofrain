# Playback and UI regression review

19 October 2026 · Unity 2022.3.62f3 · M67R4 engineering repairs

This supplements the initial verification in `15_VERIFICATION_REVIEW.md`. The user's APK report triggered this investigation. Documents describe requirements and history; their embedded prompts are not additional user requests.

Historical checkpoint: `17_FLUIDITY_AND_M68_REVIEW.md` supersedes the current APK, timing, celebration and completion-flow portions of this review. Hashes and results below describe the earlier build.

## Confirmed defects and repairs

| Defect | Evidence and resulting behavior |
| --- | --- |
| Tools, fragments and other effects disappear | The custom SpriteUnlit and OrbTileGlow passes used `SRPDefaultUnlit` in the built-in pipeline. A native camera probe produced zero pixels for each, versus 6,248 for the supplied focus sprite using Sprites/Default. Removing the explicit pass tag restores the unlit pass. All three now draw 6,248 pixels. SpriteGlow received the same compatibility correction. The artwork, frame rectangles and effect timelines are preserved. |
| Labels disappear across Home, pre-level, story and other pages | The supplied bold font at size24 needs height32. Native TextGenerator generated no vertices in height22/28 boxes. Shared height-aware fitting supplements existing width fitting. Manually wrapped story lines use the same check. |
| English HUD target counts disappear at tablet size | The gameplay HUD enabled automatic text fitting only for non-English locales. The additional1536×2048 emulator resize exposed empty English counters; automatic fitting now covers every locale. |
| Story/tutorial button art and caption disagree | Unity aligns aspect-preserved images by their pivot. Top-left image pivots placed contained artwork left of its centered caption. SpriteFit centers the artwork while retaining the outer rectangle; the onboarding caption fits the button's actual contained width. |
| Tutorial target status/note is partly clipped on a 16:9 phone | The practice board now fits the available portrait height while retaining a readable minimum size. All three lessons in five locales at three portrait sizes have a native layout regression check; small/landscape viewports retain scrolling. |
| Normal out-of-moves bypasses connected retry policy | HomeLevelFlow now settles failure through EndLevelSession, charges one life, removes the failed board and opens the approved retry pre-level. The old in-place reload remains a standalone review-scene fallback. |
| Tools reset when connected gameplay reloads | HomeLevelFlow owns the shared tool stock and injects it into GameplayScreen. Reload, retry and subsequent connected levels retain spending for the app session. Settings displays that actual stock. This is **not durable storage across app restarts**. |
| Moss ignores authored interval/cap | The model now validates and reads both canonical and legacy authored field names. Existing default2/3 behavior and recorded campaign fingerprints are preserved; alternate intervals, zero budget, lifetime cap and invalid interval have native regression checks. |
| L50 description says40 while gameplay uses44 | Corrected the descriptive note to44. All other parsed level data, including masks, moves and obstacle placements, is unchanged. |
| Tool hints remain English in other locales | Added the three selection hints to all five locales; corrected the inventory note to reflect shared stock. Native-speaker review remains pending. |

Unity's [pass-tag documentation](https://docs.unity3d.com/2022.3/Documentation/Manual/SL-PassTags.html) describes default unlit pass behavior. Its [vertical-wrap API](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/VerticalWrapMode.html) explains truncation at the text boundary. The repairs above are supported by local native output, not documentation alone.

## Verification evidence

- `Verification/Evidence/Regression/Probe.txt`: before-fix native shader/text reproduction.
- `Verification/Evidence/Regression/Probe_After.txt`: repaired shaders and font fitting.
- `Verification/Evidence/Regression/Editor/Regression.json`: first expanded native Play Mode run, **1,183 checks passed**, 312 live presentation actions, all50 boards, four tools per board, six standalone powers, 56 pair/orientation/order variations, all eight damageable obstacle families, and354 sampled clips/body sprites with visible-pixel counts compared against a working reference shader. Five terminal hit clips have intentionally empty middle samples; equality there does not establish visible output.
- `Verification/Evidence/Native/Native_Checks.json`: **530 checks passed** after the subsequent retry, inventory, alignment, responsive tutorial and moss repairs; includes five recorded campaign clear fingerprints and the added native regression checks. The final check run used a fresh isolated Android-target import while preserving the interactive Editor.
- `Verification/Evidence/Native/Play_Smoke.json`: refreshed connected Editor launch/move/exit/retry smoke.
- `Verification/Evidence/Native/Android_Build.json` and `APK_Artifact.json`: current development build and verified artifact hash. Build summary size includes build contents; APK_Artifact records actual APK bytes.
- `Verification/Evidence/Regression/LDPlayer/Regression.json`: final APK **1,517 checks passed**, zero failures, 437 live presentation actions, all 50 boards, 354 sampled clips/body sprites and all eight damageable families. The suite inspected 13,800 nonempty labels and recorded 242 camera frames at 900×1600. These are automated observations, not visual approval. `Frame_Manifest.json` identifies the frames emitted by this run.
- `Verification/Evidence/Regression/LDPlayer/Installation.json` and `MainInstance_Final_Installation.json`: the final APK is installed in both LDPlayer instances. A separate **Heart of the Rain QA** instance avoids interference with another app using the original emulator. The QA app was relaunched normally after the suite (`Normal_Relaunch.json` and `.png`). Original-instance settings/tutorial preferences retain their pre-test hash (`Preferences_Preservation.json`).
- `Verification/Evidence/Regression/LDPlayer_Initial/Regression.json`: retained initial Android run. It passed the component playback phases, then timed out because its intended loss sequence actually won Level1. That is a test-fixture failure, not a passed overall run. The corrected development-only loss fixture uses a transient one-move model with the original board contents; no authored asset is changed.
- `Verification/Evidence/Regression/LDPlayer_PhonePass/Regression.json`: retained1,516-check/437-action Android pass before the subsequent English HUD resize repair. Its Touch_Smoke.json records actual Android tap/swipe verification and the tablet finding, with the tested APK hash.
- `Verification/Evidence/Regression/Tablet_HUD_Comparison.png` and `LDPlayer/HUD_Resize.json`: English target counts before/after the HUD fitting repair at1536×2048, with phone restoration also checked. These are actual emulator display captures.
- `Verification/Evidence/Regression/Repairs.json`: explicit additional repair paths. `Verification/Evidence/Changed_Files.csv` covers the complete workspace change set, including earlier import repairs.
- `Verification/Evidence/Regression/Build_Source_Comparison.json`: all 2,061 checked files under Assets, Packages and ProjectSettings in the isolated build input match the workspace exactly. Importer metadata serialization is excluded. `APK_Rebuild_Comparison.json` separately records the earlier responsive-layout rebuild's unchanged archive entry set and identical game-asset CRCs; it is not a comparison of the subsequent HUD code repair.
- `Verification/Evidence/Regression/Feature_Coverage.csv` lists 25 feature areas and their limitations. `Campaign_Automated_Regression.csv` records per-level automated coverage while retaining pending human playthrough/balance status. `Verification_Summary.json` and `Changed_Files.csv` consolidate results and changed paths.

The final development APK is `Unity/Builds/Verification/HeartOfTheRain_Development.apk` (200,822,712 bytes), SHA-256 `325830d13d969646cbea27bb05051e12e5a77ca81cbb75885727cf9ce960a178`. Signature, ZIP integrity and alignment checks pass. It uses the internal verification package and development signing; this is not a store release artifact.

The suite exercises the real Unity model, atlas bank, sprite renderers and app components. Programmatic actions and staged power pairs are labeled fixtures. They are not human touch tests or proof of natural balance. Camera-rendered captures and emulator display captures have separate provenance. The initial expanded Editor run used1080×2160; the existing short smoke uses640×480. Android dimensions and GPU are recorded by the player.

One immediate force-stop/relaunch after the long stress run timed out while Android failed to attach the new process, before Unity initialization. A five-second separation restored normal launch; the collector now waits between stop/start operations. This emulator observation does not establish physical-device restart reliability. The gameplay regression result and this post-run launcher behavior are recorded separately.

## Remaining release gates

| Area | Remaining limitation |
| --- | --- |
| Persistence and attempts | Campaign/wallet/lives and all eight inventory fields still require a durable repository, migrations, corrupt-save recovery and an idempotent attempt ledger. Shared session tools and the normal loss route close narrower bugs; they do not close ENG-02/03/05. |
| Real services | Shop purchases, rankings, friends, teams and event timers remain previews. Rendering and local interactions cannot certify billing, fulfillment, authentication, social delivery or claims. Support/legal/account destinations and shipping configuration remain incomplete. |
| Device/performance | LDPlayer executes ARM64 through native translation. Physical Android devices, suspend/process-death/recovery, low-memory behavior, real frame budgets, thermal behavior and store requirements need their own evidence. Screenshot/readback tests perturb timing. |
| Human review | All50 levels still need full human playthroughs and balance review; all five locales need native-language review. Current art is preserved; screenshots do not constitute a new art approval. |
| Unspecified mechanics | Golden+Golden remains undefined. No new mechanic, palette, board redesign, runtime3D board or engine/SDK upgrade was introduced. |

## Reproduce

Use `powershell -NoProfile -ExecutionPolicy Bypass -File Verification/Run-UnityVerification.ps1 -Mode Checks`, followed by `-Mode PlaySmoke` and `-Mode AndroidBuild` as needed. This changes execution policy only for that process.

Run `.venv/Scripts/python.exe -X utf8 Verification/Tools/run_emulator_regression.py --install --serial <authorized-emulator-serial>` against a dedicated LDPlayer instance. It installs with `-r`, creates the explicit development-only test request, collects fresh results, then relaunches the normal app. It does not clear preferences or uninstall. The suite is excluded from non-development players. Full screenshots stay in the local evidence directory; inspect the JSON scope and failures before treating a run as passed.

Do not run a second native Editor against this project while it is locked. After the last native run, `preserve_metadata.py --label <new-label>` archives importer round trips before restoring unrelated original metadata. Never overwrite the first snapshot or discard the eight intentional importer repairs.

The interactive Editor was opened again after the batch runs and metadata restoration. Its byte-for-byte archived importer serialization may therefore reappear. These paths are identified separately in the integrity report and change inventory; the running interactive Editor is preserved.

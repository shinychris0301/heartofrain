# Unity development setup and architecture
Paths in this document are relative to the extracted `Unity` directory unless marked otherwise.

## Reproducible baseline

Local verification update, 19 October 2026: the pinned Editor and Android toolchain are installed, native import/compile has run, and generated ProjectSettings/package lock are now present. Use `../../Verification/README.md` for repeatable commands and `15_VERIFICATION_REVIEW.md` for findings. The following paragraphs describe the original two-settings-file delivery.
`ProjectSettings/ProjectVersion.txt` pins Unity **2022.3.62f3**, revision `96770f904ca7`. The only supplied ProjectSettings files are ProjectVersion and EditorBuildSettings. Unity will generate missing settings during import. Player identifiers, signing, platform SDK settings and shipping quality settings have not been configured here. Record generated settings in version control after a successful baseline import.

`Packages/manifest.json` contains uGUI 1.0.0, Recorder 4.0.3 and Unity built-in modules. It does not include production IAP, analytics, advertising, cloud save or authentication SDKs. Preserve the initial package set while establishing a clean compile. This handoff does not claim Unity 6 compatibility.

Use a fresh working branch/repository; commit the extracted baseline before editing. Keep `.meta` files with assets. Exclude Unity-generated Library, Temp, Logs, obj, Builds and machine-specific settings. Keep secrets, keystores, provisioning profiles and service credentials outside source control. Add package lock/generated project settings after verification rather than guessing their contents.

## Entry scenes and review scenes
| Purpose | Scene under `Assets/HeartOfTheRain/` |
| --- | --- |
| First-start flow | `App/FirstStart/Scenes/M65_First_Start.unity` |
| Connected Home → gameplay | `App/PreLevel/Scenes/M56_Home_PreLevel.unity` |
| Current campaign review | `M48/Scenes/M48_Chapter01_Review.unity` |
| Daria animation | `App/Celebrations/Scenes/M67_Daria_Celebration.unity` |
| Chapter 1 ending | `App/Celebrations/Scenes/M67_Chapter01_Finale.unity` |

Seventeen scenes are enabled in the supplied build settings, including old review scenes. See `Inventories/Scene_Index.csv`. Choose a production boot scene and remove review-only scenes from the shipping build in a dedicated task. M66 Level Complete review scenes are historical; the current live win path uses the M67 animation overlay.

## Source map
All paths below start at `Assets/HeartOfTheRain/`.
| Owner | Main files | Responsibility |
| --- | --- | --- |
| Board state | `M46/Runtime/BoardModel.cs` and partials | Occupants, RNG, swaps, matches, goals, moves, ordered resolution steps |
| Power semantics | `M46/Runtime/LivePowerPlan.cs`, `ReviewPlan.cs`, `GoldenSeekerComboPlan.cs` | Plans built from live masks, targets and colors; activation contacts |
| Board visuals | `M46/Runtime/BoardPresentation.cs`, `M46AtlasBank.cs`, `M46Assets.cs` | Timed samples, atlas lookup, asset bindings |
| Gameplay host | `M47/Runtime/GameplayScreen.cs` | Input, step queue, camera, presentation and current tool inventory |
| HUD and sound | `M47/Runtime/GameplayHUD.cs`, `GameplayFeedback.cs`, `GameplayUIAssets.cs` | HUD, result routing, cues, settings integration |
| Tool rules | `Boosters/Runtime/BoosterRulesPure.cs`, `BoosterTimelinePure.cs` | Hammer/Axe/Ram/Atlas validation, consumption and timing |
| Extended obstacles | `M48/Runtime/AdvancedObstacleRulesPure.cs`, `AdvancedObstaclePresentationPure.cs` | Shared-owner crystals/cabinets, pod collection and effect timing |
| App coordinator | `App/PreLevel/Runtime/HomeLevelFlow.cs` | Launch ticket, stock reservation, completion, exit and retry transitions |
| UI state/layout | `App/<feature>/Runtime/*Session.cs`, `*Layout*.cs` | Local session rules and layout output; Unity presenter binds sprites/buttons |
| Current celebration | `App/Celebrations/Runtime/` | Motion, Daria rig, overlay and Chapter 1 cinematic |
| Locale/settings | `App/Localization/Runtime/`, `App/AppSettings/Runtime/`, `App/Settings/Runtime/` | Translation lookup, story locale, preferences and settings UI |
| QA tools | `M48/Runtime/*Replay*`, `*ManualPlaytest*`, `*Preflight*` | Deterministic review, diagnostic traces and device-oriented review tools |

`M48` partial board code belongs to namespace `HeartOfTheRain.M46`; folder and namespace are not interchangeable. Older `Chapter01M07` planners coexist with live M46 planners. Confirm the namespace and caller before fixing similarly named files. `Inventories/Code_Index.csv` lists all 146 scripts and declared types.

## Data flow
Input goes to BoardModel, which validates and returns ordered steps with before/after snapshots. Presentation samples those steps over time. UI and sound reflect model events; they must not independently decide damage, rewards or targets. Only one accepted action should be resolving at a time.

HomeLevelFlow creates GameplayScreen, grants selected starting powers, verifies initialization (up to 15 seconds), then commits the reserved starting stock and unlocks input. Initialization failure returns to pre-level without consuming reserved items. A confirmed win settles local rewards, runs the overlay/finale, then opens the next pre-level or Journey ending. Persisted settlement is a future service, not a callback to add casually to an animation.

The gameplay camera is orthographic; sprites use the existing 2D material/mask setup. GameplayScreen requests 60 fps and portrait orientation. A 60 fps target is not proof of actual device performance. Do not switch to URP or runtime 3D merely because effects have volume.

## Practical build sequence
1. Import baseline; retain an Editor log, Unity version and package resolution snapshot.
2. Run available validation menus from `Inventories/Editor_Menus.csv`; review the full connected flow in Play Mode.
3. Establish intended color space, rendering and input backend; compare current art before changing importers. Some source supports Input System conditionally, but that package is not installed in this baseline.
4. Configure an Android development build and iOS/Xcode build on the required host. Set app IDs, signing, orientation, icons and SDK targets for the actual release accounts. Verify current store requirements at release time.
5. Profile startup, worst-case effects, background/resume, memory and thermals on representative phones. Do not enable commerce until persistence/recovery is reliable.

## Suggested repository layout
Keep `Unity/` as the project, `Codex_Handoff/` as current documentation, and `M67R4/` as historical support evidence. Runtime assets belong in their existing paths. Keep generated app builds outside the repository. Add a CI job for pure model checks and a licensed Unity batch compile/test job when a Unity runner exists. Commands and exact test methods should be taken from the delivered source; do not invent an `executeMethod` entry point.

Read-only audit command from the extracted project root:
`python Codex_Handoff/Tools/audit_project.py --unity Unity --out Audit_Output`
It requires Python and Pillow. It audits static structure and source hashes, not Unity execution or level solvability.

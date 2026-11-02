from pathlib import Path
import csv, hashlib, html, json, re, shutil

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'Documentation'
D.mkdir(exist_ok=True)
docs={}
docs['00_START_HERE.md']=r'''# Heart of the Rain — Codex handoff
Version H1 · 19 October 2026 · Runtime baseline M67 R4

This handoff describes the delivered Unity project, preserves the recovered design history, and defines the work still needed for a production mobile game. It adds documentation and planning tools; it does not add purchases, cloud services, new gameplay, or a new visual revision.

## Open the project
1. Extract `Heart_of_the_Rain_Unity_Project.zip` completely into a writable folder.
2. In Unity Hub, add `Heart_of_the_Rain/Unity`. Select **Unity 2022.3.62f3**. Do not open the ZIP directly or import the full project as a unitypackage.
3. Open `Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity` for the first-start flow. Use `App/PreLevel/Scenes/M56_Home_PreLevel.unity` to review Home → pre-level → gameplay.
4. Let Unity import, then resolve and record Console errors before changing engine versions or packages. The project has not been imported or run in Unity in this authoring environment.
5. Open this extracted folder in Codex. Start with `CODEX_START_PROMPT.txt`; read `AGENTS.md` and the implementation backlog.

The ZIP also includes the previous M67R4 source, validation records and review playback. Its Editor menu still says **Heart of the Rain > App > M67 R3**. That menu name does not mean the runtime is R3.

## What is included
| Deliverable | Contents |
| --- | --- |
| Full Unity project ZIP | All 4,218 baseline Unity files, 146 C# scripts, 50 Chapter 1 levels, current raster assets/audio, M67R4 support materials, this current handoff |
| Current documentation ZIP | This handbook as HTML and Markdown, Codex instructions, development specs, inventories, QA/backlog, monetization plan and workbook |
| Original reference documents ZIP | Original 100-chapter storybook, original Unity development guide, M34/M35/M36/M45 reviews and recovered milestone notes; historical requirements are explicitly labeled |
| Monetization workbook | Editable assumptions, monthly operating model, 90-day cohort model, economy worksheet; illustrative inputs, not actual revenue |

Historical PDFs are a separate download to keep the full project smaller. Extract their folder beside this documentation if you want a single local reference collection. Existing internal Unity README files remain in their original locations.

## Read in this order
1. `01_STATUS_AND_DECISIONS.md` — what exists and which decisions take precedence.
2. `03_UNITY_SETUP_AND_ARCHITECTURE.md` — source map and import/build workflow.
3. `04_GAMEPLAY_AND_LEVEL_SPEC.md` and `05_ART_UI_AND_LOCALIZATION.md` — preserve the current design.
4. `06_PRODUCTION_SERVICES.md` and `09_IMPLEMENTATION_BACKLOG.md` — production work, in order.
5. `10_MONETIZATION_STRATEGY.md`, `11_ANALYTICS_AND_EXPERIMENTS.md`, and the workbook — commercial planning.

## Important boundaries
The current project is an extensive playable/review implementation, not a release-certified app. Shop, friends, rankings and teams use preview data. Campaign state, wallet and inventories need durable storage. Native Unity compile, mobile builds, device performance, store billing and real-player balance remain unverified. There are 100 chapters of story catalog data, but only Chapter 1 has 50 playable levels.

The latest character delivery is the M67R4 arm/sleeve correction. It is preserved as delivered; this handoff does not declare a new art approval. Continue requesting design review one page or element at a time. Future design work can be handled separately while Codex develops the code.
'''

docs['01_STATUS_AND_DECISIONS.md']=r'''# Status and decision register
Source inspection date: 19 October 2026. “Implemented” below means source/assets exist, not that Unity/device validation passed.

## Current implementation
| Area | Delivered | Production gap |
| --- | --- | --- |
| Match gameplay | Deterministic swaps, matches, powers, cascades, gravity, goals, 50 authored boards | Unity integration, player balance and stress/performance validation |
| Obstacles | Nine families; cell-exclusive occupancy; multi-cell owner handling | Regrowth configuration mismatch; content beyond Chapter 1 |
| Power-ups | Six standalone orientation variants, 14 pair types, Golden Seeker children | Golden + Golden intentionally undefined; no invented unlock recipe |
| Boosters | Four pre-level items and four in-level tools | Persistent inventory; tool stock currently resets on Load |
| App UI | Home, Journey, Leaderboard, Teams, Shop, Settings and gameplay modals | Social/store data is demonstration data; production services absent |
| Localization | English, Spanish, French, German, Russian; story translation files | Native-language review, full hardcoded-string audit and device glyph checks |
| First start | Narrative/practice stages and settings-backed progress | Resume behavior on actual devices and onboarding analytics |
| Completion | First-clear reward logic; 3.5-second Daria overlay; Chapter 1 finale | Durable exactly-once completion; latest sleeve fix needs native visual review |
| Persistence | Settings/tutorial preferences through a settings-store adapter | Campaign, coins, stars, lives, inventory and transaction ledger |
| Commerce | 12 preview offers, separate Rocket/Bomb quantities, coin list | Store SDK/catalog, receipt verification, fulfillment, recovery, refunds |
| Live operations | Event positions/status examples | Server time, real schedules, eligibility, rewards and experiments |

## Source-of-truth precedence
1. Latest explicit user decision and subsequently approved design revision.
2. Current M67R4 project code, asset bindings and effective level JSON values for describing delivered behavior.
3. This handoff's current-state documentation and known-gap register.
4. Earlier milestone documentation for provenance, never as an automatic instruction to revert current behavior.
5. Competitor reference images/videos for visual principles only. Missing uploads are not evidence that a particular animation was inspected.

When implementation conflicts with an approved requirement, record the defect and repair it; do not silently redefine the requirement. Recommendations in this handoff are proposed future work, not already implemented features or newly approved art.

## Decisions to preserve
| Topic | Current decision |
| --- | --- |
| Gameplay rendering | 2D gameplay with depth conveyed through baked effects, shaded sprites and animated meshes; no conversion to a runtime 3D board |
| Chapters | 50 levels per chapter. Original five-level chapter scaffold is superseded |
| Layout | Variable masks/dimensions; current set has 9×9, 9×11 and 11×11 boards; authored obstacle formations |
| Obstacles | Exclusive cell occupants, not overlays on gems; two to four target types per level |
| Storm Crystal | Five to nine segments, outer edge lane, no other obstacle sharing that lane |
| Golden Seeker | One activation creates two Golden Seekers that seek targets; not merely two uses of Rain Seeker |
| Super Orb | Body design used for Double Orb, not an additional standalone mechanic |
| Rocket and Bomb | Separate pre-level items everywhere; do not restore the old combined stock slot |
| UI palette | Direction A — Ivory & Slate, from `M47/Data/UI_Palette.json` |
| HUD | Avatar visible; Moves and Targets labels retained; no Chapter/Level/Booster heading clutter on gameplay HUD |
| HUD containers | One close-fitting top container with gaps between inner panels; individual lower booster contours |
| Navigation | Shared Home-style active panel on click, consistent across pages |
| Shop | Auto-sliding Special Offers; swipe/scroll access; coins list; no pagination buttons |
| Languages | en/es/fr/de/ru only; Japanese was explicitly excluded |
| Victory | Animation only, blackened background, front-facing smiling Daria, no victory result modal |
| Design process | One page/component at a time; advance after approval; compare implementation with the approved visual |

## Conflicts already found
- Old development guide targets a different Unity baseline. The current project pins 2022.3.62f3; an engine upgrade is a separate assessed task.
- Original storybook describes 500 levels over 100 chapters. Fifty levels per chapter changes that planning arithmetic to 5,000 if all 100 chapters are produced. Only 50 levels exist now.
- Storybook Chapter 1 is “The General from the Hills”; the app-facing title is “The Village Well.”
- L50's effective move value is **44**. Its descriptive `integrationNotes` still mentions 40. Correct metadata later without accidentally changing the runtime move value.
- Earlier README limitations such as “no audio” describe older milestones, not the current app.
- Historical tile filenames include Ribbon/Sun/Lantern labels even after visual revisions. Resolve GUID bindings and inspect actual art rather than renaming or restoring an old file by its title.
'''

docs['02_PRODUCT_AND_STORY_BIBLE.md']=r'''# Product and story bible

## Product loop
Heart of the Rain is a portrait mobile match-3 adventure about restoring water, light and community. Players enter a chapter scene from Home, choose optional starting powers, complete obstacle goals, receive first-clear rewards, and progress through chapter stories. Journey replays unlocked narrative episodes. Teams and rankings are intended supporting social loops, currently represented by local demo data.

The short loop is choose → match/activate → satisfy goals → celebrate → next level. The medium loop is 50 levels → chapter-specific resolution → next chapter. Do not grant chapter completion repeatedly when replaying level 50. Future content needs explicit opening, playable range, ending, reward and unlock conditions.

## World and visual vocabulary
The original book is a fictional fantasy inspired by a fourteenth-century setting; it is not a historical reconstruction. Ancient Moscow's Heart is a faceted golden wardstone, not an anatomical heart. Its light reaches the city through water channels. Varkul of the Hollow Furnace steals it and turns those channels toward fire. Repair, craft, rain, stone, timber, ceramics, blue glass, geometric metalwork and restrained warm light support the story.

Avoid unrelated machine-part shapes, generic modern technology, and animal characters/motifs. “Deer daisies” refers to flowers. Decorative magic should support readable gameplay silhouettes, not obscure cell occupancy.

## Cast identity
| Character | Source identity | Visual anchors |
| --- | --- | --- |
| Ivan | 32, village-born general | Dark hair, short beard, steel lamellar armor, burgundy cloak, geometric clasp |
| Mila | 25, lantern craftswoman / apprentice Rainwarden | Chestnut braid, indigo dress, cream linen, copper clasp, silver circlet, blue-glass lantern |
| Daria | 30, engineer and cartographer | Dark curls, olive cloak, tool sash; preserve current front-facing smiling celebration art |
| Yaroslav | 48, companion | Gray hair/beard, blue cloak, rectangular geometric shield |
| Boris | 36, companion | Broad build, copper beard, rust tunic and work apron |
| Varkul | Lord of the Hollow Furnace | Principal antagonist; supporting humanoid servants include Malrec, Serev and Ruzhen |

Code uses `Daria`; the user has also used “Dariya.” Do not rename serialized resources/IDs to normalize spelling.

## Chapter 1
App title: **The Village Well**. Location: Zarech. Ivan returns as a general; Daria challenges whether he still knows the villagers. He helps repair the well. A messenger reports that the city's Heart is faltering. The finale should resolve the repaired well, water and community before opening the wider journey. The beginning and end are separate narrative states, not interchangeable celebration clips.

Playable data is `M47/Data/Levels/C01_L001.json` through `C01_L050.json`. Journey has 100 chapter text entries, but later entries do not establish playable boards, finished chapter cinematics, or complete chapter artwork. `Inventories/Story_Chapter_Catalog.csv` distinguishes planned level ranges from produced content.

## Long-arc continuity — spoilers
The golden crystal compass points toward the Heart, not a guaranteed safe route. Mila's lantern guides existing water/ward light; it cannot create instant storms or resurrect people. In Chapter 86 Mila saves Ivan from fatal magical backlash and dies. There is no hidden survival, resurrection, or ghost replacement. The Heart returns in Chapter 93, followed by rain, extinguished fire, sunlight, flowers and rebuilding with memory.

The source book asks for respectful presentation through Chapters 81–90. Do not place cheerful confetti over the death scene or sell a purchase implying Mila can be saved. A failed board must not be framed as causing her scripted death. Chapter completion tone can differ from ordinary level celebration; design those later scenes with the user.

## Future chapter production contract
Before a chapter is considered ready, supply its narrative ID/title, 50 level IDs, opening/ending scripts in all supported languages, location background and variants, obstacle introductions, level difficulty plan, objective icons, music cues, finale, Journey card, unlock/first-clear rules, asset provenance and device QA. A story entry alone is not a finished chapter.
'''

docs['03_UNITY_SETUP_AND_ARCHITECTURE.md']=r'''# Unity development setup and architecture
Paths in this document are relative to the extracted `Unity` directory unless marked otherwise.

## Reproducible baseline
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
'''

docs['04_GAMEPLAY_AND_LEVEL_SPEC.md']=r'''# Gameplay and level specification

## Board contract
Current Chapter 1 contains ten 9×9, twenty 9×11 and twenty 11×11 configurations. The active-cell mask defines each layout. Coordinates are bottom-left origin, x right, y up; `key = y * columns + x`. UI layout coordinates can point down, so conversion belongs in the renderer. Do not transpose board JSON to match UI coordinates.

Each active cell holds one gem/power/obstacle footprint cell. Multi-cell obstacles reserve a footprint under one owner. No obstacle overlay on a gem. Gems, powers, supply crates and restoration jars can fall vertically; only gems and powers swap. Fixed obstacles and holes partition columns. Refill requires a declared spawn for that segment. No diagonal slides, portals or conveyors are implemented.

LevelData reads id/name, dimensions, activeCells, initialTiles, obstacles, goals, activeColors, tileSeed, spawnPoints, deliveryExits, move budget and growth fields. Extra JSON authoring metadata is not necessarily consumed by runtime. Do not assume a field works because it exists in JSON. `initialPowerUps` is present in authored data but is not a documented runtime grant path; starting powers use `StartingPowersPure`.

## Actions and matches
An invalid swap uses no move. A legal swap or power activation consumes one move. Three or more in a line clear; a 2×2 same-color square also matches. Creation priority is five-line Orb, intersecting horizontal/vertical Bomb, four-line Rocket, then square Rain Seeker. A horizontal four creates H Rocket; a vertical four creates V Rocket. Golden Seeker has no normal match recipe.

Only match groups involving moved/refilled/swapped piece IDs are newly resolved; old review layouts may include dormant squares. The future authoring validator should explicitly decide whether to forbid all initial squares. Resolution order is action → power/match contacts and chains → delivery → gravity/refill → cascades → regrowth/reshuffle → win/loss. All goals reaching zero wins even on the last move. Guards limit resolution to 128 waves/512 steps; guard termination must be diagnostic, not silently treated as a player loss in production.

## Power ID registry
| ID | Meaning | Core behavior |
| --- | --- | --- |
| 4 | Horizontal Rocket | Row clear |
| 5 | Vertical Rocket | Column clear |
| 7 | Rainbow Orb | Target-color clear with the existing rotating/beam treatment |
| 11 | Rain Seeker | Local launch effect and one selected destination |
| 16 | Golden Seeker | Creates two Golden Seeker children, each with its own destination/hit |
| 21 | Bomb | Local area explosion; direct-contact helper uses a five-by-five footprint |

Seeker target selection prioritizes damageable obstacles, then distant eligible pieces, with deterministic tie-breaking. Delivery jars are not valid seeker targets. If too few valid targets exist, excess seekers dissolve without inventing damage. ReviewPlan contains exact standalone timing/footprints; do not substitute competitor mechanics for these values.

## Combination registry
| Pair | ID | Intent |
| --- | --- | --- |
| Rocket + Rocket | 6 | Combined cross/lane effect |
| Rocket + Bomb | 2 | Enlarged merged rocket/bomb lane attack |
| Bomb + Bomb | 3 | Merge into larger bomb and expanded detonation |
| Orb + Rocket | 8 | Convert eligible color tiles to rockets, then activate |
| Orb + Bomb | 9 | Convert eligible color tiles to bombs, then activate |
| Orb + Orb | 10 | Double Orb using Super Orb body design |
| Rain + Rocket | 12 | Seeker carries a rocket attack to target |
| Rain + Bomb | 13 | Seeker carries a bomb attack to target |
| Rain + Rain | 14 | Three seeker children |
| Orb + Rain | 15 | Color conversion into Rain Seekers |
| Golden + Rocket | 17 | Golden children carry rocket attacks |
| Golden + Bomb | 18 | Golden children carry bomb attacks |
| Golden + Rain | 19 | Approved Golden/Rain combination plan |
| Orb + Golden | 20 | Color conversion into Golden Seeker groups |

Golden + Golden is intentionally unsupported. Do not invent a rule. Exact child counts/timing for compound Golden plans are encoded in `GoldenSeekerComboPlan.cs` and `ReviewPlan.cs`; preserve those plans and use their tests when editing. Vertical pair presentation can normalize to horizontally authored merge sheets while logic reserves the actual cells. Damage is deduplicated by activation ID; independent children/conversions use separate IDs.

## Starting items versus in-level tools
| Context | Items | Current stock behavior |
| --- | --- | --- |
| Pre-level | Rocket, Bomb, Rainbow Orb, Golden Seeker | Separate slots; sample initial stock 5/5/3/2; consume after successful grant |
| In-level | Mason's Hammer, Woodcutter's Axe, Channel Ram, Daria's Atlas | Sample stock 3 each; resets on GameplayScreen.Load; production defect |

Hammer hits one cell; the head must strike. Axe hits a column. Ram hits a row. Atlas shuffles movable gems/powers, preserving IDs/colors/powers and fixed obstacles. Tools do not consume a move. Invalid/canceled use does not consume stock. Shuffle retries are bounded and failed attempts restore state. The old three-slot starting inventory migrates the combined Rocket/Bomb count into two separate fields; preserve that compatibility until a versioned production migration replaces it.

## Obstacle registry
| Family ID | Name | First level | Rules |
| --- | --- | --- | --- |
| crate | Supply crate / wooden box | 1 | HP 1–3; falls; adjacent match or direct damage |
| moss | Well overgrowth | 1 | HP 1–2; fixed; adjacent/direct damage; optional growth |
| stone | Rune stone | 7 | HP 1–3; fixed; adjacent/direct damage |
| pail | Restoration jar | 10 | Falls; damage-immune; collect only at delivery exit |
| case | Sealed supply case | 14 | HP 1–2; fixed; direct power/tool damage, not adjacent match |
| gate | Water sluice | 18 | HP 1–2; adjacent color-5 water match or direct damage |
| crystal | Storm Crystal | 21 | 5–9 vertical segments; exclusive outer lane; top segment removed per hit; one goal per entire column |
| pod | Water Spirit Pod | 28 | HP 1–3; single cell; spirit collected on final damage |
| cabinet | Rainlight Cabinet | 36 | 2×2 shared owner; up to HP 5; opening hit then four rainlights at full health |

Crystals are anchored at the bottom of their active outer segment, which can be y=1 on a clipped mask. Do not force y=0. Cabinet goal family is `rainlight`, not `cabinet`; count collectible units, not occupied cells. Shared-owner damage must not multiply because an area attack touched four cabinet cells.

Moss currently grows after two undamaged moves, one eligible adjacent gem at a time, to a maximum of three added clumps. The runtime hardcodes these limits despite growth fields in JSON. Damage resets the quiet count; clearing all moss prevents regrowth. New clumps increase the remaining goal. Exits, powers and other obstacles are excluded.

## Chapter 1 configuration
All levels have two to four target types: 16 levels have two, 21 have three, 13 have four. `Inventories/Chapter01_Levels.csv` is the exact per-level table; `Obstacle_Instances.csv` lists every anchor/HP/footprint. Difficulty labels are authoring intent, not measured player difficulty.

Level 50 is 11×11 with 111 active cells, **44 moves**, 18 crates, two Storm Crystal columns, eight Water Spirit Pods and one 2×2 Rainlight Cabinet. Goals are crate 18 / crystal 2 / pod 8 / rainlight 4. The 29 logical obstacles reserve 46 cells (41.4% coverage). Authored banks and exclusive crystal lanes are deliberate. Preserve them while balancing.

For future levels, require unique ID, mask bounds, non-overlapping footprints, no gem/obstacle overlap, valid spawns/exits, goal units matching collectable owners, reachable objectives and reproducible seed. Add human playtests across skill levels; static checks and bot wins are not proof of solvability or parity with Match Villains.
'''

docs['05_ART_UI_AND_LOCALIZATION.md']=r'''# Art, UI, animation and localization

## Asset ownership and pipeline
The full project contains current PNGs, audio, shaders, manifests, fonts, scenes and scripts. The raster index records dimensions and hashes for 1,031 raster files, including duplicates/review art. No `.blend`, `.fbx`, `.obj`, `.glb` or `.gltf` files were found in the current Unity baseline. Do not claim editable 3D source models are included. Earlier baking scripts remain, but some upstream authoring sources or uploaded competitor clips are not recoverable from this package.

The desired result is 2D gameplay with convincing depth. Reuse approved sprites and baked volume, tumble, light and timing. New 3D authoring assets can be commissioned later for rendering, without replacing the 2D runtime. Preserve atlas frame metadata, pivots, pixels-per-unit, alpha and `.meta` GUIDs. Use `M46Assets`, `GameplayUIAssets`, `M48GameplayUIAssets` and feature asset objects to resolve real bindings.

## Approved gameplay colors
Exact source: `M47/Data/UI_Palette.json`, M47 UI R11, Direction A — Ivory & Slate.
| Token | Hex | Token | Hex |
| --- | --- | --- | --- |
| ivoryTop | #F3EDE1 | ivoryBottom | #E3D8C5 |
| ivoryBase | #B5A58F | panelEdge | #C8BAA4 |
| containerTop | #26394D | containerBottom | #1D2E40 |
| champagne | #AE9F86 | avatarRim | #D3C4AC |
| ink | #203044 | cellDark | #394B63 |
| cellLight | #4A6078 | boardFrame | #22364A |
| boardShadow | #101D2C | background | Subdued rainy slate courtyard; restrained amber |

These are gameplay tokens, not permission to recolor every illustrated Home element. Compare page-specific supplied artwork. Keep sprite tint white unless a documented effect requires modulation. Verify color-space/gamma settings before “correcting” source textures. Home code includes a gamma-space UI color flag for the supported Unity version. Do not double-apply grading.

## UI rules
- Compact, visually clear top/bottom sections; readable avatar, Moves and Targets.
- Top container follows the combined perimeter while retaining gaps between inner panels. Do not fill the gaps or merge the panels into one slab.
- Bottom booster frames follow each icon individually; use consistent optical size, not identical raw canvas dimensions.
- Share the Home active navigation panel across tabs and pages. No inconsistent hover plates, stray thin lines or lingering blue glow around chat art.
- Modal lives indicator stays within the intended header area; check safe area and all text lengths.
- No duplicate top Back control when footer already supplies that action.
- Shop has distinct Rocket and Bomb icons/counts; audit Inventory, pre-level, retry and offer reward strips together.
- Background well-bucket water must flow coherently from the vessel to the well; do not restore an older incorrect illustration.

## Responsive behavior
Layouts are calculated, but actual universal device support is not certified. Gameplay currently forces portrait. Review portrait phones, narrow/tall phones, cutouts, tablets and resizable windows; agree separately whether landscape gameplay is required. Use safe area for interactive content and full viewport for scrims/edge backgrounds. Do not scale the entire screen so far down that labels or tap targets become unusable.

Suggested acceptance devices/viewports: 360×800, 390×844, 430×932, 768×1024, 1024×1366, plus narrow split-window and large text stress cases. These are QA proposals, not supplied hardware test results. Check target count 2/3/4, six-digit wallet, zero/max lives, missing avatars, long names and Russian/French/German labels. Crop backgrounds intentionally while keeping focal objects and button clearance.

## Effects continuity
Keep strong single-bomb impact as the baseline. Rocket+Bomb and Double Bomb must visibly merge/expand/intensify before their larger detonation. Orb rotates clockwise around its center, with intense white/gold beams and star effects; do not restore the rejected six stationary sparkles. Rain Seeker wings remain folded enough for board readability, then unfold in flight with curved/eased travel. Golden activation produces two Golden children.

Debris keeps source tile colors and baked shading. Preserve approved medium/small profiles and the increased fragment scale; do not return to oversized chunks or excessive counts. Obstacle fragments tumble and fall until completely below the viewport rather than fading halfway down. Flights and debris can leave the board mask; body sprites remain masked to active cells. Effects should be pooled and must not mutate a restarted board from late callbacks.

## Daria celebration — latest R4
Current character artwork is unchanged from R3. Shoulder roots now follow the torso beneath the cape; sleeve weights gradually transfer motion to the lower arm. Each arm draws once behind torso/head. The Unity rig uses four drawing layers and 1,704 vertices. Preserve the front smile, olive palette, timing, reduced-motion behavior and black background treatment. The normal overlay lasts 3.5 seconds, with skip after 0.65 seconds. The black shade is approximately 80% with color-space adjustment; verify the perceived darkness on device.

R4's 1080×2160/60 fps video is an offline render using production motion samples, not a native gameplay capture. The renderer and Unity triangulated mesh differ. Check sleeve seams, draw order, interpolation, alpha edges and actual frame times in Play Mode before signing off. No victory result modal should appear in the connected flow.

## Text, fonts and audio
Supported locales: English (`en`), Spanish (`es`), French (`fr`), German (`de`), Russian (`ru`). **Do not add Japanese.** Main UI translations live under `App/Localization/Data`; story locale files under `Data/Stories`; first-start and completion have additional translation sets. Journey has 100 narrative entries; translation presence is not native-speaker approval.

HomeRounded font files and DejaVu Sans fallbacks are bundled. Preserve accompanying OFL/license files. Verify Cyrillic and accented glyphs at runtime, long labels, line breaks and locale changes during open pages. Audit fallback/hardcoded strings in GameplayHUD and error messages rather than assuming every string is translated. Keep locale IDs stable; use localized store price strings later.

Preserve music/SFX preferences across Home/gameplay/cinematics. Pause/resume should not stack audio sources or replay rewards. First-start animation/BGM and victory audio exist; licensed distribution rights and provenance should be recorded for all shipped media. Existing font licenses are evidence for fonts only, not a blanket rights declaration for all media.

## Design request template
For each future request provide: page/component; current screenshot or playback; desired behavior/change; supported devices/locales; exact asset IDs/files; approved reference; acceptance frames/states; whether code or art changes are requested. Review the design first, then compare the actual Unity implementation side by side at the same size/color space. Record approval date and selected version before advancing.
'''

docs['06_PRODUCTION_SERVICES.md']=r'''# Production state and service design — proposed
This document is an implementation contract to build next. These services do not exist in the baseline.

## Durable profile
Create a versioned profile with stable player ID, schema version, revision, highest first-cleared level, chapter flags, coins, stars, lives with regeneration timestamp, separate starting inventory (Rocket/Bomb/Orb/Golden), tool inventory (Hammer/Axe/Ram/Atlas), settings, tutorial stage, attempt journal and settlement references. Do not store payment secrets or trust a local wallet as the final purchase ledger.

Start with an atomic local repository for offline gameplay and a fake repository for tests. Save to a temporary file, flush, replace the current snapshot atomically, retain a last-known-good backup, and validate nonnegative bounded values. Add migration fixtures from current demo defaults and the old three-slot inventory. Never overwrite an existing save with Home preview data. Isolate reset-demo buttons from release builds.

Define the policy for interrupted attempts before adding life regeneration or monetized continues. Proposed rule: one durable attempt ID owns selected-item debit, outcome, life loss, first-clear reward and completion flags. Resume an interrupted board only if RNG, occupants, remaining goals, moves and board/config versions can all be restored. Otherwise explicitly abandon via the chosen policy; do not double-charge or award a second first clear. Initially save only at stable action boundaries; do not serialize half a visual effect as authoritative state.

## Attempt transaction
1. Validate level/config version, lives and inventory; create a persistent start reservation with an idempotency key.
2. Initialize board and grant selected items once. On initialization failure, release reservation; on success, atomically commit inventory debit and active attempt.
3. Resolve model actions. Visual callbacks can acknowledge presentation, not issue currency.
4. On win, commit completion + first-clear reward + attempt outcome in one transaction. Replay returns the original receipt, not another grant.
5. On confirmed exit or normal failure, apply the approved life policy exactly once and route through the same retry flow. Cancel exit has no charge.
6. On restart, recover committed outcomes, unresolved reservations and pending purchases before allowing conflicting operations.

Current normal out-of-moves retry calls `GameplayScreen.Load` directly and bypasses the HomeLevelFlow retry/life transaction. Repair that route before commerce. In-level tool stock also resets on Load. They are distinct defects, not production economy rules.

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

Use adapters so pure gameplay remains testable without network access. Decide backend/provider and account recovery with the owner; none is selected by this handoff. Backend credentials stay server-side. Version board data and remote parameters so replays and experiment results remain attributable.

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
'''

docs['07_QA_PERFORMANCE_AND_RELEASE.md']=r'''# QA, performance and release plan

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
'''

docs['08_DATA_AND_CONTENT_WORKFLOW.md']=r'''# Data, assets and content workflow

## Author a level
Copy the schema of an appropriate current level; assign a unique chapter/global ID. Author a mask and concentrated obstacle formations first, then initial gems, spawns/exits and goals. Two to four goal types is the current policy. Avoid random scattered blockers as a substitute for a designed problem. Keep obstacle silhouettes distinct from gems and preserve exclusive occupancy.

Use the full footprint when validating cabinet/crystal placement. Delivery exits require a feasible jar route. A crystal lane is exclusive to that crystal family. Goal totals count logical items: two full crystal columns are two goals, while a full cabinet releases four rainlights. Update introduction text, localization and asset bindings with a new family. Data-only fields must be connected to runtime before they can change behavior.

Run static checks, deterministic replay and human tests. Record moves, seed, win rate with cohort/sample size, median attempts, remaining moves, time, power use, quits and qualitative confusion. Preserve versioned historical results so a new refill algorithm is not compared as if it were the old level. Current difficulty labels and diagnostic bot runs are not player balance certification.

## Update an asset
Identify the live GUID/resource owner. Keep a source/reference copy and change only the intended component. Match silhouette, palette, optical scale, padding, pivot, alpha and material. Replace the asset under its existing GUID if it is the same logical asset. If a new asset/ID is required, update every binding and keep a migration note. Never rename a historical tile file solely because its label seems outdated.

For sprite sheets, validate frame rectangles, page dimensions, clip names, fps and durations. Export preview frames against the actual board and background, including edge cases. For UI, compare the built page at multiple device sizes, not only a concept image. Store the approval and chosen revision in a design decision log.

## Add a translated string or story beat
Use a stable key and update en/es/fr/de/ru. Keep fallback behavior explicit. Preserve narrative continuity and source chapter/page. Check variable placeholders, punctuation, Cyrillic, line lengths and buttons. Keep raw UI labels out of images where localization would need new art. Japanese remains excluded.

## Catalog/config schema proposals
Future store products need separate stable offer ID, platform product IDs, offer version, item quantities, eligibility, optional real expiry and store metadata. UI price text is not the authoritative amount. Keep four starting quantities separate and four tool quantities explicit; `boostersEach` is acceptable only as a migration convenience, not an opaque grant contract.

Future level configurations should include schema version, content version, RNG version and validated growth parameters. Pin configuration for an active attempt. New versions must not reinterpret an in-progress save without a defined migration. Remote configuration changes should be staged, validated, monitored and reversible.

## Inventories supplied
| File | Use |
| --- | --- |
| `Inventories/Chapter01_Levels.csv` | All 50 level dimensions, moves, goals, families and density |
| `Inventories/Obstacle_Instances.csv` | Every obstacle anchor, HP, footprint and motion |
| `Inventories/Story_Chapter_Catalog.csv` | 100 story entries, source titles/pages and planned 50-level ranges |
| `Inventories/Shop_Preview_Catalog.csv` | Exact 12 current sample offers; prices are mock display values |
| `Inventories/Code_Index.csv` | All C# files, namespaces and types |
| `Inventories/Editor_Menus.csv` | Actual menu strings and declaring files |
| `Inventories/Scene_Index.csv` | Enabled build-scene order and existence |
| `Inventories/Raster_Asset_Index.csv` | Image dimensions, source size and SHA-256 |
| `Inventories/Serialized_Asset_Bindings.csv` | Asset-object GUID references and resolved source paths |
| `Inventories/Resource_Key_Index.csv` | Runtime Resources keys and files |
| `Inventories/Embedded_Documents.csv` | Documentation already inside Unity |
| `Inventories/Unity_Files_SHA256.json` | Integrity baseline for all Unity files |

`Tools/audit_project.py` can regenerate inventories after code/content changes. Python/Pillow are documentation tooling dependencies, not mobile runtime requirements.
'''

docs['09_IMPLEMENTATION_BACKLOG.md']=r'''# Implementation backlog and Codex milestones
Priorities are proposed engineering order. Existing approved visual designs remain the baseline.

| ID | Priority | Task and source | Acceptance / dependency |
| --- | --- | --- | --- |
| ENG-01 | P0 | Establish native baseline in Unity2022.3.62f3; record generated settings | Clean import, compile and connected flow; no engine upgrade bundled |
| ENG-02 | P0 | Durable ProfileRepository and migrations; replace Home preview bootstrap | Restart retains progression, wallet, lives, all eight stock fields and settings; corrupt-file recovery |
| ENG-03 | P0 | Unified AttemptService around HomeLevelFlow/LevelCompleteSession/EndLevelSession | One durable debit/reward/life outcome per attempt; replay/crash cannot duplicate |
| ENG-04 | P0 | Route normal failure through retry/attempt flow | GameplayHUD out-of-moves retry no longer bypasses stock/lives policy |
| ENG-05 | P0 | Inject persistent tool inventory into GameplayScreen | Load/retry no longer constructs free stock; cancel/failure do not consume |
| ENG-06 | P0 | Add Unity/device visual and performance evidence | Current board/UI/VFX and R4 arm seam match references; actual frame timing recorded |
| ENG-07 | P1 | Versioned level/save schema and RNG snapshot | Deterministic restore or explicit stable-boundary restart policy; migrations tested |
| ENG-08 | P1 | Honor validated moss growth parameters; correct stale L50 note | Effective default behavior preserved; nondefault fields tested; L50 remains44 unless balance approved |
| ENG-09 | P1 | Instrument attempt/progression/economy events | Events deduplicated, schema-valid and reconciled with profile/ledger |
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
Normal failure retry currently reloads in place; tool inventory resets. Campaign reward receipts are memory-only. Moss parameters are partly hardcoded. L50 prose metadata is stale. Demo Shop has no purchase API. Social pages are local snapshots. Official links are empty. Engine-generated settings/signing are absent. All mobile performance/build results are still outstanding. Some gameplay/error strings may bypass localization. No editable 3D model source files exist in the supplied Unity tree.

Do not resolve design questions such as Golden+Golden, new power recipes, new art palettes, live prices or later chapter endings by inventing an answer. Continue with engineering work that is already defined, and bring those specific design choices back to the user.

## Definition of done for a change
Explain the problem, changed paths, resulting behavior and validation scope. Preserve unaffected assets/levels by hash when appropriate. Include a deterministic regression test for transactional/gameplay bugs, or visual/device evidence for rendering changes. Update the corresponding docs and known-gap status. Distinguish passing source tests from passing Unity/device tests. Keep design approval and deployment/store publication separate from code completion.
'''

docs['10_MONETIZATION_STRATEGY.md']=r'''# Monetization strategy — proposed, testable plan
Commercial recommendations, not implemented features or guaranteed results. No actual revenue, retention, payer or acquisition dataset was supplied. Workbook values are illustrative assumptions, not market benchmarks.

## Objective
Optimize long-run **net contribution per acquired player**, while preserving the satisfying match loop and story. Gross sales alone can hide refunds, fees, advertising costs, churn and content expense. Establish retention, reliable state and enough content before scaling acquisition. Fifty levels can be exhausted; treat content supply as a commercial dependency.

## Recommended sequence
| Stage | Revenue design | Why / gate |
| --- | --- | --- |
| Reliability first | No live charging until save/attempt/ledger are durable | Prevent lost purchases, free stock resets and duplicate rewards |
| Initial soft launch | Transparent coin packs and a small bundle ladder | Easy to understand and reconcile; separate Rocket/Bomb and all tool quantities |
| First conversion test | One-time starter bundle after demonstrated engagement | Test eligibility/timing without blocking onboarding; no assumed price optimum |
| Retention/value test | Chapter-themed resource bundles or earned event rewards | Tie value to well restoration/craft/story, not generic pressure |
| Optional ad test | Voluntary rewarded placement outside critical gameplay/cinematics | Measure incremental contribution versus IAP cannibalization and retention |
| Later scale | Real events, team goals, potentially a pass | Only after cadence, backend and content capacity exist |

Avoid forced interstitials in the initial proposal. A voluntary reward should state the exact benefit before the player opts in; no-fill, cancel and failed validation must be clear. Any rewarded extra-move/continue offer needs a new approved mechanic and unified attempt handling; it does not exist now. Cosmetics or a pass need new design review rather than placeholder products.

## Current shop audit
There are 12 mock offers: three Special, three Mega and six coin packs. These are presentation data, not registered SKUs or validated prices. Important inconsistencies:
- Wellkeeper Kit has 2,000 coins plus items for the same displayed $1.99 as the 1,000-coin pack. This can be a deliberate restricted starter offer; unrestricted availability would undermine the coin pack.
- Rainlight Reserve displays 6,000 coins, three of each tool and three of each starting power for $6.99. Village Treasury displays 5,000 coins, two of each tool and three of each starting power for $9.99. Under the current contents/availability, the cheaper offer dominates the more expensive one.
- `boostersEach` and the four starting-power fields need an explicit grant breakdown; do not show Rocket+Bomb as a single reward.
- Hardcoded dollar labels must become store-supplied localized prices. Demo availability does not implement one-time limits, expiry or eligibility.

Before pricing, construct a value ladder using an approved economy. Define offer purpose, comparable item utility, eligibility, repeatability, region, product IDs, actual duration if any and a fallback when unavailable. Discount claims must compare a real reference value. Test different contents/timing independently so the cause of improvement is measurable.

## Economy design
Current first-clear reward is 50 coins +1 star; replay earns no new first-clear reward. Current initial stocks and lives are review defaults, not balanced production grants. Define each resource's use before selling it: coins as soft currency, stars as story/restoration progression if approved, lives as an attempt gate with explicit recovery, starting powers as planned assistance, tools as targeted control. Do not sell stars until their progression role is agreed.

Create a complete faucet/sink ledger: first clears, daily/event/team rewards, purchases and optional ads versus tools, refills, continues and cosmetics that are actually approved. Model per100 attempts and pernew-player cohort. Track free/paid currency separately for analysis, without hiding paid-item value. Tune resource availability against observed use and progression, not arbitrary scarcity. Keep all levels reasonably completable without purchase and never secretly change RNG/difficulty based on spend status.

The workbook's economy sheet proposes example tool/refill/continue costs only to expose balance mechanics. They are **not approved live prices or implemented sinks**. The current code has no complete coin-spend service or life-regeneration service.

## Offers and events in this story
Use restoration supplies, lantern craft, rainlight and the village well as content themes. A real event can reuse approved board/obstacle language with clearly scoped rules, earned progress and a transparent optional bundle. Don't add an event badge with a fake perpetual countdown. First-start story and chapter finales should have uninterrupted emotional pacing. In later tragic chapters, no “save Mila” sale or celebratory purchase framing around her death.

Home already reserves event positions, but current timer/status strings are samples. Proposed rollout: one real recurring event at a time, with server start/end, eligibility, reward claims, fallback, localized strings and support tooling. A pass needs enough reward content and consistent season cadence; do not use a subscription for benefits that do not recur reliably.

## Acquisition and retention economics
Use cohort install date, platform, country, campaign and content/config version. Compare actual net revenue and service cost against acquisition spend. Evaluate D1/D7/D30 retention, level completion/quit curves, session quality, payer conversion, repeat purchase, refund rates and content exhaustion together. High ARPPU with collapsing retention is not evidence of a healthy design.

Scale spend only when mature cohorts support contribution LTV above acquisition cost with an uncertainty margin and sufficient cash runway. The workbook's90-day horizon is not lifetime; linear retention interpolation is a sensitivity tool, not a forecast. Use measured country/platform-specific data and tax/fee treatment. Platform fees are eligibility/territory dependent; 15% is merely an editable example [S7, S8].

## Proposed experiment order
1. Onboarding clarity and first-session completion before offer pressure.
2. Starter-offer timing and eligibility; one variable at a time.
3. Bundle contents/value ladder; eliminate dominated options first.
4. Optional rewarded placement with an IAP/retention holdout.
5. Event participation and earned reward pacing.
6. Acquisition creative based on actual gameplay, then channel/country expansion.

For each experiment pre-register hypothesis, eligible population, primary metric, guardrails, minimum detectable effect/power based on baseline data, duration covering relevant cycles, and analysis date. Do not pick a fixed sample size without variance/base rate. Avoid repeated significance peeking. Report confidence intervals and absolute effects, not only percentage uplift.

## Operating dashboard
Daily: crashes, transaction failures/unacknowledged grants, currency anomalies, stuck levels, content exhaustion, revenue reconciliation. Weekly: cohorts, progression funnels, payer repeat rate, offer conversion, ad incremental value, support/refunds, content production throughput. Monthly: contribution by channel/region/platform, cash costs, experiments and release readiness. Assign an owner to each anomaly and a rollback path.
'''

docs['11_ANALYTICS_AND_EXPERIMENTS.md']=r'''# Analytics and experiment specification — proposed

## Common envelope
Every event should have event_id, schema_version, occurred_at_utc, received_at_utc, pseudonymous_player_id, session_id, app/build version, platform, locale, content_version and config_version. Add experiment_id/variant only after stable assignment. Gameplay adds attempt_id, level_id, level_data_hash and RNG version/seed where diagnostic policy permits. A retry is a new attempt; cascades are not new moves.

Do not send names, chat contents, emails, raw purchase receipts or payment tokens into general analytics. Use redacted ledger references for commerce reconciliation. Apply consent/retention policies appropriate to actual SDK behavior. Keep analytics failure from blocking gameplay or purchase fulfillment.

## Event dictionary
The machine-readable version is `Analytics_Events.csv`.
| Event | Trigger | Essential fields / deduplication |
| --- | --- | --- |
| first_open | First install/profile initialization | install_id; once per install, distinct from returning login |
| session_start | Foreground session boundary | session_id; define inactivity boundary consistently |
| tutorial_step | Stage transition/skip | stage, action, elapsed; transition ID |
| level_start | Start grant committed | attempt_id, level, selected stock, moves, goals; once per attempt |
| level_end | Durable outcome committed | outcome, moves_used, duration, remaining goals, tools_used; once per attempt |
| booster_use | Accepted tool/start debit | item_id, count, attempt_id, transaction_ref; never on mere selection |
| power_activate | Model activation | kind, combo_kind, chain_depth; aggregate/sample if volume is high |
| currency_change | Ledger commit | currency, delta, reason, resulting_balance, ledger_ref; one per ledger entry |
| offer_impression | Offer meaningfully visible | offer_id/version, placement, eligibility; dedupe per visible interval |
| offer_click | Purchase detail/buy intent | offer_id, placement; not a purchase |
| purchase_start | Store flow initiated | product_id, platform, offer_version, request_id |
| purchase_result | Verified state transition | verified_state, ledger_ref, amount/currency/tax basis; distinguish paid/granted/refunded |
| ad_opportunity | Eligible reward placement shown | placement, reward, eligibility; denominator before request |
| ad_result | Request/show/complete/fail/verified reward | opportunity_id, network result, grant_ref; no reward from view alone |
| story_event | Opening/ending viewed/skipped/replayed | chapter, scene, locale, completion; no full story text |
| event_progress | Real event increment/claim | event/version, progress, claim_ref |
| error | Recoverable/fatal classified issue | code, subsystem, diagnostic reference; no sensitive payload |

Purchase revenue should come from the reconciled ledger/store reports, not button clicks or duplicated client callbacks. Server and client events must share correlation IDs, not both count as two purchases. Offline queues keep occurrence time and event ID; receiving a delayed level_end must not create a second attempt.

## Metric definitions
| Metric | Definition |
| --- | --- |
| Dn retention | Install-cohort users active on exact day n / eligible installs; separate rolling retention |
| Win rate | Unique won attempts / ended attempts; also report abandoned/incomplete attempts separately |
| First-attempt win rate | New levels won on attempt1 / new levels started; do not blend retries |
| Payer conversion | Unique verified payers / eligible active users over stated window |
| ARPDAU | Revenue with explicit gross/net basis / DAU, same day and population |
| ARPPU | Revenue / unique payers in the same window; not purchases per payer |
| Offer conversion | Unique verified purchasers attributed to offer / eligible exposed users |
| Ad completion | Completed rewarded views / started views; separately report request fill and opt-in |
| Cohort LTV90 | Cumulative90-day net contribution / cohort installs; horizon is explicit |
| Net ROAS90 | Cumulative90-day net revenue / paid acquisition spend; costs excluded, unlike contribution |
| Payback | Earliest day cumulative contribution covers acquisition spend; no payback if never reached |

## Experiments
Assign by stable player ID and experiment version; persist the assignment. Exclude QA and transaction-fraud traffic by predeclared rules. Keep an unexposed holdout for monetization additions. Segment results by platform/region/progression only where sample size supports it; avoid post-hoc cherry-picking. Refunds, crashes, support complaints and retention are guardrails. Freeze level/config behavior during the experiment or stratify/version it explicitly.

Suggested experiment records are in `Experiment_Backlog.csv`. All proposed treatments require implementation/design review; none is live. Use practical significance and uncertainty, not a revenue uplift claim unsupported by data.
'''

docs['12_MONETIZATION_MODEL_GUIDE.md']=r'''# Monetization model guide
Workbook: `Monetization/Heart_of_the_Rain_Monetization_Model.xlsx`.

All blue input cells are editable. Example assumptions are deliberately not labeled as market benchmarks. Replace them with actual data by platform/country/cohort. Black cells contain local formulas; green formulas reference another sheet. Do not overwrite calculated cells when running a scenario.

## Monthly Model
Inputs include days, average DAU, MAU, payer conversion, average monthly spend per payer, fee/refund rates, rewarded-ad participation/opportunities/fill/net publisher eCPM, service cost, fixed content/operations cost, paid installs and CPI. IAP input is ex-tax player spend before platform fee/refunds. Ad eCPM is publisher-net; it is not charged a second platform IAP fee. Monthly contribution subtracts service cost, fixed operating cost and acquisition spend; it is not audited accounting profit and omits financing/income taxes.

The model assumes MAU payer conversion and ARPPU in the same month. It does not derive MAU from DAU. Ad opportunities are per participating DAU-day; fill is the fraction becoming a paid impression. Do not multiply by opt-in twice. Use net settlement reports to calibrate the simplified refund/fee assumptions.

## Cohort 90d
This is a sensitivity model from Day0 through Day90 inclusive. Retention is piecewise-linear between editable D0/D1/D7/D30/D90 anchors. It is not fitted to real cohorts. A monotonicity/range flag warns about invalid anchors. Per-active-user-day IAP/ad/service rates are separate explicit assumptions; monthly payer conversion is not automatically a daily rate.

Outputs: LTV90 net revenue, LTV90 contribution before acquisition/fixed costs, net ROAS, paid cohort contribution after acquisition, and modeled payback day if any. Shared fee/refund assumptions link to Monthly Model. No extrapolation beyond Day90 is presented as lifetime value. Break-even CPI is contribution per install over the modeled horizon, before fixed costs and uncertainty reserve.

## Economy
The 50-coin first-clear reward is verified in PreLevelAssets. Other daily/level-use/cost inputs are examples for future design. First-clear share means the fraction of wins that are first clears. Gross faucets and sinks are calculated per100 attempts; there is no actual revenue or purchase conversion forecast on this sheet. Tool/refill/continue costs are proposed and not implemented. The estimated levels-to-afford indicator assumes first-clear rewards only and does not predict player behavior.

## Use safely as a decision tool
Run low/base/high cases, zero-ad cases and higher-fee/higher-CPI cases. Watch retention sensitivity: monetization uplift can be erased by churn. Compare mature measured cohorts rather than trusting a single input combination. Keep assumptions, period, geography, currency and source notes with exported results. Numeric targets for launch must be agreed using actual baseline data.
'''

docs['13_SOURCES_AND_PROVENANCE.md']=r'''# Sources, provenance and recovery limits

## Current project evidence
The handoff inventories were generated from the full M67R4 Unity tree. All 4,218 runtime/source/asset/settings files are preserved byte-for-byte in the documentation-enhanced project archive. New documentation is outside Unity/Assets. Baseline ZIP SHA-256 before documentation: `bc03438f4cd16db7c6d4dba2b431bc43487ccf4f8b1a15ff8d75c5a56629dce5` (230,038,585 bytes). New archive hashes are supplied separately.

Current internal README/technical handoffs remain under their original milestone folders. They are indexed, not rewritten to erase history. The code and effective data were used to resolve conflicts; inferred risks and future proposals are labeled. The user's approval history governs design direction but does not turn offline renders into native Unity evidence.

## Recovered original references
| Document | Use | Caution |
| --- | --- | --- |
| 100 Chapter Storybook | Original cast, story continuity, all chapter narratives | Five-level chapter scaffold superseded; app Chapter1 title differs |
| Unity Development Guide | Early architecture/art planning | Engine/version and earlier feature assumptions are historical |
| M34 Design Guide | Board/booster/obstacle design history | Later revisions take precedence |
| M35 Chapter01 50 Level Review | Authored campaign layout history | Current JSON has later obstacle/balance changes |
| M36 Obstacle and Level Review | Obstacle introductions and formations | Later art/rules may supersede |
| M45 Board and Obstacle Review | Later board/obstacle visual review | M48+ adds advanced integration; current move values may differ |
| M48_Start_Here.txt | Recovered current M54 handoff under an older filename | Read document revision, not filename alone |
| M67R4_Start_Here.txt | Latest sleeve/arm revision and validation scope | Native Unity/device review remains outstanding |
| Early_README.md / Early_Technical_Specification.md | Recovered first-project planning notes | Historical; current runtime and user decisions take precedence |
| M66_Level_Complete_Review.txt | Earlier result-flow specification | Victory modal presentation superseded by M67 animation-only flow |

`Original_References_Manifest.csv` records size/hash and source identity. These are all original documents recovered for this handoff, not a claim that every historic upload, video or editable authoring file remains available. Previously missing screenshot paths cannot be reconstructed from their filenames. No new competitor artwork is included or substituted.

## Current external primary sources
Checked 19 October 2026. Policies/SDKs change; recheck when integrating/releasing. These sources inform the proposed production/monetization plan, not claims that the baseline already complies.
| ID | Source | Relevance |
| --- | --- | --- |
| S1 | https://docs.unity.com/en-us/iap/get-started | IAP installation; specific Unity2022.3 Android caveat |
| S2 | https://developer.android.com/google/play/billing/security | Backend verification, purchase state, token dedupe, acknowledgment |
| S3 | https://docs.unity.com/en-us/iap/purchases | Fulfillment, redelivery and consumable history |
| S4 | https://developer.apple.com/app-store/review/guidelines/ | App completeness, payments, user-generated content and store review |
| S5 | https://support.google.com/googleplay/android-developer/answer/10281818 | Google Play Payments policy |
| S6 | https://developer.apple.com/app-store/user-privacy-and-data-use/ | Privacy and tracking requirements |
| S7 | https://developer.apple.com/app-store/small-business-program/ | Apple program-specific fee eligibility |
| S8 | https://support.google.com/googleplay/android-developer/answer/112622 | Google Play service-fee structure |
| S9 | https://docs.unity.com/en-us/iap/restore-purchases | Restoring entitlements |

No competitor revenue, retention, price optimization or proprietary implementation is asserted. Match Villains and Royal Kingdom are creative references from the user, not a license to copy their assets or evidence of their internal engine architecture.
'''

docs['14_APP_PAGE_AND_FLOW_CONTRACTS.md']=r'''# App page and flow contracts
These contracts combine the user's page requirements with current implementation boundaries. Review each page in the connected app, not only its standalone scene.

## Navigation and page state
The five main pages are Journey, Leaderboard, Home, Teams and Shop. Use the shared Home navigation panel/active icon treatment, selected on click/tap. Page transitions should preserve the Home profile and dispose or hide old listeners/views. A modal blocks the underlying page; repeated taps must not launch duplicate views or levels. Current pages are local runtime implementations; network loading/error/pagination states are future service work where noted.

| Page | Player-facing content | Current implementation / next requirement |
| --- | --- | --- |
| Home | Avatar, coins, lives, settings, current chapter background, Start Level with number, event positions | HomeState/preview JSON supplies values; replace demo bootstrap and sample timers with profile/event services |
| Journey | Unlocked chapter opening/ending replay and chapter progress | JourneyCatalog has100 entries and localized story data; only Chapter1 has playable levels; unrevealed art is not finished chapter production |
| Leaderboard: Friends | Friend list, search, add/remove management | Local demo search/pending/removal; needs authenticated friend requests and privacy/error states |
| Leaderboard: Players | Player rankings | Demo snapshots/sorting; needs authoritative ranking and pagination/season context |
| Leaderboard: Teams | Team rankings | Demo snapshots; needs server team score and season handling |
| Teams | Your team, members, chat/mail, help/life requests | Local preview messages/actions; no live messaging or durable life grants; needs moderation/report/block and claim ledger |
| Shop | Special Offers carousel, Mega Offers, coin list | Preview catalog and sliding/swipe layout; no billing. No pagination buttons. Separate Rocket/Bomb rewards |
| App Settings | Music, sound, hints, inventory, language, help/support, follow, Terms/Privacy | Preferences/language persist; inventory is a snapshot; official URLs are empty until configured |

## Pre-level modal
Opened by Home Start Level. Display the level's goal icons/counts, potential first-clear rewards and four independent optional starting items: Rocket, Bomb, Rainbow Orb, Golden Seeker. Replays must not promise another first-clear reward. Show lives in the intended top-left area with adequate clearance; preserve the approved compact panel proportions.

Selecting an item reserves a choice, not a debit. Start checks lives, blocks repeated input and initializes the board. Inventory is consumed only after initialization and actual starting-power placement succeed. If startup fails, show a retryable error and preserve stock. Closing the modal has no life/item charge. The current scene flow implements this in local memory; persistence must make it crash-safe.

## Gameplay settings and exit
The in-game settings control pauses gameplay and offers music/SFX toggles and Exit. Exiting first opens End Level with the life-loss explanation/image and cancel/confirm choices. Cancel resumes the same attempt with no charge. Confirm applies one life loss and opens the retry pre-level modal with Try Again. Retry selection follows the same separate-item stock rules. App settings also exposes hints; avoid assuming every setting appears on both modal variants.

Current confirmed-exit handling is separate from the normal out-of-moves fallback. The latter reloads GameplayScreen directly. ENG-03/04 must unify these outcomes and persistence before release. There is no implemented paid extra-move continuation. Decide interrupted-attempt/life-regeneration policy explicitly rather than deriving it from demo restarts.

## Successful level and chapter completion
HomeLevelFlow validates the active source/level, waits for the model to finish resolving, and settles first-clear rewards locally. Ordinary wins show Daria's celebration overlay with blackened background, not a victory modal. After the overlay/skip, advance to the next pre-level if one exists. A first clear of Chapter1 Level50 runs the chapter-specific finale and routes to the Journey ending. The available campaign caps at50; do not open a fictional Level51.

Replay behavior must not duplicate rewards or first-clear finale flags. The proposed durable receipt should survive app termination before/during/after the animation. Skipping animation skips presentation only, never the reward transaction. The last delivered sleeve correction is shared by ordinary victory and finale.

## First start
The sequence contains Prologue, Chapter, Match, Rocket, Clear, Ready and Complete stages, with narrative animation/background music and three practice-board fixtures. Tutorial progress/settings use the settings store. Story skip leads into practice; practice skipping can complete the sequence. Verify resume/skip on device and in every supported locale. Production boot must distinguish a new profile from a returning player and must not reset progress because the preview scene is opened.

## Locale and accessibility review
Language choices are English, Spanish, French, German and Russian. No Japanese. Changing language should update open content coherently, including story, labels and retry/errors. Preserve reduced-motion behavior and music/SFX preferences across transitions. Check target readability without relying on color alone, button focus/input blocking, safe areas, large counters and long names. Device screenshots are required before a page is declared consistent with its approved design.
'''

for name,body in docs.items():
    (D/name).write_text(body.strip()+'\n',encoding='utf-8')

agents='''# Codex instructions — Heart of the Rain

Scope: the extracted Heart_of_the_Rain project and its documentation.

- Read Codex_Handoff/Documentation/00_START_HERE.md and 01_STATUS_AND_DECISIONS.md before editing. Runtime baseline is M67R4; engine is Unity2022.3.62f3.
- Preserve approved artwork, palette, asset GUIDs, existing level masks and gameplay semantics unless the task explicitly changes them. No broad redesign or automatic engine/SDK upgrade.
- Gameplay is 2D with depth effects. Do not introduce a runtime3D board. Japanese is excluded. Rocket and Bomb remain separate. Golden+Golden has no approved rule.
- Verify the active namespace/caller: live board code is M46, with M48 partials; earlier planners coexist. Current app win flow is HomeLevelFlow plus M67 celebrations, not the old M66 result modal.
- Treat Shop, Leaderboard, Teams and event timers as demo data until services are implemented. Do not claim purchases/social/backend work because a page renders.
- First establish native compile/device baseline, durable profile, unified attempt settlement and persistent inventory. See implementation backlog for acceptance criteria.
- Keep mutations and rewards in model/services, not animation callbacks. Use durable idempotency for purchases, attempts and claims. Never commit credentials or payment tokens to source/docs/logs.
- Use narrow diffs; preserve .meta files. Add meaningful tests for state/transaction bugs and native evidence for rendering fixes. Do not label fake-host/source checks as Unity/device tests.
- Report changed files, behavior, tests and material remaining limitations. Update current docs when a documented gap is actually closed.
- Future design changes are reviewed with the user one page/component at a time. Continue defined engineering work without inventing unresolved art/mechanic choices.
'''
(ROOT/'AGENTS.md').write_text(agents)
(ROOT/'CODEX_START_PROMPT.txt').write_text('''Work on Heart of the Rain using the supplied M67R4 baseline. Read AGENTS.md and Codex_Handoff/Documentation/00_START_HERE.md, 01_STATUS_AND_DECISIONS.md, 03_UNITY_SETUP_AND_ARCHITECTURE.md, and 09_IMPLEMENTATION_BACKLOG.md.

First inspect the actual repository and establish a clean Unity2022.3.62f3 import/compile baseline if Unity is available. Report exact blockers and do not upgrade the engine or redesign assets. The first production milestone is durable profile persistence and migration, followed by unified attempt settlement and persistent booster inventory. Preserve the approved 2D visuals, separate Rocket/Bomb stock, all50 Chapter1 layouts and current celebration.

Implement one reviewable milestone with meaningful state/recovery tests. Keep native Unity/device validation separate from headless checks. Do not activate purchases, deploy a backend, or publish a store build as part of this initial task. Update documentation and report the remaining gaps. Design questions will be reviewed separately with me.
''')

events=[
('first_open','Install/profile initialization','install_id','Once per install'),('session_start','Foreground session boundary','session_id','Once per session'),('tutorial_step','Stage transition or skip','stage;action;elapsed;transition_id','Transition ID'),('level_start','Start grant committed','attempt_id;level_id;config_version;selected_items;moves;goals','Attempt ID'),('level_end','Outcome durably committed','attempt_id;outcome;moves_used;duration;remaining_goals;tools_used','Attempt ID'),('booster_use','Accepted item debit','item_id;count;attempt_id;transaction_ref','Ledger reference'),('power_activate','Model activation','kind;combo_kind;chain_depth;activation_id','Activation ID; consider aggregation'),('currency_change','Wallet ledger commit','currency;delta;reason;balance;ledger_ref','Ledger reference'),('offer_impression','Eligible offer visible','offer_id;version;placement;exposure_id','Visible exposure interval'),('offer_click','Detail or buy intent','offer_id;placement;request_id','Request ID'),('purchase_start','Store flow initiated','product_id;platform;offer_version;request_id','Request ID'),('purchase_result','Verified purchase state transition','verified_state;ledger_ref;amount;currency;tax_basis','Ledger reference plus state'),('ad_opportunity','Eligible reward placement shown','placement;reward;opportunity_id','Opportunity ID'),('ad_result','Ad/result/grant state transition','opportunity_id;result;grant_ref','Opportunity plus state'),('story_event','Scene viewed/skipped/replayed','chapter;scene;locale;completion','View instance'),('event_progress','Progress increment or claim','event_id;version;progress;claim_ref','Claim/transaction ID'),('error','Classified diagnostic issue','code;subsystem;diagnostic_ref','Rate-limited issue fingerprint')]
with (D/'Analytics_Events.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['event','trigger','fields_in_addition_to_common_envelope','deduplication']);w.writerows(events)
experiments=[
('EXP01','Improve first-session understanding','Tutorial pacing/clarity','New players','Tutorial completion and D1 retention','Quit rate;time;errors','Before monetization pressure'),
('EXP02','Present starter value at an appropriate time','Offer eligibility/timing only','Engaged nonpayers','Net contribution per eligible user','D7 retention;refunds;support','Needs durable commerce; actual price approval'),
('EXP03','Improve bundle utility and clarity','Contents ladder','Eligible shop viewers','Verified conversion and contribution','Retention;refunds;coin-pack cannibalization','Fix dominated offers first'),
('EXP04','Optional ads add incremental value','Rewarded placement versus no-ad holdout','Consenting eligible population','Total net contribution per eligible user','IAP;retention;latency;complaints','Needs reward verification and caps'),
('EXP05','Story-themed events improve engagement','One event/reward cadence','Eligible progressed players','D7 engagement and contribution','Content exhaustion;fatigue;support','Needs server event/claim system')]
with (D/'Experiment_Backlog.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['id','hypothesis','treatment','population','primary_measure','guardrails','dependencies']);w.writerows(experiments)

source_ids={'Heart_of_the_Rain_100_Chapter_Storybook.pdf':'libfile_e7b1ecd1db0c81919e415796e61d75c6','Heart_of_the_Rain_Unity_Development_Guide.pdf':'libfile_def3834085688191aae3aa60fc4ce704','Heart_of_the_Rain_M34_Design_Guide.pdf':'libfile_33a118639e5081918b1fa6f1cceeb5ab','Heart_of_the_Rain_M35_Chapter01_50_Level_Review.pdf':'libfile_e2a3eb1691188191b294037836e9588d','Heart_of_the_Rain_M36_Obstacle_and_Level_Review.pdf':'libfile_f25fb361f58c8191bb3035a2ede0b45f','Heart_of_the_Rain_M45_Board_and_Obstacle_Review.pdf':'libfile_08bc69c766508191ab67a87d89926703'}
with (D/'Original_References_Manifest.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['filename','bytes','sha256','source_identity','status'])
    for p in sorted((ROOT/'Originals').iterdir()) if (ROOT/'Originals').exists() else []:
        if p.is_file():w.writerow([p.name,p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest(),source_ids.get(p.name,'Recovered milestone handoff'),'Historical reference; read precedence register'])

# Controlled Markdown rendering: headings, paragraphs, lists, tables, links and inline code.
def inline(s):
    s=html.escape(s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'(https://[^\s<]+)',r'<a href="\1">\1</a>',s)
    return s
def render(body):
    lines=body.splitlines();out=[];i=0
    while i<len(lines):
        s=lines[i].strip()
        if not s:i+=1;continue
        if s.startswith('#'):
            m=re.match(r'(#+) (.*)',s);out.append(f'<h{len(m[1])+1}>{inline(m[2])}</h{len(m[1])+1}>');i+=1;continue
        if s.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                row=lines[i].strip();i+=1
                if re.fullmatch(r'[| :\-]+',row):continue
                rows.append([c.strip() for c in row.strip('|').split('|')])
            out.append('<div class="table-wrap"><table>')
            for j,row in enumerate(rows):out.append('<tr>'+''.join(f'<{"th" if j==0 else "td"}>{inline(c)}</{"th" if j==0 else "td"}>' for c in row)+'</tr>')
            out.append('</table></div>');continue
        if s.startswith('- ') or re.match(r'^\d+\. ',s):
            ordered=bool(re.match(r'^\d+\. ',s));tag='ol' if ordered else 'ul';out.append('<'+tag+'>')
            while i<len(lines) and (re.match(r'^\d+\. ',lines[i].strip()) if ordered else lines[i].strip().startswith('- ')):
                out.append('<li>'+inline(re.sub(r'^(?:- |\d+\. )','',lines[i].strip()))+'</li>');i+=1
            out.append('</'+tag+'>');continue
        para=[s];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','- ')):
            para.append(lines[i].strip());i+=1
        out.append('<p>'+inline(' '.join(para))+'</p>')
    return '\n'.join(out)
toc=''.join(f'<a href="#doc{j}">{html.escape(body.splitlines()[0][2:])}</a>' for j,body in enumerate(docs.values()))
content=''.join(f'<section id="doc{j}">{render(body)}</section>' for j,body in enumerate(docs.values()))
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Heart of the Rain — Development Handoff</title><style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f3ede1;color:#203044;font:16px/1.65 system-ui,sans-serif}nav{position:fixed;inset:0 auto 0 0;width:290px;overflow:auto;padding:28px 22px;background:#22364a;color:white}nav b{display:block;font-size:21px;margin-bottom:22px}nav a{display:block;color:#f3ede1;text-decoration:none;font-size:13px;padding:8px 0;border-bottom:1px solid #4a6078}main{margin-left:290px;padding:48px max(28px,5vw);max-width:1430px}h1{font-size:42px;line-height:1.1}h2{font-size:30px;line-height:1.25;margin:0 0 24px}h3{font-size:21px;margin-top:30px}section{background:#fffdf8;border:1px solid #d3c4ac;border-radius:14px;padding:36px;margin-bottom:32px;scroll-margin-top:20px}p{max-width:85ch}code{background:#e8edf0;padding:2px 5px;border-radius:3px;font-size:.87em;overflow-wrap:anywhere}a{color:#17646c;overflow-wrap:anywhere}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px;margin:16px 0}th{background:#26394d;color:white;text-align:left}th,td{padding:10px 12px;border:1px solid #d9dddf;vertical-align:top}tr:nth-child(odd) td{background:#f5f6f4}li{margin:9px 0}.tag{color:#58717c;font-size:14px}@media(max-width:900px){nav{position:static;width:auto;max-height:320px}main{margin:0;padding:20px}section{padding:22px}h1{font-size:32px}}@media print{nav{display:none}main{margin:0;padding:0}section{border:0;padding:0;break-before:page}a{color:inherit}body{background:white;font-size:10pt}table{font-size:9pt}tr{break-inside:avoid}h2,h3{break-after:avoid}}
</style><nav><b>Heart of the Rain</b>'''+toc+'''</nav><main><p class="tag">CODEX HANDOFF · H1 · 19 OCTOBER 2026</p><h1>Development &amp; monetization handbook</h1><p>Current baseline, production gaps, design continuity and an actionable path to release.</p>'''+content+'''</main></html>'''
(ROOT/'Heart_of_the_Rain_Handbook.html').write_text(page,encoding='utf-8')
(ROOT/'README.txt').write_text('''HEART OF THE RAIN — CODEX HANDOFF H1
Open Heart_of_the_Rain_Handbook.html in a browser, or read Documentation/00_START_HERE.md.
Full project: open the sibling Unity folder in Unity Hub2022.3.62f3.
Original historical PDFs are supplied in the separate Original Reference Documents ZIP.
Monetization workbook inputs are illustrative, not actual financial performance.
The handoff changes documentation only; runtime source and assets remain M67R4.
''')
print('Wrote',len(docs),'documents, handbook, Codex instructions and data templates.')

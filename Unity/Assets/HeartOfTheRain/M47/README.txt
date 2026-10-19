HEART OF THE RAIN / M47 GAMEPLAY UI & FEEDBACK / UI REVISION 11

This milestone adds a gameplay interface and a first audio review to the
approved board, obstacle, power-up and booster assets. All 50 authored Chapter 1
boards are connected to the new scene. Approved tile, obstacle, power-up and booster source PNGs and the corrected
hammer choreography are preserved. R11 applies the selected Ivory & Slate palette
to actual M47 interface sprites, all 50 board surfaces and the courtyard backdrop.

UI REVISION 11 / APPROVED DIRECTION A APPLIED
The permanent gameplay HUD shows the essential labels, icons and counters:
- One closed outer container encloses Moves, Targets and the avatar.
- A continuous border follows the counter area and curves around the avatar.
- The individual panel outlines remain visible inside the shared background.
- Equal 12-unit gaps (halved from 24 units) separate Moves, Targets and the avatar. These spaces
  show the container background; they do not cut the container into pieces.
- Remaining moves: a raised Moves tab and a large, live count.
- Targets: a raised Targets tab above approved obstacle icons and counts.
- Both tabs overlap their panel top edges, matching the supplied examples.
- Avatar: Ivan in his burgundy cloak and steel armor; 180px versus 144px before.
- Moves and Targets panel heights are 120px versus 156px before.
- The target panel supports 2-4 goal families without overlapping the avatar.
- Bottom: four separate slate-navy backings trace each booster button and count badge.
- Each backing has its own pale border; the gaps show the background.
- Approved booster icons, stock badges and the separate settings gear retain their positions.
There is no chapter title, level text, booster heading, booster name or settings
caption. The shared header has one thin edge and a short shadow. There are no
footer dock, metallic frames, individual target wells or modal title ribbons. Warm ivory, slate navy and muted champagne skins use
one subtle edge and a short shadow. Booster targeting retains a brief contextual
instruction; dialogs retain useful action text. The intro no longer shows a level
number. Numeric level identity remains in authored data and the editor.
The interface, board surface colors and background now match Direction A.
All 50 level layouts, board masks, approved item art and gameplay/audio timing
remain unchanged. Package filenames retain R1 for stable replacement/import identities;
this package's UI contents are revision 11.
See Previews/Gameplay_UI_Before_After.png for the previous R10 and the updated R11.

REFERENCE AND DESIGN
The user's image(20261018-072730).png is the latest header reference.
The latest correction requires one enclosing container while maintaining
internal spacing and individual panel outlines. R9 halves both gaps from 24 to
12 units and tightens the outer container from 684 to 660 units. The header stays
centered; individual panels, labels and avatar retain their dimensions.
R10 retains that header and adds a separately drawn contour around each bottom
booster, including its stock-badge lobe. No filled strip connects the four backings.
Current official Royal Match, Royal Kingdom and Match Villains store listings
were also reviewed. Store promotional/minigame imagery is not treated as proof
of the main gameplay HUD. The design applies concise information and recognizable
item silhouettes with original skins. No competitor assets are redistributed.
Documentation/UI_Reference_Review.txt records the sources and specific decisions.
The existing courtyard was regraded with the built-in image tool for subdued
slate-blue lighting and restrained amber highlights. The original scene is retained.
Documentation/UI_Palette.json records the exported color targets.
Previews/Gameplay_Direction_A_R11.png is the current full gameplay preview; it is
rendered from the package assets, not from the earlier concept mockup.

DELIVERED
- 37 editable SVG UI assets and their transparent PNG exports.
- Direction A courtyard background; approved art copied into 24 UI bindings.
- 50 editable board SVGs, generated from canonical cells and original alpha masks.
- HUD with labeled Moves and Targets, 2-4 goals, avatar and four boosters.
- Original Ivan portrait, unmodified; circular UI mask and frame included.
- Normal/selected/disabled booster skins; target focus and low-move feedback.
- Level-intro, tutorial, pause/settings, success and out-of-moves UI states.
- Live Unity text; an English localization key table for production binding.
- 38 original 48 kHz / mono / 16-bit PCM sound cues with an event catalog.
- Four haptic pattern specifications and an integration event (native adapter pending).
- A shared C# feedback timeline synchronized with existing action contacts.
- All 50 unchanged level JSONs and masks, recolored surfaces and a 50-level binding.
- Unity gameplay scene, prefab, UI assets, scripts and editor validation menu.
- Full approved M46 + corrected booster dependencies in the same package.
- Gameplay/UI stills and a 24.5-second four-booster playback with sound.

OPEN IN UNITY
1. Import Heart_of_the_Rain_M47_Gameplay_UI_Feedback_R1.unitypackage into a
   separate 2D review project. Unity 2022.3 / Unity 6 APIs are intended.
2. Ensure Unity UI (com.unity.ugui) is installed. The new Input System and the
   classic input path are supported by conditional compilation.
3. Choose Heart of the Rain > M47 > Open Chapter 1 Gameplay.
4. Set a portrait Game view and press Play. Use Play on the level-goals panel.
5. Swap adjacent tiles; tap a selected power-up again to activate it. Select a
   booster, then its tile/row/column. Atlas activates immediately.
6. Select a starting board with GameplayScreen.initialLevel (1-50) before Play.
7. Run Heart of the Rain > M47 > Validate UI and Chapter Assets.
   A Rebuild Gameplay Scene menu is supplied if serialization needs regeneration.
8. GameplayScreen context menus show tutorial and result panels for UI review.

The new M47 folder supplies its own scene and 50-level binding. Prior M46 and
Booster review scenes retain their original four-level bindings. Importing this
package alongside an older one uses the original GUIDs for shared dependencies.

PREVIEW
Previews/Gameplay_Feedback_Review.mp4 contains four complete, normal-speed booster
scenarios with the new interface and synchronized sound. It is an OFFLINE asset
composition of the actual shared C# pose/feedback streams, not a Unity capture.
The UI geometry and sprite bindings mirror the Unity component; text rasterization
and the edge-glow shader are approximations. Button and counter tweens require Unity review.
Gameplay_UI_States.png shows result screens as UI examples; it does not claim a
level was naturally won. Standalone screenshots use exact authored occupancy.

VALIDATION
The prior gameplay milestone passed 4,105 standalone C# checks, including five
natural moves on each of the
50 boards and shared feedback cue/time checks. This does not establish level
solvability or win-rate balance. Asset bytes, GUID references, audio sample format,
waveform headroom, package integrity and video decoding are checked offline.

LIMITS
Unity Editor import/API compilation/rendering and real phone profiling have NOT
been run. The interface uses approved Direction A in revision 11; the sound cues retain their
first-review status. Audio is synthesized original material, not recorded foley.
No music score, voice-over or native haptic plugin is included.
The haptic event needs a platform adapter; the default is disabled.
The review resets booster stock to three on board load. Inventory persistence,
campaign saves, rewards, purchases and unlock policy belong to the host game.
Golden Seeker acquisition and Golden + Golden remain outside the approved rules.
Storm Crystal, Water Spirit Pod and Rainlight Cabinet retain their separate
milestone assets; their future campaign placement remains provisional.
Full-resolution shared FX remain a review configuration. Selective loading,
texture compression, sprite-cache limits and phone memory profiling are required.

FILES
Unity/Assets/HeartOfTheRain/M47 : new assets and runtime components
Source/UI_SVG                  : editable UI originals
Data/Levels                    : all 50 canonical authored layouts
Documentation                  : handoff, inventory, provenance and text keys
Validation                     : actual checks and preview feedback timelines
Tests                          : reproducible standalone C# checks

The ZIP includes the .unitypackage and all source resources. No external service,
account, monetization setting or application identifier is configured.

M49 integration note: shared boards now introduce Crystal at 21, Pod at 28 and
Cabinet at 36. See ../M48/README.txt. This document otherwise records M47.

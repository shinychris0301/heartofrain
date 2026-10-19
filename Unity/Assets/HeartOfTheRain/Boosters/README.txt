HEART OF THE RAIN — FOUR BOOSTER ANIMATIONS R1 — HAMMER CONTACT REVISION 3

Start with Previews/Booster_Animations_Review.mp4.
Individual MP4s: Hammer_Animation, Axe_Animation, Ram_Animation, Atlas_Animation.
Videos are silent, 720 × 1280 at 30 fps. They use the actual C# board results
and shared animation sampler, composited offline. They are NOT Unity captures.

UNITY REVIEW
Import Heart_of_the_Rain_Booster_Animations_R1.unitypackage.
Open Assets/HeartOfTheRain/Boosters/Scenes/Booster_Animation_Review.unity.
Enter Play. Use Preview Hammer/Axe/Ram/Atlas, Pause, Replay, or Speed 0.5×.
The upper row of booster controls allows manual use on the current board.
Select Hammer/Axe/Ram then tap a cell; Atlas runs immediately.
Four individual review prefabs are also included; use one per review scene.
The supplied review scene is self-contained. No external plugin is required.

SCOPE
Uses the four newly approved transparent booster designs, unchanged.
Reuses approved tile fragments, obstacle tumbling fragments, contact flashes,
and stars. Obstacle fragments remain visible until below the screen.
Animations are authored in board-cell units for changing board dimensions.
The supplied review boards are canonical L10 (9×9), L18 and L40 (9×11),
and L41 (11×11). No Chapter 1 level data was redesigned for this revision.

MECHANICS
Hammer: one cell, one obstacle layer; gems clear and power-ups activate.
Axe: one column, top to bottom, one hit per active cell; voids are skipped.
Ram: one row, left to right, one hit per active cell; voids are skipped.
Atlas: permutes eligible gems and power-ups along curved trajectories.
It preserves piece identities, colors, power-ups, goals, all obstacles and jars.
Delivery jars are immune to direct damage and keep their existing exit rules.
Each successful use consumes one booster, zero moves, and no threat clock tick.
Invalid targeting or a failed legal Atlas permutation preserves inventory.

PACKAGE CONTENTS
Unity/Assets: importable sprites, existing VFX atlases, C# runtime, scene/prefabs.
Source: reproducible metadata builder, headless compiler, review compositor.
Tests: booster behavior checks and playback exporter; Unity math shim is test-only.
Validation: check results, frame draw streams and full board-state traces.
Documentation: technical handoff and source-art checksums.

VALIDATION LIMIT
674 headless behavioral checks passed using the real C# rules/sampler.
Unity Editor import, Unity rendering and on-device profiling were NOT run;
no Unity Editor is installed in this environment. Test those before production.
This is an animation and integration review package, not a mobile release build.

INTENSITY REVISION 2
Stronger front-layer contact flashes, expanding rings, brighter directional
wakes, larger hero poses, and more pronounced hammer rebound/compression.
Atlas adds a larger clockwise light orbit, curved star wakes and landing glints.
A damped board recoil is capped at 0.12 board cells and ends within 0.24 seconds.
The HUD remains stable. Set BoosterReview.boardRecoil=false to disable recoil.
Existing booster designs, level layouts, rules, target scope, contact timestamps,
fragment counts and falling obstacle trajectories remain unchanged.
All four gameplay traces and sampled debris poses match the approved baseline.
The existing package filenames are retained for integration continuity.

HAMMER CONTACT REVISION 3
The hammer now rotates clockwise around a fixed grip pivot. Its steel striking
face lands on the target at 0.80 s, holds until 0.875 s, then rebounds upward.
The rigid sprite uses uniform scale; the handle does not cross the target cell.
The source is unchanged. Grip anchor: (330,875) pixels, top-left origin.
Face-edge anchor: (1031.614286,785.157143) pixels on the 1254x1254 source.
Impact rotation: -45 degrees. Hero scale: 2.95 cells.
The hammer silhouette renders above the contact light so the head remains visible.
Tests independently project the actual PNG silhouette at 120 samples/second;
face alignment, fixed grip, handle clearance and upward rebound all pass.
Axe, Ram and Atlas draw streams and all gameplay traces are unchanged.

Watch Previews/Hammer_Contact_Review.mp4: normal playback, then quarter speed.
The slow segment is sampled at 120 Hz and played at 30 fps, without interpolation.
To regenerate it, run after BoosterChecks:
python3 Source/compile_headless.py HammerGeometry
python3 Source/check_hammer_geometry.py
python3 Source/render_playback.py Hammer
python3 Source/render_playback.py HammerSlow
python3 Source/finish_package.py
Unity Editor import and playback remain untested in this environment.

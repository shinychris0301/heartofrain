HEART OF THE RAIN — FINAL POWER-UP ASSET PACKAGE
M33 / PowerUps_Final_R1

START HERE
1. Import Heart_of_the_Rain_M33_PowerUps_Final_R1.unitypackage into Unity.
   Import all included assets so the existing GUID references remain intact.
2. Choose Heart of the Rain > Power-Ups > Open Playback Gallery.
3. Press Play in the Unity Editor. Use a landscape Game view, ideally 1440 x 1000.
4. Select a sequence in Board playback, or select an atlas and clip in Animation library.
5. Choose Heart of the Rain > Power-Ups > Validate Complete Package to run the
   supplied C# comparison fixtures inside your editor.

The gallery opens an empty review scene with the fully bound prefab. Unity will
offer to save an already modified scene before opening it. You can instead drag
Assets/HeartOfTheRain/Chapter01M07/Prefabs/PowerUpPlaybackGallery.prefab into a
dedicated empty scene. The prefab creates its own orthographic preview camera.

WHAT IS INCLUDED
22 board sequences: six standalone views, fourteen combinations, two chains.
40 active animation atlas pages: 178 clips and 2,330 frames.
Two retained legacy atlas bindings for existing prefab compatibility.
Six approved reference tiles, wood obstacle, stars, colored debris, shaders,
materials, manifests, C# sequence planners and sprite players, and demo prefabs.
All 50 PNG assets from the approved M32 baseline are unchanged.

The standalone views are Bomb, horizontal Rocket, vertical Rocket, Rain Seeker,
Rainbow Orb and Golden Seeker. Super Orb is the formed Double Orb design.
One Golden Seeker creates two Golden Seekers. Each strikes once; arrivals do
not recursively generate additional seekers.

PLAYBACK CONTROLS
Play/Pause, Replay, Previous/Next, scrubbing, backward/forward stepping,
0.25x / 0.5x / 1x / 2x speed, Loop, and Play all.
Board playback provides 9x9, 9x11 and 11x11 layouts plus an obstacle toggle.
Seeker + Rocket combinations also provide a vertical orientation toggle.
The underlying board component accepts dimensions from 3 through 15 per axis.
Play all advances through all 22 board entries. In Animation library it advances
through the clips of the selected atlas. The atlas selector exposes all 40 pages.
Board frame steps are 1/60 second; isolated clips step at their own stored fps.
Selecting a clip and scrubbing does not change the underlying asset.

REVIEW FILES IN THE ZIP
Previews/M33_Approved_PowerUps_Playback.mp4 — all 22 sequences at normal speed,
1440 x 1000, 60 fps, no audio. Composited from the delivered sprites and mirrored
sequence plans; this is not a Unity runtime capture.
Previews/M33_PowerUps_Overview.png — board contact sheet.
Previews/Playback_Timeline.json — precise video section times.
Previews/Gallery_01.jpg through Gallery_22.jpg — individual review stills.
Documentation/Approved_Inventory.json — gallery entries and animation labels.
Documentation/Integration.txt — runtime entry points and gameplay rules.
Validation/Final_Report.json — current checks and execution limitations.
Source/ — Python builders, sequence mirrors, preview renderer and validator.
SHA256SUMS.json — hashes of the packaged payloads.

VALIDATION STATUS
Offline checks passed: 396 board cases, including all 22 entries on three board
sizes, three activation positions, and both obstacle settings. Earlier behavior
is unchanged in 378 cases; 138 legacy and 63 Golden fixtures remain intact.
18 new standalone-bomb fixtures cover center and edge blast clipping.
All C# files passed syntax parsing. Atlas dimensions, clip ranges, importer
limits, prefab references and GUID uniqueness were checked.
The video is fully decoded and the archive payloads are hash-verified.

Unity compilation, the C# fixture gates, Play Mode and mobile device profiling
have not been run: this build environment has no Unity Editor or C# compiler.
Use the included editor validation command after import. The supplied unlit
sprite shaders are intended for an orthographic 2D review; render-pipeline and
editor-version compatibility must be confirmed in the receiving project.

SCOPE
This is the consolidated power-up asset and playback package. The review board
executes deterministic targeting, impacts, destruction, gravity and refill on
a seeded demonstration layout. Connecting those events to the application's
live level state, match solver, scoring and objectives remains an integration
step. See Documentation/Integration.txt for the boundary and entry points.
No installation of UI, Input System, Timeline or Cinemachine packages is needed
by the gallery code; it uses built-in Unity components and IMGUI.

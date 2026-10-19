HEART OF THE RAIN — M46 PLAYABLE BOARD INTEGRATION, R1

This package connects the approved M45 R2 boards and obstacles to the M33
power-up artwork using a deterministic C# board model and a shared presentation
sampler. The artwork has not been redesigned.

DELIVERED
- Four canonical review levels: L10 (9x9), L18 (9x11), L40 (9x11), L41 (11x11).
- Swaps, lines and 2x2 matches, power-up creation, activation and combinations,
  cascades, vertical gravity/refill, goal counting, jar delivery and regrowth.
- Six standalone power-up variants; all 14 approved combination types.
- Six core obstacle families with the approved body states and destruction art.
- Unity scene, prefab, asset bindings, source, tests and review playbacks.

OPEN IN UNITY
1. Import Heart_of_the_Rain_M46_Playable_Board_Integration_R1.unitypackage
   into a separate 2D review project. The source ZIP also contains Unity/Assets.
2. Open Heart of the Rain > M46 > Open Playable Review.
   Scene: Assets/HeartOfTheRain/M46/Scenes/M46_Playable_Review.unity
3. Press Play. Use a portrait Game view (e.g. 720x1280).
4. Drag between adjacent cells, or select one cell and tap its neighbor.
   Tap a selected power-up again to activate it in place.
5. Level buttons, Restart, Pause/Resume, Hint and Play sample are available.
   The six placement buttons are explicitly REVIEW TOOLS. Place one on an
   ordinary gem, then activate or combine it. Placement uses no game move.
6. Run Heart of the Rain > M46 > Validate Assets and Gameplay in the editor.

The serialized review scene and prefab are supplied. A Rebuild Review Scene
menu is also included for regenerating the scene through the Unity API.

REVIEW STATUS
The actual C# logic and choreography compile and execute with .NET 8. The
headless checks pass. Unity is not installed in the authoring environment:
Unity import, Unity API compilation, renderer/input execution, and device
profiling have NOT been performed. Target API baseline: Unity 2022.3 / Unity 6;
compatibility is intended, not certified. Built-in 2D rendering is the first
verification target; URP needs its own material and mask verification.

PLAYBACK
Previews/M46_Playable_Board_Review.mp4 is a captioned highlight edit.
Previews/M46_Level_10_Playback.mp4 and the L18/L40/L41 equivalents are complete
uninterrupted review scenarios. They are offline renders of actual C# draw
commands and board state, not Unity captures. Placement-tool actions are labeled.
No audio has been added. The clips do not establish natural level solvability.

MOBILE NOTE
The reference imports retain original resolution and uncompressed color. The
full review effects library has approximately 1,023.5 MiB of RGBA32 base atlas
texels before body/board textures and runtime overhead. This is a desktop review
configuration, not a mobile release configuration. An optional ASTC 6x6 Android/
iOS preset is included under M46 > Mobile Textures. Use it only for supported
devices and compare its output. It does not resize frames or alter source PNGs.
Plan per-level asset loading, allocation reduction and real device profiling
before a mobile release. See Documentation/Technical_Handoff.txt.

The package retains the original M33 paths and GUIDs. When M33 is already in
an existing project, matching assets are the same approved files. M46 code,
boards, obstacle bindings and scene live in a separate M46 folder. No project
settings, application identifiers, purchases or backend systems are changed.

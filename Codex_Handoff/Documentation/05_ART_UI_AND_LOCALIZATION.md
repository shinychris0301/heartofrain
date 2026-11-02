# Art, UI, animation and localization

## Asset ownership and pipeline

The owner subsequently supplied and requested integration of the M68 celebration assets. Current level/chapter character presentation uses its sampled 2D mesh, raster masters and effect data; the earlier M67 cutout assets remain for history. See `17_FLUIDITY_AND_M68_REVIEW.md` for import provenance, blink-PNG recovery, six native frame comparisons and current playback scope. This does not convert the gameplay board to runtime3D.
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

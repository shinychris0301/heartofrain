# Loading-bar assets, transparent footer and Android deployment

Completed 22 October 2026. Current source/main LDPlayer installation includes the supplied loading-bar skin, checkpoint-41 Launch integration and checkpoint-42 Profile clarity imports.

## Implementation

Package `Heart_of_the_Rain_Loading_Bar_Assets.zip` SHA256: `dc89d7c0c93d9d939a94434be83c904bed026e97c779642e37fd3b15536d0170`. CRC, three PNG hashes/dimensions/alpha, supplied GUIDs and unitypackage payloads pass. Manifest `Artwork/LoadingBar/...` paths are mapped to the actual flat `Artwork/...` directory. Package notes/browser QA are reference guidance, not native evidence.

Three original PNG/meta pairs are added under `App/Launch/Art`: Loading_Track, Loading_Fill, Loading_Frame. Their source bytes/GUIDs remain intact. Import is Single Sprite, PPU400, FullRect, sRGB, Bilinear, no mipmaps, Clamp, uncompressed, max1024. Existing Profile sampling is unchanged.

LaunchPage draws white sliced track/fill/outline layers, outline last. The 240×12 reference composition scales uniformly to 62% of its available portrait region, including the one-unit inset and rounded slice borders. Fill width follows clamped monotonic actual scene progress; zero fill is hidden. Graphics do not receive raycasts. The localized loading label remains separate.

The user's black-background follow-up identified the temporary dark footer rectangle. That plate is now transparent; a small dark text outline provides readability over the illustration. The intentional navy track remains **inside** the rounded gold border. Nothing is drawn behind the bar's exterior corners. No original illustration is edited.

Existing async loading, saved tutorial/Home routing, automatic dismissal and absence of a branding timer/extra start tap are retained. Successful handoff now detaches/releases all three private skin sprites/textures plus the two existing private launch textures. The shared font is retained. LaunchSetup can bind only the new sprites into the existing scene without recreating its other objects.

## Native verification and build

Pinned Unity 2022.3.62f3 compilation/Play Mode passes: **25 progress cases** (0%, 1%, 25%, 72%, 100% at five portrait sizes), five-language fitting, four actual isolated scene handoffs and **19 inspected camera-rendered captures**. The report records 685 checks, including repeated readiness observations. Checks cover PPU/sampling, sliced/white/noninteractive layers, exact fill width, 20:1 aspect, zero hiding, outline order, transparent footer and private-texture cleanup. Tutorial stage/wallet/inventory remain unchanged in memory fixtures. Layout bars use explicit review progress values, not startup timings; safe-area inset checks remain geometry simulations.

The ARM64 IL2CPP Development APK builds with zero errors and two existing unused-field warnings. The installed SDK is reused with process-local Java repository-access settings; no engine/SDK upgrade, target change or persistent proxy configuration occurs. PlayerSettings are restored byte-for-byte, and all **4,636** frozen inputs match after building.

APK: `Unity/Builds/Verification/HeartOfTheRain_Development.apk`

- Package: `com.heartoftherain.verification`
- Bytes: **260,411,400**
- SHA256: `76ef75d321031aa0ac499879ff8d3113e936535d12b37692336b892fffa19eb6`
- ZIP CRC, development signature, ZIP4KiB alignment and ELF16KiB load-segment checks pass.

## LDPlayer installation and observation

Replacement install (`adb install -r`) succeeds on main **127.0.0.1:5555**, without uninstall or data clearing. The installed APK SHA matches the build. Preference and campaign/economy JSON hashes match before install, after install and after startup/Profile checks. Saved Raindrop/Gold appearance and actual level1/chapter1/progress0of50/stars0 are visible; no appearance choice was changed.

An actual startup recording shows the revised bar directly over the artwork, without the footer plate, then Home. The recorder began on a landscape display and embeds the portrait app in a 1600×900 video canvas: its black **side margins** are recording letterboxing, not the app's layout or loading-bar background. The selected startup image is a decoded compressed video frame. Direct Home/Profile/Stats captures are original **900×1600** framebuffer PNGs.

The Play Store briefly became foreground during initial observation. Our installation succeeded and process stayed alive; no taps were sent to the other app. Heart of the Rain was brought back, and subsequent Profile/Stats/close taps were foreground guarded. The initial strict foreground check is not counted as a successful observation. Final checks find no selected fatal, null/missing-reference or launch-error signatures. The app is left on Home. The QA LDPlayer stays stopped and unchanged.

Home and Stats `dumpsys meminfo` samples are retained as read-only observations, not peak-memory/device-budget approval. This is targeted startup/rendering verification, not FPS, exhaustive input/gameplay, every Profile option or physical-device certification.

## Files and evidence

Existing production files: LaunchPage.cs, LaunchLayout.cs, LaunchSetup.cs and Launch.unity bindings. New assets: three original PNG/meta pairs. Existing LaunchReview adds the loading-bar mode/checks; the wrapper adds configure/review modes/freshness guards. The current collector, handoff status and evidence are updated. Existing Profile runtime/import corrections, Home header/Level button, portrait policy, saved IDs and gameplay semantics are preserved.

Gallery: `Verification/Evidence/LoadingBar/Comparison.html`. Package checks, source snapshot, native report/process, build/artifact reports, installation/save hashes and reviewed image hashes retain the exact scopes. Current collector validates source → native report → APK → installed identity.

Remaining release work: mobile compression, peak-memory/FPS evaluation, physical devices/safe areas, adaptive icon artwork/exports and a larger approved launch master. Targeted Android visual evidence here narrows the prior device gap; it does not certify all 50 levels or production services.

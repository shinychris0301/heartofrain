# Launch Design R1 — Unity integration

Source checkpoint, 22 October 2026 UTC. The supplied launch art is integrated ahead of the unchanged first-start game scene. The deployed APK remains checkpoint 39; this task does not rebuild or install Android.

## Behavior and assets

`App/Launch/Scenes/Launch.unity` is first in Editor Build Settings. The development APK builder now includes Launch followed by the original `M65_First_Start.unity`. The original game scene and serialized references are unchanged.

`LaunchPage` renders the supplied key art and independent transparent title, shields input, then starts the original game scene with `SceneManager.LoadSceneAsync`. It survives that single-scene transition until `FirstStartPage.Initialized` signals that the existing tutorial/Home route is ready and visible. It then removes itself automatically, with no branding timer or extra start tap. Launch progress follows the actual scene operation, stays below completion until routing is ready and never advances on a timer. Unity may report scene progress in large steps; this implementation does not turn that into a fabricated smooth percentage. See [Unity 2022.3 progress semantics](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/AsyncOperation-progress.html).

The FirstStart change only exposes its initialization completion and adds an Editor-only memory-store injection for native verification. Existing session rules, saved keys, skip/continue behavior, lessons and production preference adapter are retained. Runtime launch code does not mutate saves, rewards, inventory, attempts, appearance or tutorial state. Profile recovery stays in the existing Home flow.

The original three PNG byte streams are imported under `App/Launch/Art`, with new GUIDs. Existing artwork/metadata are unchanged. The existing licensed Profile font is reused. New textures retain their supplied dimensions, sRGB, bilinear/clamp, no mipmaps and no CPU readability; they are uncompressed reference imports at max 2048. No new detail, high-resolution master, character animation or adaptive cutouts were generated.

Android legacy icon slots use the exact supplied opaque icon. Adaptive and round-specific artwork is not supplied or invented. Installed launcher appearance and Android packaging are not verified by this source checkpoint.

Phone illustration uses centered cover; wider portrait layouts preserve the full portrait with a static dark-blue matte at the sides. The title keeps its 2:1 aspect. Title and live loading footer use the intersection of the artwork region and runtime safe area, with localized fitting for English, Spanish, French, German and Russian. The UI has no runtime blur, particle effects or animated loading delay, and remains static under reduced-motion preferences. The existing native Unity splash and portrait-only policy remain intact.

After successful handoff, the controller detaches and explicitly unloads its two private launch textures without forcing a full `UnloadUnusedAssets`/GC scan while Home becomes interactive. It retains the shared font. See [Unity 2022.3 texture asset unloading](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Resources.UnloadAsset.html). Native verification confirms that neither named launch texture remains loaded after each tested handoff. This is not a full memory profiler result.

If the game scene is unavailable or the initialized route never becomes visible, the launch page shows localized restart guidance rather than completing a fake progress animation. The target scene is checked during configuration and native verification; the error state itself has not been fault-injected in this checkpoint.

## Native verification

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Verification/Run-UnityVerification.ps1 -Mode LaunchReview -TimeoutMinutes 8
.venv/Scripts/python.exe -X utf8 Verification/Tools/collect_results.py
```

Pinned Unity 2022.3.62f3 compilation and actual Play Mode scene transitions pass. Native UGUI review covers 393×852, 320×480, 768×1024, 900×2000 and 320×568, each in all five supported languages: 25 layout cases. English and Russian captures at each size provide ten launch frames. Additional geometry checks simulate top/bottom safe-area insets; these are not device cutout captures.

Four real asynchronous launch-to-game transitions use isolated memory campaign, tutorial and appearance stores:

| Case | Result |
| --- | --- |
| Fresh profile, tutorial stage 0 | Original Prologue visible, Home hidden |
| Saved tutorial stage 3 | Original Rocket lesson resumes, Home hidden |
| Ten first clears | Home at Level 11; tutorial bypassed |
| Tutorial marked complete with no first clear | Home at Level 1; tutorial bypassed |

For every transition, the launch root/textures release, tutorial initialization does not write stage keys, inventory/progression/reward state remains unchanged, and ordinary appearance/tutorial PlayerPrefs values remain unchanged. Authority services are injected as unavailable for these tests; campaign/appearance/tutorial fixtures remain in memory. These checks do not test interrupted-attempt settlement or backend claims again.

All 14 native camera-rendered captures are inspected and hashed in `Visual_Review.json`. Layout screenshots use an explicit 40% review fixture; they are not startup timing captures. Handoff captures show actual fixture routing after the existing fade finishes. The first interrupted verification run exposed a review-harness initial-scene callback error, which was corrected before final passing runs; it is not presented as a runtime test pass.

## Changed files and limits

- New `App/Launch` runtime, editor configuration, scene, three original PNGs and metadata.
- `FirstStartPage.cs`: initialization signal plus Editor-only tutorial-store injection.
- `NativeAndroidBuild.cs`: launch/game scene ordering.
- `EditorBuildSettings.asset` and `ProjectSettings.asset`: first scene and six legacy icon bindings; no engine/SDK/orientation upgrade.
- `Verification/Editor/LaunchReview.cs`, wrapper modes/validation, current evidence collector and handoff documentation.

`LaunchSetup.Configure` is a deliberate initial configuration command, not an automatic startup hook. It recreates the generated launch scene from the three source textures and sets the build/icon bindings. Do not run it to reset authored scene edits without reviewing them.

Evidence/gallery: `Verification/Evidence/LaunchIntegration/Comparison.html`. `Source_SHA256.json` freezes the reviewed inputs; `Verification_Summary.json` distinguishes current source from the unchanged installed APK. Prior package review is checkpoint 40; prior deployment is checkpoint 39.

Remaining production work: higher-resolution opening master for high-density targets, approved adaptive icon layers/platform exports, Android build/install/launcher verification, physical-device safe areas, compression and startup/peak-memory profiling. The exact supplied 941×1672 master is retained. No claim of store readiness, physical-device performance or whole-project regression is made.

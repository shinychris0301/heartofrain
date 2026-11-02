# Portrait orientation — 20 October 2026

The owner requested portrait-only presentation across device aspect ratios, using installed Match Villains as the orientation reference. Engine remains Unity 2022.3.62f3; the Android SDK target and gameplay/art assets are unchanged.

## Cause and reference

The previous Player Settings used Auto Rotation with all four orientations enabled. Its compiled Android activity requested `fullUser`. The only runtime portrait request was inside gameplay startup, so Home and the initial story could use landscape before gameplay existed.

On original LDPlayer instance 0, with its physical display still 1600 by 900, the preceding APK rendered Home at 1600 by 900. Launching Match Villains on the same device produced a 900 by 1600 portrait surface. Read-only inspection of installed Match Villains 7307 showed its primary Unity activity declares `portrait` and the application declares category `game`. Reference captures and manifest findings are in `Verification/Evidence/Portrait`; no competitor gameplay action, purchase or account reset was performed for this review.

## Changes

- `Unity/ProjectSettings/ProjectSettings.asset`: default Portrait, with both landscape variants and upside-down portrait disabled. Only these four settings changed from the preceding APK configuration.
- `App/Home/Runtime/AppOrientation.cs`: applies the same mobile policy before the splash/first scene and when focus returns. It does not poll every frame or change the canvas size, resolution, artwork, rewards or model state.
- `App/Home/Editor/PortraitBuildPolicy.cs`: rejects Android/iOS builds that permit other orientations. The Android postprocessor validates Unity's generated portrait activity and adds `android:appCategory="game"`, preserving its permissions, activity metadata and existing resizability setting.
- `Verification/Editor/PortraitVerification.cs`, the batch wrapper and `Verification/Tools/check_portrait_device.py`: native policy/manifest checks, actual device launches, page input, requested rotations, resume and display-profile restoration. Collection tools and current handoff references select the new evidence branch.

The game category matters on newer Android large screens: Android's documented orientation exceptions include games classified with this flag. This is the supported game classification, rather than a temporary resizability opt-out. OEM compatibility overrides and real Android 16/17 devices still need device validation. [Android 16 behavior](https://developer.android.com/about/versions/16/behavior-changes-16), [Android 17 exceptions](https://developer.android.com/about/versions/17/changes/ff-restrictions-ignored), [OEM compatibility overrides](https://developer.android.com/guide/practices/device-compatibility-mode).

The early runtime hook is supported by the pinned engine. [Unity 2022.3 BeforeSplashScreen](https://docs.unity3d.com/2022.3/Documentation/ScriptReference/RuntimeInitializeLoadType.BeforeSplashScreen.html).

## Verification

Eighteen native portrait policy/manifest checks pass, along with 530 general native checks and nine connected launch/exit smoke checks. The compiled APK declares portrait (Android enum 1) and game category (enum 0); package signature, ZIP CRC/alignment and static ELF checks pass.

The QA emulator passed 24 reviewed cases across physical/temporary profiles 900 by 1600, 1080 by 2400, 1200 by 1920 and 1920 by 1200. Each covers Home, pre-level, gameplay, two rotation preferences and background/resume. The wide tablet profile produced a 1200 by 1920 portrait surface. Returning to the app shows its existing pause/settings modal in portrait, with the move count unchanged. All temporary display and rotation settings were restored in the test's `finally` block. See `DeviceMatrix/Report.json`, `Device_Matrix_Review.png` and `Rotation_Resume_Review.png`.

All 125 pre-existing non-Editor C# files match the preceding gravity checkpoint byte for byte. Only the new orientation bootstrap extends the runtime set to 126 files. Current model, artwork, asset GUIDs, level masks, power rules and celebration/Home flow are preserved.

Android rendering evidence uses LDPlayer with ARM translation. Physical sensors, real Android 16/17 tablets/OEM overrides, foldables and iOS remain unverified. Existing durable profile/inventory/services, human balance and heavy-combo frame-budget gaps are not closed by an orientation change.

## Final APK and original-device result

The final ARM64 development APK passed **1,685 Android checks**, **419 programmatic actions**, all **50 boards**, **354 effect samples** and five recorded connected campaign clears on original LDPlayer instance 0, whose physical display remains 1600 by 900 with no size override. All **272 unique native suite captures** are 900 by 1600 portrait, including story, lessons, Home, gameplay, settings, victory and chapter-finale pages. Representative story/tutorial/victory frames were visually inspected in addition to the profile matrix.

APK: `Unity/Builds/Verification/HeartOfTheRain_Development.apk`, **200,808,007 bytes**, SHA-256 `17e895cd344f8bcbacce0140e23eab86e2606c65efb3860f00b8b65ae8674c4d`. The native build completed with zero errors and one warning. Both original and QA instances have this exact installed APK and return to normal portrait Home. The original installation/launch interval preserved shared-preference file hashes; no data clear or uninstall was used. This is narrower than durable campaign/inventory certification.

`Comparison.html` shows the actual before/after on the same original emulator and the installed reference. `Frame_Manifest.json`, `DeviceMatrix/Report.json`, final installation reports and `Player_Source_SHA256.json` identify the evidence. Current summary/coverage collectors select `Portrait`, while previous gameplay/performance evidence remains historical. No fresh frame-budget improvement is claimed.

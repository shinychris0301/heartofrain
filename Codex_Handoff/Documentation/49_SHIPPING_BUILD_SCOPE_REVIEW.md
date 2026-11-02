# Shipping build scope review — checkpoint 49

22 October 2026. Unity 2022.3.62f3. Evidence: `Verification/Evidence/Native` (`Native_Checks.json`, `Play_Smoke.json`, `Android_Release_Build.json` and their process records).

The shipping build now contains only the two scenes the runtime loads, and the four review/QA scripts that used to compile into every player are compiled for the Editor and development builds only. A non-development ARM64 IL2CPP build proves the release compile with those scripts excluded. Nothing in the live gameplay, app flow, artwork or saves changes; the review scenes and tools stay available in the Editor.

## Cause

Eighteen scenes were enabled in Build Settings: `Launch`, `M65_First_Start`, eleven `*_Review` scenes, `M48_Chapter01_Review`, `M56_Home_PreLevel` and the superseded M66 Level Complete pair. The runtime loads only `M65_First_Start` from `LaunchPage`; everything else was packaged for nothing and exposed review entry points. `GameplayReviewTools` (with its `GameplayManualPlaytest` and `GameplayReplayController` partials) and `M46Playground` carried no `#if` guard, so the review drawer, manual playtest ledger, campaign replay and the M46 playground compiled into release players.

## Changes

- `ProjectSettings/EditorBuildSettings.asset`: the sixteen review scenes are disabled, not removed, so Editor workflows and the `Configure Review Project` menu keep their list; `Launch` (index 0) and `M65_First_Start` remain enabled. The verification APK already named only these two scenes explicitly; the Editor's own Build Settings now agree.
- `M48/Runtime/GameplayReviewTools.cs`, `GameplayManualPlaytest.cs`, `GameplayReplayController.cs`, `M46/Runtime/M46Playground.cs`: whole-file `#if UNITY_EDITOR || DEVELOPMENT_BUILD` guards. No other runtime script references the types they declare (`GameplayReviewTools`, `ReviewSample`, `DeviceReviewReport`, `M46Playground`); the Editor menus and recording tools that do are Editor-only. The pure M48 helpers (`ReviewLayoutPure`, `ManualPlaytestPure`, `CampaignReplayPure`, `CampaignValidationPure`, `DevicePreflightPure`, `EffectResourcesPure`) stay unguarded because live code uses them.
- `Verification/Editor/NativeVerification.cs`: a general check requires that the enabled build scenes are exactly `Launch` and `M65_First_Start` and that the eighteen entries remain listed.
- `Verification/Editor/NativeAndroidBuild.cs`: `RunRelease` builds the same two scenes without `BuildOptions.Development`, so `DEVELOPMENT_BUILD` is undefined and every guarded script must compile out. It writes `Android_Release_Build.json` and `Builds/Verification/HeartOfTheRain_ReleaseCompile.apk`; identifier, signing and player settings handling are shared with the development build and restored afterwards.
- `Verification/Run-UnityVerification.ps1`: new `AndroidReleaseBuild` mode with the same artifact and freshness validation as `AndroidBuild`.

## Native verification

| Suite | Result | Before |
| --- | --- | ---: |
| General Editor checks (`-Mode Checks`) | 532 / 532, including the build-settings case | 531 / 531 |
| Connected Play Mode smoke (`-Mode PlaySmoke`) | 13 / 13 with the guarded scripts present in the Editor | 13 / 13 |
| Non-development Android build (`-Mode AndroidReleaseBuild`) | `PASS_ANDROID_RELEASE_COMPILE_BUILD`: 0 errors, 2 warnings (the two existing unused-field warnings), 228,609,079-byte APK, 3 min 53 s | not available |

The development APK of checkpoint 45 is 260,521,584 bytes; the release-compile APK is 31.9 MB smaller, mostly the development runtime and debugging support rather than the excluded scripts. `PlayerSettings`/`ProjectSettings.asset` are unchanged after the build.

## Remaining limits

- The release-compile APK uses the internal verification identifier and development signing; it is a compile proof, not a store candidate, and it was not installed or run on a device.
- The legacy `Chapter01M04/05/07` review scripts, the Editor-only `App/*/Editor` validators and the `Verification` runtime probes were already Editor/development-only or unreferenced by the shipping scenes; they are not changed here.
- `Inventories/Scene_Index.csv` still lists the pre-trim enabled flags; refresh it with the next inventory regeneration.

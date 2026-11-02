# Updated Android APK — LDPlayer installation

21 October 2026 local review; build/install reports use 22 October UTC.

At the owner's request, checkpoint 36 was rebuilt with pinned Unity 2022.3.62f3 as the existing internal ARM64 IL2CPP development APK. No runtime code, assets, dependencies, engine or project settings changed during this step. All 4,577 verified source/configuration hashes still match checkpoint 36; the PlayerSettings file is byte-identical to its pre-build copy.

Artifact: `Unity/Builds/Verification/HeartOfTheRain_Development.apk`, 229,997,302 bytes, SHA256 `e9309dde06f86031057f981120ad2e92be29b14d738f53c41c57f06d6afb3cc0`. Package identifier remains `com.heartoftherain.verification`. The build succeeds with zero errors and two existing unused-field warnings (`ProfilePage.prepared`, `HomeButtonFeedback.selected`). ZIP CRC, development signature, 4 KiB ZIP alignment and 16 KiB ELF load-segment checks pass. This is an internal development build, not a store release.

The active main LDPlayer instance, `127.0.0.1:5555`, received an `adb install -r` replacement without uninstall or data clearing. Its installed APK hash matches the local artifact. Preference and campaign/economy file hashes are identical before and immediately after installation, and at the initial launch check. The stopped QA instance was not started or updated.

Actual emulator screenshots show a portrait 900×1600 Home screen with the revised Chapter 1 background, Level 1 label and independent avatar header. Profile opens, renders its chrome, blurred background and live saved stats, and closes back to Home. Initial automated tap sequencing required retry; this observation is not a latency or responsiveness measurement. The app remains running on Home in the main instance, with no fatal signatures detected for its PID.

The optional Profile interaction persisted the unchanged default Ivan/Gold/Village/Rainkeeper appearance in the new `HeartOfTheRain.Profile.v1` preference key. After that interaction, omitting only that new line in memory reproduces the exact original preference-file hash; all existing preference bytes and campaign/economy JSON hashes remain unchanged. No preference file was manually edited, and no rewards, inventory or progress were changed by the check.

Evidence is `Verification/Evidence/HomeHeaderAndroid`: frozen source manifest, build/process and APK reports, `Main_Installation.json`, four inspected original ADB screencaps and `Visual_Review.json`. The gallery is `Comparison.html`. `Verification/Tools/collect_home_header_android_results.py` verifies source/artifact/install bindings and selects this deployment checkpoint through the general collector. Earlier source galleries keep their historical pre-install scope.

This closes the requested rebuild and installation on the active LDPlayer. It does not rerun the whole campaign, validate every Profile choice on Android, certify physical devices or activate production backend services.

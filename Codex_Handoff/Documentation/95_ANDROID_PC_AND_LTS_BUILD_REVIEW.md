# 95 — Android PC testing and isolated LTS build review

Status: **Scoped PC Android testing recorded; Unity6 Android build remains blocked.**

The owner approved Android testing on the PC. This follow-up uses the accepted checkpoint93 development APK on LDPlayer and separately prepares a stock Unity 6 LTS environment. The main project remains Unity **2022.3.62f3**; neither the isolated candidate nor the backend replay worker has been promoted.

## Accepted Android APK on LDPlayer

The checkpoint93 APK was replacement-installed on the proved LDPlayer index0 using `install -r`. The actual update passed its installed-APK hash, complete external-file/preference preservation, inactive-attempt and other-package checks. No package was cleared or uninstalled. The original saved progression at the update boundary remained 1,250 coins, five lives, Level 1, zero completed levels and no active attempt.

- APK: `Unity/Builds/Verification/HeartOfTheRain_Development.apk`.
- SHA256: `e4bb5d8cf99ebcbb805d14e8f167c0e245bcef585903bdcc69724a9748b422ac`; 331,223,027 bytes.
- Package: `com.heartoftherain.verification`; ARM64 development build, version code 1, minimum API **22**, target API **36**.
- **The Unity2022 splash remains enabled in this APK.** The API26 baseline and disabled splash belong to the unaccepted isolated Unity6 candidate, not this installed artifact.

Actual update evidence: [Update.json](../../Verification/Evidence/AndroidTesting95/Runs/7f111cb1abad440586fae46d51327bd9/Update.json). Its source/build/static proofs bind the existing 5,407-input checkpoint93 baseline; this was not a new APK build.

After the separately recorded recovery below, root reviewed the ordinary Russian Home OS capture at **900×1600**: 1,250 coins, five of five lives and Level 1. It fills the captured display with no obvious top band or overflow in that image. The selected PID-log error signatures total zero; durable data and current source proofs match. The read-only observation receipt retains its original `rootVisualReviewCompleted: false`; the later root visual review is recorded separately without rewriting that receipt. See [Observation Set02](../../Verification/Evidence/AndroidTesting95/Observation/Set02/Observation.json) and [VisualReview.json](../../Verification/Evidence/AndroidTesting95/VisualReview.json).

## Native regression and separate preservation recovery

The actual Android native regression passed **1,716 checks, 50 boards, 408 actions and 354 clips**, with no native failures. These accelerated transient fixtures ran on the original emulator boot. They are distinct from a manual 50-level campaign, live services or performance certification.

The host wrapper remains **`BLOCKED_ACCEPTED93_LD_REGRESSION95_PRESERVATION`** because its subsequent preservation/cleanup sequence timed out. That result is retained; the native pass does not turn the wrapper into a pass. Evidence: [original Invocation.json](../../Verification/Evidence/AndroidTesting95/Regression/d95f33d790114d0baceb3bd219c22e62/Invocation.json).

After ADB became unresponsive, a different emulator boot identity was observed. Root selected reconnect only; this workflow issued no VM reboot command. The cause of the boot change is unproven. A separate read-only post-boot inspection passed, followed by a separate preservation-recovery pass and normal app relaunch. All ordinary profile files, nested authority files, preferences and the installed APK match the pre-fixture preservation baseline; there is no active attempt or pending marker. This establishes ordinary saved-state recovery on the later boot, not a new regression run or an amended original wrapper result.

The later read-only health observation reports both `ro.boot.bootreason` and `sys.boot.reason` as `reboot`, boot completion as `1`, and zero parsed package exit-reason records. Those properties do not establish the cause of the earlier boot change. See [PostBootHealth/Set01](../../Verification/Evidence/AndroidTesting95/PostBootHealth/Set01/Report.json).

Evidence: [post-boot inspection](../../Verification/Evidence/AndroidTesting95/PostBootRecovery/e54205ddf8d44c109dbe5f4ff6265b09/Recovery.json) and [separate preservation recovery](../../Verification/Evidence/AndroidTesting95/PostBootRecovery/563cd2f8d27f4b6a8c40ec2994af504c/Recovery.json).

Root also inspected four selected native-camera images from the original regression: the English gameplay HUD, fixture Level 50 reward Home, a power-effect pose and a stacked-obstacle diagonal-fall pose. These static captures show no obvious clipping or black gap within their selected scope. They are not Android OS screenshots, owner-save progress or animation timing proof. The [gallery](../../Verification/Evidence/AndroidTesting95/Comparison.html) publishes exactly five byte-identical image copies: those four plus the ordinary Home OS image. Remaining raw evidence stays private.

## Isolated Unity6 Android build

The fresh Unity **6000.6.6f1** Android development attempt failed. Windows Application Control still rejects `Bee.VisualStudioSolution.dll` with **0x800711C7**; the original and portable-loader checks did not yield an accepted Android build. No Windows protection, trust policy or vendor binary was weakened. The actual failed invocation remains [AndroidFollowup95/BuildDevelopment/Set01](../../Verification/Evidence/Unity6Migration94/AndroidFollowup95/BuildDevelopment/Set01/Invocation.json); earlier findings remain in [checkpoint94](94_ISOLATED_UNITY6_SPLASH_REVIEW.md).

The official Unity **6000.3.27f1 LTS** Editor installer is complete and verified: **4,235,893,440 bytes**, MD5 `7b9412b4f0970814daf1ab6469944836`, SHA256 `15236d7dbe692ee683cc06e31d5f708ab15439a5c5e8cd5ff5edd82a24434055`, and a **Valid Unity Technologies Authenticode signature**. Ordinary stock installation subsequently passed to `E:/HeartRainUnity6LTS95/6000.3.27f1`; the installed product version is `6000.3.27f1_672d562a42a7`. Evidence: [verified installer](../../Verification/Evidence/Unity6LTS95/OfficialDownloads/VerifiedSegmentedSet01/Report.json) and [Installation/Set02](../../Verification/Evidence/Unity6LTS95/Installation/Set02/Report.json).

The installation receipt's initial `coreLoaderReady: false` came from a diagnostic that incorrectly assumed the Unity6.6 frontend/runtime layout. It was not itself an application-control finding. The subsequent probe used the actual stock Unity6.3 `netcorerun` route and was blocked loading **`NiceIO.dll` with 0x800711C7**. This is a loader diagnostic, not an Android build. The exact Windows policy responsible is not established here; no security-policy change or preference-fingerprint acceptance is claimed. Evidence: [CoreLoaderStock/Set01](../../Verification/Evidence/Unity6LTS95/CoreLoaderStock/Set01/Report.json).

No Unity6.3 Android module download/install, Android smoke build, full-game copy/build or APK followed that block. Android-component download, build and separate-package LD installation tools are prepared only. **No Unity6 APK has been accepted or installed, and no main-project promotion occurred.**

## Remaining acceptance gates

1. Retain the original blocked wrapper and separate successful saved-state recovery. A future fully successful regression/preservation chain must use fresh evidence; the current native pass remains tied to its original boot.
2. Obtain an administrator-approved compatible build environment or vendor resolution for the Unity loader block. Then install matching Android components and pass a real minimal Android smoke build before preparing or building the isolated full game. No security bypass is proposed.
3. Obtain a source-bound full-game development APK, perform static inspection, and test its separate package without replacing the accepted owner app. Record real splash absence and first-time/returning routes.
4. Complete ordinary gameplay, UI/lifecycle and performance checks. Existing Account clipboard failures, smoothness concerns and broader device/campaign gaps remain open.
5. Complete configured hosting, account/payment/ad-provider, release signing, legal and moderation acceptance. No live-provider, production-readiness or launch approval follows from this PC test.

The updater's 17 synthetic host guards pass separately from Android evidence: [HostControls/Set01](../../Verification/Evidence/AndroidTesting95/HostControls/Set01/Report.json). The new Android-component downloader's 14 host controls also pass without any real network/download/installer execution: [ComponentDownloadSet01](../../Verification/Evidence/Unity6LTS95/HostControls/ComponentDownloadSet01/Report.json). Backend source is protected; historical backend test counts are not relabelled as new Android or Unity6 integration tests.

The [final protected-source audit](../../Verification/Evidence/Unity6LTS95/ProtectedSourcesFinal95.json) passes: all 5,407 main Unity inputs and 95 tracked backend inputs are unchanged, with no Editor process remaining. [Privacy Set02](../../Verification/Evidence/Unity6Migration94/Privacy/Set02/Receipt.json) preserves all 80 raw logs and publishes separately bound sanitized derivatives; 40 logs required redaction. Private originals remain immutable and are not replaced by the public derivatives.

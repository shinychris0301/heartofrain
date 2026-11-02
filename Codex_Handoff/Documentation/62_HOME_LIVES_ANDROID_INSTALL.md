# Home Lives Android rebuild and LDPlayer installation

23 October 2026. Deployment checkpoint 62 installs the unchanged source from checkpoint 61 on the active main LDPlayer (`emulator-5554`). No runtime, artwork, metadata, settings or economy changes were needed.

Unity 2022.3.62f3 built the ARM64 development APK with zero errors and two existing unused-field warnings (`ProfilePage.prepared`, `HomeButtonFeedback.selected`). Clean Gradle repackaging retained all 1,058 nonsignature entries and the signing certificate, removing 22,105,521 redundant packaging bytes. ZIP CRC, signature, four-byte ZIP alignment and 16 KiB ELF segment checks passed. The manifest retains portrait orientation. These static checks do not certify store compliance.

- APK: `Unity/Builds/Verification/HeartOfTheRain_Development.apk`
- Size: 284,195,607 bytes.
- SHA-256: `4fb98cc1c7deae1bc5b0d572288ad57b4b209e7619c7b92bf571be3b09029e27`.
- Package: `com.heartoftherain.verification`.
- All 4,873 checkpoint-61 reviewed inputs match before and after building.

The APK was replacement-installed with `adb install -r`, without uninstalling or clearing data. Installed APK bytes match the checked artifact. Preference XML and all profile JSON hashes match before installation, immediately after installation and after the initial launch. The initial saved balance remains 1,300 coins, five lives, zero completed levels and current level one. There was no active attempt before installation. Private save contents were not exported to the evidence.

The app launched successfully (PID 14963). Initial process logs contain no detected Unity exceptions/fatal signatures. The 900x1600 framebuffer shows portrait Home and the new `5/5 Full` lives header, with aligned, legible text and artwork.

During a subsequent attempted heart-button check (one tap at 550,90), the framebuffer showed an active gameplay board instead of the anticipated pre-level modal. A later profile read showed one completed level, current level two, 1,350 coins, five lives and no active attempt. The source of that intervening gameplay is not established by this observation; it is not credited as an automated gameplay or heart-button verification. No further input, forced stop, data edits or return to Home was performed. Installation/startup preservation is proven by the earlier byte-identical snapshots; later gameplay changes are recorded separately.

Evidence is `Verification/Evidence/HomeLivesAndroid/Comparison.html`, `Main_Installation.json`, `Visual_Review.json`, build/artifact/packaging reports and logs. The dedicated collector is `python3.15.exe Verification/Tools/collect_home_lives_android_results.py`; it updates `Native_Source_Checkpoint.json`. The older generic `collect_results.py` still selects the frozen source-only checkpoint-61 collector, so use the dedicated deployment collector for checkpoint 62. Historical shared Native build reports were archived and restored; fresh reports belong to this deployment folder.

This is a scoped rebuild/install/startup check, not a new 50-level regression. Device countdown, confirmed loss/refill effects, texture memory, physical-device lifecycle and performance remain unverified this turn. Checkpoint 61's 3,266 native Editor checks, 534 general checks and 17 connected flow checks remain historical evidence, not newly run device tests. Life regeneration still uses device UTC; no trusted-time/backend changes were made. QA remains stopped and unchanged.

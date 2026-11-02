# Gameplay loading Android rebuild and LDPlayer installation

23 October 2026. Deployment checkpoint 64 installs the unchanged checkpoint-63 source, including the approved gameplay loading R2 integration, on the main LDPlayer (`emulator-5554`). No runtime, asset, metadata, level or PlayerSettings changes were needed. All 4,938 reviewed source inputs match before and after building.

The pinned Unity 2022.3.62f3 ARM64 development build passed with zero errors and 14 warnings, including unavailable remote SDK manifests and existing unused fields. Two initial build attempts were stopped at the SDK inventory check because Java was waiting in an HTTPS handshake. General Java timeout options were not forwarded to the SDK process. The successful attempt used the SDK launcher's supported process-scoped `SDKMANAGER_OPTS` to make remote inventory requests fail locally and use the already-installed packages. No SDK/engine files, versions, project source or global proxy settings were changed. Attempt logs and the installed SDK inventory are retained in this evidence folder.

Clean Gradle repackaging retained all 1,073 nonsignature entries and the signing certificate, removing 16,703,263 redundant packaging bytes. ZIP CRC, signature, ZIP alignment, 16 KiB ELF load-segment, package identity, ARM64 and portrait-manifest checks passed. These are static checks, not store or physical-device certification.

- APK: `Unity/Builds/Verification/HeartOfTheRain_Development.apk`.
- Size: 290,343,852 bytes.
- SHA-256: `93595b91d732ae6d36f84d4c3aeead17b6c45127e5360d4ed8a68cdf35ae49d4`.
- Package: `com.heartoftherain.verification`.

The app was replacement-installed with `adb install -r`, without uninstalling or clearing data. There was no active attempt before installation. Installed APK bytes match the checked artifact. Preference XML and all profile JSON hashes match before installation, immediately afterward and after startup. The existing save remains one completed level, current level two, five lives and 1,350 coins. Private save/preference contents were not exported. A transient ADB read failure before installation was retried after confirming the device connection; it caused no app mutation.

The app launched successfully (PID 17780). Process logs contain no detected Unity exception/fatal signatures. The native 900x1600 framebuffer shows portrait Home, the saved compass avatar, level two, five lives/Full and the expected progress and coin counts. No touch input or gameplay was started on the owner's save. The app is left running; QA remains stopped and unchanged.

Evidence/gallery: `Verification/Evidence/GameplayLoadingAndroid/Comparison.html`. Fresh build, packaging, artifact, installation, visual and source-binding reports belong to this folder. Shared historical Native build reports/logs were archived and restored. Validate this deployment with `python3.15.exe Verification/Tools/collect_gameplay_loading_android_results.py`. The older generic collector selects checkpoint 63's source-only review; use this dedicated collector to retain checkpoint 64 as the current deployment record.

This request verifies rebuilding, installation and startup. Gameplay loading transitions, retry controls and creation-animation handoff retain checkpoint 63's native Editor evidence; they were not newly exercised on LDPlayer. No fresh campaign regression, physical-device lifecycle, notch/touch, GPU/memory, trusted-time or store certification is claimed.

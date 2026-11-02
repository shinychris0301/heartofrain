# Profile design-kit APK — LDPlayer installation

21 October 2026 local review; process/install reports use 22 October UTC. Unity 2022.3.62f3.

At the owner's request, source checkpoint 38 was rebuilt as the existing ARM64 IL2CPP internal development APK and installed on the active main LDPlayer instance, `127.0.0.1:5555`. No runtime, asset, dependency, SDK-version or project-setting changes were needed. All 4,604 source/configuration hashes match checkpoint 38; the PlayerSettings file is byte-identical to its pre-build copy.

The first build stalled in `sdkmanager --list` during an online TLS read. That SDK lookup was stopped, and the retry used the same installed SDK/dependencies with process-local Java HTTP/HTTPS repository access disabled through a closed loopback proxy. No persistent proxy/network setting or SDK installation was changed. The retry built successfully with zero errors and two existing unused-field warnings. The initial lookup log/process record is retained in `.verification-cache/ProfileDesignAndroid`.

The current artifact is `Unity/Builds/Verification/HeartOfTheRain_Development.apk`, 245,876,641 bytes, SHA256 `afa3358260924d7c85bfeaa7f877827aa2bea0a4867974f662add98a7dbaac29`. Package identifier remains `com.heartoftherain.verification`. ZIP CRC, development signature, 4 KiB ZIP alignment and 16 KiB ELF load-segment checks pass. This is an internal development build, not a store release.

`adb install -r` replaced the main instance's APK without uninstalling or clearing data. Its installed artifact hash matches the local APK. Preference and campaign/economy JSON hashes match before installation, after installation, after launch, and after the final observation. Saved Raindrop/Gold appearance is preserved. The stopped QA instance was not started or updated.

Original 900×1600 emulator screenshots show the revised Village banner and layered four-card Profile stats, using saved values: level 1, chapter 1, 0/50 and 0 stars. These are ordinary saved values, not the earlier Editor fixtures. Portrait Home, the selected avatar and Level 1 label are visible after relaunch. Another app came to the foreground during optional input sequencing; that unrelated capture is excluded, Heart of the Rain was explicitly relaunched, and Home/final resumed activity were verified. This is a rendering/launch observation, not a controlled input or latency test. No fatal signatures were found for the running app PID.

Evidence is `Verification/Evidence/ProfileDesignAndroid`: frozen source manifest, build/process and APK reports, `Main_Installation.json`, inspected stats/Home screenshots and `Visual_Review.json`. Gallery: `Comparison.html`. The focused collector checks exact source, artifact, installed identity and preservation/visual records, and selects this deployment through `collect_results.py`.

This closes the requested APK installation and the targeted main-emulator rendering check. Reference imports remain uncompressed; release memory/performance/compression evaluation, every frame/banner choice on Android, full campaign regression and physical-device certification remain separate work. Production backend services and account/economy rules are unchanged.

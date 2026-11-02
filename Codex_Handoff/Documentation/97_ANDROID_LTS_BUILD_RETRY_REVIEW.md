# 97 - LTS Android build retry

**COMPLETED_LTS97_BUILD_RETRY_WITH_OPEN_STARTUP_GATES**

The isolated Unity **6000.3.27f1 LTS** full-game Android development build succeeds: **52 native checks, zero errors and 112 warnings**. Static APK inspection passes. The exact APK was verified installed as `com.heartoftherain.unity6lts95`; root reviewed its actual Russian Prologue before a later emulator VM fatal error.

[Test APK](../../Unity/Builds/Verification/HeartOfTheRain_Unity6LTS_Test.apk): **318,478,067 bytes**, SHA-256 `0269b692514a92dd87a75052e0c46d13ac4950e9223bff1ebf90ed537dc3b92a`.

| Scope | Actual result |
| --- | --- |
| Native compile / static APK | PASS; ARM64/IL2CPP, API 26/36, portrait Activity, signature/alignment and SDK-free checks |
| Installed artifact / current display | Exact installed hash verified; root reviewed the full portrait 900 x 1600 Russian Prologue |
| Original installation guard | FAIL retained: `LD95CandidateUnexpectedlyStarted`; no retrospective install PASS |
| Cold startup / Unity splash absence | Unverified; no video was produced. Native supported API splash/logo getters are false |
| Unity 6 accelerated regression / final relaunch | Not run / unverified at this cutoff |

The automatic initial start was unrecorded. Candidate revision 0 / 1,250 coins / five lives / Level 1 / zero clears / zero active attempts and owner APK/data/preferences preservation were observed before the VM failure. LDPlayer later entered `GURU_MEDITATION` with `VERR_IEM_INSTR_NOT_IMPLEMENTED`; transport recovery did not restore the guest. Fresh post-fatal save verification is unavailable. Whether the game triggered the VM fatal is unproved.

Main remains Unity **2022.3.62f3**: all **5,407 inputs**, its original development APK, the earlier 6000.6 candidate and **95 tracked backend files** are unchanged. The private copy preserves original nonmetadata assets/C# and all **2,821 original GUIDs**; actual importer/configuration metadata and package resolution are recorded. No runtime compatibility patch or main/worker promotion occurred. Backend tests were not rerun. The 112 build warnings remain documented; this is not a warning-free build.

Build controls were process-local SDK-manager settings, a short private dependency cache and gated offline Gradle preparation. This retry changed no Windows security, hosts/DNS/trust, shared Unity preferences or vendor binaries. Existing failed/interrupted evidence and checkpoint95/96 remain unchanged. The successful blank native smoke and its later read-only static revalidation remain distinct from the retained original outer FAIL; blank/diagnostic APKs were never installed as the game.

Evidence: [native build](../../Verification/Evidence/Unity6LTS95/GameRuns/d7ba91acb1374e08900f9f4e7f64a285/BuildDevelopment.json), [static APK](../../Verification/Evidence/Unity6LTS95/GameRuns/d7ba91acb1374e08900f9f4e7f64a285/StaticApk95.json), [retained install guard](../../Verification/Evidence/Unity6LTS95/LDPlayerRuns/b01a9db4ef004fcf94dc75844365b719/Installation.json), [root visual review](../../Verification/Evidence/Unity6LTS95/UnexpectedStartup97/7b7ca0eef7cd48cc8e6a904f196a1780/VisualReview.json), [VM cutoff](../../Verification/Evidence/Unity6LTS95/EmulatorFailure97/1a4ecba5fcfd4177abd6ccfbe7cec546/Report.json), [gallery](../../Verification/Evidence/Unity6LTS95/Retry97/Comparison.html), [summary](../../Verification/Evidence/Unity6LTS95/Retry97/Summary.json), [source audit](../../Verification/Evidence/Unity6LTS95/Retry97/SourceAudit.json) and [privacy receipt](../../Verification/Evidence/Unity6LTS95/Privacy97/Set01/Receipt.json).

Privacy publication preserves all **18 raw Unity/Console logs**, with separate sanitized derivatives; nine logs required redaction. Original logs and old receipts are untouched, private raw copies are read-only/hash-bound, and all 3,230 frozen historical evidence files match. This is a bounded redaction policy, not universal secret detection.

Actual splash absence, normal cold startup/relaunch, Unity 6 device regression and fresh post-fatal save verification remain open. Configured backend/providers, real payments/advertising, release signing/legal/moderation, broader physical devices, human campaign/balance and whole-game smoothness remain separate gates. This is an SDK-free internal test build.

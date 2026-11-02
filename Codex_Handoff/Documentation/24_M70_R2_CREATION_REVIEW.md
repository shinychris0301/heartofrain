# M70 R2 power-up creation integration

21 October 2026. Unity2022.3.62f3; current M67R4 runtime with approved follow-ups.

## Result and supplied material

The owner's requested `CodeChanges/M70_R2_After_M70.patch` from `Heart_of_the_Rain_M70_All_Powerups (2).zip` is integrated. The patch targets an older renderer, so its changes were merged into the current pooled M46 renderer and M47 gameplay controller. The supplied complete .cs files were references, not replacements for newer work. Other patch variants were not applied.

All 36 archive checksums pass. All 24 Unity-package file payloads already match the installed M70 R1 content and retain their GUIDs. R2 repairs playback selection; no texture/manifest/importer replacement is needed. Existing asset .meta files are preserved. The supplied creation poster/movie are offline reference material, not native evidence.

Archive SHA256: `664ea39f2908584ee5d336d32d7690d2ef289a1ded864f6713e64251cbd49f57`.

## Behavior

- Real power births now select Create, OR_Create, RS_Create or GS_Create, then enter Idle. Bomb, both Rockets and Rainbow Orb form over 0.6s; Seekers use 0.3s. The generic scale pop is disabled for these bodies because the authored frames already contain formation scale/opacity.
- Birth clocks belong to piece IDs. They continue through match, individual tile falls, cascades, idle and history pruning. Existing idle powers do not replay creation. Consumed powers stop drawing their body/accent.
- The existing StarCreate accent follows the moving body. The fixed-cell duplicate is removed.
- Converted Bomb/Rocket bodies fit formation into their existing pre-charge window. Short windows accelerate the clip; charge, contact and activation times are retained. Other combination effects remain intact.
- Selected starting items prewarm their resources and remain hidden until visible gameplay ownership is available. Intro/loading time does not consume formation. Pause holds the same clock; resume does not register another birth.
- Prewarm failure leaves input blocked and exposes StartingPowerError before InitializationComplete. The existing HomeLevelFlow launch guard sees this error before session.Complete can consume selected stock. The device failure fixture verifies the error/gate and recovery; it does not certify an end-to-end durable purchase/attempt transaction.

Golden creation supports existing grants/events; no Golden matching recipe or Golden+Golden rule is added. BoardModel and BoardPlayback are byte-identical to the preceding individual-refill checkpoint. Swap endpoint/rocket orientation, gravity paths, masks and model timing are preserved. Animation callbacks do not award rewards or mutate inventory.

## Changed files

| File | Change |
| --- | --- |
| Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPresentation.cs | Per-piece creation clocks, authored body phases, moving stars, conversion formation, pooled cache cleanup |
| Unity/Assets/HeartOfTheRain/M47/Runtime/GameplayScreen.cs | Starting-item prewarm, visible-time reveal and launch-error propagation |
| Unity/Assets/HeartOfTheRain/Chapter01M07/Scripts/BoardReactionReview.cs | Mirrors converted-body formation in the legacy preview while retaining M70 display scaling |
| Unity/Assets/HeartOfTheRain/M69/Editor/M70PowerCreationCheck.cs and .meta | Supplied checker and GUID7602faf8b13251efb841464c81a88164; adds only a Motion alias to resolve the UnityEngine/M46 name collision |
| Unity/Assets/HeartOfTheRain/Verification/Editor/M70R2Verification.cs | Additional native integration checks |
| Unity/Assets/HeartOfTheRain/Verification/M70R2Fixtures.cs; M70R2TouchProbe.cs | Development-only transient color fixtures and opt-in device tracing |
| Verification/Run-UnityVerification.ps1; Verification/Tools/check_m70r2_device.py; review_m70r2_device.py; collect_m70r2_results.py | Native runner, capture/review and guarded result collection |
| Verification/Tools/collect_results.py; install_timing_build.py; Regression/Repairs.json; .gitignore | Current evidence selection, installation gates, documented repair reasons and raw-capture exclusions |
| Documentation00/01/20 and earlier Comparison.html | Current-state links and historical evidence scope |

See Source_Changes.json: five runtime files changed, of which two are development-only verification support;127 of 132 runtime files are unchanged. There are no engine/SDK upgrades or new runtime3D assets.

## Verification

**Native Unity:** all 15 supplied R2 checks and 1,173 additional checks pass. They exercise all 90 creation frames through the actual atlas binding; five real model match recipes on 9x9,9x11 and11x11 fixtures; 24 converted-body cases; birth continuity, moving stars, final idle, model immutability and zero added managed allocations in warmed pooled sampling. The supplied checker also covers consumption, simultaneous births, pruning and short conversion windows.

Current regressions pass: 81,325 individual-fall checks, 10,987 timing checks across all 50 boards, 122 swap/rocket checks, 530 general Editor checks and connected Play Mode smoke. The legacy preview change compiles; a separate interactive legacy-preview device pass was not recorded.

**Android:** ten cases pass on the final APK: five real match swipes on transient9x9 color fixtures, Orb+Bomb and Orb+Rocket swipes, a 9x11 starting reveal after an actual intro Play tap, an 11x11 reveal after explicit ownership release, and injected missing-texture/retry recovery. Grant cases retain their authored level masks/layouts. Pause is an explicit native lifecycle control. Actual source-frame sampling observes formation before idle/charge; all ten decoded-video contact sheets were inspected.

The native GrantIntro probe completes before its programmatic retry branch, so its retryChecked field correctly remains false. A supplemental **actual Android Pause > Restart level > Play** recording and before/menu/new-intro/after images verify the retry UI: old starting powers/formations are absent, with 33 moves, targets37/2/15 and tool counts3/3/3/3 unchanged. Post-retry model fingerprint was not sampled; this is visual/UI evidence, not a native post-retry state assertion. See Touch/GrantIntro_Retry_UI.json and Retry_UI_Sequence.png.

The injected failure case is intentional, confined to a transient asset clone and explicitly identified in reports. Normal launches have no injected resource override. Both LDPlayer instances launch the final APK normally in portrait, without data clear, and shared preference hashes remain identical.

APK signature, ZIP CRC/alignment, static16KiB ELF alignment, seven M70 runtime sheets with no duplicate reference sheets, and portrait manifest checks pass. Static integrity has zero unexpected changes across 4,218 baseline files. The IL2CPP build has zero errors and one existing toolchain warning.

## Evidence and remaining limits

Open [Comparison.html](../../Verification/Evidence/M70R2/Comparison.html) for actual videos, frame sheets, the retry sequence and supplied offline reference. Evidence root: Verification/Evidence/M70R2. Source/artifact/capture hashes and both installations are checked by collect_results.py.

APK: Unity/Builds/Verification/HeartOfTheRain_Development.apk, 207,089,965 bytes. SHA256:

`aac0ad349555d5a385484f3b5ddf3263c6ff3b6b75653de72efd0f5e8641caa9`

Run native Mode M70R2Checks through Run-UnityVerification.ps1 with ExecutionPolicy Bypass. After building/installing, run check_m70r2_device.py with `--serial 127.0.0.1:5557`; `--mode GrantIntro` replaces only that case on the same APK and also captures actual UI retry. review_m70r2_device.py prepares sheets with a pending status; actual inspection must precede visual approval. Keep Unity execution separate from device capture because Unity exits can reset ADB.

This is targeted current-APK Android coverage. The entire 50-board Android campaign suite was not rerun; its older SwapCreation APK result remains historical. Physical-device performance, heavy-combo spikes, long sessions, human balance and durable profile/inventory/settlement/services remain open. Atlas/sampler checks do not certify whole-frame CPU/GPU budgets or billing/social/backend behavior.

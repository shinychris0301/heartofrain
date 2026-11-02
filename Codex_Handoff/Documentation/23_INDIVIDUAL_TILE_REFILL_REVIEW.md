# Individual tile refill review

Date: 21 October 2026. Runtime: M67R4 with approved follow-ups; Unity2022.3.62f3. This review supersedes the grouped refill scheduling retained in review22.

## Result

A destroyed obstacle now releases a stream of individual tiles. Consecutive gravity snapshots share one presentation timeline. Neighboring existing tiles start35ms apart, flights overlap, and a tile carries its fall speed through connected route segments when the path is clear. Each tile plays its100ms landing effect only at its final cell.

Cell vacancy reservations include a15ms clearance cushion. When a route needs to yield to another tile or an uncleared obstacle, that wait belongs to that tile; other columns continue. This removes the artificial wait for an entire gravity wave to land. It does not remove necessary occupancy/contact waits or invent spawns through surviving obstacles.

The model still chooses the same vertical-first and diagonal routes, including paths beneath surviving blockers. Model methods are unchanged from the preceding build; only presentation route declarations were added to BoardModel.cs. Raw model steps, piece identities, final snapshots, masks, goals, moves, power rules, approved artwork and asset GUIDs are preserved. Match, delivery and subsequent power steps remain presentation boundaries.

## Changed files

| File | Change |
| --- | --- |
| Unity/Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs | Adds FallLeg and optional Motion.path presentation data; model methods unchanged |
| Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPlayback.cs | Joins consecutive gravity runs; schedules individual legs from causal cell clearances; carries velocity along free routes; uses allocation-free per-frame helpers |
| Unity/Assets/HeartOfTheRain/M46/Runtime/BoardPresentation.cs | Samples timed routes, suppresses premature virtual spawns and flight stretch during waits, settles only at final cell |
| Unity/Assets/HeartOfTheRain/Verification/PlaybackFixtures.cs | Adds a cabinet beneath two surviving stones, creating a four-cell pocket on destruction |
| Unity/Assets/HeartOfTheRain/Verification/ObstacleFallTouchProbe.cs | Adds an actual-input LargeGap mode with unchanged-model snapshot comparison |
| Unity/Assets/HeartOfTheRain/Verification/Editor/IndividualFallVerification.cs | Native route continuity, stagger, occupancy, snapshot, bounds and allocation checks |
| Unity/Assets/HeartOfTheRain/Verification/Editor/TimingVerification.cs | Samples the shared route evaluator; bent/diagonal XY checks belong to the new suite |
| Verification/Run-UnityVerification.ps1; Verification/Tools/check_obstacle_fall_device.py | Runs the new native suite and seven device scenarios |
| Verification/Tools/review_individual_fall.py; collect_individual_fall_results.py; collect_results.py; install_timing_build.py | Capture/review collection, current-build guards, summary selection and installation verification |
| Verification/Evidence/IndividualFall; documentation00/01/22; preceding Comparison.html; .gitignore | Current evidence, status links and capture exclusions |

The runtime source comparison records five changed files and125 unchanged files among130 runtime C# files; two changed files are development-only verification support. See Source_Changes.json and Player_Source_SHA256.json. No changes to GameplayScreen or gravity model methods were needed in this improvement.

## Verification

- **81,325 custom native Unity checks pass:** all 50 authored boards with six power-up variants, plus center/edge stacks and both open and obstructed cabinet pockets. They cover10,014 routes, including 973 stitched routes; exact final rendered cells, route joints, immutable raw steps/snapshots, sampled column ordering, overlapping follower starts and bounded scheduling are checked.
- The per-frame route helpers allocate **zero managed bytes** over 10,000 warmed calls in the native Editor check. Empty deserialized path lists retain straight-motion behavior. This is not a whole-frame or physical-device performance measurement.
- **10,987 native timing checks**, **217 preceding fall checks**, **122 swap/rocket checks**, **530 general Editor checks**, and the connected Play Mode smoke pass on the final source. The timing count is lower than the preceding14,100 because gravity waves are joined; the new suite supplies actual XY trajectory checks for joined routes.
- Final Android IL2CPP build succeeds with zero errors and one existing toolchain warning. Signature, ZIP CRC/alignment, static16KiB ELF alignment, all seven M70 runtime sheets, absence of duplicate reference sheets and portrait manifest checks pass. Static integrity finds zero unexpected changes across4,218 baseline files.
- **Seven actual Android input cases pass:** natural match, hammer, left edge, right edge, rocket, forced slow frame, and cabinet LargeGap. Each compares the final model snapshot with the unmodified solve. The forced180ms stall occurs during flight; it is test instrumentation.
- All seven decoded-video contact sheets and consecutive30fps LargeGap detail were inspected. Separate feeds fill the pocket beneath the two surviving stones. Final tracked moving sample counts are Match:12, Hammer:7, EdgeLeft:5, EdgeRight:7, Rocket:7, Slow:9, LargeGap:10. These counts establish visible intermediate poses, not device FPS or input latency.
- Both LDPlayer instances have the exact final APK installed with install-r, launch normally in portrait, and retain their original shared preference hashes. No uninstall or data clear was used. QA transient markers were consumed; the installed app opens normally.

## Artifacts and reproduction

Current evidence: Verification/Evidence/IndividualFall. Open [Comparison.html](../../Verification/Evidence/IndividualFall/Comparison.html) for videos, playback-speed controls, the earlier reference recording, and frame details. The review22 page links to this checkpoint. Earlier reference/app clips retain their original APK and fixture scope.

APK: Unity/Builds/Verification/HeartOfTheRain_Development.apk, **207,023,981 bytes**. SHA256:

`95541e780f092d1857a079f471d400070282445582c454bd62aad1b482a0624c`

Run Verification/Run-UnityVerification.ps1 with Mode IndividualFallChecks using PowerShell ExecutionPolicy Bypass. The device runner accepts `--serial 127.0.0.1:5557 --out Verification/Evidence/IndividualFall/Touch --large-gap`. Native/device capture must remain sequential because Unity exits can reset ADB. review_individual_fall.py prepares sheets and deliberately marks them pending visual inspection; it cannot approve its own output. collect_results.py verifies current source/artifact hashes, reviewed capture hashes and both installations.

## Remaining limits

This is targeted Android verification, not a rerun of the entire 50-board Android suite. The previous full Android regression belongs to the older SwapCreation APK. Current all 50-board coverage is native route/timing verification. The first native scheduling fixture took at most18.58ms including cold Editor execution; it is not an Android frame-budget guarantee.

The retained Match Villains clip uses a different board and partly obscured motion. Exact pixel/internal-timing parity is not established. Physical-device performance, heavy combo spikes, long sessions, human balance, durable profile/inventory/settlement and production services remain open release gates. A required local yield can still occur when another tile occupies a route; it no longer stops an entire gravity wave.

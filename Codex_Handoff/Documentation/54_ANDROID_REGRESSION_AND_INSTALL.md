# Android regression and installation — checkpoint 54

22 October 2026. Unity 2022.3.62f3, LDPlayer 14. Evidence: `Verification/Evidence/Checkpoint53/Android` (`APK_Packaging.json`, `Regression/Regression.json`, `Regression/Installation.json`, `Main_Installation.json`, three review plates, `Main_Home.png`).

Source checkpoint 53 (with checkpoints 46–53 since the last device pass) is built, passes the full Android regression on the QA instance — 1,706 checks over all 50 boards, no failures — and is installed on main LDPlayer. Getting there exposed and fixed a regression-suite defect that had silently disabled the full Android suite since checkpoint 41. Main no longer had the app installed when this ran, so its install is a fresh one; no saved data existed to preserve.

## Regression suite defect

`PlayerRegressionSuite.Boot` runs after the first scene loads. Since checkpoint 41 that scene is `Launch`, which then loads `M65_First_Start` in single mode. The suite object was not `DontDestroyOnLoad`, so it was destroyed by that scene switch, and its `reviewAlways` switch (which keeps the suite on the in-memory review store) was applied before the First Start page existed. The marker file was consumed, the app ran normally, and no report was ever written; the runner timed out after 50 minutes. The last full Android regression on record (21 October) predates checkpoint 41. Newer probes (crate burst, obstacle density) already used `DontDestroyOnLoad`.

Repair (`Verification/PlayerRegressionSuite.cs`): the suite object survives scene loads, and a `sceneLoaded` hook sets `reviewAlways` on First Start before any `Start` runs. The failure phase's playback check also accepts the pause behind the checkpoint-53 loss dialog, which is intended.

## Build and packaging

ARM64 IL2CPP development build: 0 errors, the 2 existing warnings. Clean Gradle repackaging keeps all 1,020 non-signature entries and the signer. APK 260,562,614 bytes, SHA-256 `1b1d8cc34c197484…` (full value in `Regression/Installation.json`). Internal development signing; not a store build.

## QA regression (instance "Heart of the Rain QA", `emulator-5556`)

| Measure | Result | Last full pass (21 October) |
| --- | ---: | ---: |
| Status | `PASS_NATIVE_REGRESSION` | pass |
| Checks | 1,706 | 1,704 |
| Text labels | 13,925 | 13,976 |
| Rendered clips | 354 | 354 |
| Actions | 408 | 408 |
| Boards | 50 | 50 |
| Failures | 0 | 0 |

New on device: "Out-of-moves dialog shows before any life charge" and "Out-of-moves charges exactly one life and opens retry pre-level"; the 50-board replays still grant exactly one first-clear reward each with per-attempt seeds active (replays reload with their recorded seeds). Installed with `install -r`; QA's own saved data is not cleared. QA is stopped afterwards, its prior state.

## Main installation (instance "LDPlayer", `emulator-5554`)

Before installing, the app was not present on main: LDPlayer's `appsactive.data` (18:20) shows Heart of the Rain active earlier on 22 October, and its installed-apps list now omits it and Kingdom Match. Android deletes an app's saved profile on uninstall, and no copy of main's save exists in the repository, so the previous main profile cannot be recovered. No command in this session targeted main before this install; every regression command named the QA serial and used `install -r`.

The verified APK is installed with `install -r` (installed SHA-256 matches), launched, and left at the first-start Prologue — correct for a new profile (5/5 lives, 1,250 coins, level 1, no life timer running). Zero runtime errors in the player log. Main is left running; QA is stopped.

## Remaining limits

- Emulator only: LDPlayer translates ARM; physical-device certification, GPU budgets and sustained frame rate remain open.
- No timing run for the non-crate obstacle families (checkpoint 46); the density fixture still clears crates only.
- The bulk regression frames (about 450 MB) stay local and are ignored by Git; three review plates are committed.

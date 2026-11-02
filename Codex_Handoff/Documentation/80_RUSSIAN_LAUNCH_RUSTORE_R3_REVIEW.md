# 80 — Russian launch branding and language defaults

25 October 2026. Runtime baseline remains M67 R4; Editor remains Unity 2022.3.62f3. This targeted checkpoint follows the verified gameplay checkpoint 79.

The app display name is now **«Сердце дождя»**, the supplied Russian opening wordmark is integrated, and Russian is the initial language when a valid saved selection is absent. Russian appears first in both Settings and first-start language menus. Valid saved language choices retain their existing meaning.

**The requested removal of “Made with Unity” remains incomplete.** The actual pinned Editor reports `HasPro=false`; splash and Unity-logo settings remain enabled. The owner confirmed that no eligible license is available. The actual Android startup recording visibly retains the Unity splash. Unity 2022.3 Personal does not permit disabling these settings according to the [official pinned-version manual](https://docs.unity3d.com/2022.3/Documentation/Manual/class-PlayerSettingsSplashScreen.html). No engine upgrade, license change or runtime bypass is included.

## Package review and integration

The supplied `Heart_of_the_Rain_Launch_RuStore_R3.zip` contains 41 regular files, passes archive CRC/path checks and has SHA256 `3bca7f19b54760e1c4561a5c56aad285749c0f8b3709f2f98c601a1d5b479f6e`. Seven asset-manifest hashes match. Package guidance was reviewed as integration proposals; packaged scripts/browser previews were not executed as project verification.

The new Russian logo is 1774×887 RGBA with transparency, SHA256 `78cde073df9da35026881435901c165eb81433092bf9a38be8eb5071f5a43211`. Its supplied GUID `dbf14ca73e245a739834a16d7faa3b82` is preserved. The existing icon, opening key art, English logo and three loading-bar PNGs are byte-identical to their package counterparts. Their current metas/import policies are retained: copying the package's different loading-bar metas would have overwritten earlier corrections. A separate audit correction records Cyrillic prose lost through Windows console encoding in two audit observations; original audit records remain preserved, and package/runtime strings were unaffected.

The existing launch renderer consumes `Texture2D` through `RawImage`; its scene reference and regeneration setup now use the new Russian texture with the same proportional layout. The new source-sized RGBA32/bilinear logo is registered explicitly in the clarity guard, bringing the registry to 61 entries. Its logo-specific no-mipmap policy does not change the existing filtered artwork policies. Existing loading progress, portrait policy and first-time/returning routing remain intact.

Persisted locale indices remain English 0, Spanish 1, French 2, German 3, Russian 4. Only menu display order changes to 4,0,1,2,3. Both bootstrap and settings resolution default missing/invalid preferences to Russian 4; neither overwrites a valid stored choice. The Android build helper no longer overwrites the Russian product name with the former English verification label. The Android package ID, signing identity, profile paths and preference key stay unchanged.

## Changed Unity inputs

The final frozen manifest contains 5,165 inputs. Relative to sealed 79,11 existing files change and six files are added. Existing artwork/metas, Resources and gameplay runtime inputs remain unchanged.

| Files beneath `Unity/` | Change |
| --- | --- |
| `Assets/HeartOfTheRain/App/Localization/Runtime/GameLocale.cs`, `LocaleBootstrap.cs` | Russian default, stable persisted IDs and independent menu display mapping |
| `Assets/HeartOfTheRain/App/AppSettings/Runtime/AppSettingsLayout.cs`, `AppSettingsSession.cs`; `App/FirstStart/Runtime/FirstStartLayout.cs` | Russian-first menus and consistent missing/invalid preference resolution |
| `Assets/HeartOfTheRain/App/Launch/Editor/LaunchSetup.cs`, `App/Launch/Scenes/Launch.unity` | Bind the supplied Russian title in the existing layout and regeneration path |
| `Assets/HeartOfTheRain/App/UIClarity/Editor/UIClarityRegistry.json` | Add only the new Russian-logo import policy |
| `Assets/HeartOfTheRain/Verification/Editor/LaunchReview.cs`, `NativeAndroidBuild.cs` | Verify current logo and report/preserve actual Russian product and splash entitlement settings |
| `ProjectSettings/ProjectSettings.asset` | Russian visible product name |
| New `Assets/HeartOfTheRain/App/Launch/Art/Title_Logo_RU_R1.png` plus `.meta` | Exact supplied transparent artwork and GUID |
| New `Assets/HeartOfTheRain/Verification/Editor/RussianLaunch80Configuration.cs`, `RussianLocale80Verification.cs`, each plus `.meta` | Sanitized native entitlement/import configuration and locale/menu/preference regression verification |

Verification tooling adds the source-bound `Run-LaunchRuStoreR3.ps1`, restricted QA2 device runner, strict read-only-by-default collector and review-gallery builder. Generic result collection selects80 after its published Summary exists. No credentials, license contents or payment tokens are recorded.

## Native verification and visual review

All six selected pinned-native suites pass 15,143 custom checks. These are assertions, not 15,143 independent player scenarios. Every process has fresh report/log/before-and-after source bindings; historical native reports are restored by the runner.

| Suite | Checks | Scope |
| --- | ---: | --- |
| Locale80 | 580 | Twenty preference cases, 15 layouts, 10 live cases; stable IDs, Russian-first menus, existing selection and tutorial preservation; six native captures |
| Launch | 409 | Nineteen captures, 25 bar states, four real async routes: fresh Prologue, resumed Rocket tutorial, returning progress, completed tutorial; transient asset cleanup and unchanged settings/wallet |
| General | 534 | Existing general/model/app checks |
| Profile | 13,584 | Existing durable profile, transaction and font checks |
| Play smoke | 18 | Connected gameplay smoke with the existing actual offscreen camera witness |
| Portrait | 18 | Existing portrait policy checks |

Native configuration separately passes with zero clarity-import errors and explicitly reports the missing splash entitlement. All 25 native originals were actually inspected by the independent reviewers; the parent additionally viewed Russian 393×852 and 768×1024 originals. The five launch sizes include 320×480,320×568,393×852,768×1024 and900×2000. The Russian wordmark retains its aspect ratio and fits the approved sky slot; the footer has no added black panel.

Some immediate native Settings capture fixtures retain the preceding language on the dimmed Home behind the foreground modal until its next update. These captures establish the foreground menu/settings state; they do not establish complete Home translation or a persistent runtime translation defect. This fixture limitation is retained in the review notes.

One failed native Configure attempt is preserved at `Attempts/001_invalid_new_script_guid`: a newly authored test-script meta had a 33-character GUID, causing executeMethod class discovery to fail before configuration. Only that new meta was corrected to 32 characters; Configure and all selected suites subsequently ran against the final freeze. The failure is not counted as a pass. An initial ADB preflight also found the daemon had not yet discovered QA2; it exited before creating a target record or changing device state, and discovery was confirmed before the successful run.

The first read-only collection rejected missing convenience copies of the two build process records. A PowerShell array-expression error had skipped those copies; the original delegated records and logs were already intact under each native run's `Artifacts/Native/` directory. The runner expression is corrected for future runs. The collector now requires those original records and checks their exact equality/hash against the outer process binding; any optional convenience copy must also match. No native execution evidence was reconstructed or waived, and final collection passes.

## APKs and isolated LDPlayer verification

Both actual Android builds pass with zero build errors. The development and non-development release-compile APKs both report the exact Cyrillic label **«Сердце дождя»** and unchanged `com.heartoftherain.verification` package. These are internal verification artifacts, not a RuStore release.

| Artifact | Compressed APK bytes | SHA256 |
| --- | ---: | --- |
| Development APK, installed on QA2 | 302,933,929 | `d279a07c722c0a6938c7e52d6ade01efdc157c832d76f7357ff89fb0e7b7f6eb` |
| Non-development release compile | 265,734,997 | `83561ed76dbab056042ca1e0899a796105aafe68146e9505c15f53ad7faca9a7` |

Development APK CRC/signature,4KiB ZIP alignment and16KiB ELF segment checks pass. Clean Gradle packaging preserves all 1,088 non-signature entries and the same signer. The build runner restores the exact approved ProjectSettings bytes after its temporary build settings; the final source manifest SHA256 is `86675e6ad78d76879aca127fa4d69070d157ba224df30ab0765040db9875abab`.

The final development APK is installed with replacement on **Heart of the Rain QA79 isolated**, LDPlayer index 2, `emulator-5558`. The fresh isolated profile had no active attempt. All real profile JSON and PlayerPrefs hashes match before and after installation/startup/menu inspection. The main instance remains deployment 64 and stopped; original QA1 remains 78 and stopped with its unfinished attempt preserved. Neither was installed, launched, cleared or used for these checks.

The actual 900×1600 portrait startup and onboarding language-menu screenshots were individually viewed at full size. The menu shows Russian selected first, followed by English, Español, Français and Deutsch; Cyrillic copy, tick and buttons fit. No language was selected and onboarding was not advanced. The app was normally restarted to close the menu and left running at the Russian Prologue. Startup log inspection found zero matches for the recorded fatal/null/missing/index exception signatures; this is a bounded startup log check.

The twelve-second 720×1280 startup recording was reviewed through 31 hash-bound sparse original-PTS samples, two contact sheets and four full decoded originals. The samples visibly show the required Unity splash, then the new Russian wordmark and Russian loading caption over the approved opening artwork, followed by the ordinary Russian Prologue. Sparse sampling/recording overhead cannot establish exact transition endpoints, frame pacing or an uninterrupted continuous-video review. The internal Development Build watermark is expected.

## Evidence and remaining work

Open [the current gallery](../../Verification/Evidence/LaunchRuStoreR3/Comparison.html), [strict summary](../../Verification/Evidence/LaunchRuStoreR3/Summary.json), [native review](../../Verification/Evidence/LaunchRuStoreR3/Native_Visual_Notes.json), [actual Android review](../../Verification/Evidence/LaunchRuStoreR3/Device_Visual_Notes.json), [installation audit](../../Verification/Evidence/LaunchRuStoreR3/Android/Installation.json) and [source manifest](../../Verification/Evidence/LaunchRuStoreR3/Source_SHA256.json).

The Unity splash removal requires an eligible supported license on the pinned Editor. Store signing/publication, physical-device/notch checks, full translation, long sessions and broader device returning-profile routes remain open. This task changes no gameplay runtime or gameplay assets and does not re-run 79's full 35-suite/50-board performance regression. The prior later 359.614 ms Update / 366.029 ms following interval, dense drawing costs and wider continuation gates remain open without a new smoothness claim.

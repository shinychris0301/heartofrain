# UI Clarity R1 integration

23 October 2026 · source checkpoint 57 · Unity 2022.3.62f3 · source-only, no APK rebuilt or installed.

The Daily Gift regression is reproduced in native UGUI captures: detailed chest/reward images used bilinear sampling with one mip level, producing serrated highlights at small display sizes. The corrected captures use trilinear filtering and mip chains. Higher-resolution vector panels retain the same physical corners through a paired border/multiplier migration. The shared check badge is replaced with the package's vector reconstruction.

## Package and current-project reconciliation

Reviewed `C:\Users\shiny\Downloads\Heart_of_the_Rain_UI_Clarity_R1.zip`: documentation, changed assets, both layout/asset manifests, animation pixel budgets, vector sources, browser comparison, import/build/live-audit source, patch and Unity package. ZIP CRC, 84 bundle/patch file pairs and 43 manifest asset occurrences pass. The supplied WebGL comparison is author evidence, not native app evidence.

The current project has Daily Gift R1 but uses the older Wellworks renderer. It does not have the package's WellworksDesign page. Its current layout, service, milestones and claims are preserved; active reward images now use the corrected standalone UI sprites, including Golden Seeker. All six corrected Wellworks source assets are imported for this delivery, but its decorative panels/progress components are not added to the old page. There are no active WW progress multipliers to migrate.

Shared Primary and Check assets already live at `App/Profile/Art/Primary.png` and `CheckSource.png`. The registry maps to those existing paths/GUIDs. No duplicate fonts, Primary, check or Home background are imported. The intentionally blurred background is excluded from foreground import certification. The existing development reward disclosure stays visible; a clarity patch does not establish production reward availability. No automatic commit, TMP/engine migration, gameplay-atlas mutation, player-data deletion or account/backend change is performed from package instructions.

## Implemented changes

- Twenty-two registered standalone sprites have source-preserving RGBA32 import settings for Default, Android, iPhone and Standalone. Detailed foreground art uses Box mipmaps, trilinear filtering, zero bias and ignored quality mip limits. Sliced panels remain bilinear without mipmaps. NPOT size, sRGB, alpha transparency and Clamp are checked; streaming is disabled.
- Daily Gift card/hero vectors change from 288 to 576 pixels and borders from 54 to 108. The live renderer changes its multiplier from 3 to 6. Eight visible sliced usages have identical before/after screen bounds and physical corner sizes. Chrome/Primary multipliers stay unchanged.
- The check changes from 58×59 to 232×236 at its existing GUID, improving Profile, Account and Daily Gift wherever that shared sprite is used. Six DG vector exports and this reconstructed glyph are the only existing PNGs changed. Existing painted art remains byte-identical.
- `UIClarityAssets` supplies filtered standalone reward sprites to the current Wellworks page, leaving the mixed gameplay atlases untouched. The new Golden Seeker asset is referenced by `Resources/HOTR_UIClarity/Config.asset`.
- `HomeArtImportPolicy` had been silently resetting the shared R3 coin to no mipmaps and clearing platform overrides. A narrow exemption leaves that coin under the registered clarity policy; other Home assets retain their existing importer.
- The hero rocket slot is corrected to the contract's 51×46 logical box before its 1.15× peak transform, keeping the peak pixel budget accurate.
- The package's Editor-only `UIClarityGuard` and build preprocessor are integrated. The registry is remapped to live identities and all 22 installed entries are required. Invalid/duplicate entries, missing required art, stale DG borders and alpha regressions are also checked. No automatic import mutation is added. Explicit Apply backs up metadata locally; the build callback only validates.
- The live audit records current framebuffer bounds, preserved-aspect UV-region density, slice density, canvas mode/scale, target, material/tint, clipping and basic font diagnostics. It warns for any density below one, including the package's stated 4× limits. This is an Editor audit, not a device GPU profiler or an Addressables build hook.

Changed existing inputs: 29, including four C# files (`DailyGiftPage`, `DailyGiftDesignLayout`, `WellworksPage`, `HomeArtImportPolicy`), seven approved PNG replacements, sixteen import metadata files and two Daily Gift contracts. Existing GUIDs, source painting, fonts, scene files, level masks, schedules and project/package settings are retained. Exact audit is `Asset_Audit.json`.

## Native verification and limits

| Verification | Result |
|---|---|
| Before sweep | 20 native framebuffer captures over four sizes |
| After sweep | 177 assertions, 37 captures; five sizes, idle/scrolled/explicit peak fixtures |
| Sizes after correction | 320×568, 393×852, 900×2000, 1440×3120 and 1572×3408 |
| Peak coverage | 1.12× chest and 1.15× reward group; all seven reward days at both high-density sizes |
| Import/build guard | 15 native checks; current baseline accepted by the actual pre-build callback; no-mipmap regression rejected by it; Android downscale and invalid registry detected; all probes restored |
| General Editor checks | 533 passed, 0 failed |
| Connected Wellworks | 13 checks passed with isolated file profile and real service mutations; programmatic input |
| Inspected images | Eight native full-frame images plus three lossless 1:1 crops; raw sweep hashes recorded |

The comparison gallery is [Verification/Evidence/UIClarityR1/Comparison.html](../../Verification/Evidence/UIClarityR1/Comparison.html). Reports, import logs, live audits, retained images and source/capture manifests are alongside it. Raw sweeps stay local except selected retained frames. Static peak fixtures test maximum display size, not animation timing or device frame rate. Fonts/localization and rewards are unchanged; the previous five-locale claim review is historical, not rerun/certified by this clarity sweep.

The measured peak rocket density is **1.061** texels per displayed pixel at 1440×3120, and **0.972** at 1572×3408 (4×). The latter enlarges the source by about 2.9%; AccountChrome borders likewise reach about 0.973 at 4×. Live reports flag these bounds. Do not claim unlimited resolution support; larger presentations need an approved higher-resolution master or smaller presentation. No resampled thumbnail is presented as new detail.

Mip chains increase storage. For the chest, Unity Editor `Profiler.GetRuntimeMemorySizeLong` reports 12,580,808 bytes before and 16,768,824 after; these are Editor texture-object measurements, **not physical-device GPU residency or total app RAM**. The uncompressed RGBA32 baseline is a visual reference. Android memory/performance and any subsequent ASTC/ETC2/atlas optimization remain open and require native comparison. Other unregistered Home/UI artwork is outside this registry's certification.

No APK or Addressables build is produced. Last recorded LDPlayer deployment remains checkpoint 54 (source through 53); Account R6, Daily Gift R1 and this correction await deployment. Actual device input, notches, memory, animation performance and framebuffer acceptance are still required.

## Tools and reproducibility

Menu: `Tools > Heart of the Rain > UI Clarity` provides import audit, explicit backed-up Apply and live Play Mode audit. Future player builds execute `UIClarityBuildGate`; custom bundle-only pipelines must call validation explicitly.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File Verification/Run-UIClarityR1.ps1 -Mode Checks
powershell.exe -NoProfile -ExecutionPolicy Bypass -File Verification/Run-UIClarityR1.ps1 -Mode After
python3.15 Verification/Tools/collect_ui_clarity_r1_results.py
```

The collector validates the frozen checkpoint and does not run Unity. Fresh captures require inspection, refreshed visual/crop manifests and explicit `--seal`. `Before` must run before importing the correction; do not regenerate it against the corrected assets and label it a regression baseline. `Apply` performs the explicit paired DG border migration and shared-reference binding in this project. Earlier evidence is preserved; failed initial Apply diagnostics are in the ignored cache.

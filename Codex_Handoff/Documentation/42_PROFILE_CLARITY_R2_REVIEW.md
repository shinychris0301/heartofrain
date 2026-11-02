# Profile clarity R2 — native sampling correction

Source checkpoint, 22 October 2026 UTC. The package's rendering correction is applied to the currently bound Profile artwork. Android build/install and device acceptance remain pending; the deployed checkpoint-39 APK is unchanged.

## Findings and implementation

Archive: `Heart_of_the_Rain_Profile_Clarity_Fix_R2 (1).zip`, SHA256 `4bf9549341315014a13fcc1a66767d92d8e65b93c4fff3aa03d0c36cf46103e2`. ZIP integrity, manifest dimensions and PNG hashes pass. All **22 supplied PNGs are byte-identical to current project files**. Replacing them would not change the rendering. The included unitypackage contains only the Editor tool and matches its supplied source.

The current native baseline confirms that the four detailed stats icons, six frames and three banners were using Bilinear filtering with one texture level, despite large reduction to their physical display size. This produces noisy fine edges and highlights in the baseline captures. The code does not render these graphics into the blurred scenery RenderTexture: the intentionally blurred scenery behind Profile is a separate, unchanged presentation layer.

The supplied `ProfileClarityTools.cs` and its metadata are integrated without an automatic postprocessor. A narrow verification entry point selects only the **13 textures actually bound** to the current stats/frame/banner IDs. The tool's reversible audit/apply commands ran successfully: 13 applied, zero skipped/errors. Exact original importer backups remain local under `Unity/ProfileClarityReports` and `.verification-cache/ProfileClarityR2/Before`; selected audit is retained in evidence. These local generated audit directories are ignored by Git.

Those textures now use Box-generated mipmaps and Trilinear sampling, no mip bias, Clamp, NPOT None, sRGB and source-preserving import limits. Mipmap limits are ignored for this small explicit selection; global quality settings are unchanged. The supplied diagnostic RGBA32 uncompressed baseline is set for Android, iPhone and Standalone. The source imagery, existing GUIDs/sprite definitions, source dimensions and bindings remain intact. Refer to [Unity 2022.3 Sprite import settings](https://docs.unity3d.com/2022.3/Documentation/Manual/texture-type-sprite.html) for the sampling controls.

Masks, sliced card/inset surfaces, tabs, progress strips, checks, text and portraits retain their existing settings. No runtime Profile code, page layout, 250-unit authored avatar square, Home header's 17% square footprint, localization, stats semantics, saved IDs, economy or gameplay code is changed. The package's alternate suggested UI coordinates were reference guidance, not a request to redesign the approved page.

## Native verification

Pinned Unity **2022.3.62f3** compiled the supplied Editor tool and the focused verification harness. Before and after each pass **270 checks**, with **14 captures per phase**: 28 inspected native UGUI camera renders at original framebuffer dimensions. These are Editor captures, not Android/device screenshots.

Coverage includes 393×852, 320×480, 768×1024, 900×2000 and 320×568, all five supported languages, three banner variants, six selectable frames, Stats, the scrolled frame collection and single-column stats at both scroll endpoints. The native harness uses review-memory campaign and appearance state. It verifies actual Profile open/close, Home input restoration, the unchanged Home frame square and ordinary appearance preferences. Displayed values bind to Home's explicit fixture: level 12, chapter 1, progress 11/50, stars 24.

Runtime graphics audits identify effective textures, source sprite regions, physical screen bounds, filtering/mip counts, material and tint. The 13 selected textures are standalone/unpacked; mip counts change from 1 to 11 (icons/frames) or 12 (banners). Before/after graphics geometry, white tint, source regions and aspect flags match exactly. Source PNGs remain identical. Unchanged small controls and the existing rounded font retain their previous rendering.

Visual review shows smoother flag/book/stone/star contours and less noisy banner/frame detail at the same display dimensions. This necessarily filters subpixel detail; it does not create a larger master or sharpen the artwork. No new dark/white alpha fringe is visible in the inspected Profile captures. Static top/bottom scroll captures are covered; continuous scrolling stability/FPS is not measured here.

The initial capture harness attempt failed because its output directory had not been created; this was fixed before the final passing Before/After runs. That failed attempt is not counted as validation.

## Memory and remaining acceptance

The Editor's `Profiler.GetRuntimeMemorySizeLong` total for the **13 selected texture objects** changes from **149,607,152 bytes (142.68 MiB)** to **205,696,648 bytes (196.17 MiB)**, a **56,089,496-byte (53.49 MiB)** increase. These Editor counters are not a measurement of Android GPU residency, peak app RAM or startup memory. They include the costs reported by the Editor for imported texture objects. Besides mip chains, the diagnostic tool changes opaque banners from RGB24 to RGBA32; both remain uncompressed.

This is a visual reference baseline, not a release memory approval. An Android build at the same physical resolution must confirm filtering, scrolling, startup and memory, followed by a reviewed mobile compression/budget pass. The installed app has not yet received this correction. The supplied 197×193 Dariya reference and compact controls are unchanged; increasing import limits would not add detail if future layouts enlarge them beyond their current pixel budget. No larger replacement portrait was provided.

No claim of complete device blur resolution, physical-device performance or whole-project regression is made. Launch checkpoint 41, portrait policy, native build scene ordering and its icon settings remain byte-identical.

## Files and evidence

- **13 existing `.png.meta` files**: the three live DesignKitR1 banners, three DesignKitR1 frames, four DesignKitR1 stat icons, and `FrameGold`, `FrameSapphire`, `FrameIvory`.
- New supplied `App/Profile/Editor/ProfileClarityTools.cs` and its metadata; new `Verification/Editor/ProfileClarityReview.cs` and its metadata.
- Verification wrapper Before/Apply/After modes and freshness guards, current evidence collector, generated-audit ignore rule and current handoff documentation.

Gallery: `Verification/Evidence/ProfileClarity/Comparison.html`. It switches between 14 matching native Before/After pairs and links the original lossless captures. `Package_Review.json`, the original manifest/handoff notes, native importer audit, Before/After reports/process records, `Visual_Review.json`, frozen `Source_SHA256.json` and `Verification_Summary.json` retain the exact scope and identity checks.

Commands for future targeted verification:

```powershell
# After mode expects the corrected importers; do not apply a broad folder selection.
powershell -NoProfile -ExecutionPolicy Bypass -File Verification/Run-UnityVerification.ps1 -Mode ProfileClarityAfter -TimeoutMinutes 8
.venv/Scripts/python.exe -X utf8 Verification/Tools/collect_results.py
```

Before captures are historical evidence from the original importers. Re-running Before after the correction intentionally fails its baseline assertion; do not overwrite that evidence merely to regenerate the gallery. The explicit Apply entry point selects the current 13 bindings; the supplied Editor menu remains available for deliberate manual audits and reversible changes.

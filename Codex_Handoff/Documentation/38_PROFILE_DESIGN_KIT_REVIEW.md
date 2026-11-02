# Profile Design Kit R1 integration

21 October 2026 local review; native timestamps are 22 October UTC. Unity 2022.3.62f3.

The owner requested integration of `Heart_of_the_Rain_Profile_Design_Kit_R1.zip`, SHA256 `80570acb20c9bcd338f77f13895632f7653e7545df9f2d333b64f404a417da24`. The manifest, handoff, labels, browser review/QA and generation records were examined. The kit contains artwork and guidance, with no Unity source. Browser results are reference evidence, not Unity tests; generation prompts were not executed.

The existing approved Profile shell and Home Header R2 correction are retained. Profile keeps its 250×250 authored frame rectangle, uniformly scaled with the 941-unit page; the kit's 112-unit component reference is not substituted for the full-page coordinate system. Home retains a square frame at 17% of header width. Neither box is sized from texture dimensions.

## Implemented behavior

The existing Village, Twilight and Lantern saved banner IDs now bind to the revised 2172×724 R3 images, using a masked center-cover viewport. Earlier PNGs/GUIDs remain available through `_M71` asset bindings. Three new frame IDs—`RainkeeperGold`, `LanternSapphire`, `GardenIvory`—join Gold, Sapphire and Ivory. Existing IDs remain valid. Selection uses the existing save-before-presentation ProfileStore flow and local cosmetic rules; no purchase, entitlement or unlock rules are introduced.

All six frames use cached sprite regions from the manifest's alpha bounds. Portraits retain the 5.7% masked inset, use proportional cover sizing, and clip to the fixed slot. Original textures/importers remain unchanged. The Profile asset configuration owns and releases its runtime presentation sprites.

Stats use separate nine-sliced ivory cards, proportional alpha-bounded icons, live text and the supplied progress track/fill. Level, chapter, chapter progress and stars read current HomeState while PlayerProfileHost is ready. Unloaded values use an em dash. Progress clamps to 0–1; a zero denominator produces unavailable progress and an empty bar. Values refresh while Profile is open.

Normal layouts show four cards in two columns. Safe widths below 340 physical pixels use one column and vertical scrolling. Short screens retain whole-page scrolling. Non-scrollable tabs retain the top position when they become scrollable, avoiding a jump to the bottom after a size/column change. Stats captions allow two lines, frame captions have more vertical space, and Join has more width/separation from No team text. Five-language native text fitting is checked.

## Changed files

- `Unity/Assets/HeartOfTheRain/App/Profile/Art/DesignKitR1`: 12 exact supplied PNGs plus new metadata—three banners, three frames, four icons, two progress sprites. No pixels were regenerated or repainted.
- `.../Resources/HeartOfTheRainProfile/Config.asset`: revised/legacy banner and new frame/icon/progress bindings.
- `.../Runtime/ProfileAssets.cs`: cached alpha-region sprites and nine-slice card border.
- `.../Runtime/ProfileData.cs`: append three frame IDs; retain format version and original IDs.
- `.../Runtime/ProfilePage.cs`: layered stats, readiness/live updates, adaptive columns/scrolling, cover portraits and localized spacing.
- `.../Runtime/ProfileText.cs`: supplied labels and five-language names for the additional frames.
- `.../Editor/ProfileReview.cs`: validate all six frames and stat/progress art.
- `Unity/Assets/HeartOfTheRain/Verification/Editor/ProfileDesignKitReview.cs` and metadata, the existing runner and new focused collector: review/evidence tooling.

The supplied rounded font/license and ten approved PNGs already match existing project assets byte-for-byte, so they are reused. All pre-existing artwork and `.meta` files, gameplay, masks, Home scripts, Level button and services match checkpoint 37. The collector verifies seven changed existing inputs and 27 additions; the frozen manifest contains 4,604 source/configuration files.

## Verification

The final pinned Unity process compiles and exits successfully. `Verification/Evidence/ProfileDesignKit/Native_Review.json` records 382 checks and 18 native UGUI captures. Checks cover all six frames through actual Profile buttons, serialization/reload into a new store, unknown-ID rejection, write-failure rollback, cached sprites and unchanged Home square geometry. Reload checks here use isolated memory preferences; this is not another second-process persistence run.

Native renders/text generation cover English, Spanish, French, German and Russian at 393×852, 320×480, 768×1024, 900×2000 and 320×568. Frame captions, tabs, Join, live stat bindings, progress bounds, zero denominator, injected readiness failure and return-to-Home interaction pass. Update-method dispatch checks open-page stat refresh. Narrow captures show both ends of the collection; some page/gallery captures intentionally show scrolled positions.

All 18 final original PNGs were inspected and hash-frozen in `Visual_Review.json`; the gallery is `Verification/Evidence/ProfileDesignKit/Comparison.html`. Review-memory campaign/appearance fixtures are used. The example 12/1/11-of-50/24 values are set in the isolated model, not hard-coded into production UI. A later fixture shows level 50, 49/50 and 88 stars. No ordinary appearance preferences are changed.

Reproduce:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Verification/Run-UnityVerification.ps1 -Mode ProfileDesignKit -TimeoutMinutes 5
./.venv/Scripts/python.exe -X utf8 Verification/Tools/collect_profile_design_kit_results.py
```

The first verifier import required correction of its new GUID; native review then prompted caption/card-fit repairs. The final passing process and exact current source hashes form this checkpoint.

## Remaining scope

These are camera-rendered native Editor frames/programmatic interactions, not Android screenshots, physical taps, notch/keyboard validation, FPS measurements or a full campaign/service regression. New assets use uncompressed sRGB/bilinear/clamp/no-mipmap reference imports: banners max 4096; frames/icons max 2048. Their raw RGBA pixel storage totals about 60 MiB before platform overhead. Android memory/performance and compression evaluation remain open before release.

No APK is rebuilt/installed. The deployed checkpoint remains 37, SHA256 `e9309dde06f86031057f981120ad2e92be29b14d738f53c41c57f06d6afb3cc0`. Earlier tests retain their own scope. No engine/SDK upgrade, account/social identity, production service activation or new economy rules are included.

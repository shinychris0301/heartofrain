# M71 R2 Profile integration

21 October 2026. Unity 2022.3.62f3; existing M67 R4 gameplay baseline.

The owner's `Heart_of_the_Rain_Profile_M71_Update.zip` supplies the Profile and Change Name component opened from the Home avatar. Its SHA256 is `d3de8216c9c1d90af1492ae14b4bd8543f949531252b80281a11f6dc3938826d`. All 146 manifest entries were checked. The 43 unitypackage paths were examined and its payload matched the supplied UnityPatch tree; source-tree import avoided replacing the newer Home implementation or existing folder metadata.

The package's Home patches are alternatives. The relevant additions from `HomePage_Integration.patch` were merged into checkpoint 33; `HomePage_From_M71_R1.patch` was not applied. The package's status document describes an older campaign/service baseline and was treated as historical context. Current durable state, event services, gameplay, Home reward flow, portrait orientation and revised Chapter 1 background remain intact.

## Delivered behavior and repairs

Tapping the Home avatar opens the supplied Profile presentation. Six avatars, three banners and three frames are selectable; successful choices update the saved preference and Home portrait. Stats read current Home level, chapter progress and stars. Join routes to the existing Teams demo. Close restores Home input/focus; Change Name supports save, cancel, accents, Cyrillic, NFC normalization and the supplied twenty-text-element limit. Names are plain text. Long player/team display names are fitted and ellipsized without changing the stored value. The localized No team label remains complete. English, Spanish, French, German and Russian are supported; Japanese is not added.

Profile appearance remains a local preference under the supplied `HeartOfTheRain.Profile.v1` key, separate from durable campaign/economy data and server identity. The store now accepts a preferences adapter for isolation and failure checks; its ordinary adapter remains PlayerPrefs. Review-only fixtures use isolated memory/file storage. Unknown appearance IDs retain the supplied sanitization behavior. Model/store operations commit preferences before notifying presentation; no coins, lives, inventory, rewards or attempt receipts are changed by appearance actions.

Native integration uncovered and repaired these issues:

- The UnityPatch/unitypackage `Banner_Twilight.png` is truncated and fails native import. It is replaced with the complete, unmodified `Preview/assets/Banner_Twilight.png` from the same ZIP. GUID `8d0a35319ce45397bb2ad7078461755d` is preserved. The other 28 imported art/font binaries exactly match the supplied UnityPatch files. No artwork is generated or repainted.
- `Config.asset` repeats its `profileFont` field. The duplicate is removed, retaining the supplied reference.
- Banner thumbnails stretched differently shaped images into one rectangle. They now use proportional cover crops; header banners already used cover fitting.
- The supplied CPU blur performs a synchronous GPU readback and repeated pixel filtering on opening. A small cached GPU render target and a separable shader replace it. Profile preparation is staged while Home/onboarding loads, and the collection UI is reused until its data changes. Context-loss recovery recreates the target; owner destruction releases it. This adds no SDK/package dependency or engine upgrade.
- Outer scrolling lacked a raycast surface, and fitting inner collections could consume page drags. Transparent input surfaces and disabling unnecessary inner scrolling allow native UGUI drag routing to reach the full-page scroll. Reopening starts at the top, while responsive reflow preserves the current scroll position.
- Failed choice saves retain the previous appearance and show an error without a success check. Rename failures keep the draft open. A Profile open cannot displace a protected save-recovery modal or open over gameplay/pre-level presentation.

## Changed files

The only existing Unity player file changed from checkpoint 33 is `App/Home/Runtime/HomePage.cs`: attach Profile, expose the current backdrop, expose Home interaction state, and overlay the selected portrait/frame. Existing `.meta` files, asset GUIDs, approved prior artwork, level masks and board/service code are unchanged.

The Profile import adds its Art, Resources/config, Runtime and Editor/review files. `ProfilePage.cs`, `ProfileStore.cs`, `ProfileBackdrop.cs`, config and the Twilight binary include the repairs above. Supplied metadata GUIDs for the new module are retained; existing Profile/Runtime/Resources folder metadata is preserved. `Resources/HeartOfTheRainProfile/BackdropBlur.shader` and metadata implement the native blur. There are 81 new Unity input files in total, including the Editor-only verification script and metadata.

`Verification/ProfileM71Verification.cs` is fully guarded by `UNITY_EDITOR`. `Verification/Run-UnityVerification.ps1` adds the two native modes. `Verification/Run-ProfileM71.ps1` runs eight suites and copies fresh reports into this component's checkpoint folder while restoring historical reports and native smoke frames. The new collector and general-collector selection record source integrity, asset provenance, reviewed frames and native results. Exact paths/hashes are in `Verification/Evidence/ProfileM71/Package_Review.json`, `Source_SHA256.json` and `Verification_Summary.json`.

## Verification and limits

The gallery is `Verification/Evidence/ProfileM71/Comparison.html`. It includes supplied reference artwork separately from original native Unity camera-rendered UGUI frames. Five locale pairs, all choice categories, stats, long names, rename/choice write failures, the selected Home portrait, five portrait sizes, actual UGUI raycast/drag dispatch, scrolling and a second Unity process are covered. The portrait sizes are 393×852, 320×480, 320×568, 768×1024 and 900×2000. Scrolled frames intentionally crop the header; Profile starts at the top on reopening.

The native restart checks reload all four preferences through both an isolated file adapter and the actual PlayerPrefs adapter under a dedicated verification key, which is removed afterward. The ordinary appearance key is checked unchanged. The fixture uses review-memory campaign state and verifies its full serialized value unchanged after all appearance operations. Repeated opens reuse the backdrop; a deliberately released render target is recreated; destroying Home releases the retained target.

All eight native suites pass: Profile M71 Play/restart, durable profile transactions, Daily Gift Play, Wellworks Play, Rain Cup Play, connected gameplay smoke and general native checks. They contain 19,249 custom assertions/checks in total; all 28 Profile captures are explicitly reviewed and hash-frozen. All 4,571 frozen source/configuration inputs match the tested versions. Final process exits and report hashes are recorded in `Verification_Summary.json`; no earlier reports are relabeled as current. Backend HTTP/server suites are not rerun because their inputs are unchanged. Editor opening callback measurements are diagnostic only: preparation occurs earlier, so they are not frame times, device benchmarks or a controlled Android comparison.

Reproduce:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Verification/Run-ProfileM71.ps1
./.venv/Scripts/python.exe -X utf8 Verification/Tools/collect_profile_m71_results.py
```

There is no new APK build/installation in this source checkpoint. The deployed Rain Cup APK remains SHA256 `c9e3928c5ae91aacaa047374550bf1f2ac532ab81c3e8039d0e52b554c1fc018`. Real touch, software keyboard, notch/safe-area hardware, Android/iOS shader behavior and physical-device performance remain unverified. The supplied chrome/font are documented reconstructions/approximations of flattened artwork; exact original-layer/font parity and native-language editorial approval are not claimed. Arbitrary user Unicode beyond the tested supported-language glyphs is not certified.

Real account/name/team services, entitlements, full wallet/account migration and production authority remain separate work. This Home appearance preference is not wired to gameplay HUD or other demo social portraits. It does not close any of the existing backend, commerce, physical-device or release gates.

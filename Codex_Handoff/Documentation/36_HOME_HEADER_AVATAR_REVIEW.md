# Home header avatar separation — R2

21 October 2026 local review; native process timestamps are 22 October UTC. Unity 2022.3.62f3.

The owner supplied `Heart_of_the_Rain_Home_Header_Avatar_Fix (1).zip` (SHA256 `e35cb0e4a71c2905aa9f0fed5c6a5395af3c68972c43d65a44e533242a4f90b3`). The README identifies R2, correcting the earlier proposed frame enlargement. Its documentation is treated as scoped merge guidance. The complete fix is merged into the current branch; the alternative R1-to-R2 upgrade is not applied. Current navigation, the Level label, Profile integration and Chapter 1 background remain in place.

The supplied approved atlas is byte-identical to the existing `App/Home/Art/R4_Header.png` (SHA256 `71f17523e9c18006da5389fd1eb615403d85014616c18b3a44190f12bc63f0b3`). Its pixels, binding, GUID and importer are retained. No replacement artwork, prefab or scene rebuild is necessary.

The previous implementation drew the full flattened header, including its original Ivan portrait and gold frame, behind the selected Profile portrait/frame. The native before captures reproduce the exposed gold edge beside Dariya/Sapphire. R2 draws the panel independently from source pixels `(400,0,1721,360)`, uses the clean `(400,0,16,360)` connector, and uses `(0,0,386,360)` only for the fallback portrait. Source coordinates have a bottom-left origin. Runtime slices share the original texture and are disposed with Home.

Each custom frame retains the original square display size, 17% of header width, left aligned and vertically centered. Extraction bounds do not enlarge the visible frame. Portraits use proportional masked cover sizing. The fallback hides immediately when a valid custom portrait/frame/mask is present. The avatar hit area follows the package's separate 400/2121-width region; coin, lives and settings positions and labels retain their existing geometry.

Player changes are narrow:

- `Unity/Assets/HeartOfTheRain/App/Home/Runtime/HomeLayoutEngine.cs`: separate panel/connector/avatar layout and shared source-region fractions; retain current navigation helpers and Level label.
- `.../Runtime/HomePage.cs`: render those slices, mask the avatar slot, replace only avatar visuals on Profile changes, refresh their button feedback cache, and dispose owned sprites. Current `SpriteFit.Center`, responsive art, Profile attachment and flow integration are preserved.
- `.../Runtime/HomeHeaderSprites.cs` and supplied `.meta`: new texture-sharing slice owner, retaining the package GUID `6841ff57de094eacabee6b020582a1dc`.
- `.../Data/Home_Layout.json`: matching supplied sample header geometry; it does not override saved progression.

All pre-existing artwork, metadata, serialized bindings, Profile persistence/model code, gameplay and services are unchanged against checkpoint 35.

## Verification

Two fresh pinned Unity processes exit successfully. Before captures record Dariya/Sapphire at 720×1280, 900×2000 and 1200×1600. The final Play Mode review drives the actual Profile avatar button, avatar choices and frame choices for all six avatars × three frames × three sizes: 54 combinations. Three additional null-appearance fallback states pass.

Native assertions check original square frame dimensions/placement, proportional portrait sizing, selected portrait identity, hidden fallback, absence of a rendered full-header sprite, panel source boundaries, unchanged wallet object/position/counters, and unchanged Level/navigation/background objects during selection. Programmatic coin/lives/settings route dispatch and an actual Level 18 pre-level modal open/close pass. Currency routing retains its existing demo behavior; this does not implement purchases or refill services.

All 15 original native PNGs (three before, twelve final) were inspected and hash-frozen in `Verification/Evidence/HomeHeaderAvatar/Visual_Review.json`. The final images show Gold/Ivan, Sapphire/Dariya, Ivory/Raindrop and fallback at each size. The gallery is `Verification/Evidence/HomeHeaderAvatar/Comparison.html`. Frame dimensions match the before report exactly. Exact source/configuration hashes are in `Source_SHA256.json`; the collector verifies the scoped diff against checkpoint 35 and selects this latest component through `collect_results.py`.

`Verification/Editor/HomeHeaderAvatarReview.cs` and its metadata provide the Editor-only review. It uses isolated review-memory campaign and appearance data and restores the native GameView sizes. `Verification/Run-UnityVerification.ps1` adds `HomeHeaderAvatar` and the historical baseline mode `HomeHeaderBefore`, with fresh report validation. The baseline mode is intended for pre-merge source; running it after the merge will capture current source, not recreate the former implementation.

Reproduce the final check:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Verification/Run-UnityVerification.ps1 -Mode HomeHeaderAvatar -TimeoutMinutes 5
./.venv/Scripts/python.exe -X utf8 Verification/Tools/collect_home_header_avatar_results.py
```

These are camera-rendered native UGUI frames and programmatic dispatch, not Android screenshots, physical taps, notch/rotation coverage or FPS measurements. Appearance persistence was established at checkpoint 34 and is not retested here; no persistence code changes. Earlier gameplay/service suites retain their historical scope. No ordinary profile is modified and no APK is built or installed. The deployed Rain Cup artifact remains SHA256 `c9e3928c5ae91aacaa047374550bf1f2ac532ab81c3e8039d0e52b554c1fc018`.

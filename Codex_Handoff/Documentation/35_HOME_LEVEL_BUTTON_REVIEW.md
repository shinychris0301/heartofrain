# Home Level button label

21 October 2026; Unity 2022.3.62f3.

The owner supplied `Heart_of_the_Rain_Home_Level_Button_Update.zip` (SHA256 `98063ab6bca8e600aebd5341a5291bc4771a33650c606ed524b7a5e80b136f8e`). Its focused `Home_Level_Button.patch` was checked and applied to the Unity source. The complete replacement engine contains older navigation positioning and removes shared navigation helpers; those unrelated differences were not imported. Supplied `.meta` files were not substituted.

Only two existing player inputs change:

- `Unity/Assets/HeartOfTheRain/App/Home/Runtime/HomeLayoutEngine.cs`: replace Start Level plus a separate number with one centered `Level {currentLevel}` label. Font size is 16% of button width, with the existing text fitting. Existing translations supply Level/Nivel/Niveau/Level/Уровень; the accessible label uses the same wording. Button artwork, bounds and `prelevel` action are unchanged.
- `Unity/Assets/HeartOfTheRain/App/Home/Data/Home_Layout.json`: update the matching English sample snapshot to Level 18 and remove `start-number`. This is sample data, not an override of saved progress.

Current Home/Profile code, Chapter 1 art, shared navigation geometry, gameplay, durable campaign/services and all existing metadata/GUIDs are preserved. No engine, dependency or artwork change is made.

## Verification

The pinned Unity Editor compiles and exits successfully. `Verification/Evidence/HomeLevelButton/Native_Review.json` records eight native Play Mode Home captures: English levels 12 and 50, all five languages at level 50, and additional Russian layouts at tall-phone/tablet sizes. Viewports are 720×1280, 900×2000 and 1200×1600. Visible/accessibility labels agree; the old number node is absent; native text fits its bounds. Programmatic clicks open and close the actual pre-level modal for levels 12 and 50.

All eight original camera-rendered UGUI frames were inspected and hash-frozen in `Visual_Review.json`. The gallery is `Verification/Evidence/HomeLevelButton/Comparison.html`. Review-memory campaign and appearance fixtures are used; no ordinary saves/preferences are changed. This is targeted label/routing evidence, not physical touch, Android screenshots, full campaign/service regression or device certification. The preceding Profile suites retain their original checkpoint scope.

`Verification/Editor/HomeLevelButtonReview.cs` and its metadata provide the native capture/dispatch entry point. The existing Chapter background helper supplies/restores the three native GameView sizes. `Verification/Run-UnityVerification.ps1` adds mode `HomeLevelButton`; the focused collector verifies the narrow diff against checkpoint 34 and selects the latest source evidence through the general collector. Exact input and image hashes are retained with the evidence.

Reproduce:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Verification/Run-UnityVerification.ps1 -Mode HomeLevelButton
./.venv/Scripts/python.exe -X utf8 Verification/Tools/collect_home_level_button_results.py
```

No APK is built or installed. The earlier Rain Cup APK remains SHA256 `c9e3928c5ae91aacaa047374550bf1f2ac532ab81c3e8039d0e52b554c1fc018`.

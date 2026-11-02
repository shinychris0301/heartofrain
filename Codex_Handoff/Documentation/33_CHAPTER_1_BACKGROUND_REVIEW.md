# Chapter 1 Home background replacement

21 October 2026. Runtime baseline M67 R4; Unity 2022.3.62f3.

The owner supplied revised Chapter 1 artwork and requested replacement of the Home background. The exact supplied image was located at `C:\Users\shiny\Downloads\Home_Background_Original_Character_R1 (2).png` and visually matched to the attachment. All three identically named download variants contain identical bytes.

The original 937×1678 PNG is copied byte for byte into `Unity/Assets/HeartOfTheRain/App/Home/Art/Chapter01_VillageWell.png`. Its SHA256 is `f1b2021b887b323186e25bd5f09e2f075ff840f86ce4ab3acf5950213c020533`. The existing `.meta` is unchanged, preserving GUID `79016e1d2af753dc8f250504aeac3654`, sprite identity and importer/platform settings. No image generation, repainting or destructive image processing is involved.

`App/Home/Runtime/HomePage.cs` now selects the same approved portrait art for phones and tablets. The former tablet-specific picture remains as a retained asset, but portrait Home no longer selects it. The existing cover fit preserves proportions and fills the viewport. Vertical cropping is anchored to the top: a centered tablet crop of the taller new composition hid the face behind the top HUD. Horizontal cropping remains centered. Explicit background overrides and historical landscape previews retain their previous centered fit. The app's existing portrait-only orientation policy is unchanged.

The only changed player inputs relative to checkpoint 32 are the PNG and `HomePage.cs`. Existing metadata, serialized references, other artwork, layouts, gameplay, profile services and backend source/configuration are unchanged. The replaced original is retained locally in ignored `.verification-cache/ChapterBackground` for comparison.

## Verification

`Verification/Evidence/ChapterBackground/Comparison.html` shows six inspected original native captures: before and after at 720×1280, 900×2000 and 1200×1600. The final phone, tall-phone and tablet frames fill the viewport without stretching or empty margins; the face remains clear of the top HUD. Cover fitting crops the lower artwork on the tablet and the sides on the tall phone. UI positions and touch bounds are unchanged.

`Verification/Editor/ChapterBackgroundReview.cs` and its new metadata provide a disposable-scene native Play Mode capture entry point. It uses the actual `HomePage`, approved bound assets and preview state, without attaching a profile host or opening a player save. A native camera primes the requested viewport before responsive reflow and renders the UGUI to PNG. A viewport assertion rejects captures with stale Editor window dimensions. Preview balances, badges and timers are fixture data and do not represent live service availability.

The pinned Editor compiles and exits successfully. Three native renders pass; the collector checks all six reviewed image hashes, the exact supplied PNG hash, unchanged metadata, undistorted UV ratios and top alignment, and the narrow input diff against checkpoint 32. `Source_SHA256.json` records the verified inputs; subsequent collection rejects changes to frozen runtime inputs. This is a targeted Home visual check, not a new gameplay/transaction suite, Android screenshot, FPS measurement or device certification. Checkpoint 32's service tests retain their original scope.

Reproduce the current native pass and collect evidence:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Verification/Run-UnityVerification.ps1 -Mode ChapterBackground
./.venv/Scripts/python.exe -X utf8 Verification/Tools/collect_chapter_background_results.py
```

`Verification/Run-UnityVerification.ps1` adds the targeted native mode. `Verification/Tools/collect_results.py` selects this latest source component. The collector, native report, process record, visual review hashes and gallery are under `Verification/Evidence/ChapterBackground` and `Verification/Evidence/Native/ChapterBackground_Process.json`.

No APK is built or installed for this source-only asset replacement. The deployed Rain Cup APK remains unchanged: SHA256 `c9e3928c5ae91aacaa047374550bf1f2ac532ab81c3e8039d0e52b554c1fc018`. Android rebuild/device review and the previously documented backend/release work remain open.

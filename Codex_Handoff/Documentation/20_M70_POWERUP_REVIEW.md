# M70 power-up asset integration - 20 October 2026

Follow-up: review24 integrates the requested M70 R2 creation patch. Asset payloads remain identical; this R1 integration evidence retains its original APK scope. See `24_M70_R2_CREATION_REVIEW.md`.

The owner supplied `Heart_of_the_Rain_M70_All_Powerups.zip` and requested asset replacement and verification. Archive SHA256: `990257c818c69249d805926fa6cfe1ff0bf879e4e849156b1fb6909a0667760e`. Bundled prompts, README instructions and patch files were reviewed as references, separately from the owner's authorization. The older complete source copies were not used as replacements for current code.

Unity remains **2022.3.62f3**. The M67R4 app baseline, M68 celebration/Home reward flow, approved timing and gravity repairs, portrait policy, level definitions and gameplay rules are preserved.

## Assets and bindings

Seven body atlases and their seven manifests replace the preceding versions. Both the source/replay PNGs and the M48 streamed copies match the supplied bytes. Existing GUIDs are preserved. The live first-start asset chain resolves to `M48GameplayUIAssets` and `M48Chapter01Boards`; native and device checks exercise the active bank, not just the saved review binding.

| Body | Live atlas index | Supplied frames |
| --- | ---: | ---: |
| Horizontal Rocket | 9 | 110 |
| Vertical Rocket | 10 | 110 |
| Bomb | 6 | 110 |
| Rain Seeker | 29 | 64 |
| Golden Seeker | 40 | 64 |
| Rainbow Orb | 19 | 64 |
| Double Orb / Super Orb combination body | 26 | 64 |

Bomb and both Rockets now have 48-frame, 30fps looping idle clips. Existing activation schedules remain intact. The cumulative M69-named Editor importer runs after M48 and retains all seven sheets at 2048 pixels with ASTC4x4 mobile overrides. The supplied contract and explicit installation checker are under `M69`; their naming does not introduce new mechanics.

Source GLBs, offline videos and authoring files remain outside Unity runtime assets. The APK contains seven streamed body sheets and excludes all seven reference atlas copies. Dedicated pre-level UI illustrations are separate Sprite bindings, not stale body-atlas slices; no supplied replacement exists for those UI roles. See `UI_Icon_Bindings.json`.

## Code changes

Five existing production/review presentation files changed, with narrow merges recorded in `Merged_Presentation.patch`:

- `M46/Runtime/BoardPresentation.cs`: stationary Seeker scale correction; advancing idle age for presented powers. Authored effect transforms retain their existing scale, avoiding a second multiplier.
- `M46/Runtime/M46AtlasBank.cs`: retain variable JSON rectangles and pixelsPerUnit; reject a texture/manifest dimension mismatch. Existing asynchronous loading, cache budget and eviction behavior remain intact.
- `Chapter01M07/Scripts/BoardReactionReview.cs`: advance idle age and keep stationary body scale consistent with live presentation.
- `Chapter01M05/Scripts/BombBoardPreview.cs`: advance the legacy preview's idle sampling.
- `Chapter01M07/Scripts/PowerUpPlaybackGallery.cs`: fit the entire selected clip, including its height, instead of using the first atlas frame's width. M70's initial Orb/Create frame is only 8 pixels wide; the former rule clipped later poses. Native control/corrected images demonstrate the repair.

The resource catalog records the seven new texture hashes and ASTC4x4 sizes. Existing bakers/players already use manifest rectangles and PPU; no baked Animator clips or external sprite bundles are used by the active app.

An opt-in development verifier checks the active GameplayScreen clock, pause/resume, activation and texture residency on all three board shapes. It is absent from shipping players. In the runtime source freeze, **120 of 126 pre-existing files are byte-identical**; five presentation files and the suite caller changed, and one development verifier was added. BoardModel, BoardPlayback, GameplayScreen, AppOrientation, navigation, inventory and reward code are unchanged.

## Verification

- Offline source checks: **586 frames**, matching hashes/copies, valid variable rectangles, transparent gutters and idle body containment. Containment excludes alpha<=8 glow fringes; transparent non-idle effect tails are permitted.
- Native Unity M70: **3,051 checks**, all 586 frame/PPU samples and replay parity, mobile importer policy, active binding chain, three board sizes, and gallery containment at three viewport shapes. Actual GPU control/corrected images are retained.
- Native regression: **530 general checks**, **14,100 timing checks**, **18 portrait policy checks** and **nine connected Play Mode smoke checks** pass. Earlier gravity/performance checkpoints retain their documented scope.
- Final Android APK: **1,727 checks**, all **50 boards**, **354 rendered clip samples** and **419 standard fixture actions**, plus the M70 live checks. Story/tutorial, five locales, standalone powers, supported pair variants, tools, stacked-obstacle refill and five strict legal clears pass. All **281 unique listed frames** are portrait. Source/GUID integrity has zero unexpected changes.
- M70 device checks confirm moving Bomb/Rocket idle poses, pause/resume and activation on 9x9, 9x11 and 11x11 boards. All seven textures are ASTC4x4 at 2048x2048 with one loaded copy each. Their combined Unity-reported memory is **29,363,488 bytes (28.003MiB)**, excluding other app assets and driver overhead. This is roughly 15.5 MiB more compressed body-sheet storage than the preceding 6x6 policy; unsupported hardware can require larger fallback storage.
- Actual Android touch/display captures verify held-drag response, one-tap Rocket activation and navigation feedback. The visual review includes the new idle bodies, activation/combination frames, gravity and completion/reward flow.

`Comparison.html` distinguishes native reconstructed previous-asset fixtures, current Android-rendered gameplay and the gallery camera control. Supplied offline playback is provenance, not Unity/device evidence. The full campaign fixtures are not a human balance playthrough or a test of unimplemented services.

## Performance and final APK

The previous portrait APK and final M70 APK each ran the same eight-phase unaccelerated probe on the QA emulator, without Unity, screenshot readbacks or recording during timing. Raw measurements and `Performance_Comparison.csv` are retained. This run recorded lower frame times than its baseline, but host contention, caches and ARM translation prevent a causal performance claim. Heavy combinations still produced frame spikes; physical-device profiling remains open.

A clean Gradle launcher package removed **27,333,807 bytes** of unused incremental ZIP data. All645 non-signature entries retained their CRC and uncompressed size, and the development signer certificate is unchanged. `APK_Packaging.json` records this step after the successful pinned Unity build. No SDK/engine update or player/asset recompilation was involved in repackaging.

Final artifact: `Unity/Builds/Verification/HeartOfTheRain_Development.apk`, **206,918,245 bytes**, SHA256 **0379ed02398cc42b5806ee0b528cd0c02235f2c454898c7424326b36c4d4bd81**. ARM64 IL2CPP development/debug package; Unity build reports zero errors and one existing warning. Signature, ZIP CRC/alignment, static ELF load alignment, compiled portrait/game category and M68 payload checks pass. This is internal verification, not a store release certificate.

The final APK is installed and running in original LDPlayer instance 0 and **Heart of the Rain QA** instance 1. Installation uses `-r`, with no uninstall or data clear. Original-instance preference file hashes remain identical across the final install. Physical Android/iOS, low-memory/thermal performance, native-language approval, human balance and the existing durable-profile/inventory/settlement/backend release gates remain open.

Evidence: [interactive comparison](../../Verification/Evidence/M70/Comparison.html), [native checks](../../Verification/Evidence/M70/Native_Checks.json), [Android report](../../Verification/Evidence/M70/LDPlayer/Regression.json), [visual review](../../Verification/Evidence/M70/Visual_Review.json), [performance](../../Verification/Evidence/M70/Performance_Comparison.csv).

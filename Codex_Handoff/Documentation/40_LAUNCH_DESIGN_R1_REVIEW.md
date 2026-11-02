# Launch Design R1 — package review

Review performed 22 October 2026 UTC. This is a design/package verification checkpoint, not a new source integration or Android deployment. Source checkpoint 38 and deployed APK checkpoint 39 remain current.

The user requested checking and verifying `Heart_of_the_Rain_Launch_Design_R1.zip`. The archive's prompts and integration notes were treated as reference material. No artwork, icon setting, scene, tutorial state or saved data was replaced.

## Verified contents

Archive SHA256: `1e47dd4aa112db5d36da5b6d1040ed3b170c533005abd991167af542715908f3`. ZIP CRC, all three PNG decodes, manifest dimensions/modes and SHA256 values pass. Exact package copies and independent reports are retained in `Verification/Evidence/LaunchDesignR1`.

| Asset | Dimensions | Finding |
| --- | --- | --- |
| App_Icon_R1.png | 1254×1254 RGB | Opaque square, golden faceted wardstone within sapphire water; central gold silhouette remains readable in the supplied 48/64 px and circular-mask browser previews. |
| Opening_Key_Art_R1.png | 941×1672 RGB | Text-free portrait illustration; three faces, crystal, well and bucket remain visible in inspected phone/tablet previews. |
| Title_Logo_R1.png | 1774×887 RGBA | Correct brand text and genuine alpha range 0–255; separate from illustration and live UI. |

The included font and OFL license are byte-identical to existing project assets. The prompts record generation intent; they do not establish exact likeness, native resolution provenance, production approval or tested behavior. Manifest dimensions are independently verified; absence of prior upscaling cannot be proven from these PNGs alone.

Visual anchors agree with the product bible: Ivan's burgundy cloak/lamellar armor, Daria's curls/olive cloak/map, and Mila's braid/indigo costume/circlet/blue lantern. Ivan's existing Chapter 1 Home art, the current Daria rig source and storybook page 19 were inspected as references. This is an assessment of visual continuity, not a claim of exact facial identity. The floating Heart should remain symbolic launch art: it must not imply its early recovery or replace the Chapter 1 story sequence. Do not adopt the storybook's obsolete five-level chapter ranges.

## Independent browser verification

The exact supplied HTML was rendered in isolated headless Chrome. Checks exercised 1440, 390 and 320 px browser widths × four preview modes × two loading/ready states × five languages: **120 cases**. Ten browser captures were inspected, including icon masks and a failing stress case. These are browser screenshots, not Unity or Android captures.

All **90 portrait phone/compact/tablet cases** passed logo/footer containment, localized text bounds, page width, state toggles and language assignment. Faces/crystal remain readable in the inspected representative compositions. The tablet preview preserves the complete portrait with side backdrop.

Six landscape stress cases exceed the footer text width: French loading at browser width 390; Spanish/French/Russian loading and French/Russian ready at width 320. The French loading text visibly extends beyond the narrow portrait art region at width 320. Overall browser report therefore retains `passed: false`; it is not an unconditional layout pass. This is a low-severity review-page issue because the application remains portrait-only. No artwork correction is indicated by these cases. If that optional review mode is retained, fit/wrap footer text or give it a wider region. Supplied Layout_QA.json covers a narrower set and is not native evidence.

No real notch/safe-area simulation, runtime UGUI import, device memory/compression, launch timing or physical-device testing was performed for this package.

## Integration preparation still required

1. Prepare Android icon exports and actual adaptive foreground/background assets. The flat opaque source and CSS mask previews are not an installed launcher-icon validation. Existing Android PlayerSettings icon texture lists are empty; no new icon is configured by this package.
2. Obtain a larger opening-art master for high-density targets after composition review. Current 941×1672 artwork is suitable for this design review; increasing importer limits cannot add detail. Independently confirm the required target sizes before promising tablet sharpness.
3. Add a dedicated launch presentation ahead of the existing FirstStart/Home route. FirstStartPage currently builds Home, resumes persisted tutorial stages for first-time players and bypasses the tutorial for returning players. Preserve that behavior, Home background, portrait policy and durable progress. Do not substitute this illustration for the prologue/chapter/tutorial screens.
4. Keep logo/status/progress as separate UI. The HTML progress is a fixed illustrative 72%, and ready text is a design state; it does not load assets or implement a functioning continue action. Drive any future Unity progress from real work and transition only when initialization is ready. An extra mandatory tap is not established by this review.
5. Use runtime safe-area bounds and test portrait aspect ratios in Unity and Android. Use a prepared diffuse tablet backdrop rather than importing the HTML's CSS blur as a runtime requirement. Respect reduced motion and avoid blocking initialization for suggested fades/glints.
6. Budget texture lifetime and compression. The three rasters total about **18.0 MiB** at RGBA32 without mipmaps; opening art plus logo alone are about **12.0 MiB**. This is an arithmetic estimate, not measured GPU residency. Release transient launch textures when practical and validate quality/startup memory on device.

## Changes and limits

Only review evidence and handoff documentation were added. All **4,604** existing source/configuration hashes from checkpoint 39 match. No runtime code, Unity asset/meta, ProjectSettings, APK or emulator state was modified. No Unity compile/build/install was needed for this review-only task.

See `Verification/Evidence/LaunchDesignR1/Comparison.html`, `Package_Verification.json`, `Browser_Verification.json`, `Visual_Review.json` and `Verification_Summary.json`. The original package review remains available under `Package/Review/Launch_Design_Review.html` with its exact supporting assets.

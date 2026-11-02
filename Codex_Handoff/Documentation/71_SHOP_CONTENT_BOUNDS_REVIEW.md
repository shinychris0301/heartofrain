# In-level Shop content containment

24 October 2026. Follow-up to checkpoint 70 and the owner's screenshot showing the wallet, coin list and Back button crossing their allotted panel area.

## Cause and correction

`App/NoMovesDesign/NoMovesPage.cs` previously positioned the Shop controls against the outer `AccountChrome` rectangle. That artwork contains a title band, side frame, rounded cream corners and a bottom frame. The old 12/14-unit side offsets and 10-unit footer clearance crossed that usable surface. Compact button sizing alone did not correct the containment; checkpoint 70's visual review missed this defect.

The Shop now has one explicit `Shop interior` rectangle, inset 32 logical units horizontally, 82 below the panel top and 34 above the panel bottom at the existing slice density. The wallet, availability copy, masked viewport and footer are all children of it. The list ends 14 units above the footer; its header also has a separate gap. Back to level remains centered and 48 units high. The clipped, clamped coin list can scroll to show the final pack completely above the footer. A partially visible row at a viewport edge is normal scrolling content; it never draws over the panel frame or footer.

Rows use the interior width instead of the outer panel width. On narrow phones the pouch and quantity adapt to the reduced width while preserving the compact purchase button's touch height. The existing artwork, slice settings, palette, sprite GUIDs, Continue offer layout, Home Shop and transaction rules are preserved. No wallet, life, board or purchase-service logic changed. Real coin purchases remain unavailable.

## Verification scope

Fresh native Editor verification in Unity 2022.3.62f3 passes **39,410 checks across 175 layouts**: five screen sizes, five locales and seven states. `NoMovesPlayReview.cs` now checks actual world-space containment against the cream surface, row-child bounds, independent header/footer space, clipping and final-pack reachability at both ends of the list. These assertions are shared with the opt-in development-player probe, `NoMovesDeviceProbe.cs`. Connected flows still cover low-balance Shop routing, Back, restoration, repeated purchases and confirmed loss. The supplied prefab structural validator also passes.

Evidence is under `Verification/Evidence/ShopBounds`. Native images inspected include the normal phone, compact 320x568 phone, portrait tablet, Russian layout and bottom-of-list capture. Checkpoint 70's separate model/transaction regression suites retain their historical scope; they were not rerun for this presentation-only correction.

The device runner's `ShopBounds` mode uses three isolated memory-only fixtures derived from checkpoint 70: insufficient funds into Shop, restored Shop Back, and a restored Shop with a real ADB swipe to the last pack followed by a real Back tap. The last case verifies native bounds at the top and bottom, the exact saved board/RNG, unchanged wallet/life and return to the offer. Owner saves are never replaced. All three cases pass on QA LDPlayer (`emulator-5556`), including 78 live containment checks around a real swipe and Back tap. Real profile/preference hashes are identical after the fixtures and ordinary startup. The final development APK is 301,626,499 bytes, SHA-256 `28e3e1455619e2e66706a611a3364291e5ac7c0daad99992868c2880f0490b28`. Native compilation has zero errors; import audit, clean packaging, signature, CRC/alignment and static ELF checks pass. The frozen inventory contains 5,087 Unity inputs; only the presentation file and two verification files differ from source70, with no artwork, metadata, package or Player Settings changes.

Reproduce native checks and the structural validator with `Verification/Run-ShopBounds.ps1`. Device command: `Verification/Tools/run_no_moves_r2_device.py --serial emulator-5556 --evidence ShopBounds --install`. Collect with `Verification/Tools/collect_shop_bounds_results.py`. Historical source70 evidence is retained.

Physical-device verification, full-campaign certification, production continuation authority and real coin IAP remain open. The dedicated QA installation does not replace main LDPlayer's deployment64.

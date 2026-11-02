# No Moves R3: native layout correction

24 October 2026. Integrates `Heart_of_the_Rain_No_Moves_R3.zip` into the current Unity 2022.3.62f3 project. Checkpoint 69's repeat purchases remain: five moves for 900 coins per purchase, with no configured one-purchase cap. This is a presentation correction; the live profile transaction authority and board model are preserved.

## Corrected presentation and routing

- Play On is content-sized and centered, 57 logical units high. Label, coin and quoted cost stay together. Its sliced artwork uses the supplied source-to-logical density rather than stretching a full-width oval.
- The Continue wallet is compact, left-aligned and has the new green plus icon. Wallet/plus opens the existing in-level Shop.
- The Village Purse coin card is present beneath Continue and opens Shop. Its action reads **Shop**, rather than displaying the package's illustrative cash price: the current catalog is a preview and there is no validated store provider. It neither sells nor grants coins.
- An eligible offer remains +5 /900 at balances 0, 700, 899, 900 and 1,600. Affordability does not determine eligibility. Play On at 700 opens Shop immediately with no purchase command or life debit; 900 is accepted exactly once and leaves zero coins. Buying at 1,600 leaves 700 coins and five moves.
- Loading and recoverable quote errors are distinct presentation states, with localized loading/error/Retry copy. They do not turn a low wallet or missing resource into a confirmed unavailable offer. Existing protected save-error and unknown-purchase reconciliation remain in use.
- At the owner's follow-up, the **in-level Shop buttons** were corrected too: each coin row now has an icon and quantity on the left and a compact 51-unit button on the right. The source corners map to 30/24 logical units. Back to level is a centered, content-sized 48-unit secondary button. Coin-purchase controls remain disabled and labelled unavailable. The independent Home Shop page is unchanged.

The opening story, portrait policy, level masks, artwork palette, gameplay, win/celebration flow, repeat-purchase rules, life settlement and current checkpoint-65/66/67 fixes are retained. All previously existing metadata and asset GUIDs are preserved; shared artwork and fonts are not replaced.

## Integration details and files

The package's generator, validator, view and offer-state model are integrated in `App/NoMovesDesign/Editor/NoMovesPrefabBuilder.cs`, `NoMovesPrefabValidator.cs`, `Runtime/NoMovesOverlayView.cs`, `ContinueCanvasProfile.cs` and `ReferenceLogic/ContinueOfferViewModel.cs`. The existing project uses dynamic uGUI fonts and has no TMP dependency. The generator/view were adapted to that UI system, using the same approved fonts and small live-text shadows. No engine, SDK, package or assembly-definition upgrade was introduced. This is not an unmodified import of the supplied TMP generator.

The generated inactive asset is `App/NoMovesDesign/Generated/ContinueOverlay_R3.prefab`. `NoMovesAssets.cs`, `Editor/NoMovesSetup.cs` and `Resources/HOTR_NoMoves/Design.asset` bind it without changing the resource GUID. `NoMovesR3Binding.cs` connects presentation callbacks to the existing controller and service. It supplies display values only; the real quote identity, pending operation and durable receipt stay in the existing transaction path. The new view replaces the legacy offer while retaining the native notice, Shop, confirmed exit and unknown-purchase views. Only one offer canvas is active.

`NoMovesPage.cs` owns this handoff and the corrected in-level Shop rows/footer. `NoMovesText.cs` adds localized quote-state messages. `NoMovesController.cs` preserves repeat-purchase reset/recovery and retries missing presentation resources as an error, rather than showing false unavailability. No animation callback mutates currency, moves or lives.

All eleven pre-existing No Moves PNG masters match R3 byte-for-byte. Only `NM_Wallet_Plus.png` is new; its supplied GUID is retained. The clarity registry keeps all 59 current entries and adds that sprite, for **60**. R3 documentation is retained in `NoMovesDesign/Documentation/R3`; the package's duplicate shared assets, optional global guard/registry replacements, reference economy replacement and assembly definitions are not blindly imported. `Package_Review.json` and `Source_Delta.json` record provenance and preservation.

## Verification

Evidence: `Verification/Evidence/NoMovesR3`; gallery: `Comparison.html`; collector: `Verification/Tools/collect_no_moves_r3_results.py`.

- The generated prefab passes the supplied structural validator in the pinned Editor. The native connected UI suite passes **37,460 checks over 175 layouts**, covering five locales, five sizes/densities and seven view states, plus the five balance boundaries within offer layouts. It checks compact sizing, actual slice density, left wallet/plus, coin-card presence/actions, Retry, same-board repeated purchases, pending recovery and voluntary exit. Russian card-title overlap found during visual review was corrected using native text fitting.
- Native transaction checks pass: **4,232** base checks over **350** boards and six disk cuts, plus **93** repeat checks and **18** additional disk fault/restart cuts for first/second/third purchases.
- Existing native regressions pass: **534** general, **13,571** profile/transaction/font, **17** connected smoke, **10,285** timing and **81,325** individual-fall checks. The final UI-only Shop correction was rechecked with the native layout/flow suite; the model/service code did not change.
- The package HTML reference is captured at 393 by 852 logical pixels/DPR1. A capture-only viewport-width rule compensates for headless Chrome's minimum window width; the source artwork and reference logic are unchanged. It is labelled **design reference**, not Unity evidence. Native images at the same logical size show the corrected geometry. The reference's demo cash price intentionally differs from the app's honest Shop action. The boards are different fixtures.
- Android verification is separate: isolated memory profiles, actual ADB purchase taps, and test-driven gameplay commands for the five intervening repeat-purchase moves. The eleven cases include 1,600-to-700 spending, 700/zero/899 direct Shop routing, exact 900 spending, Shop Back, repeated purchases, third-purchase prepared/committed recovery and confirmed exit. Real QA profile/preference hashes are audited separately; no owner profile is substituted.

During preliminary verification, the normal QA startup regenerated one legitimately due life (three to four). That was detected by the strict save-hash audit; no saved state was rolled back. The final report records the subsequent clean baseline and test scope. Final APK/source/device status is recorded in `Summary.json`, `APK_Artifact.json`, `Source_SHA256.json` and `Android/Summary.json`.

Final completion: `PASS_TARGETED_NO_MOVES_R3`. The final APK is 301,609,820 bytes, SHA-256 `887a30d55ba9334f2f1a21e258a616f6bfe8f992ce1c87b8bc8f338aaa480e1d`, built from the frozen inventory of 5,087 Unity inputs. Compilation, import audit (60 assets, zero errors), clean packaging, signature, CRC, ZIP alignment and static ELF segment checks pass. All eleven final Android cases pass on QA (`emulator-5556`); real save/preference hashes match both after the isolated probes and ordinary startup. The QA instance has source70; main retains deployment64. Reviewed captures and hashes are in `Visual_Review.json` and `Comparison.html`.

Production continuation quotes and real coin purchases remain disabled pending authoritative wallet/attempt and store-validation integration. No payment, physical-device, full-campaign or all-feature certification is claimed. Main LDPlayer is not updated by the dedicated QA installation.

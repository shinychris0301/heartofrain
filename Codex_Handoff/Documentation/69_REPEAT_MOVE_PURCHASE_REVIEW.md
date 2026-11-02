# Repeat purchases of extra moves

24 October 2026. This changes checkpoint 68's provisional one-purchase rule at the owner's request. A player who exhausts purchased moves can buy another **five moves for 900 coins** in the same attempt, and can repeat while their wallet permits. The price and move quantity do not escalate. Production wallet/store limitations from checkpoint 68 remain in effect.

## Cause and changes

The previous offer had `maximumContinues=1`, the service enforced that limit at quotation/preparation/purchase, and profile validation rejected a continuation count above one. Consequently a second exhaustion could only end the level. These were the approved provisional rules at checkpoint 68; the new request supersedes that restriction.

- `App/Profile/Runtime/ContinueService.cs`: zero now means no configured purchase limit. The live policy is `NoMovesR2-Repeat-Development-v2`; each exhaustion still requires a fresh quote and operation. Validation accepts repeated purchase counts, and incrementing the count is checked. Explicit finite policies remain supported for tests/configuration.
- `Resources/HOTR_NoMoves/Design.asset` and `App/NoMovesDesign/Editor/NoMovesSetup.cs`: the live resource and its configuration command both use the repeat policy, so running Setup cannot restore the old one-purchase restriction.
- `App/NoMovesDesign/NoMovesController.cs`: each reopening resets the previous quote, notice-dismissal flag, readiness, operation and status text before capture/reconciliation. An earlier panel's quote/status cannot leak into a later exhaustion.

Each purchase still uses the same durable profile transaction for the debit, move grant and receipt. It keeps the same live board/model, goals, RNG, attempt and inventory. It does not charge a life or grant starting boosters. Old quotes cannot buy a later offer; replaying an old receipt cannot reset a newer board or clear a newer pending operation. Insufficient coins still opens Shop immediately without preparing a spend. The board and life remain preserved while Shop is open; real coin purchases are unavailable until store integration exists.

The existing Continue/Shop reopening exception remains: prepared/committed purchases reconcile once, including the third purchase. Once normal gameplay resumes, the existing interrupted-gameplay settlement rule applies. Voluntarily ending the level still requires confirmation and settles one loss. Final-move victory keeps priority over the exhaustion offer and uses the current celebration/Home flow.

No artwork, palette, GUID, level masks, shared imports, engine or SDK changed. The checkpoint-65/66 corrections and checkpoint-67 cascade responsiveness remain preserved. Four production/configuration files changed; the remaining Unity changes are verification code and its new metadata.

## Verification and evidence

`Verification/Evidence/RepeatMoves` is separate from the historical checkpoint-68 evidence. Run native tests with `powershell -ExecutionPolicy Bypass -File Verification/Run-NoMovesR2.ps1 -EvidenceFolder RepeatMoves`. Run the QA device checks with `Verification/Tools/run_no_moves_r2_device.py --serial emulator-5556 --evidence RepeatMoves --install`. The latter refuses an active QA saved attempt and uses isolated memory profiles.

- New repeat transaction suite: **93 checks**, five purchases in one attempt, consuming every granted move between purchases. Covers zero balance after the fifth purchase, unchanged lives, duplicate commands, old quotes/receipts/acknowledgements, and upgrading a checkpoint-68 pending purchase.
- File recovery: **18 fault/restart cuts**, spanning preparation, purchase and acknowledgement before/after commit for purchase ordinals one, two and three. These supplement the six existing transaction recovery cases.
- Connected native gameplay/UI: **15,732 checks over 125 layouts**. Buys second and third move bundles through the live controller after all five preceding moves are consumed, preserves the live model, rejects stale receipts, and confirms voluntary loss afterward.
- Existing suites pass: **4,232** base continuation/model checks over **350** board cases, **534** general, **13,571** profile/transaction/font, **17** connected smoke, **10,285** timing and **81,325** individual-fall checks. These are native Editor tests, not physical-device tests.

The final Android build, eight device scenarios, source hashes and selected visual review are recorded separately in `Summary.json`, `Android/Summary.json`, `Source_SHA256.json` and `Comparison.html`. Device purchase buttons use actual ADB taps. The repeat case starts after one committed purchase, buys a second bundle, consumes its five moves through test-driven gameplay commands/animations and taps to buy a third. Insufficient coins after two purchases, third-purchase pending/committed recovery, Shop Back and confirmed exit have separate cases. Android fixtures use a synthetic initial one-move budget; they do not substitute or alter the owner's profile.

Final Android result: **all eight scenarios pass**. The repeat case records two real purchase-button taps, five intervening gameplay moves and three total purchases, ending at 350 coins, five moves and five lives. Both third-purchase recovery cases also end at 350 coins/five moves/five lives. Insufficient balance after two purchases opens Shop at 710 coins and five lives; confirmed voluntary exit spends one life. The QA profile/preference hashes match before installation, throughout testing and after ordinary startup. QA is left at its normal Home.

The ARM64 development APK is **301,540,581 bytes**, SHA256 `c32d9b124b660b98eeb5fc1268425ead8b778824def2127fb6e75a94b016fcd3`. Build errors: zero. Clean packaging, signature, CRC/alignment, static ELF and all 59 registered import checks pass. **5,038** Unity inputs are frozen and checked against the tested source. The final collector reports `PASS_TARGETED_REPEAT_MOVES`.

This is a development local-wallet continuation feature. Production continuation quotes and real coin-store purchases remain disabled pending authoritative wallet/attempt and store-validation integration. No physical-device, IAP, production-service, full-campaign or all-feature certification is claimed. Main deployment 64 is not replaced by this QA verification.

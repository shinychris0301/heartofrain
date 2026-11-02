# No Moves R2: development continuation

> Historical checkpoint 68. The owner replaced the provisional one-purchase restriction with repeat purchases in [checkpoint 69](69_REPEAT_MOVE_PURCHASE_REVIEW.md). The results below describe the earlier build.

24 October 2026. Unity 2022.3.62f3; live M46 model/M47 screen, HomeLevelFlow and current M67 win presentation. The No Moves R2 package is integrated with the existing durable profile rather than introducing its reference service as a second wallet.

The owner approved a configurable development offer of **five moves for 900 coins, once per attempt**, and reopening an interrupted **Continue/Shop or pending-purchase** board. Ordinary gameplay still settles one interrupted loss on reopening. This work preserves the checkpoint-65/66 corrections and the uncommitted checkpoint-67 responsiveness changes. Historical evidence remains historical.

## Behavior

- After the final move fully resolves and goal flights arrive, a remaining objective opens the supplied Out of moves notice and Dariya Continue panel. A final-move win follows the existing celebration/Home flow instead.
- Affordable Play On atomically debits 900 coins, records an operation receipt and grants five moves to the **same live model**. Board contents, goals, RNG, obstacles, score, inventory and attempt identity are preserved. There is no new reservation, starting-booster grant or life debit.
- Insufficient balance opens the in-level Shop immediately, without dispatching a purchase. Shop Back/Close returns to the same offer and board. The existing catalog is displayed, but coin purchases are honestly marked unavailable: no store provider exists.
- End level requires confirmation; cancellation returns to the offer. Confirmed exit uses existing loss settlement exactly once. A second exhaustion after the one approved purchase offers End level rather than another purchase.
- The Awaiting checkpoint stores whether Offer or Shop was open. Prepared operations and committed receipts survive process interruption. Reopening reconstructs the exact saved board/RNG and reconciles any purchase before allowing input or exit. It neither refunds a committed purchase nor charges it again.
- Purchased unused moves remain resumable until the next gameplay command. The checkpoint is durably invalidated **before** that command runs; subsequent ordinary interruption follows the existing one-loss rule. A failed invalidation blocks the command and presents existing save-error recovery.

## State and code

`Profile/Runtime/ContinueService.cs` owns the continuation journal, frozen quotes, pending commands, debit/grant receipts and profile commit. It shares `ProfileService.Change` with other local wallet writers. Known insufficient/expired responses reconcile without spending; unknown commit outcomes reuse the same operation. No reward or debit is performed by an animation callback.

`M46/Runtime/BoardContinuation.cs` captures/restores private deterministic model state and applies an absolute, operation-keyed move grant. `M47/Runtime/GameplayContinuation.cs` validates the receipt against a checkpoint before changing the live board. `GameplayScreen` defers terminal UI while restoration is prepared and waits for goal-flight arrival before presenting exhaustion.

`PreLevel/Runtime/ContinueLevelFlow.cs` connects capture, resume, input invalidation and the existing settlement flow. Restoration verifies the authored level configuration, restores attempt tool bindings and uses an independent completion serial. Android visual review caught an initialization race: checking only whether the tutorial canvas was visible could restore gameplay before tutorial initialization, allowing Home to repaint over the board later. Restoration now waits for both initialization and dismissal; the final device probe also rejects Home being visible over restored gameplay. `PlayerProfile.cs` validates old profiles with an absent journal and exempts only restorable continuation checkpoints from ordinary interruption recovery.

`NoMovesDesign/NoMovesController.cs`, `NoMovesPage.cs`, `NoMovesText.cs` and `NoMovesAssets.cs` implement the supplied notice, band, Dariya, badge, wallet, confirmation and guarded recovery views. Native UGUI uses the project's existing fonts and shared primary/close/chrome sprites. Five languages, safe areas, compact phones and portrait tablets are covered. Button callbacks carry a layout generation so a stale button cannot spend newly credited coins.

Eleven new PNG masters retain source pixels and GUIDs; shared assets and all pre-existing metadata remain unchanged. Sixty package files (art, metadata, data, localization, documentation and two reference sources) are imported. The clarity registry retains all 48 existing entries and adds the 11 new sprites, for **59**. The first Android build guard caught a stale package entry for its unimported Primary copy; that entry was removed because the live design uses the already registered project Primary. The new resource binding is `Resources/HOTR_NoMoves/Design.asset`; all previous resource bindings remain present.

## Verification

Evidence and scopes are in `Verification/Evidence/NoMovesR2`; the gallery is `Comparison.html` and the final collector is `Verification/Tools/collect_no_moves_r2_results.py`.

- Native transaction/model suite: **4,232 checks**, **350 board roundtrips** across all 50 levels and normal/six power cases, plus **six file fault/restart cuts**. Tests include exact-balance spending, duplicate receipts, changed wallets, expired quotes, one-purchase limits, pending-exit refusal and ordinary interruption after checkpoint invalidation.
- Connected native play/UI suite: **15,719 checks, 125 layouts**, across five languages, five sizes/densities and five modal states. Uses real GameplayScreen/HomeLevelFlow with isolated profiles and a synthetic one-move budget; checks unpaid Shop restoration, paid-unused restoration, same-model purchase, final-move win, stale input, confirmed loss and existing retry routing.
- Existing native regressions pass: **534** general, **13,571** profile/transaction/font, **17** connected smoke, **10,285** timing and **81,325** individual-fall checks. These are Editor checks, not physical-device tests.
- Final Android verification passes **six isolated scenarios**: affordable purchase, insufficient balance, saved-Shop Back, prepared-command recovery, committed-purchase recovery and one-limit confirmed exit. Interactive cases use real ADB button taps. Real QA profile and preference hashes match before installation, throughout the probes and after ordinary startup. The QA instance is left at its normal Home; the main LDPlayer instance is unchanged.

The final ARM64 development APK is **301,522,481 bytes**, SHA256 `5eb7359c357ceeed2541a75029fe2d89043548e33ae747a40cc36c170984dfa0`. Native build: zero errors; signature, CRC/alignment, static ELF and clean packaging checks pass. `Source_SHA256.json` freezes **5,036** Unity inputs; the collector verifies their exact contents and inventory against the built/tested source. The final summary is `PASS_TARGETED_NO_MOVES_R2`.

## Remaining limits

This is a **development local-wallet feature**, not production commerce. Release builds and the backend gift configuration do not issue continuation quotes. The portable backend is not a unified gameplay/wallet authority, and no validated store purchase can currently supply coins. Connecting authoritative attempts, wallet transactions and IAP is required before enabling production Play On or selling coins. Device UTC quotes here are a development policy, not trusted server time.

No physical-device, production-backend, all-feature or full-campaign certification is claimed. The existing uncompressed UI memory/compression release gate remains open; this work preserves the established baseline rather than silently changing shared importers. No artwork redesign, level-mask change, engine/SDK upgrade or owner-save substitution was made.

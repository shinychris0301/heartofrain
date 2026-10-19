# Task 02 — Engine safety: no-fault deadlock handling and transactional turns

Read `AGENTS.md`, `docs/codex/FINDINGS.md` (ENG-01, ENG-02) and `docs/codex/DECISIONS.md` (D2).
Prerequisite: task 01 is merged and the harness is green. Branch: `codex/02-engine-safety`.

**`--update-golden` is NOT allowed in this task.** The existing golden data, all 50 levels and the
5 replays must stay byte-identical in behaviour.

## Part A — ENG-02: transactional turn entry points

Files: `Unity/Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs` and
`Unity/Assets/HeartOfTheRain/Boosters/Runtime/BoosterRulesPure.cs` (`UseBooster`).

1. Add `public string fault;` to `TurnResult`. Today it reads:
   `[Serializable] public class TurnResult { public bool accepted; public string reason; public List<BoardStep> steps=new List<BoardStep>(); }`
2. Add a private memento to `BoardModel` that captures **all** mutable model state:
   - deep copies of every `Piece` (`Piece.Copy()`), with their keys;
   - the values of `Goals`;
   - `Moves`, `Turn`, `Status`, `QuietMoves`, `GrowthUsed`;
   - `random`, `nextId`, `activationSerial`, `mossHit`;
   - `startingPowersApplied`, declared in `StartingPowersPure.cs`. It is the same partial class, so it is accessible.

   Grep every `partial class BoardModel` file for other mutable fields and include them too. List them in your report.
3. `Restore(memento)` puts that state back exactly. `Pieces` must contain fresh copies keyed by
   `Key(p.x,p.y)`. Then clear `pending`, `queued` and `acceptedDamage`.
4. Rename the existing bodies of `Swap`, `Tap` and `UseBooster` to private `SwapCore`, `TapCore` and
   `UseBoosterCore`, with unchanged contents. The public methods become:
   capture memento → `try { return XCore(...); } catch (Exception ex) { Restore(m); return Fault(ex); }`.
   `Fault(ex)` returns
   `new TurnResult{accepted=false,reason="Something went wrong. Your move was not used.",fault=ex.ToString()}`.
   `UseBooster` must also restore the caller's `BoosterInventory`, because `inventory.Spend(kind)` runs
   before `Finish`. Capture `hammer`, `axe`, `ram` and `atlas` (public fields) before calling
   `UseBoosterCore`, and write them back in the `catch` block. (If `inventory` is null, `UseBoosterCore`
   already rejects it, so guard the capture against null.)
5. The constructor and `Validate()` itself must keep throwing (load-time errors stay loud). Do not wrap
   `InjectReviewPower`, `TryPlaceStartingPowers` or `ValidateCampaignOpening`.
6. `M47/Runtime/GameplayScreen.cs`, method `Accept`. Current text:
   `void Accept(TurnResult result){if(!result.accepted){uiHint=result.reason;feedback.Play("ui_invalid",.65f);return;}uiHint="";Enqueue(result.steps);}`
   When `result.fault` is non-empty, call `Debug.LogError("Board rule fault: "+result.fault);` before the
   existing rejection handling. Change nothing else on that line.

## Part B — ENG-01: deadlock fallback and no-fault endings

1. In `BoardModel.cs`, add
   `public static bool IsNoFaultEnd(string status){return status=="No legal moves"||status=="Resolution limit";}`.
2. Rewrite `Shuffle(TurnResult result)` exactly per DECISIONS D2:
   - **Keep the existing 100-attempt permutation loop byte-identical**, including its `Rand` calls and
     the success branch. Deterministic replays depend on it.
   - After it fails, restore the original colours (as today), then run up to 100 recolour attempts:
     `gems[i].color=NewColor()` for every gem in the existing `gems` order. Accept the first attempt where
     `Matches(null).Count==0&&LegalSwaps().Count>0`, then `Finish(step,result);return;`.
   - If recolouring fails, restore the original colours. If `gems.Length>0`, pick the gem nearest
     `((Level.columns-1)*.5f,(Level.rows-1)*.5f)` by Manhattan distance, ties broken by lowest `Key(x,y)`
     (same ordering style as `TryPlaceStartingPowers`). Set `family="power"`, `power=4`, `color=-1`,
     add `step.created.Add(p.Copy())`, then `Finish(step,result);return;`.
   - Only when `gems.Length==0`: `Status="No legal moves";` (no `Finish` call, matching today's failure path).
   - Use the existing `"shuffle"` step kind for every outcome. Do not introduce a new step kind. Read
     `M46/Runtime/BoardPresentation.cs` and `M47/Runtime/FeedbackPlanPure.cs` to confirm that a
     `"shuffle"` step carrying a `created` piece is rendered. Usually the after-snapshot drives idle
     rendering; `Regrow` does the same with a `"grow"` step. Report what you found. If it would not render,
     stop and report instead of inventing presentation code.
3. Leave the `"Resolution limit"` guards in `Settle` as they are.
4. `M47/Runtime/GameplayScreen.cs`, method `UpdateHUD`. Current text:
   `if(!Busy&&!resultShown&&board.Status!="Playing"){resultShown=true;hud.ShowResult(board.Status=="Won",board.Level.globalLevel);}`
   Change it so that `BoardModel.IsNoFaultEnd(board.Status)` calls `hud.ShowBoardReset(board.Level.globalLevel)`,
   and every other non-`"Playing"` status keeps calling `hud.ShowResult(...)` exactly as now.
5. In `M47/Runtime/GameplayHUD.cs`, add
   `public void ShowBoardReset(int number)`, modelled on the loss branch of `ShowResult`:
   - `PauseChanged?.Invoke(true);`
   - `Dialog("Board reset","No moves are possible. No life was lost.")`
   - the same two `Picture` calls as the loss dialog;
   - one `Click(p,"Button_Teal","Try again",64,446,432,94,()=>{Close(true);RetryPressed?.Invoke();});`

   It must not call `ResultRequested` and must not play `"level_lose"`.
6. Add translations to `LocaleCatalog.cs` (AGENTS.md §4) for these strings. `"Try again"` already exists, so check before adding:
   - `"Board reset"`
   - `"No moves are possible. No life was lost."`
   - `"Something went wrong. Your move was not used."`

## Tests to add (harness)

Use reflection to call private members where needed. That is acceptable in tests.

- `Fault_RestoresStateAndRejects`:
  - Load level 1. Pick a legal swap S from `LegalSwaps()`.
  - Corrupt one gem that is not in S by setting `color=9` through `board.Pieces`.
  - Record the fingerprint, `Moves` and `Turn`, then call `Swap(S)`.
  - Assert `accepted==false`, `fault` is non-empty, and fingerprint, `Moves` and `Turn` are unchanged.
  - Assert `Pieces.Count` is unchanged and every key equals `Key(p.x,p.y)`.
- `Fault_UseBoosterRestores`: same idea, through `UseBooster(BoosterKind.Hammer, …)`. Also assert that the
  inventory count is unchanged after the fault.
- `Shuffle_RecolourFallback`:
  - Load a level and set every gem to colour `activeColors[0]` through `Pieces`, so every permutation matches.
  - Invoke private `Shuffle(new TurnResult())`.
  - Assert `Status=="Playing"`, `Matches(null)` (via reflection) is empty and `LegalSwaps().Count>0`.
- `Shuffle_GiftRocketFallback`:
  - Before constructing the board, set `level.activeColors=new[]{0}`; after constructing, set every gem
    colour to `0`. Invoke `Shuffle`.
  - Assert `Status=="Playing"`, exactly one new power with `power==4` at the expected nearest-to-centre
    cell, and `board.Validate()` passes.
- `Shuffle_NoGems_NoFaultStatus`: remove every gem from `Pieces`, invoke `Shuffle`, assert
  `Status=="No legal moves"` and `BoardModel.IsNoFaultEnd(Status)`.
- The existing campaign, determinism and golden tests must pass **unchanged**.

## Acceptance criteria

1. The harness is green with the golden data untouched (`git diff --stat Tools/HeadlessTests/Golden` is empty).
2. No public signature changed except the additions listed in this prompt.
3. `Shuffle`'s first loop is byte-identical to the baseline. Quote both versions in your report.
4. `GameplayScreen.cs` and `GameplayHUD.cs` changes are limited to the lines described above, plus the new method.
5. Every member you reference in the MonoBehaviour files exists. List each one with its declaring file.

## Human verification in Unity (copy into your report)

- [ ] Project compiles with no errors.
- [ ] Play `M65_First_Start`, start a level, and make normal moves. No regressions.
- [ ] Use the M48 review scene's review tools to force a deadlock if available. Otherwise trust the
      headless tests, but visually confirm that a reshuffle still animates.
- [ ] "Board reset" dialog text appears correctly in all 5 languages (switch language in App Settings).

# Task 03 — Rule fixes: Seeker+Seeker, power-up spawn cell, moss config

Read `AGENTS.md`, FINDINGS ENG-03/04/05 and DECISIONS D3/D4/D5. Prerequisites: tasks 01 and 02 are merged.
Branch: `codex/03-engine-rules`.

Do the three parts **in order**, running the harness after each. If a part's result contradicts the
expectations below, stop and report. Do not continue to the next part.

`--update-golden` is allowed **only in Part B**, and only under the conditions stated there.

File: `Unity/Assets/HeartOfTheRain/M46/Runtime/BoardModel.cs` (after task 02, the turn bodies live in `SwapCore`).

## Part A — ENG-03 / D3: Golden Seeker + Golden Seeker

1. Do **not** change `Combo(int a,int b)`. Its return values are combo-plan ids consumed by `ReviewPlan`.
2. In `SwapCore`:
   - Compute `bool seekerPair=a.family=="power"&&b.family=="power"&&a.power==16&&b.power==16;`.
   - The refusal line (currently `if(a.family=="power"&&b.family=="power"&&combo<0){result.reason="This combination has no approved rule";return result;}`)
     must not fire when `seekerPair` is true.
   - In the activation section (after `BeginTurn` and the swap step's `Finish`), add a branch *before*
     `if(combo>=0)`. When `seekerPair` is true:
     `pending.Enqueue(new Activation{kind=16,originId=a.id});pending.Enqueue(new Activation{kind=16,originId=b.id});queued.Add(a.id);queued.Add(b.id);`.
   - Keep the existing `if/else if/else` chain intact for all other cases (convert it to `else if` after the new branch).
3. In `LegalSwaps()`, the power-pair condition (currently `Combo(a.power,b.power)>=0`) must also accept
   `a.power==16&&b.power==16`.
4. Tests:
   - `SeekerPair_IsLegalAndActivatesBoth`:
     - Load level 1. Inject kind 16 on two horizontally adjacent gems with
       `InjectReviewPower` (choose the cells programmatically).
     - Assert that the pair appears in `LegalSwaps()`.
     - `Swap` them and assert `accepted`, `Moves` decreased by exactly 1, both seeker ids are gone, and
       `result.steps` contains at least two `"power"` steps.
     - `Validate()` passes.
   - Same test for a vertical pair.
5. Expected: the golden data and replays are unchanged, because no recorded run ever swapped two seekers.
   If golden data changes, stop.

## Part B — ENG-04 / D4: power-up spawn cell

1. Change the signature to `void ResolveMatches(List<Match> groups,TurnResult result,int preferred=-1,int secondary=-1)`
   and the `keep` ordering to:
   `.OrderBy(k=>Pieces[k].id==preferred?0:Pieces[k].id==secondary?1:2).ThenBy(k=>k)`.
2. In `SwapCore`, change `else ResolveMatches(groups,result,b.id);` to `else ResolveMatches(groups,result,b.id,a.id);`.
   Do not change any other caller.
3. Tests:
   - `SpawnCell_DraggedPieceFormsMatch`: build a deterministic situation in which only the dragged piece `a`
     completes a 4-in-a-row at its landing cell, and `b` is not part of any match. Choose a level and set gem
     colours through `Pieces`; make sure the arrangement has no pre-existing matches.
     Assert that the created power (`result.steps[...].created`) sits at `(bx,by)`.
   - `SpawnCell_OriginPieceFormsMatch`: mirror case; assert the power is at `(ax,ay)`. This is unchanged behaviour.
4. Run the harness **without** `--update-golden` first.
   - If everything passes, you are done with Part B. Report "no golden impact".
   - If `CampaignValidation_AllLevelsAndReplays` fails: **stop**. Report which replay and which action index
     diverged, and do not modify the fixture. The owner must decide whether to re-record that replay.
   - If only `RulesGolden_Baseline` differs: for each differing level, find the first diverging action and
     confirm that the cause is a power-up created at `a`'s cell instead of the lowest key. Inspect the step's
     `created` entries. Only then run `--update-golden`, and list each level with that evidence in the report.

## Part C — ENG-05 / D5: moss regrowth config

1. Extend `GrowthRule` to:
   `[Serializable] public class GrowthRule { public bool enabled; public int undamagedMoves,maxNewClumps,afterConsecutiveMovesWithoutMossDamage,maxNewCellsTotal; }`.
   JsonUtility ignores other keys, so the descriptive string fields in the level JSON are fine.
2. In `Regrow`, compute
   - `int threshold` = the first positive value of `undamagedMoves` or `afterConsecutiveMovesWithoutMossDamage`, else `2`;
   - `int cap` = the first positive value of `maxNewClumps` or `maxNewCellsTotal`, else `3`.

   Guard `Level.mossRegrowth` being null: the harness emulation never produces null, but stay defensive.
   Replace only `QuietMoves=Math.Min(2,QuietMoves+1);if(QuietMoves<2||GrowthUsed>=3)return;` with the
   equivalent using `threshold` and `cap`. Keep the `enabled` line and everything else byte-identical.
3. Search all usages of `QuietMoves` and `GrowthUsed` (outside `BoardModel` too) and confirm that no
   presentation code assumes the literal 2 or 3. Report the results.
4. Tests:
   - `Moss_ConfigAliasesParsed`:
     - L027 (alias schema): threshold 2, cap 3.
     - L044 (`undamagedMoves` schema): threshold 2, cap 3.
     - A synthetic `GrowthRule{enabled=true,undamagedMoves=1,maxNewClumps=1}` grows after 1 quiet move and
       at most once. Drive it through public `Swap` on a level with moss (L027), with the rule replaced
       before the board is constructed.
   - Golden data and replays must be **unchanged** (every level uses 2/3 today). If they change, stop.

## Acceptance criteria

1. The harness is green. Golden changes, if any, come only from Part B and are fully justified in the report.
2. `Combo()` and `Fingerprint()` are byte-identical to the baseline.
3. The `Chapter01M07/Scripts/*` duplicates are untouched (they are legacy demo code; see AGENTS.md §8).
4. The diff touches only `BoardModel.cs`, the new or changed tests, and (only if Part B allowed it) `Golden/rules_baseline.json`.

## Human verification in Unity (copy into your report)

- [ ] Compiles.
- [ ] M48 review scene: use the review drawer to place two Golden Seekers side by side and swap them.
      Both fly, there are no errors in the Console, and the board settles.
- [ ] Make a 4-match by dragging a gem into place. The rocket appears where the dragged gem landed.
- [ ] Level 27: moss spreads after 2 moves without hitting moss, at most 3 times (unchanged).

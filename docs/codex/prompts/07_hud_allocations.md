# Task 07 (optional) — Remove per-frame allocations in the gameplay HUD and render loop

Read `AGENTS.md` and FINDINGS APP-07. Run this after tasks 02–05, since it touches the same files.
Branch: `codex/07-hud-allocations`. `--update-golden` is NOT allowed.

**Behaviour must be pixel- and timing-identical.** This is a pure performance change.

## Changes

Files: `Unity/Assets/HeartOfTheRain/M47/Runtime/GameplayHUD.cs` and `GameplayScreen.cs`.

1. `GameplayHUD.UpdateState`:
   - Cache the last displayed move count. Assign `moves.text` and `moves.color` only when the count changes.
   - Cache the last hint source string and the `GameLocale.Revision` it was translated at. Recompute
     `helper.text=GameLocale.T(...)` only when either changes.
   - Replace `string signature=string.Join("/",Array.ConvertAll(goals,g=>g.family));` with an allocation-free
     comparison against a cached `string[]` of families. Rebuild the goal widgets under exactly the same
     condition as today, which is that the family sequence changed.
   - The booster loop: assign `counts[i].text` only when the count changes. Assign `interactable` and
     `sprite` as today (cheap), or cache them too, but the result must stay identical.
   - Language switches must still refresh every text in the HUD. Explain how your caching handles a
     `GameLocale.Revision` change.
2. `GameplayHUD.Update` and `Fit`: cache the `Dialog` `RectTransform` when `Dialog(...)` creates it, and
   clear the cache in `Close(...)`. Use the cache instead of `modal.Find("Dialog")`.
3. `GameplayScreen.Render`: count `uiOverlay` draws inside the existing `foreach(var d in draws)` loop,
   and replace `draws.Count(d=>d.uiOverlay)` with that counter. The value must be identical: today it counts
   **all** `uiOverlay` draws, including those skipped because `sprite==null||d.alpha<=0`. Preserve that exactly.

Do not touch `BoardPresentation.Sample` (deferred, DEF-04).

## Acceptance criteria

1. The harness is green.
2. For each change, the report explains why the observable output is identical, including the locale-switch case.
3. No other files change.

## Human verification in Unity (copy into your report)

- [ ] Compiles.
- [ ] Play a level: the moves counter, goal counters (with pulse), helper hints and booster counts update as before.
- [ ] Switch language mid-level via settings and resume: the HUD texts update.
- [ ] Profiler (Deep Profile off): `GC.Alloc` in `GameplayScreen.Update` drops while idle.

# Task 05 — Lives economy: charge losses, refill timer, retry through pre-level, safe win fallback

Read `AGENTS.md`, FINDINGS APP-02/03/04/06 and DECISIONS D2, D7, D8.
Prerequisites: tasks 01, 02 (for `BoardModel.IsNoFaultEnd`) and 04 (for `SaveProgress`, `nextLifeAt`) are merged.
Branch: `codex/05-lives-and-retry`. `--update-golden` is NOT allowed.

## 1. Pure rules — new file `App/Progress/Runtime/LivesRulesPure.cs` (with `.meta`)

Namespace `HeartOfTheRain.App.Progress`. Only `System` may be used. Add the file to `HotR.Core.csproj`.

```csharp
public static class LivesRules {
    public const int RefillSeconds=1800;
    // Normalises lives into [0,max]. Starts or clamps the timer, and grants every life that is due.
    public static int Refill(int lives,int maxLives,ref long nextLifeAt,long now);
    // Refill first, then spend one life if any. Starts the timer if none is pending.
    public static int Spend(int lives,int maxLives,ref long nextLifeAt,long now);
    public static long SecondsUntilNext(int lives,int maxLives,long nextLifeAt,long now); // 0 when full
    public static string FormatCountdown(long seconds);                                    // "m:ss", e.g. 1800 -> "30:00", 59 -> "0:59"
}
public sealed class AttemptLifeLedger {
    // At most one charge per launch ticket id. Ids are increasing positive integers.
    public bool TryCharge(int attemptId);
}
```

Exact semantics of `Refill`:
1. `max=Math.Max(1,maxLives)`; clamp `lives` into `[0,max]`.
2. If `lives>=max`: set `nextLifeAt=0` and return `max`.
3. If `nextLifeAt<=0` or `nextLifeAt-now>RefillSeconds`, set `nextLifeAt=now+RefillSeconds`.
   The second case handles a device clock that moved backwards.
4. `while(lives<max&&now>=nextLifeAt){lives++;nextLifeAt+=RefillSeconds;}`
5. If `lives>=max`, set `nextLifeAt=0`. Return `lives`.

`Spend`: `lives=Refill(...)`. If `lives<=0`, return 0 and leave the timer unchanged. Otherwise
`lives--`; if `nextLifeAt<=0`, set `nextLifeAt=now+RefillSeconds`. Return `lives`.

## 2. HomeLevelFlow (`App/PreLevel/Runtime/HomeLevelFlow.cs`)

Add the following fields:
- `readonly AttemptLifeLedger lifeLedger=new AttemptLifeLedger();`
- `int currentAttempt;`
- `float nextLivesTick;`

Then add these helpers:

```csharp
static long Now(){return DateTimeOffset.UtcNow.ToUnixTimeSeconds();}
// Mutates lives only. Callers apply state and save.
bool ChargeLife(int attempt){if(!lifeLedger.TryCharge(attempt))return false;home.State.lives=LivesRules.Spend(home.State.lives,home.State.maxLives,ref nextLifeAt,Now());return true;}
void TickLives(){ /* Refill. If lives changed: home.ApplyState(home.State). If lives or nextLifeAt changed: SaveProgress(). Then RefreshLivesMessage(). */ }
void RefreshLivesMessage(){ /* If session.IsOpen && !session.View.busy && home.State.lives<=0: set session.View.message to
   string.Format("No lives remaining. Next life in {0}",LivesRules.FormatCountdown(LivesRules.SecondsUntilNext(...)))
   and call modal.Show(session.View) only when the text changed. */ }
```

Before using `View.message` this way, read `PreLevelModal.cs` / `PreLevelLayout.cs` and confirm how it is
rendered. If the modal passes it through `GameLocale.T`, the `{0}` pattern entry translates it.
If it does not, build the text with `GameLocale.Format("No lives remaining. Next life in {0}",countdown)`.
Report which case applies.

Wire it in exactly like this:

- **Start()**: at the end, call `TickLives();`. This grants lives that refilled while the app was closed.
- **Update()**: as the first statement, add `if(session==null)return;`. Then add
  `if(Time.unscaledTime>=nextLivesTick){nextLivesTick=Time.unscaledTime+1;TickLives();}`.
  Keep the existing body after that.
- **OnApplicationPause(bool paused)** (added in task 04): `if(paused)SaveProgress();else TickLives();`.
- **Launch**: set `currentAttempt=ticket.id;` once `session.Complete(ticket)` has succeeded. Inside the existing
  `if(completion.Arm(ticket.id,ticket.level)){...}` block, after `hud.ExternalResultVisible=...;`, add:
  `hud.RetryPressed=()=>RetryFromCampaign(launched);hud.ContinuePressed=()=>ReturnHomeAfterUnsettledWin(launched);`.
  (`GameplayScreen.Start` assigned the standalone handlers earlier. `Launch` runs after `InitializationComplete`,
  so these overrides win. Confirm that ordering in your report.)
- **TryShowCompletion**: replace the first line,
  `if(!won||!source||source!=gameplay||!source.Ready||number!=source.CurrentLevel)return false;`, with:
  - `if(!source||source!=gameplay||!source.Ready||number!=source.CurrentLevel)return false;`
  - `if(!won){if(source.Model.Status=="Out of moves"&&ChargeLife(currentAttempt)){home.ApplyState(home.State);SaveProgress();}return false;}`

  Returning `false` for a loss keeps the HUD's existing loss dialog.
- **ConfirmExit**: replace `home.State.lives=decision.LivesAfter;` with `ChargeLife(currentAttempt);`.
  Keep `home.ApplyState(home.State);` and the `SaveProgress()` added in task 04.
- **New method `RetryFromCampaign(GameplayScreen source)`**:
  1. `if(!source||source!=gameplay)return;`
  2. `int level=source.CurrentLevel;string status=source.Model.Status;`
  3. `if(status!="Won"&&!BoardModel.IsNoFaultEnd(status)&&ChargeLife(currentAttempt)){home.ApplyState(home.State);SaveProgress();}`
     This covers a mid-level restart (`"Playing"`) and an "Out of moves" result whose charge was missed.
     The ledger guarantees a single charge.
  4. Tear down exactly as `ConfirmExit` does: `gameplay.gameObject.SetActive(false);Destroy(gameplay.gameObject);gameplay=null;modal.Hide();OpenPreview(level,true);`.
- **New method `ReturnHomeAfterUnsettledWin(GameplayScreen source)`**: `if(!source||source!=gameplay)return;`,
  then `Debug.LogWarning("Campaign could not settle this win; returning Home.",this);`, then tear down gameplay
  (`SetActive(false)`, `Destroy`, `gameplay=null`), `modal.Hide();home.SetPresentation(true,true);`.
  Do not open the next level.

Keep `using HeartOfTheRain.App.Progress;` and `using HeartOfTheRain.M46;` (the latter is already present).

## 3. Strings

Add `"No lives remaining. Next life in {0}"` to `LocaleCatalog.cs` with all 5 locales, keeping `{0}` in every
translation. Check whether `"No lives remaining"` already exists; do not duplicate it.

## Tests (harness)

- `Lives_FullStaysFull_NoTimer`
- `Lives_SpendFromFull_StartsTimer`: 5 → 4, and `nextLifeAt==now+1800`.
- `Lives_RefillAfter30Min`: 4 lives, 1800 s later → 5, timer cleared.
- `Lives_MultipleRefills`: 1 life, 95 min later → 4 lives, with the next life due 25 min later.
- `Lives_CapAtMax`: 0 lives, 10 hours later → 5.
- `Lives_BackwardClockClamped`: `nextLifeAt=now+100000` → clamped to `now+1800`.
- `Lives_SpendAtZero_NoChange`
- `Lives_FormatCountdown`: 0 → "0:00", 59 → "0:59", 1800 → "30:00", 3599 → "59:59".
- `Ledger_OnePerAttempt`: charging the same id twice returns false the second time; a higher id is allowed; 0 or negative ids are rejected.

## Acceptance criteria

1. The harness is green, and the golden data is untouched.
2. Changed files: `LivesRulesPure.cs` (+meta), `HomeLevelFlow.cs`, `LocaleCatalog.cs`, `HotR.Core.csproj` and tests.
   **No changes** to `GameplayHUD.cs`, `GameplayScreen.cs` or `PreLevelSession.cs`. If you believe one is required,
   stop and explain why.
3. The report contains a table of every path that can reduce lives, and shows that each goes through
   `ChargeLife`. Paths: loss, exit confirm, restart from pause, retry after loss, retry after board reset.
4. Standalone review scenes (no `HomeLevelFlow`) keep their in-place retry.

## Human verification in Unity (copy into your report)

- [ ] Compiles.
- [ ] Lose a level: lives drop by 1 when "Out of moves" appears. "Try again" opens the pre-level screen for the same level.
- [ ] Exit a level from Settings: lives drop by 1 (once), and the pre-level screen opens.
- [ ] Lose at 1 life: the pre-level screen shows "No lives remaining. Next life in 29:5x" and counts down; Play is refused.
- [ ] Wait or fake time (temporarily set the PlayerPrefs `nextLifeAt` key in the past) → a life is restored on resume.
- [ ] Board-reset dialog (task 02): "Try again" costs no life.
- [ ] Win flow is unchanged: the celebration plays, then the next-level preview opens.

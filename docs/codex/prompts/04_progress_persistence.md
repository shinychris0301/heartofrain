# Task 04 — Persist player progress, booster stock and in-level boosters

Read `AGENTS.md`, FINDINGS APP-01/APP-05 and DECISIONS D6. Prerequisite: task 01 is merged (02/03 recommended).
Branch: `codex/04-progress-persistence`. `--update-golden` is NOT allowed.

## Design (implement exactly; if anything here conflicts with the code, stop and report)

### 1. New pure model and store

- New folder `Unity/Assets/HeartOfTheRain/App/Progress/Runtime/`. Create `.meta` files for both new
  folders, `App/Progress` and `App/Progress/Runtime` (AGENTS.md §5).
- New file `App/Progress/Runtime/PlayerProgressPure.cs`, namespace `HeartOfTheRain.App.Progress`.
  It may use only `System`, `HeartOfTheRain.App.Home` (`HomeState`), `HeartOfTheRain.App.Settings`
  (`ISettingsStore`) and `HeartOfTheRain.M46` (`BoosterInventory`). **No UnityEngine.**

```csharp
[Serializable] public sealed class PlayerProgress {
    public int currentLevel,coins,stars,lives,chapterNumber,completedLevelsInChapter;
    public long nextLifeAtUnix;              // 0 = no refill pending
    public int[] preLevelStock=new int[4];   // Rocket, Bomb, Rainbow Orb, Golden Seeker
    public int hammer,axe,ram,atlas;          // in-level boosters
}
public sealed class PlayerProgressStore {
    public const string Prefix="HeartOfTheRain.Progress.v1.";
    public const long EpochUnix=1767225600;  // 2026-01-01T00:00:00Z. Timestamps are stored as int seconds since this epoch.
    public PlayerProgressStore(ISettingsStore storage);
    public bool HasProfile {get;}            // Read(Prefix+"exists",0)==1
    public PlayerProgress Load();            // null when !HasProfile; clamps negatives to 0
    public void Save(PlayerProgress p);      // writes every key, then "exists"=1, then Flush()
    public void Clear();                     // writes "exists"=0, then Flush()
    public static PlayerProgress Capture(HomeState home,int[] preLevelStock,BoosterInventory inventory,long nextLifeAtUnix);
    public static void ApplyTo(PlayerProgress p,HomeState home);  // copies the 6 HomeState fields, then home.Normalize()
}
```

- Exact keys, each prefixed with `Prefix`:
  - `exists`, `currentLevel`, `coins`, `stars`, `lives`, `chapterNumber`, `completedLevelsInChapter`
  - `nextLifeAt`: int seconds since `EpochUnix`; `0` means none. Convert with `checked`/clamping, and
    never let a value at or before the epoch read back as "pending".
  - `stock0`, `stock1`, `stock2`, `stock3`, `hammer`, `axe`, `ram`, `atlas`
- `Capture` copies `preLevelStock` into a new 4-element array. A null or short input array becomes zeros.

### 2. Shared PlayerPrefs adapter

New file `App/Progress/Runtime/PlayerPrefsSettingsStore.cs`:
`public sealed class PlayerPrefsSettingsStore:HeartOfTheRain.App.Settings.ISettingsStore`, using
`PlayerPrefs.GetInt`, `SetInt` and `Save`.

Do **not** refactor the three existing private `Preferences` classes. That is out of scope.

### 3. HomePage (`App/Home/Runtime/HomePage.cs`)

- Directly after the line `[SerializeField] private bool usePreviewState = true;`, add
  `[SerializeField] private bool persistProgress;`, plus a property `public bool PersistProgress { get { return persistProgress; } }`.
- In `Build()`, between
  `if(usePreviewState && assets.previewState) state=JsonUtility.FromJson<HomeState>(assets.previewState.text) ?? new HomeState();`
  and `state.Normalize();`, insert:
  `if(persistProgress){var saved=new HeartOfTheRain.App.Progress.PlayerProgressStore(new HeartOfTheRain.App.Progress.PlayerPrefsSettingsStore()).Load();if(saved!=null)HeartOfTheRain.App.Progress.PlayerProgressStore.ApplyTo(saved,state);}`
  A `using HeartOfTheRain.App.Progress;` directive is fine instead of the fully qualified names.

### 4. Production scene flag (`Unity/Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity`)

1. Find the MonoBehaviour block whose `m_Script` references guid `e8ab12dd92ff59418d782ab3febbc775`
   (HomePage). Confirm there is **exactly one** such block in this file.
2. In that block, insert a line `  persistProgress: 1` immediately after `  usePreviewState: 0`. Two-space
   indent, matching the siblings.
3. Change nothing else in the scene file, and keep LF line endings. No other scene gets the flag.

### 5. GameplayScreen (`M47/Runtime/GameplayScreen.cs`)

- Add `[NonSerialized] public BoosterInventory sharedInventory;` next to `pendingStartingPowers`.
- In `Load`, change only `inventory=new BoosterInventory();` to `inventory=sharedInventory??new BoosterInventory();`.

Standalone review scenes leave `sharedInventory` null, so they keep today's behaviour.

### 6. HomeLevelFlow (`App/PreLevel/Runtime/HomeLevelFlow.cs`)

- Add fields `PlayerProgressStore progressStore; BoosterInventory boosters=new BoosterInventory(); long nextLifeAt;`.
  `nextLifeAt` is only carried through in this task; task 05 uses it.
- In `Start()`, after the existing asset-validation line:
  - call `home.Build();` (it is idempotent);
  - if `home.PersistProgress`, create `progressStore` with `PlayerPrefsSettingsStore` and `Load()`;
  - build `PreLevelSession` from `saved.preLevelStock` when a profile exists, else from `assets.initialStock`
    as today;
  - set `boosters` from the saved hammer/axe/ram/atlas when a profile exists;
  - set `nextLifeAt=saved.nextLifeAtUnix`;
  - if persisting and no profile existed, call `SaveProgress()` once.
- Add `void SaveProgress(){if(progressStore==null)return;progressStore.Save(PlayerProgressStore.Capture(home.State,StartingStockSnapshot(),boosters,nextLifeAt));}`.
- In `Launch`, immediately after `gameplay=go.AddComponent<GameplayScreen>();`, set `gameplay.sharedInventory=boosters;`.
  After `if(!session.Complete(ticket)){...}` succeeds, call `SaveProgress();`. Then subscribe:
  `gameplay.PlayerActionCompleted+=r=>{if(r!=null&&r.kind=="booster"&&r.accepted)SaveProgress();};`.
  (`PlayerActionRecord` is in `M48/Runtime/ManualPlaytestPure.cs`. Verify that the fields `kind` and
  `accepted` exist, and that `UseBooster` spends the inventory *before* the event fires;
  see `GameplayScreen.AcceptPlayer`.)
- In `TryShowCompletion`, call `SaveProgress();` right after a successful `completion.TrySettle(...)`.
- In `ConfirmExit`, call `SaveProgress();` after `home.State.lives=decision.LivesAfter;home.ApplyState(home.State);`.
- Add `void OnApplicationPause(bool paused){if(paused)SaveProgress();}` and `void OnApplicationQuit(){SaveProgress();}`.

### 7. Editor utility

New `App/Progress/Editor/ProgressMenu.cs`, with `.meta` files for the file and the `Editor` folder.
It adds `[MenuItem("Heart of the Rain/Progress/Clear Saved Progress")]`, which calls
`new PlayerProgressStore(new PlayerPrefsSettingsStore()).Clear()` and logs a message.

### 8. Harness

Add `App/Progress/Runtime/PlayerProgressPure.cs` to `HotR.Core.csproj`.

## Tests (harness)

Use an in-memory `ISettingsStore` test double.
- `Progress_NoProfile_LoadReturnsNull`
- `Progress_RoundTrip_AllFields`: include a `nextLifeAtUnix` of `1792368000` (2026-10-19) and `0`.
- `Progress_KeysAreStable`: assert that the exact set of keys written by `Save` equals the list above.
- `Progress_ApplyTo_Normalizes`: negative coins become 0; lives above `maxLives` are clamped.
- `Progress_Clear_HidesProfile`
- `Progress_Capture_CopiesArrays`: mutating the source stock after `Capture` does not change the capture.

## Acceptance criteria

1. The harness is green, and the golden data is untouched.
2. Only these files change:
   - new files under `App/Progress/**` (with `.meta`);
   - `HomePage.cs`, `GameplayScreen.cs` (2 lines), `HomeLevelFlow.cs`;
   - `M65_First_Start.unity` (exactly 1 inserted line);
   - `HotR.Core.csproj` and new test files.
3. Review scenes are unaffected: `persistProgress` defaults to false, and `sharedInventory` defaults to null.
4. Your report lists every `SaveProgress()` call site, and confirms that each new member referenced from
   MonoBehaviours exists with the exact signature.

## Human verification in Unity (copy into your report)

- [ ] Compiles. `HomePage` in `M65_First_Start` shows **Persist Progress** ticked; other scenes show it unticked.
- [ ] Run `Heart of the Rain/Progress/Clear Saved Progress`. Play `M65_First_Start`, clear level 1, stop Play
      Mode, play again: Home shows level 2 and the increased coins.
- [ ] Use a Hammer in a level, exit, then start the next level: the Hammer count stays reduced.
- [ ] Pick a pre-level booster, start, stop Play Mode, play again: the stock stays reduced.
- [ ] `M55_Home_Review` and `M48_Chapter01_Review` do not change saved progress.

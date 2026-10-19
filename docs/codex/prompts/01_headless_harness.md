# Task 01 — Build the headless test harness and record the baseline

Read `AGENTS.md` first. Fixes: **PRJ-04**. Branch: `codex/01-headless-harness`.

## Goal

Create a reproducible, offline .NET harness that compiles the **unmodified** pure gameplay and app
sources from `Unity/Assets` and runs tests. It must prove that the current baseline is green, so that
every later task can show it changed only what it intended to change.

**Do not modify any file under `Unity/`.** If a production file won't compile in the harness, fix
that with a shim, never by editing the production file.

## Layout to create (outside `Unity/`, so Unity never imports it)

```
Tools/HeadlessTests/
  README.md
  HotR.Core/HotR.Core.csproj        # netstandard2.1 class library, links Unity sources
  HotR.Core/Shims/UnityMathShim.cs  # copied from M67R2/CoreReference/Tests/UnityMathShim.cs
  HotR.Tests/HotR.Tests.csproj      # net8.0 console app, references HotR.Core
  HotR.Tests/Program.cs             # minimal test runner (no NuGet packages)
  HotR.Tests/TestData.cs            # level/replay loading + JsonUtility emulation
  HotR.Tests/*Tests.cs              # test classes
  Golden/rules_baseline.json        # generated golden fingerprints
```

## Requirements

### HotR.Core.csproj
- `TargetFramework` `netstandard2.1`, `LangVersion` `9.0`, `Nullable` disabled, `ImplicitUsings` disabled,
  `TreatWarningsAsErrors` false.
  netstandard2.1 + C# 9 is a guard: it rejects APIs and syntax that Unity 2022.3 can't compile.
- `EnableDefaultCompileItems` false. Add each source explicitly with
  `<Compile Include="..\..\..\Unity\Assets\HeartOfTheRain\..." Link="..." />`.
- Starting source list. It mirrors what `M67R2/Source/run_validation.py` already compiles successfully;
  read that script, and use only the files below:
  - `M46/Runtime/`: `BoardModel.cs`, `StartingPowersPure.cs`, `LivePowerPlan.cs`, `ReviewPlan.cs`,
    `GoldenSeekerComboPlan.cs`, `BoardPresentation.cs`, `ReviewScenario.cs`
  - `Boosters/Runtime/*Pure.cs`
  - `M48/Runtime/*Pure.cs`
  - `M47/Runtime/FeedbackPlanPure.cs`
  - `App/Localization/Runtime/*.cs` except `LocaleBootstrap.cs`
  - `App/Home/Runtime/HomeLayoutEngine.cs` (defines `HomeState`)
  - `App/PreLevel/Runtime/PreLevelSession.cs`
  - `App/EndLevel/Runtime/EndLevelSession.cs`
  - `App/LevelComplete/Runtime/LevelCompleteSession.cs`
  - `App/Settings/Runtime/GameSettingsPure.cs`
  - `App/FirstStart/Runtime/FirstStartSession.cs`
- If a listed file needs a `UnityEngine` type the shim lacks, add the **minimal** member to a shim file
  under `HotR.Core/Shims/`. Mark every shim file with the header comment
  `// HEADLESS TESTS ONLY. Not shipped in Unity/Assets.`
  If a file needs real engine behaviour (rendering, `MonoBehaviour`, `Resources`), drop it from the list
  and record that in the README.

### HotR.Tests (runner)
- `net8.0` console app with no `PackageReference` (the environment may be offline).
- Discover tests by reflection: public static void methods marked with a custom `[Test]` attribute
  defined in the project. Print `PASS name` / `FAIL name: message`, then a summary line
  `N passed, M failed`. Exit code `0` only if all tests pass.
- Flags:
  - `--filter <substring>`
  - `--update-golden` rewrites `Golden/*.json` and prints which entries changed.
- Find the repo root by walking up from `AppContext.BaseDirectory` until a directory containing
  `AGENTS.md` and `Unity/` is found.

### JsonUtility emulation (TestData.cs) — this is critical for accuracy

Unity's `JsonUtility.FromJson` differs from `System.Text.Json` in ways that change game behaviour.
Implement `T FromUnityJson<T>(string json)`:
1. Deserialize with `System.Text.Json` using `IncludeFields = true` and case-sensitive names. Unknown
   members are ignored.
2. Then walk the object graph with reflection, applying JsonUtility's rule for public instance fields
   whose type is `[Serializable]`:
   - A null array field becomes an empty array.
   - A null `List<T>` becomes an empty list.
   - A null field of a `[Serializable]` class type becomes `new T()`.
   - Strings stay null.
   Recurse into the elements of arrays and lists.

   Example: in `C01_L050.json` with `"mossRegrowth":{"enabled":false}`, `undamagedMoves` must be 0.
   For any level without `spawnPoints`, `spawnPoints` must be an empty array, not null.
3. Unit-test this emulation directly: one test that asserts the null→empty and null→instance rules on a
   small inline JSON.

### Tests to include (all must pass on the unmodified baseline)

1. **CampaignValidation_AllLevelsAndReplays**:
   - Load `Unity/Assets/HeartOfTheRain/M47/Data/Levels/C01_L001.json` … `C01_L050.json` in order,
     as `HeartOfTheRain.M46.LevelData`.
   - Load `M48/Resources/HOTR_Playtests/Campaign_Replays.json` as `CampaignReplaySet`.
   - Call `HeartOfTheRain.M48.CampaignValidation.Run(levels, set)`.
   - Assert `report.status == "PASS_CAMPAIGN_LOGIC"`. On failure, print every entry of `report.errors`.
2. **Determinism_SameSeedSameResult**: for levels 1, 27 and 44, play the scripted sequence below twice
   from fresh boards and assert identical fingerprint sequences.
3. **RulesGolden_Baseline**: for every level 1–50:
   - Build a `new BoardModel(level)` (seed 0, i.e. `tileSeed`).
   - Repeat up to 15 turns, or until `Status != "Playing"`: take `LegalSwaps()`. If it is non-empty, apply
     the swap at index `turn % count`. Otherwise tap the power-up with the lowest `(y, x)`. Otherwise stop.
   - Record `CampaignReplayRules.Fingerprint(board)` after each accepted action, plus the final `Status`.
   - Compare with `Golden/rules_baseline.json`, keyed by level. In this task, generate the file with
     `--update-golden` once, commit it, then run again without the flag and confirm it passes.
4. **Invariant_BoardValidatesAfterEveryStep**: during test 3, call `board.Validate()` after every action
   (it throws on failure).
5. **Sessions_Smoke**:
   - `PreLevelSession`: open → toggle → `TryBegin` → `Complete` deducts stock exactly once; `Fail` deducts nothing.
   - `EndLevelSession.Confirm` can be committed only once.
   - `LevelCompleteSession.TrySettle` grants coins and stars exactly once per armed attempt.

### README.md (Tools/HeadlessTests)
Cover:
- Prerequisites (.NET 8 SDK).
- The run command, and how to use the filter and golden-update flags.
- What is and is not covered: no rendering, no MonoBehaviours, no Unity API compilation.
- The rule that golden updates need an explicit reason in the PR.

## Acceptance criteria
- `dotnet run --project Tools/HeadlessTests/HotR.Tests -c Release` exits 0, with all tests listed above passing.
- `git status` shows no changes under `Unity/` or `M67R2/`.
- `Golden/rules_baseline.json` exists and is deterministic: two consecutive `--update-golden` runs produce
  byte-identical files. Verify and report this.
- Your report lists any production files that could not be compiled, and why.

## Human verification
None needed in Unity (no Unity files changed). The reviewer runs the command above locally.

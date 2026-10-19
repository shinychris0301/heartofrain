# Codex runbook — Heart of the Rain fixes

This folder lets an AI coding agent (OpenAI Codex) verify and fix the issues found in the project review,
with every change small, specified and checkable.

| File | Purpose |
|---|---|
| `../../AGENTS.md` | Rules Codex loads automatically: constraints, style, verification, and what not to touch |
| `FINDINGS.md` | Issue register: evidence, impact, required behaviour |
| `DECISIONS.md` | Product choices the fixes depend on. **Review before running prompts.** |
| `prompts/NN_*.md` | One self-contained prompt per task |

## Step 0 — before Codex touches anything (human, once)

The project is not under version control. Without git you can't review or revert agent changes.

1. Install Git, Git LFS and the .NET 8 SDK.
2. In PowerShell, from `E:\Projects\Heart_of_the_Rain`, run:

```powershell
git init -b main
git lfs install
git lfs track "*.png" "*.wav" "*.mp4" "*.ttf" "*.unitypackage" "*.psd"
@"
# Unity generated
/Unity/[Ll]ibrary/
/Unity/[Tt]emp/
/Unity/[Oo]bj/
/Unity/[Bb]uild/
/Unity/[Bb]uilds/
/Unity/[Ll]ogs/
/Unity/[Uu]ser[Ss]ettings/
/Unity/*.csproj
/Unity/*.sln
/Unity/.vs/
# Headless harness build output
/Tools/**/bin/
/Tools/**/obj/
/M67R2/Validation/Build/
"@ | Out-File -Encoding utf8 .gitignore
git add .gitattributes .gitignore
git add .
git commit -m "Baseline: M67 R2 delivery"
```

3. Codex cloud tasks need the repo on GitHub, so push it to a **private** repository. Codex CLI or the IDE
   extension can work on the local folder directly.

## Step 1 — confirm decisions

Read `DECISIONS.md`. For each entry, either accept the default (change `DEFAULT` to `CONFIRMED`) or edit
the text. D10 (bundle id and names) must be final before a store build. D12 stays unconfirmed until the art
owner approves mobile compression.

## Step 2 — run the tasks in order

| # | Prompt | Depends on | Changes Unity files? |
|---|---|---|---|
| 00 | `00_verify_findings.md` | — | No (read-only) |
| 01 | `01_headless_harness.md` | — | No |
| 02 | `02_engine_safety.md` | 01 | Yes |
| 03 | `03_engine_rules.md` | 01, 02 | Yes |
| 04 | `04_progress_persistence.md` | 01 | Yes (+1 line in M65 scene) |
| 05 | `05_lives_and_retry.md` | 01, 02, 04 | Yes |
| 06 | `06_project_setup_and_build.md` | — | Yes (editor script + build list) |
| 07 | `07_hud_allocations.md` (optional) | 02–05 | Yes |
| 08 | `08_mobile_textures.md` | D12 confirmed | Yes (editor scripts) |
| 99 | `99_review_diff.md` | after each task | No (read-only review) |

For each task:

1. Create a branch: `git switch -c codex/NN-name`.
2. Give Codex the prompt file's entire contents as the task. With the CLI, from the repo root:
   `codex "$(Get-Content docs/codex/prompts/NN_name.md -Raw)"`. In the IDE or cloud, paste it.
3. When Codex finishes, check its report:
   - every acceptance criterion is PASS;
   - the harness exit code is 0;
   - golden-file changes, if any, are justified.
4. Run the harness yourself: `dotnet run --project Tools/HeadlessTests/HotR.Tests -c Release`.
5. Run `99_review_diff.md` in a **new** Codex session against the branch. Fix anything it flags. A follow-up
   prompt to the implementer works: "Apply review fixes 1–N exactly as written".
6. Open Unity 2022.3.62f3 and work through the prompt's **Human verification in Unity** checklist. Codex
   cannot run Unity, so this step is the only compile and Play Mode check.
7. Merge into `main`, then start the next task from the updated `main`.

If Codex reports a **stop** condition (a snippet not found, a replay diverged, a decision conflict),
resolve it before continuing. Don't tell it to "just make it pass".

## What the harness does and doesn't prove

- **Proves:** the pure rules and session code compiles under C# 9 / .NET Standard 2.1, all 50 levels pass
  campaign validation, the 5 golden replays still win identically, deterministic play is unchanged except
  where intended, and the new logic (lives, persistence, deadlock fallback) behaves as specified.
- **Does not prove:** that MonoBehaviour, scene and UI code compiles against the real UnityEngine, rendering,
  input, audio, performance, or device behaviour. Those need the Unity checklist and, later, a CI build (DEF-07).

## Out of scope for now

See "Deferred" in `FINDINGS.md`: asmdefs and folder reorganisation, localization tooling, Unity Test
Framework/CI, hint quality, VFX-coupled rules, and new match-3 features. Each needs its own prompt once the
items above are merged.

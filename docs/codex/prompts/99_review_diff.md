# Task 99 — Review a completed task's diff (READ-ONLY)

Use this after any task 01–08, in a **fresh** Codex session, so the reviewer doesn't share the implementer's
assumptions. Replace `<NN>` with the task number and `<branch>` with its branch.

---

Read `AGENTS.md`, `docs/codex/FINDINGS.md`, `docs/codex/DECISIONS.md` and `docs/codex/prompts/<NN>_*.md`.
Then review `git diff main...<branch>`. **Do not modify files.**

Check, and report each item as PASS / FAIL with evidence:

1. **Spec conformance.** Every numbered instruction in the task prompt is implemented as written. Nothing
   extra was added. List any deviation.
2. **Decisions.** The behaviour matches the referenced DECISIONS entries exactly.
3. **Compile safety (Unity).**
   - For every changed MonoBehaviour file: each referenced type and member exists with the right signature
     (cite the declaring file).
   - `using` directives are present.
   - No C# 10+ syntax, and no APIs beyond .NET Standard 2.1.
   - No `UnityEditor` outside `Editor/` folders.
4. **Determinism.** No `Rand()` call order or count changed and no existing iteration order changed, except
   where the prompt allows it. `Fingerprint` and `Combo` are unchanged unless the prompt says otherwise.
5. **Assets.**
   - Every new file and folder under `Unity/Assets` has a `.meta` with a unique new GUID.
   - No existing GUID changed.
   - Scene/asset YAML edits are limited to what the prompt allows.
6. **Encoding.** UTF-8 without BOM and LF line endings are preserved, and no unrelated reformatting
   (look for whole-line rewrites where one statement changed).
7. **Localization.** New user-visible strings exist in `LocaleCatalog.cs` with 5 entries, and the `{0}`
   placeholders are preserved.
8. **Tests.**
   - Run `dotnet run --project Tools/HeadlessTests/HotR.Tests -c Release` and paste the summary.
   - The new tests actually assert the acceptance criteria, rather than only exercising the code.
   - Golden files changed only if the prompt allowed it, with a justification per entry.
9. **Edge cases.** Name at least three inputs or sequences the implementer may not have considered, and say
   whether the code handles each. Examples: double taps, app pause mid-animation, 0 lives, a missing profile,
   a level with no gems.

End with a verdict, `MERGE`, `MERGE AFTER FIXES` or `REJECT`, plus a numbered list of required fixes.
Each fix must give file, snippet and the exact change.

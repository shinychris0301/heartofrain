# Task 00 — Independently verify the findings (READ-ONLY)

You are reviewing a Unity 2022.3 match-3 project. Read `AGENTS.md` first.
**Do not modify, create or delete any file in this task.**

## Goal

Another reviewer produced `docs/codex/FINDINGS.md`. Before anyone changes code, verify every finding
with status **Fix** or **Gated** against the actual source. Disagreement is valuable: if a finding is wrong,
overstated or incomplete, say so with evidence.

## Steps

1. Read `docs/codex/FINDINGS.md` and `docs/codex/DECISIONS.md`.
2. For each of ENG-01…05, APP-01…07 and PRJ-01…04:
   - Open the cited files. Find each quoted snippet and confirm it exists verbatim, giving its current line number.
   - Trace the behaviour end to end. For example, for APP-02 follow `GameplayHUD` "Try again" →
     `RetryPressed` → `GameplayScreen.Load`, and confirm that nothing on that path changes `HomeState.lives`.
   - Look for code paths the finding missed: other callers, other places where the same state changes,
     reflection, `SendMessage`, UnityEvents serialized in scenes (search `.unity` / `.prefab` YAML for method names).
3. For each decision D2–D11, check that the default can be implemented as written. Flag any conflict
   with existing code, for example a field that doesn't exist, or a status string used elsewhere.
4. Search for additional **Critical/High** issues in the same areas: board rules, the campaign flow,
   persistence, and build settings. Do not report style issues.

## Output (your entire response)

A markdown table with one row per finding: `ID | Verdict (CONFIRMED / PARTIAL / WRONG) | Current line(s) | Evidence or correction`.

Then these sections:
- **Decision feasibility**: D2–D11, each `OK` or the specific problem.
- **New Critical/High issues**: each with file:line, a quoted snippet, a failure scenario and suggested severity.
- **Questions for the owner**: only things that block implementation.

Keep it under 1200 words. Do not propose code in this task.

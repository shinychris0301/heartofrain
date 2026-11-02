# Codex instructions — Heart of the Rain

Scope: the extracted Heart_of_the_Rain project and its documentation.

- Read Codex_Handoff/Documentation/00_START_HERE.md and 01_STATUS_AND_DECISIONS.md before editing. Runtime baseline is M67R4; engine is Unity2022.3.62f3.
- Preserve approved artwork, palette, asset GUIDs, existing level masks and gameplay semantics unless the task explicitly changes them. No broad redesign or automatic engine/SDK upgrade.
- Gameplay is 2D with depth effects. Do not introduce a runtime3D board. Japanese is excluded. Rocket and Bomb remain separate. Golden+Golden has no approved rule.
- Verify the active namespace/caller: live board code is M46, with M48 partials; earlier planners coexist. Current app win flow is HomeLevelFlow plus M67 celebrations, not the old M66 result modal.
- Treat Shop, Leaderboard, Teams and event timers as demo data until services are implemented. Do not claim purchases/social/backend work because a page renders.
- First establish native compile/device baseline, durable profile, unified attempt settlement and persistent inventory. See implementation backlog for acceptance criteria.
- Keep mutations and rewards in model/services, not animation callbacks. Use durable idempotency for purchases, attempts and claims. Never commit credentials or payment tokens to source/docs/logs.
- Use narrow diffs; preserve .meta files. Add meaningful tests for state/transaction bugs and native evidence for rendering fixes. Do not label fake-host/source checks as Unity/device tests.
- Report changed files, behavior, tests and material remaining limitations. Update current docs when a documented gap is actually closed.
- Future design changes are reviewed with the user one page/component at a time. Continue defined engineering work without inventing unresolved art/mechanic choices.

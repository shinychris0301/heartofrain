# Product decisions for the Codex tasks

Each decision has a **default** that the task prompts implement. Change the default here **before**
running the prompt that depends on it. Codex must implement exactly what is written here. If text here
conflicts with a prompt, this file wins, and Codex must report the conflict.

Status values: `DEFAULT` (not yet confirmed by the owner) → `CONFIRMED` (the owner agreed).

---

## D2 — Deadlock and cascade-limit policy (prompt 02) · Status: DEFAULT

1. When no legal swap exists and the board has no power-up, `Shuffle` keeps its existing 100
   colour-permutation attempts **unchanged**.
2. If those fail: up to 100 **recolour** attempts. Each gem gets `NewColor()` (the level palette, seeded RNG).
   Accept the first result with no matches and at least one legal swap.
3. If that also fails and at least one gem exists: turn the gem nearest the board centre into a
   horizontal rocket (power kind `4`). Nearest means Manhattan distance to `((columns-1)/2, (rows-1)/2)`,
   ties broken by lowest cell key. A power-up is always a legal action (tap).
4. Only if the board has **zero gems**: status `"No legal moves"`.
5. `"No legal moves"` and `"Resolution limit"` are **no-fault endings**. The HUD does not show the
   "Out of moves" loss dialog. It shows a "Board reset" dialog whose single button retries the level,
   and no life is ever charged for these (enforced in prompt 05).

## D3 — Golden Seeker + Golden Seeker (prompt 03) · Status: DEFAULT

Swapping two Golden Seekers (kind 16) is a legal move that costs one move. Both seekers activate as two
independent single Golden Seeker activations, the dragged piece (`a`) first and then `b`. No new merge
animation is created. Alternative if you prefer: keep the refusal and change nothing (then delete ENG-03
from prompt 03).

## D4 — Power-up spawn cell (prompt 03) · Status: DEFAULT

For a player swap, the power-up created from a match goes on the cell of the swapped piece that belongs
to that match:
- If `b` (the piece that lands on the drag origin) is in the match, use `b`'s cell. This is unchanged behaviour.
- Otherwise, if `a` (the dragged piece, which lands on the drag target) is in the match, use `a`'s cell. This is new.
- Otherwise use the existing fallback (lowest cell key).

Cascade matches are unchanged.

## D5 — Moss regrowth config (prompt 03) · Status: DEFAULT

- Threshold: the first positive value of `undamagedMoves` or `afterConsecutiveMovesWithoutMossDamage`, else `2`.
- Cap: the first positive value of `maxNewClumps` or `maxNewCellsTotal`, else `3`.
- `spawnPerTrigger` stays 1 and is not read.

## D6 — Persistence (prompt 04) · Status: DEFAULT

- **Storage:** local only, through `PlayerPrefs` and the existing `ISettingsStore` interface. Key prefix
  `HeartOfTheRain.Progress.v1.`. No cloud saves.
- **Persisted fields:**
  - `HomeState`: `currentLevel`, `coins`, `stars`, `lives`, `chapterNumber`, `completedLevelsInChapter`.
  - Next-life timestamp.
  - Pre-level booster stock (4 counts: Rocket, Bomb, Rainbow Orb, Golden Seeker).
  - In-level booster inventory: `hammer`, `axe`, `ram`, `atlas`.
- **Not persisted:** `maxLives`, chapter title, the `*Visible` / `*Status` presentation fields, and `reduceMotion`.
- **Scope:** only the production boot scene `M65_First_Start.unity` persists. A new serialized
  `HomePage.persistProgress` flag defaults to `false` and is set to `1` in that scene only, so review
  scenes never read or write the saved profile.
- **New profile values:**
  - `HomeState`: whatever the scene serializes (level 1, 1250 coins, 5 lives).
  - Pre-level stock: `PreLevelAssets.initialStock`.
  - In-level inventory: `BoosterInventory` defaults (3 each).
- **When to save:**
  - Reward settlement.
  - Any change to lives.
  - Pre-level stock spent.
  - Accepted in-level booster use.
  - `OnApplicationPause(true)` and `OnApplicationQuit`.

## D7 — Lives policy (prompt 05) · Status: DEFAULT

- A loss (`"Out of moves"`) costs **1 life**, charged when the loss is detected, before the dialog shows.
- Exiting mid-level after confirmation costs 1 life. This is the existing behaviour.
- **At most one life per attempt.** An attempt is one pre-level launch ticket.
- No-fault endings (D2) never cost a life.
- In the campaign flow, "Try again" (and the HUD pause "Restart level", if reachable) closes gameplay and
  opens the **pre-level screen in retry mode** for the same level. Boosters are chosen and paid per attempt.
  A mid-level restart with status `"Playing"` is treated like an exit and charged through the same
  one-per-attempt rule.
- Standalone review scenes (no `HomeLevelFlow`) keep their current in-place reload.

## D8 — Lives refill (prompt 05) · Status: DEFAULT

- 1 life every **30 minutes** (1800 s), up to `maxLives` (5).
- The timer starts when lives drop below max. It is computed from wall-clock UTC on load, on resume and
  once per second while running.
- If the device clock moves backwards so that the next-life time is more than 1800 s in the future, clamp
  it to now + 1800 s.
- With 0 lives the pre-level message reads `No lives remaining. Next life in {0}` (`{0}` = `m:ss`).
- No purchase or refill button. The Shop stays presentation-only.

## D9 — Orientation (prompt 06) · Status: DEFAULT

Portrait-only app: default orientation Portrait, with auto-rotation to any other orientation disabled.

## D10 — Player settings values (prompt 06) · Status: DEFAULT — replace before store submission

| Setting | Value |
|---|---|
| Company name | `Heart of the Rain` |
| Product name | `Heart of the Rain` |
| Application identifier (Android and iOS) | `com.heartoftherain.game` |
| Version | `0.1.0`; Android bundle version code `1`; iOS build number `1` |
| Color space | Gamma (the approved art and `M48ReviewMenu` validation assume Gamma) |
| Android | IL2CPP, ARM64, min SDK 26, target SDK Auto |
| iOS | IL2CPP (Unity default), target OS 13.0 |

## D11 — Scenes in the player build (prompt 06) · Status: DEFAULT

Only `Assets/HeartOfTheRain/App/FirstStart/Scenes/M65_First_Start.unity` stays enabled. All other
entries stay in the list but are set to `enabled: 0`, so they can be re-enabled for internal review builds.

## D12 — Mobile texture compression (prompt 08) · Status: NOT APPROVED — do not run prompt 08

To run it, the art owner must approve ASTC on Android/iOS. Editor and Standalone stay uncompressed for
fidelity reviews. Set this to `CONFIRMED` (with the block size, default ASTC 6x6) to unlock prompt 08.

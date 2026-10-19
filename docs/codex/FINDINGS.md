# Findings register — Heart of the Rain

Baseline: delivery "M67 R2" (19 Oct 2026). Paths are relative to `Unity/Assets/HeartOfTheRain/` unless they
start with `Unity/` or the repo root. Line numbers are as of the baseline. **Always locate code by the
quoted snippet**, because earlier tasks will shift line numbers.

Severity: **Critical** = blocks release; **High** = wrong behaviour players will hit; **Medium** = wrong
in edge cases or costly; **Low** = latent / quality. Status: **Fix** (has a task prompt), **Gated** (needs a
decision first), **Deferred** (deliberately out of scope for now).

| ID | Sev | Title | Task | Status |
|---|---|---|---|---|
| ENG-01 | High | Deadlock or cascade limit is shown as a loss and soft-locks the board | 02 | Fix |
| ENG-02 | High | A rule-invariant exception mid-turn leaves a half-resolved, paid-for board | 02 | Fix |
| ENG-03 | Medium | Two Golden Seekers cannot be swapped together | 03 | Fix |
| ENG-04 | Medium | Power-up spawns bottom-left when the dragged piece made the match | 03 | Fix |
| ENG-05 | Low | Moss regrowth ignores per-level config (latent; no behaviour change today) | 03 | Fix |
| APP-01 | Critical | No progress, currency, lives or booster persistence | 04 | Fix |
| APP-02 | Critical | Losing costs no life; retry after loss is free and unlimited | 05 | Fix |
| APP-03 | Critical | No lives refill: at 0 lives no level can start | 05 | Fix |
| APP-04 | High | Pre-level boosters are paid once but lost on "Try again" | 05 | Fix |
| APP-05 | High | In-level boosters reset to 3 each on every level load | 04 | Fix |
| APP-06 | Medium | A win the campaign flow can't settle falls through to the standalone "Continue" path | 05 | Fix |
| APP-07 | Medium | HUD and render loop allocate every frame | 07 | Fix (optional) |
| PRJ-01 | Critical | `Unity/ProjectSettings/` has only 2 files; player settings undefined | 06 | Fix |
| PRJ-02 | High | 16 of the 17 enabled build scenes are review scenes | 06 | Fix |
| PRJ-03 | High | All textures uncompressed on mobile | 08 | Gated (D12) |
| PRJ-04 | High | No automated tests | 01 | Fix |
| PRJ-05 | High | No version control | README step 0 | Human |
| DEF-* | — | Deferred items | — | Deferred |

---

## ENG-01 — Deadlock or cascade limit is shown as a loss and soft-locks the board (High)

**Evidence**
- `M46/Runtime/BoardModel.cs:224-232`, `Shuffle`: after 100 attempts it restores the colours and sets the terminal status:
  `for(int i=0;i<gems.Length;i++)gems[i].color=original[i];Status="No legal moves";`
- `BoardModel.cs:202-203`, `Settle`: `if(++waves>128){Status="Resolution limit";break;}` and
  `if(result.steps.Count>512){Status="Resolution limit";break;}`
- `M47/Runtime/GameplayScreen.cs:123` treats every non-`"Playing"` status other than `"Won"` as a loss:
  `if(!Busy&&!resultShown&&board.Status!="Playing"){resultShown=true;hud.ShowResult(board.Status=="Won",board.Level.globalLevel);}`
- Once the status is not `"Playing"`, `Swap`, `Tap` and `UseBooster` (including the Atlas shuffle) all refuse.

**Impact:** the player gets an "Out of moves" dialog through no fault of their own. Once task 05 lands, that dialog would also cost a life.

**Required behaviour:** see DECISIONS D2 and prompt 02.

## ENG-02 — A rule-invariant exception mid-turn leaves a half-resolved, paid-for board (High)

**Evidence**
- `BoardModel.cs:67`: `void Finish(BoardStep s,TurnResult result){Validate();s.after=Snapshot();result.steps.Add(s);}`
- `BoardModel.cs:69-77`, `Validate()`, throws `InvalidOperationException`.
- `BoardModel.cs:136`, `BeginTurn`, has already run `Moves--;Turn++;` by the time the first `Finish` is called.
- `GameplayScreen.cs:168` calls `board.Swap(...)` with no try/catch. The exception escapes `Update()`, and play continues on a corrupted model.

**Required behaviour:** the public turn entry points (`Swap`, `Tap`, `UseBooster`) never leave the model half-mutated. On any exception inside a turn, the model is restored to its exact pre-call state and a rejected `TurnResult` is returned with the fault details. Prompt 02.

## ENG-03 — Two Golden Seekers cannot be swapped together (Medium)

**Evidence**
- `BoardModel.cs:103-110`: `Combo(int a,int b)` has no case for `16+16`.
- `BoardModel.cs:122`: `if(a.family=="power"&&b.family=="power"&&combo<0){result.reason="This combination has no approved rule";return result;}`
- `StartingPowersPure.cs:14` allows several 16s, and gravity can bring them next to each other.

**Required behaviour:** DECISIONS D3. Prompt 03.

## ENG-04 — Power-up spawns bottom-left when the dragged piece made the match (Medium)

**Evidence**
- `BoardModel.cs:129`: `else ResolveMatches(groups,result,b.id);` passes only `b`, the piece that lands on the drag **origin**.
- `BoardModel.cs:155`: `int keep=m.cells.Where(Pieces.ContainsKey).OrderBy(k=>Pieces[k].id==preferred?0:1).ThenBy(k=>k).First();`
- When only `a` (the dragged piece, which lands on the drag **target**) forms the match, `keep` falls back to the lowest key: the bottom-left cell of the match.

**Required behaviour:** DECISIONS D4. Prompt 03.

## ENG-05 — Moss regrowth ignores per-level config (Low, latent)

**Evidence**
- `BoardModel.cs:10`: `GrowthRule { public bool enabled; public int undamagedMoves,maxNewClumps; }`
- `BoardModel.cs:220` hardcodes the thresholds: `QuietMoves=Math.Min(2,QuietMoves+1);if(QuietMoves<2||GrowthUsed>=3)return;`
- Levels use two schemas:
  - `undamagedMoves` / `maxNewClumps`: L021, L022, L024, L028–30, L032, L034, L036–37, L039–40, L043–47, L049.
  - `afterConsecutiveMovesWithoutMossDamage` / `maxNewCellsTotal`: L001–L020, L023, L025–27, L031, L033, L035, L038, L041–42, L048.
  - L050 has `{"enabled":false}` only.
- **Every level currently uses 2 / 3**, and only L027 and L044 have `enabled:true`. Honouring the config therefore changes nothing today; the fix prevents future data from being silently ignored.

Prompt 03.

## APP-01 — No progress, currency, lives or booster persistence (Critical)

**Evidence**
- `HomeState` (`App/Home/Runtime/HomeLayoutEngine.cs:8-22`) lives only in the serialized `HomePage.state`. In `App/FirstStart/Scenes/M65_First_Start.unity` it is `currentLevel: 1`, `coins: 1250`, `lives: 5`, and `usePreviewState: 0`.
- `PlayerPrefs.Set*` is used only by settings, language and first-start: `GameplaySettingsController.cs`, `FirstStartPage.cs`, `AppSettingsPage.cs`.
- `HomeLevelFlow.cs:28`, `session=new PreLevelSession(assets.initialStock);`, rebuilds the booster stock from the asset on every start.

**Impact:** every app restart puts the player back at level 1 with the default coins, lives and boosters.

**Required behaviour:** DECISIONS D6. Prompt 04.

## APP-02 — Losing costs no life; retry after loss is free and unlimited (Critical)

**Evidence**
- `M47/Runtime/GameplayHUD.cs:88-89`, loss dialog: `Click(p,"Button_Teal","Try again",...,()=>{Close(true);RetryPressed?.Invoke();});`
- `GameplayScreen.cs:83`: `hud.RetryPressed=()=>Load(levelIndex,0,"retry");` reloads in place and never touches lives.
- The only life deduction is `HomeLevelFlow.cs:104`: `home.State.lives=decision.LivesAfter;`, which runs on *exit* confirmation.

**Required behaviour:** DECISIONS D7. Prompt 05.

## APP-03 — No lives refill: at 0 lives no level can start (Critical)

**Evidence**
- `PreLevelSession.cs:47`: `if(View.lives<=0){View.message="No lives remaining";return false;}`
- There is no refill timer anywhere, and the Shop is presentation-only (`App/Shop/Runtime/ShopSession.cs:17`).

**Required behaviour:** DECISIONS D8. Prompt 05.

## APP-04 — Pre-level boosters are paid once but lost on "Try again" (High)

**Evidence**
- `HomeLevelFlow.cs:73`: `session.Complete(ticket)` deducts the stock.
- `GameplayScreen.cs:93`: `...pendingStartingPowers=null;}` after the first grant, so an in-place reload has no starting powers.

**Required behaviour:** DECISIONS D7. "Try again" returns to the pre-level screen, so boosters are chosen and paid per attempt. Prompt 05.

## APP-05 — In-level boosters reset to 3 each on every level load (High)

**Evidence**
- `GameplayScreen.cs:91`: `inventory=new BoosterInventory();` inside `Load`.
- `Boosters/Runtime/BoosterRulesPure.cs:6`: `public int hammer=3,axe=3,ram=3,atlas=3;`

**Required behaviour:** DECISIONS D6. In the campaign flow, the inventory is shared and persisted. Prompt 04.

## APP-06 — A win the campaign flow can't settle falls through to the standalone "Continue" path (Medium)

**Evidence**
- `HomeLevelFlow.cs:81-85`: `TryShowCompletion` returns `false` when `!source.Ready`, on a level mismatch, or when `TrySettle` fails.
- `GameplayHUD.cs:81-86`: on `false` it runs the standalone victory and then `ContinuePressed`.
- `GameplayScreen.cs:83`: `hud.ContinuePressed=()=>Load(Mathf.Min(49,levelIndex+1),0,"continue");` loads the next level inside the same screen, with no settlement, no lives check and no pre-level screen.

**Required behaviour:** in the campaign flow, `ContinuePressed` returns the player to Home safely. Prompt 05.

## APP-07 — HUD and render loop allocate every frame (Medium, optional)

**Evidence**
- `GameplayHUD.cs:61-62` (`UpdateState`, called every frame from `GameplayScreen.cs:121`):
  - `moves.text=moveCount.ToString();`
  - `helper.text=GameLocale.T(hint??"");`
  - `string.Join("/",Array.ConvertAll(goals,g=>g.family))`
- `GameplayHUD.cs:58`: `modal.Find("Dialog")` runs every frame.
- `GameplayScreen.cs:128`: `ActiveSpriteCount=count+draws.Count(d=>d.uiOverlay);` runs every frame.

Prompt 07.

## PRJ-01 — `Unity/ProjectSettings/` has only 2 files; player settings undefined (Critical)

**Evidence**
- `Unity/ProjectSettings/` contains only `EditorBuildSettings.asset` and `ProjectVersion.txt`. There is no `Unity/Packages/packages-lock.json`.
- Unity will regenerate defaults, so company/product name, bundle id, version, orientation, scripting backend and target architectures are all undefined.
- The only intended values are review values in `M48/Editor/M48ReviewMenu.cs` (`Configure()`).

**Required behaviour:** add an editor menu that applies the production player settings from DECISIONS D9/D10. A human runs it once in Unity and commits the generated `ProjectSettings/*` and `packages-lock.json`. Prompt 06.

## PRJ-02 — 16 of the 17 enabled build scenes are review scenes (High)

**Evidence:** `Unity/ProjectSettings/EditorBuildSettings.asset` enables 17 scenes. Index 0 is `App/FirstStart/Scenes/M65_First_Start.unity`. No runtime code calls `SceneManager.LoadScene`.

**Required behaviour:** DECISIONS D11. Prompt 06.

## PRJ-03 — All textures uncompressed on mobile (High, gated)

**Evidence**
- Every PNG `.meta` has `textureCompression: 0`.
- Editor import policies force this on every import, e.g. `App/Home/Editor/HomeArtImportPolicy.cs`, which sets `t.textureCompression=TextureImporterCompression.Uncompressed` and `p.overridden=false` for Android/iPhone.
- The review validators reject compressed textures.
- Exception: `M48/Editor/M48TextureImport.cs` already applies ASTC 6x6 to `M48/Resources/M48Textures` on Android/iOS.

This was a deliberate art-fidelity policy, so it needs a decision first (D12). Prompt 08.

## PRJ-04 — No automated tests (High)

- No Unity Test Framework, and no `[Test]` attributes anywhere.
- Offline checks exist in `M67R2/Source/run_validation.py`. They compile the pure sources against `M67R2/CoreReference/Tests/UnityMathShim.cs` with Roslyn, but they live in the frozen bundle and depend on an unshipped `tmp/` folder.

**Required behaviour:** a reproducible headless harness in `Tools/HeadlessTests/`. Prompt 01.

## PRJ-05 — No version control (High)

The project is not a git repository. A human must initialise git (with LFS) before any agent work, so every change is reviewable and revertible. See `docs/codex/README.md`, step 0.

---

## Deferred (do not work on these without a new prompt)

| ID | Item | Why deferred |
|---|---|---|
| DEF-01 | Hint always picks `LegalSwaps()[0]`, the bottom-left swap (`GameplayScreen.cs:40`) | Quality, not correctness |
| DEF-02 | Retry/continue reuse seed 0 → `tileSeed`, so every attempt has identical refills | Possibly intentional for tuning; design call |
| DEF-03 | Power-up hit cells come from VFX choreography (`LivePowerPlan`/`ReviewPlan`) | Large refactor; needs Unity visual verification |
| DEF-04 | `LegalSwaps`/`Matches` allocations; `Shuffle` up to 100× and Atlas up to 800× full scans | Performance; measure on device first |
| DEF-05 | No `.asmdef` files; milestone folder names (M46/M47/M48); duplicated `Chapter01M07` plan code | Structural refactor; needs Unity compile loop |
| DEF-06 | Localization catalogs hard-coded in C# and keyed by English text | Tooling change |
| DEF-07 | Unity Test Framework / PlayMode tests / CI build | Needs Unity in CI |
| DEF-08 | Runtime review tools write files via `File.WriteAllText` (`M48/Runtime/GameplayReviewTools.cs` etc.) | Hidden outside dev builds; clean up with DEF-05 |
| DEF-09 | `GameplayScreen.Start` forces portrait/60 fps globally | Becomes harmless once D9 player settings are applied |
| DEF-10 | `HomePage.cs:191` reads `im.sprite.rect.height` without a null check | Low; only on a missing asset |
| DEF-11 | Missing match-3 features: diagonal fill, +moves offer, star ratings, end-of-level bonus, colour/score goals, swipe threshold | Product roadmap |

## Correction to an earlier review statement

An earlier review suggested deleting `M48/Resources/M48Textures` as a duplicate. **That is wrong.**
`M46/Runtime/M46AtlasBank.cs` (`Texture(...)`, `Resources.Load<Texture2D>(path)`) loads gameplay textures
from it at runtime. Do not delete or move it.

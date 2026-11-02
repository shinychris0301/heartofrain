# Gameplay and level specification

## Board contract
Current Chapter 1 contains ten 9×9, twenty 9×11 and twenty 11×11 configurations. The active-cell mask defines each layout. Coordinates are bottom-left origin, x right, y up; `key = y * columns + x`. UI layout coordinates can point down, so conversion belongs in the renderer. Do not transpose board JSON to match UI coordinates.

Each active cell holds one gem/power/obstacle footprint cell. Multi-cell obstacles reserve a footprint under one owner. No obstacle overlay on a gem. Gems, powers, supply crates and restoration jars can fall; only gems and powers swap. Gravity compacts vertically first, then feeds reachable gaps diagonally around fixed obstacles, preserving source/corner reservations and mask boundaries. Exit jars stay on their exit, and crates/jars cannot enter reserved Storm Crystal lanes. Refill uses declared spawn points. Teleport portals and conveyors are not implemented. See `18_OBSTACLE_GRAVITY_REVIEW.md` for the approved repair and native evidence.

LevelData reads id/name, dimensions, activeCells, initialTiles, obstacles, goals, activeColors, tileSeed, spawnPoints, deliveryExits, move budget and growth fields. The authored opening board never depends on the RNG seed; the seed drives refills, reshuffles and Atlas. In the connected app each attempt plays with its own seed derived from the attempt id and recorded in the receipt (owner decision, 22 October 2026); verification replays, review scenes and fixtures keep passing `tileSeed` or an explicit replay seed to `BoardModel`. Extra JSON authoring metadata is not necessarily consumed by runtime. Do not assume a field works because it exists in JSON. `initialPowerUps` is present in authored data but is not a documented runtime grant path; starting powers use `StartingPowersPure`.

## Actions and matches
An invalid swap uses no move. A legal swap or power activation consumes one move. Three or more in a line clear; a 2×2 same-color square also matches. Creation priority is five-line Orb, intersecting horizontal/vertical Bomb, four-line Rocket, then square Rain Seeker. For a player swap, a four-line Rocket follows the gesture axis: horizontal swipe creates H Rocket and vertical swipe creates V Rocket, regardless of the matched line axis. Creation uses the dragged tile at its matching destination; if only its partner forms the group, use that matching swap endpoint. Cascade four-lines retain line-axis orientation. New powers can fall normally after appearing at their creation cell. Golden Seeker has no normal match recipe.

Only match groups involving moved/refilled/swapped piece IDs are newly resolved; old review layouts may include dormant squares. The future authoring validator should explicitly decide whether to forbid all initial squares. Resolution order is action → power/match contacts and chains → delivery → gravity/refill → cascades → regrowth/reshuffle → win/loss. All goals reaching zero wins even on the last move. Remaining moves are discarded at the win: by owner decision (22 October 2026) there is no end-of-level conversion and no per-move coin bonus. Guards limit resolution to 128 waves/512 steps; guard termination must be diagnostic, not silently treated as a player loss in production.

## Power ID registry
| ID | Meaning | Core behavior |
| --- | --- | --- |
| 4 | Horizontal Rocket | Row clear |
| 5 | Vertical Rocket | Column clear |
| 7 | Rainbow Orb | Target-color clear with the existing rotating/beam treatment |
| 11 | Rain Seeker | Local launch effect and one selected destination |
| 16 | Golden Seeker | Creates two Golden Seeker children, each with its own destination/hit |
| 21 | Bomb | Local area explosion; direct-contact helper uses a five-by-five footprint |

Seeker target selection prioritizes damageable obstacles, then distant eligible pieces, with deterministic tie-breaking. Delivery jars are not valid seeker targets. If too few valid targets exist, excess seekers dissolve without inventing damage. ReviewPlan contains exact standalone timing/footprints; do not substitute competitor mechanics for these values.

## Combination registry
| Pair | ID | Intent |
| --- | --- | --- |
| Rocket + Rocket | 6 | Combined cross/lane effect |
| Rocket + Bomb | 2 | Enlarged merged rocket/bomb lane attack |
| Bomb + Bomb | 3 | Merge into larger bomb and expanded detonation |
| Orb + Rocket | 8 | Convert eligible color tiles to rockets, then activate |
| Orb + Bomb | 9 | Convert eligible color tiles to bombs, then activate |
| Orb + Orb | 10 | Double Orb using Super Orb body design |
| Rain + Rocket | 12 | Seeker carries a rocket attack to target |
| Rain + Bomb | 13 | Seeker carries a bomb attack to target |
| Rain + Rain | 14 | Three seeker children |
| Orb + Rain | 15 | Color conversion into Rain Seekers |
| Golden + Rocket | 17 | Golden children carry rocket attacks |
| Golden + Bomb | 18 | Golden children carry bomb attacks |
| Golden + Rain | 19 | Approved Golden/Rain combination plan |
| Orb + Golden | 20 | Color conversion into Golden Seeker groups |

Golden + Golden is intentionally unsupported. Do not invent a rule. Exact child counts/timing for compound Golden plans are encoded in `GoldenSeekerComboPlan.cs` and `ReviewPlan.cs`; preserve those plans and use their tests when editing. Vertical pair presentation can normalize to horizontally authored merge sheets while logic reserves the actual cells. Damage is deduplicated by activation ID; independent children/conversions use separate IDs.

## Starting items versus in-level tools
| Context | Items | Current stock behavior |
| --- | --- | --- |
| Pre-level | Rocket, Bomb, Rainbow Orb, Golden Seeker | Separate slots; sample initial stock 5/5/3/2; consume after successful grant |
| In-level | Mason's Hammer, Woodcutter's Axe, Channel Ram, Daria's Atlas | Sample stock 3 each; resets on GameplayScreen.Load; production defect |

Hammer hits one cell; the head must strike. Axe hits a column. Ram hits a row. Atlas shuffles movable gems/powers, preserving IDs/colors/powers and fixed obstacles. Tools do not consume a move. Invalid/canceled use does not consume stock. Shuffle retries are bounded and failed attempts restore state. The old three-slot starting inventory migrates the combined Rocket/Bomb count into two separate fields; preserve that compatibility until a versioned production migration replaces it.

## Obstacle registry
| Family ID | Name | First level | Rules |
| --- | --- | --- | --- |
| crate | Supply crate / wooden box | 1 | HP 1–3; falls; adjacent match or direct damage |
| moss | Well overgrowth | 1 | HP 1–2; fixed; adjacent/direct damage; optional growth |
| stone | Rune stone | 7 | HP 1–3; fixed; adjacent/direct damage |
| pail | Restoration jar | 10 | Falls; damage-immune; collect only at delivery exit |
| case | Sealed supply case | 14 | HP 1–2; fixed; direct power/tool damage, not adjacent match |
| gate | Water sluice | 18 | HP 1–2; adjacent color-5 water match or direct damage |
| crystal | Storm Crystal | 21 | 5–9 vertical segments; exclusive outer lane; top segment removed per hit; one goal per entire column |
| pod | Water Spirit Pod | 28 | HP 1–3; single cell; spirit collected on final damage |
| cabinet | Rainlight Cabinet | 36 | 2×2 shared owner; up to HP 5; opening hit then four rainlights at full health |

Crystals are anchored at the bottom of their active outer segment, which can be y=1 on a clipped mask. Do not force y=0. Cabinet goal family is `rainlight`, not `cabinet`; count collectible units, not occupied cells. Shared-owner damage must not multiply because an area attack touched four cabinet cells.

The delivered campaign's enabled moss rules grow after two undamaged moves, one eligible adjacent gem at a time, to a maximum of three added clumps. The model now honors the authored interval and lifetime cap in both canonical and legacy JSON field names; the campaign's existing default behavior is preserved. Damage resets the quiet count; clearing all moss prevents regrowth. New clumps increase the remaining goal. Exits, powers and other obstacles are excluded. Native regression evidence is in `16_PLAYBACK_AND_UI_REVIEW.md`.

## Chapter 1 configuration
All levels have two to four target types: 16 levels have two, 21 have three, 13 have four. `Inventories/Chapter01_Levels.csv` is the exact per-level table; `Obstacle_Instances.csv` lists every anchor/HP/footprint. Difficulty labels are authoring intent, not measured player difficulty.

Level 50 is 11×11 with 111 active cells, **44 moves**, 18 crates, two Storm Crystal columns, eight Water Spirit Pods and one 2×2 Rainlight Cabinet. Goals are crate 18 / crystal 2 / pod 8 / rainlight 4. The 29 logical obstacles reserve 46 cells (41.4% coverage). Authored banks and exclusive crystal lanes are deliberate. Preserve them while balancing.

For future levels, require unique ID, mask bounds, non-overlapping footprints, no gem/obstacle overlap, valid spawns/exits, goal units matching collectable owners, reachable objectives and reproducible seed. Add human playtests across skill levels; static checks and bot wins are not proof of solvability or parity with Match Villains.

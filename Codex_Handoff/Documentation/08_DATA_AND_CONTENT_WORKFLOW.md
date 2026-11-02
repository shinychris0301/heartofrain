# Data, assets and content workflow

## Author a level
Copy the schema of an appropriate current level; assign a unique chapter/global ID. Author a mask and concentrated obstacle formations first, then initial gems, spawns/exits and goals. Two to four goal types is the current policy. Avoid random scattered blockers as a substitute for a designed problem. Keep obstacle silhouettes distinct from gems and preserve exclusive occupancy.

Use the full footprint when validating cabinet/crystal placement. Delivery exits require a feasible jar route. A crystal lane is exclusive to that crystal family. Goal totals count logical items: two full crystal columns are two goals, while a full cabinet releases four rainlights. Update introduction text, localization and asset bindings with a new family. Data-only fields must be connected to runtime before they can change behavior.

Run static checks, deterministic replay and human tests. Record moves, seed, win rate with cohort/sample size, median attempts, remaining moves, time, power use, quits and qualitative confusion. Preserve versioned historical results so a new refill algorithm is not compared as if it were the old level. Current difficulty labels and diagnostic bot runs are not player balance certification.

## Update an asset
Identify the live GUID/resource owner. Keep a source/reference copy and change only the intended component. Match silhouette, palette, optical scale, padding, pivot, alpha and material. Replace the asset under its existing GUID if it is the same logical asset. If a new asset/ID is required, update every binding and keep a migration note. Never rename a historical tile file solely because its label seems outdated.

For sprite sheets, validate frame rectangles, page dimensions, clip names, fps and durations. Export preview frames against the actual board and background, including edge cases. For UI, compare the built page at multiple device sizes, not only a concept image. Store the approval and chosen revision in a design decision log.

## Add a translated string or story beat
Use a stable key and update en/es/fr/de/ru. Keep fallback behavior explicit. Preserve narrative continuity and source chapter/page. Check variable placeholders, punctuation, Cyrillic, line lengths and buttons. Keep raw UI labels out of images where localization would need new art. Japanese remains excluded.

## Catalog/config schema proposals
Future store products need separate stable offer ID, platform product IDs, offer version, item quantities, eligibility, optional real expiry and store metadata. UI price text is not the authoritative amount. Keep four starting quantities separate and four tool quantities explicit; `boostersEach` is acceptable only as a migration convenience, not an opaque grant contract.

Future level configurations should include schema version, content version, RNG version and validated growth parameters. Pin configuration for an active attempt. New versions must not reinterpret an in-progress save without a defined migration. Remote configuration changes should be staged, validated, monitored and reversible.

## Inventories supplied
| File | Use |
| --- | --- |
| `Inventories/Chapter01_Levels.csv` | All 50 level dimensions, moves, goals, families and density |
| `Inventories/Obstacle_Instances.csv` | Every obstacle anchor, HP, footprint and motion |
| `Inventories/Story_Chapter_Catalog.csv` | 100 story entries, source titles/pages and planned 50-level ranges |
| `Inventories/Shop_Preview_Catalog.csv` | Exact 12 current sample offers; prices are mock display values |
| `Inventories/Code_Index.csv` | All C# files, namespaces and types |
| `Inventories/Editor_Menus.csv` | Actual menu strings and declaring files |
| `Inventories/Scene_Index.csv` | Enabled build-scene order and existence |
| `Inventories/Raster_Asset_Index.csv` | Image dimensions, source size and SHA-256 |
| `Inventories/Serialized_Asset_Bindings.csv` | Asset-object GUID references and resolved source paths |
| `Inventories/Resource_Key_Index.csv` | Runtime Resources keys and files |
| `Inventories/Embedded_Documents.csv` | Documentation already inside Unity |
| `Inventories/Unity_Files_SHA256.json` | Integrity baseline for all Unity files |

`Tools/audit_project.py` can regenerate inventories after code/content changes. Python/Pillow are documentation tooling dependencies, not mobile runtime requirements.

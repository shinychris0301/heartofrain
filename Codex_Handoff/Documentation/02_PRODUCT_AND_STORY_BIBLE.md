# Product and story bible

## Product loop
Heart of the Rain is a portrait mobile match-3 adventure about restoring water, light and community. Players enter a chapter scene from Home, choose optional starting powers, complete obstacle goals, receive first-clear rewards, and progress through chapter stories. Journey replays unlocked narrative episodes. Teams and rankings are intended supporting social loops, currently represented by local demo data.

The short loop is choose → match/activate → satisfy goals → celebrate → next level. The medium loop is 50 levels → chapter-specific resolution → next chapter. Do not grant chapter completion repeatedly when replaying level 50. Future content needs explicit opening, playable range, ending, reward and unlock conditions.

## World and visual vocabulary
The original book is a fictional fantasy inspired by a fourteenth-century setting; it is not a historical reconstruction. Ancient Moscow's Heart is a faceted golden wardstone, not an anatomical heart. Its light reaches the city through water channels. Varkul of the Hollow Furnace steals it and turns those channels toward fire. Repair, craft, rain, stone, timber, ceramics, blue glass, geometric metalwork and restrained warm light support the story.

Avoid unrelated machine-part shapes, generic modern technology, and animal characters/motifs. “Deer daisies” refers to flowers. Decorative magic should support readable gameplay silhouettes, not obscure cell occupancy.

## Cast identity
| Character | Source identity | Visual anchors |
| --- | --- | --- |
| Ivan | 32, village-born general | Dark hair, short beard, steel lamellar armor, burgundy cloak, geometric clasp |
| Mila | 25, lantern craftswoman / apprentice Rainwarden | Chestnut braid, indigo dress, cream linen, copper clasp, silver circlet, blue-glass lantern |
| Daria | 30, engineer and cartographer | Dark curls, olive cloak, tool sash; preserve current front-facing smiling celebration art |
| Yaroslav | 48, companion | Gray hair/beard, blue cloak, rectangular geometric shield |
| Boris | 36, companion | Broad build, copper beard, rust tunic and work apron |
| Varkul | Lord of the Hollow Furnace | Principal antagonist; supporting humanoid servants include Malrec, Serev and Ruzhen |

Code uses `Daria`; the user has also used “Dariya.” Do not rename serialized resources/IDs to normalize spelling.

## Chapter 1
App title: **The Village Well**. Location: Zarech. Ivan returns as a general; Daria challenges whether he still knows the villagers. He helps repair the well. A messenger reports that the city's Heart is faltering. The finale should resolve the repaired well, water and community before opening the wider journey. The beginning and end are separate narrative states, not interchangeable celebration clips.

Playable data is `M47/Data/Levels/C01_L001.json` through `C01_L050.json`. Journey has 100 chapter text entries, but later entries do not establish playable boards, finished chapter cinematics, or complete chapter artwork. `Inventories/Story_Chapter_Catalog.csv` distinguishes planned level ranges from produced content.

## Long-arc continuity — spoilers
The golden crystal compass points toward the Heart, not a guaranteed safe route. Mila's lantern guides existing water/ward light; it cannot create instant storms or resurrect people. In Chapter 86 Mila saves Ivan from fatal magical backlash and dies. There is no hidden survival, resurrection, or ghost replacement. The Heart returns in Chapter 93, followed by rain, extinguished fire, sunlight, flowers and rebuilding with memory.

The source book asks for respectful presentation through Chapters 81–90. Do not place cheerful confetti over the death scene or sell a purchase implying Mila can be saved. A failed board must not be framed as causing her scripted death. Chapter completion tone can differ from ordinary level celebration; design those later scenes with the user.

## Future chapter production contract
Before a chapter is considered ready, supply its narrative ID/title, 50 level IDs, opening/ending scripts in all supported languages, location background and variants, obstacle introductions, level difficulty plan, objective icons, music cues, finale, Journey card, unlock/first-clear rules, asset provenance and device QA. A story entry alone is not a finished chapter.

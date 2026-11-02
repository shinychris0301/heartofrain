# App page and flow contracts
These contracts combine the user's page requirements with current implementation boundaries. Review each page in the connected app, not only its standalone scene.

## Navigation and page state
The five main pages are Journey, Leaderboard, Home, Teams and Shop. Use the shared Home navigation panel/active icon treatment, selected on click/tap. Page transitions should preserve the Home profile and dispose or hide old listeners/views. A modal blocks the underlying page; repeated taps must not launch duplicate views or levels. Current pages are local runtime implementations; network loading/error/pagination states are future service work where noted.

| Page | Player-facing content | Current implementation / next requirement |
| --- | --- | --- |
| Home | Avatar, coins, lives, settings, current chapter background, Start Level with number, event positions | HomeState/preview JSON supplies values; replace demo bootstrap and sample timers with profile/event services |
| Journey | Unlocked chapter opening/ending replay and chapter progress | JourneyCatalog has100 entries and localized story data; only Chapter1 has playable levels; unrevealed art is not finished chapter production |
| Leaderboard: Friends | Friend list, search, add/remove management | Local demo search/pending/removal; needs authenticated friend requests and privacy/error states |
| Leaderboard: Players | Player rankings | Demo snapshots/sorting; needs authoritative ranking and pagination/season context |
| Leaderboard: Teams | Team rankings | Demo snapshots; needs server team score and season handling |
| Teams | Your team, members, chat/mail, help/life requests | Local preview messages/actions; no live messaging or durable life grants; needs moderation/report/block and claim ledger |
| Shop | Special Offers carousel, Mega Offers, coin list | Preview catalog and sliding/swipe layout; no billing. No pagination buttons. Separate Rocket/Bomb rewards |
| App Settings | Music, sound, hints, inventory, language, help/support, follow, Terms/Privacy | Preferences/language persist; inventory is a snapshot; official URLs are empty until configured |

## Pre-level modal
Opened by Home Start Level. Display the level's goal icons/counts, potential first-clear rewards and four independent optional starting items: Rocket, Bomb, Rainbow Orb, Golden Seeker. Replays must not promise another first-clear reward. Show lives in the intended top-left area with adequate clearance; preserve the approved compact panel proportions.

At zero lives the Play button becomes "Refill 500" (action `refill`, a 500-coin full refill) when the wallet allows, otherwise "No lives", and carries "Next life in mm:ss" inside the button; the modal refreshes once a second and picks up a credited life. A refused refill shows "Not enough coins" or "No lives remaining" in the feedback line (`50_LIFE_REGENERATION_REVIEW.md`).

Selecting an item reserves a choice, not a debit. Start checks lives, blocks repeated input and initializes the board. Inventory is consumed only after initialization and actual starting-power placement succeed. If startup fails, show a retryable error and preserve stock. Closing the modal has no life/item charge. The current scene flow implements this in local memory; persistence must make it crash-safe.

## Gameplay settings and exit
The in-game settings control pauses gameplay and offers music/SFX toggles and Exit. Exiting first opens End Level with the life-loss explanation/image and cancel/confirm choices. Cancel resumes the same attempt with no charge. Confirm applies one life loss and opens the retry pre-level modal with Try Again. Retry selection follows the same separate-item stock rules. App settings also exposes hints; avoid assuming every setting appears on both modal variants.

Confirmed exit and the two loss end states settle through the same `HomeLevelFlow` path. A loss (`Out of moves`, or `No legal moves` after a failed reshuffle) first shows the HUD's approved loss dialog, titled "Out of moves" or "No moves left", while the loss cue plays; tapping "Try again" charges the life and opens the retry pre-level (owner decision, 22 October 2026; `53_LOSS_BEAT_REVIEW.md`). An engine-fault release shows no dialog and refunds the starting items. There is no implemented paid extra-move continuation. Decide interrupted-attempt/life-regeneration policy explicitly rather than deriving it from demo restarts.

## Successful level and chapter completion
HomeLevelFlow validates the active source/level, waits for the model to finish resolving, and settles first-clear rewards locally. Ordinary wins show Daria's celebration overlay with blackened background, not a victory modal. After the overlay/skip, advance to the next pre-level if one exists. A first clear of Chapter1 Level50 runs the chapter-specific finale and routes to the Journey ending. The available campaign caps at50; do not open a fictional Level51.

Replay behavior must not duplicate rewards or first-clear finale flags. The proposed durable receipt should survive app termination before/during/after the animation. Skipping animation skips presentation only, never the reward transaction. The last delivered sleeve correction is shared by ordinary victory and finale.

## First start
The sequence contains Prologue, Chapter, Match, Rocket, Clear, Ready and Complete stages, with narrative animation/background music and three practice-board fixtures. Tutorial progress/settings use the settings store. Story skip leads into practice; practice skipping can complete the sequence. Verify resume/skip on device and in every supported locale. Production boot must distinguish a new profile from a returning player and must not reset progress because the preview scene is opened.

## Locale and accessibility review
Language choices are English, Spanish, French, German and Russian. No Japanese. Changing language should update open content coherently, including story, labels and retry/errors. Preserve reduced-motion behavior and music/SFX preferences across transitions. Check target readability without relying on color alone, button focus/input blocking, safe areas, large counters and long names. Device screenshots are required before a page is declared consistent with its approved design.

# Rewarded video Home shortcut — R1

## Package and scope

Reviewed `Rewarded_Ad_Home_Design_R1.zip`: one 512×512 transparent runtime icon, one 64-pixel legibility preview, and `DESIGN_HANDOFF.md`. The ZIP's handoff was treated as design input. The requested Home placement below **Задание**, approved blue and gold treatment, and **Видео** label were implemented in the current Unity project.

## Implementation

- Imported the 512×512 icon as a single Unity Sprite with its own GUID. Reused the existing Home ribbon and status plate; no approved Home art was replaced.
- The imported icon's SHA-256 matches the ZIP entry: `B3DDDA9DDE48D85447F9F802C0EC2FD19E98BB712EC488162F264E8E4FB368A1`.
- Added a third right-rail entry below Team Quest. On short screens it moves into the existing Events drawer, below Team Quest there. The asset, label, status plate, and hit target share one layout group.
- The entry routes to the existing Shop rewarded-video card. Opening the page refreshes reward status first and still requires a separate, explicit Watch action and consent. It does not request or grant an ad on Home.
- Home displays the last known availability from the shared rewarded service: Ready, cooldown, daily limit, pending, or unavailable. Before Shop has refreshed the status, the plate shows a neutral dash. The shortcut is hidden when the packaged ad configuration is disabled or the app is in local economy mode, so the first-moderation build does not expose a dead ad entry.
- Added **Video** and **Later** translations, including Russian **Видео** and **Позже**. Transient reward availability survives profile-driven Home state refreshes without being saved as player progress.

## Verification

- Unity 2022.3.62f3 import and layout check: [Check.txt](../../Verification/Evidence/RewardedHome135/Check.txt). It checked sprite binding/import, Russian text, geometry at 360×640, 390×844, 347×780 and 320×480, drawer fallback, and hidden state.
- Native Unity Play Mode Home UGUI captures: [360×640](../../Verification/Evidence/RewardedHome135/Home_360x640.png), [390×844](../../Verification/Evidence/RewardedHome135/Home_390x844.png), with [capture result](../../Verification/Evidence/RewardedHome135/Capture.txt). The runtime Home route forwarded `video` successfully.
- `git -c core.whitespace=cr-at-eol diff --check` passed for the touched runtime files. Unity compiled the new code.

The captures are **Unity Editor evidence**, not Android/device or live-ad evidence. The ordinary checked-in ad configuration is disabled. A later configured Android candidate must verify the Home-to-Shop tap, Yandex load, consent, completed video, the backend's 400-coin idempotent claim, daily cap, cooldown, and restart recovery on device before ad availability is claimed.

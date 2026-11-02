# Heart of the Rain — 28.5-second vertical promo

Output: `HeartOfTheRain_Promo_28s_1080x1920.mp4` (H.264/AAC, 1080×1920, 30 fps). Rebuild with `powershell -NoProfile -ExecutionPolicy Bypass -File Marketing/LaunchVideo/build_ad.ps1` from the repository root. The script uses FFmpeg and writes intermediate encodes under `.verification-cache/Promo121/Segments`.

| Time | Scene | Source |
| --- | --- | --- |
| 0.0–2.5 s | Opening artwork and title | Approved `App/Launch/Art` PNGs |
| 2.5–5.0 s | Home screen | 29 Oct realme Android recording `Verification/Evidence/Promo121/Raw/Gameplay01.mp4` |
| 5.0–7.5 s | Journey chapter cards | 29 Oct realme Android recording `Verification/Evidence/Promo121/Raw/JourneyStoryHome.mp4` |
| 7.5–10.0 s | Chapter 1 opening story | Same realme recording |
| 10.0–12.0 s | Level 35 start and booster selection | 29 Oct realme screenshot `Verification/Evidence/Promo121/Raw/LevelStartPreview.png` |
| 12.0–15.0 s | Live rocket and board reaction | Realme recording `Gameplay01.mp4` |
| 15.0–18.0 s | Hammer booster | Prior Heart of the Rain Android capture `Verification/Evidence/ObstacleFall/Touch/Hammer.mp4` |
| 18.0–20.7 s | Bomb combination | Prior Heart of the Rain Android capture `Verification/Evidence/Gameplay79/Android/Touch/MixedBomb.mp4` |
| 20.7–23.4 s | Rainbow Orb combination | Prior Heart of the Rain Android capture `Verification/Evidence/Gameplay79/Android/Touch/MixedOrb.mp4` |
| 23.4–26.2 s | Chained power-ups | Prior Heart of the Rain Android capture `Verification/Evidence/Gameplay79/Android/Touch/MixedChain.mp4` |
| 26.2–28.5 s | Closing artwork and title | Approved `App/Launch/Art` PNGs |

The soundtrack and synchronized effect sounds come from the project's own `Village_Settings_Review_Loop.wav` and `M47/Audio` files. The Android captures themselves have no recorded audio.

This is a review cut. The last four gameplay shots are archived verification captures from earlier builds; the current phone disconnected before a new full booster/power-up capture could be made. Development Build marks remain visible in some gameplay shots. Check the final release build on a device and replace archived shots before publishing an ad that claims exact current-build visuals.

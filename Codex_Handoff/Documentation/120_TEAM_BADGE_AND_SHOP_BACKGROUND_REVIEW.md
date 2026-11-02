# Review 120 — Team badge selection and Shop background

Status: **Implemented and checked on the connected Android phone.** Live team creation remains unavailable until the HTTPS social backend is configured.

## Cause and changes

The Create Team layout disabled the name, description and badge controls whenever `view.connected` was false. The badge action handler also returned before processing local picker actions when no social session existed. On the current phone, the service is unconfigured, so the Choose button was grey and could not open the picker. The twelve badge assets and their click bindings were present.

Create Team now allows local drafting and badge selection while offline. The final Create button still requires an authenticated social session; no team, membership or reward is fabricated. The picker applies its selected badge to the Create preview after confirmation.

Shop now resolves the same `TA_Background` sprite used by Teams through its existing `TeamsAssets` resource chain. Both pages use the same full-screen cover crop, including safe-area extension. No artwork or asset GUID was changed.

## Verification

- Unity 2022.3.62f3 Teams Access component suite: **23,426 checks / 37 cases passed**, including offline picker open, selection, preview update and disabled backend submission. Report: `Verification/Evidence/Review118/Native/teams_access_BadgeShop120/Native/TeamsAccess109.json`.
- Unity 2022.3.62f3 Shop asset validation passed. The log in `Verification/Evidence/Review120/Editor/ShopBackground.log` confirms the shared background sprite resolves.
- An isolated Unity 6000.3.27f1 ARM64 Development APK built from the current main source with **zero errors and four warnings**. The build and invocation reports are in `Verification/Evidence/Review109/Native/BadgeShop120Build/`; the invocation confirms main source bytes and asset GUIDs were preserved.
- The APK at `Unity/Builds/Review120/HeartOfTheRain_Review120_Android_Test.apk` was installed in place on the realme RMX3938 at 720×1600. The installed `base.apk` SHA-256 matches the build: `c1337572f60d25456db38235fd6714ae281b541dd4de9f33cfbe99016dacecee`. Level 35, 300 coins and 3/5 lives remained after the update. The badge picker opened, the Well badge was selected and appeared on Create, and Shop painted the Teams background. No app fatal exception was found in the sampled process log.

Physical captures are in `Verification/Evidence/Review120/Android/`: `TeamCreateTap.png` shows the old disabled Choose button; `BadgePicker.png` and `BadgeSelected.png` show the new flow; `ShopSharedBackground.png` shows the updated Shop; `PreInstall.png` and `AfterInstall_Home.png` record the in-place progress check.

This is an internal debug-signed Development build. The configured social backend, real team creation and release build remain separate acceptance gates.

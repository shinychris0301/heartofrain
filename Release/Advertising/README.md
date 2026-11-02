# Rewarded video setup

The approved first placement is a voluntary **Shop video for 400 coins**,
**three credited rewards per player-local day**, with a
**600-second cooldown after each credit**. The Shop note says that free rewards
can be claimed three times a day; it no longer advertises a fixed timezone or
cooldown schedule. Reservations,
no fill, cancellation and incomplete videos do not consume quota or start a
cooldown. Crossing midnight does not shorten an existing cooldown.

The Android client sends its `java.util.TimeZone` ID and current offset only
when requesting authenticated ad status. The server uses its own UTC clock and
the IANA zone to calculate consecutive local midnights, including 23/25-hour
daylight-saving days. Country rankings do not determine the reward timezone.
Python's standard `zoneinfo` uses the system timezone database or the pinned
first-party `tzdata` package on Windows. See the [Python documentation](https://docs.python.org/3/library/zoneinfo.html)
and [Android TimeZone reference](https://developer.android.com/reference/java/util/TimeZone).

A change of timezone waits until the current quota window ends, then follows
the new zone's local midnights. It cannot clear the current three-reward quota.
The travel transition can be shorter than a normal day; there is no additional
24-hour lockout. The device clock cannot advance a server quota or cooldown.
Unsupported/non-Android zone IDs use a persisted offset fallback, refreshed on
Shop status; this fallback cannot anticipate DST until an updated offset is
reported. Older clients retain the UTC+10 compatibility fallback until a local
calendar is supplied. Existing credited UTC+10 rewards survive migration: that
current window completes before the new local calendar takes effect.

The ordinary SDK-free game shows an unavailable placement. The owner supplied
rewarded unit `R-M-20291714-1` and interstitial unit `R-M-20291714-2`. Publisher
app ownership, moderation, live delivery and advertising revenue have not been
verified. Opening Shop never initializes/loads the SDK. The player must
choose the video, review the explanation/privacy link and explicitly start it.
The first integration requests non-personalized, age-restricted ads, disables
location tracking and AppMetrica ad analytics reporting. Required native
AppMetrica/identifier/referrer components remain packaged in the SDK profile;
these settings do not establish zero collection or zero pre-consent traffic.

## Current supplied placements and activation

| Format | Public ID | Current behavior |
| --- | --- | --- |
| Rewarded video | `R-M-20291714-1` | Voluntary Shop offer; requires explicit consent, an SDK-enabled build and configured managed backend. |
| Interstitial | `R-M-20291714-2` | Stored separately; no load/show call or automatic interruption point. |

`advertising.example.json` and the packaged default deliberately use
`enabled: false` and an empty privacy URL. The owner confirmed that hosting and
privacy URLs are not ready. A registered unit ID does not supply those inputs.
The current integration work uses the already reviewed official SDK 8.6.0;
there is no automatic SDK or main-project engine upgrade.

The 107 build tooling prepares a fresh isolated Unity 6000.3.27f1 development
candidate. It can validate and temporarily package separate advertising and
six-field managed-server payloads under its own active build lease. It does not
reuse or forge the older 104 lease. The ordinary project remains Unity
2022.3.62f3 without vendor import. Actual build/test results and outstanding
Android acceptance must be read from the current checkpoint evidence; preparing
a profile or setting IDs does not demonstrate a video impression or reward.

The unconfigured review package is `com.heartoftherain.ads107review`;
configured development builds use `com.heartoftherain.stagingreview`. Production
signing, publishing and the existing production service gates remain separate.
See [SETUP107.txt](SETUP107.txt) for the public inputs and commands.

## Registration and configuration

1. Sign in or register at [Yandex Advertising Network](https://partner.yandex.com/).
   Complete the publisher/payment details and add an Android application using
   the actual owned package and RuStore listing. The current proposed release
   package is `com.heartoftherain.game`; it is not reserved by these files.
2. Create a **rewarded-video** ad unit for this application. Record its public
   `R-M-…-…` unit ID and complete the provider's app ownership, listing and
   moderation steps. Follow the current [official Unity integration guide](https://ads.yandex.com/helpcenter/en/dev/unity/quick-start).
3. Publish the app's Russian privacy information covering the actual SDK and
   backend processing. Review the intended audience and the provider's required
   disclosures. Provide the real HTTPS privacy URL/version. Do not use a demo
   unit for a live app or click live ads during testing.
4. Keep `advertising.example.json` disabled until the real privacy and backend
   URLs are available. The current v2 configuration packages both public IDs as
   `Resources/HOTR_Advertising/Configuration`. A packaged value owns selection,
   including when disabled or invalid; a device file cannot override it. The
   old persistent `HOTR_Advertising.json` is accepted only if no packaged key
   exists. No publisher password, payout credential, backend bearer, signing
   key or private API key belongs in either configuration. See [SETUP107.txt](SETUP107.txt).
5. Select the configured managed backend account and HTTPS origin separately;
   local wallet balances are not migrated. Enable the supported staging service
   through its owned descriptor and stopped transition described below. The supported staging launcher requires
   explicit `rewardedAdsEnabled: true` in its descriptor and, for an existing
   root, the stopped-service `configure-rewarded-ads` command. Editing the
   repository default alone does not activate that launcher. Its fixed policy is validated by both
   sides. Schema 8 adds durable local calendars and reserved/claim offsets while
   preserving existing opportunities, commands, wallet ledgers and receipts;
   take a verified backup before deployment. Deploy the API and updated client
   together. Older clients cannot parse a non-UTC+10 response, and existing
   installations should be upgraded before changing their reward calendar.
6. Build the separate SDK profile described below, verify real demo video
   display/dismissal/no-fill, restart/reconnect, account fencing and reward
   projection on Android, then conduct a controlled live-unit verification.
   Publisher registration, a usable HTTPS backend and the existing RuStore
   release gates remain necessary. Configuring JSON alone does not activate
   production services or clear those gates.

## Delivery and trust

`GET /v1/ads/rewarded/status`, `POST /reserve`, and opportunity `GET`,
`POST /client-completion`, `/claim`, `/cancel` live under `/v1/ads/rewarded`.
All use the authenticated stable internal player. Reserve/report/claim/cancel
commands and the opportunity are durably correlated without storing credentials
in the ad journal. SDK completion is persisted before networking; the backend
claim credits the fixed amount atomically and deduplicates callbacks/retries.
The app refreshes the authoritative wallet before displaying receipt feedback.
`GET /status` accepts optional `timeZoneId` and `utcOffsetSeconds` calendar
preferences; these never supply the current time or reward amount. A shared
per-player calendar and claim-time counts serialize eligibility across devices.
Reservation request bytes and journal operation IDs remain unchanged through
timezone changes, so pending and duplicate recovery cannot create a new grant.
Closing a video early, cancelling, no fill or a failed payment does not alter a
level, life or wallet. This Shop placement is unavailable during an active level.

**Yandex does not provide server-side reward verification.** See its
[official FAQ](https://ads.yandex.com/helpcenter/en/support/faq/sdk-integration).
The explicit integration mode is `sdk_client_reported_capped`:
`completionAuthoritative=false`, `verifiedAt=0`, and receipts identify that
source. A modified authenticated client can falsely report completion up to
the server's limit of 1,200 coins/day. Server caps, idempotency and ownership
checks limit this exposure; they do not prove an ad impression. There is no
fabricated Yandex signature/webhook. A separate server-only trusted-completion
interface remains for a future verifiable provider. Its synthetic HMAC adapter
is restricted to in-process local/staging tests and has no public grant route.

## Historical SDK build evidence and current build support

The main project remains on Unity 2022.3.62f3 with its original packages/tool
settings and no native Yandex dependency. The actual official Unity SDK 8.6.0
package is hash-pinned and reviewed by `Verification/Tools/Ads85`.

The isolated SDK-only ARM64 IL2CPP export compiles the actual adapter's SDK
branch. External Java 17/Gradle 8.9/AGP 8.7 assembly succeeds, using the installed
pinned NDK through an explicit generated task path. The stock control failed
resolving the AGP 7.4.2 plugin; this does not prove a stock SDK incompatibility.
No Unity engine upgrade, licensing bypass or global toolchain switch occurs.

`prepare_yandex85_game.py` prepares a separate full-game internal review profile
with current artwork/GUIDs/scenes and the actual provider, no demo define and
no publisher configuration. Follow its generated build instructions. Empty
SDK-fixture compilation alone does not establish full-game SDK integration.
The later actual two-scene full-game export and external assembly now pass,
along with 92 static APK checks in
`Verification/Evidence/ShopAds85/SDK/FullGameBuild/Report.json`. The isolated
internal package is `com.heartoftherain.ads85review`, API 26/35, ARM64 IL2CPP,
with the Russian app name and portrait policy. It has not been installed or
launched; no ad display, reward, runtime privacy or production acceptance is
established. That SDK-enabled full-game clone predates the subsequent narrow
reserve-denial recovery repair; its provider/native integration bytes remain
exact, while the repaired flow is verified separately. Prepare a fresh SDK
profile from the final current sources for configured-device acceptance.
Current result scope and exact evidence are tracked
in `Codex_Handoff/Documentation/85_RUBLE_SHOP_AND_REWARDED_ADS_REVIEW.md`.

Main-provider code is guarded by `HOTR_YANDEX_ADS`; only an explicitly prepared
SDK build profile should define it. The ordinary shipping guard still blocks
unconfigured release/payment identities. Actual store prices continue to come
from RuStore `GetProducts.amountLabel`; the six RUB labels in the current
preview are the launch proposal, not live Console quotations.

# Launch preparation and owner inputs — review 93

Reviewed 26 October 2026. This checklist accompanies the new app/backend review;
it records required information and acceptance work, not a production approval.
The accepted starting checkpoint is `89b32414` / Progress92. Each historical or
fresh Review93 result below retains its own source, time and execution scope;
passing a local review does not establish missing external acceptance.

## Are all testing errors fixed?

**No.** The recent full-display/background, tutorial-input and progress-bar
repairs have targeted passing evidence. They do not close every historical
failure or prove operation of unconfigured services.

| Area | Scoped evidence | Still required |
| --- | --- | --- |
| Rain Cup and related progress fills | Progress92: 16,823 native checks, including 120 cases across four sizes; two internal builds; actual phone review with save preservation | Wider physical-device coverage; these results do not measure gameplay performance |
| Display and tutorial | Display88 and PageBackdrop90 provide their separate native/phone results | Complete locale/modal/device matrix and actual L50 finale review; excluded/partial rows remain excluded |
| Current app compile/native review | Review93 executes 39 suites: 37 pass 185,463 checks and two Account suites retain FAIL; both current SDK-free internal builds/static checks pass on 5,407 Unity inputs | Ordinary configured Android/provider acceptance, broader physical coverage and the retained account/performance gaps |
| Current physical phone | Current APK replacement, 11 scoped UI cases/15 OS captures, 1,716-check/50-board transient native regression and normal relaunch preserve the owner's save | Full human campaign, foreground managed account/provider flows, more physical devices and long sessions; stills and accelerated fixture actions do not certify smoothness |
| Backend | Review93 final service run passes 472 tests with the approved real worker, zero skips; 20 transaction-time regressions and the separate local TCP/restart/restore drill pass | Operational deployment and ordinary configured Android/provider acceptance remain separate |
| Account recovery UI | Review93 repeats both strict clipboard-readback FAILs and the same failure in a separate hidden non-batch run; Win32 metadata permits opening the clipboard | Resolve the actual copy/readback discrepancy in a foreground context, then complete connected recovery/logout/deletion and disposable Android acceptance; exact cause and Android behavior remain unproven |
| Gameplay performance | Review93 retains 1,983 quiet physical diagnostic frames, including a 99.943 ms victory interval and a 50.206 ms first-command interval; older raw slow samples remain distinct | Correlated CPU/render/GPU/presentation traces, repeated dense chains, the separate historical 359 ms handoff, long-session/low-memory testing and fresh reference comparison; no whole-game smoothness approval |
| Payments, advertising, VK | Disabled adapters/services and isolated tests exist | Actual registrations, configured signed Android build, real provider sandbox/video/consent and restart/recovery acceptance |
| Public operations | Local/staging services, replay worker and backup/restore tools exist | Owned HTTPS deployment, production configuration, restore/load/monitoring drills, support and staffed moderation |

Primary project records: [Review86](../../Codex_Handoff/Documentation/86_COMPREHENSIVE_APP_BACKEND_REVIEW.md),
[Physical87](../../Codex_Handoff/Documentation/87_PHYSICAL_PHONE_CHECKLIST_REVIEW.md),
[RegionalAccounts89](../../Codex_Handoff/Documentation/89_REGIONAL_RANKINGS_VK_LOCAL_ADS_REVIEW.md),
[Progress92](../../Codex_Handoff/Documentation/92_PROGRESS_BAR_REVIEW.md),
[current Review93](../../Codex_Handoff/Documentation/93_APP_BACKEND_OPERATIONAL_REVIEW.md).
Historical counts are scoped results, not a sum of current-source coverage.

## Information the owner needs to prepare

Share the non-secret values in the following table when they are available.
Private material is listed separately and must stay in owner-controlled secret
storage, outside chat, the Git repository, Unity assets, screenshots and logs.

| Input | Current value or decision | What the owner must provide |
| --- | --- | --- |
| Publisher | No registered publisher is supplied by the project | Legal publisher name/status/country; responsible person and Console access; verification and payout setup completed directly with RuStore |
| Visible app name | **Сердце дождя** | Confirm the final Russian store name, developer display name and rights to the supplied art/music/fonts |
| Android package | Current internal build: `com.heartoftherain.verification`; release candidate: `com.heartoftherain.game` | Actual reserved production package; do not treat the candidate as registered or reuse the verification signer |
| Console Application ID | Unassigned | Numeric ID from the real application page in RuStore Console |
| Version | Internal tests use their own versioning | First production versionName/versionCode and the release/change-log text; subsequent codes must increase |
| Coin products | Six quantities and prices below are approved for preparation | Actual Console IDs, consumable type, RUB prices, icons/titles and publication/sandbox status |
| Payment-return scheme | Candidate `heartoftherain-pay` | Confirm unique ASCII scheme, package/manifest bindings and external-bank return route; this is separate from the VK HTTPS callback |
| HTTPS backend | Not deployed | Owned domain, staging and production HTTPS origins, hosting account, region/data location, persistent disk/database and operator access |
| Payment notifications | Implemented paths, disabled/unhosted | Actual HTTPS sandbox and production callback URLs; Console connection-check result; trusted ingress topology and current provider sender rules |
| Release signer | No owner release signer supplied | Public certificate SHA256 fingerprint, alias/reference and secure build-time secret references; private key/password stay external |
| VK ID | Registration and confirmed sign-in code added in checkpoint102; no live registration | Registered VK client ID and exact allowed HTTPS callback URL; current102 verification results, real test accounts and Android consent/return acceptance |
| Google | Unavailable/unimplemented in the current release path | Decide whether to omit the unavailable provider at launch or scope a separate registered integration; an existing disabled button is not working sign-in |
| Rewarded advertising | No live publisher/unit supplied | Yandex publisher registration/payout details, actual rewarded unit ID, verified app/listing, privacy URL/version and audience settings |
| Legal/support | Factual operator URLs are not supplied | Published Russian privacy policy, terms/community rules, support/deletion/refund contacts and retention policy; responsible operator and legal review |
| Audience/territories | No publication decision supplied | Countries, age/content classification, intended audience including children, languages and supported devices |
| Operations | Not publicly staffed/deployed | Expected launch traffic, budget, monitoring/on-call contacts, recovery objectives, moderator roster and response process |
| Verification | One real-phone family has scoped current Review93 UI/regression/diagnostic evidence | Disposable test users/devices, Android 8 baseline and tablet/low-memory targets, sandbox access and controlled real-payment test budget |

## Approved coin prices

The owner revised the four larger packs on 27 October 2026 in review98; the
two smaller prices and all coin quantities remain unchanged. These are owner-approved configuration values, not a market-wide
standard or evidence of Console publication.

| Coins | Internal offer | Proposed Console product ID | New RUB price | Minor units |
| ---: | --- | --- | ---: | ---: |
| 1,000 | `coins-1000` | `hotr_coins_1000` | 99 ₽ | 9,900 |
| 5,000 | `coins-5000` | `hotr_coins_5000` | 299 ₽ | 29,900 |
| 10,000 | `coins-10000` | `hotr_coins_10000` | 499 ₽ | 49,900 |
| 25,000 | `coins-25000` | `hotr_coins_25000` | 899 ₽ | 89,900 |
| 50,000 | `coins-50000` | `hotr_coins_50000` | 1,599 ₽ | 159,900 |
| 100,000 | `coins-100000` | `hotr_coins_100000` | 2,999 ₽ | 299,900 |

The updated larger packs improve coins per ruble as pack size increases. These
requested prices still require matching configuration and verification in Console.

Create these as **consumable** products. In Console, select the application,
then **Monetization → Products → New product**, supply the user-facing and
technical fields, and verify each ID/price/type. Unpublished products can be
used in sandbox but are unavailable for live purchases. [Official product setup](https://www.rustore.ru/help/developers/monetization/create-paid-product-in-application).

Use [pricing.proposal.json](pricing.proposal.json) and the disabled
[commerce.example.json](commerce.example.json) as configuration references.
The real SDK `GetProducts` formatted `amountLabel` remains the displayed checkout
price; the server verifies its own configured amount/currency/product mapping.
Changing a preview does not change a Console product or authorize a credit.
Outstanding orders retain their frozen terms; review any price transition before
enabling a new server catalog. Bundle previews are not newly approved purchasable
products.

## Account, Console and signing setup

1. Complete publisher verification and monetization/payout onboarding using the
   owner's true legal status. Delegate Console roles rather than sharing the
   owner's password. Resolve any developer-account restriction before testing.
2. Create the application in [RuStore Console](https://console.rustore.ru/),
   record its assigned ID and confirm the package. Keep the final name,
   category, territories and age rating consistent with the shipped feature set.
3. Select an owner-controlled release signing key and secure backup. Record the
   public certificate fingerprint. Prove a signed-version upgrade preserves
   identity, profile, inventory, pending transactions and settings. Android
   updates depend on compatible package/signing identity. [Official signing guide](https://www.rustore.ru/help/developers/publishing-and-verifying-apps/app-publication/apk-signature).
4. Fill an external copy of [release.example.json](release.example.json), with
   real package, Console ID, scheme, HTTPS origin, legal/support URLs and signer
   fingerprint. Point `HOTR_RUSTORE_RELEASE_CONFIG` to it through controlled
   release tooling. Do not mark unexecuted gates complete to bypass preflight.
5. Produce a non-development, correctly signed configured release candidate.
   The current SDK-free development/ReleaseCompile APKs are internal artifacts;
   neither is a RuStore production release merely because compilation passed.

## Payments and SDK acceptance

The main project stays on Unity **2022.3.62f3**. The frozen SDK record pins
Pay **11.1.0** / Core **10.5.0** and records unmodified vendor manifests declaring
Unity **6000.0**. Earlier isolated Editor/API and Java 17 assembly results do not
resolve vendor support or ordinary configured Android acceptance. Obtain a
supported integration decision before launch; assess any future engine change
separately. Do not silently upgrade or modify vendor version requirements.
The known Unity security advisory and the exact installed Editor/runtime must
also be checked for the release; a version string alone is not a security audit.
[SDK lock](sdk-lock.json), [official Unity release](https://unity.com/releases/editor/whats-new/2022.3.62f3),
[Unity security advisory](https://activation.unity3d.com/security/sept-2025-01).

In the configured SDK profile, set the actual Console ID and unique return
scheme; resolve dependencies; patch and verify the manifest. Use the SDK's
required matching Activity setup. Validate `GetProducts` prices and actual
Android bank return. The SDK documentation's sample API values do not establish
a universal target policy; this project's release baseline is API 26 and its
template target 35 requires final compatibility/policy review. [Pay Unity guide](https://www.rustore.ru/help/en/sdk/pay/unity/11-1-0).

Server secrets include the Console Public API private key and notification
decryption key. Provision external references such as
`HOTR_RUSTORE_PRIVATE_KEY_FILE` and
`HOTR_RUSTORE_NOTIFICATION_KEY_FILE` with service-account-only permissions.
Never put those keys or resulting authorization material in the app. Keep
sandbox and production keys, databases, orders and balances separate.

For notification setup, Console **Monetization → Server notifications** needs a
real HTTPS receiver. Run **Check**, verify decryption and durable receipt
handling, then enable only the intended environment. The current sandbox path
is `/v1/commerce/notifications/rustore/sandbox`; production uses
`/v1/commerce/notifications/rustore/production`. [Official notification setup](https://www.rustore.ru/help/en/developers/monetization/payment-callback/enable-notifications).
Deploy TLS and current provider sender restrictions at the trusted ingress;
do not trust arbitrary forwarded-IP headers or make all requests appear to be
an allowed loopback peer. [Official server requirements](https://www.rustore.ru/help/developers/monetization/payment-callback/server-set-up).

The engineering acceptance matrix must include all of the following on the
**ordinary configured Android app**, with disposable accounts and exact logs:

- All six product mappings, displayed RUB quotes, quantity 1 and immutable order
  bindings; account ownership and currency/amount mismatch rejection.
- Success, user cancellation, provider rejection, timeout and unknown outcome;
  duplicated/late/out-of-order callbacks; app termination before and after
  confirmation, credit and acknowledgement; restart/reconnect reconciliation.
- External banking-app launch/return, absent/outdated RuStore and revoked
  account/session; an empty purchase list must not mean confirmed cancellation.
- No spendable reward at `PAID`; one atomic credit only after verified final
  confirmation. Separate two-step confirmation/acknowledgement responsibilities.
- Refund initiation, reversal and late refund after spending: verify quarantine
  and the approved support/refund policy without inventing negative-balance rules.
- Insufficient-coins Continue → Shop preserves the board/life; successful coin
  delivery returns to the offer and requires a fresh explicit Play On tap.
  Repeated +5 moves cost 900 coins; zero-life full refill costs 900 coins.
- Controlled real-payment and refund verification after sandbox acceptance,
  using an explicit owner-approved spending budget. Synthetic callbacks are not
  proof of provider settlement.

## Hosted backend and realistic operations

Provide the actual host, domain, staging/production separation, storage location,
service identity, network topology and operator contacts. The Python API is
portable; the currently approved gameplay replay bundle is a **Windows Mono
worker protected by Windows Job Objects**. Use that verified worker environment
or separately build/isolate/verify another platform. Do not assume a Linux host
can run the approved worker because Python starts there.

Agree launch concurrency/DAU, request/message rates, database size, retention,
maximum worker queues, availability targets and recovery objectives. No existing
local read probe establishes production capacity. SQLite writer readiness,
filesystem durability and one-host deployment constraints need measurement on
the chosen host before selecting process counts or scale claims.

The staged operational rehearsal needs:

| Surface | Acceptance on the deployed topology |
| --- | --- |
| HTTPS/network | Real trusted certificate chain, DNS, Android TLS, timeouts, reverse proxy body limits, redacted access logs, firewall and genuine client/socket identity |
| Startup and workers | Supervised restart, exact approved worker/source/level bundle, bounded processes/resources/queues and reconciliation/discovery schedules |
| Health | Monitor `/healthz` liveness and `/readyz` real bounded writer/schema probe; test locked/read-only/full-disk/provider/worker failures separately |
| Stateful app | Ordinary managed account selected; no silent import of local balances; expiry/recovery, concurrent devices, network loss and pending-journal ownership fences |
| Money/rewards | Duplicate/reordered commands, concurrent claims/spends, replay settlement, local-day ad quota/DST/travel boundaries, durable notification/reconciliation backlog |
| Load | Isolated synthetic players and realistic mixed reads/writes/chat/gameplay; record p50/p95/p99, errors, lock wait, queue age, CPU/memory/disk and exact workload; preserve worse samples |
| Restore | Scheduled consistent backup, encryption/access control, off-host copy, fresh-path restore, schema/ledger/pending-order verification and measured recovery time/data-loss window |
| Release/rollback | Database backup and migration rehearsal; compatible rollback plan; previous app/API and pending-order behavior; no production database overwrite with a staging snapshot |
| Security | Least-privilege service/moderator identities; revoked-session/block/delete enforcement; TLS/secret rotation; log redaction and dependency/advisory review |
| Support | Alert routing, failed-delivery and refund escalation, compromised account recovery, incident response, abuse reports and an accountable on-call owner |

Use disposable accounts/databases for fault injection. Do not corrupt the
owner's phone save, move sandbox balances into production, send real messages to
unconsenting players, or expose verification/fault endpoints publicly. Backup
tools existing in source do not constitute a completed deployed restore drill.
See [backend operations](../../Backend/README.md).

## Identity, social and regional data

The backend implements managed guest/session/recovery/deletion, friends, direct
and team text messages, blocking/reporting/moderation, private records and opt-in
global/regional standings. They are explicit server-mode integrations; the
ordinary local phone pages remain labelled demo/offline until configured.
Message transport is bounded HTTP polling, without implemented push/media or a
claim of real Cup PvP. The Rain Cup remains the labelled practice competition
with simulated rivals; local rally/life-request previews do not establish live
team-event services.

Prepare multiple synthetic accounts in different selected countries and teams.
Test friend request acceptance/decline/removal, duplicate requests, membership
change, kick/ban/owner closure, direct/team message permissions/unread paging,
block/report after leaving/blocking, moderator actions and deletion. Verify no
wallet, recovery secret, private records or blocked/deleted actor leaks through
rankings or search. Team regional placement currently follows the captain's
selected country; it is not geolocation or verified residency.

For VK, register the actual app using the console linked from the [official VK ID setup](https://github.com/VKCOM/vkid-web-sdk)
and allow exactly `<actual-origin>/v1/identity/vk/callback`. Supply issued
client ID plus `HOTR_VK_ID_REDIRECT_URI` and enable only in the intended server
environment. Checkpoint102 extends the earlier current-guest linking flow with
registration and explicitly confirmed sign-in to an existing VK-linked journey.
The browser callback prepares the target; device-signed completion confirms that
exact target. It does not merge accounts, import offline wallets, rotate existing
recovery codes or automatically settle another device's attempt. Current test
acceptance is recorded in the checkpoint102 review; no live provider acceptance
is implied by source implementation.
Suppress OAuth query strings/codes/tokens in all proxy/app traces. Test real
consent, cancel, conflict, expiry, browser return and process death separately.
[Project VK setup](VK_ID_SETUP.txt), [official VK implementation](https://github.com/VKCOM/vkid-web-sdk).

App-account authentication and RuStore payment authorization are distinct.
Publish a truthful recovery/deletion/migration policy. The unfinished Account
UI acceptance cannot be marked passed because backend deletion tests pass.

## Rewarded advertising

The approved Shop reward is **400 coins, at most three credits per player-local
calendar day, with a 600-second cooldown**. The visible note states three free
rewards per day. A timezone change preserves the current quota window; server
time controls eligibility. Country does not determine the calendar. No-fill,
cancel and incomplete viewing do not consume a credit. This placement remains
outside an active level.

Complete Yandex publisher/app registration, create a rewarded unit, and supply
the actual public unit ID and privacy URL/version. Use provider demo units for
integration testing. Prove video display/early close/completion/no fill,
background/process death/reconnect, duplicate callback, account changes and
same-wallet credit on Android before controlled live-unit acceptance.
[Official Unity setup](https://ads.yandex.com/helpcenter/en/dev/unity/quick-start).

The project deliberately records SDK-client-reported completion as limited
trust, capped by the server. Yandex states that it does not support server-side
reward verification; do not invent an authenticated impression webhook.
The provider also documents AppMetrica dependencies, so non-personalized or
age-restricted settings must not be described as zero data collection.
[Official SDK FAQ](https://ads.yandex.com/helpcenter/en/support/faq/sdk-integration).
The capped exposure is up to 1,200 coins/day per eligible managed player; approve
the abuse/economy risk and operational monitoring. See
[advertising setup](../Advertising/README.md).

## Legal, moderation and store materials

Have the responsible operator/legal reviewer prepare factual Russian documents
covering identity/device keys, optional VK linking, country/timezone preferences,
messages/friends/reports, gameplay/payment ledgers, SDK data, hosting/access,
retention/deletion and legally retained financial/security records. Review
Russian personal-data storage/localization and any cross-border processing for
the actual chosen operator, infrastructure and audience; this checklist is not
a determination of legal compliance.

Publish privacy/support/terms URLs accessible in the app and store listing;
demonstrate account deletion and disclose retained data accurately. Assign
moderators and a complaint-response process before exposing public chat.
RuStore requires UGC reporting/blocking/moderation/contact mechanisms, supported
Android functionality and no Play Integrity barrier to RuStore installation or
launch. [Current moderation rules](https://www.rustore.ru/help/developers/publishing-and-verifying-apps/requirement-apps).

Prepare the Russian short/full description, category/tags, age rating,
territories, truthful feature/reward/purchase/ad disclosures, developer/support
contacts, release notes and reviewer instructions/test access. Do not advertise
Google sign-in, live PvP, push messages or production cloud recovery that is not
delivered and accepted. Use approved owned artwork and actual release-app
screenshots, excluding diagnostic overlays, private chats and device identifiers.

The current listing guide specifies a 512×512 fully filled PNG/JPG icon, up to 3 MB,
and mobile screenshots. The API upload guide specifies at least three matching
orientation screenshots with 320–3840 px sides and portrait 9:16 or landscape 16:9.
For this portrait game prepare at least three clean 9:16 phone images within the
stricter 3 MB phone limit; provide tablet images separately if claiming tablet
presentation. Check Console validation at upload. [Listing guide](https://www.rustore.ru/help/developers/publishing-and-verifying-apps/app-publication),
[screenshot upload limits](https://www.rustore.ru/help/work-with-rustore-api/api-upload-publication-app/apk-screens-upload).

The current Unity license does not allow removal of the Unity splash, and the
owner reported no eligible entitlement. Keep it, or supply an eligible license
for the pinned environment. No bypass is part of launch preparation.
[Unity 2022.3 splash settings](https://docs.unity3d.com/2022.3/Documentation/Manual/class-PlayerSettingsSplashScreen.html).

## Execution order and release decision

1. Owner completes Console/publisher/products, host/domain, signing,
   VK/Yandex registration, factual legal/support materials and traffic/support
   decisions. Engineering continues isolated final-source regression meanwhile.
2. Close reproducible app/backend defects without changing approved art/rules;
   retain failed evidence and rerun the affected and required regression suites.
3. Deploy isolated staging, provision disposable accounts and actual providers,
   then run ordinary configured Android workflows, operational load/fault/restore
   rehearsals and complete physical-device/performance/campaign gaps.
4. Freeze exact app/backend/config/worker/schema versions, publish bounded test
   results and unresolved items, and obtain an explicit go/no-go decision.
   Activate no real payments or public social surface from booleans alone.
5. Submit the correctly signed release and truthful metadata, monitor moderation
   questions and release operations. RuStore currently states moderation may
   take up to six days and can restart after requested information arrives;
   a two-to-three-day preparation target is not a guaranteed public launch date.
   [Current moderation timing](https://www.rustore.ru/developer/en/blog/moderation-in-rustore-requirements-timelines-and-review-stages).

The minimum useful non-secret handoff is: **real package, Console ID, six actual
SKU/coin/RUB mappings, payment scheme, staging/production HTTPS origins,
notification URLs, public signing fingerprint, VK client ID/callback, rewarded
unit ID/privacy version, legal/support URLs, audience/regions and named
operations/moderation owners**. Store private credentials directly in the
owner's secret manager and give the release process references rather than key
contents.

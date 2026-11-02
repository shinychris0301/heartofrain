# 123 - Team chat cold entry order

30 October 2026. Scope: the separate `com.heartoftherain.stagingreview` app, Unity 2022.3.62f3, the staging API, and two realme RMX3938 Android 16 phones. The ordinary game package and production service were not changed.

## Finding

On a fresh process, Teams previously read owner saved lives and saved mail before the team directory, team detail, and chat. Those independent requests prolonged the visible Loading state even for a player whose immediate intent was chat. The earlier cached-chat change helped return visits but could not help a process with no in-memory chat history.

## Change

`OnlineTeamsPage82.Refresh` now requests the team directory, detail, and messages first for the Chat route. Team life help, owner saved lives, and owner saved mail are fetched afterward. Dedicated saved-life and saved-mail pages retain their direct owner reads. A player without a team still fetches both owner entitlements after the directory request. An offline team-directory read stops the remaining serial requests; no mutation is issued by the order change.

## Verification

- The pinned Unity Editor suite passed: 76,397 checks, 44 cases, 285 localized layouts, zero errors, zero HTTP requests. It asserts the cold member request order, no-team saved-entitlement preservation, and the first-read offline short circuit. [Native report](../../Verification/Evidence/Review123/Native/TeamsChatHelp110.json).
- The isolated staging APK built with zero errors and two reported warnings, restored project settings, and used the same staging configuration hash as the previous two-phone build. It was installed with `adb install -r` on both phones. [Build receipt](../../Verification/Evidence/Review123/Android/ColdEntry_Build.json).
- On phone 1 after process restart, [Loading was visible before team data arrived](../../Verification/Evidence/Review123/Android/Phone1_ColdChat_3.png); then [chat history and Message appeared while other controls were still refreshing](../../Verification/Evidence/Review123/Android/Phone1_ColdChat_4.png). [The later ready state](../../Verification/Evidence/Review123/Android/Phone1_ColdChat_Ready.png) restored the life-help and team controls.
- Phone 2 also [showed history while life-help was still refreshing](../../Verification/Evidence/Review123/Android/Phone2_ColdChat.png), then [opened the empty Mail page](../../Verification/Evidence/Review123/Android/Phone2_MailAfterColdChat.png). The prior staging build confirmed cross-phone message delivery; a new cross-phone send was not completed in this build's cold-entry pass.

## Remaining limit

The first Teams visit still has a visible Loading interval until team identity and messages return. These ADB screenshots are observational; their timings include app navigation and capture overhead and do not establish a controlled before/after latency number. Removing that initial interval would require background prefetch from Home or a private persisted cache, with account-owner isolation, expiry, and offline handling. The backend remains staging with `productionEnabled=false`; this is not production-scale or Match Villains latency acceptance.

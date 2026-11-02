# 122 - Team chat responsiveness and two-phone staging check

The later cold-entry request-order improvement and its remaining first-visit limit are recorded in [123_TEAM_CHAT_COLD_ENTRY_REVIEW.md](123_TEAM_CHAT_COLD_ENTRY_REVIEW.md).

30 October 2026. This check used the separate `com.heartoftherain.stagingreview` Android package on two realme RMX3938 Android 16 phones and the staging backend at `api.novamind-it.ru`. It did not exercise production accounts or purchases.

## Finding and change

The Teams page serialized several unrelated reads and marked the entire page busy during them. On a return visit, the last verified chat messages were already in the session, yet the UI still showed Loading and disabled Message. The full-screen Teams backdrop also covered the scrolling message layer; that earlier rendering defect and message timestamp overlap were corrected during this two-phone pass.

The client now keeps cached chat visible while background reads run, permits opening and editing the composer during a replaceable GET, and lets a foreground Send cancel that GET before submitting its durable message command. The cancellation path refuses to interrupt a write. A successful send refreshes chat directly instead of restarting the full serialized Teams refresh. Account changes still clear the private session cache.

## Verified

- [Phone 1 cached reopen](../../Verification/Evidence/Review121/Android/Phone1_CachedReopen.png): messages appeared on return to Teams while unrelated controls were still refreshing; Message was enabled and no Loading notice covered chat.
- [Phone 1 composer](../../Verification/Evidence/Review121/Android/Phone1_CachedCompose.png) opened with the Android keyboard. The draft survived keyboard dismissal and [Send became enabled](../../Verification/Evidence/Review121/Android/Phone1_CachedDraft.png).
- The sent `TeamsQACacheR` message was [acknowledged on phone 1](../../Verification/Evidence/Review121/Android/Phone1_CacheSendAck.png) and [received on phone 2](../../Verification/Evidence/Review121/Android/Phone2_CacheSendReceived.png) without reopening the app. A second message, `TeamsQAReadPriority`, was acknowledged on phone 1 after opening the composer during another refresh. Exact transport preemption timing was checked in the scripted Unity test; the Android capture alone does not prove the GET was still in flight at the instant of Send.
- The prior two-phone pass also confirmed team creation/join, two-member roster, one life-help donation with no donor life deduction, duplicate-help lockout, cross-device chat, leave/rejoin, Mail empty state, Invite/Share UI, and empty ranking state. Direct invitations remain disabled by the owner's explicit decision.
- Pinned Unity 2022.3.62f3 native Editor suite: `PASS_NATIVE_TEAMS_CHAT_HELP110`, 76,388 checks, 43 cases, 285 layouts, zero errors and zero HTTP requests. It includes read-preemption and durable-write-protection checks. [Report](../../Verification/Evidence/Review121/Native/TeamsChatHelp110.json).
- Isolated Android staging build: `PASS_ANDROID_STAGING104_BUILD`, zero errors, two reported warnings, settings restored, same staging configuration hash as the earlier two-phone APK. Both phones accepted the update with `adb install -r`. [Build receipt](../../Verification/Evidence/Review121/Android/ChatResponsive_Build.json).

## Remaining limits

The first entry after process start still has no in-memory chat cache. The page visibly loads while it obtains Teams and chat data; this was seen on both phones. Eliminating that wait needs a separately reviewed prefetch/order change or a private persisted cache with owner isolation and expiry. A network outage must retain an honest offline/retry state rather than imply message delivery. This pass did not benchmark first-entry latency against a fresh Match Villains session or validate production-scale concurrency.

Team reward issue/claim, report/block/moderation, leadership transfer, and long-session recovery still need deployed-service tests. The VPS remains staging with `productionEnabled=false`.

# 121 — Two-phone Teams staging review

This historical checkpoint is superseded by [122_TEAM_CHAT_RESPONSIVENESS_REVIEW.md](122_TEAM_CHAT_RESPONSIVENESS_REVIEW.md), which records the later two-phone message delivery and cached-chat result.

30 October 2026. Scope: two connected realme RMX3938 Android 16 phones, the separate `com.heartoftherain.stagingreview` development package, and the staging API at `api.novamind-it.ru`. The ordinary installed game and production backend were not changed by this test. The phones use separate managed guest identities. No production purchases, ad grants, or real user accounts were involved.

## Confirmed on the two phones

1. Phone 1 created `QAStaging1030`; phone 2 found and joined it. Both displayed a two-member roster after reopening the page.
2. Phone 1 made a five-life help request. Phone 2 gave one help, then displayed the help action as already sent. Both views showed 1/5 received; phone 2 retained 5/5 lives. [Owner view](../../Verification/Evidence/Review121/Android/Phone1_AfterHelp.png), [donor view](../../Verification/Evidence/Review121/Android/Phone2_AfterHelp.png).
3. The Android full-screen keyboard now leaves the typed chat draft in the composer when its OK button closes the keyboard; the Send button becomes enabled. [Composer capture](../../Verification/Evidence/Review121/Android/Phone2_Composer_AfterKeyboardOK.png).
4. Team Detail showed the two-member roster, and Invite opened its modal. Direct invitations remain disabled under the owner's explicit unapproved-rules decision. Team mail's empty state rendered. These are page observations, not proof of invitation or reward delivery.

## Current defect and correction

Both phones later remained on Teams `Loading` despite the owner confirming `healthz` and database-writing `readyz` responses from the phone browser. The original Teams refresh serially continued through independent reads after a network failure; a stalled UnityWebRequest callback could leave the session busy indefinitely. The client now stops a serialized Teams refresh on an unreachable service, and the visible page cancels an unfinished read after 20 seconds, marks it offline, and exposes retry. Background life polling also stops after an unreachable first read. Writes are not cancelled by this read watchdog.

The actual pinned Unity 2022.3.62f3 Editor suite passed with 76,304 checks, 41 cases, 285 layouts, zero HTTP requests, including the new failed-first-read and stalled-read cases. Focused backend transaction tests passed 107/107. These are not a substitute for two-phone delivery or release acceptance.

## Still to verify

- A newly sent chat message appearing on both devices. The second phone's draft cleared after a send attempt, but the later server read stalled, so delivery cannot yet be claimed.
- The revised offline/retry state on the new Android APK, followed by recovery and cross-device chat receipt.
- Team ranking, mail reward issue/claim, invitation policy and share behavior, leadership transfer, leave/rejoin, report/block/moderation, and long-session/reconnect behavior in the deployed service. Some of these require explicit configured test fixtures or approved policy.
- Source parity between the staged VPS service and current repository, service logs for failed social reads, and release infrastructure/credential prerequisites.

All phone captures are real Android screenshots. Synthetic Editor fixtures are explicitly labelled separately.

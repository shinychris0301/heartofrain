# Review 115: Leaderboard R3 and page-design review

Status: implemented and verified in Unity Editor and a disposable local backend; physical-device and hosted-service acceptance remain open. See `Verification/Evidence/Review115/Comparison.html` for supplied designs beside selected Editor captures and `AggregateTestSummary115.md` for exact test reports and source epoch.

## Approved behavior

The owner approved Leaderboard R3 but removed its country-selection option, retaining My region only for players who already have a saved region. World is always available. No region is guessed from IP or device and no region is changed by opening this page. Other Teams region flows are not removed.

Players, Friends and Teams use the blue, cream and gold presentation, with top-three medal treatment, bounded names and controls, and authoritative ranks. Tied entries beyond the three podium positions retain their actual ranks in the list; own player/team rows use server-provided ranking instead of fabricated placement. Current player portrait/frame is local; peer portraits use the neutral fallback until the service publishes verified avatar data. Demo content remains explicitly identified as demo.

Friend name or exact-ID search, Add/Accept, request and blocked lists, and existing profile actions use service data. Search returns active, visible, opted-in, unblocked players. Searches alone never send invitations or friend requests. A potentially unknown request response stays protected by the existing recovery journal; Check, Retry and a warned Forget option are available. The previously unapproved direct team-invitation policy remains disabled.

The backend adds paginated authoritative rank and relationship data and opaque actor/query-bound search cursors. Schema 15 and a stopped, owner-bound staging upgrade and recovery checks were added; no deployed database was migrated. Existing ranking clients and privacy choices are preserved. Tests used disposable local SQLite and no hosted provider.

## Other page comparisons and fixes

The owner also requested a broader check. We reviewed available package references and prior evidence for Home, Profile, Daily Gift, Wellworks, Rain Cup, Shop, settings and gameplay-related screens, and compared Teams Mail, Invite and Leave against their package references. Historical captures and synthetic fixtures are limited evidence, not a current device-wide audit. Three confirmed discrepancies were adjusted: Mail's envelope, close control and reward cards; Invite's close control, subtitle, invite buttons and footer; and the Leave confirmation close control. No unrelated feature policy or reward behavior was changed.

The work changed Leaderboard and OnlineSocial runtime/layout/session files, introduced LeaderboardRefresh package data and verification components, and adjusted `TeamsMailLayout111.cs`, `TeamsInvitesLayout112.cs`, and `TeamsLifecycleLayout113.cs`. Backend changes cover friend search, leaderboard records and related schema/deletion/upgrade tests. `SourceAudit115_Review113.json` contains detailed source paths and attribution context. Original Unity artwork, existing metadata and GUIDs were preserved in the recorded audit. The shared workspace also contained independent Review116 edits; the combined final test epoch does not claim ownership of them.

## Verification and remaining work

155 backend tests passed with unchanged 126 inputs. Unity 2022.3.62f3 Editor passed 110 Leaderboard cases/12,199 checks; a real Unity-to-local-backend loopback passed 50 checks; regional and affected Teams Mail, Invite and Leave suites also passed. All nine final Unity invocations used the same recorded 5,884-input epoch. These are test fixtures and a local service, not production or device verification. Failed earlier epochs remain in evidence.

No current APK was built or installed for this review, and no current physical-device or live hosted-service acceptance was performed. Historical actual-device evidence reported a brief startup blank flash; it has not been verified or fixed here. A separate Review116 safe-area assertion failed once and passed twice unchanged; treat it as an unresolved intermittent concern, not a confirmed fix. A Starlette TestClient/httpx deprecation warning remains. The approved design must still be checked on current phone/tablet builds, including fonts, touch targets, all relevant online/offline states and scrolling. Production hosting/configuration and the separate direct-invitation policy remain open.

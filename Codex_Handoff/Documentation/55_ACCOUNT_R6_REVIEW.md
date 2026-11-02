# Settings > Save Progress - Account Design R6

23 October 2026. Source checkpoint 55. [Native evidence gallery](../../Verification/Evidence/AccountR6/Comparison.html).

The main Settings menu now has the supplied green **Save Progress** button below Music/Sound/Hints and before Inventory. Guests open the save/link view; a service-reported linked account opens its account/sync status. Close, Not now, Continue, Keep playing and Back return to the same Settings instance. Closing Settings still returns Home, and the Home avatar still opens Profile.

## Integration

- `AppSettingsLayout.cs` adds the button, status line and scrolling content space in the existing portrait and wide layouts. Existing Settings artwork, preferences, destinations and fixed legal footer remain in place.
- `AppSettingsPage.cs` handles the action before generic page navigation, suspends Settings drawing/input, and restores its scroll and Save Progress focus. A dismissal-frame guard prevents one Back press from closing both layers. A resize while the modal is open reflows Settings on return.
- `AppSettingsSession.cs` carries only a presentation status key. Account actions never write campaign, inventory, wallet or appearance data.
- New `AccountDesign` assets, modal, localization and `IAccountService` boundary provide the native view. The existing dynamic-TTF/UGUI text workflow is retained; this does not migrate the project to TMP. Text wraps/scrolls rather than shrinking body copy below 12 logical pixels. Header, close button and footer stay outside the body mask.

The ZIP contains assets and an HTML simulation, not Unity account source or an authentication implementation. Archive CRC passes, and all 13 unitypackage assets and metadata match UnityPatch. Four unmatched originals are imported: AccountChrome, clean Close, Google and Apple marks. Nine matching artwork/font sources reuse existing project files and GUIDs; ReviewAssets do not overwrite Settings. Original metadata and artwork hashes are unchanged. The new shell/primary use the supplied slice borders and component multipliers; the close uses its transparent 50.6-pixel child within a 46-pixel target. Current chosen avatar, frame, banner, name, level and local player ID are read from the app.

## Account state and backend boundary

`LocalAccountService` verifies the existing profile through its repository before saying it is saved on this device. Anonymous reward-service authentication is not treated as linked identity or a cloud save. Connectivity determines the offline guest view. A failed local read produces an unavailable status rather than a false save confirmation.

`IAccountService` supplies current identity and sync state on each opening and after a provider completion. Linked pending/failed sync stays distinct from confirmed cloud saved. The latter requires a linked account, Synced state and a valid service-confirmed timestamp; the view shows that UTC time, never a fabricated permanent "Just now". Duplicate linking actions are blocked; cancellation is quiet; failure retains the local journey; stale callbacks cannot replace a closed/reopened dialog.

There is currently no Google/Apple SDK or linked cloud-save backend. The default provider action is disabled with a localized explanation; there is no simulated successful sign-in in the shipping UI. The existing guest identity and progress are retained. Provider linking, cloud upload/download, conflict restoration, switching/unlinking and deletion remain service integration work. The broader prototype handoff is reference material, not a request to silently implement those flows. The account's browser demo levels, IDs, flags and times are not used as production state.

## Verification

Pinned Unity 2022.3.62f3 compilation and Play Mode pass **939 account checks**, with **34 cases and 65 native captures**:

- 30 combinations: en/es/fr/de/ru at 393x852, 320x480, 768x1024, 900x2000, 320x568 and 844x390. The wide case is an Editor layout check; portrait-only build policy is unchanged.
- Four additional portrait views: linked/synced, pending, failed and offline. Linked/provider callbacks are explicit Editor service fixtures, not real authentication or cloud operations.
- Real Settings routing, preference retention, scroll/focus return, foreground UGUI raycasts, blocked underlying actions, compact-body scrolling with fixed footer, Profile routing, duplicate/cancel/error/late callbacks, invalid confirmation timestamps, and unchanged isolated campaign/appearance snapshots.
- Source-size/slice checks, readable copy, text bounds, rendered title characters, Unicode availability strings and close-button safe-area bounds. Visual review corrected title truncation and an oversized scrollbar thumb; the final test detects both regressions.

All **533 existing native Editor checks** pass after the final source changes. Sixteen selected final captures are inspected and hashed in `Visual_Review.json`; all 65 capture hashes are retained in `Source_SHA256.json`. Tests use isolated campaign, appearance and preference stores. Historical global general-check evidence is restored after its fresh report is copied into this checkpoint.

Run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File Verification/Run-AccountR6.ps1` to generate fresh native reports. The runner prepares asset bindings, runs native UI cases and existing checks. `Verification/Tools/collect_results.py` validates this frozen reviewed checkpoint with the project Python environment. A new run creates new isolated IDs/captures; review those frames and refresh the source/capture and inspected-frame manifests before recording a new reviewed checkpoint. Collection intentionally rejects changed inputs or captures.

No APK is rebuilt or installed in this step; the last recorded deployment remains checkpoint 54. Android/iOS devices, notches, hardware Back/touch/clipboard, provider SDKs, memory/compression and production cloud recovery are not certified by these Editor captures. The supplied portrait remains at its existing source resolution. No gameplay rules, economy services, SDK/engine version or existing asset metadata are changed.

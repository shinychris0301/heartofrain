# Local attempt, progression and economy event audit

21 October 2026. Next defined engineering step after the approved Rain Cup practice review: the local layer of backlog ENG-09. This is a native-tested source checkpoint, not a new Android release. The preceding Rain Cup APK and its gallery retain their original build identity and device scope.

## Behavior

`ProfileEventFeed` projects typed, version-one events from durable attempt, tool-command, reward and Cup receipts. `PlayerProfileHost.Events` exposes it beside the existing profile service. Capture is explicit. Nothing calls it from a gameplay frame, animation callback, Home timer or background sender. Existing mutations, life rules, reward quantities, board mechanics, artwork and UI are unchanged.

The source receipts themselves serve as the recoverable event outbox. A pre-commit failure produces no event; a committed transaction whose response was lost produces its event on the next capture. Stable event IDs prevent retries, repeated win settlement, repeated claims or recreated consumers from representing another credit. There is no separate telemetry write that can succeed independently of a gameplay transaction. Existing saves need no schema field, rewrite or migration.

The thirteen kinds are attempt reserved/started/cancelled/won/lost/interrupted, tool spent, level completed, reward granted, Cup joined/point/finished/claimed. Starting items are debited only by the started event. Tools use persisted commands. A first clear has one progression event and one reward event; a replay has neither. A loss or initialized interruption debits one life. Cancellation before initialization has no debit. Cup point and claim lifecycle events do not credit the prize again; its reward receipt supplies the single credit.

Events use signed deltas for twelve quantities: coins, stars, lives, first clears, four starting-item stocks and four tools. Snapshot capture validates event shape, receipt coherence, first-clear progression and unique IDs. It derives an explicit opening balance and checks that opening plus receipt deltas matches the current saved balances. Existing progress without historical receipts is an opening balance, not fabricated gameplay or income. This arithmetic reconciliation cannot establish the provenance of historical or unjournaled changes; it is not an authoritative wallet or anti-cheat system.

Events contain hashed stream, receipt and aggregate identifiers, bounded categories, level/rank/point values and numeric deltas. They omit raw player/attempt/command IDs, arbitrary receipt-source strings, board snapshots, device IDs, names, credentials and payment data. These are still linkable, pseudonymous local records; they are not claimed to be anonymous. Existing receipts do not provide trustworthy event timestamps or a total order across journals, so neither is invented. Archive enumeration is not an event chronology.

## Explicit development delivery

`LocalProfileEventArchive` exists only in Editor/development builds. An explicitly invoked diagnostic consumer can flush a bounded batch:

```csharp
var result = new LocalProfileEventArchive(diagnosticDirectory)
    .Flush(profileHost.Events, maximum: 100);
```

Each event is flushed to a temporary file and atomically renamed to its stable filename inside its hashed stream directory. A stream lock rejects concurrent writers. A replay verifies existing content and writes only missing events. A crash before rename leaves the source receipt available for retry; a crash after rename is deduplicated when the archive is reopened. Matching IDs with different content, corrupt records and archive entries missing from recovered profile history stop delivery for investigation. Nothing deletes or silently rewrites the contradictory record, resets the profile or changes the wallet. Different player profiles have separate streams. This provides idempotent local materialization, not exactly-once network delivery.

Delivery scans retained receipts and existing entries; the batch limit bounds new writes, not the full scan. Run it outside gameplay frames. The existing profile journal and size limits remain; long-lived archival/compaction is not implemented. Atomic rename plus file flush is tested with injected interruptions, not certified against physical power loss. Existing profile-backup rollback limitations remain visible; an archive disagreement detects that situation but cannot recover a missing reward transaction.

No analytics SDK, endpoint, account binding, consent prompt, privacy policy, upload, remote acknowledgement or production sender is added. Production delivery requires those decisions and an authenticated adapter with server-side deduplication. A future event schema must version its ID namespace and delivery storage; changing a historical payload under the same identity is deliberately rejected.

## Changed files and verification

Runtime additions are `Unity/Assets/HeartOfTheRain/App/Profile/Runtime/ProfileEventFeed.cs` and `LocalProfileEventArchive.cs`, with new metadata. The sole preceding player-file modification is `PlayerProfileHost.cs`, which creates the feed without capturing or delivering it automatically. Existing asset metadata is preserved.

Native suites are `Unity/Assets/HeartOfTheRain/Verification/Editor/ProfileEventVerification.cs` and `ProfileEventPlayVerification.cs`, with new metadata. `Verification/Run-UnityVerification.ps1` adds their entry points. `Verification/Run-ProfileEvents.ps1` runs them and existing compatibility suites while restoring historical component reports. `Verification/Tools/collect_profile_event_results.py` freezes all Unity assets/metadata, verifies report freshness and process exits, checks the narrow player diff and confirms that the preceding APK has not changed. The general collector selects this source checkpoint first; `Verification/Evidence/Native_Source_Checkpoint.json` exposes it separately from the unchanged Android summary and its earlier APK scope.

Repeat with `powershell -NoProfile -ExecutionPolicy Bypass -File Verification/Run-ProfileEvents.ps1`. Evidence is `Verification/Evidence/ProfileEvents`; `Verification_Summary.json` records the final native outcome. The source freeze covers all Unity assets, including Editor verification code. The static integrity report is separate from actual native Unity execution.

Final result: all **nine native suites pass, with 35,491 custom assertions/checks**. The new audit suite passes 478 checks; connected audit Play Mode passes 13 checks over 76 projected live-fixture events. Fresh compatibility passes comprise profile transactions (10,099), Rain Cup checks (13,227), connected Cup (34), connected Daily Gift (51), Wellworks checks (11,046), connected Wellworks (13) and general project checks (530). These counts are assertions, not independent natural-play scenarios. The audit Play fixture's own 34 setup/integration checks are reported separately and are not added again to that total.

All **4,453 Unity asset/metadata files** match the source freeze after execution. Of **4,319 player inputs**, 4,314 match the preceding Rain Cup checkpoint; one existing runtime file changes and four inputs are added (two scripts and their metadata). The four additional Editor inputs are the two native suites and their metadata. Static GUID/resource/reference/art integrity passes with no unexpected original changes. The APK remains SHA-256 `c9e3928c5ae91aacaa047374550bf1f2ac532ab81c3e8039d0e52b554c1fc018`; no device process or preservation claim is newly inferred from that file hash.

The audit suite covers old saves, lifecycle immutability, replay protection, initialization cancellation, one-loss interruption, all fifty first clears, two Daily Gift cycles, five Wellworks milestones, Cup scoring/prize credit, bounded replay, source/delivery failures before and after commit, lock contention, corruption, profile rollback, stream isolation, malformed receipts, schema rejection and defensive copies. Connected Play Mode reuses the isolated Rain Cup fixture with seeded test Axe stock on authored level 11. It checks the live host's event feed after failed win-save retry beyond the Cup deadline, M68-to-Home presentation and uncertain prize-claim recovery. These staged controls do not establish natural-play balance.

No new APK build/install or Android, screenshot, FPS, long-session or physical-device certification belongs to this checkpoint. Earlier device reports retain their own APKs. Life regeneration, exact board resume, trusted services, account/cloud recovery and the remaining gameplay performance work are unchanged and remain open.

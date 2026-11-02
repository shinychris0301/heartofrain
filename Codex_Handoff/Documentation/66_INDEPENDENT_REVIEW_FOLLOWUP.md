# Review of Claude's corrections and checkpoint consolidation

23 October 2026 (New York). Read doc 65, particularly **Corrections applied**, and re-read its listed runtime/layout/text, probe and Editor/review code before modifying those files. This follow-up preserves the reviewing workstream's corrections and consolidates checkpoints 55–64, including the previously untracked root `Resources/` folder and its metadata.

Confirmed in source: save-error dialogs hide the Home chapter backdrop; disabled Daily Gift Claim leaves its hit image transparent; life cues are flushed by active attempts and requeued across binding changes; life expiry uses the host's refresh gates; loading art is asynchronous at pre-level and released on close/handoff; loading dots use a nested canvas; loading Escape is consumed before pre-level handles it; offline Account copy discloses local-only saving; Unicode name truncation uses text elements; responsive text suites traverse the nested layouts; Home files retain CRLF and narrow diffs. Existing transactions, rewards, level masks, original GUIDs and approved artwork remain intact.

## Additional corrections

- `HomeLevelFlow.ReleaseStartedLaunch` now checks ticket/generation before touching gameplay or the attempt. The newly added recovery path lacked the stale-operation guard present in the other launch callbacks. A native fault-path check invokes an obsolete recovery against a live newer attempt and verifies that neither board nor profile changes.
- Rain Cup join/claim now restore Close focus after both success and reconciliation. Account Retry and synchronous link failure also restore Close; the existing resize/rebuild focus correction is retained.
- `ProfileTransactionVerification` now measures Daily Gift text using the live design fonts, wrapping, minimum sizes and Russian title handling, rather than the legacy helper/bold font. Transaction semantics are unchanged.
- The working tree still contained several labels doc 65 said had been removed. Removed 16 demonstrably unreferenced Account labels, retaining all dynamic provider/service/status and Save Progress keys. **Do not remove Rain Cup's `unlockNote`: the current locked layout actually calls it.** No visible page copy was deleted by this cleanup.

## Clarifications to doc 65

Finding 8 does not need a new artwork decision: the owner explicitly requested the UI Clarity R1 package's higher-resolution panels and undersized check icon earlier in this session. Current `CheckSource.png` matches that supplied package (`66bdf0176736a7d2380b2f2a9f1049f78fd63e2b10e462d3085eccd53e2d64c9`) and retains GUID `14096b28f3585e91995e603135abf96a`. Keep this authorized replacement. Checkpoint 55's older frozen Account hashes describe its earlier source; they are not a current-tree certification and were not re-sealed to hide subsequent changes.

The loading tip is **Rain Seeker kind 11**, not Golden Seeker kind 16. `GameplayLoadingDesign/Data/Loading_Tips.json`, `M46/Runtime/ReviewScenario.Name` and separate atlas mappings agree. The two kinds remain distinct; no power-up rename or mechanic change is needed for this finding.

Doc 57's 22-entry count was its historical scope; the live registry now contains 48 required sprites after later integrations. Likewise, old source manifests and visual summaries must remain labelled by their checkpoint. Claude regenerated several raw reports/captures; older frozen summaries can therefore fail a current-tree hash comparison. The current follow-up is bound separately by `IndependentReview66/Source_SHA256.json`, not by silently rewriting earlier APK/visual claims.

## Fresh verification performed here

Unity 2022.3.62f3:

- Four loading-art close/reopen cycles, including an immediate close/reopen during an outstanding request; all bound sprites/textures remain valid and bindings clear on close. This checks lifecycle behavior, not actual GPU memory freed.
- All seven root resource assets load natively; their 71 serialized GUID references resolve in source. Their `.asset`, `.meta`, folder metadata and root `Resources.meta` are included in the commit.
- Stale committed-start recovery leaves live gameplay and saved state intact; Rain Cup join and offline Account retry retain keyboard/controller focus.
- **534 general checks**, **13,571 profile/transaction/font checks**, and **17 connected gameplay checks** pass. The connected smoke covers natural input, pause/resume, loss and engine-fault release. All profiles are isolated; no owner save or emulator state was changed.

The first expanded probe attempted to add a second disallow-multiple Account modal; that fixture was corrected to reuse the existing component before the passing run. No runtime correction was needed for that fixture error.

Evidence: `Verification/Evidence/IndependentReview66`. Runner: `Verification/Run-IndependentReview66.ps1`. The collector validates these reports and the frozen current source, and marks the installed checkpoint-64 APK as older than the reviewed source. No APK is rebuilt or installed in this follow-up.

## Remaining limits

The RGBA32 reference import/build-guard policy is retained. Compression policy, actual device memory/GPU cost and physical-device validation remain open; preserving clarity does not prove shipping memory suitability. Save-error chrome still loads Daily Gift design assets, as doc 65 explicitly notes. The loading hint preference still reads PlayerPrefs; no settings-store migration, cloud backend or production event service was introduced. This review does not certify every project feature or convert historical device checks into tests of the corrected tree.

Checkpoint90 root-operated evidence tools

No tool runs Unity, builds or device mutations on import. Runtime/asset changes
must finish before native/build execution. All runs use fresh directories;
failed attempts remain retained and are never promoted by the collector.

Run serial native suites (root only, no concurrent Unity):
  .venv\Scripts\python.exe -B Verification/Tools/PageBackdrop90/run_suites.py --tag Set01
The set is Backdrop90, Regional89, Provider89 and Display88. Invocation receipts
bind exact before/after source maps and the pinned Unity2022.3.62f3 process.
run_native.py also accepts an explicit method/report/status/env for a diagnostic
run. Diagnostics do not silently become the accepted four-suite set.

Build both SDK-free internal Android APKs (root only):
  .venv\Scripts\python.exe -B Verification/Tools/PageBackdrop90/run_builds.py --execute
Run check_apks.py afterward for current APK static checks. Both build variants
are internal signed compile artifacts, not store release approval. Settings and
historical fixed reports are restored by the shared approved build machinery.

Phone operation requires HOTR_PHYSICAL_SERIAL supplied privately. Never print
or commit its value. Phone(out, authorize_from=<accepted89 Target.json>,
candidate_apk=<new development APK>) binds the immutable physical87 ->88 ->89
chain and creates a current90 target. This is the fourth allowed update-chain
link. Only root explicitly calls install(), which uses compatible install -r
and rejects an active attempt, changed saves or a configured server profile.
No uninstall, data clear, emulator fallback or automatic touch route exists.

Root visual review:
  from phone_review import Review
  r = Review()
  r.begin(<current90 Builds/.../FrozenSources.json>)
  r.tap(<fresh name>, x, y, <actual overlay type or Home>)
  r.capture(<fresh name>)
  r.key_back(<fresh name>)
  r.finish()
begin uses only HOTR_RunPageBackdrop90=observe. The native observer does not
change model state; actual root-chosen navigation touches are separate. Fresh
observer readiness proves only the named visible overlay, not screenshots,
performance or successful transactions. If a route exposes no visible property,
retain that failed readiness wait and use a separate direct screenshot/root
assessment; never repeat an uncertain touch automatically. finish exports the
actual Observer_Final.json, verifies profile/preferences/progression preservation,
requests an ordinary relaunch and records current-app selected log signatures.
Its eight-second observation wait does not establish startup readiness or SLA.

VisualReview.json fields:
  schemaVersion: 1
  status: REVIEWED_PAGE_BACKDROP90_PHONE
  apkSHA256: actual installed current development SHA256
  sourceManifest: {path,sha256,bytes} for the current source map
  nativeObserver: {path,sha256,bytes} for Observer_Final.json
  scope: honest actual-device UI scope
  ordinaryDataUnchanged: true
  ordinaryDataUnchangedAfterRelaunch: true
  noActiveAttempt: true
  ordinaryBefore/ordinaryAfter/ordinaryAfterRelaunch: repository-relative paths
  cases: [{name,captures:[original PNG paths],passed:true,topBandAbsent:true,
           controlsSafe:true,scope:<root visual assessment>}]
  warnings: [...]
  limitations: [at least one honest remaining limitation]
Required actual-device cases are Home, Journey, Leaderboard, Teams, Shop and
Settings. Additional reviewed modal/page cases are retained. Leaderboard/Teams
scope must explicitly say demo/offline for the unconfigured phone. Online and
first-start coverage is native fixture evidence unless independently tested on
the phone without owner save/progression changes. Screenshot receipts must be
original complete CRC-valid OS PNGs, paired with installed-APK metadata.

Publish only after actual root visual assessment and all proofs exist:
  .venv\Scripts\python.exe -B Verification/Tools/PageBackdrop90/collect_backdrop90.py --publish --native-list Verification/Evidence/PageBackdrop90/NativeRuns.json --builds Verification/Evidence/PageBackdrop90/Builds/<run>/PageBackdrop90_Builds.json --phone Verification/Evidence/PageBackdrop90/Phone/Device01 --visual Verification/Evidence/PageBackdrop90/Phone/Device01/VisualReview.json
Then run collect_backdrop90.py without arguments and collect_results.py. The
new branch verifies current90 only; frozen89 is hash-bound historical evidence.
Backend bytes must remain identical to checkpoint89's accepted448-test source
map. No old source verifier or historical default APK path is re-evaluated.
Every *.py helper in this folder (including root baseline_capture.py) plus the
central collector and imported shared process/build/APK/baseline helpers are
hashed in the published tools manifest. Raw failed runs
stay in the artifact inventory. No live backend/provider, whole-game smoothness
or production readiness is implied by this targeted display repair.

Host-only controls:
  .venv\Scripts\python.exe -B Verification/Tools/PageBackdrop90/test_evidence90.py
These parser/scope/tamper/privacy/PNG tests do not run Unity or a device.

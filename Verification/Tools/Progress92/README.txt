Checkpoint92 root-operated progress renderer verification

These helpers dispatch nothing on import. Only root executes Unity, Android
builds, ADB or UI gestures. Source must be frozen before native/build runs.
All attempts use fresh folders; failed runs remain in the published inventory.
Engine remains Unity2022.3.62f3. No payment/ad SDK, store signing or release claim.

Host-only controls:
  .venv\Scripts\python.exe -B Verification/Tools/Progress92/test_evidence92.py

Read-only preflight before any candidate exists (private HOTR_PHYSICAL_SERIAL):
  from phone import previous_phone_preflight
  previous_phone_preflight()
It binds immutable90 and the accepted fourth owner-phone chain link; requires
that APK installed and an idle ordinary local profile. A newer owner save is
preserved, never reset to the old90 evidence values. Do not print the USB serial.

Fresh matched before frames, explicitly operated by root:
  from baseline import BaselineReview
  b = BaselineReview(); b.begin()
  b.tap(<fresh action name>, x, y, <observed overlay class>, capture=False)
  b.capture('RainCup_Before')
  ... explicit Profile Stats navigation and capture('ProfileStats_Before') ...
  ... explicit Home navigation ...
  b.finish()
Only the unchanged HOTR_RunPageBackdrop90=observe marker is allowed. No new92
target is authorized and the baseline reader refuses installation. The run
records before/after/ordinary-relaunch hashes under Progress92/Baseline90.
The native controlled1/10 comparison is distinct from the owner's actual8/10.

Native suites, serially after source freeze (root only):
  .venv\Scripts\python.exe -B Verification/Tools/Progress92/run_suites.py --tag Set01
The set is Progress92 and Display88 smoke. Fresh --list-name permits retained
diagnostic/failed sets without replacing an earlier native list. Invocation
receipts bind exact source maps, pinned Editor and unchanged90 process selector.
Progress92 requires120 actual-render rows: six families, four GameView sizes,
five fractions; old-aspect/old-Filled GPU controls and only four selected PNGs.
Launch, legacy M66 and connected Teams inventory remain source-only scope.

Both internal development/nondevelopment Android builds (root only):
  .venv\Scripts\python.exe -B Verification/Tools/Progress92/run_builds.py --execute
  .venv\Scripts\python.exe -B Verification/Tools/Progress92/check_apks.py
Shared85 build code restores exact settings/historical fixed reports, archives
old APKs and binds both before/after source maps. SDK-free internal signing is
not production signing. check_apks inspects bytes; it never installs an app.

Authorize/install current candidate only after successful builds (root only):
  from phone import CapturePathPhone
  p = CapturePathPhone(<Progress92/Phone/Device01>,
        authorize_from=<accepted90 Phone/Device01/Target.json>,
        candidate_apk=<new development APK>)
  p.install()
The current92 target is the fifth and final permitted chain link. Same owner,
installed baseline, idle local save and compatible install-r are required.
No emulator fallback, uninstall, data clear or active-attempt abandonment.

Current candidate UI observations:
  from phone_review import Review
  r = Review(); r.begin(<Progress92 Builds/run/FrozenSources.json>)
  r.tap(<fresh name>, x, y, <actual overlay class or Home>, capture=False)
  r.capture(<selected frame name>)
  r.key_back(<fresh name>); r.wait('Home', <action completedUtc>)
  r.finish()
begin has no initial screenshot unless capture_home=True; tap can omit a
screenshot. Select RainCup, Wellworks, Profile Stats and local/demo Teams;
finish adds ordinary-relaunch Home. Save only actual reviewed frames. Observe
no gameplay, help/chat, claim, purchase, rename/save or account-link actions.
The eight-second relaunch wait is an observation interval, not a ready SLA.
The collector requires that finish's FinalMarkerState be empty, its ordinary
launch report show success, and its exported app-PID log/hash independently
contain zero selected error signatures. It requires the fifth installed chain
link, nonempty profile summaries and a fresh observer tied to UI_Actions.
The Home visual case must include Screens/Relaunch_Observed.png. None of these
bounded checks is a whole-app or performance PASS.

Root VisualReview.json contract under Phone/Device01:
  schemaVersion:1, status:REVIEWED_PROGRESS92_PHONE, apkSHA256:<current>
  sourceManifest:{path,sha256,bytes}, nativeObserver:{path,sha256,bytes}
  ordinaryBefore/ordinaryAfter/ordinaryAfterRelaunch:<repository-relative paths>
  ordinaryDataUnchanged:true, ordinaryDataUnchangedAfterRelaunch:true,
  noActiveAttempt:true, scope:<honest device scope>, warnings:[], limitations:[...]
  beforeReferences:[{name:RainCup or Profile, image:{path,sha256,bytes},
    metadata:{path,sha256,bytes}, reviewed:true, matchedOwnerState:true, scope:...}]
  cases:[{name:RainCup/Wellworks/Profile/Teams/Home, captures:[original PNG path],
    passed:true, progressReviewed:true, controlsSafe:true, scope:...}]
Both RainCup and Profile matched before frames are required. Their baseline
profile/preferences/progression must match install-before and current phone
snapshots. Old90 accepted frames may be optional historical references only,
with matchedOwnerState:false. Screenshots require original complete CRC-valid
OS PNGs and paired installed-APK metadata. Native RT crops are labeled native.

Publish after exact proofs and root's actual visual assessment exist:
  .venv\Scripts\python.exe -B Verification/Tools/Progress92/collect_progress92.py --publish --native-list Verification/Evidence/Progress92/NativeRuns.json --builds Verification/Evidence/Progress92/Builds/<run>/Progress92_Builds.json --phone Verification/Evidence/Progress92/Phone/Device01 --visual Verification/Evidence/Progress92/Phone/Device01/VisualReview.json
Then run collect_progress92.py without arguments and collect_results.py. This
new branch verifies current92 only. Immutable90 summary and backend448 input
map are hash-checked without rerunning an old current-tree verifier or backend
suite. All local Python helpers plus imported process/build/APK helpers and the
central collector are bound by source_tools. Previous failures remain retained.
No whole-game smoothness, live provider/social, deployment or store acceptance.

DISPLAY88 ROOT EXECUTION GUIDE

These tools do nothing to a phone or Unity on import. Only the root operator
runs native/device steps. They never relax old Physical87 target guards and do
not overwrite sealed Review86/Physical87 source or reports. A default APK path
is an output, not its permanent identity: each run binds exact source and APK
bytes independently. Keep raw USB serials only in ignored private cache or the
process environment. Do not print them or put them in command-line arguments.

Native Editor execution, after runtime fixes and test sources are stable:

  .venv/Scripts/python.exe -B Verification/Tools/Display88/run_native.py
    --out Verification/Evidence/Display88/Native/<fresh-id>
    --entry HeartOfTheRain.Verification.Display88Verification.Run
    --report Report.json --expected PASS_NATIVE_DISPLAY88
    --output-env HOTR_DISPLAY88_OUT

The new native entry must write to HOTR_DISPLAY88_OUT and exit itself. Use
the actual entry/report/status supplied by its author if different. This runner
requires the pinned2022.3.62f3 Editor, excludes only the exact Hub background
service from its Unity process guard, gives its own process a kill-on-close job,
retains failures and freezes Assets/Packages/ProjectSettings before/after. No
automatic -quit is supplied because coroutine/Play Mode tests need to finish.
It does not claim that RenderTexture captures are full-screen phone evidence.

Internal Android compile, only after root authorizes serial Unity execution:

  .venv/Scripts/python.exe -B Verification/Tools/Display88/run_builds.py --execute

This uses the generic existing SDK-free build helper with a new Display88
evidence root. It builds Development and NonDevelopment serially, archives prior
default APKs, restores every ProjectSettings byte and historical Native report,
and records exact source/APK inputs. No install or production configuration is
performed. Prior helper statuses retain85 names; the88 wrapper describes their
current scope. Do not edit/run historical86 collectors as current-source proof.

Phone operation from a root-owned Python command:

  import os,sys,json
  from pathlib import Path
  root=Path.cwd()
  private=json.loads((root/'.verification-cache/Physical87/PhoneTarget.json').read_text())
  os.environ['HOTR_PHYSICAL_SERIAL']=private['serial']
  sys.path.insert(0,str(root/'Verification/Tools/Display88'))
  from phone import Phone,write
  phone=Phone(root/'Verification/Evidence/Display88/Phone/<fresh-id>',
    authorize_from=root/'Verification/Evidence/Physical87/20261026_e71bc9d09515/Target.json',
    candidate_apk=root/'Unity/Builds/Verification/HeartOfTheRain_Development.apk')
  write(phone.out/'Inventory_Before.json',phone.inventory())

authorize_from explicitly reauthorizes the same owner phone for the current
display repair. It checks physical/model/serial-hash and the prior baseline
installed APK; candidate bytes may differ. It never substitutes an emulator.
Inventory is read-only and allowed while the current attempt is active. It
exports only hashes, revision/balances/progress and active-attempt counts. Nested
development-authority files are hashed but not parsed as player profiles.

If the owner has an active ordinary attempt, STOP the update/fixture workflow.
Do not force-stop, launch a marker, overwrite a save or abandon it to create a
test state. The root operator should inspect the current UI and preserve it.
Managed ServerReview configuration is refused for mutation until a separate
remote-attempt audit exists. When idle:

  phone.install()

This checks idle twice, compares profile/preference hashes across force-stop,
performs only adb install -r, verifies installed candidate SHA256 and preserves
every original saved file. Failure has no uninstall, data-clear or downgrade
fallback. It deliberately does not launch afterward. To reopen later without
reauthorizing:

  phone=Phone(existing_run_directory)

Root launches the ordinary app explicitly, waits for actual Home/readiness,
captures with phone.capture('Ordinary/Home.png'), navigates via actual touches,
and records only app-scoped logs. capture() requires our foreground activity and
an unlocked screen, uses the true OS screencap framebuffer and pairs the PNG
with dimensions/display size/density/current APK hash. It does not alter camera
rects, canvas render mode, resolution, density or system settings. Do not use a
screen-recording or screenshot poll inside performance measurement windows.

DISPLAY ACCEPTANCE MATRIX (retain every failure)

1. Reproduce pre-fix Home and normal gameplay from actual OS720x1600 captures.
   Pair native Screen.width/height/safeArea and each enabled camera's rect,
   pixelRect, depth, clearFlags, targetTexture and cullingMask; canvas/root/mask
   bounds and active scene ownership. The phone historically has a64px upper
   safe inset. Distinguish system-owned bars from an app-owned black strip.
2. Fix must let decorative backgrounds cover the full app framebuffer while
   interactive header, navigation, HUD and controls remain inside safe bounds.
   Gameplay world cannot leak through an uncovered app strip behind Home or
   overlays. Verify old gameplay camera/renderer ownership during transitions.
3. Pinned native tests:720x1600 with64px top inset;720x1600 with asymmetric
   top/bottom insets;720x1280;1080x2400;1080x1920;1536x2048 portrait tablet.
   Check full-screen backdrop corners/edges, safe touch rectangles and board
   camera bounds mathematically. Render pixel tests must retain overlay
   semantics or explicitly isolate/restore camera viewport and canvas state.
4. Actual phone: cold/warm launch, Home, all five bottom destinations, Profile,
   Settings/modal close, PreLevel, immediate loading overlay, ordinary gameplay,
   pause/cancel, Continue/Shop/back and win/celebration/Home. Use audited
   transient fixtures for repeatable destructive states; never ordinary saves.
   Capture true OS images at transitions as well as stable screens to detect
   stale framebuffer leakage. No offscreen-camera artifact is device proof.
5. Background/resume and same-version compatible reinstall must preserve
   ordinary profile/preferences. Keep startup readiness timing separate from
   the existing seven-second recovery observation failure. Guard active attempts
   before every stop/update/fixture. No phone rotation/network/audio changes
   unless root separately snapshots/restores them.
6. Recheck tutorial swipe from actual input because87 failed twice; no passing
   two-tap substitution closes that issue. Retain existing83-100ms native frame
   intervals unless a separate timing fix and same-case measurement improve it.
7. One phone plus Editor geometry does not certify all tablets, OS versions,
   multi-touch,50 manual wins, payments, ads or deployed social/backend systems.

Host-side syntax/help checks are tool preparation only. They are not Unity,
Android or physical test acceptance. These tools require root-run native proof
and visible review before any rendering issue can be marked closed.

CURRENT PHONE REGRESSION / CONTINUATION / TUTORIAL

After explicitly authorizing/installing the current APK and confirming an idle
ordinary account, set HOTR_PHYSICAL_SERIAL privately and run one tool at a time:

  .venv/Scripts/python.exe -B Verification/Tools/Display88/run_phone_checks.py
    --phone Verification/Evidence/Display88/Phone/Device02 --mode regression
  .venv/Scripts/python.exe -B Verification/Tools/Display88/run_phone_checks.py
    --phone Verification/Evidence/Display88/Phone/Device02 --mode no-moves
  .venv/Scripts/python.exe -B Verification/Tools/Display88/run_tutorial.py
    --phone Verification/Evidence/Display88/Phone/Device02
  .venv/Scripts/python.exe -B Verification/Tools/Display88/run_navigation.py
    --phone Verification/Evidence/Display88/Phone/Device02

Each requires a fresh evidence subdirectory and exact current-build/source
binding. Existing outputs are preserved. Regression is accelerated/programmatic
native coverage; NoMoves and tutorial require actual Android input. Tutorial
uses an isolated memory profile and compares ordinary saves before/after and
after relaunch. Failed or uncertain mutations are never retried.
Navigation uses the ordinary idle account and a read-only geometry observer,
captures all five destinations, and compares canonical saves before/after.
Its fresh-readiness predicates and screenshot review do not certify providers,
demo social data or whole-game performance. The initial timestamp bootstrap
failure remains separate from the corrected completed run.

The completed88 regression encountered a stale extra PNG in its persistent
native output folder. Its original host invocation stays FAIL. A separate
read-only supplement may collect the already completed report without rerun:

  .venv/Scripts/python.exe -B Verification/Tools/Display88/recover_regression_collection.py
    --phone Verification/Evidence/Display88/Phone/Device02

That tool accepts only the exact recorded native PASS/current APK/source,
records unchanged remote report bytes, retains the declared output inventory
and twelve representative PNGs, and excludes unlisted/stale images from current
acceptance. It sends no marker/input/stop/launch or installation command.

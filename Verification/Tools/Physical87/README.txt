Physical phone checkpoint87 evidence instructions

checklist_template.json is a planning template, not executed test evidence.
The individual Physical87 run contains the actual results and retained failures.
Tools require HOTR_PHYSICAL_SERIAL and its matching authorized Target.json.
report.py is host-only; --verify does not operate the phone.
interrupt.py retains the original fixed seven-second observation design; its
checkpoint87 failure and separate late follow-up are preserved. Future timing
acceptance must wait for actual recovery/readiness rather than assuming7seconds. checklist_template.json has
20 acceptance rows copied verbatim from Device_Test_Matrix.csv and19 additional
current-feature rows. All statuses start NOT_RUN. Copy the template into a new
physical-phone evidence directory; root records only actual observed results,
source/APK/device binding and exact evidence paths. Do not overwrite historical
Review86 or emulator acceptance.

Select the real authorized USB phone explicitly. Record model, Android/API,
ARM64 ABI, viewport and package/build/signer without collecting unrelated phone
content. Inventory the app's existing save/attempt state before install, stop,
launch or fixture activation. Do not uninstall, clear data, overwrite a save or
abandon an owner's active attempt to manufacture a test state. Failed compatible
replacement installation stops the operation; it has no destructive fallback.

The old qa_android_target.py deliberately allows only emulator-5556/5558.
A new physical wrapper must validate the actual selected phone and its separate
authorization record. Do not spoof an emulator serial, relax the historical
emulator guard, reconnect/restart a protected emulator or reuse sealed QA evidence.
Use one explicit serial on every command. No global phone resolution, density,
clock, network, volume or preference change without preserving/restoring state.
Do not use device-wide logcat, notifications, contacts, photos or other apps as
test evidence when app-scoped data is sufficient.

Development probes are opt-in and must be audited before use. The all50-board
PlayerRegressionSuite is transient and accelerated; it is not human play,
multitouch, ordinary connected startup, live payment/ad acceptance, visual review
or whole-game performance certification. Keep scripted fixture reports separate
from actual touch observations. Do not infer inaccessible memory/GC/GPU counters.
Measure unrecorded timing separately from video. Retain slow samples and failures.
Listen to audio when recording an audio result; source counts alone are not it.

Connected/social tests use disposable synthetic accounts and a separate test
backend only. Never send a message, friend request or report to a real user.
Clipboard/account testing must never serialize clipboard text, recovery codes,
credentials, hashes of secrets or secret-bearing screenshots. Restore controlled
clipboard state in memory when possible; log only safe result metadata.
Payment/ad SDK tests stay blocked until a compatible configured Android SDK
profile, test backend and actual provider configuration exist. No real-money
spend, real banking interaction, live-ad clicks, production activation or account
deletion on an owner identity is implied by the checklist.

Record PASS, FAIL, PARTIAL, NOT_RUN or the precise blocked category per row and
subcase. A single phone cannot certify tablets/all devices. All50 scripted board
runs cannot fill Campaign_Playtest.csv as human wins. Keep externally blocked
Console, signer, legal, hosting, moderation and provider acceptance explicit.

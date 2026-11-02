Root-operated current RuStore SDK compile proof
==============================================

Run only after the current main Unity inputs are held and no Editor is running.
The tools do not modify main Assets/Packages/ProjectSettings or the old81 spike.

From the repository root, prepare a fresh short-path isolated project:

```powershell
Backend/.venv/Scripts/python.exe Verification/Tools/Review86/pay_sdk86.py prepare
```

Use the exact printed Preparation.json path for the one-use serial runner:

```powershell
Backend/.venv/Scripts/python.exe Verification/Tools/Review86/pay_sdk86.py run --preparation .verification-cache/Review86/P86_12345678/Preparation.json
```

The placeholder project suffix must be replaced by the actual printed suffix.
Preparation clones only the three old81 input directories, replaces the current
four payment C# files and their original metadata, and adds the external86 probe.
The adapter SDK branch is compiled via the inherited HOTR_RUSTORE_PAY definition.
The stock official registry pins remain Pay11.1.0/Core10.5.0. Both packages retain
their original Unity6000.0 metadata; a passing Editor experiment does not change
the vendor support declaration or the game's Unity2022.3.62f3 pin.

Each prepared project may execute once. Evidence is a fresh directory at
Verification/Evidence/Review86/SDK/<runId>. Existing success/failure artifacts are
never overwritten; prepare a new project after any source/tool change or failed
run. The runner uses the corrected86 process-image guard (the exact Hub service
is exempt, other/unknown Unity processes block), the shared serial native lock,
and a kill-on-close job for only its own pinned Editor. The default hard deadline
is600seconds; --timeout-seconds accepts60..900. No Hub/foreign process is stopped.

A passing Process.json binds the exact current source/meta copies, main before
and after input manifests, stock package manifests and every packaged file
against the checksum-pinned official cached tarballs. Old81 input bytes must
also remain unchanged. Clone input changes are recorded separately.

Scope is current C# adapter/contracts/coordinator/file-journal compile/API
compatibility only. The probe creates request value objects and an unconfigured
adapter; it never accesses the SDK singleton. No SDK initialization, Android or
native build, full-game SDK integration, SDK checkout, real payment, deployment
or production enablement is established by this experiment.

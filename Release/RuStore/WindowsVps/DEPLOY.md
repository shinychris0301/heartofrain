# Windows VPS staging deployment — `api.novamind-it.ru`

This is the controlled **staging** backend. It supports managed guest identity
and social services. The staging launcher deliberately disables production,
RuStore purchases, payment notifications, VK sign-in, rewarded grants, and
gameplay replay until their separate configuration and acceptance gates pass.
Do not use this staging package as a public store release authority.

The A record for `api.novamind-it.ru` resolves to `178.22.24.247`. The staging
service is running on the Windows VPS as of 30 October 2026. See the checkpoint
below for the exact limits of endpoint verification.

## VPS checkpoint, 30 October 2026

An authenticated RDP audit found Windows Server 2022 Standard with Desktop
Experience. The reviewed 152-file backend source bundle was copied to
`C:\Apps\HeartOfTheRain\Backend` and verified against its per-file SHA-256
manifest. Caddy 2.11.7 and WinSW 2.12.0 were copied to the tool paths below;
their hashes were checked again on the VPS. The official Python 3.14.10 x64
installer hash was checked and Python was installed for all users at
`C:\Program Files\Python314`. A 61-file, hash-verified fixture overlay supplies
Unity and release files needed by cross-project tests. The exact locked
dependencies were installed into `.venv-service` from the machine-wide Python;
the **764-test VPS suite passed with one skip and zero failures** in 716.931
seconds under that service runtime.

The `HOTRStaging` and `HOTRCaddy` WinSW services now run as LocalService. The
API binds only to `127.0.0.1:8751`; Windows Firewall allows Caddy on 80/443
only. The VPS validated normal HTTPS for `/healthz` (`status:ok`,
`productionEnabled:false`) and `/readyz` (`status:ready`). Caddy logged a
successful Let's Encrypt certificate issuance. `/docs`, `/openapi.json`, and
`/internal/v1/test` returned 404 through the proxy. A connected Android phone
reached port 80 over Wi-Fi and received Caddy's HTTP-to-HTTPS redirect.
The owner then opened `https://api.novamind-it.ru/healthz` on that phone; a
captured browser screen showed the exact staging JSON with no certificate
warning visible. The first browser attempt failed before a later successful
reload, so intermittent external reachability still needs investigation. The
development PC's outbound HTTPS request continued to time out.

The backend passed a controlled service restart. The online snapshot
`before-acceptance-20261030` completed with schema version 15, and a separate
non-activating restore drill `restore-drill-20261030` completed. An encrypted
off-VPS copy, reboot persistence test, monitoring,
and real two-account Android test remain open. Payments, VK, ads, and gameplay
verification remain disabled in this staging manifest.

An isolated Android staging client was built from the Unity 2022.3.62f3
project under `.verification-cache/Review104/Candidates/vps_20261030_a`. Its
receipt reports `PASS_ANDROID_STAGING104_BUILD`, zero errors, two build
warnings, restored temporary settings, and APK SHA-256
`D625E1EB41713E0F6641DEC0A379A0903E93E36438C3E437B85F6E3AE6127C77`.
The APK is debug signed as `com.heartoftherain.stagingreview`; it is **not** a
release artifact. It installed beside the original app on a connected realme
Android 16 phone and reached the first-time story, tutorial, Home, Teams and
team-create screens. A QA team named `QAStaging1030` was created through the
phone's managed Teams flow; after force-stopping and relaunching the staging
client, its membership and name were retrieved again. This verifies one
authenticated write and later read, but not two-account social behavior.
The Teams page took roughly 36 seconds to settle after relaunch; latency needs
diagnosis before acceptance. Android displayed a
compatibility warning on first launch; the build's minimum API is 22 and the
device reports 4 KiB memory pages, so a 16 KiB page-mode cause has **not** been
established. APK inspection also shows only `armeabi-v7a` native code, matching
the copied project's Mono/ARMv7 settings; this staging APK therefore does not
cover 64-bit-only devices. The warning's exact trigger remains unverified.
Resolve it, build an ARM64 candidate, and identify the two build warnings before
release acceptance.

The same debug APK was installed into the isolated LDPlayer QA instance for a
second account. Its default Vulkan path crashed in the emulator's
`libvulkan_enc.so`; launching that unchanged APK with Unity's `-force-gles`
argument reached Home and Teams. The second account did **not** authenticate:
its wallet stayed at zero and Teams showed an unavailable/retry state. A direct
`curl` from that emulator connected to TCP 443 but timed out during the TLS
handshake after sending ClientHello. The development PC also timed out, while
the physical phone succeeded. Treat this as an unresolved PC/emulator egress
path issue; do not count LDPlayer as a two-account backend pass.

The staged `caddy.exe` SHA-256 is
`5F93A9BD555F3AAC9D33AF2756BA14B3519D8CCA4FFD55256BDAEAB444C9DB2A`;
the staged `WinSW-x64.exe` SHA-256 is
`05B82D46AD331CC16BDC00DE5C6332C1EF818DF8CEEFCD49C726553209B3A0DA`.
WinSW's older GitHub release did not expose an asset digest through its release
API, so the latter comparison verifies transfer integrity against the local
copy downloaded from the official release, not an independent publisher checksum.

The test fixture overlay `hotr-vps-test-fixtures-20261030-r4.zip` has SHA-256
`71DA5AC0DA94BEA399F0E4EC222C544F1488B5030C07A7721CB3F5A04B9C6075`.
It adds only the approved 50 level JSON files, related Unity/release JSON and
one Windows-safe replay test assertion. The overlay does not enable checkout,
production gameplay verification, or any feature flag. Its 61 files were
verified on the VPS before the 10 affected tests passed.

## Host preparation

Use a patched Windows Server host, Python 3.14.10 x64, the exact
`Backend/requirements.lock`, an official Caddy 2 Windows binary, and an official
stable WinSW 2.x x64 binary. Verify downloaded executables against their publishers'
release information. Open inbound TCP 80 and 443 in the VPS provider firewall
and Windows Firewall. Keep the Python listener on `127.0.0.1:8751`; do not open
8751 externally. Restrict RDP, SSH and WinRM to administrator addresses or a
private management network. Check for an existing IIS or other listener on 80/443
before installing Caddy.

```powershell
Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 80,443,8751 |
  Select-Object LocalAddress,LocalPort,OwningProcess
New-NetFirewallRule -Name 'HOTR-Caddy-HTTPS' -DisplayName 'Heart of the Rain Caddy HTTPS' `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 80,443 `
  -Program 'C:\Tools\Caddy\caddy.exe' -Profile Any
```

Copy the reviewed backend bundle to a **fresh**
`C:\Apps\HeartOfTheRain\Backend` directory. Do not copy a developer `.venv`,
SQLite data, `.env`, signing key, or provider credential. From an elevated
PowerShell session on the VPS:

```powershell
Set-Location 'C:\Apps\HeartOfTheRain\Backend'
& 'C:\Program Files\Python314\python.exe' -m venv .venv-service
& .\.venv-service\Scripts\python.exe -m pip install --disable-pip-version-check -r .\requirements.lock
& .\.venv-service\Scripts\python.exe -m pip check
$env:PYTHONPATH = (Resolve-Path .\tests).Path
& .\.venv-service\Scripts\python.exe -B -m unittest discover -s tests -t . -q
```

On this host, install Python from the official x64 installer before running these
commands. The Python 3.14.10 installer is
`https://www.python.org/ftp/python/3.14.10/python-3.14.10-amd64.exe`; verify its
SHA-256 is `92480239264744fe0386a1bd8275786fefa126e3129e56a68e22b52c73329965`
and install for all users with pip at `C:\Program Files\Python314`. Run
`& 'C:\Program Files\Python314\python.exe' --version` and require
`Python 3.14.10`. The locked dependencies and full 764-test suite passed on
the VPS's machine-wide Python. The earlier per-user `.venv` was used only for
deployment testing; the installed service uses `.venv-service`.

Create a private fixed-disk parent with access only for Administrators, SYSTEM,
and the service account. Review the resulting ACL before starting services:

```powershell
$hostRoot = 'C:\ProgramData\HeartOfTheRain'
New-Item -ItemType Directory -Path $hostRoot -ErrorAction Stop
icacls.exe $hostRoot /inheritance:r
icacls.exe $hostRoot /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-19:(OI)(CI)M'
icacls.exe $hostRoot
icacls.exe 'C:\Apps\HeartOfTheRain\Backend' /grant:r '*S-1-5-19:(OI)(CI)RX'
```

`S-1-5-19` is LocalService. The two generated service definitions run as that
account, not LocalSystem. If the host has a different ACL policy, set equivalent
rights before continuing. Put `caddy.exe` at `C:\Tools\Caddy\caddy.exe` and
grant LocalService read/execute access to it. Keep the WinSW binary in a private
administrator-controlled tool directory until copied below.

## Generate the configuration

The generator refuses existing service or data roots, rejects source-tree data
paths, emits no credentials, and does not contact the network or install a
service. It uses the domain and stable review identity approved for this VPS:

```powershell
Set-Location 'C:\Apps\HeartOfTheRain\Backend'
& .\.venv-service\Scripts\python.exe -B -m hotr_backend.windows_vps_setup `
  --backend-root 'C:\Apps\HeartOfTheRain\Backend' `
  --python-exe 'C:\Apps\HeartOfTheRain\Backend\.venv-service\Scripts\python.exe' `
  --caddy-exe 'C:\Tools\Caddy\caddy.exe' `
  --output-root 'C:\ProgramData\HeartOfTheRain\services' `
  --data-root 'C:\ProgramData\HeartOfTheRain\staging-data'
```

The generated `staging-manifest.json` is private operator configuration;
`staging-build.json` contains only public Android review settings. Do not place
either inside Unity `Assets` or a web root. The data root must remain absent or
empty until the first `initialize` operation. Keep the generated identity scope,
deployment ID and data root stable across restarts and app review upgrades.

## Initialize and install services

Review the generated files and ACLs first. The backend initializer creates an
owned marker and disabled provider policy; the first start creates the database.
Never run `initialize` again against a Ready authority.

```powershell
$manifest = 'C:\ProgramData\HeartOfTheRain\services\staging-manifest.json'
$python = 'C:\Apps\HeartOfTheRain\Backend\.venv-service\Scripts\python.exe'
& $python -B -m hotr_backend.staging105 initialize --manifest $manifest
& $python -B -m hotr_backend.staging105 preflight --manifest $manifest
icacls.exe 'C:\ProgramData\HeartOfTheRain\staging-data' /grant:r '*S-1-5-19:(OI)(CI)M' /T
icacls.exe 'C:\ProgramData\HeartOfTheRain\staging-data\.hotr-staging105-owner.json'
& 'C:\Tools\Caddy\caddy.exe' validate --config 'C:\ProgramData\HeartOfTheRain\services\Caddyfile'
Copy-Item 'C:\Tools\WinSW\WinSW-x64.exe' 'C:\ProgramData\HeartOfTheRain\services\HOTRStaging.exe'
Copy-Item 'C:\Tools\WinSW\WinSW-x64.exe' 'C:\ProgramData\HeartOfTheRain\services\HOTRCaddy.exe'
Set-Location 'C:\ProgramData\HeartOfTheRain\services'
& .\HOTRStaging.exe install
& .\HOTRCaddy.exe install
$accounts = Get-CimInstance Win32_Service |
  Where-Object Name -in 'HOTRStaging','HOTRCaddy'
if ($accounts.Count -ne 2 -or @($accounts | Where-Object StartName -ne 'NT AUTHORITY\LocalService').Count -ne 0) {
  throw 'Service account mismatch; do not start services'
}
Start-Service HOTRStaging
Invoke-RestMethod 'http://127.0.0.1:8751/healthz'
Invoke-RestMethod 'http://127.0.0.1:8751/readyz'
Start-Service HOTRCaddy
```

On Windows, Python's `mkdir(mode=0o700)` restricts the new data directory to
the creating user and administrators. The parent directory's LocalService ACL
is therefore insufficient; explicitly grant LocalService Modify on the exact
owned data tree **after** initialization and before starting the API. Confirm
the grant succeeded on the ownership marker. Do not grant broad `Users` access
or apply `/T` above the staging data directory.

Check the local results before exposing the proxy. `/healthz` must report
`productionEnabled:false`; `/readyz` must pass the current schema/writer probe.
Then check `https://api.novamind-it.ru/healthz` and `/readyz` from **outside**
the VPS using normal certificate validation. Check that `/internal/v1/...`,
`/docs`, and `/openapi.json` return 404 publicly. Caddy handles automatic public
TLS only after the domain resolves to this host and the ACME validation paths on
80/443 are reachable. Its `caddy-state` directory contains TLS private keys and
must be persistent and backed up appropriately.

## App connection and operational checks

Only after HTTPS and readiness pass, use the matching public
`staging-build.novamind.json` in this directory. Compare it with the generated
`staging-build.json` on the VPS before building. Use the
existing isolated Android staging build flow in
`Release/RuStore/STAGING_BUILD_CONFIGURATION104.txt`. This does **not** alter
the ordinary APK or its offline save. Install the isolated review package and
verify two real devices/accounts: registration, profile, friends, teams, chat,
restart, and recovery. With replay disabled, do not claim server-verified levels
or compatible production progress.

Before exposing real users, configure a service monitor for both `/healthz` and
`/readyz`, test service restart after a VPS reboot, and create an online snapshot:

```powershell
& $python -B -m hotr_backend.staging_ops105 backup --manifest $manifest --name before-acceptance
```

Store an encrypted copy **off this VPS** under the owner's retention policy and
perform the existing restore drill in `STAGING_SERVER_OPERATIONS105.txt`. Do not
copy or publish the live SQLite database or the service root. Review the VPS
physical storage location and the app's actual privacy terms before storing
player data. A public HTTPS URL and green health probe do not verify RuStore
payments, ad completion, VK provider acceptance, or the approved gameplay worker.

## Remaining release gates

The repository's staging launcher intentionally has no production toggle. A
release build needs the real RuStore Console app ID, registered product IDs,
server-side provider credentials, notification network verification, recovery
worker, approved replay bundle, VK application/callback if used, Russian legal
pages, and configured Android acceptance. Keep those credentials only in
restricted server/operator storage. Do not replace the disabled values in this
staging manifest to imply release readiness.

If VK is enabled later, register exactly
`https://api.novamind-it.ru/v1/identity/vk/callback` with the VK application and
set its issued numeric client ID in a separately reviewed private manifest.
Payment notifications need an ingress that verifies the real sender network;
the loopback-only staging proxy does not establish that property.

Operational references: [Caddy Windows service and HTTPS](https://caddyserver.com/docs/running),
[Caddy persistent data directories](https://caddyserver.com/docs/conventions),
[WinSW 2.x installation](https://winsw.github.io/v2/doc/installation/), and
[WinSW 2.x service XML](https://winsw.github.io/v2/doc/xmlConfigFile/).

# 96 — Windows build administrator review

Status: **Administrator handoff ready; Smart App Control gate confirmed. Administrator resolution pending. No policy change is authorized.**

The owner chose administrator review on this PC. Matching Code Integrity records now attribute the Unity6.3 loader failure to **VerifiedAndReputableDesktop**, the Smart App Control enforcement policy. The remaining task is an administrator decision on a supported resolution. Main Unity2022, the isolated Unity6.6 candidate, vendor binaries and existing evidence remain protected.

## Five steps for the administrator

1. Open **Windows Security → App & browser control → Smart App Control settings** and inspect the current status. Record the Windows build and management context. Inspection does not authorize changing any toggle, trust setting or policy.
2. In **Event Viewer → Applications and Services Logs → Microsoft → Windows → CodeIntegrity → Operational**, review enforced-block records **1811** and **1815**, and their linked signature records **1810, 1812, 1814 and 1816**. Confirm the policy, exact file/hash, stock process and ActivityID relationships described below. Preserve the raw records privately.
3. Review the current `NiceIO.dll` **NotSigned** result against the checksum-verified stock installer. Ask Unity about a supported signed/distribution resolution, or identify an already approved compatible build environment. A signed installer does not mean each bundled DLL is signed.
4. Assess options with the PC's security owner. Microsoft documents **no individual-app Smart App Control exception**. No global Off recommendation, policy removal, runtime substitution or vendor-binary change is authorized by this handoff. The current [Microsoft FAQ](https://support.microsoft.com/en-us/windows/security/threat-malware-protection/smart-app-control-frequently-asked-questions) describes Windows-version-dependent settings behavior; do not rely on outdated claims that re-enabling always requires reinstalling Windows.
5. Report the administrator's decision and supported resolution to the owner. Once the relevant environment issue is resolved, engineering will collect a **fresh** stock-loader probe and continue the already approved Android smoke/full-game/device verification. Completing this review alone does not resolve the block or establish a successful build.

## Confirmed technical facts

The official Unity **6000.3.27f1** installer has a verified complete checksum and Valid Unity Technologies Authenticode signature. Normal installation passed to `E:/HeartRainUnity6LTS95/6000.3.27f1`. Installer verification does not establish that every bundled DLL is individually signed or allowed by Windows.

The actual stock `netcorerun` probe on **27 October 2026, 11:48:58–11:49:24 UTC** failed with exit code **1**. Its output explicitly identifies an Application Control block, HRESULT **0x800711C7**, while loading:

```text
E:\HeartRainUnity6LTS95\6000.3.27f1\Editor\Data\Tools\BuildPipeline\NiceIO.dll
```

The file is **40,960 bytes**, flat-file SHA256:

```text
bf1daba5ba1d23c895c2b82922045ba4a0cbfb02e9c9fb615cd29e3c30a7f291
```

The stack includes `Program.MyResolveEventHandler`, `Assembly.LoadFrom` and `PlayerBuildProgramTypeWrapper.Run`. This was the stock Windows frontend with deliberately absent input files, using the Unity6.3 bundled `netcorerun` and matching resolver folders. It was **not** an Android build, and it failed before reaching the intended missing-input exception. The earlier `coreLoaderReady: false` installation field was a layout-assumption guard, distinct from this subsequent real loader block.

Root subsequently collected the existing Code Integrity records without changing settings. Both event **3077** records name the same `NiceIO.dll`, the stock `netcorerun.exe` process and `VerifiedAndReputableDesktop`; their **SHA256 Flat Hash** matches the stock/current file hash above.

| Enforced-block record | UTC, 27 October 2026 | Linked 3089 records | Shared correlation SHA256 prefix |
| --- | --- | --- | --- |
| 1811 | 11:49:04.4831062 | 1810, 1812 | `22f493729672` |
| 1815 | 11:49:05.4553110 | 1814, 1816 | `e041b371cc0c` |

Both block records report requested signing level **2**, validated signing level **1**, status **0xc0e90002**, PolicyID **27555.1000.240208** and PolicyGUID **`{0283ac0f-fff1-49ae-ada1-8a933130cad6}`**. The four linked 3089 records each report **TotalSignatureCount 0**; there are two per ActivityID, associated with the 3033 and 3077 validation records. They must not be reduced to an assumed total of two signature records. Microsoft documents the enforced-block and ActivityID correlation semantics in [Understanding App Control events](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/operations/event-id-explanations).

The current file check reports **NotSigned**, **40,960 bytes**, and the same flat-file SHA256. The OS is **Windows 11 Pro, version 10.0.26300, build 26300**. The separately read `VerifiedAndReputablePolicyState` remained **1** across the diagnostic observations; those observations do not prove equality of every Windows policy or Unity preference. This is an attribution based on matching historical events and file/process identity, rather than the HRESULT or registry state alone.

Microsoft identifies `VerifiedAndReputableDesktop` as the Smart App Control enforcement policy and registry state `1` as On in its [signature-testing documentation](https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/test-your-app-with-smart-app-control). Only its read-only mode descriptions were used here; none of the configuration instructions were executed.

The stock probe preserved all **790** measured core files, **5,407** main project inputs and **5,421** isolated Unity6.6 inputs. Independent rehash confirmed those recorded maps and artifacts. No Unity process remained. The probe did not record preference/registry fingerprints; measured preference equality is therefore not claimed. Its helper contains no preference or security-setting writes.

Evidence to inspect without rewriting:

- [Current Windows event and file evidence](../../Verification/Evidence/WindowsAdmin96/Set02/Report.json), with private raw records retained and public correlation hashes in place of raw ActivityIDs. The earlier [report-preparation cardinality error](../../Verification/Evidence/WindowsAdmin96/Set01/PreparationFailure.json) is retained separately; it did not change the underlying events.
- [Stock probe report](../../Verification/Evidence/Unity6LTS95/CoreLoaderStock/Set01/Report.json) and [raw stdout](../../Verification/Evidence/Unity6LTS95/CoreLoaderStock/Set01/stdout.txt).
- [Normal installation](../../Verification/Evidence/Unity6LTS95/Installation/Set02/Report.json) and [verified official installer](../../Verification/Evidence/Unity6LTS95/OfficialDownloads/VerifiedSegmentedSet01/Report.json).
- [Checkpoint95 scope and remaining gates](95_ANDROID_PC_AND_LTS_BUILD_REVIEW.md).

## Optional read-only checks

Root has already collected the relevant events and current file/OS information. The commands below are optional read-only verification for the administrator, not a request for another native loader run. Use normal approved access if log access is denied, and preserve any access/no-events errors.

`CiTool -lp -json` lists current policy state without updating it. If needed, record the policy's management owner and current enforced/authorized state. The historical matching events above establish this block's attribution. [Microsoft CiTool reference](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/operations/citool-commands).

```powershell
Get-CimInstance -ClassName Win32_OperatingSystem |
    Select-Object Caption, Version, BuildNumber

& "$env:SystemRoot\System32\CiTool.exe" -lp -json
```

To inspect the exact existing records without changing or clearing the log:

```powershell
$reviewEvents = Get-WinEvent -LogName 'Microsoft-Windows-CodeIntegrity/Operational' `
    -FilterXPath '*[System[(EventRecordID=1809 or EventRecordID=1810 or EventRecordID=1811 or EventRecordID=1812 or EventRecordID=1813 or EventRecordID=1814 or EventRecordID=1815 or EventRecordID=1816)]]' `
    -ErrorAction Stop
$reviewEvents | Sort-Object RecordId |
    Select-Object TimeCreated, Id, RecordId, Message
$reviewEvents | Sort-Object RecordId | ForEach-Object { $_.ToXml() }
```

Check the present file and signature without loading the assembly. `NotSigned` is diagnostic information, not a maliciousness determination or permission to alter the file.

```powershell
$reviewDll = 'E:\HeartRainUnity6LTS95\6000.3.27f1\Editor\Data\Tools\BuildPipeline\NiceIO.dll'
Get-Item -LiteralPath $reviewDll |
    Select-Object FullName, Length, LastWriteTimeUtc
Get-FileHash -LiteralPath $reviewDll -Algorithm SHA256
Get-AuthenticodeSignature -LiteralPath $reviewDll |
    Select-Object Status, StatusMessage, SignerCertificate, TimeStamperCertificate
```

Compare `Get-FileHash` with the flat-file SHA256 above. Code Integrity can report other hash representations; do not treat unlike hash types as a changed file. Any unexpected current file drift requires investigation before another build attempt.

Raw event XML may contain machine names, SIDs and unrelated file paths. Keep raw collection private and immutable; publish only separately sanitized, hash-bound derivatives. The administrator should return a concise finding with event time/record/ActivityID, exact affected file/hash, policy ID/name/owner, signature result, and an approved next action.

## Resumption criteria

The Smart App Control gate is confirmed; administrator resolution remains pending. Preserve the failed probe and all historical receipts. This review does not authorize changing, removing, refreshing or downgrading policies, changing trust settings, re-signing/replacing vendor DLLs, or substituting a runtime to evade the block.

After an approved supported resolution is available, use fresh evidence to repeat the exact stock loader diagnostic against source-bound vendor bytes. Reaching the deliberate missing-input exception proves only that narrow loader path. Then install matching official Android components and pass the minimal Android smoke build before preparing the full-game LTS copy. Full-game compile, regression, APK inspection and separate-package device startup/splash verification remain required.

No Unity6.3 Android module download/build, full-game copy, APK or project promotion follows merely from completing administrator review. The accepted checkpoint93 Android app remains the available tested artifact, with its existing Unity2022 splash still enabled.

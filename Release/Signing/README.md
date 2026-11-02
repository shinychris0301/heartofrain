# Developer-owned release signing

Created on 31 October 2026 for `com.heartoftherain.game`.
The key remains on the developer's Windows account; it is not uploaded to the
backend or included in this repository. Review126 now has a Development/sandbox
APK signed with this identity. Checkout and production release acceptance
remain separate.

The public certificate, fingerprints, alias and validity are recorded in
[release-certificate.json](release-certificate.json). The certificate files
`release-certificate.der` and `release-certificate.pem` are public and safe to
share with provider consoles.

The [Review126 sandbox APK](../../Unity/Builds/Review126/HeartOfTheRain_SDK126_Sandbox.apk)
uses package `com.heartoftherain.game`, version code `126`. Its
[public APK receipt](../../Unity/Builds/Review126/APK126.json) records
`sandbox=true`, `development=true` and `productionApproved=false`. The
[static audit](../../Verification/Evidence/Review126/Android/SignedBuild01/Static/Values02/Audit.json)
verifies the actual developer-owned signer and SHA-1 registration match. Device,
real payment/ad and production acceptance remain open.

`release-certificate.json` records creation-time state, including
`androidApkSigned=false`; the Review126 receipts record the later APK signing.

| Item | Location or value |
| --- | --- |
| Private keystore | `%LOCALAPPDATA%\HeartOfTheRain\ReleaseSigning\RuStore\heartoftherain-release.keystore` |
| Key alias | `heartoftherain-release` |
| Format | PKCS#12; RSA3072; SHA256withRSA certificate |
| Local password custody | `password.dpapi` beside the keystore; Windows CurrentUser protection |
| Verified local backup | `E:\HeartOfTheRain-Private\SigningBackups\RuStore\20261031` |

Both private directories allow the current Windows owner and SYSTEM. A random
256-bit password protects the PKCS#12 file using AES256/SHA256 protection. The
same password opens the store and private-key entry. It is supplied to Java only
through a child-process environment variable, never through command arguments,
project files or logs. The setup refuses existing destinations and preserves
partial material after a failure instead of silently creating a replacement.
Once the public certificate is published, creation is blocked and verification
also checks that the backup matches the published release identity.

## Owner recovery steps

1. From a local PowerShell terminal at the project root, display the password in
   a private Windows dialog. This command does not print or copy it to chat,
   console output or the clipboard:

   ```powershell
   .\Backend\.venv\Scripts\python.exe -B Release\Signing\manage_release_signing.py show-password --root "$env:LOCALAPPDATA\HeartOfTheRain\ReleaseSigning\RuStore"
   ```

2. Save that password in your own password manager and independent recovery
   storage. Do this before the first store upload. The DPAPI file alone cannot
   provide recovery after loss of this Windows identity.
3. Copy the complete verified backup directory to storage on another device,
   such as an encrypted offline drive. Retain another secure independent copy.
   Keep the password separately from the backup. The keystore is already
   password-encrypted; its public descriptor and certificate are included.
4. Verify the copied backup with the command below, substituting its actual
   location. It checks exact keystore bytes, both public certificate formats
   and actual private-key signing. This verification on the current PC does not
   by itself establish that the independently saved password is recoverable.

   ```powershell
   .\Backend\.venv\Scripts\python.exe -B Release\Signing\manage_release_signing.py verify-backup --root "$env:LOCALAPPDATA\HeartOfTheRain\ReleaseSigning\RuStore" --backup "X:\your-backup-folder" --jdk "E:\HeartRainUnity6LTS95\6000.3.27f1\Editor\Data\PlaybackEngines\AndroidPlayer\OpenJDK"
   ```

Only the two local copies have been verified here. Off-device encrypted copies
and independent password retention are pending owner actions; complete both
before the first store upload.

## Recover on another Windows account or computer

Use this source utility, its `SigningProbe.java` companion, an existing
JDK11.0.12+ or JDK17, the backup folder, and the independently saved password.
The destination must be new and outside this repository. Run from an interactive
terminal; the password prompt hides input and refuses noninteractive input.

```powershell
.\Backend\.venv\Scripts\python.exe -B Release\Signing\manage_release_signing.py restore --root "$env:LOCALAPPDATA\HeartOfTheRain\ReleaseSigning\RecoveredRuStore" --backup "X:\your-backup-folder" --jdk "C:\path-to-your-jdk"
```

Recovery checks the backup before writing the destination, preserves existing
destinations, verifies a fresh private-key signature, and protects the password
for the new Windows current user. It does not need the original DPAPI file or
original keystore directory. The actual local recovery test used the backup and
password with original-custody reads blocked.

## Use for a release build

In the isolated SDK-enabled release project, select this external keystore and
alias under Android Publishing Settings. Enter the password locally for that
build session. Keep the main verification project and its debug signer separate.
The public SDK125 release template already records the new certificate SHA256.

After building, use Android `apksigner verify --print-certs` to compare the actual
APK signer with `release-certificate.json`, then complete the Android/provider
acceptance checks. Private-key challenge checks establish usable key material;
the APK signature audit establishes which identity signed the actual artifact.

Keep this same signing identity for subsequent updates. The `create` command is
for first setup only and rejects existing custody or backup destinations. Do not
create a replacement identity for an update without reviewing store continuity.

Earlier QA APKs use `com.heartoftherain.review98` and an Android Debug
certificate. Their fingerprint is distinct from this developer-owned identity.
The implemented VK login uses browser OAuth with callback
`https://api.novamind-it.ru/v1/identity/vk/callback`; Android platform registration
does not replace that Web/browser registration.

References: [Android signing](https://developer.android.com/studio/publish/app-signing),
[JDK keytool](https://docs.oracle.com/en/java/javase/17/docs/specs/man/keytool.html),
[Windows DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata).

# Review126 — SDK payments, rewarded ads and VK

Status: the combined, release-certificate-signed **sandbox Development APK is built and statically verified**, and the existing hosted authority has been upgraded in place to schema 125. SDK payments, capped rewarded ads, VK and constrained original 50-level replay are enabled on the same managed wallet. The bounded LocalService worker check, online backups, inactive quarantine restore and fresh healthy monitoring passed. Actual provider/device acceptance remains open. Production approval remains false.

The main project remains Unity 2022.3.62f3/M67R4. Android packaging uses the already approved isolated Unity 6000.3.27f1 SDK project. Approved art, original level JSONs, GUIDs, main settings and gameplay rules are preserved. Newer unrelated Main edits remain outside the frozen APK snapshot.

## Registered inputs and selected behavior

| Input | Value |
| --- | --- |
| Android package | `com.heartoftherain.game` |
| RuStore application | `2063777840` |
| VK application | `54867814` |
| VK callback | `https://api.novamind-it.ru/v1/identity/vk/callback` |
| Backend | `https://api.novamind-it.ru` |
| Managed identity scope | `review-novamind-vps-1` |
| Rewarded unit | `R-M-20291714-1` |
| Interstitial unit, configuration only | `R-M-20291714-2` |
| Payment-return scheme | `heartoftherain-pay` |

The owner confirmed RuStore sandbox/product readiness, Yandex rewarded-unit readiness, and VK Web/browser integration with the exact callback. These confirmations are distinct from observed SDK transactions, ad playback or VK authentication.

All twelve registered consumable SKUs are in `Release/Monetization126/commerce.sandbox.json`. Wellkeeper uses `hotr_bundle_wellkeeper_c`. The existing approved full inventory grants are retained: Special offers are once per stable player/offer; Mega and coin offers are repeatable. No offer grants story stars.

Payments use the explicitly selected `sdk_client_reported` mode. Matching SDK `CONFIRMED` purchases commit the frozen grant durably before acknowledgement. `PAID` two-step funds are not automatically captured. Durable order/receipt identity prevents repeat grants through retries and restart. This mode requires no RuStore API key ID, API private signing key or notification-decryption key. Authenticated client reports are not independent provider proof; this remains the selected trust limitation.

Voluntary Shop video grants 400 coins, at most three claims per player-local day, with a 600-second cooldown. Cancellation, no fill and incomplete playback consume no reward quota. Completion is client-reported and capped; it is not server-side impression verification. No interstitial display point was added.

## Engineering changes and verification

The new owner-bound staging126 launcher upgrades the **same** schema 15 authority to schema 125 while stopped. It holds both OS leases, preserves the database identity and original owner/scope/nonce, validates a pre-upgrade snapshot and supports interrupted-operation recovery. Original accounts, wallets, inventory and historical API orders remain. Ordinary schema 15/production launchers retain their guards. The actual `python -m` path is covered; a private-permit module-identity defect found during testing was corrected.

The new staging126 operations module provides schema 125 online backup and a permanently inactive restore quarantine. Backup receipts retain the installed monitor's ownership format. Original ad disable/re-enable controls remain usable after migration and preserve quota/cooldown and pending-claim recovery.

On Windows, rewarded-ad journal replacement now uses a flushed same-directory atomic replacement. Receipt presentation follows durable journal resolution, including lost-clear-acknowledgement recovery. Android's existing replacement path remains. Combined SDK/Yandex guards validate actual imported configuration, approved Android sources, SDK versions and privacy manifest controls.

Actual packaging also exposed two tooling defects: the stock Unity Gradle distribution has library JARs without the previously assumed batch wrapper, and Unity UPM adds `_fingerprint` to two approved package manifests. The corrected guards accept only the observed stock toolchain and exact pinned manifests with the known generated suffix/formatting. All other package contents remain byte-pinned; SDK/engine versions were not upgraded.

| Evidence | Result and scope |
| --- | --- |
| `Backend/Full02/Service_Tests.json` | 959 passed; zero failures/errors/skips; actual approved replay-worker integration; all 179 source inputs unchanged before/after/current |
| `Backend/FinalFocused126.json` | 26 passed; includes real launcher/TCP/restart, same-player concurrent purchase/ad, migration and operations cases; binds external commerce fixtures |
| `Operations/Compatibility03.json` | 59 passed, including12 new operations and47 legacy compatibility cases; overlaps other counts |
| `Advertising/Advertising126Summary.json` | 853 native Editor assertions: journal485, flow204, boundary24, parser140; zero C# errors/warnings |
| `Toolchain/UpmManifest126Summary.json` | 198 SDK guard assertions/10 cases; includes earlier Gradle checks, not an additional independent count |
| `Android/SignedBuild01/Native.json` | Actual ARM64 IL2CPP signed Development build;16 checks, zero errors, four BuildReport warnings |
| `Android/SignedBuild01/Static/Values02/Audit.json` | 31 actual APK checks: signature, resource values, payment return, SDK classes/versions, HTTPS/privacy, alignment and native libraries |
| `Android/IndependentSignedApk126.json` | Independent artifact/receipt/source seal;2966 protected files,3295 metas/GUIDs and10 owned C# files verified |

All evidence paths in this table are relative to `Verification/Evidence/Review126`. Counts overlap and must not be summed into a total of independent tests. SQLite/ASGI/TCP synthetic financial observations are not real provider transactions. Editor and APK checks are not physical-device rendering/payment/ad tests.

Four logged material diagnostics comprise three IL2CPP code-splitting notices and duplicate INTERNET permission input; the merged APK has one INTERNET declaration. The native report does not export per-step BuildReport messages, so exact warning-count attribution is not claimed. Additional stock SDK/compiler notices are recorded separately by the independent seal. Earlier aborted/failed build epochs remain retained.

## Signed test artifact

`Unity/Builds/Review126/HeartOfTheRain_SDK126_Sandbox.apk`

- SHA256: `a5477b4e14e98b23a72c71fba1ee2e95a61a745b9df1d1034a8f8342aff62d3d`
- Size:347,392,410 bytes; package `com.heartoftherain.game`; versionCode 126; API 26–36; ARM64; Development with script debugging disabled.
- Release-certificate SHA256: `7257537a5b329cc5b018d93299d748404432c1b49f1b2388444ab843a4ba170d`.
- Certificate SHA-1: `A3:92:5B:6F:BB:1F:AA:D2:0B:D5:6A:6A:7C:59:21:47:E7:F7:F7:B6`.
- Unity splash and Unity logo are disabled in the built settings. New device cold-start acceptance has not occurred.
- The registered package has separate Android storage/device credentials from existing QA packages. No installation, overwrite, silent credential transfer or local-wallet import was performed.

The four unrelated newer Main paths are `RewardedAdsLayout85.cs`, `OnlineTeamsChat110.cs`, `OnlineTeamsLeave113.cs` and `NavigationDiagnostics124.cs`. Their paths are fully recorded in `Android/PublishedApk126.json`. No claim is made that these newer edits are included or tested by this APK. The generated private Android manifest is SDK packaging output, outside the protected source set.

Before first store upload, the owner must retain the release password independently and keep an off-device encrypted keystore copy; follow `Release/Signing/README.md`. Then upload this exact signed APK to RuStore application2063777840 and use the Console-configured test account. The app/backend sandbox policy does not turn an ordinary RuStore account into a sandbox tester.

## Hosted and worker checkpoint

Fresh read-only inventory verified Windows Server2022 with Desktop Experience, two logical CPUs, 2,046 MiB RAM and 197 MiB available at that sample. Existing LocalService services, Caddy, original schema 15 ownership/two players/two wallets and nine healthy monitoring checks were preserved. No commerce/ad/gameplay rows existed. This is not evidence for Windows Server Core compatibility or production capacity.

Bundle02 contains the accepted179 backend inputs, seven public profiles and the legacy commerce fixture:187 files, ZIP SHA256 `f8f24a227a48dfe6ac8e5b276a6287b77e8b526f7703aa360edb4cf3d24eb2bf`. The existing service now uses its backend working directory at `C:\Apps\HeartOfTheRain\Monetization126\Backend`; the old source directory and existing interpreter remain untouched.

The actual VPS focused retest passes all 26 unchanged tests in 31.999 seconds on Python 3.14.10, with zero failures/errors/skips. Process-only canonical TEMP/TMP matches the verified canonical live data path. New 187/old 76 source hashes, owner, manifest, database device/inode and all financial/model counts remain unchanged; both services and all nine monitor checks remain healthy. See `Operations/VpsSourceQualification126.json`. The first host run passed 25/26 because its fixture used an 8.3 TEMP spelling; the installed monitor compares canonical ownership paths. A disposable diagnosis proved that alias cause. General 8.3 support remains an open portability finding; no source/test/monitor guard was weakened. A failed transport wrapper lost its child verdict; that failure is retained separately. The accepted wrapper persists stdout/stderr/exit metadata before judging the verdict; its nonempty stderr is a classified deprecation warning, with exit code 0.

The approved83 worker has15 source pins. Fourteen match the current/frozen client exactly. The sole BoardModel delta adds an opt-in safe-segment-bottom growth predicate. For all 50 verified original JSONs, its flag is absent/false and the predicate is always true, preserving the old candidates. All50 original JSONs byte-match worker pins; frozen asset GUIDs select them in order. `Deployment/Worker01/SourceSemantics126.json` documents this constrained source compatibility. It establishes no equivalence for opt-in preview117 configurations.

The bounded actual LocalService worker check passed under SID S-1-5-19, with one recorded L1 swap, all 50 catalog bindings, bad-pin rejection before job creation and the separate one-second Windows JobObject timeout control. Unity elapsed 0.442887 seconds; peak process/job memory was 127,856,640/129,335,296 bytes (about 122/123 MiB). Its enforced limits were 256 MiB, 60 seconds and two processes. Available physical memory was about 311 MiB before the run; the existing authority, code, services and healthy monitoring remained unchanged. See `Operations/VpsLocalServiceWorker126.json` and `Operations/HostPreparationClosure126.json`. This is one replay on Server 2022 Desktop Experience, not an entire L1 win, all-level execution, resident-RAM minimum, sustained capacity or Windows Server Core proof. The qualification cap is distinct from the unchanged serving adapter's 1 GiB ceiling; neither is an up-front memory reservation. The scheduled boundary and OS LastRun timestamps are both retained; their difference does not support a precise claim of 20 seconds of actual launch delay. No live replay activation occurred in that isolated receipt; the subsequent reviewed cutover enabled the constrained original campaign.

## Completed hosted cutover

The independently reviewed r4 controller (`fb6bbd463a8129102c4d21c11febbac1f7a84845b4d56b5c1bb5c53b941e2fab`) ran from 10:54:54 to 10:56:12 UTC with exit 0. All 21,494 captured events were valid, no validation failed and stderr was empty. The stop phase began at 10:55:08, while its qualified-worker proof was fresh. Schema 15?125 completed in place; the original database device/inode, Ready owner and all original schema-15 column projections were preserved. The original logical SHA256 remains `ef025df2aab27eeca9a73b2178e797ad78b2ae121f1daeb5c4167c20447d4e9c`: two players, two wallets, two ledger rows, and zero financial/ad/attempt/replay operations. No synthetic transaction was submitted to this authority.

Only the existing service's working directory/launcher arguments changed. It retains LocalService, its interpreter, Caddy, HTTPS origin, port 8751, identity scope, deployment ID and original owner nonce. It runs `hotr_backend.staging_sdk126 start` against the same manifest/data directory. SDK app 2063777840/package `com.heartoftherain.game`, VK 54867814/exact callback, ads 400/3/600 and the qualified original replay bundle are configured; production remains false. SDK readiness is configuration evidence, not a real purchase or ad impression.

The validated schema-125 post-backup and permanent restore quarantine completed at 10:55:38?39. The quarantine has no serving Ready owner and cannot be activated. Fresh monitoring was healthy at 10:56:02; loopback/public HTTPS health and readiness passed twice. Original source, proxy and worker bytes remained unchanged. No database replacement, schema-15 rollback or production activation occurred. Raw complete logs and exact pre-change configuration archives remain on the VPS under restricted private directories.

A separate actual read-only current-state inspection passed at 11:07 UTC: all 65 table counts, original ownership/inode/logical data, twelve SDK offers, ad/VK/replay settings, LocalService, source and worker hashes, all three Ready snapshots, permanent quarantine and fresh nine-check monitoring were verified. Public and loopback health/readiness returned 200 with normal HTTPS validation. The [cutover receipt](../../Verification/Evidence/Review126/Operations/VpsCutover126.json) and [separate current-state receipt](../../Verification/Evidence/Review126/Operations/VpsCurrentState126.json) distinguish the mutation from its later verification. Backend source remains the accepted 179-input epoch; the final complete 6,051-path Main inventory confirms exactly the four disclosed newer paths, with all ten owned C# files still matching the frozen APK.

Five operator-review findings were corrected before execution: embedded bundle metadata has no future ZIP hash, backup receipt binding needed a durable checkpoint/recheck, worker/catalog validation needed to precede stopping, SCM Running needed a bounded readiness wait, and failure logging could prevent stop containment. The final controller captures evidence before judging it and contains failed transitions without an automatic rollback. The Windows 8.3 monitor portability issue and inactive production122 CLI risk remain separate open findings.

## Remaining steps in order

1. The unchanged 26-case canonical-path host verdict and integrity checks are captured. Preserve the raw-path failure; repair general monitor alias handling in a separate narrow change with real Windows alias/ownership negatives before broad deployment.
2. The resource-gated LocalService worker check passed. Review the exact approved artifact, original 50-level source compatibility and current host health before selecting its replay configuration. Preview117, Server Core and sustained capacity remain separate acceptance work.
3. The stopped same-authority SDK126 migration, ads opt-in and owner-confirmed VK configuration are complete. Original owner/database/accounts/wallets, actual HTTPS readiness/feature flags, fresh schema 125 backup and permanently quarantined restore drill passed. Preserve those artifacts; never restore schema 15 over newer schema 125 financial writes.
4. After signing recovery custody is complete, upload the exact sandbox APK. On a real configured RuStore test account, verify all 12 native products/prices, successful one-step delivery, cancellation, bank return, app kill/restart, lost response, duplicate callbacks and one-time Special eligibility. Prove one durable grant and one presentation receipt; inspect sanitized IDs/status only.
5. Exercise Yandex rewarded playback using an official demo/test-unit harness, then the owner-approved placement according to provider testing rules. Cover no fill/cancel/incomplete, completed reward, kill between completion/claim, retry/restart, quota/day/cooldown and concurrent purchase. Do not treat live ad clicks as a test.
6. Test actual VK browser login/callback, cancellation and explicit managed-account recovery across the new game package and retained QA packages. Preserve separate credentials; no implicit wallet/account merge.
7. Replace temporary public legal/support pages with the owner's actual operator/contact facts. Complete final non-Development production build/provider/device acceptance and an explicit production cutover review.
8. Before any future production122 launcher use, reproduce and repair its inferred `__main__`/package private-permit identity risk with an actual module-CLI regression. This Review126 qualifies the selected staging launcher, not that inactive production path.

No new Git commit or provider transaction is claimed for this review. Existing unrelated worktree/index changes remain preserved.

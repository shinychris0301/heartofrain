# 59 - Rain Cup design R1 integration

23 October 2026. Runtime baseline M67R4; Unity 2022.3.62f3. Source checkpoint, no APK build/install. Evidence: `Verification/Evidence/RainCupR1/Comparison.html` and `Verification_Summary.json`.

## Request and package review

The owner requested review/integration of `Heart_of_the_Rain_Rain_Cup_Design_R1.zip`. Its handoff, layout contract, five-language strings, motion, reward table, asset/provenance manifests, pixel budgets, browser/font QA and import package were examined as supplied development context. Browser response delays, demo transitions, sample names/avatars and sample points are not runtime authority. No new TMP migration, production service, competition rule or unrelated page is authorized by those notes.

ZIP CRC passes. All 29 manifest hashes match; 38 bundle/UnityPatch file pairs match. Nine new RainCupDesign PNGs retain original bytes and supplied GUIDs. Existing chrome, close, cards, rewards, fonts, Primary and check are reused. Four differently located shared references are byte-identical at their live GUIDs. The preview backdrop and example Dariya portrait are not replacements for current Chapter 1 or saved player appearance. Package registry claims 32 entries; the merged live registry has 31 required entries because it reuses actual shared identities and excludes the preview backdrop.

## Native implementation

`RainCupPage.cs` and `RainCupLayout.cs` bind the new RainCupDesign assets/layout/localization resource. The native modal uses the current chapter blur behind white-tinted foreground sprites, independent player portrait/mask/frame, new trophy and rank medals, selected Standings/Rewards tabs, highlighted current player/prize and live quantities. Long display names ellipsize with their full label retained. Existing dynamic UGUI fonts are retained; native glyph/fit checks cover EN/ES/FR/DE/RU.

Header/footer remain fixed; only the body is masked and scrolls. Rebinding preserves scroll; switching tabs resets it. Close stays inside the safe area and outside the body mask. Compact phones scroll to all rows. The supplied short-wide fallback uses overview/list columns and a compact footer; its trophy and first row remain visible. Android portrait-only settings are unchanged.

Locked, Join, Play, Claim and Done actions derive from the current service snapshot. Play opens the existing HomeLevelFlow pre-level, without awarding points. Production remains unavailable through the existing factory. Approved practice behavior is unchanged: unlock at 10 first clears, manually joined 48 hours, one point per new clear, no loss/replay points, four labelled simulated rivals, shared tie ranks and one no-expiry finishing prize. The existing service has a fixed four-rival model; future production populations require a separate standings contract.

Join retains its command ID through uncertain failures. Both join and claim refresh persisted state after an exception: precommit failures retain eligibility with a retry notice; committed outcomes reconcile active/collected state. A committed prize cannot appear unclaimed merely because its reply was lost. A read failure is distinct from an unavailable event. Retry receives keyboard focus and each primary accessibility label matches its displayed action. Mutations, grants and scoring remain in the existing model/services, never motion callbacks.

Entry runs 250 ms in unscaled UI time. Only an acknowledged non-null grant triggers trophy motion, per-reward centered pop and fourteen pooled glints outside the scroll mask. Closing cancels presentation; reduced motion settles immediately. Disabled transparent hit graphics retain zero alpha. Cosmetics neither grant inventory nor change cup state.

Detailed art keeps mipmaps/trilinear sampling; slices/mask remain bilinear without mipmaps. Rain Cup tabs keep LBRT [96,80,96,80], multiplier 8, and the 32-pixel center strip. Primary uses 8.57, chrome 3.891, cards/hero 6, compact track 8, simple fill stretched without preserve-aspect. Existing guard coverage is retained with nine additional required sprites and tab-border validation. Prepare deliberately rejects the invalid [96,96,96,96] tab border and restores the valid importer. All existing artwork/fonts/metadata, levels, rules and Unity settings match pre-turn hashes. Exactly six existing Unity inputs change: two runtime scripts, two verification scripts, guard and registry; all other Unity inputs are additions.

## Verification

Pinned native Editor processes pass:

- Import/bindings and strict guard: 31 registered sprites, zero errors, invalid tab-center regression rejected/restored.
- UGUI: 8,081 checks, 140 cases, 150 framebuffer captures. Five languages x five physical viewports x five states, plus English states at 1179x2556/scale 3, 1536x2048/scale 2 and 2532x1170/scale 3. Fifteen full frames and two documented exact pixel crops inspected. The ordinary phone/tablet/wide fixtures use the existing responsive scale.
- Model/file suite: 822 checks covering old saves, frozen joined rules, all prize tiers, ties/deadlines/rollback, score atomicity, duplicate commands and file interruptions.
- Connected isolated file profile: 39 checks. Real join and authored L11 model-win/celebration integration, failed win-save retry after deadline, pre/postcommit join/claim failures, duplicate claims, read recovery and modal navigation pass. Axe stock is explicitly staged for this probe; it is not natural-play/balance certification. The assertion count varies with staged obstacle hits; the 23 distinct assertions are required.
- Existing general suite: 533/533.

`Confirmed_Collection.png` follows an actual saved first-place local grant (300 coins, one Rocket and one Bomb); other design state snapshots are labelled fixtures. The live UI resolution audit is an actual idle 1179x2556 Editor composition, not a device/peak performance measurement. Full captures are untouched; two inspection crops have source SHA/rect/output SHA recorded. Historical reports are retained separately from these fresh reports. Source freeze: 4833 inputs; manifest SHA-256 `95855f94567f5976fd12a809bbb14a9404c6eaec697fb1d986416914e9218058`.

Reproduce with `powershell.exe -NoProfile -ExecutionPolicy Bypass -File Verification/Run-RainCupR1.ps1`, then `Verification/Run-RainCupR1Services.ps1`. The collector validates frozen evidence and does not run Unity.

## Remaining limits

No current APK build/install, LDPlayer check or physical-device/notch/touch certification. Last recorded deployment remains 54, built from source through 53. Production identity, hosted authority, real competitors and async remote Join/Claim are not implemented by this design update; current claims are synchronous local transactions. Source-based state/retry tests do not certify a future network adapter. Native device memory, sustained performance and compression remain open; RGBA32/mipmap reference imports are preserved, and chrome's 3.891 border budget is still slightly exceeded at 4x. This page does not certify every unrelated feature or level.

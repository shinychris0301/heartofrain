# Progress artwork and exact clipping — checkpoint 92

26 October 2026. **Targeted progress repair verified and published with open gates.** `Verification/Evidence/Progress92/Summary.json` is published as `COMPLETED_PROGRESS92_WITH_OPEN_GATES`. Final Set02 passes 16,823 checks across Progress92 and Display88; both SDK-free internal Android builds and static APK checks pass on the same 5,405 inputs. Development APK `c9fa68f4` is replacement-installed on the owner phone. Root reviewed four selected native progress images, two matched before OS images and five current OS images. Rain Cup now shows a full-height body at approximately 80% for 8/10; Profile, Wellworks, local Teams and normal Home relaunch are accepted within the scope below. Profile, preferences and progression remain byte-identical at revision 36 / 1,700 coins / five lives / current Level 9 / eight completed levels, with no active attempt or pending marker. The accepted checkpoint90 summary remains immutable. This is not release approval or whole-game performance certification.

## Findings and changes

Rain Cup assigned the fractional progress width directly to a Simple image while preserving the complete sprite's aspect ratio. The image therefore became shorter at low progress, leaving a thin body inside a normally sized track. This was a rendering defect; the completed-level count and unlock threshold were correct.

Rain Cup now keeps a sliced image at the approved height inside a rectangle whose width is the exact completed/required fraction. A minimum image width retains the sprite's caps; the clip, rather than that minimum, determines visible progress. Zero progress hides the clip. The track, count, threshold and artwork remain unchanged.

The broader audit found two related problems: Profile statistics used horizontal Filled rendering on a padded sprite, and local Teams imposed a minimum visible width on its Rally/life-request fills. Profile now retains its sliced body inside an exact fractional clip. Local Teams uses the same principle so tiny values remain bounded by their actual fraction and zero has no residual fill. These changes affect presentation, not records, event totals, life-help rules or backend state.

| Family | Review and resulting behavior | Scope |
| --- | --- | --- |
| Rain Cup locked/unlock progress | Sliced fill, original height, exact fractional clip and zero hidden | PASS: controlled native fractions and matched ordinary-phone 8/10 before/after |
| Profile chapter statistics | Replace padded Filled clipping with a sliced body inside an exact-width mask | PASS: native low-progress control and matched phone Stats view at 8/50 |
| Local Teams Rally | Remove inflated minimum visible progress; minimum cap image stays inside the exact clip | PASS: native geometry/GPU and ordinary demo Rally at 2,200/3,000 |
| Local Teams life request | Exact fractional clipping; zero remains empty | PASS: native boundary fixtures and ordinary demo request at 2/5. Hypothetical very small ratios are renderer fixtures, not new gameplay rules |
| Wellworks | Existing exact clip, sliced body and zero-hidden behavior retained | PASS: actual native production Build/Render regression and ordinary phone progress at 8/50 |
| Home chapter progress | Existing sliced direct-width fill retained | PASS: actual native production Build regression and normal phone Home relaunch; no gameplay/reward action |
| Launch | Existing sliced, monotonic horizontal progress with zero hidden retained | Source invariant review; no new startup performance or readiness acceptance |
| Legacy LevelComplete | Existing M66 progress unchanged; current win route is HomeLevelFlow/M67 | Legacy source inventory only |
| Connected Teams | No equivalent local Rally/life-request bar in this renderer | Source inventory only; no live social-service acceptance |

Six runtime files change: `App/Profile/Runtime/RainCupPage.cs`, `App/RainCupDesign/RainCupDesignLayout.cs`, `App/RainCupDesign/RainCupDesignAssets.cs`, `App/Profile/Runtime/ProfilePage.cs`, `App/Teams/Runtime/TeamsLayout.cs` and `App/Teams/Runtime/TeamsPage.cs`. The existing `ProfileDesignKitReview` assertions are updated for the new clip ownership. New `Progress92Verification` is an isolated native Editor fixture.

Approved image bytes, palette, existing asset GUIDs, level data, economy, model/services and gameplay timing remain unchanged. The engine remains Unity 2022.3.62f3. No engine or provider SDK upgrade is included.

## Validation and evidence

The owner's naturally advanced save differs from the earlier checkpoint90 phone review: revision 36 / 1,700 coins / five lives / current Level 9 / eight completed levels, with no active attempt. The new before/after comparison therefore uses fresh accepted90 APK captures at that save, rather than presenting the old one-clear image as a matched control. The baseline helper cannot install an app or authorize a new target. It permits only the existing read-only observer plus explicit root-operated UI navigation, and verifies ordinary profile/preferences/progression through normal relaunch.

| Evidence | Status and acceptance limits |
| --- | --- |
| Immutable checkpoint90 | Summary SHA256 `10352d3592c35d51f29d031ca6b70107140d54e5078db94065788f4dbd796557` remains bound without rerunning its old current-tree verifier |
| Backend | Current source bytes match the accepted historical 448-test input map. No backend files changed or tests rerun in this visual repair |
| Host rejection controls | Final 20 controls PASS. Parser, source scope, tamper/privacy, PNG, matrix completeness, owner-state/fifth-link and missing completion-receipt checks only; not Unity or Android tests. Earlier 14/15 PASS reports and a host FAIL remain: a negative fixture changed zero to zero and therefore expected rejection incorrectly; only that fixture was corrected |
| Actual phone baseline | Two accepted90 APK OS images root-reviewed: Rain Cup 8/10 and Profile statistics 8/50. Rain Cup's rendered body fills only roughly a quarter of its track despite the correct 8/10 count. Before/after/ordinary-relaunch profile, preferences and progression are identical at revision 36; zero active attempts or pending markers |
| Native Set01 | Retained FAIL: 1,848 checks / 120 cases / 20 failed Home assertions. Home prefab preview state replaced each injected fixture fraction with 17/50. Only the new native fixture was corrected to opt out before Build, with an explicit state assertion; no runtime change or assertion waiver. The independent Rain Cup/Profile negative controls passed in this failed set but do not substitute for final acceptance |
| Native Progress92 Set02 | PASS: 2,043 checks / 120 cases, zero failures/errors on 5,405 inputs unchanged during execution. Six actual production renderer families × four GameView sizes × five ratios, real imported sprites, UGUI mesh checks and GPU alpha readback. Root reviewed all four selected native captures. Controlled Rain Cup 1/10 body height increases from 7 to 18 physical pixels; controlled Profile 1/50 produces 10 pixels versus the old Filled control's zero. These are native controls, not phone measurements |
| Native Display88 regression Set02 | PASS: 14,780 checks on the same 5,405 inputs. Same-source full-display/safe-area regression; no additional device or whole-app performance claim. Combined current native total is 16,823 checks |
| Development and nondevelopment APKs | Both PASS in `Builds/bcf8838e8c9a450cb9395623a72d7cd7`; same 5,405 source inputs, exact settings/source and historical-report restoration. Development SHA256 `c9fa68f46c4adcf6281eb4d4575ed4dc234a03feb87376d9b2d731eb0078a1fd`, 331,354,716 bytes. Nondevelopment SHA256 `7dcac71ac79ff07034f8ab9b3ccbf672a6ee57b697f490e3401e63b7e0715fdf`, 266,361,950 bytes. These are SDK-free internal ARM64 builds, not store-signed release acceptance |
| Static APK checks | Both PASS: actual APK CRC, internal development signature, alignment, ELF load-segment compatibility, Russian label, package/manifest and DEX checks. Payment/ad SDKs remain absent in this internal profile. No real provider or store acceptance |
| Preinstall host check | Retained `Preinstall_HostFailure.json`: Windows PowerShell stdin converted the expected literal Cyrillic label to question marks. The APK's actual aapt label was Russian. Repeating the unchanged package/label/signature/CRC requirements with Unicode escapes passed; no runtime/APK correction or assertion waiver |
| Physical owner phone | Five current original OS images root-reviewed: Rain Cup 8/10 now has a full-height body at approximately 80%; Wellworks 8/50, Profile statistics 8/50, local/demo Teams Rally 2,200/3,000 and life request 2/5, and ordinary-relaunch Home with the unchanged wallet/lives/progression. Controls remain safely positioned. Two fresh matched baseline images use the same save. No reward, help, chat, account or gameplay transaction performed |
| Owner preservation and completion | Baseline, install, ordinary before/after and ordinary-relaunch profile/preferences/progression are identical at revision 36; zero active attempts and empty final marker inventory. The fifth installed owner-phone update link is bound through the unchanged historical chain. Exported current app-PID log has zero selected error signatures; this is not a whole-app PASS. The fixed eight-second observation interval is not a startup readiness/performance SLA |
| Publication | PASS: `COMPLETED_PROGRESS92_WITH_OPEN_GATES`; current source-manifest SHA256 `9850277218374a010129d49426b0ca6dcdd58bd950e872c17d851a452cad92fc`. Exact current native/build/static/phone proofs and explicit root visual assessment are bound. New collector verifies current92 only and retains raw failures; it does not overwrite old90 evidence |

Native framebuffer sizes are 320 × 568, 393 × 852, 720 × 1600 and 768 × 1024. The five ratios are zero, a very small fraction, 10%, 50% and full. Safe-subtree translations inspect geometry invariance; they do not override Android `Screen.safeArea` or establish tablet-device acceptance. Native control images use offscreen rendering and are not OS screenshots.

The modified `ProfileDesignKitReview` was not separately executed as a standalone suite in this checkpoint. Current Profile Build/Layout/RenderStats behavior is exercised through the new Progress92 fixture; the accepted native set consists of the two suites listed above.

## Remaining limits

This review targets progress artwork, clipping and existing layout. Native renderer fixtures, source inventory and ordinary phone observations retain distinct scopes. Live configured Teams, provider flows, rewards, gameplay, frame-time performance, broader devices and the existing RuStore production gates remain separate acceptance work. No new progress rule or change to first-clear counting is included.

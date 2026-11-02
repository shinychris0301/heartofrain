# Asynchronous backend Daily Gift UI — isolated review

21 October 2026. The owner approved continuing the remaining backend work. This connects the existing Daily Gift modal to the real portable service for explicitly configured, isolated Editor/development review profiles. Hosting remains deferred. Ordinary saves and production service selection are not migrated or activated, and the deployed Rain Cup APK is unchanged.

## Behavior and boundaries

The existing modal opens before a backend request finishes. It shows localized checking/claiming status and disables the primary action while busy. Close and the existing Back command remain available during network work. Reopening shares the outstanding operation. A response received after navigation cannot reopen Daily Gift over another page, and cannot replace a fatal save dialog or its original retry callback. Unavailable offers have an explicit retry which refreshes availability without claiming accidentally.

Claims still use `BackendGiftSession` and the existing `DailyGiftService` model: durable local intent, asynchronous HTTP, receipt/identity/quantity validation, idempotent local credit, then cosmetic Home reward reveal. A server credit whose response was lost leaves the original intent pending and the local balance unchanged. Explicit retry recovers that same receipt once. Closing the modal does not discard a pending intent. Unknown local/remote confirmations and ordinary account restoration remain model/service concerns, not animation-side grants.

The backend session now updates its cached offer to claimed after confirmed local settlement, including pending-claim recovery. This closes a presentation defect where the stale cached offer could leave Claim enabled until another fetch. Home reflects saved balances and the last confirmed offer; opening/retrying refreshes backend availability. There is no background poll or claim based on a device clock. Production freshness/offline/account policy remains to be integrated.

Loading, retry and confirmation text uses the existing shell, palette, reward assets, typography, layout, button feedback and five locales. Existing local-authority behavior and reward quantities are preserved. Translations pass native glyph/bounds checks; native-language editorial approval is not implied. No Japanese or new artwork is added.

`PlayerProfileHost.VerificationBackendClient` is an in-memory Editor/development injection point. It requires an explicit isolated repository before initialization; it cannot fall back to opening an ordinary save. Remote review selects an unavailable synchronous gift authority, preventing hidden local-service fallback. The modal uses the asynchronous session instead. No endpoint or token is embedded in assets/preferences. Release factory selection remains unchanged. Wellworks and Cup pages continue their existing local review behavior; their production service adapters are not supplied by this component.

## Changed files

Four existing player files change, all under `Unity/Assets/HeartOfTheRain/App/Profile/Runtime`:

- `DailyGiftPage.cs`: asynchronous loading/claim/retry, busy guard, late-response and save-dialog handling.
- `DailyGiftLayout.cs`: additional network-state flags and localized text; the approved structure/assets remain.
- `PlayerProfileHost.cs`: guarded review injection and cached backend badge selection.
- `BackendGiftSession.cs`: mark a confirmed offer claimed immediately.

`Verification/BackendGiftUIProbe.cs` and `Verification/Editor/BackendGiftUIVerification.cs` add native UI, restart and font/layout checks, with new metadata. The probe is compiled only for the Editor. Existing metadata, level data/masks, board model, animations and approved art remain unchanged.

The backend API, storage, authority, schemas, dependency lock and approved configuration files are unchanged. Only `Backend/README.md` and two verification helpers change: `serve_fixture.py --gift-ui` provisions a separate account and file-controlled response faults, and `check_restart.py` includes that account in recovery checks. Delay, HTTP 503 and lost-confirmation controls exist only inside the explicit test helper and ignored fixture directory. There is no new HTTP fault/reset/clock endpoint in the service or ordinary launcher.

`Verification/Run-BackendGiftUI.ps1` starts a separate hidden server, runs the suites, restarts it against the same database and stops it in cleanup. Fresh copies are retained here while earlier component reports are restored. `Run-UnityVerification.ps1` adds entry points. `collect_backend_gift_ui_results.py` validates frozen tested inputs, source boundaries, report/process identities, image-review hashes, credential export protection and the unchanged prior APK. The general collector selects this source checkpoint first and updates `Native_Source_Checkpoint.json`; earlier Android evidence keeps its own APK identity.

## Verification and visual evidence

Run from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Verification/Run-BackendGiftUI.ps1
.venv/Scripts/python.exe -X utf8 Verification/Tools/collect_results.py
```

Evidence is `Verification/Evidence/BackendGiftUI`. `Verification_Summary.json` is the final authoritative outcome and `Comparison.html` is the review gallery. Native UI captures render the actual runtime UGUI through a Unity camera/RenderTexture, temporarily restoring overlay mode afterward. They are not Android screenshots or physical-device approval. Button events and scrolling are programmatic native controls, not claimed physical taps/swipes. The measured PlayerLoop updates establish that the explicit HTTP delay yields; they are not FPS measurements.

The connected UI control covers Home shortcut, loading, duplicate input, close/reopen during a delayed offer, preservation of a synthetic fatal save dialog, actual HTTP 503/retry, durable claim intent, navigation to another page during a delayed claim, a committed server gift whose response is replaced by a fixture 503, pending recovery, one Home credit, immediate claimed state and five languages. A second native Unity process reopens the same profile and confirms it cannot claim again. Its 320×568 viewport at 100% UI scale verifies native scrolling of the 602-pixel content inside the 568-pixel viewport. The large control uses 900×1600.

Final verification passes **all thirteen native suites: 45,265 custom assertions/checks**. The new layout/glyph suite contributes 9,691 checks, connected UI contributes 50, and the separate native-process restart contributes nine. The remaining ten compatibility suites contribute the preceding 35,515 checks. Python service/ASGI execution passes **23 scenarios**. An actual backend process stop/restart passes **nine authenticated HTTP checks**, three each for the primary, recovery and UI accounts. Those Python/restart checks are separate from the native total. Assertions and staged controls are not independent natural-play scenarios or balance approval.

All **twelve original native UGUI frames** were explicitly inspected and hash-frozen in `Visual_Review.json`. Five saved-state frames include the existing cosmetic Home coin interpolation (1,250 toward 1,300); the authoritative saved balance is already 1,300 before that animation. The short-screen frame is scrolled to show the footer, so its top border is partially outside the viewport by design. Earlier debug/test-selection failures are not used as passing evidence; final reports/captures are tied to the final source freeze.

The tested freeze covers **4,463 Unity assets/metadata and 19 backend files**, with verification entry points recorded alongside them. Of 4,323 preceding player inputs, 4,319 are unchanged and four runtime scripts change. Two input files are added for the Editor-only probe and its metadata, giving 4,325 non-Editor-folder inputs. The separate Editor suite/metadata are also added. Existing artwork, level/mask data and metadata retain their hashes; static GUID/reference/resource integrity passes with no unexpected original changes. No actual fixture credentials occur in exported sources/evidence. Backend core, schema, lock and reward configurations are unchanged. The APK retains SHA-256 `c9e3928c5ae91aacaa047374550bf1f2ac532ab81c3e8039d0e52b554c1fc018`; no new device test or installed-state observation is inferred from that file hash.

The viewport test initially selected the wrong Home scroll container; the corrected harness explicitly targets Daily Gift's canvas and records its actual geometry. This was a test-selection correction, not a product scrolling repair. The Game View group follows the active build target and its previous selection is restored. The suite retains the existing local/profile/attempt/reward/Wellworks/Cup/native HTTP compatibility checks. Python service/ASGI tests, Unity execution and actual backend process restart are reported separately.

## Remaining work

No ordinary profile is uploaded, reset, imported or bound to a new backend identity. Hosting/HTTPS, secure client credentials, managed onboarding/recovery, approved wallet/profile migration, actual gameplay verification and server attempt settlement, production service selection and Android networking remain open. Backend Wellworks/Cup adapters, real competition, commerce, privacy/retention/consent and physical/FPS/long-session certification are unchanged. This is one completed review component, not activation of all launch services. No new APK build/install is claimed.

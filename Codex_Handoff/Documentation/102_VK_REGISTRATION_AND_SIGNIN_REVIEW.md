# 102 - VK registration and sign-in

**REVIEWED_WITH_OPEN_ACCEPTANCE_GATES.** The owner requested code that allows registration through
VK authentication. Registration and confirmed sign-in are implemented in the
managed app/backend path. Current native Unity checks pass 793 checks across
51 cases and 45 interface states; the four selected Russian captures have been
reviewed. The full backend rerun passes 527 tests with the approved replay
worker; identity, provider and account compatibility checks pass. The actual
Unity-to-backend HTTP flow passes 44 checks with an explicitly simulated VK
provider and a separate SQLite audit.
No live VK authorization, deployment or Android provider acceptance is claimed.
Checkpoint 101 remains the previously installed test APK; no APK or device
operation is part of this checkpoint.

`fullyVetted=false`, `taskComplete=false`, `productionApproved=false`.

[Evidence gallery](../../Verification/Evidence/Review102/Comparison.html),
[reviewed Editor image bindings](../../Verification/Evidence/Review102/Reviewed/Selection102.json),
[full backend result](../../Verification/Evidence/Review102/Backend/Full02/Service_Tests.json),
[controlled HTTP result](../../Verification/Evidence/Review102/Connected/Flow01/Report.json),
[checkpoint summary](../../Verification/Evidence/Review102/Summary.json),
[source preservation](../../Verification/Evidence/Review102/SourceDelta102.json),
[warning categories](../../Verification/Evidence/Review102/CompilerWarnings102.json).

The main project remains Unity 2022.3.62f3. The approved isolated Unity 6 project
is not promoted. Approved artwork, GUIDs, level masks, gameplay, economy and the
working checkpoint 101 startup implementation must be preserved.

## Implemented behavior

- A new VK identity registers the current managed guest without changing its
  internal player ID, wallet, inventory or progression.
- An existing VK identity prepares its existing saved journey for explicit
  confirmation. Accounts and wallets are never silently merged.
- Browser callbacks verify the provider identity and prepare a target. A fresh
  device key and a protected, signed app confirmation finish authentication.
- Cancelled, expired, repeated or interrupted operations do not grant rewards
  or silently choose a different account. Pending work is stored in a protected
  journal before HTTP/browser activity. Unknown completion outcomes remain
  recoverable; they are not treated as proof that nothing committed.
- Existing recovery codes are not rotated by VK sign-in. A device that signs
  in through VK does not receive another device's recovery code.
- An existing remote attempt requires the established recovery decision rather
  than an automatic life-loss settlement.
- An authenticated terminal result can restore the source account when no
  target credentials have been published. This includes a target deleted after
  a committed sign-in whose response was lost: a cleared server tombstone and
  revoked target family establish that the target is no longer usable. A 404,
  timeout or other unknown response never independently authorizes rollback.

This is an extension of the managed-account path. Existing local profiles are
not uploaded, overwritten or imported as authoritative server wallets. Without
an explicitly configured managed backend and VK registration, sign-in stays
unavailable and the app must explain that state accurately.

## Changed files and responsibilities

| Files | Change |
| --- | --- |
| `Backend/hotr_backend/provider_signin102.py`, `provider_signin_schema102.py` | Separate device-bound sign-in flow and additive schema-9-to-10 migration |
| `identity.py`, `identity_schemas.py`, `provider_identity.py`, `api.py`, `storage.py`, `operations.py` | Signed VK challenge/completion routing, compatible legacy callback routing, migration, snapshot/restore validation and deletion integration |
| `Backend/tests/test_vk_signin102.py` | Transaction, proof, replay, cancellation, expiry, concurrent registration/completion, deletion and migration tests |
| `Backend/tests/test_commerce_grants100.py`, `Backend/README.md` | Current-schema expectations and accurate setup/status; earlier commerce changes retained |
| `App/OnlineIdentity/Runtime/VkSigninProtocol102.cs`, `VkSigninClient102.cs`, `ManagedVkSession102.cs` | New protected flow, bounded HTTP protocol, device proof and confirmed credential publication |
| Existing `ManagedIdentitySession82.cs`, `ProtectedSessionJournal82.cs`, `IdentityHttpTransport82.cs` | Narrow partial-class hooks; existing version-1 serialized intent/credential fields remain compatible |
| `App/ServerAccount/Runtime/ServerVkSignin102.cs`, `ServerVkService102.cs`, `VkSigninUI102.cs` | Registration, explicit target selection, account ownership, safe retry/reconciliation and existing-modal controls |
| Existing account selector, service, provider/modal partials and `AccountDesign/AccountModal.cs` | VK transition integration, available recovery-code state and pinned footer actions |
| `Verification/Editor/VkSignin102Verification.cs`, `VkSignin102HttpVerification.cs` | Actual native checks and controlled loopback HTTP integration; new stable metadata retained |
| `Release/RuStore/VK_ID_SETUP.txt`, `Launch_Readiness93.md`, this review | Operator setup and current feature scope |

Unity paths in this table are relative to `Unity/Assets/HeartOfTheRain/`.
The final source delta identifies exact changed inputs and binds the preserved
artwork, existing GUIDs, gameplay/economy files and working startup Java. Against
the sealed checkpoint 101 Unity inputs, 11 existing inputs change and 16 are
added; against the unchanged checkpoint 100/101 backend baseline, eight change
and three are added. Existing metadata is not rewritten. Main settings/packages,
M46/M48, Shop/economy assets and the working Java hash remain unchanged.

## Transaction and recovery boundaries

The original link-only API retains its conflict behavior. The new authenticated
`POST /v1/identity/vk/signin` binds a request/flow ID, a fresh device public key
and a completion-secret digest to the source session family. Ordinary bearer
renewal does not change ownership. Logout, deletion and another source family
cannot reuse that pending flow.

The shared VK callback verifies the provider and prepares a fixed target. The
app then signs a `vk` challenge containing the exact target, flow proof, refresh
digest and explicit confirmation. `/v1/identity/vk/complete` registers or adopts
that target atomically. It never copies wallets or creates another genesis
reward. Lost responses reconcile the same operation and session family.

Existing encrypted version-1 identity documents retain their serialized field
shape. A separate origin-bound VK journal owns new pending proofs. The source
selection changes only after the target credential record is durably confirmed.
CAS conflicts, failed readback and unknown network results cannot silently
overwrite a different pending flow. Protected-read failures release the busy UI
while retaining the unresolved selector and proof for a retry.

VK sign-in preserves existing recovery codes. A device without the original
code stores an explicit empty backup state and disables Copy Recovery; refresh,
logout and deletion still work. It does not display or invent the old code.

The VK Ready confirmation and matching pending Resume use the existing pinned
footer. Confirmation is available only on the status page with the same target
shown in that layout. Backup and other subpages retain their original return
action and cannot confirm a hidden target.

## Verification plan and current evidence

1. Add a transactional schema-9-to-10 migration that retains existing signed
   challenges, account links, purchases and wallets.
2. Preserve the earlier link-only API. Add a separate source-session-bound VK
   flow, provider callback preparation and signed completion bound to the
   exact target shown in the confirmation.
3. Keep the existing version-1 encrypted identity documents compatible. Store
   the new flow in a separate protected journal, and confirm credentials before
   changing account selection.
4. Extend the existing Save Progress component, preserving its artwork and
   settings return path. Test disabled, pending, confirmation, failure and
   completed states in the supported languages and recorded Editor viewport.
5. Run focused backend transaction/security tests, then the full service suite
   with the already approved real replay worker after source freeze.
6. Run actual native Unity protocol, journal and account tests plus a real
   loopback HTTP integration using an explicitly simulated VK provider. Such
   tests are not evidence of real VK consent or provider acceptance.

| Run | Result and limits |
| --- | --- |
| Focused backend implementation checks | Final 27 new VK tests and 60 legacy identity/link tests passed before the full run; simulated VK HTTP, real signatures/SQLite transactions |
| `VkMain01` | Earlier 718-check native pass retained in its source epoch; visual review found the confirmation action below the initial viewport |
| `VkMain02` | PASS: 793 checks / 51 cases / 45 locale-and-phase UI states, zero reported failures/engine errors and zero selected C# warning/error lines |
| `Backend/Full01` | Retained FAIL: existing 500 tests and actual approved replay-worker integration passed, but standard discovery could not import the new test module; wrapper completion-file conflict also retained |
| `Backend/Full02` | PASS: 527 tests / zero failures, errors or skips, actual approved replay worker; inputs and worker unchanged during the run |
| Identity compatibility | PASS: 69 checks / 13 cases in the actual Editor |
| Legacy VK provider compatibility | PASS: 280 checks / 34 cases in the actual Editor |
| Account compatibility | PASS: 101 checks / 8 cases; current Editor clipboard readback matched, with no assertion waived. Earlier checkpoint93 clipboard failures remain historical evidence |
| Controlled native HTTP | PASS: 44 checks, real managed guest signatures, protected journals, loopback callback/identity routes and SQLite. Provider token/user_info calls are explicitly simulated; no browser is opened |

The independent HTTP database audit observes two players and one VK link, two
signed VK operations in two distinct VK session families, and one genesis
receipt per player. The seeded target keeps 1,387 coins and the source keeps
1,250. The 137-coin difference is an explicitly controlled operator seed, not
a VK reward. There are zero reward grants and zero attempts. Existing recovery
digests remain unchanged, terminal proofs are cleared, and provider tokens are
absent. One committed HTTP response is deliberately suppressed to verify exact
retry; a separate Ready expiry is injected to verify safe source restoration.
The original ordinary Editor profile hash is identical before and after, and
the owned local listener is closed.

The five selected native runs contain zero C# warning/error lines. No Android
build was run, so there is no new BuildReport or IL2CPP outcome. The earlier
three IL2CPP compile-cost notices and the external Starlette/httpx TestClient
deprecation are retained in their own scopes; warning removal is not claimed.

This integration does not claim an actual Android process restart, Android
Keystore, natural ten-minute wait, real VK consent, external callback hosting or
live-provider behavior. Those remain separate acceptance gates.

The four reviewed Russian states are Idle, Ready for the same account, Ready
for another account, and Completed. They are actual 720 x 1600 **Editor** UGUI
captures with synthetic profile/status data, including a deliberately synthetic
1970 timestamp. They are not phone captures, real provider consent, or real cloud
save evidence. Tablet and other viewport acceptance are not inferred from them.

Failed attempts and earlier source epochs are retained; a later pass does not
erase them. The initial implementation also exposed terminal-status target
mismatches, CAS retry ownership, stale account labels, expiry reconciliation,
and protected-read retry defects during review. Their corrections are included
in the final frozen source and relevant focused/native checks.

No APK rebuild, phone installation or live provider operation is currently
required by this code-change task. The existing checkpoint 101 phone profile
and APK will remain untouched unless a concrete verification need changes that
scope.

## Live configuration and acceptance gates

Real authorization still requires an issued VK client ID, an owned HTTPS
backend origin, and the exact registered callback
`<origin>/v1/identity/vk/callback`. Provider secrets remain server-side. Reverse
proxy and application logging must redact callback parameters and credentials.
Both `HOTR_MANAGED_IDENTITY_ENABLED` and the explicit VK configuration must be
enabled only in the intended deployed environment. See
[VK setup](../../Release/RuStore/VK_ID_SETUP.txt).

After configuration, real Android acceptance must cover consent, cancellation,
browser return, network failure, restart, duplicate callbacks, account
conflicts, logout and deletion. No production or all-device approval is implied.
Google authentication, native VK SDK integration and automatic offline-save
migration are not added. The existing checkpoint 101 brief startup flash and
broader performance/production gates remain open; that startup source is not
changed by the authentication work.

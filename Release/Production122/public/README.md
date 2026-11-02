# Public player documents

Prepared on 31 October 2026 for the existing routes:

- `https://api.novamind-it.ru/privacy`
- `https://api.novamind-it.ru/terms`
- `https://api.novamind-it.ru/support`

The owner explicitly confirmed the operator as **ИП Евсягин Алексей Валерьевич**,
country **Россия**, website **https://novamind.ru/** and the support/privacy
mailbox **info@novamind.ru**. These replace the earlier request for temporary
operator/contact wording. The website's identity/contact were checked against
its public homepage and policy; its separate website policy was not copied
into the game's documents. No email, contact form, password or payment was sent.

The three Russian documents cover the actual account, saved-game, social,
payment, ad and support behavior. The existing paper/blue presentation is kept;
small-screen text wrapping and heading size prevent horizontal overflow.
They use no JavaScript, third-party assets, cookies or submission form. Existing
Caddy CSP/no-store/noindex headers remain compatible. `publication.json` is
publication metadata, not an app/runtime configuration.

## Checks and limits

Actual local HTTP and headless Chrome pass **163 checks across nine cases**:
three documents at 320×720, 720×1600 and 1280×900. Checks cover UTF-8 identity,
contact links, document structure, navigation/fragments, viewport bounds,
absence of active third-party resources and unchanged source hashes.
Root inspected mobile/desktop captures. Evidence:
`Verification/Evidence/LegalPages20261031/Browser05/LocalBrowserChecks05.json`.
These are local browser checks, not physical Android or VPS publication tests.

The updater separately passed 23 local filesystem/guard fixtures with mocked
HTTP, plus PowerShell parsing. It has not been accepted on the live VPS merely
by those tests. Mailbox monitoring was owner-confirmed; delivery was not tested.

The privacy text discloses that a complete physical-purge schedule is not
configured. Account deletion revokes access and removes optional/social data
but retains financial/security proofs and backups. The text does not create a
retention job or establish Russian data-localization/notification compliance.
Actual hosting/processor locations, retention/purge implementation and required
operator compliance remain release work. No invented retention deadline,
unlimited consent or guarantee of immediate erasure is included.

Refund inquiries go to the confirmed mailbox. The text preserves mandatory
consumer rights and does not promise an automatic refund or account unfreeze.
The owner-approved financial correction policy and safe refund resolver remain
backend work. Provider success, production readiness and off-device signing
recovery are not implied by these documents. Production remains disabled.

## Update the existing VPS pages

The current directory on the VPS is
`C:\ProgramData\HeartOfTheRain\public-draft122`. **Do not rerun
`Install-PublicDrafts122.ps1`**: that is the initial installer, which deliberately
rejects an existing root and the later Caddy configuration.

Copy this folder to a separate staging folder on the VPS. Run the new updater
from an elevated PowerShell terminal there, using its actual absolute source
path:

```powershell
.\Update-PublicPages.ps1 -SourceDirectory (Get-Location).Path -Check
.\Update-PublicPages.ps1 -SourceDirectory (Get-Location).Path
```

`-Check` writes nothing. The update validates `publication.json`, the exact
three HTML hashes, the existing root/ACL and known old-or-already-new content.
It serializes its own invocations, binds the confirmed metadata to the HTML,
and preserves unknown newer live files found by its checks. It creates a private backup and uses
atomic replacements that preserve the service's read access. Normal TLS public
GETs must return HTTP 200 and exact new body hashes; otherwise it attempts
rollback only while the affected files still contain its own bytes.

Use an exclusive publishing window: the named mutex serializes this updater,
while checks against unrelated administrator edits are best effort rather than
an atomic exclusion of every possible foreign file writer.

The script does not change Caddy, restart services, mutate the API/database,
enable payments/ads, change the app's consent version or enable production.
Successful publication returns `pages_updated_and_verified` or
`pages_already_current_and_verified`. Preserve that receipt before claiming the
new public URLs are live. `finalPublicationReady=true` permits this static-file
update only; it does not set release acceptance.

## Factual references

- `Backend/hotr_backend/identity.py`, `identity_schema.py`, `social_deletion.py`
- `Backend/hotr_backend/storage.py`, `commerce.py`, `wallet.py`, `regions.py`
- `Backend/hotr_backend/vk_provider.py`, `provider_signin102.py`
- `Unity/Assets/HeartOfTheRain/App/Advertising/Runtime/YandexRewardedAdsProvider85.cs`
- `Unity/Assets/HeartOfTheRain/App/Advertising/Runtime/RewardedShop85.cs`
- `Release/RuStore/WindowsVps/CADDY_REQUEST_LOG_AND_CLIENT_IP128.Caddyfile.example`
- `Codex_Handoff/Documentation/128_APP_BACKEND_END_TO_END_FIXES.md`
- [Owner website](https://novamind.ru/), [website operator identity](https://novamind.ru/policy)
- [RuStore user policy](https://www.rustore.ru/help/legal/privacy-policy-users)
- [RuStore purchase/refund guidance](https://www.rustore.ru/help/users/purchases-and-returns/payment-and-subscription-management)
- [Yandex policy](https://yandex.ru/legal/confidential/ru/)
- [Yandex SDK/AppMetrica information](https://ads.yandex.com/helpcenter/en/support/faq/sdk-integration)
- [Yandex age-restricted data setting](https://ads.yandex.com/helpcenter/en/dev/android/coppa)

External policies describe the provider's processing. Dependency presence and
privacy flags alone are not proof of zero SDK processing or legal compliance.

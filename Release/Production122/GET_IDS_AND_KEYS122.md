# Owner console inputs

1. **RuStore App ID:** open the app in Console and copy the digits after
   `/apps/` in the address. Example: `/apps/123456/versions` means `123456`.
   [Official instructions](https://www.rustore.ru/help/sdk/pay/unity/history/10-2-0).
2. **VK App ID:** create/select the application in the
   [VK ID connection console](https://id.vk.ru/business/go). Copy its App ID;
   register `https://api.novamind-it.ru/v1/identity/vk/callback` as redirect.
   [Official SDK guide](https://github.com/VKCOM/vkid-web-sdk).
3. **API signing key:** RuStore Console → **Компания / Разработчик → API
   RuStore → Создать ключ**. Scope it to this app and the necessary payment
   lookup/listing methods. Save the private key and its separate key ID.
   [Official instructions](https://www.rustore.ru/help/work-with-rustore-api/api-authorization-process).
4. **Notification key:** app → **Монетизация → Уведомления на сервер →
   Подключить**. The setup supplies a separate decryption key. Keep delivery
   disabled until the receiver and sender filtering pass deployment checks.
   [Official instructions](https://www.rustore.ru/help/developers/monetization/payment-callback/enable-notifications).

These provider keys are separate from the Android release keystore. Store the
exact Console-provided values in restricted server-only files outside source,
Unity Assets, web roots, screenshots and logs. The existing readers accept the
Console API private key as Base64/PEM, and the notification key as its provided
Base64 text. Do not wrap a key in JSON or place its value in a command line.

The backend configuration uses `HOTR_RUSTORE_KEY_ID`,
`HOTR_RUSTORE_PRIVATE_KEY_FILE`, and `HOTR_RUSTORE_NOTIFICATION_KEY_FILE`.
Provide the public numeric app IDs, API key ID and file locations for setup;
keep key contents private.

The owner requested temporary pages under `https://api.novamind-it.ru`:
`/privacy`, `/support`, and `/terms`. The published HTML explicitly labels them
as drafts awaiting operator/contact facts. Their presence does not establish
approved legal content or release acceptance. No company or support email has
been invented. Actual HTTPS publication and exact response bodies were verified
from the VPS and recorded in
`Verification/Evidence/Review122/PublicPages/PublicPagesSummary122.json`.

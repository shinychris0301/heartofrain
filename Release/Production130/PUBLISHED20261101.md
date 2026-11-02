# Interstitial disclosure published

Published on 1 November 2026 with the owner's approval. The two changed routes are `https://api.novamind-it.ru/privacy` and `https://api.novamind-it.ru/terms`; `https://api.novamind-it.ru/support` retained its existing bytes.

The local candidate passed 163 Chromium checks across nine 320×720, 720×1600 and 1280×900 cases. The VPS wrapper checked the exact seven-entry source archive, source hashes, administrator context, staging health/readiness, Caddy identity, static-page ACLs and live old hashes. Its read-only preflight passed before it called the rollback-capable updater. The update changed only `privacy.html` and `terms.html`; there were no rollback or concurrent-content events. The wrapper reports Caddy unchanged and staging health/readiness passing before and after.

An independent external HTTPS check with ordinary certificate validation returned HTTP 200 and exact manifest SHA-256 for all three pages:

| Route | SHA-256 |
| --- | --- |
| `/privacy` | `03051102b571923b220c6ff7446f70393be7bd946cf6bb5aa374414258d9939a` |
| `/terms` | `3f1e41b5e2ecbbc34c0441bf0c1823b15056ffce9739688f207d01941bedbf70` |
| `/support` | `7958442598840152ebc5f516aaa7843bac5f5ca6258d0d75e00ea619e8da0849` |

Backend `/healthz` still reports `mode:staging, productionEnabled:false`; `/readyz` reports `ready`. The updater's VPS backup is `C:\ProgramData\HeartOfTheRain\public-pages-backup-d9f98f4568f64b0f87b671b0ac929487`. The sanitized remote receipt, local browser result and private package are under `.verification-cache/Review130/Publication`. No backend, Caddy, account, payment or ad configuration was deployed by this page update.

This publication is not a legal-compliance or production-readiness certification. Retention/purge, hosting/processor review, refund resolution, live provider testing and a guarded signed APK remain open.

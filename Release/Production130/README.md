# Candidate player-document revision

The published 31 October edition remains in `Release/Production122/public`. The owner approved this revision on 1 November 2026. It discloses the new pre-level interstitial in the privacy policy and terms while retaining the existing support page. The manifest pins the three HTML files; `publication.json` permits static-page publication only.

`public/Update-PublicPages130.ps1` accepts only the exact published 31 October hashes or the new hashes. It passed the VPS read-only preflight and published Privacy and Terms on 1 November 2026; Support was already identical. Independent normal-TLS HTTPS checks matched all three new manifest hashes. The earlier updater is pinned to the initial draft hashes and must not be reused for this revision. See `PUBLISHED20261101.md`.

`advertising.review.json` binds the two approved Yandex placement IDs to the published `/privacy` route and this 1 November policy edition. It is a prepared input for an isolated SDK build; the ordinary Unity project's advertising resource remains disabled. Publishing the pages alone does not activate ads.

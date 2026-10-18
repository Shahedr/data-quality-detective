# Data Quality Detective SaaS — launch readiness

STATUS: PUBLIC SAMPLE DEMO, CUSTOM ADMIN REMOVED. USE THE SUPABASE PROJECT DASHBOARD FOR OPERATOR OVERSIGHT. CUSTOMER UPLOADS, PUBLIC SAAS SIGNUPS AND CHARGES MUST REMAIN DISABLED UNTIL VERIFIED AND APPROVED.

## Simplified operator workflow (2026-10-18)
- The duplicate web-based `/admin` dashboard and browser-accessible owner statistics RPC have been **retired**, including their custom database table and PostgreSQL function. Use the [Supabase project dashboard](https://supabase.com/dashboard/project/uphktngpdrjsnfnveaio) to inspect Auth users, tables, SQL, security advisors and project performance instead. Your existing Supabase Auth user and its MFA factor were NOT deleted.
- The four existing internal SaaS tables remain RLS protected. The public sample-only application and commercial feature flags are unchanged.
- Stripe live merchant account was read-only checked: individual US account for the DQD domain; `charges_enabled=false`, `payouts_enabled=false`, `details_submitted=false`, business support email not configured. Do not assume a connected live account means activated merchant status or readiness for charges.
- Permanent `production-safety-smoke.yml` requires `/admin`, `/admin.js`, `/api/saas/admin/config`, `/api/saas/admin/overview` to remain 404, and all public/private upload and billing gates remain closed.
- Vercel Git-source issue #17 was fixed by adding required Python imports to `pyproject.toml`. Production requires strict JSON smoke verification after new deployments.

## Live Stripe protection
- Application supports `sk_test_` Stripe keys for **future isolated test-mode integration only**. It does not charge or contact Stripe until separately approved customer endpoints are activated.
- A `sk_live_` key **cannot** make customer SaaS ready unless all four independently controlled variables are `1`: `DQD_SAAS_ENABLED`, `DQD_SAAS_LAUNCH_APPROVED`, `DQD_NEW_STRIPE_ACCOUNT_VERIFIED`, and `DQD_LIVE_PAYMENTS_APPROVED`. Do not set any of these to `1` until identity, legal and end-to-end security testing passes.
- Verify via the actual new Stripe **business** account, not the user's unrelated historical merchant. Confirm test-mode account identity, configured price and webhook signing key under private provider settings. Do not send keys through chat/GitHub.
- Merchant approval and the correct price cannot be inferred from a connected Stripe app alone.

## Current legal and merchant prerequisites (official sources; not legal advice)
- Stripe's [merchant website checklist](https://support.stripe.com/embedded-connect/questions/information-required-on-your-business-website-to-process-payments) calls for a complete product description, **transaction currency**, **support contact details**, **refund/return policies**, applicable legal restrictions, a privacy notice and payment-card security information. The demo is descriptive but **does not yet meet all merchant-facing disclosures** because the actual operator and policy decisions are not finalized.
- Federal recurring-subscription rules must be researched by applicable jurisdiction. The [March 2026 Federal Register record](https://www.govinfo.gov/content/pkg/FR-2026-03-13/html/2026-04952.htm) confirms the 2024 FTC amended negative-option/“click-to-cancel” rule was **vacated on July 8, 2025**. Do not describe the vacated amendment as currently enforceable. Other federal statutes (including ROSCA), existing rules and relevant state automatic-renewal laws still require counsel review for disclosures, consent and cancellation.
- The [USPTO requires a comprehensive confusing-similarity and common-law clearance search](https://www.uspto.gov/trademarks/search/comprehensive-clearance-search-similar-trademarks) before committing to a commercial brand. User screenshots identified a live DATA DETECTIVE filing/registration and another CSV analyzer displaying the exact Data Quality Detective name. They are risk leads, **not proof of trademark infringement or senior rights**. Branding is on HOLD for commercial rollout until owner selects a candidate and clearance is reviewed.
- Privacy and terms pages are correctly labeled *draft*. A complete retention/processor/log review and actual legal owner, monitored support, refunds and cancellation policy are needed before customers can subscribe.
- Stripe's [own subscription policy](https://stripe.com/legal/subscription-policy) governs Stripe's fees to its users; **do not copy it as Data Quality Detective's customer subscription agreement**.

## Mandatory release checklist

- [ ] Complete true operator identity, address, privacy contact, payment cancellation and refund terms. Replace draft Privacy and Terms informational pages with legal-review-approved contracts.
- [ ] Search federal, state, common-law and relevant international trademarks for exact and similar brands, and complete professional IP clearance.
- [ ] Audit all pinned runtime and browser dependencies, licenses, notices and security advisories; produce license inventory from deployed lockfile.
- [ ] Sign or evaluate Supabase, Stripe and Vercel data-processing agreements; document locations, subprocessors, log retention, backups, breach response and legal rights.
- [ ] Independent security assessment of unauthenticated multipart spooling, edge/proxy request size limits, zip bombs, CPU/memory concurrency, isolation, timeouts and malicious workbooks. A 2 MiB application read cap alone does not enforce a front-proxy limit.
- [ ] Use real Supabase credentials in a staging environment to validate signups, confirmation, JWT signature, expiry, forged tokens, cross-account access and delete workflow.
- [ ] Use Stripe TEST keys to validate signup → checkout → signed webhook → Pro entitlement → invoices, cancellations, disputes, failed payments and replay/out-of-order delivery.
- [ ] Exercise direct PostgreSQL with schema permissions, backups, row-lock quota concurrency and deletion. Verify no spreadsheet contents, filenames or secret credentials enter application logs.
- [ ] Conduct adversarial file tests plus load/security testing and validate public demo still rejects uploads.
- [ ] Approve the privacy notice and legal terms, company details, domain and support processes before enabling either launch flag.

## Important current behavior

Free is limited to 10 monthly analysis attempts; Pro to 500. Daily authenticated API request cap is 600. Failures after metering can still count. Uploaded content is parsed per request and is not intentionally saved in the SaaS database. Multipart parsing may spool to ephemeral disk. Downloaded reports include source data and sometimes hidden worksheets. Supabase retains identity records separately; Stripe retains billing records under its own obligations. DQD-only account deletion does not delete these provider records.

Only the separate Windows desktop app can run explicitly approved VBA; the web SaaS never executes macros. The private-beta foundation does not represent SOC2/HIPAA/GDPR certification, full data processing agreements, or a cleared brand. An installed ChatGPT Supabase integration by itself does not provision production environment variables or validate the SaaS.

Do not advertise a fully production-ready commercial application until every above item is complete.
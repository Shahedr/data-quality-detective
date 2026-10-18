# Data Quality Detective SaaS — launch readiness

STATUS: PUBLIC SAMPLE DEMO + MFA-ONLY PRIVATE OWNER DASHBOARD LIVE. CUSTOMER UPLOADS, PUBLIC SAAS SIGNUPS AND CHARGES MUST REMAIN DISABLED UNTIL APPROVED.

## Verified deployment and owner access (2026-10-18)
- PR #24 fixed missing FastAPI dependency in Vercel Git-source builds; issue #17 is closed following strict full-application preview tests.
- PR #25 added a Supabase MFA-gated aggregate dashboard. One identity (verified Auth email with enrolled TOTP) is allowlisted in a `private` schema, and browser roles cannot read any internal tables. Function rejects unauthenticated, non-owner and non-MFA calls.
- PR #26 added a permanent production public-demo safety smoke. The first run revealed the public alias was still pinned to an old direct deployment; its failure was genuine. The alias was intentionally reassigned to a verified Git-source production deployment and the original failed run was rerun successfully. Separate public-alias GitHub smoke also passed.
- Public domain `https://data-quality-detective-demo.vercel.app` now serves owner `/admin` with aggregate counts while sample-only public endpoints remain closed to uploaded files and paid checkout. Real-browser MFA owner RPC still requires owner sign-in on this origin; SQL-editor synthetic JWT tests are not a substitute.
- Vercel `DQD_SAAS_ENABLED=0` and `DQD_SAAS_LAUNCH_APPROVED=0` were independently checked before enabling only admin flags. Uploaded customer files and payments remain disabled.
- Supabase security advisor warning on the deliberate owner SECDEF RPC is documented in `saas/OWNER_DASHBOARD_SECURITY.md`. Leaked-password protection remains a real separate **WARN** and requires Auth configuration evaluation.
- Stripe's connected merchant identity and environment have NOT been inspected yet; do not assume a linked or historical merchant belongs to this product.


The public sample demo remains a separate upload-free product. The new SaaS endpoints require authentication and two independent environment flags (DQD_SAAS_ENABLED and DQD_SAAS_LAUNCH_APPROVED). Missing required configuration fails closed.

## Provider provisioning (never commit secrets)

1. Supabase: create a project, enable confirmed-email authentication using asymmetric RS256 or ES256 JWT keys, configure exact HTTPS redirect origin. Run the SQL in saas/schema.sql through an authorized SQL editor, confirm RLS, no anon grants, TLS and backup policy. Use a limited-privilege direct PostgreSQL account for the server.
2. Stripe: create a recurring Pro subscription product/price, configure customer portal and webhook for checkout.session.completed, customer.subscription.created, customer.subscription.updated, customer.subscription.deleted. Perform test-mode checkout, cancellation, failed payment, event replay and entitlement tests. Use signed webhooks. Do not turn on live charges without explicit operator approval.
3. Vercel: build from root app.py using FastAPI; core `pyproject.toml` dependencies now include web startup packages to satisfy Git-source Python runtime. Preview and production smoke tests reject placeholder HTML and require real app JSON. Keep all secrets in project environment variables and never in git or client code.

Required environment variables: DQD_SAAS_ENABLED=0; DQD_SAAS_LAUNCH_APPROVED=0; DQD_NEW_STRIPE_ACCOUNT_VERIFIED unset/0; DQD_LIVE_PAYMENTS_APPROVED unset/0; SUPABASE_URL; SUPABASE_ANON_KEY (public); DQD_SAAS_DATABASE_URL (private, sslmode=require); STRIPE_SECRET_KEY; STRIPE_WEBHOOK_SECRET; STRIPE_PRO_PRICE_ID; DQD_SITE_URL (HTTPS); DQD_LEGAL_ENTITY (real registered operator); DQD_PRIVACY_EMAIL (monitored contact).

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
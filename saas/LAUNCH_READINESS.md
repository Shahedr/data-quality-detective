# Data Quality Detective SaaS — launch readiness

STATUS: PRIVATE-BETA SOURCE CODE. CUSTOMER UPLOADS AND CHARGES MUST REMAIN DISABLED UNTIL APPROVED.

The public sample demo remains a separate upload-free product. The new SaaS endpoints require authentication and two independent environment flags (DQD_SAAS_ENABLED and DQD_SAAS_LAUNCH_APPROVED). Missing required configuration fails closed.

## Provider provisioning (never commit secrets)

1. Supabase: create a project, enable confirmed-email authentication using asymmetric RS256 or ES256 JWT keys, configure exact HTTPS redirect origin. Run the SQL in saas/schema.sql through an authorized SQL editor, confirm RLS, no anon grants, TLS and backup policy. Use a limited-privilege direct PostgreSQL account for the server.
2. Stripe: create a recurring Pro subscription product/price, configure customer portal and webhook for checkout.session.completed, customer.subscription.created, customer.subscription.updated, customer.subscription.deleted. Perform test-mode checkout, cancellation, failed payment, event replay and entitlement tests. Use signed webhooks. Do not turn on live charges without explicit operator approval.
3. Vercel: build from root app.py using FastAPI and install Python with [web,saas]. Keep all secrets in project environment variables and never in git or client code.

Required environment variables: DQD_SAAS_ENABLED=0; DQD_SAAS_LAUNCH_APPROVED=0; SUPABASE_URL; SUPABASE_ANON_KEY (public); DQD_SAAS_DATABASE_URL (private, sslmode=require); STRIPE_SECRET_KEY; STRIPE_WEBHOOK_SECRET; STRIPE_PRO_PRICE_ID; DQD_SITE_URL (HTTPS); DQD_LEGAL_ENTITY (real registered operator); DQD_PRIVACY_EMAIL (monitored contact).

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
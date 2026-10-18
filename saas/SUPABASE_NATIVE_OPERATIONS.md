# Supabase-native operations guide — Data Quality Detective

Last checked: 2026-10-18. The separate website admin dashboard has been retired on purpose.

## Where data is kept
- [Supabase Auth Users](https://supabase.com/dashboard/project/uphktngpdrjsnfnveaio/auth/users): login emails, password verification, user identities, sessions and MFA factors. **Supabase Auth** manages these; they are separate from app usage tables.
- [Supabase Table Editor](https://supabase.com/dashboard/project/uphktngpdrjsnfnveaio/editor): four RLS-restricted tables:
  - `public.saas_accounts`: account UUID, Stripe customer/subscription IDs, subscription status.
  - `public.saas_daily_usage`: UUID, UTC day, request counts.
  - `public.saas_monthly_usage`: UUID, month, analysis counts.
  - `public.saas_stripe_events`: event IDs for webhook deduplication.
- [Supabase SQL Editor](https://supabase.com/dashboard/project/uphktngpdrjsnfnveaio/sql/new): trusted operator SQL access. Do not copy user IDs, emails, access tokens, or private spreadsheet data to public issues.
- [Supabase Storage](https://supabase.com/dashboard/project/uphktngpdrjsnfnveaio/storage/buckets): currently no customer-upload storage is provisioned/used by the application. Check provider logs/ephemeral request processing separately.
- [Stripe Dashboard](https://dashboard.stripe.com/): Stripe stores future customer billing records, payment methods and invoices. App database should keep only Stripe references and entitlements. Never copy payment-card details into DQD.
- [Vercel](https://vercel.com/shahedr2744-1751/data-quality-detective-demo): runs the sample-only web application; HTTP traffic may appear in provider request/function logs even though file content isn't intended to be persisted in app tables.

## What the app does and doesn't store
The public demonstration loads a bundled fictional dataset and refuses real user-file uploads. Future approved SaaS uploads would flow through HTTPS to Vercel for ephemeral processing and returned reports. The SaaS table schema has **no file bytes, cell values, or filenames columns**. This does **not** establish that hosting/CDN, error monitoring, tmp files, generated reports, backups, user devices or Supabase/Stripe provider logs retain nothing. Verify retention before offering customer uploads.

## Owner/admin operations
Use the Supabase dashboard itself for administration. Your existing identity and authenticator remain managed by Supabase; the app no longer offers a parallel `/admin` login, client-side admin SDK, or privileged aggregate RPC. The temporary private allowlist and owner stats function were retired in migration `retire_redundant_owner_dashboard_rpc`; four SaaS data tables remain unchanged.

Avoid creating SQL policies or browser grants for the four tables merely to make them visible in a consumer app. Administrative access uses Supabase project member permissions.

## Stripe merchant verification (read-only connection)
Connected US individual Stripe account is named for the current project website. As of the check, `details_submitted=false`, `charges_enabled=false`, `payouts_enabled=false`; **zero live products and zero live prices**. Missing customer-facing support contact. Stripe reports outstanding payout account, payment descriptor and Terms-of-Service acceptance requirements. The **account owner** must complete legal acceptance, payout/bank information, and actual merchant onboarding in Stripe securely; don't send financial documents into this repository/chat. No payment readiness is implied by the connector alone.

The app requires `DQD_SAAS_ENABLED=1` AND `DQD_SAAS_LAUNCH_APPROVED=1`; with a live Stripe key it additionally requires `DQD_NEW_STRIPE_ACCOUNT_VERIFIED=1` and `DQD_LIVE_PAYMENTS_APPROVED=1`. Currently no such commercial activation is approved.

## Launch operations still outstanding
1. Actual service operator/business identity, usable support contact, service name trademark clearance.
2. Real recurring plan price/currency, billing cadence, tax treatment, refund/cancellation policy; legally reviewed Privacy and Terms.
3. Stripe account activation, test-mode product, signed webhook, test subscription lifecycle and customer portal verified. Never test the flow with real charges.
4. Least-privileged server DB user, environment secrets, authentication/signup/tenant checks, adversarial file/load tests, request-size enforcement, retention/backups/recovery and incident-response runbook.
5. Resolve Supabase Auth security advisor on leaked-password protection or document a supported alternative and the reason.
6. Approve final go/no-go checklist **before** enabling live accounts, uploads, or payments.

The one-hour engineering target does not override third-party identity checks or legal clearance.

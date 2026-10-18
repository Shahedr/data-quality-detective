# Supabase staging project provisioning

Date: 2026-10-18 UTC. Status: database provisioned, NOT open for customer file uploads, charges, or private beta.

- Supabase project: `data-quality-detective`
- Project reference: `uphktngpdrjsnfnveaio`
- Organization: `shahed's Org`
- Region: `us-east-2` (US East, Ohio)
- Supabase organization plan: Free; quoted incremental project cost at creation: USD $0/month. Usage beyond free allowances or future plan changes are subject to provider terms.
- API origin: `https://uphktngpdrjsnfnveaio.supabase.co` (public identifier; not a secret).
- SQL migration applied: `saas/schema.sql`, migration name `create_private_saas_tables`.
- Tables: `saas_accounts`, `saas_daily_usage`, `saas_monthly_usage`, `saas_stripe_events`.
- Supabase live verification: all 4 tables exist, have RLS enabled, are empty, and `anon` and `authenticated` have **no SELECT/INSERT/UPDATE/DELETE grants**.
- Security advisor: four **INFO** findings for `RLS enabled with no policy`; this is intentional because client roles must not access internal tables (server uses restricted PostgreSQL connection). Performance advisor returned no findings.
- Vercel environment variables created: `DQD_SAAS_ENABLED=0`, `DQD_SAAS_LAUNCH_APPROVED=0`, and public `SUPABASE_URL`. Both flags remain zero by design.

## Still not configured/verified

- Supabase Auth email templates, redirect URLs, asymmetric signing key algorithm, test sign-in and session expiration.
- Least-privilege direct PostgreSQL service user and server-side connection string secured as Vercel secret.
- Supabase publishable key provisioning to runtime, if and only if needed for approved private staging.
- Stripe new business account authorization/test-mode keys, recurring price, cancellation portal and signed webhook delivery. Never use legacy DoorDash account authorization as a substitute for the actual product merchant account.
- Privacy/terms legal review, business legal name, support address, refund/cancellation rules, trademark/IP clearance, and security/load testing.

Never put API secret keys, database passwords, Stripe tokens, customer email addresses or spreadsheet values in GitHub issues, docs or the frontend. Re-evaluate the project cost before upgrading the plan.
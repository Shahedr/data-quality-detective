# Actual data flow, storage and owner access — verified 2026-10-18

## Confirmed live Supabase project (read-only checks)
Project `uphktngpdrjsnfnveaio`, region `us-east-2` (Ohio), status ACTIVE_HEALTHY. Read-only SQL returned **0 Auth users**, **0 DQD accounts**, **0 Supabase Storage objects**. All four app tables are empty and have RLS enabled, with no browser-role grants; advisor reports only informational `rls_enabled_no_policy` warnings. Thus no personal admin user exists *in Supabase Auth* yet. This does **not** establish whether the user has separate Supabase dashboard/organization admin access (they can access the dashboard to view/maintain project).

## Records by location
| Type | Processing/storage | Design and verified gaps |
|---|---|---|
| Browser login email, identity, sessions, MFA | Supabase Auth `auth.users`, `auth.identities`, `auth.sessions`, MFA tables | Managed by Supabase; **separate** from `saas_accounts` |
| Customer app entitlement | Supabase PostgreSQL `public.saas_accounts` | User UUID, Stripe customer/subscription IDs, status; **no email or workbook bytes** |
| Monthly/daily counters | Supabase `public.saas_monthly_usage`, `public.saas_daily_usage` | UUID, date, counts |
| Stripe delivery deduplication | Supabase `public.saas_stripe_events` | Stripe event ID, timestamp |
| Customer CSV/XLSX/XLSM (when privately opened) | HTTPS to Vercel FastAPI, parse and return | No deliberate permanent app-table/storage copy, but multipart may spool to ephemeral disk; provider/CDN/log/backups *not verified*. |
| Reports | Created server-side, downloaded in browser | Reports may include all source data and hidden Excel sheets; customer device retains downloads |
| Credit cards/invoices | Stripe | Do not store card PAN in DQD; Stripe billing/deletion governed separately |
| Public demo | Vercel serving bundled fictional sample | Real file upload paths blocked; hosting metadata may still be logged |

## Your private admin access
A read-only `/admin` console is prepared in the **feature branch only**. It requires *all* of these before it can serve metrics:
1. A real Supabase Auth user identity created through Supabase, email verified, and **MFA/TOTP enrolled**.
2. The user's immutable Auth UUID obtained securely from the dashboard (never use email as authorization or publish UUID as client-facing configuration).
3. `DQD_ADMIN_ENABLED=1` and `DQD_ADMIN_USER_ID=<real verified UUID>` configured as **private** Vercel environment values; `SUPABASE_URL` and a public publishable/anon key, and a least-privilege **read-only** Postgres URL with SELECT on **only** needed aggregate tables.
4. Real project access in Vercel, correct origin/redirect settings, SDK/browser test, and an end-to-end admin MFA + unauthorized user test.

**Important:** `DQD_ADMIN_ENABLED` is *independent* from `DQD_SAAS_ENABLED` and `DQD_SAAS_LAUNCH_APPROVED`. Configuring the read-only console **must not** activate customer uploads, registration or payments.

The current connector can list Vercel project metadata but project API, deployments and runtime logs still return **403 Forbidden** for project `prj_Sg3Mp98CqwhrMkifYE8xpEvOTsNb`, team `team_fpkpstoAtIC83mU0VIu7nsiS`. This is a genuine access blocker; no flags/credentials have been changed and no personal admin login has been provisioned.

## Security status
- Verified: public upload fail-closed tests; automated JWT, Stripe signature, quota tests and private RLS configuration.
- To independently verify: entire real Supabase auth lifecycle, session/MFA handling, least-privilege Postgres role, end-to-end tenant separation, real Stripe test lifecycle, Vercel ingress streamed upload size limits, zip decompression/timeouts, abuse/load tests, privacy log/retention behavior, incident response, backups and restore, browser SDK integrity, access revocation.
- Current known unresolved **Git-source** Vercel failure in GitHub issue #17 prevents reliable Git-based deployment; direct pinned workaround is not equivalent to a solved source pipeline.
- Commercial launch signoff **NO**. No source code patch alone makes a cloud service production secure.

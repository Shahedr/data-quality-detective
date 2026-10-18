# Owner-only operational dashboard — deployment and security verification

**Implemented:** 2026-10-18. **Commercial launch:** NOT CLEARED.

## Why this design
The owner dashboard needs aggregate usage and account metrics, not full customer data. A single PostgreSQL login/password in Vercel could expose all SaaS tables if leaked. Instead `public.dqd_owner_overview()` is a **least-data** SQL function called over Supabase's PostgREST API with the **already signed-in** user's Supabase Auth JWT. No raw PostgreSQL password, Stripe secret, or Supabase service-role key is ever sent to the browser or added to Vercel for this feature.

## Security conditions (enforced inside PostgreSQL, not only in JavaScript)
1. Caller must have a **signed and validated Supabase Auth JWT** presented to the Supabase REST gateway. App's public publishable key alone does not authenticate a user.
2. JWT must contain a valid `sub` matching a UUID in `private.dqd_admin_owners`.
3. JWT must contain `aal=aal2`, established when the owner completes a verified authenticator-factor challenge.
4. Function executes only after **all** checks. It returns **counts and coarse UTC time series only**, no raw rows, emails, identifiers, customer files, filenames, IPs or individual payments.
5. `private` schema and allowlist are not readable by browser roles. Four internal SaaS tables continue to deny SELECT/INSERT/UPDATE/DELETE for `anon` and `authenticated`. Only `authenticated` has EXECUTE on this one narrowly scoped function; `PUBLIC` and `anon` do not.
6. SQL `SECURITY DEFINER SET search_path=''` and schema-qualified references minimize object-shadowing risk. SQL code does not contain arbitrary commands, inputs or dynamic SQL.
7. Client UI enables its dashboard only when `DQD_ADMIN_METRICS_RPC_ENABLED=1` (initially preview-only); the database function's checks still protect it even if someone manually invokes the RPC without the UI.
8. Owner setup and dashboard remain independent of `DQD_SAAS_ENABLED` and `DQD_SAAS_LAUNCH_APPROVED`; both commercial switches must remain `0`.

## Deployment and database verification
- Migration: `saas/owner_dashboard_rpc.sql`, applied through Supabase migration API as `create_owner_mfa_readonly_overview`.
- Allowlisted identity provisioned directly from a **confirmed email plus verified MFA** using an authenticated Supabase SQL operation; its UUID is not committed to GitHub.
- Live grant inspection: `anon_can_execute=false`, `user_can_execute=true`, no browser schema access, no authenticated SELECT on allowlist, SQL function is SECDEF.
- SQL editor impersonation test (not a full real-browser JWT test): denied owner JWT with `aal1`, denied unknown UUID with `aal2`, returned correct aggregate schema for allowlisted owner with simulated `aal2`. Zero SaaS accounts, 7 daily entries, 6 monthly entries. This tests function policy logic, **not** Supabase's actual token signature verification; that requires authenticated browser test.
- UI: read-only counts, UTC daily and monthly activity, and sign-out. No upload, billing or delete buttons.

## Security advisor findings (must not dismiss as a clean bill of health)
- [WARN signed-in users can invoke a SECURITY DEFINER function](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable). **Intentional and reviewed in this design**: a signed-in role is allowed to call this exact function so *it* can compare signed caller UUID and `aal2` against private table, then reject everyone else. The warning is a real reminder to maintain strict ownership checks and minimal return scope, not evidence everyone can read the metrics.
- [INFO RLS enabled but no policy](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy) for five internal tables. **Intentional**: these data tables must not be queryable by browser roles. No browser policies/grants should be added for convenience.
- [WARN leaked password protection disabled](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection). **Open**: enable in Supabase Authentication configuration if the plan provides it, verify result through the advisor; otherwise document supported alternative and account protections. Do not claim it has been enabled.

## Production acceptance not yet covered by SQL editor simulation
- End-to-end real JWT `aal2` dashboard fetch in a browser; verify expired JWT, `aal1`/non-owner sessions, sign-out, and direct `/rest/v1/rpc/dqd_owner_overview` access denied without token.
- Confirm preview config returns enabled for admin and disabled for SaaS, and production alias stays sample-only until reviewed.
- Audit cookie/session storage, third-party Supabase JS script integrity, key rotation, and Vercel/Supabase request logs and retention.
- Create incident response, operator support/retention/deletion workflows and security backup plan before any customer launch.
- Actual Stripe test account integration, business identity, compliant policy pages and name clearance remain external dependencies.

## No secrets in repo
Do not commit service-role secrets, raw PostgreSQL passwords, Stripe secret keys, or personal MFA recovery codes. Supabase publishable key is intentionally public; the owner allowlist table and JWT are the enforcement boundary.

**Release decision:** Owner private dashboard may be tested on an isolated preview; commercial SaaS must remain closed.

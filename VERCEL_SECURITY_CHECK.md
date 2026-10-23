# Vercel public deployment check — 2026-10-23

Target: https://data-quality-detective-demo.vercel.app/

## Signed-in dashboard follow-up

After the owner signed in, the dashboard confirmed Firewall is active, All
systems normal, System Mitigations Active, no system bypasses, and initially zero
custom rules. Bot Protection was Off. The OWASP Core Ruleset was shown as an
Enterprise offering; no upgrade or paid feature was selected. BotID Basic being
selected in the dashboard is not proof of application SDK integration.

Published and reopened this rule to verify saved configuration:

- Name: Limit API request bursts
- ID: rule_limit_api_request_bursts_spMMsh
- Request Path starts with /api/
- Fixed window: 120 requests per 60 seconds, keyed by IP address
- Action: Too Many Requests (429)
- The staged-change review was explicitly published and disappeared afterward.

Normal-access smoke checks after publication: homepage 200, configuration 200,
and a fictional two-row CSV analysis 200 with the expected two rows/two columns.
No deliberate threshold-exceeding load test was performed. This is a per-IP
burst guard, not a global concurrency/resource guarantee; users sharing an IP
share the quota. Rollback: disable this specific rule and publish the change.

The application deployment itself, subscription plan, broad bot challenges and
managed OWASP paid ruleset were not changed. The stricter local application
changes still await release review/deployment. Evidence:
reports/vercel-after-firewall-smoke.json and ../vercel-rate-limit.png.

## Earlier read-only checks and connector limitation

Read-only public checks confirmed:

- Homepage and configuration return HTTP 200 over certificate-verified HTTPS.
- Homepage HSTS: max-age=63072000; includeSubDomains; preload.
  This header does not independently establish inclusion in a browser preload list.
- Homepage provides Content-Security-Policy, X-Content-Type-Options: nosniff,
  X-Frame-Options: DENY, Referrer-Policy: no-referrer and Cache-Control: no-store.
- Configuration reports free_web, uploads allowed, 4 MiB upload limit and no
  web macro execution. These are server-reported settings, not an adversarial test.
- /.git/config returns 404.

Outstanding differences from the isolated MVP:

- Live homepage CSP still allows unsafe-inline scripts.
- /openapi.json is still accessible (HTTP 200). A schema is not inherently a
  vulnerability, but the local version intentionally disables it.
- The stricter local code has not been deployed. No release was performed here.

Private configuration inspection was blocked: the Vercel connector returned 403
for the known project/team when requesting project and active firewall settings.
Its suggested team-authorization tool is unavailable in this session. Browser
fallback reached Vercel's login page; the owner was asked to sign in.

At that earlier point no setting had changed; the signed-in follow-up above
supersedes the firewall/rate-limit portion of that status. Deployment protection
and other plan-specific entitlements remain unverified. No Vercel security
certification or application-level compliance claim is supported by this check.

Evidence: reports/vercel-live-check.json and reports/vercel-tls-check.json.

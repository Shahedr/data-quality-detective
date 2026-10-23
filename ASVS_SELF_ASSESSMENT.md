# OWASP ASVS self-assessment — 2026-10-23

## Result and scope

This is an AI-assisted self-assessment of the isolated free-workspace MVP source,
not a certification, human penetration test, or assertion of ASVS level compliance.
The live website is unchanged. No paid service was purchased.

Baseline: [OWASP ASVS 5.0.0 stable release](https://asvs.owasp.org/),
with versioned requirement identifiers. The companion
`ASVS_SELF_ASSESSMENT.csv` inventories all 345 requirements, including their level,
individual status and evidence or gap. Requirement text comes from the official
[versioned CSV](https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.csv),
copyright OWASP contributors, licensed CC BY-SA 4.0. Preserve that attribution
when redistributing the matrix.

The assessment focuses on applicable Level 1 controls and selected Level 2/3
controls important for hostile spreadsheet input. Higher-level requirements
without sufficient evidence remain explicitly Needs verification. Not applicable
means a feature is absent, not that an implementation passed testing. Verified
locally is limited to the cited source and tests, not the final hosted environment.

Level 1 disposition: 32 verified locally, 30 not applicable, 5 partial, and 3
requiring deployment verification. Across all levels: 50 verified locally, 119
not applicable, 9 partial, 8 known gaps, 3 requiring deployment verification and
156 needing further requirement-specific verification. This is deliberately not
a full ASVS pass claim; an inventory entry is not evidence of compliance.

## Trust boundaries and authorization

- Anonymous public users may analyze only the data supplied in their request;
  there are no accounts, shared saved reports, administrative web roles or public
  database connections. No authentication certificate is implied by anonymous use.
- Local large-file routes require loopback client/Host, validated browser Origin
  on mutations and a per-upload random 256-bit capability checked by the backend.
  The capability grants access only to its upload/result and must not be shared.
  Tokens are transmitted in headers or POST bodies, not query strings.
- Public upload limit is 4 MiB; the detailed local limit is 10 MiB. The separate
  local streaming workflow accepts at most 1 GiB and one pending job. It must not
  be exposed through a public bind, tunnel or reverse proxy.
- Web uploads never execute VBA, formulas or external workbook connections.
  The separate supervised Excel utility is outside the public web boundary.

## Changes made during this assessment

- Moved the main inline JavaScript into a same-origin static asset so the page
  can enforce script-src 'self' without unsafe-inline executable scripts.
- Applied base-uri/object/frame restrictions to every response, including error
  and privacy responses; added same-origin opener protection.
- Added a one-year HSTS header in Vercel mode only. Local HTTP does not set HSTS.
- Disabled the automatically generated OpenAPI endpoint alongside existing
  disabled interactive documentation.
- Added browser/header/internal-path regression tests and updated tests for the
  external script and owner-provided contact details.

Inline styles remain allowed; this is not a nonce-based Level 3 CSP. Generated
reports and preserved workbooks are not declarations that their contents are safe.

## Evidence

- Full test run includes isolated PostgreSQL with a runner that fails on skips.
  Result: 179 passed, no skips, 20 dependency deprecation warnings.
  See `reports/asvs-suite.log` for the final result.
- Bandit scan: zero findings in webapp and dqdetect;
  `reports/asvs-bandit.json`.
- pip-audit on 2026-10-23: 37 installed application runtime distributions,
  no known vulnerabilities; `reports/asvs-runtime-audit.json` and the runtime
  inventory. Scanner/build tools are outside this runtime inventory.
- Browser check after CSP changes: example CSV analysis completed, workspace
  appeared, dark theme toggled, no browser error logs observed. Evidence image
  is saved beside the clone as `asvs-browser-check.png`.
- Prior real Excel/VBA fixture and 1 GiB HTTP export checks are recorded in
  `LOCAL_SECURITY_REVIEW.md`; they were not repeated as part of the header change.

## Open risks and release gates

1. **Hosted abuse controls:** input limits alone do not stop repeated expensive
   requests. Verify Vercel firewall/rate controls and concurrency/resource limits
   on a preview deployment before public promotion. A process-local limiter
   would not provide a reliable distributed quota, so none is claimed.
2. **Malicious preserved content:** there is no complete antivirus scan. Macro
   preservation can preserve malicious VBA, links or other workbook content.
   Never enable macros from untrusted files. Original and cleaned copies require
   the same trust decision. Do not claim ASVS 5.4.3 compliance.
3. **CSV formula interpretation:** exact-preservation CSV output may contain
   formula-like text interpreted by spreadsheet software. Existing export notice
   warns about this. Automatically adding apostrophes changes data and has not
   been silently introduced. ASVS 1.2.10 remains a gap; generated audit XLSX uses
   literal string cells instead.
4. **Metadata preservation:** workbook metadata is intentionally retained to meet
   the preservation requirement. This is not a metadata-scrubbing service.
5. **Operations:** provider retention, protected security logs, alerting, incident
   handling, least-privilege deployment identity, TLS and deployed headers need
   actual environment evidence. The privacy page remains a draft; operator Shahed
   and shahed2338@gmail.com are supplied but mail delivery is unverified.
6. **Assurance:** higher-level controls without individual proof remain open.
   No ASVS level, human certification, malware-free claim or zero-risk guarantee
   may be advertised from this report.

## Maintenance and response policy

Before release and after dependency/security changes, refresh the runtime
inventory and vulnerability scan and rerun the relevant tests. Proposed patch
targets are: exploitable critical findings block release and trigger disabling
public uploads; high within 7 days, medium within 30 days, low within 90 days.
If a deadline cannot be met, document the exception and mitigation rather than
claiming compliance. The owner must arrange ongoing advisory monitoring.

For suspected exposure, disable public uploads using DQD_FREE_UPLOADS_DISABLED=1,
preserve restricted operational evidence without recording workbook contents or
tokens, investigate, patch and retest before reopening. Confirm actual provider
retention/deletion behavior and any required notification with the operator.

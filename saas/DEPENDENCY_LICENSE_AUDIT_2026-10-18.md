# Data Quality Detective — dependency licensing and commercial-use audit

**Assessment date:** 2026-10-18 (UTC). **Repository baseline:** `main` at `9f243b6bb3c3310b90032c72a4a68a51abc01191`.
**Release decision:** **NOT CLEARED FOR COMMERCIAL LAUNCH.** This is an evidence-backed technical triage, not a legal opinion or a certification. Do not activate uploads, signups or payments based on this report.

## Evidence inspected and provenance

- Repository `LICENSE`, `pyproject.toml`, `requirements.txt`, `action.yml`, `webapp/saas.py`, `webapp/static/saas.js`, `saas/LEGAL_IP_REVIEW.md`, existing deployment and legal notes.
- GitHub Actions **successful** dependency run [39097397279](https://github.com/Shahedr/data-quality-detective/actions/runs/39097397279), at the exact baseline commit, completed 2026-10-18 04:32 UTC.
- Downloaded **original run artifact** [12125172546](https://github.com/Shahedr/data-quality-detective/actions/runs/39097397279/artifacts/12125172546) containing `third_party_licenses.json` and `dependency_audit.json`. The inventory contains **78 Python distributions** for an Ubuntu/Python 3.11 **`.[dev,saas]` installation** with audit tools. The security report returned **no known vulnerabilities for those resolved distributions at scan time**. This is not proof that the Vercel runtime, Windows add-ons or future installs are vulnerability-free.
- Authoritative third-party sources: [MIT text](https://opensource.org/license/mit), [GNU LGPLv3 text](https://www.gnu.org/licenses/lgpl-3.0.en.html), [GNU licensing FAQ](https://www.gnu.org/licenses/gpl-faq.en.html), [psycopg](https://pypi.org/project/psycopg/), [psycopg-binary](https://pypi.org/project/psycopg-binary/), [Docutils COPYING](https://www.docutils.org/COPYING.html), [Mozilla MPLv2](https://www.mozilla.org/en-US/MPL/2.0/), [pywin32 package](https://pypi.org/project/pywin32/).

**Additional 2026-10-18 isolated audit finding:** The first hosted Python `.[web,saas]` audit reported **33 installed distributions** in its license file, including `psycopg`/`psycopg-binary` LGPL and `certifi` MPL. Its vulnerability step failed **solely on bundled `pip 24.0`**, flagging **12 advisory entries (some duplicated)**; this was the `venv` bootstrap installer, not evidence that `psycopg` or the application had those vulnerabilities. The PR now upgrades isolated bootstrap pip to a fixed release before scanning. **Do not call the revised run successful until it actually passes.** Artifact: [12126485044](https://github.com/Shahedr/data-quality-detective/actions/runs/39099487389/artifacts/12126485044).

**Limits:** The current deployed site uses a separately pinned direct Vercel deployment (see issue [#17](https://github.com/Shahedr/data-quality-detective/issues/17)). The audit's fresh Python dependency resolution does **not** prove those same wheels, platform binaries, hashes or versions were deployed. No checked-in resolved Python production lockfile or SBOM currently exists, and this audit did not inspect every packaged wheel's full license text or bundled native components. The browser uses a separately delivered `@supabase/supabase-js@2.79.0` UMD SDK, which is absent from Python inventory.

## Findings, with precise risk classifications

| Item | Verified evidence | Implication / next action |
|---|---|---|
| Project-owned source MIT | Root `LICENSE` states MIT with `Copyright (c) 2026 Shahed`; `pyproject.toml` also declares MIT | **Commercial SaaS use allowed by MIT**, but only for software whose copyright may legally be granted. Retain MIT text and copyright on copies/substantial distributions. Copyright ownership and third-party contributions are not cleared by a license file. |
| Public source and PyPI/GitHub Action | Public GitHub source, `dqdetect` Python package and composite action | An MIT public release already permits others to reuse, modify and commercially redistribute licensed code under MIT conditions. A proprietary paid hosted service is still possible, but exclusivity of existing published code should not be assumed. |
| `psycopg` 3.3.6 | `LGPL-3.0-only` in 2026-10-18 CI artifact and PyPI | **Not a commercial-use ban.** Server-only unmodified use typically does not entail distribution of application/source to customers just because they use the web service. Assess distribution of Python packages, containers, installers or embedded bundles separately. |
| `psycopg-binary` 3.3.6 | `LGPL-3.0-only` in same artifact and PyPI | Same LGPL review **plus packaged native binaries** (e.g., library bundles), whose actual notices and dynamic/static packaging need release-specific verification. Use the package's license documents, not just the metadata. |
| `docutils` 0.23 | Metadata says BSD/GPL/Public Domain in the **dev-inclusive** CI artifact | **Do not label entire app as GPL.** Official Docutils COPYING explains much of project is public domain; exceptions use BSD, and an Emacs editor helper has GPL. Determine which files, if any, are shipped with a customer artifact. |
| `certifi` 2026.7.22 | `MPL 2.0` in CI artifact | MPL is permitted commercially. If distributing covered files, comply with MPL file-level source/notice obligations; ordinary remote use is different from redistribution. Determine if included in the final hosted image/installer. |
| Other recorded dependencies | 78-package CI artifact contains MIT, BSD, Apache-2.0, PSF, mixed license labels (including `numpy`) | Preserve relevant license and attribution texts when conveying packages. For Apache-2.0, assess NOTICE if present; for multi-license labels, inspect component-specific terms. No blanket clearance from a metadata label. |
| Browser Supabase SDK | `webapp/static/saas.js` loads jsDelivr UMD package pinned to `@supabase/supabase-js@2.79.0` *only after activation* | Supabase JS project's upstream license is MIT; the actual minified distribution/transitive contents and third-party CDN/privacy/security implications have **not** been inventoried. |
| Windows/local extras | Optional `oletools>=0.60.2` and `pywin32>=306` are in `pyproject.toml` | Absent from the Ubuntu `.[dev,saas]` run. `oletools` advertises BSD, while pywin32 says its package has **mixed file-specific licenses**. Audit Windows wheel, transitive packages, packaged native binaries and notices before distributing a bundled Windows installer. |
| Versions and repeatability | `pandas>=2.2`, `openpyxl>=3.1`, `fastapi>=0.115`, etc.; SaaS constrains `stripe>=11,<15`, `PyJWT>=2.9,<3`, `psycopg[binary]>=3.2,<4` | No fully pinned hashes/lockfile for actual direct Vercel deployment. Reproduction is not assured and a future reinstall can materially change the inventory. |

## LGPLv3 analysis specific to this architecture

1. LGPLv3 allows proprietary applications to **use and link** to LGPL libraries; it is **not** equivalent to GPL-only library terms. See the FSF's [LGPLv3 text, especially sections 2–4](https://www.gnu.org/licenses/lgpl-3.0.en.html).
2. **Hosted access is different from conveying software.** Under ordinary GPLv3/LGPLv3 treatment, merely allowing users to interact with an application hosted on your own servers is generally not the distribution/conveyance that triggers delivery of object/source and relinking materials. **AGPL can differ**; no AGPL license was identified in this particular 78-package CI snapshot, but other platform/extra profiles remain unaudited.
3. If **conveying** a combined work containing LGPL-covered libraries (e.g., shipping a packaged app, on-premise binary, container image, modified wheel or executable), section 4 introduces conditions. Depending on packaging, obligations can include notice of the LGPL component, license texts (LGPLv3 and GPLv3), permission to reverse engineer for debugging library changes, and appropriate relinkability / suitable shared library mechanism or corresponding code. Review the *actual binary and link mode*, not only the Python imports.
4. **If you modify the LGPL library and convey that modified version**, stronger conditions apply to the LGPL-covered modifications/source and notices. Do not assume modifications remain private if distributing binaries. **SaaS-only internal modifications** are a different scenario, subject to the exact licenses involved.
5. Do not publish a boilerplate statement promising all LGPL corresponding source is available unless it actually is. Maintain distributable notices and sources as applicable to each concrete release. Have qualified counsel review nonstandard packaging and contracts.
6. The existing **root MIT license need not be replaced** merely because `webapp/saas.py` imports `psycopg`. Conversely, deleting a dependency from a future deployment does not erase compliance obligations for copies distributed previously.

## Required packaging / license controls before paid launch

- [ ] Record the *exact production deployment* commit, Python/runtime version, OS/architecture, installed distributions and hashes; reconcile with Vercel's actual build artifact. The tracked Git-source HTTP 500 issue is separate.
- [ ] Generate a **separate isolated hosted-profile** `.[web,saas]` audit and compare it with the existing `.[dev,saas]` 78-package audit. CI improvements are proposed in this same PR.
- [ ] Create a resolved, reviewable dependency lock or hashes for each supported deploy profile; don't silently change the production runtime as part of a legal audit.
- [ ] Inspect upstream `LICENSE`, `COPYING`, `NOTICE`, source headers and bundled native artifacts for `psycopg`, `psycopg-binary`, `certifi`, `numpy` and packages with multiple metadata labels.
- [ ] Build version-specific third-party attribution/notice package for any downloadable or distributable app. Attribute software owners correctly: the project's root MIT text is **not** a license for third parties.
- [ ] Create separate Windows `.[web,excel-native,macro-audit]` installation audit, including `oletools`, `pywin32`, and transitive / binary dependencies; record Windows Python and Excel architecture.
- [ ] Inventory the pinned Supabase browser SDK and its distribution dependencies; decide whether to self-host with notices/SRI rather than depending on a third-party CDN at auth time.
- [ ] Confirm provenance/permissions for icons, illustrative SVG assets, text, test/example data, any vendor marks, and employee/contractor/AI-assisted contributions.
- [ ] Re-run vulnerability and license checks **per release**, archive JSON/SBOM and lawyer sign-off. A passing `pip-audit` detects reported advisories, not every security flaw.

## Broader commercial/legal launch gates

**Trademark — NOT CLEARED:** In addition to `Data Quality Detective`, search `Data Detective`, `Quality Detective`, visually/phonologically similar brands, related data-analysis / SaaS services and domains. A third-party search page surfaced a *possible lead* for a `DATA DETECTIVE` mark, serial **77919412**, in computer/software services; its legal status, coverage and relevance **have NOT been verified in the live USPTO official record**. Do not treat the third-party listing as a finding of infringement or as official confirmation. Examine [USPTO Trademark Search](https://tmsearch.uspto.gov/) / TSDR, state/common-law use and foreign markets as appropriate, then obtain counsel's clearance. [USPTO comprehensive clearance guidance](https://www.uspto.gov/trademarks/search/comprehensive-clearance-search-similar-trademarks).

**Operator identity — UNRESOLVED:** Choose the *actual* sole proprietor/entity name, country/states served, business and support contact, monitored privacy email and appropriate notices; do not invent an LLC, EIN, street address or business registration.

**Recurring subscriptions — UNRESOLVED:** Publish actual price/currency/billing interval/tax treatment, express recurring-charge consent, confirmation, renewal/cancellation mechanics, effective cancellation date and refund/dispute policy. Confirm federal ROSCA/FTC, applicable state auto-renewal statutes, sales taxes and Stripe rules with counsel. As of this assessment, do **not** assume the FTC's previously announced click-to-cancel rule is the controlling rule without checking its litigation/regulatory status; regardless, maintain truthful disclosures and reasonable cancellation workflows. Stripe's [website requirements](https://support.stripe.com/embedded-connect/questions/information-required-on-your-business-website-to-process-payments) include product description, currency, support contacts, return/refund policy, privacy and other disclosures.

**Privacy/security — UNRESOLVED:** The actual server will receive complete uploaded customer files if enabled. Distinguish *not intentionally stored in application tables* from temporary upload spooling, CDN/WAF access logs, telemetry, provider logs/backups and downloaded reports, which may contain source data/hidden worksheets. Document categories, purposes, lawful bases where applicable, processors (Vercel/Supabase/Stripe/CDN), retention schedules, deletion process **including separate auth and billing records**, data-subject/consumer rights and US/international breach notification. Perform DPA/subprocessor, geographic, age-gating, security and incident-response review. See [FTC data security guidance](https://www.ftc.gov/business-guidance/privacy-security/data-security).

**Terms/service — UNRESOLVED:** Prepare enforceable actual-operator terms covering license to use, acceptable use, analysis accuracy disclaimers, ownership of uploaded data and resulting reports, warranties/limits as legally permissible, termination, export, data deletion and governing law. Draft `/privacy` and `/terms` pages explicitly say they are not final; do not present them as approved customer agreements.

**Go-live — BLOCKED:** Neither `DQD_SAAS_ENABLED` nor `DQD_SAAS_LAUNCH_APPROVED` may be enabled and Stripe live charges/customer uploads/signups must remain off until technical and legal decisions are verified and signed off. This review makes **no deployment, schema or billing changes**.

## Evidence links

- [Repository at assessed commit](https://github.com/Shahedr/data-quality-detective/tree/9f243b6bb3c3310b90032c72a4a68a51abc01191)
- [78-distribution original audit artifact](https://github.com/Shahedr/data-quality-detective/actions/runs/39097397279/artifacts/12125172546)
- [GNU LGPLv3 full license](https://www.gnu.org/licenses/lgpl-3.0.en.html) and [FSF FAQ](https://www.gnu.org/licenses/gpl-faq.en.html)
- [Docutils license exceptions](https://www.docutils.org/COPYING.html)
- [Mozilla MPL-2.0 license](https://www.mozilla.org/en-US/MPL/2.0/) and [MPL FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/)
- [USPTO clearance guidance](https://www.uspto.gov/trademarks/search/comprehensive-clearance-search-similar-trademarks)
- [FTC data security](https://www.ftc.gov/business-guidance/privacy-security/data-security)

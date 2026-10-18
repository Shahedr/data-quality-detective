# Legal, intellectual property, license and privacy review (not clearance)

Status: NOT YET APPROVED FOR A COMMERCIAL LAUNCH. This checklist documents risks and required decisions, not legal advice or a claim that trademark or dependency rights are cleared.

## Trademark and product name

Working product name: Data Quality Detective; command/package identifier: dqdetect. No exhaustive trademark clearance has been performed and no claim of ownership, exclusivity, registration, or freedom to operate is made. Searching only the exact phrase on Google or a limited web search cannot establish clearance.
Before investing in ads, paid subscriptions or a logo: search exact and phonetically/confusingly similar marks for related software/analytics classes in the USPTO Trademark Search database, pending and live registrations, state registries, WIPO/international registers if targeting other markets, domains and common-law business use. Keep dated search screenshots and attorney findings. Rename if risk is material.
USPTO authoritative guidance: https://www.uspto.gov/trademarks/search/comprehensive-clearance-search-similar-trademarks
USPTO Trademark Search: https://tmsearch.uspto.gov/

## Preliminary public trademark screening — not clearance
A preliminary public web search on October 17–18, 2026 for the exact phrase Data Quality Detective did not furnish a verified USPTO registry result or sufficient evidence to declare the phrase available or unavailable. This does NOT establish that there are no conflicting trademarks. The USPTO requires checking confusingly similar words and common-law use: https://www.uspto.gov/trademarks/search/comprehensive-clearance-search-similar-trademarks . A qualified reviewer must examine the live registry, state filings, relevant software/data services and international markets before asserting brand clearance.

## Preliminary third-party license verification
The Stripe Python SDK and Supabase JS client source repositories identify their respective licenses as MIT:
https://github.com/stripe/stripe-python/blob/master/LICENSE
https://github.com/supabase/supabase-js/blob/master/LICENSE
PyPI identifies psycopg and psycopg-binary as LGPL-3.0-only:
https://pypi.org/project/psycopg/
https://pypi.org/project/psycopg-binary/
These are source observations, not a legal assessment of deployed transitive licenses, license obligations or copyright provenance. Keep notices and review actual release artifacts.

## License and copyright provenance

Source repository LICENSE is MIT with copyright 2026 Shahed; this covers only code that the copyright holder is actually entitled to license. A license file does not clear externally incorporated artwork, third-party code, fonts, datasets, copy, platform trademarks or generated material.
Current core Python dependencies include pandas, openpyxl, FastAPI, uvicorn, python-multipart. Optional features include oletools, pywin32, SQLAlchemy, psycopg. SaaS adds PyJWT cryptography, Stripe SDK, psycopg. Hosted browser currently uses Supabase JavaScript SDK through jsDelivr. ALL applicable licenses, versions and transitive dependency notices require collection and review against the actual deployed environment, especially copyleft and attribution requirements.
Preliminary automated dependency inventory from GitHub Actions (October 18, 2026): 78 installed Python packages were enumerated. psycopg and psycopg-binary reported LGPL-3.0-only. docutils reported multiple license labels (BSD, GPL and public domain). These metadata labels require human review of actual distribution terms and the components deployed; they do not independently mean infringement or incompatibility. The first vulnerability audit identified setuptools 79.0.1, affected by CVE-2026-59890, with a fix in setuptools 83.0.0; build and audit tooling are now required to use patched setuptools >=83.0.0. The release must not claim vulnerability-free status until the re-run passes. No third-party legal clearance is yet issued.

Maintain a saved software bill of materials and third-party license inventory for each release. Record SPDX identifiers, license terms, source, copyright notices and security advisory decisions. Do not assume a license is permissive from package names.
Use python -m pip install -e '.[dev,saas]' and pip-licenses and pip-audit in isolated CI; inspect their outputs. Review the npm/browser SDK licensing and hosted CDN privacy implications independently.

## Privacy and terms are draft only

Operator's legal name, physical/business contact details, countries served, and a monitored privacy contact are required before signups. Legal counsel must review data collection categories, notice at collection, purposes, retention and deletion times, processors, cross-border transfers, cookies, children's access, consumer rights, DPAs, security commitments, incident/breach processes, jurisdiction-specific rights and recurring-billing disclosures. Draft routes /privacy and /terms are not the final legally operative texts.
Uploaded datasets can contain sensitive information, including hidden Excel tabs. SaaS processing happens in cloud infrastructure even if file bytes are not deliberately persisted in app tables; multipart upload spooling, telemetry, error logs and provider backups may still process personal data. Do not claim zero retention or end-to-end encryption without proof.
FTC data security and minimization resources: https://www.ftc.gov/business-guidance/privacy-security/data-security
FTC privacy practices: https://www.ftc.gov/business-guidance/privacy-security/consumer-privacy
California privacy rule text may apply depending on business scope: https://privacy.ca.gov/

## Payments

Stripe payments must be in test mode until product price, recurring renewal, cancellations, taxes, refunds, disputes, business/KYC and user-consent language are verified. Do not activate billing keys or promise Stripe's provider terms supersede any applicable consumer protections.

## Release decision record

Trademark counsel / date: PENDING
Dependency license audit / version/date: PENDING
Final privacy counsel / date: PENDING
Commercial terms / operator authorization: PENDING
Independent security review: PENDING
Launch decision: NO — private SaaS remains gated and customer uploads/payments must not be enabled.
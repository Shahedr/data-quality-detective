# Proposed Privacy Policy — DRAFT / NOT AN ADOPTED CUSTOMER NOTICE

**Draft date: 2026-10-18.** This template cannot be published as the final legally operative privacy notice until the **real operator**, monitored contact, supported jurisdictions, effective date, retention periods, subprocessors, security review, and provider agreements have been verified. In particular, do **not** represent it as reviewed by legal counsel or say that uploads are never stored anywhere.

## 1. Who operates the service
Data Quality Detective is a working product name and may be replaced before launch. The service operator is **[LEGAL NAME / BUSINESS TYPE — REQUIRED]**, with contact **[MONITORED PRIVACY EMAIL — REQUIRED]**, business mailing contact **[REQUIRED IF APPLICABLE]**, and notice effective date **[REQUIRED]**. Do not expose your personal home address before determining the lawful and safe business-contact solution.

## 2. Current public demo
The publicly available sample-data demonstration analyzes example information bundled with the product. At the time this draft was prepared, public customer file uploads, hosted customer sign-ups and real payments were disabled by application configuration. Our hosting provider may receive operational request data such as IP addresses, user agent, URLs, timestamps, security events and diagnostic data. We have not verified all Vercel logs, third-party telemetry or retention controls and cannot promise an entirely tracking-free experience.

## 3. Information handled if authenticated SaaS is approved and opened
- **Account identity:** email address, Supabase-managed identity, confirmation/session details, MFA enrollment and authentication/security events.
- **Subscription records:** customer and subscription identifiers, subscription status and recurring plan, and Stripe webhook IDs; the application is not designed to receive full card details.
- **Service use:** user ID, daily request counts, monthly analysis counts, abuse/security events and request metadata.
- **Customer-uploaded spreadsheets:** when an authorized person chooses to send CSV, XLSX or XLSM files, the hosted server receives their contents, including potentially personal/confidential data and hidden worksheets. Extracted data, preview cells, workbook metadata, quality findings and downloaded report content may contain the uploaded information.
- **Messages:** if contacting support, information voluntarily provided in the message.

## 4. Uses and recipients
We use these data to provide accounts and analysis, secure and rate-limit the service, bill and verify subscriptions, handle inquiries and fulfill legal obligations. The intended service providers are **Vercel** for hosting and network delivery, **Supabase** for authentication and private PostgreSQL records, **Stripe** for payment and subscriptions, and **jsDelivr** for the Supabase browser SDK only when the gated private service is configured. The precise processor lists, provider subprocessor changes, agreements, processing regions, and international transfer protections remain **UNVERIFIED**. Do not claim the entire processing lifecycle occurs solely in Ohio: only the currently configured Supabase project region has been verified.

## 5. Spreadsheet processing and downloads
Our current design has no application database table or object-storage workflow for permanently storing uploaded workbook bytes or filenames. The hosted service parses authorized uploads on request and returns results to the browser. **This does not mean uploaded bytes never touch disk or third parties:** HTTP multipart processing can spool uploads to temporary serverless storage and cloud/network providers may keep operational logs, diagnostic data, and backups. We must verify upload limits, duration, encryption, log redaction, backups, deletion practices and subprocessors before accepting real customer files. Generated reports can include the original data and hidden worksheets. Customers control where downloaded reports are saved or shared.

## 6. Browser storage, cookies and SDKs
Supabase Auth on the planned private workspace uses browser-persisted authentication state, including tokens, to maintain sign-in sessions. Third-party services may set strictly necessary security/session cookies or similar mechanisms. We have **not** verified a complete cookie/telemetry inventory. Advertising and optional analytics, if later adopted, need updated disclosures and consent controls where required.

## 7. Retention and deletion — values required before launch
- **Customer uploads and temporary data:** application design does not intentionally persist a permanent workbook record; provider temp data and logs retain until **[VERIFIED RUNTIME/PROVIDER SCHEDULE REQUIRED]**.
- **Identity and sessions:** retained by Supabase according to configured account/session policies; deletion via a verified process with Supabase Auth, subject to justified legal/security exceptions, **[PERIOD REQUIRED]**.
- **Usage and entitlements:** kept in private DQD tables for quota and billing operation, until a verified deletion/retention event, **[PERIOD REQUIRED]**.
- **Stripe billing and accounting records:** retained by Stripe/operator as required by legal, financial and dispute obligations, **[PERIOD/JURISDICTIONS REQUIRED]**.
- **Infrastructure and security logs/backups:** **[VENDOR-BY-VENDOR INVENTORY AND RETENTION REQUIRED]**.

The current DQD account-delete API removes application usage and account records only when no active subscription. It does **not** delete the separate Supabase Auth identity or Stripe records. A complete customer rights/deletion workflow is REQUIRED before launch; merely closing the browser or deleting local browser data does not delete provider records.

## 8. Security and limitations
The design includes HTTPS transport, signed project-specific authentication, private database permissions/RLS, account-specific quotas, disabled public uploads, content security policies and native Supabase project-console access controlled by the cloud provider. A redundant website-based owner console has been retired. A successful test or audit is not a guarantee of perfect security, compliance certification, encryption of every intermediate, or breach immunity. Full hosting ingress, file parsing, concurrency, redaction, session/deletion and incident-response testing remains required.

## 9. Your choices and privacy rights
Subject to the laws applicable to the operator and to the customer's location, individuals may have rights to know/access, correct, delete, export or object to certain processing, as well as appeal. Direct authenticated account and deletion requests to **[VERIFIED PRIVACY CONTACT]**. State-specific instructions, response timelines, identity verification, opt-out methods and regulator information require jurisdictional review. Do not claim that a single US federal rule supplies every consumer right.

## 10. Age restrictions and sensitive data
The commercial service must establish verified minimum-age rules and appropriate age handling before registration. Until a specific data-protection review and necessary agreements, customers should not upload regulated healthcare data, payment card data, government secrets, or highly confidential personal/customer datasets.

## 11. International processing
The Supabase database project is provisioned in US East (Ohio). Other vendors and their subprocessors can process information elsewhere. International transfer mechanisms must be confirmed if serving customers outside the United States.

## 12. Changes and contact
We will publish revised policies with an effective date and required notices for material changes. The public page remains a draft until the actual business operator adopts it. Privacy contact **[REQUIRED]**.

---

### Operator sign-off checklist (mandatory)
- [ ] Verify legal operator identity, monitored email, business address/service contact, countries and states served
- [ ] Obtain accurate Vercel/Supabase/Stripe/CDN logs, deletion and retention schedule, including storage backups and DPA/subprocessors
- [ ] Decide whether/jsDelivr browser SDK must be self-hosted to reduce third-party requests
- [ ] Verify consent/cookie tracking and privacy-right response flows, including Supabase Auth account deletion and Stripe record handling
- [ ] Decide HIPAA/financial/children's/sensitive data prohibitions and limits, incident-response and breach notifications
- [ ] Obtain qualified legal review for actual jurisdictions; remove draft banner only with operator approval

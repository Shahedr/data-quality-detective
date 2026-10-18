# Public website and Stripe activation: verification packet

Status: preparation only. Do not submit this document as a legal agreement or assert that Stripe has approved the account.

## Verified site

Public demo: https://data-quality-detective-demo.vercel.app
Product/availability overview: https://data-quality-detective-demo.vercel.app/product
Private workspace (disabled): https://data-quality-detective-demo.vercel.app/app
Privacy information (draft): https://data-quality-detective-demo.vercel.app/privacy
Service terms (draft): https://data-quality-detective-demo.vercel.app/terms

## Business description for verification

Data Quality Detective provides software to analyze CSV and Excel spreadsheets for potential data quality problems, including duplicate records, missing values, inconsistent entries, and some invalid spreadsheet options, and generates downloadable audit reports. The current public experience is a free sample-data demonstration. Private customer-file processing and paid recurring subscriptions are planned and not yet active.

## Stripe-provided website standards

Official Stripe documentation says public business descriptions must match the offering and, before accepting charges, the site should show an accessible business identity, customer support contact, refund/dispute policy, cancellation policy as relevant, privacy disclosures and other restrictions. See https://support.stripe.com/questions/business-website-for-account-activation-faq

## Operator decisions still needed

- Actual business type: unregistered individual vs registered company. Choose the truth, not what is fastest. Whether an IRS EIN exists is a separate question.
- Legal business name and business address required by Stripe and lawyers; do not invent them.
- Privately monitored support and privacy email addresses, domain control and reliable complaint/dispute handling.
- Price and currency of each recurring plan, tax treatment, trial terms, effective dates, refund policy, billing interval and cancellation procedure.
- Governing laws, jurisdictions served, consumer privacy rights, company status and entity on the legal documents.
- Stripe account activation/KYC, approved transaction descriptions and bank configuration: only the owner may verify and submit.

## Operational release rule

Do not present 'coming soon' as a subscription customers can buy. The deployed site states there is no live commercial offer; the checkout API remains disabled. Never invent a USD price, EIN, business legal address, return policy or refund guarantee to pass verification. Never share Stripe passwords, government IDs, bank details or secret API keys in chats, GitHub, or public issue trackers.

Once the owner supplies the real facts and a qualified legal reviewer confirms policies, update the customer-facing terms, business identity, customer contact, refund/cancellation page and plan prices. Re-run hosted smoke tests, then complete Stripe verification in the official dashboard.
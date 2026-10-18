# Trademark and naming decision — HOLD, not cleared

Review date: 2026-10-18.

## Evidence
- User's direct screenshot of USPTO Trademark Search for `Data Quality Detective` contains a result for **DATA DETECTIVE**, serial **77919412**, marked live/registered, Class 042 (computer services). The screenshot also shows marks such as `DATA QUALITY WATCH` (Class 042), `DATA QUALITY BARRIER` (Class 042) and `DATA QUALITY SCANNER` (Class 009/036). Search returning 7,244 results is **NOT** a count of identical conflicting marks.
- Third-party registry entry for `DATA DETECTIVE`, serial 77919412, reports owner **Keefe Group, LLC** and describes an online system for correctional facilities to track/analyze communications and transactions. This is narrower than generalized data-quality CSV analysis but is still web software. Confirm official current status and scope in USPTO TSDR before relying on details: https://tsdr.uspto.gov/#caseNumber=77919412&caseSearchType=US_APPLICATION&caseType=DEFAULT&searchType=statusSearch.
- The user supplied a screenshot of `https://dqcs.vercel.app/` whose UI is independently labeled **Data Quality Detective**, with a CSV file analyzer and sample-data option. Its ownership, launch date, first commercial use, and independence from this project are **unknown**. Public direct fetch was inaccessible to the research tool, so don't assert it is a competitor, copy, or infringer.

## Assessment
**Commercially important naming conflict risk: HIGH enough to HOLD brand investment; legal infringement finding: NOT ESTABLISHED.** USPTO likelihood-of-confusion considers similarity and the relatedness of goods/services, *not just exact wordmark matches*. The direct same-title screenshot is especially relevant for consumer confusion even if not federally registered. General words `data`, `quality` and `detective` may offer limited distinctiveness. Do not automatically assume the Keefe mark covers all software or that the screenshot site's owner has senior rights.

USPTO guidance: https://www.uspto.gov/trademarks/search/likelihood-confusion and https://www.uspto.gov/trademarks/basics/why-search-similar-trademarks

## No rename automatically
- Keep the current code/repository/domain usable for sample-only development. Do not register an unvetted new brand, move URLs, or rewrite product identity before owner approves a proposed candidate.
- Develop a shortlist of **distinctive coined names** (avoid simply swapping “Detective” for “Scanner” or “Watch”), then perform federal (live+dead) similar and phonetic searches, state/common-law search, domain/store/repository search and target-market review.
- A trademark attorney should review actual owner/priority/use for the exact-title screenshot and the federal record. Preserve dated screenshots and timestamps.
- If renaming, use a migration checklist across UI, domain, GitHub README, Python project/action display, package IDs (avoid breaking existing PyPI install names), legal terms, support email, branding and Stripe business descriptor, with redirects.
- No commercial launch or marketing commitment under the current product name until cleared.

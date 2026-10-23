# Free workspace MVP — isolated review copy

**Superseded review snapshot:** See [REVISION_REVIEW.md](REVISION_REVIEW.md) for
the current preservation-aware Excel export, themes, privacy pages, large-file
test adapter and updated zero-skipped-test results. The values-only cleaning
description below documents the earlier implementation, not the current Excel
cleaning behavior.

This checkout is a separate clone on `feature/free-workspace-mvp`, based on
`ea416cf2a76b9f2badacad9d98c540776291734f`. No remote branch was pushed,
no production configuration changed, and no live deployment was replaced.

## Run the test app

From this directory on Windows:

```powershell
.\.venv\Scripts\python.exe -m uvicorn webapp.app:app --host 127.0.0.1 --port 8765
```

Open http://127.0.0.1:8765. Upload a CSV/XLSX/XLSM file or try the built-in
example. The **Charts, templates & cleaning** link jumps to the new workspace.
The environment is local to this computer, not a public staging deployment.

## Delivered scope

- Cleaning: selected-column whitespace trimming, lowercase/uppercase,
  explicit ISO/US/day-first input date normalization and optional full-row
  duplicate removal. Preview shows original spreadsheet row numbers, before
  and after values, totals and up to 100 examples. A reviewed preview and
  confirmation are required before downloading. Changes to file/options
  invalidate the preview. The source file is never overwritten.
- Explorer: missing counts by column, up to eight numeric histogram bins,
  or eight most common non-missing values. All aggregates are computed by
  this app; no third-party chart or AI provider receives the data.
- Workbook health: visibility of every worksheet, formula counts, explicit
  broken `#REF!` references, stored Excel error cells, external workbook-link
  part counts and VBA project presence. Findings include worksheet/cell
  locations, bounded to 100 examples, with complete totals.
- Plain-English report: deterministic text from actual results, with a
  downloadable UTF-8 report. No invented business impact or AI API costs.
- Audit templates: sales, inventory and customers. Exact expected column
  names are listed in the interface. Absent columns are **not checked**,
  never treated as passing. Required/unique IDs, positive quantities,
  nonnegative amounts/stock, ISO dates and basic email format screening.

## Three review passes

1. **Code and data correctness:** automated API and export round-trip tests,
   including original-byte integrity, leading-zero CSV IDs, literal `NA`,
   formula injection, invalid/stale options, strict dates, bounded previews,
   numeric Excel headers, extreme numeric values, workbook structure,
   hidden sheets, and all template types. Existing regression suite retained.
2. **Human/user workflow:** browser sample analysis → sales template →
   region lowercase + duplicate preview → explicit confirmation → downloaded
   workbook opened independently. Browser Excel upload → inventory screening
   → workbook health → downloaded written report. Checked that errors do not
   appear in the browser console; checked narrow-screen layout at 390px.
3. **Operational/enterprise review:** original inputs untouched; no account,
   payment, external AI or database added; new routes inherit hosted upload
   caps, disabled-upload gates, no-store and security headers. Labels and
   keyboard-native controls are used; stale analysis is aborted when files
   change. This is a technical MVP review, not enterprise certification.

## Important limits

- Cleaned downloads are **values-only XLSX review copies**, including every
  sheet and making hidden sheets visible. Formulas use saved cached values
  when available; absent caches stay blank. Original formatting, VBA, links,
  controls and validation behavior are not reproduced. Keep the original.
- Date conversion applies to text cells using the selected exact format;
  existing typed Excel dates are retained. Unparseable dates stay unchanged.
- Duplicate removal is selected-sheet only, compares entire rows after
  transformations, and keeps the first matching row. It is optional.
- Cleaning preserves CSV strings instead of inferring numeric types. Text
  beginning with `=` remains literal text in Excel. Cells that exceed Excel
  limits or contain forbidden control characters are rejected, not truncated.
- Screening is heuristic. Email checks do not verify delivery. Templates use
  exact headings; there is no mapping editor in this MVP. Outliers and
  duplicates may be valid business records. The report is not legal,
  financial, security, quality or compliance certification.
- Uploads are re-parsed per request; there is no persistent file storage.
  Existing file/row/column/worksheet limits remain, and cleaned XLSX exports
  have a 1,000,000-cell cap. No claim of public-load capacity or hostile-file
  isolation. Production deployment still needs environment-specific checks.
- Full screen-reader testing, real enterprise concurrency/load testing,
  independent security review and multi-Python CI are not completed locally.
  Two existing PostgreSQL tests were skipped because no PostgreSQL test URL
  is configured. JavaScript syntax and the existing Node checks passed.
- Windows desktop packaging was explicitly excluded.

## Production gate

Review this local version before any merge or production rollout. A later
deployment must use an isolated preview first, check the actual hosting
limits and dependencies, and verify CSV/Excel analysis plus all downloads.
Do not promote an untested deployment or promise zero defects.

## Verified result

- Python 3.12 local suite: **118 passed, 2 skipped** (both PostgreSQL).
- New workspace API/data tests: **21 passed**, included in the full suite.
- Browser CSV cleaning download independently opened with openpyxl: 11 data
  rows after deduplication and the expected lowercased region values.
- Browser Excel fixture: hidden sheet and broken reference shown; inventory
  template flags source row 3; written report downloads. No console errors.
- 390px viewport: workspace fits without page-level horizontal overflow.
- Source distribution and wheel build passed; both passed `twine check`.
  `pip check` found no broken requirements. Public hosting, enterprise load and independent
  human/security sign-off remain out of scope for this local test build.

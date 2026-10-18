# Data Quality Detective — browser MVP

This directory contains a **local, functional web interface** for the existing `dqdetect` profiling engine. It is not the hosted paid SaaS product yet.

## Run locally

Requires Python 3.10 or newer. From the repository root:

```bash
python -m pip install -e ".[web]"
python -m uvicorn webapp.app:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000** and select **Try example data** or upload a CSV/XLSX/XLSM file.

The browser requests `POST /api/analyze` and displays the real Python profiler results. For Excel workbooks, you can switch among worksheets and review aggregate sheet counts. It can download **JSON** and a standalone **full-spreadsheet HTML** report; there is no mock analysis.

## Inspect the actual data

After analysis, **Inspect your actual spreadsheet** displays uploaded CSV/Excel
values as a read-only grid. Suspect cells are color-coded and labeled:

- **Missing value**: blank/null cell
- **Invalid date**: a value that fails date parsing in date-like columns
- **Mixed numeric/text**: a value belonging to the minority class
- **Potential IQR outlier**: an unusual numeric value under the existing 1.5× IQR rule
- **Duplicate row**: all rows belonging to an exact duplicate group are marked
  (the overview reports only copies after the first)
- **Constant column**: shown in the header, not falsely presented as a bad cell

Select **All flagged rows** or an individual issue type, then **scroll
continuously through every accepted row**. There are no Previous/Next buttons.
The virtualized viewer creates DOM elements for the visible rows only, so a
50,001-row CSV does not require 50,001 HTML rows in the browser. You can
scroll horizontally to view additional columns. The first column reports the
original data row number.

Internally the app retrieves blocks of 50 rows from the existing `/api/rows`
endpoint, sending the selected local file to the local backend again for
each uncached block. Only recently viewed blocks are cached in the browser;
the backend does not keep a dataset-session cache. Large datasets can
therefore take longer to load additional sections, and continuous scrolling
does not imply an unlimited file size.

**Download full HTML spreadsheet** sends the source to a dedicated local
export endpoint and streams the summary plus **every accepted spreadsheet
data row and column** across **every accepted worksheet** with the actual flagged cells and duplicate groups.
The exported HTML is a single read-only standalone file with scrollable
tables and requires no server to open. It does not recreate Excel formatting,
formulas, macros, filters, or functional dropdown controls. In very large or
wide datasets, browsers may be slow opening the full HTML file; the live
virtualized viewer remains preferable for interactive exploration.
The existing `report_html` field in the analysis API continues to contain a
50-flagged-row preview for backward compatibility; the **Download** button
uses the full export endpoint.

### Download annotated Excel audit (new)

The **Download Excel audit** button generates a separate, macro-free
`*_audit_review.xlsx` file, with one tab for each accepted worksheet, colored
issue cells, an **Issue Register** with original cell references, and a workbook
overview showing totals and warnings. It never changes the uploaded workbook.
The original formulas, executable VBA, Excel tables, dropdown controls,
styles, and hidden-sheet state are **not reproduced**: all accepted worksheet
values are exported as literal text snapshots. The export includes hidden
source sheets as visible review copies, which may expose sensitive data if you
share it. **Never share it without checking those sheets first.**

Because Excel formulas are not recalculated in the browser, formula cells
with no saved cached result remain blank in this separate review workbook.
Use the supervised Windows Excel-native recalculation workflow for fresh
formula results. The XLSX review export caps source grid size at **1 million
cells**, with up to **100,000 issue register entries**; larger jobs should use
the complete HTML export. All exported cell content is forced to literal text,
including strings beginning with `=`, to avoid spreadsheet formula injection.

For Excel files (.xlsx and .xlsm), the browser reads cell values without
executing VBA code or saving over the workbook. In supported Excel data
validation **literal lists** (for example "Open,Closed") and simple
same-/other-sheet A1-range lists, values that are not among the allowed
choices are highlighted and can be filtered under **Invalid dropdown choices**.
Named ranges, INDIRECT/OFFSET/dynamic formula sources, data validation for
dates/numbers, and form/ActiveX controls are not evaluated; a workbook notice
explicitly identifies unsupported list rules. Dropdown options are inspected,
not recreated as usable controls in HTML. Macro presence is reported, but
macro behavior itself is not analyzed, run, tested, or preserved in exports.

A selected-sheet dashboard now includes a **workbook overview** with each worksheet's name, row count, duplicate count, formula count, and selected issue counts. Hidden worksheets are included in the full HTML export and marked as hidden; exports can therefore include data you did not expect. The workbook auditor also inventories Excel tables and reports clearly broken `#REF!` references in formulas. Standard dropdown option values are visible as read-only diagnostic text.

**VBA static source audit:** Optional package `oletools` enables macro source extraction, module inventory, and auto-execution/suspicious keyword triage. Install it from the repo root on the computer running the app:

```powershell
python -m pip install -e ".[web,macro-audit]"
```

Scanner alerts are now labeled by evidence type: **code keyword found**,
**comment/text-only or unverified**, or **scanner heuristic**. These are
interpretation aids, not security verdicts: comments and strings can trigger
scanner rules, and runtime-generated calls may evade keyword matching.

The VBA scanner does **not execute, compile, debug, or prove a macro's correctness or safety**. Scanners can miss malicious or broken code. If the scanner is missing or parsing fails, the dashboard reports this plainly. Real execution requires a separate, explicitly approved and isolated Microsoft Excel for Windows environment; the upload endpoint **never executes macros**. An Excel-native test runner, full formula recalculation, workbook editing, ActiveX/control simulation, and complete VBA execution compatibility are **not included in this preview**.

Excel formulas are **not evaluated or refreshed**: the analyzer reads cached
values when they exist; formula cells with missing or stale caches may appear
blank or outdated. Excel structured tables are inventoried and treated as ordinary cells;
complex relationships across worksheets, custom workbook-defined names,
external connections, and database-like named list objects are not automatically normalized.

Data row numbers start at 1 after the header, so CSV files with embedded
line breaks may not match text-editor physical line numbers. In the live
grid, displayed cell values are truncated at 500 characters; the **full HTML
export does not truncate values**. Source files are never modified.

## Optional Excel-native runner on Windows

If Excel for Windows is installed, see [NATIVE_EXCEL.md](NATIVE_EXCEL.md)
for an independent, supervised CLI tool that opens a copy, uses real Excel to
recalculate formulas, compares stored values, and creates JSON/HTML audit
reports. There is also an **explicitly approved named-macro test mode**, but
this executes VBA with the user's full Windows privileges and **does not
sandbox its side effects**. It is never triggered by CSV/XLSX/XLSM browser
upload. The native Excel engine has mocked-COM automated tests and a Windows
installation test in CI; actual operation with Microsoft Excel on a user's
machine still requires an independent trial.

## Current preview restrictions

- CSV, XLSX and XLSM uploads; inspect up to 40 worksheets and at most 100,000 data rows total and 200 columns on any one sheet.
- Max upload file size 10 MiB; max 100,000 data rows **across all worksheets**, max 200 columns per worksheet, 40 worksheet limit. An expanded Excel ZIP archive may not exceed 250 MiB / 2,000 members.
- Current backend loads files into memory; these limits **do not** guarantee safe memory use for compressed XLSX files.
- No sign-in, subscriptions, payments, rate limiting, job queue, audit logs, tenant isolation, or data retention/privacy policy.
- Uploaded bytes are processed by the application, with no intentional database persistence. The web framework may temporarily spool multipart bytes to disk.
- **Run on loopback (127.0.0.1) only. Do not deploy this preview publicly or send sensitive datasets to an unreviewed hosting service.**

The standalone CLI has no fixed row-count limit and remains the supported distribution in v1.0.0.

## Test

```bash
python -m pip install -e ".[dev,web]"
python -m pytest tests/test_webapp.py -q
```

## Before commercial launch

1. Choose a cleared product/brand name; secure domain; determine suitable business entity and appropriate licenses.
2. Add authentication/authorization, tenant isolation, rate limiting, body-size limits at the proxy, decompression/CPU/memory guardrails, and production observability.
3. Add clear consent, privacy policy, terms, data deletion/retention controls, and security review before allowing business-sensitive uploads.
4. Add Stripe billing with metered events or limited subscriptions, payment webhooks, account entitlements, and abuse controls.
5. Integrate a versioned API key / agent-tool endpoint and separately meter **analysis calls**, not arbitrary LLM token consumption.
6. Validate performance and correctness with realistically large and varied customer datasets.
7. Deploy to appropriate backend hosting, configure DNS/TLS, collect opt-in pilot feedback, and only then begin quoting production service.

This app intentionally does **not** imply trademark protection, an already-available SaaS service, or revenue from OpenAI tokens.

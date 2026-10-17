# Data Quality Detective — browser MVP

This directory contains a **local, functional web interface** for the existing `dqdetect` profiling engine. It is not the hosted paid SaaS product yet.

## Run locally

Requires Python 3.10 or newer. From the repository root:

```bash
python -m pip install -e ".[web]"
python -m uvicorn webapp.app:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000** and select **Try example data** or upload a CSV/XLSX file.

The browser requests `POST /api/analyze` and displays the real Python profiler results. It can download **JSON and HTML** reports; there is no mock analysis.

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

The **downloadable HTML report remains a summary plus an annotated excerpt
of up to 50 flagged rows**, not a full-spreadsheet HTML export. The full
scrollable spreadsheet is currently within the live browser app.
Row numbers start at 1 after the header, so CSV files with embedded line breaks
may not match text-editor physical line numbers. Displayed cell values are
truncated at 500 characters; source files are never modified.

## Current preview restrictions

- Only CSV and XLSX uploads; first Excel worksheet is analyzed.
- Max request file size 10 MiB; max 100,000 rows and 200 columns.
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

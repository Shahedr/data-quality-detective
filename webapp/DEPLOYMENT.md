# Free web app: deployment and limits

Public URL: **https://data-quality-detective-demo.vercel.app**

Data Quality Detective is a free, open-source CSV/XLSX/XLSM quality auditor. It has no subscriptions, registrations, Supabase requirement, or Stripe integration. The Python CLI and locally hosted web app remain independently installable.

## Hosting on Vercel

The root `app.py` exports the FastAPI application. Set the project root to the repository root and deploy the `main` branch using the normal Vercel Python/FastAPI integration. The required hosting dependencies are in `pyproject.toml` (`requirements.txt` also installs the `web` extra). Do not add a catch-all rewrite to `/api/index.py`.

The site is **free**, with no sign-in. `GET /api/config` returns `mode: free_web` and `upload_allowed: true` on Vercel. On Vercel, `DQD_FREE_UPLOADS_DISABLED=1` is the emergency switch to revert to bundled-example-only mode, with all uploads returning HTTP 403. The old `DQD_PUBLIC_DEMO_ONLY` variable is ignored on Vercel because its legacy value should never disable the free app. For local development, `DQD_PUBLIC_DEMO_ONLY=1` still enables sample-only mode.

### What the app actually does

- Receives uploaded spreadsheet bytes at `POST /api/analyze` for server-side parsing and returns a JSON quality report.
- `POST /api/rows` provides filtered, virtual-scrolling row pages; the file is transmitted to the server again for uncached pages.
- `POST /api/export/html` returns a standalone full read-only spreadsheet report. `POST /api/export/xlsx` returns a separate values-only workbook with quality annotations. **No source file is modified.**
- File content isn't intentionally stored in a persistent app database or object storage. However multipart uploads may spool to transient serverless storage, and network/cloud providers can keep operational logs. Do not claim in-browser-only processing or zero retention.

### Host limits and safety caveats

- Hosted request total: **4 MiB file + 64 KiB multipart overhead**, checked against `Content-Length` before multipart parsing; missing/invalid length is rejected. Individual file size is also checked after parsing. Vercel may enforce a stricter platform request-size limit.
- Detailed analysis accepts up to 10 MiB locally and 4 MiB on Vercel. Its parser caps 100,000 data rows across worksheets, 200 columns per sheet, 40 sheets, 1,000,000 rectangular cells, 2,000 ZIP members, and 250 MiB total expanded ZIP content. CSV and workbook dimensions are checked before table allocation.
- A separate localhost-only workflow accepts files up to 1 GiB for streaming inspection and reviewed cleaning. It is unavailable on Vercel. See `LOCAL_HOSTING.md` for supported operations, preservation safeguards and temporary-file handling. Do not expose this adapter publicly.
- The web service NEVER executes VBA, macros, Excel formula recalculation or external workbook connections. XLSM macros are treated as nonexecuted content.
- There are no user accounts, background job queues, hosting-level quotas, or tenant-based records. A free public endpoint can be abused and hosting can suspend/limit it. This is **not a verified safe environment for personal/regulated/confidential data**. For private files, recommend the local mode.

## Operator verification after each deployment

The GitHub `production-safety-smoke.yml` checks real live HTTP behavior: `/api/config` reports free uploads, uploaded 3-row CSV is analyzed, paged rows and HTML/XLSX reports work, oversized and unsupported files are rejected, and all old SaaS routes return 404. It must pass on the public alias after promotion.

Keep the repository open source and avoid enabling unknown third-party analytics or upload storage without documenting them.

## Pending release approval

The owner selected Vercel for smaller public uploads and local hosting for 1 GiB files. The live website must remain unchanged until the draft privacy page has a real operator name and working support/privacy email, and the owner has reviewed the prepared version. No public large-file server is planned for this release.

## Local Windows application

Download ZIP, run `INSTALL_ON_WINDOWS.cmd`, then `START_DATA_QUALITY_DETECTIVE.cmd` to launch the web UI on 127.0.0.1. A separate supervised `START_EXCEL_VALIDATOR.cmd` command exposes local Windows Excel automation for experts, never a public web endpoint.

# Free Data Quality Detective web interface

[**Open the free website**](https://data-quality-detective-demo.vercel.app) · [Repository](https://github.com/Shahedr/data-quality-detective) · [Deploy notes](DEPLOYMENT.md)

The website uses the `dqdetect` Python profiler to inspect **real** uploaded CSV/XLSX/XLSM files and generate reports. There are no accounts, credits, billing, ads, or persistent uploaded-file tables.

## Try it

Open the website, choose **Try example data**, or upload a spreadsheet (up to 4 MiB on the hosted service). The interface shows sheet metrics, individual issue types, a read-only virtualized grid, and separate exports for JSON, full HTML and highlighted XLSX audit.

It detects missing values, duplicate records, invalid dates, mixed numeric/text values, numerical outliers, and selected Excel dropdown issues. It inspects workbook structure and reports formula and macro information **without executing macros or recalculating formulas**. The downloaded review Excel workbook contains **literal values**, not executable original formula or macro content.

## Run privately on your own computer

```bash
python -m pip install -e ".[web]"
python -m uvicorn webapp.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. The locally served app supports 10 MiB files and does not send workbook content to the hosted Vercel site. Windows users can run `INSTALL_ON_WINDOWS.cmd` followed by `START_DATA_QUALITY_DETECTIVE.cmd` instead.

## Privacy and accuracy limitations

**Hosted uploads are server-side, not browser-local:** File contents are sent to Vercel. The application itself does not intentionally persist workbook bytes, filenames or row contents in a database; multipart temporary files, logs, provider backups, and other infrastructure behavior have not been exhaustively audited. Do **not** upload confidential, health, financial-account, regulated or sensitive personal data. For such work, use a trusted local environment.

Public hosting has no authentication, advanced rate limiting, malware sandbox, or data-protection certification. It has strict upload and workbook limits, but those limits do not guarantee availability under resource-intensive or malicious files. There is no user-upload storage and no ability to retrieve previously submitted files. Web inputs are treated as values; third-party VBA never runs.

Excel formulas are read as cached values if present and are **not** freshly calculated; hidden worksheets may be included in generated audits, so review exports before sharing. Dynamic validation lists, indirect formula evaluation, ActiveX/control behavior and all Excel-native desktop features are out of scope for hosted use.

The optional [Windows native Excel workflow](NATIVE_EXCEL.md) runs locally and may request high-trust explicit user approval to execute VBA; never run untrusted macros.

## API

`POST /api/analyze`, `/api/rows`, `/api/export/html`, `/api/export/xlsx` accept multipart uploads. `GET /api/config` describes the server's active free/public sample mode. There are no `/api/saas` routes. Set `DQD_FREE_UPLOADS_DISABLED=1` on Vercel to temporarily disable uploads while leaving the fictional sample demo available. Locally, `DQD_PUBLIC_DEMO_ONLY=1` does the same.

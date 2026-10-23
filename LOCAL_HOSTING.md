# Local hosting

Double-click `START_DATA_QUALITY_DETECTIVE.cmd` from this clone. It uses this
clone's virtual environment when installed, selects an available loopback port
and opens the app. Keep the server running while inspecting files. This does
not change the public website or need a hosting account.

For a fixed port without opening another browser:

```
.venv\Scripts\python.exe -m webapp.launch_local --port 8765 --no-browser
```

Files above 10 MiB selected in the main picker automatically open large-file
inspection. The large-file panel also accepts smaller files. Maximum input is
1 GiB (1,073,741,824 bytes), uploaded in chunks of at most 4 MiB. One large job
runs at a time. Allow at least the input size plus 256 MiB free temporary disk
space for inspection. Cleaning reserves four times the input size plus 256 MiB
and checks remaining disk space while processing. Use Cancel to stop or discard
a prepared copy.

CSV inspection counts every data row and blank value. Excel inspection streams
each worksheet's XML and counts stored rows/cells, formulas and cached errors,
including hidden sheets. Original files, formula text and VBA remain unchanged;
the service never opens Excel or executes workbook code. Download overview
saves a separate JSON report. After inspection, expand Prepare a cleaned
large-file copy. Select CSV columns, or Excel column letters and a worksheet.
Preview trimming, case normalization and explicit-format date conversions over
the entire file. CSV duplicate removal compares complete transformed rows using
SQLite on temporary disk. Invalid dates remain unconverted.

Excel cleaning treats row 1 as headings, skips formula cells, blocks row
deletion and refuses signed or changed rich-text cells. Every untouched ZIP
member is hashed against the original; selected worksheet XML is validated.
Shared strings use a disk-backed index. No-change Excel copies are byte-identical.
Original formulas/VBA remain intact, but changing inputs can change their results.

Review the first 100 changes and complete counts, confirm, then download the
separate CSV/XLSX/XLSM copy. The prepared file is held locally until download,
explicit discard or expiry; only one pending copy/job is allowed. Downloads
stream through the browser without loading the entire file into JavaScript.
CSV quoting/line endings normalize; spreadsheet software may interpret
formula-like CSV text when opening it. Large mode does not yet provide the
smaller workspace's templates, grid or charts. Cached errors are not recalculation.

Safety bounds: UTF-8 CSV, 200 unique nonblank headings (200 characters each),
1 MiB per CSV record; Excel up to 40 worksheets, 10,000 package entries, 8 GiB
expanded package size, 64 XML levels and 1 MiB continuous XML text/markup tokens.
ZIP64 and multipart ZIP directories are unsupported. Changed Excel cells must
fit the 2 MiB cell XML bound and Excel's string limit. Excel's
row/column limits apply. Each job has a 15-minute processing deadline. Unusual
files can be rejected below the input-size cap; the app never silently truncates
the overview. Password-protected packages are unsupported.

The launcher binds only to 127.0.0.1 and ignores proxy forwarding headers.
Requests require a local Host/client and matching Origin when present. Each
large upload requires its own unguessable header token. Do not expose this
single-user local service through a tunnel, LAN bind or reverse proxy. It has
no user accounts or public-hosting access controls.

Temporary sources are removed when inspection/preview finishes, fails or cancels.
Prepared output is deleted after download, discard, failure or expiry. A
30-second background sweep clears inactive jobs after an hour; active upload
chunks renew the inactivity timer. Keep the server running for that cleanup.
An operating-system crash or forced kill can leave temporary files; this is not
secure disk erasure. Downloaded reports stay on your device. At most 20 finished
job reports are retained in server memory in addition to the current job.

Verification scripts (developer tools): `verify_large_local.py` uploads actual
1 GiB CSV and XLSX over HTTP and measures server memory. `verify_real_excel.py`
uses only generated fixtures with dedicated Excel automation; it never changes
Trust Center settings. `verify_vba_preservation.py` uses a hash-pinned official
XlsxWriter greeting fixture, follows existing Excel policy, and pauses for
per-workbook approval with `--approve-in-excel`. Reports are in `reports/`.
`verify_large_local.py --clean` verifies actual 1 GiB CSV and XLSX previews,
full streamed downloads, hashes and cleanup.

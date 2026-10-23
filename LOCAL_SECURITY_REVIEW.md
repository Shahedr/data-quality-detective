# Local release verification — 2026-10-21

## Follow-up — 2026-10-23

See ASVS_SELF_ASSESSMENT.md and its requirement matrix for the current scoped
ASVS 5.0.0 self-assessment, browser hardening and remaining release gates.
The independent AI follow-up is now completed for its reviewed local scope;
INDEPENDENT_AI_REVIEW.md supersedes earlier interrupted-review status below.
Operator/contact details have been supplied but email delivery, provider policy
details and public deployment verification remain unverified.

## Latest verified state (supersedes historical entries below)

- **164 tests passed, zero skipped**, including PostgreSQL; package build and
  metadata validation passed. Dependency deprecation warnings remain.
- Actual **1 GiB CSV and XLSX cleaning**, previews and full HTTP downloads passed
  with matching output hashes, expected changes and cleanup. CSV changed
  1,048,576 cells in 32.73 seconds; XLSX changed 99,999 cells below its header
  in 32.28 seconds. Peak process-tree RSS was 126,054,400 bytes (about 120 MiB).
- CSV processing was then combined into a single row pass for counting and
  cleaning. Its repeated 1 GiB upload/clean/download test completed in **24.95
  seconds**, compared with 32.73 seconds before (about 24% faster on this run).
  Preview counts, complete output hash and deletion still matched. Repeated
  validation of a 20,000-row, 10-column workbook measured **1.052 seconds cold
  versus 0.0003 seconds cached**. This is validation timing, not whole-audit timing.
  The bounded cache holds only validation hashes and includes resource limits
  in its key; workbook values are not retained there.
- Both cleaned XLSM paths opened/recalculated correctly in real Microsoft Excel.
  After the owner approved the reviewed test workbook, its preserved greeting
  VBA macro executed successfully. Original source and VBA binary stayed
  unchanged. This verifies that fixture, not all possible VBA applications.
- Bandit: zero outstanding findings. pip-audit: **37 installed app-feature
  runtime distributions**, no known vulnerabilities; scanner/test-only tools
  are excluded. This includes installed database, native Excel and VBA-scanner
  extras. Advisory coverage does not prove absence of vulnerabilities.
- The separately authorized AI reviewer independently found resource, XML,
  SQLite and download-lifecycle defects. Fixes and regression tests were added.
  Its final sign-off was interrupted by the review service; see
  `INDEPENDENT_AI_REVIEW.md`. A completed independent final approval is not claimed.
- Large mode now supports preview-first cleaning, not only summaries. Charts,
  templates and grids remain in the detailed smaller-file workspace. Formula
  editing, Excel row deletion, signed workbook editing and changed rich text
  remain blocked to protect workbook integrity. ZIP64 directories are unsupported.
- Production is unchanged. No website upload executes Excel or VBA.
- Browser flow verified in a separate tab using fictional data: choose columns,
  select day-first dates, preview one conversion while retaining an invalid date,
  confirm and download CSV, then reopen the actual downloaded bytes. Native
  form downloads required changing Referrer-Policy to same-origin; this keeps
  external referrers private while preserving Origin for the same-origin POST.
  Cross-origin and null-Origin requests remain blocked. Dark preview screenshot
  is saved beside the clone as `large-cleaning-preview-dark.png`.

## Historical verification snapshot

Scope: the isolated `feature/free-workspace-mvp` clone, loopback-only hosting.
The production repository and website have not been changed. This is an
engineering review and automated testing, **not an independent security review**.
The owner has no independent reviewer arranged. That release gate remains open.

## Findings fixed

- Ordinary local multipart requests were not bounded before Starlette parsed
  them. Both declared and actual bytes are now capped before multipart parsing;
  a forged Content-Length cannot bypass that check. Large job-creation JSON is
  capped at 8 KiB. Large-file chunks stay capped at 4 MiB.
- All local routes now reject nonlocal clients/Host values. State-changing
  requests with a different Origin are rejected. The launcher disables proxy
  headers. The service must not be exposed through a tunnel or reverse proxy.
- Large chunk credentials/state are checked before reading a body, then checked
  again before appending. Exact offsets prevent duplicate chunk writes.
- CSV limits now bound whole logical records, including quoted multiline data,
  rather than allowing 200 separate maximum-size fields in one record.
- Streaming workbook inspection uses defusedxml, caps metadata, XML nesting and
  text and markup-token size before parsing attributes, Excel coordinates,
  sheet count, package entries and expanded bytes.
  Duplicate package paths, traversal names and encrypted entries are rejected.
- Cancellation and processing deadlines interrupt readers. The temporary
  source is removed in a finally block; an expiry thread now runs without
  requiring another visitor request. Finished report metadata is capped.

## Evidence

- Full suite: **149 passed, zero skipped**, including real PostgreSQL tests.
  A Starlette test-client deprecation warning remains; it is not a test failure.
- Actual loopback HTTP uploads: two exactly **1,073,741,824-byte** files. CSV
  counted 1,048,576 data rows. XLSX scanned 100,000 real 10,000-character cells
  (roughly 1 GB worksheet XML), not just a padded tiny sheet. Checksums, byte
  counts, expected results and post-deletion 404 responses matched. Peak process
  tree RSS was 121,253,888 bytes (about 116 MiB). CSV took 11.28 seconds and XLSX
  13.06 seconds in this test; these are measurements, not performance promises.
- Bandit source scan of `webapp` and `dqdetect`: zero outstanding findings. One
  documented suppression covers importing SAX ContentHandler only: the parser
  is defusedxml, and hostile entity/depth/text tests exercise that boundary.
- pip-audit: 24 app/native runtime distributions, no known vulnerabilities.
  Inventory: `native-audit-requirements.txt`. Scanner/test-only dependencies are
  excluded; advisory coverage is not proof of absence of vulnerabilities.
- Microsoft Excel 16.0: generated cleaned XLSX opened without repair, formula
  `=B2*C2` recalculated to 21, trimmed text matched, number format and hidden
  worksheet remained, source bytes stayed unchanged. Evidence and fixtures are
  in `reports/real-excel/`.
- VBA execution: **blocked, not passed**. Existing Excel policy denies
  programmatic VBProject access, so a reviewed test macro could not be created.
  Trust Center settings were not changed. Binary-preservation tests passed,
  but runtime VBA compatibility remains unverified. To finish that check, use a
  human-created reviewed fixture or a dedicated disposable Excel test machine.
- Browser automation was blocked by browser access controls. The owner refreshed
  the app and confirmed the dark worksheet dropdown is now more readable.
  Automated end-to-end worksheet-selector interaction is unverified in this
  revision; no automated browser pass is claimed.

## Practical limits and public-release gates

Large-file inspection is read-only overview, not full GB-scale cleaning,
templates, charts or grid. XLSM uses the same package scanner; its VBA is never
executed. Public hosting, authentication, worker isolation, public abuse/load
tests, legal operator/contact details and independent security review remain
future release work. Normal small-workbook cleaning retains its stricter limits.

The local service trusts the operating-system user. It is not protected from
malware, privileged local processes, Excel add-ins or a compromised machine.
Parser deadlines are cooperative, not process isolation. A crash/forced kill
can leave temporary files; cancellation/deletion is not secure erasure. Keep
source backups. Never enable macros from an unreviewed workbook.

For an independent reviewer: inspect `webapp/app.py`, `largefiles.py`,
`largeworkbook.py`, `preserve.py`, `workbook.py`, exports and browser rendering;
rerun the suite and both integration scripts; specifically assess local request
forgery, parser resource exhaustion, spreadsheet export injection, preservation
integrity, cancellation and retention under failures. Do not close this gate
based only on this document or scanner output.

# Preservation, simpler UI, privacy and large-file test revision

## Latest: large-file cleaning and real VBA verification

Full-file preview/cleaned exports now work for CSV and XLSX/XLSM up to 1 GiB.
Actual 1 GiB CSV/XLSX files were transformed and downloaded over HTTP with
matching hashes and about 120 MiB peak process-tree memory. CSV duplicate
removal uses SQLite; Excel patches selected literal cells and preserves other
parts, with formula edits and row deletion blocked. The user approved a reviewed
test workbook in Excel, and its preserved VBA greeting macro ran successfully.
Both small and streaming cleaned XLSM copies opened/recalculated correctly.

The independent AI reviewer found several issues that were remediated, but its
final sign-off was interrupted by the review service. See
`INDEPENDENT_AI_REVIEW.md` for the exact distinction between completed review,
primary-implementer regression tests and pending independent final approval.
The following sections are historical snapshots where they differ from this one.

## Current local-hosting revision (supersedes historical limits below)

See `LOCAL_HOSTING.md` and `LOCAL_SECURITY_REVIEW.md` for current behavior and
evidence. Large read-only inspection now supports CSV, XLSX and XLSM up to
1 GiB; actual 1 GiB CSV and XLSX loopback uploads passed with bounded memory.
Cancellation, periodic expiry, downloadable overview and worksheet selection
are implemented. The smaller full workspace keeps its separate size limits.
Real Excel formula recalculation passed; VBA fixture creation was blocked by
existing Excel policy and was not bypassed. Independent review is still open.
All 149 tests passed with zero skips. Dark worksheet dropdown contrast was
corrected, with an additional synchronized picker inside workspace tools.

## Latest usability revision

- The color-theme button now floats at the bottom-right and remains visible
  while scrolling. The user's previously open tab was an older in-memory page;
  it was refreshed to the latest build and dark mode was verified there.
- Templates no longer require exact source headings. Familiar headings get
  conservative alias suggestions; ambiguous matches stay unmapped. Users can
  map any source column manually without renaming the workbook.
- Audit date format can be selected explicitly (ISO, month-first, day-first).
  Column/date changes invalidate the displayed audit and written-report download
  until rerun. Results show applied-check coverage, with unmapped fields clearly
  not assessed. Invalid or duplicate mappings fail with a clear error.
- Browser validation used unrelated headings `Our Ref`, `When Bought`,
  `How Many`, `Each Cost`, mapped all four sales fields and correctly flagged
  the invalid date at source row 3 using day-first dates. No console errors.
- **138 tests passed with zero skips**, including PostgreSQL and the real
  1 GiB upload/processing test. This supersedes earlier counts below.

An exported `_audit_review.xlsx` report is a values-only analysis artifact.
Upload the original workbook to test formula/VBA preservation; missing original
formulas cannot be recovered from an audit report.

This is the current review document. It supersedes the original values-only
cleaning limitations in MVP_REVIEW.md. Production is unchanged. No remote
branch, cloud storage, account, public deployment or live alias was changed.

## Implemented and verified

- Excel cleaning preserves the original OOXML package. Only approved literal
  cells in the selected worksheet are patched. Every other ZIP member is
  checked byte-for-byte against the source before offering the copy. Formulas,
  VBA payloads, worksheet visibility, styles, custom XML and relationships are
  retained. XLSM files keep their XLSM extension and MIME type.
- A no-change export returns the exact original bytes. There is also a direct
  original-file download in the browser. Original input bytes are not edited.
- Excel row deletion, edits to formula cells, signed workbook changes and
  unsupported rich-text cell changes are blocked. These restrictions protect
  references and unsupported workbook features; they are not silently ignored.
- Changing data inputs can change formula results or macro behavior even when
  their code/formulas remain intact. This app does not run Excel/VBA and cannot
  certify their runtime behavior. Review changed copies in trusted Excel.
- The separate audit report is explicitly labeled as an audit document without
  original formulas/VBA. It is grouped under report downloads so it is not
  confused with the original or preservation-aware cleaning copy.
- Light/dark switch, in-memory theme preference, native expandable tool panels,
  collapsed spreadsheet/column details and grouped report downloads. No cookie,
  localStorage or analytics was added. The chosen theme resets on reload.
- Privacy, cookies and usage-information pages describe actual local behavior,
  temporary processing, security limits and pending public-release details.
  `help-data@example` is explicitly a test placeholder, not a working address.
- Hardened XML parsing via defusedxml; new large-file routes enforce local
  access, same-origin requests, opaque upload credentials, exact offsets,
  per-chunk and total-size bounds, disk headroom and single-job concurrency.

## Real large-file evidence and limits

The local adapter uses chunked uploads, temporary disk storage and streaming
CSV processing. Tests generate a real **1,073,741,824-byte CSV** (not sparse),
upload all chunks through the API, finish processing, verify the row counts and
SHA-256 and confirm deletion of the server-side temporary source. Browser
verification exercises the same upload/job/report flow using a small fixture.

This is **not public 1 GB support**. The current public Vercel Function upload
path has a 4.5 MB platform request limit. The test adapter is deliberately
disabled on Vercel and for nonlocal requests. Public direct-upload storage,
an authenticated/rate-limited job service, isolated workers, quotas, cancellation,
retention enforcement and operational monitoring must be provisioned and tested
before public use. The user has deferred the server/provider choice.

The large-file path currently provides exact CSV row and blank-value counts
and a source checksum. It does not yet provide detailed GB-scale charts,
duplicate analysis, interactive grids or cleaning. **1 GB XLSX/XLSM processing
and preservation are unverified and unsupported by that path.** The ordinary
small-workbook path keeps its existing resource limits rather than pretending
it can safely load a GB-scale workbook into memory.

Large CSV fields are limited to 1 MiB and files to 200 columns to bound parsing.
Files are deleted after completion/failure or explicit clearing. Abandoned
uploads expire opportunistically after an hour on later API access. Normal
shutdown removes the temporary directory; crash recovery and guaranteed
retention schedules are not claimed.

## Test results

- **127 passed, zero skipped** on Python 3.12 using a real, isolated PostgreSQL
  16 test database bound only to 127.0.0.1:55432 with random test credentials.
- Existing PostgreSQL tests actually executed. A local runner fails the run if
  any test is skipped. The CI matrix now provisions PostgreSQL and installs
  the database driver so those tests can run there too; remote CI is unrun.
- Preservation round-trips check formulas, hidden sheets, styles, custom XML,
  macro bytes and the unchanged-original case. Signed/formula edits fail closed.
- Browser Excel download reopened independently: expected text change present,
  formulas preserved, hidden worksheet retained, only selected worksheet XML
  changed. No browser console errors in the tested flows.
- Dark/light switch, collapsed tools, privacy link and chunked CSV flow checked
  in the browser. Narrow-screen QA from the initial build is supplemented by
  the current theme/layout review. Full screen-reader testing is outstanding.
- `pip-audit` checked the 23 installed distributions in the current runtime
  dependency closure and reported **no known vulnerabilities**. The inventory
  and JSON results are in `runtime-audit-requirements.txt` and `runtime-audit.json`.
  This excludes unrelated development/scanner packages and is not proof of
  absence of vulnerabilities or an independent penetration test.
- Source and wheel builds plus package metadata validation passed. There is
  one test-library deprecation warning about Starlette's future HTTPX adapter;
  it does not skip tests or fail the current suite.

## Still required before public release

This is a test revision, not a completed enterprise-ready release. Public 1 GB
processing, large Excel workloads, real Excel/VBA runtime validation, independent
security review, load/abuse testing, live hosting-cookie inventory, legal operator
details, a working support contact and final jurisdiction-specific legal review
remain outstanding. The original live app was not modified to bypass its limits.

References: [Vercel Function limits](https://vercel.com/docs/functions/limitations),
[direct-upload guidance](https://vercel.com/kb/guide/how-to-bypass-vercel-body-size-limit-serverless-functions),
[ICO cookies guidance](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/guide-to-pecr/cookies-and-similar-technologies/).

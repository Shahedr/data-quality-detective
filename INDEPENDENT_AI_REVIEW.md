# Independent AI review record

## Completed follow-up — 2026-10-23

A separate AI reviewer inspected the final local preview scope and independently
passed 88 focused tests. It found two blockers: CSV dimensions were checked after
table allocation, and changing large-file cleaning options could retain stale
download approval. Both were fixed and independently re-reviewed, with no remaining
blocking finding identified in that scope. Two CSV regression tests were added;
the complete suite passed 166 tests with no skips (20 dependency warnings).

The reviewer did not check live browser behavior, hosted production, real Excel
or large-file benchmarks. Earlier implementer checks of Excel and 1 GiB exports
are separate evidence, not independent retests. This is an AI code review, not a
human security review or certification. Public release remains on hold for the
operator/privacy contact details and owner review.

## Earlier partial review — 2026-10-21

The owner explicitly authorized a separate AI reviewer. The reviewer was given
read-only access to this isolated clone and asked to challenge input limits,
preservation, request boundaries and cleanup. It reported 46 passing focused
tests in its initial review and independently reproduced issues below.

**Status: partial independent AI review, not a final security sign-off.** The
review service interrupted the session while preparing further security checks,
and interrupted a later code-only review. No completed final approval was
returned. The primary implementer applied and tested the remediations below;
that is not an independent retest of the complete final patch. No human security
review or certification has occurred.

| Reviewer finding | Remediation in this clone |
|---|---|
| Sparse worksheet dimensions can expand before pandas checks limits | Bounded XML preflight validates dimensions, cells, row indices, combined rows and cell count before pandas; worksheet references are validated |
| ZipFile eagerly allocates central-directory metadata before entry checks | EOCD entry/metadata bounds run before ZipFile; unsupported ZIP64 locators and directory layouts are rejected |
| SQLite context manager leaves connections open on Windows | Explicit closing context releases handles before deleting temporary indexes |
| Inline-string indentation becomes cell content | Only actual text-node content is transformed |
| Cell matcher can mistake namespace prefix c for a cell | Complete tag delimiter is required; prefixed worksheet regression passes |
| Shared-string parser lacks a depth cap | SharedStrings enforces the same 64-level depth limit |
| Dynamic cleaned-download form needs a body limit | 8 KiB declared and actual body cap runs before form parsing |
| Download failure before generator entry can strand output and job quota | Response-level finally closes the iterator and deletes output; unstarted download lease expires; transfer deadline and Content-Length apply |

Additional primary-implementer checks cover cancelled workers, stale uploads,
preview confirmation/replay rejection, signed/formula safeguards, invalid mapping,
wrong offsets/tokens, full 1 GiB cleaned exports and real Excel/VBA preservation.
See the test suite, `LOCAL_SECURITY_REVIEW.md` and `reports/` for evidence.

Public release still needs an independent reviewer to inspect the final patch
and operational design. This record must not be presented as an audit certificate.
